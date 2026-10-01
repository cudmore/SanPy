"""Manage folder-backed collections of SanPy recording analyses."""

# Acknowledgements:
# Author: Robert H Cudmore
# Date: 20210603

import os
import time
import copy  # For copy.deepcopy() of bAnalysis
# import uuid  # to generate unique key on bAnalysis spike detect
import pathlib  # ned to use this (introduced in Python 3.4) to maname paths on Windows, stop using os.path

from typing import List, Optional

import numpy as np

import pandas as pd

# Turn off pandas save h5 performance warnnig
# see: https://github.com/pandas-dev/pandas/issues/3622
# /home/cudmore/Sites/SanPy/sanpy/analysisDir.py:478: PerformanceWarning:
# your performance may suffer as PyTables will pickle object types that it cannot
# map directly to c-types [inferred_type->mixed-integer,key->block0_values] [items->Index(['detectionClass', '_isAnalyzed', '_dataPointsPerMs', '_sweepList',
import warnings
warnings.filterwarnings("ignore", category=pd.io.pytables.PerformanceWarning)

import requests
import io  # too load from the web

import sanpy
import sanpy.h5Util
from sanpy.metaData import MetaData

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)


def _experimental_metadata_columns() -> dict[str, dict[str, object]]:
    """Return file-table columns for canonical experimental metadata.

    Returns:
        Column definitions keyed by canonical experimental-metadata name, in
        definition order. ``include`` is shown in the table and is not edited
        there.
    """
    columns: dict[str, dict[str, object]] = {}
    for key in MetaData.getMetaDataDefinitions():
        isEditable = key not in {"include", "sex"}
        columns[key] = {
            "type": str,
            "isEditable": isEditable,
        }
    return columns


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

    **_experimental_metadata_columns(),

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
    "relPath": {
        "type": str,
        "isEditable": False,
    },
    "uuid": {
        "type": str,
        "isEditable": False,
    },
}

def _normalized_file_key(folder_path: str, file_path: str) -> str:
    """Return a portable file identity relative to an analysis directory.

    Args:
        folder_path: Root directory owned by the analysis directory.
        file_path: Absolute or root-relative recording path.

    Returns:
        Normalized POSIX-style relative path.

    Raises:
        ValueError: If ``file_path`` is outside ``folder_path``.
    """
    root = os.path.realpath(folder_path)
    windows_path = pathlib.PureWindowsPath(file_path)
    if os.name != "nt" and windows_path.is_absolute():
        raise ValueError(f'File "{file_path}" is outside analysis directory "{root}"')
    candidate = file_path.replace("\\", os.sep)
    if not os.path.isabs(candidate):
        candidate = os.path.join(root, candidate)
    candidate = os.path.realpath(candidate)
    relative = os.path.relpath(candidate, root)
    if relative == os.pardir or relative.startswith(f"{os.pardir}{os.sep}"):
        raise ValueError(f'File "{file_path}" is outside analysis directory "{root}"')
    return pathlib.PurePath(relative).as_posix()


class bAnalysisDirWeb:
    """Load a directory of .abf from the web (for now from GitHub).

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

def _listdir(path, theseFileTypes):
    """Recursively walk directory to specified depth
    
    Parameters
    ----------
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
                    if _ext not in theseFileTypes:
                        continue
                    yield os.path.join(dirpath, filename)
                    
def getFileList(path, theseFileTypes, depth=1):
    """Get a list of files from a path."""
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
    """Class to manage a list of files loaded from a folder.
    """

    sanpyColumns = _sanpyColumns
    # Dict of dict of column names and bookkeeping info.

    def __init__(
        self,
        path: str | None = None,
        sanPyWindow: "sanpy.interface.SanPyWindow | None" = None,
        fileLoaderDict: dict[str, object] | None = None,
        autoLoad: bool = False,
        folderDepth: Optional[int] = None,
    ) -> None:
        """Load and manage a list of files in a folder path.

        Use this as the main pandasModel for file list myTableView.

        TODO: extend to link to folder in cloud (start with box and/or github)

        Args:
            path: Path to a recording or folder.
            sanPyWindow: Optional window used to report loading progress.
            fileLoaderDict: File-loader configuration keyed by extension.
            autoLoad: Whether to load each recording while scanning a folder.
            folderDepth: Folder depth to recurse when loading a folder.

        Notes
        -----
        - Some functions are so self can mimic a pandas dataframe used by pandasModel.
            (shape, loc, loc_setter, iloc, iLoc_setter, columns, append, drop, sort_values, copy)
        - 202312 adding filepath to load just one file
        """

        self._filePath = None
        if os.path.isfile(path):
            self._filePath = path
            folderPath = os.path.split(path)[0]
        else:
            folderPath = path

        logger.info(f'{path}')

        self.path: str = folderPath  # path to folder
        
        self._sanPyWindow = sanPyWindow
        # used to signal on building initial db

        self._fileLoaderDict = fileLoaderDict
        # dist with file extension keys

        self.autoLoad = autoLoad

        self.folderDepth = folderDepth

        self._isDirty = False
        # keep track if analysis was changed and prompt on quit

        # self._poolDf = None
        """See pool_ functions"""

        # TODO: refactor, we are not using the csv parth of this, just the filename
        # name of database file created/loaded from folder path
        self.dbFile = "sanpy_recording_db.csv"  # old but still critical to keep

        self._df = self.loadHdf()
        if self._df is None:
            # did not load h5 file
            self._df = self.loadFolder(loadData=autoLoad)
            self._updateLoadedAnalyzed()
        elif self._fileLoaderDict is not None:
            logger.info(f'sync existing df with filePath: {self._filePath}')
            self.syncDfWithPath()

        #
        self._checkColumns()
        self._normalize_file_keys()
        self._updateLoadedAnalyzed()

    def _normalize_file_keys(self) -> None:
        """Normalize and validate every recording key in the file table.

        Raises:
            ValueError: If a key is missing, outside the directory, or duplicated.
        """
        keys: list[str] = []
        available_paths: list[str] | None = None
        for row_index in self._df.index:
            value = self._df.at[row_index, "relPath"]
            if not isinstance(value, str) or not value:
                value = str(self._df.at[row_index, "File"])
            try:
                key = _normalized_file_key(self.path, value)
            except ValueError:
                if available_paths is None:
                    available_paths = self.getFileList()
                filename = pathlib.PureWindowsPath(value).name
                matches = [
                    path
                    for path in available_paths
                    if os.path.basename(path) == filename
                ]
                if len(matches) != 1:
                    raise ValueError(
                        f'Cannot uniquely resolve legacy recording path "{value}"'
                    ) from None
                key = _normalized_file_key(self.path, matches[0])
            self._df.at[row_index, "relPath"] = key
            keys.append(key)
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise ValueError(f"Duplicate analysis file keys: {duplicates}")

    def get_file_key(self, row_idx: int) -> str:
        """Return the stable file key for one table row.

        Args:
            row_idx: File-table row index.

        Returns:
            Normalized path relative to the analysis directory.
        """
        return str(self._df.at[row_idx, "relPath"])

    def get_row_for_file_key(self, file_key: str) -> int | None:
        """Return the table row for a normalized file key.

        Args:
            file_key: Recording identity relative to the analysis directory.

        Returns:
            Matching row index, or ``None`` when the key is unknown.
        """
        try:
            normalized = _normalized_file_key(self.path, file_key)
        except ValueError:
            return None
        rows = self._df.index[self._df["relPath"] == normalized].tolist()
        return int(rows[0]) if rows else None

    def get_analysis_for_file_key(
        self,
        file_key: str,
        allow_auto_load: bool = True,
    ) -> Optional[sanpy.bAnalysis]:
        """Resolve and optionally load an analysis by stable file key.

        Args:
            file_key: Recording identity relative to the analysis directory.
            allow_auto_load: Whether the recording may be loaded on demand.

        Returns:
            Resolved analysis, or ``None`` when the key is unknown or cannot load.
        """
        row_index = self.get_row_for_file_key(file_key)
        if row_index is None:
            return None
        return self.getAnalysis(row_index, allowAutoLoad=allow_auto_load)

    @property
    def theseFileTypes(self):
        """Get list of file extensions we will load.
        """
        if self._fileLoaderDict is not None:
            return list(self._fileLoaderDict.keys())

    def findFileRow(self, filename):
        """Find the row index of a file in the file table.
        
        Args:
            filename: The name of the file to find.

        Returns:
            The row index of the file in the file table, or None if the file is not found.
        """
        fileIndexList = self._df.index[self._df['File'] == filename].tolist()
        if fileIndexList:
            rowIdx = fileIndexList[0]
            return rowIdx
        else:
            logger.warning(f"Did not find file {filename} in {self._df['File'].tolist()}")

    def __iter__(self):
        """Iterate over the bAnalysis objects in the file table."""
        self._iterIdx = -1
        return self
    
    def __next__(self):
        """Get the next bAnalysis object in the file table."""
        self._iterIdx += 1
        if self._iterIdx >= self.numFiles:
            self._iterIdx = -1  # reset to initial value
            raise StopIteration
        else:
            return self._df.loc[self._iterIdx]["_ba"]

    def __str__(self):
        """Get a string representation of the analysisDir.
        
        Returns:
            A string representation of the analysisDir.
        """
        totalDurSec = self._df["Dur(s)"].sum()
        theStr = f"analysisDir Num Files: {len(self)} Total Dur(s): {totalDurSec}"
        return theStr

    @property
    def isDirty(self):
        """Get the dirty state of the analysisDir.
        
        Returns:
            True if the analysisDir is dirty, False otherwise.
        """
        return self._isDirty

    def __len__(self):
        """Get the number of files in the analysisDir.
        
        Same as numFiles().

        Returns:
            The number of files in the analysisDir.
        """
        return len(self._df)

    @property
    def numFiles(self):
        """Get the number of files in the analysisDir.
        
        Same as __len__().

        Returns:
            The number of files in the analysisDir.
        """
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

    def copyToClipboard(self):
        """
        TODO: Is this used or is copy to clipboard in pandas model?
        """
        if self.getDataFrame() is not None:
            self.getDataFrame().to_clipboard(sep="\t", index=False)
            logger.info("Copied to clipboard")

    def getPathFromRelPath(self, relPath):
        """Get full path to file from relPath.
        
        Uses analysisDir folder path.
        """
        if relPath.startswith("/"):
            relPath = relPath[1:]

        fullFilePath = os.path.join(self.path, relPath)

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
        # print(df)

        dbKey = os.path.splitext(self.dbFile)[0]
        df = df.drop("_ba", axis=1)  # don't ever save _ba, use it for runtime

        # hdfStore[dbKey] = df  # save it
        df.to_hdf(hdfFilePath, key=dbKey)

        #
        self._isDirty = False  # if true, prompt to save on quit

        # rebuild the file to remove old changes and reduce size
        # self._rebuildHdf()
        sanpy.h5Util._repackHdf(hdfFilePath)

        stop = time.time()
        logger.info(f"    Saving took {round(stop-start,2)} seconds")

    def loadHdf(self, path=None, verbose=False):
        """Load the database key from an h5 file.

        We do not load analysis until user clicks on row, see loadOneAnalysis()
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
            
            # if we are one file then make sure file is in df

        return df

    def loadOneAnalysis(
        self,
        path: str,
        uuid: Optional[str] = None,
        allowAutoLoad: bool = True,
        verbose: bool = False,
    ) -> Optional[sanpy.bAnalysis]:
        """Load one analysis from its recording and optional HDF5 data.

        If from h5, we still need to reload sweeps !!!
        They are binary and fast, saving to h5 (in this case) is slow.

        Args:
            path: Recording path.
            uuid: Optional analysis identifier in the folder HDF5 file.
            allowAutoLoad: Load directly from the recording when HDF5 data is
                unavailable.
            verbose: Emit detailed loading messages.

        Returns:
            A valid loaded analysis, or ``None`` when the recording cannot be
            loaded.
        """
        if verbose:
            logger.info(f'path:"{path}" uuid:"{uuid}" allowAutoLoad:"{allowAutoLoad}"')

        hdfPath = self._getHdfFile()

        ba = None
        if uuid is not None and uuid:
            # load from h5
            if verbose:
                logger.info(f"    Retreiving uuid from hdf file {uuid}")

            # load from abf
            ba = sanpy.bAnalysis(path, fileLoaderDict=self._fileLoaderDict, verbose=verbose)

            if ba.loadError:
                logger.error('Unable to load recording "%s"', path)
                return None

            # load analysis from h5 file, will fail if uuid is not in file
            ba._loadHdf_pytables(hdfPath, uuid)

        if allowAutoLoad and ba is None:
            # load from path
            ba = sanpy.bAnalysis(path, fileLoaderDict=self._fileLoaderDict, verbose=verbose)
            if verbose:
                logger.info(f"    Loaded ba from path {path} and now ba:{ba}")

        if ba is not None and ba.loadError:
            logger.error('Unable to load recording "%s"', path)
            return None
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

    def loadFolder(self, path=None, loadData=False) -> pd.DataFrame:
        """Parse a folder and load all (abf, csv, ...).
        
        Only called if no h5 file.

        TODO: get rid of loading database from .csv (it is replaced by .h5 file)
        TODO: extend the logic to load from cloud (after we were instantiated)
        """
        logger.info("Loading folder from scratch (no h5 file)")

        start = time.time()
        if path is None:
            path = self.path
        self.path = path

        df = pd.DataFrame(columns=self.sanpyColumns.keys())
        df = self._setColumnType(df)

        # get list of all abf/csv/tif files
        fileList = self.getFileList(path)
        _numFilesToLoad = len(fileList)
        start = time.time()
        # build new db dataframe
        listOfDict = []
        for rowIdx, fullFilePath in enumerate(fileList):
            
            self.signalWindow(
                f'Loading file {rowIdx+1} of {_numFilesToLoad} "{fullFilePath}"'
            )

            # rowDict is what we are showing in the file table
            # abb debug vue, set loadData=True
            # loads bAnalysis
            ba, rowDict = self.getFileRow(fullFilePath, loadData=loadData)

            if rowDict is None:
                logger.warning(f'error loading file {fullFilePath}')
                continue
            
            # as we parse the folder, don't load ALL files (will run out of memory)
            if loadData:
                rowDict["_ba"] = ba
            else:
                rowDict["_ba"] = None  # ba

            # do not assign uuid until bAnalysis is saved in h5 file
            # rowDict['uuid'] = ''

            # logger.info(f'    row:{rowIdx} relPath:{relPath} fullFilePath:{fullFilePath}')

            listOfDict.append(rowDict)

        stop = time.time()
        logger.info(f"Loading {len(listOfDict)} files took {round(stop-start,3)} seconds.")

        df = pd.DataFrame(listOfDict)
        df = self._setColumnType(df)
        
        return df

    def _checkColumns(self, verbose = False):
        """Check columns in loaded vs sanpyColumns (and vica versa).
        """
        if self._df is None:
            return
        
        # verbose = True
        loadedColumns = self._df.columns
        for col in loadedColumns:
            if col not in self.sanpyColumns.keys():
                # loaded has unexpected column, leave it
                if verbose:
                    logger.info(
                        f'did not find loaded col: "{col}" in sanpyColumns.keys() ... ignore it'
                    )
        for col in self.sanpyColumns.keys():
            if col not in loadedColumns:
                # loaded is missing expected, add it
                if verbose:
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

                # relPath should usually be filled in ???
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

            # TODO: remove start of ba._path that corresponds to our current folder path
            # will allow our save db to be modular
            # self._df.loc[rowIdx, 'path'] = ba._path

    def isLoaded(self, rowIdx):
        isLoaded = self._df.loc[rowIdx, "_ba"] is not None
        return isLoaded

    def isAnalyzed(self, rowIdx):
        isAnalyzed = False
        ba = self._df.loc[rowIdx, "_ba"]
        if ba is not None:
            try:
                isAnalyzed = ba.isAnalyzed()
            except(AttributeError) as e:
                logger.error(f'rowIdx {rowIdx} ba is "{ba}" but expecting bAnalysis_')
                logger.error('self._df:')
                print(self._df)
                return False
        return isAnalyzed

    def analysisIsDirty(self, rowIdx):
        """Analysis is dirty when there has been detection but not saved to h5."""
        isDirty = False
        ba = self._df.loc[rowIdx, "_ba"]
        if isinstance(ba, sanpy.bAnalysis):
            isDirty = ba.isDirty()
        return isDirty

    def hasDirty(self):
        """Return true if any bAnalysis in list has been analyzed but not saved (e.g. is dirty).
        """
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

        if ba is None or ba == "":
            relPath = self._df.loc[rowIdx, "relPath"]
            filePath = self.getPathFromRelPath(relPath)

            ba = self.loadOneAnalysis(
                filePath, uuid, allowAutoLoad=allowAutoLoad, verbose=verbose
            )
            # load
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
            if col not in self.sanpyColumns:
                # logger.warning(f'Column "{col}" is not in sanpyColumns -->> ignoring')
                continue
            colType = self.sanpyColumns[col]["type"]
            if colType == str:
                df[col] = df[col].replace(np.nan, "", regex=True)
                df[col] = df[col].astype(str)
            elif colType == int:
                pass
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
        # if fileType:
        #     fileType = fileType[1:]  # [1:] to strip period
        if fileType not in self.theseFileTypes:  
            logger.warning(f'Did not load file type "{fileType}"')
            return None, None

        ba = sanpy.bAnalysis(path,
                             loadData=loadData,
                             fileLoaderDict=self._fileLoaderDict)

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
        rowDict["relPath"] = _normalized_file_key(self.path, path)

        return ba, rowDict

    def getFileList(self,
                    path: str = None,
                    santanaTif=False
                    ) -> List[str]:
        """Get file paths from path.

        Uses self.theseFileTypes

        """
        
        if self._filePath is not None:
            logger.info(f'returning one file {self._filePath}')
            return [self._filePath]
        
        if path is None:
            path = self.path

        fileList = getFileList(path, self.theseFileTypes, self.folderDepth)
        if santanaTif:
            fileList = stripSantanaTif(fileList)
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

        rowSeries = pd.Series()
        if rowDict is not None:
            # rowSeries = pd.Series(rowDict)
            rowSeries = pd.DataFrame([rowDict])

            # self._data.iloc[row] = rowSeries
            # self._data = self._data.reset_index(drop=True)

        newRowIdx = len(self._df)  # append this row

        df = self._df
        df = pd.concat([df, rowSeries], axis=0, ignore_index=True)

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

    def syncDfWithPath(self):
        """Sync path with existing df. Used to detect new/removed files.
        
        If we currently have just one file (self._filePath) we will trash it and load a folder
        
        Notes
        -----
        20231230, trying to use this to open a one file window with an exiting h5 file.
        """

        pathFileList = self.getFileList()

        # our currently loaded files
        dfFileList = self._df["File"].tolist()

        logger.info(f'dfFileList: {dfFileList}')
        # print('    === pathFileList (on drive):')
        # print('    ', pathFileList)
        # print('    === dfFileList (in table):')
        # print('    ', dfFileList)

        addedToDf = False

        # look for files in path not in df
        for pathFile in pathFileList:
            fileName = os.path.split(pathFile)[1]
            if fileName not in dfFileList:
                logger.info(f'   Found file in path "{fileName}" not in df')

                # load bAnalysis and get df column values
                addedToDf = True

                ba, rowDict = self.getFileRow(pathFile)  # loads bAnalysis

                if rowDict is not None:
                    # listOfDict.append(rowDict)

                    # TODO: get this into getFileROw()
                    # logger.warning("bug 20220718, not sure we need this ???")
                    # print(rowDict)

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

    def pool_spike_dataframe(self) -> pd.DataFrame | None:
        """Concatenate spike results for every analyzed file.

        Loads a saved analysis when that file is not already in memory. Each
        copied row receives ``file_number`` as its current file-table row and
        ``row_id`` as ``"{file_number}:{spikeNumber}"``. The per-file analysis
        keeps its stored ``file_number`` of 0.

        Returns:
            The concatenated spike table, or ``None`` when no file has spikes.

        Raises:
            ValueError: If an analyzed file has no ``spikeNumber`` column.

        Notes:
            Each call reloads and regenerates every analyzed file. NicePool (pool)
            calls this on each replot.
        """
        frames: list[pd.DataFrame] = []
        for row_idx in self._df.index:
            ba = self.getAnalysis(row_idx, allowAutoLoad=True)
            if ba is None or not ba.isAnalyzed():
                continue
            one_df = ba.asDataFrame(regenerateAnalysisDataFrame=True)
            if one_df is None or one_df.empty:
                continue
            if "spikeNumber" not in one_df.columns:
                raise ValueError(
                    "SanPy spike results are missing the spikeNumber column"
                )
            # Copy so file_number and row_id stay on the pooled frame only.
            one_df = one_df.copy()
            one_df["file_number"] = int(row_idx)
            one_df["file_key"] = self.get_file_key(int(row_idx))
            self.signalWindow(f'Adding "{ba.fileLoader.filename}"')
            frames.append(one_df)
        if not frames:
            return None
        pooled = pd.concat(frames, ignore_index=True)
        pooled["row_id"] = (
            pooled["file_number"].astype(int).astype(str)
            + ":"
            + pooled["spikeNumber"].astype(int).astype(str)
        )
        return pooled

    def signalWindow(self, str, verbose=True):
        """Update status bar of SanPy window.

        TODO make this a signal and connect app to it.
            Will not be able to do this, we need to run outside Qt
        """
        if self._sanPyWindow is not None:
            self._sanPyWindow.slot_updateStatus(str)
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
