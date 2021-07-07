"""
`sanpyPlugin` is the parent class for all SanPy plugins.

Derive from this class to create new plugins.

Users can run a plugin with the following code

```
	import sanpy
	import sys
	app = QtWidgets.QApplication([])

	# load and analyze sample data
	path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(path)
	ba.spikeDetect()

	# open the interface for the 'saveAnalysis' plugin.
	sa = sanpy.interface.plugins.saveAnalysis(ba=ba, startStop=None)

	sys.exit(app.exec_())
```

Created: 20210609
"""

import numpy as np
import scipy.signal

from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
import matplotlib.pyplot as plt

# Allow this code to run with just backend
from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

import qdarkstyle

#import sanpy

import enum

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class ResponseType(enum.Enum):
	"""Enum encapsulating types of events we respond to."""
	switchFile = 1
	analysisChange = 2
	selectSpike = 3
	setAxis = 4

class sanpyPlugin(QtCore.QObject if QtCore is not None else object):
	"""
	Plugins recieve slot() when
		(1) file is changed
		(2) detection is run
		(3) spike is selected
		(4) Axis is changed
	"""
	if QtCore is not None:

		signalCloseWindow = QtCore.pyqtSignal(object)
		"""Emit signal on window close."""

		signalSelectSpike = QtCore.pyqtSignal(object)
		"""Emit signal on spike selection."""

	myHumanName = 'UNDEFINED'
	"""Each derived class needs to define this."""

	responseTypes = ResponseType

	def __init__(self, name='', ba=None, bPlugin=None, startStop=None, options=None):
		"""
		Args:
			name(str): Name of the plugin
			ba (bAnalysis): bAnalysis object representing one file
			bPlugin (bPlugin): Used in Qt to get SanPy App and to set up signal/slot
			startStop (list of float): Start and stop (s) of x-axis
			options (dict): Dictionary of optional plugins.
							Used by 'plot tool' to plot a pool using app analysisDir dfMaster.
		"""
		if QtCore is not None:
			super(sanpyPlugin, self).__init__()
		self._ba = ba
		self._bPlugins = bPlugin # pointer to object, send signal back on close

		if startStop is not None:
			self._startSec = startStop[0]
			self._stopSec = startStop[1]
		else:
			self._startSec = None
			self._stopSec = None

		self.windowTitle = 'xxx'

		#
		# build a dict of boolean from ResponseType enum class
		self.responseOptions = {}
		for option in (self.responseTypes):
			#print(type(option))
			self.responseOptions[option.name] = True

		self.mainWidget = None
		self.layout = None

		self.fig = None
		self.ax = None

		self.winWidth_inches = 4
		self.winHeight_inches = 4

		self._installSignalSlot()

	def get_bAnalysis(self):
		"""
		Get current bAnalysis either from SanPy app or self.
		"""
		theRet = None
		if self.getSanPyApp() is not None:
			theRet = self.getSanPyApp().get_bAnalysis()
		else:
			theRet = self._ba
		return theRet

	@property
	def ba(self):
		"""
		todo: Depreciate and use self.get_bAnalysis().
		"""
		return self._ba

	def get_bPlugins(self):
		"""???"""
		return self._bPlugins

	def getSanPyApp(self):
		"""
		Return underlying SanPy app. Only exists if running in SanPy Qt Gui
		"""
		theRet = None
		if self._bPlugins is not None:
			theRet = self._bPlugins.getSanPyApp()
		return theRet

	def _installSignalSlot(self):
		"""
		Set up communication signals/slots.
		"""
		app = self.getSanPyApp()
		if app is not None:
			# receive spike selection
			app.signalSelectSpike.connect(self.slot_selectSpike)
			# receive update analysis (both file change and detect)
			app.signalSwitchFile.connect(self.slot_switchFile)
			app.signalUpdateAnalysis.connect(self.slot_updateAnalysis)
			# recieve set x axis
			app.signalSetXAxis.connect(self.slot_set_x_axis)
		bPlugins = self.get_bPlugins()
		if bPlugins is not None:
			# emit spike selection
			self.signalSelectSpike.connect(bPlugins.slot_selectSpike)
			# emit on close window
			self.signalCloseWindow.connect(bPlugins.slot_closeWindow)

	def toggleResponseOptions(self, thisOption, newValue=None):
		"""
		Sets underlying responseOptions based on name of thisOption (a ResponseType enum).

		Args:
			thisOption (enum ResponseType)
			newValue (boolean or None): If boolean then set, if None then toggle.
		"""
		logger.info(f'{thisOption} {newValue}')
		if newValue is None:
			newValue = not self.responseOptions[thisOption.name]
		self.responseOptions[thisOption.name] = newValue

	def getResponseOption(self, thisOption):
		"""
		Get the state of a plot option from responseOptions.

		Args:
			thisOption (enum ResponseType)
		"""
		return self.responseOptions[thisOption.name]

	'''
	@property
	def name(self):
		"""
		TODO: not used?
		"""
		return self._name
	'''

	def plot(self):
		"""Add code to plot."""
		pass

	def replot(self):
		"""Add code to replot."""
		pass

	def selectSpike(self, sDict):
		"""Add code to select spike from sDict."""
		pass

	def getStartStop(self):
		"""
		Ret:
			tuple: (start, stop) in seconds. Can be None
		"""
		return self._startSec, self._stopSec

	def keyPressEvent(self, event):
		"""
		Used so user can turn on/off responding to analysis changes

		Args:
			event (QtGui.QKeyEvent): Qt event
				(matplotlib.backend_bases.KeyEvent): Matplotlib event
		"""
		logger.info(type(event))
		isQt = isinstance(event, QtGui.QKeyEvent)
		isMpl = isinstance(event, mpl.backend_bases.KeyEvent)

		key = None
		text = None
		doCopy = False
		if isQt:
			key = event.key()
			text = event.text()
			doCopy = event.matches(QtGui.QKeySequence.Copy)
		elif isMpl:
			# q will quit !!!!
			text = event.key
			logger.info(f'mpl key: {text}')
		else:
			logger.warning(f'Unknown event type: {type(event)}')
			return

		if doCopy:
			self.copyToClipboard()
		elif text == '':
			pass

	def copyToClipboard(self):
		pass

	def bringToFront(self):
		# Qt
		if self.mainWidget is not None:
			self.mainWidget.show()
			self.mainWidget.activateWindow()

		# Matplotlib
		if self.fig is not None:
			FigureManagerQT = self.fig.canvas.manager
			FigureManagerQT.window.activateWindow()
			FigureManagerQT.window.raise_()

	def pyqtWindow(self):
		"""
		Create and show a PyQt Window (QWidget)
		User can then add to it

		Creates: self.mainWidget
		"""
		doDark = True

		#self.mainWidget = QtWidgets.QWidget()
		self.mainWidget = myWidget(self, doDark)
		self._mySetWindowTitle()
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
		self._mySetWindowTitle()

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

		self._mySetWindowTitle()

		self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)
		self.fig.canvas.mpl_connect('close_event', self.onClose)

		# spike selection
		# TODO: epand this to other type of objects
		# TODO: allow user to turn off
		#self.cid = self.static_canvas.mpl_connect('pick_event', self.spike_pick_event)

	def _mySetWindowTitle(self):
		if self.ba is not None:
			fileName = self.ba.getFileName()
		else:
			fileName = ''
		self.windowTitle = self.myHumanName + ':' + fileName

		# mpl
		if self.fig is not None:
			self.fig.canvas.manager.set_window_title(self.windowTitle)

		# pyqt
		if self.mainWidget is not None:
			#self.mainWidget._mySetWindowTitle(self.windowTitle)
			self.mainWidget.setWindowTitle(self.windowTitle)

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
		Signal back to parent bPlugin object.

		Args:
			event (matplotlib.backend_bases.CloseEvent): The close event
			or
			event (PyQt5.QtGui.QCloseEvent)
		"""
		self.signalCloseWindow.emit(self)

	def slot_switchFile(self, path):
		"""Respond to switch file."""
		if not self.getResponseOption(self.responseTypes.switchFile):
			return
		logger.info(path)
		app = self.getSanPyApp()
		if app is not None:
			self._ba = app.get_bAnalysis()

		# set pyqt window title
		self._mySetWindowTitle()

	def slot_updateAnalysis(self, ba):
		"""Respond to detection"""
		if not self.getResponseOption(self.responseTypes.analysisChange):
			return
		# don't update analysis if we are showing different ba
		if self._ba != ba:
			return
		#self._ba = app.get_bAnalysis()

		# set pyqt window title
		#self._mySetWindowTitle()

		#
		self.replot()

	def slot_selectSpike(self, eDict):
		"""Respond to spike selection."""
		if not self.getResponseOption(self.responseTypes.selectSpike):
			return

		print('====== TODO: fix sanpyPlugin.slot_selectSpike() only update if ba that is selected is the same as self._ba')
		# don't select spike if we are showing different ba
		#if self._ba != ba:
		#	return

		self.selectSpike(eDict)

	def slot_set_x_axis(self, startStopList):
		"""Respond to changes in x-axis."""
		if not self.getResponseOption(self.responseTypes.setAxis):
			return
		# don't set axis if we are showing different ba
		app = self.getSanPyApp()
		if app is not None:
			ba = app.get_bAnalysis()
			if self._ba != ba:
				return

		logger.info(startStopList)
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

		#self._mySetWindowTitle()

		if doDark and qdarkstyle is not None:
			self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
		else:
			self.setStyleSheet("")

		self.show()

	'''
	def _mySetWindowTitle(self, windowTitle):
		"""
		Set pyqt window title from current ba
		"""
		self.setWindowTitle(windowTitle)
	'''

	@property
	def parentPlugin(self):
		return self._parentPlugin

	def keyPressEvent(self, event):
		"""
		Used so user can turn on/off responding to analysis changes

		Args:
			event (PyQt5.QtGui.QKeyEvent): Qt event

		TODO: Add to mpl windows
		"""
		logger.info(event)
		self._parentPlugin.keyPressEvent(event)

	def contextMenuEvent(self, event):
		"""Right-click context menu depends on enum ReponseType."""
		#logger.info(event)

		contextMenu = QtWidgets.QMenu(self)

		switchFile = contextMenu.addAction("Respond to switch file")
		switchFile.setCheckable(True)
		switchFile.setChecked(self.parentPlugin.responseOptions['switchFile'])

		analysisChange = contextMenu.addAction("Respond to analysis change")
		analysisChange.setCheckable(True)
		analysisChange.setChecked(self.parentPlugin.responseOptions['analysisChange'])

		selectSpike = contextMenu.addAction("Respond to select spike")
		selectSpike.setCheckable(True)
		selectSpike.setChecked(self.parentPlugin.responseOptions['selectSpike'])

		axisChange = contextMenu.addAction("Respond to axis change")
		axisChange.setCheckable(True)
		axisChange.setChecked(self.parentPlugin.responseOptions['setAxis'])

		contextMenu.addSeparator()
		copyTable = contextMenu.addAction("Copy Table")

		contextMenu.addSeparator()
		saveTable = contextMenu.addAction("Save Table")
		#
		action = contextMenu.exec_(self.mapToGlobal(event.pos()))

		if action == switchFile:
			self.parentPlugin.toggleResponseOptions(self.parentPlugin.responseTypes.switchFile)
		elif action == analysisChange:
			self.parentPlugin.toggleResponseOptions(self.parentPlugin.responseTypes.analysisChange)
		elif action == selectSpike:
			self.parentPlugin.toggleResponseOptions(self.parentPlugin.responseTypes.selectSpike)
		elif action == axisChange:
			self.parentPlugin.toggleResponseOptions(self.parentPlugin.responseTypes.setAxis)
		elif action is not None:
			logger.warning(f'Action not taken "{action}"')

	def closeEvent(self, event):
		self._parentPlugin.onClose(event)

if __name__ == '__main__':
	#testPlot()
	sp = sanpyPlugin()
