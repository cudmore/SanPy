import os, sys, time, math
from functools import partial

import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

'''
from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
'''

from bDetectionWidget import bDetectionWidget
from bScatterPlotWidget import bScatterPlotWidget
import bFileList
from bAnalysis import bAnalysis

'''
###
now = time.time()

abfFile = '/Users/cudmore/Sites/bAnalysis/data/19221021.abf'
abfFile = '/Users/cudmore/Sites/bAnalysis/data/19114001.abf'
ba = bAnalysis(file=abfFile)

ba.getDerivative(medianFilter=5) # derivative
ba.spikeDetect(dVthresholdPos=50, minSpikeVm=-20, medianFilter=0)

print ("abf load/anaysis time:", time.time()-now, "sec")
###
'''

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

class MainWindow(QtWidgets.QMainWindow):
	def __init__(self, path='', parent=None):
		"""
		path: full path to folder with abf files
		"""
		
		super(MainWindow, self).__init__(parent)

		self.path = path # path to folder of abf files
		
		#self.ba = None
		
		tmpFile = '/Users/cudmore/Sites/bAnalysis/data/19114001.abf'
		#self._loadFile(tmpFile)
		
		self.title = 'SanPy'
		self.left = 20
		self.top = 10
		self.width = 2*1024 #640
		self.height = 1024 #1*768 #480

		self.setMinimumSize(640, 480)
		self.setWindowTitle(self.title)
		self.setGeometry(self.left, self.top, self.width, self.height)

		self.loadFolder(self.path)

		self.buildUI()
		
	def loadFolder(self, path=''):
		print('MainWindow.loadFolder() path:', path)
		if len(path)==0:
			path = self.path
		
		if not os.path.isdir(path):
			path = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
			
		self.fileList = bFileList.bFileList(path)

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
		
	def on_table_click(self):
		print('on_table_click', self.myTableWidget.currentRow())
		row = self.myTableWidget.currentRow()
		col = 1
		path = self.myTableWidget.item(row,col).text()
		print('	path:', path)
		self.myDetectionWidget.switchFile(path)
		
	def mySignal(self, this):
		print('=== mySignal() "' + this +'"')
		if this == 'detect':
			#
			# update file table
			#self.myTableWidget
			
			#
			# update scatter plot
			self.myScatterPlotWidget.plotToolbarWidget.on_table_click()
			
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
		self.myTableWidget.cellClicked.connect(self.on_table_click)

		fileList = self.fileList.getList()
		numRows = len(fileList)
		numCols = len(self.fileList.getColumns())
		self.myTableWidget.setRowCount(numRows)
		self.myTableWidget.setColumnCount(numCols)

		headerLabels = self.fileList.getColumns()
		self.myTableWidget.setHorizontalHeaderLabels(headerLabels)
		
		header = self.myTableWidget.horizontalHeader()       
		header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
		header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
		header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
		
		for idx, file in enumerate(fileList):
			print('file:', file)
			myTuple = file.asTuple()
			for idx2, j in enumerate(myTuple):
				item = QtWidgets.QTableWidgetItem(str(j))
				self.myTableWidget.setItem(idx, idx2, item)
			
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
