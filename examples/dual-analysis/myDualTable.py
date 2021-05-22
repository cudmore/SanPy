
import os, sys

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar

from PyQt5 import QtCore, QtGui, QtWidgets

from myTableWidget import myTableWidget

import dualAnalysis
import lcrPicker

# derive from myTableWidget to define right-click behavior
class myDualTable(myTableWidget):
	def __init__(self, path=None, df=None, parent=None):
		super(myDualTable, self).__init__(path=path, df=df, parent=parent)

		self.fig9PlotDict = {}

	def rightClickTable(self, position):
		selectedRow = super().getSelectedRow()

		menu = QtWidgets.QMenu()
		actionPloatImageFigure = menu.addAction("Plot Image Figure")
		action1 = menu.addAction("Plot Dual Recording")
		action2 = menu.addAction("Plot Dual Detection")
		action3 = menu.addAction("Plot Spike Clip")
		action3_5 = menu.addAction("Plot Spike Clip - Figure")
		action4 = menu.addAction("Plot LCR Hist")
		action5 = menu.addAction("LCR Picker")
		action = menu.exec_(self.tableView.mapToGlobal(position))

		# the OBJECT that was seleccted (action1, action2, action3)
		#print('action:', action)

		if action == actionPloatImageFigure:
			self.plotImageFigure(selectedRow)
		elif action == action1:
			self.plotDualRecording(selectedRow)
		elif action == action2:
			self.plotDualDetection(selectedRow)
		elif action == action3:
			self.plotSpikeClip(selectedRow)
		elif action == action3_5:
			self.plotSpikeClip(selectedRow, forFig9=True)
		elif action == action4:
			self.plotLcrHist(selectedRow)
		elif action == action5:
			self.lcrPicker(selectedRow)

	def _getPathFromRow(self, row):
		# get data path from first row
		firstRow = self.masterDf.iloc[0]
		dataPath = firstRow['data path']

		# params from selected row
		dfRow = self.masterDf.iloc[row]
		dateFolder = str(dfRow['date folder']) # is np.int64
		tifFile = dfRow['tif file']
		abfFile = dfRow['abf file']

		tifPath = os.path.join(dataPath, dateFolder, tifFile)
		abfPath = os.path.join(dataPath, dateFolder, abfFile)

		return tifPath, abfPath

	def plotDualRecording(self, row):
		print('myDualTable.plotDualRecording() row:', row)

		# params from selected row
		dfRow = self.masterDf.iloc[row]
		region = dfRow['region']

		tifPath, abfPath = self._getPathFromRow(row)

		print('doAction1()')
		print('   tifPath:', tifPath)
		print('   abfPath:', abfPath)

		dr = dualAnalysis.dualRecord(tifPath, abfPath)

		# works
		fig = dr.myPlot(fileNumber=row, region=region, myParent=self)

		# works
		# masterDf is backend model loaded from .csv and displayed in table
		#fig = dr.plotSpikeClip_df(self.masterDf, row, myParent=self)

		if fig is not None:
			fig.show()

	def plotDualDetection(self, row):
		print('myDualTable.plotDualDetection() row:', row)

		# params from selected row
		dfRow = self.masterDf.iloc[row]
		region = dfRow['region']

		tifPath, abfPath = self._getPathFromRow(row)

		dr = dualAnalysis.dualRecord(tifPath, abfPath)
		figTif, figAbf = dr.plotSpikeDetection_df(self.masterDf, row, myParent=self)
		figTif.show()
		figAbf.show()

	def plotSpikeClip(self, row, forFig9=False):
		print('myDualTable.plotSpikeClip() row:', row)

		tifPath, abfPath = self._getPathFromRow(row)
		dr = dualAnalysis.dualRecord(tifPath, abfPath)
		# masterDf is backend model loaded from .csv and displayed in table
		fig = dr.plotSpikeClip_df(self.masterDf, row, forFig9=forFig9, myParent=self)

		if fig is not None:
			fig.show()

	def plotImageFigure_better(self, fig, axImg, axLcr, row):
		"""
		may20
		using mpl figure makes a figure toolbar, does not allow to set x-axis
		"""
		self.fig9PlotDict[row] = {}


		'''
		self.main_frame = QtWidgets.QWidget()
		self.canvas = FigureCanvasQTAgg(fig)
		self.canvas.setParent(self.main_frame)
		self.canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
		self.canvas.setFocus()
		'''

		main_frame = QtWidgets.QWidget()
		canvas = FigureCanvasQTAgg(fig)
		canvas.setParent(main_frame)
		canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
		canvas.setFocus()

		self.fig9PlotDict[row]['main_frame'] = main_frame
		self.fig9PlotDict[row]['canvas'] = canvas

		#self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_frame)
		mpl_toolbar = NavigationToolbar(canvas, main_frame)
		self.fig9PlotDict[row]['mpl_toolbar'] = mpl_toolbar
		#self.canvas.mpl_connect('key_press_event', self.on_key_press)

		vbox = QtWidgets.QVBoxLayout()
		vbox.addWidget(canvas)  # the matplotlib canvas
		vbox.addWidget(mpl_toolbar)
		main_frame.setLayout(vbox)
		#self.setCentralWidget(self.main_frame)
		main_frame.show()

	def plotImageFigure(self, row):
		"""
		derived from self.plotLcrHist()
		"""

		print('myDualTable.plotImageFigure() row:', row)
		# params from selected row
		dfRow = self.masterDf.iloc[row]
		region = dfRow['region']

		tifPath, abfPath = self._getPathFromRow(row)

		dr = dualAnalysis.dualRecord(tifPath, abfPath)

		# need vm analysis to get peak seconds
		dr._loadAnalyzeAbf_from_df(self.masterDf, row)

		fig, axImg, axLcr = dr.plotFigure9(region=region, row=row) # does df/d0

		# may20, embed in a qt widget
		self.plotImageFigure_better(fig, axImg, axLcr, row)

		# may 20 removed
		# fig9 sup/inf
		if region == 'superior' and row==19:
			print('!!!!********* myDualTable.plotSpikeClip() setting superior xlim() !!!!!!!!!!!')
			#axImg.set_xlim(10.63, 11.63) # may 2021
			axImg.set_xlim(7, 8)
			axLcr.set_ylim(0, 12)
		elif region == 'inferior' and row==11:
			print('!!!!********* myDualTable.plotSpikeClip() setting inferior xlim() !!!!!!!!!!!')
			axImg.set_xlim(5.1, 6.1)
			axLcr.set_ylim(0, 12)

		#if fig is not None:
		#	fig.show()

	def plotLcrHist(self, row):
		# params from selected row
		dfRow = self.masterDf.iloc[row]
		region = dfRow['region']

		tifPath, abfPath = self._getPathFromRow(row)
		dr = dualAnalysis.dualRecord(tifPath, abfPath)

		# need vm analysis to get peak seconds
		dr._loadAnalyzeAbf_from_df(self.masterDf, row)

		fig = dr.new_plotSparkMaster(region=region)

		if fig is not None:
			fig.show()

	def lcrPicker(self, row):
		lcrPicker.lcrPicker(row, self.masterDf)

	def closeChild(self, type, row):
		pass

if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)

	# ccreate an empty table widget
	mdt = myDualTable()

	# populate from csv
	#path = 'dual-database.csv'
	df = dualAnalysis.loadDatabase() # loads and appends some full path columns
	#mdt.setModelFromCsv(path)
	mdt.setModelFromDf(df)

	#
	mdt.show()

	# debug figure9
	#mdt.plotImageFigure(19)
	#mdt.plotSpikeClipFigure(19)

	# for fig mar18

	# 19 is superior
	# 20210519, was this in original submission
	mdt.plotSpikeClip(19, forFig9=True)
	mdt.plotImageFigure(19)

	# 11 is inferior
	mdt.plotSpikeClip(11, forFig9=True)
	# my new plot only allows one at a time
	mdt.plotImageFigure(11)

	sys.exit(app.exec_())
