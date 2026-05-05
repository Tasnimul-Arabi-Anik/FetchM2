from __future__ import annotations

from pathlib import Path

import pandas as pd

from fetchm2.cli import build_parser, main
from fetchm2.metadata import MetadataCache, RequestRateLimiter, fetch_biosample_metadata


def test_metadata_cli_offline(tmp_path: Path, monkeypatch) -> None:
    input_path = Path(__file__).resolve().parents[1] / "examples" / "offline_metadata.tsv"
    outdir = tmp_path / "out"
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetchm2",
            "metadata",
            "--input",
            str(input_path),
            "--outdir",
            str(outdir),
            "--offline",
        ],
    )
    main()
    clean_path = outdir / "metadata_output" / "fetchm2_clean.csv"
    audit_path = outdir / "audit" / "standardization_audit.md"
    assert clean_path.exists()
    assert audit_path.exists()
    assert (outdir / "audit" / "production_readiness_gate.md").exists()
    assert (outdir / "audit" / "production_readiness_gate.json").exists()
    assert (outdir / "audit" / "rule_count_summary.csv").exists()
    assert (outdir / "metadata_analysis" / "metadata_analysis_report.md").exists()
    assert (outdir / "metadata_analysis" / "tables" / "field_coverage_summary.csv").exists()
    assert (outdir / "metadata_analysis" / "tables" / "top_values_by_field.csv").exists()
    df = pd.read_csv(clean_path)
    assert "Host_SD" in df.columns
    assert "Host_Context_SD" in df.columns
    assert "Isolation_Source_SD" in df.columns
    assert "Environment_Medium_SD" in df.columns
    assert (df["Country"].fillna("") == "Hospital").sum() == 0


def test_sequence_check_only_cli(tmp_path: Path, monkeypatch) -> None:
    input_path = Path(__file__).resolve().parents[1] / "examples" / "offline_metadata.tsv"
    meta_out = tmp_path / "meta"
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetchm2",
            "metadata",
            "--input",
            str(input_path),
            "--outdir",
            str(meta_out),
            "--offline",
        ],
    )
    main()
    clean_path = meta_out / "metadata_output" / "fetchm2_clean.csv"
    seq_out = tmp_path / "seq"
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetchm2",
            "seq",
            "--input",
            str(clean_path),
            "--outdir",
            str(seq_out),
            "--country",
            "Bangladesh",
            "--check-only",
        ],
    )
    main()
    assert (seq_out / "failed_accessions.txt").exists()
    assert (seq_out / "sequence_download_summary.csv").exists()


def test_analyze_cli_generates_figures(tmp_path: Path, monkeypatch) -> None:
    input_path = Path(__file__).resolve().parents[1] / "examples" / "offline_metadata.tsv"
    meta_out = tmp_path / "meta"
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetchm2",
            "metadata",
            "--input",
            str(input_path),
            "--outdir",
            str(meta_out),
            "--offline",
            "--no-analysis",
        ],
    )
    main()
    analysis_out = tmp_path / "analysis"
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetchm2",
            "analyze",
            "--input",
            str(meta_out / "metadata_output" / "fetchm2_clean.csv"),
            "--outdir",
            str(analysis_out),
        ],
    )
    main()
    assert (analysis_out / "metadata_analysis_report.md").exists()
    assert (analysis_out / "tables" / "numeric_summary.csv").exists()


def test_validate_cli_writes_production_gate(tmp_path: Path, monkeypatch) -> None:
    input_path = Path(__file__).resolve().parents[1] / "examples" / "offline_metadata.tsv"
    meta_out = tmp_path / "meta"
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetchm2",
            "metadata",
            "--input",
            str(input_path),
            "--outdir",
            str(meta_out),
            "--offline",
        ],
    )
    main()
    validate_out = tmp_path / "validation"
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetchm2",
            "validate",
            "--input",
            str(meta_out / "metadata_output" / "fetchm2_clean.csv"),
            "--outdir",
            str(validate_out),
        ],
    )
    main()
    assert (validate_out / "production_readiness_gate.md").exists()
    assert (validate_out / "production_readiness_gate.json").exists()
    assert (validate_out / "broad_vocabulary_leakage.csv").exists()


def test_cli_help_includes_core_commands() -> None:
    help_text = build_parser().format_help()
    for command in ["metadata", "run", "seq", "audit", "validate", "analyze"]:
        assert command in help_text


def test_biosample_esummary_fallback(monkeypatch, tmp_path: Path) -> None:
    class FakeResponse:
        def __init__(self, text: str = "", payload: dict | None = None, status_code: int = 200) -> None:
            self.text = text
            self._payload = payload or {}
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

        def json(self) -> dict:
            return self._payload

    fallback_xml = """
    <BioSample>
      <Description><Organism taxonomy_name="Escherichia coli"/></Description>
      <Attributes>
        <Attribute attribute_name="host">human</Attribute>
        <Attribute attribute_name="geo_loc_name">Bangladesh: Dhaka</Attribute>
        <Attribute attribute_name="collection_date">2020-04-01</Attribute>
      </Attributes>
    </BioSample>
    """
    calls: list[str] = []

    def fake_get(url, params, timeout):
        calls.append(url)
        if "efetch.fcgi" in url:
            return FakeResponse("<BioSampleSet></BioSampleSet>")
        if "esearch.fcgi" in url:
            return FakeResponse(payload={"esearchresult": {"idlist": ["123"]}})
        if "esummary.fcgi" in url:
            return FakeResponse(payload={"result": {"123": {"sampledata": fallback_xml}}})
        raise AssertionError(url)

    monkeypatch.setattr("fetchm2.metadata.requests.get", fake_get)
    cache = MetadataCache(tmp_path / "cache.sqlite3")
    try:
        result = fetch_biosample_metadata(
            "SAMN00000001",
            api_key=None,
            email=None,
            rate_limiter=RequestRateLimiter(0),
            cache=cache,
        )
    finally:
        cache.close()
    assert result["Metadata Fetch Status"] == "ok"
    assert result["Host"] == "human"
    assert "esummary_fetched" in result["Metadata Fetch Reason"]
    assert any("esummary.fcgi" in url for url in calls)
