"""
See:
"""
from typing import Union
from pprint import pprint

import pandas as pd

import pyabf

'''
path = 'data/20191009_0005.abf'
path = '/Users/cudmore/data/theanne-griffith/07.20.21/2021_07_20_0013.abf'
abf = pyabf.ABF(path)
'''

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class epochTable():
    """Load epoch/stimulation from abd file using 'sweepEpochs'.
    """
    def __init__(self, abf : pyabf.ABF):
        
        self._epochList = []

        #print('sweepX pnts:', len(abf.sweepX))

        #print('===')
        #pprint(vars(abf.sweepEpochs))
        #print('===')
        
        dataPointsPerMs = abf.dataPointsPerMs
        """To convert point to seconds"""

        try:
            _tmp = abf.sweepEpochs.p1s
        except (AttributeError) as e:
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
                'index': epochIdx,
                'type': epochType,
                'startPoint': p1,  # point the epoch starts
                'stopPoint': p2,  # point the epoch starts
                'startSec': p1_sec,
                'stopSec': p2_sec,
                'level': epochLevel,
                'pulseWidth': pulseWidth,
                'pulsePeriod': pulsePeriod,
                'digitalState': digitalState,  # list of 0/1 for 8x digital states
            }
            self._epochList.append(epochDict)

    def getEpochList(self, asDataFrame : bool = False):
        if asDataFrame:
            return pd.DataFrame(self._epochList)
        else:
            return self._epochList
    
    def findEpoch(self, pnt : int) -> Union[None, int]:
        """Return epoch index for a point in recording.

        Stop points are always the same as next epoch start point.
        Be sure to use '<' like pnt<stopPnt to get epoch index correct.
        """
        for epochIdx, epoch in enumerate(self._epochList):
            startPoint = epoch['startPoint']
            stopPoint = epoch['stopPoint']
            if pnt >= startPoint and pnt < stopPoint:
                return epochIdx
        #
        return None

if __name__ == '__main__':
    import sanpy

    #path = '/Users/cudmore/Sites/SanPy/data/19114000.abf'
    path = '/Users/cudmore/data/theanne-griffith/07.28.21/2021_07_28_0001.abf'

    ba = sanpy.bAnalysis(path)
    print(ba)

    et = ba.getEpochTable()
    df = et.getEpochList(asDataFrame=True)
    pprint(df)

    testPnt = 1280
    epochIndex = et.findEpoch(testPnt)
    print(f'testPnt:{testPnt} is in epoch index: {epochIndex}')
