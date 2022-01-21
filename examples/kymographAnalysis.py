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

import sanpy
import sanpy.analysisPlot

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def myFindPeaks(xSec, yData, startSec, stopSec):
	"""
	NOT WORKING !!!

	Find the peak in data between [startPnt,stopPnt)

	Args:
		data (npndarray):
		startPnt (int):
		stopPnt (int):
	"""
	xMask = (xSec>=startSec) & (xSec<stopSec)
	firstPnt = np.where(xMask==True)[0]
	#clip = data[startPnt:stopPnt]
	clip = yData[xMask]
	peakPnt = np.argmax(clip)
	peakPnt += firstPnt
	peakVal = yData[peakPnt]
	return peakPnt, peakVal

def myFindPeaks2(xSec, yData, startPnt, stopPnt):
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

def convertTomM(yData):
	kd = 1200
	caRest = 125
	ret = kd*yData / (kd/caRest + 1 - yData)
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

def myPlotScatter(df, xStat, yStat, ax=None):
	"""plot a scatter from masterDf of all ba analysis
	"""
	if ax is None:
		fig, ax = plt.subplots(1, 1, figsize=(4, 4))
	g = sns.lineplot(x=xStat, y=yStat, hue='condition', style='file', marker='o', data=df, ax=ax)
	# put legend outside plot
	#plt.legend(bbox_to_anchor=(0.9, 1), loc=2, borderaxespad=0.)
	g.legend(loc='center left', bbox_to_anchor=(1, 0.5))

def loadWithAnalysisDir(path):
	ad = sanpy.analysisDir(path, autoLoad = True)
	baList = []
	for idx in range(ad.numFiles):
		rowDict = ad.getRowDict(idx)
		#print(rowDict)
		mvThreshold = rowDict['mvThreshold']
		path = rowDict['path']
		kLeft = rowDict['kLeft']
		kTop = rowDict['kTop']
		kRight = rowDict['kRight']
		kBottom = rowDict['kBottom']
		theRect = [kLeft, kTop, kRight, kBottom]

		print(f'{idx} mvThreshold:{mvThreshold} kRect:{theRect} path:{path}')

		parent = os.path.split(path)[0]  # corresponds to Olympus export folder
		grandparent = os.path.split(parent)[0]
		condition = os.path.split(grandparent)[1]

		# load
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
		baList.append(ba)

	#
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

		detectionClass = sanpy.bDetection() # gets default detection class

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
			print(f'XXX ERROR: Case not taken for condition: "{condition}""')

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

def run():
	path = '/media/cudmore/data/rabbit-ca-transient/jan-12-2022'
	#path = '/media/cudmore/data/rabbit-ca-transient'

	# new
	#baList = loadWithAnalysisDir(path)

	dbPath = os.path.join(path, 'sanpy_recording_db.csv')
	dfFolder = pd.read_csv(dbPath)

	oneFile = dfFolder[ dfFolder['File']=='220110n_0052.tif' ]
	mvThreshold = oneFile['mvThreshold'].values[0]
	kLeft = oneFile['kLeft'].values[0]
	kTop = oneFile['kTop'].values[0]
	kRight = oneFile['kRight'].values[0]
	kBottom = oneFile['kBottom'].values[0]
	theRect = [kLeft, kTop, kRight, kBottom]

	print(oneFile)
	print(mvThreshold, theRect)

	sys.exit()

	# old
	baList = old_load(path)

	#
	# plot (raw, clips, variance of clips)
	# We analyze everything but just plot a subset (we remove files that do not have stable f/f0
	badList = [
		'220110n_0056.tif',
		'220110n_0064.tif',
		'220110n_0065.tif',
		'220110n_0069.tif',
		'22011on_0071.tif',
	]
	#badList = []

	sns.despine()  # remove top/right lines in plots

	#
	# plot
	yUnits0 = '[Ca2+]i (nM^2)'
	# $10^1$
	yUnits0 = '[Ca$^2$$^+$]$_i$ ($nM^2$)'

	yUnitsMean = 'Mean'
	yUnitsVariance = 'Var'
	yUnitsSD = 'SD'

	meanPeakList = []
	varPeakList = []
	condList = []
	finalAnalysisList = []  # list of ba
	# plot all clips (raw,mean/var/sd) in one plot, one line for each recording
	figSummary, axsSummary = plt.subplots(3, 1, sharex=False, figsize=(4, 4))
	figSummary.suptitle(f'One line per recording in {yUnits0}')
	for tmpAxs in axsSummary:
		myDespine(tmpAxs)

	for idx, ba in enumerate(baList):
		print(ba)

		#
		# convert each ba sweepY to nM
		ba._sweepY[:,0] = convertTomM(ba._sweepY[:,0])  # assuming one sweep

		fileName = ba.getFileName()
		if fileName in badList:
			print('  REJECTING')
			continue

		condition = ba.detectionDict['condition']

		condList.append(condition)
		finalAnalysisList.append(ba)

		# plot each recording in new figure
		# (i) raw intensity, (ii) raw clips, ,(iii) mean (iv) variance, (v) sd
		fig, axs = plt.subplots(5, 1, sharex=False, figsize=(8, 6))
		figTitle = f'{condition} {fileName}'
		fig.suptitle(figTitle)
		for tmpAxs in axs:
			myDespine(tmpAxs)

		ap = sanpy.analysisPlot.bAnalysisPlot(ba)

		# plot raw data with detected spikes
		ap.plotSpikes(plotThreshold=True, plotPeak=True, plotStyle=None, ax=axs[0])
		axs[0].set_ylabel(yUnits0)

		startMetaSec = 0.1
		stopMetaSec = 1.5
		startMetaPnt = int(startMetaSec * 1000 * ba.dataPointsPerMs)
		stopMetaPnt = int(stopMetaSec * 1000 * ba.dataPointsPerMs)

		#
		# plot clips (raw, mean, var, SD)
		markersize = 4

		xMean, yMean = ap.plotClips(plotType='Raw', ax=axs[1])
		if xMean is None:
			logger.error(f'No Spikes for {ba}')
			meanPeakList.append(np.nan)
			varPeakList.append(np.nan)
			continue

		peakMeanPnt, peakMeanVal = myFindPeaks2(xMean, yMean, startMetaPnt, stopMetaPnt)
		#peakMeanPnt, peakMeanVal = myFindPeaks(xMean, yMean, startMetaSec, stopMetaSec)
		#axs[1].plot(xMean[peakMeanPnt], peakMeanVal, 'or', markersize=3)
		#axs[1].set_ylabel(yUnits0)

		xMean, yMean = ap.plotClips(plotType='Mean', ax=axs[2])
		peakMeanPnt, peakMeanVal = myFindPeaks2(xMean, yMean, startMetaPnt, stopMetaPnt)
		#peakVarPnt, peakVarVal = myFindPeaks(xVar, yVar, startMetaSec, stopMetaSec)
		axs[2].plot(xMean[peakMeanPnt], peakMeanVal, 'or', markersize=markersize)
		axs[2].set_ylabel(yUnitsMean)

		xVar, yVar = ap.plotClips(plotType='Var', ax=axs[3])
		peakVarPnt, peakVarVal = myFindPeaks2(xVar, yVar, startMetaPnt, stopMetaPnt)
		#peakVarPnt, peakVarVal = myFindPeaks(xVar, yVar, startMetaSec, stopMetaSec)
		axs[3].plot(xVar[peakVarPnt], peakVarVal, 'or', markersize=markersize)
		axs[3].set_ylabel(yUnitsVariance)

		# SD is squar root of var
		xSD, ySD = ap.plotClips(plotType='SD', ax=axs[4])
		peakSDPnt, peakSDVal = myFindPeaks2(xSD, ySD, startMetaPnt, stopMetaPnt)
		#peakVarPnt, peakVarVal = myFindPeaks(xVar, yVar, startMetaSec, stopMetaSec)
		axs[4].plot(xSD[peakSDPnt], peakSDVal, 'or', markersize=markersize)
		axs[4].set_ylabel(yUnitsSD)

		# plot all clips (mean, var, sd) in one plot
		if condition == 'Control':
			summaryStyle = '-k'
		elif condition == 'Thapsigargin':
			summaryStyle = '-r'
		# mean
		axsSummary[0].plot(xMean, yMean, summaryStyle)
		axsSummary[0].set_ylabel(yUnitsMean)
		# var
		axsSummary[1].plot(xVar, yVar, summaryStyle)
		axsSummary[1].set_ylabel(yUnitsVariance)
		# var
		axsSummary[2].plot(xSD, ySD, summaryStyle)
		axsSummary[2].set_ylabel(yUnitsSD)

		#
		# TODO: Keep track of time of each peak in (mean, var, SD)

		meanPeakList.append(peakMeanVal)
		varPeakList.append(peakVarVal)

		# save the figure
		if 1:
			saveFolder = 'rabbit'
			fileName = ba.getFileName()
			saveName = os.path.splitext(fileName)[0] # + '_raw.png'
			saveName += '_' + condition + '.png'
			savePath = os.path.join(saveFolder, saveName)
			logger.info(f'saving: {savePath}')
			fig.savefig(savePath, dpi=300)

		#
		plt.close()  #

	# pool all ba analysis df
	dfMaster = pd.DataFrame()
	for ba in finalAnalysisList:
		df = ba.asDataFrame()
		if dfMaster is None:
			dfMaster = df
		else:
			dfMaster = dfMaster.append(df, ignore_index=True)
	#
	#print(dfMaster)

	#
	# scatter of peak height to determine stable fluorescent signal
	# TODO: for each recording (i) fit to line and (ii) determine % change form start to finish
	# todo: (something like) plot var and SD for each of these (fernando hinted at it)
	fig12, ax12 = plt.subplots(2, 1, figsize=(4, 8))
	fig12.suptitle('One Line Per Recording')
	myPlotScatter(dfMaster, 'thresholdSec', 'peakVal', ax=ax12[0])
	myPlotScatter(dfMaster, 'thresholdSec', 'peakHeight', ax=ax12[1])

	#
	#plt.show()

	#columns = ['Condition', 'meanPeak', 'varPeak', 'numSpikes', 'file']
	#df = pd.DataFrame(columns=columns)
	dictList = []
	for idx, ba in enumerate(finalAnalysisList):
		cond1 = ba.detectionDict['condition']
		#cond2 = condList[idx]  # sanity check
		meanPeak = meanPeakList[idx]
		varPeak = varPeakList[idx]
		oneDict = {
			'condition': cond1,
			'meanPeak': meanPeak,
			'varPeak': varPeak,
			'numSpikes': ba.numSpikes,
			'file': ba.getFileName(),
		}
		dictList.append(oneDict)
		#print(f'{idx} {cond1} {cond2} {meanPeak} {varPeak} {ba}')
	df = pd.DataFrame(dictList)
	print(df)

	#ax = sns.pointplot(x="condition", y="varPeak", data=df)
	#sns.catplot(x="condition", y="varPeak", data=df)  # does not take ax param

	figVar, axsVar = plt.subplots(1, 1, sharex=False, figsize=(4, 4))
	myDespine(axsVar)
	sns.stripplot(x='condition',
		y='varPeak',
		data=df,
		alpha=0.3,
		jitter=0.2,
		color='k',
		ax=axsVar);

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
				ax=axsVar)

	figVar2, axsVar2 = plt.subplots(2, 1, sharex=False, figsize=(4, 8))
	myDespine(axsVar2[0])
	myDespine(axsVar2[1])
	sns.scatterplot(x='meanPeak', y='varPeak', hue='condition', data=df, ax=axsVar2[0])

	#figVar3, axsVar3 = plt.subplots(1, 1, sharex=False, figsize=(4, 4))
	sns.scatterplot(x='numSpikes', y='varPeak', hue='condition', data=df, ax=axsVar2[1])
	#
	plt.tight_layout()
	plt.show()

if __name__ == '__main__':
	run()
