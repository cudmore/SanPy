import os, sys, time, math
#from collections import OrderedDict
from functools import partial

import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

'''
	from matplotlib.backends.backend_qt5agg import (
		FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
'''
from matplotlib.backends import backend_qt5agg

import matplotlib as mpl
#from matplotlib.figure import Figure

from bDetectionWidget import bDetectionWidget

from .. import bFileList

###
from ..bAnalysis import bAnalysis
#import pyabf # see: https://github.com/swharden/pyABF

now = time.time()

abfFile = '/Users/cudmore/Sites/bAnalysis/data/19221021.abf'
abfFile = '/Users/cudmore/Sites/bAnalysis/data/19114001.abf'
#myabf = pyabf.ABF(abfFile)
ba = bAnalysis(file=abfFile)

ba.getDerivative(medianFilter=5) # derivative
ba.spikeDetect(dVthresholdPos=50, minSpikeVm=-20, medianFilter=0)

#print('ba.spikeDict:', ba.spikeDict)

print ("abf load/anaysis time:", time.time()-now, "sec")
###

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

class MainWindow(QtWidgets.QMainWindow):
	def __init__(self, path='', parent=None):
		"""
		path: full path to folder with abf files
		"""
		
		super(MainWindow, self).__init__(parent)

		self.path = path
		
		self.title = 'SanPy'
		self.left = 20
		self.top = 10
		self.width = 2*1024 #640
		self.height = 1*768 #480

		self.setMinimumSize(640, 480)
		self.setWindowTitle(self.title)
		self.setGeometry(self.left, self.top, self.width, self.height)

		self.buildUI()

		self.loadFolder()
		
	def loadFolder(self, path=''):
		print('MainWindow.loadFolder() path:', path)
		if len(path)==0:
			path = self.path
		
		if not os.path.isdir(path):
			path = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
			
		self.fileList = bFileList.bFileList(path)

	def on_table_click(self):
		print('on_table_click', self.myTableWidget.currentRow())
	
	def buildUI(self):
		self.centralwidget = QtWidgets.QWidget(self)
		self.centralwidget.setObjectName("centralwidget")

		self.myQVBoxLayout = QtWidgets.QVBoxLayout(self.centralwidget)

		#
		# toolbar
		'''
		print('buildUI() building toobar')
		self.toolbarWidget = myToolbarWidget()
		self.addToolBar(QtCore.Qt.LeftToolBarArea, self.toolbarWidget)
		'''
		
		#
		# tree view of files
		print('buildUI() building file tree')
		#self.myTableWidget = QtWidgets.QTreeWidget()
		self.myTableWidget = QtWidgets.QTableWidget()
		self.myTableWidget.setRowCount(10)
		self.myTableWidget.setColumnCount(10)
		self.myTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
		self.myTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.myTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		self.myTableWidget.cellClicked.connect(self.on_table_click)
		headerLabels = ['a ' + str(x) for x in range(10)]
		self.myTableWidget.setHorizontalHeaderLabels(headerLabels)
		for i in range(10):
			for j in range(10):
				item = QtWidgets.QTableWidgetItem('aaaaaaaaaaaaaaaaa ' + str(i*j))
				self.myTableWidget.setItem(i,j, item)
		
		# append to layout
		self.myQVBoxLayout.addWidget(self.myTableWidget)

		#
		#
		# detect/plot widget
		#
		#
		
		self.myDetectionWidget = bDetectionWidget(ba)
		
		# add the detection widget to the main vertical layout
		self.myQVBoxLayout.addWidget(self.myDetectionWidget)

		
		#
		#
		# stat plot
		#
		#
		#self.myHBoxLayout_statplot = QtWidgets.QHBoxLayout(self.centralwidget)
		self.myHBoxLayout_statplot = QtWidgets.QHBoxLayout()

		plotToolbarWidget = myStatPlotToolbarWidget()
		self.myHBoxLayout_statplot.addWidget(plotToolbarWidget)#, stretch=2) # stretch=10, not sure on the units???

		print('buildUI() building matplotlib x/y plot')
		#static_canvas = backend_qt5agg.FigureCanvas(mpl.figure.Figure(figsize=(5, 3)))
		static_canvas = backend_qt5agg.FigureCanvas(mpl.figure.Figure())

		self._static_ax = static_canvas.figure.subplots()
		xPlot, yPlot = ba.getStat('peakSec', 'peakVal')
		self._static_ax.plot(xPlot, yPlot, ".")

		# i want the mpl toolbar in the mpl canvas or sublot
		# this is adding mpl toolbar to main window -->> not what I want
		#self.addToolBar(backend_qt5agg.NavigationToolbar2QT(static_canvas, self))
		# this kinda works as wanted, toolbar is inside mpl plot but it is FUCKING UGLY !!!!
		self.mplToolbar = backend_qt5agg.NavigationToolbar2QT(static_canvas, static_canvas) # params are (canvas, parent)

		self.myHBoxLayout_statplot.addWidget(static_canvas) #, stretch=8) # stretch=10, not sure on the units???

		#self.myQVBoxLayout.addWidget(static_canvas)
		self.myQVBoxLayout.addLayout(self.myHBoxLayout_statplot)


		#
		# leave here, critical
		self.setCentralWidget(self.centralwidget)

		print('buildUI() done')

#class myStatPlotToolbarWidget(QtWidgets.QToolBar):
class myStatPlotToolbarWidget(QtWidgets.QWidget):
	def __init__(self, parent=None):
		super(myStatPlotToolbarWidget, self).__init__(parent)

		'''
		buttonName = 'Plot'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Detect Spikes')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		self.addWidget(button)
		'''
		
		self.myTableWidget = QtWidgets.QTableWidget(self)
		self.myTableWidget.setRowCount(10)
		self.myTableWidget.setColumnCount(1)
		self.myTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
		self.myTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.myTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		self.myTableWidget.cellClicked.connect(self.on_table_click)
		headerLabels = ['Y']
		self.myTableWidget.setHorizontalHeaderLabels(headerLabels)
		for i in range(10):
			item = QtWidgets.QTableWidgetItem('s  ' + str(i))
			self.myTableWidget.setItem(i,0, item)
		#self.addWidget(self.myTableWidget)

	def on_table_click(self):
		print('on_table_click', self.myTableWidget.currentRow())
	
	@QtCore.pyqtSlot()
	def on_button_click(self, name):
		print('=== myStatPlotToolbarWidget.on_button_click() name:', name)

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
