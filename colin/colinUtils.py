"""
"""

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns

# for baseline
from scipy import sparse
from scipy.sparse.linalg import spsolve

def baseline_als_optimized(y, lam, p, niter=10):
	"""
	p for asymmetry and lam for smoothness.
	generally:
		0.001 ≤ p ≤ 0.1
		10^2 ≤ lam ≤ 10^9

	see: https://stackoverflow.com/questions/29156532/python-baseline-correction-library
	"""
	L = len(y)
	D = sparse.diags([1,-2,1],[0,-1,-2], shape=(L,L-2))
	D = lam * D.dot(D.transpose()) # Precompute this term since it does not depend on `w`
	w = np.ones(L)
	W = sparse.spdiags(w, 0, L, L)
	for i in range(niter):
		W.setdiag(w) # Do not create a new matrix, just update diagonal values
		Z = W + D
		z = spsolve(Z, w*y)
		w = p * (y > z) + (1-p) * (y < z)
	return z

def joydivision():
	# see: https://stackabuse.com/matplotlib-turn-off-axis-spines-ticklabels-axislabels-grid/
	# see: https://blogs.scientificamerican.com/sa-visual/pop-culture-pulsar-the-science-behind-joy-division-s-unknown-pleasures-album-cover/
	df = pd.read_csv(r"https://raw.githubusercontent.com/StackAbuse/CP1919/master/data-raw/clean.csv")
	groups = df.groupby(['line'])

	plt.style.use('dark_background')
	fig = plt.figure(figsize=(6, 8))

	ax = fig.add_subplot(111)
	ax.set_xlabel('Time')
	ax.set_ylabel('Intensity')

	ax.get_xaxis().set_visible(False)
	ax.get_yaxis().set_visible(False)

	for group in groups:
	    line = ax.plot(group[1]['x'], group[1]['y'], color='white')

	#plt.show()

'''
def getStats(df):
	# todo: change df as we accept/reject

	theseStats = ["count", "min", "max", "median", "mean", "std", "sem"]
	dfAgg = df.agg(
		{
			'ipi_ms': theseStats,
			'instFreq_hz': theseStats,
			'height': theseStats,
			'half_width_ms': theseStats,
			'myHeight': theseStats,
		}
	)
	dfAgg['file'] = df.loc[0, 'file']

	# check we got just one file

	return dfAgg
'''

def getAxis(axs=None):
	if axs is None:
		numSubplot = 1
		fig, axs = plt.subplots(numSubplot, 1, figsize=(8, 6))
	return axs

def plotRaw(x, y, c=None, xRange=None, axs=None):
	"""
	x: time values (usually seconds)
	y:
	"""
	axs = getAxis(axs)

	if xRange is not None:
		print('using xRange:', xRange)
		xMask = (x>=xRange[0]) & (x<=xRange[1])
		x = x[xMask]
		y = y[xMask]

	if c is not None:
		rightAxs = axs.twinx()
		if xRange is not None:
			c = c[xMask]
		rightAxs.plot(x, c, c='r', linewidth=0.5)
		rightAxs.spines['right'].set_visible(True)

	# plot lastso mouse reports raw data (last thing plotted)
	axs.plot(x, y, c='k', linewidth=0.5)


def plotHist(df, colStat, hue=None, binWidth=None, kde=False, axs=None):

	if axs is None:
		numSubplot = 1
		fig, axs = plt.subplots(numSubplot, 1, figsize=(8, 6))

	axs = sns.histplot(data=df, x=colStat, hue=hue, ax=axs, binwidth=binWidth, kde=kde)
	'''
	axs = sns.histplot(data=df, x=colStat, hue=hue, ax=axs, binwidth=binWidth, kde=kde,
					element="step", fill=False,
					cumulative=True,
					stat="density",
					common_norm=False)
	'''

	return axs

def reduceDf(df, reduceDict):
	"""
	Keep only rows specified by reductDict

	Args:
		df (dataframe):
		reduceDict (dict):

	Returns:
		df reduced by rows.

	Notes:
		theseRowDf = df[ (df['peak_sec']>=xMin) & (df['peak_sec']<=xMax)]
	"""
	retDf = df.copy(deep=True)

	for k,v in reduceDict.items():
		#print('  k:', k, 'v:', v)
		for k2,v2 in v.items():
			#print('	k2:', k2, 'v2:', v2)
			if k2=='min' and v2 is not None:
				try:
					retDf = retDf[ retDf[k] >= v2 ]
				except (KeyError) as e:
					print('error: did not find key:', k)
			if k2=='max' and v2 is not None:
				try:
					retDf = retDf[ retDf[k]<=v2 ]
				except (KeyError) as e:
					print('error: did not find key:', k)
			if k2=='bool':
				# keep True/False
				try:
					retDf = retDf[ retDf[k]==v2 ]
				except (KeyError) as e:
					print('error: did not find key:', k)

	#
	return retDf

def testPlotRaw(ca):
	# plot raw with (y, dc command, threshold)
	numFiles = ca.numFiles
	fig, axs = plt.subplots(numFiles, 1, sharex=True, figsize=(8, 6))
	if numFiles == 1:
		axs = [axs]
	for myFileIdx in range(numFiles):
		# plot all raw data
		ca.setAnalysisIdx(myFileIdx)
		df = ca.getDataFrame()
		x = ca.sweepX
		#y = ca.sweepY
		y = ca.sweepY_filtered
		c = ca.sweepC
		analysis = ca.getAnalysis()
		file = analysis['file']
		xRange = analysis['detection']['xRange']
		height = analysis['detection']['height']  # absolute threshold in pA

		plotRaw(x, y, c=None, xRange=xRange, axs=axs[myFileIdx])
		axs[myFileIdx].set_title(file)
		#axs[myFileIdx].hlines(4, color='b')
		axs[myFileIdx].axhline(height, color='b', linewidth=0.5, linestyle='--')

		# overlay (peak, foot)
		xFoot = df['xFoot']
		yFoot = df['yFoot']
		axs[myFileIdx].scatter(xFoot, yFoot, c='g', s=3, zorder=999)
		peak_sec = df['peak_sec']
		peak_val = df['peak_val']
		axs[myFileIdx].scatter(peak_sec, peak_val, c='r', s=3, zorder=999)

		#
		# half widths
		halfWidths = [20, 50, 80]
		for halfWidth in halfWidths:
			keyBase = 'hw' + str(halfWidth) + '_'
			left_sec = df[keyBase+'left_sec']
			right_sec = df[keyBase+'right_sec']
			val = df[keyBase+'val']
			axs[myFileIdx].hlines(val, left_sec, right_sec, color='b')

def testBaseline(ca):
	x = ca.sweepX
	#y = ca.sweepY
	y = ca.sweepY_filtered

	analysis = ca.getAnalysis()
	file = analysis['file']
	xRange = analysis['detection']['xRange']
	mask = (x>=xRange[0]) & (x<=xRange[1])
	x = x[mask]
	y = y[mask]

	lam = 1e13
	p = 0.5
	z = baseline_als_optimized(y, lam, p, niter=10)
	zBase = y - z
	"""
	p for asymmetry and lam for smoothness.
	generally:
		0.001 ≤ p ≤ 0.1
		10^2 ≤ lam ≤ 10^9
	"""

	numFiles = 2
	fig, axs = plt.subplots(numFiles, 1, sharex=True, figsize=(14, 10))
	if numFiles == 1:
		axs = [axs]

	axs[0].plot(x, y, linewidth=0.5, c='k')
	axs[0].plot(x, z, linewidth=0.5, c='r')

	axs[1].plot(x, zBase, linewidth=0.5, c='g')

	axs[0].set_title(file)

def testRun():
	from colinAnalysis import colinAnalysis

	path = '/media/cudmore/data/colin'
	ca = colinAnalysis(path)

	# detect all files in folder
	defaultThreshold = 6  # pA
	numFiles = ca.numFiles
	for fileNum in range(numFiles):
		xRange = None
		ca.setAnalysisIdx(fileNum)
		detectionDict = ca.getDefaultDetection()
		if fileNum == 0:
			detectionDict['xRange'] = [1.312, 49]
			detectionDict['height'] = defaultThreshold
		if fileNum == 1:
			detectionDict['xRange'] = [1.312, 81.287]
			detectionDict['height'] = defaultThreshold
		if fileNum == 3:
			detectionDict['xRange'] = [0, 50]
			detectionDict['height'] = defaultThreshold
		if fileNum == 4:
			detectionDict['xRange'] = [0, 55]
			#detectionDict['height'] = 7
			detectionDict['height'] = defaultThreshold
		# detect
		ca.detect(detectionDict)

		print(ca.getStats())
	#
	df = ca.getAllDataFrame()

	# when we reduce height, we remove peaks and change (lower) the frequency
	reduceDict = {
		'myHeight': {
			'min': None,
			'max': 20,
		},
		'accept': {
			'bool': True,
		}
	}
	df2 = reduceDf(df, reduceDict)

	numSubplot = ca.numFiles
	fig, axs = plt.subplots(numSubplot, 1, sharex=True, figsize=(8, 6))
	fig2, axs2 = plt.subplots(numSubplot, 1, sharex=True, figsize=(8, 6))
	for myFileIdx in range(ca.numFiles):
		tmpDf = df2[ df2['myFileIdx']==myFileIdx]
		plotHist(tmpDf, 'myHeight', hue='file', kde=True, binWidth=0.5, axs=axs[myFileIdx])
		plotHist(tmpDf, 'instFreq_hz', hue='file', kde=True, binWidth=0.5, axs=axs2[myFileIdx])

	# plot raw
	testPlotRaw(ca)

	#joydivision()

	#testBaseline(ca)

	#
	plt.show()

if __name__ == '__main__':
	testRun()
	
