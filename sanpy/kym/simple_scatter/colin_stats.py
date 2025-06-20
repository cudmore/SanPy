import os
import sys
from pprint import pprint
from typing import List, Optional
import itertools

import numpy as np
import pandas as pd

from scipy.stats import variation, mannwhitneyu

from sanpy.bAnalysis_ import bAnalysis
from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, PeakDetectionTypes
from sanpy.analysisDir import _walk

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

# Import FileInfo from colin_global
from sanpy.kym.simple_scatter.colin_global import FileInfo

def genStats3(df, stat, region, cond1, cond2):
    logger.info(f'stat:{stat} region:{region} -> {cond1} vs {cond2}')

    df = df[df['Region']==region]

    dfCond1 = df[df['Condition']==cond1]
    dfCond1 = dfCond1.dropna(subset=[stat])  # drop nan values
    values_1 = dfCond1[stat].to_list()
    n1 = len(values_1)

    dfCond2 = df[df['Condition']==cond2]
    dfCond2 = dfCond2.dropna(subset=[stat])  # drop nan values
    values_2 = dfCond2[stat].to_list()
    n2 = len(values_2)

    logger.info(f'{cond1}:{n1} {cond2}:{n2}')

    nRows = max(n1, n2)

    dfRet = pd.DataFrame(
        {
            cond1: [np.nan] * nRows,
            cond2: [np.nan] * nRows,
         }
    )
    dfRet[cond1][0:n1] = values_1
    dfRet[cond2][0:n2] = values_2
    
    print(dfRet)

    # pValue = mannwhitneyu(dfRet[cond1], dfRet[cond2])
    pValue = mannwhitneyu(values_1, values_2)
    print(pValue)

def genStats2(df, stat):
    """Iterate through region and cpndition,
    generate a pairwise stat for each pair
    """
    dfPlot = df
    
    regions = df['Region'].unique()
    for region in regions:
        dfPlot = dfPlot[dfPlot['Region']==region]
        conds = df['Condition'].unique()
        conds = sorted(conds)
        pairwiseConds = list(itertools.combinations(conds, 2))
        for onePair in pairwiseConds:
            genStats3(df, stat, region, onePair[0], onePair[1])

def getGroupedDataframe(df,
                        statColumn,
                        groupByColumns:List[str] = Optional[List[str]],
                        decimalPlaces: int = 3):
        
    # groupByColumns = ['Region', 'Condition']

    # aggList = ["count", "mean", "std", "sem", variation, "median", "min", "max"]
    # aggList = ["count", np.nanmean, np.nanstd, "sem"]
    # FutureWarning: The provided callable <function nanstd at 0x10d5658a0> is currently using SeriesGroupBy.std. In a future version of pandas, the provided callable will be used directly. To keep current behavior pass the string "std" instead.
    # aggList = ["count", np.nanmean, np.nanstd, "sem", "sum"]  # sum is for "Area Under Peak"
    aggList = ["count", "mean", "std", "sem", "sum"]  # sum is for "Area Under Peak"

    # df = df.dropna(subset=[statColumn])  # drop rows where statColumn is nan
        
    try:
        # AttributeError: 'SeriesGroupBy' object has no attribute 'Region'
        aggDf = df.groupby(groupByColumns).agg({
                                                'Region': 'first',
                                                # 'Condition': lambda x: x.iloc[0],  # mimic 'first'
                                                statColumn : aggList,
                                                'Path': 'last',
                                                'Date': lambda x: x.iloc[0],
                                                'Epoch': lambda x: x.iloc[0],
                                                })
    except (TypeError) as e:
        logger.error(f'groupByColumn "{groupByColumns}" failed e:{e}')
        aggDf = df

    # we end up with column multiindex with (stat, region, path)
    # aggDf.columns = ['_'.join(col) for col in aggDf.columns]


    try:
        # df.columns = df.columns.droplevel()
        aggDf.columns = aggDf.columns.droplevel(0)  # get rid of statColumn multiindex
    except (ValueError) as e:
        logger.error(e)

    _columns = list(aggDf.columns)
    # logger.info(f'aggDf.columns:{_columns}')
    firstLambda = _columns.index('<lambda>')
    _columns[firstLambda] = 'Date'
    secondLambda = _columns.index('<lambda>')
    _columns[secondLambda] = 'Epoch'
    aggDf.columns = _columns
    # print(aggDf)
    # sys.exit(1)

    
    # rename column 'first' as 'Region'
    aggDf = aggDf.rename(columns={'first': 'Region'}) 
    # aggDf = aggDf.rename(columns={'<lambda>': 'Date'})  # how do I use lambda and get a column other than <lambda>?
    aggDf = aggDf.rename(columns={'last': 'Path'}) 

    aggDf = aggDf.reset_index()  # move groupByColum (e.g. 'ROI Number') from row index label to column
    aggDf.insert(0, 'Stat', statColumn)  # add column 0, in place
    
    # rename column 'variation' as 'CV'
    # aggDf = aggDf.rename(columns={'variation': 'CV'}) 
    aggDf = aggDf.rename(columns={'nanmean': 'mean'}) 
    aggDf = aggDf.rename(columns={'nanstd': 'std'}) 

    # round some columns
    aggList = ["mean", "std", "sem"]
    for agg in aggList:
        if agg == 'count':
            continue
        try:
            aggDf[agg] =round(aggDf[agg], decimalPlaces)
        except (KeyError) as e:
            logger.error(f'did not find agg column:{agg} possible keys are {aggDf.columns}')
    
    # logger.info(f'final aggDf:')
    # print(aggDf)
    # sys.exit(1)

    return aggDf

def makeMeanDf():
    """Take master df (one row per spike) and make mean df.
        We get one mean per (cell id, condition, roi number)
    This is used to generate a table for the scatter widget.
    """

    from sanpy.kym.simple_scatter.colin_global import loadMasterDfFile
    df = loadMasterDfFile()

    # load once
    _kymRoiAnalysisDict = loadAllKymRoiAnalysis()

    statColumns = [
        # 'Peak Height',
        'Peak Inst Interval (s)',
        'Peak Inst Freq (Hz)',
        'Rise Time (ms)',
        'Decay Time (ms)',
        'FW (ms)',
        'HW (ms)',
        'Area Under Peak',
        # 'Number of Spikes',
        # 'Spike Frequency (Hz)',
        'fit_tau',
        'fit_tau1',
    ]

    #
    # seed with peak height (gives us number or rows)
    logger.info('seeding df with peak height')
    stat = 'Peak Height'
    groupByColumns = ['Cell ID', 'Condition', 'ROI Number']
    dfGrouped = getGroupedDataframe(df, stat, groupByColumns=groupByColumns)
    # dfGrouped has 'Path' to tif file
    
    dfGrouped.drop('Stat', axis=1, inplace=True)

    # rename columns
    dfGrouped = dfGrouped.rename(columns={'count': 'Number of Spikes'}) 

    dfGrouped[stat+'_cv'] = dfGrouped['std'] / dfGrouped['mean'] * 100

    # dfGrouped = dfGrouped.rename(columns={'mean': stat+"_mean"}) 
    dfGrouped = dfGrouped.rename(columns={'mean': stat}) 
    dfGrouped = dfGrouped.rename(columns={'std': stat+"_std"}) 
    dfGrouped = dfGrouped.rename(columns={'sem': stat+"_sem"}) 
    
    # logger.info('dfGrouped is:')
    # cols = ['Cell ID', 'Region', 'Condition', 'ROI Number', 'Number of Spikes',
    #         stat, stat+'_std', stat+'_sem', stat+'_cv']
    # print(dfGrouped[cols])

    # print(dfGrouped[dfGrouped['Number of Spikes']==np.nan])
    
    #
    # add all other stat columns
    logger.info(f'  adding all stat columns: {statColumns}')
    for stat in statColumns:
        oneDf = getGroupedDataframe(df, stat, groupByColumns=groupByColumns)

        oneDf['cv'] = oneDf['std'] / oneDf['mean'] * 100
        # oneDf = oneDf.rename(columns={'mean': stat}) 
        # oneDf = oneDf.rename(columns={'std': stat+"_std"}) 
        # oneDf = oneDf.rename(columns={'sem': stat+"_sem"}) 

        dfGrouped[stat] = oneDf['mean']
        dfGrouped[stat+"_std"] = oneDf['std']
        dfGrouped[stat+"_sem"] = oneDf['sem']
        dfGrouped[stat+"_cv"] = oneDf['cv']

        if stat == 'Area Under Peak':
            # add sum column for "Area Under Peak"
            #dfGrouped[stat+"_sum"] = oneDf['sum']
            dfGrouped[stat + " (Sum)"] = oneDf['sum']

    # 20250526 find (cell id, cond, roi) that have zero (0) peaks
    # append to mean df as 'Number of Spikes' == 0
    logger.info('finding roi with 0 peaks')
    zeroSpikeDictList = findZeroPeaks(_kymRoiAnalysisDict)
    logger.info(f'  found {len(zeroSpikeDictList)} cell/cond/roi with zero peaks')
    for zeroSpike in zeroSpikeDictList:
        # logger.info(f'  {zeroSpike}')
        cellID = zeroSpike['Cell ID']
        condition = zeroSpike['Condition']
        roiNumber = zeroSpike['ROI Number']
        searchThis = (dfGrouped['Cell ID']==cellID) \
                & (dfGrouped['Condition'] == condition) \
                & (dfGrouped['ROI Number'] == roiNumber)
        dfEmpty = dfGrouped.loc[searchThis]
        if len(dfEmpty>0):
            logger.error(f'NOT EMPTY {zeroSpike}')
    dfZeroSpike = pd.DataFrame(zeroSpikeDictList)
    # print(dfZeroSpike)

    dfGrouped = pd.concat([dfGrouped, dfZeroSpike], axis=0).reset_index(drop=True)

    # print(dfGrouped.columns)
    # print(dfGrouped['Date'])
    # sys.exit(1)

    logger.info('appending roi rect to df ...')
    # for each row (cellid, cond, roi number), append (l,t,r,b) of roi
    dfGrouped['Polarity'] = ''
    dfGrouped['ROI Rect'] = ''
    dfGrouped['Detection Params'] = ''
    for index, row in dfGrouped.iterrows():
        tifPath = row['Path']
        roiNumber = row['ROI Number']
        #ka = loadKymRoiAnalysis(tifPath)
        ka:KymRoiAnalysis = _kymRoiAnalysisDict[tifPath]
        
        # roiRect = fetchRoiRect(ka, roiNumber)
        roi = ka.getRoi(roiLabel=roiNumber)
        roiRect = roi.getRect()  # [l, t, r, b]
        # logger.info(f'index:{index} roiNumber:{roiNumber} roiRect:{roiRect}')
        dfGrouped.at[index, 'ROI Rect'] = roiRect

        _kymRoiDetection = roi.getDetectionParams(0, PeakDetectionTypes.intensity)
        _polarity = _kymRoiDetection.getParam('Polarity')
        dfGrouped.at[index, 'Polarity'] = _polarity

        # add detection params for row
        detectionParams = ka.getDetectionParams(roiNumber, PeakDetectionTypes.intensity, channel=0)

        _detectionDict = detectionParams.getValueDict()
        dfGrouped.at[index, 'Detection Params'] = _detectionDict

        f0_value_percentile = detectionParams.getParam('f0 Value Percentile')
        # print(f'f0_value_percentile:{f0_value_percentile}')
        dfGrouped.at[index, 'f0_value_percentile'] = f0_value_percentile

    # print(dfGrouped.columns)
    # print(dfGrouped)

    dfGrouped['show_region'] = True
    dfGrouped['show_condition'] = True
    dfGrouped['show_cell'] = True
    dfGrouped['show_roi'] = True
    dfGrouped['show_polarity'] = True
    
    # flag control kym roi with less than or equal to 2 spikes
    _removeOneSpikeControl(dfGrouped)

    # save as csv to load into scatter widget
    # was this 20250528 before switch to colin_global
    # savePath = '/Users/cudmore/colin_peak_mean_20250521.csv'
    # savePath = '/Users/cudmore/colin_peak_mean_20250527.csv'
    
    from sanpy.kym.simple_scatter.colin_global import getMeanDfPath
    savePath = getMeanDfPath()
    logger.info(f'saving dfGrouped csv:{savePath}')
    dfGrouped.to_csv(savePath)

    # print('final mean df is:')
    # print(dfGrouped)
    # print(dfGrouped.columns)

# def fetchRoiRect(ka, roiNumber):
#     # ka = loadKymRoiAnalysis(tifPath)
#     roi = ka.getRoi(roiLabel=roiNumber)
#     rect = roi.getRect()  # [l, t, r, b]
#     return rect

def loadAllKymRoiAnalysis() -> dict:
    """Load analysis for each tif and store in a dict.
    
    keys are tif path
    values are KymRoiAnalysis
    """
    retDict = {}
    from sanpy.kym.simple_scatter.colin_global import getAllTifFilePaths
    tifPaths = getAllTifFilePaths()
    logger.info(f'loading all kym roi analysis from {len(tifPaths)} tif files')
    for tifPath in tifPaths:
        ka = _loadKymRoiAnalysis(tifPath)
        retDict[tifPath] = ka
    return retDict

def _loadKymRoiAnalysis(tifPath):
    """Load one kymRoiAnalysis..
    """
    ba = bAnalysis(tifPath)
    imgData = ba.fileLoader._tif  # list of color channel images
    # logger.info(f'imgData:{imgData[0].shape} {np.min(imgData[0])} {np.max(imgData[0])} {np.mean(imgData[0])}')
    ka = KymRoiAnalysis(tifPath, imgData=imgData)
    return ka

def findZeroPeaks(kymAnalysisDict):
    """Find rois with 0 peaks and add to mean df.

    This looks for Control Trial 1 ROIs with zero peaks
    to then set all other cell id (thap, Ivab) off for that roi.
    """
    from sanpy.kym.simple_scatter.colin_global import getAllTifFilePaths
    
    rawTifPaths = getAllTifFilePaths()

    channel = 0

    zeroSpikeDictList = []
    for rawTifPath in rawTifPaths:
        ka:KymRoiAnalysis = kymAnalysisDict[rawTifPath]

        for roi in ka.getRoiLabels():
            roi = ka.getRoi(roi)
            roiLabel = roi.getLabel()
            results = roi.getAnalysisResults(channel, PeakDetectionTypes.intensity)
            # dfResults = results.df
            numSpikes = len(results.df)
            if numSpikes == 0:
                # have to add a row with 'numSpikes' 0
                # Use FileInfo to parse the file path
                file_info = FileInfo.from_path(rawTifPath)

                oneDict = {
                    'Cell ID': file_info.cellID,
                    'Condition': file_info.condition,
                    'Epoch': file_info.epoch,
                    'Date': file_info.date,
                    'ROI Number': roiLabel,
                    'Region': file_info.region,
                    'Number of Spikes': 0,
                    'Path': rawTifPath,
                }
                zeroSpikeDictList.append(oneDict)

    # for zeroSpikeDict in zeroSpikeDictList:
    #     logger.info(f'zero spike dict: {zeroSpikeDict}')

    return zeroSpikeDictList

def _removeOneSpikeControl(dfMean: pd.DataFrame):
    # remove cells that have 1 spike in control (remove control, ivab, thap)
    # from colin_global import loadMeanDfFile, getMeanDfPath
    # dfMean = loadMeanDfFile()

    # flag by setting 'show_roi' 'le2_peaks'
    removeLessThanEqual = 2
    
    dfMean['le2_peaks'] = False

    # columns = ['Cell ID', 'Region', 'Condition', 'ROI Number', 'Number of Spikes']

    # Create an explicit copy to avoid SettingWithCopyWarning
    dfControl = dfMean[dfMean['Condition'] == 'Control'].copy()
    
    # we might have a number of Epoch(s) 0,1,2. Use the last epoch
    # for each cell id, get the last epoch
    dfControl['Last Epoch'] = dfControl.groupby('Cell ID')['Epoch'].transform('max')
    
    # filter by last epoch
    dfControl = dfControl[dfControl['Epoch'] == dfControl['Last Epoch']]
    
    # filter by number of spikes
    dfOneSpike = dfControl[dfControl['Number of Spikes'] <= removeLessThanEqual]

    numControlWithOneSpike = len(dfOneSpike['Cell ID'].unique())
    logger.info(f'num Cell Id Control with <= {removeLessThanEqual} peaks is {numControlWithOneSpike}')

    # print(f'before drop, df mean has {len(dfMean)} rows.')

    # remove all rows that have (cell id, ROI Number)
    for rowLabel, rowDict in dfOneSpike.iterrows():  # iterate our <=1 spike (cell id, roi number)
        cellID = rowDict['Cell ID']
        roiNumber = rowDict['ROI Number']

        theseRows = (dfMean['Cell ID'] == cellID) & (dfMean['ROI Number'] == roiNumber)
        theseRows2 = dfMean.loc[theseRows]

        dfMean.loc[theseRows2.index, 'le2_peaks'] = True
        
        dfMean.loc[theseRows2.index, 'show_cell'] = False
        dfMean.loc[theseRows2.index, 'show_roi'] = False

if __name__ == '__main__':
    
    # works, make the mean df from master, one row per (cell id, cond, roi)
    makeMeanDf()

    # _removeOneSpikeControl()

    # find roi with 0 peaks and add to mean df
    # findZeroPeaks()