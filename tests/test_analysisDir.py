"""
Test bAnalysis.py

Run this file with

```
python -m unittest tests/test_analysis.py
```
"""

import os, shutil, tempfile
import unittest

import sanpy

import logging
from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__, level=logging.DEBUG)

class Test_Analysis_Dir(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

        # copy data into it
        src = os.path.join('data', '19114001.abf')
        dst = os.path.join(self.test_dir, '19114001.abf')
        #shutil.copyfile('data/19114001.abf', dst)
        shutil.copyfile(src, dst)

        src = os.path.join('data', '19114000.abf')
        dst = os.path.join(self.test_dir, '19114000.abf')
        #shutil.copyfile('data/19114000.abf', dst)
        shutil.copyfile(src, dst)

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)

    def testLoadDir(self):

        logger.info('')
        
        ad = sanpy.analysisDir(path=self.test_dir)

        print('xxx')
        print(ad._df)

        self.assertEqual(len(ad._df), 2)

        ad.saveHdf()

        ad.loadHdf()
        self.assertEqual(len(ad._df), 2)

        # add a new file and test sync folder
        src = os.path.join('data', '20191009_0005.abf')
        dst = os.path.join(self.test_dir, '20191009_0005.abf')
        shutil.copyfile(src, dst)

        logger.info(f'testing syncDfWithPath')
        ad.syncDfWithPath()
        self.assertEqual(len(ad._df), 3)

        # get all three files
        ba0 = ad.getAnalysis(0)
        ba1 = ad.getAnalysis(1)
        ba2 = ad.getAnalysis(2)

        # delete a row
        #ad.deleteRow(1)

        # remove from database
        #ad.removeRowFromDatabase(0)

if __name__ == '__main__':
    unittest.main()
