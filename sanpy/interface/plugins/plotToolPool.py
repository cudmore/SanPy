import sanpy
from sanpy.interface.plugins import basePlotTool

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class plotToolPool(basePlotTool):
    """Plot tool pooled across all open analysis"""

    myHumanName = "Plot Tool (pool)"

    def __init__(self, tmpMasterDf=None, **kwargs):
        """
        tmpMasterDf (pd df): only for debuggin
        """
        super().__init__(**kwargs)

        self.masterDf = None
        if self.getSanPyApp() is not None:
            uniqueColumn = 'parent2'  # corresponds to 'date' folder of kymographs
            _analysisDir = self.getSanPyApp().myAnalysisDir
            if _analysisDir is not None:
                self.masterDf = self.getSanPyApp().myAnalysisDir.pool_build(uniqueColumn=uniqueColumn)
                logger.info(self.masterDf)
            else:
                logger.error('main SanPY app does not have an analysis dir')

            # self.masterDf.to_csv("/Users/cudmore/Desktop/tmpDf-20221231.csv")
        elif tmpMasterDf is not None:
            logger.info("Using tmpMasterDf")
            self.masterDf = tmpMasterDf

        self.plot()


if __name__ == "__main__":
    import sys
    # import random
    from PyQt5 import QtCore, QtWidgets, QtGui

    app = QtWidgets.QApplication([])

    # load an analysis dir
    # path = "/home/cudmore/Sites/SanPy/data"
    path = '/media/cudmore/data/Dropbox/data/cell-shortening/fig1'
    ad = sanpy.analysisDir(path, autoLoad=True)
    #print(ad._df)
    # load all analysis
    logger.warning("=== loading all analysis")
    for fileIdx in range(ad.numFiles):
        ad.getAnalysis(fileIdx)
    # build the pool
    logger.warning("=== building pool")
    uniqueColumn = 'parent2'  # corresponds to 'date' folder of kymographs
    tmpMasterDf = ad.pool_build(uniqueColumn=uniqueColumn)

    # logger.warning('randomly assigning sex to male, female, unknown')
    # sexList = ['male', 'female', 'unknown']
    # tmpMasterDf['Sex'] = [random.choice(sexList) for k in tmpMasterDf.index]
    # print(tmpMasterDf['Sex'])

    # open window
    logger.warning(f'=== opening plotToolPool with tmpMasterDf {len(tmpMasterDf)}')
    # print('tmpMasterDf.columns:', tmpMasterDf.columns)
    ptp = plotToolPool(tmpMasterDf=tmpMasterDf)
    ptp.show()

    sys.exit(app.exec_())
