# Author: Robert H Cudmore
# Date: 20190719

import os, sys, time, math, json
import traceback # to print call stack
from functools import partial
from collections import OrderedDict
import platform
import glob
import numpy as np
import pandas as pd

import qdarkstyle

from PyQt5 import QtCore, QtWidgets, QtGui

import sanpy.interface

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)
# This causes mkdocs to infinite recurse when running locally as 'mkdocs serve'
#logger.info('SanPy app.py is starting up')

# turn off qdarkstyle logging
import logging
logging.getLogger('qdarkstyle').setLevel(logging.WARNING)

# turn off numexpr 'INFO' logging
logging.getLogger('numexpr').setLevel(logging.WARNING)

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
		return bundle_dir

	def __init__(self, path=None, parent=None):
		"""
		Args:
			path (str): Full path to folder with raw file (abf,csv,tif).
		"""

		super(SanPyWindow, self).__init__(parent)

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
		self.configDict = self.preferencesLoad()
		self.myAnalysisDir = None
		lastPath = self.configDict['lastPath']
		logger.info(f'json preferences file lastPath "{lastPath}"')
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
		if 'useDarkStyle' in self.configDict.keys():
			self.useDarkStyle = self.configDict['useDarkStyle']
		else:
			#print('  adding useDarkStyle to preferences')
			self.useDarkStyle = True
			self.configDict['useDarkStyle'] = True

		#
		# set window geometry
		self.setMinimumSize(640, 480)
		self.left = self.configDict['windowGeometry']['x']
		self.top = self.configDict['windowGeometry']['y']
		self.width = self.configDict['windowGeometry']['width']
		self.height = self.configDict['windowGeometry']['height']
		self.setGeometry(self.left, self.top, self.width, self.height)

		self.myPlugins = sanpy.interface.bPlugins(sanpyApp=self)

		self.buildMenus()
		self.buildUI()

		#self.myExportWidget = None

		#self.dfReportForScatter = None
		#self.dfError = None

		# 20210803, loadFolder was above? Still works down here
		# needed to update detection widget after buildUI()
		if self.path is not None and len(self.path)>0:
			self.loadFolder(self.path)

		self.slot_updateStatus('Ready')
		logger.info('SanPy started')

	def closeEvent(self, event):
		"""
		called when user closes main window or selects quit
		"""

		# check if our table view has been edited by uder and warn
		doQuit = True
		alreadyAsked = False
		if self.myAnalysisDir.isDirty:
			alreadyAsked = True
			userResp = sanpy.interface.bDialog.yesNoCancelDialog('You changed the file database, do you want to save then quit?')
			if userResp == QtWidgets.QMessageBox.Yes:
				self.slotSaveFilesTable()
				event.accept()
			if userResp == QtWidgets.QMessageBox.No:
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

	def toggleStyleSheet(self, doDark=None, buildingInterface=False):
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

			self.preferencesSave()

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
			logger.warning(f'Did not load path "{path}"')
			return

		self.path = path # path to loaded bAnalysisDir folder

		# will create/load csv and/or gzip (of all analysis)
		self.myAnalysisDir = sanpy.analysisDir(path)

		# set myAnalysisDir to file list model
		self.myModel = sanpy.interface.bFileTable.pandasModel(self.myAnalysisDir)
		#self.myModel.signalMyDataChanged.connect(self.slot_dataChanged)
		#self.myModel.signalMyDataChanged.connect(self.myDetectionWidget.slot_dataChanged)

		try:
			self.tableView.mySetModel(self.myModel)
			self.myModel.signalMyDataChanged.connect(self.myDetectionWidget.slot_dataChanged)
		except (AttributeError) as e:
			# needed when we call loadFolder from __init__
			# logger.warning('OK: no tableView during load folder')
			pass

		# set window title
		if self.path is not None and os.path.isdir(self.path):
			windowTitle = f'SanPy: {self.path}'
		else:
			windowTitle = 'SanPy'
		self.setWindowTitle(windowTitle)

	'''
	def slot_dataChanged(self, columnName, value, rowDict):
		"""User has edited main file table.
		Update detection widget for columns (Start(s), Stop(s), dvdtThreshold, mvThreshold)
		"""
		logger.info(f'{columnName} {value}')
		print('  ', rowDict)
	'''
	def selectSpike(self, spikeNumber, doZoom=False):
		eDict = {}
		eDict['spikeNumber'] = spikeNumber
		eDict['doZoom'] = doZoom
		self.signalSelectSpike.emit(eDict)

	def mySignal(self, this, data=None):
		"""
		this: the signal
		data: depends on signal:
			signal=='set x axis': data=[min,max]
		"""
		#print('=== sanpy_app.mySignal() "' + this +'"')

		if this == 'detect':
			# seel self.slot_detect()
			return

			'''
			logger.info('detect')
			# update scatter plot
			self.myScatterPlotWidget.plotToolbarWidget.on_scatter_toolbar_table_click()

			# data = dfReportForScatter
			# data[0] is:
			# dfReportForScatter = self.ba.spikeDetect(detectionDict)
			#self.dfReportForScatter = data[0] # can be none when start/stop is not defined

			# data[1] is
			# dfError = self.ba.errorReport()
			# update error table
			#self.dfError = data[1]
			dfError = self.get_bAnalysis().dfError
			errorReportModel = sanpy.interface.bFileTable.pandasModel(dfError)
			self.myErrorTable.setModel(errorReportModel)

			# update stats of table load/analyzed columns
			#self.myAnalysisDir._updateLoadedAnalyzed()
			self.myModel.myUpdateLoadedAnalyzed()

			# TODO: This really should have payload
			self.signalUpdateAnalysis.emit(self.get_bAnalysis())
			'''

		elif this == 'select spike':
			print('\n\nTODO: GET RID OF "select spike"\n\n')
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
			self.startSec = None
			self.stopSec = None
			#self.myScatterPlotWidget.selectXRange(None, None)
			logger.info('set full x axis')
			self.signalSetXAxis.emit([None, None])  # emits to scatter plot ONLY

		elif this == 'cancel all selections':
			self.myDetectionWidget.selectSpike(None)

			if self.myScatterPlotWidget.isVisible():
				self.myScatterPlotWidget.selectSpike(None)
			# removing this may cause problems on file change ?
			#self.myScatterPlotWidget.selectXRange(None, None)

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
		logger.info(f'key:{key} event:{event}')

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
		selectedRows = self.tableView.selectionModel().selectedRows()
		if len(selectedRows) == 0:
			return None
		else:
			selectedItem = selectedRows[0]
			selectedRow = selectedItem.row()

		rowDict = self.myModel.myGetRowDict(selectedRow)

		#logger.info(f'row:{selectedRow} {rowDict}')

		return rowDict

	def slot_fileTableClicked(self, row, rowDict):
		"""Respond to selections in file table."""

		'''
		tableRowDict = self.myModel.myGetRowDict(row)
		abfColumnName = 'File'
		fileName = self.myModel.myGetValue(row, abfColumnName)
		'''
		#fileName = rowDict['File']

		self.slot_updateStatus(f'Loading file "{rowDict["File"]}" ... please wait')# this will load ba if necc

		self.startSec = rowDict['Start(s)']
		self.stopSec = rowDict['Stop(s)']

		ba = self.myAnalysisDir.getAnalysis(row) # if None then problem loading

		if ba is not None:
			self.signalSwitchFile.emit(rowDict, ba)
			self.slot_updateStatus(f'Loaded file "{ba.getFileName()}"')# this will load ba if necc

	def buildMenus(self):

		mainMenu = self.menuBar()

		loadFolderAction = QtWidgets.QAction('Load Folder ...', self)
		loadFolderAction.setShortcut('Ctrl+O')
		loadFolderAction.triggered.connect(self.loadFolder)

		saveDatabaseAction = QtWidgets.QAction('Save Database', self)
		saveDatabaseAction.setShortcut('Ctrl+S')
		saveDatabaseAction.triggered.connect(self.slotSaveFilesTable)

		#buildDatabaseAction = QtWidgets.QAction('Build Big Database ...', self)
		#buildDatabaseAction.triggered.connect(self.buildDatabase)

		savePreferencesAction = QtWidgets.QAction('Save Preferences', self)
		savePreferencesAction.triggered.connect(self.preferencesSave)

		showLogAction = QtWidgets.QAction('Show Log', self)
		showLogAction.triggered.connect(self.openLog)

		fileMenu = mainMenu.addMenu('&File')
		fileMenu.addAction(loadFolderAction)
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
		viewMenu = mainMenu.addMenu('&View')

		'''
		statisticsPlotAction = QtWidgets.QAction('Statistics Plot', self)
		statisticsPlotAction.triggered.connect(self.toggleStatisticsPlot)
		statisticsPlotAction.setCheckable(True)
		statisticsPlotAction.setChecked(True)
		viewMenu.addAction(statisticsPlotAction)
		'''

		darkThemeAction = QtWidgets.QAction('Dark Theme', self)
		darkThemeAction.triggered.connect(self.toggleStyleSheet)
		darkThemeAction.setCheckable(True)
		darkThemeAction.setChecked(self.useDarkStyle)
		viewMenu.addAction(darkThemeAction)

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
		# a dynamic menu to show opten plugins
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

	def buildUI(self):
		self.toggleStyleSheet(buildingInterface=True)

		self.statusBar = QtWidgets.QStatusBar()
		self.setStatusBar(self.statusBar)

		# was this
		#self.centralwidget = QtWidgets.QWidget(self)
		#self.centralwidget.setObjectName("centralwidget")

		# was this
		#self.myQVBoxLayout = QtWidgets.QVBoxLayout(self.centralwidget)
		#self.myQVBoxLayout.setAlignment(QtCore.Qt.AlignTop)

		#
		# table of files

		#self.tableView = sanpy.interface.bFileTable.myTableView()
		# self.myModel starts with just columns (no data)
		self.tableView = sanpy.interface.bTableView(self.myModel)
		'''
		self.tableView.signalUnloadRow.connect(self.slotUnloadRow)
		self.tableView.signalRemoveFromDatabase.connect(self.slotRemoveFromDatabase)
		self.tableView.signalDuplicateRow.connect(self.slotDuplicateRow)
		self.tableView.signalDeleteRow.connect(self.slotDeleteRow)
		self.tableView.signalCopyTable.connect(self.slotCopyTable)
		self.tableView.signalFindNewFiles.connect(self.slotFindNewFiles)
		self.tableView.signalSaveFileTable.connect(self.slotSaveFilesTable)
		'''
		self.tableView.signalUpdateStatus.connect(self.slot_updateStatus)
		#self.tableView.mySetModel(self.myModel)
		#self.tableView.clicked.connect(self.new_tableClicked)
		#self.tableView.selectionChanged.connect(self.new_tableclicked2)
		self.tableView.signalSelectRow.connect(self.slot_fileTableClicked)
		self.tableView.signalSetDefaultDetection.connect(self.slot_setDetectionParams)

		#self.myQVBoxLayout.addWidget(self.tableView)#, stretch=4)

		#
		# detect/plot widget, on the left are params and on the right are plots
		baNone = None
		self.myDetectionWidget = sanpy.interface.bDetectionWidget(baNone,self)
		self.signalSwitchFile.connect(self.myDetectionWidget.slot_switchFile)
		self.signalSelectSpike.connect(self.myDetectionWidget.slot_selectSpike) # myDetectionWidget listens to self
		self.myDetectionWidget.signalSelectSpike.connect(self.slot_selectSpike) # self listens to myDetectionWidget
		self.myDetectionWidget.signalSelectSweep.connect(self.slot_selectSweep) # self listens to myDetectionWidget
		self.myDetectionWidget.signalDetect.connect(self.slot_detect)
		# update dvdtThreshold, mvThreshold Start(s), Stop(s)
		self.myDetectionWidget.signalDetect.connect(self.tableView.slot_detect)

		#
		# scatter plot
		self.myScatterPlotWidget = sanpy.interface.bScatterPlotWidget(self, self.myDetectionWidget)
		#self.myQVBoxLayout.addWidget(self.myScatterPlotWidget)
		self.signalSelectSpike.connect(self.myScatterPlotWidget.slotSelectSpike)
		self.signalSetXAxis.connect(self.myScatterPlotWidget.slot_setXAxis)
		self.signalSelectSweep.connect(self.myScatterPlotWidget.slot_selectSweep)
		self.signalUpdateAnalysis.connect(self.myScatterPlotWidget.slot_updateAnalysis)
		if self.configDict['display']['showScatter']:
			pass
		else:
			self.myScatterPlotWidget.hide()

		#
		# error report
		#self.myErrorTable = QtWidgets.QTableView()
		self.myErrorTable = sanpy.interface.bErrorTable.errorTableView()
		self.myErrorTable.signalSelectSpike.connect(self.slot_selectSpike)
		#self.myErrorTable.clicked.connect(self.errorTableClicked)
		self.myErrorTable.hide() # start hidden
		#self.myQVBoxLayout.addWidget(self.myErrorTable)

		#
		# use splitter
		self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
		#self.main_splitter.setAlignment(QtCore.Qt.AlignTop) # trying to get vertical alignment to be tighter
		self.main_splitter.addWidget(self.tableView)
		self.main_splitter.addWidget(self.myDetectionWidget)
		self.main_splitter.addWidget(self.myScatterPlotWidget)
		self.main_splitter.addWidget(self.myErrorTable)

		# was this
		#self.myQVBoxLayout.addWidget(self.main_splitter)

		centralwidget = QtWidgets.QWidget(self)
		myHBoxLayout = QtWidgets.QHBoxLayout(centralwidget)
		myHBoxLayout.addWidget(self.main_splitter)
		#
		# leave here, critical
		# was this
		self.setCentralWidget(centralwidget)
		#self.setCentralWidget(self.main_splitter)
		#self.setLayout(myHBoxLayout)

	def preferencesSet(self, key1, key2, val):
		"""Set a preference. See `preferencesDefaults()` for key values."""
		try:
			self.configDict[key1][key2] = val

			# actually show hide some widgets
			if key1=='display' and key2=='showScatter':
				if val:
					self.myScatterPlotWidget.show()
				else:
					self.myScatterPlotWidget.hide()
			elif key1=='display' and key2=='showErrors':
				if val:
					self.myErrorTable.show()
				else:
					self.myErrorTable.hide()

		except (KeyError) as e:
			logger.error(f'Did not set preference with keys "{key1}" and "{key2}"')

	def preferencesGet(self, key1, key2):
		"""Get a preference. See `preferencesDefaults()` for key values."""
		try:
			return self.configDict[key1][key2]
		except (KeyError) as e:
			logger.error(f'Did not get preference with keys "{key1}" and "{key2}"')

	def preferencesLoad(self):
		'''
		if getattr(sys, 'frozen', False):
			# we are running in a bundle (frozen)
			bundle_dir = sys._MEIPASS
		else:
			# we are running in a normal Python environment
			bundle_dir = os.path.dirname(os.path.abspath(__file__))
		'''
		bundle_dir = SanPyWindow._getBundledDir()
		# load preferences
		self.optionsFile = os.path.join(bundle_dir, 'sanpy_app.json')

		if os.path.isfile(self.optionsFile):
			#print('  preferencesLoad() loading options file:', self.optionsFile)
			logger.info(f'Loading options file: {self.optionsFile}')
			with open(self.optionsFile) as f:
				return json.load(f)
		else:
			#print('	 preferencesLoad() using program provided default options')
			#print('  did not find file:', self.optionsFile)
			logger.info(f'Using default options')
			return self.preferencesDefaults()

	def preferencesDefaults(self):
		configDict = OrderedDict()

		configDict['useDarkStyle'] = True
		configDict['autoDetect'] = True # FALSE DOES NOT WORK!!!! auto detect on file selection and/or sweep selection
		configDict['lastPath'] = ''
		configDict['windowGeometry'] = {}
		configDict['windowGeometry']['x'] = 100
		configDict['windowGeometry']['y'] = 100
		configDict['windowGeometry']['width'] = 1000
		configDict['windowGeometry']['height'] = 1000

		"""
		configDict['detection'] = {}
		configDict['detection']['dvdtThreshold'] = 100
		configDict['detection']['minSpikeVm'] = -20
		configDict['detection']['medianFilter'] = 5
		"""

		configDict['detect'] = {}
		configDict['detect']['detectDvDt'] = 20
		configDict['detect']['detectMv'] = -20

		configDict['display'] = {}
		configDict['display']['plotEveryPoint'] = 10 # not used?
		configDict['display']['showGlobalVm'] = True #
		configDict['display']['showDvDt'] = True #
		configDict['display']['showDAC'] = True #
		configDict['display']['showGlobalVm'] = True #
		configDict['display']['showClips'] = False #
		configDict['display']['showScatter'] = False #
		configDict['display']['showErrors'] = False #

		return configDict

	def preferencesSave(self):
		#print('=== SanPy_App.preferencesSave() file:', self.optionsFile)
		logger.info(f'Saving options file as: "{self.optionsFile}"')

		myRect = self.geometry()
		left = myRect.left()
		top = myRect.top()
		width = myRect.width()
		height = myRect.height()

		self.configDict['windowGeometry']['x'] = left
		self.configDict['windowGeometry']['y'] = top
		self.configDict['windowGeometry']['width'] = width
		self.configDict['windowGeometry']['height'] = height

		self.configDict['lastPath'] = self.path

		#
		# save
		with open(self.optionsFile, 'w') as outfile:
			json.dump(self.configDict, outfile, indent=4, sort_keys=True)

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

	def slotSaveFilesTable(self):
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

			dfError = ba.dfError
			errorReportModel = sanpy.interface.bFileTable.pandasModel(dfError)
			self.myErrorTable.setModel(errorReportModel)

			# update stats of table load/analyzed columns
			#self.myAnalysisDir._updateLoadedAnalyzed()
			#self.myModel.myUpdateLoadedAnalyzed(ba)

			# TODO: This really should have payload
			self.signalUpdateAnalysis.emit(ba)  # sweep number does not change

			self.slot_updateStatus(f'Detected {ba.numSpikes} spikes')

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
	sanpyWindow.tableView._onLeftClick(0)
	sanpyWindow.myDetectionWidget.setAxis(2.1,156.8)

	ba = sanpyWindow.get_bAnalysis()
	pluginName = 'FFT'
	fftPlugin = sanpyWindow.myPlugins.runPlugin(pluginName, ba)
	resultsStr = fftPlugin.getResultStr()

	print('BINGO')
	print(resultsStr)

	sanpyWindow.tableView._onLeftClick(1)
	sanpyWindow.myDetectionWidget.setAxis(0, 103.7)
	resultsStr = fftPlugin.getResultStr()

	sanpyWindow.tableView._onLeftClick(2)
	sanpyWindow.myDetectionWidget.setAxis(16.4, 28.7)
	resultsStr = fftPlugin.getResultStr()

	print('BINGO')
	print(resultsStr)

def testFFT(sanpyWindow):
	sanpyWindow.tableView._onLeftClick(1)
	#sanpyWindow.myDetectionWidget.setAxis(2.1,156.8)

	ba = sanpyWindow.get_bAnalysis()
	pluginName = 'FFT'
	fftPlugin = sanpyWindow.myPlugins.runPlugin(pluginName, ba)

def main():
	logger.info(f'=== Starting sanpy_app.py in __main__')
	logger.info(f'Python version is {platform.python_version()}')
	logger.info(f'PyQt version is {QtCore.QT_VERSION_STR}')

	app = QtWidgets.QApplication(sys.argv)

	'''
	if getattr(sys, 'frozen', False):
		# we are running in a bundle (frozen)
		bundle_dir = sys._MEIPASS
	else:
		# we are running in a normal Python environment
		bundle_dir = os.path.dirname(os.path.abspath(__file__))
	'''
	bundle_dir = SanPyWindow._getBundledDir()
	logger.info(f'bundle_dir is "{bundle_dir}"')

	appIconPath = os.path.join(bundle_dir, 'icons/sanpy_transparent.png')
	logger.info(f'appIconPath is "{appIconPath}"')
	if os.path.isfile(appIconPath):
		app.setWindowIcon(QtGui.QIcon(appIconPath))
	else:
		logger.error(f'Did not find appIconPath: {appIconPath}')

	# can specify with 'path='
	#path = '/Users/cudmore/data/laura-ephys/test1_sanpy2'
	#path = '/Users/cudmore/data/laura-ephys/sanap20210412'

	w = SanPyWindow()

	#testFFT(w)

	#loadFolder = '/home/cudmore/Sites/SanPy/data'
	#w.loadFolder(loadFolder)

	w.show()

	#runFft(w)

	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
