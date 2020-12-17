# Author: Robert Cudmore
# Date: 20181116

"""
Manager a list of abf files
"""

import os, json
from collections import OrderedDict

#from bAnalysis import bAnalysis
import sanpy

'''
gVideoFileColumns = ('Index', 'Path', 'File', 'kHz', 'Sweeps', 'Duration (sec)',
	'Acq Date', 'Acq Time',
	'dV/dt Threshold', 'Num Spikes', 'Analysis Date', 'Analysis Time')
'''
# abb 202012 moved into class
''
gVideoFileColumns = ('File', 'kHz', 'Sweeps', 'Duration (sec)',
	'Acq Date', 'Acq Time',
	'dV/dt Threshold', 'mV Threshold', 'Num Spikes', 'Analysis Date', 'Analysis Time')
''

#############################################################
class bFileList:

	def __init__(self, path):
		"""
		path: path to folder with .mp4 files
		"""

		#self.videoFileList = []

		self.videoFileColumns = ('File', 'kHz', 'Sweeps', 'Duration (sec)',
			'Acq Date', 'Acq Time',
			'dV/dt Threshold', 'mV Threshold', 'Num Spikes', 'Analysis Date', 'Analysis Time')

		self.path = path

		self.db = OrderedDict()
		self.databaseLoad()

		#self.populateFolder(path)

	def getFileError(self, file):
		fileDict = self.db[file]
		try:
			theRet = fileDict['abfError']
		except (KeyError) as e:
			theRet = True
			print('exception in bFileList.getFileError() did not find key "abfError" in:', file)
			print('fileDict')
			print(json.dumps(fileDict, indent=2))
		#
		return theRet

	def getFileValues(self, file):
		theRet = []

		fileDict = self.db[file]

		for colName in self.videoFileColumns:
			if colName == 'File':
				theRet.append(fileDict['file'])
			if colName == 'kHz':
				theRet.append(fileDict['kHz'])
			if colName == 'Sweeps':
				theRet.append(fileDict['numSweeps'])
			if colName == 'Duration (sec)':
				theRet.append(fileDict['durationSec'])
			if colName == 'Acq Date':
				theRet.append(fileDict['acqDate'])
			if colName == 'Acq Time':
				theRet.append(fileDict['acqTime'])
			if colName == 'dV/dt Threshold':
				theRet.append(fileDict['dvdtThreshold'])

			# abb 202012, minSpikeVm WILL NOT exist in older versions of _db.json
			try:
				if colName == 'mV Threshold':
					theRet.append(fileDict['minSpikeVm'])
			except:
				theRet.append('')

			if colName == 'Num Spikes':
				theRet.append(fileDict['numSpikes'])
			if colName == 'Analysis Date':
				theRet.append(fileDict['analysisDate'])
			if colName == 'Analysis Time':
				theRet.append(fileDict['analysisTime'])
		return theRet

	def refreshRow(self, ba):
		"""
		On saving analysis, update the database for a file

		ba: bAnalysis object
		path: path to abf file
		"""
		file = os.path.basename(ba.file)
		if file not in self.db.keys():
			# error
			print('WARNING: bFileList.databaseRefreshFile() did not find file in self.db, file:', file)
			pass
		else:
			self.db[file]['abfError'] = ba.loadError

			self.db[file]['dvdtThreshold'] = ba.dVthreshold
			self.db[file]['minSpikeVm'] = ba.minSpikeVm

			self.db[file]['numSpikes'] = ba.numSpikes

			dateAnalyzed = ba.dateAnalyzed #'%Y-%m-%d %H:%M:%S'
			myDate, myTime = dateAnalyzed.split(' ')

			self.db[file]['analysisDate'] = myDate
			self.db[file]['analysisTime'] = myTime

			#
			#
			'''
			self.videoFileList[treeViewRow].dict['dvdtThreshold'] = ba.dVthreshold
			self.videoFileList[treeViewRow].dict['numSpikes'] = ba.numSpikes
			self.videoFileList[treeViewRow].dict['analysisDate'] = myDate
			self.videoFileList[treeViewRow].dict['analysisTime'] = myTime
			'''

		self.databaseSave()

		#return self.videoFileList[treeViewRow].asTuple()

	def databaseRefresh(self):
		"""
		go through list of .abf file and compare to .json database
		"""
		useExtension = '.abf'
		videoFileIdx = 0
		fileList = sorted(os.listdir(self.path))
		mFile = len(fileList)
		for file in fileList:
			if file.startswith('.'):
				continue
			if file.endswith(useExtension):
				fullPath = os.path.join(self.path, file)

				if file in self.db.keys():
					# already in database
					#print('databaseRefresh.databaseRefresh() file is already in self.db')
					if not ('abfError' in self.db[file].keys()):
						# load file to make sure we don't get eror
						#tmpVideoFile = bVideoFile(videoFileIdx, fullPath)
						#self.db[file]['abfError'] = tmpVideoFile.loadError
						self.db[file]['abfError'] = None
					#
					continue

				print(str(videoFileIdx+1), 'of', str(mFile), 'bFileList.databaseRefresh parsing file:', file)

				myVideoFile = bVideoFile(videoFileIdx, fullPath)

				self.db[file] = OrderedDict()
				self.db[file]['file'] = file
				self.db[file]['abfError'] = myVideoFile.loadError
				self.db[file]['kHz'] = myVideoFile.dict['kHz']
				self.db[file]['durationSec'] = myVideoFile.dict['durationSec']
				self.db[file]['numSweeps'] = myVideoFile.dict['numSweeps']
				self.db[file]['dvdtThreshold'] = myVideoFile.dict['dvdtThreshold']
				self.db[file]['minSpikeVm'] = myVideoFile.dict['minSpikeVm'] # abb 202012
				self.db[file]['numSpikes'] = myVideoFile.dict['numSpikes']
				self.db[file]['analysisDate'] = myVideoFile.dict['analysisDate']
				self.db[file]['analysisTime'] = myVideoFile.dict['analysisTime']
				self.db[file]['acqDate'] = myVideoFile.dict['acqDate']
				self.db[file]['acqTime'] = myVideoFile.dict['acqTime']

				#print("   bFileList.databaseRefresh() self.db[file]['dvdtThreshold'] =" ,self.db[file]['dvdtThreshold'])

				videoFileIdx += 1

		# any time we refresh, we save
		self.databaseSave()

	def databaseLoad(self):
		# can't use this as dash is using it !!!
		enclosingFolder = os.path.basename(self.path)
		#enclosingFolder = 'db'
		dbPath = os.path.join(self.path, enclosingFolder + '_db.json')
		if os.path.isfile(dbPath):
			with open(dbPath, "r") as dbFile:
				self.db = json.load(dbFile)
		'''
		else:
			# make a new db from file list (slow)
			#self.databaseRefresh()
		'''
		# always refresh (will add new files if neccesary)
		self.databaseRefresh()

	def databaseSave(self):
		'''
		if self.db is None:
			print('bFileList.databaseSave() got None db')
			return
		'''
		# can't use this as dash is using it !!!
		if len(self.db) == 0:
			print('databaseSave() did not save, no abf files in folder', self.path)
		else:
			enclosingFolder = os.path.basename(self.path)
			#enclosingFolder = 'db'
			dbPath = os.path.join(self.path, enclosingFolder + '_db.json')
			print('bFileList.databaseSave() is saving:', dbPath)
			with open(dbPath, "w") as dbFile:
				json.dump(self.db, dbFile, indent=4)

	'''
	def populateFolder(self, path):
		"""
		given a folder path containing .abf files, populate with list of .abf files
		"""
		if not os.path.isdir(path):
			return

		useExtension = '.abf'
		videoFileIdx = 0
		for file in sorted(os.listdir(path)):
			if file.startswith('.'):
				continue
			if file.endswith(useExtension):
				fullPath = os.path.join(path, file)

				fromDict = None
				if file in self.db.keys():
					fromDict = self.db[file]
				#print('populateFolder()', file, fromDict)
				newVideoFile = bVideoFile(videoFileIdx, fullPath, fromDict)

				self.videoFileList.append(newVideoFile)
				videoFileIdx += 1
	'''

	def getColumns(self):
		return self.videoFileColumns

	def numFiles(self):
		if self.db is None:
			return 0
		else:
			return len(self.db.keys())

	def getList(self):
		#return self.videoFileList
		return self.db

	'''
	def getFileFromIndex(self, idx):
		return self.videoFileList[idx]
	'''

#############################################################
class bVideoFile:

	def __init__(self, index, path, fromDict=None):
		"""
		path: (str) full path to .mp4 video file
		fromDict: (dict) construct from database dict
		"""

		if not os.path.isfile(path):
			print('error: bVideoFile() could not open file path:', path)
			return

		self.path = path

		videoFileName = os.path.basename(path)

		# abb 20201009
		#self.dict = OrderedDict()
		self.dict = self._getDefaultDict()

		self.dict['file'] = videoFileName

		self.loadError = False # abb 202012

		# load abf file and grab parameters
		if fromDict is None:
			#
			loadWasGood = True
			'''
			try:
				ba = sanpy.bAnalysis(file=path) # load file as abf file (may fail)
			except (NotImplementedError) as e:
				print('bFileList.bVideoFile.__init__() exception, did not load file:', path)
				loadWasGood = False
			'''
			ba = sanpy.bAnalysis(file=path) # load file as abf file (may fail)
			if ba.loadError:
				print('bFileList.bVideoFile.__init__() exception, did not load file:', path)
				loadWasGood = False
				self.loadError = True
			else:
				#
				pntsPerMS = ba.dataPointsPerMs
				numSweeps = len(ba.sweepList)
				durationSec = max(ba.abf.sweepX)
				acqDate = ba.acqDate
				acqTime = ba.acqTime

				##
				##
				## THIS IS PROBABLY AN ERROR
				##
				##
				dvdtThreshold = None
				minSpikeVm = None # abb 202012
				numSpikes = None
				analysisDate = None
				analysisTime = None

		else:
			# loading from a saved _db.json file ???
			pntsPerMS = fromDict['kHz']
			numSweeps = fromDict['numSweeps']
			durationSec = fromDict['durationSec']
			acqDate = fromDict['acqDate']
			acqTime = fromDict['acqTime']

			dvdtThreshold = fromDict['dvdtThreshold']
			minSpikeVm = fromDict['minSpikeVm'] # abb 202012
			numSpikes = fromDict['numSpikes']
			analysisDate = fromDict['analysisDate']
			analysisTime = fromDict['analysisTime']

		if loadWasGood:
			self.dict['kHz'] = pntsPerMS
			self.dict['numSweeps'] = numSweeps
			self.dict['durationSec'] = int(round(durationSec))
			self.dict['acqDate'] = acqDate
			self.dict['acqTime'] = acqTime

			self.dict['dvdtThreshold'] = dvdtThreshold
			self.dict['minSpikeVm'] = minSpikeVm # abb 202012
			self.dict['numSpikes'] = numSpikes
			self.dict['analysisDate'] = analysisDate
			self.dict['analysisTime'] = analysisTime

	# abb 20201109
	def _getDefaultDict(self):
		retDict = {}
		retDict['file'] = ''
		retDict['kHz'] = None
		retDict['numSweeps'] = None
		retDict['durationSec'] = None
		retDict['acqDate'] = ''
		retDict['acqTime'] = ''

		retDict['dvdtThreshold'] = None
		retDict['minSpikeVm'] = None # abb 202012
		retDict['numSpikes'] = None
		retDict['analysisDate'] = ''
		retDict['analysisTime'] = ''

		return retDict

	def asString(self):
		theRet = ''
		for i, (k,v) in enumerate(self.dict.items()):
			if v is None:
				v = ''
			theRet += str(v) + ','
		return theRet

	def asTuple(self):
		str = self.asString()
		strList = []
		for s in str.split(','):
			strList.append(s)
		retTuple = tuple(strList)
		return retTuple

if __name__ == '__main__':
	videoPath = '/Users/cudmore/Dropbox/PiE/homecage-movie.mp4'
	videoPath = '/Users/cudmore/Dropbox/PiE/'
	myList = bVideoList(videoPath)

	for videoFile in myList.getList():
		print(videoFile.asString())
