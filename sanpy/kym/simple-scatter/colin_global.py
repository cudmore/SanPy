import os
from typing import List

import pandas as pd

from sanpy.analysisDir import _walk

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

"""
This was my analysis from 0521 through 0528

Used prominence 1.2 for all analysis
    The peaks were under-detected in control
"""
# dataPath = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/renamed-20250521'

"""
20250528 switching over to using this global to control analysis.

TODO:
    - Move all roi to the right so we can skip bleaching
    - rerun analysis to make sure we detect peaks in control
"""

# This version still has bad rois!!!
# _ROOT_ANALYSIS_FOLDER = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/renamed-20250521'

# while developing divided, detect f/f0
_ROOT_ANALYSIS_FOLDER = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/sanpy-20250530'

# analyzing divided
_ROOT_ANALYSIS_FOLDER = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/sanpy-20250608-div'

def getRootAnalysisFolder() -> str:
    return _ROOT_ANALYSIS_FOLDER

def loadMasterDfFile() -> pd.DataFrame:
    """Load our master df csv file and return as DataFrame.
    """
    file = getMasterDfPath()
    if not os.path.isfile(file):
        logger.error(f'did not find master csv file')
        print(file)
    else:
        df = pd.read_csv(file)
        return df

def loadMeanDfFile() -> pd.DataFrame:
    """Load our mean df csv file and return as DataFrame.
    """
    meanDfPath = getMeanDfPath()
    if not os.path.isfile(meanDfPath):
        logger.error(f'did not find meanDfPath')
        print(meanDfPath)
    else:
        df = pd.read_csv(meanDfPath)
        return df
    
def getMasterDfPath() -> str:
    """Get the full path to our master df csv file.

    One peak per row.
    """
    dfMasterFile = 'df-master-file.csv'
    dfMaster = os.path.join(_ROOT_ANALYSIS_FOLDER, dfMasterFile)
    return dfMaster

def getMeanDfPath() -> str:
    """Get the full path to our mean df csv file.

    One (cell id, condition, roi label) per row.
    """
    dfMeanFile = 'df-mean-file.csv'
    dfMean = os.path.join(_ROOT_ANALYSIS_FOLDER, dfMeanFile)
    return dfMean

def getAllTifFilePaths() -> List[str]:
    """Get a list of all raw tif paths.
    
    This assumes all tif files in analysis folder are to be analyzed.
    """
    thisExt = '.tif'
    paths = _walk(_ROOT_ANALYSIS_FOLDER, thisExt, 5)
    paths = list(paths)

    return paths

def getAllSanPyAnalysisCsv() -> List[str]:
    thisExt = '.csv'
    paths = _walk(_ROOT_ANALYSIS_FOLDER, thisExt, 5)
    paths = list(paths)

    # only accept "roiPeaks.csv" files
    # roiDiameter.csv
    # roiTraces.csv
    paths = [p for p in paths if ('roiPeaks.csv' in p) or ('roiDiameter.csv' in p) or ('roiTraces.csv' in p)]

    return paths

def getAllPeakAnalysisCsv() -> List[str]:
    """Get all SanPy saved analysis csv files using G_MASTER_DATA_FOLDER.
    
    Be sure to skip csv files not saved by SanPy.
    """
    thisExt = '.csv'
    paths = _walk(_ROOT_ANALYSIS_FOLDER, thisExt, 5)
    paths = list(paths)

    # only accept "roiPeaks.csv" files
    paths = [p for p in paths if 'roiPeaks.csv' in p]

    return paths

if __name__ == '__main__':
    print('')
    # getAllPeakAnalysisCsv()
    # print(getMasterDfPath())
    # print(getMeanDfPath())

    # df = loadMeanDfFile()
    # print(df.columns)

    # delete all sanpy analysis
    if 1:
        logger.warning('DELETING ALL SANPY ANALYSIS')
        csv = getAllSanPyAnalysisCsv()
        for path in csv:
            # print(os.path.split(path)[1])
            print(path)
            os.remove(path)

        logger.warning(f'{len(csv)} files.')
