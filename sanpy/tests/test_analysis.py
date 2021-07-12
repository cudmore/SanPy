"""
Run this file with

```
python -m unittest sanpy/tests/test_analysis.py
```
"""

import logging
import unittest

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__, level=logging.DEBUG)

class Test_Analysis(unittest.TestCase):
	# this patter is wierd to me?
	path = 'data/19114001.abf'
	ba = sanpy.bAnalysis(path)
	expectedNumSpikes = 102
	expectedNumErrors = 1

	#def __init__(self, *args, **kwargs):
	#	super(Test_Analysis, self).__init__(*args, **kwargs)

	def test_0_load(self):
		logger.info('')

		self.assertFalse(self.ba.loadError)
		self.assertIsNotNone(self.ba.sweepX)
		self.assertIsNotNone(self.ba.sweepY)
		self.assertEqual(len(self.ba.sweepX), len(self.ba.sweepY))

	def test_1_detect(self):
		logger.info('')
		# grab detection parameters
		dDict = sanpy.bAnalysis.getDefaultDetection()
		# detect
		self.ba.spikeDetect(dDict)

		self.assertEqual(self.ba.numSpikes, self.expectedNumSpikes) # expecting 102 spikes
		self.assertEqual(len(self.ba.dfError), self.expectedNumErrors) # expecting 102 spikes

	def test_2_stats(self):
		logger.info('')
		thresholdSec = self.ba.getStat('thresholdSec')

		self.assertEqual(len(thresholdSec), self.expectedNumSpikes) # expecting 102 spikes

if __name__ == '__main__':
    unittest.main()
