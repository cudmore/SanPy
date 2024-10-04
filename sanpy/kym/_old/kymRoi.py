from typing import List, Optional

import numpy as np

import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class MplKym:
    def __init__(self, imgData):
        plt.imshow(imgData)
        plt.show()

class KymRoi:
    def __init__(self, imgData : np.ndarray, path : str = None):
        """
        Parameters
        ----------
        imgData : np.ndarray
        path : str
            Path to save analysis
        """

        self._imgData = imgData
        self._path = path

        if self.path is None:
            self._createDefaults()
        else:
            self.load()

    @property
    def path(self):
        return self._path
    
    @property
    def roi(self):
        return self._roi
    
    @property
    def detectionParams(self) -> dict:
        return self._detectionParams
    
    def _createDefaults(self):
        self._roi : List[int] = [0, 0, 20, 20]  # [l, t, r, b]
        self._detectionParams = self._getDefaultDetectionParams()

    def _getDefaultDetectionParams(self) -> dict:
        ret = {}
        ret['notSure'] = 1

    def load(self):
        logger.info(f'Load from path')

