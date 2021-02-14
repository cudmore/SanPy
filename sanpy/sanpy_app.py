# Author: Robert H Cudmore
# Date: 20190719

import os, sys, time, math, json
from functools import partial
from collections import OrderedDict

import qdarkstyle

import logging
from logging import FileHandler #RotatingFileHandler
from logging.config import dictConfig

# set up logging
logFormat = "[%(asctime)s] {%(filename)s %(funcName)s:%(lineno)d} %(levelname)s - %(message)s"
dictConfig({
	'version': 1,
	'formatters': {'default': {
		'format': logFormat,
	}},
})

myFormatter = logging.Formatter(logFormat)

# removed to use PyInstaller
'''
logFileName = 'sanpy.log'
logFileHandler = FileHandler(logFileName, mode='w')
logFileHandler.setLevel(logging.DEBUG)
logFileHandler.setFormatter(myFormatter)
'''

logger = logging.getLogger('sanpy')
#logger.addHandler(logFileHandler)

logger.setLevel(logging.INFO)
logger.debug('initialized sanpy log')

###
###
###

#print('The first time this is run, will take 40-60 seconds to start ... please wait ...')
print('SanPy is starting up ...')

import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui
#from pyqtspinner.spinner import WaitingSpinner

import sanpy

#from sanpy import bDetectionWidget
#from bScatterPlotWidget import bScatterPlotWidget
#import bFileList
#from bAnalysis import bAnalysis
#from bExportWidget import bExportWidget

# default theme
#pg.setConfigOption('background', 'w')
#pg.setConfigOption('foreground', 'k')
# dark theme
#pg.setConfigOption('background', 'k')
#pg.setConfigOption('foreground', 'w')

class MainWindow(QtWidgets.QMainWindow):
	signalUpdateStatusBar = QtCore.Signal(object)

	def __init__(self, path='', parent=None, app=None):
		"""
		path: full path to folder with abf files
		"""

		super(MainWindow, self).__init__(parent)

		myFontSize = 10
		myFont = self.font();
		myFont.setPointSize(myFontSize);
		self.setFont(myFont)

		self.myApp = app

		# todo: update this with selected folder
		if os.path.isdir(path):
			windowTitle = f'SanPy {path}'
		else:
			windowTitle = 'SanPy'
		self.setWindowTitle(windowTitle)

		self._rowHeight = 11

		self.path = path

		# todo: modify self.path if we get a good folder
		self.configDict = self.preferencesLoad()

		# I changed saved preferences file, try not to screw up Laura's analysis
		if 'useDarkStyle' in self.configDict.keys():
			self.useDarkStyle = self.configDict['useDarkStyle']
		else:
			print('  adding useDarkStyle to preferences')
			self.useDarkStyle = True
			self.configDict['useDarkStyle'] = True

		# set window geometry
		self.setMinimumSize(640, 480)

		self.left = self.configDict['windowGeometry']['x']
		self.top = self.configDict['windowGeometry']['y']
		self.width = self.configDict['windowGeometry']['width']
		self.height = self.configDict['windowGeometry']['height']

		self.setGeometry(self.left, self.top, self.width, self.height)

		#self.ba = None

		#tmpFile = '/Users/cudmore/Sites/bAnalysis/data/19114001.abf'
		#self._loadFile(tmpFile)

		lastPath = self.configDict['lastPath']
		if lastPath is not None and os.path.isdir(lastPath):
			print('sanpy_app using last path from preferences json file:', lastPath)
			self.path = lastPath
		else:
			print('sanpy_app last path is no good:', lastPath)
			self.path = None

		self.fileList = None

		# abb 20201109, added if clause
		if self.path is not None and len(self.path)>0:
			self.loadFolder(self.path)

		self.buildMenus()

		self.buildUI()

		self.myExportWidget = None

		self.updateStatusBar('SanPy started')

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

		self.preferencesSave()

		if buildingInterface:
			pass
		else:
			msg = QtWidgets.QMessageBox()
			msg.setIcon(QtWidgets.QMessageBox.Warning)
			msg.setText("Theme Changed")
			msg.setInformativeText('Please restart SanPy for changes to take effect.')
			msg.setWindowTitle("Theme Changed")
			retval = msg.exec_()

	# no idea why I need this ???
	def _tmp_loadFolder2(self, bool):
		loadedFolder = self.loadFolder()
		if loadedFolder:
			self.refreshFileTableWidget()
			self.preferencesSave()

	def loadFolder(self, path=''):
		print('MainWindow.loadFolder() path:', path)

		'''
		if len(path)==0:
			path = self.path
		'''

		if not os.path.isdir(path):
			path = str(QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory"))

		if len(path) == 0 :
			print('User did not select a folder')
			return False

		print('loadFolder() is loading folder path:', path)

		self.path = path

		self.fileList = sanpy.bFileList(path)

		#self.refreshFileTableWidget()

		windowTitle = f'SanPy {path}'
		self.setWindowTitle(windowTitle)

		return True

	'''
	def _loadFile(self, path, defaultAnalysis=True):
		"""
		path: full path to abf file
		"""

		if not os.path.isfile(path):
			return

		self.ba = sanpy.bAnalysis(file=path)
		if defaultAnalysis:
			self.ba.getDerivative(medianFilter=5) # derivative
			self.ba.spikeDetect(dVthresholdPos=50, minSpikeVm=-20, medianFilter=0)
	'''

	def mySignal(self, this, data=None):
		"""
		this: the signal
		data: depends on signal:
			signal=='set x axis': data=[min,max]
		"""
		#print('=== sanpy_app.mySignal() "' + this +'"')

		if this == 'set abfError':
			ba = self.myDetectionWidget.ba
			self.fileList.refreshRow(ba)

			# todo: make this more efficient, just update one row
			#self.refreshFileTableWidget()
			self.refreshFileTableWidget_Row()

		elif this == 'detect':
			# update scatter plot
			self.myScatterPlotWidget.plotToolbarWidget.on_scatter_toolbar_table_click()

		elif this == 'saved':
			# update file list object
			ba = self.myDetectionWidget.ba
			self.fileList.refreshRow(ba)

			# todo: make this more efficient, just update one row
			#self.refreshFileTableWidget()
			self.refreshFileTableWidget_Row()

		elif this == 'select spike':
			self.myDetectionWidget.selectSpike(data)
			self.myScatterPlotWidget.selectSpike(data)

		elif this == 'set x axis':
			self.myScatterPlotWidget.selectXRange(data[0], data[1])

		elif this == 'set full x axis':
			self.myScatterPlotWidget.selectXRange(None, None)

		elif this == 'cancel all selections':
			self.myDetectionWidget.selectSpike(None)
			self.myScatterPlotWidget.selectSpike(None)
			self.myScatterPlotWidget.selectXRange(None, None)

		else:
			print('MainWindow.mySignal() did not understand this:', this)

	def file_table_get_value(self, thisRow, thisColumnName):
		"""
		get the value of a column columnName at a selected row
		"""
		theValue = ''

		numCol = self.myTableWidget.columnCount()
		for j in range(numCol):
			headerText = self.myTableWidget.horizontalHeaderItem(j).text()
			if headerText == thisColumnName:
				theValue = self.myTableWidget.item(thisRow,j).text()
				break
		if len(theValue) > 0:
			return theValue
		else:
			print('error: file_table_get_value() did not find', thisRow, thisColumnName)
			return None

	def on_file_table_click(self):
		row = self.myTableWidget.currentRow()

		findThisColumn = 'File'
		fileName = ''

		# todo: replace this with file_table_get_value()
		numCol = self.myTableWidget.columnCount()
		for j in range(numCol):
			headerText = self.myTableWidget.horizontalHeaderItem(j).text()
			if headerText == findThisColumn:
				tmpItem = self.myTableWidget.item(row,j)
				if tmpItem is not None:
					fileName = tmpItem.text()
				break

		if len(fileName) > 0:
			#spinner = WaitingSpinner(self.myTableWidget, True, True, QtCore.Qt.ApplicationModal)
			#spinner.start() # starts spinning

			path = os.path.join(self.path, fileName)
			print('=== sanpy.on_file_table_click() row:', row+1, 'path:', path)
			self.myDetectionWidget.switchFile(path)

			# we should be able to open one for each file?
			#if self.myExportWidget is not None:
			#	self.myExportWidget.setFile2(path, plotRaw=True)

			#spinner.stop() # starts spinning

		else:
			print('error: on_file_table_click() did not find File name at row:', row)

	def refreshFileTableWidget_Row(self):
		"""
		refresh the selected row
		"""
		selectedRow = self.myTableWidget.currentRow()
		selectedFile = self.file_table_get_value(selectedRow, 'File')

		# abb 202012
		# if abfError then set file name text to red
		abfError = self.fileList.getFileError(selectedFile)

		fileValues = self.fileList.getFileValues(selectedFile) # get list of values in correct column order
		for colIdx, fileValue in enumerate(fileValues):
			if str(fileValue) == 'None':
				fileValue = ''
			item = QtWidgets.QTableWidgetItem(str(fileValue))
			if colIdx==0 and abfError:
				item.setForeground(QtGui.QBrush(QtGui.QColor("#DD4444")))
			self.myTableWidget.setItem(selectedRow, colIdx, item)
			self.myTableWidget.setRowHeight(selectedRow, self._rowHeight)

	def refreshFileTableWidget(self):
		#print('refreshFileTableWidget()')

		if self.fileList is None:
			print('refreshFileTableWidget() did not find a file list')
			return

		#self.myTableWidget.setShowGrid(False) # remove grid
		#self.myTableWidget.setFont(QtGui.QFont('Arial', 13))

		#
		# this will not change for a given path ???
		numRows = self.fileList.numFiles()
		numCols = len(self.fileList.getColumns())
		self.myTableWidget.setRowCount(numRows+1) # trying to get last row visible
		self.myTableWidget.setColumnCount(numCols)

		headerLabels = self.fileList.getColumns()
		self.myTableWidget.setHorizontalHeaderLabels(headerLabels)

		header = self.myTableWidget.horizontalHeader()
		header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
		header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
		header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)

		#
		# update to reflect analysis date/time etc
		fileList = self.fileList.getList() #ordered dict of files

		#for idx, filename in enumerate(fileList.keys()):
		for idx, filename in enumerate(sorted(fileList)):
			abfError = self.fileList.getFileError(filename) # abb 202012
			fileValues = self.fileList.getFileValues(filename) # get list of values in correct column order
			#print('refreshFileTableWidget()', idx+1, filename, fileValues)
			for idx2, fileValue in enumerate(fileValues):
				if str(fileValue) == 'None':
					fileValue = ''
				item = QtWidgets.QTableWidgetItem(str(fileValue))
				if idx2==0 and abfError:
					item.setForeground(QtGui.QBrush(QtGui.QColor("#DD4444")))
				self.myTableWidget.setItem(idx, idx2, item)
				self.myTableWidget.setRowHeight(idx, self._rowHeight)

	def old_export_pdf(self):
		"""
		Open a new window with raw Vm and provide interface to save as pdf
		"""
		if self.myDetectionWidget.ba is not None:
			#self.myExportWidget = sanpy.bExportWidget(self.myDetectionWidget.ba.file)
			sweepX = self.myDetectionWidget.ba.abf.sweepX
			sweepY = self.myDetectionWidget.ba.abf.sweepY
			xyUnits = ('Time (sec)', 'Vm (mV)')
			self.myExportWidget = sanpy.bExportWidget(sweepX, sweepY,
								path=self.myDetectionWidget.ba.file,
								xyUnits=xyUnits,
								darkTheme=self.useDarkStyle)
		else:
			print('please select an abf file')

	def scatterPlot(self):
		"""
		open a new window with an x/y scatter plot
		"""
		print('=== scatterPlot() IS NOT IMPLEMENTED !!!')

	'''
	def closeApplication(self):
		sys.exit()
	'''

	def keyPressEvent(self, event):
		#print('=== sanpy_app.MainWindow() keyPressEvent()')
		key = event.key()
		#print(key)
		if key in [70, 82]: # 'r' or 'f'
			self.myDetectionWidget.setFullAxis()

		'''
		if key in [QtCore.Qt.Key.Key_P]: # 'r' or 'f'
			self.myDetectionWidget.myPrint()
		'''

		# todo make this a self.mySignal
		if key == QtCore.Qt.Key.Key_Escape:
			self.mySignal('cancel all selections')

	def buildMenus(self):

		mainMenu = self.menuBar()

		loadFolderAction = QtWidgets.QAction('Load Folder ...', self)
		loadFolderAction.setShortcut('Ctrl+O')
		loadFolderAction.triggered.connect(self._tmp_loadFolder2)

		savePreferencesAction = QtWidgets.QAction('Save Preferences', self)
		savePreferencesAction.triggered.connect(self.preferencesSave)

		fileMenu = mainMenu.addMenu('&File')
		fileMenu.addAction(loadFolderAction)
		fileMenu.addSeparator()
		fileMenu.addAction(savePreferencesAction)

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
		#mainWindowAction.triggered.connect(self.toggleStyleSheet)
		mainWindowAction.setCheckable(True)
		mainWindowAction.setChecked(True)
		windowsMenu.addAction(mainWindowAction)

	def toggleStatisticsPlot(self, state):
		"""
		toggle scatter plot on/off
		"""
		print('toggleStatisticsPlot() state:', state)
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
		self.myApp.processEvents()

	def buildUI(self):
		# all widgets should inherit this

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
		#
		self.myTableWidget = QtWidgets.QTableWidget()
		self.myTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
		self.myTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.myTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		self.myTableWidget.cellClicked.connect(self.on_file_table_click)
		#self.setStyleSheet(myStyleSheet)

		# set font size of table (default seems to be 13 point)
		fnt = self.font()
		#print('  original table font size:', fnt.pointSize())
		fnt.setPointSize(self._rowHeight)
		self.myTableWidget.setFont(fnt)

		self.refreshFileTableWidget()
		self.myQVBoxLayout.addWidget(self.myTableWidget)#, stretch=4)

		#
		# detect/plot widget, on the left are params and on the right are plots
		#
		baNone = None
		self.myDetectionWidget = sanpy.bDetectionWidget(baNone,self)
		self.myQVBoxLayout.addWidget(self.myDetectionWidget)#, stretch=6)


		#
		# scatter plot
		#
		self.myScatterPlotWidget = sanpy.bScatterPlotWidget(self, self.myDetectionWidget)
		self.myQVBoxLayout.addWidget(self.myScatterPlotWidget)
		if self.configDict['display']['showScatter']:
			pass
		else:
			self.myScatterPlotWidget.hide()
		#self.myScatterPlotWidget.hide()

		"""
		#
		# stat plot
		#
		#self.myHBoxLayout_statplot = QtWidgets.QHBoxLayout(self.centralwidget)
		self.myHBoxLayout_statplot = QtWidgets.QHBoxLayout()

		self.plotToolbarWidget = myStatPlotToolbarWidget(self)
		self.myHBoxLayout_statplot.addWidget(self.plotToolbarWidget, stretch=1) # stretch=10, not sure on the units???

		print('	buildUI() building matplotlib x/y plot')

		# was working???
		#static_canvas = backend_qt5agg.FigureCanvas(mpl.figure.Figure(figsize=(5, 3)))
		self.static_canvas = backend_qt5agg.FigureCanvas(mpl.figure.Figure())
		self._static_ax = self.static_canvas.figure.subplots()
		#self._static_ax.plot(xPlot, yPlot, ".")

		'''
		fig = mpl.figure.Figure()
		self._static_ax = fig.add_subplot(111)
		self.static_canvas = backend_qt5agg.FigureCanvas(fig)
		self._static_ax = self.static_canvas.figure.subplots()

		'''
		self.metaLine = None
		self.metaPlotStat('peakVal') # x='peakSec'

		# WORKS
		'''
		self.myCanvas = MyDynamicMplCanvas(self.centralwidget)
		self.myHBoxLayout_statplot.addWidget(self.myCanvas, stretch=9)
		'''

		# i want the mpl toolbar in the mpl canvas or sublot
		# this is adding mpl toolbar to main window -->> not what I want
		#self.addToolBar(backend_qt5agg.NavigationToolbar2QT(self.static_canvas, self))
		# this kinda works as wanted, toolbar is inside mpl plot but it is FUCKING UGLY !!!!
		self.mplToolbar = backend_qt5agg.NavigationToolbar2QT(self.static_canvas, self.static_canvas) # params are (canvas, parent)

		#self.mplToolbar = backend_qt5agg.NavigationToolbar2QT(self.myCanvas, self.myCanvas) # params are (canvas, parent)

		self.myHBoxLayout_statplot.addWidget(self.static_canvas, stretch=9) # stretch=10, not sure on the units???

		#self.myQVBoxLayout.addWidget(self.static_canvas)
		self.myQVBoxLayout.addLayout(self.myHBoxLayout_statplot)
		"""

		#
		# leave here, critical
		self.setCentralWidget(self.centralwidget)

		print('	sanpy.buildUI() done')

	#################################################################################
	# preferences
	#################################################################################
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
			print('  preferencesLoad() loading options file:', self.optionsFile)
			with open(self.optionsFile) as f:
				return json.load(f)
		else:
			print('	 preferencesLoad() using program provided default options')
			return self.preferencesDefaults()

	def preferencesDefaults(self):
		configDict = OrderedDict()

		configDict['useDarkStyle'] = True
		configDict['autoDetect'] = True # FALSE DOES NOT WORK!!!! auto detect on file selection and/or sweep selection
		configDict['lastPath'] = ''
		configDict['windowGeometry'] = {}
		configDict['windowGeometry']['x'] = 100
		configDict['windowGeometry']['y'] = 100
		configDict['windowGeometry']['width'] = 2000
		configDict['windowGeometry']['height'] = 1200

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
		print('=== SanPy_App.preferencesSave() file:', self.optionsFile)

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

def main():
	import platform
	print('Python version is:', platform.python_version())

	path = '/media/cudmore/data/SAN AP'
	path = '/Users/cudmore/data/laura-ephys/SAN AP'

	app = QtWidgets.QApplication([''])

	if getattr(sys, 'frozen', False):
		# we are running in a bundle (frozen)
		bundle_dir = sys._MEIPASS
	else:
		# we are running in a normal Python environment
		bundle_dir = os.path.dirname(os.path.abspath(__file__))

	appIconPath = os.path.join(bundle_dir, 'icons/sanpy_transparent.png')
	print('app icon is in', appIconPath)
	app.setWindowIcon(QtGui.QIcon(appIconPath))

	w = MainWindow(path=path, app=app)
	#w.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
	w.show()

	# abb 20201109, program is not quiting on error???
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
	'''
	print('in sanpy_app.py __main__')
	path = '/Users/cudmore/Sites/bAnalysis/data'
	path = '/media/cudmore/data/Laura-data/manuscript-data'
	path = '/media/cudmore/data/SAN AP'

	#import logging
	#import traceback

	app = QtWidgets.QApplication(sys.argv)
	#w = MainWindow(path=path)
	w = MainWindow(path='', parent=app)
	#w.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
	w.show()

	# abb 20201109, program is not quiting on error???
	sys.exit(app.exec_())
	'''
