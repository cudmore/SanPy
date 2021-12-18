"""
GUI for real-time and offline analysis
"""
import os, sys, time
from functools import partial

from datetime import datetime

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtWidgets, QtGui

import seaborn as sns

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends import backend_qt5agg

import qdarkstyle

# turn off qdarkstyle logging
import logging
logging.getLogger('qdarkstyle').setLevel(logging.WARNING)

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

from colinAnalysis import bAnalysis2
from colinAnalysis import colinAnalysis2  # list of abf from folder path
from stochAnalysis import plotRaw
from stochAnalysis import plotHist
from stochAnalysis import plotPhaseHist
from stochAnalysis import detect
from stochAnalysis import plotStimFileParams

class stochGui(QtWidgets.QMainWindow):
	"""
	Main window interface to show (file list, raw plot, stats table).
	"""

	signalLoadDroppedFile = QtCore.pyqtSignal(str)
	"""Emit when a file is dropped."""

	def __init__(self, parent=None):
		super(stochGui, self).__init__(parent)

		self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
		#sns.set(style="ticks", context="talk")
		plt.style.use("dark_background")

		self._initGui()

	def dragEnterEvent(self, e):
		"""
		Respond to user dragging a file over interface.

		This function is inherited from PyQt.

		Args:
			e (QDragEnterEvent):
		"""
		acceptedFileTypes = ['.abf']  # list of accepted file extensions

		text = e.mimeData().text()
		text = text.rstrip()  # strip trailing characters

		filePath, fileExt = os.path.splitext(text)
		if fileExt in acceptedFileTypes:
			e.accept()

	def dropEvent(self, e):
		"""
		Respond when user actually drops a drag/drop file.

		This function is inherited from PyQt.
		"""
		text = e.mimeData().text()
		text = text.rstrip()
		filePath = text.replace('file://', '')

		logger.info(filePath)

		if os.path.isfile(filePath):
			self.signalLoadDroppedFile.emit(filePath)

	def _initGui(self):
		"""
		One time initialization of main GUI.
		"""
		vLayout = QtWidgets.QVBoxLayout()

		vSplitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

		#
		# list of files
		self.fileListGui = fileListStochGui()
		vSplitter.addWidget(self.fileListGui)

		# raw plots (raw, hist, phase)
		rawPlotGui = rawStochGui()
		vSplitter.addWidget(rawPlotGui)

		# stats
		statGui = statsStochGui()
		vSplitter.addWidget(statGui)
		vLayout.addWidget(vSplitter)

		# enable drag/drop
		self.setAcceptDrops(True)

		#
		# connect signal/slot of (fileListGui, rawPlotGui, statGui)
		self.fileListGui.signalSelectFile.connect(rawPlotGui.slot_switchFile)
		self.fileListGui.signalSelectFile.connect(statGui.slot_detect)
		self.signalLoadDroppedFile.connect(self.fileListGui.loadDroppedFile)
		#
		rawPlotGui.signalDetect.connect(self.fileListGui.slot_detect)
		#
		rawPlotGui.signalDetect.connect(statGui.slot_detect)

		# finalize
		centralWidget = QtWidgets.QWidget()
		centralWidget.setLayout(vLayout)
		self.setCentralWidget(centralWidget)

class statsStochGui(QtWidgets.QWidget):
	"""
	show table of isi stats
	"""
	def __init__(self, parent=None):
		super(statsStochGui, self).__init__(parent)
		self._myModel = None  # a DataFrameModel
		self._initGui()

	def mySetModel(self, df):
		self._myModel = DataFrameModel(df)  # _dataframe
		self._tableView.setModel(self._myModel)

	def slot_detect(self, ba):
		df = ba.isiStats()
		if df is None:
			df = pd.DataFrame()
		self.mySetModel(df)

		logger.info('isi stats:')

		if len(df) == 0:
			print('  NONE')
		else:
			print(df)

	def _initGui(self):
		vLayout = QtWidgets.QVBoxLayout()

		# main table view
		self._tableView = QtWidgets.QTableView(self)
		self._tableView.setFont(QtGui.QFont('Arial', 10))
		self._tableView.horizontalHeader().setStretchLastSection(True)  # so we fill parent
		# no work
		#self._tableView.setColumnWidth(0, 500)  # set first column (file) wider
		self._tableView.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
		self._tableView.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
							QtWidgets.QSizePolicy.Expanding)
		self._tableView.setSelectionMode(QtWidgets.QTableView.SingleSelection)
		#self._tableView.clicked.connect(self.on_left_click)

		vLayout.addWidget(self._tableView)

		self.setLayout(vLayout)

class fileListStochGui(QtWidgets.QWidget):

	#signalLoadFolder = QtCore.pyqtSignal() # no payload
	#signalRefreshFolder = QtCore.pyqtSignal()  # no payload
	signalSelectFile = QtCore.pyqtSignal(object) # row index (corresponds to file on xxx)

	def __init__(self, parent=None):
		super(fileListStochGui, self).__init__(parent)

		self._fileList = colinAnalysis2()  # backend list of bAnalysis2 in folder path
		self._myModel = None  # a DataFrameModel

		self._initGui()

	def _initGui(self):
		vLayout = QtWidgets.QVBoxLayout()

		# add controls above table
		controlLayout = QtWidgets.QHBoxLayout()

		# load folder button
		aName = 'Load Folder'
		loadFolderButton = QtWidgets.QPushButton(aName)
		loadFolderButton.clicked.connect(partial(self.on_load_folder, aName))
		controlLayout.addWidget(loadFolderButton)

		aName = 'Load New Files'
		refreshButton = QtWidgets.QPushButton(aName)
		refreshButton.clicked.connect(partial(self.on_refresh_button, aName))
		controlLayout.addWidget(refreshButton)

		vLayout.addLayout(controlLayout)

		# main table view
		self._tableView = QtWidgets.QTableView(self)
		self._tableView.setFont(QtGui.QFont('Arial', 10))
		self._tableView.horizontalHeader().setStretchLastSection(True)  # so we fill parent
		# no work
		#self._tableView.setColumnWidth(0, 500)  # set first column (file) wider
		self._tableView.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
		self._tableView.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
							QtWidgets.QSizePolicy.Expanding)
		self._tableView.setSelectionMode(QtWidgets.QTableView.SingleSelection)
		self._tableView.clicked.connect(self.on_left_click)

		vLayout.addWidget(self._tableView)

		self.setLayout(vLayout)

	def loadFolder(self, path=None):

		if path is None:
			path = str(QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory With Recordings"))
			if len(path) == 0:
				return

		logger.info(path)

		self._fileList.loadFolder(path)
		df = self._fileList.asDataFrame()

		print('loaded folder looks like this:')
		print(df)

		#
		self.mySetModel(df)

		#self.signalLoadFolder.emit()

		if len(df) > 0:
			self.selectFile(0)

	def refreshFolder(self):
		"""
		Scan folder for new files
		"""
		logger.info('')
		numNewFiles = self._fileList.refreshFolder()
		if numNewFiles > 0:
			df = self._fileList.asDataFrame()
			print(df)
			#
			self.mySetModel(df)

	def selectFile(self, rowIdx):
		logger.info(rowIdx)
		# get bAnalysis2 from file list and propogate selection
		ba = self._fileList.getFile(rowIdx)
		self.signalSelectFile.emit(ba)

	def slot_detect(self, ba):
		"""
		New detection emit to update file list table
		"""
		logger.info('')
		df = self._fileList.asDataFrame()
		self.mySetModel(df)

	def on_load_folder(self, nameStr):
		logger.info(nameStr)
		self.loadFolder()

	def on_refresh_button(self, nameStr):
		logger.info(nameStr)
		self.refreshFolder()

	def on_left_click(self, item):
		row = item.row()
		df = self._myModel.dataFrame
		realRow = df.index[row] # sort order
		logger.info(f'User selected row {row} realRow {realRow}')
		self.selectFile(realRow)

	def mySetModel(self, df):
		"""
		Refresh entire table df (slow).
		Be sure to store/refresh the selected row (if any)
		"""

		# store selected row
		selectedRow = None
		selectionModel = self._tableView.selectionModel()
		if selectionModel is not None:
			indexes = selectionModel.selectedRows()
			if len(indexes) > 0:
				selectedRow = indexes[0].row()

		# update model
		self._myModel = DataFrameModel(df)  # _dataframe
		self._tableView.setModel(self._myModel)

		# reselect previous selected row
		if selectedRow is not None:
			self._tableView.selectRow(selectedRow)

	def loadDroppedFile(self, filePath):
		"""
		When user drops into a QMainWindow
		"""
		logger.info(filePath)
		df = self._fileList.appendDroppedFile(filePath)

		self.mySetModel(df)

class rawStochGui(QtWidgets.QWidget):
	"""
	Plot one of (raw, isi hist, period hist)
	"""

	signalDetect = QtCore.pyqtSignal(object) # no payload
	"""When user presses 'Detect' button and spikes are detected."""

	def __init__(self, parent=None):
		super(rawStochGui, self).__init__(parent)

		self._ba = None
		self._plotType = 'plotRaw'
		self._axs = []

		self._showDetection = True
		self._showDac = True

		self._buildGui()

	def on_detect_button(self, nameStr):
		if self._ba is not None:
			#self.detectButton  # set red
			self.detectButton.setStyleSheet("background-color : yellow")
			QtWidgets.qApp.processEvents()

			thresholdValue = self.thresholdSpinbox.value()
			detect(self._ba, thresholdValue)
			self.replot()

			self.signalDetect.emit(self._ba)

			#self.detectButton  # set normal
			self.detectButton.setStyleSheet("background-color : Blue")

	def btnstate(self):
		radioButton = self.sender()
		if not radioButton.isChecked():
			return
		logger.info(f'{radioButton.text()} {radioButton.isChecked()}')

		if radioButton.text() == "Raw":
			self._plotType = 'plotRaw'
		elif radioButton.text() == "ISI Histogram":
			self._plotType = 'plotHist'
		elif radioButton.text() == "Phase Histogram":
			self._plotType = 'plotPhaseHist'
		else:
			logger.error(f'Did not understand {radioButton.text()}')

		self.replot()

	def on_check_boxState(self, state):
		checkbox = self.sender()
		isChecked = checkbox.isChecked()

		if checkbox.text() == 'Show Detection':
			self._showDetection = isChecked
		elif checkbox.text() == 'Show DAC':
			self._showDac = isChecked
		self.replot()

	def replot(self):
		logger.info(self._plotType)

		self.static_canvas.figure.clear()

		fileName = self._ba.fileName
		self.fig.suptitle(fileName)

		# ...
		self._axs = []  # CLEAR EXISTING AXES

		numSweeps = self._ba.numSweeps
		for sweep in range(numSweeps):
			# this is needed to share x-axis across all sweeps
			#ax = self.static_canvas.figure.add_subplot(self._ba.numSweeps, 1, sweep+1)
			if sweep == 0:
				ax = self.static_canvas.figure.add_subplot(numSweeps,1, sweep+1)  # +1 because subplot index is 1 based
			else:
				ax = self.static_canvas.figure.add_subplot(numSweeps,1, sweep+1, sharex=self._axs[0])  # +1 because subplot index is 1 based

			self._axs.append(ax)
			# exaple plot
			#self._axs[sweep].plot([1,2,3], [4,5,6])

		if self._plotType == 'plotRaw':
			showDetection = self._showDetection
			showDac = self._showDac
			plotRaw(self._ba, showDetection=showDetection, showDac=showDac, axs=self._axs)
		elif self._plotType == 'plotHist':
			plotHist(self._ba, self._axs)
		elif self._plotType == 'plotPhaseHist':
			plotPhaseHist(self._ba, self._axs)

		# set default save file name
		saveFileName = os.path.splitext(fileName)[0]
		self.static_canvas.get_default_filename = lambda: f'{saveFileName}-{self._plotType}.png'

		#
		self.static_canvas.draw()

	def slot_switchFile(self, ba):
		self._ba = ba  # needed to detect
		self.replot()

	def _buildGui(self):
		vLayout = QtWidgets.QVBoxLayout()

		#
		# detect layout
		controlLayout = QtWidgets.QHBoxLayout()

		# detect button
		aName = 'Detect (mV)'
		self.detectButton = QtWidgets.QPushButton(aName)
		self.detectButton.setStyleSheet("background-color : Blue")
		self.detectButton.clicked.connect(partial(self.on_detect_button, aName))

		controlLayout.addWidget(self.detectButton)

		# detection threshold
		self.thresholdSpinbox = QtWidgets.QDoubleSpinBox()
		self.thresholdSpinbox.setKeyboardTracking(False)
		#spinBox.setObjectName(statName)  # correspond to stat to set in callback
		self.thresholdSpinbox.setRange(-1e9, 1e9)
		self.thresholdSpinbox.setDecimals(3)
		self.thresholdSpinbox.setValue(-20)
		#self.thresholdSpinbox.valueChanged.connect(self.setThreshold)

		controlLayout.addWidget(self.thresholdSpinbox)

		#
		vLayout.addLayout(controlLayout) # add mpl canvas

		#
		# plot type
		plotTypeLayout = QtWidgets.QHBoxLayout()

		b1 = QtWidgets.QRadioButton('Raw')
		b1.setChecked(True)
		b1.toggled.connect(self.btnstate)
		plotTypeLayout.addWidget(b1)

		b1 = QtWidgets.QRadioButton('ISI Histogram')
		b1.setChecked(False)
		b1.toggled.connect(self.btnstate)
		plotTypeLayout.addWidget(b1)

		b1 = QtWidgets.QRadioButton("Phase Histogram")
		b1.setChecked(False)
		b1.toggled.connect(self.btnstate)
		plotTypeLayout.addWidget(b1)

		#
		vLayout.addLayout(plotTypeLayout) # add mpl canvas

		# turn raw plot detection and dac on/off
		rawPlotOptionsLayout = QtWidgets.QHBoxLayout()

		showDetectionCheckbox = QtWidgets.QCheckBox('Show Detection')
		showDetectionCheckbox.setCheckState(2)  # annoying
		showDetectionCheckbox.stateChanged.connect(self.on_check_boxState)
		rawPlotOptionsLayout.addWidget(showDetectionCheckbox)

		showDacCheckbox = QtWidgets.QCheckBox('Show DAC')
		showDacCheckbox.setCheckState(2)  # annoying
		showDacCheckbox.stateChanged.connect(self.on_check_boxState)
		rawPlotOptionsLayout.addWidget(showDacCheckbox)

		vLayout.addLayout(rawPlotOptionsLayout) # add mpl canvas


		#
		# matplotlib
		vPlotLayout = QtWidgets.QVBoxLayout()

		#plt.style.use('dark_background')

		self.fig = mpl.figure.Figure(constrained_layout=True)
		self.static_canvas = backend_qt5agg.FigureCanvas(self.fig)
		self.static_canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
		self.static_canvas.setFocus()

		#self.static_canvas.get_default_filename = lambda: 'new_default_name.png'

		#can do self.mplToolbar.hide()
		self.mplToolbar = mpl.backends.backend_qt5agg.NavigationToolbar2QT(self.static_canvas, self.static_canvas)

		vPlotLayout.addWidget(self.static_canvas) # add mpl canvas
		vPlotLayout.addWidget(self.mplToolbar) # add mpl canvas

		vLayout.addLayout(vPlotLayout) # add mpl canvas

		#
		self.setLayout(vLayout)

class DataFrameModel(QtCore.QAbstractTableModel):
	"""
	Abstract table model to define behavior of QTableView

	Also see for another implementation:
	https://github.com/eyllanesc/stackoverflow/tree/master/questions/44603119
	"""
	DtypeRole = QtCore.Qt.UserRole + 1000
	ValueRole = QtCore.Qt.UserRole + 1001

	def __init__(self, df=pd.DataFrame(), parent=None):
		super(DataFrameModel, self).__init__(parent)
		self._dataframe = df

	def setDataFrame(self, dataframe):
		self.beginResetModel()
		self._dataframe = dataframe.copy()
		self.endResetModel()

	def dataFrame(self):
		return self._dataframe

	dataFrame = QtCore.pyqtProperty(pd.DataFrame, fget=dataFrame, fset=setDataFrame)

	@QtCore.pyqtSlot(int, QtCore.Qt.Orientation, result=str)
	def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.DisplayRole):
		if role == QtCore.Qt.DisplayRole:
			if orientation == QtCore.Qt.Horizontal:
				return self._dataframe.columns[section]
			else:
				return str(self._dataframe.index[section])
		return QtCore.QVariant()

	def rowCount(self, parent=QtCore.QModelIndex()):
		if parent.isValid():
			return 0
		return len(self._dataframe.index)

	def columnCount(self, parent=QtCore.QModelIndex()):
		if parent.isValid():
			return 0
		return self._dataframe.columns.size

	def data(self, index, role=QtCore.Qt.DisplayRole):
		if not index.isValid() or not (0 <= index.row() < self.rowCount() \
			and 0 <= index.column() < self.columnCount()):
			return QtCore.QVariant()
		row = self._dataframe.index[index.row()]
		col = self._dataframe.columns[index.column()]
		dt = self._dataframe[col].dtype

		val = self._dataframe.iloc[row][col]
		if role == QtCore.Qt.DisplayRole:
			return str(val)
		elif role == DataFrameModel.ValueRole:
			return val
		if role == DataFrameModel.DtypeRole:
			return dt
		return QtCore.QVariant()

	def roleNames(self):
		roles = {
			QtCore.Qt.DisplayRole: b'display',
			DataFrameModel.DtypeRole: b'dtype',
			DataFrameModel.ValueRole: b'value'
		}
		return roles

def run():
	app = QtWidgets.QApplication(sys.argv)

	# list of files
	#path = '/media/cudmore/data/stoch-res/20211209'
	path = '/media/cudmore/data/stoch-res'
	#path = '/Users/cudmore/data/stoch-res'

	sg = stochGui()
	if os.path.isdir(path):
		sg.fileListGui.loadFolder(path)
		#sg.signalLoadDroppedFile.emit(path)
	else:
		logger.info(f'Did not find actual path in __main__ {path}')

	sg.show()

	sys.exit(app.exec_())

if __name__ == '__main__':
	run()
