from PyQt5 import QtCore, QtWidgets, QtGui

import numpy as np

from matplotlib.backends import backend_qt5agg
import matplotlib as mpl

#import random

from bAnalysisUtil import bAnalysisUtil

class bScatterPlotWidget(QtWidgets.QWidget):
	def __init__(self, mainWindow=None, detectionWidget=None, parent=None):
		super(bScatterPlotWidget, self).__init__(parent)
	
		self.myMainWindow = mainWindow
		self.myDetectionWidget = detectionWidget
		
		self.buildUI()

	def buildUI(self):
		self.myHBoxLayout_statplot = QtWidgets.QHBoxLayout(self)

		self.plotToolbarWidget = myStatPlotToolbarWidget(self)
		self.myHBoxLayout_statplot.addWidget(self.plotToolbarWidget, stretch=2) # stretch=10, not sure on the units???

		# works
		#static_canvas = backend_qt5agg.FigureCanvas(mpl.figure.Figure(figsize=(5, 3)))
		tmpFig = mpl.figure.Figure()
		#tmpFig.tight_layout(pad=0)
		self.static_canvas = backend_qt5agg.FigureCanvas(tmpFig)
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
		
		# works
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
		#self.myQVBoxLayout.addLayout(self.myHBoxLayout_statplot)

	def metaPlotStat(self, yStatHuman):
		print('bScatterPlotWidget.metaPlotStat() yStatHuman:', yStatHuman)
		# todo: we need to tweek xStat based on particular yStat
		
		
		if self.myDetectionWidget.ba is None:
			print('got empty ba ???')
			return
		
		# works
		'''
		self.myCanvas.update_figure()
		return
		'''
		
		# todo
		# for now, always plot versus take off potential
		'''
		convertPntToSec = False
		if yStat == 'peakVal':
			xStat = 'peakSec'
		elif yStat == 'thresholdVal':
			xStat = 'thresholdPnt'
			convertPntToSec = True
		elif yStat == 'preMinVal':
			xStat = 'preMinPnt'
			convertPntToSec = True
		'''
		
		# convert human readable yStat to backend
		statList = bAnalysisUtil.getStatList()
		yStat = statList[yStatHuman]['yStat'] # the name of the backend stat
		
		# todo for now always plot versus take off potential
		xStatLabel = 'Seconds'
		xStat = 'thresholdSec'
		
		print('    xStat:', xStat, 'yStat:', yStat)
		
		xPlot, yPlot = self.myDetectionWidget.ba.getStat(xStat, yStat)
		if len(xPlot)==0 or len(yPlot)==0:
			print('    got empty stat?')
			return
		
		#if convertPntToSec:
			xPlot = [self.myDetectionWidget.ba.pnt2Sec_(x) for x in xPlot]
		#
			
		if self.metaLine is None:
			self.metaLine, = self._static_ax.plot(xPlot, yPlot, ".")
		else:
			print('	metaPlotStat() set ydata/xdata')
			self._static_ax.cla()
			self.metaLine, = self._static_ax.plot(xPlot, yPlot, ".")
			#self.metaLine.set_ydata(yPlot)
			#self.metaLine.set_xdata(xPlot)
			
		#print('	len xPlot:', len(xPlot), 'len yplot:', len(yPlot))
		
		# xmin/xmax will always be time of recording in seconds
		xMin = 0
		xMax = self.myDetectionWidget.ba.abf.sweepX[-1]
		#xMin = np.nanmin(xPlot)
		#xMax = np.nanmax(xPlot)
		yMin = np.nanmin(yPlot)
		yMax = np.nanmax(yPlot)
		
		# expand by 5%
		ySpan = abs(yMax - yMin)
		percentSpan = ySpan * 0.05
		yMin -= percentSpan
		yMax += percentSpan
		
		self._static_ax.set_xlim([xMin, xMax])
		self._static_ax.set_ylim([yMin, yMax])

		self._static_ax.set_xlabel(xStatLabel)
		self._static_ax.set_ylabel(yStatHuman)
		
		#self._static_ax.draw()
		self.static_canvas.draw()
		#self.static_canvas.flush_events()
		self.repaint() # this is updating the widget !!!!!!!!
	
#class MyMplCanvas(backend_qt5agg.FigureCanvas):
class MyMplCanvas(backend_qt5agg.FigureCanvasQTAgg):
	"""Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
	def __init__(self, parent=None):
		#fig = mpl.figure.Figure()
		fig = Figure()
		self.axes = fig.add_subplot(111)
		
		self.compute_initial_figure()
		
		#backend_qt5agg.FigureCanvas.__init__(self, fig)
		backend_qt5agg.FigureCanvasQTAgg.__init__(self, fig)
		self.setParent(parent)

		backend_qt5agg.FigureCanvasQTAgg.setSizePolicy(self,
				QtWidgets.QSizePolicy.Expanding,
				QtWidgets.QSizePolicy.Expanding)
		backend_qt5agg.FigureCanvasQTAgg.updateGeometry(self)
		
	def compute_initial_figure(self):
		pass

	'''
	def paintEvent(self, e):
		print('+++++++++++++++ paint ++++++++++++++++')
		#self.draw()
	'''
	
class MyDynamicMplCanvas(MyMplCanvas):
	"""A canvas that updates itself every second with a new plot."""
	def __init__(self, *args, **kwargs):
		MyMplCanvas.__init__(self, *args, **kwargs)
		'''
		timer = QtCore.QTimer(self)
		timer.timeout.connect(self.update_figure)
		timer.start(1000)
		'''
		
	def compute_initial_figure(self):
		self.axes.plot([0, 1, 2, 3], [1, 2, 0, 4], 'r')

	def update_figure(self):
		print('MyDynamicMplCanvas.update_figure()')
		# Build a list of 4 random integers between 0 and 10 (both inclusive)
		l = [random.randint(0, 10) for i in range(4)]
		print('    l:', l)
		#self.axes.cla()
		self.axes.clear()
		self.axes.plot([0, 1, 2, 3], l, 'r')
		print('       calling draw')

		self.draw() # update the canvas
		#self.flush_events()
		#self.update() # this is updating the widget !!!!!!!!
		self.repaint() # this is updating the widget !!!!!!!!
		
		#self.processEvents()
		#QtCore.QCoreApplication.processEvents()
		
#class myStatPlotToolbarWidget(QtWidgets.QToolBar):
class myStatPlotToolbarWidget(QtWidgets.QWidget):
	def __init__(self, myParent, parent=None):
		super(myStatPlotToolbarWidget, self).__init__(parent)

		self.myParent = myParent
		
		self.myQVBoxLayout = QtWidgets.QVBoxLayout(self)

		#self.statList = ['peakVal', 'thresholdVal', 'preMinVal']
		# stat list is a dictionary where each key is a stat
		self.statList = bAnalysisUtil.getStatList()

		self.myTableWidget = QtWidgets.QTableWidget()
		self.myTableWidget.setRowCount(len(self.statList))
		self.myTableWidget.setColumnCount(1)
		self.myTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
		self.myTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.myTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		self.myTableWidget.cellClicked.connect(self.on_scatter_toolbar_table_click)

		headerLabels = ['Y-Stat']
		self.myTableWidget.setHorizontalHeaderLabels(headerLabels)

		header = self.myTableWidget.horizontalHeader()       
		header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
		# QHeaderView will automatically resize the section to fill the available space. The size cannot be changed by the user or programmatically.
		header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

		for idx, stat in enumerate(self.statList):
			item = QtWidgets.QTableWidgetItem(stat)
			self.myTableWidget.setItem(idx, 0, item)
		#self.addWidget(self.myTableWidget)

		self.myQVBoxLayout.addWidget(self.myTableWidget)
		
	'''
	def getSelectedStat(self):
		row = self.myTableWidget.currentRow()
		yStat = self.myTableWidget.item(row,0).text() #
	'''
	
	@QtCore.pyqtSlot()
	def on_scatter_toolbar_table_click(self):
		print('*** on table click ***')
		row = self.myTableWidget.currentRow()
		if row == -1 or row is None:
			return
		yStat = self.myTableWidget.item(row,0).text() #
		print('=== on_scatter_toolbar_table_click', row, yStat)
		self.myParent.metaPlotStat(yStat)
		
	@QtCore.pyqtSlot()
	def on_button_click(self, name):
		print('=== myStatPlotToolbarWidget.on_button_click() name:', name)
