# FetchM2 Validation Report

Validation date: 2026-05-05
Current validation target: `fetchm2 0.1.5`

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
| `collection_date_reviewed_rules.csv` | 0 reviewed rows |
| `country_mapping.json` | 202 countries/regions |

## Commands Validated

The following commands were validated in isolated environments:

```bash
fetchm2 --version
fetchm2 metadata --input examples/offline_metadata.tsv --outdir /tmp/fetchm2_smoke --offline
fetchm2 audit --input /tmp/fetchm2_smoke/metadata_output/fetchm2_clean.csv --outdir /tmp/fetchm2_smoke_audit
fetchm2 validate --input /tmp/fetchm2_smoke/metadata_output/fetchm2_clean.csv --outdir /tmp/fetchm2_smoke_validation
fetchm2 seq --input /tmp/fetchm2_smoke/metadata_output/fetchm2_clean.csv --outdir /tmp/fetchm2_smoke_seq --country Bangladesh --check-only
```

## Test Results

Regression tests:

```text
11 passed
```

Package build for `0.1.2`:

```text
python -m build: passed
twine check dist/*: passed
```

Wheel installation for `0.1.2`:

```text
pip install fetchm2-0.1.2-py3-none-any.whl: passed
fetchm2 --version: fetchm2 0.1.2
```

Wheel smoke test for `0.1.2`:

```text
metadata command: production gate PASS
metadata analysis outputs: generated
validate command: production gate PASS
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

## Additional 0.1.2 CLI Hardening Validation

The 0.1.2 development update adds:

- `fetchm2 validate`
- `production_readiness_gate.md`
- `production_readiness_gate.json`
- issue-specific validation CSVs for country, collection year, sample/source/host leakage, broad vocabulary, missing columns, and sequence readiness
- `Host_Context_SD`
- packaged `collection_date_reviewed_rules.csv` support
- final terminal summaries after `metadata`, `run`, `audit`, and `validate`
- `sequence_download_summary.csv` in `--check-only` mode

Local 0.1.2 validation:

```text
pytest: 11 passed
examples/offline_metadata.tsv metadata run: production gate PASS
validate command: production gate PASS
sequence check-only: wrote failed_accessions.txt and sequence_download_summary.csv
```

Live 20-row `test.tsv` validation under 0.1.2:

```text
Rows scanned: 20
Metadata fetch status: 20 ok
Metadata fetch errors: 0
Production gate: PASS
Host TaxID mapped: 14 / 20 (70.0%)
Country present: 14 / 20 (70.0%)
Collection year present: 18 / 20 (90.0%)
Invalid host-like Sample_Type_SD rows: 0
Non-country values in Country rows: 0
Country-continent mismatch rows: 0
Country-subcontinent mismatch rows: 0
Invalid/future Collection_Year rows: 0
Unapproved broad-category rows: 0
Metadata analysis figures generated: 47
```

Live full `test.tsv` validation under 0.1.2:

```text
Rows scanned: 200
Production gate: PASS
Host TaxID mapped: 92 / 200 (46.0%)
Host review needed: 54
Country present: 178 / 200 (89.0%)
Collection year present: 196 / 200 (98.0%)
Sample_Type_SD present: 66 / 200 (33.0%)
Isolation_Source_SD present: 28 / 200 (14.0%)
Isolation_Site_SD present: 46 / 200 (23.0%)
Environment_Medium_SD present: 10 / 200 (5.0%)
Invalid host-like Sample_Type_SD rows: 0
Non-country values in Country rows: 0
Country-continent mismatch rows: 0
Country-subcontinent mismatch rows: 0
Invalid/future Collection_Year rows: 0
Unapproved Isolation_Source_SD_Broad rows: 0
Unapproved broad-category rows: 0
Source-like mapped host rows: 6
Source-like unmapped host rows: 8
Sequence-readiness issue rows: 0
```

Known scope notes for `0.1.2`:

- host lineage is bundled for common hosts and optionally enriched with `taxonkit` when installed
- embeddings/BGE are intentionally not used in production standardization
- large-scale sequence download was not run during this validation to avoid unnecessary NCBI load

## Additional 0.1.3 Documentation Validation

The 0.1.3 patch updates the README installation command to use the pinned current PyPI release:

```bash
pip install fetchm2==0.1.3
```

No runtime behavior changed from 0.1.2.

## Additional 0.1.4 Sequence Download Validation

The 0.1.4 patch fixes a sequence-download cache issue found during remote-user-style testing.

Remote-user-style `0.1.3` validation:

```text
Fresh PyPI install: passed
fetchm2 --version: fetchm2 0.1.3
Live metadata run: production gate PASS
Sequence selection: selected 2 genomes
Sequence download: failed 2 / 2
Failure reason: SQLite sequence cache connection was created on the main thread and used inside download worker threads
```

0.1.4 fix:

```text
DirectoryCache now opens SQLite with check_same_thread=False
DirectoryCache serializes cache reads/writes with a lock
Added threaded DirectoryCache regression test
pytest: 12 passed
```

Patched local real-download validation:

```text
Command: fetchm2 seq --input fetchm2_clean.csv --outdir /tmp/fetchm2_fixed_real_seq_download --max-genomes 2 --download-workers 1 --retries 2 --retry-delay 1
Sequences selected: 2
Sequences downloaded: 2
Sequences failed: 0
Downloaded files:
- GCA_006094395.1_ASM609439v1_genomic.fna
- GCF_006094395.1_ASM609439v1_genomic.fna
```

## Additional 0.1.5 FetchM Compatibility Validation

The 0.1.5 patch aligns FetchM2 clean-output behavior with original FetchM.

Compatibility behavior:

```text
BioSample metadata fetch unit: unique BioSample accession
Clean output unit: one representative row per Assembly Name
Representative priority: GCF_* over GCA_*
Full row-preserving output: metadata_output/fetchm2_all_assemblies.csv
Override: --keep-assembly-duplicates
```

Validation on bundled `test.tsv`:

```text
Input rows: 200
Unique Assembly Name values: 100
fetchm2_all_assemblies.csv rows: 200
fetchm2_clean.csv rows by default: 100
fetchm2_clean.csv Assembly Accession prefix: all GCF_ in the paired test dataset
--keep-assembly-duplicates clean rows: 200
pytest: 15 passed
```

The BioSample fallback cache was also hardened:

```text
Direct incomplete BioSample XML no longer overwrites recovered fallback metadata in cache.
Recovered esummary XML is cached and reused on subsequent calls without refetching.
```
