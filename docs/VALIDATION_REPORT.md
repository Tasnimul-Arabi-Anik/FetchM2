# FetchM2 Validation Report

Validation date: 2026-05-05
Current validation target: `fetchm2 0.1.1`

## Source Baselines

FetchM2 was built using:

- public standalone FetchM GitHub repository as the CLI/workflow baseline
- FetchM Web standardization rule files as deterministic packaged data

The public FetchM baseline inspected from GitHub was commit:

```text
11070b9 Avoid Chrome requirement for map export
```

## Packaged Rule Counts

FetchM2 packages these deterministic rule resources:

| Rule file | Rows |
| --- | ---: |
| `host_synonyms.csv` | 7,113 |
| `host_negative_rules.csv` | 408 |
| `controlled_categories.csv` | 7,505 |
| `approved_broad_categories.csv` | 50 |
| `geography_reviewed_rules.csv` | 16 |
| `country_mapping.json` | 202 countries/regions |

## Commands Validated

The following commands were validated in isolated environments:

```bash
fetchm2 --version
fetchm2 metadata --input examples/offline_metadata.tsv --outdir /tmp/fetchm2_smoke --offline
fetchm2 audit --input /tmp/fetchm2_smoke/metadata_output/fetchm2_clean.csv --outdir /tmp/fetchm2_smoke_audit
fetchm2 seq --input /tmp/fetchm2_smoke/metadata_output/fetchm2_clean.csv --outdir /tmp/fetchm2_smoke_seq --country Bangladesh --check-only
```

## Test Results

Regression tests:

```text
7 passed
```

Package build for `0.1.1`:

```text
python -m build: passed
twine check dist/*: passed
```

Wheel installation for `0.1.1`:

```text
pip install fetchm2-0.1.1-py3-none-any.whl: passed
fetchm2 --version: fetchm2 0.1.1
```

Wheel smoke test for `0.1.1`:

```text
metadata command: production gate PASS
metadata analysis outputs: generated
sequence check-only: selected 1 accession and completed without download
```

Live NCBI smoke test:

```text
Input: first two rows from public FetchM test.tsv
BioSample records requested: 1 unique BioSample
Result: metadata command completed and production gate PASS
```

## Additional 0.1.1 Development Validation

The 0.1.1 development update adds:

- top-level `test.tsv`
- conda `environment.yml`
- automatic `metadata_analysis/` outputs
- `fetchm2 analyze`
- expanded BioSample parser with direct `BioSample`, `BioSampleSet`, raw attribute tracking, matched attribute tracking, and `esummary` fallback
- shared NCBI request throttling, retry, and backoff behavior
- cached BioSample retrieval with explicit fetch status, fetch reason, and fetch error columns

Local development validation:

```text
pytest: 7 passed
test.tsv offline metadata run: production gate PASS
test.tsv offline metadata analysis: generated coverage tables, numeric summaries, top-value tables, and figures
```

Live 20-row `test.tsv` BioSample validation after the parser/fallback update:

```text
Rows scanned: 20
BioSample records fetched: 10 unique accessions
Production gate: PASS
Host TaxID mapped: 14 / 20 (70.0%)
Country present: 14 / 20 (70.0%)
Collection year present: 18 / 20 (90.0%)
Invalid host-like Sample_Type_SD rows: 0
Non-country values in Country rows: 0
Unapproved Isolation_Source_SD_Broad rows: 0
Metadata analysis figures generated: yes
```

Live full `test.tsv` BioSample validation after the retry/fallback update:

```text
Rows scanned: 200
BioSample rows fetched: 200 / 200
Metadata fetch errors: 0
Production gate: PASS
Host TaxID mapped: 92 / 200 (46.0%)
Host review needed: 54
Country present: 178 / 200 (89.0%)
Collection year present: 196 / 200 (98.0%)
Sample_Type_SD present: 66
Isolation_Source_SD present: 28
Isolation_Site_SD present: 46
Environment_Medium_SD present: 10
Invalid host-like Sample_Type_SD rows: 0
Non-country values in Country rows: 0
Unapproved Isolation_Source_SD_Broad rows: 0
Metadata analysis figures generated: 49
```

BioSample fetch reasons in the full live test:

```text
fetched: 186
efetch_no_biosample_then_esummary_fetched: 12
efetch_no_attributes_then_esummary_fetched: 2
```

## Regression Scenarios Covered

The test suite checks:

- `human blood` maps to `Host_SD=Homo sapiens`, `Host_TaxID=9606`, and `Sample_Type_SD=blood`
- `bacteria culture` is blocked from `Host_SD`
- `Hospital` is blocked from standardized `Country`
- `turkey breast sandwich` does not become a country or host
- `water deer` remains a valid host and is not treated as water
- metadata CLI writes clean outputs and audit files
- sequence `--check-only` works with standardized filters

## Release Readiness

FetchM2 `0.1.0` has been released on GitHub and PyPI.

The `0.1.1` update has passed local tests, package build validation, clean wheel installation, offline packaged-test validation, 20-row live BioSample validation, and full `test.tsv` live BioSample validation.

Known scope notes for `0.1.1`:

- host lineage is bundled for common hosts and optionally enriched with `taxonkit` when installed
- embeddings/BGE are intentionally not used in production standardization
- large-scale sequence download was not run during this validation to avoid unnecessary NCBI load
