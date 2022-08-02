# Author: Robert H Cudmore
# Date: 20190719

from curses.panel import bottom_panel
import os, sys
# import time
# import math
# import json
#import traceback # to print call stack
from functools import partial
from collections import OrderedDict
import platform
import pathlib
from datetime import datetime

#import glob
#from turtle import window_width
#import numpy as np
import pandas as pd

import qdarkstyle
#import breeze_resources

import webbrowser

from PyQt5 import QtCore, QtWidgets, QtGui

import sanpy._util
import sanpy.interface
import sanpy.interface.preferences

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)
# This causes mkdocs to infinite recurse when running locally as 'mkdocs serve'
#logger.info('SanPy app.py is starting up')

# turn off qdarkstyle logging
import logging
logging.getLogger('qdarkstyle').setLevel(logging.WARNING)

# turn off numexpr 'INFO' logging
logging.getLogger('numexpr').setLevel(logging.WARNING)

#basedir = os.path.dirname(__file__)
#print('sanpy_app basedir:', basedir)

class SanPyWindow(QtWidgets.QMainWindow):

    signalSetXAxis = QtCore.pyqtSignal(object)
    """Emit set axis."""

    signalSwitchFile = QtCore.pyqtSignal(object, object)
    """Emit on switch file."""

    signalSelectSweep = QtCore.pyqtSignal(object, object)  # (ba, sweepNumber)
    """Emit set sweep."""

    signalUpdateAnalysis = QtCore.pyqtSignal(object)
    """Emit on detect."""

    signalSelectSpike = QtCore.pyqtSignal(object)
    """Emit spike selection."""

    signalSelectSpikeList = QtCore.pyqtSignal(object)
    """Emit spike list selection."""

    '''
    # see sanpy.utils.getBundledDir()
    def _getBundledDir():
        """
        TODO: use this in all cases
        """
        if getattr(sys, 'frozen', False):
            # we are running in a bundle (frozen)
            bundle_dir = sys._MEIPASS
        else:
            # we are running in a normal Python environment
            bundle_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info(f'bundle_dir: {bundle_dir}')
        
        return bundle_dir
    '''

    def __init__(self, path=None, parent=None):
        """
        Args:
            path (str): Full path to folder with raw file (abf,csv,tif).
        """

        super(SanPyWindow, self).__init__(parent)

        self.setAcceptDrops(True)

        # TODO: if first time run (no <user>/Documents/SanPy) then warn user to quit and restart

        # create directories in <user>/Documents and add to python path
        firstTimeRunning = sanpy._util.addUserPath()
        if firstTimeRunning:
            logger.info('We created <user>/Documents/Sanpy and need to restart')

        self._detectionClass = sanpy.bDetection()

        # create an empty model for file list
        dfEmpty = pd.DataFrame(columns=sanpy.analysisDir.sanpyColumns.keys())
        self.myModel = sanpy.interface.bFileTable.pandasModel(dfEmpty)

        self.fileFromDatabase = True  # if False then from folder
        #self.csvPath = csvPath

        self.startSec = None
        self.stopSec = None

        myFontSize = 10
        myFont = self.font();
        myFont.setPointSize(myFontSize);
        self.setFont(myFont)

        # todo: update this with selected folder
        if path is not None and os.path.isdir(path):
            windowTitle = f'SanPy {path}'
        else:
            windowTitle = 'SanPy'
        self.setWindowTitle(windowTitle)

        self._rowHeight = 11
        #self.selectedRow = None

        # path to loaded folder (using bAnalysisDir)
        self.configDict = sanpy.interface.preferences(self)
        self.myAnalysisDir = None
        lastPath = self.configDict.getMostRecentFolder()
        logger.info(f'preferences lastPath is "{lastPath}"')
        if path is not None:
            self.path = path
        elif lastPath is not None and os.path.isdir(lastPath):
            self.path = lastPath
        else:
            self.path = None

        '''
        if self.path is not None and len(self.path)>0:
            self.loadFolder(self.path)
        '''

        # I changed saved preferences file,
        # try not to screw up Laura's analysis
        self.useDarkStyle = self.configDict['useDarkStyle']

        #
        # set window geometry
        self.setMinimumSize(640, 480)
        self.left = self.configDict['windowGeometry']['x']
        self.top = self.configDict['windowGeometry']['y']
        self.width = self.configDict['windowGeometry']['width']
        self.height = self.configDict['windowGeometry']['height']
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.myPlugins = sanpy.interface.bPlugins(sanpyApp=self)

        self._buildMenus()
        self._buildUI()

        #self.myExportWidget = None

        #self.dfReportForScatter = None
        #self.dfError = None

        # 20210803, loadFolder was above? Still works down here
        # needed to update detection widget after buildUI()
        if self.path is not None and len(self.path)>0:
            self.loadFolder(self.path)

        self.slot_updateStatus('Ready')
        logger.info('SanPy started')

    def getDetectionClass(self):
        return self._detectionClass

    def dragEnterEvent(self, event):
        logger.info('')
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        logger.info('')
        folders = [u.toLocalFile() for u in event.mimeData().urls()]
        if len(folders) > 1:
            return
        oneFolder = folders[0]
        if os.path.isdir(oneFolder):
            self.loadFolder(path=oneFolder)

    def closeEvent(self, event):
        """
        called when user closes main window or selects quit
        """

        # check if our table view has been edited by uder and warn
        doQuit = True
        alreadyAsked = False
        # self.myAnalysisDir is only defined after we load a folder
        if self.myAnalysisDir is not None:
            tableIsDirty = self.myAnalysisDir.isDirty
            analysisIsDirty = self.myAnalysisDir.hasDirty()
            if tableIsDirty or analysisIsDirty:
                alreadyAsked = True
                userResp = sanpy.interface.bDialog.yesNoCancelDialog('You changed the file database or have analyzed but not saved.\nDo you want to save then quit?')
                if userResp == QtWidgets.QMessageBox.Yes:
                    self.slot_saveFilesTable()
                    event.accept()
                elif userResp == QtWidgets.QMessageBox.No:
                    event.accept()
                else:
                    event.ignore()
                    doQuit = False
        if doQuit:
            if not alreadyAsked:
                userResp = sanpy.interface.bDialog.okCancelDialog('Are you sure you want to quit SanPy?', informativeText=None)
                if userResp == QtWidgets.QMessageBox.Cancel:
                    event.ignore()
                    doQuit = False

            if doQuit:
                logger.info('SanPy is quiting')
                QtCore.QCoreApplication.quit()

    def getOptions(self):
        return self.configDict

    def getWindowGeometry(self):
        myRect = self.geometry()
        left = myRect.left()
        top = myRect.top()
        width = myRect.width()
        height = myRect.height()
        return left, top, width, height

    def toggleStyleSheet(self, doDark=None, buildingInterface=False):
        # breeze
        return

        if doDark is None:
            doDark = self.useDarkStyle
        self.useDarkStyle = doDark
        if doDark:
            self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
        else:
            self.setStyleSheet("")

        self.configDict['useDarkStyle'] = self.useDarkStyle

        if not buildingInterface:
            #self.myScatterPlotWidget.defaultPlotLayout()
            #self.myScatterPlotWidget.buildUI(doRebuild=True)
            self.myDetectionWidget.mySetTheme()

        if buildingInterface:
            pass
        else:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setText("Theme Changed")
            msg.setInformativeText('Please restart SanPy for changes to take effect.')
            msg.setWindowTitle("Theme Changed")
            retval = msg.exec_()

            self.configDict.save()

    def loadFolder(self, path=''):
        """
        Load a folder of .abf

        create df and save in sanpy_recording_db.csv
        """

        #print(f'=== sanpy_app2.loadFolder() "{path}"')
        logger.info(f'Loading path: {path}')
        # ask user for folder
        if isinstance(path,bool) or len(path)==0:
            path = str(QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory With Recordings"))
            if len(path) == 0:
                return
        elif os.path.isdir(path):
            pass
        else:
            logger.warning(f'    Did not load path "{path}"')
            return

        self.path = path # path to loaded bAnalysisDir folder

        #logger.info(f'Loading path: {path}')

        # will create/load csv and/or gzip (of all analysis)
        self.myAnalysisDir = sanpy.analysisDir(path, myApp=self)

        # set myAnalysisDir to file list model
        self.myModel = sanpy.interface.bFileTable.pandasModel(self.myAnalysisDir)
        #self.myModel.signalMyDataChanged.connect(self.slot_dataChanged)
        #self.myModel.signalMyDataChanged.connect(self.myDetectionWidget.slot_dataChanged)

        #try:
        if 1:
            self._fileListWidget.mySetModel(self.myModel)
            self.myModel.signalMyDataChanged.connect(self.myDetectionWidget.slot_dataChanged)
        '''
        except (AttributeError) as e:
            # needed when we call loadFolder from __init__
            # logger.warning('OK: no tableView during load folder')
            pass
        '''

        # set window title
        if self.path is not None and os.path.isdir(self.path):
            windowTitle = f'SanPy: {self.path}'
        else:
            windowTitle = 'SanPy'
        self.setWindowTitle(windowTitle)

        # add to preferences recent folders
        self.configDict.addFolder(path)

        # save preferences
        self.configDict.save()
        
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
                'spikeNumber': spikeNumber,
                'doZoom': doZoom,
                'ba': self.get_bAnalysis(),
                }
        self.signalSelectSpike.emit(eDict)

    def selectSpikeList(self, spikeList, doZoom=False):
        eDict = {
                'spikeList': spikeList,
                'doZoom': doZoom,
                'ba': self.get_bAnalysis(),
                }
        self.signalSelectSpikeList.emit(eDict)

    def mySignal(self, this, data=None):
        """
        this: the signal
        data: depends on signal:
            signal=='set x axis': data=[min,max]
        """
        #print('=== sanpy_app.mySignal() "' + this +'"')

        if this == 'select spike':
            logger.warning('\n\nTODO: GET RID OF "select spike"\n\n')
            spikeNumber = data['spikeNumber']
            doZoom = data['isShift']
            self.selectSpike(spikeNumber, doZoom=doZoom)
            #self.signalSelectSpike.emit(data)

        elif this == 'set x axis':
            logger.info(f'set x axis {data}')

            self.startSec = data[0]
            self.stopSec = data[1]
            # old
            #self.myScatterPlotWidget.selectXRange(data[0], data[1])
            # new
            self.signalSetXAxis.emit([data[0], data[1]])  # emits to scatter plot ONLY

        elif this == 'set full x axis':
            self.startSec = 0
            if self.get_bAnalysis() is not None:
                self.stopSec = self.get_bAnalysis().recordingDur
            else:
                self.stopSec = None
            logger.info(f'set full x axis {self.startSec} {self.stopSec}')
            self.signalSetXAxis.emit([self.startSec, self.stopSec])  # emits to scatter plot ONLY

        elif this == 'cancel all selections':

            self.selectSpike(None)
            self.selectSpikeList([])

        else:
            logger.error(f'Did not understand this: "{this}"')

    '''
    def scatterPlot(self):
        """
        open a new window with an x/y scatter plot
        """
        print('=== MainWindow.scatterPlot() IS NOT IMPLEMENTED !!!')
    '''

    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()
        logger.info(f'text:{text} key:{key} event:{event}')

        # set full axis
        if key in [70, 82]: # 'r' or 'f'
            self.myDetectionWidget.setAxisFull()

        '''
        if key in [QtCore.Qt.Key.Key_P]: # 'r' or 'f'
            self.myDetectionWidget.myPrint()
        '''

        # cancel all selections
        if key == QtCore.Qt.Key.Key_Escape:
            self.mySignal('cancel all selections')

        # hide detection widget
        if text == 'h':
            if self.myDetectionWidget.detectToolbarWidget.isVisible():
                self.myDetectionWidget.detectToolbarWidget.hide()
            else:
                self.myDetectionWidget.detectToolbarWidget.show()

        # print file list model
        if text == 'p':
            print(self.myModel)
            print(self.myModel._data) # this is df updated as user updates table

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
        '''
        selectedRows = self._fileListWidget.selectionModel().selectedRows()
        if len(selectedRows) == 0:
            return None
        else:
            selectedItem = selectedRows[0]
            selectedRow = selectedItem.row()

        rowDict = self.myModel.myGetRowDict(selectedRow)
        return rowDict
        '''

    def slot_fileTableClicked(self, row, rowDict, selectingAgain):
        """Respond to selections in file table."""

        '''
        row (int):
        rowDict (dict):
        selectingAgain (bool): True if row was already selected
        '''

        if selectingAgain:
            self.slot_updateStatus(f'Refreshing file "{rowDict["File"]}"')
        else:
            self.slot_updateStatus(f'Loading file "{rowDict["File"]}" ... please wait')

        # TODO: try and remove this
        self.startSec = rowDict['Start(s)']
        self.stopSec = rowDict['Stop(s)']

        # This will load if necc, otherwise just fetch a pointer
        ba = self.myAnalysisDir.getAnalysis(row) # if None then problem loading

        if ba is not None:
            self.signalSwitchFile.emit(rowDict, ba)
            if selectingAgain:
                pass
            else:
                self.slot_updateStatus(f'Loaded file "{ba.getFileName()}"')# this will load ba if necc

    def _buildMenus(self):

        mainMenu = self.menuBar()

        # load
        loadFolderAction = QtWidgets.QAction('Open Folder ...', self)
        loadFolderAction.setShortcut('Ctrl+O')
        loadFolderAction.triggered.connect(self.loadFolder)

        # open recent (submenu)
        self.openRecentMenu = QtWidgets.QMenu('Open Recent ...')
        self.openRecentMenu.aboutToShow.connect(self._refreshOpenRecent)

        saveDatabaseAction = QtWidgets.QAction('Save Folder Analysis', self)
        saveDatabaseAction.setShortcut('Ctrl+S')
        saveDatabaseAction.triggered.connect(self.slot_saveFilesTable)

        #buildDatabaseAction = QtWidgets.QAction('Build Big Database ...', self)
        #buildDatabaseAction.triggered.connect(self.buildDatabase)

        savePreferencesAction = QtWidgets.QAction('Save Preferences', self)
        savePreferencesAction.triggered.connect(self.configDict.save)

        showLogAction = QtWidgets.QAction('Show Log', self)
        showLogAction.triggered.connect(self.openLog)

        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(loadFolderAction)
        fileMenu.addMenu(self.openRecentMenu)
        fileMenu.addSeparator()
        fileMenu.addAction(saveDatabaseAction)
        fileMenu.addSeparator()
        #fileMenu.addAction(buildDatabaseAction)
        #fileMenu.addSeparator()
        fileMenu.addAction(savePreferencesAction)
        fileMenu.addSeparator()
        fileMenu.addAction(showLogAction)

        '''
        scatterPlotAction = QtWidgets.QAction('Scatter Plot', self)
        scatterPlotAction.triggered.connect(self.scatterPlot)

        exportRawDataAction = QtWidgets.QAction('Export To pdf', self)
        exportRawDataAction.triggered.connect(self.export_pdf)

        windowsMenu = mainMenu.addMenu('&Windows')
        windowsMenu.addAction(scatterPlotAction)
        windowsMenu.addSeparator()
        windowsMenu.addAction(exportRawDataAction)
        '''

        # view menu to toggle theme
        self.viewMenu = mainMenu.addMenu('&View')
        self.viewMenu.aboutToShow.connect(self._refreshViewMenu)
        self._refreshViewMenu()
        #self._populateViewMenu()

        '''
        statisticsPlotAction = QtWidgets.QAction('Statistics Plot', self)
        statisticsPlotAction.triggered.connect(self.toggleStatisticsPlot)
        statisticsPlotAction.setCheckable(True)
        statisticsPlotAction.setChecked(True)
        viewMenu.addAction(statisticsPlotAction)
        '''

        '''
        darkThemeAction = QtWidgets.QAction('Dark Theme', self)
        darkThemeAction.triggered.connect(self.toggleStyleSheet)
        darkThemeAction.setCheckable(True)
        darkThemeAction.setChecked(self.useDarkStyle)
        viewMenu.addAction(darkThemeAction)
        '''

        #
        # plugins
        pluginsMenu = mainMenu.addMenu('&Plugins')
        # getHumanNames
        pluginList = self.myPlugins.pluginList()
        #logger.info(f'pluginList: {pluginList}')
        for plugin in pluginList:
            #logger.info(f'adding plugin: {plugin}')
            sanpyPluginAction = QtWidgets.QAction(plugin, self)

            # TODO: Add spacer between system and user plugins
            #fileMenu.addSeparator()

            '''
            type = self.myPlugins.getType(plugin)
            if type == 'system':
                print(plugin, 'system -->> bold')
                f = sanpyPluginAction.font()
                f.setBold(True);
                f.setItalic(True);
                sanpyPluginAction.setFont(f);
            '''

            sanpyPluginAction.triggered.connect(lambda checked, pluginName=plugin: self.sanpyPlugin_action(pluginName))
            pluginsMenu.addAction(sanpyPluginAction)

        '''
        pluginDir = os.path.join(self._getBundledDir(), 'plugins', '*.txt')
        pluginList = glob.glob(pluginDir)
        logger.info(f'pluginList: {pluginList}')
        pluginsMenu = mainMenu.addMenu('&Plugins')
        oneAction = 'plotRecording'
        sanpyPluginAction = QtWidgets.QAction(oneAction, self)
        #sanpyPluginAction.triggered.connect(self.sanpyPlugin_action)
        sanpyPluginAction.triggered.connect(lambda checked, oneAction=oneAction: self.sanpyPlugin_action(oneAction))
        pluginsMenu.addAction(sanpyPluginAction)
        '''

        #
        # a dynamic menu to show open plugins
        self.windowsMenu = mainMenu.addMenu('&Windows')
        self.windowsMenu.aboutToShow.connect(self._populateOpenPlugins)

        '''
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
        '''

        # help menu
        helpMenu = mainMenu.addMenu('&Help')
        name = 'SanPy Help (Opens In Browser)'
        action = QtWidgets.QAction(name, self)
        action.triggered.connect(partial(self._onHelpMenuAction, name))
        helpMenu.addAction(action)

    def _onHelpMenuAction(self, name : str):
        if name == 'SanPy Help (Opens In Browser)':
            url = 'https://cudmore.github.io/SanPy/'
            webbrowser.open(url, new=2)
        
    def _refreshOpenRecent(self):
        #logger.info('')
        self.openRecentMenu.clear()
        for recentFolder in self.configDict.getRecentFolder():

            loadFolderAction = QtWidgets.QAction(recentFolder, self)
            #loadFolderAction.setShortcut('Ctrl+O')
            loadFolderAction.triggered.connect(partial(self.loadFolder, recentFolder))

            self.openRecentMenu.addAction(loadFolderAction)
    def _refreshViewMenu(self):
        #logger.info('****************')
        
        self.viewMenu.clear()

        self.viewMenu.addSeparator()

        key1 = 'filePanels'

        name = 'File Panel'
        checkedMainPanel = self.configDict[key1]['File Panel']
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checkedMainPanel)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        self.viewMenu.addAction(action)

        self.viewMenu.addSeparator()

        key1 = 'detectionPanels'

        name = 'Detection Panel'
        checkedMainPanel = self.configDict[key1]['Detection Panel']
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checkedMainPanel)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        self.viewMenu.addAction(action)

        self.viewMenu.addSeparator()

        name = 'Detection'
        checked = self.configDict['detectionPanels'][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        action.setEnabled(checkedMainPanel)
        self.viewMenu.addAction(action)

        name = 'Display'
        checked = self.configDict['detectionPanels'][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        action.setEnabled(checkedMainPanel)
        self.viewMenu.addAction(action)

        name = 'Plot Options'
        checked = self.configDict['detectionPanels'][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        action.setEnabled(checkedMainPanel)
        self.viewMenu.addAction(action)

        self.viewMenu.addSeparator()

        # traces (globalvm, dvdt, dac)
        key1 = 'rawDataPanels'

        name = 'Full Recording'
        checked = self.configDict[key1][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        self.viewMenu.addAction(action)

        name = 'Derivative'
        checked = self.configDict[key1][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        self.viewMenu.addAction(action)

        name = 'DAC'
        checked = self.configDict[key1][name]
        action = QtWidgets.QAction(name, self, checkable=True)
        action.setChecked(checked)
        action.triggered.connect(partial(self._viewMenuAction, key1, name))
        self.viewMenu.addAction(action)

    def _viewMenuAction(self, key1, name, isChecked):
        """Respond to user selection in view menu.
        """
        logger.info(f'{name} {isChecked}')
        self.configDict[key1][name] = isChecked
        
        if key1 == 'filePanels':
            self.toggleInterface(name, isChecked)

        elif key1 == 'rawDataPanels':
            #self.toggleInterface(name, isChecked)
            self.myDetectionWidget.toggleInterface(name, isChecked)

        elif key1 == 'detectionPanels':
            self.myDetectionWidget.toggleInterface(name, isChecked)

    def toggleInterface(self, name, on):
        if name == 'File Panel':
            if on:
                #self._fileListWidget.show()
                self.fileDock.show()
            else:
                #self._fileListWidget.hide()
                self.fileDock.hide()

    def _populateOpenPlugins(self):
        self.windowsMenu.clear()
        actions = []
        for plugin in self.myPlugins._openSet:
            name = plugin.myHumanName
            windowTitle = plugin.windowTitle
            action = QtWidgets.QAction(windowTitle, self)
            action.triggered.connect(partial(self._showOpenPlugin, name, plugin, windowTitle))
            actions.append(action)
        self.windowsMenu.addActions(actions)

    def _showOpenPlugin(self, name, plugin, windowTitle, selected):
        logger.info(name)
        logger.info(plugin)
        logger.info(windowTitle)
        logger.info(selected)
        plugin.bringToFront()

    '''
    def toggleInterface(self, panelName, on):
        if panelName == 'Detection Panel':
            if on:
                self.myDetectionWidget.show()
            else:
                self.myDetectionWidget.hide()
    '''

    def _buildUI(self):
        self.toggleStyleSheet(buildingInterface=True)

        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)

        #
        # Detection widget
        baNone = None
        self.myDetectionWidget = sanpy.interface.bDetectionWidget(ba=baNone, mainWindow=self)
        
        # show/hide
        on = self.configDict['detectionPanels']['Detection Panel']
        self.myDetectionWidget.toggleInterface('Detection Panel', on)

        self.signalSwitchFile.connect(self.myDetectionWidget.slot_switchFile)
        self.signalSelectSpike.connect(self.myDetectionWidget.slot_selectSpike) # myDetectionWidget listens to self
        self.signalSelectSpikeList.connect(self.myDetectionWidget.slot_selectSpikeList) # myDetectionWidget listens to self

        self.signalUpdateAnalysis.connect(self.myDetectionWidget.slot_updateAnalysis) # myDetectionWidget listens to self

        self.myDetectionWidget.signalSelectSpike.connect(self.slot_selectSpike) # self listens to myDetectionWidget
        self.myDetectionWidget.signalSelectSweep.connect(self.slot_selectSweep) # self listens to myDetectionWidget
        self.myDetectionWidget.signalDetect.connect(self.slot_detect)

        # detection widget is persistent
        self.setCentralWidget(self.myDetectionWidget)

        #
        # list of files
        self._fileListWidget = sanpy.interface.fileListWidget(self.myModel)
        #self._fileListWidget.signalUpdateStatus.connect(self.slot_updateStatus)  # never used
        self._fileListWidget.getTableView().signalSelectRow.connect(self.slot_fileTableClicked)
        self._fileListWidget.getTableView().signalSetDefaultDetection.connect(self.slot_setDetectionParams)

        # update dvdtThreshold, mvThreshold Start(s), Stop(s)
        self.signalUpdateAnalysis.connect(self._fileListWidget.getTableView().slot_detect)
        #self.myDetectionWidget.signalDetect.connect(self._fileListWidget.slot_detect)

        #
        self.fileDock = QtWidgets.QDockWidget('Files',self)
        self.fileDock.setWidget(self._fileListWidget)
        self.fileDock.setFloating(False)
        self.fileDock.visibilityChanged.connect(self.slot_visibilityChanged)
        self.fileDock.topLevelChanged.connect(self.slot_topLevelChanged)
        self.fileDock.setAllowedAreas(QtCore.Qt.TopDockWidgetArea | QtCore.Qt.BottomDockWidgetArea)
        self.fileDock.dockLocationChanged.connect(partial(self.slot_dockLocationChanged, self.fileDock))
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.fileDock)

        # 2x docks for plugins

        # xxx
        self.myPluginTab1 = QtWidgets.QTabWidget()
        self.myPluginTab1.setMovable(True)
        self.myPluginTab1.setTabsClosable(True)
        self.myPluginTab1.tabCloseRequested.connect(partial(self.slot_closeTab, sender=self.myPluginTab1))
        self.myPluginTab1.currentChanged.connect(partial(self.slot_changeTab, sender=self.myPluginTab1))
        # re-wire right-click
        self.myPluginTab1.setContextMenuPolicy(QtCore.Qt.CustomContextMenu);
        self.myPluginTab1.customContextMenuRequested.connect(partial(self.slot_contextMenu, sender=self.myPluginTab1))

        #
        # add a number of plugins to QDockWidget 'Plugins 1'
        # we need to know the recice human name like 'xxx'
        #detectionPlugin = self.myPlugins.runPlugin('Detection Parameters', ba=None, show=False)
                
        #scatterPlugin = self.myPlugins.runPlugin('Plot Scatter', ba=None, show=False)
        #errorSummaryPlugin = self.myPlugins.runPlugin('Error Summary', ba=None, show=False)
        #summaryAnalysisPlugin = self.myPlugins.runPlugin('Summary Analysis', ba=None, show=False)

        # on add tab, the QTabWIdget makes a copy !!!
        detectionPlugin = self.myPlugins.runPlugin('Detection Parameters', ba=None, show=False)
        if detectionPlugin is not None:
            self.myPluginTab1.addTab(detectionPlugin, detectionPlugin.myHumanName)

        #clipsPlugin = self.myPlugins.runPlugin('Export Trace', ba=None, show=False)
        #self.myPluginTab1.addTab(clipsPlugin, clipsPlugin.myHumanName)

        #self.myPluginTab1.addTab(scatterPlugin, scatterPlugin.myHumanName)
        #self.myPluginTab1.addTab(errorSummaryPlugin, errorSummaryPlugin.myHumanName)
        #self.myPluginTab1.addTab(summaryAnalysisPlugin, summaryAnalysisPlugin.myHumanName)

        #
        #detectionPlugin = self.myPlugins.runPlugin('Detection Parameters', ba=None, show=False)
        #self.myPluginTab1.addTab(detectionPlugin, 'Detection')

        self.pluginDock1 = QtWidgets.QDockWidget('Plugins 1',self)
        self.pluginDock1.setWidget(self.myPluginTab1)
        self.pluginDock1.setFloating(False)
        self.pluginDock1.dockLocationChanged.connect(partial(self.slot_dockLocationChanged, self.pluginDock1))
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea,self.pluginDock1)

        #
        # tabs
        self.myPluginTab2 = QtWidgets.QTabWidget()
        self.myPluginTab2.setMovable(True)
        self.myPluginTab2.setTabsClosable(True)
        self.myPluginTab2.tabCloseRequested.connect(partial(self.slot_closeTab, sender=self.myPluginTab2))
        self.myPluginTab2.currentChanged.connect(partial(self.slot_changeTab, sender=self.myPluginTab2))
        # re-wire right-click
        self.myPluginTab2.setContextMenuPolicy(QtCore.Qt.CustomContextMenu);
        self.myPluginTab2.customContextMenuRequested.connect(partial(self.slot_contextMenu, sender=self.myPluginTab2))

        # Open some default plugins
        # no plugins

        self.pluginsDock2 = QtWidgets.QDockWidget('Plugins 2',self)
        self.pluginsDock2.setWidget(self.myPluginTab2)
        self.pluginsDock2.setFloating(False)
        self.pluginsDock2.hide() # initially hide 'Plugins 2'
        self.pluginsDock2.dockLocationChanged.connect(partial(self.slot_dockLocationChanged, self.pluginsDock2))
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.pluginsDock2)

        #self.setLayout(layout)
        #self.setWindowTitle('SanPy v3')


    def sanpyPlugin_action(self, pluginName):
        """
        Run a plugin using curent ba
        """
        #ba = self.myDetectionWidget.ba
        ba = self.get_bAnalysis()
        self.myPlugins.runPlugin(pluginName, ba)

    def slot_selectSpike(self, sDict):
        spikeNumber = sDict['spikeNumber']
        doZoom = sDict['doZoom']
        self.selectSpike(spikeNumber, doZoom)

    def slot_selectSweep(self, ba, sweepNumber):
        self.signalSelectSweep.emit(ba, sweepNumber)

    def slot_saveFilesTable(self):
        """Needed on user keyboard Ctrl+S
        """
        #logger.info('')
        self.myAnalysisDir.saveHdf()

    def slot_updateStatus(self, text):
        logger.info(text)
        self.statusBar.showMessage(text)
        self.statusBar.repaint()
        #self.statusBar.update()
        self.repaint()
        #self.update()
        QtWidgets.qApp.processEvents()

    def slot_setDetectionParams(self, row, cellType):
        """Set detection parameters to presets.

        Arguments:
            row (int): Selected row in file table
            cellType (str): One of ('SA Node Params', 'Ventricular Params', 'Neuron Params')
        """
        logger.info(f'row:{row} cellType:{cellType}')
        self.myModel.mySetDetectionParams(row, cellType)

    def slot_detect(self, ba):
            #self.myScatterPlotWidget.plotToolbarWidget.on_scatter_toolbar_table_click()

            # not used in buildUI2()
            #dfError = ba.dfError
            #errorReportModel = sanpy.interface.bFileTable.pandasModel(dfError)
            #self.myErrorTable.setModel(errorReportModel)

            # update stats of table load/analyzed columns
            #self.myAnalysisDir._updateLoadedAnalyzed()
            #self.myModel.myUpdateLoadedAnalyzed(ba)

            # TODO: This really should have payload
            self.signalUpdateAnalysis.emit(ba)  # sweep number does not change

            self.slot_updateStatus(f'Detected {ba.numSpikes} spikes')

    def slot_contextMenu(self, point, sender):
        """
        Build a menu of plugins

        Args:
            point (): Not sure
            sender (QTabWidget):
        """
        #sender = self.sender()  # PyQt5.QtWidgets.QDockWidget

        logger.info(f'point:{point}, sender:{sender}')

        # list of available plugins
        pluginList = self.myPlugins.pluginList()

        #contextMenu = QtWidgets.QMenu(self.myTab)
        contextMenu = QtWidgets.QMenu(self)

        for plugin in pluginList:
            contextMenu.addAction(plugin)

        # get current mouse/cursor position, not sure what 'point' is?
        pos = QtGui.QCursor.pos()
        action = contextMenu.exec_(pos)

        if action is None:
            # n menu selected
            return

        #print(action.text())
        pluginName = action.text()
        ba = self.get_bAnalysis()
        newPlugin = self.myPlugins.runPlugin(pluginName, ba, show=False)
        #scatterPlugin = self.myPlugins.runPlugin('Scatter Plot', ba=None, show=False)

        # only add if plugin wants to be shown
        if not newPlugin.getInitError() and newPlugin.getShowSelf():
            # add tab
            #print('newPlugin:', newPlugin)
            # 1) either this
            #newPlugin.insertIntoScrollArea()
            '''
            scrollArea = newPlugin.insertIntoScrollArea()
            if scrollArea is not None:
                newTabIndex = sender.addTab(scrollArea, pluginName)
            else:
                newTabIndex = sender.addTab(newPlugin, pluginName)
            '''
            # 2) or this
            #newTabIndex = sender.addTab(newPlugin, pluginName)  # addTab takes ownership
            newTabIndex = sender.addTab(newPlugin.getWidget(), pluginName)  # addTab takes ownership

            #widgetPointer = sender.widget(newTabIndex)
            #widgetPointer.insertIntoScrollArea()

            # bring tab to front
            #count = sender.count()
            #sender.setCurrentIndex(count-1)
            sender.setCurrentIndex(newTabIndex)

    def slot_dockLocationChanged(self, dock, area):
        """
        area (enum): QtCore.Qt.DockWidgetArea, basically left/top/right/bottom.

        Not triggered when user 'floats' a dock (See self.slot_topLevelChanged())
        """
        logger.info(f'dock:"{dock.windowTitle()}" area enum: {area}')
        return

    def slot_visibilityChanged(self, visible : bool):
        self._viewMenuAction('filePanels', 'File Panel', visible)

    def slot_topLevelChanged(self, topLevel):
        """
        topLevel (bool): True if the dock widget is now floating; otherwise False.

        This is triggered twice, once while dragging and once when finished
        """
        sender = self.sender()  # PyQt5.QtWidgets.QDockWidget
        logger.info(f'topLevel:{topLevel} sender:{sender}')
        return

    def slot_closeTab(self, index, sender):
        """
        Close an open plugin tab.

        Args:
            sender (<PyQt5.QtWidgets.QTabWidget): The tab group where a single tab was was closed
            index (int): The index into sender that gives us the tab, sender.widget(index)
        """

        logger.info(f'index:{index} sender:{sender}')

        # remove plugin from self.xxx
        widgetPointer = sender.widget(index)

        self.myPlugins.slot_closeWindow(widgetPointer)

        # remove the tab
        sender.removeTab(index)

    def slot_changeTab(self, index, sender):
        """
        User brought a different tab to the front

        Make sure only front tab (plugins) receive signals
        """
        #logger.info(f'Turn of all other tab signals !!!')
        pass

    def openLog(self):
        """
        Open sanpy.log in default app
        """
        logFilePath = sanpy.sanpyLogger.getLoggerFile()
        logFilePath = 'file://' + logFilePath
        url = QtCore.QUrl(logFilePath)
        QtGui.QDesktopServices.openUrl(url)

def runFft(sanpyWindow):
    logger.info('')
    sanpyWindow._fileListWidget._onLeftClick(0)
    sanpyWindow.myDetectionWidget.setAxis(2.1,156.8)

    ba = sanpyWindow.get_bAnalysis()
    pluginName = 'FFT'
    fftPlugin = sanpyWindow.myPlugins.runPlugin(pluginName, ba)
    resultsStr = fftPlugin.getResultStr()

    print('BINGO')
    print(resultsStr)

    sanpyWindow._fileListWidget._onLeftClick(1)
    sanpyWindow.myDetectionWidget.setAxis(0, 103.7)
    resultsStr = fftPlugin.getResultStr()

    sanpyWindow._fileListWidget._onLeftClick(2)
    sanpyWindow.myDetectionWidget.setAxis(16.4, 28.7)
    resultsStr = fftPlugin.getResultStr()

    print('BINGO')
    print(resultsStr)

def testFFT(sanpyWindow):
    sanpyWindow._fileListWidget._onLeftClick(1)
    #sanpyWindow.myDetectionWidget.setAxis(2.1,156.8)

    ba = sanpyWindow.get_bAnalysis()
    pluginName = 'FFT'
    fftPlugin = sanpyWindow.myPlugins.runPlugin(pluginName, ba)

def main():
    logger.info(f'Starting sanpy_app.py in __main__()')

    date_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f'    {date_time_str}')

    logger.info(f'    Python version is {platform.python_version()}')
    logger.info(f'    PyQt version is {QtCore.QT_VERSION_STR}')

    bundle_dir = sanpy._util.getBundledDir()
    logger.info(f'    bundle_dir is "{bundle_dir}"')

    _logFilePath = sanpy.sanpyLogger.getLoggerFile()
    logger.info(f'    logging to file {_logFilePath}')

    os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'

    app = QtWidgets.QApplication(sys.argv)

    #appIconPath = os.path.join(bundle_dir, 'interface/icons/sanpy_transparent.png')
    appIconPath = pathlib.Path(bundle_dir) / 'interface' / 'icons' / 'sanpy_transparent.png'
    appIconPathStr = str(appIconPath)
    #logger.info(f'appIconPath is "{appIconPath}"')
    if os.path.isfile(appIconPathStr):
        logger.info(f'    setting app window icon with: "{appIconPath}"')
        app.setWindowIcon(QtGui.QIcon(appIconPathStr))
    else:
        logger.warning(f'    Did not find appIconPath: {appIconPathStr}')

    #app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api=os.environ['PYQTGRAPH_QT_LIB']))

    w = SanPyWindow()

    w.show()

    # to debug the meber function openLog()
    #w.openLog()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
