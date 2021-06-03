
"""
Functions to get default detection parameters.

Usage:

```python
import sanpy

# dDict is a dictionary with default parameters
dDict = sanpy.detectionParams.getDefaultDetection()

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
	theDict[key]['units'] = 'dVdt'
	theDict[key]['humanName'] = 'dV/dt Threshold'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'dV/dt threshold for a spike, will be backed up to dvdt_percentOfMax and have xxx error when this fails'

	key = 'mvThreshold'
	theDict[key] = {}
	theDict[key]['defaultValue'] = -20
	theDict[key]['units'] = 'mV'
	theDict[key]['humanName'] = 'mV Threshold'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'mV threshold for spike AND minimum spike mV when detecting with dV/dt'

	key = 'dvdt_percentOfMax'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 0.1
	theDict[key]['units'] = 'Percent'
	theDict[key]['humanName'] = 'dV/dt Percent of max'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'For dV/dt detection, the final TOP is when dV/dt drops to this percent from dV/dt AP peak'

	key = 'onlyPeaksAbove_mV'
	theDict[key] = {}
	theDict[key]['defaultValue'] = None
	theDict[key]['units'] = 'mV'
	theDict[key]['humanName'] = 'Accept Peaks Above (mV)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'For dV/dt detection, only accept APs above this value (mV)'

	key = 'doBackupSpikeVm'
	theDict[key] = {}
	theDict[key]['defaultValue'] = True
	theDict[key]['units'] = 'Boolean'
	theDict[key]['humanName'] = 'Backup Vm Spikes'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'If true, APs detected with just mV will be backed up until Vm falls to xxx'

	key = 'refractory_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 170
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = 'Minimum AP interval (ms)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'APs with interval (with respect to previous AP) less than this will be removed'

	key = 'peakWindow_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 100
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = 'Peak Window (ms)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Window after TOP (ms) to seach for AP peak (mV)'

	key = 'dvdtPreWindow_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 10
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = 'dV/dt Pre Window (ms)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Window (ms) to search before each TOP for real threshold crossing'

	key = 'mdp_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 250
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = 'Pre AP MDP window (ms)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Window (ms) before an AP to look for MDP'

	key = 'avgWindow_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 5
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = ''
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Window (ms) to calculate MDP (mV) as a mean rather than mV at single point for MDP'

	key = 'halfHeights'
	theDict[key] = {}
	theDict[key]['defaultValue'] = [10, 20, 50, 80, 90]
	theDict[key]['units'] = ''
	theDict[key]['humanName'] = 'AP Durations (%)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'AP Durations as percent of AP height (AP Peak (mV) - TOP (mV))'

	key = 'halfWidthWindow_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 200
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = 'Half Width Window (ms)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Window (ms) after TOP to look for AP Durations'

	key = 'medianFilter'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 0
	theDict[key]['units'] = 'points'
	theDict[key]['humanName'] = 'Median Filter Points'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Number of points in median filter, must be odd, 0 for no filter'

	key = 'SavitzkyGolay_pnts'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 5
	theDict[key]['units'] = 'points'
	theDict[key]['humanName'] = 'SavitzkyGolay Filter Points'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'Number of points in SavitzkyGolay filter, must be odd, 0 for no filter'

	key = 'SavitzkyGolay_poly'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 2
	theDict[key]['units'] = ''
	theDict[key]['humanName'] = 'Savitzky-Golay Filter Polynomial Degree'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'The degree of the polynomial for Savitzky-Golay filter'

	key = 'spikeClipWidth_ms'
	theDict[key] = {}
	theDict[key]['defaultValue'] = 500
	theDict[key]['units'] = 'ms'
	theDict[key]['humanName'] = 'AP Clip Width (ms)'
	theDict[key]['errors'] = ('')
	theDict[key]['description'] = 'The width/duration of generated AP clips'


	return theDict.copy()

def _print():
	"""
	Print out human readable detection parameters and convert to markdown table

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

if __name__ == '__main__':
	_print()
