'''
Author: Robert Cudmore
Date: 20190312

switchFile(): called when user clicks on file in file list
report(): to generate output reports

'''

import sys, os, time, json, collections

import numpy as np
import pandas as pd

import tkinter
from tkinter import ttk
from tkinter import filedialog
from tkinter.filedialog import asksaveasfilename

# required to import bAnalysis which does 'import matplotlib.pyplot as plt'
# without this, tkinter crashes
import matplotlib
matplotlib.use("TkAgg")

from bAnalysis import bAnalysis
import bMenus
import bFileList
import bTree

from bPlotFrame import bPlotFrame

#__version__ = '20190312'
#__version__ = '20190316'
__version__ = '20190328'

#####################################################################################
class AnalysisApp:

	def __init__(self, path=''):

		self.preferencesLoad()

		self.root = tkinter.Tk()
		self.root.title('Analysis App')

		self.root.wm_protocol("WM_DELETE_WINDOW", self.onClose)
		self.root.bind('<Command-q>', self.onClose)
		self.root.bind("<Escape>", self.escapeKey_callback)
		
		'''
		self._after_id = None
		self.root.bind("<Configure>", self.schedule_redraw)
		'''
		
		# remove the default behavior of invoking the button with the space key
		self.root.unbind_class("Button", "<Key-space>")

		# position root window
		x = self.configDict['windowGeometry']['x']
		y = self.configDict['windowGeometry']['y']
		w = self.configDict['windowGeometry']['width']
		h = self.configDict['windowGeometry']['height']
		self.root.geometry('%dx%d+%d+%d' % (w, h, x, y))

		self.currentFilePath = ''
		self.ba = None

		self.myPadding = 5
		self.myBorderWidth = 2
		self.myRelief = "sunken"

		# preLinearFit is 'Early Diastolic Depol Rate (dV/s)'
		# 'Post AP Min (mV)' is 'MDP (mV)'
		
		#self.analysisList = ['threshold', 'peak', 'peakHeight', 'preMin', 'postMin', 'preLinearFit', 'preSpike_dvdt_max', 'postSpike_dvdt_min', 'halfWidth']
		self.analysisList = ['Take Off Potential (mV)',
								'AP Peak (mV)',
								'AP Height (mV)',
								'Pre AP Min (mV)',
								'Post AP Min (mV)',
								'Early Diastolic Depol Rate (dV/s)',
								'Early Diastolic Duration (ms)',
								'Max AP Upstroke (mV)',
								'Max AP Upstroke (dV/dt)',
								'Max AP Repolarization (mV)',
								'Max AP Repolarization (dV/dt)',
								'halfWidth',
								'Inter-Spike-Interval (ms)']
		self.metaAnalysisList = self.analysisList #+ ['Inter-Spike-Interval (ms)']

		# remove stats that are already in self.analysisList
		# todo: add in 'Late Diastolic Duration (ms)'
		self.metaAnalysisList2 = ['Cycle Length (ms)',
								'AP Duration (ms)',
								'Diastolic Duration (ms)']
		
		self.analysisListIgnore = ['AP Height (mV)',
									'Early Diastolic Depol Rate (dV/s)',
									'Max AP Upstroke (dV/dt)',
									'Max AP Repolarization (dV/dt)',
									'Inter-Spike-Interval (ms)']
				
		self.metaAnalysisList3 = ['Time (sec)'] + self.metaAnalysisList + self.metaAnalysisList2

		self.buildInterface3()

		self.myMenus = bMenus.bMenus(self)

		self.metaWindow = None # see self.metaWindow3()
		self.metaPlot3 = None

		if len(path) == 0:
			path = self.configDict['lastPath']
		self.loadFolder(path=path)

		
		# the following while try/except is SUPER IMPORTANT
		# see: https://stackoverflow.com/questions/16995969/inertial-scrolling-in-mac-os-x-with-tkinter-and-python
		# without this little trick, we get random crashes while scrolling the stat list (in meta plot) with the mouse wheel
		# the errors show up as "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff"
		# was this
		#self.root.mainloop()
		# now this
		while True:
			try:
				# this will not return until we quit
				self.root.mainloop()
				break
			except UnicodeDecodeError:
				pass
				
	def setStatus(self, str='Idle'):
		"""
		Set program status at top of window
		"""
		#print('AnalysisApp.setStatus() str:', str)
		self.statusLabel.configure(text='Status: ' + str)
		if str == 'Idle':
			self.statusLabel['foreground'] = 'black'
		else:
			self.statusLabel['foreground'] = 'red'
		# force label to update
		self.statusLabel.update()

	def buildDetectionFrame(self, container):
		"""
		Detection parameters, (sweep number, dV/dt threshold, hal widhts, etc)
		"""
		detection_frame = ttk.Frame(container, borderwidth=self.myBorderWidth, relief=self.myRelief)

		row = 0

		#
		# detect button
		detectButton = ttk.Button(detection_frame, text='Detect Spikes', command=lambda name='detectButton': self.button_Callback(name))
		detectButton.grid(row=row, column=0, sticky="w")

		# auto detect checkbox
		#print("self.configDict['autoDetect']:", self.configDict['autoDetect'])
		var = tkinter.BooleanVar(value=self.configDict['autoDetect'])
		check = ttk.Checkbutton(detection_frame, text='Auto Detect', var=var, command=lambda name='autoAnalysisCheckbox', var=var: self.check_Callback(name, var))
		check.grid(row=row, column=1, sticky="w")
		
		# popup for sweeps
		self.sweepVar = tkinter.StringVar(self.root)
 
		# Dictionary with options
		self.sweepChoices = ['','0'] # choices is a Python 'set'
		self.sweepVar.set('0') # set the default option
 
		self.sweepPopupMenu = ttk.OptionMenu(detection_frame, self.sweepVar, *self.sweepChoices, command=self.sweepPopupMenu_callback)
		sweepPopupLabel = ttk.Label(detection_frame, text="Sweep")
		sweepPopupLabel.grid(row = row, column = 2)
		self.sweepPopupMenu.grid(row = row, column =3)
 
		row += 1

		# dV/dt threshold
		labelDir = ttk.Label(detection_frame, text='dV/dt Threshold')
		labelDir.grid(row=row, column=0, sticky="w")
		
		dvdtThreshold = self.configDict['detection']['dvdtThreshold']
		self.thresholdSpinbox = ttk.Spinbox(detection_frame, from_=0, to=1000, width=5)
		self.thresholdSpinbox.insert(0,dvdtThreshold) # default is 100
		self.thresholdSpinbox.grid(row=row, column=1, sticky="w")

		row += 1

		# Vm Threshold (mV)
		labelDir = ttk.Label(detection_frame, text='Vm Threshold (mV)')
		labelDir.grid(row=row, column=0, sticky="w")

		minSpikeVm = self.configDict['detection']['minSpikeVm']
		self.minSpikeVmSpinbox = ttk.Spinbox(detection_frame, from_=0, to=1000, width=5)
		self.minSpikeVmSpinbox.insert(0,minSpikeVm) # default is 100
		self.minSpikeVmSpinbox.grid(row=row, column=1, sticky="w")


		row += 1

		# spike half-widths
		labelDir = ttk.Label(detection_frame, text='Half Widths')
		labelDir.grid(row=row, column=0, sticky="w")
		
		haldWidthsStr = '20, 50, 80'
		self.halfWidthEntry = ttk.Entry(detection_frame, width=10)
		self.halfWidthEntry.insert(0,'10,50,90') # default is 100
		self.halfWidthEntry.grid(row=row, column=1, sticky="w")

		row += 1
				
		
		# time range
		labelDir = ttk.Label(detection_frame, text='From (Sec)')
		labelDir.grid(row=row, column=0, sticky="w")

		self.startSecondsSpinbox = ttk.Spinbox(detection_frame, from_=0, to=1000, width=5)
		self.startSecondsSpinbox.insert(0,0) # default is 0
		self.startSecondsSpinbox.grid(row=row, column=1, sticky="w")

		labelDir = ttk.Label(detection_frame, text='To (Sec)')
		labelDir.grid(row=row, column=2, sticky="w")

		self.stopSecondsSpinbox = ttk.Spinbox(detection_frame, from_=0, to=1000, width=5)
		self.stopSecondsSpinbox.insert(0,float('inf')) # default is inf
		self.stopSecondsSpinbox.grid(row=row, column=3, sticky="w")

		row += 1


		# median filter
		labelDir = ttk.Label(detection_frame, text='Median Filter (pnts)')
		labelDir.grid(row=row, column=0, sticky="w")

		medianFilter = self.configDict['detection']['medianFilter']
		self.filterSpinbox = ttk.Spinbox(detection_frame, from_=0, to=1000, width=3)
		self.filterSpinbox.insert(0,medianFilter) # default is 5
		self.filterSpinbox.grid(row=row, column=1, sticky="w")

		row += 1


		#
		# feedback frame (columnspan = 3)
		feedback_frame = ttk.Frame(detection_frame, borderwidth=self.myBorderWidth, relief=self.myRelief)
		feedback_frame.grid(row=row, column=0, sticky="w", columnspan=3)
		

		# number of detected spikes
		self.numSpikesLabel = ttk.Label(feedback_frame, text='Number of spikes detected: None')
		self.numSpikesLabel.grid(row=0, column=0, sticky="w")

		# number of errors during spike detection
		self.numErrorsLabel = ttk.Label(feedback_frame, text='Number of spike errors: None')
		self.numErrorsLabel.grid(row=1, column=0, sticky="w")

		row += 1


		# save spike report button
		reportButton = ttk.Button(detection_frame, text='Save Spike Report', command=lambda name='reportButton': self.button_Callback(name))
		reportButton.grid(row=row, column=0, sticky="w")

		row += 1

		# important
		return detection_frame

	# not used
	'''
	def buildGlobalOptionsFrame(self, container):
		plotOptionsFrame = ttk.Frame(container, borderwidth=self.myBorderWidth, relief=self.myRelief)

		# reset axes button
		resetAxesButton = ttk.Button(plotOptionsFrame, text='Reset Axes', command=lambda name='fullAxisButton': self.button_Callback(name))
		resetAxesButton.grid(row=0, column=0, sticky="w")

		# plot a subset of points
		labelDir = ttk.Label(plotOptionsFrame, text='Plot Every (pnt)')
		labelDir.grid(row=0, column=1, sticky="w")

		plotEveryPoint = self.configDict['display']['plotEveryPoint']
		self.plotEverySpinbox = ttk.Spinbox(plotOptionsFrame, from_=1, to=1000, width=5, validate="focusout", validatecommand=lambda name='plotEverySpinbox': self.spinBox_Callback(name))
		self.plotEverySpinbox.insert(0,plotEveryPoint) # default is 10
		self.plotEverySpinbox.grid(row=0, column=2, sticky="w")

		return plotOptionsFrame
	'''
	
	def buildPlotOptionsFrame(self, container):
		#
		# plot options frame (checkboxes)
		plotOptionsFrame = ttk.Frame(container, borderwidth=self.myBorderWidth, relief=self.myRelief)

		# reset axes button
		resetAxesButton = ttk.Button(plotOptionsFrame, text='Reset Axes', command=lambda name='fullAxisButton': self.button_Callback(name))
		resetAxesButton.grid(row=0, column=0, sticky="w")

		# plot a subset of points
		labelDir = ttk.Label(plotOptionsFrame, text='Plot Every (pnt)')
		labelDir.grid(row=0, column=1, sticky="w")

		plotEveryPoint = self.configDict['display']['plotEveryPoint']
		self.plotEverySpinbox = ttk.Spinbox(plotOptionsFrame, from_=1, to=1000, width=5, validate="focusout", validatecommand=lambda name='plotEverySpinbox': self.plotEverySpinbox_Callback(name))
		self.plotEverySpinbox.insert(0,plotEveryPoint) # default is 10
		self.plotEverySpinbox.grid(row=0, column=2, sticky="w")

		row = 1

		# plot checkboxes
		#self.analysisList = ['threshold', 'peak', 'preMin', 'postMin', 'preLinearFit', 'preSpike_dvdt_max', 'postSpike_dvdt_min', 'halfWidth']
		self.varList = []
		#self.checkList = []
		myStyle = ttk.Style()
		numAdded = 0
		for i, analysisItem in enumerate(self.analysisList):
			# ignor some
			'''
			if analysisItem in ['peakHeight']:
				continue
			'''
			
			styleStr = analysisItem + '.TCheckbutton'
			foreground = 'black'
			if analysisItem == 'AP Peak (mV)':
				foreground = 'red2'
			if analysisItem == 'Pre AP Min (mV)':
				foreground = 'red2'
			if analysisItem == 'Post AP Min (mV)':
				foreground = 'green2'
			if analysisItem == 'Early Diastolic Depol Rate (dV/s)':
				foreground = 'blue'
			if analysisItem == 'Max AP Upstroke (mV)':
				foreground = 'yellow3'
			if analysisItem == 'Max AP Repolarization (mV)':
				foreground = 'yellow3'
			if analysisItem == 'halfWidth':
				foreground = 'blue'
			myStyle.configure(styleStr, foreground=foreground)

			var = tkinter.BooleanVar(value=False)
			self.varList.append(var)
			#if analysisItem == 'AP Height (mV)':
			if analysisItem in self.analysisListIgnore:
				pass
			else:
				check = ttk.Checkbutton(plotOptionsFrame, text=analysisItem, var=var, style=styleStr, command=lambda name=analysisItem, var=var: self.check_Callback(name, var))
				check.grid(row=row+numAdded, column=0, sticky="w")
				#self.checkList.append(check)
				numAdded += 1

		return plotOptionsFrame

	def buildClipsOptionsFrame(self, container):
		clipOptionsFrame = ttk.Frame(container, borderwidth=self.myBorderWidth, relief=self.myRelief)

		# number of detected spikes
		self.numClipsLabel = ttk.Label(clipOptionsFrame, text='Number of spike clips: None')
		self.numClipsLabel.grid(row=0, column=0, sticky="w")

		self.showClips = tkinter.BooleanVar(value=False)
		check = ttk.Checkbutton(clipOptionsFrame, text='Show clips', var=self.showClips, command=lambda name='showClips', var=self.showClips: self.check_Callback(name, var))
		check.grid(row=1, column=0, sticky="w")

		return clipOptionsFrame

	def buildMetaOptionsFrame(self, container):
		#
		# meta plot frame
		
		'''
		statList = self.metaAnalysisList + self.metaAnalysisList2
		statList = ['Time (sec)'] + statList
		'''
		
		metaStatFrame = ttk.Frame(container, borderwidth=self.myBorderWidth, relief=self.myRelief)
		metaStatFrame.grid(row=0, column=0, sticky="nsew")

		metaStatFrame.grid_rowconfigure(0, weight=1)
		metaStatFrame.grid_columnconfigure(0, weight=1)

		#
		# y
		self.metaTree_y = bTree.bMetaTree(metaStatFrame, self, statList=self.metaAnalysisList3, name='mainWindow')
		self.metaTree_y.grid(row=0,column=0, sticky="nsew")

		return metaStatFrame

	def buildInterface3(self):
		horizontalSashPos = 400

		self.root.grid_rowconfigure(0, weight=1)
		self.root.grid_columnconfigure(0, weight=1)

		self.vPane = ttk.PanedWindow(self.root, orient="vertical")
		self.vPane.grid(row=0, column=0, sticky="nsew")

		#
		# status frame, see self.setStatus()
		status_frame = ttk.Frame(self.vPane, borderwidth=self.myBorderWidth, relief=self.myRelief)
		self.vPane.add(status_frame)

		self.statusLabel = ttk.Label(status_frame)
		self.statusLabel.grid(row=0, column=0, sticky="w")
		self.setStatus('Building Interface')

		#
		# horizontal pane for file list and global plot options

		#
		# file list frame
		fileList_frame = ttk.Frame(self.vPane, borderwidth=self.myBorderWidth, relief=self.myRelief)
		self.vPane.add(fileList_frame)

		self.fileListTree = bTree.bFileTree(fileList_frame, self, videoFileList='')
		self.fileListTree.grid(row=1,column=0, sticky="nsew")

		#
		# horizontal pane for detection options and dv/dt plot
		hPane_detection = ttk.PanedWindow(self.vPane, orient="horizontal")
		self.vPane.add(hPane_detection)

		detectionFrame = self.buildDetectionFrame(hPane_detection)
		hPane_detection.add(detectionFrame)

		# dvdt plot
		derivFrame = ttk.Frame(hPane_detection, borderwidth=self.myBorderWidth, relief=self.myRelief)
		hPane_detection.add(derivFrame)

		self.derivPlot = bPlotFrame(derivFrame, self, showToolbar=False, analysisList=self.analysisList)

		hPane_detection.sashpos(0, horizontalSashPos)

		#
		# horizontal pane for plot options and raw data
		hPane_plot = ttk.PanedWindow(self.vPane, orient="horizontal")
		self.vPane.add(hPane_plot)

		plotOptionsFrame = self.buildPlotOptionsFrame(hPane_plot)
		hPane_plot.add(plotOptionsFrame)

		# vm plot
		rawFrame = ttk.Frame(hPane_plot, borderwidth=self.myBorderWidth, relief=self.myRelief)
		hPane_plot.add(rawFrame)

		self.rawPlot = bPlotFrame(rawFrame, self, showToolbar=False, analysisList=self.analysisList)

		hPane_plot.sashpos(0, horizontalSashPos)

		#
		# horizontal pane for spike clips (only one column
		# spike clips
		hPane_clips = ttk.PanedWindow(self.vPane, orient="horizontal")
		self.vPane.add(hPane_clips)

		spikeClipsOptionsFrame = self.buildClipsOptionsFrame(hPane_clips)
		hPane_clips.add(spikeClipsOptionsFrame)

		# spike clips plot
		spikeClipsFrame = ttk.Frame(hPane_clips, borderwidth=self.myBorderWidth, relief=self.myRelief)
		hPane_clips.add(spikeClipsFrame)

		self.clipsPlot = bPlotFrame(spikeClipsFrame, self, showToolbar=False, analysisList=self.analysisList, allowSpan=False)

		hPane_clips.sashpos(0, horizontalSashPos)

		#
		# horizontal pane for meta plot interface an actual meta plot
		hPane_meta = ttk.PanedWindow(self.vPane, orient="horizontal")
		self.vPane.add(hPane_meta)

		metaFrame = self.buildMetaOptionsFrame(hPane_meta)
		hPane_meta.add(metaFrame)

		# meta plot
		metaAnalysisFrame = ttk.Frame(hPane_meta, borderwidth=self.myBorderWidth, relief=self.myRelief)
		hPane_meta.add(metaAnalysisFrame)

		self.metaPlot = bPlotFrame(metaAnalysisFrame, self, showToolbar=False, allowSpan=False)

		hPane_meta.sashpos(0, horizontalSashPos)

	def escapeKey_callback(self, event):
		""" cancel all user selections (cyan) """
		print('escapeKey_callback event:', event)
		# todo: fix selectSpike(), it does not need ba, here we are passing None
		self.rawPlot.selectSpike(None, None)
		self.metaPlot.selectSpike(None, None)
		if self.metaPlot3 is not None:
			self.metaPlot3.selectSpike(None, None)
					
	def sweepPopupMenu_callback(self, event):
		""" Handle user selection of sweep popup menu """
		print('=== AnalysisApp.sweepPopupMenu_callback()', self.sweepVar.get())
		sweep = int(self.sweepVar.get())
		self.switchSweep(sweep)
		
	def plotEverySpinbox_Callback(self, name):
		plotEveryPoint = int(self.plotEverySpinbox.get())
		print('plotEverySpinbox_Callback:', name, 'plotEveryPoint:', plotEveryPoint)
		self.rawPlot.plotRaw(self.ba, plotEveryPoint=plotEveryPoint)
		self.derivPlot.plotDeriv(self.ba, plotEveryPoint=plotEveryPoint)
		return True

	def button_Callback(self, buttonName):
		print('=== AnalysisApp.button_Callback() buttonName:', buttonName)
		#print('   self.thresholdSpinbox:', self.thresholdSpinbox.get())
		#print('   self.filterSpinbox:', self.filterSpinbox.get())

		if buttonName == 'detectButton':
			'''
			if self.configDict['autoDetect']:
				self.detectSpikes()
			'''
			self.detectSpikes()
			self.replotResults()

		if buttonName == 'fullAxisButton':
			self.setXAxis_full()
			#self.rawPlot.setFullAxis()
			#self.derivPlot.setFullAxis()

		if buttonName == 'reportButton':
			theMin, theMax = self._get_xaxis()
			self.saveReport(theMin, theMax)

		if buttonName == 'Phase Plot':
			self.metaPlot3.plotMeta3('Phase Plot', 'Phase Plot')
			
	def _get_xaxis(self):
		"""
		get the currently displayed x-axis of raw plot
		"""
		theMin, theMax = self.rawPlot._get_x_axes()
		print('AnalysisApp._get_xaxis() current x axes is:', theMin, theMax)
		return theMin, theMax
		
	def check_Callback(self, name, var):
		print("=== AnalysisApp.check_Callback() name:", name, "var:", var.get())
		onoff = var.get()
		
		if name == 'showClips':
			if onoff:
				self.setStatus('Turning clips on')
				#todo: need to get x-axis range of raw data plot
				theMin, theMax = self._get_xaxis()
				numDisplayedClips = self.clipsPlot.plotClips_updateSelection(self.ba, xMin=theMin, xMax=theMax)
				self.numClipsLabel['text'] = 'Number of spike clips: ' + str(numDisplayedClips) # todo: this is case where I want signalling infrastructure to update interface
				self.setStatus()
			else:
				self.setStatus('Turning clips off')
				numDisplayedClips = self.clipsPlot.plotClips_updateSelection(self.ba, xMin=0, xMax=0)
				self.numClipsLabel['text'] = 'Number of spike clips: ' + str(numDisplayedClips) # todo: this is case where I want signalling infrastructure to update interface
				self.setStatus()
		elif name == 'autoAnalysisCheckbox':
			self.configDict['autoDetect'] = onoff
		else:
			self.rawPlot.plotStat(name, onoff)

	def detectSpikes(self):
		if self.ba is None:
			self.setStatus('Please load an abf file')
			return False

		print('AnalysisApp.detectSpikes()')
		self.setStatus('Detecting Spikes')

		dVthresholdPos = int(self.thresholdSpinbox.get())
		minSpikeVm = int(self.minSpikeVmSpinbox.get())
		medianFilter = int(self.filterSpinbox.get())
		plotEveryPoint = int(self.plotEverySpinbox.get()) # used in plot, not in detection
		halfWidths = self.halfWidthEntry.get()
		startSeconds = int(self.startSecondsSpinbox.get())
		stopSeconds = self.stopSecondsSpinbox.get() # can be 'inf'
		if stopSeconds in ('Inf', 'inf'):
			stopSeconds = max(self.ba.abf.sweepX)
		else:
			stopSeconds = int(stopSeconds)
		#theSweep = int(self.sweepVar.get())

		'''
		print('   dVthresholdPos:', dVthresholdPos)
		print('   minSpikeVm:', minSpikeVm)
		print('   medianFilter:', medianFilter)
		print('   halfWidths:', halfWidths)
		print('   startSeconds:', startSeconds)
		print('   stopSeconds:', stopSeconds)
		#print('   theSweep:', theSweep)
		'''
		
		# assuming halfWidths is a well formed list of numbers
		halfWidthsList = halfWidths.split(',')
		try:
			halfWidthsInt = list(map(int, halfWidthsList))
		except:
			self.setStatus('Invalid half widths. Please enter comma delimeted integers like 10,50,90')
			return False
			
		# calls spikeDetect0()
		self.ba.spikeDetect(dVthresholdPos=dVthresholdPos, minSpikeVm=minSpikeVm, medianFilter=medianFilter, halfHeights=halfWidthsInt, startSeconds=startSeconds, stopSeconds=stopSeconds)

		# refresh number of spikes
		self.numSpikesLabel['text'] = 'Number of spikes detected: ' + str(self.ba.numSpikes)	
		# refresh number of detection errors
		self.numErrorsLabel['text'] = 'Number of spike errors: ' + str(self.ba.numSpikeErrors)
		
		self.setStatus()

		return True
		
	def loadFolder(self, path=''):
		if len(path) < 1:
			#self.configDict['lastFolder']
			path = tkinter.filedialog.askdirectory(initialdir=self.configDict['lastPath'])

		if not os.path.isdir(path):
			print('error: did not find path:', path)
			return

		
		statusStr = 'Loading folder "' + path + '"'
		self.setStatus(statusStr)
		print(statusStr)
		
		self.path = path
		self.configDict['lastPath'] = path

		self.fileList = bFileList.bFileList(path)
		self.fileListTree.populateFiles(self.fileList, doInit=True)

		# initialize with first video in path
		firstVideoPath = ''
		if len(self.fileList.videoFileList):
			firstVideoPath = self.fileList.videoFileList[0].dict['path']

		self.setStatus()

	def switchSweep(self, sweep):
		if self.ba is None:
			print('error: switchSweep() says please select a file')
			self.setStatus('Please select a file')
			return
		
		self.setStatus('Switching to sweep ' + str(sweep))
		
		sweepSet = self.ba.setSweep(sweep)

		self.numSpikesLabel['text'] = 'Number of spikes detected: None'	
		self.numErrorsLabel['text'] = 'Number of spike errors: None'

		if sweepSet:
			# abb 20190513, always calculate and display the derivative

			medianFilter = int(self.filterSpinbox.get())
			self.ba.getDerivative(medianFilter=medianFilter)

			if self.configDict['autoDetect']:
				self.detectSpikes()
			self.replotResults()
		else:
			print('error: AnalysisApp.switchSweep() was not able to change to sweep:', sweep)
			
	def switchFile(self, filePath):
		"""
		Switch interface to a different file
		Called by bFileTree.single_click()
		"""
		print('AnalysisApp.switchFile() filePath:', filePath)

		self.currentFilePath = filePath

		self.setStatus('Loading file ' + filePath)

		self.ba = bAnalysis(file=filePath)

		# default sweep popup to 0
		self.sweepChoices = [''] + self.ba.sweepList
		self.sweepVar.set('0')
		self.ba.setSweep(0)

		# update available options in sweeps popup menu
		self.sweepPopupMenu.set_menu(*self.sweepChoices)
		
		self.numSpikesLabel['text'] = 'Number of spikes detected: None'	
		self.numErrorsLabel['text'] = 'Number of spike errors: None'

		# abb, removed 20190513
		'''
		if self.configDict['autoDetect']:
			self.detectSpikes()
		self.replotResults()
		'''
		self.switchSweep(0)
		
	def replotResults(self):
		startTime = time.time()
		
		self.setStatus('Plotting Results')
		plotEveryPoint = int(self.plotEverySpinbox.get())
		
		# plot raw
		self.rawPlot.plotRaw(self.ba, plotEveryPoint=plotEveryPoint, doInit=True)
		
		# plot deriv
		self.derivPlot.plotDeriv(self.ba, plotEveryPoint=plotEveryPoint, doInit=True)

		# plot clips
		showClips = self.showClips.get()
		if showClips:
			numDisplayedClips = self.clipsPlot.plotClips_updateSelection(self.ba, xMin=None, xMax=None)
			self.numClipsLabel['text'] = 'Number of spike clips: ' + str(numDisplayedClips) # todo: this is case where I want signalling infrastructure to update interface
		
		# refresh all stat plots
		for i, analysis in enumerate(self.analysisList):
			onoff = self.varList[i].get()
			self.rawPlot.plotStat(analysis, onoff)

		# plot meta
		statName = 'AP Peak (mV)'
		self.metaPlot.plotMeta(self.ba, statName, doInit=True)

		if self.metaPlot3 is not None:
			yStat, item = self.meta3Tree_y._getTreeViewSelection('Stat')
			xStat, item = self.meta3Tree_x._getTreeViewSelection('Stat')
			self.metaPlot3.plotMeta3(xStat, yStat)

		self.setStatus()
	
		stopTime = time.time()
		print('AnalysisApp.replotResults() took', stopTime-startTime, 'seconds')
		
	def setXAxis_full(self):
		self.rawPlot.setFullAxis()
		self.derivPlot.setFullAxis()

		showClips = self.showClips.get()
		if showClips:
			numDisplayedClips = self.clipsPlot.plotClips_updateSelection(self.ba, xMin=None, xMax=None)
			self.numClipsLabel['text'] = 'Number of spike clips: ' + str(numDisplayedClips) # todo: this is case where I want signalling infrastructure to update interface

		self.metaPlot.plotMeta_updateSelection(self.ba, xMin=None, xMax=None)

		if self.metaPlot3 is not None:
			self.metaPlot3.plotMeta_updateSelection(self.ba, xMin=None, xMax=None)

	def setXAxis(self, theMin, theMax):
		self.rawPlot.setXAxis(theMin, theMax)
		self.derivPlot.setXAxis(theMin, theMax)

		showClips = self.showClips.get()
		if showClips:
			numDisplayedClips = self.clipsPlot.plotClips_updateSelection(self.ba, theMin, theMax)
			self.numClipsLabel['text'] = 'Number of spike clips: ' + str(numDisplayedClips) # todo: this is case where I want signalling infrastructure to update interface

		self.metaPlot.plotMeta_updateSelection(self.ba, theMin, theMax)
		if self.metaPlot3 is not None:
			self.metaPlot3.plotMeta_updateSelection(self.ba, theMin, theMax)

	def selectSpike(self, spikeNumber):
		print('AnalysisApp.selectSpike() spikeNumber:', spikeNumber)

		self.rawPlot.selectSpike(self.ba, spikeNumber)
		
		self.metaPlot.selectSpikeMeta(self.ba, spikeNumber)
		if self.metaPlot3 is not None:
			self.metaPlot3.selectSpikeMeta(self.ba, spikeNumber)
		else:
			print('warning: AnalysisApp did not select spike in self.metaPlot3')
						

	#################################################################################
	# preferences
	#################################################################################
	def preferencesLoad(self):
		if getattr(sys, 'frozen', False):
			# we are running in a bundle (frozen)
			bundle_dir = sys._MEIPASS
		else:
			# we are running in a normal Python environment
			bundle_dir = os.path.dirname(os.path.abspath(__file__))

		# load preferences
		self.optionsFile = os.path.join(bundle_dir, 'AnalysisApp.json')

		if os.path.isfile(self.optionsFile):
			print('	preferencesLoad() loading options file:', self.optionsFile)
			with open(self.optionsFile) as f:
				self.configDict = json.load(f)
		else:
			print('	preferencesLoad() using program provided default options')
			self.preferencesDefaults()

	def preferencesDefaults(self):
		self.configDict = collections.OrderedDict()

		self.configDict['autoDetect'] = True # FALSE DOES NOT WORK!!!! auto detect on file selection and/or sweep selection
		self.configDict['lastPath'] = 'data'
		self.configDict['windowGeometry'] = {}
		self.configDict['windowGeometry']['x'] = 100
		self.configDict['windowGeometry']['y'] = 100
		self.configDict['windowGeometry']['width'] = 2000
		self.configDict['windowGeometry']['height'] = 1200

		self.configDict['detection'] = {}
		self.configDict['detection']['dvdtThreshold'] = 100
		self.configDict['detection']['minSpikeVm'] = -20
		self.configDict['detection']['medianFilter'] = 5

		self.configDict['display'] = {}
		self.configDict['display']['plotEveryPoint'] = 10

	def preferencesSave(self):
		print('=== AnalysisApp.preferencesSave() file:', self.optionsFile)

		x = self.root.winfo_x()
		y = self.root.winfo_y()
		width = self.root.winfo_width()
		height = self.root.winfo_height()

		self.configDict['windowGeometry']['x'] = x
		self.configDict['windowGeometry']['y'] = x
		self.configDict['windowGeometry']['width'] = width
		self.configDict['windowGeometry']['height'] = height

		#
		# detection
		dvdtThreshold = int(self.thresholdSpinbox.get())
		self.configDict['detection']['dvdtThreshold'] = dvdtThreshold

		minSpikeVm = int(self.minSpikeVmSpinbox.get())
		self.configDict['detection']['minSpikeVm'] = minSpikeVm

		medianFilter = int(self.filterSpinbox.get())
		self.configDict['detection']['medianFilter'] = medianFilter

		#
		# display
		plotEveryPoint = int(self.plotEverySpinbox.get())
		self.configDict['display']['plotEveryPoint'] = plotEveryPoint

		#
		# save
		with open(self.optionsFile, 'w') as outfile:
			json.dump(self.configDict, outfile, indent=4, sort_keys=True)

	#################################################################################
	# cleanup on quit
	#################################################################################
	def onClose(self, event=None):
		print("VideoApp.onClose()")
		'''
		self.isRunning = False
		self.vs.stop()
		'''
		self.preferencesSave()
		self.root.quit()

	#################################################################################
	# meta window
	#################################################################################
	'''
	def button_Callback3(self, buttonName):
		print('AnalysisApp.button_Callback3() buttonName:', buttonName)

		if self.metaPlot3 is not None:
			self.metaPlot3.plotMeta(self.ba, buttonName, doInit=True)
	'''
	
	def buildMetaOptionsFrame3(self, container):

		'''
		statList = self.metaAnalysisList + self.metaAnalysisList2
		statList = ['Time (sec)'] + statList
		'''
		
		metaStatFrame = ttk.Frame(container, borderwidth=self.myBorderWidth, relief=self.myRelief)
		metaStatFrame.grid(row=0, column=0, sticky="nsew")

		metaStatFrame.grid_rowconfigure(0, weight=0)
		metaStatFrame.grid_rowconfigure(1, weight=1)
		metaStatFrame.grid_columnconfigure(0, weight=1)
		metaStatFrame.grid_columnconfigure(1, weight=1)
		metaStatFrame.grid_columnconfigure(2, weight=1)

		#
		# row 0 for some buttons
		row0 = ttk.Frame(metaStatFrame, borderwidth=self.myBorderWidth, relief=self.myRelief)
		row0.grid(row=0,column=0, sticky="nw")

		phasePlotButton = ttk.Button(row0, text='Phase Plot', command=lambda name='Phase Plot': self.button_Callback(name))
		phasePlotButton.grid(row=0, column=0, sticky="w")

		#
		# y
		self.meta3Tree_y = bTree.bMetaTree(metaStatFrame, self, statList=self.metaAnalysisList3, name='meta3Window')
		self.meta3Tree_y.grid(row=1,column=0, sticky="nsew")

		#
		# x
		self.meta3Tree_x = bTree.bMetaTree(metaStatFrame, self, statList=self.metaAnalysisList3, name='meta3Window')
		self.meta3Tree_x.grid(row=1,column=1, sticky="nsew")


		#
		# plot
		metaPlotFrame = ttk.Frame(metaStatFrame, borderwidth=self.myBorderWidth, relief=self.myRelief)
		metaPlotFrame.grid(row=1, column=2, sticky="nsew")
		
		self.metaPlot3 = bPlotFrame(metaPlotFrame, self, showToolbar=True, allowSpan=False)
	
		return self.metaPlot3

	def plotMeta3(self, name):
		if name == 'mainWindow':
			yStat, item = self.metaTree_y._getTreeViewSelection('Stat')
			print('AnalysisApp.plotMeta3() yStat:', yStat)
			xStat = 'Time (sec)'
			self.metaPlot.plotMeta3(xStat, yStat)
		elif name =='meta3Window':
			yStat, item = self.meta3Tree_y._getTreeViewSelection('Stat')
			xStat, item = self.meta3Tree_x._getTreeViewSelection('Stat')
			print('AnalysisApp.plotMeta3() yStat:', yStat, 'xStat:', xStat)
			self.metaPlot3.plotMeta3(xStat, yStat)
		
		
		
	def onClose3(self, event=None):
		print('onClose3()')
		self.metaWindow.destroy()
		self.metaWindow = None
		self.metaPlot3 = None
		
	def metaWindow3(self):
		if self.metaWindow is None:
			horizontalSashPos = 300

			self.metaWindow = tkinter.Toplevel(self.root)
			self.metaWindow.wm_title('Meta Analysis')

			#self.metaWindow.wm_protocol("WM_DELETE_WINDOW", self.onClose3)
			self.metaWindow.bind("<Escape>", self.escapeKey_callback)

			w=1500
			h = 1000
			x = 200
			y = 10
			self.metaWindow.geometry('%dx%d+%d+%d' % (w, h, x, y))

			self.metaWindow.grid_rowconfigure(0, weight=1)
			self.metaWindow.grid_columnconfigure(0, weight=1)

			self.metaPlot3 = self.buildMetaOptionsFrame3(self.metaWindow)
		else:
			print('meta window 3 is already open?')

	#################################################################################
	# save results (e.g. report)
	#################################################################################
	def saveReport(self, theMin, theMax):
		"""
		save a spike report for detected spikes between theMin (sec) and theMax (sec)
		"""
		
		filePath, fileName = os.path.split(os.path.abspath(self.currentFilePath))
		fileBaseName, extension = os.path.splitext(fileName)
		excelFilePath = os.path.join(filePath, fileBaseName + '.xlsx')
		
		#print('AnalysisApp.report() saving', excelFilePath)
		print('Asking user for file name to save...')

		#savefile will be full path to user specified file
		savefile = asksaveasfilename(filetypes=(("Excel files", "*.xlsx"),
									("All files", "*.*") ),
									initialdir=filePath,
									initialfile=fileBaseName + '.xlsx')			   
														 
		# always grab a df to the entire analysis (not sure what I will do with this)
		#df = self.ba.report() # report() is my own 'bob' verbiage

		if savefile:
			print('Saving user specified .xlsx file:', savefile)
			excelFilePath = savefile
			writer = pd.ExcelWriter(excelFilePath, engine='xlsxwriter')
	
			#
			# cardiac style analysis to sheet 'cardiac'
			cardiac_df = self.ba.report2(theMin, theMax) # report2 is more 'cardiac'

			#
			# header sheet
			headerDict = collections.OrderedDict()
			headerDict['file'] = [self.ba.file]
			headerDict['Date Analyzed'] = [self.ba.dateAnalyzed]
			headerDict['dV/dt Threshold'] = [self.ba.dVthreshold]
			headerDict['Vm Threshold (mV)'] = [self.ba.minSpikeVm]
			headerDict['Median Filter (pnts)'] = [self.ba.medianFilter]
			headerDict['Analysis Start (sec)'] = [self.ba.startSeconds]
			headerDict['Analysis Stop (sec)'] = [self.ba.stopSeconds]
			headerDict['Sweep Number'] = [self.ba.currentSweep]
			headerDict['Number of Sweeps'] = [self.ba.numSweeps]
			headerDict['Export Start (sec)'] = [theMin] # on export, x-axis of raw plot will be ouput
			headerDict['Export Stop (sec)'] = [theMax] # on export, x-axis of raw plot will be ouput
			headerDict['stats'] = []
			
			for idx, col in enumerate(cardiac_df):
				headerDict[col] = []
				
			# mean
			theMean = cardiac_df.mean() # skipna default is True
			theMean['errors'] = ''
			# sd
			theSD = cardiac_df.std() # skipna default is True
			theSD['errors'] = ''
			#se
			theSE = cardiac_df.sem() # skipna default is True
			theSE['errors'] = ''
			#n
			theN = cardiac_df.count() # skipna default is True
			theN['errors'] = ''

			statCols = ['mean', 'sd', 'se', 'n']
			for j, stat in enumerate(statCols):
				if j == 0:
					pass
				else:
					headerDict['file'].append('')
					headerDict['Date Analyzed'].append('')
					headerDict['dV/dt Threshold'].append('')
					headerDict['Vm Threshold (mV)'].append('')
					headerDict['Median Filter (pnts)'].append('')
					headerDict['Analysis Start (sec)'].append('')
					headerDict['Analysis Stop (sec)'].append('')
					headerDict['Sweep Number'].append('')
					headerDict['Number of Sweeps'].append('')
					headerDict['Export Start (sec)'].append('')
					headerDict['Export Stop (sec)'].append('')
					
				# a dictionary key for each stat
				headerDict['stats'].append(stat)
				for idx, col in enumerate(cardiac_df):
					#headerDict[col].append('')
					if stat == 'mean':
						headerDict[col].append(theMean[col])
					elif stat == 'sd':
						headerDict[col].append(theSD[col])
					elif stat == 'se':
						headerDict[col].append(theSE[col])
					elif stat == 'n':
						headerDict[col].append(theN[col])
			
			
			# dict to pandas dataframe
			df = pd.DataFrame(headerDict).T
			# pandas dataframe to excel sheet 'header'
			df.to_excel(writer, sheet_name='summary')
			
			# set the column widths in excel sheet 'cardiac'
			columnWidth = 25
			worksheet = writer.sheets['summary']  # pull worksheet object
			for idx, col in enumerate(df):  # loop through all columns
				worksheet.set_column(idx, idx, columnWidth)  # set column width

			#
			# 'cardiac' sheet
			cardiac_df.to_excel(writer, sheet_name='cardiac')

			# set the column widths in excel sheet 'cardiac'
			columnWidth = 20
			worksheet = writer.sheets['cardiac']  # pull worksheet object
			for idx, col in enumerate(cardiac_df):  # loop through all columns
				worksheet.set_column(idx, idx, columnWidth)  # set column width

	
			#
			# entire (verbose) analysis to sheet 'bob'
			#df.to_excel(writer, sheet_name='bob')

			#
			# mean spike clip
			df = pd.DataFrame(self.clipsPlot.meanClip)
			df.to_excel(writer, sheet_name='Avg Spike')
	
			writer.save()
	
			#
			# always save a text file
			textFileBaseName, tmpExtension = os.path.splitext(savefile)
			textFilePath = os.path.join(filePath, textFileBaseName + '.txt')
			print('Saving .txt file:', textFilePath)
			df = self.ba.report(theMin, theMax)
			df.to_csv(textFilePath, sep=',', index_label='index', mode='w')

			self.setStatus('Saved ' + excelFilePath)
		else:
			print('Save aborted by user')

if __name__ == '__main__':

	print('starting AnalysisApp __main__')

	aa = AnalysisApp()

	print('ending AnalysisApp __main__')
