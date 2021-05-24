import os, sys
from PyQt5 import QtWidgets, QtGui
import matplotlib
import matplotlib.figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar

# needed to import from SanPy which is one folder up
sys.path.append("..")

from SanPy import bAnalysis
from SanPy import bAnalysisPlot

file = '../data/19114001.abf'

'''
global ba
ba = bAnalysis.bAnalysis(file)
'''

class PrettyWidget(QtWidgets.QWidget):
	def __init__(self, file):
		"""
		file: always iniliaize with an abf file
		"""
		super(PrettyWidget, self).__init__()
				
		self.setFile(file)
		
		self.initUI()

		self.ba = None
		
	def initUI(self):

		self.setGeometry(100, 100, 1000, 600)
		self.center()
		self.setWindowTitle('Raw Plot')

		grid = QtWidgets.QGridLayout()
		self.setLayout(grid)

		saveButton = QtWidgets.QPushButton('Save pdf', self)
		saveButton.resize(saveButton.sizeHint())
		saveButton.clicked.connect(self.save)
		grid.addWidget(saveButton, 5, 1)
		
		self.figure = matplotlib.figure.Figure()
		self.canvas = FigureCanvas(self.figure)
		
		# matplotlib navigation toolbar
		self.toolbar = NavigationToolbar(self.canvas, self)
		self.toolbar.zoom()
		
		grid.addWidget(self.toolbar, 2, 0, 1, 2)
		grid.addWidget(self.canvas, 3, 0, 1, 2)
		# grid.addWidget(self.toolbar, ??)

		self.myAxis = None
		self.plotRaw()
		
		self.show()
		
	def setFile(self, filePath):
		"""
		when main application changes file
		"""
		self.filePath = filePath
		self.ba = bAnalysis.bAnalysis(filePath)
		
	def plotRaw(self):
		self.figure.clf()
		self.myAxis = self.figure.add_subplot(111)
		
		'''
		x = [i for i in range(100)]
		y = [i**0.5 for i in x]
		ax3.plot(x, y, 'r.-')
		ax3.set_title('Square Root Plot')
		'''
		bAnalysisPlot.bPlot.plotRaw(self.ba, ax=self.myAxis)

		self.canvas.draw_idle()

	def save(self):
		"""
		Save the current view to a pdf file
		"""
		
		# get min/max of x-axis
		[xMin, xMax] = self.myAxis.get_xlim()
		if xMin < 0:
			xMin = 0
		xMin = '%.2f'%(xMin)
		xMax = '%.2f'%(xMax)

		lhs, rhs = xMin.split('.')
		xMin = 'b' + lhs + '_' + rhs

		lhs, rhs = xMax.split('.')
		xMax = 'e' + lhs + '_' + rhs

		# construct a default save file name
		parentPath, filename = os.path.split(self.filePath)
		baseFilename, file_extension = os.path.splitext(filename)
		saveFileName = baseFilename + '_' + xMin + '_' + xMax + '.pdf'
		saveFilePath = os.path.join(parentPath,saveFileName)

		# file save dialog
		fullSavePath, ignore = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', saveFilePath, "pdf Files (*.pdf)")

		# do actual save
		if len(fullSavePath) > 0:
			print('saving:', fullSavePath)
			self.figure.savefig(saveFilePath)
	
	def center(self):
		"""
		Center the window on the screen
		"""
		qr = self.frameGeometry()
		cp = QtWidgets.QDesktopWidget().availableGeometry().center()
		qr.moveCenter(cp)
		self.move(qr.topLeft())
	
app = QtWidgets.QApplication(sys.argv)
app.aboutToQuit.connect(app.deleteLater)
GUI = PrettyWidget(file)
sys.exit(app.exec_())