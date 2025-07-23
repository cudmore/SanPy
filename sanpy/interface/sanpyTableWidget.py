import os
from functools import partial
from typing import List

import pandas as pd

from qtpy import QtCore, QtWidgets, QtGui

# from sanpy.interface.plugins import myStatListWidget

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class sanpyTable:
    def __init__(self, df: pd.DataFrame, fontSize=None):

        self._df = df

        numRows = len(df)

        columnList = list(df.columns)
        numColumns = len(columnList)

        # recent files
        myTableWidget = QtWidgets.QTableWidget()
        myTableWidget.setToolTip('Double-click to open')
        myTableWidget.setWordWrap(False)
        myTableWidget.setRowCount(numRows)
        myTableWidget.setColumnCount(numColumns)
        myTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        myTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        myTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        myTableWidget.cellClicked.connect(self._on_row_click)

        # hide the row headers
        myTableWidget.horizontalHeader().hide()

        myTableWidget.setHorizontalHeaderLabels(columnList)

        # set font size of table (default seems to be 13 point)
        if fontSize is not None:
            fnt = self.font()
            fnt.setPointSize(fontSize)
            myTableWidget.setFont(fnt)
            myTableWidget.horizontalHeader().setFont(fnt)
            myTableWidget.verticalHeader().setFont(fnt)


        header = myTableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        # QHeaderView will automatically resize the section to fill the available space. The size cannot be changed by the user or programmatically.
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

        # for idx, stat in enumerate(pathList):
        #     item = QtWidgets.QTableWidgetItem(stat)
        #     myTableWidget.setItem(idx, 0, item)
        #     myTableWidget.setRowHeight(idx, _rowHeight + _rowHeight + int(_rowHeight/2))

    def _on_row_click(self, rowIdx : int):
        """On double-click, open a file and close self.
        """
        path = self.recentFileList[rowIdx]
        logger.info(f'rowId:{rowIdx} path:{path}')

        if os.path.isfile(path):
            self._sanpyApp.openSanPyWindow(path)
            self.close()
        else:
            logger.error(f'did not find path: {path}')