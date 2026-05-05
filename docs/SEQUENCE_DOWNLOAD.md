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
- `--max-genomes`

## Check Only

Use `--check-only` to compare expected accessions against an output directory without downloading:

```bash
fetchm2 seq --input fetchm2_clean.csv --outdir sequence --check-only
```
