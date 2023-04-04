import sanpy
from sanpy.interface.plugins import basePlotTool

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class plotTool(basePlotTool):
    """
    Plot tool for one bAnalysis
    """

    myHumanName = "Plot Tool"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.masterDf = None
        if self.ba is not None and self.ba.isAnalyzed():
            self.masterDf = self.ba.asDataFrame()
            self.masterDf["File Number"] = 0
        self.plot()
