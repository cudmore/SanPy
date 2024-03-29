import sys
from PyQt5 import QtWidgets, QtGui
import matplotlib
import matplotlib.figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar


class PrettyWidget(QtWidgets.QWidget):
    def __init__(self):
        super(PrettyWidget, self).__init__()
        self.initUI()

    def initUI(self):

        self.setGeometry(100, 100, 800, 600)
        #self.center()
        self.setWindowTitle('S Plot')

        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)

        btn1 = QtWidgets.QPushButton('Plot 1 ', self)
        btn1.resize(btn1.sizeHint())
        btn1.clicked.connect(self.plot1)
        grid.addWidget(btn1, 5, 0)

        btn2 = QtWidgets.QPushButton('Plot 2 ', self)
        btn2.resize(btn2.sizeHint())
        btn2.clicked.connect(self.plot2)
        grid.addWidget(btn2, 5, 1)

        self.figure = matplotlib.figure.Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        grid.addWidget(self.canvas, 3, 0, 1, 2)
        # grid.addWidget(self.toolbar, ??)

        self.show()

    def plot1(self):
        self.figure.clf()
        ax1 = self.figure.add_subplot(211)
        x1 = [i for i in range(100)]
        y1 = [i**0.5 for i in x1]
        ax1.plot(x1, y1, 'b.-')

        ax2 = self.figure.add_subplot(212)
        x2 = [i for i in range(100)]
        y2 = [i for i in x2]
        ax2.plot(x2, y2, 'b.-')
        self.canvas.draw_idle()

    def plot2(self):
        self.figure.clf()
        ax3 = self.figure.add_subplot(111)
        x = [i for i in range(100)]
        y = [i**0.5 for i in x]
        ax3.plot(x, y, 'r.-')
        ax3.set_title('Square Root Plot')
        self.canvas.draw_idle()

    '''
    def center(self):
        qr = self.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
	'''
	
app = QtWidgets.QApplication(sys.argv)
app.aboutToQuit.connect(app.deleteLater)
GUI = PrettyWidget()
sys.exit(app.exec_())