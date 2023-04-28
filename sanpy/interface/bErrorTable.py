from typing import List

from PyQt5 import QtCore, QtGui, QtWidgets

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class errorTableView(QtWidgets.QTableView):
    """
    Display a per spike error table (one row per spike eror)
    """

    signalSelectSpike = QtCore.Signal(object)  # spike number, doZoom

    def __init__(self, parent=None):
        super(errorTableView, self).__init__(parent)

        # self.setFont(QtGui.QFont('Arial', 10))

        self._blockTableUpdate = False

        self.setSortingEnabled(True)

        # self.setSizePolicy(
        #     QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        # )

        _hHeader = self.horizontalHeader()
        _hHeader.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        # _hHeader.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)

        # see
        # https://stackoverflow.com/questions/38098763/pyside-pyqt-how-to-make-set-qtablewidget-column-width-as-proportion-of-the-a
        # _hHeader = self.horizontalHeader()       
        # _hHeader.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        # _hHeader.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        # _hHeader.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

        # self.setSelectionMode(QtWidgets.QTableView.SingleSelection)

        self.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
            | QtWidgets.QAbstractItemView.DoubleClicked
        )

        # equally stretchs each columns so that they fit the table's width.
        # self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch);
        self.horizontalHeader().setStretchLastSection(True)

        # removed mar 2023
        # rowHeight = 11
        # fnt = self.font()
        # fnt.setPointSize(rowHeight)
        # self.setFont(fnt)
        # self.verticalHeader().setDefaultSectionSize(rowHeight);

        # self.resizeColumnsToContents()

        self.clicked.connect(self.errorTableClicked)
        self.doubleClicked.connect(self._on_doubleClick)

    def mySelectRows(self, rows: List[int]):
        """Select rows in the table

        TODO: Hold off on this, we need to define a sort proxy. See PyMapManager tables.
        """
        return

        logger.info(f"rows:{rows}")

        # to stop event recursion
        self._blockTableUpdate = True

        selectionModel = self.selectionModel()
        if selectionModel:
            selectionModel.clear()

            if rows:
                indexes = [self.model().index(r, 0) for r in rows]  # [QModelIndex]
                visualRows = [
                    self.proxy.mapFromSource(modelIndex) for modelIndex in indexes
                ]

                mode = (
                    QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows
                )
                [self.selectionModel().select(i, mode) for i in visualRows]

                # scroll so first row in rows is visible
                # TODO (cudmore) does not work if list is filtered
                column = 0
                row = list(rows)[0]
                index = self.model().index(row, column)
                self.scrollTo(
                    index, QtWidgets.QAbstractItemView.PositionAtTop
                )  # EnsureVisible
            else:
                # print('  CLEARING SELECTION')
                self.clearSelection()

        #
        self._blockTableUpdate = False

    def _on_doubleClick(self, index):
        """
        Parameters
        ----------
        index : QtCore.QModelIndex
        """
        row = self.model()._data.index[index.row()]  # take sorting into account
        logger.info(index.row())
        self.errorTableClicked(index, doubleClick=True)

    def errorTableClicked(self, index, doubleClick=False):
        """
        Parameters
        ----------
        index : QtCore.QModelIndex
        """
        row = self.model()._data.index[index.row()]  # take sorting into account

        doZoom = doubleClick
        # modifiers = QtWidgets.QApplication.keyboardModifiers()
        # if modifiers == QtCore.Qt.ShiftModifier:
        #     # zoomm on shift+click
        #     doZoom = True

        try:
            # .loc[i,'col'] gets from index label (correct)
            # .iloc[i,j] gets absolute row (wrong)
            spikeNumber = self.model()._data.loc[row, "Spike"]
        except KeyError as e:
            # for results plugin
            try:
                spikeNumber = self.model()._data.loc[row, "spikeNumber"]
            except KeyError as e:
                logger.warning(f'KeyError looking for column "Spike" or "spikeNumber"')
                return
        spikeNumber = int(spikeNumber)

        dDict = {
            "spikeNumber": spikeNumber,
            "doZoom": doZoom,
        }
        logger.info(f"  -->> emit signalSelectSpike with dDict")
        logger.info(dDict)

        # self._blockSlots = True
        self.signalSelectSpike.emit(dDict)

        # self._blockSlots = False
