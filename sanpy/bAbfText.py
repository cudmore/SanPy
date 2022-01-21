# 20210129

import os
import numpy as np

import tifffile

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class bAbfText:
	"""
	mimic a pyabf file to load from a text file
	"""
	def __init__(self, path=None, theDict=None):
		"""
		path is either:
			path to .csv file with columns (time (seconds), vm)
			path to .tif file

		theDict:
			sweepX
			sweepY
		"""

		self.path = path

		self.sweepX = None
		self.sweepY = None
		self.dataRate = None
		self.dataPointsPerMs = None
		self.sweepList = [0]

		self.tif = None
		self.tifNorm = None # not used
		self.tifHeader = None

		if theDict is not None:
			print('bAbfText() from dict')
			self.sweepX = theDict['sweepX']
			self.sweepY = theDict['sweepY']
		elif path.endswith('.tif'):
			self.sweepX, self.sweepY, self.tif, self.tifNorm = \
								self._abfFromLineScanTif(path)
			self.tifHeader = self._loadLineScanHeader(path)

			#logger.info(f'tif params: {np.min(self.tif)} {np.max(self.tif)} {self.tif.shape} {self.tif.dtype}')
		else:
			print('bAbfText() from path', path)
			if not os.path.isfile(path):
				print('ERROR: Did not find file:', path)
				return

			tmpNumPy = np.loadtxt(path, skiprows=1, delimiter=',')
			self.sweepX = tmpNumPy[:,0]
			self.sweepY = tmpNumPy[:,1]

		#
		# linescan is like
		# 'secondsPerLine': 0.0042494285714285715,
		# 1 / secondsPerLine = 235.32
		secondsPerSample = self.sweepX[1] - self.sweepX[0]
		samplesPerSecond = 1 / secondsPerSample
		self.dataRate = samplesPerSecond #235 #10000 # samples per second

		# todo: calculat from dataRate
		secondsPerSample = 1 / samplesPerSecond
		msPerSample = secondsPerSample * 1000
		samplesPerMs = 1 / msPerSample
		self.dataPointsPerMs = samplesPerMs #4.255 #1/235*1000,10 # 10 kHz

		self.sweepUnitsX = 'todo: fix'
		self.sweepUnitsY = 'todo: fix'

		self.myRectRoi = None
		self.myRectRoiBackground = None
		self.minLineScan = None

		defaultRect = self.defaultTifRoi_background()  # for kymograph
		self.updateTifRoi_background(defaultRect)

		defaultRect = self.defaultTifRoi()  # for kymograph
		self.updateTifRoi(defaultRect)

		#
		# print results
		'''
		if self.tifHeader is not None:
			for k,v in self.tifHeader.items():
				print('  ', k, ':', v)

		print('  ', 'bAbfText secondsPerSample:', secondsPerSample, 'seconds/sample')
		print('  ', 'bAbfText self.dataRate:', self.dataRate, 'samples/second')
		print('  ', 'bAbfText self.dataPointsPerMs:', self.dataPointsPerMs)
		'''

	def defaultTifRoi_background(self):
		"""
		Default ROI for kymograph background

		- height/width about 5 pixels
		- position near the end of the line
		"""
		widthTif = self.tif.shape[1]
		heightTif = self.tif.shape[0]
		insetPixels = 10  # from end of line (top)
		roiWidthHeight = 5
		#tifHeightPercent = self.tif.shape[0] * 0.15

		left = int(widthTif/2)
		top = heightTif - insetPixels
		right = left + roiWidthHeight - 1
		bottom = top - roiWidthHeight + 1

		return [left, top, right, bottom]

	def defaultTifRoi(self):
		"""
		A default rectangular ROI for main kymograph analysis.

		Return:
			list: [left, top, right, bottom]
		"""
		xRoiPos = 0  # startSeconds
		yRoiPos = 0  # pixels
		widthRoi = self.tif.shape[1]
		heightRoi = self.tif.shape[0]
		tifHeightPercent = self.tif.shape[0] * 0.15
		#print('tifHeightPercent:', tifHeightPercent)
		yRoiPos += tifHeightPercent
		heightRoi -= 2 * tifHeightPercent

		#pos = (xRoiPos, yRoiPos)
		#size = (widthRoi, heightRoi)

		left = xRoiPos
		top = yRoiPos + heightRoi
		right = xRoiPos + widthRoi
		bottom = yRoiPos

		left = int(left)
		top = int(top)
		right = int(right)
		bottom = int(bottom)

		return [left, top, right, bottom]

	def getTifRoiBackground(self):
		return self.myRectRoiBackground

	def getTifRoi(self):
		return self.myRectRoi

	def updateTifRoi_background(self, theRect=None):
		if theRect is None:
			theRect = self.defaultTifRoi_background()
		if theRect is not None:
			left = theRect[0]
			top = theRect[1]
			right = theRect[2]
			bottom = theRect[3]

		self.myRectRoiBackground = theRect

		tif = self.tif
		theSum = np.sum(tif[bottom:top, left:right])

		return theSum

	def updateTifRoi(self, theRect=None):
		"""
		Recalculate (sweepX, sweepY) based on user specified rect ROI

		Args:
			theRect (list): left, top, right, bottom
		"""

		#logger.info(theRect)

		self.myRectRoi = theRect

		firstFrameSeconds = 0

		tif = self.tif

		left = 0  # startSec
		top = tif.shape[0]
		right = tif.shape[1]  # stopSec
		botom = 0
		if theRect is not None:
			left = theRect[0]
			top = theRect[1]
			right = theRect[2]
			bottom = theRect[3]

		# number of pixels in subset of line scan
		numPixels = top - bottom + 1

		theBackground = self.updateTifRoi_background()

		# retains shape of entire tif
		yLineScanSum = [np.nan] * tif.shape[1]
		xLineScanSum = [np.nan] * tif.shape[1]
		for i in range(tif.shape[1]):
			# always assign time
			xLineScanSum[i] = firstFrameSeconds + (self.tifHeader['secondsPerLine'] * i)

			if i<left or i>right:
				continue

			# each line scan
			theSum = np.sum(tif[bottom:top, i])

			# background subtract
			theSum -= theBackground

			# f / f_0
			theSum /= numPixels  # tif.shape[0] # norm to number of pixels in line
			yLineScanSum[i] = theSum

		xLineScanSum = np.asarray(xLineScanSum)
		yLineScanSum = np.asarray(yLineScanSum)

		# derive simplified f/f0 by dividing by min
		self.minLineScan = np.nanmin(yLineScanSum)
		yLineScanSum /= self.minLineScan

		self.sweepX = xLineScanSum
		self.sweepY = yLineScanSum

	def setSweep(self, sweep):
		pass

	def _abfFromLineScanTif(self, path, theRect=None):
		"""

		Returns:
			xLineScanSum (np.ndarray) e.g. sweepX
			yLineScanSum (np.ndarray) e.g. sweepY
		"""
		if not os.path.isfile(path):
			print('ERROR: _abfFromLineScanTif did not find file:', path)
			return None, None, None, None

		tif = tifffile.imread(path)
		if len(tif.shape) == 3:
			tif = tif[:,:,1] # assuming image channel is 1
		tif = np.rot90(tif) # rotates 90 degrees counter-clockwise

		f0 = tif.mean()
		tifNorm = (tif - f0) / f0

		self.tif = tif

		# assuming this was exported using Olympus software
		# which gives us a .txt file
		self.tifHeader = self._loadLineScanHeader(path)
		self.tifHeader['shape'] = tif.shape
		self.tifHeader['secondsPerLine'] = \
						self.tifHeader['totalSeconds'] / self.tifHeader['shape'][1]
		#tifHeader['abfPath'] = abfFile

		defaultRect = self.defaultTifRoi()
		self.updateTifRoi(defaultRect)

		firstFrameSeconds = 0

		#
		# sum the inensities of each image line scan
		#print('tif.shape:', tif.shape) # like (146, 10000)
		'''
		yLineScanSum = [np.nan] * tif.shape[1]
		xLineScanSum = [np.nan] * tif.shape[1]
		for i in range(tif.shape[1]):
			theSum = np.sum(tif[:,i])
			theSum /= tif.shape[0] # norm to number of pixels in line
			yLineScanSum[i] = theSum
			xLineScanSum[i] = firstFrameSeconds + (self.tifHeader['secondsPerLine'] * i)

		xLineScanSum = np.asarray(xLineScanSum)
		yLineScanSum = np.asarray(yLineScanSum)
		'''

		# normalize to 0..1
		# 20220114, was this
		# yLineScanSum = self._NormalizeData(yLineScanSum)

		#print('bAbfText xLineScanSum:', xLineScanSum.shape)
		#print('bAbfText yLineScanSum:', yLineScanSum.shape)

		return self.sweepX, self.sweepY, tif, tifNorm

	def _loadLineScanHeader(self, path):
		"""
		path: full path to tif

		we will load and parse coresponding .txt file

		returns dict:
			numPixels:
			umLength:
			umPerPixel:
			totalSeconds:
		"""
		# "X Dimension"	"138, 0.0 - 57.176 [um], 0.414 [um/pixel]"
		# "T Dimension"	"1, 0.000 - 35.496 [s], Interval FreeRun"
		# "Image Size(Unit Converted)"	"57.176 [um] * 35500.000 [ms]"
		txtFile = os.path.splitext(path)[0] + '.txt'

		if not os.path.isfile(txtFile):
			print('ERROR: loadLineScanHeader did not find file:', txtFile)
			return None

		theRet = {'tif': path}

		theRet['numLines'] = self.tif.shape[1]

		with open(txtFile, 'r') as fp:
			lines = fp.readlines()
			for line in lines:
				line = line.strip()
				if line.startswith('"X Dimension"'):
					line = line.replace('"', "")
					line = line.replace(',', "")
					#print('loadLineScanHeader:', line)
					# 2 number of pixels in line
					# 5 um length of line
					# 7 um/pixel
					splitLine = line.split()
					for idx, split in enumerate(splitLine):
						#print('  ', idx, split)
						if idx == 2:
							numPixels = int(split)
							theRet['numPixels'] = numPixels
						elif idx == 5:
							umLength = float(split)
							theRet['umLength'] = umLength
						elif idx == 7:
							umPerPixel = float(split)
							theRet['umPerPixel'] = umPerPixel

				elif line.startswith('"T Dimension"'):
					line = line.replace('"', "")
					line = line.replace(',', "")
					#print('loadLineScanHeader:', line)
					# 5 total duration of image acquisition (seconds)
					splitLine = line.split()
					for idx, split in enumerate(splitLine):
						#print('  ', idx, split)
						if idx == 5:
							totalSeconds = float(split)
							theRet['totalSeconds'] = totalSeconds

							#theRet['secondsPerLine'] =

				#elif line.startswith('"Image Size(Unit Converted)"'):
				#	print('loadLineScanHeader:', line)

		theRet['shape'] = self.tif.shape
		theRet['secondsPerLine'] = theRet['totalSeconds'] / theRet['shape'][1]
		theRet['linesPerSecond'] = 1 / theRet['secondsPerLine']
		#
		return theRet

	def _NormalizeData(self, data):
		"""
		normalize to [0..1]
		"""
		return (data - np.min(data)) / (np.max(data) - np.min(data))

def test_load_tif():
	path = '/Users/cudmore/data/dual-lcr/20210115/data/20210115__0001.tif'
	abf = bAbfText(path=path)

	import matplotlib.pyplot as plt
	plt.plot(abf.sweepX, abf.sweepY)
	plt.show()

if __name__ == '__main__':

	test_load_tif()
