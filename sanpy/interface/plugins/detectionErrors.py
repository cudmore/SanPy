import pandas as pd

from PyQt5 import QtWidgets

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class detectionErrors(sanpyPlugin):
	"""
	Plugin to display detection errors

	Uses:
		QTableView: sanpy.interface.bErrorTable.errorTableView()
		QAbstractTableModel: sanpy.interface.bFileTable.pandasModel
	"""
	myHumanName = 'Error Summary'

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.pyqtWindow() # makes self.mainWidget

		layout = QtWidgets.QVBoxLayout()
		self.myErrorTable = sanpy.interface.bErrorTable.errorTableView()
		layout.addWidget(self.myErrorTable)

		self.mainWidget.setLayout(layout)

		#
		# connect clicks in error table to siganl main sanpy_app with slot_selectSpike()
		fnPtr = self.getSanPyApp().slot_selectSpike
		self.myErrorTable.signalSelectSpike.connect(fnPtr)

		self.replot()

	def replot(self):
		# update
		# todo: get default columns from ???
		dfError = pd.DataFrame(columns=['Spike', 'Seconds', 'Type', 'Details'])

		ba = self.getSanPyApp().get_bAnalysis()
		if ba is not None:
			if ba.dfError is not None:
				dfError = ba.dfError
		#
		errorReportModel = sanpy.interface.bFileTable.pandasModel(dfError)
		self.myErrorTable.setModel(errorReportModel)

if __name__ == '__main__':
	import sys
	app = QtWidgets.QApplication([])
	spl = detectionErrors()
	sys.exit(app.exec_())
