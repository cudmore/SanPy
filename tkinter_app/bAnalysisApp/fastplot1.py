import sys, time
from functools import partial

import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui

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

x = ba.abf.sweepX
y = ba.abf.sweepY

ba.getDerivative(medianFilter=5) # derivative
ba.spikeDetect0() # analysis

print ("abf load/anaysis time:", time.time()-now, "sec")
###

###
###
import struct

def eq(a, b):
	"""The great missing equivalence function: Guaranteed evaluation to a single bool value.

	This function has some important differences from the == operator:

	1. Returns True if a IS b, even if a==b still evaluates to False, such as with nan values.
	2. Tests for equivalence using ==, but silently ignores some common exceptions that can occur
	   (AtrtibuteError, ValueError).
	3. When comparing arrays, returns False if the array shapes are not the same.
	4. When comparing arrays of the same shape, returns True only if all elements are equal (whereas
	   the == operator would return a boolean array).
	"""
	if a is b:
		return True

	# Avoid comparing large arrays against scalars; this is expensive and we know it should return False.
	aIsArr = isinstance(a, (np.ndarray, MetaArray))
	bIsArr = isinstance(b, (np.ndarray, MetaArray))
	if (aIsArr or bIsArr) and type(a) != type(b):
		return False

	# If both inputs are arrays, we can speeed up comparison if shapes / dtypes don't match
	# NOTE: arrays of dissimilar type should be considered unequal even if they are numerically
	# equal because they may behave differently when computed on.
	if aIsArr and bIsArr and (a.shape != b.shape or a.dtype != b.dtype):
		return False

	# Test for equivalence.
	# If the test raises a recognized exception, then return Falase
	try:
		try:
			# Sometimes running catch_warnings(module=np) generates AttributeError ???
			catcher =  warnings.catch_warnings(module=np)  # ignore numpy futurewarning (numpy v. 1.10)
			catcher.__enter__()
		except Exception:
			catcher = None
		e = a==b
	except (ValueError, AttributeError):
		return False
	except:
		print('failed to evaluate equivalence for:')
		print("  a:", str(type(a)), str(a))
		print("  b:", str(type(b)), str(b))
		raise
	finally:
		if catcher is not None:
			catcher.__exit__(None, None, None)

	t = type(e)
	if t is bool:
		return e
	elif t is np.bool_:
		return bool(e)
	elif isinstance(e, np.ndarray) or (hasattr(e, 'implements') and e.implements('MetaArray')):
		try:   ## disaster: if a is an empty array and b is not, then e.all() is True
			if a.shape != b.shape:
				return False
		except:
			return False
		if (hasattr(e, 'implements') and e.implements('MetaArray')):
			return e.asarray().all()
		else:
			return e.all()
	else:
		raise Exception("== operator returned type %s" % str(type(e)))

def arrayToQPath(x, y, connect='all'):
	"""Convert an array of x,y coordinats to QPainterPath as efficiently as possible.
	The *connect* argument may be 'all', indicating that each point should be
	connected to the next; 'pairs', indicating that each pair of points
	should be connected, or an array of int32 values (0 or 1) indicating
	connections.
	"""

	## Create all vertices in path. The method used below creates a binary format so that all
	## vertices can be read in at once. This binary format may change in future versions of Qt,
	## so the original (slower) method is left here for emergencies:
		#path.moveTo(x[0], y[0])
		#if connect == 'all':
			#for i in range(1, y.shape[0]):
				#path.lineTo(x[i], y[i])
		#elif connect == 'pairs':
			#for i in range(1, y.shape[0]):
				#if i%2 == 0:
					#path.lineTo(x[i], y[i])
				#else:
					#path.moveTo(x[i], y[i])
		#elif isinstance(connect, np.ndarray):
			#for i in range(1, y.shape[0]):
				#if connect[i] == 1:
					#path.lineTo(x[i], y[i])
				#else:
					#path.moveTo(x[i], y[i])
		#else:
			#raise Exception('connect argument must be "all", "pairs", or array')

	## Speed this up using >> operator
	## Format is:
	##	numVerts(i4)   0(i4)
	##	x(f8)   y(f8)   0(i4)	<-- 0 means this vertex does not connect
	##	x(f8)   y(f8)   1(i4)	<-- 1 means this vertex connects to the previous vertex
	##	...
	##	0(i4)
	##
	## All values are big endian--pack using struct.pack('>d') or struct.pack('>i')

	path = QtGui.QPainterPath()

	#profiler = debug.Profiler()
	n = x.shape[0]
	# create empty array, pad with extra space on either end
	arr = np.empty(n+2, dtype=[('x', '>f8'), ('y', '>f8'), ('c', '>i4')])
	# write first two integers
	#profiler('allocate empty')
	byteview = arr.view(dtype=np.ubyte)
	byteview[:12] = 0
	byteview.data[12:20] = struct.pack('>ii', n, 0)
	#profiler('pack header')
	# Fill array with vertex values
	arr[1:-1]['x'] = x
	arr[1:-1]['y'] = y

	# decide which points are connected by lines
	if eq(connect, 'all'):
		arr[1:-1]['c'] = 1
	elif eq(connect, 'pairs'):
		arr[1:-1]['c'][::2] = 1
		arr[1:-1]['c'][1::2] = 0
	elif eq(connect, 'finite'):
		arr[1:-1]['c'] = np.isfinite(x) & np.isfinite(y)
	elif isinstance(connect, np.ndarray):
		arr[1:-1]['c'] = connect
	else:
		raise Exception('connect argument must be "all", "pairs", "finite", or array')

	#profiler('fill array')
	# write last 0
	lastInd = 20*(n+1)
	byteview.data[lastInd:lastInd+4] = struct.pack('>i', 0)
	#profiler('footer')
	# create datastream object and stream into path

	## Avoiding this method because QByteArray(str) leaks memory in PySide
	#buf = QtCore.QByteArray(arr.data[12:lastInd+4])  # I think one unnecessary copy happens here

	path.strn = byteview.data[12:lastInd+4] # make sure data doesn't run away
	try:
		buf = QtCore.QByteArray.fromRawData(path.strn)
	except TypeError:
		buf = QtCore.QByteArray(bytes(path.strn))
	#profiler('create buffer')
	ds = QtCore.QDataStream(buf)

	ds >> path
	#profiler('load')

	return path
###
###

class MultiLine(QtWidgets.QGraphicsPathItem):
	def __init__(self, x, y, parent=None):
		"""x and y are 2D arrays of shape (Nplots, Nsamples)"""
		#super(QtWidgets.QGraphicsPathItem, self).__init__(parent)

		# abb removed
		#connect = np.ones(x.shape, dtype=bool)
		#connect[:,-1] = 0 # don't draw the segment between each trace
		#self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect.flatten())

		self.path = arrayToQPath(x.flatten(), y.flatten(), connect='all')
		QtWidgets.QGraphicsPathItem.__init__(self, self.path)
		#self.setPen(pg.mkPen('w'))

	'''
	def shape(self): # override because QGraphicsPathItem.shape is too expensive.
		print('MultiLine.shape() returning:', QtGui.QGraphicsItem.shape(self))
		return QtGui.QGraphicsItem.shape(self)
	'''

	'''
	def boundingRect(self):
		# was this
		print('MultiLine.boundingRect() returning:', self.path.boundingRect())
		return self.path.boundingRect()

		# this does nothing
		#PyQt5.QtCore.QRectF(0.0, -68.359375, 59.999950000000005, 120.849609375)
		# x, y, w, h ????
		#theRet = QtCore.QRectF(0, 0, 0, 0)
		#return theRet
	'''

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

class MainWindow(QtWidgets.QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)

		self.buildUI()

	def buildUI(self):
		self.centralwidget = QtWidgets.QWidget(self)
		self.centralwidget.setObjectName("centralwidget")

		self.myQVBoxLayout = QtWidgets.QVBoxLayout(self.centralwidget)

		#
		# toolbar
		self.toolbarWidget = myToolbarWidget()
		self.addToolBar(QtCore.Qt.LeftToolBarArea, self.toolbarWidget)

		#
		# tree view of files
		self.myTableWidget = QtWidgets.QTreeWidget()
		# append to layout
		self.myQVBoxLayout.addWidget(self.myTableWidget)

		#
		# dv/dt plot
		self.myGraphicsView = myQGraphicsView(plotThis='dvdt') #myQGraphicsView(self.centralwidget)
		self.myQVBoxLayout.addWidget(self.myGraphicsView)

		#
		# vm plot
		self.myGraphicsView = myQGraphicsView(plotThis='vm') #myQGraphicsView(self.centralwidget)
		self.myQVBoxLayout.addWidget(self.myGraphicsView)


		#
		# stat plot
		static_canvas = backend_qt5agg.FigureCanvas(mpl.figure.Figure(figsize=(5, 3)))
		self.myQVBoxLayout.addWidget(static_canvas)

		# i want the mpl toolbar in the mpl canvas or sublot
		# this is adding mpl toolbar to main window -->> not what I want
		#self.addToolBar(backend_qt5agg.NavigationToolbar2QT(static_canvas, self))
		# this kinda works as wanted, toolbar is inside mpl plot but it is FUCKING UGLY !!!!
		self.mplToolbar = backend_qt5agg.NavigationToolbar2QT(static_canvas, static_canvas)

		self._static_ax = static_canvas.figure.subplots()
		t = np.linspace(0, 10, 501)
		self._static_ax.plot(t, np.tan(t), ".")

		#
		# leave here, critical
		self.setCentralWidget(self.centralwidget)

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
		w.resize(640, 480)
		w.show()
		#sys.exit(app.exec_())
	except Exception as e:
		print(traceback.format_exc())
		#logging.error(traceback.format_exc())
		sys.exit(app.exec_())
		raise
	finally:
		sys.exit(app.exec_())
