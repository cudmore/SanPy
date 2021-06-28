#20210618
import numbers

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

"""
Functions to get default detection parameters.

Usage:

```python
import sanpy

# dDict is a dictionary with default parameters
dDict = sanpy.bDetection.getDefaultDetection()

# set to your liking
dDict['dvdtThreshold'] = 50

# load a recording
myPath = '../data/19114001.abf'
ba = sanpy.bAnalysis(myPath)

# perform spike detection
ba.spikeDetect(dDict)

# browse results

```

"""
def getDefaultDetection():
	"""
	Get detection parameters including mapping from backend to human readable and long-format descriptions.

	Returns:
		dict: The default detection dictionary.
	"""
	theDict = {}

	key = 'dvdtThreshold'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 100
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = True
	theDict[key]['units'] = 'dVdt'
	theDict[key]['humanName'] = 'dV/dt Threshold'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'dV/dt threshold for a spike, will be backed up to dvdt_percentOfMax and have xxx error when this fails'

	key = 'mvThreshold'
	theDict[key] = {}
	theDict[key]['defaultValue'] = -20
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 'mV'
	theDict[key]['humanName'] = 'mV Threshold'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'mV threshold for spike AND minimum spike mV when detecting with dV/dt'

	key = 'dvdt_percentOfMax'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 0.1
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 'Percent'
	theDict[key]['humanName'] = 'dV/dt Percent of max'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'For dV/dt detection, the final TOP is when dV/dt drops to this percent from dV/dt AP peak'

	key = 'onlyPeaksAbove_mV'
	theDict[key] = {}
	theDict[key]['defaultValue'] = None
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 'mV'
	theDict[key]['humanName'] = 'Accept Peaks Above (mV)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'For dV/dt detection, only accept APs above this value (mV)'

	key = 'doBackupSpikeVm'
	theDict[key] = {}
	theDict[key]['defaultValue'] = True
	theDict[key]['type'] = 'boolean'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 'Boolean'
	theDict[key]['humanName'] = 'Backup Vm Spikes'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'If true, APs detected with just mV will be backed up until Vm falls to xxx'

	key = 'refractory_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 170
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = 'Minimum AP interval (ms)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'APs with interval (wrt previous AP) less than this will be removed'

	key = 'peakWindow_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 100
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = 'Peak Window (ms)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Window after TOP (ms) to seach for AP peak (mV)'

	key = 'dvdtPreWindow_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 10
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = 'dV/dt Pre Window (ms)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Window (ms) to search before each TOP for real threshold crossing'

	key = 'mdp_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 250
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = 'Pre AP MDP window (ms)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Window (ms) before an AP to look for MDP'

	key = 'avgWindow_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 5
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = ''
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Window (ms) to calculate MDP (mV) as a mean rather than mV at single point for MDP'

	key = 'halfHeights'
	theDict[key] = {}
	theDict[key]['defaultValue'] = [10, 20, 50, 80, 90]
	theDict[key]['type'] = 'list' # list of number
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = ''
	theDict[key]['humanName'] = 'AP Durations (%)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'AP Durations as percent of AP height (AP Peak (mV) - TOP (mV))'

	key = 'halfWidthWindow_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 200
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = 'Half Width Window (ms)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Window (ms) after TOP to look for AP Durations'

	key = 'medianFilter'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 0
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False # 0 is no median filter (see SavitzkyGolay_pnts)
	theDict[key]['units'] = 'points'
	theDict[key]['humanName'] = 'Median Filter Points'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Number of points in median filter, must be odd, 0 for no filter'

	key = 'SavitzkyGolay_pnts'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 5
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False # 0 is no filter
	theDict[key]['units'] = 'points'
	theDict[key]['humanName'] = 'SavitzkyGolay Filter Points'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Number of points in SavitzkyGolay filter, must be odd, 0 for no filter'

	key = 'SavitzkyGolay_poly'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 2
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = ''
	theDict[key]['humanName'] = 'Savitzky-Golay Filter Polynomial Degree'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'The degree of the polynomial for Savitzky-Golay filter'

	key = 'spikeClipWidth_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 500
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = 'AP Clip Width (ms)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'The width/duration of generated AP clips'

	key = 'startSeconds'
	theDict[key] = {}
	theDict[key]['defaultValue'] = None
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = True
	theDict[key]['units'] = 's'
	theDict[key]['humanName'] = 'Start(s)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Used to save reports (entire recording is always detected)'

	key = 'stopSeconds'
	theDict[key] = {}
	theDict[key]['defaultValue'] = None
	theDict[key]['type'] = 'number'
	theDict[key]['allowNone'] = True
	theDict[key]['units'] = 's'
	theDict[key]['humanName'] = 'Stop(s)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Used to save reports (entire recording is always detected)'

	key = 'cellType'
	theDict[key] = {}
	theDict[key]['defaultValue'] = ''
	theDict[key]['type'] = 'string'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 's'
	theDict[key]['humanName'] = 'Cell Type'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Cell Type'

	key = 'sex'
	theDict[key] = {}
	theDict[key]['defaultValue'] = ''
	theDict[key]['type'] = 'string'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 's'
	theDict[key]['humanName'] = 'Sex'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Sex'

	key = 'condition'
	theDict[key] = {}
	theDict[key]['defaultValue'] = ''
	theDict[key]['type'] = 'string'
	theDict[key]['allowNone'] = False
	theDict[key]['units'] = 's'
	theDict[key]['humanName'] = 'Condition'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Condition'

	return theDict.copy()


defaultDetection = getDefaultDetection()


def _print():
	"""
	Print out human readable detection parameters and convert to markdown table.

	Requires:
		pip install tabulate
	"""
	import pandas as pd

	d = getDefaultDetection()
	dictList = []
	for k,v in d.items():
		parameter = k
		oneDict = {
			'Parameter': parameter,
			'Default Value': v['defaultValue'],
			'Units': v['units'],
			'Human Readable': v['humanName'],
			'Description': v['description'],
		}
		dictList.append(oneDict)
	#
	df = pd.DataFrame(dictList)
	str = df.to_markdown()
	print(str)

class bDetection(object):
	"""
	Class to manage detection parameters
		- get defauults
		- get values
		- set values
	"""
	def __init__(self):
		# local copy of default dictionary, do not modify
		self._dDict = getDefaultDetection()

		# make local dict of k/v to bbe modified
		self.currentDict = {}
		for k,v in self._dDict.items():
			#print('k:', k)
			#print('v:', v)
			self.currentDict[k] = v['defaultValue']

	def getValue(self, key):
		try:
			return self.currentDict[key]
		except (KeyError) as e:
			logger.warning(f'Did not find key "{key}"')
			# TODO: define default when not found ???
			return None

	def setValue(self, key, value):
		try:
			valueType = type(value)
			valueIsNumber = isinstance(value, numbers.Number)
			valueIsString = isinstance(value, str)
			valueIsBool = isinstance(value, bool)
			valueIsList = isinstance(value, list)
			valueIsNone = value is None

			expectedType = self._dDict[key]['type'] # (number, string, boolean)
			allowNone = self._dDict[key]['allowNone'] # (number, string, boolean)
			if allowNone and valueIsNone:
				pass
			elif expectedType=='number' and not valueIsNumber:
				logger.warning(f'Type mismatch (number) setting key "{key}", got {valueType}, expecting {expectedType}')
				return False
			elif expectedType=='string' and not valueIsString:
				logger.warning(f'Type mismatch (string) setting "{key}", got {valueType}, expecting {expectedType}')
				return False
			elif expectedType=='boolean' and not valueIsBool:
				logger.warning(f'Type mismatch (bool) setting "{key}", got {valueType}, expecting {expectedType}')
				return False
			elif expectedType=='list' and not valueIsList:
				logger.warning(f'Type mismatch (list) setting "{key}", got {valueType}, expecting {expectedType}')
				return False
			# set
			self.currentDict[key] = value

			return True
		except (KeyError) as e:
			logger.warning(f'Did not find key "{key}" to set to "{value}"')
			return False

	def setFromDict(self, dDict):
		"""
		Set detection from key/values in dDict

		Args:
			dDict (dict): Usually a table row
		"""
		gotError = False
		for k,v in dDict.items():
			ok = self.setValue(k, v)
			if not ok:
				gotError = True
		return gotError

def test_0():
	bd = bDetection()

	#xxx = bd.getValue('xxx')

	#ok = bd.setValue('xxx', 2)
	#print('ok:', ok)

	ok1 = bd.setValue('dvdtThreshold', None)
	if not ok1:
		print('ok1:', ok1)

	ok1_5 = bd.setValue('mvThreshold', None)
	if not ok1_5:
		print('ok1_5:', ok1_5)

	ok2 = bd.setValue('cellType', '111')
	if not ok2:
		print('ok2:', ok2)

	# for setting list, check that (i) not empty and (ii) list[i] == expected type
	ok3 = bd.setValue('halfHeights', [])
	if not ok3:
		print('ok3:', ok3)

	# start/stop seconds defaults to None but we want 'number'
	ok4 = bd.setValue('startSeconds', 1e6)
	if not ok4:
		print('ok4:', ok4)

	tmpDict = {'Idx': 2.0, 'Include': 1.0, 'File': '19114001.abf', 'Dur(s)': 60.0, 'kHz': 20.0, 'Mode': 'fix', 'Cell Type': '', 'Sex': '', 'Condition': '', 'Start(s)': nan, 'Stop(s)': nan, 'dvdtThreshold': 50.0, 'mvThreshold': -20.0, 'refractory_ms': nan, 'peakWindow_ms': nan, 'halfWidthWindow_ms': nan, 'Notes': ''}
	for k,v in tmpDict.items():
		print('  ', k, ':', v)

if __name__ == '__main__':
	test_0()
