"""
Important, had to modify parsing comment of atf

see abb in:
	/home/cudmore/Sites/SanPy/sanpy_env/lib/python3.8/site-packages/pyabf/atf.py", line 63
"""
import os
import numpy as np

import matplotlib.pyplot as plt

from colinAnalysis import bAnalysis2

def load():

	path = '/media/cudmore/data/stoch-res/2021_12_06_0002.abf'
	path = '/media/cudmore/data/stoch-res/2021_12_06_0005.abf'
	path = '/Users/cudmore/box/data/stoch-res/2021_12_06_0005.abf'
	stimulusFileFolder = None #'/media/cudmore/data/stoch-res' #os.path.split(path)[0]

	ba = bAnalysis2(path, stimulusFileFolder=stimulusFileFolder)
	print(ba)

	return ba

def detect(ba, thresholdValue = -20):

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
	df = ba.analysisDf
	startSec = 5
	stopSec = 25
	df = df[ (df['peak_sec']>=startSec) & (df['peak_sec']<=stopSec)]
	return df

def plot(ba):
	abf = ba.abf
	numSweeps = len(abf.sweepList)

	df = reduce(ba)

	fig, axs = plt.subplots(numSweeps, 1, sharex=True, figsize=(8, 6))
	rightAxs = [None] * numSweeps

	noiseAmpList = [0, 0.5, 1, 1.5]
	cvISI_list = [None] * len(noiseAmpList)
	cvISI_invert_list = [None] * len(noiseAmpList)
	pSpike_list = [None] * len(noiseAmpList)

	for idx in abf.sweepList:
		abf.setSweep(idx)

		rightAxs[idx] = axs[idx].twinx()
		rightAxs[idx].set_ylabel(abf.sweepLabelC)
		rightAxs[idx].plot(abf.sweepX, abf.sweepC, 'r', lw=.5, zorder=0)

		axs[idx].set_ylabel(abf.sweepLabelY)
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
			print(f'{idx} n:{len(dfPlot)} pSpike:{pSpike} cvISI:{cvISI} cvISI_invert:{cvISI_invert}')

			cvISI_list[idx] = cvISI
			cvISI_invert_list[idx] = cvISI_invert
			pSpike_list[idx] = pSpike

			axs[idx].plot(peakSec, peakVal, 'o')

			footSec = dfPlot['foot_sec']
			footVal = dfPlot['foot_val']
			axs[idx].plot(footSec, footVal, 'og')

			# TODO: reduce by stim (start, dur)
			# calculate:
			#	spikes
			#	isi
			#	cv
			#	etc

		# get the zorder correct
		axs[idx].set_zorder(rightAxs[idx].get_zorder()+1)
		axs[idx].set_frame_on(False)

	#
	plt.tight_layout()

	fig, axs = plt.subplots(3, 1, sharex=True, figsize=(8, 6))
	axs[0].plot(noiseAmpList, cvISI_list, 'o-k')
	axs[1].plot(noiseAmpList, cvISI_invert_list, 'o-k')
	axs[2].plot(noiseAmpList, pSpike_list, 'o-k')

	axs[0].set_ylabel('cvISI')
	axs[1].set_ylabel('1/cvISI')
	axs[2].set_ylabel('Prob(spike) per sin peak')
	#
	axs[2].set_xlabel('Noise Amp (pA)')

	#
	plt.show()

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
	ba = load()

	thresholdValue = -10
	detect(ba, thresholdValue=thresholdValue)

	#reduce(ba)

	plot(ba)
