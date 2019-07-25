import os, sys, time

import pandas as pd

sys.path.append("..") # Adds higher directory to python modules path.
from SanPy import bAnalysis

def reanalyze(dataPath, dbFile):
	"""
	Reanalyze all abf files in a folder following a database file
	
	dataPath: Full path to folder with original abf files
	dbFile: full path to comma-seperated text file with database
	
	Note: dbFile has to follumn a very precise column names
	"""
	
	startSeconds_ = time.time()
	
	savePath = os.path.join(dataPath, 'NEWxxx')
	os.mkdir(savePath)
	
	df = pd.read_csv(dbFile, header=0, dtype={'ABF File': str})
	
	
	print(df[:5])
	
	numFiles = df.shape[0]
	
	actualNumFiles = 0
	totalNumberOfSpikes = 0
	for idx, file in enumerate(df['ABF File']):

		if str(file) in ['nan', 'NaN']:
			continue
		abfFile = file + '.abf'
		abfFilePath = os.path.join(dataPath, abfFile)
		if not os.path.isfile(abfFilePath):
			print('error: did not find file:', abfFilePath)
			continue

		condition = df.iloc[idx]['Condition']

		startSeconds = float(df.iloc[idx]['Start Seconds'])
		stopSeconds = float(df.iloc[idx]['Stop Seconds'])

		# can be None
		dvdtThreshold = df.iloc[idx]['dv/dt Threshold']
		if dvdtThreshold is None or dvdtThreshold == 'None':
			dvdtThreshold = None
		else:
			dvdtThreshold = int(dvdtThreshold)
		
		minVmThreshold = float(df.iloc[idx]['mV min/threshold'])
			

		print('\n', idx+1, 'of', numFiles)
		print('   ',  abfFilePath, 'startSeconds:', startSeconds, 'stopSeconds:', stopSeconds, 'dvdtThreshold:', dvdtThreshold, 'minVmThreshold:', minVmThreshold)
		
		#
		# load
		ba = bAnalysis.bAnalysis(abfFilePath)
		
		#
		# detect
		# if (dvdtThreshold is None), this will detect using min vm
		# we could also specify 'medianFilter=0, halfHeights=[20, 50, 80]'
		ba.spikeDetect(dVthresholdPos=dvdtThreshold, minSpikeVm=minVmThreshold, verbose=False)

		#
		# save
		saveFile = file + '_' + condition + '.xlsx'
		saveFilePath = os.path.join(savePath, saveFile)
		ba.saveReport(saveFilePath, startSeconds, stopSeconds)
		
		totalNumberOfSpikes += ba.numSpikes
		actualNumFiles += 1
		
	stopSeconds_ = time.time()
	print('reanalyze() finished', actualNumFiles, 'files with', totalNumberOfSpikes, 'spikes in', stopSeconds_-startSeconds_, 'seconds')
	
if __name__ == '__main__':

	dataPath = '/Users/cudmore/box/data/laura/SAN CC'
	dbFile = 'sanpy-analysis-database.csv'
	reanalyze(dataPath, dbFile)