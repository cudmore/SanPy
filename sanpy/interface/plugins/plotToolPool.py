import sanpy
from sanpy.interface.plugins import basePlotTool

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class plotToolPool(basePlotTool):
	"""
	Plot tool pooled across all open analysis
	"""
	myHumanName = 'Plot Tool (pool)'

	def __init__(self, **kwargs):
		super(plotToolPool, self).__init__(**kwargs)

		self.masterDf = self._bPlugins._sanpyApp.myAnalysisDir.pool_build()

		self.plot()
