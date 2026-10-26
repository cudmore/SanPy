
# Changelog

SanPy documentation is available at [https://cudmore.github.io/SanPy/](https://cudmore.github.io/SanPy/).

## Recent changes - 2026-10-26

### Desktop GUI

#### Added

- With more than one file selected, detection asks for confirmation, then detects every selected file over its full duration using the current preset and thresholds. Existing analysis on those files is replaced. A progress dialog can stop the rest of the batch. Failures are listed, and later files still run.
- Setting one experimental metadata value with more than one file selected asks to apply it to every selected file, with the same cancelable progress and a failure list. The edits stay unsaved until the usual folder save. A single selected file is still updated immediately.

#### Changed

- The file table can reveal a recording in the file manager and show or hide optional columns. Hidden columns are remembered and applied to open file tables. Required columns stay visible.
- The detection-parameter editor groups parameters by category. Start and stop seconds are not shown there. Single-file detection still takes that interval from the visible x-range.
- Opening a folder selects the first visible recording. The launcher and File menu show only recent paths that are still on disk.
- Export Spike Report no longer writes an Excel workbook. It writes a full spike CSV and a mean-clip CSV. The human-readable spike summary uses analysis-result display names for a fixed column set, including the width columns.

### Added

- `sanpy/io/nwb` writes and reads one intracellular NWB recording. SanPy state is stored as a versioned JSON payload in NWB scratch: experimental metadata, sweep conditions, epochs, detection parameters, and analysis results. `write_recording` refuses to replace an existing file, runs PyNWB validation, and refuses spike analysis for voltage clamp.
- `write_dandiset` and `read_dandiset` export selected analysis-directory rows as a local Dandiset and load those NWB assets back. This requires the `dandi` extra and does not upload.
- `open_remote_dandiset` and `read_remote_recording` stream one NWB asset from an explicit published DANDI version into a SanPy analysis. Draft versions are rejected. This requires the `dandi` extra.
- The NWB loader reads regularly sampled single-electrode current-clamp and voltage-clamp recordings, including an already-open NWB object, and applies a saved SanPy payload when one is present.
- `tests/test_examples.py` runs the three root example scripts, `load_data.py`, `load_folder.py`, and `load_and_analyze.py`. Plotting examples need the `plot` or `gui` extra and do not open a window.
- `tests/io/nwb/` covers local Dandiset export and remote NWB loading.
- `scripts/nwb`, `scripts/nwb_io`, and `scripts/nwb_ts` are standalone DANDI and NWB development tools: a Python streaming demo, a local export workflow, and a TypeScript reader.

### Changed

- `pynwb` and `pydantic` are required. The `nwb` extra is gone. Zarr and numcodecs are the `zarr-export` extra. TIFF support left the core install with the kymograph loader. The `dandi` extra cannot be installed together with `zarr-export`.
- The `dev` group no longer includes `test-gui`. The GUI CI job installs that group itself.
- Detection parameters and per-spike results are pydantic models. Unknown fields are rejected. Nonfinite numeric measurements are stored as missing values.
- Kymograph analysis, TIFF and CZI loading, the kymograph plugins, the user-analysis plugin base, and `vClampAnalysis` are removed, along with their docs and the bundled kymograph example. Removed detection presets are Ca Kymograph, Ca Spikes, Sub Threshold, and Wu-iPSC. The remaining presets are Default, Fast Neuron, Neuron, SA Node, and Ventricular.
- `examples/legacy` is removed. `sanpy.sanpyPaths` is now `sanpy.sanpy_paths`. `detectionUtils` and `bAbfText` are in `_retired/`.

## Recent changes - 2026-10-14

### Desktop GUI

#### Added

- Files and folders open in the background. The launcher shows loading progress in its status bar and stays open until the load finishes.
- Arrow keys in the file table select the next or previous recording.

#### Changed

- Plot Tool (Pool) loads files incrementally with progress in the status bar and reads saved analyses without loading raw recordings.
- Plot Tool and Plot Tool (Pool) include experimental-metadata columns and refresh after metadata edits.

### Added

- NWB loader for single-electrode current-clamp `.nwb` recordings, with per-sweep epoch tables. It requires the new `nwb` extra (`pynwb`) and is registered only when `pynwb` is installed.
- Development scripts in `scripts/nwb/` to export a SanPy analysis to NWB and import it back.
- `examples/` scripts that load a recording, analyze it, and open a folder using the bundled example data.
- `analysisDir` identifies recordings by a normalized path relative to the folder: `get_file_key()`, `get_row_for_file_key()`, and `get_analysis_for_file_key()`.
- The documentation site is built and deployed by a GitHub Action. Detection-parameter and analysis-result tables in Methods are generated from the SanPy definitions.
- CI runs the core tests on macOS and Windows without the `gui` extra.

### Changed

- ABF and NWB loaders read headers first and load raw sweeps only when `loadData=True`. `.sanpy` files are always loaded fully.
- Experimental metadata and sweep conditions moved from the file loader to `bAnalysis`: `ba.metaData`, `ba.getSweepCondition()`, and `ba.setSweepCondition()`. `fileLoader.metadata` was removed.
- Cell type, sex, and condition are no longer detection parameters or preset values. They come from file metadata (`cell_type`, `sex`, `condition`), including in `bExport` headers.
- The per-spike `include` result is now `spike_include` with values `yes` or `no`, separate from the file-level `include` metadata.
- `fileLoader_text` is now `fileLoader_sanpy` in `sanpy/fileloaders/fileLoader_sanpy.py`.
- Moved folders: bundled example data is in `sanpy/user_files/SanPy-User-Files/example-data` (was `data/`), `sanpy/_userFiles` is `sanpy/user_files`, `manuscript-figures` is `examples/manuscript-figures`, and `sanpy/models` is `scripts/models`.
- Documentation sources moved from `docs/docs/` to `docs/`, and `mkdocs.yml` is at the repository root.
- Tests use a smaller `tests/data` set.

## [0.3.0] - 2026-09-30

### Desktop GUI

#### Added

- Plot Tool and Plot Tool (Pool). Plot Tool (Pool) shows spikes from every analyzed file in the open folder.
- Set Meta Data edits a condition for each sweep.

#### Fixed

- Spike clips are taken from the filtered recording of the file being analyzed.
- Plot Recording reads the sweeps it shows without changing the detection view's current sweep.
- Export Trace uses its selected sweep. All still follows the detection view.
- Spike selections now apply file, sweep, and spikes as one validated window state. Plot Tool (Pool) can switch recordings from its primary row, and Plot FI raw points select their source spikes.

### Added

- Recordings store a condition for each sweep. Conditions are saved in the analysis HDF5 and copied onto each spike as `sweepCondition`.
- Spike results include a categorical file number for pooled plots.
- Added a stochastic Hodgkin-Huxley model with a settable sodium-activation shift and slow potassium adaptation.

### Changed

- Cell type and sex are categorical statistics in plot menus.
- A core install no longer includes PyQt5, pyqtgraph, qtawesome, QtPy, pyqtdarktheme-fork, or mplcursors. The desktop app is the `gui` extra: `uv sync --extra gui` or `pip install "sanpy-ephys[gui]"`.
- A core install no longer includes matplotlib or seaborn. Install them with the `plot` extra, or with the `gui` extra for the desktop app. uv ignores pyabf's unused matplotlib requirement; pip still installs it.
- A core install no longer includes requests. The unused GitHub folder loader now lives in `sandbox/bAnalysisDirWeb.py`.

## [0.2.9] - 2026-09-28

- Internal development release for experimental-metadata and file-table work.

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
- Added validated file-metadata and experimental-metadata JSON documents for each recording, each with a definitions document for display names and controlled choices.

#### Changed

- Updated the SanPy Zarr development environment and implementation for Python 3.13.
- Changed `.sanpy` loading to construct one epoch table per sweep while preserving sweep-specific command levels.
- Changed SanPy Zarr source provenance from ABF-specific metadata to explicit source format and reader version fields.
- Normalized exported epoch levels consistently across epoch and analysis-result tables.
- Changed experimental metadata to canonical snake_case keys. Display names and choices stay in the definitions, and sex values distinguish unclassified, unknown, and not applicable.
- Preserved JSON insertion order in SanPy Zarr exports.

### Desktop GUI

#### Added

- Compact analysis-window controls for detection tools, plots, and docked plugins; recent-file, user-files, and diagnostics commands.
- Sweep/epoch selection in plugins and reports, plus categorical statistics in scatter plots.
- Left toolbar for Detection, File Metadata, Experimental Metadata, Detection Parameters, and SanPy Info, plus a read-only File Metadata view of acquisition facts.
- Named NicePool presets so FI Plot and Sweep Plot can be edited independently.

#### Changed

- View menu, docks, and plugin toolbars are more compact; Plot FI options live in the Options popup.
- Plugin context menus are reduced; plot menus hide stats that are not computed or not numeric.
- Plot Recording sweep-offset and recent-file refresh behavior.
- File table columns follow the experimental-metadata definitions and share edits with Set Meta Data. Detection start, stop, and threshold columns were removed from that table.

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
- Fixed the analysis table remaining in place after a detection that found no spikes.
- Fixed X-axis auto-range on the DAC, derivative, and Vm plots, and full-axis Y scaling.

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
- Recording loaders now provide immutable file metadata, including acquisition time, channel and sweep counts, epochs per sweep, axis labels, recording mode, sampling rate, and an optional ABF user list.
- Retired the legacy Plot Tool plugins in favor of NicePool.
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
