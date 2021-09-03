# Created: 20210609

"""
`sanpyPlugin` is the parent class for all SanPy plugins.
Derive from this class to create new plugins.

Users can run a plugin with the following code

```
import sys
from PyQt5 import QtCore, QtWidgets, QtGui
import sanpy
import sanpy.interface

# create a PyQt application
app = QtWidgets.QApplication([])

# load and analyze sample data
path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
ba = sanpy.bAnalysis(path)
ba.spikeDetect()

# open the interface for the 'saveAnalysis' plugin.
sa = sanpy.interface.plugins.plotScatter(ba=ba, startStop=None)

sys.exit(app.exec_())
```
"""

import math, enum

#from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
import matplotlib.pyplot as plt

# Allow this code to run with just backend
from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

import qdarkstyle

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class ResponseType(enum.Enum):
	"""Enum representing the types of events a Plugin will respond to.
	"""
	switchFile = 1
	analysisChange = 2
	selectSpike = 3
	setAxis = 4

#class sanpyPlugin(QtCore.QObject):
class sanpyPlugin(QtWidgets.QWidget):
	"""
	Base class for all SanPy plugins. Provides general purpose API to build plugings including:

	- Open PyQt and Matplotlib plots
	- Set up signal/slots for:
		(1) file is changed
		(2) detection is run
		(3) spike is selected
		(4) Axis is changed
	"""

	signalCloseWindow = QtCore.pyqtSignal(object)
	"""Emit signal on window close."""

	signalSelectSpike = QtCore.pyqtSignal(object)
	"""Emit signal on spike selection."""

	signalSelectSpikeList = QtCore.pyqtSignal(object)
	"""Emit signal on spike selection."""

	signalDetect = QtCore.pyqtSignal(object)
	"""Emit signal on spike selection."""

	myHumanName = 'UNDEFINED-PLUGIN-NAME'
	"""Each derived class needs to define this."""

	responseTypes = ResponseType
	"""Defines how a plugin will response to interface changes. Includes (switchFile, analysisChange, selectSpike, setAxis)."""

	def __init__(self, ba=None, bPlugin=None, startStop=None, options=None, parent=None):
		"""
		Args:
			ba (sanpy.bAnalysis): [bAnalysis][sanpy.bAnalysis.bAnalysis] object representing one file.
			bPlugin (sanpy.interface.bPlugin): Used in Qt to get SanPy App and to set up signal/slot.
			startStop (list of float): Start and stop (s) of x-axis.
			options (dict): Dictionary of optional plugins.
							Used by 'plot tool' to plot a pool using app analysisDir dfMaster.
							Note: NOT USED.
		"""
		super(sanpyPlugin, self).__init__(parent)
		self._ba = ba
		self._bPlugins = bPlugin # pointer to object, send signal back on close

		self._sweepNumber = 0

		if startStop is not None:
			self._startSec = startStop[0]
			self._stopSec = startStop[1]
		else:
			self._startSec = None
			self._stopSec = None

		# keep track of analysis parameters
		#self.fileRowDict = None  # for detectionParams plugin

		# TODO: keep track of spike selection
		self.selectedSpike = None
		self.selectedSpikeList = []

		self.windowTitle = 'xxx'

		#
		# build a dict of boolean from ResponseType enum class
		self.responseOptions = {}
		for option in (self.responseTypes):
			#print(type(option))
			self.responseOptions[option.name] = True

		# created in self.pyqtWindow()
		#self.mainWidget = QtWidgets.QWidget()

		doDark = True
		if doDark and qdarkstyle is not None:
			self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
		else:
			self.setStyleSheet("")

		#self.scrollArea = QtWidgets.QScrollArea()
		#self.scrollArea.setWidget(self)

		self.layout = None

		# created in self.mplWindow()
		self.fig = None
		self.ax = None
		self.mplToolbar = None

		self.keyIsDown = None

		self.winWidth_inches = 4  # used by mpl
		self.winHeight_inches = 4

		# connect self to main app with signals/slots
		self._installSignalSlot()

	'''
	def _setLayout(self, layout):
		#self.mainWidget.setLayout(layout)
		super().setLayout(layout)

		#self.scrollArea.setWidget(self.mainWidget)
		self.scrollArea.setWidget(self)

		#self.mainWidget.show()
		#self.scrollArea.show()
	'''

	@property
	def sweepNumber(self):
		return self._sweepNumber

	def insertIntoScrollArea(self):
		"""
		When inserting this widget into an interface, may want to wrap it in a ScrollArea

		This is used in main SanPy interface to insert this widget into a tab

		Example in inherited class:
			```
			scrollArea = QtWidgets.QScrollArea()
			scrollArea.setWidget(self)
			return scrollArea
			```
		"""
		return None

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
		Be sure to call _disconnectSignalSlot() on plugin destruction.
		"""
		app = self.getSanPyApp()
		if app is not None:
			# receive spike selection
			app.signalSelectSpike.connect(self.slot_selectSpike)
			app.signalSelectSpikeList.connect(self.slot_selectSpikeList)
			# receive update analysis (both file change and detect)
			app.signalSwitchFile.connect(self.slot_switchFile)
			app.signalUpdateAnalysis.connect(self.slot_updateAnalysis)
			# recieve set sweep
			app.signalSelectSweep.connect(self.slot_setSweep)
			# recieve set x axis
			app.signalSetXAxis.connect(self.slot_set_x_axis)

			# emit when we spike detect (used in detectionParams plugin)
			self.signalDetect.connect(app.slot_detect)

		bPlugins = self.get_bPlugins()
		if bPlugins is not None:
			# emit spike selection
			self.signalSelectSpike.connect(bPlugins.slot_selectSpike)
			self.signalSelectSpikeList.connect(bPlugins.slot_selectSpikeList)
			# emit on close window
			self.signalCloseWindow.connect(bPlugins.slot_closeWindow)

		# connect to self
		self.signalSelectSpike.connect(self.slot_selectSpike)
		self.signalSelectSpikeList.connect(self.slot_selectSpikeList)

	def _disconnectSignalSlot(self):
		"""
		Disconnect signal/slot on destruction.
		"""
		app = self.getSanPyApp()
		if app is not None:
			# receive spike selection
			app.signalSelectSpike.disconnect(self.slot_selectSpike)
			# receive update analysis (both file change and detect)
			app.signalSwitchFile.disconnect(self.slot_switchFile)
			app.signalUpdateAnalysis.disconnect(self.slot_updateAnalysis)
			# recieve set sweep
			app.signalSelectSweep.disconnect(self.slot_setSweep)
			# recieve set x axis
			app.signalSetXAxis.disconnect(self.slot_set_x_axis)

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

	def plot(self):
		"""Add code to plot."""
		pass

	def replot(self):
		"""Add code to replot."""
		pass

	def selectSpike(self, sDict=None):
		"""Add code to select spike from sDict."""
		pass

	def selectSpikeList(self, sDict=None):
		"""Add code to select spike from sDict."""
		pass

	def getStartStop(self):
		"""
		Ret:
			tuple: (start, stop) in seconds. Can be None
		"""
		return self._startSec, self._stopSec

	def keyReleaseEvent(self, event):
		#logger.info(type(event))
		self.keyIsDown = None

	def keyPressEvent(self, event):
		"""
		Used so user can turn on/off responding to analysis changes

		Args:
			event (QtGui.QKeyEvent): Qt event
				(matplotlib.backend_bases.KeyEvent): Matplotlib event
		"""
		#logger.info(type(event))

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
			doCopy = text == 'ctrl+c'
			logger.info(f'mpl key: "{text}"')
		else:
			logger.warning(f'Unknown event type: {type(event)}')
			return

		self.keyIsDown = text

		if doCopy:
			self.copyToClipboard()
		elif key==QtCore.Qt.Key_Escape or text=='esc' or text=='escape':
			# single spike
			sDict = {
				'spikeNumber': None,
				'doZoom': False,
				'ba': self.ba,

			}
			self.signalSelectSpike.emit(sDict)
			# spike list
			sDict = {
				'spikeList': [],
				'doZoom': False,
				'ba': self.ba,
			}
			self.signalSelectSpikeList.emit(sDict)
		elif text == '':
			pass

		# critical difference between mpl and qt
		if isMpl:
			return text
		else:
			#return event
			return

	def copyToClipboard(self):
		"""
		Add code to copy plugin to clipboard
		"""
		pass

	def bringToFront(self):
		# Qt
		self.show()
		self.activateWindow()

		# Matplotlib
		if self.fig is not None:
			FigureManagerQT = self.fig.canvas.manager
			FigureManagerQT.window.activateWindow()
			FigureManagerQT.window.raise_()

	def old_pyqtWindow(self):
		"""
		Create and show a PyQt Window (QWidget)
		User can then add to it

		Creates: self.mainWidget
		"""
		#doDark = True
		#self.mainWidget = QtWidgets.QWidget()
		#self.mainWidget = myWidget(self, doDark)

		# testing testDock.py
		#self.setCentralWidget(self.mainWidget)

		#self._mySetWindowTitle()
		#self.mainWidget.setWindowTitle(self.name)
		#self.mainWidget.show()

	def mplWindow2(self, numRow=1, numCol=1):
		plt.style.use('dark_background')
		# this is dangerous, collides with self.mplWindow()
		self.fig = mpl.figure.Figure()

		# not working
		#self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)

		self.static_canvas = backend_qt5agg.FigureCanvas(self.fig)
		self.static_canvas.setFocusPolicy( QtCore.Qt.ClickFocus ) # this is really triccky and annoying
		self.static_canvas.setFocus()
		self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)

		self.axs = [None] * numRow  # empty list
		if numRow==1 and numCol==1:
			self._static_ax = self.static_canvas.figure.subplots()
			self.axs = self._static_ax
		else:

			for idx in range(numRow):
				plotNum = idx + 1
				#print('mplWindow2()', idx)
				self.axs[idx] = self.static_canvas.figure.add_subplot(numRow,1,plotNum)

		self._mySetWindowTitle()

		# does not work
		#self.static_canvas.mpl_connect('key_press_event', self.keyPressEvent)

		# pick_event assumes 'picker=5' in any .plot()
		self.cid = self.static_canvas.mpl_connect('pick_event', self.spike_pick_event)

		# toolbar need to be added to layout
		#from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
		self.mplToolbar = mpl.backends.backend_qt5agg.NavigationToolbar2QT(self.static_canvas, self.static_canvas)

		layout = QtWidgets.QVBoxLayout()
		layout.addWidget(self.static_canvas)
		layout.addWidget(self.mplToolbar)
		self.setLayout(layout)

	def old_mplWindow(self):
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
		self.fig.canvas.mpl_connect('key_release_event', self.keyReleaseEvent)
		self.fig.canvas.mpl_connect('close_event', self.closeEvent)

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
			if self.fig.canvas.manager is not None:
				self.fig.canvas.manager.set_window_title(self.windowTitle)

		# pyqt
		#self.mainWidget._mySetWindowTitle(self.windowTitle)
		self.setWindowTitle(self.windowTitle)

	def spike_pick_event(self, event):
		"""
		Respond to user clicks in mpl plot
		Assumes plot(..., picker=5)

		"""
		if len(event.ind) < 1:
			return

		spikeNumber = event.ind[0]

		doZoom = False
		modifiers = QtWidgets.QApplication.keyboardModifiers()
		if modifiers == QtCore.Qt.ShiftModifier:
			doZoom = True

		logger.info(f'spike:{spikeNumber} doZoom:{doZoom}')

		# propagate a signal to parent
		sDict = {
			'spikeNumber': spikeNumber,
			'doZoom': doZoom,
			'ba': self.ba,
		}
		self.signalSelectSpike.emit(sDict)

	def closeEvent(self, event):
		"""
		Signal back to parent bPlugin object.

		Args:
			event (matplotlib.backend_bases.CloseEvent): The close event
			or
			event (PyQt5.QtGui.QCloseEvent)
		"""
		self.signalCloseWindow.emit(self)

	def slot_switchFile(self, rowDict, ba, replot=True):
		"""Respond to switch file."""
		#logger.info('')
		if not self.getResponseOption(self.responseTypes.switchFile):
			return

		'''
		app = self.getSanPyApp()
		if app is not None:
			self._ba = app.get_bAnalysis()
		'''
		self._ba = ba
		#self.fileRowDict = rowDict  # for detectionParams plugin

		# reset spike and spike list selection
		self.selectedSpikeList = []
		self.selectedSpike = None
		self.selectSpike()
		self.selectSpikeList()

		# reset start/stop
		startSec = rowDict['Start(s)']
		stopSec = rowDict['Stop(s)']
		if math.isnan(startSec):
			startSec = None
		if math.isnan(stopSec):
			stopSec = None

		#logger.info(f'startSec:{startSec} {type(startSec)} stopSec:{stopSec} {type(stopSec)}')

		self._startSec = startSec
		self._stopSec = stopSec

		# set pyqt window title
		self._mySetWindowTitle()

		if replot:
			self.replot()

	def slot_switchFile2(self, ba, startStop, fileTableRowDict=None):
		"""Respond to switch file.

		Args:
			ba (bAnalysis):
			startStop (list of float): start/stop seconds of analysis
			fileTableRowDict (dict): Dictionary of values from main sanpy file table (like, 'File', 'Cell Type', etc)
		"""
		logger.info('')
		if not self.getResponseOption(self.responseTypes.switchFile):
			return
		#logger.info(path)
		self._ba = ba

		# reset start/stop
		self._startSec = startStop[0]
		self._stopSec = startStop[1]

		# set pyqt window title
		self._mySetWindowTitle()

		self.replot()

	def slot_updateAnalysis(self, ba):
		"""Respond to detection"""
		logger.info('')
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

	def slot_setSweep(self, ba, sweepNumber):
		logger.info('')
		self._sweepNumber = sweepNumber

		# reset selection
		self.selectedSpikeList = []
		self.selectedSpike = None

		self.replot()

	def slot_selectSpikeList(self, eDict):
		"""Respond to spike selection."""

		# don't respond if we are showing a different ba (bAnalysis)
		ba = eDict['ba']
		if self.ba != ba:
			return

		spikeList = eDict['spikeList']
		self.selectedSpikeList = spikeList  # [] on no selection

		self.selectSpikeList(eDict)

	def slot_selectSpike(self, eDict):
		"""Respond to spike selection."""

		# don't respond if user/code has turned this off
		if not self.getResponseOption(self.responseTypes.selectSpike):
			return

		# don't respond if we are showing a different ba (bAnalysis)
		ba = eDict['ba']
		if self.ba != ba:
			return

		self.selectedSpike = eDict['spikeNumber']

		self.selectSpike(eDict)

	def slot_set_x_axis(self, startStopList):
		"""Respond to changes in x-axis.

		Args:
			startStopList (list of float): Start stop in seconds
		"""
		if not self.getResponseOption(self.responseTypes.setAxis):
			return
		# don't set axis if we are showing different ba
		app = self.getSanPyApp()
		if app is not None:
			ba = app.get_bAnalysis()
			if self._ba != ba:
				return

		#logger.info(startStopList)
		if startStopList is None:
			self._startSec = None
			self._stopSec = None
		else:
			self._startSec = startStopList[0]
			self._stopSec = startStopList[1]
		#
		# we do not always want to replot on set axis
		self.setAxis()
		#self.replot()

	def setAxis(self):
		"""
		Respond to set axis.

		Some plugins want to replot() when x-axis changes.
		"""
		pass

	def turnOffAllSignalSlot(self):
		"""
	 	Make plugin not respond to any changes in interface.
		"""
		# turn off all signal/slot
		switchFile = self.responseTypes.switchFile
		self.toggleResponseOptions(switchFile, newValue=False)
		analysisChange = self.responseTypes.analysisChange
		self.toggleResponseOptions(analysisChange, newValue=False)
		selectSpike = self.responseTypes.selectSpike
		self.toggleResponseOptions(selectSpike, newValue=False)
		setAxis = self.responseTypes.setAxis
		self.toggleResponseOptions(setAxis, newValue=False)

	def contextMenuEvent(self, event):
		"""
		Handle right-click

		Args:
			event (xxx): USed to position popup
		"""
		if self.mplToolbar is not None:
			state = self.mplToolbar.mode
			if state in ['zoom rect', 'pan/zoom']:
				# don't process right-click when toolbar is active
				return

		logger.info(event)

		#mainWidget = self.mainWidget

		contextMenu = QtWidgets.QMenu(self)

		# prepend any menu from derived classes
		self.prependMenus(contextMenu)

		# TODO: Put these in parant sanPyPlugin
		switchFile = contextMenu.addAction("Respond to switch file")
		switchFile.setCheckable(True)
		switchFile.setChecked(self.responseOptions['switchFile'])

		analysisChange = contextMenu.addAction("Respond to analysis change")
		analysisChange.setCheckable(True)
		analysisChange.setChecked(self.responseOptions['analysisChange'])

		selectSpike = contextMenu.addAction("Respond to select spike")
		selectSpike.setCheckable(True)
		selectSpike.setChecked(self.responseOptions['selectSpike'])

		axisChange = contextMenu.addAction("Respond to axis change")
		axisChange.setCheckable(True)
		axisChange.setChecked(self.responseOptions['setAxis'])

		contextMenu.addSeparator()
		copyTable = contextMenu.addAction("Copy Table")

		#contextMenu.addSeparator()
		#saveTable = contextMenu.addAction("Save Table")

		#
		# open the menu
		action = contextMenu.exec_(self.mapToGlobal(event.pos()))

		if action is None:
			# n menu selected
			return

		#
		# handle actions
		handled = self.handleContextMenu(action)

		if handled:
			return

		if action == switchFile:
			self.toggleResponseOptions(self.responseTypes.switchFile)
		elif action == analysisChange:
			self.toggleResponseOptions(self.responseTypes.analysisChange)
		elif action == selectSpike:
			self.toggleResponseOptions(self.responseTypes.selectSpike)
		elif action == axisChange:
			self.toggleResponseOptions(self.responseTypes.setAxis)
		elif action == copyTable:
			self.copyToClipboard()
		#elif action == saveTable:
		#	#self.saveToFile()
		#	logger.info('NOT IMPLEMENTED')

		elif action is not None:
				logger.warning(f'Menu action not taken "{action.text}"')

	def prependMenus(self, contextMenu):
		pass

	def handleContextMenu(self, action):
		pass

class myWidget(QtWidgets.QWidget):
	"""
	Helper class to open a PyQt window from within a plugin.
	"""
	def __init__(self, parentPlugin, doDark=True):
		"""
		Arguments:
			parentPlugin (sanpyPlugin): [sanpyPlugin][sanpy.interface.plugins.sanpyPlugin.sanpyPlugin#sanpyPlugin]
			doDark (bool): If True then use dark theme, False use light theme.
		"""
		super().__init__()
		self._parentPlugin = parentPlugin

		#self._mySetWindowTitle()

		# breeze
		if doDark and qdarkstyle is not None:
			self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
		else:
			self.setStyleSheet("")

		#self.show()

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

		Args: event (PyQt5.QtGui.QKeyEvent): Qt event

		TODO: Add to mpl windows
		"""
		#logger.info(event)
		self._parentPlugin.keyPressEvent(event)

	def keyReleaseEvent(self, event):
		#logger.info(event)
		self._parentPlugin.keyReleaseEvent(event)

	def contextMenuEvent(self, event):
		"""Right-click context menu depends on enum ReponseType."""
		self._parentPlugin.contextMenuEvent(event)

	def closeEvent(self, event):
		self._parentPlugin.onClose(event)

def test_plugin():
	import sys
	from PyQt5 import QtCore, QtWidgets, QtGui
	import sanpy
	import sanpy.interface

	# create a PyQt application
	app = QtWidgets.QApplication([])

	# load and analyze sample data
	path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(path)
	ba.spikeDetect()

	# open the interface for the 'saveAnalysis' plugin.
	sa = sanpy.interface.plugins.plotScatter(ba=ba, startStop=None)

	sys.exit(app.exec_())

if __name__ == '__main__':
	test_plugin()
