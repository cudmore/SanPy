'''
Author: Robert H Cudmore
Date: 20190225
'''

import os, math, time

import collections

import numpy as np
import pandas as pd

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

		self.spikeDict = [] # a list of dict

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
	def spikeDetect0(self, dVthresholdPos=100, medianFilter=0):
		# check dvdt to select threshold for an action-potential
		if medianFilter > 0:
			vm = scipy.signal.medfilt(self.abf.sweepY,medianFilter)
		else:
			vm = self.abf.sweepY

		sweepDeriv = np.diff(vm)

		# scale it to V/S (mV/ms)
		sweepDeriv = sweepDeriv * self.abf.dataRate / 1000

		# add an initial point so it is the same length as raw data in abf.sweepY
		sweepDeriv=np.concatenate(([0],sweepDeriv))

		#spikeTimes = _where_cross(sweepDeriv,dVthresholdPos)
		Is=np.where(sweepDeriv>dVthresholdPos)[0]
		Is=np.concatenate(([0],Is))
		Ds=Is[:-1]-Is[1:]+1
		spikeTimes0 = Is[np.where(Ds)[0]+1]

		#
		# if there are doubles, throw-out the second one
		refractory_ms = 10 # remove spike [i] if it occurs within refractory_ms of spike [i-1]
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

		#
		# make sure all spikes are on upslope

		#
		# todo
		# for each threshold crossing, search backwards for 10% of maximum (about 10 ms)
		window_ms = 2
		window_pnts = window_ms * self.dataPointsPerMs
		spikeTimes1 = []
		for i, spikeTime in enumerate(spikeTimes0):
			# get max in derivative
			preDerivClip = sweepDeriv[spikeTime-window_pnts:spikeTime] # backwards
			#preDerivClip = np.flip(preDerivClip)
			peakPnt = np.argmax(preDerivClip)
			peakPnt += spikeTime-window_pnts
			peakVal = sweepDeriv[peakPnt]

			# look for 10% of max
			try:
				tenPercentMax = peakVal * 0.15
				preDerivClip = np.flip(preDerivClip) # backwards
				threshPnt2 = np.where(preDerivClip<tenPercentMax)[0][0]
				threshPnt2 = (spikeTime) - threshPnt2
				print('i:', i, 'spikeTime:', spikeTime, 'peakPnt:', peakPnt, 'threshPnt2:', threshPnt2)
				spikeTimes1.append(threshPnt2)
			except (IndexError) as e:
				print('IndexError spike', i, spikeTime)
				spikeTimes1.append(spikeTime)

		return spikeTimes1, vm, sweepDeriv

	def spikeDetect(self, dVthresholdPos=100, medianFilter=0, halfHeights=[20, 50, 80]):
		'''
		spike detect the current sweep and put results into spikeTime[currentSweep]

		todo: remember values of halfHeights
		'''

		startSeconds = time.time()

		# spike detect
		self.spikeTimes, vm, dvdt = self.spikeDetect0(dVthresholdPos=dVthresholdPos, medianFilter=medianFilter)

		#
		# look in a window after each threshold crossing to get AP peak
		# get minima before/after spike
		peakWindow_ms = 10
		peakWindow_pnts = self.abf.dataPointsPerMs * peakWindow_ms
		avgWindow_ms = 5 # we find the min/max before/after (between spikes) and then take an average around this value
		avgWindow_pnts = avgWindow_ms * self.abf.dataPointsPerMs
		avgWindow_pnts = math.floor(avgWindow_pnts/2)
		for i, spikeTime in enumerate(self.spikeTimes):
			peakPnt = np.argmax(vm[spikeTime:spikeTime+peakWindow_pnts])
			peakPnt += spikeTime
			peakVal = np.max(vm[spikeTime:spikeTime+peakWindow_pnts])

			spikeDict = collections.OrderedDict() # use OrderedDict so Pandas output is in the correct order
			spikeDict['file'] = self.file
			spikeDict['spikeNumber'] = i
			spikeDict['thresholdPnt'] = spikeTime
			spikeDict['thresholdSec'] = (spikeTime / self.abf.dataPointsPerMs) / 1000
			spikeDict['peakPnt'] = peakPnt
			spikeDict['peakSec'] = (peakPnt / self.abf.dataPointsPerMs) / 1000
			spikeDict['peakVal'] = peakVal

			self.spikeDict.append(spikeDict)

			# get pre/post spike minima
			self.spikeDict[i]['preMinPnt'] = None
			self.spikeDict[i]['preMinVal'] = None
			self.spikeDict[i]['postMinPnt'] = None
			self.spikeDict[i]['postMinVal'] = None

			self.spikeDict[i]['preLinearFitPnt0'] = None
			self.spikeDict[i]['preLinearFitPnt1'] = None
			self.spikeDict[i]['preLinearFitVal0'] = None
			self.spikeDict[i]['preLinearFitVal1'] = None

			self.spikeDict[i]['preSpike_dvdt_max_pnt'] = None
			self.spikeDict[i]['preSpike_dvdt_max_val'] = None
			self.spikeDict[i]['postSpike_dvdt_min_pnt'] = None
			self.spikeDict[i]['postSpike_dvdt_min_val'] = None

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
				#tmp = np.where(preRange<preMinVal)
				preMinPnt2 = np.where(preRange<preMinVal)[0][0]
				preMinPnt = self.spikeTimes[i] - preMinPnt2

				#
				# linear fit on 10% - 50% of the time from preMinPnt to self.spikeTimes[i]
				startLinearFit = 0.1 # percent of time between pre spike min and AP peak
				stopLinearFit = 0.5 # percent of time between pre spike min and AP peak
				timeInterval_pnts = self.spikeTimes[i] - preMinPnt
				#print('   timeInterval_pnts:', timeInterval_pnts)
				timeInterval_pnts = math.floor(timeInterval_pnts)
				#print('i:', i, 'timeInterval_pnts:', timeInterval_pnts)
				preLinearFitPnt0 = preMinPnt + math.floor(timeInterval_pnts * startLinearFit)
				preLinearFitPnt1 = preMinPnt + math.floor(timeInterval_pnts * stopLinearFit)
				preLinearFitVal0 = vm[preLinearFitPnt0]
				preLinearFitVal1 = vm[preLinearFitPnt1]

				#
				# maxima in dv/dt before spike
				preRange = dvdt[preMinPnt:self.spikeTimes[i]]
				preSpike_dvdt_max_pnt = np.argmax(preRange)
				preSpike_dvdt_max_pnt += preMinPnt
				#print('i:', i, 'preSpike_dvdt_max_pnt:', preSpike_dvdt_max_pnt)
				self.spikeDict[i]['preSpike_dvdt_max_pnt'] = preSpike_dvdt_max_pnt
				self.spikeDict[i]['preSpike_dvdt_max_val'] = vm[preSpike_dvdt_max_pnt]

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
					print('error postMinPnt')

				#
				# minima in dv/dt after spike
				#postRange = dvdt[self.spikeTimes[i]:postMinPnt]
				postSpike_ms = self.spikeTimes[i] + 10
				postRange = dvdt[self.spikeTimes[i]:self.spikeTimes[i]+postSpike_ms] # fixed window after spike
				postSpike_dvdt_min_pnt = np.argmin(postRange)
				postSpike_dvdt_min_pnt += self.spikeTimes[i]
				#print('i:', i, 'postSpike_dvdt_min_pnt:', postSpike_dvdt_min_pnt)
				self.spikeDict[i]['postSpike_dvdt_min_pnt'] = postSpike_dvdt_min_pnt
				self.spikeDict[i]['postSpike_dvdt_min_val'] = vm[postSpike_dvdt_min_pnt]

				self.spikeDict[i]['preMinPnt'] = preMinPnt
				self.spikeDict[i]['preMinVal'] = preMinVal
				self.spikeDict[i]['postMinPnt'] = postMinPnt
				self.spikeDict[i]['postMinVal'] = postMinVal
				# linear fit before spike
				self.spikeDict[i]['preLinearFitPnt0'] = preLinearFitPnt0
				self.spikeDict[i]['preLinearFitPnt1'] = preLinearFitPnt1
				self.spikeDict[i]['preLinearFitVal0'] = preLinearFitVal0
				self.spikeDict[i]['preLinearFitVal1'] = preLinearFitVal1

				# get 1/2 height (actually, any number of height measurements)
				# action potential duration using peak and post min
				self.spikeDict[i]['widths'] = []
				for j, halfHeight in enumerate(halfHeights):
					thisVm = postMinVal + (peakVal - postMinVal) * (halfHeight * 0.01)
					#print('halfHeight:', halfHeight, 'thisVm:', thisVm)
					# search from previous min to peak
					'''
					# pre/rising
					preRange = vm[preMinPnt:peakPnt]
					risingPnt = np.where(preRange>thisVm)[0][0] # greater than
					risingPnt += preMinPnt
					risingVal = vm[risingPnt]
					'''
					# post/falling
					widthDict = {
						'risingPnt': None,
						'risingVal': None,
						'fallingPnt': None,
						'fallingVal': None,
						'widthPnts': None,
						'widthMs': None
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
						widthDict = {
							'risingPnt': risingPnt,
							'risingVal': risingVal,
							'fallingPnt': fallingPnt,
							'fallingVal': fallingVal,
							'widthPnts': widthPnts,
							'widthMs': widthPnts / self.abf.dataPointsPerMs
						}
					except (IndexError) as e:
						print('error: spike', i, 'half height', halfHeight)
						#print(e)
					self.spikeDict[i]['widths'].append(widthDict)


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

		self.spikeClips = []
		for spikeTime in self.spikeTimes:
			currentClip = vm[spikeTime-halfClipWidth_pnts:spikeTime+halfClipWidth_pnts]
			self.spikeClips.append(currentClip)

		stopSeconds = time.time()
		print('bAnalysis.spikeDetect() for file', self.file, 'detected', len(self.spikeTimes), 'spikes in', round(stopSeconds-startSeconds,2), 'seconds')

	@property
	def numSpikes(self):
		'''
		Returns the number of spikes, assumes self.spikeDetect(dVthreshold)
		'''
		return len(self.spikeTimes)

	#############################
	# plot functions
	#############################
	def plotDeriv(self, medianFilter=0, dVthresholdPos=100):
		'''
		Plot both Vm and the derivative of Vm (dV/dt).

		Parameters:
			medianFilter:	0 is no filtering
							Integer greater than 0 specifies the number of points
		'''

		spikeTimes, vm, sweepDeriv = self.spikeDetect0(dVthresholdPos=dVthresholdPos, medianFilter=medianFilter)

		if medianFilter > 0:
			yAxisLabel = 'filtered '
		else:
			yAxisLabel = ''

		sweepDeriv = np.diff(vm) # first derivative

		#sweepDeriv = scipy.signal.medfilt(sweepDeriv)

		sweepDeriv = np.concatenate(([0],sweepDeriv))

		# add an initial point so it is the same length as raw data in abf.sweepY
		sweepDeriv2 = np.diff(sweepDeriv) # second derivative

		# scale it to V/S (mV/ms)
		sweepDeriv = sweepDeriv * self.abf.dataRate / 1000
		#sweepDeriv2 = sweepDeriv2 * self.abf.dataRate / 1000

		# add an initial point so it is the same length as raw data in abf.sweepY
		sweepDeriv2 = np.concatenate(([0],sweepDeriv2))

		grid = plt.GridSpec(2, 1, wspace=0.2, hspace=0.4)

		fig = plt.figure(figsize=(10, 8))
		ax1 = fig.add_subplot(grid[0,0])
		ax2 = fig.add_subplot(grid[1,0], sharex=ax1)
		#ax3 = fig.add_subplot(grid[2,0], sharex=ax1)


		ax1.plot(self.abf.sweepX, vm)
		ax1.set_ylabel(yAxisLabel + 'Vm (mV)')

		ax2.plot(self.abf.sweepX, sweepDeriv)
		ax2.set_ylabel('dV/dt')
		ax2.set_xlabel('Seconds')

		#ax3.plot(self.abf.sweepX, sweepDeriv2)
		#ax3.set_ylabel('dV/dt (2)')

		# spike detect and append
		ax1.plot(self.abf.sweepX[spikeTimes], vm[spikeTimes], 'or')
		ax2.plot(self.abf.sweepX[spikeTimes], sweepDeriv[spikeTimes], 'or')

		print('detected', len(spikeTimes), 'spikes')

		return fig

	def plotSpikes(self, all=True, oneSpikeNumber=None, ax=None):
		'''
		Plot Vm with all spike analysis
		'''
		if ax is None:
			grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

			fig = plt.figure(figsize=(10, 8))
			ax = fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		# plot vm
		ax.plot(self.abf.sweepX, self.abf.sweepY, 'k')

		# plot all spike times (threshold crossings)
		"""
		for spikeTime in self.spikeTimes:
			ax.plot(self.abf.sweepX[spikeTime], self.abf.sweepY[spikeTime], 'xg')
		"""
		ax.plot(self.abf.sweepX[self.spikeTimes], self.abf.sweepY[self.spikeTimes], 'pg')

		# plot the peak
		peakPntList = [spikeDict['peakPnt'] for spikeDict in self.spikeDict]
		ax.plot(self.abf.sweepX[peakPntList], self.abf.sweepY[peakPntList], 'or')

		# plot the pre min (avg)
		preMinPntList = [spikeDict['preMinPnt'] for spikeDict in self.spikeDict if spikeDict['preMinPnt'] is not None]
		preMinValList = [spikeDict['preMinVal'] for spikeDict in self.spikeDict if spikeDict['preMinVal'] is not None]
		ax.plot(self.abf.sweepX[preMinPntList], preMinValList, 'or')

		# plot the post min (avg)
		postMinPntList = [spikeDict['postMinPnt'] for spikeDict in self.spikeDict if spikeDict['postMinPnt'] is not None]
		postMinValList = [spikeDict['postMinVal'] for spikeDict in self.spikeDict if spikeDict['postMinVal'] is not None]
		ax.plot(self.abf.sweepX[postMinPntList], postMinValList, 'og')

		#
		# plot the pre spike slope
		preLinearFitPnt0List = [spikeDict['preLinearFitPnt0'] for spikeDict in self.spikeDict if spikeDict['preLinearFitPnt0'] is not None]
		preLinearFitVal0List = [spikeDict['preLinearFitVal0'] for spikeDict in self.spikeDict if spikeDict['preLinearFitVal0'] is not None]
		ax.plot(self.abf.sweepX[preLinearFitPnt0List], preLinearFitVal0List, 'oy')

		preLinearFitPnt1List = [spikeDict['preLinearFitPnt1'] for spikeDict in self.spikeDict if spikeDict['preLinearFitPnt1'] is not None]
		preLinearFitVal1List = [spikeDict['preLinearFitVal1'] for spikeDict in self.spikeDict if spikeDict['preLinearFitVal1'] is not None]
		ax.plot(self.abf.sweepX[preLinearFitPnt1List], preLinearFitVal1List, 'og')


		#
		# plot the maximum upswing of a spike
		preSpike_dvdt_max_pnt_list = [spikeDict['preSpike_dvdt_max_pnt'] for spikeDict in self.spikeDict if spikeDict['preSpike_dvdt_max_pnt'] is not None]
		preSpike_dvdt_max_val_list = [spikeDict['preSpike_dvdt_max_val'] for spikeDict in self.spikeDict if spikeDict['preSpike_dvdt_max_val'] is not None]
		ax.plot(self.abf.sweepX[preSpike_dvdt_max_pnt_list], preSpike_dvdt_max_val_list, 'xr')

		#
		# plot the minima downswing of a spike
		postSpike_dvdt_min_pnt_list = [spikeDict['postSpike_dvdt_min_pnt'] for spikeDict in self.spikeDict if spikeDict['postSpike_dvdt_min_pnt'] is not None]
		postSpike_dvdt_min_val_list = [spikeDict['postSpike_dvdt_min_val'] for spikeDict in self.spikeDict if spikeDict['postSpike_dvdt_min_val'] is not None]
		ax.plot(self.abf.sweepX[postSpike_dvdt_min_pnt_list], postSpike_dvdt_min_val_list, 'xg')

		for i,spikeDict in enumerate(self.spikeDict):
			#ax.plot(self.abf.sweepX[spikeDict['peakPnt']], self.abf.sweepY[spikeDict['peakPnt']], 'or')
			if i==0 or i==len(self.spikeTimes)-1:
				continue

			#ax.plot(self.abf.sweepX[spikeDict['preMinPnt']], spikeDict['preMinVal'], 'og')

			#
			# line for pre spike slope
			ax.plot([self.abf.sweepX[spikeDict['preLinearFitPnt0']], self.abf.sweepX[spikeDict['preLinearFitPnt1']]], [spikeDict['preLinearFitVal0'], spikeDict['preLinearFitVal1']], color='b', linestyle='-', linewidth=2)

			#
			# plot all widths
			for j,widthDict in enumerate(spikeDict['widths']):
				#print('j:', j)
				risingPntX = self.abf.sweepX[widthDict['risingPnt']]
				# y value of rising pnt is y value of falling pnt
				#risingPntY = self.abf.sweepY[widthDict['risingPnt']]
				risingPntY = self.abf.sweepY[widthDict['fallingPnt']]
				fallingPntX = self.abf.sweepX[widthDict['fallingPnt']]
				fallingPntY = self.abf.sweepY[widthDict['fallingPnt']]
				fallingPnt = widthDict['fallingPnt']
				# plotting y-value of rising to match y-value of falling
				#ax.plot(self.abf.sweepX[widthDict['risingPnt']], self.abf.sweepY[widthDict['risingPnt']], 'ob')
				ax.plot(self.abf.sweepX[widthDict['risingPnt']], self.abf.sweepY[widthDict['fallingPnt']], 'ob')
				ax.plot(self.abf.sweepX[widthDict['fallingPnt']], self.abf.sweepY[widthDict['fallingPnt']], 'ob')
				# line between rising and falling is ([x1, y1], [x2, y2])
				ax.plot([risingPntX, fallingPntX], [risingPntY, fallingPntY], color='b', linestyle='-', linewidth=2)

		#
		# plot one spike time as a yellow circle
		line = None
		if oneSpikeNumber is not None:
			oneSpikeTime = self.spikeTimes[oneSpikeNumber]
			line, = ax.plot(self.abf.sweepX[oneSpikeTime], self.abf.sweepY[oneSpikeTime], 'oy')

		ax.set_ylabel('Vm (mV)')
		ax.set_xlabel('Time (sec)')

		return line

	def plotTimeSeries(self, stat, halfWidthIdx=0, ax=None):
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
		for i, spike in enumerate(self.spikeDict):
			if i==0 or i==len(self.spikeTimes)-1:
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

	def plotISI(self, ax=None):
		""" Plot the inter-spike-interval (sec) between each spike threshold"""
		#
		# pull
		spikeTimes_sec = [x/self.abf.dataPointsPerMs/1000 for x in self.spikeTimes]
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

		#
		# plot current clip
		line = None
		if oneSpikeNumber is not None:
			try:
				line, = ax.plot(self.spikeClips_x, self.spikeClips[oneSpikeNumber], 'y')
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
		line, = ax.plot(filteredClip, dvdt, 'y')

		ax.set_ylabel('filtered dV/dt')
		ax.set_xlabel('filtered Vm (mV)')

		return line

	############################################################
	# output results
	############################################################
	def report(self):
		df = pd.DataFrame(self.spikeDict)
		# limit columns
		df = df[['file', 'spikeNumber', 'thresholdSec', 'peakSec', 'preMinVal', 'postMinVal', 'widths']]
		return df

	############################################################
	# utility
	############################################################
	def __str__(self):
		retStr = 'file: ' + self.file + '\n' + str(self.abf)
		return retStr

if __name__ == '__main__':
	ba = bAnalysis('../data/19114001.abf')
	print(ba.dataPointsPerMs)
