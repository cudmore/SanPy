import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

import qdarktheme

from PyQt5 import QtWidgets

from sanpy.kym.interface.kymRoiWidget import KymRoiWidget

from sanpy.kym.logger import get_logger
logger = get_logger(__name__)

def _broken_test_kym_roi_widget():
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
    path = '/Users/cudmore/Desktop/retreat-sept-2024/SSAN Linescan 12.tif'

    # paula for diam detection
    # path = '/Users/cudmore/Dropbox/data/cell-shortening/paula/cell01_C002T001.tif'

    # from andy collaborator (manual save of czi to tif)
    # this is one line scan of blood flow
    path = '/Users/cudmore/Dropbox/data/sanpy-users/kym-users/czi-data/linescansForVelocityMeasurement/fiji-export/Image 2.tif'

    path = '/Users/cudmore/Dropbox/data/sanpy-users/kym-users/czi-data/disjointedlinescansandframescans/fiji-export/Image 10.tif'

    #
    # paula 2-channel
    # path = '/Users/cudmore/Dropbox/data/colin/2-channel kymographs/cell 01/cell 01_C001T001.tif'
    # path = '/Users/cudmore/Dropbox/data/colin/2-channel kymographs/cell 02/cell 02_0001_C001T001.tif'
    # path = '/Users/cudmore/Dropbox/data/colin/2-channel kymographs/cell 03/cell 03_0001_C001T001.tif'
    # increase of iATP during Ca++ rise
    # path = '/Users/cudmore/Dropbox/data/colin/2-channel kymographs/cell 04/cell 04_C001T001.tif'
    # path = '/Users/cudmore/Dropbox/data/colin/2-channel kymographs/cell 06/cell 06_C001T001.tif'
    # path = '/Users/cudmore/Dropbox/data/colin/2-channel kymographs/cell 07/cell 07_C001T001.tif'
    # path = '/Users/cudmore/Dropbox/data/colin/2-channel kymographs/cell 08/cell 08_C001T001.tif'
    # path = '/Users/cudmore/Dropbox/data/colin/2-channel kymographs/cell 09/cell 09_C001T001.tif'
    
    # decrease iATP
    # path = '/Users/cudmore/Dropbox/data/colin/2-channel kymographs/cell 10/cell 10_C001T001.tif'
    
    # bi-phasic atp, decrease then increase
    # path = '/Users/cudmore/Dropbox/data/colin/2-channel kymographs/cell 14/cell 14_C001T001.tif'

    path = '/Users/cudmore/Dropbox/data/colin/2025/mito-atp/mito-atp-20250623-RHC/20250312/ISAN/20250312 ISAN FCCP R1 LS2.tif.frames/20250312 ISAN R1 LS2 FCCP.tif'
    
    from sanpy.fileloaders import fileLoader_tif
    flt = fileLoader_tif(path)

    # _imgData1 = flt.getTifData(channel=1)
    # print(f'_imgData1:{_imgData1.shape}')
    # imgData = flt.tifData  # property to get first channel

    imgData = flt._tif  # list of color channel images
    
    logger.warning(f'removing sum 0 color channels from imgData:{len(imgData)}')

    finalImgData = []
    for _imgData in imgData:
        if np.sum(_imgData) == 0:
            continue
        else:
            finalImgData.append(_imgData)
    
    logger.info(f'  final number of channels is {len(finalImgData)}')
    #
    kra = KymRoiAnalysis(path, imgData=finalImgData)

    # kra.peakDetectAllRoi()

    app = QtWidgets.QApplication(sys.argv)

    qdarktheme.setup_theme("dark")

    kw = KymRoiWidget(kra)
    kw.show()

    sys.exit(app.exec_())

def loadSaveAllRoi():
    pass

if __name__ == '__main__':
    _broken_test_kym_roi_widget()