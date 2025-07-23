import os
import sys
import pathlib

# import itertools

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Any, Optional
from datetime import datetime
import warnings

from scipy.stats import mannwhitneyu
from sanpy.analysisDir import analysisDir
from sanpy.fileloaders import getFileLoaders

from sanpy.kym.simple_scatter.colin_global import FileInfo

from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


def _old_run():
    # Define the path and folder depth
    path = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc'
    folderDepth = 5

    fileLoaderDict = getFileLoaders(verbose=True)

    # Create an instance of AnalysisDirectory
    analysis_dir = analysisDir(
        path=path, fileLoaderDict=fileLoaderDict, folderDepth=folderDepth
    )

    df = analysis_dir.getDataFrame()

    df.to_csv('colin_summary.csv', index=False)

    print(df.columns)
    print(df)


def collect_analysis():
    """Walk through a path and collect csv files into one dataframe.

    This is our master df.
    """

    from colin_global import getAllPeakAnalysisCsv

    paths = getAllPeakAnalysisCsv()

    # collect all the dataframes
    dfMaster = pd.DataFrame()
    for idx, csvPath in enumerate(paths):
        # print(f'loading peak anaysis csvPath: {csvPath}')
        _path, csvFile = os.path.split(csvPath)

        df = pd.read_csv(csvPath, header=1)  # first line is detection parameters

        # df.insert(0, 'File Name', csvFile)
        df.insert(0, 'File Number', idx)

        # get original filename from df['path']
        try:
            rawTifPath = df.at[0, 'Path']  # capitol 'P'
        except KeyError as e:
            # empty dataframe, no spikes (in any roi)
            logger.error(f'  ERROR: did not find any spikes in {csvPath}')
            continue

        _path, rawTifFile = os.path.split(rawTifPath)
        rawTifFile, _ext = os.path.splitext(rawTifFile)
        df.insert(0, 'Tif File', rawTifFile)

        # insert condition
        # _cond = getCondFromTifPath(rawTifPath)
        # df.insert(0, 'Condition', _cond)

        # insert condition from FileInfo
        fileInfo = FileInfo.from_path(rawTifPath)
        df.insert(0, 'Condition', fileInfo.condition)

        # insert epoch from FileInfo
        df.insert(0, 'Epoch', fileInfo.epoch)
        # all peaks are labeled with Epoch.
        # df.insert(0, 'Epoch', 0 if _hasEpoch else 1)

        # rawTiFile is like "250225 ISAN R1 LS1 c2 Ivab"
        # pull out a unique cell id (we can then group by cell id and condition)
        _rawTiFile = rawTifFile.split(' ')
        cellID = f'{_rawTiFile[0]} {_rawTiFile[1]} {_rawTiFile[2]} {_rawTiFile[3]}'
        dateStr = _rawTiFile[0]
        # print(f'  unique cellID:"{cellID}"')
        df.insert(0, 'Date', dateStr)
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

    dfMaster['Condition Epoch'] = (
        dfMaster['Condition'].fillna('')
        + ' '
        + dfMaster['Epoch'].astype(str).fillna('')
    ).str.strip()
    dfMaster['Condition Epoch'] = dfMaster['Condition Epoch'].astype('category')

    # for show/hide in scatter widget
    dfMaster['show_region'] = True
    dfMaster['show_condition'] = True
    dfMaster['show_cell'] = True
    dfMaster['show_roi'] = True
    dfMaster['show_polarity'] = True
    dfMaster['show_epoch'] = True

    print('dfMaster is:')
    print(dfMaster)

    if len(dfMaster) == 0:
        logger.error('dfMaster has 0 length!!!')
        sys.exit(1)
    # save to csv
    # this was my analysis with 1 roi per kym
    # savePath = '/Users/cudmore/colin_peak_summary_20250517.csv'

    # this is colins analysis with multiple roi per kym
    # savePath = '/Users/cudmore/colin_peak_summary_20250527.csv'
    from colin_global import getMasterDfPath

    savePath = getMasterDfPath()
    print(f'=== saving dfMaster to savePath:{savePath}')
    dfMaster.to_csv(savePath, index=False)


def create_condition_epoch_column(
    df: pd.DataFrame, condition_col: str = 'Condition', epoch_col: str = 'Epoch'
) -> pd.DataFrame:
    """Create a 'Condition Epoch' column by combining Condition and Epoch columns.

    Args:
        df: DataFrame containing Condition and Epoch columns
        condition_col: Name of the condition column (default: 'Condition')
        epoch_col: Name of the epoch column (default: 'Epoch')

    Returns:
        DataFrame with new 'Condition Epoch' column added
    """
    df_copy = df.copy()

    # Combine condition and epoch with space, handle NaN values
    # Convert epoch to string first to avoid TypeError
    df_copy['Condition Epoch'] = (
        df_copy[condition_col].fillna('')
        + ' '
        + df_copy[epoch_col].astype(str).fillna('')
    ).str.strip()

    # Convert to categorical for efficiency
    df_copy['Condition Epoch'] = df_copy['Condition Epoch'].astype('category')

    return df_copy


if __name__ == "__main__":
    # run()
    # rename_files()

    # works
    # this appends all peak analysis into one saved df
    if 1:
        collect_analysis()
