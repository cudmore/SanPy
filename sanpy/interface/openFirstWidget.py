"""Launcher window for opening recent or new SanPy recordings."""

import os
from functools import partial
from typing import List

from qtpy import QtCore, QtWidgets, QtGui

import sanpy

# from sanpy.interface.plugins import myStatListWidget

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class openFirstWidget(QtWidgets.QMainWindow):
    """A file/folder loading window.
    
    Open this at app start and close once a file/folder is loaded
    """
    def __init__(
        self,
        sanpyApp: "sanpy.interface.SanPyApp",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Initialize the launcher window.

        Args:
            sanpyApp: Application that owns preferences and analysis windows.
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self._sanpyApp = sanpyApp

        self.recentFileList = self._sanpyApp.getConfigDict().getRecentFiles()
        self.recentFolderList = self._sanpyApp.getConfigDict().getRecentFolder()

        self._appIcon = None
        appIconPath = self._sanpyApp.getAppIconPath()    
        if os.path.isfile(appIconPath):
            # logger.info(f'  app.setWindowIcon with: "{appIconPath}"')
            self._appIconPixmap = QtGui.QPixmap(appIconPath)
            self.setWindowIcon(QtGui.QIcon(appIconPath))
        else:
            logger.warning(f"Did not find appIconPath: {appIconPath}")

        self._buildUI()
        self._buildMenus()

        left = 100
        top = 100
        width = 800
        height = 600
        self.setGeometry(left, top, width, height)

        self.setWindowTitle('SanPy Open Files and Folders')

    def getSanPyApp(self):
        return self._sanpyApp

    def closeEvent(self, event):
        """Hide the launcher while analysis windows remain open."""
        app = self.getSanPyApp()
        if app.hasAnalysisWindows() and not app.quitInProgress:
            self.hide()
            event.ignore()
            return
        event.accept()
    
    def _makeRecentTable(
        self, pathList: List[str], headerStr: str = ""
    ) -> QtWidgets.QTableWidget:
        """Build a table containing recent paths.

        Args:
            pathList: Paths to display.
            headerStr: Optional table header.

        Returns:
            Configured table widget.
        """
        _fontSize = 12
        # recent files
        myTableWidget = QtWidgets.QTableWidget()
        myTableWidget.setToolTip('Double-click to open')
        myTableWidget.setWordWrap(False)
        myTableWidget.setRowCount(0)
        myTableWidget.setColumnCount(1)
        myTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        myTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        myTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        # self.myTableWidget.cellClicked.connect(self._on_recent_file_click)

        # hide the row headers
        myTableWidget.horizontalHeader().hide()

        # Keep long paths readable while fitting more recent items on screen.
        fnt = self.font()
        fnt.setPointSize(_fontSize)
        myTableWidget.setFont(fnt)

        headerLabels = [headerStr]
        myTableWidget.setHorizontalHeaderLabels(headerLabels)

        myTableWidget.horizontalHeader().setFont(fnt)
        myTableWidget.verticalHeader().setFont(fnt)

        header = myTableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        # QHeaderView will automatically resize the section to fill the available space. The size cannot be changed by the user or programmatically.
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

        self._populateRecentTable(myTableWidget, pathList)

        return myTableWidget

    def _populateRecentTable(
        self, table: QtWidgets.QTableWidget, paths: List[str]
    ) -> None:
        """Replace a recent-path table's rows.

        Args:
            table: Table whose rows should be replaced.
            paths: Paths to display.
        """
        table.setRowCount(len(paths))
        for index, path in enumerate(paths):
            table.setItem(index, 0, QtWidgets.QTableWidgetItem(path))
            table.setRowHeight(index, 24)

    def refreshRecent(self) -> None:
        """Reload recent paths and refresh both launcher tables."""
        preferences = self._sanpyApp.getConfigDict()
        self.recentFileList = preferences.getRecentFiles()
        self.recentFolderList = preferences.getRecentFolder()
        self._populateRecentTable(self.recentFileTable, self.recentFileList)
        self._populateRecentTable(self.recentFolderTable, self.recentFolderList)
    
    def _on_recent_file_click(self, rowIdx : int):
        """On double-click, open a file and close self.
        """
        path = self.recentFileList[rowIdx]
        logger.info(f'rowId:{rowIdx} path:{path}')

        if os.path.isfile(path):
            self._sanpyApp.openSanPyWindow(path)
            # self.close()
        else:
            logger.error(f'did not find path: {path}')

    def _on_recent_folder_click(self, rowIdx : int):    
        """On double-click, open a folder and close self.
        """
        path = self.recentFolderList[rowIdx]
        logger.info(f'rowId:{rowIdx} path:{path}')

        if os.path.isdir(path):
            self._sanpyApp.openSanPyWindow(path)
            # self.close()
        else:
            logger.error(f'did not find path: {path}')

    def _on_open_button_click(self, name : str):
        logger.info(name)
        if name == 'Open File...':
            self._sanpyApp.loadFile()
        elif name == 'Open Folder...':
            self._sanpyApp.loadFolder()

    def _buildMenus(self):
    
        mainMenu = self.menuBar()
        _helpAction = self.getSanPyApp()._buildMenus(mainMenu)

        # insert view and plugins menu (deactivated)
        self.viewMenu = QtWidgets.QMenu('&View')
        # self.viewMenu.setDisabled(True)
        noneAction = QtWidgets.QAction('None', self)
        noneAction.setEnabled(False)
        self.viewMenu.addAction(noneAction)
        mainMenu.insertMenu(_helpAction, self.viewMenu)

        self.pluginsMenu = QtWidgets.QMenu('&Plugins')
        self.pluginsMenu.setDisabled(True)
        noneAction = QtWidgets.QAction('None', self)
        self.pluginsMenu.addAction(noneAction)
        mainMenu.insertMenu(_helpAction, self.pluginsMenu)

        # windows menu for app wide open windows
        self.windowsMenu = self._buildWindowMenu()  # open SanPyWindow(s)
        self.windowsMenu.aboutToShow.connect(self._refreshWindowsMenu)
        mainMenu.insertMenu(_helpAction, self.windowsMenu)

    def _buildWindowMenu(self):
        
        windowsMenu = QtWidgets.QMenu('&Windows')
        self.getSanPyApp().getWindowsMenu(windowsMenu)
        windowsMenu.aboutToShow.connect(self._refreshWindowsMenu)
        return windowsMenu

    def _refreshWindowsMenu(self):
    
        self.windowsMenu.clear()

        self.getSanPyApp().getWindowsMenu(self.windowsMenu)

    def _buildUI(self) -> None:
        """Build the launcher controls and recent-path tables."""
        # typical wrapper for PyQt, we can't use setLayout(), we need to use setCentralWidget()
        _mainWidget = QtWidgets.QWidget()
        _mainVLayout = QtWidgets.QVBoxLayout()
        _mainWidget.setLayout(_mainVLayout)
        self.setCentralWidget(_mainWidget)

        # for open and open folder buttons
        hBoxLayout = QtWidgets.QHBoxLayout()
        hBoxLayout.setAlignment(QtCore.Qt.AlignLeft)
        _mainVLayout.addLayout(hBoxLayout)

        # aLabel = QtWidgets.QLabel()
        # aLabel.setPixmap(self._appIconPixmap)
        # hBoxLayout.addWidget(aLabel,
        #                      alignment=QtCore.Qt.AlignLeft)

        aLabel = QtWidgets.QLabel('SanPy')
        hBoxLayout.addWidget(aLabel,
                             alignment=QtCore.Qt.AlignLeft)

        name = 'Open File...'
        aButton = QtWidgets.QPushButton(name)
        aButton.setFixedSize(QtCore.QSize(200, 30))
        aButton.setToolTip('Open a file.')
        aButton.clicked.connect(partial(self._on_open_button_click, name))
        hBoxLayout.addWidget(aButton, alignment=QtCore.Qt.AlignLeft)

        name = 'Open Folder...'
        aButton = QtWidgets.QPushButton(name)
        aButton.setFixedSize(QtCore.QSize(200, 30))
        aButton.setToolTip('Open a folder.')
        aButton.clicked.connect(partial(self._on_open_button_click, name))
        hBoxLayout.addWidget(aButton, alignment=QtCore.Qt.AlignLeft)

        # recent files and tables
        recent_vBoxLayout = QtWidgets.QVBoxLayout()

        aLabel = QtWidgets.QLabel('Recent Files')
        recent_vBoxLayout.addWidget(aLabel)

        # headerStr='Recent Files (double-click to open)'
        headerStr = ''
        self.recentFileTable = self._makeRecentTable(
            self.recentFileList, headerStr=headerStr
        )
        self.recentFileTable.cellDoubleClicked.connect(self._on_recent_file_click)
        recent_vBoxLayout.addWidget(self.recentFileTable)

        aLabel = QtWidgets.QLabel('Recent Folders')
        recent_vBoxLayout.addWidget(aLabel)

        # headerStr='Recent Files (double-click to open)'
        headerStr = ''
        self.recentFolderTable = self._makeRecentTable(
            self.recentFolderList, headerStr=headerStr
        )
        self.recentFolderTable.cellDoubleClicked.connect(
            self._on_recent_folder_click
        )
        recent_vBoxLayout.addWidget(self.recentFolderTable)

        _mainVLayout.addLayout(recent_vBoxLayout)

def test():
    import sys
    from sanpy.interface import SanPyApp

    app = SanPyApp([])
    
    of = openFirstWidget(app)
    of.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    test()
