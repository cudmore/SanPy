'''
Author: Robert H Cudmore
Date: 20190225
'''

import os

import numpy as np
import scipy.signal

import matplotlib.pyplot as plt

import pyabf # see: https://github.com/swharden/pyABF

'''
The bAnalysis class wraps a pyabf file and adds spike detection and plotting.

Instantiate a bAnalysis object with a .abf file

The underlying pyabf object is always available as self.abf

Usage:
	ba = bAnalysis('data/19114001.abf')
	print(ba) # prints info about underlying abf file
	ba.plotDeriv()
	ba.spikeDetect(dVthresholdPos=100)
	ba.plotSpikes()
	ba.plotClips()
'''
class bAnalysis:
	def __init__(self, file=None):
		self.file = file
		self._abf = None
		self.spikeTimes = [] # created in self.spikeDetect()
		self.spikeClips = [] # created in self.spikeDetect()

		if not os.path.isfile(file):
			print('error: bAnalysis file does not exist "' + file + '""')
			return None

		self._abf = pyabf.ABF(file)
		
		self.currentSweep = None
		self.setSweep(0)

	############################################################
	# access to underlying pyabf object (self.abf)
	############################################################
	@property
	def abf(self):
		return self._abf

	@property
	def dataPointsPerMs(self):
		return self.abf.dataPointsPerMs
		
	def setSweep(self, sweepNumber):
		#todo: check that sweepNumber is in self.abf.sweepList
		if sweepNumber not in self.abf.sweepList:
			print('error: bAnalysis.setSweep() did not find sweep', sweepNumber, ', sweepList =', self.abf.sweepList)
		else:
			self.currentSweep = sweepNumber
			self.abf.setSweep(sweepNumber)

	@property
	def sweepList(self):
		return self.abf.sweepList

	############################################################
	# spike detection
	############################################################
	def spikeDetect(self, dVthresholdPos=100):
		'''
		spike detect the current sweep and put results into spikeTime[currentSweep]
		'''
		
		# check dvdt to select threshold for an action-potential
		sweepDeriv = np.diff(self.abf.sweepY)

		# scale it to V/S (mV/ms)
		sweepDeriv = sweepDeriv * self.abf.dataRate / 1000

		# add an initial point so it is the same length as raw data in abf.sweepY
		sweepDeriv=np.concatenate(([0],sweepDeriv))

		#spikeTimes = _where_cross(sweepDeriv,dVthresholdPos)
		Is=np.where(sweepDeriv>dVthresholdPos)[0]
		Is=np.concatenate(([0],Is))
		Ds=Is[:-1]-Is[1:]+1
		self.spikeTimes = Is[np.where(Ds)[0]+1]

		#
		# if there are doubles, throw-out the second one
		if 1:
			refractory_ms = 10 # remove spike [i] if it occurs within refractory_ms of spike [i-1]
			lastGood = 0 # first spike [0] will always be good, there is no spike [i-1]
			for i in range(len(self.spikeTimes)):
				if i==0:
					# first spike is always good
					continue
				dPoints = self.spikeTimes[i] - self.spikeTimes[lastGood]
				if dPoints < self.abf.dataPointsPerMs*refractory_ms:
					# remove spike time [i]
					self.spikeTimes[i] = 0
				else:
					# spike time [i] was good
					lastGood = i
			# regenerate self.spikeTimes by throwing out any spike time that does not pass 'if spikeTime'
			# spikeTimes[i] that were set to 0 above (they were too close to the previous spike)
			# will not pass 'if spikeTime', as 'if 0' evaluates to False
			self.spikeTimes = [spikeTime for spikeTime in self.spikeTimes if spikeTime]

		print('bAnalysis.spikeDetect() detected ', len(self.spikeTimes), 'spikes')

		#
		# build up a list of spike clips
		clipWidth_ms = 100
		clipWidth_pnts = clipWidth_ms * self.abf.dataPointsPerMs
		halfClipWidth_pnts = int(clipWidth_pnts/2)

		# make one x axis clip with the threshold crossing at 0
		self.spikeClips_x = [(x-halfClipWidth_pnts)/self.abf.dataPointsPerMs for x in range(clipWidth_pnts)]

		self.spikeClips = []
		for spikeTime in self.spikeTimes:
			currentClip = self.abf.sweepY[spikeTime-halfClipWidth_pnts:spikeTime+halfClipWidth_pnts]
			self.spikeClips.append(currentClip)

	@property
	def numSpikes(self):
		'''
		Returns the number of spikes, assumes self.spikeDetect(dVthreshold)
		'''
		return len(self.spikeTimes)

	#############################
	# plot functions
	#############################
	def plotDeriv(self, medianFilter=0):
		'''
		Plot both Vm and the derivative of Vm (dV/dt).
		
		Parameters:
			medianFilter:	0 is no filtering
							Integer greater than 0 specifies the number of points
		'''

		if medianFilter > 0:
			yAxisLabel = 'filtered '
			vm = scipy.signal.medfilt(self.abf.sweepY,medianFilter)
		else:
			yAxisLabel = ''
			vm = self.abf.sweepY

		sweepDeriv = np.diff(vm) # first derivative
		sweepDeriv2 = np.diff(sweepDeriv) # second derivative

		# scale it to V/S (mV/ms)
		sweepDeriv = sweepDeriv * self.abf.dataRate / 1000
		sweepDeriv2 = sweepDeriv2 * self.abf.dataRate / 1000

		# add an initial point so it is the same length as raw data in abf.sweepY
		sweepDeriv = np.concatenate(([0],sweepDeriv))
		sweepDeriv2 = np.concatenate(([0],sweepDeriv2))

		grid = plt.GridSpec(3, 1, wspace=0.2, hspace=0.4)

		fig = plt.figure()
		ax1 = fig.add_subplot(grid[0,0])
		ax2 = fig.add_subplot(grid[1,0], sharex=ax1)
		ax3 = fig.add_subplot(grid[2,0], sharex=ax1)


		ax1.plot(vm)
		ax1.set_ylabel(yAxisLabel + 'Vm (mV)')

		ax2.plot(sweepDeriv)
		ax2.set_ylabel('dV/dt')

		ax3.plot(sweepDeriv2)
		ax3.set_ylabel('dV/dt (2)')


	def plotSpikes(self, all=True, oneSpikeNumber=None, ax=None):
		'''
		Plot Vm with a detected spikes overlaid
		'''
		if ax is None:
			grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

			fig = plt.figure(figsize=(10, 8))
			ax = fig.add_subplot(grid[0, 0:]) #Vm, entire sweep
				
		# plot vm
		ax.plot(self.abf.sweepX, self.abf.sweepY, 'k')

		# plot all spike times
		for spikeTime in self.spikeTimes:
			ax.plot(self.abf.sweepX[spikeTime], self.abf.sweepY[spikeTime], 'og')

		# plot one spike time as a red circle
		line = None
		if oneSpikeNumber is not None:
			oneSpikeTime = self.spikeTimes[oneSpikeNumber]
			line, = ax.plot(self.abf.sweepX[oneSpikeTime], self.abf.sweepY[oneSpikeTime], 'or')

		ax.set_ylabel('Vm (mV)')
		ax.set_xlabel('Time (sec)')

		return line

	def plotClips(self, oneSpikeNumber=None, ax=None):
		'''
		Plot clips of all detected spikes

		Clips are created in self.spikeDetect() and default to clipWidth_ms = 100 ms
		'''
		if ax is None:
			grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

			fig = plt.figure(figsize=(10, 8))
			ax = fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		for i in range(len(self.spikeClips)):
			try:
				ax.plot(self.spikeClips_x, self.spikeClips[i], 'k')
			except (ValueError) as e:
				print('exception in bAnalysis.plotClips() while plotting clips', i)
				
		# plot current clip
		line = None
		if oneSpikeNumber is not None:
			try:
				line, = ax.plot(self.spikeClips_x, self.spikeClips[oneSpikeNumber], 'r')
			except (ValueError) as e:
				print('exception in bAnalysis.plotClips() while plotting oneSpikeNumber', oneSpikeNumber)

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
		line, = ax.plot(filteredClip, dvdt)
		
		ax.set_ylabel('filtered dV/dt')
		ax.set_xlabel('filtered Vm (mV)')
	
		return line
		
	############################################################
	# utility
	############################################################
	def __str__(self):
		retStr = 'file: ' + self.file + '\n' + str(self.abf)
		return retStr

if __name__ == '__main__':
	ba = bAnalysis('../data/19114001.abf')
	print(ba.dataPointsPerMs)
	
	