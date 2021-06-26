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
	myHumanName = 'Plot Scatter'

	def __init__(self, **kwargs):
		"""
		Args:
			ba (bAnalysis): Not required
		"""
		super().__init__('plotScatter', **kwargs)

		self.plotChasePlot = False # i vs i-1
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
		self.b1 = QtWidgets.QCheckBox("Respond To Analysis Changes")
		self.b1.setChecked(True)
		self.b1.stateChanged.connect(lambda:self.btnstate(self.b1))
		hLayout2.addWidget(self.b1)
		#
		self.b2 = QtWidgets.QCheckBox("Chase Plot")
		self.b2.setChecked(False)
		self.b2.stateChanged.connect(lambda:self.btnstate(self.b2))
		hLayout2.addWidget(self.b2)

		vLayout.addLayout(hLayout2)

		# x and y stat lists
		hLayout3 = QtWidgets.QHBoxLayout()
		self.xPlotWidget = myStatListWidget(self)
		self.yPlotWidget = myStatListWidget(self)
		hLayout3.addWidget(self.xPlotWidget)
		hLayout3.addWidget(self.yPlotWidget)
		vLayout.addLayout(hLayout3)

		controlWidget.setLayout(vLayout)

		#
		# create a mpl plot (self._static_ax, self.static_canvas)
		self.mplWindow2()
		# make initial empty scatter plot
		self.lines, = self._static_ax.plot([], [], 'ow', picker=5)
		# make initial empty spike selection plot
		self.linesSel, = self._static_ax.plot([], [], 'oy')

		#
		# finalize
		#hLayout.addLayout(vLayout)
		hSplitter.addWidget(controlWidget)
		hSplitter.addWidget(self.static_canvas) # add mpl canvas

		# set the layout of the main window
		self.mainWidget.setLayout(hLayout)

	def btnstate(self,b):
		state = b.isChecked()
		if b.text() == "Respond To Analysis Changes":
			self.setRespondToAnalysisChange(state)
		elif b.text() == 'Chase Plot':
			self.plotChasePlot = state
			logger.info(f'plotChasePlot:{self.plotChasePlot}')
			self.replot()
		else:
			logger.warning(f'Did not respond to button "{b.text()}"')

	def plot(self):
		pass

	def replot(self):
		"""
		Replot when analysis changes or file changes
		"""
		xStat = self.xPlotWidget.getCurrentStat()
		yStat = self.yPlotWidget.getCurrentStat()

		logger.info(xStat + ' ' + yStat)

		self.xStatName = xStat
		self.yStatName = yStat

		if self.ba is None:
			xData = []
			yData = []
		else:
			xData = self.ba.getStat(xStat)
			yData = self.ba.getStat(yStat)

		if xData is None:
			logger.warning(f'Did not find xStat: "{xStat}"')
			return
		if yData is None:
			logger.warning(f'Did not find yStat: "{yStat}"')
			return

		if self.plotChasePlot:
			#print('todo: tweek x/y to plot i (x) versus i-1 (y)')
			xData = xData[1:-1]
			yData = yData[0:-2]
			# on selection, ind will refer to y-axis spike

		self.lines.set_data(xData, yData)

		xStatLabel = xStat
		yStatLabel = yStat
		if self.plotChasePlot:
			xStatLabel += ' (i)'
			yStatLabel += ' (i-1)'
		self._static_ax.set_xlabel(xStatLabel)
		self._static_ax.set_ylabel(yStatLabel)

		# cancel any selections
		self.linesSel.set_data([], [])

		self._static_ax.relim()
		self._static_ax.autoscale_view(True,True,True)
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

		if spikeNumber >= 0:
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
	def __init__(self, myParent, parent=None):
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

		headerLabels = ['Stat']
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
		p = self.myTableWidget.palette()
		color1 = QtGui.QColor('#444444')
		color2 = QtGui.QColor('#555555')
		p.setColor(QtGui.QPalette.Base, color1)
		p.setColor(QtGui.QPalette.AlternateBase, color2)
		self.myTableWidget.setPalette(p)
		self.myTableWidget.setAlternatingRowColors(True)

		self.myQVBoxLayout.addWidget(self.myTableWidget)

		# select a default stat
		self.myTableWidget.selectRow(0) # hard coding 'Spike Frequency (Hz)'

	def getCurrentRow(self):
		return self.myTableWidget.currentRow()

	def getCurrentStat(self):
		# assuming single selection
		row = self.getCurrentRow()
		stat = self.myTableWidget.item(row,0).text()

		# convert from human readbale to backend
		stat = self.statList[stat]['name']

		return stat

	@QtCore.pyqtSlot()
	def on_scatter_toolbar_table_click(self):
		"""
		replot the stat based on selected row
		"""
		#print('*** on table click ***')
		row = self.myTableWidget.currentRow()
		if row == -1 or row is None:
			return
		yStat = self.myTableWidget.item(row,0).text() #
		#print('=== myStatPlotToolbarWidget.on_scatter_toolbar_table_click', row, yStat)
		self.myParent.replot()

	'''
	@QtCore.pyqtSlot()
	def on_button_click(self, name):
		print('=== myStatPlotToolbarWidget.on_button_click() name:', name)
	'''

if __name__ == '__main__':
	path = '/Users/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(path)
	ba.spikeDetect()
	print(ba.numSpikes)

	import sys
	app = QtWidgets.QApplication([])
	sp = scatterPlot(ba=ba)
	sys.exit(app.exec_())
