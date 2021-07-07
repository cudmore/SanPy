import sanpy
from sanpy.interface.plugins import basePlotTool

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class plotTool(basePlotTool):
	"""
	Plot tool for one bAnalysis
	"""
	myHumanName = 'Plot Tool'

	def __init__(self, **kwargs):
		super(plotTool, self).__init__(**kwargs)
		self.masterDf = self.ba.dfReportForScatter
		self.plot()
