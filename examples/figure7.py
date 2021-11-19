
import numpy as np
import matplotlib.pyplot as plt  # just to show plots during script
import seaborn as sns

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def printStats(theName, theArray):
	"""
	theName (str):
	theArray (ndarray):
	"""
	print(f'{theName} len:{len(theArray)} type:{type(theArray)}, dtype:{theArray.dtype} mean:{np.nanmean(theArray)} min:{np.nanmin(theArray)}, max:{np.nanmax(theArray)} {theArray}')

def run():
	# load from '/media/cudmore/data/laura-iso'

	# list of files to analyze
	aDict = {
		'19503001': {
			'path': '/media/cudmore/data/laura-iso/19503001.abf',
			'detectionType': 'dvdt',
			'dvdtThreshold': 60,  # chosen by visual inspection
			'controlSec': [10, 90],
			'isoSec': [210, 300],
		},
		'19503006': {
			'path': '/media/cudmore/data/laura-iso/19503006.abf',
			'detectionType': 'dvdt',
			'dvdtThreshold': 18,  # chosen by visual inspection
			'controlSec': [10, 90],
			'isoSec': [180, 270],
		},
		'20191122_0001': {
			# IMPORTANT: The recording chagegd too much in this recording !!!!
			# these changes are not due to ISO and in opposite direction from expected (which is good)!!!
			'path': '/media/cudmore/data/laura-iso/20191122_0001.abf',
			'detectionType': 'mv',
			#'dvdtThreshold': 50,
			'mvThreshold': -40,
			'controlSec': [10, 90],
			'isoSec': [380, 470],
		},
	}

	baList = []
	for file, params in aDict.items():

		filePath = params['path']
		detectionType = params['detectionType']
		controlSec = params['controlSec']
		isoSec = params['isoSec']

		# load
		ba = sanpy.bAnalysis(filePath)

		# analyze spikes
		detectionClass = ba.detectionClass
		detectionClass['verbose'] = False
		if detectionType == 'dvdt':
			detectionClass['detectionType'] = sanpy.bDetection.detectionTypes.dvdt
		elif detectionType == 'mv':
			detectionClass['detectionType'] = sanpy.bDetection.detectionTypes.mv
		ba.spikeDetect(detectionClass)
		baList.append(ba)

		# grab results as a pandas dataframe
		#df = ba.dfReportForScatter
		df = ba.asDataFrame()

		# todo: merge into big dataframe, add column 'myCellNumber'

		# pull control versus drug stats based on time
		# could do this as well
		#thresholdSec = ba.getStat('thresholdSec', asArray=True)

		# boolean mask based on a time window
		thresholdSec = df['thresholdSec']
		controlMask = (thresholdSec>controlSec[0]) & (thresholdSec<controlSec[1])
		isoMask = (thresholdSec>isoSec[0]) & (thresholdSec<isoSec[1])

		df['myCondition'] = 'None'
		df['myCondition'] = np.where(controlMask, 'Control', df['myCondition'])
		df['myCondition'] = np.where(isoMask, 'Iso', df['myCondition'])

		# drop any remaining datapoint (rows) with myCondition == 'None'
		dfPlot = df.drop(df[df['myCondition'] == 'None'].index)

	#
	# plot one ba
	ba = baList[0]


	palette = {
		"Control": "k",
		"Iso": "r",
		"None": "#dddddd",
		}

	# create an analysis plot object from one ba
	ap = sanpy.bAnalysisPlot(ba)

	# plot time series of vm and dvdt
	fig, axs = ap.plotDerivAndRaw()

	# analysis results as a time-series
	statName = 'thresholdVal'
	sns.scatterplot(x='thresholdSec', y=statName, hue='myCondition', palette=palette, data=df, ax=axs[0])


	plt.show()

	# as a category
	#sns.catplot(x="myCondition", y=statName, kind="swarm", data=dfPlot)

	statName = 'widths_50'
	sns.swarmplot(x='myCondition', y=statName, palette=palette, data=dfPlot, zorder=1)
	sns.pointplot(x='myCondition', y=statName, palette=palette, data=dfPlot, ci=68)


	plt.show()


	#
	# plot
	# !!!

if __name__ == '__main__':
	run()
