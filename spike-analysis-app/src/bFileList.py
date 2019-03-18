# Author: Robert Cudmore
# Date: 20181116

"""
Manager a list of video files
"""

import os
from collections import OrderedDict 

from bAnalysis import bAnalysis

#gVideoFileColumns = ('index', 'path', 'file', 'width', 'height', 'frames', 'fps', 'seconds', 'minutes', 'numevents', 'note')
gVideoFileColumns = ('Index', 'Path', 'File', 'kHz', 'Duration (sec)', 'Sweeps')

#############################################################
class bFileList:

	def __init__(self, path):
		"""
		path: path to folder with .mp4 files
		"""
		
		self.videoFileList = []

		self.path = path
		
		self.populateFolder(path)
		
	def populateFolder(self, path):
		"""
		given a folder path containing .mp4 files, populate with list of .mp4 files
		"""
		if not os.path.isdir(path):
			return
			
		useExtension = '.abf'
		videoFileIdx = 0
		for file in os.listdir(path):
			if file.startswith('.'):
				continue
			if file.endswith(useExtension):
				fullPath = os.path.join(path, file)
				newVideoFile = bVideoFile(videoFileIdx, fullPath)
				self.videoFileList.append(newVideoFile)
				videoFileIdx += 1
		
	def getColumns(self):
		return gVideoFileColumns

	def getList(self):
		return self.videoFileList
	
#############################################################
class bVideoFile:

	def __init__(self, index, path):
		"""
		path: (str) full path to .mp4 video file
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
		ba = bAnalysis(file=path)
		pntsPerMS = ba.dataPointsPerMs
		numSweeps = len(ba.sweepList)
		durationSec = max(ba.abf.sweepX)
		
		self.dict['kHz'] = pntsPerMS
		self.dict['durationSec'] = int(round(durationSec))
		self.dict['numSweeps'] = numSweeps

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
		