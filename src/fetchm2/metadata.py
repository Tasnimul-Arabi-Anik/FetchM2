from __future__ import annotations

import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import xmltodict
from tqdm import tqdm

from .audit import production_gate, write_audit_outputs
from .standardization import standardize_rows

NCBI_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
NCBI_TIMEOUT = 60


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_csv(path, sep="\t")


def filter_quality(df: pd.DataFrame, ani: list[str] | None, checkm: float | None) -> pd.DataFrame:
    filtered = df.copy()
    if ani and "all" not in [value.lower() for value in ani] and "ANI Check status" in filtered:
        filtered = filtered[filtered["ANI Check status"].astype(str).isin(ani)]
    if checkm is not None and "CheckM completeness" in filtered:
        filtered = filtered[pd.to_numeric(filtered["CheckM completeness"], errors="coerce") >= checkm]
    return filtered


class MetadataCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS biosample_cache (
                biosample TEXT PRIMARY KEY,
                payload TEXT,
                fetched_at REAL
            )
            """
        )
        self.conn.commit()

    def get(self, biosample: str) -> str | None:
        with self.lock:
            row = self.conn.execute("SELECT payload FROM biosample_cache WHERE biosample = ?", (biosample,)).fetchone()
        return None if row is None else str(row[0])

    def set(self, biosample: str, payload: str) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO biosample_cache (biosample, payload, fetched_at) VALUES (?, ?, ?)",
                (biosample, payload, time.time()),
            )
            self.conn.commit()

    def close(self) -> None:
        with self.lock:
            self.conn.close()


def biosample_accession(row: dict[str, Any]) -> str:
    for key in ["Assembly BioSample Accession", "BioSample Accession", "BioSample"]:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def parse_biosample_xml(xml_text: str) -> dict[str, str]:
    if not xml_text.strip():
        return {}
    parsed = xmltodict.parse(xml_text)
    sample = parsed.get("BioSampleSet", {}).get("BioSample")
    if isinstance(sample, list):
        sample = sample[0] if sample else {}
    if not isinstance(sample, dict):
        return {}
    attributes = sample.get("Attributes", {}).get("Attribute", [])
    if isinstance(attributes, dict):
        attributes = [attributes]
    output: dict[str, str] = {}
    key_map = {
        "isolation_source": "Isolation Source",
        "collection_date": "Collection Date",
        "geo_loc_name": "Geographic Location",
        "host": "Host",
        "sample_type": "Sample Type",
        "env_medium": "Environment Medium",
        "env_broad_scale": "Environment Broad Scale",
        "env_local_scale": "Environment Local Scale",
        "disease": "Host Disease",
        "host_disease": "Host Disease",
        "host_health_state": "Host Health State",
    }
    for attr in attributes:
        name = str(attr.get("@attribute_name") or attr.get("@harmonized_name") or "").strip()
        value = str(attr.get("#text") or "").strip()
        if not name or not value:
            continue
        normalized_name = name.lower().replace("-", "_").replace(" ", "_")
        output[key_map.get(normalized_name, name)] = value
    return output


def fetch_biosample_metadata(
    biosample: str,
    *,
    api_key: str | None,
    email: str | None,
    sleep: float,
    cache: MetadataCache,
) -> dict[str, str]:
    cached = cache.get(biosample)
    if cached is not None:
        return parse_biosample_xml(cached)
    params = {
        "db": "biosample",
        "id": biosample,
        "retmode": "xml",
    }
    if api_key:
        params["api_key"] = api_key
    if email:
        params["email"] = email
    if sleep > 0:
        time.sleep(sleep)
    response = requests.get(NCBI_EFETCH_URL, params=params, timeout=NCBI_TIMEOUT)
    response.raise_for_status()
    cache.set(biosample, response.text)
    return parse_biosample_xml(response.text)


def enrich_rows_with_biosample(
    rows: list[dict[str, Any]],
    *,
    cache_path: Path,
    api_key: str | None,
    email: str | None,
    workers: int,
    sleep: float,
    offline: bool,
) -> list[dict[str, Any]]:
    if offline:
        return rows
    cache = MetadataCache(cache_path)
    try:
        accessions = sorted({biosample_accession(row) for row in rows if biosample_accession(row)})
        metadata_by_biosample: dict[str, dict[str, str]] = {}
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = {
                executor.submit(
                    fetch_biosample_metadata,
                    biosample,
                    api_key=api_key,
                    email=email,
                    sleep=sleep,
                    cache=cache,
                ): biosample
                for biosample in accessions
            }
            for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching BioSample metadata"):
                biosample = futures[future]
                try:
                    metadata_by_biosample[biosample] = future.result()
                except Exception as exc:
                    metadata_by_biosample[biosample] = {"Metadata Fetch Error": str(exc)}
        enriched = []
        for row in rows:
            merged = dict(row)
            for key, value in metadata_by_biosample.get(biosample_accession(row), {}).items():
                if not str(merged.get(key) or "").strip():
                    merged[key] = value
            enriched.append(merged)
        return enriched
    finally:
        cache.close()


def run_metadata(
    *,
    input_path: Path,
    outdir: Path,
    ani: list[str] | None = None,
    checkm: float | None = None,
    api_key: str | None = None,
    email: str | None = None,
    workers: int = 3,
    sleep: float = 0.34,
    offline: bool = False,
) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    metadata_dir = outdir / "metadata_output"
    audit_dir = outdir / "audit"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    df = read_table(input_path)
    df = filter_quality(df, ani, checkm)
    rows = df.fillna("").to_dict(orient="records")
    rows = enrich_rows_with_biosample(
        rows,
        cache_path=metadata_dir / "fetchm2_biosample_cache.sqlite3",
        api_key=api_key,
        email=email,
        workers=workers,
        sleep=sleep,
        offline=offline,
    )
    standardized = standardize_rows(rows)
    clean_df = pd.DataFrame(standardized)
    clean_path = metadata_dir / "fetchm2_clean.csv"
    clean_df.to_csv(clean_path, index=False)
    clean_df.to_csv(metadata_dir / "fetchm2_clean.tsv", sep="\t", index=False)
    summary = write_audit_outputs(standardized, audit_dir)
    production_ready, hard_failures, warnings = production_gate(summary)
    report_lines = [
        "# FetchM2 Run Report",
        "",
        f"Input: {input_path}",
        f"Rows processed: {summary['rows']}",
        f"Clean table: {clean_path}",
        f"Production gate: {'PASS' if production_ready else 'FAIL'}",
    ]
    if hard_failures:
        report_lines.append(f"Hard failures: {', '.join(hard_failures)}")
    if warnings:
        report_lines.append(f"Warnings: {', '.join(warnings)}")
    (metadata_dir / "fetchm2_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return {
        "clean_path": str(clean_path),
        "summary": summary,
        "production_ready": production_ready,
        "hard_failures": hard_failures,
        "warnings": warnings,
    }
