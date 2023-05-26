
"""
See:
    https://github.com/easy-electrophysiology/load-heka-python
    
    And the older code
    https://github.com/campagnola/heka_reader

I clones and pip install -e

Needed to comment this out in load_heka_python/readers/data_reader.py
in def run_checks()

    # abb 2023
    # assert not data_kind["IsLeak"], "isLeak channels not tested"
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from load_heka_python.load_heka import LoadHeka

def printDict(d):
    for k,v in d.items():
        print(f'  === {k}: {v}')

# this is John Sack file from 2019
# Exception: Version not current supported, please contact support@easyelectrophysiology.com
#full_path_to_file = '/Users/cudmore/Dropbox/data/heka_files/MJM_2019-07-08_001.dat'

path = '/Users/cudmore/Dropbox/data/heka_files/JonsLine_2023_05_09/GeirHarelandJr_2023-05-09_001.dat'

# assert not data_kind["IsLeak"], "isLeak channels not tested"
# AssertionError: isLeak channels not tested
with LoadHeka(path) as heka_file:
    
    # heka version is "v2x91, 23-Feb-2021" 
    _version = heka_file.version
    print('_version:', _version)

    print('=== group names are:')
    heka_file.print_group_names()
    print('')

    print('=== series names of group [0] are')
    group_idx = 0
    heka_file.print_series_names(group_idx)
    print('')

    group_idx = 0
    series_idx = 2

    _record = 0
    _sweep = 2  # sweep 2 has 19 series

    # all None
    # Im works
    # Vm does not
    series_data = heka_file.get_series_data("Im", group_idx=group_idx, series_idx=series_idx, include_stim_protocol=True)

    abb_stim_sweep = series_data['stim']['abb_stim_sweep']
    print('abb_stim_sweep:')
    #print(abb_stim_sweep)

    print('stim_sweep ch:')
    for _idx, _ch in enumerate(abb_stim_sweep['ch']):
        # print('fff _idx', _idx)
        # printDict(_ch['hd'])
        
        print('aaa _ch["ch"] has num in list', len(_ch['ch']))
        for _idx2, _ch2 in enumerate(_ch['ch']):
            print('ggg idx2:', _idx2)
            printDict(_ch2['hd'])
            #printDict(_ch2['ch'])

    # series_data is dict with keys
    # ['data', 'time', 'labels', 'ts', 'data_kinds', 'num_samples', 't_starts', 't_stops', 'stim', 'dtype']
    print('series_data:', type(series_data), series_data.keys())
    printDict(series_data)

    # series_data["stim"]: dict_keys(['ts', 'num_sweeps', 'units', 'holding', 'use_relative', 'data'])
    print('series_data["stim"]:', series_data["stim"].keys())
    printDict(series_data['stim'])

    _stimData = series_data['stim']['data']
    _currentData = series_data['data']
    print('_stimData:', _stimData.shape)  # (19, 7500)
    print('_currentData:', _currentData.shape)  # (19, 7500)

    # plt.plot(_stimData)
    # plt.show()

    # plt.plot(_currentData)
    # plt.show()

    series_idx = 10
    print('qqq')
    numSeries = len(heka_file.pul["ch"][_record]["ch"][_sweep]["ch"])
    print('num series in sweep is:', numSeries)

    _tmp4 = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][series_idx]["ch"]  # [0] first group
    print('_tmp4:', len(_tmp4))
    # _tmp4[0]['data'] is recorded current
    # _tmp4[1]['data'] is voltage command
    printDict(_tmp4[0])

    _seriesIndex = 0

    currentHeader_0 = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][_seriesIndex]["ch"][0]['hd']
    print('currentHeader_0:')
    printDict(currentHeader_0)

    voltageHeader_0 = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][_seriesIndex]["ch"][1]['hd']
    print('voltageHeader_0:')
    printDict(voltageHeader_0)
    
    # TrDataScaler_voltage = voltageHeader_0['TrDataScaler']
    # TrZeroData_voltage = voltageHeader_0['TrZeroData']

    # dfStim = pd.DataFrame()
    # dfRecord = pd.DataFrame()

    print('pulling and plotting numSeries:', numSeries)

    for _seriesIndex in range(numSeries):
        # print('_seriesIndex:', _seriesIndex)
        
        # recording
        seriesHeader_record = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][_seriesIndex]["ch"][0]['hd']
        TrDataScaler = seriesHeader_record['TrDataScaler']
        TrZeroData = seriesHeader_record['TrZeroData']
        seriesData_record = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][_seriesIndex]["ch"][0]['data']
        scaling_factor = np.array(TrDataScaler, dtype=np.float64)
        # seriesData_record = (seriesData_record * scaling_factor) - TrZeroData

        # I am guessing here, we need to work this out but we will do it
        seriesData_record /= TrDataScaler
        seriesData_record /= 1000

        if _seriesIndex == 0:
            sweepY = seriesData_record
        else:
            sweepY = np.hstack((sweepY,seriesData_record))

        # dfRecord['record'+str(_seriesIndex)] = seriesData_record

        # stimulus
        _stimIndex = 1
        seriesHeader_stim = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][_seriesIndex]["ch"][_stimIndex]['hd']
        TrDataScaler = seriesHeader_stim['TrDataScaler']
        TrZeroData = seriesHeader_stim['TrZeroData']
        seriesData_stim = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][_seriesIndex]["ch"][_stimIndex]['data']

        # I am guessing here, we need to work this out but we will do it
        seriesData_stim /= TrDataScaler
        seriesData_stim /= 1000

        if _seriesIndex == 0:
            sweepC = seriesData_stim
        else:
            sweepC = np.hstack((sweepC,seriesData_stim))

        # dfStim['stim'+str(_seriesIndex)] = seriesData_stim

        TrXInterval = seriesHeader_stim['TrXInterval']  # 1e-5
        TrDataPoints = seriesHeader_stim['TrDataPoints']
        # print('  TrXInterval:', TrXInterval)
        # print('  TrDataPoints:', TrDataPoints)
        
        # x axis in seconds !
        x = [x*TrXInterval for x in range(TrDataPoints)]
        _x = np.array(x)
        if _seriesIndex == 0:
            sweepX = _x
        else:
            sweepX = np.hstack((sweepX,_x))

        # plot
        ax1 = plt.subplot(2, 1, 1)
        ax1.plot(x, seriesData_record)

        ax2 = plt.subplot(2, 1, 2, sharex=ax1)
        ax2.plot(x, seriesData_stim)

    plt.show()

    # print(dfStim.head())
    # print(dfRecord.head())

    # dfStim.to_csv('/Users/cudmore/desktop/stim.csv', index=False)
    # dfRecord.to_csv('/Users/cudmore/desktop/record.csv', index=False)

    sys.exit(1)
    
    # The pulse tree can be accessed with
    # _pulse = heka_file.pul
    # print('_pulse')
    # printDict(_pulse)

    # to load a heka file and access the header ("hd") for the
    # first record, first sweep, first series, first group
    _seriesIndex = 1
    # group [0] has TrDataKind['IsLeak'] = False
    # group [1] has TrDataKind['IsLeak'] = True
    _header0 = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][_seriesIndex]["ch"][0]["hd"] 
    _header1 = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][_seriesIndex]["ch"][1]["hd"] 
    print('_header0 TrDataKind', _header0['TrDataKind'])
    print('_header1 TrDataKind', _header1['TrDataKind'])
    # data_kind = rec["hd"]["TrDataKind"]
    # this is what fails in heka reader package
    # assert not data_kind["IsLeak"], "isLeak channels not tested"
    # print('_header')
    # printDict(_header)

    sys.exit(1)

    #  or the data
    # final [0] is recording, [1] is stimulus
    _recording = heka_file.pul["ch"][0]["ch"][0]["ch"][0]["ch"][0]["data"]
    print('_recording', type(_recording), 'shape:', _recording.shape)
    print(_recording)

    # plt.plot(_recording)
    # plt.show()

    _record = 0
    _sweep = 2  # sweep 2 has 19 series
    _series = 1
    _group = 1  # [0] is recording, [1] is dac stimulus

    print('xxx')
    _tmp1 = heka_file.pul["ch"]  # [0] is first record
    _tmp2 = heka_file.pul["ch"][_record]["ch"] # [0] first sweep
    _tmp3 = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"]  # [0] first series
    _tmp4 = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][_series]["ch"]  # [0] first group
    print('_tmp1:', len(_tmp1))  # 1 record
    print('_tmp2:', len(_tmp2))  # 3 sweeps
    print('_tmp3:', len(_tmp3))  # 1 series
    print('_tmp4:', len(_tmp4))  # 2 groups

    # _dac = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][_series]["ch"][_group]["data"]
    # print('_dac', type(_dac), 'shape:', _dac.shape)
    # print(_dac)

    # plt.plot(_dac)
    # plt.show()

    series = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"]
    numSeries = len(series)
    print('numSeries:', numSeries)
    for seriesIdx in range(numSeries):
        print('  === seriesIdx:', seriesIdx)
        print('    ', heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][seriesIdx])
        try:
            _record = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][seriesIdx]["ch"][0]["data"]
            print('  _record:', _record)
            #_dac = heka_file.pul["ch"][_record]["ch"][_sweep]["ch"][seriesIdx]["ch"][1]
            plt.plot(_record)
        except (TypeError) as e:
            print('   !!!', e)

    plt.show()

    # prints "E-1 (index: 0)"
    print('=== heka_file.print_group_names():')
    heka_file.print_group_names()

    group_idx = 0
    print('=== heka_file.print_series_names(group_idx)')
    # single-10 (index: 0)
    # captest (index: 1)
    # IV (index: 2)
    heka_file.print_series_names(group_idx)

    _series = heka_file.get_series_data("Vm", 
                                       group_idx=group_idx,
                                       series_idx=series_idx,
                                       include_stim_protocol=True,
                                       fill_with_mean=False)
    print('_series:')
    printDict(_series)
