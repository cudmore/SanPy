#20210619

from PyQt5 import QtCore, QtWidgets, QtGui

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
#import sanpy.interface
from sanpy.interface.plugins import sanpyPlugin

class resultsTable(sanpyPlugin):
	"""
	Plugin to display summary of all spikes, one spike per row.

	Uses:
		QTableView: sanpy.interface.bErrorTable.errorTableView()
		QAbstractTableModel: sanpy.interface.bFileTable.pandasModel
	"""
	myHumanName = 'Summary Spikes'

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.pyqtWindow() # makes self.mainWidget

		layout = QtWidgets.QVBoxLayout()

		controlsLayout = QtWidgets.QHBoxLayout()
		self.numSpikesLabel = QtWidgets.QLabel('unkown spikes')
		controlsLayout.addWidget(self.numSpikesLabel)
		layout.addLayout(controlsLayout)

		self.myErrorTable = sanpy.interface.bErrorTable.errorTableView()
		# TODO: derive a more general purpose table, here we are re-using error table
		self.myErrorTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive);
		self.myErrorTable.horizontalHeader().setStretchLastSection(False)

		layout.addWidget(self.myErrorTable)

		self.mainWidget.setLayout(layout)

		#
		# connect clicks in error table to siganl main sanpy_app with slot_selectSpike()
		fnPtr = self.getSanPyApp().slot_selectSpike
		self.myErrorTable.signalSelectSpike.connect(fnPtr)

		self.replot()

	def replot(self):
		# update
		ba = self.getSanPyApp().get_bAnalysis()
		if ba is None:
			return
		dfPlot = ba.dfReportForScatter
		if dfPlot is not None:
			startSec, stopSec = self.getStartStop()
			if startSec is not None and stopSec is not None:
				# use column thresholdSec
				dfPlot = dfPlot[ (dfPlot['thresholdSec']>=startSec) & (dfPlot['thresholdSec']<=stopSec)]
				pass
			#
			logger.info(f'dfReportForScatter {startSec} {stopSec}')
			errorReportModel = sanpy.interface.bFileTable.pandasModel(dfPlot)
			self.myErrorTable.setModel(errorReportModel)

			self.numSpikesLabel.setText(f'{len(dfPlot)} spikes')

	def copyToClipboard(self):
		ba = self.getSanPyApp().get_bAnalysis()
		if ba is not None:
			dfReportForScatter = ba.dfReportForScatter
			if dfReportForScatter is not None:
				logger.info('Copy to clipboard')
				dfReportForScatter.to_clipboard(sep='\t', index=False)

if __name__ == '__main__':
	import sys
	app = QtWidgets.QApplication([])
	rt = resultsTable()
	sys.exit(app.exec_())
