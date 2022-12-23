from functools import partial

import numpy as np
import pandas as pd

from PyQt5 import QtWidgets

import sanpy
import sanpy.interface
import sanpy.bDetection
from sanpy.interface.bFileTable import pandasModel

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class fileListWidget(QtWidgets.QWidget):
    """A widget showing
        - file list controls
        - file list widget, see: sanpy.interface.bTableView
    """

    #signalSelectRow = QtCore.pyqtSignal(object, object, object)  # (row, rowDict, selectingAgain)
    #signalUpdateStatus = QtCore.pyqtSignal(object)
    """Update status in main SanPy app."""
    #signalSetDefaultDetection = QtCore.pyqtSignal(object, object)  # selected row, detection type

    def __init__(self, myModel : pandasModel, parent=None):
        """
        Args:
            myModel: sanpy.interface.bFileTable.pandasModel
        """
        super().__init__(parent)
        self._myModel : pandasModel = myModel
        # self.setAcceptDrops(True)
        self._buildUI()

    # def dragEnterEvent(self, event):
    #     logger.info('')
    
    # def dropEvent(self, event):
    #     logger.info('')

    def mySetModel(self, theModel):
        """
        Args:
            theModel: sanpy.interface.bFileTable.pandasModel
        """
        self._myModel = theModel
        self._tableView.mySetModel(theModel)

    def getTableView(self):
        return self._tableView

    def _buildUI(self):
        self._vLayout = QtWidgets.QVBoxLayout()

        self._hToolbarLayout = QtWidgets.QHBoxLayout()

        buttonName = 'fileListWidget button'
        button = QtWidgets.QPushButton(buttonName)
        #button.setToolTip('Save Detected Spikes to Excel file')
        button.clicked.connect(partial(self.on_button_click,buttonName))
        self._hToolbarLayout.addWidget(button)

        self._vLayout.addLayout(self._hToolbarLayout)

        # actual list of file
        self._tableView = sanpy.interface.bTableView(self._myModel)
        self._vLayout.addWidget(self._tableView)

        self.setLayout(self._vLayout)

    def on_button_click(Self, name):
        logger.info(f'{name}')





