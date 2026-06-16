# FetchM2 Metadata Analysis

FetchM2 produces standalone metadata analysis outputs after each `fetchm2 metadata` run unless `--no-analysis` is used.

## Output Directory

For an output directory named `results`, analysis files are written to:

```text
results/metadata_analysis/
```

The directory contains:

```text
metadata_analysis_report.md
tables/field_coverage_summary.csv
tables/top_values_by_field.csv
tables/numeric_summary.csv
figures/*.png
```

The analysis is generated automatically after `fetchm2 metadata` unless `--no-analysis` is used. It can also be regenerated from an existing clean CSV with:

```bash
fetchm2 analyze --input results/metadata_output/fetchm2_clean.csv --outdir results/metadata_analysis_rerun
```

## Raw and Standardized Distributions

FetchM2 analyzes raw and standardized values where available:

| Raw field | Standardized field |
| --- | --- |
| `Host` | `Host_SD` |
| `Geographic Location` | `Country` |
| `Collection Date` | `Collection_Year` |
| `Isolation Source` | `Isolation_Source_SD` |
| `Sample Type` | `Sample_Type_SD` |
| `Isolation Site` | `Isolation_Site_SD` |
| `Environment Medium` | `Environment_Medium_SD` |
| `Host Disease` | `Host_Disease_SD` |
| `Host Health State` | `Host_Health_State_SD` |

If the input table only contains assembly-level columns, raw host/source/geography distributions will be empty in offline mode. Run without `--offline` to fetch linked BioSample metadata from NCBI.

FetchM2 also records retrieval QA fields when BioSample enrichment is used:

- `Metadata Fetch Status`
- `Metadata Fetch Reason`
- `Metadata Fetch Error`
- `Metadata Raw Attribute Names`
- `Metadata Matched Attribute Names`

These fields make it clear which rows were enriched from NCBI, which records required fallback lookup, and whether any rows failed because of network or NCBI response problems.

## Assembly and Annotation Statistics

FetchM2 summarizes and plots common assembly fields:

- `Assembly Stats Total Sequence Length`
- `Assembly Stats Total Number of Chromosomes`
- `Assembly Stats Number of Contigs`
- `Assembly Stats Contig N50`
- `Assembly Stats Scaffold N50`
- `Assembly Stats Number of Scaffolds`
- `Assembly Stats GC Percent`
- `Annotation Count Gene Total`
- `Annotation Count Gene Protein-coding`
- `Annotation Count Gene Pseudogene`
- `CheckM completeness`
- `CheckM contamination`

When `Collection_Year` is available, FetchM2 also creates scatter plots such as sequence length vs collection year and gene count vs collection year.

## Test Dataset Behavior

The top-level `test.tsv` is included for compatibility with the original FetchM-style workflow.

Offline:

```bash
fetchm2 metadata --input test.tsv --outdir test_out --offline
```

This analyzes assembly statistics and fields already present in the file.

Live BioSample enrichment:

```bash
fetchm2 metadata --input test.tsv --outdir test_out_live
```

This fetches BioSample metadata and can populate host, geography, source/sample/environment fields when those attributes exist at NCBI.

## Figures And Geographic Outputs

FetchM2 does not package static FetchM WEB figure assets. Instead, each `metadata` or `analyze` run generates standalone analysis figures from the user's current input table under `metadata_analysis/figures/`. Geography-related output is represented through standardized `Country`, `Continent`, and `Subcontinent` distributions and their generated bar plots.
