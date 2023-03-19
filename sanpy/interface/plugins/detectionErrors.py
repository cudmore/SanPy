import pandas as pd

from PyQt5 import QtWidgets

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class detectionErrors(sanpyPlugin):
    """
    Plugin to display detection errors

    Uses:
        QTableView: sanpy.interface.bErrorTable.errorTableView()
        QAbstractTableModel: sanpy.interface.bFileTable.pandasModel
    """
    myHumanName = 'Summary Error'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        #self.pyqtWindow() # makes self.mainWidget

        self._dfError = None

        layout = QtWidgets.QVBoxLayout()

        self.myErrorTable = sanpy.interface.bErrorTable.errorTableView()
        self.myErrorTable.setWordWrap(False)

        layout.addWidget(self.myErrorTable)

        #self.setLayout(layout)
        self.getVBoxLayout().addLayout(layout)
        
        #
        # connect clicks in error table to siganl main sanpy_app with slot_selectSpike()
        logger.warning('mar 11 FIX SPIKE SELECTION')
        if self.getSanPyApp() is not None:
            fnPtr = self.getSanPyApp().slot_selectSpike
            self.myErrorTable.signalSelectSpike.connect(fnPtr)

        self.replot()

    def replot(self):
        # update
        # todo: get default columns from ???
        self._dfError = pd.DataFrame(columns=['Spike', 'Seconds', 'Type', 'Details'])

        if self.ba is not None:
            if self.ba.dfError is not None:
                self._dfError = self.ba.dfError
        #
        if self._dfError is not None:
            errorReportModel = sanpy.interface.bFileTable.pandasModel(self._dfError)
            self.myErrorTable.setModel(errorReportModel)
        else:
            logger.error('Did not get error df from bAnalysis')

    def copyToClipboard(self):
        if self._dfError is not None:
            self._dfError.to_clipboard(sep='\t', index=False)
            logger.info('Error table copied to clipboard')

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication([])
    spl = detectionErrors()
    spl.show()
    sys.exit(app.exec_())
