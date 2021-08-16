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
		self.plotHistograms = True
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

		#
		self.histogramCheckbox = QtWidgets.QCheckBox("Histograms")
		self.histogramCheckbox.setChecked(self.plotHistograms)
		self.histogramCheckbox.stateChanged.connect(lambda:self.btnstate(self.histogramCheckbox))
		hLayout2.addWidget(self.histogramCheckbox)

		vLayout.addLayout(hLayout2)

		# second row of controls
		hLayout2_2 = QtWidgets.QHBoxLayout()

		aName = 'Spike: None'
		self.spikeNumberLabel = QtWidgets.QLabel(aName)
		hLayout2_2.addWidget(self.spikeNumberLabel)

		vLayout.addLayout(hLayout2_2)

		# x and y stat lists
		hLayout3 = QtWidgets.QHBoxLayout()
		self.xPlotWidget = myStatListWidget(self, headerStr='X Stat')
		self.xPlotWidget.myTableWidget.selectRow(0)
		self.yPlotWidget = myStatListWidget(self, headerStr='Y Stat')
		self.yPlotWidget.myTableWidget.selectRow(7)
		hLayout3.addWidget(self.xPlotWidget)
		hLayout3.addWidget(self.yPlotWidget)
		vLayout.addLayout(hLayout3)

		controlWidget.setLayout(vLayout)

		#
		# create a mpl plot (self._static_ax, self.static_canvas)
		#self.mplWindow2()
		plt.style.use('dark_background')
		# this is dangerous, collides with self.mplWindow()
		self.fig = mpl.figure.Figure()
		self.static_canvas = backend_qt5agg.FigureCanvas(self.fig)
		self.static_canvas.setFocusPolicy( QtCore.Qt.ClickFocus ) # this is really triccky and annoying
		self.static_canvas.setFocus()
		# self.axs[idx] = self.static_canvas.figure.add_subplot(numRow,1,plotNum)

		self._switchScatter()
		'''
		# gridspec for scatter + hist
		self.gs = self.fig.add_gridspec(2, 2,  width_ratios=(7, 2), height_ratios=(2, 7),
								left=0.1, right=0.9, bottom=0.1, top=0.9,
								wspace=0.05, hspace=0.05)

		self.axScatter = self.static_canvas.figure.add_subplot(self.gs[1, 0])
		self.axHistX = self.static_canvas.figure.add_subplot(self.gs[0, 0], sharex=self.axScatter)
		self.axHistY = self.static_canvas.figure.add_subplot(self.gs[1, 1], sharey=self.axScatter)


		# make initial empty scatter plot
		#self.lines, = self._static_ax.plot([], [], 'ow', picker=5)
		self.cmap = mpl.pyplot.cm.coolwarm
		self.cmap.set_under("white") # only works for dark theme
		#self.lines = self._static_ax.scatter([], [], c=[], cmap=self.cmap, picker=5)
		self.lines = self.axScatter.scatter([], [], c=[], cmap=self.cmap, picker=5)

		# make initial empty spike selection plot
		#self.linesSel, = self._static_ax.plot([], [], 'oy')
		self.linesSel, = self.axScatter.plot([], [], 'oy')

		# despine top/right
		self.axScatter.spines['right'].set_visible(False)
		self.axScatter.spines['top'].set_visible(False)
		self.axHistX.spines['right'].set_visible(False)
		self.axHistX.spines['top'].set_visible(False)
		self.axHistY.spines['right'].set_visible(False)
		self.axHistY.spines['top'].set_visible(False)
		'''

		#can do self.mplToolbar.hide()
		self.mplToolbar = mpl.backends.backend_qt5agg.NavigationToolbar2QT(self.static_canvas, self.static_canvas)

		#
		# finalize
		#hLayout.addLayout(vLayout)
		hSplitter.addWidget(controlWidget)
		hSplitter.addWidget(self.static_canvas) # add mpl canvas

		# set the layout of the main window
		self.mainWidget.setLayout(hLayout)

		self.replot()

	def _switchScatter(self):
		"""
		Switch between single scatter plot and scatter + marginal histograms
		"""
		if self.plotHistograms:
			# gridspec for scatter + hist
			self.gs = self.fig.add_gridspec(2, 2,  width_ratios=(7, 2), height_ratios=(2, 7),
									left=0.1, right=0.9, bottom=0.1, top=0.9,
									wspace=0.05, hspace=0.05)
		else:
			self.gs = self.fig.add_gridspec(1, 1,
									left=0.1, right=0.9, bottom=0.1, top=0.9,
									wspace=0.05, hspace=0.05)

		self.static_canvas.figure.clear()
		if self.plotHistograms:
			self.axScatter = self.static_canvas.figure.add_subplot(self.gs[1, 0])

			# x/y hist
			self.axHistX = self.static_canvas.figure.add_subplot(self.gs[0, 0], sharex=self.axScatter)
			self.axHistY = self.static_canvas.figure.add_subplot(self.gs[1, 1], sharey=self.axScatter)
			#
			self.axHistX.spines['right'].set_visible(False)
			self.axHistX.spines['top'].set_visible(False)
			self.axHistY.spines['right'].set_visible(False)
			self.axHistY.spines['top'].set_visible(False)

			#self.axHistX.tick_params(axis="x", labelbottom=False) # no labels
			#self.axHistX.tick_params(axis="y", labelleft=False) # no labels
		else:
			self.axScatter = self.static_canvas.figure.add_subplot(self.gs[0, 0])
			self.axHistX = None
			self.axHistY = None

		#
		# we wil always have axScatter
		#
		# make initial empty scatter plot
		self.cmap = mpl.pyplot.cm.coolwarm
		self.cmap.set_under("white") # only works for dark theme
		self.lines = self.axScatter.scatter([], [], c=[], cmap=self.cmap, picker=5)
		# make initial empty spike selection plot
		self.linesSel, = self.axScatter.plot([], [], 'o', markerfacecolor='none', color='y', markersize=10)  # no picker for selection
		# despine top/right
		self.axScatter.spines['right'].set_visible(False)
		self.axScatter.spines['top'].set_visible(False)

		self.cid = self.static_canvas.mpl_connect('pick_event', self.spike_pick_event)
		self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)

		#
		#self.replot()

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
		elif b.text() == 'Histograms':
			self.plotHistograms = state
			self._switchScatter()
			logger.info(f'plotHistograms:{self.plotHistograms}')
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
		logger.info(f'x:"{xStat}" y:"{yStat}"')

		if self.ba is None or xHumanStat is None or yHumanStat is None:
			xData = None
			yData = None
		else:
			xData = self.ba.getStat(xStat, sweepNumber=self.sweepNumber)
			yData = self.ba.getStat(yStat, sweepNumber=self.sweepNumber)

		self.xStatName = xStat
		self.yStatName = yStat

		# return if we got no data, happend when there is no analysis
		#if xData is None or yData is None:
		if not xData or not yData:
			logger.warning(f'Did not find either xStat: "{xStat}" or yStat: "{yStat}"')
			self.lines.set_offsets([np.nan, np.nan])
			self.scatter_hist([], [], self.axScatter, self.axHistX, self.axHistY)
			self.static_canvas.draw()
			self.mainWidget.repaint() # update the widget
			return

		#print(f'ba: {self.ba}')
		#print(f'sweepNumber: {self.sweepNumber} {type(self.sweepNumber)}')
		#print(f'xData: {xData}')

		if self.plotChasePlot:
			#print('todo: tweek x/y to plot i (x) versus i-1 (y)')
			# on selection, ind will refer to y-axis spike
			xData = xData[1:-1]
			yData = yData[0:-2]

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
		self.axScatter.set_xlabel(xStatLabel)
		self.axScatter.set_ylabel(yStatLabel)

		# cancel any selections
		self.linesSel.set_data([], [])
		#self.linesSel.set_offsets([], [])

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
		self.axScatter.set_xlim([xMin, xMax])
		self.axScatter.set_ylim([yMin, yMax])

		# this was for lines (not scatter)
		#self.axScatter.relim()
		#self.axScatter.autoscale_view(True,True,True)

		'''
		# x-hist
		self.axHistX.clear()
		self.axHistX.hist(xData)
		# y-hist
		self.axHistY.clear()
		self.axHistY.hist(xData)
		'''

		self.scatter_hist(xData, yData, self.axScatter, self.axHistX, self.axHistY)

		# redraw
		self.static_canvas.draw()
		self.mainWidget.repaint() # update the widget

	def scatter_hist(self, x, y, ax, ax_histx, ax_histy):
		"""
		plot a scatter with x/y histograms in margin

		Args:
			ax (axes) Scatter Axes
		"""

		# the scatter plot:
		#self.lines = ax.scatter(x, y)

		# now determine nice limits by hand:
		'''
		binwidth = 0.25
		xymax = max(np.max(np.abs(x)), np.max(np.abs(y)))
		lim = (int(xymax/binwidth) + 1) * binwidth
		bins = np.arange(-lim, lim + binwidth, binwidth)
		'''

		bins = 'doane'

		# x
		if ax_histx is not None:
			ax_histx.clear()
			nHistX, binsHistX, patchesHistX = ax_histx.hist(x, bins=bins, ec="gray")
			ax_histx.tick_params(axis="x", labelbottom=False) # no labels
			#ax_histx.spines['right'].set_visible(False)
			#ax_histx.spines['top'].set_visible(False)
			#ax_histx.yaxis.set_ticks_position('left')
			#ax_histx.xaxis.set_ticks_position('bottom')
			print('binsHistX:', len(binsHistX))
		# y
		if ax_histy is not None:
			ax_histy.clear()
			nHistY, binsHistY, patchesHistY = ax_histy.hist(y, bins=bins, orientation='horizontal', ec="gray")
			ax_histy.tick_params(axis="y", labelleft=False)
			#ax_histy.yaxis.set_ticks_position('left')
			#ax_histy.xaxis.set_ticks_position('bottom')
			print('binsHistY:', len(binsHistY))

	def selectSpike(self, sDict):
		"""
		Select a spike
		"""
		logger.info(sDict)

		spikeNumber = sDict['spikeNumber']

		logger.info(sDict)
		logger.info(f'{spikeNumber} {type(spikeNumber)}')

		if self.xStatName is None or self.yStatName is None:
			return

		if spikeNumber is not None and spikeNumber >= 0:
			xData = self.ba.getStat(self.xStatName, sweepNumber=self.sweepNumber)
			xData = [xData[spikeNumber]]

			yData = self.ba.getStat(self.yStatName, sweepNumber=self.sweepNumber)
			yData = [yData[spikeNumber]]
		else:
			xData = []
			yData = []

		self.linesSel.set_data(xData, yData)
		#self.linesSel.set_offsets(xData, yData)

		self.spikeNumberLabel.setText(f'Spike: {spikeNumber}')

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
		try:
			stat = self.statList[humanStat]['name']
		except (KeyError) as e:
			humanStat = None
			stat = None

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
