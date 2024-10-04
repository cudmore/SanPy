import time
import math
import os
from multiprocessing import Pool

import numpy as np
from skimage.measure import profile  # for profile_line()

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def roiLineProfileWorker(imgData, tmp):
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
    lineWidth = imgData.shape[1]
    numPixels = imgData.shape[0]
    
    if lineWidth == 1:
        intensityProfile = imgData[:,0]
        # intensityProfile = np.flip(intensityProfile)  # FLIPPED

    else:
        # intensityProfile will always have len() of number of pixels in line scane
        # -1 because profile_line uses last pnt (unlike numpy)

        # middleLine = math.floor(lineWidth/2)
        # src = (numPixels-1, middleLine)
        # dst = (0, middleLine)  # -1 because profile_line uses last pnt (unlike numpy)
        # intensityProfile = profile.profile_line(
        #     imgData, src, dst, linewidth=lineWidth
        # )

        intensityProfile = np.mean(imgData, axis=1)

    return intensityProfile

def roiLineProfilePool(imgData : np.ndarray, lineWidth : int):
    """
    Parameters
    ==========
    tifData : np.ndarry
        tif data slice to analyze
    lineWidth : int
        Must be odd
    """
    startTime = time.time()

    numLines = imgData.shape[1]

    logger.info(f'imgData:{imgData.shape} lineWidth:{lineWidth} numLines:{numLines}')  # tifData:(10000, 519)

    result_objs = []

    with Pool(processes=os.cpu_count() - 1) as pool:
        
        # add the workers
        for line in range(numLines):
            startLine = line - math.floor(lineWidth/2)
            if startLine < 0:
                startLine = 0
            # numpy uses (] indexing
            stopLine = line + math.floor(lineWidth/2) + 1
            if stopLine > numLines:
                stopLine = numLines

            imageSlice = imgData[:, startLine:stopLine]

            if line == 0:
                logger.info(f'line:{line} imageSlice:{imageSlice.shape}')

            workerParams = (imageSlice, None)
            
            result = pool.apply_async(roiLineProfileWorker, workerParams)
            result_objs.append(result)

        # run the workers - this HAS TO BE IN CONTEXT OF Pool()
        logger.info(f'   getting results from {len(result_objs)} workers')
        results = [result.get() for result in result_objs]

    # building only takes like 1 ms
    _outImg = np.empty_like(imgData)
    for _resultIdx, result in enumerate(results):
        _outImg[:,_resultIdx] = result

    stopTime = time.time()
    logger.info(f'  took {round(stopTime-startTime,3)} seconds')


    # results is a list of intensity profiles

    # stopTime2 = time.time()
    # logger.info(f'  building _outImg took {round(stopTime2-stopTime,3)} seconds')

    # logger.info(f'results len:{len(results)} results[0].shape:{results[0].shape}')

    return _outImg

def testPool():
    import tifffile
    
    # path = '/Users/cudmore/Dropbox/data/colin/sanAtp/ISAN Linescan 1.tif'
    
    # a kym with negative peaks
    path = '/Users/cudmore/Dropbox/data/colin/sanAtp/SSAN Linescan 8.tif'
    
    imgData = tifffile.imread(path)
    
    imgData = np.rot90(imgData)

    imgData = imgData[:, :, 1]

    left = 0
    top = 822
    right = 999
    bottom = 654
    roiImg = imgData[bottom:top, left:right]

    logger.info(f'imgData:{imgData.shape} roiImg:{roiImg.shape}')

    lineWidth = 3
    _outImg = roiLineProfilePool(roiImg, lineWidth=lineWidth)

    import matplotlib.pyplot as plt
    plt.imshow(_outImg)
    plt.show()

    # print('results[0]')
    # print(results[0])

if __name__ == '__main__':
    testPool()