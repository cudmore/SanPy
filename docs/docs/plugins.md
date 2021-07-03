SanPy supports user plugins. These are Python scripts that tap into the underlying architecture of the SanPy App.

With Plugins, users can easily extend the functionality of SanPy by:

 - Plotting raw data
 - Plotting analysis
 - Extend analysis in new ways

All plugins are linked into the SanPy interface to respond to spike selection, zooming, and file switching. A selection in the main interface will propagate to the plugin and visa-versa.

# Built-in plugins.

## Plot Recording

Use Matplotlib to plot a recording with spike detection overlaid.

<IMG SRC="../img/plugins/plot-recording.png" width=700>

## Spike Clips

Plot all spikes aligned to their threshold.

<IMG SRC="../img/plugins/spike-clips.png" width=700>

## Plot Scatter

A plugin to plot x/y scatter plots of detection parameters.

<IMG SRC="../img/plugins/scatter-plot.png" width=700>

## Plot Analysis

A fairly complex plugin to display a number of different plots including: Scatter, Histograms, Mean , etc.

<IMG SRC="../img/plugins/plot-tool.png" width=700>

## Export Trace

Displays a trace, allows user to modify the look and then export to a number of file formats including Png, Pdf, and SVG.

<IMG SRC="../img/plugins/export-trace.png" width=700>

## Summary analysis

Displays a table with a summary of analysis results and detection parameters. Can copy/paste into a spreadsheet like Excel.

<IMG SRC="../img/plugins/summary-analysis.png" width=700>

## Summary Spikes

Displays a table of all analysis results, one row per spike. Can copy/paste into spreadsheet for further analysis. This is the same information as when saving.

<IMG SRC="../img/plugins/summary-spikes.png" width=700>

## Error Summary

Display per-spike detection errors. Clicking on an error in the table will highlight the spike in the main interface.

<IMG SRC="../img/plugins/error-summary.png" width=700>

## Sanpy Log

A plugin to display the SanPy log. As a user interacts with SanPY, most actions are logged to a file. This is useful for debugging and communicating with developers :)

<IMG SRC="../img/plugins/sanpy-log.png" width=700>
