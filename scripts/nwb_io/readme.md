# SanPy NWB export and local Dandiset development

> **This document is not a source of truth.** The executable Python code and
> focused tests in this directory define current behavior. Keep this document
> synchronized with those files.

This standalone development workflow exports a folder-backed SanPy
`analysisDir` into new current-clamp NWB files and organizes them as a local
Dandiset. It does not upload data or contact a DANDI Archive instance.

## Development configuration

`demo_export_analysis_dir.py` contains visible, editable development values:

- source: `/Users/cudmore/data/nwb/001261-dandi-export`
- output: `/Users/cudmore/data/nwb/001261-sanpy-dandiset`
- local-only identifier: `DANDI:000000`
- species: `Mus musculus`
- missing acquisition datetime: `1970-01-01T00:00:00 America/New_York`

The synthetic Dandiset identifier must be replaced with a real existing DANDI
Sandbox draft identifier before upload. The exporter refuses to replace an
existing output directory.

Each selected `analysisDir` row receives one-based development identities such
as `development-subject-001` and `development-cell-001`. These values are
explicit development placeholders, not metadata inferred from source names.
The export report retains the stable SanPy file key for traceability.

NWB `Subject` represents the biological organism, not the recording or cell.
Production exports must therefore replace these synthetic identifiers with
authoritative biological subject identities. Empty or unknown SanPy sex is
written as NWB `U`. Missing age is not fabricated, so DANDI validation reports
the expected subject-age warning until authoritative age or date of birth is
provided.

## Run focused tests

From the repository root:

```shell
uv run --extra dandi pytest -p no:pytest-qt scripts/nwb_io/tests -q
```

## Export the configured collection

Ensure that the configured output directory does not already exist, then run:

```shell
uv run --extra dandi python scripts/nwb_io/demo_export_analysis_dir.py
```

The operation:

1. opens the configured folder through `sanpy.analysisDir`;
2. loads each requested `bAnalysis`, whether analyzed or not;
3. writes and round-trip verifies a new NWB file;
4. stops local-Dandiset construction if any requested export fails;
5. organizes successful files with the DANDI Python package;
6. reopens the result with `dandi.dandiset.Dandiset`; and
7. reports every DANDI validation finding.

The source folder and its SanPy HDF5 database are never modified. The original
on-disk recording type is irrelevant after SanPy has loaded each `bAnalysis`.
