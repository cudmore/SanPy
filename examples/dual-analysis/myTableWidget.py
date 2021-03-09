import sys, os

import pandas as pd

from PyQt5 import QtCore, QtGui, QtWidgets

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

class myPandasModel(QtCore.QAbstractTableModel):

	def __init__(self, data):
		"""
		data: pandas dataframe
		"""
		QtCore.QAbstractTableModel.__init__(self)
		self._data = data
		columnList = self._data.columns.values.tolist()
		if 'include' in columnList:
			self.includeCol = columnList.index('include')
		else:
			self.includeCol = None
		#print('pandasModel.__init__() self.includeCol:', self.includeCol)

	def rowCount(self, parent=None):
		return self._data.shape[0]

	def columnCount(self, parnet=None):
		return self._data.shape[1]

	def data(self, index, role=QtCore.Qt.DisplayRole):
		#print('data() role:', role)
		if index.isValid():
			if role == QtCore.Qt.DisplayRole:

				#return QtCore.QVariant()

				#return str(self._data.iloc[index.row(), index.column()])
				#row = index.row()
				#column = index.column()
				retVal = self._data.iloc[index.row(), index.column()]
				if isinstance(retVal, np.float64):
					retVal = float(retVal)
					if np.isnan(retVal):
						retVal = ''
				elif isinstance(retVal, np.int64):
					retVal = int(retVal)
				#
				#if column == 4:
				#	print(row, column, type(retVal), f'"{retVal}"')
				#if column == 5:
				#	print('  ', row, column, type(retVal), f'"{retVal}"')

				#
				return retVal
			else:
				return QtCore.QVariant()
			#elif role == QtCore.Qt.BackgroundRole:
			#	return

		return None

	def update(self, dataIn):
		print('myPandasModel.update()', dataIn)

	def setData(self, index, value, role=QtCore.Qt.DisplayRole):
		"""
		This is curently limited to only handle checkbox
		todo: extend to allow editing

		Returns:
			True if value is changed. Calls layoutChanged after update.
			False if value is not different from original value.
		"""
		print('myPandasModel.setData() row:', index.row(), 'column:', index.column(), 'value:', value, type(value))
		#if index.column() == self.includeCol:

		#self.dataChanged.emit(index, index)

		if 1:

			#print('value:', value, type(value))
			v = self._data.iloc[index.row(), index.column()]
			#print('before v:',v, type(v))
			#print('isinstance:', isinstance(v, np.float64))
			if isinstance(v, np.float64):
				try:
					value = float(value)
				except (ValueError) as e:
					print('please enter a number')
					return False

			# set
			self._data.iloc[index.row(), index.column()] = value

			v = self._data.iloc[index.row(), index.column()]
			print('after v:',v, type(v))
			return True
		return True

	def flags(self, index):
		#if index.column() == self.includeCol:
		if 1:
			# turn on editing (limited to checkbox for now)
			return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
		else:
			return QtCore.Qt.ItemIsEnabled

	def headerData(self, col, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
			return self._data.columns[col]
		return None

class myTableWidget(QtWidgets.QWidget):
	"""
	A widget which holds a QTableView and uses a data model :class:`myPandasModel`.
	The table is represented as a Pandas data frame and can be instantiated with either
	a file path (csv, xls, xlsx) or an existing DataFrame.
	Args:
		path (str): Full path to tiff file, this is used to open single timepoint stacks (not stacks in a map)
		df (DataFrame): existing dataframe
	"""
	def __init__(self, path=None, df=None, parent=None):
		super(myTableWidget, self).__init__(parent)
		if path is not None and os.path.isfile(path):
			pass
		elif df is not None:
			pass
		self.path = path
		self.buildUI()
		self.setModelFromCsv(path)

	def buildUI(self):
		hBoxLayout = QtWidgets.QHBoxLayout(self)

		self.tableView = QtWidgets.QTableView()
		self.tableView.setFont(QtGui.QFont('Arial', 10))
		self.tableView.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
								  QtWidgets.QSizePolicy.Expanding)

		# left mouse clicks will select rows
		self.tableView.clicked.connect(self.tableViewClicked)
		self.tableView.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

		# right mouse click brings up menu
		self.tableView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.tableView.customContextMenuRequested.connect(self.rightClickTable)

		p = self.tableView.palette();
		color1 = QtGui.QColor('#dddddd')
		color2 = QtGui.QColor('#ffffff')
		p.setColor(QtGui.QPalette.Base, color1);
		p.setColor(QtGui.QPalette.AlternateBase, color2);
		self.tableView.setAlternatingRowColors(True)
		self.tableView.setPalette(p);

		#
		hBoxLayout.addWidget(self.tableView)

		#
		self.setLayout(hBoxLayout)

		self.setGeometry(100, 100, 700, 500) # x,y,w,h

	def getSelectedRow(self):
		selectionModel = self.tableView.selectionModel()
		if selectionModel is None:
			return None
		selectedRowItems = selectionModel.selectedRows() # a list of selected row items
		selectedRow = None
		if len(selectedRowItems)>0:
			selectedRowItem = selectedRowItems[0]
			selectedRow = selectedRowItem.row()
			#print('  selectedRow:', selectedRow)
		else:
			pass
			#print('  no selected rows')

		#
		return selectedRow

	def rightClickTable(self, position):
		"""
		abstract method, redefine in derived classes to:
			show popup and take action
		"""
		print('rightClickTable()')
		selectionModel = self.tableView.selectionModel()
		if selectionModel is None:
			return None
		selectedRowItems = selectionModel.selectedRows() # a list of selected row items
		selectedRow = None
		if len(selectedRowItems)>0:
			selectedRowItem = selectedRowItems[0]
			selectedRow = selectedRowItem.row()
			print('  selectedRow:', selectedRow)
		else:
			print('  no selected rows')

		#
		return selectedRow

	# todo: this does nothin -->> remove ???
	def tableViewClicked(self, clickedIndex):
		row=clickedIndex.row()
		model=clickedIndex.model()

		#print('tableViewClicked() row:', row)

	def setModelFromCsv(self, csvPath):
		if csvPath is None:
			return
		self.masterDf = self.loadCsv(csvPath)
		if self.masterDf is None:
			self.myModel = None
		else:
			self.myModel = myPandasModel(self.masterDf)
			self.tableView.setModel(self.myModel)

		self.setWindowTitle(csvPath)

	def setModelFromDf(self, df):
		self.masterDf = df
		self.myModel = myPandasModel(self.masterDf)
		self.tableView.setModel(self.myModel)

	def loadCsv(self, path):
		masterDf = None
		if not os.path.isfile(path):
			print('eror: loadCsv() did not find file:', path)
		elif path.endswith('.csv'):
			masterDf = pd.read_csv(path, header=0) #, dtype={'ABF File': str})
		elif path.endswith('.xls'):
			masterDf = pd.read_excel(path, header=0) #, dtype={'ABF File': str})
		elif path.endswith('.xlsx'):
			masterDf = pd.read_excel(path, header=0, engine='openpyxl') #, dtype={'ABF File': str})
		else:
			print('error: file type not supported. Expecting csv/xls/xlsx. path:', path)

		return masterDf

if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)

	# ccreate an empty table widget
	ex = myTableWidget()

	# populate from csv
	path = 'dual-database.xlsx'
	ex.setModelFromCsv(path)

	#
	ex.show()
	sys.exit(app.exec_())
