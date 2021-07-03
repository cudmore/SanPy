"""
General purpose plugins to plot from a [sanpy.bAnalysis][sanpy.bAnalysis.bAnalysis] object.
"""
#Robert Cudmore
#20190328

import numpy as np
import scipy.signal
import matplotlib.pyplot as plt

import sanpy

def getEddLines(ba):
	"""Get lines representing linear fit of EDD rate.

	Args:
		ba (bAnalysis): bAnalysis object
	"""
	preLinearFitPnt0 = ba.getStat('preLinearFitPnt0')
	preLinearFitSec0 = [ba.pnt2Sec_(x) for x in preLinearFitPnt0]
	preLinearFitVal0 = ba.getStat('preLinearFitVal0')

	preLinearFitPnt1 = ba.getStat('preLinearFitPnt1')
	preLinearFitSec1 = [ba.pnt2Sec_(x) for x in preLinearFitPnt1]
	preLinearFitVal1 = ba.getStat('preLinearFitVal1')

	x = []
	y = []
	for idx, spike in enumerate(range(ba.numSpikes)):
		dx = preLinearFitSec1[idx] - preLinearFitSec0[idx]
		dy = preLinearFitVal1[idx] - preLinearFitVal0[idx]

		lineLength = 4  # TODO: make this a function of spike frequency?

		x.append(preLinearFitSec0[idx])
		x.append(preLinearFitSec1[idx] + lineLength*dx)
		x.append(np.nan)

		y.append(preLinearFitVal0[idx])
		y.append(preLinearFitVal1[idx] + lineLength*dy)
		y.append(np.nan)

	return x, y

def getHalfWidths(ba):
	"""Get lines representing half-widhts (AP Dur).

	Args:
		ba (bAnalysis): bAnalysis object

	Returns:
		x,y (enum):
	"""
	# defer until we know how many half-widths 20/50/80
	x = []
	y = []
	numPerSpike = 3  # rise/fall/nan
	numSpikes = ba.numSpikes
	xyIdx = 0
	for idx, spike in enumerate(ba.spikeDict):
		if idx ==0:
			# make x/y from first spike using halfHeights = [20,50,80]
			halfHeights = spike['halfHeights'] # will be same for all spike, like [20, 50, 80]
			numHalfHeights = len(halfHeights)
			# *numHalfHeights to account for rise/fall + padding nan
			x = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
			y = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
			#print('  len(x):', len(x), 'numHalfHeights:', numHalfHeights, 'numSpikes:', numSpikes, 'halfHeights:', halfHeights)

		for idx2, width in enumerate(spike['widths']):
			halfHeight = width['halfHeight'] # [20,50,80]
			risingPnt = width['risingPnt']
			risingVal = width['risingVal']
			fallingPnt = width['fallingPnt']
			fallingVal = width['fallingVal']

			if risingPnt is None or fallingPnt is None:
				# half-height was not detected
				continue

			risingSec = ba.pnt2Sec_(risingPnt)
			fallingSec = ba.pnt2Sec_(fallingPnt)

			x[xyIdx] = risingSec
			x[xyIdx+1] = fallingSec
			x[xyIdx+2] = np.nan
			# y
			y[xyIdx] = fallingVal  #risingVal, to make line horizontal
			y[xyIdx+1] = fallingVal
			y[xyIdx+2] = np.nan

			# each spike has 3x pnts: rise/fall/nan
			xyIdx += numPerSpike  # accounts for rising/falling/nan
		# end for width
	# end for spike
	return x, y

class bAnalysisPlot():
	"""
	Class to plot results of [sanpy.bAnalysis][sanpy.bAnalysis.bAnalysis] spike detection.
	"""
	def __init__(self, ba=None):
		"""
		Args:
			ba: [sanpy.bAnalysis][sanpy.bAnalysis] object
		"""
		self._ba = ba

	@property
	def ba(self):
		"""Get underlying bAnalysis object."""
		return self._ba

	def getDefaultPlotStyle(self):
		"""Get dictionary with default plot style."""
		d = {
			'linewidth': 0.5,
			'color': 'k',
			'width': 6,
			'height': 3,
		}
		return d.copy()

	def _makeFig(self, plotStyle=None):
		if plotStyle is None:
			plotStyle = self.getDefaultPlotStyle()

		grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

		width = plotStyle['width']
		height = plotStyle['height']
		fig = plt.figure(figsize=(width, height))
		ax = fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		ax.spines['right'].set_visible(False)
		ax.spines['top'].set_visible(False)

		return fig, ax

	def plotRaw(self, plotStyle=None, ax=None):
		"""
		Plot raw recording

		Args:
			plotStye (float):
			ax (xxx):
		"""

		if plotStyle is None:
			plotStyle = self.getDefaultPlotStyle()

		if ax is None:
			fig, ax = self._makeFig()

		color = plotStyle['color']
		linewidth = plotStyle['linewidth']
		sweepX = self.ba.sweepX
		sweepY = self.ba.sweepY

		ax.plot(sweepX, sweepY, '-', c=color, linewidth=linewidth) # fmt = '[marker][line][color]'

		xUnits = self.ba.get_xUnits()
		yUnits = self.ba.get_yUnits()
		ax.set_xlabel(xUnits)
		ax.set_ylabel(yUnits)

	def plotDerivAndRaw(self):
		"""
		Plot both Vm and the derivative of Vm (dV/dt).

		Args:
			fig (matplotlib.pyplot.figure): An existing figure to plot to.
				see: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.figure.html
		"""

		#
		# make a 2-panel figure
		grid = plt.GridSpec(2, 1, wspace=0.2, hspace=0.4)
		fig = plt.figure(figsize=(10, 8))
		ax1 = fig.add_subplot(grid[0,0])
		ax2 = fig.add_subplot(grid[1,0], sharex=ax1)
		ax1.spines['right'].set_visible(False)
		ax1.spines['top'].set_visible(False)
		ax2.spines['right'].set_visible(False)
		ax2.spines['top'].set_visible(False)

		self.plotRaw(ax=ax1);

		sweepX = self.ba.sweepX
		filteredDeriv = self.ba.filteredDeriv
		ax2.plot(sweepX, filteredDeriv)

		ax2.set_ylabel('dV/dt')
		#ax2.set_xlabel('Seconds')

		return fig

	def plotSpikes(self, plotStyle=None, ax=None):
		'''
		Plot Vm with spike analysis overlaid as symbols

		plotStyle (dict): xxx
		ax (xxx): If specified will plot into a MatPlotLib axes
		'''

		if plotStyle is None:
			plotStyle = self.getDefaultPlotStyle()

		if ax is None:
			fig, ax = self._makeFig()

		# plot vm
		self.plotRaw(ax=ax)

		# plot spike times
		thresholdVal = self.ba.getStat('thresholdVal')
		thresholdPnt = self.ba.getStat('thresholdPnt')
		thresholdSec = [self.ba.pnt2Sec_(x) for x in thresholdPnt]
		ax.plot(thresholdSec, thresholdVal, 'pg')

		# plot the peak
		peakVal = self.ba.getStat('peakVal')
		peakPnt = self.ba.getStat('peakPnt')
		peakSec = [self.ba.pnt2Sec_(x) for x in peakPnt]
		ax.plot(peakSec, peakVal, 'or')

		xUnits = self.ba.get_xUnits()
		yUnits = self.ba.get_yUnits()
		ax.set_xlabel(xUnits)
		ax.set_ylabel(yUnits)

		return fig, ax

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

def test_plot(path):
	print('=== test_plot() path:', path)
	ba = sanpy.bAnalysis(path)

	# detect
	dDict = ba.getDefaultDetection()
	dDict['dvdThreshold'] = 50
	ba.spikeDetect(dDict)

	# plot
	bp = sanpy.bAnalysisPlot(ba)

	fig = bp.plotDerivAndRaw()

	fig = bp.plotSpikes()

	plt.show()

if __name__ == '__main__':
	path = 'data/19114001.abf'
	test_plot(path)

	# TODO: check if error

	path = 'data/19114001.csv'
	test_plot(path)
