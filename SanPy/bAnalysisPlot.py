'''
Robert Cudmore
20190328

Helper class to plot results of bAnalysis object
'''

import numpy as np

import scipy.signal

import matplotlib.pyplot as plt

class bPlot:
	def __init__(self, ba=None):
		"""
		ba: bAnalysis object
		"""
		self.ba = ba
	
	#############################
	# plot functions
	#############################
	def plotDeriv(ba, fig=None):
		'''
		Plot both Vm and the derivative of Vm (dV/dt).

		Parameters:
			medianFilter:	0 is no filtering
							Integer greater than 0 specifies the number of points
		'''

		#spikeTimes, thresholdTimes, vm, sweepDeriv = self.spikeDetect0(dVthresholdPos=dVthresholdPos, medianFilter=medianFilter)

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

	def plotRaw(ba, ax=None):
		if ax is None:
			grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

			fig = plt.figure(figsize=(10, 8))
			ax = fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		ax.plot(ba.abf.sweepX, ba.abf.sweepY, 'k')

		ax.set_ylabel('Vm (mV)')
		ax.set_xlabel('Time (sec)')
	
	def plotSpikes(ba, all=True, oneSpikeNumber=None, ax=None):
		'''
		Plot Vm with all spike analysis
		'''
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

		# plot the pre min (avg)
		'''
		preMinPntList = [spikeDict['preMinPnt'] for spikeDict in ba.spikeDict if spikeDict['preMinPnt'] is not None]
		preMinValList = [spikeDict['preMinVal'] for spikeDict in ba.spikeDict if spikeDict['preMinVal'] is not None]
		ax.plot(ba.abf.sweepX[preMinPntList], preMinValList, 'or')
		'''
		xPlot, yPlot = ba.getStat('preMinPnt', 'preMinVal', xToSec=True)
		ax.plot(xPlot, yPlot, 'og')

		'''
		# plot the post min (avg)
		postMinPntList = [spikeDict['postMinPnt'] for spikeDict in ba.spikeDict if spikeDict['postMinPnt'] is not None]
		postMinValList = [spikeDict['postMinVal'] for spikeDict in ba.spikeDict if spikeDict['postMinVal'] is not None]
		ax.plot(ba.abf.sweepX[postMinPntList], postMinValList, 'og')
		'''
		xPlot, yPlot = ba.getStat('postMinPnt', 'postMinVal', xToSec=True)
		ax.plot(xPlot, yPlot, 'or')

		'''
		#
		# plot the pre spike slope
		preLinearFitPnt0List = [spikeDict['preLinearFitPnt0'] for spikeDict in ba.spikeDict if spikeDict['preLinearFitPnt0'] is not None]
		preLinearFitVal0List = [spikeDict['preLinearFitVal0'] for spikeDict in ba.spikeDict if spikeDict['preLinearFitVal0'] is not None]
		ax.plot(ba.abf.sweepX[preLinearFitPnt0List], preLinearFitVal0List, 'oy')

		preLinearFitPnt1List = [spikeDict['preLinearFitPnt1'] for spikeDict in ba.spikeDict if spikeDict['preLinearFitPnt1'] is not None]
		preLinearFitVal1List = [spikeDict['preLinearFitVal1'] for spikeDict in ba.spikeDict if spikeDict['preLinearFitVal1'] is not None]
		ax.plot(ba.abf.sweepX[preLinearFitPnt1List], preLinearFitVal1List, 'og')


		#
		# plot the maximum upswing of a spike
		preSpike_dvdt_max_pnt_list = [spikeDict['preSpike_dvdt_max_pnt'] for spikeDict in ba.spikeDict if spikeDict['preSpike_dvdt_max_pnt'] is not None]
		preSpike_dvdt_max_val_list = [spikeDict['preSpike_dvdt_max_val'] for spikeDict in ba.spikeDict if spikeDict['preSpike_dvdt_max_val'] is not None]
		ax.plot(ba.abf.sweepX[preSpike_dvdt_max_pnt_list], preSpike_dvdt_max_val_list, 'xr')

		#
		# plot the minima downswing of a spike
		postSpike_dvdt_min_pnt_list = [spikeDict['postSpike_dvdt_min_pnt'] for spikeDict in ba.spikeDict if spikeDict['postSpike_dvdt_min_pnt'] is not None]
		postSpike_dvdt_min_val_list = [spikeDict['postSpike_dvdt_min_val'] for spikeDict in ba.spikeDict if spikeDict['postSpike_dvdt_min_val'] is not None]
		ax.plot(ba.abf.sweepX[postSpike_dvdt_min_pnt_list], postSpike_dvdt_min_val_list, 'xg')

		for i,spikeDict in enumerate(ba.spikeDict):
			#ax.plot(ba.abf.sweepX[spikeDict['peakPnt']], ba.abf.sweepY[spikeDict['peakPnt']], 'or')
			if i==0 or i==len(ba.spikeTimes)-1:
				continue

			#ax.plot(ba.abf.sweepX[spikeDict['preMinPnt']], spikeDict['preMinVal'], 'og')

			#
			# line for pre spike slope
			ax.plot([ba.abf.sweepX[spikeDict['preLinearFitPnt0']], ba.abf.sweepX[spikeDict['preLinearFitPnt1']]], [spikeDict['preLinearFitVal0'], spikeDict['preLinearFitVal1']], color='b', linestyle='-', linewidth=2)

			#
			# plot all widths
			for j,widthDict in enumerate(spikeDict['widths']):
				#print('j:', j)
				risingPntX = ba.abf.sweepX[widthDict['risingPnt']]
				# y value of rising pnt is y value of falling pnt
				#risingPntY = ba.abf.sweepY[widthDict['risingPnt']]
				risingPntY = ba.abf.sweepY[widthDict['fallingPnt']]
				fallingPntX = ba.abf.sweepX[widthDict['fallingPnt']]
				fallingPntY = ba.abf.sweepY[widthDict['fallingPnt']]
				fallingPnt = widthDict['fallingPnt']
				# plotting y-value of rising to match y-value of falling
				#ax.plot(ba.abf.sweepX[widthDict['risingPnt']], ba.abf.sweepY[widthDict['risingPnt']], 'ob')
				ax.plot(ba.abf.sweepX[widthDict['risingPnt']], ba.abf.sweepY[widthDict['fallingPnt']], 'ob')
				ax.plot(ba.abf.sweepX[widthDict['fallingPnt']], ba.abf.sweepY[widthDict['fallingPnt']], 'ob')
				# line between rising and falling is ([x1, y1], [x2, y2])
				ax.plot([risingPntX, fallingPntX], [risingPntY, fallingPntY], color='b', linestyle='-', linewidth=2)
		'''
		
		#
		# plot one spike time as a yellow circle
		line = None
		if oneSpikeNumber is not None:
			oneSpikeTime = ba.spikeTimes[oneSpikeNumber]
			line, = ax.plot(ba.abf.sweepX[oneSpikeTime], ba.abf.sweepY[oneSpikeTime], 'oy')

		ax.set_ylabel('Vm (mV)')
		ax.set_xlabel('Time (sec)')

		return line

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
				print('exception in bAnalysisPlot.plotClips() while plotting clips', i)

		#
		# plot current clip
		line = None
		if oneSpikeNumber is not None:
			try:
				line, = ax.plot(ba.spikeClips_x, ba.spikeClips[oneSpikeNumber], 'y')
			except (ValueError) as e:
				print('exception in bAnalysisPlot.plotClips() while plotting oneSpikeNumber', oneSpikeNumber)

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
