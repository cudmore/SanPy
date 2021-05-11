'''
Author: Robert H Cudmore
Date: 20190225

The bAnalysis class wraps a pyabf file and adds spike detection and plotting.

Instantiate a bAnalysis object with
	1) .abf file name
	2) .csv with time/mV columns
	3) a dictionary (20210130, add this)

The underlying pyabf object is always available as self.abf

Usage:
	ba = bAnalysis('data/19114001.abf')
	print(ba) # prints info about underlying abf file
	ba.plotDeriv()
	ba.spikeDetect(dvdtThreshold=100)
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

import os, sys, math, time, collections, datetime
from collections import OrderedDict

import numpy as np
import pandas as pd

import scipy.signal

import pyabf # see: https://github.com/swharden/pyABF

import sanpy

def getDefaultDetection():
	"""
	todo: put this in a json file ???
	"""
	theDict = {}

	theDict['dvdtThreshold'] = {}
	theDict['dvdtThreshold']['value'] = 100
	theDict['dvdtThreshold']['units'] = 'dVdt'
	theDict['dvdtThreshold']['fullName'] = 'dV/dt Threshold'
	theDict['dvdtThreshold']['description'] = 'dV/dt Threshold for a spike, will be backed up to dvdt_percentOfMax and have xxx error when this fails'

	# todo: fill in all others
	'''
		'dvdtThreshold': 100, #if None then detect only using mvThreshold
		'mvThreshold': -20,
		'medianFilter': 0,
		'SavitzkyGolay_pnts': 5, # shoould correspond to about 0.5 ms
		'SavitzkyGolay_poly': 2,
		'halfHeights': [10, 20, 50, 80, 90],
		# new 20210501
		'mdp_ms': 250, # window before/after peak to look for MDP
		'refractory_ms': 170, # rreject spikes with instantaneous frequency
		'peakWindow_ms': 100, #10, # time after spike to look for AP peak
		'dvdtPreWindow_ms': 10, #5, # used in dvdt, pre-roll to then search for real threshold crossing
		'avgWindow_ms': 5,
		# 20210425, trying 0.15
		#'dvdt_percentOfMax': 0.1, # only used in dvdt detection, used to back up spike threshold to more meaningful value
		'dvdt_percentOfMax': 0.1, # only used in dvdt detection, used to back up spike threshold to more meaningful value
		# 20210413, was 50 for manuscript, we were missing lots of 1/2 widths
		'halfWidthWindow_ms': 200, #200, #20,
		# add 20210413 to turn of doBackupSpikeVm on pure vm detection
		'doBackupSpikeVm': True,
		'spikeClipWidth_ms': 500,
		'onlyPeaksAbove_mV': None,
		'startSeconds': None,
		'stopSeconds': None,

		# for detection of Ca from line scans
		#'caThresholdPos': 0.01,
		#'caMinSpike': 0.5,

		# book keeping like ('cellType', 'sex', 'condition')
		'cellType': '',
		'sex': '',
		'condition': '',
	}
	'''
	return theDict.copy()

class bAnalysis:
	def __init__(self, file=None, theTiff=None, byteStream=None):
		"""
		file: either abf or csv with time/mV columns
		theDict:
		"""

		self.loadError = False # abb 20201109

		self.detectionDict = None # remember the parameters of our last detection

		self.file = file # todo: change this to filePath
		self._abf = None

		#20190628
		self.detectionConfig = sanpy.bAnalysisUtil()

		# detection parameters specified by user
		self.dateAnalyzed = None
		self.dvdtThreshold = None
		self.mvThreshold = None # abb, 20190513
		self.medianFilter = None
		#self.startSeconds = None
		#self.stopSeconds = None

		self.detectionType = None

		self.spikeDict = [] # a list of dict

		self.spikeTimes = [] # created in self.spikeDetect()
		self.spikeClips = [] # created in self.spikeDetect()

		if file is not None and not os.path.isfile(file):
			print(f'error: bAnalysis.__init__ file does not exist: {file}')
			self.loadError = True
			return

		self.acqDate = None
		self.acqTime = None

		# instantiate and load abf file
		self.myFileType = None
		if byteStream is not None:
			print('  bAnalysis() loading bytestream with pyabf.ABF()')
			self._abf = pyabf.ABF(byteStream)
			print('  done')

		elif file.endswith('.tif'):
			self._abf = sanpy.bAbfText(file)
			print('  === REMEMBER: bAnalysis.__init__() is normalizing Ca sweepY')
			self._abf.sweepY = self.NormalizeData(self._abf.sweepY)
			self.myFileType = 'tif'
		elif file.endswith('.csv'):
			self._abf = sanpy.bAbfText(file)
			self.myFileType = 'csv'
		elif file.endswith('.abf'):
			try:
				self._abf = pyabf.ABF(file)
				#20190621
				abfDateTime = self._abf.abfDateTime #2019-01-14 15:20:48.196000
				self.acqDate = abfDateTime.strftime("%Y-%m-%d")
				self.acqTime = abfDateTime.strftime("%H:%M:%S")
			except (NotImplementedError) as e:
				print('error: bAnalysis.__init__() did not load abf file:', file)
				print('  exception was:', e)
				self.loadError = True
				self._abf = None
				return
			except (Exception) as e:
				# some abf files throw: 'unpack requires a buffer of 234 bytes'
				print('error: bAnalysis.__init__() did not load abf file:', file)
				print('  unknown exception was:', e)
				self.loadError = True
				self._abf = None
				return
			# we have a good abf file
			self.myFileType = 'abf'

		else:
			print(f'error: bAnalysis.__init__() can only open abf/csv/tif files: {file}')
			self.loadError = True
			return

		self.currentSweep = None
		self.setSweep(0)

		self.filteredVm = []
		#self.deriv = []
		self.filteredDeriv = []
		self.spikeTimes = []

		self.thresholdTimes = None # not used

		#self.condition1 = None # in ('ctrl', '1nm', '10nm', '30nm', etc)
		#self.condition2 = None # cell number
		#self.condition3 = None # sex in ('M', 'F')
		#self.condition4 = None # superior/inferior in ('superior', 'inferior')

		# keep track of the number of errors during spike detection
		self.numErrors = 0

		# get default derivative
		self.getDerivative()

	def loadFromDict(theDict):
		pass
		#return abfText

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
		"""Returns the number of spikes, assumes self.spikeDetect(dvdtThreshold)"""
		return len(self.spikeTimes)

	@property
	def numSpikeErrors(self):
		return self.numErrors

	def getStatMean(self, xStat):
		theMean = None
		x = self.getStat(xStat)
		if len(x)>1:
			theMean = np.nanmean(x)
		return theMean

	def getStat(self, xStat, yStat=None, xToSec=False):
		"""
		xToSec: Automatically convert x from points to seconds
		"""
		def clean(val):
			if val is None:
				val = float('nan')
			return val
		# peakVal, peakSec
		#x = [spike[xStat] for spike in self.spikeDict]
		#y = [spike[yStat] for spike in self.spikeDict]
		x = [clean(spike[xStat]) for spike in self.spikeDict]
		if yStat is not None:
			y = [clean(spike[yStat]) for spike in self.spikeDict]

		if xToSec:
			x = [self.pnt2Sec_(xi) for xi in x] # convert pnt to sec

		if yStat is not None:
			return x, y
		else:
			return x

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
	def getDerivative(self, dDict=None):
		"""
		medianFilter: pnts, must be int and odd
		"""
		if dDict is None:
			dDict = self.getDefaultDetection()

		medianFilter = dDict['medianFilter']
		SavitzkyGolay_pnts = dDict['SavitzkyGolay_pnts']
		SavitzkyGolay_poly = dDict['SavitzkyGolay_poly']

		#print('getDerivative() medianFilter:', medianFilter)
		if medianFilter > 0:
			if not medianFilter % 2:
				medianFilter += 1
				print('*** Warning: bAnalysis.getDerivative() Please use an odd value for the median filter, bAnalysis.getDerivative() set medianFilter =', medianFilter)
			medianFilter = int(medianFilter)
			self.filteredVm = scipy.signal.medfilt(self.abf.sweepY, medianFilter)
		elif SavitzkyGolay_pnts > 0:
			print('  bAnalysis.getDerivative() vm SavitzkyGolay_pnts:', SavitzkyGolay_pnts, 'SavitzkyGolay_poly:', SavitzkyGolay_poly)
			self.filteredVm = scipy.signal.savgol_filter(self.abf.sweepY, SavitzkyGolay_pnts, SavitzkyGolay_poly, mode='nearest')
		else:
			self.filteredVm = self.abf.sweepY

		self.filteredDeriv = np.diff(self.filteredVm)

		if medianFilter > 0:
			if not medianFilter % 2:
				medianFilter += 1
				print('*** Warning: bAnalysis.getDerivative() Please use an odd value for the median filter, bAnalysis.getDerivative() set medianFilter =', medianFilter)
			medianFilter = int(medianFilter)
			self.filteredDeriv = scipy.signal.medfilt(self.filteredDeriv, medianFilter)
		elif SavitzkyGolay_pnts > 0:
			print('  bAnalysis.getDerivative() dvdt SavitzkyGolay_pnts:', SavitzkyGolay_pnts, 'SavitzkyGolay_poly:', SavitzkyGolay_poly)
			self.filteredDeriv = scipy.signal.savgol_filter(self.filteredDeriv, SavitzkyGolay_pnts, SavitzkyGolay_poly, mode='nearest')
		else:
			self.filteredDeriv = self.filteredDeriv

		# mV/ms
		dataPointsPerMs = self.abf.dataPointsPerMs
		self.filteredDeriv = self.filteredDeriv * dataPointsPerMs #/ 1000

		# add an initial point so it is the same length as raw data in abf.sweepY
		#self.deriv = np.concatenate(([0],self.deriv))
		self.filteredDeriv = np.concatenate(([0],self.filteredDeriv))

	def getDefaultDetection(self):
		theDict = {
			'dvdtThreshold': 100, #if None then detect only using mvThreshold
			'mvThreshold': -20,
			'medianFilter': 0,
			'SavitzkyGolay_pnts': 5, # shoould correspond to about 0.5 ms
			'SavitzkyGolay_poly': 2,
			'halfHeights': [10, 20, 50, 80, 90],
			# new 20210501
			'mdp_ms': 250, # window before/after peak to look for MDP
			'refractory_ms': 170, # rreject spikes with instantaneous frequency
			'peakWindow_ms': 100, #10, # time after spike to look for AP peak
			'dvdtPreWindow_ms': 10, #5, # used in dvdt, pre-roll to then search for real threshold crossing
			'avgWindow_ms': 5,
			# 20210425, trying 0.15
			#'dvdt_percentOfMax': 0.1, # only used in dvdt detection, used to back up spike threshold to more meaningful value
			'dvdt_percentOfMax': 0.1, # only used in dvdt detection, used to back up spike threshold to more meaningful value
			# 20210413, was 50 for manuscript, we were missing lots of 1/2 widths
			'halfWidthWindow_ms': 200, #200, #20,
			# add 20210413 to turn of doBackupSpikeVm on pure vm detection
			'doBackupSpikeVm': True,
			'spikeClipWidth_ms': 500,
			'onlyPeaksAbove_mV': None,
			'startSeconds': None,
			'stopSeconds': None,

			# for detection of Ca from line scans
			#'caThresholdPos': 0.01,
			#'caMinSpike': 0.5,

			# book keeping like ('cellType', 'sex', 'condition')
			'cellType': '',
			'sex': '',
			'condition': '',
		}
		return theDict.copy()

	def getDefaultDetection_ca(self):
		theDict = self.getDefaultDetection()
		theDict['dvdtThreshold'] = 0.01 #if None then detect only using mvThreshold
		theDict['mvThreshold'] = 0.5
		#
		#theDict['medianFilter': 0
		#'halfHeights': [20,50,80]
		theDict['refractory_ms'] = 200 #170 # reject spikes with instantaneous frequency
		#theDict['peakWindow_ms': 100 #10, # time after spike to look for AP peak
		#theDict['dvdtPreWindow_ms': 2 # used in dvdt, pre-roll to then search for real threshold crossing
		#theDict['avgWindow_ms': 5
		#theDict['dvdt_percentOfMax': 0.1
		theDict['halfWidthWindow_ms'] = 200 #was 20
		#theDict['spikeClipWidth_ms': 500
		#theDict['onlyPeaksAbove_mV': None
		#theDict['startSeconds': None
		#theDict['stopSeconds': None

		# for detection of Ca from line scans
		#theDict['caThresholdPos'] = 0.01
		#theDict['caMinSpike'] = 0.5

		return theDict.copy()

	def _backupSpikeVm(self, medianFilter=None):
		"""
		when detecting with just mV threshold (not dv/dt)
		backup spike time using diminishnig SD and diff b/w vm at pnt[i]-pnt[i-1]
		"""
		print('_backupSpikeVm() medianFilter:', medianFilter)
		realSpikeTimePnts = [np.nan] * self.numSpikes

		medianFilter = 5
		if medianFilter>0:
			myVm = scipy.signal.medfilt(self.abf.sweepY, medianFilter)
		else:
			myVm = self.abf.sweepY

		maxNumPntsToBackup = 20 # todo: add _ms
		bin_ms = 1
		bin_pnts = bin_ms * self.abf.dataPointsPerMs
		half_bin_pnts = math.floor(bin_pnts/2)
		for idx, spikeTimePnts in enumerate(self.spikeTimes):
			foundRealThresh = False
			thisMean = None
			thisSD = None
			backupNumPnts = 0
			atBinPnt = spikeTimePnts
			while not foundRealThresh:
				thisWin = myVm[atBinPnt-half_bin_pnts: atBinPnt+half_bin_pnts]
				if thisMean is None:
					thisMean = np.mean(thisWin)
					thisSD = np.std(thisWin)

				nextStart = atBinPnt-1-bin_pnts-half_bin_pnts
				nextStop = atBinPnt-1-bin_pnts+half_bin_pnts
				nextWin = myVm[nextStart:nextStop]
				nextMean = np.mean(nextWin)
				nextSD = np.std(nextWin)

				meanDiff = thisMean - nextMean
				# logic
				#print(f'  spike {idx} backupNumPnts:{backupNumPnts} meanDiff:{meanDiff} thisSD:{thisSD}')
				sdMult = 0.7 # 2
				#if meanDiff < thisSD * sdMult: #* 1.2: #* 1.5:
				if (meanDiff < nextSD * sdMult) or (backupNumPnts==maxNumPntsToBackup):
					# second clause will force us to terminate (this recording has a very slow rise time)
					# bingo!
					foundRealThresh = True
					# not this xxx but the previous
					moveForwardPnts = 4
					backupNumPnts = backupNumPnts - 1 # the prev is thresh
					if backupNumPnts<moveForwardPnts:
						print(f'  WARNING: _backupSpikeVm() spike {idx} backupNumPnts:{backupNumPnts} < moveForwardPnts:{moveForwardPnts}')
						#print('  -->> not adjusting spike time')
						realBackupPnts = backupNumPnts - 0
						realPnt = spikeTimePnts - (realBackupPnts*bin_pnts)

					else:
						realBackupPnts = backupNumPnts - moveForwardPnts
						realPnt = spikeTimePnts - (realBackupPnts*bin_pnts)
					'''
					print(f'spike {idx}')
					print(f'  backupNumPnts:{backupNumPnts} meanDiff:{meanDiff} thisSD:{thisSD}')
					print(f'  orig spikeTimePnts:{spikeTimePnts} realPnt:{realPnt} atBinPnt:{atBinPnt}')
					print(f'  orig spikeTimeSec {self.pnt2Sec_(spikeTimePnts)} realSec:{self.pnt2Sec_(realPnt)}')
					'''
					realSpikeTimePnts[idx] = realPnt

				# increment
				thisMean = nextMean
				thisSD = nextSD

				atBinPnt -= bin_pnts
				backupNumPnts += 1
				'''
				if backupNumPnts>maxNumPntsToBackup:
					print(f'  WARNING: _backupSpikeVm() exiting spike {idx} ... reached maxNumPntsToBackup:{maxNumPntsToBackup}')
					print('  -->> not adjusting spike time')
					foundRealThresh = True # set this so we exit the loop
					realSpikeTimePnts[idx] = spikeTimePnts
				'''

		#
		return realSpikeTimePnts

	def _throwOutRefractory(self, spikeTimes0, goodSpikeErrors, refractory_ms=20):
		"""
		spikeTimes0: spike times to consider
		goodSpikeErrors: list of errors per spike, can be None
		refractory_ms:
		"""
		print('  bAnalysis._throwOutRefractory() len(spikeTimes0)', len(spikeTimes0), 'reject shorter than refractory_ms:', refractory_ms)
		#
		# if there are doubles, throw-out the second one
		#refractory_ms = 20 #10 # remove spike [i] if it occurs within refractory_ms of spike [i-1]
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
		if goodSpikeErrors is not None:
			goodSpikeErrors = [goodSpikeErrors[idx] for idx, spikeTime in enumerate(spikeTimes0) if spikeTime]
		spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if spikeTime]

		print('    after len(spikeTimes0)', len(spikeTimes0))

		return spikeTimes0, goodSpikeErrors
	'''
	def spikeDetect0(self, dvdtThreshold=100, mvThreshold=-20,
						peakWindow_ms=10,
						window_ms=2,
						refractory_ms=20,
						dvdt_percentOfMax=0.1,
						medianFilter=0, verbose=True): #, startSeconds=None, stopSeconds=None):
	'''
	def _getErrorDict(self, spikeNumber, pnt, type, detailStr):
		#print('_getErrorDict() pnt:', pnt, 'self.abf.dataRate:', self.abf.dataRate, 'self.abf.dataPointsPerMs:', self.abf.dataPointsPerMs)
		# self.abf.dataRate
		sec = pnt / self.abf.dataPointsPerMs / 1000
		eDict = {} #OrderedDict()
		eDict['Spike'] = spikeNumber
		eDict['Seconds'] = sec
		eDict['Type'] = type
		eDict['Details'] = detailStr
		return eDict

	def spikeDetect0(self, dDict, verbose=False):
		"""
		look for threshold crossings (dvdtThreshold) in first derivative (dV/dt) of membrane potential (Vm)
		append each threshold crossing (e.g. a spike) in self.spikeTimes list

		Returns:
			self.thresholdTimes (pnts): the time of each threshold crossing
			self.spikeTimes (pnts): the time before each threshold crossing when dv/dt crosses 15% of its max
			self.filteredVm:
			self.filtereddVdt:
		"""

		#for k,v in dDict.items():

		if verbose:
			print('bAnalysis.spikeDetect0()')
			print('	 dvdtThreshold:', dDict['dvdtThreshold'])
			print('	 mvThreshold:', dDict['mvThreshold'])
			print('	 medianFilter:', dDict['medianFilter'])

		#
		# header
		now = datetime.datetime.now()
		dateStr = now.strftime('%Y-%m-%d %H:%M:%S')
		self.dateAnalyzed = dateStr

		self.detectionType = 'dVdtThreshold'
		self.dvdtThreshold = dDict['dvdtThreshold']
		self.mvThreshold = dDict['mvThreshold'] # todo: remove
		self.medianFilter = dDict['medianFilter']

		#
		#
		startPnt = 0
		stopPnt = len(self.abf.sweepX) - 1
		secondsOffset = 0
		'''
		if dDict['startSeconds'] is not None and dDict['stopSeconds'] is not None:
			startPnt = self.dataPointsPerMs * (dDict['startSeconds']*1000) # seconds to pnt
			stopPnt = self.dataPointsPerMs * (dDict['stopSeconds']*1000) # seconds to pnt
		'''

		Is=np.where(self.filteredDeriv>dDict['dvdtThreshold'])[0]
		Is=np.concatenate(([0],Is))
		Ds=Is[:-1]-Is[1:]+1
		spikeTimes0 = Is[np.where(Ds)[0]+1]

		#
		# reduce spike times based on start/stop
		# only include spike times between startPnt and stopPnt
		spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if (spikeTime>=startPnt and spikeTime<=stopPnt)]

		#
		# throw out all spikes that are below a threshold Vm (usually below -20 mV)
		#spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if self.abf.sweepY[spikeTime] > self.mvThreshold]
		peakWindow_pnts = self.abf.dataPointsPerMs * dDict['peakWindow_ms']
		# abb 20210130 lcr analysis
		peakWindow_pnts = round(peakWindow_pnts)
		goodSpikeTimes = []
		for spikeTime in spikeTimes0:
			peakVal = np.max(self.abf.sweepY[spikeTime:spikeTime+peakWindow_pnts])
			if peakVal > dDict['mvThreshold']:
				goodSpikeTimes.append(spikeTime)
		spikeTimes0 = goodSpikeTimes

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
		#refractory_ms = 20 #10 # remove spike [i] if it occurs within refractory_ms of spike [i-1]

		spikeTimeErrors = None
		spikeTimes0, ignoreSpikeErrors = self._throwOutRefractory(spikeTimes0, spikeTimeErrors, refractory_ms=dDict['refractory_ms'])

		'''
		lastGood = 0 # first spike [0] will always be good, there is no spike [i-1]
		for i in range(len(spikeTimes0)):
			if i==0:
				# first spike is always good
				continue
			dPoints = spikeTimes0[i] - spikeTimes0[lastGood]
			if dPoints < self.abf.dataPointsPerMs * dDict['refractory_ms']:
				# remove spike time [i]
				spikeTimes0[i] = 0
			else:
				# spike time [i] was good
				lastGood = i
		# regenerate spikeTimes0 by throwing out any spike time that does not pass 'if spikeTime'
		# spikeTimes[i] that were set to 0 above (they were too close to the previous spike)
		# will not pass 'if spikeTime', as 'if 0' evaluates to False
		spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if spikeTime]
		'''

		#
		# for each threshold crossing, search backwards in dV/dt for a % of maximum (about 10 ms)
		#dvdt_percentOfMax = 0.1
		#window_ms = 2
		window_pnts = dDict['dvdtPreWindow_ms'] * self.dataPointsPerMs
		# abb 20210130 lcr analysis
		window_pnts = round(window_pnts)
		spikeTimes1 = []
		spikeErrorList1 = []
		for i, spikeTime in enumerate(spikeTimes0):
			# get max in derivative

			# 20210130, was this
			# was this
			# this is a legit bug !!!! I was only looking before
			# should be looking before AND after
			preDerivClip = self.filteredDeriv[spikeTime-window_pnts:spikeTime] # backwards
			postDerivClip = self.filteredDeriv[spikeTime:spikeTime+window_pnts] # backwards

			# 20210130 lcr analysis now this
			#preDerivClip = self.filteredDeriv[spikeTime-window_pnts:spikeTime+window_pnts] # backwards

			if len(preDerivClip) == 0:
				print('error: spikeDetect0()',
						'spike', i, 'at pnt', spikeTime,
						'window_pnts:', window_pnts,
						'dvdtPreWindow_ms:', dDict['dvdtPreWindow_ms'],
						'len(preDerivClip)', len(preDerivClip))#preDerivClip = np.flip(preDerivClip)

			# look for % of max in dvdt
			try:
				#peakPnt = np.argmax(preDerivClip)
				peakPnt = np.argmax(postDerivClip)
				#peakPnt += spikeTime-window_pnts
				peakPnt += spikeTime
				peakVal = self.filteredDeriv[peakPnt]

				percentMaxVal = peakVal * dDict['dvdt_percentOfMax'] # value we are looking for in dv/dt
				preDerivClip = np.flip(preDerivClip) # backwards
				tmpWhere = np.where(preDerivClip<percentMaxVal)
				#print('tmpWhere:', type(tmpWhere), tmpWhere)
				tmpWhere = tmpWhere[0]
				if len(tmpWhere) > 0:
					threshPnt2 = np.where(preDerivClip<percentMaxVal)[0][0]
					threshPnt2 = (spikeTime) - threshPnt2
					#print('i:', i, 'spikeTime:', spikeTime, 'peakPnt:', peakPnt, 'threshPnt2:', threshPnt2)
					threshPnt2 -= 1 # backup by 1 pnt
					spikeTimes1.append(threshPnt2)
					spikeErrorList1.append(None)

				else:
					errType = 'dvdtPercent'
					errStr = f"dvdtPercent error searching for dvdt_percentOfMax: {dDict['dvdt_percentOfMax']} peak dV/dt is {peakVal}"
					#print(f'   error: bAnalysis.spikeDetect0() spike {i} looking for dvdt_percentOfMax:', dDict['dvdt_percentOfMax'], 'peak dV/dt is', peakVal)
					#print('      ', 'np.where did not find preDerivClip<percentMaxVal')
					spikeTimes1.append(spikeTime)
					eDict = self._getErrorDict(i, spikeTime, errType, errStr) # spikeTime is in pnts
					#print('testing eDict:', eDict)
					spikeErrorList1.append(eDict)
			except (IndexError, ValueError) as e:
				##
				print('   error: bAnalysis.spikeDetect0() looking for dvdt_percentOfMax')
				print('      ', 'IndexError for spike', i, spikeTime)
				print('      ', e)
				##
				spikeTimes1.append(spikeTime)

		self.thresholdTimes = spikeTimes0 # points
		self.spikeTimes = spikeTimes1 # points

		return self.spikeTimes, self.thresholdTimes, self.filteredVm, self.filteredDeriv, spikeErrorList1

	#def spikeDetect00(self, mvThreshold=-20, refractory_ms=20, medianFilter=0, verbose=True): #, startSeconds=None, stopSeconds=None):
	def spikeDetect00(self, dDict, verbose=False):
		"""
		detect using Vm threshold and NOT dvdt
		append each threshold crossing (e.g. a spike) in self.spikeTimes list

		Returns:
			self.thresholdTimes (pnts): the time of each threshold crossing
			self.spikeTimes (pnts): the time before each threshold crossing when dv/dt crosses 15% of its max
			self.filteredVm:
			self.filtereddVdt:
		"""

		if verbose:
			print('bAnalysis.spikeDetect00() mvThreshold:', dDict['mvThreshold'])

		#
		# header
		now = datetime.datetime.now()
		dateStr = now.strftime('%Y-%m-%d %H:%M:%S')
		self.dateAnalyzed = dateStr

		self.detectionType = 'mvThreshold'
		self.dvdtThreshold = None					# 20190623 - IMPORTANT
		self.mvThreshold = dDict['mvThreshold']
		self.medianFilter = dDict['medianFilter']
		#self.startSeconds = startSeconds
		#self.stopSeconds = stopSeconds

		#
		#
		startPnt = 0
		stopPnt = len(self.abf.sweepX) - 1
		secondsOffset = 0
		'''
		if dDict['startSeconds'] is not None and dDict['stopSeconds'] is not None:
			startPnt = self.dataPointsPerMs * (dDict['startSeconds']*1000) # seconds to pnt
			stopPnt = self.dataPointsPerMs * (dDict['stopSeconds']*1000) # seconds to pnt
		'''

		Is=np.where(self.filteredVm>dDict['mvThreshold'])[0] # returns boolean array
		Is=np.concatenate(([0],Is))
		Ds=Is[:-1]-Is[1:]+1
		spikeTimes0 = Is[np.where(Ds)[0]+1]
		if verbose:
			print('  bAnalysis.spikeDetect00() spikeTimes0:', len(spikeTimes0), spikeTimes0)

		#
		# reduce spike times based on start/stop
		spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if (spikeTime>=startPnt and spikeTime<=stopPnt)]
		spikeErrorList = [None] * len(spikeTimes0)

		#
		# throw out all spikes that are below a threshold Vm (usually below -20 mV)
		#spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if self.abf.sweepY[spikeTime] > self.mvThreshold]
		# 20190623 - already done in this vm threshold funtion
		"""
		peakWindow_ms = 10
		peakWindow_pnts = self.abf.dataPointsPerMs * peakWindow_ms
		goodSpikeTimes = []
		for spikeTime in spikeTimes0:
			peakVal = np.max(self.abf.sweepY[spikeTime:spikeTime+peakWindow_pnts])
			if peakVal > self.mvThreshold:
				goodSpikeTimes.append(spikeTime)
		spikeTimes0 = goodSpikeTimes
		"""

		#
		# throw out spike that are NOT upward deflections of Vm
		tmpLastGoodSpike_pnts = None
		#minISI_pnts = 5000 # at 20 kHz this is 0.25 sec
		minISI_ms = 75 #250
		minISI_pnts = self.ms2Pnt_(minISI_ms)

		prePntUp = 10 # pnts
		goodSpikeTimes = []
		goodSpikeErrors = []
		for tmpIdx, spikeTime in enumerate(spikeTimes0):
			tmpFuckPreClip = self.abf.sweepY[spikeTime-prePntUp:spikeTime] # not including the stop index
			tmpFuckPostClip = self.abf.sweepY[spikeTime+1:spikeTime+prePntUp+1] # not including the stop index
			preAvg = np.average(tmpFuckPreClip)
			postAvg = np.average(tmpFuckPostClip)
			if postAvg > preAvg:
				tmpSpikeTimeSec = self.pnt2Sec_(spikeTime)
				if tmpLastGoodSpike_pnts is not None and (spikeTime-tmpLastGoodSpike_pnts) < minISI_pnts:
					continue
				goodSpikeTimes.append(spikeTime)
				goodSpikeErrors.append(spikeErrorList[tmpIdx])
				tmpLastGoodSpike_pnts = spikeTime
			else:
				tmpSpikeTimeSec = self.pnt2Sec_(spikeTime)

		# todo: add this to spikeDetect0()
		goodSpikeTimes, goodSpikeErrors = self._throwOutRefractory(goodSpikeTimes, goodSpikeErrors, refractory_ms=dDict['refractory_ms'])
		spikeTimes0 = goodSpikeTimes
		spikeErrorList = goodSpikeErrors

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

		self.spikeTimes = spikeTimes0

		#
		return self.spikeTimes, self.filteredVm, self.filteredDeriv, spikeErrorList

	'''
	def spikeDetect(self, dvdtThreshold=100, mvThreshold=-20,
					medianFilter=0, halfHeights=[20, 50, 80],
					refractory_ms=20, peakWindow_ms=10,
					window_ms=2, avgWindow_ms=5,
					dvdt_percentOfMax=0.1, halfWidthWindow_ms = 20,
					spikeClipWidth_ms=500, onlyPeaksAbove_mV=None,
					verbose=True): #, startSeconds=None, stopSeconds=None):
	'''
	def spikeDetect(self, dDict, verbose=False):
		'''
		spike detect the current sweep and put results into spikeTime[currentSweep]

		parameters:
			dDict: detection dictionary from self.getDefaultDetection
		'''

		self.detectionDict = dDict # remember the parameters of our last detection

		startTime = time.time()

		# todo: but sanpy analysis versions in seperate file, add documentation as to what has changed
		#analysisVersion = '0.1.3'

		if verbose:
			sanpy.bUtil.printDict(dDict)

		self.getDerivative(dDict)

		self.spikeDict = [] # we are filling this in, one dict for each spike

		self.numErrors = 0
		detectionType = None

		# spike detect
		if dDict['dvdtThreshold'] is None or np.isnan(dDict['dvdtThreshold']):
			# detect using mV threshold
			detectionType = 'mv'
			self.thresholdTimes = None
			self.spikeTimes, vm, dvdt, spikeErrorList = self.spikeDetect00(dDict, verbose=verbose)

			# backup childish vm threshold
			if dDict['doBackupSpikeVm']:
				self.spikeTimes = self._backupSpikeVm(dDict['medianFilter'])

			'''
			self.spikeTimes, vm, dvdt = \
				self.spikeDetect00(mvThreshold=mvThreshold, medianFilter=medianFilter,
									refractory_ms=refractory_ms,
									verbose=verbose) #, startSeconds=startSeconds, stopSeconds=stopSeconds)
			'''
		else:
			# detect using dv/dt threshold AND min mV
			detectionType = 'dvdt'
			self.spikeTimes, self.thresholdTimes, vm, dvdt, spikeErrorList = self.spikeDetect0(dDict, verbose=verbose)
			'''
			self.spikeTimes, self.thresholdTimes, vm, dvdt = \
				self.spikeDetect0(dvdtThreshold=dvdtThreshold, mvThreshold=mvThreshold,
									peakWindow_ms=peakWindow_ms,
									window_ms=window_ms,
									refractory_ms=refractory_ms,
									dvdt_percentOfMax=dvdt_percentOfMax,
									medianFilter=medianFilter, verbose=verbose) #, startSeconds=startSeconds, stopSeconds=stopSeconds)
			'''

		#
		# look in a window after each threshold crossing to get AP peak
		peakWindow_pnts = self.abf.dataPointsPerMs * dDict['peakWindow_ms']
		peakWindow_pnts = round(peakWindow_pnts)

		# throw out spikes that have peak below onlyPeaksAbove_mV
		newSpikeTimes = []
		newSpikeErrorList = []
		if dDict['onlyPeaksAbove_mV'] is not None:
			for i, spikeTime in enumerate(self.spikeTimes):
				peakPnt = np.argmax(vm[spikeTime:spikeTime+peakWindow_pnts])
				peakPnt += spikeTime
				peakVal = np.max(vm[spikeTime:spikeTime+peakWindow_pnts])
				if peakVal > dDict['onlyPeaksAbove_mV']:
					newSpikeTimes.append(spikeTime)
					newSpikeErrorList.append(spikeErrorList[i])
				else:
					print('peak height: rejecting spike', i, 'at pnt:', spikeTime, "dDict['onlyPeaksAbove_mV']:", dDict['onlyPeaksAbove_mV'])
			#
			self.spikeTimes = newSpikeTimes
			spikeErrorList = newSpikeErrorList
		#
		# throw out spikes on a down-slope
		avgWindow_pnts = dDict['avgWindow_ms'] * self.abf.dataPointsPerMs
		avgWindow_pnts = math.floor(avgWindow_pnts/2)

		for i, spikeTime in enumerate(self.spikeTimes):
			# spikeTime units is ALWAYS points

			peakPnt = np.argmax(vm[spikeTime:spikeTime+peakWindow_pnts])
			peakPnt += spikeTime
			peakVal = np.max(vm[spikeTime:spikeTime+peakWindow_pnts])

			spikeDict = collections.OrderedDict() # use OrderedDict so Pandas output is in the correct order

			spikeDict['include'] = 1
			spikeDict['analysisVersion'] = sanpy.analysisVersion
			spikeDict['interfaceVersion'] = sanpy.interfaceVersion
			spikeDict['file'] = self.file

			spikeDict['detectionType'] = detectionType
			#spikeDict['condition1'] = self.condition1
			#spikeDict['condition2'] = self.condition2
			#spikeDict['condition3'] = self.condition3
			#spikeDict['condition4'] = self.condition4
			spikeDict['cellType'] = dDict['cellType']
			spikeDict['sex'] = dDict['sex']
			spikeDict['condition'] = dDict['condition']

			spikeDict['spikeNumber'] = i

			spikeDict['numError'] = 0
			spikeDict['errors'] = []
			# append existing spikeErrorList from spikeDetect0() or spikeDetect00()
			tmpError = spikeErrorList[i]
			if tmpError is not None and tmpError != np.nan:
				spikeDict['numError'] += 1
				spikeDict['errors'].append(tmpError) # tmpError is from:
							#eDict = self._getErrorDict(i, spikeTime, errType, errStr) # spikeTime is in pnts


			#spikeDict['startSeconds'] = startSeconds
			#spikeDict['stopSeconds'] = stopSeconds

			# detection params
			spikeDict['dvdtThreshold'] = dDict['dvdtThreshold']
			spikeDict['mvThreshold'] = dDict['mvThreshold']
			spikeDict['medianFilter'] = dDict['medianFilter']
			spikeDict['halfHeights'] = dDict['halfHeights']

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
			#self.spikeDict[i]['postMinPnt'] = None
			#self.spikeDict[i]['postMinVal'] = defaultVal

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
			#self.spikeDict[i]['apDuration_ms'] = defaultVal
			self.spikeDict[i]['diastolicDuration_ms'] = defaultVal

			# any number of spike widths
			self.spikeDict[i]['widths'] = []
			for halfHeight in dDict['halfHeights']:
				widthDict = {
					'halfHeight': halfHeight,
					'risingPnt': None,
					'risingVal': defaultVal,
					'fallingPnt': None,
					'fallingVal': defaultVal,
					'widthPnts': None,
					'widthMs': defaultVal
				}
				# abb 20210125, make column width_<n> where <n> is 'halfHeight'
				self.spikeDict[i]['widths_' + str(halfHeight)] = defaultVal
				# was this
				self.spikeDict[i]['widths'].append(widthDict)

			# The nonlinear late diastolic depolarization phase was estimated as the duration between 1% and 10% dV/dt
			# todo: not done !!!!!!!!!!

			# 20210413, was this. This next block is for pre spike analysis
			#			ok if we are at last spike
			#if i==0 or i==len(self.spikeTimes)-1:
			if i==0:
				# was continue but moved half width out of here
				pass
			else:
				mdp_ms = dDict['mdp_ms']
				mdp_pnts = mdp_ms * self.abf.dataPointsPerMs
				#
				# pre spike min
				#preRange = vm[self.spikeTimes[i-1]:self.spikeTimes[i]]
				startPnt = self.spikeTimes[i]-mdp_pnts
				preRange = vm[startPnt:self.spikeTimes[i]] # EXCEPTION
				preMinPnt = np.argmin(preRange)
				#preMinPnt += self.spikeTimes[i-1]
				preMinPnt += startPnt
				# the pre min is actually an average around the real minima
				avgRange = vm[preMinPnt-avgWindow_pnts:preMinPnt+avgWindow_pnts]
				preMinVal = np.average(avgRange)

				# search backward from spike to find when vm reaches preMinVal (avg)
				preRange = vm[preMinPnt:self.spikeTimes[i]]
				preRange = np.flip(preRange) # we want to search backwards from peak
				try:
					preMinPnt2 = np.where(preRange<preMinVal)[0][0]
					preMinPnt = self.spikeTimes[i] - preMinPnt2
					self.spikeDict[i]['preMinPnt'] = preMinPnt
					self.spikeDict[i]['preMinVal'] = preMinVal

				except (IndexError) as e:
					self.spikeDict[i]['numError'] = self.spikeDict[i]['numError'] + 1
					# sometimes preRange is empty, don't try and put min/max in error
					errorStr = 'searching for preMinVal:' + str(preMinVal) #+ ' postRange min:' + str(np.min(postRange)) + ' max ' + str(np.max(postRange))
					eDict = self._getErrorDict(i, self.spikeTimes[i], 'preMin', errorStr) # spikeTime is in pnts
					self.spikeDict[i]['errors'].append(eDict)
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

				# linear fit before spike
				self.spikeDict[i]['preLinearFitPnt0'] = preLinearFitPnt0
				self.spikeDict[i]['preLinearFitPnt1'] = preLinearFitPnt1
				self.spikeDict[i]['earlyDiastolicDuration_ms'] = self.pnt2Ms_(preLinearFitPnt1 - preLinearFitPnt0)
				self.spikeDict[i]['preLinearFitVal0'] = preLinearFitVal0
				self.spikeDict[i]['preLinearFitVal1'] = preLinearFitVal1

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
					errorStr = 'earlyDiastolicDurationRate fit'
					eDict = self._getErrorDict(i, self.spikeTimes[i], 'fitEDD', errorStr) # spikeTime is in pnts
					self.spikeDict[i]['errors'].append(eDict)

				# not implemented
				#self.spikeDict[i]['lateDiastolicDuration'] = ???

			if True:
				#
				# maxima in dv/dt before spike
				# added try/except sunday april 14, seems to break spike detection???
				try:
					# 20210415 was this
					#preRange = dvdt[self.spikeTimes[i]:peakPnt]
					preRange = dvdt[self.spikeTimes[i]:peakPnt+1]
					preSpike_dvdt_max_pnt = np.argmax(preRange)
					preSpike_dvdt_max_pnt += self.spikeTimes[i]
					self.spikeDict[i]['preSpike_dvdt_max_pnt'] = preSpike_dvdt_max_pnt
					self.spikeDict[i]['preSpike_dvdt_max_val'] = vm[preSpike_dvdt_max_pnt] # in units mV
					self.spikeDict[i]['preSpike_dvdt_max_val2'] = dvdt[preSpike_dvdt_max_pnt] # in units mV
				except (ValueError) as e:
					self.spikeDict[i]['numError'] = self.spikeDict[i]['numError'] + 1
					# sometimes preRange is empty, don't try and put min/max in error
					#print('preRange:', preRange)
					errorStr = 'searching for preSpike_dvdt_max_pnt:'
					eDict = self._getErrorDict(i, self.spikeTimes[i], 'preSpikeDvDt', errorStr) # spikeTime is in pnts
					self.spikeDict[i]['errors'].append(eDict)
					self.numErrors += 1

			# 20210501, we do not need postMin/mdp, not used anywhere else
			'''
			if i==len(self.spikeTimes)-1:
				# last spike
				pass
			else:
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
					self.spikeDict[i]['postMinPnt'] = postMinPnt
					self.spikeDict[i]['postMinVal'] = postMinVal
				except (IndexError) as e:
					self.spikeDict[i]['numError'] = self.spikeDict[i]['numError'] + 1
					# sometimes postRange is empty, don't try and put min/max in error
					#print('postRange:', postRange)
					errorStr = 'searching for postMinVal:' + str(postMinVal) #+ ' postRange min:' + str(np.min(postRange)) + ' max ' + str(np.max(postRange))
					eDict = self._getErrorDict(i, self.spikeTimes[i], 'postMinError', errorStr) # spikeTime is in pnts
					self.spikeDict[i]['errors'].append(eDict)
					self.numErrors += 1
			'''

			if True:
				#
				# minima in dv/dt after spike
				#postRange = dvdt[self.spikeTimes[i]:postMinPnt]
				postSpike_ms = 10
				postSpike_pnts = self.abf.dataPointsPerMs * postSpike_ms
				# abb 20210130 lcr analysis
				postSpike_pnts = round(postSpike_pnts)
				#postRange = dvdt[self.spikeTimes[i]:self.spikeTimes[i]+postSpike_pnts] # fixed window after spike
				postRange = dvdt[peakPnt:peakPnt+postSpike_pnts] # fixed window after spike

				postSpike_dvdt_min_pnt = np.argmin(postRange)
				postSpike_dvdt_min_pnt += peakPnt
				self.spikeDict[i]['postSpike_dvdt_min_pnt'] = postSpike_dvdt_min_pnt
				self.spikeDict[i]['postSpike_dvdt_min_val'] = vm[postSpike_dvdt_min_pnt]
				self.spikeDict[i]['postSpike_dvdt_min_val2'] = dvdt[postSpike_dvdt_min_pnt]

				# 202102
				#self.spikeDict[i]['preMinPnt'] = preMinPnt
				#self.spikeDict[i]['preMinVal'] = preMinVal
				# 202102
				#self.spikeDict[i]['postMinPnt'] = postMinPnt
				#self.spikeDict[i]['postMinVal'] = postMinVal

				# linear fit before spike
				#self.spikeDict[i]['preLinearFitPnt0'] = preLinearFitPnt0
				#self.spikeDict[i]['preLinearFitPnt1'] = preLinearFitPnt1
				#self.spikeDict[i]['earlyDiastolicDuration_ms'] = self.pnt2Ms_(preLinearFitPnt1 - preLinearFitPnt0)
				#self.spikeDict[i]['preLinearFitVal0'] = preLinearFitVal0
				#self.spikeDict[i]['preLinearFitVal1'] = preLinearFitVal1

				#
				# Action potential duration (APD) was defined as
				# the interval between the TOP and the subsequent MDP
				# 20210501, removed AP duration, use APD_90, APD_50 etc
				'''
				if i==len(self.spikeTimes)-1:
					pass
				else:
					self.spikeDict[i]['apDuration_ms'] = self.pnt2Ms_(postMinPnt - spikeDict['thresholdPnt'])
				'''

				#
				# diastolic duration was defined as
				# the interval between MDP and TOP
				if i > 0:
					# one off error when preMinPnt is not defined
					self.spikeDict[i]['diastolicDuration_ms'] = self.pnt2Ms_(spikeTime - preMinPnt)

				self.spikeDict[i]['cycleLength_ms'] = float('nan')
				if i>0: #20190627, was i>1
					isiPnts = self.spikeDict[i]['thresholdPnt'] - self.spikeDict[i-1]['thresholdPnt']
					isi_ms = self.pnt2Ms_(isiPnts)
					isi_hz = 1 / (isi_ms / 1000)
					self.spikeDict[i]['isi_pnts'] = isiPnts
					self.spikeDict[i]['isi_ms'] = self.pnt2Ms_(isiPnts)
					self.spikeDict[i]['spikeFreq_hz'] = 1 / (self.pnt2Ms_(isiPnts) / 1000)

					# Cycle length was defined as the interval between MDPs in successive APs
					prevPreMinPnt = self.spikeDict[i-1]['preMinPnt'] # can be nan
					thisPreMinPnt = self.spikeDict[i]['preMinPnt']
					if prevPreMinPnt is not None and thisPreMinPnt is not None:
						cycleLength_pnts = thisPreMinPnt - prevPreMinPnt
						self.spikeDict[i]['cycleLength_pnts'] = cycleLength_pnts
						self.spikeDict[i]['cycleLength_ms'] = self.pnt2Ms_(cycleLength_pnts)
					else:
						# error
						self.spikeDict[i]['numError'] = self.spikeDict[i]['numError'] + 1
						errorStr = 'previous spike preMinPnt is ' + str(prevPreMinPnt) + ' this preMinPnt:' + str(thisPreMinPnt)
						eDict = self._getErrorDict(i, self.spikeTimes[i], 'cycleLength', errorStr) # spikeTime is in pnts
						self.spikeDict[i]['errors'].append(eDict)
						self.numErrors += 1
					'''
					# 20210501 was this, I am no longer using postMinPnt
					prevPostMinPnt = self.spikeDict[i-1]['postMinPnt']
					tmpPostMinPnt = self.spikeDict[i]['postMinPnt']
					if prevPostMinPnt is not None and tmpPostMinPnt is not None:
						cycleLength_pnts = tmpPostMinPnt - prevPostMinPnt
						self.spikeDict[i]['cycleLength_pnts'] = cycleLength_pnts
						self.spikeDict[i]['cycleLength_ms'] = self.pnt2Ms_(cycleLength_pnts)
					else:
						self.spikeDict[i]['numError'] = self.spikeDict[i]['numError'] + 1
						errorStr = 'previous spike postMinPnt is ' + str(prevPostMinPnt) + ' this postMinPnt:' + str(tmpPostMinPnt)
						eDict = self._getErrorDict(i, self.spikeTimes[i], 'cycleLength', errorStr) # spikeTime is in pnts
						self.spikeDict[i]['errors'].append(eDict)
						self.numErrors += 1
					'''
			#
			# spike half with and APDur
			#

			#
			# 20210130, moving 'half width' out of inner if spike # is first/last
			#
			# get 1/2 height (actually, any number of height measurements)
			# action potential duration using peak and post min
			#self.spikeDict[i]['widths'] = []
			#print('*** calculating half width for spike', i)
			doWidthVersion2 = False

			#halfWidthWindow_ms = 20
			hwWindowPnts = dDict['halfWidthWindow_ms'] * self.abf.dataPointsPerMs
			hwWindowPnts = round(hwWindowPnts)

			tmpPeakSec = spikeDict['peakSec']
			tmpErrorType = None
			for j, halfHeight in enumerate(dDict['halfHeights']):
				# halfHeight in [20, 50, 80]
				if doWidthVersion2:
					tmpThreshVm = spikeDict['thresholdVal']
					thisVm = tmpThreshVm + (peakVal - tmpThreshVm) * (halfHeight * 0.01)
				else:
					# 20210413 was this
					#thisVm = postMinVal + (peakVal - postMinVal) * (halfHeight * 0.01)
					tmpThreshVm2 = spikeDict['thresholdVal']
					thisVm = tmpThreshVm2 + (peakVal - tmpThreshVm2) * (halfHeight * 0.01)
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
				widthMs = np.nan
				try:
					if doWidthVersion2:
						postRange = vm[peakPnt:peakPnt+hwWindowPnts]
					else:
						# 20210413 was this
						#postRange = vm[peakPnt:postMinPnt]
						postRange = vm[peakPnt:peakPnt+hwWindowPnts]
					fallingPnt = np.where(postRange<thisVm)[0] # less than
					if len(fallingPnt)==0:
						#error
						tmpErrorType = 'falling point'
						raise IndexError
					fallingPnt = fallingPnt[0] # first falling point
					fallingPnt += peakPnt
					fallingVal = vm[fallingPnt]

					# use the post/falling to find pre/rising
					if doWidthVersion2:
						preRange = vm[peakPnt-hwWindowPnts:peakPnt]
					else:
						tmpPreMinPnt2 = spikeDict['thresholdPnt']
						preRange = vm[tmpPreMinPnt2:peakPnt]
					risingPnt = np.where(preRange>fallingVal)[0] # greater than
					if len(risingPnt)==0:
						#error
						tmpErrorType = 'rising point'
						raise IndexError
					risingPnt = risingPnt[0] # first falling point

					if doWidthVersion2:
						risingPnt += peakPnt-hwWindowPnts
					else:
						risingPnt += spikeDict['thresholdPnt']
					risingVal = vm[risingPnt]

					# width (pnts)
					widthPnts = fallingPnt - risingPnt
					# 20210413
					widthPnts2 = fallingPnt - spikeDict['thresholdPnt']
					tmpRisingPnt = spikeDict['thresholdPnt']
					# assign
					widthDict['halfHeight'] = halfHeight
					# 20210413, put back in
					#widthDict['risingPnt'] = risingPnt
					widthDict['risingPnt'] = tmpRisingPnt
					widthDict['risingVal'] = risingVal
					widthDict['fallingPnt'] = fallingPnt
					widthDict['fallingVal'] = fallingVal
					widthDict['widthPnts'] = widthPnts
					widthDict['widthMs'] = widthPnts / self.abf.dataPointsPerMs
					widthMs = widthPnts / self.abf.dataPointsPerMs # abb 20210125
					# 20210413, todo: make these end in 2
					widthDict['widthPnts'] = widthPnts2
					widthDict['widthMs'] = widthPnts / self.abf.dataPointsPerMs

				except (IndexError) as e:
					##
					##
					#print('  ERROR: bAnalysis.spikeDetect() spike', i, 'half height', halfHeight)
					##
					##

					self.spikeDict[i]['numError'] = self.spikeDict[i]['numError'] + 1
					#errorStr = 'spike ' + str(i) + ' half width ' + str(tmpErrorType) + ' ' + str(halfHeight) + ' halfWidthWindow_ms:' + str(dDict['halfWidthWindow_ms'])
					errorStr = (f'half width {halfHeight} error in {tmpErrorType} '
							f"with halfWidthWindow_ms:{dDict['halfWidthWindow_ms']} "
							f'searching for Vm:{round(thisVm,2)} from peak sec {round(tmpPeakSec,2)}'
							)

					eDict = self._getErrorDict(i, self.spikeTimes[i], 'spikeWidth', errorStr) # spikeTime is in pnts
					self.spikeDict[i]['errors'].append(eDict)
					self.numErrors += 1

				# abb 20210125
				self.spikeDict[i]['widths_'+str(halfHeight)] = widthMs
				#self.spikeDict[i]['widths'].append(widthDict)
				self.spikeDict[i]['widths'][j] = widthDict

		#
		# look between threshold crossing to get minima
		# we will ignore the first and last spike

		# todo: call self.makeSpikeClips()
		#
		# build a list of spike clips
		#clipWidth_ms = 500
		clipWidth_pnts = dDict['spikeClipWidth_ms'] * self.abf.dataPointsPerMs
		clipWidth_pnts = round(clipWidth_pnts)
		if clipWidth_pnts % 2 == 0:
			pass # Even
		else:
			clipWidth_pnts += 1 # Odd

		halfClipWidth_pnts = int(clipWidth_pnts/2)

		print('  spikeDetect() clipWidth_pnts:', clipWidth_pnts, 'halfClipWidth_pnts:', halfClipWidth_pnts)
		# make one x axis clip with the threshold crossing at 0
		self.spikeClips_x = [(x-halfClipWidth_pnts)/self.abf.dataPointsPerMs for x in range(clipWidth_pnts)]

		#20190714, added this to make all clips same length, much easier to plot in MultiLine
		numPointsInClip = len(self.spikeClips_x)

		self.spikeClips = []
		self.spikeClips_x2 = []
		for idx, spikeTime in enumerate(self.spikeTimes):
			#currentClip = vm[spikeTime-halfClipWidth_pnts:spikeTime+halfClipWidth_pnts]
			currentClip = vm[spikeTime-halfClipWidth_pnts:spikeTime+halfClipWidth_pnts]
			if len(currentClip) == numPointsInClip:
				self.spikeClips.append(currentClip)
				self.spikeClips_x2.append(self.spikeClips_x) # a 2D version to make pyqtgraph multiline happy
			else:
				##
				##
				if idx==0 or idx==len(self.spikeTimes)-1:
					# don't report spike clip errors for first/last spike
					pass
				else:
					print('  ERROR: bAnalysis.spikeDetect() did not add clip for spike index', idx, 'at time', spikeTime, 'currentClip:', len(currentClip), 'numPointsInClip:', numPointsInClip)
				##
				##

		# 20210426
		# generate a df holding stats (used by scatterplotwidget)
		print('  making df to pass to scatterplotwidget')
		startSeconds = dDict['startSeconds']
		stopSeconds = dDict['stopSeconds']
		#tmpAnalysisName, df0 = self.getReportDf(theMin, theMax, savefile)
		dfReportForScatter = self.report(startSeconds, stopSeconds)

		stopTime = time.time()
		if verbose:
			print('bAnalysis.spikeDetect() for file', self.file)
			print('  detected', len(self.spikeTimes), 'spikes in', round(stopTime-startTime,2), 'seconds')
			self.errorReport(justTheNumber=False)

		return dfReportForScatter

	def makeSpikeClips(self, spikeClipWidth_ms, theseTime_sec=None):
		"""
		theseTime_sec

		return
			spikeClips_x2: ms
			spikeClips: sweepY
		"""

		print('makeSpikeClips() spikeClipWidth_ms:', spikeClipWidth_ms, 'theseTime_sec:', theseTime_sec)
		if theseTime_sec is None:
			theseTime_pnts = self.spikeTimes
		else:
			# convert theseTime_sec to pnts
			theseTime_ms = [x*1000 for x in theseTime_sec]
			theseTime_pnts = [x*self.abf.dataPointsPerMs for x in theseTime_ms]
			theseTime_pnts = [round(x) for x in theseTime_pnts]

		clipWidth_pnts = spikeClipWidth_ms * self.abf.dataPointsPerMs
		clipWidth_pnts = round(clipWidth_pnts)
		if clipWidth_pnts % 2 == 0:
			pass # Even
		else:
			clipWidth_pnts += 1 # Make odd even

		halfClipWidth_pnts = int(clipWidth_pnts/2)

		print('  makeSpikeClips() clipWidth_pnts:', clipWidth_pnts, 'halfClipWidth_pnts:', halfClipWidth_pnts)
		# make one x axis clip with the threshold crossing at 0
		self.spikeClips_x = [(x-halfClipWidth_pnts)/self.abf.dataPointsPerMs for x in range(clipWidth_pnts)]

		#20190714, added this to make all clips same length, much easier to plot in MultiLine
		numPointsInClip = len(self.spikeClips_x)

		self.spikeClips = []
		self.spikeClips_x2 = []

		#for idx, spikeTime in enumerate(self.spikeTimes):
		for idx, spikeTime in enumerate(theseTime_pnts):
			#currentClip = vm[spikeTime-halfClipWidth_pnts:spikeTime+halfClipWidth_pnts]
			currentClip = self.abf.sweepY[spikeTime-halfClipWidth_pnts:spikeTime+halfClipWidth_pnts]
			if len(currentClip) == numPointsInClip:
				self.spikeClips.append(currentClip)
				self.spikeClips_x2.append(self.spikeClips_x) # a 2D version to make pyqtgraph multiline happy
			else:
				pass
				##
				print('  ERROR: bAnalysis.spikeDetect() did not add clip for spike index', idx, 'at time', spikeTime, 'currentClip:', len(currentClip), 'numPointsInClip:', numPointsInClip)
				##

		#
		return self.spikeClips_x2, self.spikeClips

	def getSpikeClips(self, theMin, theMax):
		"""
		get 2d list of spike clips, spike clips x, and 1d mean spike clip
		"""
		if theMin is None or theMax is None:
			theMin = 0
			theMax = self.abf.sweepX[-1]

		# make a list of clips within start/stop (Seconds)
		theseClips = []
		theseClips_x = []
		tmpClips = [] # for mean clip
		meanClip = []
		#if start is not None and stop is not None:
		for idx, clip in enumerate(self.spikeClips):
			spikeTime = self.spikeTimes[idx]
			spikeTime = self.pnt2Sec_(spikeTime)
			if spikeTime>=theMin and spikeTime<=theMax:
				theseClips.append(clip)
				theseClips_x.append(self.spikeClips_x2[idx]) # remember, all _x are the same
				if len(self.spikeClips_x) == len(clip):
					tmpClips.append(clip) # for mean clip
		if len(tmpClips):
			meanClip = np.mean(tmpClips, axis=0)

		return theseClips, theseClips_x, meanClip

	############################################################
	# output reports
	############################################################
	def errorReport(self, justTheNumber=False):
		"""
		return dfError
		"""

		dictList = []

		numError = 0
		errorList = []
		for spikeIdx, spike in enumerate(self.spikeDict):
			for idx, error in enumerate(spike['errors']):
				# error is dict from _getErorDict
				if error is None or error == np.nan or error == 'nan':
					continue
				dictList.append(error)
		#
		print('bAnalysis.errorReport() generated dictList:')
		for error in dictList:
			print(error)

		if len(dictList) == 0:
			dfError = None
		else:
			dfError = pd.DataFrame(dictList)

		print('bAnalysis.errorReport() returning dfError:', dfError)
		return dfError

	def report(self, theMin, theMax):
		"""
		return entire spikeDict as a pandas data frame

		(theMin, theMax): start/stop seconds of the analysis
		"""
		if theMin is None or theMax is None:
			return None

		df = pd.DataFrame(self.spikeDict)
		df = df[df['thresholdSec'].between(theMin, theMax, inclusive=True)]

		# added when trying to make scatterwidget for one file
		#print('  20210426 adding columns in bAnalysis.report()')
		#df['Condition'] = 	df['condition1']
		#df['File Number'] = 	df['condition2']
		#df['Sex'] = 	df['condition3']
		#df['Region'] = 	df['condition4']

		# make new column with sex/region encoded
		'''
		tmpNewCol = 'RegSex'
		self.masterDf[tmpNewCol] = ''
		for tmpRegion in ['Superior', 'Inferior']:
			for tmpSex in ['Male', 'Female']:
				newEncoding = tmpRegion[0] + tmpSex[0]
				regSex = self.masterDf[ (self.masterDf['Region']==tmpRegion) & (self.masterDf['Sex']==tmpSex)]
				regSex = (self.masterDf['Region']==tmpRegion) & (self.masterDf['Sex']==tmpSex)
				print('newEncoding:', newEncoding, 'regSex:', regSex.shape)
				self.masterDf.loc[regSex, tmpNewCol] = newEncoding
		'''

		# want this but region/sex/condition are not defined
		print('bAnalysis.report()')
		print(df.head())
		tmpNewCol = 'CellTypeSex'
		cellTypeStr = df['cellType'].iloc[0]
		sexStr = df['sex'].iloc[0]
		print('cellTypeStr:', cellTypeStr, 'sexStr:', sexStr)
		regSexEncoding = cellTypeStr + sexStr
		df[tmpNewCol] = regSexEncoding

		minStr = '%.2f'%(theMin)
		maxStr = '%.2f'%(theMax)
		minStr = minStr.replace('.', '_')
		maxStr = maxStr.replace('.', '_')
		tmpPath, tmpFile = os.path.split(self.file)
		tmpFile, tmpExt = os.path.splitext(tmpFile)
		analysisName = tmpFile + '_s' + minStr + '_s' + maxStr
		print('    minStr:', minStr, 'maxStr:', maxStr, 'analysisName:', analysisName)
		df['analysisname'] = analysisName

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
			#spikeDict['Post AP Min (mV)'] = spike['postMinVal']
			#
			#spikeDict['AP Duration (ms)'] = spike['apDuration_ms']
			spikeDict['Early Diastolic Duration (ms)'] = spike['earlyDiastolicDuration_ms']
			spikeDict['Early Diastolic Depolarization Rate (dV/s)'] = spike['earlyDiastolicDurationRate'] # abb 202012
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

	#################################################################################
	# save results (e.g. report)
	#################################################################################
	def saveReport(self, savefile, theMin=None, theMax=None, saveExcel=True, alsoSaveTxt=True, verbose=True):
		"""
		save a spike report for detected spikes between theMin (sec) and theMax (sec)

		savefile: path to xlsx file
		(theMin, theMax): start/stop seconds of the analysis

		Return:
			analysisName
			df
		"""

		if theMin == None:
			theMin = 0
		if theMax == None:
			theMax = self.abf.sweepX[-1]

		'''
		filePath, fileName = os.path.split(os.path.abspath(self.file))
		fileBaseName, extension = os.path.splitext(fileName)
		excelFilePath = os.path.join(filePath, fileBaseName + '.xlsx')
		'''

		#print('AnalysisApp.report() saving', excelFilePath)
		#print('Asking user for file name to save...')

		#savefile will be full path to user specified file
		'''
		savefile = asksaveasfilename(filetypes=(("Excel files", "*.xlsx"),
									("All files", "*.*") ),
									initialdir=filePath,
									initialfile=fileBaseName + '.xlsx')
		'''

		# always grab a df to the entire analysis (not sure what I will do with this)
		#df = self.report() # report() is my own 'bob' verbiage

		theRet = None

		if saveExcel and savefile:
			if verbose: print('    bAnalysis.saveReport() saving user specified .xlsx file:', savefile)
			excelFilePath = savefile
			writer = pd.ExcelWriter(excelFilePath, engine='xlsxwriter')

			#
			# cardiac style analysis to sheet 'cardiac'
			cardiac_df = self.report2(theMin, theMax) # report2 is more 'cardiac'

			#
			# header sheet
			headerDict = collections.OrderedDict()
			headerDict['file'] = [self.file]

			#headerDict['Condition 1'] = [self.condition1]
			#headerDict['Condition 2'] = [self.condition2]
			#headerDict['Condition 3'] = [self.condition3]

			headerDict['Cell Type'] = [self.detectionDict['cellType']]
			headerDict['Sex'] = [self.detectionDict['sex']]
			headerDict['Condition'] = [self.detectionDict['condition']]

			headerDict['Date Analyzed'] = [self.dateAnalyzed]
			headerDict['Detection Type'] = [self.detectionType]
			headerDict['dV/dt Threshold'] = [self.dvdtThreshold]
			#headerDict['mV Threshold'] = [self.mvThreshold] # abb 202012
			headerDict['Vm Threshold (mV)'] = [self.mvThreshold]
			headerDict['Median Filter (pnts)'] = [self.medianFilter]
			headerDict['Analysis Version'] = [sanpy.analysisVersion]
			headerDict['Interface Version'] = [sanpy.interfaceVersion]

			#headerDict['Analysis Start (sec)'] = [self.startSeconds]
			#headerDict['Analysis Stop (sec)'] = [self.stopSeconds]
			headerDict['Sweep Number'] = [self.currentSweep]
			headerDict['Number of Sweeps'] = [self.numSweeps]
			headerDict['Export Start (sec)'] = [float('%.2f'%(theMin))] # on export, x-axis of raw plot will be ouput
			headerDict['Export Stop (sec)'] = [float('%.2f'%(theMax))] # on export, x-axis of raw plot will be ouput
			headerDict['stats'] = []

			for idx, col in enumerate(cardiac_df):
				headerDict[col] = []

			# mean
			theMean = cardiac_df.mean() # skipna default is True
			theMean['errors'] = ''
			# sd
			theSD = cardiac_df.std() # skipna default is True
			theSD['errors'] = ''
			#se
			theSE = cardiac_df.sem() # skipna default is True
			theSE['errors'] = ''
			#n
			theN = cardiac_df.count() # skipna default is True
			theN['errors'] = ''

			statCols = ['mean', 'sd', 'se', 'n']
			for j, stat in enumerate(statCols):
				if j == 0:
					pass
				else:
					headerDict['file'].append('')
					#headerDict['Condition 1'].append('')
					#headerDict['Condition 2'].append('')
					#headerDict['Condition 3'].append('')
					headerDict['Cell Type'].append('')
					headerDict['Sex'].append('')
					headerDict['Condition'].append('')
					#
					headerDict['Date Analyzed'].append('')
					headerDict['Detection Type'].append('')
					headerDict['dV/dt Threshold'].append('')
					headerDict['Vm Threshold (mV)'].append('')
					headerDict['Median Filter (pnts)'].append('')
					headerDict['Analysis Version'].append('')
					headerDict['Interface Version'].append('')
					#headerDict['Analysis Start (sec)'].append('')
					#headerDict['Analysis Stop (sec)'].append('')
					headerDict['Sweep Number'].append('')
					headerDict['Number of Sweeps'].append('')
					headerDict['Export Start (sec)'].append('')
					headerDict['Export Stop (sec)'].append('')

				# a dictionary key for each stat
				headerDict['stats'].append(stat)
				for idx, col in enumerate(cardiac_df):
					#headerDict[col].append('')
					if stat == 'mean':
						headerDict[col].append(theMean[col])
					elif stat == 'sd':
						headerDict[col].append(theSD[col])
					elif stat == 'se':
						headerDict[col].append(theSE[col])
					elif stat == 'n':
						headerDict[col].append(theN[col])


			#print(headerDict)
			#for k,v in headerDict.items():
			#	print(k, v)

			# dict to pandas dataframe
			df = pd.DataFrame(headerDict).T
			# pandas dataframe to excel sheet 'header'
			df.to_excel(writer, sheet_name='summary')

			# set the column widths in excel sheet 'cardiac'
			columnWidth = 25
			worksheet = writer.sheets['summary']  # pull worksheet object
			for idx, col in enumerate(df):  # loop through all columns
				worksheet.set_column(idx, idx, columnWidth)  # set column width

			#
			# 'cardiac' sheet
			cardiac_df.to_excel(writer, sheet_name='cardiac')

			# set the column widths in excel sheet 'cardiac'
			columnWidth = 20
			worksheet = writer.sheets['cardiac']  # pull worksheet object
			for idx, col in enumerate(cardiac_df):  # loop through all columns
				worksheet.set_column(idx, idx, columnWidth)  # set column width


			#
			# entire (verbose) analysis to sheet 'bob'
			#df.to_excel(writer, sheet_name='bob')

			#
			# mean spike clip
			theseClips, theseClips_x, meanClip = self.getSpikeClips(theMin, theMax)
			try:
				first_X = theseClips_x[0] #- theseClips_x[0][0]
				#if verbose: print('    bAnalysis.saveReport() saving mean clip to sheet "Avg Spike" from', len(theseClips), 'clips')
				df = pd.DataFrame(meanClip, first_X)
				df.to_excel(writer, sheet_name='Avg Spike')
			except (IndexError) as e:
				print('warning: got bad spike clips in saveReport(). Usually happend when 1-2 spikes')
			#print('df:', df)

			writer.save()

		#
		# save a csv text file
		#
		analysisName = ''
		if alsoSaveTxt:
			# this also saves
			analysisName, df0 = self.getReportDf(theMin, theMax, savefile)

			#
			# save mean spike clip

			theseClips, theseClips_x, meanClip = self.getSpikeClips(theMin, theMax)
			if len(theseClips_x) == 0:
				pass
			else:
				first_X = theseClips_x[0] #- theseClips_x[0][0]
				first_X = np.array(first_X)
				first_X /= self.abf.dataPointsPerMs # pnts to ms
				#if verbose: print('    bAnalysis.saveReport() saving mean clip to sheet "Avg Spike" from', len(theseClips), 'clips')
				#dfClip = pd.DataFrame(meanClip, first_X)
				dfClip = pd.DataFrame.from_dict({
					'xMs': first_X,
					'yVm': meanClip
					})
				# load clip based on analysisname (with start/stop seconds)
				analysisname = df0['analysisname'].iloc[0] # name with start/stop seconds
				print('bAnalysis.saveReport() analysisname:', analysisname)
				#print('analysisname:', analysisname)
				clipFileName = analysisname + '_clip.csv'
				tmpPath, tmpFile = os.path.split(savefile)
				tmpPath = os.path.join(tmpPath, 'analysis')
				# dir is already created in getReportDf
				if not os.path.isdir(tmpPath):
					os.mkdir(tmpPath)
				clipSavePath = os.path.join(tmpPath, clipFileName)
				print('    clipSavePath:', clipSavePath)
				dfClip.to_csv(clipSavePath)
			#
			'''
			filePath, fileName = os.path.split(os.path.abspath(savefile))

			textFileBaseName, tmpExtension = os.path.splitext(savefile)
			textFilePath = os.path.join(filePath, textFileBaseName + '.txt')

			print('    saving text file:', textFilePath)

			# save header
			textFileHeader = OrderedDict()
			textFileHeader['file'] = self.file
			textFileHeader['condition1'] = self.condition1
			textFileHeader['condition2'] = self.condition2
			textFileHeader['condition3'] = self.condition3
			textFileHeader['dateAnalyzed'] = self.dateAnalyzed
			textFileHeader['detectionType'] = self.detectionType
			textFileHeader['dvdtThreshold'] = self.dvdtThreshold
			textFileHeader['mvThreshold'] = self.mvThreshold
			textFileHeader['medianFilter'] = self.medianFilter
			textFileHeader['startSeconds'] = '%.2f'%(theMin)
			textFileHeader['stopSeconds'] = '%.2f'%(theMax)
			#textFileHeader['startSeconds'] = self.startSeconds
			#textFileHeader['stopSeconds'] = self.stopSeconds
			textFileHeader['currentSweep'] = self.currentSweep
			textFileHeader['numSweeps'] = self.numSweeps
			#textFileHeader['theMin'] = theMin
			#textFileHeader['theMax'] = theMax

			headerStr = ''
			for k,v in textFileHeader.items():
				headerStr += k + '=' + str(v) + ';'
			headerStr += '\n'
			#print('headerStr:', headerStr)
			with open(textFilePath,'w') as f:
				f.write(headerStr)

			#print('Saving .txt file:', textFilePath)
			df = self.report(theMin, theMax)
			df.to_csv(textFilePath, sep=',', index_label='index', mode='a')
			'''
			theRet = df0
		#
		return analysisName, theRet

	def getReportDf(self, theMin, theMax, savefile):
		"""
		savefile: .xls file path
		"""
		filePath, fileName = os.path.split(os.path.abspath(savefile))

		# make an analysis folder
		filePath = os.path.join(filePath, 'analysis')
		if not os.path.isdir(filePath):
			print('    getReportDf() making output folder:', filePath)
			os.mkdir(filePath)

		textFileBaseName, tmpExtension = os.path.splitext(fileName)
		textFilePath = os.path.join(filePath, textFileBaseName + '.csv')

		# save header
		textFileHeader = OrderedDict()
		textFileHeader['file'] = self.file # this is actuall file path
		#textFileHeader['condition1'] = self.condition1
		#textFileHeader['condition2'] = self.condition2
		#textFileHeader['condition3'] = self.condition3
		textFileHeader['cellType'] = self.detectiondict['cellType']
		textFileHeader['sex'] = self.detectiondict['sex']
		textFileHeader['condition'] = self.detectiondict['condition']
		#
		textFileHeader['dateAnalyzed'] = self.dateAnalyzed
		textFileHeader['detectionType'] = self.detectionType
		textFileHeader['dvdtThreshold'] = self.dvdtThreshold
		textFileHeader['mvThreshold'] = self.mvThreshold
		textFileHeader['medianFilter'] = self.medianFilter
		textFileHeader['startSeconds'] = '%.2f'%(theMin)
		textFileHeader['stopSeconds'] = '%.2f'%(theMax)
		#textFileHeader['startSeconds'] = self.startSeconds
		#textFileHeader['stopSeconds'] = self.stopSeconds
		textFileHeader['currentSweep'] = self.currentSweep
		textFileHeader['numSweeps'] = self.numSweeps
		#textFileHeader['theMin'] = theMin
		#textFileHeader['theMax'] = theMax

		# 20210125, this is not needed, we are saviing pandas df below ???
		headerStr = ''
		for k,v in textFileHeader.items():
			headerStr += k + '=' + str(v) + ';'
		headerStr += '\n'
		#print('headerStr:', headerStr)
		with open(textFilePath,'w') as f:
			f.write(headerStr)

		#print('Saving .txt file:', textFilePath)
		df = self.report(theMin, theMax)

		# we need a column indicating (path), the original .abf file
		# along with (start,stop) which should make this analysis unique?
		minStr = '%.2f'%(theMin)
		maxStr = '%.2f'%(theMax)
		minStr = minStr.replace('.', '_')
		maxStr = maxStr.replace('.', '_')
		tmpPath, tmpFile = os.path.split(self.file)
		tmpFile, tmpExt = os.path.splitext(tmpFile)
		analysisName = tmpFile + '_s' + minStr + '_s' + maxStr
		print('    minStr:', minStr, 'maxStr:', maxStr, 'analysisName:', analysisName)
		df['analysisname'] = analysisName

		# should be filled in by self.report
		#df['Condition'] = 	df['condition1']
		#df['File Number'] = 	df['condition2']
		#df['Sex'] = 	df['condition3']
		#df['Region'] = 	df['condition4']
		df['filename'] = [os.path.splitext(os.path.split(x)[1])[0] for x in 	df['file'].tolist()]

		#
		print('    bAnalysis.getReportDf() saving text file:', textFilePath)
		#df.to_csv(textFilePath, sep=',', index_label='index', mode='a')
		df.to_csv(textFilePath, sep=',', index_label='index', mode='w')

		return analysisName, df

	#############################
	# utility functions
	#############################
	def pnt2Sec_(self, pnt):
		'''
		if pnt is None or math.isnan(pnt):
			return None
		'''

		# debug
		#pntInSeconds = pnt / self.abf.dataPointsPerMs / 1000
		#print(f'pnt2Sec_() pnt:{pnt}, self.abf.dataPointsPerMs:{self.abf.dataPointsPerMs}, pntInSeconds:{pntInSeconds}')

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

	def NormalizeData(self, data):
		return (data - np.min(data)) / (np.max(data) - np.min(data))

def test_load_abf():
	path = '/Users/cudmore/data/dual-lcr/20210115/data/21115002.abf'
	ba = bAnalysis(path)

	dvdtThreshold = 30
	mvThreshold = -20
	halfWidthWindow_ms = 60 # was 20
	ba.spikeDetect(dvdtThreshold=dvdtThreshold, mvThreshold=mvThreshold,
		halfWidthWindow_ms=halfWidthWindow_ms
		)
		#avgWindow_ms=avgWindow_ms,
		#window_ms=window_ms,
		#peakWindow_ms=peakWindow_ms,
		#refractory_ms=refractory_ms,
		#dvdt_percentOfMax=dvdt_percentOfMax)

	test_plot(ba)

	return ba

def test_load_tif(path):
	"""
	working on spike detection from sum of intensities along a line scan
	see: example/lcr-analysis
	"""

	# text file with 2x columns (seconds, vm)

	#path = '/Users/Cudmore/Desktop/caInt.csv'

	#path = '/Users/cudmore/data/dual-lcr/20210115/data/20210115__0001.tif'

	ba = bAnalysis(path)
	ba.getDerivative()

	#print('ba.abf.sweepX:', len(ba.abf.sweepX))
	#print('ba.abf.sweepY:', len(ba.abf.sweepY))

	#print('ba.abf.sweepX:', ba.abf.sweepX)
	#print('ba.abf.sweepY:', ba.abf.sweepY)

	# Ca recording is ~40 times slower than e-phys at 10 kHz
	mvThreshold = 0.5
	dvdtThreshold = 0.01
	refractory_ms = 60 # was 20 ms
	avgWindow_ms=60 # pre-roll to find eal threshold crossing
		# was 5, in detect I am using avgWindow_ms/2 ???
	window_ms = 20 # was 2
	peakWindow_ms = 70 # 20 gives us 5, was 10
	dvdt_percentOfMax = 0.2 # was 0.1
	halfWidthWindow_ms = 60 # was 20
	ba.spikeDetect(dvdtThreshold=dvdtThreshold, mvThreshold=mvThreshold,
		avgWindow_ms=avgWindow_ms,
		window_ms=window_ms,
		peakWindow_ms=peakWindow_ms,
		refractory_ms=refractory_ms,
		dvdt_percentOfMax=dvdt_percentOfMax,
		halfWidthWindow_ms=halfWidthWindow_ms
		)

	for k,v in ba.spikeDict[0].items():
		print('  ', k, ':', v)

	test_plot(ba)

	return ba

def test_plot(ba, firstSampleTime=0):
	#firstSampleTime = ba.abf.sweepX[0] # is not 0 for 'wait for trigger' FV3000

	# plot
	fig, axs = plt.subplots(2, 1, sharex=True)

	#
	# dv/dt
	xDvDt = ba.abf.sweepX + firstSampleTime
	yDvDt = ba.abf.filteredDeriv + firstSampleTime
	axs[0].plot(xDvDt, yDvDt, 'k')

	# thresholdVal_dvdt
	xThresh = [x['thresholdSec'] + firstSampleTime for x in ba.spikeDict]
	yThresh = [x['thresholdVal_dvdt'] for x in ba.spikeDict]
	axs[0].plot(xThresh, yThresh, 'or')

	axs[0].spines['right'].set_visible(False)
	axs[0].spines['top'].set_visible(False)

	#
	# vm with detection params
	axs[1].plot(ba.abf.sweepX, ba.abf.sweepY, 'k-', lw=0.5)

	xThresh = [x['thresholdSec'] + firstSampleTime for x in ba.spikeDict]
	yThresh = [x['thresholdVal'] for x in ba.spikeDict]
	axs[1].plot(xThresh, yThresh, 'or')

	xPeak = [x['peakSec'] + firstSampleTime for x in ba.spikeDict]
	yPeak = [x['peakVal'] for x in ba.spikeDict]
	axs[1].plot(xPeak, yPeak, 'ob')

	sweepX = ba.abf.sweepX + firstSampleTime

	for idx, spikeDict in enumerate(ba.spikeDict):
		#
		# plot all widths
		#print('plotting width for spike', idx)
		for j,widthDict in enumerate(spikeDict['widths']):
			#for k,v in widthDict.items():
			#	print('  ', k, ':', v)
			#print('j:', j)
			if widthDict['risingPnt'] is None:
				#print('  -->> no half width')
				continue

			risingPntX = sweepX[widthDict['risingPnt']]
			# y value of rising pnt is y value of falling pnt
			#risingPntY = ba.abf.sweepY[widthDict['risingPnt']]
			risingPntY = ba.abf.sweepY[widthDict['fallingPnt']]
			fallingPntX = sweepX[widthDict['fallingPnt']]
			fallingPntY = ba.abf.sweepY[widthDict['fallingPnt']]
			fallingPnt = widthDict['fallingPnt']
			# plotting y-value of rising to match y-value of falling
			#ax.plot(ba.abf.sweepX[widthDict['risingPnt']], ba.abf.sweepY[widthDict['risingPnt']], 'ob')
			# plot as pnts
			#axs[1].plot(ba.abf.sweepX[widthDict['risingPnt']], ba.abf.sweepY[widthDict['fallingPnt']], '-b')
			#axs[1].plot(ba.abf.sweepX[widthDict['fallingPnt']], ba.abf.sweepY[widthDict['fallingPnt']], '-b')
			# line between rising and falling is ([x1, y1], [x2, y2])
			axs[1].plot([risingPntX, fallingPntX], [risingPntY, fallingPntY], color='b', linestyle='-', linewidth=2)

	axs[1].spines['right'].set_visible(False)
	axs[1].spines['top'].set_visible(False)

	#
	#plt.show()

def lcrDualAnalysis():
	"""
	for 2x files, line-scan and e-phys
	plot spike time delay of ca imaging
	"""
	fileIndex = 3
	dataList[fileIndex]

	ba0 = test_load_tif(path) # image
	ba1 = test_load_abf() # recording

	# now need to get this from pClamp abf !!!
	#firstSampleTime = ba0.abf.sweepX[0] # is not 0 for 'wait for trigger' FV3000
	firstSampleTime = ba1.abf.tagTimesSec[0]
	print('firstSampleTime:', firstSampleTime)

	# for each spike in e-phys, match it with a spike in imaging
	# e-phys is shorter, fewer spikes
	numSpikes = ba1.numSpikes
	print('num spikes in recording:', numSpikes)

	thresholdSec0, peakSec0 = ba0.getStat('thresholdSec', 'peakSec')
	thresholdSec1, peakSec1 = ba1.getStat('thresholdSec', 'peakSec')

	ba1_width50, throwOut = ba1.getStat('widths_50', 'peakSec')

	# todo: add an option in bAnalysis.getStat()
	thresholdSec0 = [x + firstSampleTime for x in thresholdSec0]
	peakSec0 = [x + firstSampleTime for x in peakSec0]

	# assuming spike-detection is clean
	# truncate imaging (it is longer than e-phys)
	thresholdSec0 = thresholdSec0[0:numSpikes] # second value/max is NOT INCLUSIVE
	peakSec0 = peakSec0[0:numSpikes]

	numSubplots = 2
	fig, axs = plt.subplots(numSubplots, 1, sharex=False)

	# threshold in image starts about 20 ms after Vm
	axs[0].plot(thresholdSec1, peakSec0, 'ok')
	#axs[0].plot(thresholdSec1, 'ok')

	# draw diagonal
	axs[0].plot([0, 1], [0, 1], transform=axs[0].transAxes)

	axs[0].set_xlabel('thresholdSec1')
	axs[0].set_ylabel('peakSec0')

	#axs[1].plot(thresholdSec1, peakSec0, 'ok')

	# time to peak in image wrt AP threshold time
	caTimeToPeak = []
	for idx, thresholdSec in enumerate(thresholdSec1):
		timeToPeak = peakSec0[idx] - thresholdSec
		#print('thresholdSec:', thresholdSec, 'peakSec0:', peakSec0[idx], 'timeToPeak:', timeToPeak)
		caTimeToPeak.append(timeToPeak)

	print('caTimeToPeak:', caTimeToPeak)

	axs[1].plot(ba1_width50, caTimeToPeak, 'ok')

	# draw diagonal
	#axs[1].plot([0, 1], [0, 1], transform=axs[1].transAxes)

	axs[1].set_xlabel('ba1_width50')
	axs[1].set_ylabel('caTimeToPeak')

	#
	plt.show()

if __name__ == '__main__':
	import matplotlib.pyplot as plt

	'''
	if 0:
		print('running bAnalysis __main__')
		ba = bAnalysis('../data/19114001.abf')
		print(ba.dataPointsPerMs)
	'''

	# this is to load/analyze/plot the sum of a number of Ca imaging line scans
	# e.g. lcr
	if 0:
		ba0 = test_load_tif(path) # this can load a line scan tif
		# todo: add title
		test_plot(ba0)

		ba1 = test_load_abf()
		test_plot(ba1)

		#
		plt.show()

	if 0:
		lcrDualAnalysis()

	path = '/Users/cudmore/Sites/SanPy/examples/dual-analysis/dual-data/20210129/2021_01_29_0007.abf'
	ba = bAnalysis(path)
	dDict = ba.getDefaultDetection()
	#dDict['dvdtThreshold'] = None # detect using just Vm
	print('dDict:', dDict)
	ba.spikeDetect(dDict)

	ba.errorReport()
