"""
"""

import os
import time
import pandas as pd
import numpy as np
import scipy.signal
import pyabf

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import ipywidgets as widgets
import IPython.display

import matplotlib as mpl
mpl.rcParams['axes.spines.right'] = False
mpl.rcParams['axes.spines.top'] = False

class colinAnalysis:
	def __init__(self, folderPath):
		"""
		Load all files from a directory
		"""

		self._folderPath = folderPath

		self._analysisIdx = 0  # the first abf
		#
		# load files
		# todo: defer loading until file is selected in interface
		self._filePathList = []  # list of string
		self._abfList = []  # list of pyAbf
		self._analysisList = []  # list of self.analysisDict
		for file in os.listdir(folderPath):
			if file.startswith('.'):
				continue
			if file.endswith('.abf'):
				filePath = os.path.join(folderPath, file)
				oneAbf = pyabf.ABF(filePath)
				self._filePathList.append(filePath)
				self._abfList.append(oneAbf)
				self._analysisList.append(None)

		#
		self.detectionDict = self.defaultDetection()

		#
		#self.detect()

		self._currentPeakIdx = 0


	def __str__(self):
		return ('xxx')

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
		analysis = self.getAnalysis()
		peaks = analysis['peaks']
		if peaks is None:
			return None
		else:
			return len(peaks)

	@property
	def currentPeakIdx(self):
		"""Interface"""
		return self._currentPeakIdx

	@property
	def currentAbf(self):
		analysisIdx = self._analysisIdx
		return self._abfList[analysisIdx]

	@property
	def sweepX(self):
		return self.currentAbf.sweepX

	@property
	def sweepY(self):
		return self.currentAbf.sweepY

	@property
	def sweepY_filtered(self):
		analysis = self.getAnalysis()
		return analysis['sweepY_filtered']

	def myShow(self):
		self.initGui()

		self.refreshPlot()

		#self.replotScatter()

	def initGui(self):
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

		# scatter
		#self.scatterWidget()

	def on_zoom1_change(self, n):
		# print('on_zoom1_change')
		self.zoomSec1 = n['new']
		self.refreshPlot()

	def on_zoom2_change(self, n):
		# print('on_zoom2_change')
		self.zoomSec2 = n['new']
		self.refreshPlot()

	def on_value_change(self, n):
		"""
		n (dist): Dict with things like n['new']
		"""
		#print('on_value_change n:', n['new'])
		self._currentPeakIdx = n['new']

		with self.myOut:
			IPython.display.clear_output()
			print(self._currentPeakIdx)

		self.refreshPlot()

	def setAccept(self, newValue, peakIdx=None):
		if peakIdx is None:
			peakIdx = self._currentPeakIdx
		analysis = self.getAnalysis()
		analysis['accept'][peakIdx] = newValue

	def on_accept_button(self, e):
		with self.myOut:
			print('on_accept_button() peak:', self.currentPeakIdx)
			# todo: put into function
			#self.myAcceptList[self._currentPeakIdx] = True
			self.setAccept(True)  # will use current gui nidex

		self.refreshPlot()

	def on_reject_button(self, e):
		with self.myOut:
			print('on_reject_button() peak:', self.currentPeakIdx)
			# todo: put into function
			#self.myAcceptList[self._currentPeakIdx] = False
			self.setAccept(False)  # will use current gui nidex
		self.refreshPlot()

	def on_prev_button(self, e):
		self._currentPeakIdx -= 1
		if self._currentPeakIdx < 0:
			self._currentPeakIdx = 0

		with self.myOut:
			IPython.display.clear_output()
			print(self._currentPeakIdx)

		self.refreshPlot()

	def on_next_button(self, e):
		self._currentPeakIdx += 1
		if self._currentPeakIdx > self.numPeaks - 1:
			self._currentPeakIdx = self.numPeaks - 1

		with self.myOut:
			IPython.display.clear_output()
			print(self._currentPeakIdx)

		self.refreshPlot()

	def on_save_button(self, e):
		self.save()

	def defaultDetection(self):
		 # detect peaks (peak, prominence, width)
		detectionDict = {
			'medianFilter' : 9,  # points, must be odd
			'height' : 6, #3,  # minimum height
			'distance': 250,  # minimum number of points between peaks
			'prominence': 4,  # could also be [min, max]
			'width': [20, 500],  # [min, max] required
			'halfWidthFraction': 0.5,
			'fullWidthFraction': 0.8,
		}
		return detectionDict

	def detect(self, verbose = True):
		startSec = time.time()

		# detect peaks (peak, prominence, width)
		medianFilter = self.detectionDict['medianFilter']
		height = self.detectionDict['height']
		distance = self.detectionDict['distance']
		prominence = self.detectionDict['prominence']
		width = self.detectionDict['width']
		halfWidthFraction = self.detectionDict['halfWidthFraction']
		fullWidthFraction = self.detectionDict['fullWidthFraction']

		if medianFilter > 0:
			sweepY_filtered = scipy.signal.medfilt(self.sweepY, medianFilter)
		else:
			sweepY_filtered = self.sweepY

		analysisDict = {
			'filePath': self._filePathList[self._analysisIdx],
			'detection': self.detectionDict,
			'peaks' : None,  # list of peak points (float)
			'properties' : None,  # dict with keys {peak_height, prominences, left_bases, right_bases, widths, width_heights, left_ips, right_ips}
			'halfWidth' : None,  # converted to seconds [0] is width, [1] heights, [2] is start, [3] is stop
			'fullWidth' : None,  # converted to seconds [0] is width, [1] heights, [2] is start, [3] is stop
			'accept' : None,  # list of boolean
			'sweepY_filtered': sweepY_filtered,
			'results_summary': None,  # filled in at end
			'results_full': None,
			}

		y = sweepY_filtered
		analysisDict['peaks'], analysisDict['properties'] = scipy.signal.find_peaks(y, height=height,
														distance=distance,
														prominence=prominence,
														width=width)

		#scipy.signal.peak_widths(x, peaks, rel_height=0.5, prominence_data=None, wlen=None)[source]
		# _halfWidth is tuple, [0] is actual widths
		analysisDict['halfWidth'] = scipy.signal.peak_widths(y, analysisDict['peaks'],
															rel_height=halfWidthFraction)
		newWidthSec = []
		# [0] width, [1] heights, [2] start, [3] stop
		for idx, widths in enumerate(analysisDict['halfWidth']):
			if idx==1:
				newWidthSec.append(widths)
			else:
				newWidthSec.append(self._pnt2Sec(widths))
		analysisDict['halfWidth'] = tuple(newWidthSec)

		# full height gizes crazy answers
		analysisDict['fullWidth'] = scipy.signal.peak_widths(y, analysisDict['peaks'],
															rel_height=fullWidthFraction)
		newWidthSec = []
		# [0] is width, [1] heights, [2] is start, [3] is stop
		for idx, widths in enumerate(analysisDict['fullWidth']):
			if idx==1:
				newWidthSec.append(widths)
			else:
				newWidthSec.append(self._pnt2Sec(widths))
		analysisDict['fullWidth'] = tuple(newWidthSec)

		# create a boolean list for accept/reject
		numPeaks = len(analysisDict['peaks'])
		analysisDict['accept'] = [True] * numPeaks

		#
		# order matter
		#analysisDict['results_summary'] = self.getStats()
		#analysisDict['results_full'] = self.asDataFrame()

		# assign to list
		self._analysisList[self._analysisIdx] = analysisDict

		self._analysisList[self._analysisIdx]['results_summary'] = self.getStats()
		self._analysisList[self._analysisIdx]['results_full'] = self.asDataFrame()

		stopSec = time.time()
		if verbose:
			print(f'  detect() found {numPeaks} peaks in {round(stopSec-startSec,2)} seconds.')

	def testPlot(self):
		numSubplot = 1
		fig, axs = plt.subplots(numSubplot, 1, figsize=(12, 6))
		axs = [axs]

		# raw data
		sweepX = self.sweepX  # seconds
		sweepY = self.sweepY
		sweepY_filtered = self.sweepY_filtered

		# analysis
		analysis = self.getAnalysis()
		peaks = analysis['peaks']  # (int), not interpolated
		properties = analysis['properties']
		halfWidth = analysis['halfWidth']
		fullWidth = analysis['fullWidth']

		# plot raw (filtered) data
		#axs[0].plot(self.sweepX, sweepY, 'k', linewidth=0.5)
		axs[0].plot(sweepX, sweepY_filtered, 'k', linewidth=0.5)

		peaksSecond = self._pnt2Sec(peaks)
		axs[0].scatter(peaksSecond, self.sweepY_filtered[peaks], marker='.')

		# seems to default to 1/2 width ???
		#left_bases = analysis['properties']['left_ips']  # left_bases
		#left_bases_int = left_bases.round().astype(int)
		#left_bases_sec = self._pnt2Sec(left_bases)
		#axs[0].scatter(left_bases_sec, self.sweepY_filtered[left_bases_int], marker='.')

		# widths
		# [0] is width, [1] heights, [2] is start, [3] is stop
		axs[0].hlines(*halfWidth[1:], color="g")
		axs[0].hlines(*fullWidth[1:], color="b")

		# height
		#ymin = sweepY_filtered[peaksInt] - properties["prominences"]
		ymin = fullWidth[1]
		ymax = sweepY_filtered[peaks]
		axs[0].vlines(x=peaksSecond, ymin=ymin, ymax=ymax, color = "C1")

		#axs[0].set_xlim(11,12.2)
		#axs[0].set_ylim(-2,6)

	def plotClips(self):
		"""
		plot aligned clips

		todo: align to left ip of full width

		fullHeight is # [0] is width, [1] heights, [2] is start, [3] is stop

		"""
		numSubplot = 1
		fig, axs = plt.subplots(numSubplot, 1, figsize=(8, 6))
		axs = [axs]

		preSec = 0.05
		postSec = 0.2

		prePnts = self._sec2Pnt(preSec)
		postPnts = self._sec2Pnt(postSec)

		numPnts = postPnts + prePnts

		start = - preSec
		stop = postSec
		num = numPnts
		xOneClip = np.linspace(start, stop, num=num)
		#print('xOneClip:', xOneClip)

		# todo: normalize to mean
		analysis = self.getAnalysis()
		peaks = analysis['peaks']
		#halfWidth = analysis['halfWidth']
		fullWidth = analysis['fullWidth']
		acceptList = analysis['accept']

		for idx, peakPnt in enumerate(peaks):

			if not acceptList[idx]:
				#print('  rejecting', idx)
				continue

			# full
			leftSec = fullWidth[2][idx]
			leftPnt = self._sec2Pnt(leftSec)
			#height = self._fullHeight[1][idx]

			# half
			#leftSec = self._halfWidth[2][idx]
			#leftPnt = self._sec2Pnt(leftSec)
			#height = self._halfWidth[1][idx]

			startPnt = leftPnt - prePnts
			stopPnt = leftPnt + postPnts
			yOneClip = self.sweepY[startPnt:stopPnt]

			yLeftVal = self.sweepY[leftPnt]
			yOneClip -= yLeftVal


			axs[0].plot(xOneClip, yOneClip, '-')

		#axs[0].plot(clipList, '-')

	def refreshPlot(self):
		#self.replotScatter()  # needed for accept/reject
		#self.replotScatter_selection()

		peakNumber = self.currentPeakIdx

		analysis = self.getAnalysis()
		peaks = analysis['peaks']
		halfWidth = analysis['halfWidth']
		fullWidth = analysis['fullWidth']
		acceptList = analysis['accept']

		xPeak = peaks[peakNumber]  # point of the peak
		xPeakSec = self._pnt2Sec(xPeak)
		yPeak = self.sweepY[xPeak]

		#
		# all data
		self.axs[0].clear()
		self.axs[0].plot(self.sweepX, self.sweepY, '-')

		# plot peaks
		xPlotPeakSec0 = self._pnt2Sec(peaks)
		yPlotPeakSec0 = self.sweepY[peaks]
		self.axs[0].scatter(xPlotPeakSec0, yPlotPeakSec0, c='k', marker='.', zorder=999)

		# intermeidate zoom
		currentPeakIdx = self.currentPeakIdx

		windowPnts2 = 100

		xMin = currentPeakIdx - windowPnts2  # points
		xMax = currentPeakIdx + windowPnts2
		xClip2 = self.sweepX[xMin:xMax]
		yClip2 = self.sweepY[xMin:xMax]

		# find visible peaks between [xMin, xMax]
		xVisiblePeak_Pnt = [idx for idx,x in enumerate(peaks) if (x>xMin and x<xMax)]  # for scatter colors
		xVisiblePeak = [x for x in peaks if (x>xMin and x<xMax)]
		xVisiblePeakSec = self._pnt2Sec(xVisiblePeak)
		yVisiblePeak = self.sweepY[xVisiblePeak]

		mySelectColor = 'k' if acceptList[peakNumber] else 'r'

		#
		# zoom 1
		self.axs[1].clear()
		xMinSec = xPeakSec - (self.zoomSec1 / 2)
		xMaxSec = xPeakSec + (self.zoomSec1 / 2)
		xMaskPnts = (self.sweepX >= xMinSec) & (self.sweepX <= xMaxSec)
		yRange = max(self.sweepY[xMaskPnts]) - min(self.sweepY[xMaskPnts]) # used for rectangle
		xClip1 = self.sweepX[xMaskPnts]
		yClip1 = self.sweepY[xMaskPnts]
		self.axs[1].plot(self.sweepX[xMaskPnts], self.sweepY[xMaskPnts], '-')
		self.axs[1].scatter(xPeakSec, yPeak, c=mySelectColor, marker='x')

		# find and plot visible peaks
		xMinPnt = self._sec2Pnt(xMinSec)
		xMaxPnt = self._sec2Pnt(xMaxSec)
		xMaskPnt = (peaks >= xMinPnt) & (peaks <= xMaxPnt)
		xPlotPeakPnts = peaks[xMaskPnt]
		xPlotPeakSec = self._pnt2Sec(xPlotPeakPnts)
		yPlotPeakSec = self.sweepY[xPlotPeakPnts]
		#print(type(xMaskPnt), xMaskPnt)
		xMaskPnt2 = xMaskPnt[xMaskPnt == True]
		myColors = ['k' if acceptList[int(x)] else 'r' for x in xMaskPnt2]
		self.axs[1].scatter(xPlotPeakSec, yPlotPeakSec, c=myColors, zorder=999)

		# h line with threshold
		height = analysis['detection']['height']
		self.axs[1].hlines(height, xMinSec, xMaxSec, color='r', linestyles='--')


		#
		# zoom 2 tight zoom
		self.axs[2].clear()
		xMinSec2 = xPeakSec - (self.zoomSec2 / 2)
		xMaxSec2 = xPeakSec + (self.zoomSec2 / 2)

		xMaskPnts2 = (self.sweepX >= xMinSec2) & (self.sweepX <= xMaxSec2)
		xMinPnt2 = self._sec2Pnt(xMinSec2)
		xMaxPnt2 = self._sec2Pnt(xMaxSec2)
		xMaskPnt2 = (peaks >= xMinPnt2) & (peaks <= xMaxPnt2) # boolean
		xMaskPeakPnts = peaks[xMaskPnt2]
		xClip2 = self.sweepX[xMaskPnts2] # just points within view
		yClip2 = self.sweepY[xMaskPnts2]

		# get indices that are visible in _peaks
		peakMask2 = (peaks >= xMinPnt2) & (peaks <= xMaxPnt2) # boolean

		self.axs[2].plot(self.sweepX[xMaskPnts2], self.sweepY[xMaskPnts2], '-')
		self.axs[2].scatter(xPeakSec, yPeak, c=mySelectColor, marker='x')

		# reduce halfWidth to our x-zoom, width is a tuples of lists
		# [0] is width, [1] heights, [2] is start, [3] is stop
		#widthMask = (self._halfWidth[2]>=xMinSec2) & (self._halfWidth[3]<=xMaxSec2)
		plotWidth = (halfWidth[0][peakMask2],
						halfWidth[1][peakMask2],
						halfWidth[2][peakMask2],
						halfWidth[3][peakMask2])
		self.axs[2].hlines(*plotWidth[1:], color="C2")

		# full width (e.g. the foot)
		#widthMask = (self._fullHeight[2]>=xMinSec2) & (self._fullHeight[3]<=xMaxSec2)
		plotFullWidth = (fullWidth[0][peakMask2],
						fullWidth[1][peakMask2],
						fullWidth[2][peakMask2],
						fullWidth[3][peakMask2])
		self.axs[2].hlines(*plotFullWidth[1:], color="C3")

    	# vertical lines for prominence
		#myProminence = self._properties["prominences"][xMaskPnt2]
		myProminence = plotFullWidth[1]
		#self.axs[2].vlines(x=self.sweepX[xMaskPeakPnts],
		#					ymin=self.sweepY[xMaskPeakPnts] - myProminence,
		#					ymax=self.sweepY[xMaskPeakPnts],
		#					color="C1")
		self.axs[2].vlines(x=self.sweepX[xMaskPeakPnts],
							ymin=myProminence,
							ymax=self.sweepY[xMaskPeakPnts],
							color="C1")

		# this wil break user zooming ???
		self.axs[2].set_xlim(xMinSec2, xMaxSec2)

		# gray rectangle (on middle plot)
		rectWidth = max(xClip2) - min(xClip2)  # to match tighter view
		rectHeight = max(yClip1) - min(yClip1)
		xRectPos = min(xClip2)  # to match tighter view (3)
		yRectPos = min(yClip1)
		self.axs[1].add_patch(Rectangle((xRectPos, yRectPos), rectWidth, rectHeight, facecolor="silver"))

		# gray rectangle (on top plot)
		rectWidth = max(xClip1) - min(xClip1)  # to match middle view
		rectHeight = max(self.sweepY) - min(self.sweepY)
		xRectPos = min(xClip1)  # to match tighter view (3)
		yRectPos = min(self.sweepY)
		self.axs[0].add_patch(Rectangle((xRectPos, yRectPos), rectWidth, rectHeight, facecolor="silver"))

		# refresh
		self.fig.canvas.draw()

	def replotScatter_selection(self):
		peakNumber = self.currentPeakIdx

		prominences = self._properties["prominences"] # list of pnt

		# todo: make member variable so we synch (replotScatter_selection, replotScatter)
		xData = self._halfWidth[0] #left_ips
		yData = prominences

		xSelection = xData[peakNumber]
		ySelection = yData[peakNumber]
		self.axScatter.clear()
		self.axScatter.scatter(xSelection, ySelection, c='y', marker='x')

		self.scatterFig.canvas.draw()

	def replotScatter(self):
		peakNumber = self.currentPeakIdx

		analysis = self.getAnalysis()

		peaks = analysis['peaks']
		prominences = analysis['properties']["prominences"] # list of pnt
		acceptList = analysis['accept']
		#left_ips = self._properties["left_ips"] # list of pnt

		xData = analysis['halfWidth'][0] #left_ips
		yData = prominences
		#data = np.stack([xData, yData], axis=1)
		#self.scatterLines.set_offsets(data)  # (N, 2)
		# working
		#myColors = ['k' if x else 'r' for x in self.myAcceptList]

		#
		# strip down data based on myAcceptList
		acceptList = analysis['accept']
		npAcceptList = np.array(acceptList)
		acceptMask = (npAcceptList==True)
		xData = xData[acceptMask]
		yData = yData[acceptMask]
		#myColors = myColors[acceptMask]
		# [f(x) for x in sequence if condition]
		myColors = ['k' for x in acceptList if x==True]

		self.axScatter.scatter(xData, yData, c=myColors, marker='.', picker=5)

		#badColor = 'r'
		#self.axScatter.scatter(5, 5, c=badColor, marker='o', picker=5)

		self.axScatter.set_xlabel('Width (sec)')
		self.axScatter.set_ylabel('Prominence (y-units)')

		# select current point (yellow)

		# select visible peaks in middle plot (cyan)

		# x histogram
		self.axHistX.clear()
		xBins = 'auto'
		nHistX, binsHistX, patchesHistX = self.axHistX.hist(xData, bins=xBins,
											facecolor='silver', edgecolor="gray")
		self.axHistX.tick_params(axis="x", labelbottom=False) # no labels

		# y histogram
		self.axHistY.clear()
		yBins = 'auto'
		nHistY, binsHistY, patchesHistY = self.axHistY.hist(yData, bins=yBins,
											orientation='horizontal', facecolor='silver', edgecolor="gray")
		self.axHistY.tick_params(axis="y", labelleft=False) # no labels

		# refresh
		self.scatterFig.canvas.draw()

	def on_scatter_pick(self, event):
		"""
		e (matplotlib.backend_bases.PickEvent)
		"""
		# we need to use 'with' so error and print() show up in the jupyter/browser
		with self.myScatterOut:
			IPython.display.clear_output()
			#thisline = event.artist
			ind = event.ind  # list of points withing specified tolerance
			ind = ind[0]
			offsets = event.artist.get_offsets()
			print('on_scatter_pick() ind:', ind, 'offsets', offsets[ind])

	def scatterWidget(self):
		"""
		Plot peak vs width with marginal histograms
		"""
		self.scatterFig = plt.figure(figsize=(7, 6))

		self.gs = self.scatterFig.add_gridspec(2, 2,  width_ratios=(7, 2), height_ratios=(2, 7),
											left=0.1, right=0.9, bottom=0.1, top=0.9,
											wspace=0.05, hspace=0.05)

		self.axScatter = self.scatterFig.add_subplot(self.gs[1, 0])

		self.scatterFig.canvas.mpl_connect('pick_event', self.on_scatter_pick)

		# x/y hist
		self.axHistX = self.scatterFig.add_subplot(self.gs[0, 0], sharex=self.axScatter)
		self.axHistY = self.scatterFig.add_subplot(self.gs[1, 1], sharey=self.axScatter)
		#
		self.axHistX.spines['right'].set_visible(False)
		self.axHistX.spines['top'].set_visible(False)
		self.axHistY.spines['right'].set_visible(False)
		self.axHistY.spines['top'].set_visible(False)

		# empty scatter
		#self.scatterLines = self.axScatter.scatter([], [], picker=5)

		self.myScatterOut = widgets.Output()
		display(self.myScatterOut)

	def asDataFrame(self):

		analysis = self.getAnalysis()
		filePath = analysis['filePath']
		peaks = analysis['peaks']  # (int), not interpolated
		properties = analysis['properties']
		halfWidth = analysis['halfWidth']
		fullWidth = analysis['fullWidth']

		sweepY_filtered = analysis['sweepY_filtered']

		peaksSec = self._pnt2Sec(peaks)

		df = pd.DataFrame()

		file = os.path.split(filePath)[1]
		df['file'] = [file] * len(peaks)

		df['peakNum'] = [idx for idx,peak in enumerate(peaks)]
		df['accept'] = analysis['accept']
		df['peak_pnt'] = peaks
		df['peak_sec'] = peaksSec

		instFreq_hz = 1 / np.diff(peaksSec)
		instFreq_hz = np.insert(instFreq_hz, 0, np.nan)

		ipi_ms = np.diff(peaksSec) * 1000
		ipi_ms = np.insert(ipi_ms, 0, np.nan)

		df['ipi_ms'] = ipi_ms
		df['instFreq_hz'] = instFreq_hz

		height = np.subtract(sweepY_filtered[peaks], fullWidth[1])
		df['height'] = height

		df['half_width_ms'] = halfWidth[0] * 1000

		# [0] is width, [1] heights, [2] is start, [3] is stop
		df['halfWidth_width_sec'] = halfWidth[0]
		df['halfWidth_height_sec'] = halfWidth[1]
		df['halfWidth_left_sec'] = halfWidth[2]
		df['halfWidth_right_sec'] = halfWidth[3]
		# [0] is width, [1] heights, [2] is start, [3] is stop
		df['fullWidth_width_sec'] = fullWidth[0]
		df['fullWidth_height_sec'] = fullWidth[1]
		df['fullWidth_left_sec'] = fullWidth[2]
		df['fullWidth_right_sec'] = fullWidth[3]

		df['filePath'] = filePath

		return df

	def getStats(self):
		theseStats = ["count", "min", "max", "median", "mean"]
		df = self.asDataFrame()
		dfAgg = df.agg(
			{
				'ipi_ms': theseStats,
				'instFreq_hz': theseStats,
				'height': theseStats,
				'half_width_ms': theseStats,
			}
		)
		return dfAgg

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

		print('  todo: paramFile:', paramFile)
		#print('  todo: analysisFile:', analysisFile)

		# saving is complicated because we have (peaks, halfWidth, fullWidth)

		analysis = self.getAnalysis()

		summaryFile = os.path.splitext(filename)[0] + '_summary.csv'
		summaryPath = os.path.join(folderPath, summaryFile)
		print('saving summary:', summaryPath)
		results_summary = analysis['results_summary']
		results_summary.to_csv(summaryPath)

		resultsFile = os.path.splitext(filename)[0] + '_full.csv'
		resultsPath = os.path.join(folderPath, resultsFile)
		print('saving full:', resultsPath)
		results_full = analysis['results_full']
		results_full.to_csv(resultsPath)


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
		else:
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

	#df = ca.asDataFrame()
	#print(df.head())

	#print(ca.getStats())

	#ca.testPlot()
	#plt.show()

	#print(ca)
	#ca.myShow()

	#print(ca.getAnalysis())

	# test save
	ca.save()
