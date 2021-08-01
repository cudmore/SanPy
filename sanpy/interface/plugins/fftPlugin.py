import sys, math
from math import exp
import numpy as np
from scipy.signal import butter, lfilter, freqz
import scipy.signal
import matplotlib.pyplot as plt

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def butter_lowpass_sos(cutoff, fs, order=5):
	nyq = 0.5 * fs
	normal_cutoff = cutoff / nyq
	#sos = butter(order, normal_cutoff, btype='low', analog=False, output='sos')
	sos = butter(order, cutoff, fs=fs, btype='lowpass', analog=False, output='sos')
	return sos

def spikeDetect(t, dataFiltered, dataThreshold2, startPoint=None, stopPoint=None):
	verbose = False
	#dataThreshold2 = -59.81

	g_backupFraction = 0.3  # 0.5 or 0.3

	logger.info(f'dataThreshold2:{dataThreshold2} startPoint:{startPoint} stopPoint:{stopPoint}')

	#
	# detect spikes, dataThreshold2 changes as we zoom
	Is = np.where(dataFiltered>dataThreshold2)[0]
	Is=np.concatenate(([0],Is))
	Ds=Is[:-1]-Is[1:]+1
	spikePoints = Is[np.where(Ds)[0]+1]
	spikeSeconds = t[spikePoints]

	#
	# Throw out spikes that are within refractory (ms) of previous
	spikePoints = _throwOutRefractory(spikePoints, refractory_ms=100)
	spikeSeconds = t[spikePoints]

	#
	# remove spikes outside of start/stop
	goodSpikes = []
	if startPoint is not None and stopPoint is not None:
		if verbose:
			print(f'  Removing spikes outside point range {startPoint} ... {stopPoint}')
		#print(f'    {t[startPoint]} ... {t[stopPoint]} (s)')
		for idx, spikePoint in enumerate(spikePoints):
			if spikePoint<startPoint or spikePoint>stopPoint:
				pass
			else:
				goodSpikes.append(spikePoint)
				if verbose:
					print(f'    appending spike {idx} {t[spikePoint]}(s)')
	#
	spikePoints = goodSpikes
	spikeSeconds = t[spikePoints]

	#
	# only accept rising phase
	windowPoints = 40 # assuming 10 kHz -->> 4 ms
	goodSpikes = []
	for idx, spikePoint in enumerate(spikePoints):
		preClip = dataFiltered[spikePoint-windowPoints:spikePoint-1]
		postClip = dataFiltered[spikePoint+1:spikePoint+windowPoints]
		preMean = np.nanmean(preClip)
		postMean = np.nanmean(postClip)
		if preMean < postMean:
			goodSpikes.append(spikePoint)
		else:
			pass
			#print(f'  rejected spike {idx}, at point {spikePoint}')
	#
	spikePoints = goodSpikes
	spikeSeconds = t[spikePoints]

	#
	# throw out above take-off-potential of APs (-30 mV)
	apTakeOff = -30
	goodSpikes = []
	for idx, spikePoint in enumerate(spikePoints):
		if dataFiltered[spikePoint] < apTakeOff:
			goodSpikes.append(spikePoint)
	#
	spikePoints = goodSpikes
	spikeSeconds = t[spikePoints]

	#
	# find peak for eack spike
	# at 500 pnts, assuming spikes are slower than 20 Hz
	peakWindow_pnts = 500
	peakPoints = []
	peakVals = []
	for idx, spikePoint in enumerate(spikePoints):
		peakPnt = np.argmax(dataFiltered[spikePoint:spikePoint+peakWindow_pnts])
		peakPnt += spikePoint
		peakVal = np.max(dataFiltered[spikePoint:spikePoint+peakWindow_pnts])
		#
		peakPoints.append(peakPnt)
		peakVals.append(peakVal)

	#
	# backup each spike until pre/post is not changing
	# uses g_backupFraction to get percent of dv/dt at spike veruus each backup window
	backupWindow_pnts = 10
	maxSteps = 30  # 30 steps at 20 pnts (2ms) per step gives 60 ms
	backupSpikes = []
	for idx, spikePoint in enumerate(spikePoints):
		#print(f'=== backup spike:{idx} at {t[spikePoint]}(s)')
		foundBackupPoint = None
		for step in range(maxSteps):
			tmpPnt = spikePoint - (step*backupWindow_pnts)
			tmpSeconds = t[tmpPnt]
			preClip = dataFiltered[tmpPnt-1-backupWindow_pnts:tmpPnt-1]  # reversed
			postClip = dataFiltered[tmpPnt+1:tmpPnt+1+backupWindow_pnts]
			preMean = np.nanmean(preClip)
			postMean = np.nanmean(postClip)
			diffMean = postMean - preMean
			if step == 0:
				initialDiff = diffMean
			#print(f'  spike {idx} step:{step} tmpSeconds:{round(tmpSeconds,4)} initialDiff:{round(initialDiff,4)} diff:{round(diffMean,3)}')
			# if diffMean is 1/2 initial AP slope then accept
			if diffMean < (initialDiff * g_backupFraction):
				# stop
				foundBackupPoint = tmpPnt
				#break
		#
		if foundBackupPoint is not None:
			backupSpikes.append(foundBackupPoint)
		else:
			# needed to keep spike parity
			logger.warning(f'appending nan to backupSpike for spike {idx}')
			backupSpikes.append(np.nan)

	#
	# use backupSpikes (points) to get each spike amplitude
	spikeAmps = []
	for idx, backupSpike in enumerate(backupSpikes):
		if backupSpikes==np.nan or math.isnan(backupSpike):
			continue
		#print('backupSpike:', backupSpike)
		footVal = dataFiltered[backupSpike]
		peakVal = peakVals[idx]
		spikeAmp = peakVal - footVal
		spikeAmps.append(spikeAmp)

	# TODO: use foot and peak to get real half/width

	#
	# get estimate of duration
	# for each spike, find next downward crossing (starting at peak)
	minDurationPoints = 10
	windowPoints = 1000  # 100 ms
	fallingPoints = []
	for idx, spikePoint in enumerate(spikePoints):
		peakPoint = peakPoints[idx]
		backupPoint = backupSpikes[idx]
		if backupPoint == np.nan or math.isnan(backupPoint):
			continue
		spikeSecond = spikeSeconds[idx]
		# Not informative because we are getting spikes from absolute threshold
		thisThreshold = dataFiltered[backupPoint]
		thisPeak = dataFiltered[peakPoint]
		halfHeight = thisThreshold + (thisPeak - thisThreshold) / 2
		startPoint = peakPoint #+ 50
		postClip = dataFiltered[startPoint:startPoint+windowPoints]
		tmpFallingPoints = np.where(postClip<halfHeight)[0]
		if len(tmpFallingPoints) > 0:
			fallingPoint = startPoint + tmpFallingPoints[0]
			# TODO: check if falling point is AFTER next spike
			duration = fallingPoint - spikePoint
			if duration > minDurationPoints:
				fallingPoints.append(fallingPoint)
			else:
				print(f'  reject spike {idx} at {spikeSecond} (s), duration is {duration} points, minDurationPoints:{minDurationPoints}')
				#fallingPoints.append(fallingPoint)
		else:
			print(f'    did not find falling pnt for spike {idx} at {spikeSecond}(s) point {spikePoint}, assume it is longer than windowPoints')
			pass
			#fallingPoints.append(np.nan)

	# TODO: Pacckage all results into a dictionary

	#
	spikeSeconds = t[spikePoints]
	return spikeSeconds, spikePoints, peakPoints, peakVals, fallingPoints, backupSpikes, spikeAmps

def _throwOutRefractory(spikePoints, refractory_ms=100):
	"""
	spikePoints: spike times to consider
	refractory_ms:
	"""
	dataPointsPerMs = 10

	before = len(spikePoints)

	# if there are doubles, throw-out the second one
	#refractory_ms = 20 #10 # remove spike [i] if it occurs within refractory_ms of spike [i-1]
	lastGood = 0 # first spike [0] will always be good, there is no spike [i-1]
	for i in range(len(spikePoints)):
		if i==0:
			# first spike is always good
			continue
		dPoints = spikePoints[i] - spikePoints[lastGood]
		if dPoints < dataPointsPerMs*refractory_ms:
			# remove spike time [i]
			spikePoints[i] = 0
		else:
			# spike time [i] was good
			lastGood = i
	# regenerate spikeTimes0 by throwing out any spike time that does not pass 'if spikeTime'
	# spikeTimes[i] that were set to 0 above (they were too close to the previous spike)
	# will not pass 'if spikeTime', as 'if 0' evaluates to False
	#if goodSpikeErrors is not None:
	#	goodSpikeErrors = [goodSpikeErrors[idx] for idx, spikeTime in enumerate(spikeTimes0) if spikeTime]
	spikePoints = [spikePoint for spikePoint in spikePoints if spikePoint]

	# TODO: put back in and log if detection ['verbose']
	after = len(spikePoints)
	logger.info(f'From {before} to {after} spikes with refractory_ms:{refractory_ms}')

	return spikePoints

#class fftPlugin(sanpyPlugin):
class fftPlugin():
	myHumanName = 'FFT'

	def __init__(self, myAnalysisDir, **kwargs):
		"""
		Args:
			ba (bAnalysis): Not required
		"""
		#super().__init__(myAnalysisDir, **kwargs)
		self._analysisDir = myAnalysisDir

		self.signalHz = None  # assign when using fake data
		self.xPlotHz = 50  # limit x-axis frequenccy

		self.sos = None

		self.lastLeft = None
		self.lastRight = None

		self.loadData(2)

		self._buildInterface()

		self.spikeSeconds = None
		self.spikePoints = None
		self.peakPoints = None
		self.peakVals = None
		self.fallingPoints = None

		self._getPsd()

		self.dataLine = None
		self.dataFilteredLine = None
		self.spikesLine = None
		self.peaksLine = None
		self.fallingLine = None
		self.dataMeanLine = None
		self.thresholdLine2 = None
		self.thresholdLine3 = None

		self.replot2(firstPlot=True)
		#self.replotData(firstPlot=True)
		#self.replotPsd()

	@property
	def ba(self):
		return self._ba

	def _buildInterface(self):
		width = 10
		height = 6
		self.fig = plt.figure(figsize=(width, height))
		self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)

		numPlots = 2
		# This is for filter responnse
		plotNum = 1
		#self.ax1 = self.fig.add_subplot(3,1,1) # filter response
		self.ax2 = self.fig.add_subplot(numPlots,1,plotNum) # raw data
		plotNum += 1
		self.ax3 = self.fig.add_subplot(numPlots,1,plotNum) # psd

		self.ax2.callbacks.connect('xlim_changed', self.on_xlims_change)

		#self.ax1 = plt.subplot(3, 1, 1)  # filter response
		#self.ax2 = plt.subplot(3, 1, 2)  # raw data
		#self.ax3 = plt.subplot(3, 1, 3)  # psd

		#plt.show()
		#self.fig.show()

	def replot2(self, firstPlot=False, switchFile=False):
		logger.info(f'firstPlot:{firstPlot}')

		self.replotData(firstPlot=firstPlot, switchFile=switchFile)
		self.replotPsd()

		plt.draw()

	def replotData(self, firstPlot=False, switchFile=False):
		#logger.info(f'firstPlot:{firstPlot}')

		#
		# spike detect
		self.spikeSeconds, self.spikePoints, self.peakPoints, self.peakVals, self.fallingPoints, self.backupSpikes, self.spikeAmps = spikeDetect(
										self.t,
										self.dataFiltered,
										self.dataThreshold2,
										self.lastLeft,
										self.lastRight)

		# strip np.nan from backupSpikes
		self.backupSpikes = [tmpSpike for tmpSpike in self.backupSpikes if not math.isnan(tmpSpike)]
		#print('self.backupSpikes:', self.backupSpikes)

		# grab attributes
		t = self.t
		data = self.data
		dataFiltered = self.dataFiltered
		spikeSeconds = self.spikeSeconds
		spikePoints = self.spikePoints
		backupSpikes = self.backupSpikes
		peakPoints = self.peakPoints
		peakVals = self.peakVals
		fallingPoints = self.fallingPoints

		#backupSpikes = xxx

		if firstPlot:
			#ax2.clear()

			#self.ax2.callbacks.connect('xlim_changed', self.on_xlims_change)
			self.dataLine, = self.ax2.plot(t, data, 'k', label='data')
			self.dataFilteredLine, = self.ax2.plot(t, self.dataFiltered, 'b', linewidth=0.5, label='savgol filtered')
			#ax2.plot(t, y_sos, 'r', label='filter response')

			self.spikesLine, = self.ax2.plot(t[spikePoints], dataFiltered[spikePoints], '.r')
			self.fallingLine, = self.ax2.plot(t[fallingPoints], dataFiltered[fallingPoints], '.y')

			self.peaksLine, = self.ax2.plot(t[peakPoints], dataFiltered[peakPoints], '.g')

			self.backupLine, = self.ax2.plot(t[backupSpikes], dataFiltered[backupSpikes], '.g')

			self.dataMeanLine = self.ax2.axhline(self.dataMean, color='k', linestyle='--', linewidth=0.5)
			self.thresholdLine2 = self.ax2.axhline(self.dataThreshold2, color='r', linestyle='--', linewidth=0.5)
			self.thresholdLine3 = self.ax2.axhline(self.dataThreshold3, color='r', linestyle='--', linewidth=0.5)

			#plt.show()

		elif self.thresholdLine2 is not None:

			self.spikesLine.set_xdata(t[spikePoints])
			self.spikesLine.set_ydata(dataFiltered[spikePoints])

			self.backupLine.set_xdata(t[backupSpikes])
			self.backupLine.set_ydata(dataFiltered[backupSpikes])

			self.peaksLine.set_xdata(t[peakPoints])
			self.peaksLine.set_ydata(dataFiltered[peakPoints])

			self.fallingLine.set_xdata(t[fallingPoints])
			self.fallingLine.set_ydata(dataFiltered[fallingPoints])

			#logger.info(f'setting dataThreshold:{self.dataThreshold2} {self.dataThreshold3}')
			self.dataMeanLine.set_ydata(self.dataMean)
			self.thresholdLine2.set_ydata(self.dataThreshold2)
			self.thresholdLine3.set_ydata(self.dataThreshold3)

		autoScaleX = False
		if switchFile:
			autoScaleX = True
			self.dataLine.set_xdata(t)
			self.dataLine.set_ydata(data)
			self.dataFilteredLine.set_xdata(t)
			self.dataFilteredLine.set_ydata(dataFiltered)

		self.ax2.relim()
		self.ax2.autoscale_view(True, autoScaleX, True)  # (tight, x, y)
		#plt.draw()

	def replotPsd(self):
		#logger.info(f'len(f):{len(self.f)} Pxx_den max:{np.nanmax(self.Pxx_den)}')
		self.ax3.clear()
		self.ax3.semilogy(self.f, self.Pxx_den)
		if self.signalHz is not None:
			ax3.axvline(self.signalHz, color='k', linestyle='--', linewidth=0.5)
		self.ax3.set_ylim([1e-7, 1e2])
		self.ax3.set_xlabel('frequency [Hz]')
		self.ax3.set_ylabel('PSD [V**2/Hz]')
		#plt.xlim(0, 0.01*fs)
		self.ax3.set_xlim(0, self.xPlotHz)  # Hz

		self.ax3.relim()
		self.ax3.autoscale_view(True,True,True)
		#plt.draw()

	def loadData(self, fileIdx=0):
		self._ba = self._analysisDir.getAnalysis(fileIdx)
		#print(self.ba)
		self.t = self.ba.sweepX()[:,0]
		self.fs = self.ba.recordingFrequency * 1000
		self.data = self.ba.sweepY()[:,0]
		self.data = self.data.copy()

		# normalize data
		'''
		dataMean = np.nanmean(data)
		data -= dataMean
		'''

		SavitzkyGolay_pnts = 5
		SavitzkyGolay_poly = 2
		self.dataFiltered = scipy.signal.savgol_filter(self.data,
							SavitzkyGolay_pnts, SavitzkyGolay_poly,
							mode='nearest', axis=0)

		# thresholds based on std
		dataMean = np.nanmean(self.dataFiltered)
		dataStd = np.nanstd(self.dataFiltered)
		self.dataMean = dataMean
		self.dataThreshold2 = dataMean + (2 * dataStd)
		self.dataThreshold3 = dataMean + (3 * dataStd)

		# these are in points
		#self.lastLeft = 0
		#self.lastRight = len(self.dataFiltered)

		# rebuild filter based on loaded fs
		cutoff = 20
		order = 40
		self.sos = butter_lowpass_sos(cutoff, self.fs, order=5)

	def on_xlims_change(self, event_ax):
		#slogger.info(f'event_ax:{event_ax}')
		left, right = event_ax.get_xlim()
		logger.info(f'left:{left} right:{right}')

		# find start/stop point from seconds in 't'
		leftPoint = np.where(self.t >= left)[0]
		leftPoint = leftPoint[0]
		rightPoint = np.where(self.t >= right)[0]
		if len(rightPoint) == 0:
			rightPoint = len(self.t)  # assuming we use [left:right]
		else:
			rightPoint = rightPoint[0]
		#print('leftPoint:', leftPoint, 'rightPoint:', rightPoint, 'len(t):', len(self.t))

		# keep track of last setting, if it does not change then do nothing
		if self.lastLeft==leftPoint and self.lastRight==rightPoint:
			return
		else:
			self.lastLeft = leftPoint
			self.lastRight = rightPoint

		# get threshold fromm selection
		dataFiltered = self.dataFiltered
		theMean = np.nanmean(dataFiltered[leftPoint:rightPoint])
		theStd = np.nanstd(dataFiltered[leftPoint:rightPoint])
		self.dataMean = theMean
		self.dataThreshold2 = theMean + (2 * theStd)
		self.dataThreshold3 = theMean + (3 * theStd)
		#logger.info(f'dataThreshold:{self.dataThreshold2} {self.dataThreshold3}')

		# psd depends on x-axis
		self._getPsd()

		self.replot2(firstPlot=False)
		#self.replotData(firstPlot=False)
		#self.replotPsd()

	def _getPsd(self):
		"""Get psd from selected x-axes range.
		"""
		#logger.info(f'self.lastLeft:{self.lastLeft} self.lastRight:{self.lastRight}')
		dataFiltered = self.dataFiltered
		leftPoint = self.lastLeft
		rightPoint = self.lastRight
		y_sos = scipy.signal.sosfilt(self.sos, dataFiltered[leftPoint:rightPoint])
		self.f, self.Pxx_den = scipy.signal.periodogram(y_sos, self.fs)

	def keyPressEvent(self, event):
		logger.info(event)
		#super().keyPressEvent(event)

		#isMpl = isinstance(event, mpl.backend_bases.KeyEvent)
		text = event.key
		logger.info(f'mpl key: {text}')

		if text in ['0', '1', '2', '3', '4', '5']:
			fileIdx = int(text)
			self.loadData(fileIdx)
			self.replot2(switchFile=True)

if __name__ == '__main__':
	path = '/Users/cudmore/Sites/Sanpy/data/fft'
	ad = sanpy.analysisDir(path, autoLoad=True)
	fft = fftPlugin(ad)
	plt.show()
