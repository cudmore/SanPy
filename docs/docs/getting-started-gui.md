
These are tutorials to get started using the SanPy desktop GUI.

Please watch the videos as you follow along with a recipes.

## Load a file, detect spikes, and run some plugins

<iframe width="560" height="315" src="https://www.youtube.com/embed/OtxpjSrgPjY?si=tMCUb8qrjRdNwvd8" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>

**Recipe** for remaking the SanPy manuscript figure 3 from the GUI. Here we will load a raw data file, detect some spikes, and run some plugins.

1. Run SanPy
2. Select menu `File -> Open ...`
3. Open data file `2021_07_20_0010.abf` from the `data/` folder
4. Select a sweep with a number of spikes (for example, sweep 14)
5. Select `Fast Neuron` in the `Detection - Presets` popup
6. If it is not already shown, display the derivative of the recording with the `View - Derivative` menu
7. In the derivative plot, click and drag the horizontal cursor (C) to set the desired dvdt threshold for spike detection
8. Right click the derivative plot and select the  `Set dvdt Threshold` menu
9. Click the `Detect dV/dt` button in the `Detection` panel.

Finally, run the plugins to genarate Figure 3 a/b

10. Select the `Plugins - Plot Recording` menu, this will generate panel (a)
11. Select the `Plugins - Plot FI` menu, this will generate panel (b)

Screen shot of the main GUI.
![Figure 3](../img/figure-3/main-gui.png)

Right click the dvdt plot and select `Set dvdt Threshold`.
<IMG SRC="../img/figure-3/set-dvdt-threshold.png" width=200>

Figure 3a, the `Plot Recording` plugin.
![Figure 3a](../img/figure-3/plot-recording-plugin.png)

Figure 3b, the `Plot FI` plugin.
![Figure 3a](../img/figure-3/plot-fi-plugin.png)

## Loading a folder, detect spikes in multiple files, and run the Plot Tool (pool) plugin

<iframe width="560" height="315" src="https://www.youtube.com/embed/Z4_dgWxxPB0?si=IaVfZRSm-gNqQziY" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>

**Recipe** for remaking the SanPy manuscript Figure 4 from the GUI.

Please note, this will not be the same exact data but the plots will be similar.

1. Run SanPy
2. Use `Load Folder ...` to load the provided sample data in the `data/` folder.
3. Load and analyze two raw data files. Try with `19114001.abf` and `20191009_0005.abf`
4. Use the `Set Meta Data` plugin to set the `Condition1` of one file to `Control`, and the other file to `Drug`
3. Run the `Plot Tool (pool)` plugin
4. Set the interface as follows
    - Plot Type: Violin Plot
    - Hue: Condition1
    - X-Stat: Condition1
    - Y-Stat: Spike Frequency (Hz)

The plot in the plugin should look something like this

<IMG SRC="../img/figure-4/violin-spike-freq.png" width=200>

The step above can be repeated for any `Y-Stat` such as `Take Off Potential (mV)` or other.

Likewise, a scatter plot is easily created by selecting Plot Type `Scatter Plot` and choosing the desired X-Stat and Y-Stat.

<IMG SRC="../img/figure-4/scatter-spike-freq.png" width=200>

# Load a file, detect spikes, set spike conditions and plot with Plot Tool plugin

**Recipe** for remaking the SanPy manuscript Figure 6 from the GUI.

Please note, this will not be the same exact data but the plots will be similar.

<iframe width="560" height="315" src="https://www.youtube.com/embed/jaiFOsq3kGM?si=3DyejqH8C2wieaNp" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>

We are working on a recipe, check back soon!

