from PyQt5 import QtCore, QtGui, QtWidgets

class errorTableView(QtWidgets.QTableView):
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

		'''
		p = self.palette()
		color1 = QtGui.QColor('#dddddd')
		color2 = QtGui.QColor('#ffffff')
		p.setColor(QtGui.QPalette.Base, color1)
		p.setColor(QtGui.QPalette.AlternateBase, color2)
		self.setAlternatingRowColors(True)
		self.setPalette(p)
		'''
