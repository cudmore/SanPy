import matplotlib.pyplot as plt

import peakutils
from peakutils.plot import plot as pplot

import pyabf

def run(path):
	abf = pyabf.ABF(path)
	print(abf)

	x = abf.sweepX
	y = abf.sweepY

	indexes = peakutils.indexes(y, thres=3, min_dist=250, thres_abs=True)
	print('indexes:', len(indexes), indexes)
	print('xPeak:', x[indexes])
	print('yPeak:', y[indexes])
	plt.figure(figsize=(10,6))
	pplot(x, y, indexes)
	plt.title('First estimate')

	# remove baseline, never works right
	'''
	base = peakutils.baseline(y, 2)
	plt.figure(figsize=(10,6))
	plt.plot(x, y-base)
	plt.title("Data with baseline removed")
	'''
	
	plt.show()

if __name__ == '__main__':
	path = '/media/cudmore/data/colin/21n10003.abf'
	#path = '/media/cudmore/data/colin/21n10007.abf'
	#path = '/media/cudmore/data/colin/21n10008.abf'
	#path = '/media/cudmore/data/colin/21n19004-ko.abf'
	#path = '/media/cudmore/data/colin/21n19006-ko.abf'
	run(path)
