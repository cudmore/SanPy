import os

import pandas as pd
import numpy as np

import sanpy

import sanpy.interface.plugins.stimGen2
from sanpy.interface.plugins.stimGen2 import readFileParams, buildStimDict

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

"""
bAnalysis class that loads a stim file.

TODO:
	- as usual, split into interface and gui.
		For example, move this to main api (move out of interface)
		sanpy.interface.plugins.stimGen2.readCommentParams(stimFileComment)
"""


class bAnalysisStim(sanpy.bAnalysis):
    def __init__(self, path, loadData=True, stimulusFileFolder=None):
        if stimulusFileFolder is None:
            stimulusFileFolder = os.path.split(path)[
                0
            ]  #'/media/cudmore/data/stoch-res' #os.path.split(path)[0]
        super(bAnalysisStim, self).__init__(
            file=path, loadData=True, stimulusFileFolder=stimulusFileFolder
        )

        print(self)
        print(self.abf)  # will be none
        # tmpSweepC = self.abf.sweepC

        # stimFilePath, stimFileComment = pyabf.stimulus.abbCommentFromFile(self.abf)
        stimFilePath, stimFileComment = self._commentFromAtfFile()
        self._stimDict = None  # raw parameters from snapy.interface.plugins.stimGen
        self._stimFile = None
        self._stimDictList = None  # one element per sweep
        self._stimFileDf = None
        if stimFileComment is not None:
            self._stimFile = stimFilePath
            self._stimDict = sanpy.interface.plugins.stimGen2.readCommentParams(
                stimFileComment
            )
            self._stimDict["file"] = os.path.split(stimFilePath)[
                1
            ]  # atf does not know abf file name
            # TODO: there is an error in saving atf comment string, post sweeps are always 0
            # print(f'self._stimDict:', self._stimDict)
            self._stimDictList = sanpy.interface.plugins.stimGen2.buildStimDict(
                self._stimDict, path=self.path
            )
            self._stimFileDf = self._stimFileAsDataFrame()

    def isiStats(self, hue="sweep"):
        """
        Get mean/sd/sem etc after grouping by 'sweep'
        """
        if self.numSpikes == 0:
            return None

        # df = self.analysisDf
        df = self.asDataFrame()
        # print('df:', df)
        if df is None:
            return pd.DataFrame()  # empty

        df = self.reduce()  # reduce based on start/stop of sin stimulus

        statList = []

        statStr = "isi_ms"

        stimFileDf = self._stimFileDf

        hueList = df[hue].unique()
        # for idx,oneHue in enumerate(hueList):
        for idx, sweep in enumerate(range(self.numSweeps)):
            oneHue = sweep

            dfPlot = df[df[hue] == oneHue]  # will be empty if 0 spikes in sweep

            # someSpikes = not dfPlot.empty # no spikes for this sweep

            ipi_ms = dfPlot[statStr]

            numIntervals = len(ipi_ms)
            # print('numIntervals:', numIntervals)

            minISI = np.min(ipi_ms) if numIntervals > 1 else float("nan")
            maxISI = np.max(ipi_ms) if numIntervals > 1 else float("nan")

            meanISI = np.nanmean(ipi_ms) if numIntervals > 1 else float("nan")
            medianISI = np.nanmedian(ipi_ms) if numIntervals > 1 else float("nan")
            stdISI = np.nanstd(ipi_ms) if numIntervals > 1 else float("nan")
            cvISI = stdISI / meanISI if numIntervals > 1 else float("nan")
            cvISI = round(cvISI, 3) if numIntervals > 1 else float("nan")
            cvISI_inv = (
                np.nanstd(1 / ipi_ms) / np.nanmean(1 / ipi_ms)
                if numIntervals > 1
                else float("nan")
            )
            cvISI_inv = round(cvISI_inv, 3) if numIntervals > 1 else float("nan")

            oneDict = {
                "file": self.getFileName(),
                "stat": statStr,
                "sweep": idx,
                "count": numIntervals,
                "minISI": minISI,  # round(np.nanmin(ipi_ms),3),
                "maxISI": maxISI,  # round(np.nanmax(ipi_ms),3),
                "stdISI": round(stdISI, 3),
                "meanISI": round(meanISI, 3),
                "medianISI": round(medianISI, 3),
                "cvISI": cvISI,
                "cvISI_inv": cvISI_inv,
                # stim params from stimulus file
                "Stim Freq (Hz)": "",
                "Stim Amp": "",
                "Noise Amp": "",
            }

            if stimFileDf is not None:
                if idx < len(stimFileDf):
                    oneDict["Stim Freq (Hz)"] = stimFileDf.loc[idx, "freq(Hz)"]
                    oneDict["Stim Amp"] = stimFileDf.loc[idx, "amp"]
                    oneDict["Noise Amp"] = stimFileDf.loc[idx, "noise amp"]
                else:
                    # This happens when pClamp sweeps > stimGen sweeps (like forgetting to set post=1 in stimgen)
                    logger.error(f"Did not find row {idx} in stimFileDict")

            statList.append(oneDict)

        #
        retDf = pd.DataFrame(statList)
        return retDf

    def _commentFromAtfFile(self, channel=0):
        """
        Get the comment string from atf stimulus file
        """
        from pyabf.stimulus import findStimulusWaveformFile
        from pyabf.stimulus import cachedStimuli

        stimPath = findStimulusWaveformFile(self.abf, channel)  # , verbose=False)
        if stimPath is None:
            return None, None
        else:
            return stimPath, cachedStimuli[stimPath].header["comment"]

    @property
    def stimDict(self):
        """
        If recorded with a stimulus file, return dict of stimulus parameters.
        Stimulus parameters are defined in sanpy/interface/plugins/stimGen2.py
        """
        return self._stimDict

    def reduce(self):
        """
        Reduce spikes based on start/stop of sin stimulus

        TODO:
                Use readFileParams(atfPath) to read stimulus ATF file and get start/stop

        Return:
                df of spikes within sin stimulus
        """
        # print(self.stimDict)

        # df = self.analysisDf
        df = self.asDataFrame()  # if no spikes, will be empty

        startSec, stopSec = self.getStimStartStop()

        if startSec is not None and stopSec is not None:
            df = df[(df["thresholdSec"] >= startSec) & (df["thresholdSec"] <= stopSec)]

        """
		if self.stimDict is not None:
			#print(ba.stimDict)
			startSec = self.stimDict['stimStart_sec']
			durSeconds = self.stimDict['stimDur_sec']
			stopSec = startSec + durSeconds
			try:
				df = df[ (df['peak_sec']>=startSec) & (df['peak_sec']<=stopSec)]
			except (KeyError) as e:
				logger.error(e)
		"""
        #
        return df

    def getStimStartStop(self):
        """
        If recorded with a stimGen atf file, get start/stop of stimulus.
        Some sweeps will be black, search for the first sweep that has a stimulus parameters
        assuming the start/stop of each sweep is identical (may not be in the future)

        Returns:
                startSec (float): Start sec of the stimulus
                stopSec (float): Stop sec of the stimulus
        """
        # dfStimFile = self._stimFileAsDataFrame()  # get underlying atf file params (from stimGen2)
        dfStimFile = self._stimFileDf

        if dfStimFile is None:
            # no stim file
            return None, None

        startSec = None
        durSec = None
        stopSec = None
        for idx, sweep in enumerate(range(self.numSweeps)):
            tmpStartSec = dfStimFile.loc[sweep, "start(s)"]
            if not isinstance(tmpStartSec, str):
                startSec = tmpStartSec
                durSec = dfStimFile.loc[sweep, "dur(s)"]
                stopSec = startSec + durSec
                break
        return startSec, stopSec

    def _stimFileAsDataFrame(self):
        """
        If recorded using stimGen atf file.
        Return the stmi parameters as a dataframe
        """
        d = self.stimDict
        if d is None:
            return

        # dList = buildStimDict(d, path=self.filePath)
        # for one in dList:
        # 	print(one)
        df = pd.DataFrame(self._stimDictList)
        return df
