# Author: Robert H Cudmore
# Date: 20190719

#from curses.panel import bottom_panel
import os, sys

# import traceback # to print call stack
from functools import partial
from collections import OrderedDict
import platform
import pathlib
from datetime import datetime

from typing import Union, Dict, List, Tuple

import pandas as pd

import pyqtgraph as pg

# v1
# import qdarkstyle  # the one we originally used

# v2
import qdarktheme

# Enable HiDPI.
qdarktheme.enable_hi_dpi()

import webbrowser  # to open online help

from qtpy import QtCore, QtWidgets, QtGui

import sanpy._util
import sanpy.interface
import sanpy.interface.preferences

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)
# This causes mkdocs to infinite recurse when running locally as 'mkdocs serve'
# logger.info('SanPy app.py is starting up')

# turn off qdarkstyle logging
import logging

# logging.getLogger('qdarkstyle').setLevel(logging.WARNING)

# turn off numexpr 'INFO' logging
logging.getLogger("numexpr").setLevel(logging.WARNING)

# basedir = os.path.dirname(__file__)
# print('sanpy_app basedir:', basedir)


class SanPyWindow(QtWidgets.QMainWindow):
    # TODO: define parameter block for all signals.

    signalSetXAxis = QtCore.Signal(object)
    """Emit set axis."""

    signalSwitchFile = QtCore.Signal(object, object)
    """Emit on switch file."""

    signalSelectSweep = QtCore.Signal(object, object)  # (ba, sweepNumber)
    """Emit set sweep."""

    signalUpdateAnalysis = QtCore.Signal(object)
    """Emit on detect."""

    signalSelectSpike = QtCore.Signal(object)
    """Emit spike selection."""

    signalSelectSpikeList = QtCore.Signal(object)
    """Emit spike list selection."""

    def __init__(self, path=None, parent=None):
        """
        Parameters
        ----------
        path : str
            Full path to folder with raw files (abf,csv,tif).
        """

        super().__init__(parent)

        logger.info(f"Constructing SanPyWindow")
        date_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f'{date_time_str}')

        _version = self._getVersionInfo()
        for k,v in _version.items():
            logger.info(f'{k}: {v}')

        self.setAcceptDrops(True)

        # TODO: if first time run (no <user>/Documents/SanPy) then warn user to quit and restart

        # create directories in <user>/Documents and add to python path
        firstTimeRunning = sanpy._util.addUserPath()
        if firstTimeRunning:
            logger.info("  We created <user>/Documents/Sanpy and need to restart")

        self._fileLoaderDict = sanpy.fileloaders.getFileLoaders(verbose=True)
        
        self._detectionClass : sanpy.bDetection = sanpy.bDetection()

        # create an empty model for file list
        dfEmpty = pd.DataFrame(columns=sanpy.analysisDir.sanpyColumns.keys())
        self.myModel = sanpy.interface.bFileTable.pandasModel(dfEmpty)

        self.fileFromDatabase = True  # if False then from folder

        self.startSec = None
        self.stopSec = None

        # TODO: put font size in options file
        # removed mar 26 2023
        """
        myFontSize = 10
        myFont = self.font();
        myFont.setPointSize(myFontSize)
        self.setFont(myFont)
        """

        if path is not None and os.path.isdir(path):
            windowTitle = f"SanPy {path}"
        else:
            windowTitle = "SanPy"
        self.setWindowTitle(windowTitle)

        self._rowHeight = 11

        # path to loaded folder (using bAnalysisDir)
        self.configDict : sanpy.interface.preferences = sanpy.interface.preferences(self)
        self.myAnalysisDir = None
        lastPath = self.configDict.getMostRecentFolder()
        logger.info(f'  preferences lastPath is "{lastPath}"')
        if path is not None:
            self.path = path
        elif lastPath is not None and os.path.isdir(lastPath):
            self.path = lastPath
        else:
            self.path = None

        # TODO: refactor dark to light theme
        self.useDarkStyle = self.configDict["useDarkStyle"]
        # self.useDarkStyle = True
        self.toggleStyleSheet(self.useDarkStyle, buildingInterface=True)

        #
        # set window geometry
        self.setMinimumSize(640, 480)
        self.left = self.configDict["windowGeometry"]["x"]
        self.top = self.configDict["windowGeometry"]["y"]
        self.width = self.configDict["windowGeometry"]["width"]
        self.height = self.configDict["windowGeometry"]["height"]
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.myPlugins = sanpy.interface.bPlugins(sanpyApp=self)

        # order matter, _buildMenus uses objects created in _buildUI
        self._buildUI()
        self._buildMenus()

        # 20210803, loadFolder was above? Still works down here
        # needed to update detection widget after buildUI()
        if self.path is not None and len(self.path) > 0:
            self.slot_loadFolder(self.path)

        # self.raise_()  # bring to front, raise is a python keyword
        # self.activateWindow()  # bring to front

        self.slot_updateStatus("Ready")
        logger.info("SanPy started")

    def getDetectionClass(self) -> sanpy.bDetection:
        return self._detectionClass

    def getFileLoaderDict(self):
        return self._fileLoaderDict

    def dragEnterEvent(self, event):
        logger.info("")
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        logger.info("")
        folders = [u.toLocalFile() for u in event.mimeData().urls()]
        if len(folders) > 1:
            return
        oneFolder = folders[0]
        if os.path.isdir(oneFolder):
            self.slot_loadFolder(path=oneFolder)

    def _promptIfDirty(self) -> bool:
        """Prompt user if there is unsaved analysis.

        If this return False, do not proceed with caller action.
        e.g. on 'load folder'

        If this returns True then proceed with caller action
        """
        acceptAndContinue = True
        if self.myAnalysisDir is not None:
            tableIsDirty = self.myAnalysisDir.isDirty
            analysisIsDirty = self.myAnalysisDir.hasDirty()
            if tableIsDirty or analysisIsDirty:
                userResp = sanpy.interface.bDialog.yesNoCancelDialog(
                    "There is analysis that is not saved.\nDo you want to save?"
                )
                if userResp == QtWidgets.QMessageBox.Yes:
                    self.saveFilesTable()
                    acceptAndContinue = True
                elif userResp == QtWidgets.QMessageBox.No:
                    acceptAndContinue = True
                else:  # userResp == QtWidgets.QMessageBox.Cancel:
                    acceptAndContinue = False
        return acceptAndContinue

    def closeEvent(self, event):
        """Called when user closes main window or selects quit.

        Parameters
        ----------
        event : PyQt5.QtGui.QCloseEvent
        """

        logger.info(event)

        # check if our table view has been edited by user and warn
        doQuit = True
        alreadyAsked = False
        # self.myAnalysisDir is only defined after we load a folder
        if self.myAnalysisDir is not None:
            tableIsDirty = self.myAnalysisDir.isDirty
            analysisIsDirty = self.myAnalysisDir.hasDirty()
            if tableIsDirty or analysisIsDirty:
                alreadyAsked = True
                userResp = sanpy.interface.bDialog.yesNoCancelDialog(
                    "There is analysis that is not saved.\nDo you want to save?"
                )
                if userResp == QtWidgets.QMessageBox.Yes:
                    self.saveFilesTable()
                    event.accept()
                elif userResp == QtWidgets.QMessageBox.No:
                    event.accept()
                else:
                    event.ignore()
                    doQuit = False
        if doQuit:
            if not alreadyAsked:
                userResp = sanpy.interface.bDialog.okCancelDialog(
                    "Are you sure you want to quit SanPy?", informativeText=None
                )
                if userResp == QtWidgets.QMessageBox.Cancel:
                    event.ignore()
                    doQuit = False

            if doQuit:
                logger.info("SanPy is quiting")
                QtCore.QCoreApplication.quit()

    def getOptions(self):
        return self.configDict

    def getWindowGeometry(self):
        """Get the current window position."""
        myRect = self.geometry()
        left = myRect.left()
        top = myRect.top()
        width = myRect.width()
        height = myRect.height()
        return left, top, width, height

    def toggleStyleSheet(self, doDark=None, buildingInterface=False):
        logger.info("")
        if doDark is None:
            doDark = not self.useDarkStyle
        self.useDarkStyle = doDark
        if doDark:
            # v1
            # self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
            # v2
            qdarktheme.setup_theme("dark")

            pg.setConfigOption("background", "k")
            pg.setConfigOption("foreground", "w")
        else:
            # v1
            # self.setStyleSheet('')
            # v2
            qdarktheme.setup_theme("light")

            pg.setConfigOption("background", "w")
            pg.setConfigOption("foreground", "k")

        self.configDict["useDarkStyle"] = self.useDarkStyle

        if not buildingInterface:
            # self.myScatterPlotWidget.defaultPlotLayout()
            # self.myScatterPlotWidget.buildUI(doRebuild=True)
            self.myDetectionWidget.mySetTheme()

        if buildingInterface:
            pass
        else:
            pass
            # msg = QtWidgets.QMessageBox()
            # msg.setIcon(QtWidgets.QMessageBox.Warning)
            # msg.setText("Theme Changed")
            # msg.setInformativeText('Please restart SanPy for changes to take effect.')
            # msg.setWindowTitle("Theme Changed")
            # retval = msg.exec_()

            # self.configDict.save()

    def slot_folderDepth(self, folderDepth : int):
        self.configDict['fileList']['Folder Depth'] = folderDepth
        
    def slot_loadFolder(self, path="", folderDepth=None):
        """Load a folder of raw data files.

        Parameters
        ----------
        path : str
        folderDepth : int or None
        """

        if folderDepth is None:
            # get the depth from file list widget
            folderDepth = self._fileListWidget.getDepth()

        logger.info(f"Loading depth:{folderDepth} path: {path}")

        # if folder is already loaded, ask to save
        acceptAndContinue = self._promptIfDirty()
        if not acceptAndContinue:
            return

        # ask user for folder
        if path is None or isinstance(path, bool) or len(path) == 0:
            path = str(
                QtWidgets.QFileDialog.getExistingDirectory(
                    self, "Select Directory With Recordings"
                )
            )
            if len(path) == 0:
                return
        elif os.path.isdir(path):
            pass
        else:
            logger.warning(f'    Did not load path "{path}"')
            return

        self.path = path  # path to loaded bAnalysisDir folder

        # logger.info(f'Loading path: {path}')

        # will create/load hd5 file for folder
        self.myAnalysisDir = sanpy.analysisDir(
            path, folderDepth=folderDepth, myApp=self
        )

        # set myAnalysisDir to file list model
        self.myModel = sanpy.interface.bFileTable.pandasModel(self.myAnalysisDir)
        # self.myModel.signalMyDataChanged.connect(self.slot_dataChanged)
        # self.myModel.signalMyDataChanged.connect(self.myDetectionWidget.slot_dataChanged)

        # try:
        if 1:
            self._fileListWidget.mySetModel(self.myModel)
            self.myModel.signalMyDataChanged.connect(
                self.myDetectionWidget.slot_dataChanged
            )
        """
        except (AttributeError) as e:
            # needed when we call loadFolder from __init__
            # logger.warning('OK: no tableView during load folder')
            pass
        """

        # set window title
        if self.path is not None and os.path.isdir(self.path):
            windowTitle = f"SanPy: {self.path}"
        else:
            windowTitle = "SanPy"
        self.setWindowTitle(windowTitle)

        # add to preferences recent folders
        self.configDict.addFolder(path)

        # save preferences
        # self.configDict.save()

    '''
    def slot_dataChanged(self, columnName, value, rowDict):
        """User has edited main file table.
        Update detection widget for columns (Start(s), Stop(s), dvdtThreshold, mvThreshold)
        """
        logger.info(f'{columnName} {value}')
        print('  ', rowDict)
    '''

    def selectSpike(self, spikeNumber, doZoom=False):
        eDict = {
            "spikeNumber": spikeNumber,
            "doZoom": doZoom,
            "ba": self.get_bAnalysis(),
        }
        self.signalSelectSpike.emit(eDict)

    def selectSpikeList(self, spikeList: List[int], doZoom: bool = False):
        eDict = {
            "spikeList": spikeList,
            "doZoom": doZoom,
            "ba": self.get_bAnalysis(),
        }
        logger.info(f'-->> emit signalSelectSpikeList {eDict}')
        self.signalSelectSpikeList.emit(eDict)

    def mySignal(self, this, data=None):
        """Receive signals from children widgets.

        Parameters
        ----------
        this : str
            The signal name
        data : type depends on signal (this)
            For example, signal 'set x axis' uses data=[min,max]
        """
        # print('=== sanpy_app.mySignal() "' + this +'"')

        if this == "select spike":
            logger.warning('\n\nTODO: GET RID OF "select spike"\n\n')
            spikeNumber = data["spikeNumber"]
            doZoom = data["isShift"]
            self.selectSpike(spikeNumber, doZoom=doZoom)
            # self.signalSelectSpike.emit(data)

        elif this == "set x axis":
            logger.info(f'"set x axis" {data}')

            self.startSec = data[0]
            self.stopSec = data[1]
            # old
            # self.myScatterPlotWidget.selectXRange(data[0], data[1])
            # new
            logger.info(f'"-->> emit signalSetXAxis set full x axis" {data[0]} {data[1]}')
            self.signalSetXAxis.emit([data[0], data[1]])  # emits to scatter plot ONLY

        elif this == "set full x axis":
            self.startSec = 0
            if self.get_bAnalysis() is not None:
                self.stopSec = self.get_bAnalysis().fileLoader.recordingDur
            else:
                self.stopSec = None
            logger.info(f'"-->> emit signalSetXAxis set full x axis" {self.startSec} {self.stopSec}')
            self.signalSetXAxis.emit(
                [self.startSec, self.stopSec]
            )  # emits to scatter plot ONLY

        elif this == "cancel all selections":
            self.selectSpike(None)
            self.selectSpikeList([])

        else:
            logger.warning(f'Did not understand this: "{this}"')

    def old_keyPressEvent(self, event):
        """Respond to key press

        TODO: does not seem to work?
        """
        key = event.key()
        text = event.text()
        logger.info(f"text:{text} key:{key} event:{event}")

        # handled in bDetectionWidget
        # set full axis
        # if key in [70, 82]: # 'r' or 'f'
        # if key in [QtCore.Qt.Key.Key_R, QtCore.Qt.Key.Key_F]:
        #     self.myDetectionWidget.setAxisFull()

        """
        if key in [QtCore.Qt.Key.Key_P]: # 'r' or 'f'
            self.myDetectionWidget.myPrint()
        """

        # handled in bDetectionWidget
        # cancel all selections
        # if key == QtCore.Qt.Key.Key_Escape:
        #     self.mySignal('cancel all selections')

        # handled in bDetectionWidget
        # hide detection widget
        # if text == 'h':
        #     if self.myDetectionWidget.detectToolbarWidget.isVisible():
        #         self.myDetectionWidget.detectToolbarWidget.hide()
        #     else:
        #         self.myDetectionWidget.detectToolbarWidget.show()

        # user can copy this to the clipboard
        # print file list model
        # this is df updated as user updates table
        # if text == 'p':
        #     print(self.myModel)
        #     print(self.myModel._data)

        #
        event.accept()

    def get_bAnalysis(self):
        return self.myDetectionWidget.ba

    def getSelectedFileDict(self):
        """
        Used by detection widget to get info in selected file.

        todo: remove, pass this dict in signal emit from file table
        """

        fileDict = self._fileListWidget.getTableView().getSelectedRowDict()
        return fileDict

        # was this
        """
        selectedRows = self._fileListWidget.selectionModel().selectedRows()
        if len(selectedRows) == 0:
            return None
        else:
            selectedItem = selectedRows[0]
            selectedRow = selectedItem.row()

        rowDict = self.myModel.myGetRowDict(selectedRow)
        return rowDict
        """

    def slot_fileTableClicked(self, row, rowDict, selectingAgain):
        """Respond to selections in file table."""

        """
        row (int):
        rowDict (dict):
        selectingAgain (bool): True if row was already selected
        """

        if selectingAgain:
            self.slot_updateStatus(f'Refreshing file "{rowDict["File"]}"')
        else:
            self.slot_updateStatus(f'Loading file "{rowDict["File"]}" ... please wait')

        # TODO: try and remove this
        self.startSec = rowDict["Start(s)"]
        self.stopSec = rowDict["Stop(s)"]

        # This will load if necc, otherwise just fetch a pointer
        if self.myAnalysisDir is not None:
            ba = self.myAnalysisDir.getAnalysis(row)  # if None then problem loading

            if ba is not None:
                self.signalSwitchFile.emit(ba, rowDict)
                if selectingAgain:
                    pass
                else:
                    fileNote = ba.metaData.getMetaData('Note')
                    if fileNote:
                        fileNote = 'Note:' + fileNote
                    else:
                        fileNote = ''
                    self.slot_updateStatus(
                        f'Loaded file {ba.fileLoader.filename} {fileNote}'
                    )  # this will load ba if necc

    def _buildMenus(self):
        mainMenu = self.menuBar()

        #self.aboutAction = QtWidgets.QAction("&About", self)

        # load
        loadFolderAction = QtWidgets.QAction("Load Folder ...", self)
        loadFolderAction.setShortcut("Ctrl+O")
        loadFolderAction.triggered.connect(self.slot_loadFolder)

        # open recent (submenu)
        self.openRecentMenu = QtWidgets.QMenu("Load Recent ...")
        self.openRecentMenu.aboutToShow.connect(self._refreshOpenRecent)

        saveDatabaseAction = QtWidgets.QAction("Save Folder Analysis", self)
        saveDatabaseAction.setShortcut("Ctrl+S")
        saveDatabaseAction.triggered.connect(self.saveFilesTable)

        # buildDatabaseAction = QtWidgets.QAction('Build Big Database ...', self)
        # buildDatabaseAction.triggered.connect(self.buildDatabase)

        savePreferencesAction = QtWidgets.QAction("Save Preferences", self)
        savePreferencesAction.triggered.connect(self.configDict.save)

        # showLogAction = QtWidgets.QAction("Show Log", self)
        # showLogAction.triggered.connect(self.openLog)

        fileMenu = mainMenu.addMenu("&File")

        fileMenu.addAction(loadFolderAction)
        fileMenu.addMenu(self.openRecentMenu)

        fileMenu.addSeparator()
        fileMenu.addAction(saveDatabaseAction)

        fileMenu.addSeparator()
        # fileMenu.addAction(buildDatabaseAction)
        # fileMenu.addSeparator()
        fileMenu.addAction(savePreferencesAction)

        # fileMenu.addSeparator()
        # fileMenu.addAction(showLogAction)

        # view menu to toggle widgets on/off
        self.viewMenu = mainMenu.addMenu("&View")
        self.viewMenu.aboutToShow.connect(self._refreshViewMenu)
        self._refreshViewMenu()
        # self._populateViewMenu()

        self.windowsMenu = mainMenu.addMenu('&Window')
        self.windowsMenu.aboutToShow.connect(self._refreshWindowsMenu)
        self._refreshWindowsMenu()

        #
        # plugins menu
        pluginsMenu = mainMenu.addMenu("&Plugins")
        # list of plugin names
        # pluginList = self.myPlugins.pluginList()
        # each key is the name of theplugin
        pluginDict = self.myPlugins.pluginDict
        # print('pluginDict:', pluginDict)
        _foundUserPlugin = False
        for __humanName, v in pluginDict.items():
            if not v["showInMenu"]:
                continue

            # logger.info(f'adding plugin: {plugin}')

            sanpyPluginAction = QtWidgets.QAction(__humanName, self)

            # TODO: Add spacer between system and user plugins
            # fileMenu.addSeparator()

            """
            type = self.myPlugins.getType(plugin)
            if type == 'system':
                print(plugin, 'system -->> bold')
                f = sanpyPluginAction.font()
                f.setBold(True);
                f.setItalic(True);
                sanpyPluginAction.setFont(f);
            """

            # print(v['type'])
            if v["type"] == "user":
                if not _foundUserPlugin:
                    pluginsMenu.addSeparator()
                    _foundUserPlugin = True
                _font = sanpyPluginAction.font()
                # _font.setBold(True)
                _font.setItalic(True)
                sanpyPluginAction.setFont(_font)

            sanpyPluginAction.triggered.connect(
                lambda checked, pluginName=__humanName: self.sanpyPlugin_action(
                    pluginName
                )
            )
            pluginsMenu.addAction(sanpyPluginAction)

        """
        pluginDir = os.path.join(self._getBundledDir(), 'plugins', '*.txt')
        pluginList = glob.glob(pluginDir)
        logger.info(f'pluginList: {pluginList}')
        pluginsMenu = mainMenu.addMenu('&Plugins')
        oneAction = 'plotRecording'
        sanpyPluginAction = QtWidgets.QAction(oneAction, self)
        #sanpyPluginAction.triggered.connect(self.sanpyPlugin_action)
        sanpyPluginAction.triggered.connect(lambda checked, oneAction=oneAction: self.sanpyPlugin_action(oneAction))
        pluginsMenu.addAction(sanpyPluginAction)
        """

        #
        # a dynamic menu to show open plugins
        # self.windowsMenu = mainMenu.addMenu('&Windows')
        # self.windowsMenu.aboutToShow.connect(self._populateOpenPlugins)

        """
        # windows menu to toggle scatter plot widget
        windowsMenu = mainMenu.addMenu('&Windows')
        mainWindowAction = QtWidgets.QAction('Main', self)
        #
        openScatterAction = QtWidgets.QAction('Scatter Plot', self)
        openScatterAction.triggered.connect(self.openScatterWindow)
        #mainWindowAction.triggered.connect(self.toggleStyleSheet)
        mainWindowAction.setCheckable(True)
        mainWindowAction.setChecked(True)
        windowsMenu.addAction(mainWindowAction)
        windowsMenu.addAction(openScatterAction)
        """

        # help menu
        helpMenu = mainMenu.addMenu("&Help")

        name = "SanPy Help (Opens In Browser)"
        action = QtWidgets.QAction(name, self)
        action.triggered.connect(partial(self._onHelpMenuAction, name))
        helpMenu.addAction(action)

        # this actually does not show up in the help menu!
        # PyQt reroutes it to the main python/SanPy menu
        name = "About SanPy"
        action = QtWidgets.QAction(name, self)
        action.triggered.connect(self._onAboutMenuAction)
        helpMenu.addAction(action)

        # like the help menu, this gets rerouted to the main python/sanp menu
        name = "Preferences ..."
        action = QtWidgets.QAction(name, self)
        action.triggered.connect(self._onPreferencesMenuAction)
        helpMenu.addAction(action)

    def _onHelpMenuAction(self, name: str):
        if name == "SanPy Help (Opens In Browser)":
            url = "https://cudmore.github.io/SanPy/desktop-application"
            webbrowser.open(url, new=2)

    def _onPreferencesMenuAction(self):
        logger.info('')

    def _onAboutMenuAction(self):
        """Show a dialog with help.
        """
        print(self._getVersionInfo())

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle('About SanPy')

        vLayout = QtWidgets.QVBoxLayout()

        _versionInfo = self._getVersionInfo()
        for k,v in _versionInfo.items():
            aText = k + ' ' + str(v)
            aLabel = QtWidgets.QLabel(aText)

            if 'https' in v:
                aLabel.setText(f'{k} <a href="{v}">{v}</a>')
                aLabel.setTextFormat(QtCore.Qt.RichText)
                aLabel.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
                aLabel.setOpenExternalLinks(True)

            if k == 'email':
                # <a href = "mailto: abc@example.com">Send Email</a>
                aLabel.setText(f'{k} <a href="mailto:{v}">{v}</a>')
                aLabel.setTextFormat(QtCore.Qt.RichText)
                aLabel.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
                aLabel.setOpenExternalLinks(True)
            
            vLayout.addWidget(aLabel)

        dlg.setLayout(vLayout)

        dlg.exec()
  
    def _getVersionInfo(self) -> dict:
        retDict = {}

        #import platform
        _platform = platform.machine()
        # arm64
        # x86_64

        # from sanpy.version import __version__

        # retDict['SanPy version'] = __version__
        retDict['SanPy version'] = sanpy.__version__
        retDict['Python version'] = platform.python_version()
        retDict['Python platform'] = _platform  # platform.platform()
        retDict['PyQt version'] = QtCore.__version__  # when using import qtpy
        # retDict['Bundle folder'] = sanpy._util.getBundledDir()
        # retDict['Log file'] = sanpy.sanpyLogger.getLoggerFile()
        retDict['GitHub'] = 'https://github.com/cudmore/sanpy'
        retDict['Documentation'] = 'https://cudmore.github.io/SanPy/'
        retDict['email'] = 'rhcudmore@ucdavis.edu'

        return retDict
    
    def _refreshOpenRecent(self):
        """Dynamically generate the open recent file menu."""
        self.openRecentMenu.clear()
        for recentFolder in self.configDict.getRecentFolder():
            loadFolderAction = QtWidgets.QAction(recentFolder, self)
            # loadFolderAction.setShortcut('Ctrl+O')
            loadFolderAction.triggered.connect(
                partial(self.slot_loadFolder, recentFolder)
            )

            self.openRecentMenu.addAction(loadFolderAction)

    def _refreshWindowsMenu(self):
        self.windowsMenu.clear()

        name = "SanPy Window"
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(self.isActiveWindow())
        action.triggered.connect(partial(self._windowsMenuAction, self, name))
        self.windowsMenu.addAction(action)

        for _widget in QtWidgets.QApplication.topLevelWidgets():
            if 'sanpy.interface.plugins' in str(type(_widget)):
                myHumanName = _widget.myHumanName
                print(f'{myHumanName} {_widget}')
                action = QtWidgets.QAction(myHumanName, self, checkable=True)
                action.setChecked(_widget.isActiveWindow())
                action.triggered.connect(partial(self._windowsMenuAction, _widget, myHumanName))
                self.windowsMenu.addAction(action)

    def _refreshViewMenu(self):
        """Dynamically create the main 'View' menu each time it is selected."""

        self.viewMenu.clear()

        self.viewMenu.addSeparator()

        key1 = "filePanels"
        name = "File Panel"
        checkedMainPanel = self.configDict[key1]["File Panel"]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checkedMainPanel)
        action.setShortcut(QtGui.QKeySequence("F"))
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        self.viewMenu.addAction(action)

        self.viewMenu.addSeparator()

        key1 = "detectionPanels"

        name = "Detection Panel"
        checkedMainPanel = self.configDict[key1]["Detection Panel"]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checkedMainPanel)
        action.setShortcut(QtGui.QKeySequence("D"))
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        self.viewMenu.addAction(action)

        self.viewMenu.addSeparator()

        name = "Detection"
        checked = self.configDict["detectionPanels"][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        action.setEnabled(checkedMainPanel)
        self.viewMenu.addAction(action)

        name = "Display"
        checked = self.configDict["detectionPanels"][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        action.setEnabled(checkedMainPanel)
        self.viewMenu.addAction(action)

        # mar 11
        name = "Set Spikes"
        checked = self.configDict["detectionPanels"][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        action.setEnabled(checkedMainPanel)
        self.viewMenu.addAction(action)

        name = "Set Meta Data"
        checked = self.configDict["detectionPanels"][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        action.setEnabled(checkedMainPanel)
        self.viewMenu.addAction(action)

        name = "Plot Options"
        checked = self.configDict["detectionPanels"][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        action.setEnabled(checkedMainPanel)
        self.viewMenu.addAction(action)

        self.viewMenu.addSeparator()

        # traces (globalvm, dvdt, dac)
        key1 = "rawDataPanels"

        name = "Full Recording"
        checked = self.configDict[key1][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        self.viewMenu.addAction(action)

        name = "Derivative"
        checked = self.configDict[key1][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        self.viewMenu.addAction(action)

        name = "DAC"
        checked = self.configDict[key1][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        self.viewMenu.addAction(action)

        self.viewMenu.addSeparator()

        # show/hide plugin 1/2 dock widgets
        key1 = "pluginDocks"
        name = "Plugins 1"
        # checkedMainPanel = self.configDict[key1]['File Panel']
        _isVisible = self.pluginDock1.isVisible()  # assuming we _buildUI
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(_isVisible)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        self.viewMenu.addAction(action)

        """
        key1 = 'pluginDocks'
        name = 'Plugins 2'
        _isVisible = self.pluginDock2.isVisible()  # assuming we _buildUI
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(_isVisible)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        self.viewMenu.addAction(action)
        """

        self.viewMenu.addSeparator()

        # TODO: refactor switching themes
        name = "Dark Theme"
        checked = self.useDarkStyle
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        # action.setEnabled(False)
        action.triggered.connect(partial(self._viewMenuAction, "Dark Theme", name))
        self.viewMenu.addAction(action)

    def _windowsMenuAction(self, widget, name, isChecked):
        """
        Parameters
        ----------
        widget : QtWidgets.QWidget
            Either self or an open plugin widget
        name : str
            Name of the window
        """
        
        # don't toggle visibility
        # widget.setVisible(not widget.isVisible())

        QtWidgets.QApplication.setActiveWindow(widget)
        widget.activateWindow()
        widget.raise_()

    def _viewMenuAction(self, key1, name, isChecked):
        """Respond to user selection in view menu."""
        logger.info(f"{key1}, {name}, {isChecked}")

        try:
            self.configDict[key1][name] = isChecked
        except KeyError as e:
            pass

        if key1 == "filePanels":
            self.toggleInterface(name, isChecked)

        elif key1 == "pluginDocks":
            self.toggleInterface(name, isChecked)

        elif key1 == "rawDataPanels":
            # self.toggleInterface(name, isChecked)
            self.myDetectionWidget.toggleInterface(name, isChecked)

        elif key1 == "detectionPanels":
            self.myDetectionWidget.toggleInterface(name, isChecked)

        elif key1 == "Dark Theme":
            # doDark = not self.useDarkStyle
            # self.toggleStyleSheet(doDark=doDark)
            self.toggleStyleSheet()
        else:
            logger.warning(f'  no action for key1: "{key1}"')

    def toggleInterface(self, name, on):
        """Toggle named interface widgets show and hide.

        Parameters
        ----------
        name : str
            Name of the widget
        on : bool
            If True then show, otherwise hide.
        """
        if name == "File Panel":
            self._fileListWidget.setVisible(on)
            # if on:
            #     self.fileDock.show()
            # else:
            #     self.fileDock.hide()
        elif name == "Plugins 1":
            if on:
                self.pluginDock1.show()
            else:
                self.pluginDock1.hide()
        elif name == "Plugins 2":
            if on:
                self.pluginDock2.show()
            else:
                self.pluginDock2.hide()

    def old_populateOpenPlugins(self):
        """Depreciated. Was to be a dynamic menu to show open plugins."""
        self.windowsMenu.clear()
        actions = []
        for plugin in self.myPlugins._openSet:
            name = plugin.myHumanName
            windowTitle = plugin.windowTitle
            action = QtWidgets.QAction(windowTitle, self)
            action.triggered.connect(
                partial(self.old_showOpenPlugin, name, plugin, windowTitle)
            )
            actions.append(action)
        self.windowsMenu.addActions(actions)

    def old_showOpenPlugin(self, name, plugin, windowTitle, selected):
        logger.info(name)
        logger.info(plugin)
        logger.info(windowTitle)
        logger.info(selected)
        plugin.bringToFront()

    def _buildUI(self):
        """ "
        File List : sanpy.interface.fileListWidget
        Detection Widget: sanpy.interface.bDetectionWidget
        """
        # self.toggleStyleSheet(buildingInterface=True)

        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)

        # typical wrapper for PyQt, we can't use setLayout(), we need to use setCentralWidget()
        _mainWidget = QtWidgets.QWidget()
        _mainVLayout = QtWidgets.QVBoxLayout()
        _mainWidget.setLayout(_mainVLayout)
        self.setCentralWidget(_mainWidget)

        #
        # list of files (in a dock)
        folderDepth = self.configDict["fileList"]["Folder Depth"]
        self._fileListWidget = sanpy.interface.fileListWidget(self.myModel, folderDepth=folderDepth)
        self._fileListWidget._tableView.signalUpdateStatus.connect(self.slot_updateStatus)  # 
        self._fileListWidget.signalLoadFolder.connect(self.slot_loadFolder)
        self._fileListWidget.signalSetFolderDepth.connect(self.slot_folderDepth)
        self._fileListWidget.getTableView().signalSelectRow.connect(
            self.slot_fileTableClicked
        )
        # self._fileListWidget.getTableView().signalSetDefaultDetection.connect(self.slot_setDetectionParams)

        # update dvdtThreshold, mvThreshold Start(s), Stop(s)
        self.signalUpdateAnalysis.connect(
            self._fileListWidget.getTableView().slot_detect
        )
        # self.myDetectionWidget.signalDetect.connect(self._fileListWidget.slot_detect)

        # file list as a widget
        #_mainVLayout.addWidget(self._fileListWidget)

        # file list as a dock
        self.fileDock = QtWidgets.QDockWidget('Files',self)
        self.fileDock.setWidget(self._fileListWidget)
        self.fileDock.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures | \
                                  QtWidgets.QDockWidget.DockWidgetVerticalTitleBar)
        self.fileDock.setFloating(False)
        self.fileDock.setTitleBarWidget(QtWidgets.QWidget())
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.fileDock)

        #
        # Detection widget
        baNone = None
        self.myDetectionWidget = sanpy.interface.bDetectionWidget(
            ba=baNone, mainWindow=self
        )

        # show/hide
        on = self.configDict["detectionPanels"]["Detection Panel"]
        self.myDetectionWidget.toggleInterface("Detection Panel", on)

        # (1) detection widget in main v layout
        _mainVLayout.addWidget(self.myDetectionWidget)

        # myDetectionWidget listens to self
        self.signalSwitchFile.connect(self.myDetectionWidget.slot_switchFile)
        self.signalSelectSpike.connect(self.myDetectionWidget.slot_selectSpike)
        self.signalSelectSpikeList.connect(self.myDetectionWidget.slot_selectSpikeList)
        self.signalUpdateAnalysis.connect(self.myDetectionWidget.slot_updateAnalysis)

        # self listens to myDetectionWidget
        self.myDetectionWidget.signalSelectSpike.connect(self.slot_selectSpike)
        self.myDetectionWidget.signalSelectSpikeList.connect(self.slot_selectSpikeList)
        self.myDetectionWidget.signalSelectSweep.connect(self.slot_selectSweep)
        self.myDetectionWidget.signalDetect.connect(self.slot_detect)

        # (2) detection widget as a dock
        #  detection widget has left panel of controls and right panel of plots
        #  just make left controls a dock widget
        # self.detectionDock = QtWidgets.QDockWidget('Detection',self)
        # self.detectionDock.setWidget(self.myDetectionWidget)
        # self.detectionDock.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures | \
        #                           QtWidgets.QDockWidget.DockWidgetVerticalTitleBar)
        # self.detectionDock.setFloating(False)
        # self.detectionDock.setTitleBarWidget(QtWidgets.QWidget())
        # self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.detectionDock)

        # self.setLayout(_mainVLayout)

        #
        # 2x docks for plugins
        self.myPluginTab1 = QtWidgets.QTabWidget()
        self.myPluginTab1.setMovable(True)
        self.myPluginTab1.setTabsClosable(True)
        self.myPluginTab1.tabCloseRequested.connect(
            partial(self.slot_closeTab, sender=self.myPluginTab1)
        )
        self.myPluginTab1.currentChanged.connect(
            partial(self.slot_changeTab, sender=self.myPluginTab1)
        )
        # re-wire right-click
        self.myPluginTab1.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.myPluginTab1.customContextMenuRequested.connect(
            partial(self.on_plugin_contextMenu, sender=self.myPluginTab1)
        )

        _openPlugins = self.configDict["pluginPanels"]  # dict of
        for _openPlugin, _externalWindow in _openPlugins.items():
            _externalWindow = _externalWindow["externalWindow"]
            logger.info(
                f"  _openPlugin:{_openPlugin} _externalWindow:{_externalWindow}"
            )
            _oneOpenPlugin = self.myPlugins.runPlugin(_openPlugin, ba=None, show=True)
            if _oneOpenPlugin is not None:
                if _externalWindow:
                    # april 30, 2023. Removed! We were opening plugins twice
                    # self.sanpyPlugin_action(_openPlugin)
                    pass
                else:
                    # on add tab, the QTabWIdget makes a copy !!!
                    self.myPluginTab1.addTab(_oneOpenPlugin, _oneOpenPlugin.myHumanName)

        self.pluginDock1 = QtWidgets.QDockWidget("Plugins", self)
        self.pluginDock1.setWidget(self.myPluginTab1)
        self.pluginDock1.setVisible(self.myPluginTab1.count() > 0)
        self.pluginDock1.setFloating(False)
        self.pluginDock1.dockLocationChanged.connect(
            partial(self.slot_dockLocationChanged, self.pluginDock1)
        )
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.pluginDock1)

        #
        # tabs
        """
        self.myPluginTab2 = QtWidgets.QTabWidget()
        self.myPluginTab2.setMovable(True)
        self.myPluginTab2.setTabsClosable(True)
        self.myPluginTab2.tabCloseRequested.connect(partial(self.slot_closeTab, sender=self.myPluginTab2))
        self.myPluginTab2.currentChanged.connect(partial(self.slot_changeTab, sender=self.myPluginTab2))
        # re-wire right-click
        self.myPluginTab2.setContextMenuPolicy(QtCore.Qt.CustomContextMenu);
        self.myPluginTab2.customContextMenuRequested.connect(partial(self.on_plugin_contextMenu, sender=self.myPluginTab2))

        self.pluginDock2 = QtWidgets.QDockWidget('Plugins 2',self)
        self.pluginDock2.setWidget(self.myPluginTab2)
        self.pluginDock2.setFloating(False)
        self.pluginDock2.hide() # initially hide 'Plugins 2'
        self.pluginDock2.dockLocationChanged.connect(partial(self.slot_dockLocationChanged, self.pluginDock2))
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.pluginDock2)
        """

    def sanpyPlugin_action(self, pluginName):
        """Responds to main menu 'Plugins'.

        Run a plugin using curent ba.

        Notes:
            See also on_plugin_contextMenu for running a plugin in a tab
        """
        logger.info(f'opening pluginName: "{pluginName}"')
        ba = self.get_bAnalysis()

        # run the plugin
        _runningPlugin = self.myPlugins.runPlugin(pluginName, ba)

        ltwhTuple = _runningPlugin.getWindowGeometry()

        # add plugin to preferences so it opens next time we run the app
        if _runningPlugin is not None:
            self.configDict.addPlugin(
                _runningPlugin.getHumanName(), externalWindow=True, ltwhTuple=ltwhTuple
            )

        return _runningPlugin
    
    def slot_updateAnalysis(self, sDict : dict):
        """Respond to both detect and user setting columns in ba.
        
        sDict : dict
            setSpikeStatEvent = {}
            setSpikeStatEvent['ba'] = self.ba
            setSpikeStatEvent["spikeList"] = self.getSelectedSpikes()
            setSpikeStatEvent["colStr"] = colStr
            setSpikeStatEvent["value"] = value
        """
        
        logger.info('')
        
        # do the actual update
        ba = sDict['ba']
        spikeList = sDict['spikeList']
        colStr = sDict['colStr']
        value = sDict['value']
        if spikeList is not None and colStr is not None and value is not None:
            logger.info(f'setting backend: {spikeList} colStr: {colStr} to value:{value}')
            ba.setSpikeStat(spikeList, colStr, value)

        self.signalUpdateAnalysis.emit(sDict)

    def slot_selectSpike(self, sDict):
        spikeNumber = sDict["spikeNumber"]
        doZoom = sDict["doZoom"]
        self.selectSpike(spikeNumber, doZoom)

    def slot_selectSpikeList(self, sDict):
        spikeList = sDict["spikeList"]
        doZoom = sDict["doZoom"]
        self.selectSpikeList(spikeList, doZoom)

    def slot_selectSweep(self, ba, sweepNumber):
        """Set view to new sweep.

        Parameters
        ----------
        ba : sanpy.bAnalysis
        sweepNumber : int
        """
        self.signalSelectSweep.emit(ba, sweepNumber)

    def saveFilesTable(self):
        """Save the folder hdf5 file."""
        # logger.info('')
        self.myAnalysisDir.saveHdf()
        self.slot_updateStatus(f"Save analysis for folder: {self.myAnalysisDir.path}")

    def slot_updateStatus(self, text: str):
        """Update the bottom status bar with new str"""
        logger.info(text)

        # having trouble with an immediate update?
        self.statusBar.showMessage(text)
        self.statusBar.repaint()
        # self.statusBar.update()
        self.repaint()
        # self.update()
        QtWidgets.qApp.processEvents()

    def _old_slot_setDetectionParams(self, row, cellType):
        """Set detection parameters to presets.

        Parameters
        ----------
        row : int
            Selected row in file table
        cellType : str
            One of ('SA Node Params', 'Ventricular Params', 'Neuron Params')
        """
        logger.info(f"row:{row} cellType:{cellType}")
        self.myModel.mySetDetectionParams(row, cellType)

    def slot_detect(self, ba):
        """Respond to spike detection.

        Usually comes from the sanpy.interface.bDetectionWidget
        """

        setSpikeStatEvent = {}
        setSpikeStatEvent['ba'] = ba
        setSpikeStatEvent["spikeList"] = None  # self.getSelectedSpikes()
        setSpikeStatEvent["colStr"] = None  # colStr
        setSpikeStatEvent["value"] = None  # value

        # sweep number does not change
        self.signalUpdateAnalysis.emit(setSpikeStatEvent)

        self.slot_updateStatus(f"Detected {ba.numSpikes} spikes")

    def on_plugin_contextMenu(self, point, sender):
        """On right-click in dock, build a menu of plugins.

        On user selection, run the plugin in a tab.

        Notes:
            See also sanpyPlugin_action for running a plugin outside a tab (via main plugin menu)

        Parameters
        ----------
        point :QtCore.QPoint)
            Not used
        sender : QTabWidget
        """
        # logger.info(f'point:{point}, sender:{sender}')

        # list of available plugins
        pluginList = self.myPlugins.pluginList()

        contextMenu = QtWidgets.QMenu(self)

        for plugin in pluginList:
            contextMenu.addAction(plugin)

        # get current mouse/cursor position
        # not sure what 'point' parameter is?
        pos = QtGui.QCursor.pos()
        action = contextMenu.exec_(pos)

        if action is None:
            # no menu selected
            return

        pluginName = action.text()
        ba = self.get_bAnalysis()
        newPlugin = self.myPlugins.runPlugin(pluginName, ba, show=False)

        # only add if plugin wants to be shown
        if not newPlugin.getInitError() and newPlugin.getShowSelf():
            # add tab

            # 1) either this
            # newPlugin.insertIntoScrollArea()
            """
            scrollArea = newPlugin.insertIntoScrollArea()
            if scrollArea is not None:
                newTabIndex = sender.addTab(scrollArea, pluginName)
            else:
                newTabIndex = sender.addTab(newPlugin, pluginName)
            """
            # 2) or this
            # newTabIndex = sender.addTab(newPlugin, pluginName)  # addTab takes ownership
            newTabIndex = sender.addTab(
                newPlugin.getWidget(), pluginName
            )  # addTab takes ownership

            # widgetPointer = sender.widget(newTabIndex)
            # widgetPointer.insertIntoScrollArea()

            # bring tab to front
            sender.setCurrentIndex(newTabIndex)

            ltwhTuple = newPlugin.getWindowGeometry()

            if newPlugin is not None:
                self.configDict.addPlugin(
                    newPlugin.getHumanName(), externalWindow=False, ltwhTuple=ltwhTuple
                )

    def slot_dockLocationChanged(self, dock, area):
        """Top level dock changed

        Parameters
        ----------
        dock : xxx
        area : enum QtCore.Qt.DockWidgetArea
            Basically left/top/right/bottom.

        Not triggered when user 'floats' a dock (See self.slot_topLevelChanged())
        """
        logger.info(f'not implemented, dock:"{dock.windowTitle()}" area enum: {area}')
        return

    def on_fileDock_visibilityChanged(self, visible: bool):
        """The file dock visibility was changed."""
        self._viewMenuAction("filePanels", "File Panel", visible)

    def slot_topLevelChanged(self, topLevel):
        """
        topLevel (bool): True if the dock widget is now floating; otherwise False.

        This is triggered twice, once while dragging and once when finished
        """
        sender = self.sender()  # PyQt5.QtWidgets.QDockWidget
        logger.info(f"topLevel:{topLevel} sender:{sender}")
        return

    def slot_closeTab(self, index, sender):
        """Close an open plugin tab.

        Parameters
        ----------
        index : int
            The index into sender that gives us the tab, sender.widget(index)
        sender : PyQt5.QtWidgets.QTabWidget
            The tab group where a single tab was was closed
        """

        logger.info(f"index:{index} sender:{type(sender)}")

        # remove plugin from self.xxx
        # pluginInstancePointer is full class to actual plugin, like
        # sanpy.interface.plugins.detectionParams.detectionParams
        pluginInstancePointer = sender.widget(index)
        logger.info(f"  closing pluginInstancePointer:{type(pluginInstancePointer)}")

        # remove from preferences
        # if pluginInstancePointer is not None:
        #     self.configDict.removePlugin(pluginInstancePointer.getHumanName())

        self.myPlugins.slot_closeWindow(pluginInstancePointer)

        # remove the tab
        sender.removeTab(index)

    def slot_changeTab(self, index, sender):
        """User brought a different tab to the front

        Make sure only front tab (plugins) receive signals
        """
        logger.info(f"not implemented, index:{index} sender:{sender}")
        pass

    def _old_openLog(self):
        """Open sanpy.log"""
        logFilePath = sanpy.sanpyLogger.getLoggerFile()
        logFilePath = "file://" + logFilePath
        url = QtCore.QUrl(logFilePath)
        QtGui.QDesktopServices.openUrl(url)


def runFft(sanpyWindow):
    logger.info("")
    sanpyWindow._fileListWidget._onLeftClick(0)
    sanpyWindow.myDetectionWidget.setAxis(2.1, 156.8)

    ba = sanpyWindow.get_bAnalysis()
    pluginName = "FFT"
    fftPlugin = sanpyWindow.myPlugins.runPlugin(pluginName, ba)
    resultsStr = fftPlugin.getResultStr()

    print("BINGO")
    print(resultsStr)

    sanpyWindow._fileListWidget._onLeftClick(1)
    sanpyWindow.myDetectionWidget.setAxis(0, 103.7)
    resultsStr = fftPlugin.getResultStr()

    sanpyWindow._fileListWidget._onLeftClick(2)
    sanpyWindow.myDetectionWidget.setAxis(16.4, 28.7)
    resultsStr = fftPlugin.getResultStr()

    print("BINGO")
    print(resultsStr)


def testFFT(sanpyWindow):
    sanpyWindow._fileListWidget._onLeftClick(1)
    # sanpyWindow.myDetectionWidget.setAxis(2.1,156.8)

    ba = sanpyWindow.get_bAnalysis()
    pluginName = "FFT"
    fftPlugin = sanpyWindow.myPlugins.runPlugin(pluginName, ba)

def getAppIconPath():
    bundle_dir = sanpy._util.getBundledDir()
    if getattr(sys, "frozen", False):
        appIconPath = (
            pathlib.Path(bundle_dir) / "sanpy_transparent.png"
        )
    else:
        appIconPath = (
            pathlib.Path(bundle_dir) / "interface" / "icons" / "sanpy_transparent.png"
        )
    return str(appIconPath)

def main():
    """Main entry point for the SanPy desktop app.

    Configured in setup.py
    """
    logger.info(f"Starting sanpy_app.py in main()")
    # date_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # logger.info(f'    {date_time_str}')

    # _version = _getVersionInfo()
    # for k,v in _version.items():
    #     logger.info(f'{k} {v}')

    '''
    logger.info(f'    Python version is {platform.python_version()}')
    logger.info(f'    Python platform is {platform.platform()}')

    # when using import PyQt5
    #logger.info(f"    PyQt version is {QtCore.QT_VERSION_STR}")
    # when using import qtpy
    logger.info(f"    PyQt version is {QtCore.__version__}")

    bundle_dir = sanpy._util.getBundledDir()
    logger.info(f'    bundle_dir is "{bundle_dir}"')

    _logFilePath = sanpy.sanpyLogger.getLoggerFile()
    logger.info(f"    logging to file {_logFilePath}")
    '''

    # for qdarkstyle
    # os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'

    app = QtWidgets.QApplication(sys.argv)

    app.setQuitOnLastWindowClosed(True)

    # for manuscript we need to allow user to set light/dark theme
    # was this
    # v1
    # app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api=os.environ['PYQTGRAPH_QT_LIB']))
    # v2
    qdarktheme.setup_theme()

    appIconPath = getAppIconPath()    
    if os.path.isfile(appIconPath):
        logger.info(f'  app.setWindowIcon with: "{appIconPath}"')
        app.setWindowIcon(QtGui.QIcon(appIconPath))
    else:
        logger.warning(f"    Did not find appIconPath: {appIconPath}")

    w = SanPyWindow()

    w.show()
    w.raise_()  # bring to front, raise is a python keyword
    w.activateWindow()  # bring to front

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
