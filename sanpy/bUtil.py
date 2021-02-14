# 20210212
import os

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtGui, QtWidgets

def loadDatabase(path):
	"""
	path: full path to .csv file generated with reanalyze.py
	"""
	#path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'
	masterDf = None
	if not os.path.isfile(path):
		print('eror: bUtil.loadDatabase() did not find file:', path)
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
		print(f'  {k}: {v} {type(v)}')

class pandasModel(QtCore.QAbstractTableModel):

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
				retVal = self._data.iloc[index.row(), index.column()]
				if isinstance(retVal, np.float64):
					retVal = float(retVal)
					if np.isnan(retVal):
						retVal = ''
				elif 1:
					# string
					pass
				#
				return retVal
			elif role == QtCore.Qt.BackgroundRole:
				return

		return None

	def update(self, dataIn):
		print('pandasModel.update()', dataIn)

	def setData(self, index, value, role=QtCore.Qt.DisplayRole):
		"""
		This is curently limited to only handle checkbox
		todo: extend to allow editing

		Returns:
			True if value is changed. Calls layoutChanged after update.
			False if value is not different from original value.
		"""
		print('pandasModel.setData() row:', index.row(), 'column:', index.column(), 'value:', value, type(value))
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
			return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
		else:
			return QtCore.Qt.ItemIsEnabled

	def headerData(self, col, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
			return self._data.columns[col]
		return None

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
