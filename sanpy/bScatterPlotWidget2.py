import os, sys, io, csv
import pandas as pd
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure
import seaborn as sns

#tips = sns.load_dataset("tips")

class pandasModel(QtCore.QAbstractTableModel):

	def __init__(self, data):
		QtCore.QAbstractTableModel.__init__(self)
		self._data = data

	def rowCount(self, parent=None):
		return self._data.shape[0]

	def columnCount(self, parnet=None):
		return self._data.shape[1]

	def data(self, index, role=QtCore.Qt.DisplayRole):
		if index.isValid():
			if role == QtCore.Qt.DisplayRole:
				return str(self._data.iloc[index.row(), index.column()])
		return None

	def headerData(self, col, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
			return self._data.columns[col]
		return None

class MainWindow(QtWidgets.QMainWindow):
	send_fig = QtCore.pyqtSignal(str)

	def __init__(self, path):
		"""
		path: full path to .csv file generated with reanalyze
		"""
		super(MainWindow, self).__init__()

		self.buildMenus()

		self.statNameMap = {
			'Early Diastolic Duration': 'earlyDiastolicDurationRate',
			'Spike Frequency': 'spikeFreq_hz',
			'peakHeight': 'peakHeight',
			'peakVal': 'peakVal',
			'preMinVal': 'preMinVal',
			'postMinVal': 'postMinVal',
			'cycleLength_ms': 'cycleLength_ms',
			'apDuration_ms': 'apDuration_ms',
			'diastolicDuration_ms': 'diastolicDuration_ms',
			'Sex': 'Sex',
			'Region': 'Region',
			'File Name': 'filename',
		}

		self.loadPath(path)

		self.main_widget = QtWidgets.QWidget(self)

		self.fig = Figure()
		self.ax1 = self.fig.add_subplot(111)
		#self.ax2 = self.fig.add_subplot(122, sharex=self.ax1, sharey=self.ax1)
		#self.ax2 = self.fig.add_subplot(122)
		#self.axes=[self.ax1, self.ax2]
		self.axes=[self.ax1]
		self.canvas = FigureCanvas(self.fig)
		self.cid = self.canvas.mpl_connect('pick_event', self.on_pick_event)
		# matplotlib toolbar
		self.mplToolbar = NavigationToolbar2QT(self.canvas, self.canvas) # params are (canvas, parent)

		self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
								  QtWidgets.QSizePolicy.Expanding)
		self.canvas.updateGeometry()

		self.layout = QtWidgets.QGridLayout(self.main_widget)

		##
		keys = list(self.statNameMap.keys())
		xStatIdx = keys.index('Spike Frequency')
		yStatIdx = keys.index('Early Diastolic Duration')
		self.xDropdown = QtWidgets.QComboBox()
		self.xDropdown.addItems(keys)
		self.xDropdown.setCurrentIndex(xStatIdx)
		self.yDropdown = QtWidgets.QComboBox()
		self.yDropdown.addItems(keys)
		self.yDropdown.setCurrentIndex(yStatIdx)

		hueTypes = ['Region', 'Sex', 'File Name']
		self.hue = 'Region'
		self.hueDropdown = QtWidgets.QComboBox()
		self.hueDropdown.addItems(hueTypes)
		self.hueDropdown.setCurrentIndex(0)
		self.hueDropdown.currentIndexChanged.connect(self.updateHue)

		self.plotType = 'Scatter Plot'
		self.typeDropdown = QtWidgets.QComboBox()
		self.typeDropdown.addItems(['Scatter Plot', 'Violin Plot', 'Box Plot', 'Raw + Mean Plot', 'Regression Plot'])
		self.typeDropdown.setCurrentIndex(0)

		self.dataTypes = ['Raw', 'File Mean']
		self.dataType = 'Raw' # (Raw, File Mean)
		self.dataTypeDropdown = QtWidgets.QComboBox()
		self.dataTypeDropdown.addItems(self.dataTypes)
		self.dataTypeDropdown.setCurrentIndex(0)

		self.xDropdown.currentIndexChanged.connect(self.update2)
		self.yDropdown.currentIndexChanged.connect(self.update2)
		self.typeDropdown.currentIndexChanged.connect(self.updatePlotType)
		self.dataTypeDropdown.currentIndexChanged.connect(self.updateDataType)

		self.showLegend = True
		showLegendCheckBox = QtWidgets.QCheckBox('Show Legend')
		showLegendCheckBox.setChecked(self.showLegend)
		showLegendCheckBox.stateChanged.connect(self.setShowLegend)

		self.layout.addWidget(QtWidgets.QLabel("X-Axis"), 0, 0)
		self.layout.addWidget(self.xDropdown, 0, 1)
		self.layout.addWidget(QtWidgets.QLabel("Y-Axis"), 1, 0)
		self.layout.addWidget(self.yDropdown, 1, 1)
		self.layout.addWidget(QtWidgets.QLabel("Hue"), 2, 0)
		self.layout.addWidget(self.hueDropdown, 2, 1)
		#
		self.layout.addWidget(QtWidgets.QLabel("Plot Type"), 0, 2)
		self.layout.addWidget(self.typeDropdown, 0, 3)
		self.layout.addWidget(QtWidgets.QLabel("Data Type"), 1, 2)
		self.layout.addWidget(self.dataTypeDropdown, 1, 3)
		self.layout.addWidget(showLegendCheckBox, 2, 2)

		rowSpan = 1
		colSpan = 4
		self.layout.addWidget(self.canvas, 3, 0, rowSpan, colSpan)

		# table with pandas dataframe
		self.myModel = pandasModel(self.masterDf)
		self.tableView = QtWidgets.QTableView()
		self.tableView.setModel(self.myModel)
		self.tableView.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
								  QtWidgets.QSizePolicy.Expanding)
		self.tableView.installEventFilter(self)
		self.layout.addWidget(self.tableView, 4, 0, rowSpan, colSpan)

		self.setCentralWidget(self.main_widget)
		self.show()
		self.update2()

	def eventFilter(self, source, event):
		if (event.type() == QtCore.QEvent.KeyPress and
			event.matches(QtGui.QKeySequence.Copy)):
			self.copySelection()
			return True
		return super(MainWindow, self).eventFilter(source, event)

	def copySelection(self):
		selection = self.tableView.selectedIndexes()
		if selection:
			rows = sorted(index.row() for index in selection)
			columns = sorted(index.column() for index in selection)
			rowcount = rows[-1] - rows[0] + 1
			colcount = columns[-1] - columns[0] + 1
			table = [[''] * colcount for _ in range(rowcount)]
			for index in selection:
				row = index.row() - rows[0]
				column = index.column() - columns[0]
				table[row][column] = index.data()
			stream = io.StringIO()
			csv.writer(stream).writerows(table)
			QtWidgets.QApplication.clipboard().setText(stream.getvalue())

	def buildMenus(self):
		loadAction = QtWidgets.QAction('Load CSV', self)
		loadAction.triggered.connect(self.loadPathMenuAction)

		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		fileMenu.addAction(loadAction)

	def loadPathMenuAction(self):
		print('loadPathMenuAction')

	def loadPath(self, path):
		"""
		path: full path to .csv file generated with reanalyze.py
		"""
		#path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'
		self.masterDf = pd.read_csv(path, header=0) #, dtype={'ABF File': str})
		self.masterDf['Sex'] = self.masterDf['condition3']
		self.masterDf['Region'] = self.masterDf['condition4']
		self.masterDf['filename'] = [os.path.splitext(os.path.split(x)[1])[0] for x in self.masterDf['file'].tolist()]
		self.masterDfColumns = self.masterDf.columns.to_list()

	def setShowLegend(self, state):
		print('setShowLegend() state:', state)
		self.showLegend = state
		self.update2()

	def updateHue(self):
		hue = self.hueDropdown.currentText()
		self.hue = hue
		self.update2()

	def updatePlotType(self):
		plotType = self.typeDropdown.currentText()
		self.plotType = plotType
		self.update2()

	def updateDataType(self):
		dataType = self.dataTypeDropdown.currentText()
		self.dataType = dataType
		self.update2()

	def on_pick_event(self, event):
		print('on_pick_event() event:', event, 'event.ind:', event.ind)

		if len(event.ind) < 1:
			return
		spikeNumber = event.ind[0]
		print('  selected:', spikeNumber)

		# propagate a signal to parent
		#self.myMainWindow.mySignal('select spike', data=spikeNumber)
		#self.selectSpike(spikeNumber)

	def update2(self):
		xStatHuman = self.xDropdown.currentText()
		yStatHuman = self.yDropdown.currentText()
		print('update2() xStatHuman:', xStatHuman, 'yStatHuman:', yStatHuman)
		xStat = self.statNameMap[xStatHuman]
		yStat = self.statNameMap[yStatHuman]

		xIsCategorical = pd.api.types.is_string_dtype(self.masterDf[xStat].dtype)
		yIsCategorical = pd.api.types.is_string_dtype(self.masterDf[yStat].dtype)
		#print('xIsCategorical:', xIsCategorical, 'yIsCategorical:', yIsCategorical)

		self.axes[0].clear()
		#self.axes[1].clear()

		# per cell mean
		if self.dataType == 'Raw':
			meanDf = self.masterDf
		elif self.dataType == 'File Mean':
			supDf = self.masterDf[ self.masterDf['Region']=='Superior']
			infDf = self.masterDf[ self.masterDf['Region']=='Inferior']
			meanDf = supDf.groupby('filename', as_index=False)[[xStat, yStat]].mean()
			meanDf['Region'] = 'Superior'
			meanDf2 = infDf.groupby('filename', as_index=False)[[xStat, yStat]].mean()
			meanDf2['Region'] = 'Inferior'
			meanDf = meanDf.append(meanDf2)
			#print(meanDf)
		okGo = True
		plotType = self.plotType
		hue = self.statNameMap[self.hue]
		if plotType == 'Scatter Plot':
			try:
				sns.scatterplot(x=xStat, y=yStat, hue=hue,
						data=meanDf, ax=self.axes[0])
			except (ValueError) as e:
				self.fig.canvas.draw()
				print('EXCEPTION:', e)
		elif plotType == 'Violin Plot':
			if not xIsCategorical:
				print('Violin plot requires a categorical x statistic')
				okGo = False
			else:
				sns.violinplot(x=xStat, y=yStat, hue=hue,
						data=meanDf, ax=self.axes[0])
		elif plotType == 'Box Plot':
			if not xIsCategorical:
				print('Box plot requires a categorical x statistic')
				okGo = False
			else:
				sns.boxplot(x=xStat, y=yStat, hue=hue,
						data=meanDf, ax=self.axes[0])
		elif plotType == 'Raw + Mean Plot':
			if not xIsCategorical:
				print('Raw + Mean plot requires a categorical x statistic')
				okGo = False
			else:
				print('  todo: curently, does not use hue')
				sns.pointplot(x=xStat, y=yStat,
							data=meanDf,
							ci=68, capsize=0.1, color='k',
							ax=self.axes[0])
				sns.stripplot(x=xStat, y=yStat,
							data=meanDf,
							color="0.5",
							ax=self.axes[0]);
		elif plotType == 'Regression Plot':
			if xIsCategorical or yIsCategorical:
				print('Regression plot requires continuous x and statistics')
				okGo = False
			else:
				print(' todo: Regression plot needs some work')
				supDf = meanDf [ meanDf['Region']=='Superior' ]
				infDf = meanDf [ meanDf['Region']=='Inferior' ]
				sns.regplot(x=xStat, y=yStat, data=supDf,
							ax=self.axes[0]);
				sns.regplot(x=xStat, y=yStat, data=infDf,
							ax=self.axes[0]);

		self.axes[0].spines['right'].set_visible(False)
		self.axes[0].spines['top'].set_visible(False)

		if not self.showLegend:
			self.axes[0].legend().remove()

		self.axes[0].set_xlabel(xStatHuman)
		self.axes[0].set_ylabel(yStatHuman)

		#self.fig.canvas.draw_idle()
		self.fig.canvas.draw()

		#
		supDf = self.masterDf [ self.masterDf['Region']=='Superior' ]
		infDf = self.masterDf [ self.masterDf['Region']=='Inferior' ]
		# raises pandas.core.base.DataError
		try:
			aggStatList = ['mean', 'std', 'sem', 'median', 'min', 'max', 'count']

			newDf = supDf.groupby('filename', as_index=False)[yStat].agg(aggStatList) #.mean()
			# xStatHuman
			newDf['Region'] = 'Superior'
			newDf['Stat'] = yStatHuman
			#newDf.columns = [c for c in newDf.columns.to_list()]
			#newDf.columns = newDf.columns.get_level_values(0)
			newDf = newDf.reset_index().round(3)

			newDf2 = infDf.groupby('filename', as_index=False)[yStat].agg(aggStatList) #.mean()
			newDf2['Region'] = 'Inferior'
			newDf2['Stat'] = yStatHuman
			#newDf2.columns = [c for c in newDf2.columns.to_list()]
			#newDf2.columns = newDf2.columns.get_level_values(0)
			newDf2 = newDf2.reset_index().round(3)

			newDf = newDf.append(newDf2)

			print(newDf)

			self.myModel = pandasModel(newDf)
			self.tableView.setModel(self.myModel)
		except (pd.core.base.DataError) as e:
			print('EXCEPTION:', e)


if __name__ == '__main__':
	path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'

	app = QtWidgets.QApplication(sys.argv)
	ex = MainWindow(path)
	sys.exit(app.exec_())
