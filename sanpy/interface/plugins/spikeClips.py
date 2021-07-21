import numpy as np

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
	myHumanName = 'Spike Clips Plot'

	def __init__(self, **kwargs):
		"""
		Args:
			ba (bAnalysis): Not required
		"""
		super().__init__(**kwargs)

		#self.clipLines = None
		#self.meanClipLine = None

		# makes self.mainWidget and calls show()
		self.pyqtWindow()

		# main layout
		vLayout = QtWidgets.QVBoxLayout()

		#
		# controls
		hLayout2 = QtWidgets.QHBoxLayout()

		# TODO:
		aLabel = QtWidgets.QLabel('Clip Width (ms)')
		self.clipWidth_ms = QtWidgets.QSpinBox()
		hLayout2.addWidget(aLabel)
		hLayout2.addWidget(self.clipWidth_ms)

		self.meanCheckBox = QtWidgets.QCheckBox('Mean Trace (red)')
		self.meanCheckBox.setChecked(True)
		self.meanCheckBox.stateChanged.connect(lambda:self.replot())
		hLayout2.addWidget(self.meanCheckBox)

		self.waterfallCheckBox = QtWidgets.QCheckBox('Waterfall')
		self.waterfallCheckBox.setChecked(False)
		self.waterfallCheckBox.stateChanged.connect(lambda:self.replot())
		hLayout2.addWidget(self.waterfallCheckBox)

		self.phasePlotCheckBox = QtWidgets.QCheckBox('Phase')
		self.phasePlotCheckBox.setChecked(False)
		self.phasePlotCheckBox.stateChanged.connect(lambda:self.replot())
		hLayout2.addWidget(self.phasePlotCheckBox)

		#

		vLayout.addLayout(hLayout2)

		#
		# pyqt graph
		self.view = pg.GraphicsLayoutWidget()
		self.clipPlot = self.view.addPlot(row=0, col=0)
		#self.clipPlot.hideButtons()
		#self.clipPlot.setMenuEnabled(False)
		#self.clipPlot.setMouseEnabled(x=False, y=False)

		vLayout.addWidget(self.view) #, stretch=8)

		# set the layout of the main window
		self.mainWidget.setLayout(vLayout)

		self.replot()

	def replot(self):
		"""
		Replot when analysis changes or file changes
		"""
		self._myReplotClips()
		#
		self.mainWidget.repaint() # update the widget

	'''
	def setAxis(self):
		"""
		(self.startSec, self.stopSec) has been set by sanpyPlugins
		"""
		self.replot()
	'''

	def _myReplotClips(self):
		# remove existing
		self.clipPlot.clear()
		'''if self.clipLines is not None:
			self.clipPlot.removeItem(self.clipLines)
		if self.meanClipLine is not None:
			self.clipPlot.removeItem(self.meanClipLine)
		'''

		#
		# TODO
		# plugins need to respond to x-axis selectioon !!!
		startSec, stopSec = self.getStartStop()
		if startSec is None or stopSec is None:
			startSec = 0
			stopSec = self.ba.sweepX[-1]

		# this returns x-axis in ms
		#_makeSpikeClips
		theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(startSec, stopSec)
		dataPointsPerMs = self.ba.dataPointsPerMs

		# convert clips to 2d ndarray ???
		xTmp = np.array(theseClips_x)
		xTmp /= dataPointsPerMs # pnt to ms
		yTmp = np.array(theseClips)  # mV

		#print(xTmp.shape, yTmp.shape)
		if self.phasePlotCheckBox.isChecked():
			# plot x mV versus y dV/dt
			dvdt = np.zeros((yTmp.shape[0], yTmp.shape[1]-1))  #
			for i in range(dvdt.shape[0]):
				dvdt[i,:] = np.diff(yTmp[i,:])
				# drop first pnt in x

			#
			xTmp = yTmp[:, 1:] # drop first column of mV and swap to x-axis
			yTmp = dvdt
			#print(xTmp.shape, yTmp.shape)

		if self.waterfallCheckBox.isChecked():
			#print(xTmp.shape, yTmp.shape)
			# xTmp and yTmp are 2D with rows/clips and cols/data_pnts
			xMin = np.nanmin(xTmp)
			xMax = np.nanmax(xTmp)
			xRange = xMax - xMin
			xOffset = 0
			yOffset = 0
			xInc = xRange * 0.1 # ms, xInc is 10% of x-range
			yInc = 2 # mV
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
		for i in range(xTmp.shape[0]):
			forcePenColor = cmap.getByIndex(i)
			#print('forcePenColor:', forcePenColor)
			xPlot = xTmp[i,:]
			yPlot = yTmp[i,:]
			tmpClipLines = MultiLine(xPlot, yPlot, self, allowXAxisDrag=False, forcePenColor=forcePenColor, type='clip')
			self.clipPlot.addItem(tmpClipLines)

		if self.meanCheckBox.isChecked():
			#print(xTmp.shape) # (num spikes, time)
			self.xMeanClip = xTmp
			if len(self.xMeanClip) > 0:
				self.xMeanClip = np.nanmean(xTmp, axis=0) # xTmp is in ms
			self.yMeanClip = yTmp
			if len(self.yMeanClip) > 0:
				self.yMeanClip = np.nanmean(yTmp, axis=0)
			tmpMeanClipLine = MultiLine(self.xMeanClip, self.yMeanClip, self, allowXAxisDrag=False, type='meanclip')
			self.clipPlot.addItem(tmpMeanClipLine)

	def selectSpike(self, sDict):
		"""
		Select a spike
		"""
		logger.info(sDict)

		'''
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
		'''

class MultiLine(pg.QtGui.QGraphicsPathItem):
	"""
	This will display a time-series whole-cell recording efficiently
	It does this by converting the array of points to a QPath

	see: https://stackoverflow.com/questions/17103698/plotting-large-arrays-in-pyqtgraph/17108463#17108463
	"""
	def __init__(self, x, y, detectionWidget, type, forcePenColor=None, allowXAxisDrag=True):
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
		width = 1
		if self.myType == 'meanclip':
			penColor = 'r'
			width = 3

		print('MultiLine penColor:', penColor)
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
	path = '/Users/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(path)
	ba.spikeDetect()
	print(ba.numSpikes)

	import sys
	app = QtWidgets.QApplication([])
	sc = spikeClips(ba=ba)
	sys.exit(app.exec_())
