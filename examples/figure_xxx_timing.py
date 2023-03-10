"""
Estimate the time our spike detection takes.

    - Load an abf with lots of pikes
    - loop through the number of seconds in the recording
        - spike detect from 0 to i sec and calculate the time it takes
"""

import time
import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression

import matplotlib.pyplot as plt  # just to show plots during script

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def timingFigure():    
    # load file
    path = '/Users/cudmore/Dropbox/data/san-ap/20191009_0006.abf'
    ba = sanpy.bAnalysis(path)
 
    # get all detection presets
    _detectionParams = sanpy.bDetection()    
    # select 'SA Node' presets
    _dDict = _detectionParams.getDetectionDict('SA Node')

    # TODO: this is a bug ... fix it
    _dDict['startSeconds'] = 0

    recordingDur = ba.fileLoader.recordingDur
    recordingDurInt  = int(recordingDur)
    #recordingDurInt = 100

    logger.info(f'recordingDurInt: {recordingDurInt}')

    # make a range to test, step by 2 seconds
    secondsRange = np.arange(1, recordingDurInt, 2)

    timeItTook = []
    numSamples = []
    numSpikes = []
    for stopSec in secondsRange:
        _startSec = time.time()

        # if stopSec > 100:
        #     break

        _dDict['stopSeconds'] = stopSec
        ba.spikeDetect(_dDict)

        _numSamples = stopSec * 10000
        numSamples.append(_numSamples)

        _stopSec = time.time()
        _elapsedTime = round(_stopSec-_startSec,2)
        timeItTook.append(_elapsedTime)
        numSpikes.append(ba.numSpikes)

        if (stopSec-1) % 50 == 0:
            logger.info(f'stopSec:{stopSec} of {recordingDurInt} got {ba.numSpikes} spikes in {_elapsedTime} seconds')

    return timeItTook, numSamples, numSpikes

def plotFigure(numSpikes, timeItTook):
    logger.info(f'x is numSpikes, y is time (sec)')
    plt.plot(numSpikes, timeItTook, 'ok')
    plt.show()

def saveResults(runNumber, timeItTook, numSamples, numSpikes):
    df = pd.DataFrame()
    df['runNumber'] = runNumber
    df['timeItTook'] = timeItTook
    df['numSamples'] = numSamples
    df['numSpikes'] = numSpikes
    
    path = '/Users/cudmore/Desktop/sanpy-benchmark-20230305.csv'
    df.to_csv(path)

def linearFit():
    path = '/Users/cudmore/Desktop/sanpy-benchmark-20230305-v1.csv'
    df = pd.read_csv(path)
    
    y = df['timeItTook'].to_numpy()
    x = df['numSamples'].to_numpy().reshape(-1, 1)
    x = df['numSpikes'].to_numpy().reshape(-1, 1)

    model = LinearRegression().fit(x, y)
    print(f"intercept: {model.intercept_}")
    print(f"slope: {model.coef_}")

    # x=numSpikes
    # intercept: 0.03681416695543044
    # slope: [0.0009]

    plotFigure(x, y)

if __name__ == '__main__':
    
    if 0:
        numRuns = 10
        runNumber = []
        timeItTook = []
        numSamples = []
        numSpikes = []
        for oneRun in range(numRuns):
            _timeItTook, _numSamples, _numSpikes = timingFigure()
            for x in _timeItTook:
                timeItTook.append(x)
                runNumber.append(oneRun)
            for x in _numSamples:
                numSamples.append(x)
            for x in _numSpikes:
                numSpikes.append(x)
                
        plotFigure(numSpikes, timeItTook)
        saveResults(runNumber, timeItTook, numSamples, numSpikes)

    if 1:
        linearFit()