import math

from functools import partial

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin

class spikeClips(sanpyPlugin):
	"""
	Plot x/y statiistics as a scatter

	Get stat names and variables from sanpy.bAnalysisUtil.getStatList()
	"""
	myHumanName = 'Plot Spike Clips'

	def __init__(self, **kwargs):
		"""
		Args:
			ba (bAnalysis): Not required
		"""
		super().__init__(**kwargs)

		self.preClipWidth_ms = 50
		self.postClipWidth_ms = 50
		if self.ba is not None:
			#self.clipWidth_ms = self.ba.detectionClass['spikeClipWidth_ms']
			self.preClipWidth_ms = self.ba.detectionClass['preSpikeClipWidth_ms']
			self.postClipWidth_ms = self.ba.detectionClass['postSpikeClipWidth_ms']

		self.respondTo = 'All' # ('All', 'X-Axis', 'Spike Selection')

		# keep track so we can export to clipboard
		self.x = None
		self.y = None
		self.yMean = None

		# for waterfall
		self.xMult = 0.1
		self.yMult = 0.1

		# todo: mode these to sanpyPlugin
		self.selectedSpikeList = []
		self.selectedSpike = None

		#self.clipLines = None
		#self.meanClipLine = None
		self.singleSpikeMultiLine = None
		self.spikeListMultiLine = None

		# makes self.mainWidget and calls show()
		#self.pyqtWindow()

		# main layout
		vLayout = QtWidgets.QVBoxLayout()

		#
		# controls
		hLayout2 = QtWidgets.QHBoxLayout()

		self.numSpikesLabel = QtWidgets.QLabel('Num Spikes:None')
		hLayout2.addWidget(self.numSpikesLabel)

		self.meanCheckBox = QtWidgets.QCheckBox('Mean Trace (red)')
		self.meanCheckBox.setChecked(True)
		self.meanCheckBox.stateChanged.connect(lambda:self.replot())
		hLayout2.addWidget(self.meanCheckBox)

		self.phasePlotCheckBox = QtWidgets.QCheckBox('Phase')
		self.phasePlotCheckBox.setChecked(False)
		self.phasePlotCheckBox.stateChanged.connect(lambda:self.replot())
		hLayout2.addWidget(self.phasePlotCheckBox)

		self.waterfallCheckBox = QtWidgets.QCheckBox('Waterfall')
		self.waterfallCheckBox.setChecked(False)
		self.waterfallCheckBox.stateChanged.connect(lambda:self.replot())
		hLayout2.addWidget(self.waterfallCheckBox)

		# x mult for waterfall
		aLabel = QtWidgets.QLabel('X-Mult')
		hLayout2.addWidget(aLabel)
		self.xMultSpinBox = QtWidgets.QDoubleSpinBox()
		self.xMultSpinBox.setKeyboardTracking(False)
		self.xMultSpinBox.setSingleStep(0.05)
		self.xMultSpinBox.setRange(0, 1)
		self.xMultSpinBox.setValue(self.xMult)
		self.xMultSpinBox.valueChanged.connect(partial(self.on_spinbox, aLabel))
		hLayout2.addWidget(self.xMultSpinBox)

		# y mult for waterfall
		aLabel = QtWidgets.QLabel('Y-Mult')
		hLayout2.addWidget(aLabel)
		self.yMultSpinBox = QtWidgets.QDoubleSpinBox()
		self.yMultSpinBox.setKeyboardTracking(False)
		self.yMultSpinBox.setSingleStep(0.05)
		self.yMultSpinBox.setRange(0, 1)
		self.yMultSpinBox.setValue(self.yMult)
		self.yMultSpinBox.valueChanged.connect(partial(self.on_spinbox, aLabel))
		hLayout2.addWidget(self.yMultSpinBox)

		vLayout.addLayout(hLayout2)

		#
		hLayout3 = QtWidgets.QHBoxLayout()

		aLabel = QtWidgets.QLabel('Pre Clip Width (ms)')
		hLayout3.addWidget(aLabel)
		self.preClipWidthSpinBox = QtWidgets.QSpinBox()
		self.preClipWidthSpinBox.setKeyboardTracking(False)
		self.preClipWidthSpinBox.setRange(1, 1e9)
		self.preClipWidthSpinBox.setValue(self.preClipWidth_ms)
		#self.clipWidthSpinBox.editingFinished.connect(partial(self.on_spinbox, aLabel))
		self.preClipWidthSpinBox.valueChanged.connect(partial(self.on_spinbox, aLabel))
		hLayout3.addWidget(self.preClipWidthSpinBox)

		aLabel = QtWidgets.QLabel('Post Clip Width (ms)')
		hLayout3.addWidget(aLabel)
		self.postClipWidthSpinBox = QtWidgets.QSpinBox()
		self.postClipWidthSpinBox.setKeyboardTracking(False)
		self.postClipWidthSpinBox.setRange(1, 1e9)
		self.postClipWidthSpinBox.setValue(self.postClipWidth_ms)
		#self.clipWidthSpinBox.editingFinished.connect(partial(self.on_spinbox, aLabel))
		self.postClipWidthSpinBox.valueChanged.connect(partial(self.on_spinbox, aLabel))
		hLayout3.addWidget(self.postClipWidthSpinBox)

		#
		# radio buttons
		self.respondToAll = QtWidgets.QRadioButton('All')
		self.respondToAll.setChecked(True)
		self.respondToAll.toggled.connect(self.on_radio)
		hLayout3.addWidget(self.respondToAll)

		self.respondToAxisRange = QtWidgets.QRadioButton('X-Axis')
		self.respondToAxisRange.setChecked(False)
		self.respondToAxisRange.toggled.connect(self.on_radio)
		hLayout3.addWidget(self.respondToAxisRange)

		self.respondToSpikeSel = QtWidgets.QRadioButton('Spike Selection')
		self.respondToSpikeSel.setChecked(False)
		self.respondToSpikeSel.toggled.connect(self.on_radio)
		hLayout3.addWidget(self.respondToSpikeSel)

		#
		vLayout.addLayout(hLayout3)

		#
		# pyqt graph
		self.view = pg.GraphicsLayoutWidget()
		self.clipPlot = self.view.addPlot(row=0, col=0)
		#self.clipPlot.hideButtons()
		#self.clipPlot.setMenuEnabled(False)
		#self.clipPlot.setMouseEnabled(x=False, y=False)

		self.clipPlot.getAxis('left').setLabel('mV')
		self.clipPlot.getAxis('bottom').setLabel('time (ms)')

		# kymograph analysis
		self.variancePlot = self.view.addPlot(row=1, col=0)

		vLayout.addWidget(self.view) #, stretch=8)

		# set the layout of the main window
		#self.mainWidget.setLayout(vLayout)
		self.setLayout(vLayout)

		self.replot()

	def on_radio(self):
		"""
		Will receive this callback n times where n is # buttons/checkboxes in group
		Only one callback will have isChecked, all other will be !isChecked
		"""
		#logger.info('')
		sender = self.sender()
		senderText = sender.text()
		isChecked = sender.isChecked()

		if senderText == 'All' and isChecked:
			self.respondTo = 'All'
		elif senderText == 'X-Axis' and isChecked:
			self.respondTo = 'X-Axis'
		elif senderText == 'Spike Selection' and isChecked:
			self.respondTo = 'Spike Selection'
			# debug
			#self.selectedSpikeList = [5, 7, 10]

		#
		if isChecked:
			self.replot()

	def on_spinbox(self, label):
		#logger.info('')
		# grab from interface
		self.preClipWidth_ms = self.preClipWidthSpinBox.value()
		self.postClipWidth_ms = self.postClipWidthSpinBox.value()
		self.xMult = self.xMultSpinBox.value()
		self.yMult = self.yMultSpinBox.value()

		self.replot()

	def setAxis(self):
		self.replot()

	def replot(self):
		"""
		Replot when analysis changes or file changes
		"""
		self._myReplotClips()
		#
		#self.mainWidget.repaint() # update the widget

	'''
	def setAxis(self):
		"""
		(self.startSec, self.stopSec) has been set by sanpyPlugins
		"""
		self.replot()
	'''

	def _myReplotClips(self):
		"""
		Note: This is the same code as in bDetectionWidget.refreshClips() MERGE THEM.
		"""

		#logger.info('')

		isPhasePlot = self.phasePlotCheckBox.isChecked()

		# always remove existing
		self.clipPlot.clear()
		self.variancePlot.clear()

		if self.ba is None or self.ba.numSpikes == 0:
			return

		# TODO: Add option to select by selectSpikeList

		#
		# respond to x-axis selection
		startSec = None
		stopSec = None
		selectedSpikeList = []
		if self.respondTo == 'All':
			startSec = 0
			stopSec = self.ba.recordingDur
		elif self.respondTo == 'X-Axis':
			startSec, stopSec = self.getStartStop()
			if startSec is None or stopSec is None:
				startSec = 0
				stopSec = self.ba.recordingDur
		elif self.respondTo == 'Spike Selection':
			selectedSpikeList = self.selectedSpikeList

		#print('=== selectedSpikeList:', selectedSpikeList)

		# this returns x-axis in ms
		# theseClips is a [list] of clips
		# theseClips_x is in ms
		theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(startSec, stopSec,
												spikeSelection=selectedSpikeList,
												preSpikeClipWidth_ms=self.preClipWidth_ms,
												postSpikeClipWidth_ms=self.postClipWidth_ms,
												sweepNumber=self.sweepNumber)
		numClips = len(theseClips)
		self.numSpikesLabel.setText(f'Num Spikes: {numClips}')

		if numClips == 0:
			return

		# convert clips to 2d ndarray ???
		#dataPointsPerMs = self.ba.dataPointsPerMs
		xTmp = np.array(theseClips_x)
		#xTmp /= dataPointsPerMs # pnt to ms
		xTmp /= self.ba.dataPointsPerMs * 1000  # pnt to seconds
		yTmp = np.array(theseClips)  # mV

		#print('xTmp:', xTmp.shape)
		#print('yTmp:', yTmp.shape)

		#print(xTmp.shape, yTmp.shape)
		if isPhasePlot:
			# plot x mV versus y dV/dt
			dvdt = np.zeros((yTmp.shape[0], yTmp.shape[1]-1))  #
			for i in range(dvdt.shape[0]):
				dvdt[i,:] = np.diff(yTmp[i,:])
				# drop first pnt in x

			#
			xTmp = yTmp[:, 1:] # drop first column of mV and swap to x-axis
			yTmp = dvdt
			#print(xTmp.shape, yTmp.shape)

		# for waterfall we need x-axis to have different values for each spike
		if self.waterfallCheckBox.isChecked():
			#print(xTmp.shape, yTmp.shape)
			# xTmp and yTmp are 2D with rows/clips and cols/data_pnts
			xMin = np.nanmin(xTmp)
			xMax = np.nanmax(xTmp)
			xRange = xMax - xMin
			yMin = np.nanmin(yTmp)
			yMax = np.nanmax(yTmp)
			yRange = yMax - yMin
			xOffset = 0
			yOffset = 0
			xInc = xRange * self.xMult # ms, xInc is 10% of x-range
			yInc = yRange * self.yMult
			for i in range(xTmp.shape[0]):
				xTmp[i,:] += xOffset
				yTmp[i,:] += yOffset
				xOffset += xInc # ms
				yOffset += yInc # mV

		# color map to give each clip different color
		'''
		colormap = 'rainbow'
		cmap = cm.get_cmap(colormap);
		n = len(uids);
		colors = cmap(range(n), bytes = True);
		'''

		#
		# original, one multiline for all clips (super fast)
		#self.clipLines = MultiLine(xTmp, yTmp, self, allowXAxisDrag=False, type='clip')
		#
		# each clip so we can set color
		colors = [
			(0, 0, 0),
			(4, 5, 61),
			(84, 42, 55),
			(15, 87, 60),
			(208, 17, 141),
			(255, 255, 255)
		]

		# color map
		cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, 6), color=colors)
		#colors = ['r', 'g', 'b']
		numSpikes = xTmp.shape[0]
		for i in range(numSpikes):
			#forcePenColor = cmap.getByIndex(i)
			forcePenColor = None
			#print('forcePenColor:', forcePenColor)
			xPlot = xTmp[i,:]
			yPlot = yTmp[i,:]
			tmpClipLines = MultiLine(xPlot, yPlot, self, allowXAxisDrag=False, forcePenColor=forcePenColor, type='clip')
			self.clipPlot.addItem(tmpClipLines)

		#
		# always calculate mean clip
		# x mean is redundant but works well for waterfall
		xMeanClip = np.nanmean(xTmp, axis=0) # xTmp is in ms
		yMeanClip = np.nanmean(yTmp, axis=0)

		# plot if checkbox is on
		if self.meanCheckBox.isChecked():
			tmpMeanClipLine = MultiLine(xMeanClip, yMeanClip, self, width=3, allowXAxisDrag=False, type='meanclip')
			self.clipPlot.addItem(tmpMeanClipLine)

		#
		if 1:
			#self.variancePlot.clear()
			xVarClip = np.nanmean(xTmp, axis=0) # xTmp is in ms
			yVarClip = np.nanvar(yTmp, axis=0)
			tmpVarClipLine = MultiLine(xVarClip, yVarClip, self, width=3, allowXAxisDrag=False, type='meanclip')
			self.variancePlot.addItem(tmpVarClipLine)
			self.variancePlot.getAxis('left').setLabel('Variance')


		# set axis
		xLabel = 'time (s)'
		yLabel = 'mV'
		if isPhasePlot:
			xLabel = 'mV'
			yLabel = 'dV/dt'
		self.clipPlot.getAxis('left').setLabel(yLabel)
		self.clipPlot.getAxis('bottom').setLabel(xLabel)

		#
		# store so we can export
		#print('  xTmp:', xTmp.shape)
		#print('  yTmp:', yTmp.shape)
		#print('  yMeanClip:', yMeanClip.shape)
		self.x = xTmp  # 1D
		self.y = yTmp  # 2D
		self.yMean = yMeanClip

		#
		# replot any selected spikes
		self.selectSpike()
		self.selectSpikeList()

	def copyToClipboard(self):
		"""
		Save instead
		Copy to clipboard is not going to work, data is too big
		"""

		numSpikes = self.y.shape[0]

		columns = ['time(ms)', 'meanClip']
		# iterate through spikes
		for i in range(numSpikes):
			columns.append(f'clip_{i}')
		df = pd.DataFrame(columns=columns)

		#print('self.x:', type(self.x), self.x.shape)

		df['time(ms)'] = self.x[0,:]
		df['meanClip'] = self.yMean
		for i in range(numSpikes):
			df[f'clip_{i}'] = self.y[i]

		print(df.head())

		fileName = self.ba.getFileName()
		fileName += '.csv'
		savePath = fileName
		options = QtWidgets.QFileDialog.Options()
		fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,"Save .csv file",
							savePath,"CSV Files (*.csv)", options=options)
		if not fileName:
			return

		logger.info(f'Saving: "{fileName}"')
		df.to_csv(fileName, index=False)

	def selectSpike(self, sDict=None):
		"""
		Leave existing spikes and select one spike with a different color.
		The one spike might not be displayed, then do nothing.
		sDict (dict): NOT USED
		"""

		#logger.info(sDict)

		#if self.ba != sDict['ba']:
		#	return

		if sDict is not None:
			spikeNumber = sDict['spikeNumber']
		else:
			spikeNumber = self.selectedSpike

		x = np.zeros(1) * np.nan
		y = np.zeros(1) * np.nan
		if spikeNumber is not None:
			try:
				x = self.x[spikeNumber]
				y = self.y[spikeNumber]
			except (IndexError) as e:
				pass

		# TODO: Fix this. Not sure how to recycle single spike selection
		#    replot is calling self.clipPlot.clear()
		if self.singleSpikeMultiLine is not None:
			self.clipPlot.removeItem(self.singleSpikeMultiLine)
		self.singleSpikeMultiLine = MultiLine(x, y, self, width=3, allowXAxisDrag=False, forcePenColor='y', type='spike selection')
		self.clipPlot.addItem(self.singleSpikeMultiLine)

	def selectSpikeList(self, sDict=None):
		"""
		Select spikes based on self.selectedSpikeList.
		sDict (dict): NOT USED
		"""
		#logger.info(sDict)

		x = np.zeros(1) * np.nan
		y = np.zeros(1) * np.nan

		if len(self.selectedSpikeList) >0:
			try:
				x = self.x[self.selectedSpikeList]
				y = self.y[self.selectedSpikeList]
			except (IndexError) as e:
				pass
		if self.spikeListMultiLine is not None:
			self.clipPlot.removeItem(self.spikeListMultiLine)
		self.spikeListMultiLine = MultiLine(x, y, self, width=3, allowXAxisDrag=False, forcePenColor='c', type='spike list selection')
		self.clipPlot.addItem(self.spikeListMultiLine)

class MultiLine(pg.QtGui.QGraphicsPathItem):
	"""
	This will display a time-series whole-cell recording efficiently
	It does this by converting the array of points to a QPath

	see: https://stackoverflow.com/questions/17103698/plotting-large-arrays-in-pyqtgraph/17108463#17108463
	"""
	def __init__(self, x, y, detectionWidget, type, width=1, forcePenColor=None, allowXAxisDrag=True):
		"""
		x and y are 2D arrays of shape (Nplots, Nsamples)
		type: (dvdt, vm)
		"""

		self.exportWidgetList = []

		self.x = x
		self.y = y
		self.detectionWidget = detectionWidget
		self.myType = type
		self.allowXAxisDrag = allowXAxisDrag

		self.xDrag = None # if true, user is dragging x-axis, otherwise y-axis
		self.xStart = None
		self.xCurrent = None
		self.linearRegionItem = None

		if len(x.shape) == 2:
			connect = np.ones(x.shape, dtype=bool)
			connect[:,-1] = 0 # don't draw the segment between each trace
			self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect.flatten())
		else:
			self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect='all')
		pg.QtGui.QGraphicsPathItem.__init__(self, self.path)

		doDarkTheme = True
		if forcePenColor is not None:
			penColor = forcePenColor
		elif doDarkTheme:
			penColor = 'w'
		else:
			penColor = 'k'
		#
		if self.myType == 'meanclip':
			penColor = 'r'
			width = 3

		#print('MultiLine penColor:', penColor)
		pen = pg.mkPen(color=penColor, width=width)

		# testing gradient pen
		'''
		cm = pg.colormap.get('CET-L17') # prepare a linear color map
		#cm.reverse()                    # reverse it to put light colors at the top
		pen = cm.getPen( span=(0.0,1.0), width=5 ) # gradient from blue (y=0) to white (y=1)
		'''

		# this works
		self.setPen(pen)

	def shape(self):
		# override because QGraphicsPathItem.shape is too expensive.
		#print(time.time(), 'MultiLine.shape()', pg.QtGui.QGraphicsItem.shape(self))
		return pg.QtGui.QGraphicsItem.shape(self)

	def boundingRect(self):
		#print(time.time(), 'MultiLine.boundingRect()', self.path.boundingRect())
		return self.path.boundingRect()

	def old_mouseClickEvent(self, event):
		if event.button() == QtCore.Qt.RightButton:
			print('mouseClickEvent() right click', self.myType)
			self.contextMenuEvent(event)

	def old_contextMenuEvent(self, event):
		myType = self.myType

		if myType == 'clip':
			print('WARNING: no export for clips, try clicking again')
			return

		'''
		contextMenu = QtWidgets.QMenu()
		exportTraceAction = contextMenu.addAction(f'Export Trace {myType}')
		contextMenu.addSeparator()
		resetAllAxisAction = contextMenu.addAction(f'Reset All Axis')
		resetYAxisAction = contextMenu.addAction(f'Reset Y-Axis')
		#openAct = contextMenu.addAction("Open")
		#quitAct = contextMenu.addAction("Quit")
		#action = contextMenu.exec_(self.mapToGlobal(event.pos()))
		posQPoint = QtCore.QPoint(event.screenPos().x(), event.screenPos().y())
		action = contextMenu.exec_(posQPoint)
		if action is None:
			return
		actionText = action.text()
		if actionText == f'Export Trace {myType}':
			#print('Opening Export Trace Window')

			if self.myType == 'vmFiltered':
				xyUnits = ('Time (sec)', 'Vm (mV)')# todo: pass xMin,xMax to constructor
			elif self.myType == 'dvdtFiltered':
				xyUnits = ('Time (sec)', 'dV/dt (mV/ms)')# todo: pass xMin,xMax to constructor
			elif self.myType == 'meanclip':
				xyUnits = ('Time (ms)', 'Vm (mV)')# todo: pass xMin,xMax to constructor
			else:
				logger.error(f'Unknown myType: "{self.myType}"')
				xyUnits = ('error time', 'error y')

			path = self.detectionWidget.ba.path

			xMin = None
			xMax = None
			if self.myType in ['clip', 'meanclip']:
				xMin, xMax = self.detectionWidget.clipPlot.getAxis('bottom').range
			else:
				xMin, xMax = self.detectionWidget.getXRange()
			#print('  xMin:', xMin, 'xMax:', xMax)

			if self.myType in ['vm', 'dvdt']:
				xMargin = 2 # seconds
			else:
				xMargin = 2

			exportWidget = sanpy.interface.bExportWidget(self.x, self.y,
							xyUnits=xyUnits,
							path=path,
							xMin=xMin, xMax=xMax,
							xMargin = xMargin,
							type=self.myType,
							darkTheme=self.detectionWidget.useDarkStyle)

			exportWidget.myCloseSignal.connect(self.slot_closeChildWindow)
			exportWidget.show()

			self.exportWidgetList.append(exportWidget)
		elif actionText == 'Reset All Axis':
			#print('Reset Y-Axis', self.myType)
			self.detectionWidget.setAxisFull()
		elif actionText == 'Reset Y-Axis':
			#print('Reset Y-Axis', self.myType)
			self.detectionWidget.setAxisFull_y(self.myType)
		else:
			logger.warning(f'action not taken: {action}')
		'''

	def old_slot_closeChildWindow(self, windowPointer):
		#print('closeChildWindow()', windowPointer)
		#print('  exportWidgetList:', self.exportWidgetList)

		idx = self.exportWidgetList.index(windowPointer)
		if idx is not None:
			popedItem = self.exportWidgetList.pop(idx)
			#print('  popedItem:', popedItem)
		else:
			print(' slot_closeChildWindow() did not find', windowPointer)

	def old_mouseDragEvent(self, ev):
		"""
		default is to drag x-axis, use alt_drag for y-axis
		"""
		#print('MultiLine.mouseDragEvent():', type(ev), ev)

		if ev.button() != QtCore.Qt.LeftButton:
			ev.ignore()
			return

		#modifiers = QtWidgets.QApplication.keyboardModifiers()
		#isAlt = modifiers == QtCore.Qt.AltModifier
		isAlt = ev.modifiers() == QtCore.Qt.AltModifier

		#xDrag = not isAlt # x drag is dafault, when alt is pressed, xDrag==False

		# allowXAxisDrag is now used for both x and y
		if not self.allowXAxisDrag:
			ev.accept() # this prevents click+drag of plot
			return

		if ev.isStart():
			self.xDrag = not isAlt
			if self.xDrag:
				self.xStart = ev.buttonDownPos()[0]
				self.linearRegionItem = pg.LinearRegionItem(values=(self.xStart,0), orientation=pg.LinearRegionItem.Vertical)
			else:
				# in y-drag, we need to know (vm, dvdt)
				self.xStart = ev.buttonDownPos()[1]
				self.linearRegionItem = pg.LinearRegionItem(values=(0,self.xStart), orientation=pg.LinearRegionItem.Horizontal)
			#self.linearRegionItem.sigRegionChangeFinished.connect(self.update_x_axis)
			# add the LinearRegionItem to the parent widget (Cannot add to self as it is an item)
			self.parentWidget().addItem(self.linearRegionItem)
		elif ev.isFinish():
			if self.xDrag:
				set_xyBoth = 'xAxis'
			else:
				set_xyBoth = 'yAxis'
			#self.parentWidget().setXRange(self.xStart, self.xCurrent)
			self.detectionWidget.setAxis(self.xStart, self.xCurrent, set_xyBoth=set_xyBoth, whichPlot=self.myType)

			self.xDrag = None
			self.xStart = None
			self.xCurrent = None

			'''
			if self.myType == 'clip':
				if self.xDrag:
					self.clipPlot.setXRange(self.xStart, self.xCurrent, padding=padding)
				else:
					self.clipPlot.setYRange(self.xStart, self.xCurrent, padding=padding)
			else:
				self.parentWidget().removeItem(self.linearRegionItem)
			'''
			self.parentWidget().removeItem(self.linearRegionItem)

			self.linearRegionItem = None

			return

		if self.xDrag:
			self.xCurrent = ev.pos()[0]
			#print('xStart:', self.xStart, 'self.xCurrent:', self.xCurrent)
			self.linearRegionItem.setRegion((self.xStart, self.xCurrent))
		else:
			self.xCurrent = ev.pos()[1]
			#print('xStart:', self.xStart, 'self.xCurrent:', self.xCurrent)
			self.linearRegionItem.setRegion((self.xStart, self.xCurrent))
		ev.accept()

if __name__ == '__main__':
	#path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
	#path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
	path = '/media/cudmore/data/rabbit-ca-transient/Control/220110n_0003.tif.frames/220110n_0003.tif'
	ba = sanpy.bAnalysis(path)

	'''
	detectionClass = sanpy.bDetection()
	print(type(detectionClass))
	detectionClass['dvdtThreshold'] = math.nan #if None then detect only using mvThreshold
	detectionClass['mvThreshold'] = -0 #0.5
	'''

	detectionType = sanpy.bDetection.detectionTypes.mv

	mvThreshold = 0.5 #0
	detectionClass = sanpy.bDetection() # gets default detection class
	detectionClass['detectionType'] = detectionType  # set detection type to ('dvdt', 'vm')
	detectionClass['dvdtThreshold'] = math.nan
	detectionClass['mvThreshold'] = mvThreshold

	ba.spikeDetect(detectionClass=detectionClass)
	#ba.spikeDetect()
	print(ba)

	#sys.exit(1)

	import sys
	app = QtWidgets.QApplication([])
	sc = spikeClips(ba=ba)
	sc.show()
	sys.exit(app.exec_())
