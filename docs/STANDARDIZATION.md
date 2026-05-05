# FetchM2 Standardization Notes

FetchM2 packages deterministic standardization rules from FetchM Web so the standalone tool can reproduce the major standardized metadata fields without requiring a web database.

## Rule Sources

The packaged files live in `src/fetchm2/data/`:

- `host_synonyms.csv`: exact and broad host mappings with TaxID.
- `host_negative_rules.csv`: values blocked from `Host_SD`, including source/material/lab artifacts.
- `controlled_categories.csv`: source, sample, environment, disease, and health-state rules.
- `approved_broad_categories.csv`: allowed broad-category vocabulary.
- `geography_reviewed_rules.csv`: reviewed special geography cases.
- `country_mapping.json`: country, continent, and subcontinent mapping extracted from public FetchM.

## Output Fields

FetchM2 writes the original input columns plus standardized columns including:

- `Host_SD`, `Host_TaxID`, `Host_Rank`, host lineage fields, match method, confidence, and review status.
- `Sample_Type_SD`, `Isolation_Source_SD`, `Isolation_Site_SD`.
- `Environment_Medium_SD`, `Environment_Broad_Scale_SD`, `Environment_Local_Scale_SD`.
- `Host_Disease_SD`, `Host_Health_State_SD`.
- `Country`, `Continent`, `Subcontinent`, `Collection_Year`.

## Production Gate

The audit gate fails on obvious category leakage:

- non-country values in `Country`
- host-only values in `Sample_Type_SD`
- unapproved `Isolation_Source_SD_Broad` values

Warnings are used for curation backlogs such as high host review counts.
