import numpy as np
import pandas as pd

from sanpy.fileloaders.fileLoader_base import fileLoader_base, recordingModes

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class fileLoader_text(fileLoader_base):
    loadFileType = ".sanpy"

    # @property
    # def loadFileType(self):
    #     return 'csv'

    def loadFile(self):
        """Load file and call setLoadedData().

        Use self.filepath for the file

        Column 0 is seconds
        Column 1 is recording in ['mV', 'pA']
        """
        # load the csv file
        try:
            _df = pd.read_csv(self.filepath)
        except (pd.errors.EmptyDataError):
            self._loadError = True
            return
        
        _columns = _df.columns
        _numColumns = len(_columns)
        if _numColumns < 2:
            logger.error(f"expecting 2 or more columns but got {_numColumns}")
            self._loadError = True
            return

        _numSamples = len(_df)
        _numSweeps = _numColumns - 1  # assuming no DAC columns

        # TODO: check that the columns we will read are float (not str or object)
        #
        # make sweepX (assuming all sweeps have the same sweepX)
        sweepX = np.ndarray((_numSamples, 1))
        try:
            sweepX[:, 0] = _df[_columns[0]].to_numpy()
        except ValueError as e:
            # raise ValueError
            logger.error(f"ValueError assigning the first column")
            self._loadError = True
            return

        # make sweepY to hold (samples, sweeps) values, the values in each sweep are different
        sweepY = np.ndarray((_numSamples, _numSweeps))
        for sweep in range(_numSweeps):
            colIdx = sweep + 1
            sweepY[:, sweep] = _df[_columns[colIdx]].to_numpy()

        # sweepC = None  # not defined

        # determine recording mode from name of column 1
        _tmpColName = _columns[1].replace("_0", "")
        if _tmpColName in ["pA", "nA"]:
            _recordingMode = recordingModes.vclamp
        elif _tmpColName in ["mV", "mv"]:
            _recordingMode = recordingModes.iclamp
        else:
            logger.warning(
                f"did not infer recording mode from column name {_tmpColName}"
            )
            _recordingMode = recordingModes.unknown

        xLabel = _columns[0]
        yLabel = _tmpColName  # _columns[1]

        self.setLoadedData(
            sweepX=sweepX,
            sweepY=sweepY,
            # sweepC = sweepC,
            xLabel=xLabel,
            yLabel=yLabel,
        )
