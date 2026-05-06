from __future__ import annotations

import argparse
import os
from pathlib import Path

from . import __version__
from .analysis import generate_metadata_analysis
from .audit import production_gate, write_audit_outputs
from .metadata import run_metadata, update_pipeline_manifest_downloads
from .sequence import run_sequence_downloads


def add_filter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", nargs="+", help="Filter sequence downloads by Host_SD.")
    parser.add_argument("--host-rank", nargs="+", help="Filter sequence downloads by Host_Rank.")
    parser.add_argument("--country", nargs="+", help="Filter sequence downloads by standardized Country.")
    parser.add_argument("--continent", nargs="+", help="Filter sequence downloads by Continent.")
    parser.add_argument("--subcontinent", nargs="+", help="Filter sequence downloads by Subcontinent.")
    parser.add_argument("--sample-type", nargs="+", help="Filter by Sample_Type_SD.")
    parser.add_argument("--isolation-source", nargs="+", help="Filter by Isolation_Source_SD.")
    parser.add_argument("--environment-medium", nargs="+", help="Filter by Environment_Medium_SD.")
    parser.add_argument("--year-from", type=int, help="Minimum Collection_Year.")
    parser.add_argument("--year-to", type=int, help="Maximum Collection_Year.")
    parser.add_argument("--max-genomes", type=int, help="Maximum selected genomes for sequence download.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fetchm2",
        description="Comprehensive standalone metadata standardization and sequence download toolkit.",
    )
    parser.add_argument("--version", action="version", version=f"fetchm2 {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    metadata = subparsers.add_parser("metadata", help="Fetch/standardize metadata and write audit outputs.")
    metadata.add_argument("--input", required=True, type=Path, help="NCBI Datasets TSV/CSV input.")
    metadata.add_argument("--outdir", required=True, type=Path, help="Output directory.")
    metadata.add_argument("--ani", nargs="+", default=["all"], help="ANI Check status filter.")
    metadata.add_argument("--checkm", type=float, help="Minimum CheckM completeness.")
    metadata.add_argument("--api-key", default=os.environ.get("NCBI_API_KEY"), help="NCBI API key or NCBI_API_KEY env var.")
    metadata.add_argument("--email", default=os.environ.get("NCBI_EMAIL"), help="Optional NCBI contact email.")
    metadata.add_argument("--workers", type=int, default=3, help="Metadata fetch workers.")
    metadata.add_argument("--sleep", type=float, default=0.34, help="Delay before BioSample requests.")
    metadata.add_argument("--offline", action="store_true", help="Do not fetch BioSample metadata; standardize existing columns only.")
    metadata.add_argument("--no-analysis", action="store_true", help="Skip metadata analysis tables and figures.")
    metadata.add_argument(
        "--keep-assembly-duplicates",
        action="store_true",
        help="Keep paired GCA/GCF assembly rows in fetchm2_clean.csv instead of selecting one representative per Assembly Name.",
    )
    metadata.set_defaults(func=run_metadata_command)

    run = subparsers.add_parser("run", help="Run metadata standardization and optionally download sequences.")
    run.add_argument("--input", required=True, type=Path, help="NCBI Datasets TSV/CSV input.")
    run.add_argument("--outdir", required=True, type=Path, help="Output directory.")
    run.add_argument("--ani", nargs="+", default=["all"], help="ANI Check status filter.")
    run.add_argument("--checkm", type=float, help="Minimum CheckM completeness.")
    run.add_argument("--api-key", default=os.environ.get("NCBI_API_KEY"), help="NCBI API key or NCBI_API_KEY env var.")
    run.add_argument("--email", default=os.environ.get("NCBI_EMAIL"), help="Optional NCBI contact email.")
    run.add_argument("--workers", type=int, default=3, help="Metadata fetch workers.")
    run.add_argument("--sleep", type=float, default=0.34, help="Delay before BioSample requests.")
    run.add_argument("--offline", action="store_true", help="Do not fetch BioSample metadata; standardize existing columns only.")
    run.add_argument("--no-analysis", action="store_true", help="Skip metadata analysis tables and figures.")
    run.add_argument(
        "--keep-assembly-duplicates",
        action="store_true",
        help="Keep paired GCA/GCF assembly rows in fetchm2_clean.csv instead of selecting one representative per Assembly Name.",
    )
    run.add_argument("--download", action="store_true", help="Download sequences after metadata standardization.")
    run.add_argument("--download-workers", type=int, default=4, help="Sequence download workers.")
    run.add_argument("--retries", type=int, default=3, help="Download retries.")
    run.add_argument("--retry-delay", type=float, default=5.0, help="Download retry delay.")
    run.add_argument("--keep-gz", action="store_true", help="Keep compressed FASTA files instead of decompressing.")
    add_filter_args(run)
    run.set_defaults(func=run_all_command)

    seq = subparsers.add_parser("seq", help="Download sequences from fetchm2_clean.csv.")
    seq.add_argument("--input", required=True, type=Path, help="Path to fetchm2_clean.csv.")
    seq.add_argument("--outdir", required=True, type=Path, help="Sequence output directory.")
    seq.add_argument("--download-workers", type=int, default=4, help="Sequence download workers.")
    seq.add_argument("--retries", type=int, default=3, help="Download retries.")
    seq.add_argument("--retry-delay", type=float, default=5.0, help="Download retry delay.")
    seq.add_argument("--check-only", action="store_true", help="Audit sequence directory without downloading.")
    seq.add_argument("--keep-gz", action="store_true", help="Keep compressed FASTA files instead of decompressing.")
    add_filter_args(seq)
    seq.set_defaults(func=run_seq_command)

    audit = subparsers.add_parser("audit", help="Audit an existing standardized CSV.")
    audit.add_argument("--input", required=True, type=Path, help="Path to fetchm2_clean.csv.")
    audit.add_argument("--outdir", required=True, type=Path, help="Audit output directory.")
    audit.set_defaults(func=run_audit_command)

    validate = subparsers.add_parser("validate", help="Validate a clean metadata CSV and write production-readiness reports.")
    validate.add_argument("--input", required=True, type=Path, help="Path to fetchm2_clean.csv.")
    validate.add_argument("--outdir", required=True, type=Path, help="Validation output directory.")
    validate.set_defaults(func=run_validate_command)

    analyze = subparsers.add_parser("analyze", help="Generate metadata analysis tables and figures from a clean CSV.")
    analyze.add_argument("--input", required=True, type=Path, help="Path to fetchm2_clean.csv or another metadata CSV.")
    analyze.add_argument("--outdir", required=True, type=Path, help="Analysis output directory.")
    analyze.add_argument("--top-n", type=int, default=30, help="Top values to show in each plot.")
    analyze.set_defaults(func=run_analyze_command)
    return parser


def filter_dict(args: argparse.Namespace) -> dict[str, object]:
    return {
        "host": args.host,
        "host_rank": args.host_rank,
        "country": args.country,
        "continent": args.continent,
        "subcontinent": args.subcontinent,
        "sample_type": args.sample_type,
        "isolation_source": args.isolation_source,
        "environment_medium": args.environment_medium,
        "year_from": args.year_from,
        "year_to": args.year_to,
    }


def print_final_summary(
    summary: dict[str, object],
    *,
    clean_path: str | Path | None = None,
    analysis_dir: str | Path | None = None,
    audit_dir: str | Path | None = None,
    sequence_summary: dict[str, object] | None = None,
    production_ready: bool | None = None,
) -> None:
    total = int(summary.get("rows") or 0)

    def coverage(label: str, count_key: str, percent_key: str) -> None:
        print(f"{label}: {summary.get(count_key, 0)} / {total} ({summary.get(percent_key, 0)}%)")

    print("")
    print("FetchM2 completed.")
    print(f"Rows processed: {total}")
    print(f"Unique Assembly Accession values: {summary.get('unique_assembly_accessions', 0)}")
    if summary.get("biosample_linked_rows"):
        print(
            "BioSample-linked rows: "
            f"{summary.get('biosample_linked_rows', 0)}; "
            f"unique BioSamples represented: {summary.get('unique_biosample_accessions', 0)}"
        )
        print("BioSample fetch unit: unique BioSample accession; clean output unit: assembly row.")
    coverage("Host TaxID mapped", "host_taxid_mapped", "host_taxid_percent")
    coverage("Country present", "country_present", "country_percent")
    coverage("Collection year present", "collection_year_present", "collection_year_percent")
    coverage("Sample type present", "sample_type_present", "sample_type_percent")
    coverage("Isolation source present", "isolation_source_present", "isolation_source_percent")
    coverage("Environment medium present", "environment_medium_present", "environment_medium_percent")
    if production_ready is not None:
        print(f"Production gate: {'PASS' if production_ready else 'FAIL'}")
    if summary.get("host_review_needed"):
        print(f"Host review needed: {summary['host_review_needed']}")
    if sequence_summary:
        print(f"Sequences selected: {sequence_summary.get('selected', 0)}")
        print(f"Sequences downloaded: {sequence_summary.get('downloaded', 0)}")
        print(f"Sequences failed/missing: {sequence_summary.get('failed', sequence_summary.get('missing', 0))}")
    if clean_path:
        print(f"Clean metadata: {clean_path}")
    if analysis_dir:
        print(f"Metadata analysis: {analysis_dir}")
    if audit_dir:
        print(f"Audit/validation: {audit_dir}")


def run_metadata_command(args: argparse.Namespace) -> None:
    result = run_metadata(
        input_path=args.input,
        outdir=args.outdir,
        ani=args.ani,
        checkm=args.checkm,
        api_key=args.api_key,
        email=args.email,
        workers=args.workers,
        sleep=args.sleep,
        offline=args.offline,
        analysis=not args.no_analysis,
        keep_assembly_duplicates=args.keep_assembly_duplicates,
    )
    print(f"Wrote clean metadata: {result['clean_path']}")
    if result["analysis"]:
        print(f"Wrote metadata analysis: {result['analysis']['analysis_dir']}")
    print(f"Production gate: {'PASS' if result['production_ready'] else 'FAIL'}")
    print_final_summary(
        result["summary"],
        clean_path=result["clean_path"],
        analysis_dir=result["analysis"].get("analysis_dir") if result["analysis"] else None,
        audit_dir=args.outdir / "audit",
        production_ready=result["production_ready"],
    )


def run_all_command(args: argparse.Namespace) -> None:
    result = run_metadata(
        input_path=args.input,
        outdir=args.outdir,
        ani=args.ani,
        checkm=args.checkm,
        api_key=args.api_key,
        email=args.email,
        workers=args.workers,
        sleep=args.sleep,
        offline=args.offline,
        analysis=not args.no_analysis,
        keep_assembly_duplicates=args.keep_assembly_duplicates,
    )
    print(f"Wrote clean metadata: {result['clean_path']}")
    if result["analysis"]:
        print(f"Wrote metadata analysis: {result['analysis']['analysis_dir']}")
    print(f"Production gate: {'PASS' if result['production_ready'] else 'FAIL'}")
    sequence_summary = None
    if args.download:
        sequence_summary = run_sequence_downloads(
            input_path=Path(result["clean_path"]),
            outdir=args.outdir / "sequence",
            filters=filter_dict(args),
            retries=args.retries,
            retry_delay=args.retry_delay,
            workers=args.download_workers,
            max_genomes=args.max_genomes,
            keep_gz=args.keep_gz,
        )
        update_pipeline_manifest_downloads(
            Path(result["manifest_path"]),
            sequence_selected_count=int(sequence_summary.get("selected", 0)),
            downloaded_count=int(sequence_summary.get("downloaded", 0)),
            failed_download_count=int(sequence_summary.get("failed", 0)),
            sequence_filters_used={**filter_dict(args), "max_genomes": args.max_genomes},
        )
        print(f"Sequence summary: {sequence_summary}")
    print_final_summary(
        result["summary"],
        clean_path=result["clean_path"],
        analysis_dir=result["analysis"].get("analysis_dir") if result["analysis"] else None,
        audit_dir=args.outdir / "audit",
        sequence_summary=sequence_summary,
        production_ready=result["production_ready"],
    )


def run_seq_command(args: argparse.Namespace) -> None:
    summary = run_sequence_downloads(
        input_path=args.input,
        outdir=args.outdir,
        filters=filter_dict(args),
        retries=args.retries,
        retry_delay=args.retry_delay,
        workers=args.download_workers,
        check_only=args.check_only,
        max_genomes=args.max_genomes,
        keep_gz=args.keep_gz,
    )
    print(f"Sequence summary: {summary}")


def run_audit_command(args: argparse.Namespace) -> None:
    import pandas as pd

    rows = pd.read_csv(args.input).fillna("").to_dict(orient="records")
    summary = write_audit_outputs(rows, args.outdir)
    ready, failures, warnings = production_gate(summary)
    print(f"Production gate: {'PASS' if ready else 'FAIL'}")
    if failures:
        print(f"Hard failures: {failures}")
    if warnings:
        print(f"Warnings: {warnings}")
    print_final_summary(summary, clean_path=args.input, audit_dir=args.outdir, production_ready=ready)


def run_validate_command(args: argparse.Namespace) -> None:
    run_audit_command(args)


def run_analyze_command(args: argparse.Namespace) -> None:
    import pandas as pd

    df = pd.read_csv(args.input).fillna("")
    result = generate_metadata_analysis(df, args.outdir, top_n=args.top_n)
    print(f"Wrote metadata analysis: {result['analysis_dir']}")
    print(f"Figures generated: {result['figure_count']}")


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
