from functools import partial
from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QCheckBox,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QImage

from PyQt5 import QtGui, QtCore, QtWidgets
import pyqtgraph as pg

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, KymRoi
from sanpy.kym.kymRoiDetection import KymRoiDetection
from sanpy.kym.kymRoi import PeakDetectionTypes

from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


class SetScaleDialog(QtWidgets.QDialog):
    """Dialog to set x/y kymograph scale.

    If set, analysis has to be redone.
    """

    def __init__(self, secondsPerLine: float, umPerPixel: float, parent=None):
        # logger.info(f'secondsPerLine:{secondsPerLine} umPerPixel:{umPerPixel}')

        super().__init__(parent)

        self.setWindowTitle("Set Kymograph Scale")

        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        hLayout = QtWidgets.QHBoxLayout()

        xScaleLabel = QtWidgets.QLabel("ms/Line")
        self.xScale = QtWidgets.QDoubleSpinBox()
        self.xScale.setDecimals(5)
        self.xScale.setSingleStep(0.01)
        msPerLine = secondsPerLine * 1000
        self.xScale.setValue(msPerLine)

        yScaleLabel = QtWidgets.QLabel("Microns/Pixel")
        self.yScale = QtWidgets.QDoubleSpinBox()
        self.yScale.setDecimals(3)
        self.yScale.setSingleStep(0.01)
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
        xScale_ms_per_Line = self.xScale.value()  # units are ms/line
        yScale = self.yScale.value()
        retDict = {
            "secondsPerLine": xScale_ms_per_Line / 1000,
            "umPerPixel": yScale,
        }
        return retDict


class KymRoiImageWidget(QtWidgets.QWidget):
    """Display an image kymograph for one kymRoiAnalysis."""

    # signalSetChannel = QtCore.pyqtSignal(object)  # (channel)
    signalSelectRoi = QtCore.pyqtSignal(
        object, object
    )  # (channel, roi label), can be None
    signalRoiChanged = QtCore.pyqtSignal(object)  # (roi label)
    signalSetLineProfile = QtCore.pyqtSignal(object)  # (int), line scan index

    def __init__(
        self, kymRoiAnalysis: KymRoiAnalysis, detectThisTrace: str, kymRoiWidget=None
    ):
        super().__init__(None)

        self._kymRoiAnalysis = kymRoiAnalysis
        self._detectThisTrace = detectThisTrace
        self._kymRoiWidget = kymRoiWidget

        self._currentChannel = 0

        self.selectedRoi: Optional[str] = None
        """The selected roi label str."""

        self._minContrast = 0
        self._maxContrast = 0

        self.roiList = {}
        """Keys are str label, values are pg.ROI"""

        self.roiLabelList = {}
        """Keys are str roi label, value are QLabel."""

        self.imgData = self._kymRoiAnalysis.getImageChannel(self._currentChannel)
        # this display the entire kym image, there is no f0, each roi has an f0
        # if self._detectThisTrace == 'f_f0':
        #     self.imgData = self.imgData / self.imgData.mean()
        # elif self._detectThisTrace == 'df_f0':
        #     self.imgData = (self.imgData - self.imgData.mean()) / self.imgData.mean()

        self._buildUI()

        self.switchChannel(self._currentChannel + 1)

        # select the first kymRoi
        # if len(self.roiList) > 0:
        #     self.selectRoiFromLabel(list(self.roiList.keys())[0])

    # @property
    # def imgData(self) -> np.ndarray:
    #     """Get image data for one image channel.
    #     """
    #     return self._kymRoiAnalysis.getImageChannel(self._currentChannel)

    def onUserAddRoi(self, ltrbRoi=None):
        """Add to backend with default ltrb"""

        selectedRoiLabel = self.getSelectedRoiLabel()

        # get the current view to make roi visible
        # ltrbRoi = [100, 200, 500, 0]

        # _rect = self.myImageItem.viewRect()
        # logger.warning(f'nope _rect:{_rect}')
        # _rect = self.kymographPlot.viewRect()
        # logger.warning(f'nope kymographPlot (PlotItem) _rect:{_rect}')

        # _range is in PHYSICAL UNITS [ [xMin, xMax], [yMin, yMax]]
        _range = self.kymographPlot.viewRange()
        # logger.warning(f'kymographPlot (PlotItem) _range:{_range}')

        if ltrbRoi is None:
            _left = _range[0][0] / self._kymRoiAnalysis.secondsPerLine
            _right = _range[0][1] / self._kymRoiAnalysis.secondsPerLine
            _bottom = _range[1][0] / self._kymRoiAnalysis.umPerPixel
            _top = _range[1][1] / self._kymRoiAnalysis.umPerPixel
            _view_ltrb = [_left, _top, _right, _bottom]
            _view_ltrb = [int(x) for x in _view_ltrb]
            ltrbRoi = _view_ltrb

        logger.info(f'adding roi ltrbRoi:{ltrbRoi}')

        # add to backend
        newKymRoi = self._kymRoiAnalysis.addROI(ltrbRoi, reuseRoiLabel=selectedRoiLabel)

        # add pg.ROI to GUI
        roi = self._addRoi(newKymRoi)

        # select the new roi
        self._selectRoi(roi)

        self.mySetStatusBar(f'Added ROI {newKymRoi}')

        return roi

    def onUserDeleteRoi(self, roiLabel: Optional[str] = None):
        """Delete the selected pg.ROI from backend and gui."""
        if roiLabel is None and self.selectedRoi is None:
            logger.warning('no selected roi')
            return

        if roiLabel is not None:
            # delete the selected roi
            self.selectedRoi = roiLabel

        # ask the user if they want to delete the roi
        from sanpy.interface.bDialog import yesNoCancelDialog
        retval = yesNoCancelDialog(message=f'Delete ROI "{self.selectedRoi}"?',
                                #    informativeText=f'This may cause problems if you are comparing ROIs across conditions.'
                                   )
        if retval in [QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Cancel]:
            logger.info(f'user chose to not delete roi {roiLabel}')
            return

        # delete from backend
        self._kymRoiAnalysis.deleteRoi(self.selectedRoi)

        # delete from gui
        self._deleteRoi(self.selectedRoi)

        # after delete, no selection
        self.selectedRoi = None

        self.signalSelectRoi.emit(self._currentChannel, None)

    def _deleteRoi(self, roiLabelStr: str):

        pgRoi = self.roiList[roiLabelStr]

        _roi = self.roiList.pop(roiLabelStr, None)
        _ = self.roiLabelList.pop(roiLabelStr, None)

        self.refreshDiameterPlot([], [], [])

        self.view.scene().removeItem(pgRoi)

        return _roi

    def _addRoi(self, kymRoi: KymRoi) -> pg.ROI:
        """Add an ROI to self.imageItem

        Add a kymRoi to the GUI (NOT THE BACKEND)
        """

        pos, size = kymRoi.getPosSize()

        rectRoi = pg.ROI(
            pos=pos,
            pen=pg.mkPen('m', width=2),
            hoverPen=pg.mkPen('m', width=4),
            handlePen=pg.mkPen('m', width=2),
            handleHoverPen=pg.mkPen('m', width=4),
            size=size,
            parent=self.myImageItem,
            # remaining params turn of things like click+drag -> movable and shift+drag -> resizable
            movable=False,  # do not allow drag (makes gui better)
            rotatable=False,
            resizable=False,
            removable=False,  # we have gui <del> to remove
        )
        # self.myLineRoi.addScaleHandle((0,0), (1,1), name='topleft')  # at origin
        rectRoi.addScaleHandle((0.5, 0), (0.5, 1), name="bottom center")  # top center
        rectRoi.addScaleHandle((0.5, 1), (0.5, 0), name="top center")  # bottom center

        # abb 20250624 removed
        # rectRoi.addScaleHandle(
        #     (0, .5), (1, 0.5), name="left center"
        # )  # bottom center
        # rectRoi.addScaleHandle(
        #     (1, .5), (0, 0.5), name="right center"
        # )  # bottom center

        rectRoi.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton)
        rectRoi.sigClicked.connect(self._on_roi_clicked)
        rectRoi.sigRegionChangeFinished.connect(self._on_roi_changed)
        # rectRoi.sigRemoveRequested.connect(self._on_remove_roi)

        # each roi has a label
        roiLabelName = kymRoi.getLabel()

        # color does not match seaborn scatter
        _color = 'c'  # just use cyan
        roiLabel = pg.TextItem(roiLabelName, color=_color)
        roiLabel.setParentItem(rectRoi)
        font = QtGui.QFont()
        # font.setBold(True)
        from sanpy.kym.interface.kymRoiWidget import KymRoiWidget

        font.setPointSize(KymRoiWidget._pgAxisLabelFontSize)
        roiLabel.setFont(font)
        self.roiLabelList[roiLabelName] = roiLabel  # actual pyqtgraph TextItem()

        self.roiList[roiLabelName] = rectRoi  # actual pyqtgraph ROI()

        # 20241024, do not need this
        # self.kymRoiList[rectRoi] = kymRoi  # v2 backend roi

        return rectRoi

    def slot_setRoiLabel(self, oldRoiLabel: str, newRoiLabel: str):
        """Set the label for a roi."""
        logger.info(f'setting roi label from "{oldRoiLabel}" to "{newRoiLabel}"')

        # update the label
        _pgTextItem = self.roiLabelList.pop(oldRoiLabel)
        _pgTextItem.setText(newRoiLabel)
        self.roiLabelList[newRoiLabel] = _pgTextItem

        # update the roi
        _pgRoi = self.roiList.pop(oldRoiLabel)
        self.roiList[newRoiLabel] = _pgRoi

        # update the roi
        # self.roiList[newRoiLabel] = self.roiList.pop(oldRoiLabel)


    def getKymRoi(self, roiLabel: str) -> KymRoi:
        return self._kymRoiAnalysis.getRoi(roiLabel)

    def getRoiLabel(self, pgRoi: pg.ROI) -> str:
        """Get the string label of a pg.ROI (for backend).

        Reverse lookup from pgRoi to dictionary key (roi label str)
        """
        roiLabelStr = None
        for _roiLabelStr, _pgRoi in self.roiList.items():
            if _pgRoi == pgRoi:
                roiLabelStr = _roiLabelStr
                break

        # roiLabel = self.roiLabelList[roi].toPlainText()
        return roiLabelStr

    def getSelectedRoiLabel(self) -> Optional[str]:
        return self.selectedRoi

    def getSelectedKymRoi(self) -> Optional[KymRoi]:
        roiLabel = self.getSelectedRoiLabel()
        if roiLabel is None:
            return
        return self.getKymRoi(roiLabel)

    # abb 202505
    def slot_roi_changed(self, roiLabelStr: str):
        """roi has changed update pg roi.

        comming from KymRoiToolbar.

        abb 202505
        """
        pgRoi = self.roiList[roiLabelStr]
        if pgRoi is None:
            logger.warning(f'roiLabelStr:{roiLabelStr} not found in roiList')
            return

        # update the pgRoi
        kymRoi = self._kymRoiAnalysis.getRoi(roiLabelStr)  # KymRoi
        pos, size = kymRoi.getPosSize()

        update = False
        finish = False
        pgRoi.setPos(pos, update=update, finish=finish)
        pgRoi.setSize(size, update=update, finish=finish)
        pgRoi.stateChanged(finish=False)  # update handles

        logger.info(f'   -->> signalRoiChanged roiLabelStr:"{roiLabelStr}"')
        self.signalRoiChanged.emit(roiLabelStr)

    def _on_roi_changed(self, pgRoi: pg.ROI):
        """User finished dragging the ROI

        Args:
            event :pyqtgraph.graphicsItems.ROI.ROI

        Info:
            theRect2:[0, 383, 5000, 17]
        """

        pos = pgRoi.pos()
        size = pgRoi.size()
        # logger.info(f'pg.ROI pos:{pos}')
        # logger.info(f'pg.ROI size:{size}')

        # update the backend
        roiLabel = self.getRoiLabel(pgRoi)
        kymRoi = self._kymRoiAnalysis.getRoi(roiLabel)  # KymRoi

        # abb 20250624, was commented?
        # set the updated rect in backend
        newRect = kymRoi.setRectPosSize(pos, size)

        # get the actual constrained roi
        pos, size = kymRoi.getPosSize()

        update = False
        finish = False
        pgRoi.setPos(pos, update=update, finish=finish)
        pgRoi.setSize(size, update=update, finish=finish)
        pgRoi.stateChanged(finish=False)  # update handles

        logger.info(f'sanpy roi pos:{pos} size:{size}')

        roiLabelStr = self.getRoiLabel(pgRoi)
        logger.info(f'   -->> signalRoiChanged with event:"{roiLabelStr}"')
        self.signalRoiChanged.emit(roiLabelStr)

    def _on_roi_clicked(self, event: pg.ROI):
        """Respond to user selecting (clicking) an ROI.

        Parameters
        ==========
        event : pg.ROI
        """
        self._selectRoi(event)

    def selectRoiFromLabel(self, roiLabelStr: str):
        """Select an roi based on its text label (key).

        Used by parent.
        """
        logger.info(f'selectRoiFromLabel roiLabelStr:"{roiLabelStr}"')
        if roiLabelStr is not None:
            try:
                pgRoi = self.roiList[roiLabelStr]
            except KeyError:
                logger.warning(f'did not find roi label "{roiLabelStr}"')
                return
            self._selectRoi(pgRoi)
        else:
            self._selectRoi(None)
            
    def _selectRoi(self, pgRoi: Optional[pg.ROI] = None):
        """
        Parameter
        ---------
        pgRoi : pg.ROI
            The roi to select, None will deselect all roi.
        """
        # if pgRoi is not None and pgRoi == self.selectedRoi:
        #     # do not re-select
        #     return

        # deselect all
        pen = pg.mkPen('c', width=2)
        for v in self.roiList.values():
            v.setPen(pen)
        self.selectedRoi = None

        if pgRoi is not None:
            # selected roi is yellow
            roiLabel = self.getRoiLabel(pgRoi)
            pen = pg.mkPen('yellow', width=2)
            self.roiList[roiLabel].setPen(pen)

            self.selectedRoi = roiLabel
        else:
            roiLabel = None

        # refresh diameter
        if roiLabel is None:
            self.refreshDiameterPlot([], [], [])
        else:
            # timeSec = self._kymRoiAnalysis.getAnalysisTrace(roiLabel, 'timeSec', self._currentChannel)
            timeSec = self._kymRoiAnalysis.getAnalysisTrace(
                roiLabel, 'Time (s)', self._currentChannel
            )
            leftDiameterUm = self._kymRoiAnalysis.getAnalysisTrace(
                roiLabel, 'Left Diameter (um)', self._currentChannel
            )
            rightDiameterUm = self._kymRoiAnalysis.getAnalysisTrace(
                roiLabel, 'Right Diameter (um)', self._currentChannel
            )
            self.refreshDiameterPlot(timeSec, leftDiameterUm, rightDiameterUm)

        logger.warning(f'   -->> signalSelectRoi.emit with roiLabel:"{roiLabel}"')
        self.signalSelectRoi.emit(self._currentChannel, roiLabel)

    def _toggleROI(self, visible: bool):
        """Toggle all roi on/off."""
        # toggle labels
        for label in self.roiLabelList.values():
            label.setVisible(visible)

        # toggle roi
        for roi in self.roiList.values():
            roi.setVisible(visible)

    def setAutoContrast(self):
        from sanpy.kym.kymUtils import getAutoContrast

        _min, _max = getAutoContrast(self.imgData)  # new 20240925, should mimic ImageJ

        logger.info(f'_min:{_min} _max:{_max}')

        self._minContrast = _min  # np.min(self.imgData)
        self._maxContrast = _max  # int(np.max(self.imgData) / 2)

        # update gui
        self.minContrastSlider.setValue(self._minContrast)
        self.maxContrastSlider.setValue(self._maxContrast)

    def getImageRect(self):
        """Get image rect with (x,y) scale.

        Used to display kym ImageItem
        """
        left = 0
        top = self.imgData.shape[0] * self._kymRoiAnalysis.umPerPixel
        right = self.imgData.shape[1] * self._kymRoiAnalysis.secondsPerLine
        bottom = 0

        width = right - left
        height = top - bottom

        return left, bottom, width, height  # x, y, w, h

    def _hoverEvent(self, event):
        """Hover on image -> update status in QMainWindow"""
        if event.isExit():
            return

        xPos = event.pos().x()
        yPos = event.pos().y()

        xPos = int(xPos)
        yPos = int(yPos)

        try:
            intensity = self.imgData[yPos, xPos]  # flipped
        except IndexError as e:
            intensity = 'None'

        intensity = f'{xPos} {yPos} intensity:{intensity}'

        # logger.warning(f'todo: set on hover "{intensity}"')
        # self.mySetStatusBar(intensity)

    def _buildTopToolbar(self) -> QtWidgets.QVBoxLayout:
        vBoxLayout = QtWidgets.QVBoxLayout()
        vBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        hLayout = QtWidgets.QHBoxLayout()
        hLayout.setAlignment(QtCore.Qt.AlignLeft)
        vBoxLayout.addLayout(hLayout)

        # move to detection widget
        # buttonName = 'Save Analysis'
        # aButton = QtWidgets.QPushButton(buttonName)
        # aButton.setToolTip('Save analysis for all roi(s)')
        # aButton.clicked.connect(
        #     self.saveAnalysis
        # )
        # hLayout.addWidget(aButton)

        # aCheckBoxName = 'ROIs'
        # aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        # aCheckBox.setToolTip('Toggle ROIs on/off')
        # aCheckBox.setChecked(True)  # show by default
        # aCheckBox.stateChanged.connect(
        #     partial(self._on_checkbox_clicked, aCheckBoxName)
        # )
        # hLayout.addWidget(aCheckBox)

        buttonName = 'Add ROI'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Add an ROI')
        aButton.clicked.connect(partial(self._on_button_click, buttonName))
        hLayout.addWidget(aButton)

        buttonName = 'Delete ROI'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Delete selected ROI')
        aButton.clicked.connect(partial(self._on_button_click, buttonName))
        hLayout.addWidget(aButton)

        aCheckBoxName = 'ROI'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle roi plot on/off')
        aCheckBox.setChecked(True)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout.addWidget(aCheckBox)

        aCheckBoxName = 'Contrast'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle contrast sliders')
        aCheckBox.setChecked(False)  # hidden by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout.addWidget(aCheckBox)

        aCheckBoxName = 'Line Profile'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle contrast sliders')
        aCheckBox.setChecked(False)  # hidden by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout.addWidget(aCheckBox)

        if self._kymRoiAnalysis._fakeScale:
            aLabel = QtWidgets.QLabel('Fake Scale')
            hLayout.addWidget(aLabel)

        # set channel
        aName = 'Channel'
        # aLabel = QtWidgets.QLabel(aName)
        # hLayout.addWidget(aLabel)

        channelComboBox = QtWidgets.QComboBox()
        _channelList = [
            f'Channel {str(_channel+1)}'
            for _channel in range(self._kymRoiAnalysis.numChannels)
        ]
        channelComboBox.addItems(_channelList)
        channelComboBox.setCurrentIndex(0)  # default to 0
        channelComboBox.currentTextChanged.connect(partial(self._on_combobox, aName))
        hLayout.addWidget(channelComboBox)

        # second row
        # hLayout1 = QtWidgets.QHBoxLayout()
        # hLayout1.setAlignment(QtCore.Qt.AlignLeft)
        # vBoxLayout.addLayout(hLayout1)

        # show intensity under cursor
        # TODO: put this somewhere better
        # self.hoverLabel = QtWidgets.QLabel(None)
        # hLayout1.addWidget(self.hoverLabel, alignment=QtCore.Qt.AlignRight)

        return vBoxLayout

    def _buildContrastSliders(self) -> QtWidgets.QWidget:

        hBox = QtWidgets.QHBoxLayout()

        vBoxLeft = QtWidgets.QVBoxLayout()
        vBoxLeft.setAlignment(QtCore.Qt.AlignTop)
        vBoxRight = QtWidgets.QVBoxLayout()
        vBoxRight.setAlignment(QtCore.Qt.AlignTop)

        hBox.addLayout(vBoxLeft)
        hBox.addLayout(vBoxRight)

        # color popup
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
        colorComboBox.setCurrentIndex(0)  # default to Red
        colorComboBox.currentTextChanged.connect(partial(self.setColorMap))
        vBoxLeft.addWidget(colorComboBox)

        buttonName = 'Auto'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(partial(self._on_button_click, buttonName))
        vBoxLeft.addWidget(aButton)

        # image min/max
        hBoxImgMinMax = QtWidgets.QHBoxLayout()
        vBoxLeft.addLayout(hBoxImgMinMax)

        #
        # contrast sliders
        bitDepth = 8

        # min contrast row
        minContrastLayout = QtWidgets.QHBoxLayout()

        minLabel = QtWidgets.QLabel("Min")
        minContrastLayout.addWidget(minLabel)

        self.minContrastSpinBox = QtWidgets.QSpinBox()
        self.minContrastSpinBox.setEnabled(False)
        self.minContrastSpinBox.setMinimum(0)
        self.minContrastSpinBox.setMaximum(2**bitDepth)
        minContrastLayout.addWidget(self.minContrastSpinBox)

        self.minContrastSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.minContrastSlider.setMinimum(0)
        self.minContrastSlider.setMaximum(2**bitDepth)
        self.minContrastSlider.setValue(0)
        self.minContrastSlider.valueChanged.connect(
            lambda val, name="minSlider": self._onContrastSliderChanged(val, name)
        )
        minContrastLayout.addWidget(self.minContrastSlider)

        # image min
        self.tifMinLabel = QtWidgets.QLabel(f'Img Min:{np.min(self.imgData)}')
        minContrastLayout.addWidget(self.tifMinLabel)

        vBoxRight.addLayout(minContrastLayout)

        # max contrast row
        maxContrastLayout = QtWidgets.QHBoxLayout()

        maxLabel = QtWidgets.QLabel("Max")
        maxContrastLayout.addWidget(maxLabel)

        self.maxContrastSpinBox = QtWidgets.QSpinBox()
        self.maxContrastSpinBox.setEnabled(False)
        self.maxContrastSpinBox.setMinimum(0)
        self.maxContrastSpinBox.setMaximum(2**bitDepth)
        maxContrastLayout.addWidget(self.maxContrastSpinBox)

        self.maxContrastSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.maxContrastSlider.setMinimum(0)
        self.maxContrastSlider.setMaximum(2**bitDepth)
        self.maxContrastSlider.setValue(2**bitDepth)
        self.maxContrastSlider.valueChanged.connect(
            lambda val, name="maxSlider": self._onContrastSliderChanged(val, name)
        )
        maxContrastLayout.addWidget(self.maxContrastSlider)

        # image max
        self.tifMaxLabel = QtWidgets.QLabel(f'Max:{np.max(self.imgData)}')
        maxContrastLayout.addWidget(self.tifMaxLabel)

        vBoxRight.addLayout(maxContrastLayout)

        # row for x/y scale
        hScaleLayout = QtWidgets.QHBoxLayout()
        hScaleLayout.setAlignment(QtCore.Qt.AlignRight)
        vBoxRight.addLayout(hScaleLayout)

        self._imgBitDepth = QtWidgets.QLabel(f'dtype:{self.imgData.dtype}')
        self._xScaleLabel = QtWidgets.QLabel(
            f'ms/line:{self._kymRoiAnalysis.secondsPerLine*1000}'
        )
        self._yScaleLabel = QtWidgets.QLabel(
            f'um/pixel:{self._kymRoiAnalysis.umPerPixel}'
        )

        aName = 'Set Scale'
        aButton = QtWidgets.QPushButton(aName)
        aButton.setToolTip('Add an ROI')
        aButton.clicked.connect(partial(self._on_button_click, aName))
        hScaleLayout.addWidget(self._imgBitDepth)
        hScaleLayout.addWidget(self._xScaleLabel)
        hScaleLayout.addWidget(self._yScaleLabel)
        hScaleLayout.addWidget(aButton)

        # return as widget so we can call setVisible()
        aWidget = QtWidgets.QWidget()
        aWidget.setLayout(hBox)

        return aWidget

    def _setScaleDialog(self):
        """Show a set scale dialog."""
        secondsPerLine = self._kymRoiAnalysis.secondsPerLine
        umPerPixel = self._kymRoiAnalysis.umPerPixel
        mcd = SetScaleDialog(secondsPerLine, umPerPixel)
        if mcd.exec():
            scaleDict = mcd.getResults()
            logger.info(f'got from dialog scaleDict:{scaleDict}')
            secondsPerLine = scaleDict['secondsPerLine']
            umPerPixel = scaleDict['umPerPixel']

            # set new scale in backend
            self._kymRoiAnalysis.header['secondsPerLine'] = secondsPerLine
            self._kymRoiAnalysis.header['umPerPixel'] = umPerPixel

            # update labels
            self._xScaleLabel.setText(
                str(f'ms/line:{self._kymRoiAnalysis.secondsPerLine*1000}')
            )
            self._yScaleLabel.setText(
                str(f'um/pixel:{self._kymRoiAnalysis.umPerPixel}')
            )

            # update image
            imageRect = self.getImageRect()  # l,b,h,w
            axisOrder = "row-major"
            self.myImageItem.setImage(self.imgData, axisOrder=axisOrder, rect=imageRect)

    def _buildUI(self):
        self.setContentsMargins(0, 0, 0, 0)

        # toolbar, contrast slider, then image
        mainVBoxLayout = QtWidgets.QVBoxLayout()
        mainVBoxLayout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(mainVBoxLayout)

        self._topToolbar = (
            self._buildTopToolbar()
        )  # one row with file name, image params
        mainVBoxLayout.addLayout(self._topToolbar)

        self._contrastSliders = self._buildContrastSliders()
        self._contrastSliders.setVisible(False)
        mainVBoxLayout.addWidget(self._contrastSliders)

        # kymograph
        self.view = pg.GraphicsLayoutWidget()
        mainVBoxLayout.addWidget(self.view)

        # pyqtgraph.graphicsItems.PlotItem
        row = 0
        colSpan = 1
        rowSpan = 1
        self.kymographPlot = self.view.addPlot(
            row=row, col=0, rowSpan=rowSpan, colSpan=colSpan
        )
        """A PlotItem"""

        self.kymographPlot.setLabel("left", "Pixels (um)", units="")
        self.kymographPlot.setLabel("bottom", "Time (s)", units="")

        # make the font a bit bigger
        # _origFont = self.kymographPlot.getAxis("bottom").label.font()
        # _origFont.setPointSize(18)
        # self.kymographPlot.getAxis("bottom").label.setFont(_origFont)
        # self.kymographPlot.getAxis("left").label.setFont(_origFont)

        self.kymographPlot.setDefaultPadding()
        self.kymographPlot.enableAutoRange()
        self.kymographPlot.setMouseEnabled(x=True, y=False)
        self.kymographPlot.hideButtons()  # hide the little 'A' button to rescale axis
        self.kymographPlot.setMenuEnabled(False)  # turn off right-click menu

        # switching to PyMapManager style contrast with setLevels()
        imageRect = self.getImageRect()  # l,b,h,w
        self.myImageItem = pg.ImageItem(
            self.imgData, axisOrder="row-major", rect=imageRect
        )  # need transpose for row-major

        # logger.warning('--->>> tryin ColorBarItem')
        # self.aColorBar = pg.ColorBarItem()
        # self.aColorBar.setImageItem(self.myImageItem)
        self.setColorMap(
            'Green'
        )  # sets self.aColorBar which sets children (self.myImageItem)

        self.kymographPlot.addItem(self.myImageItem, ignorBounds=True)

        # redirect hover to self (to display intensity
        self.myImageItem.hoverEvent = self._hoverEvent

        # left/right scatter on top of kymograph
        self._overlayKymDict = {}
        self._overlayKymDict['leftDiamOverlay'] = self.kymographPlot.plot(
            name="leftDiamOverlay",
            pen=None,
            symbol='o',
            symbolPen=None,
            symbolSize=5,
            symbolBrush=pg.mkBrush(250, 0, 250, 200),  # green
        )
        self._overlayKymDict['rightDiamOverlay'] = self.kymographPlot.plot(
            name="rightDiamOverlay",
            pen=None,
            symbol='o',
            symbolPen=None,
            symbolSize=5,
            symbolBrush=pg.mkBrush(0, 250, 250, 200),  # red
        )

        # vertical line in kymographPlot to show selected line scan
        self._kymLineScanLine = pg.InfiniteLine(pen=pg.mkPen(color='c', width=2))
        self.kymographPlot.addItem(self._kymLineScanLine)

        # line scan slider
        self._lineScanSlider = QtWidgets.QSlider(
            orientation=QtCore.Qt.Orientation.Horizontal
        )
        self._lineScanSlider.setMinimum(0)
        self._lineScanSlider.setMaximum(self.imgData.shape[1])
        self._lineScanSlider.setValue(0)
        self._lineScanSlider.valueChanged.connect(
            partial(self._on_line_scan_slider, 'Line Scan Slider')
        )
        mainVBoxLayout.addWidget(self._lineScanSlider)

        self._lineProfileWidget = LineProfileWidget(self)
        self.signalSelectRoi.connect(self._lineProfileWidget.selectRoi)
        self.signalRoiChanged.connect(self._lineProfileWidget.selectRoi)
        self.signalSetLineProfile.connect(
            self._lineProfileWidget.slot_updateLineProfile
        )
        self._lineProfileWidget.setVisible(False)
        mainVBoxLayout.addWidget(self._lineProfileWidget)

        # update to line scan 0
        self._on_line_scan_slider('', 0)

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

    def setLineScanSlider(self, lineScanNumber: int):
        """Programatically set the selected line scan."""

        # line scan plot
        secondsValue = lineScanNumber * self._kymRoiAnalysis.secondsPerLine
        self._kymLineScanLine.setPos(secondsValue)

        # slider
        self._lineScanSlider.setValue(lineScanNumber)

        # line profile
        # self.signalSetLineProfile.emit(lineScanNumber)

    def _on_line_scan_slider(self, name, lineScanIdx):
        # logger.info(f'{name} {lineScanIdx}')

        # the vertical line on the kym image
        secondsValue = lineScanIdx * self._kymRoiAnalysis.secondsPerLine
        self._kymLineScanLine.setPos(secondsValue)

        self.signalSetLineProfile.emit(lineScanIdx)

    def _on_combobox(self, name, value):
        """
        Parameters
        ----------
        detectionDict : dict
            Switches between multiple detection group boxes like (detect int, detect diam)
        """

        logger.info(f'"{name}" value:{value} {type(value)}')

        if name == 'Channel':
            value = value.replace('Channel ', '')
            value = int(value)
            self.switchChannel(value)

    def _on_checkbox_clicked(self, name, value=None):
        # if self._blockSlots:
        #     # logger.warning(f'_blockSlots -->> no update for {name} {value}')
        #     return

        if value > 0:
            value = 1

        # show/hide widgets
        if name == 'Contrast':
            self._contrastSliders.setVisible(value)

        elif name == 'ROI':
            # toggle all roi
            self._toggleROI(value)

        elif name == 'Line Profile':
            self._lineProfileWidget.setVisible(value)

        else:
            logger.warning(f'did not understand name "{name}"')

    def _on_button_click(self, name: str):
        logger.info(f'name:{name}')

        if name == 'Add ROI':
            self.onUserAddRoi()

        elif name == 'Delete ROI':
            self.onUserDeleteRoi()

        elif name == 'Auto':
            # auto contrast
            self.setAutoContrast()

        elif name == 'Set Scale':
            self._setScaleDialog()

        else:
            logger.warning(f'did not understand button "{name}"')

    def mySetStatusBar(self, statusStr: str):
        """Set the status bar of a parent kymRoiWidget.

        Only exists during PyQt runtime (not in scripts).
        """
        logger.info(statusStr)
        if self._kymRoiWidget is not None:
            self._kymRoiWidget.mySetStatusbar(statusStr)

    def refreshDiameterPlot(self, timeSec, leftDiameterUm, rightDiameterUm):
        # left/right on kym image
        self._overlayKymDict['leftDiamOverlay'].setData(timeSec, leftDiameterUm)
        self._overlayKymDict['rightDiamOverlay'].setData(timeSec, rightDiameterUm)

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

    def switchChannel(self, channel: int):
        """
        Parameters
        ==========
        channel : int
            Image channel (user GUI is 1 based)
        """
        channelIdx = channel - 1

        if channelIdx < 0 or channelIdx > self._kymRoiAnalysis.numChannels:
            logger.error(
                f'got channel:{channel} but channel has to be in range {1}..{self._kymRoiAnalysis.numChannels}'
            )
            return

        logger.info(f'channel:{channel} channelIdx:{channelIdx}')

        self._currentChannel = channelIdx

        #
        # re-emit roi selection in new channel
        #
        selectedRoiLabel = self.getSelectedRoiLabel()
        # logger.info(f're-selecting roi "{selectedRoi}"')
        self.selectRoiFromLabel(selectedRoiLabel)

        imageRect = self.getImageRect()  # l,b,h,w
        axisOrder = "row-major"
        self.myImageItem.setImage(self.imgData, axisOrder=axisOrder, rect=imageRect)

        # min/max in contrast slider
        imgMax = np.max(self.imgData)
        self.tifMinLabel.setText(f'Img Min:{np.min(self.imgData)}')
        self.tifMaxLabel.setText(f'Img Max:{imgMax}')
        #
        self.minContrastSlider.setMaximum(imgMax)
        self.minContrastSpinBox.setMaximum(imgMax)
        #
        self.maxContrastSlider.setMaximum(imgMax)
        self.maxContrastSpinBox.setMaximum(imgMax)

        self.setAutoContrast()

        _levels = [self._minContrast, self._maxContrast]
        self.myImageItem.setLevels(_levels, update=True)

        # detect button follow channel color
        # from sanpy.kym.interface.kymRoiWidget import getChannelColor
        detectButtonColor = self._kymRoiAnalysis.getChannelColor(self._currentChannel)
        self.setColorMap(detectButtonColor)

        # self.signalSetChannel.emit(self._currentChannel)

    def slot_detectionChanged(self, detectionType: str, detectionDict: KymRoiDetection):
        """Pass changes in diameter detection to child lineProfileWidget."""
        self._lineProfileWidget.slot_detectionChanged(detectionType, detectionDict)


class LineProfileWidget(QtWidgets.QWidget):
    def __init__(self, kymRoiImageWidget: KymRoiImageWidget):
        super().__init__(None)

        self._kymRoiImageWidget = kymRoiImageWidget
        self._lineIndex = 0
        self._buildGui()

    @property
    def currentChannel(self):
        return self._kymRoiImageWidget._currentChannel

    def slot_detectionChanged(self, detectionType: str, detectionDict: KymRoiDetection):
        # logger.info(f'detectionType:"{detectionType}"')
        # kymRoi = self._kymRoiImageWidget.getSelectedKymRoi()
        self.slot_updateLineProfile()

    def selectRoi(self, roiLabel: str):
        # if roiLabel is None:
        #     self.lineProfilePlot.setData([], [])
        #     return
        # kymRoi = self._kymRoiImageWidget.getKymRoi(roiLabel)
        self.slot_updateLineProfile()

    def slot_updateLineProfile(self, lineIdx: int = None):

        kymRoi = self._kymRoiImageWidget.getSelectedKymRoi()

        if kymRoi is None:
            self.lineProfilePlot.setData([], [])
            return

        if lineIdx is not None:
            self._lineIndex = lineIdx

        lineIdx = self._lineIndex

        channel = self._kymRoiImageWidget._currentChannel

        # pen for mean/std/2*std
        _channelColor = self._kymRoiImageWidget._kymRoiAnalysis.getChannelColor(channel)
        _penForChannel = pg.mkPen(
            color=_channelColor, width=2, style=QtCore.Qt.DashLine
        )

        detectionParams = kymRoi.getDetectionParams(
            channel, PeakDetectionTypes.diameter
        )
        stdThreshold = detectionParams['std_threshold_mult_diam']
        lineScanFraction = detectionParams[
            'line_scan_fraction_diam'
        ]  # fraction of line for lef/right, 4 is 25% and 2 is 50%
        lineInterptMult = detectionParams[
            'line_interp_mult_diam'
        ]  # interpolate each line scan by this multiplyer

        xUm, lineProfile = kymRoi.getLineProfile(channel, lineIdx)
        self.lineProfilePlot.setData(xUm, lineProfile)

        # left
        leftStopBin = int(len(lineProfile) / lineScanFraction)
        leftStopUm = leftStopBin / lineInterptMult * kymRoi.umPerPixel
        # logger.info(f'   leftStopUm:{leftStopUm} leftStopBins:{leftStopBin}')
        leftMean = np.mean(lineProfile[0:leftStopBin])
        leftStd = np.std(lineProfile[0:leftStopBin])
        leftThreshold = leftMean + (leftStd * stdThreshold)
        self.leftThreshold.setData([0, leftStopUm], [leftThreshold, leftThreshold])
        self.leftMean.setData([0, leftStopUm], [leftMean, leftMean])
        self.leftStd1.setData([0, leftStopUm], [leftMean + leftStd, leftMean + leftStd])
        self.leftStd2.setData(
            [0, leftStopUm], [leftMean + 2 * leftStd, leftMean + 2 * leftStd]
        )
        # color based on channel
        self.leftMean.setPen(_penForChannel)
        self.leftStd1.setPen(_penForChannel)
        self.leftStd2.setPen(_penForChannel)

        # right
        rightStartBin = len(lineProfile) - int(len(lineProfile) / lineScanFraction)
        rightStartUm = rightStartBin / lineInterptMult * kymRoi.umPerPixel
        # logger.info(f'   rightStartUm:{rightStartUm} rightStartBins:{rightStartBin}')
        rightMean = np.mean(lineProfile[rightStartBin:-1])
        rightStd = np.std(lineProfile[rightStartBin:-1])
        rightThreshold = rightMean + (rightStd * stdThreshold)
        self.rightThreshold.setData(
            [rightStartUm, len(lineProfile) / lineInterptMult * kymRoi.umPerPixel],
            [rightThreshold, rightThreshold],
        )
        self.rightMean.setData(
            [rightStartUm, len(lineProfile) / lineInterptMult * kymRoi.umPerPixel],
            [rightMean, rightMean],
        )
        self.rightStd1.setData(
            [rightStartUm, len(lineProfile) / lineInterptMult * kymRoi.umPerPixel],
            [rightMean + rightStd, rightMean + rightStd],
        )
        self.rightStd2.setData(
            [rightStartUm, len(lineProfile) / lineInterptMult * kymRoi.umPerPixel],
            [rightMean + 2 * rightStd, rightMean + 2 * rightStd],
        )
        # color based on channel
        self.rightMean.setPen(_penForChannel)
        self.rightStd1.setPen(_penForChannel)
        self.rightStd2.setPen(_penForChannel)

    def _buildGui(self):
        vBoxPlot = QtWidgets.QVBoxLayout()
        self.setLayout(vBoxPlot)

        self.lineProfilePlotWidget = pg.PlotWidget()
        vBoxPlot.addWidget(self.lineProfilePlotWidget)

        self.lineProfilePlotWidget.setDefaultPadding()
        self.lineProfilePlotWidget.enableAutoRange()
        self.lineProfilePlotWidget.setMouseEnabled(x=True, y=False)
        self.lineProfilePlotWidget.hideButtons()  # hide the little 'A' button to rescale axis

        self.lineProfilePlotWidget.setLabel("left", "Intensity", units="")
        self.lineProfilePlotWidget.setLabel("bottom", 'Distance (um)', units="")

        # the actual line profileplot

        # left
        self.lineProfilePlot = self.lineProfilePlotWidget.plot(
            name="lineProfilePlot",
            pen=pg.mkPen(color='c', width=3),
            #   symbol='o',
            #   brush=pg.mkBrush(100, 255, 100, 220),
        )

        self.leftMean = self.lineProfilePlotWidget.plot(
            name="leftMean",
            pen=pg.mkPen(color='r', width=2, style=QtCore.Qt.DashLine),
            #   symbol='o',
            #   brush=pg.mkBrush(200, 0, 0, 220),
        )
        self.leftStd1 = self.lineProfilePlotWidget.plot(
            name="leftStd1",
            pen=pg.mkPen(color='r', width=2, style=QtCore.Qt.DashLine),
            #   symbol='o',
            #   brush=pg.mkBrush(200, 0, 0, 220),
        )
        self.leftStd2 = self.lineProfilePlotWidget.plot(
            name="leftStd1",
            pen=pg.mkPen(color='r', width=2, style=QtCore.Qt.DashLine),
            #   symbol='o',
            #   brush=pg.mkBrush(200, 0, 0, 220),
        )
        # build last so it is on top
        self.leftThreshold = self.lineProfilePlotWidget.plot(
            name="leftThreshold",
            pen=pg.mkPen(color='y', width=2, style=QtCore.Qt.DashLine),
            #   symbol='o',
            #   brush=pg.mkBrush(200, 0, 0, 220),
        )

        # right
        self.rightMean = self.lineProfilePlotWidget.plot(
            name="leftMean",
            pen=pg.mkPen(color='r', width=2, style=QtCore.Qt.DashLine),
            #   symbol='o',
            #   brush=pg.mkBrush(200, 0, 0, 220),
        )
        self.rightStd1 = self.lineProfilePlotWidget.plot(
            name="leftStd1",
            pen=pg.mkPen(color='r', width=2, style=QtCore.Qt.DashLine),
            #   symbol='o',
            #   brush=pg.mkBrush(200, 0, 0, 220),
        )
        self.rightStd2 = self.lineProfilePlotWidget.plot(
            name="leftStd1",
            pen=pg.mkPen(color='r', width=2, style=QtCore.Qt.DashLine),
            #   symbol='o',
            #   brush=pg.mkBrush(200, 0, 0, 220),
        )
        # build last so it is on top
        self.rightThreshold = self.lineProfilePlotWidget.plot(
            name="leftThreshold",
            pen=pg.mkPen(color='y', width=2, style=QtCore.Qt.DashLine),
            #   symbol='o',
            #   brush=pg.mkBrush(200, 0, 0, 220),
        )
