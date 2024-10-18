import os
# import math
from typing import List
from functools import partial
# from copy import copy
# import json

import numpy as np
import pandas as pd

import scipy.optimize
from scipy.signal import peak_widths, medfilt, savgol_filter, detrend, find_peaks
from skimage import restoration

import seaborn as sns  # to get color palette

import matplotlib.pyplot as plt

from PyQt5 import QtGui, QtCore, QtWidgets
import pyqtgraph as pg

import sanpy
from sanpy.interface import sanpyCursors

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, KymRoi, PeakDetectionTypes

from sanpy.kym.kymRoiDetection import KymRoiDetection
from sanpy.kym.kymRoiResults import KymRoiResults

from sanpy.kym.interface.kymDetectionToolbar import KymDetectionGroupBox
from sanpy.kym.interface.kymRoiScatter import SimpleRoiScatter
from sanpy.kym.interface.kymRoiClipsWidget import KymRoiClipsWidget

from sanpy.kym.interface.kymPlotWidget import KymPlotWidget  # new 20241014

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class RoiManager(QtWidgets.QWidget):
    """Manager a list of rectangular ROIs.
    
    The units here are always in pixels of underlying imgData
    
    TODO
    ----
    Remove physical units
    """
    signalSelectRoi = QtCore.pyqtSignal(object)  # roi
    signalRoiChanged = QtCore.pyqtSignal(object)  # roi

    def __init__(self, view, imageItem, imgData):
        super().__init__(None)
        
        self.view = view
        self.imageItem = imageItem

        self.imgData = imgData

        self.roiList = {}
        self.roiLabelList = {}

        self.kymRoiList = {}  # v2 backend

        self.selectedRoi = None
    
        # does not work, trying to match colors in seaborn scatter
        self._colors = sns.color_palette("Paired", 50).as_hex()

    def getAnalysisTrace(self, roi, name):
        return self.kymRoiList[roi].getTrace(name)
    
    def getDetectionParams(self, roi, detectionType : PeakDetectionTypes):
        # return self.kymRoiList[roi].detectionParams
        return self.kymRoiList[roi].getDetectionParams(detectionType)
    
    def getAnalysisResults(self, roi, detectionType : PeakDetectionTypes):
        return self.kymRoiList[roi].getAnalysisResults(detectionType)
    
    # def getDetectionParamsDiameter(self, roi):
    #     return self.kymRoiList[roi].detectionParamsDiameter
    
    # def getAnalysisResultsDiameter(self, roi):
    #     return self.kymRoiList[roi].analysisResultsDiameter
    
    def _old_getImgData(self, roi):
        """Get imgData for an roi.
        """
        [left, t, r, b] = self._roiAsRect(roi)  # [left, top, right, bottom]
        
        logger.info(f'fetching [left,t,r,b] {[left, t, r, b]} from image shape:{self.imgData.shape}')
        
        roiImg = self.imgData[b:t, left:r]
        
        # IMPORTANT, np array indexing returns a view (not a copy)
        roiImg = np.copy(roiImg)

        # logger.info(f'   returning roiImg shape:{roiImg.shape} from left:{left} t:{t} r:{r} b:{b}')
        
        return roiImg

    @property
    def numRoi(self):
        return len(self.roiList.keys())
    
    def switchFile(self, imgData):    
        self.imgData = imgData

    def _getDefaultRoi(self):
        """Get a default ROI.
        
        We will create a default as 20% of height. This is because rolling average is slow.
        """
        pos = (0,0)
        w = self.imgData.shape[1]
        h = self.imgData.shape[0]

        _percentHeight = 0.1
        h = int(h * _percentHeight)

        size = (w, h)
        logger.info(f'pos:{pos} size:{size}')
        return pos, size
    
    def _removeRoi(self, roi):
        
        # remove from backend
        # roiLabelName = self.kymRoiList[roi].getLabel()

        _kymRoi = self.kymRoiList.pop(roi, None)  # v2 backend

        _roi = self.roiList.pop(roi, None)
        self.view.scene().removeItem(roi)

        # roiLabel = self.roiLabelList.pop(roi, None)
        # logger.info(f'removed roiLabel:{roiLabel}')
    
        return _roi
    
    def removeSelectedRoi(self, kymRoiAnalysis : KymRoiAnalysis):
        if self.selectedRoi is not None:
            
            # delete from backend KymRoiAnalysis
            roiLabel = self.kymRoiList[self.selectedRoi].getLabel()
            kymRoiAnalysis.deleteRoi(roiLabel)

            # delte from gui
            roi = self._removeRoi(self.selectedRoi)
            
            self.selectedRoi = None
            
            # self._selectRoi(None)

            return roi
        else:
            logger.info('no selected roi to remove')
    
    def addRoi(self, kymRoi : KymRoi, doSelect=True):
        """Add an ROI to self.imageItem
        
        ltrbRoi : [l, t, r, b]
        """

        pos, size = kymRoi.getPosSize()

        movable = True
        removable = False
        rectRoi = pg.ROI(
            pos=pos,
            pen=pg.mkPen('c', width=2),
            hoverPen=pg.mkPen(width=4),
            size=size,
            parent=self.imageItem,
            movable=movable,
            removable=removable
        )
        # self.myLineRoi.addScaleHandle((0,0), (1,1), name='topleft')  # at origin
        rectRoi.addScaleHandle(
            (0.5, 0), (0.5, 1), name="bottom center"
        )  # top center
        rectRoi.addScaleHandle(
            (0.5, 1), (0.5, 0), name="top center"
        )  # bottom center
        rectRoi.addScaleHandle(
            (0, .5), (1, 0.5), name="left center"
        )  # bottom center
        rectRoi.addScaleHandle(
            (1, .5), (0, 0.5), name="right center"
        )  # bottom center
        
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
        font.setBold(True)
        font.setPointSize(12)
        roiLabel.setFont(font)
        self.roiLabelList[rectRoi] = roiLabel  # actual pyqtgraph TextItem()

        self.roiList[rectRoi] = rectRoi  # actual pyqtgraph ROI()
        self.kymRoiList[rectRoi] = kymRoi  # v2 backend roi

        if doSelect:
            self._selectRoi(rectRoi)

        return rectRoi
            
    def _on_roi_clicked(self, event):
        """
        Parameters
        ==========
        event : pyqtgraph.graphicsItems.ROI.ROI
        """
        # logger.info(event)
        self._selectRoi(event)

    def _selectRoi(self, roi = None):
        
        if roi is not None and roi == self.selectedRoi:
            # do not re-select
            return
        
        # deselect all
        pen = pg.mkPen('c', width=2)
        for v in self.roiList.values():
            v.setPen(pen)
        self.selectedRoi = None

        if roi is not None:
            # selected roi is yellow
            pen = pg.mkPen('yellow', width=2)
            self.roiList[roi].setPen(pen)

            self.selectedRoi = roi

        self.signalSelectRoi.emit(roi)

    def _toggleROI(self, visible : bool):
        for label in self.roiLabelList.keys():
            label.setVisible(visible)
        for roi in self.roiList.keys():
            roi.setVisible(visible)

    # def _roiAsRect(self, roi, inPhysicalUnits=False) -> List[int]:
    def _roiAsRect(self, roi) -> List[int]:
        """Convert a PyQt rect with pos() and size() to [l, t, r, b].

        Returns
            [l, t, r, b]
        """
        pos = roi.pos()
        size = roi.size()

        left = pos[0]
        top = pos[1] + size[1]
        right = pos[0] + size[0]
        bottom = pos[1]
        
        left = int(left)
        top = int(top)
        right = int(right)
        bottom = int(bottom)

        # logger.info(f'   after left:{left} top:{top} right:{right} bottom:{bottom}')

        return [left, top, right, bottom]

    def setPosSize(self, ltrbRoi : List[int]):
        """Set Pos() and Size() from [l, t, r, b] rect.
        
        Parameters
        ----------
        ltrbRoi : [l, t, r, b]
        """
        pos = (ltrbRoi[0], ltrbRoi[3])
        size = (ltrbRoi[2] - ltrbRoi[0], ltrbRoi[1] - ltrbRoi[3])

        self._rectRoi.setPos(pos)
        self._rectRoi.setSize(size)

    def getSelectedRoi(self):
        return self.selectedRoi
    
    def _on_roi_clicked(self, event):
        """
        Parameters
        ==========
        event : pyqtgraph.graphicsItems.ROI.ROI
        """
        # logger.info(event)
        self._selectRoi(event)

    def _selectRoi(self, roi = None):
            
        if roi is not None and roi == self.selectedRoi:
            return
        
        # deselect all
        pen = pg.mkPen('c', width=2)
        for v in self.roiList.values():
            v.setPen(pen)
        self.selectedRoi = None

        if roi is not None:
            # selected roi is yellow
            pen = pg.mkPen('yellow', width=2)
            self.roiList[roi].setPen(pen)

            self.selectedRoi = roi

        self.signalSelectRoi.emit(roi)
    
    def _on_roi_changed(self, event):
        """User finished dragging the ROI

        Args:
            event :pyqtgraph.graphicsItems.ROI.ROI

        Info:
            theRect2:[0, 383, 5000, 17]
        """

        pos = event.pos()
        size = event.size()
        
        logger.info(f'starting pos:{pos} size:{size}')

        # new rect might be contrained
        newRect = self.kymRoiList[event].setRectPosSize(pos, size)
        logger.info(f'      roi is now: {newRect}')


        # our pos and size is a PROPOSAL, might have changed if had to be contrained
        pos, size = self.kymRoiList[event].getPosSize()
        logger.info(f'      SETTING pos:{pos} size:{size}')
        update = False
        finish = False
        event.setPos(pos, update=update, finish=finish)
        event.setSize(size, update=update, finish=finish)
        event.stateChanged(finish=False)  # update handles

        #
        self._selectRoi(event)  # needed to select when click+drag on handle

        # logger.info(f'  -->> emit signalKymographRoiChanged event:{event}')
        self.signalRoiChanged.emit(event)

        return
    
class KymRoiWidget(QtWidgets.QMainWindow):
    def __init__(self, kymRoiAnalysis : KymRoiAnalysis):
        super().__init__(None)
        
        self._kymRoiAnalysis = kymRoiAnalysis

        self._minContrast = 0
        self._maxContrast = 50

        # this switches for each selected ROI
        self._detectionParams : KymRoiDetection = KymRoiDetection()
        
        self._detectionParamsDiameter : KymRoiDetection = KymRoiDetection()
        self._detectionParamsDiameter.setParam('Exponential Detrend', False)

        self._blockSlots = False
        
        self._buildUI()

        self.roiList = RoiManager(self.view, self.myImageItem, self.imgData)
        self.roiList.signalRoiChanged.connect(self._roi_changed)
        self.roiList.signalSelectRoi.connect(self.selectRoi)

        # re-wire right-click (for entire widget)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu)

        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)

        self.setWindowTitle(self.path)

        self.loadAnalysis()  # load from folder with text file analysis (if it exists)

        #
        # important
        self.switchFile(self.imgData)

        # self.font_change()

    # def font_change(self):
    #     font, ok = QtWidgets.QFontDialog.getFont()
    #     if ok:
    #         for name, obj in self.getmembers(self):
    #             if isinstance(obj, QtWidgets.QLabel):
    #                 obj.setFont(font)

    def slot_detectionChanged(self, detectionType : str):
        """Put this here so we can turn off detection when value changes.
        """
        logger.info(detectionType)
        self.slot_doAnalysis(detectionType)

    def slot_doAnalysis(self, detectionType : str):
        """Perform analysis based on which detection gui emitted the signal.
        
        Either detect in f0 or detect in diam.
        """
        logger.info(f'detectionType: {detectionType}')

        if detectionType == 'Detect Peaks (f/f_0)':
            ok = self.analyzeRoi()  # analyze the selected ROI
            if ok is not None:
                self.updateRoiIntensityPlot(doAnalysis=False)
        
        elif detectionType == 'Detect Diameter':
            # detect diameter from kym image
            roi = self.roiList.selectedRoi
            self.updateRoiDiameterPlot(roi, doAnalysis=True)
        
        elif detectionType == 'Detect Peaks (Diameter)':
            # detect peaks in 'Diameter (um)'
            ok = self.analyzeRoi(kymRoiDetection=self._detectionParamsDiameter)  # analyze the selected ROI
            if ok is not None:
                # update overlay of diameter plot (e.g. peak, threshold, etc)
                roi = self.roiList.selectedRoi
                self.updateRoiDiameterPlot2(roi)
                
                # if roi is None:
                #     logger.warning('no roi selected')
                #     return
                # dfPlot = self.roiList.kymRoiList[roi].getAnalysisResults(PeakDetectionTypes.diameter).df
                # self.diameterPlotItem.replotOverlays(dfPlot)

                # #
                # self.plotPeakClips(roi, doDiameter=True)

        else:
            logger.error(f'did not understand detectionType:{detectionType}')

    def isDirty(self):
        return self._kymRoiAnalysis._isDirty

    def closeEvent(self, event):
        logger.info('veto close if peak analysis is dirty')
        acceptAndContinue = True
        if self.isDirty():
            logger.info('   kym peak analysis is dirty, prompt to save')
            logger.info('TODO: this is not done ... finish writing code !!!')

            from sanpy.interface.bDialog import yesNoCancelDialog
            # saveDialog = yesNoCancelDialog('xxx is dirty', 'yyy save?')

            userResp = yesNoCancelDialog(
                "There is analysis that is not saved.\nDo you want to save?"
            )
            if userResp == QtWidgets.QMessageBox.Yes:
                # self.saveFilesTable()
                logger.warning('TODO: actually save kym roi peaks')
                self.saveAnalysis()
                acceptAndContinue = True
            elif userResp == QtWidgets.QMessageBox.No:
                acceptAndContinue = True
            else:  # userResp == QtWidgets.QMessageBox.Cancel:
                acceptAndContinue = False
        #
        # return acceptAndContinue
        if acceptAndContinue:
            event.accept()
        else:
            event.ignore()

    def loadAnalysis(self):
        """Load and add each roi in _kymRoiAnalysis
        """
        # logger.info(self._kymRoiAnalysis._roiDict.items())
        for _idx, (label, kymRoi) in enumerate(self._kymRoiAnalysis._roiDict.items()):
            ltrb = kymRoi.getRect()
            logger.info(f'adding roi {label} with rect {ltrb}')
            # self.addRoi(ltrb, doAnalysis=False, doSelect=False)

            doSelect = _idx == 0
            roi = self.roiList.addRoi(kymRoi, doSelect=doSelect)        
            # self.addIntensityPlot(roi, doAnalysis=False)
            if doSelect:
                self.updateRoiIntensityPlot(roi, doAnalysis=False)

    @property
    def path(self):
        return self._kymRoiAnalysis.path
    
    @property
    def imgData(self):
        return self._kymRoiAnalysis.imgData
    
    # @property
    # def _detectionDict(self):
    #     """Current selected ROI detection params.

    #     Used to detect peaks in int f0 (different from detecting peaks in diameter)
    #     """
    #     return self._detectionParams
    
    def mySetStatusbar(self, text):
        """Update the status bar with some text.
        """
        self.statusBar.showMessage(text)  # ,2000)

    @property
    def umPerPixel(self):
        return self._kymRoiAnalysis.umPerPixel
    
    @property
    def secondsPerLine(self):
        return self._kymRoiAnalysis.secondsPerLine
    
    def switchFile(self, imgData):

        # self._imgData = imgData

        logger.info(f'imgData:{imgData.shape}')

        self.roiList.switchFile(imgData)

        self.setAutoCOntrast()
        # from sanpy.kym.kymUtils import getAutoContrast
        # _min, _max = getAutoContrast(imgData)  # new 20240925, should mimic ImageJ
        # _min = int(_min)
        # _max = int(_max)
        # # logger.info(f'getAutoContrast -> {_min} {_max}')

        # self._minContrast = _min  #np.min(self.imgData)
        # self._maxContrast = _max  # int(np.max(self.imgData) / 2)

        # # update gui
        # self.minContrastSlider.setValue(self._minContrast)
        # self.maxContrastSlider.setValue(self._maxContrast)

        imageRect = self.getImageRect()  # l,b,h,w
        logger.info(f'    imageRect:{imageRect}')  # [0,0,5,113]

        # imgData = self.getContrastEnhance()

        axisOrder = "row-major"
        self.myImageItem.setImage(imgData,
                                    axisOrder=axisOrder,
                                    rect=imageRect
                                    )

        _levels = [self._minContrast, self._maxContrast]
        self.myImageItem.setLevels(_levels, update=True)

        # min/max in contrast slider
        self.tifMinLabel.setText(f'Img Min:{np.min(self.imgData)}')
        self.tifMaxLabel.setText(f'Img Max:{np.max(self.imgData)}')

        self.refreshScatter()

    def setAutoCOntrast(self):
        from sanpy.kym.kymUtils import getAutoContrast
        _min, _max = getAutoContrast(self.imgData)  # new 20240925, should mimic ImageJ
        # _min = int(_min)
        # _max = int(_max)

        self._minContrast = _min  #np.min(self.imgData)
        self._maxContrast = _max  # int(np.max(self.imgData) / 2)

        # update gui
        self.minContrastSlider.setValue(self._minContrast)
        self.maxContrastSlider.setValue(self._maxContrast)

    def _roi_changed(self, roi):
        self.updateRoiIntensityPlot(roi)

    def selectRoiByLabel(self, label : str):
        """Select an roi by text label
            To select overlapping ROI
        """
        # step though all labels and find the one with 'label'
        _selectRoi = None
        for roi, roiLabel in self.roiList.roiLabelList.items():
            roiLabelText = roiLabel.toPlainText()
            if roiLabelText == label:
                _selectRoi = roi
                break
        if _selectRoi is not None:
            logger.info(f'selecting roi label:"{label}"')
            # self.selectRoi(roi)
            self.roiList._selectRoi(roi)  # tell roi manager to select and will propogate
        else:
            logger.error(f'did not find roi label:"{label}"')

    def selectRoi(self, roi):
        # if roi is None:
        #     logger.warning('got None roi ???')
        #     return
        
        if roi is not None:
            self._detectionParams = self.roiList.getDetectionParams(roi, PeakDetectionTypes.f_f0)
            self._detectionParamsDiameter = self.roiList.getDetectionParams(roi, PeakDetectionTypes.diameter)

            self._updateDetectionParamGui()

        self.updateRoiIntensityPlot(roi, doAnalysis=False, refreshScatter=False)
        self.updateRoiDiameterPlot(roi, doAnalysis=False)
        self.updateRoiDiameterPlot2(roi)
        
    def _updateDetectionParamGui(self):
        """Update gui for KymDetectionToolbar.
        """
        logger.info('')
        self._detectionToolbar.setDetectionDict(self._detectionParams)
        self._diamDetectionToolbar.setDetectionDict(self._detectionParamsDiameter)
        self._kymDiamDetectToolbar.setDetectionDict(self._detectionParamsDiameter)

    def _buildContrastSliders(self) -> QtWidgets.QWidget:
        
        hBox = QtWidgets.QHBoxLayout()

        vBoxLeft = QtWidgets.QVBoxLayout()
        vBoxRight = QtWidgets.QVBoxLayout()

        hBox.addLayout(vBoxLeft)
        hBox.addLayout(vBoxRight)
        
        # color popup
        _colorList = ['Green', 'Red', 'Blue', 'Grey', 'Grey Invert', 'viridis', 'plasma', 'inferno']
        colorComboBox = QtWidgets.QComboBox()
        colorComboBox.addItems(_colorList)
        colorComboBox.setCurrentIndex(0)  # default to Green
        colorComboBox.currentTextChanged.connect(
            partial(self.setColorMap)
        )
        vBoxLeft.addWidget(colorComboBox)

        buttonName = 'Auto'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        vBoxLeft.addWidget(aButton)

        # image min/max
        hBoxImgMinMax = QtWidgets.QHBoxLayout()
        vBoxLeft.addLayout(hBoxImgMinMax)

        # self.tifMinLabel = QtWidgets.QLabel(f'Image Min:{np.min(self.imgData)}')
        # hBoxImgMinMax.addWidget(self.tifMinLabel)

        # self.tifMaxLabel = QtWidgets.QLabel(f'Max:{np.max(self.imgData)}')
        # hBoxImgMinMax.addWidget(self.tifMaxLabel)

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
        # myLambda = lambda chk, item=canvasName: self._userSelectCanvas(chk, item)
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

        # return as widget so we can call setVisible()
        aWidget = QtWidgets.QWidget()
        aWidget.setLayout(hBox)

        return aWidget
    
    def _onContrastSliderChanged(self, value, name):
        # logger.info(f'name:{name} value:{value}')

        if name == "minSlider":
            self._minContrast = value
            self.minContrastSpinBox.setValue(value)
        elif name == "maxSlider":
            self._maxContrast = value
            self.maxContrastSpinBox.setValue(value)

        # imgData = self.getContrastEnhance()
        # imageRect = self.getImageRect()  # l,b,h,w
        # axisOrder = "row-major"
        # self.myImageItem.setImage(imgData,
        #                             axisOrder=axisOrder,
        #                             rect=imageRect
        #                             )

        _levels = [self._minContrast, self._maxContrast]
        self.myImageItem.setLevels(_levels, update=True)

    def _buildTopToolbar(self) -> QtWidgets.QVBoxLayout:
        vBoxLayout = QtWidgets.QVBoxLayout()
        vBoxLayout.setAlignment(QtCore.Qt.AlignTop)
        
        hLayout = QtWidgets.QHBoxLayout()
        hLayout.setAlignment(QtCore.Qt.AlignLeft)
        vBoxLayout.addLayout(hLayout)

        # buttonName = 'ANALYZE'
        # aButton = QtWidgets.QPushButton(buttonName)
        # aButton.setToolTip('Perform the analysis')
        # aButton.clicked.connect(
        #     partial(self._on_button_click, buttonName, None)
        # )
        # hLayout.addWidget(aButton)

        buttonName = 'Save Analysis'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Save analysis for all roi(s)')
        aButton.clicked.connect(
            self.saveAnalysis
        )
        hLayout.addWidget(aButton)

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
        aButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        hLayout.addWidget(aButton)

        buttonName = 'Delete ROI'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Delete selected ROI')
        aButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        hLayout.addWidget(aButton)

        aCheckBoxName = 'ROI'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle roi plot on/off')
        aCheckBox.setChecked(True)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout.addWidget(aCheckBox)

        # second row
        hLayout1 = QtWidgets.QHBoxLayout()
        hLayout1.setAlignment(QtCore.Qt.AlignLeft)
        vBoxLayout.addLayout(hLayout1)

        aCheckBoxName = 'Detection'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle detection panel on/off')
        aCheckBox.setChecked(True)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout1.addWidget(aCheckBox)
                
        aCheckBoxName = 'Contrast'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle contrast sliders')
        aCheckBox.setChecked(False)  # hidden by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout1.addWidget(aCheckBox)

        aCheckBoxName = 'Sum Intensity (f0)'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle raw intensity plot')
        aCheckBox.setChecked(False)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout1.addWidget(aCheckBox)

        aCheckBoxName = 'Diameter'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle diameter plot')
        aCheckBox.setChecked(False)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout1.addWidget(aCheckBox)

        aCheckBoxName = 'Clips'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle peak clips on/off')
        aCheckBox.setChecked(False)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout1.addWidget(aCheckBox)

        aCheckBoxName = 'Scatter'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle scatter plot on/off')
        aCheckBox.setChecked(False)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout1.addWidget(aCheckBox)

        # show intensity under cursor
        # TODO: put this somewhere better
        # self.hoverLabel = QtWidgets.QLabel(None)
        # hLayout1.addWidget(self.hoverLabel, alignment=QtCore.Qt.AlignRight)

        return vBoxLayout
    
    def _on_combobox(self, name, value):
        """
        Parameters
        ----------
        detectionDict : dict
            Switches between multiple detection group boxes like (detect int, detect diam)
        """
        if self._blockSlots:
            # logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return
        
        logger.info(f'"{name}" value:{value}')
        
        # now handled in KymDetectionToolbar
        # if name == 'Polarity':
        #     detectionDict['polarity'] = value
        #     self.updateRoiIntensityPlot()  # update with selected

        # elif name == 'Background Subtract':
        #     # self._detectionDict['backgroundsubtract'] = value
        #     detectionDict['backgroundsubtract'] = value
        #     self.updateRoiIntensityPlot()  # update with selected

        # elif name == 'f0':
        #     # a popup of either manual or percentile
        #     detectionDict['f0ManualPercentile'] = value
        #     self.updateRoiIntensityPlot()  # update with selected

        #     # if in manual mode, do not allow setting the percentile
        #     # _showPercentile = value == 'Percentile'
        #     # self._detectionControls['f0 Percentile'].setEnabled(_showPercentile)

    def _on_checkbox_clicked(self, name, value = None):
        if self._blockSlots:
            # logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return

        if value > 0:
            value = 1
        
        # show/hide widgets
        if name == 'Contrast':
            self._contrastSliders.setVisible(value)

        elif name == 'Sum Intensity (f0)':
            self.rawIntensityPlotItem.setVisible(value)

        elif name == 'Diameter':
            self.diameterPlotItem.setVisible(value)

        elif name == 'Clips':
            self.peakClipsWidget.setVisible(value)

        elif name == 'Scatter':
            self.simpleScatter.setVisible(value)

        elif name == 'ROI':
            # toggle all roi
            self.roiList._toggleROI(value)

        elif name == 'Detection':
            self._mainDetectionWidget.setVisible(value)

        else:
            logger.info(f'did not understand name:"{name}"')

    def _on_button_click(self, name : str):
        logger.info(f'name:{name}')
        
        # if name == 'ANALYZE':
        #     self.analyzeRoi()  # analyze the selected ROI
        #     self.updateRoiIntensityPlot(doAnalysis=False)

        if name == 'Add ROI':
            self.addRoi()

        elif name =='Delete ROI':
            self.removeSelectedRoi()

        elif name == 'Auto':
            # auto contrast
            self.setAutoCOntrast()

        elif name == 'Plot Quality':
            _selectedRoi = self.roiList.selectedRoi
            if _selectedRoi is not None:
                _kymRoi = self.roiList.kymRoiList[_selectedRoi]
                from sanpy.kym.kymRoiAnalysis import plotDetectionResults
                plotDetectionResults(_kymRoi)

    def removeSelectedRoi(self):
        """Remove from manager and plot.
        """
        
        roi = self.roiList.removeSelectedRoi(self._kymRoiAnalysis)
        
        # if roi is not None:
        #     self.deleteIntensityPlot(roi)

    def addRoi(self, ltrbRoi = None, doAnalysis=True, doSelect=True):
        
        # add to backend with default ltrb and use our current detection params
        _newRoi = self._kymRoiAnalysis.addROI(kymRoiDetection=self._detectionParams)  # v2 backend

        roi = self.roiList.addRoi(_newRoi, doSelect=doSelect)
        
        # self.addIntensityPlot(roi, doAnalysis=doAnalysis)
        
        self.mySetStatusbar(f'Added ROI {_newRoi}')
        return roi
    
    def getImageRect(self):
        """Get image rect with (x,y) scale.
        
        Notes
        -----
        This breaks when umPerPixel is fractional.
            Trying to fix by returning float.
        """
        left = 0
        top = self.imgData.shape[0] * self.umPerPixel
        right = self.imgData.shape[1] * self.secondsPerLine
        bottom = 0

        width = right - left
        height = top - bottom

        return left, bottom, width, height  # x, y, w, h

    def _buildUI(self):

        self.myVBoxLayout = QtWidgets.QVBoxLayout()
        self.myVBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        # needed for QMainWindow
        mainWidget = QtWidgets.QWidget()
        mainWidget.setLayout(self.myVBoxLayout)
        self.setCentralWidget(mainWidget)

        mainHBox = QtWidgets.QHBoxLayout()  # left is detection, right is plots
        self.myVBoxLayout.addLayout(mainHBox)
        
        # vBoxPlot is buttons, then all the plots
        vBoxPlot = QtWidgets.QVBoxLayout()
        mainHBox.addLayout(vBoxPlot)

        self._topToolbar = self._buildTopToolbar()  # one row with file name, image params
        vBoxPlot.addLayout(self._topToolbar)

        self._contrastSliders = self._buildContrastSliders()
        self._contrastSliders.setVisible(False)
        vBoxPlot.addWidget(self._contrastSliders)

        # kymograph
        self.view = pg.GraphicsLayoutWidget()

        # pyqtgraph.graphicsItems.PlotItem
        row = 0
        colSpan = 1
        rowSpan = 1
        self.kymographPlot = self.view.addPlot(
            row=row, col=0, rowSpan=rowSpan, colSpan=colSpan
        )

        self.kymographPlot.setLabel("left", "Pixels (um)", units="")
        self.kymographPlot.setLabel("bottom", "Time (s)", units="")

        self.kymographPlot.setDefaultPadding()
        self.kymographPlot.enableAutoRange()
        self.kymographPlot.setMouseEnabled(x=True, y=False)
        self.kymographPlot.hideButtons()  # hide the little 'A' button to rescale axis
        self.kymographPlot.setMenuEnabled(False)  # turn off right-click menu
        
        # switching to PyMapManager style contrast with setLevels()
        self.myImageItem = pg.ImageItem(self.imgData, axisOrder = "row-major")  # need transpose for row-major
        self.setColorMap('Green')

        # logger.warning('--->>> tryin ColorBarItem')
        self.aColorBar = pg.ColorBarItem(colorMap='inferno')
        self.aColorBar.setImageItem(self.myImageItem)

        self.kymographPlot.addItem(self.myImageItem, ignorBounds=True)

        # redirect hover to self (to display intensity
        self.myImageItem.hoverEvent = self._hoverEvent

        # left/right scatter on top of kymograph
        self._overlayKymDict = {}
        self._overlayKymDict['leftDiamOverlay'] = self.kymographPlot.plot(name="leftDiamOverlay",
                                                  pen=None,
                                                  symbol='o',
                                                  symbolPen=None,
                                                  symbolSize=5,
                                                  symbolBrush=pg.mkBrush(0, 250, 0, 220)
                                                  )
        self._overlayKymDict['rightDiamOverlay'] = self.kymographPlot.plot(name="rightDiamOverlay",
                                                  pen=None,
                                                  symbol='o',
                                                  symbolPen=None,
                                                  symbolSize=5,
                                                  symbolBrush=pg.mkBrush(250, 0, 0, 220)
                                                  )

        vBoxPlot.addWidget(self.view)
    
        #
        # raw intensity plot (to manually set f0)
        self.rawIntensityPlotItem = pg.PlotWidget()
        self.rawIntensityPlotItem.setDefaultPadding()
        self.rawIntensityPlotItem.enableAutoRange()
        self.rawIntensityPlotItem.setMouseEnabled(x=True, y=False)
        self.rawIntensityPlotItem.hideButtons()  # hide the little 'A' button to rescale axis

        self.rawIntensityPlotItem.setLabel("left", 'Sum Intensity', units="")
        self.rawIntensityPlotItem.setLabel("bottom", 'Time (s)', units="")
        self.rawIntensityPlotItem.setXLink(self.kymographPlot)
        self.rawIntensityPlotItem.contextMenuEvent = self.myRawContextMenu  # rewire right-click to custom function
        self.rawIntensityPlotItem.setVisible(False)  # initally hidden

        self.rawIntensityPlot = self.rawIntensityPlotItem.plot(name="rawIntensityPlot",
                                                        # pen=pg.mkPen('c', width=5),
                                                        #   symbol='o',
                                                        #   brush=pg.mkBrush(100, 255, 100, 220),
                                                        )   

        self.rawIntensity_f0_line = pg.InfiniteLine(angle=0,
                                                    movable=False,
                                                    pen = pg.mkPen('c', width=2),
                                                    # label=f'f0={f0Value}',
                                                    label='f0={value}',
                                                    labelOpts={'position':0.05},
                                                    )
        self.rawIntensityPlotItem.addItem(self.rawIntensity_f0_line)

        self._rawPlotCursors = sanpyCursors(self.rawIntensityPlotItem, showCursorD=False)
        self._rawPlotCursors.toggleCursors(False)  # initially hidden
        self._rawPlotCursors._showCursorA = False
        self._rawPlotCursors._showCursorB = False
        self._rawPlotCursors.signalCursorDragged.connect(self.mySetStatusbar)

        vBoxPlot.addWidget(self.rawIntensityPlotItem)

        #
        # 4) sum intensity of each line scan (actually our int/f0 plot)
        self.sumIntensityPlotItem = KymPlotWidget()
        self.sumIntensityPlotItem.sumIntensityPlotItem.setLabel("left", 'Santana Intensity (f/f0)', units="")
        self.sumIntensityPlotItem.setXLink(self.kymographPlot)
        self.sumIntensityPlotItem.signalCursorMove.connect(self.mySetStatusbar)
        vBoxPlot.addWidget(self.sumIntensityPlotItem)

        # diameter plot
        self.diameterPlotItem = KymPlotWidget()
        self.diameterPlotItem.sumIntensityPlotItem.setLabel("left", 'Dimaeter (um)', units="")
        self.diameterPlotItem.setXLink(self.kymographPlot)
        self.diameterPlotItem.signalCursorMove.connect(self.mySetStatusbar)
        vBoxPlot.addWidget(self.diameterPlotItem)

        vBoxDetectionLayout_left = QtWidgets.QVBoxLayout()
        vBoxDetectionLayout_left.setAlignment(QtCore.Qt.AlignTop)
        self._mainDetectionWidget = QtWidgets.QWidget()
        self._mainDetectionWidget.setLayout(vBoxDetectionLayout_left)
        mainHBox.addWidget(self._mainDetectionWidget)

        # self._detectionToolbar = self._builtDetectionToolbar('Detect Peaks (f/f_0)', self._detectionParams)
        groupName = 'Detect Peaks (f/f_0)'
        detectionDict = self._detectionParams
        self._detectionToolbar = KymDetectionGroupBox(detectionDict=detectionDict, groupName=groupName)
        self._detectionToolbar.signalDetectionParamChanged.connect(self.slot_detectionChanged)
        self._detectionToolbar.signalDetection.connect(self.slot_doAnalysis)
        vBoxDetectionLayout_left.addWidget(self._detectionToolbar)

        #
        # a toolbar (group) to detect diameter from kym image
        from sanpy.kym.interface.kymDiamToolbar import KymDiameterToolbar
        groupName = 'Detect Diameter'
        detectionDict = self._detectionParamsDiameter
        self._kymDiamDetectToolbar = KymDiameterToolbar(detectionDict=detectionDict, groupName=groupName)
        self._kymDiamDetectToolbar.signalDetectionParamChanged.connect(self.slot_detectionChanged)
        self._kymDiamDetectToolbar.signalDetection.connect(self.slot_doAnalysis)
        vBoxDetectionLayout_left.addWidget(self._kymDiamDetectToolbar)

        groupName = 'Detect Peaks (Diameter)'
        detectionDict = self._detectionParamsDiameter
        # self._diamDetectionToolbar = self._builtDetectionToolbar('Detect Peaks (Diameter)', self._detectionParams)
        self._diamDetectionToolbar = KymDetectionGroupBox(detectionDict=detectionDict, groupName=groupName)
        self._diamDetectionToolbar.setWidgetEnabled('Exponential Detrend', False)
        self._diamDetectionToolbar.setWidgetEnabled('f0 Type', False)
        self._diamDetectionToolbar.setWidgetEnabled('f0 Percentile', False)
        self._diamDetectionToolbar.signalDetectionParamChanged.connect(self.slot_detectionChanged)
        self._diamDetectionToolbar.signalDetection.connect(self.slot_doAnalysis)
        vBoxDetectionLayout_left.addWidget(self._diamDetectionToolbar)

        _spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        vBoxDetectionLayout_left.addItem(_spacerItem)

        #
        vBoxForClipsScatterTable = QtWidgets.QVBoxLayout()

        _tmpWidget = QtWidgets.QWidget()
        _tmpWidget.setLayout(vBoxForClipsScatterTable)

        self.peakClipsWidget = KymRoiClipsWidget()
        self.peakClipsWidget.setVisible(False)
        vBoxForClipsScatterTable.addWidget(self.peakClipsWidget)

        #
        # simple scatter plot
        self.simpleScatter = SimpleRoiScatter()
        self.simpleScatter.setVisible(False)
        vBoxForClipsScatterTable.addWidget(self.simpleScatter)

        #
        # file list as a dock
        self.fileDock = QtWidgets.QDockWidget('Files')
        self.fileDock.setWidget(_tmpWidget)
        self.fileDock.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures | \
                                  QtWidgets.QDockWidget.DockWidgetVerticalTitleBar)
        self.fileDock.setFloating(False)
        self.fileDock.setTitleBarWidget(QtWidgets.QWidget())
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.fileDock)
    
    def setColorMap(self, colorMap : str):
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

        self.myImageItem.setColorMap(cm)
    
    def analyzeRoiDiam(self, roi=None):
        if roi is None:
            roi = self.roiList.selectedRoi  # pyqtgraph ROI()
        if roi is None:
            logger.info('please select an roi to analyze')
            return

        logger.info('   === === === WIDGET PERFORMING ROI ANALYSIS === ===> diam')

        # this creates 3x traces (left, right, diameter)
        self.roiList.kymRoiList[roi].detectDiam()
    
    def analyzeRoi(self, roi = None, kymRoiDetection : KymRoiDetection = None, doQuick=False):
        """Analyze one roi e.g. detect peaks.
        """

        if roi is None:
            roi = self.roiList.selectedRoi  # pyqtgraph ROI()
        
        if roi is None:
            logger.info('please select an roi to analyze')
            return

        logger.info('   === === === WIDGET PERFORMING ROI ANALYSIS === ===> f0')

        ok = self.roiList.kymRoiList[roi].peakDetect(kymRoiDetection=kymRoiDetection, verbose=False)

        # from sanpy.kym.kymRoiAnalysis import plotDetectionResults
        # kymRoi = self.roiList.kymRoiList[roi]
        # plotDetectionResults(kymRoi)

        return ok
    
    def _msToBin(self, msValue : float) -> int:
        """Convert ms to nearest bin using round.
        """
        _retBin1 = msValue / 1000 / self.secondsPerLine
        _retBin2 = int(round(_retBin1))
        # logger.info(f'msValue:{msValue} _retBin1:{_retBin1} _retBin2:{_retBin2}')
        return _retBin2
    
    def getDataFrame(self, peakDetectionType : PeakDetectionTypes, roi = None):
        """Get results df for one roi or all roi (use roi=None).
        """
        if roi is not None:
            # return self._analysisDf[roi].df
            return self.roiList.getAnalysisResults(roi, peakDetectionType).df
        else:
            columns = list(KymRoiResults.analysisDict.keys())
            df = pd.DataFrame(columns=columns)  # empty df with proper columns
            for _roiIdx, oneRoi in enumerate(self.roiList.kymRoiList.keys()):
                oneDf = self.roiList.getAnalysisResults(oneRoi, peakDetectionType).df
                if _roiIdx == 0:
                    df = oneDf
                else:
                    df = pd.concat([df, oneDf], axis=0)
            try:
                df = df.reset_index(drop=True)
            except (ValueError) as e:
                logger.error(e)
                logger.error('df is:')
                print(df)

            return df

    def saveAnalysis(self):
        """Save all peak analysis into one csv file.

        This includes a header with roi [l,t,r,b] and detection parameters used.
        """
                
        _saved = self._kymRoiAnalysis.saveAnalysis()

        if _saved:
            self.mySetStatusbar(f'Saved analysis for {self.path}')
        else:
            self.mySetStatusbar('Nothing to save')

    def update_fo_plot(self, roi=None):
        if roi is None:
            roi = self.roiList.selectedRoi
            if roi is None:
                logger.warning('no roi selected')
                return

        self.rawIntensityPlot.setData([], [])

        timeSec = self.roiList.getAnalysisTrace(roi, 'timeSec')
        intDetrend = self.roiList.getAnalysisTrace(roi, 'intDetrend')

        if intDetrend is None:
            return
        
        self.rawIntensityPlot.setData(timeSec, intDetrend)

        # logger.info(f'self._detectionParams {type(self._detectionParams)}')
        self._detectionParams.printValues()

        f0Value = self._detectionParams['f0 Value']
        self.rawIntensity_f0_line.setPos(round(f0Value,2))

        self._rawPlotCursors._showInView()

    def updateRoiDiameterPlot(self, roi=None, doAnalysis=True):
        """Analyze and then update diameter from kym image.
        
        This generates (left, right, and diam.
        Diam is then peak detected.
        """
        if roi is None:
            roi = self.roiList.selectedRoi
            if roi is None:
                logger.warning('no roi selected')
                return

        # set selected roi label
        _roiLabelText = self.roiList.roiLabelList[roi].toPlainText()
        # self._selectedRoiLabel.setText(f'ROI: {_roiLabelText}')
        _txt = f'ROI: {_roiLabelText}'
        self.diameterPlotItem.setRoiLabelText(_txt)

        #
        # find left/right diam from kymograph
        if doAnalysis:
            self.analyzeRoiDiam(roi)

        #
        # update plots
        timeSec = self.roiList.getAnalysisTrace(roi, 'timeSec')

        leftDiameterUm = self.roiList.getAnalysisTrace(roi, 'Left Diameter (um)')
        rightDiameterUm = self.roiList.getAnalysisTrace(roi, 'Right Diameter (um)')
        diameterUm = self.roiList.getAnalysisTrace(roi, 'Diameter (um)')

        # left/right on kym image
        self._overlayKymDict['leftDiamOverlay'].setData([], [])
        self._overlayKymDict['rightDiamOverlay'].setData([], [])
        # diameter plot
        self.diameterPlotItem.setData([], [])

        if leftDiameterUm is None:
            logger.info('no diameter to plot')
            return
        
        # left/right on kym image
        self._overlayKymDict['leftDiamOverlay'].setData(timeSec, leftDiameterUm)
        self._overlayKymDict['rightDiamOverlay'].setData(timeSec, rightDiameterUm)
        # diameter plot
        self.diameterPlotItem.setData(timeSec, diameterUm)

    def updateRoiDiameterPlot2(self, roi : KymRoi):
        # update overlay of diameter plot (e.g. peak, threshold, etc)
        # roi = self.roiList.selectedRoi
        if roi is None:
            logger.warning('no roi selected')
            return
        dfPlot = self.roiList.kymRoiList[roi].getAnalysisResults(PeakDetectionTypes.diameter).df
        self.diameterPlotItem.replotOverlays(dfPlot)

        #
        self.plotPeakClips(roi, doDiameter=True)

    def updateRoiIntensityPlot(self, roi=None, doAnalysis=True, refreshScatter=True):
        """Update f/f0 intensity plot when user adjusts roi.
        """
        if roi is None:
            roi = self.roiList.selectedRoi
            if roi is None:
                logger.warning('no roi selected')
                return

        self.sumIntensityPlotItem.clearPlot()

        # set selected roi label
        _roiLabelText = self.roiList.roiLabelList[roi].toPlainText()
        _txt = f'ROI: {_roiLabelText}'
        self.sumIntensityPlotItem.setRoiLabelText(_txt)

        # perform analysis
        logger.warning(f'turned off auto analysis - implementing "Analyze" button doAnalysis:{doAnalysis}')
        if doAnalysis:
            ok = self.analyzeRoi(roi, doQuick=True)
            if ok is None:
                logger.error('did not perform analysis')
                return
                             
        # v2
        timeSec = self.roiList.getAnalysisTrace(roi, 'timeSec')
        # int_df_f0 = self.roiList.getAnalysisTrace(roi, 'int_df_f0')
        f_f0 = self.roiList.getAnalysisTrace(roi, 'f_f0')
        if f_f0 is None:
            logger.error('f_f0 is None -->> abort')
            return
        
        df_f0 = f_f0

        if timeSec is None:
            logger.error('-->> NO ANALYSIS YET')
            return

        # self.sumIntensityPlot.setData(timeSec, df_f0, )  # fill with nan
        self.sumIntensityPlotItem.setData(timeSec, df_f0, )  # fill with nan

        dfPlot = self.roiList.kymRoiList[roi].getAnalysisResults(PeakDetectionTypes.f_f0).df
        self.sumIntensityPlotItem.replotOverlays(dfPlot)

        #
        # update other widgets
        #
        
        # raw intensity plot (to manually set f0)
        self.update_fo_plot(roi)

        #
        # peak clips
        self.plotPeakClips(roi, doDiameter=False)

        #
        # refresh scatter plot
        if refreshScatter:
            self.refreshScatter()  # update all

    def refreshScatter(self, roi = None):
        """Refresh seaborn scatter plot widget.
        """
        if roi is not None:
            # df = self._analysisDf[roi].df
            df = self.roiList.getAnalysisResults(roi, PeakDetectionTypes.f_f0).df
        else:
            df = self.getDataFrame(PeakDetectionTypes.f_f0)  # get full dataframe across all 'roi number'
        
        # logger.info('refresh with df')
        # print(df)

        self.simpleScatter.replot(df)

    def plotPeakClips(self, roi, doDiameter=False):

        if doDiameter:
            yPlot = self.roiList.getAnalysisTrace(roi, 'Diameter (um)')
            if yPlot is None:
                logger.warning('plotting peak clips did not get "Diameter (um)" trace')
                return
            
            # analysis results
            dfPlot = self.roiList.getAnalysisResults(roi, PeakDetectionTypes.diameter).df
            xPeaks = dfPlot['Peak Bin']

            plusMinBins = self._msToBin(self._detectionParamsDiameter['Decay (ms)'])
            # peak clips
            self.peakClipsWidget.plotPeakClips(yPlot, xPeaks, self.secondsPerLine, plusMinBins, doDiameter=True)

        else:
            yPlot = self.roiList.getAnalysisTrace(roi, 'f_f0')
            if yPlot is None:
                logger.warning('plotting peak clips did not get "f_f0" trace')
                return
            
            # analysis results
            dfPlot = self.roiList.getAnalysisResults(roi, PeakDetectionTypes.f_f0).df
            xPeaks = dfPlot['Peak Bin']

            plusMinBins = self._msToBin(self._detectionParams['Decay (ms)'])
            # peak clips
            self.peakClipsWidget.plotPeakClips(yPlot, xPeaks, self.secondsPerLine, plusMinBins)

    def _hoverEvent(self, event):
        """Hover on image -> update status in QMainWindow
        """
        if event.isExit():
            return
        
        xPos = event.pos().x()
        yPos = event.pos().y()

        xPos = int(xPos)
        yPos = int(yPos)

        try:
            intensity = self.imgData[yPos, xPos]  # flipped
        except (IndexError) as e:
            intensity = 'None'
        
        intensity = f'{xPos} {yPos} intensity:{intensity}'

        self.mySetStatusbar(intensity)

    def _resetZoom(self, doEmit=True):
        
        # order matter, do sum then image
        # 
        self.sumIntensityPlotItem.autoRange()  # item=self._roiIntensityPlot[roi]
        self.rawIntensityPlotItem.autoRange()
        self.diameterPlotItem.autoRange()

        self.kymographPlot.autoRange(item=self.myImageItem)

    def keyReleaseEvent(self, event):
    
        key = event.key()
        isShift = key == QtCore.Qt.Key_Shift
        
        if isShift:
            # default is x-zoom
            self.kymographPlot.setMouseEnabled(x=True, y=False)
            self.sumIntensityPlotItem.setMouseEnabled(x=True, y=False)
            self.rawIntensityPlotItem.setMouseEnabled(x=True, y=False)
            self.diameterPlotItem.setMouseEnabled(x=True, y=False)
    
    def keyPressEvent(self, event):
        """Respond to user key press.

        Parameters
        ----------
        event : PyQt5.QtGui.QKeyEvent
        """
        key = event.key()
        text = event.text()
        
        isShift = event.modifiers() == QtCore.Qt.ShiftModifier
        isAlt = event.modifiers() == QtCore.Qt.AltModifier
        isCtrl = event.modifiers() == QtCore.Qt.ControlModifier
        
        logger.info(f'key:{key} text:{text} isCtrl:{isCtrl} isAlt:{isAlt} isShift:{isShift}')

        if isShift:
            # default is x-zoom
            # self.kymographPlot.setMouseEnabled(x=True, y=False)
            # switch it to y-zoom
            self.kymographPlot.setMouseEnabled(x=False, y=True)
            self.sumIntensityPlotItem.setMouseEnabled(x=False, y=True)
            self.rawIntensityPlotItem.setMouseEnabled(x=False, y=True)
            self.diameterPlotItem.setMouseEnabled(x=False, y=True)

        if key in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            self._resetZoom()

        elif key == QtCore.Qt.Key.Key_Escape:
            self.roiList._selectRoi(None)

        elif key in [QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace]:
            #_roi = self.roiList.removeSelectedRoi()
            self.removeSelectedRoi()

        elif key in [QtCore.Qt.Key_Plus, QtCore.Qt.Key_Equal]:
            #self.roiList.addRoi()
            self.addRoi()

        elif key in [QtCore.Qt.Key_W] and isCtrl:
            self.simpleScatter.copyTableToClipboard()

        elif isCtrl and key == QtCore.Qt.Key_S:
            self.saveAnalysis()

        # elif key == QtCore.Qt.Key_S:
        #     self.savePlotItemAs()

        else:
            logger.warning('did not understand user key press')

    def savePlotItemAs(self, plotItem : pg.graphicsItems.PlotItem, name : str):
        """Save a plot item to file.
        """
        import pyqtgraph.exporters
        # filename = 'filename.png'
        # filename = 'filename.pdf'  # does not work
        # filename = 'filename.tif'
        # filename = 'filename.svg'

        # roi = self.roiList.selectedRoi
        # if roi is None:
        #     return
        
        saveFolder = self._kymRoiAnalysis._getSaveFolder(createFolder=True)
        
        _, _file = os.path.split(self.path)
        _file, _ = os.path.splitext(_file)
        _file = _file + '-' + name + '.png'
        savePath = os.path.join(saveFolder, _file)

        logger.info(f'saving {name} to {savePath}')

        exporter = pg.exporters.ImageExporter(plotItem)
        exporter.export(savePath)
        _ret = f'Saved "{name}" to {savePath}'
        return _ret
    
    def myRawContextMenu(self, event):
        """Context menu for raw plot item.
        
        Used to set f0 from cursors.
        See also _contextMenu() for global widget context menus.
        """
        # menu = QtWidgets.QMenu(self)
        # someAction = menu.addAction('New_Item')

        contextMenu = QtWidgets.QMenu()
        
        contextMenu.addAction('Full Zoom')
        contextMenu.addSeparator()

        _cursorsShowing = self._rawPlotCursors.cursorsAreShowing()
        
        cCursorValue = self._rawPlotCursors._cCursorVal

        cursorAction = QtWidgets.QAction('Cursors')
        cursorAction.setCheckable(True)
        cursorAction.setChecked(_cursorsShowing)
        contextMenu.addAction(cursorAction)
        contextMenu.addSeparator()

        #
        f0ManualPercentile = self._detectionParams['f0 Type']  # in (Manual, Percentile)
        f0Manual = f0ManualPercentile == 'Manual'
        
        f0Action = QtWidgets.QAction(f'Set f0 to {cCursorValue}')
        f0Action.setEnabled(_cursorsShowing and f0Manual)
        contextMenu.addAction(f0Action)

        action = contextMenu.exec_(event.globalPos())
        if action is None:
            return
        
        # respond to menu selection
        _ret = ''
        actionText = action.text()
        if actionText == 'Full Zoom':
            self._resetZoom()
            _ret = 'Reset zoom'

        elif actionText == 'Cursors':
            _checked = cursorAction.isChecked()
            # self._sanpyCursors.toggleCursors(_checked)
            self._rawPlotCursors.toggleCursors(_checked)

        elif action == f0Action:
            logger.info(f'TODO: set f0 to cCursorValue:{cCursorValue}')
            self._detectionParams['f0 Value'] = cCursorValue
            self.updateRoiIntensityPlot(doAnalysis=True)

        self.mySetStatusbar(_ret)

    def _contextMenu(self, pos):
        """Context menu for entire widget.
        
        See also myRawContextMenu.
        """
        logger.info('')

        selectedRoi = self.roiList.selectedRoi

        # build menu
        contextMenu = QtWidgets.QMenu()
        contextMenu.addAction('Full Zoom')
        contextMenu.addSeparator()

        # logger.warning('PUT CURSOR MENU INTO NEW KymPlotWidget')
        # cursorAction = QtWidgets.QAction('Cursors')
        # cursorAction.setCheckable(True)
        # cursorAction.setChecked(self._sanpyCursors.cursorsAreShowing())
        # contextMenu.addAction(cursorAction)
        # contextMenu.addSeparator()

        # contextMenu.addAction('Save Kym Image ...')

        # saveSumPlotAction = QtWidgets.QAction('Save Sum Plot ...')
        # saveSumPlotAction.setEnabled(selectedRoi is not None)
        # contextMenu.addAction(saveSumPlotAction)

        # saveClipsAction = QtWidgets.QAction('Save Clips ...')
        # saveClipsAction.setEnabled(selectedRoi is not None)
        # contextMenu.addAction(saveClipsAction)

        # contextMenu.addSeparator()
        # contextMenu.addAction('Copy Stats Table ...')

        # add menu to select an roi (use this when they visually overlap)
        contextMenu.addSeparator()
        for k, v in self.roiList.roiList.items():
            # logger.info(f'qqq roi menu {k} {v}')
            _key = self.roiList.roiList[k]
            roiLabelText = self.roiList.roiLabelList[k].toPlainText()
            # print(f'   roiLabelText:{roiLabelText}')
            contextMenu.addAction(f'Select ROI: {roiLabelText}')

        # show menu
        pos = self.mapToGlobal(pos)
        action = contextMenu.exec_(pos)
        if action is None:
            return
        
        # respond to menu selection
        _ret = ''
        actionText = action.text()
        if actionText == 'Full Zoom':
            self._resetZoom()
            _ret = 'Reset zoom'

        elif actionText == 'Cursors':
            _checked = cursorAction.isChecked()
            self._sanpyCursors.toggleCursors(_checked)
            # self._rawPlotCursors.toggleCursors(_checked)

        # elif actionText == 'Save Kym Image ...':
        #     _ret = self.savePlotItemAs(self.kymographPlot, 'kym-image')

        # elif actionText == 'Save Sum Plot ...':
        #     roiLabelText = self.roiList.roiLabelList[selectedRoi].toPlainText()
        #     _ret = self.savePlotItemAs(self.sumIntensityPlotItem.plotItem, f'sum-plot-roi-{roiLabelText}')

        # elif actionText == 'Save Clips ...':
        #     roiLabelText = self.roiList.roiLabelList[selectedRoi].toPlainText()
        #     _ret = self.savePlotItemAs(self.peakClipsWidget.peakClipPlotItem.plotItem, f'clip-plot-{roiLabelText}')

        # elif actionText == 'Copy Stats Table ...':
        #     _ret = self.simpleScatter.copyTableToClipboard()
        
        # special case on transition to backend
        elif actionText.startswith('Select ROI'):
            _, roiInt = actionText.split(': ')
            logger.info(f'roiInt:{roiInt}')
            self.selectRoiByLabel(roiInt)

        self.mySetStatusbar(_ret)