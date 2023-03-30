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

import os, sys, time
from functools import partial

from datetime import datetime

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtWidgets, QtGui

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends import backend_qt5agg

# import qdarkstyle

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
        if not file.endswith('.atf'):
            continue
        filePath = os.path.join(folderPath, file)
        d = readFileParams(filePath)
        dList.append(d)
    #
    df = pd.DataFrame(dList)
    outFile = os.path.join(folderPath, 'stimGen_db.csv')
    print('saving:', outFile)
    df.to_csv(outFile)

    return df

def readFileParams(path):
    """
    Read stimGen params from one atf file

    Args:
        path (Str): Path to atf file
    """
    retDict = {}
    with open(path, 'r') as f:
        while True:
            #lines = f.readlines()
            line = f.readline()
            if not line:
                break  # EOF
            if line.startswith('"Comment='):
                retDict = readCommentParams(line)
                # looks like
                # "Comment=version=0.2;numSweeps=5;sweepDurSeconds=30.0;stimType=Sin;stimStartSeconds=5.0;durSeconds=20.0;yStimOffset=0.0;amplitude=0.002;frequency=1.0;noiseAmplitude=0.0;amplitudeStep=0.0;frequencyStep=0.0;noiseStep=0.0;doRectify=False;"

                '''
                line = line.replace('"Comment=','')
                line = line[0:-2]  # remove trailing "
                #print(line)
                for param in line.split(';'):
                    kv = param.split('=')
                    #print(kv)
                    if len(kv) != 2:
                        continue
                    k = kv[0]
                    v = kv[1]
                    #print(k, v)

                    if k == 'stimType':
                        pass
                    elif k == 'doRectify':
                        v = bool(v)
                    elif k == 'numSweeps':
                        v = int(v)
                    else:
                        v = float(v)
                    #
                    retDict[k] = v
                '''
                #
                break
    #
    return retDict

def readCommentParams(commentStr):
    """
    Read stim params from comment string saved in atf
    """
    retDict = {}
    commentStr = commentStr.replace('"Comment=','')
    commentStr = commentStr[0:-1]  # remove trailing "
    #print(line)
    for param in commentStr.split(';'):
        kv = param.split('=')
        #print(kv)
        if len(kv) != 2:
            continue
        k = kv[0]
        v = kv[1]
        #print(k, v)

        strKeys = ['stimType']
        intKeys = ['saveStimIndex', 'stimType', 'preSweeps', 'numSweeps', 'postSweeps']

        if v in ['True', 'False']:
            v = bool(v)
        elif k in strKeys:
            pass
        elif k in intKeys:
            v = int(v)
        else:
            try:
                v = float(v)
            except (ValueError) as e:
                logger.error(f'ERROR: ValueError for key:{k} value:"{v}" param="{param}"')
        #
        retDict[k] = v
    #

    if retDict['version'] == 0.2:
        retDict = convertVersionToNew(retDict)

    return retDict

def convertVersionToNew(d):
    d['sweepDur_sec'] = d['durSeconds']
    d['stimFreq'] = d['frequency']
    d['stimFreqStep'] = d['frequencyStep']
    d['stimAmp'] = d['amplitude']
    d['stimAmpStep'] = d['amplitudeStep']
    d['stimNoiseAmp'] = d['noiseAmplitude']
    d['stimNoiseStep'] = d['noiseStep']
    d['stimStart_sec'] = d['stimStartSeconds']
    d['stimDur_sec'] = d['durSeconds']
    d['rectify'] = d['doRectify']
    #
    return d

def buildStimDict(d, path=None):
    """
    Build a list of dict to describe each stimulus

    Args:
        d (dict): returned from readCommentParams()

    version 0.2
    numSweeps 5
    sweepDurSeconds 30.0
    stimType Sin
    stimStartSeconds 5.0
    durSeconds 20.0
    yStimOffset 0.0
    amplitude 0.001
    frequency 1.0
    noiseAmplitude 0.0
    amplitudeStep 0.0
    frequencyStep 0.0
    noiseStep 0.002
    doRectify True
    """
    def _defaultDict():
        return {
            'file': '',
            'index': '',
            'type': '',
            'start(s)': '',
            'dur(s)': '',
            'freq(Hz)': '',
            'amp': '',
            'noise amp': '',
        }
    #
    if path is None:
        fileName = ''
    else:
        fileName = os.path.split(path)[1]

    retList = []
    masterIdx = 0
    version = d['version']
    if version == 0.2:
        d = convertVersionToNew(d)
    #
    if 'preSweeps' in d.keys():
        preSweeps = d['preSweeps']
        for pre in range(preSweeps):
            oneDict = _defaultDict()
            oneDict['index'] = masterIdx
            oneDict['type'] = 'pre'
            retList.append(oneDict)
            masterIdx += 1
    #
    numSweeps = d['numSweeps']
    currentFreq = d['stimFreq']
    stimFreqStep = d['stimFreqStep']
    currentAmp = d['stimAmp']
    stimAmpStep = d['stimAmpStep']
    currentNoise = d['stimNoiseAmp']
    stimNoiseStep = d['stimNoiseStep']
    for sweep in range(numSweeps):
        oneDict = _defaultDict()
        oneDict['file'] = fileName
        oneDict['index'] = masterIdx
        oneDict['type'] = d['stimType']
        oneDict['start(s)'] = d['stimStart_sec']
        oneDict['dur(s)'] = d['stimDur_sec']
        oneDict['freq(Hz)'] = currentFreq
        oneDict['amp'] = currentAmp
        oneDict['noise amp'] = currentNoise
        retList.append(oneDict)
        #
        currentFreq += stimFreqStep
        currentAmp += stimAmpStep
        currentNoise += stimNoiseStep
        masterIdx += 1
    #
    if 'postSweeps' in d.keys():
        postSweeps = d['postSweeps']
        
        # TODO: fix this bug in interface (I think?)
        #logger.error(f'todo: fix postSweeps')
        #if postSweeps==0:
        #    postSweeps = 1
        
        for post in range(postSweeps):
            oneDict = _defaultDict()
            oneDict['index'] = masterIdx
            oneDict['type'] = 'post'
            retList.append(oneDict)
            masterIdx += 1

    #
    return retList

def mySpinBox(
            label:str,
            stat:str,
            value,  # (int,float)
            minVal:float=0,
            maxVal:float=1e9,
            decimals:int=3,
            callback=None
    ):
    """
    infer type from value
    """
    hBoxLayout = QtWidgets.QHBoxLayout()

    aLabel = QtWidgets.QLabel(label)
    hBoxLayout.addWidget(aLabel)

    # todo: infer type from value
    if isinstance(value, int):
        spinBox = QtWidgets.QSpinBox()
    elif isinstance(value, float):
        spinBox = QtWidgets.QDoubleSpinBox()
        spinBox.setDecimals(decimals)
    else:
        print('mySpinBox error')

    spinBox.setKeyboardTracking(False)
    spinBox.setObjectName(stat)  # correspond to stat to set in callback
    spinBox.setRange(minVal, maxVal)
    '''
    if type == 'float':
        spinBox.setDecimals(decimals)
    '''
    spinBox.setValue(value)
    spinBox.valueChanged.connect(callback)

    hBoxLayout.addWidget(spinBox)

    return hBoxLayout

class myDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self, statName, value, minVal=0, maxVal=1e9, decimals=3, callback=None):
        """
        d (dict): Dict of statName (keys) and their values
        statName (str): corresponds to d[statName]
        """
        super(myDoubleSpinBox, self).__init__()

        spinBox = QtWidgets.QDoubleSpinBox()
        spinBox.setKeyboardTracking(False)
        spinBox.setObjectName(statName)  # correspond to stat to set in callback
        spinBox.setRange(minVal, maxVal)
        spinBox.setDecimals(decimals)
        spinBox.setValue(value)
        spinBox.valueChanged.connect(callback)

    '''
    def on_spin_box2(self):
        spinbox = self.sender()
        statName = spinbox.objectName()
        value = spinbox.value()

        self._d[statName] = value
    '''

class stimGen(sanpyPlugin):
    myHumanName = 'Stim Gen'

    def __init__(self, myAnalysisDir=None, **kwargs):
        """
        Args:
            ba (bAnalysis): Not required
        """
        super(stimGen, self).__init__(**kwargs)

        self._lastTime = time.time()

        self.saveStimIndex = 0

        '''
        self.version = 0.2  # v0.2 on 20211202

        self._fs = 10000
        # sampling frequency in (samples per second)
        '''

        self.stimTypes = [
                        'Sin',
                        'Chirp',
                        'Noise',
                        'Epsp train',
                        #'Stochastic HH',
                        'Integrate and Fire'
                        ]
        # TODO: add (save index, ...)
        '''
        self.stimType = 'Sin'
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
        '''

        self.savePath = ''  # remember last save folder

        # TODO: all params need to be in dictionary
        # when user clicks on interface (spinbox), we need to update this dict
        self.paramDict = self.defaultParams()

        self._data = [None] * self.numSweeps  # list of sweeps
        self._t = []

        self.buildUI()

        self.updateStim()

    @property
    def numSweeps(self):
        preSweeps = self.paramDict['preSweeps']
        numSweeps = self.paramDict['numSweeps']
        postSweeps = self.paramDict['postSweeps']
        return preSweeps + numSweeps + postSweeps

    def defaultParams(self):
        paramDict = {
            'version': 0.3,
            #'saveStimIndex': 0,
            'stimType': 'Sin',  # str of stim types
            'fs': 10000,  # int, samples per second
            'preSweeps': 1,  # int
            'numSweeps': 5,  # int
            'postSweeps': 0,  # int
            'sweepDur_sec': 30.0,
            'stimStart_sec': 5.0,
            'stimDur_sec': 20.0,
            'yOffset': 0.0,
            # First sweep parameters
            'stimFreq': 1.0,
            'stimAmp': 0.002,
            'stimNoiseAmp': 0.0,
            # step parameters
            'stimFreqStep': 0.0,
            'stimAmpStep': 0.0,
            'stimNoiseStep': 0.0,
            #
            'rectify': False,
            'scale': 1,
        }
        return paramDict

    def getComment(self):
        comment = '' # '"Comment='

        for k,v in self.paramDict.items():
            comment +=  f'{k}={v};'

        '''
        comment +=  f'version={self.version};'
        comment +=  f'numSweeps={self.numSweeps};'
        comment +=  f'sweepDurSeconds={self.sweepDurSeconds};'
        comment +=  f'stimType={self.stimType};'
        comment +=  f'stimStartSeconds={self.stimStartSeconds};'
        comment +=  f'durSeconds={self.durSeconds};'
        comment +=  f'yStimOffset={self.yStimOffset};'
        comment +=  f'amplitude={self.amplitude};'
        comment +=  f'frequency={self.frequency};'
        comment +=  f'noiseAmplitude={self.noiseAmplitude};'
        comment +=  f'amplitudeStep={self.amplitudeStep};'
        comment +=  f'frequencyStep={self.frequencyStep};'
        comment +=  f'noiseStep={self.noiseStep};'
        comment +=  f'doRectify={self.doRectify};'
        '''
        #
        #comment += '"'
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

        myUnits = 'pA'
        #myComment = 'fill in with stim params'

        numDataColumns = numChannels + 1  # time + number of channels
        eol = '\n'
        tab = '\t'
        ATF_HEADER = "ATF    1.0" + eol
        ATF_HEADER += f'8\t{numDataColumns}' + eol

        ATF_HEADER += '"AcquisitionMode=Episodic Stimulation"' + eol

        myComment = self.getComment()
        ATF_HEADER += f'"Comment={myComment}"' + eol

        ATF_HEADER += '"YTop=20000"' + eol
        ATF_HEADER += '"YBottom=-20000"' + eol
        ATF_HEADER += '"SyncTimeUnits=100"' + eol

        # for a 200 ms sweep, looks like this
        # "SweepStartTimesMS=21.000,221.000,421.000,621.000,821.000,1021.000,1221.000,1421.000,1621.000,1821.000"
        #durMs = self.durSeconds *1000
        durMs = self.getParam('sweepDur_sec') * 1000  # new 20211202
        numSweeps = self.numSweeps  # total number including pre/stim/post
        sweepRange = range(numSweeps)
        SweepStartTimesMS = '"SweepStartTimesMS='
        preRollMs = 21
        for sweepIdx, sweep in enumerate(sweepRange):
            currStartTime = preRollMs + (sweepIdx * durMs)
            SweepStartTimesMS += f'{round(float(currStartTime),3)}' + ','
        # remove last comma
        SweepStartTimesMS = SweepStartTimesMS[0:-1]
        SweepStartTimesMS += '"'
        ATF_HEADER += SweepStartTimesMS + eol

        ATF_HEADER += '"SignalsExported=IN 0"' + eol

        # signals looks like this
        # "Signals="    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"    "IN 0"
        Signals = '"Signals="' + '\t'
        for sweepIdx, sweep in enumerate(sweepRange):
            Signals += '"IN 0"' + '\t'
        # remove last tab
        Signals = Signals[0:-1]
        ATF_HEADER += Signals + eol

        ATF_HEADER += f'"Time (s)"' + tab
        traceStr = ''
        for channel in range(numChannels):
            traceStr += f'"Trace #{channel+1} ({myUnits})"' + tab  # not sure if trailing tab is ok???
        # remove last tab
        traceStr = traceStr[0:-1]
        ATF_HEADER += traceStr + eol

        print('=== ATF_HEADER:')
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

    '''
    @property
    def data(self):
        return self._data
    '''

    @property
    def t(self):
        return self._t

    '''
    @property
    def fs(self):
        return self._fs
    '''

    def old_makeStim(self):
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
            print(f'  makeStim() {type} sweep:{sweepNum} durSec:{durSec} amp:{currAmp} freq:{currFreq} noiseAmp:{currNoiseAmp}')
            self._data[sweepNum] = sanpy.atfStim.makeStim(type, sweepDurSec=sweepDurSeconds,
                            startStimSec=stimStartSeconds, durSec=durSec,
                            yStimOffset=yStimOffset, amp=currAmp,
                            freq=currFreq, fs=fs, noiseAmp=currNoiseAmp, rectify=doRectify,
                            autoPad=autoPad, autoSave=False)
            if self._data[sweepNum] is None:
                print(f'makeStim() error making {type} at sweep number {sweepNum}')
            #
            # scale
            self._data[sweepNum] *= self.scale

            print('  self._data[sweepNum].dtype:', self._data[sweepNum].dtype)

        self._t = np.arange(len(self._data[0])) / fs  # just using first sweep

    def setParam(self, name, val):
        """
        Get a stimulus parameter
        """
        self.paramDict[name] = val

    def getParam(self, name):
        """
        Get a stimulus parameter
        """
        return self.paramDict[name]

    def makeStim2(self):
        fs = self.getParam('fs')
        stimType = self.getParam('stimType')
        #numSweeps = self.getParam('numSweeps')
        sweepDur_sec = self.getParam('sweepDur_sec')
        stimStart_sec = self.getParam('stimStart_sec')
        stimDur_sec = self.getParam('stimDur_sec')
        yOffset = self.getParam('yOffset')
        stimFreq = self.getParam('stimFreq')
        stimAmp = self.getParam('stimAmp')
        stimNoiseAmp = self.getParam('stimNoiseAmp')
        stimFreqStep = self.getParam('stimFreqStep')
        stimAmpStep = self.getParam('stimAmpStep')
        stimNoiseStep = self.getParam('stimNoiseStep')
        rectify = self.getParam('rectify')
        scale = self.getParam('scale')

        autoPad = False

        preSweeps = self.paramDict['preSweeps']
        numStimSweeps = self.paramDict['numSweeps']
        postSweeps = self.paramDict['postSweeps']

        self._data = [None] * self.numSweeps  # total number including pre/num/post

        Xs = np.arange(fs*sweepDur_sec) / fs  # x/time axis, we should always be able to create this from (dur, fs)
        blankSweepData = np.zeros(shape=Xs.shape)

        for sweepNum in range(preSweeps):
            self._data[sweepNum] = blankSweepData

        for sweepNum in range(numStimSweeps):
            realSweepNum = preSweeps + sweepNum
            currAmp = stimAmp + (sweepNum * stimAmpStep)
            currFreq = stimFreq + (sweepNum * stimFreqStep)
            currNoiseAmp = stimNoiseAmp + (sweepNum * stimNoiseStep)
            autoPad = False  # TODO: ALWAYS FALSE, my pre/post sweeps don't use this
            print(f'  makeStim() {stimType} sweep:{sweepNum} durSec:{stimDur_sec} amp:{currAmp} freq:{currFreq} noiseAmp:{currNoiseAmp}')
            self._data[realSweepNum] = sanpy.atfStim.makeStim(stimType, sweepDurSec=sweepDur_sec,
                            startStimSec=stimStart_sec, durSec=stimDur_sec,
                            yStimOffset=yOffset, amp=currAmp,
                            freq=currFreq, fs=fs, noiseAmp=currNoiseAmp, rectify=rectify,
                            autoPad=autoPad, autoSave=False)
            if self._data[realSweepNum] is None:
                print(f'makeStim() error making {type} at sweep number {sweepNum}')
            #
            # scale
            self._data[realSweepNum] *= scale

            print(f'  {realSweepNum} self._data[realSweepNum].dtype:{self._data[realSweepNum].dtype}')

        for sweepNum in range(postSweeps):
            realSweepNum = preSweeps + numStimSweeps + sweepNum
            self._data[realSweepNum] = blankSweepData

        self._t = np.arange(len(self._data[0])) / fs  # just using first sweep

    '''
    def plotStim(self):
        logger.info(f'_t:{self._t.shape}')
        logger.info(f'_data:{self._data.shape}')
        plt.plot(self._t, self._data)
    '''

    '''
    def saveStim(Self):
        sanpy.atfStim.saveAtf(self.data, fileName="output.atf", fs=10000)
    '''

    def old_grabParams(self):
        """
        Grab all interface parameters in member variables
        """

        pass
        '''
        #self.sweepDurSeconds = self.sweepDurationSpinBox.value()  # new 20211202
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
        '''

        '''
        rmsMult = 1/np.sqrt(2)
        sinRms = self.amplitude * rmsMult
        sinRms = round(sinRms,2)
        aName = f'RMS:{sinRms}'
        self.sinRms.setText(aName)
        '''

    def updateStim(self):
        #self._grabParams()
        self.makeStim2()
        self.replot()

    def on_spin_box2(self):
        '''
        thisTime = time.time()
        timeDiff = thisTime - self._lastTime
        print('thisTime:', thisTime, '_lastTime:', self._lastTime, 'timeDiff:', timeDiff)
        if timeDiff < 5:
            return
        self._lastTime = thisTime
        '''

        spinbox = self.sender()
        spinbox.setEnabled(False)
        print('on_spin_box2()', spinbox.objectName(), spinbox.value())
        keyStr = spinbox.objectName()
        val = spinbox.value()
        self.setParam(keyStr, val)
        #

        # todo: only call this when changing number of sweeps
        self._updateNumSweeps()

        self.updateStim()

        spinbox.setEnabled(True)

    def on_spin_box(self, name):
        logger.info(name)
        if name == 'Save Index':
            saveStimIndex = self.saveIndexSpinBox.value()
            self.saveStimIndex = saveStimIndex
        '''
        elif name == 'Number Of Sweeps':
            numSweeps = self.numSweepsSpinBox.value()
            self.setParam('numSweeps', numSweeps)
            self._updateNumSweeps()
        else:
            logger.warning(f'"{name}" not understood')
        #
        self.updateStim()
        '''

    def on_stim_type(self, type):
        logger.info(type)
        #self.stimType = type
        self.setParam('stimType', type)
        self.updateStim()

    def on_scale(self, scale):
        logger.info(type)
        #self.scale = float(scale)
        self.setParam('scale', float(scale))
        self.updateStim()

    def on_button_click(self, name):
        logger.info(name)
        if name == 'Save As...':
            # TODO: srt a feeback red as we save, set to green when done
            # self.saveAsButton
            self.saveAs()
        else:
            logger.info(f'name "{name}" not understood.')

    def on_checkbox_clicked(self, name):
        if name == 'Rectify':
            val = self.rectifyCheckBox.isChecked()
            self.setParam('rectify', val)
        self.updateStim()

    def buildUI(self):
        # main layout
        vLayout = QtWidgets.QVBoxLayout()
        controlLayout = QtWidgets.QHBoxLayout()

        aName = 'Save As...'
        self.saveAsButton = QtWidgets.QPushButton(aName)
        self.saveAsButton.clicked.connect(partial(self.on_button_click,aName))
        controlLayout.addWidget(self.saveAsButton)

        '''
        statStr = 'saveStimIndex'
        self.saveIndexSpinBox = mySpinBox(
            label='Save Index',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout.addLayout(self.saveIndexSpinBox)
        '''

        aName = 'Save Index'
        aLabel = QtWidgets.QLabel(aName)
        controlLayout.addWidget(aLabel)
        self.saveIndexSpinBox = QtWidgets.QSpinBox()
        self.saveIndexSpinBox.setKeyboardTracking(False)
        self.saveIndexSpinBox.setObjectName(aName)
        self.saveIndexSpinBox.setRange(0, 9999)
        self.saveIndexSpinBox.setValue(self.saveStimIndex)
        self.saveIndexSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        #self.saveIndexSpinBox.valueChanged.connect(self.on_spin_box2)
        controlLayout.addWidget(self.saveIndexSpinBox)

        aName = 'Stim Type'
        aLabel = QtWidgets.QLabel(aName)
        controlLayout.addWidget(aLabel)
        self.stimTypeDropdown = QtWidgets.QComboBox()
        for type in self.stimTypes:
            self.stimTypeDropdown.addItem(type)
        self.stimTypeDropdown.currentTextChanged.connect(self.on_stim_type)
        controlLayout.addWidget(self.stimTypeDropdown)

        statStr = 'sweepDur_sec'
        aSpinBox = mySpinBox(
            label='Sweep Duration(s)',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout.addLayout(aSpinBox)

        vLayout.addLayout(controlLayout) # add mpl canvas

        # row 1.25
        controlLayout_row1_2 = QtWidgets.QHBoxLayout()

        statStr = 'preSweeps'
        aSpinBox = mySpinBox(
            label='Pre Sweeps',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row1_2.addLayout(aSpinBox)

        statStr = 'numSweeps'
        aSpinBox = mySpinBox(
            label= 'Stim Sweeps',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row1_2.addLayout(aSpinBox)

        statStr = 'postSweeps'
        aSpinBox = mySpinBox(
            label= 'Post Sweeps',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row1_2.addLayout(aSpinBox)

        vLayout.addLayout(controlLayout_row1_2) # add mpl canvas

        # row 1.5
        controlLayout_row1_5 = QtWidgets.QHBoxLayout()

        statStr = 'stimStart_sec'
        aSpinBox = mySpinBox(
            label= 'Stim Start(s)',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row1_5.addLayout(aSpinBox)

        statStr = 'stimDur_sec'
        aSpinBox = mySpinBox(
            label= 'Stim Dur(s)',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row1_5.addLayout(aSpinBox)

        statStr = 'yOffset'
        aSpinBox = mySpinBox(
            label= 'Stim Offset(y)',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row1_5.addLayout(aSpinBox)

        vLayout.addLayout(controlLayout_row1_5) # add mpl canvas

        # 2nd row
        controlLayout_row2 = QtWidgets.QHBoxLayout()
        '''
        controlLayout_row2 = QtWidgets.QGridLayout()
        rowSpan = 1
        colSpan = 1
        row = 0
        col = 0
        '''

        statStr = 'stimAmp'
        aSpinBox = mySpinBox(
            label= 'Amplitude',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row2.addLayout(aSpinBox)

        # rms of sin (amp and freq)
        '''
        rmsMult = 1/np.sqrt(2)
        sinRms = self.amplitude * rmsMult
        sinRms = round(sinRms,2)
        aName = f'RMS:{sinRms}'
        self.sinRms = QtWidgets.QLabel(aName)
        controlLayout_row2.addWidget(self.sinRms, 0, 2, rowSpan, colSpan)
        '''

        statStr = 'stimFreq'
        aSpinBox = mySpinBox(
            label= 'Frequency (Hz)',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row2.addLayout(aSpinBox)

        statStr = 'stimNoiseAmp'
        aSpinBox = mySpinBox(
            label= 'Noise Amplitude',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row2.addLayout(aSpinBox)

        vLayout.addLayout(controlLayout_row2) # add mpl canvas

        #
        # row 2
        #controlLayout_row2 = QtWidgets.QHBoxLayout()

        controlLayout_row3 = QtWidgets.QHBoxLayout()

        statStr = 'stimAmpStep'
        aSpinBox = mySpinBox(
            label= 'Amplitude Step',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row3.addLayout(aSpinBox)

        statStr = 'stimFreqStep'
        aSpinBox = mySpinBox(
            label= 'Frequency Step',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row3.addLayout(aSpinBox)

        statStr = 'stimNoiseStep'
        aSpinBox = mySpinBox(
            label= 'Noise Step',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row3.addLayout(aSpinBox)

        #
        vLayout.addLayout(controlLayout_row3) # add mpl canvas

        controlLayout_row4 = QtWidgets.QHBoxLayout()

        aValue = self.getParam('rectify')
        checkboxName = 'Rectify'
        self.rectifyCheckBox = QtWidgets.QCheckBox(checkboxName)
        self.rectifyCheckBox.setChecked(aValue)
        self.rectifyCheckBox.stateChanged.connect(partial(self.on_checkbox_clicked, checkboxName))
        controlLayout_row4.addWidget(self.rectifyCheckBox)

        statStr = 'fs'
        aSpinBox = mySpinBox(
            label= 'Samples Per Second',
            stat=statStr,
            value=self.getParam(statStr),
            callback=self.on_spin_box2)
        controlLayout_row4.addLayout(aSpinBox)

        '''
        aValue = self.getParam('fs')
        aName = 'Samples Per Second'
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row4.addWidget(aLabel)
        self.fsSpinBox = QtWidgets.QSpinBox()
        self.fsSpinBox.setKeyboardTracking(False)
        self.fsSpinBox.setObjectName(aName)
        self.fsSpinBox.setRange(1, 100000)  # TODO: Fix hard coding of 100000
        self.fsSpinBox.setValue(aValue)
        self.fsSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
        self.fsSpinBox.valueChanged.connect(self.on_spin_box2)
        controlLayout_row4.addWidget(self.fsSpinBox)
        '''

        #aValue = self.getParam('scale')
        aName = 'Scale'
        aLabel = QtWidgets.QLabel(aName)
        controlLayout_row4.addWidget(aLabel)
        self.scaleDropdown = QtWidgets.QComboBox()
        scales = [0.001, 0.01, 0.1, 1, 10, 100, 1000]
        for scale in scales:
            scaleStr = str(scale)
            self.scaleDropdown.addItem(scaleStr)
        startIndex = 3
        self.scaleDropdown.setCurrentIndex(startIndex)
        self.scaleDropdown.currentTextChanged.connect(self.on_scale)
        controlLayout_row4.addWidget(self.scaleDropdown)

        #
        vLayout.addLayout(controlLayout_row4) # add mpl canvas

        vSplitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        vLayout.addWidget(vSplitter)

        plt.style.use('dark_background')

        self.fig = mpl.figure.Figure(constrained_layout=True)
        self.static_canvas = backend_qt5agg.FigureCanvas(self.fig)
        self.static_canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
        self.static_canvas.setFocus()

        #can do self.mplToolbar.hide()
        self.mplToolbar = mpl.backends.backend_qt5agg.NavigationToolbar2QT(self.static_canvas, self.static_canvas)

        self._updateNumSweeps()
        #self.rawAxes = self.static_canvas.figure.add_subplot(self.numSweeps,1,1)
        #self.plotLine, = self.rawAxes[0].plot([], [], '-w', linewidth=1)

        vSplitter.addWidget(self.static_canvas) # add mpl canvas
        vSplitter.addWidget(self.mplToolbar) # add mpl canvas

        #
        # finalize
        #self.mainWidget = QtWidgets.QWidget()
        # if qdarkstyle is not None:
        #     self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
        # else:
        #     self.setStyleSheet("")

        # set the layout of the main window
        #self.setLayout(vLayout)
        self.getVBoxLayout().addLayout(vLayout)

    def _updateNumSweeps(self):
        """
        Remove and add all Figure axes
        """
        numSweeps = self.numSweeps


        self.static_canvas.figure.clear()

        self.plotLine = [None] * numSweeps
        self.rawAxes = [None] * numSweeps

        for i in range(numSweeps):
            if i == 0:
                self.rawAxes[i] = self.static_canvas.figure.add_subplot(numSweeps,1, i+1)  # +1 because subplot index is 1 based
            else:
                self.rawAxes[i] = self.static_canvas.figure.add_subplot(numSweeps,1, i+1, sharex=self.rawAxes[0])  # +1 because subplot index is 1 based
            self.plotLine[i], = self.rawAxes[i].plot([], [], '-w', linewidth=0.5)

            self.rawAxes[i].spines['right'].set_visible(False)
            self.rawAxes[i].spines['top'].set_visible(False)

            lastSweep = i == (numSweeps - 1)
            if not lastSweep:
                self.rawAxes[i].spines['bottom'].set_visible(False)
                self.rawAxes[i].tick_params(axis="x", labelbottom=False) # no labels

    def replot(self):
        logger.info(f't:{len(self._t)}, data:{len(self._data)}')

        yMin = 1e9
        yMax = -1e9

        for i in range(self.numSweeps):
            self.plotLine[i].set_xdata(self._t)
            self.plotLine[i].set_ydata(self._data[i])
            #
            self.rawAxes[i].relim()
            self.rawAxes[i].autoscale_view(True,True,True)

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
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,"Save .atf file",
                            savePath,"Atf Files (*.atf);;CSV Files (*.csv)", options=options)
        if not fileName:
            return

        self.savePath = os.path.split(fileName)[0]

        if fileName.endswith('.atf'):
            numSweeps = self.numSweeps
            out = self.getAtfHeader(numChannels=numSweeps)
            data = self._data  # list of sweeps
            fs = self.getParam('fs')  # self._fs

            #if numChannels == 2:
            #    myNoise = np.random.normal(scale=np.sqrt(5), size=data.shape)

            # TODO: getAtfHeader needs to append trailing eol
            #         Then here we don't pre-pend with \n but append each line
            eol = '\n'
            pntsPerSweep = len(self._data[0])
            for i in range(pntsPerSweep):
                for sweepNumber in range(self.numSweeps):
                    #sweepData = self._data[sweepNumber]
                    val = self._data[sweepNumber][i]
                    # TODO: Convert to f'' format
                    if sweepNumber == 0:
                        # time and sweep 0
                        #out += '%.05f\t%.05f'%(i/fs,val)
                        out += '%.04f\t%.04f'%(i/fs,val)
                    else:
                        # append value for next sweep
                        #out += '\t%.05f'%(val)
                        out += '\t%.04f'%(val)
                #
                out += eol
            #
            with open(fileName,'w') as f:
                f.write(out)

        elif fileName.endswith('.csv'):
            df = pd.DataFrame(columns=['sec', 'pA'])
            df['sec'] = self._t
            df['pA'] = self._data
            df.to_csv(fileName, index=False)
        #
        logger.info(f'Saved: "{fileName}"')

    def getFileName(self):
        '''
        stimType = self.stimType
        numSweeps = self.numSweeps
        durSeconds = self.durSeconds  # sweep duration
        amplitude = self.amplitude
        frequency = self.frequency
        noiseAmplitude = self.noiseAmplitude
        noiseStep = self.noiseStep
        '''
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

        filename = 'sanpy_' + datetime.today().strftime('%Y%m%d')
        filename += '_'

        #saveStimIndex = self.getParam('saveStimIndex')  # self.saveStimIndex
        saveStimIndex = self.saveStimIndex
        filename += f'{saveStimIndex:04}'

        filename += '.atf'

        # increment for next save
        self.saveStimIndex += 1
        #newStimIdx = saveStimIndex + 1
        #self.setParam('saveStimIndex', newStimIdx)

        # update interface
        # this is no longer a spinbox, it is an h layout
        #self.saveIndexSpinBox.itemAt(1).widget().setValue(newStimIdx)
        self.saveIndexSpinBox.setValue(self.saveStimIndex)

        return filename

    def buildFromDict(self, d):
        """
        build from dict constructed from saved abt file using readParams()

        TODO: Does not work because we do not update Qt interface with values from dict
        """
        myVars = vars(self)
        print(myVars)
        for k,v in d.items():
            print(k, v, type(v))
            myVars[k] = v

        self.replot()

def run():
    app = QtWidgets.QApplication(sys.argv)

    sg = stimGen()
    sg.show()

    sys.exit(app.exec_())

def testDict():
    folderPath = '/home/cudmore/Sites/SanPy'
    df = readFolderParams(folderPath)

    #sys.exit(1)

    path = '/home/cudmore/Sites/SanPy/sanpy_20211210_0000.atf'
    path = '/home/cudmore/Sites/SanPy/sanpy_20211211_0000.atf'
    path = '/media/cudmore/data/stoch-res/20211209/sanpy_20211209_0001.atf'
    d = readFileParams(path)
    for k,v in d.items():
        print(k,v)

    dList = buildStimDict(d, path)
    for one in dList:
        print(one)

    '''
    app = QtWidgets.QApplication(sys.argv)
    sg = stimGen()
    sg.buildFromDict(d)

    sg.show()

    sys.exit(app.exec_())
    '''

if __name__ == '__main__':
    #testDict()
    run()
