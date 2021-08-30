
import sanpy
from sanpy.interface.plugins import basePlotTool

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class plotToolPool(basePlotTool):
	"""
	Plot tool pooled across all open analysis
	"""
	myHumanName = 'Plot Tool (pool)'

	def __init__(self, tmpMasterDf=None, **kwargs):
		"""
		tmpMasterDf (pd df): only for debuggin
		"""
		super(plotToolPool, self).__init__(**kwargs)

		if self._bPlugins is not None:
			self.masterDf = self._bPlugins._sanpyApp.myAnalysisDir.pool_build()
		elif tmpMasterDf is not None:
			logger.info('Using tmpMasterDf')
			self.masterDf = tmpMasterDf

		self.plot()

if __name__ == '__main__':
	import sys
	from PyQt5 import QtCore, QtWidgets, QtGui

	app = QtWidgets.QApplication([])

	# load an analysis dir
	path = '/home/cudmore/Sites/SanPy/data'
	ad = sanpy.analysisDir(path, autoLoad=True)
	print(ad._df)
	# load all analysis
	print('\n=== loading all analysis')
	for fileIdx in range(ad.numFiles):
		ad.getAnalysis(fileIdx)
	# build the pool
	print('\n=== building pool')
	tmpMasterDf = ad.pool_build()

	# open window
	print('\n=== opening plotToolPool with tmpMasterDf:', len(tmpMasterDf))
	#print('tmpMasterDf.columns:', tmpMasterDf.columns)
	ptp = plotToolPool(tmpMasterDf=tmpMasterDf)
	ptp.show()

	sys.exit(app.exec_())
