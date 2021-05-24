"""
use original xlsx database of cells with (detection params, start, stop),
generate a large, one row per spike '_master.csv' database

saves all intermediate analysis into 'outputfolder'

this can then be plotted with bScatterPlotWidget2.py
"""
import os, sys, time

import numpy as np
import pandas as pd

#sys.path.append("..") # Adds higher directory to python modules path.
#from sanpy import bAnalysis
from sanpy import bAnalysis

def reanalyze(dbFile, outputFolder='newxxx', fixedDvDt=None, 
				noDvDtThreshold=False, fixedVmThreshold=None):
	"""
	Reanalyze all abf files in a folder following a database file

	dataPath: Full path to folder with original abf files
	dbFile: full path to comma-seperated text file with database

	Note: dbFile uses very precise column names
	"""

	startSeconds_ = time.time()

	print('=== reanalyze()')

	if not os.path.isfile(dbFile):
		print('  error')
		return

	dataPath = os.path.split(dbFile)[0]

	print('  dbFile:', dbFile)
	print('  dataPath:', dataPath)

	if dbFile.endswith('.csv'):
		df = pd.read_csv(dbFile, header=0, dtype={'ABF File': str})
	elif dbFile.endswith('.xlsx'):
		# stopped working 20201216???
		#df = pd.read_excel(dbFile, header=0, dtype={'ABF File': str})
		df=pd.read_excel(dbFile, header=0, engine='openpyxl')
	else:
		print('  reanalyze() error reading dbFile:', dbFile)
		return

	print('  reanalyze() loaded database is size:', df.shape)

	# check all columns are present
	useColList = ['ABF File', 'Condition', 'Male/Female', 'Superior/Inferior',
				'startSeconds', 'stopSeconds',
				'dvdtThreshold', 'mvThreshold', 'refractory_ms']
	for useCol in useColList:
		if not useCol in df.columns:
			# error
			print(f'  reanalyze() error: did not find column {useCol} in databasecolumns')

	# go through rows and make sure every abf file exists
	tmpFileCount = 0
	missingAbfFiles = 0
	for idx, file in enumerate(df['ABF File']):
		if str(file) in ['nan', 'NaN']:
			#print('  error: got empty row, id:', idx)
			continue
		abfFile = file + '.abf'
		abfFilePath = os.path.join(dataPath, abfFile)
		if not os.path.isfile(abfFilePath):
			print(f'  reanalyze() ERROR: row {idx}, did not find file: {abfFilePath}')
			missingAbfFiles += 1
			continue
		else:
			tmpFileCount += 1
	print(f'  reanalyze() found {tmpFileCount} abf files with {missingAbfFiles} missing files.')

	numFiles = df.shape[0]

	# make output folder
	savePath = os.path.join(dataPath, outputFolder)
	if not os.path.exists(savePath):
		os.mkdir(savePath)
		print('  reanalyze() created output folder:', savePath)
	else:
		print('  reanalyze() output folder already exists:', savePath)

	baList = []

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
			print('  reanalyze() error: did not find file:', abfFilePath)
			continue

		condition = df.iloc[idx]['Condition']

		# 20210125, only parse control conditions
		#if condition != 'ctrl':
		#	print('\n!!! skipping', idx, file, condition, '\n')
		#	continue

		#cellNumber = df.iloc[idx]['Cell Number']
		maleFemale = df.iloc[idx]['Male/Female']
		superiorInferior = df.iloc[idx]['Superior/Inferior']

		startSeconds = float(df.iloc[idx]['startSeconds'])
		stopSeconds = float(df.iloc[idx]['stopSeconds'])

		# can be None
		dvdtThreshold = df.iloc[idx]['dvdtThreshold']
		if noDvDtThreshold:
			dvdtThreshold = None
		elif fixedDvDt is not None:
			# parameter in function call to just use one
			dvdtThreshold = fixedDvDt
		elif dvdtThreshold is None or dvdtThreshold == 'None' or np.isnan(dvdtThreshold):
			dvdtThreshold = None
		else:
			# if we use this, we ALSO need minVmThreshold
			dvdtThreshold = float(dvdtThreshold)

		if fixedVmThreshold is not None:
			minVmThreshold = fixedVmThreshold
		else:
			# get from table
			minVmThreshold = float(df.iloc[idx]['mvThreshold'])
		refractory_ms = float(df.iloc[idx]['refractory_ms'])

		print('\n==reanalyze()', idx+1, 'of', numFiles)
		print('   ',  abfFilePath)
		print('   ', 'startSeconds:', startSeconds, 'stopSeconds:', stopSeconds)
		print('   ', 'dvdtThreshold:', type(dvdtThreshold), dvdtThreshold)
		print('   ', 'minVmThreshold:', type(minVmThreshold), minVmThreshold)
		print('   ', 'refractory_ms:', type(refractory_ms), refractory_ms)

		if dvdtThreshold is not None and np.isnan(minVmThreshold):
			print('  \nreanalyze() ERROR: when using dvdtThreshold we also need minVmThreshold')
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

		detectionDict = ba.getDefaultDetection()
		detectionDict['dvdtThreshold'] = dvdtThreshold
		detectionDict['mvThreshold'] = minVmThreshold
		if refractory_ms > 0:
			print('  reanalyze() using refractory_ms:', refractory_ms)
			detectionDict['refractory_ms'] = refractory_ms

		#
		# detect
		# if (dvdtThreshold is None), this will detect using min vm
		# we could also specify 'medianFilter=0, halfHeights=[20, 50, 80]'
		#ba.spikeDetect(dVthresholdPos=dvdtThreshold, minSpikeVm=minVmThreshold, verbose=False)
		ba.spikeDetect(detectionDict)

		# abb 20201110
		baList.append(ba)

		if ba.numSpikes == 0:
			# error
			print('\n  reanalyze() ERROR: 0 spikes !!!\n')
			continue

		print('  reanalyze() number of spikes detect:', ba.numSpikes)

		ba.errorReport()

		#
		# save
		saveFile = file + '_' + condition + '.xlsx'
		saveFilePath = os.path.join(savePath, saveFile)
		analysisName, df0 = ba.saveReport(saveFilePath, startSeconds, stopSeconds,
						saveExcel=False)

		if not 'include' in df0.columns:
			df0['include'] = 1

		#if idx==0:
		if masterDf is None:
			print('  reanalyze() seeding masterDf with df0', df0.shape)
			masterDf = df0
		else:
			masterDf = masterDf.append(df0, ignore_index=True)

		# increment
		totalNumberOfSpikes += ba.numSpikes
		actualNumFiles += 1
		cellNumber += 1

	# drop empy rows (convert to nan first)
	'''
	df['ABF File'].replace('', np.nan, inplace=True)
	df.dropna(subset=['ABF File'], inplace=True)
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
	# was this for reanalysis on April 12
	#masterPath += '_master_20210412.csv'
	masterPath += '_master.csv'
	print('  reanalyze() saving master csv in:', masterPath)
	masterDf.to_csv(masterPath)

	stopSeconds_ = time.time()
	elapsedSeconds = round(stopSeconds_-startSeconds_,2)
	print('  reanalyze() finished', actualNumFiles, 'files with', totalNumberOfSpikes, 'spikes in', elapsedSeconds, 'seconds')

	return baList

if __name__ == '__main__':

	#dataPath = '/Users/cudmore/box/data/laura/SAN CC'
	#dbFile = 'sanpy-analysis-database.csv'

	# using these to check Laura's manuscript analysis
	#dataPath = '/media/cudmore/data/Laura-data/manuscript-data'
	#dbFile = '/media/cudmore/data/Laura-data/Superior vs Inferior database.xlsx'

	#dbFile = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database.xlsx'
	#dataPath = '/Users/cudmore/data/laura-ephys/SAN AP'

	#dbFile = '/Users/cudmore/data/laura-ephys/sanap202101/Superior vs Inferior database.xlsx'
	#dataPath = '/Users/cudmore/data/laura-ephys/sanap202101'
	#outputFolder='new_20210412'

	# this is for manuscript
	dbFile = '/Users/cudmore/data/laura-ephys/sanap20210412/Superior vs Inferior database_13_Feb.xlsx'
	#dataPath = '/Users/cudmore/data/laura-ephys/sanap20210412'
	#outputFolder='new_20210415' # for manuscript
	outputFolder='new_20210425' # while merging into sanpy_app2.py
	fixedDvDt = None
	fixedVmThreshold = None
	noDvDtThreshold = False

	# using one dvdt to see how APD20/50/80 is affected
	'''
	dbFile = '/Users/cudmore/data/laura-ephys/sanap20210412/Superior vs Inferior database_13_Feb.xlsx'
	dataPath = '/Users/cudmore/data/laura-ephys/sanap20210412'
	outputFolder='onedvdt_20210413'
	fixedDvDt = 10 #10 #10
	noDvDtThreshold = False
	fixedVmThreshold = -40 #-20
	'''

	#baList = reanalyze(dataPath, dbFile, outputFolder='new_20210129')
	baList = reanalyze(dbFile, outputFolder=outputFolder,
						fixedDvDt=fixedDvDt, noDvDtThreshold=noDvDtThreshold,
						fixedVmThreshold=fixedVmThreshold)
