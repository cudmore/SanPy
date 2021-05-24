'''
Robert Cudmore
20190328

Helper class to plot results of bAnalysis object
'''

class bPlot:
	def __init__(self, ba):
		"""
		ba: bAnalysis object
		"""
		self.ba = ba
	
	#############################
	# plot functions
	#############################
	def plotDeriv(self, medianFilter=0, dVthresholdPos=100, fig=None):
		'''
		Plot both Vm and the derivative of Vm (dV/dt).

		Parameters:
			medianFilter:	0 is no filtering
							Integer greater than 0 specifies the number of points
		'''

		spikeTimes, thresholdTimes, vm, sweepDeriv = self.spikeDetect0(dVthresholdPos=dVthresholdPos, medianFilter=medianFilter)

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

		if fig is None:
			fig = plt.figure(figsize=(10, 8))
		ax1 = fig.add_subplot(grid[0,0])
		ax2 = fig.add_subplot(grid[1,0], sharex=ax1)
		#ax3 = fig.add_subplot(grid[2,0], sharex=ax1)


		ax1.plot(self.abf.sweepX, vm, label='filtered Vm (mV)')
		ax1.set_ylabel(yAxisLabel + 'Vm (mV)')

		ax2.plot(self.abf.sweepX, sweepDeriv)
		ax2.set_ylabel('dV/dt')
		ax2.set_xlabel('Seconds')

		#ax3.plot(self.abf.sweepX, sweepDeriv2)
		#ax3.set_ylabel('dV/dt (2)')

		# spike detect and append
		ax1.plot(self.abf.sweepX[spikeTimes], vm[spikeTimes], 'or', label='threshold')
		ax2.plot(self.abf.sweepX[spikeTimes], sweepDeriv[spikeTimes], 'or')

		print('detected', len(spikeTimes), 'spikes medianFilter:', medianFilter, 'dVthresholdPos:', dVthresholdPos)

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
