
import numpy as np

from sanpy.kym.kymRoiAnalysis import KymRoi
# from sanpy.kym.kymRoiAnalysis import MplKym

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def _broken_test_kym_roi():
    import tifffile
    
    path = '/Users/cudmore/Dropbox/data/colin/sanAtp/ISAN Linescan 1.tif'
    path = '/Users/cudmore/Dropbox/data/colin/sanAtp/ISAN Linescan 4.tif'

    imgData = tifffile.imread(path)
    imgData = np.rot90(imgData)
    # imgData = np.flip(imgData)
    logger.info(f"Loaded tif with shape: {imgData.shape}")

    kroi = KymRoi(imgData, path=None)

    # MplKym(imgData)

if __name__ == '__main__':
    _broken_test_kym_roi()