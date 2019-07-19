import os, sys, time, math, json
from functools import partial
from collections import OrderedDict

import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

from bDetectionWidget import bDetectionWidget
from bScatterPlotWidget import bScatterPlotWidget
import bFileList
from bAnalysis import bAnalysis

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

class MainWindow(QtWidgets.QMainWindow):
	def __init__(self, path='', parent=None):
		"""
		path: full path to folder with abf files
		"""
		
		super(MainWindow, self).__init__(parent)

		self.setWindowTitle('SanPy')

		self.path = path
		
		# todo: modify self.path if we get a good folder
		self.configDict = self.preferencesLoad()
		
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
		if os.path.isdir(lastPath):
			print('using last path from preferences json file:', lastPath)
			self.path = lastPath
		else:
			print('last path is no good', lastPath)
			
		self.fileList = None
		self.loadFolder(self.path)

		self.buildMenus()
		
		self.buildUI()
		
	# no idea why I need this ???
	def _tmp_loadFolder2(self, bool):
		loadedFolder = self.loadFolder()
		if loadedFolder:
			self.refreshFileTableWidget()
		
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
		
		self.fileList = bFileList.bFileList(path)

		#self.refreshFileTableWidget()
		
		return True
		
	'''
	def _loadFile(self, path, defaultAnalysis=True):
		"""
		path: full path to abf file
		"""
	
		if not os.path.isfile(path):
			return
		
		self.ba = bAnalysis(file=path)
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
		print('=== mySignal() "' + this +'"')

		if this == 'detect':
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
				fileName = self.myTableWidget.item(row,j).text()
				break
				
		if len(fileName) > 0:
			path = os.path.join(self.path, fileName)
			print('=== on_file_table_click row:', row, 'path:', path)
			self.myDetectionWidget.switchFile(path)
		else:
			print('error: on_file_table_click() did not find File name at row:', row)
			
	def refreshFileTableWidget_Row(self):
		"""
		refresh the selected row
		"""
		selectedRow = self.myTableWidget.currentRow()
		selectedFile = self.file_table_get_value(selectedRow, 'File')

		fileValues = self.fileList.getFileValues(selectedFile) # get list of values in correct column order
		for colIdx, fileValue in enumerate(fileValues):
			if str(fileValue) == 'None':
				fileValue = ''
			item = QtWidgets.QTableWidgetItem(str(fileValue))
			self.myTableWidget.setItem(selectedRow, colIdx, item)
		
	def refreshFileTableWidget(self):
		print('refreshFileTableWidget()')
		
		if self.fileList is None:
			print('refreshFileTableWidget() did not find a file list')
			return
				
		#self.myTableWidget.setShowGrid(False) # remove grid
		self.myTableWidget.setFont(QtGui.QFont('Arial', 13))
		
		#
		# this will not change for a given path ???
		numRows = self.fileList.numFiles()
		numCols = len(self.fileList.getColumns())
		self.myTableWidget.setRowCount(numRows)
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

		for idx, filename in enumerate(fileList.keys()):
			#print(idx, filename)
			fileValues = self.fileList.getFileValues(filename) # get list of values in correct column order
			for idx2, fileValue in enumerate(fileValues):
				if str(fileValue) == 'None':
					fileValue = ''
				item = QtWidgets.QTableWidgetItem(str(fileValue))
				self.myTableWidget.setItem(idx, idx2, item)
			
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

		scatterPlotAction = QtWidgets.QAction('Scatter Plot', self)        
		scatterPlotAction.triggered.connect(self.scatterPlot)

		windowsMenu = mainMenu.addMenu('&Windows')
		windowsMenu.addAction(scatterPlotAction)

	def scatterPlot(self):
		"""
		open a new window with an x/y scatter plot
		"""
		print('=== scatterPlot()')
		
	'''
	def closeApplication(self):
		sys.exit()
	'''
		
	def keyPressEvent(self, event):
		print('=== keyPressEvent()')
		key = event.key()
		print(key)
		if key in [70, 82]: # 'r' or 'f'
			self.myDetectionWidget.setFullAxis()
			
		if key in [QtCore.Qt.Key.Key_P]: # 'r' or 'f'
			self.myDetectionWidget.myPrint()

		# todo make this a self.mySignal
		if key == QtCore.Qt.Key.Key_Escape:
			self.mySignal('cancel all selections')
		
	def buildUI(self):
		self.centralwidget = QtWidgets.QWidget(self)
		self.centralwidget.setObjectName("centralwidget")

		self.myQVBoxLayout = QtWidgets.QVBoxLayout(self.centralwidget)

		#
		# tree view of files
		#
		
		print('	buildUI() building file table')
		self.myTableWidget = QtWidgets.QTableWidget()
		self.myTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
		self.myTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.myTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		self.myTableWidget.cellClicked.connect(self.on_file_table_click)

		self.refreshFileTableWidget()
					
		# append to layout
		self.myQVBoxLayout.addWidget(self.myTableWidget)

		#
		# detect/plot widget
		#
		baNone = None
		self.myDetectionWidget = bDetectionWidget(baNone,self)
		#self.myDetectionWidget = bDetectionWidget(self.ba)
		
		# add the detection widget to the main vertical layout
		self.myQVBoxLayout.addWidget(self.myDetectionWidget)

		
		#
		# scatter plot
		#
		self.myScatterPlotWidget = bScatterPlotWidget(self, self.myDetectionWidget)
		self.myQVBoxLayout.addWidget(self.myScatterPlotWidget)
		
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
			print('	preferencesLoad() loading options file:', self.optionsFile)
			with open(self.optionsFile) as f:
				return json.load(f)
		else:
			print('	preferencesLoad() using program provided default options')
			return self.preferencesDefaults()

	def preferencesDefaults(self):
		configDict = OrderedDict()

		configDict['autoDetect'] = True # FALSE DOES NOT WORK!!!! auto detect on file selection and/or sweep selection
		configDict['lastPath'] = 'data'
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

		configDict['display'] = {}
		configDict['display']['plotEveryPoint'] = 10

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

if __name__ == '__main__':
	path = '/Users/cudmore/Sites/bAnalysis/data'
	
	import logging
	import traceback

	try:
		app = QtWidgets.QApplication(sys.argv)
		w = MainWindow(path=path)
		#w.resize(640, 480)
		w.show()
		#sys.exit(app.exec_())
	except Exception as e:
		print('fastplot3 error')
		print(traceback.format_exc())
		#logging.error(traceback.format_exc())
		raise
	finally:
		sys.exit(app.exec_())
