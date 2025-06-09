"""
Compare sum intensity for
    - f/f0
    - f_divide
"""
import os
import numpy as np
import matplotlib.pyplot as plt

from sanpy.bAnalysis_ import bAnalysis
from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis  # , KymRoi

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def test_sum():
    rootPath = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/sanpy-20250530'
    tifPath = '250225/ISAN/ISAN Ivabradine R1 LS1.tif.frames/250225 ISAN R1 LS1 c2 Ivab.tif'
    tiffPath = os.path.join(rootPath, tifPath)
    _tifPath, _tifFile = os.path.split(tiffPath)

    # given a tif path, load with bAnalysis
    ba = bAnalysis(tiffPath)
    imgData = ba.fileLoader.tifData

    # load kymRoiAnalysis from path and imgData
    kymRoiAnalysis = KymRoiAnalysis(tiffPath, imgData)

    # for each roi in kymRoiAnalysis, get (df/f0, f/f0, f_divide)
    channel = 0
    
    numRoi = kymRoiAnalysis.numRoi
    # make subplots, one for each roi

    fig, axs = plt.subplots(numRoi, 1, sharex=True, sharey=True, figsize=(8, 6))
    if numRoi==0:
        axs = [axs]
    fig.suptitle(_tifFile)

    # traces = ['df/f0', 'f/f0', 'Divided']
    traces = ['f/f0', 'Divided']

    # for now we have one norm for kymAnalysis (across all roi)
    santanaLineScanNorm = kymRoiAnalysis.getKymDetectionParam('santanaLineScanNorm')
    for roiIdx, roi in enumerate(kymRoiAnalysis):
        print(f'{type(roi)} roi:{roi}')
        xPlot, yRaw, dividedInt = roi.getSumIntensity(channel)  # does background subtraction

        divideLine_sec = roi._lineToSecond(santanaLineScanNorm)

        # get traces from roi
        for trace in traces:
            traceData = roi.getTrace(channel, trace)
            # if trace == 'Divided':
            #     logger.warning(f'{trace} {traceData.shape} {traceData.dtype} {traceData.min()} {traceData.max()}')

            axs[roiIdx].plot(xPlot, traceData, linewidth=1, label=trace)
            # vertical line for divideLine_sec
            axs[roiIdx].axvline(divideLine_sec, color='red', linestyle='--')
            axs[roiIdx].legend()
            axs[roiIdx].set_title(f'roi:{roiIdx}')
    
    plt.show()


if __name__ == '__main__':
    test_sum()

