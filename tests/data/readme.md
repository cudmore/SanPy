# SanPy test data

This directory contains stable fixtures used only by the pytest suite. Tests
must not read data from `sanpy/user_files/SanPy-User-Files/example-data`, which
is editable user-facing example data.

`persisted_analysis/` contains a compact two-sweep SanPy text recording and its
HDF5 catalog. Together they verify restored detection results and Zarr export
without retaining the original 36 MB recording.
