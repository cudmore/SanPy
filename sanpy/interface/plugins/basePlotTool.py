import numpy as np
import scipy.signal

import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.bAnalysisUtil import statList

class basePlotTool(sanpyPlugin):
	"""
	"""
	myHumanName = 'Base Plot Tool'

	def __init__(self, **kwargs):
		super(basePlotTool, self).__init__('basePlotTool', **kwargs)

		self.masterDf = None
		# one
		#self.masterDf = self.ba.dfReportForScatter
		# pool of bAnalysis
		#self.masterDf = self._bPlugins._sanpyApp.myAnalysisDir.pool_build()

		# turn off all signal/slot
		switchFile = self.responseTypes.switchFile
		self.toggleResponseOptions(switchFile, newValue=False)
		analysisChange = self.responseTypes.switchFile
		self.toggleResponseOptions(analysisChange, newValue=False)
		switchFile = self.responseTypes.switchFile
		self.toggleResponseOptions(switchFile, newValue=False)
		selectSpike = self.responseTypes.switchFile
		self.toggleResponseOptions(selectSpike, newValue=False)

		#self.plot()

	def plot(self):
		if self.ba is None:
			return

		analysisName = 'analysisname'
		statListDict = statList # maps human readable to comments
		categoricalList = ['include', 'Condition', 'Region', 'Sex', 'RegSex', 'File Number', 'analysisname']#, 'File Name']
		hueTypes = ['Region', 'Sex', 'RegSex', 'Condition', 'File Number', 'analysisname'] #, 'File Name'] #, 'None']
		sortOrder = ['Region', 'Sex', 'Condition']
		interfaceDefaults = {'Y Statistic': 'Spike Frequency (Hz)',
							'X Statistic': 'Region',
							'Hue': 'Region',
							'Group By': 'File Number'}

		#analysisName, masterDf = analysisName, df0 = ba.getReportDf(theMin, theMax, savefile)

		#print('!!!! FIX THIS in plugin plotTool.plot()')
		#masterDf = self._bPlugins._sanpyApp.myAnalysisDir.pool_build()
		# was this
		#masterDf = self.ba.dfReportForScatter

		if self.masterDf is None:
			logger.warning('Did not get analysis df, be sure to run detectioon')
			return
		#bScatterPlotMainWindow
		#self.scatterWindow = sanpy.scatterwidget.bScatterPlotMainWindow(
		path = ''
		self.mainWidget = sanpy.interface.bScatterPlotMainWindow(
						path, categoricalList, hueTypes,
						analysisName, sortOrder, statListDict=statListDict,
						masterDf = self.masterDf,
						interfaceDefaults = interfaceDefaults)
		# rewire existing widget into plugin architecture
		self.mainWidget.closeEvent = self.onClose
		self._mySetWindowTitle()
