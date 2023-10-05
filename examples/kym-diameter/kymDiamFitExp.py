"""Implementing fit of kym diam
 - decay tau (70%)
 - half-width
 """

import sys
import warnings
import numpy as np
import pandas as pd
import scipy.optimize
# from scipy.optimize import curve_fit
import scipy.signal

import matplotlib.pyplot as plt

import sanpy

def plotDvDt(ba : sanpy.bAnalysis):
	"""Plot dvdt with mean and sd.
	"""
	sweepX = ba.fileLoader.sweepX
	filteredDeriv = ba.fileLoader.filteredDeriv
	_mean = np.mean(filteredDeriv)
	_std = np.std(filteredDeriv)
	_two_std = _std * 2

	plt.plot(sweepX, filteredDeriv)
	plt.axhline(y=_mean, color='r', linestyle='-')
	plt.axhline(y=_std, color='r', linestyle='-')
	plt.axhline(y=_two_std, color='r', linestyle='-')

	plt.show()

def guessDvDtThreshold(ba : sanpy.bAnalysis) -> float:
	"""Guess the dvdt threshold as mean+std of dvdt.

	Works well for normalized [0,1] Ca++ kymograph sum.
	"""
	filteredDeriv = ba.fileLoader.filteredDeriv
	_mean = np.mean(filteredDeriv)
	_std = np.std(filteredDeriv)
	return _mean + _std

import seaborn as sns

def run():

	path = '/media/cudmore/data/Dropbox/data/cell-shortening/Low resolution files_kymographs analysis/cell02_0002.tif.frames/cell02_0002_C002T001.tif'

	# path = '/media/cudmore/data/Dropbox/data/cell-shortening/fig1/06.03.22/cell 05.tif.frames/cell 05_C002T001.tif'

	#path = '/media/cudmore/data/Dropbox/data/cell-shortening/fig1/06.03.22/cell 08_0002.tif.frames/cell 08_0002_C002T001.tif'
	
	# broken ???
	#path = '/media/cudmore/data/Dropbox/data/cell-shortening/fig1/06.08.22/cell10.tif.frames/cell10_C002T001.tif'

	# bad fit
	#path = '/media/cudmore/data/Dropbox/data/cell-shortening/fig1/06.08.22/cell10_0001.tif.frames/cell10_0001_C002T001.tif'

	# bad fit
	#path = '/media/cudmore/data/Dropbox/data/cell-shortening/fig1/06.08.22/cell11.tif.frames/cell11_C002T001.tif'

	# bad fit
	#path = '/media/cudmore/data/Dropbox/data/cell-shortening/fig1/06.08.22/cell14.tif.frames/cell14_C002T001.tif'

	# load ba
	ba = sanpy.bAnalysis(path)

	# plotDvDt(ba)
	
	_threshold = guessDvDtThreshold(ba)
	print('_threshold:', _threshold)

	# set detection parameters and detect
	dDict = sanpy.bDetection().getDetectionDict('Ca Kymograph')
	dDict['dvdtThreshold'] = _threshold  #0.007
	dDict['verbose'] = False
	# spike detect will also detect diameter params 'diam_*'
	ba.spikeDetect(dDict)

	# analyze diameter
	ba.kymAnalysis.setAnalysisParam('imageFilterKenel', 0)
	ba.kymAnalysis.setAnalysisParam('lineWidth', 3)
	ba.kymAnalysis.analyzeDiameter(verbose=False)

	detectDiam(ba)
	sys.exit()

	print('ba is:', ba)

	# try and detect outliers in diameter_um_filt
	# see: https://www.askpython.com/python/examples/detection-removal-outliers-in-python
	diameter_um_filt = ba.kymAnalysis.getResults('diameter_um_filt')

	plt.plot(diameter_um_filt, 'k')

	if 0:
		dfDiam = ba.kymAnalysis.getResultsAsDataFrame()
		dfDiam = pd.DataFrame(dfDiam['diameter_um_filt'])
		sns.boxplot(y=dfDiam['diameter_um_filt'])
		plt.show()
		
		for x in ['diameter_um_filt']:
			q75,q25 = np.percentile(dfDiam.loc[:,x],[75,25])
			intr_qr = q75-q25
		
			max = q75+(1.5*intr_qr)
			min = q25-(1.5*intr_qr)
		
			# set to nan, we really want to linear interp the outlier diameters
			dfDiam.loc[dfDiam[x] < min,x] = np.nan
			dfDiam.loc[dfDiam[x] > max,x] = np.nan
		# dfDiam = dfDiam.interpolate(method='linear')
		dfDiam= dfDiam.interpolate(method='polynomial', order=2)
		diameter_um_filt = dfDiam['diameter_um_filt'].to_numpy()
		
		sns.boxplot(y=dfDiam['diameter_um_filt'])
		plt.show()

	# remove outliers and interpolate
	if 0:
		_three_std = np.mean(diameter_um_filt) - (3*np.std(diameter_um_filt))
		print('removing diameters less than _three_std:', _three_std)
		diameter_um_filt[diameter_um_filt<_three_std] = np.nan
		
		ok = ~np.isnan(diameter_um_filt)
		xp = ok.ravel().nonzero()[0]
		fp = diameter_um_filt[~np.isnan(diameter_um_filt)]
		x  = np.isnan(diameter_um_filt).ravel().nonzero()[0]
		# Replacing nan values
		diameter_um_filt[np.isnan(diameter_um_filt)] = np.interp(x, xp, fp)

	# foot
	k_diam_foot_pnt = ba.getStat('k_diam_foot_pnt')
	# k_diam_foot = ba.getStat('k_diam_foot')
	# peak
	k_diam_peak_pnt = ba.getStat('k_diam_peak_pnt')
	# k_diam_peak = ba.getStat('k_diam_peak')

	# print('k_diam_peak_pnt:', k_diam_peak_pnt)

	time_sec = ba.kymAnalysis.getResults('time_sec')
	time_sec = None
	# diameter_um = ba.kymAnalysis.getResults('diameter_um')
	# diameter_um_filt = ba.kymAnalysis.getResults('diameter_um_filt')

	# plt.plot(diameter_pnts)
	# plt.plot(k_diam_foot_pnt, k_diam_foot, 'o')
	# plt.plot(k_diam_peak_pnt, k_diam_peak, 'o')
	# plt.show()

	# fit exp
	expDecayFit(time_sec, diameter_um_filt, k_diam_foot_pnt, k_diam_peak_pnt)

	plt.show()

	return

	# see: https://swharden.com/blog/2020-09-24-python-exponential-fit/
	def monoExp(x, m, t, b):
		return m * np.exp(-t * x) + b

	i = 2
	_fitPeak = k_diam_peak_pnt[i]
	_fitNextFoot = k_diam_foot_pnt[i+1]
	y = diameter_pnts[_fitPeak:_fitNextFoot]
	x = range(len(y))

	plt.plot(x, y, 'o', label='data')

	from scipy.optimize import curve_fit
	_params, _ = curve_fit(monoExp, x, y)  # _params is [-3.4664  0.083  91.584 ]
	print('curve_fit params params:', _params)

	_yFit = monoExp(x, *_params)
	plt.plot(x, _yFit, 'r--', label='fit')

	plt.show()

def exponential_decay(x, a, b, c):
	return a * np.exp(-b * x) + c

def myMonoExp(x, m, t, b):
	"""
	M: a_0
	t: tau_0
	b: 
	"""
	# this triggers
	# "RuntimeWarning: overflow encountered in exp" during search for parameters, just ignor it
	ret = m * np.exp(-t * x) + b
	return ret

	# with np.errstate(divide='exp'):
	try:
		ret = m * np.exp(-t * x) + b
	except RuntimeWarning:
		print('my exception:', e)
		print('x:', x, 'm:', m, 't:', t, 'b:', b)

	return ret

def expDecayFit0(x, y, startPnt, stopPnt):
	"""Fit a single exponential decay with start and stop points.
	
	Parameters
	----------
	x : array like or None:
		if None then x is range(len(y))
	
	Returns:
	xRange, _yFit, _params
	"""

	yRange = y[startPnt:stopPnt]

	if x is None:
		x = np.arange(len(y))
		xRange = np.arange(len(yRange))
	else:
		xRange = x[startPnt:stopPnt]

	try:
		_params, _cov = scipy.optimize.curve_fit(myMonoExp, xRange, yRange)  # _params is [-3.4664  0.083  91.584 ]
	except(RuntimeError) as e:
		print('my exception:', e)
		return None, None, None
	
	_yFit = myMonoExp(xRange, *_params)

	xRange += x[startPnt]

	return xRange, _yFit, _params

def expDecayFit(diameter_time, diameter, k_diam_foot_pnt, k_diam_peak_pnt):
	"""For each spike, calculate exp decay in diameter from peak to next foot.
	"""

	plt.plot(diameter, '-b', label='raw')

	_mean = np.mean(diameter)
	_std = _mean - np.std(diameter)
	_two_std = _mean - (2* np.std(diameter))
	_three_std = _mean - (3* np.std(diameter))
	plt.axhline(y=_mean, color='k', linestyle='-')
	plt.axhline(y=_std, color='c', linestyle='-')
	plt.axhline(y=_two_std, color='c', linestyle='-')
	plt.axhline(y=_three_std, color='c', linestyle='-')

	tauList = []
	n = len(k_diam_peak_pnt)
	for idx, peakPnt in enumerate(k_diam_peak_pnt):

		# first peak might be bad
		if np.isnan(peakPnt):
			print('idx:', idx, 'peakPnt:', peakPnt, 'SKIPPING')
			continue

		if idx < n-1:
			# search to next foot
			nextFootPnt = k_diam_foot_pnt[idx+1]
		else:
			# search to the end
			nextFootPnt = len(diameter) - 1

		print('idx:', idx, 'peakPnt:', peakPnt, 'nextFootPnt:', nextFootPnt)

		_x, _yFit, _params = expDecayFit0(diameter_time, diameter, peakPnt, nextFootPnt)

		print('    _params:', _params)
		if _x is None:
			tauList.append(np.nan)
			# print('there was an error')
		else:
			# plt.plot(x, y, 'o', label='raw')
			plt.plot(_x, _yFit, 'r.--', label='fit')
			_tau = _params[0]
			tauList.append(_tau)
			
	print('tauList:', tauList)
	# damn, using matplotlib globals is LAME
	# plt.plot(tauList)

def detectDiam(ba : sanpy.bAnalysis):
	"""Detect diameter changes using first derivative dvdt.
	
		- pair core spike analysis with each diameter threshold.
	"""
	
	# reanalyze diameter from raw kymograph image
	ba.kymAnalysis.analyzeDiameter(verbose=False)
	
	warnings.filterwarnings('ignore')

	secondsPerLine = ba.kymAnalysis.secondsPerLine
	sampleRate = 1/secondsPerLine # Hz
	polarity = 'neg'

	print(ba)
	print('secondsPerLine:', secondsPerLine, 'sampleRate:', sampleRate, 'Hz')

	filteredDiam = ba.kymAnalysis.getResults('diameter_um_golay')
	filteredDeriv = ba.kymAnalysis.getResults('diameter_dvdt')
	

	# # filtered by finalDiamFilterKernel
	# diameter_um_filt = ba.kymAnalysis.getResults('diameter_um_filt')

	# # filter diam again
	# SavitzkyGolay_pnts = 5
	# SavitzkyGolay_poly = 2
	# filteredDiam = scipy.signal.savgol_filter(
	# 	diameter_um_filt,
	# 	SavitzkyGolay_pnts,
	# 	SavitzkyGolay_poly,
	# 	axis=0,
	# 	mode="nearest",
	# )

	# # get the first derivative
	# filteredDeriv = np.diff(filteredDiam, axis=0)
	# filteredDeriv = np.append(filteredDeriv, 0)  # append a points oit is same length as filteredDiam

	# # filter derivative
	# SavitzkyGolay_pnts = 5
	# SavitzkyGolay_poly = 2
	# filteredDeriv0 = filteredDeriv  # unfiltered deriv
	# filteredDeriv = scipy.signal.savgol_filter(
	# 	filteredDeriv,
	# 	SavitzkyGolay_pnts,
	# 	SavitzkyGolay_poly,
	# 	axis=0,
	# 	mode="nearest",
	# )
	
	# parameters to autodetect diameter 'spikes' using dvdt
	_mean = np.mean(filteredDeriv)
	if polarity == 'pos':
		_std = _mean + np.std(filteredDeriv)
		_two_std = _mean + (2 * np.std(filteredDeriv))
	else:
		_std = _mean - np.std(filteredDeriv)
		_two_std = _mean - (2 * np.std(filteredDeriv))

	# diameter detection dictionary of detection parameters
	ddDict = {
		'polarity': polarity,
		'dvdThresh': _two_std,
		'refactoryPnts': 20,  # specifies the fastest diameter spikes
		'peakWinPnt': 20,  # to find the peak after threshold
		'peakWidthPnts': 20  #60,  # to find decay after peak (exponential decay)
	}

	# detect diam using dvdt
	dvdThresh = ddDict['dvdThresh']
	if polarity == 'pos':
		Is = np.where(filteredDeriv > dvdThresh)[0]  # use > to search for increase in diam
	else:
		Is = np.where(filteredDeriv < dvdThresh)[0]  # use < to search for decreases in diam
	Is = np.concatenate(([0], Is))
	Ds = Is[:-1] - Is[1:] + 1
	spikeTimes0 = Is[np.where(Ds)[0] + 1]
	# backup one pnt
	spikeTimes0 -= 1

	if len(spikeTimes0) == 0:
		print('ERROR: did not find and peaks in diameter')

	# throw out fast spikes
	refactoryPnts = ddDict['refactoryPnts']
	lastGood = 0  # first spike [0] will always be good, there is no spike [i-1]
	for i in range(len(spikeTimes0)):
		if i == 0:
			# first spike is always good
			continue
		dPoints = spikeTimes0[i] - spikeTimes0[lastGood]
		if dPoints < refactoryPnts:
			# remove spike time [i]
			# print('  throwing out spike', i, 'at pnt', spikeTimes0[i])
			spikeTimes0[i] = 0
		else:
			# spike time [i] was good
			lastGood = i
	spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if spikeTime]
	
	# reduce spike times using main ba dvdtThreshold
	spikeTimesSec = ba.getStat('thresholdSec')
	for spikeIdx, spikeTimeSec in enumerate(spikeTimesSec):
		# find a spike diameter threshold within a window after each spike
		dvdtThresholdPnt = ba.fileLoader.ms2Pnt_(spikeTimeSec*1000)
		dvdtThresholdPnt -= 1
		# print('spikeIdx:', spikeIdx, 'dvdtThreshold:', spikeTimeSec, 'dvdtThresholdPnt:', dvdtThresholdPnt)
		try:
			_idx = next(x[0] for x in enumerate(spikeTimes0) if x[1] >= dvdtThresholdPnt)
		except (StopIteration) as e:
			# diameter threshold not found
			_idx = np.nan
		print('spikeIdx:', spikeIdx, 'dvdtThresholdPnt:', 'is peak _idx:', _idx)

	# find peaks
	peakWinPnt = ddDict['peakWinPnt']
	diamPeakPnts = [np.nan] * len(spikeTimes0)
	for idx, spikeTime in enumerate(spikeTimes0):
		stopPnt = min(spikeTime + peakWinPnt, len(filteredDiam)-1)
		_clip = filteredDiam[spikeTime:stopPnt]
		if polarity == 'pos':
			minPnt = spikeTime + np.argmax(_clip)
		else:
			minPnt = spikeTime + np.argmin(_clip)
		diamPeakPnts[idx] = minPnt

	# fit decay from peak
	fitParamsList = []
	fit_xRangeList = []
	fit_m_list = [None] * len(spikeTimes0)
	fit_tau_list = [None] * len(spikeTimes0)
	fit_b_list = [None] * len(spikeTimes0)
	fit_r2_list = [None] * len(spikeTimes0)
	fit_tau_sec_list = [None] * len(spikeTimes0)
	
	peakWidthPnts = ddDict['peakWidthPnts']
	for idx, spikeTime in enumerate(spikeTimes0):
		peakPnt = diamPeakPnts[idx]
		_end = min(peakPnt+peakWidthPnts, len(filteredDiam)-1)
		yRange = filteredDiam[peakPnt:_end]
		xRange = np.arange(len(yRange))  # + peakPnt
		
		try:
			_params, _cov = scipy.optimize.curve_fit(myMonoExp, xRange, yRange)
		except (RuntimeError, TypeError) as e:
			print(f'  {idx} peakPnt:{peakPnt} my ERROR: {e}')
			fitParamsList.append((np.nan, np.nan, np.nan))
			fit_xRangeList.append(xRange)
			fit_m_list[idx] = np.nan
			fit_tau_list[idx] = np.nan
			fit_b_list[idx] = np.nan
			fit_r2_list[idx] = np.nan
		else:
			m, t, b = _params
			tauSec = (1 / t) / sampleRate
			fitParamsList.append(_params)
			fit_xRangeList.append(xRange)

			fit_m_list[idx] = m
			fit_tau_list[idx] = t
			fit_tau_sec_list[idx] = tauSec
			fit_b_list[idx] = b
			
			# determine quality of the fit
			squaredDiffs = np.square(yRange - myMonoExp(xRange, m, t, b))
			squaredDiffsFromMean = np.square(yRange - np.mean(yRange))
			rSquared = 1 - np.sum(squaredDiffs) / np.sum(squaredDiffsFromMean)
			print(f"  {idx} peakPnt:{peakPnt} m:{m} t:{t} b:{b} tauSec:{tauSec} R² = {rSquared}")

			fit_r2_list[idx] = rSquared

	# collect everything into a results dict
	dResultsDict = {
		# 'filteredDiam': filteredDiam,
		# 'filteredDeriv': filteredDeriv,
		'diamSpikeTimes': spikeTimes0,  # threshold time for each peak (points)
		'diamPeakPnts': diamPeakPnts,  # peak point
		'fit_m': fit_m_list,
		'fit_tau': fit_tau_list,
		'fit_tau_sec': fit_tau_sec_list,
		'fit_b': fit_b_list,
		'fit_r2': fit_r2_list,
	}

	plotDiamFit(ba, ddDict, dResultsDict)
	
	return ddDict, dResultsDict

def plotDiamFit(ba, ddDict, dResultsDict):

	# get diameter and derivative from main kym analysis
	filteredDiam = ba.kymAnalysis.getResults('diameter_um_golay')
	filteredDeriv = ba.kymAnalysis.getResults('diameter_dvdt')

	# these will all eventually be part of main ba spike detection
	spikeTimes0 = dResultsDict['diamSpikeTimes']
	diamPeakPnts = dResultsDict['diamPeakPnts']
	fit_m = dResultsDict['fit_m']
	fit_tau = dResultsDict['fit_tau']  # we also have fit_tau_sec
	fit_b = dResultsDict['fit_b']

	# params used for diameter fit
	polarity = ddDict['polarity']
	peakWidthPnts = ddDict['peakWidthPnts']

	_mean = np.mean(filteredDeriv)
	if polarity == 'pos':
		_std = _mean + np.std(filteredDeriv)
		_two_std = _mean + (2 * np.std(filteredDeriv))
	else:
		_std = _mean - np.std(filteredDeriv)
		_two_std = _mean - (2 * np.std(filteredDeriv))

	fig, axs = plt.subplots(3, 1, sharex=True)
	# rightAxes = axs[0].twinx()

	# axs[0].plot(diameter_um, 'k')
	axs[0].plot(filteredDiam, 'r-', label='filtered diam')
	axs[0].plot(spikeTimes0, filteredDiam[spikeTimes0], 'og', label='threshold time')
	axs[0].plot(diamPeakPnts, filteredDiam[diamPeakPnts], 'ob', label='peak time')

	# axs[0].set(xlabel='Line Scan Number')
	axs[0].set(ylabel='Diameter (um)')
	
	# plot exp decay from peak
	for idx, peakPnt in enumerate(diamPeakPnts):
		_fitParam = (fit_m[idx], fit_tau[idx], fit_b[idx])
		# peakPnt = diamPeakPnts[idx]
		# xRange = fit_xRangeList[idx]
		xRange = np.arange(peakWidthPnts)
		_yFit = myMonoExp(xRange, *_fitParam)
		# print('plot fit idx:', idx, 'with fitParam:', fitParam)
		# print('_yFit:', _yFit)
		axs[0].plot(xRange+peakPnt, _yFit, 'y')

	# rightAxes.plot(filteredDeriv, '-', label='filtered derivative')

	# Put a legend to the right of the current axis
	axs[0].legend(bbox_to_anchor=(1.02, 1))
	# rightAxes.legend(bbox_to_anchor=(1.02, 1))

	# axs[1].plot(filteredDeriv0, 'k', label='filtered deriv meadian')  # before 2nd filter
	axs[1].plot(filteredDeriv, '.-r', label='filtered deriv golay')  # after
	axs[1].axhline(y=_mean, color='r', linestyle='--', label='')
	axs[1].axhline(y=_std, color='r', linestyle='--', label='')
	axs[1].axhline(y=_two_std, color='r', linestyle='--', label='')

	axs[1].legend(bbox_to_anchor=(1.02, 1))

	axs[1].set(ylabel='first deriv of diameter')
	axs[1].set(xlabel='Line Scan Number')

	thresholdSec = ba.getStat('thresholdSec')
	thresholdPnt = [ba.fileLoader.ms2Pnt_(x*1000) for x in thresholdSec]
	print('thresholdPnt:', thresholdPnt)
	yThreshold = [ba.fileLoader.sweepY[x] for x in thresholdPnt]
	print('ba.fileLoader.sweepY:', type(ba.fileLoader.sweepY), ba.fileLoader.sweepY.shape)
	axs[2].plot(ba.fileLoader.sweepY, 'k-')
	axs[2].plot(thresholdPnt, yThreshold, 'ko')
	axs[2].set(ylabel='Sum Intensity')
	rightAxes2 = axs[2].twinx()
	rightAxes2.plot(filteredDeriv, 'r-')

	plt.show()

if __name__ == '__main__':
	run()
