import sys
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns

import sanpy
from sanpy import bAnalysis
from sanpy import kymAnalysis

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def run():
    #path = '/Users/cudmore/Dropbox/data/cell-shortening/cell 03.tif'
    path = '/Users/cudmore/Dropbox/data/cell-shortening/cell 05.tif'
    #path = '/Users/cudmore/Dropbox/data/cell-shortening/Cell 04_C002T001.tif'

    kym = kymAnalysis(path)
    
    # need to perform analysis in sanpy and then load
    # need to do this to set proper rect roi
    #kym.analyzeDiameter()

    df = kym.getResultsAsDataFrame()
    print(df)

    if 0:
        xStat = 'time_sec'
        yStat = 'sumintensity'
        hue = None
        legend = False
        ax = None
        sns.scatterplot(x=xStat, y=yStat, hue=hue, data=df, ax=ax, legend=legend)
        plt.show()

    if 0:
        imageData = kym.getImage().copy()
        imageData = np.rot90(imageData)
        print('imageData:', imageData.shape)  # (5000, 378)


        # remake sum of each line scan
        # by default kymAnalysis is normalizing to max
        m = imageData.shape[0]
        n = imageData.shape[1]
        _sumInt = [None] * n
        for x in range(n):
            _sumInt[x] = imageData[:,x].sum()

        _sumInt = np.array(_sumInt)
        print('_sumInt:', _sumInt.shape)

        _sumDif = np.diff(_sumInt, axis=0)
        print('_sumDif:', _sumDif.shape)

        plt.plot(_sumInt)
        # plt.plot(_sumDif)
        plt.show()

    ba = bAnalysis(path)  # load kymAnalysis
    print(ba)
    
    # checking derivative to see if we can detect with it
    # sum int is always normalized to max and deriv is taken from that
    sweepY = ba.fileLoader.sweepY
    f = ba.fileLoader._getDerivative()
    print(f.shape)

    plt.plot(f)
    # plt.plot(sweepY)
    plt.show()

    if 0:
        import seaborn_image as isns

        # this will create thicker lines and larger fonts than usual
        isns.set_context("notebook")

        # change image related settings
        isns.set_image(cmap="deep", despine=True)  # set the colormap and despine the axes
        isns.set_scalebar(color="red")  # change scalebar color

        # ax = isns.imgplot(imageData, dx=0.001, units="s")
        ax = isns.imgplot(imageData)

        plt.show()

def extractClips(pntList, y, prePnt=20, postPnt=20):
    """Extract clips from y using pntList points.
    
    Returns:
        list : List of np.array of clips
    """
    clipSize = postPnt+prePnt+1
    
    # make a list of clips where each is an empty numpy array of the correct length
    clips = [np.full(clipSize, np.nan)] * len(pntList)
    
    for i, pnt in enumerate(pntList):
        startPnt = pnt - prePnt
        stopPnt = pnt + postPnt
        if startPnt<0 or stopPnt>len(y)-1:
            pass
        else:
            clips[i] = np.array(y[startPnt:stopPnt])
        
    return clips

def testClips():
    """20230602 this works well !!!
    """

    path = '/Users/cudmore/Dropbox/data/cell-shortening/cell 05.tif'
    ba = sanpy.bAnalysis(path)
    
    # load saved analysis from h5 file
    hdfPath = '/Users/cudmore/Dropbox/data/cell-shortening/sanpy_recording_db.h5'
    ba._loadHdf_pytables(hdfPath)  # added 20230602

    # add new analysis results for diameter foot/peak
    from sanpy.kymAnalysis import kymUserAnalysis
    _kymUserAnalysis = kymUserAnalysis(ba)
    _kymUserAnalysis.defineUserStats()
    _kymUserAnalysis.run()
    # regenerate analysis df with new keys
    ba.regenerateAnalysisDataFrame()

    df = ba.asDataFrame()
    thresholdPnt = df['thresholdPnt']
    thresholdVal = df['thresholdVal']  # mV

    diameter_um = ba.kymAnalysis.getResults('diameter_um')

    prePnt = 20
    postPnt = 50

    # get clips of sum intensity (normal sanpy feature)
    sweepY = ba.fileLoader.sweepY
    # sweepY = sweepY[:]
    sumClips = extractClips(thresholdPnt, sweepY, prePnt=prePnt, postPnt=postPnt)

    # get clips of diameter based on sum intensity spike detection
    clips = extractClips(thresholdPnt, diameter_um, prePnt=prePnt, postPnt=postPnt)

    fig, ax = plt.subplots()
    ax2 = ax.twinx()
    for spikeIdx in range(len(clips)):
        ax.plot(sumClips[spikeIdx], 'k')
        ax2.plot(clips[spikeIdx], 'r')
        
    plt.show()

    # plot sumInt and diam on same plot (left/right axis)
    sweepY = ba.fileLoader.sweepY

    diam_peak_pnt = df['diam_peak_pnt']
    diam_peak = df['diam_peak']

    fig, ax = plt.subplots()
    
    # left
    ax.plot(sweepY, 'k')
    ax.plot(thresholdPnt, thresholdVal, 'o')

    # right
    ax2 = ax.twinx()
    ax2.plot(diameter_um, 'r')
    ax2.plot(thresholdPnt, diameter_um[thresholdPnt], 'og')
    ax2.plot(diam_peak_pnt, diam_peak, 'oy')

    # The constriction occurs at thesame time as the start of Ca++ increase
    # So fast it begs the question, "is Ca++ inclux what drives constriction?"
    # or is constriction a process running in parallael with Ca++ influx?

    plt.show()

    # plot the amp of peak diam change
    # does it change over time? what happens after burst?
    diam_amp = df['diam_amp']
    fig, ax = plt.subplots()
    ax.plot(diam_peak_pnt, diam_amp, 'ok')

    ax2 = ax.twinx()
    diam_time_to_peak_sec = df['diam_time_to_peak_sec']
    ax2.plot(diam_peak_pnt, diam_time_to_peak_sec, 'or')
    plt.show()

if __name__ == '__main__':
    #run()
    testClips()