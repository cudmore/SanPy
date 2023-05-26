import numpy as np
import pandas as pd

from sanpy.fileloaders.fileLoader_base import fileLoader_base, recordingModes
from sanpy.fileloaders.epochTable import epochTable
from sanpy.fileloaders import hekaUtils

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

# this is modified version, see
from load_heka_python.load_heka import LoadHeka

# def printDict(d):
#     for k,v in d.items():
#         print(f'  === {k}: {v}')

class fileLoader_heka(fileLoader_base):
    """Load PatchMaster Heka files using the load_hekaa_python package.
    """
    loadFileType = "dat"

    def loadFile(self):
        """Load file and call setLoadedData().

        Use self.filepath for the file
        """

        group_idx = 0
        series_idx = 2

        hekaDict = hekaUtils.hekaLoad(self.filepath, group_idx=group_idx, series_idx=series_idx)

        # TODO: add this to hekaLoad
        heka_yLabel = hekaDict['yLabel']
        if heka_yLabel in ['A', 'pA', 'nA']:
            recordingMode = recordingModes.vclamp
        elif heka_yLabel in ['V', 'mV', 'uV']:
            recordingMode = recordingModes.iclamp
        else:
            recordingMode = recordingModes.unknown

        self.setLoadedData(
            sweepX=hekaDict['sweepX'],
            sweepY=hekaDict['sweepY'],
            sweepC = hekaDict['sweepC'],
            recordingMode=recordingMode,
            xLabel=hekaDict['xLabel'],
            yLabel=hekaDict['yLabel'],
        )

        # series corresponds to sweeps
        _numSeries = hekaDict['numSweeps']
        _epochList = hekaDict['epochList']
    
        self._epochTableList = [None] * _numSeries
        for _seriesIndex in range(_numSeries):
            _epochTable = epochTable()
            _starttSec = 0
            for _epoch in _epochList:
                # addEpoch(self, sweepNumber, startSec, stopSec, dataPointsPerMs : int, level, type : str = 'Step'):
                startSec = _starttSec
                stopSec = _starttSec + _epoch['seDuration']
                dataPointsPerMs = self.dataPointsPerMs
                level = _epoch['seVoltage'] + (_epoch['seDeltaVIncrement'] * _seriesIndex)
                type='Step'
                _epochTable.addEpoch(_seriesIndex, startSec, stopSec, dataPointsPerMs, level, type=type)

                _starttSec += _epoch['seDuration']
            self._epochTableList[_seriesIndex] = _epochTable

        return
    
if __name__ == '__main__':
    path = '/Users/cudmore/Dropbox/data/heka_files/JonsLine_2023_05_09/GeirHarelandJr_2023-05-09_001.dat'
    flh = fileLoader_heka(path)

    print(flh)
    # print('dataPointsPerMs:', flh.dataPointsPerMs)  # 50

    for _sweep in range(flh.numSweeps):
        df = flh.getEpochTable(_sweep).getEpochList(asDataFrame=True)
        print(df)