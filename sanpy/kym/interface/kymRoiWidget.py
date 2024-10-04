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

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, KymRoi  # v2

from sanpy.kym.kymRoiDetection import KymRoiDetection
from sanpy.kym.kymRoiResults import KymRoiResults
from sanpy.kym.interface.kymRoiScatter import SimpleRoiScatter
from sanpy.kym.interface.kymRoiClipsWidget import KymRoiClipsWidget

# from sanpy.kym.mpLineProfile import roiLineProfilePool

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
    
    def getDetectionParams(self, roi):
        return self.kymRoiList[roi].detectionParams
    
    def getAnalysisResults(self, roi):
        return self.kymRoiList[roi].analysisResults
    
    def getImgData(self, roi):
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

        # v2 refactor these, we will just have one for the selected roi
        # self._roiIntensityPlot = {}  # keys are roi

        # this switches for each selected ROI
        self._detectionParams = KymRoiDetection()

        self._blockSlots = False
        
        self._buildUI()

        # self._backgroundRoi = oneRoiRect(pos=(0,0), size=(100,100),
        #                                  imageItem=self.myImageItem,
        #                                  imgData=self._imgData,
        #                                  label='Background')
        # self._backgroundRoi.signalRoiChanged.connect(self._background_roi_changed)

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
        logger.info(self._kymRoiAnalysis._roiDict.items())
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
    
    @property
    def _detectionDict(self):
        """Current selected ROI detection params.
        """
        return self._detectionParams
    
    def mySetStatusbar(self, text):
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

    # SELECT AN ROI BY ITS LABEL !!!! SIMPLE !!!
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
            # don't update on cancel roi selection
            try:
                # self._detectionParams = self._analysisResults[roi]['detectionParams']
                self._detectionParams = self.roiList.getDetectionParams(roi)
                self._updateDetectionParamGui()
            except (KeyError) as e:
                logger.error(f'TODO: ok on load -->> {e}')

        self.updateRoiIntensityPlot(roi, doAnalysis=False, refreshScatter=False)

    def _updateDetectionParamGui(self):
        # {'ltrb': [0, 545, 2999, 383], 'medianfilter': True, 'medianfilterkernel': 3, 'filter': True, 'prominence': 3.9999999999999996, 'width': 6, 'distance': 100, 'thresh_rel_height': 0.75}
        
        # ['Median Filter', 'Savitzky-Golay', 'Prominence', 'Width', 'Distance']
        # logger.info(self._detectionControls.keys())

        self._blockSlots = True
        
        detectionParamDict = self._detectionParams
        
        # logger.info('')
        # print(detectionParamDict.printValues())

        # logger.warning(f"TODO: fix update of polarity detectionParamDict['polarity'] is {detectionParamDict['polarity']}")

        if detectionParamDict['polarity'] == 'Pos':
            self._detectionControls['Polarity'].setCurrentIndex(0)
        elif detectionParamDict['polarity'] == 'Neg':
            self._detectionControls['Polarity'].setCurrentIndex(1)
        else:
            logger.error(f"did not understand polarity {detectionParamDict['polarity']}")


        self._detectionControls['Median Filter'].setChecked(detectionParamDict['medianfilter'])  # boolean
        self._detectionControls['Median Filter Kernel'].setValue(detectionParamDict['medianfilterkernel'])  # must be odd
        self._detectionControls['Savitzky-Golay'].setChecked(detectionParamDict['filter'])
        self._detectionControls['Bin Lines'].setValue(detectionParamDict['binLineScans'])
        self._detectionControls['Prominence'].setValue(detectionParamDict['prominence'])
        self._detectionControls['Width (ms)'].setValue(detectionParamDict['width (ms)'])
        self._detectionControls['Distance (ms)'].setValue(detectionParamDict['distance (ms)'])

        # new colin retreat
        self._detectionControls['f0 Percentile'].setValue(detectionParamDict['f0 Percentile'])

        if detectionParamDict['f0ManualPercentile'] == 'Manual':
            self._detectionControls['f0'].setCurrentIndex(0)
            self._detectionControls['f0 Percentile'].setEnabled(False)
        elif detectionParamDict['f0ManualPercentile'] == 'Percentile':
            self._detectionControls['f0'].setCurrentIndex(1)
            self._detectionControls['f0 Percentile'].setEnabled(True)
        else:
            logger.error(f"did not understand f0ManualPercentile {detectionParamDict['f0ManualPercentile']}")

        backgroundSubtractTypes = KymRoiDetection.backgroundSubtractTypes
        backgroundsubtract = detectionParamDict['backgroundsubtract']
        _idx = backgroundSubtractTypes.index(backgroundsubtract)
        self._detectionControls['Background Subtract'].setCurrentIndex(_idx)

        self._detectionControls['Exp Detrend'].setChecked(detectionParamDict['doExpDetrend'])  # boolean

        # self._detectionControls['thresh_rel_height'].setValue(detectionParamDict['thresh_rel_height'])  # boolean


        self._blockSlots = False

    def _builtDetectionToolbar(self) -> QtWidgets.QVBoxLayout:
        vLayout = QtWidgets.QVBoxLayout()
        vLayout.setAlignment(QtCore.Qt.AlignTop)

        #
        hLayout0 = QtWidgets.QHBoxLayout()
        hLayout0.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout0)

        self._detectionControls = {}  # a dict of detection controls so we can update them on roi selection in _updateDetectionParamGui

        #
        aName = 'Polarity'
        aLabel = QtWidgets.QLabel(aName)
        hLayout0.addWidget(aLabel)
        
        aComboBox = QtWidgets.QComboBox()
        aComboBox.setToolTip(self._detectionDict.getDescription('polarity'))
        aComboBox.addItems(['Pos', 'Neg'])
        aComboBox.currentTextChanged.connect(
            partial(self._on_combobox, aName)
        )
        hLayout0.addWidget(aComboBox)
        self._detectionControls[aName] = aComboBox

        aCheckBoxName = 'Median Filter'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip(self._detectionDict.getDescription('medianfilter'))
        aCheckBox.setChecked(self._detectionDict['medianfilter'])
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout0.addWidget(aCheckBox)
        self._detectionControls[aCheckBoxName] = aCheckBox

        spinBoxName = 'Median Filter Kernel'
        aSpinBox = QtWidgets.QSpinBox()
        aSpinBox.setToolTip(self._detectionDict.getDescription('medianfilterkernel'))
        aSpinBox.setRange(1,100)
        aSpinBox.setSingleStep(2)
        aSpinBox.setValue(self._detectionDict['medianfilterkernel'])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout0.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        aCheckBoxName = 'Savitzky-Golay'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip(self._detectionDict.getDescription('filter'))
        aCheckBox.setChecked(self._detectionDict['filter'])
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout0.addWidget(aCheckBox)
        self._detectionControls[aCheckBoxName] = aCheckBox

        #
        spinBoxName = 'Bin Lines'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout0.addWidget(aLabel)

        aSpinBox = QtWidgets.QSpinBox()
        aSpinBox.setToolTip(self._detectionDict.getDescription('binLineScans'))
        aSpinBox.setRange(1,100)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(self._detectionDict['binLineScans'])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout0.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        buttonName = 'Reset'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Reset detection parameters to default.')
        aButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        hLayout0.addWidget(aButton)

        #
        # second row
        hLayout1 = QtWidgets.QHBoxLayout()
        hLayout1.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout1)

        spinBoxName = 'Prominence'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout1.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(self._detectionDict.getDescription('prominence'))
        aSpinBox.setRange(-100,100)
        aSpinBox.setSingleStep(0.01)
        aSpinBox.setValue(self._detectionDict['prominence'])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout1.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        # spinBoxName = 'thresh_rel_height'
        # aLabel = QtWidgets.QLabel(spinBoxName)
        # hLayout1.addWidget(aLabel)

        # aSpinBox = QtWidgets.QDoubleSpinBox()
        # aSpinBox.setToolTip(self._detectionDict.getDescription('thresh_rel_height'))
        # aSpinBox.setRange(-100,100)
        # aSpinBox.setSingleStep(0.01)
        # aSpinBox.setValue(self._detectionDict['thresh_rel_height'])
        # aSpinBox.setKeyboardTracking(False)
        # aSpinBox.valueChanged.connect(
        #     partial(self._on_spin_box, spinBoxName)
        #     )
        # hLayout1.addWidget(aSpinBox)
        # self._detectionControls[spinBoxName] = aSpinBox

        #
        # hLayout = QtWidgets.QHBoxLayout()
        # hLayout.setAlignment(QtCore.Qt.AlignLeft)
        # vLayout.addLayout(hLayout)

        spinBoxName = 'Width (ms)'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout1.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(self._detectionDict.getDescription('width (ms)'))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(self._detectionDict['width (ms)'])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout1.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        # hLayout = QtWidgets.QHBoxLayout()
        # hLayout.setAlignment(QtCore.Qt.AlignLeft)
        # vLayout.addLayout(hLayout)

        spinBoxName = 'Distance (ms)'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout1.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(self._detectionDict.getDescription('distance (ms)'))
        aSpinBox.setRange(0,10000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(self._detectionDict['distance (ms)'])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout1.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        spinBoxName = 'Decay (ms)'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout1.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(self._detectionDict.getDescription('decay (ms)'))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(self._detectionDict['decay (ms)'])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout1.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        # third row
        hLayout2 = QtWidgets.QHBoxLayout()
        hLayout2.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout2)

        #
        aName = 'Background Subtract'
        aLabel = QtWidgets.QLabel(aName)
        hLayout2.addWidget(aLabel)
        
        aComboBox = QtWidgets.QComboBox()
        aComboBox.setToolTip(self._detectionDict.getDescription('polarity'))
        _items = KymRoiDetection.backgroundSubtractTypes  # ['Off', 'Rolling-Ball', 'Median', 'Mean']
        aComboBox.addItems(_items)
        aComboBox.currentTextChanged.connect(
            partial(self._on_combobox, aName)
        )
        hLayout2.addWidget(aComboBox)
        self._detectionControls[aName] = aComboBox

        aCheckBoxName = 'Exp Detrend'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip(self._detectionDict.getDescription('doExpDetrend'))
        aCheckBox.setChecked(self._detectionDict['doExpDetrend'])
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout2.addWidget(aCheckBox)
        self._detectionControls[aCheckBoxName] = aCheckBox

        #
        aName = 'f0'
        aLabel = QtWidgets.QLabel(aName)
        hLayout2.addWidget(aLabel)
        
        aComboBox = QtWidgets.QComboBox()
        aComboBox.setToolTip(self._detectionDict.getDescription('f0ManualPercentile'))
        aComboBox.addItems(['Manual', 'Percentile'])
        aComboBox.currentTextChanged.connect(
            partial(self._on_combobox, aName)
        )
        hLayout2.addWidget(aComboBox)
        self._detectionControls[aName] = aComboBox

        #
        spinBoxName = 'f0 Percentile'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout2.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(self._detectionDict.getDescription('f0 Percentile'))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(self._detectionDict['f0 Percentile'])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout2.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        spinBoxName = 'newOnsetOffsetFraction'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout2.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(self._detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(.1)
        aSpinBox.setValue(self._detectionDict[spinBoxName])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout2.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        buttonName = 'Plot Quality'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Matplotlib plot of steps in forming dF/F0.')
        aButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        hLayout2.addWidget(aButton)

        return vLayout

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

        buttonName = 'ANALYZE'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Perform the analysis')
        aButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        hLayout.addWidget(aButton)

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

        # second row
        hLayout1 = QtWidgets.QHBoxLayout()
        hLayout1.setAlignment(QtCore.Qt.AlignLeft)
        vBoxLayout.addLayout(hLayout1)

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

        aCheckBoxName = 'Clips'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle peak clips on/off')
        aCheckBox.setChecked(True)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout1.addWidget(aCheckBox)

        aCheckBoxName = 'Scatter'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle scatter plot on/off')
        aCheckBox.setChecked(True)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout1.addWidget(aCheckBox)

        aCheckBoxName = 'ROI'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle scatter plot on/off')
        aCheckBox.setChecked(True)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout1.addWidget(aCheckBox)

        # show intensity under cursor
        # TODO: put this somewhere better
        self.hoverLabel = QtWidgets.QLabel(None)
        hLayout1.addWidget(self.hoverLabel, alignment=QtCore.Qt.AlignRight)

        return vBoxLayout
    
    def _on_spin_box(self, name, value):
        if self._blockSlots:
            # logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return
        
        logger.info(f'name:{name} value:{value}')
        
        if name == 'Median Filter Kernel':
            self._detectionDict['medianfilterkernel'] = value
            self.updateRoiIntensityPlot()  # update with selected
        
        elif name == 'Bin Lines':
            self._detectionDict['binLineScans'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Prominence':
            self._detectionDict['prominence'] = value
            self.updateRoiIntensityPlot()  # update with selected

        # elif name == 'thresh_rel_height':
        #     self._detectionDict['thresh_rel_height'] = value
        #     self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Width (ms)':
            self._detectionDict['width (ms)'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Distance (ms)':
            self._detectionDict['distance (ms)'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Decay (ms)':
            self._detectionDict['decay (ms)'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'f0 Percentile':
            self._detectionDict[name] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'newOnsetOffsetFraction':
            self._detectionDict[name] = value
            self.updateRoiIntensityPlot()  # update with selected

        else:
            logger.error(f'did not understand name:{name}')

    def _on_combobox(self, name, value):
        if self._blockSlots:
            # logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return
        
        logger.info(f'{name} {value}')
        if name == 'Polarity':
            self._detectionDict['polarity'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Background Subtract':
            self._detectionDict['backgroundsubtract'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'f0':
            self._detectionDict['f0ManualPercentile'] = value
            self.updateRoiIntensityPlot()  # update with selected

    def _on_checkbox_clicked(self, name, value):
        if self._blockSlots:
            # logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return

        if value > 1:
            value = 1
        
        # logger.info(f'name:{name} value:{value}')

        # if name == 'ROIs':
        #     logger.info('TODO: toggle image ROIs on/off')
        #     pass

        if name == 'Median Filter':
            self._detectionDict['medianfilter'] = value == 1
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Savitzky-Golay':
            self._detectionDict['filter'] = value == 1
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Exp Detrend':
            self._detectionDict['doExpDetrend'] = value == 1
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Contrast':
            self._contrastSliders.setVisible(value)

        elif name == 'Sum Intensity (f0)':
            self.rawIntensityPlotItem.setVisible(value)

        elif name == 'Clips':
            self.peakClipsWidget.setVisible(value)

        elif name == 'Scatter':
            self.simpleScatter.setVisible(value)

        elif name == 'ROI':
            # toggle all roi
            self.roiList._toggleROI(value)

        # elif name == 'Tables':
        #     self.peakClipPlotItem.setVisible(value)

        # plot overlays
        elif name in self._overlayPlotDict.keys():
            self._overlayPlotDict[name].setVisible(value)

        else:
            logger.info(f'did not understand name:"{name}"')

    def _on_button_click(self, name : str):
        logger.info(f'name:{name}')
        
        if name == 'ANALYZE':
            self.analyzeRoi()  # analyze the selected ROI
            self.updateRoiIntensityPlot(doAnalysis=False)

        elif name == 'Add ROI':
            self.addRoi()

        elif name =='Delete ROI':
            self.removeSelectedRoi()

        elif name == 'Reset':
            # reset detection params to default
            self._detectionParams.setDefaults()
            self._updateDetectionParamGui()

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

        vBoxPlot = QtWidgets.QVBoxLayout()
        mainHBox.addLayout(vBoxPlot)

        self._topToolbar = self._buildTopToolbar()  # one row with file name, image params
        vBoxPlot.addLayout(self._topToolbar)

        self._detectionToolbar = self._builtDetectionToolbar()
        vBoxPlot.addLayout(self._detectionToolbar)

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

        logger.warning('--->>> tryin ColorBarItem')
        self.aColorBar = pg.ColorBarItem(colorMap='inferno')
        self.aColorBar.setImageItem(self.myImageItem)

        self.kymographPlot.addItem(self.myImageItem, ignorBounds=True)

        # redirect hover to self (to display intensity
        self.myImageItem.hoverEvent = self._hoverEvent

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

        # initally hidden
        self.rawIntensityPlotItem.setVisible(False)

        self.rawIntensityPlot = self.rawIntensityPlotItem.plot(name="rawIntensityPlot",
                                                        # pen=pg.mkPen('c', width=5),
                                                        #   symbol='o',
                                                        #   brush=pg.mkBrush(100, 255, 100, 220),
                                                        )   

        # f0Value = self._detectionParams['f0Value']
        self.rawIntensity_f0_line = pg.InfiniteLine(angle=0,
                                                    movable=False,
                                                    pen = pg.mkPen('c', width=2),
                                                    # label=f'f0={f0Value}',
                                                    label='f0={value}',
                                                    labelOpts={'position':0.05},
                                                    )
        # f0Value = self._detectionParams['f0Value']
        # self.rawIntensity_f0_line.setPos(f0Value)
        self.rawIntensityPlotItem.addItem(self.rawIntensity_f0_line)

        self._rawPlotCursors = sanpyCursors(self.rawIntensityPlotItem, showCursorD=False)
        self._rawPlotCursors.toggleCursors(False)  # initially hidden
        self._rawPlotCursors._showCursorA = False
        self._rawPlotCursors._showCursorB = False
        self._rawPlotCursors.signalCursorDragged.connect(self.mySetStatusbar)

        vBoxPlot.addWidget(self.rawIntensityPlotItem)

        #
        # 4) sum intensity of each line scan (actually our int/f0 plot)
        self.sumIntensityPlotItem = pg.PlotWidget()
        self.sumIntensityPlotItem.setDefaultPadding()
        self.sumIntensityPlotItem.enableAutoRange()
        self.sumIntensityPlotItem.setMouseEnabled(x=True, y=False)
        self.sumIntensityPlotItem.hideButtons()  # hide the little 'A' button to rescale axis

        self.sumIntensityPlotItem.setLabel("left", 'Santana Intensity (f/f0)', units="")
        self.sumIntensityPlotItem.setLabel("bottom", 'Time (s)', units="")
        self.sumIntensityPlotItem.setXLink(self.kymographPlot)

        self.sumIntensityPlot = self.sumIntensityPlotItem.plot(name="sumIntensityPlot",
                                                        pen=pg.mkPen(width=3),
                                                        #   symbol='o',
                                                        #   brush=pg.mkBrush(100, 255, 100, 220),
                                                        )   
        
        self._sanpyCursors = sanpyCursors(self.sumIntensityPlotItem, showCursorD=True)
        self._sanpyCursors.toggleCursors(False)  # initially hidden
        self._sanpyCursors.signalCursorDragged.connect(self.mySetStatusbar)

        self._initSumPlotOverlays()
        sumOverlayToolbar = self._buildPlotOverlayToolbar()

        # order matters
        vBoxPlot.addLayout(sumOverlayToolbar)
        vBoxPlot.addWidget(self.sumIntensityPlotItem)

        #
        vBoxForClipsScatterTable = QtWidgets.QVBoxLayout()
        # mainHBox.addLayout(vBoxForClipsScatterTable)

        _tmpWidget = QtWidgets.QWidget()
        _tmpWidget.setLayout(vBoxForClipsScatterTable)

        self.peakClipsWidget = KymRoiClipsWidget()
        vBoxForClipsScatterTable.addWidget(self.peakClipsWidget)

        #
        # simple scatter plot
        self.simpleScatter = SimpleRoiScatter()
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
        
        logger.info(f'{colorMap} cm:{cm}')

        self.myImageItem.setColorMap(cm)
    
    def _buildPlotOverlayToolbar(self):
        """Dynamically build a number of check boxes from keys in _overlayPlotDict.
        """
        hBox = QtWidgets.QHBoxLayout()
        hBox.setAlignment(QtCore.Qt.AlignLeft)

        for aCheckBoxName in self._overlayPlotDict.keys():
            aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
            aCheckBox.setChecked(self._overlayPlotDict[aCheckBoxName].isVisible())
            aCheckBox.stateChanged.connect(
                partial(self._on_checkbox_clicked, aCheckBoxName)
            )
            hBox.addWidget(aCheckBox)
        
        # lab to show selected roi
        self._selectedRoiLabel = QtWidgets.QLabel('ROI: None')
        hBox.addWidget(self._selectedRoiLabel)

        return hBox
    
    def _initSumPlotOverlays(self):
        """"Initialize a number of overlay plots on top of self.sumIntensityPlotItem.
        
        e.g. (peak, threshold, half-width, etc)
        """

        self._overlayPlotDict = {}

        self._overlayPlotDict['Threshold'] = self.sumIntensityPlotItem.plot(name="sumIntensityPeaksPlot",
                                                  pen=None,
                                                  symbol='o',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(255, 0, 0, 220)
                                                  )

        self._overlayPlotDict['Decay'] = self.sumIntensityPlotItem.plot(name="sumIntensityPeaksPlot",
                                                  pen=None,
                                                  symbol='t',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(255, 0, 255, 220)
                                                  )

        self._overlayPlotDict['Peak Int'] = self.sumIntensityPlotItem.plot(name="Peak Int",
                                                  pen=None,
                                                  symbol='o',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(0, 255, 0, 220)
                                                  )

        # Peak 90 Bin
        self._overlayPlotDict['Onset 10'] = self.sumIntensityPlotItem.plot(name="Onset 10",
                                                  pen=None,
                                                  symbol='x',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(0, 255, 0, 220)
                                                  )

        # Decay 90 Bin
        self._overlayPlotDict['Decay 10'] = self.sumIntensityPlotItem.plot(name="Decay 10",
                                                  pen=None,
                                                  symbol='x',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(0, 255, 0, 220)
                                                  )

        # Peak 90 Bin
        # self._overlayPlotDict['Onset 90'] = self.sumIntensityPlotItem.plot(name="Onset 90",
        #                                           pen=None,
        #                                           symbol='x',
        #                                           symbolPen=None,
        #                                           symbolSize=10,
        #                                           symbolBrush=pg.mkBrush(0, 255, 0, 220)
        #                                           )

        # Decay 90 Bin
        # self._overlayPlotDict['Decay 90'] = self.sumIntensityPlotItem.plot(name="Decay 90",
        #                                           pen=None,
        #                                           symbol='x',
        #                                           symbolPen=None,
        #                                           symbolSize=10,
        #                                           symbolBrush=pg.mkBrush(0, 255, 0, 220)
        #                                           )

        self._overlayPlotDict['Half-width'] = self.sumIntensityPlotItem.plot(name="sumIntensityPeaksPlot",
                                                #   pen=None,
                                                  symbol='o',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(0, 255, 255, 220)
                                                  )

        self._overlayPlotDict['Exp Decay'] = self.sumIntensityPlotItem.plot(name="sumIntensityPeaksPlot",
                                                  pen=pg.mkPen(color='m', width=2),
                                                #   symbol='o',
                                                #   symbolPen=None,
                                                #   symbolSize=10,
                                                #   symbolBrush=pg.mkBrush(0, 255, 255, 220)
                                                  )
        self._overlayPlotDict['Exp Decay'].setVisible(False)

        self._overlayPlotDict['Dbl Exp Decay'] = self.sumIntensityPlotItem.plot(name="dbl exp decay",
                                                  pen=pg.mkPen(color='y', width=2),
                                                #   symbol='o',
                                                #   symbolPen=None,
                                                #   symbolSize=10,
                                                #   symbolBrush=pg.mkBrush(0, 255, 255, 220)
                                                  )
        self._overlayPlotDict['Dbl Exp Decay'].setVisible(False)

        # newOnsetBins
        # self._overlayPlotDict['newOnsetBins'] = self.sumIntensityPlotItem.plot(name="newOnsetBins",
        #                                           pen=None,
        #                                           symbol='o',
        #                                           symbolPen=None,
        #                                           symbolSize=15,
        #                                           symbolBrush=pg.mkBrush(200, 255, 200, 220)
        #                                           )
        # self._overlayPlotDict['newOffsetBins'] = self.sumIntensityPlotItem.plot(name="newOffsetBins",
        #                                           pen=None,
        #                                           symbol='o',
        #                                           symbolPen=None,
        #                                           symbolSize=15,
        #                                           symbolBrush=pg.mkBrush(200, 255, 200, 220)
        #                                           )

        # self._overlayPlotDict['newOnset10Bins'] = self.sumIntensityPlotItem.plot(name="newOnset10Bins",
        #                                           pen=None,
        #                                           symbol='star',
        #                                           symbolPen=None,
        #                                           symbolSize=10,
        #                                           symbolBrush=pg.mkBrush(200, 255, 200, 220)
        #                                           )
        # self._overlayPlotDict['newOffset10Bins'] = self.sumIntensityPlotItem.plot(name="newOffset10Bins",
        #                                           pen=None,
        #                                           symbol='star',
        #                                           symbolPen=None,
        #                                           symbolSize=10,
        #                                           symbolBrush=pg.mkBrush(200, 255, 200, 220)
        #                                           )

    def analyzeRoi(self, roi=None, doQuick=False):
        """Analyze one roi e.g. detect peaks.
        """

        if roi is None:
            roi = self.roiList.selectedRoi  # pyqtgraph ROI()
        
        if roi is None:
            logger.info('please select an roi to analyze')
            return

        logger.info('   === === === WIDGET PERFORMING ANALYSIS === === ===')
        # print(self._detectionDict.printValues())
        # print('')

        self.roiList.kymRoiList[roi].peakDetect(verbose=True)

        # from sanpy.kym.kymRoiAnalysis import plotDetectionResults
        # kymRoi = self.roiList.kymRoiList[roi]
        # plotDetectionResults(kymRoi)

    def _msToBin(self, msValue : float) -> int:
        """Convert ms to nearest bin using round.
        """
        _retBin1 = msValue / 1000 / self.secondsPerLine
        _retBin2 = int(round(_retBin1))
        # logger.info(f'msValue:{msValue} _retBin1:{_retBin1} _retBin2:{_retBin2}')
        return _retBin2
    
    def getDataFrame(self, roi = None):
        """Get results df for one roi or all roi (use roi=None).
        """
        if roi is not None:
            # return self._analysisDf[roi].df
            return self.roiList.getAnalysisResults(roi).df
        else:
            columns = list(KymRoiResults.analysisDict.keys())
            df = pd.DataFrame(columns=columns)  # empty df with proper columns
            for _roiIdx, oneRoi in enumerate(self.roiList.kymRoiList.keys()):
                oneDf = self.roiList.getAnalysisResults(oneRoi).df
                # logger.info(f'oneDf:{oneDf}')
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

        f0Value = self._detectionParams['f0Value']
        self.rawIntensity_f0_line.setPos(round(f0Value,2))

        self._rawPlotCursors._showInView()

    def updateRoiIntensityPlot(self, roi=None, doAnalysis=True, refreshScatter=True):
        """Update intensity plot when user adjusts roi.
        """
        if roi is None:
            roi = self.roiList.selectedRoi
            if roi is None:
                logger.warning('no roi selected')
                return

        # set selected roi label
        _roiLabelText = self.roiList.roiLabelList[roi].toPlainText()
        self._selectedRoiLabel.setText(f'ROI: {_roiLabelText}')

        # clear all
        # for oneRoi in self._roiIntensityPlot.keys():
        #     self._roiIntensityPlot[oneRoi].setData([],[])
        self.sumIntensityPlot.setData([], [])

        for k,v in self._overlayPlotDict.items():
            v.setData([], [])

        # perform analysis
        logger.warning(f'turned off auto analysis - implementing "Analyze" button doAnalysis:{doAnalysis}')
        if doAnalysis:
            # self._detectionDict['binLineScans']
            self.analyzeRoi(roi, doQuick=True)

        # v2
        # logger.warning('PLOTTING V2')
        timeSec = self.roiList.getAnalysisTrace(roi, 'timeSec')
        # int_df_f0 = self.roiList.getAnalysisTrace(roi, 'int_df_f0')
        int_f_f0 = self.roiList.getAnalysisTrace(roi, 'int_f_f0')

        logger.warning('swapping my int_df_f0 for santana int_f_f0')
        if int_f_f0 is None:
            return
        int_df_f0 = int_f_f0

        if timeSec is None:
            logger.error('-->> NO ANALYSIS YET')
            return

        # self._roiIntensityPlot[roi].setData(timeSec, int_df_f0, connect="finite")  # fill with nan
        self.sumIntensityPlot.setData(timeSec, int_df_f0, connect="finite")  # fill with nan
        
        #
        # analysis results
        # dfPlot = self._analysisDf[roi].df
        
        # v2
        logger.info(f'fetching v2 results')
        dfPlot = self.roiList.kymRoiList[roi].analysisResults.df
        
        numPeaks = len(dfPlot)

        # newOnsetBins/newOffsetBins
        # newOnsetBins = dfPlot['newOnsetBins']
        # try:
        #     # logger.error(f'newOnsetSeconds:{newOnsetSeconds}')
        #     # logger.error(f'y_newOnsetBins:{y_newOnsetBins}')
        #     newOnsetSeconds = timeSec[newOnsetBins]
        #     newOnsetsValues = int_df_f0[newOnsetBins]
            
        #     self._overlayPlotDict['newOnsetBins'].setData(newOnsetSeconds, newOnsetsValues)
        # except (KeyError) as e:
        #     logger.error(f'did not get newOnsetBins -->> need to reanalyze')
        
        # newOffsetBins = dfPlot['newOffsetBins']
        # try:
        #     # logger.error(f'newOnsetSeconds:{newOnsetSeconds}')
        #     # logger.error(f'y_newOnsetBins:{y_newOnsetBins}')
        #     newOffsetSeconds = timeSec[newOffsetBins]
        #     newOffsetValues = int_df_f0[newOffsetBins]
            
        #     self._overlayPlotDict['newOffsetBins'].setData(newOffsetSeconds, newOffsetValues)
        # except (KeyError) as e:
        #     logger.error(f'did not get newOffsetBins -->> need to reanalyze')

        # onset/offset at 90%
        onset10Bin = dfPlot['Onset 10 Bin']
        # newOnset10Bins = newOnset10Bins[ ~np.isnan(newOnset10Bins) ]
        # onset10Bin = onset10Bin.astype(int)
        onset10Seconds = timeSec[onset10Bin]
        onset10Value = int_df_f0[onset10Bin]
        self._overlayPlotDict['Onset 10'].setData(onset10Seconds, onset10Value)

        decay10Bin = dfPlot['Decay 10 Bin']
        decay10BinSeconds = timeSec[decay10Bin]
        decay10Value = int_df_f0[decay10Bin]            
        self._overlayPlotDict['Decay 10'].setData(decay10BinSeconds, decay10Value)

        # orig
        peakSecond = dfPlot['Peak Second']
        yPeak = dfPlot['Peak Int']
        self._overlayPlotDict['Peak Int'].setData(peakSecond, yPeak)

        thresholdSecond = dfPlot['Onset Second']
        thresholdValue = dfPlot['Onset Int']
        self._overlayPlotDict['Threshold'].setData(thresholdSecond, thresholdValue)

        decaySecond = dfPlot['Decay Second']
        decayValue = dfPlot['Decay Int']
        self._overlayPlotDict['Decay'].setData(decaySecond, decayValue)

        # Threshold 90 and Decay 90
        # peak90Second = dfPlot['Onset 90 Second']
        # peak90Value = dfPlot['Onset 90 Int']
        # self._overlayPlotDict['Onset 90'].setData(peak90Second, peak90Value)

        # decay90Second = dfPlot['Decay 90 Second']
        # decay90Value = dfPlot['Decay 90 Int']
        # self._overlayPlotDict['Decay 90'].setData(decay90Second, decay90Value)

        # half width
        xHalfwidth = []
        yHalfwidth = []
        for _peakIdx in range(numPeaks):
            hwLeftBin = dfPlot['HW Left Bin'][_peakIdx]
            hwLeftSec = timeSec[hwLeftBin]

            hwRightBin = dfPlot['HW Right Bin'][_peakIdx]
            hwRightSec = timeSec[hwRightBin]

            xHalfwidth.append( hwLeftSec )
            xHalfwidth.append( hwRightSec )
            xHalfwidth.append( np.nan )

            yHalfwidth.append( dfPlot['HW Height'][_peakIdx] )
            yHalfwidth.append( dfPlot['HW Height'][_peakIdx] )
            yHalfwidth.append( np.nan )

        self._overlayPlotDict['Half-width'].setData(xHalfwidth, yHalfwidth)

        
        # (1) exp decay
        from sanpy.kym.kymRoiAnalysis import myMonoExp
        xDecay = []
        yDecay = []
        _peakBins = dfPlot['Peak Bin']
        for _peakIdx, _peakBin in enumerate(_peakBins):
            
            # fix this constant bug !!!!
            # [_left, _, _, _] = self.roiList._roiAsRect(roi)
            # _peakBin = _peakBin - _left
            
            fit_m = dfPlot['fit_m'][_peakIdx]            
            fit_tau = dfPlot['fit_tau'][_peakIdx]
            fit_b = dfPlot['fit_b'][_peakIdx]

            if np.isnan(fit_m):
                logger.warning(f'no exp fit for peak {_peakIdx}')
                continue

            # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine
            decayFitBins = self._msToBin(self._detectionDict['decay (ms)'])
            # _xRange = xPlot[_peakBin:_peakBin+decayFitBins] - xPlot[_peakBin]
            _xRange = np.arange(decayFitBins)
            # get line showing our fit
            fit_y = myMonoExp(_xRange, fit_m, fit_tau, fit_b)

            xDecay.extend(_xRange + timeSec[_peakBin])
            xDecay.append(np.nan)

            yDecay.extend(fit_y)
            yDecay.append(np.nan)

        self._overlayPlotDict['Exp Decay'].setData(xDecay, yDecay)

        #
        # (2) double exp decay
        # xDecay = []
        # yDecay = []
        # _peakBins = dfPlot['Peak Bin']
        # for _peakIdx, _peakBin in enumerate(_peakBins):
            
        #     # fix this constant bug !!!!
        #     [_left, _, _, _] = self.roiList._roiAsRect(roi)
        #     _peakBin = _peakBin - _left
            
        #     fit_m1 = dfPlot['fit_m1'][_peakIdx]            
        #     fit_tau1 = dfPlot['fit_tau1'][_peakIdx]
        #     fit_m2 = dfPlot['fit_m2'][_peakIdx]            
        #     fit_tau2 = dfPlot['fit_tau2'][_peakIdx]

        #     if np.isnan(fit_m1):
        #         # logger.warning(f'no fit for peak {_peakIdx}')
        #         continue

        #     # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine
        #     decayFitBins = self._msToBin(self._detectionDict['decay (ms)'])
        #     _xRange = xPlot[_peakBin:_peakBin+decayFitBins] - xPlot[_peakBin]
            
        #     # get line showing our fit
        #     fit_y = myDoubleExp(_xRange, fit_m1, fit_tau1, fit_m2, fit_tau2)

        #     xDecay.extend(_xRange+xPlot[_peakBin])
        #     xDecay.append(np.nan)

        #     yDecay.extend(fit_y)
        #     yDecay.append(np.nan)

        # self._overlayPlotDict['Dbl Exp Decay'].setData(xDecay, yDecay)

        # refresh cursors
        self._sanpyCursors._showInView()

        # raw intensity plot (to manually set f0)
        self.update_fo_plot(roi)

        #
        # peak clips
        self.plotPeakClips(roi)

        #
        # refresh scatter plot
        if refreshScatter:
            self.refreshScatter()  # update all

    def refreshScatter(self, roi = None):
        """Refresh seaborn scatter plot widget.
        """
        if roi is not None:
            # df = self._analysisDf[roi].df
            df = self.roiList.getAnalysisResults(roi).df
        else:
            df = self.getDataFrame()  # get full dataframe across all 'roi number'
        
        # logger.info('refresh with df')
        # print(df)

        self.simpleScatter.replot(df)

    def plotPeakClips(self, roi):

        logger.warning('swapping my df_f0 with santana f_f0')
        # yPlot = self.roiList.getAnalysisTrace(roi, 'int_df_f0')
        yPlot = self.roiList.getAnalysisTrace(roi, 'int_f_f0')
        if yPlot is None:
            return
        
        # [_left, _, _, _] = self.roiList._roiAsRect(roi)
        # logger.info(f'roi rect left:{left}')

        # analysis results
        dfPlot = self.roiList.getAnalysisResults(roi).df
        xPeaks = dfPlot['Peak Bin']
        # xPeaks = xPeaks - _left

        plusMinBins = self._msToBin(self._detectionDict['decay (ms)'])
        # peak clips
        self.peakClipsWidget.plotPeakClips(yPlot, xPeaks, self.secondsPerLine, plusMinBins)

    def _hoverEvent(self, event):
        """Hover on image.
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
        
        # logger.info(f'x:{xPos} y:{yPos} intensity:{intensity}')

        self.hoverLabel.setText(f"Cursor:{intensity}")
        self.hoverLabel.update()

    def _resetZoom(self, doEmit=True):
        
        # order matter, do sum then image
        # 
        self.sumIntensityPlotItem.autoRange()  # item=self._roiIntensityPlot[roi]
        self.rawIntensityPlotItem.autoRange()

        self.kymographPlot.autoRange(item=self.myImageItem)

    def keyReleaseEvent(self, event):
    
        key = event.key()
        isShift = key == QtCore.Qt.Key_Shift
        
        if isShift:
            # default is x-zoom
            self.kymographPlot.setMouseEnabled(x=True, y=False)
            self.sumIntensityPlotItem.setMouseEnabled(x=True, y=False)
            self.rawIntensityPlotItem.setMouseEnabled(x=True, y=False)
    
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
        f0ManualPercentile = self._detectionParams['f0ManualPercentile']  # in (Manual, Percentile)
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
            self._detectionParams['f0Value'] = cCursorValue
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

        cursorAction = QtWidgets.QAction('Cursors')
        cursorAction.setCheckable(True)
        cursorAction.setChecked(self._sanpyCursors.cursorsAreShowing())
        contextMenu.addAction(cursorAction)
        contextMenu.addSeparator()

        contextMenu.addAction('Save Kym Image ...')

        saveSumPlotAction = QtWidgets.QAction('Save Sum Plot ...')
        saveSumPlotAction.setEnabled(selectedRoi is not None)
        contextMenu.addAction(saveSumPlotAction)

        saveClipsAction = QtWidgets.QAction('Save Clips ...')
        saveClipsAction.setEnabled(selectedRoi is not None)
        contextMenu.addAction(saveClipsAction)

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

        elif actionText == 'Save Kym Image ...':
            _ret = self.savePlotItemAs(self.kymographPlot, 'kym-image')

        elif actionText == 'Save Sum Plot ...':
            roiLabelText = self.roiList.roiLabelList[selectedRoi].toPlainText()
            _ret = self.savePlotItemAs(self.sumIntensityPlotItem.plotItem, f'sum-plot-roi-{roiLabelText}')

        elif actionText == 'Save Clips ...':
            roiLabelText = self.roiList.roiLabelList[selectedRoi].toPlainText()
            _ret = self.savePlotItemAs(self.peakClipsWidget.peakClipPlotItem.plotItem, f'clip-plot-{roiLabelText}')

        # elif actionText == 'Copy Stats Table ...':
        #     _ret = self.simpleScatter.copyTableToClipboard()
        
        # special case on transition to backend
        elif actionText.startswith('Select ROI'):
            _, roiInt = actionText.split(': ')
            logger.info(f'roiInt:{roiInt}')
            self.selectRoiByLabel(roiInt)

        self.mySetStatusbar(_ret)