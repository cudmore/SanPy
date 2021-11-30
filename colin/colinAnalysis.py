"""
"""

import os
import time
import pandas as pd
import numpy as np
import scipy.signal
import pyabf

# for baseline
from scipy import sparse
from scipy.sparse.linalg import spsolve

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import ipywidgets as widgets
import IPython.display

import matplotlib as mpl
mpl.rcParams['axes.spines.right'] = False
mpl.rcParams['axes.spines.top'] = False

import colinUtils

class colinAnalysis:
	def __init__(self, folderPath):
		"""
		Load all files from a directory
		"""

		self._folderPath = folderPath

		self._analysisIdx = 0  # the first abf

		# list of dict to hold all raw data and analysis
		self._myDictList = []

		#
		# load files
		# todo: defer loading until file is selected in interface
		self._filePathList = []  # list of string
		self._abfList = []  # list of pyAbf
		self._analysisList = []  # list of self.analysisDict
		for file in sorted(os.listdir(folderPath)):
			if file.startswith('.'):
				continue
			if file.endswith('.abf'):
				filePath = os.path.join(folderPath, file)
				oneAbf = pyabf.ABF(filePath)
				self._filePathList.append(filePath)
				self._abfList.append(oneAbf)
				self._analysisList.append(None)

				oneDict = {
					'filePath': filePath,
					'abf': oneAbf,
					'analysis': [],
				}
				self._myDictList.append(oneDict)

		# for GUI
		self._currentPeakIdx = 0

	def __str__(self):
		return ('xxx')

	def getStatList(self):
		"""
		get list of stats corresponding to df columns. Used to plot scatter
		"""
		statList = [
					'index',
					'file',
					'genotype',
					'sex',
					'userType',
					'DAC0',
					'peakNum',
					'peak_sec',
					'peak_val',
					'myHeight',
					'riseTime_ms',
					'ipi_ms',
					'instFreq_hz',
					'footSec',
					'footVal',
					'hw20_width_ms',
					'hw50_width_ms',
					'hw80_width_ms',
					'myFileIdx',
					'myMasterIdx',
					]
		return statList

	def setAnalysisIdx(self, newIdx):
		if newIdx > len(self._analysisList) - 1:
			print(f'ERROR idx must be less than {len(self._analysisList) - 1}')
		else:
			self._analysisIdx = newIdx

	def getAnalysis(self, analysisIdx=None):
		"""
		Get a dictionary of current analysis from analysisIndex
		"""
		if analysisIdx is None:
			analysisIdx = self._analysisIdx
		return self._analysisList[analysisIdx]

	def getDataFrame(self):
		return self.getAnalysis()['results_full']

	def getAllDataFrame(self):
		df = None
		totalNum = 0
		for idx, analysis in enumerate(self._analysisList):
			if analysis is None:
				print(f'   skipping file {idx}, no analysis')
				continue
			thisDf = analysis['results_full']
			thisDf['myFileIdx'] = idx
			thisDf['myMasterIdx'] = [totalNum+x for x in range(len(thisDf))]  # todo: improve efficiency

			if df is None:
				df = thisDf
			else:
				df = df.append(thisDf, ignore_index=True)

			totalNum += len(thisDf)
		#
		return df

	def getAbf(self, analysisIdx=None):
		"""
		Get a dictionary of current analysis from analysisIndex
		"""
		if analysisIdx is None:
			analysisIdx = self._analysisIdx
		return self._abfList[analysisIdx]

	@property
	def numFiles(self):
		return len(self._analysisList)

	@property
	def numPeaks(self):
		df = self.getDataFrame()
		return len(df)

	'''
	@property
	def currentPeakIdx(self):
		"""GUI Interface"""
		return self._currentPeakIdx
	'''

	@property
	def currentAbf(self):
		analysisIdx = self._analysisIdx
		return self._abfList[analysisIdx]

	def getFileList(self):
		retList = []
		for fileIdx in range(self.numFiles):
			oneFile = self._filePathList[fileIdx]
			oneFile = os.path.split(oneFile)[1]
			retList.append(oneFile)
		return retList

	@property
	def currentPath(self):
		analysisIdx = self._analysisIdx
		return self._filePathList[analysisIdx]

	@property
	def currentFile(self):
		return os.path.split(self.currentPath)[1]

	@property
	def sweepX(self):
		return self.currentAbf.sweepX

	@property
	def sweepY(self):
		return self.currentAbf.sweepY

	@property
	def sweepC(self):
		return self.currentAbf.sweepC

	@property
	def sweepY_filtered(self):
		analysis = self.getAnalysis()
		return analysis['sweepY_filtered']

	'''
	def myShow(self):
		self.initGui()

		self.refreshPlot()

		#self.replotScatter()
	'''

	'''
	def initGui(self):
		"""
		Assumes analysis has been performed
		"""
		self.zoomSec1 = 10.0
		self.zoomSec2 = 0.2

		numSubplot = 3
		self.fig, self.axs = plt.subplots(numSubplot, 1, figsize=(8, 6))
		self.axs[0].grid(True)
		self.axs[1].grid(True)
		self.axs[2].grid(True)

		# selected point slider
		min = 0
		max = self.numPeaks
		myPointSlider = widgets.IntSlider(min=min, max=max, step=1,
										   value=self.currentPeakIdx,
										   continuous_update=False,
										  description='Peak Number')
		myPointSlider.observe(self.on_value_change, names='value')

		#
		min = 0.1
		max = self.sweepX[-1]
		myZoomSlider1 = widgets.FloatSlider(min=min, max=max, step=0.1,
										   value=self.zoomSec1,
										   continuous_update=False,
										  description='Zoom 1 (Sec)')
		myZoomSlider1.observe(self.on_zoom1_change, names='value')

		min = 0.1
		max = self.sweepX[-1]
		myZoomSlider2 = widgets.FloatSlider(min=min, max=max, step=0.1,
										   value=self.zoomSec2,
										   continuous_update=False,
										  description='Zoom 2 (Sec)')
		myZoomSlider2.observe(self.on_zoom2_change, names='value')

		hBox = widgets.HBox([myPointSlider, myZoomSlider1, myZoomSlider2])
		display(hBox)

		# prev and next buttons
		prevButton = widgets.Button(description='<')
		prevButton.on_click(self.on_prev_button)

		nextButton = widgets.Button(description='>')
		nextButton.on_click(self.on_next_button)

		# accept and reject
		acceptButton = widgets.Button(description='Accept')
		acceptButton.on_click(self.on_accept_button)

		rejectButton = widgets.Button(description='Reject')
		rejectButton.on_click(self.on_reject_button)

		hBox = widgets.HBox([prevButton, nextButton, acceptButton, rejectButton])
		display(hBox)

		saveButton = widgets.Button(description='Save')
		saveButton.on_click(self.on_save_button)

		# output widget so we can give feedback like selected pnt number
		self.myOut = widgets.Output()

		hBox = widgets.HBox([saveButton, self.myOut])
		display(hBox)
	'''

	'''
	def on_zoom1_change(self, n):
		# print('on_zoom1_change')
		self.zoomSec1 = n['new']
		self.refreshPlot()
	'''

	'''
	def on_zoom2_change(self, n):
		# print('on_zoom2_change')
		self.zoomSec2 = n['new']
		self.refreshPlot()
	'''

	'''
	def updateMyOut(self, peakPnt:int = None):
		if peakPnt is None:
			peakPnt = self._currentPeakIdx

		df = self.getDataFrame()
		riseTime_ms = df.iloc[peakPnt]['riseTime_ms']
		riseTime_ms = round(riseTime_ms,2)
		height = df.iloc[peakPnt]['myHeight']
		height = round(height,2)
		with self.myOut:
			IPython.display.clear_output()
			print('Peak Index:', peakPnt, 'Amp (pA):', height, 'Rise Time (ms):', riseTime_ms)
	'''

	'''
	def updateMyOut2(self, s):
		with self.myOut:
			IPython.display.clear_output()
			print(s)
	'''

	'''
	def on_value_change(self, n):
		"""
		n (dist): Dict with things like n['new']
		"""
		#print('on_value_change n:', n['new'])
		self._currentPeakIdx = n['new']  # new value

		with self.myOut:
			IPython.display.clear_output()
			self.updateMyOut()

		self.refreshPlot()
	'''

	'''
	def setAccept(self, newValue, peakIdx=None):
		if peakIdx is None:
			peakIdx = self._currentPeakIdx
		self.getDataFrame().loc[peakIdx, 'accept'] = newValue
	'''

	'''
	def on_accept_button(self, e):
		with self.myOut:
			print('on_accept_button() peak:', self.currentPeakIdx)
			# todo: put into function
			#self.myAcceptList[self._currentPeakIdx] = True
			self.setAccept(True)  # will use current gui nidex

		self.refreshPlot()
	'''

	'''
	def on_reject_button(self, e):
		with self.myOut:
			print('on_reject_button() peak:', self.currentPeakIdx)
			# todo: put into function
			#self.myAcceptList[self._currentPeakIdx] = False
			self.setAccept(False)  # will use current gui nidex
		self.refreshPlot()
	'''

	'''
	def on_prev_button(self, e):
		self._currentPeakIdx -= 1
		if self._currentPeakIdx < 0:
			self._currentPeakIdx = 0

		with self.myOut:
			IPython.display.clear_output()
			self.updateMyOut()

		self.refreshPlot()
	'''

	'''
	def on_next_button(self, e):
		self._currentPeakIdx += 1
		if self._currentPeakIdx > self.numPeaks - 1:
			self._currentPeakIdx = self.numPeaks - 1

		with self.myOut:
			IPython.display.clear_output()
			self.updateMyOut()

		self.refreshPlot()
	'''

	'''
	def on_save_button(self, e):
		self.save()
	'''

	def getDefaultDetection(self):
		 # detect peaks (peak, prominence, width)
		detectionDict = {
			'medianFilter' : 9,  # points, must be odd
			'height' : 4, #6, #3,  # minimum height
			'distance': 250,  # minimum number of points between peaks
			#'prominence': None, #10,  # could also be [min, max]
			'wlen': 1500,
			'width': [50, 500],  # [min, max] required
			'halfWidths': [20, 50, 80],
			'fullWidthFraction': 0.75,
			'xRange': None,
			'condition': None,
			'genotype': None,
			'sex': None,
		}
		return detectionDict

	def _baseline_als_optimized(self, y, lam, p, niter=10):
		"""
		p for asymmetry and lam for smoothness.
		generally:
			0.001 ≤ p ≤ 0.1
			10^2 ≤ lam ≤ 10^9
		"""
		start = time.time()

		L = len(y)
		D = sparse.diags([1,-2,1],[0,-1,-2], shape=(L,L-2))
		D = lam * D.dot(D.transpose()) # Precompute this term since it does not depend on `w`
		w = np.ones(L)
		W = sparse.spdiags(w, 0, L, L)
		for i in range(niter):
			W.setdiag(w) # Do not create a new matrix, just update diagonal values
			Z = W + D
			z = spsolve(Z, w*y)
			w = p * (y > z) + (1-p) * (y < z)

		stop = time.time()
		#print(f'  _baseline_als_optimized() took {round(stop-start, 3)} seconds')
		return z

	def detect(self, detectionDict=None, verbose = True):
		"""
		xRange (list): [start second, stop second]
		"""
		startSec = time.time()

		if detectionDict is None:
			detectionDict = self.getDefaultDetection()

		# detect peaks (peak, prominence, width)
		medianFilter = detectionDict['medianFilter']
		height = detectionDict['height']
		distance = detectionDict['distance']
		#prominence = detectionDict['prominence']
		wlen = detectionDict['wlen']
		width = detectionDict['width']
		#halfWidthFraction = detectionDict['halfWidthFraction']
		fullWidthFraction = detectionDict['fullWidthFraction']
		xRange = detectionDict['xRange']

		analysis = self.getAnalysis()
		doFilter = analysis is None

		if doFilter:
			if medianFilter > 0:
				#sweepY_filtered = scipy.signal.medfilt(self.sweepY, medianFilter)
				SavitzkyGolay_pnts = 11 #5
				SavitzkyGolay_poly = 5 # 2
				sweepY_filtered = scipy.signal.savgol_filter(self.sweepY,
									SavitzkyGolay_pnts, SavitzkyGolay_poly,
									mode='nearest', axis=0)
			else:
				sweepY_filtered = self.sweepY
		else:
			sweepY_filtered = analysis['sweepY_filtered']

		filePath = self._filePathList[self._analysisIdx]

		analysisDict = {
			'filePath': filePath,
			'file': os.path.split(filePath)[1],
			'detection': detectionDict,  # detection parameters we used
			'peaks' : None,  # list of peak points (float)
			#'properties' : None,  # dict with keys {peak_height, prominences, left_bases, right_bases, widths, width_heights, left_ips, right_ips}
			#'halfWidth' : None,  # converted to seconds [0] is width, [1] heights, [2] is start, [3] is stop
			'fullWidth' : None,  # converted to seconds [0] is width, [1] heights, [2] is start, [3] is stop
			#'accept' : None,  # list of boolean
			#'userType' : None,  # list of boolean
			#'userNote' : None,  # list of boolean
			'sweepY_filtered': sweepY_filtered,
			'results_full': None,  # filled in at end, pandas df
			}

		# todo: fix
		# detect on all then mask at end
		#if xRange is None:
		#	xRange = [self.sweepX[0], self.sweepX[-1]]
		#xMask = (self.sweepX >= xRange[0]) & (self.sweepX <= xRange[1])
		#y = sweepY_filtered[xMask]
		y = sweepY_filtered

		# use different versions of sweepY
		#y = self.sweepY
		if doFilter:
			lam = 1e13
			p = 0.5
			z = self._baseline_als_optimized(y, lam, p, niter=10)
			y = y - z
			analysisDict['sweepY_filtered'] = y

		#
		# find peaks
		analysisDict['peaks'], analysisDict['properties'] = scipy.signal.find_peaks(y, height=height,
														distance=distance,
														prominence=None,
														wlen=None,
														width=width)

		numPeaks = len(analysisDict['peaks'])

		if numPeaks < 2:
			# ABORT
			print('error: did not detect enough peaks', numPeaks)
			return
			
		# full height to then get foot
		analysisDict['fullWidth'] = scipy.signal.peak_widths(y, analysisDict['peaks'],
															wlen=wlen,
															rel_height=fullWidthFraction)
		newWidthSec = []
		# [0] is width, [1] heights, [2] is start, [3] is stop
		for idx, widths in enumerate(analysisDict['fullWidth']):
			if idx==1:
				newWidthSec.append(widths)
			else:
				newWidthSec.append(self._pnt2Sec(widths))
		analysisDict['fullWidth'] = tuple(newWidthSec)

		#
		# order matter

		# assign to list
		self._analysisList[self._analysisIdx] = analysisDict

		self._analysisList[self._analysisIdx]['results_full'] = self._asDataFrame()

		self._getFeet()

		stopSec = time.time()
		#if verbose:
		#	print('  file:', analysisDict['filePath'])
		#	print(f'  detect() found {numPeaks} peaks in {round(stopSec-startSec,2)} seconds.')
		#	#print(f'  xRange: {xRange}, Analysis dur (s) {xRange[1] - xRange[0]}')

	def _getFeet(self):
		# backup each peak to 0 crossing in derivative
		df = self._analysisList[self._analysisIdx]['results_full']

		yFull = self.sweepY_filtered
		yDiffFull = np.diff(yFull)
		yDiffFull = np.insert(yDiffFull, 0, np.nan)
		fullWidth_left_pnt = df['fullWidth_left_pnt']
		#peakPnt = theseRowDf['peak_pnt']
		footSec = []
		yFoot = []
		myHeight = []
		preMs = 5
		prePnts = self._sec2Pnt(preMs/1000)
		for idx,footPnt in enumerate(fullWidth_left_pnt):
			# move forwared a bit in case we are already in a local minima ???
			footPnt += 2
			preStart = footPnt - prePnts
			preClip = yDiffFull[preStart:footPnt]
			zero_crossings = np.where(np.diff(np.sign(preClip)))[0]
			xLastCrossing = self._pnt2Sec(footPnt)  # defaults
			yLastCrossing = self.sweepY[footPnt]
			if len(zero_crossings)==0:
				print('  error: no foot', idx, self._pnt2Sec(footPnt), 'did not find zero crossings')
				footSec.append(xLastCrossing)
				yFoot.append(yLastCrossing)
			else:
				#print(idx, 'footPnt:', footPnt, zero_crossings, preClip)
				lastCrossingPnt = preStart + zero_crossings[-1]
				xLastCrossing = self._pnt2Sec(lastCrossingPnt)
				# get y-value (pA) from filtered. This removes 'pops' in raw data
				#yLastCrossing = self.sweepY[lastCrossingPnt]
				yLastCrossing = self.sweepY_filtered[lastCrossingPnt]

			#
			footSec.append(xLastCrossing)
			yFoot.append(yLastCrossing)

			#if len(df) == 127:
			#	print('df:', df.head())

			peakPnt = df.loc[idx, 'peak_pnt']
			peakVal = self.sweepY[peakPnt]
			height = peakVal - yLastCrossing
			#print(f'idx {idx} {peakPnt} {peakVal} - {yLastCrossing} = {height}')
			myHeight.append(height)

		#
		#df =self._analysisList[self._analysisIdx]['results_full']
		df['footSec'] = footSec  # sec
		df['footVal'] = yFoot  # pA
		df['myHeight'] = myHeight

		#
		# half-width
		numPeaks = self.numPeaks
		halfWidths = self.getAnalysis()['detection']['halfWidths']
		maxWidthPnts = self.getAnalysis()['detection']['distance']
		maxWidthSec = self._pnt2Sec(maxWidthPnts)

		for halfWidth in halfWidths:
			leftList = [None] * numPeaks
			rightList = [None] * numPeaks
			heightList = [None] * numPeaks
			widthList = [None] * numPeaks
			for idx,pnt in enumerate(df['peak_pnt']):
				xFootSec = df.loc[idx, 'footSec']
				yFootVal = df.loc[idx, 'footVal']
				peakSec = df.loc[idx, 'peak_sec']
				peakVal = df.loc[idx, 'peak_val']
				halfHeight = yFootVal + (peakVal - yFootVal) * (halfWidth * 0.01)

				startSec = xFootSec
				startPrePnt = self._sec2Pnt(startSec)
				stopSec = peakSec # xFootSec + maxWidthSec
				preClipMask = (self.sweepX>=startSec) & (self.sweepX<=stopSec)
				preClip = self.sweepY_filtered[preClipMask]

				startSec = peakSec
				startPostPnt = self._sec2Pnt(startSec)
				stopSec = startSec + maxWidthSec
				postClipMask = (self.sweepX>=startSec) & (self.sweepX<=stopSec)
				postClip = self.sweepY_filtered[postClipMask]

				#if halfWidth == 50:
				#	print(idx, halfWidth, yFootVal, peakVal, halfHeight)
				threshold_crossings = np.diff(preClip > halfHeight, prepend=False)
				upward = np.argwhere(threshold_crossings)[::2,0]  # Upward crossings

				if len(upward > 0):
					firstUpPnt = startPrePnt + upward[0]
					leftList[idx] = self._pnt2Sec(firstUpPnt)

				threshold_crossings = np.diff(postClip > halfHeight, prepend=False)
				downward = np.argwhere(threshold_crossings)[1::2,0]  # Downward crossings
				if len(downward > 0):
					lastDownPnt = startPostPnt + downward[-1]
					rightList[idx] = self._pnt2Sec(lastDownPnt)

				if len(upward > 0) and len(downward > 0):
					heightList[idx] = halfHeight
					widthList[idx] = (rightList[idx] - leftList[idx]) * 1000

			#
			keyBase = 'hw' + str(halfWidth) + '_'
			df[keyBase+'width_ms'] = widthList
			df[keyBase+'left_sec'] = leftList
			df[keyBase+'right_sec'] = rightList
			df[keyBase+'val'] = heightList # y val of height

			#
			# rise time ms
			df['riseTime_ms'] = (df['peak_sec'] - df['footSec']) * 1000

	def plotOne(self, onePeak : int = None, zoomSec: float = None):
		analysis = self.getAnalysis()
		df = analysis['results_full']

		xMin = 0
		xMax = self.sweepX[-1]
		if onePeak is not None:
			onePeakSec = df.iloc[onePeak]['peak_sec']
			if zoomSec is not None:
				xMin = onePeakSec - zoomSec
				xMax = onePeakSec + zoomSec

		print('plotOne() xMin:', xMin, 'xMax:', xMax)

		xMask = (self.sweepX >= xMin) & (self.sweepX <= xMax)
		xPlot = self.sweepX[xMask]
		yPlot = self.sweepY[xMask]
		yPlotFiltered = self.sweepY_filtered[xMask]

		# plot
		numSubplot = 2
		fig, axs = plt.subplots(numSubplot, 1, sharex=True, figsize=(12, 6))
		#axs = [axs]

		# raw data
		axs[0].plot(xPlot, yPlot, 'k', linewidth=0.5)
		axs[0].plot(xPlot, yPlotFiltered, 'r', linewidth=0.5)

		# just the rows (peaks) within (xMin, xMax)
		theseRowDf = df[ (df['peak_sec']>=xMin) & (df['peak_sec']<=xMax)]
		#print('theseRowDf', type(theseRowDf))

		# peaks
		xPlotPeak = theseRowDf['peak_sec']
		yPlotPeak = self.sweepY_filtered[theseRowDf['peak_pnt']]
		axs[0].scatter(xPlotPeak, yPlotPeak)

		'''
		xPlotFoot = theseRowDf['fullWidth_left_sec']
		yPlotFoot = self.sweepY_filtered[theseRowDf['fullWidth_left_pnt']]
		axs[0].scatter(xPlotFoot, yPlotFoot, c='r')
		'''

		#
		# dvdt
		yDiff = np.diff(yPlot)
		yDiff = np.insert(yDiff, 0, np.nan)

		axs[1].plot(xPlot, yDiff, 'r', linewidth=0.5)

		footSec = theseRowDf['footSec']
		yFoot = theseRowDf['footVal']
		axs[0].scatter(footSec, yFoot, c='g')

	def plotClips(self):
		"""
		plot aligned clips

		alignment is done using footSec/yFoot
		"""
		numSubplot = 1
		fig, axs = plt.subplots(numSubplot, 1, figsize=(8, 6))
		axs = [axs]

		preSec = 0.05
		postSec = 0.2

		df = self.getDataFrame()
		acceptList = df['accept']
		peak_pnt = df['peak_pnt']
		footSec = df['footSec']
		yFoot = df['footVal']

		for idx, peakPnt in enumerate(peak_pnt):

			if not acceptList[idx]:
				continue

			xFootSec = footSec[idx]
			startSec = xFootSec - preSec
			stopSec = xFootSec + postSec

			rawMask = (self.sweepX>=startSec) & (self.sweepX<=stopSec)
			yOneClip = self.sweepY[rawMask]
			xOneClip = np.linspace(-preSec, postSec, num=len(yOneClip))

			# normalize to foot
			yFootVal = yFoot[idx]
			yOneClip -= yFootVal

			axs[0].plot(xOneClip, yOneClip, '-')

	def _asDataFrame(self):

		analysis = self.getAnalysis()
		filePath = analysis['filePath']
		peaks = analysis['peaks']  # (int), not interpolated
		properties = analysis['properties']
		#halfWidth = analysis['halfWidth']
		fullWidth = analysis['fullWidth']
		detection = analysis['detection']
		#detection = analysis['detection']

		#sweepY_filtered = analysis['sweepY_filtered']
		sweepY_filtered = self.sweepY_filtered

		peaksSec = self._pnt2Sec(peaks)
		numPeaks = len(peaks)

		df = pd.DataFrame()

		file = os.path.split(filePath)[1]
		df['file'] = [file] * len(peaks)
		df['genotype'] = [detection['genotype']] * len(peaks)
		df['sex'] = [detection['sex']] * len(peaks)

		df['DAC0'] = self.sweepC[peaks]
		df['peakNum'] = [idx for idx,peak in enumerate(peaks)]
		df['accept'] = [True] * numPeaks  # analysis['accept']
		df['userType'] = [0] * numPeaks  # valid values are (int) [0,9]
		df['peak_pnt'] = peaks  # points
		df['peak_sec'] = peaksSec
		df['peak_val'] = sweepY_filtered[peaks]

		instFreq_hz = 1 / np.diff(peaksSec)
		instFreq_hz = np.insert(instFreq_hz, 0, np.nan)

		ipi_ms = np.diff(peaksSec) * 1000
		ipi_ms = np.insert(ipi_ms, 0, np.nan)

		df['ipi_ms'] = ipi_ms
		df['instFreq_hz'] = instFreq_hz

		df['fullWidth_left_pnt'] = self._sec2Pnt(fullWidth[2])
		#df['fullWidth_right_pnt'] = self._sec2Pnt(fullWidth[3])

		df['userNote'] = [''] * numPeaks

		detection = self.getAnalysis()['detection']
		for k,v in detection.items():
			detectionKey = 'd_' + k
			if isinstance(v, list):
				v = str(v)
			df[detectionKey] = v

		df['filePath'] = filePath

		#
		# reduce based on x-range
		xRange = detection['xRange']
		if xRange is None:
			xRange = [self.sweepX[0], self.sweepX[-1]]
		df = df[ (df['peak_sec'] >= xRange[0]) & (df['peak_sec'] <= xRange[1]) ]
		df = df.reset_index()

		numSweeps = len(self.getAbf().sweepList)
		recordingDur = round(self.sweepX[-1],2)
		print('  ', self.currentFile, 'Num Sweeps:', numSweeps, 'Recording Dur:', recordingDur, 'Peaks within xRange:', xRange, 'to', len(df), 'peaks')

		return df

	def save(self):
		"""
		todo: need to keep track of filewe are workng on, not the folder (colin) with files
		"""


		analysis = self.getAnalysis()
		filePath = analysis['filePath']
		folderPath, filename = os.path.split(filePath)

		#print( '  ', folderPath)
		#print( '  ', filename)

		paramFile = os.path.splitext(filename)[0] + '_params.txt'
		paramFile = os.path.join(folderPath, paramFile)

		analysisFile = os.path.splitext(filename)[0] + '_analysis.txt'
		analysisFile = os.path.join(folderPath, analysisFile)

		#print('  todo: paramFile:', paramFile)
		#print('  todo: analysisFile:', analysisFile)

		# saving is complicated because we have (peaks, halfWidth, fullWidth)

		analysis = self.getAnalysis()

		'''
		summaryFile = os.path.splitext(filename)[0] + '_summary.csv'
		summaryPath = os.path.join(folderPath, summaryFile)
		print('saving summary:', summaryPath)
		results_summary = analysis['results_summary']
		results_summary.to_csv(summaryPath)
		'''

		resultsFile = os.path.splitext(filename)[0] + '_full.csv'
		resultsPath = os.path.join(folderPath, resultsFile)
		#print('saving full:', resultsPath)
		results_full = analysis['results_full']  # pandas dataframe
		results_full.to_csv(resultsPath)

		return resultsPath

	def _pnt2Sec(self, pnt):
		dataPointsPerMs = self.currentAbf.dataPointsPerMs
		if isinstance(pnt, list):
			return [onePnt / dataPointsPerMs / 1000 for onePnt in pnt]
		else:
			return pnt / dataPointsPerMs / 1000

	def _sec2Pnt(self, sec):
		"""
		Returns:
			point(s) as int(s)
		"""
		dataPointsPerMs = self.currentAbf.dataPointsPerMs
		if isinstance(sec, list):
			return [round(onePnt * 1000 * dataPointsPerMs) for onePnt in sec]
		elif isinstance(sec, np.ndarray):
			ms = sec * 1000 * dataPointsPerMs
			pnt = np.around(ms).astype(int)
			return pnt
		else:
			#print('ERROR: _sec2Pnt() got unexpected type:', type(sec))
			return round(sec * 1000 * dataPointsPerMs)

if __name__ == '__main__':
	path = '/media/cudmore/data/colin'
	ca = colinAnalysis(path)
	ca._analysisIdx = 0
	ca.detect()

	'''
	a = ca.getAnalysis()
	for k,v in a.items():
		if isinstance(v, dict):
			print(k, 'dict')
			for k2,v2 in v.items():
				print('  ', k2, ':', v2)
		elif isinstance(v, tuple):
			print(k, 'tuple', '[0] width, [1] heights, [2] start, [3] stop')
			for idx,item in enumerate(v):
				print('  ', idx, ':', item)
		else:
			print(k, ':', v)
	'''

	#ca.testPlot()
	onePeak = None
	zoomSec = None
	ca.plotOne(onePeak=onePeak, zoomSec=zoomSec)

	#
	plt.show()

	print(ca.getDataFrame().head())
	#print(ca.getDataFrame()['myHeight'])

	#print(ca)
	#ca.myShow()

	#print(ca.getAnalysis())

	# test save
	#ca.save()
