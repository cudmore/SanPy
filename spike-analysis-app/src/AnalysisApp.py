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

from bAnalysis import bAnalysis

__version__ = '20190312'

LARGE_FONT= ("Verdana", 12)

#####################################################################################
# raw
class PageThree(ttk.Frame):

	def __init__(self, parent, controller, showToolbar=False):
		print('PageThree.__init__')
		
		ttk.Frame.__init__(self, parent)

		self.grid_rowconfigure(0, weight=1)
		#self.grid_rowconfigure(1, weight=1)
		self.grid_columnconfigure(0, weight=1)
		
		'''
		label = ttk.Label(self, text="Graph Page!", font=LARGE_FONT)		
		label.pack(pady=10,padx=10)
		'''
		
		'''
		button1 = ttk.Button(self, text="Back to Home",
							command=lambda: controller.show_frame(StartPage))
		button1.pack()
		'''
		
		self.fig = matplotlib.figure.Figure(figsize=(5,5), dpi=100)
		self.axes = self.fig.add_subplot(111)

		self.line, = self.axes.plot([],[], 'k') # REMEMBER ',' ON LHS
		self.spikeTimesLine, = self.axes.plot([],[], 'or') # REMEMBER ',' ON LHS


		print('1')
		
		self.canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.fig, parent)
		self.canvas.draw()
		

		self.canvas.get_tk_widget().grid_rowconfigure(0, weight=1)
		#self.canvas.get_tk_widget().grid_rowconfigure(1, weight=1)
		self.canvas.get_tk_widget().grid_columnconfigure(0, weight=1)

		# this kinda works
		self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

		# use NavigationToolbar2Tk
		if showToolbar:
			toolbar = matplotlib.backends.backend_tkagg.NavigationToolbar2Tk(self.canvas, parent)
			toolbar.update()
		#toolbar = matplotlib.backends.backend_tkagg.NavigationToolbar2Tk(canvas, controller.root)
		#toolbar.update()
		#canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

		# this kinda works
		print('2')
		#self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
		
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
		w = 800 #self.configDict['appWindowGeometry_w']
		h = 800# self.configDict['appWindowGeometry_h']
		self.root.geometry('%dx%d+%d+%d' % (w, h, x, y))

		self.buildInterface()
		
		self.myMenus = bMenus.bMenus(self)

		if path is not None:
			self.loadFolder(path=path)
			
		# this will not return until we quit
		self.root.mainloop()

	def buildInterface(self):
		myPadding = 5
		myBorderWidth = 0

		self.lastResizeWidth = None
		self.lastResizeHeight = None
		
		self.root.grid_rowconfigure(0, weight=1)
		self.root.grid_columnconfigure(0, weight=1)

		#
		# file list
		self.vPane = ttk.PanedWindow(self.root, orient="vertical") #, showhandle=True)
		self.vPane.grid(row=0, column=0, sticky="nsew")

		upper_frame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		upper_frame.grid(row=0, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		upper_frame.grid_rowconfigure(0, weight=1)
		upper_frame.grid_columnconfigure(0, weight=1)
		self.vPane.add(upper_frame)

		self.fileListTree = bTree.bFileTree(upper_frame, self, videoFileList='')
		self.fileListTree.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)

		#
		# raw data
		lower_frame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		lower_frame.grid(row=0, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		lower_frame.grid_rowconfigure(0, weight=1)
		lower_frame.grid_columnconfigure(0, weight=1)
		self.vPane.add(lower_frame)
		
		self.rawPlot = PageThree(lower_frame, self, showToolbar=False)
		#self.rawPlot.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		
		#
		# deriv data
		print('4')
		deriv_frame = ttk.Frame(self.vPane, borderwidth=myBorderWidth, relief="sunken")
		deriv_frame.grid(row=0, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		deriv_frame.grid_rowconfigure(0, weight=1)
		deriv_frame.grid_columnconfigure(0, weight=1)
		self.vPane.add(deriv_frame)
		
		self.derivPlot = PageThree(deriv_frame, self)
		#self.rawPlot.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		
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
		
		ba = bAnalysis(file=videoPath)
		#print(ba)

		self.rawPlot.plotRaw(ba)
		self.derivPlot.plotDeriv(ba)
		
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