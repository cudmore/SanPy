# Acknowledgements:
# Author: Robert H Cudmore
# Date: 20210603

import os, time
import copy  # For copy.deepcopy() of bAnalysis
import uuid  # to generate unique key on bAnalysis spike detect
import numpy as np
import pandas as pd
import requests, io  # too load from the web
from subprocess import call # to call ptrepack (might fail on windows???)

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

testTimingNumFiles = None

_sanpyColumns = {
	#'Idx': {
	#	#'type': int,
	#	'type': float,
	#	'isEditable': False,
	#},
	'L': {
		# loaded
		'type': str,
		'isEditable': False,
	},
	'A': {
		# analyzed
		'type': str,
		'isEditable': False,
	},
	'I': {
		# include
		# problems with isinstance(bool), just using string
		'type': 'bool',
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

		self._poolDf = None
		"""See pool_ functions"""

		# keys are full path to file, if from cloud, key is 'cloud/<filename>'
		# holds bAnalysisObjects
		# needs to be a list so we can have files more than one
		#self.fileList = [] #OrderedDict()

		# name of database file created/loaded from folder path
		self.dbFile = 'sanpy_recording_db.csv'

		self._df = None
		if autoLoad:
			self._df = self.loadHdf()
			if self._df is None:
				self._df = self.loadFolder()
		#
		self._checkColumns()
		self._updateLoadedAnalyzed()
		#
		logger.info(self)

	def __str__(self):
		totalDurSec = self._df['Dur(s)'].sum()
		theStr = f'Num Files: {len(self)} Total Dur(s): {totalDurSec}'
		return theStr

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
		self._df.iloc[rowIdx, colIdx] = value
		self._isDirty = True

	@property
	def index(self):
		return self._df.index

	@property
	def columns(self):
		# return list of column names
		return list(self.sanpyColumns.keys())

	def copy(self):
		return self._df.copy()

	def sort_values(self, Ncol, order):
		logger.info(f'sorting by column {self.columns[Ncol]} with order:{order}')
		self._df = self._df.sort_values(self.columns[Ncol], ascending=not order)
		#print(self._df)

	@property
	def columnsDict(self):
		return self.sanpyColumns

	def columnIsEditable(self, colName):
		return self.sanpyColumns[colName]['isEditable']

	def columnIsCheckBox(self, colName):
		"""All bool columns are checkbox

		TODO: problems with using type=bool and isinstance(). Kust using str 'bool'
		"""
		type = self.sanpyColumns[colName]['type']
		#isBool = isinstance(type, bool)
		isBool = type == 'bool'
		#logger.info(f'{colName} {type(type)}, type:{type} {isBool}')
		return isBool

	def getDataFrame(self):
		"""Get the underlying pandas DataFrame."""
		return self._df

	@property
	def numFiles(self):
		"""Get the number of files. same as len()."""
		return len(self._df)

	def copyToClipboard(self):
		"""
		TODO: Is this used or is copy to clipboard in pandas model?
		"""
		if self.getDataFrame() is not None:
			self.getDataFrame().to_clipboard(sep='\t', index=False)
			logger.info('Copied to clipboard')

	def old_saveDatabase(self):
		""" save dbFile .csv and hdf .gzip"""
		dbPath = os.path.join(self.path, self.dbFile)
		if self.getDataFrame() is not None:
			#
			logger.info(f'Saving "{dbPath}"')
			self.getDataFrame().to_csv(dbPath, index=False)
			self._isDirty = False

			#
			'''
			hdfFile = os.path.splitext(self.dbFile)[0] + '.h5'
			hdfPath = os.path.join(self.path, hdfFile)
			logger.info(f'Saving "{hdfPath}"')
			#hdfStore = pd.HDFStore(hdfPath)
			start = time.time()
			complevel = 9
			complib = 'blosc:blosclz'
			with pd.HDFStore(hdfPath, mode='w', complevel=complevel, complib=complib) as hdfStore:
				hdfStore['df'] = self.getDataFrame()  # save it
			stop = time.time()
			logger.info(f'Saving took {round(stop-start,2)} seconds')
			'''

	def saveHdf(self):
		"""
		"""
		start = time.time()

		tmpHdfFile = os.path.splitext(self.dbFile)[0] + '_tmp.h5'
		tmpHdfPath = os.path.join(self.path, tmpHdfFile)
		logger.info(f'Saving Tmp {tmpHdfPath}')

		#
		# save file database
		with pd.HDFStore(tmpHdfPath, mode='a') as hdfStore:
			dbKey = os.path.splitext(self.dbFile)[0]
			logger.info(f'Storing file db into key "{dbKey}"')
			df = self.getDataFrame()
			df = df.drop('_ba', axis=1)  # don't ever save _ba
			hdfStore[dbKey] = df  # save it
			#
			self._isDirty = False  # if true, prompt to save on quit

		# save each bAnalysis
		df = self.getDataFrame()
		for row in range(len(df)):
			# do not call this, it will load
			#ba = self.getAnalysis(row)
			ba = df.at[row, '_ba']
			if ba is not None:
				ba._saveToHdf(tmpHdfPath) # will only save if ba.detectionDirty

		#
		# rebuild the file to remove old changes and reduce size
		hdfFile = os.path.splitext(self.dbFile)[0] + '.h5'
		hdfPath = os.path.join(self.path, hdfFile)
		logger.info(f'Compressing h5 to {hdfPath}')
		#command = ["ptrepack", "-o", "--chunkshape=auto", "--propindexes", '--complevel=9', '--complib=blosc:blosclz', tmpHdfPath, hdfPath]
		command = ["ptrepack", "-o", "--chunkshape=auto", "--propindexes", tmpHdfPath, hdfPath]
		call(command)

		logger.info(f'Removing temporary file {tmpHdfPath}')
		os.remove(tmpHdfPath)

		stop = time.time()
		logger.info(f'Saving took {round(stop-start,2)} seconds')

	def deleteFromHdf(self, uuid):
		"""Delete uuid from h5 file. id corresponds to a bAnalysis detection."""
		if not uuid:
			return
		logger.info(f'TODO: Delete from h5 file uuid:{uuid}')

	def loadHdf(self, path=None):
		if path is None:
			path = self.path
		self.path = path

		df = None
		hdfFile = os.path.splitext(self.dbFile)[0] + '.h5'
		hdfPath = os.path.join(self.path, hdfFile)
		if not os.path.isfile(hdfPath):
			return

		logger.info(f'Loading existing folder hdf: {hdfPath}')
		#hdfStore = pd.HDFStore(hdfPath)
		start = time.time()
		with pd.HDFStore(hdfPath) as hdfStore:
			dbKey = os.path.splitext(self.dbFile)[0]
			df = hdfStore[dbKey]  # load it
			df['_ba'] = None

			# load each bAnalysis from hdf
			for row in range(len(df)):
				ba_uuid = df.at[row, 'uuid']
				if not ba_uuid:
					# ba was not saved in h5 file
					continue
				try:
					dfAnalysis = hdfStore[ba_uuid]
					ba = sanpy.bAnalysis(fromDf=dfAnalysis)
					logger.info(f'Loaded row {row} uuid:{ba.uuid} bAnalysis {ba}')
					df.at[row, '_ba'] = ba # can be none
				except(KeyError):
					logger.info(f'hdf uuid key for row {row} not found in .h5 file, uuid:"{ba_uuid}"')

		stop = time.time()
		logger.info(f'Loading took {round(stop-start,2)} seconds')
		#
		return df

	def loadFolder(self, path=None):
		"""
		Parse a folder and load all (abf, csv, ...). Only called if no h5 file.

		TODO: get rid of loading database from .csv (it is replaced by .h5 file)
		TODO: extend the logic to load from cloud (after we were instantiated)
		"""
		start = time.time()
		if path is None:
			path = self.path
		self.path = path

		loadedDatabase = False

		# load an existing folder db or create a new one
		dbPath = os.path.join(path, self.dbFile)
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
				self.signalApp(f'Loading "{file}"')
				ba, rowDict = self.getFileRow(file)  # loads bAnalysis

				# TODO: calculating time, remove this
				# This is 2x faster than loading frmo pandas gzip ???
				#dDict = ba.getDefaultDetection()
				#dDict['dvdtThreshold'] = 2
				#ba.spikeDetect(dDict)

				rowDict['_ba'] = ba
				# do not assign uuid until bAnalysis is saved in h5 file
				rowDict['uuid'] = ''

				listOfDict.append(rowDict)

				if testTimingNumFiles is not None and rowIdx>testTimingNumFiles-1:
					logger.warning(f'Breaking after testTimingNumFiles:{testTimingNumFiles}')
					break
			#
			df = pd.DataFrame(listOfDict)
			#print('=== built new db df:')
			#print(df)
			df = self._setColumnType(df)
		#

		# expand each to into self.fileList
		#df['_ba'] = None

		stop = time.time()
		logger.info(f'Load took {round(stop-start,2)} seconds.')
		return df

	def _checkColumns(self):
		"""Check columns in loaded vs sanpyColumns (and vica versa"""
		loadedColumns = self._df.columns
		for col in loadedColumns:
			if not col in self.sanpyColumns.keys():
				# loaded has unexpected column, leave it
				logger.error(f'error: bAnalysisDir did not find loaded col: "{col}" in sanpyColumns.keys()')
		for col in self.sanpyColumns.keys():
			if not col in loadedColumns:
				# loaded is missing expected, add it
				logger.error(f'error: bAnalysisDir did not find sanpyColumns.keys() col: "{col}" in loadedColumns')
				self._df[col] = ''

	def _updateLoadedAnalyzed(self):
		"""Refresh Loaded (L) and Analyzed (A) columns."""
		# .loc[i,'col'] gets from index (wrong)
		# .iloc[i,j] gets absolute row (correct)
		loadedCol = self._df.columns.get_loc('L')
		analyzedCol = self._df.columns.get_loc('A')
		for rowIdx in range(len(self._df)):
			# loaded
			if self.isLoaded(rowIdx):
				theChar = '\u2022'  # 'x'
			else:
				theChar = ''
			self._df.iloc[rowIdx, loadedCol] = theChar
			# analyzed
			if self.isAnalyzed(rowIdx):
				theChar = '\u2022'  # 'x'
			else:
				theChar = ''
			self._df.iloc[rowIdx, analyzedCol] = theChar

	def isLoaded(self, rowIdx):
		isLoaded = self._df.loc[rowIdx, '_ba'] is not None
		return isLoaded

	def isAnalyzed(self, rowIdx):
		isAnalyzed = False
		ba = self._df.loc[rowIdx, '_ba']
		#if ba is not None:
		if isinstance(ba, sanpy.bAnalysis):
			isAnalyzed = ba.isAnalyzed()
		return isAnalyzed

	def getAnalysis(self, rowIdx):
		"""
		Get bAnalysis object, will load if necc.

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
			#self._df.loc[rowIdx, '_ba'] = ba
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

	def getFileRow(self, path):
		"""
		Get dict representing one file (row in table). Loads bAnalysis to get headers.

		Args:
			path (Str): Full path to file.
			#rowIdx (int): Optional row index to assign in column 'Idx'

		Return:
			(tuple): tuple containing:

			- ba (bAnalysis): [sanpy.bAnalysis](/api/bAnalysis).
			- rowDict (dict): On success, otherwise None.
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

		#if rowIdx is not None:
		#	rowDict['Idx'] = rowIdx

		rowDict['I'] = 2 # need 2 because checkbox value is in (0,2)
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
		Return a dict with selected row as dict (includes detection parameters).

		Important to return a copy as our '_ba' is a pointer to bAnalysis.

		Returns:
			theRet (dict): Be sure to make a deep copy of ['_ba'] if neccessary.
		"""
		theRet = {}
		# use columns in main sanpyColumns, not in df
		#for colStr in self.columns:
		for colStr in self._df.columns:
			#theRet[colStr] = self._df.loc[rowIdx, colStr]
			theRet[colStr] = self._df.loc[rowIdx, colStr]
		#theRet['_ba'] = theRet['_ba'].copy()
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

		# delete from h5 file
		uuid = df.at[rowIdx, 'uuid']
		self.deleteFromHdf(uuid)

		# delete from df/model
		df = df.drop([rowIdx])
		df = df.reset_index(drop=True)
		self._df = df

	def duplicateRow(self, rowIdx):
		# duplicate rowIdx
		newIdx = rowIdx + 0.5

		rowDict = self.getRowDict(rowIdx)

		# CRITICAL: Need to make a deep copy of the _ba pointer to bAnalysis object
		baNew = copy.deepcopy(rowDict['_ba'])

		# copy of bAnalysis needs a new uuid
		new_uuid = str(uuid.uuid4())
		logger.info(f'assigning new uuid {new_uuid} to {baNew}')
		baNew.uuid = new_uuid

		rowDict['_ba'] = baNew

		dfRow = pd.DataFrame(rowDict, index=[newIdx])

		df = self._df
		df = df.append(dfRow, ignore_index=True)
		df = df.sort_values(by=['File'], axis='index', ascending=True, inplace=False)
		df = df.reset_index(drop=True)
		self._df = df

	def syncDfWithPath(self):
		"""
		Sync path with existing df. Used to pick up new/removed files"""
		pathFileList = self.getFileList(getFullPath=False)
		dfFileList = self._df['File'].tolist()

		'''
		print('=== pathFileList:')
		print(pathFileList)
		print('=== dfFileList:')
		print(dfFileList)
		'''

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

	def pool_build(self):
		"""Build one df with all anlysis. Use this in plot tool plugin.
		"""
		masterDf = None
		for row in range(self.numFiles):
			if not self.isAnalyzed(row):
				continue
			ba = self.getAnalysis(row)
			if ba.dfReportForScatter is not None:
				self.signalApp(f'adding "{ba.getFileName()}"')
				ba.dfReportForScatter['File Number'] = row
				if masterDf is None:
					masterDf = ba.dfReportForScatter
				else:
					masterDf = pd.concat([masterDf, ba.dfReportForScatter])
		#
		logger.info(f'final {len(masterDf)}')
		print(masterDf.head())
		self._poolDf = masterDf

		return self._poolDf

	def signalApp(self, str):
		"""Update status bar of SanPy app.

		TODO make this a signal and connect app to it.
			Will not be able to do this, we need to run outside Qt
		"""
		if self.myApp is not None:
			self.myApp.updateStatusBar(str)
		else:
			logger.info(str)

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

def test_hd5_2():
	folderPath = '/home/cudmore/Sites/SanPy/data'
	if 1:
		# save analysisDir hdf
		bad = analysisDir(folderPath)
		print('bad._df:')
		print(bad._df)
		#bad.saveDatabase()  # save .csv
		bad.saveHdf()  # save ALL bAnalysis in .h5

	if 0:
		# load h5 and reconstruct a bAnalysis object
		start = time.time()
		hdfPath = '/home/cudmore/Sites/SanPy/data/sanpy_recording_db.h5'
		with pd.HDFStore(hdfPath, 'r') as hdfStore:
			for key in hdfStore.keys():

				dfTmp = hdfStore[key]
				#path = dfTmp.iloc[0]['path']

				print('===', key)
				#if not key.startswith('/r6'):
				#	continue
				#for col in dfTmp.columns:
				#	print('  ', col, dfTmp[col])
				#print(key, type(dfTmp), dfTmp.shape)
				#print('dfTmp:')
				#print(dfTmp)


				#print(dfTmp.iloc[0]['_sweepX'])

				# load bAnalysis from a pandas DataFrame
				ba = sanpy.bAnalysis(fromDf=dfTmp)

				print(ba)

				ba.spikeDetect()  # this should reproduce exactly what was save ... It WORKS !!!

				'''
				ba = sanpy.bAnalysis(path)
				#instanceDict = vars(ba)
				ba.detectionDict = dfTmp.iloc[0]['detectionDict']
				ba.spikeDict = dfTmp.iloc[0]['spikeDict']
				ba.spikeTimes = dfTmp.iloc[0]['spikeTimes']
				ba.spikeClips = dfTmp.iloc[0]['spikeClips']
				ba.dfError = dfTmp.iloc[0]['dfError']
				ba.dfReportForScatter = dfTmp.iloc[0]['dfReportForScatter']
				ba._sweepX = dfTmp.iloc[0]['_sweepX']
				ba._sweepY = dfTmp.iloc[0]['_sweepY']
				'''

				'''
				memberName = key.split('_')[1]
				if memberName == 'path':
					path = dfTmp[0]  # .to_string()
					print('= loaded path:', path)
				elif memberName == 'detectionDict':
					detectionDict = dfTmp.iloc[0].to_dict()
					print('= loaded detectionDict:', detectionDict)
				elif memberName == 'spikeDict':
					spikeDict = dfTmp.to_dict('records')
					print('= loaded spikeDict:', type(spikeDict))
					#print(spikeDict[1])
				elif memberName == 'spikeTimes':
					spikeTimes = dfTmp.to_numpy().ravel()  # convert shape[1,0] to shape[1,]
					print('= loaded spikeTimes:', type(spikeTimes), spikeTimes.shape, spikeTimes.dtype)
				elif memberName == 'spikeClips':
					spikeClips = dfTmp.to_numpy()
					print('= loaded spikeClips:', type(spikeClips), spikeClips.shape, spikeClips.dtype)
				elif memberName == 'dfError':
					dfError = dfTmp
					print('= loaded dfError:', type(dfError), dfError.shape)
				elif memberName == 'dfReportForScatter':
					dfReportForScatter = dfTmp
					print('= loaded dfReportForScatter:', type(dfReportForScatter), dfReportForScatter.shape)
				elif memberName == 'sweepX':
					sweepX = dfTmp.to_numpy().ravel()  # convert shape[1,0] to shape[1,]
					print('= loaded sweepX:', type(sweepX), sweepX.shape, sweepX.dtype)
				elif memberName == 'sweepY':
					sweepY = dfTmp.to_numpy().ravel()
					print('= loaded sweepY:', type(sweepY), sweepY.shape, sweepY.dtype)
				'''
		stop = time.time()
		logger.info(f'h5 load took {round(stop-start,3)} seconds')

def test_hd5():
	import time
	start = time.time()
	hdfStore = pd.HDFStore('store.gzip')
	if 1:
		path = '/home/cudmore/Sites/SanPy/data'
		bad = analysisDir(path)

		# load all bAnalysis
		for idx in range(len(bad)):
			bad.getAnalysis(idx)

		hdfStore['df'] = bad.getDataFrame()  # save it
		bad.saveDatabase()

	if 0:
		df = hdfStore['df']  # load it
		print('loaded df:')
		print(df)
	stop = time.time()
	print(f'took {stop-start}')

def test_pool():
	path = '/home/cudmore/Sites/SanPy/data'
	bad = analysisDir(path)
	print('loaded df:')
	print(bad._df)

	bad.pool_build()

def test_timing():
	# not sure how to set logging level across all files
	#import logging
	#global logger
	#logger = get_logger(__name__, level=logging.DEBUG)

	global testTimingNumFiles
	path = '/home/cudmore/Sites/SanPy/data/timing'
	csvPath = os.path.join(path, 'sanpy_recording_db.csv')
	gzipPath = os.path.join(path, 'sanpy_recording_db.h5')

	maxFiles = 20
	loadBrute = []
	loadBruteSec = []
	saveHdf = []
	saveHdfSec = []
	loadHdf = []
	loadHdfSec = []
	hdfSize = []
	hdfSizeMb = []
	totalDurSec = []
	for i in range(maxFiles):
		print(f'====== {i}')
		start = time.time()
		testTimingNumFiles = i # limit number of files loaded by analysisDir
		bad = analysisDir(path)
		stop = time.time()
		seconds = round(stop-start,3)
		str = f'{i} Loading files took {seconds} seconds. {bad}'
		print(str)
		loadBrute.append(str)
		loadBruteSec.append(seconds)

		durSec = bad._df['Dur(s)'].sum()
		totalDurSec.append(durSec)

		start = time.time()
		bad.saveDatabase()
		stop = time.time()
		seconds = round(stop-start,3)
		str = f'  {i} saving hdf took: {seconds} seconds. {bad}'
		print(str)
		saveHdf.append(str)
		saveHdfSec.append(seconds)

		start = time.time()
		bad = analysisDir(path)
		stop = time.time()
		seconds = round(stop-start,3)
		str = f'  {i} loading hdf took: {seconds} seconds. {bad}'
		print(str)
		loadHdf.append(str)
		loadHdfSec.append(seconds)

		# size of gzip
		size = os.path.getsize(gzipPath)
		mbSize = size/(1024*1024)
		str = f'   {i} gzip mb:{mbSize}'
		print(str)
		hdfSize.append(str)
		hdfSizeMb.append(mbSize)

		# remove database(s) for next iteration
		os.remove(csvPath)
		os.remove(gzipPath)

	#
	for line in loadBrute:
		print(line)
	for line in saveHdf:
		print(line)
	for line in loadHdf:
		print(line)
	for line in hdfSize:
		print(line)

	print('loadBruteSec =', loadBruteSec)
	print('saveHdfSec =', saveHdfSec)
	print('loadHdfSec =', loadHdfSec)
	print('hdfSizeMb =', hdfSizeMb)
	print('totalDurSec =', totalDurSec)

def plotTiming():

	# before compression
	'''
	loadBruteSec = [1.181, 2.383, 3.518, 4.697, 5.825, 6.868, 8.059, 9.164, 10.228, 11.483, 12.566, 13.7, 14.77, 16.15, 17.163, 18.647, 19.871, 21.481, 23.251, 24.383]
	saveHdfSec = [0.136, 0.157, 0.228, 0.298, 0.363, 0.435, 0.529, 0.618, 0.645, 0.733, 0.795, 0.876, 0.933, 0.999, 1.046, 1.122, 1.2, 1.253, 1.453, 1.492]
	loadHdfSec = [0.185, 0.351, 0.51, 0.675, 0.837, 1.002, 1.123, 1.281, 1.484, 1.599, 1.761, 1.917, 2.077, 2.245, 2.469, 2.673, 2.761, 2.925, 4.605, 3.413]
	hdfSizeMb = [50.20532989501953, 99.39323425292969, 148.58114624023438, 197.76905059814453, 246.95687103271484, 296.14469146728516, 345.3325958251953, 394.52050018310547, 443.7084045410156, 492.89622497558594, 542.0840530395508, 591.2718734741211, 640.4596939086914, 689.6475982666016, 738.8355884552002, 788.0252990722656, 837.2132034301758, 886.4011077880859, 935.5889358520508, 984.7768402099609]
	totalDurSec = [60.0, 120.0, 180.0, 240.0, 300.0, 360.0, 420.0, 480.0, 540.0, 600.0, 660.0, 720.0, 780.0, 840.0, 900.0, 960.0, 1020.0, 1080.0, 1140.0, 1200.0]
	'''

	loadBruteSec = [1.202, 2.413, 3.567, 4.774, 6.0, 7.144, 8.36, 9.41, 10.61, 11.884, 12.969, 14.097, 15.32, 17.472, 18.197, 19.077, 20.117, 21.372, 22.427, 23.826]
	saveHdfSec = [0.14, 0.166, 0.238, 0.309, 0.38, 0.449, 0.541, 0.609, 0.659, 0.742, 0.816, 0.883, 0.956, 1.112, 1.058, 1.155, 1.224, 1.316, 1.363, 1.42]
	loadHdfSec = [0.198, 0.374, 0.533, 0.706, 0.862, 1.03, 1.146, 1.306, 1.51, 1.62, 1.778, 1.939, 2.289, 2.447, 2.483, 2.588, 2.741, 2.925, 3.073, 3.23]
	hdfSizeMb = [50.22023582458496, 99.40814876556396, 148.5960636138916, 197.7839708328247, 246.97179412841797, 296.15961742401123, 345.34752464294434, 394.53543186187744, 443.72333908081055, 492.9111614227295, 542.0989923477173, 591.2868156433105, 640.4746389389038, 689.6625461578369, 738.85045337677, 788.0382776260376, 837.2261848449707, 886.4140920639038, 935.6019229888916, 984.7898292541504]
	totalDurSec = [60.0, 120.0, 180.0, 240.0, 300.0, 360.0, 420.0, 480.0, 540.0, 600.0, 660.0, 720.0, 780.0, 840.0, 900.0, 960.0, 1020.0, 1080.0, 1140.0, 1200.0]

	# with compression

	totalDurMin = [x/60 for x in totalDurSec]

	import matplotlib.pyplot as plt
	plt.plot(totalDurMin, loadBruteSec, 'o-k')
	plt.plot(totalDurMin, loadHdfSec, 'o-r')
	plt.show()

	plt.plot(totalDurMin, hdfSizeMb, 'o-r')
	plt.show()

def testCloud():
	cloudDict = {
		'owner': 'cudmore',
		'repo_name': 'SanPy',
		'path': 'data'
	}
	bad = bAnalysisDirWeb(cloudDict)

if __name__ == '__main__':
	#test3()
	#test_hd5()
	test_hd5_2()
	#test_pool()
	#testCloud()

	#test_timing()
	#plotTiming()
