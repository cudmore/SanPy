"""
Display a tif kymograph and allow user to modify a rect roi

Used by main SanPy interface and kymograph plugin
"""

import sys
import numpy as np
from functools import partial

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

import sanpy

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class myCustomDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Set Kymograph Scale!")

        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        hLayout = QtWidgets.QHBoxLayout()

        xScaleLabel = QtWidgets.QLabel("Seconds/Line")
        self.xScale = QtWidgets.QDoubleSpinBox()
        self.xScale.setDecimals(4)

        yScaleLabel = QtWidgets.QLabel("Microns/Pixel")
        self.yScale = QtWidgets.QDoubleSpinBox()
        self.yScale.setDecimals(4)

        hLayout.addWidget(xScaleLabel)
        hLayout.addWidget(self.xScale)

        hLayout.addWidget(yScaleLabel)
        hLayout.addWidget(self.yScale)

        self.layout = QtWidgets.QVBoxLayout()
        # message = QtWidgets.QLabel("Set Kymograph Scale")
        # self.layout.addWidget(message)

        self.layout.addLayout(hLayout)

        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def getResults(self) -> dict:
        """Get values from user input."""
        xScale = self.xScale.value()
        yScale = self.yScale.value()
        retDict = {
            "secondsPerLine": xScale,
            "umPerPixel": yScale,
        }
        return retDict


def showdialog():
    d = QtWidgets.QDialog()
    b1 = QtWidgets.QPushButton("ok", d)
    b1.move(50, 50)
    d.setWindowTitle("Set Kymograph Scale")
    d.setWindowModality(QtCore.Qt.ApplicationModal)
    d.exec_()


class kymographImage(pg.ImageItem):
    """
    Utility class to inherit and redefine some functions.
    """

    def mouseClickEvent(self, event):
        # print("Click", event.pos())
        x = event.pos().x()
        y = event.pos().y()

    def mouseDragEvent(self, event):
        return

        if event.isStart():
            print("Start drag", event.pos())
        elif event.isFinish():
            print("Stop drag", event.pos())
        else:
            print("Drag", event.pos())

    def old_hoverEvent(self, event):
        logger.info("")
        if not event.isExit():
            # the mouse is hovering over the image; make sure no other items
            # will receive left click/drag events from here.
            event.acceptDrags(pg.QtCore.Qt.LeftButton)
            event.acceptClicks(pg.QtCore.Qt.LeftButton)


class kymographWidget(QtWidgets.QWidget):
    """Display a kymograph with contrast controls."""

    signalKymographRoiChanged = QtCore.pyqtSignal(object)  # list of [l, t, r, b]
    signalSwitchToMolar = QtCore.pyqtSignal(
        object, object, object
    )  # (boolean, kd, caConc)
    signalScaleChanged = QtCore.pyqtSignal(object)  # dict with x/y scale
    signalLineSliderChanged = QtCore.pyqtSignal(object)  # int, new line selected

    def __init__(self, ba=None, parent=None):
        """
        ba: bAnalysis
        """
        super().__init__(parent)

        logger.info(f"{type(ba)}")

        bitDepth = 8
        self._minContrast = 0
        self._maxContrast = 2**bitDepth

        self.ba = ba

        self.myImageItem = None  # kymographImage
        self.myLineRoi = None
        self.myLineRoiBackground = None
        self.myColorBarItem = None

        self._buildUI()
        self._replot()

    def on_convert_to_nm_clicked(self, value):
        onOff = value == 2
        # self.detectionWidget.toggleCrosshair(onOff)
        self.signalSwitchToMolar.emit(onOff)

    def on_button_click(self, name):
        logger.info(name)
        if name == "Reset ROI":
            newRect = self.ba.fileLoader.resetKymographRect()
            # self.ba._updateTifRoi(newRect)
            self._replot()
            self.signalKymographRoiChanged.emit(newRect)  # underlying _abf has new rect

        else:
            logger.info(f"Case not taken: {name}")

    def _buildMolarLayout(self):
        """Layout to conver sum intensity (for each line scan) into molar.

        Seems a bit silly.
        """
        molarLayout = QtWidgets.QHBoxLayout()

        # todo: add checkbox to turn kn/rest calculation on off
        #            need signal
        convertToMolarCheckBox = QtWidgets.QCheckBox("Convert to Molar")
        convertToMolarCheckBox.setChecked(False)
        convertToMolarCheckBox.stateChanged.connect(self.on_convert_to_nm_clicked)
        convertToMolarCheckBox.setDisabled(True)
        molarLayout.addWidget(convertToMolarCheckBox)

        #
        # kd
        kdLabel = QtWidgets.QLabel("kd")
        molarLayout.addWidget(kdLabel)

        kdDefault = 22.1
        self.kdSpinBox = QtWidgets.QDoubleSpinBox()
        self.kdSpinBox.setMinimum(0)
        self.kdSpinBox.setMaximum(+1e6)
        self.kdSpinBox.setValue(kdDefault)
        self.kdSpinBox.setDisabled(True)
        # self.kdSpinBox.setSpecialValueText("None")
        molarLayout.addWidget(self.kdSpinBox)

        #
        # resting Ca
        restingCaLabel = QtWidgets.QLabel("Resting Ca")
        molarLayout.addWidget(restingCaLabel)

        restingCaDefault = 113.7
        self.restingCaSpinBox = QtWidgets.QDoubleSpinBox()
        self.restingCaSpinBox.setMinimum(0)
        self.restingCaSpinBox.setMaximum(+1e6)
        self.restingCaSpinBox.setValue(restingCaDefault)
        self.restingCaSpinBox.setDisabled(True)
        # self.kdSpinBox.setSpecialValueText("None")
        molarLayout.addWidget(self.restingCaSpinBox)

        return molarLayout

    def _buildControlBarLayout(self):
        # get underlying scale from sanpy.bAbfText tif header
        xScale = "None"
        yScale = "None"
        xPixels = None
        yPixels = None
        _fileName = None
        if self.ba is not None:
            xScale = self.ba._abf.tifHeader["secondsPerLine"]
            yScale = self.ba._abf.tifHeader["umPerPixel"]

            yPixels, xPixels = self.ba.tifData.shape  # numpy order is (y,x)

            _fileName = self.ba.getFileName()

        controlBarLayout = QtWidgets.QHBoxLayout()

        self._fileNameLabel = QtWidgets.QLabel(f"{_fileName}")
        controlBarLayout.addWidget(self._fileNameLabel)

        # pixels

        aLabel = QtWidgets.QLabel(f"Pixels X:")
        controlBarLayout.addWidget(aLabel)

        self.xPixelLabel = QtWidgets.QLabel(f"{xPixels}")
        controlBarLayout.addWidget(self.xPixelLabel)

        aLabel = QtWidgets.QLabel(f"Y:")
        controlBarLayout.addWidget(aLabel)

        self.yPixelLabel = QtWidgets.QLabel(f"{yPixels}")
        controlBarLayout.addWidget(self.yPixelLabel)

        # scale

        aLabel = QtWidgets.QLabel(f"Scale X:")
        controlBarLayout.addWidget(aLabel)

        self.xScaleLabel = QtWidgets.QLabel(f"{xScale}")
        controlBarLayout.addWidget(self.xScaleLabel)

        aLabel = QtWidgets.QLabel(f"Y:")
        controlBarLayout.addWidget(aLabel)

        self.yScaleLabel = QtWidgets.QLabel(f"{yScale}")
        controlBarLayout.addWidget(self.yScaleLabel)

        # reset

        buttonName = "Reset ROI"
        button = QtWidgets.QPushButton(buttonName)
        # button.setToolTip('Detect spikes using dV/dt threshold.')
        button.clicked.connect(partial(self.on_button_click, buttonName))
        controlBarLayout.addWidget(button)

        return controlBarLayout

    def _buildUI(self):
        # one row of controls and then kymograph image
        self.myVBoxLayout = QtWidgets.QVBoxLayout(self)
        self.myVBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        if 0:
            molarLayout = self._buildMolarLayout()
            self.myVBoxLayout.addLayout(molarLayout)  #

        #
        controlBarLayout = self._buildControlBarLayout()
        self.myVBoxLayout.addLayout(controlBarLayout)  #

        # #
        # # display the (min, max, cursor) intensity
        # controlBarLayout0 = QtWidgets.QHBoxLayout()
        # # min
        # self.tifMinLabel = QtWidgets.QLabel('Min:')
        # controlBarLayout0.addWidget(self.tifMinLabel)
        # # max
        # self.tifMaxLabel = QtWidgets.QLabel('Max:')
        # controlBarLayout0.addWidget(self.tifMaxLabel)
        # # roi min
        # self.roiMinLabel = QtWidgets.QLabel('ROI Min:')
        # controlBarLayout0.addWidget(self.roiMinLabel)
        # # roi max
        # self.roiMaxLabel = QtWidgets.QLabel('ROI Max:')
        # controlBarLayout0.addWidget(self.roiMaxLabel)

        # background min
        # self.backgroundRoiMinLabel = QtWidgets.QLabel('Background Min:')
        # controlBarLayout0.addWidget(self.backgroundRoiMinLabel)
        # background max
        # self.backgroundRoiMaxLabel = QtWidgets.QLabel('Background Max:')
        # controlBarLayout0.addWidget(self.backgroundRoiMaxLabel)

        # # cursor
        self.tifCursorLabel = QtWidgets.QLabel("Cursor:")
        # controlBarLayout0.addWidget(self.tifCursorLabel)

        #
        # self.myVBoxLayout.addLayout(controlBarLayout0) #

        #
        # contrast sliders
        bitDepth = 8

        # min
        minContrastLayout = QtWidgets.QHBoxLayout()

        minLabel = QtWidgets.QLabel("Min")
        minContrastLayout.addWidget(minLabel)

        self.minContrastSpinBox = QtWidgets.QSpinBox()
        self.minContrastSpinBox.setMinimum(0)
        self.minContrastSpinBox.setMaximum(2**bitDepth)
        minContrastLayout.addWidget(self.minContrastSpinBox)

        minContrastSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        minContrastSlider.setMinimum(0)
        minContrastSlider.setMaximum(2**bitDepth)
        minContrastSlider.setValue(0)
        # myLambda = lambda chk, item=canvasName: self._userSelectCanvas(chk, item)
        minContrastSlider.valueChanged.connect(
            lambda val, name="min": self._onContrastSliderChanged(val, name)
        )
        minContrastLayout.addWidget(minContrastSlider)

        # image min
        self.tifMinLabel = QtWidgets.QLabel("Min:")
        minContrastLayout.addWidget(self.tifMinLabel)

        # roi min
        self.roiMinLabel = QtWidgets.QLabel("ROI Min:")
        minContrastLayout.addWidget(self.roiMinLabel)

        self.myVBoxLayout.addLayout(minContrastLayout)  #

        # max
        maxContrastLayout = QtWidgets.QHBoxLayout()

        maxLabel = QtWidgets.QLabel("Max")
        maxContrastLayout.addWidget(maxLabel)

        self.maxContrastSpinBox = QtWidgets.QSpinBox()
        self.maxContrastSpinBox.setMinimum(0)
        self.maxContrastSpinBox.setMaximum(2**bitDepth)
        maxContrastLayout.addWidget(self.maxContrastSpinBox)

        maxContrastSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        maxContrastSlider.setMinimum(0)
        maxContrastSlider.setMaximum(2**bitDepth)
        maxContrastSlider.setValue(2**bitDepth)
        maxContrastSlider.valueChanged.connect(
            lambda val, name="max": self._onContrastSliderChanged(val, name)
        )
        maxContrastLayout.addWidget(maxContrastSlider)

        # image max
        self.tifMaxLabel = QtWidgets.QLabel("Max:")
        maxContrastLayout.addWidget(self.tifMaxLabel)

        # roi max
        self.roiMaxLabel = QtWidgets.QLabel("ROI Max:")
        maxContrastLayout.addWidget(self.roiMaxLabel)

        self.myVBoxLayout.addLayout(maxContrastLayout)  #

        #
        # kymograph
        self.view = pg.GraphicsLayoutWidget()
        # self.view.show()
        # self.kymographWindow = pg.PlotWidget()

        row = 0
        colSpan = 1
        rowSpan = 1
        self.kymographPlot = self.view.addPlot(
            row=row, col=0, rowSpan=rowSpan, colSpan=colSpan
        )
        self.kymographPlot.enableAutoRange()
        # turn off x/y dragging of deriv and vm
        self.kymographPlot.setMouseEnabled(x=False, y=True)
        # hide the little 'A' button to rescale axis
        self.kymographPlot.hideButtons()
        # turn off right-click menu
        self.kymographPlot.setMenuEnabled(False)
        # hide by default
        self.kymographPlot.hide()  # show in _replot() if self.ba.isKymograph()

        # TODO: add show/hide, we do not want this in the main interface
        # vertical line to show selected line scan (adjusted/changed with slider)
        self._sliceLine = pg.InfiniteLine(pos=0, angle=90)
        # self._sliceLinesList.append(sliceLine) # keep a list of vertical slice lines so we can update all at once
        self.kymographPlot.addItem(self._sliceLine)

        self.myVBoxLayout.addWidget(self.view)

        #
        # # add scatter plot for rising/falling diameter detection
        # color = 'g'
        # symbol = 'o'
        # leftDiamScatterPlot = pg.PlotDataItem(pen=None, symbol=symbol, symbolSize=6, symbolPen=None, symbolBrush=color)
        # leftDiamScatterPlot.setData(x=[], y=[]) # start empty

        # color = 'r'
        # symbol = 'o'
        # rightDiamScatterPlot = pg.PlotDataItem(pen=None, symbol=symbol, symbolSize=6, symbolPen=None, symbolBrush=color)
        # rightDiamScatterPlot.setData(x=[], y=[]) # start empty

        # self.kymographPlot.addItem(leftDiamScatterPlot)
        # self.kymographPlot.addItem(rightDiamScatterPlot)

        #
        # 1.5) slider to step through "Line Profile"
        self._profileSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self._profileSlider.setMinimum(0)
        # TODO: cludge, fix
        _numLineScans = 0
        if self.ba is not None:
            _numLineScans = len(self.ba.fileLoader.sweepX) - 1
        self._profileSlider.setMaximum(_numLineScans)
        # self._profileSlider.setMaximum(self._kymographAnalysis.numLineScans())
        self._profileSlider.valueChanged.connect(self._on_line_slider_changed)
        self.myVBoxLayout.addWidget(self._profileSlider)

    def showLineSlider(self, visible):
        """Toggle line slider and vertical line (on image) on/off."""
        self._profileSlider.setVisible(visible)

    def _on_line_slider_changed(self, lineNumber: int):
        """Respond to user dragging the line slider.

        Args:
            lineNumber: Int line number, needs to be converted to 'seconds'
        """

        lineSeconds = lineNumber * self.ba._abf.tifHeader["secondsPerLine"]

        logger.info(f"lineNumber:{lineNumber} lineSeconds:{lineSeconds}")

        # set the vertical line
        self._sliceLine.setValue(lineSeconds)

        self.signalLineSliderChanged.emit(lineNumber)

    def _onContrastSliderChanged(self, val: int, name: str):
        """Respond to either the min or max contrast slider.

        Args:
            val: new value
            name: Name of slider, in ('min', 'max')
        """
        logger.info(f"{name} {val}")
        if name == "min":
            self._minContrast = val
            self.minContrastSpinBox.setValue(val)
        elif name == "max":
            self._maxContrast = val
            self.maxContrastSpinBox.setValue(val)
        self._replot()

    def getContrastEnhance(self, theMin=None, theMax=None):
        """Get contrast enhanced image."""
        bitDepth = 8

        if theMin is None:
            theMin = self._minContrast
        if theMax is None:
            theMax = self._maxContrast

        lut = np.arange(2**bitDepth, dtype="uint8")
        lut = self._getContrastedImage(lut, theMin, theMax)  # get a copy of the image
        theRet = np.take(lut, self.ba.tifData)
        return theRet

    def _getContrastedImage(
        self, image, display_min, display_max
    ):  # copied from Bi Rico
        # Here I set copy=True in order to ensure the original image is not
        # modified. If you don't mind modifying the original image, you can
        # set copy=False or skip this step.
        bitDepth = 8

        image = np.array(image, dtype=np.uint8, copy=True)
        image.clip(display_min, display_max, out=image)
        image -= display_min
        np.floor_divide(
            image,
            (display_max - display_min + 1) / (2**bitDepth),
            out=image,
            casting="unsafe",
        )
        # np.floor_divide(image, (display_max - display_min + 1) / 256,
        #                out=image, casting='unsafe')
        # return image.astype(np.uint8)
        return image

    def _replot(self, startSec=None, stopSec=None):
        logger.info("")

        if self.ba is None:
            return

        self.kymographPlot.clear()
        self.kymographPlot.show()

        myTif = self.getContrastEnhance()

        logger.info(
            f"  startSec:{startSec} stopSec:{stopSec} myTif.shape:{myTif.shape}"
        )  # like (519, 10000)

        # self.myImageItem = pg.ImageItem(myTif, axisOrder='row-major')
        #  TODO: set height to micro-meters
        axisOrder = "row-major"

        # todo: get from tifHeader
        umLength = self.ba.tifData.shape[0] * self.ba._abf.tifHeader["umPerPixel"]

        rect = [0, 0, self.ba.fileLoader.recordingDur, umLength]  # x, y, w, h

        if self.myImageItem is None:
            # first time build
            self.myImageItem = kymographImage(myTif, axisOrder=axisOrder, rect=rect)
            # redirect hover to self (to display intensity
            self.myImageItem.hoverEvent = self.hoverEvent
        else:
            # second time update
            # myTif = self.ba.tifData
            myTif = self.getContrastEnhance()
            self.myImageItem.setImage(myTif, axisOrder=axisOrder, rect=rect)
        self.kymographPlot.addItem(self.myImageItem)

        padding = 0
        if startSec is not None and stopSec is not None:
            self.kymographPlot.setXRange(
                startSec, stopSec, padding=padding
            )  # row major is different

        # re-add the vertical line
        self.kymographPlot.addItem(self._sliceLine)

        #
        # plot of diameter detection
        self._leftFitScatter = pg.ScatterPlotItem(
            size=3, brush=pg.mkBrush(50, 255, 50, 120)
        )
        _xFake = []  # self.ba.sweepX
        _yFake = []  # [200 for x in self.ba.sweepX]
        self._leftFitScatter.setData(_xFake, _yFake)
        self.kymographPlot.addItem(self._leftFitScatter)

        self._rightFitScatter = pg.ScatterPlotItem(
            size=3, brush=pg.mkBrush(255, 50, 50, 120)
        )
        _xFake = []  # self.ba.sweepX
        _yFake = []  # [350 for x in self.ba.sweepX]
        self._rightFitScatter.setData(_xFake, _yFake)
        self.kymographPlot.addItem(self._rightFitScatter)

        #
        # color bar with contrast !!!
        if myTif.dtype == np.dtype("uint8"):
            bitDepth = 8
        elif myTif.dtype == np.dtype("uint16"):
            bitDepth = 16
        else:
            bitDepth = 16
            logger.error(f"Did not recognize tif dtype: {myTif.dtype}")

        cm = pg.colormap.get(
            "Greens_r", source="matplotlib"
        )  # prepare a linear color map
        # values = (0, 2**bitDepth)
        # values = (0, maxTif)
        values = (0, 2**12)
        limits = (0, 2**12)
        # logger.info(f'color bar bit depth is {bitDepth} with values in {values}')
        doColorBar = False
        if doColorBar:
            if self.myColorBarItem == None:
                self.myColorBarItem = pg.ColorBarItem(
                    values=values,
                    limits=limits,
                    interactive=True,
                    label="",
                    cmap=cm,
                    orientation="horizontal",
                )
            # Have ColorBarItem control colors of img and appear in 'plot':
            self.myColorBarItem.setImageItem(
                self.myImageItem, insert_in=self.kymographPlot
            )
            self.myColorBarItem.setLevels(values=values)

        kymographRect = self.ba.fileLoader.getKymographRect()
        if kymographRect is not None:
            # TODO: I guess we always have a rect, o.w. this would be a runtime error
            xRoiPos = kymographRect[0]
            yRoiPos = kymographRect[3]
            top = kymographRect[1]
            right = kymographRect[2]
            bottom = kymographRect[3]
            widthRoi = right - xRoiPos + 1
            # heightRoi = bottom - yRoiPos + 1
            heightRoi = top - yRoiPos + 1
        """
        else:
            #  TODO: Put this logic into function in bAbfText
            pos, size = self.ba.defaultTifRoi()

            xRoiPos = 0  # startSeconds
            yRoiPos = 0  # pixels
            widthRoi = myTif.shape[1]
            heightRoi = myTif.shape[0]
            tifHeightPercent = myTif.shape[0] * 0.2
            #print('tifHeightPercent:', tifHeightPercent)
            yRoiPos += tifHeightPercent
            heightRoi -= 2 * tifHeightPercent
        """
        # TODO: get this out of replot, recreating the ROI is causing runtime error
        # update the rect roi
        pos = (xRoiPos, yRoiPos)
        size = (widthRoi, heightRoi)
        if self.myLineRoi is None:
            movable = False
            self.myLineRoi = pg.ROI(
                pos=pos, size=size, parent=self.myImageItem, movable=movable
            )
            # self.myLineRoi.addScaleHandle((0,0), (1,1), name='topleft')  # at origin
            self.myLineRoi.addScaleHandle(
                (0.5, 0), (0.5, 1), name="top center"
            )  # top center
            self.myLineRoi.addScaleHandle(
                (0.5, 1), (0.5, 0), name="bottom center"
            )  # bottom center
            # self.myLineRoi.addScaleHandle((0,0.5), (1,0.5))  # left center
            # self.myLineRoi.addScaleHandle((1,0.5), (0,0.5))  # right center
            # self.myLineRoi.addScaleHandle((1,1), (0,0), name='bottomright')  # bottom right
            self.myLineRoi.sigRegionChangeFinished.connect(self.kymographChanged)
        else:
            self.myLineRoi.setPos(pos, finish=False)
            self.myLineRoi.setSize(size, finish=False)

        #
        # background kymograph ROI
        backgroundRect = (
            self.ba.fileLoader.getKymographBackgroundRect()
        )  # keep this in the backend
        if backgroundRect is not None:
            xRoiPos = backgroundRect[0]
            yRoiPos = backgroundRect[3]
            top = backgroundRect[1]
            right = backgroundRect[2]
            bottom = backgroundRect[3]
            widthRoi = right - xRoiPos + 1
            # heightRoi = bottom - yRoiPos + 1
            heightRoi = top - yRoiPos + 1
        pos = (xRoiPos, yRoiPos)
        size = (widthRoi, heightRoi)

        if 0:
            if self.myLineRoiBackground is None:
                # TODO: get this out of replot, recreating the ROI is causing runtime error
                self.myLineRoiBackground = pg.ROI(
                    pos=pos, size=size, parent=self.myImageItem
                )
            else:
                self.myLineRoiBackground.setPos(pos, finish=False)
                self.myLineRoiBackground.setSize(size, finish=False)

        # update min/max labels
        # TODO: only set this once on switch file
        myTifOrig = self.ba.fileLoader.tifData
        minTif = np.nanmin(myTifOrig)
        maxTif = np.nanmax(myTifOrig)
        # print(type(dtype), dtype)  # <class 'numpy.dtype[uint16]'> uint16
        self.tifMinLabel.setText(f"Min:{minTif}")
        self.tifMaxLabel.setText(f"Max:{maxTif}")

        # update min/max displayed to user
        self._updateRoiMinMax(kymographRect)
        self._updateBackgroundRoiMinMax(backgroundRect)

    def updateLeftRightFit(self, yLeft, yRight, visible=True):
        """ """

        self._leftFitScatter.setVisible(visible)
        self._rightFitScatter.setVisible(visible)

        if visible:
            x = self.ba.fileLoader.sweepX
            # TODO: check that len(y) == len(x)
            self._leftFitScatter.setData(x, yLeft)
            self._rightFitScatter.setData(x, yRight)

    def _updateBackgroundRoiMinMax(self, backgroundRect=None):
        """
        update background roi

        TODO: Add self.ba.fileLoader.getBackGroundStats()

        """
        logger.warning(f"Need to add interface for user to adjust background roi")
        return

        if backgroundRect is None:
            backgroundRect = self.ba.fileLoader.getKymographBackgroundRect()

        left = backgroundRect[0]
        top = backgroundRect[1]
        right = backgroundRect[2]
        bottom = backgroundRect[3]

        myTif = self.ba.tifData
        tifClip = myTif[bottom:top, left:right]

        roiMin = np.nanmin(tifClip)
        roiMax = np.nanmax(tifClip)

        # self.backgroundRoiMinLabel.setText(f'Background Min:{roiMin}')
        # self.backgroundRoiMaxLabel.setText(f'Background Max:{roiMax}')

    def _updateRoiMinMax(self, theRect):
        left = theRect[0]
        top = theRect[1]
        right = theRect[2]
        bottom = theRect[3]

        logger.info(f"left:{left} top:{top} right:{right} bottom:{bottom}")

        myTif = self.ba.fileLoader.tifData
        tifClip = myTif[bottom:top, left:right]

        roiMin = np.nanmin(tifClip)
        roiMax = np.nanmax(tifClip)

        self.roiMinLabel.setText(f"ROI Min:{roiMin}")
        self.roiMaxLabel.setText(f"ROI Max:{roiMax}")

    def kymographChanged(self, event):
        """
        User finished gragging the ROI

        Args:
            event (pyqtgraph.graphicsItems.ROI.ROI)
        """
        logger.info("")
        # pos = event.pos()
        # size = event.size()

        _kymographRect = self.ba.fileLoader.getKymographRect()  # (l, t, r, b)

        left = _kymographRect[0]
        top = _kymographRect[1]
        right = _kymographRect[2]
        bottom = _kymographRect[3]

        handles = event.getSceneHandlePositions()
        for _idx, handle in enumerate(handles):
            logger.info(f"{_idx} handle: {handle}")
            if handle[0] is not None:
                # imagePos = self.myImageItem.mapFromScene(handle[1])
                imagePos = self.myImageItem.mapFromScene(handle[1])
                x = imagePos.x()
                y = imagePos.y()
                # units are in image pixels !!!
                # if handle[0] == 'topleft':
                #     left = x
                #     bottom = y
                # elif handle[0] == 'bottomright':
                #     right = x
                #     top = y
                if handle[0] == "top center":
                    top = y
                elif handle[0] == "bottom center":
                    bottom = y

        #
        left = int(left)
        top = int(top)
        right = int(right)
        bottom = int(bottom)

        if left < 0:
            left = 0
        if bottom < 0:
            bottom = 0

        # force left and right
        _kymographRect = self.ba.fileLoader.getKymographRect()  # (l, t, r, b)
        left = 0
        right = _kymographRect[2]

        logger.info(f"  left:{left} top:{top} right:{right} bottom:{bottom}")

        #  cludge
        if bottom > top:
            logger.warning(f"fixing bad top/bottom")
            tmp = top
            top = bottom
            bottom = tmp

        theRect = [left, top, right, bottom]

        self._updateRoiMinMax(theRect)

        # TODO: detection widget needs a slot to (i) analyze and then replot
        # self.ba._updateTifRoi(theRect)
        # self._replot(startSec=None, stopSec=None, userUpdate=True)
        # self.signalDetect.emit(self.ba)  # underlying _abf has new rect
        self.ba.fileLoader._updateTifRoi(theRect)
        self.signalKymographRoiChanged.emit(theRect)  # underlying _abf has new rect

    def slot_switchFile(self, ba=None, startSec=None, stopSec=None):
        if ba is not None and ba.fileLoader.isKymograph():
            self.ba = ba
            # self._updateRoiMinMax(theRect)
            self._replot(startSec=startSec, stopSec=stopSec)

            # update line scan slider
            _numLineScans = len(self.ba.fileLoader.sweepX) - 1
            self._profileSlider.setMaximum(_numLineScans)

    def hoverEvent(self, event):
        if event.isExit():
            return

        xPos = event.pos().x()
        yPos = event.pos().y()

        xPos = int(xPos)
        yPos = int(yPos)

        myTif = self.ba.fileLoader.tifData
        intensity = myTif[yPos, xPos]  # flipped

        # logger.info(f'x:{xPos} y:{yPos} intensity:{intensity}')

        self.tifCursorLabel.setText(f"Cursor:{intensity}")
        self.tifCursorLabel.update()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    if 1:
        path = "/media/cudmore/data/rabbit-ca-transient/jan-12-2022/Control/220110n_0003.tif.frames/220110n_0003.tif"
        path = "/Users/cudmore/data/rosie/test-data/filter median 1 C2-0-255 Cell 2 CTRL  2_5_21 female wt old.tif"

        ba = sanpy.bAnalysis(path)
        print(ba)

        kw = kymographWidget(ba)
        kw.show()

    # test dialog
    if 0:
        mcd = myCustomDialog()
        if mcd.exec():
            scaleDict = mcd.getResults()
            print(scaleDict)
        else:
            print('user did not hit "ok"')

    sys.exit(app.exec_())
