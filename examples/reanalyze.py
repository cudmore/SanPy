import os, sys, time

import numpy as np
import pandas as pd

sys.path.append("..") # Adds higher directory to python modules path.
from sanpy import bAnalysis

def reanalyze(dataPath, dbFile):
	"""
	Reanalyze all abf files in a folder following a database file

	dataPath: Full path to folder with original abf files
	dbFile: full path to comma-seperated text file with database

	Note: dbFile uses very precise column names
	"""

	startSeconds_ = time.time()

	print('=== reanalyze()')
	print('  dataPath:', dataPath)
	print('  dbFile:', dbFile)

	savePath = os.path.join(dataPath, 'NEWxxx')
	if not os.path.exists(savePath):
		os.mkdir(savePath)
		print('created output folder:', savePath)
	else:
		print('output folder already exists:', savePath)

	if dbFile.endswith('.csv'):
		df = pd.read_csv(dbFile, header=0, dtype={'ABF File': str})
	elif dbFile.endswith('.xlsx'):

		# stopped working 20201216???
		#df = pd.read_excel(dbFile, header=0, dtype={'ABF File': str})

		df=pd.read_excel(
				dbFile,
				header=0,
				engine='openpyxl',
				)
	else:
		print('error reading dbFile:', dbFile)

	print('loaded database is:')
	print(df[:5])

	numFiles = df.shape[0]

	baList = []

	# keep list of new stats to add to df
	'''
	nFreqList = []
	meanFreqList = []
	sdFreqList = []
	seFreqList = []
	cvFreqList = []
	'''

	actualNumFiles = 0
	totalNumberOfSpikes = 0
	cellNumber = 1
	masterDf = None
	for idx, file in enumerate(df['ABF File']):

		if str(file) in ['nan', 'NaN']:
			#print('  error: got empty row, id:', idx)
			continue
		abfFile = file + '.abf'
		abfFilePath = os.path.join(dataPath, abfFile)
		if not os.path.isfile(abfFilePath):
			print('  error: did not find file:', abfFilePath)
			continue

		condition = df.iloc[idx]['Condition']
		#cellNumber = df.iloc[idx]['Cell Number']
		maleFemale = df.iloc[idx]['Male/Female']
		superiorInferior = df.iloc[idx]['Superior/Inferior']

		startSeconds = float(df.iloc[idx]['Start Seconds'])
		stopSeconds = float(df.iloc[idx]['Stop Seconds'])

		# can be None
		dvdtThreshold = df.iloc[idx]['dv/dt Threshold']
		if dvdtThreshold is None or dvdtThreshold == 'None' or np.isnan(dvdtThreshold):
			dvdtThreshold = None
		else:
			# if we use this, we ALSO need minVmThreshold
			dvdtThreshold = float(dvdtThreshold)

		minVmThreshold = float(df.iloc[idx]['mV min/threshold'])

		print('\n', idx+1, 'of', numFiles)
		print('   ',  abfFilePath)
		print('   ', 'startSeconds:', startSeconds, 'stopSeconds:', stopSeconds)
		print('   ', 'dvdtThreshold:', type(dvdtThreshold), dvdtThreshold)
		print('   ', 'minVmThreshold:', type(minVmThreshold), minVmThreshold)

		if dvdtThreshold is not None and np.isnan(minVmThreshold):
			print('  \nERROR: when using dvdtThreshold we also need minVmThreshold')
			print('  dvdtThreshold:', dvdtThreshold)
			print('  minVmThreshold:', minVmThreshold)
			print('\n')
			continue
		#
		# load
		ba = bAnalysis(abfFilePath)

		#
		# set (condition 1, condition 2, condition 3')
		# need to do this for analysis, gets stored in each spike
		ba.condition1 = condition
		ba.condition2 = cellNumber
		ba.condition3 = maleFemale
		ba.condition4 = superiorInferior

		#
		# detect
		# if (dvdtThreshold is None), this will detect using min vm
		# we could also specify 'medianFilter=0, halfHeights=[20, 50, 80]'
		ba.spikeDetect(dVthresholdPos=dvdtThreshold, minSpikeVm=minVmThreshold, verbose=False)

		# abb 20201110
		baList.append(ba)

		if ba.numSpikes == 0:
			# error
			print('\n  ERROR: 0 spikes !!!\n')
			continue

		print('    number of spikes detect:', ba.numSpikes)

		#
		# save
		saveFile = file + '_' + condition + '.xlsx'
		saveFilePath = os.path.join(savePath, saveFile)
		df0 = ba.saveReport(saveFilePath, startSeconds, stopSeconds,
						saveExcel=False)

		#if idx==0:
		if masterDf is None:
			masterDf = df0
		else:
			masterDf = masterDf.append(df0, ignore_index=True)

		#
		# add columns to df and then save as new csv
		# use this csv to make pivot table plot
		'''
		xStat = 'spikeFreq_hz'
		yStat = 'spikeFreq_hz'
		xData, yData = ba.getStat(xStat, yStat, xToSec=True)
		nIntervals = np.count_nonzero(~np.isnan(xData))
		xMean = np.nanmean(xData)
		xMean *= 1000
		xSD = np.nanstd(xData)
		xSD *= 1000
		xCV = xSD / xMean
		#df['aMeanSpikeFreq'] = xMean
		nFreqList.append(nIntervals)
		meanFreqList.append(xMean)
		sdFreqList.append(xSD)
		cvFreqList.append(xCV)
		'''

		# increment
		totalNumberOfSpikes += ba.numSpikes
		actualNumFiles += 1
		cellNumber += 1

	# drop empy rows (convert to nan first)
	'''
	df['ABF File'].replace('', np.nan, inplace=True)
	df.dropna(subset=['ABF File'], inplace=True)
	'''

	# append columns to df
	'''
	df['aSpikeFreq_n'] = nFreqList
	df['aSpikeFreq_m'] = meanFreqList
	df['aSpikeFreq_sd'] = sdFreqList
	df['aSpikeFreq_cv'] = cvFreqList
	'''

	#
	# save the df in a new file
	'''
	tmpPath, tmpExt = os.path.splitext(dbFile)
	tmpPath += '_analysis.csv'
	print('reanalyze() saving new csv in:', tmpPath)
	df.to_csv(tmpPath)
	'''

	masterPath, tmpExt = os.path.splitext(dbFile)
	masterPath += '_master.csv'
	print('reanalyze() saving master csv in:', masterPath)
	masterDf.to_csv(masterPath)

	stopSeconds_ = time.time()
	elapsedSeconds = round(stopSeconds_-startSeconds_,2)
	print('reanalyze() finished', actualNumFiles, 'files with', totalNumberOfSpikes, 'spikes in', elapsedSeconds, 'seconds')

	return baList

if __name__ == '__main__':

	#dataPath = '/Users/cudmore/box/data/laura/SAN CC'
	#dbFile = 'sanpy-analysis-database.csv'

	# using these to check Laura's manuscript analysis
	#dataPath = '/media/cudmore/data/Laura-data/manuscript-data'
	#dbFile = '/media/cudmore/data/Laura-data/Superior vs Inferior database.xlsx'

	dbFile = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database.xlsx'
	dataPath = '/Users/cudmore/data/laura-ephys/SAN AP'

	baList = reanalyze(dataPath, dbFile)
