# FetchM2 Sequence Download

FetchM2 downloads genome FASTA files from the public NCBI genomes FTP layout using the assembly accession and assembly name in `fetchm2_clean.csv`.

By default, `fetchm2_clean.csv` contains one representative row per `Assembly Name`, preferring RefSeq `GCF_*` over GenBank `GCA_*` when paired rows share the same assembly name. This follows original FetchM behavior and prevents duplicate downloads/counting for paired GCA/GCF assemblies. If you need all input assembly rows, use `fetchm2_all_assemblies.csv` or rerun metadata with `--keep-assembly-duplicates`.

## Typical Workflow

```bash
fetchm2 metadata --input ncbi_dataset.tsv --outdir results
fetchm2 seq --input results/metadata_output/fetchm2_clean.csv --outdir results/sequence
```

## Filtered Download

You can filter using standardized metadata:

```bash
fetchm2 seq \
  --input results/metadata_output/fetchm2_clean.csv \
  --outdir results/sequence_human_bd \
  --host "Homo sapiens" \
  --country Bangladesh \
  --year-from 2018 \
  --year-to 2024
```

Supported filters include:

- `--host`
- `--host-rank`
- `--country`
- `--continent`
- `--subcontinent`
- `--sample-type`
- `--isolation-source`
- `--environment-medium`
- `--year-from` and `--year-to`
- `--max-genomes` for the legacy first-N cap after filtering
- `--subset-mode all|random|manual`
- `--subset-count` and `--subset-seed` for reproducible random subsets
- `--accessions` and `--accessions-file` for exact manual accession subsets

## Subset Selection

By default, FetchM2 keeps the previous behavior and selects all filtered rows, or the first `--max-genomes` rows when that legacy cap is supplied. For a reproducible random subset, use:

```bash
fetchm2 seq \
  --input results/metadata_output/fetchm2_clean.csv \
  --outdir results/sequence_random_bd \
  --country Bangladesh \
  --subset-mode random \
  --subset-count 25 \
  --subset-seed 20260701
```

For an exact manual subset after all metadata filters are applied:

```bash
fetchm2 seq \
  --input results/metadata_output/fetchm2_clean.csv \
  --outdir results/sequence_manual \
  --country Bangladesh \
  --subset-mode manual \
  --accessions GCA_000000001.1 GCF_000000002.1
```

Manual accessions can also be supplied from a file with `--accessions-file`. Files may use newlines, spaces, commas, or semicolons. Accessions are matched exactly after case normalization; `GCA_*` and `GCF_*` are not treated as interchangeable. Duplicate, missing, invalid, and selected counts are reported in `sequence_selection_summary.json`.

## Check Only

Use `--check-only` to compare expected accessions against an output directory without downloading:

```bash
fetchm2 seq --input fetchm2_clean.csv --outdir sequence --check-only
```

## Stable Summary Output

FetchM2 always writes:

- `sequence_download_summary.csv`
- `sequence_selection_summary.json`
- `selected_accessions.txt`
- `failed_accessions.txt`

`sequence_download_summary.csv` includes these stable downstream matching columns:

- `Assembly Accession`
- `Assembly Name`
- `BioSample`
- `selected_for_download`
- `download_status`
- `sequence_file`
- `failure_reason`
- `ftp_path`

`selected_accessions.txt` records the exact selected accession list, and `sequence_selection_summary.json` records its SHA-256 checksum plus subset-mode counts without embedding the full accession list in JSON.

The `sequence_file` value matches the expected FASTA basename used by FetchM2. Assembly accession versions are preserved so downstream tools can match ABRicate, MLST, MobileElementFinder, IntegronFinder, DefenseFinder, PanR2, and PanResistome outputs by `Assembly Accession` or by `sample_id` from `metadata_output/sample_map.csv`.
