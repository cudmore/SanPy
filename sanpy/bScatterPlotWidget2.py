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

	def update(self, dataIn):
		print('pandasModel.update()', dataIn)

	def setData(self, index, value, role=QtCore.Qt.DisplayRole):
		print('pandasModel.setData()', index.row(), index.column(), value)
		if index.column() == 1:
			#self._data.iset_value(index.row(), 1, value)
			print('  ', type(index.row()))
			self._data.loc[index.row(), 'isGood'] = value
			print(self._data)
			return value
		return value

	def flags(self, index):
		if index.column() == 1:
			return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
		else:
			return QtCore.Qt.ItemIsEnabled

	def headerData(self, col, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
			return self._data.columns[col]
		return None

class CheckBoxDelegate(QtWidgets.QItemDelegate):
	"""
	A delegate that places a fully functioning QCheckBox cell of the column to which it's applied.
	"""
	def __init__(self, parent):
		QtWidgets.QItemDelegate.__init__(self, parent)

	def createEditor(self, parent, option, index):
		"""
		Important, otherwise an editor is created if the user clicks in this cell.
		"""
		return None

	def paint(self, painter, option, index):
		"""
		Paint a checkbox without the label.
		"""
		self.drawCheck(painter, option, option.rect, QtCore.Qt.Unchecked if int(index.data()) == 0 else QtCore.Qt.Checked)

	def editorEvent(self, event, model, option, index):
		'''
		Change the data in the model and the state of the checkbox
		if the user presses the left mousebutton and this cell is editable. Otherwise do nothing.
		'''
		if not int(index.flags() & QtCore.Qt.ItemIsEditable) > 0:
			return False

		if event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton:
			# Change the checkbox-state
			self.setModelData(None, model, index)
			return True

		return False


	def setModelData (self, editor, model, index):
		'''
		The user wanted to change the old state in the opposite.
		'''
		print('CheckBoxDelegate.setModelData()')
		model.setData(index, 1 if int(index.data()) == 0 else 0, QtCore.Qt.EditRole)


class MainWindow(QtWidgets.QMainWindow):
	send_fig = QtCore.pyqtSignal(str)

	def __init__(self, path):
		"""
		path: full path to .csv file generated with reanalyze
		"""
		super(MainWindow, self).__init__()

		self.statusBar = QtWidgets.QStatusBar()
		self.setStatusBar(self.statusBar)

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
			'Condition': 'Condition',
			'Sex': 'Sex',
			'Region': 'Region',
			'File Number': 'File Number',
			'File Name': 'filename',
		}

		self.loadPath(path)

		self.yDf = None

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

		# to hold popups
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

		hueTypes = ['Region', 'Sex', 'Condition', 'File Number'] #, 'File Name'] #, 'None']
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

		self.layout.addWidget(QtWidgets.QLabel("X Statistic"), 0, 0)
		self.layout.addWidget(self.xDropdown, 0, 1)
		self.layout.addWidget(QtWidgets.QLabel("Y Statistic"), 1, 0)
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
		#self.layout.addWidget(self.canvas, 3, 0, rowSpan, colSpan)

		self.myToolbar = QtWidgets.QToolBar()
		self.myToolbar.setFloatable(True)
		self.myToolbar.setMovable(True)
		self.myToolbar.addWidget(self.canvas)
		self.addToolBar(QtCore.Qt.RightToolBarArea, self.myToolbar)

		# table with pandas dataframe
		self.myModel = pandasModel(self.masterDf)
		self.tableView = QtWidgets.QTableView()
		# todo, derive a class for tableView
		self.tableView.setItemDelegateForColumn(1, CheckBoxDelegate(None))
		self.tableView.setFont(QtGui.QFont('Arial', 10))
		self.tableView.setModel(self.myModel)
		self.tableView.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
								  QtWidgets.QSizePolicy.Expanding)
		self.tableView.installEventFilter(self)
		self.layout.addWidget(self.tableView, 4, 0, rowSpan, colSpan)

		self.setCentralWidget(self.main_widget)
		self.show()
		self.update2()

	def mySetStatusBar(self, text):
		self.statusBar.showMessage(text) #,2000)

	def eventFilter(self, source, event):
		if (event.type() == QtCore.QEvent.KeyPress and
			event.matches(QtGui.QKeySequence.Copy)):
			self.copySelection2()
			return True
		return super(MainWindow, self).eventFilter(source, event)

	'''
	def copyTable(self):
		headerList = []
		for i in self.tableView.model().columnCount():
			headers.append(self.tableView.model().headerData(i, QtCore.Qt.Horizontal).toString()
		print('copyTable()')
		print('  headers:', headers)
		m = self.tableView.rowCount()
		n = self.tableView.columnCount()
		table = [[''] * n for x in range(m+1)]
		#for i in m:
	'''

	def copySelection2(self):
		if self.yDf is not None:
			self.yDf.to_clipboard(sep='\t', index=False)
			print('Copied to clipboard')
			print(self.yDf)

	'''
	def copySelection(self):
		#self.copyTable()

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
	'''

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
		'''
		self.masterDf['Condition'] = self.masterDf['condition1']
		self.masterDf['File Number'] = self.masterDf['condition2']
		self.masterDf['Sex'] = self.masterDf['condition3']
		self.masterDf['Region'] = self.masterDf['condition4']
		self.masterDf['filename'] = [os.path.splitext(os.path.split(x)[1])[0] for x in self.masterDf['file'].tolist()]
		'''
		self.masterDfColumns = self.masterDf.columns.to_list()
		self.masterCatColumns = ['Condition', 'File Number', 'Sex', 'Region', 'filename', 'analysisname']
		self.setWindowTitle(path)

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
		print('on_pick_event() event:', event)
		print('event.ind:', event.ind)

		if len(event.ind) < 1:
			return
		spikeNumber = event.ind[0]
		print('  selected:', spikeNumber)

		# propagate a signal to parent
		#self.myMainWindow.mySignal('select spike', data=spikeNumber)
		#self.selectSpike(spikeNumber)

	def getMeanDf(self, xStat, yStat):
		# need to get all categorical columns from orig df
		# these do not change per file (sex, condition, region)
		print('getMeanDf() xStat:', xStat, 'yStat:', yStat)

		if xStat == yStat:
			groupList = [xStat]
		else:
			groupList = [xStat, yStat]
		#meanDf = self.masterDf.groupby('analysisname', as_index=False)[groupList].mean()
		meanDf = self.masterDf.groupby('analysisname', as_index=False)[groupList].mean()
		meanDf = meanDf.reset_index()

		print('after initial grouping')
		print(meanDf)

		for catName in self.masterCatColumns:
			if catName == 'analysisname':
				# this is column we grouped by, already in meanDf
				continue
			meanDf[catName] = ''

		# for each row, update all categorical columns using self.masterCatColumns
		fileNameList = meanDf['analysisname'].unique()
		#print('  fileNameList:', fileNameList)
		for analysisname in fileNameList:
			tmpDf = self.masterDf[ self.masterDf['analysisname']==analysisname ]
			if len(tmpDf) == 0:
				print('  error: got 0 length for analysisname:', analysisname)
				continue
			for catName in self.masterCatColumns:
				if catName == 'analysisname':
					# this is column we grouped by, already in meanDf
					continue
				#print('analysisname:', analysisname, 'catName:', catName)
				# find value of catName column from 1st instance in masterDf
				#print('  tmpDf[catName]:', tmpDf[catName])
				#print('  tmpDf[catName].iloc[0]:', tmpDf[catName].iloc[0])
				catValue = tmpDf[catName].iloc[0]
				#print('  analysisname:', analysisname, 'catName:', catName, 'catValue:', catValue)
				#meanDf[ meanDf['analysisname']=='analysisname' ][catName] = catValue
				theseRows = (meanDf['analysisname']==analysisname).tolist()
				#print('	theseRows:', theseRows)
				meanDf.loc[theseRows, catName] = catValue

		#
		# is good
		meanDf.insert(1, 'isGood', 0)

		#
		# sort
		meanDf = meanDf.sort_values(['Region', 'Sex', 'Condition'])
		meanDf['index'] = [x+1 for x in range(len(meanDf))]
		meanDf = meanDf.reset_index()
		meanDf = meanDf.round(3)
		#
		print('getMeanDf():')
		print(meanDf)
		#
		return meanDf

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
			meanDf = self.getMeanDf(xStat, yStat)

		plotType = self.plotType
		if self.hue == 'None':
			# special case, we do not want None in self.statNameMap
			hue = None
		else:
			hue = self.statNameMap[self.hue]

		warningStr = ''
		if plotType == 'Scatter Plot':
			try:
				sns.scatterplot(x=xStat, y=yStat, hue=hue,
						data=meanDf, ax=self.axes[0])
			except (ValueError) as e:
				self.fig.canvas.draw()
				print('EXCEPTION:', e)
		elif plotType == 'Violin Plot':
			if not xIsCategorical:
				warningStr = 'Violin plot requires a categorical x statistic'
			else:
				sns.violinplot(x=xStat, y=yStat, hue=hue,
						data=meanDf, ax=self.axes[0])
		elif plotType == 'Box Plot':
			if not xIsCategorical:
				warningStr = 'Box plot requires a categorical x statistic'
			else:
				sns.boxplot(x=xStat, y=yStat, hue=hue,
						data=meanDf, ax=self.axes[0])
		elif plotType == 'Raw + Mean Plot':
			if not xIsCategorical:
				warningStr = 'Raw + Mean plot requires a categorical x statistic'
			else:
				try:
					sns.stripplot(x=xStat, y=yStat, hue=hue,
							data=meanDf,
							ax=self.axes[0],
							zorder=1)
					sns.pointplot(x=xStat, y=yStat, hue=hue,
							data=meanDf,
							ci=68, capsize=0.1, color='k',
							ax=self.axes[0],
							zorder=10)
				except (ValueError) as e:
					print('EXCEPTION in "Raw + Mean Plot":', e)

		elif plotType == 'Regression Plot':
			# regplot does not have hue
			if xIsCategorical or yIsCategorical:
				warningStr = 'Regression plot requires continuous x and y statistics'
			else:
				# todo: loop and make a regplot
				# for each unique() name in
				# hue (like Region, Sex, Condition)
				hueList = self.masterDf[hue].unique()
				for oneHue in hueList:
					tmpDf = meanDf [ meanDf[hue]==oneHue ]
					#print('regplot oneHue:', oneHue, 'len(tmpDf)', len(tmpDf))
					sns.regplot(x=xStat, y=yStat, data=tmpDf,
							ax=self.axes[0]);

		self.mySetStatusBar(warningStr)

		self.axes[0].spines['right'].set_visible(False)
		self.axes[0].spines['top'].set_visible(False)

		if not self.showLegend:
			self.axes[0].legend().remove()

		self.axes[0].set_xlabel(xStatHuman)
		self.axes[0].set_ylabel(yStatHuman)

		#self.fig.canvas.draw_idle()
		self.fig.canvas.draw()

		#
		# raises pandas.core.base.DataError
		try:
			meanDf = self.getMeanDf(xStat, yStat)

			# before we set the model, remove some columns
			modelMeanDf = meanDf.drop(['level_0', 'File Number', 'analysisname'], axis=1)

			self.yDf = modelMeanDf

			self.myModel = pandasModel(modelMeanDf)
			self.tableView.setModel(self.myModel)
		except (pd.core.base.DataError) as e:
			print('EXCEPTION:', e)


if __name__ == '__main__':
	path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'

	app = QtWidgets.QApplication(sys.argv)
	ex = MainWindow(path)
	sys.exit(app.exec_())
