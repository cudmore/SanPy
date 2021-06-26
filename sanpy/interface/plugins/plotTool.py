import numpy as np
import scipy.signal

import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.bAnalysisUtil import statList

class plotTool(sanpyPlugin):
	"""
	"""
	myHumanName = 'Plot Tool'

	def __init__(self, **kwargs):
		super(plotTool, self).__init__('plotTool', **kwargs)
		self.plot()

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
		#masterDf = self._bPlugins._sanpyApp.dfReportForScatter
		masterDf = self.ba.dfReportForScatter
		#print('== masterDf:')
		#print(masterDf)
		if masterDf is None:
			logger.warning('Did not get analysis df, be sure to run detectioon')
			return
		#bScatterPlotMainWindow
		#self.scatterWindow = sanpy.scatterwidget.bScatterPlotMainWindow(
		path = ''
		self.scatterWindow = sanpy.interface.bScatterPlotMainWindow(
						path, categoricalList, hueTypes,
						analysisName, sortOrder, statListDict=statListDict,
						masterDf = masterDf,
						interfaceDefaults = interfaceDefaults)
