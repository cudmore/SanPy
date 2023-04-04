"""Backend kymograph analysis to be used with the kymographWidget

Perform all kymograph analysis here including:
    - Sum of each line scan
    - Diameter of each line scan
    - Detect peaks in diameter

This will replace code on bAnalysis (abfText)
"""

import os
from pprint import pprint

# from re import T
import time
import numpy as np
import pandas as pd
from skimage.measure import profile
import scipy
import tifffile

import sanpy

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

from sanpy._util import _loadLineScanHeader


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

    def __str__(self):
        return f"l:{self._l} t:{self._t} r:{self._r} b:{self._b}"


class kymAnalysis:
    def __init__(self, path: str, autoLoad: bool = True):
        """

        Args:
            path: full path to .tif file
            autoLoad: auto load analysis
        """
        self._version = "0.0.2"

        self._path = path
        # path to tif file

        # (line scan, pixels)
        self._kymImage: np.ndarray = tifffile.imread(path)

        self._kymImageFiltered = None
        # create this as needed, see self._kymImageFilterKernel

        _size = len(self._kymImage.shape)
        if _size < 2 or _size > 3:
            # TODO: raise custom exception
            logger.error(f"image must be 2d but is {self._kymImage.shape}")

        # image must be shape[0] is time/big, shape[1] is space/small
        if self._kymImage.shape[0] < self._kymImage.shape[1]:
            logger.info(f"rotating image with shape: {self._kymImage.shape}")
            self._kymImage = np.rot90(
                self._kymImage, 3
            )  # ROSIE, so lines are not backward

        # this is what we extract line profiles from
        # we create filtered version at start of detect()
        self._filteredImage: np.ndarray = self._kymImage

        logger.info(f"final image shape is: {self._kymImage.shape}")

        # load the header from Olympus exported .txt file

        self._umPerPixel = 1
        # default for pixels is unity of 1 pixel

        self._secondsPerLine = 0.001  # 0.001  #0.001  # make ms per bin = 1
        # default for time (lines) is 1 ms = 0.001 s

        _olympusHeader = _loadLineScanHeader(path)
        if _olympusHeader is not None:
            self._umPerPixel = _olympusHeader["umPerPixel"]
            self._secondsPerLine = _olympusHeader["secondsPerLine"]

        self._reduceFraction = 0.15
        # percentage to reduce t/b of full rect roi to make best guess

        self._roiRect: kymRect = self.getBestGuessRectRoi()
        # rectangular roi [l, t, r, b']

        # analysis parameters
        self._lineWidth = 1
        # Actual line width to extract a line profile.
        # If >1 will get 10x-100x slower
        # TODO: write multiprocessing code

        self._percentOfMax = 0.2
        # to find start/stop of diameter fit along one line profile

        self._kymImageFilterKernel = 0
        # on analysis, pre-filter image with median kernel

        self._lineFilterKernel = 0
        # on analysis, pre-filter each line with median kernel

        # analysis results
        _numLineScans = self.numLineScans()
        self._results = self.getDefaultResultsDict()

        # load saved analysis if it exists
        if autoLoad:
            self.loadAnalysis()

    def getDefaultResultsDict(self):
        _numLineScans = self.numLineScans()
        theDict = {
            "time_bin": [np.nan] * _numLineScans,
            "time_sec": [np.nan] * _numLineScans,
            "sumintensity": [np.nan] * _numLineScans,
            "diameter_pnts": [np.nan] * _numLineScans,
            "diameter_um": [np.nan] * _numLineScans,
            "left_pnt": [np.nan] * _numLineScans,
            "right_pnt": [np.nan] * _numLineScans,
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
            "secondsPerLine": self._secondsPerLine,
            "umPerPixel": self._umPerPixel,
            "dur_sec": self.numLineScans() * self._secondsPerLine,
            "dist_um": self.numPixels() * self._umPerPixel,
            "tifMin": np.nanmin(self._kymImage),  # TODO: make this for ROI rect
            "tifMax": np.nanmax(self._kymImage),
            #
            "minDiam": self._results["minDiam"],
            "maxDiam": self._results["maxDiam"],
            "diamChange": self._results["diamChange"],
            #
            "minSum": self._results["minSum"],
            "maxSum": self._results["maxSum"],
            "sumChange": self._results["sumChange"],
        }
        return theDict

    def pnt2um(self, point):
        return point * self._umPerPixel

    def getResults(self, key) -> list:
        return self._results[key]

    @property
    def sweepX(self):
        """Get full time array across all line scans

        Time is in sec. Same as bAnalysis.sweepX
        """

        ret = np.arange(0, self.numLineScans(), 1)
        ret = np.multiply(ret, self._secondsPerLine)

        return ret

    def getImageRect(self):
        l = 0
        t = self.pointsPerLineScan() * self._umPerPixel
        r = self.numLineScans() * self._secondsPerLine
        b = 0
        return kymRect(l, t, r, b)

    def getBestGuessRectRoi(self):
        """Get a best guess of a rectangular roi.

        Args:
            asRect: If True, return [l,t,r,b] else return (pos, size)
        """

        _rect: kymRect = self.getImageRect()  # [left, top, r, b]

        logger.info(f"before reduction _rect:{_rect}")
        # reduce top/bottom (space) by 0.15 percent
        percentReduction = _rect.getHeight() * self._reduceFraction

        newTop = _rect.getTop() - 2 * percentReduction
        newBottom = _rect.getBottom() + percentReduction
        _rect.setTop(newTop)
        _rect.setBottom(newBottom)

        logger.info(f"after reduction _rect:{_rect}")

        # self._pos = (_rect[0], _rect[1])  # (0,0)
        # self._size = (_rect[2], _rect[3])  #(self.getImageShape()[0], self.getImageShape()[1])

        return _rect

    def getRoiRect(self, asInt=True) -> kymRect:
        """Get the current roi rectangle."""
        return self._roiRect

    def setRectRoi(self, newRect):
        """
        Args:
            newRect is [l, t, r, b]
        """
        l = newRect[0]
        t = newRect[1]
        r = newRect[2]
        b = newRect[3]
        self._roiRect = kymRect(l, t, r, b)

    def setPercentOfMax(self, percent):
        """Set the percent of max used in analyze()."""
        self._percentOfMax = percent

    def getPercentOfMax(self):
        return self._percentOfMax

    def getLineWidth(self) -> int:
        return self._lineWidth

    def setLineWidth(self, width: int):
        self._lineWidth = width

    def old_rotateImage(self):
        self._kymImage = np.rot90(self._kymImage)
        return self._kymImage

    def getImage(self):
        return self._kymImage

    def getImageContrasted(self, theMin, theMax, rot90=False):
        bitDepth = 8
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
        bitDepth = 8

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

    def getAnalysisFile(self):
        """Get full path to analysis file we save/load."""
        savePath, saveFile = os.path.split(self._path)
        saveFileBase, ext = os.path.splitext(saveFile)
        saveFile = saveFileBase + "-kymanalysis.csv"
        savePath = os.path.join(savePath, saveFile)
        return savePath

    def _getFileHeader(self):
        """Get one line header to save with analysis."""
        header = ""

        lineWidth = self.getLineWidth()
        percentOfMax = self.getPercentOfMax()
        roiRect = self.getRoiRect()

        header += f"version={self._version};"

        filePath, fileName = os.path.split(self._path)
        header += f"file={fileName};"

        header += f"linewidth={lineWidth};"
        header += f"percentofmax={percentOfMax};"

        # don't put tuple in header, expand
        # header += f'roiRect={roiRect};'
        header += f"lrectroi={roiRect.getLeft()};"
        header += f"trectroi={roiRect.getTop()};"
        header += f"rrectroi={roiRect.getRight()};"
        header += f"brectroi={roiRect.getBottom()};"

        # TODO: ad other params like (image median kernel, line median kernel, ...)

        return header

    def _parseFileHeader(self, header):
        """Parse one line header into member variables.

        This is parsing header we save with analysis.
        """
        kvList = header.split(";")
        for kv in kvList:
            if not kv:
                # handle trailing ';'
                continue
            k, v = kv.split("=")
            # print('    k:', k, 'v:', v)
            if k == "lrectroi":
                left = float(v)
            elif k == "trectroi":
                top = float(v)
            elif k == "rrectroi":
                right = float(v)
            elif k == "brectroi":
                bottom = float(v)

            elif k == "linewidth":
                self._lineWidth = int(v)
            elif k == "percentofmax":
                self._percentOfMax = float(v)

        width = right - left  # + 1
        height = top - bottom  # + 1

        self._pos = (left, bottom)
        self._size = (width, height)

        # print('left:', left)
        # print('top:', top)
        # print('right:', right)
        # print('bottom:', bottom)
        logger.info(f"  _pos: {self._pos}")
        logger.info(f"  _size: {self._size}")

    def saveAnalysis(self, path: str = None):
        """Save kymograph analysis.

        This includes:
            - time bins
            - sum of each line scan
            - diameter calculation for each line scan
            ...
        """

        if path is None:
            savePath = self.getAnalysisFile()
        else:
            savePath = path

        header = self._getFileHeader()

        with open(savePath, "w") as f:
            f.write(header)
            f.write("\n")

        df = pd.DataFrame(self._results)

        logger.info(f"saving {len(df)} lines to {savePath}")

        df.to_csv(savePath, mode="a")

    def loadAnalysis(self):
        """Load <file>-kymanalysis.csv

        Look in parent folder of .tif file
        """
        savePath = self.getAnalysisFile()
        if not os.path.isfile(savePath):
            logger.info(f"did not find file: {savePath}")
            return

        logger.info(f"loading analysis from: {savePath}")

        with open(savePath) as f:
            header = f.readline().rstrip()

        self._parseFileHeader(header)  # parse header of saved analysis

        df = pd.read_csv(savePath, header=1)

        # parse df into self._results dictionary
        """
        self._results = {
            'time_ms': [],
            'sumintensity': [],
            'diameter': [],
            'leftpnt': [],
            'rightpnt': [],
        }
        """
        try:
            self._results["time_ms"] = df["time_ms"].values
            self._results["sumintensity"] = df["sumintensity"].values
            self._results["diameter_pnts"] = df["diameter_pnts"].values
            self._results["diameter_um"] = df["diameter_um"].values
            self._results["left_pnt"] = df["left_pnt"].values
            self._results["right_pnt"] = df["right_pnt"].values
            self._results["diameter_pixels"] = df["diameter_pixels"].values
        except KeyError as e:
            # if we did not find a scale in rosie rosetta
            logger.error(f"DID NOT FIND KEY {e}")
            # self._results = None

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
        return point * self._umPerPixel

    def seconds2pnt(self, seconds):
        return int(seconds / self._secondsPerLine)

    def um2pnt(self, um):
        return int(um / self._umPerPixel)

    def analyze(self, imageMedianKernel=None, lineMedianKernel=None):
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

        if imageMedianKernel is None:
            imageMedianKernel = self._kymImageFilterKernel
        else:
            self._kymImageFilterKernel = imageMedianKernel

        if lineMedianKernel is None:
            lineMedianKernel = self._lineFilterKernel
        else:
            self._lineFilterKernel = lineMedianKernel

        logger.info("")
        logger.info(f"  filtering entire image with median kernel {imageMedianKernel}")
        logger.info(f"  filtering each line with median kernel {lineMedianKernel}")

        if imageMedianKernel > 0:
            self._filteredImage = scipy.signal.medfilt(
                self._kymImage, imageMedianKernel
            )
        else:
            self._filteredImage = self._kymImage

        theRect = self.getRoiRect()

        logger.info(f"  (l,t,r,b) is {theRect}")
        leftRect_sec = theRect.getLeft()
        rightRect_sec = theRect.getRight()

        # convert left/right of rect in seconds to line scan inex
        leftRect_line = int(leftRect_sec / self._secondsPerLine)
        rightRect_line = int(rightRect_sec / self._secondsPerLine)

        logger.info(f"  leftRect_line:{leftRect_line} rightRect_line:{rightRect_line}")
        logger.info(f"  self.numLineScans():{self.numLineScans()}")
        logger.info(f"  self._umPerPixel:{self._umPerPixel}")
        logger.info(f"  self._percentOfMax:{self._percentOfMax}")

        sumIntensity = [np.nan] * self.numLineScans()
        left_idx_list = [np.nan] * self.numLineScans()
        right_idx_list = [np.nan] * self.numLineScans()
        diameter_idx_list = [np.nan] * self.numLineScans()

        lineRange = np.arange(leftRect_line, rightRect_line)
        for line in lineRange:
            # get line profile using line width
            # outside roi rect will be nan
            intensityProfile, left_idx, right_idx = self._getFitLineProfile(
                line, lineMedianKernel
            )

            # logger.info(f'  len(intensityProfile):{len(intensityProfile)} \
            #             left_idx:{left_idx} \
            #             right_idx:{right_idx}')

            # normalize to number of points in line scan
            sumIntensity[line] = np.nansum(intensityProfile)
            sumIntensity[line] /= self._kymImage.shape[1]

            left_idx_list[line] = left_idx
            right_idx_list[line] = right_idx
            diameter_idx_list[line] = right_idx - left_idx + 1

        self._results["time_sec"] = self.sweepX.tolist()
        self._results["sumintensity"] = sumIntensity

        # filter
        diameter_um = np.multiply(diameter_idx_list, self._umPerPixel)
        # kernelSize = 5
        # diameter_um = scipy.signal.medfilt(diameter_um, kernelSize)
        self._results["diameter_pnts"] = diameter_idx_list
        self._results["diameter_um"] = diameter_um

        self._results["left_pnt"] = left_idx_list
        self._results["right_pnt"] = right_idx_list

        # smooth
        # kernelSize = 3
        # logger.info(f'put kernel size at user option, kernelSize: {kernelSize}')
        # diameter_um = self._results['diameter_um']
        # diameter_um_f = scipy.signal.medfilt(diameter_um, kernelSize)

        sumintensity = self._results["sumintensity"]
        # sumintensity_f = scipy.signal.medfilt(sumintensity, kernelSize)

        #
        self._results["minDiam"] = np.nanmin(diameter_um)
        self._results["maxDiam"] = np.nanmax(diameter_um)
        self._results["diamChange"] = (
            self._results["maxDiam"] - self._results["minDiam"]
        )
        #
        self._results["minSum"] = np.nanmin(sumintensity)
        self._results["maxSum"] = np.nanmax(sumintensity)
        self._results["sumChange"] = self._results["maxSum"] - self._results["minSum"]

        stopSeconds = time.time()
        durSeconds = round(stopSeconds - startSeconds, 2)
        logger.info(f"  analyzed {len(lineRange)} line scans in {durSeconds} seconds")

    def _getFitLineProfile(self, lineScanNumber: int, medianKernel: int):
        """Get one line profile.

        - Returns points
        - Get the full line, do not look at rect roi

        Args:
            medianKernel: Use 0 for no filtering
        """

        # TODO: want to get based on rect roi

        # we know the scan line, determine start/stop based on roi
        roiRect = self.getRoiRect()  # (l, t, r, b) in um and seconds (float)
        src_pnt_space = self.um2pnt(roiRect.getBottom())
        dst_pnt_space = self.um2pnt(roiRect.getTop())

        # intensityProfile will always have len() of number of pixels in line scane
        if self._lineWidth == 1:
            intensityProfile = self._filteredImage[lineScanNumber, :]

            # oct-7-2022
            intensityProfile = np.flip(intensityProfile)  # FLIPPED

            # intensityProfile = intensityProfile.astype(float)  # we need nan

        else:
            # FLIPPED
            src = (lineScanNumber, self.numPixels() - 1)
            dst = (
                lineScanNumber,
                0,
            )  # -1 because profile_line uses last pnt (unlike numpy)

            intensityProfile = profile.profile_line(
                self._filteredImage, src, dst, linewidth=self._lineWidth
            )

        # median filter line profile
        if medianKernel > 0:
            intensityProfile = scipy.signal.medfilt(intensityProfile, medianKernel)

        x = np.arange(0, len(intensityProfile) + 1)

        # Nan out before/after roi
        intensityProfile = intensityProfile.astype(float)  # we need nan
        intensityProfile[0:src_pnt_space] = np.nan
        intensityProfile[dst_pnt_space:] = np.nan

        # fwhm, left_idx, right_idx = self.FWHM(x, intensityProfile)

        # FWHM
        _intMax = np.nanmax(intensityProfile)
        half_max = _intMax * self._percentOfMax  # 0.2
        whr = np.asarray(intensityProfile > half_max).nonzero()
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

    def old_FWHM(self, X, Y):
        """
        see: https://stackoverflow.com/questions/10582795/finding-the-full-width-half-maximum-of-a-peak
        """
        # logger.info(f'_percentOfMax:{self._percentOfMax}')

        # Y = scipy.signal.medfilt(Y, 3)

        # half_max = max(Y) / 2.
        # half_max = max(Y) * 0.7
        half_max = np.nanmax(Y) * self._percentOfMax  # 0.2

        # for explanation of this wierd syntax
        # see: https://docs.scipy.org/doc/numpy/reference/generated/numpy.where.html
        # whr = np.where(Y > half_max)
        # print('   half_max:', half_max)
        whr = np.asarray(Y > half_max).nonzero()
        if len(whr[0]) > 2:
            # whr is (array,), only interested in whr[0]
            left_idx = whr[0][0]
            right_idx = whr[0][-1]
            fwhm = X[right_idx] - X[left_idx]
        else:
            left_idx = np.nan
            right_idx = np.nan
            fwhm = np.nan
        return fwhm, left_idx, right_idx  # return the difference (full width)


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
    print("sweepX:", type(sweepX), sweepX.shape)

    sumIntensity = ka.getResults("sumintensity")
    print("sumIntensity", type(sumIntensity), len(sumIntensity))
    axs[1].plot(ka.sweepX, sumIntensity)

    # TODO: Add filtering of diameter per line scan
    diameter_pnts = ka.getResults("diameter_pnts")
    axs[2].plot(ka.sweepX, diameter_pnts)

    plt.show()


if __name__ == "__main__":
    path = "/Users/cudmore/data/rosie/Raw data for contraction analysis/Female Old/filter median 1 C2-0-255 Cell 2 CTRL  2_5_21 female wt old.tif"
    ka = kymAnalysis(path)
    ka.analyze()

    # ka.saveAnalysis()

    # plotKym(ka)
    # plotKym_plotly(ka)
    # plotDash(ka)
