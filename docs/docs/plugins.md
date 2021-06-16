SanPy supports user plugins. These are Python scripts that tap into the underlying architecture of the SanPy App.

With Plugins, users can easily extend the functionality of SanPy by:

 - Plot raw data
 - Plot analysis
 - Extend analysis in new ways
 - Link into the SanPy interface to respond to user selection, zooming, and file loading.

# Available plugins to get you started.

## plotRecording

Use Matplotlib to plot a recording with spike detection overlaid.

<IMG SRC="../img/plugins/plotRecording.png" width=700>

## scatterPlot

A plugin to plot x/y scatter plots of detection parameters. This is particularly useful because it demonstrates bi-directional signaling between a plugin and the main SanPy interface. In particular bi-direction spike selection and file switching.

<IMG SRC="../img/plugins/scatter-plot.png" width=700>

## plotTool

A fairly complex plugin to display a number of different plots including: Scatter, Histograms, Mean , etc.

<IMG SRC="../img/plugins/plot-tool.png" width=700>

## sanpyLog

A plugin to display the SanPy log. This is useful for debugging and communicating with developers :)

<IMG SRC="../img/plugins/sanpy-log.png" width=700>
