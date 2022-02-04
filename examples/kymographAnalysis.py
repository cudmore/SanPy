"""
Author: Robert Cudmore
Date: 20220115

Code to analyze Fernandos Rabiit Ca++ transients

Notes:
	- I am guessing the best ROI, need to modify manually for each file
	- I am using one set of detection params with minor tweeks for a few files
	- I have rejected some files that show monotonic dcrease in Ca++ signal (in all cases are Thaps, not control)

Grim Conclusions:
	Variance in Ca spike is due to the spike number
	Control is always first and Thap(s) is always second

	This is why we see reduced variances in Thp versus control
"""

import os, sys, math

import numpy as np
import pandas as pd

import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib as mpl
mpl.rcParams['axes.spines.right'] = False
mpl.rcParams['axes.spines.top'] = False

#mpl.rcParams.update({'font.size': 10})

SMALL_SIZE = 8
MEDIUM_SIZE = 10
BIGGER_SIZE = 12
plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

import sanpy
import sanpy.analysisPlot

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def myFindPeaks3(xSec, yData, startSec, stopSec):
	"""
	Find the peak in data between [startPnt,stopPnt)

	Args:
		data (npndarray):
		startPnt (int):
		stopPnt (int):
	"""
	xMask = (xSec>=startSec) & (xSec<stopSec)
	firstPnt = np.where(xMask==True)[0][0]
	#print('firstPnt:', firstPnt)
	#sys.exit(1)
	#clip = data[startPnt:stopPnt]
	clip = yData[xMask]
	peakPnt = np.argmax(clip)
	peakPnt += firstPnt
	peakVal = yData[peakPnt]
	return peakPnt, peakVal

def old_myFindPeaks2(xSec, yData, startPnt, stopPnt):
	"""
	Find the peak in data between [startPnt,stopPnt)

	Args:
		data (npndarray):
		startPnt (int):
		stopPnt (int):
	"""
	yClip = yData[startPnt:stopPnt]
	peakPnt = np.argmax(yClip)
	peakPnt += startPnt
	peakVal = yData[peakPnt]
	return peakPnt, peakVal

g_kd = 1200
g_caRest = 125
def convertTomM(yData):
	#kd = 1200
	#caRest = 125
	ret = g_kd*yData / (g_kd/g_caRest + 1 - yData)
	return ret

def getFileList(path):
	count = 0
	fileList = []
	for root, subdirs, files in os.walk(path):
		#print('analysisDir.getFileList() count:', count)
		#print('  ', root)
		#print('  ', subdirs)
		#print('  ', files)
		count += 1
		for file in files:
			if file.endswith('.tif'):
				oneFile = os.path.join(root, file)
				#print('  ', oneFile)
				fileList.append(oneFile)
	#
	fileList = sorted(fileList)
	return fileList

def myDespine(ax):
	"""Remove right and top lines on plots.
	"""
	ax.spines['right'].set_visible(False)
	ax.spines['top'].set_visible(False)
	#ax.spines['left'].set_visible(False)
	#ax.spines['bottom'].set_visible(False)

def myPlotScatter(df, xStat, yStat, color=None, ax=None):
	"""plot a scatter from masterDf of all ba analysis
	"""
	if ax is None:
		fig, ax = plt.subplots(1, 1, figsize=(4, 4))
	g = sns.lineplot(x=xStat, y=yStat, color=color, style='file',
						legend=False, marker='o', data=df, ax=ax)
	# put legend outside plot
	#plt.legend(bbox_to_anchor=(0.9, 1), loc=2, borderaxespad=0.)
	#g.legend(loc='center left', bbox_to_anchor=(1, 0.5))

def loadWithAnalysisDir(path):
	# load from saved cell db
	# this is awesome !!!

	ad = sanpy.analysisDir(path, autoLoad = True)

	#print(ad._df)

	baList = []
	for idx in range(ad.numFiles):
		# 'I' column to flag (include, exclude) is coming up 'False' for exclude, '2' for include ???
		includeExclude = ad._df.loc[idx, 'I']
		if includeExclude == False:
			print('  row col I at ', idx, 'was reject')
			continue

		# allowAutoLoad=False, will not load if it was not analyzed/saved in sanpy !!!
		ba = ad.getAnalysis(idx, allowAutoLoad=False)
		if ba is None:
			# was not analyzed in sanpy and saved into hd5
			continue
		#print('!!!!!!!!!!!!!!!!!!!', ba)

		# checking all manual set param have held
		# seems to be ok
		'''
		detectionDict = ba.detectionDict
		print('detectionDIct is:')
		for k,v in detectionDict.items():
			# v is a dist
			#print(f"  {k} : {v['currentValue']} {v['description']}")
			print(f"  {k} : {v['currentValue']}")
		'''

		'''
		rowDict = ad.getRowDict(idx)
		#print(rowDict)
		mvThreshold = rowDict['mvThreshold']
		path = rowDict['path']  # TODO: Switch to relative path to make data portable
		kLeft = rowDict['kLeft']
		kTop = rowDict['kTop']
		kRight = rowDict['kRight']
		kBottom = rowDict['kBottom']
		theRect = [kLeft, kTop, kRight, kBottom]

		print(f'{idx} mvThreshold:{mvThreshold} kRect:{theRect} path:{path}')
		'''

		path = ba._path

		parent = os.path.split(path)[0]  # corresponds to Olympus export folder
		grandparent = os.path.split(parent)[0]
		condition = os.path.split(grandparent)[1]

		# as we load, assign condition based on directory structure
		#detectionClass['condition'] = condition
		ba.detectionDict['condition'] = condition

		# load
		# no need to do this, we got it from analysisDir !!!!
		'''
		ba = sanpy.bAnalysis(path)

		detectionClass = sanpy.bDetection() # gets default detection class

		fileName = os.path.split(path)[1]
		if fileName == '220110n_0032.tif':
			# default is 170 ms
			print("xxx", fileName, "detectionClass['refractory_ms']:", detectionClass['refractory_ms'])
			detectionClass['refractory_ms'] = 1500

		detectionType = sanpy.bDetection.detectionTypes.mv
		detectionClass['condition'] = condition
		detectionClass['detectionType'] = detectionType  # set detection type to ('dvdt', 'vm')
		detectionClass['dvdtThreshold'] = math.nan
		detectionClass['mvThreshold'] = mvThreshold
		detectionClass['peakWindow_ms'] = 500
		detectionClass['halfWidthWindow_ms'] = 1000

		ba.spikeDetect(detectionClass=detectionClass)
		'''

		# all we do is add it to the list
		baList.append(ba)

	#
	print('baList has', len(baList), 'files')
	return baList

def old_load(path):
	fileList = getFileList(path)
	# load and analyze, some files are tweaked for thir analysis
	baList = []
	for idx, file in enumerate(fileList):
		# debug
		if 1:
			if idx==4:
				break

		ba = sanpy.bAnalysis(file)

		#detectionClass = sanpy.bDetection() # gets default detection class

		# get condition from grandparent folder in ['Thapsigargin', 'Control']
		# file path looks like this:
		#  /media/cudmore/data/rabbit-ca-transient/Control/220110n_0049.tif.frames/220110n_0049.tif
		parent = os.path.split(file)[0]  # corresponds to Olympus export folder
		grandparent = os.path.split(parent)[0]
		condition = os.path.split(grandparent)[1]

		#print(condition, file)
		if condition == 'Control':
			mvThreshold = 1.4
		elif condition == 'Thapsigargin':
			mvThreshold = 1.1
		else:
			print(f'XXX ERROR: Case not taken for condition: "{condition}"')

		detectionClass = sanpy.bDetection() # gets default detection class

		# special cases
		fileName = os.path.split(file)[1]
		if fileName == '220110n_0017.tif':
			mvThreshold = 1.2
		elif fileName == '220110n_0021.tif':
			mvThreshold = 1.2
		elif fileName == '220110n_0023.tif':
			mvThreshold = 1.2
		elif fileName == '220110n_0024.tif':
			mvThreshold = 1.2
		elif fileName == '220110n_0032.tif':
			# default is 170 ms
			print("xxx", fileName, "detectionClass['refractory_ms']:", detectionClass['refractory_ms'])
			detectionClass['refractory_ms'] = 1500
			# todo: set detection refractory_ms
		elif fileName == '220110n_0055.tif':
			mvThreshold = 1.05

		detectionType = sanpy.bDetection.detectionTypes.mv
		detectionClass['condition'] = condition
		detectionClass['detectionType'] = detectionType  # set detection type to ('dvdt', 'vm')
		detectionClass['dvdtThreshold'] = math.nan
		detectionClass['mvThreshold'] = mvThreshold
		detectionClass['peakWindow_ms'] = 500

		ba.spikeDetect(detectionClass=detectionClass)
		baList.append(ba)

	return baList

def loadFromDb(path):
	"""
	load from SanPy folder DB

	TODO: This is managing 2x lists, one from db and other from abf/tif files in folder.
	path (str): folder
	"""
	baList = []

	dbPath = os.path.join(path, 'sanpy_recording_db.csv')
	dfFolder = pd.read_csv(dbPath)

	fileList = getFileList(path)
	baList = []
	for idx, filePath in enumerate(fileList):
		# debug
		if 0:
			if idx==4:
				break

		parent = os.path.split(filePath)[0]  # corresponds to Olympus export folder
		grandparent = os.path.split(parent)[0]
		condition = os.path.split(grandparent)[1]

		fileName  = os.path.split(filePath)[1]

		ba = sanpy.bAnalysis(filePath)

		oneFile = dfFolder[ dfFolder['File']==fileName ]
		mvThreshold = oneFile['mvThreshold'].values[0]
		kLeft = oneFile['kLeft'].values[0]
		kTop = oneFile['kTop'].values[0]
		kRight = oneFile['kRight'].values[0]
		kBottom = oneFile['kBottom'].values[0]
		theRect = [kLeft, kTop, kRight, kBottom]

		#print(oneFile)
		print(idx, fileName, mvThreshold, theRect)

		ba._updateTifRoi(theRect)

		detectionClass = sanpy.bDetection() # gets default detection class
		detectionType = sanpy.bDetection.detectionTypes.mv
		detectionClass['condition'] = condition
		detectionClass['detectionType'] = detectionType  # set detection type to ('dvdt', 'vm')
		detectionClass['dvdtThreshold'] = math.nan
		detectionClass['mvThreshold'] = mvThreshold
		detectionClass['peakWindow_ms'] = 500
		detectionClass['preSpikeClipWidth_ms'] = 100
		detectionClass['postSpikeClipWidth_ms'] = 1000
		detectionClass['refractory_ms'] = 700

		if fileName == '220110n_0032.tif':
			# default is 170 ms
			print("xxx", fileName, "detectionClass['refractory_ms']:", detectionClass['refractory_ms'])
			detectionClass['refractory_ms'] = 1500
			# todo: set detection refractory_ms

		# detect
		ba.spikeDetect(detectionClass=detectionClass)

		#
		# convert each ba sweepY to nM
		#ba._sweepY[:,0] = convertTomM(ba._sweepY[:,0])  # assuming one sweep

		# does not work because oneDf is constructed on fly
		# append some columns for nano-molar
		#oneDf = ba.asDataFrame()
		#peakVal = oneDf['peakVal']
		#peak_nM = convertTomM(peakVal)
		#oneDf['peak_nM'] = peak_nM

		baList.append(ba)
	#
	return baList

'''
def run2():
	path = '/media/cudmore/data/rabbit-ca-transient/jan-18-2022'
	baList = loadWithAnalysisDir(path)
'''

def run():
	convertToMolar = True
	convertMolarStr = 'f/f_0'
	saveFolder = 'rabbit-raw'
	if convertToMolar:
		convertMolarStr = f'kd:{g_kd} caRest:{g_caRest}'
		saveFolder = 'rabbit-molar'

	badList = []

	# all this sent to fernando
	if 0:
		saveFolder += '-jan-12-2022'
		path = '/media/cudmore/data/rabbit-ca-transient/jan-12-2022'
		#path = '/Volumes/t2/data/rabbit-ca-transient/jan-12-2022'
		# load and analyze
		baList = loadFromDb(path)
		# for jan-12-2022
		badList = [
			'220110n_0056.tif',
			'220110n_0064.tif',
			'220110n_0065.tif',
			'220110n_0069.tif',
			'22011on_0071.tif',
		]

	if 1:
		# new to load from my manual analysis in sanpy 20220125, to analyze jan-18 data
		saveFolder += '-jan-18-2022'
		path = '/media/cudmore/data/rabbit-ca-transient/jan-18-2022'
		#path = '/Volumes/t2/data/rabbit-ca-transient/jan-18-2022'
		baList = loadWithAnalysisDir(path)

	# make output folder
	if not os.path.isdir(saveFolder):
		os.mkdir(saveFolder)

	# convert unints of sweepy to molar
	# all analysis is done, peakVal (in particular) is still in f/f0
	for ba in baList:
		# convert each ba sweepY to nM
		if convertToMolar:
			ba._sweepY[:,0] = convertTomM(ba._sweepY[:,0])  # assuming one sweep

	#sns.despine()  # remove top/right lines in plots

	#
	# plot
	#yUnits0 = '[Ca2+]i (nM^2)'
	# $10^1$
	#yUnits0 = '[Ca$^2$$^+$]$_i$ ($nM^2$)'
	yUnits0 = ''

	meanPeakList = []
	meanPeakTimeList = []  # ms
	varPeakList = []
	varPeakTimeList = []  # ms
	var_at_meanPeakTimeList = []  # ms
	condList = []
	percentChangeList = [] # list of % change in peakVal to compare with corresponding variance
	finalAnalysisList = []  # list of ba

	# plot all clips (mean, var) in one plot, one line for each recording
	figSummary, axsSummary = plt.subplots(2, 2, sharex=True, figsize=(4, 4))
	#figSummary.suptitle(f'One line per recording in {yUnits0} kd:{g_kd} caRest:{g_caRest}')
	figSummary.suptitle(f'1) One line per recording units:{convertMolarStr}')
	for tmpAxs in axsSummary.ravel():
		myDespine(tmpAxs)

	for idx, ba in enumerate(baList):
		print(ba)

		#
		# convert each ba sweepY to nM
		#ba._sweepY[:,0] = convertTomM(ba._sweepY[:,0])  # assuming one sweep

		fileName = ba.getFileName()
		if fileName in badList:
			print('  REJECTING')
			continue

		condition = ba.detectionDict['condition']

		condList.append(condition)
		finalAnalysisList.append(ba)

		# plot each recording in new figure
		# we save one of these per recording
		# (i) raw intensity, (ii) amp summary (iii) raw clips, ,(iv) mean (v) variance
		fig = plt.figure(figsize =([6, 11]))  #constrained_layout=True)
		#figTitle = f'{condition} {fileName} kd:{g_kd} caRest:{g_caRest}'
		figTitle = f'{condition} {fileName} units:{convertMolarStr}'
		fig.suptitle(figTitle)
		gs = GridSpec(5, 2, figure=fig)
		gs.update(wspace = 1.5, hspace = 0.3)
		ax0 = fig.add_subplot(gs[0, :])
		ax10 = fig.add_subplot(gs[1, :1])  # 3 col
		ax11 = fig.add_subplot(gs[1, 1:2])  # 3 col
		#ax12 = fig.add_subplot(gs[1, 2:3])  # 3 col
		ax2 = fig.add_subplot(gs[2, :])
		ax3 = fig.add_subplot(gs[3, :])
		ax4 = fig.add_subplot(gs[4, :])
		axs = [ax0, ax10, ax2, ax3, ax4]

		'''
		fig, axs = plt.subplots(5, 1, sharex=False, figsize=(8, 6))
		figTitle = f'{condition} {fileName}'
		fig.suptitle(figTitle)
		for tmpAxs in axs:
			myDespine(tmpAxs)
		'''

		ap = sanpy.analysisPlot.bAnalysisPlot(ba)

		# plot raw data with detected spikes
		ap.plotSpikes(plotThreshold=True, plotPeak=True, plotStyle=None, ax=axs[0])
		axs[0].set_ylabel(yUnits0)

		# plot summary amplitude for each spike
		oneDf = ba.asDataFrame()  # returns a copy

		# don't use analyzed peakVal (we might have swapped units of sweepY)
		# just pull peak using peakPnt and existing sweepY
		peakPnt = oneDf['peakPnt']
		peakVal_plot = ba.sweepY[peakPnt]
		oneDf['peakVal_plot'] = peakVal_plot

		#col0Axs = ax10
		#myPlotScatter(oneDf, 'thresholdSec', 'peak_nM', color='k', ax=col0Axs)
		col0Axs = ax10
		myPlotScatter(oneDf, 'thresholdSec', 'peakVal_plot', color='k', ax=col0Axs)
		col1Axs = ax11
		myPlotScatter(oneDf, 'thresholdSec', 'timeToPeak_ms', color='k', ax=col1Axs)
		#col2Axs = ax12
		#myPlotScatter(oneDf, 'peakVal', 'peakHeight', color='k', ax=col2Axs)

		# get list of peak_nM and calculate % change at end compared to start
		tmpPeak_plot = oneDf['peakVal_plot'].values
		#print(tmpPeak_nM.shape, tmpPeak_nM)
		tmpNumPeak = tmpPeak_plot.shape[0]
		if tmpNumPeak < 4:
			percentChangeList.append(math.nan)
		else:
			tmpStartPeak = np.nanmean(tmpPeak_plot[0:2])  # first two
			tmpStopPeak = np.nanmean(tmpPeak_plot[-2:-1])  # last two
			percentChange = tmpStopPeak * 100 / tmpStartPeak
			percentChange = round(percentChange)
			percentChangeList.append(percentChange)
			titleStr = f'{percentChange} % Change'
			col0Axs.set_title(titleStr)
		#
		startMetaSec = 0.0
		stopMetaSec = 0.5
		#startMetaPnt = int(startMetaSec * 1000 * ba.dataPointsPerMs)
		#stopMetaPnt = int(stopMetaSec * 1000 * ba.dataPointsPerMs)

		#
		# plot clips (raw, mean, var, SD)
		markersize = 4

		# put (time, mean, var) clips into dataframe and save at end
		dfTmpSaveMeanVar = pd.DataFrame()

		rawClipAxs = axs[2]
		xMean, yMean = ap.plotClips(plotType='Raw', ax=rawClipAxs)
		rawClipAxs.set_ylabel('')
		if xMean is None:
			logger.error(f'No Spikes for {ba}')
			meanPeakList.append(np.nan)
			meanPeakTimeList.append(np.nan)
			varPeakList.append(np.nan)
			varPeakTimeList.append(np.nan)
			var_at_meanPeakTimeList.append(np.nan)
			continue

		#peakMeanPnt, peakMeanVal = myFindPeaks2(xMean, yMean, startMetaPnt, stopMetaPnt)
		#peakMeanPnt, peakMeanVal = myFindPeaks(xMean, yMean, startMetaSec, stopMetaSec)
		#axs[1].plot(xMean[peakMeanPnt], peakMeanVal, 'or', markersize=3)
		#axs[1].set_ylabel(yUnits0)

		meanClipAxs = axs[3]
		xMean, yMean = ap.plotClips(plotType='Mean', ax=meanClipAxs)
		#
		dfTmpSaveMeanVar['time_sec'] = np.round(xMean,3)
		dfTmpSaveMeanVar['mean_clip'] = yMean # np.round(yMean,3)
		#
		#peakMeanPnt, peakMeanVal = myFindPeaks2(xMean, yMean, startMetaPnt, stopMetaPnt)
		peakMeanPnt, peakMeanVal = myFindPeaks3(xMean, yMean, startMetaSec, stopMetaSec)
		xPeakMean = xMean[peakMeanPnt]
		axs[3].plot(xPeakMean, peakMeanVal, '^b', markersize=markersize)
		axs[3].set_ylabel('Mean')

		xVar, yVar = ap.plotClips(plotType='Var', ax=axs[4])
		#
		#dfTmpSaveMeanVar['time'] = xMean
		dfTmpSaveMeanVar['var_clip'] = yVar # np.round(yVar,3)
		#
		#peakVarPnt, peakVarVal = myFindPeaks2(xVar, yVar, startMetaPnt, stopMetaPnt)
		peakVarPnt, peakVarVal = myFindPeaks3(xVar, yVar, startMetaSec, stopMetaSec)
		xPeakVar = xVar[peakVarPnt]
		axs[4].plot(xPeakVar, peakVarVal, 'or', markersize=markersize)
		axs[4].set_ylabel('Var')

		# the variance at same point of peak in mean
		var_at_meanPeakTime = yVar[peakMeanPnt]  # we save this
		xPeakVar2 = xVar[peakMeanPnt]
		axs[4].plot(xPeakVar2, var_at_meanPeakTime, '^b', markersize=markersize)

		#
		# save dfTmpSaveMeanVar with (time, mean, var)
		# used this on 20220125 to send fernando mean/var of clips
		tmpFileName = os.path.splitext(ba.getFileName())[0] + '_' + condition + '.csv'
		#tmpDfSaveMeanVarFile = f'rabbit/{condition}/{tmpFileName}'
		tmpTmpFolder = os.path.join(saveFolder, condition)
		if not os.path.isdir(tmpTmpFolder):
			os.mkdir(tmpTmpFolder)
		tmpDfSaveMeanVarFile = os.path.join(tmpTmpFolder, tmpFileName)
		print('!!! saving:', tmpDfSaveMeanVarFile, len(dfTmpSaveMeanVar))
		dfTmpSaveMeanVar.to_csv(tmpDfSaveMeanVarFile)

		# plot all clips (mean, var, sd) in one plot
		print('condition:', condition)
		if condition == 'Control':
			summaryStyle = '-k'
		elif condition in ['Thapsigargin', 'TG']:
			summaryStyle = '-r'
		# mean
		if condition == 'Control':
			colIdx = 0
		else:
			colIdx = 1
		axsSummary[0][colIdx].plot(xMean, yMean, summaryStyle)
		axsSummary[0][colIdx].set_ylabel('Mean')
		# var
		axsSummary[1][colIdx].plot(xVar, yVar, summaryStyle)
		axsSummary[1][colIdx].set_ylabel('Var')
		# sd
		'''
		axsSummary[2][colIdx].plot(xSD, ySD, summaryStyle)
		axsSummary[2][colIdx].set_ylabel(yUnitsSD)
		'''

		#
		# TODO: Keep track of time of each peak in (mean, var, SD)

		# if sweepY was converted with convertTomM() then these values are in MOLAR
		meanPeakList.append(peakMeanVal)
		meanPeakTimeList.append(xPeakMean)
		varPeakList.append(peakVarVal)
		varPeakTimeList.append(xPeakVar)
		# the variance at same point of peak in mean
		#var_at_meanPeakTime = yVar[peakMeanPnt]
		var_at_meanPeakTimeList.append(var_at_meanPeakTime)

		# save the figure
		if 1:
			#saveFolder = 'rabbit'
			fileName = ba.getFileName()
			saveName = os.path.splitext(fileName)[0] # + '_raw.png'
			saveName += '_' + condition + '.png'

			# prepend idx because xxx date is wonky
			saveName = str(idx) + '_' + saveName

			savePath = os.path.join(saveFolder, saveName)
			logger.info(f'saving: {savePath}')
			fig.savefig(savePath, dpi=300)

		#
		plt.close()  #

	# pool all ba analysis df
	# if analysis was done before convertTomM() these are in f/f_0 units
	dfMaster = pd.DataFrame()
	for ba in finalAnalysisList:
		df = ba.asDataFrame()
		if dfMaster is None:
			dfMaster = df
		else:
			dfMaster = dfMaster.append(df, ignore_index=True)
	#

	#
	# this does not work loading from analysis dir
	# we need to set condition in analysis df
	if 0:
		#
		# scatter of (peak value, peak height) versus spike time
		# to determine stable fluorescent signal
		# TODO: for each recording (i) fit to line and (ii) determine % change form start to finish
		# todo: (something like) plot var and SD for each of these (fernando hinted at it)
		fig12, ax12 = plt.subplots(2, 2, figsize=(4, 8))
		#fig12.suptitle(f'One Line Per Recording kd:{g_kd} caRest:{g_caRest}')
		fig12.suptitle(f'2) One Line Per Recording units:{convertMolarStr}')

		#
		# plot all peaks across all cells, speerate by ocndition
		condList = dfMaster['condition'].unique()
		# control
		condOne = condList[0]
		dfControl = dfMaster[ dfMaster['condition']==condOne ]
		myPlotScatter(dfControl, 'thresholdSec', 'peakVal', color='k', ax=ax12[0][0])
		myPlotScatter(dfControl, 'thresholdSec', 'peakHeight', color='k', ax=ax12[1][0])
		# Thapsigargin
		condTwo = condList[1]
		dfThap = dfMaster[ dfMaster['condition']==condTwo ]
		myPlotScatter(dfThap, 'thresholdSec', 'peakVal', color='r', ax=ax12[0][1])
		myPlotScatter(dfThap, 'thresholdSec', 'peakHeight', color='r', ax=ax12[1][1])

		print('plotting pooled conditions')
		print('  finalAnalysisList:', len(finalAnalysisList))
		print('  dfControl:', len(dfControl))
		print('  dfThap:', len(dfThap))

	#
	#columns = ['Condition', 'meanPeak', 'varPeak', 'numSpikes', 'file']
	#df = pd.DataFrame(columns=columns)
	dictList = []
	for idx, ba in enumerate(finalAnalysisList):
		mvThreshold = ba.detectionDict['mvThreshold']
		cond1 = ba.detectionDict['condition']
		#cond2 = condList[idx]  # sanity check
		meanPeak = meanPeakList[idx]
		meanPeakTime = meanPeakTimeList[idx]
		varPeak = varPeakList[idx]
		varPeakTime = varPeakTimeList[idx]
		var_at_meanPeakTime = var_at_meanPeakTimeList[idx]
		percentChangeInPeakVal = percentChangeList[idx]
		oneDict = {
			'saveFolder': saveFolder,
			'convertToMolar': convertToMolar,
			'condition': cond1,
			'mvThreshold': mvThreshold,
			'meanPeak': meanPeak,
			'meanPeakTime': meanPeakTime,
			'varPeak': varPeak,
			'varPeakTime': varPeakTime,
			'var_at_meanPeakTime': var_at_meanPeakTime,# variance at same point as peak in mean
			'percentChangeInPeakVal': percentChangeInPeakVal,
			'numSpikes': ba.numSpikes,
			'file': ba.getFileName(),
			'kd': '',
			'caRest': '',
			'startMetaSec': startMetaSec,  # start/stop of peak detection in mean/var clip
			'stopMetaSec': stopMetaSec,
		}
		if convertToMolar:
			oneDict['kd'] = g_kd
			oneDict['caRest'] = g_caRest

		dictList.append(oneDict)
		#print(f'{idx} {cond1} {cond2} {meanPeak} {varPeak} {ba}')
	df = pd.DataFrame(dictList)
	print('final df before plotting var as function of condition')
	print(df)

	# save summary df, one row per files
	saveFinalDfFile = os.path.join(saveFolder, 'kymSummary.csv')
	df.to_csv(saveFinalDfFile)

	#ax = sns.pointplot(x="condition", y="varPeak", data=df)
	#sns.catplot(x="condition", y="varPeak", data=df)  # does not take ax param

	# todo: plot var_at_meanPeakTime
	figVar, axsVar = plt.subplots(1, 2, sharex=False, figsize=(6, 4))
	figVar.suptitle(f'units:{convertMolarStr}')
	myDespine(axsVar[0])
	myDespine(axsVar[1])

	# plot 1
	sns.stripplot(x='condition',
		y='varPeak',
		data=df,
		alpha=0.3,
		jitter=0.2,
		color='k',
		ax=axsVar[0]);

	sns.boxplot(showmeans=True,
				meanline=True,
				meanprops={'color': 'r', 'ls': '-', 'lw': 2},
				medianprops={'visible': False},
				whiskerprops={'visible': False},
				zorder=10,
				x="condition",
				y="varPeak",
				data=df,
				showfliers=False,
				showbox=False,
				showcaps=False,
				ax=axsVar[0])

	# plot 2
	sns.stripplot(x='condition',
		y='var_at_meanPeakTime',
		data=df,
		alpha=0.3,
		jitter=0.2,
		color='k',
		ax=axsVar[1]);

	sns.boxplot(showmeans=True,
				meanline=True,
				meanprops={'color': 'r', 'ls': '-', 'lw': 2},
				medianprops={'visible': False},
				whiskerprops={'visible': False},
				zorder=10,
				x="condition",
				y="var_at_meanPeakTime",
				data=df,
				showfliers=False,
				showbox=False,
				showcaps=False,
				ax=axsVar[1])

	#
	saveVarFigFile = 'pooledVar.jpg'
	saveVarFigPath = os.path.join(saveFolder, saveVarFigFile)
	logger.info(f'saving saveVarFigPath: {saveVarFigPath}')
	figVar.savefig(saveVarFigPath, dpi=300)

	#
	# mean peak versus var peak (var peak here is max in variance, not at same itme as peak in mean)
	figVar2, axsVar2 = plt.subplots(3, 1, sharex=False, figsize=(6, 8))
	figVar2.suptitle(f'units:{convertMolarStr}')
	myDespine(axsVar2[0])
	myDespine(axsVar2[1])
	myDespine(axsVar2[2])
	# population meanPeak vs varPeak
	yStat = 'varPeak'
	yStat = 'var_at_meanPeakTime'
	sns.scatterplot(x='meanPeak', y=yStat, hue='condition', data=df, ax=axsVar2[0])
	sns.scatterplot(x='numSpikes', y=yStat, hue='condition', data=df, ax=axsVar2[1])
	sns.scatterplot(x='percentChangeInPeakVal', y=yStat, hue='condition', data=df, ax=axsVar2[2])

	# save it
	tmpInternalControlsFile = 'pooledInternalControls.png'
	saveControlsFigPath = os.path.join(saveFolder, tmpInternalControlsFile)
	logger.info(f'saving saveControlsFigPath: {saveControlsFigPath}')
	figVar2.savefig(saveControlsFigPath, dpi=300)

	#plt.tight_layout()
	plt.show()

def tooLong():
	pass

if __name__ == '__main__':
	# was working for all analysis until 20220125
	run()

	# switching to try and load precice detection params from analysisDir
	#run2()
