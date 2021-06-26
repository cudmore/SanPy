
from PyQt5 import QtCore, QtWidgets, QtGui

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
#import sanpy.interface
from sanpy.interface.plugins import sanpyPlugin

class detectionErrors(sanpyPlugin):
	"""
	Plugin to display detection errors

	Uses:
		QTableView: sanpy.interface.bErrorTable.errorTableView()
		QAbstractTableModel: sanpy.interface.bFileTable.pandasModel
	"""
	myHumanName = 'Detection Errors'

	def __init__(self, **kwargs):
		"""
		"""
		super().__init__('detectionErrors', **kwargs)

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

	'''
	def plot(self):
		self.replot()
	'''

	def replot(self):
		# update
		ba = self.getSanPyApp().get_bAnalysis()
		if ba is not None:
			dfError = ba.dfError
			if dfError is not None:
				logger.info('dfError')
				print(dfError)
				errorReportModel = sanpy.interface.bFileTable.pandasModel(dfError)
				self.myErrorTable.setModel(errorReportModel)

if __name__ == '__main__':
	import sys
	app = QtWidgets.QApplication([])
	spl = detectionErrors()
	sys.exit(app.exec_())
