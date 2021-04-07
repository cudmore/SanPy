# Author: Robert Cudmore
# Date: 20190627

import sys, os, json

from collections import OrderedDict

# abb removed 20201109, not using this, write a PyQt preferences panel
'''
import tkinter
from tkinter import ttk
'''

'''
import logging
logging.debug('This is a debug message')
logging.info('This is an info message')
'''

# todo: move these to a json file !!!
# A list of human readable stats and how to map them to backend
# Each key, like 'Take Off Potential (mV)' is a y-stat
statList = OrderedDict()
'''
statList['Inter-Spike-Interval (ms)'] = {
	'yStat': 'isi_ms',
	'yStatUnits': 'ms',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}
'''
statList['Spike Frequency (Hz)'] = {
	'yStat': 'spikeFreq_hz',
	'yStatUnits': 'Hz',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}
statList['Cycle Length (ms)'] = {
	'yStat': 'cycleLength_ms',
	'yStatUnits': 'ms',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}
statList['Take Off Potential (mV)'] = {
	'yStat': 'thresholdVal',
	'yStatUnits': 'mV',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}
statList['AP Peak (mV)'] = {
	'yStat': 'peakVal',
	'yStatUnits': 'mV',
	'xStat': 'peakPnt',
	'xStatUnits': 'Points'
	}
#spikeDict['peakVal'] - spikeDict['thresholdVal']
statList['AP Height (mV)'] = {
	'yStat': 'peakHeight',
	'yStatUnits': 'mV',
	'xStat': 'peakPnt',
	'xStatUnits': 'Points'
	}
statList['Pre AP Min (mV)'] = {
	'yStat': 'preMinVal',
	'yStatUnits': 'mV',
	'xStat': 'preMinPnt',
	'xStatUnits': 'Points'
	}
statList['Post AP Min (mV)'] = {
	'yStat': 'postMinVal',
	'yStatUnits': 'mV',
	'xStat': 'postMinPnt',
	'xStatUnits': 'Points'
	}
# todo: fix this
statList['Early Diastolic Depol Rate (dV/s)'] = {
	'yStat': 'earlyDiastolicDurationRate',
	'yStatUnits': 'dV/s',
	'xStat': '',
	'xStatUnits': ''
	}
# todo: fix this
statList['Early Diastolic Duration (ms)'] = {
	'yStat': 'earlyDiastolicDuration_ms',
	'yStatUnits': 'dV/s',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}

statList['Diastolic Duration (ms)'] = {
	'yStat': 'diastolicDuration_ms',
	'yStatUnits': 'dV/s',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}
statList['Max AP Upstroke (mV)'] = {
	'yStat': 'preSpike_dvdt_max_val',
	'yStatUnits': 'dV/s',
	'xStat': 'preSpike_dvdt_max_pnt',
	'xStatUnits': 'Points'
	}
statList['Max AP Upstroke (dV/dt)'] = {
	'yStat': 'preSpike_dvdt_max_val2',
	'yStatUnits': 'dV/dt',
	'xStat': 'preSpike_dvdt_max_pnt',
	'xStatUnits': 'Points'
	}
statList['Max AP Repolarization (mV)'] = {
	'yStat': 'postSpike_dvdt_min_val',
	'yStatUnits': 'mV',
	'xStat': 'postSpike_dvdt_min_pnt',
	'xStatUnits': 'Points'
	}
# todo: fix this
statList['AP Duration (ms)'] = {
	'yStat': 'apDuration_ms',
	'yStatUnits': 'ms',
	'xStat': 'thresholdPnt',
	'xStatUnits': 'Points'
	}

# new 20210211
statList['Half Width 20 (ms)'] = {
	'yStat': 'widths_20',
	'yStatUnits': 'ms',
	'xStat': '',
	'xStatUnits': ''
	}
statList['Half Width 50 (ms)'] = {
	'yStat': 'widths_50',
	'yStatUnits': 'ms',
	'xStat': '',
	'xStatUnits': ''
	}
statList['Half Width 80 (ms)'] = {
	'yStat': 'widths_80',
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

		self.top = None # used by tkinter interface

	@staticmethod
	def getStatList():
		return statList

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
	# unit tests
	bau = bAnalysisUtil()
	print('dvdtThreshold:', bau.getDetectionParam('dvdtThreshold'))
	print('minSpikeVm:', bau.getDetectionParam('minSpikeVm'))
	print('medianFilter:', bau.getDetectionParam('medianFilter'))
	bau.configSave()

	bau.prettyPrint()

	# abb removed 20201109, not using this, write a PyQt preferences panel
	'''
	myRoot = tkinter.Tk()
	bau.tk_PreferenesPanel(myRoot)
	myRoot.mainloop()
	'''
