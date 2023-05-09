"""
Plot example experiment of cardiac myocyte before and after bath application of ISO.

This corresponds to Figure 6
"""

import scipy
import numpy as np
import matplotlib.pyplot as plt  # just to show plots during script
import seaborn as sns

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def run():
    # load from '/media/cudmore/data/laura-iso'

    # list of files to analyze
    aDict = {
        '19503001': {
            'path': 'laura-iso-manuscript/19503001.abf',
            'detectionType': 'dvdt',
            'dvdtThreshold': 20,  # chosen by visual inspection
            'controlSec': [4, 106],
            'isoSec': [200, 300],
        },
        # '19503006': {
        #     'path': 'data/laura-iso-manuscript/19503006.abf',
        #     'detectionType': 'dvdt',
        #     'dvdtThreshold': 18,  # chosen by visual inspection
        #     'controlSec': [10, 90],
        #     'isoSec': [180, 270],
        # },
        # '20191122_0001': {
        #     # IMPORTANT: The recording chagegd too much in this recording !!!!
        #     # these changes are not due to ISO and in opposite direction from expected (which is good)!!!
        #     'path': 'data/laura-iso-manuscript/20191122_0001.abf',
        #     'detectionType': 'mv',
        #     #'dvdtThreshold': 50,
        #     'mvThreshold': -40,
        #     'controlSec': [10, 90],
        #     'isoSec': [380, 470],
        # },
    }

    baList = []
    for file, params in aDict.items():

        filePath = params['path']
        detectionType = params['detectionType']
        dvdtThreshold = params['dvdtThreshold']
        controlSec = params['controlSec']
        isoSec = params['isoSec']

        # load
        ba = sanpy.bAnalysis(filePath)

        # analyze spikes
        # detectionClass = ba.detectionClass
        # detectionClass['verbose'] = False
        # if detectionType == 'dvdt':
        #     detectionClass['detectionType'] = sanpy.bDetection.detectionTypes.dvdt
        # elif detectionType == 'mv':
        #     detectionClass['detectionType'] = sanpy.bDetection.detectionTypes.mv
        
        # get all detection presets
        _detectionParams = sanpy.bDetection()

        # print list of names of detection presets
        # print(_detectionParams.getDetectionPresetList())
        
        # select 'SA Node' presets
        _dDict = _detectionParams.getDetectionDict('SA Node')

        # set detection threshold if necessary
        _dDict['dvdtThreshold'] = dvdtThreshold

        # spike detect
        ba.spikeDetect(_dDict)
        
        baList.append(ba)

        # grab results as a pandas dataframe
        df = ba.asDataFrame()

        # all analysis result columns
        # print(df.columns)

        # todo: merge into big dataframe, add column 'myCellNumber'

        # pull control versus drug stats based on time
        # could do this as well
        #thresholdSec = ba.getStat('thresholdSec', asArray=True)

        # boolean mask based on a time window
        thresholdSec = df['thresholdSec']
        controlMask = (thresholdSec>controlSec[0]) & (thresholdSec<controlSec[1])
        isoMask = (thresholdSec>isoSec[0]) & (thresholdSec<isoSec[1])

        # add a new column for this example
        df['myCondition'] = 'None'
        df['myCondition'] = np.where(controlMask, 'Control', df['myCondition'])
        df['myCondition'] = np.where(isoMask, 'Iso', df['myCondition'])

        # drop any remaining datapoint (rows) with myCondition == 'None'
        dfPlot = df.drop(df[df['myCondition'] == 'None'].index)

    #
    # plot one ba
    ba = baList[0]

    # raw data has muted colors
    rawPalette = {
        "Control": "#777777",
        "Iso": "#CC7777",
        #"None": "#dddddd",
        }

    meanPalette = {
        "Control": "k",
        "Iso": "r",
        #"None": "#dddddd",
        }

    statList = [
         'spikeFreq_hz',
         'widths_50',
         'earlyDiastolicDurationRate',  # NOT SIGNIFICANT !!!
    ]

    sns.set_context("talk")

    # either
    #fig0, axs0 = plt.subplots(4,1, sharex=True, figsize=(12, 4))
    # or
    fig0, axs0 = plt.subplots(1,1, sharex=True, figsize=(12, 4))
    axs0 = [axs0]

    doPlotRaw = True
    if doPlotRaw:
        # create an analysis plot object from one ba
        ap = sanpy.bAnalysisPlot(ba)

        # axs = ap.plotRaw(ax=axs0[0])
        axs = ap.plotRaw(ax=axs0[0])
        #axs = [axs]

        # overlay analysis results
        xStatName = 'peakSec'
        yStatName = 'peakVal'
        g0 = sns.scatterplot(x=xStatName, y=yStatName,
                        hue='myCondition',
                        palette=rawPalette,
                        data=dfPlot,
                        ax=axs)

        g0.legend_.remove()
        #plt.show()

    # sns.scatterplot(x='thresholdSec', y='spikeFreq_hz',
    #                             hue='myCondition', palette=rawPalette,
    #                             data=dfPlot,
    #                             legend=False,
    #                             ax=axs0[1])
    # sns.scatterplot(x='thresholdSec', y='widths_50',
    #                             hue='myCondition', palette=rawPalette,
    #                             data=dfPlot,
    #                             legend=False,
    #                             ax=axs0[2])
    # sns.scatterplot(x='thresholdSec', y='earlyDiastolicDurationRate',
    #                             hue='myCondition', palette=rawPalette,
    #                             data=dfPlot,
    #                             legend=False,
    #                             ax=axs0[3])

    # adjust visual display
    fig0.set_tight_layout(True)  # remove overlap between y-axis labels
    sns.despine(fig0)  # remove top and right axis lines
    axs0[0].set_xlim(5, 300)

    # as a category
    #sns.catplot(x="myCondition", y=statName, kind="swarm", data=dfPlot)

    #
    # plot 3x stats
    # TODO: plot mean as a bar, look at whistler plots
    
    # these are all possible analysis results
    #print(dfPlot.columns)

    sns.set_context("talk")

    fig2, axs2 = plt.subplots(1,3, figsize=(12, 4))

    for _axsIdx, statName in enumerate(statList):
        oneAxs = axs2[_axsIdx]
        g = sns.swarmplot(x='myCondition', y=statName,
                            hue='myCondition', palette=rawPalette,
                            data=dfPlot, zorder=1, ax=oneAxs)
        sns.pointplot(x='myCondition', y=statName,
                            palette=meanPalette, data=dfPlot,
                            errorbar=('ci', 68), ax=oneAxs)

        # remove the legend
        #g._legend.remove()
        g.legend_.remove()

    # adjust visual display
    fig2.set_tight_layout(True)  # remove overlap between y-axis labels
    sns.despine(fig2)  # remove top and right axis lines

    #
    # run stats
    for statName in statList:
        x1 = dfPlot[dfPlot['myCondition']=='Control'][statName]
        x2 = dfPlot[dfPlot['myCondition']=='Iso'][statName]
        _stat = scipy.stats.mannwhitneyu(x1, x2)
        
        print(f'{statName}: Control vs Iso {_stat}')
        _mean = np.mean(x1)
        _std = np.std(x1)
        _n = len(x1)
        print(f'  Control mean:{_mean}  std:{_std} n:{_n}')

        _mean = np.mean(x2)
        _std = np.std(x2)
        _n = len(x2)
        print(f'   Iso    mean:{_mean}  std:{_std} n:{_n}')

    # finally, show the plots
    plt.show()

if __name__ == '__main__':
    run()
