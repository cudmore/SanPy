from typing import Union, Dict, List, Tuple
import numpy as np
import pyabf

import sanpy
from sanpy.fileloaders.fileLoader_base import fileLoader_base, recordingModes

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class fileLoader_abf(fileLoader_base):
    loadFileType = "abf"

    # @property
    # def loadFileType(self):
    #     return 'abf'

    def loadFile(self):
        self._loadAbf()

    def _loadAbf(
        self, byteStream=None, loadData: bool = True, stimulusFileFolder: str = None
    ):
        """Load pyAbf from path."""
        try:
            # logger.info(f'loadData:{loadData}')
            if byteStream is not None:
                logger.info("Loading byte stream")
                self._abf = pyabf.ABF(byteStream)
                self._isBytesIO = True
            else:
                # logger.info(f'Loading file: {self.filepath}')
                self._abf = pyabf.ABF(
                    self.filepath,
                    loadData=loadData,
                    stimulusFileFolder=stimulusFileFolder,
                )

        except NotImplementedError as e:
            logger.error(f"    did not load abf file: {self.filepath}")
            logger.error(f"      NotImplementedError exception was: {e}")
            self._loadError = True
            self._abf = None

        except Exception as e:
            # some abf files throw: 'unpack requires a buffer of 234 bytes'
            # 'ABF' object has no attribute 'sweepEpochs'
            logger.error(f"    did not load abf file: {self.filepath}")
            logger.error(f"        unknown Exception was: {e}")
            self._loadError = True
            self._abf = None

        if loadData:
            try:
                _tmp = self._abf.sweepEpochs.p1s
            except AttributeError as e:
                logger.warning(
                    f"    did not find epochTable loadData:{loadData}: {e} in file {self.filepath}"
                )
            else:
                _numSweeps = len(self._abf.sweepList)
                self._epochTableList = [None] * _numSweeps
                for _sweepIdx in range(_numSweeps):
                    self._abf.setSweep(_sweepIdx)
                    self._epochTableList[_sweepIdx] = sanpy.fileloaders.epochTable(
                        self._abf
                    )
                self._abf.setSweep(0)

            self._sweepList = self._abf.sweepList
            self._sweepLengthSec = (
                self._abf.sweepLengthSec
            )  # assuming all sweeps have the same duration

            # on load, sweep is 0
            if loadData:
                _numRows = self._abf.sweepX.shape[0]
                numSweeps = len(self._sweepList)
                self._sweepX = np.zeros((_numRows, 1))
                self._sweepY = np.zeros((_numRows, numSweeps))
                self._sweepC = np.zeros((_numRows, numSweeps))

                _channel = 0
                for sweep in self._sweepList:
                    self._abf.setSweep(sweepNumber=sweep, channel=_channel)
                    if sweep == 0:
                        self._sweepX[
                            :, sweep
                        ] = self._abf.sweepX  # <class 'numpy.ndarray'>, (60000,)
                    self._sweepY[:, sweep] = self._abf.sweepY
                    try:
                        self._sweepC[:, sweep] = self._abf.sweepC
                    except ValueError as e:
                        # pyabf will raise this error if it is an atf file
                        logger.warning(
                            f"    exception fetching sweepC for sweep {sweep} with {self.numSweeps}: {e}"
                        )
                        #
                        # if we were recorded with a stimulus file abf
                        # needed to assign stimulusWaveformFromFile
                        try:
                            tmpSweepC = self._abf.sweepC
                            self._sweepC[:, sweep] = self._abf.sweepC
                        except ValueError as e:
                            logger.warning(f"ba has no sweep {sweep} sweepC ???")

                # not needed
                self._abf.setSweep(0)

            # get v from pyAbf
            self._dataPointsPerMs = self._abf.dataPointsPerMs

            # turned back on when implementing Santana rabbit Ca kymographs
            abfDateTime = self._abf.abfDateTime  # 2019-01-14 15:20:48.196000
            
            acqDate = abfDateTime.strftime("%Y-%m-%d")
            acqTime = abfDateTime.strftime("%H:%M:%S")
            logger.info(f'acqDate:"{acqDate}')
            logger.info(f'acqTime:"{acqTime}')
            # self._acqDate = abfDateTime.strftime("%Y-%m-%d")
            # self._acqTime = abfDateTime.strftime("%H:%M:%S")

            self.setAcqDate(acqDate)
            self.setAcqTime(acqTime)
            
            self._numChannels = len(self._abf.adcUnits)
            if self._numChannels > 1:
                logger.warning(
                    f"    SanPy does not work with multi-channel recordings numChannels is {self._numChannels} {self._path}"
                )
                # logger.warning('    Will default to channel 0')

            # self.sweepUnitsY = self.adcUnits[channel]
            channel = 0
            # dacUnits = self._abf.dacUnits[channel]
            adcUnits = self._abf.adcUnits[channel]
            # print('  adcUnits:', adcUnits)  # 'mV'
            self._sweepLabelY = adcUnits
            self._sweepLabelX = "sec"

            # self._sweepLabelX = self._abf.sweepLabelX
            # self._sweepLabelY = self._abf.sweepLabelY
            if self._sweepLabelY in ["pA", "nA"]:
                self._recordingMode = recordingModes.vclamp  # 'V-Clamp'
                # self._sweepY_label = self._abf.sweepUnitsY
            elif self._sweepLabelY in ["mV"]:
                self._recordingMode = recordingModes.iclamp  #'I-Clamp'
                # self._sweepY_label = self._abf.sweepUnitsY
            else:
                logger.warning(f'did not understand adcUnit "{adcUnits}"')

        #
        self.myFileType = "abf"

        # base sanpy does not keep the abf around
        # logger.warning('[[[TURNED BACK ON]]] I turned off assigning self._abf=None for stoch-res stim file load')
        self._abf = None
