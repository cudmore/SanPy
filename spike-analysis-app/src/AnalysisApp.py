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

		self.root = tkinter.Tk()
		self.root.title('Analysis App')
		
		self.root.wm_protocol("WM_DELETE_WINDOW", self.onClose)
		self.root.bind('<Command-q>', self.onClose)		
		# remove the default behavior of invoking the button with the space key
		self.root.unbind_class("Button", "<Key-space>")

		# position root window
		x = self.configDict['windowGeometry']['x'] #100 #self.configDict['appWindowGeometry_x']
		y = self.configDict['windowGeometry']['y'] #100 #self.configDict['appWindowGeometry_y']
		w = self.configDict['windowGeometry']['width'] #2000 #self.configDict['appWindowGeometry_w']
		h = self.configDict['windowGeometry']['height'] #1000# self.configDict['appWindowGeometry_h']
		self.root.geometry('%dx%d+%d+%d' % (w, h, x, y))

		self.currentFilePath = ''
		self.ba = None
		
		self.buildInterface()
		
		self.myMenus = bMenus.bMenus(self)

		if path is not None:
			self.loadFolder(path=path)
			
		# this will not return until we quit
		self.root.mainloop()

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
		
	def buildInterface(self):
		myPadding = 5
		myBorderWidth = 2

		self.lastResizeWidth = None
		self.lastResizeHeight = None
		
		self.root.grid_rowconfigure(0, weight=1)
		self.root.grid_columnconfigure(0, weight=1)

		#
		# vertical pane to hold everything
		self.vPane = ttk.PanedWindow(self.root, orient="vertical") #, showhandle=True)
		self.vPane.grid(row=0, column=0, sticky="nsew")

		#
		# status frame
		status_frame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		status_frame.grid(row=0, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		status_frame.grid_rowconfigure(0, weight=1)
		status_frame.grid_columnconfigure(0, weight=1)
		self.vPane.add(status_frame)

		# status, see self.setStatus()
		self.statusLabel = ttk.Label(status_frame)
		self.statusLabel.grid(row=0, column=0, sticky="w")
		self.setStatus('Idle')
		
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
		# detection params
		buttonFrame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		buttonFrame.grid(row=1, column=0, sticky="nw", padx=myPadding, pady=myPadding)
		self.vPane.add(buttonFrame)

		col = 0

		# detect button
		detectButton = ttk.Button(buttonFrame, text='Detect Spikes', command=lambda name='detectButton': self.button_Callback(name))
		detectButton.grid(row=0, column=col, sticky="w")
		col += 1
		
		# time range
		labelDir = ttk.Label(buttonFrame, text='From (Sec)')
		labelDir.grid(row=0, column=col, sticky="w")
		col += 1

		self.startSecondsSpinbox = ttk.Spinbox(buttonFrame, from_=0, to=1000)
		self.startSecondsSpinbox.insert(0,0) # default is 0
		self.startSecondsSpinbox.grid(row=0, column=col, sticky="w")
		col += 1

		labelDir = ttk.Label(buttonFrame, text='To (Sec)')
		labelDir.grid(row=0, column=col, sticky="w")
		col += 1

		self.stopSecondsSpinbox = ttk.Spinbox(buttonFrame, from_=0, to=1000)
		self.stopSecondsSpinbox.insert(0,float('inf')) # default is inf
		self.stopSecondsSpinbox.grid(row=0, column=col, sticky="w")
		col += 1

		# threshold
		labelDir = ttk.Label(buttonFrame, text='dV/dt Threshold')
		labelDir.grid(row=0, column=col, sticky="w")
		col += 1

		dvdtThreshold = self.configDict['detection']['dvdtThreshold']
		self.thresholdSpinbox = ttk.Spinbox(buttonFrame, from_=0, to=1000)
		self.thresholdSpinbox.insert(0,dvdtThreshold) # default is 100
		self.thresholdSpinbox.grid(row=0, column=col, sticky="w")
		col += 1
		
		# median filter
		labelDir = ttk.Label(buttonFrame, text='Median Filter (pnts)')
		labelDir.grid(row=0, column=col, sticky="w")
		col += 1

		medianFilter = self.configDict['detection']['medianFilter']
		print('type(medianFilter):', type(medianFilter))
		self.filterSpinbox = ttk.Spinbox(buttonFrame, from_=0, to=1000)
		self.filterSpinbox.insert(0,medianFilter) # default is 5
		self.filterSpinbox.grid(row=0, column=col, sticky="w")
		col += 1
		
		# report button
		reportButton = ttk.Button(buttonFrame, text='Save Spike Report', command=lambda name='reportButton': self.button_Callback(name))
		reportButton.grid(row=0, column=col, sticky="w")
		col += 1

		'''
		# status, see self.setStatus()
		self.statusLabel = ttk.Label(buttonFrame)
		self.statusLabel.grid(row=0, column=col, sticky="w")
		self.setStatus('Idle')
		col += 1
		'''
		
		#
		# plot options (checkboxes)
		plotOptionsFrame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		plotOptionsFrame.grid(row=1, column=0, sticky="nw", padx=myPadding, pady=myPadding)
		self.vPane.add(plotOptionsFrame)

		# reset axes button
		resetAxesButton = ttk.Button(plotOptionsFrame, text='Reset Axes', command=lambda name='fullAxisButton': self.button_Callback(name))
		resetAxesButton.grid(row=0, column=0, sticky="w")

		# plot a subset of points
		labelDir = ttk.Label(plotOptionsFrame, text='Plot Every (pnt)')
		labelDir.grid(row=0, column=1, sticky="w")

		plotEveryPoint = self.configDict['display']['plotEveryPoint']
		self.plotEverySpinbox = ttk.Spinbox(plotOptionsFrame, from_=1, to=1000, validate="focusout", validatecommand=lambda name='plotEverySpinbox': self.spinBox_Callback(name))
		self.plotEverySpinbox.insert(0,plotEveryPoint) # default is 10
		self.plotEverySpinbox.grid(row=0, column=2, sticky="w")

		numCols = 3
		
		# plot checkboxes
		self.analysisList = ['peak', 'preMin', 'postMin', 'preLinearFit', 'preSpike_dvdt_max', 'postSpike_dvdt_min', 'halfWidth']
		self.varList = []
		self.checkList = []
		for i, analysisItem in enumerate(self.analysisList):
			var = tkinter.BooleanVar(value=False)
			self.varList.append(var)
			check = ttk.Checkbutton(plotOptionsFrame, text=analysisItem, var=var, command=lambda name=analysisItem, var=var: self.check_Callback(name, var))
			#check['foreground'] = 'red'
			check.grid(row=0, column=i+numCols, sticky="w") # +2 for resetAxesButton
			self.checkList.append(check)
				
		#
		# raw data
		lower_frame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		lower_frame.grid(row=2, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		lower_frame.grid_rowconfigure(0, weight=1)
		lower_frame.grid_columnconfigure(0, weight=1)
		self.vPane.add(lower_frame)
		
		self.rawPlot = bPlotFrame(lower_frame, self, showToolbar=True, analysisList=self.analysisList, figHeight=3)
		#self.rawPlot.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		
		#
		# deriv data
		deriv_frame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		deriv_frame.grid(row=3, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		deriv_frame.grid_rowconfigure(0, weight=1)
		deriv_frame.grid_columnconfigure(0, weight=1)
		self.vPane.add(deriv_frame)
		
		self.derivPlot = bPlotFrame(deriv_frame, self, showToolbar=False, analysisList=self.analysisList,figHeight=1)
		#self.derivPlot.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		
		#
		# spike clips
		clips_frame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		clips_frame.grid(row=4, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		clips_frame.grid_rowconfigure(0, weight=1)
		clips_frame.grid_columnconfigure(0, weight=1)
		self.vPane.add(clips_frame)
		
		self.clipsPlot = bPlotFrame(clips_frame, self, showToolbar=False, analysisList=self.analysisList, figHeight=3, allowSpan=False)
		#self.clipsPlot.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		
		#
		# meta analysis
		meta_frame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		meta_frame.grid(row=5, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		meta_frame.grid_rowconfigure(0, weight=1)
		meta_frame.grid_columnconfigure(0, weight=1)
		self.vPane.add(meta_frame)
		
		self.metaPlot = bPlotFrame(meta_frame, self, showToolbar=False, figHeight=3, allowSpan=False)
		#self.clipsPlot.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		
	def spinBox_Callback(self, name):
		print('spinBox_Callback:', name)
		plotEveryPoint = int(self.plotEverySpinbox.get())
		print('plotEveryPoint:', plotEveryPoint)
		self.rawPlot.plotRaw(self.ba, plotEveryPoint=plotEveryPoint)
		self.derivPlot.plotDeriv(self.ba, plotEveryPoint=plotEveryPoint)
		return True
		
	def button_Callback(self, buttonName):
		print('button_Callback() buttonName:', buttonName)
		print('   self.thresholdSpinbox:', self.thresholdSpinbox.get())
		print('   self.filterSpinbox:', self.filterSpinbox.get())

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