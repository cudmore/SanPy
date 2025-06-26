from functools import partial

import numpy as np

from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, KymRoi, PeakDetectionTypes
from sanpy.kym.interface.kymRoiImageWidget import KymRoiImageWidget
from sanpy.kym.interface.imageViewer import ImageViewer

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class KymRoiImageViewer(QtWidgets.QWidget):
    """A widget to show a kymRoiImage.
    """
    def __init__(self, kymRoiAnalysis : KymRoiAnalysis):
        super().__init__(None)

        self._kymRoiAnalysis = kymRoiAnalysis

        self._buildUI()

        # self.loadAnalysis()  # load roi from analysis and display on image

    def _buildUI(self):
        vLayout = QtWidgets.QVBoxLayout()
        self.setLayout(vLayout)

        # the whole kym
        # self._kymRoiImageWidget = KymRoiImageWidget(self._kymRoiAnalysis)
        # vLayout.addWidget(self._kymRoiImageWidget)
        channel = 0

        # one img per roi
        kymRoiImageDict = {}
        for roiLabel, kymRoi in self._kymRoiAnalysis._roiDict.items():
            # add a pg.ROI
            kymRoi:KymRoi = kymRoi
            logger.info(f'adding OneKymRoi roiLabel:{roiLabel}')
            detectionParameters = kymRoi.getDetectionParams(channel=channel, detectionType=PeakDetectionTypes.intensity)
            imgData = kymRoi.getRoiImg(channel=0)
            f0 = detectionParameters['f0 Value Percentile']
            oneKymRoi = ImageViewer(imgData,
                                  secondsPerLine=self._kymRoiAnalysis.secondsPerLine,
                                  umPerPixel=self._kymRoiAnalysis.umPerPixel,
                                  f0=f0)
            vLayout.addWidget(oneKymRoi)
            kymRoiImageDict[roiLabel] = oneKymRoi

            # if roiLabel == '2':
            #     break

    # taken from kymRoiWidget
    def loadAnalysis(self):
        """Load and add each roi in _kymRoiAnalysis
        """
        # logger.info(self._kymRoiAnalysis._roiDict.items())
        for _idx, (roiLabel, kymRoi) in enumerate(self._kymRoiAnalysis._roiDict.items()):
            ltrb = kymRoi.getRect()
            logger.info(f'adding roi {roiLabel} with rect {ltrb}')

            # add a pg.ROI
            _pgRoi = self._kymRoiImageWidget._addRoi(kymRoi)  # add roi to gui    

            # doSelect = _idx == 0
            # if doSelect:
            #     # select the first roi
            #     self.updateRoiIntensityPlot(roiLabel, doAnalysis=False)

if __name__ == '__main__':
    path = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/sanpy-20250608/250225/ISAN/ISAN R1 LS1.tif.frames/250225 ISAN R1 LS1 c1.tif'
    from sanpy.bAnalysis_ import bAnalysis
    ba = bAnalysis(path)
    imgData = ba.fileLoader.getTifData(channel=0)
    logger.info(f'imgData:{imgData.shape}')

    kymRoiAnalysis = KymRoiAnalysis(path, imgData, loadAnalysis=True)
    logger.info(f'kymRoiAnalysis:{kymRoiAnalysis.numRoi}')

    # run qt app
    app = QtWidgets.QApplication([])

    kymRoiImageViewer = KymRoiImageViewer(kymRoiAnalysis)
    kymRoiImageViewer.show()
    
    app.exec_()
