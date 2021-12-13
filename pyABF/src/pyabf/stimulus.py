"""
ABFs can be created when signals are applied using the DAC. If these "stimulus
waveforms" are used, they either come from an epoch table or from a DAC file.
Code in this file determines where the stimulus comes from and returns it for
a given sweep and channel.

If the stimulus waveform comes from a file, code here also assists in caching
the data from that file so the file only needs to be read from disk once.
"""

import numpy as np
import copy
import os
from pathlib import Path, PureWindowsPath
import warnings
import pyabf
import pyabf.waveform

# cache stimulus files in this dictionary
# keys are stimulus filenames, values are ABF and ATF objects
cachedStimuli = {}


class Stimulus:
    """
    The Stimulus class used to be where all waveform generation happened.
    Waveform generation from the epoch table now occurs in waveform.py.
    This class is kept so old code doesn't break, but is getting dismantled.
    """

    def __init__(self, abf, channel):
        assert isinstance(abf, pyabf.ABF)
        self.abf = abf
        self.channel = channel
        self.text = ""  # this is displayed on the markdown info page

    def __str__(self):
        return "Stimulus(abf, %d)" % self.channel

    def __repr__(self):
        return "Stimulus(abf, %d)" % self.channel

    def stimulusWaveform(self, stimulusSweep=0):
        """
        Return a signal (the same size as a sweep) representing the command
        waveform of the DAC for the given channel.
        """

        if hasattr(self.abf, "_synchArraySection"):
            uniqueSweepLengths = set(self.abf._synchArraySection.lLength)
            if len(uniqueSweepLengths) > 1:
                self.text = "variable-length sweeps do not support DAC waveform"
                return np.full(self.abf._synchArraySection.lLength[stimulusSweep],
                               self.abf.holdingCommand[self.channel])

        if self.abf.abfVersion["major"] == 1:
            nWaveformEnable = self.abf._headerV1.nWaveformEnable[self.channel]
            nWaveformSource = self.abf._headerV1.nWaveformSource[self.channel]
        elif self.abf.abfVersion["major"] == 2:
            nWaveformEnable = self.abf._dacSection.nWaveformEnable[self.channel]
            nWaveformSource = self.abf._dacSection.nWaveformSource[self.channel]

        if nWaveformEnable == 0 or nWaveformSource == 0:
            self.text = "DAC waveform is not enabled"
            return np.full(self.abf.sweepPointCount,
                           self.abf.holdingCommand[self.channel])

        elif nWaveformSource == 1:
            epochTable = pyabf.waveform.EpochTable(self.abf, self.channel)
            self.text = str(epochTable)
            sweepWaveform = epochTable.epochWaveformsBySweep[stimulusSweep]
            sweepC = sweepWaveform.getWaveform()
            return sweepC

        elif nWaveformSource == 2:
            self.text = "DAC waveform is controlled by custom file"
            # abb added stimulusSweep
            return stimulusWaveformFromFile(self.abf, stimulusSweep=stimulusSweep)

        else:
            self.text = "unknown nWaveformSource (%d)" % nWaveformSource
            return np.full(self.abf.sweepPointCount, np.nan)


# abb added verbose
def findStimulusWaveformFile(abf, channel=0, verbose=True):
    """
    Look for the stimulus waveform file in several places. Return the path
    where it can be found. Return None if it cannot be found.

    The original path is an absolute windows filename stored in the ABF header.
    """

    # first try looking at the path stored in the header
    pathInHeader = Path(abf._stringsIndexed.lDACFilePath[channel])
    if pathInHeader.is_file():
        return str(pathInHeader)

    # try the current working directory of the Python interpreter
    stimBasename = PureWindowsPath(pathInHeader).name
    pathCurrent = Path(stimBasename).resolve().absolute()
    if pathCurrent.is_file():
        return str(pathCurrent)

    # try path defined by the stimulusFileFolder argument of the ABF constructor
    pathUserDefined = Path(str(abf.stimulusFileFolder)).joinpath(stimBasename).resolve()
    if pathUserDefined.is_file():
        return str(pathUserDefined)

    # try the same folder that houses the ABF file
    pathSameFolderAsABF = Path(abf.abfFilePath).parent.joinpath(stimBasename).resolve()
    if pathSameFolderAsABF.is_file():
        return str(pathSameFolderAsABF)

    # warn if stimulus file was never found
    if verbose:
        warnings.warn(
            f"Could not locate stimulus file for channel {channel}.\n"
            f"ABF file path: {abf.abfFilePath}.\n"
            f"The following paths were searched:\n"
            f"* Path in the ABF header: {pathInHeader}\n"
            f"* Current working directory: {pathCurrent}\n"
            f"* User-defined stimulus folder: {pathUserDefined}\n"
            f"* Same folder as ABF: {(pathSameFolderAsABF)}\n"
        )

    return None

# abb to get comment
def abbCommentFromFile(abf, channel=0):
    """
    If stim file exists, return (path, comment)
    """
    stimPath = findStimulusWaveformFile(abf, channel, verbose=False)
    if stimPath is None:
        return None, None
    else:
        return stimPath, cachedStimuli[stimPath].header['comment']

# abb stimulusSweep=None
def stimulusWaveformFromFile(abf, channel=0, stimulusSweep=None):
    """
    Attempt to find the stimulus file used to record an ABF, read the stimulus
    file (ABF or ATF), and return the stimulus waveform (as a numpy array).
    """

    assert isinstance(abf, pyabf.ABF)
    assert channel in abf.channelList

    stimPath = findStimulusWaveformFile(abf, channel)

    if not stimPath:
        return np.full(abf.sweepPointCount, np.nan)

    if abf._cacheStimulusFiles:
        if not stimPath in cachedStimuli.keys():
            if stimPath.upper().endswith(".ABF"):
                cachedStimuli[stimPath] = pyabf.ABF(stimPath)
            elif stimPath.upper().endswith(".ATF"):
                print('abb pyabf stimulus.stimulusWaveformFromFile() assigning cachedStimuli')
                cachedStimuli[stimPath] = pyabf.ATF(stimPath)
        # abb, setSweep
        cachedStimuli[stimPath].setSweep(stimulusSweep)
        return cachedStimuli[stimPath].sweepY
    else:
        if stimPath.upper().endswith(".ABF"):
            return pyabf.ABF(stimPath).sweepY
        elif stimPath.upper().endswith(".ATF"):
            return pyabf.ATF(stimPath).sweepY
