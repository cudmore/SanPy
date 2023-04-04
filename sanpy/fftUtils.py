"""sanpy fft backend.

TODO:
	- get rid of (spikeDetect, _getHalfWidths, _throwOutRefractory)
		- these are used to spike detect model data
		- try and use main bAnalysis_
"""

import math, time, os
from math import exp
from functools import partial
from tokenize import blank_re

import numpy as np
import pandas as pd

from scipy.signal import lfilter, freqz
import scipy.signal

import matplotlib as mpl
import matplotlib.pyplot as plt

import sanpy

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


def butter_sos(cutOff, fs, order=50, passType="lowpass"):
    """
    passType (str): ('lowpass', 'highpass')
    """

    """
	nyq = fs * 0.5
	normal_cutoff = cutOff / nyq
	"""

    logger.info(
        f"Making butter file with order:{order} cutOff:{cutOff} passType:{passType} fs:{fs}"
    )

    # sos = butter(order, normal_cutoff, btype='low', analog=False, output='sos')
    # sos = scipy.signal.butter(N=order, Wn=normal_cutoff, btype=passType, analog=False, fs=fs, output='sos')
    sos = scipy.signal.butter(
        N=order, Wn=cutOff, btype=passType, analog=False, fs=fs, output="sos"
    )
    return sos


def spikeDetect(t, dataFiltered, dataThreshold2, startPoint=None, stopPoint=None):
    verbose = False
    # dataThreshold2 = -59.81

    g_backupFraction = 0.3  # 0.5 or 0.3

    logger.info(
        f"dataThreshold2:{dataThreshold2} startPoint:{startPoint} stopPoint:{stopPoint}"
    )

    #
    # detect spikes, dataThreshold2 changes as we zoom
    Is = np.where(dataFiltered > dataThreshold2)[0]
    Is = np.concatenate(([0], Is))
    Ds = Is[:-1] - Is[1:] + 1
    spikePoints = Is[np.where(Ds)[0] + 1]
    spikeSeconds = t[spikePoints]

    #
    # Throw out spikes that are within refractory (ms) of previous
    spikePoints = _throwOutRefractory(spikePoints, refractory_ms=100)
    spikeSeconds = t[spikePoints]

    #
    # remove spikes outside of start/stop
    goodSpikes = []
    if startPoint is not None and stopPoint is not None:
        if verbose:
            print(f"  Removing spikes outside point range {startPoint} ... {stopPoint}")
        # print(f'    {t[startPoint]} ... {t[stopPoint]} (s)')
        for idx, spikePoint in enumerate(spikePoints):
            if spikePoint < startPoint or spikePoint > stopPoint:
                pass
            else:
                goodSpikes.append(spikePoint)
                if verbose:
                    print(f"    appending spike {idx} {t[spikePoint]}(s)")
    #
    spikePoints = goodSpikes
    spikeSeconds = t[spikePoints]

    #
    # only accept rising phase
    windowPoints = 40  # assuming 10 kHz -->> 4 ms
    goodSpikes = []
    for idx, spikePoint in enumerate(spikePoints):
        preClip = dataFiltered[spikePoint - windowPoints : spikePoint - 1]
        postClip = dataFiltered[spikePoint + 1 : spikePoint + windowPoints]
        preMean = np.nanmean(preClip)
        postMean = np.nanmean(postClip)
        if preMean < postMean:
            goodSpikes.append(spikePoint)
        else:
            pass
            # print(f'  rejected spike {idx}, at point {spikePoint}')
    #
    spikePoints = goodSpikes
    spikeSeconds = t[spikePoints]

    #
    # throw out above take-off-potential of APs (-30 mV)
    apTakeOff = -30
    goodSpikes = []
    for idx, spikePoint in enumerate(spikePoints):
        if dataFiltered[spikePoint] < apTakeOff:
            goodSpikes.append(spikePoint)
    #
    spikePoints = goodSpikes
    spikeSeconds = t[spikePoints]

    #
    # find peak for eack spike
    # at 500 pnts, assuming spikes are slower than 20 Hz
    peakWindow_pnts = 500
    peakPoints = []
    peakVals = []
    for idx, spikePoint in enumerate(spikePoints):
        peakPnt = np.argmax(dataFiltered[spikePoint : spikePoint + peakWindow_pnts])
        peakPnt += spikePoint
        peakVal = np.max(dataFiltered[spikePoint : spikePoint + peakWindow_pnts])
        #
        peakPoints.append(peakPnt)
        peakVals.append(peakVal)

    #
    # backup each spike until pre/post is not changing
    # uses g_backupFraction to get percent of dv/dt at spike veruus each backup window
    backupWindow_pnts = 30
    maxSteps = 30  # 30 steps at 20 pnts (2ms) per step gives 60 ms
    backupSpikes = []
    for idx, spikePoint in enumerate(spikePoints):
        # print(f'=== backup spike:{idx} at {t[spikePoint]}(s)')
        foundBackupPoint = None
        for step in range(maxSteps):
            tmpPnt = spikePoint - (step * backupWindow_pnts)
            tmpSeconds = t[tmpPnt]
            preClip = dataFiltered[
                tmpPnt - 1 - backupWindow_pnts : tmpPnt - 1
            ]  # reversed
            postClip = dataFiltered[tmpPnt + 1 : tmpPnt + 1 + backupWindow_pnts]
            preMean = np.nanmean(preClip)
            postMean = np.nanmean(postClip)
            diffMean = postMean - preMean
            if step == 0:
                initialDiff = diffMean
            # print(f'  spike {idx} step:{step} tmpSeconds:{round(tmpSeconds,4)} initialDiff:{round(initialDiff,4)} diff:{round(diffMean,3)}')
            # if diffMean is 1/2 initial AP slope then accept
            if diffMean < (initialDiff * g_backupFraction):
                # stop
                if foundBackupPoint is None:
                    foundBackupPoint = tmpPnt
                # break
        #
        if foundBackupPoint is not None:
            backupSpikes.append(foundBackupPoint)
        else:
            # needed to keep spike parity
            logger.warning(
                f"Did not find backupSpike for spike {idx} at {t[spikePoint]}(s)"
            )
            backupSpikes.append(spikePoint)

    #
    # use backupSpikes (points) to get each spike amplitude
    spikeAmps = []
    for idx, backupSpike in enumerate(backupSpikes):
        if backupSpikes == np.nan or math.isnan(backupSpike):
            continue
        # print('backupSpike:', backupSpike)
        footVal = dataFiltered[backupSpike]
        peakVal = peakVals[idx]
        spikeAmp = peakVal - footVal
        spikeAmps.append(spikeAmp)

    # TODO: use foot and peak to get real half/width
    theseWidths = [10, 20, 50, 80, 90]
    window_ms = 100
    spikeDictList = _getHalfWidths(
        t,
        dataFiltered,
        backupSpikes,
        peakPoints,
        theseWidths=theseWidths,
        window_ms=window_ms,
    )
    # for idx, spikeDict in enumerate(spikeDictList):
    # 	print(idx, spikeDict)

    #
    # get estimate of duration
    # for each spike, find next downward crossing (starting at peak)
    """
	minDurationPoints = 10
	windowPoints = 1000  # 100 ms
	fallingPoints = []
	for idx, spikePoint in enumerate(spikePoints):
		peakPoint = peakPoints[idx]
		backupPoint = backupSpikes[idx]
		if backupPoint == np.nan or math.isnan(backupPoint):
			continue
		spikeSecond = spikeSeconds[idx]
		# Not informative because we are getting spikes from absolute threshold
		thisThreshold = dataFiltered[backupPoint]
		thisPeak = dataFiltered[peakPoint]
		halfHeight = thisThreshold + (thisPeak - thisThreshold) / 2
		startPoint = peakPoint #+ 50
		postClip = dataFiltered[startPoint:startPoint+windowPoints]
		tmpFallingPoints = np.where(postClip<halfHeight)[0]
		if len(tmpFallingPoints) > 0:
			fallingPoint = startPoint + tmpFallingPoints[0]
			# TODO: check if falling point is AFTER next spike
			duration = fallingPoint - spikePoint
			if duration > minDurationPoints:
				fallingPoints.append(fallingPoint)
			else:
				print(f'  reject spike {idx} at {spikeSecond} (s), duration is {duration} points, minDurationPoints:{minDurationPoints}')
				#fallingPoints.append(fallingPoint)
		else:
			print(f'    did not find falling pnt for spike {idx} at {spikeSecond}(s) point {spikePoint}, assume it is longer than windowPoints')
			pass
			#fallingPoints.append(np.nan)
	"""

    # TODO: Package all results into a dictionary
    spikeDictList = [{}] * len(spikePoints)
    for idx, spikePoint in enumerate(spikePoints):
        """
        spikeSecond = spikeSeconds[idx]
        peakPoint = peakPoints[idx]
        peakVal = peakVals[idx]
        fallingPoint = fallingPoints[idx]  # get rid of this
        backupSpike = backupSpikes[idx]  # get rid of this
        spikeAmp = spikeAmps[idx]  # get rid of this
        """
        spikeDictList[idx]["spikePoint"] = spikePoint
        spikeDictList[idx]["spikeSecond"] = spikeSeconds[idx]
        spikeDictList[idx]["peakPoint"] = peakPoints[idx]
        spikeDictList[idx]["peakVal"] = peakVals[idx]
        # spikeDictList[idx]['fallingPoint'] = fallingPoints[idx]
        spikeDictList[idx]["backupSpike"] = backupSpikes[idx]
        spikeDictList[idx]["spikeAmp"] = spikeAmps[idx]
    #
    spikeSeconds = t[spikePoints]
    # return spikeSeconds, spikePoints, peakPoints, peakVals, fallingPoints, backupSpikes, spikeAmps
    # removved fallingPoints
    return (
        spikeDictList,
        spikeSeconds,
        spikePoints,
        peakPoints,
        peakVals,
        backupSpikes,
        spikeAmps,
    )


def _getHalfWidths(
    t, v, spikePoints, peakPoints, theseWidths=[10, 20, 50, 80, 90], window_ms=50
):
    """Get half widths.

    Args:
            t (ndarray): Time
            v (ndaray): Recording (usually curent clamp Vm)
            spikePoints (list of int): List of spike threshold crossings.
                                                    Usually the back-up version
            peakPoints (list of int):
            theseWidths (list of int): Specifies full-width-half maximal to calculate
            window_ms (int): Number of ms to look after the peak for downward 1/2 height crossing

    Returns:
            List of dict, one elemennt per spike
    """
    logger.info(
        f"theseWidths:{theseWidths} window_ms:{window_ms} spikePoints:{len(spikePoints)} peakPoints:{len(peakPoints)}"
    )

    pointsPerMs = 10  # ToDo: generalize this
    window_pnts = window_ms * pointsPerMs

    spikeDictList = [{}] * len(spikePoints)  # an empy list of dict with proper size
    for idx, spikePoint in enumerate(spikePoints):
        # print(f'Spike {idx} pnt:{spikePoint}')

        # each spike has a list of dict for each width result
        spikeDictList[idx]["widths"] = []

        # check each pre/post pnt is before next spike
        nextSpikePnt = None
        if idx < len(spikePoints) - 1:
            nextSpikePnt = spikePoints[idx + 1]

        peakPoint = peakPoints[idx]
        try:
            vSpike = v[spikePoint]
        except IndexError as e:
            logger.error(f"spikePoint:{spikePoint} {type(spikePoint)}")
        vPeak = v[peakPoint]
        height = vPeak - vSpike
        preStartPnt = spikePoint + 1
        preClip = v[preStartPnt : peakPoint - 1]
        postStartPnt = peakPoint + 1
        postClip = v[postStartPnt : peakPoint + window_pnts]
        for width in theseWidths:
            thisHeight = vSpike + (height / width)  # search for a percent of height
            prePnt = np.where(preClip >= thisHeight)[0]
            if len(prePnt) > 0:
                prePnt = preStartPnt + prePnt[0]
            else:
                # print(f'  Error: Spike {idx} "prePnt" width:{width} vSpike:{vSpike} height:{height} thisHeight:{thisHeight}')
                prePnt = None
            postPnt = np.where(postClip < thisHeight)[0]
            if len(postPnt) > 0:
                postPnt = postStartPnt + postPnt[0]
            else:
                # print(f'  Error: Spike {idx} "postPnt" width:{width} vSpike:{vSpike} height:{height} thisHeight:{thisHeight}')
                postPnt = None
            widthMs = None
            if prePnt is not None and postPnt is not None:
                widthPnts = postPnt - prePnt
                widthMs = widthPnts / pointsPerMs
                # print(f'  width:{width} tPre:{t[prePnt]} tPost:{t[postPnt]} widthMs:{widthMs}')
                if nextSpikePnt is not None and prePnt >= nextSpikePnt:
                    print(
                        f"  Error: Spike {idx} widthMs:{widthMs} prePnt:{prePnt} is after nextSpikePnt:{nextSpikePnt}"
                    )
                if nextSpikePnt is not None and postPnt >= nextSpikePnt:
                    print(
                        f"  Error: Spike {idx} widthMs:{widthMs} postPnt:{postPnt} is after nextSpikePnt:{nextSpikePnt}"
                    )

            # put into dict
            widthDict = {
                "halfHeight": width,
                "risingPnt": prePnt,
                #'risingVal': defaultVal,
                "fallingPnt": postPnt,
                #'fallingVal': defaultVal,
                #'widthPnts': None,
                "widthMs": widthMs,
            }
            spikeDictList[idx]["widths_" + str(width)] = widthMs
            spikeDictList[idx]["widths"].append(widthDict)
    #
    return spikeDictList


def _throwOutRefractory(spikePoints, refractory_ms=100):
    """
    spikePoints: spike times to consider
    refractory_ms:
    """
    dataPointsPerMs = 10

    before = len(spikePoints)

    # if there are doubles, throw-out the second one
    # refractory_ms = 20 #10 # remove spike [i] if it occurs within refractory_ms of spike [i-1]
    lastGood = 0  # first spike [0] will always be good, there is no spike [i-1]
    for i in range(len(spikePoints)):
        if i == 0:
            # first spike is always good
            continue
        dPoints = spikePoints[i] - spikePoints[lastGood]
        if dPoints < dataPointsPerMs * refractory_ms:
            # remove spike time [i]
            spikePoints[i] = 0
        else:
            # spike time [i] was good
            lastGood = i
    # regenerate spikeTimes0 by throwing out any spike time that does not pass 'if spikeTime'
    # spikeTimes[i] that were set to 0 above (they were too close to the previous spike)
    # will not pass 'if spikeTime', as 'if 0' evaluates to False
    # if goodSpikeErrors is not None:
    # 	goodSpikeErrors = [goodSpikeErrors[idx] for idx, spikeTime in enumerate(spikeTimes0) if spikeTime]
    spikePoints = [spikePoint for spikePoint in spikePoints if spikePoint]

    # TODO: put back in and log if detection ['verbose']
    after = len(spikePoints)
    logger.info(f"From {before} to {after} spikes with refractory_ms:{refractory_ms}")

    return spikePoints


def getKernel(type="sumExp", amp=5, tau1=30, tau2=70):
    """Get a kernel for convolution with a spike train."""
    N = 500  # pnts
    t = [x for x in range(N)]
    y = t

    if type == "sumExp":
        for i in t:
            y[i] = -amp * (exp(-t[i] / tau1) - (exp(-t[i] / tau2)))
    #
    return y


def getSpikeTrain(numSeconds=1, fs=10000, spikeFreq=3, amp=10, noiseAmp=10):
    """Get a spike train at given frequency.

    Arguments:
            numSeconds (int): Total number of seconds
            fs (int): Sampling frequency, 10000 for 10 kH
            spikeFreq (int): Frequency of events in spike train, e.g. simulated EPSPs
            amp (float): Amplitude of sum exponential kernel (getKernel)
    """
    n = int(numSeconds * fs)  # total number of samples
    numSpikes = int(numSeconds * spikeFreq)
    spikeTrain = np.zeros(n)
    start = fs / spikeFreq
    spikeTimes = np.linspace(start, n, numSpikes, endpoint=False)
    for idx, spike in enumerate(spikeTimes):
        # print(idx, spike)
        spike = int(spike)
        spikeTrain[spike] = 1

    expKernel = getKernel(amp=amp)
    epspTrain = scipy.signal.convolve(spikeTrain, expKernel, mode="same")
    # shift to -60 mV
    epspTrain -= 60

    # add noise
    if noiseAmp == 0:
        pass
    else:
        # noise_power = 0.001 * fs / noiseAmp
        # epspTrain += np.random.normal(scale=np.sqrt(noise_power), size=epspTrain.shape)
        epspTrain += np.random.normal(scale=noiseAmp, size=epspTrain.shape)

    #
    t = np.linspace(0, numSeconds, n, endpoint=True)
    #
    return t, spikeTrain, epspTrain


class fftFromRecording:
    def __init__(
        self,
        path=None,
        ba=None,
        sweepNumber=0,
        startSec=None,
        stopSec=None,
        doPlot=True,
    ):
        """fft backend.

        Args:
                path (str) if specified, load abf from path
                ba (bAnalysis) if specified use that
        """

        if ba is not None:
            self.ba = ba
        elif path is not None:
            self.ba = sanpy.bAnalysis(path)
        else:
            logger.error(f"Expecting either a path or existing bAnalysis object")

        # self.ba.setSweep(sweepNumber)
        self.sweepNumber = sweepNumber

        if startSec is None or stopSec is None:
            self.startSec = 0
            self.stopSec = self.ba.recordingDur
        else:
            self.startSec = startSec
            self.stopSec = stopSec

        self.plotRawAxis = True

        self.doButterFilter = True
        self.butterOrder = 70
        self.butterCutoff = [0.7, 10]  # [low freq, high freq] for bandpass

        self._resultsDictList = []
        self._resultsDictList2 = []
        self._resultStr = ""

        self.isModel = False

        self._store_ba = None  # allow switching between model and self.ba

        if self.ba is not None:
            self.fs = self.ba.recordingFrequency * 1000
        else:
            self.fs = None
        self.psdWindowStr = "Hanning"  # mpl.mlab.window_hanning

        # fft Freq (Hz) resolution is fs/nfft --> resolution 0.2 Hz = 10000/50000
        self.nfft = 50000  # 512 * 100

        self.signalHz = None  # assign when using fake data
        self.maxPlotHz = 10  # limit x-axis frequenccy

        self.medianFilterPnts = 0

        self.dataLine = None
        self.dataFilteredLine = None
        self.spikesLine = None
        self.peaksLine = None
        self.dataMeanLine = None
        self.thresholdLine2 = None
        self.thresholdLine3 = None

        # self.fig = mpl.figure.Figure(constrained_layout=True)
        self.fig = plt.figure(constrained_layout=True)

        if self.plotRawAxis:
            numRow = 3
        else:
            numRow = 2

        gs = self.fig.add_gridspec(numRow, 3)

        if self.plotRawAxis:
            self.rawAxes = self.fig.add_subplot(gs[0, :])
            self.rawZoomAxes = self.fig.add_subplot(gs[1, :])
            # 3rd row has 3 subplots
            self.psdAxes = self.fig.add_subplot(gs[2, 0])
            self.spectrogramAxes = self.fig.add_subplot(gs[2, -2])
        else:
            self.rawAxes = None
            self.rawZoomAxes = self.fig.add_subplot(gs[0, :])
            # 3rd row has 3 subplots
            self.psdAxes = self.fig.add_subplot(gs[1, 0])
            self.spectrogramAxes = self.fig.figure.add_subplot(gs[1, -2])

        if doPlot:
            self.replot_fft2(sweepNumber=self.sweepNumber)

    def getFigFileName(self):
        filename = self.ba.getFileName()
        filename = os.path.splitext(filename)[0]
        sweep = self.ba.currentSweep
        figFileName = f"{filename}_sweep_{sweep}.png"
        return figFileName

    def saveFig(self, folderPath=None):
        """Save the current figure."""

        # TODO: if folderPath then check it exists

        figFileName = self.getFigFileName()
        figFilePath = os.path.join(folderPath, figFileName)

        logger.info(f"Saving figure to: {figFilePath}")

        self.fig.savefig(figFilePath, dpi=300)

    def getStartStop(self):
        # logger.warning('remember to set start/stop')
        # startSec = 0
        # stopSec = self.ba.recordingDur
        return self.startSec, self.stopSec

    def linearDetrend(self, x):
        # print('myDetrend() x:', x.shape)
        y = plt.mlab.detrend_linear(x)
        # y = plt.mlab.detrend_mean(y)
        return y

    def replot_fft2(self, sweepNumber=0):
        start = time.time()

        if self.ba is None:
            return

        self.ba.setSweep(sweepNumber)

        # if self.sweepNumber == 'All':
        # 	logger.warning(f'fft plugin can only show one sweep, received sweepNumber:{self.sweepNumber}')
        # 	return

        # logger.info(f'using ba: {self.ba}')
        startSec, stopSec = self.getStartStop()
        if (
            startSec is None
            or stopSec is None
            or math.isnan(startSec)
            or math.isnan(stopSec)
        ):
            logger.info(f"Resetting start/stop seconds to max")
            startSec = 0
            stopSec = self.ba.recordingDur  # self.ba.sweepX()[-1]
        logger.info(f"Using start(s):{startSec} stop(s):{stopSec}")
        self.lastLeft = round(startSec * 1000 * self.ba.dataPointsPerMs)
        self.lastRight = round(stopSec * 1000 * self.ba.dataPointsPerMs)

        leftPoint = self.lastLeft
        rightPoint = self.lastRight

        # sweepY = self.getSweep('y')
        sweepY = self.ba.sweepY
        if leftPoint < 0:
            leftPoint = 0
        if rightPoint > sweepY.shape[0]:
            rightPoint = sweepY.shape[0]

        y = sweepY[leftPoint:rightPoint]

        medianPnts = self.medianFilterPnts  # 50
        if medianPnts > 0:
            logger.info(f"  Median filter with pnts={medianPnts}")
            yFiltered = scipy.ndimage.median_filter(y, medianPnts)
        else:
            logger.info("  No median filter")
            yFiltered = y

        # logger.info(f'Fetching sweepX with sweepNumber: {self.sweepNumber}')

        # sweepX = self.getSweep('x')
        sweepX = self.ba.fileLoader.sweepX

        # logger.info(f'  sweepX: {sweepX.shape}')
        # logger.info(f'  leftSec:{sweepX[leftPoint]} rightSec:{sweepX[rightPoint-1]}')
        t = sweepX[leftPoint:rightPoint]

        dt = t[1] - t[0]  # 0.0001
        fs = round(1 / dt)  # samples per second
        nfft = self.nfft  # The number of data points used in each block for the FFT
        # print(f'  fs:{fs} nfft:{nfft}')

        # 20220329 hijacking raw plot to show stim
        if self.plotRawAxis:
            sweepC = self.ba.sweepC

            self.rawAxes.clear()
            # self.rawAxes.plot(sweepX, sweepY, '-', linewidth=1)
            self.rawAxes.plot(sweepX, sweepC, "-", linewidth=1)
            # draw a rectangle to show left/right time selecction
            """
			yMin = np.nanmin(sweepY)
			yMax = np.nanmax(sweepY)
			xRect = startSec
			yRect = yMin
			wRect = stopSec-startSec
			hRect = yMax-yMin
			rect1 = mpl.patches.Rectangle((xRect,yRect), wRect, hRect, color='gray')
			self.rawAxes.add_patch(rect1)
			"""
            # self.rawAxes.set_xlim([sweepX[0], sweepX[-1]])
            self.rawAxes.set_xlim([self.startSec, self.stopSec])

        #
        # replot the clip +/- std we analyzed, after detrend
        yDetrend = self.linearDetrend(yFiltered)

        #
        if self.doButterFilter:
            # self.butterCutoff = 10  # Hz
            # self.butterOrder = 70
            # self.sos = butter_sos(self.butterCutoff, self.fs, order=self.butterOrder, passType='lowpass')
            # self.butterCutoff = [0.7, 10]
            # logger.info(f'  butterOrder:{self.butterOrder} butterCutoff:{self.butterCutoff}')
            self.sos = butter_sos(
                self.butterCutoff, self.fs, order=self.butterOrder, passType="bandpass"
            )
            # filtfilt should remove phase delay in time. A forward-backward digital filter using cascaded second-order sections.
            yFiltered_Butter = scipy.signal.sosfiltfilt(self.sos, yDetrend, axis=0)
            # print('yDetrend:', yDetrend.shape, np.nanmin(yDetrend), np.nanmax(yDetrend))
            # print('yFiltered_Butter:', yFiltered_Butter.shape, np.nanmin(yFiltered_Butter), np.nanmax(yFiltered_Butter))

            # we use this for remaining
            yFiltered = yFiltered_Butter

        dataMean = np.nanmean(yDetrend)
        dataStd = np.nanstd(yDetrend)
        dataThreshold2 = dataMean + (2 * dataStd)
        dataThreshold3 = dataMean + (3 * dataStd)

        self.rawZoomAxes.clear()
        self.rawZoomAxes.plot(t, yDetrend, "-", linewidth=1)
        self.rawZoomAxes.axhline(
            dataMean, marker="", color="r", linestyle="--", linewidth=0.5
        )
        self.rawZoomAxes.axhline(
            dataThreshold2, marker="", color="r", linestyle="--", linewidth=0.5
        )
        self.rawZoomAxes.axhline(
            dataThreshold3, marker="", color="r", linestyle="--", linewidth=0.5
        )
        self.rawZoomAxes.set_xlim([t[0], t[-1]])
        #
        if self.doButterFilter:
            self.rawZoomAxes.plot(t, yFiltered, "-r", linewidth=1)

        # save yDetrend, yFiltered as csv
        """
		print('=== FOR FERNANDO')
		import pandas as pd
		print('  t:', t.shape)
		print('  yDetrend:', yDetrend.shape)
		print('  yFiltered:', yFiltered.shape)
		tmpDf = pd.DataFrame(columns=['s', 'yDetrend', 'yFiltered'])
		tmpDf['s'] = t
		tmpDf['yDetrend'] = yDetrend
		tmpDf['yFiltered'] = yFiltered
		print(tmpDf.head())
		dfFile = 'fft-20200707-0000-16sec-31sec.csv'
		print('saving dfFile:', dfFile)
		tmpDf.to_csv(dfFile, index=False)
		print('=== END')
		"""

        # we will still scale a freq plots to [0, self.maxPlotHz]
        if self.doButterFilter:
            minPlotFreq = self.butterCutoff[0]
            maxPlotFreq = self.butterCutoff[1]
        else:
            minPlotFreq = 0
            maxPlotFreq = self.maxPlotHz  # 15

        #
        # spectrogram
        # self.fftAxes.clear()
        nfft2 = int(nfft / 4)
        specSpectrum, specFreqs, spec_t, specIm = self.spectrogramAxes.specgram(
            yFiltered, NFFT=nfft2, Fs=fs, detrend=self.linearDetrend
        )
        """
		print('=== specgram')
		print('  yFiltered:', yFiltered.shape)
		print('  specSpectrum (freq, t):', specSpectrum.shape)  # (25601, 20) is (freq, t)
		print('    ', np.nanmin(specSpectrum), np.nanmax(specSpectrum))
		print('  specFreqs:', specFreqs.shape)
		print('  spec_t:', spec_t.shape)
		print('  specIm:', type(specIm))
		"""
        mask = (specFreqs >= minPlotFreq) & (specFreqs <= maxPlotFreq)
        specSpectrum = specSpectrum[mask, :]  # TRANSPOSE
        """
		print('  2 Transpose specSpectrum (freq, t):', specSpectrum.shape)  # (25601, 20) is (freq, t)
		print('    ', np.nanmin(specSpectrum), np.nanmax(specSpectrum))
		"""

        # careful: I want to eventually scale y-axis to [0, self.maxPlotHz]
        # for now use [minPlotFreq, maxPlotFreq]
        x_min = startSec
        x_max = stopSec
        y_min = maxPlotFreq  # minPlotFreq
        y_max = minPlotFreq  # maxPlotFreq
        extent = [x_min, x_max, y_min, y_max]

        self.spectrogramAxes.clear()
        self.spectrogramAxes.imshow(
            specSpectrum, extent=extent, aspect="auto", cmap="viridis"
        )
        self.spectrogramAxes.invert_yaxis()
        self.spectrogramAxes.set_xlabel("Time (s)")
        self.spectrogramAxes.set_ylabel("Freq (Hz)")

        #
        # matplotlib psd
        if self.psdWindowStr == "Hanning":
            psdWindow = mpl.mlab.window_hanning
        elif self.psdWindowStr == "Blackman":
            psdWindow = np.blackman(nfft)
        else:
            logger.warning(f"psdWindowStr not understood {self.psdWindowStr}")
        """
		print('=== calling mpl psd()')
		print('  nfft:', nfft)
		print('  fs:', fs)
		print('  myDetrend:', myDetrend)
		print('  psdWindowStr:', self.psdWindowStr)
		print('  psdWindow:', psdWindow)
		"""
        # default scale_by_freq=True
        scale_by_freq = True
        Pxx, freqs = self.psdAxes.psd(
            yFiltered,
            marker="",
            linestyle="-",
            NFFT=nfft,
            Fs=fs,
            scale_by_freq=scale_by_freq,
            detrend=self.linearDetrend,
            window=psdWindow,
        )

        #
        # replot matplotlib psd
        pxxLog10 = 10 * np.log10(Pxx)

        # pxxLog10 = Pxx # does this look better ???

        mask = (freqs >= minPlotFreq) & (freqs <= maxPlotFreq)
        pxxLog10 = pxxLog10[mask]  # order matters
        freqsLog10 = freqs[mask]  # order matters
        self.psdAxes.clear()
        self.psdAxes.plot(freqsLog10, pxxLog10, "-", linewidth=1)
        self.psdAxes.set_xlim([0, self.maxPlotHz])  # x-axes is frequency
        self.psdAxes.grid(True)
        # self.psdAxes.set_ylabel('10*log10(Pxx)')
        self.psdAxes.set_ylabel("PSD (dB)")
        self.psdAxes.set_xlabel("Freq (Hz)")

        #
        # get peak frequency from psd, finding max peak with width
        inflection = np.diff(np.sign(np.diff(pxxLog10)))
        peaks = (inflection < 0).nonzero()[0] + 1
        # excception ValueError
        try:
            peak0 = peaks[pxxLog10[peaks].argmax()]
            maxFreq0 = round(freqsLog10[peak0], 3)  # Gives 0.05
            maxPsd0 = round(pxxLog10[peak0], 3)  # Gives 0.05
        except ValueError as e:
            logger.error("BAD PEAK in pxx")
            maxFreq0 = []
            maxPsd0 = []
        # print(f'1 Results: Peak Hz={round(maxFreq0,3)} Amplitude={round(maxPsd0,3)}')

        # add to plot
        self.psdAxes.plot(maxFreq0, maxPsd0, ".r")

        # the absolute maximum in the psd
        maxPsd = np.nanmax(pxxLog10)
        maxPnt = np.argmax(pxxLog10)
        maxFreq = freqsLog10[maxPnt]
        # self.resultsLabel.setText(f'Results: Peak Hz={round(maxFreq,3)} Amplitude={round(maxPsd,3)}')
        # print(f'2 Results: Peak Hz={round(maxFreq,3)} Amplitude={round(maxPsd,3)}')

        #
        # print results
        # (file, startSec, stopSec, max psd amp, max psd freq)
        pStart = round(startSec, 3)
        pStop = round(stopSec, 3)
        pMaxFreq = round(maxFreq, 3)
        pMaxPsd = round(maxPsd, 3)

        """
		printStr = f'Type\tFile\tstartSec\tstopSec\tmaxFreqPsd\tmaxPsd'  #\tmaxFreqFft\tmaxFft'
		#self.appendResultsStr(printStr)
		print('=== FFT results are:')
		print(printStr)
		printStr = f'fftPlugin\t{self.ba.getFileName()}\t{pStart}\t{pStop}\t{pMaxFreq}\t{pMaxPsd}'
		self.appendResultsStr(printStr, maxFreq=pMaxFreq, maxPsd=pMaxPsd, 
								maxFreq0=maxFreq0, maxPsd0=maxPsd0,
								freqs=freqsLog10, psd=pxxLog10)  # last 2 are not used
		print(printStr)
		"""

        # 20220330, rms error of stim
        tmpSweepC = sweepC[leftPoint:rightPoint]
        rms = np.sqrt(np.mean(tmpSweepC**2))

        resultDict = {
            "file": self.ba.getFileName(),
            "sweep": self.ba.currentSweep,
            "startSec": self.getStartStop()[0],
            "stopSec": self.getStartStop()[1],
            "butterFilter": self.doButterFilter,
            "butterOrder": self.butterOrder,
            "lowFreqCutoff": self.butterCutoff[0],
            "highFreqCutoff": self.butterCutoff[1],
            # ultimate max
            "maxFreq": pMaxFreq,
            "maxPSD": pMaxPsd,
            # max in peak
            "maxFreq0": maxFreq0,
            "maxPSD0": maxPsd0,
            # TODO: max as stim freq
            "maxFreq_at_stim": "",
            "maxPSD_at_stim": "",
            "rmsStim": rms,  # rms of injected current
            #'freqs': freqs,
            #'psd': psd,
        }
        self.appendResults2(resultDict)

        # TODO: make a dict of results and append to pandas df

        #
        # plot np fft
        # see: https://www.gw-openscience.org/tutorial05/
        # blackman is supposed to correct for low freq signal ???
        """
		doBlackman = False
		if doBlackman:
			window = np.blackman(yFiltered.size)
			windowed_yFiltered = yFiltered*window
		else:
			windowed_yFiltered = yFiltered

		ft = np.fft.rfft(windowed_yFiltered)
		# not sure to use diff b/w [1]-[0] or fs=10000 ???
		tmpFs = t[1]-t[0]
		fftFreqs = np.fft.rfftfreq(len(windowed_yFiltered), tmpFs) # Get frequency axis from the time axis
		fftMags = abs(ft) # We don't care about the phase information here

		# find max peak with width
		inflection = np.diff(np.sign(np.diff(fftMags)))
		peaks = (inflection < 0).nonzero()[0] + 1
		peak = peaks[fftMags[peaks].argmax()]
		signal_freq = round(fftFreqs[peak],3) # Gives 0.05
		signal_mag = round(fftMags[peak],3) # Gives 0.05
		#printStr = f'FFT\t{self.ba.getFileName()}\t{pStart}\t{pStop}\t{signal_freq}\t{signal_mag}'
		#print(printStr)
		printStr += f'\t{signal_freq}\t{signal_mag}'
		print(printStr)
		self.appendResultsStr(printStr)
		#print(f'  fft signal frequency is:{signal_freq} with mag:{signal_mag}')

		# strip down to min/ax x-plot of freq
		mask = (fftFreqs>=minPlotFreq) & (fftFreqs<=maxPlotFreq)
		fftMags = fftMags[mask] # order matters
		fftFreqs = fftFreqs[mask] # order matters

		fftMags = fftMags[2:-1]
		fftFreqs = fftFreqs[2:-1]

		self.fftAxes.clear()
		self.fftAxes.semilogy(fftFreqs, fftMags, '-', linewidth=1)
		self.fftAxes.set_xlim([minPlotFreq, maxPlotFreq])  # x-axes is frequency
		self.fftAxes.set_xlabel('Freq (Hz)')
		self.fftAxes.set_ylabel('FFT Mag')
		self.fftAxes.grid(True)
		self.fftAxes.semilogy(signal_freq, signal_mag, '.r')
		"""

        stop = time.time()
        # logger.info(f'Took {stop-start} seconds.')

        #
        # self.static_canvas.draw()

        figFileName = self.getFigFileName()
        self.fig.suptitle(figFileName)

    def appendResults2(self, resultDict):
        self._resultsDictList2.append(resultDict)

    def appendResultsStr(
        self, str, maxFreq="", maxPsd="", maxFreq0="", maxPsd0="", freqs="", psd=""
    ):
        self._resultStr += str + "\n"
        resultDict = {
            "file": self.ba.getFileName(),
            "sweep": self.ba.currentSweep,
            "startSec": self.getStartStop()[0],
            "stopSec": self.getStartStop()[1],
            "butterFilter": self.doButterFilter,
            "butterOrder": self.butterOrder,
            "lowFreqCutoff": self.butterCutoff[0],
            "highFreqCutoff": self.butterCutoff[1],
            # ultimate max
            "maxFreq": maxFreq,
            "maxPSD": maxPsd,
            # max in peak
            "maxFreq0": maxFreq0,
            "maxPSD0": maxPsd0,
            #'freqs': freqs,
            #'psd': psd,
        }
        self._resultsDictList.append(resultDict)

    def getResultsDictList(self):
        return self._resultsDictList

    def getResultStr(self):
        return self._resultStr


def run():
    # need to use colinAnalysis.bAnalysis2() to load stim file atf
    # see how far I get without it, all I need from it is
    # 	- (sin, noise) params per sweep
    # 	- if a sweep is blank_re
    # 	- try and scrip these things into a table and just use a regular bAnalysis

    #
    # if we were recorded with a stimulus file abf
    # needed to assign stimulusWaveformFromFile
    # tmpSweepC = ba.abf.sweepC

    from pprint import pprint

    masterDf = pd.DataFrame()
    saveFolder = "/Users/cudmore/Desktop/stoch-plots"

    folderPath = (
        "/Users/cudmore/Library/CloudStorage/Box-Box/data/stoch-res/new20220104"
    )

    from sanpy.bAnalysisStim import bAnalysisStim

    for file in sorted(os.listdir(folderPath)):
        if not file.endswith(".abf"):
            continue

        fullPath = os.path.join(folderPath, file)

        ba = bAnalysisStim(
            fullPath
        )  # bAnalysis that loads my stim abf (with header from stimgen)
        # ba = sanpy.bAnalysis(fullPath)

        if ba.numSweeps < 2:
            print("!!! skipping file:", file)
            continue

        print(ba)

        dfStimFile = ba._stimFileDf
        pprint(dfStimFile)

        sweep = 0
        fftRecording = fftFromRecording(
            ba=ba, sweepNumber=sweep, startSec=5, stopSec=25, doPlot=False
        )

        fftRecording.medianFilterPnts = 5

        for sweep in range(ba.numSweeps):
            print(f"{sweep} {ba}")
            fftRecording.replot_fft2(sweepNumber=sweep)
            fftRecording.saveFig(folderPath=saveFolder)

        # resultsDictList = fftRecording.getResultsDictList()
        resultsDictList = fftRecording._resultsDictList2
        df = pd.DataFrame(resultsDictList)

        # add stim params to each sweep
        df["stimFreq"] = dfStimFile["freq(Hz)"]
        df["noiseAmp"] = dfStimFile["noise amp"]

        masterDf = pd.concat([masterDf, df], ignore_index=True)

    #
    pprint(masterDf)

    summaryFile = os.path.join(saveFolder, "stoch-summary.csv")
    print("saving:", summaryFile)
    masterDf.to_csv(summaryFile)

    # plt.show()


if __name__ == "__main__":
    run()
