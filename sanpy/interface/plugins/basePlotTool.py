import numpy as np
import scipy.signal

from PyQt5 import QtCore, QtGui, QtWidgets

import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin

# from sanpy.bAnalysisUtil import statList


class basePlotTool(sanpyPlugin):
    """ """

    myHumanName = "Base Plot Tool"

    def __init__(self, **kwargs):
        super(basePlotTool, self).__init__(**kwargs)

        self.masterDf = None
        # one
        # self.masterDf = self.ba.dfReportForScatter
        # pool of bAnalysis
        # self.masterDf = self._bPlugins._sanpyApp.myAnalysisDir.pool_build()

        self.mainWidget2 = None

        # turn off all signal/slot
        switchFile = self.responseTypes.switchFile
        self.toggleResponseOptions(switchFile, newValue=False)
        analysisChange = self.responseTypes.analysisChange
        self.toggleResponseOptions(analysisChange, newValue=False)
        selectSpike = self.responseTypes.selectSpike
        self.toggleResponseOptions(selectSpike, newValue=False)
        setAxis = self.responseTypes.setAxis
        self.toggleResponseOptions(setAxis, newValue=False)

        # self.plot()

    def plot(self):
        logger.info("")

        # this plugin does not rely on underlying self.ba
        # if self.ba is None:
        #    return

        # analysisName = 'analysisname'
        analysisName = "Unique Name"
        # statListDict = statList  # maps human readable to comments
        statListDict = sanpy.bAnalysisUtil.getStatList()  # maps human readable to comments
        
        metaDataKeys = [key for key in sanpy.MetaData.getMetaDataDict().keys()]

        categoricalList = metaDataKeys
        categoricalList.append('File Number')
        categoricalList.append('Unique Name')

        hueTypes = categoricalList
        # hueTypes = metaDataKeys
        # hueTypes.append('File Number')
        # hueTypes.append('Unique Name')


        sortOrder = ["Sex", "Condition1", "Condition2", "Unique Name"]

        limitToCol = ["epoch"]

        # interfaceDefaults = {
        #     "X Statistic": "Spike Time (s)",
        #     "Y Statistic": "Spike Frequency (Hz)",
        #     "Hue": "Unique Name",
        #     "Style": "None",
        #     "Group By": "Unique Name",
        # }
        interfaceDefaults = None

        # analysisName, masterDf = analysisName, df0 = ba.getReportDf(theMin, theMax, savefile)

        # print('!!!! FIX THIS in plugin plotTool.plot()')
        # masterDf = self._bPlugins._sanpyApp.myAnalysisDir.pool_build()
        # was this
        # masterDf = self.ba.dfReportForScatter

        if self.masterDf is None:
            logger.error("Did not get analysis df, be sure to run detectioon")
            return
        # bScatterPlotMainWindow
        # self.scatterWindow = sanpy.scatterwidget.bScatterPlotMainWindow(
        path = ""
        self.mainWidget2 = sanpy.interface.bScatterPlotMainWindow(
            path,
            categoricalList,
            # hueTypes,
            # analysisName,  # used for group by
            sortOrder,
            statListDict=statListDict,
            masterDf=self.masterDf,
            limitToCol=limitToCol,
            # interfaceDefaults=interfaceDefaults,
        )
        # rewire existing widget into plugin architecture
        # self.mainWidget.closeEvent = self.onClose
        self._mySetWindowTitle()

        # self.mainWidget2.show()

        tmpLayout = QtWidgets.QVBoxLayout()
        tmpLayout.addWidget(self.mainWidget2)

        #
        # self.setLayout(tmpLayout)
        self.getVBoxLayout().addLayout(tmpLayout)
