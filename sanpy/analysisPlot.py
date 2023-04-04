import sys
from typing import Union, Dict, List, Tuple, Optional

import numpy as np
import scipy.signal
import seaborn as sns
import matplotlib.pyplot as plt

import sanpy

from sanpy.sanpyLogger import get_logger

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


def old_getHalfWidths(ba):
    """Get lines representing half-widhts (AP Dur).

    Args:
        ba (bAnalysis): bAnalysis object

    Returns:
        x,y (enum):
    """
    # defer until we know how many half-widths 20/50/80
    x = []
    y = []
    numPerSpike = 3  # rise/fall/nan
    # numSpikes = ba.numSpikes
    xyIdx = 0
    spikeDictionaries = ba.getSpikeDictionaries()  # for current sweep
    numSpikes = len(spikeDictionaries)
    # for idx, spike in enumerate(ba.spikeDict):
    for idx, spike in enumerate(spikeDictionaries):
        if idx == 0:
            # make x/y from first spike using halfHeights = [20,50,80]
            halfHeights = spike[
                "halfHeights"
            ]  # will be same for all spike, like [20, 50, 80]
            numHalfHeights = len(halfHeights)
            # *numHalfHeights to account for rise/fall + padding nan
            x = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
            y = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
            # print('  len(x):', len(x), 'numHalfHeights:', numHalfHeights, 'numSpikes:', numSpikes, 'halfHeights:', halfHeights)

        for idx2, width in enumerate(spike["widths"]):
            halfHeight = width["halfHeight"]  # [20,50,80]
            risingPnt = width["risingPnt"]
            risingVal = width["risingVal"]
            fallingPnt = width["fallingPnt"]
            fallingVal = width["fallingVal"]

            if risingPnt is None or fallingPnt is None:
                # half-height was not detected
                continue

            risingSec = ba.pnt2Sec_(risingPnt)
            fallingSec = ba.pnt2Sec_(fallingPnt)

            x[xyIdx] = risingSec
            x[xyIdx + 1] = fallingSec
            x[xyIdx + 2] = np.nan
            # y
            y[xyIdx] = fallingVal  # risingVal, to make line horizontal
            y[xyIdx + 1] = fallingVal
            y[xyIdx + 2] = np.nan

            # each spike has 3x pnts: rise/fall/nan
            xyIdx += numPerSpike  # accounts for rising/falling/nan
        # end for width
    # end for spike
    return x, y


class bAnalysisPlot:
    """
    Class to plot results of [sanpy.bAnalysis][sanpy.bAnalysis] spike detection.

    """

    def __init__(self, ba=None):
        """
        Args:
            ba: [sanpy.bAnalysis][sanpy.bAnalysis] object
        """
        self._ba = ba

    @property
    def ba(self):
        """Get underlying bAnalysis object."""
        return self._ba

    def getDefaultPlotStyle(self):
        """Get dictionary with default plot style."""
        d = {
            "linewidth": 1,
            "color": "k",
            "width": 9,
            "height": 3,
        }
        return d.copy()

    def _makeFig(self, plotStyle=None):
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

    def plotRaw(self, plotStyle=None, ax=None):
        """
        Plot raw recording

        Args:
            plotStye (float):
            ax (xxx):
        """

        if plotStyle is None:
            plotStyle = self.getDefaultPlotStyle()

        if ax is None:
            _fig, _ax = self._makeFig()
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
        plotThreshold=False,
        plotPeak=False,
        plotStyle=None,
        hue: Optional[str] = "condition",
        markerSize: Optional[int] = 4,
        ax=None,
    ):
        """Plot Vm with spike analysis overlaid as symbols

        Args:
            plotThreshold
            plotPeak
            plotStyle (dict): xxx
            markerSize
            ax (xxx): If specified will plot into a MatPlotLib axes

        Returns
            fig
            ax
        """

        legend = False

        if plotStyle is None:
            plotStyle = self.getDefaultPlotStyle()

        if ax is None:
            fig, ax = self._makeFig()
            fig.suptitle(self.ba.getFileName())
        # plot vm
        self.plotRaw(ax=ax)

        # plot spike times
        if plotThreshold:
            thresholdSec = self.ba.getStat("thresholdSec")  # x
            thresholdVal = self.ba.getStat("thresholdVal")  # y

            ax.plot(thresholdSec, thresholdVal, "pr", markersize=markerSize)
            df = self.ba.spikeDict.asDataFrame()  # regenerates, can be expensive
            # logger.info(f'df hue unique is: {df[hue].unique()}')
            # sns.scatterplot(x='thresholdSec', y='thresholdVal', hue=hue, data=df, ax=ax, legend=legend)

        # plot the peak
        if plotPeak:
            peakPnt = self.ba.getStat("peakPnt")
            # don't use this for Ca++ concentration
            # peakVal = self.ba.getStat('peakVal')
            peakVal = self.ba.fileLoader.sweepY[peakPnt]
            peakSec = [self.ba.fileLoader.pnt2Sec_(x) for x in peakPnt]
            ax.plot(peakSec, peakVal, "oc", markersize=markerSize)

        xUnits = self.ba.fileLoader.get_xUnits()
        yUnits = self.ba.fileLoader.get_yUnits()
        ax.set_xlabel(xUnits)
        ax.set_ylabel(yUnits)

        return ax

    def plotStat(self, xStat: str, yStat: str, hue: Optional[str] = None, ax=None):
        # ax : Optional["matplotlib.axes._subplots.AxesSubplot"] = None):

        legend = False

        if ax is None:
            fig, ax = self._makeFig()
            fig.suptitle(self.ba.getFileName())
        print(type(ax))

        df = self.ba.spikeDict.asDataFrame()  # regenerates, can be expensive
        sns.scatterplot(x=xStat, y=yStat, hue=hue, data=df, ax=ax, legend=legend)

    def plotTimeSeries(ba, stat, halfWidthIdx=0, ax=None):
        """Plot a given spike parameter."""
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

        # Leave this none, if we pass none, ba.getSpikeClipsWill take care of this
        """
        if preClipWidth_ms is None:
            preClipWidth_ms = self.ba.detectionClass['preSpikeClipWidth_ms']
        if postClipWidth_ms is None:
            postClipWidth_ms = self.ba.detectionClass['postSpikeClipWidth_ms']
        """
        sweepNumber = 0
        theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(
            startSec,
            stopSec,
            spikeSelection=selectedSpikeList,
            preSpikeClipWidth_ms=preClipWidth_ms,
            postSpikeClipWidth_ms=postClipWidth_ms,
            sweepNumber=sweepNumber,
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

    def plotPhasePlot(self, oneSpikeNumber=None, ax=None):
        if ax is None:
            grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(grid[0, 0:])  # Vm, entire sweep

        filteredClip = scipy.signal.medfilt(self.spikeClips[oneSpikeNumber], 3)
        dvdt = np.diff(filteredClip)
        # add an initial point so it is the same length as raw data in abf.sweepY
        dvdt = np.concatenate(([0], dvdt))
        (line,) = ax.plot(filteredClip, dvdt, "y")

        ax.set_ylabel("filtered dV/dt")
        ax.set_xlabel("filtered Vm (mV)")

        return line


def test_plot(path):
    print("=== test_plot() path:", path)
    ba = sanpy.bAnalysis(path)

    # detect
    dDict = sanpy.bAnalysis.getDefaultDetection()
    dDict["dvdThreshold"] = 50
    ba.spikeDetect(dDict)

    # plot
    bp = sanpy.bAnalysisPlot(ba)

    fig = bp.plotDerivAndRaw()

    fig = bp.plotSpikes()

    plt.show()


if __name__ == "__main__":
    path = "data/19114001.abf"
    test_plot(path)

    # TODO: check if error

    path = "data/19114001.csv"
    test_plot(path)
