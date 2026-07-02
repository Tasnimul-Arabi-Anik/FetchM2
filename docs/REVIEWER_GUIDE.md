# FetchM2 Reviewer Guide

This guide is for reviewers who need to verify FetchM2 as a standalone command-line tool without relying on FetchM WEB, a web server, or production databases.

## Scope

FetchM2 is a bacterial genome metadata standardization and sequence-download CLI. It is intended to:

- read NCBI Genome Datasets TSV/CSV exports or query NCBI Datasets by bacterial taxon name;
- retrieve BioSample metadata when network access is available;
- standardize host, source, sample, environment, geography, disease, health-state, and collection-year fields with packaged deterministic rules;
- generate audit, validation, metadata-analysis, and sequence-download outputs;
- support filtered sequence download with all, seeded-random, and exact manual subset selection.

FetchM2 is not FetchM WEB. It does not include a database-backed web UI, Global Insights pages, deployment services, or web-only dashboards.

## One-Command Local Review

From a developer checkout:

```bash
python -m pip install -e ".[dev]"
./scripts/review_check.sh
```

The script runs entirely from bundled examples and local test data. It does not contact NCBI.

It verifies:

- package import and CLI version;
- all command help surfaces;
- unit and regression tests;
- Python byte-compilation;
- offline metadata standardization;
- validation gate generation;
- metadata analysis generation;
- random sequence subset selection in `--check-only` mode;
- manual accession subset selection in `--check-only` mode;
- presence of the main output artifacts.

By default, the script writes temporary outputs to `/tmp`. To preserve outputs in a chosen directory:

```bash
FETCHM2_REVIEW_WORKDIR=/tmp/fetchm2_review ./scripts/review_check.sh
```

## Expected Local Validation Result

For FetchM2 `0.1.10`, the current local validation baseline is:

```text
pytest -q: 27 passed
targeted sequence subset tests: 4 passed
python -m py_compile src/fetchm2/*.py tests/*.py: passed
fetchm2 --version: fetchm2 0.1.10
offline metadata smoke: production gate PASS
validate command smoke: production gate PASS
sequence subset check-only smoke: selected-accession manifests generated
```

Network-dependent checks, such as taxon-name retrieval and BioSample fetching, are intentionally not part of the default reviewer script. They depend on NCBI availability, local rate limits, and whether an API key is supplied.

## Optional Live NCBI Smoke Test

When network access is available and NCBI request load is acceptable, reviewers can run a small live check:

```bash
fetchm2 metadata \
  --taxon "Klebsiella pneumoniae" \
  --max-assemblies 3 \
  --outdir /tmp/fetchm2_live_taxon_smoke \
  --offline \
  --no-analysis
```

This uses the NCBI Datasets CLI to generate a small assembly table, then runs FetchM2 in offline mode on that table. To fetch BioSample metadata as well, omit `--offline` and use conservative request pacing:

```bash
fetchm2 metadata \
  --taxon "Klebsiella pneumoniae" \
  --max-assemblies 3 \
  --outdir /tmp/fetchm2_live_biosample_smoke \
  --workers 3 \
  --sleep 0.4 \
  --no-analysis
```

## Reviewer Checklist

- `fetchm2 --version` reports the expected release version.
- `pytest -q` passes.
- `./scripts/review_check.sh` completes successfully.
- `metadata_output/fetchm2_clean.csv` is created.
- `audit/production_readiness_gate.json` is created and reports no hard failures for the bundled offline example.
- `sequence_selection_summary.json` and `selected_accessions.txt` are created for subset sequence checks.
- No API keys, caches, temporary outputs, or downloaded sequence files are committed.

## Current Boundaries

- FetchM2 targets bacterial genome metadata. Other domains may run through the parser, but biological semantics outside bacteria are not currently guaranteed.
- Production standardization uses packaged deterministic rules. Embeddings and approximate matching are not used for production writes.
- Sequence downloads use NCBI assembly FTP paths from the input metadata. `--check-only` validates selection and manifests without downloading FASTA files.
- Manual sequence selection uses exact GCA/GCF accessions. It does not silently treat paired GCA/GCF records as interchangeable.
