import sys, math
import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtGui, QtWidgets

import matplotlib.pyplot as plt

import sanpy
import sanpy.interface


'''
0	2020_07_30_0001.abf	2.101	156.795	0.391	-0.692	0.019	733097.683	Maybe
1	2020_08_27_0000.abf	0	103.782	0.391	-7.297	0.067	212452.573	No

2	2020_07_07_0000.abf	0.623	14.727	0.781	-7.181	1.276	18398.972	Yes
2	2020_07_07_0000.abf	16.386	28.996	1.172	-1.581	1.11	23812.62	Yes
2*	2020_07_07_0000.abf	63.342	85.077	4.492	-1.928	5.889	34645.676	No

3	2020_10_20_0000.abf	0.549	39.622	0.391	-9.657	0.102	63602.951	Maybe
4	2020_07_28_0002.abf	9.47	275.512	0.195	-6.778	0.011	1929743.374	Maybe
5	2020_07_28_0001.abf	31.494	254.605	0.195	-0.987	0.013	1750217.564	Maybe
6	2020_07_16_0000.abf	18.964	53.389	0.195	-2.16	0.32	50860.361	No
7	2020_07_16_0001.abf	0	203.776	0.195	-0.494	0.01	3216683.756	No
8	2020_07_01_0000.abf	72.828	143.56	8.203	-6.34	8.087	64906.549	No	High Freq 8Hz oscillation
9	2020_07_23_0005.abf	0.714	25.964	2.539	-4.897	0.158	42092.002	Yes
'''

def fftPlotRaw(ad):
	"""
	NOT WORKING

	ad (analysisDir)
	"""

	numFiles = len(ad)
	fig, ax = plt.subplots(numFiles, 1)

	for idx in range(len(ad)):
		# debug
		if idx == 5:
			break

		rowDict = ad.getRowDict(idx)
		file = rowDict['File']
		startSec = rowDict['Start(s)']
		stopSec = rowDict['Stop(s)']
		cellType = rowDict['Cell Type']
		noteStr = rowDict['Notes']
		if math.isnan(startSec) or math.isnan(stopSec):
			continue
		startStop = [startSec, stopSec]
		print(f'{file} startSec:{startSec} stopSec:{stopSec}')

		ba = ad.getAnalysis(idx)

		sweepX = ba.sweepX
		sweepY = ba.sweepY
		ax[idx].plot(sweepX, sweepY, '-', linewidth=1)

	#
	plt.show()

def fftPlotResults(resultList):
	"""
	"""
	numResults = len(resultList)
	maxFreq = [result['maxFreq'] for result in resultList]
	maxPSD = [result['maxPSD'] for result in resultList]

	# color markers based on cell type ('superior', 'inferior')
	cellTypeList = [result['Cell Type'] for result in resultList]
	# too complicated for list comprehension
	#colorList = ['k' if cellType=='inferior' else 'r' for cellType in cellTypeList]
	colorList = []
	for cellType in cellTypeList:
		if cellType == 'superior':
			theColor = 'r'
		elif cellType == 'inferior':
			theColor = 'k'
		else:
			theColor = 'b'
		colorList.append(theColor)
	#print('colorList:', colorList)

	# marker label points with file index
	markers = [i for i in range(len(maxFreq))]

	fig, ax = plt.subplots(1, 1)

	ax.scatter(maxFreq, maxPSD, marker='.', c=colorList)
	for i in range(len(maxFreq)):
		oneFreq = maxFreq[i]
		onePsd = maxPSD[i]
		oneMarker = markers[i]
		xyOffset = 0.05  # So we can see the numbers away from the markers
		ax.text(oneFreq+xyOffset, onePsd+xyOffset, str(oneMarker), color=colorList[i], fontsize=10)

	ax.grid()  # show grid lines
	ax.spines['right'].set_visible(False)
	ax.spines['top'].set_visible(False)

	ax.set_xlabel('Peak Frequency (Hz)')
	ax.set_ylabel('Power (dB)')

	#
	# make a pandas dataframe with all info and save as csv
	df = pd.DataFrame(resultList)
	printColumns = ['file', 'startSec', 'stopSec', 'maxFreq', 'maxPSD', 'Cell Type', 'Notes']
	print('=== df')
	#print(df[printColumns])

	columnsStr = ''
	for column in printColumns:
		columnsStr += column + '\t'
	print(columnsStr)

	def applytab(row):
		print('\t'.join(map(str,row.values)))
	#print('\t'.join(map(str,df.columns))) # to print the column names if required
	df[printColumns].apply(applytab,axis=1)

	#
	# plot each (freq,psd)
	# I am hard-coding row/col of subplots based on ~15 files
	numRow = 5
	numCol = 3
	if numRow*numCol < numResults:
		print('error in numRow numCol')
	fig2, ax2 = plt.subplots(numRow, numCol)
	row = 0
	col = 0
	minPlotPower = 10e9
	maxPlotPower = -10e9
	for resultIdx, result in enumerate(resultList):
		cellType = result['Cell Type']
		if cellType == 'superior':
			markerColor = 'r'
		elif cellType == 'inferior':
			markerColor = 'k'
		elif cellType == 'no-cell':
			markerColor = 'b'
		marker = '-' + markerColor
		label = f"{resultIdx} {result['file']} [{result['startSec']}, {result['stopSec']}]"
		ax2[row,col].plot(result['freqs'], result['psd'], marker, linewidth=0.5)
		ax2[row,col].plot(result['maxFreq'], result['maxPSD'], '.r', label=label)
		ax2[row,col].spines['right'].set_visible(False)
		ax2[row,col].spines['top'].set_visible(False)
		ax2[row,col].set_title(label, fontdict={'fontsize':10})  # title the subplot
		lastResult = row == (numRow - 1)
		if not lastResult:
			#ax2[resultIdx].spines['bottom'].set_visible(False)
			ax2[row,col].tick_params(axis="x", labelbottom=False) # no labels
		if lastResult and col==0:
			ax2[row,col].set_xlabel('Frequency (Hz)')
			ax2[row,col].set_ylabel('Power (dB)')
		#
		# keep track of y-axis min/max
		oneMinPsd = np.nanmin(result['psd'])
		oneMaxPsd = np.nanmax(result['psd'])
		if oneMinPsd < minPlotPower:
			minPlotPower = oneMinPsd
		if oneMaxPsd > maxPlotPower:
			maxPlotPower = oneMaxPsd
		#
		# increment
		row += 1
		if row > numRow-1:
			row = 0
			col += 1
	#
	# set all y-axis to the same min/max
	# expand by percent
	yExpand = abs(maxPlotPower-minPlotPower) * 0.05
	maxPlotPower += yExpand
	minPlotPower -= yExpand
	for row in range(numRow):
		for col in range(numCol):
			ax2[row,col].set_ylim([minPlotPower, maxPlotPower])

	#
	# show all plots
	plt.show()

if __name__ == '__main__':
	if 0:
		# plot peak freq vs power and compare no butter to butter
		fftPlotResults2()
		sys.exit(1)

	app = QtWidgets.QApplication(sys.argv)

	#path = '/Users/cudmore/Sites/SanPy/data/fft'
	path = '/home/cudmore/Sites/SanPy/data/fft'
	ad = sanpy.analysisDir(path)

	fftPlotRaw(ad)
	sys.exit(1)

	realIdx = 0
	for idx in range(len(ad)):
		# debug
		if idx == 5:
			break

		rowDict = ad.getRowDict(idx)
		file = rowDict['File']
		startSec = rowDict['Start(s)']
		stopSec = rowDict['Stop(s)']
		cellType = rowDict['Cell Type']
		noteStr = rowDict['Notes']
		if math.isnan(startSec) or math.isnan(stopSec):
			continue
		startStop = [startSec, stopSec]
		print(f'{file} startSec:{startSec} stopSec:{stopSec}')

		ba = ad.getAnalysis(idx)
		if ba.loadError:
			print('  file error:', fileName)
			continue
		fileName = ba.getFileName()

		if realIdx == 0:
			# seed first
			fftPlugin = sanpy.interface.plugins.fftPlugin(ba=ba, startStop=startStop)
		else:
			fftPlugin.slot_switchFile2(ba, startStop, fileTableRowDict=rowDict)

		#
		# add key/value to last entry in fftPlugin._resultsDictList
		lastResultIdx = len(fftPlugin._resultsDictList) - 1
		fftPlugin._resultsDictList[lastResultIdx]['Cell Type'] = cellType
		fftPlugin._resultsDictList[lastResultIdx]['Notes'] = noteStr

		#input('Press Enter To Go To Next File!')
		realIdx += 1

	'''
	resultsStr = fftPlugin.getResultStr()
	print('BINGO!')
	print(resultsStr)
	'''
	resultList = fftPlugin.getResultsDictList()
	print('=== resultList')
	for result in resultList:
		print(result)

	fftPlotResults(resultList)

	#app.exec_()
	app.quit()
	sys.exit(1)
