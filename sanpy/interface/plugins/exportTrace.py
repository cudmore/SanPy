import numpy as np
# import scipy.signal

from PyQt5 import QtWidgets

import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin

# from sanpy.bAnalysisUtil import statList

class exportTrace(sanpyPlugin):
    """ 
    """

    myHumanName = "Export Trace"

    def __init__(self, **kwargs):
        super(exportTrace, self).__init__(**kwargs)

        # this plugin will not respond to any interface changes
        # self.turnOffAllSignalSlot()

        self.mainWidget = None

        self.plot()

    def _trace_xy(self) -> tuple[np.ndarray, np.ndarray] | tuple[None, None]:
        """Return the time base and Y values for this export.

        An integer plugin sweep selects that column. ``All`` keeps the loader
        current sweep, because this export is one trace.

        Returns:
            Time in seconds and the matching Y values, or ``(None, None)``
            when no recording is loaded.
        """
        if self.ba is None:
            return None, None
        sweep_x = self.ba.fileLoader.sweepX
        if isinstance(self.sweepNumber, int):
            sweep_y = self.ba.fileLoader.get_sweep_y(self.sweepNumber)
        else:
            sweep_y = self.ba.fileLoader.sweepY
        return sweep_x, sweep_y

    def replot(self) -> None:
        """Refresh the exported trace for the plugin's selected sweep."""
        logger.info(f"sweepNumber: {self.sweepNumber}")

        if self.mainWidget is None:
            self.plot()

        x, y = self._trace_xy()
        self.mainWidget.switchFile(self.ba, x, y)

    def plot(self) -> None:
        """Build the export widget for the selected trace."""
        if self.ba is None:
            return

        self.myType = "vmFiltered"

        if self.myType == "vmFiltered":
            xyUnits = ("Time (sec)", "Vm (mV)")  # todo: pass xMin,xMax to constructor
            x, y = self._trace_xy()
        elif self.myType == "dvdtFiltered":
            xyUnits = (
                "Time (sec)",
                "dV/dt (mV/ms)",
            )  # todo: pass xMin,xMax to constructor
        elif self.myType == "meanclip":
            xyUnits = ("Time (ms)", "Vm (mV)")  # todo: pass xMin,xMax to constructor
        else:
            logger.error(f'Unknown myType: "{self.myType}"')
            xyUnits = ("error time", "error y")

        path = self.ba.fileLoader.filepath

        xMin, xMax = self.getStartStop()
        """
        xMin = None
        xMax = None
        if self.myType in ['clip', 'meanclip']:
            xMin, xMax = self.detectionWidget.clipPlot.getAxis('bottom').range
        else:
            xMin, xMax = self.detectionWidget.getXRange()
        """

        if self.myType in ["vm", "dvdt"]:
            xMargin = 2  # seconds
        else:
            xMargin = 2

        # a large x margin was causing matplotlib erors when a swep was short, like 0.2 sec
        xMargin = 0

        tmpLayout = QtWidgets.QVBoxLayout()

        darkTheme = True
        if self.getSanPyApp() is not None:
            darkTheme = self.getSanPyApp().useDarkStyle
        
        self.mainWidget = sanpy.interface.bExportWidget(
            x,
            y,
            xyUnits=xyUnits,
            path=path,
            xMin=xMin,
            xMax=xMax,
            xMargin=xMargin,
            type=self.myType,
            darkTheme=darkTheme,
        )
        # darkTheme=self.detectionWidget.useDarkStyle)

        tmpLayout.addWidget(self.mainWidget)

        # rewire existing widget into plugin architecture
        # self.mainWidget.closeEvent = self.onClose
        # self._mySetWindowTitle()

        # self.setCentralWidget(self.mainWidget)
        # self.setLayout(tmpLayout)
        self.getVBoxLayout().addLayout(tmpLayout)


if __name__ == "__main__":
    path = "/Users/cudmore/Sites/SanPy/data/19114001.abf"
    ba = sanpy.bAnalysis(path)
    ba.spikeDetect()
    print(ba.numSpikes)

    import sys

    app = QtWidgets.QApplication([])
    et = exportTrace(ba=ba)
    et.show()

    path2 = "/Users/cudmore/Sites/SanPy/data/19114000.abf"
    ba2 = sanpy.bAnalysis(path2)
    et.mainWidget.switchFile(ba2)

    sys.exit(app.exec_())
