# Acknowledgements:
# Author: Robert H Cudmore
# Date: 20210603

import os
import numpy as np
import pandas as pd

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

"""
Columns to use in display in file table (pyqt, dash, vue).
We require type so we can edit with QAbstractTableModel.
Critical for qt interface to allow easy editing of values while preserving type
"""
sanpyColumns = {
	'Idx': {
		#'type': int,
		'type': float,
	},
	'Include': {
		#'type': bool,
		'type': float,
	},
	'File': {
		'type': str,
	},
	'Dur(s)': {
		'type': float,
	},
	'kHz': {
		'type': float,
	},
	'Mode': {
		'type': str,
	},
	'Cell Type': {
		'type': str,
	},
	'Sex': {
		'type': str,
	},
	'Condition': {
		'type': str,
	},
	'Start(s)': {
		'type': float,
	},
	'Stop(s)': {
		'type': float,
	},
	'dvdtThreshold': {
		'type': float,
	},
	'mvThreshold': {
		'type': float,
	},
	'refractory_ms': {
		'type': float,
	},
	'peakWindow_ms': {
		'type': float,
	},
	'halfWidthWindow_ms': {
		'type': float,
	},
	'Notes': {
		'type': str,
	},

}

# file types we will load
theseFileTypes = ['.abf', '.csv', '.tif']

def getFileRow(path, rowIdx=None):
	"""
	Get dict representing one file (row in table).

	Args:
		path (Str): Full path to file.
		rowIdx (int): Optional row index to assign in column 'Idx'

	Return:
		dict: On success, otherwise None
				fails when path does not lead to valid bAnalysis file.
	"""
	if not os.path.isfile(path):
		logger.error(path)
		return None
	if not os.path.splitext(path)[1] in theseFileTypes:
		return None

	ba = sanpy.bAnalysis(path)

	if ba.loadError:
		logger.error(path)
		return None

	# not sufficient to default everything to empty str ''
	# sanpyColumns can only have type in ('float', 'str')
	rowDict = dict.fromkeys(sanpyColumns.keys() , '')
	for k in rowDict.keys():
		if sanpyColumns[k]['type'] == str:
			rowDict[k] = ''
		elif sanpyColumns[k]['type'] == float:
			rowDict[k] = np.nan

	if rowIdx is not None:
		rowDict['Idx'] = rowIdx

	rowDict['Include'] = 1 # causes error if not here !!!!, can't be string
	rowDict['File'] = os.path.split(ba.path)[1]
	rowDict['Dur(s)'] = ba.recodingDur
	rowDict['kHz'] = ba.recordingFrequency
	rowDict['Mode'] = 'fix'

	rowDict['dvdtThreshold'] = 20
	rowDict['mvThreshold'] = -20

	return rowDict

def getFileList(path):
	fileList = []
	for file in os.listdir(path):
		if file.startswith('.'):
			continue
		#if file == 'sanpy_recording_db.csv':
		#	continue

		# tmpExt is like .abf, .csv, etc
		tmpFileName, tmpExt = os.path.splitext(file)
		if tmpExt in theseFileTypes:
			file = os.path.join(path, file)
			fileList.append(file)
	#
	return fileList

class bAnalysisDir():
	"""
	Class to manage a list of files loaded from a folder
	"""
	def __init__(self, path, myApp=None, autoLoad=True):
		"""
		Initialize with a path to folder

		TODO: extend to link to folder in cloud (start with box)

		Args:
			path (str): Path to folder
			myApp (sanpy_app): Optional
		"""
		self.path = path
		self.myApp = myApp # used to signal on building initial db
		self.fileList = [] # list of dict
		self.df = None
		if autoLoad:
			self.df = self.loadFolder(self.path)

	def numFiles(self):
		"""Get the number of files"""
		return len(self.fileList)

	def loadFolder(self, path):
		"""
		expensive
		"""
		self.path = path

		# load an existing folder db or create a new one
		dbFile = 'sanpy_recording_db.csv'
		dbPath = os.path.join(path, dbFile)
		loadedDatabase = False
		if os.path.isfile(dbPath):
			logger.info(f'Loading existing folder db: {dbPath}')
			df = pd.read_csv(dbPath, header=0, index_col=False)

			#df["Idx"] = pd.to_numeric(df["Idx"])
			df = self._setColumnType(df)
			'''
			for col in df.columns:
				colType = sanpyColumns[col]['type']
				if  colType == str:
					df[col] = df[col].replace(np.nan, '', regex=True)
					df[col] = df[col].astype(str)
				elif colType == int:
					df[col] = df[col].astype(int)
				elif colType == float:
					df[col] = df[col].astype(float)
				elif colType == bool:
					df[col] = df[col].astype(bool)
			'''

			'''
			print('=== final types')
			print(df.dtypes)
			'''
			loadedDatabase = True
		else:
			logger.info(f'No existing folder db {dbPath}')
			logger.info(f'Making default folder db')
			df = pd.DataFrame(columns=sanpyColumns.keys())
			df = self._setColumnType(df)

		if loadedDatabase:
			# check columns with sanpyColumns
			loadedColumns = df.columns
			for col in loadedColumns:
				if not col in sanpyColumns.keys():
					print(f'  error: bAnalysisDir did not find loaded col: "{col}" in sanpyColumns.keys()')
			for col in sanpyColumns.keys():
				if not col in loadedColumns:
					print(f'  error: bAnalysisDir did not find sanpyColumns.keys() col: "{col}" in loadedColumns')

		# get list of all abf/csv/tif
		fileList = getFileList(path)

		if loadedDatabase:
			# seach existing db for missing abf files
			pass
		else:
			# build new db dataframe
			listOfDict = []
			for rowIdx, file in enumerate(fileList):
				self.signalApp(f'Please wait, loading "{file}"')
				rowDict = getFileRow(file, rowIdx=rowIdx+1)
				if rowDict is not None:
					listOfDict.append(rowDict)
			#
			df = pd.DataFrame(listOfDict)
			#print('=== built new db df:')
			#print(df)
			df = self._setColumnType(df)
		#
		return df

	def _setColumnType(self, df):
		"""
		Needs to be called every time a df is created.
		Ensures proper type of columns following sanpyColumns[key]['type']
		"""
		#print('columns are:', df.columns)
		for col in df.columns:
			colType = sanpyColumns[col]['type']
			#print(f'  _setColumnType() for "{col}" is type "{colType}"')
			#print(f'    df[col]:', 'len:', len(df[col]))
			#print(df[col])
			if colType == str:
				df[col] = df[col].replace(np.nan, '', regex=True)
				df[col] = df[col].astype(str)
			elif colType == int:
				df[col] = df[col].astype(int)
			elif colType == float:
				# error if ''
				df[col] = df[col].astype(float)
			elif colType == bool:
				df[col] = df[col].astype(bool)
		#
		return df
	def old_loadFolder(self, path):
		"""
		Load all files in folder

		TODO: Curently limited to abf, extend to (txt, csv, tif)
		"""
		if not os.path.isdir(path):
			logger.error(f'Path not found: "{path}"')
			return

		#
		#
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

	def signalApp(self, str):
		if self.myApp is not None:
			self.myApp.updateStatusBar(str)

def _printDict(d):
	for k,v in d.items():
		print('  ', k, ':', v)

def test2():
	path = '/Users/cudmore/Sites/SanPy/data'
	bad = bAnalysisDir(path)
	df = bad.loadFolder(path)
	print(df)

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
	print('=== headerDict')
	_printDict(headerDict)

	sweepX = bad.getFromIndex(index, type='sweepX')
	print('  sweepX:', type(sweepX), len(sweepX), np.nanmean(sweepX))
	sweepY = bad.getFromIndex(index, type='sweepY')
	print('  sweepY:', type(sweepY), len(sweepY), np.nanmean(sweepY))

	print('== 3')
	ba = bad.getFromIndex(index, type='ba')
	tmpDict = ba.api_getRecording()
	print(tmpDict.keys())

if __name__ == '__main__':
	#test()
	test2()
