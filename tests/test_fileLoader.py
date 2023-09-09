import os

import sanpy

# from sanpy.analysisPlot import bAnalysisPlot

from sanpy.fileloaders.fileLoader_abf import fileLoader_abf
# from sanpy.fileloaders.fileLoader_csv import fileLoader_csv
from sanpy.fileloaders.fileLoader_tif import fileLoader_tif

import logging
from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__, level=logging.DEBUG)

def test_fileLoader_tif():
    #path = 'data/kymograph/rosie-kymograph.tif'
    path = os.path.join('data', 'kymograph', 'rosie-kymograph.tif')
    tifFile = fileLoader_tif(path)
    assert tifFile is not None

    logger.info(f'tifFile: {tifFile}')

    # test plot
    # ap = bAnalysisPlot(tifFile)
    # ap.plotRaw()

    # import matplotlib.pyplot as plt
    # plt.show()

def _old_test_fileLoader_csv():
    # path = 'data/19114001.csv'
    # path = 'data/2021_07_20_0010.csv'
    path = os.path.join('data', '2021_07_20_0010.csv')

    csvFile = fileLoader_csv(path)
    assert csvFile is not None

    csvFile._getDerivative() # calcullate derivates

    _filteredDeriv = csvFile.filteredDeriv
    assert _filteredDeriv.shape == csvFile.sweepX.shape

    # logger.info(f'csvFile: {csvFile}')

    csvFile.setSweep(0)

    # logger.info(f'dataPointsPerMs: {csvFile.dataPointsPerMs}')
    # logger.info(f'sweepX: {csvFile.sweepX.shape}')
    # logger.info(f'sweepY: {csvFile.sweepY.shape}')
    # logger.info(f'sweepC: {csvFile.sweepC.shape}')

    # test plot
    # ap = bAnalysisPlot(csvFile)
    # ap.plotRaw()

    # import matplotlib.pyplot as plt
    # plt.show()

def test_fileLoader_abf():
    # path = 'data/19114001.abf'
    # path = 'data/2021_07_20_0010.abf'
    path = os.path.join('data', '2021_07_20_0010.abf')

    abfFile = fileLoader_abf(path)
    assert abfFile is not None

    # logger.info(f'abfFile: {abfFile}')

    assert abfFile.loadFileType == 'abf'

    assert abfFile.sweepLabelX == 'sec'

    abfFile._getDerivative() # calcullate derivates

    _filteredDeriv = abfFile.filteredDeriv
    assert _filteredDeriv.shape == abfFile.sweepX.shape

    # print(abfFile)

    # test plot
    # ap = bAnalysisPlot(abfFile)
    # ap.plotRaw()

    # import matplotlib.pyplot as plt
    # plt.show()

    # utility to export an abf as csv (use once)
    if 0:
        import pandas as pd
        df = pd.DataFrame()
        df['sec'] = abfFile.sweepX

        for _sweep in abfFile.sweepList:
            abfFile.setSweep(_sweep)
            _sweepY = abfFile.sweepY

            colStr = 'mv_' + str(_sweep)
            df[colStr] = abfFile.sweepY

            # DAC

        _folder, csvFileName = os.path.split(path)
        csvFileName = os.path.splitext(csvFileName)[0] + '.csv'
        csvPath = os.path.join(_folder, csvFileName)
        print('csvPath:', csvPath)
        df.to_csv(csvPath, index=False)

    
def test_new_b_analysis():
    # test new version of bAnalysis using fileLoader
    # path = 'data/19114001.abf'
    path = os.path.join('..', 'data', '19114001.abf')
    ba = sanpy.bAnalysis(path)

    # path = 'data/19114001.csv'
    path = os.path.join('..', 'data', '19114001.csv')
    ba = sanpy.bAnalysis(path)

if __name__ == '__main__':
    #test_fileLoader_abf()
    # test_fileLoader_csv()
    pass