# FetchM2 Sequence Download

FetchM2 downloads genome FASTA files from the public NCBI genomes FTP layout using the assembly accession and assembly name in `fetchm2_clean.csv`.

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
- `--max-genomes`

## Check Only

Use `--check-only` to compare expected accessions against an output directory without downloading:

```bash
fetchm2 seq --input fetchm2_clean.csv --outdir sequence --check-only
```
