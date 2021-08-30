# 20210609
import numpy as np
import scipy.signal

from PyQt5 import QtCore, QtWidgets, QtGui

import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
from sanpy import bAnalysis
from sanpy.interface.plugins import sanpyPlugin
from sanpy.bAnalysisUtil import statList

class plotRecording(sanpyPlugin):
	"""
	Example of matplotlib plugin.
	"""
	myHumanName = 'Plot Recording (matplotlib)'

	def __init__(self, **kwargs):
		super(plotRecording, self).__init__(**kwargs)

		# this is a very simple plugin, do not respond to changes in interface
		switchFile = self.responseTypes.switchFile
		self.toggleResponseOptions(switchFile, newValue=False)
		analysisChange = self.responseTypes.analysisChange
		self.toggleResponseOptions(analysisChange, newValue=False)
		#selectSpike = self.responseTypes.selectSpike
		#self.toggleResponseOptions(selectSpike, newValue=False)
		setAxis = self.responseTypes.setAxis
		self.toggleResponseOptions(setAxis, newValue=False)

		self.plot()

	def plot(self):
		if self.ba is None:
			return

		self.mplWindow2() # assigns (self.fig, self.ax)

		sweepX = self.ba.sweepX(sweepNumber=self.sweepNumber)
		sweepY = self.ba.filteredVm(sweepNumber=self.sweepNumber)  # sweepY

		self.sweepX = sweepX
		self.sweepY = sweepY

		# comma is critical
		self.line, = self.axs.plot(sweepX, sweepY, '-', linewidth=0.5)

		thresholdSec = self.ba.getStat('thresholdSec')
		thresholdVal = self.ba.getStat('thresholdVal')
		if thresholdSec is None and thresholdVal is None:
			self.lineDetection, = self.axs.plot([], [], 'o')
		else:
			# comma is critical
			self.lineDetection, = self.axs.plot(thresholdSec, thresholdVal, 'or')

		peakSec = self.ba.getStat('peakSec')
		peakVal = self.ba.getStat('peakVal')
		if peakSec is None and peakVal is None:
			self.linePeak, = self.axs.plot([], [], 'o')
		else:
			# comma is critical
			self.linePeak, = self.axs.plot(peakSec, peakVal, 'or')

		preMinPnt = self.ba.getStat('preMinPnt')
		preMinSec = [self.ba.pnt2Sec_(x) for x in preMinPnt]
		preMinVal = self.ba.getStat('preMinVal')
		if preMinSec is None and preMinVal is None:
			self.linePreMin, = self.axs.plot([], [], 'og')
		else:
			# comma is critical
			self.linePreMin, = self.axs.plot(preMinSec, preMinVal, 'og')

		# 0 edd
		preLinearFitPnt0 = self.ba.getStat('preLinearFitPnt0')
		preLinearFitSec0 = [self.ba.pnt2Sec_(x) for x in preLinearFitPnt0]
		preLinearFitVal0 = self.ba.getStat('preLinearFitVal0')
		if preLinearFitSec0 is None and preLinearFitVal0 is None:
			self.linePreLinear0, = self.axs.plot([], [], 'o')
		else:
			# comma is critical
			self.linePreLinear0, = self.axs.plot(preLinearFitSec0, preLinearFitVal0, 'ob')

		# 1 edd
		preLinearFitPnt1 = self.ba.getStat('preLinearFitPnt1')
		preLinearFitSec1 = [self.ba.pnt2Sec_(x) for x in preLinearFitPnt1]
		preLinearFitVal1 = self.ba.getStat('preLinearFitVal1')
		if preLinearFitSec1 is None and preLinearFitVal1 is None:
			self.linePreLinear1, = self.axs.plot([], [], 'o')
		else:
			# comma is critical
			self.linePreLinear1, = self.axs.plot(preLinearFitSec1, preLinearFitVal1, 'ob')

		# draw line for edd
		xEdd, yEdd = self.getEddLines()
		self.lineEdd, = self.axs.plot(xEdd, yEdd, '--b')

		# hw(s)
		xHW, yHW = self.getHalfWidths()
		self.lineHW, = self.axs.plot(xHW, yHW, '-')

		#plt.show()

	def replot(self):
		"""
		bAnalysis has been updated, replot
		"""
		logger.info('')

		sweepX = self.ba.sweepX(sweepNumber=self.sweepNumber)
		sweepY = self.ba.sweepY(sweepNumber=self.sweepNumber)

		self.sweepX = sweepX
		self.sweepY = sweepY

		self.line.set_data(sweepX, sweepY)

		thresholdSec = self.ba.getStat('thresholdSec')
		thresholdVal = self.ba.getStat('thresholdVal')
		if thresholdSec is None and thresholdVal is None:
			self.lineDetection.set_data([], [])
		else:
			self.lineDetection.set_data(thresholdSec, thresholdVal)

		self.ax.relim()
		self.ax.autoscale_view(True,True,True)
		plt.draw()

	def getEddLines(self):
		preLinearFitPnt0 = self.ba.getStat('preLinearFitPnt0')
		preLinearFitSec0 = [self.ba.pnt2Sec_(x) for x in preLinearFitPnt0]
		preLinearFitVal0 = self.ba.getStat('preLinearFitVal0')

		preLinearFitPnt1 = self.ba.getStat('preLinearFitPnt1')
		preLinearFitSec1 = [self.ba.pnt2Sec_(x) for x in preLinearFitPnt1]
		preLinearFitVal1 = self.ba.getStat('preLinearFitVal1')

		x = []
		y = []
		for idx in range(self.ba.numSpikes):
			try:
				dx = preLinearFitSec1[idx] - preLinearFitSec0[idx]
				dy = preLinearFitVal1[idx] - preLinearFitVal0[idx]
			except (IndexError) as e:
				logger.error(f'spike {idx} preLinearFitSec1:{len(preLinearFitSec1)} preLinearFitSec0:{len(preLinearFitSec0)}')
				logger.error(f'spike {idx} preLinearFitPnt1:{len(preLinearFitPnt1)} preLinearFitPnt0:{len(preLinearFitPnt0)}')

			lineLength = 4  # TODO: make this a function of spike frequency?

			try:
				x.append(preLinearFitSec0[idx])
				x.append(preLinearFitSec1[idx] + lineLength*dx)
				x.append(np.nan)

				y.append(preLinearFitVal0[idx])
				y.append(preLinearFitVal1[idx] + lineLength*dy)
				y.append(np.nan)
			except (IndexError) as e:
				logger.error(f'preLinearFitSec0:{len(preLinearFitSec0)} preLinearFitSec1:{len(preLinearFitSec1)}')
				logger.error(e)

		return x, y

	def getHalfWidths(self):
		"""Get x/y pair for plotting all half widths."""
		# defer until we know how many half-widths 20/50/80
		x = []
		y = []
		numPerSpike = 3  # rise/fall/nan
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
				#risingVal = width['risingVal']
				risingVal = self.sweepY[risingPnt]
				fallingPnt = width['fallingPnt']
				#fallingVal = width['fallingVal']
				fallingVal = self.sweepY[fallingPnt]

				if risingPnt is None or fallingPnt is None:
					# half-height was not detected
					continue

				risingSec = self.ba.pnt2Sec_(risingPnt)
				fallingSec = self.ba.pnt2Sec_(fallingPnt)

				x[xyIdx] = risingSec
				x[xyIdx+1] = fallingSec
				x[xyIdx+2] = np.nan
				# y
				y[xyIdx] = fallingVal  #risingVal, to make line horizontal
				y[xyIdx+1] = fallingVal
				y[xyIdx+2] = np.nan

				# each spike has 3x pnts: rise/fall/nan
				xyIdx += numPerSpike  # accounts for rising/falling/nan
			# end for width
		# end for spike
		return x, y

	def slot_selectSpike(self, eDict):
		logger.info(eDict)
		spikeNumber = eDict['spikeNumber']
		doZoom = eDict['doZoom']

		if spikeNumber is None:
			return

		if self.ba is None:
			return

		thresholdSec = self.ba.getStat('thresholdSec')
		spikeTime = thresholdSec[spikeNumber]
		xMin = spikeTime - 0.5
		xMax = spikeTime + 0.5

		self.axs.set_xlim(xMin, xMax)

		self.fig.canvas.draw()
		self.fig.canvas.flush_events()

def testPlot():
	import os
	file_path = os.path.realpath(__file__)  # full path to this file
	file_path = os.path.split(file_path)[0]  # folder for this file
	path = os.path.join(file_path, '../../../data/19114001.abf')

	ba = bAnalysis(path)
	if ba.loadError:
		print('error loading file')
		return
	ba.spikeDetect()

	# create plugin
	ap = plotRecording(ba=ba)

	#ap.plot()

	#ap.slotUpdateAnalysis()

def main():
	path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(path)
	ba.spikeDetect()
	print(ba.numSpikes)

	import sys
	app = QtWidgets.QApplication([])
	pr = plotRecording(ba=ba)
	pr.show()
	sys.exit(app.exec_())

def testLoad():
	import os, glob
	pluginFolder = '/Users/cudmore/sanpy_plugins'
	files = glob.glob(os.path.join(pluginFolder, '*.py'))
	for file in files:
		#if file.startswith('.'):
		#	continue
		if file.endswith('__init__.py'):
			continue
		print(file)
if __name__ == '__main__':
	#testPlot()
	#testLoad()
	main()
