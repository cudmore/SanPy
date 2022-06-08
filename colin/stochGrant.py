
import os
from pprint import pprint

import sanpy
import colinAnalysis
import stochAnalysis

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

def loadOne(ad : sanpy.analysisDir, rowIdx : int):
    ba = ad.getAnalysis(rowIdx, allowAutoLoad=True)  # load from hdf file

    baPath = ba.path
    ba3 = colinAnalysis.bAnalysis3(baPath, loadData=False, stimulusFileFolder=None)

    # swap in analysis loaded from hd5 !!!
    ba3.detectionClass = ba.detectionClass
    ba3.spikeDict = ba.spikeDict

    numSweeps = ba3.numSweeps
    if not (numSweeps > 1):
        print('expecing more than one sweep')
        return

    return ba3

def plotSummaryStat(df, statName, sweepList):
    dfPlot = df[ df['sweep'].isin(sweepList)]
    
    x = dfPlot['sweep']
    y = dfPlot[statName]

    print(x)
    print(y)

    fig, axs = plt.subplots(1, 1, figsize=(2, 2))

    axs.plot(x, y, '-o', c='k')

    axs.xaxis.set_major_locator(MaxNLocator(5))
    
    axs.set_ylim(0, 0.85)
    axs.yaxis.set_major_locator(MaxNLocator(5))

    return fig

if __name__ == '__main__':
    import matplotlib.pylab as pylab
    myFontSize = 12
    params = {'legend.fontsize': myFontSize,
        'figure.figsize': (15, 5),
        'axes.labelsize': myFontSize,
        'axes.titlesize':myFontSize,
        'xtick.labelsize':myFontSize,
        'ytick.labelsize':myFontSize}
    pylab.rcParams.update(params)

    # load an entire analysis directory
    folderPath = '/Users/cudmore/data/stoch-res/11feb'
    ad = sanpy.analysisDir(path=folderPath)

    #
    # load raw data and analysis
    # 2022_02_11_0017 is one where we lose the recording
    rowIdx = 17 # 2022_02_11_0017.abf

    # 2022_02_11_0006
    rowIdx = 6

    # /2022_02_11_0008
    rowIDx = 8

    ba3 = loadOne(ad, rowIdx)

    print(ba3)
    print(ba3._stimFileAsDataFrame())

    #
    # plot
    saveFolder = None
    
    plotTheseSweeps = [1,2,3,4,5]

    '''
    stochAnalysis.plotRaw3(ba3, showDetection=False, showDac=True,
                            axs=None,
                            plotTheseSweeps=plotTheseSweeps,
                            showAxisLabels = False,
                            saveFolder=saveFolder)
    '''

    #rawFig, figStimOnly, figRawOnly = stochAnalysis.plotRaw4(ba3,
    rawFig = stochAnalysis.plotRaw4(ba3,
                axs=None,
                plotTheseSweeps=plotTheseSweeps)

    # works
    dfPhase, phaseFig = stochAnalysis.plotPhaseHist(ba3,
                saveFolder=saveFolder,
                plotTheseSweeps=plotTheseSweeps)

    # grap isi stats and plot 'synchrony' as a function of noise
    df_isi = ba3.isiStats() # can return none
    pprint(df_isi)

    summaryStat = 'ppp_15'
    summaryFig = plotSummaryStat(df_isi, summaryStat, plotTheseSweeps)

    doSave = True
    if doSave:
        _fileName = ba3.getFileName()
        savePath = '/USers/cudmore/Desktop/stoch-grant-panels'
        # raw
        saveRawName = 'raw_' + _fileName + '.pdf'
        saveRawPath = os.path.join(savePath, saveRawName)
        print('saving:', saveRawPath)
        rawFig.savefig(saveRawPath)
        # phase
        savePhaseName = 'phase_' + _fileName + '.pdf'
        savePhasePath = os.path.join(savePath, savePhaseName)
        print('saving:', savePhasePath)
        phaseFig.savefig(savePhasePath)
        # summary
        saveSummaryName = summaryStat + _fileName + '.pdf'
        saveSummaryPath = os.path.join(savePath, saveSummaryName)
        print('saving:', saveSummaryPath)
        summaryFig.savefig(saveSummaryPath)

    plt.show()