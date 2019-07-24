# Author: Robert H Cudmore
# Date: 20190717

import os, sys
from functools import partial

import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
#import pyqtgraph.exporters

from bAnalysis import bAnalysis

class bDetectionWidget(QtWidgets.QWidget):
	def __init__(self, ba=None, mainWindow=None, parent=None):
		"""
		ba: bAnalysis object
		"""

		super(bDetectionWidget, self).__init__(parent)

		self.ba = ba
		self.myMainWindow = mainWindow

		self.dvdtLines = None
		self.vmLines = None
		self.clipLines = None

		self.myPlotList = []

		# a list of possible x/y plots (overlay over dvdt and Vm)
		self.myPlots = [
			{
				'humanName': 'Threshold Sec (dV/dt)',
				'x': 'thresholdSec',
				'y': 'thresholdVal_dvdt',
				'convertx_tosec': False, # some stats are in points, we need to convert to seconds
				'color': 'r',
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
				'symbol': 'o',
				'plotOn': 'vm',
				'plotIsOn': False,
			},
		]

		self.buildUI()

	'''
	def _toggle_plot(self, idx, on):
		if on:
			pass
		else:
			self.myPlotList[idx].setData(x=[], y=[])
	'''

	def detect(self, dvdtValue, minSpikeVm):
		"""
		detect spikes
		"""

		if self.ba is None:
			return

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

		self.myMainWindow.mySignal('detect') # signal to main window so it can update (file list, scatter plot)

		#QtCore.QCoreApplication.processEvents()

	def save(self):
		"""
		Prompt user for filename and save both xlsx and txt
		Save always defaults to data folder
		"""
		print('=== bDetectionWidget.save')
		if self.ba is None or self.ba.numSpikes==0:
			print('   no analysis ???')
			return
		xMin, xMax = self.getXRange()
		#print('    xMin:', xMin, 'xMax:', xMax)

		filePath, fileName = os.path.split(os.path.abspath(self.ba.file))
		fileBaseName, extension = os.path.splitext(fileName)
		excelFileName = os.path.join(filePath, fileBaseName + '.xlsx')

		print('Asking user for file name to save...')
		savefile, tmp = QtGui.QFileDialog.getSaveFileName(self, 'Save File', excelFileName)

		print('    savefile:', savefile)
		#print('tmp:', tmp)

		if len(savefile) > 0:
			self.ba.saveReport(savefile, xMin, xMax)
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

	def _setAxis(self, start, stop):
		"""
		Shared by (setAxisFull, setAxis)
		"""
		# make sure start/stop are in correct order and swap if necc.
		if stop<start:
			tmp = start
			start = stop
			stop = tmp

		#print('bDetectionWidget.setAxis() start:', start, 'stop:', stop)

		self.derivPlot.setXRange(start, stop) # linked to Vm

		# update detection toolbar
		self.detectToolbarWidget.startSeconds.setValue(start)
		self.detectToolbarWidget.startSeconds.repaint()
		self.detectToolbarWidget.stopSeconds.setValue(stop)
		self.detectToolbarWidget.stopSeconds.repaint()

		self.refreshClips(start, stop)

		return start, stop

	def setAxisFull(self):
		if self.ba is None:
			return

		start = 0
		stop = self.ba.abf.sweepX[-1]

		start, stop = self._setAxis(start, stop)
		self.myMainWindow.mySignal('set full x axis')

	def setAxis(self, start, stop):
		start, stop = self._setAxis(start, stop)
		self.myMainWindow.mySignal('set x axis', data=[start,stop])

	def switchFile(self, path):
		"""
		set self.ba to new bAnalysis object ba
		"""
		print('=== bDetectionWidget.switchFile() path:', path)

		if self.ba is not None and self.ba.file == path:
			print('bDetectionWidget is already displaying file:', path)
			return

		if not os.path.isfile(path):
			print('error: bDetectionWidget.switchFile() did not find file:', path)
			return

		self.ba = bAnalysis(file=path)
		self.ba.getDerivative(medianFilter=5) # derivative

		#remove vm/dvdt/clip itmes
		if self.dvdtLines is not None:
			self.derivPlot.removeItem(self.dvdtLines)
		if self.vmLines is not None:
			self.vmPlot.removeItem(self.vmLines)
		if self.clipLines is not None:
			self.clipPlot.removeItem(self.clipLines)

		# cancel spike selection
		self.selectSpike(None)

		# set full axis
		self.setAxisFull()

		# update lines
		self.dvdtLines = MultiLine(self.ba.abf.sweepX, self.ba.filteredDeriv, self)
		self.derivPlot.addItem(self.dvdtLines)

		self.vmLines = MultiLine(self.ba.abf.sweepX, self.ba.abf.sweepY, self)
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

		# single spike selection
		self.vmPlot.removeItem(self.mySingleSpikeScatterPlot)
		self.vmPlot.addItem(self.mySingleSpikeScatterPlot)

		#
		# critical
		self.replot()

		#
		# set sweep to 0


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
		if self.view.getItem(2,0) is None:
			# clips are not being displayed
			return

		# remove existing
		if self.clipLines is not None:
			self.clipPlot.removeItem(self.clipLines)

		theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(xMin, xMax)

		# convert clips to 2d ndarray ???
		xTmp = np.array(theseClips_x)
		yTmp = np.array(theseClips)

		self.clipLines = MultiLine(xTmp, yTmp, self, allowXAxisDrag=False)

		self.clipPlot.addItem(self.clipLines)

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
		self.myHBoxLayout_detect = QtWidgets.QHBoxLayout(self)

		# detection widget toolbar
		self.detectToolbarWidget = myDetectToolbarWidget(self.myPlots, self)
		self.myHBoxLayout_detect.addLayout(self.detectToolbarWidget, stretch=1) # stretch=10, not sure on the units???

		#print('bDetectionWidget.buildUI() building pg.GraphicsLayoutWidget')
		self.view = pg.GraphicsLayoutWidget()
		self.view.show()

		self.derivPlot = self.view.addPlot(row=0, col=0)
		self.vmPlot = self.view.addPlot(row=1, col=0)
		self.clipPlot = self.view.addPlot(row=2, col=0)

		# hide the little 'A' button to rescale axis
		self.derivPlot.hideButtons()
		self.vmPlot.hideButtons()
		self.clipPlot.hideButtons()

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

		self.replot()

		#
		#print('bDetectionWidget.buildUI() adding view to myHBoxLayout_detect')
		self.myHBoxLayout_detect.addWidget(self.view, stretch=8) # stretch=10, not sure on the units???

		#print('bDetectionWidget.buildUI() done')

	def myPrint(self):
		# this does not do svg
		#exporter = pg.exporters.ImageExporter(self.vmPlot)

		'''
		exporter = myImageExporter(self.vmPlot)
		exporter.parameters()['width'] = 1000   # (note this also affects height parameter)
		filename = '/Users/cudmore/Desktop/myExport.png'
		'''

		exporter = pg.exporters.SVGExporter(self.vmPlot)
		filename = '/Users/cudmore/Desktop/myExport.svg'

		print('myPrint() saving file', filename)
		exporter.export(filename)
		exporter.export('fileName.png')
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
	def __init__(self, x, y, detectionWidget, allowXAxisDrag=True):
		"""x and y are 2D arrays of shape (Nplots, Nsamples)"""

		self.detectionWidget = detectionWidget
		self.allowXAxisDrag = allowXAxisDrag

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
		self.setPen(pg.mkPen(color='k', width=1))
	def shape(self):
		# override because QGraphicsPathItem.shape is too expensive.
		#print(time.time(), 'MultiLine.shape()', pg.QtGui.QGraphicsItem.shape(self))
		return pg.QtGui.QGraphicsItem.shape(self)
	def boundingRect(self):
		#print(time.time(), 'MultiLine.boundingRect()', self.path.boundingRect())
		return self.path.boundingRect()

	def mouseDragEvent(self, ev):
		#print('myGraphicsLayoutWidget.mouseDragEvent(self, ev):')

		if not self.allowXAxisDrag:
			ev.accept() # this prevents click+drag of plot
			return

		if ev.button() != QtCore.Qt.LeftButton:
			ev.ignore()
			return

		if ev.isStart():
			self.xStart = ev.buttonDownPos()[0]
			self.linearRegionItem = pg.LinearRegionItem(values=(self.xStart,0), orientation=pg.LinearRegionItem.Vertical)
			#self.linearRegionItem.sigRegionChangeFinished.connect(self.update_x_axis)
			# add the LinearRegionItem to the parent widget (Cannot add to self as it is an item)
			self.parentWidget().addItem(self.linearRegionItem)
		elif ev.isFinish():

			#self.parentWidget().setXRange(self.xStart, self.xCurrent)
			self.detectionWidget.setAxis(self.xStart, self.xCurrent)

			self.xStart = None
			self.xCurrent = None

			self.parentWidget().removeItem(self.linearRegionItem)
			self.linearRegionItem = None


			return

		self.xCurrent = ev.pos()[0]
		#print('xStart:', self.xStart, 'self.xCurrent:', self.xCurrent)
		self.linearRegionItem.setRegion((self.xStart, self.xCurrent))
		ev.accept()

	'''
	def update_x_axis(self):
		print('myGraphicsLayoutWidget.update_x_axis()')
	'''

	'''
	def mouseClickEvent(self, ev):
		print('myGraphicsLayoutWidget.mouseClickEvent(self, ev):')
	'''

#class myDetectToolbarWidget(QtWidgets.QVBoxLayout):
class myDetectToolbarWidget(QtWidgets.QGridLayout):

	def sweepSelectionChange(self,i):
		print('sweepSelectionChange() i:', i)
		'''
		print "Items in the list are :"

		for count in range(self.cb.count()):
			print self.cb.itemText(count)
		'''
		sweepNumber = int(self.cb.currentText())
		print('    sweep number:', sweepNumber)

	def __init__(self, myPlots, detectionWidget, parent=None):
		"""
		myPlots is a list of dict describing each x/y plot (on top of vm and/or dvdt)
		"""

		super(myDetectToolbarWidget, self).__init__(parent)

		self.detectionWidget = detectionWidget # parent detection widget

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

		dvdtLabel = QtWidgets.QLabel('dV/dt Theshold')
		self.addWidget(dvdtLabel, row, 1)

		self.dvdtThreshold = QtWidgets.QDoubleSpinBox()
		self.dvdtThreshold.setMinimum(-1e6)
		self.dvdtThreshold.setMaximum(+1e6)
		self.dvdtThreshold.setValue(50)
		self.addWidget(self.dvdtThreshold, row, 2)

		row += 1

		buttonName = 'Detect Vm Threshold'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Detect Spikes Using Vm Threshold')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		self.addWidget(button, row, 0)

		# Vm Threshold (mV)
		minSpikeVmLabel = QtWidgets.QLabel('Vm Threshold (mV)')
		self.addWidget(minSpikeVmLabel, row, 1)

		self.minSpikeVm = QtWidgets.QDoubleSpinBox()
		self.minSpikeVm.setMinimum(-1e6)
		self.minSpikeVm.setMaximum(+1e6)
		self.minSpikeVm.setValue(-20)
		self.addWidget(self.minSpikeVm, row, 2)

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
		self.startSeconds.valueChanged.connect(self.on_start_stop)
		self.addWidget(self.startSeconds, row, 0)
		#
		self.stopSeconds = QtWidgets.QDoubleSpinBox()
		self.stopSeconds.setMinimum(-1e6)
		self.stopSeconds.setMaximum(+1e6)
		self.stopSeconds.setValue(0)
		self.stopSeconds.valueChanged.connect(self.on_start_stop)
		self.addWidget(self.stopSeconds, row, 1)

		row += 1

		# dv/dt threshold
		self.numSpikesLabel = QtWidgets.QLabel('Number of Spikes Detected: None')
		#self.numSpikesLabel.setObjectName('numSpikesLabel')
		self.addWidget(self.numSpikesLabel, row, 0)

		row += 1

		buttonName = 'Save Spike Report'
		button = QtWidgets.QPushButton(buttonName)
		#button.setToolTip('Detect Spikes')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		self.addWidget(button, row, 0)

		row += 1

		buttonName = 'Reset X-Axis'
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

		checkbox = QtWidgets.QCheckBox('Show Clips')
		checkbox.setChecked(False)
		#checkbox.stateChanged.connect(lambda:self.on_check_click(checkbox))
		checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Show Clips'))
		self.addWidget(checkbox, row, 0)

	def on_start_stop(self):
		#print('myDetectToolbarWidget.on_start_stop()')
		start = self.startSeconds.value()
		stop = self.stopSeconds.value()
		#print('    start:', start, 'stop:', stop)
		self.detectionWidget.setAxis(start, stop)

	def on_check_click(self, checkbox, idx):
		isChecked = checkbox.isChecked()
		print('on_check_click()', checkbox.text(), isChecked, idx)
		if idx == 'Show Clips':
			self.detectionWidget.toggleClips(isChecked)
		else:
			# assuming idx is int !!!
			self.detectionWidget.togglePlot(idx, isChecked)

	@QtCore.pyqtSlot()
	def on_button_click(self, name):
		print('=== myDetectToolbarWidget.on_button_click() name:', name)
		if name == 'Detect dV/dt':
			dvdtValue = self.dvdtThreshold.value()
			minSpikeVm = self.minSpikeVm.value()
			#print('    dvdtValue:', dvdtValue)
			#print('    minSpikeVm:', minSpikeVm)
			self.detectionWidget.detect(dvdtValue, minSpikeVm)

		elif name =='Detect Vm Threshold':
			minSpikeVm = self.minSpikeVm.value()
			#print('    minSpikeVm:', minSpikeVm)
			# passing dvdtValue=None we will detect suing minSpikeVm
			dvdtValue = None
			self.detectionWidget.detect(dvdtValue, minSpikeVm)

		elif name == 'Reset X-Axis':
			self.detectionWidget.setAxisFull()

		elif name == 'Save Spike Report':
			self.detectionWidget.save()

if __name__ == '__main__':
	# load a bAnalysis file
	from bAnalysis import bAnalysis

	abfFile = '/Users/cudmore/Sites/bAnalysis/data/19221021.abf'
	abfFile = '/Users/cudmore/Sites/bAnalysis/data/19114001.abf'
	ba = bAnalysis(file=abfFile)

	# spike detect
	ba.getDerivative(medianFilter=5) # derivative
	ba.spikeDetect(dVthresholdPos=50, minSpikeVm=-20, medianFilter=0)

	pg.setConfigOption('background', 'w')
	pg.setConfigOption('foreground', 'k')

	app = QtWidgets.QApplication(sys.argv)
	w = bDetectionWidget(ba)
	w.show()

	sys.exit(app.exec_())
