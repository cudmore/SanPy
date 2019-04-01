# Author: Robert Cudmore
# Date: 20190312

import numpy as np
import scipy.signal

from tkinter import ttk

# required to import bAnalysis which does 'import matplotlib.pyplot as plt'
# without this, tkinter crashes
import matplotlib
matplotlib.use("TkAgg")

from matplotlib.widgets import SpanSelector

#####################################################################################
class bPlotFrame(ttk.Frame):

	def __init__(self, parent, controller, showToolbar=False, analysisList=[], figHeight=2, allowSpan=True):
		"""
		parent: ttk widget, usually a frame
		controller: AnalysisApp
		analysisList:
		"""

		ttk.Frame.__init__(self, parent)

		self.controller = controller

		myPadding = 10

		self.fig = matplotlib.figure.Figure(figsize=(8,figHeight), dpi=100)
		#self.fig = matplotlib.figure.Figure()
		self.axes = self.fig.add_subplot(111)

		self.line, = self.axes.plot([],[], 'k') # REMEMBER ',' ON LHS
		self.spikeTimesLine, = self.axes.plot([],[], 'or') # REMEMBER ',' ON LHS
		self.thresholdCrossingsLine, = self.axes.plot([],[], 'og') # REMEMBER ',' ON LHS

		#self.clipsLine, = self.axes.plot([],[], 'or') # REMEMBER ',' ON LHS
		self.clipLines = None
		self.clipLines_selection = None
		self.clipLines_mean = None
		self.meanClip = []
		
		self.plotMeta_selection = None

		self.canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.fig, parent)
		#self.canvas.get_tk_widget().pack(side="bottom", fill="both", expand=True)

		#here
		self.canvas.get_tk_widget().pack(side="bottom", fill="both", expand=1)
		#self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

		self.canvas.draw()

		#cid1 = self.canvas.mpl_connect('button_press_event', self.onclick)
		cid2 = self.canvas.mpl_connect('pick_event', self.onpick)

		if showToolbar:
			toolbar = matplotlib.backends.backend_tkagg.NavigationToolbar2Tk(self.canvas, parent)
			toolbar.update()
			#toolbar = matplotlib.backends.backend_tkagg.NavigationToolbar2Tk(canvas, controller.root)
			#toolbar.update()
			#self.canvas._tkcanvas.pack(side="top", fill="both", expand=True)
			self.canvas.get_tk_widget().pack(side="bottom", fill="both")

		#
		# horizontal (time) selection
		if allowSpan:
			self.span = SpanSelector(self.axes, self.onselect, 'horizontal', useblit=True,
						rectprops=dict(alpha=0.5, facecolor='yellow'))

		#
		# a list of analysis line(s)
		markerColor = 'k'
		marker = 'o'
		self.analysisLines = {}
		for analysis in analysisList:
			#print("bPlotFrame.__init__ color analysis:", analysis)
			markerColor = 'k'
			marker = 'o'
			if analysis == 'peak':
				markerColor = 'r'
			if analysis == 'preMin':
				markerColor = 'r'
			if analysis == 'postMin':
				markerColor = 'g'
			if analysis == 'preLinearFit':
				markerColor = 'b'
			if analysis == 'preSpike_dvdt_max':
				markerColor = 'y'
			if analysis == 'postSpike_dvdt_min':
				markerColor = 'y'
				marker = 'x'
			if analysis == 'halfWidth':
				markerColor = 'b'
				marker = 'o'
				# special case
				analysisLine, = self.axes.plot([], [], color=markerColor, linestyle='-', linewidth=2)
				self.analysisLines['halfWidthLines'] = analysisLine

			analysisLine, = self.axes.plot([],[], marker + markerColor) # REMEMBER ',' ON LHS
			self.analysisLines[analysis] = analysisLine

		self.metaLines, = self.axes.plot([],[], 'ok', picker=5) # REMEMBER ',' ON LHS
		self.metaLines3, = self.axes.plot([],[], 'ok', picker=5) # REMEMBER ',' ON LHS

		self.metax = []
		self.metay = []

		self.singleSpikeSelection, = self.axes.plot([],[], 'oy') # REMEMBER ',' ON LHS

	def onclick(self, event):
		print('bPlotFrame.onclick()')
		'''
		print('bPlotFrame.onclick() %s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
			('double' if event.dblclick else 'single', event.button,
			event.x, event.y, event.xdata, event.ydata))
		'''

	def onpick(self, event):
		print('bPlotFrame.onpick() event:', event)
		#print('   event.ind:', event.ind)
		thisline = event.artist
		xdata = thisline.get_xdata()
		#ydata = thisline.get_ydata()
		ind = event.ind
		print('   event.ind:', ind)
		#print('xdata:', xdata)

		ind = int(ind[0])

		print('   xdata[ind]:', xdata[ind])

		# select spike 'ind' in raw data
		self.controller.selectSpike(ind)

	def onpick3(self, event):
		print('bPlotFrame.onpick3() event:', event)
		#print('   event.ind:', event.ind)
		thisline = event.artist
		xdata = thisline.get_xdata()
		#ydata = thisline.get_ydata()
		ind = event.ind
		print('   event.ind:', ind)

		ind = int(ind[0])
		ind += 2
		
		print('   xdata[ind]:', xdata[ind])

		# select spike 'ind' in raw data
		self.controller.selectSpike(ind)

	def plotStat(self, name, onoff):
		#print("=== bPlotFrame.plotStat() name:", name, "onoff:", onoff)

		pnt = []
		val = []
		if name == 'threshold':
			pnt = [x['thresholdPnt'] for x in self.controller.ba.spikeDict]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['thresholdVal'] for x in self.controller.ba.spikeDict]
		if name == 'peak':
			pnt = [x['peakPnt'] for x in self.controller.ba.spikeDict]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['peakVal'] for x in self.controller.ba.spikeDict]
		if name == 'preMin':
			pnt = [x['preMinPnt'] for x in self.controller.ba.spikeDict if 'preMinPnt' in x]
			# remove none because first/last spike has none for preMin
			pnt = [x for x in pnt if x is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]

			val = [x['preMinVal'] for x in self.controller.ba.spikeDict if 'preMinVal' in x]
			# remove none because first/last spike has none for preMin
			val = [x for x in val if x is not None]
		if name == 'postMin':
			pnt = [x['postMinPnt'] for x in self.controller.ba.spikeDict if 'postMinPnt' in x]
			# remove none because first/last spike has none for preMin
			pnt = [x for x in pnt if x is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]

			val = [x['postMinVal'] for x in self.controller.ba.spikeDict if 'postMinVal' in x]
			# remove none because first/last spike has none for preMin
			val = [x for x in val if x is not None]

		if name == 'preLinearFit':
			# 0
			pnt0 = [x['preLinearFitPnt0'] for x in self.controller.ba.spikeDict if 'preLinearFitPnt0' in x]
			# remove none because first/last spike has none for preMin
			pnt0 = [x for x in pnt0 if x is not None]
			pnt0 = [self.controller.ba.abf.sweepX[pnt0]]
			# 1
			pnt1 = [x['preLinearFitPnt1'] for x in self.controller.ba.spikeDict if 'preLinearFitPnt1' in x]
			# remove none because first/last spike has none for preMin
			pnt1 = [x for x in pnt1 if x is not None]
			pnt1 = [self.controller.ba.abf.sweepX[pnt1]]

			pnt = pnt0 + pnt1 # concatenate

			# 0
			val0 = [x['preLinearFitVal0'] for x in self.controller.ba.spikeDict if 'preLinearFitVal0' in x]
			# remove none because first/last spike has none for preMin
			val0 = [x for x in val0 if x is not None]
			# 1
			val1 = [x['preLinearFitVal1'] for x in self.controller.ba.spikeDict if 'preLinearFitVal1' in x]
			# remove none because first/last spike has none for preMin
			val1 = [x for x in val1 if x is not None]

			val = val0 + val1 # concatenate

		if name == 'preSpike_dvdt_max':
			pnt = [x['preSpike_dvdt_max_pnt'] for x in self.controller.ba.spikeDict if 'preSpike_dvdt_max_pnt' in x]
			# remove none because first/last spike has none for preMin
			pnt = [x for x in pnt if x is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]

			val = [x['preSpike_dvdt_max_val'] for x in self.controller.ba.spikeDict if 'preSpike_dvdt_max_val' in x]
			# remove none because first/last spike has none for preMin
			val = [x for x in val if x is not None]

		if name == 'postSpike_dvdt_min':
			pnt = [x['postSpike_dvdt_min_pnt'] for x in self.controller.ba.spikeDict if 'postSpike_dvdt_min_pnt' in x]
			# remove none because first/last spike has none for preMin
			pnt = [x for x in pnt if x is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]

			val = [x['postSpike_dvdt_min_val'] for x in self.controller.ba.spikeDict if 'postSpike_dvdt_min_val' in x]
			# remove none because first/last spike has none for preMin
			val = [x for x in val if x is not None]

		# this is a little innefficient
		if name == 'halfWidth':
			pnt = []
			val = []
			for spikeDict in self.controller.ba.spikeDict:
				if 'widths' in spikeDict:
					for j,widthDict in enumerate(spikeDict['widths']):
						# todo: store x value as time (Sec) in original analysis
						pnt.append(self.controller.ba.abf.sweepX[widthDict['risingPnt']])
						pnt.append(self.controller.ba.abf.sweepX[widthDict['fallingPnt']])
						pnt.append(float('nan'))

						val.append(widthDict['risingVal'])
						val.append(widthDict['fallingVal'])
						val.append(float('nan'))
			# explicitly plot lines
			#ax.plot([risingPntX, fallingPntX], [risingPntY, fallingPntY], color='b', linestyle='-', linewidth=2)
			if onoff:
				self.analysisLines['halfWidthLines'].set_ydata(val)
				self.analysisLines['halfWidthLines'].set_xdata(pnt)
			else:
				self.analysisLines['halfWidthLines'].set_ydata([])
				self.analysisLines['halfWidthLines'].set_xdata([])

		#
		# plot
		if onoff:
			self.analysisLines[name].set_ydata(val)
			self.analysisLines[name].set_xdata(pnt)
		else:
			self.analysisLines[name].set_ydata([])
			self.analysisLines[name].set_xdata([])

		self.canvas.draw()

	def setXAxis(self, xMin, xMax):
		print("bPlotFrame.setXAxis() xMin:", xMin, "xMax:", xMax)
		self.axes.set_xlim(xMin, xMax)
		self.canvas.draw()

	def setFullAxis(self):
		print('bPlotFrame.setFullAxis()')

		xMin = min(self.line.get_xdata())
		xMax = max(self.line.get_xdata())
		self.axes.set_xlim(xMin, xMax)

		'''
		yMin = min(self.line.get_ydata())
		yMax = max(self.line.get_ydata())
		self.axes.set_ylim(yMin, yMax)
		'''

		self.canvas.draw()

	def onselect(self, xMin, xMax):
		"""
		respond to horizontal selection from self.span
		"""
		if xMin == xMax:
			return
		if abs(xMax-xMin) < 0.001:
			return
		print('bPlotFrame.onselect() xMin:', xMin, 'xMax:', xMax)
		#self.axes.set_xlim(xMin, xMax)
		self.controller.setXAxis(xMin, xMax)

	def plotRaw(self, ba, plotEveryPoint=10, doInit=False):
		"""
		ba: abf file
		plotEveryPoint: plot every plotEveryPoint, 1 will plot all, 10 will plot every 10th
		"""

		start = 0
		stop = len(ba.abf.sweepX) - 1
		subSetOfPnts = range(start, stop, plotEveryPoint)

		self.line.set_ydata(ba.abf.sweepY[subSetOfPnts])
		self.line.set_xdata(ba.abf.sweepX[subSetOfPnts])

		if doInit:
			xMin = min(ba.abf.sweepX)
			xMax = max(ba.abf.sweepX)
			self.axes.set_xlim(xMin, xMax)

			yMin = min(ba.abf.sweepY)
			yMax = max(ba.abf.sweepY)
			# increase y-axis by 5 percent
			fivePercent = abs(yMax-yMin) * 0.1
			yMin -= fivePercent
			yMax += fivePercent
			self.axes.set_ylim(yMin, yMax)

			self.axes.set_ylabel('Vm (mV)')
			self.axes.set_xlabel('Time (sec)')

		self.canvas.draw()

	def selectSpike(self, ba, spikeNumber):
		""" Select a single spike in raw trace """
		spikeVm = ba.abf.sweepY[ba.spikeTimes[spikeNumber]]
		spikeSeconds = ba.abf.sweepX[ba.spikeTimes[spikeNumber]]
		self.singleSpikeSelection.set_ydata(spikeVm)
		self.singleSpikeSelection.set_xdata(spikeSeconds)

		self.canvas.draw()

	def plotDeriv(self, ba, plotEveryPoint=10, doInit=False):
		#ba.plotDeriv(fig=self.fig)

		start = 0
		stop = len(ba.abf.sweepX) - 1
		subSetOfPnts = range(start, stop, plotEveryPoint)

		self.line.set_ydata(ba.filteredDeriv[subSetOfPnts])
		self.line.set_xdata(ba.abf.sweepX[subSetOfPnts])

		if doInit:
			xMin = min(ba.abf.sweepX)
			xMax = max(ba.abf.sweepX)
			self.axes.set_xlim(xMin, xMax)

			yMin = min(ba.filteredDeriv)
			yMax = max(ba.filteredDeriv)
			self.axes.set_ylim(yMin, yMax)

			self.axes.set_ylabel('dV/dt (mv/ms)')
			self.axes.set_xlabel('Time (sec)')

		# final spike time
		self.spikeTimesLine.set_ydata(ba.filteredDeriv[ba.spikeTimes])
		self.spikeTimesLine.set_xdata(ba.abf.sweepX[ba.spikeTimes])

		# final spike time
		#print('ba.thresholdTimes[0]:', ba.thresholdTimes[0])
		self.thresholdCrossingsLine.set_ydata(ba.filteredDeriv[ba.thresholdTimes])
		self.thresholdCrossingsLine.set_xdata(ba.abf.sweepX[ba.thresholdTimes])

		self.canvas.draw()

	def plotClips(self, ba, plotEveryPoint=10):
		print('bPlotFrame.plotClips() len(ba.spikeClips)', len(ba.spikeClips))
		# ax.plot(self.spikeClips_x, self.spikeClips[i], 'k')

		# clear existing
		if self.clipLines is not None:
			for line in self.clipLines:
				line.remove()

		self.clipLines = []

		"""
		for i in range(len(ba.spikeClips)):
			try:
				#ax.plot(self.spikeClips_x, self.spikeClips[i], 'k')
				line, = self.axes.plot(ba.spikeClips_x, ba.spikeClips[i], 'k')
				self.clipLines.append(line)
				'''
				self.clipsLine.set_ydata(ba.spikeClips[i])
				self.clipsLine.set_xdata(ba.spikeClips_x)
				'''

			except (ValueError) as e:
				print('exception in bPlotFrame.plotClips() while plotting clips', i)
		"""

		self.canvas.draw()

	def plotClips_updateSelection(self, ba, xMin, xMax):
		"""
		plot the spike clips within min/max
		"""

		print('bPlotFrame.clipsPlot_updateSelection() xMin:', xMin, 'xMax:', xMax)

		self.controller.setStatus('Updating clips')
		
		# clear existing
		if self.clipLines_selection is not None:
			for line in self.clipLines_selection:
				line.remove()
		self.clipLines_selection = []

		if self.clipLines_mean is not None:
			for line in self.clipLines_mean:
				line.remove()
		self.clipLines_mean = []

		if xMin is None and xMax is None:
			xMin = 0
			xMax = len(self.controller.ba.abf.sweepX) / ba.dataPointsPerMs / 1000 # pnts to seconds
			
		tmpClips = [] # for mean clip
		for i, spikeTime in enumerate(ba.spikeTimes):
			spikeSeconds = spikeTime / ba.dataPointsPerMs / 1000 # pnts to seconds
			if spikeSeconds >= xMin and spikeSeconds <= xMax:
				# spike clips at start/end are sometimes truncated
				if len(ba.spikeClips_x) == len(ba.spikeClips[i]):
					line, = self.axes.plot(ba.spikeClips_x, ba.spikeClips[i], 'k')
					self.clipLines_selection.append(line)
					tmpClips.append(ba.spikeClips[i]) # for mean clip

		if len(tmpClips):
			self.meanClip = np.mean(tmpClips, axis=0)
			line, = self.axes.plot(ba.spikeClips_x, self.meanClip, 'r')
			self.clipLines_mean.append(line)
		else:
			print('error: bPlotFrame.plotClips_updateSelection() did not update the mean clip')
			
		self.canvas.draw()

		self.controller.setStatus()

		return len(self.clipLines_selection)
		
	def plotMeta3(self, xStat, yStat):

		print('bPlotFrame.plotMeta3() xStat:', xStat, 'yStat:', yStat)

		cid2 = self.canvas.mpl_connect('pick_event', self.onpick3)

		# fill in based on statName
		xVal = [] # x
		yVal = [] # y

		xLabel = ''
		yLabel = ''

		# clear existing
		#self.metaLines3.remove()

		# x
		for currentAxis in ['x', 'y']:
			#
			if currentAxis == 'x':
				thisStat = xStat
			elif currentAxis == 'y':
				thisStat = yStat
		
			#
			thisLabel = thisStat
			
			if thisStat == 'Time (sec)':
				thresholdPnt = [x['thresholdPnt'] for x in self.controller.ba.spikeDict]
				del thresholdPnt[0]
				del thresholdPnt[-1] # last element
				thisVal = self.controller.ba.abf.sweepX[thresholdPnt]

			if thisStat == 'threshold':
				thisVal = [x['thresholdVal'] for x in self.controller.ba.spikeDict]
				del thisVal[0]
				del thisVal[-1] # last element
			if thisStat == 'peak':
				thisVal = [x['peakVal'] for x in self.controller.ba.spikeDict if x['peakVal'] is not None]
				del thisVal[0]
				del thisVal[-1] #last element
			if thisStat == 'preMin':
				thisVal = [x['preMinVal'] for x in self.controller.ba.spikeDict if x['preMinVal'] is not None]
			if thisStat == 'postMin':
				thisVal = [x['postMinVal'] for x in self.controller.ba.spikeDict if x['postMinVal'] is not None]
				thisLabel = thisStat
			if thisStat == 'preLinearFit':
				print('error: plotMeta3()', thisStat, 'not implemented')
				return 0
			if thisStat == 'preSpike_dvdt_max':
				thisVal = [x['preSpike_dvdt_max_val'] for x in self.controller.ba.spikeDict if x['preSpike_dvdt_max_val'] is not None]
			if thisStat == 'postSpike_dvdt_min':
				thisVal = [x['postSpike_dvdt_min_val'] for x in self.controller.ba.spikeDict if x['postSpike_dvdt_min_val'] is not None]
			if thisStat == 'isi (ms)':
				spikeTimes_sec = [x/self.controller.ba.abf.dataPointsPerMs for x in self.controller.ba.spikeTimes]
				del spikeTimes_sec[0]
				thisVal = np.diff(spikeTimes_sec)
				thisVal = np.concatenate(([np.NaN],thisVal))
				thisVal = np.delete(thisVal, 0)
				#thisVal = np.delete(thisVal, 0)
			if thisStat == 'Phase Plot':
				#pnt = scipy.signal.medfilt(self.controller.ba.spikeClips[oneSpikeNumber],3)
				pnt = scipy.signal.medfilt(self.controller.ba.spikeClips,3)
				val = np.diff(pnt)
				print('len(pnt):', len(pnt), pnt.shape)
				print('len(val):', len(val), val.shape)
				#val = np.concatenate(([np.NaN],val))
				#val = np.concatenate(([0],val)) # add an initial point so it is the same length as raw data in abf.sweepY
				val = np.insert(val, 0, float('nan'), axis=1)
				if currentAxis == 'x':
					thisVal = pnt
					thisLabel = 'Spike Clip Vm (mV)'
				elif currentAxis == 'y':
					thisVal = val
					thisLabel = 'dV/dt'

			#
			# Larson ... Proenza (2013) paper
			if thisStat == 'AP Peak (mV)':
				thisVal = [x['peakVal'] for x in self.controller.ba.spikeDict if x['peakVal'] is not None]
				del thisVal[0]
				del thisVal[-1] # last element

			if thisStat == 'MDP (mV)':
				thisVal = [x['postMinVal'] for x in self.controller.ba.spikeDict if x['postMinVal'] is not None]

			if thisStat == 'Take Off Potential (mV)':
				thisVal = [x['thresholdVal'] for x in self.controller.ba.spikeDict]
				del thisVal[0]
				del thisVal[-1] # last element

			if thisStat == 'Cycle Length (ms)':
				#todo: fix this, 'cycleLength_ms' is only calculated for spike # > 1
				thisVal = [x['cycleLength_ms'] for x in self.controller.ba.spikeDict if x['cycleLength_ms'] is not None] # todo: can be nan, never none !!!

			if thisStat == 'Max Upstroke (dV/dt)':
				thisVal = [x['preSpike_dvdt_max_val2'] for x in self.controller.ba.spikeDict if x['preSpike_dvdt_max_val2']]

			if thisStat == 'Max Repolarization (dV/dt)':
				thisVal = [x['postSpike_dvdt_min_val2'] for x in self.controller.ba.spikeDict if x['postSpike_dvdt_min_val2']]

			if thisStat == 'AP Duration (ms)':
				#todo: fix this, 'apDuration' is only calculated for spike # > 0
				# could use 'thresholdSec' and not index sweepX[]
				thisVal = [x['apDuration_ms'] for x in self.controller.ba.spikeDict if x['apDuration_ms']]

			if thisStat == 'Diastolic Duration (ms)':
				# in general, any time we plot threshold versus a stat (like diastolicDuration)
				# we need this extra 'is not None' because we are only calculating stats (like diastolicDuration)
				# for spike >1 and <len(spikes)
				thisVal = [x['diastolicDuration_ms'] for x in self.controller.ba.spikeDict if x['diastolicDuration_ms']]

			if thisStat == 'Early Diastolic Depolarization Rate (slope of Vm)':
				print('Not implemented')
				thisVal = [0]
				thisLabel = 'Not Implemented'

			if thisStat == 'Early Diastolic Duration (ms)':
				thisVal = [x['earlyDiastolicDuration_ms'] for x in self.controller.ba.spikeDict if x['earlyDiastolicDuration_ms']]

			if thisStat == 'Late Diastolic Duration (ms)':
				print('Not implemented')
				thisVal = [0]
				thisLabel = 'Not Implemented'

			#
			if currentAxis == 'x':
				xVal = thisVal
				xLabel = thisLabel
			elif currentAxis == 'y':
				yVal = thisVal
				yLabel = thisLabel

		#
		# replot
		print('len(xVal):', len(xVal))
		print('len(yVal):', len(yVal))
		self.metaLines3.set_xdata(xVal)
		self.metaLines3.set_ydata(yVal)

		#
		# set axis
		xMin = np.nanmin(xVal) # for phase plot, is 2d array
		xMax = np.nanmax(xVal)
		tenPercentRange = abs(xMax-xMin) * 0.1
		self.axes.set_xlim(xMin-tenPercentRange, xMax+tenPercentRange)

		yMin = np.nanmin(yVal)
		yMax = np.nanmax(yVal)
		tenPercentRange = abs(yMax-yMin) * 0.1
		self.axes.set_ylim(yMin-tenPercentRange, yMax+tenPercentRange)
		
		self.axes.set_xlabel(xLabel)
		self.axes.set_ylabel(yLabel)

		self.metax = xVal
		self.metay = yVal

		self.canvas.draw()

	def plotMeta(self, ba, statName, doInit=False):

		print('bPlotFrame.plotMeta() statName:', statName)

		# fill in based on statName
		pnt = [] # x
		val = [] # y

		yLabel = ''
		xLabel = ''

		# clear existing
		self.metaLines.remove()

		if doInit:
			self.metaLines, = self.axes.plot([],[], 'ok', picker=5) # REMEMBER ',' ON LHS

		if statName == 'threshold':
			pnt = [x['thresholdPnt'] for x in self.controller.ba.spikeDict]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['thresholdVal'] for x in self.controller.ba.spikeDict]
			xLabel = 'Seconds'
			yLabel = 'AP Threshold (mV)'
		if statName == 'peak':
			pnt = [x['peakPnt'] for x in self.controller.ba.spikeDict if x['peakPnt'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['peakVal'] for x in self.controller.ba.spikeDict if x['peakVal'] is not None]
			xLabel = 'Seconds'
			yLabel = 'AP Peak (mV)'
		if statName == 'preMin':
			pnt = [x['preMinPnt'] for x in self.controller.ba.spikeDict if x['preMinPnt'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['preMinVal'] for x in self.controller.ba.spikeDict if x['preMinVal'] is not None]
			xLabel = 'Seconds'
			yLabel = statName
		if statName == 'postMin':
			pnt = [x['postMinPnt'] for x in self.controller.ba.spikeDict if x['postMinPnt'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['postMinVal'] for x in self.controller.ba.spikeDict if x['postMinVal'] is not None]
			xLabel = 'Seconds'
			yLabel = statName
		if statName == 'preLinearFit':
			print(statName, 'not implemented')
			return 0
		if statName == 'preSpike_dvdt_max':
			pnt = [x['preSpike_dvdt_max_pnt'] for x in self.controller.ba.spikeDict if x['preSpike_dvdt_max_pnt'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['preSpike_dvdt_max_val'] for x in self.controller.ba.spikeDict if x['preSpike_dvdt_max_val'] is not None]
			xLabel = 'Seconds'
			yLabel = statName
		if statName == 'postSpike_dvdt_min':
			pnt = [x['postSpike_dvdt_min_pnt'] for x in self.controller.ba.spikeDict if x['postSpike_dvdt_min_pnt'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['postSpike_dvdt_min_val'] for x in self.controller.ba.spikeDict if x['postSpike_dvdt_min_val'] is not None]
			xLabel = 'Seconds'
			yLabel = statName
		if statName == 'isi (ms)':
			spikeTimes_sec = [x/self.controller.ba.abf.dataPointsPerMs for x in self.controller.ba.spikeTimes]
			val = np.diff(spikeTimes_sec)
			pnt = spikeTimes_sec[0:-1]
			xLabel = 'Seconds'
			yLabel = statName
		if statName == 'Phase Plot':
			#pnt = scipy.signal.medfilt(self.controller.ba.spikeClips[oneSpikeNumber],3)
			pnt = scipy.signal.medfilt(self.controller.ba.spikeClips,3)
			val = np.diff(pnt)
			val = np.concatenate(([0],val)) # add an initial point so it is the same length as raw data in abf.sweepY

		#
		# Larson ... Proenza (2013) paper
		if statName == 'AP Peak (mV)':
			pnt = [x['peakPnt'] for x in self.controller.ba.spikeDict if x['peakPnt'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['peakVal'] for x in self.controller.ba.spikeDict if x['peakVal'] is not None]
			xLabel = 'Seconds'
			yLabel = statName

		if statName == 'MDP (mV)':
			pnt = [x['postMinPnt'] for x in self.controller.ba.spikeDict if x['postMinPnt'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['postMinVal'] for x in self.controller.ba.spikeDict if x['postMinVal'] is not None]
			xLabel = 'Seconds'
			yLabel = statName

		if statName == 'Take Off Potential (mV)':
			pnt = [x['thresholdPnt'] for x in self.controller.ba.spikeDict]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['thresholdVal'] for x in self.controller.ba.spikeDict]
			xLabel = 'Seconds'
			yLabel = statName #'AP Threshold (mV)'

		if statName == 'Cycle Length (ms)':
			#todo: fix this, 'cycleLength_ms' is only calculated for spike # > 1
			pnt = [x['postMinPnt'] for x in self.controller.ba.spikeDict if x['postMinPnt'] is not None and x['cycleLength_ms'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['cycleLength_ms'] for x in self.controller.ba.spikeDict if x['cycleLength_ms'] is not None]
			xLabel = 'Seconds'
			yLabel = statName

		if statName == 'Max Upstroke (dV/dt)':
			pnt = [x['preSpike_dvdt_max_pnt'] for x in self.controller.ba.spikeDict if x['preSpike_dvdt_max_pnt']]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['preSpike_dvdt_max_val2'] for x in self.controller.ba.spikeDict if x['preSpike_dvdt_max_val2']]
			xLabel = 'Seconds'
			yLabel = statName

		if statName == 'Max Repolarization (dV/dt)':
			pnt = [x['preSpike_dvdt_max_pnt'] for x in self.controller.ba.spikeDict if x['preSpike_dvdt_max_pnt']]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['postSpike_dvdt_min_val2'] for x in self.controller.ba.spikeDict if x['postSpike_dvdt_min_val2']]
			xLabel = 'Seconds'
			yLabel = statName

		if statName == 'AP Duration (ms)':
			#todo: fix this, 'apDuration' is only calculated for spike # > 0
			# could use 'thresholdSec' and not index sweepX[]
			pnt = [x['thresholdPnt'] for x in self.controller.ba.spikeDict if x['thresholdPnt'] is not None and x['apDuration'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['apDuration'] for x in self.controller.ba.spikeDict if x['apDuration']]
			xLabel = 'Seconds'
			yLabel = statName

		if statName == 'Diastolic Duration (ms)':
			# in general, any time we plot threshold versus a stat (like diastolicDuration)
			# we need this extra 'is not None' because we are only calculating stats (like diastolicDuration)
			# for spike >1 and <len(spikes)
			pnt = [x['thresholdPnt'] for x in self.controller.ba.spikeDict if x['thresholdPnt'] is not None and x['diastolicDuration_ms'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['diastolicDuration_ms'] for x in self.controller.ba.spikeDict if x['diastolicDuration_ms']]
			xLabel = 'Seconds'
			yLabel = statName

		if statName == 'Early Diastolic Depolarization Rate (slope of Vm)':
			print('Not implemented')
			pnt = [0]
			val = [0]
			xLabel = 'Not Implemented'
			yLabel = statName

		if statName == 'Early Diastolic Duration (ms)':
			pnt = [x['preLinearFitPnt0'] for x in self.controller.ba.spikeDict if x['preLinearFitPnt0'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['earlyDiastolicDuration_ms'] for x in self.controller.ba.spikeDict if x['earlyDiastolicDuration_ms']]
			xLabel = 'Seconds'
			yLabel = statName

		if statName == 'Late Diastolic Duration (ms)':
			print('Not implemented')
			pnt = [0]
			val = [0]
			xLabel = 'Not Implemented'
			yLabel = statName

		#
		# replot
		self.metaLines.set_ydata(val)
		self.metaLines.set_xdata(pnt)

		#
		# set axis
		'''
		xMin = min(pnt)
		xMax = max(pnt)
		self.axes.set_xlim(xMin, xMax)
		'''
		xMin = min(ba.abf.sweepX)
		xMax = max(ba.abf.sweepX)
		self.axes.set_xlim(xMin, xMax)

		yMin = min(val)
		yMax = max(val)
		yRange = abs(yMax-yMin)
		tenPercentRange = yRange * 0.1
		self.axes.set_ylim(yMin-tenPercentRange, yMax+tenPercentRange)

		self.axes.set_ylabel(yLabel)
		self.axes.set_xlabel(xLabel)

		self.metax = pnt
		self.metay = val

		self.canvas.draw()

	def plotMeta_updateSelection(self, ba, xMin, xMax):
		"""
		select spikes withing a time range
		"""

		print('bPlotFrame.plotMeta_updateSelection() xMin:', xMin, 'xMax:', xMax)

		# clear existing
		if self.plotMeta_selection is not None:
			for line in self.plotMeta_selection:
				line.remove()

		self.plotMeta_selection = []

		if xMin is not None and xMax is not None:
			for i, spikeTime in enumerate(ba.spikeTimes):
				spikeSeconds = spikeTime / ba.dataPointsPerMs / 1000 # pnts to seconds
				#print(spikeSeconds)
				if spikeSeconds >= xMin and spikeSeconds <= xMax:
					#print(spikeTime)
					line, = self.axes.plot(self.metax[i], self.metay[i], 'oy')
					self.plotMeta_selection.append(line)

		self.canvas.draw()

