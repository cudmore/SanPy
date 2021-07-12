# 20210609
import numpy as np
import scipy.signal

import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

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
		self.plot()

	def plot(self):
		if self.ba is None:
			return

		self.mplWindow() # assigns (self.fig, self.ax)

		sweepX = self.ba.sweepX
		sweepY = self.ba.filteredVm  # sweepY
		# comma is critical
		self.line, = self.ax.plot(sweepX, sweepY, '-', linewidth=0.5)

		thresholdSec = self.ba.getStat('thresholdSec')
		thresholdVal = self.ba.getStat('thresholdVal')
		if thresholdSec is None and thresholdVal is None:
			self.lineDetection, = self.ax.plot([], [], 'o')
		else:
			# comma is critical
			self.lineDetection, = self.ax.plot(thresholdSec, thresholdVal, 'or')

		peakSec = self.ba.getStat('peakSec')
		#peakSec = [self.ba.pnt2Sec_(x) for x in peakPnt] # convert pnt to sec
		peakVal = self.ba.getStat('peakVal')
		if peakSec is None and peakVal is None:
			self.linePeak, = self.ax.plot([], [], 'o')
		else:
			# comma is critical
			self.linePeak, = self.ax.plot(peakSec, peakVal, 'or')

		preMinPnt = self.ba.getStat('preMinPnt')
		preMinSec = [self.ba.pnt2Sec_(x) for x in preMinPnt]
		preMinVal = self.ba.getStat('preMinVal')
		if preMinSec is None and preMinVal is None:
			self.linePreMin, = self.ax.plot([], [], 'og')
		else:
			# comma is critical
			self.linePreMin, = self.ax.plot(preMinSec, preMinVal, 'og')

		# 0 edd
		preLinearFitPnt0 = self.ba.getStat('preLinearFitPnt0')
		preLinearFitSec0 = [self.ba.pnt2Sec_(x) for x in preLinearFitPnt0]
		preLinearFitVal0 = self.ba.getStat('preLinearFitVal0')
		if preLinearFitSec0 is None and preLinearFitVal0 is None:
			self.linePreLinear0, = self.ax.plot([], [], 'o')
		else:
			# comma is critical
			self.linePreLinear0, = self.ax.plot(preLinearFitSec0, preLinearFitVal0, 'ob')

		# 1 edd
		preLinearFitPnt1 = self.ba.getStat('preLinearFitPnt1')
		preLinearFitSec1 = [self.ba.pnt2Sec_(x) for x in preLinearFitPnt1]
		preLinearFitVal1 = self.ba.getStat('preLinearFitVal1')
		if preLinearFitSec1 is None and preLinearFitVal1 is None:
			self.linePreLinear1, = self.ax.plot([], [], 'o')
		else:
			# comma is critical
			self.linePreLinear1, = self.ax.plot(preLinearFitSec1, preLinearFitVal1, 'ob')

		# draw line for edd
		xEdd, yEdd = self.getEddLines()
		self.lineEdd, = self.ax.plot(xEdd, yEdd, '--b')

		# hw(s)
		xHW, yHW = self.getHalfWidths()
		self.lineHW, = self.ax.plot(xHW, yHW, '-')

		plt.show()

	def replot(self):
		"""
		bAnalysis has been updated, replot
		"""
		logger.info('')

		sweepX = self.ba.sweepX
		sweepY = self.ba.sweepY
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
		for idx, spike in enumerate(range(self.ba.numSpikes)):
			dx = preLinearFitSec1[idx] - preLinearFitSec0[idx]
			dy = preLinearFitVal1[idx] - preLinearFitVal0[idx]

			lineLength = 4  # TODO: make this a function of spike frequency?

			x.append(preLinearFitSec0[idx])
			x.append(preLinearFitSec1[idx] + lineLength*dx)
			x.append(np.nan)

			y.append(preLinearFitVal0[idx])
			y.append(preLinearFitVal1[idx] + lineLength*dy)
			y.append(np.nan)

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
				risingVal = width['risingVal']
				fallingPnt = width['fallingPnt']
				fallingVal = width['fallingVal']

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

		self.ax.set_xlim(xMin, xMax)

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
	testPlot()
	#testLoad()
