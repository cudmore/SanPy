#20210203

import os, sys, math

import numpy as np
import pandas as pd

import scipy.signal

import matplotlib
import matplotlib.pyplot as plt

import tifffile
import pyabf

import sanpy

def loadDatabase(dbFile='dual-database.xlsx'):
	"""
	Load a database of dual recordings
	"""

	#
	# load cell database file
	if dbFile.endswith('.csv'):
		df = pd.read_csv(dbFile, header=0, dtype={'ABF File': str})
	elif dbFile.endswith('.xlsx'):
		# stopped working 20201216???
		#df = pd.read_excel(dbFile, header=0, dtype={'ABF File': str})
		#df=pd.read_excel(dbFile, header=0, engine='openpyxl')
		#df=pd.read_excel(dbFile, header=0, engine='xlrd')
		#df=pd.read_excel(open(dbFile,'rb'), header=0)
		df=pd.read_excel(dbFile, header=0)
	else:
		print('error reading dbFile:', dbFile)
		return None

	# append columns to dataframe
	df['tifPath'] = ''
	df['abfPath'] = ''

	#
	# check we find all data in database
	myPath = os.getcwd()
	dataPath = df['data path'].loc[0]

	numRows = df.shape[0]
	for row in range(numRows):
		dateFolder = df['date folder'].loc[row]
		dateFolder = str(int(dateFolder))
		tif = df['tif file'].loc[row]
		abf = df['abf file'].loc[row]

		tifPath = os.path.join(myPath, dataPath, dateFolder, tif)
		if os.path.isfile(tifPath):
			#df['tifPath'].iloc[row] = tifPath
			df.at[row, 'tifPath'] = tifPath
		else:
			print(f'  ERROR: did not find tif at row {row+1}, path: {tifPath}')

		abfPath = os.path.join(myPath, dataPath, dateFolder, abf)
		if os.path.isfile(abfPath):
			#df['abfPath'].iloc[row] = abfPath
			df.at[row, 'abfPath'] = abfPath
		else:
			print(f'  ERROR: did not find abf at row {row+1}, path:', abfPath)

	return df

def makeReport(df):
	"""
	df: pandas dataframe of cell database (from Excel file)
	prints abf path and firstFrameSeconds
	"""
	dictList = []
	for fileIdx in range(len(df)):
		#tmpDict = lcrData.dataList[i]
		tif, tifHeader, abf = myLoad(lcrData.dataList[fileIdx])
		dictList.append(tifHeader)
	#
	df = pd.DataFrame(dictList)
	print(df[['abfPath', 'firstFrameSeconds']])

class dualRecord:
	def __init__(self, tifFile, abfFile):
		'''
		print('dualRecord()')
		print('  tifFile:', tifFile)
		print('  abfFile:', abfFile)
		'''

		self.tifFile = tifFile
		self.abfFile = abfFile

		self.tifHeader = None # dict
		self.tif = None # 2d numpy
		self.tifNorm = None # 2d numpy

		self.abf = None # pyabf object

		# spike analysis (ba is bAnalysis object)
		self.baAbf = None # see: loadAndAnalyzeAbf
		self.baTif = None # see: loadAndAnalyzeTif

		self.load()

		#self._printDict(self.tifHeader)

		# todo: put into function
		# sum the inensities of each image line scan
		#print('tif.shape:', tif.shape) # like (146, 10000)
		tifRows = self.tif.shape[0] # number of points in each line
		tifColumns = self.tif.shape[1] # nuumber of line scane
		self.yLineScanSum = [np.nan] * tifColumns
		self.xLineScanSum = [np.nan] * tifColumns
		firstFrameSeconds = self.tifHeader['firstFrameSeconds']
		secondsPerLine = self.tifHeader['secondsPerLine']
		for i in range(tifColumns):
			# for each line scan (column)
			theSum = np.sum(self.tif[:,i])
			theSum /= tifRows
			self.yLineScanSum[i] = theSum
			self.xLineScanSum[i] = firstFrameSeconds + (secondsPerLine * i)

	def load(self):
		"""
		"""
		# todo: check they exist
		if not os.path.isfile(self.tifFile):
			print('ERROR: dualRecord.load() did not find tifFile:', self.tifFile)
			return None
		if not os.path.isfile(self.abfFile):
			print('ERROR: dualRecord.load() did not find abfFile:', self.abfFile)
			return None

		tif = tifffile.imread(self.tifFile)

		if len(tif.shape) == 3:
				tif = tif[:,:,1] # assuming image channel is 1
		tif = np.rot90(tif) # rotates 90 degrees counter-clockwise
		f0 = tif.mean()
		tifNorm = tif / f0
		#
		self.tif = tif
		self.tifNorm = tifNorm

		tifHeader = self.loadLineScanHeader()
		tifHeader['shape'] = tifNorm.shape
		tifHeader['secondsPerLine'] = tifHeader['totalSeconds'] / tifHeader['shape'][1]
		#tifHeader['abfPath'] = abfFile
		self.tifHeader = tifHeader

		self.abf = pyabf.ABF(self.abfFile)

		tagTimesSec = self.abf.tagTimesSec
		firstFrameSeconds = tagTimesSec[0]
		self.tifHeader['firstFrameSeconds'] = firstFrameSeconds

		xMaxRecordingSec = self.abf.sweepX[-1] # seconds
		self.tifHeader['xMaxRecordingSec'] = xMaxRecordingSec

	def loadLineScanHeader(self):
		"""
		path: full path to tif

		we will load and parse coresponding .txt file

		returns dict:
			numPixels:
			umLength:
			umPerPixel:
			totalSeconds:
		"""
		path = self.tifFile
		# "X Dimension"	"138, 0.0 - 57.176 [um], 0.414 [um/pixel]"
		# "T Dimension"	"1, 0.000 - 35.496 [s], Interval FreeRun"
		# "Image Size(Unit Converted)"	"57.176 [um] * 35500.000 [ms]"
		txtFile = os.path.splitext(path)[0] + '.txt'

		if not os.path.isfile(txtFile):
			print('ERROR: dualRecord.loadLineScanHeader() did not find file:', txtFile)
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

				elif line.startswith('"Date"'):
					line = line.replace('"Date"', "")
					line = line.replace('"', "")
					line = line.replace('\t', "")
					theRet['tifDateTime'] = line

				#elif line.startswith('"Image Size(Unit Converted)"'):
				#	print('loadLineScanHeader:', line)
		#
		return theRet

	def _printDict(self, theDict):
		for k,v in theDict.items():
			print(f'    {k} : {v}')

	def printHeader(self):
		self._printDict(self.tifHeader)

	def plotPhase_no_work(self):
		xPlot = self.abf.sweepX
		yPlot = self.abf.sweepY

		xLineScanSum = self.xLineScanSum #spnt[0] has delay
		yLineScanSum = self.yLineScanSum

		firstFrameSeconds = self.tifHeader['firstFrameSeconds']
		xMaxImage = self.tifHeader['totalSeconds']
		xMaxRecordingSec = self.tifHeader['xMaxRecordingSec']

		xMaxLim = min(xMaxImage+firstFrameSeconds, xMaxRecordingSec)

		print('  resample: xPlot', len(xPlot), 'yLineScanSum:', len(yLineScanSum))
		tmpImageTimePoints = np.argwhere(xLineScanSum>xMaxLim)[:,0]  # Upward crossings
		tmpLastGoodImagePnt = tmpImageTimePoints[0]
		print('  tmpImageTimePoints:', tmpImageTimePoints)
		print('  tmpImageTimePoints[0]:', type(tmpImageTimePoints[0]), tmpImageTimePoints[0])
		print('  last image x to use pnt:', tmpImageTimePoints[0], 'sec:', xLineScanSum[tmpImageTimePoints[0]])
		xLineScanTrunc = xLineScanSum[0:tmpLastGoodImagePnt]
		yLineScanTrunc = yLineScanSum[0:tmpLastGoodImagePnt]

		print('  new image length x:', len(xLineScanTrunc), 'y:', len(yLineScanTrunc))
		resampleFactor = len(xPlot) / tmpLastGoodImagePnt * len(xLineScanTrunc)
		resampleFactor = math.floor(resampleFactor)

		#dt = 0.0001
		dt = 1 / self.abf.dataRate
		print('  abf dt:', dt)
		#xLineScanResample = np.linspace(firstFrameSeconds, xMaxLim, resampleFactor, endpoint=False)
		#xLineScanResample = [firstFrameSeconds, xMaxLim, dt]
		xLineScanResample = [firstFrameSeconds + x*dt for x in range(resampleFactor)]

		print('  xLineScanResample[0]:', xLineScanResample[0])
		print('  xLineScanResample dt:', xLineScanResample[1] - xLineScanResample[0])

		# resample the truncated line scan sum (truncated to length of e-phys)
		yLineScanResample = scipy.signal.resample(yLineScanTrunc, resampleFactor)
		tmp = np.interp(xLineScanResample, xLineScanTrunc, yLineScanTrunc)
		print('tmp:', len(tmp))
		#xLineScanResample = np.linspace(0, 10, 100, endpoint=False)
		print('  resampleFactor:', resampleFactor, 'yLineScanResample:', len(yLineScanResample), 'xLineScanResample:', len(xLineScanResample))

		xLineScanResample = xLineScanResample[0:len(xPlot)]
		yLineScanResample = yLineScanResample[0:len(xPlot)]

		if 1:
			tmpFig, tmpAxs = plt.subplots(2, 1, sharex=False)
			#tmpAxs = [tmpAxs]
			tmpAxs[0].plot(xLineScanResample, yLineScanResample, '.-r')
			#tmpAxs[0].plot(xLineScanResample, yLineScanResample, '.-r')
			#tmpAxs[0].plot(xLineScanSum, yLineScanSum, '.-k')
			tmpAxs[0].plot(xPlot, yPlot, '.-k')

			tmpAxs[1].plot(yPlot, '.-r')
			tmpAxs[1].plot(tmp, '.-k')


	def plotTagTimes(self):
		"""
		analyze the timing of all tags
		tags are scan start from fv3000
		"""
		#fileIdx = 3
		#tif, tifHeader, abf = myLoad(lcrData.dataList[fileIdx])
		tif = self.tif
		tifHeader = self.tifHeader
		abf = self.abf

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

		#self._printDict(tifHeader)

		print('number of tags:', len(tagTimesSec))
		tagTimeDiff = np.diff(tagTimesSec)

		if 1:
			fig, axs = plt.subplots(2, 1, sharex=False)
			titleStr = os.path.split(tifHeader['tif'])[1]
			fig.suptitle(titleStr)

			n, bins, patches = axs[0].hist(tagTimeDiff, 100, density=False, facecolor='k', alpha=0.75)
			#axs[1].plot(tagTimeDiff)
			#axs[1].plot(nTagType)

			yPlotPos = 0
			yTagTimesSec = [yPlotPos for x in tagTimesSec]

			axs[1].plot(abf.sweepX, abf.sweepY, '.k')
			axs[1].plot(tagTimesSec, yTagTimesSec, '.r')

			#plt.show()

		#print(abf.headerText)

	def loadAndAnalyzeAbf(self, dVthresholdPos=30, minSpikeVm=-20):

		if dVthresholdPos is None and minSpikeVm is not None:
			# to allow pure mV detection
			pass
		else:
			dVthresholdPos = 20
		if minSpikeVm is None:
			minSpikeVm = -20

		#path = '/Users/cudmore/data/dual-lcr/20210115/data/21115002.abf'
		path = self.abfFile

		ba = sanpy.bAnalysis(path)
		#ba.getDerivative()

		#dVthresholdPos = 30
		#minSpikeVm = -20
		'''
		halfWidthWindow_ms = 100 # was 20
		peakWindow_ms = 100
		spikeClipWidth_ms = 1000 # for 2021_01_29_0003 (idx 13+3)
		refractory_ms = 400 # for 2021_01_29_0003 (idx 13+3)
		onlyPeaksAbove_mV = -20 # for 2021_01_29_0003 (idx 13+3)
		'''
		detectionDict = ba.getDefaultDetection()
		ba.spikeDetect(detectionDict)
		'''
		ba.spikeDetect(dVthresholdPos=dVthresholdPos, minSpikeVm=minSpikeVm,
			halfWidthWindow_ms=halfWidthWindow_ms,
			spikeClipWidth_ms=spikeClipWidth_ms,
			peakWindow_ms=peakWindow_ms,
			refractory_ms=refractory_ms,
			onlyPeaksAbove_mV=onlyPeaksAbove_mV)

			#avgWindow_ms=avgWindow_ms,
			#dvdtPreWindow_ms=dvdtPreWindow_ms,
			#peakWindow_ms=peakWindow_ms,
			#refractory_ms=refractory_ms,
			#dvdt_percentOfMax=dvdt_percentOfMax)
		'''

		#test_plot(ba)

		self.baAbf = ba

	def loadAndAnalyzeTif(self, dDict):
		"""
		working on spike detection from sum of intensities along a line scan
		see: example/lcr-analysis
		"""
		dVthresholdPos = dDict['caThresholdPos']
		minSpikeVm = dDict['caMinSpike']

		path = self.tifFile

		ba = sanpy.bAnalysis(path)
		ba.spikeDetect(dDict)

		#ba.getDerivative()

		# Ca recording is ~40 times slower than e-phys at 10 kHz
		#minSpikeVm = 0.5
		#dVthresholdPos = 0.01
		'''
		refractory_ms = 60 # was 20 ms
		avgWindow_ms=60 # pre-roll to find eal threshold crossing
			# was 5, in detect I am using avgWindow_ms/2 ???
		window_ms = 20 # was 2
		peakWindow_ms = 70 # 20 gives us 5, was 10
		dvdt_percentOfMax = 0.2 # was 0.1
		halfWidthWindow_ms = 60 # was 20
		spikeClipWidth_ms = 1000 # was 500
		ba.spikeDetect(dVthresholdPos=dVthresholdPos, minSpikeVm=minSpikeVm,
			avgWindow_ms=avgWindow_ms,
			window_ms=window_ms,
			peakWindow_ms=peakWindow_ms,
			refractory_ms=refractory_ms,
			dvdt_percentOfMax=dvdt_percentOfMax,
			halfWidthWindow_ms=halfWidthWindow_ms,
			spikeClipWidth_ms=spikeClipWidth_ms,
			)
		'''

		#for k,v in ba.spikeDict[0].items():
		#	print('  ', k, ':', v)

		#test_plot(ba, firstSampleTime)

		self.baTif = ba

	def plotSpikeAnalysis(self, type='abf', fileNumber=None, myParent=None):
		"""
		type: ('abf', 'tif')

		Expecting analysis has been run, see:
			self.loadAndAnalyzeTif
			self.loadAndAnalyzeAbf
		"""
		def close_event(event):
			"""
			tell parent we are closing
			"""
			#print('plotSpikeClip.close_event()')
			if myParent is not None:
				# for now expectin parent to be testTable.py
				myParent.closeChild('analysis plot', fileNumber)

		myParent = myParent

		if type == 'tif':
			yLabelStr = 'Ca (line scan sum)'
			tif = self.tif
			ba = self.baTif
		elif type == 'abf':
			yLabelStr = 'Vm (mV)'
			tif = None
			ba = self.baAbf
		else:
			print('ERROR: plotSpikeAnalysis() is expecting type in (tif, abf), got type:', type)
			return

		firstSampleTime = 0 # todo: get rid of this

		# plot
		if tif is None:
			fig, axs = plt.subplots(2, 1, sharex=True)
		else:
			fig, axs = plt.subplots(3, 1, sharex=True)
		titleStr = self._getTitle(fileNumber=fileNumber)
		fig.suptitle(titleStr)

		#
		# dv/dt
		xDvDt = ba.abf.sweepX + firstSampleTime
		yDvDt = ba.filteredDeriv
		axs[0].plot(xDvDt, yDvDt, 'k')

		# thresholdVal_dvdt
		xThresh = [x['thresholdSec'] + firstSampleTime for x in ba.spikeDict]
		yThresh = [x['thresholdVal_dvdt'] for x in ba.spikeDict]
		axs[0].plot(xThresh, yThresh, 'or')

		axs[0].spines['right'].set_visible(False)
		axs[0].spines['top'].set_visible(False)

		#
		# vm with detection params
		sweepX = ba.abf.sweepX + firstSampleTime
		sweepY = ba.abf.sweepY
		axs[1].plot(sweepX, sweepY, 'k-', lw=0.5)
		axs[1].set_ylabel(yLabelStr)

		xThresh = [x['thresholdSec'] + firstSampleTime for x in ba.spikeDict]
		yThresh = [x['thresholdVal'] for x in ba.spikeDict]
		axs[1].plot(xThresh, yThresh, 'or')

		xPeak = [x['peakSec'] + firstSampleTime for x in ba.spikeDict]
		yPeak = [x['peakVal'] for x in ba.spikeDict]
		axs[1].plot(xPeak, yPeak, 'ob')

		sweepX = ba.abf.sweepX + firstSampleTime

		for idx, spikeDict in enumerate(ba.spikeDict):
			#
			# plot all widths
			#print('plotting width for spike', idx)
			for j,widthDict in enumerate(spikeDict['widths']):
				#for k,v in widthDict.items():
				#	print('  ', k, ':', v)
				#print('j:', j)
				if widthDict['risingPnt'] is None:
					#print('  -->> no half width')
					continue

				risingPntX = sweepX[widthDict['risingPnt']]
				# y value of rising pnt is y value of falling pnt
				#risingPntY = ba.abf.sweepY[widthDict['risingPnt']]
				risingPntY = ba.abf.sweepY[widthDict['fallingPnt']]
				fallingPntX = sweepX[widthDict['fallingPnt']]
				fallingPntY = ba.abf.sweepY[widthDict['fallingPnt']]
				fallingPnt = widthDict['fallingPnt']
				# plotting y-value of rising to match y-value of falling
				#ax.plot(ba.abf.sweepX[widthDict['risingPnt']], ba.abf.sweepY[widthDict['risingPnt']], 'ob')
				# plot as pnts
				#axs[1].plot(ba.abf.sweepX[widthDict['risingPnt']], ba.abf.sweepY[widthDict['fallingPnt']], '-b')
				#axs[1].plot(ba.abf.sweepX[widthDict['fallingPnt']], ba.abf.sweepY[widthDict['fallingPnt']], '-b')
				# line between rising and falling is ([x1, y1], [x2, y2])
				axs[1].plot([risingPntX, fallingPntX], [risingPntY, fallingPntY], color='b', linestyle='-', linewidth=2)

		axs[1].spines['right'].set_visible(False)
		axs[1].spines['top'].set_visible(False)

		if tif is not None:
			xMin = firstSampleTime
			xMax = ba.abf.sweepX[-1]
			yMin = 0
			yMax = ba.abf.tifHeader['umLength'] #57.176
			#extent = [xMin, xMaxImage, yMax, yMin] # flipped y
			extent = [xMin, xMax, yMin, yMax] # flipped y
			axs[2].imshow(tif, extent=extent, aspect='auto')
			axs[2].spines['right'].set_visible(False)
			axs[2].spines['top'].set_visible(False)

		#
		return fig

	#def NormalizeData(self.data):
	#	return (data - np.min(data)) / (np.max(data) - np.min(data))

	def plotSpikeClip(self, doPhasePlot=False, fileNumber=None, region=None, myParent=None):
		"""
		myParent: tkInter testTable
		"""

		myParent = myParent # testTable
		global spikeNumber # needed because we will assign +/- in callback
		spikeNumber = 0 # used in callback for phase plot
		global phasePlotOptions
		phasePlotOptions = 0 # 0: one spike, 1: all + mean + one
		def close_event(event):
			"""
			tell parent we are closing
			"""
			#print('plotSpikeClip.close_event()')
			if myParent is not None:
				# for now expectin parent to be testTable.py
				myParent.closeChild('spike clip plot', fileNumber)

		def key_press_event(event):
			#print('press', event.key)
			global spikeNumber # needed because we are assigning new value
			sys.stdout.flush()
			if event.key in ['.', 'right']:
				# next
				spikeNumber += 1
				updatePhasePlot(spikeNumber)
			if event.key in [',', 'left']:
				# previous
				spikeNumber -= 1
				if spikeNumber < 0:
					spikeNumber = 0
					return
				else:
					updatePhasePlot(spikeNumber)
			if event.key == 'p':
				global phasePlotOptions
				phasePlotOptions += 1
				if phasePlotOptions > 1:
					phasePlotOptions = 0
				if phasePlotOptions == 0:
					# just one clip
					pass
				elif phasePlotOptions == 1:
					# all + mean + 1
					pass

		def updatePhasePlot(localSpikeNumber):

			numVmSpikes = len(ba1.spikeClips_x2)
			numCaSpikes = len(ba0.spikeClips_x2)

			print('spikeNumber:', localSpikeNumber, 'numVmSpikes:', numVmSpikes, 'numCaSpikes:', numCaSpikes)

			# grab x from vm recording (10kHz)
			xSpikeClips_vm = ba1.spikeClips_x2[localSpikeNumber] # list of list
			ySpikeClips_vm = ba1.spikeClips[localSpikeNumber]

			# ca
			xSpikeClips_ca = ba0.spikeClips_x2[localSpikeNumber] # list of list
			ySpikeClips_ca = ba0.spikeClips[localSpikeNumber]

			# interp for phase plot
			yInterpSpikeClips_ca = np.interp(xSpikeClips_vm, xSpikeClips_ca, ySpikeClips_ca)

			plottedPhaseLine.set_data(ySpikeClips_vm, yInterpSpikeClips_ca)

			axs[2].set_xlim(min(ySpikeClips_vm), max(ySpikeClips_vm)) #added ax attribute here
			axs[2].set_ylim(min(yInterpSpikeClips_ca), max(yInterpSpikeClips_ca)) #added ax attribute here

			#
			vmCurrentSpikeClip.set_data(xSpikeClips_vm, ySpikeClips_vm)
			caCurrentSpikeClip.set_data(xSpikeClips_ca, ySpikeClips_ca)

			fig.canvas.draw()

		#
		tifPath = self.tifFile
		abfPath = self.abfFile
		tifHeader = self.tifHeader

		#ba0 = test_load_tif(tifPath) # imaging
		#ba1 = test_load_abf(abfPath) # recording
		ba0 = self.baTif
		ba1 = self.baAbf

		if ba0 is None or ba1 is None:
			print('ERROR: plotSpikeClip() did not find analysis')
			return None

		thresholdSec0, peakSec0 = ba0.getStat('thresholdSec', 'peakSec')
		thresholdSec1, peakSec1 = ba1.getStat('thresholdSec', 'peakSec')

		print('plotSpikeClip() ca num spikes:', ba0.numSpikes, ', vm num spikes:', len(thresholdSec1), ba1.numSpikes)

		# ca
		if doPhasePlot:
			numSubplots = 3
		else:
			numSubplots = 2
		fig, axs = plt.subplots(numSubplots, 1, sharex=False)
		# share just axs[0] and axs[1], axs[2] is phase plot
		axs[0].get_shared_x_axes().join(axs[0], axs[1])

		# set the window/figure title
		titleStr = ''
		if fileNumber is not None:
			titleStr += str(fileNumber) + ' '
		if region is not None:
			titleStr += region + ' '
		titleStr += os.path.split(tifHeader['tif'])[1]
		fig.canvas.set_window_title(titleStr)
		#fig.suptitle(titleStr)

		fig.canvas.mpl_connect('key_press_event', key_press_event)
		fig.canvas.mpl_connect('close_event', close_event)

		axs[0].spines['right'].set_visible(False)
		axs[0].spines['top'].set_visible(False)
		axs[0].set_ylabel('Ca Intensity')

		axs[1].spines['right'].set_visible(False)
		axs[1].spines['top'].set_visible(False)
		axs[1].set_ylabel('Vm')

		# ca has many fewer pnts
		#print('  ca len spikeClips_x2:', len(ba0.spikeClips_x2[0]))
		#print('  vm len spikeClips_x2:', len(ba1.spikeClips_x2[0]))

		# ca
		for idx, sec in enumerate(thresholdSec0):
			try:
				spikeClips_x2 = ba0.spikeClips_x2[idx] # list of list
				spikeClips = ba0.spikeClips[idx]

				axs[0].plot(spikeClips_x2, spikeClips, '-k')
			except (IndexError) as e:
				print('error: plotSpikeClip() ca no spike', idx)

		# vm
		for idx, sec in enumerate(thresholdSec1):
			try:
				spikeClips_x2 = ba1.spikeClips_x2[idx] # list of list
				spikeClips = ba1.spikeClips[idx]

				axs[1].plot(spikeClips_x2, spikeClips, '-k')
			except (IndexError) as e:
				print('error: plotSpikeClip() vm no spike', idx)

		# phase plot
		if doPhasePlot:

			# grab x from vm recording (10kHz)
			xSpikeClips_vm = ba1.spikeClips_x2[spikeNumber] # list of list
			ySpikeClips_vm = ba1.spikeClips[spikeNumber]

			# ca
			xSpikeClips_ca = ba0.spikeClips_x2[spikeNumber] # list of list
			ySpikeClips_ca = ba0.spikeClips[spikeNumber]

			# interp ca clip to have same # samples as vm clip
			ySpikeClips_ca = np.interp(xSpikeClips_vm, xSpikeClips_ca, ySpikeClips_ca)

			plottedPhaseLine, = axs[2].plot(ySpikeClips_vm, ySpikeClips_ca, '.k')

			axs[2].spines['right'].set_visible(False)
			axs[2].spines['top'].set_visible(False)
			axs[2].set_xlabel('Vm')
			axs[2].set_ylabel('Ca')

			# make current spike larger and red
			spikeClips_x2 = ba0.spikeClips_x2[spikeNumber] # list of list
			spikeClips = ba0.spikeClips[spikeNumber]
			caCurrentSpikeClip, = axs[0].plot(spikeClips_x2, spikeClips, '-r', lw=2)

			spikeClips_x2 = ba1.spikeClips_x2[spikeNumber] # list of list
			spikeClips = ba1.spikeClips[spikeNumber]
			vmCurrentSpikeClip, = axs[1].plot(spikeClips_x2, spikeClips, '-r', lw=2)

		#
		return fig

	def myPlot(self, fileNumber=None, region=None, myParent=None):
		"""
		tif: 2D numpy.array
		tifHeader: dict
		abf: abf file
		"""

		fileNumber = fileNumber
		myParent = myParent

		tif = self.tif
		tifHeader = self.tifHeader
		abf = self.abf

		def close_event(event):
			"""
			tell parent we are closing
			"""
			if myParent is not None:
				# for now expectin parent to be testTable.py
				myParent.closeChild('raw plot', fileNumber)

		def key_press_event(event):
			#print('press', event.key)
			sys.stdout.flush()
			if event.key == '1':
				# vm line in ax[0] image
				visible = ptrRecordingOnImage.get_visible()
				ptrRecordingOnImage.set_visible(not visible)
				#
				axRight.axes.yaxis.set_visible(not visible)
				axRight.spines['right'].set_visible(not visible)
				fig.canvas.draw()
			if event.key == '2':
				# Ca line in axs[1]
				visible = ptrLineScanSum.get_visible()
				ptrLineScanSum.set_visible(not visible)
				fig.canvas.draw()
			if event.key == '3':
				# Vm line in axs[1]
				visible = ptrVmPlot2.get_visible()
				ptrVmPlot2.set_visible(not visible)
				#
				axRight1.axes.yaxis.set_visible(not visible)
				axRight1.spines['right'].set_visible(not visible)
				fig.canvas.draw()
			if event.key == '4':
				# toggle Vm axs[2] on/off
				visible = axs[2].get_visible()
				axs[2].set_visible(not visible)
				fig.canvas.draw()

			# todo: make a wrapper
			'''
			if event.key == 'n':
				newFile = fileNumber + 1
				print('key "n", newFile is', newFile)
				if newFile < len(df):
					myLoadAndPlot0(newFile, df=df) # plot image, vm, sum Ca
			if event.key == 'p':
				newFile = fileNumber - 1
				print('key "p", newFile is', newFile)
				if newFile >= 0:
					myLoadAndPlot0(newFile, df=df) # plot image, vm, sum Ca
			'''

		# todo: make a wrapper that uses database and
		# load/plots a number of dualRecord object
		#
		#df = df # used by callback
		#fileNumber = fileNumber # used by callback
		#fileNumber = None

		# open a figure window
		plotVm  = 1
		if plotVm:
			numPanels = 3
		else:
			numPanels = 2
		fig, axs = plt.subplots(numPanels, 1, sharex=True)
		fig.canvas.mpl_connect('key_press_event', key_press_event)
		fig.canvas.mpl_connect('close_event', close_event)

		# set the window/figure title
		titleStr = ''
		if fileNumber is not None:
			titleStr += str(fileNumber) + ' '
		if region is not None:
			titleStr += region + ' '
		titleStr += os.path.split(tifHeader['tif'])[1]
		fig.canvas.set_window_title(titleStr)
		#fig.suptitle(titleStr)

		# e-phy recording always starts at time 0
		xMinPhys = 0

		xPlot = abf.sweepX
		xPlot += xMinPhys # e-phys recording starts with (100 ms + 5 ms ttl)
		yPlot = abf.sweepY
		# xMaxRecordingSec is same as abf.sweepX[-1]
		xMaxRecordingSec = tifHeader['xMaxRecordingSec']

		# time of first frame, shift image by this amount
		tagTimesSec = abf.tagTimesSec
		firstFrameSeconds = tagTimesSec[0]
		'''
		print('  abf.tagTimesSec has', len(abf.tagTimesSec), 'tags,'
			'first tag seconds:', tagTimesSec[0],
			'first interval:', tagTimesSec[1] - tagTimesSec[0])
		'''

		xMaxImage = tifHeader['totalSeconds'] #35.496 # seconds
		xMax = max(xMaxImage+firstFrameSeconds, xMaxRecordingSec)
		xMaxLim = min(xMaxImage+firstFrameSeconds, xMaxRecordingSec)
		#print('  xMaxLim:', xMaxLim, 'the max on the x-axis (is min between image duration and abf record time')

		# image
		xMin = firstFrameSeconds
		yMin = 0
		yMax = tifHeader['umLength'] #57.176
		extent = [xMin, xMax, yMin, yMax] # flipped y
		cmap = 'inferno' #'Greens' # 'inferno'
		axs[0].imshow(tif, aspect='auto', cmap=cmap, extent=extent)
		axs[0].set_xlim([xMin, xMaxLim])
		axs[0].set_ylabel('Line (um)')
		axs[0].spines['right'].set_visible(False)
		axs[0].spines['top'].set_visible(False)
		#axs[0].spines['bottom'].set_visible(False)
		#axs[0].axes.xaxis.set_visible(False)

		#
		# overlay vm on top of image
		if 1:
			axRight = axs[0].twinx()  # instantiate a second axes that shares the same x-axis
			ptrRecordingOnImage, = axRight.plot(xPlot, yPlot, 'w', linewidth=0.5)
			axRight.spines['top'].set_visible(False)

		#
		# sum the inensities of each image line scan
		#print('tif.shape:', tif.shape) # like (146, 10000)
		yLineScanSum = [np.nan] * tif.shape[1]
		xLineScanSum = [np.nan] * tif.shape[1]
		for i in range(tif.shape[1]):
			theSum = np.sum(tif[:,i])
			theSum /= tif.shape[0]
			yLineScanSum[i] = theSum
			# checking if pre-roll is causing additional delay -->> conclude no
			#xLineScanSum[i] = -0.1 + firstFrameSeconds + (tifHeader['secondsPerLine'] * i)
			#xLineScanSum[i] = -0.004 + firstFrameSeconds + (tifHeader['secondsPerLine'] * i)
			# tpmTagInterval is the time interval (sec) between tags in abf header
			#tpmTagInterval = 6 * 0.025499999999999967
			#xLineScanSum[i] = -tpmTagInterval + firstFrameSeconds + (tifHeader['secondsPerLine'] * i)
			# was this
			xLineScanSum[i] = firstFrameSeconds + (tifHeader['secondsPerLine'] * i)


		# vm
		if plotVm:
			ptrVmPlot1, = axs[2].plot(xPlot, yPlot, 'k')
			axs[2].margins(x=0)
			axs[2].set_xlim([xMin, xMaxLim])
			axs[2].set_xlabel('Time (s)')
			axs[2].set_ylabel('Vm (mV)')
			axs[2].spines['right'].set_visible(False)
			axs[2].spines['top'].set_visible(False)

		# plot tag times (sec), the start of each line scan
		#tagTimesY = [0.5] * len(tagTimesSec)
		#axs[1].plot(tagTimesSec, tagTimesY, '.r')

		#
		# plot the sum of inensity along each line
		# this might contribute to membrane depolarizations !!!
		plotCaSum = True
		if plotCaSum:
			#yLineScanSumNorm = NormalizeData(yLineScanSum)
			#ptrLineScanSum, = axs[1].plot(xLineScanSum, yLineScanSumNorm, 'r')
			ptrLineScanSum, = axs[1].plot(xLineScanSum, yLineScanSum, 'r')

			axs[1].margins(x=0)
			axs[1].set_xlim([xMin, xMaxLim])
			axs[1].set_ylabel('f/f_0 (au)')
			axs[1].spines['right'].set_visible(False)
			axs[1].spines['top'].set_visible(False)
			#axs[1].axes.xaxis.set_visible(False)
			#axs[1].set_xlabel('Time (s)')

			#
			# overlay vm on top of ca sum
			if 1:
				axRight1 = axs[1].twinx()  # instantiate a second axes that shares the same x-axis
				ptrVmPlot2, = axRight1.plot(xPlot, yPlot, 'k', linewidth=0.5)
				axRight1.spines['top'].set_visible(False)

			'''
			# save a csv/txt file (open with bAbfText)
			tmpDf = pd.DataFrame()
			tmpDf['time (s)'] = xLineScanSum
			tmpDf['y'] = yLineScanSumNorm
			tmpDf.to_csv('/Users/cudmore/Desktop/caInt.csv', header=True, index=False)
			'''

		return fig

	#def _loadAnalyzeFrom_df(self, df, fileNumber):
	def _loadAnalyzeAbf_from_df(self, df, fileNumber):
		abfFile = df['abfPath'].loc[fileNumber]

		ba = sanpy.bAnalysis(abfFile)
		detectionDict = ba.getDefaultDetection()

		# pull values from df
		for k,v in detectionDict.items():
			if k in df.columns:
				dfValue = df[k].iloc[fileNumber]
				if not np.isnan(dfValue):
					detectionDict[k] = dfValue

		#detectionDict['medianFilter'] = 5

		# special case to turn off dV/dt detection and just use mV
		dVthresholdPos = df['dVthresholdPos'].iloc[fileNumber]
		if np.isnan(dVthresholdPos):
			detectionDict['dVthresholdPos'] = None

		# debug
		'''
		print('\n=== abf detection dict')
		self._printDict(detectionDict)
		'''

		ba.spikeDetect(detectionDict)

		self.baAbf = ba

	def _loadAnalyzeCa_from_df(self, df, fileNumber):
		tifFile = df['tifPath'].loc[fileNumber]

		baTif = sanpy.bAnalysis(tifFile)
		caDetectionDict = baTif.getDefaultDetection_ca()

		# update values in dDict from df
		caThresholdPos = df['caThresholdPos'].iloc[fileNumber]
		minSpikeVm = df['caMinSpike'].iloc[fileNumber]
		#print('caThresholdPos:', type(caThresholdPos), caThresholdPos)
		if ~np.isnan(caThresholdPos):
			caDetectionDict['dVthresholdPos'] = caThresholdPos
		if ~np.isnan(minSpikeVm):
			caDetectionDict['minSpikeVm'] = minSpikeVm

		# debug
		'''
		print('\n=== ca detection dict')
		self._printDict(caDetectionDict)
		'''

		baTif.spikeDetect(caDetectionDict)

		self.baTif = baTif


	def plotSpikeClip_df(self, df, fileNumber, myParent=None):
		"""
		to plot spike clips from testTable.py
		"""

		self._loadAnalyzeFrom_df(df, fileNumber)

		region = df['region'].loc[fileNumber]

		#dr.plotSpikeAnalysis(type='tif') # works
		fig = self.plotSpikeClip(doPhasePlot=True, fileNumber=fileNumber,
								region=region, myParent=myParent)

		return fig

	def plotSpikeDetection_df(self, df, fileNumber, myParent=None):
		"""
		to plot spike clips from testTable.py
		"""

		#self._loadAnalyzeFrom_df(df, fileNumber)
		self._loadAnalyzeCa_from_df(df, fileNumber)
		self._loadAnalyzeAbf_from_df(df, fileNumber)

		region = df['region'].loc[fileNumber]

		#dr.plotSpikeAnalysis(type='tif') # works
		#fig = self.plotSpikeClip(doPhasePlot=True, fileNumber=fileNumber,
		#						region=region, myParent=myParent)
		figTif = self.plotSpikeAnalysis(type='tif', fileNumber=fileNumber, myParent=myParent)
		figAbf = self.plotSpikeAnalysis(type='abf', fileNumber=fileNumber, myParent=myParent)

		return figTif, figAbf

	def old_fix_lcrDualAnalysis(self, fileIndex):
		"""
		todo: update to use df

		for 2x files, line-scan and e-phys
		plot spike time delay of ca imaging
		"""
		#fileIndex = 3
		tifPath = lcrData.dataList[fileIndex]['tif']
		abfPath = lcrData.dataList[fileIndex]['abf']

		ba1 = test_load_abf(abfPath) # recording
		# now need to get this from pClamp abf !!!
		#firstSampleTime = ba0.abf.sweepX[0] # is not 0 for 'wait for trigger' FV3000
		firstSampleTime = ba1.abf.tagTimesSec[0]
		print('firstSampleTime:', firstSampleTime)

		#myPlot(tif, tifHeader, abf, plotCaSum=False)

		test_plot(ba1)

		# abf from tif will ALWAYS be 0 based
		ba0 = test_load_tif(tifPath) # image

		tif = ba0.abf.tifNorm
		test_plot(ba0, tif=tif, firstSampleTime=firstSampleTime)

		#plt.show()

		thresholdSec0, peakSec0 = ba0.getStat('thresholdSec', 'peakSec')
		thresholdSec1, peakSec1 = ba1.getStat('thresholdSec', 'peakSec')

		# for each spike in e-phys, match it with a spike in imaging
		# e-phys is shorter, fewer spikes
		numSpikes = len(thresholdSec1) #ba1.numSpikes
		print('num spikes in recording:', numSpikes)

		ba1_width50, throwOut = ba1.getStat('widths_50', 'peakSec')

		# todo: add an option in bAnalysis.getStat()
		thresholdSec0 = [x + firstSampleTime for x in thresholdSec0]
		peakSec0 = [x + firstSampleTime for x in peakSec0]

		# assuming spike-detection is clean
		# truncate imaging (it is longer than e-phys)
		thresholdSec0 = thresholdSec0[0:numSpikes] # second value/max is NOT INCLUSIVE
		peakSec0 = peakSec0[0:numSpikes]

		numSubplots = 2
		fig, axs = plt.subplots(numSubplots, 1, sharex=False)

		titleStr = os.path.split(ba0.abf.tifHeader['tif'])[1]
		fig.suptitle(titleStr)

		# threshold in image starts about 20 ms after Vm
		axs[0].plot(thresholdSec1, peakSec0, 'ok')
		#axs[0].plot(thresholdSec1, 'ok')

		# draw diagonal
		axs[0].plot([0, 1], [0, 1], transform=axs[0].transAxes)

		axs[0].spines['right'].set_visible(False)
		axs[0].spines['top'].set_visible(False)

		axs[0].set_xlabel('thresholdSec1 (abf)')
		axs[0].set_ylabel('peakSec0 (tif)')

		#axs[1].plot(thresholdSec1, peakSec0, 'ok')

		# time to peak in image wrt AP threshold time
		caTimeToPeak = []
		for idx, thresholdSec in enumerate(thresholdSec1):
			timeToPeak = peakSec0[idx] - thresholdSec
			#print('thresholdSec:', thresholdSec, 'peakSec0:', peakSec0[idx], 'timeToPeak:', timeToPeak)
			timeToPeakMs = timeToPeak * 1000
			caTimeToPeak.append(timeToPeakMs)

		print('caTimeToPeak:', caTimeToPeak)

		axs[1].plot(ba1_width50, caTimeToPeak, 'ok')

		# draw diagonal
		#axs[1].plot([0, 1], [0, 1], transform=axs[1].transAxes)
		axs[1].spines['right'].set_visible(False)
		axs[1].spines['top'].set_visible(False)

		axs[1].set_xlabel('Vm half width (ms)')
		axs[1].set_ylabel('Ca++ Time To Peak\n(ms)')

		#
		#plt.show()

	def _getTitle(self, fileNumber=None, region=None):
		# set the window/figure title
		titleStr = ''
		if fileNumber is not None:
			titleStr += str(fileNumber) + ' '
		if region is not None:
			titleStr += region + ' '
		titleStr += os.path.split(self.tifHeader['tif'])[1]
		return titleStr

	def findSpikePairs(self, fileNumber=None, doPlot=False):
		"""
		for each vm spike, find the 1st ca spike in a later window

		we will add (caDelay_sec, caWidth_ms) to each spike dict in (baAbf)
		"""

		# max allowed delya to peak
		maxCaDelaySecond = 0.6

		#
		# add to self.baAbf.spikeDict
		for spikeDict in self.baAbf.spikeDict:
			spikeDict['caDelay_sec'] = np.nan
			spikeDict['caWidth_ms'] = np.nan

		firstFrameSeconds = self.tifHeader['firstFrameSeconds']

		vmThresholdSecs, vmPeakSeconds = self.baAbf.getStat('thresholdSec', 'peakSec')
		caThresholdSecs, caPeakSeconds = self.baTif.getStat('thresholdSec', 'peakSec')

		# shift tif image by delay to start
		caThresholdSecs = [x+firstFrameSeconds for x in caThresholdSecs]
		caPeakSeconds = [x+firstFrameSeconds for x in caPeakSeconds]

		vm_width50, throwOut = self.baAbf.getStat('widths_50', 'peakSec')
		ca_width50, throwOut = self.baTif.getStat('widths_50', 'peakSec')

		# pair each Vm spike with the next ca spike
		# is ca delay is >maxDelaySecond then reject the pairr
		print('=== findSpikePairs() start pairing, maxCaDelaySecond:', maxCaDelaySecond)
		caDelayToPeak = [np.nan] * len(vmThresholdSecs)
		caWidth = [np.nan] * len(vmThresholdSecs)
		for idx, vmThresholdSec in enumerate(vmThresholdSecs):
			# if vm threshold second is <firstFrameSeconds then igonore (we have to Ca data)
			if vmThresholdSec < firstFrameSeconds:
				print('  rejecting vm spike', idx, 'it is at', vmThresholdSec, 'before start of ca imaging at:', firstFrameSeconds)
				continue

			caPeakPoint = np.argwhere(caPeakSeconds>vmThresholdSec)[0,0]  # Upward crossings
			caPeakSecond = caPeakSeconds[caPeakPoint]

			caDelay = caPeakSecond - vmThresholdSec
			if caDelay > maxCaDelaySecond:
				print('  rejecting vm spike', idx, 'caDelay > maxCaDelaySecond, caDelay:', caDelay)

				vm_width50[idx] = np.nan
				caDelayToPeak[idx] = np.nan
				caWidth[idx] = np.nan
			else:
				'''
				print('pairing vm spike', idx, 'at', round(vmThresholdSec,3), \
						'with ca spike', caPeakPoint, 'at', round(caPeakSecond,3), \
						'caDelay:', caDelay)
				'''
				if caDelay > 0.5:
					print('warning pairing long delay of', caDelay, 'vm spike', idx, round(vmThresholdSec,3), ', with ca spike at', round(caPeakSecond,3))
				caDelayToPeak[idx] = caDelay
				#caWidth[idx] = ca_width50[idx]
				caWidth[idx] = ca_width50[caPeakPoint]

				# add to self.abfVm.spikeDict
				self.baAbf.spikeDict[idx]['caDelay_sec'] = caDelay
				self.baAbf.spikeDict[idx]['caWidth_ms'] = ca_width50[caPeakPoint]

		# plot
		if doPlot:
			fig, axs = plt.subplots(1, 2, sharex=False)
			#axs = [axs]
			titleStr = self._getTitle(fileNumber=fileNumber)
			fig.suptitle(titleStr)
			'''
			# todo: my mV threshold detection is SHIT, we are not getting half-widths
			print('plotting vm_width50:', vm_width50)
			print('plotting caDelayToPeak:', caDelayToPeak)
			'''
			axs[0].plot(vm_width50, caDelayToPeak, 'ok')
			axs[0].set_xlabel('vm_width50 (ms)')
			axs[0].set_ylabel('ca_DelayToPeak (s)')
			axs[0].spines['right'].set_visible(False)
			axs[0].spines['top'].set_visible(False)
			titleStr = self._getTitle(fileNumber=fileNumber)

			axs[1].plot(vm_width50, caWidth, 'ok')
			axs[1].set_xlabel('vm_width50 (s)')
			axs[1].set_ylabel('ca_width50 (ms)')
			axs[1].spines['right'].set_visible(False)
			axs[1].spines['top'].set_visible(False)

			if 1:
				self.plotSpikeAnalysis(type='abf', fileNumber=fileNumber) # works
				self.plotSpikeAnalysis(type='tif', fileNumber=fileNumber) # works

def runPool():
	"""
	load/analyze/findspikepairs, then
		output a long list of spike stats as a df (one row per spike
	"""
	df = loadDatabase()

	dfMaster = None

	for fileNumber in range(len(df)):

		tifFile = df['tifPath'].loc[fileNumber]
		abfFile = df['abfPath'].loc[fileNumber]

		spikeAnalysis = df['spike analysis'].iloc[fileNumber]
		if spikeAnalysis != 1:
			continue

		region = df['region'].iloc[fileNumber]
		quality = df['quality'].iloc[fileNumber]
		cellNumber = df['cell number'].iloc[fileNumber]
		trial = df['trial'].iloc[fileNumber]

		print('runPool() running on file:', fileNumber)

		dr = dualRecord(tifFile, abfFile)

		dr._loadAnalyzeCa_from_df(df, fileNumber)
		dr._loadAnalyzeAbf_from_df(df, fileNumber)

		dr.findSpikePairs(fileNumber=fileNumber, doPlot=False)

		# dr.baAbf.spikeDict[] now has (caDelay_sec, caWidth_ms)

		# make a spike report
		df0 = pd.DataFrame(dr.baAbf.spikeDict)
		# append columns
		df0['include'] = 1
		df0['cellNumber'] = cellNumber # each cell can have multiple trial
		df0['trial'] = trial # multiple trials for each cell e.g. 3a/3b/3c
		df0['quality'] = quality
		df0['region'] = region
		df0['fileNumber'] = fileNumber # rows in .xlsx database, individual recording
		print('df0.shape:', df0.shape)
		if dfMaster is None:
			dfMaster = df0
		else:
			dfMaster = dfMaster.append(df0, ignore_index=True)

		#if fileNumber==4:
		#	print(dfMaster.head())
		#	sys.exit()

	#
	print('runPool() dfMaster len:', len(dfMaster))
	savePath = '/Users/cudmore/Desktop/dualAnalysis_db.csv'
	print('savePath:', savePath)
	dfMaster.to_csv(savePath)

def runOneRecording():
	df = loadDatabase()

	if 1:
		fileNumber = 16 #20210205, was 13 but laura added 3x cells
		fileNumber = 19
		# working backwards through .xlsx
		fileNumber = 20
		fileNumber = 19
		fileNumber = 18
		# bad cell fileNumber = 17
		fileNumber = 16
		fileNumber = 15
		fileNumber = 14
		# nope fileNumber = 13
		# nope fileNumber = 12
		fileNumber = 11
		# nope fileNumber = 10
		fileNumber = 9 # PERFECT RECORDING !!!
		fileNumber = 8 # PERFECT RECORDING !!!
		# nope fileNumber = 7
		# nope fileNumber = 6
		# nope fileNumber = 5
		fileNumber = 4 # PERFECT RECORDING !!!
		fileNumber = 3 # PERFECT RECORDING !!!
		fileNumber = 2 # PERFECT RECORDING !!!

		tifFile = df['tifPath'].loc[fileNumber]
		abfFile = df['abfPath'].loc[fileNumber]

		print('tifFile:', tifFile)

		dr = dualRecord(tifFile, abfFile)

		dr._loadAnalyzeCa_from_df(df, fileNumber)
		dr._loadAnalyzeAbf_from_df(df, fileNumber)

		if 0:
			dr.plotSpikeAnalysis(type='tif', fileNumber=fileNumber) # works
			dr.plotSpikeAnalysis(type='abf', fileNumber=fileNumber) # works
			plt.show()

		# after this, underlying dr.baAbf.spikeDict[]
		# will have caDelay_sec and caWidth_ms
		dr.findSpikePairs(fileNumber=fileNumber, doPlot=True)

		#
		plt.show()

if __name__ == '__main__':
	#runOneRecording()
	runPool()
