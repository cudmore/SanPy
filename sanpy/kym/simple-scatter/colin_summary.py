import os
import pathlib
# import itertools

import numpy as np
import pandas as pd

from scipy.stats import mannwhitneyu

from sanpy.analysisDir import analysisDir
from sanpy.fileloaders import getFileLoaders
from sanpy.analysisDir import _walk

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def _old_run():
    # Define the path and folder depth
    path = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc'
    folderDepth = 5

    fileLoaderDict = getFileLoaders(verbose=True)

    # Create an instance of AnalysisDirectory
    analysis_dir = analysisDir(path=path,
                               fileLoaderDict=fileLoaderDict,
                               folderDepth=folderDepth)

    df = analysis_dir.getDataFrame()

    df.to_csv('colin_summary.csv', index=False)

    print(df.columns)
    print(df)

def rename_files():
    dataPath = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/renamed2'
    
    # run this twice, once for .tif and then for .txt
    # thisExt = '.tif'
    thisExt = '.txt'

    paths = _walk(dataPath, thisExt, 5)
    paths = list(paths)
    
    for _idx, path in enumerate(paths):
        
        # just for debugging
        # shortPath = path.replace(dataPath, '')
        shortPath = path

        print(f'{_idx} to rename')
        print(shortPath)
        
        # first element is date
        _tmpPath = path.replace(dataPath, '')
        p = pathlib.Path(_tmpPath)
        dateStr = p.parts[1]  # short path starts with '/'
        # dateStr = os.path.split(shortPath)[0]
        # print(f'  dateStr:"{dateStr}"')

        _rootPath, filename = os.path.split(shortPath)
        filename, _ext = os.path.splitext(filename)

        if dateStr not in filename:
            newname = dateStr + ' ' + filename
        else:
            newname = filename
        
        # expCond = 1
        if 'Thapsigargin' in newname:
            newname = newname.replace('Thapsigargin', '')
            newname = newname.replace('Ivabradine', '')  # remove
            newname += ' c3 Thap'
            # expCond = 3
        elif 'Ivabradine' in newname:
            newname = newname.replace('Ivabradine', '')
            newname += ' c2 Ivab'
            # expCond = 2
        else:
            newname += ' c1'

        newname = newname.replace('   ', ' ')
        newname = newname.replace('  ', ' ')
        # print(f'  newname -->> "{newname}"')
        
        newPathName = os.path.join(_rootPath, newname + _ext)
        print(newPathName)
        if path == newPathName:
            print('  same name, skipping')
            continue

        # ACTUALLY DO RENAME
        # os.rename(path, newPathName)

    print(f'found {len(paths)} files')

def _throwOutAllSanPyAnalysis():
    # 20250523 THROW OUT ALL (roiPeaks.csv and roiTraces.csv)
    deletePath = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/renamed-20250521'
    logger.info('deleting all sanypy analysis !!!')
    print(deletePath)
    sanpyCsvFiles = _walk(deletePath, '.csv', 5)
    for sanpyCsvFile in sanpyCsvFiles:
        print(sanpyCsvFile)

        os.remove(sanpyCsvFile)
        
def collect_analysis():
    """Walk through a path and collect csv files into one dataframe.
    """
    
    # this was my analysis with just 1 roi per kym
    # dataPath = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/renamed2'

    # this is colins analysis with multiple roi per kym
    dataPath = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/renamed-20250521'

    print('=== loading all csv files from:')
    print(dataPath)
    
    thisExt = '.csv'
    paths = _walk(dataPath, thisExt, 5)
    paths = list(paths)
    
    # only accept "roiPeaks.csv" files
    paths = [p for p in paths if 'roiPeaks.csv' in p]
    print(f'found {len(paths)} files')

    # collect all the dataframes
    dfMaster = pd.DataFrame()
    for idx, csvPath in enumerate(paths):
        print(f'loading csvPath: {csvPath}')
        _path, csvFile = os.path.split(csvPath)
        
        df = pd.read_csv(csvPath, header=1)  # first line is detection parameters
        
        # df.insert(0, 'File Name', csvFile)
        df.insert(0, 'File Number', idx)
        
        # get original filename from df['path']
        rawTifPath = df.at[0, 'Path']  # capitol 'P'
        _path, rawTifFile = os.path.split(rawTifPath)
        rawTifFile, _ext = os.path.splitext(rawTifFile)
        df.insert(0, 'Tif File', rawTifFile)

        if 'c1' in rawTifFile:
            df.insert(0, 'Condition', 'Control')
        elif 'c2' in rawTifFile:
            df.insert(0, 'Condition', 'Ivab')
        elif 'c3' in rawTifFile:
            df.insert(0, 'Condition', 'Thap')
        else:
            print(f'ERROR: did not find c1 c2 c3 in raw tif file ???')

        # rawTiFile is like "250225 ISAN R1 LS1 c2 Ivab"
        # pull out a unique cell id (we can then group by cell id and condition)
        _rawTiFile = rawTifFile.split(' ')
        cellID = f'{_rawTiFile[0]} {_rawTiFile[1]} {_rawTiFile[2]} {_rawTiFile[3]}'
        # print(f'  unique cellID:"{cellID}"')
        df.insert(0, 'Cell ID', cellID)

        # get the region from the filename
        if 'SSAN' in rawTifFile:
            sanRegion = 'SSAN'
        elif 'ISAN' in rawTifFile:
            sanRegion = 'ISAN'
        else:
            print('ERROR: no region found')
            sanRegion = 'Unknown'
        df.insert(0, 'Region', sanRegion)

        # print(f'loaded {csvFile} {rawDataTif} with {len(df)} peak')
        dfMaster = pd.concat([dfMaster, df], ignore_index=True)

    print(dfMaster)

    # save to csv
    # this was my analysis with 1 roi per kym
    # savePath = '/Users/cudmore/colin_peak_summary_20250517.csv'
    
    # this is colins analysis with multiple roi per kym
    savePath = '/Users/cudmore/colin_peak_summary_20250527.csv'
    
    print(f'=== saving dfMaster to savePath:{savePath}')
    
    dfMaster.to_csv(savePath, index=False)

def getMasterDf(savePath):
    """Build a df from a csv path.

    This is tweaking output of xxx so colin_scatter can use it
    """
    df = pd.read_csv(savePath)

    # this was just putting \n so cell id is readable (not usefull ???)
    # cellIDs = df['Cell ID'].to_list()
    # newList = []
    # for cellID in cellIDs:
    #     _split = cellID.split()
    #     newID = f'{_split[0]}\n{_split[1]}\n{_split[2]} {_split[3]}'
    #     newList.append(newID)
    #     # print(f'newID: "{newID}"')
    # df['Cell ID (plot)'] = newList
    
    df['show_region'] = True
    df['show_condition'] = True
    df['show_cell'] = True
    df['show_roi'] = True

    # add num spikes
    # logger.info('todo: adding num spikes -->> handle this in "mean table"')
    # df["Number of Spikes"] = np.nan
    # df['Spike Frequency (Hz)'] = np.nan
    # for cellID in df['Cell ID'].unique():
    #     dfCellID = df[df['Cell ID']==cellID]
    #     for cond in ['Control', 'Ivab', 'Thap']:
    #         _df = dfCellID[dfCellID['Condition']==cond]
    #         # print(_df.index[0])
    #         # print(_df.iloc[0])
    #         numSpikes = len(_df)
    #         if numSpikes == 0:
    #             logger.error(f'no peaks for cellID:"{cellID}" cond:"{cond}"')
    #         else:
    #             _firstIndex = _df.index[0]
    #             # print(f'  _firstIndex:{_firstIndex} cellID:{cellID} cond:{cond} numSpikes:{numSpikes}')
    #             df.at[_firstIndex, "Number of Spikes"] = numSpikes

    return df


if __name__ == "__main__":
    # run()
    #rename_files()
    
    # works
    # this appends all peak analysis into one saved df
    collect_analysis()
    
    # _throwOutAllSanPyAnalysis()