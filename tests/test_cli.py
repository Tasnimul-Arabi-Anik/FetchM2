from __future__ import annotations

from pathlib import Path

import pandas as pd

from fetchm2.cli import main


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
    assert (outdir / "metadata_analysis" / "metadata_analysis_report.md").exists()
    assert (outdir / "metadata_analysis" / "tables" / "field_coverage_summary.csv").exists()
    assert (outdir / "metadata_analysis" / "tables" / "top_values_by_field.csv").exists()
    df = pd.read_csv(clean_path)
    assert "Host_SD" in df.columns
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
