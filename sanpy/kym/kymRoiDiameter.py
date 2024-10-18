import numpy as np
# from scipy.signal import peak_widths, medfilt, savgol_filter, detrend, find_peaks
from scipy.signal import medfilt

import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def backgroundSubtract(imgData):
    """Subtract median.
    """
    theMedian = np.median(imgData)
    retData = imgData - theMedian
    return retData

def detectKymRoiDiam(imgData,
                     doBackgroundSubtract,
                     lineWidth,
                     lineMedianKernel,
                     stdThreshold,
                     lineScanFraction = 4,
                     lineInterptMult = 1,
                     verbose = False
                     ):
    """
    Parameters
    ----------
    lineScanFraction : float
        Fraction of the line scan to look at left/right.

        2 will use middle (half), 4 will use 25% (1/4) , etc

    lineInterptMult : int
        Interpolate each line scan by this multiplyer (if 4, then we have 4x points along line).
        Default = 1 yields no interpolation.
        This reduces pixelation in diameter.
    """

    if doBackgroundSubtract:
        imgData = backgroundSubtract(imgData)

    if lineMedianKernel > 0:
        imgData = medfilt(imgData, lineMedianKernel)

    # middle bin in the line scan
    mLine = imgData.shape[0]
    firstQuarterBin = int(mLine/lineScanFraction)
    lastQuarterBin = mLine - int(mLine/lineScanFraction)

    m,n = imgData.shape

    #
    leftThresholdBinList = np.empty((n,))
    leftThresholdBinList[:] = np.nan  # [np.nan] * n
    # leftThresholdIntList = [np.nan] * n
    #
    rightThresholdBinList = np.empty((n,))
    rightThresholdBinList[:] = np.nan  # [np.nan] * n
    # rightThresholdIntList = [np.nan] * n

    if lineInterptMult > 1:
        firstQuarterBin *= lineInterptMult
        lastQuarterBin *= lineInterptMult

    for lineIdx in range(n):
        startLine = lineIdx - lineWidth
        if startLine < 0:
            startLine = 0
        endLine = lineIdx + lineWidth
        if endLine > n:
            endLine = n
            
        lineImg = imgData[:,startLine:endLine]
        lineImg = np.mean(lineImg, axis=1)

        # interpolate each line scan (this screws up our firstQauarterBin ???)
        if lineInterptMult > 1:
            # if lineIdx == 10:
            #     logger.info(f'before lineIdx:{lineIdx} lineInterptMult:{lineInterptMult} lineImg:{len(lineImg)}')

            _nIntensityProfile = len(lineImg)
            _xOld = np.linspace(0, _nIntensityProfile, num=_nIntensityProfile)
            _xNew = np.linspace(0, _nIntensityProfile, num=_nIntensityProfile*lineInterptMult)        
            lineImg = np.interp(_xNew, _xOld, lineImg)
        
            # if lineIdx == 10:
            #     logger.info(f'after lineIdx:{lineIdx} lineInterptMult:{lineInterptMult} lineImg:{len(lineImg)}')

        #
        # left
        startLineImg = lineImg[0:firstQuarterBin]

        leftLineMean = np.mean(startLineImg)
        leftLineSTD = np.std(startLineImg)
        leftThreshold = leftLineMean + (leftLineSTD * stdThreshold)

        leftThreshold_crossings = np.diff(startLineImg > leftThreshold, append=False)
        leftThresholdBins = np.where(leftThreshold_crossings==1)[0]
        if len(leftThresholdBins) == 0:
            if verbose:
                logger.error(f'lineIDx:{lineIdx} --> no left threshold')
        else:
            leftThresholdBin = leftThresholdBins[0]  # from left to right, first threshold crossing
            # leftThresholdInt = startLineImg[leftThresholdBin]

            leftThresholdBinList[lineIdx] = leftThresholdBin
            # leftThresholdIntList[lineIdx] = leftThresholdInt

        #
        # right
        endLineImg = lineImg[lastQuarterBin:]
        
        rightLineMean = np.mean(endLineImg)
        rightLineSTD = np.std(endLineImg)
        rightThreshold = rightLineMean + (rightLineSTD * stdThreshold)

        rightThreshold_crossings = np.diff(endLineImg > rightThreshold, append=False)
        rightThresholdBins = np.where(rightThreshold_crossings==1)[0]
        if len(rightThresholdBins) == 0:
            if verbose:
                logger.error(f'lineIDx:{lineIdx} --> no right threshold')
        else:
            rightThresholdBin = rightThresholdBins[-1]  # from right to right, last threshold crossing
            # rightThresholdInt = endLineImg[rightThresholdBin]

            rightThresholdBin += lastQuarterBin  # we started in the middle

            rightThresholdBinList[lineIdx] = rightThresholdBin
            # rightThresholdIntList[lineIdx] = rightThresholdInt

    # might want a final medfilt on the diameter?
    diamBins = np.subtract(rightThresholdBinList, leftThresholdBinList)

    # not needed here, just interesting
    sumIntensity = np.sum(imgData, axis=0)

    if lineInterptMult > 1:
        # leftThresholdBinList = [_bin / lineInterptMult for _bin in leftThresholdBinList]
        leftThresholdBinList /= lineInterptMult
        #
        # rightThresholdBinList = [_bin / lineInterptMult for _bin in rightThresholdBinList]
        rightThresholdBinList /= lineInterptMult
        #
        # diamBins = [_bin / lineInterptMult for _bin in diamBins]
        diamBins /= lineInterptMult


    return leftThresholdBinList, rightThresholdBinList, diamBins, sumIntensity

def plotKyn(imgData, leftThresholdBinList, rightThresholdBinList, diamBins, sumIntensity=None):
    """Plot kym with left diameter.
    """
    xLines = np.arange(imgData.shape[1])

    fig, axs = plt.subplots(2, 1, sharex=True)
    
    # imgData = np.flip(imgData)  # flip for matplotlib

    axs[0].imshow(imgData, aspect='auto')
    axs[0].plot(xLines, leftThresholdBinList, 'g')
    axs[0].plot(xLines, rightThresholdBinList, 'r')

    axs[1].plot(diamBins, label='Diameter (bins)')
    axs[1].set_ylabel('Diameter (bins)')

    if sumIntensity is not None:
        axs2 = axs[1].twinx() 
        axs2.plot(sumIntensity, 'k', label='sum')
        axs2.set_ylabel('Sum Intensity')

    plt.show()

def plotLine(lineImg, lineMean, lineSTD, threshold, thresholdBin, thresholdInt):
    """Plot one line scan.
    """
    n = len(lineImg)
    
    plt.plot(lineImg)
    plt.hlines(lineMean, xmin=0, xmax=n)
    plt.hlines(lineMean+lineSTD, xmin=0, xmax=n, linestyles='dotted')
    plt.hlines(lineMean+2*lineSTD, xmin=0, xmax=n, linestyles='dotted')
    plt.hlines(threshold, xmin=0, xmax=n, colors='r', linestyles='dotted')
    plt.plot(thresholdBin, thresholdInt, 'or')

    plt.show()

if __name__ == '__main__':
    from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis

    path = '/Users/cudmore/Dropbox/data/cell-shortening/paula/cell01_C002T001.tif'
    kra = KymRoiAnalysis(path)
    roi = kra.getRoi('1')
    roiImg = roi.getRoiImg()  # get imgData within ROI

    doBackgroundSubtract = True
    lineMedianKernel = 3
    lineWidth = 1  # 2  # don't go too big (filters too much)
    stdThreshold = 1.2  # 1.8
    lineInterptMult = 4  # 0  # interpolate each line scan by this multiplyer
    lineScanFraction = 4 # 2 # percent of line scan to detect for onset/offset
        # if 2 then half/half
        # if 4 then first/last 25%

    leftThresholdBinList, rightThresholdBinList, diamBins, sumIntensity = \
        detectKymRoiDiam(roiImg,
                     doBackgroundSubtract=doBackgroundSubtract,
                     lineWidth=lineWidth,
                     lineMedianKernel=lineMedianKernel,
                     lineInterptMult=lineInterptMult,
                     stdThreshold=stdThreshold,
    )

    plotSumIntensity = None
    plotKyn(roiImg, leftThresholdBinList, rightThresholdBinList, diamBins, sumIntensity=plotSumIntensity)
