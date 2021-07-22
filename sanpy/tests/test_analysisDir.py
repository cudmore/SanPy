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
	def setUp(self):
		# Create a temporary directory
		self.test_dir = tempfile.mkdtemp()

		# copy data into it
		dst = os.path.join(self.test_dir, '19114001.abf')
		shutil.copyfile('data/19114001.abf', dst)

		dst = os.path.join(self.test_dir, '19114001.csv')
		shutil.copyfile('data/19114001.csv', dst)

	def tearDown(self):
		# Remove the directory after the test
		shutil.rmtree(self.test_dir)

	def test_3_loadDir(self):
		return

		logger.info('')
		ad = sanpy.analysisDir(path=self.test_dir)

		self.assertEqual(len(ad._df), 2)

		ad.saveHdf()

		ad.loadHdf()
		self.assertEqual(len(ad._df), 2)

if __name__ == '__main__':
    unittest.main()
	pass
