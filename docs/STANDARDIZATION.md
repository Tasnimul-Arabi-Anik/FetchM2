# FetchM2 Standardization Notes

FetchM2 packages deterministic standardization rules from FetchM Web so the standalone tool can reproduce the major standardized metadata fields without requiring a web database.

## Rule Sources

The packaged files live in `src/fetchm2/data/`:

- `host_synonyms.csv`: exact and broad host mappings with TaxID.
- `host_negative_rules.csv`: values blocked from `Host_SD`, including source/material/lab artifacts.
- `controlled_categories.csv`: source, sample, environment, disease, and health-state rules.
- `approved_broad_categories.csv`: allowed broad-category vocabulary.
- `geography_reviewed_rules.csv`: reviewed special geography cases.
- `collection_date_reviewed_rules.csv`: reviewed date phrases that need explicit year recovery.
- `country_mapping.json`: country, territory, historical-region, and marine-region mapping to continent/subcontinent labels.

## Output Fields

FetchM2 writes the original input columns plus standardized columns including:

- `Host_SD`, `Host_TaxID`, `Host_Rank`, host lineage fields, `Host_Context_SD`, match method, confidence, and review status.
- `Sample_Type_SD`, `Isolation_Source_SD`, `Isolation_Site_SD`.
- `Environment_Medium_SD`, `Environment_Broad_Scale_SD`, `Environment_Local_Scale_SD`.
- `Host_Disease_SD`, `Host_Health_State_SD`.
- `Country`, `Continent`, `Subcontinent`, `Country_Source`, `Country_Confidence`, `Country_Evidence`, `Geo_Recovery_Status`, `Collection_Year`.

Geography standardization supports primary `Country`/`Geographic Location` fields, reviewed geography rules, selected secondary text recovery from source/environment fields, and explicit false-positive guards for biological/product phrases such as `ground turkey`, `Guinea pig`, `Norway rat`, and `Aspergillus niger`.

## Production Gate

The audit gate fails on obvious category leakage:

- non-country values in `Country`
- country-continent and country-subcontinent mismatches
- invalid or future `Collection_Year` values
- host-only values in `Sample_Type_SD`
- unapproved `Isolation_Source_SD_Broad` values
- missing required clean standardized columns

Warnings are used for curation backlogs such as high host review counts.

Each `metadata`, `audit`, or `validate` run writes:

- `standardization_audit.md`
- `standardization_summary.csv`
- `production_readiness_gate.md`
- `production_readiness_gate.json`
- `top_host_review_needed.csv`
- issue-specific review CSVs for country, year, sample/source/host leakage, broad vocabulary, and sequence readiness.
