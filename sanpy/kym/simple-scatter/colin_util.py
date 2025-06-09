import sys
import os

import numpy as np
import pandas as pd

import roifile  # to import Fiji roi manager zip files

import matplotlib.pyplot as plt

from sanpy.analysisDir import _walk
from sanpy.bAnalysis_ import bAnalysis
from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, PeakDetectionTypes

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def _getRawTifDict():
    # myAnalysisFolder = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/renamed-20250521'

    from colin_global import getAllTifFilePaths
    rawTifList = getAllTifFilePaths()

    # theseFileTypes = '.tif'
    # rawTifList = _walk(myAnalysisFolder, theseFileTypes=theseFileTypes, depth=5)
    # rawTifList = list(rawTifList)

    rawTifFiles = [os.path.split(x)[1] for x in rawTifList]
    # make a dict of list, keys are tif file and list is list of roi rects
    masterDict = {}
    for rawTifFile in rawTifFiles:
        masterDict[rawTifFile] = []

    return masterDict, rawTifList

def loadRoiFile(masterDict, oneZipFile) -> dict:
    # grab a list of all raw tif file

    _path, _zipFile = os.path.split(oneZipFile)
    # the _parentFolder is (isan, ssan)
    # this is dependent on colins folder structue (very brittle')
    _path, _regionFolder = os.path.split(_path)
    _dateFolder = os.path.split(_path)[1]
    logger.info(f'_dateFolder:{_dateFolder}')  # should be (isan, ssan)
    logger.info(f'_regionFolder:{_regionFolder}')  # should be (isan, ssan)
    logger.info(f'_zipFile:{_zipFile}')  # should be (isan, ssan)

    # if _dateFolder == '250225':
    #     dateStr = '20250225'
    # else:
    #     logger.error(f'did not find matching data folder for "{_dateFolder}')

    logger.info('loading roi zip:')
    print(f'  {oneZipFile}')

    fijiRoiList = roifile.roiread(oneZipFile)
    print(f'  loaded {len(fijiRoiList)} Fiji rois')
    # read_roi_zip(oneZipFile)

    # logger.info(f'roi_dict is:')
    # pprint(roiDict, indent=2)

    for roi in fijiRoiList:
        # top/bottom correspond to line scans
        # left/right correspond to line scan points

        # [left, top, right, bottom]
        # TODO: check for overflow (out of bounds) !!!!
        left = roi.left
        top = roi.top
        right = roi.right
        bottom = roi.bottom
        
        # colin is specifying a 1-2 pixel roi with a stroke with
        # this will expand left/right
        stroke_width = roi.stroke_width

        half_stroke_width = stroke_width // 2
        left -= half_stroke_width
        right += half_stroke_width

        # our final roi rect [l, t, r, b]
        # roiRect = [left, top, right, bottom]

        # roi/kym image is rotated in Fiji versus SanPy
        # left->bottom, top->left, right->top, bottom->right
        # sanpyRect = [top, right, bottom, left]
        # top is bigger than bottom
        # sanpyRect = [top, left, bottom, right]
        
        # up till 20250530
        # in sanpy, top has to be bigger than bottom !!!
        sanpyRect = [top, right, bottom, left]  # l/t/r/b
        
        # new 20250530
        # sanpyRect = [top, left, bottom, right]  # l/t/r/b

        roiName = roi.name
        
        # roi.name is like
        # "R1 LS1 Control Mode 1"
        # "R1 LS1 Control Mode 1_2"

        # search for (c, i, t) in roiName
        # logger.info(f'searching roiName:"{roiName}"')

        _conditionStr = ''
        if 'Control' in roiName:
            # print(f'  {roiName} is "Control"')
            roiCondStr = 'Control'
            myCondStr = "c1"
        elif 'Ivabradine' in roiName:
            # print(f'  {roiName} is "Ivabradine"')
            roiCondStr = 'Ivabradine'
            myCondStr = "c2 Ivab"
        elif 'Thapsigargin' in roiName:
            # print(f'  {roiName} is "Thapsigargin"')
            roiCondStr = 'Thapsigargin'
            myCondStr = "c3 Thap"

        else:
            logger.error(f'  DID NOT FIND (c, i, t) in roi name: "{roiName}"')
            continue

        # logger.info(f'  _conditionStr:{_conditionStr}')

        # find the corresponding file
        # we are in (isan, ssan) folder
        # roiName is like:
        #  "R1 LS1 Control Mode 1"
        #  "R1 LS1 Control Mode 1_2"
        # "R1 LS1 Ivabradine Mode 1"
        # corresponding tif file is like: "ISAN R1 LS2.tif.frames" -> ISAN R1 LS2.tif
        # my renamed tif file is like:
        #  "250225 ISAN R1 LS1 c1"
        #  "250225 ISAN R2 LS2 c2 Ivab"
        #  "250225 ISAN R2 LS2 c3 Thap"

        truncIdx = roiName.index(roiCondStr)
        roiBaseName = roiName[0:truncIdx-1]  # -1 to get rid of trailing space
        
        myTifFile = f'{_dateFolder} {_regionFolder} {roiBaseName} {myCondStr}.tif'

        # find tif file name in list of tif paths
        # try:
        #     index = rawTifFiles.index(myTifFile)
        # except ValueError:
        #     logger.error(f'did not find my tif file "{myTifFile} in list')
        #     continue

        # append roi to masterDict list
        if myTifFile not in masterDict.keys():
            logger.error(f'did not find tif file key "{myTifFile}" in masterDict')
            continue
        
        masterDict[myTifFile].append(sanpyRect)

        # print(f'myTifFile:"{myTifFile}" index:{index}')
        # print(f'  roiName:"{roiName}" stroke_width:{stroke_width} ltrb:{roiRect} sanpyRect:{sanpyRect}')

        # break

    return masterDict

    # Access individual ROIs
    # for name, roi in roi_dict.items():
    #     print(f"ROI Name: {name}")
    #     print(roi.roitype)
    #     print(roi.left)
    #     print(roi.top)
        
def makeRoiDictFromZips():
    masterDict, rawTifList = _getRawTifDict()
    
    # TODO: recurisvely walk folder and find .zip files
    rootPath = '/Users/cudmore/Dropbox/data/colin/2025/roi manager - 20250520'

    zipList = [
        '250225/ISAN/20250225 ISAN RoiSet.zip',
        '250225/SSAN/20250225 SSAN RoiSet.zip',

        '250304/ISAN/20250304 ISAN RoiSet.zip',  # changed name SSAN->ISAN
        '250304/SSAN/20250304 SSAN RoiSet.zip',

        '250318/ISAN/20250318 ISAN RoiSet.zip',
        '250318/SSAN/20250318 SSAN RoiSet.zip',
    ]

    for oneZip in zipList:
        oneZipFile = os.path.join(rootPath, oneZip)
        masterDict = loadRoiFile(masterDict, oneZipFile)
    
    # check if any tif file keys have empty list (no roi)
    for k,v in masterDict.items():
        if len(v)==0:
            logger.error(f'did not get any rois for tif file "{k}"')

    #pprint(masterDict, indent=4)
    return masterDict, rawTifList

def insertRoiIntoSanPy():
    """Load all of Colins Fiji roi manager zip files and recreate SanPy analysis.
    
    DOES PEAK DETECTION ON NEWLY INSERTED ROIs

    Important:
        When we load previous SanPy peaks and then detect no peaks -->> do we save no peaks ???
    """
    
    logger.info('making master dict')
    masterDict, rawTifList = makeRoiDictFromZips()

    for tifIdx, rawTifPath in enumerate(rawTifList):
        tifFile = os.path.split(rawTifPath)[1]
        print(f'=== === {tifIdx} of {len(rawTifList)} is {tifFile}')

        # load tif as bAnalysis (does proper rotation)
        ba = bAnalysis(rawTifPath)
        imgData = ba.fileLoader._tif  # list of color channel images
        # logger.info(f'imgData:{imgData[0].shape} {np.min(imgData[0])} {np.max(imgData[0])} {np.mean(imgData[0])}')

        # TODO: maybe just throw out all SanPy peak analysis in xxx
        # in files like 250225 ISAN R2 LS2 c2 Ivab-ch0-roiPeaks.csv

        # 20250523 THROW OUT ALL (roiPeaks.csv and roiTraces.csv)

        # this will load my previous analysis (just one roi)
        ka = KymRoiAnalysis(rawTifPath, imgData=imgData)
                            
        # delete existing rois
        roiLabels = ka.getRoiLabels()
        for roiLabel in roiLabels:
            existingRoiRect = ka.getRoi(roiLabel).getRect()
            # top is bigger than bottom, imgdata has (0,0) in bottom left
            logger.info(f'  DELETIING ROI {roiLabel} existingRoiRect is:{existingRoiRect}')
            ka.deleteRoi(roiLabel)

        # add all rois from fiji
        for idx, fijiRoi in enumerate(masterDict[tifFile]):
            print(f'  ADDING FIJI ROI roi {idx+1} tifFile: "{tifFile}" fijiRoi:{fijiRoi}')
            newRoi = ka.addROI(fijiRoi)

            # check the added roi rect
            # seems to be good, it is properly clipping based on Colins out of bounds rects
            addedRect = newRoi.getRect()
            print(f'    added from FIJI rect is:{addedRect}')
        
        # peak detect each roi (each new roi from fiji)
        if 1:
            for roiLabel in ka.getRoiLabels():
                kymRoi = ka.getRoi(roiLabel)
                
                # set prominence in detection
                kymRoiDetection = kymRoi.getDetectionParams(0, PeakDetectionTypes.intensity)
                # _ok = kymRoiDetection.setParam('Prominence', 1.2)
                # 20250529
                _ok = kymRoiDetection.setParam('Prominence', 1.6)
                if _ok is None:
                    logger.error('Prominence')
                    sys.exit(1)

                # 20250608 detect 'Divided'
                _ok = kymRoiDetection.setParam('detectThisTrace', 'Divided')
                if _ok is None:
                    logger.error('detectThisTrace')
                    sys.exit(1)

                kymRoi.peakDetect(channel=0, peakDetectionType=PeakDetectionTypes.intensity)

        # print(f'ka.path:{ka.path}')
        # print(f'ka._path:{ka._path}')
        # break

        # check we got the analysis results
        # for roiLabel in ka.getRoiLabels():
        #     ar = ka.getAnalysisResults(roiLabel, PeakDetectionTypes.intensity, channel=0)
        #     print(f"  === analysis results for roiLabel:{roiLabel}")
        #     print(ar.df['Peak Height'])

        # save the analysis
        logger.info(f'SAVING ANALYSIS {tifFile} with {ka.numRoi} rois')
        ka.saveAnalysis()

        #
        # break
        # if tifIdx > 1:
        #     break

def checkRoiPerCondition():
    """Check that each (cell id, condition) has the same number of 'ROI Number'
    
    If this is not true -->> problems !!!

    We are getting different number of roi per (id, condition)
        -->> remake my master df by throwing out all previous sanpy csv analysis
    """
    # savePath = '/Users/cudmore/colin_peak_mean_20250521.csv'
    # df = pd.read_csv(savePath)
    
    from colin_global import loadMeanDfFile
    df = loadMeanDfFile()

    cellIDs = df['Cell ID'].unique()
    for cellID in cellIDs:
        print(cellID)
        dfCellID = df[df['Cell ID']==cellID]
        conditions = dfCellID['Condition'].unique()
        # logger.info(f'cellID:{cellID} has conditions:{conditions}')
        for idx, condition in enumerate(conditions):
            dfCondition = dfCellID[dfCellID['Condition']==condition]
            rois = dfCondition['ROI Number'].unique()
            print(f'  cellID:{cellID} condition:{condition} num:{len(rois)} rois:{rois}')

if __name__ == '__main__':
    if 0:
        masterDict = makeRoiDictFromZips()
        numRoi = 0
        for k,v in masterDict.items():
            _numRoi = len(v)
            if _numRoi == 0:
                logger.error('did not find any rois for {k}')
            numRoi += _numRoi
        logger.info(f'masterDict has {len(masterDict)} tif files and {numRoi} rois')

    # load all Colin's fiji roi manager and recreate ALL sanpy analysis
    if 1:
        insertRoiIntoSanPy()

    # _throwOutAllSanPyAnalysis()

    # works
    # check that each (Cell ID, Condition) has the same number of ROI
    if 0:
        checkRoiPerCondition()

    # test_load_roi()