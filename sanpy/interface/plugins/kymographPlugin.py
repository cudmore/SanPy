from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin
#from sanpy.interface import kymographWidget

class kymographPlugin(sanpyPlugin):
    myHumanName = 'Kymograph'

    #def __init__(self, myAnalysisDir=None, **kwargs):
    def __init__(self, plotRawAxis=False, ba=None, **kwargs):
        """
        Args:
            ba (bAnalysis): Not required
        """
        
        logger.info('')
        
        super().__init__(ba=ba, **kwargs)
        #super(kymographPlugin, self).__init__(ba=ba, **kwargs)

        #self.setShowSelf(False)
                
        if ba.myFileType != 'tif':
            logger.error(f'only tif files are supported')
            self._initError = True
            return

        print('  ba is type:', type(ba))
        
        path = ba.getFilePath()
        print('  path:', path)

        print('  creating kymographWidget')
        self._kymWidget = sanpy.interface.kymographWidget(path)
        print('  created')

        # does not work
        # self.setCentralWidget(self._kymWidget)
        
        #self._kymWidget.show()
        
        # does not work
        # self.addWidget(self._kymWidget)

    def replot(self):
        path = self.ba.getFilePath()
        self._kymWidget.replot(path)

    def getWidget(self):
        """Over-ride if plugin makes its own widget.
        """
        return self._kymWidget


