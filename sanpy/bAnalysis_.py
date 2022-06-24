#Author: Robert H Cudmore
#Date: 20190225
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
dDict = sanpy.bDetection.getDefaultDetection()
ba.spikeDetect(dDict)
```
"""

import os, sys, math, time, collections, datetime, enum
import json
import uuid
from collections import OrderedDict
import warnings  # to catch np.polyfit -->> RankWarning: Polyfit may be poorly conditioned

import numpy as np
import pandas as pd
import scipy.signal
import scipy.stats

import pyabf  # see: https://github.com/swharden/pyABF

import sanpy
import sanpy.bDetection
# this specific import is to stop circular imports
#from sanpy.baseUserAnalysis import baseUserAnalysis
import sanpy.user_analysis.baseUserAnalysis
#import sanpy.user_analysis

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def throwOutAboveBelow_(vm, spikeTimes, spikeErrors, peakWindow_pnts, onlyPeaksAbove_mV=None, onlyPeaksBelow_mV=None):
    """
    Args:
        vm (np.ndarray):
        spikeTimes (list): list of spike times
        spikeErrors (list): list of error
    """
    newSpikeTimes = []
    newSpikeErrorList = []
    newSpikePeakPnt = []
    newSpikePeakVal = []
    for i, spikeTime in enumerate(spikeTimes):
        peakPnt = np.argmax(vm[spikeTime:spikeTime+peakWindow_pnts])
        peakPnt += spikeTime
        peakVal = np.max(vm[spikeTime:spikeTime+peakWindow_pnts])

        goodSpikeAbove = True
        if onlyPeaksAbove_mV is not None and (peakVal < onlyPeaksAbove_mV):
            goodSpikeAbove = False
        goodSpikeBelow = True
        if onlyPeaksBelow_mV is not None and (peakVal > onlyPeaksBelow_mV):
            goodSpikeBelow = False

        if goodSpikeAbove and goodSpikeBelow:
            newSpikeTimes.append(spikeTime)
            newSpikeErrorList.append(spikeErrors[i])
            newSpikePeakPnt.append(peakPnt)
            newSpikePeakVal.append(peakVal)
        else:
            #print('spikeDetect() peak height: rejecting spike', i, 'at pnt:', spikeTime, "dDict['onlyPeaksAbove_mV']:", dDict['onlyPeaksAbove_mV'])
            pass
    #
    return newSpikeTimes, newSpikeErrorList, newSpikePeakPnt, newSpikePeakVal

def getEddLines(ba):
    """Get lines representing linear fit of EDD rate.

    Args:
        ba (bAnalysis): bAnalysis object
    """
    logger.info(ba)

    x = []
    y = []
    if ba is None or ba.numSpikes == 0:
        return x, y

    #
    # these are getting for current sweep
    preLinearFitPnt0 = ba.getStat('preLinearFitPnt0')
    preLinearFitSec0 = [ba.pnt2Sec_(x) for x in preLinearFitPnt0]
    preLinearFitVal0 = ba.getStat('preLinearFitVal0')

    preLinearFitPnt1 = ba.getStat('preLinearFitPnt1')
    preLinearFitSec1 = [ba.pnt2Sec_(x) for x in preLinearFitPnt1]
    preLinearFitVal1 = ba.getStat('preLinearFitVal1')

    thisNumSpikes = len(preLinearFitPnt0)
    #for idx, spike in enumerate(range(ba.numSpikes)):
    for idx, spike in enumerate(range(thisNumSpikes)):
        #dx = preLinearFitSec1[idx] - preLinearFitSec0[idx]
        #dy = preLinearFitVal1[idx] - preLinearFitVal0[idx]

        # always plot edd rate line at constant length
        lineLengthSec = 0.1 #8  # TODO: make this a function of spike frequency?

        x.append(preLinearFitSec0[idx])
        x.append(preLinearFitSec1[idx] + lineLengthSec)
        x.append(np.nan)

        y.append(preLinearFitVal0[idx])
        y.append(preLinearFitVal1[idx] + lineLengthSec)
        y.append(np.nan)

    #logger.info(f'{len(x)} {len(y)}')

    return x, y

def getHalfWidthLines(t, v, spikeDictList):
    """Get x/y pair for plotting all half widths."""
    x = []
    y = []

    #if len(t.shape)>1 or len(v.shape)>1:
    #    logger.error('EXPECTING 1D, EXPAND THIS TO 2D SWEEPS')
    #    print(t.shape, v.shape)
    #    return x, y

    if t.shape != v.shape:
        logger.error(f't:{t.shape} and v:{v.shape} are not the same length')
        return x, y

    is2D = len(t.shape) > 1

    numPerSpike = 3  # rise/fall/nan
    #numSpikes = self.ba.numSpikes
    numSpikes = len(spikeDictList)
    logger.info(f'numSpikes:{numSpikes}')
    xyIdx = 0
    #for idx, spike in enumerate(self.ba.spikeDict):
    #spikeDictionaries = self.ba.getSpikeDictionaries(sweepNumber=self.sweepNumber)
    for idx, spike in enumerate(spikeDictList):
        sweep = spike['sweep']
        if idx ==0:
            # make x/y from first spike using halfHeights = [20,50,80,...]
            halfHeights = spike['halfHeights'] # will be same for all spike, like [20, 50, 80]
            numHalfHeights = len(halfHeights)
            # *numHalfHeights to account for rise/fall + padding nan
            x = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
            y = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
            #print('  len(x):', len(x), 'numHalfHeights:', numHalfHeights, 'numSpikes:', numSpikes, 'halfHeights:', halfHeights)

        if 'widths' not in spike.keys():
            logger.error(f'=== Did not find "widths" key in spike {idx}')

        for idx2, width in enumerate(spike['widths']):
            #halfHeight = width['halfHeight'] # [20,50,80]
            risingPnt = width['risingPnt']
            #risingVal = width['risingVal']
            fallingPnt = width['fallingPnt']
            #fallingVal = width['fallingVal']

            if risingPnt is None or fallingPnt is None:
                # half-height was not detected
                continue

            #risingSec = self.ba.pnt2Sec_(risingPnt)
            #fallingSec = self.ba.pnt2Sec_(fallingPnt)


            # if v or t are 2D, we have multiple sweeps
            # one sweep per column
            if is2D:
                risingVal = v[risingPnt,sweep]
                fallingVal = v[fallingPnt,sweep]
                risingSec = t[risingPnt,sweep]
                fallingSec = t[fallingPnt,sweep]
            else:
                risingVal = v[risingPnt]
                fallingVal = v[fallingPnt]
                risingSec = t[risingPnt]
                fallingSec = t[fallingPnt]

            #print(f'fallingVal:{fallingVal} {type(fallingVal)}')

            # x
            x[xyIdx] = risingSec
            x[xyIdx+1] = fallingSec
            x[xyIdx+2] = np.nan
            # y
            y[xyIdx] = fallingVal  #risingVal, re-use fallingVal to make line horizontal
            y[xyIdx+1] = fallingVal
            y[xyIdx+2] = np.nan

            # each spike has 3x pnts: rise/fall/nan
            xyIdx += numPerSpike  # accounts for rising/falling/nan
        # end for width
    # end for spike

    '''
    print(f't:{len(t)} {type(t)} {t.shape}')
    print(f'v:{len(v)} {type(v)} {v.shape}')
    print(f'x:{len(x)} {type(x)} {x[0:10]}')
    print(f'y:{len(y)} {type(y)} {y[0:10]}')
    '''
    #
    return x, y

class bAnalysis:
    def getNewUuid():
        return 't' + str(uuid.uuid4()).replace('-', '_')

    def __init__(self, file=None,
                    #theTiff=None,
                    byteStream=None,
                    fromDf=None, fromDict=None,
                    detectionPreset : sanpy.bDetection.detectionPresets = None,
                    loadData=True,
                    stimulusFileFolder=None):
        """
        Args:
            file (str): Path to either .abf or .csv with time/mV columns.
            #theTiff (str): Path to .tif file. [[[NOT USED]]]
            byteStream (io.BytesIO): Binary stream for use in the cloud.
            fromDf: (pd.DataFrame): One row df with columns as instance variables
                used by analysisDir to reload from h5 file
            fromDict: (dict): Dict has keys ['sweepX', 'sweepY', 'mode']
        """
        
        logger.info(f'IF FILE IS KYMOGRAPH NEED TO SET DETECTION PARAMS {file}')
        if detectionPreset is None:
            detectionPreset = sanpy.bDetection.detectionPresets.default
        self.detectionClass = sanpy.bDetection(detectionPreset=detectionPreset)

        self._isAnalyzed = False

        # mimic pyAbf
        self._dataPointsPerMs = None
        self._currentSweep = 0  # int
        self._sweepList = [0]  # list
        self._sweepLengthSec = np.nan
        self._sweepX = None  # np.ndarray
        self._sweepY = None  # np.ndarray
        self._sweepC = None # the command waveform (DAC)

        self._epochTable = None

        self._filteredVm = None
        self._filteredDeriv = None

        self._recordingMode = 'Unknown'  # str
        self._sweepLabelX = '???'  # str
        self._sweepLabelY = '???'  # str

        self.myFileType = None
        """str: From ('abf', 'csv', 'tif', 'bytestream')"""

        self.loadError = False
        """bool: True if error loading file/stream."""

        #self.detectionDict = None  # remember the parameters of our last detection
        """dict: Dictionary specifying detection parameters, see bDetection.getDefaultDetection."""

        self._path = file  # todo: change this to filePath
        """str: File path."""

        self._abf = None
        """pyAbf: If loaded from binary .abf file"""

        self.dateAnalyzed = None
        """str: Date Time of analysis. TODO: make a property."""

        #self.detectionType = None
        """str: From ('dvdt', 'mv')"""

        #self.spikeDict = []  # a list of dict
        #self.spikeTimes = []  # created in self.spikeDetect()
        self.spikeDict = sanpy.bAnalysisResults.analysisResultList()

        self.spikeClips = []  # created in self.spikeDetect()
        self.spikeClips_x = []  #
        self.spikeClips_x2 = []  #

        self.dfError = None  # dataframe with a list of detection errors
        self.dfReportForScatter = None  # dataframe to be used by scatterplotwidget

        if file is not None and not os.path.isfile(file):
            logger.error(f'File does not exist: "{file}"')
            self.loadError = True

        # only defined when loading abf files
        # turned back on when implementing Santana rabbit Ca kymographs
        self.acqDate = None
        self.acqTime = None

        self._detectionDirty = False

        # will be overwritten by existing uuid in self._loadFromDf()
        self.uuid = bAnalysis.getNewUuid()

        # IMPORTANT:
        #        All instance variable MUST be declared before we load
        #        In particular for self._loadFromDf()

        self.tifData = None

        # instantiate and load abf file
        self.isBytesIO = False
        if fromDict is not None:
            self._loadFromDict(fromDict)
        elif fromDf is not None:
            self._loadFromDf(fromDf)
        elif byteStream is not None:
            self._loadAbf(byteStream=byteStream, loadData=loadData, stimulusFileFolder=stimulusFileFolder)
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

        # get default derivative
        self.rebuildFiltered()
        '''
        if self._recordingMode == 'I-Clamp':
            self._getDerivative()
        elif self._recordingMode == 'V-Clamp':
            self._getBaselineSubtract()
        else:
            logger.warning('Did not take derivative')
        '''

        self._detectionDirty = False

        #self.loadAnalysis()

        # switching back to faster version (no parsing when we cell self.sweepX2
        self.setSweep()

        #mySize = sys.getsizeof(self._sweepX)  # bytes
        #print('bAnalysis mySize:', mySize)

    def asDataFrame(self):
        """Return analysis as a Pandas DataFrame.

            Important:
                This returns a COPY !!!
                Do not modify and expect changes to stick
        """
        #return pd.DataFrame(self.spikeDict.asList())
        return pd.DataFrame(self.spikeDict.asList())

    @property
    def detectionDict(self):
        # TODO: remove this and just use 'detectionClass'
        return self.detectionClass

    def getDetectionDict(self):
        # TODO: remove this and just use 'detectionClass'
        return self.detectionClass

    def __str__(self):
        #return f'ba: {self.getFileName()} dur:{round(self.recordingDur,3)} spikes:{self.numSpikes} isAnalyzed:{self.isAnalyzed()} detectionDirty:{self.detectionDirty}'
        if self.isBytesIO:
             filename = '<BytesIO>'
        else:
            filename = self.getFileName()
        txt = f'ba: {filename} {self.numSweeps} sweep(s) with dur:{round(self.recordingDur,3)} spikes:{self.numSpikes}'
        return txt

    def getInfo(self, withPath=False):
        if withPath:
            pathStr = self._path
        else:
            pathStr = ''
        txt = self.__str__()
        txt += f" start(s):{self.detectionDict['startSeconds']} stop(s):{self.detectionDict['stopSeconds']} {pathStr}"
        return txt

    def isKymograph(self):
        return self.tifData is not None

    def resetKymographRect(self):
        defaultRect = self._abf.resetRoi()
        self._updateTifRoi(defaultRect)
        return defaultRect

    def getKymographRect(self):
        if self.isKymograph():
            return self._abf.getTifRoi()
        else:
            return None

    def getKymographBackgroundRect(self):
        if self.isKymograph():
            return self._abf.getTifRoiBackground()
        else:
            return None

    def _updateTifRoi(self, theRect=[]):
        """
        Update the kymograph ROI
        """
        self._abf.updateTifRoi(theRect)

        self._sweepX[:, 0] = self._abf.sweepX
        self._sweepY[:, 0] = self._abf.sweepY

    def _loadTif(self):
        #print('TODO: load tif file from within bAnalysis ... stop using bAbfText()')
        self._abf = sanpy.bAbfText(self._path)
        # 20220114 removed
        #self._abf.sweepY = self._normalizeData(self._abf.sweepY)
        self.myFileType = 'tif'

        self._sweepList = [0]

        numSweeps = 1
        tmpRows = self._abf.sweepX.shape[0]
        #logger.info(f'tmpRows {tmpRows}')

        self._sweepLengthSec = self._abf.sweepX[-1]

        self._sweepX = np.zeros((tmpRows,numSweeps))
        self._sweepX[:, 0] = self._abf.sweepX

        self._sweepY = np.zeros((tmpRows,numSweeps))
        self._sweepY[:, 0] = self._abf.sweepY

        self._recordingMode = 'tif'
        self._dataPointsPerMs = self._abf.dataPointsPerMs

        self.tifData = self._abf.tif

        self._sweepLabelY = 'f/f0'  # str

    def _loadCsv(self):
        """
        Load from a two column CSV file with columns of (s, mV)
        """
        logger.info(self._path)

        dfCsv = pd.read_csv(self._path)

        # TODO: check column names make sense
        # There must be 2 columns ('s', 'mV')
        numCols = len(dfCsv.columns)
        if numCols != 2:
            # error
            logger.warning(f'There must be two columns, found {numCols}')
            self.loadError = True
            return

        self.myFileType = 'csv'

        firstColStr = dfCsv.columns[0]
        secondColStr = dfCsv.columns[1]

        if firstColStr in ['s', 'sec', 'seconds']:
            timeMult = 1
        elif firstColStr in ['ms']:
            timeMult = 1/1000
        else:
            logger.warning(f'The first column is "{firstColStr}" but must be one of ("s", "sec", "seconds", "ms")')
            self.loadError = True
            return

        self._sweepX = dfCsv[firstColStr].values  # first col is time
        self._sweepY = dfCsv[secondColStr].values  # second col is values (either mV or pA)
        self._sweepC = np.zeros(len(self._sweepX))

        self._sweepX *= timeMult

        # imported csv will always have 1 sweep (1 column)
        self._sweepX = self._sweepX.reshape((self._sweepX.shape[0],1))
        self._sweepY = self._sweepY.reshape((self._sweepY.shape[0],1))
        self._sweepC = self._sweepC.reshape((self._sweepC.shape[0],1))
        #print('self._sweepX:', self._sweepX.shape)

        # TODO: infer from second column
        if secondColStr == 'mV':
            self._recordingMode = 'I-Clamp'
            self._sweepLabelY = 'mV' # TODO: get from column
        elif secondColStr == 'pA':
            self._recordingMode = 'V-Clamp'
            self._sweepLabelY = 'pA' # TODO: get from column
        else:
            logger.warning(f'The seconds column is "{secondColStr}" but muse be one of ("mV", "pA")')

        # always seconds
        self._sweepLabelX = 'sec' # TODO: get from column

        # TODO: infer from first column as ('s', 'ms')
        firstPnt = self._sweepX[0][0]
        secondPnt = self._sweepX[1][0]
        diff_seconds = secondPnt - firstPnt
        diff_ms = diff_seconds * 1000
        _dataPointsPerMs = 1 / diff_ms
        self._dataPointsPerMs = _dataPointsPerMs
        #logger.info(f'_dataPointsPerMs: {_dataPointsPerMs}')

        #self._recordingMode = 'I-Clamp'
        self._sweepLengthSec = self._sweepX[-1][0]

    def _loadFromDf(self, fromDf):
        """Load from a pandas df saved into a .h5 file.

        This uses vars(self) to get all class attributes.
        """
        logger.info(f"uuid: {fromDf['uuid'][0]}")

        # vars(class) retuns a dict with all instance variables
        iDict = vars(self)
        for col in fromDf.columns:
            value = fromDf.iloc[0][col]
            #logger.info(f'col:{col} {type(value)}')
            if col not in iDict.keys():
                logger.warning(f'col "{col}" not in bAnalysis iDict (self.__dict__)')
            iDict[col] = value

        logger.info(f'self._path: {self._path}')
        #logger.info(f'sweepX:{self.sweepX.shape}')
        #logger.info(f'sweepList:{self.sweepList}')
        #logger.info(f'_currentSweep:{self._currentSweep}')

    def _saveToHdf(self, hdfPath, hdfMode):
        """
        Save to h5 file with key self.uuid.
        Only save if detection has changed (e.g. self.detectionDirty)
        """
        didSave = False
        if not self.detectionDirty:
            # Do not save it detection has not changed
            #logger.info(f'NOT SAVING, is not dirty uuid:{self.uuid} {self.getInfo()}')
            logger.info(f'NOT SAVING, is not dirty {self.getInfo(withPath=True)}')
            return didSave

        logger.info(f'SAVING uuid:{self.uuid} {self.getInfo()}')

        #with pd.HDFStore(hdfPath, mode='a') as hdfStore:
        with pd.HDFStore(hdfPath, mode=hdfMode) as hdfStore:
            # vars(class) retuns a dict with all instance variables
            iDict = vars(self)

            oneDf = pd.DataFrame(columns=iDict.keys())
            #oneDf['path'] = [self.path]  # seed oneDf with one row (critical)

            # do not save these instance variables (e.g. self._ba)
            noneKeys = ['_sweepX', '_sweepY', '_sweepC',
                        '_abf', '_filteredVm', '_filteredDeriv',
                        'spikeClips', 'spikeClips_x', 'spikeClips_x2']

            for k,v in iDict.items():
                if k in noneKeys:
                    v = None
                #print(f'saving h5 k:{k} {type(v)}')
                oneDf.at[0, k] = v
            # save into file
            hdfStore[self.uuid] = oneDf

            #
            self._detectionDirty = False
            didSave= True
        #
        #logger.info(f'  Saved {self.uuid} ... {self.getInfo()}')
        #
        return didSave

    def _loadFromDict(self, theDict):
        """Create bAnalysis from a dictionary.

        Args:
            theDict (dict): Requires keys ('sweepX', 'sweepY', 'Mode')
                            Will infer dataPointsPErMs from sweepX
        """
        self._sweepX = theDict['sweepX']
        self._sweepY = theDict['sweepY']
        self._sweepC = np.zeros(self._sweepX.shape)

        self._sweepLengthSec = self._sweepX[-1][0]

        # assuming _sweepX is 2d with one column

        # for 10 kHz will be 0.0001
        dtSeconds = self._sweepX[1,0] - self._sweepX[0,0]
        self._dataPointsPerMs = 1 / (dtSeconds*1000)
        print('_dataPointsPerMs:', self._dataPointsPerMs, type(self._dataPointsPerMs))

        self._recordingMode = theDict['mode'] #'I-Clamp'

        self._path = 'Model_Data'
        self.myFileType = 'fromDict'

    def _loadAtf(self, loadData):
        # We cant't get dataPointsPerMs without loading the data
        loadData = True

        self._abf = pyabf.ATF(self._path)  # , loadData=loadData)
        print('  self._abf:', self._abf.sweepList)
        #try:
        if 1:
            self._sweepList = self._abf.sweepList
            self._sweepLengthSec = self._abf.sweepLengthSec
            if loadData:
                tmpRows = self._abf.sweepX.shape[0]
                numSweeps = len(self._sweepList)
                self._sweepX = np.zeros((tmpRows,numSweeps))
                self._sweepY = np.zeros((tmpRows,numSweeps))
                self._sweepC = np.zeros((tmpRows,numSweeps))

                for sweep in self._sweepList:
                    self._abf.setSweep(sweep)
                    self._sweepX[:, sweep] = self._abf.sweepX  # <class 'numpy.ndarray'>, (60000,)
                    self._sweepY[:, sweep] = self._abf.sweepY
                    #self._sweepC[:, sweep] = self._abf.sweepC
                # not needed
                self._abf.setSweep(0)

            logger.info(f'Loaded abf self._sweepX: {self._sweepX.shape}')
            # get v from pyAbf
            if len(self.sweepX.shape) > 1:
                t0 = self.sweepX[0][0]
                t1 = self.sweepX[1][0]
            else:
                t0 = self.sweepX[0]
                t1 = self.sweepX[1]
            dt = (t1-t0) * 1000
            dataPointsPerMs = 1 / dt
            dataPointsPerMs = round(dataPointsPerMs)
            self._dataPointsPerMs = dataPointsPerMs

            '''
            channel = 0
            adcUnits = self._abf.adcUnits[channel]
            self._sweepLabelY = adcUnits
            self._sweepLabelX = "sec'"
            '''
            self._sweepLabelY = 'mV'
            self._sweepLabelX = "sec'"

            if self._sweepLabelY in ['pA']:
                self._recordingMode = 'V-Clamp'
            elif self._sweepLabelY in ['mV']:
                self._recordingMode = 'I-Clamp'

        '''
        except (Exception) as e:
            # some abf files throw: 'unpack requires a buffer of 234 bytes'
            logger.error(f'did not load ATF file: {self._path}')
            logger.error(f'  unknown Exception was: {e}')
            self.loadError = True
            self._abf = None
        '''

        self.myFileType = 'atf'

        # don't keep _abf, we grabbed every thing we needed

    def _loadAbf(self, byteStream=None, loadData=True, stimulusFileFolder=None):
        """Load pyAbf from path."""
        try:
            #logger.info(f'loadData:{loadData}')
            if byteStream is not None:
                self._abf = pyabf.ABF(byteStream)
                self.isBytesIO = True
            else:
                self._abf = pyabf.ABF(self._path, loadData=loadData, stimulusFileFolder=stimulusFileFolder)

        except (NotImplementedError) as e:
            logger.error(f'did not load abf file: {self._path}')
            logger.error(f'  NotImplementedError exception was: {e}')
            self.loadError = True
            self._abf = None

        except (Exception) as e:
            # some abf files throw: 'unpack requires a buffer of 234 bytes'
            logger.error(f'did not load abf file: {self._path}')
            logger.error(f'  unknown Exception was: {e}')
            self.loadError = True
            self._abf = None

        if 1:
            self._epochTable = sanpy.epochTable(self._abf)
            
            self._sweepList = self._abf.sweepList
            self._sweepLengthSec = self._abf.sweepLengthSec

            # on load, sweep is 0
            if loadData:
                tmpRows = self._abf.sweepX.shape[0]
                numSweeps = len(self._sweepList)
                self._sweepX = np.zeros((tmpRows,numSweeps))
                self._sweepY = np.zeros((tmpRows,numSweeps))
                self._sweepC = np.zeros((tmpRows,numSweeps))

                for sweep in self._sweepList:
                    self._abf.setSweep(sweep)
                    self._sweepX[:, sweep] = self._abf.sweepX  # <class 'numpy.ndarray'>, (60000,)
                    self._sweepY[:, sweep] = self._abf.sweepY
                    try:
                        self._sweepC[:, sweep] = self._abf.sweepC
                    except(ValueError) as e:
                        # pyabf will raise this error if it is an atf file
                        logger.warning(f'exception fetching sweepC for sweep {sweep} with {self.numSweeps}: {e}')
                        #
                        # if we were recorded with a stimulus file abf
                        # needed to assign stimulusWaveformFromFile
                        try:
                            tmpSweepC = self._abf.sweepC
                            self._sweepC[:, sweep] = self._abf.sweepC
                        except (ValueError) as e:
                            logger.warning(f'ba has no sweep {sweep} sweepC ???')

                # not needed
                self._abf.setSweep(0)

            # get v from pyAbf
            self._dataPointsPerMs = self._abf.dataPointsPerMs

            # turned back on when implementing Santana rabbit Ca kymographs
            abfDateTime = self._abf.abfDateTime  # 2019-01-14 15:20:48.196000
            self.acqDate = abfDateTime.strftime("%Y-%m-%d")
            self.acqTime = abfDateTime.strftime("%H:%M:%S")

            #self.sweepUnitsY = self.adcUnits[channel]
            channel = 0
            #dacUnits = self._abf.dacUnits[channel]
            adcUnits = self._abf.adcUnits[channel]
            #print('  adcUnits:', adcUnits)  # 'mV'
            self._sweepLabelY = adcUnits
            self._sweepLabelX = "sec'"

            #self._sweepLabelX = self._abf.sweepLabelX
            #self._sweepLabelY = self._abf.sweepLabelY
            if self._sweepLabelY in ['pA']:
                self._recordingMode = 'V-Clamp'
                #self._sweepY_label = self._abf.sweepUnitsY
            elif self._sweepLabelY in ['mV']:
                self._recordingMode = 'I-Clamp'
                #self._sweepY_label = self._abf.sweepUnitsY

            '''
            if self._abf.sweepUnitsY in ['pA']:
                self._recordingMode = 'V-Clamp'
                self._sweepY_label = self._abf.sweepUnitsY
            elif self._abf.sweepUnitsY in ['mV']:
                self._recordingMode = 'I-Clamp'
                self._sweepY_label = self._abf.sweepUnitsY
            '''


        #
        self.myFileType = 'abf'

        # base sanpy does not keep the abf around
        logger.warning('[[[TURNED BACK ON]]] I turned off assigning self._abf=None for stoch-res stim file load')
        self._abf = None

    @property
    def detectionDirty(self):
        return self._detectionDirty

    @property
    def path(self):
        return self._path

    def getFilePath(self):
        return self._path

    def getFileName(self):
        if self._path is None:
            return None
        else:
            return os.path.split(self._path)[1]

    @property
    def abf(self):
        """Get the underlying pyabf object."""
        return self._abf

    @property
    def recordingMode(self):
        return self._recordingMode

    @property
    def recordingDur(self):
        """Get recording duration in seconds.

        If there are multiple sweeps, assuming all are the same duration.
        """
        theDur = self._sweepLengthSec
        #logger.info(f'theDur:{theDur} {type(theDur)}')
        return theDur

    @property
    def recordingFrequency(self):
        """Get recording frequency in kHz."""
        return self._dataPointsPerMs

    @property
    def currentSweep(self):
        return self._currentSweep

    @property
    def dataPointsPerMs(self):
        """Get the number of data points per ms."""
        return self._dataPointsPerMs

    '''
    def setSweep(self, sweepNumber):
        """
        Set the current sweep.

        Args:
            sweepNumber (str): from ('All', 0, 1, 2, 3, ...)

        TODO:
            - Set sweep of underlying abf (if we have one)
            - take channel into account with:
                abf.setSweep(sweepNumber: 3, channel: 0)
        """
        if sweepNumber == 'All':
            sweepNumber = 'allsweeps'
        elif sweepNumber == 'allsweeps':
            pass
        else:
            sweepNumber = int(sweepNumber)
        self._currentSweep = sweepNumber
        self.rebuildFiltered()
    '''

    @property
    def sweepList(self):
        """Get the list of sweeps."""
        return self._sweepList

    @property
    def numSweeps(self):
        """Get the number of sweeps."""
        return len(self._sweepList)

    @property
    def numSpikes(self):
        """Get the total number of detected spikes."""
        #return len(self.spikeTimes) # spikeTimes is tmp per sweep
        return len(self.spikeDict) # spikeDict has all spikes for all sweeps

    def old_getOneColumns(self, d):
        shape = d.shape
        if len(shape) == 1:
            return d
        else:
            d = d[:,0]
            logger.info(d.shape)
            return d

    def old_safeOneSweep(self, d):
        if d is None or len(d.shape) != 2:
            logger.error(f'Expecing shape len of 2 but got "{d.shape}"')
            return d
        else:
            return d[:,0]

    @property
    def sweepX(self):
        return self._sweepX[:, self.currentSweep]
        """Get the time (seconds) from recording (numpy.ndarray)."""
        '''
        if self.numSweeps == 1:
            return self._safeOneSweep(self._sweepX)
        elif sweepNumber is None or sweepNumber == 'All':
            return self._sweepX  # will be 2D
        else:
            theSweepX = self._sweepX[:,sweepNumber]
            theSweepX = self._getOneColumns(theSweepX)
            return theSweepX
        '''
    @property
    def sweepY(self):
        """Get the amplitude (mV or pA) from recording (numpy.ndarray). Units wil depend on mode"""
        return self._sweepY[:, self.currentSweep]
        '''
        if self.numSweeps == 1:
            return self._safeOneSweep(self._sweepY)
        elif sweepNumber is None or sweepNumber == 'All':
            return self._sweepY
        else:
            theSweepY = self._sweepY[:,sweepNumber]
            theSweepY = self._getOneColumns(theSweepY)
            return theSweepY
        '''

    @property
    def sweepC(self):
        """Get the command waveform DAC (numpy.ndarray). Units will depend on mode"""
        if self._sweepC is None:
            return np.zeros_like(self._sweepX[:, self.currentSweep])
        return self._sweepC[:, self.currentSweep]
        '''
        if self.numSweeps == 1:
            return self._safeOneSweep(self._sweepC)
        elif sweepNumber is None or sweepNumber == 'All':
            return self._sweepC
        else:
            #return self._sweepC[:,sweepNumber]
            theSweepC = self._sweepC[:,sweepNumber]
            theSweepC = self._getOneColumns(theSweepC)
            return theSweepC
        '''

    @property
    def filteredDeriv(self):
        """Get the command waveform DAC (numpy.ndarray). Units will depend on mode"""
        return self._filteredDeriv[:, self.currentSweep]
        '''
        #logger.info(self._filteredDeriv.shape)
        if self.numSweeps == 1:
            return self._safeOneSweep(self._filteredDeriv)
        elif sweepNumber is None or sweepNumber == 'All':
            return self._filteredDeriv
        else:
            #return self._filteredDeriv[:,sweepNumber]
            theFilteredDeriv = self._filteredDeriv[:,sweepNumber]
            theFilteredDeriv = self._getOneColumns(theFilteredDeriv)
            return theFilteredDeriv
        '''

    # TODO: Get rid of filteredVm and replace with sweepY_filtered

    @property
    def sweepY_filtered(self):
        return self._filteredVm[:, self.currentSweep]

    @property
    def filteredVm(self):
        return self._filteredVm[:, self.currentSweep]
        '''
        """Get the command waveform DAC (numpy.ndarray). Units will depend on mode"""
        if self.numSweeps == 1:
            return self._safeOneSweep(self._filteredVm)
        elif sweepNumber is None or sweepNumber == 'All':
            return self._filteredVm
        else:
            theFilteredVm = self._filteredVm[:,sweepNumber]
            theFilteredVm = self._getOneColumns(theFilteredVm)
            return theFilteredVm
        '''

    def setSweep(self, sweep=0):
        self._currentSweep = sweep
        '''
        self._sweepX2 = self._sweepX[:,sweep]
        self._sweepY2 = self._sweepY[:,sweep]
        self._sweepC2 = self._sweepC[:,sweep]
        self._filteredDeriv2 = self._filteredDeriv[:,sweep]
        '''

    '''
    @property
    def sweepX2(self):
        return self._sweepX2

    @property
    def sweepY2(self):
        return self._sweepY2

    @property
    def filteredDeriv2(self):
        return self._filteredDeriv2
    '''

    def get_yUnits(self):
        return self._sweepLabelY

    def get_xUnits(self):
        return self._sweepLabelX

    def getDetectionType(self):
        # <enum 'detectionTypes_'>
        #return self.detectionClass['detectionType'].name
        return self.detectionClass['detectionType']

    def isDirty(self):
        return self._detectionDirty

    def isAnalyzed(self):
        """Return True if this bAnalysis has been analyzed, False otherwise."""
        #return self.detectionDict is not None
        #return self.numSpikes > 0
        return self._isAnalyzed

    def getStatMean(self, statName, sweepNumber=None):
        """
        Get the mean of an analysis parameter.

        Args:
            statName (str): Name of the statistic to retreive.
                For a list of available stats use bDetection.defaultDetection.
        """
        theMean = None
        x = self.getStat(statName, sweepNumber=sweepNumber)
        if x is not None and len(x)>1:
            theMean = np.nanmean(x)
        return theMean

    def setSpikeStat(self, spikeList, stat, value):
        """Used to set simple things like ('isBad', 'userType1', ...)
        """
        if len(spikeList) == 0:
            return

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

    def getSweepStats(self, statName:str, decimals=3, asDataFrame=False, df=None):
        """

        Args:
            df (pd.DataFrame): For kymograph we sometimes have to convert (peak) values to molar
        """

        if df is None:
            df = self.spikeDict.asDataFrame()

        sweepStatList = []

        for sweep in range(self.numSweeps):
            oneDf = df[ df['sweep']==sweep ]
            theValues = oneDf[statName]

            theCount = np.count_nonzero(~np.isnan(theValues))
            theMin = np.min(theValues)
            theMax = np.max(theValues)
            theMean = np.nanmean(theValues)

            theMin = round(theMin,decimals)
            theMax = round(theMax,decimals)
            theMean = round(theMean,decimals)

            if theCount>2:
                theMedian = np.nanmedian(theValues)
                theSEM = scipy.stats.sem(theValues)
                theSD = np.nanstd(theValues)
                theVar = np.nanvar(theValues)
                theCV = theSD / theVar

                theMedian = round(theMedian,decimals)
                theSEM = round(theSEM,decimals)
                theSD = round(theSD,decimals)
                theVar = round(theVar,decimals)
                theCV = round(theCV,decimals)

            else:
                theMedian = None
                theSEM = None
                theSD = None
                theVar = None
                theCV = None

            oneDict = {
                statName+'_sweep': sweep,
                statName+'_count': theCount,
                statName+'_min': theMin,
                statName+'_max': theMax,
                statName+'_mean': theMean,
                statName+'_median': theMedian,
                statName+'_sem': theSEM,
                statName+'_std': theSD,
                statName+'_var': theVar,
                statName+'_cv': theCV,
            }

            sweepStatList.append(oneDict)

        #
        if asDataFrame:
            return pd.DataFrame(sweepStatList)
        else:
            return sweepStatList

    def getStat(self, statName1, statName2=None, sweepNumber=None, asArray=False):
        """
        Get a list of values for one or two analysis parameters.

        For a list of available analysis parameters, use [bDetection.getDefaultDetection()][sanpy.bDetection.bDetection]

        If the returned list of analysis parameters are in points,
            convert to seconds or ms using: pnt2Sec_(pnt) or pnt2Ms_(pnt).

        Args:
            statName1 (str): Name of the first analysis parameter to retreive.
            statName2 (str): Optional, Name of the second analysis parameter to retreive.

        Returns:
            list: List of analysis parameter values, None if error.

        TODO: Add convertToSec (bool)
        """
        def clean(val):
            """Convert None to float('nan')"""
            if val is None:
                val = float('nan')
            return val

        x = []  # None
        y = []  # None
        error = False

        if len(self.spikeDict) == 0:
            #logger.error(f'Did not find any spikes in spikeDict')
            error = True
        elif statName1 not in self.spikeDict[0].keys():
            logger.error(f'Did not find statName1: "{statName1}" in spikeDict')
            error = True
        elif statName2 is not None and statName2 not in self.spikeDict[0].keys():
            logger.error(f'Did not find statName2: "{statName2}" in spikeDict')
            error = True

        if sweepNumber is None:
            sweepNumber = 'All'

        if not error:
            # original
            #x = [clean(spike[statName1]) for spike in self.spikeDict]
            # only current spweek
            x = [clean(spike[statName1]) for spike in self.spikeDict if (sweepNumber=='All' or spike['sweep']==sweepNumber)]

            if statName2 is not None:
                # original
                #y = [clean(spike[statName2]) for spike in self.spikeDict]
                # only current spweek
                y = [clean(spike[statName2]) for spike in self.spikeDict if sweepNumber=='All' or spike['sweep']==sweepNumber]

        if asArray:
            x = np.array(x)
            if statName2 is not None:
                y = np.array(y)

        if statName2 is not None:
            return x, y
        else:
            return x

    def getSpikeTimes(self, sweepNumber=None):
        """Get spike times for current sweep
        """
        #theRet = [spike['thresholdPnt'] for spike in self.spikeDict if spike['sweep']==self.currentSweep]
        theRet = self.getStat('thresholdPnt', sweepNumber=sweepNumber)
        return theRet

    def getSpikeSeconds(self, sweepNumber=None):
        #theRet = [spike['thresholdSec'] for spike in self.spikeDict if spike['sweep']==self.currentSweep]
        theRet = self.getStat('thresholdSec')
        return theRet

    def getSpikeDictionaries(self, sweepNumber=None):
        """Get spike dictionaries for current sweep
        """
        if sweepNumber is None:
            sweepNumber = 'All'
        #logger.info(f'sweepNumber:{sweepNumber}')
        theRet = [spike for spike in self.spikeDict if sweepNumber=='All' or spike['sweep']==sweepNumber]
        return theRet

    def rebuildFiltered(self):
        if self._sweepX is None:
            # no data
            logger.warning('not getting derivative')
            return

        if self._recordingMode == 'I-Clamp' or self._recordingMode == 'tif':
            self._getDerivative()
        elif self._recordingMode == 'V-Clamp':
            self._getBaselineSubtract()
        else:
            logger.warning('Did not take derivative')

    def _getFilteredRecording(self, dDict=None):
        """
        Get a filtered version of recording, used for both V-Clamp and I-Clamp.

        Args:
            dDict (dict): Default detection dictionary. See bDetection.defaultDetection
        """
        if dDict is None:
            dDict = sanpy.bDetection.getDefaultDetection()

        medianFilter = dDict['medianFilter']
        SavitzkyGolay_pnts = dDict['SavitzkyGolay_pnts']
        SavitzkyGolay_poly = dDict['SavitzkyGolay_poly']

        if medianFilter > 0:
            if not medianFilter % 2:
                medianFilter += 1
                logger.warning(f'Please use an odd value for the median filter, set medianFilter: {medianFilter}')
            medianFilter = int(medianFilter)
            self._filteredVm = scipy.signal.medfilt2d(self.sweepY(), [medianFilter,1])
        elif SavitzkyGolay_pnts > 0:
            self._filteredVm = scipy.signal.savgol_filter(self.sweepY(),
                                SavitzkyGolay_pnts, SavitzkyGolay_poly,
                                mode='nearest', axis=0)
        else:
            self._filteredVm = self.sweepY

    def _getBaselineSubtract(self, dDict=None):
        """
        for V-Clamp

        Args:
            dDict (dict): Default detection dictionary. See bDetection.getDefaultDetection()
        """
        #print('\n\n _getBaselineSubtract for v-clamp IS BROKEN BECAUSE OF SWEEPS IN FILTERED DERIV\n\n')

        logger.info('XXX TODO: Need to add a way to baseline subtract for spontaneous V-Clamp data !!!')

        # temporary fix, makes no sense for V-Clamp
        self._getDerivative()

        #
        return
        #

        '''
        if dDict is None:
            dDict = sanpy.bDetection.getDefaultDetection()

        # work on a copy
        dDictCopy = dDict.copy()
        dDictCopy['medianFilter'] = 5

        self._getFilteredRecording(dDictCopy)

        # baseline subtract filtered recording
        theMean = np.nanmean(self.filteredVm)
        self.filteredDeriv = self.filteredVm.copy()
        self.filteredDeriv -= theMean
        '''

    def _getDerivative(self):
        """
        Get derivative of recording (used for I-Clamp). Uses (xxx,yyy,zzz) keys in dDict.

        Args:
            dDict (dict): Default detection dictionary. See bDetection.getDefaultDetection()
        """
        #if dDict is None:
        #    dDict = sanpy.bDetection.getDefaultDetection()

        #medianFilter = dDict['medianFilter']
        #SavitzkyGolay_pnts = dDict['SavitzkyGolay_pnts']
        #SavitzkyGolay_poly = dDict['SavitzkyGolay_poly']
        medianFilter = self.detectionClass.getValue('medianFilter')
        SavitzkyGolay_pnts = self.detectionClass.getValue('SavitzkyGolay_pnts')
        SavitzkyGolay_poly = self.detectionClass.getValue('SavitzkyGolay_poly')

        if medianFilter > 0:
            if not medianFilter % 2:
                medianFilter += 1
                logger.warning('Please use an odd value for the median filter, set medianFilter: {medianFilter}')
            medianFilter = int(medianFilter)
            self._filteredVm = scipy.signal.medfilt2d(self._sweepY, [medianFilter,1])
        elif SavitzkyGolay_pnts > 0:
            self._filteredVm = scipy.signal.savgol_filter(self._sweepY,
                                SavitzkyGolay_pnts, SavitzkyGolay_poly,
                                axis=0,
                                mode='nearest')
        else:
            self._filteredVm = self._sweepY

        self._filteredDeriv = np.diff(self._filteredVm, axis=0)

        # filter the derivative
        if medianFilter > 0:
            if not medianFilter % 2:
                medianFilter += 1
                print(f'Please use an odd value for the median filter, set medianFilter: {medianFilter}')
            medianFilter = int(medianFilter)
            self._filteredDeriv = scipy.signal.medfilt2d(self._filteredDeriv, [medianFilter,1])
        elif SavitzkyGolay_pnts > 0:
            self._filteredDeriv = scipy.signal.savgol_filter(self._filteredDeriv,
                                    SavitzkyGolay_pnts, SavitzkyGolay_poly,
                                    axis = 0,
                                    mode='nearest')
        else:
            #self._filteredDeriv = self.filteredDeriv
            pass

        # mV/ms
        dataPointsPerMs = self.dataPointsPerMs
        self._filteredDeriv = self._filteredDeriv * dataPointsPerMs #/ 1000

        # insert an initial point (rw) so it is the same length as raw data in abf.sweepY
        # three options (concatenate, insert, vstack)
        # could only get vstack working
        #self.deriv = np.concatenate(([0],self.deriv))
        rowOfZeros = np.zeros(self.numSweeps)
        rowZero = 0

        #print('  rowOfZeros:', rowOfZeros.shape)
        #print('  _filteredDeriv:', self._filteredDeriv.shape)

        self._filteredDeriv = np.vstack([rowOfZeros, self._filteredDeriv])
        #self._filteredDeriv = np.insert(self.filteredDeriv, rowZero, rowOfZeros, axis=0)
        #self._filteredDeriv = np.concatenate((zeroRow,self.filteredDeriv))
        #print('  self._filteredDeriv:', self._filteredDeriv[0:4,:])

    def _backupSpikeVm(self, spikeTimes, sweepNumber, medianFilter=None):
        """
        Backup spike time using deminishing SD and diff b/w vm at pnt[i]-pnt[i-1]
        Used when detecting with just mV threshold (not dv/dt)

        Args:
            spikeTimes (list of float):
            medianFilter (int): bin width
        """
        #realSpikeTimePnts = [np.nan] * self.numSpikes
        realSpikeTimePnts = [np.nan] * len(spikeTimes)

        medianFilter = 5
        sweepY = self.sweepY
        if medianFilter>0:
            myVm = scipy.signal.medfilt(sweepY, medianFilter)
        else:
            myVm = sweepY

        #
        # TODO: this is going to fail if spike is at start/stop of recorrding
        #

        maxNumPntsToBackup = 20 # todo: add _ms
        bin_ms = 1
        bin_pnts = round(bin_ms * self.dataPointsPerMs)
        half_bin_pnts = math.floor(bin_pnts/2)
        for idx, spikeTimePnts in enumerate(spikeTimes):
            foundRealThresh = False
            thisMean = None
            thisSD = None
            backupNumPnts = 0
            atBinPnt = spikeTimePnts
            while not foundRealThresh:
                thisWin = myVm[atBinPnt-half_bin_pnts: atBinPnt+half_bin_pnts]
                if thisMean is None:
                    thisMean = np.mean(thisWin)
                    thisSD = np.std(thisWin)

                nextStart = atBinPnt-1-bin_pnts-half_bin_pnts
                nextStop = atBinPnt-1-bin_pnts+half_bin_pnts
                nextWin = myVm[nextStart:nextStop]
                nextMean = np.mean(nextWin)
                nextSD = np.std(nextWin)

                meanDiff = thisMean - nextMean
                # logic
                sdMult = 0.7 # 2
                if (meanDiff < nextSD * sdMult) or (backupNumPnts==maxNumPntsToBackup):
                    # second clause will force us to terminate (this recording has a very slow rise time)
                    # bingo!
                    foundRealThresh = True
                    # not this xxx but the previous
                    moveForwardPnts = 4
                    backupNumPnts = backupNumPnts - 1 # the prev is thresh
                    if backupNumPnts<moveForwardPnts:
                        logger.warning(f'spike {idx} backupNumPnts:{backupNumPnts} < moveForwardPnts:{moveForwardPnts}')
                        #print('  -->> not adjusting spike time')
                        realBackupPnts = backupNumPnts - 0
                        realPnt = spikeTimePnts - (realBackupPnts*bin_pnts)

                    else:
                        realBackupPnts = backupNumPnts - moveForwardPnts
                        realPnt = spikeTimePnts - (realBackupPnts*bin_pnts)
                    #
                    realSpikeTimePnts[idx] = realPnt

                # increment
                thisMean = nextMean
                thisSD = nextSD

                atBinPnt -= bin_pnts
                backupNumPnts += 1
                '''
                if backupNumPnts>maxNumPntsToBackup:
                    print(f'  WARNING: _backupSpikeVm() exiting spike {idx} ... reached maxNumPntsToBackup:{maxNumPntsToBackup}')
                    print('  -->> not adjusting spike time')
                    foundRealThresh = True # set this so we exit the loop
                    realSpikeTimePnts[idx] = spikeTimePnts
                '''

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
        #refractory_ms = 20 #10 # remove spike [i] if it occurs within refractory_ms of spike [i-1]
        lastGood = 0 # first spike [0] will always be good, there is no spike [i-1]
        for i in range(len(spikeTimes0)):
            if i==0:
                # first spike is always good
                continue
            dPoints = spikeTimes0[i] - spikeTimes0[lastGood]
            if dPoints < self.dataPointsPerMs*refractory_ms:
                # remove spike time [i]
                spikeTimes0[i] = 0
            else:
                # spike time [i] was good
                lastGood = i
        # regenerate spikeTimes0 by throwing out any spike time that does not pass 'if spikeTime'
        # spikeTimes[i] that were set to 0 above (they were too close to the previous spike)
        # will not pass 'if spikeTime', as 'if 0' evaluates to False
        if goodSpikeErrors is not None:
            goodSpikeErrors = [goodSpikeErrors[idx] for idx, spikeTime in enumerate(spikeTimes0) if spikeTime]
        spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if spikeTime]

        # TODO: put back in and log if detection ['verbose']
        after = len(spikeTimes0)
        if self.detectionClass['verbose']:
            logger.info(f'From {before} to {after} spikes with refractory_ms:{refractory_ms}')

        return spikeTimes0, goodSpikeErrors

    def _getHalfWidth(self, vm, iIdx, spikeDict, thresholdPnt, peakPnt, hwWindowPnts, dataPointsPerMs, halfHeightList, verbose=False):
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

        spikeSecond = thresholdPnt / dataPointsPerMs /1000
        peakSec = peakPnt / dataPointsPerMs /1000

        widthDictList = []
        errorList = []

        # clear out any existing list
        spikeDict[iIdx]['widths'] = []

        tmpErrorType = None
        for j, halfHeight in enumerate(halfHeightList):
            # halfHeight in [20, 50, 80]

            # search rising/falling phae of vm for this vm
            thisVm = thresholdVal + spikeHeight * (halfHeight * 0.01)

            #todo: logic is broken, this get over-written in following try
            widthDict = {
                'halfHeight': halfHeight,
                'risingPnt': None,
                #'risingVal': defaultVal,
                'fallingPnt': None,
                #'fallingVal': defaultVal,
                'widthPnts': None,
                'widthMs': float('nan')
            }
            widthMs = float('nan')
            try:
                postRange = vm[peakPnt:peakPnt+hwWindowPnts]
                fallingPnt = np.where(postRange<thisVm)[0] # less than
                if len(fallingPnt)==0:
                    # no falling pnts found within hwWindowPnts
                    tmpErrorType = 'falling point'
                    raise IndexError
                fallingPnt = fallingPnt[0] # first falling point
                fallingPnt += peakPnt
                fallingVal = vm[fallingPnt]

                # use the post/falling to find pre/rising
                preRange = vm[thresholdPnt:peakPnt]
                risingPnt = np.where(preRange>fallingVal)[0] # greater than
                if len(risingPnt)==0:
                    tmpErrorType = 'rising point'
                    raise IndexError
                risingPnt = risingPnt[0] # first rising point
                risingPnt += thresholdPnt
                #risingVal = vm[risingPnt]

                # width (pnts)
                widthPnts = fallingPnt - risingPnt
                widthMs = widthPnts / dataPointsPerMs
                # 20210825 may want to add this to analysis
                #widthPnts2 = fallingPnt - thresholdPnt
                # assign
                widthDict['halfHeight'] = halfHeight
                widthDict['risingPnt'] = risingPnt
                #widthDict['risingVal'] = risingVal
                widthDict['fallingPnt'] = fallingPnt
                #widthDict['fallingVal'] = fallingVal
                widthDict['widthPnts'] = widthPnts
                widthDict['widthMs'] = widthMs
                #widthMs = widthPnts / dataPointsPerMs # abb 20210125

                # may want to add this
                #widthDict['widthPnts2'] = widthPnts2
                #widthDict['widthMs2'] = widthPnts2 / dataPointsPerMs

            except (IndexError) as e:
                errorType = 'Spike Width'
                errorStr = (f'Half width {halfHeight} error in "{tmpErrorType}" '
                        f"with halfWidthWindow_ms:{halfWidthWindow_ms} "
                        f'searching for Vm:{round(thisVm,2)} from peak sec {round(peakSec,2)}'
                        )

                # was this
                #eDict = self._getErrorDict(spikeNumber, thresholdPnt, errorType, errorStr) # spikeTime is in pnts
                eDict = self._getErrorDict(iIdx, thresholdPnt, errorType, errorStr) # spikeTime is in pnts
                #self.spikeDict[dictNumber]['errors'].append(eDict)
                spikeDict[iIdx]['errors'].append(eDict)
                if verbose:
                    print(f'_getHalfWidth() error iIdx:{iIdx} j:{j} halfHeight:{halfHeight} eDict:{eDict}')
            #
            #self.spikeDict[dictNumber]['widths_'+str(halfHeight)] = widthMs
            #self.spikeDict[dictNumber]['widths'][j] = widthDict

            #logger.info('================')
            #print(f'len(spikeDict):{len(spikeDict)} iIdx:{iIdx} j:{j} widthDict:{widthDict}')

            spikeDict[iIdx]['widths_'+str(halfHeight)] = widthMs
            #spikeDict[iIdx]['widths'][j] = widthDict
            spikeDict[iIdx]['widths'].append(widthDict)

        #
        #return widthDictList, errorList

    def _getErrorDict(self, spikeNumber, pnt, type, detailStr):
        """
        Get error dict for one spike

        TODO: xxx
        """
        sec = self.pnt2Sec_(pnt)  # pnt / self.dataPointsPerMs / 1000
        sec = round(sec,4)

        eDict = {
            'Spike': spikeNumber,
            'Seconds': sec,
            'Type': type,
            'Details': detailStr,
        }
        return eDict

    def _spikeDetect_dvdt(self, dDict, sweepNumber, verbose=False):
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
        filteredDeriv = self.filteredDeriv
        Is=np.where(filteredDeriv>dDict['dvdtThreshold'])[0]
        Is=np.concatenate(([0],Is))
        Ds=Is[:-1]-Is[1:]+1
        spikeTimes0 = Is[np.where(Ds)[0]+1]

        #
        # reduce spike times based on start/stop
        if dDict['startSeconds'] is not None and dDict['stopSeconds'] is not None:
            startPnt = self.dataPointsPerMs * (dDict['startSeconds']*1000) # seconds to pnt
            stopPnt = self.dataPointsPerMs * (dDict['stopSeconds']*1000) # seconds to pnt
            tmpSpikeTimes = [spikeTime for spikeTime in spikeTimes0 if (spikeTime>=startPnt and spikeTime<=stopPnt)]
            spikeTimes0 = tmpSpikeTimes

        #
        # throw out all spikes that are below a threshold Vm (usually below -20 mV)
        peakWindow_pnts = self.ms2Pnt_(dDict['peakWindow_ms'])
        #peakWindow_pnts = self.dataPointsPerMs * dDict['peakWindow_ms']
        #peakWindow_pnts = round(peakWindow_pnts)
        goodSpikeTimes = []
        sweepY = self.sweepY
        for spikeTime in spikeTimes0:
            peakVal = np.max(sweepY[spikeTime:spikeTime+peakWindow_pnts])
            if peakVal > dDict['mvThreshold']:
                goodSpikeTimes.append(spikeTime)
        spikeTimes0 = goodSpikeTimes

        #
        # throw out spike that are not upward deflections of Vm
        '''
        prePntUp = 7 # pnts
        goodSpikeTimes = []
        for spikeTime in spikeTimes0:
            preAvg = np.average(self.abf.sweepY[spikeTime-prePntUp:spikeTime-1])
            postAvg = np.average(self.abf.sweepY[spikeTime+1:spikeTime+prePntUp])
            #print(preAvg, postAvg)
            if preAvg < postAvg:
                goodSpikeTimes.append(spikeTime)
        spikeTimes0 = goodSpikeTimes
        '''

        #
        # if there are doubles, throw-out the second one
        spikeTimeErrors = None
        spikeTimes0, ignoreSpikeErrors = self._throwOutRefractory(spikeTimes0, spikeTimeErrors, refractory_ms=dDict['refractory_ms'])

        #logger.warning('REMOVED SPIKE TOP AS % OF DVDT')
        #return spikeTimes0, [None] * len(spikeTimes0)
        
        #
        # for each threshold crossing, search backwards in dV/dt for a % of maximum (about 10 ms)
        #dvdt_percentOfMax = 0.1
        #window_ms = 2
        window_pnts = dDict['dvdtPreWindow_ms'] * self.dataPointsPerMs
        # abb 20210130 lcr analysis
        window_pnts = round(window_pnts)
        spikeTimes1 = []
        spikeErrorList1 = []
        filteredDeriv = self.filteredDeriv
        for i, spikeTime in enumerate(spikeTimes0):
            # get max in derivative

            preDerivClip = filteredDeriv[spikeTime-window_pnts:spikeTime] # backwards
            postDerivClip = filteredDeriv[spikeTime:spikeTime+window_pnts] # forwards

            if len(preDerivClip) == 0:
                print('FIX ERROR: spikeDetect_dvdt()',
                        'spike', i, 'at pnt', spikeTime,
                        'window_pnts:', window_pnts,
                        'dvdtPreWindow_ms:', dDict['dvdtPreWindow_ms'],
                        'len(preDerivClip)', len(preDerivClip))#preDerivClip = np.flip(preDerivClip)

            # look for % of max in dvdt
            try:
                #peakPnt = np.argmax(preDerivClip)
                peakPnt = np.argmax(postDerivClip)
                #peakPnt += spikeTime-window_pnts
                peakPnt += spikeTime
                peakVal = filteredDeriv[peakPnt]

                percentMaxVal = peakVal * dDict['dvdt_percentOfMax'] # value we are looking for in dv/dt
                preDerivClip = np.flip(preDerivClip) # backwards
                tmpWhere = np.where(preDerivClip<percentMaxVal)
                #print('tmpWhere:', type(tmpWhere), tmpWhere)
                tmpWhere = tmpWhere[0]
                if len(tmpWhere) > 0:
                    threshPnt2 = np.where(preDerivClip<percentMaxVal)[0][0]
                    threshPnt2 = (spikeTime) - threshPnt2
                    #print('i:', i, 'spikeTime:', spikeTime, 'peakPnt:', peakPnt, 'threshPnt2:', threshPnt2)
                    threshPnt2 -= 1 # backup by 1 pnt
                    spikeTimes1.append(threshPnt2)
                    spikeErrorList1.append(None)

                else:
                    errorType = 'dvdt Percent'
                    errStr = f"Did not find dvdt_percentOfMax: {dDict['dvdt_percentOfMax']} peak dV/dt is {round(peakVal,2)}"
                    eDict = self._getErrorDict(i, spikeTime, errorType, errStr) # spikeTime is in pnts
                    spikeErrorList1.append(eDict)
                    # always append, do not REJECT spike if we can't find % in dv/dt
                    spikeTimes1.append(spikeTime)
            except (IndexError, ValueError) as e:
                ##
                print('   FIX ERROR: bAnalysis.spikeDetect_dvdt() looking for dvdt_percentOfMax')
                print('      ', 'IndexError for spike', i, spikeTime)
                print('      ', e)
                # always append, do not REJECT spike if we can't find % in dv/dt
                spikeTimes1.append(spikeTime)

        return spikeTimes1, spikeErrorList1

    def _spikeDetect_vm(self, dDict, sweepNumber, verbose=False):
        """
        spike detect using Vm threshold and NOT dvdt
        append each threshold crossing (e.g. a spike) in self.spikeTimes list

        Returns:
            self.spikeTimes (pnts): the time before each threshold crossing when dv/dt crosses 15% of its max
            self.filteredVm:
            self.filtereddVdt:
        """

        filteredVm = self.filteredVm
        Is=np.where(filteredVm>dDict['mvThreshold'])[0] # returns boolean array
        Is=np.concatenate(([0],Is))
        Ds=Is[:-1]-Is[1:]+1
        spikeTimes0 = Is[np.where(Ds)[0]+1]

        #
        # reduce spike times based on start/stop
        if dDict['startSeconds'] is not None and dDict['stopSeconds'] is not None:
            startPnt = self.dataPointsPerMs * (dDict['startSeconds']*1000) # seconds to pnt
            stopPnt = self.dataPointsPerMs * (dDict['stopSeconds']*1000) # seconds to pnt
            tmpSpikeTimes = [spikeTime for spikeTime in spikeTimes0 if (spikeTime>=startPnt and spikeTime<=stopPnt)]
            spikeTimes0 = tmpSpikeTimes

        spikeErrorList = [None] * len(spikeTimes0)

        #
        # throw out all spikes that are below a threshold Vm (usually below -20 mV)
        #spikeTimes0 = [spikeTime for spikeTime in spikeTimes0 if self.abf.sweepY[spikeTime] > self.mvThreshold]
        # 20190623 - already done in this vm threshold funtion
        '''
        peakWindow_ms = 10
        peakWindow_pnts = self.abf.dataPointsPerMs * peakWindow_ms
        goodSpikeTimes = []
        for spikeTime in spikeTimes0:
            peakVal = np.max(self.abf.sweepY[spikeTime:spikeTime+peakWindow_pnts])
            if peakVal > self.mvThreshold:
                goodSpikeTimes.append(spikeTime)
        spikeTimes0 = goodSpikeTimes
        '''

        #
        # throw out spike that are NOT upward deflections of Vm
        tmpLastGoodSpike_pnts = None
        #minISI_pnts = 5000 # at 20 kHz this is 0.25 sec
        minISI_ms = 75 #250
        minISI_pnts = self.ms2Pnt_(minISI_ms)

        prePntUp = 10 # pnts
        goodSpikeTimes = []
        goodSpikeErrors = []
        sweepY = self.sweepY
        for tmpIdx, spikeTime in enumerate(spikeTimes0):
            tmpFuckPreClip = sweepY[spikeTime-prePntUp:spikeTime]  # not including the stop index
            tmpFuckPostClip = sweepY[spikeTime+1:spikeTime+prePntUp+1]  # not including the stop index
            preAvg = np.average(tmpFuckPreClip)
            postAvg = np.average(tmpFuckPostClip)
            if postAvg > preAvg:
                tmpSpikeTimeSec = self.pnt2Sec_(spikeTime)
                if tmpLastGoodSpike_pnts is not None and (spikeTime-tmpLastGoodSpike_pnts) < minISI_pnts:
                    continue
                goodSpikeTimes.append(spikeTime)
                goodSpikeErrors.append(spikeErrorList[tmpIdx])
                tmpLastGoodSpike_pnts = spikeTime
            else:
                tmpSpikeTimeSec = self.pnt2Sec_(spikeTime)

        # todo: add this to spikeDetect_dvdt()
        goodSpikeTimes, goodSpikeErrors = self._throwOutRefractory(goodSpikeTimes, goodSpikeErrors, refractory_ms=dDict['refractory_ms'])
        spikeTimes0 = goodSpikeTimes
        spikeErrorList = goodSpikeErrors

        #
        return spikeTimes0, spikeErrorList

    def spikeDetect(self, detectionClass=None):
        """
        Spike Detect all sweeps.

        When we are instantiated we create a default self.detectionClass

        Each spike is a row and has 'sweep'

        Args:
            detectionClass (sanpy.bDetection.detectionPresets)
        """

        rememberSweep = self.currentSweep  # This is BAD we are mixing analysis with interface !!!

        startTime = time.time()

        if detectionClass is None:
            detectionClass = self.detectionClass
        else:
            self.detectionClass = detectionClass

        #
        # todo: ask user if they want to remove their settings for (isBad, userType)
        #

        if self.detectionClass['verbose']:
            logger.info('=== detectionClass is:')
            for k in self.detectionClass.keys():
                v = self.detectionClass[k]
                print(f'  {k} value:"{v}" is type {type(v)}')

        self._isAnalyzed = True

        self.spikeDict = sanpy.bAnalysisResults.analysisResultList()
         # we are filling this in, one dict for each spike
        #self.spikeDict = [] # we are filling this in, one dict for each spike

        for sweepNumber in self.sweepList:
            #self.setSweep(sweep)
            self.spikeDetect2__(sweepNumber, dDict=self.detectionClass)

        #
        self.setSweep(rememberSweep)

        stopTime = time.time()

        if detectionClass['verbose']:
            logger.info(f'Detected {len(self.spikeDict)} spikes in {round(stopTime-startTime,3)} seconds')

    def spikeDetect2__(self, sweepNumber, dDict):
        """
        Working on using bAnalysisResult.py.

        Args:
            sweepNumber:
            dDict: Detection Dict
        """
        # a list of dict of sanpy.bAnalysisResults.analysisResult (one dict per spike)
        spikeDict = sanpy.bAnalysisResults.analysisResultList()
        # append one spike
        #arl.appendDefault()

        #dDict['verbose'] = True

        verbose = dDict['verbose']
        
        '''
        verbose = False
        if dDict['verbose']:
            verbose = True
            logger.info('=== dDict is:')
            for k in dDict.keys():
                value = dDict[k]
                print(f'  {k} value:"{value}" is type {type(value)}')
        '''

        #
        self.setSweep(sweepNumber)
        #

        # in case dDict has new filter values
        self.rebuildFiltered()

        #
        # spike detect
        detectionType = dDict['detectionType']
        #logger.info(f'detectionType: "{detectionType}')

        # detect all spikes either with dvdt or mv
        if detectionType == sanpy.bDetection.detectionTypes['mv'].value:
            # detect using mV threshold
            spikeTimes, spikeErrorList = self._spikeDetect_vm(dDict, sweepNumber)

            # TODO: get rid of this and replace with foot
            # backup childish vm threshold
            if dDict['doBackupSpikeVm']:
                spikeTimes = self._backupSpikeVm(spikeTimes, sweepNumber, dDict['medianFilter'])
        elif detectionType == sanpy.bDetection.detectionTypes['dvdt'].value:
            # detect using dv/dt threshold AND min mV
            spikeTimes, spikeErrorList = self._spikeDetect_dvdt(dDict, sweepNumber)
        else:
            logger.error(f'Unknown detection type "{detectionType}"')
            return

        #
        # backup thrshold to zero crossing in dvdt
        if 0:
            tmp_window_ms = dDict['dvdtPreWindow_ms']
            tmp_window_pnts = self.ms2Pnt_(tmp_window_ms)
            spikeTimes = self._getFeet(spikeTimes, tmp_window_pnts)

        #
        # set up
        sweepX = self.sweepX  # sweepNumber is not optional
        filteredVm = self.filteredVm  # sweepNumber is not optional
        filteredDeriv = self.filteredDeriv
        sweepC = self.sweepC

        #
        now = datetime.datetime.now()
        dateStr = now.strftime('%Y-%m-%d %H:%M:%S')
        self.dateAnalyzed = dateStr

        #
        # look in a window after each threshold crossing to get AP peak
        peakWindow_pnts = self.ms2Pnt_(dDict['peakWindow_ms'])

        #
        # throw out spikes that have peak BELOW onlyPeaksAbove_mV
        # throw out spikes that have peak ABOVE onlyPeaksBelow_mV
        onlyPeaksAbove_mV = dDict['onlyPeaksAbove_mV']
        onlyPeaksBelow_mV = dDict['onlyPeaksBelow_mV']
        spikeTimes,spikeErrorList, newSpikePeakPnt, newSpikePeakVal \
                         = throwOutAboveBelow_(filteredVm,
                                spikeTimes, spikeErrorList,
                                peakWindow_pnts,
                                onlyPeaksAbove_mV=onlyPeaksAbove_mV,
                                onlyPeaksBelow_mV=onlyPeaksBelow_mV)

        #
        # small window to average Vm to calculate MDP (itself in a window before spike)
        avgWindow_pnts = self.ms2Pnt_(dDict['avgWindow_ms'])
        avgWindow_pnts = math.floor(avgWindow_pnts/2)

        #
        # for each spike
        numSpikes = len(spikeTimes)
        for i, spikeTime in enumerate(spikeTimes):
            # spikeTime units is ALWAYS points

            # new, add a spike dict for this spike time
            spikeDict.appendDefault()

            # get the AP peak
            peakPnt = newSpikePeakPnt[i]
            peakVal = newSpikePeakVal[i]
            peakSec = (newSpikePeakPnt[i] / self.dataPointsPerMs) / 1000

            # create one spike dictionary
            #spikeDict = OrderedDict() # use OrderedDict so Pandas output is in the correct order

            #spikeDict[i]['isBad'] = False
            spikeDict[i]['analysisVersion'] = sanpy.analysisVersion
            spikeDict[i]['interfaceVersion'] = sanpy.interfaceVersion
            spikeDict[i]['file'] = self.getFileName()

            spikeDict[i]['detectionType'] = detectionType

            spikeDict[i]['cellType'] = dDict['cellType']
            spikeDict[i]['sex'] = dDict['sex']
            spikeDict[i]['condition'] = dDict['condition']

            spikeDict[i]['sweep'] = sweepNumber
            # keep track of per sweep spike and total spike
            spikeDict[i]['sweepSpikeNumber'] = i
            spikeDict[i]['spikeNumber'] = i  # self.numSpikes

            spikeDict[i]['include'] = True

            # todo: make this a byte encoding so we can have multiple user tyes per spike
            spikeDict[i]['userType'] = 0  # One userType (int) that can have values

            # using bAnalysisResults will already be []
            spikeDict[i]['errors'] = []

            # append existing spikeErrorList from spikeDetect_dvdt() or spikeDetect_mv()
            tmpError = spikeErrorList[i]
            if tmpError is not None and tmpError != np.nan:
                spikeDict[i]['errors'].append(tmpError) # tmpError is from:
                if verbose:
                    print(f'  spike:{i} error:{tmpError}')
            #
            # detection params
            spikeDict[i]['dvdtThreshold'] = dDict['dvdtThreshold']
            spikeDict[i]['mvThreshold'] = dDict['mvThreshold']
            spikeDict[i]['medianFilter'] = dDict['medianFilter']
            spikeDict[i]['halfHeights'] = dDict['halfHeights']

            spikeDict[i]['thresholdPnt'] = spikeTime
            spikeDict[i]['thresholdSec'] = (spikeTime / self.dataPointsPerMs) / 1000
            spikeDict[i]['thresholdVal'] = filteredVm[spikeTime] # in vm
            spikeDict[i]['thresholdVal_dvdt'] = filteredDeriv[spikeTime] # in dvdt, spikeTime is points

            # DAC command at the precise spike point
            spikeDict[i]['dacCommand'] = sweepC[spikeTime]  # spikeTime is in points

            spikeDict[i]['peakPnt'] = peakPnt
            spikeDict[i]['peakSec'] = peakSec
            spikeDict[i]['peakVal'] = peakVal

            spikeDict[i]['peakHeight'] = spikeDict[i]['peakVal'] - spikeDict[i]['thresholdVal']

            tmpThresholdSec = spikeDict[i]['thresholdSec']
            spikeDict[i]['timeToPeak_ms'] = (peakSec - tmpThresholdSec) * 1000
            #
            # only append to spikeDict after we are done (accounting for spikes within a sweep)
            # was this
            #self.spikeDict.append(spikeDict)
            #iIdx = len(self.spikeDict) - 1
            #
            #

            iIdx = i

            #
            # was this, assigning default

            # todo: get rid of this
            defaultVal = float('nan')

            '''
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
            '''

            #
            mdp_ms = dDict['mdp_ms']
            mdp_pnts = self.ms2Pnt_(mdp_ms)  # mdp_ms * self.dataPointsPerMs
            mdp_pnts = int(mdp_pnts)

            # pre spike min
            # other algorithms look between spike[i-1] and spike[i]
            # here we are looking in a predefined window
            startPnt = spikeTimes[i]-mdp_pnts
            if startPnt < 0:
                logger.info('TODO: add an official warning, we went past 0 for pre spike mdp ms window')
                startPnt = 0
            preRange = filteredVm[startPnt:spikeTimes[i]] # EXCEPTION
            preMinPnt = np.argmin(preRange)
            preMinPnt += startPnt
            # the pre min is actually an average around the real minima
            avgRange = filteredVm[preMinPnt-avgWindow_pnts:preMinPnt+avgWindow_pnts]
            preMinVal = np.average(avgRange)

            # search backward from spike to find when vm reaches preMinVal (avg)
            preRange = filteredVm[preMinPnt:spikeTimes[i]]
            preRange = np.flip(preRange) # we want to search backwards from peak
            try:
                preMinPnt2 = np.where(preRange<preMinVal)[0][0]
                preMinPnt = spikeTimes[i] - preMinPnt2
                spikeDict[iIdx]['preMinPnt'] = preMinPnt
                spikeDict[iIdx]['preMinVal'] = preMinVal

            except (IndexError) as e:
                errorType = 'Pre spike min (mdp)'
                errorStr = 'Did not find preMinVal: ' + str(round(preMinVal,3)) #+ ' postRange min:' + str(np.min(postRange)) + ' max ' + str(np.max(postRange))
                eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr) # spikeTime is in pnts
                spikeDict[iIdx]['errors'].append(eDict)
                if verbose:
                    print(f'  spike:{iIdx} error:{eDict}')
                    
            #
            # The nonlinear late diastolic depolarization phase was
            # estimated as the duration between 1% and 10% dV/dt
            # linear fit on 10% - 50% of the time from preMinPnt to self.spikeTimes[i]
            startLinearFit = 0.1 # percent of time between pre spike min and AP peak
            stopLinearFit = 0.5 #
            timeInterval_pnts = spikeTimes[i] - preMinPnt
            # taking round() so we always get an integer # points
            preLinearFitPnt0 = preMinPnt + round(timeInterval_pnts * startLinearFit)
            preLinearFitPnt1 = preMinPnt + round(timeInterval_pnts * stopLinearFit)
            preLinearFitVal0 = filteredVm[preLinearFitPnt0]
            preLinearFitVal1 = filteredVm[preLinearFitPnt1]

            # linear fit before spike
            spikeDict[iIdx]['preLinearFitPnt0'] = preLinearFitPnt0
            spikeDict[iIdx]['preLinearFitPnt1'] = preLinearFitPnt1
            spikeDict[iIdx]['earlyDiastolicDuration_ms'] = self.pnt2Ms_(preLinearFitPnt1 - preLinearFitPnt0)
            spikeDict[iIdx]['preLinearFitVal0'] = preLinearFitVal0
            spikeDict[iIdx]['preLinearFitVal1'] = preLinearFitVal1

            # a linear fit where 'm,b = np.polyfit(x, y, 1)'
            # m*x+b"
            xFit = sweepX[preLinearFitPnt0:preLinearFitPnt1]  # abb added +1
            yFit = filteredVm[preLinearFitPnt0:preLinearFitPnt1]

            # sometimes xFit/yFit have 0 length -->> TypeError
            #print(f' {iIdx} preLinearFitPnt0:{preLinearFitPnt0}, preLinearFitPnt1:{preLinearFitPnt1}')
            #print(f'    xFit:{len(xFit)} yFit:{len(yFit)}')

            # TODO: I need to trigger following errors to confirm code works !!!!
            with warnings.catch_warnings():
                warnings.filterwarnings('error')
                try:
                    mLinear, bLinear = np.polyfit(xFit, yFit, 1) # m is slope, b is intercept
                    spikeDict[iIdx]['earlyDiastolicDurationRate'] = mLinear
                    # todo: make an error if edd rate is too low
                    lowestEddRate = dDict['lowEddRate_warning']  #8
                    if mLinear <= lowestEddRate:
                        errorType = 'Fit EDD'
                        errorStr = f'Early diastolic duration rate fit - Too low {round(mLinear,3)}<={lowestEddRate}'
                        eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr) # spikeTime is in pnts
                        #print('fit edd start num error:', 'iIdx:', iIdx, 'num error:', len(spikeDict[iIdx]['errors']))
                        spikeDict[iIdx]['errors'].append(eDict)
                        #print('  after num error:', len(spikeDict[iIdx]['errors']))
                        if verbose:
                            print(f'  spike:{iIdx} error:{eDict}')

                except (TypeError) as e:
                    #catching exception:  expected non-empty vector for x
                    # xFit/yFit turn up empty when mdp and TOP points are within 1 point
                    spikeDict[iIdx]['earlyDiastolicDurationRate'] = defaultVal
                    errorType = 'Fit EDD'
                    #errorStr = 'Early diastolic duration rate fit - TypeError'
                    errorStr = 'Early diastolic duration rate fit - preMinPnt == spikePnt'
                    eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr)
                    spikeDict[iIdx]['errors'].append(eDict)
                    if verbose:
                        print(f'  spike:{iIdx} error:{eDict}')
                except (np.RankWarning) as e:
                    #logger.error('== FIX preLinearFitPnt0/preLinearFitPnt1 RankWarning')
                    #logger.error(f'  error is: {e}')
                    #print('RankWarning')
                    # also throws: RankWarning: Polyfit may be poorly conditioned
                    spikeDict[iIdx]['earlyDiastolicDurationRate'] = defaultVal
                    errorType = 'Fit EDD'
                    errorStr = 'Early diastolic duration rate fit - RankWarning'
                    eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr)
                    spikeDict[iIdx]['errors'].append(eDict)
                    if verbose:
                        print(f'  spike:{iIdx} error:{eDict}')
                except:
                    logger.error(f' !!!!!!!!!!!!!!!!!!!!!!!!!!! UNKNOWN EXCEPTION DURING EDD LINEAR FIT for spike {i}')
                    spikeDict[iIdx]['earlyDiastolicDurationRate'] = defaultVal
                    errorType = 'Fit EDD'
                    errorStr = 'Early diastolic duration rate fit - Unknown Exception'
                    eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr)
                    if verbose:
                        print(f'  spike:{iIdx} error:{eDict}')

            # not implemented
            #self.spikeDict[i]['lateDiastolicDuration'] = ???

            #
            # maxima in dv/dt before spike (between TOP and peak)
            try:
                preRange = filteredDeriv[spikeTimes[i]:peakPnt+1]
                preSpike_dvdt_max_pnt = np.argmax(preRange)
                preSpike_dvdt_max_pnt += spikeTimes[i]
                spikeDict[iIdx]['preSpike_dvdt_max_pnt'] = preSpike_dvdt_max_pnt
                spikeDict[iIdx]['preSpike_dvdt_max_val'] = filteredVm[preSpike_dvdt_max_pnt] # in units mV
                spikeDict[iIdx]['preSpike_dvdt_max_val2'] = filteredDeriv[preSpike_dvdt_max_pnt] # in units mV
            except (ValueError) as e:
                # sometimes preRange is empty, don't try and put min/max in error
                errorType = 'Pre Spike dvdt'
                errorStr = 'Searching for dvdt max - ValueError'
                eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr) # spikeTime is in pnts
                spikeDict[iIdx]['errors'].append(eDict)
                if verbose:
                    print(f'  spike:{iIdx} error:{eDict}')

            #
            # minima in dv/dt after spike
            #postRange = dvdt[self.spikeTimes[i]:postMinPnt]
            #postSpike_ms = 20 # 10
            #postSpike_pnts = self.ms2Pnt_(postSpike_ms)
            dvdtPostWindow_ms = dDict['dvdtPostWindow_ms']
            dvdtPostWindow_pnts = self.ms2Pnt_(dvdtPostWindow_ms)
            postRange = filteredDeriv[peakPnt:peakPnt+dvdtPostWindow_pnts] # fixed window after spike

            postSpike_dvdt_min_pnt = np.argmin(postRange)
            postSpike_dvdt_min_pnt += peakPnt
            spikeDict[iIdx]['postSpike_dvdt_min_pnt'] = postSpike_dvdt_min_pnt
            spikeDict[iIdx]['postSpike_dvdt_min_val'] = filteredVm[postSpike_dvdt_min_pnt]
            spikeDict[iIdx]['postSpike_dvdt_min_val2'] = filteredDeriv[postSpike_dvdt_min_pnt]

            #
            # diastolic duration was defined as the interval between MDP and TOP
            # one off error when preMinPnt is not defined
            spikeDict[iIdx]['diastolicDuration_ms'] = self.pnt2Ms_(spikeTime - preMinPnt)

            #
            # calculate instantaneous spike frequency and ISI, for first spike this is not defined
            spikeDict[iIdx]['cycleLength_ms'] = float('nan')
            if i > 0:
                isiPnts = spikeDict[iIdx]['thresholdPnt'] - spikeDict[iIdx-1]['thresholdPnt']
                isi_ms = self.pnt2Ms_(isiPnts)
                isi_hz = 1 / (isi_ms / 1000)
                spikeDict[iIdx]['isi_pnts'] = isiPnts
                spikeDict[iIdx]['isi_ms'] = self.pnt2Ms_(isiPnts)
                spikeDict[iIdx]['spikeFreq_hz'] = 1 / (self.pnt2Ms_(isiPnts) / 1000)

                # Cycle length was defined as the interval between MDPs in successive APs
                prevPreMinPnt = spikeDict[iIdx-1]['preMinPnt'] # can be nan
                thisPreMinPnt = spikeDict[iIdx]['preMinPnt']
                if prevPreMinPnt is not None and thisPreMinPnt is not None:
                    cycleLength_pnts = thisPreMinPnt - prevPreMinPnt
                    spikeDict[iIdx]['cycleLength_pnts'] = cycleLength_pnts
                    spikeDict[iIdx]['cycleLength_ms'] = self.pnt2Ms_(cycleLength_pnts)
                else:
                    # error
                    prevPreMinSec = self.pnt2Sec_(prevPreMinPnt)
                    thisPreMinSec = self.pnt2Sec_(thisPreMinPnt)
                    #errorStr = f'Previous spike preMinPnt is {prevPreMinPnt} and this preMinPnt: {thisPreMinPnt}'
                    errorType = 'Cycle Length'
                    errorStr = f'Previous spike preMinPnt (s) is {prevPreMinSec} and this preMinPnt: {thisPreMinSec}'
                    eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr) # spikeTime is in pnts
                    spikeDict[iIdx]['errors'].append(eDict)
                    if verbose:
                        print(f'  spike:{iIdx} error:{eDict}')

            #
            # TODO: Move half-width to a function !!!
            #
            hwWindowPnts = dDict['halfWidthWindow_ms'] * self.dataPointsPerMs
            hwWindowPnts = round(hwWindowPnts)
            halfHeightList = dDict['halfHeights']
            # was this
            #self._getHalfWidth(filteredVm, i, iIdx, spikeTime, peakPnt, hwWindowPnts, self.dataPointsPerMs, halfHeightList)
            self._getHalfWidth(filteredVm, iIdx, spikeDict, spikeTime, peakPnt, hwWindowPnts, self.dataPointsPerMs, halfHeightList, verbose=verbose)

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
        #print('=== addind', len(spikeDict))
        self.spikeDict.appendAnalysis(spikeDict)
        #print('   now have', len(self.spikeDict))

        #print(self.spikeDict)

        #
        # generate a df holding stats (used by scatterplotwidget)
        startSeconds = dDict['startSeconds']
        stopSeconds = dDict['stopSeconds']
        if self.numSpikes > 0:
            exportObject = sanpy.bExport(self)
            self.dfReportForScatter = exportObject.report(startSeconds, stopSeconds)
        else:
            self.dfReportForScatter = None

        self.dfError = self.errorReport()

        self._detectionDirty = True  # e.g. bAnalysis needs to be saved

        # run all user analysis ... what if this fails ???
        #sanpy.user_analysis.baseUserAnalysis.runAllUserAnalysis(self)
        sanpy.user_analysis.baseUserAnalysis.runAllUserAnalysis(self)

        ## done

    #def _getFeet(self, df):
    def _getFeet(self, thresholdPnts : list[int], prePnts : int) -> list[int]:
        """
        
        Args:
            thresholdPnts (list of int)
            prePnts (int): pre point window to search for zero crossing

        Notes:
            Will need to calculate new (height, half widths)
        """

        #prePnts = int(prePnts)
        
        logger.info(f'num thresh:{len(thresholdPnts)} prePnts:{prePnts}')

        #df = self.asDataFrame()
        #peaks = df['peakVal']
        #thresholdPnts = df['thresholdPnt']

        verbose = self.detectionClass['verbose']

        # using the derivstive to find zero crossing before
        # original full width left point
        # TODO: USer self.filteredDeriv
        #yFull = self.filteredVm
        #yDiffFull = np.diff(yFull)
        #yDiffFull = np.insert(yDiffFull, 0, np.nan)
        yDiffFull = self.filteredDeriv

        secondDeriv = np.diff(yDiffFull, axis=0)
        secondDeriv = np.insert(secondDeriv, 0, np.nan)

        n = len(thresholdPnts)
        footPntList = [None] * n
        footSec = [None] * n  # not used
        yFoot = [None] * n  # not used
        #myHeight = []

        # todo: add this to bAnalysis
        #preMs = self._detectionParams['preFootMs']
        #prePnts = self._sec2Pnt(preMs/1000)

        # TODO: add to bDetection
        logger.warning('ADD preMs AS PARAMETER !!!')
        #preWinMs = 50  # sa-node
        #prePnts = self.ms2Pnt_(preMs)

        for idx,footPnt in enumerate(thresholdPnts):
            #footPnt = round(footPnt)  # footPnt is in fractional points
            lastCrossingPnt = footPnt
            # move forwared a bit in case we are already in a local minima ???
            logger.warning('REMOVED WHEN WORKING ON NEURON DETECTION')
            footPnt += 2  # TODO: add as param
            preStart = footPnt - prePnts
            preClip = yDiffFull[preStart:footPnt]

            zero_crossings = np.where(np.diff(np.sign(preClip)))[0]  # find where derivative flips sign (crosses 0)
            xLastCrossing = self.pnt2Sec_(footPnt)  # defaults
            yLastCrossing = self.sweepY_filtered[footPnt]
            if len(zero_crossings)==0:
                if verbose:
                    tmpSec = round(self.pnt2Sec_(footPnt), 3)
                    logger.error(f'  no foot for peak {idx} at sec {tmpSec} ... did not find zero crossings')
            else:
                #print(idx, 'footPnt:', footPnt, zero_crossings, preClip)
                lastCrossingPnt = preStart + zero_crossings[-1]
                xLastCrossing = self.pnt2Sec_(lastCrossingPnt)
                # get y-value (pA) from filtered. This removes 'pops' in raw data
                yLastCrossing = self.sweepY_filtered[lastCrossingPnt]


            # find peak in second derivative
            '''
            preStart2 = lastCrossingPnt
            footMs2 = 20
            footPnt2 = preStart2 + self.ms2Pnt_(footMs2)
            preClip2 = secondDeriv[preStart2:footPnt2]
            #zero_crossings = np.where(np.diff(np.sign(preClip2)))[0]
            peakPnt2 = np.argmax(preClip2)
            peakPnt2 += preStart2

            #
            footPntList[idx] = peakPnt2
            '''

            footPntList[idx] = lastCrossingPnt # was this and worked, a bit too early

            footSec[idx] = xLastCrossing
            yFoot[idx] = yLastCrossing

            '''
            peakPnt = df.loc[idx, 'peak_pnt']
            peakVal = self.sweepY_filtered[peakPnt]
            height = peakVal - yLastCrossing
            #print(f'idx {idx} {peakPnt} {peakVal} - {yLastCrossing} = {height}')
            myHeight[idx] = (height)
            '''

        #
        #df =self._analysisList[self._analysisIdx]['results_full']
        '''
        df['foot_pnt'] = footPntList  # sec
        df['foot_sec'] = footSec  # sec
        df['foot_val'] = yFoot  # pA
        '''
        #df['myHeight'] = myHeight

        #return footPntList, footSec, yFoot
        return footPntList

    def printSpike(self, idx):
        """
        Print values in one spike analysis using self.spikeDict (sanpy.bAnalysisResults).
        """
        spike = self.spikeDict[idx]
        for k,v in spike.items():
            if k == 'widths':
                widths = v
                print(f'  spike:{idx} has {len(widths)} widths...')
                for wIdx, width in enumerate(widths):
                    print(f'    spike:{idx} width:{wIdx}: {width}')
            elif k == 'errors':
                errors = v
                print(f'  spike:{idx} has {len(errors)} errors...')
                for eIdx, error in enumerate(errors):
                    print(f'    spike:{idx} error #:{eIdx}: {error}')
            else:
                print(f'{k}: {v}')

    def printErrors(self):
        for idx, spike in enumerate(self.spikeDict):
            print(f"spike {idx} has {len(spike['errors'])} errors")
            for eIdx, error in enumerate(spike['errors']):
                print(f'  error # {eIdx} is: {error}')

    def old_spikeDetect__(self, sweepNumber, dDict):
        """
        Spike detect the current sweep and put results into list of dict `self.spikeDict[]`.

        Args:
            dDict (bDetection): A detection class/dictionary from [bDetection()][sanpy.bDetection]
        """

        verbose = True

        if dDict['verbose']:
            logger.info('dDict is:')
            for k in dDict.keys():
                value = dDict[k]
                print(f'  {k}: {type(value)} "{value}"')

        #
        self.setSweep(sweepNumber)
        #

        # in case dDict has new filter values
        self.rebuildFiltered()

        #
        # spike detect
        detectionType = dDict['detectionType']
        #logger.info(f'detectionType: "{detectionType}')

        # detect all spikes either with dvdt or mv
        if detectionType == sanpy.bDetection.detectionTypes.mv:
            # detect using mV threshold
            spikeTimes, spikeErrorList = self._spikeDetect_vm(dDict, sweepNumber)

            # backup childish vm threshold
            if dDict['doBackupSpikeVm']:
                #self.spikeTimes = self._backupSpikeVm(dDict['medianFilter'])
                spikeTimes = self._backupSpikeVm(spikeTimes, sweepNumber, dDict['medianFilter'])
        elif detectionType == sanpy.bDetection.detectionTypes.dvdt:
            # detect using dv/dt threshold AND min mV
            spikeTimes, spikeErrorList = self._spikeDetect_dvdt(dDict, sweepNumber)
        else:
            logger.error(f'Unknown detection type "{detectionType}"')
            return

        #
        # set up
        sweepX = self.sweepX  # sweepNumber is not optional
        filteredVm = self.filteredVm  # sweepNumber is not optional
        filteredDeriv = self.filteredDeriv
        sweepC = self.sweepC

        #
        now = datetime.datetime.now()
        dateStr = now.strftime('%Y-%m-%d %H:%M:%S')
        self.dateAnalyzed = dateStr

        #
        # look in a window after each threshold crossing to get AP peak
        peakWindow_pnts = self.ms2Pnt_(dDict['peakWindow_ms'])

        #
        # throw out spikes that have peak BELOW onlyPeaksAbove_mV
        # throw out spikes that have peak ABOVE onlyPeaksBelow_mV
        onlyPeaksAbove_mV = dDict['onlyPeaksAbove_mV']
        onlyPeaksBelow_mV = dDict['onlyPeaksBelow_mV']
        spikeTimes,spikeErrorList, newSpikePeakPnt, newSpikePeakVal \
                         = throwOutAboveBelow_(filteredVm,
                                spikeTimes, spikeErrorList,
                                peakWindow_pnts,
                                onlyPeaksAbove_mV=onlyPeaksAbove_mV,
                                onlyPeaksBelow_mV=onlyPeaksBelow_mV)

        #
        # small window to average Vm to calculate MDP (itself in a window before spike)
        avgWindow_pnts = self.ms2Pnt_(dDict['avgWindow_ms'])
        avgWindow_pnts = math.floor(avgWindow_pnts/2)

        #
        # for each spike
        numSpikes = len(spikeTimes)
        for i, spikeTime in enumerate(spikeTimes):
            # spikeTime units is ALWAYS points

            # get the AP peak
            '''
            peakPnt = np.argmax(filteredVm[spikeTime:spikeTime+peakWindow_pnts])
            peakPnt += spikeTime
            peakVal = np.max(filteredVm[spikeTime:spikeTime+peakWindow_pnts])
            '''
            peakPnt = newSpikePeakPnt[i]
            peakVal = newSpikePeakVal[i]
            peakSec = (newSpikePeakPnt[i] / self.dataPointsPerMs) / 1000

            #
            # todo: break this out into a configuration file with
            # {
            #    'name': analysisVersion,
            #    'type': 'str',
            #    'description': 'The analysis version'
            # }

            # create one spike dictionary
            spikeDict = OrderedDict() # use OrderedDict so Pandas output is in the correct order

            #spikeDict['isBad'] = False
            spikeDict['analysisVersion'] = sanpy.analysisVersion
            spikeDict['interfaceVersion'] = sanpy.interfaceVersion
            spikeDict['file'] = self.getFileName()

            spikeDict['detectionType'] = detectionType

            spikeDict['cellType'] = dDict['cellType']
            spikeDict['sex'] = dDict['sex']
            spikeDict['condition'] = dDict['condition']

            spikeDict['sweep'] = sweepNumber
            # keep track of per sweep spike and total spike
            spikeDict['sweepSpikeNumber'] = i
            spikeDict['spikeNumber'] = i  # self.numSpikes

            spikeDict['include'] = True

            # todo: make this a byte encoding so we can have multiple user tyes per spike
            spikeDict['userType'] = 0  # One userType (int) that can have values

            #spikeDict['userType2'] = False
            #spikeDict['userType3'] = False

            spikeDict['errors'] = []
            # append existing spikeErrorList from spikeDetect_dvdt() or spikeDetect_mv()
            tmpError = spikeErrorList[i]
            if tmpError is not None and tmpError != np.nan:
                #spikeDict['numError'] += 1
                spikeDict['errors'].append(tmpError) # tmpError is from:
                #eDict = self._getErrorDict(i, spikeTime, errType, errStr) # spikeTime is in pnts

            #
            # detection params
            spikeDict['dvdtThreshold'] = dDict['dvdtThreshold']
            spikeDict['mvThreshold'] = dDict['mvThreshold']
            spikeDict['medianFilter'] = dDict['medianFilter']
            spikeDict['halfHeights'] = dDict['halfHeights']

            spikeDict['thresholdPnt'] = spikeTime
            spikeDict['thresholdSec'] = (spikeTime / self.dataPointsPerMs) / 1000
            spikeDict['thresholdVal'] = filteredVm[spikeTime] # in vm
            spikeDict['thresholdVal_dvdt'] = filteredDeriv[spikeTime] # in dvdt, spikeTime is points

            # DAC command at the precise spike point
            spikeDict['dacCommand'] = sweepC[spikeTime]  # spikeTime is in points

            spikeDict['peakPnt'] = peakPnt
            spikeDict['peakSec'] = peakSec
            spikeDict['peakVal'] = peakVal

            spikeDict['peakHeight'] = spikeDict['peakVal'] - spikeDict['thresholdVal']

            #
            # only append to spikeDict after we are done (accounting for spikes within a sweep)
            self.spikeDict.append(spikeDict)
            iIdx = len(self.spikeDict) - 1
            #
            #

            defaultVal = float('nan')

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
            self.spikeDict[iIdx]['widths'] = []
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
                self.spikeDict[iIdx]['widths_' + str(halfHeight)] = defaultVal
                self.spikeDict[iIdx]['widths'].append(widthDict)

            #
            mdp_ms = dDict['mdp_ms']
            mdp_pnts = self.ms2Pnt_(mdp_ms)  # mdp_ms * self.dataPointsPerMs
            mdp_pnts = int(mdp_pnts)

            # pre spike min
            # other algorithms look between spike[i-1] and spike[i]
            # here we are looking in a predefined window
            startPnt = spikeTimes[i]-mdp_pnts
            if startPnt < 0:
                logger.info('TODO: add an official warning, we went past 0 for pre spike mdp ms window')
                startPnt = 0
            preRange = filteredVm[startPnt:spikeTimes[i]] # EXCEPTION
            preMinPnt = np.argmin(preRange)
            preMinPnt += startPnt
            # the pre min is actually an average around the real minima
            avgRange = filteredVm[preMinPnt-avgWindow_pnts:preMinPnt+avgWindow_pnts]
            preMinVal = np.average(avgRange)

            # search backward from spike to find when vm reaches preMinVal (avg)
            preRange = filteredVm[preMinPnt:spikeTimes[i]]
            preRange = np.flip(preRange) # we want to search backwards from peak
            try:
                preMinPnt2 = np.where(preRange<preMinVal)[0][0]
                preMinPnt = spikeTimes[i] - preMinPnt2
                self.spikeDict[iIdx]['preMinPnt'] = preMinPnt
                self.spikeDict[iIdx]['preMinVal'] = preMinVal

            except (IndexError) as e:
                errorType = 'Pre spike min (mdp)'
                errorStr = 'Did not find preMinVal: ' + str(round(preMinVal,3)) #+ ' postRange min:' + str(np.min(postRange)) + ' max ' + str(np.max(postRange))
                eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr) # spikeTime is in pnts
                self.spikeDict[iIdx]['errors'].append(eDict)

            #
            # The nonlinear late diastolic depolarization phase was
            # estimated as the duration between 1% and 10% dV/dt
            # linear fit on 10% - 50% of the time from preMinPnt to self.spikeTimes[i]
            startLinearFit = 0.1 # percent of time between pre spike min and AP peak
            stopLinearFit = 0.5 #
            timeInterval_pnts = spikeTimes[i] - preMinPnt
            # taking round() so we always get an integer # points
            preLinearFitPnt0 = preMinPnt + round(timeInterval_pnts * startLinearFit)
            preLinearFitPnt1 = preMinPnt + round(timeInterval_pnts * stopLinearFit)
            preLinearFitVal0 = filteredVm[preLinearFitPnt0]
            preLinearFitVal1 = filteredVm[preLinearFitPnt1]

            # linear fit before spike
            self.spikeDict[iIdx]['preLinearFitPnt0'] = preLinearFitPnt0
            self.spikeDict[iIdx]['preLinearFitPnt1'] = preLinearFitPnt1
            self.spikeDict[iIdx]['earlyDiastolicDuration_ms'] = self.pnt2Ms_(preLinearFitPnt1 - preLinearFitPnt0)
            self.spikeDict[iIdx]['preLinearFitVal0'] = preLinearFitVal0
            self.spikeDict[iIdx]['preLinearFitVal1'] = preLinearFitVal1

            # a linear fit where 'm,b = np.polyfit(x, y, 1)'
            # m*x+b"
            xFit = sweepX[preLinearFitPnt0:preLinearFitPnt1]  # abb added +1
            yFit = filteredVm[preLinearFitPnt0:preLinearFitPnt1]

            # sometimes xFit/yFit have 0 length -->> TypeError
            #print(f' {iIdx} preLinearFitPnt0:{preLinearFitPnt0}, preLinearFitPnt1:{preLinearFitPnt1}')
            #print(f'    xFit:{len(xFit)} yFit:{len(yFit)}')

            with warnings.catch_warnings():
                warnings.filterwarnings('error')
                try:
                    mLinear, bLinear = np.polyfit(xFit, yFit, 1) # m is slope, b is intercept
                    self.spikeDict[iIdx]['earlyDiastolicDurationRate'] = mLinear
                    # todo: make an error if edd rate is too low
                    lowestEddRate = dDict['lowEddRate_warning']  #8
                    if mLinear <= lowestEddRate:
                        errorType = 'Fit EDD'
                        errorStr = 'Early diastolic duration rate fit - Too low'
                        eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr) # spikeTime is in pnts
                        self.spikeDict[iIdx]['errors'].append(eDict)

                except (TypeError) as e:
                    #catching exception:  expected non-empty vector for x
                    # xFit/yFit turn up empty when mdp and TOP points are within 1 point
                    '''
                    print('!!!!!! ERROR is e:', e)
                    print ('  xFit:', xFit)
                    print ('  yFit:', yFit)
                    print('  preLinearFitPnt0:', preLinearFitPnt0)
                    print('  preLinearFitPnt1:', preLinearFitPnt1)
                    '''
                    self.spikeDict[iIdx]['earlyDiastolicDurationRate'] = defaultVal
                    errorType = 'Fit EDD'
                    #errorStr = 'Early diastolic duration rate fit - TypeError'
                    errorStr = 'Early diastolic duration rate fit - preMinPnt == spikePnt'
                    eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr)
                    self.spikeDict[iIdx]['errors'].append(eDict)
                except (np.RankWarning) as e:
                    #logger.error('== FIX preLinearFitPnt0/preLinearFitPnt1 RankWarning')
                    #logger.error(f'  error is: {e}')
                    #print('RankWarning')
                    # also throws: RankWarning: Polyfit may be poorly conditioned
                    self.spikeDict[iIdx]['earlyDiastolicDurationRate'] = defaultVal
                    errorType = 'Fit EDD'
                    errorStr = 'Early diastolic duration rate fit - RankWarning'
                    eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr)
                    self.spikeDict[iIdx]['errors'].append(eDict)
                except:
                    logger.error(f' !!!!!!!!!!!!!!!!!!!!!!!!!!! UNKNOWN EXCEPTION DURING EDD LINEAR FIT for spike {i}')
                    self.spikeDict[iIdx]['earlyDiastolicDurationRate'] = defaultVal
                    errorType = 'Fit EDD'
                    errorStr = 'Early diastolic duration rate fit - Unknown Exception'
                    eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr)

            # not implemented
            #self.spikeDict[i]['lateDiastolicDuration'] = ???

            #
            # maxima in dv/dt before spike (between TOP and peak)
            try:
                preRange = filteredDeriv[spikeTimes[i]:peakPnt+1]
                preSpike_dvdt_max_pnt = np.argmax(preRange)
                preSpike_dvdt_max_pnt += spikeTimes[i]
                self.spikeDict[iIdx]['preSpike_dvdt_max_pnt'] = preSpike_dvdt_max_pnt
                self.spikeDict[iIdx]['preSpike_dvdt_max_val'] = filteredVm[preSpike_dvdt_max_pnt] # in units mV
                self.spikeDict[iIdx]['preSpike_dvdt_max_val2'] = filteredDeriv[preSpike_dvdt_max_pnt] # in units mV
            except (ValueError) as e:
                #self.spikeDict[iIdx]['numError'] = self.spikeDict[iIdx]['numError'] + 1
                # sometimes preRange is empty, don't try and put min/max in error
                errorType = 'Pre Spike dvdt'
                errorStr = 'Searching for dvdt max - ValueError'
                eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr) # spikeTime is in pnts
                self.spikeDict[iIdx]['errors'].append(eDict)

            #
            # minima in dv/dt after spike
            #postRange = dvdt[self.spikeTimes[i]:postMinPnt]
            #postSpike_ms = 20 # 10
            #postSpike_pnts = self.ms2Pnt_(postSpike_ms)
            dvdtPostWindow_ms = dDict['dvdtPostWindow_ms']
            dvdtPostWindow_pnts = self.ms2Pnt_(dvdtPostWindow_ms)
            postRange = filteredDeriv[peakPnt:peakPnt+dvdtPostWindow_pnts] # fixed window after spike

            postSpike_dvdt_min_pnt = np.argmin(postRange)
            postSpike_dvdt_min_pnt += peakPnt
            self.spikeDict[iIdx]['postSpike_dvdt_min_pnt'] = postSpike_dvdt_min_pnt
            self.spikeDict[iIdx]['postSpike_dvdt_min_val'] = filteredVm[postSpike_dvdt_min_pnt]
            self.spikeDict[iIdx]['postSpike_dvdt_min_val2'] = filteredDeriv[postSpike_dvdt_min_pnt]

            #
            # diastolic duration was defined as the interval between MDP and TOP
            # one off error when preMinPnt is not defined
            self.spikeDict[iIdx]['diastolicDuration_ms'] = self.pnt2Ms_(spikeTime - preMinPnt)

            #
            # calculate instantaneous spike frequency and ISI
            self.spikeDict[iIdx]['cycleLength_ms'] = float('nan')
            if i > 0:
                isiPnts = self.spikeDict[iIdx]['thresholdPnt'] - self.spikeDict[iIdx-1]['thresholdPnt']
                isi_ms = self.pnt2Ms_(isiPnts)
                isi_hz = 1 / (isi_ms / 1000)
                self.spikeDict[iIdx]['isi_pnts'] = isiPnts
                self.spikeDict[iIdx]['isi_ms'] = self.pnt2Ms_(isiPnts)
                self.spikeDict[iIdx]['spikeFreq_hz'] = 1 / (self.pnt2Ms_(isiPnts) / 1000)

                # Cycle length was defined as the interval between MDPs in successive APs
                prevPreMinPnt = self.spikeDict[iIdx-1]['preMinPnt'] # can be nan
                thisPreMinPnt = self.spikeDict[iIdx]['preMinPnt']
                if prevPreMinPnt is not None and thisPreMinPnt is not None:
                    cycleLength_pnts = thisPreMinPnt - prevPreMinPnt
                    self.spikeDict[iIdx]['cycleLength_pnts'] = cycleLength_pnts
                    self.spikeDict[iIdx]['cycleLength_ms'] = self.pnt2Ms_(cycleLength_pnts)
                else:
                    # error
                    prevPreMinSec = self.pnt2Sec_(prevPreMinPnt)
                    thisPreMinSec = self.pnt2Sec_(thisPreMinPnt)
                    #errorStr = f'Previous spike preMinPnt is {prevPreMinPnt} and this preMinPnt: {thisPreMinPnt}'
                    errorType = 'Cycle Length'
                    errorStr = f'Previous spike preMinPnt (s) is {prevPreMinSec} and this preMinPnt: {thisPreMinSec}'
                    eDict = self._getErrorDict(i, spikeTimes[i], errorType, errorStr) # spikeTime is in pnts
                    self.spikeDict[iIdx]['errors'].append(eDict)

            #
            # TODO: Move half-width to a function !!!
            #
            hwWindowPnts = dDict['halfWidthWindow_ms'] * self.dataPointsPerMs
            hwWindowPnts = round(hwWindowPnts)
            halfHeightList = dDict['halfHeights']
            self._getHalfWidth(filteredVm, i, iIdx, spikeTime, peakPnt, hwWindowPnts, self.dataPointsPerMs, halfHeightList)
            #for i in range(1):
            #    self.spikeDict[iIdx]['widths_'+str(halfHeight)] = widthMs
            #    self.spikeDict[iIdx]['widths'][j] = widthDict

        #
        # look between threshold crossing to get minima
        # we will ignore the first and last spike

        #
        # spike clips
        self.spikeClips = None
        self.spikeClips_x = None
        self.spikeClips_x2 = None

        #
        # generate a df holding stats (used by scatterplotwidget)
        startSeconds = dDict['startSeconds']
        stopSeconds = dDict['stopSeconds']
        if self.numSpikes > 0:
            exportObject = sanpy.bExport(self)
            self.dfReportForScatter = exportObject.report(startSeconds, stopSeconds)
        else:
            self.dfReportForScatter = None

        self.dfError = self.errorReport()

        self._detectionDirty = True  # e.g. bAnalysis needs to be saved

        # done

    def _makeSpikeClips(self, preSpikeClipWidth_ms, postSpikeClipWidth_ms=None, theseTime_sec=None, sweepNumber=None):
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

        verbose = self.detectionClass['verbose']

        if preSpikeClipWidth_ms is None:
            preSpikeClipWidth_ms = self.detectionClass['preSpikeClipWidth_ms']
        if postSpikeClipWidth_ms is None:
            postSpikeClipWidth_ms = self.detectionClass['postSpikeClipWidth_ms']

        if sweepNumber is None:
            sweepNumber = 'All'

        #print('makeSpikeClips() spikeClipWidth_ms:', spikeClipWidth_ms, 'theseTime_sec:', theseTime_sec)
        if theseTime_sec is None:
            theseTime_pnts = self.getSpikeTimes(sweepNumber=sweepNumber)
        else:
            # convert theseTime_sec to pnts
            theseTime_ms = [x*1000 for x in theseTime_sec]
            theseTime_pnts = [x*self.dataPointsPerMs for x in theseTime_ms]
            theseTime_pnts = [round(x) for x in theseTime_pnts]

        preClipWidth_pnts = self.ms2Pnt_(preSpikeClipWidth_ms)
        #if preClipWidth_pnts % 2 == 0:
        #    pass # Even
        #else:
        #    clipWidth_pnts += 1 # Make odd even
        postClipWidth_pnts = self.ms2Pnt_(postSpikeClipWidth_ms)

        #halfClipWidth_pnts = int(clipWidth_pnts/2)

        #print('  makeSpikeClips() clipWidth_pnts:', clipWidth_pnts, 'halfClipWidth_pnts:', halfClipWidth_pnts)
        # make one x axis clip with the threshold crossing at 0
        # was this, in ms
        #self.spikeClips_x = [(x-halfClipWidth_pnts)/self.dataPointsPerMs for x in range(clipWidth_pnts)]

        # in ms
        self.spikeClips_x = [(x-preClipWidth_pnts)/self.dataPointsPerMs for x in range(preClipWidth_pnts)]
        self.spikeClips_x += [(x)/self.dataPointsPerMs for x in range(postClipWidth_pnts)]

        #20190714, added this to make all clips same length, much easier to plot in MultiLine
        numPointsInClip = len(self.spikeClips_x)

        self.spikeClips = []
        self.spikeClips_x2 = []

        sweepY = self.sweepY_filtered

        # when there are no spikes getStat() will not return anything
        sweepNum = self.getStat('sweep', sweepNumber=sweepNumber)  # For 'All' sweeps, we need to know column

        #logger.info(f'sweepY: {sweepY.shape} {len(sweepY.shape)}')
        #logger.info(f'theseTime_pnts: {theseTime_pnts}')

        for idx, spikeTime in enumerate(theseTime_pnts):

            sweep = sweepNum[idx]

            if len(sweepY.shape) == 1:
                # 1D case where recording has only oone sweep
                #currentClip = sweepY[spikeTime-halfClipWidth_pnts:spikeTime+halfClipWidth_pnts]
                currentClip = sweepY[spikeTime-preClipWidth_pnts:spikeTime+postClipWidth_pnts]
            else:
                # 2D case where recording has multiple sweeps
                #currentClip = sweepY[spikeTime-halfClipWidth_pnts:spikeTime+halfClipWidth_pnts, sweep]
                try:
                    currentClip = sweepY[spikeTime-preClipWidth_pnts:spikeTime+preClipWidth_pnts, sweep]
                except (IndexError) as e:
                    logger.error(e)
                    print(f'sweep: {sweep}')
                    print(f'sweepY.shape: {sweepY.shape}')

            if len(currentClip) == numPointsInClip:
                self.spikeClips.append(currentClip)
                self.spikeClips_x2.append(self.spikeClips_x) # a 2D version to make pyqtgraph multiline happy
            else:
                #pass
                if verbose:
                    logger.warning(f'Did not add clip for spike index: {idx} at time: {spikeTime} len(currentClip): {len(currentClip)} != numPointsInClip: {numPointsInClip}')

        #
        return self.spikeClips_x2, self.spikeClips

    def getSpikeClips(self, theMin, theMax, spikeSelection=[], preSpikeClipWidth_ms=None, postSpikeClipWidth_ms=None, sweepNumber=None):
        """
        Get 2d list of spike clips, spike clips x, and 1d mean spike clip

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
            theMax = self.recordingDur  # self.sweepX[-1]

        # new interface, spike detect no longer auto generates these
        # need to do this every time because we get here when sweepNumber changes
        #if self.spikeClips is None:
        #    self._makeSpikeClips(spikeClipWidth_ms=spikeClipWidth_ms, sweepNumber=sweepNumber)
        # TODO: don't make all clips
        #self._makeSpikeClips(spikeClipWidth_ms=spikeClipWidth_ms, sweepNumber=sweepNumber)
        self._makeSpikeClips(preSpikeClipWidth_ms=preSpikeClipWidth_ms, postSpikeClipWidth_ms=postSpikeClipWidth_ms, sweepNumber=sweepNumber)

        # make a list of clips within start/stop (Seconds)
        theseClips = []
        theseClips_x = []
        tmpMeanClips = [] # for mean clip
        meanClip = []
        spikeTimes = self.getSpikeTimes(sweepNumber=sweepNumber)

        #if len(spikeTimes) != len(self.spikeClips):
        #    logger.error(f'len spikeTimes {len(spikeTimes)} !=  spikeClips {len(self.spikeClips)}')

        # self.spikeClips is a list of clips
        for idx, clip in enumerate(self.spikeClips):
            doThisSpike = False
            if doSpikeSelection:
                doThisSpike = idx in spikeSelection
            else:
                spikeTime = spikeTimes[idx]
                spikeTime = self.pnt2Sec_(spikeTime)
                if spikeTime>=theMin and spikeTime<=theMax:
                    doThisSpike = True
            if doThisSpike:
                theseClips.append(clip)
                theseClips_x.append(self.spikeClips_x2[idx]) # remember, all _x are the same
                if len(self.spikeClips_x) == len(clip):
                    tmpMeanClips.append(clip) # for mean clip
        if len(tmpMeanClips):
            meanClip = np.mean(tmpMeanClips, axis=0)

        return theseClips, theseClips_x, meanClip

    def numErrors(self):
        if self.dfError is None:
            return 'N/A'
        else:
            return len(self.dfError)

    def errorReport(self):
        """
        Generate an error report, one row per error. Spikes can have more than one error.

        Returns:
            (pandas DataFrame): Pandas DataFrame, one row per error.
        """

        dictList = []

        numError = 0
        errorList = []
        for spikeIdx, spike in enumerate(self.spikeDict):
            for idx, error in enumerate(spike['errors']):
                # error is dict from _getErorDict
                if error is None or error == np.nan or error == 'nan':
                    continue
                dictList.append(error)

        if len(dictList) == 0:
            fakeErrorDict = self._getErrorDict(1, 1, 'fake', 'fake')
            dfError = pd.DataFrame(columns=fakeErrorDict.keys())
        else:
            dfError = pd.DataFrame(dictList)

        #print('bAnalysis.errorReport() returning len(dfError):', len(dfError))
        if self.detectionClass['verbose']:
            logger.info(f'Found {len(dfError)} errors in spike detection')

        #
        return dfError

    def save_csv(self):
        """
        Save as a CSV text file with name <path>_analysis.csv'

        TODO: Fix
        TODO: We need to save header with xxx
        TODO: Load <path>_analysis.csv
        """
        savefile = os.path.splitext(self._path)[0]
        savefile += '_analysis.csv'
        saveExcel = False
        alsoSaveTxt = True
        logger.info(f'Saving "{savefile}"')

        be = sanpy.bExport(self)
        be.saveReport(savefile, saveExcel=saveExcel, alsoSaveTxt=alsoSaveTxt)

    def pnt2Sec_(self, pnt):
        """
        Convert a point to Seconds using `self.dataPointsPerMs`

        Args:
            pnt (int): The point

        Returns:
            float: The point in seconds
        """
        if pnt is None:
            #return math.isnan(pnt)
            return math.nan
        else:
            return pnt / self.dataPointsPerMs / 1000

    def pnt2Ms_(self, pnt):
        """
        Convert a point to milliseconds (ms) using `self.dataPointsPerMs`

        Args:
            pnt (int): The point

        Returns:
            float: The point in milliseconds (ms)
        """
        return pnt / self.dataPointsPerMs

    def ms2Pnt_(self, ms):
        """
        Convert milliseconds (ms) to point in recording using `self.dataPointsPerMs`

        Args:
            ms (float): The ms into the recording

        Returns:
            int: The point in the recording
        """
        theRet = ms * self.dataPointsPerMs
        #theRet = int(theRet)
        theRet = round(theRet)
        return theRet

    def _normalizeData(self, data):
        """
        Used to calculate normalized data for detection from Kymograph. Is NOT for df/d0.
        """
        return (data - np.min(data)) / (np.max(data) - np.min(data))

    def loadAnalysis(self):
        """
        Not used.
        """
        saveBase = self._getSaveBase()

        # load detection parameters
        #self.detectionClass.load(saveBase)

        # load analysis
        #self.spikeDict.load(saveBase)

        saveBase = self._getSaveBase()
        savePath = saveBase + '-analysis.json'

        if not os.path.isfile(savePath):
            #logger.error(f'Did not find file: {savePath}')
            return

        logger.info(f'Loading from saved analysis: {savePath}')

        with open(savePath, 'r') as f:
            #self._dDict = json.load(f)
            loadedDict = json.load(f)

        dDict = loadedDict['detection']
        self.detectionClass._dDict = dDict

        analysisList = loadedDict['analysis']
        self.spikeDict._myList = analysisList

        self._detectionDirty = False
        self._isAnalyzed = True

    def saveAnalysis(self, forceSave=False):
        """Not used.
        """
        if not self._detectionDirty and not forceSave:
            return

        saveFolder = self._getSaveFolder()
        if not os.path.isdir(saveFolder):
            logger.info(f'making folder: {saveFolder}')
            os.mkdir(saveFolder)

        saveBase = self._getSaveBase()
        savePath = saveBase + '-analysis.json'

        # save detection parameters
        #self.detectionClass.save(saveBase)
        dDict = self.detectionClass.getDict()

        saveDict = {}
        saveDict['detection'] = dDict

        # save list of dict
        #self.spikeDict = sanpy.bAnalysisResults.analysisResultList()
        #self.spikeDict.save(saveBase)
        analysisList = self.spikeDict.asList()

        saveDict['analysis'] = analysisList

        with open(savePath, 'w') as f:
            json.dump(saveDict, f, cls=NumpyEncoder, indent=4)

        self._detectionDirty = False

        logger.info(f'Saved analysis to: {savePath}')

    def _getSaveFolder(self):
        """
        All analysis will be saved in folder 'sanpy_analysis'
        """
        parentPath, fileName = os.path.split(self._path)
        saveFolder = os.path.join(parentPath, 'sanpy_analysis')
        return saveFolder

    def _getSaveBase(self):
        """
        Return basename to append to to save

        This will always be in a subfolder named 'sanpy_analysis'

        For example, bDetection uses this to save <base>-detection.json
        """
        saveFolder = self._getSaveFolder()

        parentPath, fileName = os.path.split(self._path)
        baseName = os.path.splitext(fileName)[0]
        savePath = os.path.join(saveFolder, baseName)

        return savePath

    def api_getHeader(self):
        """
        Get header as a dict.

        TODO:
            - add info on abf file, like samples per ms

        Returns:
            dict: Dictionary of information about loaded file.
        """
        #recordingDir_sec = len(self.sweepX) / self.dataPointsPerMs / 1000
        recordingFrequency = self.dataPointsPerMs

        ret = {
            'myFileType': self.myFileType, # ('abf', 'tif', 'bytestream', 'csv')
            'loadError': self.loadError,
            #'detectionDict': self.detectionClass,
            'path': self._path,
            'file': self.getFileName(),
            'dateAnalyzed': self.dateAnalyzed,
            #'detectionType': self.detectionType,
            'acqDate': self.acqDate,
            'acqTime': self.acqTime,
            #
            '_recordingMode': self._recordingMode,
            'get_yUnits': self.get_yUnits(),
            #'currentSweep': self.currentSweep,
            'recording_kHz': recordingFrequency,
            'recordingDur_sec': self.recordingDur
        }
        return ret

    def api_getSpikeInfo(self, spikeNum=None):
        """
        Get info about each spike.

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

    def api_getSpikeStat(self, stat):
        """
        Get stat for each spike

        Args:
            stat (str): The name of the stat to get. Corresponds to key in self.spikeDict[i].

        Returns:
            list: List of values for 'stat'. Ech value is for one spike.
        """
        statList = self.getStat(statName1=stat, statName2=None)
        return statList

    def api_getRecording(self):
        """
        Return primary recording

        Returns:
            dict: {'header', 'sweepX', 'sweepY'}

        TODO:
            Add param to only get every n'th point, to return a subset faster (for display)
        """
        #start = time.time()
        ret = {
            'header': self.api_getHeader(),
            'sweepX': self.sweepX2.tolist(),
            'sweepY': self.sweepY2.tolist(),
        }
        #stop = time.time()
        #print(stop-start)
        return ret

    def donotuse_openHeaderInBrowser(self):
        """Open abf file header in browser. Only works for actual abf files."""
        #ba.abf.headerLaunch()
        if self.abf is None:
            return
        import webbrowser
        logFile = sanpy.sanpyLogger.getLoggerFile()
        htmlFile = os.path.splitext(logFile)[0] + '.html'
        #print('htmlFile:', htmlFile)
        html = pyabf.abfHeaderDisplay.abfInfoPage(self.abf).generateHTML()
        with open(htmlFile, 'w') as f:
            f.write(html)
        webbrowser.open('file://' + htmlFile)

class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

def _test_load_abf():
    path = '/Users/cudmore/data/dual-lcr/20210115/data/21115002.abf'
    ba = bAnalysis(path)

    dvdtThreshold = 30
    mvThreshold = -20
    halfWidthWindow_ms = 60 # was 20
    ba.spikeDetect(dvdtThreshold=dvdtThreshold, mvThreshold=mvThreshold,
        halfWidthWindow_ms=halfWidthWindow_ms
        )
        #avgWindow_ms=avgWindow_ms,
        #window_ms=window_ms,
        #peakWindow_ms=peakWindow_ms,
        #refractory_ms=refractory_ms,
        #dvdt_percentOfMax=dvdt_percentOfMax)

    test_plot(ba)

    return ba

def _test_load_tif(path):
    """
    working on spike detection from sum of intensities along a line scan
    see: example/lcr-analysis
    """

    # text file with 2x columns (seconds, vm)

    #path = '/Users/Cudmore/Desktop/caInt.csv'

    #path = '/Users/cudmore/data/dual-lcr/20210115/data/20210115__0001.tif'

    ba = bAnalysis(path)
    ba.getDerivative()

    #print('ba.abf.sweepX:', len(ba.abf.sweepX))
    #print('ba.abf.sweepY:', len(ba.abf.sweepY))

    #print('ba.abf.sweepX:', ba.abf.sweepX)
    #print('ba.abf.sweepY:', ba.abf.sweepY)

    # Ca recording is ~40 times slower than e-phys at 10 kHz
    mvThreshold = 0.5
    dvdtThreshold = 0.01
    refractory_ms = 60 # was 20 ms
    avgWindow_ms=60 # pre-roll to find eal threshold crossing
        # was 5, in detect I am using avgWindow_ms/2 ???
    window_ms = 20 # was 2
    peakWindow_ms = 70 # 20 gives us 5, was 10
    dvdt_percentOfMax = 0.2 # was 0.1
    halfWidthWindow_ms = 60 # was 20
    ba.spikeDetect(dvdtThreshold=dvdtThreshold, mvThreshold=mvThreshold,
        avgWindow_ms=avgWindow_ms,
        window_ms=window_ms,
        peakWindow_ms=peakWindow_ms,
        refractory_ms=refractory_ms,
        dvdt_percentOfMax=dvdt_percentOfMax,
        halfWidthWindow_ms=halfWidthWindow_ms
        )

    for k,v in ba.spikeDict[0].items():
        print('  ', k, ':', v)

    test_plot(ba)

    return ba

def _test_plot(ba, firstSampleTime=0):
    #firstSampleTime = ba.abf.sweepX[0] # is not 0 for 'wait for trigger' FV3000

    # plot
    fig, axs = plt.subplots(2, 1, sharex=True)

    #
    # dv/dt
    xDvDt = ba.abf.sweepX + firstSampleTime
    yDvDt = ba.abf.filteredDeriv + firstSampleTime
    axs[0].plot(xDvDt, yDvDt, 'k')

    # thresholdVal_dvdt
    xThresh = [x['thresholdSec'] + firstSampleTime for x in ba.spikeDict]
    yThresh = [x['thresholdVal_dvdt'] for x in ba.spikeDict]
    axs[0].plot(xThresh, yThresh, 'or')

    axs[0].spines['right'].set_visible(False)
    axs[0].spines['top'].set_visible(False)

    #
    # vm with detection params
    axs[1].plot(ba.abf.sweepX, ba.abf.sweepY, 'k-', lw=0.5)

    xThresh = [x['thresholdSec'] + firstSampleTime for x in ba.spikeDict]
    yThresh = [x['thresholdVal'] for x in ba.spikeDict]
    axs[1].plot(xThresh, yThresh, 'or')

    xPeak = [x['peakSec'] + firstSampleTime for x in ba.spikeDict]
    yPeak = [x['peakVal'] for x in ba.spikeDict]
    axs[1].plot(xPeak, yPeak, 'ob')

    sweepX = ba.abf.sweepX + firstSampleTime

    for idx, spikeDict in enumerate(ba.spikeDict):
        #
        # plot all widths
        #print('plotting width for spike', idx)
        for j,widthDict in enumerate(spikeDict['widths']):
            #for k,v in widthDict.items():
            #    print('  ', k, ':', v)
            #print('j:', j)
            if widthDict['risingPnt'] is None:
                #print('  -->> no half width')
                continue

            risingPntX = sweepX[widthDict['risingPnt']]
            # y value of rising pnt is y value of falling pnt
            #risingPntY = ba.abf.sweepY[widthDict['risingPnt']]
            risingPntY = ba.abf.sweepY[widthDict['fallingPnt']]
            fallingPntX = sweepX[widthDict['fallingPnt']]
            fallingPntY = ba.abf.sweepY[widthDict['fallingPnt']]
            fallingPnt = widthDict['fallingPnt']
            # plotting y-value of rising to match y-value of falling
            #ax.plot(ba.abf.sweepX[widthDict['risingPnt']], ba.abf.sweepY[widthDict['risingPnt']], 'ob')
            # plot as pnts
            #axs[1].plot(ba.abf.sweepX[widthDict['risingPnt']], ba.abf.sweepY[widthDict['fallingPnt']], '-b')
            #axs[1].plot(ba.abf.sweepX[widthDict['fallingPnt']], ba.abf.sweepY[widthDict['fallingPnt']], '-b')
            # line between rising and falling is ([x1, y1], [x2, y2])
            axs[1].plot([risingPntX, fallingPntX], [risingPntY, fallingPntY], color='b', linestyle='-', linewidth=2)

    axs[1].spines['right'].set_visible(False)
    axs[1].spines['top'].set_visible(False)

    #
    #plt.show()

def _lcrDualAnalysis():
    """
    for 2x files, line-scan and e-phys
    plot spike time delay of ca imaging
    """
    fileIndex = 3
    dataList[fileIndex]

    ba0 = test_load_tif(path) # image
    ba1 = test_load_abf() # recording

    # now need to get this from pClamp abf !!!
    #firstSampleTime = ba0.abf.sweepX[0] # is not 0 for 'wait for trigger' FV3000
    firstSampleTime = ba1.abf.tagTimesSec[0]
    print('firstSampleTime:', firstSampleTime)

    # for each spike in e-phys, match it with a spike in imaging
    # e-phys is shorter, fewer spikes
    numSpikes = ba1.numSpikes
    print('num spikes in recording:', numSpikes)

    thresholdSec0, peakSec0 = ba0.getStat('thresholdSec', 'peakSec')
    thresholdSec1, peakSec1 = ba1.getStat('thresholdSec', 'peakSec')

    ba1_width50, throwOut = ba1.getStat('widths_50', 'peakSec')

    # todo: add an option in bAnalysis.getStat()
    thresholdSec0 = [x + firstSampleTime for x in thresholdSec0]
    peakSec0 = [x + firstSampleTime for x in peakSec0]

    # assuming spike-detection is clean
    # truncate imaging (it is longer than e-phys)
    thresholdSec0 = thresholdSec0[0:numSpikes] # second value/max is NOT INCLUSIVE
    peakSec0 = peakSec0[0:numSpikes]

    numSubplots = 2
    fig, axs = plt.subplots(numSubplots, 1, sharex=False)

    # threshold in image starts about 20 ms after Vm
    axs[0].plot(thresholdSec1, peakSec0, 'ok')
    #axs[0].plot(thresholdSec1, 'ok')

    # draw diagonal
    axs[0].plot([0, 1], [0, 1], transform=axs[0].transAxes)

    axs[0].set_xlabel('thresholdSec1')
    axs[0].set_ylabel('peakSec0')

    #axs[1].plot(thresholdSec1, peakSec0, 'ok')

    # time to peak in image wrt AP threshold time
    caTimeToPeak = []
    for idx, thresholdSec in enumerate(thresholdSec1):
        timeToPeak = peakSec0[idx] - thresholdSec
        #print('thresholdSec:', thresholdSec, 'peakSec0:', peakSec0[idx], 'timeToPeak:', timeToPeak)
        caTimeToPeak.append(timeToPeak)

    print('caTimeToPeak:', caTimeToPeak)

    axs[1].plot(ba1_width50, caTimeToPeak, 'ok')

    # draw diagonal
    #axs[1].plot([0, 1], [0, 1], transform=axs[1].transAxes)

    axs[1].set_xlabel('ba1_width50')
    axs[1].set_ylabel('caTimeToPeak')

    #
    plt.show()

def test_load_abf():
    path = 'data/19114001.abf' # needs to be run fron SanPy
    print('=== test_load_abf() path:', path)
    ba = bAnalysis(path)

    detectionPreset = sanpy.bDetection.detectionPresets.default
    detectionClass = sanpy.bDetection(detectionPreset=detectionPreset)
    ba.spikeDetect(detectionClass=detectionClass)

    print(ba.getDetectionType(), type(ba.getDetectionType()))

    print('  ba.numSpikes:', ba.numSpikes)
    #ba.openHeaderInBrowser()

    thresholdSec = ba.getStat('thresholdSec')
    print('  thresholdSec:', thresholdSec)

def test_load_csv():
    path = 'data/19114001.csv' # needs to be run fron SanPy
    print('=== test_load_csv() path:', path)
    ba = bAnalysis(path)

    dDict = sanpy.bDetection.getDefaultDetection()
    ba.spikeDetect(dDict)

    print('  ba.numSpikes:', ba.numSpikes)

def test_save():
    path = 'data/19114001.abf' # needs to be run fron SanPy
    ba = bAnalysis(path)

    dDict = sanpy.bDetection.getDefaultDetection()
    ba.spikeDetect(dDict)

    #ba.save_csv()

def test_load_atf():
    path = '/home/cudmore/Sites/SanPy/data/atf/sin_a5.0_f7.0.atf'
    ba = bAnalysis(path)
    print(ba)
    print('sweepList:', ba.sweepList)
    print('_sweepX:', ba._sweepX.shape)
    print('dataPointsPerMs:', ba.dataPointsPerMs)
    t0 = ba.sweepX[0]
    t1 = ba.sweepX[1]
    dt = (t1 - t0) * 1000
    datapointsperms = 1 / dt
    print(t0*1000, t1*1000, dt, datapointsperms)

def main():
    import matplotlib.pyplot as plt

    test_load_atf()

    #test_load_abf()

    #test_load_csv()

    sys.exit(1)

    test_save()

    '''
    if 0:
        print('running bAnalysis __main__')
        ba = bAnalysis('../data/19114001.abf')
        print(ba.dataPointsPerMs)
    '''

    # this is to load/analyze/plot the sum of a number of Ca imaging line scans
    # e.g. lcr
    if 0:
        ba0 = test_load_tif(path) # this can load a line scan tif
        # todo: add title
        test_plot(ba0)

        ba1 = test_load_abf()
        test_plot(ba1)

        #
        plt.show()

    if 0:
        lcrDualAnalysis()

    if 0:
        path = '/Users/cudmore/Sites/SanPy/examples/dual-analysis/dual-data/20210129/2021_01_29_0007.abf'
        ba = bAnalysis(path)
        dDict = sanpy.bDetection.getDefaultDetection()
        #dDict['dvdtThreshold'] = None # detect using just Vm
        print('dDict:', dDict)
        ba.spikeDetect(dDict)
        ba.errorReport()

    if 1:
        path = 'data/19114001.abf'
        ba = bAnalysis(path)
        dDict = sanpy.bDetection.getDefaultDetection()
        #dDict['dvdtThreshold'] = None # detect using just Vm

        recordingFrequency = ba.recordingFrequency
        print('recordingFrequency:', recordingFrequency)

        ba.spikeDetect(dDict)
        ba.errorReport()

        headerDict = ba.api_getHeader()
        print('--- headerDictheaderDict')
        for k,v in headerDict.items():
            print('  ', k, ':' ,v)

        if 0:
            oneSpike = 1
            oneSpikeList = ba.api_getSpikeInfo(oneSpike)
            for idx, spikeDict in enumerate(oneSpikeList):
                print('--- oneSpikeList for oneSpike:', oneSpike, 'idx:', idx)
                for k,v in spikeDict.items():
                    print('  ', k,v)

        stat = 'peakSec'
        statList = ba.api_getSpikeStat(stat)
        print('--- stat:', stat)
        print(statList)

        recDict = ba.api_getRecording()
        print('--- recDict')
        for k,v in recDict.items():
            print('  ', k, 'len:', len(v), np.nanmean(v))

def test_hdf():
    path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
    ba = sanpy.bAnalysis(path)
    ba.spikeDetect()

def test_sweeps():
    path = '/home/cudmore/Sites/SanPy/data/tests/171116sh_0018.abf'
    ba = sanpy.bAnalysis(path)
    logger.info(ba.numSweeps)
    logger.info(ba.sweepList)

    # plot all sweeps
    import matplotlib.pyplot as plt
    numSpikes = []
    for sweepNumber in ba.abf.sweepList:
        sweepSet = ba.setSweep(sweepNumber)
        ba.spikeDetect()
        print(f'   sweepNumber:{sweepNumber} numSpikes:{ba.numSpikes} maxY:{np.nanmax(ba.sweepY)}')
        numSpikes.append(ba.numSpikes)
        offset = 0 #140*sweepNumber
        print(f'   {type(ba.abf.sweepX)}, {ba.abf.sweepX.shape}')
        plt.plot(ba.abf.sweepX, ba.abf.sweepY+offset, color='C0')
    print(f'numSpikes:{numSpikes}')
    #plt.gca().get_yaxis().set_visible(False)  # hide Y axis
    plt.xlabel(ba.abf.sweepLabelX)
    plt.show()

def test_foot():
    if 0:
        path = '/media/cudmore/data/rabbit-ca-transient/feb-8-2022/Control/20220204__0013.tif.frames/20220204__0013.tif'

        ba = bAnalysis(path)
        print(ba)

        detectionPreset= sanpy.bDetection.detectionPresets.caKymograph
        detectionClass = sanpy.bDetection(detectionPreset=detectionPreset)
        detectionClass['mvThreshold'] = 1.42
        detectionClass['doBackupSpikeVm'] = False
        detectionClass['SavitzkyGolay_pnts'] = 5
        ba.spikeDetect(detectionClass=detectionClass)

    if 1:
        path = '/media/cudmore/data/Laura-data/manuscript-data/2020_07_23_0002.abf'
        ba = bAnalysis(path)
        print(ba)

        detectionPreset= sanpy.bDetection.detectionPresets.saNode
        detectionClass = sanpy.bDetection(detectionPreset=detectionPreset)
        detectionClass['dvdtThreshold'] = 2
        detectionClass['mvThreshold'] = -20
        detectionClass['doBackupSpikeVm'] = False
        detectionClass['SavitzkyGolay_pnts'] = 5
        detectionClass['verbose'] = True
        ba.spikeDetect(detectionClass=detectionClass)

    print(ba)

    #footPntList, footSec, yFoot = ba._getFeet()
    #print('footSec:', footSec)

    thresholdSec = ba.getStat('thresholdSec')
    thresholdVal = ba.getStat('thresholdVal')

    print('thresholdSec:', thresholdSec)

    # 2nd deriv
    secondDeriv = np.diff(ba.filteredDeriv, axis=0)
    secondDeriv = np.insert(secondDeriv, 0, np.nan)

    # plot
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 1, sharex=True)

    axs[0].plot(ba.sweepX, ba.filteredDeriv, '-k', linewidth=0.5)
    axs[0].plot(ba.sweepX, secondDeriv, '-r', linewidth=0.5)
    axs[0].hlines(0, ba.sweepX[0], ba.sweepX[-1], linestyles='dashed')

    axs[1].plot(ba.sweepX, ba.sweepY, '.k', linewidth=0.5)
    #axs[1].plot(footSec, yFoot, 'or')

    axs[1].plot(thresholdSec, thresholdVal, 'ob')
    #axs[1].vlines(1.4073, np.min(ba.sweepY), np.max(ba.sweepY), linestyles='dashed')

    plt.show()

if __name__ == '__main__':
    # was using this for manuscript
    #main()
    #test_hdf()
    test_load_abf()
    #test_sweeps()

    #test_foot()
