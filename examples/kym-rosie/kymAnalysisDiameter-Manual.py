"""
Implementing this for Rosie.

Do manual peak detection from Kymograph diameter measurements.

This is because the data is noisey (it is not bad).
"""

import os, sys

import pandas as pd
import numpy as np

#import matplotlib.pyplot as plt
from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

import sanpy

class footPeakList:
    """Hold lists of foot/peak point/val
    
    Use this to manually annotate otherwise good but noisey foot/peak traces.
    """
    def __init__(self, yPlot : np.ndarray, xPlot = None):
        self._yPlot = yPlot
        if xPlot is None:
            xPlot = np.arange(0,len(self._yPlot))
        self._xPlot = xPlot
        
        self._dx = self._xPlot[1] - self._xPlot[0]
        # to convert between scales x-axis and point number.

        self._xPosFoot = []
        self._yPosFoot = []
    
        self._xPosPeak = []
        self._yPosPeak = []

        self._yPeakAmp = []  # yPeak - yFoot

        # detection params
        self._peakWindowPnts = 300
        # point to search for min/max in peak

    def xToPnt(self, x : float) -> int:
        """
        Args:
            x: Like seconds and _dx like 'seconds per line'
        """
        return int(x / self._dx)
    
    def pntToX(self, pnt : int) -> float:
        return pnt / (1/self._dx)
    
    def setPeakWindow(self, peakWindowPnts):
        self._peakWindowPnts = peakWindowPnts
    
    def getDataX(self):
        return self._xPlot
    
    def getDataY(self):
        return self._yPlot
    
    def getPeakWindow(self):
        return self._peakWindowPnts

    def _addNewFootPeak(self):
        self._xPosFoot.append(np.nan)
        self._yPosFoot.append(np.nan)
        self._xPosPeak.append(np.nan)
        self._yPosPeak.append(np.nan)
    
        self._yPeakAmp.append(np.nan)

    def assignFootPeak(self, xFoot : int, yFoot : float,
                                xPeak : int, yPeak : float):
        """Assign a new foot/peak.
        
        All x values are in points (int).
        
        Foot will always exist, peak can be None/nan
        """
        
        self._addNewFootPeak()
        
        self._xPosFoot[-1] = self.pntToX(xFoot)
        self._yPosFoot[-1] = yFoot
        self._xPosPeak[-1] = self.pntToX(xPeak)
        self._yPosPeak[-1] = yPeak
        
        self._yPeakAmp[-1] = yPeak - yFoot

    def deleteLast(self):
        """Delete the last foot/peak.
        """
        if len(self._xPosFoot) > 0:
            self._xPosFoot.pop()
            self._yPosFoot.pop()
            self._xPosPeak.pop()
            self._yPosPeak.pop()
            
            self._yPeakAmp.pop()
        
    def getValueAtPoint(self, xPnt):
        """Get y value at an x point.
        """
        xPnt = int(xPnt)
        return self._yPlot[xPnt]
    
    def getFootPos(self):
        return self._xPosFoot, self._yPosFoot

    def getPeakPos(self):
        return self._xPosPeak, self._yPosPeak

    def findPeak(self, startPnt, minMax='min', peakWindowPnts=None):
        """Get the pnt of a peak from a start point and within a window.
        
        Args:
            startPnt:
            minMax: In ('min', 'max') to specify search for min or max
            peakWin: Window to search in, specified in points
        """        
        if peakWindowPnts is None:
            peakWindowPnts = self._peakWindowPnts
        
        startPnt = int(startPnt)
        
        stopPnt = startPnt + peakWindowPnts
        if stopPnt > len(self._yPlot):
            # no peak
            return np.nan, np.nan
        
        _clip = self._yPlot[startPnt:stopPnt]
        
        if minMax == 'min':
            peakPnt = np.argmin(_clip)
        elif minMax == 'max':
            peakPnt = np.argmax(_clip)
        else:
            print(f'ERROR: did not understand minMax:"{minMax}", expecting ["min", "max"]')
            return np.nan, np.nan

        peakPnt = startPnt + peakPnt
        peakVal = self._yPlot[peakPnt]

        print(f'findPeak() from pnt:{startPnt} with peak pnt window:{peakWindowPnts}')
        print(f'  peakPnt:{peakPnt} peakVal:{peakVal}')

        return peakPnt, peakVal

    def asDataFrame(self):
        """Get the foot/peak as a Pandas Dataframe.

            Columns are:
                xFoot, yFoot, xPeak, yPeak
        """
        columns = ['xFoot', 'yFoot', 'xPeak', 'yPeak', 'yPeakAmp']
        df = pd.DataFrame(columns=columns)

        df['xFoot'] = self._xPosFoot
        df['yFoot'] = self._yPosFoot
        df['xPeak'] = self._xPosPeak
        df['yPeak'] = self._yPosPeak

        df['yPeakAmp'] = self._yPeakAmp

        return df

    def save(self, path):
        # header

        # data
        df = self.asDataFrame()
        df.to_csv(path)
        print(f'  saved {len(df)} peaks to path:{path}')

    def load(self, path):
        df = pd.read_csv(path)
        self._xPosFoot = df['xFoot'].tolist()
        self._yPosFoot = df['yFoot'].tolist()
        self._xPosPeak = df['xPeak'].tolist()
        self._yPosPeak = df['yPeak'].tolist()

        self._yPeakAmp = df['yPeakAmp'].tolist()

class linePlotPeakWidget(QtWidgets.QWidget):
    """Widget to plot a line and provide interface for user clicks to:
        - shift+click: Create a foot and search for corresponding peak
        - keyboard+d: Delete the last foot/peak pair
    """
    def __init__(self, yPlot, xPlot = None, yPlot2 = None, path : str = None):
        """
        
        Args:
            yPlot: data to analyze
            xPlot: If specified, _dt=xPlot[1]-xPlot[0], otherwise _dt=1
            path: Path to .tif kymograph, we will load -analysis.csv
        """
        super().__init__()
        
        self.path = path
        # path to kymograph tif we loaded

        self._footPeakList = footPeakList(yPlot, xPlot=xPlot)
        # backend object we edit, a trace to detect, a list of foot peak.

        self._findPolarity = 'min'
        # search for positive (max) or negative (min) peaks

        self._yPlot2 = yPlot2

        self._buildUI()

        # load and redraw foot/peak, loading from '-fpAnalysis.csv'
        self.load()

        if path is None:
            windowTitle = 'None'
        else:
            windowTitle = os.path.split(path)[1]
        self.setWindowTitle(windowTitle)

    def switchFile(self, yPlot, xPlot = None, path = None):
        self.path = path
        self._footPeakList = footPeakList(yPlot, xPlot=xPlot)

        self.load()

        self._redraw()

        if path is None:
            windowTitle = 'None'
        else:
            windowTitle = os.path.split(path)[1]
        self.setWindowTitle(windowTitle)

    def _peakWindowChanged(self, value):
        """User edited peak window points.
        """
        self._footPeakList.setPeakWindow(value)

    def _buildToolbar(self):
        """Horizontal toolbar of controls.
        """
        hBoxLayout = QtWidgets.QHBoxLayout(self)

        peakWindowPointsLabel = QtWidgets.QLabel('Peak Window Points')
        hBoxLayout.addWidget(peakWindowPointsLabel)

        self._peakWindowSpinBox = QtWidgets.QSpinBox()
        self._peakWindowSpinBox.valueChanged.connect(self._peakWindowChanged)
        self._peakWindowSpinBox.setMaximum(100000)
        self._peakWindowSpinBox.setValue(self._footPeakList.getPeakWindow())
        hBoxLayout.addWidget(self._peakWindowSpinBox)

        polarityLabel = QtWidgets.QLabel('Peak Polarity')
        hBoxLayout.addWidget(polarityLabel)

        peakPolarity = QtWidgets.QComboBox()
        peakPolarity.addItem('min')
        peakPolarity.addItem('max')
        peakPolarity.setCurrentIndex(0)
        peakPolarity.currentTextChanged.connect(self._onPolarityChanged)
        hBoxLayout.addWidget(peakPolarity)

        return hBoxLayout

    def _onPolarityChanged(self, newPolarity : str):
        """User selected polarity popup.
        
        Args:
            newPolarity: in ['min', 'max']
        """
        self._findPolarity = newPolarity

    def _buildUI(self):
        
        # using self assigns the v box as layout for self widget
        vBoxLayoutForPlot = QtWidgets.QVBoxLayout(self)

        hToolbar = self._buildToolbar()
        vBoxLayoutForPlot.addLayout(hToolbar)

        # self.view gets added to vboxlayout
        self.view = pg.GraphicsLayoutWidget()
        self.view.show()

        row = 0
        col = 0
        rowSpan = 1
        colSpan = 1
        
        self._linePlot = self.view.addPlot(row=row, col=col, rowSpan=rowSpan, colSpan=colSpan)
        self._linePlot.enableAutoRange()

        # plot diameter for each line scan
        _xPlot = self._footPeakList.getDataX()
        _yPlot = self._footPeakList.getDataY()
        self._linePlot.plot(_xPlot, _yPlot)

        # signals, _linePlot is type <PlotItem>
        self._linePlot.scene().sigMouseMoved.connect(self._myMouseMoved)   
        self._linePlot.scene().sigMouseClicked.connect(self._myMouseClicked)   
        #self._linePlot.sigPointsClicked.connect(self._on_scatterClicked)

        # crosshair to follow cursor
        self._crosshairDict = {
            'h': pg.InfiniteLine(angle=0, movable=False),
            'v': pg.InfiniteLine(angle=90, movable=False)
        }

        self._linePlot.addItem(self._crosshairDict['h'], ignoreBounds=True)
        self._linePlot.addItem(self._crosshairDict['v'], ignoreBounds=True)

        # scatter plot of foot (red)
        symbol = 'o'
        color = 'r'
        self._footScatterPlot = pg.PlotDataItem(pen=None, symbol=symbol, symbolSize=6, symbolPen=None, symbolBrush=color)
        self._footScatterPlot.setData(x=[], y=[]) # start empty
        self._footScatterPlot.sigPointsClicked.connect(self._on_scatterClicked)
        self._linePlot.addItem(self._footScatterPlot)

        # scatter plot of peak (red)
        symbol = 'o'
        color = 'w'
        self._peakScatterPlot = pg.PlotDataItem(pen=None, symbol=symbol, symbolSize=6, symbolPen=None, symbolBrush=color)
        self._peakScatterPlot.setData(x=[], y=[]) # start empty
        self._peakScatterPlot.sigPointsClicked.connect(self._on_scatterClicked)
        self._linePlot.addItem(self._peakScatterPlot)

        # line plot 2
        row = 1
        self._linePlot2 = self.view.addPlot(row=row, col=col, rowSpan=rowSpan, colSpan=colSpan)
        self._linePlot2.enableAutoRange()
        self._linePlot2.plot(_xPlot, self._yPlot2)
        self._linePlot2.addItem(self._crosshairDict['v'], ignoreBounds=True)
        # link x-axis with kymograph PlotWidget
        self._linePlot2.setXLink(self._linePlot)

        # add to v box
        vBoxLayoutForPlot.addWidget(self.view)

    def _redraw(self):
        """Redraw foot and peak.
        
        Used on add/delete.
        """
        xFoot, yFoot = self._footPeakList.getFootPos()
        self._footScatterPlot.setData(xFoot, yFoot)

        xPeak, yPeak = self._footPeakList.getPeakPos()
        self._peakScatterPlot.setData(xPeak, yPeak)

        #yPlot2 = 

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_D:
            # delete last foot/peak
            self._deleteLastFootPeak()
            event.accept()
        elif event.key() == QtCore.Qt.Key_S:
            # save
            self.save()
            event.accept()
        elif event.key() == QtCore.Qt.Key_P:
            # print foot/peak dataframe
            df = self._footPeakList.asDataFrame()
            print(df)
            event.accept()
        # elif event.key() == QtCore.Qt.Key_Enter:
        #     self.proceed()
        

    def _deleteLastFootPeak(self):
        self._footPeakList.deleteLast()
        self._redraw()

    def _myMouseMoved(self, pointEvent):
        """
        pointEvent: QPointF
        """

        # one plot for now
        inPlot = self._linePlot

        mousePoint = inPlot.vb.mapSceneToView(pointEvent)
        #print('  _myMouseMoved() mousePoint:', mousePoint)

        self._crosshairDict['h'].setPos(mousePoint.y())
        self._crosshairDict['v'].setPos(mousePoint.x())

    def _myMouseClicked(self, event):
        """User clicks on foot.

        Args:
            event: MouseClickEvent
        """
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        isShift = modifiers == QtCore.Qt.ShiftModifier
        
        scenePos = event.scenePos()
        inPlotItem = self._linePlot
        pos = inPlotItem.vb.mapSceneToView(scenePos)
        print('=== pos:', pos)
        
        xFoot = pos.x()
        #yFoot = pos.y()  # y is always value at [xFoot]

        # convert scaled x to point
        xFoot = self._footPeakList.xToPnt(xFoot)
        print('=== xFoot:', xFoot)

        if isShift:
            
            # xFoot is always a point
            xFoot = int(xFoot)

            # yFoot is always value at xFoot
            yFoot = self._footPeakList.getValueAtPoint(xFoot)

            # look for min/max peak
            xPeak, yPeak = self._footPeakList.findPeak(xFoot, minMax=self._findPolarity)

            # update backend
            self._footPeakList.assignFootPeak(xFoot, yFoot, xPeak, yPeak)

            # debug
            # df = self._footPeakList.asDataFrame()
            # print(df)

            # refresh interface
            self._redraw()

            # auto save
            #self.save()

    def _on_scatterClicked(self, item, points, event=None):
        """
        
        Args:
            item: pyqtgraph.graphicsItems.PlotDataItem.PlotDataItem
            points: [<pyqtgraph.graphicsItems.ScatterPlotItem.SpotItem]
        """
        # print('_on_scatterClicked()')
        # print('  item:', item)
        # print('  points:', points)
        # print('  event:', event)
        
        if len(points) > 0:
            peakPoint = points[0].index()
            print('_on_scatterClicked() peakPoint:', peakPoint)

    def getSavePath(self):
        # file to save
        if self.path is None:
            print('WARNING: no path to save to.')
            return
        
        tifFolder, tifFile = os.path.split(self.path)
        tifFileBase, tifFileExt = os.path.splitext(tifFile)
        
        saveFile = tifFileBase + '-fpAnalysis2.csv'
        savePath = os.path.join(tifFolder, saveFile)
        return savePath

    def save(self):
        """Save foot/peak list.
        """
        
        savePath = self.getSavePath()

        print('saving to:', savePath)

        # save a pandas DataFrame with columns (xFoot, yFoot, xPeak, yPeak)
        # df = self._footPeakList.asDataFrame()
        # print(df)

        self._footPeakList.save(savePath)

    def load(self):
        savePath = self.getSavePath()
        if os.path.isfile(savePath):
            self._footPeakList.load(savePath)
            self._redraw()

def run():
    path = '/Users/cudmore/data/rosie/Raw data for contraction analysis/Female Old/filter median 1 C2-0-255 Cell 3 ISO 2_5_21 female wt old.tif' #-analysis.csv'

    # loads analysis (asumes kymograph plugin saved)
    ka = sanpy.kymographAnalysis(path)
    
    # we are working in pixels
    # yPlot = ka._results['diameter_um'].values
    yPlot = ka._results['diameter_pixels'].values

    secondsPerLine = 0.001818
    xPlot = np.arange(0,len(yPlot)) * secondsPerLine
    
    app = QtWidgets.QApplication(sys.argv)
    
    lppw = linePlotPeakWidget(yPlot, xPlot=xPlot, path=path)
    lppw.show()

    # test switch file
    # path = '/Users/cudmore/data/rosie/Raw data for contraction analysis/Female Old/filter median 1 C2-0-255 Cell 4 ISO 2_5_21 female wt old.tif'
    # yPlot = ka._results['diameter_um'].values
    # xPlot = np.arange(0,len(yPlot)) * secondsPerLine
    # lppw.switchFile(yPlot, xPlot=xPlot, path = path)

    sys.exit(app.exec_())

def runFolder():
    folderPath = '/Users/cudmore/data/rosie/Raw data for contraction analysis/Female Old'
    # folderPath = '/Users/cudmore/data/rosie/Raw data for contraction analysis/Female Young'
    # folderPath = '/Users/cudmore/data/rosie/Raw data for contraction analysis/Male Old'
    # folderPath = '/Users/cudmore/data/rosie/Raw data for contraction analysis/Male Young'
    # folderPath = '/Users/cudmore/data/rosie/Raw data for contraction analysis/Male Old AAV9 shBin1'
    
    app = QtWidgets.QApplication(sys.argv)

    files = os.listdir(folderPath)
    for file in files:
        if not file.endswith('.tif'):
            continue

        path = os.path.join(folderPath, file)
        print(f'=== runFolder() is showing file:{file}')

        # loads analysis (asumes kymograph plugin saved)
        ka = sanpy.kymographAnalysis(path)
        #yPlot = ka._results['diameter_um']
        if ka._results is None:
            print(f'ERROR: did not find results for file {file}')
            continue
        
        yPlot = ka._results['diameter_pixels']
        yPlot2 = ka._results['sumintensity']

        # secondsPerLine = 0.001818
        # xPlot = np.arange(0,len(yPlot)) * secondsPerLine
        xPlot = None  # forces 1 bin sampling

        lppw = linePlotPeakWidget(yPlot, xPlot=xPlot, yPlot2=yPlot2, path=path)
        lppw.show()

        #sys.exit(app.exec_())
        app.exec_()

    print('DONE !!!')

if __name__ == '__main__':
    # rosieRosetta = '/Users/cudmore/data/rosie/rosie-rosetta.csv'
    # df = pd.read_csv(rosieRosetta)
    # print(f'"{df["fileName"][0]}"')

    #run()

    runFolder()