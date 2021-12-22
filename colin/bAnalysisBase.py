"""
20211217
Robert H Cudmore

Encapsulate a Pandas DataFrame. User will derive their own class to specify unique analysis.
"""

"""
def getDefaultDict():
	defaultDict = {
		'type': '',  # like: int, float, boolean, list
		'default': '',  # default value, can be 0, None, NaN, ...
		'units': '',  # real world units like point, mV, dvdt
		'depends on detection': '',  # organize documentation and refer to bDetect keys
		'error': '',  # if this analysis results can trigger an error
		'description': '',  # long description for documentation
		}
	return defaultDict.copy()
"""

import pandas as pd
import numpy as np

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class baseAnalysis:
	def getDefaultStatDict():
		defaultDict = {
			'statName': '',  # column in dataframe
			'humanName': '',  # to show in display
			'type': '',  # like: int, float, boolean, list
			'default': '',  # default value, can be 0, None, NaN, ...
			'units': '',  # real world units like point, mV, dvdt
			'depends on detection': '',  # organize documentation and refer to bDetect keys
			'error': '',  # if this analysis results can trigger an error
			'description': '',  # long description for documentation
			}
		return defaultDict.copy()

	def __init__(self):
		self._df = pd.DataFrame()

		self._dict = {}
		""" A dictionary to hold key (stat) and value (dict with description of stat).
			Each key corresponds to column in self._df
		"""

	'''
	def __str__(self):
		return print(self.dataframe)
	'''

	@property
	def dataframe(self):
		return self._df

	def len(self):
		return len(self.dataframe)

	def addStat(self, colStr, defaultValues=None):
		if self._colInDataFrame(colStr):
			logger.error(f'"{colStr}" is already a column in dataframe.')
			return
		self.dataframe[colStr] = defaultValues

	def getVal(self, rowIdx:int, colStr:str):
		"""
		Get one value.
		"""
		if not self._colInDataFrame(colStr):
			logger.error(f'Did not find "{colStr}" in dataframe columns.')
			return
		if rowIdx > self.len() -1:
			logger.error(f'Did not row {rowIdx} in dataframe with {self.len()} rows.')
			return

		val = self.dataframe.loc[rowIdx, colStr]
		return val

	def setVal(self, rowIdx:int, colStr:str, val):
		"""
		Set one value.
		"""
		if not self._colInDataFrame(colStr):
			logger.error(f'Did not find "{colStr}" in dataframe columns.')
			return
		if rowIdx > self.len() -1:
			logger.error(f'Did not row {rowIdx} in dataframe with {self.len()} rows.')
			return

		self.dataframe.loc[rowIdx, colStr] = val

	def getCol(self, colStr):
		"""
		Get an entire column of values
		"""
		if not self._colInDataFrame(colStr):
			logger.error(f'Did not find "{colStr}" in dataframe columns.')
			return
		return self.dataframe[colStr]

	def setCol(self, colStr, values):
		"""
		Set an entire column with values
		"""
		if not self._colInDataFrame(colStr):
			logger.error(f'Did not find "{colStr}" in dataframe columns')
			return
		# check that value has correct length
		if len(values) != self.len():
			logger.error(f'Length of values with {len(values)} does not match dataframe length of {self.len()}')
			return

		self.dataframe[colStr] = values

	def _colInDataFrame(self, colStr):
		return colStr in self.dataframe.columns

class stochAnalysis(baseAnalysis):
	def __init__(self):
		super(stochAnalysis, self).__init__()

def testRun():
	sa = stochAnalysis()

	#sa.appendColumn('xxx')
	#sa.appendColumn('yyy')

	#baseAnalysis.getDefaultStatDict['statName'] = 'peakTimeSec'

	sa.addStat('zzz')
	sa.addStat('xxx')

	sa.setCol('xxx', [1,2,3])
	sa.setCol('yyy', ['a', 'b', 'c'])

	# produce an error
	#sa.getCol('axxx')

	print('sa:', sa.dataframe)

	val = sa.getVal(0, 'xxx')
	print('val:', val)

	sa.setVal(0, 'xxx', 13)
	val = sa.getVal(0, 'xxx')
	print('new val:', val)

if __name__ == '__main__':
	testRun()
