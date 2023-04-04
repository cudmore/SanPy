import pandas as pd

from PyQt5 import QtWidgets

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class analysisSummary(sanpyPlugin):
    """Plugin to display overview of analysis.

    Notes
    -----
        QTableView: sanpy.interface.bErrorTable.errorTableView()
        QAbstractTableModel: sanpy.interface.bFileTable.pandasModel
    """

    myHumanName = "Summary Analysis"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.df = None

        # self.pyqtWindow()  # makes self.mainWidget

        layout = QtWidgets.QVBoxLayout()
        self.myErrorTable = sanpy.interface.bErrorTable.errorTableView()
        self.myErrorTable.setSortingEnabled(False)

        layout.addWidget(self.myErrorTable)

        # mar 17
        # self.setLayout(layout)
        self.getVBoxLayout().addLayout(layout)

        self.replot()

    def replot(self):
        """Grab a report from sanpy.bExport.getSummary()
        Put it in a table.
        """
        logger.info("")

        if self.ba is None:
            return

        exportObject = sanpy.bExport(self.ba)
        theMin, theMax = self.getStartStop()
        dfSummary = exportObject.getSummary(theMin=theMin, theMax=theMax)
        if dfSummary is not None:
            errorReportModel = sanpy.interface.bFileTable.pandasModel(dfSummary)
            self.myErrorTable.setModel(errorReportModel)
        else:
            # no spikes
            logger.info(f"No spikes to report")
            dfSummary = pd.DataFrame(columns=["", "", "", "", ""])
            errorReportModel = sanpy.interface.bFileTable.pandasModel(dfSummary)
            self.myErrorTable.setModel(errorReportModel)

        # hard-cde column widths
        self.myErrorTable.setColumnWidth(0, 300)
        self.myErrorTable.setColumnWidth(1, 300)

        #
        self.df = dfSummary

    def setAxis(self):
        # inherited
        # regenerate summary with new range
        self.replot()

    def copyToClipboard(self):
        if self.df is not None:
            print(self.df.head())
            self.df.to_clipboard(
                sep="\t", index=False
            )  # index=False so we do not duplicate 1s column
            logger.info("Copied to clipboard")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication([])

    # load and analyze sample data
    path = "/home/cudmore/Sites/SanPy/data/19114001.abf"
    ba = sanpy.bAnalysis(path)
    ba.spikeDetect()

    # open a plugin
    sa = analysisSummary(ba=ba, startStop=None)
    sa.show()

    sys.exit(app.exec_())
