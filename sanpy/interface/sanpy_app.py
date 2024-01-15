# Author: Robert H Cudmore
# Date: 20190719

# see: https://stackoverflow.com/questions/63871662/python-multiprocessing-freeze-support-error
from multiprocessing import freeze_support
freeze_support()

#from curses.panel import bottom_panel
import os
import sys
import webbrowser  # to open online help

import platform
import pathlib
from datetime import datetime

from typing import Union, Dict, List, Tuple

import pandas as pd

import pyqtgraph as pg

import qdarktheme
qdarktheme.enable_hi_dpi()

from qtpy import QtCore, QtWidgets, QtGui

import sanpy
import sanpy._util
import sanpy.interface
import sanpy.interface.preferences

from sanpy.interface.sanpy_window import SanPyWindow
# import sanpy.interface.SanPyWindow

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)
# This causes mkdocs to infinite recurse when running locally as 'mkdocs serve'
# logger.info('SanPy app.py is starting up')

import logging

# turn off qdarkstyle logging
# logging.getLogger('qdarkstyle').setLevel(logging.WARNING)

# turn off numexpr 'INFO' logging
logging.getLogger("numexpr").setLevel(logging.WARNING)

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

class SanPyApp(QtWidgets.QApplication):
    def __init__(self, argv):
        super().__init__(argv)

        self._windowList = []

        firstTimeRunning = sanpy._util.addUserPath()
        if firstTimeRunning:
            logger.info("  We created <user>/Documents/Sanpy and need to restart")

        self._fileLoaderDict = sanpy.fileloaders.getFileLoaders(verbose=True)
        
        self._detectionClass : sanpy.bDetection = sanpy.bDetection()

        self._configDict : sanpy.interface.preferences = sanpy.interface.preferences(self)
        self._currentWindowGeometry = {
            'x': self._configDict['windowGeometry']['x'],
            'y': self._configDict['windowGeometry']['y'],
            'width': self._configDict['windowGeometry']['width'],
            'height': self._configDict['windowGeometry']['height']
        }

        self._plugins = sanpy.interface.bPlugins(sanpyApp=self)
        self._analysisUtil = sanpy.bAnalysisUtil()

        # self._useDarkStyle = self._configDict["useDarkStyle"]
        self.toggleStyleSheet(buildingInterface=True)
        
        appIconPath = getAppIconPath()    
        if os.path.isfile(appIconPath):
            # logger.info(f'  app.setWindowIcon with: "{appIconPath}"')
            self.setWindowIcon(QtGui.QIcon(appIconPath))
        else:
            logger.warning(f"Did not find appIconPath: {appIconPath}")

        logger.info('-->> SanPyApp done initializing')

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
        
        logger.info(f'path:{path}')
        logger.info(f'   sweep:{sweep}')
        logger.info(f'   spikeNumber:{spikeNumber}')

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

        return foundWindow
    
    def closeSanPyWindow(self, theWindow : SanPyWindow):
        """Remove theWindow from self._windowList.
        """
        logger.info('todo: implement this')
        logger.info('  remove sanpy window from app list of windows')
        for idx, aWindow in enumerate(self._windowList):
            if aWindow == theWindow:
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
        print(self._getVersionInfo())
        self.getSanPyApp()._onAboutMenuAction
        return
    
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

def main():
    """Main entry point for the SanPy desktop app.

    Configured in setup.py
    """
    # logger.info('calling freeze support')
    # freeze_support()

    logger.info(f"Starting sanpy_app.py in main()")
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
    app.openSanPyWindow()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
