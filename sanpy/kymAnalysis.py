"""Backend kymograph analysis to be used with the kymographWidget

Perform all kymograph analysis here including:
    - Sum of each line scan
    - Diameter of each line scan
    - Detect peaks in diameter

This will replace code on bAnalysis (abfText)

For analysis of each raw tif file, we save a csv (text) file.
Each row is measurements for one line scan. Columns are as follows.

time_bin
    Time of the line scan (points)
time_sec
    Time of the line scan (s)
sumintensity_raw
    Raw sum intensity of the line scan
sumintensity_filt
    Sum intensity after median filter
sumintensity
    Sum intensity normalized to maximum (range is 0 to 1)
diameter_pnts
    Diameter estimate for the line scan (points)
diameter_um
    Diameter estimate for the line scan (um)
diameter_um_filt
    Diameter estimate for the line scan (um)
left_pnt
    Position of left (earlier) for fit (point)
right_pnt
    Position of right (later) for fit (point)

"""

import os
import math
import time

from multiprocessing import Pool

from typing import List, Union, Optional

import numpy as np
import pandas as pd
from skimage.measure import profile
import scipy.signal
import scipy
import tifffile

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class kymRect:
    """Class to represent a rectangle as [l, t, r, b]"""

    def __init__(self, l, t, r, b):
        self._l = l
        self._t = t
        self._r = r
        self._b = b

    def setTop(self, t):
        self._t = t

    def setBottom(self, b):
        self._b = b

    def getWidth(self):
        return self._r - self._l

    def getHeight(self):
        return self._t - self._b

    def getLeft(self):
        return self._l

    def getTop(self):
        return self._t

    def getRight(self):
        return self._r

    def getBottom(self):
        return self._b

    def getMatPlotLibExtent(self):
        """Get matplotlib extend for imshow in (l,r,b,t)"""
        return (self._l, self._r, self._b, self._t)

    def getPosAndSize(self):
        """For PyQtGraph rect ROI.
        """
        left = self.getLeft()  # kymographRect[0]
        bottom = self.getBottom()  # kymographRect[3]
        top = self.getTop()  # kymographRect[1]
        right = self.getRight()  # kymographRect[2]
        widthRoi = right - left
        # heightRoi = bottom - yRoiPos + 1
        heightRoi = top - bottom

        pos = (left, bottom)
        size = (widthRoi, heightRoi)

        return pos, size
    
    def __str__(self):
        return f"l:{self._l} t:{self._t} r:{self._r} b:{self._b}"


class kymAnalysis:
    def getDefaultAnalysisParams() -> dict:
        return {
            'version': '0.0.4',
            
            'reduceFraction': 0,    #0.05,
                                    # percentage to reduce t/b of full rect roi to make best guess
                                    # not used in analysis
                                    # used to set initial rect roi

            'lineWidth': 1,  # number of lines to analyze for each 'line' (slow)

            'imageFilterKenel': 5,
            'lineFilterKernel': 5,

            'lineWidth': 1,  # Number of lines scans to use in calculating line profile

            'detectPosNeg': 'pos',  # for each line, detect positive or negative intensity
            'percentOfMax': 0.3,  # Percent of max to use in calculation of diameter

            # all fields need a default so we can infer the type() when loading from json
            
            # used to save/load
            'lRoi': 0,
            'tRoi': 0,
            'rRoi': 0,
            'bRoi': 0,

            # used to save/load
            'umPerPixel': 0.1,
            'secondsPerLine': 0.001,
            'bitDepth': 8,
            'dtype': np.uint8,
            
        }
    
    def __init__(self,
                 path : str,
                 tifData : np.ndarray = None,
                 tifHeader : dict = None,
                 autoLoad: bool = True):
        """

        Parameters
        ----------
            path : str
                full path to .tif file
            tifData : np.ndarray
                if None then load from path, o.w. use tifData
            tifHeader : dict
                To specify (umPerPixel, secondsPerLine, bitDepth)
            autoLoad : bool
                auto load analysis
        """

        self._path = path
        # path to tif file

        # (line scan, pixels)
        if tifData is not None:
            self._kymImage = tifData
        else:
            # load
            self._kymImage: np.ndarray = tifffile.imread(path)

        self._kymImageFiltered = None
        # create this as needed, see self._kymImageFilterKernel

        _size = len(self._kymImage.shape)
        if _size < 2 or _size > 3:
            # TODO: raise custom exception
            logger.error(f"image must be 2d but is {self._kymImage.shape}")

        # image must be shape[0] is time/big, shape[1] is space/small
        if self._kymImage.shape[0] < self._kymImage.shape[1]:
            # logger.info(f"rot90 image with shape: {self._kymImage.shape}")
            self._kymImage = np.rot90(
                self._kymImage, 3
            )  # ROSIE, so lines are not backward

        # this is what we extract line profiles from
        # we create filtered version at start of detect()
        self._filteredImage: np.ndarray = self._kymImage

        # logger.info(f"final image shape is: {self._kymImage.shape}")

        # load the header from Olympus exported .txt file

        # TODO: put this in tif fileLoader
        if tifHeader is None:
            if self._kymImage.dtype == np.uint8:
                _bitDepth = 8
            elif self._kymImage.dtype == np.uint16:
                _bitDepth = 16
            else:
                logger.warning(f'Did not undertand dtype {self._tif.dtype} defaulting to bit depth 16')
                _bitDepth = 16
            self._header = {
                'umPerPixel': 1,
                'secondsPerLine': 0.005,  # 0.001  #0.001  # make ms per bin = 1
                'bitDepth': _bitDepth,
            }
        else:
            self._header = tifHeader

        self._analysisParams = kymAnalysis.getDefaultAnalysisParams()

        # self._reduceFraction = 0.2
        # percentage to reduce t/b of full rect roi to make best guess

        self._roiRect : kymRect = self.getBestGuessRectRoi()
        # rectangular roi [l, t, r, b']

        # If >1 will get 10x-100x slower
        # TODO: write multiprocessing code

        # self._percentOfMax = 0.5
        # to find start/stop of diameter fit along one line profile

        # self._kymImageFilterKernel = 0
        # on analysis, pre-filter image with median kernel

        # self._lineFilterKernel = 0
        # on analysis, pre-filter each line with median kernel

        # analysis results
        # _numLineScans = self.numLineScans()
        self._diamResults = self.getDefaultResultsDict()
        self._diamAnalyzed = False
        self._analysisDirty = False

        # load saved analysis if it exists
        if autoLoad:
            self.loadAnalysis()

    def hasDiamAnalysis(self):
        return self._diamAnalyzed

    def getAnalysisParam(self, name):
        return self._analysisParams[name]
    
    def setAnalysisParam(self, name, value):
        self._analysisParams[name] = value

    @property
    def umPerPixel(self):
        return self._header['umPerPixel']
    
    @property
    def secondsPerLine(self):
        return self._header['secondsPerLine']
    
    def getDefaultResultsDict(self):
        _numLineScans = self.numLineScans()
        theDict = {
            "time_bin": [np.nan] * _numLineScans,
            "time_sec": [np.nan] * _numLineScans,
            "sumintensity_raw": [np.nan] * _numLineScans,  # raw sum of each line scan
            "sumintensity_filt": [np.nan] * _numLineScans,  # raw sum of each line scan
            "sumintensity": [np.nan] * _numLineScans,  # normalized to max
            "diameter_pnts": [np.nan] * _numLineScans,
            "diameter_um": [np.nan] * _numLineScans,
            "diameter_um_filt": [np.nan] * _numLineScans,
            "left_pnt": [np.nan] * _numLineScans,
            "right_pnt": [np.nan] * _numLineScans,
            # each line has intensity (min, max, range)
            "minInt": [np.nan] * _numLineScans,
            "maxInt": [np.nan] * _numLineScans,
            "rangeInt": [np.nan] * _numLineScans,
        }
        return theDict

    def getReport(self):
        """Get a dict of all parameters and results.

        This can be appended to a pandas dataframe.
        """
        folder, fileName = os.path.split(self._path)
        folder, _tmp = os.path.split(folder)  # _tmp is Olympus export folder
        folder, folderName = os.path.split(folder)
        _tmp, grandParentFolder = os.path.split(folder)

        """
        numLines: Number of line scans in kymograph
        numPixels: Number of pixels in each line scan
        secondsPerLine: The duration (sec) of each line scan
        umPerPixel: The um per pixel along the line scan
        dur_sec: Total duration of kymograph (sec)
        dist_um: The um length of each line scan

        # analysis 
        tifMin: Minimum intensity of the tif
        tifMax: Maximum intensity of the tif
        
        # diameter analysis
        minDiam: Minimum diameter (among all line scans)
        maxDiam: Maximum diameter (among all line scans)
        diamChange: (maxDIam-minDiam) to quickly find kymographs that have a large change in diameter.
        
        # sum along the entire line scan (to find cell wide Ca2+ spikes)
        minSum: The minimum (sum all pixels in line scan / numPixels)
        maxSum: The maximum ...
        sumChange: (maxSum-minSUm) to quickly find kymographs that have a large change in diameter
        """
        theDict = {
            "folder": folderName,
            "grandParentFolder": grandParentFolder,
            "file": fileName,
            "numLines": self.numLineScans(),
            "numPixels": self.numPixels(),
            "secondsPerLine": self.secondsPerLine,
            "umPerPixel": self.umPerPixel,
            "dur_sec": self.numLineScans() * self.secondsPerLine,
            "dist_um": self.numPixels() * self.umPerPixel,
            "tifMin": np.nanmin(self._kymImage),  # TODO: make this for ROI rect
            "tifMax": np.nanmax(self._kymImage),
            #
            "minDiam": self._diamResults["minDiam"],
            "maxDiam": self._diamResults["maxDiam"],
            "diamChange": self._diamResults["diamChange"],
            #
            "minSum": self._diamResults["minSum"],
            "maxSum": self._diamResults["maxSum"],
            "sumChange": self._diamResults["sumChange"],
        }
        return theDict

    def pnt2um(self, point):
        return point * self.umPerPixel

    def getResults(self, key) -> list:
        """Get analysis result.
        
        Parameters
        ----------
        key : str
            Key in results dictionary
        """
        try:
            ret = self._diamResults[key]
            return ret
        except (KeyError) as e:
            logger.error(f'Did not find results key "{key}"')
            logger.error(f'Available keys are {self._diamResults.keys()}')

    def getResultsAsDataFrame(self):
        df = pd.DataFrame(self._diamResults)
        return df
    
    @property
    def sweepX(self):
        """Get full time array across all line scans

        Time is in sec. Same as bAnalysis.sweepX
        """

        ret = np.arange(0, self.numLineScans(), 1)
        ret = np.multiply(ret, self.secondsPerLine)

        return ret

    def getImageRect_no_scale(self, asList=False):
        l = 0
        t = self.pointsPerLineScan() # * self.umPerPixel
        t = math.floor(t)

        r = self.numLineScans() # * self.secondsPerLine
        r = math.floor(r)
        
        b = 0

        w = r - l
        h = t - b

        if asList:
            return [l, b, w, h]  # x, y, w, h
        else:
            return kymRect(l, t, r, b)
    
    def getImageRect(self, asList=False):
        """Get image rect with (x,y) scale.
        
        Notes
        -----
        This breaks when umPerPixel is fractional.
            Trying to fix by returning float.
        """
        l = 0
        t = self.pointsPerLineScan() * self.umPerPixel
        #t = math.floor(t)

        r = self.numLineScans() * self.secondsPerLine
        #r = math.floor(r)
        
        b = 0

        w = r - l
        h = t - b

        if asList:
            return [l, b, w, h]  # x, y, w, h
        else:
            return kymRect(l, t, r, b)

    def resetKymRect(self):
        """reset to default.
        """
        self._roiRect: kymRect = self.getBestGuessRectRoi()

    def getBestGuessRectRoi(self):
        """Get a best guess of a rectangular roi.

        Info
        ----
            theRect2:[0, 383, 5000, 17]
        """

        _rect : kymRect = self.getImageRect_no_scale()  # [left, top, r, b]
        # _rect : kymRect = self.getImageRect()  # [left, top, r, b]

        # logger.info(f'  getImageRect_no_scale: {_rect}')

        reduceFraction = self.getAnalysisParam('reduceFraction')

        # logger.info(f'  reduceFraction: {reduceFraction}')

        # reduce top/bottom (space) by 0.15 percent
        percentReduction = _rect.getHeight() * reduceFraction

        newTop = _rect.getTop() - 2 * percentReduction
        newBottom = _rect.getBottom() + percentReduction
        
        newTop = math.floor(newTop)
        newBottom = math.floor(newBottom)
        
        _rect.setTop(newTop)
        _rect.setBottom(newBottom)

        # logger.info(f"  after reduction _rect:{_rect}")

        return _rect

    def getRoiRect(self, asInt=True) -> kymRect:
        """Get the current roi rectangle."""
        return self._roiRect

    def setRoiRect(self, newRect):
        """
        Args:
            newRect is [l, t, r, b]
        """
        # logger.info(newRect)

        l = newRect[0]
        t = newRect[1]
        r = newRect[2]
        b = newRect[3]

        # logger.info(f'')

        self._roiRect = kymRect(l, t, r, b)

    def getImage(self):
        return self._kymImage

    def getImageContrasted(self, theMin, theMax, rot90=False):
        bitDepth = self._header['bitDepth']
        lut = np.arange(2**bitDepth, dtype="uint8")
        lut = self._getContrastedImage(lut, theMin, theMax)  # get a copy of the image
        theRet = np.take(lut, self._kymImage)

        if rot90:
            theRet = np.rot90(theRet)

        return theRet

    def _getContrastedImage(
        self, image, display_min, display_max
    ):  # copied from Bi Rico
        # Here I set copy=True in order to ensure the original image is not
        # modified. If you don't mind modifying the original image, you can
        # set copy=False or skip this step.
        bitDepth = self._header['bitDepth']

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

    def getImageShape(self):
        return self._kymImage.shape  # (w, h)

    def numLineScans(self):
        """Number of line scans in kymograph."""
        return self.getImageShape()[0]

    def pointsPerLineScan(self):
        """Number of points in each line scan."""
        return self.getImageShape()[1]

    def _getAnalysisFolder(self):
        savePath, saveFile = os.path.split(self._path)
        analysisFolder = os.path.join(savePath, 'kymAnalysis')
        return analysisFolder
    
    def getAnalysisFile(self):
        """Get full path to analysis file we save/load."""
        savePath, saveFile = os.path.split(self._path)
        saveFileBase, ext = os.path.splitext(saveFile)
        # was this
        # saveFile = saveFileBase + "-kymanalysis.csv"
        saveFile = saveFileBase + "-kymDiameter.csv"
        #saveFile = saveFileBase + "-analysis2.csv"

        _analysisFolder = self._getAnalysisFolder()

        savePath = os.path.join(_analysisFolder, saveFile)
        return savePath

    def _getFileHeader(self):
        """Get one line header to save with analysis.
        
        This includes:
            - tif header
            - roi rect
            - detection params
        """
        
        headerStr = ""

        # insert image header into save dictionary
        for k,v in self._header.items():
            #headerStr += f'{k}={v};'
            self._analysisParams[k] = v

        # insert current roi into save dictionary
        roiRect = self.getRoiRect()
        self._analysisParams['lRoi'] = roiRect.getLeft()
        self._analysisParams['tRoi'] = roiRect.getTop()
        self._analysisParams['rRoi'] = roiRect.getRight()
        self._analysisParams['bRoi'] = roiRect.getBottom()

        for k,v in self._analysisParams.items():
            headerStr += f'{k}={v};'

        return headerStr

    def _parseFileHeader(self, savePath, header):
        """Parse one line header into an analysis parameter dictionary.

        This is parsing header we save with analysis.
        """

        kvList = header.split(";")
        for kv in kvList:
            if not kv:
                # handle trailing ';'
                continue
            
            try:
                k, v = kv.split("=")
            except (ValueError) as e:
                logger.error(f'did not parse kym file header for "{kv}"')
                continue
            
            # print('    k:', k, 'v:', v)
            
            try:
                # we need to cast to the currect type
                _type = type(self._analysisParams[k])
                self._analysisParams[k] = _type(v)
            
            except (KeyError) as e:
                logger.error(f'Did not understand key:{k} with value:{v}')
        
        # set tif header
        self._header['umPerPixel'] = self.getAnalysisParam('umPerPixel')
        self._header['secondsPerLine'] = self.getAnalysisParam('secondsPerLine')
        self._header['bitDepth'] = self.getAnalysisParam('bitDepth')

        # build the roi
        l = self.getAnalysisParam('lRoi')
        t = self.getAnalysisParam('tRoi')
        r = self.getAnalysisParam('rRoi')
        b = self.getAnalysisParam('bRoi')
        
        self.setRoiRect([l,t,r,b])

        # logger.info('Loaded _analysisParams')
        # for k,v in self._analysisParams.items():
        #     print(f'  {k}: {v}')

    def saveAnalysis(self, path: str = None, verbose=False):
        """Save kymograph analysis.

        This includes:
            - time bins
            - sum of each line scan
            - diameter calculation for each line scan
            ...
        """

        if not self.hasDiamAnalysis():
            return
        
        if path is None:
            savePath = self.getAnalysisFile()
            _analysisFolder = self._getAnalysisFolder()
            if not os.path.isdir(_analysisFolder):
                if verbose:
                    logger.info(f'making folder:{_analysisFolder}')
                os.mkdir(_analysisFolder)
        else:
            savePath = path

        header = self._getFileHeader()

        with open(savePath, "w") as f:
            f.write(header)
            f.write("\n")

        df = pd.DataFrame(self._diamResults)

        df.to_csv(savePath, mode="a")

        if verbose:
            logger.info(f"saving analysis with {len(df)} lines to file")
            logger.info(f'   {savePath}')

        self._analysisDirty = False

    def loadAnalysis(self):
        """Load <file>-kymanalysis.csv

        Look in parent folder of .tif file
        """
        savePath = self.getAnalysisFile()
        if not os.path.isfile(savePath):
            # logger.info(f"did not find file: {savePath}")
            return

        # logger.info(f"loading analysis from: {savePath}")

        with open(savePath) as f:
            headerStr = f.readline().rstrip()
        self._parseFileHeader(savePath, headerStr)  # parse header of saved analysis

        df = pd.read_csv(savePath, header=1)

        # parse df into self._diamResults dictionary
        for k in self._diamResults.keys():
            try:
                self._diamResults[k] = df[k].values
            except KeyError as e:
                logger.error(f"Did not find key {k} in loaded file columns")
        
        self._diamAnalyzed = True
        self._analysisDirty = False

    def loadPeaks(self):
        """
        Load foot/peaks from manual detection.
        """
        # self._fpAnalysis = None  # Pandas dataframe with xFoot, yFoot, xPeak, yPeak

        fpFilePath = self._path.replace(".tif", "-fpAnalysis2.csv")
        fpFileName = os.path.split(fpFilePath)[1]
        if not os.path.isfile(fpFilePath):
            logger.error(f"Did not find manual peak file:{fpFileName}")
            print("  fpFilePath:", fpFilePath)
            return

        logger.info(f"loading fpFilePath:{fpFileName}")
        print("  fpFilePath:", fpFilePath)

        _fpAnalysis = pd.read_csv(fpFilePath)

        return _fpAnalysis

    def pnt2um(self, point):
        return point * self.umPerPixel

    def seconds2pnt(self, seconds):
        return int(seconds / self.secondsPerLine)

    def um2pnt(self, um):
        return int(um / self.umPerPixel)

    def _getFitLineProfile(self, lineScanNumber : int,
                           lineFilterKernel : int = None,
                           verbose=False):
        """Get one line profile.

        - Returns points
        - Get the full line, do not look at rect roi

        Args:
            medianKernel: Use 0 for no filtering
        """

        detectPosNeg = self.getAnalysisParam('detectPosNeg')

        lineWidth = self.getAnalysisParam('lineWidth')
        percentOfMax = self.getAnalysisParam('percentOfMax')
        if lineFilterKernel is None:
            lineFilterKernel = self.getAnalysisParam('lineFilterKernel')

        # we know the scan line, determine start/stop based on roi
        roiRect = self.getRoiRect()  # (l, t, r, b) in um and seconds (float)

        src_pnt_space = roiRect.getBottom()
        dst_pnt_space = roiRect.getTop()
        # logger.info(f'src_pnt_space:{src_pnt_space} dst_pnt_space:{dst_pnt_space}')
        
        # intensityProfile will always have len() of number of pixels in line scane
        if lineWidth == 1:
            intensityProfile = self._filteredImage[lineScanNumber, :]

            # oct-7-2022
            intensityProfile = np.flip(intensityProfile)  # FLIPPED

            # intensityProfile = intensityProfile.astype(float)  # we need nan

        else:
            numPixels = self._filteredImage.shape[1]
            
            # FLIPPED
            # -1 because profile_line uses last pnt (unlike numpy)
            src = (lineScanNumber, numPixels - 1)
            dst = (lineScanNumber,0)  

            intensityProfile = profile.profile_line(
                self._filteredImage, src, dst, linewidth=lineWidth
            )

        # median filter line profile
        if lineFilterKernel > 0:
            intensityProfile = scipy.signal.medfilt(intensityProfile, lineFilterKernel)

        x = np.arange(0, len(intensityProfile) + 1)

        # Nan out before/after roi
        intensityProfile = intensityProfile.astype(float)  # we need nan
        intensityProfile[0:src_pnt_space] = np.nan
        intensityProfile[dst_pnt_space:] = np.nan

        # fwhm, left_idx, right_idx = self.FWHM(x, intensityProfile)
        
        # detect either a pos (max) or neg (min) intensity along the line
        _doMax = detectPosNeg == 'pos'

        # 1) FWHM
        if _doMax:
            _intMax = np.nanmax(intensityProfile)
            half_max = _intMax * percentOfMax  # 0.2
            # half_max = _intMax + (_intMax * _percentOfMax)  # 0.2
        else:
            _intMax = np.nanmin(intensityProfile)
            half_max = _intMax + (_intMax * percentOfMax)  # 0.2

        # 2) STD
        stdMult = percentOfMax
        _intMean = np.nanmean(intensityProfile)
        _intStd = np.nanstd(intensityProfile)
        if _doMax:
            half_max = _intMean + (stdMult * _intStd)
        else:
            half_max = _intMean - (stdMult * _intStd)

        # 3) determine pos/neg by comparing first/middle/last
        if 1:
            _linesInEpoch = 10  # must be even
            _halfLinesInEpoch = _linesInEpoch  # int(_linesInEpoch * 2 / 2)  # twice as many point in the middle
            _middle_pnt_space = src_pnt_space + int( (dst_pnt_space - src_pnt_space) / 2 )
            _firstEpoch = intensityProfile[src_pnt_space:src_pnt_space+_linesInEpoch]
            _middleEpoch = intensityProfile[_middle_pnt_space-_halfLinesInEpoch:_middle_pnt_space+_halfLinesInEpoch]
            _lastEpoch = intensityProfile[dst_pnt_space-_linesInEpoch:dst_pnt_space]

            _firstEpochMean = np.nanmean(_firstEpoch)
            _middleEpochMean = np.nanmean(_middleEpoch)
            _lastEpochMean = np.nanmean(_lastEpoch)
            
            _minFirstLast = min(_firstEpochMean, _lastEpochMean)  # really need min and/or max

            # choose to search for pos/neg
            # if _minFirstLast < _middleEpochMean:
            #     _doMax = True
            # else:
            #     _doMax = False

        if verbose:
            logger.info('')
            logger.info(f'  percentOfMax:{percentOfMax}')
            logger.info(f'  detectPosNeg:{detectPosNeg} _doMax:{_doMax}')
            logger.info(f'  _intMean:{_intMean} _intStd:{_intStd}')
            logger.info(f'  _intMax:{_intMax} half_max:{half_max}')
            logger.info(f'  _firstEpochMean:{_firstEpochMean} _middleEpochMean:{_middleEpochMean} _lastEpochMean:{_lastEpochMean}')

        if _doMax:
            whr = np.asarray(intensityProfile > half_max).nonzero()
        else:
            whr = np.asarray(intensityProfile < half_max).nonzero()

        if len(whr[0]) > 2:
            # whr is (array,), only interested in whr[0]
            left_idx = whr[0][0]
            right_idx = whr[0][-1]
            # fwhm = X[right_idx] - X[left_idx]
        else:
            left_idx = np.nan
            right_idx = np.nan
            # fwhm = np.nan

        """
        if lineScanNumber < 5:
            logger.info(f'  line:{lineScanNumber} src_pnt_space:{src_pnt_space} dst_pnt_space:{dst_pnt_space}')
            logger.info(f'    intensityProfile:{len(intensityProfile)}')
            logger.info(f'    left_idx:{left_idx}')
            logger.info(f'    right_idx:{right_idx}')
            logger.info(f'    _intMax:{_intMax}')
            logger.info(f'    half_max:{half_max}')

            # import matplotlib.pyplot as plt
            # plt.plot(intensityProfile)
            # plt.show()
        """

        return intensityProfile, left_idx, right_idx

    def analyzeDiameter(self, verbose=False):
        """Analyze the diameter of each line scan.

        Args:
            imageMedianKernel: filter the raw tif with this median kernel
                            If None then use self._kymImageFilterKernel
                            If not None then set self._kymImageFilterKernel
            lineMedianKernel: filter the each line of the raw tif with this median kernel
                            If None then use self._lineFilterKernel
                            If not None then set self._lineFilterKernel
        """
        startSeconds = time.time()

        if verbose:
            logger.info('Start')

        imageFilterKenel = self.getAnalysisParam('imageFilterKenel')
        lineFilterKernel = self.getAnalysisParam('lineFilterKernel')

        if imageFilterKenel > 0:
            self._filteredImage = scipy.signal.medfilt(self._kymImage, imageFilterKenel)
        else:
            self._filteredImage = self._kymImage

        _pointsPerLineScan = self.pointsPerLineScan()
        theRect = self.getRoiRect()

        if verbose:
            logger.info(f"  filtering entire image with median kernel {imageFilterKenel}")
            logger.info(f"  filtering each line with median kernel {lineFilterKernel}")
            logger.info(f"  getRoiRect (l,t,r,b) is {theRect}")
        
        # leftRect_sec = theRect.getLeft()
        # rightRect_sec = theRect.getRight()
        leftRect_line = theRect.getLeft()
        rightRect_line = theRect.getRight()

        # convert left/right of rect in seconds to line scan inex
        # leftRect_line = int(leftRect_sec / self.secondsPerLine)
        # rightRect_line = int(rightRect_sec / self.secondsPerLine)

        if verbose:
            logger.info(f"  leftRect_line:{leftRect_line} rightRect_line:{rightRect_line}")
            logger.info(f"  numLineScans():{self.numLineScans()}")
            logger.info(f"  _pointsPerLineScan():{_pointsPerLineScan}")
            logger.info(f"  umPerPixel:{self.umPerPixel}")
            logger.info(f"  secondsPerLine:{self.secondsPerLine}")
            logger.info(f"  percentOfMax:{self.getAnalysisParam('percentOfMax')}")

        sumIntensity = [np.nan] * self.numLineScans()
        left_idx_list = [np.nan] * self.numLineScans()
        right_idx_list = [np.nan] * self.numLineScans()
        diameter_idx_list = [np.nan] * self.numLineScans()

        min_list = [np.nan] * self.numLineScans()
        max_list = [np.nan] * self.numLineScans()
        range_list = [np.nan] * self.numLineScans()

        _maxSumIntensity = 0

        lineRange = np.arange(leftRect_line, rightRect_line)
        for line in lineRange:
            # get line profile using line width
            # outside roi rect will be nan
            intensityProfile, left_idx, right_idx = self._getFitLineProfile(line)
            #intensityProfile, left_idx, right_idx = lineProfileWorker()

            # logger.info(f'  len(intensityProfile):{len(intensityProfile)} \
            #             left_idx:{left_idx} \
            #             right_idx:{right_idx}')

            _sumIntensity = np.nansum(intensityProfile)
            sumIntensity[line] = _sumIntensity
            #sumIntensity[line] /= self._kymImage.shape[1]  # normalize to number of points in line scan
            if _sumIntensity > _maxSumIntensity:
                _maxSumIntensity = _sumIntensity

            _diamPixels = right_idx - left_idx + 1

            # 20230727, blank out if diam is really small
            # if _diamPixels < (_pointsPerLineScan * 0.5):
            #     logger.info(f'  blanking line {line} with _diamPixels:{_diamPixels}')
            #     left_idx_list[line] = np.nan
            #     right_idx_list[line] = np.nan
            #     diameter_idx_list[line] = np.nan
            # else:
            if 1:
                left_idx_list[line] = left_idx
                right_idx_list[line] = right_idx
                diameter_idx_list[line] = _diamPixels

            _min = np.nanmin(intensityProfile)
            _max = np.nanmax(intensityProfile)
            _range = _max - _min
            # logger.info(f'{_min} {_max} {_range}')
            min_list[line] = _min
            max_list[line] = _max
            range_list[line] = _range
            
        self._diamResults["time_sec"] = self.sweepX.tolist()
        
        self._diamResults["sumintensity_raw"] = sumIntensity
        
        kernelSize = 3
        sumintensity_filt = scipy.signal.medfilt(sumIntensity, kernelSize)
        self._diamResults["sumintensity_filt"] = sumintensity_filt

        # normalize sum to max
        sumIntensity = [_x/_maxSumIntensity for _x in sumIntensity]
        self._diamResults["sumintensity"] = sumIntensity  # normalized

        # filter
        diameter_um = np.multiply(diameter_idx_list, self.umPerPixel)
        self._diamResults["diameter_pnts"] = diameter_idx_list
        self._diamResults["diameter_um"] = diameter_um

        kernelSize = 5
        diameter_um_filt = scipy.signal.medfilt(diameter_um, kernelSize)
        self._diamResults["diameter_um_filt"] = diameter_um_filt

        self._diamResults["left_pnt"] = left_idx_list
        self._diamResults["right_pnt"] = right_idx_list

        self._diamResults["minInt"] = min_list
        self._diamResults["maxInt"] = max_list
        self._diamResults["rangeInt"] = range_list

        # smooth
        # kernelSize = 3
        # logger.info(f'put kernel size at user option, kernelSize: {kernelSize}')
        # diameter_um = self._diamResults['diameter_um']
        # diameter_um_f = scipy.signal.medfilt(diameter_um, kernelSize)

        # sumintensity = self._diamResults["sumintensity"]
        # sumintensity_f = scipy.signal.medfilt(sumintensity, kernelSize)

        # july 28, 2023, these are all the same for each line scan
        # not useful
        # self._diamResults["minDiam"] = np.nanmin(diameter_um)
        # self._diamResults["maxDiam"] = np.nanmax(diameter_um)
        # self._diamResults["diamChange"] = (
        #     self._diamResults["maxDiam"] - self._diamResults["minDiam"]
        # )
        # #
        # self._diamResults["minSum"] = np.nanmin(sumintensity)
        # self._diamResults["maxSum"] = np.nanmax(sumintensity)
        # self._diamResults["sumChange"] = self._diamResults["maxSum"] - self._diamResults["minSum"]

        self._diamAnalyzed = True
        self._analysisDirty = True

        if verbose:
            stopSeconds = time.time()
            durSeconds = round(stopSeconds - startSeconds, 2)
            logger.info(f"  analyzed {len(lineRange)} line scans in {durSeconds} seconds")

    def analyzeDiameter_mp(self):

        roiRect = self.getRoiRect()  # (l, t, r, b) in um and seconds (float)

        _detectionDict = {
            'lineWidth': self.getAnalysisParam('lineWidth'),
            'lineFilterKernel': self.getAnalysisParam('lineFilterKernel'),
            'detectPosNeg': self.getAnalysisParam('detectPosNeg'),
            'percentOfMax': self.getAnalysisParam('percentOfMax'),
            'src_pnt_space': roiRect.getBottom(),
            'dst_pnt_space': roiRect.getTop(),
        }
    
        results = lineProfilePool(self.getImage(), _detectionDict)

        print('results:', type(results))
        print(results[0])
        return

        #
        # # file results
        # self._diamResults["time_sec"] = self.sweepX.tolist()

        # self._diamResults["left_pnt"] = left_idx_list
        # self._diamResults["right_pnt"] = right_idx_list

        
        # self._diamResults["sumintensity_raw"] = sumIntensity

        # # normalize sum to max
        # sumIntensity = [_x/_maxSumIntensity for _x in sumIntensity]
        # self._diamResults["sumintensity"] = sumIntensity

        # diameter_um = np.multiply(diameter_idx_list, self.umPerPixel)
        # self._diamResults["diameter_pnts"] = diameter_idx_list
        # self._diamResults["diameter_um"] = diameter_um


# def lineProfileWorker(imgData, _percentOfMax, lineFilterKernel=0, src_pnt_space=None, dst_pnt_space=None):
def lineProfileWorker(imgData, detectionDict : dict):
    """
    Parameters
    ==========
        imgData : np.ndarry
            Image data to extract line profile from
            Assuming shape (line scans, pixels per line)
            line scans must be odd
        detectionDict : dict
            'lineWidth': lineWidth,
            'lineFilterKernel': lineFilterKernel,
            'percentOfMax': percentOfMax,
            'src_pnt_space': src_pnt_space,
            'dst_pnt_space': dst_pnt_space,
    """
    lineWidth = imgData.shape[0]
    numPixels = imgData.shape[1]

    lineFilterKernel = detectionDict['lineFilterKernel']
    detectPosNeg = detectionDict['detectPosNeg']
    percentOfMax = detectionDict['percentOfMax']
    src_pnt_space = detectionDict['src_pnt_space']
    dst_pnt_space = detectionDict['dst_pnt_space']

    print('lineWidth:', lineWidth, 'lineFilterKernel:', lineFilterKernel)
    
    if lineWidth == 1:
        intensityProfile = imgData[0,:]
        intensityProfile = np.flip(intensityProfile)  # FLIPPED

    else:
        middleLine = math.floor(lineWidth/2)
        # intensityProfile will always have len() of number of pixels in line scane
        # -1 because profile_line uses last pnt (unlike numpy)
        src = (middleLine, numPixels - 1)
        dst = (middleLine, 0)  # -1 because profile_line uses last pnt (unlike numpy)
        intensityProfile = profile.profile_line(
            imgData, src, dst, linewidth=lineWidth
        )

    # logger.info(f'intensityProfile:{intensityProfile.shape}')  # 379,
    # sys.exit(1)

    # median filter line profile
    if lineFilterKernel > 0:
        intensityProfile = scipy.signal.medfilt(intensityProfile, lineFilterKernel)

    # x = np.arange(0, len(intensityProfile) + 1)

    # Nan out before/after roi
    intensityProfile = intensityProfile.astype(float)  # we need nan
    if src_pnt_space is not None:
        intensityProfile[0:src_pnt_space] = np.nan
    if dst_pnt_space is not None:
        intensityProfile[dst_pnt_space:] = np.nan

    # fwhm, left_idx, right_idx = self.FWHM(x, intensityProfile)

    # detect either a pos (max) or neg (min) intensity along the line
    _doMax = detectPosNeg == 'pos'

    # 1) FWHM
    # if _doMax:
    #     _intMax = np.nanmax(intensityProfile)
    #     half_max = _intMax * percentOfMax  # 0.2
    #     # half_max = _intMax + (_intMax * _percentOfMax)  # 0.2
    # else:
    #     _intMax = np.nanmin(intensityProfile)
    #     half_max = _intMax + (_intMax * percentOfMax)  # 0.2

    # 2) STD
    stdMult = percentOfMax
    _intMean = np.nanmean(intensityProfile)
    _intStd = np.nanstd(intensityProfile)
    if _doMax:
        half_max = _intMean + (stdMult * _intStd)
    else:
        half_max = _intMean - (stdMult * _intStd)

    # 3) determine pos/neg by comparing first/middle/last
    if 0:
        _linesInEpoch = 10  # must be even
        _halfLinesInEpoch = _linesInEpoch  # int(_linesInEpoch * 2 / 2)  # twice as many point in the middle
        _middle_pnt_space = src_pnt_space + int( (dst_pnt_space - src_pnt_space) / 2 )
        _firstEpoch = intensityProfile[src_pnt_space:src_pnt_space+_linesInEpoch]
        _middleEpoch = intensityProfile[_middle_pnt_space-_halfLinesInEpoch:_middle_pnt_space+_halfLinesInEpoch]
        _lastEpoch = intensityProfile[dst_pnt_space-_linesInEpoch:dst_pnt_space]

        _firstEpochMean = np.nanmean(_firstEpoch)
        _middleEpochMean = np.nanmean(_middleEpoch)
        _lastEpochMean = np.nanmean(_lastEpoch)
        
        _minFirstLast = min(_firstEpochMean, _lastEpochMean)  # really need min and/or max

        # choose to search for pos/neg
        # if _minFirstLast < _middleEpochMean:
        #     _doMax = True
        # else:
        #     _doMax = False

    if _doMax:
        whr = np.asarray(intensityProfile > half_max).nonzero()
    else:
        whr = np.asarray(intensityProfile < half_max).nonzero()

    if len(whr[0]) > 2:
        # whr is (array,), only interested in whr[0]
        left_idx = whr[0][0]
        right_idx = whr[0][-1]
        # fwhm = X[right_idx] - X[left_idx]
    else:
        left_idx = np.nan
        right_idx = np.nan
        # fwhm = np.nan

    return intensityProfile, left_idx, right_idx
    # intensityProfile, left_idx, right_idx = self._getFitLineProfile(line)

# def lineProfilePool(imgData, lineWidth, roiRect, percentOfMax, detectPosNeg):
def lineProfilePool(imgData, detectionDict):
    """
    Parameters
    ==========
    tifData : np.ndarry
        tif data slice to analyze
    lineWidth : int
        Must be odd
    """
    startTime = time.time()

    # we know the scan line, determine start/stop based on roi
    # roiRect = self.getRoiRect()  # (l, t, r, b) in um and seconds (float)

    # src_pnt_space = self.um2pnt(roiRect.getBottom())
    # dst_pnt_space = self.um2pnt(roiRect.getTop())

    logger.info(f'imgData:{imgData.shape}')  # tifData:(10000, 519)
    numLines = imgData.shape[0]
    result_objs = []

    # _detectionDict = {
    #     'lineWidth': lineWidth,
    #     'lineFilterKernel': lineFilterKernel,
    #     'detectPosNeg': detectPosNeg,
    #     'percentOfMax': percentOfMax,
    #     'src_pnt_space': src_pnt_space,
    #     'dst_pnt_space': dst_pnt_space,
    # }

    lineWidth = detectionDict['lineWidth']

    with Pool(processes=os.cpu_count() - 1) as pool:
        
        for line in range(numLines):
            startLine = line - math.floor(lineWidth/2)
            if startLine < 0:
                startLine = 0
            # numpy uses (] indexing
            stopLine = line + math.floor(lineWidth/2) + 1
            if stopLine > numLines:
                stopLine = numLines

            imageSlice = imgData[startLine:stopLine,:]
            
            # logger.info(f'startLine:{startLine} stopLine:{stopLine} imageSlice:{imageSlice.shape}')
            
            # workerParams = (imageSlice, percentOfMax, lineFilterKernel, src_pnt_space, dst_pnt_space)
            workerParams = (imageSlice, detectionDict)
            
            result = pool.apply_async(lineProfileWorker, workerParams)
            result_objs.append(result)

        # run the workers
        logger.info(f'getting results from {len(result_objs)} workers')
        results = [result.get() for result in result_objs]

        # fetch the results (fast as everything is done)
        # for k, result in enumerate(results):
        #     # result is a tuple like
        #     # (intensityProfile, left_idx, right_idx)
        #     intensityProfile = result[0]
        #     left_idx = result[1]
        #     right_idx = result[2]
        
        # print(results[0])

    stopTime = time.time()
    logger.info(f'  took {round(stopTime-startTime,3)} seconds')

    return results

def testLineProfilePool():
    # path = "/Users/cudmore/data/rosie/Raw data for contraction analysis/Female Old/filter median 1 C2-0-255 Cell 2 CTRL  2_5_21 female wt old.tif"
    path = '/Users/cudmore/Dropbox/data/cell-shortening/cell 03.tif'
    
    ka = kymAnalysis(path)
    
    # linewidth 1 takes 5 seconds
    # linewidth 3 takes 120 seconds for 10000 line scans (for 5000 scans takes 44 sec)
    # ka.analyzeDiameter()

    # ka.saveAnalysis()

    # linewidth of 1 takes 16 seconds (need to use simplified version if linewidth is 1 !!!)
    # linewidth of 3 takes 16 seconds for 10000 line scans, 7.3 sec for 5000 scans
    # linewidth of 5 takes 17 seconds
    # linewidth of 7 takes 17 seconds
    roiRect = ka.getRoiRect()  # (l, t, r, b) in um and seconds (float)
    
    _testLineWidth = 1
    ka.setAnalysisParam('lineWidth', _testLineWidth)

    # ka.setAnalysisParam('lineFilterKernel', 0)

    _detectionDict = {
        'lineWidth': ka.getAnalysisParam('lineWidth'),
        'lineFilterKernel': ka.getAnalysisParam('lineFilterKernel'),
        'detectPosNeg': ka.getAnalysisParam('detectPosNeg'),
        'percentOfMax': ka.getAnalysisParam('percentOfMax'),
        'src_pnt_space': roiRect.getBottom(),
        'dst_pnt_space': roiRect.getTop(),
    }


    # todo: put this in kymAnalysis class
    # lineProfilePool(ka.getImage(), lineWidth, roiRect, _percentOfMax)
    lineProfilePool(ka.getImage(), _detectionDict)

    # plotKym(ka)
    # plotKym_plotly(ka)
    # plotDash(ka)

def plotKym(ka: kymAnalysis):
    """Plot a kym image using matplotlib."""
    import matplotlib.pyplot as plt

    sharex = False
    fig, axs = plt.subplots(3, 1, sharex=sharex)

    # extent is [l, r, b, t]
    _extent = ka.getImageRect().getMatPlotLibExtent()  # [l, t, r, b]
    logger.info(f"_extent [left, right, bottom, top]:{_extent}")
    tifDataCopy = ka.getImage().copy()
    tifDataCopy = np.rot90(tifDataCopy)
    # axs[0].imshow(tifDataCopy, extent=_extent)
    axs[0].imshow(tifDataCopy)

    sweepX = ka.sweepX
    print("  sweepX:", type(sweepX), sweepX.shape)

    sumIntensity = ka.getResults("sumintensity")
    print("  sumIntensity", type(sumIntensity), len(sumIntensity))
    axs[1].plot(ka.sweepX, sumIntensity)

    # TODO: Add filtering of diameter per line scan
    diameter_um = ka.getResults("diameter_um")
    axs[2].plot(ka.sweepX, diameter_um)

    plt.show()

if __name__ == "__main__":
    testLineProfilePool()