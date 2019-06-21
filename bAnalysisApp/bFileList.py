# Author: Robert Cudmore
# Date: 20181116

"""
Manager a list of abf files
"""

import os, json
from collections import OrderedDict

from bAnalysis import bAnalysis

gVideoFileColumns = ('Index', 'Path', 'File', 'kHz', 'Duration (sec)', 'Sweeps', 
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

	def databaseRefreshFile(self, path, ba):
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
		
		self.databaseSave()

	def databaseRefresh(self):
		useExtension = '.abf'
		videoFileIdx = 0
		for file in sorted(os.listdir(self.path)):
			if file.startswith('.'):
				continue
			if file.endswith(useExtension):
				if file in self.db.keys():
					# already in database
					continue

				fullPath = os.path.join(self.path, file)
				print('bFileList.databaseRefresh is parsing file:', file)
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
				self.db[file]['acqDate'] = None
				self.db[file]['acqTime'] = None

				print("   bFileList.databaseRefresh() self.db[file]['dvdtThreshold'] =" ,self.db[file]['dvdtThreshold'])
				
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

		#print('bVideoFile() index:', index, 'path:', path)

		if not os.path.isfile(path):
			print('error: bVideoFile() could not open file path:', path)
			return

		'''
		# open file using cv2
		myFile = cv2.VideoCapture(path)

		if not myFile.isOpened():
			print('error: bVideoFile() found file but could not open it:', path)
			return

		width = int(myFile.get(cv2.CAP_PROP_FRAME_WIDTH))
		height = int(myFile.get(cv2.CAP_PROP_FRAME_HEIGHT))
		numFrames = int(myFile.get(cv2.CAP_PROP_FRAME_COUNT))
		fps = myFile.get(cv2.CAP_PROP_FPS)
		'''

		videoFileName = os.path.basename(path)

		self.dict = OrderedDict()
		self.dict['index'] = index
		self.dict['path'] = path
		self.dict['file'] = videoFileName

		# load abf file and grab parameters
		if fromDict is None:
			ba = bAnalysis(file=path)
			pntsPerMS = ba.dataPointsPerMs
			numSweeps = len(ba.sweepList)
			durationSec = max(ba.abf.sweepX)
		else:
			pntsPerMS = fromDict['kHz']
			numSweeps = fromDict['numSweeps']
			durationSec = fromDict['durationSec']
			dvdtThreshold = fromDict['dvdtThreshold']
			numSpikes = fromDict['numSpikes']
			analysisDate = fromDict['analysisDate']
			analysisTime = fromDict['analysisTime']

		self.dict['kHz'] = pntsPerMS
		self.dict['durationSec'] = int(round(durationSec))
		self.dict['numSweeps'] = numSweeps
		self.dict['dvdtThreshold'] = dvdtThreshold
		self.dict['numSpikes'] = numSpikes
		self.dict['analysisDate'] = analysisDate
		self.dict['analysisTime'] = analysisTime

		'''
		self.dict['width'] = width
		self.dict['height'] = height
		self.dict['frames'] = numFrames
		self.dict['fps'] = round(fps, 2)
		self.dict['seconds'] = round(self.dict['frames'] / self.dict['fps'], 2)
		self.dict['minutes'] = round(self.dict['seconds'] / 60, 2)
		self.dict['numevents'] = ''
		self.dict['note'] = ''

		cv2.VideoCapture.release(myFile)

		# read the header from event .txt file
		videoDirName = os.path.dirname(path)
		eventFileName = videoFileName.replace('.mp4', '.txt')
		eventFilePath = os.path.join(videoDirName, eventFileName)
		#print('eventFilePath:', eventFilePath)
		if os.path.isfile(eventFilePath):
			#print('bVideoFile() is parsing event header:', eventFilePath)
			with open(eventFilePath) as f:
				header = f.readline().strip()
				for n in header.split(','):
					if len(n) > 0:
						name, value = n.split('=')
						if name == 'videoFileNote':
							self.dict['note'] = value
						if name == 'numEvents':
							self.dict['numevents'] = value
		'''

	def asString(self):
		theRet = ''
		for i, (k,v) in enumerate(self.dict.items()):
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
