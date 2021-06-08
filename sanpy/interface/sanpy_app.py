# Author: Robert H Cudmore
# Date: 20190719

import os, sys, time, math, json
from functools import partial
from collections import OrderedDict
import platform

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

class MainWindow(QtWidgets.QMainWindow):

	"""signalUpdateStatusBar (pyqtSignal): xxx"""
	signalUpdateStatusBar = QtCore.pyqtSignal(object)

	# yyy
	signalSetXAxis = QtCore.pyqtSignal(object)
	# zzz
	signalSelectSpike = QtCore.pyqtSignal(object)

	def __init__(self, csvPath=None, path=None, parent=None):
		"""
		Args:
			path (str): Full path to folder with raw file (abf,csv,tif).
		"""

		super(MainWindow, self).__init__(parent)

		self.myModel = None

		self.fileFromDatabase = True # if False then from folder
		self.csvPath = csvPath

		myFontSize = 10
		myFont = self.font();
		myFont.setPointSize(myFontSize);
		self.setFont(myFont)

		# todo: update this with selected folder
		if path is not None and os.path.isdir(path):
			windowTitle = f'SanPy {path}'
		elif csvPath is not None:
			csvName = os.path.split(csvPath)[1]
			windowTitle = f'SanPy {csvName}'
		else:
			windowTitle = 'SanPy'
		self.setWindowTitle(windowTitle)

		self._rowHeight = 11
		self.selectedRow = None

		# todo: modify self.path if we get a good folder
		self.configDict = self.preferencesLoad()
		lastPath = self.configDict['lastPath']
		logger.info(f'json preferences file lastPath "{lastPath}"')
		if path is not None:
			self.path = path
		elif csvPath is not None:
			self.path = os.path.split(csvPath)[0]
		elif lastPath is not None and os.path.isdir(lastPath):
			self.path = lastPath
		else:
			self.path = None
		#print('  self.path:', self.path)
		if self.path is not None and len(self.path)>0:
			self.loadFolder(self.path)

		# I changed saved preferences file, try not to screw up Laura's analysis
		if 'useDarkStyle' in self.configDict.keys():
			self.useDarkStyle = self.configDict['useDarkStyle']
		else:
			#print('  adding useDarkStyle to preferences')
			self.useDarkStyle = True
			self.configDict['useDarkStyle'] = True

		# set window geometry
		self.setMinimumSize(640, 480)

		self.left = self.configDict['windowGeometry']['x']
		self.top = self.configDict['windowGeometry']['y']
		self.width = self.configDict['windowGeometry']['width']
		self.height = self.configDict['windowGeometry']['height']

		self.setGeometry(self.left, self.top, self.width, self.height)

		self.csvPath = csvPath
		masterDf = sanpy.interface.bFileTable.loadDatabase(csvPath)
		if masterDf is not None:
			loggerr.debug(f'Loaded csvPath: {csvPath}')

		self.buildMenus()

		self.buildUI(masterDf)

		self.myExportWidget = None

		self.dfReportForScatter = None
		self.dfError = None

		self.updateStatusBar('SanPy started')
		logger.info('SanPy started')

	def closeEvent(self, event):
		"""
		called when user closes main window or selects quit
		"""
		#print('sanpy_app2.closeEvent()', event)

		# check if our table view has been edited by uder and warn
		doQuit = True
		if self.myModel is not None and self.myModel.isDirty:
			#print('  model is dirty -->> need to save')
			#userResp = sanpy.interface.bDialog.okDialog('xxx')
			userResp = sanpy.interface.bDialog.yesNoCancelDialog('You changed the file database, do you want to save then quit?')
			#print('  todo: fix userResp:', userResp)
			if userResp == QtWidgets.QMessageBox.Yes:
				self.slotSaveFilesTable()
				event.accept()
			if userResp == QtWidgets.QMessageBox.No:
				event.accept()
			else:
				event.ignore()
				doQuit = False
		else:
			pass
			#print('  model is not dirty -->> no need to save')
		if doQuit:
			logger.info('SanPy is quiting')

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
			#print('  returning none')
			logger.info('returning None')
			return

		bad = sanpy.bAnalysisDir(path)
		df = bad.df

		self.path = path

		# set df to model
		self.myModel = sanpy.interface.bFileTable.pandasModel(df)
		try:
			self.tableView.setModel(self.myModel)
		except (AttributeError) as e:
			# needed when we call loadFolder from __init__
			logger.info('OK exception', e)

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

		if this == 'set abfError':
			pass

			# todo: make this more efficient, just update one row
			#self.refreshFileTableWidget()
			#self.refreshFileTableWidget_Row()

		elif this == 'detect':
			# update scatter plot
			self.myScatterPlotWidget.plotToolbarWidget.on_scatter_toolbar_table_click()

			# data = dfReportForScatter
			self.dfReportForScatter = data[0] # can be none when start/stop is not defined

			# update eror table
			self.dfError = data[1]
			errorReportModel = sanpy.interface.bFileTable.pandasModel(self.dfError)
			self.myErrorTable.setModel(errorReportModel)

		elif this == 'saved':
			pass
			# todo: make this more efficient, just update one row
			#self.refreshFileTableWidget()
			#self.refreshFileTableWidget_Row()

		elif this == 'select spike':
			spikeNumber = data['spikeNumber']
			doZoom = data['isShift']
			self.selectSpike(spikeNumber, doZoom=doZoom)
			#self.signalSelectSpike.emit(data)

		elif this == 'set x axis':
			# old
			self.myScatterPlotWidget.selectXRange(data[0], data[1])
			# new
			self.signalSetXAxis.emit([data[0], data[1]])

		elif this == 'set full x axis':
			self.myScatterPlotWidget.selectXRange(None, None)

		elif this == 'cancel all selections':
			self.myDetectionWidget.selectSpike(None)
			self.myScatterPlotWidget.selectSpike(None)
			# removing this may cause problems on file change ?
			#self.myScatterPlotWidget.selectXRange(None, None)

		else:
			print('MainWindow.mySignal() did not understand this:', this)

	def scatterPlot(self):
		"""
		open a new window with an x/y scatter plot
		"""
		print('=== MainWindow.scatterPlot() IS NOT IMPLEMENTED !!!')

	def keyPressEvent(self, event):
		#print('=== sanpy_app.MainWindow() keyPressEvent()')
		key = event.key()
		text = event.text()

		#print('== MainWindow.keyPressEvent() key:', key, 'text:', text)
		#logger.info(f'key: {key} text: {text}')

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

	def toggleErrorTable(self, state):
		if state:
			self.myErrorTable.show()
		else:
			self.myErrorTable.hide()

	def toggleStatisticsPlot(self, state):
		"""
		toggle scatter plot on/off
		"""
		#print('toggleStatisticsPlot() state:', state)
		self.configDict['display']['showScatter'] = state
		if state:
			self.myScatterPlotWidget.show()
		else:
			self.myScatterPlotWidget.hide()

	def updateStatusBar(self, text):
		#self.signalUpdateStatusBar.emit(text)
		self.statusBar.showMessage(text)
		self.statusBar.repaint()
		self.statusBar.update()

	def getSelectedRowDict(self):
		"""
		used by detection widget

		todo: problem is this dict has a mixture of float/int/str and hard to parse
		"""
		rowDict = None
		if self.selectedRow is not None:
			rowDict = self.myModel.myGetRowDict(self.selectedRow)
		return rowDict

	def errorTableClicked(self, index):
		row = index.row()
		column = index.column()

		self.myErrorTable.selectRow(row)

		doZoom = False
		modifiers = QtGui.QApplication.keyboardModifiers()
		if modifiers == QtCore.Qt.ShiftModifier:
			# zoomm on shift+click
			doZoom = True

		spikeNumber = self.dfError.loc[row, 'Spike']
		spikeNumber = int(spikeNumber)

		#self.signalSelectSpike.emit(spikeNumber)
		#print('errorTableClicked() spikeNumber:', spikeNumber, type(spikeNumber), 'modifiers:', modifiers)
		self.selectSpike(spikeNumber, doZoom=doZoom)

	def new_tableClicked(self, index):
		"""
		index is QtCore.QModelIndex
		"""
		#print('new_tableClicked() index:', 'row:', index.row(), 'column:', index.column())

		row = index.row()
		column = index.column()

		# select in table view (todo: switch to signal/slot)
		if self.selectedRow is not None and row==self.selectedRow:
			#print('  new_tableClicked() row', row, 'is already selected')
			return

		self.selectedRow = row
		self.tableView.selectRow(row)

		tableRowDict = self.myModel.myGetRowDict(row)

		abfColumnName = 'File'
		fileName = self.myModel.myGetValue(row, abfColumnName)
		if not isinstance(fileName, str):
			#print('  error: no "ABF File" specified')
			logger.warning('No file specified')
			return

		#if not fileName.endswith('.abf'):
		#	fileName += '.abf'

		path = os.path.join(self.path, fileName)
		switchedFile = self.myDetectionWidget.switchFile(path, tableRowDict)
		if not switchedFile:
			self.updateStatusBar(f'Failed to load file: "{path}"')

	def buildMenus(self):

		mainMenu = self.menuBar()

		loadFolderAction = QtWidgets.QAction('Load Folder ...', self)
		loadFolderAction.setShortcut('Ctrl+O')
		loadFolderAction.triggered.connect(self.loadFolder)

		saveDatabaseAction = QtWidgets.QAction('Save Database', self)
		saveDatabaseAction.setShortcut('Ctrl+S')
		saveDatabaseAction.triggered.connect(self.slotSaveFilesTable)

		buildDatabaseAction = QtWidgets.QAction('Build Big Database ...', self)
		buildDatabaseAction.triggered.connect(self.buildDatabase)

		savePreferencesAction = QtWidgets.QAction('Save Preferences', self)
		savePreferencesAction.triggered.connect(self.preferencesSave)

		showLogAction = QtWidgets.QAction('Show Log', self)
		showLogAction.triggered.connect(self.openLog)

		fileMenu = mainMenu.addMenu('&File')
		fileMenu.addAction(loadFolderAction)
		fileMenu.addSeparator()
		fileMenu.addAction(saveDatabaseAction)
		fileMenu.addSeparator()
		fileMenu.addAction(buildDatabaseAction)
		fileMenu.addSeparator()
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

		# view menu to toggle scatter plot widget
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

		# view menu to toggle scatter plot widget
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

	def buildUI(self, masterDf=None):
		self.toggleStyleSheet(buildingInterface=True)

		self.statusBar = QtWidgets.QStatusBar()
		#self.statusBar.showMessage.connect(self.signalUpdateStatusBar)
		self.setStatusBar(self.statusBar)

		self.centralwidget = QtWidgets.QWidget(self)
		self.centralwidget.setObjectName("centralwidget")

		self.myQVBoxLayout = QtWidgets.QVBoxLayout(self.centralwidget)
		self.myQVBoxLayout.setAlignment(QtCore.Qt.AlignTop)

		#
		# tree view of files
		if masterDf is not None:
			self.myModel = sanpy.interface.bFileTable.pandasModel(masterDf)

		#
		# table of files
		self.tableView = sanpy.interface.bFileTable.myTableView()
		self.tableView.signalDuplicateRow.connect(self.slotDuplicateRow)
		self.tableView.signalDeleteRow.connect(self.slotDeleteRow)
		self.tableView.signalCopyTable.connect(self.slotCopyTable)
		self.tableView.signalFindNewFiles.connect(self.slotFindNewFiles)
		self.tableView.signalSaveFileTable.connect(self.slotSaveFilesTable)
		self.tableView.mySetModel(self.myModel)
		self.tableView.clicked.connect(self.new_tableClicked)

		#self.myQVBoxLayout.addWidget(self.tableView)#, stretch=4)

		#
		# detect/plot widget, on the left are params and on the right are plots
		baNone = None
		self.myDetectionWidget = sanpy.interface.bDetectionWidget(baNone,self)
		self.signalSelectSpike.connect(self.myDetectionWidget.slotSelectSpike) # myDetectionWidget listens to self
		self.myDetectionWidget.signalSelectSpike.connect(self.slotSelectSpike) # self listens to myDetectionWidget
		#self.myQVBoxLayout.addWidget(self.myDetectionWidget)#, stretch=6)

		#
		# scatter plot
		self.myScatterPlotWidget = sanpy.interface.bScatterPlotWidget(self, self.myDetectionWidget)
		#self.myQVBoxLayout.addWidget(self.myScatterPlotWidget)
		self.signalSelectSpike.connect(self.myScatterPlotWidget.slotSelectSpike)
		if self.configDict['display']['showScatter']:
			pass
		else:
			self.myScatterPlotWidget.hide()

		#
		# error report
		#self.myErrorTable = QtWidgets.QTableView()
		self.myErrorTable = sanpy.interface.bErrorTable.errorTableView()
		self.myErrorTable.clicked.connect(self.errorTableClicked)
		self.myErrorTable.hide() # start hidden
		#self.myQVBoxLayout.addWidget(self.myErrorTable)

		#
		# use splitter, abb 20210521
		self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
		#self.main_splitter.setAlignment(QtCore.Qt.AlignTop) # trying to get vertical alignment to be tighter
		self.main_splitter.addWidget(self.tableView)
		self.main_splitter.addWidget(self.myDetectionWidget)
		self.main_splitter.addWidget(self.myScatterPlotWidget)
		self.main_splitter.addWidget(self.myErrorTable)
		self.myQVBoxLayout.addWidget(self.main_splitter)

		#
		# leave here, critical
		self.setCentralWidget(self.centralwidget)

	def preferencesLoad(self):
		if getattr(sys, 'frozen', False):
			# we are running in a bundle (frozen)
			bundle_dir = sys._MEIPASS
		else:
			# we are running in a normal Python environment
			bundle_dir = os.path.dirname(os.path.abspath(__file__))

		# load preferences
		self.optionsFile = os.path.join(bundle_dir, 'sanpy_app.json')

		if os.path.isfile(self.optionsFile):
			#print('  preferencesLoad() loading options file:', self.optionsFile)
			logger.info(f'Loading json options file: {self.optionsFile}')
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
		configDict['display']['showDvDt'] = True # not used?
		configDict['display']['showClips'] = False # not used?
		configDict['display']['showScatter'] = True # not used?

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

	def openScatterWindow(self):
		"""
		TODO: Make 2 versions of this
			one for a single cell df and
			second to load master csv across entire dataset
		"""
		print('MainWindow.openScatterWindow()')

		csvBase, csvExt = os.path.splitext(self.csvPath)
		masterCsvPath = csvBase + '_master.csv'

		if not os.path.isfile(masterCsvPath):
			print('error: openScatterWindow() did not find csvPath:', masterCsvPath)
			return

		from bAnalysisUtil import statList

		print('  loading', masterCsvPath)
		path = masterCsvPath
		analysisName = 'analysisname'
		statListDict = statList # maps human readable to comments
		categoricalList = ['include', 'Condition', 'Region', 'Sex', 'RegSex', 'File Number', 'analysisname']#, 'File Name']
		hueTypes = ['Region', 'Sex', 'RegSex', 'Condition', 'File Number', 'analysisname'] #, 'File Name'] #, 'None']
		sortOrder = ['Region', 'Sex', 'Condition']
		interfaceDefaults = {'Y Statistic': 'Spike Frequency (Hz)',
							'X Statistic': 'Region',
							'Hue': 'Region',
							'Group By': 'File Number'}
		#analysisName, masterDf = analysisName, df0 = ba.getReportDf(theMin, theMax, savefile)
		masterDf = self.dfReportForScatter
		self.scatterWindow = sanpy.scatterwidget.bScatterPlotMainWindow(
						path, categoricalList, hueTypes,
						analysisName, sortOrder, statListDict=statListDict,
						masterDf = masterDf,
						interfaceDefaults = interfaceDefaults)

		self.scatterWindow.signalSelectFromPlot.connect(self.slotSelectFromScatter)

	def slotSelectFromScatter(self, selectDict):
		print('MainWindow.slotSelectFromScatter()')
		print('  ', selectDict)

	def slotSelectSpike(self, spikeNumber, doZoom=False):
		self.selectSpike(spikeNumber, doZoom)

	def slotCopyTable(self):
		self.myModel.myCopyTable()

	def slotDeleteRow(self, rowIdx):
		# prompt user
		msg = QtWidgets.QMessageBox()
		msg.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
		msg.setIcon(QtWidgets.QMessageBox.Warning)
		msg.setText(f'Are you sure you want to delete row {rowIdx}?')
		#msg.setInformativeText('informative text xxx')
		msg.setWindowTitle("Delete Row")
		returnValue = msg.exec_()
		if returnValue == QtWidgets.QMessageBox.Ok:
			#print('  deleting row:', rowIdx)
			logger.info(f'Deleting file table row {rowIdx}')
			self.myModel.myDeleteRow(rowIdx)
			#df = self.myModel._data.drop([rowIdx])
			#df = df.reset_index(drop=True)
			#self.myModel._data = df # REQUIRED
			# todo: select row none
			self.selectedRow = None
			self.tableView.clearSelection()
		else:
			pass
			#print('  no action taken')

	def slotDuplicateRow(self, row):
		#print('MainWindow.slotDuplicateRow() row:', row, type(row))
		logger.info(f'Duplicating row {row}')
		self.myModel.myDuplicateRow(row)

	def slotFindNewFiles(self):
		"""
		find files in self.path that are not in pandas data model
		"""
		print('MainWindow.slotFindNewFiles()')
		# get all abf/csv/tif in folder
		abfList = []
		print('TODO: have slotFindNewFiles find (abf, csv, tif)')
		for file in os.listdir(self.path):
			if file.startswith('.'):
				continue
			if file.endswith('.abf'):
				#print('  ', file)
				abfList.append(file)

		# our curent database
		abfInDb = self.myModel.myGetColumnList('File')

		# files in database that are not in folder
		'''
		print('abfInDb:', abfInDb)
		for abf in abfInDb:
			if not isinstance(abf, str):
				continue
			abfPath = os.path.join(self.path, abf+'.abf')
			if not os.path.isfile(abfPath):
				print('  error: abf in database that is not in folder:', abfPath)
		'''

		# files in folder that are not in db
		for abf in abfList:
			#if not isinstance(abf, str):
			#	continue
			#abf = os.path.splitext(abf)[0] # remove .abf
			if not abf in abfInDb:
				print('  info: file in folder that is not in db:', abf)
				# add this abf file to main db

				# add an empty row
				self.myModel.myAppendRow()

				rowCount = self.myModel.rowCount()
				# this gives us the proper keys, iterate and fill in as necc.
				rowDict = self.myModel.myGetRowDict(rowCount-1)

				rowDict['Idx'] = ''
				rowDict['Include'] = 1
				rowDict['File'] = abf

				# TODO: load abf to get these
				# dur(s)
				# kHz
				# Mode

				rowDict['Cell Type'] = ''
				rowDict['Sex'] = ''
				rowDict['Condition'] = ''
				rowDict['dvdtThreshold'] = 20
				rowDict['mvThreshold'] = -20

				# TODO: insert in proper place, this is appending
				print('	 adding to db rowDict:', rowDict)
				self.myModel.mySetRow(rowCount-1, rowDict)
		#
		#print(self.myModel._data)

	def slotSaveFilesTable(self):
		#print('sanpy_app2.slotSaveFilesTable()')
		dbFile = 'sanpy_recording_db.csv'
		savePath = os.path.join(self.path, dbFile)
		logger.info(f'Saving folder csv as {savePath}')
		self.myModel.mySaveDb(savePath)

	def buildDatabase(self):
		"""
		prompt user for xls and build large per spike database
		"""
		print('== MainWindow.buildDatabase()')
		print('  TODO: FIX THIS -- returning')
		return

		dbFile = '/Users/cudmore/data/laura-ephys/sanap20210412/Superior vs Inferior database_13_Feb.xlsx'
		#dataPath = '/Users/cudmore/data/laura-ephys/sanap20210412'
		#outputFolder='new_20210129'
		outputFolder='new_20210425'
		fixedDvDt = None
		fixedVmThreshold = None
		noDvDtThreshold = False

		baList = sanpy.reanalyze(dbFile, outputFolder=outputFolder,
				fixedDvDt=fixedDvDt, noDvDtThreshold=noDvDtThreshold,
				fixedVmThreshold=fixedVmThreshold)

	def openLog(self):
		"""
		Open sanpy.log in default app
		"""
		logFilePath = sanpy.sanpyLogger.getLoggerFile()
		logFilePath = 'file://' + logFilePath
		url = QtCore.QUrl(logFilePath)
		QtGui.QDesktopServices.openUrl(url)

def main():
	logger.info(f'Python version is {platform.python_version()}')

	app = QtWidgets.QApplication(sys.argv)

	if getattr(sys, 'frozen', False):
		# we are running in a bundle (frozen)
		bundle_dir = sys._MEIPASS
	else:
		# we are running in a normal Python environment
		bundle_dir = os.path.dirname(os.path.abspath(__file__))

	#print(' pyinistaller bundle_dir:', bundle_dir)
	logger.info(f'bundle_dir is {bundle_dir}')

	appIconPath = os.path.join(bundle_dir, 'icons/sanpy_transparent.png')
	#print('  app icon is in', appIconPath)
	logger.info(f'appIconPath is {appIconPath}')
	if os.path.isfile(appIconPath):
		app.setWindowIcon(QtGui.QIcon(appIconPath))
	else:
		logger.error(f'Did not find appIconPath: {appIconPath}')

	# upgrading to mvc for file table (read from excel file)
	#w = MainWindow(path=path, app=app)
	csvPath = '/Users/cudmore/data/laura-ephys/sanap202101/Superior vs Inferior database.xlsx'
	csvPath = '/Users/cudmore/data/laura-ephys/sanap202101/Superior vs Inferior database_13_Feb.xlsx'

	# this is for manuscript
	csvPath = '/Users/cudmore/data/laura-ephys/sanap20210412/Superior vs Inferior database_13_Feb.xlsx'

	# use one dvdt to see if we get good APD20/50/80
	#csvPath = '/Users/cudmore/data/laura-ephys/sanap20210412/Superior vs Inferior database_Feb13_just_dvdt.xlsx'

	# now working on new version of sanpy
	csvPath = '/Users/cudmore/data/laura-ephys/sanap20210412/recording_db_20210427.csv'

	# trying to get sanpy to run with no foldeer, bbuild it as needed
	csvPath = None
	path = '/Users/cudmore/data/laura-ephys/test1_sanpy2'
	path = '/Users/cudmore/data/laura-ephys/sanap20210412'

	w = MainWindow(csvPath=csvPath)
	#w.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))

	w.show()

	#w.openLog()

	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
