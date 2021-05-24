# 20210212
import os, math

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtGui, QtWidgets

def loadDatabase(path):
	"""
	path: full path to .csv file generated with reanalyze.py
	"""
	#path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'
	masterDf = None
	if path is None:
		pass
	elif not os.path.isfile(path):
		print(f'error: bUtil.loadDatabase() did not find file: "{path}"')
	elif path.endswith('.csv'):
		masterDf = pd.read_csv(path, header=0) #, dtype={'ABF File': str})
	elif path.endswith('.xls'):
		masterDf = pd.read_excel(path, header=0) #, dtype={'ABF File': str})
	elif path.endswith('.xlsx'):
		masterDf = pd.read_excel(path, header=0, engine='openpyxl') #, dtype={'ABF File': str})
	else:
		print('error: file type not supported. Expecting csv/xls/xlsx. Path:', path)

	#self.masterDfColumns = self.masterDf.columns.to_list()

	# not sure what this was for ???
	# 20210112, put back in if necc
	#self.masterCatColumns = ['Condition', 'File Number', 'Sex', 'Region', 'filename', 'analysisname']
	#self.masterCatColumns = self.categoricalList

	#print(self.masterDf.head())
	'''
	print(masterDf.info())
	print('masterDf.iloc[0,3]:', masterDf.iloc[0,3], type(masterDf.iloc[0,3]))
	print('start seconds:', masterDf['Start Seconds'].dtype.type)
	print('start seconds:', masterDf['Start Seconds'].dtype)
	'''
	#
	return masterDf

def printDict(d, withType=False):
	for k,v in d.items():
		if withType:
			print(f'  {k}: {v} {type(v)}')
		else:
			print(f'  {k}: {v}')

class errorTableView(QtWidgets.QTableView):
	def __init__(self, parent=None):
		super(errorTableView, self).__init__(parent)

		self.setFont(QtGui.QFont('Arial', 10))
		self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
								  QtWidgets.QSizePolicy.Expanding)
		self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

		self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers |
							 QtWidgets.QAbstractItemView.DoubleClicked)

		#self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch);
		self.horizontalHeader().setStretchLastSection(True)

		rowHeight = 11
		fnt = self.font()
		fnt.setPointSize(rowHeight)
		self.setFont(fnt)
		self.verticalHeader().setDefaultSectionSize(rowHeight);

		'''
		p = self.palette()
		color1 = QtGui.QColor('#dddddd')
		color2 = QtGui.QColor('#ffffff')
		p.setColor(QtGui.QPalette.Base, color1)
		p.setColor(QtGui.QPalette.AlternateBase, color2)
		self.setAlternatingRowColors(True)
		self.setPalette(p)
		'''

class myTableView(QtWidgets.QTableView):
	'''
	signalDuplicateRow = QtCore.Signal(object) # row index
	signalDeleteRow = QtCore.Signal(object) # row index
	#signalRefreshTabe = QtCore.Signal(object) # row index
	signalCopyTable = QtCore.Signal()
	signalFindNewFiles = QtCore.Signal()
	'''
	signalDuplicateRow = QtCore.pyqtSignal(object) # row index
	signalDeleteRow = QtCore.pyqtSignal(object) # row index
	#signalRefreshTabe = QtCore.pyqtSignal(object) # row index
	signalCopyTable = QtCore.pyqtSignal()
	signalFindNewFiles = QtCore.pyqtSignal()
	signalSaveFileTable = QtCore.pyqtSignal()

	def __init__(self, parent=None):
		"""
		"""
		super(myTableView, self).__init__(parent)

		self.doIncludeCheckbox = False # todo: turn this on
		self.keepCheckBoxDelegate = myCheckBoxDelegate(None)

		self.setFont(QtGui.QFont('Arial', 10))
		self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
								  QtWidgets.QSizePolicy.Expanding)
		self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

		self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers |
							 QtWidgets.QAbstractItemView.DoubleClicked)

		rowHeight = 11
		fnt = self.font()
		fnt.setPointSize(rowHeight)
		self.setFont(fnt)
		self.verticalHeader().setDefaultSectionSize(rowHeight);
		'''
		p = self.palette()
		color1 = QtGui.QColor('#dddddd')
		color2 = QtGui.QColor('#ffffff')
		p.setColor(QtGui.QPalette.Base, color1)
		p.setColor(QtGui.QPalette.AlternateBase, color2)
		self.setPalette(p)
		self.setAlternatingRowColors(True)
		'''

	#def keyPressEvent(self, event): #Reimplement the event here, in your case, do nothing
	#	return

	def contextMenuEvent(self, event):
		"""
		handle right mouse click
		"""
		print('myTableView.contextMenuEvent() event:', event)
		contextMenu = QtWidgets.QMenu(self)
		duplicateRow = contextMenu.addAction("Duplicate Row")
		contextMenu.addSeparator()
		deleteRow = contextMenu.addAction("Delete Row")
		contextMenu.addSeparator()
		copyTable = contextMenu.addAction("Copy Table")
		contextMenu.addSeparator()
		findNewFiles = contextMenu.addAction("Find New Files")
		contextMenu.addSeparator()
		saveTable = contextMenu.addAction("Save Table")
		#
		action = contextMenu.exec_(self.mapToGlobal(event.pos()))
		if action == duplicateRow:
			print('  todo: duplicateRow')
			tmp = self.selectedIndexes()
			if len(tmp)>0:
				selectedRow = tmp[0].row()
				self.signalDuplicateRow.emit(selectedRow)
		elif action == deleteRow:
			#print('  todo: deleteRow')
			tmp = self.selectedIndexes()
			if len(tmp)>0:
				selectedRow = tmp[0].row()
				self.signalDeleteRow.emit(selectedRow)
		elif action == copyTable:
			#print('  todo: copyTable')
			self.signalCopyTable.emit()
		elif action == findNewFiles:
			#print('  todo: findNewFiles')
			self.signalFindNewFiles.emit()
		elif action == saveTable:
			#print('  todo: saveTable')
			self.signalSaveFileTable.emit()

class pandasModel(QtCore.QAbstractTableModel):

	def __init__(self, data):
		"""
		data: pandas dataframe
		"""
		QtCore.QAbstractTableModel.__init__(self)
		self.isDirty = False
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
				retVal = self._data.iloc[index.row(), index.column()]
				if isinstance(retVal, np.float64):
					retVal = float(retVal)
					if np.isnan(retVal):
						retVal = ''
				elif isinstance(retVal, np.int64):
					retVal = int(retVal)
				#
				#print(retVal, type(retVal))
				if isinstance(retVal, float) and math.isnan(retVal):
					# don't show 'nan' in table
					#print('  convert to empty')
					retVal = ''
				return retVal
			elif role == QtCore.Qt.BackgroundRole:
				#return QtCore.QVariant()
				if index.row() % 2 == 0:
					return QtCore.QVariant(QtGui.QColor('#444444'))
				else:
					return QtCore.QVariant(QtGui.QColor('#555555'))

		return None

	def update(self, dataIn):
		print('pandasModel.update()', dataIn)

	def setData(self, index, value, role=QtCore.Qt.EditRole):
		"""
		This is curently limited to only handle checkbox

		Returns:
			True if value is changed. Calls layoutChanged after update.
			False if value is not different from original value.
		"""
		print('pandasModel.setData() row:', index.row(), 'column:', index.column(), 'value:', value, type(value))
		if index.isValid():
			if role == QtCore.Qt.EditRole:
				row = index.row()
				column=index.column()
				#print('value:', value, type(value))
				v = self._data.iloc[row, column]
				#print('before v:',v, type(v))
				#print('isinstance:', isinstance(v, np.float64))
				if isinstance(v, np.float64):
					try:
						value = float(value)
					except (ValueError) as e:
						print('  please enter a number')
						return False
				# set
				self._data.iloc[row, column] = value

				self.isDirty = True

				#print('  after value:',value, type(value))
				return True
		#
		return False

	def flags(self, index):
		#if index.column() == self.includeCol:
		if 1:
			# turn on editing (limited to checkbox for now)
			#return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
			return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

		else:
			return QtCore.Qt.ItemIsEnabled

	def headerData(self, col, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
			return self._data.columns[col]
		return None

	def myCopyTable(self):
		"""
		copy model data to clipboard
		"""
		print('myCopyTable()')
		dfCopy = self._data.copy()
		dfCopy.to_clipboard(sep='\t', index=False)
		#print(dfCopy)

	def myGetValue(self, rowIdx, colStr):
		val = None
		if colStr not in self._data.columns: # columns is a list
			print('error: myGetTableValue() got bad column name:', colStr)
		elif len(self._data)-1 < rowIdx:
			print('error: myGetTableValue() got bad row:', row)
		else:
			val = self._data.loc[rowIdx, colStr]
		return val

	def myGetRowDict(self, rowIdx):
		"""
		return a dict with selected row as dict (includes detection parameters)
		"""
		theRet = {}
		for column in self._data.columns:
			theRet[column] = self.myGetValue(rowIdx, column)
		return theRet

	def myGetColumnList(self, col):
		# return all valuues in column as a list
		colList = self._data[col].tolist()
		return colList

	def myAppendRow(self, rowDict=None):
		# append one empty row
		newRowIdx = len(self._data)
		self.beginInsertRows(QtCore.QModelIndex(), newRowIdx, newRowIdx)

		self._data = self._data.append(pd.Series(), ignore_index=True)
		self._data = self._data.reset_index(drop=True)

		self.endInsertRows()

	def myDeleteRow(self, rowIdx):
		self.beginRemoveRows(QtCore.QModelIndex(), rowIdx, rowIdx)
		df = self._data.drop([rowIdx])
		df = df.reset_index(drop=True)
		self._data = df # REQUIRED
		self.endRemoveRows()

	def myDuplicateRow(self, rowIdx):
		self.beginInsertRows(QtCore.QModelIndex(), rowIdx+1, rowIdx+1)
		newIdx = rowIdx + 0.5
		rowDict = self.myGetRowDict(rowIdx)
		dfRow = pd.DataFrame(rowDict, index=[newIdx])
		df = self._data
		df = df.append(dfRow, ignore_index=False)
		df = df.sort_index().reset_index(drop=True)
		#
		self._data = df # not needed?
		self.endInsertRows()

	def mySetRow(self, row, rowDict):
		print('mySetRow() row:', row, 'rowDict:', rowDict)
		rowSeries = pd.Series(rowDict)
		self._data.iloc[row] = rowSeries
		self._data = self._data.reset_index(drop=True)

	def mySaveDb(self, path):
		print('pandasModel.mySaveDb() path:', path)
		self._data.to_csv(path)
		self.isDirty = False
		
# see: https://stackoverflow.com/questions/17748546/pyqt-column-of-checkboxes-in-a-qtableview
class myCheckBoxDelegate(QtWidgets.QItemDelegate):
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
		print('myCheckBoxDelegate.setModelData()')
		model.setData(index, 1 if int(index.data()) == 0 else 0, QtCore.Qt.EditRole)
