"""Show example usage of the API
    - Load a csv file
    - Detect spike
    - plot raw + threshold
    - plot scatter of spike freq (Hz) and half width (ms)
"""

import seaborn as sns
import matplotlib.pyplot as plt  # just to show plots during script

import sanpy

def run():

    # load raw data
    path = 'data/model-manuscript/stoch-hh-gk-20230312-152309-36-30.csv'
    ba = sanpy.bAnalysis(path)

    # get detection presets and choose 'Fast Neuron'
    _detectionParams = sanpy.bDetection()
    _dDict = _detectionParams.getDetectionDict('Fast Neuron')

    # spike detect
    ba.spikeDetect(_dDict)

    # set spike conditions
    ba.setSpikeStat_time(0, 1, 'condition', 'control')
    ba.setSpikeStat_time(1, 2, 'condition', 'drug')

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
    plt.show()

if __name__ == '__main__':
    run()