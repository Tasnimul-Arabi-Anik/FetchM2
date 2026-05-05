# FetchM2

FetchM2 is a standalone command-line toolkit for genome metadata retrieval, comprehensive metadata standardization, audit reporting, and optional sequence download.

It keeps the simple standalone installation model of the original public [`FetchM`](https://github.com/Tasnimul-Arabi-Anik/FetchM), while packaging deterministic rule files and QA concepts developed in FetchM Web.

## What FetchM2 Does

- Reads NCBI Genome Datasets TSV/CSV exports.
- Optionally fetches linked BioSample metadata from NCBI.
- Standardizes host, country/geography, collection year, sample type, isolation source, isolation site, environment medium, host disease, and host health state.
- Adds host TaxID, rank, lineage fields, match method, confidence, and review status.
- Writes clean metadata tables and audit reports.
- Downloads genome FASTA files from NCBI with flexible filters.
- Runs offline on already annotated tables for reproducible tests and local standardization.

## Installation

Recommended clean environment:

```bash
python -m venv fetchm2-env
source fetchm2-env/bin/activate
pip install fetchm2
```

For development from source:

```bash
git clone https://github.com/Tasnimul-Arabi-Anik/FetchM2.git
cd FetchM2
python -m pip install -e ".[dev]"
pytest
```

FetchM2 uses Python dependencies only. `taxonkit` is optional. If available, FetchM2 can use it to enrich less common host TaxIDs with lineage fields; common host lineages are bundled.

## Quick Start

Offline smoke test using the bundled example:

```bash
fetchm2 metadata --input examples/offline_metadata.tsv --outdir demo_out --offline
```

Full BioSample metadata retrieval:

```bash
fetchm2 metadata --input ncbi_dataset.tsv --outdir results
```

With NCBI API key:

```bash
export NCBI_API_KEY=YOUR_NCBI_API_KEY
fetchm2 metadata --input ncbi_dataset.tsv --outdir results --workers 6 --sleep 0.15
```

All-in-one metadata plus sequence download:

```bash
fetchm2 run --input ncbi_dataset.tsv --outdir results --download
```

Filtered sequence download from a clean table:

```bash
fetchm2 seq \
  --input results/metadata_output/fetchm2_clean.csv \
  --outdir results/sequence \
  --host "Homo sapiens" \
  --country Bangladesh \
  --year-from 2018 \
  --year-to 2024
```

## Main Commands

```bash
fetchm2 metadata --help
fetchm2 run --help
fetchm2 seq --help
fetchm2 audit --help
```

## Metadata Outputs

FetchM2 writes:

- `metadata_output/fetchm2_clean.csv`
- `metadata_output/fetchm2_clean.tsv`
- `metadata_output/fetchm2_report.md`
- `audit/standardization_summary.csv`
- `audit/top_host_review_needed.csv`
- `audit/standardization_audit.md`

Important standardized fields include:

- `Host_SD`, `Host_TaxID`, `Host_Rank`, `Host_Superkingdom`, `Host_Phylum`, `Host_Class`, `Host_Order`, `Host_Family`, `Host_Genus`, `Host_Species`
- `Host_Common_Name`, `Host_Match_Method`, `Host_Confidence`, `Host_Review_Status`
- `Sample_Type_SD`, `Sample_Type_SD_Broad`
- `Isolation_Source_SD`, `Isolation_Source_SD_Broad`
- `Isolation_Site_SD`
- `Environment_Medium_SD`, `Environment_Medium_SD_Broad`
- `Environment_Broad_Scale_SD`, `Environment_Local_Scale_SD`
- `Host_Disease_SD`, `Host_Health_State_SD`
- `Country`, `Continent`, `Subcontinent`, `Collection_Year`

## Sequence Download Options

FetchM2 supports filtering by:

- host
- host rank
- country
- continent
- subcontinent
- sample type
- isolation source
- environment medium
- collection year range
- maximum genomes

Use `--check-only` to audit a sequence output directory without downloading.

## API Keys

For NCBI, prefer environment variables:

```bash
export NCBI_API_KEY=YOUR_NCBI_API_KEY
export NCBI_EMAIL=you@example.com
```

Do not place API keys in scripts, notebooks, README files, or Git commits.

## Design Compared With FetchM and FetchM Web

FetchM2 uses the original FetchM standalone flow as the command-line baseline:

- metadata
- run
- seq
- SQLite cache
- NCBI BioSample fetch
- sequence download from NCBI FTP

FetchM2 adds FetchM Web-style standardized metadata fields and deterministic rule files:

- host synonyms and negative host rules
- controlled source/sample/environment categories
- approved broad vocabulary
- production-style audit gate
- richer sequence filtering on standardized fields

FetchM2 intentionally does not use embeddings or AI for production mappings. Embeddings can be used later as a review assistant, but final production rules should remain deterministic and auditable.

## Testing

Run:

```bash
pytest
python -m build
python -m pip install dist/fetchm2-*.whl
fetchm2 metadata --input examples/offline_metadata.tsv --outdir smoke_out --offline
fetchm2 seq --input smoke_out/metadata_output/fetchm2_clean.csv --outdir smoke_seq --country Bangladesh --check-only
```

## License

MIT License.
