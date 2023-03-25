from pprint import pprint

from PyQt5 import QtCore, QtWidgets, QtGui

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin

class resultsTable(sanpyPlugin):
    """Plugin to display summary of all spikes, one spike per row.

    Uses:
        QTableView: sanpy.interface.bErrorTable.errorTableView()
        QAbstractTableModel: sanpy.interface.bFileTable.pandasModel
    """
    myHumanName = 'Summary Spikes'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        #self.pyqtWindow() # makes self.mainWidget

        # layout = QtWidgets.QVBoxLayout()

        # topToolbarLayout0, topToolbarLayout1 = self._buildTopToolbar()  # horizontal toolbar with checkboxes to toggle signals
        # layout.addLayout(topToolbarLayout0)
        # layout.addLayout(topToolbarLayout1)

        # TODO: derive a more general purpose table, here we are re-using error table
        self.myErrorTable = sanpy.interface.bErrorTable.errorTableView()
        self.myErrorTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive);
        self.myErrorTable.horizontalHeader().setStretchLastSection(False)

        #layout.addWidget(self.myErrorTable)
        self.getVBoxLayout().addWidget(self.myErrorTable)

        #self.setLayout(layout)

        #
        # connect clicks in error table to signal main sanpy_app with slot_selectSpike()
        logger.warning('FIX SPIKE SELECTION')
        if self.getSanPyApp() is not None:
            fnPtr = self.getSanPyApp().slot_selectSpike
            self.myErrorTable.signalSelectSpike.connect(fnPtr)

        self.replot()

    def setAxis(self):
        # inherited, resopnd to user setting x-axis
        self.replot()

    def _getReport(self):
        dfPlot = self.ba.asDataFrame()
        return dfPlot

    def replot(self):
        logger.info('')
        # update
        if self.ba is None:
            return

        startSec, stopSec = self.getStartStop()

        dfPlot = self._getReport()

        if dfPlot is not None:
            if startSec is not None and stopSec is not None:
                # use column thresholdSec
                dfPlot = dfPlot[ (dfPlot['thresholdSec']>=startSec) & (dfPlot['thresholdSec']<=stopSec)]
                #pass
            #
            logger.info(f'dfReportForScatter {startSec} {stopSec}')
            errorReportModel = sanpy.interface.bFileTable.pandasModel(dfPlot)
            self.myErrorTable.setModel(errorReportModel)

            # mar 21, when did i get rid of this?
            # self._fileLabel.setText(f'{self.ba.fileLoader.filename}')
            # self._numSpikesLabel.setText(f'{len(dfPlot)} spikes')

    def copyToClipboard(self):
        if self.ba is not None:
            dfPlot = self._getReport()
            if dfPlot is not None:
                logger.info('Copy to clipboard')
                dfPlot.to_clipboard(sep='\t', index=False)

def main():
    path = 'data/19114001.abf'
    ba = sanpy.bAnalysis(path)

    bd = sanpy.bDetection()  # gets default
    dDict = bd.getDetectionDict('SA Node')

    ba.spikeDetect(dDict)
    #print(ba.numSpikes)

    #print(ba.spikeDict._myList[0])
    #_df = ba.asDataFrame()
    #pprint(_df)

    # does not work, _myList[3] is class sanpy.analysisResults.analysisResult
    # print('qqqqqqqqqq')
    # print(ba.spikeDict._myList[3])

    #pprint(ba.spikeDict.asDataFrame())

    # print('=== 2')
    # print(ba.spikeDict[2])

    #sys.exit()

    import sys
    app = QtWidgets.QApplication([])
    rt = resultsTable(ba=ba)
    rt.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
