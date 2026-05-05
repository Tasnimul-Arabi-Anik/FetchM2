# FetchM2 Release Checklist

Use this checklist before each GitHub/PyPI release.

## Pre-release

- Update `src/fetchm2/__init__.py` version.
- Update `pyproject.toml` version.
- Run `pytest`.
- Run `python -m build`.
- Run `python -m twine check dist/*`.
- Install the wheel in a clean environment.
- Run offline metadata smoke test.
- Run sequence `--check-only` smoke test.
- Run a small live NCBI smoke test when network access is available.
- Confirm no API keys, tokens, caches, or output directories are committed.

## Release

- Commit all source, data, docs, tests, and examples.
- Tag the commit, for example `v0.1.0`.
- Push branch and tag to GitHub.
- Upload `dist/*` to PyPI using an environment variable or secure prompt.

## Post-release

- Install from PyPI in a fresh environment.
- Run `fetchm2 --version`.
- Run the offline smoke test from the PyPI-installed package.
- Record results in `docs/VALIDATION_REPORT.md`.
