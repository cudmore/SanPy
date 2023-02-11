import numpy as np
import pandas as pd

from sanpy.fileloaders.fileLoader_base import fileLoader_base, recordingModes

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class fileLoader_csv(fileLoader_base):
    #filetype = 'csv'
    
    def loadFileType():
        return 'csv'
    
    def loadFile(self):
        """Load file and call setLoadedData().
        
        Use self.filepath for the file
        """
        # load the csv file
        _df = pd.read_csv(self.filepath)
        _columns = _df.columns
        _numColumns = len(_columns)
        if _numColumns < 2:
             logger.error(f'expecting 2 or more columns but got {_numColumns}')

        _numSamples = len(_df)
        _numSweeps = _numColumns - 1  # assuming no DAC columns
                        
        # make sweepX (assuming all sweeps have the same sweepX)
        sweepX = np.ndarray( (_numSamples,1))
        sweepX[:,0] = _df[_columns[0]].to_numpy()
        # make sweepY to hold (samples, sweeps) values, the values in each sweep are different
        sweepY = np.ndarray( (_numSamples,_numSweeps))
        for sweep in range(_numSweeps):
            colIdx = sweep + 1
            sweepY[:,sweep] = _df[_columns[colIdx]].to_numpy()
                
        #sweepC = None  # not defined

        # determine recording mode from name of column 1
        _tmpColName = _columns[1].replace('_0','')
        if _tmpColName in ['pA', 'nA']:
            _recordingMode = recordingModes.vclamp
        elif _tmpColName in ['mV', 'mv']:
            _recordingMode = recordingModes.iclamp
        else:
            logger.warning(f'did not infer recording mode from column name {_tmpColName}')
            _recordingMode = recordingModes.unknown

        _sweepLabelX = _columns[0]
        _sweepLabelY = _tmpColName  #_columns[1]
        
        self.setLoadedData(
                sweepX = sweepX,
                sweepY = sweepY,
                #sweepC = sweepC,
        )