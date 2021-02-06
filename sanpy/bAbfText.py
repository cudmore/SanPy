# 20210129

import os
import numpy as np

import tifffile

class bAbfText:
	"""
	mimic a pyabf file to load from a text file
	"""
	def __init__(self, path=None, theDict=None):
		"""
		path: path to .csv file with columns
			time (seconds)
			vm
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
		self.tifNorm = None
		self.tifHeader = None

		if theDict is not None:
			print('bAbfText() from dict')
			self.sweepX = theDict['sweepX']
			self.sweepY = theDict['sweepY']
		elif path.endswith('.tif'):
			self.sweepX, self.sweepY, self.tif, self.tifNorm = \
								self._abfFromLineScanTif(path)
			self.tifHeader = self._loadLineScanHeader(path)
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

		#
		# print results
		if self.tifHeader is not None:
			for k,v in self.tifHeader.items():
				print('  ', k, ':', v)
		print('  ', 'bAbfText secondsPerSample:', secondsPerSample, 'seconds/sample')
		print('  ', 'bAbfText self.dataRate:', self.dataRate, 'samples/second')
		print('  ', 'bAbfText self.dataPointsPerMs:', self.dataPointsPerMs)

	def setSweep(self, sweep):
		pass

	def _abfFromLineScanTif(self, path):
		"""
		"""
		if not os.path.isfile(path):
			print('ERROR: _abfFromLineScanTif did not find file:', path)
			return None, None, None, None

		tif = tifffile.imread(path)

		if len(tif.shape) == 3:
			tif = tif[:,:,1] # assuming image channel is 1
		tif = np.rot90(tif) # rotates 90 degrees counter-clockwise

		f0 = tif.mean()
		tifNorm = tif / f0

		# assuming this was exported using Olympus software
		# which gives us a .txt file
		self.tifHeader = self._loadLineScanHeader(path)
		self.tifHeader['shape'] = tifNorm.shape
		self.tifHeader['secondsPerLine'] = \
						self.tifHeader['totalSeconds'] / self.tifHeader['shape'][1]
		#tifHeader['abfPath'] = abfFile

		firstFrameSeconds = 0

		#
		# sum the inensities of each image line scan
		#print('tif.shape:', tif.shape) # like (146, 10000)
		yLineScanSum = [np.nan] * tif.shape[1]
		xLineScanSum = [np.nan] * tif.shape[1]
		for i in range(tif.shape[1]):
			theSum = np.sum(tif[:,i])
			theSum /= tif.shape[0] # norm to number of pixels in line
			yLineScanSum[i] = theSum
			xLineScanSum[i] = firstFrameSeconds + (self.tifHeader['secondsPerLine'] * i)

		xLineScanSum = np.asarray(xLineScanSum)
		yLineScanSum = np.asarray(yLineScanSum)

		# normalize to 0..1
		yLineScanSum = self._NormalizeData(yLineScanSum)

		return xLineScanSum, yLineScanSum, tif, tifNorm

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
		#
		return theRet

	def _NormalizeData(self, data):
		return (data - np.min(data)) / (np.max(data) - np.min(data))

def test_load_tif():
	path = '/Users/cudmore/data/dual-lcr/20210115/data/20210115__0001.tif'
	abf = bAbfText(path=path)

	import matplotlib.pyplot as plt
	plt.plot(abf.sweepX, abf.sweepY)
	plt.show()

if __name__ == '__main__':

	test_load_tif()
