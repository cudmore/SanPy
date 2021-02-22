"""
202012

General purpose plotting from arbitrary csv files

Started as specifically for SanPy (using reanalyze.py) from a database of spikes

20210112, extending it to any csv for use with bImPy nodes/edges
	See: bImPy/bimpy/analysis/bScrapeNodesAndEdges.py

I want this to run independent of SanPy, to do this:
	copy (pandas model, checkbox delegate) from sanpy.butil
	into a local folder and change imports
"""

import os, sys, io, csv
import traceback
import pandas as pd
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.pyplot as plt # abb 202012 added to set theme
import seaborn as sns
import mplcursors

#sysPath = os.path.dirname(sys.path[0])
#sysPath = os.path.join(sysPath, 'sanpy')
#print('bScatterPlotWidget2.py sysPath:', sysPath)
#sys.path.append(sysPath)

#print('os.getcwd():', os.getcwd())
import sanpy
#import bUtil # from sanpy folder, for pandas model

#class MainWindow(QtWidgets.QWidget):
class bScatterPlotMainWindow(QtWidgets.QMainWindow):
	#send_fig = QtCore.pyqtSignal(str)

	def __init__(self, path,
					categoricalList, hueTypes, analysisName, sortOrder=None,
					statListDict=None, masterDf=None, parent=None):
		"""
		path: full path to .csv file generated with reanalyze
		categoricalList: specify columns that are categorical
			would just like to use 'if column is string' but sometimes number like 1/2/3 need to be categorical
		statListDict: dict where keys are human readable stat names that map onto 'yStat' to specify column in csv
		analysisName: column used for group by
		masterDf: if not none then use it (rather than loading)
					used by main sanpy interface
		todo: make pure text columns categorical
		"""
		super(bScatterPlotMainWindow, self).__init__(parent)

		self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+w"), self)
		self.shortcut.activated.connect(self.myCloseAction)

		self.statusBar = QtWidgets.QStatusBar()
		self.setStatusBar(self.statusBar)

		self.buildMenus()

		self.loadPath(path, masterDf=masterDf)

		# statListDict is a dict with key=humanstat name and yStat=column name in csv
		#self.statListDict = sanpy.bAnalysisUtil.getStatList()
		if statListDict is None:
			# build statListDict from columns of csv path
			self.statListDict = {}
			for colStr in self.masterDfColumns:
				self.statListDict[colStr] = {'yStat': colStr}
		else:
			self.statListDict = statListDict

		#categoricalList = ['Condition', 'Sex', 'Region', 'File Number', 'File Name']
		for categorical in categoricalList:
			self.statListDict[categorical] = {'yStat': categorical}
		# this was originally in self.load() ???
		self.masterCatColumns = categoricalList


		self.hueTypes = hueTypes # ['Region', 'Sex', 'Condition', 'File Number'] #, 'File Name'] #, 'None']
		#self.colorTypes = self.hueTypes

		# unique identifyer to group by
		# for sanpy this is 'analysisName', for bImPy this is xxx
		self.analysisName = analysisName
		self.sortOrder = sortOrder

		# 20210112 moved up
		#self.loadPath(path)

		self.whatWeArePlotting = None # return from sns scatter plot (all plots)
		self.yDf = None # datframe show visually as a table
		self.plotDF = None # df we are plotting (can be same as mean yDf)
							# use this to get row on self.onPick
		self.plotStatx = None
		self.plotStaty = None

		#self.main_widget = QtWidgets.QWidget(self)

		self.darkTheme = True
		if self.darkTheme:
			plt.style.use('dark_background')
		sns.set_context('talk')

		self.doKDE = False # fits on histogram plots
		self.doHover = False

		# HBox for control and plot
		self.hBoxLayout = QtWidgets.QHBoxLayout(self)

		# this is confusing, beacaue we are a QMainWindow
		# we need to create a central widget
		# set its layout
		# and then set the central widget of self (QMainWindow)
		centralWidget = QtWidgets.QWidget()
		centralWidget.setLayout(self.hBoxLayout)
		self.setCentralWidget(centralWidget)

		# WHAT THE  FUCK HAPPENED !!!!!!!!!!!!
		#self.setLayout(self.hBoxLayout)

		self.fig = Figure()
		self.ax1 = self.fig.add_subplot(111)
		#self.ax2 = self.fig.add_subplot(122, sharex=self.ax1, sharey=self.ax1)
		#self.ax2 = self.fig.add_subplot(122)
		#self.axes=[self.ax1, self.ax2]
		self.axes = [self.ax1]
		self.canvas = FigureCanvas(self.fig)
		self.cid = self.canvas.mpl_connect('pick_event', self.on_pick_event)
		# matplotlib toolbar
		# maybe use
		#self.toolbar = NavigationToolbar(self.canvas, self)
		self.mplToolbar = NavigationToolbar2QT(self.canvas, self.canvas) # params are (canvas, parent)

		self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
								  QtWidgets.QSizePolicy.Expanding)
		self.canvas.updateGeometry()

		# to hold popups
		#self.layout = QtWidgets.QGridLayout(self.main_widget)
		self.layout = QtWidgets.QGridLayout()

		self.hBoxLayout.addLayout(self.layout)

		##
		# 20210112, don't do this because we do not know the columsn of the csv
		#keys = list(self.statNameMap.keys())
		keys = list(self.statListDict.keys())
		#xStatIdx = keys.index('Spike Frequency (Hz)')
		#yStatIdx = keys.index('Early Diastolic Depol Rate (dV/s)')
		self.xDropdown = QtWidgets.QComboBox()
		self.xDropdown.addItems(keys)
		#self.xDropdown.setCurrentIndex(xStatIdx)
		self.yDropdown = QtWidgets.QComboBox()
		self.yDropdown.addItems(keys)
		#self.yDropdown.setCurrentIndex(yStatIdx)
		self.yDropdown.setCurrentIndex(0)

		# 20210112 we need to specify this on creation
		#hueTypes = ['Region', 'Sex', 'Condition', 'File Number'] #, 'File Name'] #, 'None']
		self.hue = self.hueTypes[0]
		#self.hue = 'Region'
		self.hueDropdown = QtWidgets.QComboBox()
		self.hueDropdown.addItems(['None'] + self.hueTypes)
		self.hueDropdown.setCurrentIndex(1) # 1 because we pre-pended 'None'
		self.hueDropdown.currentIndexChanged.connect(self.updateHue)

		# color
		#colorTypes = ['Region', 'Sex', 'Condition', 'File Number'] #, 'File Name'] #, 'None']
		#self.color = 'Region'
		'''
		self.color = self.colorTypes[0]
		self.colorDropdown = QtWidgets.QComboBox()
		self.colorDropdown.addItems(self.colorTypes)
		self.colorDropdown.setCurrentIndex(0)
		self.colorDropdown.currentIndexChanged.connect(self.updateColor)
		'''

		self.plotType = 'Scatter Plot'
		self.typeDropdown = QtWidgets.QComboBox()
		self.typeDropdown.addItems(['Scatter Plot', 'Regression Plot', 'Violin Plot', 'Box Plot', 'Raw + Mean Plot', 'Histogram', 'Cumulative Histogram'])
		self.typeDropdown.setCurrentIndex(0)

		self.dataTypes = ['All Spikes', 'File Mean']
		self.dataType = 'File Mean' # (Raw, File Mean)
		self.dataTypeDropdown = QtWidgets.QComboBox()
		self.dataTypeDropdown.setToolTip('All Spikes is all spikes \n File Mean is the mean within each analysis file')
		self.dataTypeDropdown.addItems(self.dataTypes)
		self.dataTypeDropdown.setCurrentIndex(1)

		self.xDropdown.currentIndexChanged.connect(self.update2)
		self.yDropdown.currentIndexChanged.connect(self.update2)
		self.typeDropdown.currentIndexChanged.connect(self.updatePlotType)
		self.dataTypeDropdown.currentIndexChanged.connect(self.updateDataType)

		self.showLegend = True
		showLegendCheckBox = QtWidgets.QCheckBox('Legend')
		showLegendCheckBox.setChecked(self.showLegend)
		showLegendCheckBox.stateChanged.connect(self.setShowLegend)

		darkThemeCheckBox = QtWidgets.QCheckBox('Dark Theme')
		darkThemeCheckBox.setChecked(self.darkTheme)
		darkThemeCheckBox.stateChanged.connect(self.setTheme)

		kdeCheckBox = QtWidgets.QCheckBox('kde (hist)')
		kdeCheckBox.setChecked(self.doKDE)
		kdeCheckBox.stateChanged.connect(self.setKDE)

		hoverCheckbox = QtWidgets.QCheckBox('Hover Info')
		hoverCheckbox.setChecked(self.doHover)
		hoverCheckbox.stateChanged.connect(self.setHover)

		plotSizeList = ['paper', 'poster', 'talk']
		self.plotSizeDropdown = QtWidgets.QComboBox()
		self.plotSizeDropdown.setToolTip('All Spikes is all spikes \n File Mean is the mean within each analysis file')
		self.plotSizeDropdown.addItems(plotSizeList)
		self.plotSizeDropdown.setCurrentIndex(2) # talk
		self.plotSizeDropdown.currentIndexChanged.connect(self.updatePlotSize)

		self.layout.addWidget(QtWidgets.QLabel("X Statistic"), 0, 0)
		self.layout.addWidget(self.xDropdown, 0, 1)
		self.layout.addWidget(QtWidgets.QLabel("Y Statistic"), 1, 0)
		self.layout.addWidget(self.yDropdown, 1, 1)
		self.layout.addWidget(QtWidgets.QLabel("Hue"), 2, 0)
		self.layout.addWidget(self.hueDropdown, 2, 1)
		#self.layout.addWidget(QtWidgets.QLabel("Color"), 3, 0)
		#self.layout.addWidget(self.colorDropdown, 3, 1)
		#
		self.layout.addWidget(QtWidgets.QLabel("Plot Type"), 0, 2)
		self.layout.addWidget(self.typeDropdown, 0, 3)
		self.layout.addWidget(QtWidgets.QLabel("Data Type"), 1, 2)
		self.layout.addWidget(self.dataTypeDropdown, 1, 3)
		self.layout.addWidget(showLegendCheckBox, 2, 2)
		self.layout.addWidget(darkThemeCheckBox, 2, 3)
		self.layout.addWidget(kdeCheckBox, 3, 2)
		self.layout.addWidget(hoverCheckbox, 3, 3)
		self.layout.addWidget(QtWidgets.QLabel("Plot Size"), 4, 2)
		self.layout.addWidget(self.plotSizeDropdown, 4, 3)

		nextRow = 5 # for text table
		rowSpan = 1
		colSpan = 4
		#self.layout.addWidget(self.canvas, 3, 0, rowSpan, colSpan)

		# switch from toolbar to widget
		self.hBoxLayout.addWidget(self.canvas)
		'''
		self.myToolbar = QtWidgets.QToolBar()
		self.myToolbar.setFloatable(True)
		self.myToolbar.setMovable(True)
		self.tmpToolbarAction = self.myToolbar.addWidget(self.canvas)
		self.addToolBar(QtCore.Qt.RightToolBarArea, self.myToolbar)
		'''

		# table with pandas dataframe
		self.myModel = sanpy.bUtil.pandasModel(self.masterDf)
		self.tableView = QtWidgets.QTableView()
		# todo, derive a class for tableView
		# put this back in to enable isGood checkBox
		'''
		colList = self.masterDf.columns.values.tolist()
		if 'include' in colList:
			includeCol = colList.index('include')
			print(f'setting include column {includeCol} to "myCheckBoxDelegate"')
			self.tableView.setItemDelegateForColumn(includeCol, myCheckBoxDelegate(None))
		'''
		self.tableView.setFont(QtGui.QFont('Arial', 10))

		#self.tableView.setModel(self.myModel)
		self._switchTableModel(self.myModel)

		self.tableView.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
								  QtWidgets.QSizePolicy.Expanding)
		self.tableView.installEventFilter(self)
		self.layout.addWidget(self.tableView, nextRow, 0, rowSpan, colSpan)

		self.show()
		self.update2()

	def _switchTableModel(self, newModel):
		"""
		switch between full .csv model and getMeanDf model
		"""
		self.tableView.setModel(newModel)

		print('  todo: on xxx when we set check box delegate we crash !!!')
		if 1:
			# install checkboxes in 'incude' column
			colList = newModel._data.columns.values.tolist()
			if 'include' in colList:
				includeCol = colList.index('include')
				print(f'_switchTableModel() setting include column {includeCol} to "sanpy.bUtil.myCheckBoxDelegate"')
				self.tableView.setItemDelegateForColumn(includeCol, sanpy.bUtil.myCheckBoxDelegate(None))

	def myCloseAction(self):
		print('myCloseAction()')

	def mySetStatusBar(self, text):
		self.statusBar.showMessage(text) #,2000)

	def eventFilter(self, source, event):
		if (event.type() == QtCore.QEvent.KeyPress and
			event.matches(QtGui.QKeySequence.Copy)):
			self.copySelection2()
			return True
		return super(bScatterPlotMainWindow, self).eventFilter(source, event)

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
		loadAction = QtWidgets.QAction('Load database.xlsx', self)
		loadAction.triggered.connect(self.loadPathMenuAction)

		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		fileMenu.addAction(loadAction)

	def loadPathMenuAction(self):
		"""
		prompt user for database.xlsx
		run reanalyze.py on that xlsx database
		load resultant _master.csv
		"""
		print('loadPathMenuAction')

	def loadPath(self, path, masterDf=None):
		"""
		path: full path to .csv file generated with reanalyze.py
		"""
		#path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'
		if masterDf is not None:
			self.masterDf = masterDf
		else:
			if path.endswith('.csv'):
				self.masterDf = pd.read_csv(path, header=0) #, dtype={'ABF File': str})
			elif path.endswith('.xls'):
				self.masterDf = pd.read_excel(path, header=0) #, dtype={'ABF File': str})
			elif path.endswith('.xlsx'):
				self.masterDf = pd.read_excel(path, header=0, engine='openpyxl') #, dtype={'ABF File': str})
			else:
				print('error: file type not supported. Expecting csv/xls/xlsx. Path:', path)

		self.masterDfColumns = self.masterDf.columns.to_list()

		# not sure what this was for ???
		# 20210112, put back in if necc
		#self.masterCatColumns = ['Condition', 'File Number', 'Sex', 'Region', 'filename', 'analysisname']
		#self.masterCatColumns = self.categoricalList

		# todo: put this somewhere better
		self.setWindowTitle(path)

	def setShowLegend(self, state):
		print('setShowLegend() state:', state)
		self.showLegend = state
		self.update2()

	def setKDE(self, state):
		# only used in histograms
		self.doKDE = state
		self.update2()

	def setHover(self, state):
		# used in scatterplots and point plots
		self.doHover = state
		self.update2()

	def setTheme(self, state):
		print('setTheme() state:', state)

		print('NOT IMPLEMENTED')
		#return

		self.darkTheme = state
		if self.darkTheme:
			plt.style.use('dark_background')
			#sns.set_context('talk')

		else:
			#print(plt.style.available)
			plt.rcParams.update(plt.rcParamsDefault)
			#sns.set_context('paper')
		###
		###
		# remove
		#self.plotVBoxLayout.removeWidget(self.toolbar)
		# need this !!! removeWidget does not work
		#self.myToolbar.removeAction(self.tmpToolbarAction)
		self.hBoxLayout.removeWidget(self.canvas)

		#self.toolbar.setParent(None)
		self.canvas.setParent(None)

		self.fig = None # ???
		self.mplToolbar = None
		self.canvas = None

		self.fig = Figure()
		self.canvas = FigureCanvas(self.fig)

		self.ax1 = self.fig.add_subplot(111)
		self.axes = [self.ax1]
		self.cid = self.canvas.mpl_connect('pick_event', self.on_pick_event)

		# matplotlib navigation toolbar
		self.mplToolbar = NavigationToolbar2QT(self.canvas, self.canvas) # params are (canvas, parent)

		self.hBoxLayout.addWidget(self.canvas)

		self.update2()

	def updatePlotSize(self):
		plotSize = self.plotSizeDropdown.currentText()
		sns.set_context(plotSize) #, font_scale=1.4)
		self.update2()

	def updateHue(self):
		hue = self.hueDropdown.currentText()
		self.hue = hue
		self.update2()

	'''
	def updateColor(self):
		color = self.colorDropdown.currentText()
		self.color = color
		self.update2()
	'''

	def updatePlotType(self):
		plotType = self.typeDropdown.currentText()
		self.plotType = plotType
		self.update2()

	def updateDataType(self):
		dataType = self.dataTypeDropdown.currentText()
		self.dataType = dataType
		self.update2()

	def on_pick_event(self, event):
		try:
			print('on_pick_event() event:', event)
			print('event.ind:', event.ind)

			if len(event.ind) < 1:
				return
			spikeNumber = event.ind[0]
			print('  selected:', spikeNumber)

			# propagate a signal to parent
			#self.myMainWindow.mySignal('select spike', data=spikeNumber)
			#self.selectSpike(spikeNumber)
		except (AttributeError) as e:
			pass

	def getMeanDf(self, xStat, yStat, verbose=False):
		# need to get all categorical columns from orig df
		# these do not change per file (sex, condition, region)
		print('getMeanDf() xStat:', xStat, 'yStat:', yStat)

		if xStat == yStat:
			groupList = [xStat]
		else:
			groupList = [xStat, yStat]
		meanDf = self.masterDf.groupby(self.analysisName, as_index=False)[groupList].mean()
		meanDf = meanDf.reset_index()

		#
		# 20210211 get median/std/sem/n
		# try and add median/std/sem/sem/n
		tmpDf = self.masterDf.groupby(self.analysisName, as_index=False)[groupList].median()
		print('tmpDf:', tmpDf)
		meanDf['median'] = tmpDf[self.analysisName]

		for catName in self.masterCatColumns:
			#if catName == 'analysisname':
			if catName == self.analysisName:
				# this is column we grouped by, already in meanDf
				continue
			meanDf[catName] = ''

		# for each row, update all categorical columns using self.masterCatColumns
		#fileNameList = meanDf['analysisname'].unique()
		fileNameList = meanDf[self.analysisName].unique()
		#print('  fileNameList:', fileNameList)
		for analysisname in fileNameList:
			#tmpDf = self.masterDf[ self.masterDf['analysisname']==analysisname ]
			tmpDf = self.masterDf[ self.masterDf[self.analysisName]==analysisname ]
			if len(tmpDf) == 0:
				print('  error: got 0 length for analysisname:', analysisname)
				continue
			for catName in self.masterCatColumns:
				if catName == self.analysisName:
					# this is column we grouped by, already in meanDf
					continue

				# find value of catName column from 1st instance in masterDf
				catValue = tmpDf[catName].iloc[0]

				theseRows = (meanDf[self.analysisName]==analysisname).tolist()
				meanDf.loc[theseRows, catName] = catValue
				#print('catName:', catName, 'catValue:', type(catValue), catValue)
		#
		# is good
		#meanDf.insert(1, 'isGood', 0)

		#
		# sort
		#meanDf = meanDf.sort_values(['Region', 'Sex', 'Condition'])
		if self.sortOrder is not None:
			meanDf = meanDf.sort_values(self.sortOrder)
		meanDf['index'] = [x+1 for x in range(len(meanDf))]
		meanDf = meanDf.reset_index()
		meanDf = meanDf.round(3)
		#
		if verbose:
			print('getMeanDf():')
			print(meanDf)
		#
		return meanDf

	def update2(self):
		xStatHuman = self.xDropdown.currentText()
		yStatHuman = self.yDropdown.currentText()
		print('update2() xStatHuman:', xStatHuman, 'yStatHuman:', yStatHuman)
		#xStat = self.statNameMap[xStatHuman]
		#yStat = self.statNameMap[yStatHuman]
		xStat = self.statListDict[xStatHuman]['yStat']
		yStat = self.statListDict[yStatHuman]['yStat']

		xIsCategorical = pd.api.types.is_string_dtype(self.masterDf[xStat].dtype)
		yIsCategorical = pd.api.types.is_string_dtype(self.masterDf[yStat].dtype)
		#print('xIsCategorical:', xIsCategorical, 'yIsCategorical:', yIsCategorical)

		self.axes[0].clear()
		#self.axes[1].clear()

		# per cell mean
		if self.dataType == 'All Spikes':
			meanDf = self.masterDf
			# need to sort so onPick works
			if self.sortOrder is not None:
				meanDf = meanDf.sort_values(self.sortOrder)
			#meanDf['index'] = [x+1 for x in range(len(meanDf))]

			print(' before removing nan rows:', len(meanDf))
			# remove rows that have nan in our x or y stat
			meanDf = meanDf[~meanDf[xStat].isnull()]
			meanDf = meanDf[~meanDf[yStat].isnull()]
			print(' after removing nan rows:', len(meanDf))

			meanDf = meanDf.reset_index()
		elif self.dataType == 'File Mean':
			# self.getMeanDf sort by self.sortOrder
			meanDf = self.getMeanDf(xStat, yStat)
		else:
			print('error in self.dataType:', self.dataType)

		# remove x/y nan values from meanDf
		# for onPick to work, we need to remove nans

		# keep track of what we are plotting (todo: put this in a dict)
		self.plotDf = meanDf # use this to get back to row on self.onPick
		self.plotStatx = xStat
		self.plotStaty = yStat

		plotType = self.plotType
		if self.hue == 'None':
			# special case, we do not want None in self.statNameMap
			hue = None
		else:
			#hue = self.statNameMap[self.hue]
			# don't map hue
			hue = self.hue

		self.whatWeArePlotting = None

		warningStr = ''
		picker = 5
		if plotType == 'Scatter Plot':
			try:
				self.whatWeArePlotting = sns.scatterplot(x=xStat, y=yStat, hue=hue,
						data=meanDf, ax=self.axes[0], picker=picker)
			except (ValueError) as e:
				self.fig.canvas.draw()
				print('EXCEPTION:', e)

		elif plotType == 'Histogram':
			yStatHuman = 'Count'
			kde = True
			g = sns.histplot(x=xStat, hue=hue, kde=self.doKDE,
					data=meanDf, ax=self.axes[0], picker=picker)

		elif plotType == 'Cumulative Histogram':
			yStatHuman = 'Probability'
			g = sns.histplot(x=xStat, hue=hue, cumulative=True, stat='density',
					element="step", fill=False, common_norm=False,
					data=meanDf, ax=self.axes[0], picker=picker)

		elif plotType == 'Violin Plot':
			if not xIsCategorical:
				warningStr = 'Violin plot requires a categorical x statistic'
			else:
				g = sns.violinplot(x=xStat, y=yStat, hue=hue,
						data=meanDf, ax=self.axes[0])

		elif plotType == 'Box Plot':
			if not xIsCategorical:
				warningStr = 'Box plot requires a categorical x statistic'
			else:
				g = sns.boxplot(x=xStat, y=yStat, hue=hue,
						data=meanDf, ax=self.axes[0])

		elif plotType == 'Raw + Mean Plot':
			if not xIsCategorical:
				warningStr = 'Raw + Mean plot requires a categorical x statistic'
			else:
				try:
					#print(meanDf)

					'''
					colorList = [('red'), ('green'), 'b', 'c', 'm', 'y']
					hueList = meanDf[hue].unique()
					palette = {}
					for idx, hue in enumerate(hueList):
						palette[hue] = colorList[idx]
					print(palette)
					'''

					palette = sns.color_palette("Paired")
					#palette = ['r', 'g', 'b']

					g = sns.stripplot(x=xStat, y=yStat,
							hue=hue,
							palette=palette,
							data=meanDf,
							ax=self.axes[0],
							picker=picker,
							zorder=1)

					#g.legend().remove()
					self.axes[0].legend().remove()

					handles, labels = self.axes[0].get_legend_handles_labels()
					l = self.axes[0].legend(handles[0:2], labels[0:2], bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

					'''
					if self.darkTheme:
						color = 'w'
					else:
						color = 'k'
					color = [color] * len(hueList)
					print('color:', color)
					'''

					self.whatWeArePlotting = sns.pointplot(x=xStat, y=yStat,
							hue=hue,
							palette=palette,
							data=meanDf,
							estimator=np.nanmean,
							ci=68, capsize=0.1,
							ax=self.axes[0],
							#legend='full',
							zorder=10)

				except (ValueError) as e:
					print('EXCEPTION in "Raw + Mean Plot":', e)
					traceback.print_exc()

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
					if oneHue == 'None':
						continue
					tmpDf = meanDf [ meanDf[hue]==oneHue ]
					#print('regplot oneHue:', oneHue, 'len(tmpDf)', len(tmpDf))
					sns.regplot(x=xStat, y=yStat, data=tmpDf,
							ax=self.axes[0]);

		#
		# picker
		self.axes[0].figure.canvas.mpl_connect("pick_event", self.onPick)

		if self.doHover and self.whatWeArePlotting is not None:
			c2 = mplcursors.cursor(self.whatWeArePlotting, hover=True)
			@c2.connect("add")
			def _(sel):
				#sel.annotation.get_bbox_patch().set(fc="white")
				sel.annotation.arrow_patch.set(arrowstyle="simple", fc="white", alpha=.5)
				# row in df is from sel.target.index
				#print('sel.target.index:', sel.target.index)
				ind = sel.target.index
				myText = self.getAnnotation(ind)
				sel.annotation.set_text(myText)

		'''
		# hover, make a popup showing x/y stat and original file on hover
		self.axes[0].figure.canvas.mpl_connect("motion_notify_event", self.onHover)

		self.annot = self.axes[0].annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
						bbox=dict(boxstyle="round", fc="w"),
						arrowprops=dict(arrowstyle="->"))
		self.annot.set_visible(False)
		'''

		#
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
		# update the table showing a database of mean
		try:
			meanDf = self.getMeanDf(xStat, yStat)

			# before we set the model, remove some columns
			#modelMeanDf = meanDf.drop(['level_0', 'File Number', 'analysisname'], axis=1)
			#modelMeanDf = meanDf.drop(['level_0', 'File Number', self.analysisName], axis=1)
			#modelMeanDf = meanDf.drop(['level_0', self.analysisName], axis=1)
			modelMeanDf = meanDf.drop(['level_0'], axis=1)

			self.yDf = modelMeanDf

			self.myModel = sanpy.bUtil.pandasModel(modelMeanDf)
			#self.tableView.setModel(self.myModel)
			self._switchTableModel(self.myModel)
		except (pd.core.base.DataError) as e:
			print('EXCEPTION:', e)

	def onPick(self, event):
		"""
		when user clicks on a point in the graph

		todo: this makes perfect sense for scatter but maybe not other plots???
		"""
		print('=== onPick()') #' event:', type(event), event)
		line = event.artist

		# when categorical x, line switches (superior/inferior)
		# then ind is within that categorical line
		'''
		print('  type(event)', type(event))
		print('  line:', line)
		print('  type(line)', type(line))
		'''

		# error
		# 'PathCollection' object has no attribute 'get_data'
		#xdata, ydata = line.get_data()

		# filter out clicks on 'Annotation' used by mplcursors
		try:
			# when Scatter, line is 'PathCollection', a list of (x,y)
			offsets = line.get_offsets()
		except (AttributeError) as e:
			return
		#print('offsets:', offsets)

		# ind corresponds to the list in the table???
		# if meanDf we sorted by 'region'
		# can pick off any other value in the mean df by row[ind]
		ind = event.ind # ind is a list []
		#print('  ind:', ind)
		if len(ind)==0:
			return
		ind = ind[0]
		#print('on pick line:', np.array([xdata[ind], ydata[ind]]).T)

		# ind is the ith element in (x,y) list of offsets
		# ind 10 (0 based) is index 11 (1 based) in table list
		print(f'  selected from plot ind:{ind}, offsets values are {offsets[ind]}')
		myString = self.getAnnotation(ind)
		print(myString)

	def getAnnotation(self, ind):
		# todo: replace with _getStatFromPlot

		if not np.issubdtype(ind, np.integer):
			print('getAnnotation() got bad ind:', ind, type(ind))
			return

		analysisName = self.plotDf.at[ind, self.analysisName]
		index = self.plotDf.at[ind, 'index']
		region = self.plotDf.at[ind, 'region'] # not all will have this
		xVal = self.plotDf.at[ind, self.plotStatx]
		yVal = self.plotDf.at[ind, self.plotStaty]

		theRet = f'index: {index}\n'
		theRet += f'analysisName: {analysisName}\n'
		theRet += f'region: {region}\n'
		theRet += f'{self.plotStatx}: {xVal}\n'
		theRet += f'{self.plotStaty}: {yVal}'

		return theRet

	# see: https://stackoverflow.com/questions/7908636/possible-to-make-labels-appear-when-hovering-over-a-point-in-matplotlib
	"""
	def onHover(self, event):
		print('onHover:', type(event), 'inaxes:', event.inaxes)
		if event.inaxes == self.axes[0]:
			print('  in plotted axes')
		else:
			print('  not in plotted axes:', self.axes[0])

		print('  whatWeArePlotting:', type(self.whatWeArePlotting))
		cont, ind = self.whatWeArePlotting.contains(event)
		print('  cont:', cont)
		print('  ind:', ind)
		'''
		ind = event.ind # ind is a list []
		ind = ind[0]
		self._getStatFromPlot(ind)
		'''
	"""

	def _getStatFromPlot(self, ind):
		"""
		get stat from self.plotDf from connected click/hover
		"""
		analysisName = self.plotDf.at[ind, self.analysisName]
		index = self.plotDf.at[ind, 'index']
		region = self.plotDf.at[ind, 'region']
		xVal = self.plotDf.at[ind, self.plotStatx]
		yVal = self.plotDf.at[ind, self.plotStaty]
		print(f'index:{index}, analysisName:{analysisName}, region:{region}, {self.plotStatx}:{xVal}, {self.plotStaty}:{yVal}')

if __name__ == '__main__':
	"""
	20210112, extending this to work with any csv. Starting with nodes/edges from bimpy
	"""

	# todo: using 'analysisname' for group by, I think I can also use 'File Number'
	statListDict = None # list of dict mapping human readbale to column names

	# machine learning db
	if 0:
		# this is from mac laptop
		#path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'
		path = '/Users/cudmore/data/laura-ephys/SANdatabaseForMachineLearning.xlsx'
		analysisName = 'File Number'
		#statListDict = None #sanpy.bAnalysisUtil.getStatList()
		categoricalList = ['LOCATION', 'SEX', 'File Number']#, 'File Name']
		hueTypes = ['LOCATION', 'SEX', 'File Number'] #, 'File Name'] #, 'None']
		sortOrder = ['LOCATION', 'SEX', 'File Number']

	# sanpy database
	if 0:
		#import sanpy

		# this is from mac laptop
		#path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'
		path = '../examples/Superior vs Inferior database_master.csv'
		path = '/Users/cudmore/data/laura-ephys/Superior_Inferior_database_master_jan25.csv'
		path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'
		analysisName = 'analysisname'
		#statListDict = None #sanpy.bAnalysisUtil.getStatList()
		categoricalList = ['Condition', 'Sex', 'Region', 'File Number']#, 'File Name']
		hueTypes = ['Region', 'Sex', 'Condition', 'File Number'] #, 'File Name'] #, 'None']
		sortOrder = ['Region', 'Sex', 'Condition']

	# bimpy database
	if 0:
		path = '../examples/edges_db.csv'
		analysisName = 'fileNumber'
		categoricalList = ['san', 'region', 'path', 'file', 'fileNumber', 'nCon']
		hueTypes = categoricalList
		sortOrder = ['san', 'region']

	# dualAnalysis database
	if 1:
		# grab our list of dict mapping human readable to .csv column names
		sys.path.append(os.path.join(os.path.dirname(sys.path[0]),'sanpy'))
		import bAnalysisUtil
		statListDict = bAnalysisUtil.statList

		path = '/Users/cudmore/Desktop/dualAnalysis_db.csv'
		analysisName = 'fileNumber' # # rows in .xlsx database, one recording per row
		# trial is 1a/1b/1c... trial withing cellNumber
		categoricalList = ['include', 'region', 'fileNumber', 'cellNumber', 'trial', 'quality']
		hueTypes = categoricalList
		sortOrder = ['region']

	#
	app = QtWidgets.QApplication(sys.argv)

	ex = bScatterPlotMainWindow(path, categoricalList, hueTypes,
					analysisName, sortOrder, statListDict=statListDict)

	sys.exit(app.exec_())
