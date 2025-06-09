
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
    aggList = ["count", np.nanmean, np.nanstd, "sem", "sum"]  # sum is for "Area Under Peak"

    # df = df.dropna(subset=[statColumn])  # drop rows where statColumn is nan
        
    try:
        # AttributeError: 'SeriesGroupBy' object has no attribute 'Region'
        aggDf = df.groupby(groupByColumns).agg({
                                                'Region': 'first',
                                                # 'Condition': lambda x: x.iloc[0],  # mimic 'first'
                                                statColumn : aggList,
                                                'Path': 'last',
                                                'Date': lambda x: x.iloc[0],
                                                })
    except (TypeError) as e:
        logger.error(f'groupByColumn "{groupByColumns}" failed e:{e}')
        aggDf = df

    # aggDf = aggDf.rename(columns={('Region','first'): ('Region','Region')})
    # aggDf.rename_axis(columns=[('Region','first'), ('Region','Region')], inplace=True)
    # aggDf.columns.set_levels(['b1','c1','f1'],level=1,inplace=True)


    # we end up with column multiindex with (stat, region, path)
    # aggDf.columns = ['_'.join(col) for col in aggDf.columns]

    try:
        aggDf.columns = aggDf.columns.droplevel(0)  # get rid of statColumn multiindex
    except (ValueError) as e:
        logger.error(e)

    # rename column 'first' as 'Region'
    aggDf = aggDf.rename(columns={'first': 'Region'}) 
    aggDf = aggDf.rename(columns={'<lambda>': 'Date'})  # how do I use lambda and get a column other than <lambda>?
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
            logger.warning(f'did not find agg column:{agg} possible keys are {aggDf.columns}')
    
    return aggDf

def makeMeanDf():
    """Take master df (one row per spike) and make mean df.
        We get one mean per (cell id, condition, roi number)
    This is used to generate a table for the scatter widget.
    """
    # master df is made in collect_analysis()
    # from colin_summary import getMasterDf
    # savePath = '/Users/cudmore/colin_peak_summary_20250517.csv'
    # savePath = '/Users/cudmore/colin_peak_summary_20250521.csv'
    # was this 20250528 before switch to colin_global
    # savePath = '/Users/cudmore/colin_peak_summary_20250527.csv'
    # df = getMasterDf(savePath)

    from colin_global import loadMasterDfFile
    df = loadMasterDfFile()

    # load once
    _kymRoiAnalysisDict = loadAllKymRoiAnalysis()

    statColumns = [
        # 'Peak Height',
        'Peak Inst Interval (s)',
        'Peak Inst Freq (Hz)',
        'HW (ms)',
        'Rise Time (ms)',
        'Decay Time (ms)',
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
    logger.info(f'adding all stat columns: {statColumns}')
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

    logger.info('appending roi rect ... slow')
    # for each row (cellid, cond, roi number), append (l,t,r,b) of roi
    dfGrouped['ROI Rect'] = ''
    for index, row in dfGrouped.iterrows():
        tifPath = row['Path']
        roiNumber = row['ROI Number']
        #ka = loadKymRoiAnalysis(tifPath)
        ka = _kymRoiAnalysisDict[tifPath]
        roiRect = fetchRoiRect(ka, roiNumber)
        # logger.info(f'index:{index} roiNumber:{roiNumber} roiRect:{roiRect}')
        dfGrouped.at[index, 'ROI Rect'] = roiRect

        detectionParams = ka.getDetectionParams(roiNumber, PeakDetectionTypes.intensity, channel=0)
        f0_value_percentile = detectionParams.getParam('f0 Value Percentile')
        # print(f'f0_value_percentile:{f0_value_percentile}')
        dfGrouped.at[index, 'f0_value_percentile'] = f0_value_percentile

    # print(dfGrouped.columns)
    # print(dfGrouped)

    dfGrouped['show_region'] = True
    dfGrouped['show_condition'] = True
    dfGrouped['show_cell'] = True
    dfGrouped['show_roi'] = True
    
    # flag control kym roi with less than or equal to 2 spikes
    _removeOneSpikeControl(dfGrouped)

    # save as csv to load into scatter widget
    # was this 20250528 before switch to colin_global
    # savePath = '/Users/cudmore/colin_peak_mean_20250521.csv'
    # savePath = '/Users/cudmore/colin_peak_mean_20250527.csv'
    
    from colin_global import getMeanDfPath
    savePath = getMeanDfPath()
    logger.info(f'saving dfGrouped csv:{savePath}')
    dfGrouped.to_csv(savePath)

    # print('final mean df is:')
    # print(dfGrouped)
    # print(dfGrouped.columns)

def fetchRoiRect(ka, roiNumber):
    # ka = loadKymRoiAnalysis(tifPath)
    roi = ka.getRoi(roiLabel=roiNumber)
    rect = roi.getRect()  # [l, t, r, b]
    return rect

def loadAllKymRoiAnalysis() -> dict:
    """Load analysis for each tif and store in a dict.
    
    keys are tif path
    values are KymRoiAnalysis
    """
    retDict = {}
    from colin_global import getAllTifFilePaths
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
    # 20250526, grab Path to tif and load kymAnalysis, look for missing (num peak =0) rois

    # was this 20250528 before switch to colin_global
    # this is colins analysis with multiple roi per kym
    # path = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/renamed-20250521'
    # rawTifPaths = _walk(path=path, theseFileTypes='.tif', depth=5)

    from colin_global import getAllTifFilePaths
    rawTifPaths = getAllTifFilePaths()

    zeroSpikeDictList = []
    for rawTifPath in rawTifPaths:
        # load tif as bAnalysis (does proper rotation)
        # ba = bAnalysis(rawTifPath)
        # imgData = ba.fileLoader._tif  # list of color channel images
        # # logger.info(f'imgData:{imgData[0].shape} {np.min(imgData[0])} {np.max(imgData[0])} {np.mean(imgData[0])}')
        # ka = KymRoiAnalysis(rawTifPath, imgData=imgData)
        ka = kymAnalysisDict[rawTifPath]

        for roi in ka.getRoiLabels():
            roi = ka.getRoi(roi)
            roiLabel = roi.getLabel()
            results = roi.getAnalysisResults(0, PeakDetectionTypes.intensity)
            # dfResults = results.df
            numSpikes = len(results.df)
            # rawTifDict[rawTifPath]=numSpikes
            if numSpikes == 0:
                # have to add a row with 'numSpikes' 0
                tifFile = os.path.split(rawTifPath)[1]  # like: "250304 SSAN R3 LS1 c1.tif"
                # cell id: 250225 ISAN R1 LS1
                # Condition: (Control, Ivab, Thaps)
                if ' c1.tif' in tifFile:
                    condition = 'Control'
                    cellID = tifFile.replace(' c1.tif', '')
                elif ' c2 Ivab.tif' in tifFile:
                    condition = 'Ivab'
                    cellID = tifFile.replace(' c2 Ivab.tif', '')
                elif ' c3 Thap.tif' in tifFile:
                    condition = 'Thap'
                    cellID = tifFile.replace(' c3 Thap.tif', '')
                else:
                    logger.error(f'ERROR: did not find c1 c2 c3 in raw tif file ??? {tifFile}')
                    condition = 'Unknown'
                
                # not needed
                if 'ISAN' in tifFile:
                    region = 'ISAN'
                elif 'SSAN' in tifFile:
                    region = 'SSAN'
                else:
                    logger.error(f'ERROR: did not find ISAN or SSAN in raw tif file ??? {tifFile}')
                    region = 'Unknown'
                
                # poor form, out date folder is not part of the tif file name (renamed by colin rename fn())
                dateStr = tifFile.split(' ')[0]

                oneDict = {
                    'Cell ID': cellID,
                    'Condition': condition,
                    'Date': dateStr,
                    'ROI Number': roiLabel,
                    'Region': region,
                    'Number of Spikes': 0,
                    'Path': rawTifPath,
                }
                zeroSpikeDictList.append(oneDict)

    # for zeroSpikeDict in zeroSpikeDictList:
    #     logger.info(f'zero spike dict: {zeroSpikeDict}')

    return zeroSpikeDictList

def _removeOneSpikeControl(dfMean):
    # remove cells that have 1 spike in control (remove control, ivab, thap)
    # from colin_global import loadMeanDfFile, getMeanDfPath
    # dfMean = loadMeanDfFile()

    # flag by setting 'show_roi' 'le2_peaks'
    removeLessThanEqual = 2
    
    dfMean['le2_peaks'] = False

    columns = ['Cell ID', 'Region', 'Condition', 'ROI Number', 'Number of Spikes']

    dfControl = dfMean[dfMean['Condition'] == 'Control']
    dfOneSpike = dfControl[dfControl['Number of Spikes'] <= removeLessThanEqual]

    numControlWithOneSpike = len(dfOneSpike['Cell ID'].unique())
    logger.info(f'numm Cell Id Control with <= {removeLessThanEqual} is {numControlWithOneSpike}')

    # print(f'before drop, df mean has {len(dfMean)} rows.')

    # remove all rows that have (cell id, ROI Number)
    for rowLabel, rowDict in dfOneSpike.iterrows():  # iterate our <=1 spike (cell id, roi number)
        cellID = rowDict['Cell ID']
        roiNumber = rowDict['ROI Number']
        # logger.info(f'removing cellID:{cellID} roiNumber:{roiNumber}')
        theseRows = (dfMean['Cell ID'] == cellID) & (dfMean['ROI Number'] == roiNumber)
        # print(dfMean.loc[theseRows, columns])
        
        theseRows2 = dfMean.loc[theseRows]
        # print(theseRows2.index)
        # dfMean = dfMean.drop(theseRows2.index)
        dfMean.loc[theseRows2.index, 'le2_peaks'] = True

    # print(f'after drop, df mean has {len(dfMean)} rows.')

    # 20250529
    # before drop, df mean has 241 rows.
    # after drop, df mean has 147 rows.

    # then runnin again with <=2
    # numm Cell Id Control with <= 2 is 7
    # before drop, df mean has 147 rows.
    # after drop, df mean has 123 rows.

    # resave dfMean
    # dfMeanPath = getMeanDfPath()
    # logger.info(F'saving {dfMeanPath}')
    # dfMean.to_csv(dfMeanPath)

if __name__ == '__main__':
    
    # works, make the mean df from master, one row per (cell id, cond, roi)
    makeMeanDf()

    # _removeOneSpikeControl()

    # find roi with 0 peaks and add to mean df
    # findZeroPeaks()