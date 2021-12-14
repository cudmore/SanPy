"""
Important, had to modify parsing comment of atf

see abb in:
	/home/cudmore/Sites/SanPy/sanpy_env/lib/python3.8/site-packages/pyabf/atf.py", line 63
"""
import os, sys
import numpy as np
import pandas as pd
import seaborn as sns

import matplotlib.pyplot as plt

from colinAnalysis import bAnalysis2
from sanpy.interface.plugins.stimGen2 import readFileParams, buildStimDict

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def load(path):

	stimulusFileFolder = None #'/media/cudmore/data/stoch-res' #os.path.split(path)[0]

	ba = bAnalysis2(path, stimulusFileFolder=stimulusFileFolder)
	print(ba)

	#print('_stimFile:', ba._stimFile)
	#print('_stimFileComment:', ba._stimFileComment)

	'''
	# load and print the parameters from the atf stimulus file
	atfPath = '/media/cudmore/data/stoch-res/sanpy_20211206_0007.atf'
	atfParams = readFileParams(atfPath)
	print('=== atf file params', atfPath)
	print(atfParams)
	'''

	return ba

def plotStimFileParams(ba):
	d = ba.stimDict
	if d is None:
		return

	dList = buildStimDict(d, path=ba.filePath)
	#for one in dList:
	#	print(one)
	df = pd.DataFrame(dList)
	print(df)
	return df
def detect(ba, thresholdValue = -20):
	"""
	Detect spikes
	"""
	detectionDict = ba.detectionParams
	detectionDict['threshold'] = thresholdValue
	detectionDict['width'] = [50, 800*10]
	detectionDict['doBaseline'] = False
	detectionDict['preFootMs'] = 50 * 10
	detectionDict['verbose'] = True
	ba.detect(detectionDict=detectionDict)

	if ba.analysisDf is not None:
		logger.info(f'detected {len(ba.analysisDf)} spikes')
		#print(ba.analysisDf.head())
	else:
		logger.info(f'detected No spikes')

def reduce(ba):
	"""
	Reduce spikes based on start/stop of sin stimulus

	TODO:
		Use readFileParams(atfPath) to read stimulus ATF file and get start/stop

	Return:
		df of spikes within sin stimulus
	"""
	df = ba.analysisDf
	if ba.stimDict is not None:
		#print(ba.stimDict)
		stimStartSeconds = ba.stimDict['stimStartSeconds']
		durSeconds = ba.stimDict['durSeconds']
		startSec = stimStartSeconds
		stopSec = startSec + durSeconds
		try:
			df = df[ (df['peak_sec']>=startSec) & (df['peak_sec']<=stopSec)]
		except (KeyError) as e:
			logger.error(e)

	return df

def plotStats(ba):
	"""
	Plot xxx
	"""
	df = reduce(ba)

	noiseAmpList = [0, 0.5, 1, 1.5]
	cvISI_list = [None] * len(noiseAmpList)
	cvISI_invert_list = [None] * len(noiseAmpList)
	pSpike_list = [None] * len(noiseAmpList)

	for idx in range(ba.numSweeps):
		#abf.setSweep(idx)
		dfStats = df[ df['sweep']== idx]

		peakSec = dfStats['peak_sec']
		peakVal = dfStats['peak_val']

		# given 20 peaks, calculate "probability of spike"
		# 20 spikes yields p=1
		# 10/20 spikes yields p=0.5

		nSinPeaks = 20 # number of peaks in sin wave
		pSpike = len(dfStats)/nSinPeaks
		isiSec = np.diff(peakSec)
		cvISI = np.std(isiSec) / np.mean(isiSec)
		cvISI_invert = 1 / cvISI
		print(f'{idx} n:{len(dfStats)} pSpike:{pSpike} cvISI:{cvISI} cvISI_invert:{cvISI_invert}')

		cvISI_list[idx] = cvISI
		cvISI_invert_list[idx] = cvISI_invert
		pSpike_list[idx] = pSpike

	# plot
	fig, axs = plt.subplots(3, 1, sharex=True, figsize=(8, 6))
	axs[0].plot(noiseAmpList, cvISI_list, 'o-k')
	axs[1].plot(noiseAmpList, cvISI_invert_list, 'o-k')
	axs[2].plot(noiseAmpList, pSpike_list, 'o-k')

	axs[0].set_ylabel('cvISI')
	axs[1].set_ylabel('1/cvISI')
	axs[2].set_ylabel('Prob(spike) per sin peak')
	#
	axs[2].set_xlabel('Noise Amp (pA)')

def plotShotPlot(df):
	"""
	Plot ISI(i) versus ISI(i-1)

	Args:
		df (DataFrame): already reduce()
	"""
	file = df['file'].values[0]

	fig, axs = plt.subplots(1, 1, sharex=True, figsize=(8, 6))
	axs = [axs]
	fig.suptitle(file)

	colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k']

	sweeps = df['sweep'].unique()
	print(f'plotShotPlot() num sweeps:{len(sweeps)} {sweeps}')
	for sweepIdx, sweep in enumerate(sweeps):
		dfPlot = df[ df['sweep'] == sweep ]

		peakSec = dfPlot['peak_sec']
		isi = np.diff(peakSec)
		isi_minusOne = isi[0:-2]
		isi = isi[1:-1]

		axs[0].scatter(isi, isi_minusOne, marker='o', c=colors[sweepIdx])

		axs[0].set_ylabel('ISI -1 (s)')
		axs[0].set_xlabel('ISI (s)')

def plotPhaseHist(ba, axs=None, hue='sweep'):
	"""
	Plot hist of spike arrival times as function of phase/angle within sine wave

	Args:
		df (DataFrame): assuming spikes are reduced to just stimulus
		startSec (float):
		freq (float):
	"""
	if ba.stimDict is None:
		return

	df = ba.analysisDf
	if df is None:
		return

	df = reduce(ba)

	# grab freq and startSec from header
	stimStartSeconds = ba.stimDict['stimStart_sec']
	stimFreq = ba.stimDict['stimFreq']  # TODO: will not work if we are stepping frequency
	stimAmp = ba.stimDict['stimAmp']

	file = df['file'].values[0]

	sinInterval = 1 / stimFreq
	hueList = df[hue].unique()
	numHue = len(hueList)
	bins = 'auto'

	print(f'plotPhaseHist() stimStartSeconds:{stimStartSeconds} stimFreq:{stimFreq} sinInterval:{sinInterval} bins:{bins}')

	if axs is None:
		numSubplot = len(hueList)
		fig, axs = plt.subplots(numSubplot, 1, sharex=True, figsize=(8, 6))
		fig.suptitle(file)

	fs = ba.dataPointsPerMs * 1000  # 10000
	durSec = 1 / stimFreq
	Xs = np.arange(fs*durSec) / fs  # x/time axis, we should always be able to create this from (dur, fs)
	sinData = stimAmp * np.sin(2*np.pi*(Xs)*stimFreq)
	xPlot = Xs * stimFreq  #/ fs  # normalize to interval [0,1] fpr plotting

	for idx,oneHue in enumerate(hueList):
		dfPlot = df[ df[hue]==oneHue ]
		peakSecs = dfPlot['peak_sec']
		peakSecs -= stimStartSeconds
		#peakPhase =  peakSecs - (peakSecs/sinInterval).astype(int)
		peakPhase_float = peakSecs/sinInterval
		peakPhase = peakPhase_float - peakPhase_float.astype(int)

		# debug
		'''
		tmpDf = pd.DataFrame()
		tmpDf['peakSecs'] = peakSecs
		tmpDf['peakPhase_float'] = peakPhase_float
		tmpDf['peakPhase_int'] = peakPhase_float.astype(int)
		tmpDf['peakPhase'] = peakPhase
		print(idx, tmpDf.head())
		'''

		#sns.histplot(x='ipi_ms', data=dfPlot, bins=numBins, ax=axs[idx])
		axs[idx].hist(peakPhase, bins=bins, density=False)

		axsSin = axs[idx].twinx()
		axsSin.plot(xPlot, sinData, 'r')

		'''
		if idx == len(hueList)-1:
			axs[idx].set_xlabel('Phase')
		'''

		# label x-axis of subplots
		lastSweep = idx == (numHue - 1)
		if lastSweep:
			axs[idx].set_xlabel('Phase')
		else:
			axs[idx].spines['bottom'].set_visible(False)
			axs[idx].tick_params(axis="x", labelbottom=False) # no labels
			axs[idx].set_xlabel('')

	#plotStimFileParams(ba)

def isiStats(ba, hue='sweep'):
	df = ba.analysisDf
	if df is None:
		return

	df = reduce(ba)

	statList = []

	statStr = 'ipi_ms'

	hueList = df[hue].unique()
	for idx,oneHue in enumerate(hueList):
		dfPlot = df[ df[hue]==oneHue ]
		ipi_ms = dfPlot[statStr]

		meanISI = np.nanmean(ipi_ms)
		stdISI = np.nanstd(ipi_ms)
		cvISI = stdISI / meanISI
		cvISI_inv = np.nanstd(1/ipi_ms) / np.nanmean(1/ipi_ms)

		oneDict = {
			'file': ba.fileName,
			'stat': statStr,
			'count': len(ipi_ms),
			'minISI': np.nanmin(ipi_ms),
			'maxISI': np.nanmax(ipi_ms),
			'stdISI': round(stdISI,3),
			'meanISI': round(np.nanmean(ipi_ms),3),
			'medianISI': round(np.nanmedian(ipi_ms),3),
			'cvISI': cvISI,
			'cvISI_inv': cvISI_inv,

		}

		statList.append(oneDict)

	#
	retDf = pd.DataFrame(statList)
	return retDf

def plotHist(ba, axs=None, hue='sweep'):

	df = ba.analysisDf
	if df is None:
		return

	df = reduce(ba)

	file = df['file'].values[0]

	# same number of bins per hist
	bins = 'auto' #12
	statStr = 'ipi_ms'

	hueList = df[hue].unique()
	numHue = len(hueList)

	# plot one hist per subplot
	if axs is None:
		numSubplot = len(hueList)
		fig, axs = plt.subplots(numSubplot, 1, sharex=True, figsize=(8, 6))
		fig.suptitle(file)


	for idx,oneHue in enumerate(hueList):
		dfPlot = df[ df[hue]==oneHue ]

		# hist of isi
		# screws up x-axis line at 0 (annoying !!!)
		sns.histplot(x=statStr, data=dfPlot, bins=bins, ax=axs[idx])
		# screws up x-axis line at 0 (annoying !!!)
		#xStatVal = dfPlot[statStr]
		#axs[idx].hist(xStatVal, bins=bins, density=False)

		'''
		if idx == len(hueList)-1:
			axs[idx].set_xlabel('ipi_ms')
		else:
			axs[idx].set_xlabel('')
		'''

		# label x-axis of subplots
		lastSweep = idx == (numHue - 1)
		if lastSweep:
			axs[idx].set_xlabel(statStr)
		else:
			axs[idx].spines['bottom'].set_visible(False)
			axs[idx].tick_params(axis="x", labelbottom=False) # no labels
			axs[idx].set_xlabel('')

	'''
	logger.info('')
	dfStat = isiStats(ba)
	print(dfStat)

	plotStimFileParams(ba)
	'''

def plotRaw(ba, axs=None):

	numSweeps = ba.numSweeps

	if axs is None:
		fig, axs = plt.subplots(numSweeps, 1, sharex=True, figsize=(8, 6))
		if numSweeps == 1:
			axs = [axs]

			fig.suptitle(ba.fileName)

	rightAxs = [None] * numSweeps

	#print(ba.fileName)

	for idx in ba.sweepList:
		ba.setSweep(idx)

		rightAxs[idx] = axs[idx].twinx()
		#rightAxs[idx].set_ylabel(abf.sweepLabelC)
		rightAxs[idx].set_ylabel('DAC (nA)')
		rightAxs[idx].plot(ba.sweepX, ba.sweepC, 'r', lw=.5, zorder=0)

		#axs[idx].set_ylabel(abf.sweepLabelY)
		axs[idx].set_ylabel('Vm (mV)')
		axs[idx].plot(ba.sweepX, ba.sweepY, 'k', lw=1.0, zorder=10)

		if ba.analysisDf is not None:
			df = reduce(ba)
			# just one sweep
			#df = ba.analysisDf
			dfPlot = df[ df['sweep']== idx]

			peakSec = dfPlot['peak_sec']
			peakVal = dfPlot['peak_val']

			# given 20 peaks, calculate "probability of spike"
			# 20 spikes yields p=1
			# 10/20 spikes yields p=0.5

			'''
			nSinPeaks = 20 # number of peaks in sin wave
			pSpike = len(dfPlot)/nSinPeaks
			isiSec = np.diff(peakSec)
			cvISI = np.std(isiSec) / np.mean(isiSec)
			cvISI_invert = 1 / cvISI
			# round
			cvISI = round(cvISI,3)
			cvISI_invert = round(cvISI_invert,3)
			print(f'  {idx} plotRaw() n:{len(dfPlot)} pSpike:{pSpike} cvISI:{cvISI} cvISI_invert:{cvISI_invert}')
			'''

			axs[idx].plot(peakSec, peakVal, 'o')

			footSec = dfPlot['foot_sec']
			footVal = dfPlot['foot_val']
			axs[idx].plot(footSec, footVal, 'og')

		# label x-axis of subplots
		lastSweep = idx == (numSweeps - 1)
		if lastSweep:
			axs[idx].set_xlabel('Time (s)')
		else:
			axs[idx].spines['bottom'].set_visible(False)
			axs[idx].tick_params(axis="x", labelbottom=False) # no labels
			axs[idx].set_xlabel('')

		# get the zorder correct
		axs[idx].set_zorder(rightAxs[idx].get_zorder()+1)
		axs[idx].set_frame_on(False)

	#
	plt.tight_layout()

if __name__ == '__main__':
	# one trial of spont
	#path = '/media/cudmore/data/stoch-res/2021_12_06_0002.abf'
	# sin stim
	path = '/media/cudmore/data/stoch-res/2021_12_06_0005.abf'

	# second day of recording
	#path = '/media/cudmore/data/stoch-res/20211209/2021_12_09_0010.abf'  # 194 seconds of baseline
	path = '/media/cudmore/data/stoch-res/20211209/2021_12_09_0011.abf'  # 1pA/1Hz/2pA step
	#path = '/media/cudmore/data/stoch-res/20211209/2021_12_09_0012.abf'  # 1pA/5Hz/2pA step

	ba = load(path)

	plotStimFileParams(ba)

	#print('stimDict:', ba._stimDict)  # can be none

	thresholdValue = -10
	detect(ba, thresholdValue=thresholdValue)

	dfStat = isiStats(ba)
	print('dfStat')
	print(dfStat)

	sys.exit(1)
	# if we have a stimulus file
	if ba.stimDict is not None:
		stimStartSeconds = ba.stimDict['stimStart_sec']
		frequency = ba.stimDict['stimFreq']  # TODO: will not work if we are stepping frequency
		durSeconds = ba.stimDict['sweepDur_sec']

		df = reduce(ba)

		plotPhaseHist(df, stimStartSeconds, frequency)

	#plotRaw(ba)

	#plotStats(ba)  # not working

	#plotHist(df)
	#plotShotPlot(df)

	#
	plt.show()
