# 20210307
import os, sys, math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import dualAnalysis

def mergeDatabase(df):
	"""
	go through all rows in database
	load _lcrPicker.csv
	merge into one big df
	save as 'lcrPicker-db.csv'
	view with bScatterPlotWidget2.py
	"""

	absPath = os.path.abspath(__file__)
	absPath = os.path.split(absPath)[0]
	absPath = ''

	dataPath = os.path.join(absPath, 'dual-data')

	dfFinal = None

	# 20210122__0002_lcrPicker has high-freq ap, no lcr b/w spikes
	rejectionList = ['dual-data/20210122/20210122__0002_lcrPicker.csv']

	print('dataPath:', dataPath)
	numFiles = 0
	for obj in os.listdir(dataPath):
		folderPath = os.path.join(dataPath, obj)
		if os.path.isdir(folderPath):
			print('folderPath:', folderPath)
			for file in os.listdir(folderPath):
				if file.startswith('.'):
					continue
				if file.endswith('_lcrPicker.csv'):
					csvPath = os.path.join(folderPath, file)
					print('  csvPath:', csvPath)

					if csvPath in rejectionList:
						print('!!! rejecting csvPath:', csvPath)
						continue
					numFiles += 1
					if dfFinal is None:
						dfFinal = pd.read_csv(csvPath, header=0)
					else:
						df0 = pd.read_csv(csvPath, header=0)
						dfFinal = dfFinal.append(df0)
						dfFinal.reset_index(drop=True)
						# todo: should be
						#dfFinal = dfFinal.reset_index(drop=True)

	#
	# add new column for time of lcr before spike
	# todo: make new col to get rid of lcr where lcrPreSpikeSec < 0.1 sec
	if 1:
		dfFinal['lcrPreSpikeSec'] = dfFinal['spikeSec'] - dfFinal['lcrSec']

		#print(dfFinal[ np.isnan(dfFinal['lcrPreSpikeSec']) ] )

		# remove lcr (rows) that are close to before the spike,  lcrPreSpikeSec<0.1
		# important: we need second or np.isnan() to KEEP lcrPicker with no spike detecct
		lcrNoCloserThanSec = 0.15
		print('num lcr before removing lcr close to spike:', len(dfFinal))
		dfFinal = dfFinal[ (dfFinal['lcrPreSpikeSec'] > lcrNoCloserThanSec) | (np.isnan(dfFinal['lcrPreSpikeSec']) ) ]
		print('  after removing lcr close to spike:', len(dfFinal))

	#
	# save merged ccsv
	masterCsv = 'lcrPicker-db.csv'
	print('mergeDatabase() merged:', numFiles, '...saving masterCsv:', masterCsv)
	dfFinal.to_csv(masterCsv)

def runStats(df):
	"""
	load merged database and test if
	1) there is a significant linear correlation b/w lcr vm and pre vm
	"""
	pass

class lcrPicker():
	"""
	row:
	df:
	"""
	def __init__(self, row, df, doVmDetect=True):
		"""
		doVmDetect: False to not detect spikes in Vm,
					just step through trace in 500 ms chunks
		"""
		self.row = row
		self.df = df
		self.doVmDetect = doVmDetect

		# used with (not doVmDetect)
		self.endOfCurrentWindow = None
		self.noDetectWindowWidth_sec = 1

		# ms to bin lcr to make hist CRITICAL PARAMETER
		self.tifBins_ms = 50 #10
		self.vmBinSeconds = 0.01 # to get avg vm for (lcr, preMv, postMv)

		self.region = self.df['region'].loc[row]
		self.cellNumber = self.df['cell number'].loc[row]
		self.trial = self.df['trial'].loc[row]

		self.spikeNumber = None # zoom to spike with (left, right)
		self.lcrNum = None # to step through existing lcr
							# and then set corresponding Vm (pre lcr)

		self.fig = None
		self.axRight2 = None
		self.tPos_offset = None #has x-axis of lcr(s) shifted wrt delay to start of imaging
		self.lcrAmp = None
		self.lcrBins = None
		self.lastKey  = None
		self.selectedLcr = None

		# df to hold results
		self.colList = ['idx',
						'spikeNum', 'spikeSec',
						'lcrSec', 'lcrSum', 'lcrNum', 'lcrVm',
						'preVmSec', 'preVmInt', 'preVmMean',
						'postVmSec', 'postVmInt','postVmMean',
						'lcrPreDepol', 'lcrPostDepol',
						'region', 'cell number', 'trial',
						'tifBins_ms',
						'vmBinSeconds',
						'tifFile', 'tifPath'
						]
		self.printCols = ['idx', 'spikeNum', 'spikeSec',
						'lcrSec', 'lcrSum', 'lcrVm',
						'preVmSec', 'preVmMean',
						'postVmSec','postVmMean',
						'lcrPreDepol', 'lcrPostDepol',
						'region',
		]

		self.dfAnalysis = pd.DataFrame(columns=self.colList)

		tifPath, abfPath = dualAnalysis.getPathFromRow(df, row)

		print('lcrPicker()')
		print('  tifPath:', tifPath)
		print('  abfPath:', abfPath)

		# load dualAnalysis from df(row)
		self.dr = dualAnalysis.dualRecord(tifPath, abfPath)

		# need vm analysis to get peak seconds
		if doVmDetect:
			self.dr._loadAnalyzeAbf_from_df(self.df, self.row)

		# analyze spike

		# plot
		self.fig, self.axs, self.tPos_offset, self.lcrAmp, self.lcrBins, \
			self.axsLcrAnalysisLeft, \
			self.axsLcrAnalysisRight = self.plot()

		self.tifPath = self.dr.abfTif.tifHeader['tif']
		self.tifFile = os.path.split(self.dr.abfTif.tifHeader['tif'])[1]

		self.fig.show()

	def _getSavePath(self):
		csvPath = os.path.splitext(self.tifPath)[0]
		csvPath += '_lcrPicker.csv'
		return csvPath

	def save(self):
		"""save .csv based on namme of .tif"""
		# save self.dfAnalysis
		csvPath = self._getSavePath()
		print('saving:', csvPath)
		self.dfAnalysis.to_csv(csvPath)

	def load(self):
		""" load csv based on name of .tif """
		# save self.dfAnalysis
		csvPath = self._getSavePath()
		if os.path.isfile(csvPath):
			print('todo: load from', csvPath)
			self.dfAnalysis = pd.read_csv(csvPath, header=0)
			self.updateAnalysisPlot()
		else:
			print('did not find saved file csvPath:', csvPath)

	def getMeanVm(self, theSeconds):
		#binWidthSeconds = 0.01
		startSeconds = theSeconds - self.vmBinSeconds
		stopSeconds = theSeconds + self.vmBinSeconds
		# find values in range of sweepX
		binIndices = np.where((self.dr.abf.sweepX>startSeconds) & (self.dr.abf.sweepX<stopSeconds))
		binIndices = binIndices[0]

		#print('getMeanVm() self.vmBinSeconds:', self.vmBinSeconds, 'binIndices:', binIndices)

		# grab from sweepY
		theMean = np.nanmean(self.dr.abf.sweepY[binIndices])

		theMean = round(theMean,2) # round to 2 decimal placces

		return theMean

	def _appendLcr(self, xSeconds, ySum, numLcr):
		"""
		xSeconds: seconds
		ySum: amp
		numLcr: number of lcr going into amp
		"""
		if self.doVmDetect and self.spikeNumber is None:
			print('use right arrow to enter into a zoomed spike')
			return

		# append a now lcr to analysis
		row = len(self.dfAnalysis)
		print('  _appendLcr() row:', row, 'seconds:', xSeconds, 'amp:', ySum, 'numLcr', numLcr)

		for col in self.colList:
			self.dfAnalysis.loc[row, col] = np.nan

		if self.doVmDetect:
			vmThresholdSecs, vmPeakSeconds = self.dr.baAbf.getStat('thresholdSec', 'peakSec')
			spikeSeconds = vmThresholdSecs[self.spikeNumber]
		else:
			spikeSeconds = np.nan

		lcrVm = self.getMeanVm(xSeconds)
		lcrVm = round(lcrVm,3)

		self.dfAnalysis.loc[row, 'idx'] = row
		self.dfAnalysis.loc[row, 'spikeNum'] = self.spikeNumber if self.doVmDetect else np.nan
		self.dfAnalysis.loc[row, 'spikeSec'] = spikeSeconds
		self.dfAnalysis.loc[row, 'lcrSec'] = round(xSeconds, 4)
		self.dfAnalysis.loc[row, 'lcrNum'] = numLcr
		self.dfAnalysis.loc[row, 'lcrSum'] = round(ySum, 3)
		self.dfAnalysis.loc[row, 'lcrVm'] = lcrVm
		self.dfAnalysis.loc[row, 'tifBins_ms'] = self.tifBins_ms
		self.dfAnalysis.loc[row, 'vmBinSeconds'] = self.vmBinSeconds
		self.dfAnalysis.loc[row, 'region'] = self.region
		self.dfAnalysis.loc[row, 'cell number'] = self.cellNumber
		self.dfAnalysis.loc[row, 'trial'] = self.trial
		self.dfAnalysis.loc[row, 'tifFile'] = self.tifFile
		self.dfAnalysis.loc[row, 'tifPath'] = self.tifPath

		newNumLcr = len(self.dfAnalysis)
		return newNumLcr

	def _appendVm(self, xSec, lcrIndex, thisOne='pre'):
		"""
		append a vm clip at xSec for lcr lcrIndex
		"""
		print('  _appendVm()', thisOne, 'at sec:', xSec, 'for lcr at index:', lcrIndex)

		if lcrIndex is None:
			return

		prePostMv = self.getMeanVm(xSec)
		prePostMv = round(prePostMv,3)
		lcrVm = self.dfAnalysis.loc[lcrIndex, 'lcrVm']
		lcrDepol = lcrVm - prePostMv
		lcrDepol = round(lcrDepol,3)

		# time of the lcr we are adding to
		lcrSeconds = self.dfAnalysis.loc[lcrIndex, 'lcrSec']

		if thisOne == 'pre':
			self.dfAnalysis.loc[lcrIndex, 'preVmSec'] = round(xSec, 4)
			preVmInterval = lcrSeconds - xSec
			self.dfAnalysis.loc[lcrIndex, 'preVmInt'] = round(preVmInterval, 4)
			self.dfAnalysis.loc[lcrIndex, 'preVmMean'] = prePostMv
			# the magnitude of depol of the lcr wrt the pre vm
			# # positive means the lcr induces membrane depol
			self.dfAnalysis.loc[lcrIndex, 'lcrPreDepol'] = lcrDepol
		elif thisOne == 'post':
			self.dfAnalysis.loc[lcrIndex, 'postVmSec'] = round(xSec, 4)
			postVmInterval = xSec - lcrSeconds
			self.dfAnalysis.loc[lcrIndex, 'postVmInt'] = round(postVmInterval, 4)
			self.dfAnalysis.loc[lcrIndex, 'postVmMean'] = prePostMv
			# the magnitude of depol of the lcr wrt the pre vm
			# # positive means the lcr induces membrane depol
			self.dfAnalysis.loc[lcrIndex, 'lcrPostDepol'] = lcrDepol

	def printInfo(self):
		print('=== printInfo()')
		if self.doVmDetect:
			print('  spikeNumber:', self.spikeNumber, 'of', self.dr.baAbf.numSpikes-1)
		else:
			print('not doing Vm spike detection self.doVmDetect:', self.doVmDetect)
		print('  selectedLcr:', self.selectedLcr)
		print('  tifBins_ms:', self.tifBins_ms)
		print('  vmBinSeconds:', self.vmBinSeconds)
		# drop some columns so df print fits in terminal
		#dfNoTifPath = self.dfAnalysis.drop(['idx', 'tifBins_ms', 'tifFile', 'tifPath'], axis=1)
		dfImportantCols = self.dfAnalysis[ self.printCols ]
		print(dfImportantCols)

	def key_release_event(self, event):
		self.lastKey = None

	def key_press_event(self, event):
		#print('press', event.key)
		#print('key_press_event() event.key:', event.key)
		sys.stdout.flush()

		self.lastKey = event.key

		if event.key == 's':
			# save
			self.save()

		elif event.key == 'l':
			# load
			self.load()

		elif event.key == 'i':
			self.printInfo()

		elif event.key in ['.', 'right']:
			# next (first) spike
			if self.doVmDetect:
				if self.spikeNumber is None:
					self.spikeNumber = 0
				else:
					self.spikeNumber += 1
					if self.spikeNumber > self.dr.baAbf.numSpikes-1:
						print('at last spike')
						self.spikeNumber -= 1
			else:
				if self.endOfCurrentWindow is None:
					self.endOfCurrentWindow = self.noDetectWindowWidth_sec
				else:
					self.endOfCurrentWindow += self.noDetectWindowWidth_sec * 0.75
			# update
			self.zoomSpike(self.spikeNumber, self.endOfCurrentWindow)

		elif event.key in [',', 'left']:
			# previous spike
			if self.doVmDetect:
				if self.spikeNumber is None:
					print('use right to start at first spike')
					return
				self.spikeNumber -= 1
				if self.spikeNumber < 0:
					self.spikeNumber = 0
					return
			else:
				if self.endOfCurrentWindow is None:
					print('use right to start at first window (no spike detection)')
					return
				else:
					self.endOfCurrentWindow -= self.noDetectWindowWidth_sec * 0.75
					if self.endOfCurrentWindow < 0:
						self.endOfCurrentWindow = self.noDetectWindowWidth_sec
						print('at first window)')
						return
			# update
			self.zoomSpike(self.spikeNumber, self.endOfCurrentWindow)

		elif event.key == 'escape':
			# lccr selection
			#self.selectedLcr = None
			self.selectLcr(None)
			# reset x axis
			self.spikeNumber = None
			startSeconds = 0
			stopSeconds = self.dr.abf.sweepX[-1]
			self.axRight2.set_xlim(startSeconds, stopSeconds)
			self.fig.canvas.draw()

	def zoomSpike(self, n, endOfCurrentWindow):
		"""
		n: spike number
		"""
		if self.doVmDetect:
			print('zoomSpike() n:', n, 'of', self.dr.baAbf.numSpikes-1)
			# get time of spike (n, n-1)
			vmThresholdSecs, vmPeakSeconds = self.dr.baAbf.getStat('thresholdSec', 'peakSec')
			if n == 0:
				startSeconds = 0
			else:
				startSeconds = vmPeakSeconds[n-1]
			stopSeconds = vmPeakSeconds[n]
			stopSeconds += 0.02
		else:
			# no spike detect
			startSeconds = endOfCurrentWindow - self.noDetectWindowWidth_sec
			stopSeconds = endOfCurrentWindow
			stopSeconds += 0.02

		self.axRight2.set_xlim(startSeconds, stopSeconds)
		self.axRight2.set_ylim(0, 5)
		self.fig.canvas.draw()

		# remove lcr selection
		self.selectLcr(None)

	def onpick(self, event):
		"""
		"""
		print('onpick() event.ind:', event.ind)
		ind = event.ind
		if len(ind)>0:
			ind = ind[0]

		self.selectLcr(ind)

		'''
		thisline = event.artist
		xdata = thisline.get_xdata()
		ydata = thisline.get_ydata()
		x = xdata[ind]
		y = ydata[ind]
		print('  lcr ind:', ind, 'x:', x, 'y:', y)
		# select the lcr in scatter axs[4]
		self.lcrAnalysisSelectionLine2D.set_data(x,y)
		self.fig.canvas.draw()
		'''

	def selectLcr(self, ind):
		""
		""
		self.selectedLcr = ind

		if ind is None:
			self.lcrAnalysisSelectionLine2D.set_data([], [])
		else:
			xdata = self.lcrAnalysisLine2D.get_xdata()
			ydata = self.lcrAnalysisLine2D.get_ydata()
			x = xdata[ind]
			y = ydata[ind]
			print('  selectLcr() ind:', ind, 'x:', x, 'y:', y)
			self.lcrAnalysisSelectionLine2D.set_data(x,y)

			# this almost works
			# add to main plot and keep ref = axs[2].plot()
			# then use set_data
			#vLineMin, vLineMax= self.axs[2].get_ylim()
			#self.axs[2].plot([x,x], [vLineMin, vLineMax]) # returns LineCollection

		self.fig.canvas.draw()

	def on_button_press_event(self, event):
		# event is type MouseEvent

		print('on_button_press_event()')
		verbose = False
		if verbose:
			print('  ', event.xdata, event.ydata, 'lastKey:', self.lastKey)
		if event.xdata is None:
			#print('  please click within a plot')
			return
		ax = event.inaxes
		if ax != self.axRight2:
			#print('  please click in histogram axes')
			return

		if self.doVmDetect and self.spikeNumber is None:
			print('on_button_press_event() use right arrow to enter into a zoomed spike')
			return

		xPos = event.xdata

		# append pre/post vm
		if self.selectedLcr is not None and self.lastKey == 'v':
			# append pre vm
			self._appendVm(xPos, self.selectedLcr, thisOne='pre')
			# replot
			self.updateAnalysisPlot()
			return

		# append pre/post vm
		if self.selectedLcr is not None and self.lastKey == 'm':
			# append pre vm
			self._appendVm(xPos, self.selectedLcr, thisOne='post')
			# replot
			self.updateAnalysisPlot()
			return

		# find the lcr hist bin number corresponding to xPos
		lcrBinIdx = np.where(self.lcrBins>=xPos)[0]
		if len(lcrBinIdx) > 0:
			lcrBinIdx = lcrBinIdx[0]
			if verbose:
				print('  lcr bin idx:', lcrBinIdx, 'n bins:', len(self.lcrBins), 'last bin:', self.lcrBins[-1])
				print('    bin val:', self.lcrBins[lcrBinIdx])
			if lcrBinIdx > 0:
				realBinIdx = lcrBinIdx - 1
				if verbose:
					print('    self.lcrAmp[idx]:', self.lcrAmp[realBinIdx])

				# append to analysis df
				x = self.lcrBins[lcrBinIdx]
				y = self.lcrAmp[realBinIdx]
				numLcr = np.nan # todo: add this
				if y == 0:
					# do not allow lcr amp 0
					print('  ignoring lcrAmp 0 at x:', x, 'realBinIdx:', realBinIdx)
				else:
					newNumLcr = self._appendLcr(x, y, numLcr)
					# replot
					self.updateAnalysisPlot()
					# select the new lcr
					self.selectLcr(newNumLcr-1)

			else:
				print('  please try again, bad lcr bin index')
		else:
			print('  did not find', xPos, 'in lcr lcrBins')

	def updateAnalysisPlot(self):
		#
		# update lcr
		x = self.dfAnalysis['lcrSec']
		y = self.dfAnalysis['lcrSum']
		self.lcrAnalysisLine2D.set_data(x, y)

		# set new limits
		yMin = min(y)
		yMax = max(y)
		yRange = yMax - yMin
		if yRange == 0:
			yRange = 1
		yPadding = yRange * 0.05
		yMin -= yPadding
		yMax += yPadding
		self.axsLcrAnalysisRight.set_ylim(yMin, yMax)

		#
		# update pre vm (todo: add post vm???)
		x = self.dfAnalysis['preVmSec'].tolist()
		y = self.dfAnalysis['preVmMean'].tolist()
		#print('updateAnalysisPlot() vm')
		#print('  x:', x, type(x))
		#print('  y:', y, type(y))

		# update plot
		self.vmAnalysisLine2D.set_data(x, y)

		# set new limits
		yMin = np.nanmin(y)
		yMax = np.nanmax(y)
		if not np.isnan(yMin) and not np.isnan(yMax):
			yRange = yMax - yMin
			if yRange == 0:
				yRange = 1
			yPadding = yRange * 0.05
			yMin -= yPadding
			yMax += yPadding
			self.axsLcrAnalysisLeft.set_ylim(yMin, yMax)

		self.fig.canvas.draw()

	def plot(self):
		"""
		using csv output of SparkMaster result with one LCR per line

		parameters:
			self.tifBins_ms: how to bin SM LCR ROIs

		self.tPos_offset: has x-axis of lcr(s) shifted wrt delay to start of imaging
		"""

		print('lcrPicker.plot()')
		if self.dr.dfSparkMaster is None:
			print('  error: new_plotSparkMaster() did not find self.dr.dfSparkMaster')

		#print(self.dfSparkMaster.head)
		print('  sm columns:', self.dr.dfSparkMaster.columns)

		tifFirstFrameSeconds = self.dr.abfTif.tifHeader['firstFrameSeconds']
		tifSecondsPerLine = self.dr.abfTif.tifHeader['secondsPerLine']
		tifTotalSeconds = self.dr.abfTif.tifHeader['totalSeconds']
		print('  first frame of the image wrt pClamp abf as at', tifFirstFrameSeconds)

		xLineScanSum = self.dr.abfTif.sweepX + tifFirstFrameSeconds
		yLineScanSum = self.dr.abfTif.sweepY

		# now stripping leading spaces in SparkMaster columns (see loadSparkMaster)
		# remember: when traversing rows, t-pos is out of order w.r.t. time
		xSmStatStr = 't-pos' # t-pos is in seconds?
		xSmStat = self.dr.dfSparkMaster[xSmStatStr]
		# shift wrt tifFirstFrameSeconds
		xSmStatSec = [x+tifFirstFrameSeconds for x in xSmStat]

		yDoThisSmStat = 'FWHM' # 'Ampl.' # or 'FWHM'
		ySmStatStr = yDoThisSmStat
		ySmStat = self.dr.dfSparkMaster[ySmStatStr]

		yDoThisSmStat2 = 'Ampl.' # 'Ampl.' # or 'FWHM'
		ySmStatStr2 = yDoThisSmStat2
		ySmStat2 = self.dr.dfSparkMaster[ySmStatStr2]

		tPos_orig = self.dr.dfSparkMaster['t-pos']
		tPos_offset = tPos_orig + tifFirstFrameSeconds
		tPos_bin = [round(x/tifSecondsPerLine) for x in tPos_orig] # t-pos of each LCR as bin # (into tif)
		#print('tPos_bin:', tPos_bin)

		xPos = self.dr.dfSparkMaster['x-pos'] # pixel along line scan???

		#
		# bin sparkmaster time and count the number of LCR ROIs in a bin
		#print('  self.tifBins_ms:', self.tifBins_ms)
		tifBins_sec = self.tifBins_ms / 1000
		# important to consider wrt tifBins_sec
		xNumBins = math.floor(tifTotalSeconds / tifBins_sec)
		print('tifBins_sec:', tifBins_sec, 'xNumBins:', xNumBins, 'tifSecondsPerLine:', tifSecondsPerLine)
		# make new x-axis with bins
		xBins = [tifFirstFrameSeconds+(x*tifBins_sec) for x in range(xNumBins)]

		# if weights is None, will count LCR in each bin
		# if weight=ampl, will sum ampl for each LCRR in each bin
		weights = None
		weights = self.dr.dfSparkMaster['Ampl.']

		# plotted below
		#myHist,myBins = np.histogram(tPos_offset, weights=weights,
		#							bins=xBins)

		#
		# plot
		numPanels = 5
		fig, axs = plt.subplots(numPanels, 1, sharex=True)
		if numPanels == 1:
			axs = [axs]
		fig.canvas.mpl_connect('key_press_event', self.key_press_event)
		fig.canvas.mpl_connect('key_release_event', self.key_release_event)
		fig.canvas.mpl_connect('button_press_event', self.on_button_press_event)
		fig.canvas.mpl_connect('pick_event', self.onpick)

		titleStr = str(self.region)
		titleStr += ' ' + os.path.split(self.dr.abfTif.tifHeader['tif'])[1]
		titleStr += ' self.tifBins_ms:' + str(self.tifBins_ms)
		fig.suptitle(titleStr)

		# ephys Vm
		xVm = self.dr.abf.sweepX
		yVm = self.dr.abf.sweepY
		axs[0].plot(xVm, yVm, 'k')
		axs[0].set_ylabel('Vm (mV)')

		# sparkmaster over Vm
		axRight1 = axs[0].twinx()  # instantiate a second axes that shares the same x-axis
		axRight1.plot(xSmStatSec, ySmStat, '.b')
		#axRight1.set_xlabel(xStatStr)
		axRight1.set_ylabel('SM ' + ySmStatStr)

		#
		# sum of each line scan
		xLineScan = self.dr.abfTif.sweepX
		yLineScan = self.dr.abfTif.sweepY
		axs[1].plot(xLineScanSum, yLineScan, 'r')
		axs[1].set_ylabel('Ca Line Scan Sum')

		# sparkmaster over Ca Line Scan Sum
		axRight1 = axs[1].twinx()  # instantiate a second axes that shares the same x-axis
		axRight1.plot(xSmStatSec, ySmStat2, '.b')
		#axRight1.set_xlabel(xStatStr)
		axRight1.set_ylabel('SM ' + ySmStatStr2)

		#
		axs[2].plot(xVm, yVm, '-k')
		axs[2].set_ylabel('Vm (mV)')

		self.axRight2 = axs[2].twinx()  # instantiate a second axes that shares the same x-axis
		#axRight2.plot(xLineScanSum, yLineScanSum, '-r')
		n, bins, patches = self.axRight2.hist(tPos_offset, weights=weights,
									bins=xBins,
									facecolor='k', histtype='step')
		if weights is None:
			self.axRight2.set_ylabel('SM LCR Count')
		else:
			self.axRight2.set_ylabel('SM LCR Weight (amp)')
		# once we mask out Ca++ in response to spikes
		# we do not need log plot !!!
		#axRight2.set_yscale('log')

		#
		# plot tif image overlaid with position of LCRs
		if 1:
			firstFrameSeconds = self.dr.abfTif.tifHeader['firstFrameSeconds']
			xMin = firstFrameSeconds
			xMax = firstFrameSeconds + self.dr.abfTif.sweepX[-1]
			yMin = 0
			yMax = self.dr.abfTif.tifHeader['umLength'] #57.176
			#extent = [xMin, xMaxImage, yMax, yMin] # flipped y
			extent = [xMin, xMax, yMin, yMax] # flipped y
			axs[3].imshow(self.dr.abfTif.tif, extent=extent, aspect='auto')
			axs[3].spines['right'].set_visible(False)
			axs[3].spines['top'].set_visible(False)

			axRight3 = axs[3].twinx()  # instantiate a second axes that shares the same x-axis
			axRight3.plot(tPos_offset, xPos, '.r')

		#
		# plot analysis results, both (picked lcr) and (picked vm)

		axsLcrAnalysisLeft = axs[4]
		self.vmAnalysisLine2D, = axs[4].plot([], [], 'ob')

		axsLcrAnalysisRight = axs[4].twinx()  # instantiate a second axes that shares the same x-axis
		self.lcrAnalysisLine2D, = axsLcrAnalysisRight.plot(self.dfAnalysis['lcrSec'],
								self.dfAnalysis['lcrSum'],
								'or',
								picker=5)
		self.lcrAnalysisSelectionLine2D, = axsLcrAnalysisRight.plot([],
								[],
								'oy')

		return fig, axs, tPos_offset, n, bins, axsLcrAnalysisLeft, axsLcrAnalysisRight

if __name__ == '__main__':
	df = dualAnalysis.loadDatabase() # loads and appends some full path columns

	# manual analysis
	if 0:
		row = 3 #4
		row = 4
		row = 8
		# 20210122__0002 really high frequency spikes, Vm is always falling/rising b/w APs
		row = 9
		row = 11
		row = 14
		row = 15 # not many lcr, lots on ap upstroke
		row = 16 # not many lcr, lots on ap upstroke
		row = 19
		row = 20
		row = 22 # not many lcr, most on ap upstroke
		row = 26 # lots of isolated lcr, flat vm between spikes --- GOOD
		row = 27
		row = 29
		#row = 33 # did not analyze, no LCR in kymograph
		row = 34
		row = 35

		#print(df.columns)
		lcrPick = lcrPicker(row, df)

		plt.show()

	#20210312 NO SPIKE DETECT
	if 0:
		#row = 5 # 20210312
		#row = 6	# 20210313
		#row = 7 # NOT ANALYZED ... BAD LINE SCAN
		row = 13
		#row = 30
		#row = 31
		lcrPick = lcrPicker(row, df, doVmDetect=False)
		plt.show()

	if 1:
		mergeDatabase(df)
