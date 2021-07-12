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
		self.setSelectionMode(QtWidgets.QTableView.SingleSelection)

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

	def errorTableClicked(self, index):
		row = self.model()._data.index[index.row()] # take sorting into account

		doZoom = False
		modifiers = QtGui.QApplication.keyboardModifiers()
		if modifiers == QtCore.Qt.ShiftModifier:
			# zoomm on shift+click
			doZoom = True

		try:
			# .loc[i,'col'] gets from index label (correct)
			# .iloc[i,j] gets absolute row (wrong)
			spikeNumber = self.model()._data.loc[row, 'Spike']
		except (KeyError) as e:
			# for results plugin
			try:
				spikeNumber = self.model()._data.loc[row, 'spikeNumber']
			except (KeyError) as e:
				logger.warning(f'KeyError looking for column "Spike" or "spikeNumber"')
				return
		spikeNumber = int(spikeNumber)

		dDict = {
			'spikeNumber': spikeNumber,
			'doZoom': doZoom,
		}
		logger.info(dDict)
		self.signalSelectSpike.emit(dDict)
