from functools import partial

from PyQt5 import QtGui, QtCore, QtWidgets
import numpy as np
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)
from PyQt5.QtCore import pyqtSignal

from sanpy.kym.kymRoiMetaData import KymRoiMetaData
from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


class MetaDataWidget(QtWidgets.QWidget):
    def __init__(self, kymRoiMetaData: KymRoiMetaData):
        super().__init__()

        self._kymRoiMetaData = kymRoiMetaData

        self._buildUI()

    def _buildUI(self):
        vBox = QtWidgets.QVBoxLayout()
        vBox.setContentsMargins(0, 0, 0, 0)
        vBox.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(vBox)

        for key, v in self._kymRoiMetaData.items():
            if not self._kymRoiMetaData.showInGui(key):
                continue

            hBox = QtWidgets.QHBoxLayout()
            hBox.setAlignment(QtCore.Qt.AlignLeft)
            vBox.addLayout(hBox)

            aLabel = QtWidgets.QLabel(key)
            hBox.addWidget(aLabel)

            _allowEdit = self._kymRoiMetaData.allowTextEdit(key)
            if _allowEdit:
                aLineEdit = QtWidgets.QLineEdit(v)
                aLineEdit.editingFinished.connect(
                    partial(self.on_text_edit, aLineEdit, key)
                )
                hBox.addWidget(aLineEdit)

            else:
                vStr = str(v)
                aLabel = QtWidgets.QLabel(vStr)
                hBox.addWidget(aLabel)

    def on_text_edit(self, aWidget, key):
        strValue = aWidget.text()
        logger.info(f'key:"{key}" strValue:{strValue}')
        self._kymRoiMetaData.setParam(key, strValue)
