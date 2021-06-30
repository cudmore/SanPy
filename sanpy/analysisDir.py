# Acknowledgements:
# Author: Robert H Cudmore
# Date: 20210603

import os
import numpy as np
import pandas as pd
import requests, io  # too load from the web

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)


_sanpyColumns = {
	#'Idx': {
	#	#'type': int,
	#	'type': float,
	#	'isEditable': False,
	#},
	'File': {
		'type': str,
		'isEditable': False,
	},
	'Include': {
		#'type': bool,
		'type': float,
		'isEditable': True,
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
"""
Columns to use in display in file table (pyqt, dash, vue).
We require type so we can edit with QAbstractTableModel.
Critical for qt interface to allow easy editing of values while preserving type
"""

class bAnalysisDirWeb():
	"""
	Load a directory of .abf from the web (for now from GitHub).

	Will etend this to Box, Dropbox, other?.
	"""

	def __init__(self, cloudDict):
		"""
		Args: cloudDict (dict): {
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

class analysisDir():
	"""
	Class to manage a list of files loaded from a folder
	"""
	sanpyColumns = _sanpyColumns

	theseFileTypes = ['.abf', '.csv']
	"""File types to load"""

	def __init__(self, path=None, myApp=None, autoLoad=True):
		"""
		Load and manage a list of files in a folder path.
		Use this as the main pandasModel for file list myTableView.

		TODO: extend to link to folder in cloud (start with box and/or github)

		Args:
			path (str): Path to folder
			myApp (sanpy_app): Optional
			autoLoad (boolean):
			cloudDict (dict): To load frmo cloud, for now  just github

		Notes:
			- on load existing .csv
				- match columns in file with 'sanpyColumns'
				- check that each file in csv exists in the path
				- check if there are files in the path NOT in the csv

			- Some functions are so self can mimic a pandas dataframe used by pandasModel.
				(shape, loc, loc_setter, iloc, iLoc_setter, columns, append, drop, sort_values, copy)
		"""
		self.path = path
		self.myApp = myApp # used to signal on building initial db
		self.autoLoad = autoLoad

		self._isDirty = False

		# keys are full path to file, if from cloud, key is 'cloud/<filename>'
		# holds bAnalysisObjects
		# needs to be a list so we can have files more than one
		#self.fileList = [] #OrderedDict()

		# name of database file created/loaded from folder path
		self.dbFile = 'sanpy_recording_db.csv'

		self._df = None
		if autoLoad:
			self._df = self.loadFolder()

	@property
	def isDirty(self):
		return self._isDirty

	def __len__(self):
		return len(self._df)

	@property
	def shape(self):
		"""
		Can't just return shape of _df, columns (like 'ba') may have been added
		Number of columns is based on self.columns
		"""
		#return self._df.shape
		numRows = self._df.shape[0]
		numCols = len(self.columns)
		return (numRows, numCols)

	@property
	def loc(self):
		"""Mimic pandas df.loc[]"""
		return self._df.loc

	@loc.setter
	def loc_setter(self, rowIdx, colStr, value):
		self._df.loc[rowIdx,colStr] = value

	@property
	def iloc(self):
		# mimic pandas df.iloc[]
		return self._df.iloc

	@iloc.setter
	def iLoc_setter(self, rowIdx, colIdx, value):
		self._df.iloc[rowIdx,colIdx] = value
		self._isDirty = True

	@property
	def columns(self):
		# return list of column names
		return list(self.sanpyColumns.keys())

	def copy(self):
		return self._df.copy()

	def sort_values(self, Ncol, order):
		self._df = self._df.sort_values(self.columns[Ncol], ascending=not order)

	@property
	def columnsDict(self):
		return self.sanpyColumns

	def columnIsEditable(self, colName):
		return self.sanpyColumns[colName]['isEditable']

	def getDataFrame(self):
		"""Get the underlying pandas DataFrame."""
		return self._df

	def numFiles(self):
		"""Get the number of files"""
		return len(self._df)

	def copyToClipboard(self):
		if self.getDataFrame() is not None:
			self.getDataFrame().to_clipboard(sep='\t', index=False)
			logger.info('Copied to clipboard')

	def saveDatabase(self):
		""" save dbFile .csv"""
		dbPath = os.path.join(self.path, self.dbFile)
		if self.getDataFrame() is not None:
			logger.info(f'Saving "{dbPath}"')
			self.getDataFrame().to_csv(dbPath, index=False)
			self._isDirty = False

	def loadFolder(self, path=None):
		"""
		expensive

		TODO: extend the logic to load from cloud (after we were instantiated)
		"""
		if path is None:
			path = self.path
		self.path = path

		# load an existing folder db or create a new one
		dbPath = os.path.join(path, self.dbFile)
		loadedDatabase = False
		if os.path.isfile(dbPath):
			logger.info(f'Loading existing folder db: {dbPath}')
			df = pd.read_csv(dbPath, header=0, index_col=False)
			#df["Idx"] = pd.to_numeric(df["Idx"])
			df = self._setColumnType(df)
			loadedDatabase = True
			#logger.info(f'  shape is {df.shape}')
		else:
			logger.info(f'No existing db file, making {dbPath}')
			df = pd.DataFrame(columns=self.sanpyColumns.keys())
			df = self._setColumnType(df)

		if loadedDatabase:
			# check columns with sanpyColumns
			loadedColumns = df.columns
			for col in loadedColumns:
				if not col in self.sanpyColumns.keys():
					logger.error(f'error: bAnalysisDir did not find loaded col: "{col}" in sanpyColumns.keys()')
			for col in self.sanpyColumns.keys():
				if not col in loadedColumns:
					logger.error(f'error: bAnalysisDir did not find sanpyColumns.keys() col: "{col}" in loadedColumns')

		if loadedDatabase:
			# seach existing db for missing abf files
			pass
		else:
			# get list of all abf/csv/tif
			fileList = self.getFileList(path)
			# build new db dataframe
			listOfDict = []
			for rowIdx, file in enumerate(fileList):
				self.signalApp(f'Please wait, loading "{file}"')
				ba, rowDict = self.getFileRow(file, rowIdx=rowIdx+1) # loads bAnalysis
				if rowDict is not None:
					listOfDict.append(rowDict)
					#self.fileList[file] = ba
			#
			df = pd.DataFrame(listOfDict)
			#print('=== built new db df:')
			#print(df)
			df = self._setColumnType(df)
		#

		# expand each to into self.fileList
		df['_ba'] = None
		'''
		for rowIdx in range(len(df)):
			file= df.at[rowIdx, 'File']
			filePath = os.path.join(path, file)
			#print(f'{rowIdx} {filePath}')
			newDict = {
						'ba': None,
						'file': file,
						'filePath': filePath
						}
			self.fileList.append(newDict)
		'''
		#
		logger.info('df:')
		print(df)

		return df

	def getAnalysis(self, rowIdx):
		"""
		Get bAnalysis object, will load if necc

		Args:
			rowIdx (int): Row index from table, corresponds to row in self._df
		"""
		file = self._df.loc[rowIdx, 'File']
		filePath = os.path.join(self.path, file)
		ba = self._df.loc[rowIdx, '_ba']
		if ba is None:
			# load
			logger.info(f'Loading bAnalysis from row {rowIdx} "{filePath}"')
			ba = sanpy.bAnalysis(filePath)
			#self.fileList[filePath]['ba'] = ba
			self._df.loc[rowIdx, '_ba'] = ba
		#
		return ba

	def _setColumnType(self, df):
		"""
		Needs to be called every time a df is created.
		Ensures proper type of columns following sanpyColumns[key]['type']
		"""
		#print('columns are:', df.columns)
		for col in df.columns:
			# when loading from csv, 'col' may not be in sanpyColumns
			if not col in self.sanpyColumns:
				logger.warning(f'Column "{col}" is not in sanpyColumns -->> ignoring')
				continue
			colType = self.sanpyColumns[col]['type']
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

	def getFileRow(self, path, rowIdx=None):
		"""
		Get dict representing one file (row in table). Loads bAnalysis to get headers.

		Args:
			path (Str): Full path to file.
			rowIdx (int): Optional row index to assign in column 'Idx'

		Return:
			bAnalysis:
			dict: On success, otherwise None
					fails when path does not lead to valid bAnalysis file.
		"""
		if not os.path.isfile(path):
			logger.warning(f'Did not find file "{path}"')
			return None, None
		fileType = os.path.splitext(path)[1]
		if fileType not in self.theseFileTypes:
			logger.warning(f'Did not load file type "{fileType}"')
			return None, None

		# load bAnalysis
		logger.info(f'Loading bAnalysis "{path}"')
		ba = sanpy.bAnalysis(path)

		if ba.loadError:
			logger.error(f'Error loading bAnalysis file "{path}"')
			return None, None

		# not sufficient to default everything to empty str ''
		# sanpyColumns can only have type in ('float', 'str')
		rowDict = dict.fromkeys(self.sanpyColumns.keys() , '')
		for k in rowDict.keys():
			if self.sanpyColumns[k]['type'] == str:
				rowDict[k] = ''
			elif self.sanpyColumns[k]['type'] == float:
				rowDict[k] = np.nan

		if rowIdx is not None:
			rowDict['Idx'] = rowIdx

		rowDict['Include'] = 1 # causes error if not here !!!!, can't be string
		rowDict['File'] = ba.getFileName() #os.path.split(ba.path)[1]
		rowDict['Dur(s)'] = ba.recodingDur
		rowDict['kHz'] = ba.recordingFrequency
		rowDict['Mode'] = 'fix'

		rowDict['dvdtThreshold'] = 20
		rowDict['mvThreshold'] = -20

		return ba, rowDict

	def getFileList(self, path=None, getFullPath=True):
		"""
		Get file paths from path
		"""
		if path is None:
			path = self.path
		fileList = []
		for file in os.listdir(path):
			if file.startswith('.'):
				continue
			# ignore our database file
			if file == self.dbFile:
				continue

			# tmpExt is like .abf, .csv, etc
			tmpFileName, tmpExt = os.path.splitext(file)
			if tmpExt in self.theseFileTypes:
				if getFullPath:
					file = os.path.join(path, file)
				fileList.append(file)
		#
		return fileList

	def getRowDict(self, rowIdx):
		"""
		Return a dict with selected row as dict (includes detection parameters)
		Use sanpyColumns, not df columns
		"""
		theRet = {}
		# use columns in main sanpyColumns, not in df
		for colStr in self.columns:
			theRet[colStr] = self._df.loc[rowIdx, colStr]
		return theRet

	def appendRow(self, rowDict=None, ba=None):
		# append one empty row
		rowSeries = pd.Series()
		if rowDict is not None:
			rowSeries = pd.Series(rowDict)
			# self._data.iloc[row] = rowSeries
			# self._data = self._data.reset_index(drop=True)

		newRowIdx = len(self._df)
		df = self._df
		df = df.append(rowSeries, ignore_index=True)
		df = df.reset_index(drop=True)

		if ba is not None:
			df.loc[newRowIdx, '_ba'] = ba

		#
		self._df = df

	def deleteRow(self, rowIdx):
		df = self._df
		df = df.drop([rowIdx])
		df = df.reset_index(drop=True)
		self._df = df

	def duplicateRow(self, rowIdx):
		# duplicate rowIdx
		newIdx = rowIdx + 0.5
		rowDict = self.getRowDict(rowIdx)
		dfRow = pd.DataFrame(rowDict, index=[newIdx])

		df = self._df
		df = df.append(dfRow, ignore_index=True)
		df = df.sort_values(by=['File'], axis='index', ascending=True, inplace=False)
		df = df.reset_index(drop=True)
		self._df = df

	def syncDfWithPath(self):
		pathFileList = self.getFileList(getFullPath=False)
		dfFileList = self._df['File'].tolist()

		print('=== pathFileList:')
		print(pathFileList)
		print('=== dfFileList:')
		print(dfFileList)

		addedToDf = False

		# look for files in path not in df
		for pathFile in pathFileList:
			if pathFile not in dfFileList:
				logger.info(f'Found file in path "{pathFile}" not in df')
				# load bAnalysis and get df column values
				addedToDf = True
				fullPathFile = os.path.join(self.path, pathFile)
				ba, rowDict = self.getFileRow(fullPathFile) # loads bAnalysis
				if rowDict is not None:
					#listOfDict.append(rowDict)
					self.appendRow(rowDict=rowDict, ba=ba)

		# look for files in df not in path
		for dfFile in dfFileList:
			if not dfFile in pathFileList:
				logger.info(f'Found file in df "{dfFile}" not in path')

		if addedToDf:
			df = self._df
			df = df.sort_values(by=['File'], axis='index', ascending=True, inplace=False)
			df = df.reset_index(drop=True)
			self._df = df

	def signalApp(self, str):
		"""Update status bar of app"""
		if self.myApp is not None:
			self.myApp.updateStatusBar(str)

def _printDict(d):
	for k,v in d.items():
		print('  ', k, ':', v)

def test3():
	path = '/home/cudmore/Sites/SanPy/data'
	bad = analysisDir(path)

	#file = '19221014.abf'
	rowIdx = 3
	ba = bad.getAnalysis(rowIdx)
	ba = bad.getAnalysis(rowIdx)

	print(bad.getDataFrame())

	print('bad.shape', bad.shape)
	print('bad.columns:', bad.columns)

	print('bad.iloc[rowIdx,5]:', bad.iloc[rowIdx,5])
	print('setting to xxxyyyzzz')

	# setter
	#bad.iloc[2,5] = 'xxxyyyzzz'

	print('bad.iloc[2,5]:', bad.iloc[rowIdx,5])
	print('bad.loc[2,"File"]:', bad.loc[rowIdx,'File'])

	print('bad.iloc[2]')
	print(bad.iloc[rowIdx])
	#bad.iloc[rowIdx] = ''
	print('bad.loc[2]')
	print(bad.loc[rowIdx])

	#bad.saveDatabase()

def testCloud():
	cloudDict = {
		'owner': 'cudmore',
		'repo_name': 'SanPy',
		'path': 'data'
	}
	bad = bAnalysisDirWeb(cloudDict)

if __name__ == '__main__':
	test3()
	#testCloud()
