# Author: Robert Cudmore
# Date: 20190312

import os

import tkinter
from tkinter import ttk
from tkinter import filedialog

import bMenus
import bFileList
import bTree

# required to import bAnalysis which does 'import matplotlib.pyplot as plt'
# without this, tkinter crashes
import matplotlib
matplotlib.use("TkAgg")

from matplotlib.widgets import SpanSelector

from bAnalysis import bAnalysis

__version__ = '20190312'

LARGE_FONT= ("Verdana", 12)

#####################################################################################
# raw
class PageThree(ttk.Frame):

	def __init__(self, parent, controller, showToolbar=False, analysisList=None):
		"""
		analysisList:
		"""
		print('PageThree.__init__')
		
		ttk.Frame.__init__(self, parent)

		self.controller = controller
		
		myPadding = 10
		
		self.fig = matplotlib.figure.Figure(figsize=(8,4), dpi=100)
		self.axes = self.fig.add_subplot(111)

		self.line, = self.axes.plot([],[], 'k') # REMEMBER ',' ON LHS
		self.spikeTimesLine, = self.axes.plot([],[], 'or') # REMEMBER ',' ON LHS
		
		self.canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.fig, parent)
		self.canvas.get_tk_widget().pack(side="bottom", fill="both", expand=True)
		self.canvas.draw()

		if showToolbar:
			toolbar = matplotlib.backends.backend_tkagg.NavigationToolbar2Tk(self.canvas, parent)
			toolbar.update()
			#toolbar = matplotlib.backends.backend_tkagg.NavigationToolbar2Tk(canvas, controller.root)
			#toolbar.update()
			#self.canvas._tkcanvas.pack(side="top", fill="both", expand=True)
			self.canvas.get_tk_widget().pack(side="bottom", fill="both", expand=True)
		
		#
		# to allow horizontal (time) selection
		self.span = SpanSelector(self.axes, self.onselect, 'horizontal', useblit=True,
					rectprops=dict(alpha=0.5, facecolor='yellow'))

		#
		# a list of analysis line(s)
		self.analysisLines = {}
		for analysis in analysisList:
			print("PageThree.__init__ color analysis:", analysis)
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
			analysisLine, = self.axes.plot([],[], marker + markerColor) # REMEMBER ',' ON LHS
			self.analysisLines[analysis] = analysisLine
			
	def plotStat(self, name, onoff):
		print("=== PageThree.plotStat() name:", name, "onoff:", onoff)
		# self.line.set_ydata
		#self.controller.abf
		#print(self.controller.ba.spikeDict)
		
		# make a list of spike peaks
		pnt = []
		val = []
		if name == 'peak':
			pnt = [x['peakPnt'] for x in self.controller.ba.spikeDict]
			pnt = self.controller.ba.abf.sweepX[pnt]
			val = [x['peakVal'] for x in self.controller.ba.spikeDict]
		if name == 'preMin':
			pnt = [x['preMinPnt'] for x in self.controller.ba.spikeDict]
			# remove none because first/last spike has none for preMin
			pnt = [x for x in pnt if x is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]

			val = [x['preMinVal'] for x in self.controller.ba.spikeDict]
			# remove none because first/last spike has none for preMin
			val = [x for x in val if x is not None]
		if name == 'postMin':
			pnt = [x['postMinPnt'] for x in self.controller.ba.spikeDict]
			# remove none because first/last spike has none for preMin
			pnt = [x for x in pnt if x is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]

			val = [x['preMinVal'] for x in self.controller.ba.spikeDict]
			# remove none because first/last spike has none for preMin
			val = [x for x in val if x is not None]

		if name == 'preLinearFit':
			# 0
			pnt0 = [x['preLinearFitPnt0'] for x in self.controller.ba.spikeDict]
			# remove none because first/last spike has none for preMin
			pnt0 = [x for x in pnt0 if x is not None]
			pnt0 = [self.controller.ba.abf.sweepX[pnt0]]
			# 1
			pnt1 = [x['preLinearFitPnt1'] for x in self.controller.ba.spikeDict]
			# remove none because first/last spike has none for preMin
			pnt1 = [x for x in pnt1 if x is not None]
			pnt1 = [self.controller.ba.abf.sweepX[pnt1]]

			pnt = pnt0 + pnt1 # concatenate
			
			# 0
			val0 = [x['preLinearFitVal0'] for x in self.controller.ba.spikeDict]
			# remove none because first/last spike has none for preMin
			val0 = [x for x in val0 if x is not None]
			# 1
			val1 = [x['preLinearFitVal1'] for x in self.controller.ba.spikeDict]
			# remove none because first/last spike has none for preMin
			val1 = [x for x in val1 if x is not None]
		
			val = val0 + val1 # concatenate
		
		if name == 'preSpike_dvdt_max':
			pnt = [x['preSpike_dvdt_max_pnt'] for x in self.controller.ba.spikeDict]
			# remove none because first/last spike has none for preMin
			pnt = [x for x in pnt if x is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]

			val = [x['preSpike_dvdt_max_val'] for x in self.controller.ba.spikeDict]
			# remove none because first/last spike has none for preMin
			val = [x for x in val if x is not None]
			
		if name == 'postSpike_dvdt_min':
			pnt = [x['postSpike_dvdt_min_pnt'] for x in self.controller.ba.spikeDict]
			# remove none because first/last spike has none for preMin
			pnt = [x for x in pnt if x is not None]
			pnt = self.controller.ba.abf.sweepX[pnt]

			val = [x['postSpike_dvdt_min_val'] for x in self.controller.ba.spikeDict]
			# remove none because first/last spike has none for preMin
			val = [x for x in val if x is not None]
			
		if onoff:
			self.analysisLines[name].set_ydata(val)
			self.analysisLines[name].set_xdata(pnt)
		else:
			self.analysisLines[name].set_ydata([])
			self.analysisLines[name].set_xdata([])

		#print("self.analysisLines[name]:", self.analysisLines[name])
		
		#self.analysisLines[name]
		
		self.canvas.draw()

	def setXAxis(self, xMin, xMax):
		print("PageThree.setXAxis() ", self, "xMin:", xMin, "xMax:", xMax)
		self.axes.set_xlim(xMin, xMax)
		self.canvas.draw()
		
	def onselect(self, xMin, xMax):
		print('PageThree.onselect() xMin:', xMin, 'xMax:', xMax)
		#self.axes.set_xlim(xMin, xMax)
		self.controller.setXAxis(xMin, xMax)

	def plotRaw(self, ba):
		start = 0
		stop = len(ba.abf.sweepX) - 1
		step = 10
		subSetOfPnts = range(start, stop, step)
		
		#ba.plotDeriv(fig=self.fig)
		self.line.set_ydata(ba.abf.sweepY[subSetOfPnts])
		self.line.set_xdata(ba.abf.sweepX[subSetOfPnts])
		
		xMin = min(ba.abf.sweepX)
		xMax = max(ba.abf.sweepX)
		self.axes.set_xlim(xMin, xMax)
		
		yMin = min(ba.abf.sweepY)
		yMax = max(ba.abf.sweepY)
		self.axes.set_ylim(yMin, yMax)
		
		self.canvas.draw()
		
	def plotDeriv(self, ba, dVthresholdPos=50, medianFilter=3):
		#ba.plotDeriv(fig=self.fig)
		
		start = 0
		stop = len(ba.abf.sweepX) - 1
		step = 10
		subSetOfPnts = range(start, stop, step)

		spikeTimes, vm, sweepDeriv = ba.spikeDetect0(dVthresholdPos=dVthresholdPos, medianFilter=medianFilter)
		ba.spikeDetect()
		
		self.line.set_ydata(sweepDeriv[subSetOfPnts])
		self.line.set_xdata(ba.abf.sweepX[subSetOfPnts])
		
		xMin = min(ba.abf.sweepX)
		xMax = max(ba.abf.sweepX)
		self.axes.set_xlim(xMin, xMax)
		
		yMin = min(sweepDeriv)
		yMax = max(sweepDeriv)
		self.axes.set_ylim(yMin, yMax)
		
		self.spikeTimesLine.set_ydata(sweepDeriv[spikeTimes])
		self.spikeTimesLine.set_xdata(ba.abf.sweepX[spikeTimes])

		self.canvas.draw()
		
#####################################################################################
class AnalysisApp:

	def __init__(self, path=None):

		self.configDict = {}
		# load config file

		print(1)
		self.root = tkinter.Tk()

		self.root.title('Analysis App')

		# position root window
		x = 100 #self.configDict['appWindowGeometry_x']
		y = 100 #self.configDict['appWindowGeometry_y']
		w = 2000 #self.configDict['appWindowGeometry_w']
		h = 1000# self.configDict['appWindowGeometry_h']
		self.root.geometry('%dx%d+%d+%d' % (w, h, x, y))

		self.buildInterface()
		
		self.myMenus = bMenus.bMenus(self)

		if path is not None:
			self.loadFolder(path=path)
			
		# this will not return until we quit
		self.root.mainloop()

	def buildInterface(self):
		myPadding = 5
		myBorderWidth = 5

		self.lastResizeWidth = None
		self.lastResizeHeight = None
		
		self.root.grid_rowconfigure(0, weight=1)
		self.root.grid_columnconfigure(0, weight=1)

		#
		# vertical pane to hold everything
		self.vPane = ttk.PanedWindow(self.root, orient="vertical") #, showhandle=True)
		self.vPane.grid(row=0, column=0, sticky="nsew")

		#
		# file list
		upper_frame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		upper_frame.grid(row=0, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		upper_frame.grid_rowconfigure(0, weight=1)
		upper_frame.grid_columnconfigure(0, weight=1)
		self.vPane.add(upper_frame)

		self.fileListTree = bTree.bFileTree(upper_frame, self, videoFileList='')
		self.fileListTree.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)

		#
		# detection params and plot checkboxes
		buttonFrame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		buttonFrame.grid(row=1, column=0, sticky="nw", padx=myPadding, pady=myPadding)
		#buttonFrame.grid_rowconfigure(0, weight=1)
		#buttonFrame.grid_columnconfigure(0, weight=1)
		self.vPane.add(buttonFrame)

		# detection params
		detectButton = ttk.Button(buttonFrame, text='Detect', command=lambda name='detectButton': self.buttonCallback(name))
		detectButton.grid(row=0, column=0, sticky="w")
		#detectButton.pack(side="left")
		
		# threshold
		labelDir = ttk.Label(buttonFrame, text='dV/dt Threshold')
		labelDir.grid(row=0, column=1, sticky="w")
		#labelDir.pack(side="left")

		self.thresholdSpinbox = ttk.Spinbox(buttonFrame, from_=0, to=1000)
		self.thresholdSpinbox.insert(0,100) # default is 100
		self.thresholdSpinbox.grid(row=0, column=2, sticky="w")
		
		# median filter
		labelDir = ttk.Label(buttonFrame, text='Median Filter (pnts)')
		labelDir.grid(row=0, column=3, sticky="w")
		#labelDir.pack(side="left")

		self.filterSpinbox = ttk.Spinbox(buttonFrame, from_=0, to=1000)
		self.filterSpinbox.insert(0,5) # default is 5
		self.filterSpinbox.grid(row=0, column=4, sticky="w")
		
		# plot checkboxes
		self.analysisList = ['vm', 'peak', 'preMin', 'postMin', 'preLinearFit', 'preSpike_dvdt_max', 'postSpike_dvdt_min']
		self.varList = []
		self.checkList = []
		for i, analysisItem in enumerate(self.analysisList):
			var = tkinter.BooleanVar(value=False)
			self.varList.append(var)
			check = ttk.Checkbutton(buttonFrame, text=analysisItem, var=var, command=lambda name=analysisItem, var=var: self.checkCallback(name, var))
			check.grid(row=1, column=i, sticky="w")
			self.checkList.append(check)
		
		#
		# raw data
		lower_frame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		lower_frame.grid(row=2, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		lower_frame.grid_rowconfigure(0, weight=1)
		lower_frame.grid_columnconfigure(0, weight=1)
		self.vPane.add(lower_frame)
		
		self.rawPlot = PageThree(lower_frame, self, showToolbar=True, analysisList=self.analysisList)
		#self.rawPlot.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		
		#
		# deriv data
		print('4')
		deriv_frame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		deriv_frame.grid(row=3, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		deriv_frame.grid_rowconfigure(0, weight=1)
		deriv_frame.grid_columnconfigure(0, weight=1)
		self.vPane.add(deriv_frame)
		
		self.derivPlot = PageThree(deriv_frame, self, showToolbar=False, analysisList=self.analysisList)
		#self.rawPlot.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		
	def buttonCallback(self, buttonName):
		print('buttonCallback() buttonName:', buttonName)
		print('   self.thresholdSpinbox:', self.thresholdSpinbox.get())
		print('   self.filterSpinbox:', self.filterSpinbox.get())
		
	def checkCallback(self, name, var):
		print("checkCallback() name:", name, "var:", var.get())
		onoff = var.get()
		self.rawPlot.plotStat(name, onoff)
		
	def loadFolder(self, path=''):
		if len(path) < 1:
			path = tkinter.filedialog.askdirectory()
		
		if not os.path.isdir(path):
			print('error: did not find path:', path)
			return
		
		self.path = path
		self.configDict['lastPath'] = path
		
		self.fileList = bFileList.bFileList(path)		
		self.fileListTree.populateVideoFiles(self.fileList, doInit=True)
	
		# initialize with first video in path
		firstVideoPath = ''
		if len(self.fileList.videoFileList):
			firstVideoPath = self.fileList.videoFileList[0].dict['path']


	def switchvideo(self, videoPath, paused=False, gotoFrame=None):
		print('=== VideoApp.switchvideo() videoPath:', videoPath, 'paused:', paused, 'gotoFrame:', gotoFrame)

		print('AnalysisApp.switchvideo() we should plot the abf file with matplotlib !!!')
		print('   videoPath:', videoPath)
		
		self.ba = bAnalysis(file=videoPath)
		#print(ba)

		self.rawPlot.plotRaw(self.ba)
		self.derivPlot.plotDeriv(self.ba)
	
	def setXAxis(self, theMin, theMax):
		self.rawPlot.setXAxis(theMin, theMax)
		self.derivPlot.setXAxis(theMin, theMax)

	def onClose(self, event=None):
		print("VideoApp.onClose()")
		'''
		self.isRunning = False
		self.vs.stop()
		self.savePreferences()
		'''
		self.root.quit()

if __name__ == '__main__':
	
	print('starting analysisapp')
	
	aa = AnalysisApp(path='/Users/cudmore/Sites/bAnalysis/data')
	
	print('ending analysis app')