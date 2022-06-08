"""
Important, had to modify parsing comment of atf

see abb in:
    /home/cudmore/Sites/SanPy/sanpy_env/lib/python3.8/site-packages/pyabf/atf.py", line 63
"""
import os, sys
import numpy as np
import pandas as pd
import seaborn as sns

from typing import List, Set, Dict, Tuple, Optional

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from colinAnalysis import bAnalysis2
from sanpy.interface.plugins.stimGen2 import buildStimDict  # readFileParams

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def load(path):

    stimulusFileFolder = os.path.split(path)[0] #'/media/cudmore/data/stoch-res' #os.path.split(path)[0]

    ba = bAnalysis2(path, stimulusFileFolder=stimulusFileFolder)
    print(ba)

    #print('_stimFile:', ba._stimFile)
    #print('_stimFileComment:', ba._stimFileComment)

    '''
    # load and print the parameters from the atf stimulus file
    atfPath = '/media/cudmore/data/stoch-res/sanpy_20211206_0007.atf'
    atfParams = readFileParams(atfPath)
    print('=== atf file params', atfPath)
    print(atfParams)
    '''

    return ba

def old_plotStimFileParams(ba):
    d = ba.stimDict
    if d is None:
        return

    dList = buildStimDict(d, path=ba.filePath)
    #for one in dList:
    #    print(one)
    df = pd.DataFrame(dList)
    print(df)
    return df

def detect(ba, thresholdValue = -20):
    """
    Detect spikes
    """
    detectionDict = ba.detectionParams
    detectionDict['threshold'] = thresholdValue
    detectionDict['width'] = [50, 800*10]
    detectionDict['doBaseline'] = False
    detectionDict['preFootMs'] = 50 * 10
    detectionDict['verbose'] = True
    ba.detect(detectionDict=detectionDict)

    if ba.analysisDf is not None:
        logger.info(f'detected {len(ba.analysisDf)} spikes')
        #print(ba.analysisDf.head())
    else:
        logger.info(f'detected No spikes')

def reduce(ba):
    """
    Reduce spikes based on start/stop of sin stimulus

    TODO:
        Use readFileParams(atfPath) to read stimulus ATF file and get start/stop

    Return:
        df of spikes within sin stimulus
    """
    df = ba.asDataFrame()
    if ba.stimDict is not None:
        #print(ba.stimDict)
        '''
        stimStartSeconds = ba.stimDict['stimStartSeconds']
        durSeconds = ba.stimDict['durSeconds']
        startSec = stimStartSeconds
        stopSec = startSec + durSeconds
        '''

        startSec, stopSec = ba.getStimStartStop()

        try:
            #df = df[ (df['peak_sec']>=startSec) & (df['peak_sec']<=stopSec)]
            df = df[ (df['thresholdSec']>=startSec) & (df['thresholdSec']<=stopSec)]
        except (KeyError) as e:
            logger.error(f'my key error: {e}')

    return df

def old_plotStats(ba):
    """
    Plot xxx
    """
    df = reduce(ba)

    noiseAmpList = [0, 0.5, 1, 1.5]
    cvISI_list = [None] * len(noiseAmpList)
    cvISI_invert_list = [None] * len(noiseAmpList)
    pSpike_list = [None] * len(noiseAmpList)

    for idx in range(ba.numSweeps):
        #abf.setSweep(idx)
        dfStats = df[ df['sweep']== idx]

        peakSec = dfStats['peak_sec']
        peakVal = dfStats['peak_val']

        # given 20 peaks, calculate "probability of spike"
        # 20 spikes yields p=1
        # 10/20 spikes yields p=0.5

        nSinPeaks = 20 # number of peaks in sin wave
        pSpike = len(dfStats)/nSinPeaks
        isiSec = np.diff(peakSec)
        cvISI = np.std(isiSec) / np.mean(isiSec)
        cvISI_invert = 1 / cvISI
        print(f'{idx} n:{len(dfStats)} pSpike:{pSpike} cvISI:{cvISI} cvISI_invert:{cvISI_invert}')

        cvISI_list[idx] = cvISI
        cvISI_invert_list[idx] = cvISI_invert
        pSpike_list[idx] = pSpike

    # plot
    fig, axs = plt.subplots(3, 1, sharex=True, figsize=(8, 6))
    axs[0].plot(noiseAmpList, cvISI_list, 'o-k')
    axs[1].plot(noiseAmpList, cvISI_invert_list, 'o-k')
    axs[2].plot(noiseAmpList, pSpike_list, 'o-k')

    axs[0].set_ylabel('cvISI')
    axs[1].set_ylabel('1/cvISI')
    axs[2].set_ylabel('Prob(spike) per sin peak')
    #
    axs[2].set_xlabel('Noise Amp (pA)')

def old_plotShotPlot(df):
    """
    Plot ISI(i) versus ISI(i-1)

    Args:
        df (DataFrame): already reduce()
    """
    file = df['file'].values[0]

    fig, axs = plt.subplots(1, 1, sharex=True, figsize=(8, 6))
    axs = [axs]
    fig.suptitle(file)

    colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k']

    sweeps = df['sweep'].unique()
    print(f'plotShotPlot() num sweeps:{len(sweeps)} {sweeps}')
    for sweepIdx, sweep in enumerate(sweeps):
        dfPlot = df[ df['sweep'] == sweep ]

        peakSec = dfPlot['peak_sec']
        isi = np.diff(peakSec)
        isi_minusOne = isi[0:-2]
        isi = isi[1:-1]

        axs[0].scatter(isi, isi_minusOne, marker='o', c=colors[sweepIdx])

        axs[0].set_ylabel('ISI -1 (s)')
        axs[0].set_xlabel('ISI (s)')

# see ba3 in colinAnalysis
def getSpikePhase(thresholdSeconds : List[float], stimFreq : float, stimStartSeconds : float):
    """Given a list of spike times, return the phase [0,1] 

    Args:
        thresholdSeconds
        stimFreq
        stimStartSeconds
    """
    # caller should reduce spikes to start stop

    sinInterval = 1 / stimFreq
    thresholdSeconds -= stimStartSeconds
    peakPhase_float = thresholdSeconds/sinInterval
    thresholdPhase = peakPhase_float - peakPhase_float.astype(int)
    return thresholdPhase

def plotPhaseHist(ba3, axs=None, hue='sweep',
                    plotTheseSweeps : list = None, saveFolder=None):
    """
    Plot hist of spike arrival times as function of phase/angle within sine wave

    Args:
        ba3:
        axs:
        hue
        plotTheseSweeps: Limit plot to list of sweeps
    """
    
    if ba3.stimDict is None:
        return

    '''
    df = ba3.asDataFrame()
    if df is None:
        return
    '''

    #logger.info(f'hue: "{hue}"')

    df = reduce(ba3)

    if len(df)==0:
        logger.error(f'got no spikes after reduce -->> return')
        return None

    # grab freq and startSec from header
    stimStartSeconds = ba3.stimDict['stimStart_sec']
    stimFreq = ba3.stimDict['stimFreq']  # TODO: will not work if we are stepping frequency
    stimAmp = ba3.stimDict['stimAmp']

    file = df['file'].values[0]

    if plotTheseSweeps is not None:
        numPlots = len(plotTheseSweeps)
    else:
        numPlots = ba3.numSweeps

    sinInterval = 1 / stimFreq
    hueList = df[hue].unique()  # hue is 'sweep'
    #numHue = len(hueList)
    bins = 'auto'

    print(f'plotPhaseHist() stimStartSeconds:{stimStartSeconds} stimFreq:{stimFreq} sinInterval:{sinInterval} bins:{bins}')

    if axs is None:
        fig, axs = plt.subplots(numPlots, 1, sharex=False, figsize=(3, 5))
        fig.suptitle(file)
        #axs[numPlots-1].set_xlabel('Phase')

    axs_sin = [None] * numPlots

    fs = ba3.dataPointsPerMs * 1000  # 10000
    durSec = 1 / stimFreq
    Xs = np.arange(fs*durSec) / fs  # x/time axis, we should always be able to create this from (dur, fs)
    sinData = stimAmp * np.sin(2*np.pi*(Xs)*stimFreq)
    xPlot = Xs * stimFreq  #/ fs  # normalize to interval [0,1] fpr plotting

    # for gianni
    gMasterDf = None

    #for idx,oneHue in enumerate(hueList):
    if plotTheseSweeps is not None:
        plotSweepList = plotTheseSweeps
    else:
        plotSweepList = range(ba3.numSweeps)  # all sweeps

    myLineWidth = 0.5

    #for idx in range(numSweeps):
    for _plotIdx, _sweepNumber in enumerate(plotSweepList):
        if not _sweepNumber in hueList:
            continue

        #oneHue = idx
        #oneHue = _sweepNumber

        #dfPlot = df[ df[hue]==oneHue ]
        dfPlot = df[ df[hue]==_sweepNumber ]

        if len(dfPlot) < 2:
            logger.error(f'sweep {_sweepNumber} only had {len(dfPlot)} spikes ... not plotting')
            continue

        '''
        peakSecs = dfPlot['peakSec']
        peakSecs -= stimStartSeconds
        #peakPhase =  peakSecs - (peakSecs/sinInterval).astype(int)
        peakPhase_float = peakSecs/sinInterval
        peakPhase = peakPhase_float - peakPhase_float.astype(int)
        '''

        peakSecs_values = dfPlot['peakSec'].values
        peakPhase = getSpikePhase(peakSecs_values, stimFreq, stimStartSeconds)

        #print('   !!! peakPhase is:', 'file:', file, 'sweep:', idx, type(peakPhase))
        #print(peakPhase)
        
        # for gianni
        thisDf = pd.DataFrame()
        thisDf['peakPhase'] = peakPhase # to get the number of rows correct
        thisDf.insert(0, 'sweep', _sweepNumber)  # thisDf['sweep'] = oneHue
        thisDf.insert(0, 'filename', ba3.getFileName())  # thisDf['filename'] = ba.fileName
        if gMasterDf is None:
            gMasterDf = thisDf
        else:
            gMasterDf = gMasterDf.append(thisDf, ignore_index=True)

        # debug
        '''
        tmpDf = pd.DataFrame()
        tmpDf['peakSecs'] = peakSecs
        tmpDf['peakPhase_float'] = peakPhase_float
        tmpDf['peakPhase_int'] = peakPhase_float.astype(int)
        tmpDf['peakPhase'] = peakPhase
        print(idx, tmpDf.head())
        '''

        #sns.histplot(x='ipi_ms', data=dfPlot, bins=numBins, ax=axs[idx])
        axs[_plotIdx].hist(peakPhase, bins=bins, density=False,
                        color='gray',
                        ec='k')

        axs_sin[_plotIdx] = axs[_plotIdx].twinx()
        axs_sin[_plotIdx].plot(xPlot, sinData, 'r', lw=myLineWidth)

        '''
        if idx == len(hueList)-1:
            axs[idx].set_xlabel('Phase')
        '''

        # label x-axis of subplots
        '''
        isLastSweep = _plotIdx == (numPlots - 1)
        if isLastSweep:
            axs[_plotIdx].set_xlabel('Phase')
        else:
            #axs[idx].spines['bottom'].set_visible(False)
            axs[_plotIdx].tick_params(axis="x", labelbottom=False) # no labels
            axs[_plotIdx].set_xlabel('')
        '''

    #
    # remove all lines/labels
    for _plotIdx, _sweepNum in enumerate(plotSweepList):
        # remove all axis labels
        lastPlot = _plotIdx == len(plotSweepList)-1
        remove_x = True
        if lastPlot:
            remove_x = False
        _removeAxisLines(axs[_plotIdx], remove_x=remove_x)
        _removeAxisLines(axs_sin[_plotIdx], remove_x=remove_x)

        # for stoch manuscript/grant
        if lastPlot:
            # specify bins, number of ticks is bins-1
            axs[_plotIdx].xaxis.set_major_locator(MaxNLocator(5))
            axs_sin[_plotIdx].xaxis.set_major_locator(MaxNLocator(5)) 
            # x-label as pi
            xTickLoc = [0, .25, .5, .75, 1]
            axs[_plotIdx].set_xticks(xTickLoc)
            axs_sin[_plotIdx].set_xticks(xTickLoc)
            xTickLabels = ['0', '', '$\pi$', '', '2$\pi$']
            axs[_plotIdx].set_xticklabels(xTickLabels)
            axs_sin[_plotIdx].set_xticklabels(xTickLabels)

    #plotStimFileParams(ba)

    if saveFolder is not None:
        saveName = os.path.splitext(ba3.getFileName())[0] + '_phase.png'
        savePath = os.path.join(saveFolder, saveName)
        logger.info(f'saving: {savePath}')
        fig.savefig(savePath, dpi=300)

        # for gianni
        saveName = os.path.splitext(ba3.getFileName())[0] + '_gianni.csv'
        savePath = os.path.join(saveFolder, saveName)
        logger.info(f'  gianni savePath: {savePath}')
        #print(gMasterDf)
        gMasterDf.to_csv(savePath, index=False)

    # one row per sweep
    return gMasterDf, fig

def _removeAxisLines(axs, remove_x=True, remove_y=True):
    # remove all axis labels
    if remove_x:
        axs.axes.xaxis.set_ticklabels([])
        axs.spines['bottom'].set_visible(False)
        axs.set_xticks([])
        axs.set_xticks([], minor=True)

    if remove_y:
        axs.axes.yaxis.set_ticklabels([])
        axs.spines['left'].set_visible(False)
        axs.set_yticks([])
        axs.set_yticks([], minor=True)

def isiStats(ba, hue='sweep'):
    df = ba.analysisDf
    if df is None:
        return

    df = reduce(ba)

    statList = []

    statStr = 'ipi_ms'

    hueList = df[hue].unique()
    for idx,oneHue in enumerate(hueList):
        dfPlot = df[ df[hue]==oneHue ]
        ipi_ms = dfPlot[statStr]

        meanISI = np.nanmean(ipi_ms)
        stdISI = np.nanstd(ipi_ms)
        cvISI = stdISI / meanISI
        cvISI_inv = np.nanstd(1/ipi_ms) / np.nanmean(1/ipi_ms)

        oneDict = {
            'file': ba.fileName,
            'stat': statStr,
            'count': len(ipi_ms),
            'minISI': np.nanmin(ipi_ms),
            'maxISI': np.nanmax(ipi_ms),
            'stdISI': round(stdISI,3),
            'meanISI': round(np.nanmean(ipi_ms),3),
            'medianISI': round(np.nanmedian(ipi_ms),3),
            'cvISI': cvISI,
            'cvISI_inv': cvISI_inv,

        }

        statList.append(oneDict)

    #
    retDf = pd.DataFrame(statList)
    return retDf

def plotHist(ba3, axs=None, hue='sweep', saveFolder=None):
    """
    Args:

        ba (bAnalysis3)
    """

    '''
    df = ba3.asDataFrame()
    if df is None:
        logger.error(f'did not find analysis for {ba}')
        return
    '''

    df = reduce(ba3)

    if len(df)==0:
        logger.error(f'after reduce, got empty df')
        return

    file = ba3.getFileName()  # df['file'].values[0]

    # same number of bins per hist
    bins = 'auto' #12
    statStr = 'isi_ms'

    numSweeps = ba3.numSweeps

    #hueList = df[hue].unique()
    #numHue = len(hueList)

    #logger.info(f'plotting hueList: {hueList}')

    # plot one hist per subplot
    if axs is None:
        numSubplot = numSweeps
        fig, axs = plt.subplots(numSubplot, 1, sharex=True, figsize=(8, 6))
        fig.suptitle(file)
        axs[numSubplot-1].set_xlabel('ISI (ms)')


    #for idx,oneHue in enumerate(hueList):
    for idx in range(numSweeps):
        #if not idx in hueList:
        #    continue

        oneHue = idx

        #hueList = df[hue].unique()

        dfPlot = df[ df[hue]==oneHue ]

        if len(dfPlot) < 2:
            logger.error(f'sweep {idx} only had {len(dfPlot)} spikes ... not plotting')
            continue

        # hist of isi
        # screws up x-axis line at 0 (annoying !!!)
        sns.histplot(x=statStr, data=dfPlot, bins=bins, ax=axs[idx])
        # screws up x-axis line at 0 (annoying !!!)
        #xStatVal = dfPlot[statStr]
        #axs[idx].hist(xStatVal, bins=bins, density=False)

        '''
        if idx == len(hueList)-1:
            axs[idx].set_xlabel('ipi_ms')
        else:
            axs[idx].set_xlabel('')
        '''

        # label x-axis of subplots
        lastSweep = idx == (numSweeps - 1)
        if lastSweep:
            axs[idx].set_xlabel(statStr)
        else:
            #axs[idx].spines['bottom'].set_visible(False)
            axs[idx].tick_params(axis="x", labelbottom=False) # no labels
            axs[idx].set_xlabel('')

    if saveFolder is not None:
        saveName = os.path.splitext(ba3.getFileName())[0] + '_hist.png'
        savePath = os.path.join(saveFolder, saveName)
        logger.info(f'saving: {savePath}')
        fig.savefig(savePath, dpi=300)

    '''
    logger.info('')
    dfStat = isiStats(ba)
    print(dfStat)

    plotStimFileParams(ba)
    '''

def old_plotRaw(ba, showDetection=True, showDac=True, axs=None, saveFolder=None):
    """
    Plot Raw data.

    Args:
        ba (bAnalysis2)
        showDetection (bool): Overlay detection parameters
        showDac (bool): Overlay Stimulus File DAC stimulus
        axs (matpltlib): If given then plot in this axes
    """

    numSweeps = ba.numSweeps

    if axs is None:
        fig, axs = plt.subplots(numSweeps, 1, sharex=True, sharey=True, figsize=(8, 6))
        if numSweeps == 1:
            axs = [axs]

        fig.suptitle(ba.getFileName())

    # If we are plotting Dac
    rightAxs = [None] * numSweeps

    # keep track of x/y min of each plot to make them all the same
    yRawMin = 1e9
    yRawMax = -1e9

    yDacMin = 1e9
    yDacMax = -1e9

    for idx in ba.sweepList:
        ba.setSweep(idx)

        lastSweep = idx == (numSweeps - 1)

        try:
            sweepC = ba.sweepC
        except (ValueError) as e:
            sweepC = None

        if showDac and sweepC is not None:
            rightAxs[idx] = axs[idx].twinx()
            rightAxs[idx].spines['right'].set_visible(True)
            if lastSweep:
                rightAxs[idx].set_ylabel('DAC (nA)')
            rightAxs[idx].plot(ba.sweepX, sweepC, 'r', lw=.5, zorder=0)

            yMin = np.min(sweepC)
            if yMin < yDacMin:
                yDacMin = yMin
            yMax = np.max(sweepC)
            if yMax > yDacMax:
                yDacMax = yMax

        if lastSweep:
            axs[idx].set_ylabel('Vm (mV)')

        axs[idx].plot(ba.sweepX, ba.sweepY, lw=0.5, zorder=10)

        yMin = np.min(ba.sweepY)
        if yMin < yRawMin:
            yRawMin = yMin
        yMax = np.max(ba.sweepY)
        if yMax > yRawMax:
            yRawMax = yMax

        if showDetection and ba.analysisDf is not None:
            #df = reduce(ba)
            df = ba.analysisDf
            dfPlot = df[ df['sweep']== idx]

            peakSec = dfPlot['peak_sec']
            peakVal = dfPlot['peak_val']

            axs[idx].plot(peakSec, peakVal, 'ob', markersize=3, zorder=999)

            footSec = dfPlot['foot_sec']
            footVal = dfPlot['foot_val']
            #axs[idx].plot(footSec, footVal, 'og', markersize=3, zorder=999)

        # label x-axis of subplots
        if lastSweep:
            axs[idx].set_xlabel('Time (s)')
        else:
            #axs[idx].spines['bottom'].set_visible(False)
            axs[idx].tick_params(axis="x", labelbottom=False) # no labels
            axs[idx].set_xlabel('')

        # get the zorder correct
        if showDac and sweepC is not None:
            axs[idx].set_zorder(rightAxs[idx].get_zorder()+1)
            axs[idx].set_frame_on(False)

    # set common y min/max
    # expand left axis by a percentage %
    percentExpand = 0.05
    thisExpand = (yRawMax - yRawMin) * percentExpand
    yRawMin -= thisExpand
    yRawMax += thisExpand
    for idx in ba.sweepList:
        axs[idx].set_ylim(yRawMin, yRawMax)
        if showDac and sweepC is not None:
            rightAxs[idx].set_ylim(yDacMin, yDacMax)

    #
    plt.tight_layout()

    if saveFolder is not None:
        saveName = os.path.splitext(ba.fileName)[0] + '_raw.png'
        savePath = os.path.join(saveFolder, saveName)
        logger.info(f'saving: {savePath}')
        fig.savefig(savePath, dpi=300)

def _getMin(val, array):
    """Get min between val and min of array.
    """
    arrayMin = np.min(array)
    if val < arrayMin:
        return val
    else:
        return arrayMin

def _getMax(val, array):
    arrayMin = np.max(array)
    if val > arrayMin:
        return val
    else:
        return arrayMin

def plotRaw4(ba3,
            axs = None,
            plotTheseSweeps : list = None
            ):
    """Plot raw data and stim in individual subplots.
    
    This is for stoch-res grant
    """

    import sanpy.atfStim

    if plotTheseSweeps is not None:
        numPlots = len(plotTheseSweeps)
        sweepList = plotTheseSweeps
    else:
        numPlots = ba3.numSweeps
        sweepList = ba3.sweepList

    numPlots2 = numPlots
    numPlots *= 2  # one axis for each of (raw, stim)

    # build figure
    if axs is None:
        sharey = False
        sharex = False
        fig, axs = plt.subplots(numPlots, 1, sharex=sharex, sharey=sharey, figsize=(3, 5))
        if numPlots == 1:
            axs = [axs]
        fig.suptitle(ba3.getFileName())

        #figStimOnly, axsstimOnly = plt.subplots(numPlots, 1, sharex=sharex, sharey=sharey, figsize=(4, 3))
        #figRawOnly, axsRawOnly = plt.subplots(numPlots, 1, sharex=sharex, sharey=sharey, figsize=(4, 3))

    # keep track of y min/max to make them all the same
    yRawMin = 1e9
    yRawMax = -1e9
    yStimMin = 1e9
    yStimMax = -1e9

    # grab freq and startSec from header
    stimStartSeconds = ba3.stimDict['stimStart_sec']
    stimFreq = ba3.stimDict['stimFreq']  # TODO: will not work if we are stepping frequency
    stimAmp = ba3.stimDict['stimAmp']

    # sometimes our noise is to big to overlay pure sin() no noise
    # remake some fake stimulus here using sanpy.atfStim.makeStim
    stimType = 'Sin'
    sweepDur_sec = 30
    yOffset = 0
    sinAmp = 0.002  # we can't see out sin() wave because noise is too big !!!
    sinAmp = 0.5
    sinFreq = stimFreq
    noiseAmp = 0
    rectify = False
    fs = 10000
    autoPad = False  # TODO: ALWAYS FALSE, my pre/post sweeps don't use this

    sinStep = 0
    noiseStep = 0.1

    stimStart_sec, stimStop_sec = ba3.getStimStartStop()
    stimDur_sec = stimStop_sec - stimStart_sec  # + 1 ???

    # plot each subplot
    for _plotIdx, _sweepNum in enumerate(sweepList):
        ba3.setSweep(_sweepNum)  # to get raw data

        realPlotIdx = _plotIdx * 2

        try:
            sweepC = ba3.sweepC
        except (ValueError) as e:
            sweepC = None

        myLineWidth = 0.5

        #
        # plot raw
        axs[realPlotIdx].plot(ba3.sweepX, ba3.sweepY, lw=myLineWidth, zorder=10, c='k')

        # update raw min/max
        yRawMin = _getMin(yRawMin, ba3.sweepY)
        yRawMax = _getMax(yRawMax, ba3.sweepY)

        #
        # plot stim from file
        #axs[realPlotIdx+1].plot(ba3.sweepX, sweepC, c='tab:gray', lw=.5, zorder=0)
        
        #
        # over-lay pure sin() wave, no noise
        _noNoiseAmp = 0
        sinNoNoise = sanpy.atfStim.makeStim(stimType, sweepDurSec=sweepDur_sec,
                        startStimSec=stimStart_sec, durSec=stimDur_sec,
                        yStimOffset=yOffset, amp=sinAmp,
                        freq=sinFreq, fs=fs, noiseAmp=_noNoiseAmp, rectify=rectify,
                        autoPad=autoPad, autoSave=False)
        
        axs[realPlotIdx+1].plot(ba3.sweepX, sinNoNoise, c='tab:red', lw=myLineWidth, zorder=1)

        sinWithNoise = sanpy.atfStim.makeStim(stimType, sweepDurSec=sweepDur_sec,
                        startStimSec=stimStart_sec, durSec=stimDur_sec,
                        yStimOffset=yOffset, amp=sinAmp,
                        freq=sinFreq, fs=fs, noiseAmp=noiseAmp, rectify=rectify,
                        autoPad=autoPad, autoSave=False)
        
        axs[realPlotIdx+1].plot(ba3.sweepX, sinWithNoise, c='tab:gray', lw=.5, zorder=0)
        
        #axsstimOnly[_plotIdx] = .plot(ba3.sweepX, sinWithNoise, c='tab:gray', lw=.5, zorder=0)

        # update stim min/max
        yStimMin = _getMin(yStimMin, sinWithNoise)
        yStimMax = _getMax(yStimMax, sinWithNoise)

        # increment
        sinAmp += sinStep
        noiseAmp += noiseStep

    #
    # make y-axis the same

    # expand y-axis by a percentage %
    percentExpand = 0.05

    yRawExpand = (yRawMax - yRawMin) * percentExpand
    yRawMin -= yRawExpand
    yRawMax += yRawExpand

    yStimExpand = (yStimMax - yStimMin) * percentExpand
    yStimMin -= yStimExpand
    yStimMax += yStimExpand

    for _plotIdx, _sweepNum in enumerate(sweepList):
        realPlotIdx = _plotIdx * 2
        axs[realPlotIdx].set_ylim(yRawMin, yRawMax)
        axs[realPlotIdx+1].set_ylim(yStimMin, yStimMax)

    #
    # set the x-axis, if x-axis is linked, really only need one of these
    for _plotIdx, _sweepNum in enumerate(sweepList):
        realPlotIdx = _plotIdx * 2
        axs[realPlotIdx].set_xlim(stimStart_sec, stimStop_sec)
        axs[realPlotIdx+1].set_xlim(stimStart_sec, stimStop_sec)

    #
    # remove all lines/labels    
    for _plotIdx, _sweepNum in enumerate(sweepList):
        realPlotIdx = _plotIdx * 2

        # remove all axis labels
        lastPlot = _plotIdx == len(sweepList)-1
        remove_x = True
        if lastPlot:
            remove_x = False
        _removeAxisLines(axs[realPlotIdx], remove_x=True)
        _removeAxisLines(axs[realPlotIdx+1], remove_x=remove_x)

        # FOR MANUSCRIPT/GRANT
        if lastPlot:
            # specify bins, number of ticks is bins-1
            axs[realPlotIdx+1].xaxis.set_major_locator(MaxNLocator(5))

            # start at 0 sec
            #xTickLoc = [stimStart_sec + x for x in []]
            xTickLoc = [5, 10, 15, 20, 25]
            axs[realPlotIdx+1].set_xticks(xTickLoc)
            axs[realPlotIdx+1].set_xticklabels(['0','5','10','15', '20'])

    return fig  # , figStimOnly, figRawOnly

def plotRaw3(ba3, showDetection=True, showDac=True, axs=None,
                    plotTheseSweeps : list = None,
                    showAxisLabels = True,
                    saveFolder=None):
    """
    Plot Raw data.

    Args:
        ba3 (bAnalysis3)
        showDetection (bool): Overlay detection parameters
        showDac (bool): Overlay Stimulus File DAC stimulus
        axs (matpltlib): If given then plot in this axes
        plotTheseSweeps: limit plot to a list of sweeps
    """

    if plotTheseSweeps is not None:
        numPlots = len(plotTheseSweeps)
        sweepList = plotTheseSweeps
    else:
        numPlots = ba3.numSweeps
        #numSweeps = ba3.numSweeps
        sweepList = ba3.sweepList

    if axs is None:
        fig, axs = plt.subplots(numPlots, 1, sharex=True, sharey=True, figsize=(8, 6))
        if numPlots == 1:
            axs = [axs]

        fig.suptitle(ba3.getFileName())

    # If we are plotting Dac
    rightAxs = [None] * numPlots

    # keep track of x/y min of each plot to make them all the same
    yRawMin = 1e9
    yRawMax = -1e9

    yDacMin = 1e9
    yDacMax = -1e9

    #for idx in ba3.sweepList:
    for _plotIdx, _sweepNum in enumerate(sweepList):
        ba3.setSweep(_sweepNum)  # to get raw data

        lastPlot = _plotIdx == (numPlots - 1)

        try:
            sweepC = ba3.sweepC
        except (ValueError) as e:
            sweepC = None

        if showDac and sweepC is not None:
            rightAxs[_plotIdx] = axs[_plotIdx].twinx()
            rightAxs[_plotIdx].spines['right'].set_visible(False)
            if lastPlot and showAxisLabels:
                rightAxs[_plotIdx].set_ylabel('DAC (nA)')
            rightAxs[_plotIdx].plot(ba3.sweepX, sweepC, c='tab:gray', lw=.5, zorder=0)

            yMin = np.min(sweepC)
            if yMin < yDacMin:
                yDacMin = yMin
            yMax = np.max(sweepC)
            if yMax > yDacMax:
                yDacMax = yMax

        if lastPlot and showAxisLabels:
            axs[_plotIdx].set_ylabel('Vm (mV)')

        axs[_plotIdx].plot(ba3.sweepX, ba3.sweepY, lw=0.5, zorder=10)

        yMin = np.min(ba3.sweepY)
        if yMin < yRawMin:
            yRawMin = yMin
        yMax = np.max(ba3.sweepY)
        if yMax > yRawMax:
            yRawMax = yMax

        if showDetection and ba3.isAnalyzed is not None and ba3.numSpikes>0:
            #df = reduce(ba)
            #df = ba3.analysisDf
            df = ba3.asDataFrame()

            dfPlot = df[ df['sweep'] == _sweepNum]

            peakSec = dfPlot['peakSec']
            peakVal = dfPlot['peakVal']
            axs[_plotIdx].plot(peakSec, peakVal, 'ob', markersize=3, zorder=999)

            footSec = dfPlot['thresholdSec']
            footVal = dfPlot['thresholdVal']
            axs[_plotIdx].plot(footSec, footVal, 'og', markersize=3, zorder=999)

        # label x-axis of subplots
        if lastPlot and showAxisLabels:
            axs[_plotIdx].set_xlabel('Time (s)')
        else:
            #axs[idx].spines['bottom'].set_visible(False)
            axs[_plotIdx].tick_params(axis="x", labelbottom=False) # no labels
            axs[_plotIdx].set_xlabel('')

        # get the zorder correct
        if showDac and sweepC is not None:
            axs[_plotIdx].set_zorder(rightAxs[_plotIdx].get_zorder()+1)
            axs[_plotIdx].set_frame_on(False)

    # set common y min/max
    # expand left axis by a percentage %
    percentExpand = 0.05
    thisExpand = (yRawMax - yRawMin) * percentExpand
    yRawMin -= thisExpand
    yRawMax += thisExpand
    for idx in ba3.sweepList:
        axs[_plotIdx].set_ylim(yRawMin, yRawMax)
        if showDac and sweepC is not None:
            rightAxs[_plotIdx].set_ylim(yDacMin, yDacMax)

    #
    plt.tight_layout()

    if saveFolder is not None:
        saveName = os.path.splitext(ba3.getFileName())[0] + '_raw.png'
        savePath = os.path.join(saveFolder, saveName)
        logger.info(f'saving: {savePath}')
        fig.savefig(savePath, dpi=300)

def run0():
    # one trial of spont
    #path = '/media/cudmore/data/stoch-res/2021_12_06_0002.abf'
    # sin stim
    path = '/media/cudmore/data/stoch-res/2021_12_06_0005.abf'

    # second day of recording
    #path = '/media/cudmore/data/stoch-res/20211209/2021_12_09_0010.abf'  # 194 seconds of baseline
    #path = '/media/cudmore/data/stoch-res/20211209/2021_12_09_0011.abf'  # 1pA/1Hz/2pA step
    path = '/media/cudmore/data/stoch-res/20211209/2021_12_09_0012.abf'  # 1pA/5Hz/2pA step

    ba = load(path)

    # old_plotStimFileParams(ba)

    #print('stimDict:', ba._stimDict)  # can be none

    thresholdValue = -10
    detect(ba, thresholdValue=thresholdValue)

    dfStat = isiStats(ba)
    print('dfStat')
    print(dfStat)

    #sys.exit(1)

    # if we have a stimulus file
    if ba.stimDict is not None:
        stimStartSeconds = ba.stimDict['stimStart_sec']
        frequency = ba.stimDict['stimFreq']  # TODO: will not work if we are stepping frequency
        durSeconds = ba.stimDict['sweepDur_sec']

        #df = reduce(ba)

        #plotPhaseHist(df, stimStartSeconds, frequency)
        plotPhaseHist(ba)

    #plotRaw(ba)

    #plotStats(ba)  # not working

    #plotHist(df)
    #plotShotPlot(df)

    #
    plt.show()

def plotCV(csvPath, statCol):
    """
    statCol (str) name of the column to plot
    """
    #csvPath = '/media/cudmore/data/stoch-res/11feb/analysis/isi_analysis.csv'
    df = pd.read_csv(csvPath)

    fileNames = df['file'].unique()

    numFiles = len(fileNames)

    numCol = 2
    numRow = round(numFiles/numCol)

    fig, axs = plt.subplots(numRow, numCol, sharex=True, sharey=True, figsize=(8, 10))
    axs = np.ravel(axs)

    #statCol = 'cvISI_inv'  # cvISI
    #statCol = 'cvISI'  # cvISI
    
    for idx, file in enumerate(fileNames):
        plotDf = df[ df['file']==file ]

        xPlot = plotDf['sweep']
        yPlot = plotDf[statCol]

        axs[idx].plot(xPlot, yPlot, 'o-k')

        axs[idx].title.set_text(file)

        #axs[idx].set_ylabel(statCol)
        #axs[idx].set_xlabel('Sweep')

    idx = 0
    for row in range(numRow):
        for col in range(numCol):
            if col==0:
                axs[idx].set_ylabel(statCol)
            if row==numRow-1:
                axs[idx].set_xlabel('Sweep')
            #
            idx += 1

    #plt.show()
    return fig  # to save

def test_bAnalysis3():
    """
    TODO:
        1) Load bAnalysis from saved hf5 analysis folder (with saved analysis)
        2) Construct a bAnalysis3() from path
        3) swap in loaded (detection, analysis) into bAnalysis3
    """
    import sanpy
    import colinAnalysis
    import stochAnalysis
    import matplotlib.pyplot as plt

    #folderPath = '/media/cudmore/data/stoch-res/11feb'
    folderPath = '/Users/cudmore/data/stoch-res/11feb'
    
    # this will load from saved hdf file, if not present, will not work
    
    ad = sanpy.analysisDir(path=folderPath)
    baList = []
    for rowIdx,oneBa in enumerate(ad):
        #if rowIdx > 9:
        #    break
        oneBa = ad.getAnalysis(rowIdx, allowAutoLoad=True)  # load from hdf file
        if not oneBa.isAnalyzed():
            logger.warning(f'oneBa does not have any analysis, did you save a hdf5 file?')
            print('  ', oneBa)
            #continue
        
        # reject
        #if oneBa.getFileName() == '2022_02_11_0019.abf':
        #    continue

        baList.append(oneBa)

    #sys.exit(1)
    
    ba3List = []
    for ba in baList:
        baPath = ba.path
        ba3 = colinAnalysis.bAnalysis3(baPath, loadData=False, stimulusFileFolder=None)

        # swap in analysis loaded from hd5 !!!
        ba3.detectionClass = ba.detectionClass
        ba3.spikeDict = ba.spikeDict

        ba3List.append(ba3)

    print(f'we have {len(ba3List)} ba3')

    #path = '/media/cudmore/data/stoch-res/11feb/2022_02_11_0008.abf'
    #ba3 = colinAnalysis.bAnalysis3(path, loadData=True, stimulusFileFolder=None)

    dfMaster = None
    for idx, ba3 in enumerate(ba3List):
        print(f'file idx {idx}')
        print('   ba3:', ba3)

        numSweeps = ba3.numSweeps

        if numSweeps > 1:
            # works
            saveFolder = os.path.join(folderPath, 'analysis')
            if not os.path.isdir(saveFolder):
                os.mkdir(saveFolder)
            stochAnalysis.plotRaw3(ba3, showDetection=True, showDac=True, axs=None, saveFolder=saveFolder)
            plt.close()

            stochAnalysis.plotHist(ba3, saveFolder=saveFolder)
            plt.close()

            stochAnalysis.plotPhaseHist(ba3, saveFolder=saveFolder)
            plt.close()

        df_isi = ba3.isiStats() # can return none

        #print(df_isi)
        #print('')

        if dfMaster is None and df_isi is not None:
            dfMaster = df_isi
        elif df_isi is not None:
            dfMaster = pd.concat([dfMaster,df_isi], ignore_index=True)

    #
    #print(dfMaster)

    saveFolder = os.path.join(folderPath, 'analysis')
    if not os.path.isdir(saveFolder):
        os.mkdir(saveFolder)
    saveFile_csv = os.path.join(saveFolder, 'isi_analysis.csv')
    print('=== saving saveFile_csv:', saveFile_csv)
    dfMaster.to_csv(saveFile_csv)

    fig = plotCV(saveFile_csv, 'cvISI')
    savePlotFile = os.path.join(saveFolder, 'cvISI.png')
    print('=== saving fig:', savePlotFile)
    fig.savefig(savePlotFile, dpi=300)

    fig = plotCV(saveFile_csv, 'nSpikes')
    savePlotFile = os.path.join(saveFolder, 'nSpikes.png')
    print('=== saving fig:', savePlotFile)
    fig.savefig(savePlotFile, dpi=300)

    fig = plotCV(saveFile_csv, 'cvISI_inv')
    savePlotFile = os.path.join(saveFolder, 'cvISI_inv.png')
    print('=== saving fig:', savePlotFile)
    fig.savefig(savePlotFile, dpi=300)

    # 20210422
    # add plot of 'probability in phase percent
    # for each of ppp_5, ppp_10, ppp_15, ppp_20
    
    pppList = [5, 10, 15, 20]
    for ppp in pppList:
        pppColumn = 'ppp_' + str(ppp)
        fig = plotCV(saveFile_csv, pppColumn)
        savePlotFile = os.path.join(saveFolder, pppColumn + '.png')
        print('=== saving fig:', savePlotFile)
        fig.savefig(savePlotFile, dpi=300)

    plt.show()

if __name__ == '__main__':
    # run0()

    # works
    test_bAnalysis3()

    # load saved csv and plot
    #plotCV()
