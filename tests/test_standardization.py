from __future__ import annotations

from fetchm2.audit import summarize_rows
from fetchm2.standardization import standardize_row


def test_human_blood_maps_host_and_sample() -> None:
    row = standardize_row(
        {
            "Host": "human blood",
            "Sample Type": "blood",
            "Collection Date": "2020-04-01",
            "Geographic Location": "Bangladesh: Dhaka",
        }
    )
    assert row["Host_SD"] == "Homo sapiens"
    assert row["Host_TaxID"] == "9606"
    assert row["Sample_Type_SD"] == "blood"
    assert row["Country"] == "Bangladesh"
    assert row["Continent"] == "Asia"
    assert row["Subcontinent"] == "Southern Asia"
    assert row["Collection_Year"] == "2020"


def test_non_host_and_country_false_positive_blocked() -> None:
    row = standardize_row(
        {
            "Host": "bacteria culture",
            "Geographic Location": "Hospital",
            "Sample Type": "pure culture",
        }
    )
    assert row["Host_SD"] == ""
    assert row["Host_Review_Status"] == "non_host_source"
    assert row["Country"] == ""
    assert row["Sample_Type_SD"] in {"pure/single culture", "pure culture"}


def test_food_cut_does_not_become_country_or_host() -> None:
    row = standardize_row(
        {
            "Host": "turkey breast sandwich",
            "Geographic Location": "ground turkey",
            "Sample Type": "meat",
        }
    )
    assert row["Country"] == ""
    assert row["Host_SD"] == ""
    assert row["Sample_Type_SD"] == "meat"


def test_water_deer_is_host_not_water_medium() -> None:
    row = standardize_row({"Host": "water deer"})
    assert row["Host_SD"] == "Hydropotes inermis"
    assert row["Host_TaxID"]
    assert row["Environment_Medium_SD"] == ""


def test_host_context_recovery_and_date_alias() -> None:
    row = standardize_row(
        {
            "Host": "",
            "Sample Type": "human feces",
            "sample_collection_date": "2021-07",
        }
    )
    assert row["Host_SD"] == "Homo sapiens"
    assert row["Host_Context_SD"] == "human feces"
    assert row["Host_Match_Method"] == "context_recovery"
    assert row["Collection_Year"] == "2021"


def test_audit_reports_assembly_and_biosample_units_separately() -> None:
    rows = [
        standardize_row(
            {
                "Assembly Accession": "GCA_000000001.1",
                "Assembly BioSample Accession": "SAMN00000001",
                "Host": "human",
            }
        ),
        standardize_row(
            {
                "Assembly Accession": "GCF_000000001.1",
                "Assembly BioSample Accession": "SAMN00000001",
                "Host": "human",
            }
        ),
    ]

    summary = summarize_rows(rows)
    assert summary["rows"] == 2
    assert summary["unique_assembly_accessions"] == 2
    assert summary["duplicate_assembly_accession_extra_rows"] == 0
    assert summary["biosample_linked_rows"] == 2
    assert summary["unique_biosample_accessions"] == 1
    assert summary["biosample_reused_extra_rows"] == 1
    assert summary["biosamples_with_multiple_assembly_accessions"] == 1
