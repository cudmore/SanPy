from PyQt5 import QtWidgets

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class analysisSummary(sanpyPlugin):
	"""
	Plugin to display overview of analysis.

	Uses:
		QTableView: sanpy.interface.bErrorTable.errorTableView()
		QAbstractTableModel: sanpy.interface.bFileTable.pandasModel
	"""
	myHumanName = 'Summary Analysis'

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.df = None

		self.pyqtWindow()  # makes self.mainWidget

		layout = QtWidgets.QVBoxLayout()
		self.myErrorTable = sanpy.interface.bErrorTable.errorTableView()
		layout.addWidget(self.myErrorTable)

		self.mainWidget.setLayout(layout)

		self.replot()

	def replot(self):
		ba = self.get_bAnalysis()
		if ba is not None:
			be = sanpy.bExport(ba)
			theMin, theMax = self.getStartStop()
			dfSummary = be.getSummary(theMin=theMin, theMax=theMax)
			if dfSummary is not None:
				errorReportModel = sanpy.interface.bFileTable.pandasModel(dfSummary)
				self.myErrorTable.setModel(errorReportModel)
			self.df = dfSummary

	def copyToClipboard(self):
		if self.df is not None:
			self.df.to_clipboard(sep='\t', index=True)
			logger.info('Copied to clipboard')

if __name__ == '__main__':
	import sys
	app = QtWidgets.QApplication([])

	# load and analyze sample data
	path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(path)
	ba.spikeDetect()

	# open a plugin
	sa = analysisSummary(ba=ba, startStop=None)

	sys.exit(app.exec_())
