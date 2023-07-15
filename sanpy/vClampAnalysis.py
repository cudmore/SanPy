import numpy as np
import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def vClampAnalysis(ba : sanpy.bAnalysis):
    self = ba
    
    self.spikeDict = sanpy.bAnalysisResults.analysisResultList()

    for sweep in self.fileLoader.sweepList:
        self.fileLoader.setSweep(sweep)
        self._getFilteredRecording() # in case dDict has new filter values

        # epochTable :sanpy.fileloaders.epochTable
        epochTable = self.fileLoader.getEpochTable(sweep)
        for epoch in epochTable.getEpochList():
            vClampAnalysis_epoch(ba, sweep, epoch)

def vClampAnalysis_epoch(ba, sweep, epoch : dict):
    """
    # epoch is a dict like
    #       sweepNumber  index  type  startPoint  stopPoint  startSec  stopSec  durSec  level
    # 0           18      0  Step         0.0     5000.0       0.0     0.10    0.10  -0.12
    """

    self = ba

    # new detection params
    # amount to skip to not analyze series resistance
    msOffsetSeries = 0.2
    pntOffsetSeries = self.fileLoader.ms2Pnt_(msOffsetSeries)
    
    # setup
    sweepX = self.fileLoader.sweepX  # sweepNumber is not optional
    sweepY = self.fileLoader.sweepY  # sweepNumber is not optional
    filteredVm = self.fileLoader.sweepY_filtered  # sweepNumber is not optional
    filteredDeriv = self.fileLoader.filteredDeriv
    
    # a list of dict of sanpy.bAnalysisResults.analysisResult (one dict per spike)
    spikeDict = sanpy.bAnalysisResults.analysisResultList()

    spikeIdx = 0  # for v-clamp, each epoch is like a spike (min, max, width, etc)
    spikeDict.appendDefault()  # append just one spike
    
    spikeDict[spikeIdx]['sweep'] = epoch['sweepNumber']
    spikeDict[spikeIdx]['epoch'] = epoch['index']  # index should be called epoch
    spikeDict[spikeIdx]['epochLevel'] = epoch['level']
        
    startPoint = epoch['startPoint']
    stopPoint = epoch['stopPoint']

    startPoint += pntOffsetSeries
    
    iRecord = sweepX[startPoint:stopPoint]

    # get min current
    minPnt = np.argmin(iRecord) + startPoint

    # get max current
    maxPnt = np.argmax(iRecord) + startPoint

    # logger.info(f'sweep:{sweep} epoch:{epoch["index"]}')
    # print(f'  startPoint:{startPoint} minPnt:{minPnt} maxPnt:{maxPnt}')

    spikeDict[spikeIdx]['thresholdPnt'] = minPnt
    spikeDict[spikeIdx]['thresholdSec'] = sweepX[minPnt]
    spikeDict[spikeIdx]['thresholdVal'] = sweepY[minPnt]

    spikeDict[spikeIdx]['peakPnt'] = maxPnt
    spikeDict[spikeIdx]['peakSec'] = sweepX[maxPnt]
    spikeDict[spikeIdx]['peakVal'] = sweepY[maxPnt]

    spikeDict[spikeIdx]['peakHeight'] = sweepY[maxPnt] = sweepY[minPnt]

    # append analysis for this sweep/epoch
    self.spikeDict.appendAnalysis(spikeDict)

def _plot_vclamp(ba):
    import matplotlib.pyplot as plt

    epochNumber = 1
    
    xStat = 'thresholdSec'  # current min
    yStat = 'thresholdVal'
    
    xPlot = ba.getStat(xStat, epochNumber=epochNumber)
    yPlot = ba.getStat(yStat, epochNumber=epochNumber)

    xStatMax = 'peakSec'  # current max
    yStatMax = 'peakVal'
    xPlotMax = ba.getStat(xStatMax, epochNumber=epochNumber)
    yPlotMax = ba.getStat(yStatMax, epochNumber=epochNumber)

    # plt.plot(xPlot, yPlot, 'ro')
    # plt.plot(xPlotMax, yPlotMax, 'bo')

    peakHeight = ba.getStat('peakHeight', epochNumber=epochNumber)
    xPlotMax = ba.getStat('peakSec', epochNumber=epochNumber)
    plt.plot(xPlotMax, peakHeight, 'bo')

    plt.show()

if __name__ == '__main__':
    path = '/Users/cudmore/Dropbox/data/heka_files/JonsLine_2023_05_09/GeirHarelandJr_2023-05-09_001.dat'
    ba = sanpy.bAnalysis(path)

    print(ba)

    vClampAnalysis(ba)

    print(ba)

    _plot_vclamp(ba)