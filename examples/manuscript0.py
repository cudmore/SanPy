
"""
20201110

This will plot stats (like spike freq) between superior (0) and inferior (1)
color will be condition with ctrl black and iso red

This is two step
	1) python reanalyze to make a new .csv with columns like aSpikeFreq_m
	2) run the code here to step through list of [condition] and [superior/inferior]
		and make the plot
"""

import numpy as np
import pandas as pd

import matplotlib as mpl
import matplotlib.pyplot as plt

import reanalyze

def doReAnalyze(dataPath, dbFile):
	"""
	analyze a number of files
	"""
	baList = reanalyze.reanalyze(dataPath, dbFile)

	# todo: have reanaize make/return a df with one row per file, and columns ['aMeanFreq']

	for ba in baList:
		xStat = 'spikeFreq_hz'
		yStat = 'spikeFreq_hz'
		xData, yData = ba.getStat(xStat, yStat, xToSec=True)
		#print('x:', x)
		xMean = np.nanmean(xData)
		xMean *= 1000

		# all spikes in the same bas have condition 1/2/3 the same
		condition1 = ba.spikeDict[0]['condition1'] # condition
		condition2 = ba.spikeDict[0]['condition2'] # cell number
		condition3 = ba.spikeDict[0]['condition3'] # male/female
		condition4 = ba.spikeDict[0]['condition4'] # superio/inferior

		print(condition1, condition2, condition3, condition4, xMean)

if __name__ == '__main__':


	# do this once to make analysis and save a new csv like
	#    /media/cudmore/data/Laura-data/Superior vs Inferior database_analysis.csv
	if 0:
		dataPath = '/media/cudmore/data/Laura-data/manuscript-data'
		dbFile = '/media/cudmore/data/Laura-data/Superior vs Inferior database.xlsx'
		doReAnalyze(dataPath, dbFile)
		# this generates a new .csv called _analysis.csv (using original database.xlsx as a template

	if 1:
		# load _analysis.csv and make plots
		analysisFile = '/media/cudmore/data/Laura-data/Superior vs Inferior database_analysis.csv'
		df = pd.read_csv(analysisFile, header=0, dtype={'ABF File': str})

		print('loaded analysisFile:', analysisFile)
		print(df[ ['ABF File', 'Condition', 'Superior/Inferior', 'aSpikeFreq_n', 'aSpikeFreq_m', 'aSpikeFreq_cv'] ])

		# step through df and pull numbers based on (Condition, Superior/Inferior)
		colorList = ['k', 'r'] # (ctrl, ISO 100nm)
		symbolList = ['o', 'v']
		columnList = [0, 1] # superior inferior

		# x-axis will be 0/1 superior inferior

		conditionList = ['ctrl', 'ISO 100nM']
		regionList = ['Superior', 'Inferior']

		# build up lists to plot

		finalStatList = ['aSpikeFreq_n', 'aSpikeFreq_m', 'aSpikeFreq_cv']

		#defaultPlotLayout()
		nStat = len(finalStatList)
		fig,axs = plt.subplots(1, nStat, figsize=(12,5)) # need constrained_layout=True to see axes titles

		for statNameIdx, finalStatName in enumerate(finalStatList):
			axs[statNameIdx].set_ylabel(finalStatName)
			for conditionIdx, condition in enumerate(conditionList):
				color = colorList[conditionIdx]
				for regionIdx, region in enumerate(regionList):
					a = df[df['Condition']==condition]
					a = a[a['Superior/Inferior']==region]

					# todo: check if len==0
					# len() here is giving me number of cells
					'''
					nStat = len(a['aSpikeFreq_n'].tolist())
					if nStat < 20:
						print('  rejecting', condition, region, 'n=', nStat)
						continue
					'''

					theStat = a[finalStatName]

					#print('condition:', condition, 'region:', region, 'stat:', finalStatName)
					#print('  ', theStat.tolist())

					statList = theStat.tolist()
					nStatList = len(statList)

					# each (condition, region) get its own list
					xAxis = np.random.rand(nStatList) / 5 + regionIdx #[regionIdx] * len(statList)
					symbol = symbolList[regionIdx]
					axs[statNameIdx].plot(xAxis, statList, symbol, color=color)

		# do the plot
		plt.show()
