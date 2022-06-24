# Acknowledgements:
# Author: Robert H Cudmore
# Date: 20210603

import os, time, sys
import copy  # For copy.deepcopy() of bAnalysis
import uuid  # to generate unique key on bAnalysis spike detect
import pathlib  # ned to use this (introduced in Python 3.4) to maname paths on Windows, stop using os.path

from typing import List  #, Union

import numpy as np
import pandas as pd
import requests, io  # too load from the web
from subprocess import call # to call ptrepack (might fail on windows???)
from pprint import pprint
import tables.scripts.ptrepack  # to save compressed .h5 file
import shutil

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

# Turn off pandas save h5 performance warnnig
# see: https://github.com/pandas-dev/pandas/issues/3622
#/home/cudmore/Sites/SanPy/sanpy/analysisDir.py:478: PerformanceWarning:
#your performance may suffer as PyTables will pickle object types that it cannot
#map directly to c-types [inferred_type->mixed-integer,key->block0_values] [items->Index(['detectionClass', '_isAnalyzed', '_dataPointsPerMs', '_sweepList',
import warnings
warnings.filterwarnings('ignore',category=pd.io.pytables.PerformanceWarning)

_sanpyColumns = {
    #'Idx': {
    #    #'type': int,
    #    'type': float,
    #    'isEditable': False,
    #},
    'L': {
        # loaded
        'type': str,
        'isEditable': False,
    },
    'A': {
        # analyzed
        'type': str,
        'isEditable': False,
    },
    'S': {
        # saved
        'type': str,
        'isEditable': False,
    },
    'N': {
        # number of spikes
        'type': int,
        'isEditable': False,
    },
    'I': {
        # include
        # problems with isinstance(bool), just using string
        'type': 'bool',
        'isEditable': True,
    },
    'File': {
        'type': str,
        'isEditable': False,
    },
    'Dur(s)': {
        'type': float,
        'isEditable': False,
    },
    'Sweeps': {
        'type': int,
        'isEditable': False,
    },
    'kHz': {
        'type': float,
        'isEditable': False,
    },
    'Mode': {
        'type': str,
        'isEditable': False,
    },
    'Start(s)': {
        'type': float,
        'isEditable': False,
    },
    'Stop(s)': {
        'type': float,
        'isEditable': False,
    },
    'dvdtThreshold': {
        'type': float,
        'isEditable': True,
    },
    'mvThreshold': {
        'type': float,
        'isEditable': True,
    },
    'Cell Type': {
        'type': str,
        'isEditable': True,
    },
    'Sex': {
        'type': str,
        'isEditable': True,
    },
    'Condition': {
        'type': str,
        'isEditable': True,
    },
    'Notes': {
        'type': str,
        'isEditable': True,
    },
    # kymograph interface
    'kLeft': {
        'type': int,
        'isEditable': False,
    },
    'kTop': {
        'type': int,
        'isEditable': False,
    },
    'kRight': {
        'type': int,
        'isEditable': False,
    },
    'kBottom': {
        'type': int,
        'isEditable': False,
    },
    'relPath': {
        'type': str,
        'isEditable': False,
    },
    'uuid': {
        'type': str,
        'isEditable': False,
    },

}


"""
Columns to use in display in file table (pyqt, dash, vue).
We require type so we can edit with QAbstractTableModel.
Critical for qt interface to allow easy editing of values while preserving type
"""

def fixRelPath(folderPath, dfTable :pd.DataFrame, fileList : List[str]):
    """
    was not assigning relPath on initial load (no hd5 file)
    """
    logger.info('')
    
    print('fileList:', fileList)
    pprint(dfTable[['File', 'relPath']])
    
    if dfTable is None:
        logger.error('no dfTable')

    n = len(dfTable)
    for rowIdx in range(n):
        file = dfTable.loc[rowIdx, 'File']
        relPath = dfTable.loc[rowIdx, 'relPath']
        
        # 20220422 why was this here?
        #if relPath:
        #    continue
        
        #print(rowIdx, file, relPath)
        for filePath in fileList:
            if filePath.find(file) != -1:
                print(f'  fixRelPath() file idx {rowIdx} file:{file} now has relPath:{filePath}')
                dfTable.loc[rowIdx, 'relPath'] = filePath

    #sys.exit(1)

def h5_printKey(hdfPath):
    print('\n=== h5_printKey() hdfPath:', hdfPath)
    with pd.HDFStore(hdfPath, mode='r') as store:
        for key in store.keys():
            print('  ', key)
    print('\n')

class bAnalysisDirWeb():
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
        """
        Load using cloudDict
        """

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

        owner = self._cloudDict['owner']
        repo_name = self._cloudDict['repo_name']
        path = self._cloudDict['path']
        url = f'https://api.github.com/repos/{owner}/{repo_name}/contents/{path}'

        # response is a list of dict
        response = requests.get(url).json()
        #print('response:', type(response))

        for idx, item in enumerate(response):
            if not item['name'].endswith('.abf'):
                continue
            print(idx)
            # use item['git_url']
            for k,v in item.items():
                print('  ', k, ':', v)

        #
        # test load
        download_url = response[1]['download_url']
        content = requests.get(download_url).content

        fileLikeObject = io.BytesIO(content)
        ba = sanpy.bAnalysis(byteStream=fileLikeObject)
        #print(ba._abf)
        #print(ba.api_getHeader())
        ba.spikeDetect()
        print(ba.numSpikes)

class analysisDir():
    """
    Class to manage a list of files loaded from a folder
    """
    sanpyColumns = _sanpyColumns

    # abb 20210803
    #theseFileTypes = ['.abf', '.csv']
    theseFileTypes = ['.abf', '.atf', '.csv', '.tif']
    """File types to load"""

    def __init__(self, path=None, myApp=None, autoLoad=False, folderDepth=None):
        """
        Load and manage a list of files in a folder path.
        Use this as the main pandasModel for file list myTableView.

        TODO: extend to link to folder in cloud (start with box and/or github)

        Args:
            path (str): Path to folder
            myApp (sanpy_app): Optional
            autoLoad (boolean):
            cloudDict (dict): To load frmo cloud, for now  just github

        Notes:
            - on load existing .csv
                - match columns in file with 'sanpyColumns'
                - check that each file in csv exists in the path
                - check if there are files in the path NOT in the csv

            - Some functions are so self can mimic a pandas dataframe used by pandasModel.
                (shape, loc, loc_setter, iloc, iLoc_setter, columns, append, drop, sort_values, copy)
        """
        self.path = path
        self.myApp = myApp # used to signal on building initial db
        self.autoLoad = autoLoad

        self.folderDepth = folderDepth  # specify int

        self._isDirty = False

        self._poolDf = None
        """See pool_ functions"""

        # keys are full path to file, if from cloud, key is 'cloud/<filename>'
        # holds bAnalysisObjects
        # needs to be a list so we can have files more than one
        #self.fileList = [] #OrderedDict()

        # name of database file created/loaded from folder path
        self.dbFile = 'sanpy_recording_db.csv'

        self._df = None
        #if autoLoad:
        if 1:
            self._df = self.loadHdf()
            if self._df is None:
                self._df = self.loadFolder(loadData=autoLoad)  # only used if no h5 file
                self._updateLoadedAnalyzed()

        # self._df = self.loadFolder(loadData=autoLoad)

        #
        self._checkColumns()
        self._updateLoadedAnalyzed()

        logger.warning('\n   temporary fix with fixRelPath()\n')
        tmpFileList = self.getFileList()
        fixRelPath(self.path, self._df, tmpFileList)

        #sys.exit(1)

        #
        #logger.info(self)

    def __iter__(self):
        self._iterIdx = 0
        return self

    def __next__(self):
        if self._iterIdx < self.numFiles:
            x = self._df.loc[self._iterIdx]['_ba']
            self._iterIdx += 1
            return x
        else:
            raise StopIteration

    def __str__(self):
        totalDurSec = self._df['Dur(s)'].sum()
        theStr = f'analysisDir Num Files: {len(self)} Total Dur(s): {totalDurSec}'
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
        #return self._df.shape
        numRows = self._df.shape[0]
        numCols = len(self.columns)
        return (numRows, numCols)

    @property
    def loc(self):
        """Mimic pandas df.loc[]"""
        return self._df.loc

    @loc.setter
    def loc_setter(self, rowIdx, colStr, value):
        self._df.loc[rowIdx,colStr] = value

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

    '''
    @property
    def iat(self):
        # mimic pandas df.iat[]
        return self._df.iat

    @iat.setter
    def iat_setter(self, rowIdx, colStr, value):
        self._df.iat[rowIdx, colStr] = value
        self._isDirty = True
    '''

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
        logger.info(f'sorting by column {self.columns[Ncol]} with order:{order}')
        self._df = self._df.sort_values(self.columns[Ncol], ascending=not order)
        #print(self._df)

    @property
    def columnsDict(self):
        return self.sanpyColumns

    def columnIsEditable(self, colName):
        return self.sanpyColumns[colName]['isEditable']

    def columnIsCheckBox(self, colName):
        """All bool columns are checkbox

        TODO: problems with using type=bool and isinstance(). Kust using str 'bool'
        """
        type = self.sanpyColumns[colName]['type']
        #isBool = isinstance(type, bool)
        isBool = type == 'bool'
        #logger.info(f'{colName} {type(type)}, type:{type} {isBool}')
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
            self.getDataFrame().to_clipboard(sep='\t', index=False)
            logger.info('Copied to clipboard')

    def old_saveDatabase(self):
        """ save dbFile .csv and hdf .gzip"""
        dbPath = os.path.join(self.path, self.dbFile)
        if self.getDataFrame() is not None:
            #
            logger.info(f'Saving "{dbPath}"')
            self.getDataFrame().to_csv(dbPath, index=False)
            self._isDirty = False

            #
            '''
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
            '''

    def _getFrozenPath(self):
        if getattr(sys, 'frozen', False):
            # running in a bundle (frozen)
            myPath = sys._MEIPASS
        else:
            # running in a normal Python environment
            #myPath = os.path.dirname(os.path.abspath(__file__))
            myPath = pathlib.Path(__file__).parent.absolute()
        return myPath

    def _rebuildHdf(self):
        #
        # rebuild the file to remove old changes and reduce size
        tmpHdfFile = os.path.splitext(self.dbFile)[0] + '_tmp.h5'
        #tmpHdfPath = os.path.join(self.path, tmpHdfFile)
        tmpHdfPath = pathlib.Path(self.path) / tmpHdfFile

        hdfFile = os.path.splitext(self.dbFile)[0] + '.h5'
        #hdfPath = os.path.join(self.path, hdfFile)
        hdfPath = pathlib.Path(self.path) / hdfFile
        logger.info(f'Rebuilding h5 to {hdfPath}')
        
        '''
        #command = ["ptrepack", "-o", "--chunkshape=auto", "--propindexes", '--complevel=9', '--complib=blosc:blosclz', tmpHdfPath, hdfPath]
        #command = ["ptrepack", "-o", "--chunkshape=auto", "--propindexes", tmpHdfPath, hdfPath]
        command = ["_ptrepack", "-o", "--chunkshape=auto", tmpHdfPath, hdfPath]
        '''

        if getattr(sys, 'frozen', False):
            # running in a bundle (frozen)
            bundle_dir = sys._MEIPASS
        else:
            bundle_dir = os.path.dirname(os.path.abspath(__file__))
        
        #_ptrepack_path = os.path.join(bundle_dir, 'ptrepack')
        #logger.info(f'frozen _ptrepack_path: {_ptrepack_path}')
        #command[0] = _ptrepack_path

        #_ptrepackPath = os.path.join(bundle_dir, '_ptrepack.py')

        # can't pass sys.argv a 'POsixPath' (from pathlib.Path, need to be a string
        # The first item is normally the command line command name (not used)
        tmpHdfPath = str(tmpHdfPath)
        hdfPath = str(hdfPath)
        
        # on Windows, path cannot have a ':'
        # tables.scripts.ptrepack.main() has a but (since 2017) that causes it to fail with a ':'
        
        # when calling ptrepack, we need trailing ':' on each src/dst path
        _tmpHdfPath = tmpHdfPath + ':'
        _hdfPath = hdfPath + ':'
        
        sys.argv = ["", "--overwrite", "--chunkshape=auto", _tmpHdfPath, _hdfPath]

        logger.info('running tables.scripts.ptrepack.main()')
        logger.info(f'sys.argv: {sys.argv}')
        try:
            # works
            # exec(open(_ptrepackPath).read(), globals())
            
            tables.scripts.ptrepack.main()

            # delete the temporary (large file)
            logger.info(f'Deleting tmp file: {tmpHdfPath}')
            os.remove(tmpHdfPath)

            #self.signalApp(f'Call success to script {_ptrepackPath}')
            self.signalApp(f'Saved compressed folder analysis with tables.scripts.ptrepack.main()')

        except(FileNotFoundError) as e:
            logger.error('tables.scripts.ptrepack.main() failed ... file was not saved')
            logger.error(e)
            self.signalApp(f'ERROR in tables.scripts.ptrepack.main(): {e}')
        '''
        try:
            call(command)
        except(FileNotFoundError) as e:
            logger.error('Call to ptrepack command line fails in pyinstaller bundled app')
            logger.error(e)
        '''

    def save(self):
        for ba in self:
            if ba is not None:
                ba.saveAnalysis()

    def saveHdf(self):
        """
        Save file table and any number of loaded and analyzed bAnalysis.

        Set file table 'uuid' column when we actually save a bAnalysis

        Important: Order matters
                (1) Save bAnalysis first, it updates uuid in file table.
                (2) Save file table with updated uuid
                """
        start = time.time()

        df = self.getDataFrame()

        # kymograph, just save as csv
        # 20220612 WHY WAS I DOING THIS !!!!
        '''
        dbPath = os.path.join(self.path, self.dbFile)
        logger.info(f'Saving "{dbPath}"')
        self.getDataFrame().to_csv(dbPath, index=False)
        '''

        tmpHdfFile = os.path.splitext(self.dbFile)[0] + '_tmp.h5'
        #tmpHdfPath = os.path.join(self.path, tmpHdfFile)
        tmpHdfPath = pathlib.Path(self.path) / tmpHdfFile

        # the compressed version from the last save
        # if it exists, append to it
        hdfFile = os.path.splitext(self.dbFile)[0] + '.h5'
        #hdfFilePath = os.path.join(self.path, hdfFile)
        hdfFilePath = pathlib.Path(self.path) / hdfFile

        #print('!!! hdfFilePath:', hdfFilePath)
        
        hdfMode = 'w'
        if os.path.isfile(hdfFilePath):
            logger.info(f'copying existing hdf file to tmp')
            print('    hdfFilePath:', hdfFilePath)
            print('    tmpHdfPath:', tmpHdfPath)
            shutil.copyfile(hdfFilePath,tmpHdfPath)
            hdfMode = 'a'
        #
        # save each bAnalysis
        #print(df)
        doSaveAnalysis = True
        logger.info(f'Saving tmp db with doSaveAnalysis:{doSaveAnalysis} (will be compressed) {tmpHdfPath}')

        if doSaveAnalysis:
            for row in range(len(df)):
                #ba = self.getAnalysis(row)  # do not call this, it will load
                ba = df.at[row, '_ba']
                if ba is not None:
                    # 20220615
                    didSave = ba._saveToHdf(tmpHdfPath, hdfMode=hdfMode) # will only save if ba.detectionDirty
                    if didSave:
                        # we are now saved into h5 file, remember uuid to load
                        df.at[row, 'uuid'] = ba.uuid

            # rebuild (L, A, S) columns
            self._updateLoadedAnalyzed()

        #
        # save file database
        #with pd.HDFStore(tmpHdfPath, mode='a') as hdfStore:
        with pd.HDFStore(tmpHdfPath, mode=hdfMode) as hdfStore:
            dbKey = os.path.splitext(self.dbFile)[0]
            #logger.critical(f'Storing file database into key "{dbKey}"')
            #df = self.getDataFrame()
            df = df.drop('_ba', axis=1)  # don't ever save _ba, use it for runtime

            logger.info(f'saving file db with {len(df)} rows')

            #print(df[['File', 'uuid']])
            print(df)
            '''
            for col in df.columns:
                print(col, df[col])
            '''

            hdfStore[dbKey] = df  # save it
            #
            self._isDirty = False  # if true, prompt to save on quit

        #h5_printKey(tmpHdfPath)

        #
        # rebuild the file to remove old changes and reduce size
        self._rebuildHdf()
        
        # abb removed 20220612
        '''
        hdfFile = os.path.splitext(self.dbFile)[0] + '.h5'
        hdfPath = os.path.join(self.path, hdfFile)
        logger.critical(f'Rebuilding h5 using call to to command line "ptrepack" {hdfPath}')
        #command = ["ptrepack", "-o", "--chunkshape=auto", "--propindexes", '--complevel=9', '--complib=blosc:blosclz', tmpHdfPath, hdfPath]
        #command = ["ptrepack", "-o", "--chunkshape=auto", "--propindexes", tmpHdfPath, hdfPath]
        command = ["ptrepack", "-o", "--chunkshape=auto", tmpHdfPath, hdfPath]
        
        try:
            call(command)
        except(FileNotFoundError) as e:
            logger.error('Call to ptrepack command line fails in pyinstaller bundled app')
            logger.error(e)
        '''

        #logger.info(f'Removing temporary file {tmpHdfPath}')
        #os.remove(tmpHdfPath)

        stop = time.time()
        logger.info(f'Saving took {round(stop-start,2)} seconds')

    def loadHdf(self, path=None):
        if path is None:
            path = self.path
        self.path = path

        df = None
        hdfFile = os.path.splitext(self.dbFile)[0] + '.h5'
        #hdfPath = os.path.join(self.path, hdfFile)
        hdfPath = pathlib.Path(self.path) / hdfFile
        if not os.path.isfile(hdfPath):
            # abb 20220612 for bundled pyinstaller
            # we can't compress h5 file on save using system call to ptrepack
            tmp_hdfFile = os.path.splitext(self.dbFile)[0] + '_tmp.h5'
            #hdfPath = os.path.join(self.path, tmp_hdfFile)
            hdfPath = pathlib.Path(self.path) / tmp_hdfFile
            if not os.path.isfile(hdfPath):
                return

        logger.info(f'Loading existing folder hdf {hdfPath}')

        start = time.time()
        with pd.HDFStore(hdfPath) as hdfStore:
            print('  hdfStore has keys:')
            for k in hdfStore.keys():
                print(f'  {k}')

            dbKey = os.path.splitext(self.dbFile)[0]

            try:
                df = hdfStore[dbKey]  # load it
            except (KeyError) as e:
                logger.error(f'Did not find dbKey:"{dbKey}" {e}')

            # _ba is for runtime, assign after loading from either (abf or h5)
            df['_ba'] = None

            '''
            logger.info('loaded db df')
            print(df[['File', 'uuid', '_ba']])
            '''
            # load each bAnalysis from hdf
            # No, don't load anything until user clicks
            '''
            for row in range(len(df)):
                ba_uuid = df.at[row, 'uuid']
                if not ba_uuid:
                    # ba was not saved in h5 file
                    continue
                try:
                    # TODO: Get rid of this, don't load all data on init, wait for user to click
                    print(f'xxx not loading uuid {ba_uuid} ... wait for user click')
                    dfAnalysis = hdfStore[ba_uuid]
                    ba = sanpy.bAnalysis(fromDf=dfAnalysis)
                    logger.info(f'Loaded row {row} uuid:{ba.uuid} bAnalysis {ba}')
                    df.at[row, '_ba'] = ba # can be none
                except(KeyError):
                    logger.error(f'hdf uuid key for row {row} not found in .h5 file, uuid:"{ba_uuid}"')
            '''

        # fixRelPath(self.path, df, self.getFileList())

        stop = time.time()
        logger.info(f'Loading took {round(stop-start,2)} seconds')
        #
        return df

    def _deleteFromHdf(self, uuid):
        """Delete uuid from h5 file. id corresponds to a bAnalysis detection."""
        if uuid is None or not uuid:
            return
        logger.info(f'TODO: Delete from h5 file uuid:{uuid}')

        tmpHdfFile = os.path.splitext(self.dbFile)[0] + '_tmp.h5'
        #tmpHdfPath = os.path.join(self.path, tmpHdfFile)
        tmpHdfPath = pathlib.Path(self.path) / tmpHdfFile
        removed = False
        with pd.HDFStore(tmpHdfPath, mode='a') as hdfStore:
            try:
                hdfStore.remove(uuid)
                removed = True
            except (KeyError):
                logger.error(f'Did not find uuid {uuid} in h5 file.')

        #
        if removed:
            self._rebuildHdf()
            self._updateLoadedAnalyzed()

    def loadFolder(self, path=None, loadData=False):
        """
        Parse a folder and load all (abf, csv, ...). Only called if no h5 file.

        TODO: get rid of loading database from .csv (it is replaced by .h5 file)
        TODO: extend the logic to load from cloud (after we were instantiated)
        """
        logger.info('Loading folder from scratch (no hdf file)')

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
            logger.info(f'Loading existing folder db: {dbPath}')
            df = pd.read_csv(dbPath, header=0, index_col=False)
            #df["Idx"] = pd.to_numeric(df["Idx"])
            df = self._setColumnType(df)
            loadedDatabase = True
            #logger.info(f'  shape is {df.shape}')
        else:
            #logger.info(f'No existing db file, making {dbPath}')
            logger.info(f'No existing db file, making default dataframe')
            df = pd.DataFrame(columns=self.sanpyColumns.keys())
            df = self._setColumnType(df)

        if loadedDatabase:
            # check columns with sanpyColumns
            loadedColumns = df.columns
            for col in loadedColumns:
                if not col in self.sanpyColumns.keys():
                    logger.error(f'error: bAnalysisDir did not find loaded col: "{col}" in sanpyColumns.keys()')
            for col in self.sanpyColumns.keys():
                if not col in loadedColumns:
                    logger.error(f'error: bAnalysisDir did not find sanpyColumns.keys() col: "{col}" in loadedColumns')

        if loadedDatabase:
            # seach existing db for missing abf files
            pass
        else:
            # get list of all abf/csv/tif
            fileList = self.getFileList(path)
            start = time.time()
            # build new db dataframe
            listOfDict = []
            for rowIdx, file in enumerate(fileList):
                self.signalApp(f'Loading "{file}"')

                # rowDict is what we are showing in the file table
                # abb debug vue, set loadData=True
                ba, rowDict = self.getFileRow(file, loadData=loadData)  # loads bAnalysis

                # TODO: calculating time, remove this
                # This is 2x faster than loading from pandas gzip ???
                #dDict = sanpy.bAnalysis.getDefaultDetection()
                #dDict['dvdtThreshold'] = 2
                #ba.spikeDetect(dDict)

                # as we parse the folder, don't load ALL files (will run out of memory)
                if loadData:
                    rowDict['_ba'] = ba
                else:
                    rowDict['_ba'] = None  # ba

                # do not assign uuid until bAnalysis is saved in h5 file
                #rowDict['uuid'] = ''

                rowDict['relPath'] = file

                listOfDict.append(rowDict)

            stop = time.time()
            logger.info(f'Load took {round(stop-start,3)} seconds.')

            #
            df = pd.DataFrame(listOfDict)
            #print('=== built new db df:')
            #print(df)
            df = self._setColumnType(df)
        #

        # expand each to into self.fileList
        #df['_ba'] = None

        stop = time.time()
        logger.info(f'Load took {round(stop-start,2)} seconds.')
        return df

    def _checkColumns(self):
        """Check columns in loaded vs sanpyColumns (and vica versa"""
        if self._df is None:
            return
        loadedColumns = self._df.columns
        for col in loadedColumns:
            if not col in self.sanpyColumns.keys():
                # loaded has unexpected column, leave it
                logger.error(f'error: bAnalysisDir did not find loaded col: "{col}" in sanpyColumns.keys()')
        for col in self.sanpyColumns.keys():
            if not col in loadedColumns:
                # loaded is missing expected, add it
                logger.error(f'error: bAnalysisDir did not find sanpyColumns.keys() col: "{col}" in loadedColumns')
                self._df[col] = ''

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

            ba = self._df.loc[rowIdx, '_ba']  # Can be None

            #uuid = self._df.at[rowIdx, 'uuid']
            #
            # loaded
            if self.isLoaded(rowIdx):
                theChar = '\u2022'  # FILLED BULLET
            #elif uuid:
            #    #theChar = '\u25CB'  # open circle
            #    theChar = '\u25e6'  # white bullet
            else:
                theChar = ''
            #self._df.iloc[rowIdx, loadedCol] = theChar
            self._df.loc[rowIdx, 'L'] = theChar
            #
            # analyzed
            if self.isAnalyzed(rowIdx):
                theChar = '\u2022'  # FILLED BULLET
                self._df.loc[rowIdx, 'N'] = ba.numSpikes
            #elif uuid:
            #    #theChar = '\u25CB'
            #    theChar = '\u25e6'  # white bullet
            else:
                theChar = ''
                self._df.loc[rowIdx, 'A'] = ''
            #self._df.iloc[rowIdx, analyzedCol] = theChar
            self._df.loc[rowIdx, 'A'] = theChar
            #
            # saved
            if self.isSaved(rowIdx):
                theChar = '\u2022'  # FILLED BULLET
            else:
                theChar = ''
            #self._df.iloc[rowIdx, savedCol] = theChar
            self._df.loc[rowIdx, 'S'] = theChar
            #
            # start(s) and stop(s) from ba detectionDict
            if self.isAnalyzed(rowIdx):
                # set table to values we just detected with
                startSec = ba.detectionClass['startSeconds']
                stopSec = ba.detectionClass['stopSeconds']
                self._df.loc[rowIdx, 'Start(s)'] = startSec
                self._df.loc[rowIdx, 'Stop(s)'] = stopSec

                dvdtThreshold = ba.detectionClass['dvdtThreshold']
                mvThreshold = ba.detectionClass['mvThreshold']
                self._df.loc[rowIdx, 'dvdtThreshold'] = dvdtThreshold
                self._df.loc[rowIdx, 'mvThreshold'] = mvThreshold

                #
                # TODO: remove start of ba._path that corresponds to our current folder path
                # will allow our save db to be modular
                self._df.loc[rowIdx, 'relPath'] = ba._path

            # kymograph interface
            if ba is not None and ba.isKymograph():
                kRect = ba.getKymographRect()

                #print(kRect)
                #sys.exit(1)

                self._df.loc[rowIdx, 'kLeft'] = kRect[0]
                self._df.loc[rowIdx, 'kTop'] = kRect[1]
                self._df.loc[rowIdx, 'kRight'] = kRect[2]
                self._df.loc[rowIdx, 'kBottom'] = kRect[3]
                #
                # TODO: remove start of ba._path that corresponds to our current folder path
                # will allow our save db to be modular
                #self._df.loc[rowIdx, 'path'] = ba._path

    '''
    def setCellValue(self, rowIdx, colStr, value):
        self._df.loc[rowIdx, colStr] = value
    '''

    def isLoaded(self, rowIdx):
        isLoaded = self._df.loc[rowIdx, '_ba'] is not None
        return isLoaded

    def isAnalyzed(self, rowIdx):
        isAnalyzed = False
        ba = self._df.loc[rowIdx, '_ba']
        #print('isAnalyzed()', rowIdx, ba)
        #if ba is not None:
        if isinstance(ba, sanpy.bAnalysis):
            isAnalyzed = ba.isAnalyzed()
        return isAnalyzed

    def analysisIsDirty(self, rowIdx):
        """Analysis is dirty when there has been detection but not saved to h5.
        """
        isDirty = False
        ba = self._df.loc[rowIdx, '_ba']
        if isinstance(ba, sanpy.bAnalysis):
            isDirty = ba.isDirty()
        return isDirty

    def hasDirty(self):
        """Return true if any bAnalysis in list has been analyzed but not saved (e.g. is dirty)
        """
        haveDirty = False
        numRows = len(self._df)
        for rowIdx in range(numRows):
            if self.analysisIsDirty(rowIdx):
                haveDirty = True

        return haveDirty

    def isSaved(self, rowIdx):
        uuid = self._df.at[rowIdx, 'uuid']
        return len(uuid) > 0

    def getAnalysis(self, rowIdx, allowAutoLoad=True):
        """
        Get bAnalysis object, will load if necc.

        Args:
            rowIdx (int): Row index from table, corresponds to row in self._df
            allowAutoLoad (bool)
        Return:
            bAnalysis
        """
        file = self._df.loc[rowIdx, 'File']
        ba = self._df.loc[rowIdx, '_ba']
        uuid = self._df.loc[rowIdx, 'uuid']  # if we have a uuid bAnalysis is saved in h5f
        #filePath = os.path.join(self.path, file)

        #logger.info(f'Found _ba in file db with ba:"{ba}" {type(ba)}')

        #logger.info(f'rowIdx: {rowIdx} ba:{ba}')

        if ba is None or ba=='':
            #logger.info('did not find _ba ... loading from abf file ...')
            # working on kymograph
            filePath = self._df.loc[rowIdx, 'relPath']

            ba = self.loadOneAnalysis(filePath, uuid, allowAutoLoad=allowAutoLoad)
            # load
            '''
            logger.info(f'Loading bAnalysis from row {rowIdx} "{filePath}"')
            ba = sanpy.bAnalysis(filePath)
            '''
            if ba is None:
                logger.warning(f'Did not load row {rowIdx} path: "{filePath}". Analysis was probably not saved')
            else:
                self._df.at[rowIdx, '_ba'] = ba
                # does not get a uuid until save into h5
                if uuid:
                    # there was an original uuid (in table), means we are saved into h5
                    self._df.at[rowIdx, 'uuid'] = uuid
                    if uuid != ba.uuid:
                        logger.error('Loaded uuid does not match existing in file table')
                        logger.error(f'  Loaded {ba.uuid}')
                        logger.error(f'  Existing {uuid}')

                # kymograph, set ba rect from table
                if ba.isKymograph():
                    left = self._df.loc[rowIdx, 'kLeft']
                    top = self._df.loc[rowIdx, 'kTop']
                    right = self._df.loc[rowIdx, 'kRight']
                    bottom = self._df.loc[rowIdx, 'kBottom']

                    # on first load, these will be empty
                    # grab rect from ba (in _updateLoadedAnalyzed())
                    if left=='' or top=='' or right=='' or bottom=='':
                        pass
                    else:
                        theRect = [left, top, right, bottom]
                        print(f'  theRect:{theRect}')
                        ba._updateTifRoi(theRect)

                #
                # update stats of table load/analyzed columns
                self._updateLoadedAnalyzed()

        return ba

    def loadOneAnalysis(self, path, uuid=None, allowAutoLoad=True):
        """
        Load one bAnalysis either from original file path or uuid of h5 file.

        If from h5, we still need to reload sweeps !!!
        They are binary and fast, saving to h5 (in this case) is slow.
        """
        logger.info(f'path:"{path}" uuid:"{uuid}" allowAutoLoad:"{allowAutoLoad}"')

        ba = None
        allowUUID = True  # on transition to bAnalysis save as json
        if allowUUID and uuid is not None and uuid:
            # load from h5
            hdfFile = os.path.splitext(self.dbFile)[0] + '.h5'
            hdfPath = os.path.join(self.path, hdfFile)
            with pd.HDFStore(hdfPath) as hdfStore:
                # hdfStore is of type pandas.io.pytables.HDFStore
                try:
                    logger.info(f'retreiving uuid from hdf file {uuid}')

                    realKey = '/' + uuid

                    if not realKey in hdfStore.keys():
                        logger.error(f' did not find uuid in hdf store, uuid: {realKey}')
                        print('  valid h5 keys are:')
                        for key in hdfStore.keys():
                            print('    ', key)

                    # logger.info(f'hdfStore: {hdfStore}')

                    # dfAnalysis = hdfStore[realKey]

                    # i don't understand why accessing an hd5 key we get a vlaue error (it is type checking my cutum enum types???
                    try:
                        dfAnalysis = hdfStore.select(realKey)
                    except(ValueError) as e:
                        logger.error(f'!!!!!!!!!!!!!!! my exception: {e}')

                    #logger.info(f'dfAnalysis is of type {type(dfAnalysis)}')

                    # 20220422, need to fix the path here !!!
                    #logger.info('NEED TO FIX THE PATH HERE')
                    #print('  dfAnalysis is:')
                    #print("dfAnalysis['_path']:", dfAnalysis['_path'])
                    logger.info(f'swapping dfAnalysis _path to: {path}')
                    dfAnalysis['_path'] = path
                    
                    #pprint(dfAnalysis)
                    

                    ba = sanpy.bAnalysis(fromDf=dfAnalysis)



                    # WHY IS THIS BROKEN ?????????????????????????????????????????????????????????????
                    # This is SLOPPY ON MY PART, WE ALWAYS NEED TO RELOAD FILTER
                    # ADD SOME COD  THAT CHECKS THIS AND REBUILDS AS NECC !!!!!!!!!!
                    if path.endswith('.tif'):
                        # kymograph
                        ba._loadTif()
                    else:
                        ba._loadAbf()
                    ba.rebuildFiltered()


                    logger.info(f'Loaded ba from h5 uuid {uuid} and now ba:{ba}')
                except (KeyError):
                    logger.error(f'Did not find uuid in h5 file, uuid:{uuid}')
        if allowAutoLoad and ba is None:
            # load from path
            ba = sanpy.bAnalysis(path)
            logger.info(f'Loaded ba from path {path} and now ba:{ba}')
        #
        return ba

    def _setColumnType(self, df):
        """
        Needs to be called every time a df is created.
        Ensures proper type of columns following sanpyColumns[key]['type']
        """
        #print('columns are:', df.columns)
        for col in df.columns:
            # when loading from csv, 'col' may not be in sanpyColumns
            if not col in self.sanpyColumns:
                logger.warning(f'Column "{col}" is not in sanpyColumns -->> ignoring')
                continue
            colType = self.sanpyColumns[col]['type']
            #print(f'  _setColumnType() for "{col}" is type "{colType}"')
            #print(f'    df[col]:', 'len:', len(df[col]))
            #print(df[col])
            if colType == str:
                df[col] = df[col].replace(np.nan, '', regex=True)
                df[col] = df[col].astype(str)
            elif colType == int:
                pass
                #print('!!! df[col]:', df[col])
                #df[col] = df[col].astype(int)
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
        """
        Get dict representing one file (row in table). Loads bAnalysis to get headers.

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

        # load bAnalysis
        #logger.info(f'Loading bAnalysis "{path}"')
        ba = sanpy.bAnalysis(path, loadData=loadData)

        if ba.loadError:
            logger.error(f'Error loading bAnalysis file "{path}"')
            #return None, None

        # not sufficient to default everything to empty str ''
        # sanpyColumns can only have type in ('float', 'str')
        rowDict = dict.fromkeys(self.sanpyColumns.keys() , '')
        for k in rowDict.keys():
            if self.sanpyColumns[k]['type'] == str:
                rowDict[k] = ''
            elif self.sanpyColumns[k]['type'] == float:
                rowDict[k] = np.nan

        #if rowIdx is not None:
        #    rowDict['Idx'] = rowIdx

        '''
        if ba.loadError:
            rowDict['I'] = 0
        else:
            rowDict['I'] = 2 # need 2 because checkbox value is in (0,2)
        '''

        rowDict['File'] = ba.getFileName() #os.path.split(ba.path)[1]
        rowDict['Dur(s)'] = ba.recordingDur
        rowDict['Sweeps'] = ba.numSweeps
        rowDict['kHz'] = ba.recordingFrequency
        rowDict['Mode'] = ba.recordingMode

        #rowDict['dvdtThreshold'] = 20
        #rowDict['mvThreshold'] = -20
        if ba.isAnalyzed():
            dDict = ba.getDetectionDict()
            rowDict['I'] = dDict.getValue('include')
            rowDict['dvdtThreshold'] = dDict.getValue('dvdtThreshold')
            rowDict['mvThreshold'] = dDict.getValue('mvThreshold')
            rowDict['Start(s)'] = dDict.getValue('startSeconds')
            rowDict['Stop(s)'] = dDict.getValue('stopSeconds')

        return ba, rowDict

    def getFileList(self, path=None, getFullPath=True):
        """
        Get file paths from path.

        Uses self.theseFileTypes
        """
        if path is None:
            path = self.path

        logger.warning('MODIFIED TO LOAD TIF FILES IN SUBFOLDERS')
        count = 0
        tmpFileList = []
        folderDepth = self.folderDepth  # if none then all depths
        for root, subdirs, files in os.walk(path):
            #print('analysisDir.getFileList() count:', count)
            #print('  ', root)
            #print('  ', subdirs)
            #print('  ', files)
            '''
            parentFolder = os.path.split(root)[1]
            print(root)
            print('  ', parentFolder)
            if parentFolder.startswith('__'):
                continue
            '''
            if folderDepth is not None and count > folderDepth:
                break
            count += 1
            for file in files:
                #if file.endswith('.tif'):
                if file.endswith('.tif') or file.endswith('.abf'):
                    oneFile = os.path.join(root, file)
                    #print('  ', oneFile)
                    tmpFileList.append(oneFile)
        #tmpFileList = os.listdir(path)

        fileList = []
        for file in sorted(tmpFileList):
            if file.startswith('.'):
                continue
            # ignore our database file
            if file == self.dbFile:
                continue

            # tmpExt is like .abf, .csv, etc
            tmpFileName, tmpExt = os.path.splitext(file)
            if tmpExt in self.theseFileTypes:
                if getFullPath:
                    #file = os.path.join(path, file)
                    file = pathlib.Path(path) / file
                    file = str(file)  # return List[str] NOT List[PosixPath]
                fileList.append(file)
        #
        logger.info(f'found {len(fileList)} files ...')
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
        #for colStr in self.columns:
        for colStr in self._df.columns:
            #theRet[colStr] = self._df.loc[rowIdx, colStr]
            theRet[colStr] = self._df.loc[rowIdx, colStr]
        #theRet['_ba'] = theRet['_ba'].copy()
        return theRet

    def appendRow(self, rowDict=None, ba=None):
        # append one empty row
        rowSeries = pd.Series()
        if rowDict is not None:
            rowSeries = pd.Series(rowDict)
            # self._data.iloc[row] = rowSeries
            # self._data = self._data.reset_index(drop=True)

        newRowIdx = len(self._df)
        df = self._df
        df = df.append(rowSeries, ignore_index=True)
        df = df.reset_index(drop=True)

        if ba is not None:
            df.loc[newRowIdx, '_ba'] = ba

        #
        self._df = df

    def unloadRow(self, rowIdx):
        self._df.loc[rowIdx, '_ba'] = None
        self._updateLoadedAnalyzed()

    def removeRowFromDatabase(self, rowIdx):
        # delete from h5 file
        uuid = self._df.at[rowIdx, 'uuid']
        self._deleteFromHdf(uuid)

        # clear uuid
        self._df.at[rowIdx, 'uuid'] = ''

    def deleteRow(self, rowIdx):
        df = self._df

        # delete from h5 file
        uuid = df.at[rowIdx, 'uuid']
        self._deleteFromHdf(uuid)

        # delete from df/model
        df = df.drop([rowIdx])
        df = df.reset_index(drop=True)
        self._df = df

    def duplicateRow(self, rowIdx):
        # duplicate rowIdx
        newIdx = rowIdx + 0.5

        rowDict = self.getRowDict(rowIdx)

        # CRITICAL: Need to make a deep copy of the _ba pointer to bAnalysis object
        logger.info(f"copying {type(rowDict['_ba'])} {rowDict['_ba']}")
        baNew = copy.deepcopy(rowDict['_ba'])

        # copy of bAnalysis needs a new uuid
        new_uuid = sanpy.bAnalysis.getNewUuid()  # 't' + str(uuid.uuid4())   #.replace('-', '_')
        logger.info(f'assigning new uuid {new_uuid} to {baNew}')

        if baNew.uuid == new_uuid:
            logger.error('!!!!!!!!!!!!!!!!!!!!!!!!!CRITICAL, new uuid is same as old')

        baNew.uuid = new_uuid

        rowDict['_ba'] = baNew
        rowDict['uuid'] = baNew.uuid  # new row can never have same uuid as old

        dfRow = pd.DataFrame(rowDict, index=[newIdx])

        df = self._df
        df = df.append(dfRow, ignore_index=True)
        df = df.sort_values(by=['File'], axis='index', ascending=True, inplace=False)
        df = df.reset_index(drop=True)
        self._df = df

    def syncDfWithPath(self):
        """
        Sync path with existing df. Used to pick up new/removed files"""
        pathFileList = self.getFileList(getFullPath=False)
        dfFileList = self._df['File'].tolist()

        '''
        print('=== pathFileList:')
        print(pathFileList)
        print('=== dfFileList:')
        print(dfFileList)
        '''

        addedToDf = False

        # look for files in path not in df
        for pathFile in pathFileList:
            if pathFile not in dfFileList:
                logger.info(f'Found file in path "{pathFile}" not in df')
                # load bAnalysis and get df column values
                addedToDf = True
                fullPathFile = os.path.join(self.path, pathFile)
                ba, rowDict = self.getFileRow(fullPathFile) # loads bAnalysis
                if rowDict is not None:
                    #listOfDict.append(rowDict)
                    self.appendRow(rowDict=rowDict, ba=ba)

        # look for files in df not in path
        for dfFile in dfFileList:
            if not dfFile in pathFileList:
                logger.info(f'Found file in df "{dfFile}" not in path')

        if addedToDf:
            df = self._df
            df = df.sort_values(by=['File'], axis='index', ascending=True, inplace=False)
            df = df.reset_index(drop=True)
            self._df = df

    def pool_build(self):
        """Build one df with all analysis. Use this in plot tool plugin.
        """
        masterDf = None
        for row in range(self.numFiles):
            if not self.isAnalyzed(row):
                continue
            ba = self.getAnalysis(row)
            if ba.dfReportForScatter is not None:
                self.signalApp(f'adding "{ba.getFileName()}"')
                ba.dfReportForScatter['File Number'] = row
                if masterDf is None:
                    masterDf = ba.dfReportForScatter
                else:
                    masterDf = pd.concat([masterDf, ba.dfReportForScatter])
        #
        if masterDf is None:
            logger.error('Did not find any analysis.')
        else:
            logger.info(f'final num spikes {len(masterDf)}')
        #print(masterDf.head())
        self._poolDf = masterDf

        return self._poolDf

    def signalApp(self, str):
        """Update status bar of SanPy app.

        TODO make this a signal and connect app to it.
            Will not be able to do this, we need to run outside Qt
        """
        if self.myApp is not None:
            self.myApp.slot_updateStatus(str)
        else:
            logger.info(str)

    def api_getFileHeaders(self):
        headerList = []
        df = self.getDataFrame()
        for row in range(len(df)):
            #ba = self.getAnalysis(row)  # do not call this, it will load
            ba = df.at[row, '_ba']
            if ba is not None:
                headerDict = ba.api_getHeader()
                headerList.append(headerDict)
        #
        return headerList

def _printDict(d):
    for k,v in d.items():
        print('  ', k, ':', v)

def test3():
    path = '/home/cudmore/Sites/SanPy/data'
    bad = analysisDir(path)

    #file = '19221014.abf'
    rowIdx = 3
    ba = bad.getAnalysis(rowIdx)
    ba = bad.getAnalysis(rowIdx)

    print(bad.getDataFrame())

    print('bad.shape', bad.shape)
    print('bad.columns:', bad.columns)

    print('bad.iloc[rowIdx,5]:', bad.iloc[rowIdx,5])
    print('setting to xxxyyyzzz')

    # setter
    #bad.iloc[2,5] = 'xxxyyyzzz'

    print('bad.iloc[2,5]:', bad.iloc[rowIdx,5])
    print('bad.loc[2,"File"]:', bad.loc[rowIdx,'File'])

    print('bad.iloc[2]')
    print(bad.iloc[rowIdx])
    #bad.iloc[rowIdx] = ''
    print('bad.loc[2]')
    print(bad.loc[rowIdx])

    #bad.saveDatabase()

def test_hd5_2():
    folderPath = '/home/cudmore/Sites/SanPy/data'
    if 1:
        # save analysisDir hdf
        bad = analysisDir(folderPath)
        print('bad._df:')
        print(bad._df)
        #bad.saveDatabase()  # save .csv
        bad.saveHdf()  # save ALL bAnalysis in .h5

    if 0:
        # load h5 and reconstruct a bAnalysis object
        start = time.time()
        hdfPath = '/home/cudmore/Sites/SanPy/data/sanpy_recording_db.h5'
        with pd.HDFStore(hdfPath, 'r') as hdfStore:
            for key in hdfStore.keys():

                dfTmp = hdfStore[key]
                #path = dfTmp.iloc[0]['path']

                print('===', key)
                #if not key.startswith('/r6'):
                #    continue
                #for col in dfTmp.columns:
                #    print('  ', col, dfTmp[col])
                #print(key, type(dfTmp), dfTmp.shape)
                #print('dfTmp:')
                #print(dfTmp)


                #print(dfTmp.iloc[0]['_sweepX'])

                # load bAnalysis from a pandas DataFrame
                ba = sanpy.bAnalysis(fromDf=dfTmp)

                print(ba)

                ba.spikeDetect()  # this should reproduce exactly what was save ... It WORKS !!!

        stop = time.time()
        logger.info(f'h5 load took {round(stop-start,3)} seconds')

def test_hd5():
    import time
    start = time.time()
    hdfStore = pd.HDFStore('store.gzip')
    if 1:
        path = '/home/cudmore/Sites/SanPy/data'
        bad = analysisDir(path)

        # load all bAnalysis
        for idx in range(len(bad)):
            bad.getAnalysis(idx)

        hdfStore['df'] = bad.getDataFrame()  # save it
        bad.saveDatabase()

    if 0:
        df = hdfStore['df']  # load it
        print('loaded df:')
        print(df)
    stop = time.time()
    print(f'took {stop-start}')

def test_pool():
    path = '/home/cudmore/Sites/SanPy/data'
    bad = analysisDir(path)
    print('loaded df:')
    print(bad._df)

    bad.pool_build()

def testCloud():
    cloudDict = {
        'owner': 'cudmore',
        'repo_name': 'SanPy',
        'path': 'data'
    }
    bad = bAnalysisDirWeb(cloudDict)

if __name__ == '__main__':
    #test3()
    #test_hd5()
    test_hd5_2()
    #test_pool()
    #testCloud()

    #test_timing()
    #plotTiming()
