"""Backend kymograph analysis to be used with the kymographWidget

This is primarily for extracting the diameter from kymographs.

We also have a main sanpy interface to treat kymographs like e-phys recording
"""

import os
from pprint import pprint
import time
import numpy as np
import pandas as pd
from skimage.measure import profile
import scipy
import tifffile

#from shapeanalysisplugin._my_logger import logger
#from shapeanalysisplugin._util import _loadLineScanHeader

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

from sanpy._util import _loadLineScanHeader

class kymographAnalysis():
    def __init__(self, path, data=None, autoLoad=True):
        
        self._path = path
        
        # image must be shape[0] is time/big, shape[1] is space/small
        # opposite from my load abf from kymograph!!!
        if data is None:
            self._image = tifffile.imread(path)  # (line scan, pixels)
        else:
            self._image = data

        if self._image.shape[0] < self._image.shape[1]:
            logger.info(f'Rotating image with shape: {self._image.shape}')
            self._image = np.rot90(self._image, 3)  # ROSIE, so lines are not backward

        logger.info(f'final image shape is: {self._image.shape}')

        # load the header from Olympus exported .txt file
        self._umPerPixel = 1
        self._secondsPerLine = 1
        
        _olympusHeader = _loadLineScanHeader(path)
        #pprint(_olympusHeader)
        if _olympusHeader is not None:
            self._umPerPixel = _olympusHeader['umPerPixel']
            self._secondsPerLine = _olympusHeader['secondsPerLine']

        #logger.info(f'image has shape: {self._image.shape}')
        #logger.info(f'  _umPerPixel: {self._umPerPixel}')
        #logger.info(f'  _secondsPerLine: {self._secondsPerLine}')

        _size = len(self._image.shape)
        if  _size < 2 or _size > 3:
            logger.error(f'image must be 2d but is {self._image.shape}')
        
        # pos and size of rectangular ROI for analysis
        #_imageRect =self.getImageRect()
        #self._pos = (_imageRect[0], _imageRect[1])
        #self._size = (_imageRect[2], _imageRect[3])
        _posRoi, _sizeRoi = self.getFullRectRoi()
        self.setPosRoi(_posRoi)
        self.setSizeRoi(_sizeRoi)
        
        # analysis parameters
        self._lineWidth = 1  # If >1 the analysis get 100x SLOWER
        self._percentOfMax = 0.2

        self._version = '0.0.1'

        # analysis results
        _numLineScans = self.numLineScans()
        self._results = {
            'time_ms': [np.nan] * _numLineScans,
            'sumintensity': [np.nan] * _numLineScans,
            'diameter_um': [np.nan] * _numLineScans,
            'left_pnt': [np.nan] * _numLineScans,
            'right_pnt': [np.nan] * _numLineScans,
        }

        # load analysis if it exists
        if autoLoad:
            self.load()

    def getReport(self):
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
            'folder': folderName,
            'grandParentFolder': grandParentFolder,
            'file': fileName,
            'numLines': self.numLineScans(),
            'numPixels': self.numPixels(),
            'secondsPerLine': self._secondsPerLine,
            'umPerPixel': self._umPerPixel,
            'dur_sec': self.numLineScans() * self._secondsPerLine,
            'dist_um': self.numPixels() * self._umPerPixel,
            'tifMin': np.nanmin(self._image),  # TODO: make this for ROI rect
            'tifMax': np.nanmax(self._image),
            #
            'minDiam': self._results['minDiam'],
            'maxDiam': self._results['maxDiam'],
            'diamChange': self._results['diamChange'],
            #
            'minSum': self._results['minSum'],
            'maxSum': self._results['maxSum'],
            'sumChange': self._results['sumChange'],
        }
        return theDict

    def pnt2um(self, point):
        return point * self._umPerPixel
    
    def getResults(self, key):
        return self._results[key]

    def getTimeArray(self):
        """Get full time array across all line scans
        
        Time is in sec.
        """

        # (um/pixel, ms/line)
        #timeScale = self._scale[1]

        start = 0
        stop = self.numLineScans() #* timeScale
        step = 1 #timeScale

        ret = np.arange(start, stop, step)

        # ret is in lines: line*(seconds/line) -> seconds
        ret = np.multiply(ret, self._secondsPerLine)

        return ret

    def getSpaceArray(self):
        """Get full time array across all line scans
        
        Time is in sec.
        """

        # (um/pixel, ms/line)
        #timeScale = self._scale[1]

        start = 0
        stop = self.pointsPerLineScan() #* timeScale
        step = 1 #timeScale

        ret = np.arange(start, stop, step)

        # ret is in lines: line*(seconds/line) -> seconds
        ret = np.multiply(ret, self._umPerPixel)

        return ret

    def getImageRect(self):
        """
        Returns:
            (x, y, w, h)
        """
        width_sec = self.numLineScans() * self._secondsPerLine
        height_um = self.pointsPerLineScan() * self._umPerPixel
        x = 0
        y = 0
        return x, y, width_sec, height_um

    def getFullRectRoi(self, asRect=False):
        _reduceFraction = 0.16
        
        _rect = self.getImageRect()  # [left, top, widht, height]
        _rect = list(_rect)

        logger.info(f'before reduction _rect:{_rect}')
        # reduce top/bottom (space) by 0.15 percent
        percentReduction = _rect[3] * _reduceFraction
        _rect[1] += percentReduction
        _rect[3] -= 2*percentReduction
        logger.info(f'after reduction _rect:{_rect}')

        self._pos = (_rect[0], _rect[1])  # (0,0)
        self._size = (_rect[2], _rect[3])  #(self.getImageShape()[0], self.getImageShape()[1])        
        
        if asRect:
            return _rect
        else:
            return self._pos, self._size

    def getRoiRect(self, asInt=True):
        """
        Get the current roi rectangle.
        
        Return:
            l,t,r,b
        """
        #imageShape = self.getImageShape()
        pos = self._pos
        size = self._size

        left = pos[0]
        top = pos[1] + size[1]
        right = pos[0] + size[0]
        bottom = pos[1]

        if asInt:
            left = int(left)
            top = int(top)
            right = int(right)
            bottom = int(bottom)

        # TODO (cudmore) implement this
        '''
        if left<0: left = 0
        if top>xxx: top = xxx
        if right>yyy: right = yyy
        if bottom<0: bottom = 0
        '''

        return (left, top, right, bottom)

    def setPercentOfMax(self, percent):
        """Set the percent of max used in xxx().
        """
        self._percentOfMax = percent
    
    def getPercentOfMax(self):
        return self._percentOfMax
    
    def getLineWidth(self) -> int:
        return self._lineWidth
    
    def setLineWidth(self, width : int):
        self._lineWidth = width
    
    def old_setPosSizeFromRect(self, rect):
        """
        rect: (l, t, r, b)
        """
        left = rect[0]
        top = rect[0]
        right = rect[0]
        bottom = rect[0]

        width = right - left + 1
        height = top - bottom + 1

        self._pos = (bottom, left)
        self._size = (width, height)

        #logger.info(f'pos:{self._pos} size:{self._size}')

    def rotateImage(self):
        self._image = np.rot90(self._image)
        return self._image

    def getImage(self):
        return self._image
    
    def getImageShape(self):
        return self._image.shape  # (w, h)
        
    def getLineWidth(self):
        return self._lineWidth
    
    def setPosRoi(self, pos : tuple):
        logger.info(f'pos is (left,bottom): {pos}')
        self._pos = pos
    
    def setSizeRoi(self, size : tuple):
        logger.info(f'size is (width,height): {size}')
        self._size = size
    
    def getPosRoi(self):
        return self._pos
    
    def getSizeRoi(self):
        return self._size

    def numLineScans(self):
        return self.getImageShape()[0]

    def pointsPerLineScan(self):
        return self.getImageShape()[1]

    def numPixels(self):
        return self.getImageShape()[1]

    def getAnalysisFile(self):
        """Get full path to analysis file we save/load.
        """
        savePath, saveFile = os.path.split(self._path)
        saveFileBase, ext = os.path.splitext(saveFile)
        saveFile = saveFileBase + '-analysis.csv'
        #print('    savePath:', savePath)
        #print('    saveFileBase:', saveFileBase)
        #print('    saveFile:', saveFile)

        savePath = os.path.join(savePath, saveFile)
        #print('    savePath:', savePath)

        return savePath

    def _getHeader(self):
        header = ''

        lineWidth = self.getLineWidth()
        percentOfMax = self.getPercentOfMax()
        roiRect = self.getRoiRect()

        header += f'version={self._version};'

        filePath, fileName = os.path.split(self._path)
        header += f'file={fileName};'
        
        header += f'linewidth={lineWidth};'
        header += f'percentofmax={percentOfMax};'
        
        # don't put tuple in header, expand
        #header += f'roiRect={roiRect};'
        header += f'lrectroi={roiRect[0]};'
        header += f'trectroi={roiRect[1]};'
        header += f'rrectroi={roiRect[2]};'
        header += f'brectroi={roiRect[3]};'

        return header

    def save(self, path : str = None):
        #logger.info('')

        if path is None:
            savePath = self.getAnalysisFile()
            #name = QtGui.QFileDialog.getSaveFileName(self, 'Save File')
        else:
            savePath = path

        header = self._getHeader()

        df = pd.DataFrame(self._results)
        #pprint(df)

        with open(savePath, 'w') as f:
            f.write(header)
            f.write('\n')
        
        logger.info(f'saving {len(df)} lines to {savePath}')

        df.to_csv(savePath, mode='a')

    def _parseHeader(self, header):
        """Parse one line header into member variables.
        
        This is parsing header we save with analysis.
        """
        kvList = header.split(';')
        for kv in kvList:
            if not kv:
                # handle trailing ';'
                continue
            k,v = kv.split('=')
            #print('    k:', k, 'v:', v)
            if k == 'lrectroi':
                left = float(v)
            elif k == 'trectroi':
                top = float(v)
            elif k == 'rrectroi':
                right = float(v)
            elif k == 'brectroi':
                bottom = float(v)

            elif k == 'linewidth':
                self._lineWidth = int(v)
            elif k == 'percentofmax':
                self._percentOfMax = float(v)

        width = right - left #+ 1
        height = top - bottom #+ 1
        
        self._pos = (left, bottom)
        self._size = (width, height)

        # print('left:', left)
        # print('top:', top)
        # print('right:', right)
        # print('bottom:', bottom)
        logger.info(f'  _pos: {self._pos}')
        logger.info(f'  _size: {self._size}')
        
    def load(self):
        """Load <file>-analysis.csv
        
            Look in parent folder of .tif file
        """
        savePath = self.getAnalysisFile()
        if not os.path.isfile(savePath):
            logger.info(f'did not find file: {savePath}')
            return

        logger.info(f'loading analysis from: {savePath}')

        with open(savePath) as f:
            header = f.readline().rstrip()
        
        self._parseHeader(header)  # parse header of saved analysis

        df = pd.read_csv(savePath, header=1)
        #pprint(df)

        # parse df into self._results dictionary
        '''
        self._results = {
            'time_ms': [],
            'sumintensity': [],
            'diameter': [],
            'leftpnt': [],
            'rightpnt': [],
        }
        '''
        self._results['time_ms'] = df['time_ms']
        self._results['sumintensity'] = df['sumintensity']
        self._results['diameter_um'] = df['diameter_um']
        self._results['left_pnt'] = df['left_pnt']
        self._results['right_pnt'] = df['right_pnt']
        
    def analyze(self):
        startSeconds = time.time()
        
        # ROSIE, set to 0.15 percent
        #theRect = self.getFullRectRoi(asRect=True)
        #theRect = self.getRoiRect()  # (l, t, r, b)
        theRect = self.getRoiRect()

        logger.info(f'(l,t,r,b) is {theRect}')
        leftRect_sec = theRect[0]
        rightRect_sec = theRect[2]
                
        # convert left/right of rect in seconds to line scan inex
        leftRect_line = int(leftRect_sec / self._secondsPerLine)
        rightRect_line = int(rightRect_sec / self._secondsPerLine)
        
        #logger.info(f'roi rect:{theRect} leftRect_line:{leftRect_line} rightRect_line:{rightRect_line}')

        sumIntensity = [np.nan] * self.numLineScans()
        left_idx_list = [np.nan] * self.numLineScans()
        right_idx_list = [np.nan] * self.numLineScans()
        diameter_idx_list = [np.nan] * self.numLineScans()
        
        # print('=== DEBUG ROSIE rightRect_line = 2000')
        # rightRect_line = 2000
        
        #logger.info(f'leftRect_line:{leftRect_line} rightRect_line:{rightRect_line}')
        
        lineRange = np.arange(leftRect_line, rightRect_line)
        for line in lineRange:
                        
            # logger.info(f'line:{line}')
            # logger.info(f'  ')

            # get line profile using line width
            # outside roi rect will be nan
            intensityProfile, left_idx, right_idx = \
                            self._getFitLineProfile(line)

            # logger.info(f'  len(intensityProfile):{len(intensityProfile)} \
            #             left_idx:{left_idx} \
            #             right_idx:{right_idx}')

            sumIntensity[line] = np.nansum(intensityProfile)
            # normalize to number of points in line scan
            sumIntensity[line] /= self._image.shape[1]

            left_idx_list[line] = left_idx
            right_idx_list[line] = right_idx
            diameter_idx_list[line] = right_idx - left_idx + 1

        self._results['time_ms'] = self.getTimeArray().tolist()
        self._results['sumintensity'] = sumIntensity
        self._results['diameter_um'] = np.multiply(diameter_idx_list, self._umPerPixel)
        self._results['left_pnt'] = left_idx_list
        self._results['right_pnt'] = right_idx_list

        # smooth
        kernelSize = 5
        diameter_um = self._results['diameter_um']
        sumintensity = self._results['sumintensity']
        logger.info(f'Smoothing with scipy.signal.medfilt')
        logger.info(f'  len(diameter_um):{len(diameter_um)} kernelSize:{kernelSize}')
        diameter_um_f = scipy.signal.medfilt(diameter_um, kernelSize)
        logger.info(f'  len(sumintensity):{len(sumintensity)} kernelSize:{kernelSize}')
        sumintensity_f = scipy.signal.medfilt(sumintensity, kernelSize)
        #
        self._results['minDiam'] = np.nanmin(diameter_um_f)
        self._results['maxDiam'] = np.nanmax(diameter_um_f)
        self._results['diamChange'] = self._results['maxDiam'] - self._results['minDiam']
        #
        self._results['minSum'] = np.nanmin(sumintensity_f)
        self._results['maxSum'] = np.nanmax(sumintensity_f)
        self._results['sumChange'] = self._results['maxSum'] - self._results['minSum']

        stopSeconds = time.time()
        durSeconds = round(stopSeconds-startSeconds,2)
        logger.info(f'  analyzed {len(lineRange)} line scans in {durSeconds} seconds')

    def pnt2um(self, point):
        return point * self._umPerPixel
    
    def seconds2pnt(self, seconds):
        return int(seconds / self._secondsPerLine)

    def um2pnt(self, um):
        return int(um / self._umPerPixel)

    def _getFitLineProfile(self, lineScanNumber):
        """
        Returns points
        """
        
        # TODO: want to get based on rect roi

        # we know the scan line, determine start/stop based on roi
        roiRect = self.getRoiRect()  # (l, t, r, b) in um and seconds (float)
        
        #logger.info(f'roiRect: {roiRect} self._image.shape:{self._image.shape}')
        
        src_pnt_space = self.um2pnt(roiRect[3])
        dst_pnt_space = self.um2pnt(roiRect[1])

        # intensityProfile will always have len() of number of pixels in line scan
        src = (lineScanNumber, 0)
        dst = (lineScanNumber, self.numPixels()-1)  # -1 because profile_line uses last pnt (unlike numpy)
        
        #print('  image:', self._image.shape)
        #print('  src:', src)
        #print('  dst:', dst)
        
        # intensityProfile will always have len() of number of pixels in line scane
        if self._lineWidth == 1:
            intensityProfile = self._image[lineScanNumber,:]
            intensityProfile = intensityProfile.astype(float)
            # median filter line profile
            kernelSize = 5
            intensityProfile = scipy.signal.medfilt(intensityProfile, kernelSize)

        else:
            intensityProfile = \
                    profile.profile_line(self._image, src, dst, linewidth=self._lineWidth)

        #print('  intensityProfile:', intensityProfile.shape, type(intensityProfile))

        # TODO: line profile will always have same length, 
        #   nan our based on rect roi ???

        #x = np.asarray([a for a in range(len(intensityProfile))]) # make alist of x points (todo: should be um, not points!!!)
        x = np.arange(0, len(intensityProfile)+1)

        # TODO: nan out before/after roi
        intensityProfile[0:src_pnt_space] = np.nan
        #intensityProfile[dst_pnt_space:-1] = np.nan
        intensityProfile[dst_pnt_space:] = np.nan
        
        fwhm, left_idx, right_idx = self.FWHM(x, intensityProfile)

        #left_idx = self.pnt2um(left_idx)
        #right_idx = self.pnt2um(right_idx)

        '''
        print('  roiRect:', roiRect)
        print('  len(intensityProfile):', len(intensityProfile))
        print('  len(x):', len(x))
        print('  src_pnt_space:', src_pnt_space)
        print('  dst_pnt_space:', dst_pnt_space)
        print('  left_idx:', left_idx)
        print('  right_idx:', right_idx)
        '''

        return intensityProfile, left_idx, right_idx

    # see: https://stackoverflow.com/questions/10582795/finding-the-full-width-half-maximum-of-a-peak
    def FWHM(self, X, Y):
        #logger.info(f'_percentOfMax:{self._percentOfMax}')
        
        #Y = scipy.signal.medfilt(Y, 3)
        
        #half_max = max(Y) / 2.
        #half_max = max(Y) * 0.7
        half_max = np.nanmax(Y) * self._percentOfMax  #0.2

        # for explanation of this wierd syntax
        # see: https://docs.scipy.org/doc/numpy/reference/generated/numpy.where.html
        #whr = np.where(Y > half_max)
        #print('   half_max:', half_max)
        whr = np.asarray(Y > half_max).nonzero()
        if len(whr[0]) > 2:
            left_idx = whr[0][0]
            right_idx = whr[0][-1]
            fwhm = X[right_idx] - X[left_idx]
        else:
            left_idx = np.nan
            right_idx = np.nan
            fwhm = np.nan
        return fwhm, left_idx, right_idx #return the difference (full width)
