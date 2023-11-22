from datetime import datetime
import os
from typing import Union, Dict, List, Tuple

import numpy as np

import tifffile

import sanpy
from sanpy.fileloaders.fileLoader_base import fileLoader_base
from sanpy.fileloaders.fileLoader_base import recordingModes
from sanpy._util import _loadLineScanHeader

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

try:
    from aicsimageio import AICSImage
    from aicspylibczi import CziFile
except (ModuleNotFoundError):
    pass

def loadCziHeader(cziPath : str) -> dict:
    """Load header from a czi file.

    Notes:
        For Whistler datetime, I am just dropping "-07:00"
        Otherwise I get exception
        "Invalid isoformat string: '2022-09-06T11:28:35.0731032-07:00'"

        Whister czi files also have one too many decimals in fractional seconds
    """
    
    if CziFile is None:
        return
    
    with open(cziPath) as f:
        czi = CziFile(f)

    # print('czi:', [x for x in dir(czi)])
    # print('  czi.meta:')
    # print(czi.meta)
    print('czi.dims:', czi.dims)  # HTCZYX
    print('czi.size:', czi.size)  # HTCZYX

    # [{'X': (0, 1024), 'Y': (0, 1), 'Z': (0, 1), 'C': (0, 1), 'T': (0, 8716), 'H': (0, 1)}]
    print('czi.get_dims_shape():', czi.get_dims_shape())

    # tmp = czi.read_image()
    # print('tmp:', tmp)
    # img, shp = czi.read_image(S=13, Z=16)
    # img2, shp2 = czi.read_image(Y=0, Z=0, C=0, H=0)
    img2, shp2 = czi.read_image()
    print('img2.shape:', img2.shape)
    print('shp2:', shp2)

    print('czi.meta:', czi.meta)

    xpath_str = "./Metadata/Information/Document/CreationDate"
    _creationdate = czi.meta.findall(xpath_str)  #  [<Element 'CreationDate' at 0x7fa670647f40>]
    #print('_creationdate:', _creationdate)
    for creationdate in _creationdate:
        # xml.etree.ElementTree.Element
        #print('  creationdate:', creationdate)
        #print(dir(creationdate))
        _datetimeText = creationdate.text
        
        # _datetime: 2022-09-06T11:28:35.0731032-07:00
        if _datetimeText.endswith('-07:00'):
            _datetimeText = _datetimeText.replace('-07:00', '')
            _datetimeText = _datetimeText[0:-1]  # remove last fractional second

        # take apart datetime
        _date = ''
        _time = ''
        try:
            #_datetime = datetime.strptime(datetime_text, "%Y-%m-%dT%H:%M:%S%f")
            #_datetime = datetime.strptime(_datetimeText, "%Y-%m-%dT%H:%M:%S.%f%z")
            _datetime = datetime.fromisoformat(_datetimeText)
            #print(_datetime)
            _date = _datetime.strftime('%Y-%m-%d')
            _time = _datetime.strftime('%H-%M-%S')
        except (ValueError) as e:
            print(f'EXCEPTION IN PARSING TIME STR "{_datetimeText}"')
            print(e)

        img = AICSImage(cziPath)  # selects the first scene found
    
        xVoxel = img.physical_pixel_sizes.X
        yVoxel = img.physical_pixel_sizes.Y
        zVoxel = img.physical_pixel_sizes.Z

        # tVoxel = img.physical_pixel_sizes.T

        xPixels = img.dims.X
        yPixels = img.dims.Y
        zPixels = img.dims.Z

        _parentFolder, _ = os.path.split(cziPath)
        _, _parentFolder = os.path.split(_parentFolder)
        
        _header = {
            'file': os.path.split(cziPath)[1],
            'parentFolder': _parentFolder,
            'date': _date,
            'time': _time,
            'xPixels': xPixels,
            'yPixels': yPixels,
            'zPixels': zPixels,
            'xVoxel': xVoxel,
            'yVoxel': yVoxel,
            'zVoxel': zVoxel,
        }

        return _header

def test_czi():
    if AICSImage:
        return
    
    import matplotlib.pyplot as plt

    path = '/media/cudmore/data/Dropbox/data/wu-lab-stanford/test_lu.czi'

    # header = loadCziHeader(path)
    # print(header)

    # return

    img = AICSImage(path)
    _tif = img.data

    # csv has 4071 line scans

    print('img:', img)
    print('img.shape:', img.shape)
    print('img.dims:', img.dims)
    print('img.dims.order:', img.dims.order)  # TCZYX

    print('_tif.shape:', _tif.shape)
    # _img: <AICSImage [Reader: CziReader, Image-is-in-Memory: True]>
    # kymograph is shape
    # (169, 1, 1, 1, 1024)


    # image must be shape[0] is time/big, shape[1] is space/small
    _tif = _tif[:,0,0,0,:]
    print('_tif:', _tif.shape)

    if _tif.shape[1] < _tif.shape[0]:
        # logger.info(f"rot90 image with shape: {self._tif.shape}")
        print('ROTATING')
        _tif = np.rot90(_tif, 1)  # ROSIE, so lines are not backward
        print('   _tif:', _tif.shape)

    plt.imshow(_tif)
    plt.show()

    xVoxel = img.physical_pixel_sizes.X
    yVoxel = img.physical_pixel_sizes.Y
    zVoxel = img.physical_pixel_sizes.Z

    print('voxels:', xVoxel, yVoxel, zVoxel)

    #print(os.path.split(path)[1], xVoxel, type(xVoxel))

    xPixels = img.dims.X
    yPixels = img.dims.Y
    zPixels = img.dims.Z
    print('pixels:', xPixels, yPixels, zPixels)

class fileLoader_czi(fileLoader_base):
    """
    requires:
    pip install aicspylibczi>=3.1.1
    """
    loadFileType = "czi"

    def loadFile(self):
        if AICSImage is None:
            return
        
        logger.info('')

        # <AICSImage [Reader: CziReader, Image-is-in-Memory: True]>
        _img = AICSImage(self.filepath)
        self._tif = _img.data

        print('_img:', _img)
        print(self._tif.shape)
        # _img: <AICSImage [Reader: CziReader, Image-is-in-Memory: True]>
        # kymograph is shape
        # (169, 1, 1, 1, 1024)

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
    # path = 'data/kymograph/rosie-kymograph.tif'
    # tlt = fileLoader_tif(path)

    test_czi()