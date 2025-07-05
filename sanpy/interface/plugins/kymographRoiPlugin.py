from typing import Union, Dict, List, Tuple, Optional

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin

# from sanpy.interface import kymographWidget

class kymographRoiPlugin(sanpyPlugin):
    myHumanName = "Kymograph ROI"

    # def __init__(self, myAnalysisDir=None, **kwargs):
    def __init__(self, ba=None, **kwargs):
        """
        Args:
            ba (bAnalysis): Not required
        """

        logger.info("")

        super().__init__(ba=ba, **kwargs)

        # self._kymWidget = sanpy.interface.kymographPlugin2(ba)

        # kym roi will not respond to main sanpy gui (in particlar switch file)
        self._turnOffAllSignalSlot()

        if ba is None or not ba.fileLoader.isKymograph():
            logger.error('ba file is not a kymograph')
            from PyQt5 import QtWidgets
            self._kymWidget = QtWidgets.QLabel('NOT A KYMOGRAPH FILE!')
            self.getVBoxLayout().addWidget(self._kymWidget)
            return
        
        path = self.ba.fileLoader.filepath
        
        if self.darkTheme:
            # updated 20230914
            import matplotlib.pyplot as plt
            plt.style.use("dark_background")
        else:
            import matplotlib.pyplot as plt
            plt.rcParams.update(plt.rcParamsDefault)

        import numpy as np
        from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis


        imgData = self.ba.fileLoader._tif  # list of color channel images
        
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

        from sanpy.kym.interface.kymRoiWidget import KymRoiWidget
        # self._kymWidget = KymRoiWidget(imgData=imgData, header=headerDict)
        self._kymWidget = KymRoiWidget(kra)

        self.getVBoxLayout().addWidget(self._kymWidget)

    def closeEvent(self, event):
        self._kymWidget.closeEvent(event)
