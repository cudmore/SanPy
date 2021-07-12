import numpy as np
import scipy.signal

import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.bAnalysisUtil import statList

class exportTrace(sanpyPlugin):
	"""
	"""
	myHumanName = 'Export Trace'

	def __init__(self, **kwargs):
		super(exportTrace, self).__init__(**kwargs)

		# this plugin will not respond to any interface changes
		self.turnOffAllSignalSlot()

		self.plot()

	def plot(self):
		if self.ba is None:
			return

		self.myType = 'vmFiltered'

		if self.myType == 'vmFiltered':
			xyUnits = ('Time (sec)', 'Vm (mV)')# todo: pass xMin,xMax to constructor
			x = self.ba.sweepX
			y = self.ba.sweepY
		elif self.myType == 'dvdtFiltered':
			xyUnits = ('Time (sec)', 'dV/dt (mV/ms)')# todo: pass xMin,xMax to constructor
		elif self.myType == 'meanclip':
			xyUnits = ('Time (ms)', 'Vm (mV)')# todo: pass xMin,xMax to constructor
		else:
			logger.error(f'Unknown myType: "{self.myType}"')
			xyUnits = ('error time', 'error y')

		path = self.ba.path

		xMin, xMax = self.getStartStop()
		'''
		xMin = None
		xMax = None
		if self.myType in ['clip', 'meanclip']:
			xMin, xMax = self.detectionWidget.clipPlot.getAxis('bottom').range
		else:
			xMin, xMax = self.detectionWidget.getXRange()
		'''

		if self.myType in ['vm', 'dvdt']:
			xMargin = 2 # seconds
		else:
			xMargin = 2

		self.mainWidget = sanpy.interface.bExportWidget(x, y,
						xyUnits=xyUnits,
						path=path,
						xMin=xMin, xMax=xMax,
						xMargin = xMargin,
						type = self.myType,
						darkTheme = True)
						#darkTheme=self.detectionWidget.useDarkStyle)

		# rewire existing widget into plugin architecture
		self.mainWidget.closeEvent = self.onClose
		self._mySetWindowTitle()
