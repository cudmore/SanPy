import os
import sys
from typing import List
from dataclasses import dataclass

import pandas as pd
import shutil
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Any, Optional, NamedTuple
from datetime import datetime
import warnings

from sanpy.analysisDir import _walk
# from sanpy.bAnalysis_ import bAnalysis
from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis
from sanpy.kym.logger import get_logger
logger = get_logger(__name__)

@dataclass
class FileInfo:
    """Dataclass to hold parsed file information from tif file paths.
    
    Example path: "20250602 ISAN R3 LS3 Control Epoch 1.tif"
    """
    cellID: str
    epoch: int
    date: str
    region: str
    condition: str
    
    @classmethod
    def from_path(cls, tif_path: str) -> 'FileInfo':
        """Create FileInfo from a tif file path.
        
        Args:
            tif_path: Path like "20250602 ISAN R3 LS3 Control Epoch 1.tif"
            
        Returns:
            FileInfo object with parsed components
        """
        # Get just the filename without path
        _, tif_file = os.path.split(tif_path)
        
        # Remove .tif extension
        tif_file = tif_file.replace('.tif', '')
        
        # Split into components
        parts = tif_file.split(' ')
        
        # Extract date (first part)
        date = parts[0]
        
        # Extract region (ISAN or SSAN)
        region = None
        for part in parts:
            if part in ['ISAN', 'SSAN']:
                region = part
                break
        if region is None:
            logger.error(f'ERROR: did not find ISAN or SSAN in raw tif file ??? {tif_file}')
            region = 'Unknown'
        
        # Extract condition
        condition = None
        for cond in conditionOrder:
            if cond in tif_file:
                condition = cond
                break
        if condition is None:
            logger.error(f'ERROR: did not find one of {conditionOrder} in raw tif file ??? {tif_file}')
            condition = 'Unknown'
        
        # Extract epoch
        epoch = 0  # default
        if 'Epoch' in tif_file:
            epoch_str = tif_file.split('Epoch ')[1]
            epoch = int(epoch_str)
        
        # Extract cellID - everything up to the condition
        # Remove epoch part if present
        cell_id_parts = tif_file
        if 'Epoch' in cell_id_parts:
            cell_id_parts = cell_id_parts.split(' Epoch')[0]
        
        # Remove condition part
        for cond in conditionOrder:
            if cond in cell_id_parts:
                cell_id_parts = cell_id_parts.replace(f' {cond}', '')
                break
        
        cellID = cell_id_parts.strip()
        
        return cls(
            cellID=cellID,
            epoch=epoch,
            date=date,
            region=region,
            condition=condition
        )


conditionOrder = ['Control', 'Ivab', 'Thap', 'FCCP']
# List of all possible conditions

# abb 20250621
# conditionEpochOrder = ['Control 0', 'Control 1', 'Ivab 0', 'Thap 0']

# fijiConditions = ['Control', 'Ivabradine', 'Thapsigargin']
fijiConditions = ['Control', 'Ivabradine', 'Thapsigargin', 'FCCP']

regionOrder = ['SSAN', 'ISAN']

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

# df_f0
# _ROOT_ANALYSIS_FOLDER = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/sanpy-20250610-df_f0'

# f_f0
# _ROOT_ANALYSIS_FOLDER = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/sanpy-20250610-f_f0'

# adding mode 1/2 to each roi
# _ROOT_ANALYSIS_FOLDER = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/sanpy-20250612-f_f0'

# analyzing divided
# _ROOT_ANALYSIS_FOLDER = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/sanpy-20250608-div'
# working on import of new data, this wil be merged into main fiolder
# _ROOT_ANALYSIS_FOLDER = '/Users/cudmore/Dropbox/data/colin/2025/new-20250613/20250602'

_ROOT_ANALYSIS_FOLDER = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250618-rhc'

_ROOT_ANALYSIS_FOLDER = '/Users/cudmore/Dropbox/data/colin/2025/mito-atp/mito-atp-20250623-RHC'

_ROOT_SANPY_REPORT_FOLDER = 'sanpy-reports-pdf'

# _IGOR_THESE_FOLDERS = [_ROOT_ANALYSIS_FOLDER]

def getCellCondEpoch(df:pd.DataFrame, cellID:str, condition:str, epoch:int, roi:int=None) -> pd.DataFrame:
    """Get a dataframe with only the rows for a given cellID, condition, epoch, and roi.
    """
    df = df[df['Cell ID'] == cellID]
    df = df[df['Condition'] == condition]
    df = df[df['Epoch'] == epoch]
    if roi is not None:
        df = df[df['ROI Number'] == roi]
    return df

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

    # only accept tif files not in folder 'roi-img-clips
    paths = [p for p in paths if 'roi-img-clips' not in p and 'sanpy-reports-pdf' not in p]

    return paths

def getAllSanPyAnalysisCsv() -> List[str]:
    thisExt = '.csv'
    paths = _walk(_ROOT_ANALYSIS_FOLDER, thisExt, 5)
    paths = list(paths)

    # only accept paths that have 'sanpy-kym-roi-analysis' folder
    paths = [p for p in paths if 'sanpy-kym-roi-analysis' in p]

    return paths

def getAllPeakAnalysisCsv() -> List[str]:
    """Get all SanPy saved analysis csv files using G_MASTER_DATA_FOLDER.
    
    Be sure to skip csv files not saved by SanPy.
    """
    thisExt = '.csv'
    paths = _walk(_ROOT_ANALYSIS_FOLDER, thisExt, 5)
    paths = list(paths)

    # only accept "roiPeaks.csv" files
    paths = [p for p in paths if 'roiPeaks.csv' in p and 'sanpy-kym-roi-analysis' in p]

    return paths

def getSanpyReportsPdfPath() -> str:
    """Get the full path to the sanpy reports pdf folder.

    'sanpy-reports-pdf'
    """
    pdfPath = os.path.join(_ROOT_ANALYSIS_FOLDER, _ROOT_SANPY_REPORT_FOLDER)
    if not os.path.isdir(pdfPath):
        os.makedirs(pdfPath)
    return pdfPath

def getCellIdPdfFolder(pdfOutputType: str,
                       cellId: str,
                       dateStr:str,
                       regionStr:str
                       ) -> str:
    """Get the full folder path to the cell id pdf folder.
    
    like 'Per Cell Cond Plots'

    Actually makes folders
    """
    reportPath = getSanpyReportsPdfPath()
    reportPath = os.path.join(reportPath, pdfOutputType)
    if not os.path.exists(reportPath):
        # like 'Per Cell Cond Plots'
        os.mkdir(reportPath)
    
    # make date folders
    reportPath = os.path.join(reportPath, dateStr)
    if not os.path.exists(reportPath):
        os.mkdir(reportPath)

    # make region folders
    reportPath = os.path.join(reportPath, regionStr)
    if not os.path.exists(reportPath):
        os.mkdir(reportPath)

    return reportPath

def iterate_unique_cell_rows(df: pd.DataFrame, cellID: str, roiNumber: int = None):
    """Iterator function that returns unique rows from DataFrame for a given cellID.
    
    Args:
        df: DataFrame with columns 'Cell ID', 'Condition', 'Epoch'
        cellID: The cell ID to filter by
        roiNumber: Optional ROI number to filter by
        
    Yields:
        pd.Series: Each unique row for the given cellID (unique by Condition and Epoch)
    """
    # Filter DataFrame for the given cellID
    cell_df = df[df['Cell ID'] == cellID]

    if roiNumber is not None:
        roiNumber = int(roiNumber)
        cell_df = cell_df[cell_df['ROI Number'] == roiNumber]

    # Get unique combinations of Condition and Epoch
    # Use drop_duplicates to remove duplicate rows based on these columns
    unique_rows = cell_df.drop_duplicates(subset=['Condition', 'Epoch'])

    # Yield each unique row
    for _, row in unique_rows.iterrows():
        yield row

def loadAllKymRoiAnalysis(loadImgData=True) -> dict:
    """Load analysis for each tif and store in a dict.
    
    keys are tif path
    values are KymRoiAnalysis
    """
    retDict = {}
    # from sanpy.kym.simple_scatter.colin_global import getAllTifFilePaths
    tifPaths = getAllTifFilePaths()
    logger.info(f'loading all kym roi analysis from {len(tifPaths)} tif files, loadImgData:{loadImgData}')
    for tifPath in tifPaths:
        # print(tifPath)
        ka = _loadKymRoiAnalysis(tifPath, loadImgData=loadImgData)
        retDict[tifPath] = ka
    return retDict

def _loadKymRoiAnalysis(tifPath, loadImgData=True):
    """Load one kymRoiAnalysis..
    """
    # ba = bAnalysis(tifPath)
    # imgData = ba.fileLoader._tif  # list of color channel images
    # logger.info(f'imgData:{imgData[0].shape} {np.min(imgData[0])} {np.max(imgData[0])} {np.mean(imgData[0])}')
    ka = KymRoiAnalysis(tifPath,
                        # imgData=imgData,
                        loadImgData=loadImgData)
    return ka

if __name__ == '__main__':
    print('')
    
    # getAllPeakAnalysisCsv()
    # print(getMasterDfPath())
    # print(getMeanDfPath())

    # df = loadMeanDfFile()
    # print(df.columns)

    # if use passes DELETE_ALL_SANPY_ANALYSIS, delete all sanpy analysis
    if 'DELETE_ALL_SANPY_ANALYSIS' in sys.argv:
        # delete all 'sanpy-kym-roi-analysis' folders
        logger.warning('=== DELETING ALL SANPY ANALYSIS CSV FILES')
        logger.warning(getRootAnalysisFolder())
        csv = getAllSanPyAnalysisCsv()
        for path in csv:
            _path, _file = os.path.split(path)
            if 'sanpy-kym-roi-analysis' in _path:
                if os.path.isdir(_path):
                    shutil.rmtree(_path)
                # else:
                #     os.remove(path)
            # pass

        logger.warning(f'  deleted {len(csv)} csv files.')

        # delete folder with all pdf
        pdfPath = getSanpyReportsPdfPath()
        logger.warning('=== DELETING ALL SANPY output pdf')
        if os.path.isdir(pdfPath):
            logger.info('  deleting folder pdf folder:')
            logger.info(f'    {pdfPath}')
            shutil.rmtree(pdfPath)


    # print(getSanpyReportsPdfPath())
    # print(getCellIdPdfFolder('test pdf out', 'fakecellid', '20250521', 'left'))