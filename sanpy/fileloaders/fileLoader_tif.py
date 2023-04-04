from typing import Union, Dict, List, Tuple
import numpy as np

# import pandas as pd

import tifffile

import sanpy
from sanpy.fileloaders.fileLoader_base import fileLoader_base

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class fileLoader_tif(fileLoader_base):
    loadFileType = "tif"

    # @property
    # def loadFileType(self):
    #     return 'tif'

    def loadFile(self):
        # assuming pixels x line scan like (519, 10000)
        self._tif = tifffile.imread(self.filepath)

        dt = 0.001  # sec

        # using 'reshape(-1,1)' to convert shape from (n,) to (n,1)
        sweepX = np.arange(0, self._tif.shape[1]).reshape(-1, 1)
        sweepY = np.sum(self._tif, axis=0).reshape(-1, 1)

        self._dt = 1
        self._dy = 1

        self.setLoadedData(
            sweepX=sweepX,
            sweepY=sweepY,
        )

    #
    # need to pull/merge code from xxx
    # bAbfText._abfFromLineScanTif()

    def resetKymographRect(self):
        defaultRect = self._abf.resetRoi()
        self._updateTifRoi(defaultRect)
        return defaultRect

    def getKymographRect(self):
        if self.isKymograph():
            return self._abf.getTifRoi()
        else:
            return None

    def getKymographBackgroundRect(self):
        if self.isKymograph():
            return self._abf.getTifRoiBackground()
        else:
            return None

    def _updateTifRoi(self, theRect=[]):
        """
        Update the kymograph ROI
        """
        self._abf.updateTifRoi(theRect)

        self._sweepX[:, 0] = self._abf.sweepX
        self._sweepY[:, 0] = self._abf.sweepY
