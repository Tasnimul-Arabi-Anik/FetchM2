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

Use `--keep-assembly-duplicates` if you intentionally want paired `GCA_*` and `GCF_*` rows retained in `fetchm2_clean.csv`.

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

