"""Matplotlib helpers for plotting SanPy recordings and analysis results."""

from typing import Any, Optional, TYPE_CHECKING

import numpy as np
import scipy.signal

import sanpy

from sanpy.sanpyLogger import get_logger

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

logger = get_logger(__name__)


def old_getEddLines(ba):
    """Get lines representing linear fit of EDD rate.

    Args:
        ba (bAnalysis): bAnalysis object
    """
    logger.info(ba)

    x = []
    y = []
    if ba is None or ba.numSpikes == 0:
        return x, y

    # these are getting for current sweep
    preLinearFitPnt0 = ba.getStat("preLinearFitPnt0")
    preLinearFitSec0 = [ba.pnt2Sec_(x) for x in preLinearFitPnt0]
    preLinearFitVal0 = ba.getStat("preLinearFitVal0")

    preLinearFitPnt1 = ba.getStat("preLinearFitPnt1")
    preLinearFitSec1 = [ba.pnt2Sec_(x) for x in preLinearFitPnt1]
    preLinearFitVal1 = ba.getStat("preLinearFitVal1")

    thisNumSpikes = len(preLinearFitPnt0)
    # for idx, spike in enumerate(range(ba.numSpikes)):
    for idx, spike in enumerate(range(thisNumSpikes)):
        dx = preLinearFitSec1[idx] - preLinearFitSec0[idx]
        dy = preLinearFitVal1[idx] - preLinearFitVal0[idx]

        lineLength = 8  # TODO: make this a function of spike frequency?

        x.append(preLinearFitSec0[idx])
        x.append(preLinearFitSec1[idx] + lineLength * dx)
        x.append(np.nan)

        y.append(preLinearFitVal0[idx])
        y.append(preLinearFitVal1[idx] + lineLength * dy)
        y.append(np.nan)

        # print('here')

    return x, y

class bAnalysisPlot:
    """Plot a recording and its spike-detection results with Matplotlib.

    Attributes:
        ba: Analysis whose recording and results will be plotted.

    Examples:
        Plot detected spike thresholds and peaks:

        ``axes = bAnalysisPlot(analysis).plotSpikes(plotThreshold=True, plotPeak=True)``
    """

    def __init__(self, ba: sanpy.bAnalysis) -> None:
        """Initialize a plotter for an analysis.

        Args:
            ba: Loaded SanPy analysis to plot.
        """
        self._ba = ba

    @property
    def ba(self) -> sanpy.bAnalysis:
        """Return the analysis being plotted."""
        return self._ba

    def getDefaultPlotStyle(self) -> dict[str, Any]:
        """Return a new dictionary containing the default plot style."""
        d = {
            "linewidth": 1,
            "color": "k",
            "width": 9,
            "height": 3,
        }
        return d.copy()

    def _makeFig(
        self, plotStyle: Optional[dict[str, Any]] = None
    ) -> tuple["Figure", "Axes"]:
        """Create a single-panel Matplotlib figure.

        Args:
            plotStyle: Plot appearance values. The default style is used when
                omitted.

        Returns:
            The new figure and its axes.
        """
        import matplotlib.pyplot as plt

        if plotStyle is None:
            plotStyle = self.getDefaultPlotStyle()

        grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

        width = plotStyle["width"]
        height = plotStyle["height"]
        fig = plt.figure(figsize=(width, height))
        ax = fig.add_subplot(grid[0, 0:])  # Vm, entire sweep

        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)

        return fig, ax

    def plotRaw(
        self,
        plotStyle: Optional[dict[str, Any]] = None,
        ax: Optional["Axes"] = None,
    ) -> "Axes":
        """Plot the active sweep's raw recording.

        Args:
            plotStyle: Plot appearance values. The default style is used when
                omitted.
            ax: Existing Matplotlib axes. New axes are created when omitted.

        Returns:
            Axes containing the plotted recording.
        """

        if plotStyle is None:
            plotStyle = self.getDefaultPlotStyle()

        if ax is None:
            _fig, _ax = self._makeFig(plotStyle)
            _fig.suptitle(f"{self._ba.fileLoader.filepath}")
        else:
            _ax = ax

        color = plotStyle["color"]
        linewidth = plotStyle["linewidth"]
        sweepX = self.ba.fileLoader.sweepX
        sweepY = self.ba.fileLoader.sweepY

        _ax.plot(
            sweepX, sweepY, "-", c=color, linewidth=linewidth
        )  # fmt = '[marker][line][color]'

        xUnits = self.ba.fileLoader.get_xUnits()
        yUnits = self.ba.fileLoader.get_yUnits()
        _ax.set_xlabel(xUnits)
        _ax.set_ylabel(yUnits)

        return _ax

    def plotDerivAndRaw(self):
        """
        Plot both Vm and the derivative of Vm (dV/dt).

        Args:
            fig (matplotlib.pyplot.figure): An existing figure to plot to.
                see: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.figure.html

        Return:
            fig and axs
        """

        import matplotlib.pyplot as plt

        #
        # make a 2-panel figure
        grid = plt.GridSpec(2, 1, wspace=0.2, hspace=0.4)
        fig = plt.figure(figsize=(10, 8))
        ax1 = fig.add_subplot(grid[0, 0])
        ax2 = fig.add_subplot(grid[1, 0], sharex=ax1)
        ax1.spines["right"].set_visible(False)
        ax1.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)
        ax2.spines["top"].set_visible(False)

        self.plotRaw(ax=ax1)

        sweepX = self.ba.fileLoader.sweepX
        filteredDeriv = self.ba.fileLoader.filteredDeriv
        ax2.plot(sweepX, filteredDeriv)

        ax2.set_ylabel("dV/dt")
        # ax2.set_xlabel('Seconds')

        return fig, [ax1, ax2]

    def plotSpikes(
        self,
        plotThreshold: bool = False,
        plotPeak: bool = False,
        plotStyle: Optional[dict[str, Any]] = None,
        hue: Optional[str] = "condition",
        markerSize: Optional[int] = 4,
        ax: Optional["Axes"] = None,
    ) -> "Axes":
        """Plot the active voltage sweep with detected spikes overlaid.

        Run ``bAnalysis.spikeDetect()`` before requesting threshold or peak
        overlays.

        Args:
            plotThreshold: Whether to mark detected spike thresholds.
            plotPeak: Whether to mark detected spike peaks.
            plotStyle: Plot appearance values. The default style is used when
                omitted.
            hue: Reserved for backward compatibility and currently unused.
            markerSize: Matplotlib marker size for thresholds and peaks.
            ax: Existing Matplotlib axes. New axes are created when omitted.

        Returns:
            Axes containing the recording and requested analysis overlays.
        """
        if plotStyle is None:
            plotStyle = self.getDefaultPlotStyle()

        if ax is None:
            fig, ax = self._makeFig(plotStyle)
            fig.suptitle(self.ba.getFileName())
        # plot vm
        self.plotRaw(plotStyle=plotStyle, ax=ax)

        current_sweep = self.ba.fileLoader.currentSweep

        # plot spike times
        if plotThreshold:
            thresholdSec = self.ba.getStat(
                "thresholdSec", sweepNumber=current_sweep
            )
            thresholdVal = self.ba.getStat(
                "thresholdVal", sweepNumber=current_sweep
            )

            ax.plot(
                thresholdSec,
                thresholdVal,
                "pr",
                markersize=markerSize,
                label="Threshold",
            )

        # plot the peak
        if plotPeak:
            peakPnt = self.ba.getStat("peakPnt", sweepNumber=current_sweep)
            # don't use this for Ca++ concentration
            # peakVal = self.ba.getStat('peakVal')
            peakVal = self.ba.fileLoader.sweepY[peakPnt]
            peakSec = [self.ba.fileLoader.pnt2Sec_(x) for x in peakPnt]
            ax.plot(
                peakSec,
                peakVal,
                "oc",
                markersize=markerSize,
                label="Peak",
            )

        xUnits = self.ba.fileLoader.get_xUnits()
        yUnits = self.ba.fileLoader.get_yUnits()
        ax.set_xlabel(xUnits)
        ax.set_ylabel(yUnits)

        return ax

    def plotStat(self, xStat: str, yStat: str, hue: Optional[str] = None, ax=None):
        # ax : Optional["matplotlib.axes._subplots.AxesSubplot"] = None):

        import seaborn as sns

        legend = False

        if ax is None:
            fig, ax = self._makeFig()
            fig.suptitle(self.ba.getFileName())
        print(type(ax))

        df = self.ba.spikeDict.asDataFrame()  # regenerates, can be expensive
        sns.scatterplot(x=xStat, y=yStat, hue=hue, data=df, ax=ax, legend=legend)

    def plotTimeSeries(ba, stat, halfWidthIdx=0, ax=None):
        """Plot a given spike parameter."""
        import matplotlib.pyplot as plt
        if stat == "peak":
            yStatName = "peakVal"
            yStatLabel = "Spike Peak (mV)"
        if stat == "preMin":
            yStatName = "preMinVal"
            yStatLabel = "Pre Min (mV)"
        if stat == "halfWidth":
            yStatName = "widthPnts"
            yStatLabel = "Spike Half Width (ms)"

        #
        # pull
        statX = []
        statVal = []
        for i, spike in enumerate(ba.spikeDict):
            if i == 0 or i == len(ba.spikeTimes) - 1:
                continue
            else:
                statX.append(spike["peakSec"])
                if stat == "halfWidth":
                    statVal.append(spike["widths"][halfWidthIdx]["widthMs"])
                else:
                    statVal.append(spike[yStatName])

        #
        # plot
        if ax is None:
            grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(grid[0, 0:])  # Vm, entire sweep

        ax.plot(statX, statVal, "o-k")

        ax.set_ylabel(yStatLabel)
        ax.set_xlabel("Time (sec)")

        return statVal

    def plotISI(ba, ax=None):
        """Plot the inter-spike-interval (sec) between each spike threshold"""
        import matplotlib.pyplot as plt
        #
        # pull
        spikeTimes_sec = [x / ba.dataPointsPerMs / 1000 for x in ba.spikeTimes]
        isi = np.diff(spikeTimes_sec)
        isi_x = spikeTimes_sec[0:-1]

        #
        # plot
        if ax is None:
            grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(grid[0, 0:])  # Vm, entire sweep

        ax.plot(isi_x, isi, "o-k")

        ax.set_ylabel("Inter-Spike-Interval (sec)")
        ax.set_xlabel("Time (sec)")

    def plotClips(
        self, plotType="Raw", preClipWidth_ms=None, postClipWidth_ms=None, ax=None
    ):
        """Plot clips of all detected spikes

        Clips are created in self.spikeDetect() and default to clipWidth_ms = 100 ms

        Args:
            plotType (str): From [Raw, RawPlusMean, Mean, SD, Var]
            #plotVariance (bool): If tru, plot variance. Otherwise plot all raw clips (black) with mean (red)

        Returns:
            xPlot
            yPlot
        """

        import matplotlib.pyplot as plt

        """
        if ax is None:
            grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(grid[0, 0:]) #Vm, entire sweep
        """

        if self.ba.numSpikes == 0:
            return None, None

        if ax is None:
            fig, ax = self._makeFig()
            fig.suptitle(self.ba.getFileName())

        startSec, stopSec = None, None
        selectedSpikeList = []
        # preClipWidth_ms = 200
        # postClipWidth_ms = 1000

        # Leave this none, if we pass none, spike_clips.get uses detection widths
        """
        if preClipWidth_ms is None:
            preClipWidth_ms = self.ba.detectionClass['preSpikeClipWidth_ms']
        if postClipWidth_ms is None:
            postClipWidth_ms = self.ba.detectionClass['postSpikeClipWidth_ms']
        """
        sweepNumber = 0
        theseClips, theseClips_x, meanClip = self.ba.spike_clips.get(
            startSec,
            stopSec,
            spike_selection=selectedSpikeList,
            pre_spike_clip_width_ms=preClipWidth_ms,
            post_spike_clip_width_ms=postClipWidth_ms,
            sweep_number=sweepNumber,
        )
        numClips = len(theseClips)

        # convert clips to 2d ndarray ???
        xTmp = np.array(theseClips_x)
        # xTmp /= self.ba.dataPointsPerMs * 1000  # pnt to seconds
        xTmp /= 1000  # ms to seconds
        yTmp = np.array(theseClips)  # mV

        # TODO: plot each clip as different color
        # this will show variation in sequential clips (for Ca++ imaging they are decreasing)
        # print(xTmp.shape)  # ( e.g. (9,306)
        # sys.exit(1)

        # plot variance
        if plotType == "Mean":
            xPlot = np.nanmean(xTmp, axis=0)  # xTmp is in ms
            yPlot = np.nanmean(yTmp, axis=0)
            ax.plot(xPlot, yPlot, "-k", linewidth=1)
            ax.set_ylabel("Mean")
            ax.set_xlabel("Time (sec)")
        elif plotType == "Var":
            xPlot = np.nanmean(xTmp, axis=0)  # xTmp is in ms
            yPlot = np.nanvar(yTmp, axis=0)
            ax.plot(xPlot, yPlot, "-k", linewidth=1)
            ax.set_ylabel("Variance")
            ax.set_xlabel("Time (sec)")
        elif plotType == "SD":
            xPlot = np.nanmean(xTmp, axis=0)  # xTmp is in ms
            yPlot = np.nanstd(yTmp, axis=0)
            ax.plot(xPlot, yPlot, "-k", linewidth=1)
            ax.set_ylabel("STD")
            ax.set_xlabel("Time (sec)")
        elif plotType in ["Raw", "RawPlusMean"]:
            # plot raw
            # logger.info('PLOTTING RAW')

            cmap = plt.get_cmap("jet")
            colors = [cmap(i) for i in np.linspace(0, 1, numClips)]

            for i in range(numClips):
                color = colors[i]
                xPlot = xTmp[i, :]
                yPlot = yTmp[i, :]
                # I want different colors here
                # ax.plot(xPlot, yPlot, '-k', linewidth=0.5)
                # WHY IS THIS NOT WORKING !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                # logger.info(f'!!!!!!!!!!!!!!!!!!!!!! plotting color g {plotType} {color}')
                # ax.plot(xPlot, yPlot, '-g', linewidth=0.5, color='g')
                ax.plot(xPlot, yPlot, "-", label=f"{i}", color=color, linewidth=0.5)

            yLabel = self.ba._sweepLabelY
            ax.set_ylabel(yLabel)
            ax.set_xlabel("Time (sec)")

            # plot mean
            if plotType == "RawPlusMean":
                xMeanClip = np.nanmean(xTmp, axis=0)  # xTmp is in ms
                yMeanClip = np.nanmean(yTmp, axis=0)
                ax.plot(xMeanClip, yMeanClip, "-r", linewidth=1)

            # show legend for each raw race 0,1,2,3,...
            ax.legend(loc="best")

        else:
            logger.error(f"Did not understand plot type: {plotType}")

        #
        return xPlot, yPlot

    def plotPhasePlot(
        self, oneSpikeNumber: Optional[int] = None, ax: Optional["Axes"] = None
    ) -> Optional[Any]:
        """Plot one sweep-0 spike clip as filtered Vm versus its derivative.

        Args:
            oneSpikeNumber: Detection spike index within sweep 0. ``None``
                plots nothing.
            ax: Axes to draw on. ``None`` creates a new figure.

        Returns:
            The plotted line, or ``None`` when that spike has no clip.
        """
        if oneSpikeNumber is None or self.ba.numSpikes == 0:
            return None

        result = self.ba.spike_clips.get(
            None,
            None,
            spike_selection=[oneSpikeNumber],
            sweep_number=0,
        )
        if result is None:
            return None
        clips, _clips_x, _mean_clip = result
        if len(clips) == 0:
            return None

        if ax is None:
            import matplotlib.pyplot as plt

            grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(grid[0, 0:])

        filtered_clip = scipy.signal.medfilt(clips[0], 3)
        dvdt = np.diff(filtered_clip)
        dvdt = np.concatenate(([0], dvdt))
        (line,) = ax.plot(filtered_clip, dvdt, "y")

        ax.set_ylabel("filtered dV/dt")
        ax.set_xlabel("filtered Vm (mV)")

        return line
