# 20210609
import numpy as np
import scipy.signal

import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin

class plotRecording(sanpyPlugin):
	"""
	Example of matplotlib plugin.

	"""
	myHumanName = 'Plot Reccording'

	def __init__(self, **kwargs):
		super(plotRecording, self).__init__('plotRecording', **kwargs)
		self.plot()

	def plot(self):
		if self.ba is None:
			return

		self.mplWindow() # assigns self (fig, ax)

		sweepX = self.ba.sweepX
		sweepY = self.ba.sweepY

		# comma is critical
		self.line, = self.ax.plot(sweepX, sweepY, '-', linewidth=0.5)

		thresholdSec = self.ba.getStat('thresholdSec')
		thresholdVal = self.ba.getStat('thresholdVal')
		if thresholdSec is None and thresholdVal is None:
			self.lineDetection, = self.ax.plot([], [], 'o')
		else:
			# comma is critical
			self.lineDetection, = self.ax.plot(thresholdSec, thresholdVal, 'or')

		plt.show()

	def replot(self):
		"""
		bAnalysis has been updated, replot
		"""
		logger.info('xxx')

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
	path = '/Users/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(path)
	ba.spikeDetect()

	# create plugin
	ap = plotRecording(ba=ba)

	ap.plot()

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
