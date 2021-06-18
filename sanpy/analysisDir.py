# Acknowledgements:
# Author: Robert H Cudmore
# Date: 20210603

import os
import numpy as np
import pandas as pd
import requests, io # too load from the web

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
		'isEditable': False,
	},
	'Include': {
		#'type': bool,
		'type': float,
		'isEditable': True,
	},
	'File': {
		'type': str,
		'isEditable': False,
	},
	'Dur(s)': {
		'type': float,
		'isEditable': False,
	},
	'kHz': {
		'type': float,
		'isEditable': False,
	},
	'Mode': {
		'type': str,
		'isEditable': False,
	},
	'Cell Type': {
		'type': str,
		'isEditable': True,
	},
	'Sex': {
		'type': str,
		'isEditable': True,
	},
	'Condition': {
		'type': str,
		'isEditable': True,
	},
	'Start(s)': {
		'type': float,
		'isEditable': True,
	},
	'Stop(s)': {
		'type': float,
		'isEditable': True,
	},
	'dvdtThreshold': {
		'type': float,
		'isEditable': True,
	},
	'mvThreshold': {
		'type': float,
		'isEditable': True,
	},
	'refractory_ms': {
		'type': float,
		'isEditable': True,
	},
	'peakWindow_ms': {
		'type': float,
		'isEditable': True,
	},
	'halfWidthWindow_ms': {
		'type': float,
		'isEditable': True,
	},
	'Notes': {
		'type': str,
		'isEditable': True,
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

def findNewFiles(path):
	fileList = getFileList(path)
	# (1) for each file, see if it is in df

	# (2) for each file in df, see if it is in dir

class bAnalysisDirWeb():
	"""
	Load a directory of .abf from the web (for now from GitHub).
	Will etend this to Box, Dropbox, other?.
	"""
	def __init__(self, cloudDict):
		"""
		cloudDict (dict): {
					'owner': 'cudmore',
					'repo_name': 'SanPy',
					'path': 'data'
					}
		"""
		self._cloudDict = cloudDict
		self.loadFolder()

	def loadFolder(self):
		"""
		Load using cloudDict
		"""

		"""
		# use ['download_url'] to download abf file (no byte conversion)
		response[0] = {
			name : 171116sh_0018.abf
			path : data/171116sh_0018.abf
			sha : 5f3322b08d86458bf7ac8b5c12564933142ffd17
			size : 2047488
			url : https://api.github.com/repos/cudmore/SanPy/contents/data/171116sh_0018.abf?ref=master
			html_url : https://github.com/cudmore/SanPy/blob/master/data/171116sh_0018.abf
			git_url : https://api.github.com/repos/cudmore/SanPy/git/blobs/5f3322b08d86458bf7ac8b5c12564933142ffd17
			download_url : https://raw.githubusercontent.com/cudmore/SanPy/master/data/171116sh_0018.abf
			type : file
			_links : {'self': 'https://api.github.com/repos/cudmore/SanPy/contents/data/171116sh_0018.abf?ref=master', 'git': 'https://api.github.com/repos/cudmore/SanPy/git/blobs/5f3322b08d86458bf7ac8b5c12564933142ffd17', 'html': 'https://github.com/cudmore/SanPy/blob/master/data/171116sh_0018.abf'}
		}
		"""

		owner = self._cloudDict['owner']
		repo_name = self._cloudDict['repo_name']
		path = self._cloudDict['path']
		url = f'https://api.github.com/repos/{owner}/{repo_name}/contents/{path}'

		# response is a list of dict
		response = requests.get(url).json()
		#print('response:', type(response))

		for idx, item in enumerate(response):
			if not item['name'].endswith('.abf'):
				continue
			print(idx)
			# use item['git_url']
			for k,v in item.items():
				print('  ', k, ':', v)

		#
		# test load
		download_url = response[1]['download_url']
		content = requests.get(download_url).content

		fileLikeObject = io.BytesIO(content)
		ba = sanpy.bAnalysis(byteStream=fileLikeObject)
		#print(ba._abf)
		#print(ba.api_getHeader())
		ba.spikeDetect()
		print(ba.numSpikes)

class bAnalysisDir():
	"""
	Class to manage a list of files loaded from a folder
	"""
	def __init__(self, path=None, myApp=None, autoLoad=True):
		"""
		Initialize with a path to folder

		TODO: extend to link to folder in cloud (start with box)

		Args:
			path (str): Path to folder
			myApp (sanpy_app): Optional
			autoLoad (boolean):
			cloudDict (dict): To load frmo cloud, for now  just github
		"""
		self.path = path
		self.myApp = myApp # used to signal on building initial db
		self.autoLoad = autoLoad
		#self.cloudDict = cloudDict
		self.fileList = [] # list of dict
		self.df = None
		if autoLoad:
			self.df = self.loadFolder()

	def numFiles(self):
		"""Get the number of files"""
		return len(self.fileList)

	def loadFolder(self, path=None):
		"""
		expensive

		TODO: extand the logic to load from cloud (after we were instantiated)
		"""
		if path is None:
			path = self.path
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

def testCloud():
	cloudDict = {
		'owner': 'cudmore',
		'repo_name': 'SanPy',
		'path': 'data'
	}
	bad = bAnalysisDirWeb(cloudDict)

if __name__ == '__main__':
	#test()
	#test2()
	testCloud()
