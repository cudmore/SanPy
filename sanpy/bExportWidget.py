# Author: Robert H Cudmore
# Date: 20190722

import os, sys
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
	def __init__(self, ax, xPos, yPos, hLength=5, vLength=20, linewidth=3, color='k', doPick=False):
		self.ax = ax
		self.c = ax.get_figure().canvas

		self.hLineLength = hLength
		self.vLineLength = vLength

		# horz line
		x = [xPos, xPos+hLength]
		y = [yPos, yPos]
		self.hLine = matplotlib.lines.Line2D(x, y, linewidth=linewidth, c=color, picker=5)
		self.ax.add_line(self.hLine)

		# vert line
		x = [xPos, xPos]
		y = [yPos, yPos+vLength]
		self.vLine = matplotlib.lines.Line2D(x, y, linewidth=linewidth, c=color, picker=None)
		self.ax.add_line(self.vLine)

		self.c.draw_idle()
		self.sid = self.c.mpl_connect('pick_event', self.clickonline)

	def clickonline(self, event):
		print('clickonline()')
		if event.artist == self.hLine:
			print("  line selected ", event.artist)
			self.follower = self.c.mpl_connect("motion_notify_event", self.followmouse)
			self.releaser = self.c.mpl_connect("button_press_event", self.releaseonclick)

	def followmouse(self, event):
		print('followmouse()')
		self.hLine.set_ydata([event.ydata, event.ydata])
		self.hLine.set_xdata([event.xdata, event.xdata + self.hLineLength])
		# a second line print('Vline is vertical')
		self.vLine.set_xdata([event.xdata, event.xdata])
		self.vLine.set_ydata([event.ydata, event.ydata + self.vLineLength])

		self.c.draw_idle()

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
					parent=None):
		"""
		"""
		super(bExportWidget, self).__init__(parent)

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

		self.initUI()

		if xMin is not None and xMax is not None:
			self.myAxis.set_xlim(xMin, xMax)

	def closeEvent(self, event):
		"""
		in Qt, close only hides the widget!
		"""
		self.deleteLater()
		self.myCloseSignal.emit(self)

	def initUI(self):

		self.setGeometry(100, 100, 1000, 600)
		self.center()

		if self.path:
			windowTitle = os.path.split(self.path)[1]
			self.setWindowTitle('Raw Plot: ' + windowTitle)
		else:
			self.setWindowTitle('Raw Plot: ' + 'None')

		self.grid = QtWidgets.QGridLayout()
		self.setLayout(self.grid)

		col = 0
		# x min
		xMinLabel = QtWidgets.QLabel('X-Min')
		self.grid.addWidget(xMinLabel, 5, col)
		col += 1
		self.xMinSpinBox = QtWidgets.QDoubleSpinBox()
		self.xMinSpinBox.setSingleStep(0.1)
		self.xMinSpinBox.setMinimum(-1e6)
		self.xMinSpinBox.setMaximum(1e6)
		self.xMinSpinBox.setValue(0)
		self.xMinSpinBox.setKeyboardTracking(False)
		self.xMinSpinBox.valueChanged.connect(self._setXAxis)
		#self.lineWidthSpinBox.editingFinished.connect(self._setLineWidth)
		self.grid.addWidget(self.xMinSpinBox, 5, col)
		col += 1

		# x max
		xMaxLabel = QtWidgets.QLabel('X-Max')
		self.grid.addWidget(xMaxLabel, 5, col)
		col += 1
		self.xMaxSpinBox = QtWidgets.QDoubleSpinBox()
		self.xMaxSpinBox.setSingleStep(0.1)
		self.xMaxSpinBox.setMinimum(-1e6)
		self.xMaxSpinBox.setMaximum(1e6)
		self.xMaxSpinBox.setValue(self.mySweepX_Downsample[-1])
		self.xMaxSpinBox.setKeyboardTracking(False)
		self.xMaxSpinBox.valueChanged.connect(self._setXAxis)
		#self.lineWidthSpinBox.editingFinished.connect(self._setLineWidth)
		self.grid.addWidget(self.xMaxSpinBox, 5, col)
		col += 1

		# x axis
		self.xAxisCheckBox = QtWidgets.QCheckBox('X-Axis')
		self.xAxisCheckBox.setChecked(True)
		self.xAxisCheckBox.stateChanged.connect(self.xAxisToggle)
		self.grid.addWidget(self.xAxisCheckBox, 5, col)
		col += 1
		# y axis
		self.yAxisCheckBox = QtWidgets.QCheckBox('Y-Axis')
		self.yAxisCheckBox.setChecked(True)
		self.yAxisCheckBox.stateChanged.connect(self.yAxisToggle)
		self.grid.addWidget(self.yAxisCheckBox, 5, col)
		col += 1

		# line width
		lineWidthLabel = QtWidgets.QLabel('Line Width')
		self.grid.addWidget(lineWidthLabel, 5, col)
		col += 1
		self.lineWidthSpinBox = QtWidgets.QDoubleSpinBox()
		self.lineWidthSpinBox.setSingleStep(0.1)
		self.lineWidthSpinBox.setMinimum(0.01)
		self.lineWidthSpinBox.setMaximum(100.0)
		self.lineWidthSpinBox.setValue(0.5)
		self.lineWidthSpinBox.setKeyboardTracking(False)
		self.lineWidthSpinBox.valueChanged.connect(self._setLineWidth)
		#self.lineWidthSpinBox.editingFinished.connect(self._setLineWidth)
		self.grid.addWidget(self.lineWidthSpinBox, 5, col)
		col += 1

		# color
		colorList = ['red', 'green', 'blue', 'cyan', 'magenta', 'yellow', 'black', 'white']
		wIdx = colorList.index('white')
		kIdx = colorList.index('black')
		colorLabel = QtWidgets.QLabel('Line Color')
		self.grid.addWidget(colorLabel, 5, col)
		col += 1
		self.colorDropdown = QtWidgets.QComboBox()
		self.colorDropdown.addItems(colorList)
		self.colorDropdown.setCurrentIndex(wIdx if self.darkTheme else kIdx)
		self.colorDropdown.currentIndexChanged.connect(self._setLineColor)
		self.grid.addWidget(self.colorDropdown, 5, col)
		col += 1

		# downsample
		downsampleLabel = QtWidgets.QLabel('Downsample')
		self.grid.addWidget(downsampleLabel, 5, col)
		col += 1
		self.downSampleSpinBox = QtWidgets.QSpinBox()
		self.downSampleSpinBox.setSingleStep(1)
		self.downSampleSpinBox.setMinimum(1)
		self.downSampleSpinBox.setMaximum(200)
		self.downSampleSpinBox.setValue(1)
		self.downSampleSpinBox.setKeyboardTracking(False)
		self.downSampleSpinBox.valueChanged.connect(self._setDownSample)
		#self.downSampleSpinBox.editingFinished.connect(self._setDownSample)
		self.grid.addWidget(self.downSampleSpinBox, 5, col)
		col += 1

		# meadianFilter
		medianFilterLabel = QtWidgets.QLabel('Median Filter (points)')
		self.grid.addWidget(medianFilterLabel, 5, col)
		col += 1
		self.medianFilterSpinBox = QtWidgets.QSpinBox()
		#self.medianFilterSpinBox.setStyle(CustomStyle())
		self.medianFilterSpinBox.setSingleStep(2)
		self.medianFilterSpinBox.setMinimum(1)
		self.medianFilterSpinBox.setMaximum(1000)
		self.medianFilterSpinBox.setValue(1)
		self.medianFilterSpinBox.setKeyboardTracking(False)
		self.medianFilterSpinBox.valueChanged.connect(self._setDownSample)
		#self.medianFilterSpinBox.editingFinished.connect(self._setDownSample)
		self.grid.addWidget(self.medianFilterSpinBox, 5, col)
		col += 1

		# dark theme
		self.darkThemeCheckBox = QtWidgets.QCheckBox('Dark Theme')
		self.darkThemeCheckBox.setChecked(self.darkTheme)
		self.darkThemeCheckBox.stateChanged.connect(self._changeTheme)
		self.grid.addWidget(self.darkThemeCheckBox, 5, col)
		col += 1

		# save button
		'''
		saveButton = QtWidgets.QPushButton('Save', self)
		saveButton.resize(saveButton.sizeHint())
		saveButton.clicked.connect(self.save)
		self.grid.addWidget(saveButton, 5, col)
		col += 1
		'''

		self.figure = matplotlib.figure.Figure()
		self.canvas = FigureCanvas(self.figure)

		# set defaullt save name
		baseName = 'export'
		if self.path:
			baseName = os.path.splitext(self.path)[0]
		self.canvas.get_default_filename = lambda: f'{baseName}'

		# matplotlib navigation toolbar
		self.toolbar = NavigationToolbar(self.canvas, self)
		self.toolbar.zoom()

		self.numCol = col # as I add controls above, increment this
		self.grid.addWidget(self.toolbar, 2, 0, 1, self.numCol)
		self.grid.addWidget(self.canvas, 3, 0, 1, self.numCol)
		# self.grid.addWidget(self.toolbar, ??)

		self.myAxis = None
		self.plotRaw(firstPlot=True)

		self.show()

		#self.changeTheme()

	def _changeTheme(self):
		"""
		to change the theme, we need to redraw everything
		"""
		checked = self.darkThemeCheckBox.isChecked()

		# remove
		self.grid.removeWidget(self.toolbar)
		self.grid.removeWidget(self.canvas)

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
		self.toolbar.zoom()

		self.grid.addWidget(self.toolbar, 2, 0, 1, self.numCol)
		self.grid.addWidget(self.canvas, 3, 0, 1, self.numCol)
		# self.grid.addWidget(self.toolbar, ??)

		self.myAxis = None
		self.plotRaw(firstPlot=True)

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

	def _setXAxis(self):
		xMin = self.xMinSpinBox.value()
		xMax = self.xMaxSpinBox.value()

		self.myAxis.set_xlim(xMin, xMax)

	def _setDownSample(self):
		self.downSampleSpinBox.setEnabled(False)
		self.medianFilterSpinBox.setEnabled(False)

		try:
			downSample = self.downSampleSpinBox.value()
			medianFilter = self.medianFilterSpinBox.value()

			if (medianFilter % 2) == 0:
				medianFilter += 1

			print('_setDownSample() downSample:', downSample, 'medianFilter:', medianFilter)

			self.mySweepX_Downsample = self.mySweepX[::downSample]
			self.mySweepY_Downsample = self.mySweepY[::downSample]

			if medianFilter > 1:
				self.mySweepY_Downsample = scipy.signal.medfilt(self.mySweepY_Downsample,
											kernel_size=medianFilter)

			#
			self.plotRaw()
		except (Exception) as e:
			print('EXCEPTION in _setDownSample():', e)

		self.downSampleSpinBox.setEnabled(True)
		self.medianFilterSpinBox.setEnabled(True)

	def xAxisToggle(self):
		checked = self.xAxisCheckBox.isChecked()
		self._toggleAxis('bottom', checked)

	def yAxisToggle(self):
		checked = self.yAxisCheckBox.isChecked()
		self._toggleAxis('left', checked)

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

	def _setLineColor(self, colorStr):

		colorStr = self.colorDropdown.currentText()

		for line in self.myAxis.lines:
			line.set_color(colorStr)

		#
		self.canvas.draw()
		self.repaint()

	def _setLineWidth(self):
		lineWidth = self.lineWidthSpinBox.value()

		print('bExportWidget._setLineWidth() lineWidth:', lineWidth)

		for line in self.myAxis.lines:
			line.set_linewidth(lineWidth)

		#
		self.canvas.draw()
		self.repaint()

	def plotRaw(self, firstPlot=False):
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
			self.myAxis.plot(sweepX, sweepY, '-', c=color, linewidth=lineWidth) # fmt = '[marker][line][color]'
			self.myAxis.callbacks.connect('xlim_changed', self.on_xlims_change)

			'''
			if self.scaleBar is not None:
				hLength = 5
				vLength = 20
				scaleBarLineWidth = 5
				self.scaleBars = draggable_lines(self.myAxis, sweepX[-1], sweepY[-1], hLength=hLength, vLength=vLength, linewidth=scaleBarLineWidth, doPick=True)
			'''
			
		else:
			for line in self.myAxis.lines:
				print('plotRaw() is updating with set_xdata/set_ydata')
				line.set_xdata(sweepX)
				line.set_ydata(sweepY)

		if firstPlot:
			#self.myAxis.set_ylabel('Vm (mV)')
			#self.myAxis.set_xlabel('Time (sec)')
			self.myAxis.set_ylabel(self.xyUnits[1])
			self.myAxis.set_xlabel(self.xyUnits[0])

		self.canvas.draw_idle()
		self.repaint()

	def on_xlims_change(self, mplEvent):
		"""
		matplotlib callback
		"""
		xLim = mplEvent.get_xlim()
		print('on_xlims_change() xLim:', xLim)

		xMin = xLim[0]
		xMax = xLim[1]

		self.xMinSpinBox.setValue(xMin)
		self.xMaxSpinBox.setValue(xMax)

		self.canvas.draw_idle()

	def save(self):
		"""
		Save the current view to a pdf file
		"""

		# get min/max of x-axis
		'''
		[xMin, xMax] = self.myAxis.get_xlim()
		if xMin < 0:
			xMin = 0
		xMin = '%.2f'%(xMin)
		xMax = '%.2f'%(xMax)

		lhs, rhs = xMin.split('.')
		xMin = 'b' + lhs + '_' + rhs

		lhs, rhs = xMax.split('.')
		xMax = 'e' + lhs + '_' + rhs
		'''

		# construct a default save file name
		saveFilePath = ''
		if self.path:
			parentPath, filename = os.path.split(self.path)
			baseFilename, file_extension = os.path.splitext(filename)
			#saveFileName = baseFilename + '_' + xMin + '_' + xMax + '.pdf'
			saveFileName = baseFilename + '.svg'
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
		GUI = bExportWidget(sweepX, sweepY, path=path, xyUnits=xyUnits)
		GUI.show()

		sys.exit(app.exec_())
