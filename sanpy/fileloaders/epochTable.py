from typing import Union, Optional
from pprint import pprint

import pandas as pd

import pyabf

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

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

    def __init__(self, abf: pyabf.ABF = None):
        self._epochList = []

        if abf is not None:
            self._builFromAbf(abf)
    
    def __str__(self):
        return self.getEpochList(asDataFrame=True).to_string()

    def addEpoch(self, sweepNumber, startSec, stopSec, dataPointsPerMs : int, level, type : str = 'Step'):
        newEpochIdx = self.numEpochs()
        
        p1 = (startSec * 1000) * dataPointsPerMs
        p1 = int(p1)
        
        p2 = (stopSec * 1000) * dataPointsPerMs
        p2 = int(p2)
        
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
            # "pulseWidth": pulseWidth,
            # "pulsePeriod": pulsePeriod,
            # "digitalState": digitalState,  # list of 0/1 for 8x digital states
        }
        self._epochList.append(epochDict)

    def getSweepEpoch(self, sweep):
        return self._epochList[sweep]

    def _builFromAbf(self, abf: pyabf.ABF):
        dataPointsPerMs = abf.dataPointsPerMs
        """To convert point to seconds"""

        try:
            _tmp = abf.sweepEpochs.p1s
        except AttributeError as e:
            logger.error(e)
            return

        # sweepEpochs is type "pyabf.waveform.EpochSweepWaveform"
        for epochIdx, p1 in enumerate(abf.sweepEpochs.p1s):
            p2 = abf.sweepEpochs.p2s[epochIdx]  # stop point of each pulse
            epochLevel = abf.sweepEpochs.levels[epochIdx]
            epochType = abf.sweepEpochs.types[epochIdx]
            pulseWidth = abf.sweepEpochs.pulseWidths[epochIdx]
            pulsePeriod = abf.sweepEpochs.pulsePeriods[epochIdx]
            digitalState = abf.sweepEpochs.pulsePeriods[epochIdx]
            ##print(f"epoch index {epochIdx}: at point {p1} there is a {epochType} to level {epochLevel}")

            p1_sec = p1 / abf.dataPointsPerMs / 1000
            p2_sec = p2 / abf.dataPointsPerMs / 1000

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
    import sanpy

    # path = '/Users/cudmore/Sites/SanPy/data/19114000.abf'
    path = "/Users/cudmore/data/theanne-griffith/07.28.21/2021_07_28_0001.abf"

    ba = sanpy.bAnalysis(path)
    print(ba)

    sweep = 13

    et = ba.fileLoader.getEpochTable(sweep)
    df = et.getEpochList(asDataFrame=True)
    pprint(df)

    testPnt = 1280
    epochIndex = et.findEpoch(testPnt)
    print(f"testPnt:{testPnt} is in epoch index: {epochIndex}")

    print("getStartSecs:", et.getStartSecs())
    print("getEpochLines:", et.getEpochLines())
