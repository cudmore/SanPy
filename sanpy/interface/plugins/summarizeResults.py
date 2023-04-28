# 20210619

from PyQt5 import QtCore, QtWidgets, QtGui

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin
# from sanpy.interface.plugins import ResponseType


class SummarizeResults(sanpyPlugin):
    """Plugin to display summary of analysis.

    Three versions are included
     - All: similar to what is exported to csv
     - Human Readable: A subset of human redable columns
     - Sweep summary: Report the mean/std/se/n etc for one sweep

    Uses:
        sanpy.bExport
        QTableView: sanpy.interface.bErrorTable.errorTableView()
        QAbstractTableModel: sanpy.interface.bFileTable.pandasModel
    """

    myHumanName = "Summarize Results"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # self.toggleResponseOptions(ResponseType.setSweep, False)  # we plot all sweeps
        # self.toggleResponseOptions(ResponseType.setAxis, False)

        self._reportType = 'Full Export'
        
        self.cardiacDf = None

        self._buildUI()

        self.replot()

    def _buildUI(self):

        self._buildingInterface = True

        layout = QtWidgets.QVBoxLayout()

        # one row of controls
        controlsLayout = QtWidgets.QHBoxLayout()
        layout.addLayout(controlsLayout)

        # the number of spikes in the report
        aLabel = QtWidgets.QLabel("Report Type")
        controlsLayout.addWidget(aLabel)

        #groupBox = QtWidgets.QGroupBox("Report Type")
        radio1 = QtWidgets.QRadioButton("Full Export")
        radio1.toggled.connect(lambda:self._on_radio_clicked(radio1))

        radio2 = QtWidgets.QRadioButton("Human Readable")
        radio2.toggled.connect(lambda:self._on_radio_clicked(radio2))

        radio3 = QtWidgets.QRadioButton("Sweep Summary")
        radio3.toggled.connect(lambda:self._on_radio_clicked(radio3))

        radio4 = QtWidgets.QRadioButton("Detection Errors")
        radio4.toggled.connect(lambda:self._on_radio_clicked(radio4))

        radio1.setChecked(True)

        controlsLayout.addWidget(radio1)
        controlsLayout.addWidget(radio2)
        controlsLayout.addWidget(radio3)
        controlsLayout.addWidget(radio4)

        # the number of spikes in the report
        self.numSpikesLabel = QtWidgets.QLabel("no spikes")
        controlsLayout.addWidget(self.numSpikesLabel)

        self.myErrorTable = sanpy.interface.bErrorTable.errorTableView()
        # TODO: derive a more general purpose table, here we are re-using error table
        self.myErrorTable.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Interactive
        )
        self.myErrorTable.horizontalHeader().setStretchLastSection(False)

        layout.addWidget(self.myErrorTable)

        # self.setLayout(layout)
        self.getVBoxLayout().addLayout(layout)

        #
        # connect clicks in error table to signal main sanpy_app with slot_selectSpike()
        logger.warning("mar 11 FIX SPIKE SELECTION")
        if self.getSanPyApp() is not None:
            fnPtr = self.getSanPyApp().slot_selectSpike
            self.myErrorTable.signalSelectSpike.connect(fnPtr)

        self._buildingInterface = False

    def _on_radio_clicked(self, radioButton):
        """Respond to user click in radio buttons.
        
        We receive this twice on each new radio button selection
        We receive false for what gets unselected and then true for the new selection.
        
        Only prococess True
        """
        if self._buildingInterface:
            return
        
        buttonName = radioButton.text()
        isChecked = radioButton.isChecked()
        logger.info(f'buttonName:{buttonName} isChecked:{isChecked}')
        if isChecked:
            self._reportType = buttonName
            self.replot()

    def setAxis(self):
        # inherited, resopnd to user setting x-axis
        self.replot()

    def replot(self):
        """Generate report with sanpy.bExport.report2()
        and put it into a table.
        """
        logger.info("")
        # update
        if self.ba is None:
            return

        # an export object to create any number of reports
        exportObject = sanpy.bExport(self.ba)

        startSec, stopSec = self.getStartStop()

        self.cardiacDf = None

        if self._reportType == 'Full Export':
            # v2, full export
            self.cardiacDf = exportObject.report3(
                sweep = self.sweepNumber,
                epoch = self.epochNumber,
                theMin=startSec,
                theMax=stopSec
            )  # report2 is more 'cardiac'
        
        elif self._reportType == 'Human Readable':
            # v1, human readable columns
            self.cardiacDf = exportObject.report2(
                sweep = self.sweepNumber,
                epoch = self.epochNumber,
                theMin=startSec,
                theMax=stopSec
            )  # report2 is more 'cardiac'

        elif self._reportType == 'Sweep Summary':
            # v3
            self.cardiacDf = exportObject.getSummary(
                sweep=self.sweepNumber,
                epoch=self.epochNumber,
                theMin=startSec,
                theMax=stopSec)

        elif self._reportType == 'Detection Errors':
            self.cardiacDf = self.ba.dfError

        else:
            logger.warning(f'Did not understand _reportType:{self._reportType}')

        if self.cardiacDf is None:
            return
    
        errorReportModel = sanpy.interface.bFileTable.pandasModel(self.cardiacDf)
        self.myErrorTable.setModel(errorReportModel)

        for colIdx in range(len(self.cardiacDf.columns)):
            if colIdx == 0:
                continue
            self.myErrorTable.setColumnWidth(colIdx, 170)

        self.numSpikesLabel.setText(f"{len(self.cardiacDf)} spikes")

    def copyToClipboard(self):
        if self.ba is not None and self.cardiacDf is not None:
            logger.info("Copy to clipboard")
            self.cardiacDf.to_clipboard(sep="\t", index=False)

    def selectSpikeList(self):
        spikeList = self.getSelectedSpikes()
        logger.info(f"{spikeList}")
        self.myErrorTable.mySelectRows(spikeList)


def main():
    path = "/home/cudmore/Sites/SanPy/data/19114001.abf"
    ba = sanpy.bAnalysis(path)
    ba.spikeDetect()
    print(ba.numSpikes)

    import sys

    app = QtWidgets.QApplication([])
    rt = SummarizeResults(ba=ba)
    rt.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
