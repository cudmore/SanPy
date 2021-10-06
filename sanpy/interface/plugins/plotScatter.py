import math
import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtWidgets, QtGui

from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector  # To click+drag rectangular selection
import matplotlib.markers as mmarkers  # To define different markers for scatter

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
		super().__init__(**kwargs)

		self.plotChasePlot = False # i vs i-1
		self.plotColorTime = False
		#self.plotColorType = True  # Plot userType1, userType2, userType3
		#self.plotIsBad= True
		self.plotHistograms = True

		# keep track of what we are plotting, use this in replot()
		self.xStatName = None
		self.yStatName = None
		self.xStatHumanName = None
		self.yStatHumanName = None

		self.xData = []
		self.yData = []
		self.xAxisSpikeNumber = []  # We need to keep track of this for 'Chase Plot'

		#self.selectedSpike = None
		#self.selectedSpikeList = []  # Always a list, if empy then None

		#self.pyqtWindow()  # makes self.mainWidget and calls show()

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
		'''
		self.colorType = QtWidgets.QCheckBox("Color Type")
		self.colorType.setChecked(self.plotColorType)
		self.colorType.stateChanged.connect(lambda:self.btnstate(self.colorType))
		hLayout2.addWidget(self.colorType)
		'''

		#
		'''
		self.showBad = QtWidgets.QCheckBox("Show Bad")
		self.showBad.setChecked(self.plotIsBad)
		self.showBad.stateChanged.connect(lambda:self.btnstate(self.showBad))
		hLayout2.addWidget(self.showBad)
		'''

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
		#self.spikeSel, = self._static_ax.plot([], [], 'oy')
		self.spikeSel, = self.axScatter.plot([], [], 'oy')

		# despine top/right
		self.axScatter.spines['right'].set_visible(False)
		self.axScatter.spines['top'].set_visible(False)
		self.axHistX.spines['right'].set_visible(False)
		self.axHistX.spines['top'].set_visible(False)
		self.axHistY.spines['right'].set_visible(False)
		self.axHistY.spines['top'].set_visible(False)
		'''

		#can do self.mplToolbar.hide()
		# matplotlib.backends.backend_qt5.NavigationToolbar2QT
		self.mplToolbar = mpl.backends.backend_qt5agg.NavigationToolbar2QT(self.static_canvas, self.static_canvas)

		# put toolbar and static_canvas in a V layout
		plotWidget = QtWidgets.QWidget()
		vLayoutPlot = QtWidgets.QVBoxLayout()
		vLayoutPlot.addWidget(self.static_canvas)
		vLayoutPlot.addWidget(self.mplToolbar)
		plotWidget.setLayout(vLayoutPlot)

		#
		# finalize
		#hLayout.addLayout(vLayout)
		hSplitter.addWidget(controlWidget)
		#hSplitter.addWidget(self.static_canvas) # add mpl canvas
		hSplitter.addWidget(plotWidget)

		# set the layout of the main window
		# playing with dock
		#self.mainWidget.setLayout(hLayout)
		self.setLayout(hLayout)

		#self.mainWidget.setGeometry(100, 100, 1200, 600)

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

		# we might have memory garbage collection issues
		# passing self so we can receive selectSpikesFromHighlighter()
		self.myHighlighter = Highlighter(self, self.axScatter, [], [])

		#
		# we wil always have axScatter
		#
		# make initial empty scatter plot
		self.cmap = mpl.pyplot.cm.coolwarm.copy()
		self.cmap.set_under("white") # only works for dark theme
		# do not specify 'c' argument, we set colors using set_facecolor, set_color
		self.lines = self.axScatter.scatter([], [], picker=5)
		# make initial empty spike selection plot
		self.spikeSel, = self.axScatter.plot([], [], 'x', markerfacecolor='none', color='y', markersize=10)  # no picker for selection
		self.spikeListSel, = self.axScatter.plot([], [], 'o', markerfacecolor='none', color='y', markersize=10)  # no picker for selection
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
		#elif b.text() == 'Color Type':
		#	self.plotColorType = state
		#	logger.info(f'plotColorType:{self.plotColorType}')
		#	self.replot()
		#elif b.text() == 'Show Bad':
		#	self.plotIsBad = state
		#	logger.info(f'plotIsBad:{self.plotIsBad}')
		#	self.replot()
		elif b.text() == 'Histograms':
			self.plotHistograms = state
			self._switchScatter()
			logger.info(f'plotHistograms:{self.plotHistograms}')
			self.replot()
		else:
			logger.warning(f'Did not respond to button "{b.text()}"')

	def setAxis(self):
		# inherited, resopnd to user setting x-axis
		#self.replot()

		# generate a list of spike and select

		startSec, stopSec = self.getStartStop()
		if startSec is None or stopSec is None:
			return

		# select spike in range
		thresholdSec = self.ba.getStat('thresholdSec')
		self.selectedSpikeList = [spikeIdx for spikeIdx,spikeSec in enumerate(thresholdSec) if (spikeSec>startSec and spikeSec<stopSec)]

		self.selectSpikeList()

	def replot(self):
		"""
		Replot when analysis changes or file changes
		"""

		# get from stat lists
		xHumanStat, xStat = self.xPlotWidget.getCurrentStat()
		yHumanStat, yStat = self.yPlotWidget.getCurrentStat()

		logger.info(f'x:"{xHumanStat}" y:"{yHumanStat}"')
		#logger.info(f'x:"{xStat}" y:"{yStat}"')

		if self.ba is None or xHumanStat is None or yHumanStat is None:
			xData = []
			yData = []
		else:
			xData = self.ba.getStat(xStat, sweepNumber=self.sweepNumber)
			yData = self.ba.getStat(yStat, sweepNumber=self.sweepNumber)


		#
		# convert to numpy
		xData = np.array(xData)
		yData = np.array(yData)

		#
		# return if we got no data, happend when there is no analysis
		if xData is None or yData is None or np.isnan(xData).all() or np.isnan(yData).all():
			# We get here when there is no analysis
			#logger.warning(f'Did not find either xStat: "{xStat}" or yStat: "{yStat}"')
			self.lines.set_offsets([np.nan, np.nan])
			self.scatter_hist([], [], self.axHistX, self.axHistY)
			self.static_canvas.draw()
			return

		self.xStatName = xStat
		self.yStatName = yStat
		self.xStatHumanName = xHumanStat
		self.yStatHumanName = yHumanStat

		# keep track of x-axis spike number (for chae plot)
		xAxisSpikeNumber = self.ba.getStat('spikeNumber', sweepNumber=self.sweepNumber)
		xAxisSpikeNumber = np.array(xAxisSpikeNumber)

		# need to mask color and marker
		if self.plotChasePlot:
			# on selection, ind will refer to y-axis spike
			xData = xData[1:-1] # x is the reference spike for marking (bad, type)
			yData = yData[0:-2]
			#
			#xAxisSpikeNumber = xAxisSpikeNumber[1:-1]
			xAxisSpikeNumber = xAxisSpikeNumber[0:-2]

		self.xData = xData
		self.yData = yData
		self.xAxisSpikeNumber = xAxisSpikeNumber

		# data
		data = np.stack([xData, yData], axis=1)
		self.lines.set_offsets(data)  # (N, 2)

		#
		# color
		if self.plotColorTime:
			tmpColor = np.array(range(len(xData)))
			self.lines.set_array(tmpColor)  # set_array is for a color map
			self.lines.set_cmap(self.cmap)  # mpl.pyplot.cm.coolwarm
			self.lines.set_color(None)
		else:
			#tmpColor = np.array(range(len(xData)))
			# assuming self.cmap.set_under("white")

			#from matplotlib.colors import ListedColormap
			color_dict={1:"blue",
				2:"red",
				13:"orange",
				7:"green"}
			color_dict= {
				'good':(0,1,1,1), # cyan
				'bad':'r', # red
				#'userType1':(0,0,1,1), # blue
				#'userType2':(0,1,1,1), # cyan
				#'userType3':(1,0,1,1), # magenta
			}
			marker_dict = {
				'userType1': mmarkers.MarkerStyle('*'),  # star
				'userType2': mmarkers.MarkerStyle('v'),  # triangle_down
				'userType3': mmarkers.MarkerStyle('<'),  # triangle_left
			}

			# no need for a cmap ???
			#cm = ListedColormap([color_dict[x] for x in color_dict.keys()])
			#self.lines.set_cmap(cm)

			goodSpikes = self.ba.getStat('include', sweepNumber=self.sweepNumber)
			userTypeList = self.ba.getStat('userType', sweepNumber=self.sweepNumber)

			if self.plotChasePlot:
				#xData = xData[1:-1] # x is the reference spike for marking (bad, type)
				#goodSpikes = goodSpikes[1:-1]
				#userTypeList = userTypeList[1:-1]
				goodSpikes = goodSpikes[0:-2]
				userTypeList = userTypeList[0:-2]

			tmpColors = [color_dict['bad']] * len(xData) # start as all good
			# user types will use symbols
			#tmpColors = [color_dict['type'+num2str(x)] if x>0 else tmpColors[idx] for idx,x in enumerate(userTypeList)]
			# bad needs to trump user type !!!
			tmpColors = [color_dict['good'] if x else tmpColors[idx] for idx,x in enumerate(goodSpikes)]
			tmpColors = np.array(tmpColors)
			#print('tmpColors', type(tmpColors), tmpColors.shape, tmpColors)

			self.lines.set_array(None)  # used to map [0,1] to color map
			self.lines.set_facecolor(tmpColors)
			self.lines.set_color(tmpColors)  # sets the outline

			# set user type 2 to 'star'
			# see: https://stackoverflow.com/questions/52303660/iterating-markers-in-plots/52303895#52303895
			#import matplotlib.markers as mmarkers
			myMarkerList = [marker_dict['userType'+str(x)] if x>0 else mmarkers.MarkerStyle('o') for x in userTypeList]
			myPathList = []
			for myMarker in myMarkerList:
				path = myMarker.get_path().transformed(myMarker.get_transform())
				myPathList.append(path)
			self.lines.set_paths(myPathList)

		#
		# update highlighter, needs coordinates of x/y to highlight
		self.myHighlighter.setData(xData, yData)

		# label axes
		xStatLabel = xHumanStat
		yStatLabel = yHumanStat
		if self.plotChasePlot:
			xStatLabel += ' [i]'
			yStatLabel += ' [i-1]'
		self.axScatter.set_xlabel(xStatLabel)
		self.axScatter.set_ylabel(yStatLabel)

		# don't cancel on replot
		'''
		# cancel any selections
		self.spikeSel.set_data([], [])
		#self.spikeSel.set_offsets([], [])
		self.spikeListSel.set_data([], [])
		#self.spikeListSel.set_offsets([], [])
		'''

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

		self.axScatter.set_xlim([xMin, xMax])
		self.axScatter.set_ylim([yMin, yMax])

		#self.scatter_hist(xData, yData, self.axScatter, self.axHistX, self.axHistY)
		self.scatter_hist(xData, yData, self.axHistX, self.axHistY)

		# redraw
		self.static_canvas.draw()
		# was this
		#self.repaint() # update the widget

	#def scatter_hist(self, x, y, ax, ax_histx, ax_histy):
	def scatter_hist(self, x, y, ax_histx, ax_histy):
		"""
		plot a scatter with x/y histograms in margin

		Args:
			x (date):
			y (data):
			ax_histx (axes) Histogram Axes
			ax_histy (axes) Histogram Axes
		"""

		xBins = 'auto'
		yBins = 'auto'

		xTmp = np.array(x)  #y[~np.isnan(y)]
		xTmp = xTmp[~np.isnan(xTmp)]
		xTmpBins = np.histogram_bin_edges(xTmp, 'auto')
		xNumBins = len(xTmpBins)
		if xNumBins*2 < len(x):
			xNumBins *= 2
		xBins = xNumBins

		yTmp = np.array(y)  #y[~np.isnan(y)]
		yTmp = yTmp[~np.isnan(yTmp)]
		yTmpBins = np.histogram_bin_edges(yTmp, 'auto')
		yNumBins = len(yTmpBins)
		if yNumBins*2 < len(y):
			yNumBins *= 2
		yBins = yNumBins

		# x
		if ax_histx is not None:
			ax_histx.clear()
			nHistX, binsHistX, patchesHistX = ax_histx.hist(x, bins=xBins, facecolor='silver', edgecolor="gray")
			ax_histx.tick_params(axis="x", labelbottom=False) # no labels
			#ax_histx.spines['right'].set_visible(False)
			#ax_histx.spines['top'].set_visible(False)
			#ax_histx.yaxis.set_ticks_position('left')
			#ax_histx.xaxis.set_ticks_position('bottom')
			#print('  binsHistX:', len(binsHistX))
		# y
		if ax_histy is not None:
			ax_histy.clear()
			nHistY, binsHistY, patchesHistY = ax_histy.hist(y, bins=yBins, orientation='horizontal', facecolor='silver', edgecolor="gray")
			ax_histy.tick_params(axis="y", labelleft=False)
			#ax_histy.yaxis.set_ticks_position('left')
			#ax_histy.xaxis.set_ticks_position('bottom')
			#print('  binsHistY:', len(binsHistY))

	def selectSpikeList(self, sDict=None):
		"""
		sDict (dict): NOT USED
		"""
		#spikeList = sDict['spikeList']
		#logger.info(sDict)

		if self.xStatName is None or self.yStatName is None:
			return

		#self.selectedSpikeList = spikeList  # [] on no selection

		spikeList = self.selectedSpikeList

		#logger.info(f'spikeList:{spikeList}')

		#if spikeList is not None:
		if len(spikeList) > 0:
			#xData = self.ba.getStat(self.xStatName, sweepNumber=self.sweepNumber)
			#xData = np.array(xData)
			xData = [self.xData[spikeList]]

			#yData = self.ba.getStat(self.yStatName, sweepNumber=self.sweepNumber)
			#yData = np.array(yData)
			yData = [self.yData[spikeList]]
		else:
			xData = []
			yData = []

		self.spikeListSel.set_data(xData, yData)

		self.static_canvas.draw()
		# was this
		#self.repaint() # update the widget

	def selectSpike(self, sDict=None):
		"""
		Select a spike
		sDict (dict): NOT USED
		"""

		#logger.info(sDict)

		#spikeNumber = sDict['spikeNumber']
		#spikeList = [spikeNumber]

		spikeNumber = self.selectedSpike

		if self.xStatName is None or self.yStatName is None:
			return

		xData = []
		yData = []
		if spikeNumber is not None:
			try:
				xData = [self.xData[spikeNumber]]
				yData = [self.yData[spikeNumber]]
			except (IndexError) as e:
				logger.error(e)

		self.spikeSel.set_data(xData, yData)
		#self.spikeSel.set_offsets(xData, yData)

		self.spikeNumberLabel.setText(f'Spike: {spikeNumber}')

		self.static_canvas.draw()
		#was this
		#self.repaint() # update the widget

	def selectSpikesFromHighlighter(self, selectedSpikeList):
		"""
		User selected some spikes with Highlighter -->> PRopogate to main
		"""

		if len(selectedSpikeList) > 0:
			self.selectedSpikeList = selectedSpikeList
			sDict = {
				'spikeList': selectedSpikeList,
				'doZoom': False, # never zoom on multiple spike selection
				'ba': self.ba,
			}
			self.signalSelectSpikeList.emit(sDict)

	def toolbarHasSelection(self):
		"""
		return true if either ['zoom rect', 'pan/zoom'] are selected
		This is needed to cancel mouse clicks in Highlighter and right click in SanPyPLugin
		"""
		state = self.mplToolbar.mode
		return state in ['zoom rect', 'pan/zoom']

	def prependMenus(self, contextMenu):
		"""
		Prepend menus to context menu
		"""

		noSpikesSelected = len(self.selectedSpikeList) == 0

		includeAction = contextMenu.addAction("Accept")
		includeAction.setDisabled(noSpikesSelected)  # disable if no spikes

		rejectAction = contextMenu.addAction("Reject")
		rejectAction.setDisabled(noSpikesSelected)

		userType1_action = contextMenu.addAction("User Type 1")
		userType1_action.setDisabled(noSpikesSelected)

		userType2_action = contextMenu.addAction("User Type 2")
		userType2_action.setDisabled(noSpikesSelected)

		userType3_action = contextMenu.addAction("User Type 3")
		userType3_action.setDisabled(noSpikesSelected)

		userType4_action = contextMenu.addAction("Reset User Type")
		userType4_action.setDisabled(noSpikesSelected)

		contextMenu.addSeparator()

	def handleContextMenu(self, action):
		"""
		return true if handled
		"""
		if action is None:
			return False

		text = action.text()
		logger.info(f'Action text "{text}"')

		handled = False
		if text == 'Accept':
			#print('Set selected spikes to include (not isbad)')
			self.ba.setSpikeStat(self.selectedSpikeList, 'isBad', False)
			self.replot()
			handled = True
		elif text == 'Reject':
			#print('Set selected spikes to reject (isbad)')
			self.ba.setSpikeStat(self.selectedSpikeList, 'isBad', True)
			self.replot()
			handled = True
		elif text == 'User Type 1':
			self.ba.setSpikeStat(self.selectedSpikeList, 'userType', 1)
			self.replot()
			handled = True
		elif text == 'User Type 2':
			self.ba.setSpikeStat(self.selectedSpikeList, 'userType', 2)
			self.replot()
			handled = True
		elif text == 'User Type 3':
			self.ba.setSpikeStat(self.selectedSpikeList, 'userType', 3)
			self.replot()
			handled = True
		elif text == 'Reset User Type':
			self.ba.setSpikeStat(self.selectedSpikeList, 'userType', 0)
			self.replot()
			handled = True
		else:
			#logger.info(f'Action not understood "{text}"')
			pass

		#
		return handled

	def copyToClipboard(self):
		"""
		Copy current x/y stats to clipboard with some other book-keeping.
		For example: spike number, spike time (s), is bad, user type, and file name.
		"""
		spikeNumber = self.ba.getStat('spikeNumber', sweepNumber=self.sweepNumber)
		spikeTimeSec = self.ba.getStat('thresholdSec', sweepNumber=self.sweepNumber)
		#
		xStat = self.ba.getStat(self.xStatName, sweepNumber=self.sweepNumber)
		yStat = self.ba.getStat(self.yStatName, sweepNumber=self.sweepNumber)
		#
		goodSpikes = self.ba.getStat('include', sweepNumber=self.sweepNumber)
		userType = self.ba.getStat('userType', sweepNumber=self.sweepNumber)
		file = self.ba.getStat('file', sweepNumber=self.sweepNumber)

		columns = ['Spike Number', 'Spike Time(s)', self.xStatHumanName, self.yStatHumanName, 'Include', 'User Type', 'File']
		df = pd.DataFrame(columns=columns)
		df['Spike Number'] = spikeNumber
		df['Spike Time(s)'] = spikeTimeSec
		df[self.xStatHumanName] = xStat
		df[self.yStatHumanName] = yStat
		df['Include'] = goodSpikes
		df['User Type'] = userType
		df['File'] = file

		excel = True
		sep = '\t'
		df.to_clipboard(excel=excel, sep=sep)

		logger.info(f'Copied {len(df)} spikes to clipboard.')

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
		self._rowHeight = 9

		self.myQVBoxLayout = QtWidgets.QVBoxLayout(self)

		self.myTableWidget = QtWidgets.QTableWidget()
		self.myTableWidget.setWordWrap(False)
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
			logger.error(f'Did not find humanStat "{humanStat}" exception:{e}')
			#for k,v in

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

class Highlighter(object):
	"""
	See: https://stackoverflow.com/questions/31919765/choosing-a-box-of-data-points-from-a-plot
	"""
	def __init__(self, parentPlot, ax, x, y):
		self._parentPlot = parentPlot
		self.ax = ax
		self.canvas = ax.figure.canvas
		self.x, self.y = x, y

		# mask will be set in self.setData
		if x and y:
			self.mask = np.zeros(x.shape, dtype=bool)
		else:
			self.mask = None

		markerSize = 50
		self._highlight = ax.scatter([], [], s=markerSize, color='yellow', zorder=10)

		# here self is setting the callback and calls __call__
		#self.selector = RectangleSelector(ax, self, useblit=True, interactive=False)
		self.selector = RectangleSelector(ax, self._HighlighterReleasedEvent,
											button=[1],
											useblit=True, interactive=False)

		self.mouseDownEvent = None
		self.keyIsDown = None

		self.ax.figure.canvas.mpl_connect('key_press_event', self._keyPressEvent)
		self.ax.figure.canvas.mpl_connect('key_release_event', self._keyReleaseEvent)

		# remember, sanpyPlugin is installing for key press and on pick
		self.keepOnMotion = self.ax.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)
		self.keepMouseDown = self.ax.figure.canvas.mpl_connect('button_press_event', self.on_button_press)

	def _keyPressEvent(self, event):
		#logger.info(event)
		self.keyIsDown = event.key

	def _keyReleaseEvent(self, event):
		#logger.info(event)
		self.keyIsDown = None

	def on_button_press(self, event):
		"""
		Args:
			event (matplotlib.backend_bases.MouseEvent):
		"""
		#print(f'  event.button:"{event.button}" {type(event.button)}')
		# don't take action on right-click
		if event.button != 1:
			# not the left button
			#print('  rejecting not button 1')
			return

		#logger.info(event)

		# do nothing in zoom or pan/zoom is active
		# finding documentation on mpl toolbar is near impossible
		# https://stackoverflow.com/questions/20711148/ignore-matplotlib-cursor-widget-when-toolbar-widget-selected
		#state = self._parentPlot.static_canvas.manager.toolbar.mode  # manager is coming up None
		if self._parentPlot.toolbarHasSelection():
			return
		# was this
		#state = self._parentPlot.mplToolbar.mode
		#if state in ['zoom rect', 'pan/zoom']:
		#	logger.info(f'Ignoring because tool "{state}" is active')
		#	return

		self.mouseDownEvent = event

		# if shift is down then add to mask
		#print('  self.keyIsDown', self.keyIsDown)
		if self.keyIsDown == 'shift':
			pass
		else:
			self.mask = np.zeros(self.x.shape, dtype=bool)

	def on_motion(self, event):
		"""
		event (<class 'matplotlib.backend_bases.MouseEvent'>):

		event contains:
			motion_notify_event: xy=(113, 36) xydata=(None, None) button=None dblclick=False inaxes=None
		"""

		# self.ax is our main scatter plot axes
		if event.inaxes != self.ax:
			return

		# mouse is not down
		if self.mouseDownEvent is None:
			return

		#logger.info('')

		event1 = self.mouseDownEvent
		event2 = event

		if event1 is None or event2 is None:
			return

		self.mask |= self.inside(event1, event2)
		xy = np.column_stack([self.x[self.mask], self.y[self.mask]])
		self._highlight.set_offsets(xy)
		self.canvas.draw()

	def setData(self, x, y):
		"""
		Set underlying highlighter data, call this when we replot() scatter
		"""
		# convert list to np array
		xArray = np.array(x)
		yArray = np.array(y)

		self.mask = np.zeros(xArray.shape, dtype=bool)
		self.x = xArray
		self.y = yArray

	#def __call__(self, event1, event2):
	def _HighlighterReleasedEvent(self, event1, event2):
		"""
		Callback when mouse is released

		event1:
			button_press_event: xy=(87.0, 136.99999999999991) xydata=(27.912559411227885, 538.8555851528383) button=1 dblclick=False inaxes=AxesSubplot(0.1,0.1;0.607046x0.607046)
		event2:
			button_release_event: xy=(131.0, 211.99999999999991) xydata=(48.83371692821588, 657.6677439956331) button=1 dblclick=False inaxes=AxesSubplot(0.1,0.1;0.607046x0.607046)
		"""

		#logger.info(event1)
		#logger.info(event2)

		self.mouseDownEvent = None

		# emit the selected spikes
		selectedSpikes = np.where(self.mask==True)
		selectedSpikes = selectedSpikes[0]  # why does np do this ???

		#logger.info(f'Num Spikes Select:{len(selectedSpikes)}')

		selectedSpikesList = selectedSpikes.tolist()
		self._parentPlot.selectSpikesFromHighlighter(selectedSpikesList)

		# clear the selection use just made, will get 'reselected' in signal/slot
		self._highlight.set_offsets([np.nan, np.nan])

		return

	def inside(self, event1, event2):
		"""Returns a boolean mask of the points inside the rectangle defined by
		event1 and event2."""
		# Note: Could use points_inside_poly, as well
		x0, x1 = sorted([event1.xdata, event2.xdata])
		y0, y1 = sorted([event1.ydata, event2.ydata])
		mask = ((self.x > x0) & (self.x < x1) &
				(self.y > y0) & (self.y < y1))
		return mask

if __name__ == '__main__':
	path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(path)
	ba.spikeDetect()
	print(ba.numSpikes)

	import sys
	app = QtWidgets.QApplication([])
	sp = plotScatter(ba=ba)
	sp.show()
	sys.exit(app.exec_())
