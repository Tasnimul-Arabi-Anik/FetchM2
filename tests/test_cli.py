from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from fetchm2.cli import build_parser, main
from fetchm2.metadata import MetadataCache, RequestRateLimiter, fetch_biosample_metadata
from fetchm2.sequence import DirectoryCache


def test_metadata_cli_taxon_query_generates_dataset(tmp_path: Path, monkeypatch) -> None:
    class FakeCompletedProcess:
        returncode = 0
        stderr = ""

        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    payload = {
        "accession": "GCF_000001405.1",
        "assembly_info": {
            "assembly_name": "ASM140v1",
            "assembly_level": "Complete Genome",
            "assembly_status": "current",
            "release_date": "2020-01-02",
            "bioproject_accession": "PRJNA1",
            "biosample": {"accession": "SAMN00000001", "attributes": [{"name": "strain", "value": "KPN1"}]},
        },
        "organism": {"organism_name": "Klebsiella pneumoniae", "tax_id": 573, "infraspecific_names": {"strain": "KPN1"}},
        "assembly_stats": {"total_sequence_length": 5300000, "gc_percent": 57.1, "number_of_contigs": 1},
        "average_nucleotide_identity": {"taxonomy_check_status": "OK"},
        "annotation_info": {"pipeline": "PGAP", "stats": {"gene_counts": {"total": 5000, "protein_coding": 4800}}},
        "checkm_info": {"completeness": 99.1, "contamination": 0.2},
    }

    def fake_run(command, check, capture_output, text, timeout):
        assert command[:4] == ["datasets", "summary", "genome", "taxon"]
        assert command[4] == "Klebsiella pneumoniae"
        assert "--limit" in command
        return FakeCompletedProcess(json.dumps(payload) + "\n")

    monkeypatch.setattr("fetchm2.metadata.subprocess.run", fake_run)
    outdir = tmp_path / "taxon"
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetchm2",
            "metadata",
            "--taxon",
            "Klebsiella pneumoniae",
            "--outdir",
            str(outdir),
            "--offline",
            "--no-analysis",
            "--max-assemblies",
            "5",
        ],
    )
    main()
    generated_input = outdir / "metadata_output" / "ncbi_dataset.tsv"
    clean_path = outdir / "metadata_output" / "fetchm2_clean.csv"
    manifest = json.loads((outdir / "metadata_output" / "fetchm2_manifest.json").read_text())
    assert generated_input.exists()
    assert clean_path.exists()
    clean_df = pd.read_csv(clean_path)
    assert clean_df.loc[0, "Assembly Accession"] == "GCF_000001405.1"
    assert clean_df.loc[0, "Organism Name"] == "Klebsiella pneumoniae"
    assert manifest["filters_used"]["taxon_query"] == "Klebsiella pneumoniae"
    assert manifest["input_file"] == str(generated_input)


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
    assert (outdir / "metadata_output" / "sample_map.csv").exists()
    assert (outdir / "metadata_output" / "metadata_completeness.csv").exists()
    assert (outdir / "metadata_output" / "metadata_bias_warning.txt").exists()
    assert (outdir / "metadata_output" / "fetchm2_manifest.json").exists()
    assert (outdir / "metadata_output" / "ncbi_clean.csv").exists()
    assert (outdir / "metadata_output" / "fetchm2_clean_compat.csv").exists()
    df = pd.read_csv(clean_path)
    for column in [
        "Assembly Accession",
        "Assembly Name",
        "Assembly BioSample Accession",
        "Organism Name",
        "Geographic Location",
        "Continent",
        "Subcontinent",
        "Collection Date",
        "Collection_Year",
        "Host",
        "Host_SD",
        "Host_Context_SD",
        "Isolation_Source",
        "Isolation_Source_SD",
        "Sample_Type_SD",
        "Environment_Medium_SD",
    ]:
        assert column in df.columns
    assert (df["Country"].fillna("") == "Hospital").sum() == 0
    sample_map = pd.read_csv(outdir / "metadata_output" / "sample_map.csv")
    assert list(sample_map.columns) == ["sample_id", "Assembly Accession", "Assembly Name", "sequence_file"]
    assert sample_map["Assembly Accession"].astype(str).str.contains(r"\.\d+$", regex=True).all()
    assert sample_map["sequence_file"].astype(str).str.endswith(".fna").all()


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
    summary = pd.read_csv(seq_out / "sequence_download_summary.csv")
    assert list(summary.columns) == [
        "Assembly Accession",
        "Assembly Name",
        "BioSample",
        "selected_for_download",
        "download_status",
        "sequence_file",
        "failure_reason",
        "ftp_path",
    ]
    assert summary.loc[0, "selected_for_download"] in [True, "True"]
    assert str(summary.loc[0, "Assembly Accession"]).startswith("G")
    assert "." in str(summary.loc[0, "Assembly Accession"])


def test_metadata_cli_selects_representative_assemblies_by_default(tmp_path: Path, monkeypatch) -> None:
    input_path = Path(__file__).resolve().parents[1] / "test.tsv"
    outdir = tmp_path / "dedup"
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
            "--no-analysis",
        ],
    )
    main()

    clean_df = pd.read_csv(outdir / "metadata_output" / "fetchm2_clean.csv")
    all_df = pd.read_csv(outdir / "metadata_output" / "fetchm2_all_assemblies.csv")
    summary_df = pd.read_csv(outdir / "audit" / "standardization_summary.csv")
    assert len(all_df) == 200
    assert len(clean_df) == 100
    assert int(summary_df.loc[0, "rows"]) == 100
    assert clean_df["Assembly Name"].nunique() == 100
    assert clean_df["Assembly Accession"].str.startswith("GCF_").all()
    assert clean_df["Assembly Accession"].str.contains(r"\.\d+$", regex=True).all()


def test_metadata_cli_can_keep_assembly_duplicates(tmp_path: Path, monkeypatch) -> None:
    input_path = Path(__file__).resolve().parents[1] / "test.tsv"
    outdir = tmp_path / "keep_duplicates"
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
            "--no-analysis",
            "--keep-assembly-duplicates",
        ],
    )
    main()

    clean_df = pd.read_csv(outdir / "metadata_output" / "fetchm2_clean.csv")
    assert len(clean_df) == 200
    assert clean_df["Assembly Name"].nunique() == 100


def test_sequence_directory_cache_is_thread_safe(tmp_path: Path) -> None:
    cache = DirectoryCache(tmp_path / "sequence_cache.sqlite3")

    def write_and_read(index: int) -> str | None:
        accession = f"GCA_000000{index:03d}.1"
        name = f"Assembly {index}"
        directory = f"{accession}_Assembly_{index}"
        cache.set(accession, name, directory)
        return cache.get(accession, name)

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(write_and_read, range(12)))
    finally:
        cache.close()

    assert results == [f"GCA_000000{index:03d}.1_Assembly_{index}" for index in range(12)]


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
        used_esummary = any("esummary.fcgi" in url for url in calls)
        calls.clear()
        cached_result = fetch_biosample_metadata(
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
    assert used_esummary
    assert cached_result["Metadata Fetch Status"] == "ok"
    assert cached_result["Host"] == "human"
    assert calls == []
