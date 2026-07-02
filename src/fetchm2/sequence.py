from __future__ import annotations

import gzip
import hashlib
import json
import random
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
ACCESSION_RE = re.compile(r"^(?:GCA|GCF)_\d{9}(?:\.\d+)?$")
ACCESSION_TOKEN_RE = re.compile(r"[\s,;]+")
MANUAL_ACCESSION_LIMIT = 10_000
MANUAL_ACCESSION_TEXT_LIMIT = 1_048_576


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_accession(value: Any) -> str:
    return str(value or "").strip().upper()


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


def read_rows(input_path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(input_path)
    return df.fillna("").to_dict(orient="records")


def split_manual_accessions(accession_text: str = "", accession_files: list[Path] | None = None) -> dict[str, Any]:
    parts: list[str] = []
    text_bytes = len(accession_text.encode("utf-8"))
    if text_bytes > MANUAL_ACCESSION_TEXT_LIMIT:
        return {
            "accessions": [],
            "duplicates": 0,
            "invalid": [],
            "submitted": 0,
            "error": f"Manual accession input is {text_bytes:,} bytes; limit is {MANUAL_ACCESSION_TEXT_LIMIT:,} bytes.",
        }
    if accession_text:
        parts.extend(token for token in ACCESSION_TOKEN_RE.split(accession_text.strip()) if token)
    for file_path in accession_files or []:
        file_text = file_path.read_text(encoding="utf-8")
        text_bytes += len(file_text.encode("utf-8"))
        if text_bytes > MANUAL_ACCESSION_TEXT_LIMIT:
            return {
                "accessions": [],
                "duplicates": 0,
                "invalid": [],
                "submitted": len(parts),
                "error": f"Manual accession input exceeds {MANUAL_ACCESSION_TEXT_LIMIT:,} bytes across text and files.",
            }
        parts.extend(token for token in ACCESSION_TOKEN_RE.split(file_text.strip()) if token)

    seen: set[str] = set()
    accessions: list[str] = []
    invalid: list[str] = []
    duplicates = 0
    for token in parts:
        accession = normalize_accession(token)
        if not ACCESSION_RE.fullmatch(accession):
            invalid.append(token)
            continue
        if accession in seen:
            duplicates += 1
            continue
        seen.add(accession)
        accessions.append(accession)
        if len(accessions) > MANUAL_ACCESSION_LIMIT:
            return {
                "accessions": accessions,
                "duplicates": duplicates,
                "invalid": invalid,
                "submitted": len(parts),
                "error": f"Manual accession selection exceeds {MANUAL_ACCESSION_LIMIT:,} unique accessions.",
            }
    return {
        "accessions": accessions,
        "duplicates": duplicates,
        "invalid": invalid,
        "submitted": len(parts),
        "error": "",
    }


def apply_sequence_subset(
    rows: list[dict[str, Any]],
    *,
    subset_mode: str = "all",
    subset_count: int | None = None,
    subset_seed: int | None = None,
    manual_accessions: str = "",
    manual_accession_files: list[Path] | None = None,
    max_genomes: int | None = None,
) -> dict[str, Any]:
    mode = (subset_mode or "all").strip().lower()
    if mode not in {"all", "random", "manual"}:
        return {"rows": [], "metadata": {"error": f"Unsupported subset mode: {subset_mode}"}}
    if max_genomes is not None and max_genomes <= 0:
        return {"rows": [], "metadata": {"error": "--max-genomes must be a positive integer."}}
    if mode != "all" and max_genomes is not None:
        return {"rows": [], "metadata": {"error": "--max-genomes is only compatible with --subset-mode all."}}

    matched_total = len(rows)
    metadata: dict[str, Any] = {
        "mode": mode,
        "matched_row_total": matched_total,
        "selected_row_total": 0,
        "selected_accession_total": 0,
        "requested_count": subset_count,
        "random_seed": subset_seed,
        "random_request_exceeds_matches": False,
        "manual_submitted_total": 0,
        "manual_duplicate_total": 0,
        "manual_invalid_total": 0,
        "manual_missing_total": 0,
        "manual_missing_accessions": [],
        "error": "",
    }

    if mode == "all":
        selected = list(rows)
        if max_genomes is not None:
            selected = selected[:max_genomes]
            metadata["requested_count"] = max_genomes
    elif mode == "random":
        if subset_count is None or subset_count <= 0:
            metadata["error"] = "--subset-count must be a positive integer for --subset-mode random."
            return {"rows": [], "metadata": metadata}
        sorted_rows = sorted(rows, key=lambda row: normalize_accession(row.get("Assembly Accession")))
        if subset_count >= len(sorted_rows):
            selected = sorted_rows
            metadata["random_request_exceeds_matches"] = subset_count > len(sorted_rows)
        else:
            selected = random.Random(subset_seed).sample(sorted_rows, subset_count)
    else:
        parsed = split_manual_accessions(manual_accessions, manual_accession_files)
        metadata["manual_submitted_total"] = parsed["submitted"]
        metadata["manual_duplicate_total"] = parsed["duplicates"]
        metadata["manual_invalid_total"] = len(parsed["invalid"])
        if parsed["error"]:
            metadata["error"] = parsed["error"]
            return {"rows": [], "metadata": metadata}
        if parsed["invalid"]:
            metadata["error"] = "Malformed manual accession token(s): " + ", ".join(parsed["invalid"][:20])
            return {"rows": [], "metadata": metadata}
        if not parsed["accessions"]:
            metadata["error"] = "--subset-mode manual requires --accessions or --accessions-file."
            return {"rows": [], "metadata": metadata}
        rows_by_accession = {normalize_accession(row.get("Assembly Accession")): row for row in rows}
        selected = []
        missing = []
        for accession in parsed["accessions"]:
            row = rows_by_accession.get(accession)
            if row is None:
                missing.append(accession)
                continue
            selected.append(row)
        metadata["manual_missing_total"] = len(missing)
        metadata["manual_missing_accessions"] = missing[:200]
        if not selected:
            metadata["error"] = "Manual accession selection matched zero rows after filters."
            return {"rows": [], "metadata": metadata}

    selected_accessions = [normalize_accession(row.get("Assembly Accession")) for row in selected if normalize_accession(row.get("Assembly Accession"))]
    metadata["selected_row_total"] = len(selected)
    metadata["selected_accession_total"] = len(selected_accessions)
    return {"rows": selected, "metadata": metadata}


def selected_accession_manifest(outdir: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    accessions = [normalize_accession(row.get("Assembly Accession")) for row in rows if normalize_accession(row.get("Assembly Accession"))]
    path = outdir / "selected_accessions.txt"
    text = "\n".join(accessions) + ("\n" if accessions else "")
    path.write_text(text, encoding="utf-8")
    return {
        "selected_accessions_manifest_path": path.name,
        "selected_accessions_manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def select_rows(
    input_path: Path,
    filters: dict[str, Any],
    max_genomes: int | None,
    *,
    subset_mode: str = "all",
    subset_count: int | None = None,
    subset_seed: int | None = None,
    manual_accessions: str = "",
    manual_accession_files: list[Path] | None = None,
) -> dict[str, Any]:
    matched_rows = [row for row in read_rows(input_path) if row_matches_filters(row, filters)]
    return apply_sequence_subset(
        matched_rows,
        subset_mode=subset_mode,
        subset_count=subset_count,
        subset_seed=subset_seed,
        manual_accessions=manual_accessions,
        manual_accession_files=manual_accession_files,
        max_genomes=max_genomes,
    )


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
    subset_mode: str = "all",
    subset_count: int | None = None,
    subset_seed: int | None = None,
    manual_accessions: str = "",
    manual_accession_files: list[Path] | None = None,
) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    filters = filters or {}
    selection = select_rows(
        input_path,
        filters,
        max_genomes,
        subset_mode=subset_mode,
        subset_count=subset_count,
        subset_seed=subset_seed,
        manual_accessions=manual_accessions,
        manual_accession_files=manual_accession_files,
    )
    rows = selection["rows"]
    subset_metadata = selection["metadata"]
    if subset_metadata.get("error"):
        raise ValueError(str(subset_metadata["error"]))
    subset_metadata.update(selected_accession_manifest(outdir, rows))
    (outdir / "sequence_selection_summary.json").write_text(
        json.dumps(subset_metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
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
        return {"selected": len(rows), "missing": len(missing), "downloaded": 0, "failed": len(missing), "subset": subset_metadata}
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
        "subset": subset_metadata,
    }
    pd.DataFrame(results).to_csv(outdir / "sequence_download_summary.csv", index=False)
    return summary
