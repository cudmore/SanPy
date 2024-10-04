import sys

import numpy as np

from PyQt5 import QtWidgets

from sanpy.kym.interface.kymRoiWidget import KymRoiWidget

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def test_kym_roi_widget():
    from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis

    # path = '/Users/cudmore/Dropbox/data/colin/sanAtp/ISAN Linescan 3.tif'
    
    #
    # colin retreat sept 2024
    #

    # santana int done
    # (1)
    # path = '/Users/cudmore/Desktop/retreat-sept-2024/ISAN Linescan 1.tif'
    # (2)
    # super noisy - no peaks?
    # path = '/Users/cudmore/Desktop/retreat-sept-2024/ISAN Linescan 9.tif'
    # (3)
    # negative peaks - REALY NOISY
    # roi there is exponential decay but fit failed
    # path = '/Users/cudmore/Desktop/retreat-sept-2024/ISAN Linescan 10.tif'  #negative peak,  roi 2 has issues
    # (4)
    # path = '/Users/cudmore/Desktop/retreat-sept-2024/SSAN Linescan 1.tif'
    # (5)
    # path = '/Users/cudmore/Desktop/retreat-sept-2024/SSAN Linescan 11.tif'    
    # (6)
    path = '/Users/cudmore/Desktop/retreat-sept-2024/SSAN Linescan 12.tif'

    #
    kra = KymRoiAnalysis(path)

    # kra.peakDetectAllRoi()

    app = QtWidgets.QApplication(sys.argv)

    kw = KymRoiWidget(kra)
    kw.show()

    sys.exit(app.exec_())

def loadSaveAllRoi():
    pass

def test_kym_roi_widget_v0():
    import tifffile
    
    path = '/Users/cudmore/Dropbox/data/colin/sanAtp/ISAN Linescan 1.tif'
    
    # not great
    # path = '/Users/cudmore/Dropbox/data/colin/sanAtp/ISAN Linescan 2.tif'
    
    path = '/Users/cudmore/Dropbox/data/colin/sanAtp/ISAN Linescan 3.tif'

    # negative peaks
    path = '/Users/cudmore/Dropbox/data/colin/sanAtp/SSAN Linescan 8.tif'
    
    imgData = tifffile.imread(path)

    # some Olympus exports are 3D RGB ???
    if len(imgData.shape) == 3:
        imgData = imgData[:, :, 1]  # olympus export is sometimes with 3x channels, assuming channel 1

    imgData = np.rot90(imgData)
    # imgData = np.flip(imgData, axis=0)
    logger.info(f"Loaded tif with shape: {imgData.shape}")

    # find corresponding Olympus txt file with params
    from sanpy._util import _loadLineScanHeader
    olympusHeader = _loadLineScanHeader(path)

    if olympusHeader is None:
        logger.error(f'did not find corresponding Olympus header txt file for path :{path}')
        return

    app = QtWidgets.QApplication(sys.argv)

    headerDict = {
        'secondsPerLine' : olympusHeader['secondsPerLine'],  #0.003,
        'umPerPixel' : olympusHeader['umPerPixel'],  #.166,
        'path' : path,
    }
    logger.info(f'header:{headerDict}')
    
    # kw = KymRoiWidget(imgData=imgData, header=headerDict)
    kw = KymRoiWidget(imgData=imgData, header=headerDict)
    kw.show()

    # kw.switchFile(imgData, headerDict)
    
    # [0, 958, 999, 864]
    # kw.addRoi([0, 958, 999, 864])

    # kw.loadAnalysis()

    # kw.saveAnalysisResults()

    sys.exit(app.exec_())

if __name__ == '__main__':
    test_kym_roi_widget()