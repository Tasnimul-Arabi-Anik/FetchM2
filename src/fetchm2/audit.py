from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .standardization import load_rules, normalize_lookup
from .utils import write_csv, write_text

ALLOWED_MARINE_REGIONS = {
    "Arctic Ocean",
    "Atlantic Ocean",
    "Indian Ocean",
    "Pacific Ocean",
    "Southern Ocean",
    "Mediterranean Sea",
    "North Sea",
    "Baltic Sea",
}


def value_present(value: Any) -> bool:
    return bool(str(value or "").strip())


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    host_taxid = sum(1 for row in rows if value_present(row.get("Host_TaxID")))
    host_review = sum(1 for row in rows if row.get("Host_Review_Status") == "review_needed")
    country = sum(1 for row in rows if value_present(row.get("Country")))
    collection_year = sum(1 for row in rows if value_present(row.get("Collection_Year")))
    sample_type = sum(1 for row in rows if value_present(row.get("Sample_Type_SD")))
    isolation_source = sum(1 for row in rows if value_present(row.get("Isolation_Source_SD")))
    isolation_site = sum(1 for row in rows if value_present(row.get("Isolation_Site_SD")))
    environment_medium = sum(1 for row in rows if value_present(row.get("Environment_Medium_SD")))
    host_disease = sum(1 for row in rows if value_present(row.get("Host_Disease_SD")))
    host_health = sum(1 for row in rows if value_present(row.get("Host_Health_State_SD")))
    invalid_sample = [
        row
        for row in rows
        if normalize_lookup(row.get("Sample_Type_SD")) in {"human", "patient", "animal", "poultry", "cattle", "pig", "plant", "bacteria"}
    ]
    non_country = [
        row
        for row in rows
        if value_present(row.get("Country"))
        and row.get("Country") not in load_rules().country_mapping
        and row.get("Country") not in ALLOWED_MARINE_REGIONS
    ]
    broad_values = Counter(str(row.get("Isolation_Source_SD_Broad") or "").strip() for row in rows if value_present(row.get("Isolation_Source_SD_Broad")))
    approved_broad = load_rules().approved_broad.get("Isolation_Source_SD_Broad", set())
    unapproved_broad = {
        value: count
        for value, count in broad_values.items()
        if value and value not in approved_broad
    }
    return {
        "rows": total,
        "host_taxid_mapped": host_taxid,
        "host_taxid_percent": round((host_taxid / total) * 100, 2) if total else 0,
        "host_review_needed": host_review,
        "country_present": country,
        "country_percent": round((country / total) * 100, 2) if total else 0,
        "collection_year_present": collection_year,
        "collection_year_percent": round((collection_year / total) * 100, 2) if total else 0,
        "sample_type_present": sample_type,
        "isolation_source_present": isolation_source,
        "isolation_site_present": isolation_site,
        "environment_medium_present": environment_medium,
        "host_disease_present": host_disease,
        "host_health_state_present": host_health,
        "invalid_host_like_sample_type_rows": len(invalid_sample),
        "non_country_values_in_country_rows": len(non_country),
        "unapproved_isolation_source_broad_rows": sum(unapproved_broad.values()),
        "unique_isolation_source_broad_values": len(broad_values),
    }


def write_audit_outputs(rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    summary = summarize_rows(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "standardization_summary.csv", [summary])

    top_host_review = Counter(
        str(row.get("Host_Original") or "").strip()
        for row in rows
        if row.get("Host_Review_Status") == "review_needed"
    )
    write_csv(
        output_dir / "top_host_review_needed.csv",
        [{"host_original": key, "count": count} for key, count in top_host_review.most_common(200)],
    )

    markdown = [
        "# FetchM2 Metadata Standardization Audit",
        "",
        f"Rows scanned: {summary['rows']}",
        f"Host TaxID mapped: {summary['host_taxid_mapped']} ({summary['host_taxid_percent']}%)",
        f"Host review needed: {summary['host_review_needed']}",
        f"Country present: {summary['country_present']} ({summary['country_percent']}%)",
        f"Collection year present: {summary['collection_year_present']} ({summary['collection_year_percent']}%)",
        f"Sample_Type_SD present: {summary['sample_type_present']}",
        f"Isolation_Source_SD present: {summary['isolation_source_present']}",
        f"Isolation_Site_SD present: {summary['isolation_site_present']}",
        f"Environment_Medium_SD present: {summary['environment_medium_present']}",
        f"Invalid host-like Sample_Type_SD rows: {summary['invalid_host_like_sample_type_rows']}",
        f"Non-country values in Country rows: {summary['non_country_values_in_country_rows']}",
        f"Unapproved Isolation_Source_SD_Broad rows: {summary['unapproved_isolation_source_broad_rows']}",
    ]
    write_text(output_dir / "standardization_audit.md", "\n".join(markdown) + "\n")
    return summary


def production_gate(summary: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    hard_failures: list[str] = []
    warnings: list[str] = []
    for key in [
        "invalid_host_like_sample_type_rows",
        "non_country_values_in_country_rows",
        "unapproved_isolation_source_broad_rows",
    ]:
        if int(summary.get(key) or 0) > 0:
            hard_failures.append(f"{key}={summary[key]}")
    if int(summary.get("host_review_needed") or 0) > 1000:
        warnings.append(f"host_review_needed={summary['host_review_needed']}")
    return not hard_failures, hard_failures, warnings
