"""
Plugin to create and save Axon ATF files

File looks like this 20211119

ATF    1.0
8    11
"AcquisitionMode=Episodic Stimulation"
"Comment="
"YTop=20000"
"YBottom=-20000"
"SyncTimeUnits=100"
"SweepStartTimesMS=21.000,221.000,421.000,621.000,821.000,1021.000,1221.000,1421.000,1621.000,1821.000"
"SignalsExported=IN 0"
"Signals="    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"
"Time (s)"    "Trace #1 (pA)"    "Trace #2 (pA)"    "Trace #3 (pA)"    "Trace #4 (pA)"    "Trace #5 (pA)"    "Trace #6 (pA)"    "Trace #7 (pA)"    "Trace #8 (pA)"    "Trace #9 (pA)"    "Trace #10 (pA)"
0    1.2207    1.2207    5.49316    2.44141    3.66211    0.610352    2.44141    5.49316    1.83105    2.44141
1e-4    2.44141    1.2207    0.610352    2.44141    2.44141    0.610352    0.610352    1.2207    3.05176    3.05176
"""

import os, sys
from functools import partial

from datetime import datetime

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtWidgets, QtGui

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends import backend_qt5agg

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


def readFolderParams(folderPath):
    """
    Return a DataFrame, one row per file. Columns are stim parameters
    """
    dList = []
    for file in sorted(os.listdir(folderPath)):
        if not file.endswith(".atf"):
            continue
        filePath = os.path.join(folderPath, file)
        d = readFileParams(filePath)
        dList.append(d)
    #
    df = pd.DataFrame(dList)
    outFile = os.path.join(folderPath, "stimGen_db.csv")
    print("saving:", outFile)
    df.to_csv(outFile)

    return df


def readFileParams(path):
    """
    Read stimGen params from one atf file
    """
    retDict = {}
    with open(path, "r") as f:
        while True:
            # lines = f.readlines()
            line = f.readline()
            if not line:
                break  # EOF
            if line.startswith('"Comment='):
                # looks like
                # "Comment=version=0.2;numSweeps=5;sweepDurSeconds=30.0;stimType=Sin;stimStartSeconds=5.0;durSeconds=20.0;yStimOffset=0.0;amplitude=0.002;frequency=1.0;noiseAmplitude=0.0;amplitudeStep=0.0;frequencyStep=0.0;noiseStep=0.0;doRectify=False;"
                line = line.replace('"Comment=', "")
                line = line[0:-2]  # remove trailing "
                # print(line)
                for param in line.split(";"):
                    kv = param.split("=")
                    # print(kv)
                    if len(kv) != 2:
                        continue
                    k = kv[0]
                    v = kv[1]
                    # print(k, v)

                    if k == "stimType":
                        pass
                    elif k == "doRectify":
                        v = bool(v)
                    elif k == "numSweeps":
                        v = int(v)
                    else:
                        v = float(v)
                    #
                    retDict[k] = v
                #
                break
    #
    return retDict


class stimGen(sanpyPlugin):
    myHumanName = "Stim Gen"

    def __init__(self, myAnalysisDir=None, **kwargs):
        """
        Args:
            ba (bAnalysis): Not required
        """
        super(stimGen, self).__init__(**kwargs)

        self.saveStimIndex = 0

        self.version = 0.2  # v0.2 on 20211202

        self._fs = 10000
        # sampling frequency in (samples per second)

        self.numSweeps = 5

        self._data = [None] * self.numSweeps  # list of sweeps
        self._t = []

        self.stimTypes = [
            "Sin",
            "Chirp",
            "Noise",
            "Epsp train",
            #'Stochastic HH',
            "Integrate and Fire",
        ]
        # TODO: add (save index, ...)
        self.stimType = "Sin"
        self.sweepDurSeconds = 30.0
        self.stimStartSeconds = 5.0
        self.durSeconds = 20.0  # of stim
        self.yStimOffset = 0.0
        self.amplitude = 0.002
        self.frequency = 1.0
        self.noiseAmplitude = 0.0  # sqrt() of this is STD of Gaussian noise

        # step for multiple sweeps
        self.amplitudeStep = 0.0
        self.frequencyStep = 0.0
        self.noiseStep = 0.0

        self.doRectify = False
        """ remove all <0 from output stim """

        self.scale = 1
        """ scale output stim by this factor"""

        self.savePath = ""  # remember last save folder

        # TODO: all params need to be in dictionary
        # when user clicks on interface (spinbox), we need to update this dict
        self.paramDict = self.defaultParams()

        self.buildUI()

        self.updateStim()

    def defaultParams(self):
        paramDict = {
            "version": 0.3,
            "stimType": "Sin",  # str of stim types
            "fs": 10000,  # int, samples per second
            "numSweeps": 5,  # int
            "sweepDur_sec": 30.0,
            "stimStart_sec": 5.0,
            "stimDur_sec": 20.0,
            "yOffset": 0.0,
            # First sweep parameters
            "stimFreq": 1.0,
            "stimAmp": 0.002,
            "stimNoiseAmp": 0.0,
            # step parameters
            "stimFreqStep": 0.0,
            "stimAmpStep": 0.0,
            "stimNoiseStep": 0.0,
            #
            "rectify": False,
            "scale": 1,
        }

    def getComment(self):
        comment = ""  # '"Comment='

        comment += f"version={self.version};"
        comment += f"numSweeps={self.numSweeps};"
        comment += f"sweepDurSeconds={self.sweepDurSeconds};"
        comment += f"stimType={self.stimType};"
        comment += f"stimStartSeconds={self.stimStartSeconds};"
        comment += f"durSeconds={self.durSeconds};"
        comment += f"yStimOffset={self.yStimOffset};"
        comment += f"amplitude={self.amplitude};"
        comment += f"frequency={self.frequency};"
        comment += f"noiseAmplitude={self.noiseAmplitude};"
        comment += f"amplitudeStep={self.amplitudeStep};"
        comment += f"frequencyStep={self.frequencyStep};"
        comment += f"noiseStep={self.noiseStep};"
        comment += f"doRectify={self.doRectify};"

        #
        # comment += '"'
        return comment

    def getAtfHeader(self, numChannels=1):
        """
        See: https://github.com/christianrickert/Axon-Text-File/blob/master/data.atf

        File looks like this 20211119

        ATF    1.0
        8    11
        "AcquisitionMode=Episodic Stimulation"
        "Comment="
        "YTop=20000"
        "YBottom=-20000"
        "SyncTimeUnits=100"
        "SweepStartTimesMS=21.000,221.000,421.000,621.000,821.000,1021.000,1221.000,1421.000,1621.000,1821.000"
        "SignalsExported=IN 0"
        "Signals="    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"
        "Time (s)"    "Trace #1 (pA)"    "Trace #2 (pA)"    "Trace #3 (pA)"    "Trace #4 (pA)"    "Trace #5 (pA)"    "Trace #6 (pA)"    "Trace #7 (pA)"    "Trace #8 (pA)"    "Trace #9 (pA)"    "Trace #10 (pA)"
        0    1.2207    1.2207    5.49316    2.44141    3.66211    0.610352    2.44141    5.49316    1.83105    2.44141
        1e-4    2.44141    1.2207    0.610352    2.44141    2.44141    0.610352    0.610352    1.2207    3.05176    3.05176
        """

        myUnits = "pA"
        # myComment = 'fill in with stim params'

        numDataColumns = numChannels + 1  # time + number of channels
        eol = "\n"
        tab = "\t"
        ATF_HEADER = "ATF    1.0" + eol
        ATF_HEADER += f"8\t{numDataColumns}" + eol

        ATF_HEADER += '"AcquisitionMode=Episodic Stimulation"' + eol

        myComment = self.getComment()
        ATF_HEADER += f'"Comment={myComment}"' + eol

        ATF_HEADER += '"YTop=20000"' + eol
        ATF_HEADER += '"YBottom=-20000"' + eol
        ATF_HEADER += '"SyncTimeUnits=100"' + eol

        # for a 200 ms sweep, looks like this
        # "SweepStartTimesMS=21.000,221.000,421.000,621.000,821.000,1021.000,1221.000,1421.000,1621.000,1821.000"
        # durMs = self.durSeconds *1000
        durMs = self.sweepDurSeconds * 1000  # new 20211202
        numSweeps = self.numSweeps
        sweepRange = range(numSweeps)
        SweepStartTimesMS = '"SweepStartTimesMS='
        preRollMs = 21
        for sweepIdx, sweep in enumerate(sweepRange):
            currStartTime = preRollMs + (sweepIdx * durMs)
            SweepStartTimesMS += f"{round(float(currStartTime),3)}" + ","
        # remove last comma
        SweepStartTimesMS = SweepStartTimesMS[0:-1]
        SweepStartTimesMS += '"'
        ATF_HEADER += SweepStartTimesMS + eol

        ATF_HEADER += '"SignalsExported=IN 0"' + eol

        # signals looks like this
        # "Signals="    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"
        Signals = '"Signals="' + "\t"
        for sweepIdx, sweep in enumerate(sweepRange):
            Signals += '"IN 0"' + "\t"
        # remove last tab
        Signals = Signals[0:-1]
        ATF_HEADER += Signals + eol

        ATF_HEADER += f'"Time (s)"' + tab
        traceStr = ""
        for channel in range(numChannels):
            traceStr += (
                f'"Trace #{channel+1} ({myUnits})"' + tab
            )  # not sure if trailing tab is ok???
        # remove last tab
        traceStr = traceStr[0:-1]
        ATF_HEADER += traceStr + eol

        print("=== ATF_HEADER:")
        print(ATF_HEADER)

        '''
        ATF_HEADER = """
        ATF    1.0
        8    3
        "AcquisitionMode=Episodic Stimulation"
        "Comment="
        "YTop=2000"
        "YBottom=-2000"
        "SyncTimeUnits=20"
        "SweepStartTimesMS=0.000"
        "SignalsExported=IN 0"
        "Signals="    "IN 0"
        "Time (s)"    "Trace #1"    "Trace #2"
        """.strip()
        '''

        return ATF_HEADER

    """
    @property
    def data(self):
        return self._data
    """

    @property
    def t(self):
        return self._t

    @property
    def fs(self):
        return self._fs

    def makeStim(self):
        type = self.stimType
        fs = self.fs
        sweepDurSeconds = self.sweepDurSeconds  # new 20211202
        stimStartSeconds = self.stimStartSeconds  # of stim
        durSec = self.durSeconds  # of stim
        yStimOffset = self.yStimOffset
        amp = self.amplitude
        freq = self.frequency
        noiseAmp = self.noiseAmplitude
        doRectify = self.doRectify

        amplitudeStep = self.amplitudeStep
        frequencyStep = self.frequencyStep
        noiseStep = self.noiseStep

        self._data = [None] * self.numSweeps
        for sweepNum in range(self.numSweeps):
            currAmp = amp + (sweepNum * amplitudeStep)
            currFreq = freq + (sweepNum * frequencyStep)
            currNoiseAmp = noiseAmp + (sweepNum * noiseStep)
            autoPad = False

            # print(
            #     f"  makeStim() {type} sweep:{sweepNum} durSec:{durSec} amp:{currAmp} freq:{currFreq} noiseAmp:{currNoiseAmp}"
            # )

            self._data[sweepNum] = sanpy.atfStim.makeStim(
                type,
                sweepDurSec=sweepDurSeconds,
                startStimSec=stimStartSeconds,
                durSec=durSec,
                yStimOffset=yStimOffset,
                amp=currAmp,
                freq=currFreq,
                fs=fs,
                noiseAmp=currNoiseAmp,
                rectify=doRectify,
                autoPad=autoPad,
                autoSave=False,
            )
            if self._data[sweepNum] is None:
                print(f"makeStim() error making {type} at sweep number {sweepNum}")
            #
            # scale
            self._data[sweepNum] *= self.scale
            print("  self._data[sweepNum].dtype:", self._data[sweepNum].dtype)

        self._t = np.arange(len(self._data[0])) / fs  # just using first sweep

    """
    def plotStim(self):
        logger.info(f'_t:{self._t.shape}')
        logger.info(f'_data:{self._data.shape}')
        plt.plot(self._t, self._data)
    """

    """
    def saveStim(Self):
        sanpy.atfStim.saveAtf(self.data, fileName="output.atf", fs=10000)
    """

    def _grabParams(self):
        """
        Grab all interface parameters in member variables
        """

        self.sweepDurSeconds = self.sweepDurationSpinBox.value()  # new 20211202
        self.numSweeps = self.numSweepsSpinBox.value()

        self.stimStartSeconds = self.stimStartSpinBox.value()  # start of sin
        self.durSeconds = self.durationSpinBox.value()  # duration of stim
        self.yStimOffset = self.yStimOffsetSpinBox.value()
        self.amplitude = self.amplitudeSpinBox.value()
        self.frequency = self.frequencySpinBox.value()
        self.noiseAmplitude = self.noiseAmpSpinBox.value()

        self.amplitudeStep = self.amplitudeStepSpinBox.value()
        self.frequencyStep = self.frequencyStepSpinBox.value()
        self.noiseStep = self.noiseStepSpinBox.value()

        self.doRectify = self.rectifyCheckBox.isChecked()
        self._fs = self.fsSpinBox.value()

        """
        rmsMult = 1/np.sqrt(2)
        sinRms = self.amplitude * rmsMult
        sinRms = round(sinRms,2)
        aName = f'RMS:{sinRms}'
        self.sinRms.setText(aName)
        """

    def updateStim(self):
        self._grabParams()
        self.makeStim()
        self.replot()

    def on_spin_box2(self, name, obj):
        print(name, obj.value())

    def on_spin_box(self, name):
        logger.info(name)
        if name == "Number Of Sweeps":
            numSweeps = self.numSweepsSpinBox.value()
            self._updateNumSweeps(numSweeps)
        elif name == "Save Index":
            saveStimIndex = self.saveIndexSpinBox.value()
            self.saveStimIndex = saveStimIndex
            #
        self.updateStim()

    def on_stim_type(self, type):
        logger.info(type)
        self.stimType = type
        self.updateStim()

    def on_scale(self, scale):
        logger.info(type)
        self.scale = float(scale)
        self.updateStim()

    def on_button_click(self, name):
        logger.info(name)
        if name == "Make Stimulus":
            self.makeStim()
        elif name == "Save As...":
            # TODO: srt a feeback red as we save, set to green when done
            # self.saveAsButton
            self.saveAs()
        else:
            logger.info(f'name "{name}" not understood.')

    def on_checkbox_clicked(self, name):
        self.updateStim()

    def buildUI(self):
        # main layout
        vLayout = QtWidgets.QVBoxLayout()
        controlLayout = QtWidgets.QHBoxLayout()

        """
        aName = 'Make Stimulus'
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click,aName))
        controlLayout.addWidget(aButton)
        """

        aName = "Save As..."
        self.saveAsButton = QtWidgets.QPushButton(aName)
        self.saveAsButton.clicked.connect(partial(self.on_button_click, aName))
        controlLayout.addWidget(self.saveAsButton)

        aName = "Save Index"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout.addWidget(aLabel)
        self.saveIndexSpinBox = QtWidgets.QSpinBox()
        self.saveIndexSpinBox.setKeyboardTracking(False)
        self.saveIndexSpinBox.setRange(0, 9999)
        self.saveIndexSpinBox.setValue(self.saveStimIndex)
        self.saveIndexSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        # self.saveIndexSpinBox.valueChanged.connect(partial(self.on_spin_box2, aName, self.saveIndexSpinBox))
        controlLayout.addWidget(self.saveIndexSpinBox)

        aName = "Stim Type"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout.addWidget(aLabel)
        self.stimTypeDropdown = QtWidgets.QComboBox()
        for type in self.stimTypes:
            self.stimTypeDropdown.addItem(type)
        self.stimTypeDropdown.currentTextChanged.connect(self.on_stim_type)
        controlLayout.addWidget(self.stimTypeDropdown)

        aName = "Sweep Duration(s)"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout.addWidget(aLabel)
        self.sweepDurationSpinBox = QtWidgets.QDoubleSpinBox()
        self.sweepDurationSpinBox.setKeyboardTracking(False)
        self.sweepDurationSpinBox.setRange(0, 2**16)
        self.sweepDurationSpinBox.setValue(self.sweepDurSeconds)
        self.sweepDurationSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        controlLayout.addWidget(self.sweepDurationSpinBox)

        aName = "Number Of Sweeps"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout.addWidget(aLabel)
        self.numSweepsSpinBox = QtWidgets.QSpinBox()
        self.numSweepsSpinBox.setKeyboardTracking(False)
        self.numSweepsSpinBox.setRange(1, 100)
        self.numSweepsSpinBox.setValue(self.numSweeps)
        self.numSweepsSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        controlLayout.addWidget(self.numSweepsSpinBox)

        vLayout.addLayout(controlLayout)  # add mpl canvas

        # row 1.5
        controlLayout_row1_5 = QtWidgets.QHBoxLayout()

        aName = "Stim Start(s)"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row1_5.addWidget(aLabel)
        self.stimStartSpinBox = QtWidgets.QDoubleSpinBox()
        self.stimStartSpinBox.setKeyboardTracking(False)
        self.stimStartSpinBox.setRange(0, 2**16)
        self.stimStartSpinBox.setValue(self.stimStartSeconds)
        self.stimStartSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        controlLayout_row1_5.addWidget(self.stimStartSpinBox)

        aName = "Stim Duration(s)"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row1_5.addWidget(aLabel)
        self.durationSpinBox = QtWidgets.QDoubleSpinBox()
        self.durationSpinBox.setKeyboardTracking(False)
        self.durationSpinBox.setRange(0, 2**16)
        self.durationSpinBox.setValue(self.durSeconds)
        self.durationSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        controlLayout_row1_5.addWidget(self.durationSpinBox)

        aName = "Stim Offset(y)"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row1_5.addWidget(aLabel)
        self.yStimOffsetSpinBox = QtWidgets.QDoubleSpinBox()
        self.yStimOffsetSpinBox.setKeyboardTracking(False)
        self.yStimOffsetSpinBox.setRange(-1e9, 2**16)
        self.yStimOffsetSpinBox.setValue(self.yStimOffset)
        self.yStimOffsetSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        controlLayout_row1_5.addWidget(self.yStimOffsetSpinBox)

        vLayout.addLayout(controlLayout_row1_5)  # add mpl canvas

        # 2nd row
        controlLayout_row2 = QtWidgets.QGridLayout()
        rowSpan = 1
        colSpan = 1
        row = 0
        col = 0

        aName = "Amplitude"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row2.addWidget(aLabel, row, col, rowSpan, colSpan)
        self.amplitudeSpinBox = QtWidgets.QDoubleSpinBox()
        self.amplitudeSpinBox.setKeyboardTracking(False)
        self.amplitudeSpinBox.setRange(0, 2**16)
        self.amplitudeSpinBox.setDecimals(5)
        self.amplitudeSpinBox.setValue(self.amplitude)
        self.amplitudeSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        controlLayout_row2.addWidget(self.amplitudeSpinBox, 0, 1, rowSpan, colSpan)

        # rms of sin (amp and freq)
        """
        rmsMult = 1/np.sqrt(2)
        sinRms = self.amplitude * rmsMult
        sinRms = round(sinRms,2)
        aName = f'RMS:{sinRms}'
        self.sinRms = QtWidgets.QLabel(aName)
        controlLayout_row2.addWidget(self.sinRms, 0, 2, rowSpan, colSpan)
        """

        aName = "Frequency (Hz)"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row2.addWidget(aLabel, 0, 3, rowSpan, colSpan)
        self.frequencySpinBox = QtWidgets.QDoubleSpinBox()
        self.frequencySpinBox.setKeyboardTracking(False)
        self.frequencySpinBox.setRange(0, 2**16)
        self.frequencySpinBox.setValue(self.frequency)
        self.frequencySpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        controlLayout_row2.addWidget(self.frequencySpinBox, 0, 4, rowSpan, colSpan)

        aName = "Noise Amplitude"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row2.addWidget(aLabel, 0, 5, rowSpan, colSpan)
        self.noiseAmpSpinBox = QtWidgets.QDoubleSpinBox()
        self.noiseAmpSpinBox.setKeyboardTracking(False)
        self.noiseAmpSpinBox.setDecimals(5)
        self.noiseAmpSpinBox.setSingleStep(0.01)
        self.noiseAmpSpinBox.setRange(0, 2**16)
        self.noiseAmpSpinBox.setValue(self.noiseAmplitude)
        self.noiseAmpSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        controlLayout_row2.addWidget(self.noiseAmpSpinBox, 0, 6, rowSpan, colSpan)

        #
        # row 2
        # controlLayout_row2 = QtWidgets.QHBoxLayout()

        aName = "Amplitude Step"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row2.addWidget(aLabel, 1, 0, rowSpan, colSpan)
        self.amplitudeStepSpinBox = QtWidgets.QDoubleSpinBox()
        self.amplitudeStepSpinBox.setKeyboardTracking(False)
        self.amplitudeStepSpinBox.setDecimals(5)
        self.amplitudeStepSpinBox.setSingleStep(0.01)
        self.amplitudeStepSpinBox.setRange(0, 2**16)
        self.amplitudeStepSpinBox.setValue(self.amplitudeStep)
        self.amplitudeStepSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        controlLayout_row2.addWidget(self.amplitudeStepSpinBox, 1, 1, rowSpan, colSpan)

        aName = "Frequency Step"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row2.addWidget(aLabel, 1, 3, rowSpan, colSpan)
        self.frequencyStepSpinBox = QtWidgets.QDoubleSpinBox()
        self.frequencyStepSpinBox.setKeyboardTracking(False)
        self.frequencyStepSpinBox.setSingleStep(0.1)
        self.frequencyStepSpinBox.setRange(0, 2**16)
        self.frequencyStepSpinBox.setValue(self.frequencyStep)
        self.frequencyStepSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        controlLayout_row2.addWidget(self.frequencyStepSpinBox, 1, 4, rowSpan, colSpan)

        # first row in grid has freq rms

        aName = "Noise Step"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row2.addWidget(aLabel, 1, 5, rowSpan, colSpan)
        self.noiseStepSpinBox = QtWidgets.QDoubleSpinBox()
        self.noiseStepSpinBox.setKeyboardTracking(False)
        self.noiseStepSpinBox.setDecimals(5)
        self.noiseStepSpinBox.setSingleStep(0.01)
        self.noiseStepSpinBox.setRange(0, 2**16)
        self.noiseStepSpinBox.setValue(self.frequencyStep)
        self.noiseStepSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        controlLayout_row2.addWidget(self.noiseStepSpinBox, 1, 6, rowSpan, colSpan)

        #
        vLayout.addLayout(controlLayout_row2)  # add mpl canvas

        controlLayout_row3 = QtWidgets.QHBoxLayout()

        checkboxName = "Rectify"
        self.rectifyCheckBox = QtWidgets.QCheckBox(checkboxName)
        self.rectifyCheckBox.setChecked(self.doRectify)
        self.rectifyCheckBox.stateChanged.connect(
            partial(self.on_checkbox_clicked, checkboxName)
        )
        controlLayout_row3.addWidget(self.rectifyCheckBox)

        aName = "Samples Per Second"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row3.addWidget(aLabel)
        self.fsSpinBox = QtWidgets.QSpinBox()
        self.fsSpinBox.setKeyboardTracking(False)
        self.fsSpinBox.setRange(1, 100000)  # TODO: Fix hard coding of 100000
        self.fsSpinBox.setValue(self._fs)
        self.fsSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        controlLayout_row3.addWidget(self.fsSpinBox)

        aName = "Scale"
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row3.addWidget(aLabel)
        self.scaleDropdown = QtWidgets.QComboBox()
        scales = [0.001, 0.01, 0.1, 1, 10, 100, 1000]
        for scale in scales:
            scaleStr = str(scale)
            self.scaleDropdown.addItem(scaleStr)
        startIndex = 3
        self.scaleDropdown.setCurrentIndex(startIndex)
        self.scaleDropdown.currentTextChanged.connect(self.on_scale)
        controlLayout_row3.addWidget(self.scaleDropdown)

        #
        vLayout.addLayout(controlLayout_row3)  # add mpl canvas

        vSplitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        vLayout.addWidget(vSplitter)

        # plt.style.use('dark_background')
        if self.darkTheme:
            plt.style.use("dark_background")
        else:
            plt.rcParams.update(plt.rcParamsDefault)

        self.fig = mpl.figure.Figure(constrained_layout=True)
        self.static_canvas = backend_qt5agg.FigureCanvas(self.fig)
        self.static_canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.static_canvas.setFocus()

        # can do self.mplToolbar.hide()
        self.mplToolbar = mpl.backends.backend_qt5agg.NavigationToolbar2QT(
            self.static_canvas, self.static_canvas
        )

        self._updateNumSweeps(self.numSweeps)
        # self.rawAxes = self.static_canvas.figure.add_subplot(self.numSweeps,1,1)
        # self.plotLine, = self.rawAxes[0].plot([], [], '-w', linewidth=1)

        vSplitter.addWidget(self.static_canvas)  # add mpl canvas
        vSplitter.addWidget(self.mplToolbar)  # add mpl canvas

        #
        # finalize
        # self.mainWidget = QtWidgets.QWidget()
        # if qdarkstyle is not None:
        #     self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
        # else:
        #     self.setStyleSheet("")

        # set the layout of the main window
        # self.setLayout(vLayout)
        self.getVBoxLayout().addLayout(vLayout)

    def _updateNumSweeps(self, numSweeps):
        """
        Remove and add all Figure axes
        """
        self.numSweeps = numSweeps

        self.static_canvas.figure.clear()

        self.plotLine = [None] * numSweeps
        self.rawAxes = [None] * numSweeps

        for i in range(numSweeps):
            if i == 0:
                self.rawAxes[i] = self.static_canvas.figure.add_subplot(
                    numSweeps, 1, i + 1
                )  # +1 because subplot index is 1 based
            else:
                self.rawAxes[i] = self.static_canvas.figure.add_subplot(
                    numSweeps, 1, i + 1, sharex=self.rawAxes[0]
                )  # +1 because subplot index is 1 based
            (self.plotLine[i],) = self.rawAxes[i].plot([], [], "-w", linewidth=0.5)

            self.rawAxes[i].spines["right"].set_visible(False)
            self.rawAxes[i].spines["top"].set_visible(False)

            lastSweep = i == (numSweeps - 1)
            if not lastSweep:
                self.rawAxes[i].spines["bottom"].set_visible(False)
                self.rawAxes[i].tick_params(axis="x", labelbottom=False)  # no labels

    def replot(self):
        logger.info(f"t:{len(self._t)}, data:{len(self._data)}")

        yMin = 1e9
        yMax = -1e9

        for i in range(self.numSweeps):
            self.plotLine[i].set_xdata(self._t)
            self.plotLine[i].set_ydata(self._data[i])
            #
            self.rawAxes[i].relim()
            self.rawAxes[i].autoscale_view(True, True, True)

            thisMin = np.nanmin(self._data[i])
            thisMax = np.nanmax(self._data[i])
            if thisMin < yMin:
                yMin = thisMin
            if thisMax > yMax:
                yMax = thisMax

        for i in range(self.numSweeps):
            self.rawAxes[i].set_ylim([yMin, yMax])

        #
        self.static_canvas.draw()

    '''
    def _getTime(self):
        """Get time in seconds."""
        n = int(durSec * fs) # total number of samples
        t = np.linspace(0, self.durSeconds, n, endpoint=True)
        return t
    '''

    def saveAs(self):
        """Save a stimulus waveform array as an ATF 1.0 file.

        If use specifies .atf then save as .atf
        If user specifies .csv then save as .csv
        """
        fileName = self.getFileName()
        options = QtWidgets.QFileDialog.Options()
        savePath = os.path.join(self.savePath, fileName)
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save .atf file",
            savePath,
            "Atf Files (*.atf);;CSV Files (*.csv)",
            options=options,
        )
        if not fileName:
            return

        self.savePath = os.path.split(fileName)[0]

        if fileName.endswith(".atf"):
            numSweeps = self.numSweeps
            out = self.getAtfHeader(numChannels=numSweeps)
            data = self._data  # list of sweeps
            fs = self._fs

            # if numChannels == 2:
            #    myNoise = np.random.normal(scale=np.sqrt(5), size=data.shape)

            # TODO: getAtfHeader needs to append trailing eol
            #         Then here we don't pre-pend with \n but append each line
            eol = "\n"
            pntsPerSweep = len(self._data[0])
            for i in range(pntsPerSweep):
                for sweepNumber in range(self.numSweeps):
                    # sweepData = self._data[sweepNumber]
                    val = self._data[sweepNumber][i]
                    # TODO: Convert to f'' format
                    if sweepNumber == 0:
                        # time and sweep 0
                        out += "%.05f\t%.05f" % (i / fs, val)
                    else:
                        # append value for next sweep
                        out += "\t%.05f" % (val)
                #
                out += eol
            #
            with open(fileName, "w") as f:
                f.write(out)

        elif fileName.endswith(".csv"):
            df = pd.DataFrame(columns=["sec", "pA"])
            df["sec"] = self._t
            df["pA"] = self._data
            df.to_csv(fileName, index=False)
        #
        logger.info(f'Saved: "{fileName}"')

    def getFileName(self):
        stimType = self.stimType
        numSweeps = self.numSweeps
        durSeconds = self.durSeconds  # sweep duration
        amplitude = self.amplitude
        frequency = self.frequency
        noiseAmplitude = self.noiseAmplitude
        noiseStep = self.noiseStep
        """
        _s : number of sweeps
        _sd : sweep duration (seconds)
        _a : amplitude
        _f : frequency
        _g : start noise amplitude
        _ns : noise step
        """

        """
        filename = f'{stimType}_s{numSweeps}_sd{durSeconds}_a{amplitude}_f{frequency}_g{noiseAmplitude}'
        if numSweeps > 1:
            filename += f'_ns{noiseStep}'
        filename += '.atf'
        return filename
        """

        filename = "sanpy_" + datetime.today().strftime("%Y%m%d")
        filename += "_"

        saveStimIndex = self.saveStimIndex
        filename += f"{saveStimIndex:04}"

        filename += ".atf"

        # increment for next save
        self.saveStimIndex += 1

        # update interface
        self.saveIndexSpinBox.setValue(self.saveStimIndex)

        return filename

    def buildFromDict(self, d):
        """
        build from dict constructed from saved abt file using readParams()

        TODO: Does not work because we do not update Qt interface with values from dict
        """
        myVars = vars(self)
        print(myVars)
        for k, v in d.items():
            print(k, v, type(v))
            myVars[k] = v

        self.replot()


def run():
    app = QtWidgets.QApplication(sys.argv)

    sg = stimGen()
    sg.show()

    sys.exit(app.exec_())


def testDict():
    folderPath = "/home/cudmore/Sites/SanPy"
    df = readFolderParams(folderPath)

    sys.exit(1)

    path = "/home/cudmore/Sites/SanPy/sanpy_20211206_0000.atf"
    path = "/home/cudmore/Sites/SanPy/sanpy_20211206_0001.atf"

    d = readFileParams(path)
    for k, v in d.items():
        print(k, v)

    """
    app = QtWidgets.QApplication(sys.argv)
    sg = stimGen()
    sg.buildFromDict(d)

    sg.show()

    sys.exit(app.exec_())
    """


if __name__ == "__main__":
    run()

    # testDict()
