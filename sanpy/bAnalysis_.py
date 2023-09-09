import os
import math
import time
import datetime
import copy
import json
from collections import OrderedDict
import warnings  # to catch np.polyfit -->> RankWarning: Polyfit may be poorly conditioned

from typing import Union, Dict, List, Tuple, Optional

# import h5py

import numpy as np
import pandas as pd
import scipy
import scipy.signal
import scipy.stats

import pyabf  # see: https://github.com/swharden/pyABF

import sanpy
import sanpy.bDetection
import sanpy.user_analysis.baseUserAnalysis  # to stop circular imports
import sanpy.h5Util
import sanpy.fileloaders
import sanpy.bAnalysisResults
import sanpy._util

from sanpy.fileloaders import recordingModes

# from metaData import MetaData

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class bAnalysis:
    """
    The bAnalysis class represents a whole-cell recording and provides functions for analysis.

    A bAnalysis object can be created in a number of ways:
    (i) From a file path including .abf and .csv
    (ii) From a pandas DataFrame when loading from a h5 file.
    (iii) From a byteStream abf when working in the cloud.

    Once loaded, a number of operations can be performed including:
    Spike detection, Error checking, Plotting, and Saving.

    Examples:

    ```python
    path = 'data/19114001.abf'
    ba = bAnalysis(path)
    dDict = sanpy.bDetection().getDetectionDict('SA Node')
    ba.spikeDetect(dDict)
    print(ba)
    ```
    """

    # def getNewUuid():
    #     return 't' + str(uuid.uuid4()).replace('-', '_')

    def __init__(
        self,
        filepath: str = None,
        byteStream=None,
        loadData: bool = True,
        fileLoaderDict: dict = None,
        stimulusFileFolder: str = None,
        verbose: bool = False,
    ):
        """
        Args:
            filepath (str): Path to either .abf or .csv with time/mV columns.
            byteStream (io.BytesIO): Binary stream for use in the cloud.
            loadData: If true, load raw data, otherwise just load header
            fileLoaderDict (dict)
                If None then fetch from sanpy.fileloaders.getFileLoaders()
                Do this if running in a script.
                If running an SanPy app, we pass the dict
            stimulusFileFolder:
        """

        """
        self._path = file  # todo: change this to filePath
        """
        """str: File path."""

        self._detectionDict: dict = None  # corresponds to an item in sanpy.bDetection

        # sept 9, moving this to file loader
        # fileloader holds meta data
        #self._metaData = MetaData(self)  #self.getMetaDataDict()

        self._isAnalyzed: bool = False

        self.loadError: bool = False
        """bool: True if error loading file/stream."""

        # self.detectionDict = None  # remember the parameters of our last detection
        """dict: Dictionary specifying detection parameters, see bDetection.getDefaultDetection."""

        # self._abf = None
        """pyAbf: If loaded from binary .abf file"""

        self.dateAnalyzed: str = None
        """str: Date Time of analysis. TODO: make a property."""

        # self.detectionType = None
        """str: From ('dvdt', 'mv')"""

        self.spikeDict: sanpy.bAnalysisResults.analysisResultList = (
            sanpy.bAnalysisResults.analysisResultList()
        )
        # class to store all analysis results

        # self._spikesPerSweep : int = None

        self.spikeClips = []  # created in self.spikeDetect()
        self.spikeClips_x = []  #
        self.spikeClips_x2 = []  #

        self.dfError = None  # dataframe with a list of detection errors
        self._dfReportForScatter = None  # dataframe to be used by scatterplotwidget

        self._detectionDirty = False

        # will be overwritten by existing uuid in self._loadFromDf()
        self.uuid = sanpy._util.getNewUuid()

        # self.tifData = None
        # when we have a tif kymograph

        # self.isBytesIO = False
        # when we are running in the cloud

        # TODO (cudmore) need to parse folder of file loaders in fileloders/ and determine
        # class to use to load file (using fileLoader.filetype
        self._fileLoader = None
        if filepath is not None and not os.path.isfile(filepath):
            logger.error(f'File does not exist: "{filepath}"')
            self.loadError = True
        else:
            if fileLoaderDict is None:
                fileLoaderDict = (
                    sanpy.fileloaders.getFileLoaders()
                )  # EXPENSIVE, to do, pass in from app

            _ext = os.path.splitext(filepath)[1]
            _ext = _ext[1:]
            try:
                if verbose:
                    logger.info(f"Loading file with extension: {_ext}")
                constructorObject = fileLoaderDict[_ext]["constructor"]
                self._fileLoader = constructorObject(filepath)
                # may 2, 2023
                if self._fileLoader._loadError:
                    logger.error(f'load error in file loader for ext: "{_ext}"')
                    self.loadError = True

            except KeyError as e:
                logger.error(f'did not find a file loader for extension "{_ext}"')
                self.loadError = True
            
            self._kymAnalysis : sanpy.kymAnalysis = None
            if (self.fileLoader is not None) and (self.fileLoader.recordingMode == recordingModes.kymograph):
                if verbose:
                    logger.info('creating kymAnalysis')
                    logger.info(f'    self.fileLoader.filepath:{self.fileLoader.filepath}')
                    logger.info(f'    self.fileLoader.filepath:{self.fileLoader.tifData.shape}')
                    logger.info(f'    self.fileLoader.filepath:{self.fileLoader.tifHeader}')
                self._kymAnalysis = sanpy.kymAnalysis(self.fileLoader.filepath,
                                                      self.fileLoader.tifData,
                                                      self.fileLoader.tifHeader)

            if self._fileLoader is not None:
                # we need to so file loader meta data can set ba (Self) dirty when changed
                self.fileLoader.metadata._ba = self


        """
        if byteStream is not None:
            self._loadAbf(byteStream=byteStream,
                    loadData=loadData,
                    stimulusFileFolder=stimulusFileFolder)
        elif file is not None and file.endswith('.abf'):
            self._loadAbf(loadData=loadData)
        elif file is not None and file.endswith('.atf'):
            self._loadAtf(loadData=loadData)
        elif file is not None and file.endswith('.tif'):
            self._loadTif()
        elif file is not None and file.endswith('.csv'):
            self._loadCsv()
        else:
            pass
            #logger.error(f'Can only open abf/csv/tif/stream files: {file}')
            #self.loadError = True
        """

        # get default derivative
        if loadData and not self.loadError:
            self._rebuildFiltered()

        self._detectionDirty = False

        """
        self.setSweep()
        """

    @property
    def metaData(self):
        # sept 9, moved to file loader
        # return self._metaData
        return self.fileLoader.metadata
    
    @property
    def kymAnalysis(self):
        """Get the kymAnalysis object (if it exists).
        """
        return self._kymAnalysis
    
    @property
    def fileLoader(self):
        """ """
        return self._fileLoader

    def getFileName(self):
        return self.fileLoader.filename

    def asDataFrame(self):
        """Return analysis as a Pandas DataFrame.

        Important:
            This is a df copy of our self.spikeDict
            Do not modify and expect changes to stick
        """
        return self._dfReportForScatter
        # return self.spikeDict.asDataFrame()

    def getDetectionDict(self, asCopy: bool = False):
        """Get the detection dictionary that was used for detect()."""
        if asCopy:
            return copy.deepcopy(self._detectionDict)
        else:
            return self._detectionDict

    def __str__(self):
        """Get a brief str representation. Usefull for print()."""
        # if self.isBytesIO:
        #      filename = '<BytesIO>'
        # else:
        #     filename = self.getFileName()
        fileLoadStr = self.fileLoader.__str__()
        txt = f"fileLoader: {fileLoadStr} spikes:{self.numSpikes}"
        return txt

    def _saveHdf_pytables(self, hdfPath):
        """Save detection parameters and analysis into an hdf5 file.
        """

        # save kym diameter analysis
        if self._kymAnalysis is not None:
            if self._kymAnalysis.hasDiamAnalysis() and self._kymAnalysis._analysisDirty:
                self._kymAnalysis.saveAnalysis()


        if not self.detectionDirty:
            # Do not save it detection has not changed
            logger.info(f"NOT SAVING, is not dirty {self}")
            return False

        # always save as csv
        self.saveAnalysis_tocsv()

        # when making df from dict, need to pass it a list
        # o.w. key values that are lists get expanded into rows
        if self._detectionDict is not None:
            dfDetection = pd.DataFrame([self._detectionDict])

        dfMetaData = pd.DataFrame([self.metaData])

        # convert spikeList (list of dict) to json
        # spikeList = self.spikeDict.asList()
        # dataJson = json.dumps(spikeList, cls=NumpyEncoder)  # list of dict
        # dfAnalysis = pd.DataFrame(spikeList)
        if len(self.spikeDict) > 0:
            dfAnalysis = self.spikeDict.asDataFrame()

        uuid = self.uuid

        logger.info(
            f"    Saving {self.numSpikes} spikes to uuid {uuid} in h5 file {hdfPath}"
        )

        with pd.HDFStore(hdfPath) as hdfStore:
            if self._detectionDict is not None:
                key = uuid + "/" + "detectionDict"
                dfDetection.to_hdf(hdfStore, key)  # default mode='a'

            # always save meta data
            key = uuid + "/" + "metaDataDict"
            dfMetaData.to_hdf(hdfStore, key)  # default mode='a'
            
            # logger.warning('=== saving dfMetaData')
            # print(dfMetaData)

            if len(self.spikeDict) > 0:
                key = uuid + "/" + "analysisList"
                dfAnalysis.to_hdf(hdfStore, key)

        # we saved, detection is not dirty
        self._detectionDirty = False

        return True

    def _findUuid(self, hdfPath):
        """Find this analysis uuid in an h5 file. If analysis is not saved, it will not exists.
        """

        # load the database
        detectionDictKey = 'sanpy_recording_db'
        dfDetection = pd.read_hdf(hdfPath, key=detectionDictKey)
        
        fileList = dfDetection['File'].to_list()
        
        filename = self.fileLoader.filename
        try:
            idx = fileList.index(filename)
        except (ValueError) as e:
            #logger.warning(f'did not find file {filename} in file list {fileList}')
            return
        
        uuid = dfDetection['uuid'].to_list()[idx]

        return uuid
    
    def _loadHdf_pytables(self, hdfPath, uuid = None):
        """Load analysis from an h5 file using key 'uuid'.

        Parameters
        ----------
        hdfPath : str
            path to h5 file
        uuid : uuid
            Unique uuid for the file, if None then will try and find the file in hdfPath

        Notes
        -----
        If uuid is None, this only work for 'flat' directories,
        the ba has to be in same folder as h5 file
        """

        # df.to_dict() requires into=OrderedDict, o.w. column order is sorted
        # Error report needs to be generated (is not in h5 file) use getErrorReport()

        # cant use pd.HDFStore(<path>) as read_hdf does not understand file pointer

        if uuid is None:
            uuid = self._findUuid(hdfPath)
            if uuid is None:
                logger.warning(f'did not find a uuid for {self.fileLoader.filename} in h5 file {hdfPath}')
                logger.warning(f'this usually happens when the analysis was not saved')
                return
            
        # logger.info(f"loading {uuid} from {hdfPath}")

        # load pandas dataframe(s) from h5 file
        loadedDetection = False
        loadedMetaData = False
        loadedAnalysis = False
        try:
            detectionDictKey = uuid + "/" + "detectionDict"  # group
            dfDetection = pd.read_hdf(hdfPath, detectionDictKey)
            loadedDetection = True
        except KeyError as e:
            logger.error(f'detectionDict: {e}')
            # didLoad = False
            
        try:
            metaDataDictKey = uuid + "/" + "metaDataDict"  # group
            dfMetaData = pd.read_hdf(hdfPath, metaDataDictKey)
            loadedMetaData = True
        except KeyError as e:
            logger.error(f'metaDataDict: {e}')
            # didLoad = False

        try:
            analysisListKey = uuid + "/" + "analysisList"
            dfAnalysis = pd.read_hdf(hdfPath, analysisListKey)
            loadedAnalysis = True
        except KeyError as e:
            logger.error(f'analysisList: {e}')
            # didLoad = False

        # if didLoad:
        if 1:
            # we take on the uuid we were loaded from
            self.uuid = uuid

            # convert to a dict
            if loadedDetection:
                detectionDict = dfDetection.to_dict("records", into=OrderedDict)[
                    0
                ]  # one dict
                self._detectionDict = detectionDict

            if loadedMetaData:
                metaDataDict = self.metaData.getMetaDataDict()  # default
                loadedMetaDataDict = dfMetaData.to_dict("records", into=OrderedDict)[
                    0
                ]  # one dict
                # we need to load current meta data dict with all current keys
                # saved file may be out of date

                # bug during implementing meta data code
                # if loadedMetaDataDict['sex'] == '':
                #     loadedMetaDataDict['sex'] = 'unknown'

                # logger.info('loadedMetaDataDict')
                # logger.info(loadedMetaDataDict)

                for k,v in loadedMetaDataDict.items():
                    if not k in metaDataDict.keys():
                        logger.error(f'did not find loaded meta data key "{k}" in meta data keys {metaDataDict.keys()}')
                        continue
                    metaDataDict[k] = v
                self.metaData.fromDict(metaDataDict, triggerDirty=False)

                # logger.warning(f'LOADED META DATA:')
                # print('self.metaData:', self.metaData)

            # convert to a list of dict
            if loadedAnalysis:
                analysisList = dfAnalysis.to_dict(
                    "records", into=OrderedDict
                )  # list of dict
                self.spikeDict.setFromListDict(analysisList)
                # pprint(analysisList[0])

                # recreate spike analysis dataframe
                # self._dfReportForScatter = dfAnalysis
                self.regenerateAnalysisDataFrame()

                # regenerate error report
                self.dfError = self.getErrorReport()

                # dec 2022
                self._isAnalyzed = True

            # logger.info(
            #     f"    loaded {len(detectionDict.keys())} detection keys and {len(self.spikeDict)} spikes"
            # )
        else:
            logger.error(f"    LOAD FAILED")

    @property
    def detectionDirty(self):
        return self._detectionDirty

    @property
    def numSpikes(self):
        """Get the total number of detected spikes (all sweeps).

        See getNumSpikes(sweep)
        """
        return len(self.spikeDict)  # spikeDict has all spikes for all sweeps

    def getNumSpikes(self, sweep: int = 0):
        """Get number of spikes in a sweep.

        See property numSpikes
        """
        thresholdSec = self.getStat("thresholdSec", sweepNumber=sweep)
        return len(thresholdSec)
        # return self._spikesPerSweep[sweep]

    @property
    def numErrors(self) -> int:
        """Get number of detection errors.
        """
        if self.dfError is None:
            # no analysis
            return None
        else:
            return len(self.dfError)
        
    def _old_getAbsSpikeFromSweep(self, sweepSpikeIdx: int, sweep: int) -> int:
        """Given a spike index within a sweep, get the absolute spike index.

        See getSweepSpikeFromAbsolute()
        """
        absIdx = 0
        for sweepIdx in range(sweep):
            absIdx += self._spikesPerSweep[sweepIdx]
        absIdx += sweepSpikeIdx
        return absIdx

    def getSweepSpikeFromAbsolute(self, absSpikeIdx: int, sweep: int) -> int:
        """Get sweep spike from absolute spike.

        See getAbsSpikeFromSweep()
        """
        sweepSpikeNum = self.spikeDict[absSpikeIdx]["sweepSpikeNumber"]
        return sweepSpikeNum

        # absIdx = 0
        # for oneSweep in range(sweep):
        #     absIdx += self._spikesPerSweep[oneSweep]
        # sweepSpike = absSpikeIdx - absIdx
        # return sweepSpike

    def isDirty(self):
        """Return True if analysis has been modified but not save."""
        return self._detectionDirty

    def isAnalyzed(self):
        """Return True if this bAnalysis has been analyzed, False otherwise."""
        return self._isAnalyzed

    def getStatMean(self, statName: str, sweepNumber: int = None):
        """
        Get the mean of an analysis parameter.

        Args:
            statName (str): Name of the statistic to retreive.
                For a list of available stats use bDetection.defaultDetection.
        """
        theMean = None
        x = self.getStat(statName, sweepNumber=sweepNumber)
        if x is not None and len(x) > 1:
            theMean = np.nanmean(x)
        return theMean

    def getSpikeStat(self, spikeList : List[int], stat : str):
        """Get one stat from a list of spikes
        
        Parameters
        ----------
        spikeList : List[int]
        stat : str
        """

        # if isinstance(spikeList, int):
        #     spikeList = [spikeList]

        if len(spikeList) == 0:
            return None

        # logger.info(f'spikeList: {spikeList} stat:{stat}')
        
        retList = []
        # count = 0
        for idx, spike in enumerate(self.spikeDict):
            # logger.info(f'  idx:{idx}')
            if idx in spikeList:
                try:
                    val = spike[stat]
                    retList.append(val)
                    # count += 1
                except KeyError as e:
                    logger.error(e)
        # logger.info(f'  retList: {retList}')
        return retList

    def setSpikeStat_time(self, startSec: int, stopSec: int, stat: str, value):
        """Set a spike stat for spikes in a range of time."""

        # get spike list in range [startSec, stopSec]
        spikeSeconds = self.getSpikeSeconds()
        spikeList = [
            idx for idx, x in enumerate(spikeSeconds) if x >= startSec and x < stopSec
        ]
        self.setSpikeStat(spikeList, stat, value)

    def setSpikeStat(self, spikeList: Union[list, int], stat: str, value):
        """Set a spike stat for one spike or a list of spikes.

        Used to set things like ('isBad', 'userType1', 'condition', ...)
        """
        if isinstance(spikeList, int):
            spikeList = [spikeList]
            # else:
            #     logger.error(f'Expecting list[int] or int but got spikeList type {type(spikeList)}')
            return

        if len(spikeList) == 0:
            return

        now = datetime.datetime.now()
        modDate = now.strftime("%Y%m%d")
        modTime = now.strftime("%H:%M:%S")

        for spike in spikeList:
            self.spikeDict[spike][stat] = value
            self.spikeDict[spike]["modDate"] = modDate
            self.spikeDict[spike]["modTime"] = modTime

        self._detectionDirty = True

        logger.info(f'set spikes {spikeList} stat "{stat}" to value "{value}"')

        """
        count = 0
        for idx, spike in enumerate(self.spikeDict):
            if idx in spikeList:
                try:
                    spike[stat] = value
                    count += 1
                except (KeyError) as e:
                    logger.info(e)
        #
        logger.info(f'Given {len(spikeList)} and set {count}')
        """

    def _old_getSweepStats(
        self, statName: str, decimals=3, asDataFrame=False, df: pd.DataFrame = None
    ):
        """

        Args:
            df (pd.DataFrame): For kymograph we sometimes have to convert (peak) values to molar
        """

        if df is None:
            df = self.spikeDict.asDataFrame()

        sweepStatList = []

        for sweep in range(self.fileLoader.numSweeps):
            oneDf = df[df["sweep"] == sweep]
            theValues = oneDf[statName]

            theCount = np.count_nonzero(~np.isnan(theValues))
            theMin = np.min(theValues)
            theMax = np.max(theValues)
            theMean = np.nanmean(theValues)

            theMin = round(theMin, decimals)
            theMax = round(theMax, decimals)
            theMean = round(theMean, decimals)

            if theCount > 2:
                theMedian = np.nanmedian(theValues)
                theSEM = scipy.stats.sem(theValues)
                theSD = np.nanstd(theValues)
                theVar = np.nanvar(theValues)
                theCV = theSD / theVar

                theMedian = round(theMedian, decimals)
                theSEM = round(theSEM, decimals)
                theSD = round(theSD, decimals)
                theVar = round(theVar, decimals)
                theCV = round(theCV, decimals)

            else:
                theMedian = None
                theSEM = None
                theSD = None
                theVar = None
                theCV = None

            oneDict = {
                statName + "_sweep": sweep,
                statName + "_count": theCount,
                statName + "_min": theMin,
                statName + "_max": theMax,
                statName + "_mean": theMean,
                statName + "_median": theMedian,
                statName + "_sem": theSEM,
                statName + "_std": theSD,
                statName + "_var": theVar,
                statName + "_cv": theCV,
            }

            sweepStatList.append(oneDict)

        #
        if asDataFrame:
            return pd.DataFrame(sweepStatList)
        else:
            return sweepStatList

    def getStat(
        self,
        statName1,
        statName2: Optional[str] = None,
        sweepNumber: Optional[int] = None,
        epochNumber: Optional[int] = None,
        asArray: Optional[bool] = False,
        getFullList : Optional[bool] = False
    ):
        """Get a list of values for one or two analysis results.

        Parameters
        ----------
        statName1 : str
            Name of the first analysis parameter to retreive.
        statName2 : str
            Optional name of the second analysis parameter to retreive.
        sweepNumber : int str or None
            Optional sweep number, if None or 'All' then get all sweeps
        epochNumber : int str or None
            Optional epoch number, if None or 'All' then get all epochs
        asArray : bool
            If True then return as np.array(), otherwise return as a list

        Notes
        -----
        For a list of available analysis results,
            see [bDetection.getDefaultDetection()][sanpy.bDetection.bDetection]

        If the returned list of analysis results are in points,
            convert to seconds or ms using: pnt2Sec_(pnt) or pnt2Ms_(pnt).

        Returns
        -------
        list or np.array
            List of analysis parameter values, None if error.
            Returns a np.array is asArray is True
        """

        def clean(val):
            """Convert None to float('nan')"""
            if val is None:
                val = float("nan")
            return val

        x = []  # None
        y = []  # None
        error = False
        if len(self.spikeDict) == 0:
            # logger.error(f'Did not find any spikes in spikeDict')
            error = True
        elif statName1 not in self.spikeDict[0].keys():
            logger.error(f'Did not find statName1: "{statName1}" in spikeDict')
            error = True
        elif statName2 is not None and statName2 not in self.spikeDict[0].keys():
            logger.error(f'Did not find statName2: "{statName2}" in spikeDict')
            error = True

        if sweepNumber is None:
            sweepNumber = "All"

        if epochNumber is None:
            epochNumber = "All"

        if not error:
            # original
            # x = [clean(spike[statName1]) for spike in self.spikeDict]
            
            if getFullList:
                # April 15, 2023, trying to fix bug in scatter plugin when we are
                # using sweep and epoch
                # strategy is to return all spikes, just nan out the ones we 
                # are not interested in
                x = []
                for spike in self.spikeDict:
                    _include = \
                        (sweepNumber == "All" or spike["sweep"] == sweepNumber) \
                            and (epochNumber == "All" or spike["epoch"] == epochNumber)
                    if _include:
                        x.append(clean(spike[statName1]))
                    else:
                        x.append(float("nan"))
            
            else:
                # only current sweep and epoch
                # (1) was this
                # was causing errors with kym diam analysis
                x = [
                    clean(spike[statName1])
                    for spike in self.spikeDict
                    if (sweepNumber == "All" or spike["sweep"] == sweepNumber)
                    and (epochNumber == "All" or spike["epoch"] == epochNumber)
                ]
                # for _idx, spike in enumerate(self.spikeDict):
                #     if (sweepNumber == "All" or spike["sweep"] == sweepNumber) and (epochNumber == "All" or spike["epoch"] == epochNumber):
                #         try:
                #             val = spike[statName1]
                #         except (KeyError) as e:
                #             logger.error(f'did not find key "{statName1}" at spike {_idx}')
                #         clean(val)

            if statName2 is not None:
                # original
                # y = [clean(spike[statName2]) for spike in self.spikeDict]
                # only current spweek
                y = [
                    clean(spike[statName2])
                    for spike in self.spikeDict
                    if sweepNumber == "All" or spike["sweep"] == sweepNumber
                ]

        if asArray:
            x = np.array(x)
            if statName2 is not None:
                y = np.array(y)

        if statName2 is not None:
            return x, y
        else:
            return x

    def getSpikeTimes(self, sweepNumber=None, epochNumber='All'):
        """Get spike times (points) for current sweep"""
        # theRet = [spike['thresholdPnt'] for spike in self.spikeDict if spike['sweep']==self.currentSweep]
        theRet = self.getStat("thresholdPnt", sweepNumber=sweepNumber, epochNumber=epochNumber)
        return theRet

    def getSpikeSeconds(self, sweepNumber=None):
        """Get spike times (seconds) for current sweep"""
        # theRet = [spike['thresholdSec'] for spike in self.spikeDict if spike['sweep']==self.currentSweep]
        theRet = self.getStat("thresholdSec", sweepNumber=sweepNumber)
        return theRet

    def getSpikeDictionaries(self, sweepNumber=None):
        """Get spike dictionaries for current sweep
        """
        if sweepNumber is None:
            sweepNumber = "All"
        # logger.info(f'sweepNumber:{sweepNumber}')
        theRet = [
            spike
            for spike in self.spikeDict
            if sweepNumber == "All" or spike["sweep"] == sweepNumber
        ]
        return theRet

    def getOneSpikeDict(self, spikeNumber: int):
        return self.spikeDict[spikeNumber]

    def _rebuildFiltered(self):
        if self.fileLoader.sweepX is None:
            # no data
            logger.warning("not getting derivative ... sweepX was none?")
            return

        if (
            self.fileLoader.recordingMode == recordingModes.iclamp
            or self.fileLoader.recordingMode == recordingModes.kymograph
        ):
            self.fileLoader._getDerivative()
        elif self.fileLoader.recordingMode == recordingModes.vclamp:
            self.fileLoader._getDerivative()
        else:
            logger.warning(
                f'Did not take derivative, unknown recording mode "{self.fileLoader.recordingMode}"'
            )

    def _getFilteredRecording(self):
        """
        Get a filtered version of recording, used for both V-Clamp and I-Clamp.

        Args:
            dDict (dict): Default detection dictionary. See bDetection.defaultDetection
        """

        if self._detectionDict is not None:
            medianFilter = self._detectionDict["medianFilter"]
            SavitzkyGolay_pnts = self._detectionDict["SavitzkyGolay_pnts"]
            SavitzkyGolay_poly = self._detectionDict["SavitzkyGolay_poly"]
        else:
            # we have not been analyzed, impose some defaults
            medianFilter = 0  # no median filter
            SavitzkyGolay_pnts = 5
            SavitzkyGolay_poly = 2

        self.fileLoader._getDerivative(
            medianFilter, SavitzkyGolay_pnts, SavitzkyGolay_poly
        )

        # if medianFilter > 0:
        #     if not medianFilter % 2:
        #         medianFilter += 1
        #         logger.warning(f'Please use an odd value for the median filter, set medianFilter: {medianFilter}')
        #     medianFilter = int(medianFilter)
        #     self._filteredVm = scipy.signal.medfilt2d(self.sweepY(), [medianFilter,1])
        # elif SavitzkyGolay_pnts > 0:
        #     self._filteredVm = scipy.signal.savgol_filter(self.sweepY(),
        #                         SavitzkyGolay_pnts, SavitzkyGolay_poly,
        #                         mode='nearest', axis=0)
        # else:
        #     self._filteredVm = self.sweepY

    def _backupSpikeVm(self, spikeTimes, sweepNumber, medianFilter=None):
        """
        Backup spike time using deminishing SD and diff b/w vm at pnt[i]-pnt[i-1]
        Used when detecting with just mV threshold (not dv/dt)

        Args:
            spikeTimes (list of float):
            medianFilter (int): bin width
        """
        # realSpikeTimePnts = [np.nan] * self.numSpikes
        realSpikeTimePnts = [np.nan] * len(spikeTimes)

        medianFilter = 5
        sweepY = self.fileLoader.sweepY
        if medianFilter > 0:
            myVm = scipy.signal.medfilt(sweepY, medianFilter)
        else:
            myVm = sweepY

        #
        # TODO: this is going to fail if spike is at start/stop of recorrding
        #

        maxNumPntsToBackup = 20  # todo: add _ms
        bin_ms = 1
        bin_pnts = round(bin_ms * self.fileLoader.dataPointsPerMs)
        half_bin_pnts = math.floor(bin_pnts / 2)
        for idx, spikeTimePnts in enumerate(spikeTimes):
            foundRealThresh = False
            thisMean = None
            thisSD = None
            backupNumPnts = 0
            atBinPnt = spikeTimePnts
            while not foundRealThresh:
                thisWin = myVm[atBinPnt - half_bin_pnts : atBinPnt + half_bin_pnts]
                if thisMean is None:
                    thisMean = np.mean(thisWin)
                    thisSD = np.std(thisWin)

                nextStart = atBinPnt - 1 - bin_pnts - half_bin_pnts
                nextStop = atBinPnt - 1 - bin_pnts + half_bin_pnts
                nextWin = myVm[nextStart:nextStop]
                nextMean = np.mean(nextWin)
                nextSD = np.std(nextWin)

                meanDiff = thisMean - nextMean
                # logic
                sdMult = 0.7  # 2
                if (meanDiff < nextSD * sdMult) or (
                    backupNumPnts == maxNumPntsToBackup
                ):
                    # second clause will force us to terminate (this recording has a very slow rise time)
                    # bingo!
                    foundRealThresh = True
                    # not this xxx but the previous
                    moveForwardPnts = 4
                    backupNumPnts = backupNumPnts - 1  # the prev is thresh
                    if backupNumPnts < moveForwardPnts:
                        logger.warning(
                            f"spike {idx} backupNumPnts:{backupNumPnts} < moveForwardPnts:{moveForwardPnts}"
                        )
                        # print('  -->> not adjusting spike time')
                        realBackupPnts = backupNumPnts - 0
                        realPnt = spikeTimePnts - (realBackupPnts * bin_pnts)

                    else:
                        realBackupPnts = backupNumPnts - moveForwardPnts
                        realPnt = spikeTimePnts - (realBackupPnts * bin_pnts)
                    #
                    realSpikeTimePnts[idx] = realPnt

                # increment
                thisMean = nextMean
                thisSD = nextSD

                atBinPnt -= bin_pnts
                backupNumPnts += 1
                """
                if backupNumPnts>maxNumPntsToBackup:
                    print(f'  WARNING: _backupSpikeVm() exiting spike {idx} ... reached maxNumPntsToBackup:{maxNumPntsToBackup}')
                    print('  -->> not adjusting spike time')
                    foundRealThresh = True # set this so we exit the loop
                    realSpikeTimePnts[idx] = spikeTimePnts
                """

        #
        return realSpikeTimePnts

    def _throwOutRefractory(self, spikeTimes0, goodSpikeErrors, refractory_ms=20):
        """
        spikeTimes0: spike times to consider
        goodSpikeErrors: list of errors per spike, can be None
        refractory_ms:
        """
        before = len(spikeTimes0)

        # if there are doubles, throw-out the second one
        # refractory_ms = 20 #10 # remove spike [i] if it occurs within refractory_ms of spike [i-1]
        lastGood = 0  # first spike [0] will always be good, there is no spike [i-1]
        for i in range(len(spikeTimes0)):
            if i == 0:
                # first spike is always good
                continue
            dPoints = spikeTimes0[i] - spikeTimes0[lastGood]
            if dPoints < self.fileLoader.dataPointsPerMs * refractory_ms:
                # remove spike time [i]
                spikeTimes0[i] = 0
            else:
                # spike time [i] was good
                lastGood = i
        # regenerate spikeTimes0 by throwing out any spike time that does not pass 'if spikeTime'
        # spikeTimes[i] that were set to 0 above (they were too close to the previous spike)
        # will not pass 'if spikeTime', as 'if 0' evaluates to False
        if goodSpikeErrors is not None:
            goodSpikeErrors = [
                goodSpikeErrors[idx]
                for idx, spikeTime in enumerate(spikeTimes0)
                if spikeTime
            ]
        spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if spikeTime]

        # TODO: put back in and log if detection ['verbose']
        after = len(spikeTimes0)
        if self._detectionDict["verbose"]:
            logger.info(
                f"From {before} to {after} spikes with refractory_ms:{refractory_ms}"
            )

        return spikeTimes0, goodSpikeErrors

    def _getHalfWidth(
        self,
        vm,
        iIdx,
        spikeDict,
        thresholdPnt,
        peakPnt,
        hwWindowPnts,
        dataPointsPerMs,
        halfHeightList,
        verbose=False,
    ):
        """
        Get half-widhts for one spike.

        Note: Want to make this standalone function outside of class but we need self._getErrorDict()

        Args:
            vm ():
            iIdx (int):
            spikeDict (): new 20210928
            #dictNumber (int):
            thresholdPnt (int): AP threshold crossing
            peakPnt (int): AP peak
            hwWindowPnts (int): Window to look after peakPnt for falling vm
            dataPointsPerMs (int):
            halfHeightList (list): List of half-height [10,20,50,80,90]
        """

        halfWidthWindow_ms = hwWindowPnts / dataPointsPerMs

        thresholdVal = vm[thresholdPnt]
        peakVal = vm[peakPnt]
        spikeHeight = peakVal - thresholdVal

        spikeSecond = thresholdPnt / dataPointsPerMs / 1000
        peakSec = peakPnt / dataPointsPerMs / 1000

        widthDictList = []
        errorList = []

        # clear out any existing list
        spikeDict[iIdx]["widths"] = []

        tmpErrorType = None
        for j, halfHeight in enumerate(halfHeightList):
            # halfHeight in [20, 50, 80]

            # search rising/falling phae of vm for this vm
            thisVm = thresholdVal + spikeHeight * (halfHeight * 0.01)

            # todo: logic is broken, this get over-written in following try
            widthDict = {
                "halfHeight": halfHeight,
                "risingPnt": None,
                #'risingVal': defaultVal,
                "fallingPnt": None,
                #'fallingVal': defaultVal,
                "widthPnts": None,
                "widthMs": float("nan"),
            }
            widthMs = float("nan")
            try:
                postRange = vm[peakPnt : peakPnt + hwWindowPnts]
                fallingPnt = np.where(postRange < thisVm)[0]  # less than
                if len(fallingPnt) == 0:
                    # no falling pnts found within hwWindowPnts
                    tmpErrorType = "falling point"
                    raise IndexError
                fallingPnt = fallingPnt[0]  # first falling point
                fallingPnt += peakPnt
                fallingVal = vm[fallingPnt]

                # use the post/falling to find pre/rising
                preRange = vm[thresholdPnt:peakPnt]
                risingPnt = np.where(preRange > fallingVal)[0]  # greater than
                if len(risingPnt) == 0:
                    tmpErrorType = "rising point"
                    raise IndexError
                risingPnt = risingPnt[0]  # first rising point
                risingPnt += thresholdPnt
                # risingVal = vm[risingPnt]

                # width (pnts)
                widthPnts = fallingPnt - risingPnt
                widthMs = widthPnts / dataPointsPerMs
                # 20210825 may want to add this to analysis
                # widthPnts2 = fallingPnt - thresholdPnt
                # assign
                widthDict["halfHeight"] = halfHeight
                widthDict["risingPnt"] = risingPnt
                # widthDict['risingVal'] = risingVal
                widthDict["fallingPnt"] = fallingPnt
                # widthDict['fallingVal'] = fallingVal
                widthDict["widthPnts"] = widthPnts
                widthDict["widthMs"] = widthMs
                # widthMs = widthPnts / dataPointsPerMs # abb 20210125

                # may want to add this
                # widthDict['widthPnts2'] = widthPnts2
                # widthDict['widthMs2'] = widthPnts2 / dataPointsPerMs

            except IndexError as e:
                errorType = "Spike Width"
                errorStr = (
                    f'Half width {halfHeight} error in "{tmpErrorType}" '
                    f"with halfWidthWindow_ms:{halfWidthWindow_ms} "
                    f"searching for Vm:{round(thisVm,2)} from peak sec {round(peakSec,2)}"
                )

                # was this
                # eDict = self._getErrorDict(spikeNumber, thresholdPnt, errorType, errorStr) # spikeTime is in pnts
                eDict = self._getErrorDict(
                    iIdx, thresholdPnt, errorType, errorStr
                )  # spikeTime is in pnts
                # self.spikeDict[dictNumber]['errors'].append(eDict)
                spikeDict[iIdx]["errors"].append(eDict)
                if verbose:
                    print(
                        f"_getHalfWidth() error iIdx:{iIdx} j:{j} halfHeight:{halfHeight} eDict:{eDict}"
                    )
            #
            # self.spikeDict[dictNumber]['widths_'+str(halfHeight)] = widthMs
            # self.spikeDict[dictNumber]['widths'][j] = widthDict

            # logger.info('================')
            # print(f'len(spikeDict):{len(spikeDict)} iIdx:{iIdx} j:{j} widthDict:{widthDict}')

            spikeDict[iIdx]["widths_" + str(halfHeight)] = widthMs
            # spikeDict[iIdx]['widths'][j] = widthDict
            spikeDict[iIdx]["widths"].append(widthDict)

        #
        # return widthDictList, errorList

    def _getErrorDict(self, spikeNumber, pnt, _type : str, detailStr) -> dict:
        """Get error dict for one spike
        
        Notes
        -----
        Can't use self.getSpikeStat() because it is not created yet.
            We are in the middle of analysis
        """
        sec = self.fileLoader.pnt2Sec_(pnt)  # pnt / self.dataPointsPerMs / 1000
        sec = round(sec, 4)

        # print(f'  spikeNumber: {spikeNumber} {type(spikeNumber)}')
        # print('    sweep:', self.getSpikeStat([spikeNumber], 'sweep'))

        eDict = {
            "Spike": spikeNumber,
            "Seconds": sec,
            "Sweep": '',  # self.getSpikeStat([spikeNumber], 'sweep')[0],
            "Epoch": '',  # self.getSpikeStat([spikeNumber], 'epoch')[0],
            "Type": _type,
            "Details": detailStr,
        }
        return eDict

    def _spikeDetect_dvdt(self, dDict: dict, sweepNumber: int, verbose: bool = False):
        """
        Search for threshold crossings (dvdtThreshold) in first derivative (dV/dt) of membrane potential (Vm)
        append each threshold crossing (e.g. a spike) in self.spikeTimes list

        Returns:
            self.spikeTimes (pnts): the time before each threshold crossing when dv/dt crosses 15% of its max
            self.filteredVm:
            self.filtereddVdt:
        """

        #
        # analyze full recording
        filteredDeriv = self.fileLoader.filteredDeriv
        Is = np.where(filteredDeriv > dDict["dvdtThreshold"])[0]
        Is = np.concatenate(([0], Is))
        Ds = Is[:-1] - Is[1:] + 1
        spikeTimes0 = Is[np.where(Ds)[0] + 1]

        #
        # reduce spike times based on start/stop
        # logger.error('THIS IS a BUg if start sec is none then set to 0 !!!')
        # THIS IS ABUG ... FIX
        if dDict["startSeconds"] is not None and dDict["stopSeconds"] is not None:
            startPnt = self.fileLoader.dataPointsPerMs * (
                dDict["startSeconds"] * 1000
            )  # seconds to pnt
            stopPnt = self.fileLoader.dataPointsPerMs * (
                dDict["stopSeconds"] * 1000
            )  # seconds to pnt
            tmpSpikeTimes = [
                spikeTime
                for spikeTime in spikeTimes0
                if (spikeTime >= startPnt and spikeTime <= stopPnt)
            ]
            spikeTimes0 = tmpSpikeTimes

        #
        # throw out all spikes that are below a threshold Vm (usually below -20 mV)
        peakWindow_pnts = self.fileLoader.ms2Pnt_(dDict["peakWindow_ms"])
        # peakWindow_pnts = self.dataPointsPerMs * dDict['peakWindow_ms']
        # peakWindow_pnts = round(peakWindow_pnts)
        goodSpikeTimes = []
        sweepY = self.fileLoader.sweepY
        for spikeTime in spikeTimes0:
            peakVal = np.max(sweepY[spikeTime : spikeTime + peakWindow_pnts])
            if peakVal > dDict["mvThreshold"]:
                goodSpikeTimes.append(spikeTime)
        spikeTimes0 = goodSpikeTimes

        #
        # throw out spike that are not upward deflections of Vm
        """
        prePntUp = 7 # pnts
        goodSpikeTimes = []
        for spikeTime in spikeTimes0:
            preAvg = np.average(self.abf.sweepY[spikeTime-prePntUp:spikeTime-1])
            postAvg = np.average(self.abf.sweepY[spikeTime+1:spikeTime+prePntUp])
            #print(preAvg, postAvg)
            if preAvg < postAvg:
                goodSpikeTimes.append(spikeTime)
        spikeTimes0 = goodSpikeTimes
        """

        #
        # if there are doubles, throw-out the second one
        spikeTimeErrors = None
        spikeTimes0, ignoreSpikeErrors = self._throwOutRefractory(
            spikeTimes0, spikeTimeErrors, refractory_ms=dDict["refractory_ms"]
        )

        # logger.warning('REMOVED SPIKE TOP AS % OF DVDT')
        # return spikeTimes0, [None] * len(spikeTimes0)

        #
        # for each threshold crossing, search backwards in dV/dt for a % of maximum (about 10 ms)
        # dvdt_percentOfMax = 0.1
        # window_ms = 2
        window_pnts = dDict["dvdtPreWindow_ms"] * self.fileLoader.dataPointsPerMs
        # abb 20210130 lcr analysis
        window_pnts = round(window_pnts)
        spikeTimes1 = []
        spikeErrorList1 = []
        filteredDeriv = self.fileLoader.filteredDeriv
        for i, spikeTime in enumerate(spikeTimes0):
            # get max in derivative

            preDerivClip = filteredDeriv[
                spikeTime - window_pnts : spikeTime
            ]  # backwards
            postDerivClip = filteredDeriv[
                spikeTime : spikeTime + window_pnts
            ]  # forwards

            if len(preDerivClip) == 0:
                print(
                    "FIX ERROR: spikeDetect_dvdt()",
                    "spike",
                    i,
                    "at pnt",
                    spikeTime,
                    "window_pnts:",
                    window_pnts,
                    "dvdtPreWindow_ms:",
                    dDict["dvdtPreWindow_ms"],
                    "len(preDerivClip)",
                    len(preDerivClip),
                )  # preDerivClip = np.flip(preDerivClip)

            # look for % of max in dvdt
            try:
                # peakPnt = np.argmax(preDerivClip)
                peakPnt = np.argmax(postDerivClip)
                # peakPnt += spikeTime-window_pnts
                peakPnt += spikeTime
                peakVal = filteredDeriv[peakPnt]

                percentMaxVal = (
                    peakVal * dDict["dvdt_percentOfMax"]
                )  # value we are looking for in dv/dt
                preDerivClip = np.flip(preDerivClip)  # backwards
                tmpWhere = np.where(preDerivClip < percentMaxVal)
                # print('tmpWhere:', type(tmpWhere), tmpWhere)
                tmpWhere = tmpWhere[0]
                if len(tmpWhere) > 0:
                    threshPnt2 = np.where(preDerivClip < percentMaxVal)[0][0]
                    threshPnt2 = (spikeTime) - threshPnt2
                    # print('i:', i, 'spikeTime:', spikeTime, 'peakPnt:', peakPnt, 'threshPnt2:', threshPnt2)
                    threshPnt2 -= 1  # backup by 1 pnt
                    spikeTimes1.append(threshPnt2)
                    spikeErrorList1.append(None)

                else:
                    errorType = "dvdt Percent"
                    errStr = f"Did not find dvdt_percentOfMax: {dDict['dvdt_percentOfMax']} peak dV/dt is {round(peakVal,2)}"
                    eDict = self._getErrorDict(
                        i, spikeTime, errorType, errStr
                    )  # spikeTime is in pnts
                    spikeErrorList1.append(eDict)
                    # always append, do not REJECT spike if we can't find % in dv/dt
                    spikeTimes1.append(spikeTime)
            except (IndexError, ValueError) as e:
                ##
                print(
                    "   FIX ERROR: bAnalysis.spikeDetect_dvdt() looking for dvdt_percentOfMax"
                )
                print("      ", "IndexError for spike", i, spikeTime)
                print("      ", e)
                # always append, do not REJECT spike if we can't find % in dv/dt
                spikeTimes1.append(spikeTime)

        return spikeTimes1, spikeErrorList1

    def _spikeDetect_vm(self, dDict: dict, sweepNumber: int, verbose: bool = False):
        """
        spike detect using Vm threshold and NOT dvdt
        append each threshold crossing (e.g. a spike) in self.spikeTimes list

        Returns:
            self.spikeTimes (pnts): the time before each threshold crossing when dv/dt crosses 15% of its max
            self.filteredVm:
            self.filtereddVdt:
        """

        filteredVm = self.fileLoader.sweepY_filtered
        Is = np.where(filteredVm > dDict["mvThreshold"])[0]  # returns boolean array
        Is = np.concatenate(([0], Is))
        Ds = Is[:-1] - Is[1:] + 1
        spikeTimes0 = Is[np.where(Ds)[0] + 1]

        #
        # reduce spike times based on start/stop
        if dDict["startSeconds"] is not None and dDict["stopSeconds"] is not None:
            startPnt = self.fileLoader.dataPointsPerMs * (
                dDict["startSeconds"] * 1000
            )  # seconds to pnt
            stopPnt = self.fileLoader.dataPointsPerMs * (
                dDict["stopSeconds"] * 1000
            )  # seconds to pnt
            tmpSpikeTimes = [
                spikeTime
                for spikeTime in spikeTimes0
                if (spikeTime >= startPnt and spikeTime <= stopPnt)
            ]
            spikeTimes0 = tmpSpikeTimes

        spikeErrorList = [None] * len(spikeTimes0)

        #
        # throw out all spikes that are below a threshold Vm (usually below -20 mV)
        # spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if self.abf.sweepY[spikeTime] > self.mvThreshold]
        # 20190623 - already done in this vm threshold funtion
        """
        peakWindow_ms = 10
        peakWindow_pnts = self.abf.dataPointsPerMs * peakWindow_ms
        goodSpikeTimes = []
        for spikeTime in spikeTimes0:
            peakVal = np.max(self.abf.sweepY[spikeTime:spikeTime+peakWindow_pnts])
            if peakVal > self.mvThreshold:
                goodSpikeTimes.append(spikeTime)
        spikeTimes0 = goodSpikeTimes
        """

        #
        # throw out spike that are NOT upward deflections of Vm
        tmpLastGoodSpike_pnts = None
        # minISI_pnts = 5000 # at 20 kHz this is 0.25 sec
        minISI_ms = 75  # 250
        minISI_pnts = self.fileLoader.ms2Pnt_(minISI_ms)

        prePntUp = 10  # pnts
        goodSpikeTimes = []
        goodSpikeErrors = []
        sweepY = self.fileLoader.sweepY
        for tmpIdx, spikeTime in enumerate(spikeTimes0):
            tmpFuckPreClip = sweepY[
                spikeTime - prePntUp : spikeTime
            ]  # not including the stop index
            tmpFuckPostClip = sweepY[
                spikeTime + 1 : spikeTime + prePntUp + 1
            ]  # not including the stop index
            preAvg = np.average(tmpFuckPreClip)
            postAvg = np.average(tmpFuckPostClip)
            if postAvg > preAvg:
                # tmpSpikeTimeSec = self.fileLoader.pnt2Sec_(spikeTime)
                if (
                    tmpLastGoodSpike_pnts is not None
                    and (spikeTime - tmpLastGoodSpike_pnts) < minISI_pnts
                ):
                    continue
                goodSpikeTimes.append(spikeTime)
                goodSpikeErrors.append(spikeErrorList[tmpIdx])
                tmpLastGoodSpike_pnts = spikeTime
            else:
                tmpSpikeTimeSec = self.fileLoader.pnt2Sec_(spikeTime)

        # todo: add this to spikeDetect_dvdt()
        goodSpikeTimes, goodSpikeErrors = self._throwOutRefractory(
            goodSpikeTimes, goodSpikeErrors, refractory_ms=dDict["refractory_ms"]
        )
        spikeTimes0 = goodSpikeTimes
        spikeErrorList = goodSpikeErrors

        #
        return spikeTimes0, spikeErrorList

    def spikeDetect(self, detectionDict: dict):
        """Run spike detection for all sweeps.

        Each spike is a row and has 'sweep'

        Args:
            detectionDict: From sanpy.bDetection
        """

        rememberSweep = (
            self.fileLoader.currentSweep
        )  # This is BAD we are mixing analysis with interface !!!

        startTime = time.time()

        #
        # todo: ask user if they want to remove their settings for (isBad, userType)
        #

        self._detectionDict = detectionDict

        if detectionDict["verbose"]:
            logger.info("=== detectionDict is:")
            for k in detectionDict.keys():
                v = detectionDict[k]
                print(f'  {k} value:"{v}" is type {type(v)}')

        self._isAnalyzed = True

        self.spikeDict = sanpy.bAnalysisResults.analysisResultList()
        # we are filling this in, one dict for each spike
        # self.spikeDict = [] # we are filling this in, one dict for each spike

        # self._spikesPerSweep = [0] * self.fileLoader.numSweeps

        for sweepNumber in self.fileLoader.sweepList:
            # self.setSweep(sweep)
            self._spikeDetect2(sweepNumber)

        #
        self.fileLoader.setSweep(rememberSweep)

        stopTime = time.time()

        if detectionDict["verbose"]:
            logger.info(
                f"Detected {len(self.spikeDict)} spikes in {round(stopTime-startTime,3)} seconds"
            )

    def _spikeDetect2(self, sweepNumber: int):
        """Detect all spikes in one sweep.

         Populate bAnalysisResult.py.

        Notes
        -----
        First spike in a sweep cannot have interval statistics like freq or isi

        Parameters
        ----------
        sweepNumber : int
        """
        dDict = self._detectionDict

        # a list of dict of sanpy.bAnalysisResults.analysisResult (one dict per spike)
        spikeDict = sanpy.bAnalysisResults.analysisResultList()

        verbose = dDict["verbose"]

        #
        self.fileLoader.setSweep(sweepNumber)
        #

        # in case dDict has new filter values
        self._getFilteredRecording()

        #
        # spike detect
        detectionType = dDict["detectionType"]

        # detect all spikes either with dvdt or mv
        if detectionType == sanpy.bDetection.detectionTypes["mv"].value:
            # detect using mV threshold
            spikeTimes, spikeErrorList = self._spikeDetect_vm(dDict, sweepNumber)

            # TODO: get rid of this and replace with foot
            # backup childish vm threshold
            if dDict["doBackupSpikeVm"]:
                spikeTimes = self._backupSpikeVm(
                    spikeTimes, sweepNumber, dDict["medianFilter"]
                )
        elif detectionType == sanpy.bDetection.detectionTypes["dvdt"].value:
            # detect using dv/dt threshold AND min mV
            spikeTimes, spikeErrorList = self._spikeDetect_dvdt(dDict, sweepNumber)
        else:
            logger.error(f'Unknown detection type "{detectionType}"')
            return

        #
        # backup thrshold to zero crossing in dvdt
        if 0:
            tmp_window_ms = dDict["dvdtPreWindow_ms"]
            tmp_window_pnts = self.fileLoader.ms2Pnt_(tmp_window_ms)
            spikeTimes = self._getFeet(spikeTimes, tmp_window_pnts)

        #
        # set up
        sweepX = self.fileLoader.sweepX  # sweepNumber is not optional
        filteredVm = self.fileLoader.sweepY_filtered  # sweepNumber is not optional
        filteredDeriv = self.fileLoader.filteredDeriv
        sweepC = self.fileLoader.sweepC

        #
        now = datetime.datetime.now()
        dateStr = now.strftime("%Y%m%d")
        timeStr = now.strftime("%H:%M:%S")
        self.dateAnalyzed = dateStr

        #
        # look in a window after each threshold crossing to get AP peak
        peakWindow_pnts = self.fileLoader.ms2Pnt_(dDict["peakWindow_ms"])

        #
        # throw out spikes that have peak BELOW onlyPeaksAbove_mV
        # throw out spikes that have peak ABOVE onlyPeaksBelow_mV
        onlyPeaksAbove_mV = dDict["onlyPeaksAbove_mV"]
        onlyPeaksBelow_mV = dDict["onlyPeaksBelow_mV"]
        (
            spikeTimes,
            spikeErrorList,
            newSpikePeakPnt,
            newSpikePeakVal,
        ) = sanpy.analysisUtil.throwOutAboveBelow(
            filteredVm,
            spikeTimes,
            spikeErrorList,
            peakWindow_pnts,
            onlyPeaksAbove_mV=onlyPeaksAbove_mV,
            onlyPeaksBelow_mV=onlyPeaksBelow_mV,
        )

        #
        # small window to average Vm to calculate MDP (itself in a window before spike)
        avgWindow_pnts = self.fileLoader.ms2Pnt_(dDict["avgWindow_ms"])
        avgWindow_pnts = math.floor(avgWindow_pnts / 2)

        #
        # for each spike
        # numSpikes = len(spikeTimes)
        for i, spikeTime in enumerate(spikeTimes):
            # spikeTime units is ALWAYS points

            # new, add a spike dict for this spike time
            spikeDict.appendDefault()

            # get the AP peak
            peakPnt = newSpikePeakPnt[i]
            peakVal = newSpikePeakVal[i]
            peakSec = (newSpikePeakPnt[i] / self.fileLoader.dataPointsPerMs) / 1000

            # create one spike dictionary
            # spikeDict = OrderedDict() # use OrderedDict so Pandas output is in the correct order

            # spikeDict[i]['isBad'] = False
            spikeDict[i]["analysisDate"] = dateStr
            spikeDict[i]["analysisTime"] = timeStr
            spikeDict[i]["analysisVersion"] = sanpy.analysisVersion
            spikeDict[i]["interfaceVersion"] = sanpy.interfaceVersion
            spikeDict[i]["file"] = self.fileLoader.filename

            spikeDict[i]["detectionType"] = detectionType

            spikeDict[i]["cellType"] = dDict["cellType"]
            spikeDict[i]["sex"] = dDict["sex"]
            spikeDict[i]["condition"] = dDict["condition"]

            spikeDict[i]["sweep"] = sweepNumber

            epoch = float("nan")
            epochLevel = float("nan")
            epochTable = self.fileLoader.getEpochTable(sweepNumber)
            if epochTable is not None:
                epoch = epochTable.findEpoch(spikeTime)
                epochLevel = epochTable.getLevel(epoch)
            spikeDict[i]["epoch"] = epoch
            spikeDict[i]["epochLevel"] = epochLevel

            # keep track of per sweep spike and total spike
            spikeDict[i]["sweepSpikeNumber"] = i
            spikeDict[i]["spikeNumber"] = self.numSpikes + i

            spikeDict[i]["include"] = True

            # todo: make this a byte encoding so we can have multiple user tyes per spike
            spikeDict[i]["userType"] = 0  # One userType (int) that can have values

            # using bAnalysisResults will already be []
            spikeDict[i]["errors"] = []

            # append existing spikeErrorList from spikeDetect_dvdt() or spikeDetect_mv()
            tmpError = spikeErrorList[i]
            if tmpError is not None and tmpError != np.nan:
                spikeDict[i]["errors"].append(tmpError)  # tmpError is from:
                if verbose:
                    print(f"  spike:{i} error:{tmpError}")
            #
            # detection params
            spikeDict[i]["dvdtThreshold"] = dDict["dvdtThreshold"]
            spikeDict[i]["mvThreshold"] = dDict["mvThreshold"]
            spikeDict[i]["medianFilter"] = dDict["medianFilter"]
            spikeDict[i]["halfHeights"] = dDict["halfHeights"]

            spikeDict[i]["thresholdPnt"] = spikeTime
            spikeDict[i]["thresholdSec"] = (
                spikeTime / self.fileLoader.dataPointsPerMs
            ) / 1000
            spikeDict[i]["thresholdVal"] = filteredVm[spikeTime]  # in vm
            spikeDict[i]["thresholdVal_dvdt"] = filteredDeriv[
                spikeTime
            ]  # in dvdt, spikeTime is points

            # TODO: revamp this for 'Plot FI' plugin
            # spikeTime falls into wrong epoch for first fast spike
            # DAC command at the precise spike point
            # spikeDict[i]['dacCommand'] = sweepC[spikeTime]  # spikeTime is in points
            # spikeDict[i]['dacCommand'] = sweepC[peakPnt]  # spikeTime is in points

            spikeDict[i]["peakPnt"] = peakPnt
            spikeDict[i]["peakSec"] = peakSec
            spikeDict[i]["peakVal"] = peakVal

            spikeDict[i]["peakHeight"] = (
                spikeDict[i]["peakVal"] - spikeDict[i]["thresholdVal"]
            )

            tmpThresholdSec = spikeDict[i]["thresholdSec"]
            spikeDict[i]["timeToPeak_ms"] = (peakSec - tmpThresholdSec) * 1000

            # only append to spikeDict after we are done (accounting for spikes within a sweep)
            # self.spikeDict.append(spikeDict)
            # iIdx = len(self.spikeDict) - 1

            iIdx = i

            # todo: get rid of this
            defaultVal = float("nan")

            """
            # get pre/post spike minima
            self.spikeDict[iIdx]['preMinPnt'] = None
            self.spikeDict[iIdx]['preMinVal'] = defaultVal

            # early diastolic duration
            # 0.1 to 0.5 of time between pre spike min and spike time
            self.spikeDict[iIdx]['preLinearFitPnt0'] = None
            self.spikeDict[iIdx]['preLinearFitPnt1'] = None
            self.spikeDict[iIdx]['earlyDiastolicDuration_ms'] = defaultVal # seconds between preLinearFitPnt0 and preLinearFitPnt1
            self.spikeDict[iIdx]['preLinearFitVal0'] = defaultVal
            self.spikeDict[iIdx]['preLinearFitVal1'] = defaultVal
            # m,b = np.polyfit(x, y, 1)
            self.spikeDict[iIdx]['earlyDiastolicDurationRate'] = defaultVal # fit of y=preLinearFitVal 0/1 versus x=preLinearFitPnt 0/1
            self.spikeDict[iIdx]['lateDiastolicDuration'] = defaultVal #

            self.spikeDict[iIdx]['preSpike_dvdt_max_pnt'] = None
            self.spikeDict[iIdx]['preSpike_dvdt_max_val'] = defaultVal # in units mV
            self.spikeDict[iIdx]['preSpike_dvdt_max_val2'] = defaultVal # in units dv/dt
            self.spikeDict[iIdx]['postSpike_dvdt_min_pnt'] = None
            self.spikeDict[iIdx]['postSpike_dvdt_min_val'] = defaultVal # in units mV
            self.spikeDict[iIdx]['postSpike_dvdt_min_val2'] = defaultVal # in units dv/dt

            self.spikeDict[iIdx]['isi_pnts'] = defaultVal # time between successive AP thresholds (thresholdSec)
            self.spikeDict[iIdx]['isi_ms'] = defaultVal # time between successive AP thresholds (thresholdSec)
            self.spikeDict[iIdx]['spikeFreq_hz'] = defaultVal # time between successive AP thresholds (thresholdSec)
            self.spikeDict[iIdx]['cycleLength_pnts'] = defaultVal # time between successive MDPs
            self.spikeDict[iIdx]['cycleLength_ms'] = defaultVal # time between successive MDPs

            # Action potential duration (APD) was defined as the interval between the TOP and the subsequent MDP
            #self.spikeDict[iIdx]['apDuration_ms'] = defaultVal
            self.spikeDict[iIdx]['diastolicDuration_ms'] = defaultVal

            # any number of spike widths
            #print('spikeDetect__() appending widths list to spike iIdx:', iIdx)
            # was this
            #self.spikeDict[iIdx]['widths'] = []
            # debug 20210929, self._getHalfWidth() will assign spikeDict[iIdx]['widths'] = []
            for halfHeight in dDict['halfHeights']:
                widthDict = {
                    'halfHeight': halfHeight,
                    'risingPnt': None,
                    'risingVal': defaultVal,
                    'fallingPnt': None,
                    'fallingVal': defaultVal,
                    'widthPnts': None,
                    'widthMs': defaultVal
                }
                # was this
                #spikeDict[iIdx]['widths_' + str(halfHeight)] = defaultVal
                spikeDict[iIdx]['widths'].append(widthDict)
            """

            #
            mdp_ms = dDict["mdp_ms"]
            mdp_pnts = self.fileLoader.ms2Pnt_(mdp_ms)  # mdp_ms * self.dataPointsPerMs
            mdp_pnts = int(mdp_pnts)

            # pre spike min
            # other algorithms look between spike[i-1] and spike[i]
            # here we are looking in a predefined window
            startPnt = spikeTimes[i] - mdp_pnts
            if startPnt < 0:
                # logger.info('TODO: add an official warning, we went past 0 for pre spike mdp ms window')
                startPnt = 0
                # log error
                errorType = "Pre spike min under-run (mdp)"
                errorStr = "Went past time 0 searching for pre-spike min"
                eDict = self._getErrorDict(
                    i, spikeTimes[i], errorType, errorStr
                )  # spikeTime is in pnts
                spikeDict[iIdx]["errors"].append(eDict)
                if verbose:
                    print(f"  spike:{iIdx} error:{eDict}")

            preRange = filteredVm[startPnt : spikeTimes[i]]  # EXCEPTION
            try:
                preMinPnt = np.argmin(preRange)
            except ValueError as e:
                # 20220926, happend when we have no scale and mdp_pnts=0
                # print(f'xxx i:{i} mdp_pnts:{mdp_pnts} len:{len(filteredVm)} startPnt:{startPnt} spikeTimes[i]:{spikeTimes[i]}')
                # 20220926, we really just want ot bail on this error
                # lots of code below relies on this
                # TODO: fix this mess
                preMinPnt = startPnt
                errorType = "Pre spike min 0 (mdp)"
                errorStr = f"Did not find preMinPnt mdp_pnts:{mdp_pnts} startPnt:{startPnt} spikeTimes[i]:{spikeTimes[i]}"
                eDict = self._getErrorDict(
                    i, spikeTimes[i], errorType, errorStr
                )  # spikeTime is in pnts
                spikeDict[iIdx]["errors"].append(eDict)
                if verbose:
                    print(f"  spike:{iIdx} error:{eDict}")
            if preMinPnt is not None:
                preMinPnt += startPnt
                # the pre min is actually an average around the real minima
                avgRange = filteredVm[
                    preMinPnt - avgWindow_pnts : preMinPnt + avgWindow_pnts
                ]
                preMinVal = np.average(avgRange)

                # search backward from spike to find when vm reaches preMinVal (avg)
                preRange = filteredVm[preMinPnt : spikeTimes[i]]
                preRange = np.flip(preRange)  # we want to search backwards from peak
                try:
                    preMinPnt2 = np.where(preRange < preMinVal)[0][0]
                    preMinPnt = spikeTimes[i] - preMinPnt2
                    spikeDict[iIdx]["preMinPnt"] = preMinPnt
                    spikeDict[iIdx]["preMinVal"] = preMinVal

                except IndexError as e:
                    errorType = "Pre spike min (mdp)"
                    errorStr = "Did not find preMinVal: " + str(
                        round(preMinVal, 3)
                    )  # + ' postRange min:' + str(np.min(postRange)) + ' max ' + str(np.max(postRange))
                    eDict = self._getErrorDict(
                        i, spikeTimes[i], errorType, errorStr
                    )  # spikeTime is in pnts
                    spikeDict[iIdx]["errors"].append(eDict)
                    if verbose:
                        print(f"  spike:{iIdx} error:{eDict}")

            #
            # The nonlinear late diastolic depolarization phase was
            # estimated as the duration between 1% and 10% dV/dt
            # linear fit on 10% - 50% of the time from preMinPnt to self.spikeTimes[i]
            startLinearFit = 0.1  # percent of time between pre spike min and AP peak
            stopLinearFit = 0.5  #
            timeInterval_pnts = spikeTimes[i] - preMinPnt
            # taking round() so we always get an integer # points
            preLinearFitPnt0 = preMinPnt + round(timeInterval_pnts * startLinearFit)
            preLinearFitPnt1 = preMinPnt + round(timeInterval_pnts * stopLinearFit)
            preLinearFitVal0 = filteredVm[preLinearFitPnt0]
            preLinearFitVal1 = filteredVm[preLinearFitPnt1]

            # linear fit before spike
            spikeDict[iIdx]["preLinearFitPnt0"] = preLinearFitPnt0
            spikeDict[iIdx]["preLinearFitPnt1"] = preLinearFitPnt1
            spikeDict[iIdx]["earlyDiastolicDuration_ms"] = self.fileLoader.pnt2Ms_(
                preLinearFitPnt1 - preLinearFitPnt0
            )
            spikeDict[iIdx]["preLinearFitVal0"] = preLinearFitVal0
            spikeDict[iIdx]["preLinearFitVal1"] = preLinearFitVal1

            # a linear fit where 'm,b = np.polyfit(x, y, 1)'
            # m*x+b"
            xFit = sweepX[preLinearFitPnt0:preLinearFitPnt1]  # abb added +1
            yFit = filteredVm[preLinearFitPnt0:preLinearFitPnt1]

            # sometimes xFit/yFit have 0 length -->> TypeError
            # print(f' {iIdx} preLinearFitPnt0:{preLinearFitPnt0}, preLinearFitPnt1:{preLinearFitPnt1}')
            # print(f'    xFit:{len(xFit)} yFit:{len(yFit)}')

            # TODO: somehow trigger following errors to confirm code works (pytest)
            with warnings.catch_warnings():
                warnings.filterwarnings("error")
                try:
                    mLinear, bLinear = np.polyfit(
                        xFit, yFit, 1
                    )  # m is slope, b is intercept
                    spikeDict[iIdx]["earlyDiastolicDurationRate"] = mLinear
                    # todo: make an error if edd rate is too low
                    lowestEddRate = dDict["lowEddRate_warning"]  # 8
                    if mLinear <= lowestEddRate:
                        errorType = "Fit EDD"
                        errorStr = f"Early diastolic duration rate fit - Too low {round(mLinear,3)}<={lowestEddRate}"
                        eDict = self._getErrorDict(
                            i, spikeTimes[i], errorType, errorStr
                        )  # spikeTime is in pnts
                        # print('fit edd start num error:', 'iIdx:', iIdx, 'num error:', len(spikeDict[iIdx]['errors']))
                        spikeDict[iIdx]["errors"].append(eDict)
                        # print('  after num error:', len(spikeDict[iIdx]['errors']))
                        if verbose:
                            print(f"  spike:{iIdx} error:{eDict}")

                except (TypeError, RuntimeWarning) as e:
                    # catching exception:  expected non-empty vector for x
                    # xFit/yFit turn up empty when mdp and TOP points are within 1 point
                    spikeDict[iIdx]["earlyDiastolicDurationRate"] = defaultVal
                    errorType = "Fit EDD"
                    # errorStr = 'Early diastolic duration rate fit - TypeError'
                    errorStr = (
                        "Early diastolic duration rate fit - preMinPnt == spikePnt"
                    )
                    eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr)
                    spikeDict[iIdx]["errors"].append(eDict)
                    if verbose:
                        print(f"  spike:{iIdx} error:{eDict}")
                except np.RankWarning as e:
                    # logger.error('== FIX preLinearFitPnt0/preLinearFitPnt1 RankWarning')
                    # logger.error(f'  error is: {e}')
                    # print('RankWarning')
                    # also throws: RankWarning: Polyfit may be poorly conditioned
                    spikeDict[iIdx]["earlyDiastolicDurationRate"] = defaultVal
                    errorType = "Fit EDD"
                    errorStr = "Early diastolic duration rate fit - RankWarning"
                    eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr)
                    spikeDict[iIdx]["errors"].append(eDict)
                    if verbose:
                        print(f"  spike:{iIdx} error:{eDict}")
                # 20230422, don't ever catch an unknown exception
                # except:
                #     logger.error(
                #         f" !!!!!!!!!!!!!!!!!!!!!!!!!!! UNKNOWN EXCEPTION DURING EDD LINEAR FIT for spike {i}"
                #     )
                #     spikeDict[iIdx]["earlyDiastolicDurationRate"] = defaultVal
                #     errorType = "Fit EDD"
                #     errorStr = "Early diastolic duration rate fit - Unknown Exception"
                #     eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr)
                #     if verbose:
                #         print(f"  spike:{iIdx} error:{eDict}")

            # not implemented
            # self.spikeDict[i]['lateDiastolicDuration'] = ???

            #
            # maxima in dv/dt before spike (between TOP and peak)
            try:
                preRange = filteredDeriv[spikeTimes[i] : peakPnt + 1]
                preSpike_dvdt_max_pnt = np.argmax(preRange)
                preSpike_dvdt_max_pnt += spikeTimes[i]
                spikeDict[iIdx]["preSpike_dvdt_max_pnt"] = preSpike_dvdt_max_pnt
                spikeDict[iIdx]["preSpike_dvdt_max_val"] = filteredVm[
                    preSpike_dvdt_max_pnt
                ]  # in units mV
                spikeDict[iIdx]["preSpike_dvdt_max_val2"] = filteredDeriv[
                    preSpike_dvdt_max_pnt
                ]  # in units mV
            except ValueError as e:
                # sometimes preRange is empty, don't try and put min/max in error
                errorType = "Pre Spike dvdt"
                errorStr = "Searching for dvdt max - ValueError"
                eDict = self._getErrorDict(
                    i, spikeTimes[i], errorType, errorStr
                )  # spikeTime is in pnts
                spikeDict[iIdx]["errors"].append(eDict)
                if verbose:
                    print(f"  spike:{iIdx} error:{eDict}")

            #
            # minima in dv/dt after spike
            # postRange = dvdt[self.spikeTimes[i]:postMinPnt]
            # postSpike_ms = 20 # 10
            # postSpike_pnts = self.ms2Pnt_(postSpike_ms)
            dvdtPostWindow_ms = dDict["dvdtPostWindow_ms"]
            dvdtPostWindow_pnts = self.fileLoader.ms2Pnt_(dvdtPostWindow_ms)
            postRange = filteredDeriv[
                peakPnt : peakPnt + dvdtPostWindow_pnts
            ]  # fixed window after spike

            postSpike_dvdt_min_pnt = np.argmin(postRange)
            postSpike_dvdt_min_pnt += peakPnt
            spikeDict[iIdx]["postSpike_dvdt_min_pnt"] = postSpike_dvdt_min_pnt
            spikeDict[iIdx]["postSpike_dvdt_min_val"] = filteredVm[
                postSpike_dvdt_min_pnt
            ]
            spikeDict[iIdx]["postSpike_dvdt_min_val2"] = filteredDeriv[
                postSpike_dvdt_min_pnt
            ]

            #
            # diastolic duration was defined as the interval between MDP and TOP
            # one off error when preMinPnt is not defined
            spikeDict[iIdx]["diastolicDuration_ms"] = self.fileLoader.pnt2Ms_(
                spikeTime - preMinPnt
            )

            #
            # calculate instantaneous spike frequency and ISI, for first spike this is not defined
            spikeDict[iIdx]["cycleLength_ms"] = float("nan")
            if iIdx > 0:
                isiPnts = (
                    spikeDict[iIdx]["thresholdPnt"]
                    - spikeDict[iIdx - 1]["thresholdPnt"]
                )
                isi_ms = self.fileLoader.pnt2Ms_(isiPnts)
                isi_hz = 1 / (isi_ms / 1000)
                spikeDict[iIdx]["isi_pnts"] = isiPnts
                spikeDict[iIdx]["isi_ms"] = self.fileLoader.pnt2Ms_(isiPnts)
                spikeDict[iIdx]["spikeFreq_hz"] = 1 / (
                    self.fileLoader.pnt2Ms_(isiPnts) / 1000
                )

                # Cycle length was defined as the interval between MDPs in successive APs
                prevPreMinPnt = spikeDict[iIdx - 1]["preMinPnt"]  # can be nan
                thisPreMinPnt = spikeDict[iIdx]["preMinPnt"]
                if prevPreMinPnt is not None and thisPreMinPnt is not None:
                    cycleLength_pnts = thisPreMinPnt - prevPreMinPnt
                    spikeDict[iIdx]["cycleLength_pnts"] = cycleLength_pnts
                    spikeDict[iIdx]["cycleLength_ms"] = self.fileLoader.pnt2Ms_(
                        cycleLength_pnts
                    )
                else:
                    # error
                    prevPreMinSec = self.fileLoader.pnt2Sec_(prevPreMinPnt)
                    thisPreMinSec = self.fileLoader.pnt2Sec_(thisPreMinPnt)
                    # errorStr = f'Previous spike preMinPnt is {prevPreMinPnt} and this preMinPnt: {thisPreMinPnt}'
                    errorType = "Cycle Length"
                    errorStr = f"Previous spike preMinPnt (s) is {prevPreMinSec} and this preMinPnt: {thisPreMinSec}"
                    eDict = self._getErrorDict(
                        i, spikeTimes[i], errorType, errorStr
                    )  # spikeTime is in pnts
                    spikeDict[iIdx]["errors"].append(eDict)
                    if verbose:
                        print(f"  spike:{iIdx} error:{eDict}")

            #
            # TODO: Move half-width to a function !!!
            #
            hwWindowPnts = dDict["halfWidthWindow_ms"] * self.fileLoader.dataPointsPerMs
            hwWindowPnts = round(hwWindowPnts)
            halfHeightList = dDict["halfHeights"]
            # was this
            # self._getHalfWidth(filteredVm, i, iIdx, spikeTime, peakPnt, hwWindowPnts, self.dataPointsPerMs, halfHeightList)
            self._getHalfWidth(
                filteredVm,
                iIdx,
                spikeDict,
                spikeTime,
                peakPnt,
                hwWindowPnts,
                self.fileLoader.dataPointsPerMs,
                halfHeightList,
                verbose=verbose,
            )

        #
        # look between threshold crossing to get minima
        # we will ignore the first and last spike

        #
        # spike clips
        self.spikeClips = None
        self.spikeClips_x = None
        self.spikeClips_x2 = None

        # SUPER important, previously our self.spikeDict was simple list of dict
        # now it is a list of class xxx
        # print('=== addind', len(spikeDict))
        self.spikeDict.appendAnalysis(spikeDict)
        # print('   now have', len(self.spikeDict))
        # print(self.spikeDict)

        # keep track of spikes per sweep (expensive to calculate)
        # self._spikesPerSweep[sweepNumber] = len(spikeDict)

        # run all user analysis ... what if this fails ???
        sanpy.user_analysis.baseUserAnalysis.runAllUserAnalysis(self)

        #
        # generate a df holding stats (used by scatterplotwidget)
        # startSeconds = dDict['startSeconds']
        # stopSeconds = dDict['stopSeconds']
        # if self.numSpikes > 0:
        #     # exportObject = sanpy.bExport(self)
        #     # self.dfReportForScatter = exportObject.report(startSeconds, stopSeconds)
        #     self._dfReportForScatter = self.spikeDict.asDataFrame()
        # else:
        #     self.dfReportForScatter = None
        self.regenerateAnalysisDataFrame()

        # generate error report
        self.dfError = self.getErrorReport()

        # bAnalysis needs to be saved
        self._detectionDirty = True

        ## done

    def regenerateAnalysisDataFrame(self):
        if self.numSpikes > 0:
            # exportObject = sanpy.bExport(self)
            # self.dfReportForScatter = exportObject.report(startSeconds, stopSeconds)
            self._dfReportForScatter = self.spikeDict.asDataFrame()

            # get rid of analysis results columns, we get these from file metadata
            #  - include
            #  - cellType
            #  - sex
            #  - condition
            self._dfReportForScatter = self._dfReportForScatter.drop('include', axis=1)
            self._dfReportForScatter = self._dfReportForScatter.drop('cellType', axis=1)
            self._dfReportForScatter = self._dfReportForScatter.drop('sex', axis=1)
            self._dfReportForScatter = self._dfReportForScatter.drop('condition', axis=1)

            # add all file meta data to df
            for k,v in self.metaData.items():
                self._dfReportForScatter[k] = v

        else:
            self.dfReportForScatter = None

    def _getFeet(self, thresholdPnts: List[int], prePnts: int) -> List[int]:
        """

        Args:
            thresholdPnts (list of int)
            prePnts (int): pre point window to search for zero crossing

        Notes:
            Will need to calculate new (height, half widths)
        """

        # prePnts = int(prePnts)

        logger.info(f"num thresh:{len(thresholdPnts)} prePnts:{prePnts}")

        # df = self.asDataFrame()
        # peaks = df['peakVal']
        # thresholdPnts = df['thresholdPnt']

        verbose = self._detectionDict["verbose"]

        # using the derivstive to find zero crossing before
        # original full width left point
        # TODO: USer self.filteredDeriv
        # yFull = self.filteredVm
        # yDiffFull = np.diff(yFull)
        # yDiffFull = np.insert(yDiffFull, 0, np.nan)
        yDiffFull = self.fileLoader.filteredDeriv

        secondDeriv = np.diff(yDiffFull, axis=0)
        secondDeriv = np.insert(secondDeriv, 0, np.nan)

        n = len(thresholdPnts)
        footPntList = [None] * n
        footSec = [None] * n  # not used
        yFoot = [None] * n  # not used
        # myHeight = []

        # todo: add this to bAnalysis
        # preMs = self._detectionParams['preFootMs']
        # prePnts = self._sec2Pnt(preMs/1000)

        # TODO: add to bDetection
        logger.warning("ADD preMs AS PARAMETER !!!")
        # preWinMs = 50  # sa-node
        # prePnts = self.ms2Pnt_(preMs)

        for idx, footPnt in enumerate(thresholdPnts):
            # footPnt = round(footPnt)  # footPnt is in fractional points
            lastCrossingPnt = footPnt
            # move forwared a bit in case we are already in a local minima ???
            logger.warning("REMOVED WHEN WORKING ON NEURON DETECTION")
            footPnt += 2  # TODO: add as param
            preStart = footPnt - prePnts
            preClip = yDiffFull[preStart:footPnt]

            zero_crossings = np.where(np.diff(np.sign(preClip)))[
                0
            ]  # find where derivative flips sign (crosses 0)
            xLastCrossing = self.fileLoader.pnt2Sec_(footPnt)  # defaults
            yLastCrossing = self.fileLoader.sweepY_filtered[footPnt]
            if len(zero_crossings) == 0:
                if verbose:
                    tmpSec = round(self.fileLoader.pnt2Sec_(footPnt), 3)
                    logger.error(
                        f"  no foot for peak {idx} at sec {tmpSec} ... did not find zero crossings"
                    )
            else:
                # print(idx, 'footPnt:', footPnt, zero_crossings, preClip)
                lastCrossingPnt = preStart + zero_crossings[-1]
                xLastCrossing = self.fileLoader.pnt2Sec_(lastCrossingPnt)
                # get y-value (pA) from filtered. This removes 'pops' in raw data
                yLastCrossing = self.fileLoader.sweepY_filtered[lastCrossingPnt]

            # find peak in second derivative
            """
            preStart2 = lastCrossingPnt
            footMs2 = 20
            footPnt2 = preStart2 + self.ms2Pnt_(footMs2)
            preClip2 = secondDeriv[preStart2:footPnt2]
            #zero_crossings = np.where(np.diff(np.sign(preClip2)))[0]
            peakPnt2 = np.argmax(preClip2)
            peakPnt2 += preStart2

            #
            footPntList[idx] = peakPnt2
            """

            footPntList[idx] = lastCrossingPnt  # was this and worked, a bit too early

            footSec[idx] = xLastCrossing
            yFoot[idx] = yLastCrossing

            """
            peakPnt = df.loc[idx, 'peak_pnt']
            peakVal = self.sweepY_filtered[peakPnt]
            height = peakVal - yLastCrossing
            #print(f'idx {idx} {peakPnt} {peakVal} - {yLastCrossing} = {height}')
            myHeight[idx] = (height)
            """

        #
        # df =self._analysisList[self._analysisIdx]['results_full']
        """
        df['foot_pnt'] = footPntList  # sec
        df['foot_sec'] = footSec  # sec
        df['foot_val'] = yFoot  # pA
        """
        # df['myHeight'] = myHeight

        # return footPntList, footSec, yFoot
        return footPntList

    def printSpike(self, idx):
        """
        Print values in one spike analysis using self.spikeDict (sanpy.bAnalysisResults).
        """
        spike = self.spikeDict[idx]
        for k, v in spike.items():
            if k == "widths":
                widths = v
                print(f"  spike:{idx} has {len(widths)} widths...")
                for wIdx, width in enumerate(widths):
                    print(f"    spike:{idx} width:{wIdx}: {width}")
            elif k == "errors":
                errors = v
                print(f"  spike:{idx} has {len(errors)} errors...")
                for eIdx, error in enumerate(errors):
                    print(f"    spike:{idx} error #:{eIdx}: {error}")
            else:
                print(f"{k}: {v}")

    def printErrors(self):
        for idx, spike in enumerate(self.spikeDict):
            print(f"spike {idx} has {len(spike['errors'])} errors")
            for eIdx, error in enumerate(spike["errors"]):
                print(f"  error # {eIdx} is: {error}")

    def _makeSpikeClips(
        self,
        preSpikeClipWidth_ms,
        postSpikeClipWidth_ms=None,
        theseTime_sec=None,
        sweepNumber=None,
        epochNumber='All'
    ):
        """
        (Internal) Make small clips for each spike.

        Args:
            preSpikeClipWidth_ms (int): Width of each spike clip in milliseconds.
            postSpikeClipWidth_ms (int): Width of each spike clip in milliseconds.
            theseTime_sec (list of float): [NOT USED] List of seconds to make clips from.

        Returns:
            spikeClips_x2: ms
            self.spikeClips (list): List of spike clips
        """

        verbose = self._detectionDict["verbose"]

        if preSpikeClipWidth_ms is None:
            preSpikeClipWidth_ms = self._detectionDict["preSpikeClipWidth_ms"]
        if postSpikeClipWidth_ms is None:
            postSpikeClipWidth_ms = self._detectionDict["postSpikeClipWidth_ms"]

        if sweepNumber is None:
            sweepNumber = "All"

        # print('makeSpikeClips() spikeClipWidth_ms:', spikeClipWidth_ms, 'theseTime_sec:', theseTime_sec)
        if theseTime_sec is None:
            theseTime_pnts = self.getSpikeTimes(sweepNumber=sweepNumber, epochNumber=epochNumber)
        else:
            # convert theseTime_sec to pnts
            theseTime_ms = [x * 1000 for x in theseTime_sec]
            theseTime_pnts = [x * self.fileLoader.dataPointsPerMs for x in theseTime_ms]
            theseTime_pnts = [round(x) for x in theseTime_pnts]

        preClipWidth_pnts = self.fileLoader.ms2Pnt_(preSpikeClipWidth_ms)
        # if preClipWidth_pnts % 2 == 0:
        #    pass # Even
        # else:
        #    clipWidth_pnts += 1 # Make odd even
        postClipWidth_pnts = self.fileLoader.ms2Pnt_(postSpikeClipWidth_ms)

        # halfClipWidth_pnts = int(clipWidth_pnts/2)

        # print('  makeSpikeClips() clipWidth_pnts:', clipWidth_pnts, 'halfClipWidth_pnts:', halfClipWidth_pnts)
        # make one x axis clip with the threshold crossing at 0
        # was this, in ms
        # self.spikeClips_x = [(x-halfClipWidth_pnts)/self.dataPointsPerMs for x in range(clipWidth_pnts)]

        # in ms
        self.spikeClips_x = [
            (x - preClipWidth_pnts) / self.fileLoader.dataPointsPerMs
            for x in range(preClipWidth_pnts)
        ]
        self.spikeClips_x += [
            (x) / self.fileLoader.dataPointsPerMs for x in range(postClipWidth_pnts)
        ]

        # 20190714, added this to make all clips same length, much easier to plot in MultiLine
        numPointsInClip = len(self.spikeClips_x)

        self.spikeClips = []
        self.spikeClips_x2 = []

        sweepY = self.fileLoader.sweepY_filtered

        # when there are no spikes getStat() will not return anything
        # For 'All' sweeps, we need to know column
        sweepNum = self.getStat("sweep", sweepNumber=sweepNumber)

        # logger.info(f'sweepY: {sweepY.shape} {len(sweepY.shape)}')
        # logger.info(f'theseTime_pnts: {theseTime_pnts}')

        for idx, spikeTime in enumerate(theseTime_pnts):
            sweep = sweepNum[idx]

            if len(sweepY.shape) == 1:
                # 1D case where recording has only oone sweep
                # currentClip = sweepY[spikeTime-halfClipWidth_pnts:spikeTime+halfClipWidth_pnts]
                currentClip = sweepY[
                    spikeTime - preClipWidth_pnts : spikeTime + postClipWidth_pnts
                ]
            else:
                # 2D case where recording has multiple sweeps
                # currentClip = sweepY[spikeTime-halfClipWidth_pnts:spikeTime+halfClipWidth_pnts, sweep]
                try:
                    currentClip = sweepY[
                        spikeTime - preClipWidth_pnts : spikeTime + preClipWidth_pnts,
                        sweep,
                    ]
                except IndexError as e:
                    logger.error(e)
                    print(f"sweep: {sweep}")
                    print(f"sweepY.shape: {sweepY.shape}")

            if len(currentClip) == numPointsInClip:
                self.spikeClips.append(currentClip)
                self.spikeClips_x2.append(
                    self.spikeClips_x
                )  # a 2D version to make pyqtgraph multiline happy
            else:
                # pass
                if verbose:
                    logger.warning(
                        f"Did not add clip for spike index: {idx} at time: {spikeTime} len(currentClip): {len(currentClip)} != numPointsInClip: {numPointsInClip}"
                    )

        #
        return self.spikeClips_x2, self.spikeClips

    def getSpikeClips(
        self,
        theMin,
        theMax,
        spikeSelection=[],
        preSpikeClipWidth_ms=None,
        postSpikeClipWidth_ms=None,
        sweepNumber=None,
        epochNumber='All',
        ignoreMinMax=False  # added 20230418
    ):
        """Get 2d list of spike clips, spike clips x, and 1d mean spike clip.

        Args:
            theMin (float): Start seconds.
            theMax (float): Stop seconds.
            spikeSelection (list): List of spike numbers
            preSpikeClipWidth_ms (float):
            postSpikeClipWidth_ms (float):

        Requires: self.spikeDetect() and self._makeSpikeClips()

        Returns:
            theseClips (list): List of clip
            theseClips_x (list): ms
            meanClip (list)
        """

        if self.numSpikes == 0:
            return

        doSpikeSelection = len(spikeSelection) > 0

        if doSpikeSelection:
            pass
        elif theMin is None or theMax is None:
            theMin = 0
            theMax = self.fileLoader.recordingDur  # self.sweepX[-1]

        # new interface, spike detect no longer auto generates these
        # need to do this every time because we get here when sweepNumber changes
        # if self.spikeClips is None:
        #    self._makeSpikeClips(spikeClipWidth_ms=spikeClipWidth_ms, sweepNumber=sweepNumber)
        # TODO: don't make all clips
        # self._makeSpikeClips(spikeClipWidth_ms=spikeClipWidth_ms, sweepNumber=sweepNumber)
        self._makeSpikeClips(
            preSpikeClipWidth_ms=preSpikeClipWidth_ms,
            postSpikeClipWidth_ms=postSpikeClipWidth_ms,
            sweepNumber=sweepNumber,
            epochNumber=epochNumber
        )

        # make a list of clips within start/stop (Seconds)
        theseClips = []
        theseClips_x = []
        tmpMeanClips = []  # for mean clip
        meanClip = []
        
        # spikeTimes are in pnts
        spikeTimes = self.getSpikeTimes(sweepNumber=sweepNumber, epochNumber=epochNumber)

        logger.info(f'spikeTimes:{len(spikeTimes)} sweepNumber:{sweepNumber} epochNumber:{epochNumber}')

        # if len(spikeTimes) != len(self.spikeClips):
        #    logger.error(f'len spikeTimes {len(spikeTimes)} !=  spikeClips {len(self.spikeClips)}')

        # self.spikeClips is a list of clips
        for idx, clip in enumerate(self.spikeClips):
            doThisSpike = False
            if doSpikeSelection:
                doThisSpike = idx in spikeSelection
            else:
                spikeTime = spikeTimes[idx]
                spikeTime = self.fileLoader.pnt2Sec_(spikeTime)
                if ignoreMinMax or (spikeTime >= theMin and spikeTime <= theMax):
                    doThisSpike = True
            if doThisSpike:
                theseClips.append(clip)
                theseClips_x.append(
                    self.spikeClips_x2[idx]
                )  # remember, all _x are the same
                if len(self.spikeClips_x) == len(clip):
                    tmpMeanClips.append(clip)  # for mean clip
        if len(tmpMeanClips):
            meanClip = np.mean(tmpMeanClips, axis=0)

        return theseClips, theseClips_x, meanClip

    # def numErrors(self):
    #     if self.dfError is None:
    #         return "N/A"
    #     else:
    #         return len(self.dfError)

    def getErrorReport(self):
        """Generate an error report, one row per error.
        
        Spikes can have more than one error.

        Returns:
            (pandas DataFrame): Pandas DataFrame, one row per error.
        """

        dictList = []

        # numError = 0
        # errorList = []

        # logger.info(f'Generating error report for {len(self.spikeDict)} spikes')

        #  20230422 spikeDict is not working as an iterable
        # use it as a list instead
        numSpikes = len(self.spikeDict)
        #for spike in self.spikeDict:
        for _spikeNumber in range(numSpikes):
            spike = self.spikeDict[_spikeNumber]
            # spike is sanpy.bAnalysisResults.analysisResult
            #print('spike:', spike)
            for error in spike["errors"]:
                # spike["errors"] is a list of dict
                # error is dict from _getErrorDict
                if error is None or error == np.nan or error == "nan":
                    continue

                # 20230422 add sweep and epoch to error dict
                #_spikeNumber = error['Spike']
                
                #print('  _spikeNumber:', _spikeNumber, type(_spikeNumber))
                
                # _sweep = self.getSpikeStat([_spikeNumber], 'sweep')
                # if len(_sweep)==0:
                #     logger.error(f"_spikeNumber:{_spikeNumber} sweep:{_sweep}")
                #     #print(self.getOneSpikeDict(_spikeNumber))
                
                error['Sweep'] = self.getSpikeStat([_spikeNumber], 'sweep')[0]
                error['Epoch'] = self.getSpikeStat([_spikeNumber], 'epoch')[0]

                dictList.append(error)

        if len(dictList) == 0:
            fakeErrorDict = self._getErrorDict(1, 1, "fake", "fake")
            dfError = pd.DataFrame(columns=fakeErrorDict.keys())
        else:
            dfError = pd.DataFrame(dictList)

        if self._detectionDict["verbose"]:
            logger.info(f"Found {len(dfError)} errors in spike detection")

        return dfError

    def _old_to_csv(self):
        """Save as a CSV text file with name <path>_analysis.csv'"""
        savefile = os.path.splitext(self._path)[0]
        savefile += "_analysis.csv"
        saveExcel = False
        alsoSaveTxt = True
        logger.info(f'Saving "{savefile}"')

        be = sanpy.bExport(self)
        be.saveReport(savefile, saveExcel=saveExcel, alsoSaveTxt=alsoSaveTxt)

    def _old__normalizeData(self, data):
        """Calculate normalized data for detection from Kymograph. Is NOT for df/d0."""
        return (data - np.min(data)) / (np.max(data) - np.min(data))

    def _not_used_loadAnalysis(self):
        """Not used."""
        saveBase = self._getSaveBase()

        # load detection parameters
        # self.detectionClass.load(saveBase)

        # load analysis
        # self.spikeDict.load(saveBase)

        saveBase = self._getSaveBase()
        savePath = saveBase + "-analysis.json"

        if not os.path.isfile(savePath):
            # logger.error(f'Did not find file: {savePath}')
            return

        logger.info(f"Loading from saved analysis: {savePath}")

        with open(savePath, "r") as f:
            # self._dDict = json.load(f)
            loadedDict = json.load(f)

        dDict = loadedDict["detection"]
        self.detectionClass._dDict = dDict

        analysisList = loadedDict["analysis"]
        self.spikeDict._myList = analysisList

        self._detectionDirty = False
        self._isAnalyzed = True

    def saveAnalysis_tocsv(self, path : str = None, verbose=False):
        """Save analysis to csv.
        
        CSV starts with one 
        Parameters
        ----------
        path : str
            Full path of file to save, if None will save as default.
        """

        if path is None:
            saveFolder = self._getSaveFolder()
            if not os.path.isdir(saveFolder):
                if verbose:
                    logger.info(f"making folder: {saveFolder}")
                os.mkdir(saveFolder)

            saveBase = self._getSaveBase()
            path = saveBase + "-analysis.csv"

        if verbose:
            logger.info(f'saving to: {path}')

        metaDataHeader = self.metaData.getHeader()

        with open(path, "w") as f:
            f.write(metaDataHeader)
            f.write("\n")

        df = self.asDataFrame()  # pd.DataFrame(self.spikeDict)
        if df is not None:
            df.to_csv(path, mode="a")
        # else:
            # happens when user sets metaDat but does not do analysis
            # logger.warning(f'asDataFrame() returned None')
            # logger.warning(f'  did not save: {self}')

    def saveAnalysis(self, forceSave=False):
        """Not used.

        Save detection parameters and analysis results as json.
        """
        if not self._detectionDirty and not forceSave:
            return

        saveFolder = self._getSaveFolder()
        if not os.path.isdir(saveFolder):
            logger.info(f"making folder: {saveFolder}")
            os.mkdir(saveFolder)

        saveBase = self._getSaveBase()
        savePath = saveBase + "-analysis.json"

        # save detection parameters
        # self.detectionClass.save(saveBase)
        dDict = self.detectionClass.getDict()

        saveDict = {}
        saveDict["detection"] = dDict

        # save list of dict
        # self.spikeDict = sanpy.bAnalysisResults.analysisResultList()
        # self.spikeDict.save(saveBase)
        analysisList = self.spikeDict.asList()

        saveDict["analysis"] = analysisList

        with open(savePath, "w") as f:
            json.dump(saveDict, f, cls=NumpyEncoder, indent=4)

        self._detectionDirty = False

        logger.info(f"Saved analysis to: {savePath}")

    def _getSaveFolder(self):
        """
        All analysis will be saved in folder 'sanpy_analysis'
        """
        filepath = self.fileLoader.filepath
        parentPath, fileName = os.path.split(filepath)
        saveFolder = os.path.join(parentPath, "sanpy_analysis")
        return saveFolder

    def _getSaveBase(self):
        """Get basename to append to to save

        This will always be in a subfolder named 'sanpy_analysis'

        For example, bDetection uses this to save <base>-detection.json
        """
        saveFolder = self._getSaveFolder()

        filepath = self.fileLoader.filepath
        parentPath, fileName = os.path.split(filepath)
        baseName = os.path.splitext(fileName)[0]
        savePath = os.path.join(saveFolder, baseName)

        return savePath

    @property
    def analysisDate(self):
        if self.spikeDict is not None:
            return self.spikeDict.analysisDate()

    @property
    def analysisTime(self):
        if self.spikeDict is not None:
            return self.spikeDict.analysisTime()

    def _api_getHeader(self):
        """Get header as a dict.

        TODO:
            - add info on abf file, like samples per ms

        Returns:
            dict: Dictionary of information about loaded file.
        """
        # recordingDir_sec = len(self.sweepX) / self.dataPointsPerMs / 1000
        recordingFrequency = self.dataPointsPerMs

        ret = {
            "myFileType": self.myFileType,  # ('abf', 'tif', 'bytestream', 'csv')
            "loadError": self.loadError,
            #'detectionDict': self.detectionClass,
            "path": self._path,
            "file": self.fileLoader.filename,
            "dateAnalyzed": self.dateAnalyzed,
            #'detectionType': self.detectionType,
            "acqDate": self.acqDate,
            "acqTime": self.acqTime,
            #
            "_recordingMode": self._recordingMode,
            "get_yUnits": self.get_yUnits(),
            #'currentSweep': self.currentSweep,
            "recording_kHz": recordingFrequency,
            "recordingDur_sec": self.recordingDur,
        }
        return ret

    def _api_getSpikeInfo(self, spikeNum=None):
        """Get info about each spike.

        Args:
            spikeNum (int): Get info for one spike, None for all spikes.

        Returns:
            list: List of dict with info for all (one) spike.
        """
        if spikeNum is not None:
            ret = [self.spikeDict[spikeNum]]
        else:
            ret = self.spikeDict
        return ret

    def _api_getSpikeStat(self, stat):
        """Get stat for each spike

        Args:
            stat (str): The name of the stat to get. Corresponds to key in self.spikeDict[i].

        Returns:
            list: List of values for 'stat'. Ech value is for one spike.
        """
        statList = self.getStat(statName1=stat, statName2=None)
        return statList

    def _api_getRecording(self):
        """Return primary recording

        Returns:
            dict: {'header', 'sweepX', 'sweepY'}

        TODO:
            Add param to only get every n'th point, to return a subset faster (for display)
        """
        # start = time.time()
        ret = {
            "header": self.api_getHeader(),
            "sweepX": self.sweepX2.tolist(),
            "sweepY": self.sweepY2.tolist(),
        }
        # stop = time.time()
        # print(stop-start)
        return ret


class NumpyEncoder(json.JSONEncoder):
    """Special json encoder for numpy types"""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


if __name__ == "__main__":
    pass
