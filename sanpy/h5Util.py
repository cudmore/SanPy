import time
import pandas as pd

import logging
logging.getLogger('numexpr').setLevel(logging.WARNING)

import sanpy.bAnalysis

def listKeys(hdfPath):
	"""List all keys in h5 file."""
	with pd.HDFStore(hdfPath, mode='r') as store:
		print(store)
		for key in store.keys():
			print('=== key:', key, 'type:', type(store[key]))
			print(store[key])

def loadAnalysis(hdfPath):
	"""Load all bAnalysis from h5"""
	print('=== loadAnalysis hdfPath:', hdfPath)
	start = time.time()
	numLoaded =0
	with pd.HDFStore(hdfPath, mode='r') as store:
		for key in store.keys():
			data = store[key]
			if isinstance(data, pd.DataFrame):
				if '_sweepX' in data.columns:
					ba = sanpy.bAnalysis(fromDf=data)
					print('    ', ba)
					numLoaded += 1
				else:
					# this is usually the file database
					print('Dur(s):')
					print(store[key]['Dur(s)'])
					# the entire file db df
					print(data)
	#
	stop = time.time()
	print(f'Loading {numLoaded} bAnalysis took {round(stop-start,3)} seconds.')

if __name__ == '__main__':
	hdfPath = '/home/cudmore/Sites/SanPy/data/sanpy_recording_db.h5'
	#listKeys(hdfPath)
	loadAnalysis(hdfPath)

	# the file befor compression
	'''
	hdfPath = '/home/cudmore/Sites/SanPy/data/sanpy_recording_db_tmp.h5'
	loadAnalysis(hdfPath)
	'''
