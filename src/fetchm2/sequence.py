from __future__ import annotations

import gzip
import re
import shutil
import sqlite3
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


class DirectoryCache:
    def __init__(self, path: Path) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS assembly_directory_cache (accession TEXT PRIMARY KEY, assembly_name TEXT, directory TEXT)"
        )
        self.conn.commit()

    def get(self, accession: str, name: str) -> str | None:
        row = self.conn.execute(
            "SELECT directory FROM assembly_directory_cache WHERE accession = ? AND assembly_name = ?",
            (accession, normalize_assembly_name(name)),
        ).fetchone()
        return None if row is None else str(row[0])

    def set(self, accession: str, name: str, directory: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO assembly_directory_cache (accession, assembly_name, directory) VALUES (?, ?, ?)",
            (accession, normalize_assembly_name(name), directory),
        )
        self.conn.commit()

    def close(self) -> None:
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


def download_one(row: dict[str, Any], outdir: Path, cache: DirectoryCache, retries: int, retry_delay: float, keep_gz: bool) -> tuple[str, str]:
    accession = str(row.get("Assembly Accession") or "").strip()
    name = str(row.get("Assembly Name") or "").strip()
    if not accession:
        return "", "missing accession"
    for attempt in range(1, retries + 1):
        try:
            directory = resolve_assembly_directory(accession, name, cache)
            gz_name = f"{directory}_genomic.fna.gz"
            fna_name = f"{directory}_genomic.fna"
            gz_path = outdir / gz_name
            fna_path = outdir / fna_name
            if fna_path.exists() or gz_path.exists():
                return accession, "exists"
            url = f"{build_parent_url(accession)}/{directory}/{gz_name}"
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
            return accession, "downloaded"
        except Exception as exc:
            if attempt >= retries:
                return accession, f"failed: {exc}"
            import time

            time.sleep(retry_delay * attempt)
    return accession, "failed"


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
        return {"selected": len(rows), "missing": len(missing), "downloaded": 0, "failed": len(missing)}
    cache = DirectoryCache(outdir / "fetchm2_sequence_cache.sqlite3")
    results: list[tuple[str, str]] = []
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
    failed = [accession for accession, status in results if status.startswith("failed") or status == "missing accession"]
    (outdir / "failed_accessions.txt").write_text("\n".join(failed) + ("\n" if failed else ""), encoding="utf-8")
    summary = {
        "selected": len(rows),
        "downloaded": sum(1 for _, status in results if status == "downloaded"),
        "existing": sum(1 for _, status in results if status == "exists"),
        "failed": len(failed),
    }
    pd.DataFrame([{"assembly_accession": accession, "status": status} for accession, status in results]).to_csv(
        outdir / "sequence_download_summary.csv", index=False
    )
    return summary
