import os
# import math
from typing import List
from functools import partial
from copy import copy
import json

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

from sanpy.kym.kymRoiDetection import KymRoiDetection
from sanpy.kym.kymRoiResults import KymRoiResults
from sanpy.kym.interface.kymRoiScatter import SimpleRoiScatter
from sanpy.kym.interface.kymRoiClipsWidget import KymRoiClipsWidget

from sanpy.kym.mpLineProfile import roiLineProfilePool

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def myDetrend(xPlot, yPlot):
    # from scipy.signal import detrend
    
    y_log = np.log(yPlot)
    y_log_detrended = detrend(y_log)
    
    y_detrended = np.exp(y_log_detrended)

    plt.plot(xPlot, yPlot, label='raw')
    plt.plot(xPlot, y_detrended, label='detrended')

    _params, _cov = scipy.optimize.curve_fit(myMonoExp, xPlot, yPlot)
    _m, _tau, _b = _params
    fit_y = myMonoExp(xPlot, _m, _tau, _b)
    plt.plot(xPlot, fit_y, 'r-', label='exp fit')

    y_minus_single = np.subtract(yPlot, fit_y)
    plt.plot(xPlot, y_minus_single, 'k-', label='exp fit 1 detrend')

    _params, _cov = scipy.optimize.curve_fit(myDoubleExp, xPlot, yPlot)
    _m1, _tau1, _m2, _tau2 = _params
    fit_y2 = myDoubleExp(xPlot, _m1, _tau1, _m2, _tau2)
    plt.plot(xPlot, fit_y2, 'g-', label='exp fit 2')

    y_minus_double = np.subtract(yPlot, fit_y2)
    plt.plot(xPlot, y_minus_double, 'c-', label='exp fit 2 detrend')

    plt.legend()
    plt.show()

    return y_minus_double

def getSavitzkyGolay_Filter(y: np.ndarray, pnts: int = 5, poly: int = 2, verbose=False):
    """Get SavitzkyGolay filtered version of y using scipy.signal.savgol_filter"""
    if verbose:
        logger.info("")
    filtered = savgol_filter(y, pnts, poly, mode="nearest", axis=0)
    return filtered

def myMonoExp(x, m, t, b):
    """
    M: a_0
    t: tau_0
    b: 
    """
    # this triggers
    # "RuntimeWarning: overflow encountered in exp" during search for parameters, just ignor it
    # ret = m * np.exp(-t * x) + b
    ret = m * np.exp(-t * x) + b
    return ret

def myDoubleExp(x, m1, t1, m2, t2):
    # pos peak -> decay
    return m1 * np.exp(-t1 * x) + m2 * np.exp(-t2 * x)
    
    # neg peak -> recovery
    # return m1 * np.exp(t1 * x) + m2 * np.exp(t2 * x)

def _expFit2(xPlot, yPlot, xPeakBins, decayFitBins :int):
    doDebug = False
    
    numPeaks = len(xPeakBins)
    fit_m1 = [np.nan] * numPeaks
    fit_tau1 = [np.nan] * numPeaks
    fit_m2 = [np.nan] * numPeaks
    fit_tau2 = [np.nan] * numPeaks
    fit_r2 = [np.nan] * numPeaks
    fit_error = [''] * numPeaks

    for _peakIdx, _peakBin in enumerate(xPeakBins):
        # logger.info(f'_peakIdx:{_peakIdx}')
        
        try:
            xRange = xPlot[_peakBin:_peakBin+decayFitBins] - xPlot[_peakBin]
        except (IndexError) as e:
            # logger.error(f'{e}')
            # logger.error(f'   _peakIdx:{_peakIdx}')
            # logger.error(f'      xPlot: {len(xPlot)} {xPlot}')
            # logger.error(f'      yPlot: {len(yPlot)} {yPlot}')
            # logger.error(f'      decayFitBins:{decayFitBins}')
            # logger.error(f'      _peakBin:{_peakBin}')
            # logger.error(f'      _peakBin+fitWinPnts:{_peakBin+decayFitBins}')
            continue

        yRange = yPlot[_peakBin:_peakBin+decayFitBins]
        
        # plot the raw data
        if doDebug:
            plt.plot(xRange+xPlot[_peakBin], yRange)
        
        try:
            _params, _cov = scipy.optimize.curve_fit(myDoubleExp, xRange, yRange)

            # plot the fit
            _fit_m1, _fit_tau1, _fit_m2, _fit_tau2 = _params

            fit_m1[_peakIdx] = _fit_m1
            fit_tau1[_peakIdx] = _fit_tau1
            fit_m2[_peakIdx] = _fit_m2
            fit_tau2[_peakIdx] = _fit_tau2

            #
            # residual sum of squares
            _y_fit = myDoubleExp(xRange, _fit_m1, _fit_tau1, _fit_m2, _fit_tau2)
            ss_res = np.sum((yRange - _y_fit) ** 2)
            ss_tot = np.sum((yRange - np.mean(yRange)) ** 2)  # total sum of squares
            fit_r2[_peakIdx] = 1 - (ss_res / ss_tot)  # r-squared

            if doDebug:
                fit_y = myDoubleExp(xRange, _fit_m1, _fit_tau1, _fit_m2, _fit_tau2)
                plt.plot(xRange+xPlot[_peakBin], fit_y, 'c-')

        except (RuntimeError, TypeError) as e:
            if doDebug:
                logger.error(f'  _peakIdx:{_peakIdx} _peakBin:{_peakBin} -->> {e}')
            fit_error[_peakIdx] = str(f'_expFit2:{e}')

        if doDebug:
            plt.show()

    return fit_m1, fit_tau1, fit_m2, fit_tau2, fit_r2, fit_error

def _expFit(xPlot, yPlot, xPeakBins, decayFitBins :int):
    """Perform single exponential fit (myMonoExp) for each peak.
    """
    doDebug = False
    
    numPeaks = len(xPeakBins)
    fit_m = [np.nan] * numPeaks
    fit_tau = [np.nan] * numPeaks
    fit_b = [np.nan] * numPeaks
    fit_r2 = [np.nan] * numPeaks
    fit_error = [''] * numPeaks
    
    for _peakIdx, _peakBin in enumerate(xPeakBins):
        # logger.info(f'_peakIdx:{_peakIdx}')
        
        try:
            xRange = xPlot[_peakBin:_peakBin+decayFitBins] - xPlot[_peakBin]
        except (IndexError) as e:
            if doDebug:
                logger.error(f'{e}')
                logger.error(f'   _peakIdx:{_peakIdx}')
                logger.error(f'      xPlot: {len(xPlot)} {xPlot}')
                logger.error(f'      yPlot: {len(yPlot)} {yPlot}')
                logger.error(f'      decayFitBins:{decayFitBins}')
                logger.error(f'      _peakBin:{_peakBin}')
                logger.error(f'      _peakBin+fitWinPnts:{_peakBin+decayFitBins}')
            continue

        yRange = yPlot[_peakBin:_peakBin+decayFitBins]
        
        # plot the raw data
        if doDebug:
            plt.plot(xRange+xPlot[_peakBin], yRange)
        
        try:
            _params, _cov = scipy.optimize.curve_fit(myMonoExp, xRange, yRange)

            # plot the fit
            _m, _tau, _b = _params

            fit_m[_peakIdx] = _m
            fit_tau[_peakIdx] = _tau
            fit_b[_peakIdx] = _b

            #
            # residual sum of squares
            _y_fit = myMonoExp(xRange, _m, _tau, _b)
            ss_res = np.sum((yRange - _y_fit) ** 2)
            # total sum of squares
            ss_tot = np.sum((yRange - np.mean(yRange)) ** 2)
            # r-squared
            fit_r2[_peakIdx] = 1 - (ss_res / ss_tot)

            if doDebug:
                fit_y = myMonoExp(xRange, _m, _tau, _b)
                plt.plot(xRange+xPlot[_peakBin], fit_y, 'r-')

        except (RuntimeError, TypeError) as e:
            if doDebug:
                logger.error(f'  _peakIdx:{_peakIdx} _peakBin:{_peakBin} -->> {e}')
            fit_error[_peakIdx] = str(f'_expFit:{e}')

        if doDebug:
            plt.show()

    return fit_m, fit_tau, fit_b, fit_r2, fit_error

class RoiManager(QtWidgets.QWidget):
    """Manager a list of rectangular ROIs.
    
    The units here are always in pixels of underlying imgData
    
    TODO
    ----
    Remove physical units
    """
    signalSelectRoi = QtCore.pyqtSignal(object)  # roi
    signalRoiChanged = QtCore.pyqtSignal(object)  # roi

    def __init__(self, view, imageItem, imgData, header):
        super().__init__(None)
        
        self.view = view
        self.imageItem = imageItem
        self.imgData = imgData
        # self._header = header

        self.roiList = {}
        self.roiLabelList = {}
        self.selectedRoi = None
    
        # does not work, trying to match colors in seaborn scatter
        self._colors = sns.color_palette("Paired", 50).as_hex()

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
    
    def switchFile(self, imgData, header):    
        self.imgData = imgData
        # self._header = header

    # @property
    # def umPerPixel(self):
    #     return self._header['umPerPixel']
    
    # @property
    # def secondsPerLine(self):
    #     return self._header['secondsPerLine']
    
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
        _roi = self.roiList.pop(roi, None)
        self.view.scene().removeItem(roi)

        roiLabel = self.roiLabelList.pop(roi, None)
        logger.info(f'removed roiLabel:{roiLabel}')
    
        return _roi
    
    def removeSelectedRoi(self):
        if self.selectedRoi is not None:
            roi = self._removeRoi(self.selectedRoi)
            self.selectedRoi = None
            return roi
        else:
            logger.info('no selected roi to remove')

    def _getNewRoiLabel(self):
        """Get the name (label) and color of a new roi.
        """
        if len(self.roiLabelList.keys()) == 0:
            roiLabelName = str(1)
        else:
            _items = self.roiLabelList.values()
            _items = list(_items)
            # print(f'_items:{_items}')
            roiLabelName = int(_items[-1].toPlainText()) + 1
            roiLabelName = str(roiLabelName)
        roiColorIndex = int(roiLabelName)
        if roiColorIndex > len(self._colors):
            roiColorIndex -= len(self._colors)
        return roiLabelName, roiColorIndex
    
    def addRoi(self, pos=None, size=None, ltrbRoi=None, doSelect=True):
        """Add an ROI to self.imageItem
        
        ltrbRoi : [l, t, r, b]
        """
        if ltrbRoi is not None:
            pos = (ltrbRoi[0], ltrbRoi[3])
            size = (ltrbRoi[2] - ltrbRoi[0], ltrbRoi[1] - ltrbRoi[3])
            # logger.info(f'ltrbRoi:{ltrbRoi} -> pos:{pos} size:{size}')
        elif pos is None or size is None:
            pos, size = self._getDefaultRoi()

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
        # roiLabel = pg.TextItem(color=self.currentPen.color())
        roiLabelName, roiColorIndex = self._getNewRoiLabel()
        # color does not match seaborn scatter
        _color = self._colors[roiColorIndex]
        _color = 'c'  # just use cyan
        roiLabel = pg.TextItem(roiLabelName, color=_color)
        roiLabel.setParentItem(rectRoi)
        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(12)
        roiLabel.setFont(font)
        self.roiLabelList[rectRoi] = roiLabel

        self.roiList[rectRoi] = rectRoi

        if doSelect:
            self._selectRoi(rectRoi)

        return rectRoi, roiLabelName
    
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

    def _on_roi_changed(self, event):
        """User finished dragging the ROI

        Args:
            event :pyqtgraph.graphicsItems.ROI.ROI

        Info:
            theRect2:[0, 383, 5000, 17]
        """

        self._constrainRoi(event)

        self._selectRoi(event)  # needed to select when click+drag on handle

        # logger.info(f'roi is now: {self._roiAsRect(event)}')

        # self.ba.kymAnalysis.setRoiRect(theRect2)
        
        # logger.info(f'  -->> emit signalKymographRoiChanged theRect:{theRect2}')
        self.signalRoiChanged.emit(event)  # underlying _abf has new rect

        return
    
    # def _roiAsRect(self, roi, inPhysicalUnits=False) -> List[int]:
    def _roiAsRect(self, roi) -> List[int]:
        """
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

        # if inPhysicalUnits:
        #     # logger.info(f'   before left:{left} top:{top} right:{right} bottom:{bottom}')
        #     left *= self.secondsPerLine
        #     top *= self.umPerPixel
        #     right *= self.secondsPerLine
        #     bottom *= self.umPerPixel
        
        #     left = int(left)
        #     top = int(top)
        #     right = int(right)
        #     bottom = int(bottom)

        #     logger.info(f'   after left:{left} top:{top} right:{right} bottom:{bottom}')

        return [left, top, right, bottom]

    def _constrainRoi(self, roi):
        """Constrain an roi to imgData.
        """
        pos = roi.pos()
        size = roi.size()

        widthMax = self.imgData.shape[1] - 1
        heightMax = self.imgData.shape[0] - 1

        if pos[0] < 0:
            pos[0] = 0
        if pos[1] < 0:
            pos[1] = 0
            
        if pos[0] > widthMax:
            pos[0] = widthMax
        if pos[1] > heightMax:
            pos[1] = heightMax
        
        rightExtent = pos[0] + size[0]
        if rightExtent > widthMax:
            size[0] = widthMax - pos[0]

        topExtent = pos[1] + size[1]
        if topExtent > heightMax:
            size[1] = heightMax - pos[1]

        # set
        update = False
        finish = False
        roi.setPos(pos, update=update, finish=finish)
        roi.setSize(size, update=update, finish=finish)

        roi.stateChanged(finish=False)  # update handles

class oneRoiRect(QtWidgets.QWidget):
    signalSelectRoi = QtCore.pyqtSignal(object)  # roi
    signalRoiChanged = QtCore.pyqtSignal(object)  # [l, t, r, b]

    def __init__(self, imageItem, imgData, pos, size, label : str):
        super().__init__(None)

        self._imageItem = imageItem
        self._imgData = imgData
        
        movable = True
        removable = False
        self._rectRoi = pg.ROI(
            pos=pos,
            pen=pg.mkPen('m', width=2),
            hoverPen=pg.mkPen(width=4),
            size=size,
            parent=self._imageItem,
            movable=movable,
            removable=removable
        )
        # self.myLineRoi.addScaleHandle((0,0), (1,1), name='topleft')  # at origin
        self._rectRoi.addScaleHandle(
            (0.5, 0), (0.5, 1), name="bottom center"
        )  # top center
        self._rectRoi.addScaleHandle(
            (0.5, 1), (0.5, 0), name="top center"
        )  # bottom center
        self._rectRoi.addScaleHandle(
            (0, .5), (1, 0.5), name="left center"
        )  # bottom center
        self._rectRoi.addScaleHandle(
            (1, .5), (0, 0.5), name="right center"
        )  # bottom center
        
        self._rectRoi.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton)
        self._rectRoi.sigClicked.connect(self._on_roi_clicked)
        self._rectRoi.sigRegionChangeFinished.connect(self._on_roi_changed)
        # rectRoi.sigRemoveRequested.connect(self._on_remove_roi)

        # each roi has a label
        # roiLabel = pg.TextItem(color=self.currentPen.color())
        # roiLabelName, roiColorIndex = self._getNewRoiLabel()
        # roiLabel = pg.TextItem(roiLabelName, color=self._colors[roiColorIndex])
        # roiLabel.setParentItem(self._rectRoi)
        # font = QtGui.QFont()
        # roiLabel.setFont(font)
        
        self._label = label
        # self.roiLabelList[rectRoi] = roiLabel

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

    def getImgData(self):
        """Get imgData for an roi.
        """
        [left, t, r, b] = self._roiAsRect()  # [left, top, right, bottom]
        
        logger.info(f'fetching [left,t,r,b] {[left, t, r, b]} from image shape:{self._imgData.shape}')
        
        roiImg = self._imgData[b:t, left:r]
        
        # logger.info(f'   returning roiImg shape:{roiImg.shape} from left:{left} t:{t} r:{r} b:{b}')
        
        return roiImg

    def _on_roi_clicked(self, event):
        """
        Parameters
        ==========
        event : pyqtgraph.graphicsItems.ROI.ROI
        """
        # logger.info(event)
        self._selectRoi(event)

    def _selectRoi(self, roi = None):

        return
            
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

        self._constrainRoi()

        # self._selectRoi(event)  # needed to select when click+drag on handle

        newRect = self._roiAsRect()
        
        logger.info(f'roi is now: {newRect}')

        # self.ba.kymAnalysis.setRoiRect(theRect2)
        
        # logger.info(f'  -->> emit signalKymographRoiChanged event:{event}')
        self.signalRoiChanged.emit(newRect)  # underlying _abf has new rect

        return

    # def _roiAsRect(self, roi, inPhysicalUnits=False) -> List[int]:
    def _roiAsRect(self) -> List[int]:
        """
        Returns
            [l, t, r, b]
        """
        roi = self._rectRoi
        
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

        return [left, top, right, bottom]
    
    def _constrainRoi(self):
        """Constrain an roi to imgData.
        """
        roi = self._rectRoi
        
        pos = roi.pos()
        size = roi.size()

        widthMax = self._imgData.shape[1] - 1
        heightMax = self._imgData.shape[0] - 1

        if pos[0] < 0:
            pos[0] = 0
        if pos[1] < 0:
            pos[1] = 0
            
        if pos[0] > widthMax:
            pos[0] = widthMax
        if pos[1] > heightMax:
            pos[1] = heightMax
        
        rightExtent = pos[0] + size[0]
        if rightExtent > widthMax:
            size[0] = widthMax - pos[0]

        topExtent = pos[1] + size[1]
        if topExtent > heightMax:
            size[1] = heightMax - pos[1]

        # set
        update = False
        finish = False
        roi.setPos(pos, update=update, finish=finish)
        roi.setSize(size, update=update, finish=finish)

        roi.stateChanged(finish=False)  # update handles

class KymRoiWidget(QtWidgets.QMainWindow):
    def __init__(self, imgData, header : dict):
        super().__init__(None)
        
        if imgData is None:
            imgData = np.ndarray((1,1), dtype=np.uint8)
        self._imgData = imgData
        self._header = header

        self._minContrast = 0
        self._maxContrast = 50

        self._roiIntensityPlot = {}  # keys are roi
        self._roiPeakPlot = {}  # keys are roi
        self._roiTakeoffPlot = {}  # keys are roi

        # this switches for each selected ROI
        self._detectionParams = KymRoiDetection()

        # self._detectionDict = {
        #     'ltrb' : None,  # [l,t,r,b] of rect roi
        #     'binLineScans' : 1,  # number of line scans to bin in calculating sum
        #     'polarity' : 'pos',
        #     'medianfilter' : True,
        #     'medianfilterkernel' : 3,
        #     'filter' : True,
        #     'prominence' : 0.09,  # 0.09,  # 0.6,  # 4.0 was for sum as percent,   # allow peaks that rise above baseline by this amount
        #     'width (ms)': 15,  #6,  # minimum allowed peak width (ms)
        #     'distance (ms)': 150,  #50,  # refractory period, minimal allowable time (ms) between peaks
        #     'thresh_rel_height' : 0.85,  #0.75,  # find threshold as 'width' at this fraction of height. 0 is peak, 1 is baseline
        #     'decay_rel_height' : 0.85,  # find return to baseline as 'width' at this fraction of height. 0 is peak, 1 is baseline
        #     'decay (ms)': 50,  # 50,  # number of bins to fit decay from peak
        #     # 'peakClipBins': 40,  # Number of bins in spike clips (length is 2*bins)
        # }

        self._blockSlots = False
        
        # get rid of this
        self._analysisResults = {}

        # use this
        self._analysisDf = {}

        self._isDirty = False

        self._buildUI()

        self._backgroundRoi = oneRoiRect(pos=(0,0), size=(100,100),
                                         imageItem=self.myImageItem,
                                         imgData=self._imgData,
                                         label='Background')
        self._backgroundRoi.signalRoiChanged.connect(self._background_roi_changed)

        self.roiList = RoiManager(self.view, self.myImageItem, self._imgData, self._header)
        self.roiList.signalRoiChanged.connect(self._roi_changed)
        self.roiList.signalSelectRoi.connect(self.selectRoi)

        # re-wire right-click
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu)

        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)

        self.setWindowTitle(self.path)

        # logger.debug('adding default roi')
        # self.addRoi()

        #
        # important
        self.switchFile(imgData, header)
        self.loadAnalysis()  # load from folder with text file analysis (if it exists)

        #kw.addRoi([0, 801, 2999, 578])

    @property
    def _detectionDict(self):
        """Current selected ROI detection params.
        """
        return self._detectionParams


    def getDirty(self):
        return self._isDirty
    
    def mySetStatusbar(self, text):
        self.statusBar.showMessage(text)  # ,2000)

    @property
    def path(self):
        return self._header['path']

    @property
    def umPerPixel(self):
        return self._header['umPerPixel']
    
    @property
    def secondsPerLine(self):
        return self._header['secondsPerLine']
    
    def switchFile(self, imgData, header):
        self._imgData = imgData
        self._header = header

        logger.info(f'imgData:{imgData.shape} header:{self._header}')

        self.roiList.switchFile(imgData, header)

        self._minContrast = np.min(self._imgData)
        self._maxContrast = int(np.max(self._imgData) / 2)

        # update gui
        self.minContrastSlider.setValue(self._minContrast)
        self.maxContrastSlider.setValue(self._maxContrast)

        imageRect = self.getImageRect()  # l,b,h,w
        # logger.info(f'    imageRect:{imageRect}')  # [0,0,5,113]

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

    def _background_roi_changed(self, ltrb : List[int]):
        logger.info(f'ltrb:{ltrb}')
        self._isDirty = True

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
                self._detectionParams = self._analysisResults[roi]['detectionParams']
                self._updateDetectionParamGui()
            except (KeyError) as e:
                logger.error(f'TODO: ok on load -->> {e}')

        self.updateRoiIntensityPlot(roi, doAnalysis=False, refreshScatter=False)

    @property
    def imgData(self):
        return self._imgData
    
    def _updateDetectionParamGui(self):
        # {'ltrb': [0, 545, 2999, 383], 'medianfilter': True, 'medianfilterkernel': 3, 'filter': True, 'prominence': 3.9999999999999996, 'width': 6, 'distance': 100, 'thresh_rel_height': 0.75}
        
        # ['Median Filter', 'Savitzky-Golay', 'Prominence', 'Width', 'Distance']
        # logger.info(self._detectionControls.keys())

        self._blockSlots = True
        
        detectionParamDict = self._detectionParams
        
        logger.info('')
        print(detectionParamDict.printValues())

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

        self._blockSlots = False

    def _builtDetectionToolbar(self) -> "QVBoxLayout":
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
        aSpinBox.setRange(0,200)
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

        return vLayout

    def _buildContrastSliders(self) -> QtWidgets.QHBoxLayout:
        
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

        return hBox
    
    def _onContrastSliderChanged(self, value, name):
        logger.info(f'name:{name} value:{value}')

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

    def _buildTopToolbar(self) -> QtWidgets.QHBoxLayout:
        hLayout = QtWidgets.QHBoxLayout()
        hLayout.setAlignment(QtCore.Qt.AlignLeft)

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

        aCheckBoxName = 'Clips'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle peak clips on/off')
        aCheckBox.setChecked(True)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout.addWidget(aCheckBox)

        aCheckBoxName = 'Scatter'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle scatter plot on/off')
        aCheckBox.setChecked(True)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout.addWidget(aCheckBox)

        # aCheckBoxName = 'Tables'
        # aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        # aCheckBox.setToolTip('Toggle yables on/off')
        # aCheckBox.setChecked(True)  # show by default
        # aCheckBox.stateChanged.connect(
        #     partial(self._on_checkbox_clicked, aCheckBoxName)
        # )
        # hLayout.addWidget(aCheckBox)

        # TODO: put this somewhere better
        self.hoverLabel = QtWidgets.QLabel(None)
        hLayout.addWidget(self.hoverLabel, alignment=QtCore.Qt.AlignRight)

        return hLayout
    
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

        elif name == 'Width (ms)':
            self._detectionDict['width (ms)'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Distance (ms)':
            self._detectionDict['distance (ms)'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Decay (ms)':
            self._detectionDict['decay (ms)'] = value
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

    def _on_checkbox_clicked(self, name, value):
        if self._blockSlots:
            # logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return

        if value > 1:
            value = 1
        logger.info(f'name:{name} value:{value}')

        # if name == 'ROIs':
        #     logger.info('TODO: toggle image ROIs on/off')
        #     pass

        if name == 'Median Filter':
            self._detectionDict['medianfilter'] = value == 1
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Savitzky-Golay':
            self._detectionDict['filter'] = value == 1
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Clips':
            self.peakClipsWidget.setVisible(value)

        elif name == 'Scatter':
            self.simpleScatter.setVisible(value)

        # elif name == 'Tables':
        #     self.peakClipPlotItem.setVisible(value)

        # plot overlays
        elif name == 'Threshold':
            self._overlayPlotDict['Threshold'].setVisible(value)
        elif name == 'Decay':
            self._overlayPlotDict['Decay'].setVisible(value)
        elif name == 'Peak':
            self._overlayPlotDict['Peak'].setVisible(value)
        elif name == 'Half-width':
            self._overlayPlotDict['Half-width'].setVisible(value)
        elif name == 'Exp Decay':
            self._overlayPlotDict['Exp Decay'].setVisible(value)
        elif name == 'Dbl Exp Decay':
            self._overlayPlotDict['Dbl Exp Decay'].setVisible(value)

        else:
            logger.info(f'did not understand name:{name}')

    def _on_button_click(self, name : str):
        logger.info(f'name:{name}')
        
        if name == 'ANALYZE':
            self.analyzeRoi()  # analyze the selected ROI
            self.updateRoiIntensityPlot(doAnalysis=False)

        elif name == 'Add ROI':
            # pos, size = self._getDefaultRoi()
            self.addRoi()
            # roi = self.roiList.addRoi()
            # self.addIntensityPlot(roi)

        elif name =='Delete ROI':
            self.removeSelectedRoi()
            # roi = self.roiList.removeSelectedRoi()
            # if roi is not None:
            #     self.deleteIntensityPlot(roi)

        elif name == 'Reset':
            self._detectionParams.setDefaults()
            self._updateDetectionParamGui()

    def removeSelectedRoi(self):
        """Remove from manager and plot.
        """
        roi = self.roiList.removeSelectedRoi()
        if roi is not None:
            self.deleteIntensityPlot(roi)
            self._isDirty = True

    def addRoi(self, ltrbRoi = None, doAnalysis=True, doSelect=True):
        roi, roiLabel = self.roiList.addRoi(ltrbRoi=ltrbRoi, doSelect=doSelect)
        
        self.addIntensityPlot(roi, doAnalysis=doAnalysis)
        
        self.mySetStatusbar(f'Added ROI {roiLabel}')
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

        _contrastSliders = self._buildContrastSliders()
        vBoxPlot.addLayout(_contrastSliders)

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

        # now using transpose .T
        # axisOrder = "row-major"
        # self.myImageItem = pg.ImageItem(self.getContrastEnhance().T)  # need transpose for row-major
        
        # switching to PyMapManager style contrast with setLevels()
        # self.myImageItem = pg.ImageItem(self.getContrastEnhance(), axisOrder = "row-major")  # need transpose for row-major
        self.myImageItem = pg.ImageItem(self.imgData, axisOrder = "row-major")  # need transpose for row-major

        # from pg import colormap
        # cm = pg.colormap.get('Greens_r', source='matplotlib')
        # cm = pg.colormap.get('Reds_r', source='matplotlib')
        # cm = pg.colormap.get('Greys_r', source='matplotlib')  # same as not specifying
        # cm = pg.colormap.get('Greys', source='matplotlib')
        # cm = pg.colormap.get('plasma')
        # cm = pg.colormap.get('viridis')
        # self.myImageItem.setColorMap(cm)

        self.setColorMap('Green')

        # we use this in PyMapMAnager
        # self.myImageItem.setLookupTable()
        # _colorLut = xxx
        # _updateLUT = True
        # self.myImageItem.setLookupTable(colorLut, update=_updateLUT)

        self.kymographPlot.addItem(self.myImageItem, ignorBounds=True)

        # redirect hover to self (to display intensity
        self.myImageItem.hoverEvent = self._hoverEvent

        vBoxPlot.addWidget(self.view)
    
        #
        # 4) sum intensity of each line scan
        self.sumIntensityPlotItem = pg.PlotWidget()
        self.sumIntensityPlotItem.setDefaultPadding()
        self.sumIntensityPlotItem.enableAutoRange()
        self.sumIntensityPlotItem.setMouseEnabled(x=True, y=False)
        self.sumIntensityPlotItem.hideButtons()  # hide the little 'A' button to rescale axis

        self.sumIntensityPlotItem.setLabel("left", 'Intensity (pixel)', units="")
        self.sumIntensityPlotItem.setLabel("bottom", 'Time (s)', units="")
        self.sumIntensityPlotItem.setXLink(self.kymographPlot)

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

        #
        # peak clips
        # self.peakClipPlotItem = pg.PlotWidget()
        # self.peakClipPlotItem.setLabel("left", "Intensity (%)", units="")
        # self.peakClipPlotItem.setLabel("bottom", "Time (s)", units="")
        # vBoxForClipsScatterTable.addWidget(self.peakClipPlotItem)

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
        
        self.myImageItem.setColorMap(cm)
    
    def getSumIntRoi(self, roi, binLineScans=1):
        """Get the sum of intensity for each line scan.
        """
        
        # get part of image in roi
        roiImg = self.roiList.getImgData(roi)
        
        #
        # background subtract
        # backgroundImgData = self._backgroundRoi.getImgData()
        # backgroundMean = round(np.mean(backgroundImgData))
        # backgroundMean = int(backgroundMean)

        # CRITICAL, NEED TO CAST TO A SIGNED INTEGER
        roiImg = roiImg.astype(np.int64)

        # 20240920, background subtract with rolling ball
        _rollingBallRadius = 50
        logger.info(f'calling restoration.rolling_ball on roiImg:{roiImg.shape} _rollingBallRadius:{_rollingBallRadius}')

        background = restoration.rolling_ball(roiImg, radius=_rollingBallRadius)
        logger.info(f'   after _rollingBallRadius:{_rollingBallRadius} background:{background.shape} {background.dtype} min:{np.min(background)} max:{np.max(background)} mean:{np.mean(background)}')

        # logger.info(f'background subtraction backgroundImgData:{backgroundImgData.shape} backgroundMean:{backgroundMean} {type(backgroundMean)}')
        
        logger.info(f'     before roiImg:{roiImg.shape} {roiImg.dtype} min:{np.min(roiImg)} max:{np.max(roiImg)} mean:{np.mean(roiImg)}')
        
        # do background subtract
        # roiImg = roiImg - backgroundMean
        roiImg -= background

        # reject negative intensities
        roiImg[roiImg<0] = 0

        logger.info(f'     after roiImg:{roiImg.shape} {roiImg.dtype} min:{np.min(roiImg)} max:{np.max(roiImg)} mean:{np.mean(roiImg)}')

        # binLineScans = self.detectionParams.getParam('binLineScans')
        if binLineScans > 1:
            logger.info(f"sum intensity in roi - will be expensive on binLineScans:{binLineScans} - roiImg:{roiImg.shape}")
            roiImg = roiLineProfilePool(roiImg, lineWidth=binLineScans)

        [left, t, right, b] = self.roiList._roiAsRect(roi)  # pixels

        # xPlot is in physical units
        # xPlot = np.arange(roi.pos()[0], roi.pos()[0]+roi.size()[0])
        xPlot = np.arange(left, right, dtype=np.float32)
        # logger.info(f'xPlot:{xPlot.shape} {xPlot.dtype} secondsPerLine:{type(self.secondsPerLine)}')
        xPlot *= self.secondsPerLine

        yPlot = roiImg.sum(axis=0)

        # normalize sum to 0..100
        # yPlot = yPlot / np.max(yPlot) * 100

        # normalize sum to pixel intensity
        # logger.info(f'normalizing each line scan to num pixels in scan: {roiImg.shape[0]}')
        yPlot = yPlot / roiImg.shape[0]

        # convert to (f-f_0)/f_0
        # _mean = yPlot.mean(axis=0)
        _f0 = np.mean(yPlot)
        logger.info(f'_mean of yPlot is _f0:{_f0}')
        yPlot = (yPlot - _f0) / _f0  # (f - f_0) / f_0

        # logger.warning(f'len xPlot:{len(xPlot)} yPlot:{len(yPlot)}')

        return xPlot, yPlot
    
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

        self._overlayPlotDict['Peak'] = self.sumIntensityPlotItem.plot(name="sumIntensityPeaksPlot",
                                                  pen=None,
                                                  symbol='o',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(0, 255, 0, 220)
                                                  )

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

    def addIntensityPlot(self, roi, doAnalysis=True):
        """Add an roi to the sum plot.
        """
        sumIntensityPlot = self.sumIntensityPlotItem.plot(name="sumIntensityPlot",
                                                        #   symbol='o',
                                                        #   brush=pg.mkBrush(100, 255, 100, 220),
                                                        )        
        self._roiIntensityPlot[roi] = sumIntensityPlot
        
        # update
        self.updateRoiIntensityPlot(roi, doAnalysis=doAnalysis)

    def deleteIntensityPlot(self, roi):
        """Delete an roi from the gui.

         - intensity plot (and overlay)
         - clip plot
         - scatter plot
        """
        roiIntensityPlot = self._roiIntensityPlot.pop(roi, None)
        self.sumIntensityPlotItem.removeItem(roiIntensityPlot)

        # don't remove, just blank (these are same for each roi)
        for _plotName, oneOverlayPlot in self._overlayPlotDict.items():
            oneOverlayPlot.setData([], [])
        
        # clear clips
        # self._roiClipPlot[roi].setData([], [])

        # refresh scatter
        _kymRoiResults = self._analysisDf.pop(roi, None)
        # logger.info(f'popped _kymRoiResults:{_kymRoiResults}')
        self.refreshScatter()

    def _findPeaks(self, y):
        
        prominence = self._detectionDict['prominence']
        width = self._detectionDict['width (ms)'] / 1000 / self.secondsPerLine
        distance = self._detectionDict['distance (ms)'] / 1000 / self.secondsPerLine

        rel_height = 0.5  # to get half-width

        logger.info(f'prominence:{prominence} width:{width} distance:{distance} rel_height:{rel_height}')

        xPeaks = find_peaks(y,
                            prominence=prominence,
                            width=width,
                            rel_height=rel_height,
                            distance=distance,
                            # threshold=(None,None),
                            # plateau_size=(None,None),
                            )

        return xPeaks
    
    def analyzeRoi(self, roi=None, doQuick=False):
        """Analyze one roi e.g. detect peaks.
        """
        logger.info('   === === === PERFORMING ANALYSIS === === ===')
        print(self._detectionDict.printValues())
        print('')

        if roi is None:
            roi = self.roiList.selectedRoi
        
        if roi is None:
            logger.info('please select an roi to analyze')
            return
        
        # was this
        # xPlot, yPlot = self.getSumIntRoi(roi)
        if doQuick:
            binLineScans = 1
        else:
            binLineScans = self._detectionDict['binLineScans']
        logger.info(f'fetching binLineScans() with binLineScans:{binLineScans} -->> SLOW')
        xPlot, yPlot = self.getSumIntRoi(roi, binLineScans=binLineScans)
    
        #
        # TEST bin line scan
        # tmpBinLineScans = 3
        # xPlot2, yPlot2 = self.getSumIntRoi(roi, binLineScans=tmpBinLineScans)
        # tmpBinLineScans = 5
        # xPlot3, yPlot3 = self.getSumIntRoi(roi, binLineScans=tmpBinLineScans)
        # # plt.plot(xPlot, yPlot, 'k')  # original
        # plt.plot(xPlot2, yPlot2, 'r')
        # plt.plot(xPlot3, yPlot3, 'b')
        # plt.show()

        # from scipy.signal import detrend
        # yPlot =detrend(yPlot) ##, axis=-1, type='constant', bp=0, overwrite_data=True)
        
        if self._detectionDict['medianfilter']:
            # 1) medfilt
            medianfilterkernel = self._detectionDict['medianfilterkernel']
            # logger.info(f'   applying median filter with medianfilterkernel:{medianfilterkernel}')
            yPlot = medfilt(yPlot, kernel_size=medianfilterkernel)

        if self._detectionDict['filter']:
            # 2) SavitzkyGolay_Filter
            # logger.info(f'   applying Savitzky-Golay filter')
            yPlot = getSavitzkyGolay_Filter(yPlot)

        # yDetrend = myDetrend(xPlot, yPlot)
        # logger.warning('USING double exp detrend !!!')
        # yPlot = yDetrend

        #
        if self._detectionDict['polarity'] == 'Neg':
            detectThisY = -yPlot
        else:
            detectThisY = yPlot

        peakResults = self._findPeaks(detectThisY)  # detect peaks
        xPeaksBins = peakResults[0] # time of peak in POINTS
        peakDict = peakResults[1]  # dict of features (all in points)

        if self._detectionDict['polarity'] == 'Neg':
            peakDict['width_heights'] = -peakDict['width_heights']

        # try and use peak width to get esitmate of threshold
        # peak_widths() info is returned from find peaks
        # rel_height = 0.75  # 0.8  # 0.9
        thresh_rel_height = self._detectionDict['thresh_rel_height']  # 1 is foot, 0 is peak
        logger.info(f'using peak_widths() with thresh_rel_height:{thresh_rel_height} to try and get onset threshold???')
        _peakWidths = peak_widths(detectThisY, xPeaksBins,
                                  rel_height=thresh_rel_height,
                                  prominence_data=None,
                                  wlen=None)
        # logger.info('   _peakWidths from peak_widths() is:')
        peakWidthDict = {
            # 'widths' : _peakWidths[0],
            # 'width_heights' : _peakWidths[1],
            'left_ips' : _peakWidths[2],  # ip is 'interpolated position': Interpolated positions of left and right intersection points of a horizontal line at the respective evaluation height.
            # 'right_ips' : _peakWidths[3],
        }
        peakDict['myThresholdBin'] = peakWidthDict['left_ips']
        peakDict['timeToPeakBins'] = np.subtract(xPeaksBins, peakDict['myThresholdBin'])

        # for k,v in peakWidthDict.items():
        #     print(f'   "{k}": {v.dtype} {v}')

        #
        decay_rel_height = self._detectionDict['decay_rel_height']  # 1 is foot, 0 is peak
        logger.info(f'TODO: implement time to decay -> need good estimate of when we return to baseline -> using decay_rel_height:{decay_rel_height}')
        _peakWidthsDecay = peak_widths(detectThisY, xPeaksBins,
                                  rel_height=decay_rel_height,
                                  prominence_data=None,
                                  wlen=None
                                  )
        # logger.info('   _peakWidthsDecay from peak_widths() is:')
        _peakWidthsDecayDict = {
            # 'widths' : _peakWidthsDecay[0],
            # 'width_heights' : _peakWidthsDecay[1],
            # 'left_ips' : _peakWidthsDecay[2],  # ip is 'interpolated position': Interpolated positions of left and right intersection points of a horizontal line at the respective evaluation height.
            'right_ips' : _peakWidthsDecay[3],
        }
        # peakDict['myThresholdBin2'] = _peakWidthsDecayDict['right_ips']

        numPeaks = len(xPeaksBins)
        yPeaks = []
        if numPeaks>0:
            yPeaks = yPlot[xPeaksBins]

        # logger.info('TODO: handle reduced (non 0) left roi')
        [left, top, right, bottom] = self.roiList._roiAsRect(roi)
        xPeaksBins = xPeaksBins + left
        peakDict['left_ips'] = peakDict['left_ips'] + left
        peakDict['right_ips'] = peakDict['right_ips'] + left
        peakWidthDict['left_ips'] = peakWidthDict['left_ips'] + left
        _peakWidthsDecayDict['right_ips'] = _peakWidthsDecayDict['right_ips'] + left

        # store raw data
        self._detectionDict['ltrb'] = self.roiList._roiAsRect(roi)
        self._analysisResults[roi] = {
            'detectionParams' : KymRoiDetection(kymRoiDetection=self._detectionDict),  # store analysis parameters used
            'xPlot' : xPlot,
            'yPlot' : yPlot,
        }

        oneRoiResults = KymRoiResults()
        self._analysisDf[roi] = oneRoiResults  # immediately add to analysis

        self._isDirty = True

        if numPeaks == 0:
            return
        
        # IMPORTANT, do this first to seed proper number of rows
        oneRoiResults.setValues('Peak Number', range(1,numPeaks+1))

        oneRoiResults.setValues('Path', self.path)

        oneRoiResults.setValues('Accept', True)  # all peaks start as Accept=True
        oneRoiResults.setValues('Detection Errors', '')  # all peaks start as errors = ''
        
        roiLabelText = self.roiList.roiLabelList[roi].toPlainText()
        roiLabelNumber = int(roiLabelText)
        oneRoiResults.setValues('ROI Number', roiLabelNumber)

        oneRoiResults.setValues('Peak Bin', xPeaksBins)

        _peakSeconds = xPeaksBins * self.secondsPerLine
        oneRoiResults.setValues('Peak Second', _peakSeconds)

        # inter-peak-interval (seconds)
        _peakInterval = np.diff(_peakSeconds)
        _peakInterval = np.insert(_peakInterval, 0, np.nan)  # insert np.nan as first (0) element
        oneRoiResults.setValues('Peak Interval (s)', _peakInterval)
        oneRoiResults.setValues('Peak Freq (Hz)', 1 / _peakInterval)

        oneRoiResults.setValues('Peak', yPeaks)
        
        # take off threshold
        thresholdBin = np.round(peakWidthDict['left_ips'])
        thresholdBin = thresholdBin.astype(np.int64)  # use this as list index
        
        oneRoiResults.setValues('Threshold Bin Fraction', peakWidthDict['left_ips'])  # threshold in fractional bins
        oneRoiResults.setValues('Threshold Bin', thresholdBin)  # potentially sloppy
        oneRoiResults.setValues('Threshold Second', peakWidthDict['left_ips']  * self.secondsPerLine)
        oneRoiResults.setValues('Threshold Value', yPlot[thresholdBin - left])  # yPlot is already reduced to roi (left)
        
        # return to baseline (not great)
        decayBin = np.round(_peakWidthsDecayDict['right_ips'])
        decayBin = decayBin.astype(np.int64)  # use this as list index

        oneRoiResults.setValues('Decay Bin Fraction', _peakWidthsDecayDict['right_ips'])  # threshold in fractional bins
        oneRoiResults.setValues('Decay Bin', decayBin)  # potentially sloppy
        oneRoiResults.setValues('Decay Second', _peakWidthsDecayDict['right_ips']  * self.secondsPerLine)
        oneRoiResults.setValues('Decay Value', yPlot[decayBin - left]) # yPlot is already reduced to roi (left)

        # hw
        oneRoiResults.setValues('HW Left Bin', peakDict['left_ips'])
        oneRoiResults.setValues('HW Right Bin', peakDict['right_ips'])
        oneRoiResults.setValues('HW Height', peakDict['width_heights'])

        hwSeconds = (peakDict['right_ips'] * self.secondsPerLine) - (peakDict['left_ips'] * self.secondsPerLine)
        hwMs = hwSeconds * 1000
        oneRoiResults.setValues('HW (ms)', hwMs)

        # rise and decay time
        riseTimeSeconds = oneRoiResults.getValues('Peak Second') - oneRoiResults.getValues('Threshold Second')  # element wise subtract
        riseTimeMs = riseTimeSeconds *1000
        oneRoiResults.setValues('Rise Time (ms)', riseTimeMs)

        decayTimeSeconds = oneRoiResults.getValues('Decay Second') - oneRoiResults.getValues('Peak Second')  # element wide subtraction
        decayTimeMs = decayTimeSeconds *1000
        oneRoiResults.setValues('Decay Time (ms)', decayTimeMs)

        # peak height
        peakHeight = np.subtract(oneRoiResults.getValues('Peak'), oneRoiResults.getValues('Threshold Value'))
        oneRoiResults.setValues('Peak Height', peakHeight)

        # (1) exp fit of each peak
        [_left, _, _, _] = self.roiList._roiAsRect(roi)
        # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine  # TODO: convert to sec or ms
        decayFitBins = self._msToBin(self._detectionDict['decay (ms)'])
        fit_m, fit_tau, fit_b, fit_r2, fit_error = _expFit(xPlot, yPlot, xPeaksBins - _left, decayFitBins=decayFitBins)
        oneRoiResults.setValues('fit_m', fit_m)
        oneRoiResults.setValues('fit_tau', fit_tau)
        oneRoiResults.setValues('fit_b', fit_b)
        oneRoiResults.setValues('fit_r2', fit_r2)
        # logger.info(f'fit_error is:{fit_error}')
        for _peakErrorIdx, oneError in enumerate(fit_error):
            if oneError != '':
                oneRoiResults.addError(_peakErrorIdx, oneError)

        # (2) double exp fit of each peak
        [_left, _, _, _] = self.roiList._roiAsRect(roi)
        # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine  # TODO: convert to sec or ms
        decayFitBins = self._msToBin(self._detectionDict['decay (ms)'])
        fit_m1, fit_tau1, fit_m2, fit_tau2, fit_r22, fit_error = _expFit2(xPlot, yPlot, xPeaksBins - _left, decayFitBins=decayFitBins)
        oneRoiResults.setValues('fit_m1', fit_m1)
        oneRoiResults.setValues('fit_tau1', fit_tau1)
        oneRoiResults.setValues('fit_m2', fit_m2)
        oneRoiResults.setValues('fit_tau2', fit_tau2)
        oneRoiResults.setValues('fit_r22', fit_r22)
        # logger.info(f'fit_error is:{fit_error}')
        for _peakErrorIdx, oneError in enumerate(fit_error):
            if oneError != '':
                oneRoiResults.addError(_peakErrorIdx, oneError)

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
            return self._analysisDf[roi].df
        else:
            columns = list(KymRoiResults.analysisDict.keys())
            df = pd.DataFrame(columns=columns)  # empty df with proper columns
            for _roiIdx, oneRoi in enumerate(self._analysisDf.keys()):
                oneDf = self._analysisDf[oneRoi].df
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
    
    def _getSaveFolder(self, createFolder=True):
        _folder, _ = os.path.split(self.path)  # folder the raw tif is in
        
        _folder = os.path.join(_folder, 'sanpy-kym-roi-analysis')
        if createFolder and not os.path.isdir(_folder):
            os.mkdir(_folder)
        
        return _folder
    
    def _getSaveFile(self, createFolder=True):
        """Get full path to file to save/load analysis.
        """
        saveFolder = self._getSaveFolder(createFolder=createFolder)

        _, _file = os.path.split(self.path)  # folder the raw tif is in
        
        _saveFile = os.path.splitext(_file)[0]

        saveFilePeaks = _saveFile + '-roiPeaks.csv'  # peaks
        saveFilePeaks = os.path.join(saveFolder, saveFilePeaks)

        saveFileInt = _saveFile + '-roiInt.csv'  # intensity
        saveFileIntPath = os.path.join(saveFolder, saveFileInt)

        return saveFilePeaks, saveFileIntPath
    
    def saveAnalysisResults(self):
        """Save all roi time and intensity in one dataframe (csv).
        """
        peakPath, intPath = self._getSaveFile()

        df = pd.DataFrame()

        # get the largest number of rows from all roi (e.g. right-left rect roi)
        maxNumRows = 0
        for roi in self.roiList.roiList.keys():
            resultDict = self._analysisResults[roi]
            xPlot = resultDict['xPlot']
            rows = xPlot.shape[0]
            if rows > maxNumRows:
                maxNumRows = rows

        for roi in self.roiList.roiList.keys():
            roiLabel = self.roiList.roiLabelList[roi].toPlainText()

            timeCol = f'ROI{roiLabel}_time'
            intCol = f'ROI{roiLabel}_int'

            resultDict = self._analysisResults[roi]
            xPlot = resultDict['xPlot']
            yPlot = resultDict['yPlot']

            # logger.info(f'timeCol:{timeCol} intCol:{intCol}')
            # logger.info(f'df:{len(df)} xPlot:{xPlot.shape} yPlot:{yPlot.shape}')

            df[timeCol] = [np.nan] * maxNumRows
            df[intCol] = [np.nan] * maxNumRows
            
            # print('   orig df is:')
            # print(df)

            df.loc[0:xPlot.shape[0]-1, timeCol] = xPlot
            df.loc[0:yPlot.shape[0]-1, intCol] = yPlot
            
            # print('df is now:')
            # print(df)

        logger.info(f'saving intensity to: {intPath}')
        df.to_csv(intPath, index=False)

    def saveAnalysis(self):
        """Save all peak analysis into one csv file.

        This includes a header with roi [l,t,r,b] and detection parameters used.
        """

        # one line header with all rois name=[l,t,r,b]
        
        # TODO: we also need to save the detection parameters for each roi
        
        if not self._isDirty:
            _noSaveStr = 'No changes to save.'
            logger.info(_noSaveStr)
            self.mySetStatusbar(_noSaveStr)
            return
        
        _fileHeaderDict = {}

        # add backgroundRoi
        _fileHeaderDict['backgroundRoi'] = self._backgroundRoi._roiAsRect()

        for roi in self.roiList.roiList.keys():
            # what was used for detection, including [l,t,r,b] of rect roi
            _detectionDict = self._analysisResults[roi]['detectionParams']  # KymRoiDetection()
            # text label of roi
            roiLabelText = self.roiList.roiLabelList[roi].toPlainText()
            
            _fileHeaderDict[roiLabelText] = _detectionDict.getValueDict()  # just key value pairs for detection parameters

        # one line json header with all roi and their detection params
        # logger.info(f'_fileHeaderDict:{_fileHeaderDict}')
        _fileHeaderJson = json.dumps(_fileHeaderDict)
        
        # print('_fileHeaderJson')
        # print(_fileHeaderJson)

        savePath, intPath = self._getSaveFile()
        logger.info(f'saving to: {savePath}')

        dfToSave = self.getDataFrame()
        
        # logger.info('saving df')
        # print(dfToSave)

        with open(savePath, 'w') as f:
            f.write(_fileHeaderJson)
            f.write('\n')
            f.write(dfToSave.to_csv(header=True, index=False, mode='a'))

        self.saveAnalysisResults()

        self._isDirty = False

        self.mySetStatusbar(f'Saved {savePath}')

    def loadAnalysis(self):
        savePath, intPath = self._getSaveFile(createFolder=False)
        if not os.path.isfile(savePath):
            logger.info(f'did not find file to load:{savePath}')
            return
        
        logger.info(f'loading analysis from: {savePath}')

        with open(savePath) as f:
            headerJson = f.readline()
            _headerDict = json.loads(headerJson)

        dfLoadedFromFile = pd.read_csv(savePath, header=1)
        
        # logger.info('dfLoadedFromFile')
        # print(dfLoadedFromFile)

        # logger.info(f'loaded _headerDict {savePath}')
        # for k,v in _headerDict.items():
        #     print(f'   {k}: {v}')

        loadedIntDf = pd.read_csv(intPath)

        # _headerDict is a dict with roi name keys, make a number of rois
        # self._detectionDict = _headerDict
        _firstRoi = None
        for _roiIndex, (roiNumber,detectionDict) in enumerate(_headerDict.items()):
            # roiNumber is like 1,2,3,...
            # logger.info(f'   {roiNumber} {type(roiNumber)}: {detectionDict}')
            
            if roiNumber == 'backgroundRoi':
                logger.warning(f'TODO: assign background roi to detectionDict:{detectionDict}')
                ltrb = detectionDict['ltrb']
                self._backgroundRoi.setPosSize(ltrb)
                continue

            kymRoiDetection = KymRoiDetection(fromDict=detectionDict)

            # add the roi
            roi = self.addRoi(kymRoiDetection['ltrb'], doAnalysis=False, doSelect=False)

            # set xPlot and yPlot from int file
            # ROI1_time,ROI1_int
            timeCol = f'ROI{roiNumber}_time'
            intCol = f'ROI{roiNumber}_int'
            
            xPlot = loadedIntDf[timeCol]
            xPlot = xPlot[~np.isnan(xPlot)]
            
            yPlot = loadedIntDf[intCol]
            yPlot = yPlot[~np.isnan(yPlot)]

            self._analysisResults[roi] = {
                'detectionParams' : kymRoiDetection,  # on load, no copy
                'xPlot' : xPlot,
                'yPlot' : yPlot,
            }

            #
            # fill in analysis results
            oneRoiResults = KymRoiResults()
            dfRoi = dfLoadedFromFile[ dfLoadedFromFile['ROI Number']==int(roiNumber) ]
            dfRoi = dfRoi.reset_index(drop=True)  # Do not try to insert index into dataframe columns.
            oneRoiResults._swapInNewDf(dfRoi)
            self._analysisDf[roi] = oneRoiResults

            # logger.info(f'_roiIndex:{_roiIndex}')
            if _firstRoi is None:
                _firstRoi = roi

        self._isDirty = False

        # once the roi is fully loaded, update the interface
        # _firstRoi = list(self._analysisResults.keys())[0]  # assuming >0 roi
        # self.roiList._selectRoi(_firstRoi)

        self.refreshScatter()

        if _firstRoi is not None:
            self.roiList._selectRoi(_firstRoi)  # tell roi manager to select and will propogate

        _str = f'Loaded {self.roiList.numRoi} ROIs from {savePath}'
        self.mySetStatusbar(_str)

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
        for oneRoi in self._roiIntensityPlot.keys():
            self._roiIntensityPlot[oneRoi].setData([],[])

        for k,v in self._overlayPlotDict.items():
            v.setData([], [])

        # perform analysis
        logger.warning(f'turned off auto analysis - implementing "Analyze" button doAnalysis:{doAnalysis}')
        if doAnalysis:
            # self._detectionDict['binLineScans']
            self.analyzeRoi(roi, doQuick=True)

        if roi not in self._analysisResults.keys():
            logger.warning(f'did not find roi:{roi} in _analysisResults.keys()')
            return
                
        #
        # raw data
        resultDict = self._analysisResults[roi]
        xPlot = resultDict['xPlot']
        yPlot = resultDict['yPlot']
        self._roiIntensityPlot[roi].setData(xPlot, yPlot, connect="finite")  # fill with nan
        
        #
        # analysis results
        dfPlot = self._analysisDf[roi].df
        numPeaks = len(dfPlot)

        peakSecond = dfPlot['Peak Second']
        yPeak = dfPlot['Peak']
        self._overlayPlotDict['Peak'].setData(peakSecond, yPeak)

        thresholdSecond = dfPlot['Threshold Second']
        thresholdValue = dfPlot['Threshold Value']
        self._overlayPlotDict['Threshold'].setData(thresholdSecond, thresholdValue)

        decaySecond = dfPlot['Decay Second']
        decayValue = dfPlot['Decay Value']
        self._overlayPlotDict['Decay'].setData(decaySecond, decayValue)

        # half width
        xHalfwidth = []
        yHalfwidth = []
        for _peakIdx in range(numPeaks):
            xHalfwidth.append( dfPlot['HW Left Bin'][_peakIdx] * self.secondsPerLine )
            xHalfwidth.append( dfPlot['HW Right Bin'][_peakIdx] * self.secondsPerLine )
            xHalfwidth.append( np.nan )

            yHalfwidth.append( dfPlot['HW Height'][_peakIdx] )
            yHalfwidth.append( dfPlot['HW Height'][_peakIdx] )
            yHalfwidth.append( np.nan )

        self._overlayPlotDict['Half-width'].setData(xHalfwidth, yHalfwidth)

        #
        # (1) exp decay
        xDecay = []
        yDecay = []
        _peakBins = dfPlot['Peak Bin']
        for _peakIdx, _peakBin in enumerate(_peakBins):
            
            # fix this constant bug !!!!
            [_left, _, _, _] = self.roiList._roiAsRect(roi)
            _peakBin = _peakBin - _left
            
            fit_m = dfPlot['fit_m'][_peakIdx]            
            fit_tau = dfPlot['fit_tau'][_peakIdx]
            fit_b = dfPlot['fit_b'][_peakIdx]

            if np.isnan(fit_m):
                logger.warning(f'no exp fit for peak {_peakIdx}')
                continue

            # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine
            decayFitBins = self._msToBin(self._detectionDict['decay (ms)'])
            _xRange = xPlot[_peakBin:_peakBin+decayFitBins] - xPlot[_peakBin]
            
            # get line showing our fit
            fit_y = myMonoExp(_xRange, fit_m, fit_tau, fit_b)

            xDecay.extend(_xRange+xPlot[_peakBin])
            xDecay.append(np.nan)

            yDecay.extend(fit_y)
            yDecay.append(np.nan)

        self._overlayPlotDict['Exp Decay'].setData(xDecay, yDecay)

        #
        # (2) double exp decay
        xDecay = []
        yDecay = []
        _peakBins = dfPlot['Peak Bin']
        for _peakIdx, _peakBin in enumerate(_peakBins):
            
            # fix this constant bug !!!!
            [_left, _, _, _] = self.roiList._roiAsRect(roi)
            _peakBin = _peakBin - _left
            
            fit_m1 = dfPlot['fit_m1'][_peakIdx]            
            fit_tau1 = dfPlot['fit_tau1'][_peakIdx]
            fit_m2 = dfPlot['fit_m2'][_peakIdx]            
            fit_tau2 = dfPlot['fit_tau2'][_peakIdx]

            if np.isnan(fit_m1):
                # logger.warning(f'no fit for peak {_peakIdx}')
                continue

            # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine
            decayFitBins = self._msToBin(self._detectionDict['decay (ms)'])
            _xRange = xPlot[_peakBin:_peakBin+decayFitBins] - xPlot[_peakBin]
            
            # get line showing our fit
            fit_y = myDoubleExp(_xRange, fit_m1, fit_tau1, fit_m2, fit_tau2)

            xDecay.extend(_xRange+xPlot[_peakBin])
            xDecay.append(np.nan)

            yDecay.extend(fit_y)
            yDecay.append(np.nan)

        self._overlayPlotDict['Dbl Exp Decay'].setData(xDecay, yDecay)

        # refresh cursors
        self._sanpyCursors._showInView()

        #
        # peak clips
        self.plotPeakClips(roi)

        #
        # refresh scatter plot
        if refreshScatter:
            self.refreshScatter()  # update all

    def refreshScatter(self, roi = None):
        if roi is not None:
            df = self._analysisDf[roi].df
        else:
            df = self.getDataFrame()  # get full dataframe across all 'roi number'
        
        # logger.info('refresh with df')
        # print(df)

        self.simpleScatter.replot(df)

    def plotPeakClips(self, roi):

        # clear
        # logger.info('clearing clip plot')
        # for oneRoi in self._roiClipPlot.keys():
        #     self._roiClipPlot[oneRoi].setData([], [])

        # plot
        # plusMinusBins = 50
        # plusMinusBins = self._detectionDict['peakClipBins']
        # numPntsInClip = plusMinusBins * 2

        # logger.info(f'plusMinusBins:{plusMinusBins} numPntsInClip:{numPntsInClip}')

        # raw data
        resultDict = self._analysisResults[roi]
        yPlot = resultDict['yPlot']

        [left, _, _, _] = self.roiList._roiAsRect(roi)
        # logger.info(f'roi rect left:{left}')

        # analysis results
        dfPlot = self._analysisDf[roi].df
        xPeaks = dfPlot['Peak Bin']
        xPeaks = xPeaks - left

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

    def _old_getContrastEnhance(self, theMin = None, theMax = None) -> np.ndarray:
        """Get contrast enhanced image."""
    
        if theMin is None:
            theMin = self._minContrast
        if theMax is None:
            theMax = self._maxContrast
            
        bitDepth = 8
        dType = self.imgData.dtype  # np.uint8

        lut = np.arange(2**bitDepth, dtype=dType)
        
        #lut = self._getContrastedImage(lut, theMin, theMax, bitDepth)  # get a copy of the image
        if bitDepth == 8:
            lut = np.array(lut, dtype=np.uint8, copy=True)
        else:
            lut = np.array(lut, dtype=np.uint16, copy=True)
        lut.clip(theMin, theMax, out=lut)
        lut -= theMin
        np.floor_divide(
            lut,
            (theMax - theMin + 1) / (2**bitDepth),
            out=lut,
            casting="unsafe",
        )

        theRet = np.take(lut, self.imgData)
        return theRet

    def _resetZoom(self, doEmit=True):
        
        # order matter, do sum then image
        # 
        self.sumIntensityPlotItem.autoRange()  # item=self._roiIntensityPlot[roi]

        self.kymographPlot.autoRange(item=self.myImageItem)

    def keyReleaseEvent(self, event):
    
        key = event.key()
        isShift = key == QtCore.Qt.Key_Shift
        
        if isShift:
            # default is x-zoom
            self.kymographPlot.setMouseEnabled(x=True, y=False)
            self.sumIntensityPlotItem.setMouseEnabled(x=True, y=False)
    
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

        saveFolder = self._getSaveFolder(createFolder=True)
        
        _, _file = os.path.split(self.path)
        _file, _ = os.path.splitext(_file)
        _file = _file + '-' + name + '.png'
        savePath = os.path.join(saveFolder, _file)

        logger.info(f'saving {name} to {savePath}')

        exporter = pg.exporters.ImageExporter(plotItem)
        exporter.export(savePath)
        _ret = f'Saved "{name}" to {savePath}'
        return _ret
    
    def _contextMenu(self, pos):
        logger.info('')
        pos = self.mapToGlobal(pos)

        selectedRoi = self.roiList.selectedRoi

        # build menu
        contextMenu = QtWidgets.QMenu()
        contextMenu.addAction('Full Zoom')
        contextMenu.addSeparator()

        cursorAction = QtWidgets.QAction('Cursors')
        cursorAction.setCheckable(True)
        cursorAction.setChecked(self._sanpyCursors.cursorsAreShowing())
        contextMenu.addAction(cursorAction)

        contextMenu.addAction('Save Kym Image ...')

        saveSumPlotAction = QtWidgets.QAction('Save Sum Plot ...')
        saveSumPlotAction.setEnabled(selectedRoi is not None)
        contextMenu.addAction(saveSumPlotAction)

        saveClipsAction = QtWidgets.QAction('Save Clips ...')
        saveClipsAction.setEnabled(selectedRoi is not None)
        contextMenu.addAction(saveClipsAction)

        contextMenu.addSeparator()
        contextMenu.addAction('Copy Stats Table ...')

        # add menu to select an roi (use this when they visually overlap)
        contextMenu.addSeparator()
        for k, v in self.roiList.roiList.items():
            # logger.info(f'qqq roi menu {k} {v}')
            _key = self.roiList.roiList[k]
            roiLabelText = self.roiList.roiLabelList[k].toPlainText()
            # print(f'   roiLabelText:{roiLabelText}')
            contextMenu.addAction(f'Select ROI: {roiLabelText}')

        # show menu
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

        elif actionText == 'Save Kym Image ...':
            _ret = self.savePlotItemAs(self.kymographPlot, 'kym-image')

        elif actionText == 'Save Sum Plot ...':
            roiLabelText = self.roiList.roiLabelList[selectedRoi].toPlainText()
            _ret = self.savePlotItemAs(self.sumIntensityPlotItem.plotItem, f'sum-plot-roi-{roiLabelText}')

        elif actionText == 'Save Clips ...':
            roiLabelText = self.roiList.roiLabelList[selectedRoi].toPlainText()
            _ret = self.savePlotItemAs(self.peakClipsWidget.peakClipPlotItem.plotItem, f'clip-plot-{roiLabelText}')

        elif actionText == 'Copy Stats Table ...':
            _ret = self.simpleScatter.copyTableToClipboard()
        
        # special case on transition to backend
        elif actionText.startswith('Select ROI'):
            _, roiInt = actionText.split(': ')
            logger.info(f'roiInt:{roiInt}')
            self.selectRoiByLabel(roiInt)

        self.mySetStatusbar(_ret)