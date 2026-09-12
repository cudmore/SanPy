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

# 202609 - upgrade to packaging
# PyInstaller sets MPLCONFIGDIR to a throwaway temp dir; persist the font cache.
# Import platformdirs here, not sanpy (matplotlib).
from platformdirs import user_cache_dir


def _configure_matplotlib_cache():
    """Persist Matplotlib's cache when possible in a frozen application."""
    if not getattr(sys, "frozen", False):
        return

    try:
        mpl_config_dir = os.path.join(
            user_cache_dir("SanPy", appauthor=False, ensure_exists=True),
            "matplotlib",
        )
        os.makedirs(mpl_config_dir, exist_ok=True)
    except OSError:
        # A persistent cache is only an optimization. Keep the temporary
        # MPLCONFIGDIR selected by PyInstaller and allow SanPy to start.
        return

    # Override PyInstaller's runtime hook (throwaway temp MPLCONFIGDIR).
    os.environ["MPLCONFIGDIR"] = mpl_config_dir


_configure_matplotlib_cache()

import pandas as pd

import pyqtgraph as pg

import qdarktheme
qdarktheme.enable_hi_dpi()

from qtpy import QtCore, QtWidgets, QtGui

import sanpy
from sanpy import build_info
import sanpy._util
from sanpy.sanpyPaths import SanPyPaths
import sanpy.interface
import sanpy.interface.preferences

from sanpy.fileloaders import getFileLoaders
from sanpy.interface.preferences import preferences
from sanpy.interface.sanpy_window import SanPyWindow
from sanpy.interface.openFirstWidget import openFirstWidget

# import sanpy.interface.SanPyWindow

from sanpy.sanpyLogger import getLoggerText, get_logger
logger = get_logger(__name__)
# This causes mkdocs to infinite recurse when running locally as 'mkdocs serve'
# logger.info('SanPy app.py is starting up')

import logging

# turn off qdarkstyle logging
# logging.getLogger('qdarkstyle').setLevel(logging.WARNING)

# turn off numexpr 'INFO' logging
logging.getLogger("numexpr").setLevel(logging.WARNING)


def _getSanPyInfoForClipboard() -> str:
    """Return complete build metadata followed by all retained log text."""
    logText = getLoggerText()

    return f'{build_info.get_build_info_json()}\n\n=== log file ===\n{logText}'


def _openSanPyUserFilesFolder(
    parent: QtWidgets.QWidget | None = None,
    sanpy_paths: SanPyPaths | None = None,
) -> bool:
    """Open the SanPy user-files folder in the platform file browser.

    Args:
        parent: Parent widget for an error dialog.
        sanpy_paths: Optional application path manager.

    Returns:
        True when Qt accepts the request to open the folder, otherwise False.
    """
    user_folder = (sanpy_paths or SanPyPaths()).user_files_dir
    if not user_folder.is_dir():
        message = f'SanPy-User-Files folder was not found:\n{user_folder}'
        logger.warning(message)
        QtWidgets.QMessageBox.warning(parent, 'SanPy-User-Files', message)
        return False

    folder_url = QtCore.QUrl.fromLocalFile(str(user_folder))
    if not QtGui.QDesktopServices.openUrl(folder_url):
        message = f'Could not open SanPy-User-Files folder:\n{user_folder}'
        logger.warning(message)
        QtWidgets.QMessageBox.warning(parent, 'SanPy-User-Files', message)
        return False
    return True

def getAppIconPath(sanpy_paths: SanPyPaths | None = None) -> str:
    """Return the application icon path.

    Args:
        sanpy_paths: Optional application path manager.

    Returns:
        Application icon path for source or frozen execution.
    """
    bundle_dir = (sanpy_paths or SanPyPaths()).bundled_dir
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
    """Own the SanPy desktop application and its shared services."""

    def __init__(
        self, argv: list[str], sanpy_paths: SanPyPaths | None = None
    ) -> None:
        """Initialize the desktop application.

        Args:
            argv: Command-line arguments passed to Qt.
            sanpy_paths: Optional path manager, primarily for test isolation.
        """
        super().__init__(argv)

        self.sanpy_paths = sanpy_paths or SanPyPaths()

        self._windowList: list[SanPyWindow] = []
        # Keep analysis windows alive until Qt emits their destroyed signal.

        self._quitInProgress = False

        firstTimeRunning = self.sanpy_paths.ensure_user_files()
        if firstTimeRunning:
            logger.info("  We created <user>/Documents/Sanpy and need to restart")

        self._fileLoaderDict = getFileLoaders(verbose=True)
        
        self._detectionClass : sanpy.bDetection = sanpy.bDetection(self.sanpy_paths)

        self._configDict: preferences = preferences(self)
        self._currentWindowGeometry = {
            'x': self._configDict['windowGeometry']['x'],
            'y': self._configDict['windowGeometry']['y'],
            'width': self._configDict['windowGeometry']['width'],
            'height': self._configDict['windowGeometry']['height']
        }

        # Import after sanpy.interface finishes initializing its plugin helpers.
        from sanpy.interface.bPlugins import bPlugins

        self._plugins = bPlugins(sanpyApp=self)
        # self._useDarkStyle = self._configDict["useDarkStyle"]
        self.toggleStyleSheet(buildingInterface=True)
        
        appIconPath = getAppIconPath(self.sanpy_paths)
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

    def showOpenFirstWidget(self):
        """Show and activate the reusable file/folder launcher."""
        self._openFirstWidget.show()
        self._openFirstWidget.raise_()
        self._openFirstWidget.activateWindow()

    def hasAnalysisWindows(self) -> bool:
        """Return True when at least one analysis window is registered."""
        return bool(self._windowList)

    def isLastAnalysisWindow(self, window: SanPyWindow) -> bool:
        """Return True when ``window`` is the only registered analysis window."""
        return len(self._windowList) == 1 and self._windowList[0] is window

    def _register_sanpy_window(self, window: SanPyWindow) -> None:
        """Register an analysis window until Qt destroys it.

        Args:
            window: Analysis window whose Qt lifetime should be tracked.
        """
        window_id = id(window)

        # Capture only the immutable ID. Capturing the window in this callback
        # would create another strong Python reference to the closing widget.
        window.destroyed.connect(
            partial(self._on_sanpy_window_destroyed, window_id)
        )
        self._windowList.append(window)

    def _on_sanpy_window_destroyed(
        self,
        window_id: int,
        _destroyed_object: QtCore.QObject | None = None,
    ) -> None:
        """Remove a window from the registry after Qt destroys it.

        Args:
            window_id: Python identity recorded when the window was registered.
            _destroyed_object: QObject supplied by Qt's ``destroyed`` signal.
        """
        # Do not inspect the emitted QObject because its C++ destruction is
        # already in progress. The stable Python ID is sufficient for removal.
        for index, window in enumerate(self._windowList):
            if id(window) == window_id:
                self._windowList.pop(index)
                return

    @property
    def quitInProgress(self) -> bool:
        return self._quitInProgress

    def requestQuit(self) -> bool:
        """Ask every analysis window to approve, then quit the application.

        Saves are intentionally performed as each window is reviewed. If a later
        window cancels, earlier successful saves remain saved, but no windows
        have been closed.
        """
        if self._quitInProgress:
            return False

        windows = list(self._windowList)
        for window in windows:
            if not window.prepareToClose():
                return False

        self._quitInProgress = True
        for window in windows:
            window.close()

        if self._openFirstWidget is not None:
            self._openFirstWidget.close()

        self.quit()
        return True

    def _buildMenus(
        self,
        mainMenu: QtWidgets.QMenuBar,
        saveFolderAnalysisAction: QtWidgets.QAction | None = None,
    ) -> QtWidgets.QAction | None:
        """Build the shared application menus for a SanPy window.

        Args:
            mainMenu: Menu bar that receives the shared menus.
            saveFolderAnalysisAction: Optional window-specific folder-save
                action. The launcher does not supply one.

        Returns:
            Help-menu action used to insert window-specific menus before Help.
        """
        # fileMenu = mainMenu.addMenu("&File")
        fileMenu = mainMenu.addMenu("File")

        loadFileAction = QtWidgets.QAction("Open File...", self)
        loadFileAction.setCheckable(False)  # setChecked is True by default?
        loadFileAction.setShortcut("Ctrl+O")
        loadFileAction.triggered.connect(self.loadFile)
        fileMenu.addAction(loadFileAction)
        
        loadFolderAction = QtWidgets.QAction("Open Folder...", self)
        loadFolderAction.setCheckable(False)  # setChecked is True by default?
        loadFolderAction.triggered.connect(self.loadFolder)
        fileMenu.addAction(loadFolderAction)
        
        # open recent (submenu) will show two lists, one for files and then one for folders
        self.openRecentMenu = QtWidgets.QMenu("Open Recent ...")
        self.openRecentMenu.aboutToShow.connect(self._refreshOpenRecent)
        fileMenu.addMenu(self.openRecentMenu)

        if saveFolderAnalysisAction is not None:
            fileMenu.addSeparator()
            fileMenu.addAction(saveFolderAnalysisAction)

        fileMenu.addSeparator()

        # QKeySequence.Close maps to Command-W on macOS and Ctrl-W on Windows.
        # Parent the action to this menu's window so only the active window closes.
        window = mainMenu.window()
        closeWindowAction = QtWidgets.QAction("Close Window", window)
        closeWindowAction.setShortcut(QtGui.QKeySequence.Close)
        closeWindowAction.setShortcutContext(QtCore.Qt.WindowShortcut)
        closeWindowAction.triggered.connect(self._close_active_menu_window)
        fileMenu.addAction(closeWindowAction)

        fileMenu.addSeparator()

        savePreferencesAction = QtWidgets.QAction("Save Preferences", self)
        savePreferencesAction.triggered.connect(self.configDict.save)
        fileMenu.addAction(savePreferencesAction)

        quitAction = QtWidgets.QAction("Quit", self)
        quitAction.setMenuRole(QtWidgets.QAction.QuitRole)
        quitAction.setShortcut(QtGui.QKeySequence.Quit)
        quitAction.triggered.connect(self.requestQuit)
        fileMenu.addAction(quitAction)

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

        # like the help menu, this gets rerouted to the main python/sanp menu
        name = "Preferences ..."
        action = QtWidgets.QAction(name, self)
        action.triggered.connect(self._onPreferencesMenuAction)
        self.helpMenu.addAction(action)
    
        # get help menu as action so other windows can insert their menus before it
        # e.g. SanPyWindow inserts (View, Windows) menus
        logger.info('mainMenu is now')
        self._helpMenuAction = None
        for _action in mainMenu.actions():
            actionText = _action.text()
            # print('   ', _action.menu(), actionText, _action)
            if actionText == 'Help':
                self._helpMenuAction = _action

        return self._helpMenuAction

    def _close_active_menu_window(self, _checked: bool = False) -> None:
        """Close the active owner window or one of its registered plugins.

        Args:
            _checked: Unused checked state emitted by ``QAction.triggered``.
        """
        action = self.sender()
        if not isinstance(action, QtWidgets.QAction):
            logger.error("Close Window was triggered without an owning action.")
            return

        window = action.parent()
        if not isinstance(window, QtWidgets.QWidget):
            logger.error("Close Window action does not have a window parent.")
            return

        active_window = QtWidgets.QApplication.activeWindow()
        if active_window is window:
            window.close()
            return

        # Native menu shortcuts can be consumed before a plugin receives its
        # key event. Route the command only to a plugin owned by this window.
        for plugin in getattr(window, "_openPluginSet", set()):
            plugin_window = plugin.getWidget() if hasattr(plugin, "getWidget") else plugin
            if active_window is plugin_window:
                plugin_window.close()
                return
    
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

    def _refreshOpenRecent(self) -> None:
        """Rebuild the recent file/folder menu from preferences."""
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

        self.openRecentMenu.addSeparator()
        clear_action = self.openRecentMenu.addAction("Clear Recents")
        clear_action.triggered.connect(self._clearRecent)

    def _clearRecent(self, _checked: bool = False) -> None:
        """Clear recent paths and refresh the reusable launcher.

        Args:
            _checked: Unused checked state emitted by ``QAction.triggered``.
        """
        self.configDict.clearRecent()
        if self._openFirstWidget is not None:
            self._openFirstWidget.refreshRecent()

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

    def _recording_file_filter(self) -> str:
        """Build the file-dialog filter from registered recording loaders.

        Returns:
            Qt file filter containing every supported recording extension.
        """
        extensions = sorted(
            extension if extension.startswith(".") else f".{extension}"
            for extension in self._fileLoaderDict
        )
        patterns = " ".join(f"*{extension}" for extension in extensions)
        return f"SanPy recordings ({patterns})"

    def _is_supported_recording(self, file_path: str | os.PathLike[str]) -> bool:
        """Return whether a file has a registered recording loader.

        Args:
            file_path: Recording path to validate.

        Returns:
            True when the file extension has a registered loader.
        """
        supported_extensions = {
            extension.lower()
            if extension.startswith(".")
            else f".{extension.lower()}"
            for extension in self._fileLoaderDict
        }
        return pathlib.Path(file_path).suffix.lower() in supported_extensions

    def loadFile(
        self,
        filePath: str | os.PathLike[str] | bool | None = None,
    ) -> None:
        """Prompt for one recording, then open it in an analysis window.

        Args:
            filePath: Explicit recording path. Qt may pass a boolean when this
                method is connected directly to a menu action.
        """

        logger.info(f'filePath:"{filePath}" {type(filePath)}')

        # ask user for file
        if filePath is None or isinstance(filePath, bool):
            filePath, _filter = QtWidgets.QFileDialog.getOpenFileName(
                caption="Select a raw data file",
                filter=self._recording_file_filter(),
            )
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
            folderDepth = 1

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
        
    def getAppIconPath(self) -> str:
        """Return the application icon path.

        Returns:
            Application icon path for source or frozen execution.
        """
        return getAppIconPath(self.sanpy_paths)
    
    @property
    def useDarkStyle(self):
        # return self._useDarkStyle
        return self._configDict["useDarkStyle"]
    
    def toggleStyleSheet(
        self, doDark: bool | None = None, buildingInterface: bool = False
    ) -> None:
        """Apply the selected Qt and pyqtgraph application theme.

        Args:
            doDark: Whether to use the dark theme. The saved preference is used
                when omitted.
            buildingInterface: Whether the application is still constructing
                its initial interface.
        """
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
            # pyqtgraph configuration options are defaults for new widgets;
            # refresh plots that already belong to every open analysis window.
            for window in tuple(self._windowList):
                window.myDetectionWidget.setPlotTheme(doDark)

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

    def openSanPyWindow(
        self,
        path: str | os.PathLike[str] | None = None,
        sweep: int | None = None,
        spikeNumber: int | None = None,
    ) -> SanPyWindow | None:
        """Open or activate an analysis window for a recording or folder.

        Args:
            path: Recording or folder path, or None for an empty window.
            sweep: Optional sweep to select when opening a recording.
            spikeNumber: Optional spike to select when opening a recording.

        Returns:
            Newly created or existing analysis window, or None when ``path``
            is an unsupported file.
        """
        
        logger.info(f'path:{path}')
        logger.info(f'   sweep:{sweep}')
        logger.info(f'   spikeNumber:{spikeNumber}')

        # Reject unsupported files before constructing an analysis window.
        if path is not None and os.path.isfile(path):
            if not self._is_supported_recording(path):
                extension = pathlib.Path(path).suffix or "(no extension)"
                message = (
                    f'SanPy cannot open files with the "{extension}" extension.'
                )
                logger.warning('%s Path: "%s"', message, path)
                QtWidgets.QMessageBox.warning(
                    self._openFirstWidget,
                    "Unsupported File",
                    message,
                )
                return None

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
            foundWindow = SanPyWindow(self, path)
            foundWindow.show()
            foundWindow.raise_()  # bring to front, raise is a python keyword
            foundWindow.activateWindow()  # bring to front
            self._register_sanpy_window(foundWindow)

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
            # The launcher is reused rather than reconstructed, so refresh its
            # cached tables after the successful open updates preferences.
            self._openFirstWidget.refreshRecent()

        # close the initial open first window
        # logger.warning('todo: figure out how to close and garbage collect the _openFirstWidget properly')
        self._openFirstWidget.hide()
        # self._openFirstWidget.close()
        #self._openFirstWidget = None

        return foundWindow
    
    def _onHelpMenuAction(self, name: str):
        if name == "SanPy Help (Opens In Browser)":
            url = "https://cudmore.github.io/SanPy/desktop-application"
            webbrowser.open(url, new=2)

    def _onPreferencesMenuAction(self):
        logger.info('')
    
    def _onAboutMenuAction(self):
        """Show a dialog with help.
        """
        dlg = QtWidgets.QDialog()
        dlg.setWindowTitle('About SanPy')

        vLayout = QtWidgets.QVBoxLayout()

        description = QtWidgets.QLabel(
            'SanPy is designed for whole-cell current clamp analysis. '
            'We are always open to comments and suggestions on how to improve, '
            'extend, and fix SanPy. '
            'Reach out to Robert Cudmore with any ideas, questions, or bug fixes.'
        )
        description.setWordWrap(True)
        vLayout.addWidget(description)

        contact = QtWidgets.QLabel(
            'Contact: Robert Cudmore '
            '(<a href="mailto:robert.cudmore@gmail.com">'
            'robert.cudmore@gmail.com</a>)<br>'
            'Website: <a href="https://mapmanager.net/">'
            'https://mapmanager.net/</a><br>'
            'SanPy Documentation: '
            '<a href="https://cudmore.github.io/SanPy/">'
            'https://cudmore.github.io/SanPy/</a>'
        )
        contact.setTextFormat(QtCore.Qt.RichText)
        contact.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        contact.setOpenExternalLinks(True)
        vLayout.addWidget(contact)

        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setFrameShadow(QtWidgets.QFrame.Sunken)
        vLayout.addWidget(divider)

        for label, value in build_info.get_build_summary_rows():
            vLayout.addWidget(QtWidgets.QLabel(f'{label}: {value}'))

        buttonLayout = QtWidgets.QHBoxLayout()

        copyButton = QtWidgets.QPushButton('Copy SanPy Info')
        copyButton.clicked.connect(
            lambda: QtWidgets.QApplication.clipboard().setText(
                _getSanPyInfoForClipboard()
            )
        )
        buttonLayout.addWidget(copyButton)

        userFilesButton = QtWidgets.QPushButton('SanPy-User-Files')
        userFilesButton.clicked.connect(
            lambda: _openSanPyUserFilesFolder(dlg, self.sanpy_paths)
        )
        buttonLayout.addWidget(userFilesButton)

        vLayout.addLayout(buttonLayout)

        closeButton = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        closeButton.rejected.connect(dlg.reject)
        vLayout.addWidget(closeButton)

        dlg.setLayout(vLayout)

        dlg.exec()

def main():
    """Main entry point for the SanPy desktop app.

    Configured in pyproject.toml.
    """
    # logger.info('calling freeze support')
    # freeze_support()

    logger.info("Starting sanpy_app.py in main()")
    # date_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # logger.info(f'    {date_time_str}')

    # app = QtWidgets.QApplication(sys.argv)
    app = SanPyApp(sys.argv)

    # abb 202609 on windows is painful
    # app.setQuitOnLastWindowClosed(False)
    app.setQuitOnLastWindowClosed(True)

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
