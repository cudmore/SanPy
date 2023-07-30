from typing import Union, Dict, List, Tuple
import numpy as np

import tifffile

import sanpy
from sanpy.fileloaders.fileLoader_base import fileLoader_base
from sanpy.fileloaders.fileLoader_base import recordingModes
from sanpy._util import _loadLineScanHeader

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class fileLoader_tif(fileLoader_base):
    loadFileType = "tif"

    def loadFile(self):
        # assuming pixels x line scan like (519, 10000)
        self._tif = tifffile.imread(self.filepath)

        # logger.info(f'loaded tif: {self._tif.shape}')

        # check if 3d, assume (z,y,x)
        if len(self._tif.shape) > 2:
            self._tif = self._tif[0,:,:]
            
        # image must be shape[0] is time/big, shape[1] is space/small
        if self._tif.shape[1] < self._tif.shape[0]:
            # logger.info(f"rot90 image with shape: {self._tif.shape}")
            self._tif = np.rot90(
                self._tif, 1
            )  # ROSIE, so lines are not backward

        if self._tif.dtype == np.uint8:
            _bitDepth = 8
        elif self._tif.dtype == np.uint16:
            _bitDepth = 16
        else:
            logger.warning(f'Did not undertand dtype {self._tif.dtype} defaulting to bit depth 16')
            _bitDepth = 16

        # print('_bitDepth:', _bitDepth)
        
        # we need a header to mimic one in original bAnalysis
        self._tifHeader = {
            'secondsPerLine': 0.001,  # 1 ms
            'umPerPixel': 0.3,
            'bitDepth': _bitDepth,
            'dtype': self._tif.dtype,
        }

        # load olympus txt file if it exists
        _olympusHeader = _loadLineScanHeader(self.filepath)
        if _olympusHeader is not None:
            # logger.info('loaded olympus header for {self.filepath}')
            # for k,v in _olympusHeader.items():
            #     logger.info(f'  {k}: {v}')
            self._tifHeader['umPerPixel'] = _olympusHeader["umPerPixel"]
            self._tifHeader['secondsPerLine'] = _olympusHeader["secondsPerLine"]

        # logger.info('loaded header for {self.filepath}')
        # for k,v in self._tifHeader.items():
        #     logger.info(f'  {k}: {v}')

        # using 'reshape(-1,1)' to convert shape from (n,) to (n,1)
        sweepX = np.arange(0, self._tif.shape[1]).reshape(-1, 1)
        sweepX = sweepX.astype(np.float64)
        sweepX *= self._tifHeader['secondsPerLine']

        # logger.info(f'  sweepX shape:{sweepX.shape}')
        # logger.info(f'  sweepX max:{np.nanmax(sweepX)}')
        # logger.info(f'  sweepX dt:{sweepX[1]-sweepX[0]}')

        sweepY = np.sum(self._tif, axis=0).reshape(-1, 1)
        sweepY = np.divide(sweepY, np.max(sweepY))

        # logger.info(f'sweepX:{sweepX.shape}')
        # logger.info(f'sweepY:{sweepY.shape}')

        self.setLoadedData(
            sweepX=sweepX,
            sweepY=sweepY,
            recordingMode=recordingModes.kymograph
        )

        # logger.info(f'dataPointsPerMs:{self.dataPointsPerMs}')

        #self.setScale(secondsPerLine, umPerPixel)

    #
    # need to pull/merge code from xxx
    # bAbfText._abfFromLineScanTif()

    def setScale(self, secondsPerLine, umPerPixel):
        """Redraw when x/y scale is changed.
        """
        logger.info(f'secondsPerLine:{secondsPerLine} umPerPixel:{umPerPixel}')
        
        self._tifHeader['secondsPerLine'] = secondsPerLine
        self._tifHeader['umPerPixel'] = umPerPixel
        # self._tifHeader = {
        #     'secondsPerLine': secondsPerLine,
        #     'umPerPixel': umPerPixel,
        # }

        sweepX = np.arange(0, self._tif.shape[1]).reshape(-1, 1)
        sweepX = sweepX.astype(np.float64)
        sweepX *= self._tifHeader['secondsPerLine']

        # todo: need to use rect roi
        sweepY = np.sum(self._tif, axis=0).reshape(-1, 1)

        self.setLoadedData(
            sweepX=sweepX,
            sweepY=sweepY,
            recordingMode=recordingModes.kymograph
        )

    @property
    def tifData(self) -> np.ndarray:
        return self._tif
    
    @property
    def tifHeader(self) -> dict:
        return self._tifHeader
    
    # this all goes into kymAnalysis
    def _old_resetKymographRect(self):
        defaultRect = self._abf.resetRoi()
        self._updateTifRoi(defaultRect)
        return defaultRect

    def _old_getKymographRect(self):
        if self.isKymograph():
            return self._abf.getTifRoi()
        else:
            return None

    def _old_getKymographBackgroundRect(self):
        if self.isKymograph():
            return self._abf.getTifRoiBackground()
        else:
            return None

    def _old_updateTifRoi(self, theRect=[]):
        """
        Update the kymograph ROI
        """
        self._abf.updateTifRoi(theRect)

        self._sweepX[:, 0] = self._abf.sweepX
        self._sweepY[:, 0] = self._abf.sweepY

if __name__ == '__main__':
    path = 'data/kymograph/rosie-kymograph.tif'
    tlt = fileLoader_tif(path)
