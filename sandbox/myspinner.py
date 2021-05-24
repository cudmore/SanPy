import math, sys, time
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import *

from PyQt5 import QtCore, QtWidgets, QtGui

class Overlay(QtWidgets.QWidget):

	def __init__(self, parent = None):
	
		QtWidgets.QWidget.__init__(self, parent)
		palette = QPalette(self.palette())
		palette.setColor(palette.Background, Qt.transparent)
		self.setPalette(palette)
	
	def paintEvent(self, event):
	
		print('paintEvent() self.counter:', self.counter)
		
		painter = QPainter()
		painter.begin(self)
		painter.setRenderHint(QPainter.Antialiasing)
		painter.fillRect(event.rect(), QBrush(QColor(255, 255, 255, 127)))
		painter.setPen(QPen(Qt.NoPen))
		
		for i in range(6):
			if (self.counter / 5) % 6 == i:
				painter.setBrush(QBrush(QColor(127 + (self.counter % 5)*32, 127, 127)))
			else:
				painter.setBrush(QBrush(QColor(127, 127, 127)))
			painter.drawEllipse(
				self.width()/2 + 30 * math.cos(2 * math.pi * i / 6.0) - 10,
				self.height()/2 + 30 * math.sin(2 * math.pi * i / 6.0) - 10,
				20, 20)
		
		painter.end()
	
	def showEvent(self, event):
	
		#print('Overlay.showEvent() event:', event)
		self.timer = self.startTimer(50)
		self.counter = 0
	
	def timerEvent(self, event):
	
		print('Overlay.timerEvent() event:', event)
		self.counter += 1
		self.update()
		if self.counter == 60:
			self.killTimer(self.timer)
			self.hide()
		
	'''
	def myKillTimer(self):
		self.killTimer(self.timer)
		self.hide()
	'''

class MainWindow(QtWidgets.QMainWindow):

	def __init__(self, parent = None):
	
		QtWidgets.QMainWindow.__init__(self, parent)
		
		widget = QtWidgets.QWidget(self)
		self.editor = QtWidgets.QTextEdit()
		self.editor.setPlainText("0123456789"*100)
		layout = QtWidgets.QGridLayout(widget)
		layout.addWidget(self.editor, 0, 0, 1, 3)
		button = QtWidgets.QPushButton("Wait")
		layout.addWidget(button, 1, 1, 1, 1)
		
		self.setCentralWidget(widget)
		self.overlay = Overlay(self.centralWidget())
		self.overlay.hide()
		button.clicked.connect(self.overlay.show)
		#button.clicked.connect(self.longtask)
	
	'''
	def longtask(self):
		self.overlay.show()
		
		print('start sleep')
		#time.sleep(10)
		print('stop sleep')
		
		#self.overlay.myKillTimer()
	'''	
	def resizeEvent(self, event):
	
		self.overlay.resize(event.size())
		event.accept()


if __name__ == "__main__":

	app = QtWidgets.QApplication(sys.argv)
	window = MainWindow()
	window.show()
	sys.exit(app.exec_())