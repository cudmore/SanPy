# Acknowledgements:
# Author: Robert H Cudmore
# Date: 20210603

import os
import numpy as np

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class bAnalysisDir():
	"""
	Class to manage a list of files loaded from a folder
	"""
	def __init__(self, path, autoLoad=True):
		"""
		Initialize with a path to folder

		TODO: extend to link to folder in cloud (start with box)

		Args:
			path (str): Path to folder
		"""
		self.path = path
		self.fileList = [] # list of dict
		if autoLoad:
			self.loadFolder(self.path)

	def numFiles(self):
		"""Get the number of files"""
		return len(self.fileList)

	def loadFolder(self, path):
		"""
		Load all files in folder

		TODO: Curently limited to abf, extend to (txt, csv, tif)
		"""
		if not os.path.isdir(path):
			logger.error(f'Path not found: "{path}"')
			return

		self.path = path

		fileList = []
		fileIdx = 0
		for file in os.listdir(path):
			if file.startswith('.'):
				continue
			if file.endswith('.abf'):
				# load
				filePath = os.path.join(path, file)
				ba = sanpy.bAnalysis(filePath)

				# header
				headerDict = ba.api_getHeader()
				headerDict['index'] = fileIdx

				item = {
					'header': headerDict,
					'ba': ba,
					'sweepX': ba.abf.sweepX,
					'sweepY': ba.abf.sweepY,
				}
				fileList.append(item)
				fileIdx += 1
		#
		self.fileList = fileList

	def getHeaderList(self):
		"""
		Get list of header dict for folder
		"""
		theRet = []
		for file in self.fileList:
			item = file['header']
			theRet.append(item)
		return theRet

	def getFromIndex(self, index, type='header'):
		"""
		Get one file from index

		Args:
			index (int): Index into list of files
			type (str): type of data to return.
				('header', 'ba', 'sweepX', 'sweepY')
		"""
		theRet = self.fileList[index][type]
		return theRet

def _printDict(d):
	for k,v in d.items():
		print('  ', k, ':', v)

def test():
	path = '/Users/cudmore/Sites/SanPy/data'
	bad = bAnalysisDir(path)

	# get list of dict, useful for inserting into table (pyqt, dash, vue)
	if 0:
		dirDictList = bad.getHeaderList()
		for idx, itemDict in enumerate(dirDictList):
			print('idx:', idx)
			_printDict(itemDict)

	# get one file
	index = 1
	headerDict = bad.getFromIndex(index, type='header')
	_printDict(headerDict)

	sweepX = bad.getFromIndex(index, type='sweepX')
	print('  sweepX:', type(sweepX), len(sweepX), np.nanmean(sweepX))
	sweepY = bad.getFromIndex(index, type='sweepY')
	print('  sweepY:', type(sweepY), len(sweepY), np.nanmean(sweepY))

	ba = bad.getFromIndex(index, type='ba')
	tmpDict = ba.api_getRecording()
	print(tmpDict.keys())

if __name__ == '__main__':
	test()
