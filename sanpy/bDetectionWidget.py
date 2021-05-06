# Author: Robert H Cudmore
# Date: 20190717

import os, sys, math
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
	signalSelectSpike = QtCore.Signal(object, object) # spike number, doZoom

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
		self.dvdtLinesFiltered = None
		self.vmLines = None
		self.vmLinesFiltered = None
		self.clipLines = None
		self.meanClipLine = None

		self.myPlotList = []

		# a list of possible x/y plots (overlay over dvdt and Vm)
		# order here determines order in interface
		self.myPlots = [
			{
				'humanName': 'Threshold (mV)',
				'x': 'thresholdSec',
				'y': 'thresholdVal',
				'convertx_tosec': False, # some stats are in points, we need to convert to seconds
				'color': 'r',
				'styleColor': 'color: red',
				'symbol': 'o',
				'plotOn': 'vm', # which plot to overlay (vm, dvdt)
				'plotIsOn': True,
			},
			{
				'humanName': 'Threshold (dV/dt)',
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
				'color': 'g',
				'styleColor': 'color: green',
				'symbol': 'o',
				'plotOn': 'vm',
				'plotIsOn': True,
			},
			{
				'humanName': 'Half-Widths',
				'x': None,
				'y': None,
				'convertx_tosec': True,
				'color': 'y',
				'styleColor': 'color: yellow',
				'symbol': 'o',
				'plotOn': 'vm',
				'plotIsOn': False,
			},
			{
				'humanName': 'Pre AP Min (mV)',
				'x': 'preMinPnt',
				'y': 'preMinVal',
				'convertx_tosec': True,
				'color': 'y',
				'styleColor': 'color: green',
				'symbol': 'o',
				'plotOn': 'vm',
				'plotIsOn': False,
			},
			#{
			#	'humanName': 'Post AP Min (mV)',
			#	'x': 'postMinPnt',
			#	'y': 'postMinVal',
			#	'convertx_tosec': True,
			#	'color': 'b',
			#	'styleColor': 'color: blue',
			#	'symbol': 'o',
			#	'plotOn': 'vm',
			#	'plotIsOn': False,
			#},
			{
				'humanName': 'EDD',
				'x': None,
				'y': None,
				'convertx_tosec': True,
				'color': 'm',
				'styleColor': 'color: megenta',
				'symbol': 'o',
				'plotOn': 'vm',
				'plotIsOn': False,
			},
		]

		self.buildUI()

		windowOptions = self.getMainWindowOptions()
		showDvDt = True
		showClips = False
		showScatter = True
		if windowOptions is not None:
			showDvDt = windowOptions['display']['showDvDt']
			showClips = windowOptions['display']['showClips']
			showScatter = windowOptions['display']['showScatter']

			self.toggle_dvdt(showDvDt)
			self.toggleClips(showClips)

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

	def getMainWindowOptions(self):
		theRet = None
		if self.myMainWindow is not None:
			theRet = self.myMainWindow.getOptions()
		return theRet

	def detect(self, dvdtThreshold, vmThreshold):
		"""
		detect spikes
		"""

		if self.ba is None:
			return

		print('== bDetectionWidget.detect() dvdtThreshold:', dvdtThreshold, 'vmThreshold', vmThreshold)
		if self.ba.loadError:
			print('bDetectionWidget.detect() did not spike detect because the file was not loaded (may be corrupt .abf file?)')
			return

		self.updateStatusBar(f'Detecting spikes dvdt:{dvdtThreshold} minVm:{vmThreshold}')

		detectionDict = self.ba.getDefaultDetection()
		detectionDict['dvdtThreshold'] = dvdtThreshold
		detectionDict['mvThreshold'] = vmThreshold
		#print('default detection dict is:')
		#sanpy.bUtil.printDict(detectionDict, withType=True)

		# grab parameters from main interface table
		if self.myMainWindow is not None:
			print('  grabbing detection parameters from main window table')
			myDetectionDict = self.myMainWindow.getSelectedRowDict()
			#print('  row detection dict is:')
			#sanpy.bUtil.printDict(myDetectionDict, withType=True)
			#todo fill in detectionDict
			#print('  todo: fill in from table row:')
			if myDetectionDict['refractory_ms'] > 0:
				detectionDict['refractory_ms'] = myDetectionDict['refractory_ms']
			if myDetectionDict['halfWidthWindow_ms'] > 0:
				# default is 50 ms
				detectionDict['halfWidthWindow_ms'] = myDetectionDict['halfWidthWindow_ms']
			#
			if myDetectionDict['startSeconds'] >= 0:
				# default is 50 ms
				detectionDict['startSeconds'] = myDetectionDict['startSeconds']
			if myDetectionDict['stopSeconds'] >= 0:
				# default is 50 ms
				detectionDict['stopSeconds'] = myDetectionDict['stopSeconds']
			#
			detectionDict['cellType'] = myDetectionDict['Cell Type']
			detectionDict['sex'] = myDetectionDict['Sex']
			detectionDict['condition'] = myDetectionDict['Condition']

		print('final detection params')
		sanpy.bUtil.printDict(detectionDict, withType=True)
		#self.ba.spikeDetect(dvdtThreshold=dvdtThreshold, vmThreshold=vmThreshold)
		dfReportForScatter = self.ba.spikeDetect(detectionDict)

		# error report
		dfError = self.ba.errorReport()

		if self.ba.numSpikes == 0:
			msg = QtWidgets.QMessageBox()
			msg.setIcon(QtWidgets.QMessageBox.Warning)
			msg.setText("No Spikes Detected")
			msg.setInformativeText('dV/dt Threshold: ' + str(dvdtThreshold) + '\r' + ' Vm Threshold (mV): '  + str(vmThreshold))
			msg.setWindowTitle("No Spikes Detected")
			retval = msg.exec_()

		self.replot() # replot statistics over traces

		self.refreshClips() # replot clips

		if self.myMainWindow is not None:
			self.myMainWindow.mySignal('detect', data=(dfReportForScatter,dfError)) # signal to main window so it can update (file list, scatter plot)

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

		# abb 20201217, I thought I was already doing this?
		xMinStr = '%.2f'%(xMin)
		xMaxStr = '%.2f'%(xMax)

		lhs, rhs = xMinStr.split('.')
		xMinStr = '_b' + lhs + '_' + rhs

		lhs, rhs = xMaxStr.split('.')
		xMaxStr = '_e' + lhs + '_' + rhs

		filePath, fileName = os.path.split(os.path.abspath(self.ba.file))
		fileBaseName, extension = os.path.splitext(fileName)
		fileBaseName = f'{fileBaseName}{xMinStr}{xMaxStr}.xlsx'
		#excelFileName = os.path.join(filePath, fileBaseName + '.xlsx')
		excelFileName = os.path.join(filePath, fileBaseName)

		print('Asking user for file name to save...')
		savefile, tmp = QtGui.QFileDialog.getSaveFileName(self, 'Save File', excelFileName)

		print('	savefile:', savefile)
		#print('tmp:', tmp)

		if len(savefile) > 0:
			analysisName, df = self.ba.saveReport(savefile, xMin, xMax, alsoSaveTxt=alsoSaveTxt)
			if self.myMainWindow is not None:
				self.myMainWindow.mySignal('saved', data=analysisName)
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
			if whichPlot in ['dvdt', 'dvdtFiltered']:
				self.derivPlot.setYRange(start, stop) # linked to Vm
			elif whichPlot in ['vm', 'vmFiltered']:
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
		#print('bDetectionWidget.setAxis()', start, stop)
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

	def switchFile(self, path, tableRowDict):
		"""
		set self.ba to new bAnalysis object ba

		Can fail if .abf file is corrupt
		"""
		print('=== bDetectionWidget.switchFile() path:', path)

		#if self.ba is not None and self.ba.file == path:
		#	print('bDetectionWidget is already displaying file:', path)
		#	return

		if not os.path.isfile(path):
			print('  error: bDetectionWidget.switchFile() did not find file:', path)
			return None

		self.updateStatusBar(f'Loading file {path}')

		# make analysis object from file
		self.ba = sanpy.bAnalysis(file=path) # loads abf file
		dDict = self.ba.getDefaultDetection() # so we can fill in filtered derivartive

		if self.ba.loadError:
			# happens when .abf file is corrupt
			pass
		else:
			self.ba.getDerivative(dDict) # derivative

		#remove vm/dvdt/clip items (even when abf file is corrupt)
		#if self.dvdtLines is not None:
		#	self.derivPlot.removeItem(self.dvdtLines)
		if self.dvdtLinesFiltered is not None:
			self.derivPlot.removeItem(self.dvdtLinesFiltered)
		#if self.vmLines is not None:
		#	self.vmPlot.removeItem(self.vmLines)
		if self.vmLinesFiltered is not None:
			self.vmPlot.removeItem(self.vmLinesFiltered)
		if self.clipLines is not None:
			self.clipPlot.removeItem(self.clipLines)

		# abb 20201009
		if self.ba.loadError:
			self.replot()
			print('bDetectionWidget.switchFile() did not switch file, the .abf file may be corrupt:', path)
			self.updateStatusBar(f'Error loading file {path}')
			self.myMainWindow.mySignal('set abfError')
			return None

		# fill in detection parameters
		self.fillInDetectionParameters(tableRowDict) # fills in controls

		self.updateStatusBar(f'Plotting file {path}')

		# cancel spike selection
		self.selectSpike(None)

		# set full axis
		#self.setAxisFull()

		# update lines
		#self.dvdtLines = MultiLine(self.ba.abf.sweepX, self.ba.deriv,
		#					self, type='dvdt')
		self.dvdtLinesFiltered = MultiLine(self.ba.abf.sweepX, self.ba.filteredDeriv,
							self, forcePenColor=None, type='dvdtFiltered')
		#self.derivPlot.addItem(self.dvdtLines)
		self.derivPlot.addItem(self.dvdtLinesFiltered)

		#self.vmLines = MultiLine(self.ba.abf.sweepX, self.ba.abf.sweepY,
		#					self, type='vm')
		self.vmLinesFiltered = MultiLine(self.ba.abf.sweepX, self.ba.filteredVm,
							self, forcePenColor=None, type='vmFiltered')
		#self.vmPlot.addItem(self.vmLines)
		self.vmPlot.addItem(self.vmLinesFiltered)

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

		return True

	def fillInDetectionParameters(self, tableRowDict):
		"""
		{'idx': 4, 'include': 1.0, 'ABF File': '2020_07_23_0003', 'Cell Type': 'Inferior', 'Sex': 'Male', 'Condition': 'ISO 100nM', 'startSeconds': 177.26, 'stopSeconds': 276.67, 'dvdtThreshold': 3.5, 'mvThreshold': -20.0, 'refractory_ms': 150.0, 'peakWindow_ms': nan, 'halfWidthWindow_ms': nan, 'Notes': nan}
		"""
		print('fillInDetectionParameters() tableRowDict:', tableRowDict)
		self.detectToolbarWidget.fillInDetectionParameters(tableRowDict)

	def updateStatusBar(self, text):
		if self.myMainWindow is not None:
			self.myMainWindow.updateStatusBar(text)

	def on_scatterClicked(self, item, points, ev=None):
		"""
		item: PlotDataItem that was clicked
		points: list of points clicked
		"""
		print('=== bDetectionWidget.on_scatterClicked')
		print('  item:', item)
		print('  points:', points)
		print('  ev:', ev)
		indexes = []
		#print('item.data:', item.data())
		for idx, p in enumerate(points):
			print(f'  points[{idx}].data(): {p.data()} p.pos: {p.pos()}')
		'''
		for p in points:
			p = p.pos()
			x, y = p.x(), p.y()
			lx = np.argwhere(item.data['x'] == x)
			ly = np.argwhere(item.data['y'] == y)
			i = np.intersect1d(lx, ly).tolist()
			indexes += i
		indexes = list(set(indexes))
		print('spike(s):', indexes)
		'''

	def getEDD(self):
		# get x/y plot position of all EDD from all spikes
		print('bDetectionWidget.getEDD()')
		x = []
		y = []
		for idx, spike in enumerate(self.ba.spikeDict):
			preLinearFitPnt0 = spike['preLinearFitPnt0']
			preLinearFitPnt1 = spike['preLinearFitPnt1']

			if preLinearFitPnt0 is not None:
				preLinearFitPnt0 = self.ba.pnt2Sec_(preLinearFitPnt0)
			else:
				preLinearFitPnt0 = np.nan

			if preLinearFitPnt1 is not None:
				preLinearFitPnt1 = self.ba.pnt2Sec_(preLinearFitPnt1)
			else:
				preLinearFitPnt1 = np.nan

			preLinearFitVal0 = spike['preLinearFitVal0']
			preLinearFitVal1 = spike['preLinearFitVal1']

			x.append(preLinearFitPnt0)
			x.append(preLinearFitPnt1)
			x.append(np.nan)

			y.append(preLinearFitVal0)
			y.append(preLinearFitVal1)
			y.append(np.nan)

		print ('  returning', len(x), len(y))
		return x, y

	def getHalfWidths(self):
		#print('bDetectionWidget.getHalfWidths()')
		# defer until we know how many half-widths 20/50/80
		x = []
		y = []
		numPerSpike = 3 # rise/fall/nan
		numSpikes = self.ba.numSpikes
		xyIdx = 0
		for idx, spike in enumerate(self.ba.spikeDict):
			if idx ==0:
				# make x/y from first spike using halfHeights = [20,50,80]
				halfHeights = spike['halfHeights'] # will be same for all spike, like [20, 50, 80]
				numHalfHeights = len(halfHeights)
				# *numHalfHeights to account for rise/fall + padding nan
				x = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
				y = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
				#print('  len(x):', len(x), 'numHalfHeights:', numHalfHeights, 'numSpikes:', numSpikes, 'halfHeights:', halfHeights)

			for idx2, width in enumerate(spike['widths']):
				halfHeight = width['halfHeight'] # [20,50,80]
				risingPnt = width['risingPnt']
				risingVal = width['risingVal']
				fallingPnt = width['fallingPnt']
				fallingVal = width['fallingVal']

				#print('	spike:', idx, 'halfHeight:', halfHeight, 'risingPnt:', risingPnt)
				if risingPnt is None or fallingPnt is None:
					# half-height was not detected
					#print('  getHalfWidths() skipping spike', idx, 'width', halfHeight , 'not dtected')
					continue

				risingSec = self.ba.pnt2Sec_(risingPnt)
				fallingSec = self.ba.pnt2Sec_(fallingPnt)

				#if idx==2:
				#	print('')
				#	print('risingSec:', risingSec, 'fallingSec:', fallingSec)
				#	sanpy.bUtil.printDict(width)

				x[xyIdx] = risingSec
				x[xyIdx+1] = fallingSec
				x[xyIdx+2] = np.nan
				# y
				y[xyIdx] = fallingVal #risingVal, to make line horizontal
				y[xyIdx+1] = fallingVal
				y[xyIdx+2] = np.nan

				# each spike has 3x pnts: rise/fall/nan
				xyIdx += numPerSpike # accounts for rising/falling/nan
			# end for width
		# end for spike
		#print('  numSpikes:', numSpikes, 'xyIdx:', xyIdx)
		#
		return x, y

	def replot(self):

		if self.ba is None:
			return

		for idx, plot in enumerate(self.myPlots):
			if plot['humanName'] == 'Half-Widths':
				# new 20210212
				xPlot, yPlot = self.getHalfWidths()
			elif plot['humanName'] == 'EDD':
				xPlot, yPlot = self.getEDD()
			else:
				xPlot, yPlot = self.ba.getStat(plot['x'], plot['y'])
				if plot['convertx_tosec']:
					xPlot = [self.ba.pnt2Sec_(x) for x in xPlot] # convert pnt to sec
			#
			# added connect='finite' to respect nan in half-width
			# not sure how connect='finite' affect all other plots using scatter???
			self.myPlotList[idx].setData(x=xPlot, y=yPlot)
			self.togglePlot(idx, plot['plotIsOn'])

		# update label with number of spikes detected
		print('todo: move numSpikesLable to status')
		'''
		numSpikesStr = str(self.ba.numSpikes)
		self.detectToolbarWidget.numSpikesLabel.setText('Number of Spikes: ' + numSpikesStr)
		self.detectToolbarWidget.numSpikesLabel.repaint()
		'''

		# spike freq
		print('todo: move spikeFreqLabel to status')
		'''
		meanSpikeFreq = self.ba.getStatMean('spikeFreq_hz')
		if meanSpikeFreq is not None:
			meanSpikeFreq = round(meanSpikeFreq,2)
		self.detectToolbarWidget.spikeFreqLabel.setText('Frequency: ' + str(meanSpikeFreq))
		self.detectToolbarWidget.spikeFreqLabel.repaint()
		'''

	def togglePlot(self, idx, on):
		"""
		Toggle overlay of stats like spike peak.

		idx: overlay index into self.myPlots
		on: boolean
		"""
		# toggle the plot on/off
		self.myPlots[idx]['plotIsOn'] = on

		if on:
			#self.myPlotList[idx].setData(pen=pg.mkPen(width=5, color=plot['color'], symbol=plot['symbol']), size=2)
			self.myPlotList[idx].show()
			#self.myPlotList[idx].setPen(pg.mkPen(width=5, color=plot['color'], symbol=plot['symbol']))
			# removed for half-width
			#self.myPlotList[idx].setSize(2)
		else:
			#self.myPlotList[idx].setData(pen=pg.mkPen(width=0, color=plot['color'], symbol=plot['symbol']), size=0)
			self.myPlotList[idx].hide()
			#self.myPlotList[idx].setPen(pg.mkPen(width=0, color=plot['color'], symbol=plot['symbol']))
			# removed for half-width
			#self.myPlotList[idx].setSize(0)

	def selectSpike(self, spikeNumber, doZoom=False, doEmit=False):
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

		if doZoom:
			thresholdSeconds = self.ba.getStat('thresholdSec')
			if spikeNumber > len(thresholdSeconds)-1:
				return
			thresholdSecond = thresholdSeconds[spikeNumber]
			thresholdSecond = round(thresholdSecond, 3)
			startSec = thresholdSecond - 0.5
			startSec = round(startSec, 2)
			stopSec = thresholdSecond + 0.5
			stopSec = round(stopSec, 2)
			print('  spikeNumber:', spikeNumber, 'thresholdSecond:', thresholdSecond, 'startSec:', startSec, 'stopSec:', stopSec)
			start = self.setAxis(startSec, stopSec)

		if doEmit:
			self.signalSelectSpike.emit(spikeNumber, doZoom)

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

		# this returns x-axis in ms
		theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(xMin, xMax)

		dataPointsPerMs = self.ba.abf.dataPointsPerMs

		# convert clips to 2d ndarray ???
		xTmp = np.array(theseClips_x)
		xTmp /= dataPointsPerMs # pnt to ms
		yTmp = np.array(theseClips)
		self.clipLines = MultiLine(xTmp, yTmp, self, allowXAxisDrag=False, type='clip')
		self.clipPlot.addItem(self.clipLines)

		#print(xTmp.shape) # (num spikes, time)
		self.xMeanClip = np.nanmean(xTmp, axis=0) # xTmp is in ms
		self.yMeanClip = np.nanmean(yTmp, axis=0)
		self.meanClipLine = MultiLine(self.xMeanClip, self.yMeanClip, self, allowXAxisDrag=False, type='meanclip')
		self.clipPlot.addItem(self.meanClipLine)

	def toggle_errorTable(self, on):
		if self.myMainWindow is not None:
			self.myMainWindow.toggleErrorTable(on)

	def toggle_scatter(self, on):
		"""
		toggle scatter plot in parent (e.g. xxx)
		"""
		# 20210426, need to clean this up

		# 20210426, was this
		if self.myMainWindow is not None:
			self.myMainWindow.toggleStatisticsPlot(on)

		# 20210426, need to clean this up
		'''
		if on:
			self.myScatterPlotWidget.show()
		else:
			self.myScatterPlotWidget.hide()
		'''

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
		self.myHBoxLayout_detect.setAlignment(QtCore.Qt.AlignTop)

		# detection widget toolbar
		# abb 20201110, switching over to a better layout
		#self.detectToolbarWidget = myDetectToolbarWidget(self.myPlots, self)
		#self.myHBoxLayout_detect.addLayout(self.detectToolbarWidget, stretch=1) # stretch=10, not sure on the units???
		self.detectToolbarWidget = myDetectToolbarWidget2(self.myPlots, self)
		#if self.myMainWindow is not None:
		#	self.detectToolbarWidget.signalSelectSpike.connect(self.myMainWindow.slotSelectSpike)
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

		#
		# mouse crosshair
		crosshairPlots = ['derivPlot', 'vmPlot', 'clipPlot']
		self.crosshairDict = {}
		for crosshairPlot in crosshairPlots:
			self.crosshairDict[crosshairPlot] = {
				'h': pg.InfiniteLine(angle=0, movable=False),
				'v': pg.InfiniteLine(angle=90, movable=False)
			}
			# start hidden
			self.crosshairDict[crosshairPlot]['h'].hide()
			self.crosshairDict[crosshairPlot]['v'].hide()

			# add h/v to appropriate plot
			if crosshairPlot == 'derivPlot':
				self.derivPlot.addItem(self.crosshairDict[crosshairPlot]['h'], ignoreBounds=True)
				self.derivPlot.addItem(self.crosshairDict[crosshairPlot]['v'], ignoreBounds=True)
			elif crosshairPlot == 'vmPlot':
				self.vmPlot.addItem(self.crosshairDict[crosshairPlot]['h'], ignoreBounds=True)
				self.vmPlot.addItem(self.crosshairDict[crosshairPlot]['v'], ignoreBounds=True)
			elif crosshairPlot == 'clipPlot':
				self.clipPlot.addItem(self.crosshairDict[crosshairPlot]['h'], ignoreBounds=True)
				self.clipPlot.addItem(self.crosshairDict[crosshairPlot]['v'], ignoreBounds=True)

		# trying to implement mouse moved events
		self.myProxy = pg.SignalProxy(self.vmPlot.scene().sigMouseMoved, rateLimit=60, slot=self.myMouseMoved)
		#self.vmPlot.scene().sigMouseMoved.connect(self.myMouseMoved)

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

		#self.toggleClips(False)

		# add all overlaid scatter plots
		self.myPlotList = [] # list of pg.ScatterPlotItem
		for idx, plot in enumerate(self.myPlots):
			color = plot['color']
			symbol = plot['symbol']
			humanName = plot['humanName']
			if humanName == 'Half-Widths':
				# PlotCurveItem
				#myScatterPlot = pg.PlotItem(pen=pg.mkPen(width=5, color=color), symbol=symbol, size=2)
				#myScatterPlot = pg.PlotCurveItem(pen=pg.mkPen(width=5, color=color), symbol=symbol, size=2, connect='finite')
				myScatterPlot = pg.PlotDataItem(pen=pg.mkPen(width=4, color=color), connect='finite') # default is no symbol
				#myScatterPlot.setData(x=[], y=[]) # start empty
				#smyScatterPlot.sigClicked.connect(self.on_scatterClicked)
			else:
				myScatterPlot = pg.PlotDataItem(pen=None, symbol=symbol, symbolSize=4, symbolPen=None, symbolBrush=color)
				#myScatterPlot = pg.ScatterPlotItem(pen=pg.mkPen(width=5, color=color), symbol=symbol, size=2)
				myScatterPlot.setData(x=[], y=[]) # start empty
				#myScatterPlot.sigClicked.connect(self.on_scatterClicked)
				myScatterPlot.sigPointsClicked.connect(self.on_scatterClicked)

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
		self.derivPlot.getAxis('left').setLabel('dV/dt (mV/ms)')
		self.vmPlot.getAxis('left').setLabel('Vm (mV)')
		self.vmPlot.getAxis('bottom').setLabel('Seconds')

		self.replot()

		# 20210426
		# make vboxlayout and stack self.view with a scatter
		vBoxLayout_detect = QtWidgets.QVBoxLayout(self)

		#
		#print('bDetectionWidget.buildUI() adding view to myHBoxLayout_detect')

		# 20210426, was this
		#self.myHBoxLayout_detect.addWidget(self.view, stretch=8) # self.view is GraphicsLayoutWidget

		'''
		# works
		self.myScatterPlotWidget = sanpy.bScatterPlotWidget(mainWindow=self.myMainWindow, detectionWidget=self)
		self.myMainWindow.signalSetXAxis.connect(self.myScatterPlotWidget.slotSetXAxis)
		self.myMainWindow.signalSelectSpike.connect(self.myScatterPlotWidget.slotSelectSpike)
		self.myScatterPlotWidget.hide()
		'''

		vBoxLayout_detect.addWidget(self.view) #, stretch=8)
		#vBoxLayout_detect.addWidget(self.myScatterPlotWidget) #, stretch=2)

		self.myHBoxLayout_detect.addLayout(vBoxLayout_detect)


	def toggleCrosshair(self, onOff):
		for plotName in self.crosshairDict.keys():
			self.crosshairDict[plotName]['h'].setVisible(onOff)
			self.crosshairDict[plotName]['v'].setVisible(onOff)

	def myMouseMoved(self, event):
		# event: PyQt5.QtCore.QPointF
		#print('myMouseMoved()', event)

		# looking directly at checkbox in myDetectionToolbarWidget2
		if not self.detectToolbarWidget.crossHairCheckBox.isChecked():
			return

		pos = event[0]  ## using signal proxy turns original arguments into a tuple

		x = None
		y = None
		mousePoint = None
		inPlot = None
		if self.derivPlot.sceneBoundingRect().contains(pos):
			# deriv
			inPlot = 'derivPlot'
			self.crosshairDict[inPlot]['h'].show()
			self.crosshairDict[inPlot]['v'].show()
			mousePoint = self.derivPlot.vb.mapSceneToView(pos)
			# hide the horizontal in vmPlot
			self.crosshairDict['vmPlot']['v'].show()
			self.crosshairDict['vmPlot']['h'].hide()

		elif self.vmPlot.sceneBoundingRect().contains(pos):
			# vm
			inPlot = 'vmPlot'
			self.crosshairDict[inPlot]['h'].show()
			self.crosshairDict[inPlot]['v'].show()
			mousePoint = self.vmPlot.vb.mapSceneToView(pos)
			# hide the horizontal in derivPlot
			self.crosshairDict['derivPlot']['v'].show()
			self.crosshairDict['derivPlot']['h'].hide()

		elif self.clipPlot.sceneBoundingRect().contains(pos):
			# clip
			inPlot = 'clipPlot'
			self.crosshairDict[inPlot]['h'].show()
			self.crosshairDict[inPlot]['v'].show()
			mousePoint = self.clipPlot.vb.mapSceneToView(pos)
			# hide the horizontal/vertical in both derivPlot and vmPlot

		if inPlot is not None and mousePoint is not None:
			self.crosshairDict[inPlot]['h'].setPos(mousePoint.y())
			self.crosshairDict[inPlot]['v'].setPos(mousePoint.x())

		if inPlot == 'derivPlot':
			self.crosshairDict['vmPlot']['v'].setPos(mousePoint.x())
		if inPlot == 'vmPlot':
			self.crosshairDict['derivPlot']['v'].setPos(mousePoint.x())

		# hide
		if inPlot in ['derivPlot', 'vmPlot']:
			# hide h/v in clipPlot
			self.crosshairDict['clipPlot']['h'].hide()
			self.crosshairDict['clipPlot']['v'].hide()
		elif inPlot == 'clipPlot':
			# hide h/v in derivPlot and vmPlot
			self.crosshairDict['derivPlot']['h'].hide()
			self.crosshairDict['derivPlot']['v'].hide()
			self.crosshairDict['vmPlot']['h'].hide()
			self.crosshairDict['vmPlot']['v'].hide()

		if mousePoint is not None:
			x = mousePoint.x()
			y = mousePoint.y()

		# x/y can still be None
		self.detectToolbarWidget.setMousePositionLabel(x,y)

	'''
	def slot_dvdtMouseReleased(self, event):
		print('slot_dvdtMouseReleased() event:', event)
		print('  event.buttons()', event.buttons())
		pos = event.pos()
		items = self.view.scene().items(pos)
		print('  items:', items)
	'''

	def slotSelectSpike(self, sDict):
		print('detectionWidget.slotSelectSpike() sDict:', sDict)
		spikeNumber = sDict['SpikeNumber']
		doZoom = sDict['doZoom']
		self.selectSpike(spikeNumber, doZoom=doZoom)

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

	def old_exploreSpikes(self):
		"""
		use bScatterPlotWidget2.py to explore spike stat for one file

		todo:
			limit to start/stop
			don't reload, just reuse spike analysis in bAnalysis
		"""
		print('bDetectionWidget.exploreSpikes()')
		print('  todo:')
		print('    limit start/stop')
		print('    do not reload, just reuse spike analysis in bAnalysis')

		if self.ba is None:
			print('please detect first')

		# get the df rport
		saveFilePath = ''
		# todo: get start/stop from curent x-axis ???
		startSeconds = self.detectToolbarWidget.startSeconds.value()
		stopSeconds = self.detectToolbarWidget.stopSeconds.value()

		df0 = self.ba.report(startSeconds, stopSeconds)

		print(df0.head())

		# show it with bScatterPlotWidget
		path = ''
		categoricalList = []
		hueTypes = ['file'] # fix this
		analysisName = 'file' # fix this
		sortOrder = None
		statListDict = None # fix this sanpy.bAnalysisUtil.statList
		masterDf = df0
		parent = None
		sanpy.bScatterPlotMainWindow(
			path,
			categoricalList, hueTypes, analysisName, sortOrder,
			statListDict=statListDict, masterDf=masterDf, parent=None
		)

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

		# holy shit, this is bad, without this the app becomes non responsive???
		# if width > 1.0 then this whole app STALLS
		# default heme
		#self.setPen(pg.mkPen(color='k', width=1))
		# dark theme
		if forcePenColor is not None:
			penColor = forcePenColor
		elif self.detectionWidget.myMainWindow is None:
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
			print('Opening Export Trace Window')

			if self.myType == 'vm':
				xyUnits = ('Time (sec)', 'Vm (mV)')# todo: pass xMin,xMax to constructor
			elif self.myType == 'dvdt':
				xyUnits = ('Time (sec)', 'dV/dt (mV/ms)')# todo: pass xMin,xMax to constructor
			elif self.myType == 'meanclip':
				xyUnits = ('Time (ms)', 'Vm (mV)')# todo: pass xMin,xMax to constructor

			path = self.detectionWidget.ba.file

			xMin = None
			xMax = None
			if self.myType in ['clip', 'meanclip']:
				xMin, xMax = self.detectionWidget.clipPlot.getAxis('bottom').range
			else:
				xMin, xMax = self.detectionWidget.getXRange()
			print('  xMin:', xMin, 'xMax:', xMax)

			if self.myType in ['vm', 'dvdt']:
				xMargin = 2 # seconds
			else:
				xMargin = 2

			exportWidget = sanpy.bExportWidget(self.x, self.y,
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
			print('Reset Y-Axis', self.myType)
			self.detectionWidget.setAxisFull()
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
	#signalSelectSpike = QtCore.Signal(object, object) # spike number, doZoom

	def __init__(self, myPlots, detectionWidget, parent=None):
		super(myDetectToolbarWidget2, self).__init__(parent)

		self.myPlots = myPlots
		self.detectionWidget = detectionWidget # parent detection widget
		self.buildUI()

	def fillInDetectionParameters(self, tableRowDict):
		print('fillInDetectionParameters() tableRowDict:')
		print('  tableRowDict:', tableRowDict)
		dvdtThreshold = tableRowDict['dvdtThreshold']
		mvThreshold = tableRowDict['mvThreshold']
		startSeconds = tableRowDict['startSeconds']
		stopSeconds = tableRowDict['stopSeconds']

		# when number vvalues are set to 'empty' they come in as str ''
		if isinstance(dvdtThreshold,str) and len(dvdtThreshold)==0:
			dvdtThreshold = -1
		if isinstance(startSeconds,str) and len(startSeconds)==0:
			startSeconds = 0
		if isinstance(stopSeconds,str) and len(stopSeconds)==0:
			stopSeconds = self.detectionWidget.ba.abf.sweepX[-1] # max seconds

		self.dvdtThreshold.setValue(dvdtThreshold)
		self.vmThreshold.setValue(mvThreshold)
		self.startSeconds.setValue(startSeconds)
		self.stopSeconds.setValue(stopSeconds)

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
		#print('=== myDetectToolbarWidget2.on_button_click() name:', name)

		modifiers = QtWidgets.QApplication.keyboardModifiers()
		isShift = modifiers == QtCore.Qt.ShiftModifier

		if name == 'Detect dV/dt':
			dvdtThreshold = self.dvdtThreshold.value()
			vmThreshold = self.vmThreshold.value()
			#print('	dvdtThreshold:', dvdtThreshold)
			#print('	vmThreshold:', vmThreshold)
			if dvdtThreshold==-1:
				print('please set a threshold greater than 0')
				return
			self.detectionWidget.detect(dvdtThreshold, vmThreshold)

		elif name =='Detect mV':
			vmThreshold = self.vmThreshold.value()
			#print('	vmThreshold:', vmThreshold)
			# passing dvdtThreshold=None we will detect suing vmThreshold
			dvdtThreshold = None
			#print('	dvdtThreshold:', dvdtThreshold)
			#print('	vmThreshold:', vmThreshold)
			self.detectionWidget.detect(dvdtThreshold, vmThreshold)

		elif name == 'Reset All Axes':
			self.detectionWidget.setAxisFull()

		elif name == 'Save Spike Report':
			print('"Save Spike Report" isShift:', isShift)
			self.detectionWidget.save(alsoSaveTxt=isShift)

		#elif name == 'Explore':
		#	# open bScatterPlot2 for one recording
		#	self.detectionWidget.exploreSpikes()

		#elif name == 'Error':
		#	self.detectionWidget.ba.errorReport()

		elif name == 'Go':
			spikeNumber = self.spikeNumber.value()
			doZoom = True
			self.detectionWidget.selectSpike(spikeNumber, doZoom, doEmit=True)

		elif name == '<<':
			spikeNumber = self.spikeNumber.value()
			spikeNumber -= 1
			if spikeNumber < 0:
				spikeNumber = 0
			self.spikeNumber.setValue(spikeNumber)
			self.on_button_click('Go')

		elif name == '>>':
			spikeNumber = self.spikeNumber.value()
			spikeNumber += 1
			if spikeNumber > self.detectionWidget.ba.numSpikes - 1:
				spikeNumber = self.detectionWidget.ba.numSpikes - 1
			self.spikeNumber.setValue(spikeNumber)
			self.on_button_click('Go')

		else:
			print('on_button_click() did not understand button:', name)

	def on_check_click(self, checkbox, idx):
		isChecked = checkbox.isChecked()
		print('on_check_click() text:', checkbox.text(), 'isChecked:', isChecked, 'idx:', idx)
		if idx == 'Clips':
			self.detectionWidget.toggleClips(isChecked)
		elif idx == 'dV/dt':
			self.detectionWidget.toggle_dvdt(isChecked)
		elif idx == 'Scatter':
			self.detectionWidget.toggle_scatter(isChecked)
		elif idx == 'Errors':
			self.detectionWidget.toggle_errorTable(isChecked)
		#elif idx == 'Show Vm':
		#	self.detectionWidget.toggle_vm(isChecked)
		else:
			# Toggle overlay of stats like spike peak.
			# assuming idx is int !!!
			self.detectionWidget.togglePlot(idx, isChecked)

	def on_crosshair_clicked(self, value):
		print('on_crosshair_clicked() value:', value)
		onOff = value==2
		self.detectionWidget.toggleCrosshair(onOff)

	def buildUI(self):
		#self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))

		myPath = os.path.dirname(os.path.abspath(__file__))

		windowOptions = self.detectionWidget.getMainWindowOptions()
		detectDvDt = 20
		detectMv = -20
		showDvDt = True
		showClips = False
		showScatter = True
		if windowOptions is not None:
			detectDvDt = windowOptions['detect']['detectDvDt']
			detectMv = windowOptions['detect']['detectMv']
			showDvDt = windowOptions['display']['showDvDt']
			showClips = windowOptions['display']['showClips']
			showScatter = windowOptions['display']['showScatter']

		mystylesheet_css = os.path.join(myPath, 'css', 'mystylesheet.css')
		if os.path.isfile(mystylesheet_css):
			with open(mystylesheet_css) as f:
				myStyleSheet = f.read()

		self.setFixedWidth(330)
		self.mainLayout = QtWidgets.QVBoxLayout(self)
		self.mainLayout.setAlignment(QtCore.Qt.AlignTop)

		# IMPLEMENT SWEEPS AND
		# PUT THIS BACK IN
		'''
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
		'''

		#
		# detection parameters group
		detectionGroupBox = QtWidgets.QGroupBox('Detection')
		detectionGroupBox.setStyleSheet(myStyleSheet)

		detectionGridLayout = QtWidgets.QGridLayout()

		buttonName = 'Detect dV/dt'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Detect Spikes Using BOTH dV/dt Threshold and minimum mV')
		button.clicked.connect(partial(self.on_button_click,buttonName))

		row = 0
		rowSpan = 1
		columnSpan = 2
		detectionGridLayout.addWidget(button, row, 0, rowSpan, columnSpan)

		self.dvdtThreshold = QtWidgets.QDoubleSpinBox()
		self.dvdtThreshold.setMinimum(-1e6)
		self.dvdtThreshold.setMaximum(+1e6)
		self.dvdtThreshold.setValue(detectDvDt)
		#self.dvdtThreshold.setValue(np.nan)
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
		#vmThresholdLabel = QtWidgets.QLabel('Vm Threshold (mV)')
		#self.addWidget(vmThresholdLabel, row, 1)

		#row += 1
		self.vmThreshold = QtWidgets.QDoubleSpinBox()
		self.vmThreshold.setMinimum(-1e6)
		self.vmThreshold.setMaximum(+1e6)
		self.vmThreshold.setValue(detectMv)
		detectionGridLayout.addWidget(self.vmThreshold, row, 2, rowSpan, columnSpan)

		# moved into a save group box
		'''
		# todo: remove after adding to save group box
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
		'''

		tmpRowSpan = 1
		tmpColSpan = 2

		# always the last row
		# todo: move this to status after detect
		'''
		row += 1
		self.numSpikesLabel = QtWidgets.QLabel('Number of Spikes: None')
		#self.numSpikesLabel.setObjectName('numSpikesLabel')
		detectionGridLayout.addWidget(self.numSpikesLabel, row, 0, tmpRowSpan, tmpColSpan)
		'''

		# todo: move this to status after detect
		'''
		self.spikeFreqLabel = QtWidgets.QLabel('Frequency: None')
		detectionGridLayout.addWidget(self.spikeFreqLabel, row, 2, tmpRowSpan, tmpColSpan)
		'''


		'''
		hBoxSpikeBrowser = self.buildSpikeBrowser()
		row += 1
		rowSpan = 1
		columnSpan = 4
		detectionGridLayout.addLayout(hBoxSpikeBrowser, row, 0, rowSpan, columnSpan)
		'''

		# finalize
		detectionGroupBox.setLayout(detectionGridLayout)
		self.mainLayout.addWidget(detectionGroupBox)

		#
		# save with range
		#
		saveGroupBox = QtWidgets.QGroupBox('Save')
		saveGroupBox.setStyleSheet(myStyleSheet)

		saveGridLayout = QtWidgets.QGridLayout()

		row = 0
		buttonName = 'Save Spike Report'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Save Detected Spikes to Excel file')
		button.setStyleSheet("background-color: green")
		button.clicked.connect(partial(self.on_button_click,buttonName))
		#self.mainLayout.addWidget(button)
		rowSpan=1
		colSpan = 4
		saveGridLayout.addWidget(button, row , 0, rowSpan, colSpan)

		row += 1
		startSeconds = QtWidgets.QLabel('From (Sec)')
		saveGridLayout.addWidget(startSeconds, row, 0)
		#
		#row += 1
		self.startSeconds = QtWidgets.QDoubleSpinBox()
		self.startSeconds.setMinimum(-1e6)
		self.startSeconds.setMaximum(+1e6)
		self.startSeconds.setKeyboardTracking(False)
		self.startSeconds.setValue(0)
		self.startSeconds.valueChanged.connect(self.on_start_stop)
		#self.startSeconds.editingFinished.connect(self.on_start_stop)
		saveGridLayout.addWidget(self.startSeconds, row, 1)
		#
		stopSeconds = QtWidgets.QLabel('To (Sec)')
		saveGridLayout.addWidget(stopSeconds, row, 2)

		self.stopSeconds = QtWidgets.QDoubleSpinBox()
		self.stopSeconds.setMinimum(-1e6)
		self.stopSeconds.setMaximum(+1e6)
		self.stopSeconds.setKeyboardTracking(False)
		self.stopSeconds.setValue(0)
		self.stopSeconds.valueChanged.connect(self.on_start_stop)
		#self.stopSeconds.editingFinished.connect(self.on_start_stop)
		saveGridLayout.addWidget(self.stopSeconds, row, 3)

		# final
		saveGroupBox.setLayout(saveGridLayout)
		self.mainLayout.addWidget(saveGroupBox)

		#
		# display  group
		displayGroupBox = QtWidgets.QGroupBox('Display')
		displayGroupBox.setStyleSheet(myStyleSheet)

		displayGridLayout = QtWidgets.QGridLayout()

		# todo: remove 'reset all axes' and leave it in right-click
		# 20210426 removed
		'''
		row = 0
		buttonName = 'Reset All Axes'
		button = QtWidgets.QPushButton(buttonName)
		#button.setToolTip('Detect Spikes')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		displayGridLayout.addWidget(button, row, 0)
		'''

		row = 0

		self.crossHairCheckBox = QtWidgets.QCheckBox('Crosshair')
		self.crossHairCheckBox.setChecked(False)
		self.crossHairCheckBox.stateChanged.connect(self.on_crosshair_clicked)
		tmpRowSpan = 1
		tmpColSpan = 1
		displayGridLayout.addWidget(self.crossHairCheckBox, row, 0, tmpRowSpan, tmpColSpan)

		# x/y coordinates of mouse in each of derivPlot, vmPlot, clipPlot)
		self.mousePositionLabel = QtWidgets.QLabel('x:None\ty:None')
		displayGridLayout.addWidget(self.mousePositionLabel, row, 1, tmpRowSpan, tmpColSpan)

		hBoxSpikeBrowser = self.buildSpikeBrowser()
		row += 1
		rowSpan = 1
		columnSpan = 2
		displayGridLayout.addLayout(hBoxSpikeBrowser, row, 0, rowSpan, columnSpan)

		# a number of stats that will get overlaid on dv/dt and Vm
		#row += 1
		row += 1
		col = 0
		for idx, plot in enumerate(self.myPlots):
			#print('humanName:', plot['humanName'])
			humanName = plot['humanName']
			isChecked = plot['plotIsOn']
			styleColor = plot['styleColor']
			checkbox = QtWidgets.QCheckBox(humanName)
			checkbox.setChecked(isChecked)
			#checkbox.setStyleSheet(styleColor) # looks really ugly
			#checkbox.stateChanged.connect(lambda:self.on_check_click(checkbox))
			checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,idx))
			# append
			displayGridLayout.addWidget(checkbox, row, col)
			# increment
			col += 1
			if col == 2: # we only have col 0/1, nx2 grid
				col = 0
				row += 1

		# finalize
		displayGroupBox.setLayout(displayGridLayout)
		self.mainLayout.addWidget(displayGroupBox)

		#
		# plots  group
		plotGroupBox = QtWidgets.QGroupBox('Plots')
		plotGroupBox.setStyleSheet(myStyleSheet)

		plotGridLayout = QtWidgets.QGridLayout()

		# add widgets
		row = 0
		col = 0
		show_dvdt_checkbox = QtWidgets.QCheckBox('dV/dt')
		show_dvdt_checkbox.setChecked(showDvDt)
		show_dvdt_checkbox.stateChanged.connect(partial(self.on_check_click,show_dvdt_checkbox,'dV/dt'))
		plotGridLayout.addWidget(show_dvdt_checkbox, row, col)

		row = 0
		col = 1
		checkbox = QtWidgets.QCheckBox('Clips')
		checkbox.setChecked(showClips)
		checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Clips'))
		plotGridLayout.addWidget(checkbox, row, col)

		row = 0
		col = 2
		checkbox = QtWidgets.QCheckBox('Scatter')
		checkbox.setChecked(showScatter)
		checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Scatter'))
		plotGridLayout.addWidget(checkbox, row, col)

		row = 0
		col = 3
		checkbox = QtWidgets.QCheckBox('Errors')
		checkbox.setChecked(False)
		checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Errors'))
		plotGridLayout.addWidget(checkbox, row, col)

		'''
		row = 0
		col = 3
		buttonName = 'Explore'
		spikeExploreButton = QtWidgets.QPushButton(buttonName)
		spikeExploreButton.setToolTip('Explore spike measurements')
		#spikeExploreButton.setStyleSheet("background-color: green")
		spikeExploreButton.clicked.connect(partial(self.on_button_click, buttonName))
		self.mainLayout.addWidget(spikeExploreButton)
		'''

		# finalize
		plotGroupBox.setLayout(plotGridLayout)
		self.mainLayout.addWidget(plotGroupBox)

	def buildSpikeBrowser(self):
		#
		# row for (error report, spike #, go, prev, next)
		hBoxSpikeBrowser = QtWidgets.QHBoxLayout()

		'''
		buttonName = 'Error'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Print Spike Errors')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		#hBoxSpikeBrowser.addStretch()
		hBoxSpikeBrowser.addWidget(button)
		'''

		# spike number
		self.spikeNumber = QtWidgets.QSpinBox()
		self.spikeNumber.setMinimum(0)
		self.spikeNumber.setMaximum(+1e6)
		self.spikeNumber.setKeyboardTracking(False)
		self.spikeNumber.setValue(0)
		#self.spikeNumber.valueChanged.connect(self.on_spike_number)
		hBoxSpikeBrowser.addWidget(self.spikeNumber)

		buttonName = 'Go'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Go To Spike Number')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		hBoxSpikeBrowser.addWidget(button)

		buttonName = '<<'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Previous Spike')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		hBoxSpikeBrowser.addWidget(button)

		buttonName = '>>'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Next Spike')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		hBoxSpikeBrowser.addWidget(button)

		return hBoxSpikeBrowser

	def setMousePositionLabel(self, x, y):
		if x is not None:
			x = round(x,4) # 4 to get 10kHz precision, 0.0001
		if y is not None:
			y = round(y,2)
		labelStr = f'x:{x}   y:{y}'
		self.mousePositionLabel.setText(labelStr)
		self.mousePositionLabel.repaint()

	def slotSelectSpike(self, eDict):
		spikeNumber = eDict['SpikeNumber']
		self.spikeNumber.setValue(spikeNumber)

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
	ba.spikeDetect(dvdtThreshold=50, vmThreshold=-20, medianFilter=0)
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
