import sys, time
from functools import partial

import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

'''
	from matplotlib.backends.backend_qt5agg import (
		FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
'''
from matplotlib.backends import backend_qt5agg

import matplotlib as mpl
#from matplotlib.figure import Figure

###
from bAnalysis import bAnalysis
#import pyabf # see: https://github.com/swharden/pyABF

now = time.time()

abfFile = '/Users/cudmore/Sites/bAnalysis/data/19221021.abf'
abfFile = '/Users/cudmore/Sites/bAnalysis/data/19114001.abf'
#myabf = pyabf.ABF(abfFile)
ba = bAnalysis(file=abfFile)

ba.getDerivative(medianFilter=5) # derivative
ba.spikeDetect(dVthresholdPos=100, minSpikeVm=-20, medianFilter=0)

#print('ba.spikeDict:', ba.spikeDict)

print ("abf load/anaysis time:", time.time()-now, "sec")
###

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

class myQGraphicsView(QtWidgets.QGraphicsView):
	"""
	Main canvas widget
	"""
	def __init__(self, plotThis='Vm', parent=None):
		#print('myQGraphicsView().__init__()')
		super(QtWidgets.QGraphicsView, self).__init__(parent)

		self.setBackgroundBrush(QtCore.Qt.darkGray)

		self.myScene = QtWidgets.QGraphicsScene()

		if plotThis == 'vm':
			lines = MultiLine(x, ba.abf.sweepY)
		elif plotThis == 'dvdt':
			lines = MultiLine(x, ba.filteredDeriv)
		else:
			print('error: myQGraphicsView() expecting plotThis in ("vm", "dvdt")')

		self.myScene.addItem(lines)

		self.setScene(self.myScene)

class MultiLine(pg.QtGui.QGraphicsPathItem):
	def __init__(self, x, y):
		"""x and y are 2D arrays of shape (Nplots, Nsamples)"""
		# abb removed
		#connect = np.ones(x.shape, dtype=bool)
		#connect[:,-1] = 0 # don't draw the segment between each trace
		#self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect.flatten())
		self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect='all')
		pg.QtGui.QGraphicsPathItem.__init__(self, self.path)

		# holy shit, this is bad, without this the app becomes non responsive???
		# if width > 1.0 then this whole app STALLS
		self.setPen(pg.mkPen(color='k', width=1))
	def shape(self):
		# override because QGraphicsPathItem.shape is too expensive.
		#print(time.time(), 'MultiLine.shape()', pg.QtGui.QGraphicsItem.shape(self))
		return pg.QtGui.QGraphicsItem.shape(self)
	def boundingRect(self):
		#print(time.time(), 'MultiLine.boundingRect()', self.path.boundingRect())
		return self.path.boundingRect()

class MainWindow(QtWidgets.QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)

		self.title = 'SanPy'
		self.left = 20
		self.top = 10
		self.width = 2*1024 #640
		self.height = 1*768 #480

		self.setMinimumSize(320, 240)
		self.setWindowTitle(self.title)
		self.setGeometry(self.left, self.top, self.width, self.height)

		self.buildUI()

	def buildUI(self):
		self.centralwidget = QtWidgets.QWidget(self)
		self.centralwidget.setObjectName("centralwidget")

		self.myQVBoxLayout = QtWidgets.QVBoxLayout(self.centralwidget)

		#
		# toolbar
		print('buildUI() building toobar')
		self.toolbarWidget = myToolbarWidget()
		self.addToolBar(QtCore.Qt.LeftToolBarArea, self.toolbarWidget)

		#
		# tree view of files
		print('buildUI() building file tree')
		self.myTableWidget = QtWidgets.QTreeWidget()
		# append to layout
		self.myQVBoxLayout.addWidget(self.myTableWidget)

		#
		print('buildUI() building pg.GraphicsLayoutWidget')
		view = pg.GraphicsLayoutWidget()
		view.show()
		w1 = view.addPlot(row=0, col=0)
		w2 = view.addPlot(row=1, col=0)

		print('buildUI() building lines for deriv')
		lines = MultiLine(ba.abf.sweepX, ba.filteredDeriv)
		w1.addItem(lines)

		print('buildUI() building lines for vm')
		lines = MultiLine(ba.abf.sweepX, ba.abf.sweepY)
		#lines = MultiLine(x, y)
		w2.addItem(lines)

		#
		# on top of Vm
		xPlot, yPlot = ba.getStat('peakSec', 'peakVal')

		self.scatterPeak = pg.ScatterPlotItem(pen=pg.mkPen(width=5, color='r'), symbol='o', size=2)
		self.scatterPeak.setData(x=xPlot, y=yPlot)
		self.scatterPeak.sigClicked.connect(self.scatterClicked)
		w2.addItem(self.scatterPeak)

		# try for horizontal selection
		linearRegionItem = pg.LinearRegionItem(values=(0,0), orientation=pg.LinearRegionItem.Vertical)
		linearRegionItem.sigRegionChangeFinished.connect(self.update_x_axis)
		w2.addItem(linearRegionItem)

		print('buildUI() adding view to myQVBoxLayout')
		self.myQVBoxLayout.addWidget(view)

		#
		# stat plot
		print('buildUI() building matplotlib x/y plot')
		static_canvas = backend_qt5agg.FigureCanvas(mpl.figure.Figure(figsize=(5, 3)))
		self.myQVBoxLayout.addWidget(static_canvas)

		# i want the mpl toolbar in the mpl canvas or sublot
		# this is adding mpl toolbar to main window -->> not what I want
		#self.addToolBar(backend_qt5agg.NavigationToolbar2QT(static_canvas, self))
		# this kinda works as wanted, toolbar is inside mpl plot but it is FUCKING UGLY !!!!
		self.mplToolbar = backend_qt5agg.NavigationToolbar2QT(static_canvas, static_canvas)

		self._static_ax = static_canvas.figure.subplots()
		#t = np.linspace(0, 10, 501)
		#self._static_ax.plot(t, np.tan(t), ".")
		xPlot, yPlot = ba.getStat('peakSec', 'peakVal')
		self._static_ax.plot(xPlot, yPlot, ".")


		#
		# leave here, critical
		self.setCentralWidget(self.centralwidget)

		print('buildUI() done')

	def update_x_axis(self):
		print('update_x_axis()')

	def scatterClicked(self, scatter, points):
		print('scatterClicked() scatter:', scatter, points)
	
class myToolbarWidget(QtWidgets.QToolBar):
	def __init__(self, parent=None):
		print('myToolbarWidget.__init__')
		super(QtWidgets.QToolBar, self).__init__(parent)

		buttonName = 'Save Canvas'
		button = QtWidgets.QPushButton(buttonName)
		button.setToolTip('Load a canvas from disk')
		button.clicked.connect(partial(self.on_button_click,buttonName))
		self.addWidget(button)

	@QtCore.pyqtSlot()
	def on_button_click(self, name):
		print('=== myToolbarWidget.on_button_click() name:', name)

if __name__ == '__main__':
	import logging
	import traceback

	try:
		app = QtWidgets.QApplication(sys.argv)
		w = MainWindow()
		#w.resize(640, 480)
		w.show()
		#sys.exit(app.exec_())
	except Exception as e:
		print(traceback.format_exc())
		#logging.error(traceback.format_exc())
		sys.exit(app.exec_())
		raise
	finally:
		sys.exit(app.exec_())
