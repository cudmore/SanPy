# 20210609
import numpy as np
import scipy.signal

import matplotlib.pyplot as plt

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
from sanpy.interface import aPlugin

class plotRecording(aPlugin):
	"""
	TODO: plugin should recieve slot() when
		(1) detection is run
		(2) spike is selected
		(3) file is changed
	"""
	def __init__(self, ba):
		super(plotRecording, self).__init__(ba)

	def plot(self):
		if self.ba is None:
			return

		grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

		width = 4
		height = 4
		self.fig = plt.figure(figsize=(width, height))
		self.ax = self.fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		self.ax.spines['right'].set_visible(False)
		self.ax.spines['top'].set_visible(False)

		sweepX = self.ba.sweepX
		sweepY = self.ba.sweepY
		self.line = self.ax.plot(sweepX, sweepY)

		plt.show()

	def slot_selectSpike(self, spikeNumber, doZoom):
		logger.info(f'spikeNumber:{spikeNumber} doZoom:{doZoom}')

		if spikeNumber is None:
			return

		if self.ba is None:
			return

		thresholdSec = self.ba.getStat('thresholdSec')
		spikeTime = thresholdSec[spikeNumber]
		xMin = spikeTime - 0.5
		xMax = spikeTime + 0.5

		print('  ', xMin, xMax)
		self.ax.set_xlim(xMin, xMax)

		self.fig.canvas.draw()
		self.fig.canvas.flush_events()

def testPlot():
	path = '/Users/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(path)
	ba.spikeDetect()

	# create plugin
	ap = plotRecording(ba)

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
	#testPlot()
	testLoad()
