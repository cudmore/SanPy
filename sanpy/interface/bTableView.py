import os, math

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtGui, QtWidgets

# using sanpy.analysisDir in pandasModel.__init__()
import sanpy
import sanpy.interface
#import sanpy.analysisDir
import sanpy.bDetection

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class bTableView(QtWidgets.QTableView):
	"""Table view to display list of files.

	TODO: Try and implement the first column (filename) as a frozen column.

	See:
		#https://doc.qt.io/qt-5/qtwidgets-itemviews-frozencolumn-example.html
		https://github.com/PyQt5/Examples/tree/master/PyQt5/itemviews/frozencolumn
	"""

	signalDuplicateRow = QtCore.pyqtSignal(object)  # row index
	signalDeleteRow = QtCore.pyqtSignal(object)  # row index
	#signalRefreshTabe = QtCore.pyqtSignal(object) # row index
	signalCopyTable = QtCore.pyqtSignal()
	signalFindNewFiles = QtCore.pyqtSignal()
	signalSaveFileTable = QtCore.pyqtSignal()
	signalSelection = QtCore.pyqtSignal(object, object)  # (row, column)

	def __init__(self, model, parent=None):
		super(bTableView, self).__init__(parent)

		#
		# frozen
		self.setModel(model)

		self.frozenTableView = QtWidgets.QTableView(self)
		self.frozenTableView.setSortingEnabled(True)
		self.frozenTableView.setSelectionBehavior(QtWidgets.QTableView.SelectRows)  # abb
		self.init()
		self.horizontalHeader().sectionResized.connect(self.updateSectionWidth)
		self.verticalHeader().sectionResized.connect(self.updateSectionHeight)
		self.frozenTableView.verticalScrollBar().valueChanged.connect(
			self.verticalScrollBar().setValue)
		self.verticalScrollBar().valueChanged.connect(
			self.frozenTableView.verticalScrollBar().setValue)

		#
		# original
		self.doIncludeCheckbox = False  # todo: turn this on
		# need a local reference to delegate else 'segmentation fault'
		self.keepCheckBoxDelegate = myCheckBoxDelegate(None)

		self.setSortingEnabled(True)

		self.setFont(QtGui.QFont('Arial', 10))
		self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
							QtWidgets.QSizePolicy.Expanding)
		self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

		self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers
							| QtWidgets.QAbstractItemView.DoubleClicked)

		rowHeight = 11
		fnt = self.font()
		fnt.setPointSize(rowHeight)
		self.setFont(fnt)
		self.verticalHeader().setDefaultSectionSize(rowHeight)

		# frozen column
		self.frozenTableView.setFont(fnt)
		self.frozenTableView.verticalHeader().setDefaultSectionSize(rowHeight)
	#
	# frozen
	def init(self):
		self.frozenTableView.setModel(self.model())
		self.frozenTableView.setFocusPolicy(QtCore.Qt.NoFocus)
		self.frozenTableView.verticalHeader().hide()
		self.frozenTableView.horizontalHeader().setSectionResizeMode(
				QtWidgets.QHeaderView.Fixed)
		self.viewport().stackUnder(self.frozenTableView)

		#self.frozenTableView.setStyleSheet('''
		#	QtWidgets.QTableView { border: none;
		#				 background-color: #8EDE21;
		#				 selection-background-color: #999;
		#	}''') # for demo purposes

		self.frozenTableView.setSelectionModel(self.selectionModel())
		for col in range(1, self.model().columnCount()):
			self.frozenTableView.setColumnHidden(col, True)
		self.frozenTableView.setColumnWidth(0, self.columnWidth(0))
		self.frozenTableView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.frozenTableView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.frozenTableView.show()
		self.updateFrozenTableGeometry()
		self.setHorizontalScrollMode(self.ScrollPerPixel)
		self.setVerticalScrollMode(self.ScrollPerPixel)
		self.frozenTableView.setVerticalScrollMode(self.ScrollPerPixel)

	def selectionChanged(self, selected, deselected):
		super(bTableView, self).selectionChanged(selected, deselected)
		logger.info(selected)
		modelIndexList = selected.indexes()
		if len(modelIndexList) == 0:
			return
		else:
			modelIndex = modelIndexList[0]
			row = modelIndex.row()
			column = modelIndex.column()
			self.signalSelection.emit(row, column)

	def mySetModel(self, model):
		"""
		Set the model. Needed so we can show/hide columns

		Args:
			model (xxx):
		"""
		self.setModel(model)

		self.frozenTableView.setModel(self.model())
		# this is required otherwise selections become disconnected
		self.frozenTableView.setSelectionModel(self.selectionModel())

	def mySelectRow(self, rowIdx):
		"""Needed to connect main and frozen table."""
		self.selectRow(rowIdx)
		self.frozenTableView.selectRow(rowIdx)

	'''
	# trying to use this to remove tooltip when it comes up as empty ''
	def viewportEvent(self, event):
		logger.info('')
		return True
	'''

	def contextMenuEvent(self, event):
		"""
		handle right mouse click
		"""
		contextMenu = QtWidgets.QMenu(self)
		duplicateRow = contextMenu.addAction("Duplicate Row")
		contextMenu.addSeparator()
		deleteRow = contextMenu.addAction("Delete Row")
		contextMenu.addSeparator()
		copyTable = contextMenu.addAction("Copy Table")
		contextMenu.addSeparator()
		findNewFiles = contextMenu.addAction("Sync With Folder")
		contextMenu.addSeparator()
		saveTable = contextMenu.addAction("Save Table")
		#
		action = contextMenu.exec_(self.mapToGlobal(event.pos()))
		#logger.info(f'  action:{action}')
		if action == duplicateRow:
			#print('  todo: duplicateRow')
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
			else:
				logger.warning('no selection?')
		elif action == copyTable:
			#print('  todo: copyTable')
			self.signalCopyTable.emit()
		elif action == findNewFiles:
			#print('  todo: findNewFiles')
			self.signalFindNewFiles.emit()
		elif action == saveTable:
			#print('  todo: saveTable')
			self.signalSaveFileTable.emit()
		else:
			logger.warning(f'action not taken "{action}"')

#
# frozen
	def updateSectionWidth(self, logicalIndex, oldSize, newSize):
		#if self.logicalIndex == 0:
		if logicalIndex == 0:
			self.frozenTableView.setColumnWidth(0, newSize)
			self.updateFrozenTableGeometry()

	def updateSectionHeight(self, logicalIndex, oldSize, newSize):
		self.frozenTableView.setRowHeight(logicalIndex, newSize)

	def resizeEvent(self, event):
		super(bTableView, self).resizeEvent(event)
		self.updateFrozenTableGeometry()

	def moveCursor(self, cursorAction, modifiers):
		current = super(bTableView, self).moveCursor(cursorAction, modifiers)
		if (cursorAction == self.MoveLeft and
				self.current.column() > 0 and
				self.visualRect(current).topLeft().x() <
					self.frozenTableView.columnWidth(0)):
			newValue = (self.horizontalScrollBar().value() +
						self.visualRect(current).topLeft().x() -
						self.frozenTableView.columnWidth(0))
			self.horizontalScrollBar().setValue(newValue)
		return current

	def scrollTo(self, index, hint):
		if index.column() > 0:
			super(bTableView, self).scrollTo(index, hint)

	def updateFrozenTableGeometry(self):
		self.frozenTableView.setGeometry(
				self.verticalHeader().width() + self.frameWidth(),
				self.frameWidth(), self.columnWidth(0),
				self.viewport().height() + self.horizontalHeader().height())

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


	def setModelData(self, editor, model, index):
		'''
		The user wanted to change the old state in the opposite.
		'''
		print('myCheckBoxDelegate.setModelData()')
		model.setData(index, 1 if int(index.data()) == 0 else 0, QtCore.Qt.EditRole)

def test():
	import sys
	app = QtWidgets.QApplication([])

	path = '/home/cudmore/Sites/SanPy/data'
	ad = sanpy.analysisDir(path)

	df = ad.getDataFrame()
	print('df:')
	print(df)
	model = sanpy.interface.bFileTable.pandasModel(df)

	# make an empty dataframe with just headers !!!
	dfEmpty = pd.DataFrame(columns=sanpy.analysisDir.sanpyColumns.keys())
	#dfEmpty = dfEmpty.append(pd.Series(), ignore_index=True)
	#dfEmpty['_ba'] = ''
	print('dfEmpty:')
	print(dfEmpty)
	emptyModel = sanpy.interface.bFileTable.pandasModel(dfEmpty)

	btv = bTableView(emptyModel)
	#btv.mySetModel(model)

	btv.show()

	sys.exit(app.exec_())

if __name__ == '__main__':
	test()
