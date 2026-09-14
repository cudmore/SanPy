
# Changelog

SanPy documentation is available at [https://cudmore.github.io/SanPy/](https://cudmore.github.io/SanPy/).

## [0.2.8] - 2026-09-10

### SanPy Zarr

#### Added

- Added a NicePool desktop plugin for linked exploration of detected spike
  statistics with bidirectional SanPy selection synchronization.
- Added a self-contained SanPy Zarr v3 collection export with validated JSON manifests, chunked signal arrays, CSV and Parquet table options, and atomic destination replacement.
- Added export support for both ABF and canonical `.sanpy` recordings, including command waveforms, point-aligned epoch indexes, per-sweep epoch tables, and HDF5-restored analysis results.
- Added a folder export command at `scripts/export_folder_to_zarr.py` for regenerating a complete collection from a SanPy data folder and its `sanpy_recording_db.h5` catalog.
- Added runtime-owned detection and analysis-result definitions, result axis labels, trace-overlay definitions, and collection-level recording summaries to SanPy Zarr exports.
- Added a strict `.sanpy` text loader format using `seconds`, optional integer `epoch_index`, numbered recording columns, and matching command columns.
- Added a stochastic Hodgkin-Huxley `.sanpy` example with saved analysis results for loader and Zarr integration testing.

#### Changed

- Updated the SanPy Zarr development environment and implementation for Python 3.13.
- Changed `.sanpy` loading to construct one epoch table per sweep while preserving sweep-specific command levels.
- Changed SanPy Zarr source provenance from ABF-specific metadata to explicit source format and reader version fields.
- Normalized exported epoch levels consistently across epoch and analysis-result tables.

### Desktop GUI

#### Added

- Compact analysis-window controls for detection tools, plots, and docked plugins; recent-file, user-files, and diagnostics commands.
- Sweep/epoch selection in plugins and reports, plus categorical statistics in scatter plots.

#### Changed

- View menu, docks, and plugin toolbars are more compact; Plot FI options live in the Options popup.
- Plugin context menus are reduced; plot menus hide stats that are not computed or not numeric.
- Plot Recording sweep-offset and recent-file refresh behavior.

#### Fixed

- Fixed Qt window and plugin lifecycle handling that could cause native crashes after closing and reopening analysis windows.
- Fixed standard close-window shortcuts so they close only the active analysis or plugin window.
- Fixed dark/light theme propagation, plot resizing when panels are toggled, and voltage and overview Y-axis fitting when sweeps change.
- Fixed Plot Scatter time and sweep coloring and Plot FI updates when switching files.
- Fixed Sweep Summary crashing when export start/stop are unset.
- Fixed Plot Scatter crashing on non-numeric axes.
- Reject unsupported recording files instead of opening a broken window.
- Keep plot cursors out of auto-range.
- Size the compact plugin toolbar to its visible controls.

### Added

- Added local PyInstaller build pipelines for macOS ARM64 and Windows AMD64. The macOS pipeline builds, signs, notarizes, staples, and validates the application; the Windows pipeline produces a single-file executable.
- Added self-contained build records with `build_info.json`, an installed-package `environment.txt`, an exact `source-<commit>.zip`, the user distribution ZIP, and `SHA256SUMS.txt`.
- Added platform-specific build IDs and output directories such as `macos-YYYYMMDD-vN` and `windows-YYYYMMDD-vN`.
- Added a consolidated packaging guide covering both platforms, dependency updates, build-record retention, and recovery of the exact source used for a distributed application.
- Added a locked Python 3.13 development environment using `uv.lock`.
- Added Myokit treatment example `.sanpy` output.
- Install Zarr export dependencies by default.

### Changed

- Spike results now record SanPy source identity via `sanpy/sanpy_version.py`. Removed `sanpy/version.py` and the old `analysisVersion` / `interfaceVersion` fields.
- Analysis-result definitions were refactored toward a single schema.
- Public SanPy import surface is explicit; tests enforce that the backend does not import the GUI.
- External user-code imports are disabled; user-plugin load failures are isolated.
- SanPy filesystem locations are centralized; sample data path is `sample-data`.
- Archived legacy stimulus experiments and moved the old scatter widget out of the package.
- Releases are named from the SanPy version; Git-derived version metadata was refreshed.
- Updated SanPy for pandas 2.3 compatibility and removed obsolete analysis-directory duplication code.
- Exposed the folder-analysis save action through the GUI application and window lifecycle.
- Removed obsolete platform-specific Python 3.11 requirement files and broken lock-update scripts now superseded by `pyproject.toml` and the shared `uv.lock`.
- Replaced the legacy `setup.py` and `requirements.txt` installation with `pyproject.toml` and uv.
- Moved PyInstaller and its hooks into a shared `packaging` dependency group in `pyproject.toml`; both platform build scripts now install from the cross-platform `uv.lock` with `uv sync --locked`.
- Expanded packaged build metadata to include the platform-local build ID and timestamp, full Git commit and clean-tree state, platform details, and Python, uv, PyInstaller, and key package versions.
- Changed macOS and Windows builds to require a clean committed source tree and to archive that exact commit before packaging.
- Changed final distribution checksums to use `SHA256SUMS.txt`, generated only after the user-facing ZIP is complete.
- Updated source installation and GitHub workflows to use uv and follow the repository's single `.python-version` source of truth.
- Changed PyPI publishing to an explicit, tag-based manual workflow.

### Fixed

- Store SanPy logs outside frozen application bundles so logging does not modify signed or notarized applications.
- Persist the Matplotlib cache outside PyInstaller's temporary directory to avoid rebuilding the font cache on every launch.
- Allow SanPy to start when its preferred log or Matplotlib cache directory is unavailable.
- Clean up Qt plugins correctly in the test suite, preventing a teardown segmentation fault.

## 20240126

 - Added a file folder opening window. This is show at first run and allows users to open new and previous opened files and folder.
 - Limiting analysis to the visible part of the recording
 - Greatly improved panning and zooming of all raw data
   - Retained click+drag to pan x-axis and mouse-wheel to zoom x-axis
   - New feature using keyboard shift, to click+drag the y-axis and mouse wheel to zoom the y-axis.

- Detailed fixes and additions
  - Fix a bug where when user sets sweep, we loose the current zoom
  - Roll over SanPy.log so it does not get too big
  - fixed spin boxes in plot recording
  - Fixed bug where `unknown` recording mode was not allowing data to be displayed (problem in initializing the filtered recording).
  - Now include build date and time on each pi install

 - Known bugs
  - (seems to be fixed) If user open a plugin and closes the main raw data file, SanPy crashes
  
### Next release to do
 
 - Add documentation for Plot Tool plugins

## 20240117

### New features
 - Now provide opening of one raw data file. Either menu `File - Open` or drag and drop
 - Add horizontal and vertical cursors to Vm and deriv plot. Can do lots with these including selecting spikes within the cursors and seet some detection params like dv/dt and mV spike threshold as well as some windows like refactory period and window to detect half-widths

### bug fixes
 - Fixed lots of bugs (and extended the interface) of the plot recording plugin.
 - Fixed lots of bugs in plotting with `Plot Tool` and `Plot Tool (pool)` plugins.
 
## 20231201

### New Features
 - Added fast AHP. The fast AHP after a spike. Measured in a window using detection parameter fastAhpWindow_ms
 - Added API documentation for adding a new measurement to the core analysis

### Bug fixes
 - Fixed bug in loading detection-presets when they do not match the default detection presets (missing keys)
 - Fixed bug in loading folder of raw data. Previouslly, the folder would not load if there was an error in one abf file. We are getting abf file errors trying to read abf exported from sutter patch.
