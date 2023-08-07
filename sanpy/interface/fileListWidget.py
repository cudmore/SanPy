from functools import partial

import numpy as np
import pandas as pd

from PyQt5 import QtWidgets, QtCore

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

    signalLoadFolder = QtCore.pyqtSignal(object, object)  # path, depth
    signalSetFolderDepth = QtCore.pyqtSignal(int)

    # signalSelectRow = QtCore.pyqtSignal(object, object, object)  # (row, rowDict, selectingAgain)
    # signalUpdateStatus = QtCore.pyqtSignal(object)
    """Update statu s in main SanPy app."""
    # signalSetDefaultDetection = QtCore.pyqtSignal(object, object)  # selected row, detection type

    def __init__(self, myModel: pandasModel, folderDepth:int=1,parent=None):
        """
        Parameters
        ----------
        myModel: sanpy.interface.bFileTable.pandasModel
        folderDepth : int
        """
        super().__init__(parent)
        self._myModel: pandasModel = myModel
        # self.setAcceptDrops(True)
        self._folderDepth = folderDepth
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

        buttonName = "Load Folder"
        button = QtWidgets.QPushButton(buttonName)
        # button.setToolTip('Save Detected Spikes to Excel file')
        button.clicked.connect(partial(self.on_button_click, buttonName))
        self._hToolbarLayout.addWidget(button, alignment=QtCore.Qt.AlignLeft)

        labelName = "Depth"
        aLabel = QtWidgets.QLabel(labelName)
        self._hToolbarLayout.addWidget(aLabel)

        aSpinBox = QtWidgets.QSpinBox()
        aSpinBox.setMinimum(1)
        aSpinBox.setMaximum(10)
        aSpinBox.setValue(self._folderDepth)
        aSpinBox.valueChanged.connect(self.on_depth_spin_box)
        self._hToolbarLayout.addWidget(aSpinBox, alignment=QtCore.Qt.AlignLeft)

        self._hToolbarLayout.addStretch()

        self._vLayout.addLayout(self._hToolbarLayout)

        #
        # actual list of file
        self._tableView = sanpy.interface.bTableView(self._myModel)
        self._vLayout.addWidget(self._tableView)

        self.setLayout(self._vLayout)

    def on_depth_spin_box(self, value):
        self._folderDepth = value
        self.signalSetFolderDepth.emit(value)

    def on_button_click(self, name):
        logger.info(f"{name}")
        if name == "Load Folder":
            self.signalLoadFolder.emit(None, self._folderDepth)

    def getDepth(self):
        """Get the folder depth."""
        return self._folderDepth
