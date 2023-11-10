from typing import List  # Union, Dict, List, Tuple, Optional

import numpy as np

import logging
logger = logging.getLogger(__name__)

from load_heka_python.load_heka import LoadHeka

def hekaLoad(path : str, group_idx : int = 0, series_idx : int = 2) -> dict:
    """Load a heka file and return a dictionary with the loaded data.
        numSweeps : int
            Number of sweeps in the recording
        sweepX : np.ndarray([n samples, m sweeps])
            2D array of sample times (s)
        sweepY : np.ndarray([n samples, m sweeps])
            2D array of recording
        sweepC : np.ndarray([n samples, m sweeps])
            2D array of recorded ILeak
        samplingInterval : float
            Sampling interval in seconds
        dataPointsPerMs : int
            Number of data points per ms, used by SanPy
        epochList : List[dict]
            List of dict containing information about each epoch within a sweep.
            Epochs correspond to voltage holding currents and steps.
            This includes an increment value when performing increasing voltage steps
                across sweeps.
        xLabel : str
            X axis label for recording
        yLabel': str
            Y axis label for recording
        version': str
            PatchMaster software version
    """

    with LoadHeka(path) as heka_file:
        numSeries = len(heka_file.pul["ch"][group_idx]["ch"][series_idx]["ch"])

        _version = heka_file.version
        logger.info(f'Loading Heka .dat file version:: "{_version}"')

    # series corresponds to sweeps
    for _seriesIndex in range(numSeries):

        # recording
        seriesHeader_record = heka_file.pul["ch"][group_idx]["ch"][series_idx]["ch"][_seriesIndex]["ch"][0]['hd']
        seriesData_record = heka_file.pul["ch"][group_idx]["ch"][series_idx]["ch"][_seriesIndex]["ch"][0]['data']

        # I am guessing here, we need to work this out but we will do it
        _yRecordUnits = seriesHeader_record['TrYUnit']
        # TrDataScaler = seriesHeader_record['TrDataScaler']
        # seriesData_record /= TrDataScaler
        # seriesData_record /= 1000
        seriesData_record /= 1e-12  # pico amp is 1e-12

        if _seriesIndex == 0:
            sweepY = seriesData_record[:,None]
        else:
            sweepY = np.append(sweepY, seriesData_record[:,None], 1)

        # stimulus
        seriesHeader_stim = heka_file.pul["ch"][group_idx]["ch"][series_idx]["ch"][_seriesIndex]["ch"][1]['hd']
        seriesData_stim = heka_file.pul["ch"][group_idx]["ch"][series_idx]["ch"][_seriesIndex]["ch"][1]['data']

        #_yStimUnits = seriesHeader_stim['TrYUnit']

        # I am guessing here, we need to work this out but we will do it
        #TrDataScaler = seriesHeader_stim['TrDataScaler']
        #seriesData_stim /= TrDataScaler
        #seriesData_stim /= 1000
        seriesData_stim /= 1e-12

        if _seriesIndex == 0:
            sweepC = seriesData_stim[:,None]
        else:
            sweepC = np.hstack((sweepC,seriesData_stim[:,None]))

        # x axis in seconds !
        TrXInterval = seriesHeader_stim['TrXInterval']  # 1e-5 corresponds to 20 kHz
        TrDataPoints = seriesHeader_stim['TrDataPoints']
        x = [x*TrXInterval for x in range(TrDataPoints)]
        _x = np.array(x)
        if _seriesIndex == 0:
            sweepX = _x[:,None]
        else:
            sweepX = np.append(sweepX,_x[:,None], 1)
    
    xLabel = 's'
    if _yRecordUnits in ['A']:
        yLabel = 'pA'
    elif _yRecordUnits in ['V']:
        yLabel = 'mV'

    series_data = heka_file.get_series_data("Im", group_idx=group_idx, series_idx=series_idx, include_stim_protocol=True)
    epochList = hekaGetEpochList(series_data)
        
    # to mimic sanpy backend, dataPointsPerMs is required
    dtSeconds = sweepX[1, 0] - sweepX[0, 0]  # seconds per sample
    dtSeconds = float(dtSeconds)
    dtMilliseconds = dtSeconds * 1000
    dataPointsPerMs = int(1 / dtMilliseconds)

    retDict = {
        'numSweeps': numSeries,
        'sweepX': sweepX,
        'sweepY': sweepY,
        'sweepC': sweepC,
        'samplingInterval': TrXInterval,  # kHz
        'dataPointsPerMs': dataPointsPerMs,
        'epochList': epochList,
        'xLabel': xLabel,
        'yLabel': yLabel,
        #'yStimUnits': _yStimUnits,
        'version': _version,
    }
    return retDict

def hekaGetEpochList(series_data : dict) -> List[dict]:
    """Get a epoch stim table from a dat heka file.
    """

    # added the 'abb_stim_sweep' key to source code
    abb_stim_sweep = series_data['stim']['abb_stim_sweep']

    # print('stim_sweep ch:')
    _epochList = []
    logger.info('generating local _epochList')
    for _idx, _ch in enumerate(abb_stim_sweep['ch']):
        # print('fff _idx', _idx)
        # printDict(_ch['hd'])
        
        # print('aaa _ch["ch"] has num in list', len(_ch['ch']))
        for _idx2, _ch2 in enumerate(_ch['ch']):
            # print('ggg idx2:', _idx2)
            #printDict(_ch2['hd'])
            #printDict(_ch2['ch'])
            seVoltage = _ch2['hd']['seVoltage']  # start voltage (sweep 0), unit of V
            seDeltaVIncrement = _ch2['hd']['seDeltaVIncrement']  # increment per sweep, units of V
            seDuration = _ch2['hd']['seDuration']  # pulse duration in seconds
            
            _epochList.append(
                {
                    'seVoltage': seVoltage,
                    'seDeltaVIncrement': seDeltaVIncrement,
                    'seDuration': seDuration,
                }
            )
    return _epochList

if __name__ == '__main__':
    path = '/Users/cudmore/Dropbox/data/heka_files/JonsLine_2023_05_09/GeirHarelandJr_2023-05-09_001.dat'
    hekaDict = hekaLoad(path)
    for k,v in hekaDict.items():
        print(f'  {k}: {v}')

