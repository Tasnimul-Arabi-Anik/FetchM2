# FetchM2

FetchM2 is a comprehensive standalone command-line toolkit for bacterial genome metadata analysis, metadata standardization, audit reporting, and optional genome sequence download.

FetchM2 is designed as the updated successor to the original FetchM standalone tool. It keeps the same practical command-line workflow, but adds many more standardized metadata fields, richer filtering, packaged curation rules, audit outputs, and reproducible test data.

Recommended one-command workflow:

```bash
fetchm2 run --input ncbi_dataset.tsv --outdir results --download
```

## Key Features

- Standalone command-line tool installable with `pip` or a conda environment.
- Reads NCBI Genome Datasets TSV/CSV exports.
- Optionally fetches linked BioSample metadata from NCBI with retry, cache, and fallback lookup support.
- Supports offline analysis when metadata columns are already present.
- Applies packaged deterministic standardization rules.
- Writes clean CSV and TSV metadata outputs.
- Generates metadata analysis tables and figures automatically.
- Produces audit summaries and review queues.
- Downloads genome FASTA files from NCBI.
- Supports flexible sequence-download filtering by standardized metadata.
- Includes `test.tsv`, matching the public FetchM-style test dataset layout.
- Includes `examples/offline_metadata.tsv` for fast local smoke testing.

## Installation

### Option 1: pip

```bash
python -m venv fetchm2-env
source fetchm2-env/bin/activate
pip install fetchm2==0.1.5
```

Verify:

```bash
fetchm2 --version
```

### Option 2: conda / mamba environment

Clone the repository and create the environment:

```bash
git clone https://github.com/Tasnimul-Arabi-Anik/FetchM2.git
cd FetchM2
mamba env create -f environment.yml
conda activate fetchm2
```

If you use `conda` instead of `mamba`:

```bash
conda env create -f environment.yml
conda activate fetchm2
```

The conda environment includes `taxonkit`, which can improve host lineage enrichment for less common TaxIDs. FetchM2 still works without `taxonkit`; common host lineages are bundled.

### Option 3: developer install

```bash
git clone https://github.com/Tasnimul-Arabi-Anik/FetchM2.git
cd FetchM2
python -m pip install -e ".[dev]"
pytest
```

## Quick Start

Run the bundled standalone smoke test:

```bash
fetchm2 metadata --input examples/offline_metadata.tsv --outdir demo_out --offline
```

Run the FetchM-style test dataset:

```bash
fetchm2 metadata --input test.tsv --outdir test_out --offline
```

`test.tsv` contains assembly-level NCBI dataset columns and BioSample accessions. In offline mode, FetchM2 analyzes assembly statistics and any metadata already present in the table. To populate host, source, sample, environment, and geography from NCBI BioSample records, run without `--offline`.

Run metadata retrieval with BioSample enrichment:

```bash
fetchm2 metadata --input test.tsv --outdir test_out_live --workers 3 --sleep 0.4
```

Use an NCBI API key for larger jobs:

```bash
export NCBI_API_KEY=YOUR_NCBI_API_KEY
export NCBI_EMAIL=you@example.com
fetchm2 metadata --input ncbi_dataset.tsv --outdir results --workers 6 --sleep 0.15
```

Run metadata standardization and sequence download in one command:

```bash
fetchm2 run --input ncbi_dataset.tsv --outdir results --download
```

## Typical Species/Genus Workflow

1. Download an NCBI Genome Datasets TSV or CSV for your target species or genus.
2. Run FetchM2:

```bash
fetchm2 run --input ncbi_dataset.tsv --outdir results --download
```

3. Review the main outputs:

- `results/metadata_output/fetchm2_clean.csv`
- `results/metadata_output/fetchm2_all_assemblies.csv`
- `results/metadata_analysis/metadata_analysis_report.md`
- `results/audit/standardization_audit.md`
- `results/audit/production_readiness_gate.md`
- `results/sequence/`

For large NCBI retrieval jobs without an API key, use a conservative request delay:

```bash
fetchm2 run --input ncbi_dataset.tsv --outdir results --download --workers 3 --sleep 0.4
```

## Metadata Retrieval Workflow

FetchM2 can work in two modes.

Offline mode:

- Uses metadata columns already present in the input table.
- Applies standardization rules.
- Generates audit and metadata analysis outputs.
- Does not contact NCBI.

Live BioSample mode:

- Reads BioSample accessions from NCBI dataset exports.
- Retrieves BioSample records through NCBI E-utilities.
- Uses direct BioSample XML first, then an `esummary` fallback when the direct record lacks usable attributes.
- Tracks raw BioSample attribute names and matched standardized attribute names.
- Uses a local SQLite cache so repeated runs do not refetch the same BioSample records.
- Uses request throttling, retry, and backoff behavior for temporary NCBI rate-limit or server errors.

Important output columns from retrieval include:

- `BioSample`
- `BioSample Taxonomy Name`
- `Metadata Fetch Status`
- `Metadata Fetch Reason`
- `Metadata Fetch Error`
- `Metadata Raw Attribute Names`
- `Metadata Matched Attribute Names`

FetchM2 currently recognizes common BioSample attribute aliases for host, source, sample type, isolation site, collection date, geography, environmental medium/broad/local scale, host disease, and host health state.

## Main Commands

```bash
fetchm2 metadata --help
fetchm2 run --help
fetchm2 seq --help
fetchm2 audit --help
fetchm2 validate --help
fetchm2 analyze --help
```

### `fetchm2 metadata`

Reads an NCBI dataset TSV/CSV, optionally fetches BioSample metadata, standardizes fields, and writes clean outputs.

Example:

```bash
fetchm2 metadata \
  --input ncbi_dataset.tsv \
  --outdir results \
  --ani OK \
  --checkm 95 \
  --workers 6
```

Common options:

- `--input`: NCBI dataset TSV/CSV.
- `--outdir`: output directory.
- `--ani`: filter by ANI Check status, for example `OK`.
- `--checkm`: minimum CheckM completeness.
- `--api-key`: NCBI API key; can also use `NCBI_API_KEY`.
- `--email`: NCBI email; can also use `NCBI_EMAIL`.
- `--workers`: BioSample fetch worker count.
- `--sleep`: shared request delay between NCBI calls. Use a slower value such as `0.4` to `0.5` for unauthenticated larger jobs.
- `--offline`: skip NCBI fetching and standardize existing columns only.
- `--no-analysis`: skip automatic `metadata_analysis/` table and figure generation.

### `fetchm2 run`

Runs metadata analysis and, if requested, sequence download.

```bash
fetchm2 run \
  --input ncbi_dataset.tsv \
  --outdir results \
  --ani OK \
  --checkm 95 \
  --download \
  --country Bangladesh \
  --host "Homo sapiens" \
  --year-from 2018 \
  --year-to 2024
```

### `fetchm2 seq`

Downloads genome FASTA files using the standardized clean metadata table.

```bash
fetchm2 seq \
  --input results/metadata_output/fetchm2_clean.csv \
  --outdir results/sequence \
  --host "Homo sapiens" \
  --country Bangladesh \
  --year-from 2018 \
  --year-to 2024
```

Check expected sequences without downloading:

```bash
fetchm2 seq \
  --input results/metadata_output/fetchm2_clean.csv \
  --outdir results/sequence \
  --country Bangladesh \
  --check-only
```

### `fetchm2 audit`

Audits an existing standardized output:

```bash
fetchm2 audit \
  --input results/metadata_output/fetchm2_clean.csv \
  --outdir results/audit_rerun
```

### `fetchm2 validate`

Runs the same production-readiness checks as `audit`, but names the workflow explicitly for CLI validation:

```bash
fetchm2 validate \
  --input results/metadata_output/fetchm2_clean.csv \
  --outdir results/validation
```

### `fetchm2 analyze`

Generates metadata analysis outputs from any existing clean metadata CSV.

```bash
fetchm2 analyze \
  --input results/metadata_output/fetchm2_clean.csv \
  --outdir results/metadata_analysis_rerun \
  --top-n 30
```

## Metadata Outputs

FetchM2 writes:

- `metadata_output/fetchm2_clean.csv`
- `metadata_output/fetchm2_clean.tsv`
- `metadata_output/fetchm2_report.md`
- `audit/standardization_summary.csv`
- `audit/top_host_review_needed.csv`
- `audit/standardization_audit.md`
- `metadata_analysis/metadata_analysis_report.md`
- `metadata_analysis/tables/field_coverage_summary.csv`
- `metadata_analysis/tables/top_values_by_field.csv`
- `metadata_analysis/tables/numeric_summary.csv`
- `metadata_analysis/figures/*.png`

Typical output structure:

```text
results/
├── metadata_output/
│   ├── fetchm2_clean.csv
│   ├── fetchm2_clean.tsv
│   ├── fetchm2_all_assemblies.csv
│   ├── fetchm2_all_assemblies.tsv
│   └── fetchm2_report.md
├── metadata_analysis/
│   ├── metadata_analysis_report.md
│   ├── tables/
│   └── figures/
├── audit/
│   ├── standardization_summary.csv
│   ├── standardization_audit.md
│   ├── production_readiness_gate.md
│   ├── production_readiness_gate.json
│   ├── top_host_review_needed.csv
│   ├── non_country_values_in_country.csv
│   ├── country_continent_mismatch.csv
│   ├── country_subcontinent_mismatch.csv
│   ├── invalid_collection_years.csv
│   ├── invalid_host_like_sample_type.csv
│   ├── source_like_mapped_hosts.csv
│   ├── source_like_unmapped_hosts_for_review.csv
│   ├── broad_vocabulary_leakage.csv
│   ├── sequence_readiness.csv
│   └── rule_count_summary.csv
└── sequence/
    ├── *.fna
    ├── failed_accessions.txt
    ├── sequence_download_summary.csv
    └── fetchm2_sequence_cache.sqlite3
```

By default, `fetchm2_clean.csv` follows original FetchM behavior: it selects one representative row per `Assembly Name`, preferring RefSeq `GCF_*` over GenBank `GCA_*` when both are present. This prevents paired GCA/GCF assemblies sharing the same BioSample from being double-counted in downstream prevalence analyses. The full row-preserving output is still saved as `fetchm2_all_assemblies.csv`.

If you intentionally want paired GCA/GCF rows retained in `fetchm2_clean.csv`, use:

```bash
fetchm2 metadata --input ncbi_dataset.tsv --outdir results --keep-assembly-duplicates
```

## Standardized Metadata Fields

FetchM2 keeps the original input columns and adds standardized fields.

### Host Standardization

Original FetchM had host-oriented metadata summaries. FetchM2 expands this into detailed host standardization:

- `Host_Original`
- `Host_Cleaned`
- `Host_SD`
- `Host_TaxID`
- `Host_Rank`
- `Host_Superkingdom`
- `Host_Phylum`
- `Host_Class`
- `Host_Order`
- `Host_Family`
- `Host_Genus`
- `Host_Species`
- `Host_Common_Name`
- `Host_Context_SD`
- `Host_Match_Method`
- `Host_Confidence`
- `Host_Review_Status`

Examples:

- `human`, `human blood`, `Homosapines` variants can map to `Homo sapiens`, TaxID `9606`.
- `cattle feces` can map to `Bos taurus`, TaxID `9913`, while also preserving feces/stool as sample metadata.
- `bacteria culture`, `DH5a`, lab strain terms, missing values, and source/material terms are blocked from becoming host values.

### Source, Sample, and Environment

FetchM2 standardizes source/sample/environment fields into:

- `Sample_Type_SD`
- `Sample_Type_SD_Broad`
- `Isolation_Source_SD`
- `Isolation_Source_SD_Broad`
- `Isolation_Site_SD`
- `Environment_Medium_SD`
- `Environment_Medium_SD_Broad`
- `Environment_Broad_Scale_SD`
- `Environment_Local_Scale_SD`

Examples:

- `blood` -> `Sample_Type_SD=blood`
- `urine` -> `Sample_Type_SD=urine`
- `feces`, `faeces`, `stool` -> `Sample_Type_SD=feces/stool`
- `soil` -> `Environment_Medium_SD=soil`
- `sediment` -> `Environment_Medium_SD=sediment`
- `wastewater`, `sewage` -> `Environment_Medium_SD=wastewater/sewage`
- `hospital surface` -> healthcare/source context
- `rectal swab` -> sample type plus anatomical site when available

### Geography and Date

FetchM2 standardizes:

- `Country`
- `Continent`
- `Subcontinent`
- `Collection_Year`

It also blocks common false positives such as:

- `Hospital` as country
- `ground turkey` as Turkey
- `Guinea pig` as Guinea
- `Norway rat` as Norway
- `Aspergillus niger` as Niger

### Disease and Health State

FetchM2 includes:

- `Host_Disease_SD`
- `Host_Health_State_SD`

These are conservative deterministic fields. Disease words are not treated as sample material unless an actual specimen is present.

## Sequence Download Features

FetchM2 downloads genome FASTA files from the NCBI genomes FTP structure using `Assembly Accession` and `Assembly Name`.

When using the default `fetchm2_clean.csv`, sequence download operates on representative assemblies only, matching original FetchM behavior. Use `fetchm2_all_assemblies.csv` or `--keep-assembly-duplicates` only when you deliberately want both paired `GCA_*` and `GCF_*` accessions.

Filtering options:

- `--host`
- `--host-rank`
- `--country`
- `--continent`
- `--subcontinent`
- `--sample-type`
- `--isolation-source`
- `--environment-medium`
- `--year-from`
- `--year-to`
- `--max-genomes`

Download control:

- `--download-workers`
- `--retries`
- `--retry-delay`
- `--keep-gz`
- `--check-only`

Outputs:

- genome FASTA files
- `failed_accessions.txt`
- `sequence_download_summary.csv`
- `fetchm2_sequence_cache.sqlite3`

## Test Dataset

FetchM2 includes:

- `test.tsv`: FetchM-style NCBI dataset example copied from the public FetchM test dataset.
- `examples/test_ncbi_dataset.tsv`: same dataset stored under examples.
- `examples/offline_metadata.tsv`: small annotated metadata table for fast offline testing.

Run:

```bash
fetchm2 metadata --input test.tsv --outdir test_run --offline
fetchm2 audit --input test_run/metadata_output/fetchm2_clean.csv --outdir test_run/audit_check
```

For BioSample metadata retrieval:

```bash
fetchm2 metadata --input test.tsv --outdir test_run_live --workers 3 --sleep 0.34
```

## Rule Files Packaged With FetchM2

FetchM2 ships deterministic rules in `src/fetchm2/data/`:

- `host_synonyms.csv`
- `host_negative_rules.csv`
- `controlled_categories.csv`
- `approved_broad_categories.csv`
- `geography_reviewed_rules.csv`
- `collection_date_reviewed_rules.csv`
- `country_mapping.json`

These rules let the standalone tool produce richer standardized fields without needing a web database.

## API Keys

For NCBI, use environment variables:

```bash
export NCBI_API_KEY=YOUR_NCBI_API_KEY
export NCBI_EMAIL=you@example.com
```

Do not put API keys in scripts, notebooks, README files, Git commits, or issue reports.

## Validation

Run local validation:

```bash
pytest
python -m build
python -m twine check dist/*
python -m pip install dist/fetchm2-*.whl
fetchm2 metadata --input examples/offline_metadata.tsv --outdir smoke_out --offline
fetchm2 validate --input smoke_out/metadata_output/fetchm2_clean.csv --outdir smoke_out/validation
fetchm2 seq --input smoke_out/metadata_output/fetchm2_clean.csv --outdir smoke_seq --country Bangladesh --check-only
```

The validation report is in:

```text
docs/VALIDATION_REPORT.md
```

More analysis details:

```text
docs/METADATA_ANALYSIS.md
docs/STANDARDIZATION.md
docs/SEQUENCE_DOWNLOAD.md
docs/RELEASE_CHECKLIST.md
```

## License

MIT License.
