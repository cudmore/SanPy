"""
Author: RObert H Cudmore
Date: 20210811

Purpose:
	Provide functions to generate stimulation patterns and save them as Axon-Text-Files (atf).

Usage:
	coming soon.

Notes:
	Opening atf files in pClamp is slow, you want to open abf files instead.
	To acheive this, open the generated atf in Clampfit and save it as abf.

See:
	https://github.com/swharden/pyABF/tree/master/docs/advanced/creating-waveforms

"""

import sys, math
from math import exp
import numpy as np
import scipy.signal
import matplotlib.pyplot as plt

import sanpy

def getAtfHeader():
    ATF_HEADER = """
	ATF	1.0
	8	2
	"AcquisitionMode=Episodic Stimulation"
	"Comment="
	"YTop=2000"
	"YBottom=-2000"
	"SyncTimeUnits=20"
	"SweepStartTimesMS=0.000"
	"SignalsExported=IN 0"
	"Signals="	"IN 0"
	"Time (s)"	"Trace #1"
	""".strip()

    return ATF_HEADER


def padData(data, fs=10000, preSec=1, postSec=1, autoPad=True):
    """
    All stimuli sent to pClamp need to be padded with zeros before/after the stimulus.

    pClamp something like zero(ing) out the first 1/16th duration of a stimulus.

    Note:
            - ClampEx cuts off the first 1/64th of a sweep
                    TODO: Make sure our preSec of 1 second is LONGER than 1/64th of the sweep length !!!
            - Need to check this for V-Clamp protocols!!!

    Args:
            data (np.ndarray):
            fs (int): samlpes-per-unit-time, 10000 for 10 kHz
            preSec (int):
            postSec (int):
            autoPad (bool): If True will pad before/after data (1/16)*2 durations with zeros
    """
    dataSeconds = len(data) / fs
    oneSixteenthSeconds = dataSeconds / 16
    if autoPad:
        preSec = oneSixteenthSeconds  # * 2
        postSec = oneSixteenthSeconds  # * 2
    # check that preSec is larger than 1/16 of total duration in data
    elif preSec < oneSixteenthSeconds:
        print(
            f"ERROR padData(): preSec is {preSec} seconds but needs to be more than 1/16th of data seconds {dataSeconds}."
        )
        print(f"  Make preSec > {oneSixteenthSeconds}")

    prePnts = preSec * fs  # seconds * samples-per-second
    postPnts = postSec * fs

    prePnts = math.ceil(
        prePnts
    )  # ceil rather than round for fear we lose 1 sampling point
    postPnts = math.ceil(postPnts)

    newLen_pnts = prePnts + len(data) + postPnts
    newData = np.zeros(newLen_pnts)
    newData[prePnts : prePnts + len(data)] = data

    return newData


def saveAtf(data, fileName="output.atf", fs=10000):
    """Save a stimulus waveform array as an ATF 1.0 file."""
    out = getAtfHeader()

    # make a second sweep with noise (See if pyAbf can load it)
    # myNoise = np.random.normal(scale=np.sqrt(5), size=data.shape)

    for i, val in enumerate(data):
        # noiseVal = myNoise[i]
        # TODO: Convert to f'' format
        # out += '\n%.05f\t%.05f'%(i/fs,val)
        out += "\n%.05f\t%.05f" % (i / fs, val)
    with open(fileName, "w") as f:
        f.write(out)
        print(f'Saved: "{fileName}"')
    return True


def _loadAtf(path):
    """
    Load our saved atf file. Primarily for testing the code.
    """
    import pyabf

    # load
    abf = pyabf.ATF(path)
    print("_loadAtf()", abf)

    # plot
    data = abf.sweepY
    # plotData(data)
    return data


def plotData(data, fs=10000):
    """ """
    # make a time axies
    t = np.arange(len(data)) / fs

    fig = plt.figure()
    ax1 = fig.add_subplot(1, 1, 1)  #
    ax1.plot(t, data)
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("pA")  # assuming we are working in I-Clamp
    plt.show()


def _makeSin(durSec=10, amp=10, freqHz=10, fs=10000):
    """
    Create a Sin wave.

    Args:
            durSec (float): Duration of stimulus
            amp (float): Amplitude of sin
            freqHz (float):
            fs (int): Sampling frequency in 'samples per unit time', 10000 for 10 kHz

    See: https://github.com/swharden/pyABF/tree/master/docs/advanced/creating-waveforms
    """
    Xs = (
        np.arange(fs * durSec) / fs
    )  # x/time axis, we should always be able to create this from (dur, fs)
    data = amp * np.sin(2 * np.pi * (Xs) * freqHz)

    return data


def _makeChirp(durSec=10, amp=10, maxFreqHz=10, fs=10000):
    """
    Create a Sin wave sweep, a.k.a. a 'chirp'.

    Args:
            durSec (float): Duration of stimulus
            amp (float): Amplitude of sin
            maxFreqHz (float): Max frequency, chirp will go from/to (0, maxFreq_hz) Hz
            fs (int): Sampling frequency in 'samples per unit time', 10000 for 10 kHz
            autoPad (bool):

    See: https://github.com/swharden/pyABF/tree/master/docs/advanced/creating-waveforms
    """
    timeScale = maxFreqHz / durSec / 2
    Xs = (
        np.arange(fs * durSec) / fs
    )  # x/time axis, we should always be able to create this from (dur, fs)
    data = amp * np.sin(2 * np.pi * (Xs**2) * timeScale)

    #
    return data


def _makeNoise(durSec, noiseAmp, fs=10000):
    Xs = (
        np.arange(fs * durSec) / fs
    )  # x/time axis, we should always be able to create this from (dur, fs)
    # data = np.random.normal(scale=np.sqrt(noiseAmp), size=Xs.shape)
    data = np.random.normal(scale=noiseAmp, size=Xs.shape)
    return data


def _addNoise(data, noiseAmp):
    """Add normal (gaussian) noise to existing data.

    Args:
            noiseAmp (float): After sqrt(noiseAmp) specifies the STD of noise.
    """
    # data += np.random.normal(scale=np.sqrt(noiseAmp), size=data.shape)
    data += np.random.normal(scale=noiseAmp, size=data.shape)
    return data


def makeStim(
    type,
    sweepDurSec=10,
    startStimSec=2.0,
    durSec=5.0,
    yStimOffset=0,
    amp=10,
    freq=10,
    fs=10000,
    noiseAmp=1,
    rectify=True,
    autoPad=False,
    autoSave=True,
):
    """
    Make a different number of stim

    Args:
            durSec (float): Duration of stim
            rectify (bool): If tru then stim<0 = 0
    """

    # make the stim of duration durSec (then embed into longer sweepDurSec)
    if type == "Noise":
        data = _makeNoise(durSec, noiseAmp, fs)
    elif type == "Chirp":
        data = _makeChirp(durSec=durSec, amp=amp, maxFreqHz=freq, fs=fs)
    elif type == "Sin":
        data = _makeSin(durSec=durSec, amp=amp, freqHz=freq, fs=fs)
    elif type == "Epsp train":
        tmpSpikeTrain, data = getSpikeTrain(
            durSec=durSec,
            fs=10000,
            spikeFreq=freq,
            amp=amp,
            noiseAmp=0,
            baseLineShift=0,
        )
    elif type == "Integrate and Fire":
        data = integrateAndFire(durSec=durSec, freqHz=freq, fs=10000)
    # TODO: TOO SLOW TO BE USEFUL !!!
    elif type == "Stochastic HH":
        from sanpy.models.myStochHH import myRun2

        data = sanpy.models.myStochHH.myRun2()
    else:
        print(f'makeStim() type "{type}" not understood.')
        return

    if noiseAmp > 0 and type != "Noise":
        data = _addNoise(data, noiseAmp=noiseAmp)

    # always pad
    if autoPad:
        data = padData(data, autoPad=autoPad)

    if rectify:
        data[data < 0] = 0

    # always add offset, if 0 will have no effect
    data += yStimOffset

    #
    # insert stim (data) into final sweep (sweepData)
    Xs = (
        np.arange(fs * sweepDurSec) / fs
    )  # x/time axis, we should always be able to create this from (dur, fs)
    sweepData = np.zeros(shape=Xs.shape)
    xStartPnt = int(fs * startStimSec)
    xStopPnt = xStartPnt + len(data)
    if xStopPnt > len(sweepData):
        xStopPnt = len(sweepData)
    sweepData[xStartPnt:xStopPnt] = data

    fileName = ""
    if autoSave:
        fileName = f"{type}_dur{durSec}_freq{freq}.atf"
        saveAtf(sweepData, fileName=fileName)

    #
    if autoSave:
        return sweepData, fileName
    else:
        return sweepData


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


def getSpikeTrain(
    durSec=1, fs=10000, spikeFreq=3, amp=10, noiseAmp=10, baseLineShift=-60
):
    """Get a spike train at given frequency.

    Arguments:
            durSec (int): Total number of seconds
            fs (int): Sampling frequency, 10000 for 10 kH
            spikeFreq (int): Frequency of events in spike train, e.g. simulated EPSPs
            amp (float): Amplitude of sum exponential kernel (getKernel)
    """
    n = int(durSec * fs)  # total number of samples
    numSpikes = int(durSec * spikeFreq)
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
    epspTrain -= baseLineShift

    # add noise
    if noiseAmp == 0:
        pass
    else:
        noise_power = 0.001 * fs / noiseAmp
        epspTrain += np.random.normal(scale=np.sqrt(noise_power), size=epspTrain.shape)

    #
    # t = np.linspace(0, durSec, n, endpoint=True)

    #
    return spikeTrain, epspTrain


def integrateAndFire(durSec, freqHz, fs):
    """
    See: https://mark-kramer.github.io/Case-Studies-Python/IF.html
    """
    print("integrateAndFire()")
    # durSec = 50
    # fs = 10000
    dt = 1 / fs
    durPnts = (1 / dt) * durSec
    durPnts = int(durPnts)
    print("  durPnts:", durPnts)

    # constant current
    constantAmp = 0.7
    I = np.zeros(durPnts) + constantAmp
    print(f"  constantAmp:{constantAmp} I:{I.shape}")
    # plus sin
    sinAmp = 0.5
    sinFreq = freqHz
    rmsMult = 1 / np.sqrt(2)
    sinRms = sinAmp * rmsMult
    # want sinRms to equal constantAMp
    sinAmp = constantAmp / rmsMult
    iSin = _makeSin(durSec=durSec, amp=sinAmp, freqHz=sinFreq, fs=fs)
    print(f"  sinAmp:{sinAmp} sinRms:{sinRms} iSin:{iSin.shape}")
    I += iSin
    # Pluse noise
    noiseAmp = 1
    I += np.random.normal(scale=noiseAmp, size=I.shape)

    # I = 2					  # constant current
    C = 1  # capacitance
    Vth = 1
    # voltage threshold.
    Vreset = 0
    # reset voltage.
    V = np.zeros(durPnts)  # Initialize V.
    V[0] = 0.2
    # Set the initial condition.

    spikeTimesSeconds = []
    for k in range(1, durPnts - 1):  # March forward in time,
        V[k + 1] = V[k] + dt * (I[k] / C)  # Update the voltage,
        if V[k + 1] > Vth:  # ... and check if the voltage exceeds the threshold.
            V[k + 1] = Vreset
            spikeTimesSeconds.append(k * dt)

    print(f"  numSpikes:{len(spikeTimesSeconds)}")
    spikeTimeAmp = [Vth] * len(spikeTimesSeconds)

    t = np.arange(0, len(V)) * dt  # Define the time axis.

    """
	fig, axs = plt.subplots(3, 1, sharex=True)
	axs[0].plot(t,I, '-k', linewidth=1)
	axs[1].plot(t,V, '-k', linewidth=1)
	axs[1].plot(spikeTimesSeconds, spikeTimeAmp, 'or')

	isi_sec = np.diff(spikeTimesSeconds)
	spikeFreq = [1/isi for isi in isi_sec]
	axs[2].plot(spikeTimesSeconds[1:], spikeFreq, 'o')

	axs[0].set_ylabel('Current')
	axs[1].set_ylabel('Vm')

	axs[2].set_xlabel('Time (s)')
	axs[2].set_ylabel('Spike Frequency (Hz)')

	#
	plt.show()
	"""

    return V


if __name__ == "__main__":
    amp = 10
    durSec = 20
    fs = 10000

    data = makeStim("sin")
    data = makeStim("sin + noise")
    data = makeStim("chirp")

    integrateAndFire()

    """
	plotData(data)

	loadedData = _loadAtf(fileName)
	plotData(loadedData)
	"""
