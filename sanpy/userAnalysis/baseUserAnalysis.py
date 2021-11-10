"""
Implement a base class so users can add additional analysis.

Author: Robert Cudmore

Date: 20210929
"""
import inspect
import numpy as np

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def getObjectList():
	"""
	Return a list of classes defined in sanpy.userAnalysis.

	Each of these is an object and we can construct or interrogate statis class members
	"""

	#logger.info('')

	ignoreModuleList = ['baseUserAnalysis']

	objList = []
	#userStatDict = {}
	for moduleName, obj in inspect.getmembers(sanpy.userAnalysis):
		#print('moduleName:', moduleName, 'obj:', obj)
		if inspect.isclass(obj):
			if moduleName in ignoreModuleList:
				continue
			print(f'  is class moduleName {moduleName} obj:{obj}')
			# obj is a constructor function
			# <class 'sanpy.userAnalysis.userAnalysis.exampleUserAnalysis'>
			print('  ', obj.userStatDict)

			# from findUserAnalysis
			'''
			oneStatDict = obj.userStatDict
			for k,v in oneStatDict.items():
				userStatDict[k] = {}
				userStatDict[k]['name'] = v['name']
			'''
			objList.append(obj)  # obj is a class constructor

	#
	return objList

def findUserAnalysis():
	"""
	Find files in 'sanpy/userAnalysis' and populate a dict with stat names
	this will be appended to bAnalysisUtil.statList
	"""

	logger.info('')

	ignoreModuleList = ['baseUserAnalysis']

	userStatDict = {}
	for moduleName, obj in inspect.getmembers(sanpy.userAnalysis):
		#print('moduleName:', moduleName, 'obj:', obj)
		if inspect.isclass(obj):
			if moduleName in ignoreModuleList:
				continue
			print(f' is class moduleName {moduleName} obj:{obj}')
			# obj is a constructor function
			# <class 'sanpy.userAnalysis.userAnalysis.exampleUserAnalysis'>
			print('  ', obj.userStatDict)
			oneStatDict = obj.userStatDict
			for k,v in oneStatDict.items():
				userStatDict[k] = {}
				userStatDict[k]['name'] = v['name']

	#
	return userStatDict

def runAllUserAnalysis(ba):
	"""
	call at end of bAnalysis
	"""

	# step through each
	objList = getObjectList()
	for obj in objList:
		# instantiate and call run (will add values for stats
		userObj = obj(ba)
		userObj.run()

class baseUserAnalysis:
	"""
	Create a userAnalysis object after bAnalysis has been analyzed with the core analysis results.
	"""
	userStatDict = {}
	"""User needs to fill this in see xxx for example"""

	def __init__(self, ba):
		self._myAnalysis = ba

		self._installStats()

	def _installStats(self):
		logger.info(f'Installing "{self.userStatDict}"')
		for k, v in self.userStatDict.items():
			logger.info(f'{k}: {v}')
			name = v['name']
			self.addKey(name, theDefault=None)

	@property
	def ba(self):
		"""Get the underlying sanpy.bAnalysis object"""
		return self._myAnalysis

	def getSweepX(self):
		"""Get the x-axis of a recording."""
		return self.ba.sweepX

	def getSweepY(self):
		"""Get the y-axis of a recording."""
		return self.ba.sweepY

	def getSweepC(self):
		"""Get the DAC axis of a recording."""
		return self.ba.sweepC

	def getFilteredVm(self):
		return self.ba.filteredVm

	def addKey(self, theKey, theDefault=None):
		"""Add a new key to analysis results.

		Will add key to each spike in self.ba.spikeDict
		"""
		self.ba.spikeDict.addAnalysisResult(theKey, theDefault)

	def setSpikeValue(self, spikeIdx, theKey, theVal):
		"""
		Set the value of a spike key.

		Args:
			spikeIdx (int): The spike index , 0 based.
			theKey (str): Name of the key.
			theVal (): The value for the key, can be almost any type like
						(float, int, bool, dict, list)

		Raises:
			KeyError: xxx.
			IndexError: xxx.
		"""
		self.ba.spikeDict[spikeIdx][theKey] = theVal

	def getSpikeValue(self, spikeIdx, theKey):
		"""
		Get a single spike analysis result from key.

		Args:
			spikeIdx (int): The spike index, 0 based
			theKey (str): xxx

		Raises:
			KeyError: If theKey is not a key in analysis results.
			IndexError: If spikeIdx is beyond number of spikes -1.
		"""
		try:
			theRet = self.ba.spikeDict[spikeIdx][theKey]
			return theRet
		except (KeyError) as e:
			print(e)
		except (IndexError) as e:
			print(e)

	def run(self):
		"""
		Run user analysis. Add a key to analysis results and fill in its values.

		Try not to re-use existing keys
		"""


def test1():
	findUserAnalysis()

if __name__ == '__main__':
	test1()
