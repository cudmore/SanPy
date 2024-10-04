from typing import Union, Dict, List, Tuple, Optional, Optional

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
        tifData = self.ba.fileLoader.tifData
        if 0:
            secondsPerLine = self.ba.fileLoader.tifHeader['secondsPerLine']
            umPerPixel = self.ba.fileLoader.tifHeader['umPerPixel']

            imgData = self.ba.fileLoader.tifData

            logger.info(f'imgData:{imgData.shape}')

            headerDict = {
                'secondsPerLine' : secondsPerLine,  #olympusHeader['secondsPerLine'],  #0.003,
                'umPerPixel' : umPerPixel,  #olympusHeader['umPerPixel'],  #.166,
                'path' : path,
            }

            logger.info(headerDict)

        if self.darkTheme:
            # updated 20230914
            import matplotlib.pyplot as plt
            plt.style.use("dark_background")
        else:
            import matplotlib.pyplot as plt
            plt.rcParams.update(plt.rcParamsDefault)

        from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis
        kra = KymRoiAnalysis(path=path, imgData=tifData)

        from sanpy.kym.interface.kymRoiWidget import KymRoiWidget
        # self._kymWidget = KymRoiWidget(imgData=imgData, header=headerDict)
        self._kymWidget = KymRoiWidget(kra)

        self.getVBoxLayout().addWidget(self._kymWidget)

    def closeEvent(self, event):
        self._kymWidget.closeEvent(event)
