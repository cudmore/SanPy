"""
Widget to act as the interface for kymographPlugin

I am keeping it seperate because it can be used standalone.
"""

import os
import sys
from turtle import back
import numpy as np

from qtpy import QtGui, QtSql, QtCore, QtWidgets

import pyqtgraph as pg

# import qdarkstyle

# turn off qdarkstyle logging
# import logging
# logging.getLogger('qdarkstyle').setLevel(logging.WARNING)

# from shapeanalysisplugin._my_logger import logger
# from shapeanalysisplugin import kymographAnalysis

import sanpy
import sanpy.interface

# from sanpy import kymographAnalysis

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

class kymographPlugin2(QtWidgets.QWidget):
    def __init__(self, ba: sanpy.bAnalysis, parent=None):
        logger.info("")

        super().__init__(parent)

        # switching to hold actual bAnalysis
        # self._ba = sanpy.bAnalysis(path)
        self._ba = None
        if ba is not None and ba.fileLoader.isKymograph():
            self._ba = ba

        # self._kymographAnalysis = sanpy.kymographAnalysis(path)
        # dec 2022
        self._kymographAnalysis = None  # will be created in slotSwitchFile()
        if self._ba is not None:
            self._kymographAnalysis = sanpy.kymAnalysis(ba.getFilePath())

        self._imageMedianKernel = 0
        self._lineMedianKernel = 5

        self._currentLineNumber = 0

        self._fitIsVivible = True
        # keep track of left/right fit on top of kym image

        self._kymWidgetMain = None  # sanpy.interface.kymographWidget(self._ba)
        self._initGui()

        self._on_slider_changed(0)

        self.refreshSumLinePlot()
        self.refreshDiameterPlot()

    def _checkboxCallback(self, state: bool, name: str):
        logger.info(f"state:{state} name:{name}")
        if name == "Line Profile":
            self.showLineProfile(state)
        elif name == "Diameter":
            self.diameterPlotItem.setVisible(state)
        elif name == "Sum Line":
            self.sumIntensityPlotItem.setVisible(state)
        elif name == "Fit On Image":
            self._fitIsVivible = state
            self.refreshDiameterPlot()

    def showLineProfile(self, state: bool):
        """Toggle interface for "Line Profile" """
        # self.profileSlider.setVisible(state)

        self.lineIntensityPlotItem.setVisible(state)

        for line in self._sliceLinesList:
            line.setVisible(state)

    def _buttonCallback(self, name):
        logger.info(f"name:{name}")
        # pos = self._rectRoi.pos()  # (left, bottom)
        # size = self._rectRoi.size()  # (widht, height)
        # print(f'    pos:{pos} size:{size}')

        if name == "Reset ROI":
            pos, size = self._kymographAnalysis.getFullRectRoi()  # (w,h)
            self._rectRoi.setPos(pos)
            self._rectRoi.setSize(size)
            # set the x-axis of the image plot
            # self.kymographWindow.setXRange(0, shape[0])

        elif name == "Analyze":
            self._analyzeButton.setStyleSheet("background-color : #AA2222")
            self._analyzeButton.repaint()
            self._analyzeButton.update()
            QtCore.QCoreApplication.processEvents()

            # left_idx, right_idx = self._kymographAnalysis.getLineProfileWidth()
            imageMedianKernel = self._imageMedianKernel
            lineMedianKernel = self._lineMedianKernel
            self._kymographAnalysis.analyze(
                imageMedianKernel=imageMedianKernel, lineMedianKernel=lineMedianKernel
            )

            # self.refreshSumLinePlot()
            self.refreshDiameterPlot()

            self._analyzeButton.setStyleSheet("background-color : #22AA22")
            self._analyzeButton.repaint()
            self._analyzeButton.update()
            QtCore.QCoreApplication.processEvents()

        elif name == "Save":
            saveFilePath = self._kymographAnalysis.getAnalysisFile()
            # get file name to save
            # name = QtGui.QFileDialog.getSaveFileName(self, 'Save File')
            savefile, tmp = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save File", saveFilePath
            )
            self._kymographAnalysis.save(savefile)

        elif name == "Rot -90":
            newImage = self._kymographAnalysis.rotateImage()
            self.kymographImage.setImage(newImage)

        else:
            logger.warning(f'did not understand "{name}"')

    def setLineWidth(self, value: int):
        logger.info(value)
        if self._kymographAnalysis is not None:
            self._kymographAnalysis.setLineWidth(value)

    def setPercentMax(self, value: float):
        logger.info(f"value:{value}")
        if self._kymographAnalysis is not None:
            self._kymographAnalysis.setPercentOfMax(value)

    def slotSwitchFile(self, ba: sanpy.bAnalysis):
        if ba is not None and not ba.fileLoader.isKymograph():
            return

        self._ba = ba

        self._kymWidgetMain.slot_switchFile(ba=self._ba)

        path = self._ba.getFilePath()
        self._kymographAnalysis = sanpy.kymAnalysis(path)

        self.refreshSumLinePlot()
        self.refreshDiameterPlot()

    def _slot_roi_changed2(self, newRect):
        """User modified ROI.

        Sent from bKymographWidget. Rewrite of '_slot_roi_changed'
            To use new improved bKymographWidget

        Args:
            newRect: [l,t,r,b]
        """
        lNew = newRect[0]
        tNew = newRect[1]
        rNew = newRect[2]
        bNew = newRect[3]

        widthNew = rNew - lNew
        heightNew = tNew - bNew  # swapped

        _pos = (lNew, bNew)
        _size = (widthNew, heightNew)

        # pos = self._rectRoi.pos()
        # size = self._rectRoi.size()

        logger.info(f"pos:{_pos} size:{_size}")

        self._kymographAnalysis.setPosRoi(_pos)
        self._kymographAnalysis.setSizeRoi(_size)

        # update line profile plot
        # _lineScanValue = self.profileSlider.value()
        # self._on_slider_changed(_lineScanValue)

        # replot sum
        self.refreshSumLinePlot()

    def old_slot_roi_changed(self):
        pos = self._rectRoi.pos()
        size = self._rectRoi.size()

        logger.info(f"pos:{pos} size:{size}")

        self._kymographAnalysis.setPosRoi(pos)
        self._kymographAnalysis.setSizeRoi(size)

        # update line profile plot
        _lineScanValue = self.profileSlider.value()
        self._on_slider_changed(_lineScanValue)

    def setImageMedianKernel(self, value):
        self._imageMedianKernel = value

    def setLineMedianKernel(self, value):
        self._lineMedianKernel = value

        # refresh the line profile plot
        self._on_slider_changed(value=None)

    def _on_slider_changed(self, value: int = None):
        """Respond to user changing the "Line Scan" slider.

        Args:
            value: The line profile number
        """
        if self._ba is None:
            return

        if value is None:
            value = self._currentLineNumber
        else:
            self._currentLineNumber = value

        logger.info(f"value:{value}")

        xScale = self._ba._abf.tifHeader["secondsPerLine"]

        # secondsValue = value * self._kymographAnalysis._secondsPerLine
        secondsValue = value * xScale

        # update verical lines on top of plots
        for line in self._sliceLinesList:
            line.setValue(secondsValue)

        # update one line profile plot
        lineProfile, left_pnt, right_pnt = self._kymographAnalysis._getFitLineProfile(
            value, self._lineMedianKernel
        )
        # print('    left:', left, 'right:', right)

        # logger.info(f'  len(lineProfile):{len(lineProfile)} \
        #             left_pnt:{left_pnt} \
        #             right_pnt:{right_pnt}')

        # +1 because np.arange() does NOT include the last point
        # xData = np.arange(0, self._kymographAnalysis.pointsPerLineScan()+1)
        pointsPerLineScan = self._kymographAnalysis.pointsPerLineScan()
        umPerPixel = self._kymographAnalysis._umPerPixel
        logger.info(f"pointsPerLineScan:{pointsPerLineScan} umPerPixel:{umPerPixel}")

        xData = np.arange(0, pointsPerLineScan)
        xData = np.multiply(xData, umPerPixel)
        if len(xData) != len(lineProfile):
            logger.error(f"xData: {len(xData)}")
            logger.error(f"lineProfile: {len(lineProfile)}")
        self.lineIntensityPlot.setData(xData, lineProfile)

        # if the fit fails we get left/right as nan
        if np.isnan(left_pnt) or np.isnan(right_pnt):
            xLeftRightData = [np.nan, np.nan]
            yLeftRightData = [np.nan, np.nan]
        else:
            left_um = self._kymographAnalysis.pnt2um(left_pnt)
            right_um = self._kymographAnalysis.pnt2um(right_pnt)
            xLeftRightData = [left_um, right_um]
            # print(xLeftRightData)
            yLeftRightData = [lineProfile[left_pnt], lineProfile[right_pnt]]
        self.leftRightPlot.setData(xLeftRightData, yLeftRightData)

    def _initGui(self):
        self.setWindowTitle("Kymograph Analysis")

        self._sliceLinesList = []

        vBoxLayout = QtWidgets.QVBoxLayout()

        # new oct 5 rosie
        #
        # kymograph widget from main interface
        self._kymWidgetMain = sanpy.interface.kymographWidget(
            self._ba
        )  # will handle na is None
        self._kymWidgetMain.signalKymographRoiChanged.connect(self._slot_roi_changed2)
        self._kymWidgetMain.signalLineSliderChanged.connect(self._on_slider_changed)
        vBoxLayout.addWidget(self._kymWidgetMain)

        #
        # control bar
        hBoxLayoutControls = QtWidgets.QHBoxLayout()

        lineWidthLabel = QtWidgets.QLabel("Line Width (pixels)")
        hBoxLayoutControls.addWidget(lineWidthLabel)

        lineWidthSpinbox = QtWidgets.QSpinBox()
        lineWidthSpinbox.setMinimum(1)
        if self._kymographAnalysis is not None:
            lineWidthSpinbox.setValue(self._kymographAnalysis.getLineWidth())
        else:
            lineWidthSpinbox.setValue(1)
        lineWidthSpinbox.valueChanged.connect(
            self.setLineWidth
        )  # triggers as user types e.g. (22)
        hBoxLayoutControls.addWidget(lineWidthSpinbox)

        # percent of max in line profile (for analysis)
        percentMaxLabel = QtWidgets.QLabel("Percent Of Max")
        hBoxLayoutControls.addWidget(percentMaxLabel)

        percentMaxSpinbox = QtWidgets.QDoubleSpinBox()
        percentMaxSpinbox.setSingleStep(0.1)
        percentMaxSpinbox.setMinimum(0.001)
        if self._kymographAnalysis is not None:
            percentMaxSpinbox.setValue(self._kymographAnalysis.getPercentOfMax())
        else:
            percentMaxSpinbox.setValue(10)
        percentMaxSpinbox.valueChanged.connect(
            self.setPercentMax
        )  # triggers as user types e.g. (22)
        hBoxLayoutControls.addWidget(percentMaxSpinbox)

        # median kernels for image and line profile
        medianLabel = QtWidgets.QLabel("Median Image")
        hBoxLayoutControls.addWidget(medianLabel)

        imageMedianKernelSpinbox = QtWidgets.QSpinBox()
        imageMedianKernelSpinbox.setMinimum(0)
        imageMedianKernelSpinbox.setValue(self._imageMedianKernel)
        imageMedianKernelSpinbox.valueChanged.connect(
            self.setImageMedianKernel
        )  # triggers as user types e.g. (22)
        hBoxLayoutControls.addWidget(imageMedianKernelSpinbox)

        medianLabel2 = QtWidgets.QLabel("Line")
        hBoxLayoutControls.addWidget(medianLabel2)

        aSpinbox = QtWidgets.QSpinBox()
        aSpinbox.setMinimum(0)
        aSpinbox.setValue(self._lineMedianKernel)
        aSpinbox.valueChanged.connect(
            self.setLineMedianKernel
        )  # triggers as user types e.g. (22)
        hBoxLayoutControls.addWidget(aSpinbox)

        # buttons
        # buttonName = 'Reset ROI'
        # aButton = QtWidgets.QPushButton(buttonName)
        # aButton.clicked.connect(lambda state, name=buttonName: self._buttonCallback(name))
        # hBoxLayoutControls.addWidget(aButton)

        # buttonName = 'Rot -90'
        # aButton = QtWidgets.QPushButton(buttonName)
        # aButton.setEnabled(False)
        # aButton.clicked.connect(lambda state, name=buttonName: self._buttonCallback(name))
        # hBoxLayoutControls.addWidget(aButton)

        # keep reference to button so we can change color during analysis
        buttonName = "Analyze"
        self._analyzeButton = QtWidgets.QPushButton(buttonName)
        self._analyzeButton.setStyleSheet("background-color : #22AA22")
        self._analyzeButton.clicked.connect(
            lambda state, name=buttonName: self._buttonCallback(name)
        )
        hBoxLayoutControls.addWidget(self._analyzeButton)

        buttonName = "Save"
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(
            lambda state, name=buttonName: self._buttonCallback(name)
        )
        hBoxLayoutControls.addWidget(aButton)

        # 2nd row of controls
        hBoxLayoutControls2 = QtWidgets.QHBoxLayout()

        checkboxName = "Line Profile"
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setChecked(True)
        aCheckBox.stateChanged.connect(
            lambda state, name=checkboxName: self._checkboxCallback(state, name)
        )
        hBoxLayoutControls2.addWidget(aCheckBox)

        checkboxName = "Diameter"
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setChecked(True)
        aCheckBox.stateChanged.connect(
            lambda state, name=checkboxName: self._checkboxCallback(state, name)
        )
        hBoxLayoutControls2.addWidget(aCheckBox)

        checkboxName = "Sum Line"
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setChecked(True)
        aCheckBox.stateChanged.connect(
            lambda state, name=checkboxName: self._checkboxCallback(state, name)
        )
        hBoxLayoutControls2.addWidget(aCheckBox)

        checkboxName = "Fit On Image"
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setChecked(self._fitIsVivible)
        aCheckBox.stateChanged.connect(
            lambda state, name=checkboxName: self._checkboxCallback(state, name)
        )
        hBoxLayoutControls2.addWidget(aCheckBox)

        # 3rd row of controls
        # hBoxLayoutControls3 = QtWidgets.QHBoxLayout()

        # percentMaxLabel = QtWidgets.QLabel('y: um/pixel')
        # hBoxLayoutControls3.addWidget(percentMaxLabel)

        # percentMaxLabel = QtWidgets.QLabel('x: sec/line')
        # hBoxLayoutControls3.addWidget(percentMaxLabel)

        # add 2 rows of controls
        vBoxLayout.addLayout(hBoxLayoutControls)
        vBoxLayout.addLayout(hBoxLayoutControls2)
        # vBoxLayout.addLayout(hBoxLayoutControls3)

        # 1) kymograph image
        if 0:
            self.kymographWindow = pg.PlotWidget()
            self.kymographWindow.setLabel("left", "Line Scan", units="")
            # self.kymographWindow.setLabel('bottom', 'Time', units='')

            self.kymographImage = pg.ImageItem(self._kymographAnalysis.getImage())
            # setRect(x, y, w, h)
            imageRect = self._kymographAnalysis.getImageRect()  # (x,y,w,h)
            # pos, size = self._kymographAnalysis.getFullRectRoi()  # (x,y,w,h)
            self.kymographImage.setRect(
                imageRect[0], imageRect[1], imageRect[2], imageRect[3]
            )
            # self.kymographImage.setRect(pos[0], pos[1], size[0], size[1])
            self.kymographWindow.addItem(self.kymographImage)

            # vertical line to show "Line Profile"
            sliceLine = pg.InfiniteLine(pos=0, angle=90)
            self._sliceLinesList.append(
                sliceLine
            )  # keep a list of vertical slice lines so we can update all at once
            self.kymographWindow.addItem(sliceLine)

            # rectangulaar roi over image
            # _penWidth = self._kymographAnalysis.getLineWidth()
            _penWidth = 1
            rectPen = pg.mkPen("r", width=_penWidth)
            pos = self._kymographAnalysis.getPosRoi()
            size = self._kymographAnalysis.getSizeRoi()
            _imageRect = self._kymographAnalysis.getImageRect()  # (x,y,w,h)
            maxBounds = QtCore.QRectF(
                _imageRect[0], _imageRect[1], _imageRect[2], _imageRect[3]
            )
            # print('  init roi pos:', pos)
            # print('  init roi size:', size)
            # print('  init roi pos:', maxBounds)
            self._rectRoi = pg.ROI(pos=pos, size=size, maxBounds=maxBounds, pen=rectPen)
            self._rectRoi.addScaleHandle(pos=(1, 0), center=(0, 1))
            self._rectRoi.sigRegionChangeFinished.connect(
                self._slot_roi_changed
            )  # remove
            self.kymographWindow.addItem(self._rectRoi)

            vBoxLayout.addWidget(self.kymographWindow)

        #
        # 1.5) slider to step through "Line Profile"
        if 0:
            self.profileSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.profileSlider.setMinimum(0)
            self.profileSlider.setMaximum(self._kymographAnalysis.numLineScans())
            self.profileSlider.valueChanged.connect(self._on_slider_changed)
            vBoxLayout.addWidget(self.profileSlider)

        #
        # plot of just one line intensity
        self.lineIntensityPlotItem = pg.PlotWidget()
        self.lineIntensityPlotItem.setLabel("left", "Intensity", units="")
        self.lineIntensityPlotItem.setLabel("bottom", "Points", units="")
        self.lineIntensityPlot = self.lineIntensityPlotItem.plot(
            name="lineIntensityPlot"
        )
        if self._kymographAnalysis is not None:
            xPlot = np.arange(0, self._kymographAnalysis.pointsPerLineScan())
        else:
            xPlot = np.arange(0, 0)
        yPlot = xPlot * np.nan
        self.lineIntensityPlot.setData(xPlot, yPlot, connect="finite")  # fill with nan
        # single point of left/right
        self.leftRightPlot = self.lineIntensityPlotItem.plot(name="leftRightPlot")

        vBoxLayout.addWidget(self.lineIntensityPlotItem)

        #
        # 3) dimaeter of each line scan
        self.diameterPlotItem = pg.PlotWidget()
        self.diameterPlotItem.setLabel("left", "Diameter", units="")
        self.diameterPlot = self.diameterPlotItem.plot(name="diameterPlot")
        if self._kymographAnalysis is not None:
            xPlot = np.arange(0, self._kymographAnalysis.numLineScans())
        else:
            xPlot = np.arange(0, 0)
        yPlot = xPlot * np.nan
        self.diameterPlot.setData(xPlot, yPlot, connect="finite")  # fill with nan
        # link x-axis with kymograph PlotWidget
        # self.diameterPlotItem.setXLink(self.kymographWindow)
        # link to kymographWidget plot of the image
        self.diameterPlotItem.setXLink(self._kymWidgetMain.kymographPlot)

        # vertical line to show "Line Profile"
        sliceLine = pg.InfiniteLine(pos=0, angle=90)
        self._sliceLinesList.append(
            sliceLine
        )  # keep a list of vertical slice lines so we can update all at once
        self.diameterPlotItem.addItem(sliceLine)

        vBoxLayout.addWidget(self.diameterPlotItem)

        # 4) sum intensity of each line scan
        self.sumIntensityPlotItem = pg.PlotWidget()
        self.sumIntensityPlotItem.setLabel("left", "Sum Intensity", units="")
        self.sumIntensityPlot = self.sumIntensityPlotItem.plot(name="sumIntensityPlot")
        # TODO: fix
        if self._ba is not None:
            _recordingDur = self._ba.recordingDur
        else:
            _recordingDur = 0
        # xPlot = np.arange(0, self._kymographAnalysis.numLineScans())
        xPlot = np.arange(0, _recordingDur)
        yPlot = xPlot * np.nan
        self.sumIntensityPlot.setData(xPlot, yPlot, connect="finite")  # fill with nan
        # link x-axis with kymograph PlotWidget
        # self.sumIntensityPlotItem.setXLink(self.kymographWindow)
        # link to kymographWidget plot of the image
        self.sumIntensityPlotItem.setXLink(self._kymWidgetMain.kymographPlot)

        # vertical line to show "Line Profile"
        sliceLine = pg.InfiniteLine(pos=0, angle=90)
        self._sliceLinesList.append(
            sliceLine
        )  # keep a list of vertical slice lines so we can update all at once
        self.sumIntensityPlotItem.addItem(sliceLine)

        vBoxLayout.addWidget(self.sumIntensityPlotItem)

        # finalize
        self.setLayout(vBoxLayout)

    def old_replot(self, path):
        logger.info("")

        self._kymographAnalysis = sanpy.kymAnalysis(path)

        if 0:
            # clear the image from the panel
            # self.kymographWindow.clear()

            self.kymographImage = pg.ImageItem(self._kymographAnalysis.getImage())
            # setRect(x, y, w, h)
            imageRect = self._kymographAnalysis.getImageRect()  # (x,y,w,h)
            self.kymographImage.setRect(
                imageRect[0], imageRect[1], imageRect[2], imageRect[3]
            )
            self.kymographWindow.addItem(self.kymographImage)

            # update roi
            _imageRect = self._kymographAnalysis.getImageRect()  # (x,y,w,h)
            maxBounds = QtCore.QRectF(
                _imageRect[0], _imageRect[1], _imageRect[2], _imageRect[3]
            )
            self._rectRoi.maxBounds = maxBounds
            pos = self._kymographAnalysis.getPosRoi()
            size = self._kymographAnalysis.getSizeRoi()
            print(f"  pos:{pos}, size:{size}")
            self._rectRoi.setPos(pos)
            self._rectRoi.setSize(size)
            self._rectRoi.stateChanged()

        # update slider
        # self.profileSlider.setMaximum(self._kymographAnalysis.numLineScans())

        #
        # self._on_slider_changed(0)

        self.refreshSumLinePlot()
        self.refreshDiameterPlot()

    def refreshSumLinePlot(self):
        logger.info("")
        if self._ba is None:
            return
        numLineScans = self._kymographAnalysis.numLineScans()
        # xPlot = self._kymographAnalysis.getResults('time_ms')

        # xPlot = self._kymographAnalysis.getTimeArray()  # always the same
        # yPlot = self._kymographAnalysis.getResults('sumintensity')

        xPlot = self._ba.fileLoader.sweepX
        yPlot = self._ba.fileLoader.sweepY

        self.sumIntensityPlot.setData(xPlot, yPlot, connect="finite")

    def refreshDiameterPlot(self):
        logger.info("")
        if self._ba is None:
            return
        # numLineScans = self._kymographAnalysis.numLineScans()
        # xPlot = self._kymographAnalysis.getResults('time_ms')
        # xPlot = self._kymographAnalysis.getTimeArray()  # always the same
        xPlot = self._ba.fileLoader.sweepX
        yDiam_um = self._kymographAnalysis.getResults("diameter_um")

        self.diameterPlot.setData(xPlot, yDiam_um, connect="finite")

        # show start/stop of fit in main kymograph
        left_pnt = self._kymographAnalysis.getResults("left_pnt")
        right_pnt = self._kymographAnalysis.getResults("right_pnt")
        self._kymWidgetMain.updateLeftRightFit(
            left_pnt, right_pnt, visible=self._fitIsVivible
        )


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api=os.environ['PYQTGRAPH_QT_LIB']))
    # app.setStyleSheet(qdarkstyle.load_stylesheet())

    path = "/Users/cudmore/data/kym-example/control 2.5_0012.tif.frames/control 2.5_0012.tif"
    # path = '/Users/cudmore/data/sa-node-ca-video/HighK-aligned-8bit_ch1.tif'

    path = "/Users/cudmore/data/rosie/Raw data for contraction analysis/Female Old/filter median 1 C2-0-255 Cell 2 CTRL  2_5_21 female wt old.tif"

    ba = sanpy.bAnalysis(path)

    kw = kymographPlugin2(ba)
    kw.show()

    # print(kw._kymographAnalysis._getHeader())

    sys.exit(app.exec_())
