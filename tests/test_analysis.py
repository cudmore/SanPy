"""
Test bAnalysis.py

Run this file with

```
python -m unittest sanpy/tests/test_analysis.py
```
"""

import os, shutil, tempfile
import unittest

import sanpy

import logging
from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__, level=logging.DEBUG)

class Test_Analysis(unittest.TestCase):
    # this patter is wierd to me?
    path = 'data/19114001.abf'
    # path = 'data/19114001.csv'
    #path = 'data/rosie-kymograph.tif'
    ba = sanpy.bAnalysis(path)
    expectedNumSpikes = 103
    expectedNumErrors = 69

    def test_0_load(self):
        logger.info('RUNNING')

        self.assertFalse(self.ba.loadError)
        self.assertIsNotNone(self.ba.fileLoader.sweepX)
        self.assertIsNotNone(self.ba.fileLoader.sweepY)
        self.assertEqual(len(self.ba.fileLoader.sweepX), len(self.ba.fileLoader.sweepY))

    def test_1_detect(self):
        logger.info('RUNNING')
        # grab detection parameters
        # see: sanpy.bDetection.detectionPresets.cakymograph
        bd = sanpy.bDetection()  # gets default
        dDict = bd.getDetectionDict('SA Node')
        # detect
        self.ba.spikeDetect(dDict)

        self.assertEqual(self.ba.numSpikes, self.expectedNumSpikes) # expecting 102 spikes
        self.assertEqual(len(self.ba.dfError), self.expectedNumErrors) # expecting 102 spikes

    def test_2_stats(self):
        logger.info('RUNNING')
        thresholdSec = self.ba.getStat('thresholdSec')

        self.assertEqual(len(thresholdSec), self.expectedNumSpikes) # expecting 102 spikes

if __name__ == '__main__':
    unittest.main()
