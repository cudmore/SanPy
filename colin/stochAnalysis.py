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
from sanpy.interface.plugins.stimGen2 import buildStimDict  # readFileParams

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def load(path):

	stimulusFileFolder = os.path.split(path)[0] #'/media/cudmore/data/stoch-res' #os.path.split(path)[0]

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

def old_plotStimFileParams(ba):
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
	df = ba.asDataFrame()
	if ba.stimDict is not None:
		#print(ba.stimDict)
		'''
		stimStartSeconds = ba.stimDict['stimStartSeconds']
		durSeconds = ba.stimDict['durSeconds']
		startSec = stimStartSeconds
		stopSec = startSec + durSeconds
		'''

		startSec, stopSec = ba.getStimStartStop()

		try:
			df = df[ (df['peak_sec']>=startSec) & (df['peak_sec']<=stopSec)]
		except (KeyError) as e:
			logger.error(f'my key error: {e}')

	return df

def old_plotStats(ba):
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

def plotPhaseHist(ba3, axs=None, hue='sweep', saveFolder=None):
	"""
	Plot hist of spike arrival times as function of phase/angle within sine wave

	Args:
		df (DataFrame): assuming spikes are reduced to just stimulus
		startSec (float):
		freq (float):
	"""
	if ba3.stimDict is None:
		return

	'''
	df = ba3.asDataFrame()
	if df is None:
		return
	'''

	#logger.info(f'hue: "{hue}"')

	df = reduce(ba3)

	if len(df)==0:
		logger.error(f'got no spikes after reduce')
		return

	# grab freq and startSec from header
	stimStartSeconds = ba3.stimDict['stimStart_sec']
	stimFreq = ba3.stimDict['stimFreq']  # TODO: will not work if we are stepping frequency
	stimAmp = ba3.stimDict['stimAmp']

	file = df['file'].values[0]

	numSweeps = ba3.numSweeps

	sinInterval = 1 / stimFreq
	hueList = df[hue].unique()
	numHue = len(hueList)
	bins = 'auto'

	print(f'plotPhaseHist() stimStartSeconds:{stimStartSeconds} stimFreq:{stimFreq} sinInterval:{sinInterval} bins:{bins}')

	if axs is None:
		numSubplot = numSweeps
		fig, axs = plt.subplots(numSubplot, 1, sharex=True, figsize=(8, 6))
		fig.suptitle(file)
		axs[numSubplot-1].set_xlabel('Phase')

	fs = ba3.dataPointsPerMs * 1000  # 10000
	durSec = 1 / stimFreq
	Xs = np.arange(fs*durSec) / fs  # x/time axis, we should always be able to create this from (dur, fs)
	sinData = stimAmp * np.sin(2*np.pi*(Xs)*stimFreq)
	xPlot = Xs * stimFreq  #/ fs  # normalize to interval [0,1] fpr plotting

	# for gianni
	gMasterDf = None

	#for idx,oneHue in enumerate(hueList):
	for idx in range(numSweeps):
		if not idx in hueList:
			continue

		oneHue = idx

		dfPlot = df[ df[hue]==oneHue ]

		if len(dfPlot) < 2:
			logger.error(f'sweep {idx} only had {len(dfPlot)} spikes ... not plotting')
			continue

		peakSecs = dfPlot['peakSec']
		peakSecs -= stimStartSeconds
		#peakPhase =  peakSecs - (peakSecs/sinInterval).astype(int)
		peakPhase_float = peakSecs/sinInterval
		peakPhase = peakPhase_float - peakPhase_float.astype(int)

		# for gianni
		thisDf = pd.DataFrame()
		thisDf['peakPhase'] = peakPhase # to get the number of rows correct
		thisDf.insert(0, 'sweep', oneHue)  # thisDf['sweep'] = oneHue
		thisDf.insert(0, 'filename', ba3.getFileName())  # thisDf['filename'] = ba.fileName
		if gMasterDf is None:
			gMasterDf = thisDf
		else:
			gMasterDf = gMasterDf.append(thisDf, ignore_index=True)

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
		lastSweep = idx == (numSweeps - 1)
		if lastSweep:
			axs[idx].set_xlabel('Phase')
		else:
			#axs[idx].spines['bottom'].set_visible(False)
			axs[idx].tick_params(axis="x", labelbottom=False) # no labels
			axs[idx].set_xlabel('')

	#plotStimFileParams(ba)

	if saveFolder is not None:
		saveName = os.path.splitext(ba3.getFileName())[0] + '_phase.png'
		savePath = os.path.join(saveFolder, saveName)
		logger.info(f'saving: {savePath}')
		fig.savefig(savePath, dpi=300)

	# for gianni
	saveName = os.path.splitext(ba3.getFileName())[0] + '_gianni.csv'
	savePath = os.path.join(saveFolder, saveName)
	logger.info(f'gianni savePath: {savePath}')
	print(gMasterDf)
	gMasterDf.to_csv(savePath, index=False)

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

def plotHist(ba3, axs=None, hue='sweep', saveFolder=None):
	"""
	Args:

		ba (bAnalysis3)
	"""

	'''
	df = ba3.asDataFrame()
	if df is None:
		logger.error(f'did not find analysis for {ba}')
		return
	'''

	df = reduce(ba3)

	if len(df)==0:
		logger.error(f'after reduce, got empty df')
		return

	file = ba3.getFileName()  # df['file'].values[0]

	# same number of bins per hist
	bins = 'auto' #12
	statStr = 'isi_ms'

	numSweeps = ba3.numSweeps

	#hueList = df[hue].unique()
	#numHue = len(hueList)

	#logger.info(f'plotting hueList: {hueList}')

	# plot one hist per subplot
	if axs is None:
		numSubplot = numSweeps
		fig, axs = plt.subplots(numSubplot, 1, sharex=True, figsize=(8, 6))
		fig.suptitle(file)
		axs[numSubplot-1].set_xlabel('ISI (ms)')


	#for idx,oneHue in enumerate(hueList):
	for idx in range(numSweeps):
		#if not idx in hueList:
		#	continue

		oneHue = idx

		#hueList = df[hue].unique()

		dfPlot = df[ df[hue]==oneHue ]

		if len(dfPlot) < 2:
			logger.error(f'sweep {idx} only had {len(dfPlot)} spikes ... not plotting')
			continue

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
		lastSweep = idx == (numSweeps - 1)
		if lastSweep:
			axs[idx].set_xlabel(statStr)
		else:
			#axs[idx].spines['bottom'].set_visible(False)
			axs[idx].tick_params(axis="x", labelbottom=False) # no labels
			axs[idx].set_xlabel('')

	if saveFolder is not None:
		saveName = os.path.splitext(ba3.getFileName())[0] + '_hist.png'
		savePath = os.path.join(saveFolder, saveName)
		logger.info(f'saving: {savePath}')
		fig.savefig(savePath, dpi=300)

	'''
	logger.info('')
	dfStat = isiStats(ba)
	print(dfStat)

	plotStimFileParams(ba)
	'''

def plotRaw(ba, showDetection=True, showDac=True, axs=None, saveFolder=None):
	"""
	Plot Raw data.

	Args:
		ba (bAnalysis2)
		showDetection (bool): Overlay detection parameters
		showDac (bool): Overlay Stimulus File DAC stimulus
		axs (matpltlib): If given then plot in this axes
	"""

	numSweeps = ba.numSweeps

	if axs is None:
		fig, axs = plt.subplots(numSweeps, 1, sharex=True, sharey=True, figsize=(8, 6))
		if numSweeps == 1:
			axs = [axs]

		fig.suptitle(ba.getFileName())

	# If we are plotting Dac
	rightAxs = [None] * numSweeps

	# keep track of x/y min of each plot to make them all the same
	yRawMin = 1e9
	yRawMax = -1e9

	yDacMin = 1e9
	yDacMax = -1e9

	for idx in ba.sweepList:
		ba.setSweep(idx)

		lastSweep = idx == (numSweeps - 1)

		try:
			sweepC = ba.sweepC
		except (ValueError) as e:
			sweepC = None

		if showDac and sweepC is not None:
			rightAxs[idx] = axs[idx].twinx()
			rightAxs[idx].spines['right'].set_visible(True)
			if lastSweep:
				rightAxs[idx].set_ylabel('DAC (nA)')
			rightAxs[idx].plot(ba.sweepX, sweepC, 'r', lw=.5, zorder=0)

			yMin = np.min(sweepC)
			if yMin < yDacMin:
				yDacMin = yMin
			yMax = np.max(sweepC)
			if yMax > yDacMax:
				yDacMax = yMax

		if lastSweep:
			axs[idx].set_ylabel('Vm (mV)')

		axs[idx].plot(ba.sweepX, ba.sweepY, lw=0.5, zorder=10)

		yMin = np.min(ba.sweepY)
		if yMin < yRawMin:
			yRawMin = yMin
		yMax = np.max(ba.sweepY)
		if yMax > yRawMax:
			yRawMax = yMax

		if showDetection and ba.analysisDf is not None:
			#df = reduce(ba)
			df = ba.analysisDf
			dfPlot = df[ df['sweep']== idx]

			peakSec = dfPlot['peak_sec']
			peakVal = dfPlot['peak_val']

			axs[idx].plot(peakSec, peakVal, 'ob', markersize=3, zorder=999)

			footSec = dfPlot['foot_sec']
			footVal = dfPlot['foot_val']
			#axs[idx].plot(footSec, footVal, 'og', markersize=3, zorder=999)

		# label x-axis of subplots
		if lastSweep:
			axs[idx].set_xlabel('Time (s)')
		else:
			#axs[idx].spines['bottom'].set_visible(False)
			axs[idx].tick_params(axis="x", labelbottom=False) # no labels
			axs[idx].set_xlabel('')

		# get the zorder correct
		if showDac and sweepC is not None:
			axs[idx].set_zorder(rightAxs[idx].get_zorder()+1)
			axs[idx].set_frame_on(False)

	# set common y min/max
	# expand left axis by a percentage %
	percentExpand = 0.05
	thisExpand = (yRawMax - yRawMin) * percentExpand
	yRawMin -= thisExpand
	yRawMax += thisExpand
	for idx in ba.sweepList:
		axs[idx].set_ylim(yRawMin, yRawMax)
		if showDac and sweepC is not None:
			rightAxs[idx].set_ylim(yDacMin, yDacMax)

	#
	plt.tight_layout()

	if saveFolder is not None:
		saveName = os.path.splitext(ba.fileName)[0] + '_raw.png'
		savePath = os.path.join(saveFolder, saveName)
		logger.info(f'saving: {savePath}')
		fig.savefig(savePath, dpi=300)

def plotRaw3(ba3, showDetection=True, showDac=True, axs=None, saveFolder=None):
	"""
	Plot Raw data.

	Args:
		ba3 (bAnalysis3)
		showDetection (bool): Overlay detection parameters
		showDac (bool): Overlay Stimulus File DAC stimulus
		axs (matpltlib): If given then plot in this axes
	"""

	numSweeps = ba3.numSweeps

	if axs is None:
		fig, axs = plt.subplots(numSweeps, 1, sharex=True, sharey=True, figsize=(8, 6))
		if numSweeps == 1:
			axs = [axs]

		fig.suptitle(ba3.getFileName())

	# If we are plotting Dac
	rightAxs = [None] * numSweeps

	# keep track of x/y min of each plot to make them all the same
	yRawMin = 1e9
	yRawMax = -1e9

	yDacMin = 1e9
	yDacMax = -1e9

	for idx in ba3.sweepList:
		ba3.setSweep(idx)

		lastSweep = idx == (numSweeps - 1)

		try:
			sweepC = ba3.sweepC
		except (ValueError) as e:
			sweepC = None

		if showDac and sweepC is not None:
			rightAxs[idx] = axs[idx].twinx()
			rightAxs[idx].spines['right'].set_visible(True)
			if lastSweep:
				rightAxs[idx].set_ylabel('DAC (nA)')
			rightAxs[idx].plot(ba3.sweepX, sweepC, c='tab:gray', lw=.5, zorder=0)

			yMin = np.min(sweepC)
			if yMin < yDacMin:
				yDacMin = yMin
			yMax = np.max(sweepC)
			if yMax > yDacMax:
				yDacMax = yMax

		if lastSweep:
			axs[idx].set_ylabel('Vm (mV)')

		axs[idx].plot(ba3.sweepX, ba3.sweepY, lw=0.5, zorder=10)

		yMin = np.min(ba3.sweepY)
		if yMin < yRawMin:
			yRawMin = yMin
		yMax = np.max(ba3.sweepY)
		if yMax > yRawMax:
			yRawMax = yMax

		if showDetection and ba3.isAnalyzed is not None and ba3.numSpikes>0:
			#df = reduce(ba)
			#df = ba3.analysisDf
			df = ba3.asDataFrame()

			dfPlot = df[ df['sweep']== idx]

			peakSec = dfPlot['peakSec']
			peakVal = dfPlot['peakVal']
			axs[idx].plot(peakSec, peakVal, 'ob', markersize=3, zorder=999)

			footSec = dfPlot['thresholdSec']
			footVal = dfPlot['thresholdVal']
			axs[idx].plot(footSec, footVal, 'og', markersize=3, zorder=999)

		# label x-axis of subplots
		if lastSweep:
			axs[idx].set_xlabel('Time (s)')
		else:
			#axs[idx].spines['bottom'].set_visible(False)
			axs[idx].tick_params(axis="x", labelbottom=False) # no labels
			axs[idx].set_xlabel('')

		# get the zorder correct
		if showDac and sweepC is not None:
			axs[idx].set_zorder(rightAxs[idx].get_zorder()+1)
			axs[idx].set_frame_on(False)

	# set common y min/max
	# expand left axis by a percentage %
	percentExpand = 0.05
	thisExpand = (yRawMax - yRawMin) * percentExpand
	yRawMin -= thisExpand
	yRawMax += thisExpand
	for idx in ba3.sweepList:
		axs[idx].set_ylim(yRawMin, yRawMax)
		if showDac and sweepC is not None:
			rightAxs[idx].set_ylim(yDacMin, yDacMax)

	#
	plt.tight_layout()

	if saveFolder is not None:
		saveName = os.path.splitext(ba3.getFileName())[0] + '_raw.png'
		savePath = os.path.join(saveFolder, saveName)
		logger.info(f'saving: {savePath}')
		fig.savefig(savePath, dpi=300)

def run0():
	# one trial of spont
	#path = '/media/cudmore/data/stoch-res/2021_12_06_0002.abf'
	# sin stim
	path = '/media/cudmore/data/stoch-res/2021_12_06_0005.abf'

	# second day of recording
	#path = '/media/cudmore/data/stoch-res/20211209/2021_12_09_0010.abf'  # 194 seconds of baseline
	#path = '/media/cudmore/data/stoch-res/20211209/2021_12_09_0011.abf'  # 1pA/1Hz/2pA step
	path = '/media/cudmore/data/stoch-res/20211209/2021_12_09_0012.abf'  # 1pA/5Hz/2pA step

	ba = load(path)

	# old_plotStimFileParams(ba)

	#print('stimDict:', ba._stimDict)  # can be none

	thresholdValue = -10
	detect(ba, thresholdValue=thresholdValue)

	dfStat = isiStats(ba)
	print('dfStat')
	print(dfStat)

	#sys.exit(1)

	# if we have a stimulus file
	if ba.stimDict is not None:
		stimStartSeconds = ba.stimDict['stimStart_sec']
		frequency = ba.stimDict['stimFreq']  # TODO: will not work if we are stepping frequency
		durSeconds = ba.stimDict['sweepDur_sec']

		#df = reduce(ba)

		#plotPhaseHist(df, stimStartSeconds, frequency)
		plotPhaseHist(ba)

	#plotRaw(ba)

	#plotStats(ba)  # not working

	#plotHist(df)
	#plotShotPlot(df)

	#
	plt.show()

def plotCV(csvPath):
	#csvPath = '/media/cudmore/data/stoch-res/11feb/analysis/isi_analysis.csv'
	df = pd.read_csv(csvPath)

	fileNames = df['file'].unique()

	numFiles = len(fileNames)

	numCol = 2
	numRow = round(numFiles/numCol)

	fig, axs = plt.subplots(numRow, numCol, sharex=True, sharey=True, figsize=(8, 10))
	axs = np.ravel(axs)

	statCol = 'cvISI_inv'  # cvISI
	statCol = 'cvISI'  # cvISI
	for idx, file in enumerate(fileNames):
		plotDf = df[ df['file']==file ]

		xPlot = plotDf['sweep']
		yPlot = plotDf[statCol]

		axs[idx].plot(xPlot, yPlot, 'o-k')

		axs[idx].title.set_text(file)

		axs[idx].set_ylabel('cvISI')
		axs[idx].set_xlabel('Noise')

	plt.show()

def test_bAnalysis3():
	"""
	TODO:
		1) Load bAnalysis from saved hf5 analysis folder (with saved analysis)
		2) Construct a bAnalysis3() from path
		3) swap in loaded (detection, analysis) into bAnalysis3
	"""
	import sanpy
	import colinAnalysis
	import stochAnalysis
	import matplotlib.pyplot as plt

	folderPath = '/media/cudmore/data/stoch-res/11feb'
	ad = sanpy.analysisDir(path=folderPath)
	baList = []
	for rowIdx,oneBa in enumerate(ad):
		#if rowIdx > 9:
		#	break
		oneBa = ad.getAnalysis(rowIdx)  # load from hdf file
		baList.append(oneBa)

	ba3List = []
	for ba in baList:
		baPath = ba.path
		ba3 = colinAnalysis.bAnalysis3(baPath, loadData=False, stimulusFileFolder=None)

		# swap in analysis loaded from hd5 !!!
		ba3.detectionClass = ba.detectionClass
		ba3.spikeDict = ba.spikeDict

		ba3List.append(ba3)

	print(f'we have {len(ba3List)} ba3')

	#path = '/media/cudmore/data/stoch-res/11feb/2022_02_11_0008.abf'
	#ba3 = colinAnalysis.bAnalysis3(path, loadData=True, stimulusFileFolder=None)

	dfMaster = None
	for idx, ba3 in enumerate(ba3List):
		print(f'file idx {idx}')
		print('   ba3:', ba3)

		numSweeps = ba3.numSweeps

		if numSweeps > 1:
			# works
			saveFolder = os.path.join(folderPath, 'analysis')
			if not os.path.isdir(saveFolder):
				os.mkdir(saveFolder)
			stochAnalysis.plotRaw3(ba3, showDetection=True, showDac=True, axs=None, saveFolder=saveFolder)
			plt.close()

			stochAnalysis.plotHist(ba3, saveFolder=saveFolder)
			plt.close()

			stochAnalysis.plotPhaseHist(ba3, saveFolder=saveFolder)
			plt.close()

		df_isi = ba3.isiStats() # can return none

		#print(df_isi)
		#print('')

		if dfMaster is None and df_isi is not None:
			dfMaster = df_isi
		elif df_isi is not None:
			dfMaster = pd.concat([dfMaster,df_isi], ignore_index=True)

	#
	#print(dfMaster)

	saveFile = os.path.join(folderPath, 'analysis')
	if not os.path.isdir(saveFile):
		os.mkdir(saveFile)
	saveFile = os.path.join(saveFile, 'isi_analysis.csv')
	print('=== saving:', saveFile)
	dfMaster.to_csv(saveFile)

	plotCV(saveFile)

	plt.show()

if __name__ == '__main__':
	# run0()

	# works
	test_bAnalysis3()

	# load saved csv and plot
	#plotCV()
