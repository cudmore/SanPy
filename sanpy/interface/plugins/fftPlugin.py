"""
To be complete, I need:
    - PSD
    - FFT
    - Auto Corelation (on detected spikes?)

See:
    https://stackoverflow.com/questions/59265603/how-to-find-period-of-signal-autocorrelation-vs-fast-fourier-transform-vs-power
"""

import sys, math, time
from math import exp
from functools import partial
from typing import Union, Dict, List, Tuple, Optional, Optional

import numpy as np
from scipy.signal import lfilter, freqz
import scipy.signal

from PyQt5 import QtCore, QtWidgets, QtGui
import matplotlib as mpl
import matplotlib.pyplot as plt

import sanpy
from sanpy.interface.plugins import sanpyPlugin

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
    #    print(idx, spikeDict)

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
    #    goodSpikeErrors = [goodSpikeErrors[idx] for idx, spikeTime in enumerate(spikeTimes0) if spikeTime]
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


class fftPlugin(sanpyPlugin):
    myHumanName = "FFT"

    # def __init__(self, myAnalysisDir=None, **kwargs):
    def __init__(self, plotRawAxis=False, ba=None, **kwargs):
        """
        Args:
            ba (bAnalysis): Not required
        """
        super(fftPlugin, self).__init__(ba=ba, **kwargs)

        self._isInited = False

        self.plotRawAxis = plotRawAxis

        self.doButterFilter = True
        self.butterOrder = 70
        self.butterCutoff = [0.7, 10]  # [low freq, high freq] for bandpass

        self._resultsDictList = []
        self._resultStr = ""

        self.isModel = False

        # only defined when running without SanPy app
        # self._analysisDir = myAnalysisDir

        self._store_ba = None  # allow switching between model and self.ba

        if self.ba is not None:
            self.fs = self.ba.fileLoader.recordingFrequency * 1000
        else:
            self.fs = None
        self.psdWindowStr = "Hanning"  # mpl.mlab.window_hanning

        # fft Freq (Hz) resolution is fs/nfft --> resolution 0.2 Hz = 10000/50000
        self.nfft = 50000  # 512 * 100

        self.signalHz = None  # assign when using fake data
        self.maxPlotHz = 10  # limit x-axis frequenccy

        # self.sos = None

        self.medianFilterPnts = 0

        # points
        self.lastLeft = None  # 0
        self.lastRight = None  # len(self.ba.sweepX())

        # if self._analysisDir is not None:
        #    # running lpugin without sanpy
        #    self.loadData(2)  # load the 3rd file in analysis dir

        self._buildInterface()

        # self._getPsd()

        self.dataLine = None
        self.dataFilteredLine = None
        self.spikesLine = None
        self.peaksLine = None
        self.dataMeanLine = None
        self.thresholdLine2 = None
        self.thresholdLine3 = None

        # self.getMean()
        self.plot()  # first plot of data
        self.replot2(switchFile=True)
        # self.replotPsd()
        # self.replot_fft()

        self._isInited = True

    @property
    def ba(self):
        return self._ba

    def _buildInterface(self):
        # self.pyqtWindow()

        # main layout
        vLayout = QtWidgets.QVBoxLayout()

        self.controlLayout = QtWidgets.QHBoxLayout()
        #
        # aLabel = QtWidgets.QLabel('fft')
        # self.controlLayout.addWidget(aLabel)

        """
        buttonName = 'Detect'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(partial(self.on_button_click,buttonName))
        self.controlLayout.addWidget(aButton)
        """

        """
        aLabel = QtWidgets.QLabel('mV Threshold')
        self.controlLayout.addWidget(aLabel)

        self.mvThresholdSpinBox = QtWidgets.QDoubleSpinBox()
        self.mvThresholdSpinBox.setRange(-1e9, 1e9)
        self.controlLayout.addWidget(self.mvThresholdSpinBox)
        """

        """
        checkboxName = 'PSD'
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setChecked(True)
        aCheckBox.stateChanged.connect(partial(self.on_checkbox_clicked, checkboxName))
        self.controlLayout.addWidget(aCheckBox)
        """

        """
        checkboxName = 'Auto-Correlation'
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setChecked(True)
        aCheckBox.stateChanged.connect(partial(self.on_checkbox_clicked, checkboxName))
        self.controlLayout.addWidget(aCheckBox)
        """

        buttonName = "Replot"
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(partial(self.on_button_click, buttonName))
        self.controlLayout.addWidget(aButton)

        self.resultsLabel = QtWidgets.QLabel("Results: Peak Hz=??? Ampplitude=???")
        self.controlLayout.addWidget(self.resultsLabel)

        checkboxName = "Butter Filter"
        butterCheckBox = QtWidgets.QCheckBox(checkboxName)
        butterCheckBox.setChecked(self.doButterFilter)
        butterCheckBox.stateChanged.connect(
            partial(self.on_checkbox_clicked, checkboxName)
        )
        self.controlLayout.addWidget(butterCheckBox)

        aLabel = QtWidgets.QLabel("Order")
        self.controlLayout.addWidget(aLabel)
        self.butterOrderSpinBox = QtWidgets.QSpinBox()
        self.butterOrderSpinBox.setRange(0, 2**16)
        self.butterOrderSpinBox.setValue(self.butterOrder)
        self.butterOrderSpinBox.editingFinished.connect(
            partial(self.on_cutoff_spinbox, aLabel)
        )
        self.controlLayout.addWidget(self.butterOrderSpinBox)

        aLabel = QtWidgets.QLabel("Low (Hz)")
        self.controlLayout.addWidget(aLabel)
        self.lowCutoffSpinBox = QtWidgets.QDoubleSpinBox()
        self.lowCutoffSpinBox.setRange(0, 2**16)
        self.lowCutoffSpinBox.setValue(self.butterCutoff[0])
        self.lowCutoffSpinBox.editingFinished.connect(
            partial(self.on_cutoff_spinbox, aLabel)
        )
        self.controlLayout.addWidget(self.lowCutoffSpinBox)

        aLabel = QtWidgets.QLabel("High")
        self.controlLayout.addWidget(aLabel)
        self.highCutoffSpinBox = QtWidgets.QDoubleSpinBox()
        self.highCutoffSpinBox.setRange(0, 2**16)
        self.highCutoffSpinBox.setValue(self.butterCutoff[1])
        self.highCutoffSpinBox.editingFinished.connect(
            partial(self.on_cutoff_spinbox, aLabel)
        )
        self.controlLayout.addWidget(self.highCutoffSpinBox)

        psdWindowComboBox = QtWidgets.QComboBox()
        psdWindowComboBox.addItem("Hanning")
        psdWindowComboBox.addItem("Blackman")
        psdWindowComboBox.currentTextChanged.connect(self.on_psd_window_changed)
        self.controlLayout.addWidget(psdWindowComboBox)

        #
        vLayout.addLayout(self.controlLayout)  # add mpl canvas

        self.controlLayout1_5 = QtWidgets.QHBoxLayout()

        self.fsLabel = QtWidgets.QLabel(f"fs={self.fs}")
        self.controlLayout1_5.addWidget(self.fsLabel)

        aLabel = QtWidgets.QLabel("NFFT")
        self.controlLayout1_5.addWidget(aLabel)
        self.nfftSpinBox = QtWidgets.QSpinBox()
        self.nfftSpinBox.setRange(0, 2**16)
        self.nfftSpinBox.setValue(self.nfft)
        self.nfftSpinBox.editingFinished.connect(
            partial(self.on_cutoff_spinbox, aLabel)
        )
        self.controlLayout1_5.addWidget(self.nfftSpinBox)

        # self.freqResLabel = QtWidgets.QLabel(f'Freq Resolution (Hz) {round(self.fs/self.nfft,3)}')
        self.freqResLabel = QtWidgets.QLabel(f"Freq Resolution (Hz) Unknown")
        self.controlLayout1_5.addWidget(self.freqResLabel)

        aLabel = QtWidgets.QLabel("Median Filter (Pnts)")
        self.controlLayout1_5.addWidget(aLabel)
        self.medianFilterPntsSpinBox = QtWidgets.QSpinBox()
        self.medianFilterPntsSpinBox.setRange(0, 2**16)
        self.medianFilterPntsSpinBox.setValue(self.medianFilterPnts)
        self.medianFilterPntsSpinBox.editingFinished.connect(
            partial(self.on_cutoff_spinbox, aLabel)
        )
        self.controlLayout1_5.addWidget(self.medianFilterPntsSpinBox)

        aLabel = QtWidgets.QLabel("Max Plot (Hz)")
        self.controlLayout1_5.addWidget(aLabel)
        self.maxPlotHzSpinBox = QtWidgets.QDoubleSpinBox()
        self.maxPlotHzSpinBox.setRange(0, 2**16)
        self.maxPlotHzSpinBox.setValue(self.maxPlotHz)
        self.maxPlotHzSpinBox.editingFinished.connect(
            partial(self.on_cutoff_spinbox, aLabel)
        )
        self.controlLayout1_5.addWidget(self.maxPlotHzSpinBox)

        """
        aLabel = QtWidgets.QLabel('Order')
        self.controlLayout1_5.addWidget(aLabel)
        self.orderSpinBox = QtWidgets.QDoubleSpinBox()
        self.orderSpinBox.setRange(-1e9, 1e9)
        self.orderSpinBox.setValue(self.order)
        self.orderSpinBox.editingFinished.connect(partial(self.on_cutoff_spinbox, aLabel))
        self.controlLayout1_5.addWidget(self.orderSpinBox)
        """

        buttonName = "Filter Response"
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(partial(self.on_button_click, buttonName))
        self.controlLayout1_5.addWidget(aButton)

        """
        buttonName = 'Rebuild Auto-Corr'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(partial(self.on_button_click,buttonName))
        self.controlLayout1_5.addWidget(aButton)
        """

        #
        vLayout.addLayout(self.controlLayout1_5)  # add mpl canvas

        #
        # second row of controls (for model)
        self.controlLayout_row2 = QtWidgets.QHBoxLayout()

        checkboxName = "Model Data"
        self.modelDataCheckBox = QtWidgets.QCheckBox(checkboxName)
        self.modelDataCheckBox.setChecked(False)
        self.modelDataCheckBox.stateChanged.connect(
            partial(self.on_checkbox_clicked, checkboxName)
        )
        self.controlLayout_row2.addWidget(self.modelDataCheckBox)

        """
        buttonName = 'Detect'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(partial(self.on_button_click,buttonName))
        self.controlLayout_row2.addWidget(aButton)
        """

        """
        aLabel = QtWidgets.QLabel('mvThreshold')
        self.controlLayout_row2.addWidget(aLabel)

        self.mvThresholdSpinBox = QtWidgets.QDoubleSpinBox()
        self.mvThresholdSpinBox.setValue(-52)
        self.mvThresholdSpinBox.setRange(-1000, 1000)
        self.controlLayout_row2.addWidget(self.mvThresholdSpinBox)
        """

        # numSeconds, spikeFreq, amp, noise
        aLabel = QtWidgets.QLabel("Seconds")
        self.controlLayout_row2.addWidget(aLabel)

        self.modelSecondsSpinBox = QtWidgets.QDoubleSpinBox()
        self.modelSecondsSpinBox.setValue(20)
        self.modelSecondsSpinBox.setRange(0, 1000)
        self.controlLayout_row2.addWidget(self.modelSecondsSpinBox)

        # finalize row 2
        vLayout.addLayout(self.controlLayout_row2)  # add mpl canvas

        # 3rd row
        # second row of controls (for model)
        # self.controlLayout_row3 = QtWidgets.QHBoxLayout()

        aLabel = QtWidgets.QLabel("Spike Frequency")
        self.controlLayout_row2.addWidget(aLabel)

        self.modelFrequencySpinBox = QtWidgets.QDoubleSpinBox()
        self.modelFrequencySpinBox.setValue(1)
        self.modelFrequencySpinBox.setRange(0, 100)
        self.controlLayout_row2.addWidget(self.modelFrequencySpinBox)

        aLabel = QtWidgets.QLabel("Amplitude")
        self.controlLayout_row2.addWidget(aLabel)

        self.modelAmpSpinBox = QtWidgets.QDoubleSpinBox()
        self.modelAmpSpinBox.setValue(100)
        self.modelAmpSpinBox.setRange(-100, 100)
        self.controlLayout_row2.addWidget(self.modelAmpSpinBox)

        aLabel = QtWidgets.QLabel("Noise Amp")
        self.controlLayout_row2.addWidget(aLabel)

        self.modelNoiseAmpSpinBox = QtWidgets.QDoubleSpinBox()
        self.modelNoiseAmpSpinBox.setValue(50)
        self.modelNoiseAmpSpinBox.setRange(0, 1000)
        self.controlLayout_row2.addWidget(self.modelNoiseAmpSpinBox)

        # finalize row 3
        # vLayout.addLayout(self.controlLayout_row3) # add mpl canvas

        vSplitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        vLayout.addWidget(vSplitter)

        # don't use inherited, want 3x3 with rows: 1, 1, 3 subplits
        """
        self.mplWindow2(numRow=3)  # makes self.axs[] and self.static_canvas
        #self.vmAxes = self.axs[0]
        self.rawAxes = self.axs[0]
        self.rawZoomAxes = self.axs[1]
        self.fftAxes = self.axs[2]
        #self.autoCorrAxes = self.axs[3]  # uses spike detection
        """

        #  mirror self.mplWindow2()
        from matplotlib.backends import backend_qt5agg

        self.fig = mpl.figure.Figure(constrained_layout=True)
        self.static_canvas = backend_qt5agg.FigureCanvas(self.fig)
        # this is really tricky and annoying
        self.static_canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.static_canvas.setFocus()
        # self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)

        self.mplToolbar = mpl.backends.backend_qt5agg.NavigationToolbar2QT(
            self.static_canvas, self.static_canvas
        )

        if self.plotRawAxis:
            numRow = 3
        else:
            numRow = 2

        gs = self.fig.add_gridspec(numRow, 3)
        # self.rawAxes = self.fig.addsubplot(gs[0,:])
        if self.plotRawAxis:
            self.rawAxes = self.static_canvas.figure.add_subplot(gs[0, :])
            self.rawZoomAxes = self.static_canvas.figure.add_subplot(gs[1, :])
            # 3rd row has 3 subplots
            self.psdAxes = self.static_canvas.figure.add_subplot(gs[2, 0])
            self.spectrogramAxes = self.static_canvas.figure.add_subplot(gs[2, -2])
        else:
            self.rawAxes = None
            self.rawZoomAxes = self.static_canvas.figure.add_subplot(gs[0, :])
            # 3rd row has 3 subplots
            self.psdAxes = self.static_canvas.figure.add_subplot(gs[1, 0])
            self.spectrogramAxes = self.static_canvas.figure.add_subplot(gs[1, -2])

        vSplitter.addWidget(self.static_canvas)  # add mpl canvas
        vSplitter.addWidget(self.mplToolbar)  # add mpl canvas

        # this works
        # self.mplToolbar.hide()

        # set the layout of the main window
        # self.setLayout(vLayout)
        self.getVBoxLayout().addLayout(vLayout)

    def on_psd_window_changed(self, item):
        """User selected window dropdown

        Args:
            item (str):
        """
        logger.info(f'item:"{item}" {type(item)}')
        self.psdWindowStr = item
        """
        if item == 'Hanning':
            self.psdWindow = mpl.mlab.window_hanning
        if item == 'Blackman':
            self.psdWindow = np.blackman(51)
        else:
            logger.warning(f'Item not understood {item}')
        """
        #
        self.replot2(switchFile=False)

    def setAxis(self):
        self.replot()

    def replot(self):
        logger.info("")

        # self.getMean()
        self.replot2(switchFile=True)

    def replot2(self, switchFile=False):
        logger.info(f"switchFile:{switchFile}")

        # self.replotData(switchFile=switchFile)
        # self.replotPsd()
        # self.replot_fft()
        # self.replotAutoCorr()
        self.replot_fft2()

        if switchFile:
            self._mySetWindowTitle()

        self.static_canvas.draw()
        # plt.draw()

    def replot_fft2(self):
        def myDetrend(x):
            # print('myDetrend() x:', x.shape)
            y = plt.mlab.detrend_linear(x)
            # y = plt.mlab.detrend_mean(y)
            return y

        start = time.time()

        if self.ba is None:
            return

        if self.sweepNumber == "All":
            logger.warning(
                f"fft plugin can only show one sweep, received sweepNumber:{self.sweepNumber}"
            )
            return

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
            stopSec = self.ba.fileLoader.recordingDur  # self.ba.sweepX()[-1]
        logger.info(f"Using start(s):{startSec} stop(s):{stopSec}")
        self.lastLeft = round(startSec * 1000 * self.ba.fileLoader.dataPointsPerMs)
        self.lastRight = round(stopSec * 1000 * self.ba.fileLoader.dataPointsPerMs)

        leftPoint = self.lastLeft
        rightPoint = self.lastRight

        sweepY = self.getSweep("y")
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

        sweepX = self.getSweep("x")

        # logger.info(f'  sweepX: {sweepX.shape}')
        # logger.info(f'  leftSec:{sweepX[leftPoint]} rightSec:{sweepX[rightPoint-1]}')
        t = sweepX[leftPoint:rightPoint]

        dt = t[1] - t[0]  # 0.0001
        fs = round(1 / dt)  # samples per second
        nfft = self.nfft  # The number of data points used in each block for the FFT
        # print(f'  fs:{fs} nfft:{nfft}')

        if self.plotRawAxis:
            self.rawAxes.clear()
            self.rawAxes.plot(sweepX, sweepY, "-", linewidth=1)
            # draw a rectangle to show left/right time selecction
            yMin = np.nanmin(sweepY)
            yMax = np.nanmax(sweepY)
            xRect = startSec
            yRect = yMin
            wRect = stopSec - startSec
            hRect = yMax - yMin
            rect1 = mpl.patches.Rectangle((xRect, yRect), wRect, hRect, color="gray")
            self.rawAxes.add_patch(rect1)
            self.rawAxes.set_xlim([sweepX[0], sweepX[-1]])

        #
        # replot the clip +/- std we analyzed, after detrend
        yDetrend = myDetrend(yFiltered)

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
            yFiltered, NFFT=nfft2, Fs=fs, detrend=myDetrend
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
            detrend=myDetrend,
            window=psdWindow,
        )

        #
        # replot matplotlib psd
        pxxLog10 = 10 * np.log10(Pxx)
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
            peak = peaks[pxxLog10[peaks].argmax()]
            maxFreq = round(freqsLog10[peak], 3)  # Gives 0.05
            maxPsd = round(pxxLog10[peak], 3)  # Gives 0.05
        except ValueError as e:
            logger.error("BAD PEAK in pxx")
            maxFreq = []
            maxPsd = []

        # add to plot
        self.psdAxes.plot(maxFreq, maxPsd, ".r")

        maxPsd = np.nanmax(pxxLog10)
        maxPnt = np.argmax(pxxLog10)
        maxFreq = freqsLog10[maxPnt]
        self.resultsLabel.setText(
            f"Results: Peak Hz={round(maxFreq,3)} Amplitude={round(maxPsd,3)}"
        )

        #
        # print results
        # (file, startSec, stopSec, max psd amp, max psd freq)
        pStart = round(startSec, 3)
        pStop = round(stopSec, 3)
        pMaxFreq = round(maxFreq, 3)
        pMaxPsd = round(maxPsd, 3)

        printStr = f"Type\tFile\tstartSec\tstopSec\tmaxFreqPsd\tmaxPsd"  # \tmaxFreqFft\tmaxFft'
        # self.appendResultsStr(printStr)

        # print("=== FFT results are:")
        # print(printStr)

        printStr = f"fftPlugin\t{self.ba.fileLoader.filename}\t{pStart}\t{pStop}\t{pMaxFreq}\t{pMaxPsd}"

        self.appendResultsStr(
            printStr, maxFreq=pMaxFreq, maxPsd=pMaxPsd, freqs=freqsLog10, psd=pxxLog10
        )
        # print(printStr)

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
        self.static_canvas.draw()

    def appendResultsStr(self, str, maxFreq="", maxPsd="", freqs="", psd=""):
        self._resultStr += str + "\n"
        resultDict = {
            "file": self.ba.fileLoader.filename,
            "startSec": self.getStartStop()[0],
            "stopSec": self.getStartStop()[1],
            "butterFilter": self.doButterFilter,
            "butterOrder": self.butterOrder,
            "lowFreqCutoff": self.butterCutoff[0],
            "highFreqCutoff": self.butterCutoff[1],
            "maxFreq": maxFreq,
            "maxPSD": maxPsd,
            "freqs": freqs,
            "psd": psd,
        }
        self._resultsDictList.append(resultDict)

    def getResultsDictList(self):
        return self._resultsDictList

    def getResultStr(self):
        return self._resultStr

    def old_replot_fft(self):
        self.replot_fft2()
        return

    def replotFilter(self):
        """Plot frequency response of butter sos filter."""

        logger.info("")

        # self.sos = butter_sos(self.butterCutoff, self.fs, self.butterOrder, passType='lowpass')

        fs = self.fs

        if self.sos is None:
            # filter has not been created
            self.sos = butter_sos(
                self.butterCutoff, self.fs, order=self.butterOrder, passType="bandpass"
            )

        w, h = scipy.signal.sosfreqz(self.sos, worN=fs * 5, fs=fs)

        print("w:", w)
        print("h:", np.abs(h))

        fig = plt.figure(figsize=(3, 3))
        ax1 = fig.add_subplot(1, 1, 1)  #

        # plt.plot(0.5*fs*w/np.pi, np.abs(H), 'b')
        db = 20 * np.log10(np.maximum(np.abs(h), 1e-5))
        # y = np.abs(H)  # 10*np.log10(np.maximum(1e-10, np.abs(H)))
        ax1.plot(w, db, "-")
        ax1.axvline(self.butterCutoff[0], color="r", linestyle="--", linewidth=0.5)
        ax1.axvline(self.butterCutoff[1], color="r", linestyle="--", linewidth=0.5)
        # y_sos = signal.sosfilt(sos, x)
        ax1.set_xlim(0, self.maxPlotHz * 2)

        ax1.set_xlabel("Frequency (Hz)")
        ax1.set_ylabel("Decibles (dB)")

        plt.show()

    def old_getPsd(self):
        """Get psd from selected x-axes range."""
        # logger.info(f'self.lastLeft:{self.lastLeft} self.lastRight:{self.lastRight}')
        dataFiltered = self.getSweep("filteredVm")
        leftPoint = self.lastLeft
        rightPoint = self.lastRight
        y_sos = scipy.signal.sosfilt(self.sos, dataFiltered[leftPoint:rightPoint])
        self.f, self.Pxx_den = scipy.signal.periodogram(y_sos, self.fs)

    def rebuildModel(self):
        numSeconds = self.modelSecondsSpinBox.value()
        spikeFreq = self.modelFrequencySpinBox.value()
        amp = self.modelAmpSpinBox.value()
        noiseAmp = self.modelNoiseAmpSpinBox.value()
        fs = 10000  # 10 kHz
        t, spikeTrain, data = getSpikeTrain(
            numSeconds=numSeconds,
            spikeFreq=spikeFreq,
            fs=fs,
            amp=amp,
            noiseAmp=noiseAmp,
        )
        # (t, data) need to be one column (for bAnalysis)
        t = t.reshape(t.shape[0], -1)
        data = data.reshape(data.shape[0], -1)

        self._startSec = 0
        self._stopSec = numSeconds

        # t = t[:,0]
        # data = data[:,0]

        print("  model t:", t.shape)
        print("  model data:", data.shape)

        modelDict = {"sweepX": t, "sweepY": data, "mode": "I-Clamp"}
        self._ba = sanpy.bAnalysis(fromDict=modelDict)

        # self.modelDetect()

    def loadData(self, fileIdx=0, modelData=False):
        """Load from an analysis directory. Only used when no SanPyApp."""
        if modelData:
            self.isModel = True

            # store bAnalysis so we can bring it back
            self._store_ba = self._ba
            self._store_startSec = self._startSec
            self._store_stopSec = self._stopSec

            #
            # load from a model
            # numSeconds = 50
            # spikeFreq = 1
            # amp = 20
            #  TODO: ensure we separate interface from backend !!!
            self.rebuildModel()
        else:
            self.isModel = False
            if self._analysisDir is not None:
                self._ba = self._analysisDir.getAnalysis(fileIdx)

            if self._store_ba is not None:
                self._ba = self._store_ba
                self._startSec = self._store_startSec
                self._stopSec = self._store_stopSec

        # either real ba or model
        print(self.ba)

        self.fs = self.ba.fileLoader.recordingFrequency * 1000

        self.replot2(switchFile=True)

        return

    def not_used_modelDetect(self):
        # mvThreshold = self.mvThresholdSpinBox.value() # for detection
        mvThreshold = -20

        dDict = sanpy.bDetection().getDetectionDict("SA Node")
        dDict["dvdtThreshold"] = np.nan
        dDict["mvThreshold"] = mvThreshold
        dDict["onlyPeaksAbove_mV"] = None
        dDict["doBackupSpikeVm"] = False
        self._ba.spikeDetect(dDict)

    def on_cutoff_spinbox(self, name):
        """When user sets values, rebuild low-pass filter."""
        self.nfft = self.nfftSpinBox.value()
        self.maxPlotHz = self.maxPlotHzSpinBox.value()
        self.medianFilterPnts = self.medianFilterPntsSpinBox.value()  # int

        self.butterOrder = self.butterOrderSpinBox.value()

        lowCutoff = self.lowCutoffSpinBox.value()  # int
        highCutoff = self.highCutoffSpinBox.value()  # int
        self.butterCutoff = [lowCutoff, highCutoff]

        self.freqResLabel.setText(f"Freq Resolution (Hz) {round(self.fs/self.nfft, 3)}")

        # self.order = self.orderSpinBox.value()
        # self.sos = butter_lowpass_sos(self.cutOff, self.fs, self.order)

    def on_checkbox_clicked(self, name, value):
        # print('on_crosshair_clicked() value:', value)
        logger.info(f'name:"{name}" value:{value}')
        isOn = value == 2
        if name == "PSD":
            self.psdAxes.set_visible(isOn)
            if isOn:
                self.vmAxes.change_.geometry(2, 1, 1)
                self.replotPsd()
            else:
                self.vmAxes.change_geometry(1, 1, 1)
            self.static_canvas.draw()
        elif name == "Auto-Correlation":
            pass
        elif name == "Model Data":
            self.loadData(fileIdx=0, modelData=isOn)
        elif name == "Butter Filter":
            self.doButterFilter = value == 2
            self.replot2(switchFile=False)
        else:
            logger.warning(f'name:"{name}" not understood')

    def on_button_click(self, name):
        if name == "Replot":
            if self.isModel:
                self.rebuildModel()
                # self.replot2(switchFile=False)
            #
            self.replot2(switchFile=False)
        elif name == "Filter Response":
            # popup new window
            self.replotFilter()
        else:
            logger.warning(f'name:"{name}" not understood')
        """
        elif name == 'Detect':
            #mvThreshold = self.mvThresholdSpinBox.value()
            #logger.info(f'{name} mvThreshold:{mvThreshold}')
            self.modelDetect()
            self.replot2()
        elif name == 'Rebuild Auto-Corr':
            self.replotAutoCorr()
        """

    def on_xlims_change(self, event_ax):
        return

        if not self._isInited:
            return

        # slogger.info(f'event_ax:{event_ax}')
        left, right = event_ax.get_xlim()  # seconds
        logger.info(f"left:{left} right:{right}")

        # find start/stop point from seconds in 't'
        t = self.getSweep("x")
        leftPoint = np.where(t >= left)[0]
        leftPoint = leftPoint[0]
        rightPoint = np.where(t >= right)[0]
        if len(rightPoint) == 0:
            rightPoint = len(t)  # assuming we use [left:right]
        else:
            rightPoint = rightPoint[0]
        # print('leftPoint:', leftPoint, 'rightPoint:', rightPoint, 'len(t):', len(self.t))

        # keep track of last setting, if it does not change then do nothing
        if self.lastLeft == leftPoint and self.lastRight == rightPoint:
            logger.info("left/right point same doing nothng -- RETURNING")
            return
        else:
            self.lastLeft = leftPoint
            self.lastRight = rightPoint

        #
        # get threshold fromm selection
        self.getMean()

        self.replotPsd()
        self.replot_fft()
        # self.replotAutoCorr()  # slow, requires button push

    def keyPressEvent(self, event):
        logger.info(event)
        text = super().keyPressEvent(event)

        # isMpl = isinstance(event, mpl.backend_bases.KeyEvent)
        # text = event.key
        # logger.info(f'xxx mpl key: "{text}"')

        if text == "h":
            # hide controls (leave plots)
            self.controlLayout.hide()

        if text in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            # self.loadData yyy
            fileIdx = int(text)
            self.loadData(fileIdx)
            self.replot2(switchFile=True)

        elif text == "f":
            self.replotFilter()

    def slot_switchFile(
        self, ba: sanpy.bAnalysis, rowDict: Optional[dict] = None, replot: bool = True
    ):
        super().slot_switchFile(ba, rowDict, replot=False)

        self.fs = self.ba.fileLoader.recordingFrequency * 1000

        self.freqResLabel.setText(f"Freq Resolution (Hz) {round(self.fs/self.nfft, 3)}")

        self.replot()


def testPlugin():
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication([])

    path = "/Users/cudmore/Sites/Sanpy/data/fft"
    ad = sanpy.analysisDir(path, autoLoad=True)

    fft = fftPlugin(ad)
    # plt.show()

    sys.exit(app.exec_())


def test_fft():
    if 0:
        # abf data
        path = "/Users/cudmore/Sites/SanPy/data/fft/2020_07_07_0000.abf"
        ba = sanpy.bAnalysis(path)

        x = ba.fileLoader.sweepX
        y = ba.fileLoader.sweepY

        # 20-30 sec
        startSec = 16.968  # good signal
        stopSec = 31.313

        # reduce to get fft with N=1024 in excel
        dataPointsPerMs = ba.fileLoader.dataPointsPerMs  # 10 for 10 kHz
        startPnt = round(startSec * 1000 * dataPointsPerMs)
        stopPnt = round(stopSec * 1000 * dataPointsPerMs)

        numPnts = stopPnt - startPnt
        print(f"N={numPnts}")

        t = x[startPnt:stopPnt]
        y = y[startPnt:stopPnt]

        # y -= np.nanmean(y)

        dt = 0.0001
        fs = 1 / dt
        NFFT = 512  # 2**16 #512 * 100  # The number of data points used in each block for the FFT
        medianPnts = 50  # 5 ms

        fileName = ba.fileLoader.filename

    if 1:
        # sin wave data
        # Fixing random state for reproducibility
        np.random.seed(19680801)

        durSec = 10.24  # to get 1024 points at dt=0.01 (power of two)
        dt = 0.01
        fs = 1 / dt
        nfft = 512  # The number of data points used in each block for the FFT
        medianPnts = 5  #

        t = np.arange(0, durSec, dt)
        nse = np.random.randn(len(t))
        r = np.exp(-t / 0.05)

        cnse = np.convolve(nse, r) * dt
        cnse = cnse[: len(t)]

        secondFre = 7
        y = 0.1 * np.sin(2 * np.pi * t) + cnse
        y += 0.1 * np.sin(secondFre * 2 * np.pi * t) + cnse

        fileName = "fakeSin"

    # def replot_fft():

    #
    # filter
    yFiltered = scipy.ndimage.median_filter(y, medianPnts)

    # subsample down to 1024
    """
    from scipy.interpolate import interp1d
    t2 = interp1d(np.arange(1024), t, 'linear')
    yFiltered2 = interp1d(t, yFiltered, 'linear')
    print(f'N2={len(t2)}')
    plt.plot(t2, yFiltered2)
    """

    # save [t,y] to csv
    """
    import pandas as pd
    tmpDf = pd.DataFrame(columns=['t', 'y'])
    tmpDf['t'] = t
    tmpDf['y'] = y
    csvPath = fileName + '.csv'
    print('saving csv:', csvPath)
    tmpDf.to_csv(csvPath, index=False)
    """

    """
    cutOff = 10 #20  # 20, cutOff of filter (Hz)
    order = 50 # 40  # order of filter
    sos = butter_lowpass_sos(cutOff, fs, order)
    """

    # yFiltered = scipy.signal.sosfilt(sos, yFiltered)

    #
    # Fs = 1/dt  # The sampling frequency (samples per time unit)
    # NFFT = 512  # The number of data points used in each block for the FFT

    # plot
    fig, (ax0, ax1, ax2) = plt.subplots(3, 1)

    ax0.plot(t, y, "k")
    ax0.plot(t, yFiltered, "r")

    def myDetrend(x):
        y = plt.mlab.detrend_linear(x)
        y = plt.mlab.detrend_mean(y)
        return y

    # The power spectral density 𝑃𝑥𝑥 by Welch's average periodogram method
    print("  fs:", fs, "nfft:", nfft)
    ax1.clear()
    Pxx, freqs = ax1.psd(yFiltered, NFFT=nfft, Fs=fs, detrend=myDetrend)
    ax1.set_xlim([0, 20])
    ax1.set_ylabel("PSD (dB/Hz)")
    # ax1.callbacks.connect('xlim_changed', self.on_xlims_change)

    """
    ax1.clear()
    ax1.plot(freqs, Pxx)
    ax1.set_xlim([0, 20])
    """

    """
    # recompute the ax.dataLim
    ax1.relim()
    # update ax.viewLim using the new dataLim
    ax1.autoscale_view()
    plt.draw()
    """

    """
    ax2.plot(freqs, Pxx)
    ax2.set_xlim([0, 20])
    """

    maxPsd = np.nanmax(Pxx)
    maxPnt = np.argmax(Pxx)
    print(f"Max PSD freq is {freqs[maxPnt]} with power {maxPsd}")

    scipy_f, scipy_Pxx = scipy.signal.periodogram(yFiltered, fs)
    ax2.plot(scipy_f[1:-1], scipy_Pxx[1:-1])  # drop freq 0
    ax2.set_xlim([0, 20])

    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("scipy_Pxx")

    #
    plt.show()


def testFilter():
    butterOrder = 50
    butterCutoff = [0.7, 10]
    fs = 10000
    # nyq = fs * 0.5
    # normal_cutoff = butterCutoff / nyq
    # normal_cutoff = butterCutoff
    passType = "bandpass"

    # sos = scipy.signal.butter(N=butterOrder, Wn=butterCutoff, btype=passType, analog=False, fs=fs, output='sos')
    sos = butter_sos(butterCutoff, fs, order=butterOrder, passType="bandpass")

    w, h = scipy.signal.sosfreqz(sos, worN=fs * 5, fs=fs)

    db = 20 * np.log10(np.maximum(np.abs(h), 1e-5))

    print("w:", w)
    print("db:", db)

    fig = plt.figure(figsize=(3, 3))
    ax1 = fig.add_subplot(1, 1, 1)  #

    ax1.plot(w, db, "-")
    ax1.set_xlim([0, 15])

    plt.show()


def main():
    path = "/home/cudmore/Sites/SanPy/data/19114001.abf"
    ba = sanpy.bAnalysis(path)
    ba.spikeDetect()
    print(ba.numSpikes)

    import sys

    app = QtWidgets.QApplication([])
    fft = fftPlugin(ba=ba)
    fft.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    # test_fft()
    # testFilter()
    main()
