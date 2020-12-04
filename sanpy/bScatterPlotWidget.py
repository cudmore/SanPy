# Author: Robert H Cudmore
# Date: 20190719

import os, math

from PyQt5 import QtCore, QtWidgets, QtGui

import numpy as np

from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
import matplotlib.pyplot as plt # used to set global plot options in defaultPlotLayout()

#import qdarkstyle

from bAnalysisUtil import bAnalysisUtil

class bScatterPlotWidget(QtWidgets.QWidget):
	def __init__(self, mainWindow=None, detectionWidget=None, parent=None):
		super(bScatterPlotWidget, self).__init__(parent)

		self.myMainWindow = mainWindow
		self.myDetectionWidget = detectionWidget

		#self.colorTable = plt.cm.coolwarm
		self.colorTable = mpl.pyplot.cm.coolwarm

		#self.static_canvas = None # debug, adding defaultPlotLayout

		self.buildUI()

		# default stat
		# does not work
		#self.metaPlotStat('Spike Frequency (Hz)')

	def on_pick_event(self, event):
		print('=== bScatterWidget.on_pick_event() event:', event, 'event.ind:', event.ind)

		if len(event.ind) < 1:
			return
		spikeNumber = event.ind[0]

		# propagate a signal to parent
		self.myMainWindow.mySignal('select spike', data=spikeNumber)
		#self.selectSpike(spikeNumber)

	'''
	def on_button_press(self, event):
		print('=== bScatterWidget.on_button_press() event:', event, 'event:', event)
	'''

	def defaultPlotLayout(self, buildingInterface=False):

		# get the style from the main window
		plotForTalk = self.myMainWindow.useDarkStyle

		if plotForTalk:
			useThisStyleSheet = 'dark_background'
			print('bScatterPlotWidget.defaultPlotLayout() setting "dark_background"')
			plt.style.use('dark_background')
		else:
			useThisStyleSheet = 'seaborn'
			print('bScatterPlotWidget.defaultPlotLayout() setting "seaborn"')
			plt.style.use('seaborn')

		fontSize = 10
		#if plotForTalk:
		#	fontSize = 14

		mpl.rcParams['figure.figsize'] = [3.0, 4.0]
		mpl.rcParams['figure.constrained_layout.use'] = True # also applies to plt.subplots(1)
		mpl.rcParams['lines.linewidth'] = 3.0
		mpl.rcParams["lines.markersize"] = 7 # default: 6.0
		mpl.rcParams["lines.marker"] = 'o'
		mpl.rcParams['axes.spines.top'] = False
		mpl.rcParams['axes.spines.right'] = False
		mpl.rcParams['axes.xmargin'] = 0.3 # default: 0.05
		mpl.rcParams['axes.ymargin'] = 0.1 # default: 0.05
		mpl.rcParams['axes.labelsize'] = fontSize # font size of x/y axes labels (not ticks)
		mpl.rcParams['xtick.labelsize']=fontSize
		mpl.rcParams['ytick.labelsize']=fontSize

		if not buildingInterface:
			self.static_canvas.setStyleSheet(useThisStyleSheet)
			# does not work
			#self._static_ax.setStyleSheet(useThisStyleSheet)
			self.mplToolbar.setStyleSheet(useThisStyleSheet)

	def buildUI(self, doRebuild=False):
		if doRebuild:
			self.myHBoxLayout_statplot.removeWidget(self.static_canvas)

		self.defaultPlotLayout(buildingInterface=True) # sets matplotlib to dark theme
		#self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))

		self.myHBoxLayout_statplot = QtWidgets.QHBoxLayout(self) # if I remove self here, plot does not show up

		self.plotToolbarWidget = myStatPlotToolbarWidget(self)
		self.myHBoxLayout_statplot.addWidget(self.plotToolbarWidget, stretch=2) # stretch=10, not sure on the units???

		# works
		#static_canvas = backend_qt5agg.FigureCanvas(mpl.figure.Figure(figsize=(5, 3)))
		tmpFig = mpl.figure.Figure()
		#tmpFig.tight_layout(pad=0)
		self.static_canvas = backend_qt5agg.FigureCanvas(tmpFig)
		self._static_ax = self.static_canvas.figure.subplots()
		#self._static_ax.plot(xPlot, yPlot, ".")

		# pick_event assumes 'picker=5' in any .plot()
		self.cid = self.static_canvas.mpl_connect('pick_event', self.on_pick_event)

		'''
		fig = mpl.figure.Figure()
		self._static_ax = fig.add_subplot(111)
		self.static_canvas = backend_qt5agg.FigureCanvas(fig)
		self._static_ax = self.static_canvas.figure.subplots()
		'''

		self.lastSpikeNumber = None
		self.lastFileName = ''

		self.plotMeta_selection = None # selection of many spikes matching detection widget x-aixs

		# holds data of current x/y plot values (used to quickly select a range with xxx
		self.my_xPlot = None
		self.my_yPlot = None

		self.metaLine = None
		self.singleSpikeSelection = None
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

	def selectSpike(self, spikeNumber):
		""" Select a single spike in scatter plot """

		print('bSCatterPlotWidget.selectSpike() spikeNumber:', spikeNumber)

		if spikeNumber is None:
			self.lastSpikeNumber = None
			self.singleSpikeSelection.set_ydata([])
			self.singleSpikeSelection.set_xdata([])
		else:
			self.lastSpikeNumber = spikeNumber

			offsets = self.metaLine.get_offsets()
			xData = offsets[spikeNumber][0]
			yData = offsets[spikeNumber][1]
			print('   xData:', xData, 'yData:', yData)

			self.singleSpikeSelection.set_xdata(xData)
			self.singleSpikeSelection.set_ydata(yData)

		self.static_canvas.draw()
		self.repaint() # this is updating the widget !!!!!!!!

	def selectXRange(self, xMin, xMax):
		"""
		select all spikes in range
		"""

		print('bScatterPlotWidget.selectXRange() xMin:', xMin, 'xMax:', xMax)

		'''
		# clear existing
		if self.plotMeta_selection is not None:
			for line in self.plotMeta_selection:
				line.remove()

		self.plotMeta_selection = []
		'''

		if self.plotMeta_selection is None:
			return

		#if xMin is not None and xMax is not None:
		if xMin is None and xMax is None:
			self.plotMeta_selection.set_ydata([])
			self.plotMeta_selection.set_xdata([])
		else:
			xData = []
			yData = []
			for i, spikeTime in enumerate(self.myDetectionWidget.ba.spikeTimes):
				spikeSeconds = spikeTime / self.myDetectionWidget.ba.dataPointsPerMs / 1000 # pnts to seconds
				#print(spikeSeconds)
				if spikeSeconds >= xMin and spikeSeconds <= xMax:
					'''
					line, = self._static_ax.plot(self.my_xPlot[i], self.my_yPlot[i], 'oy', markersize=10)
					self.plotMeta_selection.append(line)
					'''
					xData.append(self.my_xPlot[i])
					yData.append(self.my_yPlot[i])
			self.plotMeta_selection.set_xdata(xData)
			self.plotMeta_selection.set_ydata(yData)

		self.static_canvas.draw()
		self.repaint() # this is updating the widget !!!!!!!!

	def metaPlotStat(self, yStatHuman):
		print('bScatterPlotWidget.metaPlotStat() yStatHuman:', yStatHuman)
		# todo: we need to tweek xStat based on particular yStat


		if self.myDetectionWidget.ba is None:
			print('bScatterPlotWidget.metaPlotStat() got empty ba ???')
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
		if len(self.lastFileName)==0 or (self.lastFileName != self.myDetectionWidget.ba.file):
			self.lastSpikeNumber = None
			self.lastFileName = self.myDetectionWidget.ba.file

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
		#	xPlot = [self.myDetectionWidget.ba.pnt2Sec_(x) for x in xPlot]
		#

		# todo add to constructor
		self.my_xPlot = xPlot
		self.my_yPlot = yPlot

		tmpColor = range(len(xPlot))
		if self.metaLine is None:
			#self.metaLine, = self._static_ax.plot(xPlot, yPlot, ".", picker=5)
			self.metaLine = self._static_ax.scatter(xPlot, yPlot, c=tmpColor, cmap=self.colorTable, picker=5)
		else:
			print('	metaPlotStat() set ydata/xdata')
			self._static_ax.cla()
			#self.metaLine, = self._static_ax.plot(xPlot, yPlot, ".")
			self.metaLine = self._static_ax.scatter(xPlot, yPlot, c=tmpColor, cmap=self.colorTable, picker=5)
			#self.metaLine.set_ydata(yPlot)
			#self.metaLine.set_xdata(xPlot)

		# todo keep track of multi spike selection so we do not loose it on switching stats
		self.plotMeta_selection, = self._static_ax.plot([], [], "oy", markersize=10)

		if 1: #or self.singleSpikeSelection is None:
			if self.lastSpikeNumber is None:
				self.singleSpikeSelection, = self._static_ax.plot([], [], "oc", markersize=10)
			else:
				self.singleSpikeSelection, = self._static_ax.plot(xPlot[self.lastSpikeNumber], yPlot[self.lastSpikeNumber], "oc", markersize=10)

		#print('	len xPlot:', len(xPlot), 'len yplot:', len(yPlot))

		# xmin/xmax will always be time of recording in seconds
		xMin = 0
		xMax = self.myDetectionWidget.ba.abf.sweepX[-1]
		self._static_ax.set_xlim([xMin, xMax])

		yMin = np.nanmin(yPlot)
		yMax = np.nanmax(yPlot)

		# expand by 5%
		ySpan = abs(yMax - yMin)
		percentSpan = ySpan * 0.05
		yMin -= percentSpan
		yMax += percentSpan

		#print('metaplotstat() ymin:', yMin, 'yMax:', yMax)

		if math.isnan(yMin) or math.isnan(xMin):
			pass
		else:
			self._static_ax.set_ylim([yMin, yMax])

		self._static_ax.set_xlabel(xStatLabel)
		self._static_ax.set_ylabel(yStatHuman)

		#self._static_ax.draw()
		self.static_canvas.draw()
		#self.static_canvas.flush_events()
		self.repaint() # this is updating the widget !!!!!!!!

# todo: not used
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

# todo: not used
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

		#self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))

		self.myParent = myParent

		self._rowHeight = 12

		self.myQVBoxLayout = QtWidgets.QVBoxLayout(self)

		#self.statList = ['peakVal', 'thresholdVal', 'preMinVal']
		# stat list is a dictionary where each key is a stat
		self.statList = bAnalysisUtil.getStatList()

		# load stye sheet
		'''
		myPath = os.path.dirname(os.path.abspath(__file__))
		mystylesheet_css = os.path.join(myPath, 'css', 'mystylesheet.css')
		if os.path.isfile(mystylesheet_css):
			with open(mystylesheet_css) as f:
				myStyleSheet = f.read()
			self.setStyleSheet(myStyleSheet)
		'''

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
			self.myTableWidget.setRowHeight(idx, self._rowHeight)
		#self.addWidget(self.myTableWidget)

		self.myQVBoxLayout.addWidget(self.myTableWidget)

		# select a default stat
		self.myTableWidget.selectRow(12) # hard coding 'Spike Frequency (Hz)'

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
