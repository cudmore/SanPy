# 20210129

import os
import numpy as np

class bAbfText:
	"""
	mimic a pyabf file to load from a text file
	"""
	def __init__(self, path):
		"""
		path: path to .csv file with columns
			time (seconds)
			vm
		"""
		print('bAbfText.__init__() path:', path)

		tmpNumPy = np.loadtxt(path, skiprows=1, delimiter=',')
		self.sweepX = tmpNumPy[:,0]
		self.sweepY = tmpNumPy[:,1]

		# linescan is like
		# 'secondsPerLine': 0.0042494285714285715,
		# 1 / secondsPerLine = 235.32
		secondsPerSample = self.sweepX[1] - self.sweepX[0]
		samplesPerSecond = 1 / secondsPerSample
		self.dataRate = samplesPerSecond #235 #10000 # samples per second
		# todo: calculat from dataRate
		secondsPerSample = 1 / samplesPerSecond
		msPerSample = secondsPerSample * 1000
		samplesPerMs = 1 / msPerSample

		self.dataPointsPerMs = samplesPerMs #4.255 #1/235*1000,10 # 10 kHz

		print('  bAbfText secondsPerSample:', secondsPerSample, 'seconds/sample')
		print('  bAbfText self.dataRate:', self.dataRate, 'samples/second')
		print('  bAbfText self.dataPointsPerMs:', self.dataPointsPerMs)

		self.sweepList = [0]

	def setSweep(self, sweep):
		pass
