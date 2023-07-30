import numpy as np

import pyabf

from sanpy.fileloaders.fileLoader_base import fileLoader_base, recordingModes

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class fileLoader_atf(fileLoader_base):
    loadFileType = "atf"

    # def __init__(self, path):
    #     super().__init__(path)
    #     # self._loadAtf()

    def loadFile(self):
        self._loadAtf()

    def _loadAtf(self):
        # We cant't get dataPointsPerMs without loading the data
        loadData = True

        try:
            self._abf = pyabf.ATF(self.filepath)  # , loadData=loadData)
        except (ValueError) as e:
            logger.error(f"    did not load atf file: {self.filepath}")
            logger.error(f"      ValueError exception was: {e}")
            self.setLoadError(True)
            self._abf = None
            return
        except (Exception) as e:
            logger.error(f"    did not load atf file: {self.filepath}")
            logger.error(f"      ValueError exception was: {e}")
            self.setLoadError(True)
            self._abf = None
            return

        print("  self._abf:", self._abf.sweepList)
        # try:
        if 1:
            self._sweepList = self._abf.sweepList
            self._sweepLengthSec = self._abf.sweepLengthSec
            if loadData:
                tmpRows = self._abf.sweepX.shape[0]
                numSweeps = len(self._sweepList)
                self._sweepX = np.zeros((tmpRows, numSweeps))
                self._sweepY = np.zeros((tmpRows, numSweeps))
                self._sweepC = np.zeros((tmpRows, numSweeps))

                for sweep in self._sweepList:
                    self._abf.setSweep(sweep)
                    self._sweepX[
                        :, sweep
                    ] = self._abf.sweepX  # <class 'numpy.ndarray'>, (60000,)
                    self._sweepY[:, sweep] = self._abf.sweepY
                    # self._sweepC[:, sweep] = self._abf.sweepC
                # not needed
                self._abf.setSweep(0)

            logger.info(f"Loaded abf self._sweepX: {self._sweepX.shape}")
            # get v from pyAbf
            if len(self.sweepX.shape) > 1:
                t0 = self.sweepX[0][0]
                t1 = self.sweepX[1][0]
            else:
                t0 = self.sweepX[0]
                t1 = self.sweepX[1]
            dt = (t1 - t0) * 1000
            dataPointsPerMs = 1 / dt
            dataPointsPerMs = round(dataPointsPerMs)
            self._dataPointsPerMs = dataPointsPerMs

            """
            channel = 0
            adcUnits = self._abf.adcUnits[channel]
            self._sweepLabelY = adcUnits
            self._sweepLabelX = "sec'"
            """
            self._sweepLabelY = "mV"
            self._sweepLabelX = "sec'"

            if self._sweepLabelY in ["pA"]:
                self._recordingMode = recordingModes.vclamp  # 'V-Clamp'
            elif self._sweepLabelY in ["mV"]:
                self._recordingMode = recordingModes.iclamp  #'I-Clamp'

        """
        except (Exception) as e:
            # some abf files throw: 'unpack requires a buffer of 234 bytes'
            logger.error(f'did not load ATF file: {self._path}')
            logger.error(f'  unknown Exception was: {e}')
            self.loadError = True
            self._abf = None
        """

        self.myFileType = "atf"

        # don't keep _abf, we grabbed every thing we needed
