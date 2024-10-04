import json
import os
import sys
from typing import List

import numpy as np
import pandas as pd
import tifffile

import scipy.optimize
from scipy.signal import peak_widths, medfilt, savgol_filter, detrend, find_peaks
from skimage import restoration

import matplotlib.pyplot as plt

from sanpy._util import _loadLineScanHeader
from sanpy.kym.kymRoiDetection import KymRoiDetection, getAnalysisDict
from sanpy.kym.kymRoiResults import KymRoiResults

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def myDetrend(xPlot, yPlot, doPlot=False):
    # from scipy.signal import detrend
    
    y_log = np.log(yPlot)
    y_log_detrended = detrend(y_log)
    
    y_detrended = np.exp(y_log_detrended)

    try:
        _params, _cov = scipy.optimize.curve_fit(myMonoExp, xPlot, yPlot)
    except (RuntimeError) as e:
        logger.error(e)
        logger.error('DID NOT PERFORM single exp DETREND')
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

def getSavitzkyGolay_Filter(y: np.ndarray, pnts: int = 5, poly: int = 2, verbose=False):
    """Get SavitzkyGolay filtered version of y using scipy.signal.savgol_filter"""
    if verbose:
        logger.info("")
    filtered = savgol_filter(y, pnts, poly, mode="nearest", axis=0)
    return filtered

class KymRoi:
    """One rectangular ROI.
    """
    def __init__(self, label : str,
                 kymRoiAnalysis : "KymRoiAnalysis",
                 imgData : np.ndarray,
                 header : dict,
                 ltrbRect : List[int] = None,
                 kymRoiDetection : KymRoiDetection = KymRoiDetection(),
                 doAnalysis : bool = False,
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
            Seed with this rect, if none than use getDefaultRect()
        kymRoiDetection : KymRoiDetection
            Seed with this detection, if None then use defaults
        """
        self._label = label
        self._kymRoiAnalysis = kymRoiAnalysis  # just used to set _isDirty
        self._imgData = imgData
        
        if ltrbRect is None:
            ltrbRect = self.getDefaultRect()
        self._ltrbRect = ltrbRect
        
        # store a copy
        self._kymRoiDetection = KymRoiDetection(kymRoiDetection)  # detection used in peakDetect()
        
        self._header = header

        self._kymRoiResults = KymRoiResults()

        # self._analysisTraces['timeSec'] = xPlot
        # self._analysisTraces['intRaw'] = yRaw  # raw sum intensity
        # self._analysisTraces['intDetrend'] = yDetrend # after detrend with single exponential
        # self._analysisTraces['int_df_f0'] = yDf_f0

        self._analysisTraceList = ['timeSec', 'intRaw', 'intDetrend', 'int_df_f0', 'int_f_f0']
        self._analysisTraces = {}  # filled in in peakDetect()

        if doAnalysis:
            self.detectPeaks()

    def getTrace(self, name):
        """Get a trace name fomr analysis.
        """
        if name not in self._analysisTraces.keys():
            logger.error(f'did not find trace name "{name}". Available names are {self._analysisTraces.keys()}')
            print(self._analysisTraces.keys())
            return
        return self._analysisTraces[name]
    
    def __str__(self):
        ret = f'{self._label} {self._ltrbRect}'
        return ret
    
    def getLabel(self):
        return self._label
    
    @property
    def path(self):
        return self._header['path']
    
    @property
    def umPerPixel(self):
        return self._header['umPerPixel']
    
    @property
    def secondsPerLine(self):
        return self._header['secondsPerLine']
    
    def getDefaultRect(self):
        h, w = self._imgData.shape
        left = 0
        top = h
        right = w
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
        
    def getRect(self) -> List[int]:
        """Get the current roi as [l, t, r, b]
        """
        return self._ltrbRect
    
    def setRect(self, ltrb : List, doAnalysis : bool = False):
        """Set the roi rect [l, t, r, b]
        """
                
        ltrbActual = self._getConstrainedRoi(ltrb)

        logger.info(f'   proposed ltrb:{ltrb}')
        logger.info(f'   contrain ltrb:{ltrbActual}')

        self._ltrbRect = ltrbActual
        
        # if doAnalysis:
        #     self.peakDetect()

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
        
        logger.info(f'pos:{pos} size:{size}')
        logger.info(f'newRect:{newRect}')
        
        self.setRect(newRect)

        return newRect
    
    def _getConstrainedRoi(self, ltrb) -> List[int]:
        """Given a rect, return rect constrained to imgData.
        """

        left = ltrb[0]
        top = ltrb[1]
        right = ltrb[2]
        bottom = ltrb[3]

        heightMax = self._imgData.shape[0]
        widthMax = self._imgData.shape[1]

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
 
    @property
    def detectionParams(self):
        return self._kymRoiDetection
    
    @property
    def analysisResults(self):
        return self._kymRoiResults
    
    def getRoiImg(self):
        """Get roi inside the rect.
        """
        left, top, right, bottom = self.getRect()
        roiImg = self._imgData[bottom:top, left:right]
        roiImg = np.copy(roiImg)
        return roiImg
    
    def backgroundSubtract(self, roiImg):
        
        backgroundsubtract = self.detectionParams['backgroundsubtract']

        # _printImgStat(roiImg, f'before background subtract: "{backgroundsubtract}"')        
                
        if backgroundsubtract == 'Off':
            pass
        
        elif backgroundsubtract == 'Rolling-Ball':
            _rollingBallRadius = 50
            logger.info(f'   _rollingBallRadius:{_rollingBallRadius}')
            rollingBackground = restoration.rolling_ball(roiImg, radius=_rollingBallRadius)
            _printImgStat(rollingBackground, '   rollingBackground img')
            roiImg = roiImg - rollingBackground
        
        elif backgroundsubtract == 'Median':
            # logger.warning('problem with median is "after" we get negative value and can not perform log transform !!!')
            _subtactValue = np.median(roiImg).astype(np.int64)
            # logger.info(f'   _subtactValue: {type(_subtactValue)} {_subtactValue}')
            roiImg = roiImg - _subtactValue
            roiImg[roiImg<0] = 0
            self.detectionParams['backgroundSubtractValue'] = int(_subtactValue)

        elif backgroundsubtract == 'Mean':
            _subtactValue = np.mean(roiImg).astype(np.int64)
            # logger.info(f'   _subtactValue: {type(_subtactValue)} {_subtactValue}')
            roiImg = roiImg - _subtactValue
            roiImg[roiImg<0] = 0
            self.detectionParams['backgroundSubtractValue'] = int(_subtactValue)
        
        else:
            logger.error(f'did not understand background subtract "{backgroundsubtract}" -->> no subtraction')

        # _printImgStat(roiImg, f'after background subtract: "{backgroundsubtract}"')        

        return roiImg
    
    def getSumIntensity(self):
        """Get sum intensity for each line scan.
        
        Algorithm
        ---------
            1) background subtract roi image
            2) Bin line scans using mean for each pixel across a bin line scan width
            3) sum intensity of each lnie scan
            4) normalize each intensity line scan to number of pixels

        Returns
        -------
            Tuple of (x, y)
        """
        roiImg = self.getRoiImg()  # get imgData within ROI
        
        _left, _top, _right, _bottom = self.getRect()
        
        # xPlot = np.arange(roiImg.shape[1]) * self.secondsPerLine
        xPlot = np.arange(_left, _right, dtype=np.float32) * self.secondsPerLine

        # "background" subtract
        # background subtract can not result in negative values
        roiImg = self.backgroundSubtract(roiImg)
        # _printImgStat(roiImg, f'after backgroundsubtract: with "{backgroundsubtract}"')

        binLineScans = self.detectionParams['binLineScans']
        # logger.info(f'binLineScans:{binLineScans}')
        if binLineScans == 0:
            pass
        else:
            roiImg = BinLineScans(roiImg, binLineScans)

        # sum intensities in each line scan
        sumInt = np.sum(roiImg, axis=0)
        # normalize to number of points in line scan
        sumInt = sumInt / roiImg.shape[0]

        #
        # filter
        if self.detectionParams['medianfilter']:
            # 1) medfilt
            medianfilterkernel = self.detectionParams['medianfilterkernel']
            # logger.info(f'   applying median filter with medianfilterkernel:{medianfilterkernel}')
            sumInt = medfilt(sumInt, kernel_size=medianfilterkernel)

        if self.detectionParams['filter']:
            # 2) SavitzkyGolay_Filter
            # logger.info(f'   applying Savitzky-Golay filter')
            sumInt = getSavitzkyGolay_Filter(sumInt)

        return xPlot, sumInt

    def _msToBin(self, msValue : float) -> int:
        """Convert ms to nearest bin using round.
        """
        _retBin1 = msValue / 1000 / self.secondsPerLine
        _retBin2 = int(round(_retBin1))
        # logger.info(f'msValue:{msValue} _retBin1:{_retBin1} _retBin2:{_retBin2}')
        return _retBin2
    
    def getAnalysisTraces(self):
        return self._analysisTraces

    def peakDetect(self, verbose : bool = False):
        # store the ltrb of rect we analysed
        roiRect = self.getRect()
        self.detectionParams['ltrb'] = roiRect
        _left = roiRect[0]

        logger.info(f'=== === peakDetect()   === === roi label:{self._label} with detectionParams === ===')
        if verbose:
            print(self.detectionParams.printValues())

        # parameters
        detectThisTrace = self.detectionParams['detectThisTrace']  # from (int_df_f0, int_f_f0)
        polarity = self.detectionParams['polarity']
        prominence = self.detectionParams['prominence']
        width = self.detectionParams['width (ms)'] / 1000 / self.secondsPerLine
        distance = self.detectionParams['distance (ms)'] / 1000 / self.secondsPerLine

        # if f0ManualPercentile=='Manual' then user need to directly set f0, we do not calulate it
        f0ManualPercentile = self.detectionParams['f0ManualPercentile']  # in (Manual, Percentile)
        f0Percentile = self.detectionParams['f0 Percentile']
        manual_f0 = f0ManualPercentile == 'Manual'
        percentile_f0 = f0ManualPercentile == 'Percentile'
        if manual_f0 and self.detectionParams['f0Value'] is None:
            logger.warning('f0ManualPercentile is set to "Manual" but f0Value is None --> user needs to set value')
            return
        f0 = self.detectionParams['f0Value']

        xPlot, yRaw = self.getSumIntensity()  # does background subtraction
       
        # subtract single exponential to account for intensity decay (bleaking)
        # yRaw can not have negative values (We are taking the log)
        doExpDetrend = self.detectionParams['doExpDetrend']
        if doExpDetrend:
            logger.info(f'detrend')
            logger.info(f'   xPlot:{xPlot}')
            logger.info(f'   yRaw:{yRaw}')
            
            fitDict, yDetrend = myDetrend(xPlot, yRaw, doPlot=False)
            
            if fitDict is None:
                logger.error('error calling myDetrend')
                yDetrend = yRaw

            else:
                self.detectionParams['expDetrendFit'] = fitDict  # store the fit params

                # shift back to all positive
                yDetrend += abs(np.min(yDetrend))

        else:
            yDetrend = yRaw
            self.detectionParams['expDetrendFit'] = None  # when off -->> no fit

        # get df/f0 (f0 = median)
        if percentile_f0:
            if polarity == 'Neg':
                f0Percentile = 100 -f0Percentile

            f0 = np.percentile(yDetrend, f0Percentile)
            # logger.info(f'   TODO: what is f0? Using f0Percentile:{f0Percentile} gives f0:{f0}')
            self.detectionParams['f0Value'] = float(f0)  # store the f0 value
        else:
            logger.info(f'colin symposium -->> using user specified f0:{f0}')

        # proper dF/F0
        yDf_f0 = (yDetrend - f0) / f0
        # santana likes
        f_f0 = yDetrend / f0

        #
        # add everything to a NEW results object
        self._kymRoiResults = KymRoiResults()  # create a new one each time we run analysis
        oneRoiResults = self._kymRoiResults  # to ractor from widget

        # self._isDirty = True
        self._kymRoiAnalysis._isDirty = True

        #
        # store what we used for analysis
        self._analysisTraces['timeSec'] = xPlot
        self._analysisTraces['intRaw'] = yRaw  # raw sum intensity
        self._analysisTraces['intDetrend'] = yDetrend # after detrend with single exponential
        self._analysisTraces['int_df_f0'] = yDf_f0
        self._analysisTraces['int_f_f0'] = f_f0

        yDf_f0 = self._analysisTraces[detectThisTrace]

        #
        if polarity == 'Pos':
            detectThisY = yDf_f0
        elif polarity == 'Neg':
            detectThisY = -yDf_f0
        else:
            logger.error(f'   did not understand polarity:"{polarity}"')
                                                        
        #
        # find peaks (this includes half-width)
        #
        # will default to rel_height 0.5, 1 is foot, 0 is peak
        peakTuple = find_peaks(detectThisY,
                               prominence=prominence,
                               distance=distance,
                               width=width,
                            #    rel_height = thresh_rel_height,
                               )
        peakBins = peakTuple[0]
        peakDict = peakTuple[1]

        logger.info(f'   detected {len(peakBins)} peaks with peakBins:{peakBins}')

        if polarity == 'Neg':
            peakDict['width_heights'] = -peakDict['width_heights']

        numPeaks = len(peakBins)
        yPeaks = []
        if numPeaks == 0:
            return
        
        # GOT SOME PEAKS
        # IMPORTANT, do this first to seed proper number of rows
        oneRoiResults.setValues('Peak Number', range(1,numPeaks+1))  # +1 because range is [)
        oneRoiResults.setValues('ROI Number', self._label)
        oneRoiResults.setValues('Path', self.path)
        oneRoiResults.setValues('Accept', True)  # all peaks start as Accept=True
        oneRoiResults.setValues('Detection Errors', '')  # all peaks start as errors = ''

        oneRoiResults.setValues('Peak Bin', peakBins)
        _peakSeconds = (peakBins + _left) * self.secondsPerLine
        oneRoiResults.setValues('Peak Second', _peakSeconds)
        yPeaks = yDf_f0[peakBins]
        oneRoiResults.setValues('Peak Int', yPeaks)

        # shift everything by the left pixel of our ROI
        # peakBins = peakBins + _left
        # peakDict['left_ips'] = peakDict['left_ips'] + _left
        # peakDict['right_ips'] = peakDict['right_ips'] + _left

        #
        # get the onset and offset of the peak
        thresh_rel_height = self.detectionParams['thresh_rel_height']  # using default of 0.85, 1 is foot, 0 is peak
        peak_10_tuple = peak_widths(detectThisY, peakBins, rel_height=thresh_rel_height)
        peak10_widths = peak_10_tuple[0]
        peak10_width_heights = peak_10_tuple[1]
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
        oneRoiResults.setValues('Peak Interval (s)', _peakInterval)
        oneRoiResults.setValues('Peak Freq (Hz)', 1 / _peakInterval)

        # take off threshold, this is not good and will be replaced by results of findThreshold()
        # thresholdBin = np.round(peak10_left_ips)
        # thresholdBin = thresholdBin.astype(np.int64)  # use this as list index
        # # oneRoiResults.setValues('Threshold Bin Fraction', peak10_left_ips)  # threshold in fractional bins
        # oneRoiResults.setValues('Threshold Bin', thresholdBin)  # potentially sloppy
        # oneRoiResults.setValues('Threshold Second', (thresholdBin + _left)  * self.secondsPerLine)
        # oneRoiResults.setValues('Threshold Value', yDf_f0[thresholdBin])  # yPlot is already reduced to roi (left)

        # return to baseline, this is not good and will be replaced by results of findThreshold()
        # decayBin = np.round(peak10_right_ips)
        # decayBin = decayBin.astype(np.int64)  # use this as list index
        # # oneRoiResults.setValues('Decay Bin Fraction', peak10_right_ips)  # threshold in fractional bins
        # oneRoiResults.setValues('Decay Bin', decayBin)  # potentially sloppy
        # oneRoiResults.setValues('Decay Second', (decayBin + _left)  * self.secondsPerLine)
        # oneRoiResults.setValues('Decay Value', yDf_f0[decayBin]) # yPlot is already reduced to roi (left)

        # peak height
        # peakHeight = np.subtract(oneRoiResults.getValues('Peak Int'), oneRoiResults.getValues('Onset Value'))
        # oneRoiResults.setValues('Peak Height', peakHeight)

        #
        # hw, this is directly from find_peaks
        hwLeftBin = np.round(peakDict['left_ips']).astype(np.int64)
        hwRightBin = np.round(peakDict['right_ips']).astype(np.int64)
        oneRoiResults.setValues('HW Left Bin', hwLeftBin)
        oneRoiResults.setValues('HW Right Bin', hwRightBin)
        
        oneRoiResults.setValues('HW Height', peakDict['width_heights'])

        hwSeconds = ((peakDict['right_ips'] + _left) * self.secondsPerLine) - ((peakDict['left_ips'] + _left) * self.secondsPerLine)
        hwMs = hwSeconds * 1000
        oneRoiResults.setValues('HW (ms)', hwMs)

        ##
        # CRITICAL: refine peak params using my findThreshold()
        # this requires the following to be filled in: (Peak Bin, Peak, Peak Height)
        ##
        newOnsetOffsetFraction = self.detectionParams['newOnsetOffsetFraction']
        newOnsetBins, newDecayBins, newOnset10Bins, newDecay10Bins, newHeight = findThreshold(self, newOnsetOffsetFraction=newOnsetOffsetFraction)

        newOnsetSeconds = [(_bin+_left)*self.secondsPerLine for _bin in newOnsetBins]
        newDecaySeconds = [(_bin+_left)*self.secondsPerLine for _bin in newDecayBins]

        newOnset10Seconds = [(_bin+_left)*self.secondsPerLine for _bin in newOnset10Bins]
        newDecay10Seconds = [(_bin+_left)*self.secondsPerLine for _bin in newDecay10Bins]

        # fill in with new/refined results
        oneRoiResults.setValues('Onset Bin', newOnsetBins)  
        oneRoiResults.setValues('Onset Second', newOnsetSeconds)
        oneRoiResults.setValues('Onset Int', yDf_f0[newOnsetBins])  # yPlot is already reduced to roi (left)
        # peak height is wrt onset (not decay)
        peakHeight = np.subtract(oneRoiResults.getValues('Peak Int'), oneRoiResults.getValues('Onset Int'))
        oneRoiResults.setValues('Peak Height', peakHeight)

        oneRoiResults.setValues('Onset 10 Bin', newOnset10Bins)  
        oneRoiResults.setValues('Onset 10 Second', newOnset10Seconds)
        oneRoiResults.setValues('Onset 10 Int', yDf_f0[newOnset10Bins])  # yPlot is already reduced to roi (left)

        oneRoiResults.setValues('Decay Bin', newDecayBins)  
        oneRoiResults.setValues('Decay Second', newDecaySeconds)
        oneRoiResults.setValues('Decay Int', yDf_f0[newDecayBins]) # yPlot is already reduced to roi (left)

        oneRoiResults.setValues('Decay 10 Bin', newDecay10Bins)  
        oneRoiResults.setValues('Decay 10 Second', newDecay10Seconds)
        oneRoiResults.setValues('Decay 10 Int', yDf_f0[newDecay10Bins]) # yPlot is already reduced to roi (left)

        ##
        # done refining with findThreshold()
        ##

        # 90% or rise and decay works with peak detect
        rel_height = 0.1  # 1 is base, 0 is peak
        peak_90_tuple = peak_widths(detectThisY, peakBins, rel_height=rel_height)
        peak90_widths = peak_90_tuple[0]
        peak90_width_heights = peak_90_tuple[1]
        peak90_left_ips = peak_90_tuple[2]
        peak90_right_ips = peak_90_tuple[3]
        # shift everything by the left pixel of our ROI
        # peak90_left_ips = peak90_left_ips + _left
        # peak90_right_ips = peak90_right_ips + _left

        peak90Bin = np.round(peak90_left_ips)
        peak90Bin = peak90Bin.astype(np.int64)  # use this as list index
        # oneRoiResults.setValues('Peak 90 Bin Fraction', peak90_left_ips)  # threshold in fractional bins
        oneRoiResults.setValues('Onset 90 Bin', peak90Bin)  # potentially sloppy
        oneRoiResults.setValues('Onset 90 Second', (peak90Bin + _left)  * self.secondsPerLine)
        oneRoiResults.setValues('Onset 90 Int', yDf_f0[peak90Bin])  # yPlot is already reduced to roi (left)

        # 90 of decay, this is from peak_detect and is good
        decay90Bin = np.round(peak90_right_ips)
        decay90Bin = decay90Bin.astype(np.int64)  # use this as list index
        # oneRoiResults.setValues('Decay 90 Bin Fraction', peak90_right_ips)  # threshold in fractional bins
        oneRoiResults.setValues('Decay 90 Bin', decay90Bin)  # potentially sloppy
        oneRoiResults.setValues('Decay 90 Second', (decay90Bin + _left) * self.secondsPerLine)
        oneRoiResults.setValues('Decay 90 Int', yDf_f0[decay90Bin]) # yPlot is already reduced to roi (left)

        #
        # colin symposium, full width from onset to offset (using peak "10" detection)
        fwSeconds = ((peak10_right_ips + _left) * self.secondsPerLine) - ((peak10_left_ips + _left) * self.secondsPerLine)
        fwMs = fwSeconds * 1000
        oneRoiResults.setValues('FW (ms)', fwMs)


        # colin, full with from rise 10 to decay 10
        fw10Seconds = (oneRoiResults.getValues('Decay 10 Second') - oneRoiResults.getValues('Onset 10 Second'))
        fw10Ms = fw10Seconds * 1000
        oneRoiResults.setValues('FW 10 (ms)', fw10Ms)

        # Rise Decay 10 width (ms)

        # rise and decay time (from onset to peak and peak to decay)
        riseTimeSeconds = oneRoiResults.getValues('Peak Second') - oneRoiResults.getValues('Onset Second')  # element wise subtract
        riseTimeMs = riseTimeSeconds *1000
        oneRoiResults.setValues('Rise Time (ms)', riseTimeMs)

        decayTimeSeconds = oneRoiResults.getValues('Decay Second') - oneRoiResults.getValues('Peak Second')  # element wide subtraction
        decayTimeMs = decayTimeSeconds *1000
        oneRoiResults.setValues('Decay Time (ms)', decayTimeMs)


        # colin symposium
        riseTen90Seconds = oneRoiResults.getValues('Onset 90 Second') - oneRoiResults.getValues('Onset 10 Second')  # element wise subtract
        rise1090Ms = riseTen90Seconds *1000
        oneRoiResults.setValues('10-90 Rise Time (ms)', rise1090Ms)

        decay1090Seconds = oneRoiResults.getValues('Decay 10 Second') - oneRoiResults.getValues('Decay 90 Second')  # element wise subtract
        decay1090Ms = decay1090Seconds *1000
        oneRoiResults.setValues('10-90 Decay Time (ms)', decay1090Ms)

        #
        # (1) exp fit of each peak
        # [_left, _, _, _] = self.roiList._roiAsRect(roi)
        # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine  # TODO: convert to sec or ms
        decayFitBins = self._msToBin(self.detectionParams['decay (ms)'])
        # fit_m, fit_tau, fit_b, fit_r2, fit_error = _expFit(xPlot, yDf_f0, peakBins - _left, decayFitBins=decayFitBins)
        fit_m, fit_tau, fit_b, fit_r2, fit_error = _expFit(xPlot, yDf_f0, peakBins, decayFitBins=decayFitBins)
        oneRoiResults.setValues('fit_m', fit_m)
        oneRoiResults.setValues('fit_tau', fit_tau)
        oneRoiResults.setValues('fit_b', fit_b)
        oneRoiResults.setValues('fit_r2', fit_r2)
        # logger.info(f'fit_error is:{fit_error}')
        for _peakErrorIdx, oneError in enumerate(fit_error):
            if oneError != '':
                oneRoiResults.addError(_peakErrorIdx, oneError)

        #
        # (2) double exp fit of each peak
        # [_left, _, _, _] = self.roiList._roiAsRect(roi)
        # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine  # TODO: convert to sec or ms
        decayFitBins = self._msToBin(self.detectionParams['decay (ms)'])
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
                oneRoiResults.addError(_peakErrorIdx, oneError)

class KymRoiAnalysis:
    def __init__(self, path : str = None,
                 imgData : np.ndarray = None):
        """
        Parameters
        ----------
        path : str
            Full path to .tif file
        """
        self._path = path
        
        # find corresponding Olympus txt file with params
        olympusHeader = _loadLineScanHeader(path)

        if imgData is not None:
            self._imgData = imgData
            logger.info(f'from imgData:{self._imgData.shape}')
        elif path is not None:
            self._imgData = tifffile.imread(path)
            # self._imgData = self._imgData.astype(np.int64)  # to all pos and negative
            if self._imgData.dtype == np.uint8:
                logger.warning(f'converting self._imgData from: {self._imgData.dtype} to np.int8')
                self._imgData = self._imgData.astype(np.int8)  # to all pos and negative
            elif self._imgData.dtype == np.uint16:
                logger.warning(f'converting self._imgData from: {self._imgData.dtype} to np.int16')
                self._imgData = self._imgData.astype(np.int16)  # to all pos and negative

            if olympusHeader is not None:
                self._imgData = np.rot90(self._imgData)
                # self._imgData = np.flip(self._imgData)

            logger.info(f'from path:{self._imgData.shape}')
        else:
            logger.error('please specify either a path or imgData')

        self._defaultChannel = 1

        _date = ''
        _time = ''
        secondsPerLine = 0.002
        umPerPixel = 0.15
        
        if olympusHeader is not None:
            _date = olympusHeader['date']
            _time = olympusHeader['time']
            secondsPerLine = olympusHeader['secondsPerLine']
            umPerPixel = olympusHeader['umPerPixel']

            if len(self.imgData.shape) == 3:
                self._imgData = self._imgData[:, :, self._defaultChannel]

            # self._imgData = np.rot90(self._imgData)
            # self._imgData = np.flip(self._imgData, axis=0)

        self._headerDict = {
            'path' : path,
            'date': _date,
            'time': _time,
            'secondsPerLine' : secondsPerLine,
            'umPerPixel' : umPerPixel,
        }

        self._roiDict = {}  # keys are labels, values are KymRoi

        self._isDirty = False

        logger.info(f'loaded self._imgData.shape:{self._imgData.shape}')
        logger.info(f'   self._path:{self._path}')

        self.loadAnalysis()

    def peakDetectAllRoi(self):
        logger.info('=== detecting peaks for all roi')
        for roiLabel, kymRoiAnalysis in self._roiDict.items():
            logger.info(f'   -->> roiLabel:{roiLabel}')
            kymRoiAnalysis.peakDetect()

    @property
    def path(self):
        return self._path
    
    @property
    def imgData(self):
        return self._imgData
    
    @property
    def header(self):
        return self._headerDict

    @property
    def umPerPixel(self):
        return self.header['umPerPixel']
    
    @property
    def secondsPerLine(self):
        return self.header['secondsPerLine']
    
    @property
    def numRoi(self):
        return len(self._roiDict.keys())

    def getRoiLabels(self) -> List[str]:
        return list(self._roiDict.keys())

    def _getNextRoiLabel(self) -> str:
        if self.numRoi == 0:
            return '1'
        else:
            # return str(self.numRoi + 1)
            # logger.info(self._roiDict.keys())
            nextLabel = list(self._roiDict.keys())[self.numRoi - 1]
            nextLabel = int(nextLabel)
            nextLabel += 1
            return str(nextLabel)
        
    def addROI(self,
               ltrbRect : List[int] = None,
               kymRoiDetection : KymRoiDetection = KymRoiDetection(),
               doAnalysis : bool = False
               ) -> KymRoi:
        """
        Parameters
        ----------
        ltrb : [l, t, r, b]
        kymRoiDetection : KymRoiDetection
        """
        roiLabel = self._getNextRoiLabel()
        logger.info(f'adding new roi label {roiLabel}')
        newRoi = KymRoi(roiLabel,
                        self,  # parent used to just set _isDirty
                        self.imgData,
                        header=self.header,
                        ltrbRect=ltrbRect,
                        kymRoiDetection=kymRoiDetection,
                        doAnalysis=doAnalysis,
                        )
        self._roiDict[roiLabel] = newRoi
        self._isDirty = True

        return newRoi
    
    def deleteRoi(self, roiLabel) -> bool:
        roi = self._roiDict.pop(roiLabel, None)
        
        self._isDirty = True
        
        logger.info(f'deleted roi:{roi}')
        
        return roi
    
    def getRoi(self, roiLabel):
        return self._roiDict[roiLabel]

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

    def getDataFrame(self, roiLabel = None):
        """Get results df for one roi or all roi (use roi=None).
        """
        if roiLabel is not None:
            return self._roiDict[roiLabel].analysisResults.df
        else:
            columns = list(KymRoiResults.analysisDict.keys())
            df = pd.DataFrame(columns=columns)  # empty df with proper columns
            for _roiIdx, roi in enumerate(self._roiDict.values()):
                # logger.info(f'oneDf:{oneDf}')
                oneDf = roi.analysisResults.df
                if _roiIdx == 0:
                    df = oneDf
                else:
                    df = pd.concat([df, oneDf], axis=0)
            try:
                df = df.reset_index(drop=True)
            except (ValueError) as e:
                logger.error(e)
                # logger.error('df is:')
                # print(df)

            return df
        
    def saveAnalysisResults(self):
        """Save all roi time and intensity in one dataframe (csv).
        """
        peakPath, intPath = self._getSaveFile()

        df = pd.DataFrame()

        # get the largest number of rows from all roi (e.g. right-left rect roi)
        maxNumRows = 0
        for roiLabel, kymRoi in self._roiDict.items():
            resultDict = kymRoi.getAnalysisTraces()
            _firstTrace = list(resultDict.keys())[0]
            
            # logger.info(f'_firstTrace:{_firstTrace}')
            # logger.info(resultDict[_firstTrace])
            
            rows = resultDict[_firstTrace].shape[0]
            if rows > maxNumRows:
                maxNumRows = rows

        for roiLabel, roi in self._roiDict.items():

            # timeCol = f'ROI{roiLabel}_time'
            # intCol = f'ROI{roiLabel}_int'

            # TODO: save all these
            # self._analysisTraces['xPlot'] = xPlot
            # self._analysisTraces['yRaw'] = yRaw  # raw sum intensity
            # self._analysisTraces['yDetrend'] = yDetrend # after detrend with single exponential
            # self._analysisTraces['yPlot'] = yDf_f0

            resultDict = roi.getAnalysisTraces()
            for traceKey,traceValues in resultDict.items():
                colName = f'ROI{roiLabel}_{traceKey}'
                df[colName] = [np.nan] * maxNumRows
                df.loc[0:traceValues.shape[0]-1, colName] = traceValues

            # xPlot = resultDict['xPlot']
            # yPlot = resultDict['yPlot']

            # df[timeCol] = [np.nan] * maxNumRows
            # df[intCol] = [np.nan] * maxNumRows
            
            # df.loc[0:xPlot.shape[0]-1, timeCol] = xPlot
            # df.loc[0:yPlot.shape[0]-1, intCol] = yPlot

        logger.info(f'saving intensity to: {intPath}')
        df.to_csv(intPath, index=False)

    def saveAnalysis(self):
        """Save all peak analysis into one csv file.

        This includes a header with roi [l,t,r,b] and detection parameters used.
        """

        # one line header with all rois name=[l,t,r,b]
        
        # TODO: we also need to save the detection parameters for each roi
        
        logger.info(f'self._isDirty:{self._isDirty} {type(self._isDirty)}')
        if not self._isDirty:
            _noSaveStr = 'No changes to save.'
            logger.info(_noSaveStr)
            # self.mySetStatusbar(_noSaveStr)
            return False
        
        _fileHeaderDict = {}

        # add backgroundRoi
        # _fileHeaderDict['backgroundRoi'] = self._backgroundRoi._roiAsRect()

        for roiLabel, roi in self._roiDict.items():
            # what was used for detection, including [l,t,r,b] of rect roi
            
            # logger.info(f'roiLabel:{roiLabel} detection is: {roi.detectionParams.getValueDict()}')

            _fileHeaderDict[roiLabel] = roi.detectionParams.getValueDict()  # just key value pairs for detection parameters

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

        return True

    def loadAnalysis(self):
        """
        """
        savePath, intPath = self._getSaveFile(createFolder=False)
        if not os.path.isfile(savePath):
            logger.info(f'did not find file to load:{savePath}')
            return

        # current version of analysis, mostly changes when modifying columns in kymRoiResults
        _currentVersion = getAnalysisDict()['version']['defaultvalue']

        logger.info(f'=== loading analysis from: {savePath}')

        self._isDirty = False  # do this first, we re-analyze based on roi verion (making self dirty)

        with open(savePath) as f:
            headerJson = f.readline()
            _headerDict = json.loads(headerJson)

        dfLoadedFromFile = pd.read_csv(savePath, header=1)
        
        loadedIntDf = pd.read_csv(intPath)

        # _headerDict is a dict with roi name keys, make a number of rois
        # self._detectionDict = _headerDict
        _firstRoi = None
        for _roiIndex, (roiNumber,detectionDict) in enumerate(_headerDict.items()):
            # roiNumber is str like '1', '2', '3',...
            logger.info(f'{roiNumber}: {detectionDict}')
            
            # if roiNumber == 'backgroundRoi':
            #     logger.warning(f'TODO: assign background roi to detectionDict:{detectionDict}')
            #     ltrb = detectionDict['ltrb']
            #     self._backgroundRoi.setPosSize(ltrb)
            #     continue

            kymRoiDetection = KymRoiDetection(fromDict=detectionDict)

            # add the roi
            kymRoi = self.addROI(kymRoiDetection['ltrb'],
                              kymRoiDetection=kymRoiDetection)

            # set xPlot and yPlot from int file
            # ROI1_time,ROI1_int
            roiTraceList = kymRoi._analysisTraceList
            for roiTrace in roiTraceList:
                colName = f'ROI{roiNumber}_{roiTrace}'
                
                if colName not in loadedIntDf.columns:
                    logger.error(f'   did not find trace name "{roiTrace}" column in file {intPath}')
                    continue
                oneTrace = loadedIntDf[colName]
                oneTrace = oneTrace[~np.isnan(oneTrace)]
                
                kymRoi._analysisTraces[roiTrace] = oneTrace

            #
            # fill in analysis results
            oneRoiResults = KymRoiResults()
            dfRoi = dfLoadedFromFile[ dfLoadedFromFile['ROI Number']==int(roiNumber) ]
            dfRoi = dfRoi.reset_index(drop=True)  # Do not try to insert index into dataframe columns.
            oneRoiResults._swapInNewDf(dfRoi)
            kymRoi._kymRoiResults = oneRoiResults

            try:
                loadedVersion = detectionDict['version']
            except (KeyError):
                # oldest verion does not have 'version' key
                loadedVersion = 0
            if loadedVersion < _currentVersion:
                logger.info(f'    -->> re-analyze !!! loadedVersion:{loadedVersion} < _currentVersion:{_currentVersion}')
                kymRoi.peakDetect()

        # self._isDirty = False  # do at start in case we re-analyze

    def getParamDataFrame(self) -> pd.DataFrame:
        """Get a dataframe of all detection params.
        
        One row per roi.
        """
        dictList = []
        for roiLabel, roi in self._roiDict.items():
            dictList.append(roi.detectionParams.getValueDict())
        df = pd.DataFrame.from_dict(dictList) 
        return df

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

def findThreshold(kymRoi : KymRoi, newOnsetOffsetFraction : float = 0.1, doMpl = False):
    """Refine all peak parameters.
        - Rise 10
        - [depreciated] Rise 90
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

    thisTrace = kymRoi.detectionParams['detectThisTrace']
    int_df_f0 = kymRoi._analysisTraces[thisTrace]  # in (int_f_f0, int_df_f0)
    # medianfilterkernel = 3
    # int_df_f0 = medfilt(int_df_f0, kernel_size=medianfilterkernel)

    peakBins = kymRoi.analysisResults.getValues('Peak Bin')
    peakValues = kymRoi.analysisResults.getValues('Peak Int')  # y-value at peak
    peakHeights = kymRoi.analysisResults.getValues('Peak Height')  # peak - threshold value

    numPeaks = len(peakBins)
    
    # returns
    onsetBinList = [np.nan] * numPeaks
    offsetBinList = [np.nan] * numPeaks
    onset10BinList = [np.nan] * numPeaks
    offset10BinList = [np.nan] * numPeaks
    newPeakHeightList = [np.nan] * numPeaks

    peaksErrors = [''] * numPeaks

    for _idx, peakBin in enumerate(peakBins):
        
        # peakBin -= _left

        yPeak = peakValues[_idx]
        peakHeight = peakHeights[_idx]

        # logger.info(f'_idx:{_idx} peakBin:{peakBin} yPeak:{yPeak} peakHeight:{peakHeight} newOnsetOffsetFraction:{newOnsetOffsetFraction}')

        #
        # new rise and decay
        threshold =  yPeak - (peakHeight * newOnsetOffsetFraction)  # 0.9 is 90% height
        # logger.info(f'  threshold 10:{threshold}')

        # threshold_crossings = np.diff(int_df_f0 > threshold, prepend=False)
        threshold_crossings = np.diff(int_df_f0 > threshold, append=False)  # "False" is the value to append
        thresholdBins = np.where(threshold_crossings[0:peakBin]==1)[0]
        thresholdBin = thresholdBins[-1]  # first threshold before peak
        # back it up by one bin ??? When onset is fast, actual threshold crossing is way too high
        # this is achieved with apend=False
        # thresholdBin = thresholdBin - 1
        onsetBinList[_idx] = thresholdBin

        threshold_crossings = np.diff(int_df_f0 > threshold, prepend=False)  # "False" is the value to append
        decayBins = np.where(threshold_crossings[peakBin:-1]==1)[0]
        decayBin = decayBins[0]  # first threshold after peak
        decayBin += peakBin
        offsetBinList[_idx] = decayBin

        # we have a new peak height
        peakHeight2 = yPeak - int_df_f0[thresholdBin]
        newPeakHeightList[_idx] = peakHeight2

        # 10% in rise
        threshold2 =  yPeak - (peakHeight2 * 0.9)  # 0.9 is 90% height, eg rise 10

        # threshold_crossings2 = np.diff(int_df_f0 > threshold2, append=False)  # "False" is the value to append
        threshold_crossings2 = np.diff(int_df_f0 > threshold2, prepend=False)  # "False" is the value to append
        threshold10Bins = np.where(threshold_crossings2[0:peakBin]==1)[0]
        threshold10Bin = threshold10Bins[-1]  # first threshold before peak
        onset10BinList[_idx] = threshold10Bin

        # decay has different height
        peakHeight3 = yPeak - int_df_f0[decayBin]
        threshold3 =  yPeak - (peakHeight3 * 0.9)  # 0.9 is 90% height
        # using append=False to backup bin by one
        threshold_crossings3 = np.diff(int_df_f0 > threshold3, append=False)  # "False" is the value to append
        decay10Bins = np.where(threshold_crossings3[peakBin:-1]==1)[0]
        decay10Bin = decay10Bins[0]  # first threshold after peak
        decay10Bin += peakBin
        offset10BinList[_idx] = decay10Bin

        if doMpl:
            # make a new figure each time. I do not understand matplotlib !!!
            fig, axs = plt.subplots(1, 1, figsize=(18,10))
            axs = [axs]

            # raw int
            axs[0].plot(int_df_f0, color='k', marker='', label='int')
            axs[0].set_xlim([peakBin-75, peakBin+75])

            # peak
            axs[0].plot(peakBin, int_df_f0[peakBin], color='c', marker='^', label='peak')

            #
            axs[0].axhline(y=threshold)

            # new threshold
            plt.plot(thresholdBin, int_df_f0[thresholdBin], color='c', marker='o', markersize=10, label='thresholdBin')

            # old threshold
            # plt.plot(thresholdBin_orig, int_df_f0[thresholdBin_orig], color='y', marker='s', markersize=10, label='thresholdBin_orig')
            # plt.plot(decayBin_orig, int_df_f0[decayBin_orig], color='y', marker='s', markersize=10, label='decayBin_orig')

            # decay
            plt.plot(decayBin, int_df_f0[decayBin], color='m', marker='o', markersize=10, label='decayBin')

            # threshold crossings
            axs[0].plot(threshold_crossings, color='r', marker='o', label='threshold_crossings')
            
            axs[0].legend()
            plt.show()

    return onsetBinList, offsetBinList, onset10BinList, offset10BinList, newPeakHeightList

def plotDetectionResults(kymRoi : KymRoi):
    """Plot steps in analysis.
        - Raw sum
        - Detrended sum
        - df/d0
    
    Parameters
    ----------
    kymRoi : KymROi
        Results for one ROI
    """
    imgData = kymRoi.getRoiImg()

    timeSec = kymRoi._analysisTraces['timeSec']  # seconds
    intRaw = kymRoi._analysisTraces['intRaw']
    intDetrend = kymRoi._analysisTraces['intDetrend']
    # int_df_f0 = kymRoi._analysisTraces['int_df_f0']  # yDf_f0
    logger.warning('swapping my df_d0 for santana f_f0')
    int_df_f0 = kymRoi._analysisTraces['int_f_f0']  # yDf_f0

    peakSecond = kymRoi.analysisResults.getValues('Peak Second')
    peakValue = kymRoi.analysisResults.getValues('Peak Int')

    #
    fig, axs = plt.subplots(4, 1, figsize=(6,6), sharex=True)

    roiLabel = kymRoi.getLabel()
    _backgroundsubtract = f"Background subtract: {kymRoi.detectionParams['backgroundsubtract']}"
    _title = f'{os.path.split(kymRoi.path)[1]}, ROI {roiLabel}, {_backgroundsubtract}'
    fig.suptitle( _title )

    # image
    left, top, right, bottom = kymRoi.getRect()
    # logger.info(f'timeSec:{timeSec} {type(timeSec)}')
    try:
        leftSec = timeSec.values[0]
        rightSec = timeSec.values[-1]
    except (AttributeError) as e:
        logger.error(f'sometimes timeSec is pandas, sometimes numpy ???: {e}')
        leftSec = timeSec[0]
        rightSec = timeSec[-1]
    _extent=[leftSec, rightSec, bottom, top]
    logger.info(f'_extent:{_extent}')
    # _label = f"Background subtract: {kymRoi.detectionParams['backgroundsubtract']}"
    imgplot = axs[0].imshow(imgData, extent=_extent, aspect="auto")
    imgplot.set_cmap('nipy_spectral')
    # axs[0].legend(loc='upper right')  # legend does not work with imshow()

    # raw sum with fit
    axs[1].plot(timeSec, intRaw, 'r', label=f"Sum (bins={kymRoi.detectionParams['binLineScans']})")
    axs[1].set_ylabel('Intensity (per pixel)')
    # add exp fit
    fitDict = kymRoi.detectionParams['expDetrendFit']
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
        axs[1].plot(timeSec, yFit, 'k', label=_label)
        axs[1].legend()

    # after remove fit (if on) and selecting f0
    axs[2].plot(timeSec, intDetrend, 'c', label='Detrend')
    axs[2].set_ylabel('Subtract exp')
    # add f0
    _f0 = kymRoi.detectionParams['f0Value']
    _label = f"f0 = {round(_f0,2)}"
    axs[2].axhline(y=_f0, label=_label)
    axs[2].legend()

    # final dF/F0
    axs[3].plot(timeSec, int_df_f0, 'k', label='int/f0')
    axs[3].set_ylabel('int_f_f0')
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
    _peakBins = kymRoi.analysisResults.getValues('Peak Bin')

    xDecay = []
    yDecay = []
    for _peakIdx, _peakBin in enumerate(_peakBins):
        
        _peakBin = _peakBin - _left
        
        fit_m = kymRoi.analysisResults.getValues('fit_m')[_peakIdx]            
        fit_tau = kymRoi.analysisResults.getValues('fit_tau')[_peakIdx]
        fit_b = kymRoi.analysisResults.getValues('fit_b')[_peakIdx]

        if np.isnan(fit_m):
            # logger.warning(f'no fit for peak {_peakIdx}')
            continue

        # ms to bin
        _decayMs = kymRoi.detectionParams['decay (ms)']
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
    axs[3].plot(xDecay, yDecay, 'r')  # single exp fit to decay

    #
    # (2) double exp decay
    xDecay2 = []
    yDecay2 = []
    for _peakIdx, _peakBin in enumerate(_peakBins):
        
        # fix this constant bug !!!!
        _peakBin = _peakBin - _left
        
        fit_m1 = kymRoi.analysisResults.getValues('fit_m1')[_peakIdx]            
        fit_tau1 = kymRoi.analysisResults.getValues('fit_tau1')[_peakIdx]
        fit_m2 = kymRoi.analysisResults.getValues('fit_m2')[_peakIdx]            
        fit_tau2 = kymRoi.analysisResults.getValues('fit_tau2')[_peakIdx]

        if np.isnan(fit_m1):
            # logger.warning(f'no dbl exp fit for peak {_peakIdx}')
            continue

        # ms to bin
        _decayMs = kymRoi.detectionParams['decay (ms)']
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
    axs[3].plot(xDecay2, yDecay2, 'c')  # double exp fit to decay

    plt.show()

def _testDetectionParams():
    """Step through a number of detection params and compare the results.
    """
    # logger.setLevel(level='DEBUG')

    doMpl = False

    # path = '/Users/cudmore/Dropbox/data/colin/sanAtp/ISAN Linescan 3.tif'
    
    # working
    path = '/Users/cudmore/Dropbox/data/colin/sanAtp/ISAN Linescan 3.tif'
    _roiRect = [150, 954, 999, 852]

    # works
    # negative peaks
    # path = '/Users/cudmore/Dropbox/data/colin/sanAtp/SSAN Linescan 8.tif'

    kra = KymRoiAnalysis(path=path)

    kymRoiDetection = KymRoiDetection()
    kymRoiDetection['prominence'] = 1.5
    kymRoiDetection['binLineScans'] = 0

    # # 1
    # oneRoi = kra.addROI(_roiRect, kymRoiDetection=kymRoiDetection)
    # oneRoi.detectionParams['backgroundsubtract'] = "Off"
    # oneRoi.peakDetect()

    # # 2
    # oneRoi = kra.addROI(_roiRect, kymRoiDetection=kymRoiDetection)
    # oneRoi.detectionParams['backgroundsubtract'] = "Rolling-Ball"
    # oneRoi.peakDetect()

    # # 3
    # oneRoi = kra.addROI(_roiRect, kymRoiDetection=kymRoiDetection)
    # oneRoi.detectionParams['backgroundsubtract'] = "Median"
    # oneRoi.peakDetect()

    # # 4
    # oneRoi = kra.addROI(_roiRect, kymRoiDetection=kymRoiDetection)
    # oneRoi.detectionParams['backgroundsubtract'] = "Mean"
    # oneRoi.peakDetect()

    binLineScanList = [0, 1, 2, 3, 5, 10]
    # _roiRect = None
    for bin in binLineScanList:
        oneRoi = kra.addROI(ltrbRect=_roiRect, kymRoiDetection=kymRoiDetection, doAnalysis=False)
        oneRoi.detectionParams['backgroundsubtract'] = "Median"
        oneRoi.detectionParams['binLineScans'] = bin
        oneRoi.detectionParams['prominence'] = 1
        # oneRoi.detectionParams['polarity'] = 'Neg'
        oneRoi.peakDetect()
        
        # use matplotlib to plot results for one roi
        plotDetectionResults(oneRoi)
        # break

    # save results and open in widget
    # kra.saveAnalysis()

    print(kra.getParamDataFrame())

def _testThreshold():
    # working
    path = '/Users/cudmore/Desktop/retreat-sept-2024/ISAN Linescan 1.tif'
    # path = '/Users/cudmore/Desktop/retreat-sept-2024/ISAN Linescan 9.tif'  # 3 roi
    # path = '/Users/cudmore/Desktop/retreat-sept-2024/ISAN Linescan 10.tif'  # 3 roi
    # path = '/Users/cudmore/Desktop/retreat-sept-2024/SSAN Linescan 1.tif'  # 1 roi

    kra = KymRoiAnalysis(path)
    logger.info(f'numRoi:{kra.numRoi}')
    # oneRoi = kra.getRoi("1")
    oneRoi = kra.getRoi("2")
    # oneRoi = kra.getRoi("3")
    findThreshold(oneRoi)

def _testLoad():
    """After saving in _testDetectionParams() try and load.
    """
    path = '/Users/cudmore/Dropbox/data/colin/sanAtp/ISAN Linescan 3.tif'
    kra = KymRoiAnalysis(path=path)

    kra.loadAnalysis()

    for label in kra.getRoiLabels():
        roi = kra.getRoi(label)
        plotDetectionResults(roi)

    logger.info(f'   num roi: {kra.numRoi}')

if __name__ == '__main__':
    # _testDetectionParams()

    # _testLoad()

    _testThreshold()