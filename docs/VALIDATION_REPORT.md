# FetchM2 Validation Report

Validation date: 2026-05-05

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
6 passed
```

Package build:

```text
python -m build: passed
twine check dist/*: passed
```

Wheel installation:

```text
pip install dist/fetchm2-0.1.0-py3-none-any.whl: passed
```

Wheel smoke test:

```text
metadata command: production gate PASS
sequence check-only: selected 1 accession, wrote failed_accessions.txt as expected
```

Live NCBI smoke test:

```text
Input: first two rows from public FetchM test.tsv
BioSample records requested: 1 unique BioSample
Result: metadata command completed and production gate PASS
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

FetchM2 is ready for an initial `0.1.0` GitHub/PyPI release as a standalone alpha package.

Known scope limits for `0.1.0`:

- host lineage is bundled for common hosts and optionally enriched with `taxonkit` when installed
- figures are not yet as extensive as FetchM Web dashboards
- embeddings/BGE are intentionally not used in production standardization
- large-scale sequence download was not run during this validation to avoid unnecessary NCBI load
