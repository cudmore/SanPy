"""
Utilities to define analysis results.

These are keys in bAnalysis_ spike dict and columns in output reports
"""

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

defaultVal = float('nan')

# each key in analysisResultDict needs to have the same dict
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

analysisResultDict = {}

key = 'analysisVersion'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'str'
analysisResultDict[key]['default'] = ''
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'Analysis version when analysis was run. See sanpy.analysisVersion'

key = 'interfaceVersion'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'str'
analysisResultDict[key]['default'] = ''
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'Interface version string when analysis was run. See sanpy.interfaceVersion'

key = 'file'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'str'
analysisResultDict[key]['default'] = ''
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'Name of raw data file analyzed'

key = 'detectionType'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = ''
analysisResultDict[key]['default'] = None
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'Type of detection, either vm or dvdt. See enum sanpy.bDetection.detectionTypes'

key = 'cellType'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'str'
analysisResultDict[key]['default'] = ''
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'User specified cell type'

key = 'sex'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'str'
analysisResultDict[key]['default'] = ''
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'User specified sex'

key = 'condition'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'str'
analysisResultDict[key]['default'] = ''
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'User specified condition'

#
# start real analysis results
key = 'sweep'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = 0  # todo: not sure
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'Sweep number of analyzed sweep. Zero based.'

key = 'sweepSpikeNumber'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = None  # todo: not sure
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'Spike number within the sweep. Zero based.'

key = 'spikeNumber'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = None  # todo: not sure
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'Spike number across all sweeps. Zero based.'

key = 'include'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'bool'
analysisResultDict[key]['default'] = True
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'Boolean indication include or not. Can be set by user/programatically after analysis.'

key = 'userType'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = 0
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'Integer indication user type. Can be set by user/programatically after analysis.'


key = 'errors'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'list'
analysisResultDict[key]['default'] = []
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'List of dictionary to hold detection errors for this spike'

#
# detection parameters
key = 'dvdtThreshold'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'dvdt'
analysisResultDict[key]['depends on detection'] = 'dvdtThreshold'
analysisResultDict[key]['description'] = 'AP Threshold in derivative dv/dt'

key = 'mvThreshold'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'mV'
analysisResultDict[key]['depends on detection'] = 'mvThreshold'
analysisResultDict[key]['description'] = 'AP Threshold in primary recording mV'

# todo: what about solay ...
key = 'medianFilter'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = 0
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['depends on detection'] = 'medianFilter'
analysisResultDict[key]['description'] = 'Median filter to generate filtered vm and dvdt. Value 0 indicates no filter.'

key = 'halfHeights'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'list'
analysisResultDict[key]['default'] = []
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['depends on detection'] = 'halfHeights'
analysisResultDict[key]['description'] = 'List of int to specify half-heights like [10, 20, 50, 80, 90].'

#
# actual value coming out of detection !!!!
key = 'thresholdPnt'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'point'
analysisResultDict[key]['description'] = 'AP threshold point'

key = 'thresholdSec'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'sec'
analysisResultDict[key]['description'] = 'AP threshold seconds'

key = 'thresholdVal'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'mV'  # TODO: will be pA for voltage-clamp
analysisResultDict[key]['description'] = 'Value of Vm at AP threshold point.'

key = 'thresholdVal_dvdt'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'dvdt'  # TODO: will be pA for voltage-clamp
analysisResultDict[key]['description'] = 'Value of dvdt at AP threshold point.'

key = 'dacCommand'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'mV'  # TODO: will be pA for voltage-clamp
analysisResultDict[key]['description'] = 'Value of DAC command at AP threshold point.'

key = 'peakPnt'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'point'
analysisResultDict[key]['depends on detection'] = '(onlyPeaksAbove_mV, peakWindow_ms)'
analysisResultDict[key]['description'] = 'AP peak point.'

key = 'peakSec'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'sec'
analysisResultDict[key]['description'] = 'AP peak seconds.'

key = 'peakVal'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'mV' # voltage-clamp'
analysisResultDict[key]['description'] = 'Value of Vm at AP peak point.'

key = 'peakHeight'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'mV'  # voltage-clamp
analysisResultDict[key]['description'] = 'Difference between peakVal minus thresholdVal.'

key = 'timeToPeak_ms'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'ms' # voltage-clamp'
analysisResultDict[key]['description'] = 'Time to peak (ms) after TOP.'

key = 'preMinPnt'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'point'  # voltage-clamp
analysisResultDict[key]['depends on detection'] = 'mdp_ms'
analysisResultDict[key]['description'] = 'Minimum before an AP taken from predefined window.'

key = 'preMinVal'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'mV'  # voltage-clamp
analysisResultDict[key]['description'] = 'Minimum before an AP taken from predefined window.'

key = 'preLinearFitPnt0'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'point'  # voltage-clamp
analysisResultDict[key]['description'] = 'Point where pre linear fit starts. Used for EDD Rate'

key = 'preLinearFitPnt1'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'point'  # voltage-clamp
analysisResultDict[key]['description'] = 'Point where pre linear fit stops. Used for EDD Rate'

key = 'earlyDiastolicDuration_ms'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'ms'  # voltage-clamp
analysisResultDict[key]['description'] = 'Time (ms) between start/stop of EDD.'

key = 'preLinearFitVal0'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'mv'  # voltage-clam
analysisResultDict[key]['description'] = ''

key = 'preLinearFitVal1'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'mv'
analysisResultDict[key]['description'] = ''

key = 'earlyDiastolicDurationRate'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'mv/S'
analysisResultDict[key]['description'] = 'Early diastolic duration rate, the slope of the linear fit between start/stop of EDD.'

key = 'lateDiastolicDuration'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'TODO: Not sure this is implemented'

key = 'preSpike_dvdt_max_pnt'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'point'
analysisResultDict[key]['description'] = 'Point corresponding to peak in dv/dt before an AP.'

key = 'preSpike_dvdt_max_val'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'mV'
analysisResultDict[key]['description'] = 'Value of Vm at peak of dv/dt before an AP.'

key = 'preSpike_dvdt_max_val2'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'dv/dt'
analysisResultDict[key]['description'] = 'Value of dv/dt at peak of dv/dt before an AP.'

key = 'postSpike_dvdt_min_pnt'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'point'
analysisResultDict[key]['depends on detection'] = 'dvdtPostWindow_ms'
analysisResultDict[key]['description'] = 'Point corresponding to min in dv/dt after an AP.'

key = 'postSpike_dvdt_min_val'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'mV'
analysisResultDict[key]['description'] = 'Value of Vm at minimum of dv/dt after an AP.'

key = 'postSpike_dvdt_min_val2'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'dvdt'
analysisResultDict[key]['description'] = 'Value of dv/dt at minimum of dv/dt after an AP.'

key = 'isi_pnts'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'point'
analysisResultDict[key]['depends on detection'] = 'refractory_ms'
analysisResultDict[key]['description'] = 'Inter-Spike-Interval (points) with respect to previous AP.'

key = 'isi_ms'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'ms'
analysisResultDict[key]['description'] = 'Inter-Spike-Interval (ms) with respect to previous AP.'

key = 'spikeFreq_hz'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'Hz'
analysisResultDict[key]['description'] = 'AP frequency with respect to previous AP.'

key = 'cycleLength_pnts'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'point'
analysisResultDict[key]['description'] = 'Points between APs with respect to previous AP.'

key = 'cycleLength_ms'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'int'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'point'
analysisResultDict[key]['description'] = 'Time (ms) between APs with respect to previous AP.'

key = 'diastolicDuration_ms'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'float'
analysisResultDict[key]['default'] = defaultVal
analysisResultDict[key]['units'] = 'ms'
analysisResultDict[key]['description'] = 'Time (ms) between minimum before AP (preMinPnt) and AP time (thresholdPnt).'

key = 'widths'
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]['type'] = 'list'
analysisResultDict[key]['default'] = []
analysisResultDict[key]['units'] = ''
analysisResultDict[key]['description'] = 'A list of dict to hold half-height information for each half-height in detection halfHeights.'

# need to define keys width_<i> from halfHeights list [10, 20, 50, 80, 90]
for i in [10, 20, 50, 80, 90]:
	key = 'widths_' + str(i)
	analysisResultDict[key] = getDefaultDict()
	analysisResultDict[key]['type'] = 'int'
	analysisResultDict[key]['default'] = defaultVal
	analysisResultDict[key]['units'] = 'percent'
	analysisResultDict[key]['depends on detection'] = 'halfWidthWindow_ms'
	analysisResultDict[key]['description'] = f'Width (ms) at half-height {i} %.'

# now we have (AP threshold, AP peak), derive stats about each AP

def printDocs():
	"""
	Print out human readable detection parameters and convert to markdown table.

	Requires:
		pip install tabulate

	See: bDetection.printDocs()
	"""
	import pandas as pd
	from datetime import datetime

	logger.info('Ensure there are no errors')

	dictList = []
	for k, v in analysisResultDict.items():
		# iterating on getDefaultDict() to ensure all code above has valid k/v pairs
		#lineStr = k + '\t'
		oneDict = {
			'Name': k,
		}
		for k2 in getDefaultDict().keys():
			#print(f'  {k}: {k2}: {v[k2]}')
			#lineStr += f'{v[k2]}' + '\t'
			oneDict[k2] = v[k2]
		#
		#print(lineStr)

		dictList.append(oneDict)

		# check that k is in headerDefaultDict
		for k3 in v:
			if not k3 in getDefaultDict().keys():
				logger.error(f'Found extra key "{k}" in "analysisResultDict"')

	#
	df = pd.DataFrame(dictList)
	#str = df.to_markdown()
	str = df.to_html()
	myDate = datetime.today().strftime('%Y-%m-%d')
	print(f'Generated {myDate} with sanpy.analysisVersion {sanpy.analysisVersion}')
	print(str)

class analysisResultList:
	"""
	Class encapsulating a list of analysisResultDict (one dict per spike)
	"""
	def __init__(self):
		# one copy for entire list
		self._dDict = analysisResultDict

		# list of analysisResultDict
		self._myList = []

		self._iterIdx = -1

	def appendDefault(self):
		"""Append a spike to analysis."""
		oneResult = analysisResult()
		self._myList.append(oneResult)

	def addAnalysisResult(self, theKey, theDefault=None):

		# go through list and add to each [i] dict
		for spike in self:
			spike.addNewKey(theKey, theDefault=theDefault)

	def aslist(self):
		"""
		Return underlying list.

		Needed to create pandas dataframe from list.
		See bExport.xxx.
		"""
		return [spike.asDict() for spike in self._myList]

	def __getitem__(self, key):
		"""
		Allow [] indexing with self[int].
		"""
		try:
			#return self._dDict[key]['currentValue']
			return self._myList[key]
		except (IndexError) as e:
			logger.error(f'{e}')

	def __len__(self):
		""" Allow len() with len(this)
		"""
		return len(self._myList)

	def __iter__(self):
		"""
		Allow iteration with "for item in self"
		"""
		return self

	def __next__(self):
		"""
		Allow iteration with "for item in self"
		"""
		self._iterIdx += 1
		if self._iterIdx >= len(self._myList):
			self._iterIdx = -1 # reset to initial value
			raise StopIteration
		else:
			return self._myList[self._iterIdx]


class analysisResult:
	def __init__(self):
		# this is the raw definition of analysis results (See above)
		# pull from this to create key/value self.rDict
		#self._dDict = analysisResultDict
		defaultDict = analysisResultDict
		# this is simple key/value pairs as we will in detection
		self._rDict = {}
		for k,v in defaultDict.items():
			default = v['default']
			self._rDict[k] = default

	def __str__(self):
		'''
		for k,v in self._rDict.items():
			if k == 'widths':
				widths = v
				for idx2, width in enumerate(widths):
					print(f'{idx2}')
					print(width)
			else:
				print(f'key:{k} v:{v}')
		return str('xxx')
		'''
		return str(self._rDict)

	def addNewKey(self, theKey, theDefault=None):
		"""
		Add a new key to this spike.

		Returns: (bool) True if new key added, false if key already exists.
		"""
		if theDefault is None:
			#theType = 'float'
			theDefault = float('nan')

		# check if key exists
		keyExists = theKey in self._rDict.keys()
		addedKey = False
		if keyExists:
			 #key exists, don't modify
			 #logger.warning(f'The key "{theKey}" already exists and has value "{self._rDict[theKey]}"')
			 pass
		else:
			self._rDict[theKey] = theDefault
			addedKey = True

		#
		return addedKey

	def asDict(self):
		"""
		Returns underlying dictionary
		"""
		return self._rDict

	def __getitem__(self, key):
		# to mimic a dictionary
		ret = None
		try:
			#return self._dDict[key]['currentValue']
			ret = self._rDict[key]
		except (KeyError) as e:
			logger.error(f'Error getting key "{key}" exception:{e}')
			raise
		#
		return ret

	def __setitem__(self, key, value):
		# to mimic a dictionary
		try:
			#self._dDict[key]['currentValue'] = value
			self._rDict[key] = value
		except (KeyError) as e:
			logger.error(f'{e}')

	def items(self):
		# to mimic a dictionary
		return self._rDict.items()

	def keys(self):
		# to mimic a dictionary
		return self._rDict.keys()


def test():
	for k,v in analysisResultDict.items():
		print(k,v)

	ar = analysisResults()

	key = 'analysisVersion'
	print(f'key:{key} value:"{ar[key]}" type:{type(ar[key])}')

	key = 'errors'
	print(f'key:{key} value:"{ar[key]}" type:{type(ar[key])}')

def test2():
	# load abf
	path = '/home/cudmore/Sites/SanPy/data/19114000.abf'
	ba = sanpy.bAnalysis(path)

	# detect
	sweepNumber = 0
	detectionClass = ba.detectionClass
	detectionClass['verbose'] = True
	ba.spikeDetect2__(sweepNumber, detectionClass)

	'''
	printSpikeNum = 4
	print(f'== printing spike {printSpikeNum}')
	ba.printSpike(printSpikeNum)
	'''

	#ba.printErrors()

	sd = ba.getSpikeDictionaries()
	'''
	for idx, s in enumerate(sd):
		if idx == 2:
			print(s)
	'''

if __name__ == '__main__':
	#test()
	test2()
	#printDocs()
