"""
Functions to get default detection parameters.

Usage:

```python
import sanpy

# dDict is a dictionary with default parameters
dDict = sanpy.bDetection.getDefaultDetection()

# set to your liking
dDict['dvdtThreshold'] = 50

# load a recording
myPath = '../data/19114001.abf'
ba = sanpy.bAnalysis(myPath)

# perform spike detection
ba.spikeDetect(dDict)

# browse results
```
"""
import os
import numbers, math, enum
import json
from pprint import pprint

from matplotlib.font_manager import json_load
#from colin.stochAnalysis import load

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class detectionTypes_(enum.Enum):
    """
    Detection type is one of (dvdt, mv).

    dvdt: Search for threshold crossings in first derivative of membrane potential.
    mv: Search for threshold crossings in membrane potential.
    """
    dvdt = 'dvdt'
    mv = 'mv'

# TODO (Cudmore) this needs to be a class so we can expand/contract based on what we find on the hard-drive
# allow user to save to detection presets
class detectionPresets_(enum.Enum):
    """
    Detection presets is one of:
    """
    # default = 1
    # saNode = 2
    # ventricular = 3
    # neuron = 4
    # subthreshold = 5
    # caSpikes = 6
    # caKymograph = 7
    default = 'Default'
    saNode = 'SA Node'
    ventricular = 'Ventricular'
    neuron = 'Neuron'
    subthreshold = 'Sub-threshold'
    caSpikes = 'Ca Spikes'
    caKymograph = 'Kymograph'

#def getDefaultDetection(cellType=None):
def getDefaultDetection(detectionPreset):
    """
    Get detection parameters including mapping from backend
    to human readable and long-format descriptions.

    Args:
        detectionPreset (enum): bDetection.detectionPresets.default

    Returns:
        dict: The default detection dictionary.
    """
    theDict = {}

    #key = 'detectionName'
    #theDict[key] = {}
    #theDict[key]['defaultValue'] = ''  # the name of the preset

    key = 'include'
    theDict[key] = {}
    theDict[key]['defaultValue'] = True
    theDict[key]['type'] = 'bool'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = ''
    theDict[key]['humanName'] = 'Include'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Include analysis for this file'

    key = 'detectionType'
    theDict[key] = {}
    theDict[key]['defaultValue'] = sanpy.bDetection.detectionTypes['dvdt'].value # ('dvdt', 'mv')
    theDict[key]['type'] = 'sanpy.bDetection.detectionTypes'
    theDict[key]['allowNone'] = False  # To do, have 2x entry points to bAnalysis detect, never set this to nan
    theDict[key]['units'] = ''
    theDict[key]['humanName'] = 'Detection Type'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Detect using derivative (dvdt) or membrane potential (mV)'

    key = 'dvdtThreshold'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 20
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = True  # To do, have 2x entry points to bAnalysis detect, never set this to nan
    theDict[key]['units'] = 'dVdt'
    theDict[key]['humanName'] = 'dV/dt Threshold'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'dV/dt threshold for a spike, will be backed up to dvdt_percentOfMax and have xxx error when this fails'

    key = 'mvThreshold'
    theDict[key] = {}
    theDict[key]['defaultValue'] = -20
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'mV'
    theDict[key]['humanName'] = 'mV Threshold'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'mV threshold for spike AND minimum spike mV when detecting with dV/dt'

    key = 'startSeconds'
    theDict[key] = {}
    theDict[key]['defaultValue'] = None
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = True
    theDict[key]['units'] = 's'
    theDict[key]['humanName'] = 'Start(s)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Start seconds of analysis'

    key = 'stopSeconds'
    theDict[key] = {}
    theDict[key]['defaultValue'] = None
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = True
    theDict[key]['units'] = 's'
    theDict[key]['humanName'] = 'Stop(s)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Stop seconds of analysis'

    key = 'cellType'
    theDict[key] = {}
    theDict[key]['defaultValue'] = ''
    theDict[key]['type'] = 'string'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = ''
    theDict[key]['humanName'] = 'Cell Type'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Cell Type'

    key = 'sex'
    theDict[key] = {}
    theDict[key]['defaultValue'] = ''
    theDict[key]['type'] = 'string'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = ''
    theDict[key]['humanName'] = 'Sex'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Sex'

    key = 'condition'
    theDict[key] = {}
    theDict[key]['defaultValue'] = ''
    theDict[key]['type'] = 'string'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = ''
    theDict[key]['humanName'] = 'Condition'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Condition'

    key = 'dvdt_percentOfMax'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 0.1
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'Percent'
    theDict[key]['humanName'] = 'dV/dt Percent of max'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'For dV/dt detection, the final TOP is when dV/dt drops to this percent from dV/dt AP peak'

    key = 'onlyPeaksAbove_mV'
    theDict[key] = {}
    theDict[key]['defaultValue'] = None
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = True
    theDict[key]['units'] = 'mV'
    theDict[key]['humanName'] = 'Accept Peaks Above (mV)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Only accept APs with peaks above this value (mV)'

    key = 'onlyPeaksBelow_mV'
    theDict[key] = {}
    theDict[key]['defaultValue'] = None
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = True
    theDict[key]['units'] = 'mV'
    theDict[key]['humanName'] = 'Accept Peaks Below (mV)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Only accept APs below this value (mV)'

    # TODO: get rid of this and replace with foot
    key = 'doBackupSpikeVm'
    theDict[key] = {}
    theDict[key]['defaultValue'] = False
    theDict[key]['type'] = 'boolean'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'Boolean'
    theDict[key]['humanName'] = 'Backup Vm Spikes'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'If true, APs detected with just mV will be backed up until Vm falls to xxx'

    key = 'refractory_ms'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 170
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'ms'
    theDict[key]['humanName'] = 'Minimum AP interval (ms)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'APs with interval (wrt previous AP) less than this will be removed'

    key = 'peakWindow_ms'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 100
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'ms'
    theDict[key]['humanName'] = 'Peak Window (ms)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Window after TOP (ms) to seach for AP peak (mV)'

    key = 'dvdtPreWindow_ms'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 10
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'ms'
    theDict[key]['humanName'] = 'dV/dt Pre Window (ms)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Window (ms) to search before each TOP for real threshold crossing'

    key = 'dvdtPostWindow_ms'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 20
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'ms'
    theDict[key]['humanName'] = 'dV/dt Post Window (ms)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Window (ms) to search after each AP peak for minimum in dv/dt'

    key = 'mdp_ms'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 250
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'ms'
    theDict[key]['humanName'] = 'Pre AP MDP window (ms)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Window (ms) before an AP to look for MDP'

    key = 'avgWindow_ms'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 5
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'ms'
    theDict[key]['humanName'] = 'MDP averaging window (ms)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Window (ms) to calculate MDP (mV) as a mean rather than mV at single point for MDP'

    key = 'lowEddRate_warning'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 8
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'EDD slope'
    theDict[key]['humanName'] = 'EDD slope warning'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Generate warning when EED slope is lower than this value.'

    key = 'halfHeights'
    theDict[key] = {}
    theDict[key]['defaultValue'] = [10, 20, 50, 80, 90]
    theDict[key]['type'] = 'list' # list of number
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = ''
    theDict[key]['humanName'] = 'AP Durations (%)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'AP Durations as percent of AP height (AP Peak (mV) - TOP (mV))'

    key = 'halfWidthWindow_ms'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 200
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'ms'
    theDict[key]['humanName'] = 'Half Width Window (ms)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Window (ms) after TOP to look for AP Durations'

    key = 'preSpikeClipWidth_ms'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 500
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'ms'
    theDict[key]['humanName'] = 'Pre AP Clip Width (ms)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'The pre duration of generated AP clips (Before AP)'

    key = 'postSpikeClipWidth_ms'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 500
    theDict[key]['type'] = 'float'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'ms'
    theDict[key]['humanName'] = 'Post AP Clip Width (ms)'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'The post duration of generated AP clips (After AP)'

    key = 'medianFilter'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 0
    theDict[key]['type'] = 'int'
    theDict[key]['allowNone'] = True # 0 is no median filter (see SavitzkyGolay_pnts)
    theDict[key]['units'] = 'points'
    theDict[key]['humanName'] = 'Median Filter Points'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Number of points in median filter, must be odd, 0 for no filter'

    key = 'SavitzkyGolay_pnts'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 5 #20211001 was 5
    theDict[key]['type'] = 'int'
    theDict[key]['allowNone'] = True # 0 is no filter
    theDict[key]['units'] = 'points'
    theDict[key]['humanName'] = 'SavitzkyGolay Points'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Number of points in SavitzkyGolay filter, must be odd, 0 for no filter'

    key = 'SavitzkyGolay_poly'
    theDict[key] = {}
    theDict[key]['defaultValue'] = 2
    theDict[key]['type'] = 'int'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = ''
    theDict[key]['humanName'] = 'SavitzkyGolay Poly Deg'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'The degree of the polynomial for Savitzky-Golay filter'

    key = 'verbose'
    theDict[key] = {}
    theDict[key]['defaultValue'] = False
    theDict[key]['type'] = 'boolean'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = 'Boolean'
    theDict[key]['humanName'] = 'Verbose'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Verbose Detection Reporting'

    if detectionPreset == bDetection.detectionPresets.default:
        # these are defaults from above
        pass
    elif detectionPreset == bDetection.detectionPresets.saNode:
        # these are defaults from above
        pass
    elif detectionPreset == bDetection.detectionPresets.ventricular:
        theDict['dvdtThreshold']['defaultValue'] = 100
        theDict['mvThreshold']['defaultValue'] = -20
        theDict['refractory_ms']['defaultValue'] = 200  # max freq of 5 Hz
        theDict['peakWindow_ms']['defaultValue'] = 100
        theDict['halfWidthWindow_ms']['defaultValue'] = 300
        theDict['preSpikeClipWidth_ms']['defaultValue'] = 200
        theDict['postSpikeClipWidth_ms']['defaultValue'] = 500
    elif detectionPreset == bDetection.detectionPresets.neuron:
        theDict['dvdtThreshold']['defaultValue'] = 100
        theDict['mvThreshold']['defaultValue'] = -40
        theDict['refractory_ms']['defaultValue'] = 4
        theDict['peakWindow_ms']['defaultValue'] = 5
        theDict['halfWidthWindow_ms']['defaultValue'] = 4
        theDict['dvdtPreWindow_ms']['defaultValue'] = 2
        theDict['dvdtPostWindow_ms']['defaultValue'] = 2
        theDict['preSpikeClipWidth_ms']['defaultValue'] = 20
        theDict['postSpikeClipWidth_ms']['defaultValue'] = 20
    elif detectionPreset == bDetection.detectionPresets.subthreshold:
        theDict['dvdtThreshold']['defaultValue'] = math.nan
        theDict['mvThreshold']['defaultValue'] = -20  # user specifies
        theDict['refractory_ms']['defaultValue'] = 100  # max freq is 10 Hz
        theDict['peakWindow_ms']['defaultValue'] = 50
        theDict['halfWidthWindow_ms']['defaultValue'] = 100
        theDict['preSpikeClipWidth_ms']['defaultValue'] = 100
        theDict['postSpikeClipWidth_ms']['defaultValue'] = 200
        theDict['onlyPeaksAbove_mV']['defaultValue'] = None
        theDict['onlyPeaksBelow_mV']['defaultValue'] = -20
        # todo: add onlyPeaksBelow_mV
    elif detectionPreset == bDetection.detectionPresets.caSpikes:
        #theDict['detectionType']['defaultValue'] = sanpy.bDetection.detectionTypes.mv # ('dvdt', 'mv')
        theDict['dvdtThreshold']['defaultValue'] = math.nan #if None then detect only using mvThreshold
        theDict['mvThreshold']['defaultValue'] = 0.5
        #theDict['refractory_ms']['defaultValue'] = 200 #170 # reject spikes with instantaneous frequency
        #theDict['halfWidthWindow_ms']['defaultValue'] = 200 #was 20
    elif detectionPreset == bDetection.detectionPresets.caKymograph:
        theDict['detectionType']['defaultValue'] = sanpy.bDetection.detectionTypes['mv'].value
        theDict['dvdtThreshold']['defaultValue'] = math.nan #if None then detect only using mvThreshold
        theDict['mvThreshold']['defaultValue'] = 1.2
        theDict['peakWindow_ms']['defaultValue'] = 700
        theDict['halfWidthWindow_ms']['defaultValue'] = 800
        theDict['refractory_ms']['defaultValue'] = 500
        theDict['doBackupSpikeVm']['defaultValue'] = False

        # theDict['SavitzkyGolay_pnts']['defaultValue'] = 5
        theDict['preSpikeClipWidth_ms']['defaultValue'] = 200
        theDict['postSpikeClipWidth_ms']['defaultValue'] = 1000

    else:
        logger.error(f'Did not understand detection type "{detectionPreset}"')

    # assign each detection param current value to it default value
    for k,v in theDict.items():
        defaultValue = theDict[k]['defaultValue']
        theDict[k]['currentValue'] = defaultValue

    return theDict.copy()

def printDocs():
    """
    Print out human readable detection parameters and convert to markdown table.

    Requires:
        pip install tabulate

    See: bAnalysisResults.printDocs()
    """
    import pandas as pd

    detectionPreset = detectionPresets_.default  # detectionPresets_ is an enum class
    d = getDefaultDetection(detectionPreset=detectionPreset)
    dictList = []
    for k,v in d.items():
        parameter = k
        oneDict = {
            'Parameter': parameter,
            'Default Value': v['defaultValue'],
            'Units': v['units'],
            'Human Readable': v['humanName'],
            'Description': v['description'],
        }
        dictList.append(oneDict)
    #
    df = pd.DataFrame(dictList)
    str = df.to_markdown()
    print(str)

class detectionPresets():
    """A list of bDetection that are saved/loaded from json files.
    """
    def __init__(self):
        self._path = 'detectionPresets'  # dolder to load from
        
        self.loadPresets()
    
    def loadPresets(self):
        """Load all presets in folder 'detectionPresets'
        """
        
        files = os.dir(self._path)
        for file in files:
            if not file.endswith('.json'):
                continue
            oneJson = json_load(file)
            print(oneJson)
            
class bDetection(object):
    """ Class to manage detection parameters (experimental).

        - get defaults
        - get values
        - set values
    """

    detectionPresets = detectionPresets_
    """Enum with names of preset detection types"""

    detectionTypes = detectionTypes_
    """ Enum with the type of spike detection, (dvdt, mv)"""

    def getDetectionPresetList():
        """"Get list of names of detection type.
        """
        detectionList = []
        for detectionPreset in bDetection.detectionPresets:
            detectionList.append(detectionPreset.value)
        return detectionList

    #def __init__(self, detectionPreset=detectionPresets.caKymograph):
    def __init__(self, detectionPreset=detectionPresets.default):
        #logger.warning('\n   !!! LOADING: detectionPreset=detectionPresets.caKymograph\n\n')
        # local copy of default dictionary, do not modify
        self._dDict = getDefaultDetection(detectionPreset)
        self.toJson()


    def toJson(self):
        """Get key and defaultValue
        """
        theDict = {}
        for k,v in self._dDict.items():
            theDict[k] = v['defaultValue']

        logger.info('theDict:')
        #pprint(theDict)

        #with open(savePath, 'w') as f:
        #    json.dump(self._dDict, f, indent=4)
        theJson = json.dumps(theDict, indent=4)
        logger.info('theJson:')
        #print(theJson)
        
    def setToType(self, detectionPreset):
        """
        detectionPreset (enum) detectionPresets
        """
        self._dDict = getDefaultDetection(detectionPreset)

    #def __str__(self):
    #    return pprint(self._dDict)
    
    def getDefaultDetectionItem(self, key):
        #key = 'include'
        theDict = {}
        theDict[key] = {}
        theDict[key]['defaultValue'] = True
        theDict[key]['type'] = 'bool'
        theDict[key]['allowNone'] = False
        theDict[key]['units'] = ''
        theDict[key]['humanName'] = 'Include'
        theDict[key]['errors'] = ('')
        theDict[key]['description'] = 'Include analysis for this file'
        return theDict.copy()

    def printDict(self):
        for k in self._dDict.keys():
            v = self._dDict[k]['currentValue']
            print(f'  {k}: "{v}" {type(v)}')

    def __getitem__(self, key):
        # to mimic a dictionary
        # myDetection['a key']
        try:
            return self._dDict[key]['currentValue']
        except (KeyError) as e:
            logger.error(f'{e}')

    def __setitem__(self, key, value):
        # to mimic a dictionary
        try:
            self._dDict[key]['currentValue'] = value
        except (KeyError) as e:
            logger.error(f'{e}')

    def items(self):
        # to mimic a dictionary
        return self._dDict.items()

    def keys(self):
        # to mimic a dictionary
        return self._dDict.keys()

    def getMsValueAsPnt(self, key : str, dataPointsPerMs : int):
        """Get current value of a ms key as points.
        """
        if not key.endswith('_ms'):
            logger.warning(f'key "{key}" does not end in "_ms" ?')
        msValue = self.getValue(key)
        ret = msValue * dataPointsPerMs
        ret = round(ret)  # ensure it is an int
        return ret

    def getValue(self, key):
        "Get current value from key. Valid keys are defined in getDefaultDetection."
        try:
            return self._dDict[key]['currentValue']
        except (KeyError) as e:
            logger.warning(f'Did not find key "{key}" to get current value')
            # TODO: define default when not found ???
            return None

    def setValue(self, key, value):
        """
        Set current value for key. Valid keys are defined in getDefaultDetection.

        For float values that need to take on none, vlue comes in as -1e9
        """
        try:
            valueType = type(value)
            valueIsNumber = isinstance(value, numbers.Number)
            valueIsString = isinstance(value, str)
            valueIsBool = isinstance(value, bool)
            valueIsList = isinstance(value, list)
            valueIsNone = value is None

            expectedType = self._dDict[key]['type'] # (number, string, boolean)
            allowNone = self._dDict[key]['allowNone'] # used to turn off a detection param

            #logger.info(f'expectedType:{expectedType} value type is {type(value)}')

            if allowNone and valueIsNone:
                pass
            elif expectedType=='number' and not valueIsNumber:
                logger.warning(f'Type mismatch (number) setting key "{key}", got {valueType}, expecting {expectedType}')
                return False
            elif expectedType=='string' and not valueIsString:
                logger.warning(f'Type mismatch (string) setting "{key}", got {valueType}, expecting {expectedType}')
                return False
            elif expectedType=='boolean' and not valueIsBool:
                logger.warning(f'Type mismatch (bool) setting "{key}", got {valueType}, expecting {expectedType}')
                return False
            elif expectedType=='list' and not valueIsList:
                logger.warning(f'Type mismatch (list) setting "{key}", got {valueType}, expecting {expectedType}')
                return False
            elif expectedType=='sanpy.bDetection.detectionTypes':
                try:
                    value = sanpy.bDetection.detectionTypes[value].name
                    #print(value == sanpy.bDetection.detectionTypes.dvdt)
                    #print(value == sanpy.bDetection.detectionTypes.mv)
                except (KeyError) as e:
                    logger.error(f'sanpy.bDetection.detectionTypes does not contain value "{value}"')
            #
            # set
            self._dDict[key]['currentValue'] = value

            logger.info(f"now key:{key}: {self._dDict[key]['currentValue']} {type(self._dDict[key]['currentValue'])}")

            return True
        except (KeyError) as e:
            logger.warning(f'Did not find key "{key}" to set current value to "{value}"')
            return False

    def setFromDict(self, dDict):
        """
        Set detection from key/values in dDict

        Args:
            dDict (dict): Usually a table row like interface/bTableView.py
        """
        gotError = False
        for k,v in dDict.items():
            ok = self.setValue(k, v)
            if not ok:
                gotError = True
        return gotError

    def print(self):
        for k, v in self._dDict.items():
            print(k)
            for k2,v2 in v.items():
                print(f'  {k2} : {v2}')

    def old_save(self, saveBase):
        """
        Save underlying dict to json file

        Args:
            save base (str): basename to append '-detection.json'
        """

        # convert

        savePath = saveBase + '-detection.json'

        with open(savePath, 'w') as f:
            json.dump(self._dDict, f, indent=4)

    def old_load(self, loadBase):
        """
        Load detection from json file.

        Fill in underlying dict
        """

        loadPath = loadBase + '-detection.json'

        if not os.path.isfile(loadPath):
            logger.error(f'Did not find file: {loadPath}')
            return

        with open(loadPath, 'r') as f:
            self._dDict = json.load(f)

        # convert

    def getDict(self):
        return self._dDict

def test_0():
    """
    Testing get/set of detection params
    """

    bd = bDetection()

    #xxx = bd.getValue('xxx')

    #ok = bd.setValue('xxx', 2)
    #print('ok:', ok)

    ok1 = bd.setValue('dvdtThreshold', None)
    if not ok1:
        print('ok1:', ok1)

    ok1_5 = bd.setValue('mvThreshold', None)
    if not ok1_5:
        print('failure ok ok1_5:', ok1_5)

    ok2 = bd.setValue('cellType', '111')
    if not ok2:
        print('ok2:', ok2)

    # for setting list, check that (i) not empty and (ii) list[i] == expected type
    ok3 = bd.setValue('halfHeights', [])
    if not ok3:
        print('ok3:', ok3)

    # start/stop seconds defaults to None but we want 'number'
    ok4 = bd.setValue('startSeconds', 1e6)
    if not ok4:
        print('ok4:', ok4)

    tmpDict = {'Idx': 2.0, 'Include': 1.0, 'File': '19114001.abf', 'Dur(s)': 60.0, 'kHz': 20.0, 'Mode': 'fix', 'Cell Type': '', 'Sex': '', 'Condition': '', 'Start(s)': math.nan, 'Stop(s)': math.nan, 'dvdtThreshold': 50.0, 'mvThreshold': -20.0, 'refractory_ms': math.nan, 'peakWindow_ms': math.nan, 'halfWidthWindow_ms': math.nan, 'Notes': ''}
    for k,v in tmpDict.items():
        print('  ', k, ':', v)
    okSetFromDict = bd.setFromDict(tmpDict)

def test_save_load():
    # load an abf
    path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
    ba = sanpy.bAnalysis(path)

    # analyze
    ba.spikeDetect()
    print(ba)

    #print(ba._getSaveFolder())
    saveBase = ba._getSaveBase()

    detectionClass = ba.detectionClass

    '''
    detectionClass.save(saveBase)
    detectionClass._dDict = None

    detectionClass.load(saveBase)

    detectionClass.print()
    '''

    # might work
    ba.saveAnalysis()

    ba.loadAnalysis()

    #ba.detectionClass.print()

    print(ba)

if __name__ == '__main__':
    #test_0()

    # this works
    #printDocs()

    test_save_load()
