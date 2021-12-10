"""
Important, had to modify parsing comment of atf

see abb in:
	/home/cudmore/Sites/SanPy/sanpy_env/lib/python3.8/site-packages/pyabf/atf.py", line 63
"""
import os
import numpy as np
import seaborn as sns

import matplotlib.pyplot as plt

from colinAnalysis import bAnalysis2
from sanpy.interface.plugins.stimGen2 import readFileParams
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
		print(ba.analysisDf.head())

def reduce(ba):
	"""
	Reduce spikes based on start/stop of sin stimulus

	TODO:
		Use readFileParams(atfPath) to read stimulus ATF file and get start/stop

	Return:
		df of spikes within sin stimulus
	"""
	df = ba.analysisDf
	startSec = 5
	stopSec = 25
	df = df[ (df['peak_sec']>=startSec) & (df['peak_sec']<=stopSec)]
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
	fig, axs = plt.subplots(1, 1, sharex=True, figsize=(8, 6))
	axs = [axs]

	colors = ['r', 'g', 'b', 'k']

	sweeps = df['sweep'].unique()
	for sweepIdx, sweep in enumerate(sweeps):
		dfPlot = df[ df['sweep'] == sweep ]

		peakSec = dfPlot['peak_sec']
		isi = np.diff(peakSec)
		isi_minusOne = isi[0:-2]
		isi = isi[1:-1]

		axs[0].scatter(isi, isi_minusOne, marker='o', c=colors[sweepIdx])

		axs[0].set_ylabel('ISI -1 (s)')
		axs[0].set_xlabel('ISI (s)')

def plotPhaseHist(df, startSec, freq, hue='sweep'):
	"""
	Plot hist of spike arrival times as function of phase/angle within sine wave

	Args:
		df (DataFrame): assuming spikes are reduced to just stimulus
		startSec (float):
		freq (float):
	"""
	sinInterval = 1 / freq
	hueList = df[hue].unique()
	bins = 12

	numSubplot = len(hueList)
	fig, axs = plt.subplots(numSubplot, 1, sharex=True, figsize=(8, 6))

	for idx,oneHue in enumerate(hueList):
		dfPlot = df[ df[hue]==oneHue ]
		peakSecs = dfPlot['peak_sec']
		peakSecs -= startSec
		peakPhase =  peakSecs - (peakSecs/sinInterval).astype(int)

		#sns.histplot(x='ipi_ms', data=dfPlot, bins=numBins, ax=axs[idx])
		axs[idx].hist(peakPhase, bins=bins, density=True)

		if idx == len(hueList)-1:
			axs[idx].set_xlabel('Phase')

def plotHist(df, hue='sweep'):

	# plot on one hist
	#fig, axs = plt.subplots(1, 1, sharex=True, figsize=(8, 6))
	#axs = [axs]
	#hue = 'sweep'
	#sns.histplot(x='ipi_ms', data=df, hue=hue)

	# same number of bins per hist
	numBins = 12

	hueList = df[hue].unique()

	# plot one hist per subplot
	numSubplot = len(hueList)
	fig, axs = plt.subplots(numSubplot, 1, sharex=True, figsize=(8, 6))


	for idx,oneHue in enumerate(hueList):
		dfPlot = df[ df[hue]==oneHue ]
		'''
		peakSec = dfPlot['peak_sec']
		isiSec = np.diff(peakSec)
		cvISI = np.std(isiSec) / np.mean(isiSec)
		cvISI_invert = 1 / cvISI
		'''
		#dfPlot = df[ df['sweep']== idx]

		# hist of isi
		sns.histplot(x='ipi_ms', data=dfPlot, bins=numBins, ax=axs[idx])

def plotRaw(ba):
	abf = ba.abf
	numSweeps = len(abf.sweepList)
	df = reduce(ba)

	fig, axs = plt.subplots(numSweeps, 1, sharex=True, figsize=(8, 6))
	rightAxs = [None] * numSweeps

	for idx in abf.sweepList:
		abf.setSweep(idx)

		rightAxs[idx] = axs[idx].twinx()
		#rightAxs[idx].set_ylabel(abf.sweepLabelC)
		rightAxs[idx].set_ylabel('DAC (nA)')
		rightAxs[idx].plot(abf.sweepX, abf.sweepC, 'r', lw=.5, zorder=0)

		#axs[idx].set_ylabel(abf.sweepLabelY)
		axs[idx].set_ylabel('Vm (mV)')
		axs[idx].plot(abf.sweepX, abf.sweepY, 'k', lw=1.0, zorder=10)

		if ba.analysisDf is not None:
			# just one sweep
			#df = ba.analysisDf
			dfPlot = df[ df['sweep']== idx]

			peakSec = dfPlot['peak_sec']
			peakVal = dfPlot['peak_val']

			# given 20 peaks, calculate "probability of spike"
			# 20 spikes yields p=1
			# 10/20 spikes yields p=0.5

			nSinPeaks = 20 # number of peaks in sin wave
			pSpike = len(dfPlot)/nSinPeaks
			isiSec = np.diff(peakSec)
			cvISI = np.std(isiSec) / np.mean(isiSec)
			cvISI_invert = 1 / cvISI
			print(f'plotRaw() {idx} n:{len(dfPlot)} pSpike:{pSpike} cvISI:{cvISI} cvISI_invert:{cvISI_invert}')

			axs[idx].plot(peakSec, peakVal, 'o')

			footSec = dfPlot['foot_sec']
			footVal = dfPlot['foot_val']
			axs[idx].plot(footSec, footVal, 'og')

		# get the zorder correct
		axs[idx].set_zorder(rightAxs[idx].get_zorder()+1)
		axs[idx].set_frame_on(False)

	#
	plt.tight_layout()

	#
	#plt.show()

def plotFinal(ba):
	"""
	BROKEN
	"""
	abf = ba.abf

	#xMask = (ba.sweepX<=5) and (ba.seepsX<=25)

	numSweeps = len(abf.sweepList)
	for idx in abf.sweepList:
		abf.setSweep(idx)

		df = ba.analysisDf
		df = df[ df['sweep']== idx]

if __name__ == '__main__':
	path = '/media/cudmore/data/stoch-res/2021_12_06_0002.abf'
	# 0005.abf is 4 sweeps with increading noise
	#path = '/media/cudmore/data/stoch-res/2021_12_06_0005.abf'
	#path = '/Users/cudmore/box/data/stoch-res/2021_12_06_0005.abf'

	ba = load(path)

	print('stimDict:', ba._stimDict)  # can be none

	thresholdValue = -10
	detect(ba, thresholdValue=thresholdValue)

	# if we have a stimulus file
	if ba.stimDict is not None:
		stimStartSeconds = ba.stimDict['stimStartSeconds']
		frequency = ba.stimDict['frequency']  # TODO: will not work if we are stepping frequency
		durSeconds = ba.stimDict['durSeconds']

		df = reduce(ba)

		plotPhaseHist(df, stimStartSeconds, frequency)

	#plotStats(ba)
	#plotHist(df)
	#plotShotPlot(df)


	#
	plt.show()
