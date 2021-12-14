"""
GUI for real-time and offline analysis
"""
import os, sys, time
from functools import partial

from datetime import datetime

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtWidgets, QtGui

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends import backend_qt5agg

import qdarkstyle

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

from colinAnalysis import bAnalysis2
from colinAnalysis import colinAnalysis2  # list of abf from folder path
from stochAnalysis import plotRaw
from stochAnalysis import plotHist
from stochAnalysis import plotPhaseHist
from stochAnalysis import detect
from stochAnalysis import plotStimFileParams

class stochGui(QtWidgets.QWidget):
	signalSelectFile = QtCore.pyqtSignal(object) # ba
	#signalUpdateDetection = QtCore.pyqtSignal()

	def __init__(self, parent=None):
		super(stochGui, self).__init__(parent)

		self._fileList = colinAnalysis2()  # backend list of bAnalysis2 in folder path

		self.initGui()

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
		self.fileListGui.mySetModel(df)

	def refreshFolder(self):
		logger.info('')
		numNewFiles = self._fileList.refreshFolder()
		if numNewFiles > 0:
			df = self._fileList.asDataFrame()
			print(df)
			#
			self.fileListGui.mySetModel(df)

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
		#self.signalUpdateDetection.emit()
		df = self._fileList.asDataFrame()
		self.fileListGui.mySetModel(df)

	def initGui(self):
		vLayout = QtWidgets.QVBoxLayout()

		vSplitter0 = QtWidgets.QSplitter(QtCore.Qt.Vertical)

		# list of files
		self.fileListGui = fileListStochGui()
		self.fileListGui.signalLoadFolder.connect(self.loadFolder)
		self.fileListGui.signalRefreshFolder.connect(self.refreshFolder)
		self.fileListGui.signalSelectFile.connect(self.selectFile)
		#self.signalUpdateDetection.connect(self.fileListGui.slot_updateDetection)
		#vLayout.addWidget(self.fileListGui)
		vSplitter0.addWidget(self.fileListGui)
		vLayout.addWidget(vSplitter0)

		vSplitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

		# raw plots (raw, hist, phase)
		self.raw = rawStochGui()
		self.raw.signalDetect.connect(self.slot_detect)
		self.signalSelectFile.connect(self.raw.slot_switchFile)
		vSplitter.addWidget(self.raw)

		vLayout.addWidget(vSplitter)

		# stats
		vSplitter2 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
		self.statGui = statsStochGui()
		self.raw.signalDetect.connect(self.statGui.slot_detect)
		self.signalSelectFile.connect(self.statGui.slot_detect)
		vSplitter2.addWidget(self.statGui)
		vLayout.addWidget(vSplitter2)

		#
		self.setLayout(vLayout)


class statsStochGui(QtWidgets.QWidget):
	"""
	show table of isi stats
	"""
	def __init__(self, parent=None):
		super(statsStochGui, self).__init__(parent)
		self._myModel = None  # a DataFrameModel
		self.initGui()

	def mySetModel(self, df):
		self._myModel = DataFrameModel(df)  # _dataframe
		self._tableView.setModel(self._myModel)

	def slot_detect(self, ba):
		df = ba.isiStats()
		if df is None:
			df = pd.DataFrame()
		self.mySetModel(df)

		print('isi stats:')
		if len(df) == 0:
			print('  NONE')
		else:
			print(df)

	def initGui(self):
		vLayout = QtWidgets.QVBoxLayout()

		# main table view
		self._tableView = QtWidgets.QTableView(self)
		self._tableView.setFont(QtGui.QFont('Arial', 10))
		#print('here seg fault')
		#self._tableView.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
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

	signalLoadFolder = QtCore.pyqtSignal() # no payload
	signalRefreshFolder = QtCore.pyqtSignal()  # no payload
	signalSelectFile = QtCore.pyqtSignal(object) # row index (corresponds to file on xxx)

	def __init__(self, parent=None):
		super(fileListStochGui, self).__init__(parent)
		self._myModel = None  # a DataFrameModel
		self.initGui()

	def initGui(self):
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
		#print('here seg fault')
		#self._tableView.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
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

	def on_load_folder(self, nameStr):
		logger.info(nameStr)
		self.signalLoadFolder.emit()

	def on_refresh_button(self, nameStr):
		logger.info(nameStr)
		self.signalRefreshFolder.emit()

	def on_left_click(self, item):
		logger.info('')
		row = item.row()
		df = self._myModel.dataFrame
		realRow = df.index[row] # sort order
		self.signalSelectFile.emit(realRow)

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

	'''
	def slot_updateDetection(self):
		"""
		Rebuild entire table (slow)
		"""
	'''

class rawStochGui(QtWidgets.QWidget):
	"""
	Plot one of (xxx, yyy, zzz)
	"""
	signalDetect = QtCore.pyqtSignal(object) # no payload

	def __init__(self, parent=None):
		super(rawStochGui, self).__init__(parent)

		self._ba = None
		self._plotType = 'plotRaw'
		self._axs = []

		self.buildGui()

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
			self.detectButton.setStyleSheet("background-color : None")

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
			plotRaw(self._ba, self._axs)
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

	def buildGui(self):
		vLayout = QtWidgets.QVBoxLayout()

		#
		# detect
		controlLayout = QtWidgets.QHBoxLayout()

		# detect button
		aName = 'Detect (mV)'
		self.detectButton = QtWidgets.QPushButton(aName)
		self.detectButton.setStyleSheet("background-color : None")
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

		#
		# matplotlib
		#vSplitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
		#vLayout.addWidget(vSplitter)
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

	'''
	path = '/media/cudmore/data/stoch-res/20211209/2021_12_09_0011.abf'  # 1pA/1Hz/2pA step
	ba = bAnalysis2(path)
	print(ba)

	thresholdValue = -20
	detect(ba)


	rsg = rawStochGui()
	rsg.show()
	rsg.slot_switchFile(ba)
	'''

	# list of files
	#path = '/media/cudmore/data/stoch-res/20211209'
	path = '/media/cudmore/data/stoch-res'
	#path = '/Users/cudmore/data/stoch-res'
	'''
	ca = colinAnalysis2(path)

	flsg = fileListStochGui()
	flsg.mySetModel(ca.asDataFrame())
	flsg.show()
	'''

	sg = stochGui()
	sg.loadFolder(path)
	sg.show()

	sys.exit(app.exec_())

if __name__ == '__main__':
	run()
