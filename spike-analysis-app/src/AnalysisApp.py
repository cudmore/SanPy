# Author: Robert Cudmore
# Date: 20190312

import sys, os, json

import numpy as np
import pandas as pd

import tkinter
from tkinter import ttk
from tkinter import filedialog

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
__version__ = '20190316'

#####################################################################################
class AnalysisApp:

	def __init__(self, path=None):

		self.loadPreferences()

		self.root = tkinter.Tk()
		self.root.title('Analysis App')

		self.root.wm_protocol("WM_DELETE_WINDOW", self.onClose)
		self.root.bind('<Command-q>', self.onClose)
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

		self.analysisList = ['threshold', 'peak', 'preMin', 'postMin', 'preLinearFit', 'preSpike_dvdt_max', 'postSpike_dvdt_min', 'halfWidth']
		self.metaAnalysisList = self.analysisList + ['isi (sec)', 'Phase Plot']

		self.metaAnalysisList2 = ['AP Peak (mV)',
								'MDP (mV)',
								'Take Off Potential (mV)',
								'Cycle Length (sec)',
								'Max Upstroke (dV/dt)',
								'Max Repolarization (dV/dt)',
								'AP Duration (sec)',
								'Diastolic Duration (sec)',
								'Early Diastolic Depolarization Rate (slope of Vm)',
								'Early Diastolic Duration (sec)',
								'Late Diastolic Duration (sec)']

		#self.buildInterface2()
		self.buildInterface3()

		self.myMenus = bMenus.bMenus(self)

		#self.metaWindow()

		if path is not None:
			self.loadFolder(path=path)

		# this will not return until we quit
		self.root.mainloop()

	def setStatus(self, str='Idle'):
		print('AnalysisApp.setStatus() str:', str)
		#self.statusLabel['text'] = 'Status: ', str
		self.statusLabel.configure(text='Status: ' + str)
		if str == 'Idle':
			self.statusLabel['foreground'] = 'black'
		else:
			self.statusLabel['foreground'] = 'red'
		# force tkinter to update
		#self.statusLabel.update_idletasks()
		self.statusLabel.update()

	def buildDetectionFrame(self, container):
		#
		# detection frame
		detection_frame = ttk.Frame(container, borderwidth=self.myBorderWidth, relief="sunken")

		row = 0

		detectButton = ttk.Button(detection_frame, text='Detect Spikes', command=lambda name='detectButton': self.button_Callback(name))
		detectButton.grid(row=row, column=0, sticky="w")

		# threshold
		labelDir = ttk.Label(detection_frame, text='dV/dt Threshold')
		labelDir.grid(row=row, column=1, sticky="w")

		dvdtThreshold = self.configDict['detection']['dvdtThreshold']
		self.thresholdSpinbox = ttk.Spinbox(detection_frame, from_=0, to=1000, width=5)
		self.thresholdSpinbox.insert(0,dvdtThreshold) # default is 100
		self.thresholdSpinbox.grid(row=row, column=2, sticky="w")

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

		# save spike report button
		reportButton = ttk.Button(detection_frame, text='Save Spike Report', command=lambda name='reportButton': self.button_Callback(name))
		reportButton.grid(row=row, column=0, sticky="w")

		return detection_frame

	def buildGlobalOptionsFrame(self, container):
		plotOptionsFrame = ttk.Frame(container, borderwidth=self.myBorderWidth, relief="sunken")


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
		
	def buildPlotOptionsFrame(self, container):
		#
		# plot options frame (checkboxes)
		plotOptionsFrame = ttk.Frame(container, borderwidth=self.myBorderWidth, relief="sunken")


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

		row = 1

		# plot checkboxes
		#self.analysisList = ['threshold', 'peak', 'preMin', 'postMin', 'preLinearFit', 'preSpike_dvdt_max', 'postSpike_dvdt_min', 'halfWidth']
		self.varList = []
		self.checkList = []
		myStyle = ttk.Style()
		for i, analysisItem in enumerate(self.analysisList):
			styleStr = analysisItem + '.TCheckbutton'
			foreground = 'black'
			if analysisItem == 'peak':
				foreground = 'red2'
			if analysisItem == 'preMin':
				foreground = 'red2'
			if analysisItem == 'postMin':
				foreground = 'green2'
			if analysisItem == 'preLinearFit':
				foreground = 'blue'
			if analysisItem == 'preSpike_dvdt_max':
				foreground = 'yellow3'
			if analysisItem == 'postSpike_dvdt_min':
				foreground = 'yellow3'
			if analysisItem == 'halfWidth':
				foreground = 'blue'
			myStyle.configure(styleStr, foreground=foreground)

			var = tkinter.BooleanVar(value=False)
			self.varList.append(var)
			check = ttk.Checkbutton(plotOptionsFrame, text=analysisItem, var=var, style=styleStr, command=lambda name=analysisItem, var=var: self.check_Callback(name, var))
			check.grid(row=row+i, column=0, sticky="w")
			self.checkList.append(check)

		return plotOptionsFrame

	def buildClipsOptionsFrame(self, container):
		metaPlotFrame = ttk.Frame(container, borderwidth=self.myBorderWidth, relief="sunken")
		return metaPlotFrame

	def buildMetaOptionsFrame(self, container):
		#
		# meta plot frame
		metaPlotFrame = ttk.Frame(container, borderwidth=self.myBorderWidth, relief="sunken")
		#metaPlotFrame.grid(row=0, column=0, sticky="nsew")

		row = 0
		col = 0
		for i, analysisItem in enumerate(self.metaAnalysisList):
			button = ttk.Button(metaPlotFrame, text=analysisItem, command=lambda name=analysisItem+'_button': self.button_Callback(name))
			button.grid(row=row+i, column=col, sticky="w")

		row = 0
		col = 1
		for i, analysisItem in enumerate(self.metaAnalysisList2):
			button = ttk.Button(metaPlotFrame, text=analysisItem, command=lambda name=analysisItem: self.button_Callback2(name))
			button.grid(row=row+i, column=col, sticky="w")

		return metaPlotFrame

	def buildInterface3(self):
		horizontalSashPos = 400

		self.root.grid_rowconfigure(0, weight=1)
		self.root.grid_columnconfigure(0, weight=1)

		self.vPane = ttk.PanedWindow(self.root, orient="vertical")
		self.vPane.grid(row=0, column=0, sticky="nsew")

		#
		# status frame, see self.setStatus()
		status_frame = ttk.Frame(self.vPane, borderwidth=self.myBorderWidth, relief="sunken")
		self.vPane.add(status_frame)

		self.statusLabel = ttk.Label(status_frame)
		self.statusLabel.grid(row=0, column=0, sticky="w")
		self.setStatus('Building Interface')

		#
		# horizontal pane for file list and global plot options
		'''
		hPane_top = ttk.PanedWindow(self.vPane, orient="horizontal")
		self.vPane.add(hPane_top)
		'''
		
		#
		# file list frame
		fileList_frame = ttk.Frame(self.vPane, borderwidth=self.myBorderWidth, relief="sunken")
		self.vPane.add(fileList_frame)
		'''
		fileList_frame = ttk.Frame(hPane_top, borderwidth=self.myBorderWidth, relief="sunken")
		hPane_top.add(fileList_frame)
		'''
		
		'''
		fileListFrameLabel = ttk.Label(fileList_frame)
		fileListFrameLabel.grid(row=0, column=0, sticky="w")
		fileListFrameLabel.configure(text='File List')
		'''
		
		self.fileListTree = bTree.bFileTree(fileList_frame, self, videoFileList='')
		self.fileListTree.grid(row=1,column=0, sticky="nsew")

		'''
		globalOptionsFrame = self.buildGlobalOptionsFrame(hPane_top)
		hPane_top.add(globalOptionsFrame)

		hPane_top.sashpos(0, 500)
		'''

		#
		# horizontal pane for detection options and dv/dt plot
		hPane_detection = ttk.PanedWindow(self.vPane, orient="horizontal")
		#self.vPane.grid(row=0, column=0, sticky="nsew")
		self.vPane.add(hPane_detection)

		detectionFrame = self.buildDetectionFrame(hPane_detection)
		hPane_detection.add(detectionFrame)

		# dvdt plot
		derivFrame = ttk.Frame(hPane_detection, borderwidth=self.myBorderWidth, relief="sunken")
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
		rawFrame = ttk.Frame(hPane_plot, borderwidth=self.myBorderWidth, relief="sunken")
		hPane_plot.add(rawFrame)

		self.rawPlot = bPlotFrame(rawFrame, self, showToolbar=True, analysisList=self.analysisList)

		hPane_plot.sashpos(0, horizontalSashPos)

		#
		# horizontal pane for spike clips (only one column
		# spike clips
		hPane_clips = ttk.PanedWindow(self.vPane, orient="horizontal")
		self.vPane.add(hPane_clips)

		spikeClipsOptionsFrame = self.buildClipsOptionsFrame(hPane_clips)
		hPane_clips.add(spikeClipsOptionsFrame)

		# spike clips plot
		spikeClipsFrame = ttk.Frame(hPane_clips, borderwidth=self.myBorderWidth, relief="sunken")
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
		metaAnalysisFrame = ttk.Frame(hPane_meta, borderwidth=self.myBorderWidth, relief="sunken")
		hPane_meta.add(metaAnalysisFrame)

		self.metaPlot = bPlotFrame(metaAnalysisFrame, self, showToolbar=False, allowSpan=False)

		hPane_meta.sashpos(0, horizontalSashPos)

	def metaWindow(self):
		horizontalSashPos = 300

		newWindow = tkinter.Toplevel(self.root)
		newWindow.wm_title('Meta Analysis')

		w=500
		h = 500
		x = 200
		y = 200
		newWindow.geometry('%dx%d+%d+%d' % (w, h, x, y))

		newWindow.grid_rowconfigure(0, weight=1)
		newWindow.grid_columnconfigure(0, weight=1)

		myPadding = 5

		hPane_meta = ttk.PanedWindow(newWindow, orient="horizontal")
		hPane_meta.grid(row=0, column=0, sticky="nsew")

		metaFrame = self.buildMetaOptionsFrame(hPane_meta)
		# DO NOT GRID A FRAME WHEN PLACED INTO PANNED WINDOW
		#metaFrame.grid(row=1, column=0, sticky="nsew")
		hPane_meta.add(metaFrame)

		# meta plot
		metaAnalysisFrame = ttk.Frame(hPane_meta, borderwidth=self.myBorderWidth, relief="sunken")
		# DO NOT GRID A FRAME WHEN PLACED INTO PANNED WINDOW
		#metaFrame.grid(row=1, column=0, sticky="nsew")
		hPane_meta.add(metaAnalysisFrame)

		metaPlot = bPlotFrame(metaAnalysisFrame, self, showToolbar=False, allowSpan=False)

		hPane_meta.sashpos(0, horizontalSashPos)

	def spinBox_Callback(self, name):
		print('spinBox_Callback:', name)
		plotEveryPoint = int(self.plotEverySpinbox.get())
		print('plotEveryPoint:', plotEveryPoint)
		self.rawPlot.plotRaw(self.ba, plotEveryPoint=plotEveryPoint)
		self.derivPlot.plotDeriv(self.ba, plotEveryPoint=plotEveryPoint)
		return True

	def button_Callback2(self, buttonName):
		print('button_Callback2() buttonName:', buttonName)

		self.metaPlot.plotMeta(self.ba, buttonName, doInit=True)

	def button_Callback(self, buttonName):
		print('AnalysisApp.button_Callback() buttonName:', buttonName)
		#print('   self.thresholdSpinbox:', self.thresholdSpinbox.get())
		#print('   self.filterSpinbox:', self.filterSpinbox.get())

		if buttonName == 'detectButton':
			self.detectSpikes()
			'''
			self.setStatus('Detecting Spikes')

			dVthresholdPos = int(self.thresholdSpinbox.get())
			medianFilter = int(self.filterSpinbox.get())
			plotEveryPoint = int(self.plotEverySpinbox.get())

			# calls spike detect
			self.derivPlot.plotDeriv(self.ba, dVthresholdPos=dVthresholdPos, medianFilter=medianFilter)

			self.rawPlot.plotRaw(self.ba, plotEveryPoint=plotEveryPoint)

			# refresh all stat plots
			for i, analysis in enumerate(self.analysisList):
				onoff = self.varList[i].get()
				self.rawPlot.plotStat(analysis, onoff)

			self.setStatus()
			'''

		if buttonName == 'fullAxisButton':
			self.setXAxis_full()
			#self.rawPlot.setFullAxis()
			#self.derivPlot.setFullAxis()

		if buttonName == 'reportButton':
			self.report()

		#
		# respond to meta plot
		if buttonName == 'threshold_button':
			statName = 'threshold'
			self.metaPlot.plotMeta(self.ba, statName, doInit=True)
		if buttonName == 'peak_button':
			statName = 'peak'
			self.metaPlot.plotMeta(self.ba, statName, doInit=True)
		if buttonName == 'preMin_button':
			statName = 'preMin'
			self.metaPlot.plotMeta(self.ba, statName, doInit=True)
		if buttonName == 'postMin_button':
			statName = 'postMin'
			self.metaPlot.plotMeta(self.ba, statName, doInit=True)
		if buttonName == 'preLinearFit_button':
			print('   not implemented')
		if buttonName == 'preSpike_dvdt_max_button':
			statName = 'preSpike_dvdt_max'
			self.metaPlot.plotMeta(self.ba, statName, doInit=True)
		if buttonName == 'postSpike_dvdt_min_button':
			statName = 'postSpike_dvdt_min'
			self.metaPlot.plotMeta(self.ba, statName, doInit=True)
		if buttonName == 'isi (sec)_button':
			statName = 'isi (sec)'
			self.metaPlot.plotMeta(self.ba, statName, doInit=True)
		if buttonName == 'Phase Plot_button':
			statName = 'Phase Plot'
			self.metaPlot.plotMeta(self.ba, statName, doInit=True)

	def check_Callback(self, name, var):
		print("check_Callback() name:", name, "var:", var.get())
		onoff = var.get()
		self.rawPlot.plotStat(name, onoff)

	def detectSpikes(self):
		if self.ba is None:
			self.setStatus('Please load an abf file')
			return False

		print('AnalysisApp.detectSpikes()')
		self.setStatus('Detecting Spikes')

		plotEveryPoint = int(self.plotEverySpinbox.get()) # used in plot, not in detection
		startSeconds = int(self.startSecondsSpinbox.get())
		stopSeconds = self.stopSecondsSpinbox.get() # can be 'inf'
		if stopSeconds in ('Inf', 'inf'):
			stopSeconds = max(self.ba.abf.sweepX)
		else:
			stopSeconds = int(stopSeconds)
		dVthresholdPos = int(self.thresholdSpinbox.get())
		medianFilter = int(self.filterSpinbox.get())

		print('   startSeconds:', startSeconds)
		print('   stopSeconds:', stopSeconds)
		print('   dVthresholdPos:', dVthresholdPos)
		print('   medianFilter:', medianFilter)

		#self.ba.spikeDetect0(dVthresholdPos=dVthresholdPos, medianFilter=medianFilter, startSeconds=startSeconds, stopSeconds=stopSeconds)
		self.ba.spikeDetect(dVthresholdPos=dVthresholdPos, medianFilter=medianFilter, startSeconds=startSeconds, stopSeconds=stopSeconds) # calls spikeDetect0()

		# refresh raw
		self.rawPlot.plotRaw(self.ba, plotEveryPoint=plotEveryPoint)

		# refresh deriv
		self.derivPlot.plotDeriv(self.ba, plotEveryPoint=plotEveryPoint)

		# refresh deriv
		self.clipsPlot.plotClips(self.ba, plotEveryPoint=plotEveryPoint)

		# refresh all stat plots
		for i, analysis in enumerate(self.analysisList):
			onoff = self.varList[i].get()
			self.rawPlot.plotStat(analysis, onoff)

		# refresh meta plot
		statName = 'peak'
		self.metaPlot.plotMeta(self.ba, statName, doInit=True)

		self.setStatus()

	def loadFolder(self, path=''):
		if len(path) < 1:
			path = tkinter.filedialog.askdirectory()

		if not os.path.isdir(path):
			print('error: did not find path:', path)
			return

		self.setStatus('Loading folder')

		self.path = path
		self.configDict['lastPath'] = path

		self.fileList = bFileList.bFileList(path)
		self.fileListTree.populateVideoFiles(self.fileList, doInit=True)

		# initialize with first video in path
		firstVideoPath = ''
		if len(self.fileList.videoFileList):
			firstVideoPath = self.fileList.videoFileList[0].dict['path']

		self.setStatus()

	def switchvideo(self, videoPath, paused=False, gotoFrame=None):
		print('=== VideoApp.switchvideo() videoPath:', videoPath, 'paused:', paused, 'gotoFrame:', gotoFrame)

		print('   videoPath:', videoPath)

		self.currentFilePath = videoPath

		self.setStatus('Loading file ' + videoPath)
		self.ba = bAnalysis(file=videoPath)

		self.detectSpikes()

		self.setStatus('Plotting Results')
		plotEveryPoint = int(self.plotEverySpinbox.get())
		self.rawPlot.plotRaw(self.ba, plotEveryPoint=plotEveryPoint, doInit=True)
		self.derivPlot.plotDeriv(self.ba, plotEveryPoint=plotEveryPoint, doInit=True)

		# just for testing
		statName = 'peak'
		self.metaPlot.plotMeta(self.ba, statName, doInit=True)

		self.clipsPlot.plotClips_updateSelection(self.ba, xMin=None, xMax=None)

		self.setStatus()

	def setXAxis_full(self):
		self.rawPlot.setFullAxis()
		self.derivPlot.setFullAxis()

		self.clipsPlot.plotClips_updateSelection(self.ba, xMin=None, xMax=None)
		self.metaPlot.plotMeta_updateSelection(self.ba, xMin=None, xMax=None)

	def setXAxis(self, theMin, theMax):
		self.rawPlot.setXAxis(theMin, theMax)
		self.derivPlot.setXAxis(theMin, theMax)

		self.clipsPlot.plotClips_updateSelection(self.ba, theMin, theMax)
		self.metaPlot.plotMeta_updateSelection(self.ba, theMin, theMax)

	def selectSpike(self, spikeNumber):
		print('AnalysisApp.selectSpike() spikeNumber:', spikeNumber)
		self.rawPlot.selectSpike(self.ba, spikeNumber)

	def report(self):
		filePath, fileName = os.path.split(os.path.abspath(self.currentFilePath))
		fileBaseName, extension = os.path.splitext(fileName)
		excelFilePath = os.path.join(filePath, fileBaseName + '.xlsx')
		print('AnalysisApp.report() saving', excelFilePath)

		writer = pd.ExcelWriter(excelFilePath, engine='xlsxwriter')

		df2 = self.ba.report2() # report2 is more 'cardiac'
		df2.to_excel(writer, sheet_name='Sheet1')

		df = self.ba.report() # report() is my own verbiage
		df.to_excel(writer, sheet_name='Sheet2')

		df = pd.DataFrame(self.clipsPlot.meanClip)
		df.to_excel(writer, sheet_name='Avg Spike')
		
		writer.save()

		self.setStatus('Saved ' + excelFilePath)

		#
		# save a text file
		textFilePath = os.path.join(filePath, fileBaseName + '.txt')
		df.to_csv(textFilePath, sep=',', index_label='index', mode='a')

		'''
		# display all stats in a window
		df_col = df.columns.values # df_col is numpy.ndarray
		#df_col = np.insert(df_col, 0, 'index')
		df_col = tuple(df_col)
		print('df_col:', df_col)

		# create a window
		newWindow = tkinter.Toplevel(self.root)
		newWindow.wm_title('Spike Report')

		newWindow.grid_rowconfigure(0, weight=1)
		newWindow.grid_columnconfigure(0, weight=1)

		myPadding = 5

		# self.treeview = ttk.Treeview(self, selectmode="browse", show=['headings'], *args, **kwargs)
		tree = ttk.Treeview(newWindow, selectmode="browse", show=['headings'])
		tree.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)

		myScrollbar = ttk.Scrollbar(newWindow, orient="vertical", command = tree.yview)
		myScrollbar.grid(row=0, column=0, sticky='nse', padx=myPadding, pady=myPadding)
		tree.configure(yscrollcommand=myScrollbar.set)

		myScrollbar_h = ttk.Scrollbar(newWindow, orient="horizontal", command = tree.xview)
		myScrollbar_h.grid(row=0, column=0, sticky='nse', padx=myPadding, pady=myPadding)
		tree.configure(xscrollcommand=myScrollbar_h.set)

		tree["columns"] = df_col # rhs is tuple
		for idx, column in enumerate(df_col):
			tree.column(column, width=10)
			#tree.heading(column, text=column, command=lambda c=column: self.sort_column(c, False))
			tree.heading(column, text=column)

		for index, row in df.iterrows():
			#print('index:', index, 'row:', row.values)
			rowTuple = tuple(row.values)
			position = "end"
			tree.insert("" , position, text=str(index+1), values=rowTuple)
		'''

	#################################################################################
	# preferences
	#################################################################################
	def loadPreferences(self):
		if getattr(sys, 'frozen', False):
			# we are running in a bundle (frozen)
			bundle_dir = sys._MEIPASS
		else:
			# we are running in a normal Python environment
			bundle_dir = os.path.dirname(os.path.abspath(__file__))

		# load preferences
		self.optionsFile = os.path.join(bundle_dir, 'AnalysisApp.json')

		if os.path.isfile(self.optionsFile):
			print('    loading options file:', self.optionsFile)
			with open(self.optionsFile) as f:
				self.configDict = json.load(f)
		else:
			print('    using program provided default options')
			self.preferencesDefaults()

	def preferencesDefaults(self):
		self.configDict = {}

		self.configDict['windowGeometry'] = {}
		self.configDict['windowGeometry']['x'] = 100
		self.configDict['windowGeometry']['y'] = 100
		self.configDict['windowGeometry']['width'] = 1000
		self.configDict['windowGeometry']['height'] = 700

		self.configDict['detection'] = {}
		self.configDict['detection']['dvdtThreshold'] = 100
		self.configDict['detection']['medianFilter'] = 5

		self.configDict['display'] = {}
		self.configDict['display']['plotEveryPoint'] = 10

	def savePreferences(self):
		print('=== AnalysisApp.savePreferences() file:', self.optionsFile)

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
		self.savePreferences()
		self.root.quit()

if __name__ == '__main__':

	print('starting AnalysisApp __main__')

	aa = AnalysisApp(path='/Users/cudmore/Sites/bAnalysis/data')

	print('ending AnalysisApp __main__')
