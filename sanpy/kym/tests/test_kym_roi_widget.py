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
    # (4), good for negative peaks
    # path = '/Users/cudmore/Desktop/retreat-sept-2024/SSAN Linescan 1.tif'
    # (5)
    # path = '/Users/cudmore/Desktop/retreat-sept-2024/SSAN Linescan 11.tif'    
    # (6)
    
    # colin line across lots of cells
    # path = '/Users/cudmore/Desktop/retreat-sept-2024/SSAN Linescan 12.tif'

    # paula for diam detection
    path = '/Users/cudmore/Dropbox/data/cell-shortening/paula/cell01_C002T001.tif'

    from sanpy.fileloaders import fileLoader_tif
    flt = fileLoader_tif(path)

    # _imgData1 = flt.getTifData(channel=1)
    # print(f'_imgData1:{_imgData1.shape}')
    # imgData = flt.tifData  # property to get first channel

    imgData = flt._tif  # list of color channel images
    imgData = imgData[0]
    
    #
    kra = KymRoiAnalysis(path, imgData=imgData)

    # kra.peakDetectAllRoi()

    app = QtWidgets.QApplication(sys.argv)

    kw = KymRoiWidget(kra)
    kw.show()

    sys.exit(app.exec_())

def loadSaveAllRoi():
    pass

if __name__ == '__main__':
    test_kym_roi_widget()