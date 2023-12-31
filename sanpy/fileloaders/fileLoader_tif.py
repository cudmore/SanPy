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

def _test_czi():

    if not AICSImage:
        return
    
    import matplotlib.pyplot as plt

    # path = '/media/cudmore/data/Dropbox/data/wu-lab-stanford/test_lu.czi'
    path = '/Users/cudmore/Dropbox/data/sanpy-users/kym-users/plesnila/linescansForVelocityMeasurement/CO2.czi'

    # header = loadCziHeader(path)
    # print(header)


    logger.info('')
    img = AICSImage(path)

    print(img.ome_metadata)
    
    # fiji reports XYCZT
    _tmp = img.get_image_data()  # default is TCZYX
    _tmp = img.get_image_data("ZYX", T=0, C=0)

    print('   _tmp:', _tmp.shape)

    _tif = img.data

    # csv has 4071 line scans

    print('   img:', img)
    print('   img.shape:', img.shape)
    print('   img.dims:', img.dims)
    print('   img.dims.order:', img.dims.order)  # TCZYX

    print('   _tif.shape:', _tif.shape)
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

    print('   voxels:', xVoxel, yVoxel, zVoxel)

    #print(os.path.split(path)[1], xVoxel, type(xVoxel))

    xPixels = img.dims.X
    yPixels = img.dims.Y
    zPixels = img.dims.Z
    print('   pixels:', xPixels, yPixels, zPixels)

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

        _tmp = _img.get_image_data('XYCZT')

class fileLoader_tif(fileLoader_base):
    loadFileType = ".tif"

    def loadFile(self):
        # assuming pixels x line scan like (519, 10000)
        self._tif = []
        
        loadedTif = tifffile.imread(self.filepath)

        self._useThisChannel = 1
        
        # logger.info(f'loaded tif: {self._tif.shape}')

        # 202312 load czi tif (exported from Fiji bFolder2MapMAnager)
        numLoadedDims = len(loadedTif.shape)
        if numLoadedDims == 2:
            # one channel
            # already just a 2d image
            self._numChannels = 1
            self._tif.append(loadedTif)

        elif numLoadedDims == 3:
            # one channel
            # czi line scan with frames (frames, height, width)
            self._numChannels = 1
            self._tif.append(loadedTif[:, 0, :])
        elif numLoadedDims == 4:
            # multi channel czi line scan with frames (frames, channels, height, width)
            _channelDimension = 1
            self._numChannels = loadedTif.shape[_channelDimension]
            
            for _channel in range(self._numChannels):
                self._tif.append(loadedTif[:, _channel, 0, :])
        else:
            logger.error(f'did not understand image with sahpe {loadedTif.shape}')
            self._loadError = True
            return
        
        # image must be shape[0] is time/big, shape[1] is space/small
        for _channel, img in enumerate(self._tif):
            if img.shape[1] < img.shape[0]:
                logger.info(f"rot90 image with shape: {img.shape}")
                self._tif[_channel] = np.rot90(
                    img, 1
                )  # ROSIE, so lines are not backward

        if self._tif[0].dtype == np.uint8:
            _bitDepth = 8
        elif self._tif[0].dtype == np.uint16:
            _bitDepth = 16
        else:
            logger.warning(f'Did not undertand dtype {self._tif[0].dtype} defaulting to bit depth 16')
            _bitDepth = 16
        
        # we need a header to mimic one in original bAnalysis
        self._tifHeader = {
            'secondsPerLine': 0.001,  # 1 ms
            'umPerPixel': 0.3,
            'bitDepth': _bitDepth,
            'dtype': self._tif[0].dtype,
        }

        # load olympus txt file if it exists
        _olympusHeader = _loadLineScanHeader(self.filepath)
        if _olympusHeader is not None:
            # logger.info('loaded olympus header for {self.filepath}')
            # for k,v in _olympusHeader.items():
            #     logger.info(f'  {k}: {v}')
            try:
                self._tifHeader['umPerPixel'] = _olympusHeader["umPerPixel"]
                self._tifHeader['secondsPerLine'] = _olympusHeader["secondsPerLine"]
            except (KeyError) as e:
                pass

        self._setLoadedData()

    #
    # need to pull/merge code from xxx
    # bAbfText._abfFromLineScanTif()

    def _setLoadedData(self, channel=1):
        channelIdx = channel - 1

        # using 'reshape(-1,1)' to convert shape from (n,) to (n,1)
        sweepX = np.arange(0, self._tif[channelIdx].shape[1]).reshape(-1, 1)
        sweepX = sweepX.astype(np.float64)
        sweepX *= self._tifHeader['secondsPerLine']

        sweepY = np.sum(self._tif[channelIdx], axis=0).reshape(-1, 1)
        sweepY = np.divide(sweepY, np.max(sweepY))

        self.setLoadedData(
            sweepX=sweepX,
            sweepY=sweepY,
            recordingMode=recordingModes.kymograph
        )

    def setScale(self, secondsPerLine, umPerPixel, channel=1):
        """Redraw when x/y scale is changed.
        """
        logger.info(f'secondsPerLine:{secondsPerLine} umPerPixel:{umPerPixel} channel:{channel}')
        
        channelIdx = channel - 1

        self._tifHeader['secondsPerLine'] = secondsPerLine
        self._tifHeader['umPerPixel'] = umPerPixel
        # self._tifHeader = {
        #     'secondsPerLine': secondsPerLine,
        #     'umPerPixel': umPerPixel,
        # }

        sweepX = np.arange(0, self._tif[channelIdx].shape[1]).reshape(-1, 1)
        sweepX = sweepX.astype(np.float64)
        sweepX *= self._tifHeader['secondsPerLine']

        # todo: need to use rect roi
        sweepY = np.sum(self._tif[channelIdx], axis=0).reshape(-1, 1)

        self.setLoadedData(
            sweepX=sweepX,
            sweepY=sweepY,
            recordingMode=recordingModes.kymograph
        )

    @property
    def tifData(self, channel=1) -> np.ndarray:
        channelIdx = channel - 1
        return self._tif[channelIdx]
    
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

    _test_czi()