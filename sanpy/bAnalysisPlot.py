'''
Robert Cudmore
20190328

Helper class to plot results of bAnalysis object
'''

import numpy as np
import scipy.signal

import matplotlib.pyplot as plt

import sanpy

class bPlot:
	def __init__(self, ba=None):
		"""
		ba: bAnalysis object
		"""
		self.ba = ba

	#############################
	# plot functions
	#############################
	def plotDeriv(self, fig=None):
		'''
		Plot both Vm and the derivative of Vm (dV/dt).

		Parameters:
			medianFilter:	0 is no filtering
							Integer greater than 0 specifies the number of points
		'''

		ba = self.ba

		grid = plt.GridSpec(2, 1, wspace=0.2, hspace=0.4)
		if fig is None:
			fig = plt.figure(figsize=(10, 8))
		ax1 = fig.add_subplot(grid[0,0])
		ax2 = fig.add_subplot(grid[1,0], sharex=ax1)
		#ax3 = fig.add_subplot(grid[2,0], sharex=ax1)


		ax1.plot(ba.abf.sweepX, ba.abf.sweepY, label='Vm (mV)')
		ax1.set_ylabel('Vm (mV)')

		ax2.plot(ba.abf.sweepX, ba.filteredDeriv)
		ax2.set_ylabel('dV/dt')
		ax2.set_xlabel('Seconds')

		#ax3.plot(self.abf.sweepX, sweepDeriv2)
		#ax3.set_ylabel('dV/dt (2)')

		# spike detect and append
		#ax1.plot(ba.abf.sweepX[spikeTimes], ba.abf.sweepY[spikeTimes], 'or', label='threshold')
		#ax2.plot(ba.abf.sweepX[spikeTimes], ba.filteredDeriv[spikeTimes], 'or')

		return fig

	def plotRaw(ba, lineWidth=1, color='k', ax=None):
		"""
		plot raw recording
		"""
		if ax is None:
			grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

			fig = plt.figure(figsize=(10, 8))
			ax = fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		#ax.plot(ba.abf.sweepX, ba.abf.sweepY, 'k')
		ax.plot(ba.abf.sweepX, ba.abf.sweepY, '-', c=color, linewidth=lineWidth) # fmt = '[marker][line][color]'

		ax.set_ylabel('Vm (mV)')
		ax.set_xlabel('Time (sec)')

	def plotSpikes(self, oneSpikeNumber=None, ax=None, xMin=None, xMax=None):
		'''
		Plot Vm with spike analysis overlaid as symbols

		oneSpikeNumber: If specified will select one spike with a yellow symbol
		ax: If specified will plot into a MatPlotLib axes
		xMin/xMax: if specified will set_xlim(xMin, xMax)
		'''

		ba = self.ba

		fig = None
		if ax is None:
			grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

			fig = plt.figure(figsize=(10, 8))
			ax = fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		# plot vm
		ax.plot(ba.abf.sweepX, ba.abf.sweepY, 'k')

		# plot all spike times (threshold crossings)
		"""
		for spikeTime in ba.spikeTimes:
			ax.plot(ba.abf.sweepX[spikeTime], ba.abf.sweepY[spikeTime], 'xg')
		"""
		ax.plot(ba.abf.sweepX[ba.spikeTimes], ba.abf.sweepY[ba.spikeTimes], 'pg')

		# plot the peak
		peakPntList = [spikeDict['peakPnt'] for spikeDict in ba.spikeDict]
		ax.plot(ba.abf.sweepX[peakPntList], ba.abf.sweepY[peakPntList], 'or')

		#
		# plot one spike time as a yellow circle
		line = None
		if oneSpikeNumber is not None:
			oneSpikeTime = ba.spikeTimes[oneSpikeNumber]
			line, = ax.plot(ba.abf.sweepX[oneSpikeTime], ba.abf.sweepY[oneSpikeTime], 'oy')

		ax.set_ylabel('Vm (mV)')
		ax.set_xlabel('Time (sec)')

		# set the x-axis of the plot
		if xMin is not None and xMax is not None:
			ax.set_xlim([xMin,xMax])

		# 20190816, was return line
		# not sure if this break anything???
		#return fig, ax
		return fig

	def plotTimeSeries(ba, stat, halfWidthIdx=0, ax=None):
		""" Plot a given spike parameter"""
		if stat == 'peak':
			yStatName = 'peakVal'
			yStatLabel = 'Spike Peak (mV)'
		if stat == 'preMin':
			yStatName = 'preMinVal'
			yStatLabel = 'Pre Min (mV)'
		if stat == 'halfWidth':
			yStatName = 'widthPnts'
			yStatLabel = 'Spike Half Width (ms)'

		#
		# pull
		statX = []
		statVal = []
		for i, spike in enumerate(ba.spikeDict):
			if i==0 or i==len(ba.spikeTimes)-1:
				continue
			else:
				statX.append(spike['peakSec'])
				if stat == 'halfWidth':
					statVal.append(spike['widths'][halfWidthIdx]['widthMs'])
				else:
					statVal.append(spike[yStatName])

		#
		# plot
		if ax is None:
			grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

			fig = plt.figure(figsize=(10, 8))
			ax = fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		ax.plot(statX, statVal, 'o-k')

		ax.set_ylabel(yStatLabel)
		ax.set_xlabel('Time (sec)')

		return statVal

	def plotISI(ba, ax=None):
		""" Plot the inter-spike-interval (sec) between each spike threshold"""
		#
		# pull
		spikeTimes_sec = [x/ba.abf.dataPointsPerMs/1000 for x in ba.spikeTimes]
		isi = np.diff(spikeTimes_sec)
		isi_x = spikeTimes_sec[0:-1]

		#
		# plot
		if ax is None:
			grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

			fig = plt.figure(figsize=(10, 8))
			ax = fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		ax.plot(isi_x, isi, 'o-k')

		ax.set_ylabel('Inter-Spike-Interval (sec)')
		ax.set_xlabel('Time (sec)')

	def plotClips(ba, oneSpikeNumber=None, ax=None):
		'''
		Plot clips of all detected spikes

		Clips are created in self.spikeDetect() and default to clipWidth_ms = 100 ms
		'''
		if ax is None:
			grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

			fig = plt.figure(figsize=(10, 8))
			ax = fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		for i in range(len(ba.spikeClips)):
			try:
				ax.plot(ba.spikeClips_x, ba.spikeClips[i], 'k')
			except (ValueError) as e:
				print('exception in bPlot.plotClips() while plotting clips', i)

		#
		# plot current clip
		line = None
		if oneSpikeNumber is not None:
			try:
				line, = ax.plot(ba.spikeClips_x, ba.spikeClips[oneSpikeNumber], 'y')
			except (ValueError) as e:
				print('exception in bPlot.plotClips() while plotting oneSpikeNumber', oneSpikeNumber)

		ax.set_ylabel('Vm (mV)')
		ax.set_xlabel('Time (ms)')

		return line

	def plotPhasePlot(self, oneSpikeNumber=None, ax=None):
		if ax is None:
			grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

			fig = plt.figure(figsize=(10, 8))
			ax = fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		filteredClip = scipy.signal.medfilt(self.spikeClips[oneSpikeNumber],3)
		dvdt = np.diff(filteredClip)
		# add an initial point so it is the same length as raw data in abf.sweepY
		dvdt = np.concatenate(([0],dvdt))
		line, = ax.plot(filteredClip, dvdt, 'y')

		ax.set_ylabel('filtered dV/dt')
		ax.set_xlabel('filtered Vm (mV)')

		return line

def test():
	# load abf
	abfPath = '../data/19114000.abf'
	ba = sanpy.bAnalysis(abfPath)
	if ba.loadError:
		print('did not load file:', abfPath)
		return

	# detect
	dDict = ba.getDefaultDetection()
	dDict['dvdThreshold'] = 50
	ba.spikeDetect(dDict)

	# plot
	bp = bPlot(ba)
	fig = bp.plotDeriv()

	fig = bp.plotSpikes(oneSpikeNumber=10)

	plt.show()

if __name__ == '__main__':
	test()
