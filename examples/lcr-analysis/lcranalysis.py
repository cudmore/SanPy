# 20210128

import os, pprint
import numpy as np
import pandas as pd
import scipy.signal
import matplotlib.pyplot as plt
import tifffile
import pyabf

import lcrData

def loadLineScanHeader(path):
	"""
	path: full path to tif

	we will load and parse coresponding .txt file

	returns dict:
		numPixels:
		umLength:
		umPerPixel:
		totalSeconds:
	"""
	# "X Dimension"	"138, 0.0 - 57.176 [um], 0.414 [um/pixel]"
	# "T Dimension"	"1, 0.000 - 35.496 [s], Interval FreeRun"
	# "Image Size(Unit Converted)"	"57.176 [um] * 35500.000 [ms]"
	txtFile = os.path.splitext(path)[0] + '.txt'

	if not os.path.isfile(txtFile):
		print('ERROR: loadLineScanHeader did not find file:', txtFile)
		return None

	theRet = {'tif': path}

	with open(txtFile, 'r') as fp:
		lines = fp.readlines()
		for line in lines:
			line = line.strip()
			if line.startswith('"X Dimension"'):
				line = line.replace('"', "")
				line = line.replace(',', "")
				#print('loadLineScanHeader:', line)
				# 2 number of pixels in line
				# 5 um length of line
				# 7 um/pixel
				splitLine = line.split()
				for idx, split in enumerate(splitLine):
					#print('  ', idx, split)
					if idx == 2:
						numPixels = int(split)
						theRet['numPixels'] = numPixels
					elif idx == 5:
						umLength = float(split)
						theRet['umLength'] = umLength
					elif idx == 7:
						umPerPixel = float(split)
						theRet['umPerPixel'] = umPerPixel

			elif line.startswith('"T Dimension"'):
				line = line.replace('"', "")
				line = line.replace(',', "")
				#print('loadLineScanHeader:', line)
				# 5 total duration of image acquisition (seconds)
				splitLine = line.split()
				for idx, split in enumerate(splitLine):
					#print('  ', idx, split)
					if idx == 5:
						totalSeconds = float(split)
						theRet['totalSeconds'] = totalSeconds

						#theRet['secondsPerLine'] =

			#elif line.startswith('"Image Size(Unit Converted)"'):
			#	print('loadLineScanHeader:', line)
	#
	return theRet

def loadLineScan(path):
	"""
	path: full path to .tif file
	"""
	#tifHeader = loadLineScanHeader(path)
	if not os.path.isfile(path):
		print('ERROR: loadLineScan did not find file:', path)
		return None
	else:
		tif = tifffile.imread(path)
		return tif

def myLoad(myDict):
	tifFile = myDict['tif']
	abfFile = myDict['abf']

	# todo: check they exist

	tif = loadLineScan(tifFile)
	#print('tif.shape:', tif.shape)
	#print('tif.dtype:', tif.dtype)
	if len(tif.shape) == 3:
			tif = tif[:,:,1] # assuming image channel is 1
	tif = np.rot90(tif) # rotates 90 degrees counter-clockwise
	f0 = tif.mean()
	tifNorm = tif / f0
	#print(type(tifNorm))

	tifHeader = loadLineScanHeader(tifFile)
	tifHeader['shape'] = tifNorm.shape
	tifHeader['secondsPerLine'] = tifHeader['totalSeconds'] / tifHeader['shape'][1]
	tifHeader['abfPath'] = abfFile

	abf = pyabf.ABF(abfFile)

	tagTimesSec = abf.tagTimesSec
	firstFrameSeconds = tagTimesSec[0]
	tifHeader['firstFrameSeconds'] = firstFrameSeconds

	xMaxRecordingSec = abf.sweepX[-1] # seconds
	tifHeader['xMaxRecordingSec'] = xMaxRecordingSec

	return tif, tifHeader, abf

def simpleAnalysis(mvThreshold=-20):

	fileNumber = 3
	tif, tifHeader, abf = myLoad(lcrData.dataList[fileNumber])

	print('abf.dataRate', abf.dataRate)

	xVm = abf.sweepX
	yVm = abf.sweepY

	medianKernel = 31
	yVmFiltered = scipy.signal.medfilt(yVm, medianKernel)

	dtSeconds = xVm[1] - xVm[0]
	print(dtSeconds)

	# threshholdCrossing is a boolean aray
	threshholdCrossing = np.diff(yVm > mvThreshold, prepend=False)

	# spikePoints is just points where threshold was crossed
	spikePoints = np.argwhere(threshholdCrossing)[:,0]  # Upward crossings

	# remove spikes on downward trajectory
	goodSpikePoints = []
	pntWindow = 20
	for spikePoint in spikePoints:
		preMean = np.mean(yVmFiltered[spikePoint-pntWindow:spikePoint-1])
		postMean = np.mean(yVmFiltered[spikePoint+1:spikePoint+pntWindow])
		#print(spikePoint, preMean, postMean)
		if preMean<postMean:
			goodSpikePoints.append(spikePoint)
	#
	print(goodSpikePoints)

	spikeTimes0 = [x*dtSeconds for x in goodSpikePoints]

	refractorySeconds = 0.3 # 500 ms
	print('refractorySeconds:', refractorySeconds)

	spikeTimes = [spikeTimes0[0]]
	lastSpikeTime = spikeTimes[0]
	for idx, spikeTime in enumerate(spikeTimes0):
		if idx == 0:
			continue
		if (spikeTime-lastSpikeTime) > refractorySeconds:
			spikeTimes.append(spikeTime)
			lastSpikeTime = spikeTime


	xSpikes = spikeTimes
	ySpikes = [mvThreshold] * len(spikeTimes)
	#threshold_crossings = [mvThreshold if x==1 else np.nan for x in threshold_crossings]

	#
	# plot
	numPanels = 1
	fig, axs = plt.subplots(numPanels, 1, sharex=True)
	if numPanels == 1:
		axs = [axs]

	axs[0].plot(xVm, yVm, 'k')
	axs[0].plot(xVm, yVmFiltered, 'r', lw=1)
	axs[0].plot(xSpikes, ySpikes, 'ro')

	plt.show()

def myPlot(tif, tifHeader, abf, plotCaSum=False):
	"""
	tif: 2D numpy.array
	tifHeader: dict
	abf: abf file
	"""

	xMaxImage = tifHeader['totalSeconds'] #35.496 # seconds

	if plotCaSum:
		numPanels = 3
	else:
		numPanels = 2
	fig, axs = plt.subplots(numPanels, 1, sharex=True)
	titleStr = os.path.split(tifHeader['tif'])[1]
	fig.suptitle(titleStr)

	# e-phys
	# has 100 ms + 5 ms ttl
	'''
	preRoll = 100 / 1000 # ms -> sec
	ttlDur = 5 / 1000 # ms -> sec
	xMinPhys = (preRoll + ttlDur) * -1
	'''
	xMinPhys = 0

	xPlot = abf.sweepX
	xPlot += xMinPhys # e-phys recording starts with (100 ms + 5 ms ttl)
	yPlot = abf.sweepY
	#xMaxRecording = abf.sweepX[-1] # seconds
	xMaxRecordingSec = tifHeader['xMaxRecordingSec']
	#print('xMaxRecording:', xMaxRecording)

	# time of first frame, shift image by this amount
	tagTimesSec = abf.tagTimesSec
	firstFrameSeconds = tagTimesSec[0]
	#print('firstFrameSeconds:', firstFrameSeconds)

	xMax = max(xMaxImage+firstFrameSeconds, xMaxRecordingSec)
	xMaxLim = xMax
	#xMaxLim = 2.5 # debugging

	# image
	xMin = firstFrameSeconds
	yMin = 0
	yMax = tifHeader['umLength'] #57.176
	#extent = [xMin, xMaxImage, yMax, yMin] # flipped y
	extent = [xMin, xMax, yMin, yMax] # flipped y
	cmap = 'inferno' #'Greens' # 'inferno'
	axs[0].imshow(tif, aspect='auto', cmap=cmap, extent=extent)
	#axs[0].imshow(tif, aspect='auto', extent=extent)
	#axs[0].imshow(tif, aspect='auto')
	axs[0].set_xlim([xMinPhys, xMaxLim])
	axs[0].set_ylabel('Line (um)')
	axs[0].spines['right'].set_visible(False)
	axs[0].spines['top'].set_visible(False)

	#
	# sum the inensities of each image line scan
	#print('tif.shape:', tif.shape) # like (146, 10000)
	yLineScanSum = [np.nan] * tif.shape[1]
	xLineScanSum = [np.nan] * tif.shape[1]
	for i in range(tif.shape[1]):
		theSum = np.sum(tif[:,i])
		theSum /= tif.shape[0]
		yLineScanSum[i] = theSum
		xLineScanSum[i] = firstFrameSeconds + (tifHeader['secondsPerLine'] * i)
	meanLineScanSum = np.mean(yLineScanSum)
	stdLineScanSum = np.std(yLineScanSum)

	#
	# overlay vm on top of image
	if 0:
		axRight = axs[0].twinx()  # instantiate a second axes that shares the same x-axis
		axRight.plot(xPlot, yPlot, 'w', linewidth=0.5)

	axs[1].plot(xPlot, yPlot, 'k')
	axs[1].margins(x=0)
	axs[1].set_xlim([xMinPhys, xMaxLim])
	if not plotCaSum:
		axs[1].set_xlabel('Time (s)')
	axs[1].set_ylabel('Vm (mV)')
	axs[1].spines['right'].set_visible(False)
	axs[1].spines['top'].set_visible(False)

	# plot tag times (sec), the start of each line scan
	#tagTimesY = [-50] * len(tagTimesSec)
	#axs[1].plot(tagTimesSec, tagTimesY, '.r')

	#
	# plot the sum of inensity along each line
	# this might contribute to membrane depolarizations !!!
	if plotCaSum:
		yPlotNorm = NormalizeData(yPlot)
		axs[2].plot(xPlot, yPlotNorm, 'k')

		yLineScanSumNorm = NormalizeData(yLineScanSum)
		axs[2].plot(xLineScanSum, yLineScanSumNorm, 'r')

		#axs[2].axhline(y=meanLineScanSum, linewidth=1, color='r')
		#axs[2].axhline(y=meanLineScanSum+stdLineScanSum, linewidth=1, color='r')
		axs[2].margins(x=0)
		axs[2].set_xlim([xMinPhys, xMaxLim])
		#tmpMinY = meanLineScanSum - 1.5 * stdLineScanSum
		#tmpMaxY = meanLineScanSum + 1.5 * stdLineScanSum
		#axs[2].set_ylim([tmpMinY, tmpMaxY])
		#axs[2].set_ylabel('Sum Line Inensity')
		axs[2].spines['right'].set_visible(False)
		axs[2].spines['top'].set_visible(False)
		axs[2].set_xlabel('Time (s)')

		tmpDf = pd.DataFrame()
		tmpDf['time (s)'] = xLineScanSum
		tmpDf['y'] = yLineScanSumNorm
		tmpDf.to_csv('/Users/cudmore/Desktop/caInt.csv', header=True, index=False)


	#
	# cross cor between 'sum of line scan intensity' and Vm
	# todo: work on this, need to subsample Vm to match pnts in kymograph
	if 0:
		fig2, ax2 = plt.subplots(1, 1, sharex=True)
		print('yLineScanSum:', len(yLineScanSum))
		print('yPlot:', len(yPlot[0:-1:4]))
		ax2.xcorr(yLineScanSum, yPlot, usevlines=True,
				maxlags=50, normed=True, lw=2)
		ax2.grid(True)

	plt.show()

def NormalizeData(data):
	return (data - np.min(data)) / (np.max(data) - np.min(data))

def test_header():
	tifFile = '/Users/cudmore/data/dual-lcr/20201222/data/20201222_.tif'
	abfFile = '/Users/cudmore/data/dual-lcr/20201222/data/20d22000.abf'
	tifHeader = loadLineScanHeader(tifFile)
	print(tifHeader)

def test_plot():
	fileNumber = 3
	tif, tifHeader, abf = myLoad(lcrData.dataList[fileNumber])

	# bingo !!!
	#print(abf.tagTimesSec) # bingo!!! list of tag times in seconds

	pprint.pprint(tifHeader)

	myPlot(tif, tifHeader, abf, plotCaSum=True)

def myPrintDict(theDict):
	for k,v in theDict.items():
		print(f'  {k} : {v}')

def makeReport():
	dictList = []
	for fileIdx in range(len(lcrData.dataList)):
		#tmpDict = lcrData.dataList[i]
		tif, tifHeader, abf = myLoad(lcrData.dataList[fileIdx])
		dictList.append(tifHeader)
	#
	df = pd.DataFrame(dictList)
	print(df[['abfPath', 'firstFrameSeconds']])

def analyzeTagTimes():
	"""
	analyze the timing of all tags
	tags are scan start from fv3000
	"""
	fileIdx = 3
	tif, tifHeader, abf = myLoad(lcrData.dataList[fileIdx])
	tagTimesSec = abf.tagTimesSec # [0.516, 0.5415, 0.567, 0.5925, 0.618, 0.6435, 0.669, 0.6945

	# looking into other tags
	tagTimesMin = abf.tagTimesMin
	tagComments = abf.tagComments
	tagSweeps = abf.tagSweeps # tagSweeps = [0.020640000000000002, 0.02166, 0.02268, 0.023700000000000002, 0.02472, 0.02574, 0.026760000000000003,
	# not available?
	#nTagType = abf.nTagType # is 2 for 'external'

	# not available
	# seems to be fSynchTimeUnit = 100.0
	#fSynchTimeUnit = abf.fSynchTimeUnit

	'''
	Later we will populate the times and sweeps (human-understandable units)
	by multiplying the lTagTime by fSynchTimeUnit from the protocol section.
	'''
	# not available
	# like lTagTime = [0.516, 0.5415, 0.567, 0.5925, 0.618, 0.6435, 0.669
	#lTagTime = abf.lTagTime

	myPrintDict(tifHeader)
	print('number of tags:', len(tagTimesSec))
	tagTimeDiff = np.diff(tagTimesSec)

	if 0:
		fig, axs = plt.subplots(2, 1, sharex=False)
		titleStr = os.path.split(tifHeader['tif'])[1]
		fig.suptitle(titleStr)

		n, bins, patches = axs[0].hist(tagTimeDiff, 100, density=False, facecolor='k', alpha=0.75)
		#axs[1].plot(tagTimeDiff)
		axs[1].plot(nTagType)
		plt.show()

	#print(abf.headerText)

if __name__ == '__main__':
	#test_header()

	test_plot()
	#makeReport()
	#analyzeTagTimes()
	#simpleAnalysis()
