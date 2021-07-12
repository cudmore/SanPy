import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui

from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin

class plotScatter(sanpyPlugin):
	"""
	Plot x/y statiistics as a scatter

	Get stat names and variables from sanpy.bAnalysisUtil.getStatList()
	"""
	myHumanName = 'Scatter Plot'

	def __init__(self, **kwargs):
		"""
		Args:
			ba (bAnalysis): Not required
		"""
		super().__init__(**kwargs)

		self.plotChasePlot = False # i vs i-1
		self.plotColorTime = True
		# keep track of what we are plotting, use this in replot()
		self.xStatName = None
		self.yStatName = None

		# makes self.mainWidget and calls show()
		self.pyqtWindow()

		# main layout
		hLayout = QtWidgets.QHBoxLayout()
		hSplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
		hLayout.addWidget(hSplitter)

		# coontrols and 2x stat list
		vLayout = QtWidgets.QVBoxLayout()

		#
		# controls
		controlWidget = QtWidgets.QWidget()

		hLayout2 = QtWidgets.QHBoxLayout()

		#
		self.b2 = QtWidgets.QCheckBox("Chase Plot")
		self.b2.setChecked(self.plotChasePlot)
		self.b2.stateChanged.connect(lambda:self.btnstate(self.b2))
		hLayout2.addWidget(self.b2)

		#
		self.colorTime = QtWidgets.QCheckBox("Color Time")
		self.colorTime.setChecked(self.plotColorTime)
		self.colorTime.stateChanged.connect(lambda:self.btnstate(self.colorTime))
		hLayout2.addWidget(self.colorTime)

		vLayout.addLayout(hLayout2)

		# x and y stat lists
		hLayout3 = QtWidgets.QHBoxLayout()
		self.xPlotWidget = myStatListWidget(self, headerStr='X Stat')
		self.xPlotWidget.myTableWidget.selectRow(0)
		self.yPlotWidget = myStatListWidget(self, headerStr='Y Stat')
		self.yPlotWidget.myTableWidget.selectRow(1)
		hLayout3.addWidget(self.xPlotWidget)
		hLayout3.addWidget(self.yPlotWidget)
		vLayout.addLayout(hLayout3)

		controlWidget.setLayout(vLayout)

		#
		# create a mpl plot (self._static_ax, self.static_canvas)
		self.mplWindow2()

		# make initial empty scatter plot
		#self.lines, = self._static_ax.plot([], [], 'ow', picker=5)
		self.cmap = mpl.pyplot.cm.coolwarm
		self.cmap.set_under("white") # only works for dark theme
		self.lines = self._static_ax.scatter([], [], c=[], cmap=self.cmap, picker=5)

		# make initial empty spike selection plot
		self.linesSel, = self._static_ax.plot([], [], 'oy')

		# despine top/right
		self._static_ax.spines['right'].set_visible(False)
		self._static_ax.spines['top'].set_visible(False)

		#
		# finalize
		#hLayout.addLayout(vLayout)
		hSplitter.addWidget(controlWidget)
		hSplitter.addWidget(self.static_canvas) # add mpl canvas

		# set the layout of the main window
		self.mainWidget.setLayout(hLayout)

		self.replot()

	def btnstate(self, b):
		state = b.isChecked()
		#if b.text() == "Respond To Analysis Changes":
		#	self.setRespondToAnalysisChange(state)
		if b.text() == 'Chase Plot':
			self.plotChasePlot = state
			logger.info(f'plotChasePlot:{self.plotChasePlot}')
			self.replot()
		elif b.text() == 'Color Time':
			self.plotColorTime = state
			logger.info(f'plotColorTime:{self.plotColorTime}')
			self.replot()
		else:
			logger.warning(f'Did not respond to button "{b.text()}"')

	def replot(self):
		"""
		Replot when analysis changes or file changes
		"""
		xHumanStat, xStat = self.xPlotWidget.getCurrentStat()
		yHumanStat, yStat = self.yPlotWidget.getCurrentStat()

		logger.info(f'x:"{xHumanStat}" y:"{yHumanStat}"')

		self.xStatName = xStat
		self.yStatName = yStat

		if self.ba is None:
			xData = None
			yData = None
		else:
			xData = self.ba.getStat(xStat)
			yData = self.ba.getStat(yStat)

		# return if we got no data, happend when there is no analysis
		if xData is None or yData is None:
			logger.warning(f'Did not find either xStat: "{xStat}" or yStat: "{yStat}"')
			self.lines.set_offsets([np.nan, np.nan])
			self.static_canvas.draw()
			self.mainWidget.repaint() # update the widget
			return

		if self.plotChasePlot:
			#print('todo: tweek x/y to plot i (x) versus i-1 (y)')
			xData = xData[1:-1]
			yData = yData[0:-2]
			# on selection, ind will refer to y-axis spike

		# was used for plot(), not scatter()
		#self.lines.set_data(xData, yData)
		# data
		data = np.stack([xData, yData], axis=1)
		self.lines.set_offsets(data)
		# color
		if self.plotColorTime:
			tmpColor = np.array(range(len(xData)))
			self.lines.set_array(tmpColor)
			self.lines.set_cmap(self.cmap)  # mpl.pyplot.cm.coolwarm
		else:
			tmpColor = np.array(range(len(xData)))
			# assuming self.cmap.set_under("white")
			self.lines.set_array(np.ones_like(tmpColor)*np.nanmin(tmpColor)-1)

		xStatLabel = xHumanStat
		yStatLabel = yHumanStat
		if self.plotChasePlot:
			xStatLabel += ' [i]'
			yStatLabel += ' [i-1]'
		self._static_ax.set_xlabel(xStatLabel)
		self._static_ax.set_ylabel(yStatLabel)

		# cancel any selections
		self.linesSel.set_data([], [])

		xMin = np.nanmin(xData)
		xMax = np.nanmax(xData)
		yMin = np.nanmin(yData)
		yMax = np.nanmax(yData)
		# expand by 5%
		xSpan = abs(xMax - xMin)
		percentSpan = xSpan * 0.05
		xMin -= percentSpan
		xMax += percentSpan
		#
		ySpan = abs(yMax - yMin)
		percentSpan = ySpan * 0.05
		yMin -= percentSpan
		yMax += percentSpan
		#
		self._static_ax.set_xlim([xMin, xMax])
		self._static_ax.set_ylim([yMin, yMax])

		# this was for lines (not scatter)
		#self._static_ax.relim()
		#self._static_ax.autoscale_view(True,True,True)

		# redraw
		self.static_canvas.draw()
		self.mainWidget.repaint() # update the widget

	def selectSpike(self, sDict):
		"""
		Select a spike
		"""
		logger.info(sDict)

		spikeNumber = sDict['spikeNumber']

		if self.xStatName is None or self.yStatName is None:
			return

		if spikeNumber is not None and spikeNumber >= 0:
			xData = self.ba.getStat(self.xStatName)
			xData = [xData[spikeNumber]]

			yData = self.ba.getStat(self.yStatName)
			yData = [yData[spikeNumber]]
		else:
			xData = []
			yData = []

		self.linesSel.set_data(xData, yData)

		self.static_canvas.draw()
		self.mainWidget.repaint() # update the widget

	#def slot_selectSpike(self, sDict):
	#	pass

class myStatListWidget(QtWidgets.QWidget):
	"""
	Widget to display a table with selectable stats.

	Gets list of stats from: sanpy.bAnalysisUtil.getStatList()
	"""
	def __init__(self, myParent, headerStr='Stat', parent=None):
		super().__init__(parent)

		self.myParent = myParent
		self.statList = sanpy.bAnalysisUtil.getStatList()
		self._rowHeight = 10

		self.myQVBoxLayout = QtWidgets.QVBoxLayout(self)

		self.myTableWidget = QtWidgets.QTableWidget()
		self.myTableWidget.setRowCount(len(self.statList))
		self.myTableWidget.setColumnCount(1)
		self.myTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
		self.myTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.myTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		self.myTableWidget.cellClicked.connect(self.on_scatter_toolbar_table_click)

		# set font size of table (default seems to be 13 point)
		fnt = self.font()
		fnt.setPointSize(self._rowHeight)
		self.myTableWidget.setFont(fnt)

		headerLabels = [headerStr]
		self.myTableWidget.setHorizontalHeaderLabels(headerLabels)

		header = self.myTableWidget.horizontalHeader()
		header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
		# QHeaderView will automatically resize the section to fill the available space. The size cannot be changed by the user or programmatically.
		header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

		for idx, stat in enumerate(self.statList):
			item = QtWidgets.QTableWidgetItem(stat)
			self.myTableWidget.setItem(idx, 0, item)
			self.myTableWidget.setRowHeight(idx, self._rowHeight)

		# assuming dark theme
		# does not work
		'''
		p = self.myTableWidget.palette()
		color1 = QtGui.QColor('#222222')
		color2 = QtGui.QColor('#555555')
		p.setColor(QtGui.QPalette.Base, color1)
		p.setColor(QtGui.QPalette.AlternateBase, color2)
		self.myTableWidget.setPalette(p)
		self.myTableWidget.setAlternatingRowColors(True)
		'''
		self.myQVBoxLayout.addWidget(self.myTableWidget)

		# select a default stat
		self.myTableWidget.selectRow(0) # hard coding 'Spike Frequency (Hz)'

	def getCurrentRow(self):
		return self.myTableWidget.currentRow()

	def getCurrentStat(self):
		# assuming single selection
		row = self.getCurrentRow()
		humanStat = self.myTableWidget.item(row,0).text()

		# convert from human readbale to backend
		stat = self.statList[humanStat]['name']

		return humanStat, stat

	@QtCore.pyqtSlot()
	def on_scatter_toolbar_table_click(self):
		"""
		replot the stat based on selected row
		"""
		#print('*** on table click ***')
		row = self.myTableWidget.currentRow()
		if row == -1 or row is None:
			return
		yStat = self.myTableWidget.item(row,0).text()
		self.myParent.replot()

	'''
	@QtCore.pyqtSlot()
	def on_button_click(self, name):
		print('=== myStatPlotToolbarWidget.on_button_click() name:', name)
	'''

if __name__ == '__main__':
	path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(path)
	ba.spikeDetect()
	print(ba.numSpikes)

	import sys
	app = QtWidgets.QApplication([])
	sp = plotScatter(ba=ba)
	sys.exit(app.exec_())
