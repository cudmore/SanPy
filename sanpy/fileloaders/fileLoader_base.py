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
from sanpy.config import DO_KYMOGRAPH_ANALYSIS

import sanpy.metaData
from sanpy.fileloaders.fileMetadata import FileMetadata
from sanpy.sanpyPaths import SanPyPaths

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)


def getFileLoaders(verbose: bool = False) -> dict:
    """Return built-in and optionally external recording file loaders.

    Args:
        verbose: Whether to log details about registered file loaders.

    Returns:
        File-loader definitions keyed by supported file extension.
    """
    retDict = {}

    ignoreModuleList = [
        "fileLoader_base",
        "recordingModes",
        "epochTable",
        "FileMetadata",
        "hekaUtils",
    ]

    if not DO_KYMOGRAPH_ANALYSIS:
        ignoreModuleList.append('fileLoader_tif')
    #
    # system file loaders from sanpy.fileloaders
    loadedList = []
    for moduleName, obj in inspect.getmembers(sanpy.fileloaders):
        if inspect.isclass(obj):
            # if verbose:
            #     logger.info(f"moduleName:{moduleName}")
            if moduleName in ignoreModuleList:
                # if verbose:
                #     logger.info(f'IGNORING {moduleName}')
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
    fileLoaderFolder = SanPyPaths().file_loader_dir
    # loadedModuleList = []
    if (
        sanpy._util.ALLOW_USER_CODE_IMPORTS
        and fileLoaderFolder.is_dir()
    ):
        files = glob.glob(str(fileLoaderFolder / "*.py"))
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

        logger.info(filepath)

        self._loadError = False

        self._path = filepath

        self._metaData = sanpy.metaData.MetaData()  # per file metadata

        self._sweep_conditions: Dict[int, str] = {}
        self._sweep_conditions_dirty: bool = False

        self._fileMetadata: Optional[FileMetadata] = None
        self._acqDate: str = ""
        self._acqTime: str = ""
        self._acqDateTime: str = ""

        self._filteredY : np.ndarray = None  # set in _getDerivative
        self._filteredDeriv : np.ndarray = None
        self._currentSweep: int = 0

        self._epochTableList: List[sanpy.fileloaders.epochTable] = None

        self._sweepX = None
        self._sweepY = None
        self._sweepC = None
        self._numSweeps: Optional[int] = None
        self._sweepList = None
        self._sweepLengthSec = None
        self._dataPointsPerMs: Optional[float] = None
        self._recordingMode = recordingModes.unknown
        self._userList: Optional[List[float]] = None  # 20240123 owlanalysis
        self._numChannels: int = 1
        self._sweepLabelX = None
        self._sweepLabelY = None

        # load file from inherited class
        self.loadFile()

        if not self._loadError:
            for sweep in self._sweepList:
                self._sweep_conditions.setdefault(sweep, "")
            self._finalizeFileMetadata()

        # check our work
        self._checkLoadedData()

    def __str__(self) -> str:
        """Get a short string representing this file."""
        num_sweeps = (
            len(self._sweepList) if self._sweepList is not None else "unavailable"
        )
        txt = (
            f"file: {self.filename} sweeps: {num_sweeps} "
            f"dur (Sec):{self.recordingDur}"
        )
        return txt

    @property
    def metadata(self) -> sanpy.metaData.MetaData:
        """Return mutable experimental metadata for the recording."""
        return self._metaData

    @property
    def fileMetadata(self) -> FileMetadata:
        """Return immutable metadata read or derived from the source file.

        Returns:
            Finalized metadata for the loaded recording.

        Raises:
            RuntimeError: If the loader did not complete successfully.
        """
        if self._fileMetadata is None:
            raise RuntimeError("File metadata is unavailable because loading did not complete")
        return self._fileMetadata
    
    def setAcqDate(self, value: str) -> None:
        """Stage a file-derived acquisition date.

        Args:
            value: Acquisition date formatted as ``YYYY-MM-DD``.
        """
        self._acqDate = value

    def setAcqTime(self, value: str) -> None:
        """Stage a file-derived acquisition time.

        Args:
            value: Acquisition time formatted as ``HH:MM:SS``.
        """
        self._acqTime = value

    def setAcqDateTime(self, value: str) -> None:
        """Stage a complete file-derived acquisition timestamp.

        Args:
            value: Complete acquisition timestamp.
        """
        self._acqDateTime = value

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
        """Return the number of recorded channels in the source file."""
        if self._fileMetadata is not None:
            return self._fileMetadata.num_channels
        return self._numChannels

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
    def recordingMode(self) -> recordingModes:
        """Return the recording mode as the compatibility enum."""
        if self._fileMetadata is not None:
            return recordingModes(self._fileMetadata.mode)
        return self._recordingMode

    # feb 2023, uncommented
    @property
    def sweepLabelX(self) -> Optional[str]:
        """Return the sweep X-axis label."""
        if self._fileMetadata is not None:
            return self._fileMetadata.sweep_label_x
        return self._sweepLabelX

    @property
    def sweepLabelY(self) -> Optional[str]:
        """Return the sweep Y-axis label."""
        if self._fileMetadata is not None:
            return self._fileMetadata.sweep_label_y
        return self._sweepLabelY

    @property
    def recordingDur(self):
        return self._sweepLengthSec

    @property
    def numSweeps(self) -> int:
        """Return the stored number of loaded sweeps."""
        if self._fileMetadata is not None:
            return self._fileMetadata.num_sweeps
        if self._numSweeps is not None:
            return self._numSweeps
        return len(self._sweepList)

    @property
    def sweepList(self):
        return self._sweepList

    @property
    def dataPointsPerMs(self) -> Optional[float]:
        """Return samples per millisecond, numerically equal to kilohertz."""
        if self._fileMetadata is not None:
            return self._fileMetadata.recording_frequency_khz
        return self._dataPointsPerMs

    @property
    def acqDate(self) -> str:
        """Return the file-derived acquisition date."""
        if self._fileMetadata is not None:
            return self._fileMetadata.acq_date
        return self._acqDate

    @property
    def acqTime(self) -> str:
        """Return the file-derived acquisition time."""
        if self._fileMetadata is not None:
            return self._fileMetadata.acq_time
        return self._acqTime

    @property
    def sweepX(self) -> np.ndarray:
        """Return the shared sweep time base in seconds.

        Every sweep uses column 0. This property does not read ``currentSweep``.

        Returns:
            Time values shared by the loaded sweeps.
        """
        return self._sweepX[:, 0]

    def get_sweep_y(self, sweep: int) -> np.ndarray:
        """Return recorded Y values for one sweep.

        Args:
            sweep: Zero-based column of ``_sweepY``.

        Returns:
            Recorded values for ``sweep``. This does not read or change
            ``currentSweep``.
        """
        return self._sweepY[:, sweep]

    @property
    def sweepY(self) -> np.ndarray:
        """Return recorded Y values for ``currentSweep``.

        ``currentSweep`` is shared mutable loader state, not an argument.
        A caller that already knows the sweep must call ``get_sweep_y``.
        ``sweepC``, ``filteredDeriv``, and ``sweepY_filtered`` have this same
        dependency.

        Returns:
            Recorded values for the loader's current sweep.
        """
        return self.get_sweep_y(self.currentSweep)

    @property
    def sweepC(self) -> np.ndarray:
        """Return the DAC command for ``currentSweep``.

        This follows the loader's current sweep, like ``sweepY``. It is not
        the sweep a caller has selected elsewhere.

        Returns:
            DAC command for the current sweep, or zeros when no command was loaded.
        """
        if self._sweepC is None:
            return np.zeros_like(self._sweepX[:, 0])
        return self._sweepC[:, self.currentSweep]

    def get_xUnits(self):
        return self._sweepLabelX

    def get_yUnits(self):
        return self._sweepLabelY

    @property
    def filteredDeriv(self) -> Optional[np.ndarray]:
        """Return the filtered derivative for ``currentSweep``.

        This column follows the loader's current sweep, like ``sweepY``.

        Returns:
            Filtered derivative for the current sweep, or None before filtering.
        """
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
            # abb 20260929
            # self.sweepY is the property that returns _sweepY[:, currentSweep], one column
            # self._filteredY = self.sweepY
            self._filteredY = self._sweepY

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

        self._filteredDeriv = np.vstack([rowOfZeros, self._filteredDeriv])

        return self._filteredDeriv
    
    @property
    def sweepY_filtered(self) -> Optional[np.ndarray]:
        """Return filtered Y values for ``currentSweep``.

        This column follows the loader's current sweep, like ``sweepY``.
        The full filtered recording remains ``_filteredY``.

        Returns:
            Filtered values for the current sweep, or None before filtering.
        """
        if self._filteredY is not None:
            return self._filteredY[:, self.currentSweep]
        return None

    @property
    def recordingFrequency(self) -> float:
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
        theRet = int(round(theRet))
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
        """Return the validated number of epochs per sweep when available."""
        if self._fileMetadata is not None:
            return self._fileMetadata.num_epochs
        return self._validatedNumEpochs()

    def _validatedNumEpochs(self) -> Optional[int]:
        """Return a common per-sweep epoch count when one can be represented.

        Returns:
            Common epoch count, or ``None`` when tables are absent or differ.
        """
        if self._epochTableList is None:
            return None
        counts = [
            table.numEpochs()
            for table in self._epochTableList
            if table is not None
        ]
        if not counts:
            return None
        if len(counts) != len(self._epochTableList) or len(set(counts)) != 1:
            logger.warning(
                "Could not represent one epoch count per sweep for %s: %s",
                self.filename,
                counts,
            )
            return None
        return counts[0]

    def _finalizeFileMetadata(self) -> None:
        """Construct the immutable file metadata after a loader completes.

        Raises:
            ValueError: If required loaded dimensions or sampling values are invalid.
        """
        if self._numSweeps is None:
            if self._sweepList is None:
                raise ValueError("Loaded recording has no sweep list")
            self._numSweeps = len(self._sweepList)
        if self._sweepList is None or len(self._sweepList) != self._numSweeps:
            raise ValueError("Loaded sweep count does not match the sweep list")
        if self._sweepY is not None and self._sweepY.shape[1] != self._numSweeps:
            raise ValueError("Loaded sweep count does not match the recording array")
        if self._dataPointsPerMs is None or self._dataPointsPerMs <= 0:
            raise ValueError("Loaded recording frequency must be positive")

        user_list = (
            None
            if self._userList is None
            else tuple(float(value) for value in self._userList)
        )
        self._fileMetadata = FileMetadata(
            acq_date=self._acqDate,
            acq_time=self._acqTime,
            acq_datetime=self._acqDateTime,
            num_channels=self._numChannels,
            num_sweeps=self._numSweeps,
            num_epochs=self._validatedNumEpochs(),
            sweep_label_x=self._sweepLabelX or "",
            sweep_label_y=self._sweepLabelY or "",
            mode=self._recordingMode.value,
            recording_frequency_khz=float(self._dataPointsPerMs),
            user_list=user_list,
        )

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
        userList: Optional[List[float]] = None,  # owl analysis
        xLabel: str = "",
        yLabel: str = "",
    ) -> None:
        """Store arrays and derive common acquisition values for a loader.

        Args:
            sweepX: Time values in seconds.
            sweepY: Recorded values arranged as point by sweep.
            sweepC: Optional DAC command arranged as point by sweep.
            recordingMode: Recording mode for the loaded values.
            userList: Optional ABF user-list values.
            xLabel: X-axis label.
            yLabel: Y-axis label.
        """
        self._sweepX = sweepX
        self._sweepY = sweepY
        self._sweepC = sweepC

        self._userList = userList

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

        if self._fileMetadata is not None:
            self._finalizeFileMetadata()

    def setSweepCondition(self, sweep: int, condition: str) -> None:
        """Set the condition string for a loaded sweep.

        Args:
            sweep: Sweep index that already has a condition entry.
            condition: Condition label to store for that sweep.
        """
        if sweep not in self._sweep_conditions:
            logger.warning(
                f"Cannot set sweep condition; sweep {sweep} is not loaded in {self.filename}"
            )
            return
        if not isinstance(condition, str):
            logger.warning(
                f"Cannot set sweep condition; condition for sweep {sweep} must be a string"
            )
            return
        if self._sweep_conditions[sweep] == condition:
            return
        self._sweep_conditions[sweep] = condition
        self._sweep_conditions_dirty = True

    def getSweepCondition(self, sweep: int) -> str:
        """Return the condition string for a loaded sweep.

        Args:
            sweep: Sweep index that already has a condition entry.

        Returns:
            The stored condition, or an empty string when the sweep is not loaded.
        """
        if sweep not in self._sweep_conditions:
            logger.warning(
                f"Cannot get sweep condition; sweep {sweep} is not loaded in {self.filename}"
            )
            return ""
        return self._sweep_conditions[sweep]

    @property
    def sweepConditionsDirty(self) -> bool:
        """Return whether sweep conditions have changed since loading or saving."""
        return self._sweep_conditions_dirty

    def clearSweepConditionsDirty(self) -> None:
        """Mark the current sweep conditions as loaded or successfully saved."""
        self._sweep_conditions_dirty = False

if __name__ == "__main__":
    d = getFileLoaders()
    # for k,v in d.items():
    #     print(k,v)
