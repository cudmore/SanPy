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
	myHumanName = 'Spike Clips'

	def __init__(self, **kwargs):
		"""
		Args:
			ba (bAnalysis): Not required
		"""
		super().__init__('plotScatter', **kwargs)

		self.clipLines = None
		self.meanClipLine = None

		# makes self.mainWidget and calls show()
		self.pyqtWindow()

		# main layout
		vLayout = QtWidgets.QVBoxLayout()

		#
		# controls
		hLayout2 = QtWidgets.QHBoxLayout()
		#
		self.b1 = QtWidgets.QCheckBox("Respond To Analysis Changes")
		self.b1.setChecked(True)
		self.b1.stateChanged.connect(lambda:self.btnstate(self.b1))
		hLayout2.addWidget(self.b1)

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

	def btnstate(self,b):
		if b.text() == "Respond To Analysis Changes":
			state = b.isChecked()
			self.setRespondToAnalysisChange(state) # inherited
		else:
			logger.warning(f'Did not respond to button "{b.text()}"')

	def plot(self):
		pass

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
		if self.clipLines is not None:
			self.clipPlot.removeItem(self.clipLines)
		if self.meanClipLine is not None:
			self.clipPlot.removeItem(self.meanClipLine)

		#
		# TODO
		# plugins need to respond to x-axis selectioon !!!
		startSec, stopSec = self.getStartStop()
		if startSec is None or stopSec is None:
			startSec = 0
			stopSec = self.ba.sweepX[-1]

		# this returns x-axis in ms
		theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(startSec, stopSec)
		dataPointsPerMs = self.ba.dataPointsPerMs

		# convert clips to 2d ndarray ???
		xTmp = np.array(theseClips_x)
		xTmp /= dataPointsPerMs # pnt to ms
		yTmp = np.array(theseClips)
		self.clipLines = MultiLine(xTmp, yTmp, self, allowXAxisDrag=False, type='clip')
		self.clipPlot.addItem(self.clipLines)

		#print(xTmp.shape) # (num spikes, time)
		self.xMeanClip = xTmp
		if len(self.xMeanClip) > 0:
			self.xMeanClip = np.nanmean(xTmp, axis=0) # xTmp is in ms
		self.yMeanClip = yTmp
		if len(self.yMeanClip) > 0:
			self.yMeanClip = np.nanmean(yTmp, axis=0)
		self.meanClipLine = MultiLine(self.xMeanClip, self.yMeanClip, self, allowXAxisDrag=False, type='meanclip')
		self.clipPlot.addItem(self.meanClipLine)

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
		#
		self.setPen(pg.mkPen(color=penColor, width=width))

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
