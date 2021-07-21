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

	'''
	signalUnloadRow = QtCore.pyqtSignal(object)  # row index
	signalRemoveFromDatabase = QtCore.pyqtSignal(object)  # row index
	signalDuplicateRow = QtCore.pyqtSignal(object)  # row index
	signalDeleteRow = QtCore.pyqtSignal(object)  # row index
	#signalRefreshTabe = QtCore.pyqtSignal(object) # row index
	signalCopyTable = QtCore.pyqtSignal()
	signalFindNewFiles = QtCore.pyqtSignal()

	signalSaveFileTable = QtCore.pyqtSignal()
	"""Save entire database as pandas hsf."""
	'''

	signalSelectRow = QtCore.pyqtSignal(object, object)  # (row, rowDict)

	signalUpdateStatus = QtCore.pyqtSignal(object)
	"""Update status in main SanPy app."""

	signalSetDefaultDetection = QtCore.pyqtSignal(object, object)  # selected row, detection type

	def __init__(self, model, parent=None):
		super(bTableView, self).__init__(parent)

		self.lastSeletedRow = None
		self.clicked.connect(self.onLeftClick)

		#
		# frozen
		self.setModel(model)

		# (L, A, S, I, File)
		self.numFrozenColumns = 5 # depends on columns in analysisDir

		self.frozenTableView = QtWidgets.QTableView(self)
		self.frozenTableView.clicked.connect(self.onLeftClick)
		self.frozenTableView.setSortingEnabled(True)
		self.frozenTableView.setSelectionBehavior(QtWidgets.QTableView.SelectRows)  # abb
		# only allow one row to be selected
		self.frozenTableView.setSelectionMode(QtWidgets.QTableView.SingleSelection)
		self.initFrozenColumn()
		self.horizontalHeader().sectionResized.connect(self.updateSectionWidth)
		self.verticalHeader().sectionResized.connect(self.updateSectionHeight)
		self.frozenTableView.verticalScrollBar().valueChanged.connect(
			self.verticalScrollBar().setValue)
		self.verticalScrollBar().valueChanged.connect(
			self.frozenTableView.verticalScrollBar().setValue)

		# rewire contextMenuEvent to self (WIERD BUT SEEMS TO WORK)
		self.frozenTableView.contextMenuEvent = self.contextMenuEvent

		#
		# original
		#self.doIncludeCheckbox = False  # todo: turn this on
		# need a local reference to delegate else 'segmentation fault'
		#self.keepCheckBoxDelegate = myCheckBoxDelegate(self)
		#self.setItemDelegateForColumn(1, self.keepCheckBoxDelegate)

		self.setSortingEnabled(True)

		self.setFont(QtGui.QFont('Arial', 10))
		self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
							QtWidgets.QSizePolicy.Expanding)
		self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
		# only allow one row to be selected
		# should ignore shift+click
		self.setSelectionMode(QtWidgets.QTableView.SingleSelection)


		self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers
							| QtWidgets.QAbstractItemView.DoubleClicked)

		self.horizontalHeader().setStretchLastSection(True)

		rowHeight = 11
		fnt = self.font()
		fnt.setPointSize(rowHeight)
		self.setFont(fnt)
		self.verticalHeader().setDefaultSectionSize(rowHeight)

		# todo: minimize all column widths
		#for col in range(showNumCol):
		#	self.frozenTableView.setColumnWidth(col, self.columnWidth(col))

		# frozen column
		#self.frozenTableView.setFont(QtGui.QFont('Arial', 10))
		self.frozenTableView.setFont(fnt)
		self.frozenTableView.verticalHeader().setDefaultSectionSize(rowHeight)

		# TODO: THIS DOES NOTHING !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
		# needed so blue selection stays when losing focus
		'''
		from PyQt5.QtGui import QPalette
		p = self.palette()
		# p.color(goup, role)
		# p.setColor(group, role, color)
		highlightColor = p.color(QtGui.QPalette.Active, QtGui.QPalette.Highlight)
		#p.setColor(QPalette.Inactive, QtGui.QPalette.Highlight,
		#			p.color(QtGui.QPalette.Active, QtGui.QPalette.Highlight))
		p.setColor(QPalette.Active, QPalette.Highlight, highlightColor);
		p.setColor(QPalette.Disabled, QPalette.Highlight, highlightColor);
		p.setColor(QPalette.Inactive, QPalette.Highlight, highlightColor);
		p.setColor(QPalette.Inactive, QPalette.HighlightedText, highlightColor);
		self.setPalette(p);
		'''

		# original was this
		# active background-color: #346792;
		# !active background-color: #37414F;
		qss = """
			QTreeView::item:selected:active,
			QListView::item:selected:active,
			QTableView::item:selected:active,
			QColumnView::item:selected:active {
				background-color: #346792;
			}

			QTreeView::item:selected:!active,
			QListView::item:selected:!active,
			QTableView::item:selected:!active,
			QColumnView::item:selected:!active {
				color: #E0E1E3;
				background-color: #346792;
			}
			"""
		# this almost works but header becomes white???
		#self.setStyleSheet(qss)
		#self.frozenTableView.setStyleSheet(qss)

	#
	# frozen
	def initFrozenColumn(self):
		self.frozenTableView.setModel(self.model())

		# this is causing selection to be in muted blue
		#self.frozenTableView.setFocusPolicy(QtCore.Qt.NoFocus)

		self.frozenTableView.verticalHeader().hide()
		#self.frozenTableView.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
		self.viewport().stackUnder(self.frozenTableView)

		#self.frozenTableView.setStyleSheet('''
		#	QtWidgets.QTableView { border: none;
		#				 background-color: #8EDE21;
		#				 selection-background-color: #999;
		#	}''') # for demo purposes

		self.frozenTableView.setSelectionModel(self.selectionModel())

		# hide trailing column
		for col in range(self.numFrozenColumns, self.model().columnCount()):
			self.frozenTableView.setColumnHidden(col, True)

		# set width of remaining columns
		for col in range(self.numFrozenColumns):
			#print('  col:', col, 'widht:', self.columnWidth(col))
			columnWidth = self.columnWidth(col)
			columnWidth = 28
			self.frozenTableView.setColumnWidth(col, columnWidth)
			#self.setColumnWidth(col, columnWidth)
		#columnWidth = 150
		#self.frozenTableView.setColumnWidth(self.numFrozenColumns-1, columnWidth)
		#self.setColumnWidth(self.numFrozenColumns-1, columnWidth)

		#self.frozenTableView.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
		#					QtWidgets.QSizePolicy.Expanding)

		self.frozenTableView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.frozenTableView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.frozenTableView.show()
		self.updateFrozenTableGeometry()
		self.setHorizontalScrollMode(self.ScrollPerPixel)
		self.setVerticalScrollMode(self.ScrollPerPixel)
		self.frozenTableView.setVerticalScrollMode(self.ScrollPerPixel)

		# set Loaded and Analyzed columns
		self.frozenTableView.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
		self.frozenTableView.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
		self.frozenTableView.horizontalHeader().setStretchLastSection(True)

	# does not work ???
	def onLeftClick(self, item):
		"""Hanlde user left-click on a row. Keep track of lastSelected row to differentiate between
		switch-file and click again.
		"""
		row = item.row()
		realRow = self.model()._data.index[row] # sort order
		logger.info(f'User clicked row:{row} realRow:{realRow}')
		if self.lastSeletedRow is None or self.lastSeletedRow != realRow:
			# new row selection
			#print('  new row selection')
			rowDict = self.model().myGetRowDict(realRow)
			logger.info(f'realRow:{realRow} rowDict:{rowDict}')
			self.signalSelectRow.emit(realRow, rowDict)
		else:
			#print('  handle another click on already selected row')
			pass
		self.lastSeletedRow = realRow

	def old_selectionChanged(self, selected, deselected):
		logger.info('')
		modelIndexList = selected.indexes()
		if len(modelIndexList) == 0:
			return

		super(bTableView, self).selectionChanged(selected, deselected)
		#self.frozenTableView.selectionChanged(selected, deselected)
		modelIndex = modelIndexList[0]
		#row = modelIndex.row()
		column = modelIndex.column()

		realRow = self.model()._data.index[modelIndex.row()]

		# assuming model is my pandas model
		rowDict = self.model().myGetRowDict(realRow)

		logger.info(f'realRow:{realRow} col:{column} {rowDict}')

		self.signalSelectRow.emit(realRow, rowDict)

	def mySetModel(self, model):
		"""
		Set the model. Needed so we can show/hide columns

		Args:
			model (xxx):
		"""
		logger.info('')

		self.setModel(model)

		self.frozenTableView.setModel(self.model())
		# this is required otherwise selections become disconnected
		self.frozenTableView.setSelectionModel(self.selectionModel())

	def mySelectRow(self, rowIdx):
		"""Needed to connect main and frozen table."""
		logger.info('')

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
		#
		unloadData = contextMenu.addAction("Unload Data")
		contextMenu.addSeparator()
		removeFromDatabase = contextMenu.addAction("Remove From Database")
		contextMenu.addSeparator()
		duplicateRow = contextMenu.addAction("Duplicate Row")
		contextMenu.addSeparator()
		deleteRow = contextMenu.addAction("Delete Row")
		contextMenu.addSeparator()
		copyTable = contextMenu.addAction("Copy Table")
		contextMenu.addSeparator()
		findNewFiles = contextMenu.addAction("Sync With Folder")
		contextMenu.addSeparator()
		saveAllAnalysis = contextMenu.addAction("Save All Analysis")
		contextMenu.addSeparator()
		saNodeParams = contextMenu.addAction('SA Node Params')
		saNodeParams = contextMenu.addAction('Ventricular Params')
		neuronParams = contextMenu.addAction('Neuron Params')
		#
		action = contextMenu.exec_(self.mapToGlobal(event.pos()))
		#logger.info(f'  action:{action}')
		selectedRow = None
		tmp = self.selectedIndexes()
		if len(tmp)>0:
			selectedRow = tmp[0].row() # not in sort order

		if action == unloadData:
			#self.signalUnloadRow.emit(selectedRow) # not in sort order
				self.model().myUnloadRow(selectedRow)
		elif action == removeFromDatabase:
			#self.signalRemoveFromDatabase.emit(selectedRow) # not in sort order
			self.model().myRemoveFromDatabase(selectedRow)
		elif action == duplicateRow:
			#self.signalDuplicateRow.emit(selectedRow) # not in sort order
			self.model().myDuplicateRow(selectedRow)
		elif action == deleteRow:
			#self.signalDeleteRow.emit(selectedRow)
			self.model().myDeleteRow(selectedRow)
		elif action == copyTable:
			#self.signalCopyTable.emit()
			self.model().myCopyTable()
		elif action == findNewFiles:
			#self.signalFindNewFiles.emit()
			self.model().mySyncDfWithPath()
		elif action == saveAllAnalysis:
			#self.signalSaveFileTable.emit()
			self.model().saveHdf()
		elif action in [saNodeParams, neuronParams]:
			#print(action, action.text())
			if selectedRow is not None:
				self.signalSetDefaultDetection.emit(selectedRow, action.text())
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
		logger.info('')
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
		logger.info('')
		if index.column() > 0:
			super(bTableView, self).scrollTo(index, hint)

	def updateFrozenTableGeometry(self):
		#myWidth = self.columnWidth(0) + self.columnWidth(1) + self.columnWidth(2)
		myWidth = 0
		for i in range(self.numFrozenColumns):
			#logger.info(f'{i} {self.frozenTableView.columnWidth(i)}')
			myWidth += self.columnWidth(i)

		self.frozenTableView.setGeometry(
			self.verticalHeader().width() + self.frameWidth(),
			self.frameWidth(),
			#self.columnWidth(0),
			myWidth,
			self.viewport().height() + self.horizontalHeader().height())

	def slot_detect(self, ba):
		"""Find row of _ba and update model
		"""
		tmp = self.selectedIndexes()
		if len(tmp)>0:
			selectedRow = tmp[0].row() # not in sort order
		self.model().myUpdateLoadedAnalyzed(ba, selectedRow)

def test():
	import sys
	app = QtWidgets.QApplication([])

	path = '/home/cudmore/Sites/SanPy/data'
	ad = sanpy.analysisDir(path)

	df = ad.getDataFrame()
	print('df:')
	print(df)
	model = sanpy.interface.bFileTable.pandasModel(ad)

	# make an empty dataframe with just headers !!!
	dfEmpty = pd.DataFrame(columns=sanpy.analysisDir.sanpyColumns.keys())
	#dfEmpty = dfEmpty.append(pd.Series(), ignore_index=True)
	#dfEmpty['_ba'] = ''
	print('dfEmpty:')
	print(dfEmpty)
	emptyModel = sanpy.interface.bFileTable.pandasModel(dfEmpty)

	btv = bTableView(model)
	#btv.mySetModel(model)

	btv.show()

	sys.exit(app.exec_())

if __name__ == '__main__':
	test()
