import json
import os
import sys
from typing import List, Optional, Dict
from enum import Enum

import numpy as np
import pandas as pd
# import uuid
import tifffile

import scipy.optimize
from scipy.signal import peak_widths, medfilt, savgol_filter, detrend, find_peaks
from skimage import restoration

import matplotlib.pyplot as plt

from sanpy._util import _loadLineScanHeader
from sanpy.kym.kymRoiDetection import KymRoiDetection, getAnalysisDict
from sanpy.kym.kymRoiResults import KymRoiResults
from sanpy.kym.kymRoiMetaData import KymRoiMetaData

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def _printImgStats(imgData:np.ndarray, name:str=''):
    logger.info(f'name:"{name}" imgStats: {imgData.shape} min:{np.min(imgData)} max:{np.max(imgData)}')

def myDetrend(xPlot, yPlot, doPlot=False):
    # from scipy.signal import detrend
    
    y_log = np.log(yPlot)
    try:
        y_log_detrended = detrend(y_log)
    except (ValueError) as e:
        logger.error(f'got -inf in log (is the image empty?) {e} -->> No Detrend')
        return None, None
    
    # y_detrended = np.exp(y_log_detrended)

    try:
        _params, _cov = scipy.optimize.curve_fit(myMonoExp, xPlot, yPlot)
    except (RuntimeError) as e:
        logger.error(f'{e} -->> No Detrend')
        return None, None
    
    _m, _tau, _b = _params
    fit_y = myMonoExp(xPlot, _m, _tau, _b)
    y_minus_single = np.subtract(yPlot, fit_y)

    # try:
    #     _params, _cov = scipy.optimize.curve_fit(myDoubleExp, xPlot, yPlot)
    # except (RuntimeError) as e:
    #     logger.error(e)
    #     logger.error('DID NOT PERFORM dbl exp DETREND')
    #     return None, None
    # _m1, _tau1, _m2, _tau2 = _params
    # fit_y2 = myDoubleExp(xPlot, _m1, _tau1, _m2, _tau2)
    # y_minus_double = np.subtract(yPlot, fit_y2)

    if doPlot:
        plt.plot(xPlot, yPlot, label='raw')
        # plt.plot(xPlot, y_detrended, label='detrended')
        plt.plot(xPlot, fit_y, 'r-', label='exp fit')
        plt.plot(xPlot, y_minus_single, 'k-', label='exp fit 1 detrend')
        
        # plt.plot(xPlot, fit_y2, 'g-', label='exp fit 2')
        # plt.plot(xPlot, y_minus_double, 'c-', label='exp fit 2 detrend')

        plt.legend()
        plt.show()

    # return y_minus_double
    expFitDict = {
        'fn': 'myMonoExp',
        'm': _m,
        'tau': _tau,
        'b': _b,
    }
    return expFitDict, y_minus_single
    # return y_detrended

def myMonoExp(x, m, t, b):
    """
    m: a_0
    t: tau_0
    b: 
    """
    # this triggers
    # "RuntimeWarning: overflow encountered in exp" during search for parameters, just ignor it
    # ret = m * np.exp(-t * x) + b
    try:
        ret = m * np.exp(-t * x) + b
    except (RuntimeWarning) as e:
        logger.error(e)
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
            try:
                _params, _cov = scipy.optimize.curve_fit(myDoubleExp, xRange, yRange)
            except (ValueError) as e:
                fit_error[_peakIdx] += f'peak {_peakIdx} _expFit2:{e}' + ';'
                continue

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
            # fit_error[_peakIdx] += f'peak {_peakIdx} _expFit2:{e}' + ';'
            fit_error[_peakIdx] += f'_expFit2():{e}' + ';'

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
            try:
                _params, _cov = scipy.optimize.curve_fit(myMonoExp, xRange, yRange)
            except (ValueError) as e:
                _errStr = f'_expFit():{e}'
                # logger.error(_errStr)
                fit_error[_peakIdx] += _errStr + ';'
                print(xRange)
                print(yRange)
                continue
            
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
            # _errStr = f'  _peakIdx:{_peakIdx} myMonoExp:{e}'
            _errStr = f'_expFit():{e}'
            # logger.error(_errStr)
            fit_error[_peakIdx] += _errStr + ';'

        if doDebug:
            plt.show()

    return fit_m, fit_tau, fit_b, fit_r2, fit_error

def getSavitzkyGolay_Filter(y: np.ndarray, pnts: int = 5, poly: int = 2, verbose=False):
    """Get SavitzkyGolay filtered version of y using scipy.signal.savgol_filter"""
    if verbose:
        logger.info("")
    filtered = savgol_filter(y, pnts, poly, mode="nearest", axis=0)
    return filtered

class PeakDetectionTypes(Enum):
    intensity = 'Intensity'
    diameter = 'Diameter (um)'
    # diameter = 'diameter'

class KymRoiTraces:
    """Class to hold a number of raw traces for one Kym ROI.

    Each instance of *this is for one channel
    """
    def __init__(self, numLineScans : int, secondsPerLine : float):
        self._analysisTraceList = ['Time (s)',
                                   'intRaw',
                                   'intDetrend',
                                   'df/f0',
                                   'f/f0',
                                   'Divided',
                                   # diameter
                                   'Diameter (um)',
                                   'Left Diameter (um)',
                                   'Right Diameter (um)'
                                   ]

        self._analysisTraces = {}
        """Keys are trace name, values are np.ndarray."""

        for trace in self._analysisTraceList:
            # self._analysisTraces[trace] = np.empty( shape=(0) )
            self._analysisTraces[trace] = np.empty( shape=(numLineScans) )
            self._analysisTraces[trace][:] = np.nan

        # fill in time sec and time bin
        _timeBins = np.arange(0, numLineScans)
        _timeSeconds = _timeBins * secondsPerLine
        self.setTrace2('Time (s)', _timeBins, _timeSeconds)

    def setTrace2(self, traceName, bins : np.ndarray, values : np.ndarray):
        """bins tell us which line scans to set, this accounts for left/right of roi rect.
        """
        if traceName not in self._analysisTraces.keys():
            logger.error(f'traceName "{traceName}" not in keys, available keys are {self._analysisTraces.keys()}')
            return
        
        self._analysisTraces[traceName][:] = np.nan
        self._analysisTraces[traceName][bins] = values

    def getTrace(self, name,
                #  stripNan=False
                 ) -> Optional[np.ndarray]:
        """Get a trace name fomr analysis.
        """
        if name not in self._analysisTraces.keys():
            logger.error(f'did not find trace name "{name}". Available names are {self._analysisTraces.keys()}')
            return
        _ret = self._analysisTraces[name]
        # if stripNan:
        #     _ret = _ret[~np.isnan(_ret)]
        return _ret
    
    def loadTraces(self, roiNumber, loadedIntDf : pd.DataFrame):
        """Load traces from a pandas df.
        
        This is for one kymRoi.
        """
        roiTraceList = self._analysisTraceList
        for roiTrace in roiTraceList:
            colName = f'ROI {roiNumber} {roiTrace}'
            
            if colName not in loadedIntDf.columns:
                # logger.error(f'   did not find trace name "{colName}" column in file')
                # logger.info(f'available columns from file are:{loadedIntDf.columns}')
                continue
            
            oneTrace = loadedIntDf[colName].to_numpy()  # added as_numpy() 20241012
            self._analysisTraces[roiTrace] = oneTrace

    def items(self):
        return self._analysisTraces.items()
    
    def keys(self):
        return self._analysisTraces.keys()
    
    def __getitem__(self, key):
        # to mimic a dictionary
        ret = None
        try:
            ret = self._analysisTraces[key]
        except KeyError:
            logger.error(f'Error getting trace key "{key}" available keys are {self._analysisTraces.keys()}')
            raise
        #
        return ret

    def __setitem__(self, key, value):
        # to mimic a dictionary
        if isinstance(value, list):
            logger.error(f'key:{key} is a list, should be numpy array')
            value = np.ndarray(value)
        try:
            self._analysisTraces[key] = value
        except KeyError as e:
            logger.error(f"{e}")

class KymRoi:
    """One rectangular ROI.

    Has the imgData, detection params, analysis results, and traces for one roi.
    """
    def __init__(self, label : str,
                 imgData : List[np.ndarray],
                 header : dict,
                 ltrbRect : List[int] = None,
                 reuseRoiLabel : str = None,
                 kymRoiAnalysis = None,
                #  mode : str = None
                 ):
        """
        Parameters
        ==========
        label : str
            Unique string label for the roi, usually 1,2,3,..
        imgData : np.ndarray
            Underlying image data. The full image we extract an roi with getRoiImg()
        header : dict
            Requires two keys ('umPerPixel', 'secondsPerline')
        ltrbRect : List[l, t, r, b]
            Seed with this rect, if None than use getDefaultRect()
        reuseRoiLabel : str
            Reuse detection params from this roi (can be None)
        kymRoiAnalysis : KymRoiAnalysis
            Only used to fetch params if reuseRoiLabel is not None
        """
        self._label = label        
        self._imgData : List[np.ndarray] = imgData
        self._header = header
        
        self._ltrbRect : List[int] = ltrbRect

        if ltrbRect is None:
            ltrbRect = self.getDefaultRect()  # needs imgData
        
        self._kymRoiAnalysis : KymRoiAnalysis = kymRoiAnalysis

        # self._mode : str = mode

        self.setRect(ltrbRect)  # will contrain
                
        #self._isDirty = False
        self.setDirty(False)

        _numChannels = self.header['numChannels']
        self._detectioParams = [None] * _numChannels
        self._analysisResults = [None] * _numChannels
        self.kymRoiTraces = [None] * _numChannels
        # self._mode = [None] * _numChannels
        
        # each roi has detection, analysis, and traces for each image channel
        for channel in range(_numChannels):
            
            # self._mode[channel] = mode

            self._detectioParams[channel] = {}
            self._analysisResults[channel] = {}
            
            for peakDetectionType in PeakDetectionTypes:
                if reuseRoiLabel is not None:
                    _reuseKymRoiDetection = kymRoiAnalysis.getDetectionParams(reuseRoiLabel, peakDetectionType, channel)
                    thisDetection = KymRoiDetection(peakDetectionType, kymRoiDetection=_reuseKymRoiDetection)
                else:
                    # uses current defaults set in code
                    thisDetection = KymRoiDetection(peakDetectionType)
                    
                    # abb 20250529 colin
                    # rect will always exist, was created as default if not specified
                    thisDetection.setParam('ltrb', self.getRect())

                if peakDetectionType == PeakDetectionTypes.diameter:
                    thisDetection.setParam('detectThisTrace', 'Diameter (um)')
                    # thisDetection.setParam('Prominence', 2)
                    # thisDetection.setParam('Polarity', 'Neg')

                self._detectioParams[channel][peakDetectionType.name] = thisDetection
                self._analysisResults[channel][peakDetectionType.name] = KymRoiResults()

            numLineScans = imgData[channel].shape[1]
            self.kymRoiTraces[channel] = KymRoiTraces(numLineScans, self.secondsPerLine)
            # traces are basically a df with sum for each line scan, columns are things like (time, raw, norm, int_f0, df_f0)
            # traces are one value per line scan (multiple columns) and shared between peak detection in f0 and diameter

    def setDirty(self, value : bool):
        # logger.info(f'setting to value:{value}')
        self._isDirty = value

    def getDetectionParams(self, channel : int, detectionType : PeakDetectionTypes) -> KymRoiDetection:
        return self._detectioParams[channel][detectionType.name]
    
    def setDetection(self, channel, detectionType : PeakDetectionTypes, kymRoiDetection : KymRoiDetection):
        """Set detection params for a channel.
        """
        self._detectioParams[channel][detectionType.name] = kymRoiDetection
        self.setDirty(True)

    def getAnalysisResults(self, channel : int, detectionType : PeakDetectionTypes) -> KymRoiResults:
        return self._analysisResults[channel][detectionType.name]
    
    def getTrace(self, channel, name,
                #  stripNan=False
                #  ) -> KymRoiTraces:
                 ) -> np.ndarray:
        # return self.kymRoiTraces[channel][name]
        return self.kymRoiTraces[channel].getTrace(name)
        
    def setResults(self, channel, detectionType : PeakDetectionTypes, kymRoiResults : KymRoiResults) -> KymRoiResults:
        # logger.info(f'channel:{channel} detectionType:{detectionType}')
        self._analysisResults[channel][detectionType.name] = kymRoiResults
        self.setDirty(True)
        return kymRoiResults

    def setTrace2(self, channel, name, xBins, values : np.ndarray):
        """
        Parameters
        ==========
        xBins : arange
            The line scan bins to set
        """
        self.kymRoiTraces[channel].setTrace2(name, xBins, values)

    def setTrace(self, channel, name, values : np.ndarray):
        """Set a named trace in kym analysis.
        
        Parameters
        ==========
        name : str
            Something like df_f0, diameter (um), etc.

        Traces are a df of rows (line scans) and columns (trace names).
        """
        self.kymRoiTraces[channel][name] = values

    def __str__(self):
        ret = f'kymRoi label:{self._label} ltrb:{self._ltrbRect}'
        return ret
    
    def getLabel(self):
        return self._label
    
    @property
    def header(self):
        return self._header
    
    @property
    def path(self):
        """Get the path to the tif file.
        """
        return self._header['path']
    
    @property
    def umPerPixel(self):
        return self._header['umPerPixel']
    
    @property
    def secondsPerLine(self):
        return self._header['secondsPerLine']
    
    def getDefaultRect(self):
        # h, w = self._imgData.shape
        left = 0
        top = self.header['imageHeight']
        right = self.header['imageWidth']
        bottom = 0

        return [left, top, right, bottom]
    
    def getPosSize(self):
        """Get rect roi as (pos[], size[])
        
        Used in GUI.
        """
        ltrbRoi = self.getRect()
        pos = [ltrbRoi[0], ltrbRoi[3]]
        size = [ltrbRoi[2] - ltrbRoi[0], ltrbRoi[1] - ltrbRoi[3]]
        return pos, size
        
    def getRect_json(self) -> str:
        """Get the current roi as a json string
        """
        rectDict = self.getRectDict()
        return json.dumps(rectDict)
    
    def getRect(self) -> List[int]:
        """Get the current roi as [l, t, r, b]
        """
        return self._ltrbRect
    
    def getRectDict(self) -> dict:
        """Get the current roi as a dict
        """
        ltrb = self.getRect()
        return {
            'left': ltrb[0],
            'top': ltrb[1],
            'right': ltrb[2],
            'bottom': ltrb[3]
        }

    # abb 202505
    def setRoiHeightPixels(self, heightPixels : int):
        """Set the roi height in pixels.
        
        This is used to set the height of the roi in the GUI.
        """
        ltrb = self.getRect()
        ltrb[1] = ltrb[3] + heightPixels
        self.setRect(ltrb)

    # abb 202505
    def nudge(self, direction : str):
        """Nudge the roi rect by delta pixels.
        
        This is used to set the height of the roi in the GUI.
        """
        ltrb = self.getRect()
        if direction == 'left':
            delta = -1
            ltrb[0] = ltrb[0] + delta
            ltrb[2] = ltrb[2] + delta
        elif direction == 'right':
            delta = 1
            ltrb[0] = ltrb[0] + delta
            ltrb[2] = ltrb[2] + delta
        elif direction == 'up':
            delta = 1
            ltrb[1] = ltrb[1] + delta
            ltrb[3] = ltrb[3] + delta
        elif direction == 'down':
            delta = -1
            ltrb[1] = ltrb[1] + delta
            ltrb[3] = ltrb[3] + delta
        else:
            logger.error(f'unknown direction "{direction}"')
            return
        
        logger.info(f'   roi nudge "{direction}" delta:{delta} orig ltrb:{self.getRect()}')
        self.setRect(ltrb)
        logger.info(f'  -->> accepted rect is:{self.getRect()}')

    def setRect(self, ltrb : List):  #, doAnalysis : bool = False):
        """Set the roi rect [l, t, r, b]


        """
        ltrbActual = self._getConstrainedRoi(ltrb)
        self._ltrbRect = ltrbActual    
        self.setDirty(True)

    def setRectPosSize(self, pos, size):
        """Set ltrb rect using pos() and size()
        
        Parameters
        ----------
        pos : (left, bottom)
        size : (width, heigh)
        """
        
        left = pos[0]
        top = pos[1] + size[1]
        right = pos[0] + size[0]
        bottom = pos[1]

        left = int(left)
        top = int(top)
        right = int(right)
        bottom = int(bottom)
        
        newRect = [left, top, right, bottom]
        self.setRect(newRect)

        return newRect
    
    def _getConstrainedRoi(self, ltrb) -> List[int]:
        """Given a rect, return rect constrained to imgData.
        """

        left = ltrb[0]
        top = ltrb[1]
        right = ltrb[2]
        bottom = ltrb[3]

        heightMax = self.header['imageHeight']
        widthMax = self.header['imageWidth']

        if left<0:
            left = 0
        if top > heightMax:
            top = heightMax
        if right > widthMax:
            right = widthMax
        if bottom < 0:
            bottom = 0

        newRect = [left, top, right, bottom]
        
        return newRect
    
    def getRoiImg(self, channel) -> np.ndarray:
        """Get roi img data inside the roi rect.

        Return a copy so when modified does not modify the original (e.g. background subtract).
        """
        left, top, right, bottom = self.getRect()
        roiImg = self._imgData[channel][bottom:top, left:right]
        roiImg = np.copy(roiImg)
        return roiImg
    
    def backgroundSubtract(self, channel, roiImg, peakDetectionTypes : PeakDetectionTypes):
        
        detectionParameters = self.getDetectionParams(channel, peakDetectionTypes)
        
        backgroundsubtract = detectionParameters['Background Subtract']
        # logger.info(f'performing backgroundsubtract:"{backgroundsubtract}"')

        if backgroundsubtract == 'Off':
            pass
        
        elif backgroundsubtract == 'Rolling-Ball':
            _rollingBallRadius = detectionParameters['Rolling-Ball Radius']
            rollingBackground = restoration.rolling_ball(roiImg, radius=_rollingBallRadius)
            roiImg = roiImg - rollingBackground
        
        elif backgroundsubtract == 'Median':
            # problem with median is "after" we get negative value and
            # can not perform log transform !!!'
            _subtactValue = np.median(roiImg).astype(np.int64)
            # logger.info(f'   _subtactValue: {type(_subtactValue)} {_subtactValue}')
            roiImg = roiImg - _subtactValue
            roiImg[roiImg<0] = 0
            detectionParameters['backgroundSubtractValue'] = int(_subtactValue)

        elif backgroundsubtract == 'Mean':
            _subtactValue = np.mean(roiImg).astype(np.int64)
            roiImg = roiImg - _subtactValue
            roiImg[roiImg<0] = 0
            detectionParameters['backgroundSubtractValue'] = int(_subtactValue)
        
        else:
            logger.error(f'did not understand background subtract "{backgroundsubtract}" -->> no subtraction')

        # _printImgStat(roiImg, f'after background subtract: "{backgroundsubtract}"')        

        self.setDirty(True)

        return roiImg
    
    def getTimeBins(self):
        _left, _top, _right, _bottom = self.getRect()
        xPlot = np.arange(_left, _right, dtype=np.int32)
        return xPlot
    
    def getRoiImgClips(self, channel) -> Dict:
        """Get roi img data inside the roi rect.

        Return a copy so when modified does not modify the original (e.g. background subtract).
        
        Returns
        -------
        Dict with keys:
            - raw
            - bs
            - binned
            - divided
        """
        
        detectionParams = self.getDetectionParams(channel, PeakDetectionTypes.intensity)

        f0Value = detectionParams['f0 Value Percentile']

        roiImg_raw = self.getRoiImg(channel)
        
        roiImg_f_f0 = roiImg_raw / f0Value
        roiImg_df_f0 = (roiImg_raw - f0Value) / f0Value

        # "background" subtract
        roiImg_bs = self.backgroundSubtract(channel, roiImg_raw, PeakDetectionTypes.intensity)

        binLineScans = detectionParams['Bin Line Scans']
        if binLineScans == 0:
            pass
        else:
            roiImg_binned = BinLineScans(roiImg_bs, binLineScans)

        # divided
        # divideLinescan = detectionParams['Divide Line Scan']
        santanaLineScanNorm = self._kymRoiAnalysis.getKymDetectionParam('Divide Line Scan')
        # logger.info(f'  santanaLineScanNorm:{santanaLineScanNorm}')
        if santanaLineScanNorm is None:
            # logger.warning('no santana division')
            roiImg_divided = roiImg_raw.astype('float64')  # copy

        else:
            column_to_divide_by = roiImg_raw[:, santanaLineScanNorm]
            reshaped_column = column_to_divide_by.reshape(-1, 1)
            
            try:
                # Cannot cast ufunc 'divide' output from dtype('float64') to dtype('int16')
                roiImgFloat = roiImg_raw.astype('float64')  # copy
                reshaped_column_float = reshaped_column.astype('float64')
                ones_like = np.ones_like(roiImgFloat)
                roiImg_divided = np.divide(roiImgFloat, reshaped_column_float, out=ones_like, where=reshaped_column != 0)

                # this col should be all 1
                if not np.all(roiImg_divided[:,santanaLineScanNorm] == 1):
                    logger.error(f'santanaLineScanNorm:{santanaLineScanNorm} column should be all 1')
                    # print(dividedImg[:,santanaLineScanNorm])

            except (RuntimeWarning) as e:
                # RuntimeWarning: divide by zero encountered in divide
                logger.error(e)

        retDict = {
            'raw': roiImg_raw,
            'f_f0': roiImg_f_f0,
            'df_f0': roiImg_df_f0,
            #
            'bs': roiImg_bs,
            'binned': roiImg_binned,
            'divided': roiImg_divided
        }
        return retDict

    def getSumIntensity(self, channel):
        """Get sum intensity for each line scan.
        
        Algorithm
        ---------
            - Background subtract roi image
            - Bin line scans using mean for each pixel across a bin line scan width
            - Sum intensity of each line scan
            - Normalize each intensity line scan to number of pixels

        Returns
        -------
        Tuple of (xPlot, sumInt)

        xPlot : np.arange
            Line scan time seconds (after clipping to left/right of roi rect)
        sumInt : np.ndarray
            Sum of each line scan (after clipping to left/right and top/bottom of roiRect)

        """
        _debug = False

        detectionParams = self.getDetectionParams(channel, PeakDetectionTypes.intensity)
        roiImg = self.getRoiImg(channel)  # get imgData within ROI
        _left, _, _right, _ = self.getRect()
        
        xPlot = np.arange(_left, _right, dtype=np.float32) * self.secondsPerLine

        # "background" subtract
        roiImg = self.backgroundSubtract(channel, roiImg, PeakDetectionTypes.intensity)
        if _debug:
            _printImgStats(roiImg, 'after background subtract')

        binLineScans = detectionParams['Bin Line Scans']
        if binLineScans == 0:
            pass
        else:
            roiImg = BinLineScans(roiImg, binLineScans)
            if _debug:
                _printImgStats(roiImg, 'after bin line scans')

        # sum intensities in each line scan
        sumInt = np.sum(roiImg, axis=0)
        if _debug:
            _printImgStats(sumInt, 'after sum intensities')
        # normalize to number of points in line scan
        sumInt = sumInt / roiImg.shape[0]
        if _debug:
            _printImgStats(sumInt, 'after normalize')

        # divideLinescan = detectionParams['Divide Line Scan']
        santanaLineScanNorm = self._kymRoiAnalysis.getKymDetectionParam('Divide Line Scan')
        # set in roi, can be None
        detectionParams.setParam('Divide Line Scan', santanaLineScanNorm)
        
        logger.info(f'  santanaLineScanNorm:{santanaLineScanNorm}')
        if santanaLineScanNorm is None:
            # logger.error(f'no divide normalization (santana), e.g. "Divide Line Scan"')
            dividedInt = sumInt.copy()
            dividedInt[:] = np.nan

        else:
            # logger.warning(f'dividing by santanaLineScanNorm:{santanaLineScanNorm} roiImg:{roiImg.shape}')
            column_to_divide_by = roiImg[:, santanaLineScanNorm]
            reshaped_column = column_to_divide_by.reshape(-1, 1)
            
            try:
                # Cannot cast ufunc 'divide' output from dtype('float64') to dtype('int16')
                roiImgFloat = roiImg.astype('float64')
                reshaped_column_float = reshaped_column.astype('float64')
                ones_like = np.ones_like(roiImgFloat)
                
                # logger.warning(f'roiImg:{roiImg.dtype} reshaped_column:{reshaped_column.dtype} zeros_like:{zeros_like.dtype}')

                dividedImg = np.divide(roiImgFloat, reshaped_column_float, out=ones_like, where=reshaped_column != 0)

                # this col should be all 1
                if not np.all(dividedImg[:,santanaLineScanNorm] == 1):
                    logger.error(f'santanaLineScanNorm:{santanaLineScanNorm} column should be all 1')
                    # print(dividedImg[:,santanaLineScanNorm])

            except (RuntimeWarning) as e:
                # RuntimeWarning: divide by zero encountered in divide
                logger.error(e)

            # logger.warning(f'  dividedImg:{dividedImg.shape} {dividedImg.dtype}')
            
            # sum intensities in each line scan
            dividedInt = np.sum(dividedImg, axis=0)
            # normalize to number of points in line scan
            dividedInt = dividedInt / dividedImg.shape[0]
            
            # logger.warning(f'  dividedInt:{dividedInt.shape} {dividedInt.dtype}')

        #
        # filter - before detection
        if detectionParams['Median Filter']:
            # 1) medfilt
            medianfilterkernel = detectionParams['Median Filter Kernel']
            logger.info(f'   applying median filter with medianfilterkernel:{medianfilterkernel}')
            sumInt = medfilt(sumInt, kernel_size=medianfilterkernel)
            if _debug:
                _printImgStats(sumInt, 'after median filter')

        if detectionParams['Savitzky-Golay']:
            # 2) SavitzkyGolay_Filter
            logger.info('   applying Savitzky-Golay filter')
            sumInt = getSavitzkyGolay_Filter(sumInt)

        # logger.warning(f'xPlot:{xPlot.shape} sumInt:{sumInt.shape} dividedInt:{dividedInt.shape}')
        # logger.warning(f'xPlot:{xPlot.dtype} sumInt:{sumInt.dtype} dividedInt:{dividedInt.dtype}')

        # check if sumInt is all nan
        if np.isnan(sumInt).all():
            logger.error('sumInt is all nan -->> ABORTING')
            sys.exit(1)

        postMedianFilterKernel = detectionParams['Post Median Filter Kernel']
        if postMedianFilterKernel > 0:
            # if postMedianFilterKernel is even, make it odd
            if postMedianFilterKernel % 2 == 0:
                logger.warning(f'forcing odd postMedianFilterKernel:{postMedianFilterKernel}')
                postMedianFilterKernel += 1
            sumInt = medfilt(sumInt, kernel_size=postMedianFilterKernel)
            dividedInt = medfilt(dividedInt, kernel_size=postMedianFilterKernel)

        return xPlot, sumInt, dividedInt

    def _lineToSecond(self, lineNumber) -> float:
        """Convert a line scan to seconds.
        """
        _left, _top, _right, _bottom = self.getRect()
        _lineNumber = lineNumber - _left
        _seconds = _lineNumber * self.secondsPerLine
        return _seconds

    def _msToBin(self, msValue : float) -> int:
        """Convert ms to nearest bin using round.
        """
        _retBin1 = msValue / 1000 / self.secondsPerLine
        _retBin2 = int(round(_retBin1))
        return _retBin2
    
    def _umToBin(self, umValue : float) -> int:
        """Convert ms to nearest bin using round.
        """
        _retBin1 = umValue / self.umPerPixel
        _retBin2 = int(round(_retBin1))
        return _retBin2
    
    def getLineProfile(self, channel, lineIdx):
        """Get an intensity profile for one line.
        """
        roiImg = self.getRoiImg(channel)

        detectionParams = self.getDetectionParams(channel, PeakDetectionTypes.diameter)

        doBackgroundSubtract = detectionParams['do_background_subtract_diam']
        line_width_diam = detectionParams['line_width_diam']
        line_median_kernel_diam = detectionParams['line_median_kernel_diam']
        # stdThreshold = detectionParams['std_threshold_mult_diam']
        # lineScanFraction = detectionParams['line_scan_fraction_diam']  # fraction of line for lef/right, 4 is 25% and 2 is 50%
        line_interp_mult_diam = detectionParams['line_interp_mult_diam']  # interpolate each line scan by this multiplyer
        
        from sanpy.kym.kymRoiDiameter import getLineProfile
        lineProfile = getLineProfile(roiImg,
                       lineIdx=lineIdx,
                       doBackgroundSubtract=doBackgroundSubtract,
                       lineWidth=line_width_diam,
                       lineMedianKernel=line_median_kernel_diam,
                       lineInterptMult=line_interp_mult_diam
                       )
        
        xUm = np.arange(len(lineProfile)) * self.umPerPixel
        if line_interp_mult_diam > 1:
            xUm /= line_interp_mult_diam

        return xUm, lineProfile
    
    # TODO: extend this to 10/90 rise/decay
    def getHalfWidthPlot(self, channel, peakDetectionType : PeakDetectionTypes):
        """Get x/y to plot half-width for all peaks.
        """
        analysisResults = self.getAnalysisResults(channel, peakDetectionType)
        
        # _peakBins is just used to iterate through peaks
        _peakBins = analysisResults.getValues('Peak Bin')
        
        xHalfWidth = []
        yHalfWidth = []
        for _peakIdx, _peakBin in enumerate(_peakBins):
            hwLeftSecond = analysisResults.getValues('HW Left (s)')[_peakIdx]   
            hwRightSecond = analysisResults.getValues('HW Right (s)')[_peakIdx]   

            hwLeftInt = analysisResults.getValues('HW Left Int')[_peakIdx]   
            # using 'hw left int' for both, otherwise the half-width line is crooked
            hwRightInt = analysisResults.getValues('HW Left Int')[_peakIdx]   

            # logger.info(f'   hwLeftSecond:{hwLeftSecond} {type(hwLeftSecond)}')
            # hwLeftSecond = float(hwLeftSecond)
            
            # here we are expanding by one float (do not extend)
            xHalfWidth.append(hwLeftSecond)
            xHalfWidth.append(hwRightSecond)
            xHalfWidth.append(np.nan)

            yHalfWidth.append(hwLeftInt)
            yHalfWidth.append(hwRightInt)
            yHalfWidth.append(np.nan)

        return xHalfWidth, yHalfWidth

    def getExpDecayPlot(self, channel, peakDetectionType : PeakDetectionTypes):
        """Get x/y to plot exp decay for all peaks.
        
        Exp Decay depends on detection 'Polarity'
        """
        kymRoi = self
        
        detectionParams = self.getDetectionParams(channel, peakDetectionType)
        analysisResults = self.getAnalysisResults(channel, peakDetectionType)
        timeSec = self.getTrace(channel, 'Time (s)')

        # fix this constant bug !!!!
        # [_left, _, _, _] = kymRoi.getRect()
        _peakBins = analysisResults.getValues('Peak Bin')

        xDecay = []
        yDecay = []
        for _peakIdx, _peakBin in enumerate(_peakBins):
            
            # _peakBin = _peakBin - _left
            
            fit_m = analysisResults.getValues('fit_m')[_peakIdx]            
            fit_tau = analysisResults.getValues('fit_tau')[_peakIdx]
            fit_b = analysisResults.getValues('fit_b')[_peakIdx]

            if np.isnan(fit_m):
                # logger.warning(f'no fit for peak {_peakIdx}')
                continue

            # ms to bin
            _decayMs = detectionParams['Decay (ms)']
            _decayBin = _decayMs / 1000 / kymRoi._header['secondsPerLine']
            _decayBin = int(round(_decayBin))

            # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine
            decayFitBins = _decayBin
            _xRange = timeSec[_peakBin:_peakBin+decayFitBins] - timeSec[_peakBin]
            
            # get line showing our fit
            fit_y = myMonoExp(_xRange, fit_m, fit_tau, fit_b)

            # here we need to extend because we are adding more than one point
            xDecay.extend(_xRange+timeSec[_peakBin])
            xDecay.append(np.nan)

            yDecay.extend(fit_y)
            yDecay.append(np.nan)

        return xDecay, yDecay
    
    def getPeakClips(self, peakDetectionType : PeakDetectionTypes,
                 channel : int,
                 asPercent : bool = True,
                 plusMinusMs : float = 50) -> tuple[np.ndarray, np.ndarray]:

        xPeakBins = self.getAnalysisResults(channel, peakDetectionType).getValues('Peak Bin')
        numPeaks = len(xPeakBins)
        
        if numPeaks == 0:
            # logger.warning(f'peakDetectionType:{peakDetectionType} channel:{channel} -->> no detection found')
            return None, None
        
        detectThisTrace = self.getDetectionParams(channel, peakDetectionType).getParam('detectThisTrace')
        yPlot = self.getTrace(channel, detectThisTrace)

        plusMinusBins = self._msToBin(plusMinusMs)
        numPntsInClip = plusMinusBins * 2

        # all clips share same x
        xOneClip = [(x-plusMinusBins)*self.secondsPerLine for x in range(numPntsInClip)]

        xPlotClips = np.empty((numPeaks*2, numPntsInClip))
        xPlotClips[:] = np.nan
        yPlotClips = np.empty((numPeaks*2, numPntsInClip))
        yPlotClips[:] = np.nan

        for peakIdx, xPeak in enumerate(xPeakBins):
            # logger.info(f'peakIdx:{peakIdx}')
            
            xStart = xPeak - plusMinusBins
            if xStart < 0:
                xStart = 0
            xStop = xPeak + plusMinusBins
            if xStop > len(yPlot)-1:
                xStop = len(yPlot)-1
            
            # logger.info(f'xStart:{xStart} xStop:{xStop} plusMinusBins:{plusMinusBins}')
            yOneClip = yPlot[xStart:xStop]

            # normalize to max -> percent
            try:
                if asPercent:
                    yOneClip = yOneClip / np.max(yOneClip) * 100

            except (ValueError) as e:
                logger.warning(f'   (1) not calculating clip for peak: {peakIdx} --> {e}')
                logger.error(f'      peakIdx:{peakIdx} xStart:{xStart} yStart:{xStart}')
                continue

            xPlotClips[peakIdx*2, :] = xOneClip
            
            try:
                yPlotClips[peakIdx*2, :] = yOneClip
            except (ValueError) as e:
                logger.warning(f'   (2) not calculating clip for peak: {peakIdx} --> {e}')

        return xPlotClips, yPlotClips
    
    def detectDiam(self, channel, verbose : bool = False):
        """Detect diam from kym image.
        
        Uses detectKymRoiDiam()
        """
        self.setDirty(True)

        roiImg = self.getRoiImg(channel)  # clipped to ltrb of roi rect
        
        logger.info(f'==>> calling detectKymRoiDiam() with roi {self.getLabel()} {roiImg.shape}')
        
        from sanpy.kym.kymRoiDiameter import detectKymRoiDiam

        detectionParams = self.getDetectionParams(channel, PeakDetectionTypes.diameter)

        # print('detectionParams:')
        # print(detectionParams)

        doBackgroundSubtract = detectionParams['do_background_subtract_diam']
        lineWidth = detectionParams['line_width_diam']
        lineMedianKernel = detectionParams['line_median_kernel_diam']
        stdThreshold = detectionParams['std_threshold_mult_diam']
        lineScanFraction = detectionParams['line_scan_fraction_diam']  # fraction of line for lef/right, 4 is 25% and 2 is 50%
        lineInterptMult = detectionParams['line_interp_mult_diam']  # interpolate each line scan by this multiplyer
        
        # lineScanFraction = 2 # 2 # fraction of line scan to detect for onset/offset
            # if 2 then half/half
            # if 4 then first/last 25% (good for colin)

        # logger.info(f'   doBackgroundSubtract:{doBackgroundSubtract}')

        # need to shift bins to make roi _bottom
        leftThresholdBins, rightThresholdBins, diameterBins, sumIntensity = \
            detectKymRoiDiam(roiImg,  # roiImg is clipped to ltrb of roi rect
                        doBackgroundSubtract=doBackgroundSubtract,
                        lineWidth=lineWidth,
                        lineMedianKernel=lineMedianKernel,
                        lineScanFraction=lineScanFraction,
                        lineInterptMult=lineInterptMult,
                        stdThreshold=stdThreshold,
        )
    
        _left, _top, _right, _bottom = self.getRect()
        leftThresholdBins += _bottom
        rightThresholdBins += _bottom
        
        _timeBins = self.getTimeBins()

        # self.setTrace2(channel, 'leftThresholdBins', _timeBins, leftThresholdBins)
        # self.setTrace2(channel, 'rightThresholdBins', _timeBins, rightThresholdBins)
        # self.setTrace2(channel, 'diameterBins', _timeBins, diameterBins)

        self.setTrace2(channel, 'Left Diameter (um)', _timeBins, leftThresholdBins * self.umPerPixel)
        self.setTrace2(channel, 'Right Diameter (um)', _timeBins, rightThresholdBins * self.umPerPixel)
        self.setTrace2(channel, 'Diameter (um)', _timeBins, diameterBins * self.umPerPixel)

    def peakDetect(self, channel,
                   peakDetectionType : PeakDetectionTypes,
                   verbose : bool = False):
        """
        Parameters
        ==========
        channel : int
            Channel number to analyze (0 base)
        """
        # diameterTraces = ['Diameter (um)', 'Left Diameter (um)', 'Right Diameter (um)']
        
        # either intensity or diameter
        detectionParams = self.getDetectionParams(channel, detectionType=peakDetectionType)
        
        logger.info(f'-->> peakDetectionType:{peakDetectionType}')
        # print(detectionParams.printValues())

        # store the ltrb of rect we analysed
        roiRect = self.getRect()
        detectionParams['ltrb'] = roiRect
        _left = roiRect[0]
        _right = roiRect[2]

        detectThisTrace = detectionParams['detectThisTrace']  # from (df_f0, f_f0, Diameter (um))

        # if detectThisTrace in diameterTraces:
        if peakDetectionType == PeakDetectionTypes.diameter:
            _tmpTrace = self.getTrace(channel, detectThisTrace)
            if np.isnan(_tmpTrace).all():
                logger.error(f'trace "{detectThisTrace}" has no value, did you perform "detect diameter"?-->> no detection performed')
                return
        
        logger.info(f'<<=== KymRoi.peakDetect() ==>>')
        logger.info(f'  roi label:{self._label} with trace:"{detectThisTrace}"')
        if verbose:
            print(detectionParams.printValues())

        # parameters
        polarity = detectionParams['Polarity']
        prominence = detectionParams['Prominence']
        width = detectionParams['Width (ms)'] / 1000 / self.secondsPerLine
        distance = detectionParams['Distance (ms)'] / 1000 / self.secondsPerLine

        # abb 20250530
        # linescan to divide kym image for normalization (Santana)
        # 20250608, this is for kym, not individual roi
        # divideLinescan = detectionParams['Divide Line Scan']

        # abb 202505 colin, use 2x f0 value, one for auto, another for manual
        # if f0ManualPercentile=='Manual' then user need to directly set f0, we do not calulate it
        f0ManualPercentile = detectionParams['f0 Type']  # in (Manual, Percentile)
        f0Percentile = detectionParams['f0 Percentile']
        _do__manual_f0 = f0ManualPercentile == 'Manual'
        _do__percentile_f0 = f0ManualPercentile == 'Percentile'
        if _do__manual_f0 and detectionParams['f0 Value Manual'] is None:
            logger.error('ManualPercentile is set to "Manual" but "f0 Value Manual" is None --> user needs to set value')
            return
        if _do__manual_f0:
            f0 = detectionParams['f0 Value Manual']
        elif _do__percentile_f0:
            # wil get calculated after removing exp (below)
            f0 = detectionParams['f0 Value Percentile']

        self.setDirty(True)

        # if detectThisTrace in diameterTraces:
        if peakDetectionType == PeakDetectionTypes.diameter:
            xPlot, _, _ = self.getSumIntensity(channel)  # does background subtraction
        else:
            # xPlot are line scan seconds within roi rect
            # yPlot is corresponding sum intensity within roi rect
            xPlot, yRaw, dividedInt = self.getSumIntensity(channel)  # does background subtraction
        
            # check if yRaw is all nan
            if np.isnan(yRaw).all():
                logger.error('  yRaw is all nan -->> using yRaw')
                # sys.exit(1)
                # yRaw = dividedInt

            # subtract single exponential to account for intensity decay (bleaking)
            # yRaw can not have negative values (We are taking the log)
            doExpDetrend = detectionParams['Exponential Detrend']
            logger.info(f'   -->> Exponential Detrend:{doExpDetrend}')
            if doExpDetrend:
                # logger.info('performing Exponential Detrend')
                
                fitDict, yDetrend = myDetrend(xPlot, yRaw, doPlot=False)
                
                if fitDict is None:
                    logger.error('  error calling myDetrend -->> using yRaw')
                    yDetrend = yRaw

                else:
                    detectionParams['expDetrendFit'] = fitDict  # store the fit params

                    # shift back to all positive
                    yDetrend += abs(np.min(yDetrend))

            else:
                # logger.info('skipping Exponential Detrend')
                yDetrend = yRaw
                detectionParams['expDetrendFit'] = None  # when off -->> no fit

            if polarity == 'Neg':
                f0Percentile = 100 - f0Percentile

            if _do__percentile_f0:
                # f0 is a percentile of f_f0, 50 percentile is median
                f0 = np.percentile(yDetrend, f0Percentile)
                detectionParams['f0 Value Percentile'] = float(f0)  # store the f0 value
            logger.info(f'   -->> using f0 Type: "{f0ManualPercentile}" f0Percentile:{f0Percentile} f0 is :{f0}')

        # the time bins (line scans) within the roi rect
        _timeBins = self.getTimeBins()

        if peakDetectionType == PeakDetectionTypes.diameter:
            pass
        else:
            if f0 == 0:
                logger.error(f'f0 is {f0}, did not perform df/f0')
                f0 = 1

            # proper dF/F0
            yDf_f0 = (yDetrend - f0) / f0
            # santana likes f/f0
            f_f0 = yDetrend / f0

            #
            # store what we used for analysis
            self.setTrace2(channel, 'intRaw', _timeBins, yRaw)
            self.setTrace2(channel, 'intDetrend', _timeBins, yDetrend)
            self.setTrace2(channel, 'df/f0', _timeBins, yDf_f0)
            self.setTrace2(channel, 'f/f0', _timeBins, f_f0)
            self.setTrace2(channel, 'Divided', _timeBins, dividedInt)

        yDf_f0 = self.getTrace(channel, detectThisTrace)
        # clip to _left/_right
        # logger.info(f'   clipping _left:{_left} right:{_right } yDf_f0 "{detectThisTrace}" from {len(yDf_f0)}')
        yDf_f0 = yDf_f0[_left:_right]
        # logger.info(f'      to: {len(yDf_f0)}')

        _numNan = np.count_nonzero(np.isnan(yDf_f0))
        # logger.info(f'      num nan: {_numNan}')

        #
        # add everything to a NEW results object (results are one of PeakDetectionTypes)
        oneRoiResults = self.setResults(channel, peakDetectionType, KymRoiResults())

        #
        if polarity == 'Pos':
            detectThisY = yDf_f0
        elif polarity == 'Neg':
            detectThisY = -yDf_f0
        else:
            logger.error(f'   did not understand polarity:"{polarity}"')

        self.setDirty(True)

        #
        # find peaks (this includes half-width)
        #
        # will default to rel_height 0.5, 1 is foot, 0 is peak
        peakTuple = find_peaks(detectThisY,
                               prominence=prominence,
                               distance=distance,
                               width=width,
                               # rel_height = thresh_rel_height,
                               )
        peakBins = peakTuple[0]
        peakDict = peakTuple[1]

        logger.info(f'   -->> detected {len(peakBins)} peaks')

        if polarity == 'Neg':
            peakDict['width_heights'] = -peakDict['width_heights']

        numPeaks = len(peakBins)
        yPeaks = []
        if numPeaks == 0:
            return True
        
        # 20250521 if our folder/files were moved, this self.path is bad !!!
        # print(f'self.path:{self.path}')
        # sys.exit(1)

        # GOT SOME PEAKS
        # CRITICAL, do this first to seed proper number of rows
        oneRoiResults.setValues('Peak Number', range(1,numPeaks+1))  # +1 because range is [)
        oneRoiResults.setValues('Detected Trace', detectThisTrace)
        oneRoiResults.setValues('Channel Number', channel+1)
        oneRoiResults.setValues('ROI Number', self._label)
        oneRoiResults.setValues('Path', self.path)
        oneRoiResults.setValues('Accept', True)  # all peaks start as Accept=True
        oneRoiResults.setValues('Detection Errors', '')  # all peaks start as errors = ''

        # 20241104 was this
        # oneRoiResults.setValues('Peak Bin', peakBins)
        oneRoiResults.setValues('Peak Bin', peakBins + _left)

        _peakSeconds = (peakBins + _left) * self.secondsPerLine
        oneRoiResults.setValues('Peak (s)', _peakSeconds)

        yPeaks = yDf_f0[peakBins]  # yDf_f0 is NOT inverted on 'Neg' polarity (always raw trace to analyze)
        oneRoiResults.setValues('Peak Int', yPeaks)

        # shift everything by the left pixel of our ROI
        # peakBins = peakBins + _left
        # peakDict['left_ips'] = peakDict['left_ips'] + _left
        # peakDict['right_ips'] = peakDict['right_ips'] + _left

        #
        # get the onset and offset of the peak
        #
        thresh_rel_height = detectionParams['thresh_rel_height']  # using default of 0.85, 1 is foot, 0 is peak
        # logger.info(f'finding initial onset/offset thresholds using thresh_rel_height:{thresh_rel_height}')
        peak_10_tuple = peak_widths(detectThisY, peakBins, rel_height=thresh_rel_height)
        # peak10_widths = peak_10_tuple[0]
        # peak10_width_heights = peak_10_tuple[1]
        peak10_left_ips = peak_10_tuple[2]
        peak10_right_ips = peak_10_tuple[3]
        
        # shift everything by the left pixel of our ROI
        # peak10_left_ips = peak10_left_ips + _left
        # peak10_right_ips = peak10_right_ips + _left
        
        # IMPORTANT: DO THIS AFTER ALL DETECTION IS DONE
        # peakBins = peakBins + _left
                    
        thresholdBin = np.round(peak10_left_ips)
        thresholdBin = thresholdBin.astype(np.int64)  # use this as list index
        peakHeight = np.subtract(yPeaks, yDf_f0[thresholdBin])
        oneRoiResults.setValues('Peak Height', peakHeight)

        # inter-peak-interval (seconds)
        _peakInterval = np.diff(_peakSeconds)
        _peakInterval = np.insert(_peakInterval, 0, np.nan)  # insert np.nan as first (0) element
        oneRoiResults.setValues('Peak Inst Interval (s)', _peakInterval)
        oneRoiResults.setValues('Peak Inst Freq (Hz)', 1 / _peakInterval)

        hwLeftSecond = (peakDict['left_ips'] + _left) * self.secondsPerLine
        hwRightSecond = (peakDict['right_ips'] + _left) * self.secondsPerLine

        oneRoiResults.setValues('HW Left (s)', hwLeftSecond)
        oneRoiResults.setValues('HW Right (s)', hwRightSecond)

        hwLeftBin = np.round(peakDict['left_ips'])
        hwLeftBin = hwLeftBin.astype(np.int64)  # use this as list index
        hwRightBin = np.round(peakDict['right_ips'])
        hwRightBin = hwRightBin.astype(np.int64)  # use this as list index

        hwLeftIntensity = yDf_f0[hwLeftBin]
        # half-width left/right intensity use the left ???
        hwRigthIntensity = yDf_f0[hwRightBin]
        # hwRigthIntensity = yDf_f0[hwLeftBin]
        oneRoiResults.setValues('HW Left Int', hwLeftIntensity)
        oneRoiResults.setValues('HW Right Int', hwRigthIntensity)
                             
        oneRoiResults.setValues('HW Height', peakDict['width_heights'])

        hwSeconds = ((peakDict['right_ips'] + _left) * self.secondsPerLine) - ((peakDict['left_ips'] + _left) * self.secondsPerLine)
        hwMs = hwSeconds * 1000
        oneRoiResults.setValues('HW (ms)', hwMs)

        ##
        # CRITICAL: refine peak params using my findThreshold()
        # this requires the following to be filled in: (Peak Bin, Peak, Peak Height)
        ##
        newOnsetOffsetFraction = detectionParams['newOnsetOffsetFraction']
        # logger.info(f'calling findThreshold() with newOnsetOffsetFraction:{newOnsetOffsetFraction} polarity:{polarity}')
        if polarity == 'Neg':
            doMpl = False
        else:
            doMpl = False
        
        newOnsetBins, newDecayBins, newOnset10Bins, newDecay10Bins, _errorList = \
            findThreshold(detectThisY,
                          polarity,
                          oneRoiResults,
                          _leftRoiRect=_left,
                          newOnsetOffsetFraction=newOnsetOffsetFraction,
                          doMpl=doMpl)

        newOnsetSeconds = [(_bin+_left)*self.secondsPerLine for _bin in newOnsetBins]
        newDecaySeconds = [(_bin+_left)*self.secondsPerLine for _bin in newDecayBins]

        newOnset10Seconds = [(_bin+_left)*self.secondsPerLine for _bin in newOnset10Bins]
        newDecay10Seconds = [(_bin+_left)*self.secondsPerLine for _bin in newDecay10Bins]

        # 20241104
        # for numpy
        # newOnsetBins += _left
        # newDecayBins += _left
        # newOnset10Bins += _left
        # newDecay10Bins += _left
        # as lists
        # newOnsetBins = [x+_left for x in newOnsetBins]
        # newDecayBins = [x+_left for x in newDecayBins]
        # newOnset10Bins = [x+_left for x in newOnset10Bins]
        # newDecay10Bins = [x+_left for x in newDecay10Bins]

        # fill in with new/refined results
        # oneRoiResults.setValues('Onset Bin', newOnsetBins)  
        oneRoiResults.setValues('Onset (s)', newOnsetSeconds)
        # IMPORTANT: newOnsetBins can have nan values
        _tmp_yDf_f0 = [yDf_f0[_newOnsetBin] if ~np.isnan(_newOnsetBin) else np.nan for _newOnsetBin in newOnsetBins]
        # oneRoiResults.setValues('Onset Int', yDf_f0[newOnsetBins])  # yPlot is already reduced to roi (left)
        oneRoiResults.setValues('Onset Int', _tmp_yDf_f0)  # yPlot is already reduced to roi (left)
        # peak height is wrt onset (not decay)
        peakHeight = np.subtract(oneRoiResults.getValues('Peak Int'), oneRoiResults.getValues('Onset Int'))
        oneRoiResults.setValues('Peak Height', peakHeight)

        # oneRoiResults.setValues('Onset 10 Bin', newOnset10Bins)  
        oneRoiResults.setValues('Onset 10 (s)', newOnset10Seconds)
        # IMPORTANT: newOnset10Bins can have nan values
        _tmp_yDf_f0 = [yDf_f0[_newOnset10Bin] if ~np.isnan(_newOnset10Bin) else np.nan for _newOnset10Bin in newOnset10Bins]
        # oneRoiResults.setValues('Onset 10 Int', yDf_f0[newOnset10Bins])  # yPlot is already reduced to roi (left)
        oneRoiResults.setValues('Onset 10 Int', _tmp_yDf_f0)  # yPlot is already reduced to roi (left)

        # oneRoiResults.setValues('Decay Bin', newDecayBins)  
        oneRoiResults.setValues('Decay (s)', newDecaySeconds)
        # IMPORTANT: newDecayBins can have nan values
        _tmp_yDf_f0 = [yDf_f0[_newDecayBin] if ~np.isnan(_newDecayBin) else np.nan for _newDecayBin in newDecayBins]
        # oneRoiResults.setValues('Decay Int', yDf_f0[newDecayBins]) # yPlot is already reduced to roi (left)
        oneRoiResults.setValues('Decay Int', _tmp_yDf_f0) # yPlot is already reduced to roi (left)

        # oneRoiResults.setValues('Decay 10 Bin', newDecay10Bins)  
        oneRoiResults.setValues('Decay 10 (s)', newDecay10Seconds)
        # IMPORTANT: newDecay10Bins can have nan values
        _tmp_yDf_f0 = [yDf_f0[_newDecay10Bin] if ~np.isnan(_newDecay10Bin) else np.nan for _newDecay10Bin in newDecay10Bins]
        # oneRoiResults.setValues('Decay 10 Int', yDf_f0[newDecay10Bins]) # yPlot is already reduced to roi (left)
        oneRoiResults.setValues('Decay 10 Int', _tmp_yDf_f0) # yPlot is already reduced to roi (left)

        # logger.info(f'adding _errorList: {len(_errorList)} {_errorList}')
        # print(oneRoiResults.df)
        for _peakIdx, _err in enumerate(_errorList):
            oneRoiResults.addError(_peakIdx, _err)  # +1 because we start at 1
        ##
        # done refining with findThreshold()
        ##

        # 90% or rise and decay works with peak detect
        rel_height = 0.1  # 1 is base, 0 is peak
        peak_90_tuple = peak_widths(detectThisY, peakBins, rel_height=rel_height)
        # peak90_widths = peak_90_tuple[0]
        # peak90_width_heights = peak_90_tuple[1]
        peak90_left_ips = peak_90_tuple[2]
        peak90_right_ips = peak_90_tuple[3]

        # shift everything by the left pixel of our ROI
        # peak90_left_ips = peak90_left_ips + _left
        # peak90_right_ips = peak90_right_ips + _left

        peak90Bin = np.round(peak90_left_ips)
        peak90Bin = peak90Bin.astype(np.int64)  # use this as list index
        # oneRoiResults.setValues('Peak 90 Bin Fraction', peak90_left_ips)  # threshold in fractional bins
        # oneRoiResults.setValues('Onset 90 Bin', peak90Bin)  # potentially sloppy
        oneRoiResults.setValues('Onset 90 (s)', (peak90Bin + _left)  * self.secondsPerLine)
        oneRoiResults.setValues('Onset 90 Int', yDf_f0[peak90Bin])  # yPlot is already reduced to roi (left)

        # 90 of decay, this is from peak_detect and is good
        decay90Bin = np.round(peak90_right_ips)
        decay90Bin = decay90Bin.astype(np.int64)  # use this as list index
        # oneRoiResults.setValues('Decay 90 Bin Fraction', peak90_right_ips)  # threshold in fractional bins
        # oneRoiResults.setValues('Decay 90 Bin', decay90Bin)  # potentially sloppy
        oneRoiResults.setValues('Decay 90 (s)', (decay90Bin + _left) * self.secondsPerLine)
        oneRoiResults.setValues('Decay 90 Int', yDf_f0[decay90Bin]) # yPlot is already reduced to roi (left)

        #
        # colin symposium, full width from onset to offset (using peak "10" detection)
        fwSeconds = ((peak10_right_ips + _left) * self.secondsPerLine) - ((peak10_left_ips + _left) * self.secondsPerLine)
        fwMs = fwSeconds * 1000
        oneRoiResults.setValues('FW (ms)', fwMs)

        # colin, full with from rise 10 to decay 10
        fw10Seconds = (oneRoiResults.getValues('Decay 10 (s)') - oneRoiResults.getValues('Onset 10 (s)'))
        fw10Ms = fw10Seconds * 1000
        oneRoiResults.setValues('FW 10 (ms)', fw10Ms)

        # Rise Decay 10 width (ms)

        # rise and decay time (from onset to peak and peak to decay)
        riseTimeSeconds = oneRoiResults.getValues('Peak (s)') - oneRoiResults.getValues('Onset (s)')  # element wise subtract
        riseTimeMs = riseTimeSeconds * 1000
        oneRoiResults.setValues('Rise Time (ms)', riseTimeMs)

        decayTimeSeconds = oneRoiResults.getValues('Decay (s)') - oneRoiResults.getValues('Peak (s)')  # element wide subtraction
        decayTimeMs = decayTimeSeconds * 1000
        oneRoiResults.setValues('Decay Time (ms)', decayTimeMs)

        riseTen90Seconds = oneRoiResults.getValues('Onset 90 (s)') - oneRoiResults.getValues('Onset 10 (s)')  # element wise subtract
        rise1090Ms = riseTen90Seconds * 1000
        oneRoiResults.setValues('10-90 Rise Time (ms)', rise1090Ms)

        decay1090Seconds = oneRoiResults.getValues('Decay 10 (s)') - oneRoiResults.getValues('Decay 90 (s)')  # element wise subtract
        decay1090Ms = decay1090Seconds * 1000
        oneRoiResults.setValues('10-90 Decay Time (ms)', decay1090Ms)

        #
        # (1) exp fit of each peak
        # [_left, _, _, _] = self.roiList._roiAsRect(roi)
        # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine  # TODO: convert to sec or ms
        decayFitBins = self._msToBin(detectionParams['Decay (ms)'])
        # fit_m, fit_tau, fit_b, fit_r2, fit_error = _expFit(xPlot, yDf_f0, peakBins - _left, decayFitBins=decayFitBins)
        fit_m, fit_tau, fit_b, fit_r2, fit_error = _expFit(xPlot, yDf_f0, peakBins, decayFitBins=decayFitBins)
        oneRoiResults.setValues('fit_m', fit_m)
        oneRoiResults.setValues('fit_tau', fit_tau)
        oneRoiResults.setValues('fit_b', fit_b)
        oneRoiResults.setValues('fit_r2', fit_r2)
        # logger.info(f'fit_error is:{fit_error}')
        for _peakErrorIdx, oneError in enumerate(fit_error):
            if oneError != '':
                # logger.warning(f'_expFit oneError:{oneError}')
                oneRoiResults.addError(_peakErrorIdx, oneError)

        #
        # (2) double exp fit of each peak
        # [_left, _, _, _] = self.roiList._roiAsRect(roi)
        # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine  # TODO: convert to sec or ms
        decayFitBins = self._msToBin(detectionParams['Decay (ms)'])
        # fit_m1, fit_tau1, fit_m2, fit_tau2, fit_r22, fit_error = _expFit2(xPlot, yDf_f0, peakBins - _left, decayFitBins=decayFitBins)
        fit_m1, fit_tau1, fit_m2, fit_tau2, fit_r22, fit_error = _expFit2(xPlot, yDf_f0, peakBins, decayFitBins=decayFitBins)
        oneRoiResults.setValues('fit_m1', fit_m1)
        oneRoiResults.setValues('fit_tau1', fit_tau1)
        oneRoiResults.setValues('fit_m2', fit_m2)
        oneRoiResults.setValues('fit_tau2', fit_tau2)
        oneRoiResults.setValues('fit_r22', fit_r22)
        # logger.info(f'fit_error is:{fit_error}')
        for _peakErrorIdx, oneError in enumerate(fit_error):
            if oneError != '':
                # logger.warning(f'_expFit2 oneError:{oneError}')
                oneRoiResults.addError(_peakErrorIdx, oneError)

        # 202505 colin, calculate sum intensity in the peak
        # there are a few ways to do this !!!
        _sumPeakList = []
        # logger.error(f'TODO 202505 getAreaUnderPeak')
        for _idx, newOnsetBin in enumerate(newOnsetBins):
            newDecayBin = newDecayBins[_idx]
            _sumPeak = getAreaUnderPeak(detectThisY, newOnsetBin, newDecayBin)
            _sumPeakList.append(_sumPeak)
        oneRoiResults.setValues('Area Under Peak', _sumPeakList)

        #
        return True

# abb 202505 colin
def getAreaUnderPeak(yPlot, onsetBin, offsetBin, baseline:float = None) -> float:
    """
    Get the sum/area under the peak.

    This is normalized sum of intensity from oneset to offset (inclusive).

    TODO: we want to have an alternate "Santana" version where user specifies a baseline.

    TODO: This is currently in pixels, maybe convert to physical units of "per second"?
      Rather than "per pixel"
    """
    if onsetBin is None or onsetBin is None:
        logger.error(f'onsetBin:{onsetBin} offsetBin:{offsetBin}')
        return np.nan

    if baseline is not None:
        onsetBaseline = baseline
    else:
        onsetBaseline = yPlot[onsetBin]  # this will be 0

    try:
        peakCLip = yPlot[onsetBin:offsetBin+1] - onsetBaseline
        peakCLipSum = np.sum(peakCLip)  # the area under the peak
    except (TypeError) as e:
        logger.error(e)
        logger.error(f'colin 20250521 onsetBin:{onsetBin} offsetBin:{offsetBin} onsetBaseline:{onsetBaseline}')
        return np.nan
    
    return peakCLipSum

class KymRoiAnalysis:
    def __init__(self, path : str = None,
                 imgData : List[np.ndarray] = None,
                 kymRoiWidget = None,
                 loadAnalysis : bool = False):
        """
        Holds a number of kymRoi for one image file (multiple channels).
        
        Parameters
        ----------
        path : str
            Full path to .tif file
        imgData : List[np.ndarray]
            A list of equal sized 2d arrays, one item per image channel.
        kymRoiWidget : sanpy.kym.interface.KymRoiWidget
            During GUI runtime to update the statusbar
        """
        self._path = path
        self._kymRoiWidget = kymRoiWidget  # used to just call mySetStatusbar(str)
        self._loadError = False

        self._roiDict = {}
        """Keys are labels, values are KymRoi"""

        # 202505 colin
        # now our kym itself (not roi) has detection params
        self._kymDetectionParams = {
            'Divide Line Scan': None,
        }

        # ingest or load image data
        # self._imgData : List[np.ndarray] = []
        if imgData is not None:
            if not isinstance(imgData, List):
                imgData = [imgData]
            if len(imgData) == 0:
                logger.error(f'did not get image data for path:{path}')
                self._loadError = True
                return
            
            self._imgData : List[np.ndarray] = imgData
            """List of single channel images."""
            
            # logger.info(f'from imgData channels:{len(self._imgData)} shape:{self._imgData[0].shape}')

        # elif path is not None:
        #     self._imgData = tifffile.imread(path)
        #     # self._imgData = self._imgData.astype(np.int64)  # to all pos and negative
        #     if self._imgData.dtype == np.uint8:
        #         logger.warning(f'converting self._imgData from: {self._imgData.dtype} to np.int8')
        #         self._imgData = self._imgData.astype(np.int8)  # to all pos and negative
        #     elif self._imgData.dtype == np.uint16:
        #         logger.warning(f'converting self._imgData from: {self._imgData.dtype} to np.int16')
        #         self._imgData = self._imgData.astype(np.int16)  # to all pos and negative

        #     if olympusHeader is not None:
        #         self._imgData = np.rot90(self._imgData)
        #         # self._imgData = np.flip(self._imgData)

        #     logger.info(f'from path:{self._imgData.shape}')
        # else:
        #     logger.error('please specify either a path or imgData')

        self._fakeScale = False
        
        self._kymRoiMetaData = KymRoiMetaData(path, self._imgData)

        # 1) try and load from saved files
        loadedHeaderDict = self.loadAnalysis()

        if loadedHeaderDict is not None:
            self._kymRoiMetaData['Acq Date'] = loadedHeaderDict['Acq Date']
            self._kymRoiMetaData['Acq Time'] = loadedHeaderDict['Acq Time']
            self._kymRoiMetaData['secondsPerLine'] = loadedHeaderDict['secondsPerLine']
            self._kymRoiMetaData['umPerPixel'] = loadedHeaderDict['umPerPixel']

        else:
            # find corresponding Olympus txt file with params
            olympusHeader = _loadLineScanHeader(path)
            if olympusHeader is not None:
                self._kymRoiMetaData['Acq Date'] = olympusHeader['date']
                self._kymRoiMetaData['Acq Time'] = olympusHeader['time']
                self._kymRoiMetaData['secondsPerLine'] = olympusHeader['secondsPerLine']
                self._kymRoiMetaData['umPerPixel'] = olympusHeader['umPerPixel']
            else:
                self._fakeScale = True
                _secondsPerLine = 0.002
                _umPerPixel = 0.15
                self._kymRoiMetaData['secondsPerLine'] = _secondsPerLine
                self._kymRoiMetaData['umPerPixel'] = _umPerPixel
                logger.error(f'USING FAKE IMAGE SCALE !! secondsPerLine:{_secondsPerLine} umPerPixel:{_umPerPixel}')

        _xAxisBins = np.arange(0, self.numLineScans)
        self._xAxisSeconds = np.array(_xAxisBins, dtype=np.float32)
        self._xAxisSeconds *= self.secondsPerLine
        """Static X-Axis (s).
        """

        self.setDirty(False)

    def setKymDetectionParam(self, key, value):
        if key not in self._kymDetectionParams.keys():
            logger.error(f'key:{key} not in self._kymDetectionParams.keys()')
            return
        self._kymDetectionParams[key] = value

    def getKymDetectionParam(self, key):
        if key not in self._kymDetectionParams.keys():
            logger.error(f'key:{key} not in self._kymDetectionParams.keys()')
            return
        return self._kymDetectionParams[key]

    def getChannelColor(self, channel : int):
        colorConfig = {
            0 : 'Red',
            1 : 'Green'
        }
        if self.numChannels == 1:
            # 1 channel will always be green
            return colorConfig[1]
        else:
            return colorConfig[channel]

    def peakDetectAllRoi(self, channel):
        logger.info('=== detecting peaks for all roi')
        for roiLabel, kymRoi in self._roiDict.items():
            logger.info(f'   -->> roiLabel:{roiLabel}')
            kymRoi.peakDetect(channel, peakDetectionType=PeakDetectionTypes.intensity)

    def setDirty(self, value):
        # logger.info(f'value:{value}')
        self._isDirty = value

    @property
    def path(self):
        return self._path
    
    def getImageChannel(self, channel):
        if channel > len(self._imgData) - 1:
            logger.error(f'bad image channel {channel}, max channel number is {len(self._imgData)-1}')
            return
        return self._imgData[channel]
        
    @property
    def header(self):
        # return self._headerDict
        return self._kymRoiMetaData

    @property
    def umPerPixel(self) -> float:
        return self.header['umPerPixel']
    
    @property
    def numChannels(self) -> int:
        return self.header['numChannels']

    @property
    def secondsPerLine(self) -> float:
        return self.header['secondsPerLine']
    
    @property
    def numLineScans(self) -> float:
        return self.header['imageWidth']
    
    @property
    def numRoi(self) -> int:
        """Get the number of rois.
        """
        return len(self._roiDict.keys())

    def getRoiLabels(self) -> List[str]:
        return list(self._roiDict.keys())

    # abb 202505 colin
    def getCopyToClipboard(self) -> dict:
        """Get a json serializable dict of all roi
        """
        roiLabels = self.getRoiLabels()
        ret = {}
        for label in roiLabels:
            roi = self.getRoi(label)
            oneRoiDict = roi.getRectDict()
            ret[label] = oneRoiDict
        return ret
    
    def _getNextRoiLabel(self) -> str:
        """Get the next available roi label.
        """
        if self.numRoi == 0:
            return '1'
        else:
            nextLabel = list(self._roiDict.keys())[self.numRoi - 1]
            nextLabel = int(nextLabel)
            nextLabel += 1
            return str(nextLabel)
        
    def addROI(self,
               ltrbRect : List[int] = None,
               reuseRoiLabel : str = None,
               mode : str = None
               ) -> KymRoi:
        """Add a new roi.

        Parameters
        ----------
        ltrb : [l, t, r, b]
        reuseRoiLabel : 
            Reuse detection params of existing roi.
        """
        
        roiLabel = self._getNextRoiLabel()
        
        # logger.info(f'adding new roi label {roiLabel}')
        
        newRoi = KymRoi(roiLabel,
                        self._imgData,
                        header=self.header,
                        ltrbRect=ltrbRect,
                        reuseRoiLabel=reuseRoiLabel,
                        kymRoiAnalysis=self,  # so roi can use reuseRoiLabel
                        )
        self._roiDict[roiLabel] = newRoi
        self.setDirty(True)
        return newRoi
    
    def deleteRoi(self, roiLabel : str) -> bool:
        # roi will be none if it is not a key
        # logger.info(f'pop roiLabel:{roiLabel} from self._roiDict keys:{self._roiDict.keys()}')
        roi = self._roiDict.pop(roiLabel, None)
        self.setDirty(True)
        return roi
    
    def getRoi(self, roiLabel : str) -> KymRoi:
        """Get a KymRoi from a label str.
        """
        if not isinstance(roiLabel, str):
            roiLabel = str(roiLabel)
        if roiLabel not in self._roiDict.keys():
            logger.error(f'roiLabel "{roiLabel}" does not exist, available roi keys are {list(self._roiDict.keys())}')
            return
        return self._roiDict[roiLabel]

    def getXAxis(self):
        return self._xAxisSeconds
    
    def _msToBin(self, msValue : float) -> int:
        """Convert ms to nearest bin using round.
        """
        _retBin1 = msValue / 1000 / self.secondsPerLine
        _retBin2 = int(round(_retBin1))
        # logger.info(f'msValue:{msValue} _retBin1:{_retBin1} _retBin2:{_retBin2}')
        return _retBin2
    
    # TODO: refactor, only used by _getSaveFile
    def _getSaveFolder(self, enclosingFolder=False, createFolder=True):
        _folder, _ = os.path.split(self.path)  # folder the raw tif is in
        
        if not enclosingFolder:
            # folder we save csv into
            _folder = os.path.join(_folder, 'sanpy-kym-roi-analysis')
        if createFolder and not os.path.isdir(_folder):
            os.mkdir(_folder)
        
        return _folder

    def _getSaveFile(self, channel, createFolder=True):
        """Get full path to file to save/load analysis.
        
        Returns
        -------
        peaks
        diameter
        traces
        """
        saveFolder = self._getSaveFolder(createFolder=createFolder)

        _, _file = os.path.split(self.path)  # folder the raw tif is in
        
        _saveFile = os.path.splitext(_file)[0]

        saveFilePeaks = _saveFile + f'-ch{channel}-roiPeaks.csv'  # peaks
        saveFilePeaks = os.path.join(saveFolder, saveFilePeaks)

        saveFileDiameter = _saveFile + f'-ch{channel}-roiDiameter.csv'  # diameter
        saveFileDiameter = os.path.join(saveFolder, saveFileDiameter)

        saveFileInt = _saveFile + f'-ch{channel}-roiTraces.csv'  # intensity
        saveFileIntPath = os.path.join(saveFolder, saveFileInt)

        return saveFilePeaks, saveFileDiameter, saveFileIntPath

    def getDataFrame(self,
                     channel,
                     peakDetectionType : PeakDetectionTypes,
                     roiLabel = None):
        """Get results df for one roi or all roi (use roi=None).
        
        Only results for one typ of PeakDetectionTypes
        """
        if roiLabel is not None:
            return self.getRoi(roiLabel).getAnalysisResults(channel, peakDetectionType)
        else:
            columns = list(KymRoiResults.analysisDict.keys())
            df = pd.DataFrame(columns=columns)  # empty df with proper columns
            for _roiIdx, roi in enumerate(self._roiDict.values()):
                # logger.info(f'oneDf:{oneDf}')
                oneDf = roi.getAnalysisResults(channel, peakDetectionType).df
                if _roiIdx == 0:
                    df = oneDf
                else:
                    df = pd.concat([df, oneDf], axis=0)
            try:
                df = df.reset_index(drop=True)
            except (ValueError) as e:
                logger.error(e)

            return df
    
    def getCombindedDataFrame(self, channel):
        """Get combined DataFrame of analysis including both f_f0 and diameter.
        """
        dfSum = self.getDataFrame(channel, PeakDetectionTypes.intensity)
        dfSum['Analysis Type'] = 'f/f0'
        
        dfDiameter = self.getDataFrame(channel, PeakDetectionTypes.diameter)
        dfDiameter['Analysis Type'] = 'Diameter (um)'

        df = pd.concat([dfSum, dfDiameter], axis=0)
        df = df.reset_index(drop=True)
        return df
    
    def isDirty(self):
        """isDirty is true if we are dirty or any of the rois are dirty.
        """
        if self._isDirty:
            logger.info('kymRoiAnalysis is dirty')
            return True
        for roiLabel, kymRoi in self._roiDict.items():
            if kymRoi._isDirty:
                logger.info(f'roiLabel: {roiLabel} is dirty')
                return True
        return False
    
    def mySetStatusBar(self, statusStr : str):
        """Set the status bar of a parent kymRoiWidget.
        
        Only exists during PyQt runtime (not in scripts).
        """
        if self._kymRoiWidget is not None:
            self._kymRoiWidget.mySetStatusbar(statusStr)

    def saveAnalysisTraces(self, channel):
        """Save all roi traces for a channel in one csv file.
        """
        _, _, tracePath = self._getSaveFile(channel)

        df = pd.DataFrame()

        for roiLabel, kymRoi in self._roiDict.items():

            kymRoi:KymRoi = kymRoi
            
            kymRoiTraces = kymRoi.kymRoiTraces[channel]
            # if kymRoiTraces.isEmpty():
            #     continue
            for traceKey, traceValues in kymRoiTraces.items():
                # don't save if all nan
                if np.all(np.isnan(traceValues)):
                    # logger.warning(f'  not saving trace:{traceKey} -->> all nan')
                    continue
                
                colName = f'ROI {roiLabel} {traceKey}'
                # df[colName] = [np.nan] * numLineScans
                # logger.info(f'   roiLabel:{roiLabel} traceKey:{traceKey} colName:{colName} len:{len(traceValues)}')
                df[colName] = traceValues  # might be nan

        # logger.warning('todo: save a one line header with um/pixel and seconds/line')
        _fileHeaderJson = self._kymRoiMetaData.toJson()
        
        # logger.warning('saving traces even if 0 peaks')
        # if len(df) == 0:
        #     # nothing to save
        #     pass
        # else:
        if 1:
            logger.info(f'saving intensity traces to: {tracePath}')
            # df.to_csv(intPath, index=False)
            with open(tracePath, 'w') as f:
                f.write(_fileHeaderJson)
                f.write('\n')
                f.write(df.to_csv(header=True, index=False, mode='a'))

    def saveImageClips(self):
        """Save image clips for each roi.

        Each ROI will have 4x files (* color channel)
            - raw
            - background subtracted
            - binned
            - divided
        """
        # cell id from tif file
        _folder, _name = os.path.split(self.path)
        cellID = os.path.splitext(_name)[0]

        # WARNING: we need to ignore folder 'roi-img-clips' when building tif list !!!
        tifFolder = os.path.join(self._getSaveFolder(), 'kym-roi-img-clips')
        # logger.info(f'saving to tifFolder:{tifFolder}')

        for channel in range(self.numChannels):
            for roiLabel, kymRoi in self._roiDict.items():
                kymRoi:KymRoi = kymRoi
                # roiImg_raw, roiImg_bs, roiImg_binned, roiImg_divided = \
                
                # get a number of image clips (raw, f/f0 df/f0, divided)
                roiImgClipsDict = kymRoi.getRoiImgClips(channel)
                
                for clipKey, clipImgData in roiImgClipsDict.items():
                    if not os.path.isdir(tifFolder):
                        os.makedirs(tifFolder)
                    tifFileName = f'{cellID}-ch{channel}-roi{roiLabel}-{clipKey}.tif'
                    savePath = os.path.join(tifFolder, tifFileName)
                    # logger.info(f'  roiLabel:{roiLabel} clipKey:{clipKey}')
                    # logger.info(f'    tifFileName:{tifFileName}')
                    # logger.info(f'  savePath:{savePath}')
                    tifffile.imwrite(savePath, clipImgData)


    def saveAnalysis(self):
        """Save all analysis into a number of csv files.

        This includes a header with roi [l,t,r,b] and detection parameters used.

        Each ROI will have 3x files (* color channel)
            - intensity peaks
            - diameter peaks
            - traces (raw data that was analyzed, for both f/f0 peaks and diameter peaks)
        """

        logger.info('')
        if not self.isDirty:
            _noSaveStr = 'No changes to save.'
            logger.info(_noSaveStr)
            self.mySetStatusBar(_noSaveStr)
            return False
        
        self.saveImageClips()

        for channel in range(self.numChannels):
            
            # each channel goes to its own file
            _fileHeaderDict = {}
            _fileHeaderDictDiameter = {}

            # 202505 colin
            logger.info(f'saving key "_kymDetectionParams":{self._kymDetectionParams}')
            _fileHeaderDict['kymDetectionParams'] = self._kymDetectionParams
            
            for roiLabel, kymRoi in self._roiDict.items():
                # what was used for detection, including [l,t,r,b] of rect roi                

                # just key value pairs for detection parameters
                _fileHeaderDict[roiLabel] = kymRoi.getDetectionParams(channel, PeakDetectionTypes.intensity).getValueDict()
                _fileHeaderDictDiameter[roiLabel] = kymRoi.getDetectionParams(channel, PeakDetectionTypes.diameter).getValueDict()

            # one line json header with all roi and their detection params
            _fileHeaderJson = json.dumps(_fileHeaderDict)
            _fileHeaderJson_diameter = json.dumps(_fileHeaderDictDiameter)
            
            peakPath, diameterPath, _ = self._getSaveFile(channel)
            
            # _savedPeaks = False
            
            dfToSaveIntensity = self.getDataFrame(channel, PeakDetectionTypes.intensity)

            # if len(dfToSaveIntensity) == 0:
            #     pass
            #     # no intensity peaks to save
            # else:
            if 1:
                logger.info(f'saving f/f0 peaks to: {peakPath}')
                # _savedPeaks = True
                with open(peakPath, 'w') as f:
                    f.write(_fileHeaderJson)
                    f.write('\n')
                    f.write(dfToSaveIntensity.to_csv(header=True, index=False, mode='a'))

            dfToSaveDiameter = self.getDataFrame(channel, PeakDetectionTypes.diameter)

            if len(dfToSaveDiameter) == 0:
                # no diameter peaks to save
                pass
            else:
                logger.info(f'saving diameter to: {diameterPath}')
                # _savedPeaks = True
                with open(diameterPath, 'w') as f:
                    f.write(_fileHeaderJson_diameter)
                    f.write('\n')
                    f.write(dfToSaveDiameter.to_csv(header=True, index=False, mode='a'))

            # only save analysis traces if we save (intensity or diameter) peaks
            # 202505 always save, even of no peaks
            # if _savedPeaks:
            if 1:
                self.saveAnalysisTraces(channel)

        self.setDirty(False)
        for roiLabel, roi in self._roiDict.items():
            roi.setDirty(False)

        return True

    def _loadThisFile(self, filePath, channel, peakDetectionType : PeakDetectionTypes, addRois):
        """Load peak detection file from either intensity or diameter.

        Parameters
        ==========
        addRois : bool
            If true then add rois
        """
        if not os.path.isfile(filePath):
            # if peakDetectionType == PeakDetectionTypes.diameter:
            #     logger.info(f'did not find file to load:{filePath}')
            return False

        with open(filePath) as f:
            headerJson = f.readline()
            _headerDict = json.loads(headerJson)

        dfLoadedFromFile = pd.read_csv(filePath, header=1)  # can be empty
        
        # _headerDict is a dict with roi name keys, make a number of rois
        # self._detectionDict = _headerDict
        _firstRoi = None
        for roiNumber,detectionDict in _headerDict.items():
            # roiNumber is str like '1', '2', '3',...
            # logger.info(f'{roiNumber}: {detectionDict}')
            
            if roiNumber == 'kymDetectionParams':
                # abb 202505 colin, global detection params for kym
                # logger.info(f'loading kymDetectionParams detectionDict:{detectionDict}')
                # print(filePath)
                self._kymDetectionParams = detectionDict 
                continue

            kymRoiDetection = KymRoiDetection(peakDetectionType, fromDict=detectionDict)

            # add the roi
            if addRois:
                kymRoi = self.addROI(kymRoiDetection['ltrb'])  # add to all channels
                # logger.info(f'   added roi channel:{channel} kymRoi:{kymRoi}')
            else:
                kymRoi = self.getRoi(roiNumber)

            # set detection
            kymRoi.setDetection(channel, PeakDetectionTypes.intensity, kymRoiDetection)

            # ValueError: invalid literal for int() with base 10: 'kymDetectionParams'
            # fill in analysis results
            oneRoiResults = KymRoiResults()
            dfRoi = dfLoadedFromFile[ dfLoadedFromFile['ROI Number']==int(roiNumber) ]
            dfRoi = dfRoi.reset_index(drop=True)  # Do not try to insert index into dataframe columns.
            oneRoiResults._swapInNewDf(dfRoi)
            # kymRoi._kymRoiResults = oneRoiResults
            kymRoi.setResults(channel, PeakDetectionTypes.intensity, oneRoiResults)
        return True
    
    def loadAnalysis(self):
        _loadedHeaderDict = None
        addRois = True
        for channel in range(self.numChannels):
            peakPath, diameterPath, tracePath = self._getSaveFile(channel, createFolder=False)

            # load header (metadata) from trace file
            if not os.path.isfile(tracePath):
                continue
            else:
                # trace header has path to tif, if use moves entire folder, this is broken

                with open(tracePath) as f:
                    headerJson = f.readline()
                    _loadedHeaderDict = json.loads(headerJson)
                    # print(f'self.path is: {self.path}')
                    # print(f"_loadedHeaderDict.path is: {_loadedHeaderDict['path']}")
                    _loadedHeaderDict['path'] = self.path
                    # logger.info(f'trace header is:{_loadedHeaderDict}')
                    # self._kymRoiMetaData.fromJson(headerJson)
                    self._kymRoiMetaData.fromDict(_loadedHeaderDict)

            loaded_f_f0 = self._loadThisFile(peakPath, channel, PeakDetectionTypes.intensity, addRois=addRois)
            if loaded_f_f0:
                addRois = False
            loaded_diameter = self._loadThisFile(diameterPath, channel, PeakDetectionTypes.diameter, addRois=addRois)
            if loaded_diameter:
                addRois = False

            # there is one trace file per channel, with all roi traces
            # need to file them into the correct kymRoi

            # with open(tracePath) as f:
            #     headerJson = f.readline()
            #     _loadedHeaderDict = json.loads(headerJson)
            #     logger.info(f'trace header is:{_loadedHeaderDict}')

            # set secondsPerLine and umPerPixel
            # self.header['secondsPerLine'] = _headerDict['secondsPerLine']
            # self.header['umPerPixel'] = _headerDict['umPerPixel']

            # one df spanning all roi(s)
            loadedIntDf = pd.read_csv(tracePath, header=1)

            for _roiLabel in self.getRoiLabels():
                try:
                    kymRoi = self.getRoi(_roiLabel)
                    kymRoi.kymRoiTraces[channel].loadTraces(_roiLabel, loadedIntDf)
                except pd.errors.EmptyDataError:
                    # file was empty -->> nothing to load
                    pass
        
        return _loadedHeaderDict
    
    def getParamDataFrame(self) -> pd.DataFrame:
        """Get a dataframe of all detection params.
        
        One row per roi.
        """
        dictList = []
        for roiLabel, roi in self._roiDict.items():
            dictList.append(roi.detectionParams.getValueDict())
        df = pd.DataFrame.from_dict(dictList) 
        return df

    def getAnalysisTrace(self, roi : str, name : str, channel : int) -> np.ndarray:
        kymRoi = self.getRoi(roi)
        return kymRoi.getTrace(channel, name)
    
    def getDetectionParams(self,
                           roi : str,
                           detectionType : PeakDetectionTypes,
                           channel : int) -> KymRoiDetection:
        kymRoi = self.getRoi(roi)
        return kymRoi.getDetectionParams(channel, detectionType)
    
    def getAnalysisResults(self, roi : str,
                           detectionType : PeakDetectionTypes,
                           channel : int) -> KymRoiResults:
        kymRoi = self.getRoi(roi)
        if kymRoi is None:
            logger.error(f'did not find roi label "{roi}"')
            return
        return kymRoi.getAnalysisResults(channel, detectionType)
    
    def detectDiam(self, roi : str, channel : int):
        kymRoi = self.getRoi(roi)
        kymRoi.detectDiam(channel=channel)

    def __iter__(self):
        self._currentIter = -1
        return self

    def __next__(self): # Python 2: def next(self)
        self._currentIter += 1
        if self._currentIter < self.numRoi:
            _keyList = list(self._roiDict.keys())
            _key = _keyList[self._currentIter]
            return self.getRoi(_key)
        raise StopIteration

# utils
def _printImgStat(imgData : np.ndarray, name : str = ''):

    if name != '':
        name += ':'
    numZeros = np.count_nonzero(imgData==0)
    logger.info(f'{name} {imgData.shape} mean:{np.mean(imgData)} median:{np.median(imgData)} min:{np.min(imgData)} max:{np.max(imgData)} num zero:{numZeros} {imgData.dtype}')

def BinLineScans(imgData, numLinesPerBin):
    numLines = imgData.shape[1]
    
    # logger.info(f'numLines:{numLines} numLinesPerBin:{numLinesPerBin}')
    
    retImg = np.empty_like(imgData)
    
    for _idx, line in enumerate(range(numLines)):
        
        lineStart = line - numLinesPerBin
        if lineStart < 0:
            lineStart = 0
        lineStop = line + numLinesPerBin
        if lineStop > imgData.shape[1]-1:
            lineStop = imgData.shape[1]
            
            
        oneSlice = imgData[:, lineStart:lineStop]
        oneLine = np.mean(oneSlice, axis=1)
        
        # if _idx == 100:
        #     logger.info(f'imgData:{imgData.shape} oneSlice:{oneSlice.shape} oneLine:{oneLine.shape}')

        retImg[:,line] = oneLine

    return retImg

def findThreshold(kymRoiTrace : np.ndarray,
                  polarity : str,
                  kymRoiResults : KymRoiResults,
                  _leftRoiRect : int,
                  newOnsetOffsetFraction : float = 0.1,
                  doMpl = False):
    """Refine all peak parameters.
        - Onset
        - Rise 10
        - [depreciated] Rise 90
        - Offset
        - Decay 10
        - [depecriated] Decay 90
        -half-width

    Notes:
    ------
    Removed Rise 90 and Decay 90, scipy peak_detect is good at getting this

    Although scipy peak_detect is awesome for peaks, it is not great at onset/offset beyond half-height.
    Started 20240925 - colin symposium
    """
    
    # _left, _, _, _ = kymRoi.getRect()
    # logger.info(f'_left:{_left}')

    int_df_f0 = kymRoiTrace

    peakBins = kymRoiResults.getValues('Peak Bin')
    peakValues = kymRoiResults.getValues('Peak Int')  # y-value at peak
    
    # will be negative if we detected negative peaks
    peakHeights = kymRoiResults.getValues('Peak Height')  # peak - threshold value
    if polarity == 'Neg':
        peakHeights = -peakHeights
        peakValues = -peakValues
    
    # logger.info(f'   peakHeights:{peakHeights}')
    # logger.info(f'   peakValues:{peakValues}')

    # logger.info(f'polarity:{polarity}')
    # cludge, trying to remove all if pos/neg below
    polarity = 'Pos'

    numPeaks = len(peakBins)
    
    # returns
    # onsetBinList = np.empty(shape=numPeaks)  # [np.nan] * numPeaks
    # onsetBinList[:] = np.nan
    # offsetBinList = np.empty(shape=numPeaks)  # [np.nan] * numPeaks
    # offsetBinList[:] = np.nan
    # onset10BinList = np.empty(shape=numPeaks)  # [np.nan] * numPeaks
    # onset10BinList[:] = np.nan
    # offset10BinList = np.empty(shape=numPeaks)  # [np.nan] * numPeaks
    # offset10BinList[:] = np.nan
    # newPeakHeightList = np.empty(shape=numPeaks)  # [np.nan] * numPeaks
    # newPeakHeightList[:] = np.nan

    onsetBinList = [np.nan] * numPeaks
    offsetBinList = [np.nan] * numPeaks
    onset10BinList = [np.nan] * numPeaks
    offset10BinList = [np.nan] * numPeaks
    newPeakHeightList = [np.nan] * numPeaks
    
    peaksErrors = [''] * numPeaks

    for _idx, peakBin in enumerate(peakBins):
        
        # THIS IS SUPER BAD ... BUT NEEDED
        peakBin -= _leftRoiRect

        yPeak = peakValues[_idx]
        peakHeight = peakHeights[_idx]

        #
        # new rise and decay
        if polarity == 'Pos':
            threshold =  yPeak - (peakHeight * newOnsetOffsetFraction)  # 0.9 is 90% height
        elif polarity == 'Neg':
            threshold =  yPeak + (peakHeight * newOnsetOffsetFraction)  # 0.9 is 90% height
        else:
            logger.error(f'did not understand polarity:{polarity}')

        if polarity == 'Pos':
            threshold_crossings = np.diff(int_df_f0 > threshold, append=False)  # "False" is the value to append
        elif polarity == 'Neg':
            threshold_crossings = np.diff(int_df_f0 < threshold, append=False)  # "False" is the value to append
        thresholdBins = np.where(threshold_crossings[0:peakBin]==1)[0]
        if len(thresholdBins) == 0:
            # _errStr = f'peak {_idx} findThreshold failed to find rise bin.'
            _errStr = f'findThreshold failed to find rise bin.'
            peaksErrors[_idx] += _errStr + ';'
            logger.error(_errStr)
        else:
            thresholdBin = thresholdBins[-1]  # first threshold before peak
            # back it up by one bin ??? When onset is fast, actual threshold crossing is way too high
            # this is achieved with apend=False
            # thresholdBin = thresholdBin - 1
            onsetBinList[_idx] = thresholdBin

            # we have a new peak height
            if polarity == 'Pos':
                peakHeight2 = yPeak - int_df_f0[thresholdBin]
            elif polarity == 'Neg':
                peakHeight2 = yPeak + int_df_f0[thresholdBin]
            newPeakHeightList[_idx] = peakHeight2

            # 10% in rise
            if polarity == 'Pos':
                threshold2 =  yPeak - (peakHeight2 * 0.9)  # 0.9 is 90% height, eg rise 10
            if polarity == 'Neg':
                threshold2 =  yPeak + (peakHeight2 * 0.9)  # 0.9 is 90% height, eg rise 10

            if polarity == 'Pos':
                threshold_crossings2 = np.diff(int_df_f0 > threshold2, prepend=False)
            elif polarity == 'Neg':
                threshold_crossings2 = np.diff(int_df_f0 < threshold2, prepend=False)
            threshold10Bins = np.where(threshold_crossings2[0:peakBin]==1)[0]
            if len(threshold10Bins) == 0:
                # _errStr = f'peak {_idx} findThreshold failed to find 10% rise bin'
                _errStr = f'findThreshold failed to find 10% rise bin'
                logger.error(_errStr)
                peaksErrors[_idx] += _errStr + ';'
            else:
                threshold10Bin = threshold10Bins[-1]  # first threshold before peak
                onset10BinList[_idx] = threshold10Bin

        if polarity == 'Pos':
            threshold_crossings = np.diff(int_df_f0 > threshold, prepend=False)  # "False" is the value to append
        elif polarity == 'Neg':
            threshold_crossings = np.diff(int_df_f0 < threshold, prepend=False)  # "False" is the value to append
        decayBins = np.where(threshold_crossings[peakBin:-1]==1)[0]
        if len(decayBins) == 0:
            # _errStr = f'peak {_idx} findThreshold failed to find falling bin'
            _errStr = f'findThreshold failed to find falling bin'
            peaksErrors[_idx] += _errStr + ';'
            logger.error(_errStr)
        else:
            decayBin = decayBins[0]  # first threshold after peak
            decayBin += peakBin
            offsetBinList[_idx] = decayBin

            # decay has different height
            if polarity == 'Pos':
                peakHeight3 = yPeak - int_df_f0[decayBin]
                threshold3 =  yPeak - (peakHeight3 * 0.9)  # 0.9 is 90% height
            elif polarity == 'Neg':
                peakHeight3 = yPeak + int_df_f0[decayBin]
                threshold3 =  yPeak + (peakHeight3 * 0.9)  # 0.9 is 90% height
            # using append=False to backup bin by one
            if polarity == 'Pos':
                threshold_crossings3 = np.diff(int_df_f0 > threshold3, append=False)  # "False" is the value to append
            elif polarity == 'Neg':
                threshold_crossings3 = np.diff(int_df_f0 < threshold3, append=False)  # "False" is the value to append
            decay10Bins = np.where(threshold_crossings3[peakBin:-1]==1)[0]
            if len(decay10Bins) == 0:
                # _errStr = f'peak {_idx} findThreshold failed to find 10% falling bin'
                _errStr = f'findThreshold failed to find 10% falling bin'
                logger.error(_errStr)
                peaksErrors[_idx] += _errStr + ';'
            else:
                decay10Bin = decay10Bins[0]  # first threshold after peak
                decay10Bin += peakBin
                offset10BinList[_idx] = decay10Bin

        if doMpl and _idx in [1,2]:
            # make a new figure each time. I do not understand matplotlib !!!
            fig, axs = plt.subplots(1, 1, figsize=(18,10))
            axs = [axs]

            # raw int
            axs[0].plot(int_df_f0, color='k', marker='', label='intensity')
            axs[0].set_xlim([peakBin-75, peakBin+75])

            # peak
            axs[0].plot(peakBin, int_df_f0[peakBin], color='c', marker='^', label='peak')

            #
            axs[0].axhline(y=threshold)

            # new threshold
            try:
                plt.plot(thresholdBin, int_df_f0[thresholdBin], color='c', marker='o', markersize=10, label='thresholdBin')
            except (UnboundLocalError) as e:
                logger.error(e)

            # old threshold
            # plt.plot(thresholdBin_orig, int_df_f0[thresholdBin_orig], color='y', marker='s', markersize=10, label='thresholdBin_orig')
            # plt.plot(decayBin_orig, int_df_f0[decayBin_orig], color='y', marker='s', markersize=10, label='decayBin_orig')

            # decay
            try:
                plt.plot(decayBin, int_df_f0[decayBin], color='m', marker='o', markersize=10, label='decayBin')
            except (UnboundLocalError) as e:
                logger.error(e)

            # threshold crossings
            # try:
            #     axs[0].plot(threshold_crossings, color='r', marker='o', label='threshold_crossings')
            # except (UnboundLocalError) as e:
            #     logger.error(e)
            
            axs[0].legend()
            plt.show()

    return onsetBinList, offsetBinList, onset10BinList, offset10BinList, peaksErrors

# def plotDetectionResults(kymRoi : KymRoi, channel):
def plotDetectionResults(kymRoiAnalysis : KymRoiAnalysis,
                         roiLabelStr,
                         channel):
    """Plot analysis steps using MatPlotLib.
        - Raw sum
        - Detrended sum
        - df/d0
    
    Parameters
    ----------
    kymRoi : KymROi
        Results for one ROI
    """
    _channelColor = kymRoiAnalysis.getChannelColor(channel=channel)
    
    kymRoi = kymRoiAnalysis.getRoi(roiLabelStr)
    
    imgData = kymRoi.getRoiImg(channel=channel)

    timeSec = kymRoi.getTrace(channel, 'Time (s)')  # seconds
    intRaw = kymRoi.getTrace(channel, 'intRaw')
    intDetrend = kymRoi.getTrace(channel, 'intDetrend')
    logger.warning('defaulting to santana f/f0')
    int_df_f0 = kymRoi.getTrace(channel, 'f/f0')  # yDf_f0

    detectionParams = kymRoi.getDetectionParams(channel, PeakDetectionTypes.intensity)
    analysisResults = kymRoi.getAnalysisResults(channel, PeakDetectionTypes.intensity)

    peakSecond = analysisResults.getValues('Peak (s)')
    peakValue = analysisResults.getValues('Peak Int')

    #
    fig, axs = plt.subplots(4, 1, figsize=(6,8), sharex=True)

    roiLabel = kymRoi.getLabel()
    _backgroundsubtract = f"Background subtract: {detectionParams['Background Subtract']}"
    _title = f'{os.path.split(kymRoi.path)[1]}, ROI {roiLabel}, {_backgroundsubtract}'
    fig.suptitle( _title )

    # image
    left, top, right, bottom = kymRoi.getRect()
    # logger.info(f'timeSec:{timeSec} {type(timeSec)}')
    # abb removed 20250508
    # try:
    #     leftSec = timeSec.values[0]
    #     rightSec = timeSec.values[-1]
    # except (AttributeError) as e:
    #     logger.error(f'sometimes timeSec is pandas, sometimes numpy ???: {e}')
    #     logger.error(f'  timeSec is type:{type(timeSec)}')
    #     logger.error(f'  timeSec:{timeSec}')
    #     logger.error(f'  roi left:{left}')
    #     leftSec = timeSec[0]
    #     rightSec = timeSec[-1]

    logger.warning('should be using left of roi (pixels)')
    leftSec = timeSec[0]
    rightSec = timeSec[-1]

    _extent=[leftSec, rightSec, bottom, top]
    # logger.info(f'_extent:{_extent}')
    # _label = f"Background subtract: {kymRoi.detectionParams['backgroundsubtract']}"
    imgplot = axs[0].imshow(imgData, extent=_extent, aspect="auto")
    
    # I do not like how 'Greens' look ...
    imgplot.set_cmap('nipy_spectral')
    # if _channelColor == 'Green':
    #     imgPlotColor = 'Greens'
    # else:
    #     imgPlotColor = 'Reds'
    # imgplot.set_cmap(imgPlotColor)
    # axs[0].legend(loc='upper right')  # legend does not work with imshow()

    # raw sum with fit
    axs[1].plot(timeSec, intRaw, _channelColor, label=f"Sum (bins={detectionParams['Bin Line Scans']})")
    axs[1].set_ylabel('Intensity (per pixel)')
    # add exp fit
    fitDict = detectionParams['expDetrendFit']
    if fitDict is None:
        logger.info('expDetrend is off -->> no fit')
        # axs[0].legend('No Exp Detrend')
    else:
        _m = fitDict['m']
        _t = fitDict['tau']
        _b = fitDict['b']
        yFit = myMonoExp(timeSec, _m, _t, _b)
        _m = round(_m, 1)
        _t = round(_t, 1)
        _b = round(_b, 1)
        # ret = m * np.exp(-t * x) + b
        # _label = f'y = {_m} * exp(-{_t} * x) + {_b}'
        _label = 'Exp Fit'
        axs[1].plot(timeSec, yFit, 'c', label=_label)
        axs[1].legend()

    # after remove fit (if on) and selecting f0
    # axs[2].plot(timeSec, intDetrend, 'r', label='Detrend')
    axs[2].plot(timeSec, intDetrend, _channelColor)
    axs[2].set_ylabel('Subtract exp')
    # add f0
    f0_type = detectionParams['f0 Type']
    if f0_type == 'Percentile':
        _f0 = detectionParams['f0 Value Percentile']
    elif f0_type == 'Manual':
        _f0 = detectionParams['f0 Value Manual']
    else:
        logger.error(f'did not understand f0_type:{f0_type}')
        _f0=1
    _label = f"f0 {f0_type} = {round(_f0,2)}"
    axs[2].axhline(y=_f0, label=_label, color='c')
    axs[2].legend()

    # final dF/F0, with peaks (and fit)
    logger.warning('TODO: dynamically switch betwee df/d0 and santana f/f0')
    axs[3].plot(timeSec, int_df_f0, _channelColor, label='f/f0')
    axs[3].set_ylabel('f/f0')
    axs[3].plot(peakSecond, peakValue, 'go')
    axs[2].legend()

    # rise
    # axs[2].plot(peak10_left_ips, yDf_f0[peak10_left_ips.astype(int)], 'ro')
    # axs[2].plot(peak90_left_ips, yDf_f0[peak90_left_ips.astype(int)], 'r^')

    # decay
    # axs[2].plot(peak10_right_ips, yDf_f0[peak10_right_ips.astype(int)], 'co')
    # axs[2].plot(peak90_right_ips, yDf_f0[peak90_right_ips.astype(int)], 'c^')

    #
    # (1) exp decay

    # fix this constant bug !!!!
    [_left, _, _, _] = kymRoi.getRect()
    _peakBins = analysisResults.getValues('Peak Bin')

    xDecay = []
    yDecay = []
    for _peakIdx, _peakBin in enumerate(_peakBins):
        
        _peakBin = _peakBin - _left
        
        fit_m = analysisResults.getValues('fit_m')[_peakIdx]            
        fit_tau = analysisResults.getValues('fit_tau')[_peakIdx]
        fit_b = analysisResults.getValues('fit_b')[_peakIdx]

        if np.isnan(fit_m):
            # logger.warning(f'no fit for peak {_peakIdx}')
            continue

        # ms to bin
        _decayMs = detectionParams['Decay (ms)']
        _decayBin = _decayMs / 1000 / kymRoi._header['secondsPerLine']
        _decayBin = int(round(_decayBin))

        # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine
        decayFitBins = _decayBin
        _xRange = timeSec[_peakBin:_peakBin+decayFitBins] - timeSec[_peakBin]
        
        # get line showing our fit
        fit_y = myMonoExp(_xRange, fit_m, fit_tau, fit_b)

        xDecay.extend(_xRange+timeSec[_peakBin])
        xDecay.append(np.nan)

        yDecay.extend(fit_y)
        yDecay.append(np.nan)
    #
    axs[3].plot(xDecay, yDecay, 'c')  # single exp fit to decay

    #
    # (2) double exp decay
    xDecay2 = []
    yDecay2 = []
    for _peakIdx, _peakBin in enumerate(_peakBins):
        
        # fix this constant bug !!!!
        _peakBin = _peakBin - _left
        
        fit_m1 = analysisResults.getValues('fit_m1')[_peakIdx]            
        fit_tau1 = analysisResults.getValues('fit_tau1')[_peakIdx]
        fit_m2 = analysisResults.getValues('fit_m2')[_peakIdx]            
        fit_tau2 = analysisResults.getValues('fit_tau2')[_peakIdx]

        if np.isnan(fit_m1):
            # logger.warning(f'no dbl exp fit for peak {_peakIdx}')
            continue

        # ms to bin
        _decayMs = detectionParams['Decay (ms)']
        decayFitBins = _decayMs / 1000 / kymRoi._header['secondsPerLine']
        decayFitBins = int(round(decayFitBins))

        _xRange = timeSec[_peakBin:_peakBin+decayFitBins] - timeSec[_peakBin]
        
        # get line showing our fit
        fit_y = myDoubleExp(_xRange, fit_m1, fit_tau1, fit_m2, fit_tau2)

        xDecay2.extend(_xRange+timeSec[_peakBin])
        xDecay2.append(np.nan)

        yDecay2.extend(fit_y)
        yDecay2.append(np.nan)
    #
    axs[3].plot(xDecay2, yDecay2, 'b')  # double exp fit to decay

    plt.show()

if __name__ == '__main__':
    pass