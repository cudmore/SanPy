"""Show example usage of the API
    - Load a csv file
    - Detect spike
    - plot raw + threshold
    - plot scatter of spike freq (Hz) and half width (ms)
"""
import numpy as np
import scipy.stats

import seaborn as sns
import matplotlib.pyplot as plt  # just to show plots during script

import sanpy

def run():

    # load raw data
    path = 'model-manuscript/stoch-hh-gk-20230312-152309-36-30.csv'
    ba = sanpy.bAnalysis(path)

    # get detection presets and choose 'Fast Neuron'
    _detectionParams = sanpy.bDetection()
    _dDict = _detectionParams.getDetectionDict('Fast Neuron')

    # spike detect
    ba.spikeDetect(_dDict)

    # set spike conditions
    ba.setSpikeStat_time(0, 0.99, 'condition', 'control')
    ba.setSpikeStat_time(1.01, 2, 'condition', 'drug')

    sns.set_context("talk")
    fig, axs = plt.subplots(3,1, sharex=True, figsize=(10, 8))

    bap = sanpy.bAnalysisPlot(ba)

    # plot raw data with threshold    
    bap.plotSpikes(plotThreshold=True, ax=axs[0])

    bap.plotStat('thresholdSec', 'spikeFreq_hz', hue='condition', ax=axs[1])

    #bap.plotStat('thresholdSec', 'widths_50', hue='condition')

    df = ba.spikeDict.asDataFrame()  # regenerates, can be expensive
    sns.scatterplot(x='thresholdSec', y='widths_50',
                    hue='condition', data=df,
                    legend=False, ax=axs[2])

    sns.despine(fig)

    #
    # run stats
    statList = [
         'spikeFreq_hz',
         'widths_50',
         'thresholdVal',  # NOT SIGNIFICANT !!!
    ]

    dfPlot = df
    
    for statName in statList:
        x1 = dfPlot[dfPlot['condition']=='control'][statName]
        x1 = x1[~np.isnan(x1)]  # first spike has nan freq
        
        x2 = dfPlot[dfPlot['condition']=='drug'][statName]

        _stat = scipy.stats.mannwhitneyu(x1, x2)
        print(f'{statName}: Control vs Iso {_stat}')
        
        _mean = np.mean(x1)
        _std = np.std(x1)
        _n = len(x1)
        print(f'  Control mean:{_mean}  std:{_std} n:{_n}')

        _mean = np.mean(x2)
        _std = np.std(x2)
        _n = len(x2)
        print(f'   Drug    mean:{_mean}  std:{_std} n:{_n}')

        # print('x1 nan', np.count_nonzero(np.isnan(x1)))
        # print('x2 nan', np.count_nonzero(np.isnan(x2)))

    plt.show()

if __name__ == '__main__':
    run()