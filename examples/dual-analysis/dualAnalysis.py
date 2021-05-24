#20210203

import os, sys, math

import numpy as np
import pandas as pd

#import scipy.signal
import scipy.optimize
import scipy.stats

import matplotlib
import matplotlib.pyplot as plt
#from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar

import tifffile
import pyabf

import sanpy

def getPathFromRow(df, row):
	# get data path from first row
	firstRow = df.iloc[0]
	dataPath = firstRow['data path']

	# params from selected row
	dfRow = df.iloc[row]
	dateFolder = str(dfRow['date folder']) # is np.int64
	tifFile = dfRow['tif file']
	abfFile = dfRow['abf file']

	tifPath = os.path.join(dataPath, dateFolder, tifFile)
	abfPath = os.path.join(dataPath, dateFolder, abfFile)

	return tifPath, abfPath

def loadDatabase(dbFile='dual-database.xlsx'):
	"""
	Load a database of dual recordings
	"""

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
		return None

	print('  dualAnalysis.py loadDatabase() loaded:', dbFile)

	# append columns to dataframe
	df['tifPath'] = ''
	df['abfPath'] = ''

	#
	# check we find all data in database
	myPath = os.getcwd()
	dataPath = df['data path'].loc[0]

	numRows = df.shape[0]
	for row in range(numRows):
		dateFolder = df['date folder'].loc[row]
		dateFolder = str(int(dateFolder))
		tif = df['tif file'].loc[row]
		abf = df['abf file'].loc[row]

		tifPath = os.path.join(myPath, dataPath, dateFolder, tif)
		if os.path.isfile(tifPath):
			#df['tifPath'].iloc[row] = tifPath
			df.at[row, 'tifPath'] = tifPath
		else:
			print(f'  ERROR: did not find tif at row {row+1}, path: {tifPath}')

		abfPath = os.path.join(myPath, dataPath, dateFolder, abf)
		if os.path.isfile(abfPath):
			#df['abfPath'].iloc[row] = abfPath
			df.at[row, 'abfPath'] = abfPath
		else:
			print(f'  ERROR: did not find abf at row {row+1}, path:', abfPath)

	return df

def makeReport(df):
	"""
	df: pandas dataframe of cell database (from Excel file)
	prints abf path and firstFrameSeconds
	"""
	dictList = []
	for fileIdx in range(len(df)):
		#tmpDict = lcrData.dataList[i]
		tif, tifHeader, abf = myLoad(lcrData.dataList[fileIdx])
		dictList.append(tifHeader)
	#
	df = pd.DataFrame(dictList)
	print(df[['abfPath', 'firstFrameSeconds']])

# todo use database to pull (region, quality, etc)
def makeLcrReport():
	"""
	go through all _clipped_sm.csv and make one big dataframe
	save df as lcr-database.csv

	as we parse, add columns:
		date
		tifFile
	"""
	dfDatabase = loadDatabase()

	basePath = 'dual-data'
	df = None
	numFiles = 0
	for dateFolder in sorted(os.listdir(basePath)):
		if dateFolder.startswith('.'):
			continue
		dateFolderPath = os.path.join(basePath, dateFolder)
		print(dateFolderPath)
		for file in sorted(os.listdir(dateFolderPath)):
			if file.startswith('.'):
				continue
			filePath = os.path.join(dateFolderPath, file)
			# we detect with sparkmaster from (raw .tif OR _clipped.tif)
			isClippedCsv = filePath.endswith('_clipped_sm.csv')
			#isRawCsv = filePath.endswith('_sm.csv')
			if filePath.endswith('_clipped_sm.csv') or filePath.endswith('_sm.csv'):
				print('  ', filePath)

				# find row in main database
				oneTifFile = file.replace('_clipped_sm.csv', '.tif')
				oneTifFile = oneTifFile.replace('_sm.csv', '.tif')
				dfRow = dfDatabase.loc[dfDatabase['tif file'] == oneTifFile]
				if len(dfRow) == 0:
					print('error: did not find tif in main database with oneTifFile:', oneTifFile)
				else:
					# grab (quality, trial, region) from master database
					clippedTif = isClippedCsv
					quality = dfRow['quality'].values[0]
					trial = dfRow['trial'].values[0]
					region = dfRow['region'].values[0]

				# load lcr csv for this one file
				df0 = pd.read_csv(filePath, header=0)

				# append columns
				df0['fileNumber'] = numFiles
				df0['dateFolder'] = str(dateFolder)
				df0['tifFile'] = file.replace('_clipped_sm.csv', '')
				# from master database
				df0['clippedTif'] = clippedTif
				df0['quality'] = quality
				df0['trial'] = trial
				df0['region'] = region

				# append to master df
				if df is None:
					df = df0
				else:
					df = df.append(df0)
					df.reset_index(drop=True)
				numFiles += 1

	# remove all spaces from column names and rename them
	for colIdx, colStr in enumerate(df.columns):
		newColStr = colStr.replace(' ', '')
		#dfSparkMaster.columns[colIdx] = colStr
		df.rename(columns={colStr: newColStr}, inplace=True)
	# remove columns (Analysis, Parameters)
	df=df.drop('Analysis',1)
	df=df.drop('Parameters',1)

	# derive signal mass from Vinogradova et al 2006
	fwhm = df['FWHM']
	fdhm = df['FDHM']
	ampl = df['Ampl.']
	#print(df.columns)
	df_f0 = df['Δ(F/Fo)/Δtmax']
	df['sm ampl'] = fwhm * fdhm * 0.5 * ampl
	df['sm dF'] = fwhm * fdhm * 0.5 * df_f0
	# end dateFolder
	print(len(df), f'LCRs from {numFiles} files.')
	print(df.head())

	#
	# save the database
	if 1:
		saveName = 'lcr-database.csv'
		print('saving saveName:', saveName)
		df.to_csv(saveName)

def new_plotSparkMaster_from_db(fileNumber):

	df = loadDatabase()
	folderStr = str(df['date folder'][fileNumber])
	tifFile = df['tif file'][fileNumber]
	abfFile = df['abf file'][fileNumber]

	tifPath = os.path.join('dual-data', folderStr, tifFile)
	abfPath = os.path.join('dual-data', folderStr, abfFile)

	dr = dualRecord(tifPath, abfPath)
	dr.new_plotSparkMaster()

def spikeClipPlotAndSave():
	"""
	step through database and call plotSpikeClip for a subset of rows (in db)
	"""
	df = loadDatabase()
	n = len(df)
	dataPath = df['data path'][0]
	plotTheseQuality = ['perfect', 'good', 'meh']
	for row in range(n):
		quality = df['quality'][row]
		if quality in plotTheseQuality:
			print('row:', row, quality)

			dateFolder = str(df['date folder'][row])
			tifFile = df['tif file'][row]
			abfFile = df['abf file'][row]
			tifPath = os.path.join(dataPath, dateFolder, tifFile)
			abfPath = os.path.join(dataPath, dateFolder, abfFile)
			dr = dualRecord(tifPath, abfPath)
			# df is backend model loaded from .csv and displayed in table
			fig = dr.plotSpikeClip_df(df, row, myParent=None)

			#dr.findSpikePairs(fileNumber=row, doPlot=False)

	# mergae all those files into one csv
	fig9MergeDatabase()

def new_TifReport():
	"""
	load each tif and print new columns from tifHeader
	"""
	theseCol = ['tif', 'numLines', 'numPixels', 'umLength', 'umPerPixel',
				'totalSeconds', 'secondsPerLine', 'linesPerSecond', 'firstFrameSeconds','xMaxRecordingSec'
				]
	print('new_TifReport()')
	dfReport = pd.DataFrame()

	df = loadDatabase()
	n = len(df)
	#for i in [2]:
	for i in range(n):

		dateFolder = str(df['date folder'][i])
		tifFile = df['tif file'][i]
		abfFile = df['abf file'][i]

		tifFile = os.path.join('dual-data', dateFolder, tifFile)
		abfFile = os.path.join('dual-data', dateFolder, abfFile)

		dr = dualRecord(tifFile, abfFile)

		print(i)
		dr.printHeader()

		#
		# load files, spike detect,
		# blank abf spikes in tif, save _clipped.tif
		if 1:
			quality = df['quality'][i]
			if quality in ['perfect', 'meh', 'good']:
				dr.new_blankAbfSpikesInTif(i)
			else:
				print('NOT BLANKING SPIKES, NOT SAVING _clipped.tif')

		#
		# save _sm.txt with SparrkMaster parameters
		# not used, requires rewrrite of sparkMaster
		if 0:
			smFile = os.path.splitext(tifFile)[0] + '_sm.txt'
			theseParams = ['umPerPixel', 'linesPerSecond', ]
			theFileLines = []
			theFileLines.append(f'tif={dr.tifFile}')
			for param in theseParams:
				paramVal = dr.abfTif.tifHeader[param]
				theFileLines.append(f'{param}={paramVal}\n')
			# criterion=2.5
			# background=2
			theFileLines.append('criterion=2.5\n')
			theFileLines.append('background=2\n')
			print('theFileLines:')
			print(theFileLines)
			print('smFile:', smFile)
			with open(smFile, 'w') as f:
				for L in theFileLines:
					f.writelines(L)

		#
		for col in theseCol:
			colVal = dr.abfTif.tifHeader[col]
			dfReport.loc[i, col] = colVal

	#
	if 1:
		print('saving tif header db into "tifHeader-db.csv"')
		dfReport.to_csv('tifHeader-db.csv')

def fig9MergeDatabase():
	# this is saved when we plot spike clip
	# it has columns for lcr including # lcr per spike (lcrNum)
	folderPath = '/Users/cudmore/Sites/SanPy/examples/dual-analysis/tmpMergedDatabase/analysis'
	dfMaster = None
	for file in os.listdir(folderPath):
		if file.startswith('.'):
			continue
		if file.endswith('_clip.csv'):
			continue
		csvPath = os.path.join(folderPath, file)
		print('csvPath:', csvPath)
		if not os.path.isfile(csvPath):
			continue
		df0 = pd.read_csv(csvPath, header=0)
		if dfMaster is None:
			dfMaster = df0
		else:
			dfMaster = dfMaster.append(df0, ignore_index=True)

	# save dfMaster
	savePath = '/Users/cudmore/Sites/SanPy/examples/dual-analysis/combined-sanpy-lcr-db.csv'
	print('saving merged database to', savePath)
	dfMaster.to_csv(savePath)

class dualRecord:
	def __init__(self, tifFile, abfFile):

		self.tifFile = tifFile # path
		self.abfFile = abfFile

		self.abf = None # pyabf object
		self.dfSparkMaster = None # df from output of SparkMaster saved as a csv

		# spike analysis (ba is bAnalysis object)
		self.baAbf = None # see: loadAndAnalyzeAbf
		self.baTif = None # see: loadAndAnalyzeTif

		self.load()
		self.loadSparkMaster()

	def new_blankAbfSpikesInTif(self, fileNumber):
		"""
		blank regions of linescan .tif kymograph that corespond to
		spikes in the abf file

		Also, shorten linescan tif to duration of ephys recording

		save _clipped.tif

		Parameters:
			clip_sec: Seconds to blank after abf spike peak
		"""

		print('new_blankAbfSpikesInTif()')

		df = loadDatabase()

		# analyze abf
		#fileNumber = 4
		self._loadAnalyzeAbf_from_df(df, fileNumber)

		firstFrameSeconds = self.abfTif.tifHeader['firstFrameSeconds']
		secondsPerLine = self.abfTif.tifHeader['secondsPerLine']
		xMaxRecordingSec = self.abfTif.tifHeader['xMaxRecordingSec']

		clippedTif = self.abfTif.tif.copy()
		print('  ', clippedTif.shape)
		print('  ', self.abfTif.sweepX[0:3])

		# spark master
		#tPosSec = self.dfSparkMaster['t-pos'] # seconds in image

		clip_sec = 0.2 #0.17 # remove from spike peak out to this window
		abfPeakSec = self.baAbf.getStat('peakSec')
		for idx,peakSecAbf in enumerate(abfPeakSec):
			peakSecTif = peakSecAbf - firstFrameSeconds # !!!
			startClip_sec = peakSecTif
			stopClip_sec = startClip_sec + clip_sec

			#print('  removing abf spike', idx, 'startClip_sec:', startClip_sec, 'stopClip_sec:', stopClip_sec)

			startClip_bins = startClip_sec / secondsPerLine
			stopClip_bins = stopClip_sec / secondsPerLine

			startClip_bins = round(startClip_bins)
			stopClip_bins = round(stopClip_bins)

			if startClip_bins<0 or stopClip_bins>clippedTif.shape[1]-1:
				print('  error at spike:', idx, 'startClip_bins:', startClip_bins, 'stopClip_bins:', stopClip_bins)
			#print('idx:', idx, 'startClip_bins:', startClip_bins, 'stopClip_bins:', stopClip_bins)

			# clip spike out of image
			clippedTif[:,startClip_bins:stopClip_bins] = 0

		#
		# reduce tif line scans to match time of abf ephys recoring
		# todo: will be error if abf ephys recording is LONGER than imaging
		endTif_bins = (xMaxRecordingSec-firstFrameSeconds) / secondsPerLine
		endTif_bins = math.floor(endTif_bins)
		print('  removing line scans after endTif_bins:', endTif_bins, 'xMaxRecordingSec:', xMaxRecordingSec)
		clippedTif[:,endTif_bins:clippedTif.shape[1]] = 0

		#
		# plot
		fig, axs = plt.subplots(2, 1, sharex=True)
		tif = self.abfTif.tif
		dfMean = np.nanmean(tif)
		df_d0 = (tif- dfMean) / dfMean
		axs[0].imshow(df_d0, aspect='auto')

		dfMean = np.nanmean(clippedTif)
		df_d0_2 = (clippedTif- dfMean) / dfMean
		axs[1].imshow(df_d0_2, aspect='auto')

		#
		# rotate back into original orientation (bAbfText rotates tif on load)
		clippedTif = np.rot90(clippedTif, k=3)

		#
		# save
		tmpPath = os.path.splitext(self.tifFile)[0]
		tmpPath += '_clipped.tif'
		print('  saving:', tmpPath)
		tifffile.imsave(tmpPath, clippedTif)


	def plotImage(self, ax, fig, cbar_ax, region=None, row=None):
		print('!!!!!!!!!!!!!!!! dualAnalysis.plotImage() is plotting (f - f0) / f0')
		# make proper dF/f_0, using mean as f_0

		# df/f0
		tifData = self.abfTif.tif
		f0 = np.nanmean(tifData)
		print('  **********  raw mean f0:', f0, 'min:', np.nanmin(tifData), 'max:', np.nanmax(tifData))
		print('                         dtype:', tifData.dtype, 'shape:', tifData.shape)
		if region == 'superior':
			#f0 = f0
			pass
		elif region == 'inferior' and row==11:
			# 1.2 looked ok, making more dim
			tmpMult = 1.1
			if tmpMult > 1:
				print('     inferior f0 = 3797 *', tmpMult, '(tmpMult)')
				f0 = 3797 * tmpMult # background is 2 * superioior
		print('          using f0:', f0, 'region:', region)

		df_f0 = (tifData - f0) / f0
		# raw
		#df_f0 = self.abfTif.tif
		print('    mean f0 is', f0, 'df_f0 min:', np.nanmin(df_f0), 'df_f0 max:', np.nanmax(df_f0))

		cmap = 'plasma'

		firstFrameSeconds = self.abfTif.tifHeader['firstFrameSeconds']
		xMin = firstFrameSeconds
		xMax = firstFrameSeconds + self.abfTif.sweepX[-1]
		yMin = 0
		yMax = self.abfTif.tifHeader['umLength'] #57.176
		extent = [xMin, xMax, yMin, yMax] # flipped y

		vmin = 0
		vmax = 10 #15 #6
		print('     forcing scalebar to vmin:', vmin, 'vmax:', vmax)
		plottedImage = ax.imshow(df_f0, cmap=cmap,
						#vmin=vmin,
						#vmax=vmax,
						extent=extent, aspect='auto')

		ax.spines['left'].set_visible(False)
		ax.spines['top'].set_visible(False)
		ax.spines['right'].set_visible(False)
		ax.spines['bottom'].set_visible(False)

		ax.set_xticks([], minor=False)
		ax.set_xticks([], minor=True)
		#ax.set_yticks([], minor=False)
		#ax.set_yticks([], minor=True)

		#fig.colorbar(plottedImage, cax=cbar_ax, shrink=0.2)
		#fig.colorbar(plottedImage,fraction=0.046, pad=0.04)
		fig.colorbar(plottedImage,fraction=0.02, pad=0.04)
		#cax = fig.add_axes([0.9, 0.5, 0.03, 0.38]) # [x, y, w, h]
		#plt.colorbar(im0,fraction=0.046, pad=0.04, cax=axs[2])
		#plt.colorbar(im0,cax=cax)

	def plotLcrHist(self, ax):
		tifFirstFrameSeconds = self.abfTif.tifHeader['firstFrameSeconds']
		tifSecondsPerLine = self.abfTif.tifHeader['secondsPerLine']
		tifTotalSeconds = self.abfTif.tifHeader['totalSeconds']
		print('  first frame of the image wrt pClamp abf as at', tifFirstFrameSeconds)

		xLineScanSum = self.abfTif.sweepX + tifFirstFrameSeconds
		yLineScanSum = self.abfTif.sweepY

		# now stripping leading spaces in SparkMaster columns (see loadSparkMaster)
		# remember: when traversing rows, t-pos is out of order w.r.t. time
		xSmStatStr = 't-pos' # t-pos is in seconds?
		xSmStat = self.dfSparkMaster[xSmStatStr]
		# shift wrt tifFirstFrameSeconds
		xSmStatSec = [x+tifFirstFrameSeconds for x in xSmStat]

		yDoThisSmStat = 'FWHM' # 'Ampl.' # or 'FWHM'
		ySmStatStr = yDoThisSmStat
		ySmStat = self.dfSparkMaster[ySmStatStr]

		yDoThisSmStat2 = 'Ampl.' # 'Ampl.' # or 'FWHM'
		ySmStatStr2 = yDoThisSmStat2
		ySmStat2 = self.dfSparkMaster[ySmStatStr2]

		tPos_orig = self.dfSparkMaster['t-pos']
		tPos_offset = tPos_orig + tifFirstFrameSeconds
		tPos_bin = [round(x/tifSecondsPerLine) for x in tPos_orig] # t-pos of each LCR as bin # (into tif)
		#print('tPos_bin:', tPos_bin)

		xPos = self.dfSparkMaster['x-pos'] # pixel along line scan???

		#
		# bin sparkmaster time and count the number of LCR ROIs in a bin
		tifBins_ms = 50 #10
		print('  tifBins_ms:', tifBins_ms)
		tifBins_sec = tifBins_ms / 1000
		# important to consider wrt tifBins_sec
		xNumBins = math.floor(tifTotalSeconds / tifBins_sec)
		print('tifBins_sec:', tifBins_sec, 'xNumBins:', xNumBins, 'tifSecondsPerLine:', tifSecondsPerLine)
		# make new x-axis with bins
		xBins = [tifFirstFrameSeconds+(x*tifBins_sec) for x in range(xNumBins)]

		# if weights is None, will count LCR in each bin
		# if weight=ampl, will sum ampl for each LCRR in each bin
		weights = None
		weights = self.dfSparkMaster['Ampl.']

		n, bins, patches = ax.hist(tPos_offset, weights=weights,
									bins=xBins,
									facecolor='0.6',
									#histtype='step',
									#color = "k",
									ec="k"
									)

		ax.spines['left'].set_visible(False)
		ax.spines['top'].set_visible(False)
		ax.spines['right'].set_visible(False)
		#ax.spines['bottom'].set_visible(False)

	def plotClips(self, fileNumber=None, region=None, axs=None):

		traceColor = 'k'
		if region == 'superior':
			traceColor = 'r'
		elif region == 'inferior':
			traceColor = 'b'

		# need to get these from database df
		#region = None
		cellNumber = None
		trial = None
		#fileNumber = None

		fig = None
		if axs is None:
			'''
			fig, axs = plt.subplots(1, 1)
			fig.set_size_inches(4, 1.5)
			'''

			figSize =(4,1.5) # inches
			fig = plt.figure(figsize=figSize, constrained_layout=True)
			widths = [2]
			heights = [1, 0.5]
			gridSpec = fig.add_gridspec(ncols=1, nrows=2, width_ratios=widths, height_ratios=heights)

			fig, axs = plt.subplots(nrows=2, ncols=1, sharex=True, sharey=False,
                               gridspec_kw={'height_ratios': [2, 1]},
                               figsize=figSize)

			fig.suptitle(f'{fileNumber} {region}')

			# plot vm
			'''
			row = 0
			col = 0
			axVm = fig.add_subplot(gridSpec[row, col])
			'''
			axVm = axs[0]
			axVm.xaxis.set_visible(False)
			# plot lcr
			'''
			row = 1
			col = 0
			axLcr = fig.add_subplot(gridSpec[row, col])
			'''
			axLcr = axs[1]
			axLcr.xaxis.set_visible(False)


		spikeClipWidth_ms = 400
		spikeClipWidth_sec = spikeClipWidth_ms / 1000

		theseTime_sec = self.baAbf.getStat('thresholdSec') # spike times from abf

		# theseTime_sec is spike time in abf, need to shift it for imaging
		firstFrameSeconds = self.abfTif.tifHeader['firstFrameSeconds']
		caTheseTime_sec = [x-firstFrameSeconds for x in theseTime_sec]

		thresholdSec0, peakSec0 = self.baTif.getStat('thresholdSec', 'peakSec')
		thresholdSec1, peakSec1 = self.baAbf.getStat('thresholdSec', 'peakSec')

		#
		# vm plot
		abfSpikeClips_x2, abfSpikeClips = self.baAbf.makeSpikeClips(spikeClipWidth_ms, theseTime_sec=theseTime_sec)
		for idx, sec in enumerate(thresholdSec1):
			try:
				oneSpikeClips_x2 = abfSpikeClips_x2[idx]
				oneSpikeClips = abfSpikeClips[idx]
				axVm.plot(oneSpikeClips_x2, oneSpikeClips, '-', color=traceColor)

				'''
				if idx == 0:
					currentSpikeClipPlot, = axVm.plot(oneSpikeClips_x2, oneSpikeClips, '-k')
				'''

			except (IndexError) as e:
				print('error: plotSpikeClip() vm no spike', idx)

		axVm.spines['left'].set_visible(False)
		axVm.spines['top'].set_visible(False)
		axVm.spines['right'].set_visible(False)
		axVm.spines['bottom'].set_visible(False)
		axVm.xaxis.set_visible(False)
		axVm.yaxis.set_visible(False)
		print('xxx set_ylim -6 20')
		axVm.set_ylim(-60, 20)

		#
		# sparkmaster
		# bin SM LCR before each spike
		if self.dfSparkMaster is not None:
			halWidth_ms_int = int(spikeClipWidth_ms/2)
			# this yPreClipSparkMasterBins is misleading
			# generate a y for EACH spike and take avg/#spike to get something more like a probability
			#yPreClipSparkMasterBins2 = [0] * halWidth_ms_int +1 for LCR -1 for none
			yPreClipSparkMasterBins = [0] * halWidth_ms_int # for count for each ms across all spikes
			xPreClipSparkMasterBins = [-x for x in range(halWidth_ms_int)] # -0, -1, -2

			# 2d list of spark-master bins per spike
			yPreClipSparkMasterBins_2d = []

			#xPreClipSparkMasterBins.reverse() # -3, -2, -1

			# 2d ndaray to get mean of each bin (column)
			# this is like a probability
			numSpikes = len(caTheseTime_sec)
			yPreClipPerSpike = np.zeros((numSpikes,halWidth_ms_int))

			# the time of each LCR (w.r.t. imaging)
			tPos = self.dfSparkMaster['t-pos'].values
			#print(type(tPos), tPos)
			# caTheseTime_sec is based on abf 'thresholdSec'
			for idx, smSec in enumerate(caTheseTime_sec):
				# new row to hold lcr hist for this one spike (idx)
				yPreClipSparkMasterBins_2d.append([0] * halWidth_ms_int)

				smStartSec = smSec-(spikeClipWidth_sec/2)
				smStopSec = smSec #+spikeClipWidth_sec
				smHits_pnts = np.argwhere((tPos>smStartSec) & (tPos<smStopSec))
				#print('  tPos[smHits_pnts]:', tPos[smHits_pnts])
				smHits_ms = (smSec*1000) - (tPos[smHits_pnts]*1000)
				# - because we want BEFORE spike and with int() we bin for manual hist
				smHits_ms = [int(-x) for x in smHits_ms]
				for smHitms in smHits_ms:
					# todo: make sure -smHitms is good index
					try:
						yPreClipSparkMasterBins[-smHitms] += 1 # add one to bin
						yPreClipPerSpike[idx][-smHitms] += 1
						# 2d list to keep track of lcr per spike
						yPreClipSparkMasterBins_2d[idx][-smHitms] += 1
					except (IndexError) as e:
						print('    ERROR: spike', idx, 'had error with -smHitms:', -smHitms)

				print('  spike', idx, 'smSec:', smSec, 'has', len(smHits_pnts), 'sm pnts before it, smHits_ms:', smHits_ms)
				#print('    20ms before spike', xPreClipSparkMasterBins[0:20])
				#print('    20ms before spike', yPreClipSparkMasterBins[0:20])

				# fit line and put in self.baAbf spikeDict
				x_values = xPreClipSparkMasterBins # same for every spikes
				y_values = yPreClipSparkMasterBins # starts at all 0 and accumulates lcr (could be 0 lcr !!!)
				resultObj = scipy.stats.linregress(x_values, y_values)
				# there is also resultObj.rvalue (not need to run pearsons)
				print('spike', idx, 'region:', region, 'resultObj slope:', resultObj.slope, 'p:', resultObj.pvalue)
				self.baAbf.spikeDict[idx]['lcrSlope'] = resultObj.slope
				self.baAbf.spikeDict[idx]['lcrNum'] = len(smHits_pnts) # number of lcr before spike
				self.baAbf.spikeDict[idx]['region'] = region
				self.baAbf.spikeDict[idx]['cell number'] = cellNumber
				self.baAbf.spikeDict[idx]['trial'] = trial

			#
			# 20210311
			# save the merged SanPy/clr anaysis
			# this is for generating figure 9
			if 0:
				tmpSavefile = '/Users/cudmore/Sites/SanPy/examples/dual-analysis/tmpMergedDatabase'
				print('self.baAbf.file:', self.baAbf.file)
				tmpAbfPath, tmpAbfFile = os.path.split(self.baAbf.file)
				tmpAbfFile, tmpExt = os.path.splitext(tmpAbfFile)
				tmpAbfFile += '.csv'
				tmpSavefile = os.path.join(tmpSavefile, tmpAbfFile)
				print('saving fig9 merged database to tmpSavefile:', tmpSavefile)
				self.baAbf.saveReport(tmpSavefile, saveExcel=False, alsoSaveTxt=True)

			# 2d, take mean of col (# lcr in each ms across all spikes)
			#print('yPreClipPerSpike:', yPreClipPerSpike)
			yPreClipSpikeMean = yPreClipPerSpike.mean(axis=0)
			#print('yPreClipSpikeMean[0:20]:', yPreClipSpikeMean[0:20])

			# compare the slope for each spike to its earlyDiastolicDurationRate
			# test significance
			eddRate, lcrSlope = self.baAbf.getStat('earlyDiastolicDurationRate', 'lcrSlope') #returns list []
			eddRate = np.array(eddRate)
			lcrSlope = np.array(lcrSlope)
			notNaNIdx = ~np.isnan(eddRate) & ~np.isnan(lcrSlope) # strip nan
			#print('notNaNIdx:', notNaNIdx)
			rTmp, pTmp = scipy.stats.pearsonr(eddRate[notNaNIdx], lcrSlope[notNaNIdx])
			'''
			print('  test eddRate vs lcrSlope pearsonsr r:', rTmp, 'p:', pTmp)
			if 0:
				# plot slope versus early diastolic duration rate
				tmpFig, tmpAxs = plt.subplots(1, 1, sharex=False)
				tmpAxs = [tmpAxs]
				tmpAxs[0].plot(eddRate, lcrSlope)
				plt.show()
			'''

			#
			# fit a line to all spike
			# see https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.linregress.html
			def lineFitFunction(x, a, b, c):
				return a * x + b
			x_values = xPreClipSparkMasterBins
			y_values = yPreClipSpikeMean
			# popt: [0.0002 0.0418 1.    ]
			popt, pcov = scipy.optimize.curve_fit(lineFitFunction, x_values, y_values)
			#print('slope*x + intercept ... a * x + b')
			#print('popt:', popt)
			#print('pcov:', pcov)
			xFit = np.linspace(min(x_values), max(x_values), 1000)
			yFit = lineFitFunction(xFit, *popt)
			# plot(x_line, y_line)
			resultObj = scipy.stats.linregress(x_values, y_values)
			print('  all spikes resultObj slope of # lcr approacing spike:', resultObj.slope, 'p:', resultObj.pvalue)

			# copy/paste to excel
			tifStr = os.path.split(self.tifFile)[1]
			print(f'index\ttif\tregion\tnSpikes\tslope\tp\tr\tp')
			print(f'{fileNumber}\t{tifStr}\t{region}\t{numSpikes}\t{round(resultObj.slope,5)}\t{round(resultObj.pvalue,5)}\t{round(rTmp,5)}\t{round(pTmp,5)}')

			#
			# use axLcr instead
			#secondAxs1 = axs.twinx()
			#secondAxs1.spines['right'].set_visible(False)
			#secondAxs1.spines['top'].set_visible(False)
			#secondAxs1.plot(xPreClipSparkMasterBins, yPreClipSparkMasterBins, '.b')
			# was this
			'''
			yPreClipSparkMasterBins = [x if x>0 else np.nan for x in yPreClipSparkMasterBins]
			secondAxs1.stem(xPreClipSparkMasterBins, yPreClipSparkMasterBins,
						linefmt='.b',
						markerfmt=' ', # use space ' ' and not None or ''
						basefmt=' ')
			'''
			# now this
			yPreClipSpikeMean = [x if x>0 else np.nan for x in yPreClipSpikeMean]
			axLcr.stem(xPreClipSparkMasterBins, yPreClipSpikeMean,
						#linefmt='grey',
						linefmt=traceColor,
						markerfmt=' ', # use space ' ' and not None or ''
						basefmt=' ')
			# before adding color r/b sup/inf for manuscript
			#axLcr.plot(xFit, yFit, 'b', linewidth=2.5)
			axLcr.plot(xFit, yFit, 'k', linewidth=2.5)
			#
			axLcr.set_ylabel('Prob LCR')
			axLcr.spines['left'].set_visible(False)
			axLcr.spines['top'].set_visible(False)
			axLcr.spines['right'].set_visible(False)
			axLcr.spines['bottom'].set_visible(False)
			axLcr.xaxis.set_visible(False)
			axLcr.yaxis.set_visible(False)

			print('xxx axLcr set_ylim 0 .2')
			axLcr.set_ylim(0, 0.1)
		#
		return fig

	def plotFigure9(self, region=None, row=''):
		"""
		for figure 9
		plot dF/f_o, add image scale bar,
		plot lcr bins
		"""

		figSize =(6,2) # inches
		fig = plt.figure(figsize=figSize, constrained_layout=True)
		widths = [2, 0.25]
		heights = [1, 0.2]
		gridSpec = fig.add_gridspec(ncols=2, nrows=2, width_ratios=widths, height_ratios=heights)

		fig.suptitle(region + ' ' + str(row))

		# plot image
		row = 0
		col = 0
		axImage = fig.add_subplot(gridSpec[row, col])

		# remove x axis
		axImage.xaxis.set_visible(False)
		axImage.yaxis.set_visible(False)

		# colorbar for image
		#cbar_ax = fig.add_axes([0.85, 0.15, 0.05, 0.7])
		#figColorBar, axsColorBar = plt.subplots(1, 1, figsize=(1,2))
		'''
		row = 0
		col = 1
		axColorBar = fig.add_subplot(gridSpec[row, col])
		'''

		#
		#self.plotImage(axImage, fig, axsColorBar)
		self.plotImage(axImage, fig, None, region=region, row=row)
		axImage.xaxis.set_visible(False)
		axImage.yaxis.set_visible(False)

		# twin image x and overlay Vm
		axImageRight = axImage.twinx()  # instantiate a second axes that shares the same x-axis
		sweepX = self.abf.sweepX
		sweepY = self.abf.sweepY
		axImageRight.plot(sweepX, sweepY, '-w', linewidth=0.5)
		axImageRight.set_xticks([], minor=False)
		axImageRight.set_xticks([], minor=True)
		#axImageRight.set_yticks([], minor=False)
		#axImageRight.set_yticks([], minor=True)
		axImageRight.spines['left'].set_visible(False)
		axImageRight.spines['top'].set_visible(False)
		axImageRight.spines['right'].set_visible(False)
		axImageRight.spines['bottom'].set_visible(False)
		axImageRight.xaxis.set_visible(False)
		axImageRight.yaxis.set_visible(False)

		#plt.axis('off')
		'''
		plt.tick_params(
			axis='x',          # changes apply to the x-axis
			which='both',      # both major and minor ticks are affected
			left=False,      # ticks along the bottom edge are off
			right=False,      # ticks along the bottom edge are off
			bottom=False,      # ticks along the bottom edge are off
			top=False,         # ticks along the top edge are off
			labelbottom=False) # labels along the bottom edge are off
		'''

		# plot lcr hist
		row = 1
		col = 0
		axLcr = fig.add_subplot(gridSpec[row, col])
		self.plotLcrHist(ax=axLcr)
		axLcr.xaxis.set_visible(False)
		axLcr.yaxis.set_visible(False)

		# join x-axis between image and lcr
		axImage.get_shared_x_axes().join(axImage, axLcr)

		# set_xlim to range of e-phys (shorter than image acq)
		# using 2021_01_29_0006
		#axLcr.set_ylim(0, 12)
		#axLcr.set_xlim(7.0, 8)

		# 2nd argument needs to be canvas widget we are within
		#fig.canvas.toolbar_visible = False
		#win = fig.canvas.window()
		#win = fig.canvas.manager.window
		#toolbar = NavigationToolbar(fig.canvas, win)

		#
		#plt.show()
		return fig, axImage, axLcr

	def new_plotSparkMaster(self, region=None):
		"""
		using csv output of SparkMaster result with one LCR per line

		parameters:
			tifBins_ms: how to bin SM LCR ROIs
		"""

		def lcrHist_key_press_event(event):
			#print('press', event.key)
			global spikeNumber # needed because we are assigning new value
			#print('lcrHist_key_press_event() event.key:', event.key)
			sys.stdout.flush()
			if event.key in ['.', 'right']:
				# next
				spikeNumber += 1
				if spikeNumber > self.baAbf.numSpikes-1:
					print('at last spike')
					spikeNumber -= 1
					pass
				else:
					lcrHist_Zoom_Spike(spikeNumber)

			elif event.key in [',', 'left']:
				# previous
				spikeNumber -= 1
				if spikeNumber < 0:
					spikeNumber = 0
					return
				else:
					lcrHist_Zoom_Spike(spikeNumber)

			elif event.key == 'escape':
				# reset x axis
				startSeconds = 0
				stopSeconds = self.abf.sweepX[-1]
				axRight2.set_xlim(startSeconds, stopSeconds)
				fig.canvas.draw()

		def lcrHist_Zoom_Spike(n):
			print('lcrHist_Zoom_Spike() n:', n, 'of', self.baAbf.numSpikes-1)
			# get time of spike (n, n-1)
			vmThresholdSecs, vmPeakSeconds = self.baAbf.getStat('thresholdSec', 'peakSec')
			if n == 0:
				startSeconds = 0
			else:
				startSeconds = vmPeakSeconds[n-1]
			stopSeconds = vmPeakSeconds[n]
			stopSeconds += 0.02

			axRight2.set_xlim(startSeconds, stopSeconds)
			axRight2.set_ylim(0, 5)
			fig.canvas.draw()

		def onpick2(event):
			# event is type MouseEvent
			print('onpick2 line:', event.xdata, event.ydata)

		# main fn()
		global spikeNumber # needed because we will assign +/- in callback
		spikeNumber = 0 # used in callback for phase plot
		print('new_plotSparkMaster()')
		if self.dfSparkMaster is None:
			print('  error: new_plotSparkMaster() did not find self.dfSparkMaster')

		#print(self.dfSparkMaster.head)
		print('  sm columns:', self.dfSparkMaster.columns)

		tifFirstFrameSeconds = self.abfTif.tifHeader['firstFrameSeconds']
		tifSecondsPerLine = self.abfTif.tifHeader['secondsPerLine']
		tifTotalSeconds = self.abfTif.tifHeader['totalSeconds']
		print('  first frame of the image wrt pClamp abf as at', tifFirstFrameSeconds)

		xLineScanSum = self.abfTif.sweepX + tifFirstFrameSeconds
		yLineScanSum = self.abfTif.sweepY

		# now stripping leading spaces in SparkMaster columns (see loadSparkMaster)
		# remember: when traversing rows, t-pos is out of order w.r.t. time
		xSmStatStr = 't-pos' # t-pos is in seconds?
		xSmStat = self.dfSparkMaster[xSmStatStr]
		# shift wrt tifFirstFrameSeconds
		xSmStatSec = [x+tifFirstFrameSeconds for x in xSmStat]

		yDoThisSmStat = 'FWHM' # 'Ampl.' # or 'FWHM'
		ySmStatStr = yDoThisSmStat
		ySmStat = self.dfSparkMaster[ySmStatStr]

		yDoThisSmStat2 = 'Ampl.' # 'Ampl.' # or 'FWHM'
		ySmStatStr2 = yDoThisSmStat2
		ySmStat2 = self.dfSparkMaster[ySmStatStr2]

		tPos_orig = self.dfSparkMaster['t-pos']
		tPos_offset = tPos_orig + tifFirstFrameSeconds
		tPos_bin = [round(x/tifSecondsPerLine) for x in tPos_orig] # t-pos of each LCR as bin # (into tif)
		#print('tPos_bin:', tPos_bin)

		xPos = self.dfSparkMaster['x-pos'] # pixel along line scan???

		#
		# bin sparkmaster time and count the number of LCR ROIs in a bin
		tifBins_ms = 50 #10
		print('  tifBins_ms:', tifBins_ms)
		tifBins_sec = tifBins_ms / 1000
		# important to consider wrt tifBins_sec
		xNumBins = math.floor(tifTotalSeconds / tifBins_sec)
		print('tifBins_sec:', tifBins_sec, 'xNumBins:', xNumBins, 'tifSecondsPerLine:', tifSecondsPerLine)
		# make new x-axis with bins
		xBins = [tifFirstFrameSeconds+(x*tifBins_sec) for x in range(xNumBins)]

		# if weights is None, will count LCR in each bin
		# if weight=ampl, will sum ampl for each LCRR in each bin
		weights = None
		weights = self.dfSparkMaster['Ampl.']

		# plotted below
		#myHist,myBins = np.histogram(tPos_offset, weights=weights,
		#							bins=xBins)

		#
		# plot
		numPanels = 4
		fig, axs = plt.subplots(numPanels, 1, sharex=True)
		if numPanels == 1:
			axs = [axs]
		fig.canvas.mpl_connect('key_press_event', lcrHist_key_press_event)

		titleStr = str(region)
		titleStr += ' ' + os.path.split(self.abfTif.tifHeader['tif'])[1]
		titleStr += ' tifBins_ms:' + str(tifBins_ms)
		fig.suptitle(titleStr)

		# ephys Vm
		xVm = self.abf.sweepX
		yVm = self.abf.sweepY
		axs[0].plot(xVm, yVm, 'k')
		axs[0].set_ylabel('Vm (mV)')

		# sparkmaster over Vm
		axRight1 = axs[0].twinx()  # instantiate a second axes that shares the same x-axis
		axRight1.plot(xSmStatSec, ySmStat, '.b')
		#axRight1.set_xlabel(xStatStr)
		axRight1.set_ylabel('SM ' + ySmStatStr)

		#
		# sum of each line scan
		xLineScan = self.abfTif.sweepX
		yLineScan = self.abfTif.sweepY
		axs[1].plot(xLineScanSum, yLineScan, 'r')
		axs[1].set_ylabel('Ca Line Scan Sum')

		# sparkmaster over Ca Line Scan Sum
		axRight1 = axs[1].twinx()  # instantiate a second axes that shares the same x-axis
		axRight1.plot(xSmStatSec, ySmStat2, '.b')
		#axRight1.set_xlabel(xStatStr)
		axRight1.set_ylabel('SM ' + ySmStatStr2)

		#
		axs[2].plot(xVm, yVm, '-k')
		axs[2].set_ylabel('Vm (mV)')

		axRight2 = axs[2].twinx()  # instantiate a second axes that shares the same x-axis
		fig.canvas.mpl_connect('button_press_event', onpick2)
		#axRight2.plot(xLineScanSum, yLineScanSum, '-r')
		n, bins, patches = axRight2.hist(tPos_offset, weights=weights,
									bins=xBins,
									facecolor='k', histtype='step')
		if weights is None:
			axRight2.set_ylabel('SM LCR Count')
		else:
			axRight2.set_ylabel('SM LCR Weight (amp)')
		# once we mask out Ca++ in response to spikes
		# we do not need log plot !!!
		#axRight2.set_yscale('log')

		#
		# plot tif image overlaid with position of LCRs
		if 1:
			firstFrameSeconds = self.abfTif.tifHeader['firstFrameSeconds']
			xMin = firstFrameSeconds
			xMax = firstFrameSeconds + self.abfTif.sweepX[-1]
			yMin = 0
			yMax = self.abfTif.tifHeader['umLength'] #57.176
			#extent = [xMin, xMaxImage, yMax, yMin] # flipped y
			extent = [xMin, xMax, yMin, yMax] # flipped y
			dfMean = np.nanmean(self.abfTif.tif)
			df_d0 = (self.abfTif.tif- dfMean) / dfMean
			axs[3].imshow(df_d0, extent=extent, aspect='auto')
			axs[3].spines['right'].set_visible(False)
			axs[3].spines['top'].set_visible(False)

			axRight3 = axs[3].twinx()  # instantiate a second axes that shares the same x-axis
			axRight3.plot(tPos_offset, xPos, '.r')

		# 2nd plot
		# correllation between LCR FWHM and Amplitude is really weak
		# this is disturbing !!!
		'''
		fig2, axs2 = plt.subplots(1, 1, sharex=True)
		axs2 = [axs2]
		axs2[0].plot(ySmStat, ySmStat2, '.k')
		axs2[0].set_xlabel(ySmStatStr)
		axs2[0].set_ylabel(ySmStatStr2)
		'''

		# sparkmaster
		'''
		axs[1].plot(xStat, yStat, 'ok')
		axs[1].set_xlabel(xStatStr)
		axs[1].set_ylabel(yStatStr)
		'''
		return fig

	def load(self):
		"""
		"""
		#
		# check they exist
		numError = 0
		if not os.path.isfile(self.tifFile):
			print('ERROR: dualRecord.load() did not find tifFile:', self.tifFile)
			numError += 1
		if not os.path.isfile(self.abfFile):
			print('ERROR: dualRecord.load() did not find abfFile:', self.abfFile)
			numError += 1
		if numError>0:
			return None

		#
		# tif
		self.abfTif = sanpy.bAbfText(self.tifFile)

		#
		# abf
		self.abf = pyabf.ABF(self.abfFile)

		tagTimesSec = self.abf.tagTimesSec
		firstFrameSeconds = tagTimesSec[0]
		self.abfTif.tifHeader['firstFrameSeconds'] = firstFrameSeconds

		xMaxRecordingSec = self.abf.sweepX[-1] # seconds
		self.abfTif.tifHeader['xMaxRecordingSec'] = xMaxRecordingSec

	def _old_loadLineScanHeader(self):
		"""
		path: full path to tif

		we will load and parse coresponding .txt file

		returns dict:
			numPixels:
			umLength:
			umPerPixel:
			totalSeconds:
		"""
		path = self.tifFile
		# "X Dimension"	"138, 0.0 - 57.176 [um], 0.414 [um/pixel]"
		# "T Dimension"	"1, 0.000 - 35.496 [s], Interval FreeRun"
		# "Image Size(Unit Converted)"	"57.176 [um] * 35500.000 [ms]"
		txtFile = os.path.splitext(path)[0] + '.txt'

		if not os.path.isfile(txtFile):
			print('ERROR: dualRecord.loadLineScanHeader() did not find file:', txtFile)
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

	def _printDict(self, theDict):
		for k,v in theDict.items():
			print(f'    {k} : {v}')

	def printHeader(self):
		self._printDict(self.abfTif.tifHeader)

	def plotTagTimes(self):
		"""
		analyze the timing of all tags
		tags are scan start from fv3000
		"""
		#fileIdx = 3
		#tif, tifHeader, abf = myLoad(lcrData.dataList[fileIdx])
		tif = self.abfTif.tif
		tifHeader = self.abfTif.tifHeader
		abf = self.abf

		tagTimesSec = abf.tagTimesSec # [0.516, 0.5415, 0.567, 0.5925, 0.618, 0.6435, 0.669, 0.6945

		# looking into other tags
		tagTimesMin = abf.tagTimesMin
		tagComments = abf.tagComments
		tagSweeps = abf.tagSweeps # tagSweeps = [0.020640000000000002, 0.02166, 0.02268, 0.023700000000000002, 0.02472, 0.02574, 0.026760000000000003,
		# not available?
		#nTagType = abf.nTagType # is 2 for 'external'

		# not available
		# seems to be fSynchTimeUnit = 100.0
		#fSynchTimeUnit = abf.fSynchTimeUnit

		'''
		Later we will populate the times and sweeps (human-understandable units)
		by multiplying the lTagTime by fSynchTimeUnit from the protocol section.
		'''
		# not available
		# like lTagTime = [0.516, 0.5415, 0.567, 0.5925, 0.618, 0.6435, 0.669
		#lTagTime = abf.lTagTime

		#self._printDict(tifHeader)

		print('number of tags:', len(tagTimesSec))
		tagTimeDiff = np.diff(tagTimesSec)

		if 1:
			fig, axs = plt.subplots(2, 1, sharex=False)
			titleStr = os.path.split(tifHeader['tif'])[1]
			fig.suptitle(titleStr)

			n, bins, patches = axs[0].hist(tagTimeDiff, 100, density=False, facecolor='k', alpha=0.75)
			#axs[1].plot(tagTimeDiff)
			#axs[1].plot(nTagType)

			yPlotPos = 0
			yTagTimesSec = [yPlotPos for x in tagTimesSec]

			axs[1].plot(abf.sweepX, abf.sweepY, '.k')
			axs[1].plot(tagTimesSec, yTagTimesSec, '.r')

			#plt.show()

		#print(abf.headerText)

	def loadAndAnalyzeAbf(self, dVthresholdPos=30, minSpikeVm=-20):

		if dVthresholdPos is None and minSpikeVm is not None:
			# to allow pure mV detection
			pass
		else:
			dVthresholdPos = 20
		if minSpikeVm is None:
			minSpikeVm = -20

		#path = '/Users/cudmore/data/dual-lcr/20210115/data/21115002.abf'
		path = self.abfFile

		ba = sanpy.bAnalysis(path)
		#ba.getDerivative()

		#dVthresholdPos = 30
		#minSpikeVm = -20
		'''
		halfWidthWindow_ms = 100 # was 20
		peakWindow_ms = 100
		spikeClipWidth_ms = 1000 # for 2021_01_29_0003 (idx 13+3)
		refractory_ms = 400 # for 2021_01_29_0003 (idx 13+3)
		onlyPeaksAbove_mV = -20 # for 2021_01_29_0003 (idx 13+3)
		'''
		detectionDict = ba.getDefaultDetection()
		ba.spikeDetect(detectionDict)
		'''
		ba.spikeDetect(dVthresholdPos=dVthresholdPos, minSpikeVm=minSpikeVm,
			halfWidthWindow_ms=halfWidthWindow_ms,
			spikeClipWidth_ms=spikeClipWidth_ms,
			peakWindow_ms=peakWindow_ms,
			refractory_ms=refractory_ms,
			onlyPeaksAbove_mV=onlyPeaksAbove_mV)

			#avgWindow_ms=avgWindow_ms,
			#dvdtPreWindow_ms=dvdtPreWindow_ms,
			#peakWindow_ms=peakWindow_ms,
			#refractory_ms=refractory_ms,
			#dvdt_percentOfMax=dvdt_percentOfMax)
		'''

		#test_plot(ba)

		self.baAbf = ba

	def loadAndAnalyzeTif(self, dDict):
		"""
		working on spike detection from sum of intensities along a line scan
		see: example/lcr-analysis
		"""
		dVthresholdPos = dDict['caThresholdPos']
		minSpikeVm = dDict['caMinSpike']

		path = self.tifFile

		ba = sanpy.bAnalysis(path)
		ba.spikeDetect(dDict)

		#ba.getDerivative()

		# Ca recording is ~40 times slower than e-phys at 10 kHz
		#minSpikeVm = 0.5
		#dVthresholdPos = 0.01
		'''
		refractory_ms = 60 # was 20 ms
		avgWindow_ms=60 # pre-roll to find eal threshold crossing
			# was 5, in detect I am using avgWindow_ms/2 ???
		window_ms = 20 # was 2
		peakWindow_ms = 70 # 20 gives us 5, was 10
		dvdt_percentOfMax = 0.2 # was 0.1
		halfWidthWindow_ms = 60 # was 20
		spikeClipWidth_ms = 1000 # was 500
		ba.spikeDetect(dVthresholdPos=dVthresholdPos, minSpikeVm=minSpikeVm,
			avgWindow_ms=avgWindow_ms,
			window_ms=window_ms,
			peakWindow_ms=peakWindow_ms,
			refractory_ms=refractory_ms,
			dvdt_percentOfMax=dvdt_percentOfMax,
			halfWidthWindow_ms=halfWidthWindow_ms,
			spikeClipWidth_ms=spikeClipWidth_ms,
			)
		'''

		#for k,v in ba.spikeDict[0].items():
		#	print('  ', k, ':', v)

		#test_plot(ba, firstSampleTime)

		self.baTif = ba

	def plotSpikeAnalysis(self, type='abf', fileNumber=None, region=None, myParent=None):
		"""
		type: ('abf', 'tif')

		Expecting analysis has been run, see:
			self.loadAndAnalyzeTif
			self.loadAndAnalyzeAbf
		"""
		def close_event(event):
			"""
			tell parent we are closing
			"""
			#print('plotSpikeClip.close_event()')
			if myParent is not None:
				# for now expectin parent to be testTable.py
				myParent.closeChild('analysis plot', fileNumber)

		myParent = myParent

		if type == 'tif':
			yLabelStr = 'Ca (line scan sum)'
			tif = self.abfTif.tif
			ba = self.baTif
		elif type == 'abf':
			yLabelStr = 'Vm (mV)'
			tif = None
			ba = self.baAbf
		else:
			print('ERROR: plotSpikeAnalysis() is expecting type in (tif, abf), got type:', type)
			return

		firstSampleTime = 0 # todo: get rid of this

		# plot
		if tif is None:
			fig, axs = plt.subplots(2, 1, sharex=True)
		else:
			fig, axs = plt.subplots(3, 1, sharex=True)
		titleStr = self._getTitle(fileNumber=fileNumber, region=region)
		fig.suptitle(titleStr)

		#
		# dv/dt
		xDvDt = ba.abf.sweepX + firstSampleTime
		yDvDt = ba.filteredDeriv
		axs[0].plot(xDvDt, yDvDt, 'k')

		# thresholdVal_dvdt
		xThresh = [x['thresholdSec'] + firstSampleTime for x in ba.spikeDict]
		yThresh = [x['thresholdVal_dvdt'] for x in ba.spikeDict]
		axs[0].plot(xThresh, yThresh, 'or')

		axs[0].spines['right'].set_visible(False)
		axs[0].spines['top'].set_visible(False)

		#
		# vm with detection params
		sweepX = ba.abf.sweepX + firstSampleTime
		sweepY = ba.abf.sweepY
		axs[1].plot(sweepX, sweepY, 'k-', lw=0.5)
		axs[1].set_ylabel(yLabelStr)

		xThresh = [x['thresholdSec'] + firstSampleTime for x in ba.spikeDict]
		yThresh = [x['thresholdVal'] for x in ba.spikeDict]
		axs[1].plot(xThresh, yThresh, 'or')

		xPeak = [x['peakSec'] + firstSampleTime for x in ba.spikeDict]
		yPeak = [x['peakVal'] for x in ba.spikeDict]
		axs[1].plot(xPeak, yPeak, 'ob')

		sweepX = ba.abf.sweepX + firstSampleTime

		for idx, spikeDict in enumerate(ba.spikeDict):
			#
			# plot all widths
			#print('plotting width for spike', idx)
			for j,widthDict in enumerate(spikeDict['widths']):
				#for k,v in widthDict.items():
				#	print('  ', k, ':', v)
				#print('j:', j)
				if widthDict['risingPnt'] is None:
					#print('  -->> no half width')
					continue

				risingPntX = sweepX[widthDict['risingPnt']]
				# y value of rising pnt is y value of falling pnt
				#risingPntY = ba.abf.sweepY[widthDict['risingPnt']]
				risingPntY = ba.abf.sweepY[widthDict['fallingPnt']]
				fallingPntX = sweepX[widthDict['fallingPnt']]
				fallingPntY = ba.abf.sweepY[widthDict['fallingPnt']]
				fallingPnt = widthDict['fallingPnt']
				# plotting y-value of rising to match y-value of falling
				#ax.plot(ba.abf.sweepX[widthDict['risingPnt']], ba.abf.sweepY[widthDict['risingPnt']], 'ob')
				# plot as pnts
				#axs[1].plot(ba.abf.sweepX[widthDict['risingPnt']], ba.abf.sweepY[widthDict['fallingPnt']], '-b')
				#axs[1].plot(ba.abf.sweepX[widthDict['fallingPnt']], ba.abf.sweepY[widthDict['fallingPnt']], '-b')
				# line between rising and falling is ([x1, y1], [x2, y2])
				axs[1].plot([risingPntX, fallingPntX], [risingPntY, fallingPntY], color='b', linestyle='-', linewidth=2)

		axs[1].spines['right'].set_visible(False)
		axs[1].spines['top'].set_visible(False)

		if tif is not None:
			xMin = firstSampleTime
			xMax = ba.abf.sweepX[-1]
			yMin = 0
			yMax = ba.abf.tifHeader['umLength'] #57.176
			#extent = [xMin, xMaxImage, yMax, yMin] # flipped y
			dfMean = np.nanmean(tif)
			df_d0 = (tif- dfMean) / dfMean
			extent = [xMin, xMax, yMin, yMax] # flipped y
			axs[2].imshow(df_d0, extent=extent, aspect='auto')
			axs[2].spines['right'].set_visible(False)
			axs[2].spines['top'].set_visible(False)

		ba.errorReport()

		#
		return fig

	def NormalizeData(self, data):
		return (data - np.min(data)) / (np.max(data) - np.min(data))

	def plotSpikeClip(self, doPhasePlot=False, fileNumber=None, region=None, myParent=None, df=None):
		"""
		myParent: tkInter testTable
		"""

		cellNumber = None
		trial = None
		if df is not None:
			cellNumber = df['cell number'].loc[fileNumber]
			trial = df['trial'].loc[fileNumber]

		myParent = myParent # testTable
		global spikeNumber # needed because we will assign +/- in callback
		spikeNumber = 0 # used in callback for phase plot
		global phasePlotOptions
		phasePlotOptions = 0 # 0: one spike, 1: all + mean + one
		def close_event(event):
			"""
			tell parent we are closing
			"""
			#print('plotSpikeClip.close_event()')
			if myParent is not None:
				# for now expectin parent to be testTable.py
				try:
					myParent.closeChild('spike clip plot', fileNumber)
				except (AttributeError) as e:
					pass
		def key_press_event(event):
			#print('press', event.key)
			global spikeNumber # needed because we are assigning new value
			sys.stdout.flush()
			if event.key in ['.', 'right']:
				# next
				spikeNumber += 1
				updatePhasePlot(spikeNumber)
				updateOneSpikeClip(spikeNumber)

			if event.key in [',', 'left']:
				# previous
				spikeNumber -= 1
				if spikeNumber < 0:
					spikeNumber = 0
					return
				else:
					updatePhasePlot(spikeNumber)
					updateOneSpikeClip(spikeNumber)
			if event.key == 'p':
				global phasePlotOptions
				phasePlotOptions += 1
				if phasePlotOptions > 1:
					phasePlotOptions = 0
				if phasePlotOptions == 0:
					# just one clip
					pass
				elif phasePlotOptions == 1:
					# all + mean + 1
					pass

		def updateOneSpikeClip(localSpikeNumber):
			"""
			update axs[2] with (i) spike clip and (ii) lcr hist
			"""
			# grab x from vm recording (10kHz)
			xSpikeClips_vm = baAbf.spikeClips_x2[localSpikeNumber] # list of list
			ySpikeClips_vm = baAbf.spikeClips[localSpikeNumber]

			numVmSpikes = len(baAbf.spikeClips_x2)

			currentSpikeClipPlot.set_data(xSpikeClips_vm, ySpikeClips_vm)

			# yPreClipSparkMasterBins_2d is 2d list, one row per spike
			#print('  xPreClipSparkMasterBins:', xPreClipSparkMasterBins)
			#print('  yPreClipSparkMasterBins_2d:', yPreClipSparkMasterBins_2d[localSpikeNumber])
			# using stem(), easier to replot than to set data
			secondAxs2.cla()
			oneSpikeLcrBins = yPreClipSparkMasterBins_2d[localSpikeNumber]
			numLcr = sum(oneSpikeLcrBins)
			spikeTime = theseTime_sec[localSpikeNumber]
			print('updateOneSpikeClip() spikeNumber:', localSpikeNumber, 'of', numVmSpikes, 'spikeTime:', spikeTime, 'numLcr:', numLcr)

			secondAxs2.stem(xPreClipSparkMasterBins, oneSpikeLcrBins,
				linefmt='grey',
				markerfmt=' ', # use space ' ' and not None or ''
				basefmt=' ')

			fig.canvas.draw()

		def updatePhasePlot(localSpikeNumber):

			if doPhasePlot == 0:
				return

			numVmSpikes = len(baAbf.spikeClips_x2)
			numCaSpikes = len(baTiff.spikeClips_x2)

			print('localSpikeNumber:', localSpikeNumber, 'numVmSpikes:', numVmSpikes, 'numCaSpikes:', numCaSpikes)

			# grab x from vm recording (10kHz)
			xSpikeClips_vm = baAbf.spikeClips_x2[localSpikeNumber] # list of list
			ySpikeClips_vm = baAbf.spikeClips[localSpikeNumber]

			# ca
			xSpikeClips_ca = baTiff.spikeClips_x2[localSpikeNumber] # list of list
			ySpikeClips_ca = baTiff.spikeClips[localSpikeNumber]

			# interp for phase plot
			yInterpSpikeClips_ca = np.interp(xSpikeClips_vm, xSpikeClips_ca, ySpikeClips_ca)

			plottedPhaseLine.set_data(ySpikeClips_vm, yInterpSpikeClips_ca)

			axs[2].set_xlim(min(ySpikeClips_vm), max(ySpikeClips_vm)) #added ax attribute here
			axs[2].set_ylim(min(yInterpSpikeClips_ca), max(yInterpSpikeClips_ca)) #added ax attribute here

			#
			vmCurrentSpikeClip.set_data(xSpikeClips_vm, ySpikeClips_vm)
			caCurrentSpikeClip.set_data(xSpikeClips_ca, ySpikeClips_ca)

			fig.canvas.draw()

		#
		# start of main function
		tifPath = self.tifFile
		abfPath = self.abfFile
		tifHeader = self.abfTif.tifHeader

		#baTiff = test_load_tif(tifPath) # imaging
		#baAbf = test_load_abf(abfPath) # recording
		baTiff = self.baTif
		baAbf = self.baAbf

		if baTiff is None or baAbf is None:
			print('ERROR: plotSpikeClip() did not find analysis')
			return None

		thresholdSec0, peakSec0 = baTiff.getStat('thresholdSec', 'peakSec')
		thresholdSec1, peakSec1 = baAbf.getStat('thresholdSec', 'peakSec')

		print('plotSpikeClip() ca num spikes:', baTiff.numSpikes, ', vm num spikes:', len(thresholdSec1), baAbf.numSpikes)

		# ca
		doPhasePlot = 0
		if doPhasePlot:
			numSubplots = 3
		else:
			numSubplots = 2
		numSubplots = 3 # axs[2] will be one spike clip + lcr
		fig, axs = plt.subplots(numSubplots, 1, sharex=True)
		# share just axs[0] and axs[1], axs[2] is phase plot
		#axs[0].get_shared_x_axes().join(axs[0], axs[1])

		# set the window/figure title
		titleStr = self._getTitle(fileNumber=fileNumber, region=region)
		titleStr = 'SpikeClips:' + titleStr
		fig.canvas.set_window_title(titleStr)
		fig.suptitle(titleStr)

		fig.canvas.mpl_connect('key_press_event', key_press_event)
		fig.canvas.mpl_connect('close_event', close_event)

		axs[0].spines['right'].set_visible(False)
		axs[0].spines['top'].set_visible(False)
		axs[0].set_ylabel('Ca Intensity')

		axs[1].spines['right'].set_visible(False)
		axs[1].spines['top'].set_visible(False)
		axs[1].set_ylabel('Vm')
		axs[1].set_xlabel('Time (ms)')

		# use threshholdSec of abf file to retrieve spike clips from Ca
		spikeClipWidth_ms = 400
		spikeClipWidth_sec = spikeClipWidth_ms / 1000

		#
		# ca
		theseTime_sec = self.baAbf.getStat('thresholdSec') # spike times from abf
		# theseTime_sec is spike time in abf, need to shift it for imaging
		firstFrameSeconds = self.abfTif.tifHeader['firstFrameSeconds']
		caTheseTime_sec = [x-firstFrameSeconds for x in theseTime_sec]
		#caTheseTime_sec = None
		spikeClips_x2, spikeClips = baTiff.makeSpikeClips(spikeClipWidth_ms, theseTime_sec=caTheseTime_sec)
		for idx, sec in enumerate(thresholdSec0):
			try:
				#spikeClips_x2 = baTiff.spikeClips_x2[idx] # list of list
				#spikeClips = baTiff.spikeClips[idx]
				oneSpikeClips_x2 = spikeClips_x2[idx]
				oneSpikeClips = spikeClips[idx]
				axs[0].plot(oneSpikeClips_x2, oneSpikeClips, '-k')
			except (IndexError) as e:
				print('error: plotSpikeClip() ca no spike', idx)

		#
		# start 20210317
		#

		#
		# vm
		abfSpikeClips_x2, abfSpikeClips = baAbf.makeSpikeClips(spikeClipWidth_ms, theseTime_sec=theseTime_sec)
		for idx, sec in enumerate(thresholdSec1):
			try:
				'''
				spikeClips_x2 = baAbf.spikeClips_x2[idx] # list of list
				spikeClips = baAbf.spikeClips[idx]
				axs[1].plot(spikeClips_x2, spikeClips, '-k')
				'''

				oneSpikeClips_x2 = abfSpikeClips_x2[idx]
				oneSpikeClips = abfSpikeClips[idx]
				axs[1].plot(oneSpikeClips_x2, oneSpikeClips, '-k')

				if idx == 0:
					currentSpikeClipPlot, = axs[2].plot(oneSpikeClips_x2, oneSpikeClips, '-k')

			except (IndexError) as e:
				print('error: plotSpikeClip() vm no spike', idx)

		#
		# sparkmaster
		# bin SM LCR before each spike
		if self.dfSparkMaster is not None:
			halWidth_ms_int = int(spikeClipWidth_ms/2)
			# this yPreClipSparkMasterBins is misleading
			# generate a y for EACH spike and take avg/#spike to get something more like a probability
			#yPreClipSparkMasterBins2 = [0] * halWidth_ms_int +1 for LCR -1 for none
			yPreClipSparkMasterBins = [0] * halWidth_ms_int # for count for each ms across all spikes
			xPreClipSparkMasterBins = [-x for x in range(halWidth_ms_int)] # -0, -1, -2

			# 2d list of spark-master bins per spike
			yPreClipSparkMasterBins_2d = []

			#xPreClipSparkMasterBins.reverse() # -3, -2, -1

			# 2d ndaray to get mean of each bin (column)
			# this is like a probability
			numSpikes = len(caTheseTime_sec)
			yPreClipPerSpike = np.zeros((numSpikes,halWidth_ms_int))

			# the time of each LCR (w.r.t. imaging)
			tPos = self.dfSparkMaster['t-pos'].values
			#print(type(tPos), tPos)
			# caTheseTime_sec is based on abf 'thresholdSec'
			for idx, smSec in enumerate(caTheseTime_sec):
				# new row to hold lcr hist for this one spike (idx)
				yPreClipSparkMasterBins_2d.append([0] * halWidth_ms_int)

				smStartSec = smSec-(spikeClipWidth_sec/2)
				smStopSec = smSec #+spikeClipWidth_sec
				smHits_pnts = np.argwhere((tPos>smStartSec) & (tPos<smStopSec))
				#print('  tPos[smHits_pnts]:', tPos[smHits_pnts])
				smHits_ms = (smSec*1000) - (tPos[smHits_pnts]*1000)
				# - because we want BEFORE spike and with int() we bin for manual hist
				smHits_ms = [int(-x) for x in smHits_ms]
				for smHitms in smHits_ms:
					# todo: make sure -smHitms is good index
					try:
						yPreClipSparkMasterBins[-smHitms] += 1 # add one to bin
						yPreClipPerSpike[idx][-smHitms] += 1
						# 2d list to keep track of lcr per spike
						yPreClipSparkMasterBins_2d[idx][-smHitms] += 1
					except (IndexError) as e:
						print('    ERROR: spike', idx, 'had error with -smHitms:', -smHitms)

				print('  spike', idx, 'smSec:', smSec, 'has', len(smHits_pnts), 'sm pnts before it, smHits_ms:', smHits_ms)
				#print('    20ms before spike', xPreClipSparkMasterBins[0:20])
				#print('    20ms before spike', yPreClipSparkMasterBins[0:20])

				# fit line and put in self.baAbf spikeDict
				x_values = xPreClipSparkMasterBins # same for every spikes
				y_values = yPreClipSparkMasterBins # starts at all 0 and accumulates lcr (could be 0 lcr !!!)
				resultObj = scipy.stats.linregress(x_values, y_values)
				# there is also resultObj.rvalue (not need to run pearsons)
				print('spike', idx, 'region:', region, 'resultObj slope:', resultObj.slope, 'p:', resultObj.pvalue)
				self.baAbf.spikeDict[idx]['lcrSlope'] = resultObj.slope
				self.baAbf.spikeDict[idx]['lcrNum'] = len(smHits_pnts) # number of lcr before spike
				self.baAbf.spikeDict[idx]['region'] = region
				self.baAbf.spikeDict[idx]['cell number'] = cellNumber
				self.baAbf.spikeDict[idx]['trial'] = trial

			#
			# 20210311
			# save the merged SanPy/clr anaysis
			# this is for generating figure 9
			if 0:
				tmpSavefile = '/Users/cudmore/Sites/SanPy/examples/dual-analysis/tmpMergedDatabase'
				print('self.baAbf.file:', self.baAbf.file)
				tmpAbfPath, tmpAbfFile = os.path.split(self.baAbf.file)
				tmpAbfFile, tmpExt = os.path.splitext(tmpAbfFile)
				tmpAbfFile += '.csv'
				tmpSavefile = os.path.join(tmpSavefile, tmpAbfFile)
				print('saving fig9 merged database to tmpSavefile:', tmpSavefile)
				self.baAbf.saveReport(tmpSavefile, saveExcel=False, alsoSaveTxt=True)

			# 2d, take mean of col (# lcr in each ms across all spikes)
			#print('yPreClipPerSpike:', yPreClipPerSpike)
			yPreClipSpikeMean = yPreClipPerSpike.mean(axis=0)
			#print('yPreClipSpikeMean[0:20]:', yPreClipSpikeMean[0:20])

			# compare the slope for each spike to its earlyDiastolicDurationRate
			# test significance
			eddRate, lcrSlope = baAbf.getStat('earlyDiastolicDurationRate', 'lcrSlope') #returns list []
			eddRate = np.array(eddRate)
			lcrSlope = np.array(lcrSlope)
			notNaNIdx = ~np.isnan(eddRate) & ~np.isnan(lcrSlope) # strip nan
			#print('notNaNIdx:', notNaNIdx)
			rTmp, pTmp = scipy.stats.pearsonr(eddRate[notNaNIdx], lcrSlope[notNaNIdx])
			print('  test eddRate vs lcrSlope pearsonsr r:', rTmp, 'p:', pTmp)
			if 0:
				# plot slope versus early diastolic duration rate
				tmpFig, tmpAxs = plt.subplots(1, 1, sharex=False)
				tmpAxs = [tmpAxs]
				tmpAxs[0].plot(eddRate, lcrSlope)
				plt.show()

			#
			# fit a line to all spike
			# see https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.linregress.html
			def lineFitFunction(x, a, b, c):
				return a * x + b
			x_values = xPreClipSparkMasterBins
			y_values = yPreClipSpikeMean
			# popt: [0.0002 0.0418 1.    ]
			popt, pcov = scipy.optimize.curve_fit(lineFitFunction, x_values, y_values)
			#print('slope*x + intercept ... a * x + b')
			#print('popt:', popt)
			#print('pcov:', pcov)
			xFit = np.linspace(min(x_values), max(x_values), 1000)
			yFit = lineFitFunction(xFit, *popt)
			# plot(x_line, y_line)
			resultObj = scipy.stats.linregress(x_values, y_values)
			print('  all spikes resultObj slope of # lcr approacing spike:', resultObj.slope, 'p:', resultObj.pvalue)

			# copy/paste to excel
			tifStr = os.path.split(tifPath)[1]
			print(f'index\ttif\tregion\tnSpikes\tslope\tp\tr\tp')
			print(f'{fileNumber}\t{tifStr}\t{region}\t{numSpikes}\t{round(resultObj.slope,5)}\t{round(resultObj.pvalue,5)}\t{round(rTmp,5)}\t{round(pTmp,5)}')

			#
			secondAxs1 = axs[1].twinx()
			#secondAxs1.spines['right'].set_visible(False)
			secondAxs1.spines['top'].set_visible(False)
			#secondAxs1.plot(xPreClipSparkMasterBins, yPreClipSparkMasterBins, '.b')
			# was this
			'''
			yPreClipSparkMasterBins = [x if x>0 else np.nan for x in yPreClipSparkMasterBins]
			secondAxs1.stem(xPreClipSparkMasterBins, yPreClipSparkMasterBins,
						linefmt='.b',
						markerfmt=' ', # use space ' ' and not None or ''
						basefmt=' ')
			'''
			# now this
			yPreClipSpikeMean = [x if x>0 else np.nan for x in yPreClipSpikeMean]
			secondAxs1.stem(xPreClipSparkMasterBins, yPreClipSpikeMean,
						linefmt='grey',
						markerfmt=' ', # use space ' ' and not None or ''
						basefmt=' ')
			secondAxs1.plot(xFit, yFit, 'b', linewidth=2.5)
			#
			secondAxs1.set_ylabel('Prob LCR')

			#
			# end 20210317
			#

			#
			# axs[2] is showing 1 spike
			# twin axs[2] to show one hist of lcr (for one spike)
			secondAxs2 = axs[2].twinx()
			secondAxs2.spines['top'].set_visible(False)
			# xPreClipSparkMasterBins is 1d
			oneSpikeLCRHist = secondAxs2.stem(xPreClipSparkMasterBins, yPreClipSparkMasterBins_2d[0],
						linefmt='grey',
						markerfmt=' ', # use space ' ' and not None or ''
						basefmt=' ')
			# todo: maybe add line fit???

		# BROKEN 20210218
		#
		# phase plot
		if doPhasePlot:

			# grab x from vm recording (10kHz)
			xSpikeClips_vm = baAbf.spikeClips_x2[spikeNumber] # list of list
			ySpikeClips_vm = baAbf.spikeClips[spikeNumber]

			# ca
			xSpikeClips_ca = baTiff.spikeClips_x2[spikeNumber] # list of list
			ySpikeClips_ca = baTiff.spikeClips[spikeNumber]

			# interp ca clip to have same # samples as vm clip
			ySpikeClips_ca = np.interp(xSpikeClips_vm, xSpikeClips_ca, ySpikeClips_ca)

			plottedPhaseLine, = axs[2].plot(ySpikeClips_vm, ySpikeClips_ca, '.k')

			axs[2].spines['right'].set_visible(False)
			axs[2].spines['top'].set_visible(False)
			axs[2].set_xlabel('Vm')
			axs[2].set_ylabel('Ca')

			# make current spike larger and red
			spikeClips_x2 = baTiff.spikeClips_x2[spikeNumber] # list of list
			spikeClips = baTiff.spikeClips[spikeNumber]
			caCurrentSpikeClip, = axs[0].plot(spikeClips_x2, spikeClips, '-r', lw=2)

			spikeClips_x2 = baAbf.spikeClips_x2[spikeNumber] # list of list
			spikeClips = baAbf.spikeClips[spikeNumber]
			vmCurrentSpikeClip, = axs[1].plot(spikeClips_x2, spikeClips, '-r', lw=2)

		#
		return fig

	def myPlot(self, fileNumber=None, region=None, myParent=None):
		"""
		tif: 2D numpy.array
		tifHeader: dict
		abf: abf file
		"""

		fileNumber = fileNumber
		myParent = myParent

		tif = self.abfTif.tif
		tifHeader = self.abfTif.tifHeader
		abf = self.abf

		def close_event(event):
			"""
			tell parent we are closing
			"""
			if myParent is not None:
				# for now expectin parent to be testTable.py
				myParent.closeChild('raw plot', fileNumber)

		def key_press_event(event):
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

			# todo: make a wrapper
			'''
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
			'''

		# todo: make a wrapper that uses database and
		# load/plots a number of dualRecord object
		#
		#df = df # used by callback
		#fileNumber = fileNumber # used by callback
		#fileNumber = None

		# open a figure window
		plotVm  = 1
		if plotVm:
			numPanels = 3
		else:
			numPanels = 2
		fig, axs = plt.subplots(numPanels, 1, sharex=True)
		fig.canvas.mpl_connect('key_press_event', key_press_event)
		fig.canvas.mpl_connect('close_event', close_event)

		# set the window/figure title
		titleStr = ''
		if fileNumber is not None:
			titleStr += str(fileNumber) + ' '
		if region is not None:
			titleStr += region + ' '
		titleStr += os.path.split(tifHeader['tif'])[1]
		fig.canvas.set_window_title(titleStr)
		#fig.suptitle(titleStr)
		'''
		titleStr = 'SpikeClips:' + titleStr
		fig.canvas.set_window_title(titleStr)
		'''

		# e-phy recording always starts at time 0
		xMinPhys = 0

		xPlot = abf.sweepX
		xPlot += xMinPhys # e-phys recording starts with (100 ms + 5 ms ttl)
		yPlot = abf.sweepY
		# xMaxRecordingSec is same as abf.sweepX[-1]
		xMaxRecordingSec = tifHeader['xMaxRecordingSec']
		firstFrameSeconds = tifHeader['firstFrameSeconds']

		# time of first frame, shift image by this amount
		#tagTimesSec = abf.tagTimesSec
		#firstFrameSeconds = tagTimesSec[0]
		'''
		print('  abf.tagTimesSec has', len(abf.tagTimesSec), 'tags,'
			'first tag seconds:', tagTimesSec[0],
			'first interval:', tagTimesSec[1] - tagTimesSec[0])
		'''

		xMaxImage = tifHeader['totalSeconds'] #35.496 # seconds
		xMax = max(xMaxImage+firstFrameSeconds, xMaxRecordingSec)
		xMaxLim = min(xMaxImage+firstFrameSeconds, xMaxRecordingSec)
		#print('  xMaxLim:', xMaxLim, 'the max on the x-axis (is min between image duration and abf record time')

		# image
		xMin = firstFrameSeconds
		yMin = 0
		yMax = tifHeader['umLength'] #57.176
		extent = [xMin, xMax, yMin, yMax] # flipped y
		cmap = 'inferno' #'Greens' # 'inferno'
		dfMean = np.nanmean(tif)
		df_d0 = (tif- dfMean) / dfMean
		axs[0].imshow(df_d0, aspect='auto', cmap=cmap, extent=extent)
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
		'''
		yLineScanSum = [np.nan] * tif.shape[1]
		xLineScanSum = [np.nan] * tif.shape[1]
		for i in range(tif.shape[1]):
			# dimension [1] steps through each line scan (like 10,000)
			theSum = np.sum(tif[:,i])
			theSum /= tif.shape[0]
			yLineScanSum[i] = theSum
			xLineScanSum[i] = firstFrameSeconds + (tifHeader['secondsPerLine'] * i)
		'''

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
			self._printDict(self.abfTif.tifHeader)

			xLineScanSum = self.abfTif.sweepX + firstFrameSeconds
			yLineScanSum = self.abfTif.sweepY

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

		return fig

	def loadSparkMaster(self):
		#
		# try and load _sm.csv
		tmpPath, tmpExt = os.path.splitext(self.tifFile)
		# sm .csv will come from raw (_sm.csv) or clipped (_clipped_sm.csv)
		csvPath = tmpPath + '_clipped_sm.csv'
		if not os.path.isfile(csvPath):
			csvPath = tmpPath + '_sm.csv'

		if not os.path.isfile(csvPath):
			print('  warning: dualAnalysis.loadSparkMaster() did not find csvPath:', csvPath)
		else:
			dfSparkMaster = pd.read_csv(csvPath, header=0)
			# remove all spaces from column names and rename them
			for colIdx, colStr in enumerate(dfSparkMaster.columns):
				newColStr = colStr.replace(' ', '')
				#dfSparkMaster.columns[colIdx] = colStr
				dfSparkMaster.rename(columns={colStr: newColStr}, inplace=True)

			self.dfSparkMaster = dfSparkMaster

			print('dualAnalysis.loadSparkMaster() loaded sparkmaster analysis')
			print('  csvPath:', csvPath)
			print('  number of LCR ROIs:', len(dfSparkMaster))
			#print(dfSparkMaster.head())

	#def _loadAnalyzeFrom_df(self, df, fileNumber):
	def _loadAnalyzeAbf_from_df(self, df, fileNumber):
		abfFile = df['abfPath'].loc[fileNumber]

		ba = sanpy.bAnalysis(abfFile)
		detectionDict = ba.getDefaultDetection()

		# pull values from df
		for k,v in detectionDict.items():
			if k in df.columns:
				dfValue = df[k].iloc[fileNumber]
				if not np.isnan(dfValue):
					detectionDict[k] = dfValue

		#detectionDict['medianFilter'] = 5

		# special case to turn off dV/dt detection and just use mV
		dvdtThreshold = df['dvdtThreshold'].iloc[fileNumber]
		if np.isnan(dvdtThreshold):
			detectionDict['dvdtThreshold'] = None

		# debug
		'''
		print('\n=== abf detection dict')
		self._printDict(detectionDict)
		'''

		ba.spikeDetect(detectionDict)

		self.baAbf = ba

	def _loadAnalyzeCa_from_df(self, df, fileNumber):
		tifFile = df['tifPath'].loc[fileNumber]

		baTif = sanpy.bAnalysis(tifFile)
		caDetectionDict = baTif.getDefaultDetection_ca()

		# update values in dDict from df
		caThresholdPos = df['caThresholdPos'].iloc[fileNumber]
		minSpikeVm = df['caMinSpike'].iloc[fileNumber]
		#print('caThresholdPos:', type(caThresholdPos), caThresholdPos)
		if ~np.isnan(caThresholdPos):
			caDetectionDict['dvdtThreshold'] = caThresholdPos
		if ~np.isnan(minSpikeVm):
			caDetectionDict['vmThreshold'] = minSpikeVm

		# debug
		'''
		print('\n=== ca detection dict')
		self._printDict(caDetectionDict)
		'''

		baTif.spikeDetect(caDetectionDict)

		#
		self.baTif = baTif


	def plotSpikeClip_df(self, df, fileNumber, forFig9=False, myParent=None):
		"""
		to plot spike clips from testTable.py
		"""

		#self._loadAnalyzeFrom_df(df, fileNumber)
		self._loadAnalyzeCa_from_df(df, fileNumber)
		self._loadAnalyzeAbf_from_df(df, fileNumber)

		region = df['region'].loc[fileNumber]

		self.findSpikePairs(fileNumber=fileNumber, doPlot=False)

		#dr.plotSpikeAnalysis(type='tif') # works
		if forFig9:
			fig = self.plotClips(fileNumber=fileNumber, region=region)
		else:
			fig = self.plotSpikeClip(doPhasePlot=True, fileNumber=fileNumber,
								region=region, df=df,
								myParent=myParent)

		return fig

	def plotSpikeDetection_df(self, df, fileNumber, myParent=None):
		"""
		to plot spike clips from testTable.py
		"""

		#self._loadAnalyzeFrom_df(df, fileNumber)
		self._loadAnalyzeCa_from_df(df, fileNumber)
		self._loadAnalyzeAbf_from_df(df, fileNumber)

		region = df['region'].loc[fileNumber]

		#dr.plotSpikeAnalysis(type='tif') # works
		#fig = self.plotSpikeClip(doPhasePlot=True, fileNumber=fileNumber,
		#						region=region, myParent=myParent)
		figTif = self.plotSpikeAnalysis(type='tif', fileNumber=fileNumber, myParent=myParent)
		figAbf = self.plotSpikeAnalysis(type='abf', fileNumber=fileNumber, region=region, myParent=myParent)

		return figTif, figAbf

	def old_fix_lcrDualAnalysis(self, fileIndex):
		"""
		todo: update to use df

		for 2x files, line-scan and e-phys
		plot spike time delay of ca imaging
		"""
		#fileIndex = 3
		tifPath = lcrData.dataList[fileIndex]['tif']
		abfPath = lcrData.dataList[fileIndex]['abf']

		ba1 = test_load_abf(abfPath) # recording
		# now need to get this from pClamp abf !!!
		#firstSampleTime = baTiff.abf.sweepX[0] # is not 0 for 'wait for trigger' FV3000
		firstSampleTime = ba1.abf.tagTimesSec[0]
		print('firstSampleTime:', firstSampleTime)

		#myPlot(tif, tifHeader, abf, plotCaSum=False)

		test_plot(ba1)

		# abf from tif will ALWAYS be 0 based
		ba0 = test_load_tif(tifPath) # image

		tif = ba0.abf.tifNorm
		test_plot(ba0, tif=tif, firstSampleTime=firstSampleTime)

		#plt.show()

		thresholdSec0, peakSec0 = ba0.getStat('thresholdSec', 'peakSec')
		thresholdSec1, peakSec1 = ba1.getStat('thresholdSec', 'peakSec')

		# for each spike in e-phys, match it with a spike in imaging
		# e-phys is shorter, fewer spikes
		numSpikes = len(thresholdSec1) #ba1.numSpikes
		print('num spikes in recording:', numSpikes)

		ba1_width50, throwOut = ba1.getStat('widths_50', 'peakSec')

		# todo: add an option in bAnalysis.getStat()
		thresholdSec0 = [x + firstSampleTime for x in thresholdSec0]
		peakSec0 = [x + firstSampleTime for x in peakSec0]

		# assuming spike-detection is clean
		# truncate imaging (it is longer than e-phys)
		thresholdSec0 = thresholdSec0[0:numSpikes] # second value/max is NOT INCLUSIVE
		peakSec0 = peakSec0[0:numSpikes]

		numSubplots = 2
		fig, axs = plt.subplots(numSubplots, 1, sharex=False)

		titleStr = os.path.split(ba0.abf.tifHeader['tif'])[1]
		fig.suptitle(titleStr)

		# threshold in image starts about 20 ms after Vm
		axs[0].plot(thresholdSec1, peakSec0, 'ok')
		#axs[0].plot(thresholdSec1, 'ok')

		# draw diagonal
		axs[0].plot([0, 1], [0, 1], transform=axs[0].transAxes)

		axs[0].spines['right'].set_visible(False)
		axs[0].spines['top'].set_visible(False)

		axs[0].set_xlabel('thresholdSec1 (abf)')
		axs[0].set_ylabel('peakSec0 (tif)')

		#axs[1].plot(thresholdSec1, peakSec0, 'ok')

		# time to peak in image wrt AP threshold time
		caTimeToPeak = []
		for idx, thresholdSec in enumerate(thresholdSec1):
			timeToPeak = peakSec0[idx] - thresholdSec
			#print('thresholdSec:', thresholdSec, 'peakSec0:', peakSec0[idx], 'timeToPeak:', timeToPeak)
			timeToPeakMs = timeToPeak * 1000
			caTimeToPeak.append(timeToPeakMs)

		print('caTimeToPeak:', caTimeToPeak)

		axs[1].plot(ba1_width50, caTimeToPeak, 'ok')

		# draw diagonal
		#axs[1].plot([0, 1], [0, 1], transform=axs[1].transAxes)
		axs[1].spines['right'].set_visible(False)
		axs[1].spines['top'].set_visible(False)

		axs[1].set_xlabel('Vm half width (ms)')
		axs[1].set_ylabel('Ca++ Time To Peak\n(ms)')

		#
		#plt.show()

	def _getTitle(self, fileNumber=None, region=None):
		# set the window/figure title
		titleStr = ''
		if fileNumber is not None:
			titleStr += str(fileNumber) + ' '
		if region is not None:
			titleStr += region + ' '
		titleStr += os.path.split(self.abfTif.tifHeader['tif'])[1]
		return titleStr

	def findSpikePairs(self, fileNumber=None, doPlot=False):
		"""
		for each vm spike, find the 1st ca spike in a later window

		we will add (caDelay_sec, caWidth_ms) to each spike dict in (baAbf)
		"""

		# max allowed delya to peak
		maxCaDelaySecond = 0.6

		print('=== findSpikePairs() start pairing, maxCaDelaySecond:', maxCaDelaySecond)
		#
		# add to self.baAbf.spikeDict
		for spikeDict in self.baAbf.spikeDict:
			spikeDict['caDelay_sec'] = np.nan
			spikeDict['caWidth_ms'] = np.nan

		firstFrameSeconds = self.abfTif.tifHeader['firstFrameSeconds']
		print('  firstFrameSeconds:', firstFrameSeconds)

		vmThresholdSecs, vmPeakSeconds = self.baAbf.getStat('thresholdSec', 'peakSec')
		caThresholdSecs, caPeakSeconds = self.baTif.getStat('thresholdSec', 'peakSec')

		print('  len(vmThresholdSecs)', len(vmThresholdSecs))
		print('  len(caThresholdSecs)', len(caThresholdSecs))

		# shift tif image by delay to start
		caThresholdSecs = [x+firstFrameSeconds for x in caThresholdSecs]
		caPeakSeconds = [x+firstFrameSeconds for x in caPeakSeconds]

		vm_width50, throwOut = self.baAbf.getStat('widths_50', 'peakSec')
		ca_width50, throwOut = self.baTif.getStat('widths_50', 'peakSec')

		# pair each Vm spike with the next ca spike
		# is ca delay is >maxDelaySecond then reject the pairr
		caDelayToPeak = [np.nan] * len(vmThresholdSecs)
		caWidth = [np.nan] * len(vmThresholdSecs)
		for idx, vmThresholdSec in enumerate(vmThresholdSecs):
			# if vm threshold second is <firstFrameSeconds then igonore (we have to Ca data)
			if vmThresholdSec < firstFrameSeconds:
				print('  rejecting vm spike', idx, 'it is at', vmThresholdSec, 'before start of ca imaging at:', firstFrameSeconds)
				continue

			#caPeakPoint = np.argwhere(caPeakSeconds>vmThresholdSec)[0,0]  # Upward crossings
			caPeakPoint = np.argwhere(caPeakSeconds>vmThresholdSec)  # Upward crossings
			if len(caPeakPoint) == 0:
				print(f'  rejecting vm spike {idx}, did not find caPeakSeconds>vmThresholdSec {vmThresholdSec}')
				continue
			caPeakPoint = caPeakPoint[0,0]
			caPeakSecond = caPeakSeconds[caPeakPoint]

			caDelay = caPeakSecond - vmThresholdSec
			if caDelay > maxCaDelaySecond:
				print('  rejecting vm spike', idx, 'caDelay > maxCaDelaySecond, caDelay:', caDelay)

				vm_width50[idx] = np.nan
				caDelayToPeak[idx] = np.nan
				caWidth[idx] = np.nan
			else:
				'''
				print('pairing vm spike', idx, 'at', round(vmThresholdSec,3), \
						'with ca spike', caPeakPoint, 'at', round(caPeakSecond,3), \
						'caDelay:', caDelay)
				'''
				if caDelay > 0.5:
					print('warning pairing long delay of', caDelay, 'vm spike', idx, round(vmThresholdSec,3), ', with ca spike at', round(caPeakSecond,3))
				caDelayToPeak[idx] = caDelay
				#caWidth[idx] = ca_width50[idx]
				caWidth[idx] = ca_width50[caPeakPoint]

				# add to self.abfVm.spikeDict
				self.baAbf.spikeDict[idx]['caDelay_sec'] = caDelay
				self.baAbf.spikeDict[idx]['caWidth_ms'] = ca_width50[caPeakPoint]

		# plot
		if doPlot:
			fig, axs = plt.subplots(1, 2, sharex=False)
			#axs = [axs]
			titleStr = self._getTitle(fileNumber=fileNumber)
			fig.suptitle(titleStr)
			'''
			# todo: my mV threshold detection is SHIT, we are not getting half-widths
			print('plotting vm_width50:', vm_width50)
			print('plotting caDelayToPeak:', caDelayToPeak)
			'''
			axs[0].plot(vm_width50, caDelayToPeak, 'ok')
			axs[0].set_xlabel('vm_width50 (ms)')
			axs[0].set_ylabel('ca_DelayToPeak (s)')
			axs[0].spines['right'].set_visible(False)
			axs[0].spines['top'].set_visible(False)
			titleStr = self._getTitle(fileNumber=fileNumber)

			axs[1].plot(vm_width50, caWidth, 'ok')
			axs[1].set_xlabel('vm_width50 (s)')
			axs[1].set_ylabel('ca_width50 (ms)')
			axs[1].spines['right'].set_visible(False)
			axs[1].spines['top'].set_visible(False)

			if 1:
				self.plotSpikeAnalysis(type='abf', fileNumber=fileNumber) # works
				self.plotSpikeAnalysis(type='tif', fileNumber=fileNumber) # works

def runPool():
	"""
	load/analyze/findspikepairs, then
		output a long list of spike stats as a df (one row per spike
	"""
	df = loadDatabase()

	dfMaster = None

	for fileNumber in range(len(df)):

		tifFile = df['tifPath'].loc[fileNumber]
		abfFile = df['abfPath'].loc[fileNumber]

		spikeAnalysis = df['spike analysis'].iloc[fileNumber]
		if spikeAnalysis != 1:
			continue

		region = df['region'].iloc[fileNumber]
		quality = df['quality'].iloc[fileNumber]
		cellNumber = df['cell number'].iloc[fileNumber]
		trial = df['trial'].iloc[fileNumber]

		print('runPool() running on file:', fileNumber)

		dr = dualRecord(tifFile, abfFile)

		dr._loadAnalyzeCa_from_df(df, fileNumber)
		dr._loadAnalyzeAbf_from_df(df, fileNumber)

		dr.findSpikePairs(fileNumber=fileNumber, doPlot=False)

		# dr.baAbf.spikeDict[] now has (caDelay_sec, caWidth_ms)

		# make a spike report
		df0 = pd.DataFrame(dr.baAbf.spikeDict)
		# append columns
		df0['include'] = 1
		df0['cellNumber'] = cellNumber # each cell can have multiple trial
		df0['trial'] = trial # multiple trials for each cell e.g. 3a/3b/3c
		df0['quality'] = quality
		df0['region'] = region
		df0['fileNumber'] = fileNumber # rows in .xlsx database, individual recording
		print('df0.shape:', df0.shape)
		if dfMaster is None:
			dfMaster = df0
		else:
			dfMaster = dfMaster.append(df0, ignore_index=True)

		#if fileNumber==4:
		#	print(dfMaster.head())
		#	sys.exit()

	#
	print('runPool() dfMaster len:', len(dfMaster))
	#savePath = '/Users/cudmore/Desktop/dualAnalysis_final_db.csv'
	savePath = 'dualAnalysis_final_db.csv'
	print('savePath:', savePath)
	dfMaster.to_csv(savePath)

def runOneRecording():
	df = loadDatabase()

	if 1:
		fileNumber = 16 #20210205, was 13 but laura added 3x cells
		fileNumber = 19
		# working backwards through .xlsx
		fileNumber = 20
		fileNumber = 19
		fileNumber = 18
		# bad cell fileNumber = 17
		fileNumber = 16
		fileNumber = 15
		fileNumber = 14
		# nope fileNumber = 13
		# nope fileNumber = 12
		fileNumber = 11
		# nope fileNumber = 10
		fileNumber = 9 # PERFECT RECORDING !!!
		fileNumber = 8 # PERFECT RECORDING !!!
		# nope fileNumber = 7
		# nope fileNumber = 6
		# nope fileNumber = 5
		fileNumber = 4 # PERFECT RECORDING !!!
		fileNumber = 3 # PERFECT RECORDING !!!
		fileNumber = 2 # PERFECT RECORDING !!!

		tifFile = df['tifPath'].loc[fileNumber]
		abfFile = df['abfPath'].loc[fileNumber]

		print('tifFile:', tifFile)

		dr = dualRecord(tifFile, abfFile)

		dr._loadAnalyzeCa_from_df(df, fileNumber)
		dr._loadAnalyzeAbf_from_df(df, fileNumber)

		if 0:
			dr.plotSpikeAnalysis(type='tif', fileNumber=fileNumber) # works
			dr.plotSpikeAnalysis(type='abf', fileNumber=fileNumber) # works
			plt.show()

		# after this, underlying dr.baAbf.spikeDict[]
		# will have caDelay_sec and caWidth_ms
		dr.findSpikePairs(fileNumber=fileNumber, doPlot=True)

		#
		plt.show()

if __name__ == '__main__':

	# this works, generate per spike _db across all files in xlsx database
	# then open with bScatterPlotWidthet2.py
	if 0:
		#runOneRecording()
		# make a spike db (with ca peak/delay)
		# likewe would for sanpy
		runPool()

	# testing the plotting of output of Fiji/ImageJ spark master
	if 0:
		fileNumber = 3
		tifPath = '/Users/cudmore/Sites/SanPy/examples/dual-analysis/dual-data/20210115/20210115__0001.tif'
		abfPath = '/Users/cudmore/Sites/SanPy/examples/dual-analysis/dual-data/20210115/21115002.abf'

		fileNumber = 4
		tifPath = '/Users/cudmore/Sites/SanPy/examples/dual-analysis/dual-data/20210115/20210115__0002.tif'
		abfPath = '/Users/cudmore/Sites/SanPy/examples/dual-analysis/dual-data/20210115/21115003.abf'

		dr = dualRecord(tifPath, abfPath)
		#dr.printHeader()
		#dr.plotSpikeClip(doPhasePlot=True, fileNumber=None, region=None, myParent=None)

		# (1) first, clip out abf spikes from kymograph tif
		#    saves _clipped.tif
		#dr.new_blankAbfSpikesInTif(fileNumber=fileNumber)

		# (2) then, plot abf/tif/sparkmaster
		dr.new_plotSparkMaster()

		plt.show()
	if 0:
		# overlay lcr hist and vm
		fileNumber = 4
		new_plotSparkMaster_from_db(fileNumber)
		plt.show()

	if 0:
		# make _clipped.tif for each .tif
		new_TifReport()

	if 0:
		# merge all _clipped_sm.csv into big df and save
		# use saved .csv in bScatterPlot2.py
		makeLcrReport()

	if 0:
		# merge combined sanpy/lcr spike database from 'plot spike clip'
		# use this in fig9 to show per spike lcr slope versus eddr
		fig9MergeDatabase()

	if 1:
		# step through main lcr database and call 'spike clips' to save to sanpy analysis
		# key here, we are adding columns to saved file like:
		# (lcr slope, lcrNum, etc)
		spikeClipPlotAndSave()
