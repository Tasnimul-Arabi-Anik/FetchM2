# FetchM Compatibility Notes

FetchM2 is designed as a standalone CLI successor to FetchM. The points below document compatibility-sensitive behavior that affects downstream analysis.

## BioSample Fetching

FetchM2 follows FetchM by fetching metadata once per unique BioSample accession, not once per assembly row. If paired `GCA_*` and `GCF_*` rows share the same BioSample, FetchM2 retrieves that BioSample metadata once and applies it back to both rows before representative selection.

Audit outputs report both units:

- `rows`: rows in `fetchm2_clean.csv`
- `unique_assembly_accessions`: unique assemblies represented in the clean output
- `biosample_linked_rows`: clean rows with a BioSample accession
- `unique_biosample_accessions`: unique BioSample accessions represented
- `biosample_reused_extra_rows`: extra rows caused by BioSample reuse across assemblies

## Representative Clean Output

Original FetchM writes its main clean output after deduplicating by `Assembly Name`, prioritizing `GCF_*` rows when paired RefSeq/GenBank assemblies exist.

FetchM2 follows that behavior by default:

- `fetchm2_clean.csv`: one representative row per `Assembly Name`, preferring `GCF_*`.
- `fetchm2_all_assemblies.csv`: all standardized assembly rows before representative selection.
- `ncbi_clean.csv`: FetchM-compatible alias of `fetchm2_clean.csv`.
- `fetchm2_clean_compat.csv`: explicit compatibility alias of `fetchm2_clean.csv`.

Use `--keep-assembly-duplicates` if you intentionally want paired `GCA_*` and `GCF_*` rows retained in `fetchm2_clean.csv`.

## Stable Pipeline Contract

FetchM2 always writes the following downstream-facing columns in `fetchm2_clean.csv`, even when values are blank:

- `Assembly Accession`
- `Assembly Name`
- `Assembly BioSample Accession`
- `Organism Name`
- `Geographic Location`
- `Continent`
- `Subcontinent`
- `Collection Date`
- `Collection_Year`
- `Host`
- `Host_SD`
- `Isolation_Source`
- `Isolation_Source_SD`
- `Sample_Type_SD`
- `Environment_Medium_SD`

Assembly accession versions are preserved. For example, `GCF_000123456.1` remains `GCF_000123456.1`.

FetchM2 also writes:

- `sample_map.csv` for stable sequence-analysis sample IDs.
- `metadata_completeness.csv` for field-level coverage checks.
- `metadata_bias_warning.txt` for low-coverage and representative-selection warnings.
- `fetchm2_manifest.json` for machine-readable run metadata.

## Sequence Download Unit

Sequence download from the default `fetchm2_clean.csv` operates on representative assemblies, matching FetchM and avoiding duplicate GCA/GCF downloads for the same assembly name.

If downstream prevalence or resistome tools operate at assembly/genome level, use `Assembly Accession` as the denominator. If they operate at BioSample level, deduplicate intentionally and document the representative rule.

## Cache and Fallback Behavior

FetchM2 aligns with FetchM's BioSample fallback behavior:

- direct BioSample XML is tried first
- esummary fallback is used when direct XML lacks usable attributes
- recovered fallback XML is cached, not the incomplete direct XML
- stale incomplete cache entries are ignored and retried

This avoids rerun regressions where a recovered BioSample would later appear missing because incomplete direct XML had been cached.

## Known Intentional Differences

FetchM2 adds standardized fields, richer audits, production gate outputs, and additional sequence filters. These are additions, not replacements for the core FetchM workflow.

FetchM2 does not generate FetchM's DOCX report; it focuses on CSV/TSV, Markdown, JSON, and figure outputs that are easier to use in automated CLI workflows.
