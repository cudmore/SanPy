#20210619

from PyQt5 import QtCore, QtWidgets, QtGui

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
#import sanpy.interface
from sanpy.interface.plugins import sanpyPlugin

class resultsTable2(sanpyPlugin):
    """
    Plugin to display 'human readable' summary of all spikes, one spike per row.

    Uses:
        sanpy.bExport.report2()
        QTableView: sanpy.interface.bErrorTable.errorTableView()
        QAbstractTableModel: sanpy.interface.bFileTable.pandasModel
    """
    myHumanName = 'Summary Spikes (Full)'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cardiacDf = None

        layout = QtWidgets.QVBoxLayout()

        controlsLayout = QtWidgets.QHBoxLayout()
        self.numSpikesLabel = QtWidgets.QLabel('unknown spikes')
        controlsLayout.addWidget(self.numSpikesLabel)
        layout.addLayout(controlsLayout)

        self.myErrorTable = sanpy.interface.bErrorTable.errorTableView()
        # TODO: derive a more general purpose table, here we are re-using error table
        self.myErrorTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive);
        self.myErrorTable.horizontalHeader().setStretchLastSection(False)

        layout.addWidget(self.myErrorTable)

        self.setLayout(layout)

        #
        # connect clicks in error table to signal main sanpy_app with slot_selectSpike()
        if self.getSanPyApp() is not None:
            fnPtr = self.getSanPyApp().slot_selectSpike
            self.myErrorTable.signalSelectSpike.connect(fnPtr)

        self.replot()

    def setAxis(self):
        # inherited, resopnd to user setting x-axis
        self.replot()

    def replot(self):
        """Generate report with sanpy.bExport.report2()
        and put it into a table.
        """
        logger.info('')
        # update
        if self.ba is None:
            return

        myExport = sanpy.bExport(self.ba)

        startSec, stopSec = self.getStartStop()
        if startSec is None or stopSec is None:
            startSec = 0
            stopSec = self.ba.fileLoader.recordingDur

        self.cardiacDf = myExport.report2(startSec, stopSec) # report2 is more 'cardiac'

        logger.info(f' generated df len:{len(self.cardiacDf)} startSec:{startSec} stopSec:{stopSec}')

        errorReportModel = sanpy.interface.bFileTable.pandasModel(self.cardiacDf)
        self.myErrorTable.setModel(errorReportModel)

        for colIdx in range(len(self.cardiacDf.columns)):
            if colIdx == 0:
                continue
            self.myErrorTable.setColumnWidth(colIdx, 170)

        self.numSpikesLabel.setText(f'{len(self.cardiacDf)} spikes')

    def copyToClipboard(self):
        if self.ba is not None and self.cardiacDf is not None:
            logger.info('Copy to clipboard')
            self.cardiacDf.to_clipboard(sep='\t', index=False)

def main():
    path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
    ba = sanpy.bAnalysis(path)
    ba.spikeDetect()
    print(ba.numSpikes)

    import sys
    app = QtWidgets.QApplication([])
    rt = resultsTable2(ba=ba)
    rt.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
