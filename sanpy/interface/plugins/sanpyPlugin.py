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

class myWidget(QtWidgets.QWidget):
	"""
	Helper class to open a PyQt window from within a plugin.
	"""
	def __init__(self, parentPlugin, name='', doDark=True):
		super().__init__()
		self._parentPlugin = parentPlugin
		self.name = name
		self.setWindowTitle(name)

		if doDark and qdarkstyle is not None:
			self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
		else:
			self.setStyleSheet("")

		self.show()

	def closeEvent(self, event):
		self._parentPlugin.onClose(event)

class sanpyPlugin(QtCore.QObject if QtCore is not None else object):
	"""
	TODO: plugin should recieve slot() when
		(1) detection is run
		(2) spike is selected
		(3) file is changed
	"""
	if QtCore is not None:
		signalCloseWindow = QtCore.pyqtSignal(object)
		signalSelectSpike = QtCore.pyqtSignal(object)

	myHumanName = 'UNDEFINED'

	def __init__(self, name ='', ba=None, bPlugin=None):
		"""
		Args:
			name(str): Name of the plugin
			ba (bAnalysis): bAnalysis object representing one file
		"""
		if QtCore is not None:
			super(sanpyPlugin, self).__init__()
		self._name = name
		self._ba = ba
		self._bPlugins = bPlugin # pointer to object, send signal back on close

		self.mainWidget = None
		self.layout = None

		self.fig = None
		self.ax = None

		self.winWidth_inches = 4
		self.winHeight_inches = 4

		self.installSignalSlot()

	def get_bPlugins(self):
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
		bPlugins = self.get_bPlugins()
		if bPlugins is not None:
			# emit  spike select
			self.signalSelectSpike.connect(bPlugins.slot_selectSpike)
			# emit on close window
			self.signalCloseWindow.connect(bPlugins.slot_closeWindow)

	@property
	def ba(self):
		return self._ba

	@property
	def name(self):
		return self._name

	def plot(self):
		pass

	def replot(self):
		pass

	def pyqtWindow(self):
		"""
		Create and show a PyQt QWidget
		User can then add to it

		Creates: self.mainWidget
		"""
		doDark = True

		#self.mainWidget = QtWidgets.QWidget()
		self.mainWidget = myWidget(self, self.name, doDark)
		#self.mainWidget.setWindowTitle(self.name)
		#self.mainWidget.show()

	def mplWindow2(self):
		tmpFig = mpl.figure.Figure()
		self.static_canvas = backend_qt5agg.FigureCanvas(tmpFig)
		self._static_ax = self.static_canvas.figure.subplots()
		#
		#self.lines, = self._static_ax.plot([], [], 'ow', picker=5)
		#self.linesSel, = self._static_ax.plot([], [], 'oy')

		# pick_event assumes 'picker=5' in any .plot()
		self.cid = self.static_canvas.mpl_connect('pick_event', self.spike_pick_event)

	def mplWindow(self):
		"""
		Create a MatPlotLib (mpl) window.
		User can then plot to window with self.ax.plot(x,y)
		"""
		grid = plt.GridSpec(1, 1, wspace=0.2, hspace=0.4)

		width = self.winWidth_inches
		height = self.winHeight_inches

		self.fig = plt.figure(figsize=(width, height))
		self.ax = self.fig.add_subplot(grid[0, 0:]) #Vm, entire sweep

		self.ax.spines['right'].set_visible(False)
		self.ax.spines['top'].set_visible(False)

		self.fig.canvas.manager.set_window_title(self.name)

		self.fig.canvas.mpl_connect('close_event', self.onClose)

		# spike selection
		# TODO: epand this to other type of objects
		# TODO: allow user to turn off
		#self.cid = self.static_canvas.mpl_connect('pick_event', self.spike_pick_event)

	def spike_pick_event(self, event):
		"""
		Respond to user clicks in plot
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
		self.signalCloseWindow.emit(self._name)

	def slot_updateAnalysis(self):
		"""Used for both switch file and detection"""
		app = self.getSanPyApp()
		if app is not None:
			self._ba = app.get_bAnalysis()
		self.replot()

	def slot_selectSpike(self, eDict):
		logger.info(eDict)

#class PyQtPlugin()

if __name__ == '__main__':
	#testPlot()
	sp = sanpyPlugin()
