SanPy supports user plugins. These are Python scripts that tap into the underlying architecture of the SanPy App.

With Plugins, users can easily extend the functionality of SanPy by:

 - Plotting raw data
 - Plotting analysis
 - Extend analysis in new ways

All plugins are linked into the SanPy interface to respond to spike selection, zooming, and file switching. A selection in the main interface will propagate to the plugin and visa-versa.

# Built-in plugins.

## Plot Recording

Plot a recording with an overlay of spike detection parameters.

<IMG SRC="../img/plugins/plot-recording.png" width=700>

## Spike Clips

Plot all spikes aligned to their threshold. Also has waterfall and phase plots.

<IMG SRC="../img/plugins/spike-clips.png" width=700>

## Plot Scatter

Plot x/y scatter of spike detection parameters. Includes x/y histograms and 'shot' plots of spike i versus spike -1.

<IMG SRC="../img/plugins/scatter-plot.png" width=700>

## Plot Analysis

Visualize a number of plot types including: Scatter, Histograms, Mean , etc. Basically 'Plot Scatter' on steroids.

<IMG SRC="../img/plugins/plot-tool.png" width=700>

## Detection Parameters

Allows setting of all detection parameters, includes a description of each as well as presets for different types of cells and recordings.

<IMG SRC="../img/plugins/detection-parameters.png" width=700>

## Export Trace

Plot a trace, set some display parameters and export to a file. File formats include Png, Pdf, and SVG.

<IMG SRC="../img/plugins/export-trace.png" width=700>

## Summary Analysis

Display a table with a summary of analysis results and detection parameters. User can copy/paste into a spreadsheet for further analysis.

<IMG SRC="../img/plugins/summary-analysis.png" width=500>

## Summary Spikes

Display a table of all per-spike analysis results, one row per spike. User can copy/paste into spreadsheet for further analysis. This is the same information as when saving.

<IMG SRC="../img/plugins/summary-spikes.png" width=700>

## Error Summary

Display per-spike detection errors. Clicking on an error in the table will highlight the spike in the main interface.

<IMG SRC="../img/plugins/error-summary.png" width=700>

## FFT

Calculate and display the Power-Spectral-Density (PSD) of any recording using the Fast-Fourier-Transform (FFT).

<IMG SRC="../img/plugins/fft.png" width=700>

## Stim Gen

A plugin to generate stimuli and save them as csv or Axon Text Files (ATF). Optimized to generate noisy sin waves!

<IMG SRC="../img/plugins/stimgen.png" width=700>

## Sanpy Log

Display the SanPy log. As a user interacts with SanPY, most actions are logged to a file. This is useful for debugging and communicating with developers :)

<IMG SRC="../img/plugins/sanpy-log.png" width=700>
