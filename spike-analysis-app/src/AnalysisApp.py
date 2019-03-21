# Author: Robert Cudmore
# Date: 20190312

import sys, os, json

import numpy as np

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
		
		self.myPadding = 10
		self.myBorderWidth = 5
		
		self.buildInterface2()
		
		self.myMenus = bMenus.bMenus(self)

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
		
	def buildInterface_Left(self):
		"""
		Populate left vertical frame with user interface controls.
		Including: tree view, buttons, spin boxes, checkboxes
		"""
		
		# width=600 will set the initial width
		self.leftVPane = ttk.PanedWindow(self.hPane, orient="vertical", width=600)
		
		#
		# status frame, see self.setStatus()
		status_frame = ttk.Frame(self.leftVPane, borderwidth=self.myBorderWidth, relief="sunken")
		self.leftVPane.add(status_frame)

		self.statusLabel = ttk.Label(status_frame)
		self.statusLabel.grid(row=0, column=0, sticky="w")
		self.setStatus('Building Interface')

		#
		# file list frame
		fileList_frame = ttk.Frame(self.leftVPane, borderwidth=self.myBorderWidth, relief="sunken")
		self.leftVPane.add(fileList_frame)

		fileListFrameLabel = ttk.Label(fileList_frame)
		fileListFrameLabel.grid(row=0, column=0, sticky="w")
		fileListFrameLabel.configure(text='File List')

		self.fileListTree = bTree.bFileTree(fileList_frame, self, videoFileList='')
		self.fileListTree.grid(row=1,column=0, sticky="nsew")

		#
		# detection frame
		detection_frame = ttk.Frame(self.leftVPane, borderwidth=self.myBorderWidth, relief="sunken")
		self.leftVPane.add(detection_frame)

		detectionFrameLabel = ttk.Label(detection_frame)
		detectionFrameLabel.grid(row=0, column=0, sticky="w")
		detectionFrameLabel.configure(text='Spike Detection')

		row = 1
		
		detectButton = ttk.Button(detection_frame, text='Detect Spikes', command=lambda name='detectButton': self.button_Callback(name))
		detectButton.grid(row=row, column=0, sticky="w")
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

		# threshold
		labelDir = ttk.Label(detection_frame, text='dV/dt Threshold')
		labelDir.grid(row=row, column=0, sticky="w")

		dvdtThreshold = self.configDict['detection']['dvdtThreshold']
		self.thresholdSpinbox = ttk.Spinbox(detection_frame, from_=0, to=1000, width=5)
		self.thresholdSpinbox.insert(0,dvdtThreshold) # default is 100
		self.thresholdSpinbox.grid(row=row, column=1, sticky="w")
		
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

		#
		# plot options frame (checkboxes)
		plotOptionsFrame = ttk.Frame(self.leftVPane, borderwidth=self.myBorderWidth, relief="sunken")
		self.leftVPane.add(plotOptionsFrame)

		
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
		self.analysisList = ['threshold', 'peak', 'preMin', 'postMin', 'preLinearFit', 'preSpike_dvdt_max', 'postSpike_dvdt_min', 'halfWidth']
		self.varList = []
		self.checkList = []
		for i, analysisItem in enumerate(self.analysisList):
			var = tkinter.BooleanVar(value=False)
			self.varList.append(var)
			check = ttk.Checkbutton(plotOptionsFrame, text=analysisItem, var=var, command=lambda name=analysisItem, var=var: self.check_Callback(name, var))
			#check['foreground'] = 'red'
			check.grid(row=row+i, column=0, sticky="w")
			self.checkList.append(check)

		#
		# meta plot frame
		metaPlotFrame = ttk.Frame(self.leftVPane, borderwidth=self.myBorderWidth, relief="sunken")
		self.leftVPane.add(metaPlotFrame)

		row = 0 
		for i, analysisItem in enumerate(self.analysisList):
			button = ttk.Button(metaPlotFrame, text=analysisItem, command=lambda name=analysisItem+'_button': self.button_Callback(name))
			button.grid(row=row+i, column=0, sticky="w") 
					
	def buildInterface_Right(self):
		#
		# populate right v pane with plots
		#
		self.rightVPane = ttk.PanedWindow(self.hPane, orient="vertical")

		# raw data
		rawFrame = ttk.Frame(self.rightVPane, borderwidth=self.myBorderWidth, relief="sunken")
		self.rightVPane.add(rawFrame)
		
		self.rawPlot = bPlotFrame(rawFrame, self, showToolbar=True, analysisList=self.analysisList, figHeight=3)
		
		# deriv data
		derivFrame = ttk.Frame(self.rightVPane, borderwidth=self.myBorderWidth, relief="sunken")
		self.rightVPane.add(derivFrame)
		
		self.derivPlot = bPlotFrame(derivFrame, self, showToolbar=False, analysisList=self.analysisList,figHeight=1)
		
		# spike clips
		spikeClipsFrame = ttk.Frame(self.rightVPane, borderwidth=self.myBorderWidth, relief="sunken")
		self.rightVPane.add(spikeClipsFrame)
		
		self.clipsPlot = bPlotFrame(spikeClipsFrame, self, showToolbar=False, analysisList=self.analysisList, figHeight=3, allowSpan=False)
		
		# meta analysis
		metaAnalysisFrame = ttk.Frame(self.rightVPane, borderwidth=self.myBorderWidth, relief="sunken")
		self.rightVPane.add(metaAnalysisFrame)
		
		self.metaPlot = bPlotFrame(metaAnalysisFrame, self, showToolbar=False, figHeight=3, allowSpan=False)
		
	def buildInterface2(self):
		self.root.grid_rowconfigure(0, weight=1)
		self.root.grid_columnconfigure(0, weight=1)

		self.hPane = ttk.PanedWindow(self.root, orient="horizontal")
		self.hPane.grid(row=0, column=0, sticky="nsew")

		self.buildInterface_Left() # for controls, creates self.leftVPane
		self.hPane.add(self.leftVPane)

		self.buildInterface_Right() # for plots, , creates self.rightVPane
		self.hPane.add(self.rightVPane)

		# finish
		self.setStatus('Idle')

	def spinBox_Callback(self, name):
		print('spinBox_Callback:', name)
		plotEveryPoint = int(self.plotEverySpinbox.get())
		print('plotEveryPoint:', plotEveryPoint)
		self.rawPlot.plotRaw(self.ba, plotEveryPoint=plotEveryPoint)
		self.derivPlot.plotDeriv(self.ba, plotEveryPoint=plotEveryPoint)
		return True
		
	def button_Callback(self, buttonName):
		print('button_Callback() buttonName:', buttonName)
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
			self.rawPlot.setFullAxis()
			self.derivPlot.setFullAxis()
			
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

	def check_Callback(self, name, var):
		print("check_Callback() name:", name, "var:", var.get())
		onoff = var.get()
		self.rawPlot.plotStat(name, onoff)
		
	def detectSpikes(self):
		if self.ba is None:
			self.setStatus('Please load an abf file')
			return False
			
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

		self.setStatus()
		
	def setXAxis(self, theMin, theMax):
		self.rawPlot.setXAxis(theMin, theMax)
		self.derivPlot.setXAxis(theMin, theMax)
		
		self.clipsPlot.plotClips_updateSelection(self.ba, theMin, theMax)
		
	def report(self):
		df = self.ba.report()

		filePath, fileName = os.path.split(os.path.abspath(self.currentFilePath))
		fileBaseName, extension = os.path.splitext(fileName)
		excelFilePath = os.path.join(filePath, fileBaseName + '.xlsx')
		print('AnalysisApp.report() saving', excelFilePath)
		df.to_excel(excelFilePath)
		self.setStatus('Saved ' + excelFilePath)

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
		self.configDict['display']['showEveryPoint'] = 10

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