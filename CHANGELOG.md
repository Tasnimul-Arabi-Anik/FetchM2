# Changelog

All notable FetchM2 release changes are recorded here.

FetchM2 is a standalone CLI successor to FetchM. It packages expanded deterministic metadata standardization, metadata analysis, audit/validation reporting, and sequence-download filtering into a terminal workflow.

## 0.1.3 - 2026-05-05

### Changed

- Pinned the README installation example to the current PyPI release:

```bash
pip install fetchm2==0.1.3
```

- Updated package version metadata to `0.1.3`.

### Validation

- Runtime behavior is unchanged from the validated `0.1.2` release.
- Fresh PyPI install was verified with:

```bash
pip install fetchm2==0.1.3
fetchm2 --version
fetchm2 metadata --input examples/offline_metadata.tsv --outdir /tmp/fetchm2_pypi_013_smoke --offline
```

## 0.1.2 - 2026-05-05

### Added

- Added `fetchm2 validate` for CLI production-readiness checks.
- Added production gate outputs:
  - `audit/production_readiness_gate.md`
  - `audit/production_readiness_gate.json`
- Added issue-specific audit CSVs for:
  - non-country values in `Country`
  - country/continent and country/subcontinent mismatches
  - invalid or future collection years
  - host-like values leaking into `Sample_Type_SD`
  - source-like host review queues
  - broad vocabulary leakage
  - sequence-readiness issues
- Added `Host_Context_SD`.
- Added packaged support for `collection_date_reviewed_rules.csv`.
- Added concise terminal summaries after `metadata`, `run`, `audit`, and `validate`.
- Added `sequence_download_summary.csv` output for sequence `--check-only` mode.

### Validation

- `pytest`: `11 passed`
- Package build and `twine check`: passed.
- Offline metadata smoke test: production gate `PASS`.
- `fetchm2 validate`: production gate `PASS`.
- Sequence check-only smoke test: completed and wrote summary outputs.
- Full live `test.tsv` validation:
  - rows scanned: `200`
  - production gate: `PASS`
  - Host TaxID mapped: `92 / 200 (46.0%)`
  - host review needed: `54`
  - country present: `178 / 200 (89.0%)`
  - collection year present: `196 / 200 (98.0%)`
  - invalid host-like `Sample_Type_SD` rows: `0`
  - non-country values in `Country`: `0`
  - country-continent mismatch rows: `0`
  - country-subcontinent mismatch rows: `0`
  - invalid/future `Collection_Year` rows: `0`
  - unapproved broad-category rows: `0`
  - sequence-readiness issue rows: `0`

### Scope

- Embeddings/BGE are intentionally not used for production standardization.
- Large-scale sequence download was not run during validation to avoid unnecessary NCBI load.

## 0.1.1 - 2026-05-05

### Added

- Added top-level `test.tsv`.
- Added conda environment support through `environment.yml`.
- Added automatic `metadata_analysis/` outputs.
- Added `fetchm2 analyze`.
- Expanded BioSample parsing for direct `BioSample`, `BioSampleSet`, raw attribute tracking, matched attribute tracking, and `esummary` fallback.
- Added shared NCBI request throttling, retry, and backoff behavior.
- Added cached BioSample retrieval with explicit fetch status, reason, and error columns.

### Validation

- Local tests: `7 passed`.
- Offline `test.tsv` metadata run: production gate `PASS`.
- Live 20-row `test.tsv` validation:
  - rows scanned: `20`
  - production gate: `PASS`
  - Host TaxID mapped: `14 / 20 (70.0%)`
  - country present: `14 / 20 (70.0%)`
  - collection year present: `18 / 20 (90.0%)`
  - invalid host-like `Sample_Type_SD` rows: `0`
  - non-country values in `Country`: `0`
  - unapproved `Isolation_Source_SD_Broad` rows: `0`
- Full live `test.tsv` validation:
  - rows scanned: `200`
  - BioSample rows fetched: `200 / 200`
  - metadata fetch errors: `0`
  - production gate: `PASS`
  - Host TaxID mapped: `92 / 200 (46.0%)`
  - host review needed: `54`
  - country present: `178 / 200 (89.0%)`
  - collection year present: `196 / 200 (98.0%)`

## 0.1.0 - 2026-05-05

### Added

- Initial standalone FetchM2 CLI release.
- Added commands for metadata processing, audit reporting, analysis, and sequence download.
- Packaged deterministic rule resources for host, source/sample/environment, geography, broad categories, and country mapping.
- Added README, validation documentation, sequence-download documentation, metadata-analysis documentation, and release checklist.

