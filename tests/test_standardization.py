from __future__ import annotations

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
