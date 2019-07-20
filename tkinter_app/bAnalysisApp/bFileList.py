# Author: Robert Cudmore
# Date: 20181116

"""
Manager a list of abf files
"""

import os, json
from collections import OrderedDict

from bAnalysis import bAnalysis

gVideoFileColumns = ('Index', 'Path', 'File', 'kHz', 'Sweeps', 'Duration (sec)',
	'Acq Date', 'Acq Time',
	'dV/dt Threshold', 'Num Spikes', 'Analysis Date', 'Analysis Time')

#############################################################
class bFileList:

	def __init__(self, path):
		"""
		path: path to folder with .mp4 files
		"""

		self.videoFileList = []

		self.path = path

		self.db = OrderedDict()
		self.databaseLoad()

		self.populateFolder(path)

	def refreshRow(self, treeViewRow, path, ba):
		"""
		On saving analysis, update the database for a file
		
		path: path to abf file
		"""
		file = os.path.basename(path)
		if file not in self.db.keys():
			# error
			print('WARNING: bFileList.databaseRefreshFile() did not find file in self.db, file:', file)
			pass
		else:
			self.db[file]['dvdtThreshold'] = ba.dVthreshold
			self.db[file]['numSpikes'] = ba.numSpikes
			
			dateAnalyzed = ba.dateAnalyzed #'%Y-%m-%d %H:%M:%S'
			myDate, myTime = dateAnalyzed.split(' ')
			
			self.db[file]['analysisDate'] = myDate
			self.db[file]['analysisTime'] = myTime
		
			#
			#
			self.videoFileList[treeViewRow].dict['dvdtThreshold'] = ba.dVthreshold
			self.videoFileList[treeViewRow].dict['numSpikes'] = ba.numSpikes
			self.videoFileList[treeViewRow].dict['analysisDate'] = myDate
			self.videoFileList[treeViewRow].dict['analysisTime'] = myTime
			
		self.databaseSave()
		
		return self.videoFileList[treeViewRow].asTuple()
		
	def databaseRefresh(self):
		useExtension = '.abf'
		videoFileIdx = 0
		fileList = sorted(os.listdir(self.path))
		mFile = len(fileList)
		for file in fileList:
			if file.startswith('.'):
				continue
			if file.endswith(useExtension):
				if file in self.db.keys():
					# already in database
					continue

				fullPath = os.path.join(self.path, file)
				print(str(videoFileIdx+1), 'of', str(mFile), 'bFileList.databaseRefresh parsing file:', file)

				myVideoFile = bVideoFile(videoFileIdx, fullPath)

				self.db[file] = OrderedDict()
				self.db[file]['file'] = file
				self.db[file]['kHz'] = myVideoFile.dict['kHz']
				self.db[file]['durationSec'] = myVideoFile.dict['durationSec']
				self.db[file]['numSweeps'] = myVideoFile.dict['numSweeps']
				self.db[file]['dvdtThreshold'] = myVideoFile.dict['dvdtThreshold']
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
			print('bFileList.databaseSave is saving:', dbPath)
			with open(dbPath, "w") as dbFile:
				json.dump(self.db, dbFile, indent=4)

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

	def getColumns(self):
		return gVideoFileColumns

	def getList(self):
		return self.videoFileList

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

		videoFileName = os.path.basename(path)

		self.dict = OrderedDict()
		self.dict['index'] = index
		self.dict['path'] = path
		self.dict['file'] = videoFileName

		# load abf file and grab parameters
		if fromDict is None:
			#
			ba = bAnalysis(file=path)
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
			numSpikes = None
			analysisDate = None
			analysisTime = None
			
		else:
			pntsPerMS = fromDict['kHz']
			numSweeps = fromDict['numSweeps']
			durationSec = fromDict['durationSec']
			acqDate = fromDict['acqDate']
			acqTime = fromDict['acqTime']

			dvdtThreshold = fromDict['dvdtThreshold']
			numSpikes = fromDict['numSpikes']
			analysisDate = fromDict['analysisDate']
			analysisTime = fromDict['analysisTime']

		self.dict['kHz'] = pntsPerMS
		self.dict['numSweeps'] = numSweeps
		self.dict['durationSec'] = int(round(durationSec))
		self.dict['acqDate'] = acqDate
		self.dict['acqTime'] = acqTime

		self.dict['dvdtThreshold'] = dvdtThreshold
		self.dict['numSpikes'] = numSpikes
		self.dict['analysisDate'] = analysisDate
		self.dict['analysisTime'] = analysisTime

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