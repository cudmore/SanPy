'''
Author: Robert H Cudmore
Date: 20190225

The bAnalysis class wraps a pyabf file and adds spike detection and plotting.

Instantiate a bAnalysis object with a .abf file name

The underlying pyabf object is always available as self.abf

Usage:
	ba = bAnalysis('data/19114001.abf')
	print(ba) # prints info about underlying abf file
	ba.plotDeriv()
	ba.spikeDetect(dVthresholdPos=100)
	ba.plotSpikes()
	ba.plotClips()

Detection:
	getDerivative() creates a median filtered derivative
	spikeDetect0() does threshold detection to generate a list of spike times
	spikeDetect() takes a list of spike times and performs detailed analysis on each spike
Reports:
	report() and report2() generate pandas data frames of the results and can easily by manipulated or saved
Plots:
	Plot vm, derivative, spike stats etc

Updates
	20190513, added self.VmThreshold

Acknowledgements
	https://github.com/swharden/pyABF

'''

import os, math, time, collections, datetime
import sys # for debugging to call sys.exit()
from collections import OrderedDict

import numpy as np
import pandas as pd

import scipy.signal
import matplotlib.pyplot as plt

import pyabf # see: https://github.com/swharden/pyABF

from bAnalysisUtil import bAnalysisUtil

class bAnalysis:
	def __init__(self, file=None):
		self.file = file # todo: change this to filePath
		self._abf = None

		#20190628
		self.detectionConfig = bAnalysisUtil()

		# detection parameters specified by user
		self.dateAnalyzed = None
		self.dVthreshold = None
		self.minSpikeVm = None # abb, 20190513
		self.medianFilter = None
		self.startSeconds = None
		self.stopSeconds = None

		self.spikeDict = [] # a list of dict

		self.spikeTimes = [] # created in self.spikeDetect()
		self.spikeClips = [] # created in self.spikeDetect()

		if not os.path.isfile(file):
			print('error: bAnalysis.__init__ file does not exist "' + file + '""')
			return None

		# instantiate and load abf file
		self._abf = pyabf.ABF(file)

		#20190621
		abfDateTime = self._abf.abfDateTime #2019-01-14 15:20:48.196000
		self.acqDate = abfDateTime.strftime("%Y-%m-%d")
		self.acqTime = abfDateTime.strftime("%H:%M:%S")

		self.currentSweep = None
		self.setSweep(0)

		self.filteredVm = []
		self.filteredDeriv = []
		self.spikeTimes = []

		self.thresholdTimes = None

		# keep track of the number of errors during spike detection
		self.numErrors = 0

	############################################################
	# access to underlying pyabf object (self.abf)
	############################################################
	@property
	def abf(self):
		return self._abf

	@property
	def dataPointsPerMs(self):
		return self.abf.dataPointsPerMs

	@property
	def sweepList(self):
		return self.abf.sweepList

	@property
	def numSweeps(self):
		return len(self.abf.sweepList)

	def setSweep(self, sweepNumber):
		if sweepNumber not in self.abf.sweepList:
			print('error: bAnalysis.setSweep() did not find sweep', sweepNumber, ', sweepList =', self.abf.sweepList)
			return False
		else:
			self.currentSweep = sweepNumber
			self.abf.setSweep(sweepNumber)
			return True

	@property
	def numSpikes(self):
		"""Returns the number of spikes, assumes self.spikeDetect(dVthreshold)"""
		return len(self.spikeTimes)

	@property
	def numSpikeErrors(self):
		return self.numErrors


	def getStat(self, xStat, yStat):
		def clean(val):
			if val is None:
				val = float('nan')
			return val
		# peakVal, peakSec
		#x = [spike[xStat] for spike in self.spikeDict]
		#y = [spike[yStat] for spike in self.spikeDict]
		x = [clean(spike[xStat]) for spike in self.spikeDict]
		y = [clean(spike[yStat]) for spike in self.spikeDict]
		return x, y
		
	############################################################
	# map human readable to backend stat
	############################################################
	'''
	def statNames_Init(self):
		"""
		Initialize list of stats and their mapping from human readable to backend
		"""
		statDict = collections.OrderedDict()
		statDict['Take Off Potential (s)'] = 'thresholdSec'
		statDict['Take Off Potential (mV)'] = 'thresholdVal'
		statDict['AP Peak (mV)'] = 'peakVal'
		statDict['AP Height (mV)'] = 'peakHeight'
		statDict['Pre AP Min (mV)'] = 'preMinVal'
		statDict['Post AP Min (mV)'] = 'postMinVal'
		statDict['AP Duration (ms)'] = 'apDuration_ms'
		# 'Early Diastolic Depol Rate (dV/s)'
		statDict['Early Diastolic Duration (ms)'] = 'earlyDiastolicDuration_ms'
		statDict['Diastolic Duration (ms)'] = 'diastolicDuration_ms'
		statDict['Max AP Upstroke (dV/dt)'] = 'preSpike_dvdt_max_val2'
		statDict['Max AP Upstroke (mV)'] = 'preSpike_dvdt_max_val'
		statDict['Max AP Repolarization (dV/dt)'] = 'postSpike_dvdt_min_val2'
		statDict['Max AP Repolarization (mV)'] = 'postSpike_dvdt_min_val'
		statDict['Inter-Spike-Interval (ms)'] = 'isi_ms'
		statDict['Cycle Length (ms)'] = 'cycleLength_ms'
		# 'halfWidth' # THIS HAS TO BE DYNAMIC ???
		statDict['Condition 1'] = 'Condition 1'
		statDict['Condition 2'] = 'Condition 2'
		statDict['Condition 3'] = 'Condition 3'

		# make a list of string from keys
		#myStatList = list(statDict.keys())
	'''

	############################################################
	# spike detection
	############################################################
	def getDerivative(self, medianFilter=0):
		if medianFilter > 0:
			if not medianFilter % 2:
				medianFilter += 1
				print('*** Warning: Please use an odd value for the median filter, bAnalysis.getDerivative() set medianFilter =', medianFilter)
			self.filteredVm = scipy.signal.medfilt(self.abf.sweepY, medianFilter)
		else:
			self.filteredVm = self.abf.sweepY

		self.filteredDeriv = np.diff(self.filteredVm)

		# scale it to V/S (mV/ms)
		self.filteredDeriv = self.filteredDeriv * self.abf.dataRate / 1000

		# add an initial point so it is the same length as raw data in abf.sweepY
		self.filteredDeriv = np.concatenate(([0],self.filteredDeriv))

	def spikeDetect0(self, dVthresholdPos=100, minSpikeVm=-20, medianFilter=0, startSeconds=None, stopSeconds=None):
		"""
		look for threshold crossings (dVthresholdPos) in first derivative (dV/dt) of membrane potential (Vm)
		tally each threshold crossing (e.g. a spike) in self.spikeTimes list

		Returns:
			self.thresholdTimes (pnts): the time of each threshold crossing
			self.spikeTimes (pnts): the time before each threshold crossing when dv/dt crosses 15% of its max
			self.filteredVm:
			self.filtereddVdt:
		"""

		print('bAnalysis.spikeDetect0()')
		print('	dVthresholdPos:', dVthresholdPos)
		print('	minSpikeVm:', minSpikeVm)
		print('	medianFilter:', medianFilter)
		print('	startSeconds:', startSeconds)
		print('	stopSeconds:', stopSeconds)

		#
		# header
		now = datetime.datetime.now()
		dateStr = now.strftime('%Y-%m-%d %H:%M:%S')
		self.dateAnalyzed = dateStr

		self.dVthreshold = dVthresholdPos
		self.minSpikeVm = minSpikeVm
		self.medianFilter = medianFilter
		self.startSeconds = startSeconds
		self.stopSeconds = stopSeconds

		#
		#
		startPnt = 0
		stopPnt = len(self.abf.sweepX) - 1
		secondsOffset = 0
		if startSeconds is not None and stopSeconds is not None:
			startPnt = self.dataPointsPerMs * (startSeconds*1000) # seconds to pnt
			stopPnt = self.dataPointsPerMs * (stopSeconds*1000) # seconds to pnt
		'''
		print('   startSeconds:', startSeconds, 'stopSeconds:', stopSeconds)
		print('   startPnt:', startPnt, 'stopPnt:', stopPnt)
		'''

		# removed 20190513
		'''
		if medianFilter > 0:
			self.filteredVm = scipy.signal.medfilt(self.abf.sweepY,medianFilter)
		else:
			self.filteredVm = self.abf.sweepY

		self.filteredDeriv = np.diff(self.filteredVm)

		# scale it to V/S (mV/ms)
		self.filteredDeriv = self.filteredDeriv * self.abf.dataRate / 1000

		# add an initial point so it is the same length as raw data in abf.sweepY
		self.filteredDeriv = np.concatenate(([0],self.filteredDeriv))
		'''

		#spikeTimes = _where_cross(sweepDeriv,dVthresholdPos)
		Is=np.where(self.filteredDeriv>dVthresholdPos)[0]
		Is=np.concatenate(([0],Is))
		Ds=Is[:-1]-Is[1:]+1
		spikeTimes0 = Is[np.where(Ds)[0]+1]

		#
		# reduce spike times based on start/stop
		# only include spike times between startPnt and stopPnt
		#print('before stripping len(spikeTimes0):', len(spikeTimes0))
		spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if (spikeTime>=startPnt and spikeTime<=stopPnt)]
		
		#print('after stripping len(spikeTimes0):', len(spikeTimes0))

		#
		# throw out all spikes that are below a threshold Vm (usually below -20 mV)
		#spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if self.abf.sweepY[spikeTime] > self.minSpikeVm]
		peakWindow_ms = 10
		peakWindow_pnts = self.abf.dataPointsPerMs * peakWindow_ms
		goodSpikeTimes = []
		for spikeTime in spikeTimes0:
			peakVal = np.max(self.abf.sweepY[spikeTime:spikeTime+peakWindow_pnts])
			if peakVal > self.minSpikeVm:
				goodSpikeTimes.append(spikeTime)
		spikeTimes0 = goodSpikeTimes
		
		#print('after stripping min isi', self.minSpikeVm, 'len(spikeTimes0):', len(spikeTimes0))

		#
		# throw out spike that are not upward deflections of Vm
		'''
		prePntUp = 7 # pnts
		goodSpikeTimes = []
		for spikeTime in spikeTimes0:
			preAvg = np.average(self.abf.sweepY[spikeTime-prePntUp:spikeTime-1])
			postAvg = np.average(self.abf.sweepY[spikeTime+1:spikeTime+prePntUp])
			#print(preAvg, postAvg)
			if preAvg < postAvg:
				goodSpikeTimes.append(spikeTime)
		spikeTimes0 = goodSpikeTimes
		'''

		#
		# if there are doubles, throw-out the second one
		refractory_ms = 20 #10 # remove spike [i] if it occurs within refractory_ms of spike [i-1]
		lastGood = 0 # first spike [0] will always be good, there is no spike [i-1]
		for i in range(len(spikeTimes0)):
			if i==0:
				# first spike is always good
				continue
			dPoints = spikeTimes0[i] - spikeTimes0[lastGood]
			if dPoints < self.abf.dataPointsPerMs*refractory_ms:
				# remove spike time [i]
				spikeTimes0[i] = 0
			else:
				# spike time [i] was good
				lastGood = i
		# regenerate spikeTimes0 by throwing out any spike time that does not pass 'if spikeTime'
		# spikeTimes[i] that were set to 0 above (they were too close to the previous spike)
		# will not pass 'if spikeTime', as 'if 0' evaluates to False
		spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if spikeTime]
		
		#print('after stripping doubles refractory_ms', refractory_ms, 'len(spikeTimes0):', len(spikeTimes0))

		#
		# todo: make sure all spikes are on upslope

		#
		# for each threshold crossing, search backwards in dV/dt for a % of maximum (about 10 ms)
		dvdt_percentOfMax = 0.1
		window_ms = 2
		window_pnts = window_ms * self.dataPointsPerMs
		spikeTimes1 = []
		for i, spikeTime in enumerate(spikeTimes0):
			# get max in derivative
			preDerivClip = self.filteredDeriv[spikeTime-window_pnts:spikeTime] # backwards
			#preDerivClip = np.flip(preDerivClip)
			peakPnt = np.argmax(preDerivClip)
			peakPnt += spikeTime-window_pnts
			peakVal = self.filteredDeriv[peakPnt]

			# look for % of max
			try:
				percentMaxVal = peakVal * dvdt_percentOfMax # value we are looking for in dv/dt
				preDerivClip = np.flip(preDerivClip) # backwards
				threshPnt2 = np.where(preDerivClip<percentMaxVal)[0][0]
				threshPnt2 = (spikeTime) - threshPnt2
				#print('i:', i, 'spikeTime:', spikeTime, 'peakPnt:', peakPnt, 'threshPnt2:', threshPnt2)
				spikeTimes1.append(threshPnt2)
			except (IndexError) as e:
				print('   error: bAnalysis.spikeDetect0() IndexError spike', i, spikeTime, 'percentMaxVal:', percentMaxVal)
				spikeTimes1.append(spikeTime)

		self.thresholdTimes = spikeTimes0 # points
		self.spikeTimes = spikeTimes1 # points

		#print('spikeDetect0() got', len(spikeTimes0), 'spikes')

		return self.spikeTimes, self.thresholdTimes, self.filteredVm, self.filteredDeriv

	def spikeDetect00(self, minSpikeVm=-20, medianFilter=0, startSeconds=None, stopSeconds=None):
		"""
		added 20190623 - to detect using Vm threshold - NOT dvdt

		look for threshold crossings (dVthresholdPos) in first derivative (dV/dt) of membrane potential (Vm)
		tally each threshold crossing (e.g. a spike) in self.spikeTimes list

		Returns:
			self.thresholdTimes (pnts): the time of each threshold crossing
			self.spikeTimes (pnts): the time before each threshold crossing when dv/dt crosses 15% of its max
			self.filteredVm:
			self.filtereddVdt:
		"""

		print('bAnalysis.spikeDetect00()')
		#print('	dVthresholdPos:', dVthresholdPos)
		print('	minSpikeVm:', minSpikeVm)
		print('	medianFilter:', medianFilter)
		print('	startSeconds:', startSeconds)
		print('	stopSeconds:', stopSeconds)

		#
		# header
		now = datetime.datetime.now()
		dateStr = now.strftime('%Y-%m-%d %H:%M:%S')
		self.dateAnalyzed = dateStr

		self.dVthreshold = None					# 20190623 - IMPORTANT
		self.minSpikeVm = minSpikeVm
		self.medianFilter = medianFilter
		self.startSeconds = startSeconds
		self.stopSeconds = stopSeconds

		#
		#
		startPnt = 0
		stopPnt = len(self.abf.sweepX) - 1
		secondsOffset = 0
		if startSeconds is not None and stopSeconds is not None:
			startPnt = self.dataPointsPerMs * (startSeconds*1000) # seconds to pnt
			stopPnt = self.dataPointsPerMs * (stopSeconds*1000) # seconds to pnt
		'''
		print('   startSeconds:', startSeconds, 'stopSeconds:', stopSeconds)
		print('   startPnt:', startPnt, 'stopPnt:', stopPnt)
		'''

		# removed 20190513
		'''
		if medianFilter > 0:
			self.filteredVm = scipy.signal.medfilt(self.abf.sweepY,medianFilter)
		else:
			self.filteredVm = self.abf.sweepY

		self.filteredDeriv = np.diff(self.filteredVm)

		# scale it to V/S (mV/ms)
		self.filteredDeriv = self.filteredDeriv * self.abf.dataRate / 1000

		# add an initial point so it is the same length as raw data in abf.sweepY
		self.filteredDeriv = np.concatenate(([0],self.filteredDeriv))
		'''

		#spikeTimes = _where_cross(sweepDeriv,dVthresholdPos)
		#Is=np.where(self.filteredDeriv>dVthresholdPos)[0]
		Is=np.where(self.filteredVm>minSpikeVm)[0]
		Is=np.concatenate(([0],Is))
		Ds=Is[:-1]-Is[1:]+1
		spikeTimes0 = Is[np.where(Ds)[0]+1]

		#
		# reduce spike times based on start/stop
		# only include spike times between startPnt and stopPnt
		spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if (spikeTime>=startPnt and spikeTime<=stopPnt)]

		#
		# throw out all spikes that are below a threshold Vm (usually below -20 mV)
		#spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if self.abf.sweepY[spikeTime] > self.minSpikeVm]
		# 20190623 - already done in this vm threshold funtion
		"""
		peakWindow_ms = 10
		peakWindow_pnts = self.abf.dataPointsPerMs * peakWindow_ms
		goodSpikeTimes = []
		for spikeTime in spikeTimes0:
			peakVal = np.max(self.abf.sweepY[spikeTime:spikeTime+peakWindow_pnts])
			if peakVal > self.minSpikeVm:
				goodSpikeTimes.append(spikeTime)
		spikeTimes0 = goodSpikeTimes
		"""

		#
		# 20190623
		# throw out spike that are NOT upward deflections of Vm

		#localVm = self.abf.sweepY

		# debug
		#print('before len(spikeTimes0):', len(spikeTimes0), 'type(self.abf.sweepY):', type(self.abf.sweepY))
		# if recording is REALLY slow, we need more points here !!!!

		# trying to fix this BULLSHIT
		tmpLastGoodSpike_pnts = None
		#minISI_pnts = 5000 # at 20 kHz this is 0.25 sec
		minISI_ms = 75 #250
		minISI_pnts = self.ms2Pnt_(minISI_ms)

		prePntUp = 10 # pnts
		goodSpikeTimes = []
		for tmpIdx, spikeTime in enumerate(spikeTimes0):
			tmpFuckPreClip = self.abf.sweepY[spikeTime-prePntUp:spikeTime] # not including the stop index
			tmpFuckPostClip = self.abf.sweepY[spikeTime+1:spikeTime+prePntUp+1] # not including the stop index
			preAvg = np.average(tmpFuckPreClip)
			postAvg = np.average(tmpFuckPostClip)
			#if preAvg < postAvg:
			if postAvg > preAvg:
				tmpSpikeTimeSec = self.pnt2Sec_(spikeTime)
				# debug
				'''
				print('GOOD tmpIdx:', tmpIdx, 'tmpSpikeTimeSec:', tmpSpikeTimeSec, 'preAvg:', preAvg, 'postAvg:', postAvg)
				print('   spikeTime:', spikeTime)
				print('   tmpFuckPreClip:', tmpFuckPreClip)
				print('   tmpFuckPostClip:', tmpFuckPostClip)
				'''

				if tmpLastGoodSpike_pnts is not None and (spikeTime-tmpLastGoodSpike_pnts) < minISI_pnts:
					continue
				goodSpikeTimes.append(spikeTime)
				tmpLastGoodSpike_pnts = spikeTime
			else:
				tmpSpikeTimeSec = self.pnt2Sec_(spikeTime)
				# debug
				'''
				print('BAD tmpIdx:', tmpIdx, 'tmpSpikeTimeSec:', tmpSpikeTimeSec, 'preAvg:', preAvg, 'postAvg:', postAvg)
				print('   spikeTime:', spikeTime)
				print('   tmpFuckPreClip:', tmpFuckPreClip)
				print('   tmpFuckPostClip:', tmpFuckPostClip)
				'''
			# debug
			'''
			if tmpIdx == 10:
				#sys.exit()
				#break
				pass
			'''

		spikeTimes0 = goodSpikeTimes
		# debug
		'''
		print('after len(spikeTimes0):', len(spikeTimes0), 'type(self.abf.sweepY):', type(self.abf.sweepY))
		'''

		###########
		###########
		## PUT HITS BACK IN 20160623
		###########
		###########
		"""
		#
		# if there are doubles, throw-out the second one
		refractory_ms = 20 #10 # remove spike [i] if it occurs within refractory_ms of spike [i-1]
		lastGood = 0 # first spike [0] will always be good, there is no spike [i-1]
		for i in range(len(spikeTimes0)):
			if i==0:
				# first spike is always good
				continue
			dPoints = spikeTimes0[i] - spikeTimes0[lastGood]
			if dPoints < self.abf.dataPointsPerMs*refractory_ms:
				# remove spike time [i]
				spikeTimes0[i] = 0
			else:
				# spike time [i] was good
				lastGood = i
		# regenerate spikeTimes0 by throwing out any spike time that does not pass 'if spikeTime'
		# spikeTimes[i] that were set to 0 above (they were too close to the previous spike)
		# will not pass 'if spikeTime', as 'if 0' evaluates to False
		spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if spikeTime]
		"""

		#
		# todo: make sure all spikes are on upslope

		#
		# for each threshold crossing, search backwards in dV/dt for a % of maximum (about 10 ms)
		"""
		dvdt_percentOfMax = 0.1
		window_ms = 2
		window_pnts = window_ms * self.dataPointsPerMs
		spikeTimes1 = []
		for i, spikeTime in enumerate(spikeTimes0):
			# get max in derivative
			preDerivClip = self.filteredDeriv[spikeTime-window_pnts:spikeTime] # backwards
			#preDerivClip = np.flip(preDerivClip)
			peakPnt = np.argmax(preDerivClip)
			peakPnt += spikeTime-window_pnts
			peakVal = self.filteredDeriv[peakPnt]

			# look for % of max
			try:
				percentMaxVal = peakVal * dvdt_percentOfMax # value we are looking for in dv/dt
				preDerivClip = np.flip(preDerivClip) # backwards
				threshPnt2 = np.where(preDerivClip<percentMaxVal)[0][0]
				threshPnt2 = (spikeTime) - threshPnt2
				#print('i:', i, 'spikeTime:', spikeTime, 'peakPnt:', peakPnt, 'threshPnt2:', threshPnt2)
				spikeTimes1.append(threshPnt2)
			except (IndexError) as e:
				print('   error: bAnalysis.spikeDetect0() IndexError spike', i, spikeTime, 'percentMaxVal:', percentMaxVal)
				spikeTimes1.append(spikeTime)

		self.thresholdTimes = spikeTimes0 # points
		self.spikeTimes = spikeTimes1 # points
		"""

		#20190623
		self.spikeTimes = spikeTimes0

		# 201906233 - in this version we have one spike time, the crossing of Vm
		# we still have filteredVm but it is ONLY for display purposes
		#return self.spikeTimes, self.thresholdTimes, self.filteredVm, self.filteredDeriv
		return self.spikeTimes, self.filteredVm, self.filteredDeriv

	def spikeDetect(self, dVthresholdPos=100, minSpikeVm=-20, medianFilter=0, halfHeights=[20, 50, 80], startSeconds=None, stopSeconds=None):
		'''
		spike detect the current sweep and put results into spikeTime[currentSweep]

		dVthresholdPos: if None then detect only using minSpikeVm
		
		todo: remember values of halfHeights
		'''

		startTime = time.time()

		self.spikeDict = [] # we are filling this in, one entry for each spike

		self.numErrors = 0

		# spike detect
		if dVthresholdPos is None:
			# new 20190623
			self.thresholdTimes = None
			self.spikeTimes, vm, dvdt = self.spikeDetect00(minSpikeVm=minSpikeVm, medianFilter=medianFilter, startSeconds=startSeconds, stopSeconds=stopSeconds)
		else:
			self.spikeTimes, self.thresholdTimes, vm, dvdt = self.spikeDetect0(dVthresholdPos=dVthresholdPos, minSpikeVm=minSpikeVm, medianFilter=medianFilter, startSeconds=startSeconds, stopSeconds=stopSeconds)

		#
		# look in a window after each threshold crossing to get AP peak
		# get minima before/after spike
		peakWindow_ms = 10
		peakWindow_pnts = self.abf.dataPointsPerMs * peakWindow_ms
		#
		avgWindow_ms = 5 # we find the min/max before/after (between spikes) and then take an average around this value
		avgWindow_pnts = avgWindow_ms * self.abf.dataPointsPerMs
		avgWindow_pnts = math.floor(avgWindow_pnts/2)
		for i, spikeTime in enumerate(self.spikeTimes):
			# spikeTime units is ALWAYS points

			peakPnt = np.argmax(vm[spikeTime:spikeTime+peakWindow_pnts])
			peakPnt += spikeTime
			peakVal = np.max(vm[spikeTime:spikeTime+peakWindow_pnts])

			spikeDict = collections.OrderedDict() # use OrderedDict so Pandas output is in the correct order
			spikeDict['file'] = self.file
			spikeDict['spikeNumber'] = i

			spikeDict['numError'] = 0
			spikeDict['errors'] = []

			spikeDict['startSeconds'] = startSeconds
			spikeDict['stopSeconds'] = stopSeconds

			# detection params
			spikeDict['dVthreshold'] = dVthresholdPos
			spikeDict['minSpikeVm'] = minSpikeVm
			spikeDict['medianFilter'] = medianFilter
			spikeDict['halfHeights'] = halfHeights

			spikeDict['thresholdPnt'] = spikeTime
			spikeDict['thresholdVal'] = vm[spikeTime] # in vm
			spikeDict['thresholdVal_dvdt'] = dvdt[spikeTime] # in dvdt
			spikeDict['thresholdSec'] = (spikeTime / self.abf.dataPointsPerMs) / 1000

			spikeDict['peakPnt'] = peakPnt
			spikeDict['peakVal'] = peakVal
			spikeDict['peakSec'] = (peakPnt / self.abf.dataPointsPerMs) / 1000

			spikeDict['peakHeight'] = spikeDict['peakVal'] - spikeDict['thresholdVal']

			self.spikeDict.append(spikeDict)

			defaultVal = float('nan')

			# get pre/post spike minima
			self.spikeDict[i]['preMinPnt'] = None
			self.spikeDict[i]['preMinVal'] = defaultVal
			self.spikeDict[i]['postMinPnt'] = None
			self.spikeDict[i]['postMinVal'] = defaultVal

			# early diastolic duration
			# 0.1 to 0.5 of time between pre spike min and spike time
			self.spikeDict[i]['preLinearFitPnt0'] = None
			self.spikeDict[i]['preLinearFitPnt1'] = None
			self.spikeDict[i]['earlyDiastolicDuration_ms'] = defaultVal # seconds between preLinearFitPnt0 and preLinearFitPnt1
			self.spikeDict[i]['preLinearFitVal0'] = defaultVal
			self.spikeDict[i]['preLinearFitVal1'] = defaultVal
			# m,b = np.polyfit(x, y, 1)
			self.spikeDict[i]['earlyDiastolicDurationRate'] = defaultVal # fit of y=preLinearFitVal 0/1 versus x=preLinearFitPnt 0/1
			self.spikeDict[i]['lateDiastolicDuration'] = defaultVal #

			self.spikeDict[i]['preSpike_dvdt_max_pnt'] = None
			self.spikeDict[i]['preSpike_dvdt_max_val'] = defaultVal # in units mV
			self.spikeDict[i]['preSpike_dvdt_max_val2'] = defaultVal # in units dv/dt
			self.spikeDict[i]['postSpike_dvdt_min_pnt'] = None
			self.spikeDict[i]['postSpike_dvdt_min_val'] = defaultVal # in units mV
			self.spikeDict[i]['postSpike_dvdt_min_val2'] = defaultVal # in units dv/dt

			self.spikeDict[i]['isi_pnts'] = defaultVal # time between successive AP thresholds (thresholdSec)
			self.spikeDict[i]['isi_ms'] = defaultVal # time between successive AP thresholds (thresholdSec)
			self.spikeDict[i]['spikeFreq_hz'] = defaultVal # time between successive AP thresholds (thresholdSec)
			self.spikeDict[i]['cycleLength_pnts'] = defaultVal # time between successive MDPs
			self.spikeDict[i]['cycleLength_ms'] = defaultVal # time between successive MDPs

			# Action potential duration (APD) was defined as the interval between the TOP and the subsequent MDP
			self.spikeDict[i]['apDuration_ms'] = defaultVal
			self.spikeDict[i]['diastolicDuration_ms'] = defaultVal

			# any number of spike widths
			self.spikeDict[i]['widths'] = []
			for halfHeight in halfHeights:
				widthDict = {
					'halfHeight': halfHeight,
					'risingPnt': None,
					'risingVal': defaultVal,
					'fallingPnt': None,
					'fallingVal': defaultVal,
					'widthPnts': None,
					'widthMs': defaultVal
				}
				self.spikeDict[i]['widths'].append(widthDict)

			# The nonlinear late diastolic depolarization phase was estimated as the duration between 1% and 10% dV/dt
			# todo: not done !!!!!!!!!!

			if i==0 or i==len(self.spikeTimes)-1:
				continue
			else:
				#
				# pre spike min
				preRange = vm[self.spikeTimes[i-1]:self.spikeTimes[i]]
				preMinPnt = np.argmin(preRange)
				preMinPnt += self.spikeTimes[i-1]
				# the pre min is actually an average around the real minima
				avgRange = vm[preMinPnt-avgWindow_pnts:preMinPnt+avgWindow_pnts]
				preMinVal = np.average(avgRange)

				# search backward from spike to find when vm reaches preMinVal (avg)
				preRange = vm[preMinPnt:self.spikeTimes[i]]
				preRange = np.flip(preRange) # we want to search backwards from peak
				try:
					preMinPnt2 = np.where(preRange<preMinVal)[0][0]
					preMinPnt = self.spikeTimes[i] - preMinPnt2
				except (IndexError) as e:
					self.spikeDict[i]['numError'] = self.spikeDict[i]['numError'] + 1
					# sometimes preRange is empty, don't try and put min/max in error
					errorStr = 'spike ' + str(i) + ' searching for preMinVal:' + str(preMinVal) #+ ' postRange min:' + str(np.min(postRange)) + ' max ' + str(np.max(postRange))
					self.spikeDict[i]['errors'].append(errorStr)
					self.numErrors += 1

				#
				# linear fit on 10% - 50% of the time from preMinPnt to self.spikeTimes[i]
				startLinearFit = 0.1 # percent of time between pre spike min and AP peak
				stopLinearFit = 0.5 # percent of time between pre spike min and AP peak
				# taking floor() so we always get an integer # points
				timeInterval_pnts = math.floor(self.spikeTimes[i] - preMinPnt)
				preLinearFitPnt0 = preMinPnt + math.floor(timeInterval_pnts * startLinearFit)
				preLinearFitPnt1 = preMinPnt + math.floor(timeInterval_pnts * stopLinearFit)
				preLinearFitVal0 = vm[preLinearFitPnt0]
				preLinearFitVal1 = vm[preLinearFitPnt1]
				# a linear fit where 'm,b = np.polyfit(x, y, 1)'
				# m*x+b"
				xFit = self.abf.sweepX[preLinearFitPnt0:preLinearFitPnt1]
				yFit = vm[preLinearFitPnt0:preLinearFitPnt1]
				try:
					mLinear, bLinear = np.polyfit(xFit, yFit, 1) # m is slope, b is intercept
					self.spikeDict[i]['earlyDiastolicDurationRate'] = mLinear
				except TypeError:
					#catching exception: raise TypeError("expected non-empty vector for x")
					self.spikeDict[i]['earlyDiastolicDurationRate'] = defaultVal
					self.spikeDict[i]['numError'] = self.spikeDict[i]['numError'] + 1
					errorStr = 'error in earlyDiastolicDurationRate fit'
					self.spikeDict[i]['errors'].append(errorStr)

				# not implemented
				#self.spikeDict[i]['lateDiastolicDuration'] = ???

				#
				# maxima in dv/dt before spike
				# added try/except sunday april 14, seems to break spike detection???
				try:
					preRange = dvdt[self.spikeTimes[i]:peakPnt]
					preSpike_dvdt_max_pnt = np.argmax(preRange)
					preSpike_dvdt_max_pnt += self.spikeTimes[i]
					self.spikeDict[i]['preSpike_dvdt_max_pnt'] = preSpike_dvdt_max_pnt
					self.spikeDict[i]['preSpike_dvdt_max_val'] = vm[preSpike_dvdt_max_pnt] # in units mV
					self.spikeDict[i]['preSpike_dvdt_max_val2'] = dvdt[preSpike_dvdt_max_pnt] # in units mV
				except (ValueError) as e:
					self.spikeDict[i]['numError'] = self.spikeDict[i]['numError'] + 1
					# sometimes preRange is empty, don't try and put min/max in error
					#print('preRange:', preRange)
					errorStr = 'spike ' + str(i) + ' searching for preSpike_dvdt_max_pnt:'
					self.spikeDict[i]['errors'].append(errorStr)
					self.numErrors += 1

				#
				# post spike min
				postRange = vm[self.spikeTimes[i]:self.spikeTimes[i+1]]
				postMinPnt = np.argmin(postRange)
				postMinPnt += self.spikeTimes[i]
				# the post min is actually an average around the real minima
				avgRange = vm[postMinPnt-avgWindow_pnts:postMinPnt+avgWindow_pnts]
				postMinVal = np.average(avgRange)

				# search forward from spike to find when vm reaches postMinVal (avg)
				postRange = vm[self.spikeTimes[i]:postMinPnt]
				try:
					postMinPnt2 = np.where(postRange<postMinVal)[0][0]
					postMinPnt = self.spikeTimes[i] + postMinPnt2
					#print('i:', i, 'postMinPnt:', postMinPnt)
				except (IndexError) as e:
					self.spikeDict[i]['numError'] = self.spikeDict[i]['numError'] + 1
					# sometimes postRange is empty, don't try and put min/max in error
					#print('postRange:', postRange)
					errorStr = 'spike ' + str(i) + ' searching for postMinVal:' + str(postMinVal) #+ ' postRange min:' + str(np.min(postRange)) + ' max ' + str(np.max(postRange))
					self.spikeDict[i]['errors'].append(errorStr)
					self.numErrors += 1

				#
				# minima in dv/dt after spike
				#postRange = dvdt[self.spikeTimes[i]:postMinPnt]
				postSpike_ms = 10
				postSpike_pnts = self.abf.dataPointsPerMs * postSpike_ms
				#postRange = dvdt[self.spikeTimes[i]:self.spikeTimes[i]+postSpike_pnts] # fixed window after spike
				postRange = dvdt[peakPnt:peakPnt+postSpike_pnts] # fixed window after spike

				postSpike_dvdt_min_pnt = np.argmin(postRange)
				postSpike_dvdt_min_pnt += peakPnt
				#print('i:', i, 'postSpike_dvdt_min_pnt:', postSpike_dvdt_min_pnt)
				self.spikeDict[i]['postSpike_dvdt_min_pnt'] = postSpike_dvdt_min_pnt
				self.spikeDict[i]['postSpike_dvdt_min_val'] = vm[postSpike_dvdt_min_pnt]
				self.spikeDict[i]['postSpike_dvdt_min_val2'] = dvdt[postSpike_dvdt_min_pnt]

				self.spikeDict[i]['preMinPnt'] = preMinPnt
				self.spikeDict[i]['preMinVal'] = preMinVal
				self.spikeDict[i]['postMinPnt'] = postMinPnt
				self.spikeDict[i]['postMinVal'] = postMinVal
				# linear fit before spike
				self.spikeDict[i]['preLinearFitPnt0'] = preLinearFitPnt0
				self.spikeDict[i]['preLinearFitPnt1'] = preLinearFitPnt1
				self.spikeDict[i]['earlyDiastolicDuration_ms'] = self.pnt2Ms_(preLinearFitPnt1 - preLinearFitPnt0)
				self.spikeDict[i]['preLinearFitVal0'] = preLinearFitVal0
				self.spikeDict[i]['preLinearFitVal1'] = preLinearFitVal1

				#
				# Action potential duration (APD) was defined as the interval between the TOP and the subsequent MDP
				self.spikeDict[i]['apDuration_ms'] = self.pnt2Ms_(postMinPnt - spikeDict['thresholdPnt'])

				#
				# diastolic duration was defined as the interval between MDP and TOP
				self.spikeDict[i]['diastolicDuration_ms'] = self.pnt2Ms_(spikeTime - preMinPnt)

				self.spikeDict[i]['cycleLength_ms'] = float('nan')
				if i>1: #20190627, was i>1
					isiPnts = self.spikeDict[i]['thresholdPnt'] - self.spikeDict[i-1]['thresholdPnt']
					self.spikeDict[i]['isi_pnts'] = isiPnts
					self.spikeDict[i]['isi_ms'] = self.pnt2Ms_(isiPnts)
					# new 20190627
					self.spikeDict[i]['spikeFreq_hz'] = 1 / (self.pnt2Ms_(isiPnts) / 1000)

					cycleLength_pnts = self.spikeDict[i]['postMinPnt'] - self.spikeDict[i-1]['postMinPnt']
					self.spikeDict[i]['cycleLength_pnts'] = cycleLength_pnts
					self.spikeDict[i]['cycleLength_ms'] = self.pnt2Ms_(cycleLength_pnts)

				#
				# get 1/2 height (actually, any number of height measurements)
				# action potential duration using peak and post min
				#self.spikeDict[i]['widths'] = []
				for j, halfHeight in enumerate(halfHeights):
					thisVm = postMinVal + (peakVal - postMinVal) * (halfHeight * 0.01)
					#todo: logic is broken, this get over-written in following try
					widthDict = {
						'halfHeight': halfHeight,
						'risingPnt': None,
						'risingVal': defaultVal,
						'fallingPnt': None,
						'fallingVal': defaultVal,
						'widthPnts': None,
						'widthMs': defaultVal
					}
					try:
						postRange = vm[peakPnt:postMinPnt]
						fallingPnt = np.where(postRange<thisVm)[0][0] # less than
						fallingPnt += peakPnt
						fallingVal = vm[fallingPnt]

						# use the post/falling to find pre/rising
						preRange = vm[preMinPnt:peakPnt]
						risingPnt = np.where(preRange>fallingVal)[0][0] # greater than
						risingPnt += preMinPnt
						risingVal = vm[risingPnt]

						# width (pnts)
						widthPnts = fallingPnt - risingPnt
						# assign
						widthDict['halfHeight'] = halfHeight
						widthDict['risingPnt'] = risingPnt
						widthDict['risingVal'] = risingVal
						widthDict['fallingPnt'] = fallingPnt
						widthDict['fallingVal'] = fallingVal
						widthDict['widthPnts'] = widthPnts
						widthDict['widthMs'] = widthPnts / self.abf.dataPointsPerMs

					except (IndexError) as e:
						print('error: bAnalysis.spikeDetect() spike', i, 'half height', halfHeight)
						self.spikeDict[i]['numError'] = self.spikeDict[i]['numError'] + 1
						errorStr = 'spike ' + str(i) + ' half width ' + str(j)
						self.spikeDict[i]['errors'].append(errorStr)
						self.numErrors += 1
					#self.spikeDict[i]['widths'].append(widthDict)
					self.spikeDict[i]['widths'][j] = widthDict

		#
		# look between threshold crossing to get minima
		# we will ignore the first and last spike

		#
		# build a list of spike clips
		clipWidth_ms = 500
		clipWidth_pnts = clipWidth_ms * self.abf.dataPointsPerMs
		halfClipWidth_pnts = int(clipWidth_pnts/2)

		# make one x axis clip with the threshold crossing at 0
		self.spikeClips_x = [(x-halfClipWidth_pnts)/self.abf.dataPointsPerMs for x in range(clipWidth_pnts)]

		#20190714, added this to make all clips same length, much easier to plot in MultiLine
		numPointsInClip = len(self.spikeClips_x)
		
		self.spikeClips = []
		self.spikeClips_x2 = []
		for idx, spikeTime in enumerate(self.spikeTimes):
			currentClip = vm[spikeTime-halfClipWidth_pnts:spikeTime+halfClipWidth_pnts]
			if len(currentClip) == numPointsInClip:
				self.spikeClips.append(currentClip)
				self.spikeClips_x2.append(self.spikeClips_x) # a 2D version to make pyqtgraph multiline happy
			else:
				print('bAnalysis.spikeDetect() did not add clip for spike index', idx, 'at time', spikeTime)
				
		stopTime = time.time()
		print('bAnalysis.spikeDetect() for file', self.file, 'detected', len(self.spikeTimes), 'spikes in', round(stopTime-startTime,2), 'seconds')

	############################################################

	############################################################
	# output reports
	############################################################
	def report(self, theMin, theMax):
		""" return entire spikeDict as a pandas data frame """
		df = pd.DataFrame(self.spikeDict)
		df = df[df['thresholdSec'].between(theMin, theMax, inclusive=True)]
		return df

	def report2(self, theMin, theMax):
		"""
		generate a report of spikes with spike times between theMin (sec) and theMax (sec)
		"""
		newList = []
		for spike in self.spikeDict:

			# if current spike time is out of bounds then continue (e.g. it is not between theMin (sec) and theMax (sec)
			spikeTime_sec = self.pnt2Sec_(spike['thresholdPnt'])
			if spikeTime_sec<theMin or spikeTime_sec>theMax:
				continue

			spikeDict = collections.OrderedDict() # use OrderedDict so Pandas output is in the correct order
			spikeDict['Take Off Potential (s)'] = self.pnt2Sec_(spike['thresholdPnt'])
			spikeDict['Take Off Potential (ms)'] = self.pnt2Ms_(spike['thresholdPnt'])
			spikeDict['Take Off Potential (mV)'] = spike['thresholdVal']
			spikeDict['AP Peak (ms)'] = self.pnt2Ms_(spike['peakPnt'])
			spikeDict['AP Peak (mV)'] = spike['peakVal']
			spikeDict['AP Height (mV)'] = spike['peakHeight']
			spikeDict['Pre AP Min (mV)'] = spike['preMinVal']
			spikeDict['Post AP Min (mV)'] = spike['postMinVal']
			#
			spikeDict['AP Duration (ms)'] = spike['apDuration_ms']
			spikeDict['Early Diastolic Duration (ms)'] = spike['earlyDiastolicDuration_ms']
			spikeDict['Diastolic Duration (ms)'] = spike['diastolicDuration_ms']
			#
			spikeDict['Inter-Spike-Interval (ms)'] = spike['isi_ms']
			spikeDict['Spike Frequency (Hz)'] = spike['spikeFreq_hz']

			spikeDict['Cycle Length (ms)'] = spike['cycleLength_ms']

			spikeDict['Max AP Upstroke (dV/dt)'] = spike['preSpike_dvdt_max_val2']
			spikeDict['Max AP Upstroke (mV)'] = spike['preSpike_dvdt_max_val']

			spikeDict['Max AP Repolarization (dV/dt)'] = spike['postSpike_dvdt_min_val2']
			spikeDict['Max AP Repolarization (mV)'] = spike['postSpike_dvdt_min_val']

			# half-width
			for widthDict in spike['widths']:
				keyName = 'width_' + str(widthDict['halfHeight'])
				spikeDict[keyName] = widthDict['widthMs']

			# errors
			spikeDict['numError'] = spike['numError']
			spikeDict['errors'] = spike['errors']


			# append
			newList.append(spikeDict)

		df = pd.DataFrame(newList)
		return df

	#############################
	# utility functions
	#############################
	def pnt2Sec_(self, pnt):
		'''
		if pnt is None or math.isnan(pnt):
			return None
		'''
		if pnt is None:
			return math.isnan(pnt)
		else:
			return pnt / self.abf.dataPointsPerMs / 1000

	def pnt2Ms_(self, pnt):
		return pnt / self.abf.dataPointsPerMs

	def ms2Pnt_(self, ms):
		return ms * self.abf.dataPointsPerMs

	def __str__(self):
		retStr = 'file: ' + self.file + '\n' + str(self.abf)
		return retStr

if __name__ == '__main__':
	print('running bAnalysis __main__')
	ba = bAnalysis('../data/19114001.abf')
	print(ba.dataPointsPerMs)
