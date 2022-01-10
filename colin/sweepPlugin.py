# 20220106

import os
import math
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

import sanpy

from colinAnalysis import bAnalysis2
#from stochAnalysis import plotStimFileParams
from stochAnalysis import plotRaw

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def plotOne2(ba : bAnalysis2, doSave=False):
    """
    Try plotting from df with seaborn
    
    Not working
    """
    df = ba.isiStats()

    print(df.columns)

    fig, axs = plt.subplots(1, 1, figsize=(5, 5))
    fig.suptitle(ba.fileName)

    yStat = 'cvISI'
    
    # markers are different for noise amp or no noise amp
    markers = []
    for idx, noiseAmp in enumerate(df['Noise Amp']):
        yVal = df.loc[idx, yStat]
        if math.isnan(yVal):
            # no marker for nan value
            continue
        marker = '^' if isinstance(noiseAmp,str) else 's'
        markers.append(marker)

    hue = None #'sweep'
    style = 'Noise Amp'
    #markers = True
    sns.lineplot(data=df, x='sweep', y=yStat,
                        hue=hue, style=style,
                        markers=markers,
                        ax=axs)

def plotHist(ba : bAnalysis2, axs=None, doSave=False):
    """
    plot ISI Histogram, one per sweep
    """
    dfISI = ba.isiStats()
    #print(dfISI)

    #startSec, stopSec = ba.getStimStartStop()
    df = ba.reduce()

    #print(df.columns)

    sweeps = df['sweep'].unique()
    numSweeps = len(sweeps)

    plotSweep = []
    plotCV = []

    # plot
    if axs is None:
        fig, axs = plt.subplots(numSweeps, 1, figsize=(5, 7), sharex=True)
        #axs = np.ravel(axs)
        fig.suptitle(ba.fileName)

    for sweep in sweeps:
        dfPlot = df[ df['sweep']==sweep ]

        ipi_ms = dfPlot['ipi_ms']
    
        bins='auto'
        axs[sweep].hist(ipi_ms)

        noiseAmp = dfISI.loc[sweep, 'Noise Amp']
        cvISI = dfISI.loc[sweep, 'cvISI']
        numIntervals = dfISI.loc[sweep, 'count']

        if len(str(noiseAmp)) == 0:
            noiseAmp = 'None'
        legendStr = f'noise amp = {noiseAmp}\ncvISI={cvISI}\ncount={numIntervals}'
        #print(legendStr)

        props = dict(boxstyle='round', facecolor='gray', alpha=0.5)
        # place a text box in upper left in axes coords
        axs[sweep].text(0.8, 0.95, legendStr, transform=axs[sweep].transAxes, fontsize=9, verticalalignment='top', bbox=props)

        plotSweep.append(sweep)
        plotCV.append(cvISI)


    if doSave:
        saveName = os.path.splitext(ba.fileName)[0] + '_isi.png'
        logger.info(f'saving: {saveName}')
        fig.savefig(saveName, dpi=300)

    #
    fig2, axs2 = plt.subplots(1, 1, figsize=(4, 4), sharex=True)
    #axs = np.ravel(axs)
    fig2.suptitle(ba.fileName)
    axs2.plot(plotSweep, plotCV, 'o-k')

    if doSave:
        saveName = os.path.splitext(ba.fileName)[0] + '_cv.png'
        logger.info(f'saving: {saveName}')
        fig2.savefig(saveName, dpi=300)

def plotOne(ba : bAnalysis2, axs=None, doSave=False):
    """
    Plot stim noise (x) versus number of spikes (y) for each sweep in a recording
    
    Simplified analysis inspired by Laura

    Args:
        ba (bAnalysis2) file to plot
    """
    
    dfStimFile = ba._stimFileAsDataFrame()  # get underlying atf file params (from stimGen2)
    #('dfStimFile:')
    #print(dfStimFile)

    numSweeps = ba.numSweeps  # len(dfStimFile)  # TODO: USe ba.numSweeps

    # assuming stim start and dur are identical across sweeps
    # find first sweep that has stim params defined
    # when no stim params defined, there was no stimulus (from an atf)
    startSec = None
    durSec = None
    stopSec = None
    for idx, sweep in enumerate(range(numSweeps)):
        tmpStartSec = dfStimFile.loc[sweep, 'start(s)']
        if not isinstance(tmpStartSec, str):
            startSec = tmpStartSec
            durSec = dfStimFile.loc[sweep, 'dur(s)']
            stopSec = startSec + durSec
            break

    xPlot = []
    yPlot = []
    xPlotBlank = []
    yPlotBlank = []
    xNoiseAmp = []
    for idx, sweep in enumerate(range(numSweeps)):
        #file = dfStimFile.loc[sweep, 'file']  # abf file, empty when no atf
        try:
            theType = dfStimFile.loc[sweep, 'type']
            noiseAmp = dfStimFile.loc[sweep, 'noise amp']
        except (KeyError) as e:
            logger.error(f'did not find sweep {sweep} in dfStimFile')
            theType = 'pre'  # so we trigger ignorType
            noiseAmp = None

        #startSec = dfStimFile.loc[sweep, 'start(s)']
        #durSec = dfStimFile.loc[sweep, 'dur(s)']
        #stopSec = startSec + durSec
    
        ignoreType = ['pre', 'post']
        #if theType in ignoreType:
        #    print(f'"{startSec}" "{durSec}" {type(startSec)}')
        #    continue

        dfOne = ba.analysisDf
        #print(dfOne.columns)

        # reduce by sweep
        dfTwo = dfOne[ dfOne['sweep'] == sweep]

        # reduce by start/stop seconds
        dfThree = dfTwo[ (dfTwo['peak_sec']>=startSec) & (dfTwo['peak_sec']<=stopSec)]
        numEvents = len(dfThree)

        #print(f'  abf file:{ba.fileName} sweep:{sweep} noiseAmp:{noiseAmp} numEvents:{numEvents}')
        
        #xPlot.append(noiseAmp)
        xPlot.append(sweep)
        if theType in ignoreType:
            #xPlotBlank.append(sweep)
            yPlotBlank.append(numEvents)
            yPlot.append(float('nan'))
            xNoiseAmp.append('None')
        else:
            yPlot.append(numEvents)
            yPlotBlank.append(float('nan'))
            xNoiseAmp.append(str(noiseAmp))

    # plot
    if axs is None:
        fig, axs = plt.subplots(1, 1, figsize=(5, 5))
        fig.suptitle(ba.fileName)

    axs.plot(xPlot, yPlot, 'o-')
    axs.plot(xPlot, yPlotBlank, '^k')
    
    axs.set_xlim(0, numSweeps-1)
    axs.set_xticks(range(numSweeps))

    axs.set_xticklabels(xNoiseAmp)    

    # Just for appearance's sake
    axs.margins(0.05)
    axs.axis('tight')

    axs.set_xlabel('Sweeps (Noise Amp)')
    axs.set_ylabel('Number Of Spikes')

    textstr = 'Noise Amp\n'
    for idx, noise in enumerate(xNoiseAmp):
        textstr += f'{idx}: {noise}\n'
    textstr = textstr[0:-1]
    props = dict(boxstyle='round', facecolor='gray', alpha=0.5)
    # place a text box in upper left in axes coords
    axs.text(0.85, 0.95, textstr, transform=axs.transAxes, fontsize=10, verticalalignment='top', bbox=props)

    if doSave:
        saveName = os.path.splitext(ba.fileName)[0] + '_count.png'
        logger.info(f'saving: {saveName}')
        fig.savefig(saveName, dpi=300)

if __name__ == '__main__':
    includeList = []
    path = '/media/cudmore/data/stoch-res/new20220104/2021_12_13_0001.abf'
    includeList.append(path)
    path = '/media/cudmore/data/stoch-res/new20220104/2021_12_15_0002.abf'
    includeList.append(path)
    path = '/media/cudmore/data/stoch-res/new20220104/2021_12_15_0008.abf'
    includeList.append(path)
    path = '/media/cudmore/data/stoch-res/new20220104/2021_12_27_0004.abf'
    includeList.append(path)
    path = '/media/cudmore/data/stoch-res/new20220104/2021_12_27_0005.abf'
    includeList.append(path)
    path = '/media/cudmore/data/stoch-res/new20220104/2021_12_27_0006.abf'
    includeList.append(path)
    path = '/media/cudmore/data/stoch-res/new20220104/2021_12_28_0002.abf'
    includeList.append(path)
    
    # debug
    path = '/media/cudmore/data/stoch-res/new20220104/2021_12_27_0006.abf'
    includeList = [path]

    baList = []
    for path in includeList:
        ba = bAnalysis2(path)

        thresholdValue = -40  # mV
        detectionDict = ba.detectionParams
        detectionDict['threshold'] = thresholdValue
        detectionDict['distance'] = 400 * 10 # minimum number of points between peaks (250 pnts default)
        detectionDict['width'] = [50, 800*10]
        detectionDict['doBaseline'] = False
        detectionDict['preFootMs'] = 50 * 10
        detectionDict['verbose'] = False
        
        ba.detect(detectionDict=detectionDict)
        baList.append(ba)

    print('plotting ...')
    for ba in baList:
        print('  plotting:', ba)
    
        #plotRaw(ba, doSave=True)
        #plotOne(ba, doSave=True)
        #plotOne2(ba, doSave=True)
        
        plotHist(ba, doSave=True)

        dfISI = ba.isiStats()
        print('isiStats:')
        print(dfISI)

    plt.show()