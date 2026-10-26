"""File-table view for the SanPy desktop window."""

import math
import os
import platform
import subprocess
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtGui, QtWidgets

import sanpy
import sanpy.interface

# import sanpy.analysisDir
import sanpy.bDetection

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

REQUIRED_FILE_COLUMNS: frozenset[str] = frozenset({"L", "A", "S", "N", "E", "File"})
"""File-table columns that stay visible and do not appear in the Columns menu."""

DEFAULT_HIDDEN_FILE_COLUMNS: tuple[str, ...] = (
    "Epochs",
    "kHz",
    "Mode",
    "animal_id",
    "species",
    "region",
    "cell_type",
    "age",
    "sex",
    "experiment",
    "parent3",
    "relPath",
    "uuid",
)
"""Optional file-table columns hidden until the user shows them."""


def hidden_file_column_keys(
    stored: object,
    known_columns: Iterable[str],
) -> list[str]:
    """Return optional file-table columns that should be hidden.

    Args:
        stored: Saved hidden-column value. A missing value or a non-list uses
            ``DEFAULT_HIDDEN_FILE_COLUMNS``. An empty list hides nothing.
        known_columns: Column keys currently defined for the file table.

    Returns:
        Hidden column keys that are known and not required, in stored order.
    """
    candidates = stored if isinstance(stored, list) else DEFAULT_HIDDEN_FILE_COLUMNS
    known = {str(column) for column in known_columns}
    hidden: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        if candidate not in known or candidate in REQUIRED_FILE_COLUMNS:
            continue
        if candidate in hidden:
            continue
        hidden.append(candidate)
    return hidden


def file_manager_reveal_label() -> str:
    """Return the context-menu label for revealing a recording.

    Returns:
        Finder, Explorer, or file-manager label for the current platform.
    """
    system = platform.system()
    if system == "Darwin":
        return "Reveal in Finder"
    if system == "Windows":
        return "Show in Explorer"
    return "Show in File Manager"


def recording_path_for_visual_row(
    table: sanpy.analysisDir,
    visual_row: int,
) -> str | None:
    """Return the recording path for one visible file-table row.

    Args:
        table: Folder catalog backing the file table.
        visual_row: Row position in the current table order.

    Returns:
        Full path stored for that row, or None when the row or its relative
        path is missing.
    """
    row_labels = table.index
    if visual_row < 0 or visual_row >= len(row_labels):
        return None
    relative_path = table.loc[row_labels[visual_row], "relPath"]
    if not isinstance(relative_path, str) or relative_path == "":
        return None
    return table.getPathFromRelPath(relative_path)


def reveal_in_file_manager(file_path: str) -> bool:
    """Reveal a file in the platform file manager.

    macOS uses Finder and Windows uses Explorer. Linux asks the desktop file
    manager to select the file, then opens the parent folder if that call fails.

    Args:
        file_path: Path of the file to reveal.

    Returns:
        True when the platform command accepts the request. A missing file
        returns False.
    """
    try:
        path = Path(file_path).resolve()
    except OSError:
        return False
    if not path.is_file():
        return False

    system = platform.system()
    if system == "Darwin":
        return _run_reveal_command(["open", "-R", str(path)])
    if system == "Windows":
        if '"' in str(path):
            logger.warning(f'Cannot reveal a path that contains a quote: "{path}"')
            return False
        # Explorer treats a space after the comma as a separate argument, and
        # it exits 1 after a successful handoff to the running shell.
        return _run_reveal_command(
            f'explorer.exe /select,"{path}"',
            accept_any_exit_code=True,
        )
    if system == "Linux":
        return _reveal_with_linux_file_manager(path)
    logger.warning(f'No file-manager reveal for platform "{system}"')
    return False


def _run_reveal_command(
    command: list[str] | str,
    accept_any_exit_code: bool = False,
) -> bool:
    """Run one file-manager command.

    Args:
        command: Argument list, or a Windows command line that must preserve quotes.
        accept_any_exit_code: Whether any exit code counts as success.

    Returns:
        True when the command starts and, unless requested, exits 0.
    """
    try:
        completed = subprocess.run(command, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning(f"Could not run file-manager command: {exc}")
        return False
    if accept_any_exit_code:
        return True
    return completed.returncode == 0


def _reveal_with_linux_file_manager(path: Path) -> bool:
    """Select a file in the Linux file manager, or open its parent folder.

    Args:
        path: Existing file to reveal.

    Returns:
        True when either the file-manager call or the folder fallback accepts
        the request.
    """
    dbus_command = [
        "dbus-send",
        "--session",
        "--print-reply",
        "--reply-timeout=5000",
        "--dest=org.freedesktop.FileManager1",
        "/org/freedesktop/FileManager1",
        "org.freedesktop.FileManager1.ShowItems",
        f'array:string:"{path.as_uri()}"',
        'string:""',
    ]
    try:
        completed = subprocess.run(
            dbus_command,
            check=False,
            timeout=5,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning(f"File manager selection failed: {exc}")
    else:
        if completed.returncode == 0:
            return True
        logger.warning(
            f"File manager selection failed with exit code {completed.returncode}"
        )

    try:
        completed = subprocess.run(["xdg-open", str(path.parent)], check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning(f"Could not open the parent folder: {exc}")
        return False
    return completed.returncode == 0


class bTableView(QtWidgets.QTableView):
    """Table view to display list of files."""

    """
    signalUnloadRow = QtCore.pyqtSignal(object)  # row index
    signalRemoveFromDatabase = QtCore.pyqtSignal(object)  # row index
    signalDuplicateRow = QtCore.pyqtSignal(object)  # row index
    signalDeleteRow = QtCore.pyqtSignal(object)  # row index
    #signalRefreshTabe = QtCore.pyqtSignal(object) # row index
    signalCopyTable = QtCore.pyqtSignal()
    signalFindNewFiles = QtCore.pyqtSignal()

    signalSaveFileTable = QtCore.pyqtSignal()
    # Save entire database as pandas hsf.
    """

    signalSelectRow = QtCore.pyqtSignal(
        object, object, object
    )  # (row, rowDict, selectingAgain)

    signalFileSelectionChanged = QtCore.pyqtSignal(object)
    """Emit selected recording keys in current visual-row order."""

    signalUpdateStatus = QtCore.pyqtSignal(object)
    """Update status in main SanPy app."""

    signalSetDefaultDetection = QtCore.pyqtSignal(
        object, object
    )  # selected row, detection type

    def __init__(self, model, parent=None):
        """
        Args:
            model: sanpy.interface.bFileTable.pandasModel
        """
        super().__init__(parent=parent)

        # self.setAcceptDrops(True)
        # self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        # self.setDropIndicatorShown(True)

        self.lastSeletedRow = None
        self._mousePressActive = False
        self._selectionChangedDuringMousePress = False
        self.clicked.connect(self.onLeftClick)

        self.mySetModel(model)

        # frozen table was my attempt to keep a few columns always on the left
        # this led to huge problems and is not worth it

        # (L, A, S, N, I(include), File)
        """
        self.numFrozenColumns = 6 # depends on columns in analysisDir

        self.frozenTableView = QtWidgets.QTableView(self)
        self.frozenTableView.clicked.connect(self.onLeftClick)
        self.frozenTableView.setSortingEnabled(True)
        self.frozenTableView.setSelectionBehavior(QtWidgets.QTableView.SelectRows)  # abb
        # only allow one row to be selected
        self.frozenTableView.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.initFrozenColumn()
        """

        # dec 2022, not needed
        # self.horizontalHeader().sectionResized.connect(self.updateSectionWidth)
        # self.verticalHeader().sectionResized.connect(self.updateSectionHeight)

        _hHeader = self.horizontalHeader()
        _hHeader.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        # _hHeader.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        """
        self.frozenTableView.verticalScrollBar().valueChanged.connect(self.verticalScrollBar().setValue)
        self.verticalScrollBar().valueChanged.connect(self.frozenTableView.verticalScrollBar().setValue)
        """

        # rewire contextMenuEvent to self (WIERD BUT SEEMS TO WORK)
        """
        self.frozenTableView.contextMenuEvent = self.contextMenuEvent
        """

        #
        # original
        # self.doIncludeCheckbox = False  # todo: turn this on
        # need a local reference to delegate else 'segmentation fault'
        # self.keepCheckBoxDelegate = myCheckBoxDelegate(self)
        # self.setItemDelegateForColumn(1, self.keepCheckBoxDelegate)

        self.setSortingEnabled(True)

        self.setAlternatingRowColors(True)

        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.setSelectionMode(QtWidgets.QTableView.ExtendedSelection)

        # TODO: add font size to options
        """
        _fonSize = 10
        self.setFont(QtGui.QFont('Arial', _fonSize))
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                            QtWidgets.QSizePolicy.Expanding)
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        
        # only allow one row to be selected, should ignore shift+click
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)


        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers
                            | QtWidgets.QAbstractItemView.DoubleClicked)

        self.horizontalHeader().setStretchLastSection(True)

        rowHeight = _fonSize + 1
        fnt = self.font()
        fnt.setPointSize(rowHeight)

        self.setFont(fnt)
        self.verticalHeader().setDefaultSectionSize(rowHeight)
        """

        # todo: minimize all column widths
        # for col in range(showNumCol):
        #    self.frozenTableView.setColumnWidth(col, self.columnWidth(col))

        # frozen column
        # self.frozenTableView.setFont(QtGui.QFont('Arial', 10))
        """
        self.frozenTableView.setFont(fnt)
        self.frozenTableView.verticalHeader().setDefaultSectionSize(rowHeight)
        """

        # original was this
        # active background-color: #346792;
        # !active background-color: #37414F;
        # removed for manuscript 2023
        # qss = """
        #     QTableView::item:selected:active {
        #         background-color: #346792;
        #     }

        #     QTableView::item:selected:!active {
        #         color: #E0E1E3;
        #         background-color: #346792;
        #     }
        #     """
        # this almost works but header becomes white???
        # self.setStyleSheet(qss)

    # def dragEnterEvent(self, event):
    #     logger.info('')

    # def dropEvent(self, event):
    #     logger.info('')

    #
    # frozen
    def _old_initFrozenColumn(self):
        self.frozenTableView.setModel(self.model())

        # this is causing selection to be in muted blue
        # self.frozenTableView.setFocusPolicy(QtCore.Qt.NoFocus)

        self.frozenTableView.verticalHeader().hide()
        # self.frozenTableView.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.viewport().stackUnder(self.frozenTableView)

        # self.frozenTableView.setStyleSheet('''
        #    QtWidgets.QTableView { border: none;
        #                 background-color: #8EDE21;
        #                 selection-background-color: #999;
        #    }''') # for demo purposes

        self.frozenTableView.setSelectionModel(self.selectionModel())

        # hide trailing column
        for col in range(self.numFrozenColumns, self.model().columnCount()):
            self.frozenTableView.setColumnHidden(col, True)

        # set width of remaining columns, does not have an effect ???
        for col in range(self.numFrozenColumns):
            # print('  col:', col, 'widht:', self.columnWidth(col))
            columnWidth = self.columnWidth(col)
            columnWidth = 28
            self.frozenTableView.setColumnWidth(col, columnWidth)
            # self.setColumnWidth(col, columnWidth)
        # columnWidth = 150
        # self.frozenTableView.setColumnWidth(self.numFrozenColumns-1, columnWidth)
        # self.setColumnWidth(self.numFrozenColumns-1, columnWidth)

        # self.frozenTableView.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
        #                    QtWidgets.QSizePolicy.Expanding)

        self.frozenTableView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.frozenTableView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.frozenTableView.show()
        self.updateFrozenTableGeometry()
        self.setHorizontalScrollMode(self.ScrollPerPixel)
        self.setVerticalScrollMode(self.ScrollPerPixel)
        self.frozenTableView.setVerticalScrollMode(self.ScrollPerPixel)

        # set Loaded and Analyzed columns
        self.frozenTableView.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents
        )
        self.frozenTableView.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeToContents
        )
        self.frozenTableView.horizontalHeader().setStretchLastSection(True)

    def getSelectedRowDict(self):
        selectedRows = self.selectionModel().selectedRows()
        if len(selectedRows) == 0:
            return None
        else:
            selectedItem = selectedRows[0]
            selectedRow = selectedItem.row()
        rowDict = self.model().myGetRowDict(selectedRow)
        return rowDict

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Let the Qt selection model handle keyboard navigation.

        Args:
            event: Key event forwarded to the base table view.
        """
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Track whether a mouse press changed the row selection.

        Args:
            event: Mouse event forwarded to the base table view.
        """
        self._mousePressActive = event.button() == QtCore.Qt.LeftButton
        self._selectionChangedDuringMousePress = False
        try:
            super().mousePressEvent(event)
        finally:
            self._mousePressActive = False

    def selectionChanged(
        self,
        selected: QtCore.QItemSelection,
        deselected: QtCore.QItemSelection,
    ) -> None:
        """Emit stable file keys after the Qt row selection changes.

        Args:
            selected: Newly selected model indexes.
            deselected: Newly deselected model indexes.
        """
        super().selectionChanged(selected, deselected)
        if self._mousePressActive:
            self._selectionChangedDuringMousePress = True
        selection_model = self.selectionModel()
        model = self.model()
        if selection_model is None or model is None:
            self.signalFileSelectionChanged.emit(())
            return
        visual_rows = sorted(index.row() for index in selection_model.selectedRows())
        file_keys = tuple(
            model._data.get_file_key(model._data.index[visual_row])
            for visual_row in visual_rows
        )
        self.signalFileSelectionChanged.emit(file_keys)

    def onLeftClick(self, item: QtCore.QModelIndex) -> None:
        """Refresh an unchanged single-row selection.

        Selection changes are handled by :meth:`selectionChanged`. This path
        preserves the existing behavior where clicking the only selected row
        again refreshes that displayed recording.

        Args:
            item: Clicked model index.
        """
        if self._selectionChangedDuringMousePress:
            self._selectionChangedDuringMousePress = False
            return
        if len(self.selectionModel().selectedRows()) != 1:
            return
        row = item.row()
        realRow = self.model()._data.index[row]  # sort order
        # logger.info(f'User clicked row:{row} realRow:{realRow}')
        self._onLeftClick(realRow)

    def selectRowByFile(self, filename : str):
        # fileList = self.model()._data['File'].tolist()
        df = self.model()._data._df
        fileIndexList = df.index[df['File'] == filename].tolist()
        if fileIndexList:
            rowIdx = fileIndexList[0]
            self._onLeftClick(rowIdx)
        else:
            logger.warning(f"Did not find file {filename} in {df['File'].tolist()}")

    def select_row_silently(self, real_row: int) -> None:
        """Select a source row without emitting the file-click signal.

        A row that is already selected keeps the current cell and the
        horizontal scroll position from the click. A newly selected row is
        scrolled into view vertically, and the horizontal scrollbar is restored.

        Args:
            real_row: Dataframe index identifying the recording row.
        """
        indexes = list(self.model()._data.index)
        if real_row not in indexes:
            return
        visual_row = indexes.index(real_row)
        row_is_selected = any(
            index.row() == visual_row for index in self.selectionModel().selectedRows()
        )
        if not row_is_selected:
            horizontal = self.horizontalScrollBar().value()
            self.selectRow(visual_row)
            # Bypass this class's scrollTo override, which ignores column 0,
            # so the selected row can scroll into view vertically.
            super().scrollTo(
                self.currentIndex(), QtWidgets.QAbstractItemView.EnsureVisible
            )
            self.horizontalScrollBar().setValue(horizontal)
        self.lastSeletedRow = real_row

    def _onLeftClick(self, realRow):
        rowDict = self.model().myGetRowDict(realRow)

        logger.info(f"=== User click row:{realRow} relPath:{rowDict['relPath']}")

        # always emit on click, keep track if row was already selected
        # if self.lastSeletedRow is None or self.lastSeletedRow != realRow:
        if 1:
            selectedAgain = self.lastSeletedRow == realRow
            # new row selection
            # print('  new row selection')
            # logger.info(f'realRow:{realRow} rowDict:{rowDict}')
            logger.info('-->> emit signalSelectRow')
            self.signalSelectRow.emit(realRow, rowDict, selectedAgain)
        else:
            # print('  handle another click on already selected row')
            pass

        # print('!!!!! TODO: _onLeftClick needs to always emit on click but pass along if row was already selected')
        self.lastSeletedRow = realRow

    def _old_selectionChanged(self, selected, deselected):
        logger.info("")
        modelIndexList = selected.indexes()
        if len(modelIndexList) == 0:
            return

        super(bTableView, self).selectionChanged(selected, deselected)
        # self.frozenTableView.selectionChanged(selected, deselected)
        modelIndex = modelIndexList[0]
        # row = modelIndex.row()
        column = modelIndex.column()

        realRow = self.model()._data.index[modelIndex.row()]

        # assuming model is my pandas model
        rowDict = self.model().myGetRowDict(realRow)

        logger.info(f"realRow:{realRow} col:{column} {rowDict}")

        self.signalSelectRow.emit(realRow, rowDict)

    def mySetModel(self, model: QtCore.QAbstractItemModel) -> None:
        """Set the model and apply saved column visibility.

        An empty dataframe is the startup model and is left unchanged.

        Args:
            model: ``sanpy.interface.bFileTable.pandasModel`` for the file table.
        """
        self.setModel(model)
        self._apply_hidden_columns()

    def mySelectRow(self, rowIdx):
        """Needed to connect main and frozen table."""
        # logger.info('')

        self.selectRow(rowIdx)
        """
        self.frozenTableView.selectRow(rowIdx)
        """

    """
    # trying to use this to remove tooltip when it comes up as empty ''
    def viewportEvent(self, event):
        logger.info('')
        return True
    """

    def _preferences(self) -> "sanpy.interface.preferences | None":
        """Return the application preferences object when SanPy is running.

        Returns:
            The application preferences, or ``None`` when the current
            ``QApplication`` does not own them.
        """
        app = QtWidgets.QApplication.instance()
        getter = getattr(app, "getConfigDict", None)
        if not callable(getter):
            return None
        return getter()

    def _stored_hidden_columns(self) -> object:
        """Return the hidden-column value stored in preferences.

        Returns:
            The stored value, or ``None`` when preferences have no file-list
            entry. ``None`` selects the default hidden columns.
        """
        preferences = self._preferences()
        if preferences is None:
            return None
        file_list = preferences.configDict.get("fileList")
        if not isinstance(file_list, dict) or "hiddenColumns" not in file_list:
            return None
        return file_list["hiddenColumns"]

    def _write_hidden_columns(self, hidden: list[str]) -> None:
        """Store hidden column keys in memory.

        Args:
            hidden: Optional column keys that should be hidden.
        """
        preferences = self._preferences()
        if preferences is None:
            return
        file_list = preferences.configDict.get("fileList")
        if not isinstance(file_list, dict):
            return
        file_list["hiddenColumns"] = list(hidden)

    def _apply_hidden_columns(self) -> None:
        """Show or hide columns from the saved hidden-column list."""
        model = self.model()
        if model is None or not hasattr(model, "_data"):
            return
        data = model._data
        if isinstance(data, pd.DataFrame) and data.empty:
            return
        columns = [str(column) for column in data.columns]
        hidden = set(hidden_file_column_keys(self._stored_hidden_columns(), columns))
        for index, column_name in enumerate(columns):
            self.setColumnHidden(
                index,
                column_name not in REQUIRED_FILE_COLUMNS and column_name in hidden,
            )

    def _refresh_open_file_tables(self) -> None:
        """Apply the saved hidden columns to every open file table."""
        app = QtWidgets.QApplication.instance()
        views: list[bTableView] = []
        for window in getattr(app, "_windowList", ()):
            file_list = getattr(window, "_fileListWidget", None)
            if file_list is None:
                continue
            view = file_list.getTableView()
            if isinstance(view, bTableView):
                views.append(view)
        if self not in views:
            views.append(self)
        for view in views:
            view._apply_hidden_columns()

    def _set_column_hidden(self, column_key: str, hidden: bool) -> None:
        """Remember one optional column's visibility and refresh open tables.

        Args:
            column_key: File-table column key.
            hidden: Whether the column should be hidden.
        """
        if column_key in REQUIRED_FILE_COLUMNS:
            return
        known = [str(column) for column in sanpy.analysisDir.sanpyColumns.keys()]
        current = hidden_file_column_keys(self._stored_hidden_columns(), known)
        if hidden:
            if column_key not in current:
                current.append(column_key)
        else:
            current = [key for key in current if key != column_key]
        self._write_hidden_columns(current)
        self._refresh_open_file_tables()

    def _add_column_visibility_actions(
        self, menu: QtWidgets.QMenu
    ) -> dict[QtWidgets.QAction, str]:
        """Add checkable actions for the optional file-table columns.

        A checked action means the column is visible. Required columns are
        omitted.

        Args:
            menu: Context menu that receives the Columns submenu.

        Returns:
            Pairs of submenu action and column key, in table order.
        """
        model = self.model()
        if model is None or not hasattr(model, "_data"):
            return {}
        data = model._data
        if isinstance(data, pd.DataFrame) and data.empty:
            return {}
        columns = [str(column) for column in data.columns]
        hidden = set(hidden_file_column_keys(self._stored_hidden_columns(), columns))
        menu.addSeparator()
        column_menu = menu.addMenu("Columns")
        actions: list[tuple[QtWidgets.QAction, str]] = []
        for index, column_name in enumerate(columns):
            if column_name in REQUIRED_FILE_COLUMNS:
                continue
            label = model.headerData(index, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
            action = column_menu.addAction(str(label))
            action.setCheckable(True)
            action.setChecked(column_name not in hidden)
            actions.append((action, column_name))
        return actions

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        """Open the file-table context menu.

        Args:
            event: Right-click event that positions the menu.
        """
        contextMenu = QtWidgets.QMenu(self)

        #
        unloadData = contextMenu.addAction("Unload Data")
        reveal_path = self._recording_path_for_event(event)
        reveal_action = contextMenu.addAction(file_manager_reveal_label())
        reveal_action.setEnabled(reveal_path is not None)

        # contextMenu.addSeparator()
        # removeFromDatabase = contextMenu.addAction("Remove From Database")

        # contextMenu.addSeparator()
        # duplicateRow = contextMenu.addAction("Duplicate Row")
        contextMenu.addSeparator()
        # deleteRow = contextMenu.addAction("Delete Row")
        # contextMenu.addSeparator()
        findNewFiles = contextMenu.addAction("Sync With Folder")
        contextMenu.addSeparator()

        # saveAllAnalysis = contextMenu.addAction("Save All Analysis")
        # contextMenu.addSeparator()

        copyTable = contextMenu.addAction("Copy Table")
        column_actions = self._add_column_visibility_actions(contextMenu)

        # contextMenu.addSeparator()
        # saNodeParams = contextMenu.addAction('SA Node Params')
        # ventricularParams = contextMenu.addAction('Ventricular Params')
        # neuronParams = contextMenu.addAction('Neuron Params')
        # subthresholdParams = contextMenu.addAction('Subthreshold Params')

        #
        action = contextMenu.exec_(self.mapToGlobal(event.pos()))

        if action is None:
            # no user selection
            return

        logger.info(f'  action: "{action.text()}"')

        selectedRow = None
        tmp = self.selectedIndexes()
        if len(tmp) > 0:
            selectedRow = tmp[0].row()  # not in sort order

        if action == unloadData:
            # self.signalUnloadRow.emit(selectedRow) # not in sort order
            self.model().myUnloadRow(selectedRow)
        # elif action == removeFromDatabase:
        #     #self.signalRemoveFromDatabase.emit(selectedRow) # not in sort order
        #     self.model().myRemoveFromDatabase(selectedRow)

        # depreciated, we no longer duplicate rows
        # elif action == duplicateRow:
        #     #self.signalDuplicateRow.emit(selectedRow) # not in sort order
        #     self.model().myDuplicateRow(selectedRow)

        # elif action == deleteRow:
        #     #self.signalDeleteRow.emit(selectedRow)
        #     self.model().myDeleteRow(selectedRow)

        elif action == copyTable:
            # self.signalCopyTable.emit()
            self.model().myCopyTable()
            self.signalUpdateStatus.emit(f'File list copied to clipboard, can be pasted into a spreadsheet')

        elif action == findNewFiles:
            # self.signalFindNewFiles.emit()
            self.model().mySyncDfWithPath()

        elif action == reveal_action:
            if reveal_path is not None:
                self._reveal_recording(reveal_path)

        else:
            for column_action, column_key in column_actions:
                if action == column_action:
                    self._set_column_hidden(column_key, not action.isChecked())
                    return
            logger.warning(f'Action not taken "{action.text()}"')

        # elif action == saveAllAnalysis:
        #     # self.signalSaveFileTable.emit()
        #     self.model().mySave()

        # not sure what this was supposed to do
        # elif action in [saNodeParams, ventricularParams, neuronParams, subthresholdParams]:
        #     #print(action, action.text())
        #     if selectedRow is not None:
        #         self.signalSetDefaultDetection.emit(selectedRow, action.text())

    def _recording_path_for_event(self, event: QtGui.QContextMenuEvent) -> str | None:
        """Return the recording path under a context-menu click.

        Args:
            event: Right-click event received by the table.

        Returns:
            Full recording path, or None when the click is not on an analysis row.
        """
        model = self.model()
        if model is None or not model.isAnalysisDir:
            return None
        viewport_position = self.viewport().mapFromGlobal(event.globalPos())
        index = self.indexAt(viewport_position)
        if not index.isValid():
            return None
        return recording_path_for_visual_row(model._data, index.row())

    def _reveal_recording(self, file_path: str) -> None:
        """Show one recording in the platform file manager.

        Args:
            file_path: Recording path from the clicked file-table row.
        """
        title = file_manager_reveal_label()
        if not os.path.isfile(file_path):
            message = f"File was not found:\n{file_path}"
            logger.warning(message)
            QtWidgets.QMessageBox.warning(self, title, message)
            return
        if not reveal_in_file_manager(file_path):
            message = f"Could not reveal file:\n{file_path}"
            logger.warning(message)
            QtWidgets.QMessageBox.warning(self, title, message)
            return
        logger.info(f'Revealed "{file_path}"')
        self.signalUpdateStatus.emit(f"Revealed {file_path}")

    #
    # frozen
    def _old_updateSectionWidth(self, logicalIndex, oldSize, newSize):
        # if self.logicalIndex == 0:
        if logicalIndex == 0:
            # logger.info(f'XXX {newSize}')
            """
            self.frozenTableView.setColumnWidth(0, newSize)
            """
            self.updateFrozenTableGeometry()

    def _old_updateSectionHeight(self, logicalIndex, oldSize, newSize):
        self.frozenTableView.setRowHeight(logicalIndex, newSize)

    def _old_resizeEvent(self, event):
        super(bTableView, self).resizeEvent(event)
        self.updateFrozenTableGeometry()

    def _old_moveCursor(self, cursorAction, modifiers):
        # logger.info('')
        current = super(bTableView, self).moveCursor(cursorAction, modifiers)
        if (
            cursorAction == self.MoveLeft
            and self.current.column() > 0
            and self.visualRect(current).topLeft().x()
            < self.frozenTableView.columnWidth(0)
        ):
            newValue = (
                self.horizontalScrollBar().value()
                + self.visualRect(current).topLeft().x()
                - self.frozenTableView.columnWidth(0)
            )
            self.horizontalScrollBar().setValue(newValue)
        return current

    def scrollTo(self, index, hint):
        """Not sure what this is for?"""
        # logger.info(f'index:{index} hint:{hint}')
        if index.column() > 0:
            super(bTableView, self).scrollTo(index, hint)

    def _old_updateFrozenTableGeometry(self):
        """ """
        myWidth = 400
        theGeometryRect = self.geometry()
        # theGeometryRect.setWidth(myWidth)
        # self.frozenTableView.setGeometry(theGeometryRect)

        """
        print('=== self.verticalHeader().width():', self.verticalHeader().width())
        print('  self.frameWidth():', self.frameWidth())
        print('  self.viewport().height():', self.viewport().height())
        print('  self.horizontalHeader().height():', self.horizontalHeader().height())
        """

        self.frozenTableView.setGeometry(
            self.verticalHeader().width() - self.frameWidth(),
            self.frameWidth(),
            myWidth,
            self.viewport().height() + self.horizontalHeader().height(),
        )

        return

        """
        #myWidth = self.columnWidth(0) + self.columnWidth(1) + self.columnWidth(2)
        myWidth = 0
        for i in range(self.numFrozenColumns):
            #logger.info(f'{i} {self.frozenTableView.columnWidth(i)}')
            myWidth += self.columnWidth(i)
            print('  col', i, self.columnWidth(i))
        logger.info(f'myWidth:{myWidth}')

        # (x, y, w, h)
        self.frozenTableView.setGeometry(
            self.verticalHeader().width() + self.frameWidth(),
            self.frameWidth(),
            #self.columnWidth(0),
            myWidth,
            self.viewport().height() + self.horizontalHeader().height())
        """

    def slot_detect(self, ba: object) -> None:
        """Refresh the file-table row that owns a detected analysis.

        Args:
            ba: Analysis whose detection results changed.
        """
        model = self.model()
        if model is None or not model.isAnalysisDir:
            return
        for row_label in model._data.index:
            if model._data.loc[row_label, "_ba"] is ba:
                model.refresh_file_key(model._data.get_file_key(row_label))
                return
