"""Load Axon Binary Format recordings."""

from typing import Any

import numpy as np
import pyabf
from pyabf.waveform import EpochTable as PyAbfEpochTable

from sanpy.fileloaders.epochTable import epochTable as SanPyEpochTable
from sanpy.fileloaders.fileLoader_base import fileLoader_base, recordingModes

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class fileLoader_abf(fileLoader_base):
    """Load ABF metadata eagerly and raw sweep arrays only when requested."""

    loadFileType = ".abf"

    def loadFile(self) -> None:
        """Load ABF headers and optionally materialize raw sweep arrays."""
        self._loadAbf(loadData=self._loadData)

    def _loadAbf(
        self,
        byteStream: Any | None = None,
        loadData: bool = True,
        stimulusFileFolder: str | None = None,
    ) -> None:
        """Load ABF metadata and optionally its raw sweeps.

        Args:
            byteStream: Optional pyABF-compatible byte stream.
            loadData: Whether to materialize raw sweep arrays.
            stimulusFileFolder: Optional alternate folder for stimulus files.
        """
        try:
            if byteStream is not None:
                logger.info("Loading byte stream")
                self._abf = pyabf.ABF(byteStream, loadData=loadData)
                self._isBytesIO = True
            else:
                self._abf = pyabf.ABF(
                    self.filepath,
                    loadData=loadData,
                    stimulusFileFolder=stimulusFileFolder,
                )

        except NotImplementedError as error:
            logger.error(f"    did not load abf file: {self.filepath}")
            logger.error(f"      NotImplementedError exception was: {error}")
            self._loadError = True
            self._abf = None

        except Exception as error:
            logger.error(f"    did not load abf file: {self.filepath}")
            logger.error(f"        unknown Exception was: {error}")
            self._loadError = True
            self._abf = None

        if self._loadError or self._abf is None:
            self.myFileType = "abf"
            return

        self._sweepList = list(self._abf.sweepList)
        self._numSweeps = len(self._sweepList)
        self._sweepLengthSec = float(self._abf.sweepLengthSec)
        self._dataPointsPerMs = float(self._abf.dataPointsPerMs)
        self._epochTableList = self._build_epoch_tables(self._abf)

        abf_datetime = self._abf.abfDateTime
        self.setAcqDate(abf_datetime.strftime("%Y-%m-%d"))
        self.setAcqTime(abf_datetime.strftime("%H:%M:%S"))
        self.setAcqDateTime(abf_datetime.isoformat(sep=" "))

        self._numChannels = len(self._abf.adcUnits)
        if self._numChannels > 1:
            logger.warning(
                f"SanPy defaults to channel 0 for {self._numChannels}-channel "
                f"recording {self._path}"
            )

        adc_units = self._abf.adcUnits[0]
        self._sweepLabelX = "sec"
        self._sweepLabelY = adc_units
        if adc_units in ["A", "pA", "nA", "uA"]:
            self._recordingMode = recordingModes.vclamp
        elif adc_units in ["mV", "uv", "V"]:
            self._recordingMode = recordingModes.iclamp
        else:
            logger.warning(f'did not understand adcUnit "{adc_units}"')

        self._userList = self._abf.userList
        if loadData:
            self._load_sweep_arrays(self._abf)

        self.myFileType = "abf"
        self._abf = None

    def _build_epoch_tables(
        self, abf: pyabf.ABF
    ) -> list[SanPyEpochTable] | None:
        """Build SanPy epoch tables from ABF header structures.

        Args:
            abf: Header-loaded pyABF recording.

        Returns:
            One epoch table per sweep, or ``None`` when headers have no usable
            epoch description.
        """
        try:
            pyabf_table = PyAbfEpochTable(abf, 0)
        except (AttributeError, IndexError, ValueError) as error:
            logger.warning(
                f"Could not read ABF epoch headers from {self.filepath}: {error}"
            )
            return None

        tables: list[SanPyEpochTable] = []
        for sweep, waveform in enumerate(pyabf_table.epochWaveformsBySweep):
            abf.sweepNumber = sweep
            abf.sweepEpochs = waveform
            tables.append(SanPyEpochTable(abf))
        return tables

    def _load_sweep_arrays(self, abf: pyabf.ABF) -> None:
        """Materialize ABF time, recording, and command arrays.

        Args:
            abf: pyABF recording whose signal data may be loaded on demand.
        """
        abf.setSweep(0, channel=0)
        row_count = abf.sweepX.shape[0]
        sweep_count = len(self._sweepList)
        self._sweepX = np.zeros((row_count, 1))
        self._sweepY = np.zeros((row_count, sweep_count))
        self._sweepC = np.zeros((row_count, sweep_count))

        for sweep in self._sweepList:
            abf.setSweep(sweepNumber=sweep, channel=0)
            if sweep == 0:
                self._sweepX[:, 0] = abf.sweepX
            self._sweepY[:, sweep] = abf.sweepY
            try:
                self._sweepC[:, sweep] = abf.sweepC
            except ValueError as error:
                logger.warning(
                    f"Could not load command sweep {sweep} from "
                    f"{self.filepath}: {error}"
                )

        abf.setSweep(0, channel=0)
