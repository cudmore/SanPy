from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin


class exampleUserPlugin1(sanpyPlugin):
    """
    Plot x/y statistics as a scatter

    Get stat names and variables from sanpy.bAnalysisUtil.getStatList()
    """

    myHumanName = "Example User Plugin 1"

    def __init__(self, **kwargs):
        """
        Args:
            ba (bAnalysis): Not required
        """
        super().__init__(**kwargs)

        self.plot()
        self.replot()

    def plot(self):
        """Create the plot in the widget (called once)."""
        self.mplWindow2()  # assigns (self.fig, self.axs)

        # white line with raw data
        (self.line,) = self.axs.plot([], [], "-w", linewidth=0.5)

        # red circles with spike threshold
        (self.lineDetection,) = self.axs.plot([], [], "ro")

    def replot(self):
        """Replot the widget. Usually when the file is switched"""

        logger.info("")

        if self.ba is None:
            return

        # get the x/y values from the recording
        sweepX = self.getSweep("x")  # self.ba.sweepX(sweepNumber=self.sweepNumber)
        sweepY = self.getSweep("y")  # self.ba.sweepY(sweepNumber=self.sweepNumber)

        # update plot of raw data
        self.line.set_data(sweepX, sweepY)

        # update plot of spike threshold
        thresholdSec = self.getStat("thresholdSec")
        thresholdVal = self.getStat("thresholdVal")
        self.lineDetection.set_data(thresholdSec, thresholdVal)

        # make sure the matplotlib axis auto scale
        self.axs.relim()
        self.axs.autoscale_view(True, True, True)

        # plt.draw()
        self.static_canvas.draw()


if __name__ == "__main__":
    # load an example file
    path = "/Users/cudmore/Sites/SanPy/data/19114001.abf"
    ba = sanpy.bAnalysis(path)

    # set detection parameters
    detectionPreset = sanpy.bDetection.detectionPresets.default
    detectionClass = sanpy.bDetection(detectionPreset=detectionPreset)

    # detectionClass['preSpikeClipWidth_ms'] = 100
    # detectionClass['postSpikeClipWidth_ms'] = 400

    # spike detect
    ba.spikeDetect(detectionClass=detectionClass)
    print(ba)

    # run the plugin
    import sys
    from PyQt5 import QtCore, QtWidgets  # , QtGui

    app = QtWidgets.QApplication([])
    sc = exampleUserPlugin1(ba=ba)
    sc.show()
    sc.replot()

    sys.exit(app.exec_())
