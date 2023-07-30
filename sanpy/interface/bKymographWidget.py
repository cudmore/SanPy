
import sys
import math
import numpy as np
from functools import partial

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

import sanpy

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class myScaleDialog(QtWidgets.QDialog):
    """Dialog to set x/y kymograph scale.
    
    If set, analysis has to be redone
    """
    def __init__(self, secondsPerLine :float, umPerPixel : float, parent=None):
        logger.info(f'secondsPerLine:{secondsPerLine} umPerPixel:{umPerPixel}')
        
        super().__init__(parent)

        self.setWindowTitle("Set Kymograph Scale")

        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        hLayout = QtWidgets.QHBoxLayout()

        xScaleLabel = QtWidgets.QLabel("Seconds/Line")
        self.xScale = QtWidgets.QDoubleSpinBox()
        self.xScale.setDecimals(5)
        self.xScale.setSingleStep(0.001)
        self.xScale.setValue(secondsPerLine)

        yScaleLabel = QtWidgets.QLabel("Microns/Pixel")
        self.yScale = QtWidgets.QDoubleSpinBox()
        self.yScale.setDecimals(3)
        self.yScale.setSingleStep(0.1)
        self.yScale.setValue(umPerPixel)

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

def showScaleDialog():
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
    """Display a kymograph image
    
     - a top toobar with
       - image size in pixels and um
       - contrast controls.
     - a draggable rect roi
     - allow user to set scale (right-click)
     """

    signalKymographRoiChanged = QtCore.pyqtSignal(object)  # list of [l, t, r, b]
    signalSwitchToMolar = QtCore.pyqtSignal(
        object, object, object
    )  # (boolean, kd, caConc)
    signalScaleChanged = QtCore.pyqtSignal(object)  # dict with x/y scale
    signalLineSliderChanged = QtCore.pyqtSignal(object)  # int, new line selected
    signalResetZoom = QtCore.pyqtSignal()  # int, new line selected

    def __init__(self, ba = None, parent = None):
        """
        ba: bAnalysis
        """
        super().__init__(parent)

        logger.info(f"{type(ba)}")

        self.ba = ba

        # bitDepth = 8
        self._minContrast = None  #0
        self._maxContrast = None  #2**bitDepth
        
        # self.guessContrastEnhance()

        self.myImageItem = None  # kymographImage
        self.myLineRoi = None
        self.myLineRoiBackground = None
        # self.myColorBarItem = None

        # self.guessContrastEnhance()

        self._buildUI()

        self.slot_switchFile(ba)  # trigger self._replot()

    def contextMenuEvent(self, event):
        """
        Parameters
        ----------
        event : QtGui.QContextMenuEvent
        """
        contextMenu = QtWidgets.QMenu(self)
        
        _visible = self._topToolbar.isVisible()
        toggleToolbar = QtWidgets.QAction("Top Toolbar", self, checkable=True)
        toggleToolbar.setChecked(_visible)
        toggleToolbar.triggered.connect(partial(self.showTopToolbar, not _visible))
        contextMenu.addAction(toggleToolbar)

        resetZoom = contextMenu.addAction("Reset Zoom")
        resetRoi = contextMenu.addAction("Reset ROI")
        setScale = contextMenu.addAction("Set Scale")
        
        action = contextMenu.exec_(self.mapToGlobal(event.pos()))
        if action == resetZoom:
            self._resetZoom()
        elif action == resetRoi:
            self._resetRoi()
        elif action == setScale:
            self._setScaleDialog()

    def _resetZoom(self, doEmit=True):
        imageBoundingRect = self.myImageItem.boundingRect()  # QtCore.QRectF
        
        _rect = self.ba.kymAnalysis.getImageRect()
        x = _rect.getLeft()
        y = _rect.getBottom()
        w = _rect.getWidth()
        h = _rect.getHeight()

        imageBoundingRect = QtCore.QRectF(x,y,w,h)

        logger.info(f'reset image zoom with imageBoundingRect (x,y,w,h):{imageBoundingRect}')
        
        padding = None
        self.kymographPlot.setRange(imageBoundingRect, padding=padding)
    
        if doEmit:
            self.signalResetZoom.emit()
        
    def _setScaleDialog(self):
        """Show a set scale dialog.
        """
        secondsPerLine = self.ba.fileLoader.tifHeader['secondsPerLine']
        umPerPixel = self.ba.fileLoader.tifHeader['umPerPixel']
        mcd = myScaleDialog(secondsPerLine, umPerPixel)
        if mcd.exec():
            scaleDict = mcd.getResults()
            #print('scaleDict:', scaleDict)
            # self.ba.fileLoader.tifHeader['secondsPerLine'] = scaleDict['secondsPerLine']
            # self.ba.fileLoader.tifHeader['umPerPixel'] = scaleDict['umPerPixel']
            secondsPerLine = scaleDict['secondsPerLine']
            umPerPixel = scaleDict['umPerPixel']
            self.ba.fileLoader.setScale(secondsPerLine, umPerPixel)

            self.xScaleLabel.setText(str(secondsPerLine))
            self.yScaleLabel.setText(str(umPerPixel))

            self._resetRoi()
            # self.ba.kymAnalysis.resetKymRect()
            # self._replot()

    def _old_on_convert_to_nm_clicked(self, value):
        onOff = value == 2
        # self.detectionWidget.toggleCrosshair(onOff)
        self.signalSwitchToMolar.emit(onOff)

    def _resetRoi(self):
        newRect = self.ba.kymAnalysis.resetKymRect()
        # self.ba._updateTifRoi(newRect)
        self._replot()
        
        logger.info(f'-->> emit signalKymographRoiChanged newRect:{newRect}')
        self.signalKymographRoiChanged.emit(newRect)  # underlying _abf has new rect

    def _old_on_button_click(self, name):
        logger.info(name)
        if name == "Reset ROI":
            self._resetRoi()
        else:
            logger.info(f"Case not taken: {name}")

    def _old__buildMolarLayout(self):
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

    def _refreshControlBarWidget(self):
        tifData = self.ba.fileLoader.tifData

       # x and y pixels
        _xPixels = str(tifData.shape[1])
        self.xPixelLabel.setText(_xPixels)
        _yPixels = str(tifData.shape[0])
        self.yPixelLabel.setText(_yPixels)

        # x and y scale
        secondsPerLine = str(self.ba.fileLoader.tifHeader['secondsPerLine'])
        self.xScaleLabel.setText(secondsPerLine)
        umPerPixel = str(self.ba.fileLoader.tifHeader['umPerPixel'])
        self.yScaleLabel.setText(umPerPixel)

        # update min/max labels
        tifData = self.ba.fileLoader.tifData
        minTif = np.nanmin(tifData)
        maxTif = np.nanmax(tifData)
        # print(type(dtype), dtype)  # <class 'numpy.dtype[uint16]'> uint16
        self.tifMinLabel.setText(f"Min:{minTif}")
        self.tifMaxLabel.setText(f"Max:{maxTif}")

        # update contrast slider controls
        bitDepth = self.ba.fileLoader.tifHeader['bitDepth']
        self.minContrastSpinBox.setMaximum(2**bitDepth)
        self.minContrastSlider.setMaximum(2**bitDepth)
        self.maxContrastSpinBox.setMaximum(2**bitDepth)
        self.maxContrastSlider.setMaximum(2**bitDepth)

        self.minContrastSpinBox.setValue(self._minContrast)
        self.minContrastSlider.setValue(self._minContrast)
        self.maxContrastSpinBox.setValue(self._maxContrast)
        self.maxContrastSlider.setValue(self._maxContrast)

    def _buildControlBarWidget(self) -> QtWidgets.QWidget:
        """Build a top control bar.
        """

        # get underlying scale from sanpy.bAbfText tif header
        xScale = "None"
        yScale = "None"
        xPixels = None
        yPixels = None
        _fileName = None
        if self.ba is not None:
            xScale = self.ba.fileLoader.tifHeader["secondsPerLine"]
            yScale = self.ba.fileLoader.tifHeader["umPerPixel"]

            yPixels, xPixels = self.ba.fileLoader.tifData.shape  # numpy order is (y,x)

            _fileName = self.ba.fileLoader.filename

        _VBoxLayout = QtWidgets.QVBoxLayout(self)

        controlBarLayout = QtWidgets.QHBoxLayout()
        _VBoxLayout.addLayout(controlBarLayout)

        self._fileNameLabel = QtWidgets.QLabel(f"{_fileName}")
        controlBarLayout.addWidget(self._fileNameLabel, alignment=QtCore.Qt.AlignLeft)

        # pixels
        aLabel = QtWidgets.QLabel(f"Pixels X:")
        controlBarLayout.addWidget(aLabel, alignment=QtCore.Qt.AlignLeft)

        self.xPixelLabel = QtWidgets.QLabel(f"{xPixels}")
        controlBarLayout.addWidget(self.xPixelLabel, alignment=QtCore.Qt.AlignLeft)

        aLabel = QtWidgets.QLabel(f"Y:")
        controlBarLayout.addWidget(aLabel, alignment=QtCore.Qt.AlignLeft)

        self.yPixelLabel = QtWidgets.QLabel(f"{yPixels}")
        controlBarLayout.addWidget(self.yPixelLabel, alignment=QtCore.Qt.AlignLeft)

        # scale
        aLabel = QtWidgets.QLabel(f"Scale X:")
        controlBarLayout.addWidget(aLabel, alignment=QtCore.Qt.AlignLeft)

        self.xScaleLabel = QtWidgets.QLabel(f"{xScale}")
        controlBarLayout.addWidget(self.xScaleLabel, alignment=QtCore.Qt.AlignLeft)

        aLabel = QtWidgets.QLabel(f"Y:")
        controlBarLayout.addWidget(aLabel, alignment=QtCore.Qt.AlignLeft)

        self.yScaleLabel = QtWidgets.QLabel(f"{yScale}")
        controlBarLayout.addWidget(self.yScaleLabel, alignment=QtCore.Qt.AlignLeft)

        # cursor
        self.tifCursorLabel = QtWidgets.QLabel("Cursor:")
        controlBarLayout.addWidget(self.tifCursorLabel, alignment=QtCore.Qt.AlignLeft)

        # align left
        controlBarLayout.addStretch()

        #
        # contrast sliders
        bitDepth = 8

        # min contrast row
        minContrastLayout = QtWidgets.QHBoxLayout()

        minLabel = QtWidgets.QLabel("Min")
        minContrastLayout.addWidget(minLabel)

        self.minContrastSpinBox = QtWidgets.QSpinBox()
        self.minContrastSpinBox.setMinimum(0)
        self.minContrastSpinBox.setMaximum(2**bitDepth)
        minContrastLayout.addWidget(self.minContrastSpinBox)

        self.minContrastSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.minContrastSlider.setMinimum(0)
        self.minContrastSlider.setMaximum(2**bitDepth)
        self.minContrastSlider.setValue(0)
        # myLambda = lambda chk, item=canvasName: self._userSelectCanvas(chk, item)
        self.minContrastSlider.valueChanged.connect(
            lambda val, name="min": self._onContrastSliderChanged(val, name)
        )
        minContrastLayout.addWidget(self.minContrastSlider)

        # image min
        self.tifMinLabel = QtWidgets.QLabel("Min:")
        minContrastLayout.addWidget(self.tifMinLabel)

        # roi min
        # self.roiMinLabel = QtWidgets.QLabel("ROI Min:")
        # minContrastLayout.addWidget(self.roiMinLabel)

        # self.myVBoxLayout.addLayout(minContrastLayout)  #
        _VBoxLayout.addLayout(minContrastLayout)

        # max contrast row
        maxContrastLayout = QtWidgets.QHBoxLayout()

        maxLabel = QtWidgets.QLabel("Max")
        maxContrastLayout.addWidget(maxLabel)

        self.maxContrastSpinBox = QtWidgets.QSpinBox()
        self.maxContrastSpinBox.setMinimum(0)
        self.maxContrastSpinBox.setMaximum(2**bitDepth)
        maxContrastLayout.addWidget(self.maxContrastSpinBox)

        self.maxContrastSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.maxContrastSlider.setMinimum(0)
        self.maxContrastSlider.setMaximum(2**bitDepth)
        self.maxContrastSlider.setValue(2**bitDepth)
        self.maxContrastSlider.valueChanged.connect(
            lambda val, name="max": self._onContrastSliderChanged(val, name)
        )
        maxContrastLayout.addWidget(self.maxContrastSlider)

        # image max
        self.tifMaxLabel = QtWidgets.QLabel("Max:")
        maxContrastLayout.addWidget(self.tifMaxLabel)

        # roi max
        # self.roiMaxLabel = QtWidgets.QLabel("ROI Max:")
        # maxContrastLayout.addWidget(self.roiMaxLabel)

        #self.myVBoxLayout.addLayout(maxContrastLayout)  #
        _VBoxLayout.addLayout(maxContrastLayout)

        _aWidget = QtWidgets.QWidget()
        _aWidget.setLayout(_VBoxLayout)

        #return controlBarLayout
        return _aWidget

    def showTopToolbar(self, visible : bool = True):
        self._topToolbar.setVisible(visible)

    
    def _buildUI(self):

        self.myVBoxLayout = QtWidgets.QVBoxLayout(self)
        # self.myVBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        if 0:
            molarLayout = self._buildMolarLayout()
            self.myVBoxLayout.addLayout(molarLayout)  #

        #
        self._topToolbar = self._buildControlBarWidget()  # one row with file name, image params
        self.myVBoxLayout.addWidget(self._topToolbar)
        self.showTopToolbar(False)  # initially hidden

        # kymograph
        self.view = pg.GraphicsLayoutWidget()

        row = 0
        colSpan = 1
        rowSpan = 1
        self.kymographPlot = self.view.addPlot(
            row=row, col=0, rowSpan=rowSpan, colSpan=colSpan
        )

        self.kymographPlot.enableAutoRange()

        # turn off x/y dragging of deriv and vm
        self.kymographPlot.setMouseEnabled(x=True, y=True)
        # hide the little 'A' button to rescale axis
        self.kymographPlot.hideButtons()
        # turn off right-click menu
        self.kymographPlot.setMenuEnabled(False)
        # hide by default
        # self.kymographPlot.hide()  # show in _replot() if self.ba.isKymograph()

        #myTif = self.getContrastEnhance()
        _fakeTif = np.ndarray((1,1))

        # todo: get from tifHeader
        # umLength = self.ba.fileLoader.tifData.shape[0] * self.ba.fileLoader.tifHeader["umPerPixel"]
        # # rect of the image uses x/y scale
        # rect = [0, 0, self.ba.fileLoader.recordingDur, umLength]  # x, y, w, h
        
        imageRect = None  #self.ba.kymAnalysis.getImageRect(asList=True)
        imageRect = QtCore.QRectF(QtCore.QPointF(0,0), QtCore.QPointF(0,0))
        # logger.info(f'  setting myImageItem with [x, y, w, h] rect:{imageRect}')

        # now using transpose .T
        axisOrder = "row-major"
        self.myImageItem = kymographImage(_fakeTif.T,
                                            #axisOrder=axisOrder,
                                            #rect=imageRect
                                            )
                
        # redirect hover to self (to display intensity
        self.myImageItem.hoverEvent = self.hoverEvent

        self.kymographPlot.addItem(self.myImageItem, ignorBounds=True)

        # kymographRect is in scaled units, we need plot units
        # kymographRect = self.ba.kymAnalysis.getRoiRect()
        # logger.info(f'getImageRect_no_scale kymographRect is {kymographRect}')
        # pos, size = kymographRect.getPosAndSize()

        pos = (0,0)
        size = (0,0)

        # TODO: add show/hide, we do not want this in the main interface
        # vertical line to show selected line scan (adjusted/changed with slider)
        self._sliceLine = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('y', width=2),)
        self.kymographPlot.addItem(self._sliceLine, ignorBounds=True)

        # plot of diameter detection left/right
        self._leftFitScatter = pg.ScatterPlotItem(
            size=3, brush=pg.mkBrush(50, 255, 50, 120)
        )
        _xFake = []  # self.ba.sweepX
        _yFake = []  # [200 for x in self.ba.sweepX]
        self._leftFitScatter.setData(_xFake, _yFake)
        self.kymographPlot.addItem(self._leftFitScatter, ignorBounds=True)

        self._rightFitScatter = pg.ScatterPlotItem(
            size=3, brush=pg.mkBrush(255, 50, 50, 120)
        )
        _xFake = []  # self.ba.sweepX
        _yFake = []  # [350 for x in self.ba.sweepX]
        self._rightFitScatter.setData(_xFake, _yFake)
        self.kymographPlot.addItem(self._rightFitScatter, ignorBounds=True)

        # roi rect
        # kymographRect = self.ba.kymAnalysis.getRoiRect()
        # pos, size = kymographRect.getPosAndSize()

        # logger.info(f'kymographRect is {kymographRect}')
        # logger.info(f'  building lineRoi with pos:{pos} size:{size}')

        movable = False
        self.myLineRoi = pg.ROI(
            pos=pos, size=size,
            parent=self.myImageItem,
            movable=movable
        )
        # self.myLineRoi.addScaleHandle((0,0), (1,1), name='topleft')  # at origin
        self.myLineRoi.addScaleHandle(
            # (0.5, 0), (0.5, 1), name="top center"
            (0.5, 0), (0.5, 1), name="bottom center"
        )  # top center
        self.myLineRoi.addScaleHandle(
            # (0.5, 1), (0.5, 0), name="bottom center"
            (0.5, 1), (0.5, 0), name="top center"
        )  # bottom center
        self.myLineRoi.sigRegionChangeFinished.connect(self.kymographChanged)

        self.myVBoxLayout.addWidget(self.view)

        # slider to step through "Line Profile"
        self._lineProfileSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self._lineProfileSlider.setMinimum(0)
        # TODO: cludge, fix
        _numLineScans = 0
        # if self.ba is not None:
        #     _numLineScans = len(self.ba.fileLoader.sweepX) - 1
        self._lineProfileSlider.setMaximum(_numLineScans)
        self._lineProfileSlider.valueChanged.connect(self._on_line_slider_changed)
        self.myVBoxLayout.addWidget(self._lineProfileSlider)

    def showLineSlider(self, visible):
        """Toggle line slider and vertical line (on image) on/off."""
        self._lineProfileSlider.setVisible(visible)

    def showSliceLine(self, visible : bool):
        self._sliceLine.setVisible(visible)

    def incDecLineSlider(self, incDec : int):
        """Increment or decriment the line slider.
        
        Used by main widget for keyboard left/right
        """
        _numLineScans = len(self.ba.fileLoader.sweepX)
        
        value = self._lineProfileSlider.value()
        value += incDec
        if value < 0:
            value = 0
        elif value > _numLineScans-1:
            value = _numLineScans - 1
        self._lineProfileSlider.setValue(value)
        self._on_line_slider_changed(value)

    def _on_line_slider_changed(self, lineNumber: int):
        """Respond to user dragging the line slider.

        Args:
            lineNumber: Int line number, needs to be converted to 'seconds'
        """

        lineSeconds = lineNumber * self.ba.fileLoader.tifHeader["secondsPerLine"]

        # set the vertical line
        self._sliceLine.setValue(lineSeconds)

        self.signalLineSliderChanged.emit(lineNumber)

    def _onContrastSliderChanged(self, val: int, name: str):
        """Respond to either the min or max contrast slider.

        Args:
            val: new value
            name: Name of slider, in ('min', 'max')
        """
        # logger.info(f"{name} {val}")
        if name == "min":
            self._minContrast = val
            self.minContrastSpinBox.setValue(val)
        elif name == "max":
            self._maxContrast = val
            self.maxContrastSpinBox.setValue(val)
        
        self._replot()

    def guessContrastEnhance(self):
        """Gues a good min/max contrast based on range of intensities.
        """
        tifData = self.ba.fileLoader.tifData
        
        min = tifData.min()
        max = tifData.max()
        
        range = max - min

        tenPercent = range * 0.25

        #min += tenPercent
        max -= tenPercent
        
        min = math.floor(min)
        max = math.ceil(max)
        
        self._minContrast = min
        self._maxContrast = max
        
        logger.info(f'guessed min:{min} max:{max}')

    def getContrastEnhance(self, theMin=None, theMax=None):
        """Get contrast enhanced image."""
        # return self.ba.fileLoader.tifData
    
        try:
            bitDepth = self.ba.fileLoader.tifHeader['bitDepth']
        except (KeyError) as e:
            logger.error('did not find bitdepth, defaulting to 8 bit.')
            bitDepth = 8
        
        try:
            dType = self.ba.fileLoader.tifHeader['dtype']
        except (KeyError) as e:
            logger.error('did not find dtype, defaulting to np.uint8.')
            dType = np.uint8

        if theMin is None:
            theMin = self._minContrast
        if theMax is None:
            theMax = self._maxContrast

        lut = np.arange(2**bitDepth, dtype=dType)
        lut = self._getContrastedImage(lut, theMin, theMax, bitDepth)  # get a copy of the image

        # logger.info('')
        # print('  theMin:', theMin)
        # print('  theMax:', theMax)
        # print('  lut:', lut.shape)
        # print('  self.ba.fileLoader.tifData:', self.ba.fileLoader.tifData.shape)
        # IndexError: index 287 is out of bounds for axis 0 with size 256
        # sys.exit(1)

        theRet = np.take(lut, self.ba.fileLoader.tifData)
        return theRet

    def _getContrastedImage(self, image, display_min, display_max, bitDepth):
        # copied from Bi Rico
        # Here I set copy=True in order to ensure the original image is not
        # modified. If you don't mind modifying the original image, you can
        # set copy=False or skip this step.
        
        # bitDepth = 8

        if bitDepth == 8:
            image = np.array(image, dtype=np.uint8, copy=True)
        else:
            image = np.array(image, dtype=np.uint16, copy=True)
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

        myTif = self.getContrastEnhance()

        logger.info(
            f"    startSec:{startSec} stopSec:{stopSec} myTif.shape:{myTif.shape}"
        )  # like (519, 10000)

        imageRect = self.ba.kymAnalysis.getImageRect(asList=True)
        # imageRect[2] = myTif.shape[1]
        logger.info(f'    imageRect:{imageRect}')  # [0,0,5,113]

        axisOrder = "row-major"
        self.myImageItem.setImage(myTif,
                                    axisOrder=axisOrder,
                                    rect=imageRect
                                    )

        # w = imageRect[2]
        # h = imageRect[3]
        # w = 0.001
        # h = 0.3
        # tr = QtGui.QTransform()  # prepare ImageItem transformation:
        # tr.scale(w, h)       # scale horizontal and vertical axes
        # # #tr.translate(-1.5, -1.5) # move 3x3 image to locate center at axis origin
        # # tr.translate(0,0)
        # self.myImageItem.setTransform(tr)

        if startSec is not None and stopSec is not None:
            padding = 0
            self.kymographPlot.setXRange(
                startSec, stopSec, padding=padding
            )  # row major is different

        # color bar with contrast !!!
        if myTif.dtype == np.dtype("uint8"):
            bitDepth = 8
        elif myTif.dtype == np.dtype("uint16"):
            bitDepth = 16
        else:
            bitDepth = 16
            logger.error(f"Did not recognize tif dtype: {myTif.dtype}")

        # cm = pg.colormap.get(
        #     "Greens_r", source="matplotlib"
        # )  # prepare a linear color map
        # # values = (0, 2**bitDepth)
        # # values = (0, maxTif)
        # values = (0, 2**12)
        # limits = (0, 2**12)
        # # logger.info(f'color bar bit depth is {bitDepth} with values in {values}')
        # doColorBar = False
        # if doColorBar:
        #     if self.myColorBarItem == None:
        #         self.myColorBarItem = pg.ColorBarItem(
        #             values=values,
        #             limits=limits,
        #             interactive=True,
        #             label="",
        #             cmap=cm,
        #             orientation="horizontal",
        #         )
        #     # Have ColorBarItem control colors of img and appear in 'plot':
        #     self.myColorBarItem.setImageItem(
        #         self.myImageItem, insert_in=self.kymographPlot
        #     )
        #     self.myColorBarItem.setLevels(values=values)

        # kymographRect is in scaled units, we need plot units
        kymographRect = self.ba.kymAnalysis.getRoiRect()
        #kymographRect = self.ba.kymAnalysis.getImageRect_no_scale()
        logger.info(f'    getRoiRect() kymographRect is {kymographRect}')
        pos, size = kymographRect.getPosAndSize()
        
        # logger.info(f'    myLineRoi pos:{pos} size:{size}')
        #size = (5000, 250)
        # size = (myTif.shape[1], myTif.shape[0])

        # pos = QtCore.QPointF(pos[0], pos[1])
        # size = QtCore.QPointF(size[0], size[1])
        # pos = self.myImageItem.mapFromScene(pos)
        # size = self.myImageItem.mapFromScene(size)

        # logger.info(f'    myLineRoi pg.ROI has pos:{pos} size:{size}')  # pos:(0, 77) size:(11, -285)
        # pos:(0, 51) size:(11, 365)

        # If finish is False, then sigRegionChangeFinished will not be emitted
        _finish = False
        self.myLineRoi.setPos(pos, finish=_finish)
        self.myLineRoi.setSize(size, finish=_finish)

        #
        # background kymograph ROI
        if 0:
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

        # update min/max displayed to user
        #self._updateRoiMinMax(kymographRect)
        # self._updateBackgroundRoiMinMax(backgroundRect)

    def updateLeftRightFit(self, yLeft, yRight, visible=True):
        """
        
        Parameters
        ----------
        yLeft : List[int]
        yRight : List[int]
        """
        self._leftFitScatter.setVisible(visible)
        self._rightFitScatter.setVisible(visible)

        if visible:
            x = self.ba.fileLoader.sweepX

            umPerPixel = self.ba.fileLoader.tifHeader['umPerPixel']
            
            yLeft = np.array(yLeft, dtype=np.float64)
            yLeft *= umPerPixel

            yRight = np.array(yRight, dtype=np.float64)
            yRight *= umPerPixel
            
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
        left = theRect.getLeft()
        top = theRect.getTop()
        right = theRect.getRight()
        bottom = theRect.getBottom()

        logger.info(f"left:{left} top:{top} right:{right} bottom:{bottom}")

        myTif = self.ba.fileLoader.tifData
        tifClip = myTif[bottom:top, left:right]

        roiMin = np.nanmin(tifClip)
        roiMax = np.nanmax(tifClip)

        self.roiMinLabel.setText(f"ROI Min:{roiMin}")
        self.roiMaxLabel.setText(f"ROI Max:{roiMax}")

    def kymographChanged(self, event):
        """User finished dragging the ROI

        Args:
            event :pyqtgraph.graphicsItems.ROI.ROI

        Info:
            theRect2:[0, 383, 5000, 17]
        """
        # logger.info("")

        # logger.info(f'  parentBounds:{event.parentBounds()}')
        # logger.info(f'  event.pos:{event.pos()}')
        # logger.info(f'  event.size:{event.size()}')

        l2 = event.pos().x()
        b2 = event.pos().y()
        t2 = b2 + event.size().y()
        r2 = l2 + event.size().x()
        
        l2 = math.floor(l2)
        t2 = math.floor(t2)
        r2 = math.floor(r2)
        b2 = math.floor(b2)

        if b2<0:
            b2 = 0
        # if t2 > self.

        theRect2 = [l2, t2, r2, b2]
        logger.info(f'  theRect2:{theRect2}')

        self.ba.kymAnalysis.setRoiRect(theRect2)
        
        logger.info(f'  -->> emit signalKymographRoiChanged theRect:{theRect2}')
        self.signalKymographRoiChanged.emit(theRect2)  # underlying _abf has new rect

        return
    
        _kymographRect = self.ba.kymAnalysis.getRoiRect()  # (l, t, r, b)

        left = _kymographRect.getLeft()  # _kymographRect[0]
        top = _kymographRect.getTop()  # _kymographRect[1]
        right = _kymographRect.getRight()  # _kymographRect[2]
        bottom = _kymographRect.getBottom()  # _kymographRect[3]

        logger.info(f'  original _kymographRect:{_kymographRect}')

        handles = event.getSceneHandlePositions()
        for _idx, handle in enumerate(handles):
            logger.info(f"{_idx} handle: {handle}")
            if handle[0] is not None:

                # units are in image pixels !!!
                # imagePos = self.myImageItem.mapFromScene(handle[1])
                # x = imagePos.x()
                # y = imagePos.y()
                
                x = handle[1].x()
                y = handle[1].y()
                
                if handle[0] == "top center":
                    bottom = y
                elif handle[0] == "bottom center":
                    top = y

        if left < 0:
            left = 0
        if bottom < 0:
            bottom = 0

        # force left and right
        # _kymographRect = self.ba.kymAnalysis.getRoiRect()  # (l, t, r, b)
        # left = _kymographRect.getLeft()
        # right = _kymographRect.getRight()

        logger.info(f"  left:{left} top:{top} right:{right} bottom:{bottom}")

        #  cludge
        # if bottom > top:
        #     logger.warning(f'fixing bad top/bottom top:{top} bottom:{bottom}')
        #     tmp = top
        #     top = bottom
        #     bottom = tmp

        left = math.floor(left)
        top = math.floor(top)
        right = math.floor(right)
        bottom = math.floor(bottom)

        theRect = [left, top, right, bottom]

        logger.info(f'  new roi rect is theRect{theRect}')

        #self._updateRoiMinMax(theRect)

        # TODO: detection widget needs a slot to (i) analyze and then replot
        # self.ba._updateTifRoi(theRect)
        # self._replot(startSec=None, stopSec=None, userUpdate=True)
        # self.signalDetect.emit(self.ba)  # underlying _abf has new rect
        self.ba.kymAnalysis.setRoiRect(theRect)
        
        logger.info(f'  -->> emit signalKymographRoiChanged theRect:{theRect}')
        self.signalKymographRoiChanged.emit(theRect)  # underlying _abf has new rect

    def slot_switchFile(self, ba=None, startSec=None, stopSec=None):
        if ba is not None and ba.fileLoader.isKymograph():
            self.ba = ba

            self.guessContrastEnhance()

            self._replot(startSec=startSec, stopSec=stopSec)

            self._resetZoom()

            # update line scan slider
            _numLineScans = len(self.ba.fileLoader.sweepX) - 1
            self._lineProfileSlider.setValue(0)
            self._lineProfileSlider.setMaximum(_numLineScans)

            # update top control bar
            self._refreshControlBarWidget()

            theRect = self.ba.kymAnalysis.getRoiRect()
            logger.info(f'-->> emit signalKymographRoiChanged theRect:{theRect}')
            self.signalKymographRoiChanged.emit(theRect)  # underlying _abf has new rect

    def hoverEvent(self, event):
        if event.isExit():
            return

        if self.ba is None:
            return
        
        xPos = event.pos().x()
        yPos = event.pos().y()

        xPos = int(xPos)
        yPos = int(yPos)

        myTif = self.ba.fileLoader.tifData
        try:
            intensity = myTif[yPos, xPos]  # flipped
        except (IndexError) as e:
            intensity = 'None'
        # logger.info(f'x:{xPos} y:{yPos} intensity:{intensity}')

        self.tifCursorLabel.setText(f"Cursor:{intensity}")
        self.tifCursorLabel.update()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    if 1:
        path = "/media/cudmore/data/rabbit-ca-transient/jan-12-2022/Control/220110n_0003.tif.frames/220110n_0003.tif"
        path = "/Users/cudmore/data/rosie/test-data/filter median 1 C2-0-255 Cell 2 CTRL  2_5_21 female wt old.tif"

        path = '/Users/cudmore/Sites/SanPy/data/kymograph/rosie-kymograph.tif'

        path = 'data/kymograph/rosie-kymograph.tif'

        ba = sanpy.bAnalysis(path)
        print(ba)

        kw = kymographWidget(ba)
        kw.show()

    # test dialog
    if 0:
        mcd = myScaleDialog()
        mcd.show()
        if mcd.exec():
            scaleDict = mcd.getResults()
            print(scaleDict)
        else:
            print('user did not hit "ok"')

    sys.exit(app.exec_())
