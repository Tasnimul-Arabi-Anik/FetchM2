#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="${FETCHM2_REVIEW_WORKDIR:-}"

if [[ -z "${WORKDIR}" ]]; then
  WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/fetchm2_review_check.XXXXXX")"
fi

mkdir -p "${WORKDIR}"

cd "${ROOT_DIR}"

echo "FetchM2 review check"
echo "Repository: ${ROOT_DIR}"
echo "Workdir: ${WORKDIR}"

echo
echo "== CLI version =="
python -m fetchm2 --version

echo
echo "== Help surfaces =="
python -m fetchm2 --help >/dev/null
python -m fetchm2 metadata --help >/dev/null
python -m fetchm2 run --help >/dev/null
python -m fetchm2 seq --help >/dev/null
python -m fetchm2 audit --help >/dev/null
python -m fetchm2 validate --help >/dev/null
python -m fetchm2 analyze --help >/dev/null
echo "CLI help commands: passed"

echo
echo "== Unit/regression tests =="
pytest -q

echo
echo "== Byte compilation =="
python -m py_compile src/fetchm2/*.py tests/*.py
echo "py_compile: passed"

echo
echo "== Offline metadata standardization =="
python -m fetchm2 metadata \
  --input examples/offline_metadata.tsv \
  --outdir "${WORKDIR}/offline_metadata" \
  --offline

echo
echo "== Validation command =="
python -m fetchm2 validate \
  --input "${WORKDIR}/offline_metadata/metadata_output/fetchm2_clean.csv" \
  --outdir "${WORKDIR}/validation"

echo
echo "== Analysis command =="
python -m fetchm2 analyze \
  --input "${WORKDIR}/offline_metadata/metadata_output/fetchm2_clean.csv" \
  --outdir "${WORKDIR}/analysis" \
  --top-n 10

echo
echo "== Sequence check-only random subset =="
python -m fetchm2 seq \
  --input "${WORKDIR}/offline_metadata/metadata_output/fetchm2_clean.csv" \
  --outdir "${WORKDIR}/seq_random" \
  --subset-mode random \
  --subset-count 1 \
  --subset-seed 7 \
  --check-only

echo
echo "== Sequence check-only manual subset =="
python - <<PY "${WORKDIR}/manual_sequence_input.csv" "${WORKDIR}/manual_accessions.txt"
import csv
import sys

manual_csv, accession_file = sys.argv[1:3]
accession = "GCF_000001405.40"
with open(manual_csv, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=[
        "Assembly Accession",
        "Assembly Name",
        "BioSample",
        "Country",
        "Host_SD",
    ])
    writer.writeheader()
    writer.writerow({
        "Assembly Accession": accession,
        "Assembly Name": "review_manual_subset_smoke",
        "BioSample": "SAMN00000000",
        "Country": "Bangladesh",
        "Host_SD": "Homo sapiens",
    })
with open(accession_file, "w", encoding="utf-8") as out:
    out.write(accession + "\n")
PY

python -m fetchm2 seq \
  --input "${WORKDIR}/manual_sequence_input.csv" \
  --outdir "${WORKDIR}/seq_manual" \
  --subset-mode manual \
  --accessions-file "${WORKDIR}/manual_accessions.txt" \
  --check-only

echo
echo "== Output checks =="
test -s "${WORKDIR}/offline_metadata/metadata_output/fetchm2_clean.csv"
test -s "${WORKDIR}/offline_metadata/audit/production_readiness_gate.json"
test -s "${WORKDIR}/validation/production_readiness_gate.json"
test -s "${WORKDIR}/analysis/metadata_analysis_report.md"
test -s "${WORKDIR}/seq_random/selected_accessions.txt"
test -s "${WORKDIR}/seq_random/sequence_selection_summary.json"
test -s "${WORKDIR}/seq_manual/selected_accessions.txt"
test -s "${WORKDIR}/seq_manual/sequence_selection_summary.json"
echo "Expected review artifacts: present"

echo
echo "Review check completed successfully."
echo "Artifacts retained at: ${WORKDIR}"
