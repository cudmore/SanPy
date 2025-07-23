import sys
import os
import time
from pprint import pprint

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Any, Optional, Tuple
import pathlib
from datetime import datetime
import warnings
from scipy import stats
from scipy.stats import mannwhitneyu, ttest_ind, pearsonr, spearmanr

import roifile  # to import Fiji roi manager zip files

from colin_global import getAllTifFilePaths, FileInfo

from sanpy.bAnalysis_ import bAnalysis
from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, PeakDetectionTypes

from sanpy.kym.simple_scatter.colin_global import fijiConditions

from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


def _getRawTifDict():
    """Grab a list of all raw tif file and a list of all rois

    Returns
    -------
    masterDict is a dict of list, keys are tif file and list is list of roi rects
    rawTifList is a list of raw tif file paths
    """
    rawTifList = getAllTifFilePaths()

    rawTifFiles = [os.path.split(x)[1] for x in rawTifList]
    # make a dict of list, keys are tif file and list is list of roi rects
    masterDict = {}
    for rawTifFile in rawTifFiles:
        # 20250612, masterDict was list [], now is dict
        masterDict[rawTifFile] = {
            'sanpyRoiRects': [],
            'fijiRoiRects': [],
            'Region': '',
            'Cell ID': '',
            'Condition': '',
            'ROI Number': [],
            'Fiji ROI Name': [],
            'Mode': [],  # mode 1/2
        }

    return masterDict, rawTifList


# abb 20250617
def _parseFijiRoiName(
    fijiRoiName: str,
    dateFolder: str,
    regionFolder: str,
    fijiRoiRect: list,
    sanpyRoiRect: list,
) -> dict:
    """Parse Colins Fiji roi name from RoiManager zip file
        and return a dict of the roi info

    we get date and region from original folder path.

    trailing _1, _2, _3, ... are ROIs
    """
    # 20250602 SSAN Control R1 LS1 Mode 1_1
    # 20250602 SSAN Control R2 LS1_0001 Mode 1_1
    # 20250602 SSAN Control R2 LS1_0002 Mode 1_1
    # 20250602 SSAN Control R2 LS1_0003 Mode 1_1  # the final one is 'Control'

    # ISAN Control R1 LS1 Mode 1_1
    # 20250331 ISAN R1 LS1.tif
    logger.info(f'parsing fijiRoiName:{fijiRoiName}')

    roiName2 = fijiRoiName.replace(f'{dateFolder} ', '')
    roiName2 = roiName2.replace(f'{regionFolder} ', '')
    # now "Control R1 LS1 Mode 1_1"

    retDict = {
        'fijiRoiName': fijiRoiName,
        'Date': dateFolder,
        'Region': regionFolder,
        'Fiji ROI Condition': '',
        'Sanpy ROI Condition': '',  # different from final condition based on _000n
        # 'Fiji Repeat Number': '',
        'Fiji ROI Number': '',  # from trailing _n where n is integer
        'Epoch': None,  # first epoch _0000 will not have epoch (epoch 0)
        'Mode': '',
        'Polarity': '',
        'fijiRoiRect': fijiRoiRect,
        'sanpyRoiRect': sanpyRoiRect,
        'tifFileName': '',
    }

    for cond in fijiConditions:
        # cond is sanpy short name (Control, Ivab, Thap)
        if cond in roiName2:
            roiName2 = roiName2.replace(f'{cond} ', '')
            fijiCond = cond
            retDict['Fiji ROI Condition'] = fijiCond
            if fijiCond == 'Ivabradine':
                retDict['Sanpy ROI Condition'] = 'Ivab'
                sanpyCond = 'Ivab'
            elif fijiCond == 'Thapsigargin':
                retDict['Sanpy ROI Condition'] = 'Thap'
                sanpyCond = 'Thap'
            # abb 20250623 mito atp
            elif fijiCond == 'FCCP':
                retDict['Sanpy ROI Condition'] = 'FCCP'
                sanpyCond = 'FCCP'
            elif fijiCond == 'Control':
                retDict['Sanpy ROI Condition'] = 'Control'
                sanpyCond = 'Control'

            else:
                logger.warning(f'did not find condition in fijiRoiName:"{fijiRoiName}"')
                retDict['Sanpy ROI Condition'] = 'Control'
                sanpyCond = 'Control'

            break

    # two types of mode ('Mode 1', Mode 2')
    for modeIdx, mode in enumerate(['Mode 1', 'Mode 2']):
        if mode in roiName2:
            roiName2 = roiName2.replace(f'{mode}', '')  # no space after mode
            retDict['Mode'] = mode
            retDict['Polarity'] = 'Pos' if modeIdx == 0 else 'Neg'
            break

    # find _000n where n is an integer
    retDict['Epoch'] = 0  # default to 0 (there is never _0000)
    for epochNumber in range(10):
        epochNumberStr = f'_{str(epochNumber).zfill(4)}'
        if epochNumberStr in roiName2:
            roiName2 = roiName2.replace(epochNumberStr, '')
            # for a given condition, different repeats
            # the first kym will not have this !!!
            retDict['Epoch'] = epochNumber
            break

    # the trailing _n where n is integer is the ROI number
    # we need to get the ROI number
    # logger.info(f'roiName2:{roiName2}')  # is "R1 LS1 _1"
    roiNumberStr = roiName2.split('_')[-1]  # TODO: will not work for roi numbeer >= 10
    retDict['Fiji ROI Number'] = roiNumberStr
    roiName2 = roiName2.replace(f'_{roiNumberStr}', '')

    # renamed tif is like: 20250602 ISAN R1 LS3 Control Epoch 1
    # logger.info(f'using roiName2:"{roiName2}"')
    if sanpyCond == 'Control':
        if dateFolder == '20250509':
            tifFileName = f'{dateFolder} {regionFolder} {sanpyCond} {roiName2}'
        else:
            tifFileName = f'{dateFolder} {regionFolder} {roiName2}'
    else:
        # 20250331 ISAN R1 LS1 FCCP.tif
        # 20250331 ISAN FCCP R1 LS2.tif
        tifFileName = f'{dateFolder} {regionFolder} {sanpyCond} {roiName2}'

    if retDict["Epoch"] > 0:
        tifFileName += f' Epoch {retDict["Epoch"]}'
    tifFileName = tifFileName.replace('  ', ' ')
    # if tifFileName ends in ' ' then remove it
    if tifFileName.endswith(' '):
        tifFileName = tifFileName[:-1]
    tifFileName += '.tif'
    retDict['tifFileName'] = tifFileName
    # logger.info(f'renamed tif is like:"20250602 ISAN R1 LS3 Control Epoch 1"')
    # logger.info(f'     tifFileName is:"{tifFileName}')
    # tifFileName is:"20250602 ISAN R1 LS1  Control Epoch 0
    # sys.exit(1)

    return retDict


def loadRoiFile(masterDict, oneZipFile) -> pd.DataFrame:
    """Grab a list of all raw tif file and a list of all rois

    Returns
    -------
    df is a df of roi info
    masterDict is a dict of dict, keys are tif file and dict is dict of roi info
    """

    _path, _zipFile = os.path.split(oneZipFile)
    # the _parentFolder is (isan, ssan)
    # this is dependent on colins folder structue (very brittle')
    _path, _regionFolder = os.path.split(_path)
    _dateFolder = os.path.split(_path)[1]

    # logger.info(f'_dateFolder:{_dateFolder}')  # should be (isan, ssan)
    # logger.info(f'_regionFolder:{_regionFolder}')  # should be (isan, ssan)
    # logger.info(f'_zipFile:{_zipFile}')  # should be (isan, ssan)

    # if _dateFolder == '250225':
    #     dateStr = '20250225'
    # else:
    #     logger.error(f'did not find matching data folder for "{_dateFolder}')

    logger.info('loading roi zip:')
    print(f'  {oneZipFile}')

    fijiRoiList = roifile.roiread(oneZipFile)
    logger.info(f'  loaded {len(fijiRoiList)} Fiji rois')
    # read_roi_zip(oneZipFile)

    # logger.info(f'roi_dict is:')
    # pprint(roiDict, indent=2)

    roiInfoList = []

    for fijiRoiNumber, roi in enumerate(fijiRoiList):
        # top/bottom correspond to line scans
        # left/right correspond to line scan points

        # [left, top, right, bottom]
        # TODO: check for overflow (out of bounds) !!!!
        left = roi.left
        top = roi.top
        right = roi.right
        bottom = roi.bottom

        fijiRoiRect = [left, top, right, bottom]

        # colin is specifying a 1-2 pixel roi with a stroke with
        # this will expand left/right
        stroke_width = roi.stroke_width

        half_stroke_width = stroke_width // 2
        left -= half_stroke_width
        right += half_stroke_width

        # up till 20250530
        # in sanpy, top has to be bigger than bottom !!!
        sanpyRect = [top, right, bottom, left]  # l/t/r/b

        # "20250602 SSAN Control R1 LS1 Mode 1_1"
        fijiRoiName = roi.name
        # logger.info(f'fijiRoiName:"{fijiRoiName}"')

        # handle some bad roi names
        # 20250602 SSAN Control R2 LS1_0002 Mode 1_1 -> 20250602 SSAN Control R2 LS1_0001 Mode 1_2
        # 20250602 SSAN Control R2 LS1_0003 Mode 1_1 -> 20250602 SSAN Control R2 LS1_0001 Mode 1_3
        if fijiRoiName == "20250602 SSAN Control R2 LS1_0002 Mode 1_1":
            fijiRoiName = "20250602 SSAN Control R2 LS1_0001 Mode 1_2"
        elif fijiRoiName == "20250602 SSAN Control R2 LS1_0003 Mode 1_1":
            fijiRoiName = "20250602 SSAN Control R2 LS1_0001 Mode 1_3"

        roiInfoDict = _parseFijiRoiName(
            fijiRoiName, _dateFolder, _regionFolder, fijiRoiRect, sanpyRect
        )
        logger.info(f'roiInfoDict:')
        pprint(roiInfoDict, indent=4)

        # check if we can match fiji roi name with a raw tif file
        tifFileName = roiInfoDict['tifFileName']

        # badRoiName = "20250602 SSAN Control R2 LS1"
        # if badRoiName in fijiRoiName:
        #     logger.warning(f'potentialls bad fijiRoiName:"{fijiRoiName}"')

        if tifFileName not in masterDict.keys():
            # 20250602 SSAN Control R2 LS1_0002 Mode 1_1
            # 20250602 SSAN Control R2 LS1_0003 Mode 1_1
            # find all items in masterDict.keys() that match "20250602 SSAN R2 LS1 Control"
            _tifList = masterDict.keys()
            for _tif in _tifList:
                if '20250602 SSAN R2 LS1 Control' in _tif:
                    # 20250602 SSAN R2 LS1 Control.tif
                    # 20250602 SSAN R2 LS1 Control Epoch 1.tif
                    print(_tif)

            logger.error(f'  fijiRoiName:"{fijiRoiName}"')
            logger.error('  did not find roi')
            logger.error(f'  tifFileName "{tifFileName}" in masterDict keys')
            
            for _x in masterDict.keys():
                print(f'  {_x}')
            sys.exit(1)

        #
        # before we append, make sure we matched roi name with a tif file
        roiInfoList.append(roiInfoDict)

    # make a df from roiInfoList
    df = pd.DataFrame(roiInfoList)
    logger.info(f'df has {len(df)} rows (one row per fiji roi)')
    # pprint(df, indent=4)

    return df


def test_loadRoiFile():
    dfRoi, roiDict, tifList = makeRoiDictFromZips2()

    # roiTifList = dfRoi['tifFileName'].unique()
    # for tifPath in tifList:
    #     tifFile = os.path.split(tifPath)[1]
    #     if tifFile not in roiTifList:
    #         logger.error(f'did not find tif file "{tifFile}" in roi dfMaster')

    logger.info(f'df has {len(dfRoi)} rows (one row per fiji roi)')


def makeRoiDictFromZips2() -> tuple[pd.DataFrame, dict, list]:
    """While starting analysis for mito atp."""

    masterDict, rawTifList = _getRawTifDict()

    from colin_global import _ROOT_ANALYSIS_FOLDER, _walk

    zipPaths = _walk(_ROOT_ANALYSIS_FOLDER, '.zip', 5)
    zipPaths = list(zipPaths)
    zipPaths = [z for z in zipPaths if 'RoiSet.zip' in z]

    for zipIdx, oneZipPath in enumerate(zipPaths):
        print(f'zipIdx:{zipIdx} of {len(zipPaths)}')
        print(oneZipPath)

        dfOne = loadRoiFile(masterDict, oneZipPath)
        if zipIdx == 0:
            dfMaster = dfOne
        else:
            dfMaster = pd.concat([dfMaster, dfOne])

    # check if any tif file keys have empty list (no roi)
    # for k,v in masterDict.items():
    #     if len(v['sanpyRoiRects'])==0:
    #         logger.error(f'did not get any rois for tif file "{k}"')

    # pprint(masterDict, indent=4)
    return dfMaster, masterDict, rawTifList


def makeRoiDictFromZips() -> tuple[pd.DataFrame, dict, list]:
    """
    Returns
    -------
    dfMaster is a df of roi info
    masterDict is a dict of dict, keys are tif file and dict is dict of roi info
    rawTifList is a list of raw tif file paths
    """
    masterDict, rawTifList = _getRawTifDict()

    """
            masterDict[rawTifFile] = {
            'sanpyRoiRects': [],
            'fijiRoiRects': [],
            'Mode': [],
            'Region': '',
            'Cell ID': '',
            'Condition': '',
            'ROI Number': [],
            'Fiji ROI Name': [],
        }
    """
    # TODO: recurisvely walk folder and find .zip files
    rootPath1 = '/Users/cudmore/Dropbox/data/colin/2025/roi manager - 20250520'

    zipList1 = [
        '20250225/ISAN/20250225 ISAN RoiSet.zip',
        '20250225/SSAN/20250225 SSAN RoiSet.zip',
        '20250304/ISAN/20250304 ISAN RoiSet.zip',  # changed name SSAN->ISAN
        '20250304/SSAN/20250304 SSAN RoiSet.zip',
        '20250318/ISAN/20250318 ISAN RoiSet.zip',
        '20250318/SSAN/20250318 SSAN RoiSet.zip',
    ]

    rootPath2 = '/Users/cudmore/Dropbox/data/colin/2025/new-20250613'
    zipList2 = [
        '20250602/ISAN/ISAN RoiSet.zip',
        '20250602/SSAN/SSAN RoiSet.zip',
    ]

    zipListFinal = []
    for oneZip in zipList1:
        zipListFinal.append(os.path.join(rootPath1, oneZip))
    for oneZip in zipList2:
        zipListFinal.append(os.path.join(rootPath2, oneZip))

    for zipIdx, oneZipPath in enumerate(zipListFinal):
        # oneZipFile = os.path.join(rootPath, oneZip)
        dfOne = loadRoiFile(masterDict, oneZipPath)
        if zipIdx == 0:
            dfMaster = dfOne
        else:
            dfMaster = pd.concat([dfMaster, dfOne])

    # check if any tif file keys have empty list (no roi)
    # for k,v in masterDict.items():
    #     if len(v['sanpyRoiRects'])==0:
    #         logger.error(f'did not get any rois for tif file "{k}"')

    # pprint(masterDict, indent=4)
    return dfMaster, masterDict, rawTifList


def _setDetection_df_f0(kymRoiAnalysis: KymRoiAnalysis, roiLabel: str, cond: str):

    kymRoi = kymRoiAnalysis.getRoi(roiLabel)

    kymRoiDetection = kymRoi.getDetectionParams(0, PeakDetectionTypes.intensity)

    _ok = kymRoiDetection.setParam('detectThisTrace', 'df/f0')

    # prominence is different across conditions
    if cond == 'Control':
        prominence = 1.2
    else:
        prominence = 1.4
    _ok = kymRoiDetection.setParam('Prominence', prominence)
    # kymRoiDetection.setParam('Distance (ms)', 220)
    _ok = kymRoiDetection.setParam('Width (ms)', 24)


def _setDetection_Divide(kymRoiAnalysis: KymRoiAnalysis, roiLabel: str, cond: str):

    kymRoi = kymRoiAnalysis.getRoi(roiLabel)

    kymRoiDetection = kymRoi.getDetectionParams(0, PeakDetectionTypes.intensity)

    _ok = kymRoiDetection.setParam('detectThisTrace', 'Divided')
    if _ok is None:
        logger.error('detectThisTrace')
        sys.exit(1)
    # no background subtraction
    prominence = 0.2
    _ok = kymRoiDetection.setParam('Prominence', prominence)

    _ok = kymRoiDetection.setParam('Background Subtract', 'Off')
    if _ok is None:
        logger.error('Background Subtract')
        sys.exit(1)
    kymRoiDetection.setParam('Exponential Detrend', False)  # global
    if _ok is None:
        logger.error('Exponential Detrend')
        sys.exit(1)

    kymRoiDetection.setParam('Distance (ms)', 220)

    # set global divide line scan
    # NEEDS TO BE MANUALLY SET IN GUI
    kymRoiAnalysis.setKymDetectionParam('Divide Line Scan', 1665)  # global


def insertRoiIntoSanPy():
    """Load all of Colins Fiji roi manager zip files and recreate SanPy analysis.

    DOES PEAK DETECTION ON NEWLY INSERTED ROIs

    Important:
        When we load previous SanPy peaks and then detect no peaks -->> do we save no peaks ???
    """

    _startTime = time.time()

    logger.info('making master dict')
    dfMaster, masterDict, rawTifList = makeRoiDictFromZips2()

    channel = 0

    for tifIdx, rawTifPath in enumerate(rawTifList):
        tifFile = os.path.split(rawTifPath)[1]
        print(f'=== === {tifIdx} of {len(rawTifList)} is "{tifFile}"')

        tifInfo = FileInfo.from_path(tifFile)

        # fetch all rows for tif file from dfMaster
        _tifList = dfMaster['tifFileName'].unique()
        if tifFile not in _tifList:
            logger.error(f'did not find tif file "{tifFile}" in roi dfMaster')

            # when code fails, turn this on
            # for p in _tifList:
            #     print(p)
            # logger.error('-->> exit')
            # sys.exit(1)

            continue

        dfTif = dfMaster[dfMaster['tifFileName'] == tifFile]
        # logger.info(f'dfTif:')
        # print(dfTif)
        if len(dfTif) == 0:
            logger.error(
                f'did not find any rois for tif file "{tifFile}" in roi dfMaster'
            )
            logger.error('-->> exit')
            sys.exit(1)

        # load tif as bAnalysis (does proper rotation)
        ba = bAnalysis(rawTifPath)
        imgData = ba.fileLoader._tif  # list of color channel images

        # this will load my previous analysis (just one roi)
        ka = KymRoiAnalysis(rawTifPath, imgData=imgData)

        # delete existing rois
        roiLabels = ka.getRoiLabels()
        for roiLabel in roiLabels:
            existingRoiRect = ka.getRoi(roiLabel).getRect()
            # top is bigger than bottom, imgdata has (0,0) in bottom left
            logger.info(
                f'  DELETIING ROI {roiLabel} existingRoiRect is:{existingRoiRect}'
            )
            ka.deleteRoi(roiLabel)

        #
        # add all rois from fiji, for one tifFile
        # fijiRoiDict = masterDict[tifFile]

        # sanpyRects = fijiRoiDict['sanpyRoiRects']
        # for sanpyRectIdx, sanpyRect in enumerate(sanpyRects):
        for rowLabel, rowDict in dfTif.iterrows():
            # mode = mode=fijiRoiDict['Mode'][sanpyRectIdx]
            polarity = rowDict['Polarity']
            sanpyRect = rowDict['sanpyRoiRect']
            # add roi with mode 1/2
            logger.info(f'  adding roi with polarity:{polarity} sanpyRect:{sanpyRect}')

            newRoi = ka.addROI(sanpyRect)
            kymRoiDetection = newRoi.getDetectionParams(0, PeakDetectionTypes.intensity)

            _ok = kymRoiDetection.setParam('Polarity', polarity)

        #
        # peak detect each roi (each new roi from fiji)
        if 1:
            cond = tifInfo.condition
            if cond == 'Control':
                prominence = 0.8
            else:
                prominence = 1.6
            logger.info(f'  cond:{cond} prominence:{prominence}')

            for roiLabel in ka.getRoiLabels():
                kymRoi = ka.getRoi(roiLabel)

                kymRoiDetection = kymRoi.getDetectionParams(
                    0, PeakDetectionTypes.intensity
                )
                # logger.info(f'kymRoiDetection:{kymRoiDetection.getParam("Polarity")}')
                kymRoiDetection.setParam('Distance (ms)', 220)
                kymRoiDetection.setParam('Width (ms)', 20)

                # prominence is different across conditions
                _ok = kymRoiDetection.setParam('Prominence', prominence)

                # f/f0
                # _setDetection_f_f0(ka, roiLabel, cond)

                # df/f0
                # _setDetection_df_f0(ka, roiLabel, cond)

                #
                # 20250608 detect 'Divided'
                #
                # sanpy-20250608-div
                # _setDetection_Divide(ka, roiLabel, cond)

                # peak detect
                kymRoi.peakDetect(
                    channel=0, peakDetectionType=PeakDetectionTypes.intensity
                )

        # save the analysis
        logger.info(f'SAVING ANALYSIS {tifFile} with {ka.numRoi} rois')
        ka.saveAnalysis()

        #
        # break
        # if tifIdx > 1:
        #     break

    _endTime = time.time()
    _elapsedTime = _endTime - _startTime
    logger.info(f'  elapsed time:{_elapsedTime:.2f} seconds')


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
        logger.info(f'cellID:{cellID}')
        dfCellID = df[df['Cell ID'] == cellID]
        conditions = dfCellID['Condition'].unique()
        # logger.info(f'cellID:{cellID} has conditions:{conditions}')
        _numRoi = None
        for idx, condition in enumerate(conditions):
            dfCondition = dfCellID[dfCellID['Condition'] == condition]
            rois = dfCondition['ROI Number'].unique()
            if idx == 0:
                _numRoi = len(rois)
            numRoi = len(rois)
            print(f'  cellID:{cellID} condition:{condition} num:{numRoi}')
            if numRoi != _numRoi:
                logger.error(
                    f'  cellID:{cellID} condition:{condition} numRoi:{numRoi} != _numRoi:{_numRoi}'
                )
                # sys.exit(1)


if __name__ == '__main__':
    # run this first to ensure we get matches between colins fiji roi names and tif file
    if 0:
        test_loadRoiFile()

    # load all Colin's fiji roi manager and recreate ALL sanpy analysis
    if 1:
        # WILL PERFORM PEAK DETECTION !!!
        insertRoiIntoSanPy()

    # _throwOutAllSanPyAnalysis()

    # works
    # check that each (Cell ID, Condition) has the same number of ROI
    # if 1:
    #     checkRoiPerCondition()
