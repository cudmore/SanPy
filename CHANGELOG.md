
SanPy Documentation is available at [https://cudmore.github.io/SanPy/](https://cudmore.github.io/SanPy/)

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

