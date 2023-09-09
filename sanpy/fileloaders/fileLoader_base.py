import os
import glob
import math
import enum
import inspect
from typing import Union, Dict, List, Tuple, Optional
from abc import ABC, abstractmethod

import numpy as np
import scipy.signal

import sanpy.fileloaders

import sanpy.metaData

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)


def getFileLoaders(verbose: bool = False) -> dict:
    """Load file loaders from both

    1) Module sanpy.fileloaders
    2) Folder <user>/Documents/SanPy/File Loaders

    Each file loader is a class derived from [fileLoader_base](../../api/fileloader/fileLoader_base.md)

    See: sanpy.interface.bPlugins.loadPlugins()

    Returns
    -------
    dict
        A dictionary of file loaders.
    """
    retDict = {}

    ignoreModuleList = ["fileLoader_base", "recordingModes", "epochTable", "hekaUtils"]

    if not sanpy.DO_KYMOGRAPH_ANALYSIS:
        ignoreModuleList.append('fileLoader_tif')
    #
    # system file loaders from sanpy.fileloaders
    loadedList = []
    for moduleName, obj in inspect.getmembers(sanpy.fileloaders):
        if inspect.isclass(obj):
            if verbose:
                logger.info(f"moduleName:{moduleName}")
            if moduleName in ignoreModuleList:
                if verbose:
                    logger.info(f'IGNORING {moduleName}')
                continue
            loadedList.append(moduleName)
            fullModuleName = "sanpy.fileloaders." + moduleName
            # filetype is a static str, e.g. the extension to load
            try:
                filetype = obj.loadFileType
            except AttributeError as e:
                logger.warning(f'Did not load "{moduleName}", no "filetype" attribute')
                continue
            oneLoaderDict = {
                "fileLoaderClass": moduleName,
                "type": "system",
                "module": fullModuleName,
                "path": "",
                "constructor": obj,
                #'filetype': filetype
            }
            if filetype in retDict.keys():
                logger.warning(
                    f'loader already added "{moduleName}" filetype:"{filetype}"'
                )
                logger.warning(f"  this loader will overwrite the previous loader.")
            retDict[filetype] = oneLoaderDict

    # logger.info(f'Loaded system file loaders:')
    # for k,v in retDict.keys():
    #     logger.info(f'    {k}:{v}')
    # # sort
    # retDict = dict(sorted(retDict.items()))

    #
    # user plugins from files in folder "<user>/SanPy/file loaders"
    fileLoaderFolder = sanpy._util._getUserFileLoaderFolder()
    loadedModuleList = []
    if os.path.isdir(fileLoaderFolder):
        files = glob.glob(os.path.join(fileLoaderFolder, "*.py"))
    else:
        # no user file loader folder ???
        files = []

    for file in files:
        if file.endswith("__init__.py"):
            continue

        moduleName = os.path.split(file)[1]
        moduleName = os.path.splitext(moduleName)[0]
        fullModuleName = "sanpy.fileloaders." + moduleName

        loadedModule = sanpy._util._module_from_file(fullModuleName, file)

        try:
            oneConstructor = getattr(loadedModule, moduleName)
        except AttributeError as e:
            logger.error(
                f'Did not load file loader, make sure file name and class name are the same:"{moduleName}"'
            )
        else:
            # filetype is a static str, e.g. the extension to load
            try:
                filetype = oneConstructor.loadFileType
            except AttributeError as e:
                logger.warning(f'Did not load "{moduleName}", no "filetype" attribute')
                continue
            oneLoaderDict = {
                "fileLoaderClass": moduleName,
                "type": "user",
                "module": fullModuleName,
                "path": file,
                "constructor": oneConstructor,
                #'filetype': filetype
            }
            if filetype in retDict.keys():
                logger.warning(
                    f'loader already added "{moduleName}" handleExtension:"{filetype}"'
                )
                logger.warning(f"  this loader will overwrite the previous loader.")
            retDict[filetype] = oneLoaderDict

    if verbose:
        logger.info(f"Loaded {len(retDict.keys())} file loaders:")
        for k, v in retDict.items():
            # logger.info(f'    {k}:{v}')
            logger.info(f"  {k}")
            for k2, v2 in v.items():
                logger.info(f"    {k2}: {v2}")

    # sort
    # retDict = dict(sorted(retDict.items()))

    return retDict


class recordingModes(enum.Enum):
    """Recording modes for I-Clamp, V-Clamp, and unknown."""

    iclamp = "I-Clamp"
    vclamp = "V-Clamp"
    kymograph = "Kymograph"
    unknown = "unknown"


class fileLoader_base(ABC):
    """Abstract base class to derive file loaders.

    For some working examples of derived classes, see
    [fileLoader_abf](../../api/fileloader/fileLoader_abf.md) and
    [fileLoader_csv](../../api/fileloader/fileLoader_csv.md)

    To create a file loader

    1) derive a class from fileLoader_base and define `loadFileType`

        class myFileLoader(fileLoader_base):
            loadFileType = 'the_file_extension_this_will_load'

    2) Define a `loadFile` function

        def loadFile(self):
            # load the data from self.filepath and create sweepX and sweepY
            # specify what was loaded
            self.setLoadedData(sweepX, sweepY)

    """

    loadFileType: str = ""
    # @property
    # @abstractmethod
    # def loadFileType(self) -> str:
    #     """Derived classes must return the file type to handle.
    #     For example, 'csv', or 'm', or 'dat'
    #     """
    #     pass

    @abstractmethod
    def loadFile(self):
        """Derived classes must load the data and call setLoadedData(sweepX, sweepY)."""
        pass

    def __init__(self, filepath: str, loadData: bool = True):
        """Base class to derive new file loaders.

        Parameters
        ----------
        filepath : str
            File path to load. Will use different derived classes based on extension
        loadData : bool
            If True then load raw data, otherwise just load the header.
        """

        super().__init__()

        self._loadError = False

        self._path = filepath

        self._metaData = sanpy.metaData.MetaData()  # per file metadata

        self._filteredY : np.ndarray = None  # set in _getDerivative
        self._filteredDeriv : np.ndarray = None
        self._currentSweep: int = 0

        self._epochTableList: List[sanpy.fileloaders.epochTable] = None

        self._sweepX = None
        self._sweepY = None
        self._sweepC = None
        self._numSweeps = None
        self._sweepList = None
        self._sweepLengthSec = None
        self._dataPointsPerMs = None
        self._recordingMode = recordingModes.unknown
        self._sweepLabelX = None
        self._sweepLabelY = None

        # load file from inherited class
        self.loadFile()

        # check our work
        self._checkLoadedData()

    def __str__(self):
        """Get a short string representing this file."""
        txt = f"file: {self.filename} sweeps: {self.numSweeps} dur (Sec):{self.recordingDur}"
        return txt

    @property
    def metadata(self):
        return self._metaData
    
    def setAcqDate(self, value):
        self.metadata.setMetaData('Acq Date', value, triggerDirty=False)

    def setAcqTime(self, value):
        self.metadata.setMetaData('Acq Time', value, triggerDirty=False)

    def getLoadError(self) -> bool:
        return self._loadError
    
    def setLoadError(self, value : bool):
        self._loadError = value

    def isKymograph(self) -> bool:
        return isinstance(self, sanpy.fileloaders.fileLoader_tif)

    @property
    def filepath(self) -> str:
        """Get the full file path."""
        return self._path

    @property
    def filename(self) -> str:
        """Get the filename."""
        if self.filepath is None:
            return None
        else:
            return os.path.split(self.filepath)[1]

    @property
    def numChannels(self) -> int:
        """Get the number of channels.

        If more than one channel, must be defined in derived class.
        """
        return 1

    @property
    def currentSweep(self) -> int:
        """Get the current sweep."""
        return self._currentSweep

    def setSweep(self, currentSweep: int):
        """Set the current sweep."""
        if currentSweep > self.numSweeps - 1:
            logger.error(f"max sweep is {self.numSweeps-1}, got {currentSweep}")
            return
        self._currentSweep = currentSweep

    @property
    def recordingMode(self):
        return self._recordingMode

    # feb 2023, uncommented
    @property
    def sweepLabelX(self):
        return self._sweepLabelX

    @property
    def sweepLabelY(self):
        return self._sweepLabelY

    @property
    def recordingDur(self):
        return self._sweepLengthSec

    @property
    def numSweeps(self):
        return len(self._sweepList)

    @property
    def sweepList(self):
        return self._sweepList

    @property
    def dataPointsPerMs(self):
        return self._dataPointsPerMs

    @property
    def acqDate(self):
        return self._acqDate

    @property
    def acqTime(self):
        return self._acqTime

    @property
    def sweepX(self):
        """Get the X-Values for a sweep.

        Notes
        -----
        All sweeps are assumed to have the same x-values (seconds).
        """
        # return self._sweepX[:, self.currentSweep]
        return self._sweepX[:, 0]

    @property
    def sweepY(self):
        """Get the Y values for the current sweep."""
        return self._sweepY[:, self.currentSweep]

    @property
    def sweepC(self):
        """Get the DAC command for the current sweep."""
        if self._sweepC is None:
            # return np.zeros_like(self._sweepX[:, self.currentSweep])
            return np.zeros_like(self._sweepX[:, 0])
        return self._sweepC[:, self.currentSweep]

    def get_xUnits(self):
        return self._sweepLabelX

    def get_yUnits(self):
        return self._sweepLabelY

    @property
    def filteredDeriv(self) -> Optional[np.ndarray]:
        """Get the filtered first derivative of sweepY."""
        if self._filteredDeriv is not None:
            return self._filteredDeriv[:, self.currentSweep]
        else:
            return None

    def _getDerivative(
        self,
        medianFilter: int = 0,
        SavitzkyGolay_pnts: int = 5,
        SavitzkyGolay_poly: int = 2,
    ):
        """Get filtered version of recording and derivative of recording (used for I-Clamp).

            By default we will use a SavitzkyGolay filter with 5 points and a 2nd order polynomial.

        Parameters
        ----------
        medianFilter : int
            Median filter box with. Must be odd, specify 0 for no median filter
        SavitzkyGolay_pnts : int
            Specify 0 for no filter.
        SavitzkyGolay_poly : int

        Notes
        -----
        Creates:
            self._filteredVm
            self._filteredDeriv
        """

        # logger.info(f'{self.filename} medianFilter:{medianFilter} SavitzkyGolay_pnts:{SavitzkyGolay_pnts} SavitzkyGolay_poly:{SavitzkyGolay_poly}')

        if not isinstance(medianFilter, int):
            logger.error(f"expecting int medianFilter, got: {medianFilter}")

        if medianFilter > 0:
            if not medianFilter % 2:
                medianFilter += 1
                logger.warning(
                    "Please use an odd value for the median filter, set medianFilter: {medianFilter}"
                )
            medianFilter = int(medianFilter)
            self._filteredY = scipy.signal.medfilt2d(self._sweepY, [medianFilter, 1])
        elif SavitzkyGolay_pnts > 0:
            self._filteredY = scipy.signal.savgol_filter(
                self._sweepY,
                SavitzkyGolay_pnts,
                SavitzkyGolay_poly,
                axis=0,
                mode="nearest",
            )
        else:
            self._filteredY = self.sweepY

        self._filteredDeriv = np.diff(self._filteredY, axis=0)

        # filter the derivative
        if medianFilter > 0:
            if not medianFilter % 2:
                medianFilter += 1
                print(
                    f"Please use an odd value for the median filter, set medianFilter: {medianFilter}"
                )
            medianFilter = int(medianFilter)
            self._filteredDeriv = scipy.signal.medfilt2d(
                self._filteredDeriv, [medianFilter, 1]
            )
        elif SavitzkyGolay_pnts > 0:
            self._filteredDeriv = scipy.signal.savgol_filter(
                self._filteredDeriv,
                SavitzkyGolay_pnts,
                SavitzkyGolay_poly,
                axis=0,
                mode="nearest",
            )
        else:
            # self._filteredDeriv = self.filteredDeriv
            pass

        # mV/ms
        dataPointsPerMs = self.dataPointsPerMs
        self._filteredDeriv = self._filteredDeriv * dataPointsPerMs  # / 1000

        # insert an initial point (rw) so it is the same length as raw data in abf.sweepY
        # three options (concatenate, insert, vstack), could only get vstack working
        rowOfZeros = np.zeros(self.numSweeps)

        # logger.info(f' dataPointsPerMs:{dataPointsPerMs}')
        # logger.info(f' self.numSweeps:{self.numSweeps}')
        # logger.info(f' rowOfZeros:{rowOfZeros.shape}')
        # logger.info(f' 1 - _filteredDeriv:{self._filteredDeriv.shape}')

        # rowZero = 0
        self._filteredDeriv = np.vstack([rowOfZeros, self._filteredDeriv])

        # logger.info(f'  sweepX:{self.sweepX.shape}')
        # logger.info(f'  sweepY:{self.sweepY.shape}')
        # logger.info(f'  _filteredY:{self._filteredY.shape}')
        # logger.info(f'  2- _filteredDeriv:{self._filteredDeriv.shape}')

        return self._filteredDeriv
    
    @property
    def sweepY_filtered(self) -> np.ndarray:
        """Get a filtered version of sweepY."""
        if self._filteredY is not None:
            return self._filteredY[:, self.currentSweep]

    @property
    def recordingFrequency(self) -> int:
        """Convenience for dataPointsPerMs, recording frequency in kHz."""
        return self.dataPointsPerMs

    def pnt2Sec_(self, pnt: int) -> float:
        """Convert a point to seconds using dataPointsPerMs.

        Parameters
        ----------
        pnt : int

        Returns
        -------
        float
            The point in seconds (s)
        """
        if pnt is None:
            # return math.isnan(pnt)
            return math.nan
        else:
            return pnt / self.dataPointsPerMs / 1000

    def pnt2Ms_(self, pnt: int) -> float:
        """
        Convert a point to milliseconds (ms) using `self.dataPointsPerMs`

        Parameters
        ----------
        pnt : int

        Returns
        -------
        float
            The point in milliseconds (ms)
        """
        return pnt / self.dataPointsPerMs

    def ms2Pnt_(self, ms: float) -> int:
        """
        Convert milliseconds (ms) to point in recording using `self.dataPointsPerMs`

        Parameters
        ----------
        ms : float
            The ms into the recording

        Returns
        -------
        int
            The point in the recording corresponding to ms
        """
        theRet = ms * self.dataPointsPerMs
        theRet = round(theRet)
        return theRet

    def getEpochTable(self, sweep: int):
        """Only proper abf files will have an epoch table.

        TODO: Make all file loders have an epoch table.
            Make API so derived file loaders can create their own
        """
        if self._epochTableList is not None:
            return self._epochTableList[sweep]
        else:
            return None

    @property
    def numEpochs(self) -> Optional[int]:
        """Get the number of epochs.

        Epochs are mostly for pClamp abf files. We are assuming each sweep has the same namber of epochs.
        """
        if self._epochTableList is not None:
            return self._epochTableList[0].numEpochs()

    def _checkLoadedData(self):
        # TODO: check all the member vraiables are correct
        # set error if they are not
        pass
    
    def setLoadedData(
        self,
        sweepX: np.ndarray,
        sweepY: np.ndarray,
        sweepC: Optional[np.ndarray] = None,
        recordingMode: recordingModes = recordingModes.iclamp,
        xLabel: str = "",
        yLabel: str = "",
    ):
        """Derived classes call this function once the data is loaded in loadFile().

        Parameters
        ----------
        sweepX : np.ndarray
            Time values
        sweepY : np.ndarray
            Recording values, mV or pA
        sweepC : np.ndarray
            (optional) DAC stimulus, pA or mV
        recordingMode : recordingModes
            (optional) Defaults to recordingModes.iclamp)
        xLabel : str
            (optional) str for x-axis label
        yLabel : str
            (optional) str for y-axis label

        Notes
        -----
        - Number of sweeps: sweepY.shape[1]
        - Sweep Length (sec): sweepX[-1,0]
        - Data Points Per Millisecond: 1 / ((sweepX[1,0] - sweepX[0,0]) * 1000)
        """
        self._sweepX = sweepX
        self._sweepY = sweepY
        self._sweepC = sweepC

        self._numSweeps: int = self._sweepY.shape[1]
        self._sweepList: List[int] = list(range(self._numSweeps))

        self._sweepLengthSec: float = self._sweepX[-1, 0]  # from 0 to last sample point

        dtSeconds = self._sweepX[1, 0] - self._sweepX[0, 0]  # seconds per sample
        dtSeconds = float(dtSeconds)
        dtMilliseconds = dtSeconds * 1000
        # july 2023 paula
        # _dataPointsPerMs = int(1 / dtMilliseconds)
        _dataPointsPerMs = 1 / dtMilliseconds
        
        if _dataPointsPerMs == 0:
            logger.error(f'_dataPointsPerMs is zero!')
            logger.error(f'  dtSeconds:{dtSeconds}')
            logger.error(f'  dtMilliseconds:{dtMilliseconds}')
            logger.error(f'  _dataPointsPerMs = int(1 / dtMilliseconds)')

        self._dataPointsPerMs: int = _dataPointsPerMs

        self._recordingMode: recordingModes = recordingMode
        self._sweepLabelX: str = xLabel
        self._sweepLabelY: str = yLabel

if __name__ == "__main__":
    d = getFileLoaders()
    # for k,v in d.items():
    #     print(k,v)
