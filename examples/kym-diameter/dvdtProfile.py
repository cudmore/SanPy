"""
Oct 3, 2023

See if we can detect rise/fall in dvdt of line profile
"""

import numpy as np
import scipy.signal

import matplotlib.pyplot as plt

import sanpy

def guessDvDtThreshold(ba : sanpy.bAnalysis) -> float:
	"""Guess the dvdt threshold as mean+std of dvdt.

	Works well for normalized [0,1] Ca++ kymograph sum.
	"""
	filteredDeriv = ba.fileLoader.filteredDeriv
	_mean = np.mean(filteredDeriv)
	_std = np.std(filteredDeriv)
	return _mean + _std

def run():
	# works
	path = '/media/cudmore/data/Dropbox/data/cell-shortening/Low resolution files_kymographs analysis/cell02_0002.tif.frames/cell02_0002_C002T001.tif'
	
	# example of different start/stop change
	path = '/media/cudmore/data/Dropbox/data/cell-shortening/fig1/06.15.22/cell 25_0002.tif.frames/cell 25_0002_C002T001.tif'

	# path = '/media/cudmore/data/Dropbox/data/cell-shortening/fig1/06.08.22/cell10.tif.frames/cell10_C002T001.tif'

	# cell goes negative
	# path = '/media/cudmore/data/Dropbox/data/cell-shortening/fig1/06.08.22/cell10_0001.tif.frames/cell10_0001_C002T001.tif'

	# cell goes negative
	# path = '/media/cudmore/data/Dropbox/data/cell-shortening/fig1/06.08.22/cell11.tif.frames/cell11_C002T001.tif'

	ba = sanpy.bAnalysis(path)

	# plotDvDt(ba)
	
	detectSpikes = 0
	if detectSpikes:
		_threshold = guessDvDtThreshold(ba)
		print('_threshold:', _threshold)

		# set detection parameters and detect
		dDict = sanpy.bDetection().getDetectionDict('Ca Kymograph')
		dDict['dvdtThreshold'] = _threshold  #0.007
		dDict['verbose'] = False
		# spike detect will also detect diameter params 'diam_*'
		ba.spikeDetect(dDict)

	ba.kymAnalysis.setAnalysisParam('imageFilterKenel', 0)
	ba.kymAnalysis.setAnalysisParam('lineFilterKernel', 3)
	ba.kymAnalysis.setAnalysisParam('lineWidth', 3)
	ba.kymAnalysis.setAnalysisParam('interpMult', 4)
	print(ba.kymAnalysis.printAnlysisParam())

	lineScanNumber = 120
	lineProfile, leftPnt, rightPnt = ba.kymAnalysis._getFitLineProfile(lineScanNumber=lineScanNumber)

	# filter line profile again
	SavitzkyGolay_pnts = 5
	SavitzkyGolay_poly = 2
	lineProfile = scipy.signal.savgol_filter(
		lineProfile,
		SavitzkyGolay_pnts,
		SavitzkyGolay_poly,
		axis=0,
		mode="nearest",
	)

	# get the first derivative
	lineDeriv = np.diff(lineProfile, axis=0)
	lineDeriv = np.append(lineDeriv, 0)  # append a point so it is same length as filteredDiam

	meanDeriv = np.nanmean(lineDeriv)
	stdDeriv = np.nanstd(lineDeriv)

	startStopFromDeriv(lineProfile)
	plt.show()
	return

	# plot
	numSubplots = 1
	fig, axs = plt.subplots(numSubplots, 1, sharex=True)
	if numSubplots == 1:
		axs = [axs]
	rightAxes = axs[0].twinx()

	axs[0].plot(lineProfile, 'k')
	rightAxes.plot(lineDeriv, 'r')
	rightAxes.axhline(y=meanDeriv, color='r', linestyle='-')
	rightAxes.axhline(y=meanDeriv+stdDeriv, color='r', linestyle='-')
	rightAxes.axhline(y=meanDeriv-stdDeriv, color='r', linestyle='-')

	plt.show()

def startStopFromDeriv(lineProfile, doPlot=False, verbose=False):

	# filter line profile again
	SavitzkyGolay_pnts = 5
	SavitzkyGolay_poly = 2
	lineProfile = scipy.signal.savgol_filter(
		lineProfile,
		SavitzkyGolay_pnts,
		SavitzkyGolay_poly,
		axis=0,
		mode="nearest",
	)

	# get the first derivative
	lineDeriv = np.diff(lineProfile, axis=0)
	lineDeriv = np.append(lineDeriv, 0)  # append a point so it is same length as filteredDiam

	midPoint = int(lineProfile.shape[0]/2)
	# print('midPoint:', midPoint)

	leftDeriv = lineDeriv[0:midPoint]
	rightDeriv = lineDeriv[midPoint:-1]

	leftMean = np.nanmean(leftDeriv)
	leftStd = np.nanstd(leftDeriv)

	rightMean = np.nanmean(rightDeriv)
	rightStd = np.nanstd(rightDeriv)

	# positive deflection in deriv
	leftThreshold = leftMean - 2 * leftStd
	
	# negative deflection in deriv
	rightThreshold = rightMean - 2 * rightStd

	whereLeft = np.asarray(leftDeriv > leftThreshold).nonzero()[0]
	if len(whereLeft) > 0:
		leftPnt = whereLeft[0]
	else:
		leftPnt = np.nan

	whereRight = np.asarray(rightDeriv < rightThreshold).nonzero()[0]
	# print('whereRight:', whereRight)
	if len(whereRight) > 0:
		rightPnt = whereRight[-1] + midPoint
	else:
		rightPnt = np.nan

	# plot
	if doPlot:
		numSubplots = 1
		fig, axs = plt.subplots(numSubplots, 1, sharex=True)
		if numSubplots == 1:
			axs = [axs]
		rightAxes = axs[0].twinx()

		axs[0].plot(lineProfile, 'k')
		axs[0].plot(leftPnt, lineProfile[leftPnt], 'oc')
		axs[0].plot(rightPnt, lineProfile[rightPnt], 'oc')
		
		rightAxes.plot(lineDeriv, 'r')

		rightAxes.axhline(y=leftMean, xmin=0, xmax=0.5, color='r', linestyle='--')
		rightAxes.axhline(y=leftMean+leftStd, xmin=0, xmax=0.5, color='r', linestyle='--')
		rightAxes.axhline(y=leftMean+2*leftStd, xmin=0, xmax=0.5, color='r', linestyle='--')

		rightAxes.axhline(y=rightMean, xmin=0.5, xmax=1, color='b', linestyle='--')
		rightAxes.axhline(y=rightMean-rightStd, xmin=0.5, xmax=1, color='b', linestyle='--')
		rightAxes.axhline(y=rightMean-2*rightStd, xmin=0.5, xmax=1, color='b', linestyle='--')

		plt.show()

	return leftPnt, rightPnt

if __name__ == '__main__':
	run()