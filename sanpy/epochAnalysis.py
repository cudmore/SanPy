"""
"""
from pprint import pprint
import pandas as pd

import sanpy


class epochAnalysis:
    def __init__(self, ba: sanpy.bAnalysis):
        retDictList = []

        df = ba.asDataFrame()

        files = df["file"].unique()
        for file in files:
            dfFile = df[df["file"] == file]
            sweeps = dfFile["sweep"].unique()
            for sweep in sweeps:
                dfSweep = dfFile[dfFile["sweep"] == sweep]
                epochs = dfSweep["epoch"].unique()
                for epoch in epochs:
                    dfEpoch = dfSweep[dfSweep["epoch"] == epoch]

                    # pprint(dfEpoch)

                    # count number of spikes in this (file, sweep, epoch)
                    numSpikes = len(dfEpoch)

                    firstSpikeFreq = float("nan")
                    spikeFreq_mean = float("nan")
                    if numSpikes > 1:
                        firstSpikeFreq = dfEpoch["spikeFreq_hz"].iloc[1]

                        # TODO: this can't include the first spike in the epoch
                        # average spike freq from each spikes 'spikeFreq_hz'
                        spikeFreq_mean = (
                            dfEpoch["spikeFreq_hz"].iloc[1 : len(dfEpoch)].mean()
                        )

                    # print('file:', file, 'sweep:', sweep, 'epoch:', epoch, 'numSpikes:', numSpikes)

                    oneDict = self.getDefaultDict()
                    oneDict["file"] = file
                    oneDict["sweep"] = sweep
                    oneDict["epoch"] = epoch
                    oneDict["numSpikes"] = numSpikes
                    oneDict["spikeFreq_mean"] = spikeFreq_mean
                    oneDict["firstSpikeFreq"] = firstSpikeFreq
                    retDictList.append(oneDict)

        #
        dfReturn = pd.DataFrame(retDictList)
        pprint(dfReturn)

    def getDefaultDict(self):
        """A dictionary for one (file, sweep, epoch).

        Will be a row in a dataframe
        """
        retDict = {
            "file": "",
            "sweep": float("nan"),
            "epoch": float("nan"),
            "numSpikes": float("nan"),
        }
        return retDict.copy()


if __name__ == "__main__":
    path = "/Users/cudmore/Sites/SanPy/data/2021_07_20_0010.abf"
    ba = sanpy.bAnalysis(path)

    detectionPreset = sanpy.bDetection.detectionPresets.fastneuron
    detectionClass = sanpy.bDetection(detectionPreset=detectionPreset)

    """
    detectionClass['dvdtThreshold'] = 20
    detectionClass['refractory_ms'] = 3
    detectionClass['peakWindow_ms'] = 2
    detectionClass['halfWidthWindow_ms'] = 4
    detectionClass['preSpikeClipWidth_ms'] = 2
    detectionClass['postSpikeClipWidth_ms'] = 2
    """

    ba.spikeDetect(detectionClass=detectionClass)

    # print(ba)
    # df = ba.asDataFrame()

    ea = epochAnalysis(ba)

    # works
    """
    numSweeps = ba.numSweeps
    for sweep in range(numSweeps):
        et = ba.getEpochTable(sweep)
        dfEpoch = et.getEpochList(asDataFrame=True)
        print(dfEpoch)
    """

    # works, while trying to understand abf sweep epoch table
    # each sweep has its own epoch table
    """
    import pyabf
    abf = pyabf.ABF(path)
    numSweeps = len(abf.sweepList)
    for sweep in range(numSweeps):
        abf.setSweep(sweep)
        print(abf.sweepNumber)
        et = sanpy.fileloaders.epochTable(abf)
        #dfEpoch = ba._epochTable.getEpochList(asDataFrame=True)
        dfEpoch = et.getEpochList(asDataFrame=True)
        print(dfEpoch)
    """
