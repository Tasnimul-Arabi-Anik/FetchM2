from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .utils import first_present, read_package_csv, read_package_json


STANDARDIZED_COLUMNS = [
    "Host_Original",
    "Host_Cleaned",
    "Host_SD",
    "Host_TaxID",
    "Host_Rank",
    "Host_Superkingdom",
    "Host_Phylum",
    "Host_Class",
    "Host_Order",
    "Host_Family",
    "Host_Genus",
    "Host_Species",
    "Host_Common_Name",
    "Host_Context_SD",
    "Host_Match_Method",
    "Host_Confidence",
    "Host_Review_Status",
    "Sample_Type_SD",
    "Sample_Type_SD_Broad",
    "Isolation_Source_SD",
    "Isolation_Source_SD_Broad",
    "Isolation_Site_SD",
    "Environment_Medium_SD",
    "Environment_Medium_SD_Broad",
    "Environment_Broad_Scale_SD",
    "Environment_Local_Scale_SD",
    "Host_Disease_SD",
    "Host_Health_State_SD",
    "Country",
    "Continent",
    "Subcontinent",
    "Collection_Year",
    "FetchM2_Standardization_Notes",
]

HOST_ALIASES = [
    "Host",
    "host",
    "host scientific name",
    "host_scientific_name",
    "specific host",
]
SOURCE_FIELDS = {
    "Sample Type": [
        "Sample Type",
        "sample_type",
        "sample type",
        "specimen",
        "sample material",
    ],
    "Isolation Source": [
        "Isolation Source",
        "isolation_source",
        "isolation source",
        "source",
        "source type",
    ],
    "Isolation Site": [
        "Isolation Site",
        "isolation_site",
        "isolation site",
        "anatomical site",
        "body site",
    ],
    "Environment Medium": [
        "Environment Medium",
        "env_medium",
        "environmental medium",
        "environment",
    ],
    "Environment Broad Scale": [
        "Environment Broad Scale",
        "env_broad_scale",
        "broad-scale environmental context",
    ],
    "Environment Local Scale": [
        "Environment Local Scale",
        "env_local_scale",
        "local-scale environmental context",
    ],
    "Host Disease": [
        "Host Disease",
        "host disease",
        "disease",
    ],
    "Host Health State": [
        "Host Health State",
        "host health state",
        "health state",
    ],
}

MISSING_TOKENS = {
    "",
    "na",
    "n/a",
    "none",
    "null",
    "unknown",
    "unk",
    "missing",
    "not collected",
    "not applicable",
    "not available",
    "not reported",
    "not provided",
    "no data",
    "no host",
    "absent",
    "nil",
    "#ref!",
}

COUNTRY_FALSE_CONTEXT = re.compile(
    r"\b(hospital|clinic|outpatient|inpatient|ward|guinea pig|norway rat|ground turkey|aspergillus niger)\b",
    re.IGNORECASE,
)
DATE_YEAR_RE = re.compile(r"(19|20)\d{2}")
FOOD_PRODUCT_RE = re.compile(
    r"\b(sandwich|salad|sausage|pasta|food|retail|abattoir|fillet|tenderloin|meat product)\b",
    re.IGNORECASE,
)
SAMPLE_MATERIAL_RE = re.compile(
    r"\b(blood|feces|faeces|stool|urine|sputum|swab|tissue|milk|saliva|lavage|pleural fluid|meat|manure)\b",
    re.IGNORECASE,
)


def normalize_lookup(value: Any) -> str:
    text = "" if value is None else str(value).strip().lower()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[()\[\]{}\"'`]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,:;")


def is_missing(value: Any) -> bool:
    return normalize_lookup(value) in MISSING_TOKENS


@dataclass(frozen=True)
class ControlledRule:
    synonym: str
    source_column: str
    destination: str
    proposed_value: str
    broad_value: str
    ontology_id: str
    confidence: str
    method: str


@dataclass
class RuleStore:
    host_exact: dict[str, tuple[str, str, str]]
    host_broad: dict[str, tuple[str, str, str]]
    host_negative: dict[str, str]
    controlled: dict[str, list[ControlledRule]]
    controlled_source_specific: dict[tuple[str, str], list[ControlledRule]]
    approved_broad: dict[str, set[str]]
    country_mapping: dict[str, dict[str, str]]
    geography_rules: dict[str, str]
    collection_date_rules: dict[str, str]


@lru_cache(maxsize=1)
def load_rules() -> RuleStore:
    host_exact: dict[str, tuple[str, str, str]] = {}
    host_broad: dict[str, tuple[str, str, str]] = {}
    for row in read_package_csv("host_synonyms.csv"):
        key = normalize_lookup(row.get("synonym"))
        canonical = (row.get("canonical") or "").strip()
        taxid = (row.get("taxid") or "").strip()
        confidence = normalize_lookup(row.get("confidence") or "high")
        if not key or not canonical or not taxid:
            continue
        target = host_broad if confidence == "medium" else host_exact
        target[key] = (canonical, taxid, confidence or "high")

    host_negative: dict[str, str] = {}
    for row in read_package_csv("host_negative_rules.csv"):
        key = normalize_lookup(row.get("synonym"))
        decision = normalize_lookup(row.get("decision") or "non_host_source")
        if key:
            host_negative[key] = decision

    controlled: dict[str, list[ControlledRule]] = {}
    controlled_source_specific: dict[tuple[str, str], list[ControlledRule]] = {}
    for row in read_package_csv("controlled_categories.csv"):
        status = normalize_lookup(row.get("status") or "approved")
        if status not in {"approved", "active"}:
            continue
        key = normalize_lookup(row.get("synonym") or row.get("original_value") or row.get("normalized_value"))
        destination = (row.get("destination") or "").strip()
        proposed = (row.get("proposed_value") or row.get("category") or "").strip()
        if not key or not destination or not proposed:
            continue
        rule = ControlledRule(
            synonym=key,
            source_column=normalize_lookup(row.get("source_column")),
            destination=destination,
            proposed_value=proposed,
            broad_value=(row.get("broad_value") or "").strip(),
            ontology_id=(row.get("ontology_id") or "").strip(),
            confidence=normalize_lookup(row.get("confidence") or "medium"),
            method=normalize_lookup(row.get("method") or "dictionary"),
        )
        controlled.setdefault(key, []).append(rule)
        if rule.source_column:
            controlled_source_specific.setdefault((rule.source_column, key), []).append(rule)

    approved_broad: dict[str, set[str]] = {}
    for row in read_package_csv("approved_broad_categories.csv"):
        field = (row.get("field") or "").strip()
        value = (row.get("approved_value") or "").strip()
        if field and value:
            approved_broad.setdefault(field, set()).add(value)

    geography_rules = {
        normalize_lookup(row.get("source_value")): (row.get("country") or "").strip()
        for row in read_package_csv("geography_reviewed_rules.csv")
        if normalize_lookup(row.get("source_value")) and (row.get("country") or "").strip()
    }
    collection_date_rules = {
        normalize_lookup(row.get("source_value")): (row.get("year") or "").strip()
        for row in read_package_csv("collection_date_reviewed_rules.csv")
        if normalize_lookup(row.get("source_value")) and (row.get("year") or "").strip()
    }
    country_mapping = read_package_json("country_mapping.json")
    return RuleStore(
        host_exact=host_exact,
        host_broad=host_broad,
        host_negative=host_negative,
        controlled=controlled,
        controlled_source_specific=controlled_source_specific,
        approved_broad=approved_broad,
        country_mapping=country_mapping,
        geography_rules=geography_rules,
        collection_date_rules=collection_date_rules,
    )


COMMON_LINEAGE = {
    "9606": {
        "Host_Rank": "species",
        "Host_Superkingdom": "Eukaryota",
        "Host_Phylum": "Chordata",
        "Host_Class": "Mammalia",
        "Host_Order": "Primates",
        "Host_Family": "Hominidae",
        "Host_Genus": "Homo",
        "Host_Species": "Homo sapiens",
        "Host_Common_Name": "human",
    },
    "9913": {
        "Host_Rank": "species",
        "Host_Superkingdom": "Eukaryota",
        "Host_Phylum": "Chordata",
        "Host_Class": "Mammalia",
        "Host_Order": "Artiodactyla",
        "Host_Family": "Bovidae",
        "Host_Genus": "Bos",
        "Host_Species": "Bos taurus",
        "Host_Common_Name": "cattle",
    },
    "9823": {
        "Host_Rank": "species",
        "Host_Superkingdom": "Eukaryota",
        "Host_Phylum": "Chordata",
        "Host_Class": "Mammalia",
        "Host_Order": "Artiodactyla",
        "Host_Family": "Suidae",
        "Host_Genus": "Sus",
        "Host_Species": "Sus scrofa",
        "Host_Common_Name": "pig",
    },
    "9031": {
        "Host_Rank": "species",
        "Host_Superkingdom": "Eukaryota",
        "Host_Phylum": "Chordata",
        "Host_Class": "Aves",
        "Host_Order": "Galliformes",
        "Host_Family": "Phasianidae",
        "Host_Genus": "Gallus",
        "Host_Species": "Gallus gallus",
        "Host_Common_Name": "chicken",
    },
    "8782": {
        "Host_Rank": "class",
        "Host_Superkingdom": "Eukaryota",
        "Host_Phylum": "Chordata",
        "Host_Class": "Aves",
        "Host_Order": "",
        "Host_Family": "",
        "Host_Genus": "",
        "Host_Species": "",
        "Host_Common_Name": "bird",
    },
    "9615": {
        "Host_Rank": "subspecies",
        "Host_Superkingdom": "Eukaryota",
        "Host_Phylum": "Chordata",
        "Host_Class": "Mammalia",
        "Host_Order": "Carnivora",
        "Host_Family": "Canidae",
        "Host_Genus": "Canis",
        "Host_Species": "Canis lupus",
        "Host_Common_Name": "dog",
    },
    "9685": {
        "Host_Rank": "species",
        "Host_Superkingdom": "Eukaryota",
        "Host_Phylum": "Chordata",
        "Host_Class": "Mammalia",
        "Host_Order": "Carnivora",
        "Host_Family": "Felidae",
        "Host_Genus": "Felis",
        "Host_Species": "Felis catus",
        "Host_Common_Name": "cat",
    },
}


def empty_lineage() -> dict[str, str]:
    return {
        "Host_Rank": "",
        "Host_Superkingdom": "",
        "Host_Phylum": "",
        "Host_Class": "",
        "Host_Order": "",
        "Host_Family": "",
        "Host_Genus": "",
        "Host_Species": "",
        "Host_Common_Name": "",
    }


@lru_cache(maxsize=5000)
def taxonkit_lineage(taxid: str) -> dict[str, str]:
    taxid = str(taxid or "").strip()
    if taxid in COMMON_LINEAGE:
        return dict(COMMON_LINEAGE[taxid])
    if not taxid.isdigit() or shutil.which("taxonkit") is None:
        return empty_lineage()
    try:
        lineage = subprocess.run(
            ["taxonkit", "lineage", "-r"],
            input=f"{taxid}\n",
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        reformatted = subprocess.run(
            ["taxonkit", "reformat", "-f", "{k}\t{p}\t{c}\t{o}\t{f}\t{g}\t{s}"],
            input=lineage.stdout,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return empty_lineage()
    if lineage.returncode != 0 or reformatted.returncode != 0:
        return empty_lineage()
    line = reformatted.stdout.splitlines()[0] if reformatted.stdout.splitlines() else ""
    parts = line.split("\t")
    result = empty_lineage()
    if parts:
        result.update(
            {
                "Host_Rank": (lineage.stdout.split("\t")[2].strip() if len(lineage.stdout.split("\t")) >= 3 else ""),
                "Host_Phylum": parts[1].strip() if len(parts) > 1 else "",
                "Host_Class": parts[2].strip() if len(parts) > 2 else "",
                "Host_Order": parts[3].strip() if len(parts) > 3 else "",
                "Host_Family": parts[4].strip() if len(parts) > 4 else "",
                "Host_Genus": parts[5].strip() if len(parts) > 5 else "",
                "Host_Species": parts[6].strip() if len(parts) > 6 else "",
            }
        )
    return result


def host_match(value: str, *, allow_substring: bool = True) -> tuple[str, str, str, str]:
    rules = load_rules()
    cleaned = normalize_lookup(value)
    if is_missing(cleaned):
        return "", "", "missing", "none"
    if cleaned in rules.host_negative:
        decision = rules.host_negative[cleaned]
        if decision in {"missing", "absent"}:
            return "", "", "missing", "none"
        if decision in {"not_identifiable", "not identifiable"}:
            return "", "", "not_identifiable", "none"
        return "", "", "non_host_source", "none"
    if FOOD_PRODUCT_RE.search(str(value)) and not re.search(r"\b(human|patient|cattle|bovine|pig|swine|chicken)\b", str(value), re.I):
        return "", "", "non_host_source", "none"
    if cleaned in rules.host_exact:
        name, taxid, confidence = rules.host_exact[cleaned]
        return name, taxid, "dictionary", confidence
    if cleaned in rules.host_broad:
        name, taxid, confidence = rules.host_broad[cleaned]
        return name, taxid, "broad_dictionary", confidence or "medium"
    if allow_substring:
        compact = f" {cleaned.replace('.', '')} "
        for key, (name, taxid, confidence) in sorted(rules.host_exact.items(), key=lambda item: len(item[0]), reverse=True):
            if len(key) < 3:
                continue
            if re.search(rf"(^|\s){re.escape(key.replace('.', ''))}(\s|$)", compact):
                return name, taxid, "context_dictionary", confidence
        for key, (name, taxid, confidence) in sorted(rules.host_broad.items(), key=lambda item: len(item[0]), reverse=True):
            if len(key) < 4:
                continue
            if re.search(rf"(^|\s){re.escape(key)}(\s|$)", cleaned):
                return name, taxid, "broad_dictionary", confidence or "medium"
    return "", "", "review_needed", "none"


def standardize_host(row: dict[str, Any]) -> dict[str, str]:
    original = first_present(row, HOST_ALIASES)
    source_value = original
    context_value_used = ""
    name, taxid, method, confidence = host_match(original, allow_substring=True)
    if not taxid and method in {"missing", "non_host_source", "not_identifiable", "review_needed"}:
        for aliases in SOURCE_FIELDS.values():
            context_value = first_present(row, aliases)
            if not context_value or is_missing(context_value):
                continue
            context_name, context_taxid, context_method, context_conf = host_match(context_value, allow_substring=True)
            if context_taxid and SAMPLE_MATERIAL_RE.search(context_value):
                name, taxid = context_name, context_taxid
                method, confidence = "context_recovery", "medium"
                source_value = context_value
                context_value_used = context_value
                break
    cleaned = normalize_lookup(source_value)
    result = {
        "Host_Original": original,
        "Host_Cleaned": cleaned,
        "Host_SD": name,
        "Host_TaxID": taxid,
        "Host_Context_SD": context_value_used,
        "Host_Match_Method": method,
        "Host_Confidence": confidence,
        "Host_Review_Status": "accepted" if taxid else method,
    }
    result.update(empty_lineage())
    if taxid:
        result.update(taxonkit_lineage(taxid))
        if not result.get("Host_Common_Name") and name.lower() != cleaned:
            result["Host_Common_Name"] = cleaned
    return result


def compress_broad_value(field: str, value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    approved = load_rules().approved_broad.get(field, set())
    if value in approved:
        return value
    key = normalize_lookup(value)
    if "meat" in key:
        return "food/meat"
    if "dairy" in key or "milk" in key:
        return "food/dairy"
    if "food" in key:
        return "food"
    if "healthcare" in key or "hospital" in key or "clinical" in key:
        return "healthcare-associated environment" if "environment" in key else "clinical/host-associated material"
    if "culture" in key or "laboratory" in key:
        return "culture/laboratory"
    if "water" in key:
        return "water"
    if "soil" in key:
        return "soil"
    if "sediment" in key:
        return "sediment"
    if "environment" in key:
        return "environmental material"
    return value


def apply_controlled_rules(row: dict[str, Any]) -> dict[str, str]:
    rules = load_rules()
    output = {column: "" for column in STANDARDIZED_COLUMNS if column not in {"Country", "Continent", "Subcontinent", "Collection_Year"}}
    notes: list[str] = []
    for source_label, aliases in SOURCE_FIELDS.items():
        value = first_present(row, aliases)
        key = normalize_lookup(value)
        if not key or is_missing(key):
            continue
        source_key = normalize_lookup(source_label)
        candidates = rules.controlled_source_specific.get((source_key, key)) or rules.controlled.get(key, [])
        for rule in candidates:
            if rule.source_column and rule.source_column != source_key:
                continue
            if rule.destination == "Sample_Type_SD" and not SAMPLE_MATERIAL_RE.search(rule.proposed_value) and normalize_lookup(rule.proposed_value) in {
                "human",
                "patient",
                "animal",
                "poultry",
                "cattle",
                "pig",
                "plant",
                "bacteria",
            }:
                notes.append(f"skipped host-like sample type: {value}")
                continue
            if rule.destination in output and not output[rule.destination]:
                output[rule.destination] = rule.proposed_value
                broad_column = f"{rule.destination}_Broad"
                if broad_column in output and rule.broad_value:
                    output[broad_column] = compress_broad_value(broad_column, rule.broad_value)
        if source_label == "Sample Type" and key in {"pure culture", "bacterial culture", "bacteria culture", "single culture"}:
            output["Sample_Type_SD"] = "pure/single culture"
            if not output.get("Sample_Type_SD_Broad"):
                output["Sample_Type_SD_Broad"] = "culture/laboratory"
    output["FetchM2_Standardization_Notes"] = "; ".join(notes)
    return output


def standardize_collection_year(row: dict[str, Any]) -> str:
    rules = load_rules()
    value = first_present(
        row,
        [
            "Collection Date",
            "collection_date",
            "collection date",
            "sample_collection_date",
            "date_of_collection",
            "isolation_date",
            "Assembly Release Date",
        ],
    )
    key = normalize_lookup(value)
    if key in rules.collection_date_rules:
        return rules.collection_date_rules[key]
    match = DATE_YEAR_RE.search(value)
    return match.group(0) if match else ""


def standardize_geography(row: dict[str, Any]) -> dict[str, str]:
    rules = load_rules()
    raw = first_present(row, ["Geographic Location", "geo_loc_name", "geographic location", "Country", "country"])
    if not raw or is_missing(raw) or COUNTRY_FALSE_CONTEXT.search(raw):
        return {"Country": "", "Continent": "", "Subcontinent": ""}
    key = normalize_lookup(raw)
    if key in rules.geography_rules:
        country = rules.geography_rules[key]
    else:
        candidate = raw.split(":", 1)[0].strip()
        normalized_candidate = normalize_lookup(candidate)
        country = ""
        for known_country in rules.country_mapping:
            if normalize_lookup(known_country) == normalized_candidate:
                country = known_country
                break
        if not country:
            for alias, canonical in {
                "usa": "United States",
                "us": "United States",
                "u s a": "United States",
                "united states of america": "United States",
                "uk": "United Kingdom",
                "u k": "United Kingdom",
                "england": "United Kingdom",
                "south korea": "South Korea",
                "republic of korea": "South Korea",
            }.items():
                if normalized_candidate == alias:
                    country = canonical
                    break
    metadata = rules.country_mapping.get(country, {})
    return {
        "Country": country,
        "Continent": metadata.get("Continent", ""),
        "Subcontinent": metadata.get("Subcontinent", ""),
    }


def standardize_row(row: dict[str, Any]) -> dict[str, Any]:
    output = dict(row)
    standardized = {column: "" for column in STANDARDIZED_COLUMNS}
    standardized.update(apply_controlled_rules(row))
    standardized.update(standardize_host(row))
    standardized.update(standardize_geography(row))
    standardized["Collection_Year"] = standardize_collection_year(row)
    if standardized["Host_SD"] and not standardized.get("Sample_Type_SD"):
        sample_name, _, _, _ = host_match(first_present(row, HOST_ALIASES), allow_substring=False)
        if not sample_name:
            pass
    output.update(standardized)
    return output


def standardize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [standardize_row(row) for row in rows]
