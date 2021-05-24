"""
20210128

Load and plot dual line-scan .tif and whole-cell recording .abf files

Usage:
	cd dual-analysis
	python3 dualPlot.py

Interface:
	Once a plot is opened, use the keyboard like this:
		1: Toggle Vm plot over kymograph image
		2: Toggle middle Ca plot
		3: Toggle middle Vm plot
		4: Toggle subplot showing lower Vm

		n: go to next file in dual-database.xlsx
		p: go to previous file in dual-database.xlsx

Save:
	to save the entire plot, use the toolbar and
	specify desired file extension from (.svg, .tif, .png, .jpg)

Install:
	pip3 install --upgrade -r requirements.txt

Notes:
	- the imaging starts at a variable time into the abf recording
		get the start time of the .tif wrt the abf with abf.tagTimesSec[0]

	- there are a smaller number of abf.tagTimesSec
		should correspond to the number of line scans (during abf recording) but it does not

	- the interval between abf.tagTimesSec is way to long
		should be the duration of each tif file scan but it is not

"""

import os, sys
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

import tifffile
import pyabf

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

			elif line.startswith('"Date"'):
				line = line.replace('"Date"', "")
				line = line.replace('"', "")
				line = line.replace('\t', "")
				theRet['tifDateTime'] = line

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
	"""
	myDict['tif']: pull path
	myDict['abf']: pull path
	"""
	tifFile = myDict['tif']
	abfFile = myDict['abf']

	# todo: check they exist
	if not os.path.isfile(tifFile):
		print('ERROR: myLoad() did not find tifFile:', tifFile)
		return None, None, None
	if not os.path.isfile(abfFile):
		print('ERROR: myLoad() did not find abfFile:', abfFile)
		return None, None, None

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
	tifHeader['abfPath'] = abfFile

	abf = pyabf.ABF(abfFile)

	tagTimesSec = abf.tagTimesSec
	firstFrameSeconds = tagTimesSec[0]
	tifHeader['firstFrameSeconds'] = firstFrameSeconds

	xMaxRecordingSec = abf.sweepX[-1] # seconds
	tifHeader['xMaxRecordingSec'] = xMaxRecordingSec

	return tif, tifHeader, abf


def myPlot(tif, tifHeader, abf, fileNumber=None, df=None):
	"""
	tif: 2D numpy.array
	tifHeader: dict
	abf: abf file
	"""
	def myKeyPress(event):
		#print('press', event.key)
		sys.stdout.flush()
		if event.key == '1':
			# vm line in ax[0] image
			visible = ptrRecordingOnImage.get_visible()
			ptrRecordingOnImage.set_visible(not visible)
			#
			axRight.axes.yaxis.set_visible(not visible)
			axRight.spines['right'].set_visible(not visible)
			fig.canvas.draw()
		if event.key == '2':
			# Ca line in axs[1]
			visible = ptrLineScanSum.get_visible()
			ptrLineScanSum.set_visible(not visible)
			fig.canvas.draw()
		if event.key == '3':
			# Vm line in axs[1]
			visible = ptrVmPlot2.get_visible()
			ptrVmPlot2.set_visible(not visible)
			#
			axRight1.axes.yaxis.set_visible(not visible)
			axRight1.spines['right'].set_visible(not visible)
			fig.canvas.draw()
		if event.key == '4':
			# toggle Vm axs[2] on/off
			visible = axs[2].get_visible()
			axs[2].set_visible(not visible)
			fig.canvas.draw()

		if event.key == 'n':
			newFile = fileNumber + 1
			print('key "n", newFile is', newFile)
			if newFile < len(df):
				myLoadAndPlot0(newFile, df=df) # plot image, vm, sum Ca
		if event.key == 'p':
			newFile = fileNumber - 1
			print('key "p", newFile is', newFile)
			if newFile >= 0:
				myLoadAndPlot0(newFile, df=df) # plot image, vm, sum Ca

	#
	df = df # used by callback
	fileNumber = fileNumber # used by callback

	plotVm  = 1
	if plotVm:
		numPanels = 3
	else:
		numPanels = 2
	fig, axs = plt.subplots(numPanels, 1, sharex=True)
	fig.canvas.mpl_connect('key_press_event', myKeyPress)

	titleStr = ''
	if fileNumber is not None:
		titleStr += str(fileNumber+1) + ' '
	titleStr += os.path.split(tifHeader['tif'])[1]
	fig.suptitle(titleStr)

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
	#xMaxRecording = abf.sweepX[-1] # seconds
	xMaxRecordingSec = tifHeader['xMaxRecordingSec']
	#print('xMaxRecording:', xMaxRecording)

	# time of first frame, shift image by this amount
	tagTimesSec = abf.tagTimesSec
	firstFrameSeconds = tagTimesSec[0]
	# plot tags
	#yTagTimeSec = [0.5] * len(abf.tagTimesSec)
	#axs[1].plot(tagTimesSec, yTagTimeSec, 'og')
	print('  abf.tagTimesSec has', len(abf.tagTimesSec), 'tags,'
		'first tag seconds:', tagTimesSec[0],
		'first interval:', tagTimesSec[1] - tagTimesSec[0])

	xMaxImage = tifHeader['totalSeconds'] #35.496 # seconds
	#xMax = max(xMaxImage+firstFrameSeconds, xMaxRecordingSec)
	xMax = max(xMaxImage+firstFrameSeconds, xMaxRecordingSec)
	xMaxLim = min(xMaxImage+firstFrameSeconds, xMaxRecordingSec)
	print('  xMaxLim:', xMaxLim, 'the max on the x-axis (is min between image duration and abf record time')

	# image
	xMin = firstFrameSeconds
	yMin = 0
	yMax = tifHeader['umLength'] #57.176
	extent = [xMin, xMax, yMin, yMax] # flipped y
	cmap = 'inferno' #'Greens' # 'inferno'
	axs[0].imshow(tif, aspect='auto', cmap=cmap, extent=extent)
	axs[0].set_xlim([xMin, xMaxLim])
	axs[0].set_ylabel('Line (um)')
	axs[0].spines['right'].set_visible(False)
	axs[0].spines['top'].set_visible(False)
	#axs[0].spines['bottom'].set_visible(False)
	#axs[0].axes.xaxis.set_visible(False)

	#
	# overlay vm on top of image
	if 1:
		axRight = axs[0].twinx()  # instantiate a second axes that shares the same x-axis
		ptrRecordingOnImage, = axRight.plot(xPlot, yPlot, 'w', linewidth=0.5)
		axRight.spines['top'].set_visible(False)

	#
	# sum the inensities of each image line scan
	#print('tif.shape:', tif.shape) # like (146, 10000)
	yLineScanSum = [np.nan] * tif.shape[1]
	xLineScanSum = [np.nan] * tif.shape[1]
	for i in range(tif.shape[1]):
		theSum = np.sum(tif[:,i])
		theSum /= tif.shape[0]
		yLineScanSum[i] = theSum
		# checking if pre-roll is causing additional delay -->> conclude no
		#xLineScanSum[i] = -0.1 + firstFrameSeconds + (tifHeader['secondsPerLine'] * i)
		#xLineScanSum[i] = -0.004 + firstFrameSeconds + (tifHeader['secondsPerLine'] * i)
		# tpmTagInterval is the time interval (sec) between tags in abf header
		#tpmTagInterval = 6 * 0.025499999999999967
		#xLineScanSum[i] = -tpmTagInterval + firstFrameSeconds + (tifHeader['secondsPerLine'] * i)
		# was this
		xLineScanSum[i] = firstFrameSeconds + (tifHeader['secondsPerLine'] * i)


	# vm
	if plotVm:
		ptrVmPlot1, = axs[2].plot(xPlot, yPlot, 'k')
		axs[2].margins(x=0)
		axs[2].set_xlim([xMin, xMaxLim])
		axs[2].set_xlabel('Time (s)')
		axs[2].set_ylabel('Vm (mV)')
		axs[2].spines['right'].set_visible(False)
		axs[2].spines['top'].set_visible(False)

	# plot tag times (sec), the start of each line scan
	#tagTimesY = [0.5] * len(tagTimesSec)
	#axs[1].plot(tagTimesSec, tagTimesY, '.r')

	#
	# plot the sum of inensity along each line
	# this might contribute to membrane depolarizations !!!
	plotCaSum = True
	if plotCaSum:
		#yLineScanSumNorm = NormalizeData(yLineScanSum)
		#ptrLineScanSum, = axs[1].plot(xLineScanSum, yLineScanSumNorm, 'r')
		ptrLineScanSum, = axs[1].plot(xLineScanSum, yLineScanSum, 'r')

		axs[1].margins(x=0)
		axs[1].set_xlim([xMin, xMaxLim])
		axs[1].set_ylabel('f/f_0 (au)')
		axs[1].spines['right'].set_visible(False)
		axs[1].spines['top'].set_visible(False)
		#axs[1].axes.xaxis.set_visible(False)
		#axs[1].set_xlabel('Time (s)')

		#
		# overlay vm on top of ca sum
		if 1:
			axRight1 = axs[1].twinx()  # instantiate a second axes that shares the same x-axis
			ptrVmPlot2, = axRight1.plot(xPlot, yPlot, 'k', linewidth=0.5)
			axRight1.spines['top'].set_visible(False)

		'''
		# save a csv/txt file (open with bAbfText)
		tmpDf = pd.DataFrame()
		tmpDf['time (s)'] = xLineScanSum
		tmpDf['y'] = yLineScanSumNorm
		tmpDf.to_csv('/Users/cudmore/Desktop/caInt.csv', header=True, index=False)
		'''

	#
	# cross cor between 'sum of line scan intensity' and Vm
	# todo: work on this, need to subsample Vm to match pnts in kymograph
	if 0:
		fig2, ax2 = plt.subplots(1, 1, sharex=True)
		print('yLineScanSum:', len(yLineScanSum))
		print('yPlot:', len(yPlot[0:-1:4]))
		ax2.xcorr(yLineScanSum, yPlot, usevlines=True,
				maxlags=50, normed=True, lw=2)
		ax2.grid(True)

	plt.show()

def myLoadAndPlot0(fileNumber, df):
	"""
	todo: add myLoadAndPlot(tif, abf)
	"""

	dataPath = df['data path'].loc[0]
	dateFolder = df['date folder'].loc[fileNumber]
	dateFolder = str(int(dateFolder))
	tifFile = df['tif file'].loc[fileNumber]
	abfFile = df['abf file'].loc[fileNumber]
	loadDict = {
		'tif': os.path.join(dataPath, dateFolder, tifFile),
		'abf': os.path.join(dataPath, dateFolder, abfFile),
	}

	#tif, tifHeader, abf = myLoad(lcrData.dataList[fileNumber])
	tif, tifHeader, abf = myLoad(loadDict)

	if tif is None:
		return

	# bingo !!!
	#print(abf.tagTimesSec) # bingo!!! list of tag times in seconds

	print('=== myLoadAndPlot0 fileNumber:', fileNumber)
	print('  tif header is:')
	myPrintDict(tifHeader)

	myPlot(tif, tifHeader, abf, fileNumber=fileNumber, df=df)

def myPrintDict(theDict):
	for k,v in theDict.items():
		print(f'    {k} : {v}')

def run():
	dbFile = 'dual-database.xlsx'

	#
	# load cell database file
	if dbFile.endswith('.csv'):
		df = pd.read_csv(dbFile, header=0, dtype={'ABF File': str})
	elif dbFile.endswith('.xlsx'):
		# stopped working 20201216???
		#df = pd.read_excel(dbFile, header=0, dtype={'ABF File': str})
		#df=pd.read_excel(dbFile, header=0, engine='openpyxl')
		#df=pd.read_excel(dbFile, header=0, engine='xlrd')
		#df=pd.read_excel(open(dbFile,'rb'), header=0)
		df=pd.read_excel(dbFile, header=0)
	else:
		print('error reading dbFile:', dbFile)

	#
	# check we find all data in database
	myPath = os.getcwd()
	dataPath = df['data path'].loc[0]

	numRows = df.shape[0]
	for row in range(numRows):
		folder = df['date folder'].loc[row]
		folder = str(int(folder))
		tif = df['tif file'].loc[row]
		abf = df['abf file'].loc[row]

		tifPath = os.path.join(myPath, dataPath, folder, tif)
		if not os.path.isfile(tifPath):
			print(f'  ERROR: did not find tif at row {row+1}, path:', tifPath)
		abfPath = os.path.join(myPath, dataPath, folder, abf)
		if not os.path.isfile(abfPath):
			print(f'  ERROR: did not find abf at row {row+1}, path:', abfPath)

	#
	# plot the first file in database
	myLoadAndPlot0(14, df)

if __name__ == '__main__':
	run()

	'''
	fileNumber = 3 # in figure panel a 20210115__0001
	#fileNumber = 2 # spike detection
	#fileNumber = 11 # for lcr 20210122__0006
	fileNumber = 16 # new

	test_plot0(fileNumber) # plot image, vm, sum Ca
	'''

	# works
	#spikeTriggeredAverage(fileNumber)

	# [9, 10] is really high freq, hard to analyze Ca
	# [11] ok recording, need to use vM thresh (no dv/dt)
	# good = [2, 3, 4, 8, 11]
	# use this

	# runs spike detectiion on both Ca and Vm
	#lcrDualAnalysis(fileNumber) # show spike detection
