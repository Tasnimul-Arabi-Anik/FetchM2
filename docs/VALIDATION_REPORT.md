# FetchM2 Validation Report

Validation date: 2026-05-06
Current validation target: `fetchm2 0.1.8`

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
| `country_mapping.json` | 238 countries/territories/marine regions |

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
18 passed
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

## Additional 0.1.6 Geography and Alias Parity Validation

The 0.1.6 update improves standalone parity with the active FetchM Web deterministic metadata standardization layer while keeping FetchM2 CLI-only.

Geography parity changes:

```text
country_mapping.json entries: 202 -> 238
Territory labels added: Puerto Rico, Greenland, French Guiana, Guadeloupe, New Caledonia, French Polynesia, Bermuda, Cayman Islands, Macau, and related entries
Marine region labels added: Arctic Ocean, Atlantic Ocean, Pacific Ocean, Indian Ocean, Southern Ocean, Mediterranean Sea, Baltic Sea, North Sea, Tasman Sea, and related entries
Geography traceability columns added: Country_Source, Country_Confidence, Country_Evidence, Geo_Recovery_Status
```

Web-style standalone input aliases added:

```text
BioSample Host / BioSample Specific Host / BioSample NAT Host / BioSample LAB Host
BioSample Collection Timestamp / BioSample Collection Date Remark / BioSample Isolation Date
BioSample Geographic Location Country AND OR SEA / BioSample Geographic Location Country AND OR SEA Region
BioSample Isolation Source / BioSample Isolation Site / BioSample Source Material ID
Environment (Broad Scale) / Environment (Local Scale)
BioSample Host Disease / BioSample Host Health State
```

0.1.6 local validation:

```text
pytest: 18 passed
python -m build: passed
twine check dist/fetchm2-0.1.6*: passed
fresh wheel install: passed
fetchm2 --version from installed wheel: fetchm2 0.1.6
examples/offline_metadata.tsv metadata run: production gate PASS
validate command: production gate PASS
sequence check-only: selected 1 Bangladesh row and completed without network download
```

0.1.6 regression coverage includes:

```text
Puerto Rico -> Continent=North America, Subcontinent=Caribbean
Greenland -> Continent=North America, Subcontinent=Northern America
Mediterranean Sea -> Continent=Marine, Subcontinent=Sea
Arctic Ocean sediment -> Country=Arctic Ocean, Continent=Marine, Subcontinent=Ocean
Boston Harbor Massachusetts, United States isolation source -> Country=United States by reviewed secondary recovery
ground turkey / guinea pig / Norway rat / Aspergillus niger / Deschampsia antarctica are blocked as geography false positives
Web-style BioSample alias columns are standardized without requiring FetchM Web
```

## Additional 0.1.7 Downstream Pipeline Contract Validation

The 0.1.7 update hardens FetchM2 as a drop-in metadata producer for FetchM-style downstream pipelines, PanR2, and PanResistome.

New stable metadata outputs:

```text
metadata_output/sample_map.csv
metadata_output/metadata_completeness.csv
metadata_output/metadata_bias_warning.txt
metadata_output/fetchm2_manifest.json
metadata_output/ncbi_clean.csv
metadata_output/fetchm2_clean_compat.csv
```

Guaranteed `fetchm2_clean.csv` compatibility columns:

```text
Assembly Accession
Assembly Name
Assembly BioSample Accession
Organism Name
Geographic Location
Continent
Subcontinent
Collection Date
Collection_Year
Host
Host_SD
Isolation_Source
Isolation_Source_SD
Sample_Type_SD
Environment_Medium_SD
```

0.1.7 local validation:

```text
pytest: 18 passed
python -m build: passed
twine check dist/fetchm2-0.1.7*: passed
fresh wheel install: passed
fetchm2 --version from installed wheel: fetchm2 0.1.7
examples/offline_metadata.tsv metadata run: production gate PASS
metadata_output/sample_map.csv: generated
metadata_output/metadata_completeness.csv: generated
metadata_output/metadata_bias_warning.txt: generated
metadata_output/fetchm2_manifest.json: generated with fetchm2_version=0.1.7
metadata_output/ncbi_clean.csv: generated
metadata_output/fetchm2_clean_compat.csv: generated
sequence check-only: generated stable sequence_download_summary.csv columns
installed-wheel smoke: no missing PanR2/PanResistome contract columns
```

Stable sequence summary columns:

```text
Assembly Accession
Assembly Name
BioSample
selected_for_download
download_status
sequence_file
failure_reason
ftp_path
```

Compatibility behavior retained:

```text
Assembly accession versions are preserved.
fetchm2_clean.csv remains one representative row per Assembly Name by default.
GCF_* is preferred over paired GCA_* accessions.
fetchm2_all_assemblies.csv preserves all standardized assembly rows.
BioSample metadata is fetched once per unique BioSample and applied back to assembly rows.
```

## Additional 0.1.7 CI and Release-Hardening Validation

Validation date: 2026-05-09

Added GitHub Actions CI:

```text
Python versions: 3.10, 3.11, 3.12
Install command: python -m pip install -e ".[dev]"
Test command: pytest
Build command: python -m build
Distribution check: python -m twine check dist/*
```

Local release-hardening validation:

```text
python -m pip install -e ".[dev]": passed
fetchm2 --version: fetchm2 0.1.7
pytest: 18 passed
python -m build: passed
python -m twine check dist/*: passed
offline metadata smoke: production gate PASS
validate command smoke: production gate PASS
sequence check-only smoke: selected 1 Bangladesh row and completed without sequence download
```

Post-push GitHub Actions validation:

```text
Commit: f02d1dd Add CI release validation workflow
Workflow run: 25607936518
Status: success
Python 3.10 test job: success
Python 3.11 test job: success
Python 3.12 test job: success
Build package job: success
```

Live NCBI smoke validation:

```text
Command: fetchm2 metadata --input test.tsv --outdir /tmp/fetchm2_live_smoke --workers 3 --sleep 0.4
Rows processed: 100
BioSample-linked rows: 100
Unique BioSamples represented: 100
Metadata fetch failed rows: 0
Production gate: PASS
Hard failures: none
Warnings: host_taxid_percent=47.0
Host TaxID mapped: 47 / 100 (47.0%)
Host review needed: 27
Country present: 90 / 100 (90.0%)
Collection year present: 98 / 100 (98.0%)
Sample_Type_SD present: 33 / 100 (33.0%)
Isolation_Source_SD present: 14 / 100 (14.0%)
Isolation_Site_SD present: 23 / 100 (23.0%)
Environment_Medium_SD present: 5 / 100 (5.0%)
Invalid host-like Sample_Type_SD rows: 0
Non-country values in Country rows: 0
Country-continent mismatch rows: 0
Country-subcontinent mismatch rows: 0
Invalid/future Collection_Year rows: 0
Unapproved broad-category rows: 0
Sequence-readiness issue rows: 0
```

PyPI post-release validation:

```text
PyPI version: fetchm2 0.1.7
Fresh environment: /tmp/fetchm2_pypi_017_env
Install command: python -m pip install fetchm2==0.1.7
Installed CLI version: fetchm2 0.1.7
Offline metadata smoke: production gate PASS
Validate command smoke: production gate PASS
Sequence check-only smoke: selected 1 Bangladesh row and completed without sequence download
```

## Additional 0.1.8 Taxon-Name Input Validation

Validation date: 2026-05-10

The 0.1.8 update adds standalone species/genus input support while preserving the existing NCBI TSV/CSV input workflow.

Implemented behavior:

```text
fetchm2 metadata --taxon "Klebsiella pneumoniae" --outdir results
fetchm2 run --taxon "Klebsiella pneumoniae" --outdir results --download
fetchm2 run --input "Klebsiella pneumoniae" --outdir results --download
```

Validation performed:

```text
python -m pytest: 19 passed
python -m fetchm2 --help: passed
python -m fetchm2 metadata --help: passed; shows --taxon, --assembly-source, --max-assemblies, --tax-exact-match
Mocked NCBI Datasets taxon query test: passed
Live NCBI Datasets taxon smoke: passed
```

Live smoke command:

```bash
python -m fetchm2 metadata --taxon "Klebsiella pneumoniae" --outdir /tmp/fetchm2_taxon_smoke --offline --no-analysis --max-assemblies 3
```

Live smoke result:

```text
Rows processed: 3
Unique Assembly Accession values: 3
BioSample-linked rows: 3
Unique BioSamples represented: 3
Production gate: PASS
Generated taxon table: /tmp/fetchm2_taxon_smoke/metadata_output/ncbi_dataset.tsv
Generated clean table: /tmp/fetchm2_taxon_smoke/metadata_output/fetchm2_clean.csv
```

The generated table preserved versioned accessions:

```text
GCF_000364385.3 Klebsiella pneumoniae
GCF_000689275.1 Klebsiella pneumoniae
GCF_000710075.1 Klebsiella pneumoniae
```

Important implementation note:

```text
--max-assemblies is passed upstream to NCBI Datasets as --limit, so large genus/species queries do not need to wait for all records before FetchM2 can cap the result set.
```

0.1.8 release-package validation:

```text
python -m build: passed
python -m twine check dist/fetchm2-0.1.8*: passed
fresh wheel install: passed
fetchm2 --version from installed wheel: fetchm2 0.1.8
python -m fetchm2 --help from installed wheel: passed
offline metadata smoke from installed wheel: production gate PASS
validate command smoke from installed wheel: production gate PASS
```
