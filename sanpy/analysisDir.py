# Acknowledgements:
# Author: Robert H Cudmore
# Date: 20210603

import os, time, sys
import random
import copy  # For copy.deepcopy() of bAnalysis
import uuid  # to generate unique key on bAnalysis spike detect
import pathlib  # ned to use this (introduced in Python 3.4) to maname paths on Windows, stop using os.path

from typing import List, Union, Optional

import numpy as np
import pandas as pd
import requests, io  # too load from the web

# for old code that was compressing hdf5 files
# from subprocess import call # to call ptrepack (might fail on windows???)
# from pprint import pprint
# import tables.scripts.ptrepack  # to save compressed .h5 file
# import shutil

import sanpy
import sanpy.h5Util

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

# Turn off pandas save h5 performance warnnig
# see: https://github.com/pandas-dev/pandas/issues/3622
# /home/cudmore/Sites/SanPy/sanpy/analysisDir.py:478: PerformanceWarning:
# your performance may suffer as PyTables will pickle object types that it cannot
# map directly to c-types [inferred_type->mixed-integer,key->block0_values] [items->Index(['detectionClass', '_isAnalyzed', '_dataPointsPerMs', '_sweepList',
import warnings

warnings.filterwarnings("ignore", category=pd.io.pytables.PerformanceWarning)

_sanpyColumns = {
    #'Idx': {
    #    #'type': int,
    #    'type': float,
    #    'isEditable': False,
    # },
    "L": {
        # loaded
        "type": str,
        "isEditable": False,
    },
    "A": {
        # analyzed
        "type": str,
        "isEditable": False,
    },
    "S": {
        # saved
        "type": str,
        "isEditable": False,
    },
    "N": {
        # number of spikes
        "type": int,
        "isEditable": False,
    },
    "E": {
        # number of errors
        "type": int,
        "isEditable": False,
    },
    # 'I': {
    #     # include
    #     # problems with isinstance(bool), just using string
    #     'type': bool,
    #     'isEditable': True,
    # },
    "File": {
        "type": str,
        "isEditable": False,
    },
    "Dur(s)": {
        "type": float,
        "isEditable": False,
    },
    "Channels": {  # For Thianne
        "type": int,
        "isEditable": False,
    },
    "Sweeps": {
        "type": int,
        "isEditable": False,
    },
    "Epochs": {  # For Thianne
        "type": int,
        "isEditable": False,
    },
    "kHz": {
        "type": float,
        "isEditable": False,
    },
    "Mode": {
        "type": str,
        "isEditable": False,
    },
    "Start(s)": {
        "type": float,
        "isEditable": False,
    },
    "Stop(s)": {
        "type": float,
        "isEditable": False,
    },
    "dvdtThreshold": {
        "type": float,
        "isEditable": True,
    },
    "mvThreshold": {
        "type": float,
        "isEditable": True,
    },
    "Cell Type": {
        "type": str,
        "isEditable": True,
    },
    # "Sex": {
    #     "type": str,
    #     "isEditable": True,
    # },

    # "Condition": {
    #     "type": str,
    #     "isEditable": True,
    # },

    # # bAnalysis metadata
    # metaDataDict = sanpy.bAnalysis.getMetaDataDict()
    # for k,v in metaDataDict.items()
        # _metaData = {
        #     'include': 'yes',
        #     'condition1': '',
        #     'condition2': '',
        #     'ID': '',
        #     'age': '',
        #     'sex': 'unknown',
        #     'age': '',
        #     'genotype': '',
        #     'note': '',
        # }

    "Include": {
        "type": str,
        "isEditable": True,
    },
    "Condition1": {
        "type": str,
        "isEditable": True,
    },
    "Condition2": {
        "type": str,
        "isEditable": True,
    },
    "ID": {
        "type": str,
        "isEditable": True,
    },
    "Age": {
        "type": str,
        "isEditable": True,
    },
    "Sex": {
        "type": str,
        "isEditable": True,
    },
    "Genotype": {
        "type": str,
        "isEditable": True,
    },
    "Note": {
        "type": str,
        "isEditable": True,
    },

    "parent1": {
        "type": str,
        "isEditable": False,
    },
    "parent2": {
        "type": str,
        "isEditable": False,
    },
    "parent3": {
        "type": str,
        "isEditable": False,
    },

    # kymograph interface
    # "kLeft": {
    #     "type": int,
    #     "isEditable": False,
    # },
    # "kTop": {
    #     "type": int,
    #     "isEditable": False,
    # },
    # "kRight": {
    #     "type": int,
    #     "isEditable": False,
    # },
    # "kBottom": {
    #     "type": int,
    #     "isEditable": False,
    # },

    "relPath": {
        "type": str,
        "isEditable": False,
    },
    "uuid": {
        "type": str,
        "isEditable": False,
    },
}


"""
Columns to use in display in file table (pyqt, dash, vue).
We require type so we can edit with QAbstractTableModel.
Critical for qt interface to allow easy editing of values while preserving type
"""


def _fixRelPath(folderPath, dfTable: pd.DataFrame, fileList: List[str]):
    """
    Was not assigning relPath on initial load (no hd5 file).

    We need a path relative to location of loaded folder.
    This allows a folder of files and analysis to be moved (to a different machine)
    """

    # print('fileList:', fileList)
    # pprint(dfTable[['File', 'relPath']])

    # if dfTable is None:
    #     logger.error('no dfTable')

    n = len(dfTable)

    logger.info(f"Checking path for {n} file(s)")

    for rowIdx in range(n):
        file = dfTable.loc[rowIdx, "File"]
        relPath = dfTable.loc[rowIdx, "relPath"]

        # 20220422 why was this here?
        # if relPath:
        #    continue

        # print(rowIdx, file, relPath)
        for filePath in fileList:
            if filePath.find(file) != -1:
                logger.info(
                    f"    _fixRelPath() file idx {rowIdx} file:{file} now has relPath:{filePath}"
                )
                dfTable.loc[rowIdx, "relPath"] = filePath


def old_h5_printKey(hdfPath):
    logger.info(f"hdfPath: {hdfPath} has keys:")
    with pd.HDFStore(hdfPath, mode="r") as store:
        for key in store.keys():
            logger.info(f"    {key}")


class bAnalysisDirWeb:
    """
    Load a directory of .abf from the web (for now from GitHub).

    Will etend this to Box, Dropbox, other?.
    """

    def __init__(self, cloudDict):
        """
        Args: cloudDict (dict): {
                    'owner': 'cudmore',
                    'repo_name': 'SanPy',
                    'path': 'data'
                    }
        """
        self._cloudDict = cloudDict
        self.loadFolder()

    def loadFolder(self):
        """Load using cloudDict"""

        """
        # use ['download_url'] to download abf file (no byte conversion)
        response[0] = {
            name : 171116sh_0018.abf
            path : data/171116sh_0018.abf
            sha : 5f3322b08d86458bf7ac8b5c12564933142ffd17
            size : 2047488
            url : https://api.github.com/repos/cudmore/SanPy/contents/data/171116sh_0018.abf?ref=master
            html_url : https://github.com/cudmore/SanPy/blob/master/data/171116sh_0018.abf
            git_url : https://api.github.com/repos/cudmore/SanPy/git/blobs/5f3322b08d86458bf7ac8b5c12564933142ffd17
            download_url : https://raw.githubusercontent.com/cudmore/SanPy/master/data/171116sh_0018.abf
            type : file
            _links : {'self': 'https://api.github.com/repos/cudmore/SanPy/contents/data/171116sh_0018.abf?ref=master', 'git': 'https://api.github.com/repos/cudmore/SanPy/git/blobs/5f3322b08d86458bf7ac8b5c12564933142ffd17', 'html': 'https://github.com/cudmore/SanPy/blob/master/data/171116sh_0018.abf'}
        }
        """

        owner = self._cloudDict["owner"]
        repo_name = self._cloudDict["repo_name"]
        path = self._cloudDict["path"]
        url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{path}"

        # response is a list of dict
        response = requests.get(url).json()
        # print('response:', type(response))

        for idx, item in enumerate(response):
            if not item["name"].endswith(".abf"):
                continue
            print(idx)
            # use item['git_url']
            for k, v in item.items():
                print("  ", k, ":", v)

        #
        # test load
        download_url = response[1]["download_url"]
        content = requests.get(download_url).content

        fileLikeObject = io.BytesIO(content)
        ba = sanpy.bAnalysis(byteStream=fileLikeObject)
        # print(ba._abf)
        # print(ba.api_getHeader())
        ba.spikeDetect()
        print(ba.numSpikes)


import os
from glob import glob

def _old_santana_file_finder(files):
    """
    
    Parameters
    ----------
    files: List[str]
        List of full file path.
    
    cell 05_C001T001.tif
    cell 05_C002T001.tif
    cell 05.txt

    cell 08_0002_C001T001.tif
    cell 08_0002_C002T001.tif
    cell 08_0002.txt

    Text file name is prefix up to _C0
    """
    #path = '/Users/cudmore/Dropbox/data/cell-shortening/fig1'


    retDict = {}
    
    # list of full path to tif files in all subfolders
    # files = [y for x in os.walk(path) for y in glob(os.path.join(x[0], '*.tif'))]
    #files = sanpy._util.getFileList(path)

    for file in files:
        if not file.endswith('.tif'):
            continue
        
        # we only want to load channel 2 (Ca++)
        if file.find('_C002') == -1:
            continue
        
        filePath, fileName = os.path.split(file)

        otherFileName = fileName.replace('_C002', '_C001')
        otherFilePath = os.path.join(filePath, otherFileName)
        if not os.path.isfile(otherFilePath):
            print(f'Did not find other file "{otherFileName}" for {file}')
            otherFilePath = ''

        _idx = fileName.find('_C')
        filePrefix = fileName[0:_idx]
    
        txtFileName = filePrefix + '.txt'
        txtFilePath = os.path.join(filePath, txtFileName)
        if not os.path.isfile(txtFilePath):
            print(f'Did not find txt file for {file}')
            txtFilePath = ''

        retDict[file] = {
            'otherFilePath': otherFilePath,
            'txtFilePath': txtFilePath,
        }

    #print('n=', len(files))
    return retDict

def _listdir(path, theseFileTypes):
    """
    recursively walk directory to specified depth
    :param path: (str) path to list files from
    :yields: (str) filename, including path
    """
    for filename in os.listdir(path):
        _filebase, _ext = os.path.splitext(filename)
        if filename.startswith('.'):
            continue
        if not _ext in theseFileTypes:
            continue
        yield os.path.join(path, filename)


def _walk(path, theseFileTypes, depth=None):
    """
    recursively walk directory to specified depth
    :param path: (str) the base path to start walking from
    :param depth: (None or int) max. recursive depth, None = no limit
    :yields: (str) filename, including path
    """
    if depth and depth == 1:
        for filename in _listdir(path, theseFileTypes):
            yield filename
    else:
        top_pathlen = len(path) + len(os.path.sep)
        for dirpath, dirnames, filenames in os.walk(path):
            dirlevel = dirpath[top_pathlen:].count(os.path.sep)
            if depth and dirlevel >= depth:
                dirnames[:] = []
            else:
                for filename in filenames:
                    _filebase, _ext = os.path.splitext(filename)
                    if filename.startswith('.'):
                        continue
                    if not _ext in theseFileTypes:
                        continue
                    yield os.path.join(dirpath, filename)
                    
def getFileList(path, theseFileTypes, depth=1):
    fileList = [filePath for filePath in _walk(path, theseFileTypes, depth)]
    return fileList

def stripSantanaTif(fileList : List[str]) -> List[str]:
    """Given a list of files, if tif, only return _C002
    """
    retList = []
    for file in fileList:
        _filePath, _filename = os.path.split(file)
        if not _filename.endswith('.tif'):
            retList.append(file)
            continue
        # elif _filename.find('_C002') != -1:
        #     retList.append(file)
        elif _filename.find('_C001') != -1:
            continue
        else:
            retList.append(file)
        
    return retList

class analysisDir:
    """
    Class to manage a list of files loaded from a folder.
    """

    sanpyColumns = _sanpyColumns
    """Dict of dict of column names and bookkeeping info.
    """

    theseFileTypes = [".abf", ".atf", ".sanpy", ".dat", ".tif"]
    """File types to load.
    """

    def __init__(
        self,
        path: str = None,
        myApp : "sanpy.interface.sanpy_app" = None,
        autoLoad: bool = False,
        folderDepth: Optional[int] = None,
    ):
        """Load and manage a list of files in a folder path.

        Use this as the main pandasModel for file list myTableView.

        TODO: extend to link to folder in cloud (start with box and/or github)

        Args:
            path (str): Path to folder
            myApp (sanpy.interface.sanpy_app): Optional
            autoLoad (bool):
            folderDepth (int):
            #cloudDict (dict): To load from cloud, for now  just github

        Notes:
            - Some functions are so self can mimic a pandas dataframe used by pandasModel.
                (shape, loc, loc_setter, iloc, iLoc_setter, columns, append, drop, sort_values, copy)
        """
        self.path: str = path
        self.myApp = myApp  # used to signal on building initial db
        self.autoLoad = autoLoad  # not used

        self.folderDepth = folderDepth  # specify int

        self._isDirty = False

        # self._poolDf = None
        """See pool_ functions"""

        # keys are full path to file, if from cloud, key is 'cloud/<filename>'
        # holds bAnalysisObjects
        # needs to be a list so we can have files more than one
        # self.fileList = [] #OrderedDict()

        # TODO: refactor, we are not using the csv parth of this, just the filename
        # name of database file created/loaded from folder path
        self.dbFile = "sanpy_recording_db.csv"

        self._df = None
        # if autoLoad:
        if 1:
            self._df = self.loadHdf()
            if self._df is None:
                self._df = self.loadFolder(loadData=autoLoad)  # only used if no h5 file
                self._updateLoadedAnalyzed()

        # self._df = self.loadFolder(loadData=autoLoad)

        #
        self._checkColumns()
        self._updateLoadedAnalyzed()

        """
        logger.warning('remember: temporary fix with _fixRelPath()\n')
        tmpFileList = self.getFileList()
        _fixRelPath(self.path, self._df, tmpFileList)
        """

    def __iter__(self):
        self._iterIdx = -1
        return self
        
        # self._iterIdx = 0
        # logger.info(f'making iter for bAnalysisDir')
        # print(self._df)
        # x = self._df.loc[self._iterIdx]["_ba"]
        # return x
    
    def __next__(self):
        self._iterIdx += 1
        if self._iterIdx >= self.numFiles:
            self._iterIdx = -1  # reset to initial value
            raise StopIteration
        else:
            return self._df.loc[self._iterIdx]["_ba"]

        # if self._iterIdx < self.numFiles:
        #     x = self._df.loc[self._iterIdx]["_ba"]
        #     self._iterIdx += 1
        #     return x
        # else:
        #     raise StopIteration

    def __str__(self):
        totalDurSec = self._df["Dur(s)"].sum()
        theStr = f"analysisDir Num Files: {len(self)} Total Dur(s): {totalDurSec}"
        return theStr

    @property
    def isDirty(self):
        return self._isDirty

    def __len__(self):
        return len(self._df)

    @property
    def numFiles(self):
        return len(self._df)

    @property
    def shape(self):
        """
        Can't just return shape of _df, columns (like 'ba') may have been added
        Number of columns is based on self.columns
        """
        # return self._df.shape
        numRows = self._df.shape[0]
        numCols = len(self.columns)
        return (numRows, numCols)

    @property
    def loc(self):
        """Mimic pandas df.loc[]"""
        return self._df.loc

    @loc.setter
    def loc_setter(self, rowIdx, colStr, value):
        self._df.loc[rowIdx, colStr] = value

    @property
    def iloc(self):
        # mimic pandas df.iloc[]
        return self._df.iloc

    @iloc.setter
    def iLoc_setter(self, rowIdx, colIdx, value):
        self._df.iloc[rowIdx, colIdx] = value
        self._isDirty = True

    @property
    def at(self):
        # mimic pandas df.at[]
        return self._df.at

    @at.setter
    def at_setter(self, rowIdx, colStr, value):
        self._df.at[rowIdx, colStr] = value
        self._isDirty = True

    """
    @property
    def iat(self):
        # mimic pandas df.iat[]
        return self._df.iat

    @iat.setter
    def iat_setter(self, rowIdx, colStr, value):
        self._df.iat[rowIdx, colStr] = value
        self._isDirty = True
    """

    @property
    def index(self):
        return self._df.index

    @property
    def columns(self):
        # return list of column names
        return list(self.sanpyColumns.keys())

    def copy(self):
        return self._df.copy()

    def sort_values(self, Ncol, order):
        logger.info(f"sorting by column {self.columns[Ncol]} with order:{order}")
        self._df = self._df.sort_values(self.columns[Ncol], ascending=not order)
        # print(self._df)

    @property
    def columnsDict(self):
        return self.sanpyColumns

    def columnIsEditable(self, colName):
        return self.sanpyColumns[colName]["isEditable"]

    def columnIsCheckBox(self, colName):
        """All bool columns are checkbox

        TODO: problems with using type=bool and isinstance(). Kust using str 'bool'
        """
        type = self.sanpyColumns[colName]["type"]
        # isBool = isinstance(type, bool)
        isBool = type == "bool"
        # logger.info(f'{colName} {type(type)}, type:{type} {isBool}')
        return isBool

    def getDataFrame(self):
        """Get the underlying pandas DataFrame."""
        return self._df

    @property
    def numFiles(self):
        """Get the number of files. same as len()."""
        return len(self._df)

    def copyToClipboard(self):
        """
        TODO: Is this used or is copy to clipboard in pandas model?
        """
        if self.getDataFrame() is not None:
            self.getDataFrame().to_clipboard(sep="\t", index=False)
            logger.info("Copied to clipboard")

    def old_saveDatabase(self):
        """save dbFile .csv and hdf .gzip"""
        dbPath = os.path.join(self.path, self.dbFile)
        if self.getDataFrame() is not None:
            #
            logger.info(f'Saving "{dbPath}"')
            self.getDataFrame().to_csv(dbPath, index=False)
            self._isDirty = False

            #
            """
            hdfFile = os.path.splitext(self.dbFile)[0] + '.h5'
            hdfPath = os.path.join(self.path, hdfFile)
            logger.info(f'Saving "{hdfPath}"')
            #hdfStore = pd.HDFStore(hdfPath)
            start = time.time()
            complevel = 9
            complib = 'blosc:blosclz'
            with pd.HDFStore(hdfPath, mode='w', complevel=complevel, complib=complib) as hdfStore:
                hdfStore['df'] = self.getDataFrame()  # save it
            stop = time.time()
            logger.info(f'Saving took {round(stop-start,2)} seconds')
            """

    def old_getFrozenPath(self):
        if getattr(sys, "frozen", False):
            # running in a bundle (frozen)
            myPath = sys._MEIPASS
        else:
            # running in a normal Python environment
            # myPath = os.path.dirname(os.path.abspath(__file__))
            myPath = pathlib.Path(__file__).parent.absolute()
        return myPath

    def _old_rebuildHdf(self):
        #
        # rebuild the file to remove old changes and reduce size
        tmpHdfFile = os.path.splitext(self.dbFile)[0] + "_tmp.h5"
        # tmpHdfPath = os.path.join(self.path, tmpHdfFile)
        tmpHdfPath = pathlib.Path(self.path) / tmpHdfFile

        hdfFile = os.path.splitext(self.dbFile)[0] + ".h5"
        # hdfPath = os.path.join(self.path, hdfFile)
        hdfPath = pathlib.Path(self.path) / hdfFile
        logger.info(f"Rebuilding h5 to {hdfPath}")

        # can't pass sys.argv a 'PosixPath' from pathlib.Path, needs to be a string
        tmpHdfPath = str(tmpHdfPath)
        hdfPath = str(hdfPath)

        # when calling ptrepack, we need trailing ':' on each src/dst path
        # without this Windows fails to find the file
        _tmpHdfPath = tmpHdfPath + ":"
        _hdfPath = hdfPath + ":"

        # The first item is normally the command line command name (not used)
        sys.argv = ["", "--overwrite", "--chunkshape=auto", _tmpHdfPath, _hdfPath]

        logger.info("running tables.scripts.ptrepack.main()")
        logger.info(f"sys.argv: {sys.argv}")
        try:
            tables.scripts.ptrepack.main()  # noqa

            # delete the temporary (large file)
            logger.info(f"Deleting tmp file: {tmpHdfPath}")
            os.remove(tmpHdfPath)

            self.signalApp(
                f"Saved compressed folder analysis with tables.scripts.ptrepack.main()"
            )

        except FileNotFoundError as e:
            logger.error("tables.scripts.ptrepack.main() failed ... file was not saved")
            logger.error(e)
            self.signalApp(f"ERROR in tables.scripts.ptrepack.main(): {e}")

    def _not_used_save(self):
        """Save all analysis as csv."""
        logger.info("")
        for ba in self:
            if ba is not None:
                # save detection and analysis to json
                # ba.saveAnalysis(forceSave=True)

                # save analysis to csv
                ba.saveAnalysis_tocsv()

    def _old_getTmpHdfFile(self):
        """Get temporary h5 file to write to.

        We will always then compress with _rebuildHdf.
        """
        logger.info("")

        tmpHdfFile = os.path.splitext(self.dbFile)[0] + "_tmp.h5"
        tmpHdfPath = pathlib.Path(self.path) / tmpHdfFile

        # the compressed version from the last save
        hdfFile = os.path.splitext(self.dbFile)[0] + ".h5"
        hdfFilePath = pathlib.Path(self.path) / hdfFile

        # hdfMode = 'w'
        if os.path.isfile(hdfFilePath):
            logger.info(f"    copying existing hdf file to tmp ")
            logger.info(f"    hdfFilePath {hdfFilePath}")
            logger.info(f"    tmpHdfPath {tmpHdfPath}")
            shutil.copyfile(hdfFilePath, tmpHdfPath)  # noqa
        else:
            pass
            # compressed file does not exist, just use tmp path
            # print('   does not exist:', hdfFilePath)

        return tmpHdfPath

    def getPathFromRelPath(self, relPath):
        """Get full path to file from relPath.
        
        Uses analysisDir folder path.
        """
        if relPath.startswith("/"):
            relPath = relPath[1:]

        fullFilePath = os.path.join(self.path, relPath)

        """
        print('xxx', self.path)
        print('xxx', relPath)
        print('xxx', fullFilePath)
        """

        return fullFilePath

    def saveHdf(self):
        """Save file table and any number of loaded and analyzed bAnalysis.

        Set file table 'uuid' column when we actually save a bAnalysis

        Important: Order matters
                (1) Save bAnalysis first, it updates uuid in file table.
                (2) Save file table with updated uuid
        """
        start = time.time()

        df = self.getDataFrame()

        # the compressed version from the last save
        hdfFile = os.path.splitext(self.dbFile)[0] + ".h5"
        hdfFilePath = pathlib.Path(self.path) / hdfFile

        logger.info(f"Saving db (will be compressed) {hdfFilePath}")

        # save each bAnalysis
        for row in range(len(df)):
            ba = df.at[row, "_ba"]
            if ba is not None:
                didSave = ba._saveHdf_pytables(hdfFilePath)
                if didSave:
                    # we are now saved into h5 file, remember uuid to load
                    # print('xxx SETTING dir uuid')
                    df.at[row, "uuid"] = ba.uuid

        # rebuild (L, A, S) columns
        self._updateLoadedAnalyzed()

        #
        # save file database
        logger.info(f"    saving file db with {len(df)} rows")
        print(df)

        dbKey = os.path.splitext(self.dbFile)[0]
        df = df.drop("_ba", axis=1)  # don't ever save _ba, use it for runtime

        # hdfStore[dbKey] = df  # save it
        df.to_hdf(hdfFilePath, dbKey)

        #
        self._isDirty = False  # if true, prompt to save on quit

        # rebuild the file to remove old changes and reduce size
        # self._rebuildHdf()
        sanpy.h5Util._repackHdf(hdfFilePath)

        # list the keys in the file
        # sanpy.h5Util.listKeys(hdfFilePath)

        stop = time.time()
        logger.info(f"Saving took {round(stop-start,2)} seconds")

    def loadHdf(self, path=None, verbose=False):
        """Load the database key from an h5 file.

        We do not load analy anlysis until user clicks on row, see loadOneAnalysis()
        """
        if path is None:
            path = self.path
        self.path = path

        df = None
        hdfFile = os.path.splitext(self.dbFile)[0] + ".h5"
        hdfPath = pathlib.Path(self.path) / hdfFile
        if not hdfPath.is_file():
            return

        # logger.info(f"Loading existing folder h5 file {hdfPath}")
        # sanpy.h5Util.listKeys(hdfPath)

        _start = time.time()
        dbKey = os.path.splitext(self.dbFile)[0]

        try:
            df = pd.read_hdf(hdfPath, dbKey)
        except KeyError as e:
            # file is corrupt !!!
            logger.error(f'    Load h5 failed, did not find dbKey:"{dbKey}" {e}')

        if df is not None:
            # _ba is for runtime, assign after loading from either (abf or h5)
            df["_ba"] = None

            # fix bug during dev of ba metadata
            # df['Sex'] = 'unknown'
            
            if verbose:
                logger.info("    loaded db df")

            _stop = time.time()
            # logger.info(f"Loading took {round(_stop-_start,2)} seconds")
        #
        return df

    def loadOneAnalysis(self, path, uuid=None, allowAutoLoad=True, verbose=False):
        """Load one bAnalysis either from original file path or uuid of h5 file.

        If from h5, we still need to reload sweeps !!!
        They are binary and fast, saving to h5 (in this case) is slow.
        """
        if verbose:
            logger.info(f'path:"{path}" uuid:"{uuid}" allowAutoLoad:"{allowAutoLoad}"')

        hdfPath = self._getHdfFile()

        # grab the fileLoaderDict from our app
        # if it is None then bAnalysis will load this (from disk)
        if self.myApp is not None:
            _fileLoaderDict = self.myApp.getFileLoaderDict()
        else:
            _fileLoaderDict = None

        ba = None
        if uuid is not None and uuid:
            # load from h5
            if verbose:
                logger.info(f"    Retreiving uuid from hdf file {uuid}")

            # load from abf
            ba = sanpy.bAnalysis(path, fileLoaderDict=_fileLoaderDict, verbose=verbose)

            # load analysis from h5 file, will fail if uuid is not in file
            ba._loadHdf_pytables(hdfPath, uuid)

        if allowAutoLoad and ba is None:
            # load from path
            ba = sanpy.bAnalysis(path, fileLoaderDict=_fileLoaderDict, verbose=verbose)
            if verbose:
                logger.info(f"    Loaded ba from path {path} and now ba:{ba}")
        #
        return ba

    def _getHdfFile(self):
        hdfFile = os.path.splitext(self.dbFile)[0] + ".h5"
        hdfPath = os.path.join(self.path, hdfFile)
        return hdfPath

    def _deleteFromHdf(self, uuid):
        """Delete uuid from h5 file.

        Each bAnalysis detection get a unique uuid.
        """
        if uuid is None or not uuid:
            return
        logger.info(f"deleting from h5 file uuid:{uuid}")

        _hdfFile = os.path.splitext(self.dbFile)[0] + ".h5"
        hdfPath = pathlib.Path(self.path) / _hdfFile

        # tmpHdfPath = self._getTmpHdfFile()

        removed = False
        with pd.HDFStore(hdfPath) as hdfStore:
            try:
                hdfStore.remove(uuid)
                removed = True
            except KeyError:
                logger.error(f"Did not find uuid {uuid} in h5 file {hdfPath}")

        #
        if removed:
            # will rebuild on next save
            # self._rebuildHdf()
            self._updateLoadedAnalyzed()
            self._isDirty = True  # if true, prompt to save on quit

    def loadFolder(self, path=None, loadData=False):
        """
        Parse a folder and load all (abf, csv, ...). Only called if no h5 file.

        TODO: get rid of loading database from .csv (it is replaced by .h5 file)
        TODO: extend the logic to load from cloud (after we were instantiated)
        """
        logger.info("Loading folder from scratch (no hdf file)")

        start = time.time()
        if path is None:
            path = self.path
        self.path = path

        loadedDatabase = False

        # load an existing folder db or create a new one
        # abb 20220612 turned off loading from self.dbFile .csv file
        dbPath = os.path.join(path, self.dbFile)
        if 0 and os.path.isfile(dbPath):
            # load from .csv
            logger.info(f"Loading existing folder db: {dbPath}")
            df = pd.read_csv(dbPath, header=0, index_col=False)
            # df["Idx"] = pd.to_numeric(df["Idx"])
            df = self._setColumnType(df)
            loadedDatabase = True
            # logger.info(f'  shape is {df.shape}')
        else:
            # logger.info(f'No existing db file, making {dbPath}')
            logger.info(f"No existing db file, making default dataframe")
            df = pd.DataFrame(columns=self.sanpyColumns.keys())
            df = self._setColumnType(df)

        if loadedDatabase:
            # check columns with sanpyColumns
            loadedColumns = df.columns
            for col in loadedColumns:
                if not col in self.sanpyColumns.keys():
                    logger.error(
                        f'error: bAnalysisDir did not find loaded col: "{col}" in sanpyColumns.keys()'
                    )
            for col in self.sanpyColumns.keys():
                if not col in loadedColumns:
                    logger.error(
                        f'error: bAnalysisDir did not find sanpyColumns.keys() col: "{col}" in loadedColumns'
                    )

        if loadedDatabase:
            # seach existing db for missing abf files
            pass
        else:
            # get list of all abf/csv/tif files
            fileList = self.getFileList(path)
            _numFilesToLoad = len(fileList)
            start = time.time()
            # build new db dataframe
            listOfDict = []
            for rowIdx, fullFilePath in enumerate(fileList):
                self.signalApp(
                    f'Loading file {rowIdx+1} of {_numFilesToLoad} "{fullFilePath}"'
                )

                # rowDict is what we are showing in the file table
                # abb debug vue, set loadData=True
                # loads bAnalysis
                ba, rowDict = self.getFileRow(fullFilePath, loadData=loadData)

                if rowDict is None:
                    logger.warning(f'error loading file {fullFilePath}')
                    continue
                
                # print('XXX')
                # print('rowDict')
                # print(rowDict)

                # TODO: calculating time, remove this
                # This is 2x faster than loading from pandas gzip ???
                # dDict = sanpy.bAnalysis.getDefaultDetection()
                # dDict['dvdtThreshold'] = 2
                # ba.spikeDetect(dDict)

                # as we parse the folder, don't load ALL files (will run out of memory)
                if loadData:
                    rowDict["_ba"] = ba
                else:
                    rowDict["_ba"] = None  # ba

                # do not assign uuid until bAnalysis is saved in h5 file
                # rowDict['uuid'] = ''

                # 20230313 moved into getFileRow()
                # relPath = fullFilePath.replace(path, '')
                # if relPath.startswith('/'):
                #     # so we can use os.path.join()
                #     relPath = relPath[1:]
                # rowDict['relPath'] = relPath

                # logger.info(f'    row:{rowIdx} relPath:{relPath} fullFilePath:{fullFilePath}')

                listOfDict.append(rowDict)

            stop = time.time()
            logger.info(f"Load took {round(stop-start,3)} seconds.")

            #
            df = pd.DataFrame(listOfDict)
            # print('=== built new db df:')
            # print(df)
            df = self._setColumnType(df)
        #

        # expand each to into self.fileList
        # df['_ba'] = None

        stop = time.time()
        logger.info(f"Load took {round(stop-start,2)} seconds.")
        return df

    def _checkColumns(self):
        """Check columns in loaded vs sanpyColumns (and vica versa).
        """
        if self._df is None:
            return
        
        verbose = True
        loadedColumns = self._df.columns
        for col in loadedColumns:
            if not col in self.sanpyColumns.keys():
                # loaded has unexpected column, leave it
                if verbose:
                    logger.info(
                        f'did not find loaded col: "{col}" in sanpyColumns.keys() ... ignore it'
                    )
        for col in self.sanpyColumns.keys():
            if not col in loadedColumns:
                # loaded is missing expected, add it
                logger.info(
                    f'did not find sanpyColumns.keys() col: "{col}" in loadedColumns ... adding col'
                )
                self._df[col] = ""

    def _updateLoadedAnalyzed(self, theRowIdx=None):
        """Refresh Loaded (L) and Analyzed (A) columns.

        Arguments:
            theRowIdx (int): Update just one row

        TODO: For kymograph, add rows (left, top, right, bottom) and update
        """
        if self._df is None:
            return
        for rowIdx in range(len(self._df)):
            if theRowIdx is not None and theRowIdx != rowIdx:
                continue

            ba = self._df.loc[rowIdx, "_ba"]  # Can be None

            # uuid = self._df.at[rowIdx, 'uuid']
            #
            # loaded
            if self.isLoaded(rowIdx):
                theChar = "\u2022"  # FILLED BULLET
            # elif uuid:
            #    #theChar = '\u25CB'  # open circle
            #    theChar = '\u25e6'  # white bullet
            else:
                theChar = ""
            # self._df.iloc[rowIdx, loadedCol] = theChar
            self._df.loc[rowIdx, "L"] = theChar
            #
            # analyzed
            if self.isAnalyzed(rowIdx):
                theChar = "\u2022"  # FILLED BULLET
                self._df.loc[rowIdx, "N"] = ba.numSpikes
                _numErrors = ba.numErrors
                if _numErrors is None:
                    _numErrors = ''
                # logger.warning(f'setting E to _numErrors {_numErrors}')
                self._df.loc[rowIdx, "E"] = _numErrors
            # elif uuid:
            #    #theChar = '\u25CB'
            #    theChar = '\u25e6'  # white bullet
            else:
                theChar = ""
                self._df.loc[rowIdx, "A"] = ""
            # self._df.iloc[rowIdx, analyzedCol] = theChar
            self._df.loc[rowIdx, "A"] = theChar
            #
            # saved
            if self.isSaved(rowIdx):
                theChar = "\u2022"  # FILLED BULLET
            else:
                theChar = ""
            # self._df.iloc[rowIdx, savedCol] = theChar
            self._df.loc[rowIdx, "S"] = theChar
            #
            # start(s) and stop(s) from ba detectionDict
            if self.isAnalyzed(rowIdx):
                # set table to values we just detected with
                startSec = ba.getDetectionDict()["startSeconds"]
                stopSec = ba.getDetectionDict()["stopSeconds"]
                self._df.loc[rowIdx, "Start(s)"] = startSec
                self._df.loc[rowIdx, "Stop(s)"] = stopSec

                dvdtThreshold = ba.getDetectionDict()["dvdtThreshold"]
                mvThreshold = ba.getDetectionDict()["mvThreshold"]
                self._df.loc[rowIdx, "dvdtThreshold"] = dvdtThreshold
                self._df.loc[rowIdx, "mvThreshold"] = mvThreshold

                #
                # TODO: remove start of ba._path that corresponds to our current folder path
                # will allow our save db to be modular

                # relPth should usually be filled in ???
                """
                relPath = self.getPathFromRelPath(ba._path)
                self._df.loc[rowIdx, 'relPath'] = relPath
                """

                # logger.info('maybe put back in')
                # print(f'    self._df.loc[rowIdx, "relPath"] is "{self._df.loc[rowIdx, "relPath"]}"')

            # aug 2023, update meta data columns
            if ba is not None:
                for k,v in ba.metaData.items():
                    self._df.loc[rowIdx, k] = v

            # kymograph interface
            # 20230602, don't show rect in interface
            # if ba is not None and ba.fileLoader.isKymograph():
            #     kRect = ba.fileLoader.getKymographRect()

            #     # print(kRect)
            #     # sys.exit(1)

            #     if kRect is None:
            #         logger.error(f"Got None kymograph rect")
            #     else:
            #         self._df.loc[rowIdx, "kLeft"] = kRect[0]
            #         self._df.loc[rowIdx, "kTop"] = kRect[1]
            #         self._df.loc[rowIdx, "kRight"] = kRect[2]
            #         self._df.loc[rowIdx, "kBottom"] = kRect[3]
            #
            # TODO: remove start of ba._path that corresponds to our current folder path
            # will allow our save db to be modular
            # self._df.loc[rowIdx, 'path'] = ba._path

    """
    def setCellValue(self, rowIdx, colStr, value):
        self._df.loc[rowIdx, colStr] = value
    """

    def isLoaded(self, rowIdx):
        isLoaded = self._df.loc[rowIdx, "_ba"] is not None
        return isLoaded

    def isAnalyzed(self, rowIdx):
        isAnalyzed = False
        ba = self._df.loc[rowIdx, "_ba"]
        # print('isAnalyzed()', rowIdx, ba)
        # if ba is not None:
        # print('qqq', rowIdx, ba, type(ba))
        # sanpy.bAnalysis_.bAnalysis
        # if isinstance(ba, sanpy.bAnalysis):
        if ba is not None:
            isAnalyzed = ba.isAnalyzed()
        return isAnalyzed

    def analysisIsDirty(self, rowIdx):
        """Analysis is dirty when there has been detection but not saved to h5."""
        isDirty = False
        ba = self._df.loc[rowIdx, "_ba"]
        if isinstance(ba, sanpy.bAnalysis):
            isDirty = ba.isDirty()
        return isDirty

    def hasDirty(self):
        """Return true if any bAnalysis in list has been analyzed but not saved (e.g. is dirty)"""
        haveDirty = False
        numRows = len(self._df)
        for rowIdx in range(numRows):
            if self.analysisIsDirty(rowIdx):
                haveDirty = True

        return haveDirty

    def isSaved(self, rowIdx):
        uuid = self._df.at[rowIdx, "uuid"]
        return len(uuid) > 0

    def getAnalysis(self, rowIdx, allowAutoLoad=True, verbose=False) -> sanpy.bAnalysis:
        """Get bAnalysis object, will load if necc.

        Args:
            rowIdx (int): Row index from table, corresponds to row in self._df
            allowAutoLoad (bool)
        Return:
            bAnalysis
        """
        file = self._df.loc[rowIdx, "File"]
        ba = self._df.loc[rowIdx, "_ba"]
        uuid = self._df.loc[rowIdx, "uuid"]  # if we have a uuid bAnalysis is saved in h5f
        # filePath = os.path.join(self.path, file)
        # logger.info(f'Found _ba in file db with ba:"{ba}" {type(ba)}')
        # logger.info(f'rowIdx: {rowIdx} ba:{ba}')

        if ba is None or ba == "":
            # logger.info('did not find _ba ... loading from abf file ...')
            # working on kymograph
            #                 relPath = self.getPathFromRelPath(ba._path)
            relPath = self._df.loc[rowIdx, "relPath"]
            filePath = self.getPathFromRelPath(relPath)

            ba = self.loadOneAnalysis(
                filePath, uuid, allowAutoLoad=allowAutoLoad, verbose=verbose
            )
            # load
            """
            logger.info(f'Loading bAnalysis from row {rowIdx} "{filePath}"')
            ba = sanpy.bAnalysis(filePath)
            """
            if ba is None:
                logger.warning(
                    f'Did not load row {rowIdx} path: "{filePath}". Analysis was probably not saved'
                )
            else:
                self._df.at[rowIdx, "_ba"] = ba
                # does not get a uuid until save into h5
                if uuid:
                    # there was an original uuid (in table), means we are saved into h5
                    self._df.at[rowIdx, "uuid"] = uuid
                    if uuid != ba.uuid:
                        logger.error(
                            "Loaded uuid does not match existing in file table"
                        )
                        logger.error(f"  Loaded {ba.uuid}")
                        logger.error(f"  Existing {uuid}")

                # kymograph, set ba rect from table
                # if ba is not None and ba.fileLoader.isKymograph():
                #     left = self._df.loc[rowIdx, "kLeft"]
                #     top = self._df.loc[rowIdx, "kTop"]
                #     right = self._df.loc[rowIdx, "kRight"]
                #     bottom = self._df.loc[rowIdx, "kBottom"]

                #     # on first load, these will be empty
                #     # grab rect from ba (in _updateLoadedAnalyzed())
                #     if left == "" or top == "" or right == "" or bottom == "":
                #         pass
                #     else:
                #         theRect = [left, top, right, bottom]
                #         logger.info(f"  theRect:{theRect}")
                #         ba.fileLoader._updateTifRoi(theRect)

                #
                # update stats of table load/analyzed columns
                self._updateLoadedAnalyzed()

        return ba

    def _setColumnType(self, df):
        """Needs to be called every time a df is created.
        Ensures proper type of columns following sanpyColumns[key]['type']
        """
        # print('columns are:', df.columns)
        for col in df.columns:
            # when loading from csv, 'col' may not be in sanpyColumns
            if not col in self.sanpyColumns:
                logger.warning(f'Column "{col}" is not in sanpyColumns -->> ignoring')
                continue
            colType = self.sanpyColumns[col]["type"]
            # print(f'  _setColumnType() for "{col}" is type "{colType}"')
            # print(f'    df[col]:', 'len:', len(df[col]))
            # print(df[col])
            if colType == str:
                df[col] = df[col].replace(np.nan, "", regex=True)
                df[col] = df[col].astype(str)
            elif colType == int:
                pass
                # print('!!! df[col]:', df[col])
                # df[col] = df[col].astype(int)
            elif colType == float:
                # error if ''
                df[col] = df[col].astype(float)
            elif colType == bool:
                df[col] = df[col].astype(bool)
            else:
                logger.warning(f'Did not parse col "{col}" with type "{colType}"')
        #
        return df

    def getFileRow(self, path, loadData=False):
        """Get dict representing one file (row in table). Loads bAnalysis to get headers.

        On load error of proper file type (abf, csv), ba.loadError==True

        Args:
            path (Str): Full path to file.
            #rowIdx (int): Optional row index to assign in column 'Idx'

        Return:
            (tuple): tuple containing:

            - ba (bAnalysis): [sanpy.bAnalysis](/api/bAnalysis).
            - rowDict (dict): On success, otherwise None.
                    fails when path does not lead to valid bAnalysis file.
        """
        if not os.path.isfile(path):
            logger.warning(f'Did not find file "{path}"')
            return None, None
        fileType = os.path.splitext(path)[1]
        if fileType not in self.theseFileTypes:
            logger.warning(f'Did not load file type "{fileType}"')
            return None, None

        # grab the fileLoaderDict from our app
        # if it is None then bAnalysis will load this (from disk)
        if self.myApp is not None:
            _fileLoaderDict = self.myApp.getFileLoaderDict()
        else:
            _fileLoaderDict = None

        # load bAnalysis
        # logger.info(f'Loading bAnalysis "{path}"')
        # loadData is false, load header
        ba = sanpy.bAnalysis(path, loadData=loadData, fileLoaderDict=_fileLoaderDict)

        if ba.loadError:
            logger.error(f'Error loading bAnalysis file "{path}"')
            # return None, None

        # not sufficient to default everything to empty str ''
        # sanpyColumns can only have type in ('float', 'str')
        rowDict = dict.fromkeys(self.sanpyColumns.keys(), "")
        for k in rowDict.keys():
            if self.sanpyColumns[k]["type"] == str:
                rowDict[k] = ""
            elif self.sanpyColumns[k]["type"] == float:
                rowDict[k] = np.nan

        # if rowIdx is not None:
        #    rowDict['Idx'] = rowIdx

        """
        if ba.loadError:
            rowDict['I'] = 0
        else:
            rowDict['I'] = 2 # need 2 because checkbox value is in (0,2)
        """

        if ba.loadError:
            return None, None
        
        rowDict["File"] = ba.fileLoader.filename  # os.path.split(ba.path)[1]
        rowDict["Dur(s)"] = ba.fileLoader.recordingDur

        rowDict["Channels"] = ba.fileLoader.numChannels  # Theanne

        rowDict["Sweeps"] = ba.fileLoader.numSweeps

        # TODO: here, we do not get an epoch table until the file is loaded !!!
        rowDict["Epochs"] = ba.fileLoader.numEpochs  # Theanne, data has to be loaded

        rowDict["kHz"] = ba.fileLoader.recordingFrequency
        rowDict["Mode"] = ba.fileLoader.recordingMode.value

        # rowDict['dvdtThreshold'] = 20
        # rowDict['mvThreshold'] = -20
        if ba.isAnalyzed():
            dDict = ba.getDetectionDict()
            # rowDict['I'] = dDict.getValue('include')
            rowDict["dvdtThreshold"] = dDict.getValue("dvdtThreshold")
            rowDict["mvThreshold"] = dDict.getValue("mvThreshold")
            rowDict["Start(s)"] = dDict.getValue("startSeconds")
            rowDict["Stop(s)"] = dDict.getValue("stopSeconds")

        # add parent1, parent2, parent3
        _path, _file = os.path.split(path)
        _path, _parent1 = os.path.split(_path)
        _path, _parent2 = os.path.split(_path)
        _path, _parent3 = os.path.split(_path)
        rowDict['parent1'] = _parent1
        rowDict['parent2'] = _parent2
        rowDict['parent3'] = _parent3
        
        # aug 2023,  adding bAnalysis metadata columns
        for k,v in ba.metaData.items():
            rowDict[k] = v

        # remove the path to the folder we have loaded
        relPath = path.replace(self.path, "")
        
        # logger.info(f'xxx self.path: "{self.path}"')
        # logger.info(f'xxx path: "{path}"')
        # logger.info(f'xxx relPath: "{relPath}"')
        
        if relPath.startswith("/"):
            # so we can use os.path.join()
            relPath = relPath[1:]
        # added 20230505 working with johnson in 1313 to fix windows bug ???
        if relPath.startswith("\\"):
            # so we can use os.path.join()
            relPath = relPath[1:]

        rowDict["relPath"] = relPath

        #logger.info(f'2) xxx relPath: "{relPath}"')
        logger.info('qqq')
        print(rowDict)

        return ba, rowDict

    def getFileList(self, path: str = None, santanaTif=True) -> List[str]:
        """Get file paths from path.

        Uses self.theseFileTypes
        """
        if path is None:
            path = self.path

        fileList = getFileList(path, self.theseFileTypes, self.folderDepth)
        if santanaTif:
            fileList = stripSantanaTif(fileList)
        return fileList
    
        logger.warning("Remember: MODIFIED TO LOAD TIF FILES IN SUBFOLDERS")
        count = 1
        tmpFileList = []
        folderDepth = self.folderDepth  # if none then all depths
        excludeFolders = ["analysis", "hide"]
        for root, subdirs, files in os.walk(path):
            subdirs[:] = [d for d in subdirs if d not in excludeFolders]

            print(f'count:{count} folderDepth:{folderDepth}')
            print('  root:', root)
            print('  subdirs:', subdirs)
            print('  files:', files)

            # strip out folders that start with __
            # _parentFolder = os.path.split(root)[1]
            # print('root:', root)
            # print('  parentFolder:', _parentFolder)
            # if _parentFolder.startswith('__'):
            if "__" in root:
                logger.info(f"SKIPPING based on path root:{root}")
                continue

            if os.path.split(root)[1] == "analysis":
                # don't load from analysis/ folder, we save analysis there
                continue

            # if os.path.split(root)[1] == 'hide':
            #     # special case/convention, don't load from 'hide' folders
            #     continue

            for file in files:
                # TODO (cudmore) parse all our fileLoader(s) for a list
                _, _ext = os.path.splitext(file)
                if _ext in self.theseFileTypes:
                    oneFile = os.path.join(root, file)
                    tmpFileList.append(oneFile)

            count += 1
            if folderDepth is not None and count > folderDepth:
                break

        fileList = []
        for file in sorted(tmpFileList):
            if file.startswith("."):
                continue
            # ignore our database file
            if file == self.dbFile:
                continue

            # tmpExt is like .abf, .csv, etc
            tmpFileName, tmpExt = os.path.splitext(file)
            if tmpExt in self.theseFileTypes:
                # if getFullPath:
                #     #file = os.path.join(path, file)
                #     file = pathlib.Path(path) / file
                #     file = str(file)  # return List[str] NOT List[PosixPath]
                fileList.append(file)
        #
        logger.info(f"found {len(fileList)} files ...")
        return fileList

    def getRowDict(self, rowIdx):
        """
        Return a dict with selected row as dict (includes detection parameters).

        Important to return a copy as our '_ba' is a pointer to bAnalysis.

        Returns:
            theRet (dict): Be sure to make a deep copy of ['_ba'] if neccessary.
        """
        theRet = {}
        # use columns in main sanpyColumns, not in df
        # for colStr in self.columns:
        for colStr in self._df.columns:
            # theRet[colStr] = self._df.loc[rowIdx, colStr]
            theRet[colStr] = self._df.loc[rowIdx, colStr]
        # theRet['_ba'] = theRet['_ba'].copy()
        return theRet

    def appendRow(self, rowDict=None, ba=None):
        """Append an empty row."""

        # logger.info('')
        # print('    rowDict:', rowDict)
        # print('    ba:', ba)

        rowSeries = pd.Series()
        if rowDict is not None:
            rowSeries = pd.Series(rowDict)
            # self._data.iloc[row] = rowSeries
            # self._data = self._data.reset_index(drop=True)

        newRowIdx = len(self._df)
        df = self._df
        logger.warning(f"need to replace append with concat")
        df = df.append(rowSeries, ignore_index=True)
        # df = pd.concat([df,rowSeries], ignore_index=True, axis=1)
        df = df.reset_index(drop=True)

        if ba is not None:
            df.loc[newRowIdx, "_ba"] = ba

        #
        self._df = df

    def unloadRow(self, rowIdx):
        self._df.loc[rowIdx, "_ba"] = None
        self._updateLoadedAnalyzed()

    def removeRowFromDatabase(self, rowIdx):
        # delete from h5 file
        uuid = self._df.at[rowIdx, "uuid"]
        self._deleteFromHdf(uuid)

        # clear uuid
        self._df.at[rowIdx, "uuid"] = ""

        self._updateLoadedAnalyzed()

    def deleteRow(self, rowIdx):
        df = self._df

        # delete from h5 file
        uuid = df.at[rowIdx, "uuid"]
        self._deleteFromHdf(uuid)

        # delete from df/model
        df = df.drop([rowIdx])
        df = df.reset_index(drop=True)
        self._df = df

        self._updateLoadedAnalyzed()

    def old_duplicateRow(self, rowIdx):
        """Depreciated, Was used to have different ocnditions within a recording,
        this is now handled by condiiton column.
        """
        # duplicate rowIdx
        newIdx = rowIdx + 0.5

        rowDict = self.getRowDict(rowIdx)

        # CRITICAL: Need to make a deep copy of the _ba pointer to bAnalysis object
        logger.info(f"copying {type(rowDict['_ba'])} {rowDict['_ba']}")
        baNew = copy.deepcopy(rowDict["_ba"])

        # copy of bAnalysis needs a new uuid
        new_uuid = (
            sanpy._util.getNewUuid()
        )  # 't' + str(uuid.uuid4())   #.replace('-', '_')
        logger.info(f"assigning new uuid {new_uuid} to {baNew}")

        if baNew.uuid == new_uuid:
            logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!CRITICAL, new uuid is same as old")

        baNew.uuid = new_uuid

        rowDict["_ba"] = baNew
        rowDict["uuid"] = baNew.uuid  # new row can never have same uuid as old

        dfRow = pd.DataFrame(rowDict, index=[newIdx])

        df = self._df
        df = df.append(dfRow, ignore_index=True)
        df = df.sort_values(by=["File"], axis="index", ascending=True, inplace=False)
        df = df.reset_index(drop=True)
        self._df = df

        self._updateLoadedAnalyzed()

    def syncDfWithPath(self):
        """Sync path with existing df. Used to detect new/removed files."""

        pathFileList = self.getFileList()  # always full path
        dfFileList = self._df["File"].tolist()

        logger.info("")
        # print('    === pathFileList (on drive):')
        # print('    ', pathFileList)
        # print('    === dfFileList (in table):')
        # print('    ', dfFileList)

        addedToDf = False

        # look for files in path not in df
        for pathFile in pathFileList:
            fileName = os.path.split(pathFile)[1]
            if fileName not in dfFileList:
                logger.info(f'Found file in path "{fileName}" not in df')
                # load bAnalysis and get df column values
                addedToDf = True
                # fullPathFile = os.path.join(self.path, pathFile)
                ba, rowDict = self.getFileRow(pathFile)  # loads bAnalysis
                if rowDict is not None:
                    # listOfDict.append(rowDict)

                    # TODO: get this into getFileROw()
                    logger.warning("bug 20220718, not sure we need this ???")
                    # rowDict['relPath'] = pathFile
                    rowDict["_ba"] = None

                    self.appendRow(rowDict=rowDict, ba=None)

        # look for files in df not in path
        # for dfFile in dfFileList:
        #     if not dfFile in pathFileList:
        #         logger.info(f'Found file in df "{dfFile}" not in path')

        if addedToDf:
            df = self._df
            df = df.sort_values(
                by=["File"], axis="index", ascending=True, inplace=False
            )
            df = df.reset_index(drop=True)
            self._df = df

        self._updateLoadedAnalyzed()

    def pool_build(self, uniqueColumn=None, includeNo=True, verbose=False):
        """Build one df with all analysis. Use this in plot tool plugin.
        
        Parameters
        ----------
        uniqueColumn : str
            Name of column to prepend to File column to make a unique name.
            Use 'parant2' for Kymograph tif files exported from Olympus.
        includeNo : boolean
            if True then include files with metadata 'Include' of no.
        """
        if verbose:
            logger.info("")
        
        masterDf = None
        
        # for row in range(self.numFiles):
        for rowIdx, rowDict in self._df.iterrows():
            if (not includeNo) and (rowDict['Include'] == 'no'):
                if verbose:
                    logger.info(f'  rowIdx:{rowIdx} Include is "no"')
                continue

            ba = self.getAnalysis(rowIdx)

            if not ba.isAnalyzed():
                if verbose:
                    logger.info(f"  rowIdx:{rowIdx} not analyzed")
                continue
                
            oneDf = ba.asDataFrame()
            if oneDf is not None:
                self.signalApp(f'  adding "{ba.fileLoader.filename}"', verbose=verbose)
                
                oneDf["File Number"] = int(rowIdx)
                
                uniqueName = os.path.splitext(ba.fileLoader.filename)[0]
                if uniqueColumn is not None:
                    uniqueName = rowDict[uniqueColumn] + '-' + uniqueName
                oneDf["Unique Name"] = uniqueName

                logger.warning('TEMPORARY WHILE WORKING ON KYM POOLING !!!!!!!!!!!!!!!!!!!!!!!!!')
                logger.warning('randomly assigning sex to male, female, unknown')
                sexList = ['male', 'female', 'unknown']
                oneDf['Sex'] = random.choice(sexList)

                # drop some redundant analysis results (no in file metadata)
                
                if masterDf is None:
                    masterDf = oneDf
                else:
                    masterDf = pd.concat([masterDf, oneDf], ignore_index=True)
        #
        if masterDf is None:
            if verbose:
                logger.error("Did not find any analysis.")
        else:
            # add an index column (for plotting)
            masterDf['index'] = [x for x in range(len(masterDf))]
            if verbose:
                logger.info(f"final num spikes {len(masterDf)}")
        
        # print(masterDf.head())
        #self._poolDf = masterDf

        return masterDf

    def signalApp(self, str, verbose=True):
        """Update status bar of SanPy app.

        TODO make this a signal and connect app to it.
            Will not be able to do this, we need to run outside Qt
        """
        if self.myApp is not None:
            self.myApp.slot_updateStatus(str)
        elif verbose:
            logger.info(str)

    def api_getFileHeaders(self):
        headerList = []
        df = self.getDataFrame()
        for row in range(len(df)):
            # ba = self.getAnalysis(row)  # do not call this, it will load
            ba = df.at[row, "_ba"]
            if ba is not None:
                headerDict = ba.api_getHeader()
                headerList.append(headerDict)
        #
        return headerList


def _printDict(d):
    for k, v in d.items():
        print("  ", k, ":", v)

def test3():
    path = "/home/cudmore/Sites/SanPy/data"
    bad = analysisDir(path)

    # file = '19221014.abf'
    rowIdx = 3
    ba = bad.getAnalysis(rowIdx)
    ba = bad.getAnalysis(rowIdx)

    print(bad.getDataFrame())

    print("bad.shape", bad.shape)
    print("bad.columns:", bad.columns)

    print("bad.iloc[rowIdx,5]:", bad.iloc[rowIdx, 5])
    print("setting to xxxyyyzzz")

    # setter
    # bad.iloc[2,5] = 'xxxyyyzzz'

    print("bad.iloc[2,5]:", bad.iloc[rowIdx, 5])
    print('bad.loc[2,"File"]:', bad.loc[rowIdx, "File"])

    print("bad.iloc[2]")
    print(bad.iloc[rowIdx])
    # bad.iloc[rowIdx] = ''
    print("bad.loc[2]")
    print(bad.loc[rowIdx])

    # bad.saveDatabase()


def test_hd5_2():
    folderPath = "/home/cudmore/Sites/SanPy/data"
    if 1:
        # save analysisDir hdf
        bad = analysisDir(folderPath)
        print("bad._df:")
        print(bad._df)
        # bad.saveDatabase()  # save .csv
        bad.saveHdf()  # save ALL bAnalysis in .h5

    if 0:
        # load h5 and reconstruct a bAnalysis object
        start = time.time()
        hdfPath = "/home/cudmore/Sites/SanPy/data/sanpy_recording_db.h5"
        with pd.HDFStore(hdfPath, "r") as hdfStore:
            for key in hdfStore.keys():
                dfTmp = hdfStore[key]
                # path = dfTmp.iloc[0]['path']

                print("===", key)
                # if not key.startswith('/r6'):
                #    continue
                # for col in dfTmp.columns:
                #    print('  ', col, dfTmp[col])
                # print(key, type(dfTmp), dfTmp.shape)
                # print('dfTmp:')
                # print(dfTmp)

                # print(dfTmp.iloc[0]['_sweepX'])

                # load bAnalysis from a pandas DataFrame
                ba = sanpy.bAnalysis(fromDf=dfTmp)

                print(ba)

                ba.spikeDetect()  # this should reproduce exactly what was save ... It WORKS !!!

        stop = time.time()
        logger.info(f"h5 load took {round(stop-start,3)} seconds")


def test_hd5():
    import time

    start = time.time()
    hdfStore = pd.HDFStore("store.gzip")
    if 1:
        path = "/home/cudmore/Sites/SanPy/data"
        bad = analysisDir(path)

        # load all bAnalysis
        for idx in range(len(bad)):
            bad.getAnalysis(idx)

        hdfStore["df"] = bad.getDataFrame()  # save it
        bad.saveDatabase()

    if 0:
        df = hdfStore["df"]  # load it
        print("loaded df:")
        print(df)
    stop = time.time()
    print(f"took {stop-start}")


def test_pool():
    path = "/home/cudmore/Sites/SanPy/data"
    ad = analysisDir(path)
    print("loaded df:")
    print(ad._df)

    ad.pool_build()


def testCloud():
    cloudDict = {"owner": "cudmore", "repo_name": "SanPy", "path": "data"}
    bad = bAnalysisDirWeb(cloudDict)


if __name__ == "__main__":
    # test3()
    # test_hd5()
    
    # was this
    # test_hd5_2()
    
    # test_pool()
    # testCloud()

    # test_timing()
    # plotTiming()

    # july 2023 for kym, file structure is really complex
    path = '/Users/cudmore/Dropbox/data/cell-shortening/fig1'
    theseFileTypes = [".abf", ".atf", ".csv", ".dat", ".tif"]
    fileList = _walk(path, theseFileTypes, depth=4)
    fileList = stripSantanaTif(fileList)
    for file in fileList:
        print(file)
    
