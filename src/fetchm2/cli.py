from __future__ import annotations

import argparse
import os
from pathlib import Path

from . import __version__
from .audit import production_gate, summarize_rows, write_audit_outputs
from .metadata import run_metadata
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
    )
    print(f"Wrote clean metadata: {result['clean_path']}")
    print(f"Production gate: {'PASS' if result['production_ready'] else 'FAIL'}")


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
    )
    print(f"Wrote clean metadata: {result['clean_path']}")
    if args.download:
        summary = run_sequence_downloads(
            input_path=Path(result["clean_path"]),
            outdir=args.outdir / "sequence",
            filters=filter_dict(args),
            retries=args.retries,
            retry_delay=args.retry_delay,
            workers=args.download_workers,
            max_genomes=args.max_genomes,
            keep_gz=args.keep_gz,
        )
        print(f"Sequence summary: {summary}")


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


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
