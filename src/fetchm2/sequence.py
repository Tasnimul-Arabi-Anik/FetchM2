from __future__ import annotations

import gzip
import re
import shutil
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from tqdm import tqdm

BASE_URL = "https://ftp.ncbi.nlm.nih.gov/genomes/all"


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_assembly_name(name: str) -> str:
    cleaned = str(name or "").strip()
    return cleaned.replace(" ", "_") if cleaned else "NA"


def build_parent_url(accession: str) -> str:
    prefix, digits = accession.split("_", 1)
    core = digits.split(".", 1)[0]
    return f"{BASE_URL}/{prefix}/{core[:3]}/{core[3:6]}/{core[6:9]}/{core[9:]}"


def biosample_value(row: dict[str, Any]) -> str:
    for column in ["Assembly BioSample Accession", "BioSample", "BioSample Accession"]:
        value = str(row.get(column) or "").strip()
        if value:
            return value
    return ""


def expected_directory_name(row: dict[str, Any]) -> str:
    accession = str(row.get("Assembly Accession") or "").strip()
    name = str(row.get("Assembly Name") or "").strip()
    return f"{accession}_{normalize_assembly_name(name)}" if accession else ""


def expected_sequence_file(row: dict[str, Any], *, keep_gz: bool = False) -> str:
    directory = expected_directory_name(row)
    if not directory:
        return ""
    suffix = ".fna.gz" if keep_gz else ".fna"
    return f"{directory}_genomic{suffix}"


def expected_ftp_path(row: dict[str, Any]) -> str:
    accession = str(row.get("Assembly Accession") or "").strip()
    directory = expected_directory_name(row)
    if not accession or not directory or "_" not in accession:
        return ""
    return f"{build_parent_url(accession)}/{directory}/{directory}_genomic.fna.gz"


def sequence_summary_row(
    row: dict[str, Any],
    *,
    selected_for_download: bool,
    download_status: str,
    sequence_file: str = "",
    failure_reason: str = "",
    ftp_path: str = "",
) -> dict[str, Any]:
    return {
        "Assembly Accession": str(row.get("Assembly Accession") or "").strip(),
        "Assembly Name": str(row.get("Assembly Name") or "").strip(),
        "BioSample": biosample_value(row),
        "selected_for_download": bool(selected_for_download),
        "download_status": download_status,
        "sequence_file": sequence_file or expected_sequence_file(row),
        "failure_reason": failure_reason,
        "ftp_path": ftp_path or expected_ftp_path(row),
    }


class DirectoryCache:
    def __init__(self, path: Path) -> None:
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS assembly_directory_cache (accession TEXT PRIMARY KEY, assembly_name TEXT, directory TEXT)"
        )
        self.conn.commit()

    def get(self, accession: str, name: str) -> str | None:
        with self.lock:
            row = self.conn.execute(
                "SELECT directory FROM assembly_directory_cache WHERE accession = ? AND assembly_name = ?",
                (accession, normalize_assembly_name(name)),
            ).fetchone()
        return None if row is None else str(row[0])

    def set(self, accession: str, name: str, directory: str) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO assembly_directory_cache (accession, assembly_name, directory) VALUES (?, ?, ?)",
                (accession, normalize_assembly_name(name), directory),
            )
            self.conn.commit()

    def close(self) -> None:
        with self.lock:
            self.conn.close()


def resolve_assembly_directory(accession: str, name: str, cache: DirectoryCache) -> str:
    cached = cache.get(accession, name)
    if cached:
        return cached
    parent_url = build_parent_url(accession)
    normalized_name = normalize_assembly_name(name)
    candidates = [f"{accession}_{normalized_name}", f"{accession}_NA"]
    session = requests.Session()
    for candidate in candidates:
        if session.get(f"{parent_url}/{candidate}", timeout=30).ok:
            cache.set(accession, name, candidate)
            return candidate
    response = session.get(parent_url, timeout=60)
    response.raise_for_status()
    matches = [item.rstrip("/") for item in re.findall(r'href="([^"]+/)"', response.text) if item.startswith(f"{accession}_")]
    if not matches:
        raise FileNotFoundError(f"No remote assembly directory found for {accession}")
    cache.set(accession, name, matches[0])
    return matches[0]


def row_matches_filters(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    for field, values in {
        "Country": filters.get("country"),
        "Continent": filters.get("continent"),
        "Subcontinent": filters.get("subcontinent"),
        "Host_SD": filters.get("host"),
        "Host_Rank": filters.get("host_rank"),
        "Sample_Type_SD": filters.get("sample_type"),
        "Isolation_Source_SD": filters.get("isolation_source"),
        "Environment_Medium_SD": filters.get("environment_medium"),
    }.items():
        if values and normalize_text(row.get(field)) not in {normalize_text(value) for value in values}:
            return False
    year_from = filters.get("year_from")
    year_to = filters.get("year_to")
    if year_from is not None or year_to is not None:
        try:
            year = int(str(row.get("Collection_Year") or row.get("Collection Date") or "")[:4])
        except ValueError:
            return False
        if year_from is not None and year < year_from:
            return False
        if year_to is not None and year > year_to:
            return False
    return True


def select_rows(input_path: Path, filters: dict[str, Any], max_genomes: int | None) -> list[dict[str, Any]]:
    df = pd.read_csv(input_path)
    rows = [row for row in df.fillna("").to_dict(orient="records") if row_matches_filters(row, filters)]
    if max_genomes is not None:
        rows = rows[:max_genomes]
    return rows


def download_one(
    row: dict[str, Any],
    outdir: Path,
    cache: DirectoryCache,
    retries: int,
    retry_delay: float,
    keep_gz: bool,
) -> dict[str, Any]:
    accession = str(row.get("Assembly Accession") or "").strip()
    name = str(row.get("Assembly Name") or "").strip()
    if not accession:
        return sequence_summary_row(
            row,
            selected_for_download=True,
            download_status="failed",
            failure_reason="missing accession",
        )
    for attempt in range(1, retries + 1):
        try:
            directory = resolve_assembly_directory(accession, name, cache)
            gz_name = f"{directory}_genomic.fna.gz"
            fna_name = f"{directory}_genomic.fna"
            gz_path = outdir / gz_name
            fna_path = outdir / fna_name
            url = f"{build_parent_url(accession)}/{directory}/{gz_name}"
            if fna_path.exists() or gz_path.exists():
                return sequence_summary_row(
                    row,
                    selected_for_download=True,
                    download_status="exists",
                    sequence_file=fna_name if fna_path.exists() else gz_name,
                    ftp_path=url,
                )
            with requests.get(url, stream=True, timeout=300) as response:
                response.raise_for_status()
                with gz_path.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
            if not keep_gz:
                with gzip.open(gz_path, "rb") as source, fna_path.open("wb") as target:
                    shutil.copyfileobj(source, target)
                gz_path.unlink()
            return sequence_summary_row(
                row,
                selected_for_download=True,
                download_status="downloaded",
                sequence_file=gz_name if keep_gz else fna_name,
                ftp_path=url,
            )
        except Exception as exc:
            if attempt >= retries:
                return sequence_summary_row(
                    row,
                    selected_for_download=True,
                    download_status="failed",
                    failure_reason=str(exc),
                )
            import time

            time.sleep(retry_delay * attempt)
    return sequence_summary_row(row, selected_for_download=True, download_status="failed", failure_reason="failed")


def run_sequence_downloads(
    *,
    input_path: Path,
    outdir: Path,
    filters: dict[str, Any] | None = None,
    retries: int = 3,
    retry_delay: float = 5.0,
    workers: int = 4,
    check_only: bool = False,
    max_genomes: int | None = None,
    keep_gz: bool = False,
) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    filters = filters or {}
    rows = select_rows(input_path, filters, max_genomes)
    expected = [str(row.get("Assembly Accession") or "").strip() for row in rows]
    if check_only:
        existing = {path.name.split("_", 2)[0] + "_" + path.name.split("_", 2)[1] for path in outdir.glob("*_genomic.fna*")}
        missing = [accession for accession in expected if accession not in existing]
        (outdir / "failed_accessions.txt").write_text("\n".join(missing) + ("\n" if missing else ""), encoding="utf-8")
        pd.DataFrame(
            [
                sequence_summary_row(
                    row,
                    selected_for_download=True,
                    download_status="exists" if str(row.get("Assembly Accession") or "").strip() in existing else "missing",
                    failure_reason=""
                    if str(row.get("Assembly Accession") or "").strip() in existing
                    else "missing local sequence file",
                )
                for row in rows
            ]
        ).to_csv(outdir / "sequence_download_summary.csv", index=False)
        return {"selected": len(rows), "missing": len(missing), "downloaded": 0, "failed": len(missing)}
    cache = DirectoryCache(outdir / "fetchm2_sequence_cache.sqlite3")
    results: list[dict[str, Any]] = []
    try:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = [
                executor.submit(download_one, row, outdir, cache, retries, retry_delay, keep_gz)
                for row in rows
            ]
            for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading FASTA"):
                results.append(future.result())
    finally:
        cache.close()
    failed = [
        str(result.get("Assembly Accession") or "").strip()
        for result in results
        if result.get("download_status") == "failed"
    ]
    (outdir / "failed_accessions.txt").write_text("\n".join(failed) + ("\n" if failed else ""), encoding="utf-8")
    summary = {
        "selected": len(rows),
        "downloaded": sum(1 for result in results if result.get("download_status") == "downloaded"),
        "existing": sum(1 for result in results if result.get("download_status") == "exists"),
        "failed": len(failed),
    }
    pd.DataFrame(results).to_csv(outdir / "sequence_download_summary.csv", index=False)
    return summary
