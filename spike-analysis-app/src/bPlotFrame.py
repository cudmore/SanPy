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
		
		self.plotMeta_selection = None
		
		self.canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.fig, parent)
		#self.canvas.get_tk_widget().pack(side="bottom", fill="both", expand=True)

		#here
		self.canvas.get_tk_widget().pack(side="bottom", fill="both", expand=1)
		#self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

		self.canvas.draw()

		cid1 = self.canvas.mpl_connect('button_press_event', self.onclick)
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
		
		self.metax = []
		self.metay = []
		
	def onclick(self, event):
		print('onclick() %s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
			('double' if event.dblclick else 'single', event.button,
			event.x, event.y, event.xdata, event.ydata))

	def onpick(self, event):
		print('onpick() event:', event)
		print('   event.ind:', event.ind)
		thisline = event.artist
		xdata = thisline.get_xdata()
		ydata = thisline.get_ydata()
		ind = event.ind
		#print('xdata:', xdata)
		print('   xdata[ind]:', xdata[ind])
		#print('ydata:', ydata)
		print('   ydata[ind]:', ydata[ind])
		points = tuple(zip(xdata[ind], ydata[ind]))
		print('   onpick() points:', points)

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
		yMin = min(self.line.get_ydata())
		yMax = max(self.line.get_ydata())
		
		self.axes.set_xlim(xMin, xMax)
		self.axes.set_ylim(yMin, yMax)

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
		print('ba.thresholdTimes[0]:', ba.thresholdTimes[0])
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
		
		# clear existing
		if self.clipLines_selection is not None:
			for line in self.clipLines_selection:
				line.remove()
		
		self.clipLines_selection = []
		
		for i, spikeTime in enumerate(ba.spikeTimes):
			spikeSeconds = spikeTime / ba.dataPointsPerMs / 1000 # pnts to seconds
			#print(spikeSeconds)
			if spikeSeconds >= xMin and spikeSeconds <= xMax:
				#print(spikeTime)
				line, = self.axes.plot(ba.spikeClips_x, ba.spikeClips[i], 'y')
				self.clipLines_selection.append(line)

		self.canvas.draw()
		
	def plotMeta(self, ba, statName, doInit=False):
		
		print('plotMeta() statName:', statName)
		
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
		if statName == 'isi (sec)':
			spikeTimes_sec = [x/self.controller.ba.abf.dataPointsPerMs/1000 for x in self.controller.ba.spikeTimes]
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
		plot the spike clips within min/max
		"""
				
		print('bPlotFrame.plotMeta_updateSelection() xMin:', xMin, 'xMax:', xMax)
		
		# clear existing
		if self.plotMeta_selection is not None:
			for line in self.plotMeta_selection:
				line.remove()
		
		self.plotMeta_selection = []
		
		for i, spikeTime in enumerate(ba.spikeTimes):
			spikeSeconds = spikeTime / ba.dataPointsPerMs / 1000 # pnts to seconds
			#print(spikeSeconds)
			if spikeSeconds >= xMin and spikeSeconds <= xMax:
				#print(spikeTime)
				line, = self.axes.plot(self.metax[i], self.metay[i], 'oy')
				self.plotMeta_selection.append(line)

		self.canvas.draw()
		
	
		


