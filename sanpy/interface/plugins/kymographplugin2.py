"""
Widget to act as the interface for kymographPlugin

I am keeping it seperate because it can be used standalone.
"""

import os
import sys
import numpy as np

from qtpy import QtGui, QtSql, QtCore, QtWidgets

import pyqtgraph as pg

import qdarkstyle

# turn off qdarkstyle logging
#import logging
#logging.getLogger('qdarkstyle').setLevel(logging.WARNING)

#from shapeanalysisplugin._my_logger import logger
#from shapeanalysisplugin import kymographAnalysis

from sanpy import kymographAnalysis

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class kymographPlugin2(QtWidgets.QWidget):

    def __init__(self, path : str, parent = None):
        logger.info('')
        
        super().__init__(parent)
        
        self._kymographAnalysis = kymographAnalysis(path)
        
        self._initGui()

        self._on_slider_changed(0)

        self.refreshSumLinePlot()
        self.refreshDiameterPlot()

    def _checkboxCallback(self, state : bool, name : str):
        logger.info(f'state:{state} name:{name}')
        if name == 'Line Profile':
            self.showLineProfile(state)
        elif name == 'Diameter':
            self.diameterPlotItem.setVisible(state)
        elif name == 'Sum Line':
            self.sumIntensityPlotItem.setVisible(state)

    def showLineProfile(self, state : bool):
        """Toggle interface for "Line Profile"
        """
        self.profileSlider.setVisible(state)
        
        self.lineIntensityPlotItem.setVisible(state)

        for line in self._sliceLinesList:
            line.setVisible(state)

    def _buttonCallback(self, name):
        logger.info(f'name:{name}')
        pos = self._rectRoi.pos()  # (left, bottom)
        size = self._rectRoi.size()  # (widht, height)
        #print(f'    pos:{pos} size:{size}')
    
        if name == 'Reset ROI':
            pos, size = self._kymographAnalysis.getFullRectRoi()  # (w,h)
            self._rectRoi.setPos(pos)
            self._rectRoi.setSize(size)
            # set the x-axis of the image plot
            #self.kymographWindow.setXRange(0, shape[0])

        elif name == 'Analyze':
            #left_idx, right_idx = self._kymographAnalysis.getLineProfileWidth()
            self._kymographAnalysis.analyze()
            self.refreshSumLinePlot()
            self.refreshDiameterPlot()
        
        elif name == 'Save':
            saveFilePath = self._kymographAnalysis.getAnalysisFile()
            # get file name to save
            #name = QtGui.QFileDialog.getSaveFileName(self, 'Save File')
            savefile, tmp = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', saveFilePath)
            self._kymographAnalysis.save(savefile)

        elif name == 'Rot -90':
            newImage = self._kymographAnalysis.rotateImage()
            self.kymographImage.setImage(newImage)

        else:
            logger.warning(f'did not understand "{name}"')

    def setLineWidth(self, value : int):
        logger.info(value)
        self._kymographAnalysis.setLineWidth(value)

    def setPercentMax(self, value : float):
        logger.info(f'value:{value}')
        self._kymographAnalysis.setPercentOfMax(value)

    def _slot_roi_changed(self):
        pos = self._rectRoi.pos()
        size = self._rectRoi.size()

        logger.info(f'pos:{pos} size:{size}')

        self._kymographAnalysis.setPosRoi(pos)
        self._kymographAnalysis.setSizeRoi(size)

        # update line profile plot
        _lineScanValue = self.profileSlider.value()
        self._on_slider_changed(_lineScanValue)

    def _on_slider_changed(self, value : int):
        """Respond to user changing the "Line Scan" slider.
        
        Args:
            value: The line profile number
        """
        logger.info(f'value:{value}')

        secondsValue = value * self._kymographAnalysis._secondsPerLine
        # update verical lines on top of plots
        for line in self._sliceLinesList:
            line.setValue(secondsValue)

        # update one line profile plot
        lineProfile, left_pnt, right_pnt = \
            self._kymographAnalysis._getFitLineProfile(value)
        #print('    left:', left, 'right:', right)

        # logger.info(f'  len(lineProfile):{len(lineProfile)} \
        #             left_pnt:{left_pnt} \
        #             right_pnt:{right_pnt}')

        # +1 because np.arange() does NOT include the last point
        #xData = np.arange(0, self._kymographAnalysis.pointsPerLineScan()+1)
        xData = np.arange(0, self._kymographAnalysis.pointsPerLineScan())
        xData = np.multiply(xData, self._kymographAnalysis._umPerPixel)
        if len(xData) != len(lineProfile):
            logger.error(f'xData: {len(xData)}')
            logger.error(f'lineProfile: {len(lineProfile)}')
        self.lineIntensityPlot.setData(xData, lineProfile)

        # if the fit fails we get left/right as nan
        if np.isnan(left_pnt) or np.isnan(right_pnt):
            xLeftRightData = [np.nan, np.nan]
            yLeftRightData = [np.nan, np.nan]
        else:
            left_um = self._kymographAnalysis.pnt2um(left_pnt)
            right_um = self._kymographAnalysis.pnt2um(right_pnt)
            xLeftRightData = [left_um, right_um] 
            #print(xLeftRightData)
            yLeftRightData = [lineProfile[left_pnt], lineProfile[right_pnt]] 
        self.leftRightPlot.setData(xLeftRightData, yLeftRightData)

    def _initGui(self):
        self.setWindowTitle('Kymograph Analysis')
        
        self._sliceLinesList = []
        
        vBoxLayout = QtWidgets.QVBoxLayout()

        #
        # control bar
        hBoxLayoutControls = QtWidgets.QHBoxLayout()

        lineWidthLabel = QtWidgets.QLabel('Line Width (pixels)')
        hBoxLayoutControls.addWidget(lineWidthLabel)

        lineWidthSpinbox = QtWidgets.QSpinBox()
        lineWidthSpinbox.setMinimum(1)
        lineWidthSpinbox.setValue(self._kymographAnalysis.getLineWidth())
        lineWidthSpinbox.valueChanged.connect(self.setLineWidth)  # triggers as user types e.g. (22)
        hBoxLayoutControls.addWidget(lineWidthSpinbox)

        # percent of max in line profile (for analysis)
        percentMaxLabel = QtWidgets.QLabel('Percent Of Max')
        hBoxLayoutControls.addWidget(percentMaxLabel)

        percentMaxSpinbox = QtWidgets.QDoubleSpinBox()
        percentMaxSpinbox.setSingleStep(0.1)
        percentMaxSpinbox.setMinimum(0.001)
        percentMaxSpinbox.setValue(self._kymographAnalysis.getPercentOfMax())
        percentMaxSpinbox.valueChanged.connect(self.setPercentMax)  # triggers as user types e.g. (22)
        hBoxLayoutControls.addWidget(percentMaxSpinbox)

        buttonName = 'Reset ROI'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(lambda state, name=buttonName: self._buttonCallback(name))
        hBoxLayoutControls.addWidget(aButton)

        buttonName = 'Rot -90'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setEnabled(False)
        aButton.clicked.connect(lambda state, name=buttonName: self._buttonCallback(name))
        hBoxLayoutControls.addWidget(aButton)

        buttonName = 'Analyze'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(lambda state, name=buttonName: self._buttonCallback(name))
        hBoxLayoutControls.addWidget(aButton)

        buttonName = 'Save'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(lambda state, name=buttonName: self._buttonCallback(name))
        hBoxLayoutControls.addWidget(aButton)

        # 2nd row of controls
        hBoxLayoutControls2 = QtWidgets.QHBoxLayout()

        checkboxName = 'Line Profile'
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setChecked(True)
        aCheckBox.stateChanged.connect(lambda state, name=checkboxName: self._checkboxCallback(state,name))
        hBoxLayoutControls2.addWidget(aCheckBox)

        checkboxName = 'Diameter'
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setChecked(True)
        aCheckBox.stateChanged.connect(lambda state, name=checkboxName: self._checkboxCallback(state,name))
        hBoxLayoutControls2.addWidget(aCheckBox)

        checkboxName = 'Sum Line'
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setChecked(True)
        aCheckBox.stateChanged.connect(lambda state, name=checkboxName: self._checkboxCallback(state,name))
        hBoxLayoutControls2.addWidget(aCheckBox)

        # 3rd row of controls
        hBoxLayoutControls3 = QtWidgets.QHBoxLayout()

        percentMaxLabel = QtWidgets.QLabel('y: um/pixel')
        hBoxLayoutControls3.addWidget(percentMaxLabel)

        percentMaxLabel = QtWidgets.QLabel('x: sec/line')
        hBoxLayoutControls3.addWidget(percentMaxLabel)

        # add 2 rows of controls
        vBoxLayout.addLayout(hBoxLayoutControls)
        vBoxLayout.addLayout(hBoxLayoutControls2)
        vBoxLayout.addLayout(hBoxLayoutControls3)

        # 1) kymograph image
        self.kymographWindow = pg.PlotWidget()
        self.kymographWindow.setLabel('left', 'Line Scan', units='')
        #self.kymographWindow.setLabel('bottom', 'Time', units='')

        self.kymographImage = pg.ImageItem(self._kymographAnalysis.getImage())
        # setRect(x, y, w, h)
        imageRect = self._kymographAnalysis.getImageRect()  # (x,y,w,h)
        #pos, size = self._kymographAnalysis.getFullRectRoi()  # (x,y,w,h)
        self.kymographImage.setRect(imageRect[0], imageRect[1], imageRect[2], imageRect[3])
        #self.kymographImage.setRect(pos[0], pos[1], size[0], size[1])
        self.kymographWindow.addItem(self.kymographImage)

        # vertical line to show "Line Profile"
        sliceLine = pg.InfiniteLine(pos=0, angle=90)
        self._sliceLinesList.append(sliceLine) # keep a list of vertical slice lines so we can update all at once
        self.kymographWindow.addItem(sliceLine)

        # rectangulaar roi over image
        #_penWidth = self._kymographAnalysis.getLineWidth()
        _penWidth = 1
        rectPen = pg.mkPen('r', width=_penWidth)
        pos = self._kymographAnalysis.getPosRoi()
        size = self._kymographAnalysis.getSizeRoi()
        _imageRect = self._kymographAnalysis.getImageRect()   # (x,y,w,h)
        maxBounds = QtCore.QRectF(_imageRect[0], _imageRect[1],
                            _imageRect[2], _imageRect[3])
        #print('  init roi pos:', pos)
        #print('  init roi size:', size)
        #print('  init roi pos:', maxBounds)
        self._rectRoi = pg.ROI(pos=pos,
                            size=size, maxBounds=maxBounds,
                            pen=rectPen)
        self._rectRoi.addScaleHandle(pos=(1,0), center=(0,1))
        self._rectRoi.sigRegionChangeFinished.connect(self._slot_roi_changed)
        self.kymographWindow.addItem(self._rectRoi)

        vBoxLayout.addWidget(self.kymographWindow)

        #
        # 1.5) slider to step through "Line Profile"
        self.profileSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.profileSlider.setMinimum(0)
        self.profileSlider.setMaximum(self._kymographAnalysis.numLineScans())
        self.profileSlider.valueChanged.connect(self._on_slider_changed)
        vBoxLayout.addWidget(self.profileSlider)

        #
        # plot of just one line intensity
        self.lineIntensityPlotItem = pg.PlotWidget()
        self.lineIntensityPlotItem.setLabel('left', 'Intensity', units='')
        self.lineIntensityPlotItem.setLabel('bottom', 'Points', units='')
        self.lineIntensityPlot = self.lineIntensityPlotItem.plot(name='lineIntensityPlot')
        xPlot = np.arange(0, self._kymographAnalysis.pointsPerLineScan())
        yPlot = xPlot * np.nan
        self.lineIntensityPlot.setData(xPlot, yPlot, connect='finite')  # fill with nan
        # single point of left/right
        self.leftRightPlot = self.lineIntensityPlotItem.plot(name='leftRightPlot')

        vBoxLayout.addWidget(self.lineIntensityPlotItem)

        #
        # 3) dimaeter of each line scan
        self.diameterPlotItem = pg.PlotWidget()
        self.diameterPlotItem.setLabel('left', 'Diameter', units='')
        self.diameterPlot = self.diameterPlotItem.plot(name='diameterPlot')
        xPlot = np.arange(0, self._kymographAnalysis.numLineScans())
        yPlot = xPlot * np.nan
        self.diameterPlot.setData(xPlot, yPlot, connect='finite')  # fill with nan
        # link x-axis with kymograph PlotWidget
        self.diameterPlotItem.setXLink(self.kymographWindow)

        # vertical line to show "Line Profile"
        sliceLine = pg.InfiniteLine(pos=0, angle=90)
        self._sliceLinesList.append(sliceLine) # keep a list of vertical slice lines so we can update all at once
        self.diameterPlotItem.addItem(sliceLine)

        vBoxLayout.addWidget(self.diameterPlotItem)

        # 4) sum intensity of each line scan
        self.sumIntensityPlotItem = pg.PlotWidget()
        self.sumIntensityPlotItem.setLabel('left', 'Sum Intensity', units='')
        self.sumIntensityPlot = self.sumIntensityPlotItem.plot(name='sumIntensityPlot')
        xPlot = np.arange(0, self._kymographAnalysis.numLineScans())
        yPlot = xPlot * np.nan
        self.sumIntensityPlot.setData(xPlot, yPlot, connect='finite')  # fill with nan
        # link x-axis with kymograph PlotWidget
        self.sumIntensityPlotItem.setXLink(self.kymographWindow)

        # vertical line to show "Line PRofile"
        sliceLine = pg.InfiniteLine(pos=0, angle=90)
        self._sliceLinesList.append(sliceLine) # keep a list of vertical slice lines so we can update all at once
        self.sumIntensityPlotItem.addItem(sliceLine)

        vBoxLayout.addWidget(self.sumIntensityPlotItem)

        # finalize
        self.setLayout(vBoxLayout)

    def replot(self,path):

        logger.info('')
        
        self._kymographAnalysis = kymographAnalysis(path)
        
        # clear the image from the panel
        #self.kymographWindow.clear()
        
        self.kymographImage = pg.ImageItem(self._kymographAnalysis.getImage())
        # setRect(x, y, w, h)
        imageRect = self._kymographAnalysis.getImageRect()  # (x,y,w,h)
        self.kymographImage.setRect(imageRect[0], imageRect[1], imageRect[2], imageRect[3])
        self.kymographWindow.addItem(self.kymographImage)

        # update roi
        _imageRect = self._kymographAnalysis.getImageRect()   # (x,y,w,h)
        maxBounds = QtCore.QRectF(_imageRect[0], _imageRect[1],
                            _imageRect[2], _imageRect[3])
        self._rectRoi.maxBounds = maxBounds
        pos = self._kymographAnalysis.getPosRoi()
        size = self._kymographAnalysis.getSizeRoi()
        print(f'  pos:{pos}, size:{size}')
        self._rectRoi.setPos(pos)
        self._rectRoi.setSize(size)
        self._rectRoi.stateChanged()

        # update slider
        self.profileSlider.setMaximum(self._kymographAnalysis.numLineScans())

        #
        self._on_slider_changed(0)

        self.refreshSumLinePlot()
        self.refreshDiameterPlot()

    def refreshSumLinePlot(self):
        logger.info('')
        numLineScans = self._kymographAnalysis.numLineScans()
        #xPlot = self._kymographAnalysis.getResults('time_ms')
        xPlot = self._kymographAnalysis.getTimeArray()  # always the same
        yPlot = self._kymographAnalysis.getResults('sumintensity')

        self.sumIntensityPlot.setData(xPlot, yPlot, connect='finite')

    def refreshDiameterPlot(self):
        logger.info('')
        #numLineScans = self._kymographAnalysis.numLineScans()
        #xPlot = self._kymographAnalysis.getResults('time_ms')
        xPlot = self._kymographAnalysis.getTimeArray()  # always the same
        yDiam_um = self._kymographAnalysis.getResults('diameter_um')

        self.diameterPlot.setData(xPlot, yDiam_um, connect='finite')

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    #app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api=os.environ['PYQTGRAPH_QT_LIB']))
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    path = '/Users/cudmore/data/kym-example/control 2.5_0012.tif.frames/control 2.5_0012.tif'
    #path = '/Users/cudmore/data/sa-node-ca-video/HighK-aligned-8bit_ch1.tif'
    kw = kymographPlugin2(path)
    kw.show()

    #print(kw._kymographAnalysis._getHeader())

    sys.exit(app.exec_())