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

import matplotlib.pyplot as plt

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

		# for color maps, see
		# https://chrisalbon.com/python/basics/set_the_color_of_a_matplotlib/
		# https://stackoverflow.com/questions/17682216/scatter-plot-and-color-mapping-in-python
		# was 'plt.cm.RdGy'
		#self.colorTable = plt.cm.YlOrRd
		self.colorTable = plt.cm.coolwarm
		
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
		#cid2 = self.canvas.mpl_connect('pick_event', self.onpick_callback)

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
			if analysis == 'AP Peak (mV)':
				markerColor = 'r'
			if analysis == 'Pre AP Min (mV)':
				markerColor = 'r'
			if analysis == 'Post AP Min (mV)':
				markerColor = 'g'
			if analysis == 'Early Diastolic Duration (ms)':
				markerColor = 'b'
			if analysis == 'Max AP Upstroke (mV)':
				markerColor = 'y'
			if analysis == 'Max AP Repolarization (mV)':
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

		#
		# single point selection
		#self.singlePointSelection, = self.axes.plot([], [], 'oc', markersize=10) # cyan circle
		
		self.metaLines = None
		self.metaLines3 = None
		#self.metaLines, = self.axes.plot([],[], 'ok', cmap=plt.get_cmap('inferno'), picker=5) # REMEMBER ',' ON LHS
		#self.metaLines, = self.axes.scatter([],[], 'ok', c=[], cmap=self.colorTable, picker=5) # REMEMBER ',' ON LHS
		#self.metaLines3, = self.axes.plot([],[], 'ok', picker=5) # REMEMBER ',' ON LHS

		self.metax = []
		self.metay = []

		self.singleSpikeSelection, = self.axes.plot([],[], 'oc', markersize=10) # REMEMBER ',' ON LHS

	'''
	def onclick(self, event):
		print('bPlotFrame.onclick()')
	'''
	
	'''
	def onpick_callback(self, event):
		""" select and propogate user selection of a single spike"""
		
		print('=== bPlotFrame.onpick_callback() event:', event)
		
		# the x/y data we are plotting
		thisline = event.artist
		xdata = thisline.get_xdata()
		ydata = thisline.get_ydata()

		ind = event.ind
		print('   event.ind:', ind)
		ind = int(ind[0])

		print('   xdata[ind]:', xdata[ind], 'ydata[ind]:', ydata[ind])

		#
		# select spike in this plot
		xDataSinglePoint = xdata[ind]
		yDataSinglePoint = ydata[ind]
		self.singleSpikeSelection.set_xdata(xDataSinglePoint)
		self.singleSpikeSelection.set_ydata(yDataSinglePoint)
		self.canvas.draw()
		
		#
		# propagate selected spike to other views
		# e.g. select spike in (raw data, meta plot 3)
		self.controller.selectSpike(event, ind)
	'''
	
	def onpick3_callback(self, event):
		print('=== bPlotFrame.onpick3_callback() event:', event, 'event.ind:', event.ind)

		ind = event.ind
		ind = ind[0]
		
		'''
		# the x/y data we are plotting
		offsets = event.artist.get_offsets()
		print('   offsets[ind]:', offsets[ind])
		xData = offsets[ind][0]
		yData = offsets[ind][1]
		
		print('   x:', xData, 'y:', yData)
		'''
		
		#
		# select spike in this plot
		'''
		self.singleSpikeSelection.set_xdata(xData)
		self.singleSpikeSelection.set_ydata(yData)
		self.canvas.draw()
		'''
		
		# select spike 'ind' in raw data
		self.controller.selectSpike(ind)

	def plotStat(self, name, onoff):
		#print("=== bPlotFrame.plotStat() name:", name, "onoff:", onoff)

		if not onoff:
			self.analysisLines[name].set_ydata([])
			self.analysisLines[name].set_xdata([])
			#
			if name == 'halfWidth':
				self.analysisLines['halfWidthLines'].set_ydata([])
				self.analysisLines['halfWidthLines'].set_xdata([])
			#
			self.canvas.draw()
			###
			return 
			###
			
		pnt = []
		val = []
		if name == 'Take Off Potential (mV)':
			pnt = [x['thresholdPnt'] for x in self.controller.ba.spikeDict]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['thresholdVal'] for x in self.controller.ba.spikeDict]
		if name == 'AP Peak (mV)':
			pnt = [x['peakPnt'] for x in self.controller.ba.spikeDict]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['peakVal'] for x in self.controller.ba.spikeDict]
		if name == 'Pre AP Min (mV)':
			pnt = [x['preMinPnt'] for x in self.controller.ba.spikeDict if x['preMinPnt'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['preMinVal'] for x in self.controller.ba.spikeDict if x['preMinPnt'] is not None]
		if name == 'Post AP Min (mV)':
			pnt = [x['postMinPnt'] for x in self.controller.ba.spikeDict if x['postMinPnt'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['postMinVal'] for x in self.controller.ba.spikeDict if x['postMinPnt'] is not None]

		if name == 'Early Diastolic Duration (ms)':
			# 0
			pnt0 = [x['preLinearFitPnt0'] for x in self.controller.ba.spikeDict if x['preLinearFitPnt0'] is not None]
			# 1
			pnt1 = [x['preLinearFitPnt1'] for x in self.controller.ba.spikeDict if x['preLinearFitPnt1'] is not None]
			# concatenate
			pnt = pnt0 + pnt1 # concatenate
			# could convert pnt to sec???
			pnt = self.controller.ba.abf.sweepX[pnt]

			# 0
			val0 = [x['preLinearFitVal0'] for x in self.controller.ba.spikeDict if x['preLinearFitPnt0'] is not None]
			# remove none because first/last spike has none for preMin
			val0 = [x for x in val0 if x is not None]
			# 1
			val1 = [x['preLinearFitVal1'] for x in self.controller.ba.spikeDict if x['preLinearFitPnt1'] is not None]
			# concatenate
			val = val0 + val1 # concatenate

		if name == 'Max AP Upstroke (mV)':
			pnt = [x['preSpike_dvdt_max_pnt'] for x in self.controller.ba.spikeDict if x['preSpike_dvdt_max_pnt'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['preSpike_dvdt_max_val'] for x in self.controller.ba.spikeDict if x['preSpike_dvdt_max_pnt'] is not None]

		if name == 'Max AP Repolarization (mV)':
			pnt = [x['postSpike_dvdt_min_pnt'] for x in self.controller.ba.spikeDict if x['postSpike_dvdt_min_pnt'] is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['postSpike_dvdt_min_val'] for x in self.controller.ba.spikeDict if x['postSpike_dvdt_min_pnt'] is not None]

		# this is a little innefficient
		if name == 'halfWidth':
			pnt = []
			val = []
			for i, spikeDict in enumerate(self.controller.ba.spikeDict):
				for j,widthDict in enumerate(spikeDict['widths']):
					'''
					print('bPlotFrame widthDict:', widthDict)
					print("xxx spike", i, "width", j, "widthDict['risingPnt']:", widthDict['risingPnt'])
					print("    spike", i, "width", j, "widthDict['fallingPnt']:", widthDict['fallingPnt'])
					'''
					if widthDict['risingPnt'] is not None:
						pnt.append(self.controller.ba.abf.sweepX[widthDict['risingPnt']])
						pnt.append(self.controller.ba.abf.sweepX[widthDict['fallingPnt']])
						pnt.append(float('nan'))

						#val.append(widthDict['risingVal'])
						# use the faalingVal as it makes plot look more 'real', rising val is too fast
						val.append(widthDict['fallingVal'])
						val.append(widthDict['fallingVal'])
						val.append(float('nan'))
			# explicitly plot lines
			#ax.plot([risingPntX, fallingPntX], [risingPntY, fallingPntY], color='b', linestyle='-', linewidth=2)
			# 'halfWidthLines' sits dormant for all other plots
			if onoff:
				self.analysisLines['halfWidthLines'].set_ydata(val)
				self.analysisLines['halfWidthLines'].set_xdata(pnt)
			else:
				self.analysisLines['halfWidthLines'].set_ydata([])
				self.analysisLines['halfWidthLines'].set_xdata([])
			
		#
		# plot
		if onoff:
			self.analysisLines[name].set_ydata(val) #todo: stupid to have self.analysisLines as dict. We are only ever plotting one stat !!!
			self.analysisLines[name].set_xdata(pnt)
		else:
			self.analysisLines[name].set_ydata([])
			self.analysisLines[name].set_xdata([])

		self.canvas.draw()

	def _get_x_axes(self):
		theMin, theMax = self.axes.get_xlim()
		return theMin, theMax
		
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
		print('=== bPlotFrame.onselect() xMin:', xMin, 'xMax:', xMax)
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
		print('bPlotFrame.selectSpike() spikeNumber:', spikeNumber)
		if spikeNumber is None:
			self.singleSpikeSelection.set_ydata([])
			self.singleSpikeSelection.set_xdata([])		
		else:
			spikeVm = ba.abf.sweepY[ba.spikeTimes[spikeNumber]]
			spikeSeconds = ba.abf.sweepX[ba.spikeTimes[spikeNumber]]
			self.singleSpikeSelection.set_ydata(spikeVm)
			self.singleSpikeSelection.set_xdata(spikeSeconds)

		self.canvas.draw()
	
	def selectSpikeMeta(self, ba, spikeNumber):
		""" Select a single spike in raw trace """

		print('bPlotFrame.selectSpikeMeta() spikeNumber:', spikeNumber)

		if spikeNumber is None:
			self.singleSpikeSelection.set_ydata([])
			self.singleSpikeSelection.set_xdata([])		
		else:			

			offsets = self.metaLines3.get_offsets()
			xData = offsets[spikeNumber][0]
			yData = offsets[spikeNumber][1]
			print('   xData:', xData, 'yData:', yData)

			self.singleSpikeSelection.set_xdata(xData)
			self.singleSpikeSelection.set_ydata(yData)
			
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
			if xMin==0 and xMax==0:
				# donlt warn
				pass
			else:
				print('error: bPlotFrame.plotClips_updateSelection() did not update the mean clip')
			
		self.canvas.draw()

		self.controller.setStatus()

		return len(self.clipLines_selection)
		
	def plotMeta3(self, xStat, yStat):

		print('bPlotFrame.plotMeta3() xStat:', xStat, 'yStat:', yStat)

		cid2 = self.canvas.mpl_connect('pick_event', self.onpick3_callback)

		# fill in based on statName
		xVal = [] # x
		yVal = [] # y

		xLabel = ''
		yLabel = ''

		# clear existing
		if self.metaLines3 is not None:
			#print('type(self.metaLines3):', type(self.metaLines3))
			self.metaLines3.remove()
			self.metaLines3 = None
			
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
				thisVal = self.controller.ba.abf.sweepX[thresholdPnt]

			'''
			if thisStat == 'threshold':
				thisVal = [x['thresholdVal'] for x in self.controller.ba.spikeDict]
			'''
			if thisStat == 'AP Height (mV)':
				thisVal = [x['peakHeight'] for x in self.controller.ba.spikeDict]
			'''
			if thisStat == 'peak':
				thisVal = [x['peakVal'] for x in self.controller.ba.spikeDict]
			'''
			if thisStat == 'Pre AP Min (mV)':
				thisVal = [x['preMinVal'] for x in self.controller.ba.spikeDict]
			if thisStat == 'Post AP Min (mV)':
				thisVal = [x['postMinVal'] for x in self.controller.ba.spikeDict]
			if thisStat == 'Early Diastolic Depol Rate (dV/s)':
				thisVal = [x['earlyDiastolicDurationRate'] for x in self.controller.ba.spikeDict]
			if thisStat == 'Max AP Upstroke (mV)':
				thisVal = [x['preSpike_dvdt_max_val'] for x in self.controller.ba.spikeDict]
			if thisStat == 'Max AP Repolarization (mV)':
				thisVal = [x['postSpike_dvdt_min_val'] for x in self.controller.ba.spikeDict]
			
			if thisStat == 'halfWidth':
				thisVal = [x['widths'][0]['widthMs'] for x in self.controller.ba.spikeDict]
				'''
				thisVal = []
				for j,widthDict in enumerate(self.controller.ba.spikeDict['widths']):
					thisValue.append(widthDict['widthMs']
				'''
				
			if thisStat == 'Inter-Spike-Interval (ms)':
				'''
				spikeTimes_sec = [x/self.controller.ba.abf.dataPointsPerMs for x in self.controller.ba.spikeTimes]
				del spikeTimes_sec[0]
				thisVal = np.diff(spikeTimes_sec)
				thisVal = np.concatenate(([np.NaN],thisVal))
				thisVal = np.delete(thisVal, 0)
				#thisVal = np.delete(thisVal, 0)
				'''
				thisVal = [x['isi_ms'] for x in self.controller.ba.spikeDict]
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
				thisVal = [x['peakVal'] for x in self.controller.ba.spikeDict]

			if thisStat == 'MDP (mV)':
				thisVal = [x['postMinVal'] for x in self.controller.ba.spikeDict]

			if thisStat == 'Take Off Potential (mV)':
				thisVal = [x['thresholdVal'] for x in self.controller.ba.spikeDict]

			if thisStat == 'Cycle Length (ms)':
				#todo: fix this, 'cycleLength_ms' is only calculated for spike # > 1
				thisVal = [x['cycleLength_ms'] for x in self.controller.ba.spikeDict] # todo: can be nan, never none !!!

			if thisStat == 'Max AP Upstroke (dV/dt)':
				thisVal = [x['preSpike_dvdt_max_val2'] for x in self.controller.ba.spikeDict]

			if thisStat == 'Max AP Repolarization (dV/dt)':
				thisVal = [x['postSpike_dvdt_min_val2'] for x in self.controller.ba.spikeDict]

			if thisStat == 'AP Duration (ms)':
				#todo: fix this, 'apDuration' is only calculated for spike # > 0
				# could use 'thresholdSec' and not index sweepX[]
				thisVal = [x['apDuration_ms'] for x in self.controller.ba.spikeDict]

			if thisStat == 'Diastolic Duration (ms)':
				# in general, any time we plot threshold versus a stat (like diastolicDuration)
				# we need this extra 'is not None' because we are only calculating stats (like diastolicDuration)
				# for spike >1 and <len(spikes)
				thisVal = [x['diastolicDuration_ms'] for x in self.controller.ba.spikeDict]

			if thisStat == 'Early Diastolic Depol Rate (dV/s)':				
				thisVal = [x['earlyDiastolicDurationRate'] for x in self.controller.ba.spikeDict]

			if thisStat == 'Early Diastolic Duration (ms)':
				thisVal = [x['earlyDiastolicDuration_ms'] for x in self.controller.ba.spikeDict]

			if thisStat == 'Late Diastolic Duration (ms)':
				thisVal = [x['lateDiastolicDuration'] for x in self.controller.ba.spikeDict]

			#
			if currentAxis == 'x':
				xVal = thisVal
				xLabel = thisLabel
			elif currentAxis == 'y':
				yVal = thisVal
				yLabel = thisLabel

		#
		# replot
		#print('   len(xVal):', len(xVal), 'len(yVal):', len(yVal))
		tmpColor = range(len(xVal))
		if xStat == 'Phase Plot' and yStat == 'Phase Plot':
			# todo: get color in here
			self.metaLines3 = self.axes.scatter(xVal,yVal, picker=5)
		
		else:
			self.metaLines3 = self.axes.scatter(xVal,yVal, c=tmpColor, cmap=self.colorTable, picker=5)

		# remove previous selection
		self.singleSpikeSelection.set_xdata([])
		self.singleSpikeSelection.set_ydata([])

		#
		# set axis
		#print('xStat:', xStat)
		try:
			xMin = np.nanmin(xVal) # for phase plot, is 2d array
			xMax = np.nanmax(xVal)
			if xMin == float('nan') or xMax == float('nan'):
				print('error: bPlotFrame.plotMeta3() got xMin/xMax nan?')
			else:
				if xStat == 'Time (sec)':
					tenPercentRange = 0 #abs(xMax-xMin) * 0.05
					xMin = self.controller.ba.abf.sweepX[0]
					xMax = self.controller.ba.abf.sweepX[-1]
				else:
					tenPercentRange = abs(xMax-xMin) * 0.1
				self.axes.set_xlim(xMin-tenPercentRange, xMax+tenPercentRange)
		except ValueError:
			print('warning: bPlotFrame.plotMeta3() ValueError in setting x-axis')
			
		try:
			yMin = np.nanmin(yVal)
			yMax = np.nanmax(yVal)
			if yMin == float('nan') or yMax == float('nan'):
				print('error: bPlotFrame.plotMeta3() got yMin/yMax nan?')
			else:
				tenPercentRange = abs(yMax-yMin) * 0.1
				self.axes.set_ylim(yMin-tenPercentRange, yMax+tenPercentRange)
		except ValueError:
			print('warning: bPlotFrame.plotMeta3() ValueError in setting y-axis')
						
		self.axes.set_xlabel(xLabel)
		self.axes.set_ylabel(yLabel)

		self.metax = xVal
		self.metay = yVal

		# on plotting, always cancel single spike selection
		self.singleSpikeSelection.set_ydata([])
		self.singleSpikeSelection.set_xdata([])		

		self.canvas.draw()

	def plotMeta(self, ba, statName, doInit=False):

		print('bPlotFrame.plotMeta() statName:', statName)

		self.plotMeta3('Time (sec)', statName)
		
		return	

	def plotMeta_updateSelection(self, ba, xMin, xMax):
		"""
		select spikes withing a time range (they will be yellow)
		"""

		print('bPlotFrame.plotMeta_updateSelection() xMin:', xMin, 'xMax:', xMax)

		self.controller.setStatus('Updating meta plot selection')

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
					line, = self.axes.plot(self.metax[i], self.metay[i], 'oy', markersize=10)
					self.plotMeta_selection.append(line)

		self.canvas.draw()

		self.controller.setStatus()

