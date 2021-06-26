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
		self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
								  QtWidgets.QSizePolicy.Expanding)
		self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

		self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers |
							 QtWidgets.QAbstractItemView.DoubleClicked)

		# equally stretchs each columns so that they fit the table's width.
		self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch);
		self.horizontalHeader().setStretchLastSection(True)

		rowHeight = 11
		fnt = self.font()
		fnt.setPointSize(rowHeight)
		self.setFont(fnt)
		self.verticalHeader().setDefaultSectionSize(rowHeight);

		self.clicked.connect(self.errorTableClicked)

		'''
		p = self.palette()
		color1 = QtGui.QColor('#dddddd')
		color2 = QtGui.QColor('#ffffff')
		p.setColor(QtGui.QPalette.Base, color1)
		p.setColor(QtGui.QPalette.AlternateBase, color2)
		self.setAlternatingRowColors(True)
		self.setPalette(p)
		'''

	def errorTableClicked(self, index):
		row = index.row()
		column = index.column()

		# was this
		#self.myErrorTable.selectRow(row)

		doZoom = False
		modifiers = QtGui.QApplication.keyboardModifiers()
		if modifiers == QtCore.Qt.ShiftModifier:
			# zoomm on shift+click
			doZoom = True

		try:
			spikeNumber = self.model()._data.loc[row, 'Spike']
		except (KeyError) as e:
			# for results plugin
			try:
				spikeNumber = self.model()._data.loc[row, 'spikeNumber']
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
