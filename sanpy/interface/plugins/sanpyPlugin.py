# 20210609
import numpy as np
import scipy.signal

from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
import matplotlib.pyplot as plt

# Allow this code to run with just backend
try:
	from PyQt5 import QtCore, QtWidgets, QtGui
except (ModuleNotFoundError) as e:
	PyQt5 = None
	QtCore = None
	QtWidgets = None
	QtGui = None
try:
	import pyqtgraph as pg
except (ModuleNotFoundError) as e:
	pyqtgraph = None

try:
	import qdarkstyle
except (ModuleNotFoundError) as e:
	qdarkstyle = None

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy

class sanpyPlugin(QtCore.QObject if QtCore is not None else object):
	"""
	TODO: plugin should recieve slot() when
		(1) detection is run
		(2) spike is selected
		(3) file is changed
	"""
	if QtCore is not None:
		"""emit signal on window close"""
		signalCloseWindow = QtCore.pyqtSignal(object)

		"""emit signal on spike selection"""
		signalSelectSpike = QtCore.pyqtSignal(object)

	"""Each derived class needs to implement this"""
	myHumanName = 'UNDEFINED'

	def __init__(self, name ='', ba=None, bPlugin=None, startStop=None):
		"""
		Args:
			name(str): Name of the plugin
			ba (bAnalysis): bAnalysis object representing one file
			bPlugin (xxx):
			startStop (list of float): Start and stop (s) of x-axis
		"""
		if QtCore is not None:
			super(sanpyPlugin, self).__init__()
		self._name = name
		self._ba = ba
		self._bPlugins = bPlugin # pointer to object, send signal back on close
		#self._startStop = startStop

		if startStop is not None:
			self._startSec = startStop[0]
			self._stopSec = startStop[1]
		else:
			self._startSec = None
			self._stopSec = None

		"""To respond to changes in ba analysis or file"""
		self._respondToAnalysisChange = True

		"""To respond to changes in x-axis"""
		self._respondToSetXAxis = True

		self.mainWidget = None
		self.layout = None

		self.fig = None
		self.ax = None

		self.winWidth_inches = 4
		self.winHeight_inches = 4

		self.installSignalSlot()

	def get_bPlugins(self):
		"""???"""
		return self._bPlugins

	def getSanPyApp(self):
		"""
		Return underlying SanPy app. Only exists if running in Qt Gui
		"""
		theRet = None
		if self._bPlugins is not None:
			theRet = self._bPlugins.getSanPyApp()
		return theRet

	def installSignalSlot(self):
		app = self.getSanPyApp()
		if app is not None:
			# receive spike selecting
			app.signalSelectSpike.connect(self.slot_selectSpike)
			# receive update analysis (both file change and detect)
			app.signalUpdateAnalysis.connect(self.slot_updateAnalysis)
			# recieve set x axis
			app.signalSetXAxis.connect(self.slot_set_x_axis)
		bPlugins = self.get_bPlugins()
		if bPlugins is not None:
			# emit  spike select
			self.signalSelectSpike.connect(bPlugins.slot_selectSpike)
			# emit on close window
			self.signalCloseWindow.connect(bPlugins.slot_closeWindow)

	def setRespondToAnalysisChange(self, respond):
		"""
		If respond==True then we will update when analysis and/or file changes.

		Args:
			respond (bool): respond or not
		"""
		self._respondToAnalysisChange = respond

	@property
	def ba(self):
		return self._ba

	@property
	def name(self):
		return self._name

	def plot(self):
		"""
		add code to plot.
		"""
		pass

	def replot(self):
		"""
		add code to replot.
		"""
		pass

	def selectSpike(self, sDict):
		"""
		add code to select spike from sDict.
		"""
		pass

	def getStartStop(self):
		"""
		Can be None
		"""
		return self._startSec, self._stopSec

	def keyPressEvent(self, event):
		"""
		Add code to handle key-press events. One example is to command+c to copy to clipboard
		See plugin resultsTable.py
		"""
		pass

	def pyqtWindow(self):
		"""
		Create and show a PyQt Window (QWidget)
		User can then add to it

		Creates: self.mainWidget
		"""
		doDark = True

		#self.mainWidget = QtWidgets.QWidget()
		self.mainWidget = myWidget(self, doDark)
		#self.mainWidget.setWindowTitle(self.name)
		#self.mainWidget.show()

	def mplWindow2(self):
		tmpFig = mpl.figure.Figure()
		self.static_canvas = backend_qt5agg.FigureCanvas(tmpFig)
		self._static_ax = self.static_canvas.figure.subplots()
		#
		#self.lines, = self._static_ax.plot([], [], 'ow', picker=5)
		#self.linesSel, = self._static_ax.plot([], [], 'oy')

		#windowTitle = self.myHumanName + ':' + self.name
		#self.fig.canvas.manager.set_window_title(windowTitle)

		# pick_event assumes 'picker=5' in any .plot()
		self.cid = self.static_canvas.mpl_connect('pick_event', self.spike_pick_event)

	def mplWindow(self):
		"""
		Create an mpl (MatPlotLib) window.
		User can then plot to window with self.ax.plot(x,y)
		"""
		grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

		width = self.winWidth_inches
		height = self.winHeight_inches

		self.fig = plt.figure(figsize=(width, height))
		self.ax = self.fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		self.ax.spines['right'].set_visible(False)
		self.ax.spines['top'].set_visible(False)

		self.mySetWindowTitle()

		self.fig.canvas.mpl_connect('close_event', self.onClose)

		# spike selection
		# TODO: epand this to other type of objects
		# TODO: allow user to turn off
		#self.cid = self.static_canvas.mpl_connect('pick_event', self.spike_pick_event)

	def mySetWindowTitle(self):
		if self.ba is not None:
			fileName = self.ba.getFileName()
		else:
			fileName = ''
		windowTitle = self.myHumanName + ':' + fileName

		# mpl
		if self.fig is not None:
			self.fig.canvas.manager.set_window_title(windowTitle)

		# pyqt
		if self.mainWidget is not None:
			self.mainWidget.mySetWindowTitle()

	def spike_pick_event(self, event):
		"""
		Respond to user clicks in mpl plot
		Assumes plot(..., picker=5)
		"""
		if len(event.ind) < 1:
			return

		spikeNumber = event.ind[0]

		doZoom = False
		modifiers = QtGui.QApplication.keyboardModifiers()
		if modifiers == QtCore.Qt.ShiftModifier:
			doZoom = True

		logger.info(f'{spikeNumber} {doZoom}')

		# propagate a signal to parent
		sDict = {
			'spikeNumber': spikeNumber,
			'doZoom': doZoom
		}
		self.signalSelectSpike.emit(sDict)

	def onClose(self, event):
		"""
		Signal back to parent bPlugin object

		Args:
			event (matplotlib.backend_bases.CloseEvent): The close event
			or
			event (PyQt5.QtGui.QCloseEvent)
		"""
		self.signalCloseWindow.emit(self)

	def slot_updateAnalysis(self):
		"""Used for both switch file and detection"""
		if not self._respondToAnalysisChange:
			return
		app = self.getSanPyApp()
		if app is not None:
			self._ba = app.get_bAnalysis()

		# set pyqt window title
		self.mySetWindowTitle()

		#
		self.replot()

	def slot_selectSpike(self, eDict):
		if not self._respondToAnalysisChange:
			return
		self.selectSpike(eDict)

	def slot_set_x_axis(self, startStopList):
		logger.info(startStopList)
		if not self._respondToSetXAxis:
			return
		if startStopList is None:
			self._startSec = None
			self._stopSec = None
		else:
			self._startSec = startStopList[0]
			self._stopSec = startStopList[1]
		#
		#self.setAxis()
		self.replot()

class myWidget(QtWidgets.QWidget):
	"""
	Helper class to open a PyQt window from within a plugin.
	"""
	def __init__(self, parentPlugin, doDark=True):
		super().__init__()
		self._parentPlugin = parentPlugin

		self.mySetWindowTitle()

		if doDark and qdarkstyle is not None:
			self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
		else:
			self.setStyleSheet("")

		self.show()

	def mySetWindowTitle(self):
		"""
		Set pyqt window title from current ba
		"""
		if self._parentPlugin.ba is not None:
			fileName = self._parentPlugin.ba.getFileName()
		else:
			fileName = ''
		windowTitle = self._parentPlugin.myHumanName + ':' + fileName
		self.setWindowTitle(windowTitle)

	def keyPressEvent(self, event):
		"""
		Used so user can turn on/off responding to analysis changes

		TODO: Add to mpl windows
		"""
		pass
		#logger.info('event')
		self._parentPlugin.keyPressEvent(event)

	def closeEvent(self, event):
		self._parentPlugin.onClose(event)

if __name__ == '__main__':
	#testPlot()
	sp = sanpyPlugin()
