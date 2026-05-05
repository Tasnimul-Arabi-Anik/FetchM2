from __future__ import annotations

import json
from collections import Counter
from datetime import date
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

HOST_LIKE_SAMPLE_TYPES = {
    "human",
    "patient",
    "people",
    "animal",
    "mammal",
    "bird",
    "poultry",
    "cattle",
    "cow",
    "pig",
    "swine",
    "chicken",
    "fish",
    "plant",
    "bacteria",
    "organism",
    "host",
}

SOURCE_LIKE_HOST_TERMS = {
    "soil",
    "water",
    "wastewater",
    "sewage",
    "sediment",
    "sludge",
    "air",
    "dust",
    "biofilm",
    "food",
    "meat",
    "milk",
    "dairy",
    "seafood",
    "hospital",
    "clinic",
    "icu",
    "ward",
    "surface",
    "culture",
    "cell line",
    "strain",
    "isolate",
    "metagenome",
    "not reported",
    "not applicable",
    "#ref!",
}

REQUIRED_CLEAN_COLUMNS = [
    "Host_SD",
    "Host_TaxID",
    "Host_Review_Status",
    "Country",
    "Continent",
    "Subcontinent",
    "Collection_Year",
    "Sample_Type_SD",
    "Isolation_Source_SD",
    "Isolation_Source_SD_Broad",
    "Isolation_Site_SD",
    "Environment_Medium_SD",
]

ISSUE_FIELDNAMES = [
    "issue",
    "details",
    "assembly_accession",
    "biosample",
    "host_original",
    "host_sd",
    "sample_type_sd",
    "isolation_source_sd",
    "isolation_source_sd_broad",
    "environment_medium_sd",
    "country",
    "continent",
    "subcontinent",
    "collection_year",
    "field",
    "value",
    "missing_columns",
]


def value_present(value: Any) -> bool:
    return bool(str(value or "").strip())


def percent(count: int, total: int) -> float:
    return round((count / total) * 100, 2) if total else 0.0


def short_row(row: dict[str, Any], issue: str, details: str = "") -> dict[str, Any]:
    return {
        "issue": issue,
        "details": details,
        "assembly_accession": str(row.get("Assembly Accession") or "").strip(),
        "biosample": str(row.get("BioSample") or row.get("Assembly BioSample Accession") or "").strip(),
        "host_original": str(row.get("Host_Original") or row.get("Host") or "").strip(),
        "host_sd": str(row.get("Host_SD") or "").strip(),
        "sample_type_sd": str(row.get("Sample_Type_SD") or "").strip(),
        "isolation_source_sd": str(row.get("Isolation_Source_SD") or "").strip(),
        "isolation_source_sd_broad": str(row.get("Isolation_Source_SD_Broad") or "").strip(),
        "environment_medium_sd": str(row.get("Environment_Medium_SD") or "").strip(),
        "country": str(row.get("Country") or "").strip(),
        "continent": str(row.get("Continent") or "").strip(),
        "subcontinent": str(row.get("Subcontinent") or "").strip(),
        "collection_year": str(row.get("Collection_Year") or "").strip(),
    }


def valid_country(country: str) -> bool:
    if not country:
        return True
    return country in load_rules().country_mapping or country in ALLOWED_MARINE_REGIONS


def expected_geography(country: str) -> dict[str, str]:
    return load_rules().country_mapping.get(country, {})


def collection_year_issue(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not text.isdigit():
        return "not_integer"
    year = int(text)
    current_year = date.today().year
    if year < 1800:
        return "too_old"
    if year > current_year:
        return "future_year"
    return ""


def source_like(value: Any) -> bool:
    normalized = normalize_lookup(value)
    if not normalized:
        return False
    return any(term in normalized for term in SOURCE_LIKE_HOST_TERMS)


def rule_count_summary() -> dict[str, Any]:
    rules = load_rules()
    return {
        "host_exact_rules": len(rules.host_exact),
        "host_broad_rules": len(rules.host_broad),
        "host_negative_rules": len(rules.host_negative),
        "controlled_rule_keys": len(rules.controlled),
        "controlled_source_specific_keys": len(rules.controlled_source_specific),
        "approved_broad_fields": len(rules.approved_broad),
        "approved_broad_values": sum(len(values) for values in rules.approved_broad.values()),
        "geography_reviewed_rules": len(rules.geography_rules),
        "country_mapping_entries": len(rules.country_mapping),
        "collection_date_reviewed_rules": len(getattr(rules, "collection_date_rules", {})),
    }


def first_present(row: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def assembly_biosample_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    assembly_values = [
        first_present(row, ["Assembly Accession"])
        for row in rows
    ]
    assembly_values = [value for value in assembly_values if value]
    biosample_values = [
        first_present(row, ["BioSample", "Assembly BioSample Accession", "BioSample Accession"])
        for row in rows
    ]
    biosample_values = [value for value in biosample_values if value]

    biosample_to_assemblies: dict[str, set[str]] = {}
    for row in rows:
        biosample = first_present(row, ["BioSample", "Assembly BioSample Accession", "BioSample Accession"])
        assembly = first_present(row, ["Assembly Accession"])
        if biosample:
            biosample_to_assemblies.setdefault(biosample, set())
            if assembly:
                biosample_to_assemblies[biosample].add(assembly)

    unique_assemblies = len(set(assembly_values))
    unique_biosamples = len(set(biosample_values))
    return {
        "assembly_rows": len(rows),
        "assembly_accession_present_rows": len(assembly_values),
        "unique_assembly_accessions": unique_assemblies,
        "duplicate_assembly_accession_extra_rows": max(0, len(assembly_values) - unique_assemblies),
        "biosample_linked_rows": len(biosample_values),
        "unique_biosample_accessions": unique_biosamples,
        "biosample_reused_extra_rows": max(0, len(biosample_values) - unique_biosamples),
        "biosamples_with_multiple_assembly_accessions": sum(
            1 for assemblies in biosample_to_assemblies.values() if len(assemblies) > 1
        ),
    }


def issue_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    rules = load_rules()
    country_mismatches: list[dict[str, Any]] = []
    subcontinent_mismatches: list[dict[str, Any]] = []
    non_country: list[dict[str, Any]] = []
    invalid_years: list[dict[str, Any]] = []
    invalid_sample: list[dict[str, Any]] = []
    broad_leakage: list[dict[str, Any]] = []
    source_like_mapped: list[dict[str, Any]] = []
    source_like_unmapped: list[dict[str, Any]] = []
    missing_required: list[dict[str, Any]] = []
    sequence_readiness: list[dict[str, Any]] = []

    for row in rows:
        country = str(row.get("Country") or "").strip()
        if country and not valid_country(country):
            non_country.append(short_row(row, "non_country_value", country))
        expected = expected_geography(country)
        if expected and str(row.get("Continent") or "").strip() and row.get("Continent") != expected.get("Continent"):
            country_mismatches.append(short_row(row, "country_continent_mismatch", f"expected={expected.get('Continent', '')}"))
        if expected and str(row.get("Subcontinent") or "").strip() and row.get("Subcontinent") != expected.get("Subcontinent"):
            subcontinent_mismatches.append(short_row(row, "country_subcontinent_mismatch", f"expected={expected.get('Subcontinent', '')}"))

        year_problem = collection_year_issue(row.get("Collection_Year"))
        if year_problem:
            invalid_years.append(short_row(row, year_problem, str(row.get("Collection_Year") or "")))

        sample_key = normalize_lookup(row.get("Sample_Type_SD"))
        if sample_key in HOST_LIKE_SAMPLE_TYPES:
            invalid_sample.append(short_row(row, "host_like_sample_type", str(row.get("Sample_Type_SD") or "")))

        for field, approved_values in rules.approved_broad.items():
            value = str(row.get(field) or "").strip()
            if value and value not in approved_values:
                issue = short_row(row, "unapproved_broad_value", f"{field}={value}")
                issue["field"] = field
                issue["value"] = value
                broad_leakage.append(issue)

        host_original = str(row.get("Host_Original") or row.get("Host") or "").strip()
        if source_like(host_original):
            if value_present(row.get("Host_SD")):
                source_like_mapped.append(short_row(row, "source_like_host_mapped", host_original))
            elif row.get("Host_Review_Status") in {"review_needed", "non_host_source", "missing", "not_identifiable", ""}:
                source_like_unmapped.append(short_row(row, "source_like_host_unmapped", host_original))

        missing_cols = [column for column in REQUIRED_CLEAN_COLUMNS if column not in row]
        if missing_cols:
            missing_required.append({"issue": "missing_required_columns", "missing_columns": "|".join(missing_cols)})
            break

        if not value_present(row.get("Assembly Accession")):
            sequence_readiness.append(short_row(row, "missing_assembly_accession"))
        elif not value_present(row.get("Assembly Name")):
            sequence_readiness.append(short_row(row, "missing_assembly_name"))

    return {
        "country_continent_mismatch": country_mismatches,
        "country_subcontinent_mismatch": subcontinent_mismatches,
        "non_country_values_in_country": non_country,
        "invalid_collection_years": invalid_years,
        "invalid_host_like_sample_type": invalid_sample,
        "broad_vocabulary_leakage": broad_leakage,
        "source_like_mapped_hosts": source_like_mapped,
        "source_like_unmapped_hosts_for_review": source_like_unmapped,
        "missing_required_columns": missing_required,
        "sequence_readiness": sequence_readiness,
    }


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
    issues = issue_rows(rows)
    broad_values = Counter(str(row.get("Isolation_Source_SD_Broad") or "").strip() for row in rows if value_present(row.get("Isolation_Source_SD_Broad")))
    fetch_failed = sum(1 for row in rows if row.get("Metadata Fetch Status") == "fetch_failed")
    unit_counts = assembly_biosample_summary(rows)
    return {
        "rows": total,
        **unit_counts,
        "host_taxid_mapped": host_taxid,
        "host_taxid_percent": percent(host_taxid, total),
        "host_review_needed": host_review,
        "country_present": country,
        "country_percent": percent(country, total),
        "collection_year_present": collection_year,
        "collection_year_percent": percent(collection_year, total),
        "sample_type_present": sample_type,
        "sample_type_percent": percent(sample_type, total),
        "isolation_source_present": isolation_source,
        "isolation_source_percent": percent(isolation_source, total),
        "isolation_site_present": isolation_site,
        "isolation_site_percent": percent(isolation_site, total),
        "environment_medium_present": environment_medium,
        "environment_medium_percent": percent(environment_medium, total),
        "host_disease_present": host_disease,
        "host_health_state_present": host_health,
        "invalid_host_like_sample_type_rows": len(issues["invalid_host_like_sample_type"]),
        "non_country_values_in_country_rows": len(issues["non_country_values_in_country"]),
        "country_continent_mismatch_rows": len(issues["country_continent_mismatch"]),
        "country_subcontinent_mismatch_rows": len(issues["country_subcontinent_mismatch"]),
        "invalid_collection_year_rows": len(issues["invalid_collection_years"]),
        "unapproved_isolation_source_broad_rows": len(
            [row for row in issues["broad_vocabulary_leakage"] if row.get("field") == "Isolation_Source_SD_Broad"]
        ),
        "unapproved_broad_category_rows": len(issues["broad_vocabulary_leakage"]),
        "source_like_mapped_host_rows": len(issues["source_like_mapped_hosts"]),
        "source_like_unmapped_host_rows": len(issues["source_like_unmapped_hosts_for_review"]),
        "missing_required_column_rows": len(issues["missing_required_columns"]),
        "sequence_readiness_issue_rows": len(issues["sequence_readiness"]),
        "metadata_fetch_failed_rows": fetch_failed,
        "unique_isolation_source_broad_values": len(broad_values),
        **{f"rules_{key}": value for key, value in rule_count_summary().items()},
    }


def write_audit_outputs(rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    summary = summarize_rows(rows)
    issues = issue_rows(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "standardization_summary.csv", [summary])
    write_csv(output_dir / "rule_count_summary.csv", [rule_count_summary()])

    top_host_review = Counter(
        str(row.get("Host_Original") or "").strip()
        for row in rows
        if row.get("Host_Review_Status") == "review_needed"
    )
    write_csv(
        output_dir / "top_host_review_needed.csv",
        [{"host_original": key, "count": count} for key, count in top_host_review.most_common(200)],
        fieldnames=["host_original", "count"],
    )
    for name, rows_for_issue in issues.items():
        write_csv(output_dir / f"{name}.csv", rows_for_issue, fieldnames=ISSUE_FIELDNAMES)

    production_ready, hard_failures, warnings = production_gate(summary)
    gate = {
        "production_ready": production_ready,
        "status": "PASS" if production_ready else "FAIL",
        "hard_failures": hard_failures,
        "warnings": warnings,
        "summary": summary,
    }
    (output_dir / "production_readiness_gate.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    gate_markdown = [
        "# FetchM2 Production Readiness Gate",
        "",
        f"Status: {'PASS' if production_ready else 'FAIL'}",
        "",
        "## Hard Failures",
        "",
    ]
    gate_markdown.extend([f"- {failure}" for failure in hard_failures] or ["- None"])
    gate_markdown.extend(["", "## Warnings", ""])
    gate_markdown.extend([f"- {warning}" for warning in warnings] or ["- None"])
    write_text(output_dir / "production_readiness_gate.md", "\n".join(gate_markdown) + "\n")

    markdown = [
        "# FetchM2 Metadata Standardization Audit",
        "",
        f"Production gate: {'PASS' if production_ready else 'FAIL'}",
        f"Rows scanned: {summary['rows']}",
        f"Unique Assembly Accession values: {summary['unique_assembly_accessions']}",
        f"Duplicate Assembly Accession extra rows: {summary['duplicate_assembly_accession_extra_rows']}",
        f"BioSample-linked rows: {summary['biosample_linked_rows']}",
        f"Unique BioSample accessions represented: {summary['unique_biosample_accessions']}",
        f"BioSample reuse extra rows: {summary['biosample_reused_extra_rows']}",
        f"BioSamples linked to multiple Assembly Accession values: {summary['biosamples_with_multiple_assembly_accessions']}",
        "BioSample fetch unit: unique BioSample accession; clean output unit: assembly row.",
        f"Host TaxID mapped: {summary['host_taxid_mapped']} ({summary['host_taxid_percent']}%)",
        f"Host review needed: {summary['host_review_needed']}",
        f"Country present: {summary['country_present']} ({summary['country_percent']}%)",
        f"Collection year present: {summary['collection_year_present']} ({summary['collection_year_percent']}%)",
        f"Sample_Type_SD present: {summary['sample_type_present']} ({summary['sample_type_percent']}%)",
        f"Isolation_Source_SD present: {summary['isolation_source_present']} ({summary['isolation_source_percent']}%)",
        f"Isolation_Site_SD present: {summary['isolation_site_present']} ({summary['isolation_site_percent']}%)",
        f"Environment_Medium_SD present: {summary['environment_medium_present']} ({summary['environment_medium_percent']}%)",
        f"Invalid host-like Sample_Type_SD rows: {summary['invalid_host_like_sample_type_rows']}",
        f"Non-country values in Country rows: {summary['non_country_values_in_country_rows']}",
        f"Country-continent mismatch rows: {summary['country_continent_mismatch_rows']}",
        f"Country-subcontinent mismatch rows: {summary['country_subcontinent_mismatch_rows']}",
        f"Invalid/future Collection_Year rows: {summary['invalid_collection_year_rows']}",
        f"Unapproved Isolation_Source_SD_Broad rows: {summary['unapproved_isolation_source_broad_rows']}",
        f"Unapproved broad-category rows: {summary['unapproved_broad_category_rows']}",
        f"Metadata fetch failed rows: {summary['metadata_fetch_failed_rows']}",
        f"Source-like mapped host rows: {summary['source_like_mapped_host_rows']}",
        f"Source-like unmapped host rows: {summary['source_like_unmapped_host_rows']}",
        f"Sequence-readiness issue rows: {summary['sequence_readiness_issue_rows']}",
        "",
        "## Review Files",
        "",
        "- `production_readiness_gate.md`",
        "- `production_readiness_gate.json`",
        "- `top_host_review_needed.csv`",
        "- `non_country_values_in_country.csv`",
        "- `country_continent_mismatch.csv`",
        "- `country_subcontinent_mismatch.csv`",
        "- `invalid_collection_years.csv`",
        "- `invalid_host_like_sample_type.csv`",
        "- `source_like_mapped_hosts.csv`",
        "- `source_like_unmapped_hosts_for_review.csv`",
        "- `broad_vocabulary_leakage.csv`",
        "- `sequence_readiness.csv`",
        "- `rule_count_summary.csv`",
    ]
    write_text(output_dir / "standardization_audit.md", "\n".join(markdown) + "\n")
    return summary


def production_gate(summary: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    hard_failures: list[str] = []
    warnings: list[str] = []
    for key in [
        "invalid_host_like_sample_type_rows",
        "non_country_values_in_country_rows",
        "country_continent_mismatch_rows",
        "country_subcontinent_mismatch_rows",
        "invalid_collection_year_rows",
        "unapproved_isolation_source_broad_rows",
        "unapproved_broad_category_rows",
        "missing_required_column_rows",
    ]:
        if int(summary.get(key) or 0) > 0:
            hard_failures.append(f"{key}={summary[key]}")
    if int(summary.get("host_review_needed") or 0) > 1000:
        warnings.append(f"host_review_needed={summary['host_review_needed']}")
    if int(summary.get("source_like_unmapped_host_rows") or 0) > 5000:
        warnings.append(f"source_like_unmapped_host_rows={summary['source_like_unmapped_host_rows']}")
    if float(summary.get("host_taxid_percent") or 0) < 55:
        warnings.append(f"host_taxid_percent={summary['host_taxid_percent']}")
    if float(summary.get("country_percent") or 0) < 80:
        warnings.append(f"country_percent={summary['country_percent']}")
    if float(summary.get("collection_year_percent") or 0) < 75:
        warnings.append(f"collection_year_percent={summary['collection_year_percent']}")
    return not hard_failures, hard_failures, warnings
