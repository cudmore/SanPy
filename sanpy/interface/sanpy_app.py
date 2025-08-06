# Author: Robert H Cudmore
# Date: 20190719

# see: https://stackoverflow.com/questions/63871662/python-multiprocessing-freeze-support-error
from multiprocessing import freeze_support
freeze_support()

#from curses.panel import bottom_panel
import os
import sys
from functools import partial
import webbrowser  # to open online help

import platform
import pathlib
from datetime import datetime

from typing import Union, Dict, List, Tuple

import pandas as pd

import pyqtgraph as pg

# enable_hi_dpi() must be called before the instantiation of QApplication.
import qdarktheme
qdarktheme.enable_hi_dpi()

from qtpy import QtCore, QtWidgets, QtGui

# from sanpy.interface.plugins.sanpyLog import sanpyLog

# # import sanpy
# from sanpy.bDetection import bDetection
# from sanpy.bAnalysisUtil import bAnalysisUtil
# # import sanpy._util
# import sanpy.interface
# import sanpy.interface.preferences

# from sanpy.interface.sanpy_window import SanPyWindow
# from sanpy.interface.openFirstWidget import openFirstWidget

# import sanpy.interface.SanPyWindow

# 202507 need this before starting logger
# from sanpy._util import addUserPath

def _getUserDocumentsFolder():
    """Get <user>/Documents folder."""
    userPath = pathlib.Path.home()
    userDocumentsFolder = os.path.join(userPath, "Documents")
    if not os.path.isdir(userDocumentsFolder):
        # logger.error(f'Did not find path "{userDocumentsFolder}"')
        # logger.error(f'   Using "{userPath}"')
        return userPath
    else:
        return userDocumentsFolder
    
def _getUserSanPyFolder():
    """Get <user>/Documents/SanPy folder."""
    userDocumentsFolder = _getUserDocumentsFolder()
    sanpyFolder = os.path.join(userDocumentsFolder, "SanPy-User-Files")
    return sanpyFolder

def addSanPyUserPath():
    """Make <user>/Documents/SanPy folder and add it to the Python sys.path

    Returns:
        True: If we made the folder (first time SanPy is running)
    """

    # logger.info("")

    madeUserFolder = _makeSanPyFolders()  # make <user>/Documents/SanPy if necc
    userSanPyFolder = _getUserSanPyFolder()

    # if userSanPyFolder in sys.path:
    #     sys.path.remove(userSanPyFolder)

    if userSanPyFolder not in sys.path:
        # logger.info(f"Adding to sys.path: {userSanPyFolder}")
        sys.path.append(userSanPyFolder)

        # logger.info("sys.path is now:")
        # for path in sys.path:
        #     logger.info(f"    {path}")

    return madeUserFolder

def getBundledDir():
    """Get the working directory where user preferences are installed with the package.

    This will be source code folder when running from source,
      will be a more freeform folder when running as a frozen app/exe
    """
    if getattr(sys, "frozen", False):
        # we are running in a bundle (frozen)
        bundle_dir = sys._MEIPASS
    else:
        # we are running in a normal Python environment
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
        # 202507 get the path to the package source
        # when running locally this is Sanpy/sanpy
        bundle_dir = os.path.dirname(bundle_dir)
    return bundle_dir

def _makeSanPyFolders():
    """Make <user>/Documents/SanPy-User-Files folder .

    If no Documents folder then make SanPy folder directly in <user> path.
    """
    # userDocumentsFolder = _getUserDocumentsFolder()

    madeUserFolder = False

    # main <user>/Documents/SanPy folder
    sanpyFolder = _getUserSanPyFolder()
    if not os.path.isdir(sanpyFolder):
        # first time run
        # logger.info(f'Making <user>/SanPy-User-Files folder "{sanpyFolder}"')
        madeUserFolder = True
        #
        # copy entire xxx into <user>/Documents/SanPy
        _bundDir = getBundledDir()  # where our package source is
        _srcPath = pathlib.Path(_bundDir) / "_userFiles" / "SanPy-User-Files"
        _dstPath = pathlib.Path(sanpyFolder)
        # logger.info("    copying folder tree to <user>/Documents/SanPy-User-Folder")
        # logger.info(f"    _srcPath:{_srcPath}")
        # logger.info(f"    _dstPath:{_dstPath}")
        import shutil
        shutil.copytree(_srcPath, _dstPath)
    else:
        # already exists, make sure we have all sub-folders that are expected
        pass

    return madeUserFolder

# CRITICAL: THIS INSTALLS SanPy user files in <user>/Documents
# needs to be done before we start the logger
addSanPyUserPath()

# import sanpy
from sanpy.bDetection import bDetection
from sanpy.bAnalysisUtil import bAnalysisUtil
# import sanpy._util
import sanpy.interface
import sanpy.interface.preferences

from sanpy.interface.sanpy_window import SanPyWindow
from sanpy.interface.openFirstWidget import openFirstWidget

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)
# This causes mkdocs to infinite recurse when running locally as 'mkdocs serve'
# logger.info('SanPy app.py is starting up')

# import to turn off some annoying logging in other packages
import logging

# turn off qdarkstyle logging
# logging.getLogger('qdarkstyle').setLevel(logging.WARNING)

# turn off numexpr 'INFO' logging
logging.getLogger("numexpr").setLevel(logging.WARNING)

def getAppIconPath():
    # bundle_dir = sanpy._util.getBundledDir()
    bundle_dir = getBundledDir()
    if getattr(sys, "frozen", False):
        appIconPath = (
            pathlib.Path(bundle_dir) / "sanpy_transparent.png"
        )
    else:
        appIconPath = (
            pathlib.Path(bundle_dir) / "interface" / "icons" / "sanpy_transparent.png"
        )
    return str(appIconPath)

class SanPyApp(QtWidgets.QApplication):
    def __init__(self, argv):
        super().__init__(argv)

        self._windowList = []
        # list of open SanPyWindow

        # firstTimeRunning = sanpy._util.addUserPath()
        # firstTimeRunning = addSanPyUserPath()
        # if firstTimeRunning:
        #     logger.info("  We created <user>/Documents/Sanpy and need to restart")

        self._fileLoaderDict = sanpy.fileloaders.getFileLoaders(verbose=False)
        
        self._detectionClass : bDetection = bDetection()

        self._configDict : sanpy.interface.preferences = sanpy.interface.preferences(self)
        self._currentWindowGeometry = {
            'x': self._configDict['windowGeometry']['x'],
            'y': self._configDict['windowGeometry']['y'],
            'width': self._configDict['windowGeometry']['width'],
            'height': self._configDict['windowGeometry']['height']
        }

        self._plugins = sanpy.interface.bPlugins(sanpyApp=self)
        
        self._analysisUtil = bAnalysisUtil()

        # self._useDarkStyle = self._configDict["useDarkStyle"]
        self.toggleStyleSheet(buildingInterface=True)
        
        appIconPath = getAppIconPath()    
        if os.path.isfile(appIconPath):
            # logger.info(f'  app.setWindowIcon with: "{appIconPath}"')
            self.setWindowIcon(QtGui.QIcon(appIconPath))
        else:
            logger.warning(f"Did not find appIconPath: {appIconPath}")

        self.openRecentMenu = None

        # open the widget to allow open from recent
        self._openFirstWidget = None
        self.openFirstWidget()

        logger.info('-->> SanPyApp done initializing')

    def openFirstWidget(self):
        """Open a window to allow opening of new and recent files and folder.
        """
        self._openFirstWidget = openFirstWidget(self)
    
        logger.info('   raising openFirstWidget')
        self._openFirstWidget.show()
        # self._openFirstWidget.raise_()  # bring to front, raise is a python keyword
        # self._openFirstWidget.activateWindow()  # bring to front

    def _buildMenus(self, mainMenu):
        
        # fileMenu = mainMenu.addMenu("&File")
        fileMenu = mainMenu.addMenu("File")

        loadFileAction = QtWidgets.QAction("Open File...", self)
        loadFileAction.setEnabled(False)  # disable for now
        loadFileAction.setCheckable(False)  # setChecked is True by default?
        loadFileAction.setShortcut("Ctrl+O")
        loadFileAction.triggered.connect(self.loadFile)
        fileMenu.addAction(loadFileAction)
        
        loadFolderAction = QtWidgets.QAction("Open Folder...", self)
        loadFolderAction.setEnabled(False)  # disable for now
        loadFolderAction.setCheckable(False)  # setChecked is True by default?
        loadFolderAction.triggered.connect(self.loadFolder)
        fileMenu.addAction(loadFolderAction)
        
        # open recent (submenu) will show two lists, one for files and then one for folders
        self.openRecentMenu = QtWidgets.QMenu("Open Recent ...")
        self.openRecentMenu.aboutToShow.connect(self._refreshOpenRecent)
        fileMenu.addMenu(self.openRecentMenu)

        fileMenu.addSeparator()

        # save frontmost window
        saveAction = QtWidgets.QAction("Save", self)
        saveAction.setEnabled(False)  # disable for now
        saveAction.triggered.connect(self.saveFrontmost)
        fileMenu.addAction(saveAction)

        fileMenu.addSeparator()
        
        savePreferencesAction = QtWidgets.QAction("Save Preferences", self)
        savePreferencesAction.setEnabled(False)  # disable for now
        savePreferencesAction.triggered.connect(self.configDict.save)
        fileMenu.addAction(savePreferencesAction)

        # moved to SanPyWindow, see self.getWindowsMenu()
        # show open SanPyWindow(s)
        # self.windowsMenu = mainMenu.addMenu('&Window')
        # self.windowsMenu = mainMenu.addMenu('Window')
        # self.windowsMenu.aboutToShow.connect(self._refreshWindowsMenu)
        # self._refreshWindowsMenu()

        # help menu
        # self.helpMenu = mainMenu.addMenu("&Help")
        self.helpMenu = mainMenu.addMenu("Help")

        name = "SanPy Help (Opens In Browser)"
        action = QtWidgets.QAction(name, self)
        action.triggered.connect(partial(self._onHelpMenuAction, name))
        self.helpMenu.addAction(action)

        # this actually does not show up in the help menu!
        # On macOS PyQt reroutes it to the main python/SanPy menu
        name = "About SanPy"
        action = QtWidgets.QAction(name, self)
        action.triggered.connect(self._onAboutMenuAction)
        self.helpMenu.addAction(action)

        # Add 'SanPy Log...' action before 'About SanPy'
        name = "SanPy Log..."
        # self._sanpyLogWindow = None  # instance variable to hold the log window
        action = QtWidgets.QAction(name, self)
        action.triggered.connect(partial(self._showSanPyLog))
        self.helpMenu.addAction(action)

        # Add 'Email SanPy Support' action
        name = "Email SanPy Support"
        action = QtWidgets.QAction(name, self)
        action.triggered.connect(self._showSupportDialog)
        self.helpMenu.addAction(action)

        # like the help menu, this gets rerouted to the main python/sanp menu
        name = "Preferences ..."
        action = QtWidgets.QAction(name, self)
        action.triggered.connect(self._onPreferencesMenuAction)
        action.setEnabled(False)  # disable for now
        self.helpMenu.addAction(action)
    
        # get help menu as action so other windows can insert their menus before it
        # e.g. SanPyWindow inserts (View, Windows) menus
        # logger.info('mainMenu is now')
        self._helpMenuAction = None
        for _action in mainMenu.actions():
            actionText = _action.text()
            # print('   ', _action.menu(), actionText, _action)
            if actionText == 'Help':
                self._helpMenuAction = _action

        return self._helpMenuAction

    def _showSanPyLog(self):
        # _sanpyLogWindow = sanpyLog()
        # _sanpyLogWindow.show()
        pluginName = 'SanPy Log'
        pluginDict = self.getPlugins().pluginDict
        if pluginName not in pluginDict.keys():
            logger.error(f'Did not find plugin: "{pluginName}"')
            return
        else:
            humanName = pluginDict[pluginName]["constructor"].myHumanName

            logger.info("Running plugin:")
            logger.info(f"  pluginName:{pluginName}")
            logger.info(f"  humanName:{humanName}")
            # if _pluginDict is not None:
            #     logger.info(f"  _pluginDict:{_pluginDict}")
            logger.info("  TODO: put try except back in !!!")
            # TODO: to open PyQt windows, we need to keep a local (persistent) variable
            # try:
            if 1:
                # print(1)
                newPlugin = pluginDict[pluginName]["constructor"](
                    ba=None,
                    sanPyWindow=None,
                    startStop=None
                )
                newPlugin.getWidget().show()
                newPlugin.getWidget().setVisible(True)
    # def _refreshWindowsMenu(self):
    def getWindowsMenu(self, aWindowsMenu):
        
        # aWindowsMenu = QtWidgets.QMenu('&Window')
        
        # open first widget
        action = QtWidgets.QAction('Open Files and Folders', self, checkable=True)
        if self._openFirstWidget is not None:
            action.setChecked(self._openFirstWidget.isActiveWindow())
        action.triggered.connect(partial(self._openFirstWidgetAction))
        aWindowsMenu.addAction(action)

        aWindowsMenu.addSeparator()

        for _sanPyWindow in self._windowList:
            path = _sanPyWindow.path
            action = QtWidgets.QAction(path, self, checkable=True)
            action.setChecked(_sanPyWindow.isActiveWindow())
            action.triggered.connect(partial(self._windowsMenuAction, _sanPyWindow, path))
            # self.windowsMenu.addAction(action)
            aWindowsMenu.addAction(action)
        
        return aWindowsMenu
    
        # was a open plugin menu
        # move back into SanPyWindow and append open widgets
        # for _widget in QtWidgets.QApplication.topLevelWidgets():
        #     if 'sanpy.interface.plugins' in str(type(_widget)):
        #         myHumanName = _widget.myHumanName
        #         print(f'{myHumanName} {_widget}')
        #         action = QtWidgets.QAction(myHumanName, self, checkable=True)
        #         action.setChecked(_widget.isActiveWindow())
        #         action.triggered.connect(partial(self._windowsMenuAction, _widget, myHumanName))
        #         self.windowsMenu.addAction(action)

    def _openFirstWidgetAction(self):
        self._openFirstWidget.show()
        self._openFirstWidget.raise_()
        self._openFirstWidget.activateWindow()  # bring to front

    def _refreshOpenRecent(self):
        """Dynamically generate the open recent file/folder menu.
        
        This is a list of files and then a list of folders"""
        self.openRecentMenu.clear()

        # add files
        for recentFile in self.configDict.getRecentFiles():
            loadFileAction = QtWidgets.QAction(recentFile, self)
            loadFileAction.triggered.connect(
                partial(self.openSanPyWindow, recentFile)
            )

            self.openRecentMenu.addAction(loadFileAction)
        
        self.openRecentMenu.addSeparator()

        # add folders
        for recentFolder in self.configDict.getRecentFolder():
            loadFolderAction = QtWidgets.QAction(recentFolder, self)
            loadFolderAction.triggered.connect(
                partial(self.openSanPyWindow, recentFolder)
            )

            self.openRecentMenu.addAction(loadFolderAction)

    def _windowsMenuAction(self, aSanPyWindow : "SanPyWindow", path, isChecked):
        """
        Parameters
        ----------
        widget : QtWidgets.QWidget
            Either self or an open plugin widget
        path : str
            Name of the window
        """
        
        # don't toggle visibility
        # widget.setVisible(not widget.isVisible())

        logger.info(f'{aSanPyWindow} {path} {isChecked}')
        
        self.setActiveWindow(aSanPyWindow)
        aSanPyWindow.activateWindow()
        aSanPyWindow.raise_()

    def loadFile(self, filePath : str = None):
        """Load one file and open a sanpy window.
        
        Notes
        -----
        Selecting File -> Open... passes bool even when setCheckable(False)
        """

        logger.info(f'filePath:"{filePath}" {type(filePath)}')

        # ask user for file
        if filePath is None or isinstance(filePath, bool):
            filePath, _filter = QtWidgets.QFileDialog.getOpenFileName(caption="Select a raw data file")
            if len(filePath) == 0:
                return
            # filePath is a tuple like
            # ('/Users/cudmore/Sites/SanPy/data/19114000.abf', 'All Files (*)')
            # filePath = filePath[0]
        elif os.path.isfile(filePath):
            pass
        else:
            logger.warning(f'   Did not load file path "{filePath}"')
            return

        logger.info(f'   user selected open file {filePath}')
        
        # spawn a new window
        logger.info('   spawning new window')
        self.openSanPyWindow(filePath)

    def saveFrontmost(self):
        """Save analysis in frontmost window.
        """
        logger.info('')
        # sanpy.interface.sanpy_window.SanPyWindow
        activeWindow = self.activeWindow()
        
        if isinstance(activeWindow, sanpy.interface.sanpy_window.SanPyWindow):
            activeWindow.saveFilesTable()

    def loadFolder(self, path : str = None, folderDepth=None):
        """Load a folder of raw data files.

        Parameters
        ----------
        path : str
        folderDepth : int or None
        """

        if folderDepth is None:
            # get the depth from file list widget
            #folderDepth = self._fileListWidget.getDepth()
            folderDepth = 4
            logger.warning(f'balt april 2025, hard coding folderDepth to {folderDepth}')

        logger.info(f"Loading depth:{folderDepth} path: {path}")

        # ask user for folder
        if path is None:
            path = str(
                QtWidgets.QFileDialog.getExistingDirectory(
                    caption="Select folder with raw data files"
                )
            )
            if len(path) == 0:
                return
        
        if not os.path.isdir(path):
            logger.warning(f'   Did not load path "{path}"')
            return

        self.openSanPyWindow(path)
        
    def getAppIconPath(self):
        return getAppIconPath()
    
    @property
    def useDarkStyle(self):
        # return self._useDarkStyle
        return self._configDict["useDarkStyle"]
    
    def toggleStyleSheet(self, doDark=None, buildingInterface=False):
        logger.info("")
        if doDark is None:
            # doDark = not self._useDarkStyle
            doDark = self.useDarkStyle
        # self._useDarkStyle = doDark
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

        self.configDict["useDarkStyle"] = doDark  # self._useDarkStyle

        if not buildingInterface:
            # self.myScatterPlotWidget.defaultPlotLayout()
            # self.myScatterPlotWidget.buildUI(doRebuild=True)
            
            # 20231229 removed
            # self.myDetectionWidget.mySetTheme()
            pass

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
        
    def getAnalysisUtil(self):
        return self._analysisUtil
    
    def getPlugins(self):
        return self._plugins
    
    def getFileLoaderDict(self):
        return self._fileLoaderDict
    
    def getDetectionClass(self) -> "sanpy.bDetection":
        return self._detectionClass

    # todo: the next three functions can be reduced to just one!

    @property
    def configDict(self):
        return self._configDict
    
    def getConfigDict(self) -> "sanpy.interface.preferences":
        return self._configDict

    def getOptions(self):
        return self._configDict
    
    def newWindowGeometry(self) -> dict:
        """Get geometry for a new window.
        """
        xyOffset = 20
        newWindowGeometry = {
            'x': self._currentWindowGeometry['x'] + xyOffset,
            'y': self._currentWindowGeometry['y'] + xyOffset,
            'width': self._currentWindowGeometry['width'],
            'height': self._currentWindowGeometry['height']
        }

        self._currentWindowGeometry = newWindowGeometry

        return newWindowGeometry

    def openSanPyWindow(self, path=None, sweep=None, spikeNumber=None):
        """Open a new SanPyWindow from a path.
        
        Can be either a file or a folder.
        
        Parameters
        ----------
        sweep : int
            Only works for file path
        """
        interface_mode = self.configDict['interface_mode']  # 'sanpy' or 'kymograph'
        
        logger.info(f'path:{path}')
        logger.info(f'   sweep:{sweep}')
        logger.info(f'   spikeNumber:{spikeNumber}')
        logger.info(f'   interface_mode:{interface_mode}')

        # check if it is open
        foundWindow = None
        for aWindow in self._windowList:
            if aWindow.path == path:
                logger.info('   raising existing window')
                aWindow.raise_()  # bring to front, raise is a python keyword
                aWindow.activateWindow()  # bring to front
                foundWindow = aWindow
            
        # open new window
        if foundWindow is None:
            logger.info('   opening new window')
            
            if interface_mode == 'sanpy':
                foundWindow = SanPyWindow(self, path)
            elif interface_mode == 'kymograph':
                # will either open a TifTreeWindow or a KymRoiWidget

                if os.path.isfile(path):
                    # open KymRoiWidget
                    # from sanpy.kym.interface.kymRoiWidget import KymRoiWidget
                    # foundWindow = KymRoiWidget(self, path)
                    pass
                elif os.path.isdir(path):
                    from sanpy.kym.interface.kym_file_list.tif_tree_window import TifTreeWindow
                    foundWindow = TifTreeWindow(self, path)
                else:
                    logger.warning(f'   Did not load path "{path}"')
                    return
            
            foundWindow.show()
            foundWindow.raise_()  # bring to front, raise is a python keyword
            foundWindow.activateWindow()  # bring to front
            self._windowList.append(foundWindow)

        # only set sweep and select spike if
        # we opened a file path
        if path is not None:
            if os.path.isfile(path):
                if sweep is not None:
                    # _ba = foundWindow.get_bAnalysis()
                    # foundWindow.slot_selectSweep(_ba, sweep)
                    foundWindow.selectSweep_external(sweep)

                if spikeNumber is not None:
                    # foundWindow.slot_selectSpike(sDict)
                    foundWindow.selectSpike(spikeNumber, doZoom=False)

        # add to recent opened windows
        if path is not None:
            self.getOptions().addPath(path)

        # close the initial open first window
        # logger.warning('todo: figure out how to close and garbage collect the _openFirstWidget properly')
        self._openFirstWidget.hide()
        # self._openFirstWidget.close()
        #self._openFirstWidget = None

        return foundWindow
    
    def closeSanPyWindow(self, theWindow : SanPyWindow):
        """Remove theWindow from self._windowList.
        """

        for idx, aWindow in enumerate(self._windowList):
            if aWindow == theWindow:
                logger.info(f'  remove/pop sanpy window from app, idx:{idx}')
                _removedValue = self._windowList.pop(idx)

    def _onHelpMenuAction(self, name: str):
        if name == "SanPy Help (Opens In Browser)":
            url = "https://cudmore.github.io/SanPy/desktop-application"
            webbrowser.open(url, new=2)

    def _onPreferencesMenuAction(self):
        logger.info('')
    
    def _onAboutMenuAction(self):
        """Show a dialog with help.
        """
        # print(self._getVersionInfo())

        dlg = QtWidgets.QDialog()
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
    
    def _showSupportDialog(self):
        """Show the support dialog for sending emails."""
        from sanpy.interface.sanpy_support_widget import show_support_dialog
        # Find the active window to use as parent, or use None if no window is active
        active_window = self.activeWindow()
        show_support_dialog(active_window)
  
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

def main():
    """Main entry point for the SanPy desktop app.

    Configured in setup.py
    """
    # logger.info('calling freeze support')
    # freeze_support()

    logger.info("Starting sanpy_app.py in main()")
    # date_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # logger.info(f'    {date_time_str}')

    # _version = _getVersionInfo()
    # for k,v in _version.items():
    #     logger.info(f'{k} {v}')

    # app = QtWidgets.QApplication(sys.argv)
    app = SanPyApp(sys.argv)

    app.setQuitOnLastWindowClosed(False)

    # for manuscript we need to allow user to set light/dark theme
    # was this
    # v1
    # app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api=os.environ['PYQTGRAPH_QT_LIB']))
    # v2
    qdarktheme.setup_theme()

    # w = SanPyWindow()
    # w.show()
    # w.raise_()  # bring to front, raise is a python keyword
    # w.activateWindow()  # bring to front
    # app.openSanPyWindow()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
