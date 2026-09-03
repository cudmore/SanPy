
# Changelog

SanPy documentation is available at [https://cudmore.github.io/SanPy/](https://cudmore.github.io/SanPy/).

## Unreleased

### Added

- Added local PyInstaller build pipelines for macOS ARM64 and Windows AMD64. The macOS pipeline builds, signs, notarizes, staples, and validates the application; the Windows pipeline produces a single-file executable.
- Added self-contained build records with `build_info.json`, an installed-package `environment.txt`, an exact `source-<commit>.zip`, the user distribution ZIP, and `SHA256SUMS.txt`.
- Added platform-specific build IDs and output directories such as `macos-YYYYMMDD-vN` and `windows-YYYYMMDD-vN`.
- Added a consolidated packaging guide covering both platforms, dependency updates, build-record retention, and recovery of the exact source used for a distributed application.
- Added a locked Python 3.11 development environment using `uv.lock`.

### Changed

- Replaced the legacy `setup.py` and `requirements.txt` installation with `pyproject.toml` and uv.
- Moved PyInstaller and its hooks into a shared `packaging` dependency group in `pyproject.toml`; both platform build scripts now install from the cross-platform `uv.lock` with `uv sync --locked`.
- Expanded packaged build metadata to include the platform-local build ID and timestamp, full Git commit and clean-tree state, platform details, and Python, uv, PyInstaller, and key package versions.
- Changed macOS and Windows builds to require a clean committed source tree and to archive that exact commit before packaging.
- Changed final distribution checksums to use `SHA256SUMS.txt`, generated only after the user-facing ZIP is complete.
- Updated source-installation documentation and GitHub Actions to use Python 3.11 and uv.
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
