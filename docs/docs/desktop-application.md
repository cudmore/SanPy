The SanPy deskop application is an easy to use and powerful GUI designed to satisfy all your analysis needs. You can [download](../download) the desktop appication or [build from source](../install).

## Getting Started

Load a folder of raw data files with the `Load Folder` button, or use the `File - Load Folder ...` menu, or drag and drop a folder from your hard-drive. Once a folder of raw data is loaded, each file in the folder will be shown in a list, one row per raw data file. Selecting a file will display the raw data recording.

Spike detection is then performed by specifying a threshold in either the derivative of the membrane potential (Detect dV/dt) or the membrane potential (Detect mV).

Once spikes are detected, the analysis results are overlaid over the plots of the raw data. Finally, [plugins](../plugins) can be used to inspect the analysis results.

<IMG SRC="../img/sanpy-app.png" width=700>

## File List Table

<IMG = SRC="../img/desktop-main-window/file-list.png" width=700>

A list of files in a loaded folder, each row is a file and columns are information on the file including a subset of the [detection parameters](../methods/#detection-parameters) and [analysis results](../methods/#analysis-results-full). The file list table can be toggled on and off with the `View - File Panel` menu or keyboard `f`. 

 - **L** - Indicates if the file is loaded. Use the right-click menu `Unload Data` to unload a loaded file. This can save memory.
 - **A** - Indicates if the file has been analyzed.
 - **S** - Indicates if the analysis has been saved.
 - **N** - Once analyzed, indicates the number of spikes detected.
 - **File** - The name of the raw data file.
 - **Dur(s)** - The duration of the recording (this is the duration of each sweep).
 - **Sweeps** - The number of sweeps.
 - **Epochs** - The number of epochs per sweep. Epochs correspond to different current clamp steps/amplitudes within each sweep.
 - **KHz** - The sampling rate of the recording.
 - **Mode** - The mode of the recording, either V-Clamp or I-Clamp. Currently, SanPy will only analyze I-Clamp.
 - **Start(s)** - Once analyzed, indicates the start second of the analysis.
 - **Stop(s)** - Once analyzed, indicates the stop second of the analysis.
 - **dvdtTheshold** - Once analyzed, indicates the dV/dt used for detection.
 - **mvThreshold** - Once analyzed, indicates the mV used for detection.
 
<IMG = SRC="../img/desktop-main-window/file-menu-right-click.png" width=125 align="left">

Right-click in the file list table for a popup menu.

- **Unload Data** - Unload the raw data from the selected row. Useful to conserve memory if the folder has lots of files.
- **Synch With Folder** - Synchronize the contents of the folder with SanPy. Useful if you are acquiring new data on an electrophysiology setup.
- **Save All Analysis** - Save all the analysis for a folder to a single hdf5 file. This file is then used to load all the analysis the next time SanPy is run. See also, menu `File - Save Folder Analysis`.
- **Copy Table** - Copy the contents of the file list table. Useful to paste into a spreadsheet.

## Detection panel

<IMG = SRC="../img/desktop-main-window/detection-panel.png" width=250 align="left">

The detection panel has subcategories to detect spikes and to control the display of the raw data and analysis results. The detection panel can be toggled on and off using the `View - Detection Panel` menu or with keyboard `d`.

### Detection

Set detection parameters, finer control of all detection parameters is provided with the [Detection Parameters Plugin](../plugins/#detection-parameters).

- **Presets** - A popup to set a pre-defined set of detection parameters.
- **Detect dV/dt** - Detect spikes with the specified value in the first derivative (dV/dt). The first derivative can be plotted with menu `View - Derivative`.
- **Detect mV** - Detect spikes with the specified value in mV.

<!--
- **From(s) To(s)** - **depreciated** Displays the current x-axis zoom and allows it to be set. Use Click+drag with the mouse to visually zoom in on the recording. Use keyboard 'enter' or 'return' to set a recording to full zoom.
- **Spikes/Freq/Errors** - Once analyzed, displays the number of detected spikes, the mean instantaneous frequency between spikes, and the number of errors encountered during spike detection. View all spike analysis results with the [Summary Spikes](../plugins/#summary-spikes) plugin and all errors with the [Summary Error](../plugins/#summary-error) plugins.
-->

- **Export Spike Report** - Export all analysis for the selected file to a CSV file. This file includes all [detection parameters](../methods/#detection-parameters) and [analysis results](../methods/#analysis-results-full).

### Display

Control the display of SanPy.

- **Sweep** - Set the displayed sweep. This includes a popup menu to select a sweep and controls to go to the previous `<` and next `>` sweep.

<!--
- **Crosshair** - Checkbox to toggle a crosshair to track the mouse position and display the current position in seconds (x) and mV (y).
-->

- **Spike** - Select individual spikes by spike number and scroll to the previous `<<` and next `>>` spike.

- **[]** - A button to set the raw data plots to full scale/zoom. This can also be done with keyboard `enter` or `return`.

### Set Spikes
 - Set parameters for the currently selected spike(s) like: Condition, User Type, and include.

### Plot Options
 - Control the analysis results that are overlayed over the raw data. See [below](#raw-data-overlayed-with-analysis-results) for a detailed description.

<!-- move byond the pervious image. My Slacker generation comes through !!! -->
<p style="clear: both;">
</p>

## Raw data plots

<IMG = SRC="../img/desktop-main-window/raw-data-plots.png" width=350 align="left">

There are four different plots of the raw data. These can be toggled on and off using the [view menu](#view-menu) entries: `full recording`, `derivative`, and `DAC`. Note, the raw data (bottom plot) is always shown and cannot be toggled.

Click+drag with the mouse to zoom in on the time-axis.

 - **Full Recording** - An overview of the total recording. This plot also shows the current zoom as a gray box.
 - **Derivative** - The first derivative (dV/dt) of the raw recording. Used for spike detection by setting a value in the [detection panel](#detection).
 - **DAC** - A plot of the stimulation output. Please note, in this example it is 0 (no stimulation).
 - **Recording** - A plot of the actual recording with analysis results overlaid. Here is shown spike threshold (mV, red circle) and spike peak (mV, green circle).

<!-- move byond the pervious image. My Slacker generation comes through !!! -->
<p style="clear: both;">
</p>

## Raw data overlayed with analysis results

<IMG = SRC="../img/desktop-main-window/plot-options.png" width=250 align="left">
<IMG = SRC="../img/desktop-main-window/raw-data-plot-zoom.png" width=350 align="right">

<!-- move byond the pervious image. My Slacker generation comes through !!! -->
<p style="clear: both;">
</p>

A number of analysis results can be overlaid using the [Plot Options](#plot-options) checkboxes  in the [detection](#detection) panel. For a full list of analysis results, see [Methods - Analysis Results](../methods/#analysis-results-full)

 - Global Threshold - Plot the spike threshold in the 'Full Recording' plot.
 - Threshold (dV/dt) - Plot the spike threshold in the 'Derivative' plot (red circle)
 
 The other plot options are displayed on the main recording (bottom most plot).
 
 - Half-Widths - Spike half with for 10, 20, 50, 80, and 90 percent (yellow lines).
 - Pre AP Min - Minimum mV before a spike (mV).
 - EDD Rate - The early Diatolic Duation Rate (mV/s).
 - Threshold (mV) - Spike threshold (mV). Also used as the time of a spike.
 - AP Peak (mV) - Spike peak (mV).
 - Epoch Lines - Epochs represent different DAC steps within a sweep (gray vertical lines).
 - EDD - The early diastolic duration.

<!-- move byond the pervious image. My generation X comes through !!! -->
<p style="clear: both;">
</p>

## Mouse and Keyboard

### Mouse

 - Mouse click - Select individual spikes.
 - Mouse wheel - Zoom in and out on x-axis (time).
 - Mouse click+drag - Pan the x-axis (time).
 - Mouse option+click+drag to zoom into the recording (y-axis).

### Keyboard

 - "return" or "enter" - Set plot of recordings to full scale.
 - "esc" - Canel spike selection.
 - [coming soon] "b" - Toggle selected spike(s) bad.

## Menus

### File menu

<IMG = SRC="../img/desktop-main-window/file-menu.png" width=350 align="left">

 - **Load Folder ...** - Load a folder of raw data. A loaded folder will be shown in the [File List Table](#file-list-table).
 - **Load Recent ...** - Load recently loaded folders.
 - **Save Folder Analysis ...** - Save all the analysis for the loaded folder.
 - **Save Preferences** - Save the SanPy preferences. This includes mostly information about the GUI like window position and opened plugins.
 - **Show Log** - Show the SanPy log. A log is kept as a user interacts with SanPy. This is useful to send to the developers if there are problems. The logs can also be viewed with the [SanPy Log Plugin](../plugins/#sanpy-log).

<!-- move byond the pervious image. My generation X comes through !!! -->
<p style="clear: both;">
</p>

### View menu

<IMG = SRC="../img/desktop-main-window/view-menu.png" width=175 align="left">

A menu that allows different pieces of the interface to be shown or hidden.

- **File Panel** - Toggle the visibility of the [file list panel](#file-list-table).
- **Detection Panel** - Toggle the visibility of the [detection panel](#detection-panel).
- **Detection** - Toggle [detection](#detection) in the Detection Panel
- **Display** - Toggle [display](#display) in the Detection Panel
- **Plot Options** - Toggle [plot options](#plot-options) in the Detection Panel. This is a panel with checkboxes to show/hide analysis results over the raw data.
- **Set Spikes** - Toggle [set spikes](#set-spikes) in the Detection Panel. This is a panel to allow selected spike parameters to be set. For example, to set spikes as good/bad, user type, and condition.
- **Full Recording** - Toggle the display of the [full recording](#raw-data-plots).
- **Derivative** - Toggle the display of the membrane potential [derivate](#raw-data-plots) (dV/dt). This is useful for detecting spikes with dV/dt.
- **DAC** - Toggle the display of the [current clamp stimulus](#raw-data-plots).
- **Plugins** - Toggle the display of a plugins dock. A right-click in the plugins dock will insert a plugin. Plugins can also be opened as seperate windows with the main [Plugins menu](#plugins-menu).
- **Dark Theme** - Toggle dark and light themes. If checked, SanPy will use a dark theme, otherwise it will use a light theme. Please note that switching themes while SanPy is running will give sub-optimal results. To fully switch themes, select a theme then save preferences with the main `File - Save Preferences` menu, and restart SanPy.

<!-- move byond the pervious image. My generation X comes through !!! -->
<p style="clear: both;">
</p>

### Plugins menu

<IMG = SRC="../img/desktop-main-window/plugins-menu.png" width=175 align="left">

A menu to open a SanPy [plugin](../plugins). Plugins opened with this menu will be displayed in their own window.

To open a plugin within the main SanPy window, use the `View - Plugins` menu to show the plugins dock and then right-click to select a plugin to display.

All open plugins can be saved and re-opened with the next run of SanPy by saving the SanPy preferences with the `File - Save Preferences` menu.

<!-- move beyond the pervious image. My generation X comes through !!! -->
<p style="clear: both;">
</p>

## Plugins

There is a dedicated [plugin](../plugins) documentaion page. Here we want to highlight a few key plugins.

### [Plot Scatter](../plugins#plot-scatter)

The `plot scatter` plugin is designed to plot any [analysis results](../methods#analysis-results-full). Spike selections are bi-directional between the plot scatter widget and the main interface. The markers symbols and colors can be used to specify detailed results per spike. For example, coloring based on time or sweep, if the spike is marked bad, and if the spike has a specified user type. These types of things can be set in the main interface `Detection Panel - Set Spikes`.

<img src="../img/plugins/scatter-plot.png" width="600" align="right">

<!-- move byond the pervious image. My generation X comes through !!! -->
<p style="clear: both;">
</p>

### [Plot FI](../plugins#plot-fi)

The `plot fi` plugin is designed to visualize the raw data and analysis of a current-clamp experiment where a range of hyperpolarizing and depolarizing current steps are delivered.

<img src="../img/plugins/plot-fi.png" width="600" align="right">

<!-- move byond the pervious image. My generation X comes through !!! -->
<p style="clear: both;">
</p>

### [Summarize Results](../plugins/#summarize-results)

The `summarize results` plugin shows a number of different tables to review the analysis results. Here, we focus on errors that occured during spike detection. Each row represents an error in an individual spike. Selecting the error will select the spike in the main interface. This should be used in a curation feedback loop. Once spikes are detected, check for errors and adjust the detection parameters until the errors are acceptable. Alternatively, you can set a tag in individual spikes to 'reject' them.

<img src="../img/plugins/detection-errors.png" width="600" align="right">

<!-- move byond the pervious image. My generation X comes through !!! -->
<p style="clear: both;">
</p>

## User Files

When the SanPy desktop application is first run, it creates a folder to contain user files in `<username>/Documents/SanPy-User-Files`. This is where you drop in your custom code to extend the capabilities of SanPy. This includes:

- [Writing a file loader](../api/writing-a-file-loader)
- [Writing new analysis](../api/writing-new-analysis)
- [Writing a plugin](../api/writing-a-plugin)


