# 20210609
import numpy as np
import scipy.signal

from PyQt5 import QtCore, QtWidgets, QtGui

import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

import sanpy
from sanpy import bAnalysis
from sanpy.interface.plugins import sanpyPlugin
from sanpy.bAnalysisUtil import statList
from sanpy.interface.plugins import (
    ResponseType,
)  # to toggle response to set sweeps, etc


class plotRecording(sanpyPlugin):
    """
    Example of matplotlib plugin.
    """

    myHumanName = "Plot Recording"

    def __init__(self, **kwargs):
        super(plotRecording, self).__init__(**kwargs)

        # this is a very simple plugin, do not respond to changes in interface
        # switchFile = self.responseTypes.switchFile
        # self.toggleResponseOptions(switchFile, newValue=False)

        # analysisChange = self.responseTypes.analysisChange
        # self.toggleResponseOptions(analysisChange, newValue=False)

        # selectSpike = self.responseTypes.selectSpike
        # self.toggleResponseOptions(selectSpike, newValue=False)

        # we are plotting all sweeps and all axis, turn these off
        self.toggleResponseOptions(ResponseType.setSweep, False)  # we plot all sweeps
        self.toggleResponseOptions(ResponseType.setAxis, False)

        setAxis = self.responseTypes.setAxis
        self.toggleResponseOptions(setAxis, newValue=False)

        self.rawLine = None
        self.thresholdLine = None

        self.plot()
        self.replot()

    def plot(self):
        # if self.ba is None:
        #     return

        self.mplWindow2()  # assigns (self.fig, self.axs)

        return

    def replot(self):
        """bAnalysis has been updated, replot"""
        logger.info(f"{self.ba}")

        if self.ba is None:
            return

        self.xOffset = 0.01
        self.yOffset = 50

        xCurrentOffset = 0
        yCurrentOffset = 0

        currentSweep = self.ba.fileLoader.currentSweep
        numSweeps = self.ba.fileLoader.numSweeps

        self.fig.clear(True)
        self.axs = self.fig.add_subplot(1, 1, 1)

        """
        if self.rawLine is not None:
            for line in self.rawLine:
                line.clear()
        self.rawLine = [None] * numSweeps
        
        if self.thresholdLine is not None:
            for line in self.thresholdLine:
                line.clear()
        self.thresholdLine = [None] * numSweeps
        """
        self.rawLine = [None] * numSweeps
        self.thresholdLine = [None] * numSweeps

        _penColor = self.getPenColor()

        for sweepIdx in range(numSweeps):
            self.ba.fileLoader.setSweep(sweepIdx)

            # self.axs[_idx].self.fig.add_subplot(numSweeps, 1, _idx)

            sweepX = self.getSweep("x")
            sweepY = self.getSweep("y")

            self.sweepX = sweepX
            self.sweepY = sweepY

            (self.rawLine[sweepIdx],) = self.axs.plot(
                sweepX + xCurrentOffset,
                sweepY + yCurrentOffset,
                "-",
                color=_penColor,
                linewidth=0.5,
            )

            thresholdSec = self.ba.getStat("thresholdSec", sweepNumber=sweepIdx)
            thresholdSec = [x + xCurrentOffset for x in thresholdSec]
            thresholdVal = self.ba.getStat("thresholdVal", sweepNumber=sweepIdx)
            thresholdVal = [x + yCurrentOffset for x in thresholdVal]
            markersize = 4
            self.thresholdLine[sweepIdx] = self.axs.plot(
                thresholdSec, thresholdVal, "r.", markersize=markersize
            )
            """
            if thresholdSec is None or thresholdVal is None:
                self.thresholdLine[sweepIdx].set_data([], [])
            else:
                self.thresholdLine[sweepIdx] = self.axs.plot(thresholdSec, thresholdSec, 'o')
            """

            """
            xHW, yHW = self.getHalfWidths()
            self.lineHW, = self.axs.plot(xHW, yHW, '-')
            """

            xCurrentOffset += self.xOffset
            yCurrentOffset += self.yOffset

        self.axs.relim()
        self.axs.autoscale_view(True, True, True)

        self.ba.fileLoader.setSweep(currentSweep)
        self.static_canvas.draw_idle()
        plt.draw()

    def old_getEddLines(self):
        preLinearFitPnt0 = self.ba.getStat("preLinearFitPnt0")
        preLinearFitSec0 = [self.ba.fileLoader.pnt2Sec_(x) for x in preLinearFitPnt0]
        preLinearFitVal0 = self.ba.fileLoader.getStat("preLinearFitVal0")

        preLinearFitPnt1 = self.ba.getStat("preLinearFitPnt1")
        preLinearFitSec1 = [self.ba.fileLoader.pnt2Sec_(x) for x in preLinearFitPnt1]
        preLinearFitVal1 = self.ba.getStat("preLinearFitVal1")

        x = []
        y = []
        for idx in range(self.ba.numSpikes):
            try:
                dx = preLinearFitSec1[idx] - preLinearFitSec0[idx]
                dy = preLinearFitVal1[idx] - preLinearFitVal0[idx]
            except IndexError as e:
                logger.error(
                    f"spike {idx} preLinearFitSec1:{len(preLinearFitSec1)} preLinearFitSec0:{len(preLinearFitSec0)}"
                )
                logger.error(
                    f"spike {idx} preLinearFitPnt1:{len(preLinearFitPnt1)} preLinearFitPnt0:{len(preLinearFitPnt0)}"
                )

            lineLength = 4  # TODO: make this a function of spike frequency?

            try:
                x.append(preLinearFitSec0[idx])
                x.append(preLinearFitSec1[idx] + lineLength * dx)
                x.append(np.nan)

                y.append(preLinearFitVal0[idx])
                y.append(preLinearFitVal1[idx] + lineLength * dy)
                y.append(np.nan)
            except IndexError as e:
                logger.error(
                    f"preLinearFitSec0:{len(preLinearFitSec0)} preLinearFitSec1:{len(preLinearFitSec1)}"
                )
                logger.error(e)

        return x, y

    def getHalfWidths(self):
        """Get x/y pair for plotting all half widths.

        DOes not work with new version because of sweeps.
        """
        # defer until we know how many half-widths 20/50/80
        x = []
        y = []
        numPerSpike = 3  # rise/fall/nan
        numSpikes = self.ba.numSpikes
        xyIdx = 0
        for idx, spike in enumerate(self.ba.spikeDict):
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
                # risingVal = width['risingVal']
                risingVal = self.sweepY[risingPnt]
                fallingPnt = width["fallingPnt"]
                # fallingVal = width['fallingVal']
                fallingVal = self.sweepY[fallingPnt]

                if risingPnt is None or fallingPnt is None:
                    # half-height was not detected
                    continue

                risingSec = self.ba.fileLoader.pnt2Sec_(risingPnt)
                fallingSec = self.ba.fileLoader.pnt2Sec_(fallingPnt)

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

    def selectSpikeList(self):
        """Only respond to single spike selection."""
        logger.info("")
        spikeList = self.getSelectedSpikes()

        if spikeList == [] or len(spikeList) > 1:
            return

        if self.ba is None:
            return

        spikeNumber = spikeList[0]

        thresholdSec = self.ba.getStat("thresholdSec")
        spikeTime = thresholdSec[spikeNumber]
        xMin = spikeTime - 0.5
        xMax = spikeTime + 0.5

        self.axs.set_xlim(xMin, xMax)

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def old_slot_selectSpike(self, eDict):
        logger.info(eDict)
        spikeNumber = eDict["spikeNumber"]
        # doZoom = eDict['doZoom']

        if spikeNumber is None:
            return

        if self.ba is None:
            return

        thresholdSec = self.ba.getStat("thresholdSec")
        spikeTime = thresholdSec[spikeNumber]
        xMin = spikeTime - 0.5
        xMax = spikeTime + 0.5

        self.axs.set_xlim(xMin, xMax)

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()


def testPlot():
    import os

    file_path = os.path.realpath(__file__)  # full path to this file
    file_path = os.path.split(file_path)[0]  # folder for this file
    path = os.path.join(file_path, "../../../data/19114001.abf")

    ba = bAnalysis(path)
    if ba.loadError:
        print("error loading file")
        return
    ba.spikeDetect()

    # create plugin
    ap = plotRecording(ba=ba)

    # ap.plot()

    # ap.slotUpdateAnalysis()


def main():
    path = "/Users/cudmore/Sites/SanPy/data/2021_07_20_0010.abf"
    ba = sanpy.bAnalysis(path)
    ba.spikeDetect()
    print(ba.numSpikes)

    import sys

    app = QtWidgets.QApplication([])
    pr = plotRecording(ba=ba)
    pr.show()
    sys.exit(app.exec_())


def testLoad():
    import os, glob

    pluginFolder = "/Users/cudmore/sanpy_plugins"
    files = glob.glob(os.path.join(pluginFolder, "*.py"))
    for file in files:
        # if file.startswith('.'):
        #    continue
        if file.endswith("__init__.py"):
            continue
        print(file)


if __name__ == "__main__":
    # testPlot()
    # testLoad()
    main()
