# 20210129

import os, sys
import numpy as np

import tifffile

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class bAbfText:
    """
    mimic a pyabf file to load from a text file
    """

    def __init__(self, path=None, theDict=None):
        """
        path is either:
            path to .csv file with columns (time (seconds), vm)
            path to .tif file

        theDict:
            sweepX
            sweepY
        """

        self.path = path

        self.sweepX = None
        self.sweepY = None
        self.dataRate = None
        self.dataPointsPerMs = None
        self.sweepList = [0]

        self.tif = None
        self.tifNorm = None  # not used
        self.tifHeader = None

        if theDict is not None:
            logger.info("bAbfText() from dict")
            self.sweepX = theDict["sweepX"]
            self.sweepY = theDict["sweepY"]
        elif path.endswith(".tif"):
            self.sweepX, self.sweepY, self.tif, self.tifNorm = self._abfFromLineScanTif(
                path
            )
            # self.tifHeader = self._loadLineScanHeader(path)

            # logger.info(f'tif params: {np.min(self.tif)} {np.max(self.tif)} {self.tif.shape} {self.tif.dtype}')
        else:
            logger.info("bAbfText() from path: {path}")
            if not os.path.isfile(path):
                logger.error("Did not find file: {path}")
                return

            tmpNumPy = np.loadtxt(path, skiprows=1, delimiter=",")
            self.sweepX = tmpNumPy[:, 0]
            self.sweepY = tmpNumPy[:, 1]

        #
        # linescan is like
        # 'secondsPerLine': 0.0042494285714285715,
        # 1 / secondsPerLine = 235.32
        # 20220926, if this is '1' second, detection will fail
        #  because self.dataPointsPerMs goes to 0
        secondsPerSample = self.sweepX[1] - self.sweepX[0]
        samplesPerSecond = 1 / secondsPerSample
        self.dataRate = samplesPerSecond  # 235 #10000 # samples per second

        # todo: calculat from dataRate
        secondsPerSample = 1 / samplesPerSecond
        msPerSample = secondsPerSample * 1000
        samplesPerMs = 1 / msPerSample
        self.dataPointsPerMs = samplesPerMs  # 4.255 #1/235*1000,10 # 10 kHz

        self.sweepUnitsX = "todo: fix"
        self.sweepUnitsY = "todo: fix"

        # self.myRectRoi = None
        self.myRectRoiBackground = None
        # self.minLineScan = None

        # done in _abfFromLineScanTif
        # defaultRect = self.defaultTifRoi_background()  # for kymograph
        # self.updateTifRoi_background(defaultRect)

        # defaultRect = self.defaultTifRoi()  # for kymograph
        # self.updateTifRoi(defaultRect)

        #
        # print results
        """
        if self.tifHeader is not None:
            for k,v in self.tifHeader.items():
                print('  ', k, ':', v)

        print('  ', 'bAbfText secondsPerSample:', secondsPerSample, 'seconds/sample')
        print('  ', 'bAbfText self.dataRate:', self.dataRate, 'samples/second')
        print('  ', 'bAbfText self.dataPointsPerMs:', self.dataPointsPerMs)
        """

    def defaultTifRoi_background(self):
        """
        Default ROI for kymograph background

        - height/width about 5 pixels
        - position near the end of the line
        """
        widthTif = self.tif.shape[1]
        heightTif = self.tif.shape[0]
        insetPixels = 10  # from end of line (top)
        roiWidthHeight = 5
        # tifHeightPercent = self.tif.shape[0] * 0.15

        left = int(widthTif / 2)
        top = heightTif - insetPixels
        right = left + roiWidthHeight - 1
        bottom = top - roiWidthHeight + 1

        return [left, top, right, bottom]

    def resetRoi(self):
        """reset the kymograph roi to default"""
        defaultRect = self.defaultTifRoi()
        self.updateTifRoi(defaultRect)
        return defaultRect

    def defaultTifRoi(self):
        """
        A default rectangular ROI for main kymograph analysis.

        TODO: Remove hard coding of 0.15 percent of height

        Return:
            list: [left, top, right, bottom]
        """
        xRoiPos = 0  # startSeconds
        yRoiPos = 0  # pixels
        widthRoi = self.tif.shape[1]
        heightRoi = self.tif.shape[0]
        tifHeightPercent = self.tif.shape[0] * 0.15
        yRoiPos += tifHeightPercent
        heightRoi -= 2 * tifHeightPercent

        left = xRoiPos
        top = yRoiPos + heightRoi
        right = xRoiPos + widthRoi
        bottom = yRoiPos

        left = int(left)
        top = int(top)
        right = int(right)
        bottom = int(bottom)

        return [left, top, right, bottom]

    def getTifRoiBackground(self):
        return self.myRectRoiBackground

    def getTifRoi(self):
        return self.myRectRoi

    def updateTifRoi_background(self, theRect=None):
        if theRect is None:
            theRect = self.defaultTifRoi_background()
        if theRect is not None:
            left = theRect[0]
            top = theRect[1]
            right = theRect[2]
            bottom = theRect[3]

        self.myRectRoiBackground = theRect

        tif = self.tif
        theSum = np.sum(tif[bottom:top, left:right])

        return theSum

    def updateTifRoi(self, theRect=None):
        """
        Recalculate (sweepX, sweepY) based on user specified rect ROI

        Args:
            theRect (list): left, top, right, bottom

        Notes:
            This is doing 'background subtract' on sum of line - sum in background roi
                I don't think this is correct???
                'sum of line' has num pixels in scan
                'sum background roi' has a different number of pixels !!!
        """

        logger.info(theRect)

        self.myRectRoi = theRect

        firstFrameSeconds = 0

        tif = self.tif

        left = 0  # startSec
        top = tif.shape[0]
        right = tif.shape[1]  # stopSec
        bottom = 0
        if theRect is not None:
            # left = theRect[0]
            top = theRect[1]
            # right = theRect[2]
            bottom = theRect[3]

        # number of pixels in subset of line scan
        numPixels = top - bottom + 1

        # theBackground = self.updateTifRoi_background()

        # logger.warning(f'I turned off background subtract .. placement of background is sometimes bad')

        _secondsPerLine = self.tifHeader["secondsPerLine"]
        if _secondsPerLine is None:
            _secondsPerLine = 0.001  # so we get 1 pnt per ms
            logger.warning(
                f"No header, secondsPerLine is None. Using fake _secondsPerLine:{_secondsPerLine}"
            )

        # retains shape of entire tif
        yLineScanSum = [np.nan] * tif.shape[1]
        xLineScanSum = [np.nan] * tif.shape[1]
        for i in range(tif.shape[1]):
            # sum each column and background subtract

            # always assign time
            xLineScanSum[i] = firstFrameSeconds + (_secondsPerLine * i)
            # if self.tifHeader['secondsPerLine'] is None:
            #     # no units on kymograph
            #     _fakeSecondsPerLine = 0.001
            #     #logger.error(f'No header, secondsPerLine is None. Using _fakeSecondsPerLine:{_fakeSecondsPerLine}')
            #     xLineScanSum[i] = firstFrameSeconds + (_fakeSecondsPerLine * i)
            # else:
            #     xLineScanSum[i] = firstFrameSeconds + (self.tifHeader['secondsPerLine'] * i)

            if i < left or i > right:
                continue

            # each line scan
            theSum = np.sum(tif[bottom:top, i])

            # background subtract
            # print(f'   === theSum:{theSum} {type(theSum)} theBackground:{theBackground} {type(theBackground)}')
            # if not isinstance(theSum, np.uint64) or not isinstance(theBackground, np.uint64):
            #    print(f'   === theSum:{theSum} {type(theSum)} theBackground:{theBackground} {type(theBackground)}')

            # logger.warning(f'I turned off background subtract .. placement of background is sometimes bad')
            # theSum -= theBackground

            # sys.exit(1)

            # f / f_0
            theSum /= numPixels  # tif.shape[0] # norm to number of pixels in line
            yLineScanSum[i] = theSum

        xLineScanSum = np.asarray(xLineScanSum)
        yLineScanSum = np.asarray(yLineScanSum)

        # derive simplified f/f0 by dividing by min
        self.minLineScan = np.nanmin(yLineScanSum)

        # 20221003, do not do this, ysweep will be sum/pnts
        # yLineScanSum /= self.minLineScan

        logger.info("updating sweepX and sweepY with new rect ROI")
        self.sweepX = xLineScanSum
        self.sweepY = yLineScanSum

    def setSweep(self, sweep):
        pass

    def _abfFromLineScanTif(self, path, theRect=None):
        """

        Returns:
            xLineScanSum (np.ndarray) e.g. sweepX
            yLineScanSum (np.ndarray) e.g. sweepY
        """
        if not os.path.isfile(path):
            logger.error(f"Did not find file: {path}")
            return None, None, None, None

        tif = tifffile.imread(path)
        logger.info(f"Loaded tif with shape: {tif.shape}")

        if len(tif.shape) == 3:
            tif = tif[:, :, 1]  # assuming image channel is 1

        # we want our tiffs to be short and wide
        # shape[0] is space, shape[1] is time
        if tif.shape[0] < tif.shape[1]:
            # correct shape
            pass
        else:
            tif = np.rot90(tif)  # rotates 90 degrees counter-clockwise

        f0 = tif.mean()
        tifNorm = (tif - f0) / f0

        self.tif = tif

        # assuming this was exported using Olympus software
        # which gives us a .txt file
        self.tifHeader = self._loadLineScanHeader(path)
        # self.tifHeader['shape'] = tif.shape
        # self.tifHeader['secondsPerLine'] = \
        #                self.tifHeader['totalSeconds'] / self.tifHeader['shape'][1]
        # tifHeader['abfPath'] = abfFile

        # updateTifRoi sets sweepX and seepY
        defaultRect = self.defaultTifRoi()
        self.updateTifRoi(defaultRect)

        firstFrameSeconds = 0

        #
        # sum the inensities of each image line scan
        # print('tif.shape:', tif.shape) # like (146, 10000)
        """
        yLineScanSum = [np.nan] * tif.shape[1]
        xLineScanSum = [np.nan] * tif.shape[1]
        for i in range(tif.shape[1]):
            theSum = np.sum(tif[:,i])
            theSum /= tif.shape[0] # norm to number of pixels in line
            yLineScanSum[i] = theSum
            xLineScanSum[i] = firstFrameSeconds + (self.tifHeader['secondsPerLine'] * i)

        xLineScanSum = np.asarray(xLineScanSum)
        yLineScanSum = np.asarray(yLineScanSum)
        """

        # normalize to 0..1
        # 20220114, was this
        # yLineScanSum = self._NormalizeData(yLineScanSum)

        # print('bAbfText xLineScanSum:', xLineScanSum.shape)
        # print('bAbfText yLineScanSum:', yLineScanSum.shape)

        return self.sweepX, self.sweepY, tif, tifNorm

    def _loadLineScanHeader(self, path):
        """Load scale from .txt file saved by olympus export.

        Args:
            path: full path to tif

        returns dict:
            numPixels:
            umLength:
            umPerPixel:
            totalSeconds:
        """

        def _defaultHeader():
            defaultHeader = {
                "tif": path,
                "numLines": self.tif.shape[1],
                "totalSeconds": None,
                "shape": self.tif.shape,
                "secondsPerLine": 0.001,
                #'linesPerSecond': None,  # 1/secondsPerLine
                "numPixels": self.tif.shape[0],
                "umLength": None,
                "umPerPixel": 1,
            }
            return defaultHeader

        # "X Dimension"    "138, 0.0 - 57.176 [um], 0.414 [um/pixel]"
        # "T Dimension"    "1, 0.000 - 35.496 [s], Interval FreeRun"
        # "Image Size(Unit Converted)"    "57.176 [um] * 35500.000 [ms]"
        txtFile = os.path.splitext(path)[0] + ".txt"

        theRet = _defaultHeader()
        # theRet = {'tif': path}
        # theRet['numLines'] = self.tif.shape[1]

        if not os.path.isfile(txtFile):
            logger.warning(f"Did not find file: {txtFile}")
            logger.warning(f"  The Kymograph will have no scale.")
            return theRet

        # to open export .txt file for Olympus FV3000
        with open(txtFile, "r") as fp:
            lines = fp.readlines()
            for line in lines:
                line = line.strip()
                if line.startswith('"X Dimension"'):
                    line = line.replace('"', "")
                    line = line.replace(",", "")
                    # print('loadLineScanHeader:', line)
                    # 2 number of pixels in line
                    # 5 um length of line
                    # 7 um/pixel
                    splitLine = line.split()
                    for idx, split in enumerate(splitLine):
                        # print('  ', idx, split)
                        if idx == 2:
                            numPixels = int(split)
                            theRet["numPixels"] = numPixels
                        elif idx == 5:
                            umLength = float(split)
                            theRet["umLength"] = umLength
                        elif idx == 7:
                            umPerPixel = float(split)
                            theRet["umPerPixel"] = umPerPixel

                elif line.startswith('"T Dimension"'):
                    line = line.replace('"', "")
                    line = line.replace(",", "")
                    # print('loadLineScanHeader:', line)
                    # 5 total duration of image acquisition (seconds)
                    splitLine = line.split()
                    for idx, split in enumerate(splitLine):
                        # print('  ', idx, split)
                        if idx == 5:
                            totalSeconds = float(split)
                            theRet["totalSeconds"] = totalSeconds

                            # theRet['secondsPerLine'] =

                # elif line.startswith('"Image Size(Unit Converted)"'):
                #    print('loadLineScanHeader:', line)

        # theRet['shape'] = self.tif.shape
        theRet["secondsPerLine"] = theRet["totalSeconds"] / theRet["shape"][1]
        # theRet['linesPerSecond'] = 1 / theRet['secondsPerLine']
        #
        return theRet

    def _NormalizeData(self, data):
        """
        normalize to [0..1]
        """
        return (data - np.min(data)) / (np.max(data) - np.min(data))


def test_load_tif():
    path = "/Users/cudmore/data/dual-lcr/20210115/data/20210115__0001.tif"
    abf = bAbfText(path=path)

    import matplotlib.pyplot as plt

    plt.plot(abf.sweepX, abf.sweepY)
    plt.show()


if __name__ == "__main__":
    test_load_tif()
