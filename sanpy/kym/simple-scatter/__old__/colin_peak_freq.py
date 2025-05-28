import os
import sys
import json

from pprint import pprint

import pandas as pd

from sanpy.analysisDir import _walk

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis

def getSimpleFreq(tifPath, csvPath):
    df = pd.read_csv(csvPath, header=1)  # first line is detection parameters

    # reduce to ROI "1"
    df = df[df['ROI Number'] == 1]
    numPeaks = len(df)
    
    # each csv has a coresponding tif file
    # tifPath = df['Path'].iloc[0]
    # _tifPath, _tifFile = os.path.split(tifPath)
    # print(f'  raw tif file is:"{_tifFile}"')

    from sanpy._util import _loadLineScanHeader
    olympusHeader = _loadLineScanHeader(tifPath)
    # pprint(olympusHeader)

    secondsPerLine = olympusHeader['secondsPerLine']
    # print(f'  Olympus header secondsPerLine:{secondsPerLine}')
    
    with open(csvPath) as f:
        line = f.readline().strip()

    lineDict = json.loads(line)
    numRois  = len(lineDict.keys())
    roiOne = lineDict['1']
    ltrb = roiOne['ltrb']
    # print(f'  peak csv roi 1 ltrb:{ltrb}')
    roiDurSec = (ltrb[2] - ltrb[0]) * secondsPerLine
    # print(f'  roiDurSec:{roiDurSec}')

    spikesPerSecond = numPeaks / roiDurSec
    # print(f'  spikesPerSecond:{spikesPerSecond}')

    # oneDict = {
    #     'numRois': numRois,
    #     'secondsPerLine': secondsPerLine,
    #     'ltrb': ltrb,
    #     'roiDurSec': roiDurSec,
    #     'numPeaks': numPeaks,
    #     'spikesPerSecond': spikesPerSecond,
    #     'tifFile' : _tifFile,
    #     'tifPath' : tifPath,
    #     'csvPath' : csvPath,
    # }
    return spikesPerSecond

def calculate_peak_freq():
    """Calculate a frequency of peaks for each file (kym image).

    Very simple, frequency for a file is (num peaks) / (roi seconds)
    """
    dataPath = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/renamed2'

    # run this twice, once for .tif and then for .txt
    thisExt = '.csv'

    paths = _walk(dataPath, thisExt, 5)
    paths = list(paths)

    # only accept "roiPeaks.csv" files
    paths = [p for p in paths if 'roiPeaks.csv' in p]
    
    print(f'found {len(paths)} files in')
    print(dataPath)

    _dictList = []

    for idx, csvPath in enumerate(paths):
        _path, csvFile = os.path.split(csvPath)
        # print(f'  loading csvFile:"{csvFile}"')
        
        df = pd.read_csv(csvPath, header=1)  # first line is detection parameters

        # reduce to ROI "1"
        df = df[df['ROI Number'] == 1]
        numPeaks = len(df)
        
        # each csv has a coresponding tif file
        tifPath = df['Path'].iloc[0]
        _tifPath, _tifFile = os.path.split(tifPath)
        # print(f'  raw tif file is:"{_tifFile}"')

        from sanpy._util import _loadLineScanHeader
        olympusHeader = _loadLineScanHeader(tifPath)
        # pprint(olympusHeader)

        secondsPerLine = olympusHeader['secondsPerLine']
        # print(f'  Olympus header secondsPerLine:{secondsPerLine}')
        
        with open(csvPath) as f:
            line = f.readline().strip()

        lineDict = json.loads(line)
        numRois  = len(lineDict.keys())
        roiOne = lineDict['1']
        ltrb = roiOne['ltrb']
        # print(f'  peak csv roi 1 ltrb:{ltrb}')
        roiDurSec = (ltrb[2] - ltrb[0]) * secondsPerLine
        # print(f'  roiDurSec:{roiDurSec}')

        spikesPerSecond = numPeaks / roiDurSec
        # print(f'  spikesPerSecond:{spikesPerSecond}')

        oneDict = {
            'numRois': numRois,
            'secondsPerLine': secondsPerLine,
            'ltrb': ltrb,
            'roiDurSec': roiDurSec,
            'numPeaks': numPeaks,
            'spikesPerSecond': spikesPerSecond,
            'tifFile' : _tifFile,
            'tifPath' : tifPath,
            'csvPath' : csvPath,
        }

        _dictList.append(oneDict)

        # pprint(oneDict, sort_dicts=False)
        # sys.exit(1)

    df = pd.DataFrame(_dictList)
    cols = ['tifFile', 'numRois', 'secondsPerLine', 'roiDurSec', 'numPeaks', 'spikesPerSecond']
    print(df[cols])

if __name__ == '__main__':
    calculate_peak_freq()