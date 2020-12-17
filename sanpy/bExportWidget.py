# Author: Robert H Cudmore
# Date: 20190722

import os, sys
import numpy as np
import scipy.signal
from PyQt5 import QtWidgets, QtGui, QtCore
import matplotlib
import matplotlib.figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt # abb 202012 added to set theme

# abb 20200718
# needed to import from SanPy which is one folder up
#sys.path.append("..")

#from SanPy import bAnalysis
#from SanPy import bAnalysisPlot
#import bAnalysis
#import bAnalysisPlot
from sanpy import bAnalysis
#from sanpy import bAnalysisPlot

class CustomStyle(QtWidgets.QProxyStyle):
	def styleHint(self, hint, option=None, widget=None, returnData=None):
		if hint == QtWidgets.QStyle.SH_SpinBox_KeyPressAutoRepeatRate:
			return 10**10
		elif hint == QtWidgets.QStyle.SH_SpinBox_ClickAutoRepeatRate:
			return 10**10
		elif hint == QtWidgets.QStyle.SH_SpinBox_ClickAutoRepeatThreshold:
			# You can use only this condition to avoid the auto-repeat,
			# but better safe than sorry ;-)
			return 10**10
		else:
			return super().styleHint(hint, option, widget, returnData)

class draggable_lines:
	def __init__(self, ax, xPos, yPos,
					hLength=5, vLength=20,
					linewidth=3, color='k', doPick=False):
		self.ax = ax
		self.c = ax.get_figure().canvas

		self.xPos = xPos
		self.yPos = yPos

		self.hLineLength = hLength
		self.vLineLength = vLength

		# horz line (user can drag this)
		x = [xPos, xPos+hLength]
		y = [yPos, yPos]
		self.hLine, = self.ax.plot(x, y, '-',
								label='xScaleBar',
								linewidth=linewidth, c=color,
								clip_on = False,
								picker=5)
		'''
		self.hLine = matplotlib.lines.Line2D(x, y, label='xScaleBar',
								marker=None,
								linewidth=linewidth, c=color,
								clip_on = False,
								picker=5)
		self.ax.add_line(self.hLine)
		'''

		# vert line
		x = [xPos, xPos]
		y = [yPos, yPos+vLength]
		self.vLine, = self.ax.plot(x, y, '-',
								label='yScaleBar',
								linewidth=linewidth, c=color,
								clip_on = False,
								picker=None)
		'''
		self.vLine = matplotlib.lines.Line2D(x, y, label='yScaleBar',
								marker=None,
								linewidth=linewidth, c=color,
								clip_on = False,
								picker=None)
		self.ax.add_line(self.vLine)
		'''

		self.c.draw_idle()
		self.sid = self.c.mpl_connect('pick_event', self.clickonline)

	def clickonline(self, event):
		print('clickonline()')
		if event.artist == self.hLine:
			print("  line selected ", event.artist)
			self.follower = self.c.mpl_connect("motion_notify_event", self.followmouse)
			#self.releaser = self.c.mpl_connect("button_press_event", self.releaseonclick)
			self.releaser = self.c.mpl_connect("button_release_event", self.releaseonclick)

	def hideScaleBar(self, xChecked, yChecked):
		xPos = np.nan
		yPos = np.nan

		if xChecked:
			self.hLine.set_ydata([self.yPos, self.yPos])
			self.hLine.set_xdata([self.xPos, self.xPos + self.hLineLength])
		else:
			self.hLine.set_ydata([yPos, yPos])
			self.hLine.set_xdata([xPos, xPos + self.hLineLength])

		# a second line print('Vline is vertical')
		if yChecked:
			self.vLine.set_xdata([self.xPos, self.xPos])
			self.vLine.set_ydata([self.yPos, self.yPos + self.vLineLength])
		else:
			self.vLine.set_xdata([xPos, xPos])
			self.vLine.set_ydata([yPos, yPos + self.vLineLength])

		self.c.draw_idle()

	def setWidthHeight(self, width=None, height=None):
		"""
		set the size (width/height) of a scale bar
		"""
		if width is not None:
			self.hLineLength = width
		if height is not None:
			self.vLineLength = height

		# refresh
		self.setPos()

	def setThickness(self, thickness):
		self.hLine.set_linewidth(thickness)
		self.vLine.set_linewidth(thickness)

	def setPos(self, xPos=None, yPos=None, fromMax=False):
		"""
		use this while (i) user-drag and (2) set x/y scale

		fromMax: USe this when setting from x/y axes max and we will shift position

		"""
		#print('draggable_lines.setPos()', 'xPos:', xPos, 'yPos:', yPos, 'fromMax:', fromMax)

		if xPos is None:
			pass
			#xPos = self.xPos
		else:
			if fromMax:
				self.xPos = xPos - 1.5 * self.hLineLength
			else:
				self.xPos = xPos
		if yPos is None:
			pass
			#yPos = self.yPos
		else:
			if fromMax:
				self.yPos = yPos - 1.5 * self.vLineLength
			else:
				self.yPos = yPos

		xPos = self.xPos
		yPos = self.yPos

		#print('  xPos:', xPos, 'yPos:', yPos)

		self.hLine.set_ydata([yPos, yPos])
		self.hLine.set_xdata([xPos, xPos + self.hLineLength])
		# a second line print('Vline is vertical')
		self.vLine.set_xdata([xPos, xPos])
		self.vLine.set_ydata([yPos, yPos + self.vLineLength])

		self.c.draw_idle()

	def followmouse(self, event):
		#print('followmouse()')
		self.setPos(event.xdata, event.ydata)

	def releaseonclick(self, event):
		print('releaseonclick()')
		self.c.mpl_disconnect(self.releaser)
		self.c.mpl_disconnect(self.follower)

class bExportWidget(QtWidgets.QWidget):
	"""
	Open a window and display the raw Vm of a bAnalysis abf file
	"""

	myCloseSignal = QtCore.Signal(object)

	def __init__(self, sweepX, sweepY, xyUnits=('',''), path='',
					darkTheme=False,
					xMin=None,
					xMax=None,
					xMargin=2,
					type='vm', # (vm, dvdt, meanclip)
					parent=None):
		"""
		"""
		super(bExportWidget, self).__init__(parent)

		self.setFont(QtGui.QFont("Helvetica", 11, QtGui.QFont.Normal, italic=False))

		self.myType = type # use this to size defaults for scale bar
		self.myParent = parent

		self.mySweepX = sweepX
		self.mySweepY = sweepY
		self.mySweepX_Downsample = self.mySweepX
		self.mySweepY_Downsample = self.mySweepY

		#okGo = self.setFile(file)
		self.path = path
		self.xyUnits = xyUnits

		self.darkTheme = darkTheme

		if self.darkTheme:
			plt.style.use('dark_background')
		else:
			plt.rcParams.update(plt.rcParamsDefault)

		self.scaleBarDict = {}
		self.scaleBarDict['hLength'] = 5
		self.scaleBarDict['vLength'] = 20
		self.scaleBarDict['lineWidth'] = 5
		if self.darkTheme:
			self.scaleBarDict['color'] = 'w'
		else:
			self.scaleBarDict['color'] = 'k'
		if self.myType == 'vm':
			self.scaleBarDict['hLength'] = 1 # second
			self.scaleBarDict['vLength'] = 20 # mv
		elif self.myType == 'dvdt':
			self.scaleBarDict['hLength'] = 1 # secon
			self.scaleBarDict['vLength'] = 10
		elif self.myType == 'meanclip':
			self.scaleBarDict['hLength'] = 5 # ms
			self.scaleBarDict['vLength'] = 20 # mv

		self.xMargin = xMargin # seconds
		self.internalUpdate = False

		self.initUI()

		if xMin is not None and xMax is not None:
			pass
			#self.xMin = xMin
			#self.xMax = xMax
		else:
			xMin = np.nanmin(self.mySweepX_Downsample)
			xMax = np.nanmax(self.mySweepX_Downsample)
		#
		self.myAxis.set_xlim(xMin, xMax)
		#self._setXAxis(xMin, xMax)

	def closeEvent(self, event):
		"""
		in Qt, close only hides the widget!
		"""
		self.deleteLater()
		self.myCloseSignal.emit(self)

	def initUI(self):

		#self.setGeometry(100, 100, 1000, 600)
		self.center()

		if self.path:
			windowTitle = os.path.split(self.path)[1]
			self.setWindowTitle('Raw Plot: ' + windowTitle)
		else:
			self.setWindowTitle('Raw Plot: ' + 'None')

		myAlignLeft = QtCore.Qt.AlignLeft
		myAlignTop = QtCore.Qt.AlignTop

		hMasterLayout = QtWidgets.QHBoxLayout()
		hMasterLayout.setAlignment(QtCore.Qt.AlignTop)
		self.setLayout(hMasterLayout)

		left_container = QtWidgets.QWidget(self)
		left_container.setFixedWidth(300)

		hMasterLayout.addWidget(left_container, myAlignTop)

		vBoxLayout = QtWidgets.QVBoxLayout(left_container) # VBox for controls
		vBoxLayout.setAlignment(QtCore.Qt.AlignTop)

		hBoxRow0 = QtWidgets.QHBoxLayout()
		vBoxLayout.addLayout(hBoxRow0, myAlignTop)

		#
		# first row of controls

		# x axis on/off (todo: does not need self)
		self.xAxisCheckBox = QtWidgets.QCheckBox('')
		self.xAxisCheckBox.setToolTip('Toggle X-Axis Labels')
		self.xAxisCheckBox.setChecked(True)
		self.xAxisCheckBox.stateChanged.connect(self.xAxisToggle)
		hBoxRow0.addWidget(self.xAxisCheckBox, myAlignLeft)

		# x min
		xMinLabel = QtWidgets.QLabel('X-Min')
		hBoxRow0.addWidget(xMinLabel, myAlignLeft)
		self.xMinSpinBox = QtWidgets.QDoubleSpinBox()
		self.xMinSpinBox.setToolTip('X-Axis Minimum')
		self.xMinSpinBox.setSingleStep(0.1)
		self.xMinSpinBox.setMinimum(-1e6)
		self.xMinSpinBox.setMaximum(1e6)
		self.xMinSpinBox.setValue(0)
		self.xMinSpinBox.setKeyboardTracking(False)
		self.xMinSpinBox.valueChanged.connect(self._setXAxis)
		#self.lineWidthSpinBox.editingFinished.connect(self._setLineWidth)
		hBoxRow0.addWidget(self.xMinSpinBox, myAlignLeft)

		# x max
		xMaxLabel = QtWidgets.QLabel('X-Max')
		hBoxRow0.addWidget(xMaxLabel, myAlignLeft)
		self.xMaxSpinBox = QtWidgets.QDoubleSpinBox()
		self.xMaxSpinBox.setToolTip('X-Axis Maximum')
		self.xMaxSpinBox.setSingleStep(0.1)
		self.xMaxSpinBox.setMinimum(-1e6)
		self.xMaxSpinBox.setMaximum(1e6)
		self.xMaxSpinBox.setValue(self.mySweepX_Downsample[-1])
		self.xMaxSpinBox.setKeyboardTracking(False)
		self.xMaxSpinBox.valueChanged.connect(self._setXAxis)
		#self.lineWidthSpinBox.editingFinished.connect(self._setLineWidth)
		hBoxRow0.addWidget(self.xMaxSpinBox, myAlignLeft)

		#
		# second row
		hBoxRow1 = QtWidgets.QHBoxLayout()
		vBoxLayout.addLayout(hBoxRow1)

		# y axis
		self.yAxisCheckBox = QtWidgets.QCheckBox('')
		self.yAxisCheckBox.setToolTip('Toggle Y-Axis Labels')
		self.yAxisCheckBox.setChecked(True)
		self.yAxisCheckBox.stateChanged.connect(self.yAxisToggle)
		hBoxRow1.addWidget(self.yAxisCheckBox)

		# y min
		yMinLabel = QtWidgets.QLabel('Y-Min')
		hBoxRow1.addWidget(yMinLabel)
		yMinValue = np.nanmin(self.mySweepY_Downsample)
		self.yMinSpinBox = QtWidgets.QDoubleSpinBox()
		self.yMinSpinBox.setSingleStep(0.1)
		self.yMinSpinBox.setMinimum(-1e6)
		self.yMinSpinBox.setMaximum(1e6)
		self.yMinSpinBox.setValue(yMinValue) # flipped
		self.yMinSpinBox.setKeyboardTracking(False)
		self.yMinSpinBox.valueChanged.connect(self._setYAxis)
		#self.lineWidthSpinBox.editingFinished.connect(self._setLineWidth)
		hBoxRow1.addWidget(self.yMinSpinBox)

		# y max
		yMaxLabel = QtWidgets.QLabel('Y-Max')
		hBoxRow1.addWidget(yMaxLabel)
		yMaxValue = np.nanmax(self.mySweepY_Downsample)
		self.yMaxSpinBox = QtWidgets.QDoubleSpinBox()
		self.yMaxSpinBox.setSingleStep(0.1)
		self.yMaxSpinBox.setMinimum(-1e6)
		self.yMaxSpinBox.setMaximum(1e6)
		self.yMaxSpinBox.setValue(yMaxValue) # flipped
		self.yMaxSpinBox.setKeyboardTracking(False)
		self.yMaxSpinBox.valueChanged.connect(self._setYAxis)
		#self.lineWidthSpinBox.editingFinished.connect(self._setLineWidth)
		hBoxRow1.addWidget(self.yMaxSpinBox)

		#
		# third row
		hBoxRow2 = QtWidgets.QHBoxLayout()
		vBoxLayout.addLayout(hBoxRow2)

		# x margin
		xMaxLabel = QtWidgets.QLabel('X-Margin')
		hBoxRow2.addWidget(xMaxLabel)
		self.xMarginSpinBox = QtWidgets.QDoubleSpinBox()
		self.xMarginSpinBox.setToolTip('X-Axis Maximum')
		self.xMarginSpinBox.setSingleStep(0.1)
		self.xMarginSpinBox.setMinimum(0)
		self.xMarginSpinBox.setMaximum(1e6)
		self.xMarginSpinBox.setValue(self.xMargin)
		self.xMarginSpinBox.setKeyboardTracking(False)
		self.xMarginSpinBox.valueChanged.connect(self._setXMargin)
		#self.lineWidthSpinBox.editingFinished.connect(self._setLineWidth)
		hBoxRow2.addWidget(self.xMarginSpinBox)

		#
		# fourth row
		hBoxRow3 = QtWidgets.QHBoxLayout()
		vBoxLayout.addLayout(hBoxRow3)

		# line width
		lineWidthLabel = QtWidgets.QLabel('Line Width')
		hBoxRow3.addWidget(lineWidthLabel)
		self.lineWidthSpinBox = QtWidgets.QDoubleSpinBox()
		self.lineWidthSpinBox.setSingleStep(0.1)
		self.lineWidthSpinBox.setMinimum(0.01)
		self.lineWidthSpinBox.setMaximum(100.0)
		self.lineWidthSpinBox.setValue(0.5)
		self.lineWidthSpinBox.setKeyboardTracking(False)
		self.lineWidthSpinBox.valueChanged.connect(self._setLineWidth)
		#self.lineWidthSpinBox.editingFinished.connect(self._setLineWidth)
		hBoxRow3.addWidget(self.lineWidthSpinBox)

		# color
		colorList = ['red', 'green', 'blue', 'cyan', 'magenta', 'yellow', 'black', 'white']
		wIdx = colorList.index('white')
		kIdx = colorList.index('black')
		colorLabel = QtWidgets.QLabel('Line Color')
		hBoxRow3.addWidget(colorLabel)
		self.colorDropdown = QtWidgets.QComboBox()
		self.colorDropdown.addItems(colorList)
		self.colorDropdown.setCurrentIndex(wIdx if self.darkTheme else kIdx)
		self.colorDropdown.currentIndexChanged.connect(self._setLineColor)
		hBoxRow3.addWidget(self.colorDropdown)

		#
		# fifth row
		hBoxRow4 = QtWidgets.QHBoxLayout()
		vBoxLayout.addLayout(hBoxRow4)

		# downsample
		downsampleLabel = QtWidgets.QLabel('Downsample')
		hBoxRow4.addWidget(downsampleLabel)
		self.downSampleSpinBox = QtWidgets.QSpinBox()
		self.downSampleSpinBox.setSingleStep(1)
		self.downSampleSpinBox.setMinimum(1)
		self.downSampleSpinBox.setMaximum(200)
		self.downSampleSpinBox.setValue(1)
		self.downSampleSpinBox.setKeyboardTracking(False)
		self.downSampleSpinBox.valueChanged.connect(self._setDownSample)
		#self.downSampleSpinBox.editingFinished.connect(self._setDownSample)
		hBoxRow4.addWidget(self.downSampleSpinBox)

		# meadianFilter
		medianFilterLabel = QtWidgets.QLabel('Median Filter (points)')
		hBoxRow4.addWidget(medianFilterLabel)
		self.medianFilterSpinBox = QtWidgets.QSpinBox()
		#self.medianFilterSpinBox.setStyle(CustomStyle())
		self.medianFilterSpinBox.setSingleStep(2)
		self.medianFilterSpinBox.setMinimum(1)
		self.medianFilterSpinBox.setMaximum(1000)
		self.medianFilterSpinBox.setValue(1)
		self.medianFilterSpinBox.setKeyboardTracking(False)
		self.medianFilterSpinBox.valueChanged.connect(self._setDownSample)
		#self.medianFilterSpinBox.editingFinished.connect(self._setDownSample)
		hBoxRow4.addWidget(self.medianFilterSpinBox)

		#
		# fifth row
		hBoxRow4_5 = QtWidgets.QHBoxLayout()
		vBoxLayout.addLayout(hBoxRow4_5, myAlignTop)

		# dark theme
		self.darkThemeCheckBox = QtWidgets.QCheckBox('Dark Theme')
		self.darkThemeCheckBox.setChecked(self.darkTheme)
		self.darkThemeCheckBox.stateChanged.connect(self._changeTheme)
		hBoxRow4_5.addWidget(self.darkThemeCheckBox)

		#
		# sixth row
		scaleBarGroupBox = QtWidgets.QGroupBox('Scale Bar')
		vBoxLayout.addWidget(scaleBarGroupBox, myAlignTop)

		gridBoxScaleBar = QtWidgets.QGridLayout()
		scaleBarGroupBox.setLayout(gridBoxScaleBar)

		hLength = self.scaleBarDict['hLength']
		vLength = self.scaleBarDict['vLength']
		lineWidth = self.scaleBarDict['lineWidth']

		# scale bar width (length)
		scaleBarWidthLabel = QtWidgets.QLabel('Width')
		gridBoxScaleBar.addWidget(scaleBarWidthLabel, 0, 0)
		self.scaleBarWidthSpinBox = QtWidgets.QDoubleSpinBox()
		self.scaleBarWidthSpinBox.setToolTip('X Scale Bar Width (0 to remove)')
		self.scaleBarWidthSpinBox.setSingleStep(0.1)
		self.scaleBarWidthSpinBox.setMinimum(-1e6)
		self.scaleBarWidthSpinBox.setMaximum(1e6)
		self.scaleBarWidthSpinBox.setValue(hLength)
		self.scaleBarWidthSpinBox.setKeyboardTracking(False)
		self.scaleBarWidthSpinBox.valueChanged.connect(self._setScaleBarSize)
		#self.lineWidthSpinBox.editingFinished.connect(self._setLineWidth)
		gridBoxScaleBar.addWidget(self.scaleBarWidthSpinBox, 0, 1)

		# scale bar height (length)
		scaleBarHeightLabel = QtWidgets.QLabel('Height')
		gridBoxScaleBar.addWidget(scaleBarHeightLabel, 1, 0)
		self.scaleBarHeightSpinBox = QtWidgets.QDoubleSpinBox()
		self.scaleBarHeightSpinBox.setToolTip('Y Scale Bar Height (0 to remove)')
		self.scaleBarHeightSpinBox.setSingleStep(0.1)
		self.scaleBarHeightSpinBox.setMinimum(-1e6)
		self.scaleBarHeightSpinBox.setMaximum(1e6)
		self.scaleBarHeightSpinBox.setValue(vLength)
		self.scaleBarHeightSpinBox.setKeyboardTracking(False)
		self.scaleBarHeightSpinBox.valueChanged.connect(self._setScaleBarSize)
		#self.lineWidthSpinBox.editingFinished.connect(self._setLineWidth)
		gridBoxScaleBar.addWidget(self.scaleBarHeightSpinBox, 1, 1)

		# scale bar line thickness
		scaleBarThicknessLabel = QtWidgets.QLabel('Thickness')
		gridBoxScaleBar.addWidget(scaleBarThicknessLabel, 2, 0)
		self.scaleBarThicknessSpinBox = QtWidgets.QDoubleSpinBox()
		self.scaleBarThicknessSpinBox.setToolTip('Scale Bar Thickness')
		self.scaleBarThicknessSpinBox.setSingleStep(1)
		self.scaleBarThicknessSpinBox.setMinimum(0.1)
		self.scaleBarThicknessSpinBox.setMaximum(1e6)
		self.scaleBarThicknessSpinBox.setValue(lineWidth)
		self.scaleBarThicknessSpinBox.setKeyboardTracking(False)
		self.scaleBarThicknessSpinBox.valueChanged.connect(self._setScaleBarThickness)
		gridBoxScaleBar.addWidget(self.scaleBarThicknessSpinBox, 2, 1)

		# save button
		saveButton = QtWidgets.QPushButton('Save', self)
		saveButton.resize(saveButton.sizeHint())
		saveButton.clicked.connect(self.save)
		vBoxLayout.addWidget(saveButton)

		self.figure = matplotlib.figure.Figure()
		self.canvas = FigureCanvas(self.figure)

		# set defaullt save name
		baseName = 'export'
		if self.path:
			baseName = os.path.splitext(self.path)[0]
		self.canvas.get_default_filename = lambda: f'{baseName}'

		# matplotlib navigation toolbar
		self.toolbar = NavigationToolbar(self.canvas, self)
		#self.toolbar.zoom()

		# need self. here to set theme
		self.plotVBoxLayout = QtWidgets.QVBoxLayout()
		self.plotVBoxLayout.addWidget(self.toolbar)
		self.plotVBoxLayout.addWidget(self.canvas)

		hMasterLayout.addLayout(self.plotVBoxLayout) #, stretch=8)

		#self.myAxis = None
		self.plotRaw(firstPlot=True)

		self.show()

	def _changeTheme(self):
		"""
		to change the theme, we need to redraw everything
		"""
		checked = self.darkThemeCheckBox.isChecked()

		# get x/y axes limits
		xMin, xMax = self.myAxis.get_xlim()
		yMin, yMax = self.myAxis.get_ylim()

		# remove
		self.plotVBoxLayout.removeWidget(self.toolbar)
		self.plotVBoxLayout.removeWidget(self.canvas)

		self.toolbar.setParent(None)
		self.canvas.setParent(None)

		self.figure = None # ???
		self.toolbar = None
		self.canvas = None

		#self.canvas.draw()
		#self.repaint()

		# set theme
		if checked:
			plt.style.use('dark_background')
			self.darkTheme = True
		else:
			plt.rcParams.update(plt.rcParamsDefault)
			self.darkTheme = False

		self.figure = matplotlib.figure.Figure()
		self.canvas = FigureCanvas(self.figure)

		# matplotlib navigation toolbar
		self.toolbar = NavigationToolbar(self.canvas, self)
		#self.toolbar.zoom()

		self.plotVBoxLayout.addWidget(self.toolbar)
		self.plotVBoxLayout.addWidget(self.canvas)
		# self.grid.addWidget(self.toolbar, ??)

		if self.darkTheme:
			self.scaleBarDict['color'] = 'w'
		else:
			self.scaleBarDict['color'] = 'k'

		#self.myAxis = None
		self.plotRaw(firstPlot=True)

		# restore original x/y axes
		self.myAxis.set_xlim(xMin, xMax)
		self.myAxis.set_ylim(yMin, yMax)

	def old_setFile(self, filePath, plotRaw=False):
		"""
		when main application changes file
		"""
		if not os.path.isfile(filePath):
			print('bExportWidget.setFile did not find path:', filePath)
			return False

		self.filePath = filePath
		self.ba = bAnalysis(filePath)
		if self.ba.loadError:
			print('there was an error loading file', filePath)
			return False

		self.mySweepX = self.ba.abf.sweepX
		self.mySweepY = self.ba.abf.sweepY

		self.mySweepX_Downsample = self.ba.abf.sweepX
		self.mySweepY_Downsample = self.ba.abf.sweepY

		if plotRaw:
			self.plotRaw()
		return True

	def _setXMargin(self):
		self.xMargin = self.xMarginSpinBox.value()

		self.plotRaw()

	def _setXAxis(self):
		"""
		called when user sets values in x spin boxes
		see: on_xlim_change
		"""
		xMin = self.xMinSpinBox.value()
		xMax = self.xMaxSpinBox.value()

		xMin -= self.xMargin
		xMax += self.xMargin

		self.internalUpdate = True
		self.myAxis.set_xlim(xMin, xMax)
		self.internalUpdate = False

		self.scaleBars.setPos(xPos=xMax, fromMax=True)

		#self.plotRaw(xMin=xMin, xMax=xMax)
		self.plotRaw()

	def _setYAxis(self):
		"""
		called when user sets values in y spin boxes
		see: on_xlim_change
		"""
		yMin = self.yMinSpinBox.value()
		yMax = self.yMaxSpinBox.value()

		self.myAxis.set_ylim(yMin, yMax)

		self.scaleBars.setPos(yPos=yMax, fromMax=True)

	def on_xlims_change(self, mplEvent):
		"""
		matplotlib callback
		"""

		if self.internalUpdate:
			return

		xLim = mplEvent.get_xlim()
		print('on_xlims_change() xLim:', xLim)

		xMin = xLim[0]
		xMax = xLim[1]

		self.xMinSpinBox.setValue(xMin)
		self.xMaxSpinBox.setValue(xMax)

		self.plotRaw()

		#self.canvas.draw_idle()

	def _setDownSample(self):
		self.downSampleSpinBox.setEnabled(False)
		self.medianFilterSpinBox.setEnabled(False)

		try:
			downSample = self.downSampleSpinBox.value()
			medianFilter = self.medianFilterSpinBox.value()

			if (medianFilter % 2) == 0:
				medianFilter += 1

			print('_setDownSample() downSample:', downSample, 'medianFilter:', medianFilter)

			print('downSample ... please wait')
			self.mySweepX_Downsample = self.mySweepX[::downSample]
			self.mySweepY_Downsample = self.mySweepY[::downSample]

			if medianFilter > 1:
				print('medianFilter ... please wait')
				self.mySweepY_Downsample = scipy.signal.medfilt(self.mySweepY_Downsample,
											kernel_size=medianFilter)

			#
			self.plotRaw()

			# refresh scale-bar
			xPos = self.mySweepX_Downsample[-1]
			yPos = np.nanmax(self.mySweepY_Downsample)
			#self.scaleBars.setPos(xPos, yPos, fromMax=True)

		except (Exception) as e:
			print('EXCEPTION in _setDownSample():', e)

		self.downSampleSpinBox.setEnabled(True)
		self.medianFilterSpinBox.setEnabled(True)
		self.repaint()

	def xAxisToggle(self):
		checked = self.xAxisCheckBox.isChecked()
		self._toggleAxis('bottom', checked)

	def yAxisToggle(self):
		checked = self.yAxisCheckBox.isChecked()
		self._toggleAxis('left', checked)

	def scaleBarToggle(self):
		xChecked = self.xScaleBarCheckBox.isChecked()
		yChecked = self.yScaleBarCheckBox.isChecked()
		self._toggleScaleBar(xChecked, yChecked)

	def _setScaleBarSize(self):
		width = self.scaleBarWidthSpinBox.value()
		height = self.scaleBarHeightSpinBox.value()
		self.scaleBars.setWidthHeight(width=width, height=height)
		#
		self.canvas.draw()
		self.repaint()

	def _setScaleBarThickness(self):
		thickness = self.scaleBarThicknessSpinBox.value()
		self.scaleBars.setThickness(thickness)
		#
		self.canvas.draw()
		self.repaint()

	def _toggleAxis(self, leftBottom, onOff):
		if leftBottom == 'bottom':
			self.myAxis.get_xaxis().set_visible(onOff)
			self.myAxis.spines['bottom'].set_visible(onOff)
		elif leftBottom == 'left':
			self.myAxis.get_yaxis().set_visible(onOff)
			self.myAxis.spines['left'].set_visible(onOff)
		#
		self.canvas.draw()
		self.repaint()

	def _toggleScaleBar(self, xChecked, yChecked):
		self.scaleBars.hideScaleBar(xChecked, yChecked)

	def _setLineColor(self, colorStr):

		colorStr = self.colorDropdown.currentText()

		self.myTraceLine.set_color(colorStr)
		'''
		for line in self.myAxis.lines:
			print('_setLineColor:', line.get_label())
			line.set_color(colorStr)
		'''

		#
		self.canvas.draw()
		self.repaint()

	def _setLineWidth(self):
		lineWidth = self.lineWidthSpinBox.value()

		print('bExportWidget._setLineWidth() lineWidth:', lineWidth)

		self.myTraceLine.set_linewidth(lineWidth)
		'''
		for line in self.myAxis.lines:
			line.set_linewidth(lineWidth)
		'''
		#
		self.canvas.draw()
		self.repaint()

	def plotRaw(self, xMin=None, xMax=None, firstPlot=False):
		if firstPlot:
			self.figure.clf()
			self.myAxis = self.figure.add_subplot(111)

			self.myAxis.spines['right'].set_visible(False)
			self.myAxis.spines['top'].set_visible(False)

			if self.darkTheme:
				color = 'w'
			else:
				color = 'k'

			lineWidth = self.lineWidthSpinBox.value()

		#bAnalysisPlot.bPlot.plotRaw(self.ba, ax=self.myAxis, color=color, lineWidth=lineWidth)
		#sweepX = self.ba.abf.sweepX
		#sweepY = self.ba.abf.sweepX
		sweepX = self.mySweepX_Downsample
		sweepY = self.mySweepY_Downsample

		if firstPlot:
			xMinOrig = sweepX[0]
			xMaxOrig = sweepX[-1]
		else:
			xMinOrig, xMaxOrig = self.myAxis.get_xlim()

		yMinOrig = np.nanmin(sweepY)
		yMaxOrig = np.nanmax(sweepY)

		xClip = self.xMargin

		#self.myAxis.margins(x=0.5)

		if xMin is not None and xMax is not None:
			minClip = xMin + xClip
			maxClip = xMax - xClip
		else:
			minClip = xMinOrig + xClip
			maxClip = xMaxOrig - xClip

		sweepX = np.ma.masked_where( (sweepX<minClip), sweepX)
		sweepY = np.ma.masked_where( (sweepX<minClip), sweepY)

		sweepX = np.ma.masked_where( (sweepX>maxClip), sweepX)
		sweepY = np.ma.masked_where( (sweepX>maxClip), sweepY)

		if firstPlot:
			# using label 'myTrace' to differentiate from x/y scale bar
			self.myTraceLine, = self.myAxis.plot(sweepX, sweepY,
									'-', # fmt = '[marker][line][color]'
									c=color, linewidth=lineWidth,
									label='myTrace')
			#matplotlib.lines.Line2D

			self.myAxis.callbacks.connect('xlim_changed', self.on_xlims_change)

			# scale bar
			hLength = self.scaleBarDict['hLength']
			vLength = self.scaleBarDict['vLength']
			scaleBarLineWidth = self.scaleBarDict['lineWidth']
			scaleBarColor = self.scaleBarDict['color']
			xPos = xMaxOrig #sweepX[-1]
			yPos = yMaxOrig #np.nanmax(sweepY)
			self.scaleBars = draggable_lines(self.myAxis, xPos, yPos,
								hLength=hLength, vLength=vLength,
								linewidth=scaleBarLineWidth,
								color=scaleBarColor,
								doPick=True)
			self.scaleBars.setPos(xPos, yPos, fromMax=True)

		else:
			self.myTraceLine.set_xdata(sweepX)
			self.myTraceLine.set_ydata(sweepY)
			'''
			for line in self.myAxis.lines:
				print('plotRaw() is updating with set_xdata/set_ydata')
				line.set_xdata(sweepX)
				line.set_ydata(sweepY)
			'''

		if firstPlot:
			#self.myAxis.set_ylabel('Vm (mV)')
			#self.myAxis.set_xlabel('Time (sec)')
			self.myAxis.set_ylabel(self.xyUnits[1])
			self.myAxis.set_xlabel(self.xyUnits[0])

		self.canvas.draw_idle()
		self.repaint()

	def save(self):
		"""
		Save the current view to a pdf file
		"""

		# get min/max of x-axis
		[xMin, xMax] = self.myAxis.get_xlim()
		#if xMin < 0:
		#	xMin = 0
		xMin = '%.2f'%(xMin)
		xMax = '%.2f'%(xMax)

		lhs, rhs = xMin.split('.')
		xMin = 'b' + lhs + '_' + rhs

		lhs, rhs = xMax.split('.')
		xMax = 'e' + lhs + '_' + rhs

		# construct a default save file name
		saveFilePath = ''
		if self.path:
			parentPath, filename = os.path.split(self.path)
			baseFilename, file_extension = os.path.splitext(filename)
			#saveFileName = baseFilename + '_' + self.myType + '_' + xMin + '_' + xMax + '.svg'
			saveFileName = f'{baseFilename}_{self.myType}_{xMin}_{xMax}.svg'
			#saveFileName = baseFilename + '.svg'
			saveFilePath = os.path.join(parentPath,saveFileName)

		# file save dialog
		#fullSavePath, ignore = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', saveFilePath, "pdf Files (*.pdf)")
		fullSavePath, ignore = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', saveFilePath)

		# do actual save
		if len(fullSavePath) > 0:
			print('saving:', fullSavePath)
			self.figure.savefig(fullSavePath)

	def center(self):
		"""
		Center the window on the screen
		"""
		qr = self.frameGeometry()
		cp = QtWidgets.QDesktopWidget().availableGeometry().center()
		qr.moveCenter(cp)
		self.move(qr.topLeft())

if __name__ == '__main__':
	path = '../data/19114001.abf'

	ba = bAnalysis(path)
	if ba.loadError:
		print('there was an error loading file', path)
	else:
		app = QtWidgets.QApplication(sys.argv)
		app.aboutToQuit.connect(app.deleteLater)

		sweepX = ba.abf.sweepX
		sweepY = ba.abf.sweepY
		xyUnits = ('Time (sec)', 'Vm (mV)')
		type = 'vm'
		GUI = bExportWidget(sweepX, sweepY, path=path, xyUnits=xyUnits, type=type)
		GUI.show()

		sys.exit(app.exec_())
