# Author: Robert Cudmore
# Date: 20190627

import sys, os, json
from collections import OrderedDict

# todo: move these to a json file !!!
# A list of human readable stats and how to map them to backend
# Each key, like 'Take Off Potential (mV)' is a y-stat

import sanpy
#import sanpy.useranalysis
#from . import useranalysis
from .useranalysis import findUserAnalysis

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)


"""
A dictionary of detection parameters.
"""

"""
Functions to map human readable name to backend stat name and vica versa.

See [xxx-methods](../../Methods) section for a list of available stats

Example:

```
from sanpy.bAnalysisUtil import getHumandFromStat, getStatFromHuman

humanStr = getHumandFromStat('thresholdSec')
statStr = getStatFromHuman('Spike Time (s)')
```

"""

# add this to keep al key VALUES the same
# or maybe make a class??? like bDetection (which holds detection parameters?)
'''
def _defaultStatDict():
	return
'''

statList = OrderedDict()
statList['Spike Time (s)'] = {
	'name': 'thresholdSec',
	'units': 's',
	'yStat': 'thresholdVal',
	'yStatUnits': 'mV',
	'xStat': 'thresholdSec',
	'xStatUnits': 's'
	}
statList['Spike Number'] = {
	'name': 'spikeNumber',
	'units': '',
	'yStat': '',
	'yStatUnits': '',
	'xStat': 'spikeNumber',
	'xStatUnits': ''
	}
statList['Sweep Spike Number'] = {
	'name': 'sweepSpikeNumber',
	'units': '',
	'yStat': '',
	'yStatUnits': '',
	'xStat': 'sweepSpikeNumber',
	'xStatUnits': ''
	}
statList['Sweep Number'] = {
	'name': 'sweep',
	'units': '',
	'yStat': 'sweep',
	'yStatUnits': '',
	'xStat': '',
	'xStatUnits': ''
	}
statList['DAC Command'] = {
	'name': 'dacCommand',
	'units': '',
	'yStat': 'dacCommand',
	'yStatUnits': '',
	'xStat': '',
	'xStatUnits': ''
	}
statList['Take Off Potential (mV)'] = {
	'name': 'thresholdVal',
	'units': 'mV',
	'yStat': 'thresholdVal',
	'yStatUnits': 'mV',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}
statList['Spike Frequency (Hz)'] = {
	'name': 'spikeFreq_hz',
	'units': 'Hz',
	'yStat': 'spikeFreq_hz',
	'yStatUnits': 'Hz',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}
statList['Inter-Spike-Interval (ms)'] = {
	'name': 'isi_ms',
	'units': 'ms',
	'yStat': 'isi_ms',
	'yStatUnits': 'ms',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}
statList['Cycle Length (ms)'] = {
	'name': 'cycleLength_ms',
	'units': 'ms',
	'yStat': 'cycleLength_ms',
	'yStatUnits': 'ms',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}
statList['AP Peak (mV)'] = {
	'name': 'peakVal',
	'units': 'mV',
	'yStat': 'peakVal',
	'yStatUnits': 'mV',
	'xStat': 'peakPnt',
	'xStatUnits': 'Points'
	}
#spikeDict['peakVal'] - spikeDict['thresholdVal']
statList['AP Height (mV)'] = {
	'name': 'peakHeight',
	'units': 'mV',
	'yStat': 'peakHeight',
	'yStatUnits': 'mV',
	'xStat': 'peakPnt',
	'xStatUnits': 'Points'
	}
statList['Pre AP Min (mV)'] = {
	'name': 'preMinVal',
	'units': 'mV',
	'yStat': 'preMinVal',
	'yStatUnits': 'mV',
	'xStat': 'preMinPnt',
	'xStatUnits': 'Points'
	}
statList['Post AP Min (mV)'] = {
	'name': 'postMinVal',
	'units': 'mV',
	'yStat': 'postMinVal',
	'yStatUnits': 'mV',
	'xStat': 'postMinPnt',
	'xStatUnits': 'Points'
	}
# todo: fix this
statList['Early Diastolic Depol Rate (dV/s)'] = {
	'name': 'earlyDiastolicDurationRate',
	'units': 'dV/s',
	'yStat': 'earlyDiastolicDurationRate',
	'yStatUnits': 'dV/s',
	'xStat': '',
	'xStatUnits': ''
	}
# todo: fix this
statList['Early Diastolic Duration (ms)'] = {
	'name': 'earlyDiastolicDuration_ms',
	'units': 'ms',
	'yStat': 'earlyDiastolicDuration_ms',
	'yStatUnits': 'dV/s',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}

statList['Diastolic Duration (ms)'] = {
	'name': 'diastolicDuration_ms',
	'units': 'ms',
	'yStat': 'diastolicDuration_ms',
	'yStatUnits': 'dV/s',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}
statList['Max AP Upstroke (mV)'] = {
	'name': 'preSpike_dvdt_max_val',
	'units': 'mV',
	'yStat': 'preSpike_dvdt_max_val',
	'yStatUnits': 'dV/s',
	'xStat': 'preSpike_dvdt_max_pnt',
	'xStatUnits': 'Points'
	}
statList['Max AP Upstroke (dV/dt)'] = {
	'name': 'preSpike_dvdt_max_val2',
	'units': 'dV/dt',
	'yStat': 'preSpike_dvdt_max_val2',
	'yStatUnits': 'dV/dt',
	'xStat': 'preSpike_dvdt_max_pnt',
	'xStatUnits': 'Points'
	}
statList['Max AP Repolarization (mV)'] = {
	'name': 'postSpike_dvdt_min_val',
	'units': 'mV',
	'yStat': 'postSpike_dvdt_min_val',
	'yStatUnits': 'mV',
	'xStat': 'postSpike_dvdt_min_pnt',
	'xStatUnits': 'Points'
	}
# todo: fix this
statList['AP Duration (ms)'] = {
	'name': 'apDuration_ms',
	'units': 'ms',
	'yStat': 'apDuration_ms',
	'yStatUnits': 'ms',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}

# new 20210211
statList['Half Width 10 (ms)'] = {
	'name': 'widths_10',
	'yStat': 'widths_10',
	'yStatUnits': 'ms',
	'xStat': '',
	'xStatUnits': ''
	}
statList['Half Width 20 (ms)'] = {
	'name': 'widths_20',
	'yStat': 'widths_20',
	'yStatUnits': 'ms',
	'xStat': '',
	'xStatUnits': ''
	}
statList['Half Width 50 (ms)'] = {
	'name': 'widths_50',
	'yStat': 'widths_50',
	'yStatUnits': 'ms',
	'xStat': '',
	'xStatUnits': ''
	}
statList['Half Width 80 (ms)'] = {
	'name': 'widths_80',
	'yStat': 'widths_80',
	'yStatUnits': 'ms',
	'xStat': '',
	'xStatUnits': ''
	}
statList['Half Width 90 (ms)'] = {
	'name': 'widths_90',
	'yStat': 'widths_90',
	'yStatUnits': 'ms',
	'xStat': '',
	'xStatUnits': ''
	}
# sa node specific
'''
statList['Region'] = {
	'yStat': 'Region',
	'yStatUnits': '',
	'xStat': '',
	'xStatUnits': ''
	}
'''
# kymograph analysis
statList['Ca++ Delay (s)'] = {
	'yStat': 'caDelay_sec',
	'yStatUnits': 's',
	'xStat': '',
	'xStatUnits': ''
	}
statList['Ca++ Width (ms)'] = {
	'yStat': 'caWidth_ms',
	'yStatUnits': 'ms',
	'xStat': '',
	'xStatUnits': ''
	}

def getHumanFromStat(statName):
	"""Get human readable stat name from backend stat name."""
	ret = ''
	for k,v in statList.items():
		name = v['name']
		if name == statName:
			ret = k
			break
	if ret =='':
		logger.warning(f'Did not find "{statName}"')
	#
	return ret

def getStatFromHuman(humanStat):
	"""Get backend stat name from human readable stat."""
	ret = ''
	try:
		ret = statList[humanStat]['name']
	except (KeyError) as e:
		logger.warning(f'Bad key "{humanStat}"')
	#
	return ret

def _print():
	"""
	Print out human readable detection parameters and convert to markdown table

	Requires:
		pip install tabulate
	"""
	import pandas as pd

	# statList is a dict with keys, one key per stat
	d = statList

	dictList = []
	for k,v in d.items():
		stat = k
		oneDict = {
			'Stat': stat,
		}
		for k2,v2 in v.items():
			oneDict[k2] = v2

		dictList.append(oneDict)
	#
	df = pd.DataFrame(dictList)
	str = df.to_markdown()
	print(str)

class bAnalysisUtil:
	def __init__(self):
		self.configDict = self.configDefault()

		# load preferences
		if getattr(sys, 'frozen', False):
			# we are running in a bundle (frozen)
			bundle_dir = sys._MEIPASS
		else:
			# we are running in a normal Python environment
			bundle_dir = os.path.dirname(os.path.abspath(__file__))
		self.configFilePath = os.path.join(bundle_dir, 'AnalysisApp_Config.json')

		self.configLoad()

		# self.top = None  # used by tkinter interface

	@staticmethod
	def getStatList():
		"""20210929 working on extending stat list with sanpy.userAnalysis

		We first define stat list in this function as statList
		We then ask for user defined stat functions static members xxx
		"""
		coreStateList = statList  # from global withing function

		#userStatList = sanpy.useranalysis.findUserAnalysis()
		userStatList = findUserAnalysis()

		for k, v in userStatList.items():
			# check if key exists !!!
			if k in coreStateList.keys():
				logger.error(f'key {k} already exists in statList')
			else:
				name = v['name']
				coreStateList[k] = {}
				coreStateList[k][name] = name

		return coreStateList

	'''
	@staticmethod
	def humanStatToBackend(theStat):
		return ''
	'''

	def prettyPrint(self):
		print(json.dumps(self.configDict, indent=4, sort_keys=True))

	def getDetectionConfig(self):
		return self.config

	def getDetectionParam(self, theParam):
		if theParam in self.configDict['detection'].keys():
			return self.configDict['detection'][theParam]['value']
		else:
			print('error: bAnalysisUtil.getDetectionParam() detection parameter not found:', theParam)
			return None

	def getDetectionDescription(self, theParam):
		if theParam in self.configDict['detection'].keys():
			return self.configDict['detection'][theParam]['meaning']
		else:
			print('error: bAnalysisUtil.getDetectionDescription() detection parameter not found:', theParam)
			return None

	def setDetectionParam(self, theParam, theValue):
		if theParam in self.configDict['detection'].keys():
			self.configDict['detection'][theParam]['value'] = theValue
		else:
			print('error: bAnalysisUtil.setDetectionParam() detection parameter not found:', theParam)
			return None

	def configSave(self):
		print('bAnalysisUtil.configSave()')
		with open(self.configFilePath, 'w') as outfile:
			json.dump(self.configDict, outfile, indent=4, sort_keys=True)

	def configLoad(self):
		if os.path.isfile(self.configFilePath):
			print('	bAnalysisUtil.configLoad() loading configFile file:', self.configFilePath)
			with open(self.configFilePath) as f:
				self.configDict = json.load(f)
		else:
			#print('	bAnalysisUtil.preferencesLoad() using program provided default options')
			self.configDefault()

	def configDefault(self):
		theRet = OrderedDict()

		theRet['detection'] = OrderedDict()

		theRet['detection']['dvdtThreshold'] = OrderedDict()
		theRet['detection']['dvdtThreshold'] = {
			'value': 100,
			'meaning': 'Threshold crossing in dV/dt',
		}

		theRet['detection']['minSpikeVm'] = OrderedDict()
		theRet['detection']['minSpikeVm'] = {
			'value': -20,
			'meaning': 'Minimum Vm to accept a detected spike',
		}

		theRet['detection']['medianFilter'] = OrderedDict()
		theRet['detection']['medianFilter'] = {
			'value': 5,
			'meaning': 'Median filter for Vm (must be odd)',
		}

		theRet['detection']['minISI_ms'] = OrderedDict()
		theRet['detection']['minISI_ms'] = {
			'value': 75,
			'meaning': 'Minimum allowable inter-spike-interval (ms), anything shorter than this will be rejected',
		}

		return theRet

	# abb removed 20201109, not using this, write a PyQt preferences panel
	'''
	def tk_PreferenesPanel(self, app):
		"""
		app: tkinter.Tk()
		"""
		myPadding = 3

		self.top = tkinter.Toplevel(app)
		self.top.grab_set()
		self.top.bind('<Button-1>', self.tk_ignore)

		self.top.title('Preferences')
		self.top.geometry('900x500') # w x h

		self.top.grid_rowconfigure(0, weight=1) # main
		self.top.grid_rowconfigure(1, weight=1) # ok

		myFrame = ttk.Frame(self.top, borderwidth=5,relief="groove")
		myFrame.grid(row=0, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		myFrame.grid_columnconfigure(0, weight=1)
		myFrame.grid_columnconfigure(1, weight=1)

		from_ = 0
		to = 2**32-1

		for idx, key in enumerate(self.configDict['detection'].keys()):
			myText = self.getDetectionParam(key)
			myInt = int(myText)

			myLabel = ttk.Label(myFrame, text=key)
			myLabel.grid(row=idx, column=0, sticky="w", padx=myPadding, pady=myPadding)

			# spinbox only responds to clicking up/down arrow, does not respond to values directly entered
			# this lambda is complex but handles both up/down arrows AND bind of <Return> key
			mySpinbox = ttk.Spinbox(myFrame, from_=from_, to=to)
			cmd = lambda event=None, spinboxWidget=mySpinbox, option=key: self.tk_spinbox_Callback(event, spinboxWidget, option)
			mySpinbox['command'] = cmd
			mySpinbox.bind('<Return>', cmd)
			mySpinbox.bind('<FocusOut>', cmd)

			mySpinbox.set(myInt)
			mySpinbox.selection_range(0, "end")
			mySpinbox.icursor("end")

			mySpinbox.grid(row=idx, column=1, sticky="w", padx=myPadding, pady=myPadding)

			myLabel2 = ttk.Label(myFrame, text=self.getDetectionDescription(key))
			myLabel2.grid(row=idx, column=2, sticky="w", padx=myPadding, pady=myPadding)

		# ok
		buttonPadding = 10
		myFrameOK = ttk.Frame(self.top) #, borderwidth=5,relief="groove")
		myFrameOK.grid(row=2, column=0, sticky="e", padx=buttonPadding, pady=buttonPadding)
		myFrameOK.grid_columnconfigure(0, weight=1)
		myFrameOK.grid_columnconfigure(1, weight=1)

		cancelButton = ttk.Button(myFrameOK, text="Cancel", command=self.tk_cancelButton_Callback)
		cancelButton.grid(row=0, column=1)

		okButton = ttk.Button(myFrameOK, text="Save Preferences", command=self.tk_okButton_Callback)
		okButton.grid(row=0, column=2)
	'''

	# abb removed 20201109, not using this, write a PyQt preferences panel
	'''
	def tk_spinbox_Callback(self, event=None, xxx=None, yyy=None):
		print('spinbox_Callback() event:', event, 'xxx:', xxx, 'yyy:', yyy)
		print('new value is:', xxx.get())
		newValue = xxx.get() # str
		# not sure if everything is int() ???
		newValue = int(newValue)
		self.setDetectionParam(yyy, newValue)

	def tk_cancelButton_Callback(self):
		self.top.destroy() # destroy *this, the modal

	def tk_okButton_Callback(self):
		self.configSave()
		self.top.destroy() # destroy *this, the modal

	def tk_ignore(self, event):
		#print('_ignore event:', event)
		return 'break'
	'''

if __name__ == '__main__':

	if 0:
		# unit tests
		bau = bAnalysisUtil()
		print('dvdtThreshold:', bau.getDetectionParam('dvdtThreshold'))
		print('minSpikeVm:', bau.getDetectionParam('minSpikeVm'))
		print('medianFilter:', bau.getDetectionParam('medianFilter'))
		bau.configSave()

		bau.prettyPrint()

	_print()

	# abb removed 20201109, not using this, write a PyQt preferences panel
	'''
	myRoot = tkinter.Tk()
	bau.tk_PreferenesPanel(myRoot)
	myRoot.mainloop()
	'''
