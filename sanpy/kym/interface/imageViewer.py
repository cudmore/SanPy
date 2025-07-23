from functools import partial

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSlider,
    QCheckBox,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import pyqtgraph.exporters

from sanpy.kym.kymUtils import getAutoContrast

from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)

from enum import Enum, auto


class ImageDisplayMode(Enum):
    """Display modes for image data."""

    RAW = 'Raw'  # Raw fluorescence values
    F_F0 = 'f/f0'  # F/F0 normalized values
    DF_F0 = 'df/f0'  # (F-F0)/F0 normalized values


class ImageViewer(QtWidgets.QWidget):
    """General perpose 2D image viewer."""

    def __init__(
        self,
        imgData: np.ndarray,
        secondsPerLine: float = 1,
        umPerPixel: float = 1,
        f0=1,
    ):
        super().__init__(None)

        self._imgData = imgData
        self._secondsPerLine = secondsPerLine
        self._umPerPixel = umPerPixel
        self._f0 = f0

        self._imgDataDisplay = imgData
        # the image data displayed on the kymograph

        self._minContrast = 0
        self._maxContrast = self.imgDisplayMax

        self._buildUI()

    @property
    def imgData(self) -> np.ndarray:
        """Get image data for one image channel."""
        return self._imgData

    @property
    def imgDisplayMax(self):
        return np.max(self._imgDataDisplay)

    def getImageRect(self):
        """Get image rect with (x,y) scale.

        Used to display kym ImageItem
        """
        left = 0
        top = self._imgDataDisplay.shape[0] * self._umPerPixel
        right = self._imgDataDisplay.shape[1] * self._secondsPerLine
        bottom = 0

        width = right - left
        height = top - bottom

        return left, bottom, width, height  # x, y, w, h

    def _on_button_click(self, name: str):
        logger.info(f'name:{name}')

        if name == 'Auto':
            # auto contrast
            self.setAutoContrast()

        # elif name == 'Set Scale':
        #     self._setScaleDialog()

        else:
            logger.warning(f'did not understand button "{name}"')

    def setAutoContrast(self):
        _min, _max = getAutoContrast(
            self._imgDataDisplay
        )  # new 20240925, should mimic ImageJ

        logger.info(f'_min:{_min} _max:{_max}')

        self._minContrast = _min
        self._maxContrast = _max

        # update gui
        self.minContrastSlider.setValue(self._minContrast)
        self.maxContrastSlider.setValue(self._maxContrast)

    def setColorMap(self, colorMap: str):
        """
        _colorList = ['Green', 'Red', 'Blue', 'Grey', 'Grey Invert', 'viridis', 'plasma', 'inferno']
        """

        # cm is type pg.ColorMap
        if colorMap == 'Green':
            cm = pg.colormap.get('Greens_r', source='matplotlib')
        elif colorMap == 'Red':
            cm = pg.colormap.get('Reds_r', source='matplotlib')
        elif colorMap == 'Blue':
            cm = pg.colormap.get('Blues_r', source='matplotlib')
        elif colorMap == 'Grey':
            cm = pg.colormap.get('Greys_r', source='matplotlib')
        elif colorMap == 'Grey Invert':
            cm = pg.colormap.get('Greys', source='matplotlib')
        elif colorMap == 'viridis':
            cm = pg.colormap.get('viridis', source='matplotlib')
        elif colorMap == 'plasma':
            cm = pg.colormap.get('plasma', source='matplotlib')
        elif colorMap == 'inferno':
            cm = pg.colormap.get('inferno', source='matplotlib')
        else:
            logger.error(f'did not understand color map: {colorMap}')
            return

        # logger.info(f'{colorMap} cm:{cm}')

        # self.aColorBar.setColorMap(cm)
        self.myImageItem.setColorMap(cm)

    def _hoverEvent(self, event):
        """Hover on image -> update status in QMainWindow"""
        if event.isExit():
            return

        xPos = event.pos().x()
        yPos = event.pos().y()

        xPos = int(xPos)
        yPos = int(yPos)

        try:
            intensity = self._imgDataDisplay[yPos, xPos]  # flipped
        except IndexError as e:
            intensity = 'None'

        intensity = f'{xPos} {yPos} intensity:{intensity}'

        # logger.warning(f'todo: set on hover "{intensity}"')
        # self.mySetStatusBar(intensity)

    def _toggleGui(self, item: str, visible: bool):
        if item == 'contrastSliders':
            self._contrastSliders.setVisible(visible)
        else:
            logger.warning(f'did not understand item: {item}')

    def _buildContrastSliders(self) -> QtWidgets.QWidget:
        # Main container with horizontal layout
        mainLayout = QtWidgets.QHBoxLayout()
        mainLayout.setSpacing(10)
        mainLayout.setContentsMargins(5, 5, 5, 5)

        # Left column for color and auto controls
        leftColumn = QtWidgets.QVBoxLayout()
        leftColumn.setAlignment(QtCore.Qt.AlignTop)
        leftColumn.setSpacing(5)

        # Color selection combo
        _colorList = [
            'Red',
            'Green',
            'Blue',
            'Grey',
            'Grey Invert',
            'viridis',
            'plasma',
            'inferno',
        ]
        colorComboBox = QtWidgets.QComboBox()
        colorComboBox.addItems(_colorList)
        colorComboBox.setCurrentIndex(0)
        colorComboBox.currentTextChanged.connect(partial(self.setColorMap))
        leftColumn.addWidget(colorComboBox)

        # Auto contrast button
        autoButton = QtWidgets.QPushButton('Auto')
        autoButton.clicked.connect(partial(self._on_button_click, 'Auto'))
        leftColumn.addWidget(autoButton)

        # Right column for contrast controls and scale info
        rightColumn = QtWidgets.QVBoxLayout()
        rightColumn.setAlignment(QtCore.Qt.AlignTop)
        rightColumn.setSpacing(5)

        # Min contrast controls
        minContrastLayout = QtWidgets.QHBoxLayout()
        minContrastLayout.setSpacing(5)
        minContrastLayout.addWidget(QtWidgets.QLabel("Min"))

        self.minContrastSpinBox = QtWidgets.QSpinBox()
        self.minContrastSpinBox.setEnabled(False)
        self.minContrastSpinBox.setMinimum(0)
        self.minContrastSpinBox.setMaximum(self.imgDisplayMax)
        minContrastLayout.addWidget(self.minContrastSpinBox)

        self.minContrastSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.minContrastSlider.setMinimum(0)
        self.minContrastSlider.setMaximum(self.imgDisplayMax)
        self.minContrastSlider.setValue(0)
        self.minContrastSlider.valueChanged.connect(
            lambda val, name="minSlider": self._onContrastSliderChanged(val, name)
        )
        minContrastLayout.addWidget(self.minContrastSlider)

        self.tifMinLabel = QtWidgets.QLabel(f'Img Min:{np.min(self._imgDataDisplay)}')
        minContrastLayout.addWidget(self.tifMinLabel)
        rightColumn.addLayout(minContrastLayout)

        # Max contrast controls
        maxContrastLayout = QtWidgets.QHBoxLayout()
        maxContrastLayout.setSpacing(5)
        maxContrastLayout.addWidget(QtWidgets.QLabel("Max"))

        self.maxContrastSpinBox = QtWidgets.QSpinBox()
        self.maxContrastSpinBox.setEnabled(False)
        self.maxContrastSpinBox.setMinimum(0)
        self.maxContrastSpinBox.setMaximum(self.imgDisplayMax)
        maxContrastLayout.addWidget(self.maxContrastSpinBox)

        self.maxContrastSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.maxContrastSlider.setMinimum(0)
        self.maxContrastSlider.setMaximum(self.imgDisplayMax)
        self.maxContrastSlider.setValue(self.imgDisplayMax)
        self.maxContrastSlider.valueChanged.connect(
            lambda val, name="maxSlider": self._onContrastSliderChanged(val, name)
        )
        maxContrastLayout.addWidget(self.maxContrastSlider)

        self.tifMaxLabel = QtWidgets.QLabel(f'Max:{np.max(self._imgDataDisplay)}')
        maxContrastLayout.addWidget(self.tifMaxLabel)
        rightColumn.addLayout(maxContrastLayout)

        # Scale info row
        scaleLayout = QtWidgets.QHBoxLayout()
        scaleLayout.setAlignment(QtCore.Qt.AlignRight)
        scaleLayout.setSpacing(10)

        self._imgBitDepth = QtWidgets.QLabel(f'dtype:{self._imgDataDisplay.dtype}')
        self._xScaleLabel = QtWidgets.QLabel(f'ms/line:{self._secondsPerLine*1000}')
        self._yScaleLabel = QtWidgets.QLabel(f'um/pixel:{self._umPerPixel}')

        scaleLayout.addWidget(self._imgBitDepth)
        scaleLayout.addWidget(self._xScaleLabel)
        scaleLayout.addWidget(self._yScaleLabel)
        rightColumn.addLayout(scaleLayout)

        # Add columns to main layout
        # mainLayout.addLayout(leftColumn, stretch=1)
        mainLayout.addLayout(leftColumn)
        mainLayout.addLayout(rightColumn, stretch=4)

        # Create and return widget
        widget = QtWidgets.QWidget()
        widget.setLayout(mainLayout)
        return widget

    def _buildUI(self):
        vLayout = QtWidgets.QVBoxLayout()
        self.setLayout(vLayout)

        self._contrastSliders = self._buildContrastSliders()
        self._contrastSliders.setVisible(False)  # Set initial visibility
        vLayout.addWidget(self._contrastSliders)

        # Display mode selection and f0 control
        displayModeLayout = QtWidgets.QHBoxLayout()
        displayModeLayout.setAlignment(QtCore.Qt.AlignLeft)
        displayModeLayout.setSpacing(10)

        # Add f0 spinbox
        f0Label = QtWidgets.QLabel("f0:")
        self.f0SpinBox = QtWidgets.QDoubleSpinBox()
        self.f0SpinBox.setMinimum(0.0001)  # Avoid division by zero
        self.f0SpinBox.setMaximum(99999)
        self.f0SpinBox.setValue(self._f0)
        self.f0SpinBox.setKeyboardTracking(False)
        self.f0SpinBox.valueChanged.connect(self._onF0Changed)
        displayModeLayout.addWidget(f0Label)
        displayModeLayout.addWidget(self.f0SpinBox)

        displayModeLabel = QtWidgets.QLabel("Display Mode:")
        self.displayModeCombo = QtWidgets.QComboBox()
        for mode in ImageDisplayMode:
            self.displayModeCombo.addItem(mode.value)
        self.displayModeCombo.setCurrentText(ImageDisplayMode.RAW.name)
        self.displayModeCombo.currentTextChanged.connect(self._onDisplayModeChanged)

        displayModeLayout.addWidget(displayModeLabel)
        displayModeLayout.addWidget(self.displayModeCombo)
        vLayout.addLayout(displayModeLayout)

        # kymograph
        self.view = pg.GraphicsLayoutWidget()
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)  # Enable context menu
        vLayout.addWidget(self.view)

        # pyqtgraph.graphicsItems.PlotItem
        row = 0
        colSpan = 1
        rowSpan = 1
        self.kymographPlot = self.view.addPlot(
            row=row, col=0, rowSpan=rowSpan, colSpan=colSpan
        )
        """A PlotItem"""

        # self.kymographPlot.setLabel("left", "Pixels (um)", units="")
        # self.kymographPlot.setLabel("bottom", "Time (s)", units="")

        self.toggleAxis(False)
        # self.kymographPlot.hideAxis('bottom')
        # self.kymographPlot.hideAxis('left')

        self.kymographPlot.setDefaultPadding(0)
        self.kymographPlot.enableAutoRange()
        self.kymographPlot.setMouseEnabled(x=True, y=False)
        self.kymographPlot.hideButtons()  # hide the little 'A' button to rescale axis
        # self.kymographPlot.setMenuEnabled(False)  # turn off right-click menu

        # switching to PyMapManager style contrast with setLevels()
        imageRect = self.getImageRect()  # l,b,h,w
        self.myImageItem = pg.ImageItem(
            self._imgDataDisplay, axisOrder="row-major", rect=imageRect
        )  # need transpose for row-major

        self.setColorMap(
            'Green'
        )  # sets self.aColorBar which sets children (self.myImageItem)

        self.kymographPlot.addItem(self.myImageItem, ignorBounds=True)

        # redirect hover to self (to display intensity
        self.myImageItem.hoverEvent = self._hoverEvent

    def _onF0Changed(self, value):
        """Handle changes to f0 spinbox value.

        Parameters
        ----------
        value : float
            New f0 value
        """
        self._f0 = value

        logger.info(f'f0:{self._f0}')

        # refresh displayed image based on current display mode
        currentMode = self.displayModeCombo.currentText()
        if currentMode == ImageDisplayMode.F_F0.value:
            self._imgDataDisplay = self._imgData / self._f0
        elif currentMode == ImageDisplayMode.DF_F0.value:
            self._imgDataDisplay = (self._imgData - self._f0) / self._f0
        else:
            # Raw mode - no f0 normalization needed
            self._imgDataDisplay = self._imgData

        # update image
        self.myImageItem.setImage(self._imgDataDisplay, autoRange=True)

    def exportImage(self):
        """Export the current image to a file."""
        filter = ["*." + str(f) for f in QtGui.QImageWriter.supportedImageFormats()]
        preferred = ['*.png', '*.tif', '*.jpg']

        logger.info(f'filter:{filter}')
        logger.info(f'preferred:{preferred}')

        exporter = pg.exporters.ImageExporter(self.myImageItem)
        # exporter.parameters()['width'] = 100
        # exporter.export('image.png')
        saveFile = '/Users/cudmore/Desktop/export.png'
        logger.info(saveFile)
        exporter.export(saveFile)

    def toggleAxis(self, visible):
        if visible:
            self.kymographPlot.showAxis('bottom')
            self.kymographPlot.showAxis('left')
        else:
            self.kymographPlot.hideAxis('bottom')
            self.kymographPlot.hideAxis('left')

    def _resetZoom(self, doEmit=True):
        self.kymographPlot.autoRange(item=self.myImageItem)

    def keyReleaseEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Shift:
            self.kymographPlot.setMouseEnabled(x=True, y=False)

    def keyPressEvent(self, event):
        """Respond to user key press.

        Parameters
        ----------
        event : PyQt5.QtGui.QKeyEvent
        """
        logger.info('')
        key = event.key()
        text = event.text()

        isShift = event.modifiers() == QtCore.Qt.ShiftModifier
        isAlt = event.modifiers() == QtCore.Qt.AltModifier
        isCtrl = event.modifiers() == QtCore.Qt.ControlModifier

        logger.info(
            f'key:{key} text:{text} isCtrl:{isCtrl} isAlt:{isAlt} isShift:{isShift}'
        )

        if key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
            self._resetZoom()
        elif isShift:
            # switch it to y-zoom
            self.kymographPlot.setMouseEnabled(x=False, y=True)

    def _onDisplayModeChanged(self, mode):
        """Handle changes to display mode.

        Parameters
        ----------
        mode : ImageDisplayMode
            The new display mode to use
        """

        if mode == ImageDisplayMode.RAW.value:
            displayData = self.imgData
        elif mode == ImageDisplayMode.F_F0.value:
            displayData = self.imgData / self._f0
        elif mode == ImageDisplayMode.DF_F0.value:
            displayData = (self.imgData - self._f0) / self._f0
        else:
            logger.warning(f'did not understand display mode: {mode}')
            return

        displayData = displayData.astype(np.int16)
        self._imgDataDisplay = displayData

        imageRect = self.getImageRect()
        self.myImageItem.setImage(displayData, rect=imageRect)

        # Reset contrast to auto levels for new display mode
        minVal, maxVal = getAutoContrast(displayData)
        self._minContrast = minVal
        self._maxContrast = maxVal
        self.myImageItem.setLevels([minVal, maxVal])

        # Update UI controls
        self.minContrastSpinBox.setValue(minVal)
        self.maxContrastSpinBox.setValue(maxVal)
        self.minContrastSlider.setValue(minVal)
        self.maxContrastSlider.setValue(maxVal)

    def _onContrastSliderChanged(self, value, name):
        # logger.info(f'name:{name} value:{value}')

        if name == "minSlider":
            self._minContrast = value
            self.minContrastSpinBox.setValue(value)
        elif name == "maxSlider":
            self._maxContrast = value
            self.maxContrastSpinBox.setValue(value)

        _levels = [self._minContrast, self._maxContrast]
        self.myImageItem.setLevels(_levels, update=True)
        # self.aColorBar.setLevels(_levels)

    def contextMenuEvent(self, event):
        """Handle right-click context menu events."""
        menu = QtWidgets.QMenu(self)

        # Create toggle action for contrast sliders
        showContrastAction = menu.addAction("Show Contrast Controls")
        showContrastAction.setCheckable(True)
        showContrastAction.setChecked(self._contrastSliders.isVisible())
        showContrastAction.triggered.connect(
            lambda checked: self._contrastSliders.setVisible(checked)
        )

        # Create toggle action for axis visibility
        showAxisAction = menu.addAction("Show Axis")
        showAxisAction.setCheckable(True)
        showAxisAction.setChecked(self.kymographPlot.getAxis("bottom").isVisible())
        showAxisAction.triggered.connect(lambda checked: self.toggleAxis(checked))
        # Add export image action
        exportAction = menu.addAction("Export Image...")
        exportAction.triggered.connect(self.exportImage)

        # Show the menu at cursor position
        menu.exec_(event.globalPos())
