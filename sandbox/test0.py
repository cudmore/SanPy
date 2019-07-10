# -*- coding: utf-8 -*-

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
from pyqtgraph.dockarea import *

app = QtGui.QApplication([])
gui = QtGui.QMainWindow()
area = DockArea()
gui.setCentralWidget(area)
gui.resize(1000,500)
gui.setWindowTitle("Scroll and Zoomed Plot")

dockCtrl = Dock("Plot Control", size=(200, 500))
dockCtrl.setFixedWidth(200)
area.addDock(dockCtrl, 'left')
winCtrl = pg.LayoutWidget()
dockCtrl.addWidget(winCtrl)

restartBttn = QtGui.QPushButton("Restart")
restartBttn.setMinimumSize(100,40)
winCtrl.addWidget(restartBttn)

def RestartPlot():
    global dataRnd,ptrDataRnd
    timer.stop()
    dataRnd = np.empty(100)
    ptrDataRnd = 0
    timer.start(50)

restartBttn.clicked.connect(RestartPlot)

dockScroll = Dock("Scrolling plot", size=(800,250))
area.addDock(dockScroll, 'right')
winScroll = pg.GraphicsWindow()
dockScroll.addWidget(winScroll)

dockZoom = Dock("Zoomed plot", size=(800,250))
area.addDock(dockZoom, 'right')
winZoom = pg.GraphicsWindow()
dockZoom.addWidget(winZoom)
area.moveDock(dockScroll, 'top', dockZoom)

plotScroll = winScroll.addPlot()
plotScroll.setDownsampling(mode='peak')
plotScroll.setClipToView(True)
curveScroll = plotScroll.plot()

dataRnd = np.empty(100)
ptrDataRnd = 0

def updateScroll():
    global dataRnd, ptrDataRnd
    dataRnd[ptrDataRnd] = np.random.normal()
    ptrDataRnd += 1
    if ptrDataRnd >= dataRnd.shape[0]:
        tmp = dataRnd
        dataRnd = np.empty(dataRnd.shape[0] * 2)
        dataRnd[:tmp.shape[0]] = tmp
    curveScroll.setData(dataRnd[:ptrDataRnd])

LinRegionItem = pg.LinearRegionItem([0,100])
LinRegionItem.setZValue(-10)
plotScroll.addItem(LinRegionItem)

plotZoom = winZoom.addPlot()
curveZoom = plotZoom.plot(dataRnd, pen=(255,255,255,200))

def updatePlot():
    plotZoom.setXRange(*LinRegionItem.getRegion(), padding=0)
def updateRegion():
    LinRegionItem.setRegion(plotZoom.getViewBox().viewRange()[0])

LinRegionItem.sigRegionChanged.connect(updatePlot)
plotZoom.sigXRangeChanged.connect(updateRegion)
updatePlot()

# added lines
def updateZoom():
    curveZoom.setData(dataRnd[:ptrDataRnd])

# update all plots
def update():
    updateScroll()
    # added line
    updateZoom()

timer = pg.QtCore.QTimer()
timer.timeout.connect(update)
timer.start(50)

gui.show()

if __name__ == '__main__':
    import sys

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()