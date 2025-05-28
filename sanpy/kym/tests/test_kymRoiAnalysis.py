from sanpy.fileloaders import fileLoader_tif
from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, PeakDetectionTypes
from sanpy.kym.kymRoiDetection import KymRoiDetection

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def testKymRoi(path):
    # test add, delete, and iterator
    flt = fileLoader_tif(path)
    imgData = flt._tif  # list of color channel images

    kymRoiAnalysis = KymRoiAnalysis(path, imgData)

    logger.info(f'=== 0 roi: kymRoiAnalysis.numRoi:{kymRoiAnalysis.numRoi}')
    for kymRoi in kymRoiAnalysis:
        print(kymRoi)

    kymRoiAnalysis.addROI()
    logger.info(f'=== 1 roi: kymRoiAnalysis.numRoi:{kymRoiAnalysis.numRoi}')
    for kymRoi in kymRoiAnalysis:
        print(kymRoi)

    ltrb = [0, 30, 1000, 0]
    kymRoiAnalysis.addROI(ltrb)
    logger.info(f'=== 2 roi: kymRoiAnalysis.numRoi:{kymRoiAnalysis.numRoi}')
    for kymRoi in kymRoiAnalysis:
        print(kymRoi)

    kymRoiAnalysis.deleteRoi("5")
    for kymRoi in kymRoiAnalysis:
        print(kymRoi)

    kymRoiAnalysis.deleteRoi("1")
    for kymRoi in kymRoiAnalysis:
        print(kymRoi)

    ltrb = [100, 60, 900, 12]
    kymRoiAnalysis.addROI(ltrb)
    logger.info(f'=== 2 roi: kymRoiAnalysis.numRoi:{kymRoiAnalysis.numRoi}')
    for kymRoi in kymRoiAnalysis:
        print(kymRoi)

    _badRoi = kymRoiAnalysis.getRoi('12')
    print(f'_badRoi:{_badRoi}')

def testKymSaveLoad(path):
    flt = fileLoader_tif(path)
    imgData = flt._tif  # list of color channel images

    kra = KymRoiAnalysis(path, imgData)

    ltrb = [0, 30, 1000, 0]
    roi = kra.addROI(ltrb)

    kra.saveAnalysis()

    logger.info('TEST LOAD ===')
    kra2 = KymRoiAnalysis(path, imgData)
    kra2.loadAnalysis()

def _old_testKymRoiAnalysis(path):

    flt = fileLoader_tif(path)
    imgData = flt._tif  # list of color channel images
    # imgData = imgData[0]

    kra = KymRoiAnalysis(path, imgData)

    # add an empty roi
    roi = kra.addROI()
    logger.info('added roi:{roi}')

    # add a specific roi
    ltrb = [0, 30, 1000, 0]
    roi = kra.addROI(ltrb)
    logger.info('added roi:{roi}')

    numChannels = kra.numChannels
    for channel in range(numChannels):        
        logger.info(f'   DETECTING channel:{channel} === === ===')
        
        # detect peak in PeakDetectionTypes.f_f0
        roi.peakDetect(channel)

        f_f0_DetectionParams = roi.getDetectionParams(channel, PeakDetectionTypes.f_f0)
        for backgroundType in KymRoiDetection.backgroundSubtractTypes:
            logger.info(f'backgroundType:{backgroundType}')
            f_f0_DetectionParams['Background Subtract'] = backgroundType
            roi.peakDetect(channel, f_f0_DetectionParams)
            # print(f"f_f0_DetectionParams backgroundSubtractValue:{f_f0_DetectionParams['backgroundSubtractValue']}")

        # detect diameter in the image
        roi.detectDiam(channel)

        #
        diamDetectionParams = roi.getDetectionParams(channel, PeakDetectionTypes.diameter)

        for polarity in ['Pos', 'Neg']:
            logger.info(f'polarity:{polarity}')
            diamDetectionParams['Polarity'] = polarity
            roi.peakDetect(channel, diamDetectionParams)

        for backgroundType in KymRoiDetection.backgroundSubtractTypes:
            logger.info(f'backgroundType:{backgroundType}')
            diamDetectionParams['Background Subtract'] = backgroundType
            roi.peakDetect(channel, diamDetectionParams)
            # print(f"backgroundSubtractValue:{diamDetectionParams['backgroundSubtractValue']}")

if __name__ == '__main__':
    path = '/Users/cudmore/Desktop/retreat-sept-2024/SSAN Linescan 12.tif'
    # path = '/Users/cudmore/Dropbox/data/cell-shortening/paula/cell01_C002T001.tif'
    
    # testKymRoiAnalysis(path)
    testKymSaveLoad(path)
    testKymRoi(path)