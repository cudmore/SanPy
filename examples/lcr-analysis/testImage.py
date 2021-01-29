
import os, pprint

import numpy as np
import tifffile
# %matplotlib notebook
# %matplotlib inline
import matplotlib.pyplot as plt

import pyabf

import lcranalysis

def myLoad(myDict):
	tifFile = myDict['tif']
	abfFile = myDict['abf']

	# todo: check they exist

	tif = lcranalysis.loadLineScan(tifFile)
	print('tif.shape:', tif.shape)
	print('tif.dtype:', tif.dtype)
	if len(tif.shape) == 3:
			tif = tif[:,:,1] # assuming image channel is 1
	#tif = np.rot90(tif) # rotates 90 degrees counter-clockwise
	f0 = tif.mean()
	tifNorm = tif / f0
	#print(type(tifNorm))

	tifHeader = lcranalysis.loadLineScanHeader(tifFile)
	tifHeader['shape'] = tifNorm.shape

	abf = pyabf.ABF(abfFile)

	return tif, tifHeader, abf


if __name__ == '__main__':
	dataPath = '/Users/cudmore/data/dual-lcr/'
	dataList = []
	dataList += [{
			'tif': f'{dataPath}20210122/data/20210122__0008-v2.tif',
			'abf': f'{dataPath}20210122/data/2021_01_22_0006.abf',
			}]

	fileNumber = 0
	tif, tifHeader, abf = myLoad(dataList[fileNumber])
	#tif = np.rot90(tif) # rotates 90 degrees counter-clockwise
	#plt.rcParams["figure.figsize"] = (20,10)
	plt.imshow(tif, cmap='plasma', aspect='auto')
	plt.show()
