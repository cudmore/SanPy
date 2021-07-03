from PyQt5 import QtCore, QtGui, QtWidgets

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class errorTableView(QtWidgets.QTableView):
	"""
	Display a per spike error table (one row per spike eror)
	"""
	signalSelectSpike = QtCore.Signal(object) # spike number, doZoom

	def __init__(self, parent=None):
		super(errorTableView, self).__init__(parent)

		self.setFont(QtGui.QFont('Arial', 10))

		self.setSortingEnabled(True)

		self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
								  QtWidgets.QSizePolicy.Expanding)
		self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

		self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers |
							 QtWidgets.QAbstractItemView.DoubleClicked)

		# equally stretchs each columns so that they fit the table's width.
		#self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch);
		self.horizontalHeader().setStretchLastSection(True)

		rowHeight = 11
		fnt = self.font()
		fnt.setPointSize(rowHeight)
		self.setFont(fnt)
		self.verticalHeader().setDefaultSectionSize(rowHeight);

		#self.resizeColumnsToContents()

		self.clicked.connect(self.errorTableClicked)

	def old_selectionChanged(self, selected, deselected):
		super(errorTableView, self).selectionChanged(selected, deselected)
		logger.info(selected)
		modelIndexList = selected.indexes()
		if len(modelIndexList) == 0:
			return

		doZoom = False
		modifiers = QtGui.QApplication.keyboardModifiers()
		if modifiers == QtCore.Qt.ShiftModifier:
			# zoomm on shift+click
			doZoom = True

		modelIndex = modelIndexList[0]
		row = modelIndex.row()
		#column = modelIndex.column()

		try:
			# .loc[i,'col'] gets from index (wrong)
			# .iloc[i,j] gets absolute row (correct)
			spikeCol = self.model()._data.columns.get_loc('Spike')
			spikeNumber = self.model()._data.iloc[row, spikeCol]
		except (KeyError) as e:
			# for results plugin
			try:
				spikeNumberCol = self.model()._data.columns.get_loc('Spike')
				spikeNumber = self.model()._data.iloc[row, spikeNumberCol]
			except (KeyError) as e:
				logger.warning(f'KeyError looking for column "Spike" or "spikeNumber"')
				return
		spikeNumber = int(spikeNumber)

		#self.selectSpike(spikeNumber, doZoom=doZoom)
		dDict = {
			'spikeNumber': spikeNumber,
			'doZoom': doZoom,
		}
		logger.info(dDict)
		self.signalSelectSpike.emit(dDict)


	def errorTableClicked(self, index):
		row = index.row()
		#column = index.column()

		# was this
		#self.myErrorTable.selectRow(row)

		doZoom = False
		modifiers = QtGui.QApplication.keyboardModifiers()
		if modifiers == QtCore.Qt.ShiftModifier:
			# zoomm on shift+click
			doZoom = True

		try:
			# .loc[i,'col'] gets from index (wrong)
			# .iloc[i,j] gets absolute row (correct)
			spikeCol = self.model()._data.columns.get_loc('Spike')
			spikeNumber = self.model()._data.iloc[row, spikeCol]
		except (KeyError) as e:
			# for results plugin
			try:
				spikeNumberCol = self.model()._data.columns.get_loc('spikeNumber')
				spikeNumber = self.model()._data.iloc[row, spikeNumberCol]
			except (KeyError) as e:
				logger.warning(f'KeyError looking for column "Spike" or "spikeNumber"')
				return
		spikeNumber = int(spikeNumber)

		#self.selectSpike(spikeNumber, doZoom=doZoom)
		dDict = {
			'spikeNumber': spikeNumber,
			'doZoom': doZoom,
		}
		logger.info(dDict)
		self.signalSelectSpike.emit(dDict)
