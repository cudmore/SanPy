"""
Estimate the time our spike detection takes.

    - Load an abf with lots of spikes
    - loop through the number of seconds in the recording
        - spike detect from 0 to i sec and calculate the time it takes

Note: the raw data for this to run is not provided in the repo. We can provide it upon request.
"""

import os
import sys
import time
import numpy as np
import pandas as pd
import scipy

from sklearn.linear_model import LinearRegression

import matplotlib.pyplot as plt  # just to show plots during script
import seaborn as sns

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def timingFigure():    
    # load file
    path = '/Users/cudmore/Dropbox/data/san-ap/20191009_0006.abf'
    if not os.path.isfile(path):
        logger.warning(f'File not found. This file was not included in the repo.')
        logger.warning(f'  {path}')
        logger.warning(f'  please contact rhcudmore@ucdavis.edu if you want a copy of this file')
        sys.exit()
        
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

def plotFigure(df : pd.DataFrame):
    logger.info(f'x is numSpikes, y is time (sec)')
    x = 'numSamples'  # 'numSpikes'
    y = '_timeItTook_filtered'
    sns.scatterplot(x=x, y=y, data=df)
    sns.despine()
    plt.show()

def saveResults(runNumber, timeItTook, numSamples, numSpikes):
    df = pd.DataFrame()
    df['runNumber'] = runNumber
    df['timeItTook'] = timeItTook
    df['numSamples'] = numSamples
    df['numSpikes'] = numSpikes
    
    path = '/Users/cudmore/Desktop/sanpy-benchmark-20230313.csv'
    df.to_csv(path, index=False)

def linearFit():
    path = '/Users/cudmore/Desktop/sanpy-benchmark-20230313.csv'
    df : pd.DataFrame = pd.read_csv(path)
    
    # add a seconds colum (num samples - >seconds)
    # assuming dt = 0.01 ms (100 samples per second)
    df['seconds'] = df['numSamples'] / 10000

    # filter points with each runNumber
    for run in df['runNumber'].unique():
        print('run:', run, type(run))
        dfRun = df.loc[df['runNumber'] == run]
        _timeItTook = dfRun['timeItTook']
        _timeItTook_filtered = scipy.ndimage.median_filter(_timeItTook,5)
        df.loc[df['runNumber'] == run, 'timeItTook_filtered'] = _timeItTook_filtered

    print(df.head())

    #y = df['timeItTook'].to_numpy()
    y = df['timeItTook_filtered'].to_numpy()
    
    # numSpikes is linear wrt timeItTook
    # numSamples has exponential increase in timeItTook?
    x = df['numSamples'].to_numpy().reshape(-1, 1)
    x = df['seconds'].to_numpy().reshape(-1, 1)
    x = df['numSpikes'].to_numpy().reshape(-1, 1)

    #x = x.reshape(-1, 1)
    #x = x.ravel()
    #y = y.ravel()
    print('x.shape:', x.shape)
    print('y.shape:', y.shape)

    # fit to line
    model = LinearRegression().fit(x, np.log(y))
    print(f"linear intercept: {model.intercept_}")
    print(f"linear slope: {model.coef_}")

    x = x.ravel()

    # fit to exponential
    p = np.polyfit(x, np.log(y), 1)
    # Convert the polynomial back into an exponential
    a = np.exp(p[1])
    b = p[0]
    x_fitted = np.linspace(np.min(x), np.max(x), 100)
    y_fitted = a * np.exp(b * x_fitted)

    sns.set_context("talk")

    ax = plt.axes()
    #ax.scatter(x, y)
    hue = None  # runNumber
    sns.scatterplot(x='numSpikes', y='timeItTook_filtered', hue=hue, data=df, ax=ax)

    ax.plot(x_fitted, y_fitted, 'k', label='Fitted curve')

    ax.set_yscale('log')

    sns.despine()
    plt.tight_layout()

    plt.show()

    # x=numSpikes
    # intercept: 0.03681416695543044
    # slope: [0.0009]

    #plotFigure(df)

if __name__ == '__main__':
    
    if 0:
        # run spike detection on progressively longer seconds
        # takes a few minutes to run
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
        # load out results
        linearFit()