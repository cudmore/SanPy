"""
Author: Robert Cudmore
Date: 20211221

Purpose: Load a csv, massage it, and plot.
"""

import pandas as pd
import matplotlib.pyplot as plt

def plotOneFile(df, filename : str):
	"""
	Plot each file in a figure with subplots corresponding to sweep

	Args:
		df (dataframe): Pandas dataframe with columns ['filename', 'sweeps', peakPhase']
		filename (str): Name of file to plot.

	Notes:
		This is bad form as I am mixing code for plotting and analysis.
	"""

	dfFile = df[ df['filename']==filename ]  # grab specified filename
	sweeps = dfFile['sweep'].unique()  # get list of sweeps [0, 1, 2, ...]

	numSubplot = len(sweeps)
	fig, axs = plt.subplots(numSubplot, 1, sharex=True, figsize=(8, 6))
	fig.suptitle(filename)

	for idx,sweep in enumerate(sweeps):
		dfSweep = dfFile[ dfFile['sweep'] == sweep]  # grab one sweep from one file
		peakPhase = dfSweep['peakPhase']  # grab the raw data

		# selecting appropriate bins is important
		# lots of different algorithms, not sure which one is best
		# see: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.hist.html
		bins = 'auto'

		# plot the histogram and grab its data
		counts, bins, bars = axs[idx].hist(peakPhase, bins=bins)

		#
		# TODO: Do a sine fit of x=bins and y=counts
		#

		axs[idx].set_ylabel('Count')
		axs[idx].set_xlabel('Phase')  # This is phase within a sin wave (we don't know the frequency)

def run(path : str):
	"""
	Each 'filename' is a different recording
		Within each recording we have a number of different sweeps ('sweep')
			Within each sweep are 'peakPhase' values to analyze/fit

	Args:
		path (str): Full path to csv file for analysis.
	"""

	# load the file
	df = pd.read_csv(path)

	# check the format of loaded csv
	print(f'this is what our loaded file looks like, it has {len(df)} rows.')
	print(df.head())

	# print some stats
	aggList = ['count', 'median', 'mean', 'std', 'min', 'max']
	dfTmp = df.groupby(['filename', 'sweep']).agg(aggList)
	print('')
	print("and here it is grouped by ['filename', 'sweep'] ...")
	print(dfTmp)

	# plot each file in a figure with subplots corresponding to sweep
	filenames = df['filename'].unique()
	for filename in filenames:
		plotOneFile(df, filename)

	#
	plt.show()

if __name__ == '__main__':
	if 0:
		#
		# change this to location of your csv file
		#
		path = '/home/cudmore/Sites/SanPy/colin/gianni-master.csv'

		run(path)

	if 1:
		from colinAnalysis import bAnalysis2
		from colinAnalysis import colinAnalysis2

		path = '/media/cudmore/data/stoch-res/new20220104'
		ca2 = colinAnalysis2(path)
		
		dDict = bAnalysis2.getDefaultDetection()
		dDict['doBaseline'] = False
		for file in ca2:
			file.detect(dDict)
		df = ca2.asDataFrame()
		print('saving tmpCell-db.csv')
		df.to_csv('tmpCell-db.csv')