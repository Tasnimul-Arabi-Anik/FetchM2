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

from .analysis import generate_metadata_analysis
from .audit import production_gate, write_audit_outputs
from .standardization import standardize_rows

NCBI_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
NCBI_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
NCBI_TIMEOUT = 60
DEFAULT_FETCH_RETRIES = 4
DEFAULT_RETRY_BACKOFF = 1.5
FALLBACK_CACHE_XML_KEY = "_FetchM2_Cache_XML"

ATTRIBUTE_KEY_MAP = {
    "isolation_source": "Isolation Source",
    "isolation-source": "Isolation Source",
    "isolation source": "Isolation Source",
    "source_of_isolation": "Isolation Source",
    "source type": "Isolation Source",
    "source material id": "Isolation Source",
    "source mat id": "Isolation Source",
    "env material": "Isolation Source",
    "environment material": "Isolation Source",
    "sample_type": "Sample Type",
    "sample type": "Sample Type",
    "specimen": "Sample Type",
    "package": "Sample Type",
    "env package": "Sample Type",
    "collection_date": "Collection Date",
    "collection-date": "Collection Date",
    "collection date": "Collection Date",
    "collection timestamp": "Collection Date",
    "colection date": "Collection Date",
    "collection date remark": "Collection Date",
    "sampling event date time start": "Collection Date",
    "date host collection": "Collection Date",
    "harvest date": "Collection Date",
    "specimen collection date": "Collection Date",
    "dna isolation date": "Collection Date",
    "sample_collection_date": "Collection Date",
    "date_of_collection": "Collection Date",
    "isolation_date": "Collection Date",
    "geo_loc_name": "Geographic Location",
    "geo-loc-name": "Geographic Location",
    "geo_loc name": "Geographic Location",
    "geographic_location": "Geographic Location",
    "geographic location": "Geographic Location",
    "geographic_location_region_and_locality": "Geographic Location",
    "geographic location country and or sea": "Geographic Location",
    "geographic location country and or sea region": "Geographic Location",
    "country": "Geographic Location",
    "host": "Host",
    "host_scientific_name": "Host",
    "host scientific name": "Host",
    "host_common_name": "Host",
    "host common name": "Host",
    "specific_host": "Host",
    "specific host": "Host",
    "nat host": "Host",
    "lab host": "Host",
    "env_medium": "Environment Medium",
    "environmental medium": "Environment Medium",
    "environment material": "Environment Medium",
    "material": "Environment Medium",
    "environment": "Environment Medium",
    "env_broad_scale": "Environment Broad Scale",
    "broad-scale environmental context": "Environment Broad Scale",
    "environment biome": "Environment Broad Scale",
    "env biome": "Environment Broad Scale",
    "biome": "Environment Broad Scale",
    "metagenome source": "Environment Broad Scale",
    "env_local_scale": "Environment Local Scale",
    "local-scale environmental context": "Environment Local Scale",
    "environment feature": "Environment Local Scale",
    "env feature": "Environment Local Scale",
    "feature": "Environment Local Scale",
    "coll site geo feat": "Environment Local Scale",
    "isolation_site": "Isolation Site",
    "isolation site": "Isolation Site",
    "body site": "Isolation Site",
    "anatomical site": "Isolation Site",
    "organism part": "Isolation Site",
    "tissue": "Isolation Site",
    "host tissue sampled": "Isolation Site",
    "disease": "Host Disease",
    "host_disease": "Host Disease",
    "host disease": "Host Disease",
    "diseases": "Host Disease",
    "study disease": "Host Disease",
    "ifsac category": "Host Disease",
    "host_health_state": "Host Health State",
    "host health state": "Host Health State",
    "health state": "Host Health State",
}

ISOLATION_SOURCE_FALLBACK_FIELDS = {
    "Sample Type",
    "Environment Medium",
    "Environment Broad Scale",
    "Environment Local Scale",
    "Isolation Site",
}


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


def select_representative_assemblies(df: pd.DataFrame) -> pd.DataFrame:
    if "Assembly Name" not in df.columns or "Assembly Accession" not in df.columns:
        return df.copy()

    working = df.copy()
    working["_fetchm2_original_order"] = range(len(working))
    assembly_name = working["Assembly Name"].fillna("").astype(str).str.strip()
    with_name = working[assembly_name != ""].copy()
    without_name = working[assembly_name == ""].copy()
    if not with_name.empty:
        with_name["_fetchm2_gcf_priority"] = (
            with_name["Assembly Accession"].fillna("").astype(str).str.startswith("GCF_").astype(int)
        )
        with_name = (
            with_name.sort_values(
                by=["Assembly Name", "_fetchm2_gcf_priority", "_fetchm2_original_order"],
                ascending=[True, False, True],
            )
            .drop_duplicates(subset=["Assembly Name"], keep="first")
        )
    selected = pd.concat([with_name, without_name], ignore_index=True)
    selected = selected.sort_values("_fetchm2_original_order")
    return selected.drop(columns=["_fetchm2_original_order", "_fetchm2_gcf_priority"], errors="ignore").reset_index(drop=True)


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


class RequestRateLimiter:
    def __init__(self, interval_seconds: float) -> None:
        self.interval_seconds = max(0.0, interval_seconds)
        self.lock = threading.Lock()
        self.next_allowed = 0.0

    def wait(self) -> None:
        if self.interval_seconds <= 0:
            return
        with self.lock:
            now = time.monotonic()
            wait_seconds = max(0.0, self.next_allowed - now)
            self.next_allowed = max(now, self.next_allowed) + self.interval_seconds
        if wait_seconds > 0:
            time.sleep(wait_seconds)

    def penalize(self, multiplier: float = 2.0) -> None:
        with self.lock:
            self.next_allowed = max(self.next_allowed, time.monotonic()) + self.interval_seconds * multiplier


def biosample_accession(row: dict[str, Any]) -> str:
    for key in ["Assembly BioSample Accession", "BioSample Accession", "BioSample"]:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def ncbi_params(api_key: str | None, email: str | None, **kwargs: Any) -> dict[str, Any]:
    params = {"tool": "fetchm2", **kwargs}
    if api_key:
        params["api_key"] = api_key
    if email:
        params["email"] = email
    return params


def normalize_attribute_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def biosample_node(parsed: dict[str, Any]) -> dict[str, Any]:
    sample = parsed.get("BioSample")
    if sample is None:
        sample_set = parsed.get("BioSampleSet") or {}
        sample = sample_set.get("BioSample") if isinstance(sample_set, dict) else {}
    if isinstance(sample, list):
        sample = sample[0] if sample else {}
    return sample if isinstance(sample, dict) else {}


def request_with_retries(
    url: str,
    *,
    params: dict[str, Any],
    rate_limiter: RequestRateLimiter,
) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, DEFAULT_FETCH_RETRIES + 1):
        rate_limiter.wait()
        try:
            response = requests.get(url, params=params, timeout=NCBI_TIMEOUT)
            if response.status_code == 429 or response.status_code >= 500:
                last_error = requests.HTTPError(f"{response.status_code} response from NCBI")
                rate_limiter.penalize(multiplier=attempt + 1)
                time.sleep(DEFAULT_RETRY_BACKOFF * attempt)
                continue
            response.raise_for_status()
            return response
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            last_error = exc
            rate_limiter.penalize(multiplier=attempt + 1)
            if attempt < DEFAULT_FETCH_RETRIES:
                time.sleep(DEFAULT_RETRY_BACKOFF * attempt)
                continue
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("NCBI request failed without response")


def attribute_list(sample: dict[str, Any]) -> list[dict[str, Any]]:
    attributes_node = sample.get("Attributes") or {}
    if not isinstance(attributes_node, dict):
        return []
    attributes = attributes_node.get("Attribute", [])
    if isinstance(attributes, dict):
        attributes = [attributes]
    return [attr for attr in attributes if isinstance(attr, dict)]


def taxonomy_name_from_sample(sample: dict[str, Any]) -> str:
    description = sample.get("Description") or {}
    if not isinstance(description, dict):
        return ""
    organism = description.get("Organism") or {}
    if isinstance(organism, dict):
        return str(organism.get("@taxonomy_name") or organism.get("OrganismName") or "").strip()
    return ""


def parse_biosample_xml(xml_text: str) -> dict[str, str]:
    if not xml_text.strip():
        return {"Metadata Fetch Status": "source_missing", "Metadata Fetch Reason": "empty_payload"}
    parsed = xmltodict.parse(xml_text)
    sample = biosample_node(parsed)
    if not sample:
        return {"Metadata Fetch Status": "source_missing", "Metadata Fetch Reason": "no_biosample"}
    attributes = attribute_list(sample)
    output: dict[str, str] = {}
    raw_names: list[str] = []
    matched_names: dict[str, list[str]] = {
        "Isolation Source": [],
        "Collection Date": [],
        "Geographic Location": [],
        "Host": [],
        "Sample Type": [],
        "Environment Medium": [],
        "Environment Broad Scale": [],
        "Environment Local Scale": [],
        "Isolation Site": [],
        "Host Disease": [],
        "Host Health State": [],
    }
    isolation_source_fallback = ""
    isolation_source_fallback_name = ""
    for attr in attributes:
        names = [
            str(attr.get("@attribute_name") or "").strip(),
            str(attr.get("@harmonized_name") or "").strip(),
            str(attr.get("@display_name") or "").strip(),
        ]
        value = str(attr.get("#text") or "").strip()
        raw_names.extend(name for name in names if name)
        if not value:
            continue
        destination = ""
        matched_name = ""
        for name in names:
            for key_variant in {name, normalize_attribute_key(name), normalize_attribute_key(name).replace("_", " ")}:
                destination = ATTRIBUTE_KEY_MAP.get(key_variant)
                if destination:
                    matched_name = name
                    break
            if destination:
                break
        if not destination:
            continue
        if destination == "Isolation Source":
            if not output.get(destination):
                output[destination] = value
                matched_names[destination].append(matched_name)
            continue
        if destination in ISOLATION_SOURCE_FALLBACK_FIELDS and not isolation_source_fallback:
            isolation_source_fallback = value
            isolation_source_fallback_name = matched_name
        if not output.get(destination):
            output[destination] = value
            matched_names[destination].append(matched_name)
    if not output.get("Isolation Source") and isolation_source_fallback:
        output["Isolation Source"] = isolation_source_fallback
        matched_names["Isolation Source"].append(isolation_source_fallback_name or "fallback_attribute")
    output["Metadata Fetch Status"] = "ok" if attributes else "source_missing"
    output["Metadata Fetch Reason"] = "fetched" if attributes else "no_attributes"
    output["Metadata Raw Attribute Names"] = "|".join(sorted({name for name in raw_names if name}))
    compact_matches = []
    for field, names in matched_names.items():
        if names:
            compact_matches.append(f"{field}:{'|'.join(sorted({name for name in names if name}))}")
    output["Metadata Matched Attribute Names"] = ";".join(compact_matches)
    output["BioSample Taxonomy Name"] = taxonomy_name_from_sample(sample)
    return output


def fetch_biosample_via_esummary(
    biosample: str,
    *,
    api_key: str | None,
    email: str | None,
    rate_limiter: RequestRateLimiter,
) -> dict[str, str]:
    search_response = request_with_retries(
        NCBI_ESEARCH_URL,
        params=ncbi_params(api_key, email, db="biosample", term=f"{biosample}[accn]", retmode="json"),
        rate_limiter=rate_limiter,
    )
    search_response.raise_for_status()
    id_list = search_response.json().get("esearchresult", {}).get("idlist", [])
    if not id_list:
        return {"Metadata Fetch Status": "not_found", "Metadata Fetch Reason": "esearch_no_uid"}
    summary_response = request_with_retries(
        NCBI_ESUMMARY_URL,
        params=ncbi_params(api_key, email, db="biosample", id=id_list[0], retmode="json"),
        rate_limiter=rate_limiter,
    )
    summary_response.raise_for_status()
    sampledata = summary_response.json().get("result", {}).get(id_list[0], {}).get("sampledata")
    if not sampledata:
        return {"Metadata Fetch Status": "source_missing", "Metadata Fetch Reason": "esummary_no_sampledata"}
    result = parse_biosample_xml(sampledata)
    if result.get("Metadata Fetch Status") == "ok":
        result["Metadata Fetch Reason"] = "esummary_fetched"
        result[FALLBACK_CACHE_XML_KEY] = sampledata
    return result


def fetch_biosample_metadata(
    biosample: str,
    *,
    api_key: str | None,
    email: str | None,
    rate_limiter: RequestRateLimiter,
    cache: MetadataCache,
) -> dict[str, str]:
    cached = cache.get(biosample)
    if cached is not None:
        cached_result = parse_biosample_xml(cached)
        if cached_result.get("Metadata Fetch Status") == "ok":
            return cached_result
    response = request_with_retries(
        NCBI_EFETCH_URL,
        params=ncbi_params(api_key, email, db="biosample", id=biosample, retmode="xml"),
        rate_limiter=rate_limiter,
    )
    result = parse_biosample_xml(response.text)
    if result.get("Metadata Fetch Status") == "ok":
        cache.set(biosample, response.text)
        return result
    fallback = fetch_biosample_via_esummary(biosample, api_key=api_key, email=email, rate_limiter=rate_limiter)
    if fallback.get("Metadata Fetch Status") == "ok":
        fallback_cache_xml = fallback.pop(FALLBACK_CACHE_XML_KEY, "")
        if fallback_cache_xml:
            cache.set(biosample, fallback_cache_xml)
        fallback["Metadata Fetch Reason"] = f"efetch_{result.get('Metadata Fetch Reason', 'missing')}_then_{fallback['Metadata Fetch Reason']}"
        return fallback
    return result


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
    rate_limiter = RequestRateLimiter(sleep)
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
                    rate_limiter=rate_limiter,
                    cache=cache,
                ): biosample
                for biosample in accessions
            }
            for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching BioSample metadata"):
                biosample = futures[future]
                try:
                    metadata_by_biosample[biosample] = future.result()
                except Exception as exc:
                    metadata_by_biosample[biosample] = {
                        "Metadata Fetch Status": "fetch_failed",
                        "Metadata Fetch Reason": type(exc).__name__,
                        "Metadata Fetch Error": str(exc),
                    }
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
    analysis: bool = True,
    keep_assembly_duplicates: bool = False,
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
    all_df = pd.DataFrame(standardized)
    all_df.to_csv(metadata_dir / "fetchm2_all_assemblies.csv", index=False)
    all_df.to_csv(metadata_dir / "fetchm2_all_assemblies.tsv", sep="\t", index=False)
    clean_df = all_df if keep_assembly_duplicates else select_representative_assemblies(all_df)
    clean_path = metadata_dir / "fetchm2_clean.csv"
    clean_df.to_csv(clean_path, index=False)
    clean_df.to_csv(metadata_dir / "fetchm2_clean.tsv", sep="\t", index=False)
    clean_rows = clean_df.fillna("").to_dict(orient="records")
    summary = write_audit_outputs(clean_rows, audit_dir)
    analysis_result = {}
    if analysis:
        analysis_result = generate_metadata_analysis(clean_df, outdir / "metadata_analysis")
    production_ready, hard_failures, warnings = production_gate(summary)
    report_lines = [
        "# FetchM2 Run Report",
        "",
        f"Input: {input_path}",
        f"All assembly rows after filters: {len(all_df)}",
        f"Rows processed: {summary['rows']}",
        f"Representative assembly mode: {'disabled; all assembly rows retained' if keep_assembly_duplicates else 'enabled; one row per Assembly Name, preferring GCF accessions'}",
        f"Unique Assembly Accession values: {summary.get('unique_assembly_accessions', 0)}",
        f"BioSample-linked rows: {summary.get('biosample_linked_rows', 0)}",
        f"Unique BioSample accessions represented: {summary.get('unique_biosample_accessions', 0)}",
        "BioSample fetch unit: unique BioSample accession; clean output unit: assembly row.",
        f"Clean table: {clean_path}",
        f"Metadata analysis: {outdir / 'metadata_analysis' if analysis else 'disabled'}",
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
        "analysis": analysis_result,
    }
