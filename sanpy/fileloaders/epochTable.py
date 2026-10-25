"""Represent stimulus epochs for one recording sweep."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Optional
from pprint import pprint

import pandas as pd

import pyabf
from pydantic import BaseModel, ConfigDict, field_validator

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

EpochLevelUnit = Literal["pA", "mV"]
"""Supported SanPy command units for epoch levels."""


class Epoch(BaseModel):
    """Store one canonical stimulus epoch using sample-point boundaries."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sweep_number: int
    index: int
    type: str
    start_point: int
    stop_point: int
    level: float
    pulse_width: float | None = None
    pulse_period: float | None = None
    digital_state: tuple[int, ...] | None = None

    @field_validator("stop_point")
    @classmethod
    def _validate_stop_point(cls, value: int, info: Any) -> int:
        """Require the stop point to follow the start point.

        Args:
            value: Candidate exclusive stop point.
            info: Pydantic validation context containing earlier fields.

        Returns:
            Validated stop point.

        Raises:
            ValueError: If the stop point does not follow the start point.
        """
        start_point = info.data.get("start_point")
        if start_point is not None and value <= start_point:
            raise ValueError("Epoch stop_point must be greater than start_point")
        return value

class epochTable():
    """Load epoch/stimulation from abf file using 'sweepEpochs'.

    Values in epoch table are per sweep!

    sweepNumber  index  type  startPoint  stopPoint  startSec  stopSec  durSec  level  pulseWidth  pulsePeriod  digitalState
    0           13      0  Step           0         25    0.0000   0.0025  0.0025   -0.1           0            0             0
    1           13      1  Step          25        275    0.0025   0.0275  0.0250   -0.1           0            0             0
    2           13      2  Step         275       1275    0.0275   0.1275  0.1000    0.7           0            0             0
    3           13      3  Step        1275       1525    0.1275   0.1525  0.0250   -0.1           0            0             0
    4           13      4  Step        1525       1600    0.1525   0.1600  0.0075   -0.1           0            0             0

    """

    def __init__(
        self,
        abf: pyabf.ABF | None = None,
        level_unit: EpochLevelUnit | None = None,
    ) -> None:
        """Initialize an optional ABF-backed epoch table.

        Args:
            abf: Optional pyABF recording positioned at one sweep.
            level_unit: Unit shared by every epoch level in this table.
        """
        self._epochList = []
        self._level_unit = level_unit

        if abf is not None:
            self._builFromAbf(abf)

    @property
    def level_unit(self) -> EpochLevelUnit | None:
        """Return the command unit shared by every epoch in the table."""
        return self._level_unit

    def set_level_unit(self, level_unit: EpochLevelUnit) -> None:
        """Set the command unit shared by every epoch.

        Args:
            level_unit: Current-clamp ``pA`` or voltage-clamp ``mV``.
        """
        self._level_unit = level_unit

    @classmethod
    def from_epochs(
        cls,
        epochs: Sequence[Epoch],
        data_points_per_ms: float,
        level_unit: EpochLevelUnit,
    ) -> epochTable:
        """Construct a complete table from validated canonical epochs.

        Args:
            epochs: Ordered epochs belonging to one sweep.
            data_points_per_ms: Recording sampling rate in points per millisecond.
            level_unit: Unit shared by every epoch level.

        Returns:
            New epoch table with derived second values.

        Raises:
            ValueError: If sampling is invalid or indices are not contiguous.
        """
        if data_points_per_ms <= 0:
            raise ValueError("data_points_per_ms must be positive")
        if [epoch.index for epoch in epochs] != list(range(len(epochs))):
            raise ValueError("Epoch indices must be contiguous and start at zero")
        table = cls(level_unit=level_unit)
        for epoch in epochs:
            table.addEpoch(
                sweepNumber=epoch.sweep_number,
                startPoint=epoch.start_point,
                stopPoint=epoch.stop_point,
                dataPointsPerMs=data_points_per_ms,
                level=epoch.level,
                type=epoch.type,
                pulseWidth=epoch.pulse_width,
                pulsePeriod=epoch.pulse_period,
                digitalState=epoch.digital_state,
            )
        return table
    
    def __str__(self):
        return self.getEpochList(asDataFrame=True).to_string()

    def addEpoch(
        self,
        sweepNumber: int,
        startPoint: int,
        stopPoint: int,
        dataPointsPerMs: float,
        level: float,
        type: str = "Step",
        pulseWidth: float | None = None,
        pulsePeriod: float | None = None,
        digitalState: tuple[int, ...] | None = None,
    ) -> None:
        """Append one epoch defined by sample points.

        Points are stored as given. Seconds are derived from points, the same
        way ``_builFromAbf`` derives them.

        Args:
            sweepNumber: Sweep the epoch belongs to.
            startPoint: First sample point of the epoch.
            stopPoint: Exclusive stop sample point of the epoch.
            dataPointsPerMs: Sampling rate in points per millisecond.
            level: Command level of the epoch.
            type: Epoch type label.
            pulseWidth: Optional pulse width from the source protocol.
            pulsePeriod: Optional pulse period from the source protocol.
            digitalState: Optional digital output state.
        """
        newEpochIdx = self.numEpochs()

        p1 = int(startPoint)
        p2 = int(stopPoint)
        startSec = p1 / dataPointsPerMs / 1000
        stopSec = p2 / dataPointsPerMs / 1000

        epochDict = {
            "sweepNumber": sweepNumber,
            "index": newEpochIdx,
            "type": type,
            "startPoint": p1,  # point the epoch starts
            "stopPoint": p2,  # point the epoch ends
            "startSec": startSec,
            "stopSec": stopSec,
            "durSec": stopSec - startSec,
            "level": level,
            "pulseWidth": pulseWidth,
            "pulsePeriod": pulsePeriod,
            "digitalState": digitalState,
        }
        self._epochList.append(epochDict)

    def getSweepEpoch(self, sweep):
        return self._epochList[sweep]

    def _builFromAbf(self, abf: pyabf.ABF):
        # dataPointsPerMs = abf.dataPointsPerMs
        """To convert point to seconds"""

        try:
            _tmp = abf.sweepEpochs.p1s
        except AttributeError as e:
            logger.error(e)
            return

        # abf.sweepEpoch is
        # pyabf.waveform.EpochSweepWaveform
        # logger.info(f'   abf.sweepEpochs is {type(abf.sweepEpochs)}')
        # print(abf.sweepEpochs)

        # print(pyabf.waveform.epochTable())

        # sweepEpochs is type "pyabf.waveform.EpochSweepWaveform"
        for epochIdx, p1 in enumerate(abf.sweepEpochs.p1s):
            p2 = abf.sweepEpochs.p2s[epochIdx]  # stop point of each pulse
            epochLevel = abf.sweepEpochs.levels[epochIdx]
            epochType = abf.sweepEpochs.types[epochIdx]
            pulseWidth = abf.sweepEpochs.pulseWidths[epochIdx]
            pulsePeriod = abf.sweepEpochs.pulsePeriods[epochIdx]
            digitalState = abf.sweepEpochs.digitalStates[epochIdx]  # 20240117 owl-analysis
            ##print(f"epoch index {epochIdx}: at point {p1} there is a {epochType} to level {epochLevel}")

            try:
                p1_sec = p1 / abf.dataPointsPerMs / 1000
                p2_sec = p2 / abf.dataPointsPerMs / 1000
            except (ZeroDivisionError) as e:
                logger.error(f'ZeroDivisionError: {e}')
                p1_sec = float('nan')
                p2_sec = float('nan')

            epochDict = {
                "sweepNumber": abf.sweepNumber,
                "index": epochIdx,
                "type": epochType,
                "startPoint": p1,  # point the epoch starts
                "stopPoint": p2,  # point the epoch ends
                "startSec": p1_sec,
                "stopSec": p2_sec,
                "durSec": p2_sec - p1_sec,
                "level": epochLevel,
                "pulseWidth": pulseWidth,
                "pulsePeriod": pulsePeriod,
                "digitalState": digitalState,  # list of 0/1 for 8x digital states
            }
            self._epochList.append(epochDict)

    def getEpochList(self, asDataFrame: bool = False):
        if asDataFrame:
            return pd.DataFrame(self._epochList)
        else:
            return self._epochList

    def findEpoch(self, pnt: int) -> Optional[int]:
        """Return epoch index for a point in recording.

        Stop points are always the same as next epoch start point.
        Be sure to use '<' like pnt<stopPnt to get epoch index correct.

        If not found, return None

        Parameters
        ----------
        pnt : int
            Point index into recording (within a sweep)
        """
        for epochIdx, epoch in enumerate(self._epochList):
            startPoint = epoch["startPoint"]
            stopPoint = epoch["stopPoint"]
            if pnt >= startPoint and pnt < stopPoint:
                return epochIdx
        #
        # return None

    def getLevel(self, epoch):
        """Given an epoch number return the 'level'"""
        return self._epochList[epoch]["level"]

    def getStartSec(self, epoch):
        """Given an epoch number return the 'startSec'"""
        return self._epochList[epoch]["startSec"]

    def getStartSecs(self):
        """Return all epoch start times."""
        startSecs = [epoch["startSec"] for epoch in self._epochList]
        return startSecs

    def getEpochLines(self, yMin=0, yMax=1):
        x = [float("nan")] * (self.numEpochs() * 3)
        y = [float("nan")] * (self.numEpochs() * 3)

        for epoch in range(self.numEpochs()):
            idx = epoch * 3
            x[idx] = self._epochList[epoch]["startSec"]
            x[idx + 1] = self._epochList[epoch]["startSec"]
            x[idx + 2] = float("nan")

            y[idx] = yMin
            y[idx + 1] = yMax
            y[idx + 2] = float("nan")

        return x, y

    def numEpochs(self):
        # print('qqq:', self._epochList)
        return len(self._epochList)


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import sanpy

    # path = '/Users/cudmore/Sites/SanPy/data/19114000.abf'
    path = "/Users/cudmore/data/theanne-griffith/07.28.21/2021_07_28_0001.abf"

    path = '/Users/cudmore/Dropbox/data/sanpy-users/porter/data/2022_08_15_0022.abf'

    ba = sanpy.bAnalysis(path)
    print(ba)

    _abf = pyabf.ABF(path)
    # _epochTable = pyabf.waveform.EpochTable(_abf, 1)
    # print('   _epochTable')
    # print(_epochTable)

    sweeps = [9, 10, 11]
    for sweep in sweeps:
        ba.setSweep(sweep)
        et = ba.fileLoader.getEpochTable(sweep)
        df = et.getEpochList(asDataFrame=True)
        print(f'   sweep:{sweep}')
        pprint(df)

        # owl
        #<bound method ABF.sweepD of ABF (v2.9) with 1 channel (pA), sampled at 10.0 kHz, containing 18 sweeps, having no tags, with a total length of 6.33 minutes, recorded with protocol "PPR_v-clamp_owl". path=/Users/cudmore/Dropbox/data/sanpy-users/porter/2022_08_15_0022.abf>
        # print('self._abf.sweepD')
        # for _i in range(8):
        #     print(_i)
        #     print(self._abf.sweepD(_i))
        _abf.setSweep(sweep)
        for _i in range(8):
            _sweepD = _abf.sweepD(_i)

    testPnt = 1280
    epochIndex = et.findEpoch(testPnt)
    print(f"testPnt:{testPnt} is in epoch index: {epochIndex}")

    print("getStartSecs:", et.getStartSecs())
    print("getEpochLines:", et.getEpochLines())
