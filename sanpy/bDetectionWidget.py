# Author: Robert H Cudmore
# Date: 20190717

import os, sys
from functools import partial

import numpy as np

#import qdarkstyle

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
#import pyqtgraph.exporters

#from bAnalysis import bAnalysis
import sanpy

# abb trying to get detection widget to look respactable
'''
class bLeftDetectionWidget(QtWidgets.QWidget):
	def __init__(self, mainWindow=None, parent=None):
		super(bLeftDetectionWidget, self).__init__(parent)

		self.mainWindow = mainWindow

		self.buildUI()
'''

class bDetectionWidget(QtWidgets.QWidget):
	def __init__(self, ba=None, mainWindow=None, parent=None):
		"""
		ba: bAnalysis object
		"""

		super(bDetectionWidget, self).__init__(parent)

		# all widgets should inherit this
		#self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))

		self.ba = ba
		self.myMainWindow = mainWindow

		self.mySetTheme()

		self.dvdtLines = None
		self.vmLines = None
		self.clipLines = None
		self.meanClipLine = None

		self.myPlotList = []

		# a list of possible x/y plots (overlay over dvdt and Vm)
		self.myPlots = [
			{
				'humanName': 'Threshold Sec (dV/dt)',
				'x': 'thresholdSec',
				'y': 'thresholdVal_dvdt',
				'convertx_tosec': False, # some stats are in points, we need to convert to seconds
				'color': 'r',
				'styleColor': 'color: red',
				'symbol': 'o',
				'plotOn': 'dvdt', # which plot to overlay (vm, dvdt)
				'plotIsOn': True,
			},
			{
				'humanName': 'AP Peak (mV)',
				'x': 'peakSec',
				'y': 'peakVal',
				'convertx_tosec': False,
				'color': 'r',
				'styleColor': 'color: red',
				'symbol': 'o',
				'plotOn': 'vm',
				'plotIsOn': True,
			},
			{
				'humanName': 'Pre AP Min (mV)',
				'x': 'preMinPnt',
				'y': 'preMinVal',
				'convertx_tosec': True,
				'color': 'g',
				'styleColor': 'color: green',
				'symbol': 'o',
				'plotOn': 'vm',
				'plotIsOn': False,
			},
			{
				'humanName': 'Post AP Min (mV)',
				'x': 'postMinPnt',
				'y': 'postMinVal',
				'convertx_tosec': True,
				'color': 'b',
				'styleColor': 'color: blue',
				'symbol': 'o',
				'plotOn': 'vm',
				'plotIsOn': False,
			},
		]

		self.buildUI()

	'''
	def eventFilter(self, target, event : QtCore.QEvent):
		if event.type() == QtCore.QEvent.MouseButtonPress:
			if event.button() == QtCore.Qt.RightButton:
				print("Right button clicked")
		return False
	'''

	def mySetTheme(self):
		if self.myMainWindow is not None and self.myMainWindow.useDarkStyle:
			pg.setConfigOption('background', 'k')
			pg.setConfigOption('foreground', 'w')
			self.useDarkStyle = True
		else:
			pg.setConfigOption('background', 'w')
			pg.setConfigOption('foreground', 'k')
			self.useDarkStyle = False

	def detect(self, dvdtValue, minSpikeVm):
		"""
		detect spikes
		"""

		if self.ba is None:
			return

		if self.ba.loadError:
			print('bDetectionWidget.detect() did not spike detect because the file was not loaded (may be corrupt .abf file?)')
			return

		self.updateStatusBar(f'Detecting spikes dvdt:{dvdtValue} minVm:{minSpikeVm}')

		self.ba.spikeDetect(dVthresholdPos=dvdtValue, minSpikeVm=minSpikeVm)

		if self.ba.numSpikes == 0:
			msg = QtWidgets.QMessageBox()
			msg.setIcon(QtWidgets.QMessageBox.Warning)
			msg.setText("No Spikes Detected")
			msg.setInformativeText('dV/dt Threshold: ' + str(dvdtValue) + '\r' + ' Vm Threshold (mV): '  + str(minSpikeVm))
			msg.setWindowTitle("No Spikes Detected")
			retval = msg.exec_()

		self.replot() # replot statistics over traces

		self.refreshClips() # replot clips

		if self.myMainWindow is not None:
			self.myMainWindow.mySignal('detect') # signal to main window so it can update (file list, scatter plot)

		#QtCore.QCoreApplication.processEvents()
		self.updateStatusBar(f'Detected {self.ba.numSpikes} spikes')

	def save(self, alsoSaveTxt=False):
		"""
		Prompt user for filename and save both xlsx and txt
		Save always defaults to data folder
		"""
		print('=== bDetectionWidget.save')
		if self.ba is None or self.ba.numSpikes==0:
			print('   no analysis ???')
			return
		xMin, xMax = self.getXRange()
		#print('	xMin:', xMin, 'xMax:', xMax)

		filePath, fileName = os.path.split(os.path.abspath(self.ba.file))
		fileBaseName, extension = os.path.splitext(fileName)
		excelFileName = os.path.join(filePath, fileBaseName + '.xlsx')

		print('Asking user for file name to save...')
		savefile, tmp = QtGui.QFileDialog.getSaveFileName(self, 'Save File', excelFileName)

		print('	savefile:', savefile)
		#print('tmp:', tmp)

		if len(savefile) > 0:
			self.ba.saveReport(savefile, xMin, xMax, alsoSaveTxt=alsoSaveTxt)
			if self.myMainWindow is not None:
				self.myMainWindow.mySignal('saved')
		else:
			print('no file saved')

	def getXRange(self):
		"""
		Get the current range of X-Axis
		"""
		rect = self.derivPlot.viewRect() # get xaxis
		xMin = rect.left()
		xMax = rect.right()
		return xMin, xMax

	def _setAxis(self, start, stop, set_xyBoth='xAxis', whichPlot='vm'):
		"""
		Shared by (setAxisFull, setAxis)
		"""
		# make sure start/stop are in correct order and swap if necc.
		if stop<start:
			tmp = start
			start = stop
			stop = tmp

		#print('bDetectionWidget.setAxis() start:', start, 'stop:', stop)

		padding = 0
		if set_xyBoth == 'xAxis':
			self.derivPlot.setXRange(start, stop, padding=padding) # linked to Vm
		if set_xyBoth == 'yAxis':
			if whichPlot == 'dvdt':
				self.derivPlot.setYRange(start, stop) # linked to Vm
			elif whichPlot == 'vm':
				self.vmPlot.setYRange(start, stop) # linked to Vm
			else:
				print('bDetectionWidget._setAxis() did not understand whichPlot:', whichPlot)

		# update detection toolbar
		if set_xyBoth == 'xAxis':
			self.detectToolbarWidget.startSeconds.setValue(start)
			self.detectToolbarWidget.startSeconds.repaint()
			self.detectToolbarWidget.stopSeconds.setValue(stop)
			self.detectToolbarWidget.stopSeconds.repaint()
		#else:
		#	print('todo: add interface for y range in bDetectionWidget._setAxis()')

		if set_xyBoth == 'xAxis':
			self.refreshClips(start, stop)

		return start, stop

	def setAxisFull_y(self, thisAxis):
		"""
		thisAxis: (vm, dvdt)
		"""
		# y-axis is NOT shared
		# dvdt
		if thisAxis == 'dvdt':
			top = np.nanmax(self.ba.filteredDeriv)
			bottom = np.nanmin(self.ba.filteredDeriv)
			start, stop = self._setAxis(bottom, top,
									set_xyBoth='yAxis',
									whichPlot='dvdt')
		# vm
		if thisAxis == 'vm':
			top = np.nanmax(self.ba.abf.sweepY)
			bottom = np.nanmin(self.ba.abf.sweepY)
			start, stop = self._setAxis(bottom, top,
									set_xyBoth='yAxis',
									whichPlot='vm')
	def setAxisFull(self):

		if self.ba is None:
			return

		# x-axis is shared between (dvdt, vm)
		start = 0
		stop = self.ba.abf.sweepX[-1]
		start, stop = self._setAxis(start, stop, set_xyBoth='xAxis')

		# y-axis is NOT shared
		# dvdt
		top = np.nanmax(self.ba.filteredDeriv)
		bottom = np.nanmin(self.ba.filteredDeriv)
		start, stop = self._setAxis(bottom, top,
									set_xyBoth='yAxis',
									whichPlot='dvdt')
		# vm
		top = np.nanmax(self.ba.abf.sweepY)
		bottom = np.nanmin(self.ba.abf.sweepY)
		start, stop = self._setAxis(bottom, top,
									set_xyBoth='yAxis',
									whichPlot='vm')

		# todo: make this a signal, with slot in main window
		if self.myMainWindow is not None:
			self.myMainWindow.mySignal('set full x axis')

	def setAxis(self, start, stop, set_xyBoth='xAxis', whichPlot='vm'):
		"""
		set_xyBoth: (xAxis, yAxis, Both)
		whichPlot: (dvdt, vm)
		"""
		start, stop = self._setAxis(start, stop, set_xyBoth=set_xyBoth, whichPlot=whichPlot)
		if set_xyBoth == 'xAxis':
			if self.myMainWindow is not None:
				self.myMainWindow.mySignal('set x axis', data=[start,stop])
		# no nned to emit change in y-axis, no other widgets change
		'''
		elif set_xyBoth == 'yAxis':
			# todo: this needs to know which plot
			if self.myMainWindow is not None:
				self.myMainWindow.mySignal('set y axis', data=[start,stop])
		'''
		#elif set_xyBoth == 'both':
		#	self.myMainWindow.mySignal('set y axis', data=[start,stop])

	def switchFile(self, path):
		"""
		set self.ba to new bAnalysis object ba

		Can fail if .abf file is corrupt
		"""
		print('=== bDetectionWidget.switchFile() path:', path)

		if self.ba is not None and self.ba.file == path:
			print('bDetectionWidget is already displaying file:', path)
			return

		if not os.path.isfile(path):
			print('error: bDetectionWidget.switchFile() did not find file:', path)
			return

		self.updateStatusBar(f'Loading file {path}')

		# make analysis object from file
		self.ba = sanpy.bAnalysis(file=path) # loads abf file

		if self.ba.loadError:
			# happend when .abf file is corrupt
			pass
		else:
			self.ba.getDerivative(medianFilter=5) # derivative

		#remove vm/dvdt/clip items (even when abf file is corrupt)
		if self.dvdtLines is not None:
			self.derivPlot.removeItem(self.dvdtLines)
		if self.vmLines is not None:
			self.vmPlot.removeItem(self.vmLines)
		if self.clipLines is not None:
			self.clipPlot.removeItem(self.clipLines)

		# abb 20201009
		if self.ba.loadError:
			self.replot()
			print('bDetectionWidget.switchFile() did not switch file, the .abf file may be corrupt:', path)
			self.updateStatusBar(f'Error loading file {path}')
			return None

		self.updateStatusBar(f'Plotting file {path}')

		# cancel spike selection
		self.selectSpike(None)

		# set full axis
		#self.setAxisFull()

		# update lines
		self.dvdtLines = MultiLine(self.ba.abf.sweepX, self.ba.filteredDeriv,
							self, type='dvdt')
		self.derivPlot.addItem(self.dvdtLines)

		self.vmLines = MultiLine(self.ba.abf.sweepX, self.ba.abf.sweepY,
							self, type='vm')
		self.vmPlot.addItem(self.vmLines)

		# remove and re-add plot overlays
		for idx, plot in enumerate(self.myPlots):
			plotItem = self.myPlotList[idx]
			if plot['plotOn'] == 'vm':
				self.vmPlot.removeItem(plotItem)
				self.vmPlot.addItem(plotItem)
			elif plot['plotOn'] == 'dvdt':
				self.derivPlot.removeItem(plotItem)
				self.derivPlot.addItem(plotItem)

		# set full axis
		self.setAxisFull()

		# single spike selection
		self.vmPlot.removeItem(self.mySingleSpikeScatterPlot)
		self.vmPlot.addItem(self.mySingleSpikeScatterPlot)

		#
		# critical
		self.replot()

		#
		# set sweep to 0

		self.updateStatusBar(f'Done loading file {path}')

	def updateStatusBar(self, text):
		if self.myMainWindow is not None:
			self.myMainWindow.updateStatusBar(text)

	def on_scatterClicked(self, scatter, points):
		print('scatterClicked() scatter:', scatter, points)

	def togglePlot(self, idx, on):
		"""
		Toggle overlay of stats like spike peak.

		idx: overlay index into self.myPlots
		on: boolean
		"""

		#print('togglePlot()', idx, on)

		# toggle the plot on/off
		self.myPlots[idx]['plotIsOn'] = on

		#We do not want to setData as it seems to trash x/y data if it is not specified
		#We just want to set the pen/size in order to show/hide
		plot = self.myPlots[idx]
		if on:
			#self.myPlotList[idx].setData(pen=pg.mkPen(width=5, color=plot['color'], symbol=plot['symbol']), size=2)
			self.myPlotList[idx].setPen(pg.mkPen(width=5, color=plot['color'], symbol=plot['symbol']))
			self.myPlotList[idx].setSize(2)
		else:
			#self.myPlotList[idx].setData(pen=pg.mkPen(width=0, color=plot['color'], symbol=plot['symbol']), size=0)
			self.myPlotList[idx].setPen(pg.mkPen(width=0, color=plot['color'], symbol=plot['symbol']))
			self.myPlotList[idx].setSize(0)

	def replot(self):

		if self.ba is None:
			return

		for idx, plot in enumerate(self.myPlots):
			xPlot, yPlot = self.ba.getStat(plot['x'], plot['y'])
			if plot['convertx_tosec']:
				xPlot = [self.ba.pnt2Sec_(x) for x in xPlot] # convert pnt to sec

			self.myPlotList[idx].setData(x=xPlot, y=yPlot)

			self.togglePlot(idx, plot['plotIsOn'])

		# update label with number of spikes detected
		numSpikesStr = str(self.ba.numSpikes)
		self.detectToolbarWidget.numSpikesLabel.setText('Number of Spikes Detected: ' + numSpikesStr)
		self.detectToolbarWidget.numSpikesLabel.repaint()

	def selectSpike(self, spikeNumber):
		if spikeNumber is not None:
			print('bDetectionWIdget.selectSpike() spikeNumber:', spikeNumber)
		# we will always use self.ba peak
		if spikeNumber is None:
			x = None
			y = None
		else:
			xPlot, yPlot = self.ba.getStat('peakSec', 'peakVal')
			x = [xPlot[spikeNumber]]
			y = [yPlot[spikeNumber]]
		self.mySingleSpikeScatterPlot.setData(x=x, y=y)

	def refreshClips(self, xMin=None, xMax=None):
		if self.ba is None:
			return

		if self.view.getItem(2,0) is None:
			# clips are not being displayed
			return

		# remove existing
		if self.clipLines is not None:
			self.clipPlot.removeItem(self.clipLines)
		if self.meanClipLine is not None:
			self.clipPlot.removeItem(self.meanClipLine)

		theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(xMin, xMax)

		# convert clips to 2d ndarray ???
		xTmp = np.array(theseClips_x)
		yTmp = np.array(theseClips)
		self.clipLines = MultiLine(xTmp, yTmp, self, allowXAxisDrag=False, type='clip')
		self.clipPlot.addItem(self.clipLines)

		#print(xTmp.shape) # (num spikes, time)
		self.xMeanClip = np.nanmean(xTmp, axis=0)
		self.yMeanClip = np.nanmean(yTmp, axis=0)
		self.meanClipLine = MultiLine(self.xMeanClip, self.yMeanClip, self, allowXAxisDrag=False, type='meanclip')
		self.clipPlot.addItem(self.meanClipLine)

	def toggle_scatter(self, on):
		"""
		toggle scatter plot in parent (e.g. xxx)
		"""
		if self.myMainWindow is not None:
			self.myMainWindow.toggleStatisticsPlot(on)

	def toggle_dvdt(self, on):
		"""
		toggle dv/dt plot on/off
		"""
		if on:
			self.derivPlot.show()
		else:
			self.derivPlot.hide()

	def toggle_vm(self, on):
		"""
		toggle vm plot on/off
		"""
		if on:
			self.vmPlot.show()
		else:
			self.vmPlot.hide()

	def toggleClips(self, on):
		"""
		toggle clips plot on/off
		"""
		if on:
			if self.view.getItem(2,0) is None:
				self.clipPlot = self.view.addPlot(row=2, col=0)
				self.refreshClips() # refresh if they exist (e.g. analysis has been done)
		else:
			self.view.removeItem(self.clipPlot)

	def buildUI(self):
		# left is toolbar, right is PYQtGraph (self.view)
		self.myHBoxLayout_detect = QtWidgets.QHBoxLayout(self)

		# detection widget toolbar
		# abb 20201110, switching over to a better layout
		#self.detectToolbarWidget = myDetectToolbarWidget(self.myPlots, self)
		#self.myHBoxLayout_detect.addLayout(self.detectToolbarWidget, stretch=1) # stretch=10, not sure on the units???
		self.detectToolbarWidget = myDetectToolbarWidget2(self.myPlots, self)
		self.myHBoxLayout_detect.addWidget(self.detectToolbarWidget, stretch=1) # stretch=10, not sure on the units???

		#print('bDetectionWidget.buildUI() building pg.GraphicsLayoutWidget')
		self.view = pg.GraphicsLayoutWidget()

		#self.view.scene().sigMouseClicked.connect(self.slot_dvdtMouseReleased)

		# works but does not stick
		#self.view.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
		self.view.show()

		self.derivPlot = self.view.addPlot(row=0, col=0)
		self.vmPlot = self.view.addPlot(row=1, col=0)
		self.clipPlot = self.view.addPlot(row=2, col=0)

		# does not have setStyleSheet
		#self.derivPlot.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))

		# hide the little 'A' button to rescale axis
		self.derivPlot.hideButtons()
		self.vmPlot.hideButtons()
		self.clipPlot.hideButtons()

		# turn off right-click menu
		self.derivPlot.setMenuEnabled(False)
		self.vmPlot.setMenuEnabled(False)
		self.clipPlot.setMenuEnabled(False)

		# link x-axis of deriv and vm
		self.derivPlot.setXLink(self.vmPlot)
		self.vmPlot.setXLink(self.derivPlot)

		# turn off x/y dragging of deriv and vm
		self.derivPlot.setMouseEnabled(x=False, y=False)
		self.vmPlot.setMouseEnabled(x=False, y=False)
		self.clipPlot.setMouseEnabled(x=False, y=False)

		self.toggleClips(False)

		# add all overlaid scatter plots
		self.myPlotList = [] # list of pg.ScatterPlotItem
		for idx, plot in enumerate(self.myPlots):
			color = plot['color']
			symbol = plot['symbol']
			myScatterPlot = pg.ScatterPlotItem(pen=pg.mkPen(width=5, color=color), symbol=symbol, size=2)
			myScatterPlot.setData(x=[], y=[]) # start empty
			myScatterPlot.sigClicked.connect(self.on_scatterClicked)

			self.myPlotList.append(myScatterPlot)

			# add plot to pyqtgraph
			if plot['plotOn'] == 'vm':
				self.vmPlot.addItem(myScatterPlot)
			elif plot['plotOn'] == 'dvdt':
				self.derivPlot.addItem(myScatterPlot)

		# single spike selection
		color = 'c'
		symbol = 'o'
		self.mySingleSpikeScatterPlot = pg.ScatterPlotItem(pen=pg.mkPen(width=5, color=color), symbol=symbol, size=2)
		self.vmPlot.addItem(self.mySingleSpikeScatterPlot)

		# axis labels
		self.derivPlot.getAxis('left').setLabel('dV/dt')
		self.vmPlot.getAxis('left').setLabel('mV')
		self.vmPlot.getAxis('bottom').setLabel('Seconds')

		self.replot()

		#
		#print('bDetectionWidget.buildUI() adding view to myHBoxLayout_detect')
		self.myHBoxLayout_detect.addWidget(self.view, stretch=8) # stretch=10, not sure on the units???

		#print('bDetectionWidget.buildUI() done')

	'''
	def slot_dvdtMouseReleased(self, event):
		print('slot_dvdtMouseReleased() event:', event)
		print('  event.buttons()', event.buttons())
		pos = event.pos()
		items = self.view.scene().items(pos)
		print('  items:', items)
	'''

	def old_myPrint(self):
		"""
		save the vmPlot to a file????
		"""
		print('bDetectionWidget.myPrint()  -->>  NOT IMPLEMENTED')
		return

		# this does not do svg
		#exporter = pg.exporters.ImageExporter(self.vmPlot)

		'''
		exporter = myImageExporter(self.vmPlot)
		exporter.parameters()['width'] = 1000   # (note this also affects height parameter)
		filename = '/Users/cudmore/Desktop/myExport.png'
		'''

		exporter = pg.exporters.SVGExporter(self.vmPlot)
		# macOs
		#filename = '/Users/cudmore/Desktop/myExport.svg'
		# linux
		filename_svg = '/home/cudmore/Desktop/myExport.svg'
		filename_png = '/home/cudmore/Desktop/myExport.png'

		try:
			print('  myPrint() saving file', filename_svg)
			exporter.export(filename_svg)
		except (FileNotFoundError) as e:
			print('exception:', e)

		print('  myPrint() saving file', filename_png)
		exporter.export(filename_png)
		print('   done')

class myImageExporter(ImageExporter):
	def __init__(self, item):
		pg.exporters.ImageExporter.__init__(self, item)
		print('QtGui.QImageWriter.supportedImageFormats():', QtGui.QImageWriter.supportedImageFormats())

	def widthChanged(self):
		sr = self.getSourceRect()
		ar = float(sr.height()) / sr.width()
		myHeight = int(self.params['width'] * ar)
		self.params.param('height').setValue(myHeight, blockSignal=self.heightChanged)

	def heightChanged(self):
		sr = self.getSourceRect()
		ar = float(sr.width()) / sr.height()
		myWidth = int(self.params['height'] * ar)
		self.params.param('width').setValue(myWidth, blockSignal=self.widthChanged)

class MultiLine(pg.QtGui.QGraphicsPathItem):
	"""
	This will display a time-series whole-cell recording efficiently
	It does this by converting the array of points to a QPath

	see: https://stackoverflow.com/questions/17103698/plotting-large-arrays-in-pyqtgraph/17108463#17108463
	"""
	def __init__(self, x, y, detectionWidget, type, allowXAxisDrag=True):
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

		# holy shit, this is bad, without this the app becomes non responsive???
		# if width > 1.0 then this whole app STALLS
		# default heme
		#self.setPen(pg.mkPen(color='k', width=1))
		# dark theme
		if self.detectionWidget.myMainWindow is None:
			penColor = 'k'
		else:
			if self.detectionWidget.myMainWindow.useDarkStyle:
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

	def mouseClickEvent(self, event):
		if event.button() == QtCore.Qt.RightButton:
			print('mouseClickEvent() right click', self.myType)
			self.contextMenuEvent(event)

	def contextMenuEvent(self, event):
		myType = self.myType

		if myType == 'clip':
			print('WARNING: no export for clips, try clicking again')
			return

		contextMenu = QtWidgets.QMenu()
		exportTraceAction = contextMenu.addAction(f'Export Trace {myType}')
		contextMenu.addSeparator()
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
			print('Opening Export Trace Window')

			if self.myType == 'vm':
				xyUnits = ('Time (sec)', 'Vm (mV)')# todo: pass xMin,xMax to constructor
			elif self.myType == 'dvdt':
				xyUnits = ('Time (sec)', 'dV/dt')# todo: pass xMin,xMax to constructor
			elif self.myType == 'meanclip':
				xyUnits = ('Time (sec)', 'Vm (mV)')# todo: pass xMin,xMax to constructor

			path = self.detectionWidget.ba.file

			xMin = None
			xMax = None
			if self.myType in ['clip', 'meanclip']:
				xMin, xMax = self.detectionWidget.clipPlot.getAxis('bottom').range
			else:
				xMin, xMax = self.detectionWidget.getXRange()
			print('  xMin:', xMin, 'xMax:', xMax)

			exportWidget = sanpy.bExportWidget(self.x, self.y,
							xyUnits=xyUnits,
							path=path,
							xMin=xMin, xMax=xMax,
							darkTheme=self.detectionWidget.useDarkStyle)

			exportWidget.myCloseSignal.connect(self.slot_closeChildWindow)
			exportWidget.show()

			self.exportWidgetList.append(exportWidget)
		elif actionText == 'Reset Y-Axis':
			print('Reset Y-Axis', self.myType)
			self.detectionWidget.setAxisFull_y(self.myType)
		else:
			print('  action not taken:', action)

	def slot_closeChildWindow(self, windowPointer):
		#print('closeChildWindow()', windowPointer)
		#print('  exportWidgetList:', self.exportWidgetList)

		idx = self.exportWidgetList.index(windowPointer)
		if idx is not None:
			popedItem = self.exportWidgetList.pop(idx)
			#print('  popedItem:', popedItem)
		else:
			print(' slot_closeChildWindow() did not find', windowPointer)

	def mouseDragEvent(self, ev):
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

class myDetectToolbarWidget2(QtWidgets.QWidget):
	def __init__(self, myPlots, detectionWidget, parent=None):
		super(myDetectToolbarWidget2, self).__init__(parent)

		self.myPlots = myPlots
		self.detectionWidget = detectionWidget # parent detection widget
		self.buildUI()

	def sweepSelectionChange(self,i):
		print('sweepSelectionChange() i:', i)
		'''
		print "Items in the list are :"

		for count in range(self.cb.count()):
			print self.cb.itemText(count)
		'''
		sweepNumber = int(self.cb.currentText())
		print('	sweep number:', sweepNumber)

	@QtCore.pyqtSlot()
	def on_start_stop(self):
		#print('myDetectToolbarWidget.on_start_stop()')
		start = self.startSeconds.value()
		stop = self.stopSeconds.value()
		#print('	start:', start, 'stop:', stop)
		self.detectionWidget.setAxis(start, stop)

	@QtCore.pyqtSlot()
	def on_button_click(self, name):
		print('=== myDetectToolbarWidget.on_button_click() name:', name)

		modifiers = QtWidgets.QApplication.keyboardModifiers()
		isShift = modifiers == QtCore.Qt.ShiftModifier

		if name == 'Detect dV/dt':
			dvdtValue = self.dvdtThreshold.value()
			minSpikeVm = self.minSpikeVm.value()
			#print('	dvdtValue:', dvdtValue)
			#print('	minSpikeVm:', minSpikeVm)
			self.detectionWidget.detect(dvdtValue, minSpikeVm)

		elif name =='Detect mV':
			minSpikeVm = self.minSpikeVm.value()
			#print('	minSpikeVm:', minSpikeVm)
			# passing dvdtValue=None we will detect suing minSpikeVm
			dvdtValue = None
			#print('	dvdtValue:', dvdtValue)
			#print('	minSpikeVm:', minSpikeVm)
			self.detectionWidget.detect(dvdtValue, minSpikeVm)

		elif name == 'Reset All Axes':
			self.detectionWidget.setAxisFull()

		elif name == 'Save Spike Report':
			print('isShift:', isShift)
			self.detectionWidget.save(alsoSaveTxt=isShift)

	def on_check_click(self, checkbox, idx):
		isChecked = checkbox.isChecked()
		print('on_check_click() text:', checkbox.text(), 'isChecked:', isChecked, 'idx:', idx)
		if idx == 'Clips':
			self.detectionWidget.toggleClips(isChecked)
		elif idx == 'dV/dt':
			self.detectionWidget.toggle_dvdt(isChecked)
		elif idx == 'Scatter':
			self.detectionWidget.toggle_scatter(isChecked)
		#elif idx == 'Show Vm':
		#	self.detectionWidget.toggle_vm(isChecked)
		else:
			# assuming idx is int !!!
			self.detectionWidget.togglePlot(idx, isChecked)

	def buildUI(self):
		#self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))

		myPath = os.path.dirname(os.path.abspath(__file__))

		'''
		mystylesheet_css = os.path.join(myPath, 'css', 'mystylesheet.css')
		if os.path.isfile(mystylesheet_css):
			with open(mystylesheet_css) as f:
				myStyleSheet = f.read()
		'''

		self.setFixedWidth(330)
		self.mainLayout = QtWidgets.QVBoxLayout(self)
		self.mainLayout.setAlignment(QtCore.Qt.AlignTop)

		#
		# sweeps
		sweepLayout = QtWidgets.QHBoxLayout(self)

		sweepLabel = QtWidgets.QLabel('Sweep')
		sweepLayout.addWidget(sweepLabel)

		sweeps = [0,1,2,3,4]
		self.cb = QtWidgets.QComboBox()
		#self.cb.addItems(sweeps)
		for sweep in sweeps:
			self.cb.addItem(str(sweep))
		self.cb.currentIndexChanged.connect(self.sweepSelectionChange)
		sweepLayout.addWidget(self.cb)

		# finalize
		self.mainLayout.addLayout(sweepLayout)

		#
		# detection parameters group
		detectionGroupBox = QtWidgets.QGroupBox('Detect Parameters')
		#detectionGroupBox.setStyleSheet(myStyleSheet)

		detectionGridLayout = QtWidgets.QGridLayout()

		buttonName = 'Detect dV/dt'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Detect Spikes Using dV/dt Threshold')
		button.clicked.connect(partial(self.on_button_click,buttonName))

		row = 0
		rowSpan = 1
		columnSpan = 2
		detectionGridLayout.addWidget(button, row, 0, rowSpan, columnSpan)

		self.dvdtThreshold = QtWidgets.QDoubleSpinBox()
		self.dvdtThreshold.setMinimum(-1e6)
		self.dvdtThreshold.setMaximum(+1e6)
		self.dvdtThreshold.setValue(50)
		detectionGridLayout.addWidget(self.dvdtThreshold, row, 2, rowSpan, columnSpan)

		row += 1
		rowSpan = 1
		columnSpan = 2
		buttonName = 'Detect mV'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Detect Spikes Using Vm Threshold')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		detectionGridLayout.addWidget(button, row, 0, rowSpan, columnSpan)

		# Vm Threshold (mV)
		#minSpikeVmLabel = QtWidgets.QLabel('Vm Threshold (mV)')
		#self.addWidget(minSpikeVmLabel, row, 1)

		#row += 1
		self.minSpikeVm = QtWidgets.QDoubleSpinBox()
		self.minSpikeVm.setMinimum(-1e6)
		self.minSpikeVm.setMaximum(+1e6)
		self.minSpikeVm.setValue(-20)
		detectionGridLayout.addWidget(self.minSpikeVm, row, 2, rowSpan, columnSpan)

		# start/stop seconds
		row += 1
		startSeconds = QtWidgets.QLabel('From (Sec)')
		detectionGridLayout.addWidget(startSeconds, row, 0)
		#
		#row += 1
		self.startSeconds = QtWidgets.QDoubleSpinBox()
		self.startSeconds.setMinimum(-1e6)
		self.startSeconds.setMaximum(+1e6)
		self.startSeconds.setKeyboardTracking(False)
		self.startSeconds.setValue(0)
		self.startSeconds.valueChanged.connect(self.on_start_stop)
		#self.startSeconds.editingFinished.connect(self.on_start_stop)
		detectionGridLayout.addWidget(self.startSeconds, row, 1)
		#
		stopSeconds = QtWidgets.QLabel('To (Sec)')
		detectionGridLayout.addWidget(stopSeconds, row, 2)

		self.stopSeconds = QtWidgets.QDoubleSpinBox()
		self.stopSeconds.setMinimum(-1e6)
		self.stopSeconds.setMaximum(+1e6)
		self.stopSeconds.setKeyboardTracking(False)
		self.stopSeconds.setValue(0)
		self.stopSeconds.valueChanged.connect(self.on_start_stop)
		#self.stopSeconds.editingFinished.connect(self.on_start_stop)
		detectionGridLayout.addWidget(self.stopSeconds, row, 3)

		# always the last row
		row += 1
		self.numSpikesLabel = QtWidgets.QLabel('Number of Spikes Detected: None')
		#self.numSpikesLabel.setObjectName('numSpikesLabel')
		tmpRowSpan = 1
		tmpColSpan = 4
		detectionGridLayout.addWidget(self.numSpikesLabel, row, 0, tmpRowSpan, tmpColSpan) # columnSpan=2 does not work?

		# finalize
		detectionGroupBox.setLayout(detectionGridLayout)
		self.mainLayout.addWidget(detectionGroupBox)

		#
		# save button (has its own row in mainLayout VBoxLayout)
		buttonName = 'Save Spike Report'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Save Detected Spikes to Excel file')
		button.setStyleSheet("background-color: green")
		button.clicked.connect(partial(self.on_button_click,buttonName))
		self.mainLayout.addWidget(button)

		#
		# display  group
		displayGroupBox = QtWidgets.QGroupBox('Display')
		#displayGroupBox.setStyleSheet(myStyleSheet)

		displayGridLayout = QtWidgets.QGridLayout()

		row = 0
		buttonName = 'Reset All Axes'
		button = QtWidgets.QPushButton(buttonName)
		#button.setToolTip('Detect Spikes')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		displayGridLayout.addWidget(button, row, 0)

		# a number of stats that will get overlaid
		row += 1
		for idx, plot in enumerate(self.myPlots):
			humanName = plot['humanName']
			isChecked = plot['plotIsOn']
			styleColor = plot['styleColor']
			checkbox = QtWidgets.QCheckBox(humanName)
			checkbox.setChecked(isChecked)
			#checkbox.setStyleSheet(styleColor) # looks really ugly
			#checkbox.stateChanged.connect(lambda:self.on_check_click(checkbox))
			checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,idx))
			col = 0
			if humanName == 'Post AP Min (mV)':
				col = 1
			displayGridLayout.addWidget(checkbox, row, col)
			if humanName == 'Pre AP Min (mV)':
				# don't increment row, we are in col = 1
				pass
			else:
				row += 1

		# finalize
		displayGroupBox.setLayout(displayGridLayout)
		self.mainLayout.addWidget(displayGroupBox)

		#
		# plots  group
		plotGroupBox = QtWidgets.QGroupBox('Plots')
		#plotGroupBox.setStyleSheet(myStyleSheet)

		plotGridLayout = QtWidgets.QGridLayout()

		# add widgets
		row = 0
		col = 0
		show_dvdt_checkbox = QtWidgets.QCheckBox('dV/dt')
		show_dvdt_checkbox.setChecked(True)
		show_dvdt_checkbox.stateChanged.connect(partial(self.on_check_click,show_dvdt_checkbox,'dV/dt'))
		plotGridLayout.addWidget(show_dvdt_checkbox, row, col)

		row = 0
		col = 1
		checkbox = QtWidgets.QCheckBox('Clips')
		checkbox.setChecked(False)
		checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Clips'))
		plotGridLayout.addWidget(checkbox, row, col)

		row = 0
		col = 2
		checkbox = QtWidgets.QCheckBox('Scatter')
		checkbox.setChecked(True)
		checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Scatter'))
		plotGridLayout.addWidget(checkbox, row, col)

		# finalize
		plotGroupBox.setLayout(plotGridLayout)
		self.mainLayout.addWidget(plotGroupBox)

#class myDetectToolbarWidget(QtWidgets.QVBoxLayout):
class myDetectToolbarWidget(QtWidgets.QGridLayout):

	def __init__(self, myPlots, detectionWidget, parent=None):
		"""
		myPlots is a list of dict describing each x/y plot (on top of vm and/or dvdt)
		"""

		super(myDetectToolbarWidget, self).__init__(parent)

		self.detectionWidget = detectionWidget # parent detection widget

		# this does not work
		#self.setMaximumWidth(22)

		self.setAlignment(QtCore.Qt.AlignTop)

		row = 0

		# sweeps
		sweepLabel = QtWidgets.QLabel('Sweep')
		self.addWidget(sweepLabel, row, 0)

		sweeps = [0,1,2,3,4]
		self.cb = QtWidgets.QComboBox()
		#self.cb.addItems(sweeps)
		for sweep in sweeps:
			self.cb.addItem(str(sweep))
		self.cb.currentIndexChanged.connect(self.sweepSelectionChange)
		self.addWidget(self.cb, row, 1)

		row += 1

		buttonName = 'Detect dV/dt'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Detect Spikes Using dV/dt Threshold')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		self.addWidget(button, row, 0)

		#dvdtLabel = QtWidgets.QLabel('dV/dt Theshold')
		#self.addWidget(dvdtLabel, row, 1)

		self.dvdtThreshold = QtWidgets.QDoubleSpinBox()
		self.dvdtThreshold.setMinimum(-1e6)
		self.dvdtThreshold.setMaximum(+1e6)
		self.dvdtThreshold.setValue(50)
		self.addWidget(self.dvdtThreshold, row, 1)

		row += 1

		buttonName = 'Detect mV'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Detect Spikes Using Vm Threshold')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		self.addWidget(button, row, 0)

		# Vm Threshold (mV)
		#minSpikeVmLabel = QtWidgets.QLabel('Vm Threshold (mV)')
		#self.addWidget(minSpikeVmLabel, row, 1)

		self.minSpikeVm = QtWidgets.QDoubleSpinBox()
		self.minSpikeVm.setMinimum(-1e6)
		self.minSpikeVm.setMaximum(+1e6)
		self.minSpikeVm.setValue(-20)
		self.addWidget(self.minSpikeVm, row, 1)

		row += 1

		# start/stop seconds
		startSeconds = QtWidgets.QLabel('From (Sec)')
		self.addWidget(startSeconds, row, 0)
		stopSeconds = QtWidgets.QLabel('To (Sec)')
		self.addWidget(stopSeconds, row, 1)
		#
		row += 1
		self.startSeconds = QtWidgets.QDoubleSpinBox()
		self.startSeconds.setMinimum(-1e6)
		self.startSeconds.setMaximum(+1e6)
		self.startSeconds.setValue(0)
		# abb 20200718
		#self.startSeconds.valueChanged.connect(self.on_start_stop)
		self.startSeconds.editingFinished.connect(self.on_start_stop)
		self.addWidget(self.startSeconds, row, 0)
		#
		self.stopSeconds = QtWidgets.QDoubleSpinBox()
		self.stopSeconds.setMinimum(-1e6)
		self.stopSeconds.setMaximum(+1e6)
		self.stopSeconds.setValue(0)
		#self.stopSeconds.valueChanged.connect(self.on_start_stop)
		self.stopSeconds.editingFinished.connect(self.on_start_stop)
		self.addWidget(self.stopSeconds, row, 1)

		row += 1

		# dv/dt threshold
		self.numSpikesLabel = QtWidgets.QLabel('Number of Spikes Detected: None')
		#self.numSpikesLabel.setObjectName('numSpikesLabel')
		tmpRowSpan = 1
		tmpColSpan = 2
		self.addWidget(self.numSpikesLabel, row, 0, tmpRowSpan, tmpColSpan) # columnSpan=2 does not work?

		row += 1

		buttonName = 'Save Spike Report'
		button = QtWidgets.QPushButton(buttonName)
		#button.setToolTip('Detect Spikes')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		self.addWidget(button, row, 0)

		row += 1

		buttonName = 'Reset All Axes'
		button = QtWidgets.QPushButton(buttonName)
		#button.setToolTip('Detect Spikes')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		self.addWidget(button, row, 0)

		row += 1

		for idx, plot in enumerate(myPlots):
			humanName = plot['humanName']
			isChecked = plot['plotIsOn']
			checkbox = QtWidgets.QCheckBox(humanName)
			checkbox.setChecked(isChecked)
			#checkbox.stateChanged.connect(lambda:self.on_check_click(checkbox))
			checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,idx))
			self.addWidget(checkbox, row, 0)
			row += 1

		#row += 1
		show_dvdt_checkbox = QtWidgets.QCheckBox('Show dV/dt')
		show_dvdt_checkbox.setChecked(True)
		#checkbox.stateChanged.connect(lambda:self.on_check_click(checkbox))
		show_dvdt_checkbox.stateChanged.connect(partial(self.on_check_click,show_dvdt_checkbox,'Show dV/dt'))
		self.addWidget(show_dvdt_checkbox, row, 0)

		# don't allow user to turn off all plot
		# the layout gets screwed up
		'''
		row += 1
		show_vm_checkbox = QtWidgets.QCheckBox('Show Vm')
		show_vm_checkbox.setChecked(True)
		#checkbox.stateChanged.connect(lambda:self.on_check_click(checkbox))
		show_vm_checkbox.stateChanged.connect(partial(self.on_check_click,show_vm_checkbox,'Show Vm'))
		self.addWidget(show_vm_checkbox, row, 0)
		'''

		row += 1
		checkbox = QtWidgets.QCheckBox('Show Clips')
		checkbox.setChecked(False)
		#checkbox.stateChanged.connect(lambda:self.on_check_click(checkbox))
		checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Show Clips'))
		self.addWidget(checkbox, row, 0)

		# this does not work at all !!!
		'''
		# abb 20201109, we have two columns (detection buttons and plot)
		# set the width of the detection buttons
		self.setColumnStretch(1, 10)
		self.setColumnStretch(0, 2)
		'''

	@QtCore.pyqtSlot()
	def on_start_stop(self):
		#print('myDetectToolbarWidget.on_start_stop()')
		start = self.startSeconds.value()
		stop = self.stopSeconds.value()
		#print('	start:', start, 'stop:', stop)
		self.detectionWidget.setAxis(start, stop)

	def on_check_click(self, checkbox, idx):
		isChecked = checkbox.isChecked()
		print('on_check_click() text:', checkbox.text(), 'isChecked:', isChecked, 'idx:', idx)
		if idx == 'Show Clips':
			self.detectionWidget.toggleClips(isChecked)
		elif idx == 'Show dV/dt':
			self.detectionWidget.toggle_dvdt(isChecked)
		elif idx == 'Show Vm':
			self.detectionWidget.toggle_vm(isChecked)
		else:
			# assuming idx is int !!!
			self.detectionWidget.togglePlot(idx, isChecked)

	@QtCore.pyqtSlot()
	def on_button_click(self, name):
		print('=== myDetectToolbarWidget.on_button_click() name:', name)

		modifiers = QtWidgets.QApplication.keyboardModifiers()
		isShift = modifiers == QtCore.Qt.ShiftModifier

		if name == 'Detect dV/dt':
			dvdtValue = self.dvdtThreshold.value()
			minSpikeVm = self.minSpikeVm.value()
			#print('	dvdtValue:', dvdtValue)
			#print('	minSpikeVm:', minSpikeVm)
			self.detectionWidget.detect(dvdtValue, minSpikeVm)

		elif name =='Detect mV':
			minSpikeVm = self.minSpikeVm.value()
			#print('	minSpikeVm:', minSpikeVm)
			# passing dvdtValue=None we will detect suing minSpikeVm
			dvdtValue = None
			#print('	dvdtValue:', dvdtValue)
			#print('	minSpikeVm:', minSpikeVm)
			self.detectionWidget.detect(dvdtValue, minSpikeVm)

		elif name == 'Reset All Axes':
			self.detectionWidget.setAxisFull()

		elif name == 'Save Spike Report':
			print('isShift:', isShift)
			self.detectionWidget.save(alsoSaveTxt=isShift)

	def sweepSelectionChange(self,i):
		print('sweepSelectionChange() i:', i)
		'''
		print "Items in the list are :"

		for count in range(self.cb.count()):
			print self.cb.itemText(count)
		'''
		sweepNumber = int(self.cb.currentText())
		print('	sweep number:', sweepNumber)


if __name__ == '__main__':
	# load a bAnalysis file

	abfFile = '/Users/cudmore/Sites/bAnalysis/data/19221021.abf'
	abfFile = '/Users/cudmore/Sites/bAnalysis/data/19114001.abf'
	abfFile = '/media/cudmore/data/Laura-data/manuscript-data/2020_06_23_0006.abf'
	path = '../data/19114001.abf'

	'''
	ba = sanpy.bAnalysis(file=abfFile)
	# spike detect
	ba.getDerivative(medianFilter=5) # derivative
	ba.spikeDetect(dVthresholdPos=50, minSpikeVm=-20, medianFilter=0)
	'''

	# default theme
	#pg.setConfigOption('background', 'w')
	#pg.setConfigOption('foreground', 'k')
	# dark theme
	#pg.setConfigOption('background', 'k')
	#pg.setConfigOption('foreground', 'w')

	app = QtWidgets.QApplication(sys.argv)
	w = bDetectionWidget()
	w.switchFile(path)
	w.detect(10, -20)

	w.show()

	sys.exit(app.exec_())
