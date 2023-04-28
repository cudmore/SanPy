## Overview

SanPy supports user plugins. These are Python classes that tap into the underlying API architecture of the SanPy desktop GUI.

With Plugins, the core funtionality of SanPy can easily be extended, including:

 - Plotting raw data
 - Plotting analysis
 - Tabular reports
 - Extend analysis in new ways

For a tutorial on writing your own plugin, please see our [writing-a-plugin](api/writing-a-plugin.md) guide.

## Common plugin interface

All plugins are linked into the SanPy interface to respond to file and sweep selections, changes to the analysis, spike selection, and changes in the zooming of a recording.

Each plugin shares a common interface to turn these actions on and off. This interface can be toggled with a right-mouse-click and selecting `Toggle Top Toolbar`.

<IMG SRC="../img/plugins/plugin-common-interface.png" width=500>


## Built-in plugins.

### Plot Recording

Plot a recording with an overlay of spike detection parameters.

<IMG SRC="../img/plugins/plot-recording.png" width=700>

### Spike Clips

Plot all spikes aligned to their threshold. Also has waterfall and phase plots.

<table style="border:1px">
<tr>
    <td>
    <IMG SRC="../img/plugins/plot-spike-clips-1.png" width=700>
    </td>
    <td>
    <IMG SRC="../img/plugins/plot-spike-clips-2.png" width=700>
    </td>
</tr>
</table>

### Plot Scatter

A plugin to explore scatter plots of analysis results. Possibly the most useful plugin!

<IMG SRC="../img/plugins/scatter-plot.png" width=700>

### Plot FI

Analyze and plot analysis results versus current steps.

<IMG SRC="../img/plugins/plot-fi.png" width=700>

### Plot Analysis

Visualize a number of plot types including: Scatter, Histograms, Mean , etc. Basically 'Plot Scatter' on steroids.

<IMG SRC="../img/plugins/plot-tool.png" width=700>

### Detection Parameters

Allows setting of all detection parameters, includes a description of each as well as presets for different types of cells and recordings.

<IMG SRC="../img/plugins/detection-parameters.png" width=700>

### Export Trace

Plot a trace, set some display parameters and export to a file. File formats include Png, Pdf, and SVG.

<IMG SRC="../img/plugins/export-trace.png" width=700>

### Summarize Results

This plugin will display a table of analysis results with four different views including:

 - Full Export - The same table saved as `Export Spike Report`.
 - Human Readable - A nicer looking table with human readable column names.
 - Sweep Summary - A summary of spike statistics for one sweep. Useful if your recordings have just one sweep.
 - Detection Errors - A list of spike detection errors. Usefull while searching for the correct detection parameters.

Each row in the tble represents one spike. On selecting a spike, the corresponding spike will be selected in the main interface. Double-click on a spike to zoom into one spike.
 
 All reports can be copied to the clipboard and then pasted into a spreadsheet.

#### Full Export

Export all spikes like saving csv.

<IMG SRC="../img/plugins/summarize-results/full-export.png" width=500>

#### Human Readable

A slightly nicer table where column names are human readable.

<IMG SRC="../img/plugins/summarize-results/human-readable.png" width=500>

#### Sweep Summary

A summary of a single sweep. This is particularly usefull if a recording uses just one sweep..

<IMG SRC="../img/plugins/summarize-results/sweep-summary.png" width=500>

#### Detection Errors

A summary of all detection errors.

!!! Important

    This plugin allows the browsing of `Detection Errors` and is critical for the curation of data analysis! Browe through these errors and adjust [detection parameters](#detection-parameters) as neccessary.

<IMG SRC="../img/plugins/summarize-results/detection-errors.png" width=500>

### Sanpy Log

Display the SanPy log. As a user interacts with SanPy, most actions are logged to a file. This is useful for debugging and communicating with developers :)

<IMG SRC="../img/plugins/sanpy-log.png" width=700>

### FFT

Calculate and plot the Power-Spectral-Density (PSD) of any recording using the Fast-Fourier-Transform (FFT).

<IMG SRC="../img/plugins/fft.png" width=700>

### Stim Gen

A plugin to generate stimuli and save them as csv or Axon Text Files (ATF). Optimized to generate noisy sin waves! These files can then be presented as a stimulus during an ePhys recording.

<IMG SRC="../img/plugins/stimgen.png" width=700>
