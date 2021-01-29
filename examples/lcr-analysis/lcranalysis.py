# 20210128

import os, pprint
import numpy as np
import matplotlib.pyplot as plt
import tifffile
import pyabf

import lcrData

def loadLineScanHeader(path):
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

def loadLineScan(path):
	"""
	path: full path to .tif file
	"""
	#tifHeader = loadLineScanHeader(path)
	if not os.path.isfile(path):
		print('ERROR: loadLineScan did not find file:', path)
		return None
	else:
		tif = tifffile.imread(path)
		return tif

def myLoad(myDict):
	tifFile = myDict['tif']
	abfFile = myDict['abf']

	# todo: check they exist

	tif = loadLineScan(tifFile)
	#print('tif.shape:', tif.shape)
	#print('tif.dtype:', tif.dtype)
	if len(tif.shape) == 3:
			tif = tif[:,:,1] # assuming image channel is 1
	tif = np.rot90(tif) # rotates 90 degrees counter-clockwise
	f0 = tif.mean()
	tifNorm = tif / f0
	#print(type(tifNorm))

	tifHeader = loadLineScanHeader(tifFile)
	tifHeader['shape'] = tifNorm.shape
	tifHeader['secondsPerLine'] = tifHeader['totalSeconds'] / tifHeader['shape'][1]

	abf = pyabf.ABF(abfFile)

	return tif, tifHeader, abf

def myPlot(tif, tifHeader, abf):
	"""
	tif: 2D numpy.array
	tifHeader: dict
	abf: abf file
	"""

	xMaxImage = tifHeader['totalSeconds'] #35.496 # seconds

	fig, axs = plt.subplots(3, 1, sharex=True)

	# e-phys
	# has 100 ms + 5 ms ttl
	'''
	preRoll = 100 / 1000 # ms -> sec
	ttlDur = 5 / 1000 # ms -> sec
	xMinPhys = (preRoll + ttlDur) * -1
	'''
	xMinPhys = 0

	xPlot = abf.sweepX
	xPlot += xMinPhys # e-phys recording starts with (100 ms + 5 ms ttl)
	yPlot = abf.sweepY
	xMaxRecording = abf.sweepX[-1] # seconds
	print('xMaxRecording:', xMaxRecording)
	# time of first frame, shift image by this amount
	tagTimesSec = abf.tagTimesSec
	firstFrameSeconds = tagTimesSec[0]
	print('firstFrameSeconds:', firstFrameSeconds)

	xMax = max(xMaxImage+firstFrameSeconds, xMaxRecording)
	xMaxLim = xMax
	#xMaxLim = 2.5 # debugging

	# image
	xMin = firstFrameSeconds
	yMin = 0
	yMax = tifHeader['umLength'] #57.176
	#extent = [xMin, xMaxImage, yMax, yMin] # flipped y
	extent = [xMin, xMax, yMin, yMax] # flipped y
	cmap = 'inferno' #'Greens' # 'inferno'
	axs[0].imshow(tif, aspect='auto', cmap=cmap, extent=extent)
	#axs[0].imshow(tif, aspect='auto', extent=extent)
	#axs[0].imshow(tif, aspect='auto')
	axs[0].set_xlim([xMinPhys, xMaxLim])
	axs[0].set_ylabel('Line (um)')
	axs[0].spines['right'].set_visible(False)
	axs[0].spines['top'].set_visible(False)

	#
	# sum the inensities of each image line scan
	#print('tif.shape:', tif.shape) # like (146, 10000)
	yLineScanSum = [np.nan] * tif.shape[1]
	xLineScanSum = [np.nan] * tif.shape[1]
	for i in range(tif.shape[1]):
		theSum = np.sum(tif[:,i])
		theSum /= tif.shape[0]
		yLineScanSum[i] = theSum
		xLineScanSum[i] = firstFrameSeconds + (tifHeader['secondsPerLine'] * i)
	meanLineScanSum = np.mean(yLineScanSum)
	stdLineScanSum = np.std(yLineScanSum)

	#
	# overlay vm on top of image
	if 0:
		axRight = axs[0].twinx()  # instantiate a second axes that shares the same x-axis
		axRight.plot(xPlot, yPlot, 'w', linewidth=0.5)

	axs[1].plot(xPlot, yPlot, 'k')
	axs[1].margins(x=0)
	axs[1].set_xlim([xMinPhys, xMaxLim])
	axs[1].set_xlabel('Time (s)')
	axs[1].set_ylabel('Vm (mV)')
	axs[1].spines['right'].set_visible(False)
	axs[1].spines['top'].set_visible(False)

	# plot tag times (sec), the start of each line scan
	#tagTimesY = [-50] * len(tagTimesSec)
	#axs[1].plot(tagTimesSec, tagTimesY, '.r')

	#
	# plot the sum of inensity along each line
	# this might contribute to membrane depolarizations !!!
	axs[2].plot(xLineScanSum, yLineScanSum)
	axs[2].axhline(y=meanLineScanSum, linewidth=1, color='r')
	axs[2].axhline(y=meanLineScanSum+stdLineScanSum, linewidth=1, color='r')
	axs[2].margins(x=0)
	axs[2].set_xlim([xMinPhys, xMaxLim])
	tmpMinY = meanLineScanSum - 1.5 * stdLineScanSum
	tmpMaxY = meanLineScanSum + 1.5 * stdLineScanSum
	axs[2].set_ylim([tmpMinY, tmpMaxY])
	axs[2].set_ylabel('Sum Line Inensity')
	axs[2].spines['right'].set_visible(False)
	axs[2].spines['top'].set_visible(False)

	plt.show()

def test_header():
	tifFile = '/Users/cudmore/data/dual-lcr/20201222/data/20201222_.tif'
	abfFile = '/Users/cudmore/data/dual-lcr/20201222/data/20d22000.abf'
	tifHeader = loadLineScanHeader(tifFile)
	print(tifHeader)

def test_plot():
	fileNumber = 12
	tif, tifHeader, abf = myLoad(lcrData.dataList[fileNumber])

	# bingo !!!
	#print(abf.tagTimesSec) # bingo!!! list of tag times in seconds

	pprint.pprint(tifHeader)

	myPlot(tif, tifHeader, abf)

if __name__ == '__main__':
	#test_header()

	test_plot()
