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
class PageThree(ttk.Frame):

	def __init__(self, parent, controller):
		ttk.Frame.__init__(self, parent)

		self.grid_rowconfigure(0, weight=1)
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
		
		fig = matplotlib.figure.Figure(figsize=(5,5), dpi=100)
		ax = fig.add_subplot(111)
		#self.line, = ax.plot([1,2,3,4,5,6,7,8],[5,6,1,3,8,9,3,5]) # REMEMBER ',' ON LHS
		self.line, = ax.plot([],[]) # REMEMBER ',' ON LHS

		self.fig = fig
		self.axes = ax

		#canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(f, self)
		self.canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(fig, parent)
		#canvas.show()
		self.canvas.draw()
		#canvas.get_tk_widget().pack(side=ttk.BOTTOM, fill=ttk.BOTH, expand=True)
		#self.canvas.get_tk_widget().pack(side="bottom", fill="both", expand=True)
		
		# this kinda works
		self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

		# use NavigationToolbar2Tk
		#toolbar = matplotlib.backends.backend_tkagg.NavigationToolbar2Tk(canvas, controller.root)
		#toolbar.update()
		#canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
		
	def plot(self, ba):
		#ba.plotDeriv(fig=self.fig)
		self.line.set_ydata(ba.abf.sweepY)
		self.line.set_xdata(ba.abf.sweepX)
		
		xMin = min(ba.abf.sweepX)
		xMax = max(ba.abf.sweepX)
		self.axes.set_xlim(xMin, xMax)
		
		yMin = min(ba.abf.sweepY)
		yMax = max(ba.abf.sweepY)
		self.axes.set_ylim(yMin, yMax)
		
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
		w = 500 #self.configDict['appWindowGeometry_w']
		h = 300# self.configDict['appWindowGeometry_h']
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
		
		self.rawPlot = PageThree(lower_frame, self)
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

		self.rawPlot.plot(ba)
		
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