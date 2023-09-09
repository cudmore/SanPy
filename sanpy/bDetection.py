"""
The bDetection class provides an interface to get and set detection paramers.

Example
-------

```python
import sanpy

# grab the presets for 'SA Node' cells
dDict = sanpy.bDetection().getDetectionDict('SA Node')
ba.spikeDetect(dDict)

# tweek individual parameters
dDict['dvdtThreshold'] = 50

# load a recording
myPath = 'data/19114001.abf'
ba = sanpy.bAnalysis(myPath)

# perform spike detection
ba.spikeDetect(dDict)

# browse results
```
"""
from http.client import RemoteDisconnected
import os
import numbers
import math
from enum import Enum
import json
import pathlib
from pprint import pprint
import glob
import copy
from collections import OrderedDict

from matplotlib.font_manager import json_load

# from colin.stochAnalysis import load

import sanpy

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class detectionTypes_(Enum):
    """
    Detection type is one of (dvdt, mv).

    dvdt: Search for threshold crossings in first derivative of membrane potential.
    mv: Search for threshold crossings in membrane potential.
    """

    dvdt = "dvdt"
    mv = "mv"


# TODO (Cudmore) this needs to be a class so we can expand/contract based
# on what we find on the hard-drive
# allow user to save to detection presets


def getDefaultDetection():
    """Get detection parameters

    This includes a mapping from backend variable names to
    front-end human readable and long-format descriptions.

    Args:
        detectionPreset (enum): bDetection.detectionPresets.default

    Returns:
        dict: The default detection dictionary.
    """

    theDict = OrderedDict()  # {}

    """
    key = 'include'
    theDict[key] = {}
    theDict[key]['defaultValue'] = True
    theDict[key]['type'] = 'bool'
    theDict[key]['allowNone'] = False
    theDict[key]['units'] = ''
    theDict[key]['humanName'] = 'Include'
    theDict[key]['errors'] = ('')
    theDict[key]['description'] = 'Include analysis for this file'
    """

    key = "detectionName"
    theDict[key] = {}
    theDict[key]["defaultValue"] = "default"  # detectionPreset.value # ('dvdt', 'mv')
    theDict[key]["type"] = "string"
    theDict[key][
        "allowNone"
    ] = False  # To do, have 2x entry points to bAnalysis detect, never set this to nan
    theDict[key]["units"] = ""
    theDict[key]["humanName"] = "Detection Preset Name"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "The name of detection preset"

    key = "userSaveName"
    theDict[key] = {}
    theDict[key]["defaultValue"] = ""  # detectionPreset.value # ('dvdt', 'mv')
    theDict[key]["type"] = "string"
    theDict[key][
        "allowNone"
    ] = False  # To do, have 2x entry points to bAnalysis detect, never set this to nan
    theDict[key]["units"] = ""
    theDict[key]["humanName"] = "Saved Detection Params"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "The name of saved user detection params"

    key = "detectionType"
    theDict[key] = {}
    theDict[key]["defaultValue"] = sanpy.bDetection.detectionTypes[
        "dvdt"
    ].value  # ('dvdt', 'mv')
    theDict[key]["type"] = "sanpy.bDetection.detectionTypes"
    theDict[key][
        "allowNone"
    ] = False  # To do, have 2x entry points to bAnalysis detect, never set this to nan
    theDict[key]["units"] = ""
    theDict[key]["humanName"] = "Detection Type"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "Detect using derivative (dvdt) or membrane potential (mV)"

    key = "dvdtThreshold"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 20
    theDict[key]["type"] = "float"
    theDict[key][
        "allowNone"
    ] = True  # To do, have 2x entry points to bAnalysis detect, never set this to nan
    theDict[key]["units"] = "dVdt"
    theDict[key]["humanName"] = "dV/dt Threshold"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "dV/dt threshold for a spike, will be backed up to dvdt_percentOfMax and have xxx error when this fails"

    key = "mvThreshold"
    theDict[key] = {}
    theDict[key]["defaultValue"] = -20
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "mV"
    theDict[key]["humanName"] = "mV Threshold"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "mV threshold for spike AND minimum spike mV when detecting with dV/dt"

    key = "startSeconds"
    theDict[key] = {}
    theDict[key]["defaultValue"] = None
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = True
    theDict[key]["units"] = "s"
    theDict[key]["humanName"] = "Start(s)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Start seconds of analysis"

    key = "stopSeconds"
    theDict[key] = {}
    theDict[key]["defaultValue"] = None
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = True
    theDict[key]["units"] = "s"
    theDict[key]["humanName"] = "Stop(s)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Stop seconds of analysis"

    key = "cellType"
    theDict[key] = {}
    theDict[key]["defaultValue"] = ""
    theDict[key]["type"] = "string"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = ""
    theDict[key]["humanName"] = "Cell Type"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Cell Type"

    key = "sex"
    theDict[key] = {}
    theDict[key]["defaultValue"] = ""
    theDict[key]["type"] = "string"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = ""
    theDict[key]["humanName"] = "Sex"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Sex"

    key = "condition"
    theDict[key] = {}
    theDict[key]["defaultValue"] = ""
    theDict[key]["type"] = "string"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = ""
    theDict[key]["humanName"] = "Condition"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Condition"

    key = "dvdt_percentOfMax"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 0.1
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "Percent"
    theDict[key]["humanName"] = "dV/dt Percent of max"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "For dV/dt detection, the final TOP is when dV/dt drops to this percent from dV/dt AP peak"

    key = "onlyPeaksAbove_mV"
    theDict[key] = {}
    theDict[key]["defaultValue"] = None
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = True
    theDict[key]["units"] = "mV"
    theDict[key]["humanName"] = "Accept Peaks Above (mV)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Only accept APs with peaks above this value (mV)"

    key = "onlyPeaksBelow_mV"
    theDict[key] = {}
    theDict[key]["defaultValue"] = None
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = True
    theDict[key]["units"] = "mV"
    theDict[key]["humanName"] = "Accept Peaks Below (mV)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Only accept APs below this value (mV)"

    # TODO: get rid of this and replace with foot
    key = "doBackupSpikeVm"
    theDict[key] = {}
    theDict[key]["defaultValue"] = False
    theDict[key]["type"] = "boolean"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "Boolean"
    theDict[key]["humanName"] = "Backup Vm Spikes"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "If true, APs detected with just mV will be backed up until Vm falls to xxx"

    key = "refractory_ms"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 170
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "Minimum AP interval (ms)"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "APs with interval (wrt previous AP) less than this will be removed"

    key = "peakWindow_ms"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 100
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "Peak Window (ms)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Window after TOP (ms) to seach for AP peak (mV)"

    key = "dvdtPreWindow_ms"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 10
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "dV/dt Pre Window (ms)"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "Window (ms) to search before each TOP for real threshold crossing"

    key = "dvdtPostWindow_ms"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 20
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "dV/dt Post Window (ms)"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "Window (ms) to search after each AP peak for minimum in dv/dt"

    key = "mdp_ms"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 250
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "Pre AP MDP window (ms)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Window (ms) before an AP to look for MDP"

    key = "avgWindow_ms"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 5
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "MDP averaging window (ms)"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "Window (ms) to calculate MDP (mV) as a mean rather than mV at single point for MDP"

    key = "lowEddRate_warning"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 8
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "EDD slope"
    theDict[key]["humanName"] = "EDD slope warning"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "Generate warning when EED slope is lower than this value."

    key = "halfHeights"
    theDict[key] = {}
    theDict[key]["defaultValue"] = [10, 20, 50, 80, 90]
    theDict[key]["type"] = "list"  # list of number
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = ""
    theDict[key]["humanName"] = "AP Durations (%)"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "AP Durations as percent of AP height (AP Peak (mV) - TOP (mV))"

    key = "halfWidthWindow_ms"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 200
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "Half Width Window (ms)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Window (ms) after TOP to look for AP Durations"

    key = "preSpikeClipWidth_ms"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 200
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "Pre AP Clip Width (ms)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "The pre duration of generated AP clips (Before AP)"

    key = "postSpikeClipWidth_ms"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 500
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "Post AP Clip Width (ms)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "The post duration of generated AP clips (After AP)"

    key = "medianFilter"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 0
    theDict[key]["type"] = "int"
    theDict[key]["allowNone"] = True  # 0 is no median filter (see SavitzkyGolay_pnts)
    theDict[key]["units"] = "points"
    theDict[key]["humanName"] = "Median Filter Points"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "Number of points in median filter, must be odd, 0 for no filter"

    key = "SavitzkyGolay_pnts"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 5  # 20211001 was 5
    theDict[key]["type"] = "int"
    theDict[key]["allowNone"] = True  # 0 is no filter
    theDict[key]["units"] = "points"
    theDict[key]["humanName"] = "SavitzkyGolay Points"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "Number of points in SavitzkyGolay filter, must be odd, 0 for no filter"

    key = "SavitzkyGolay_poly"
    theDict[key] = {}
    theDict[key]["defaultValue"] = 2
    theDict[key]["type"] = "int"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = ""
    theDict[key]["humanName"] = "SavitzkyGolay Poly Deg"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "The degree of the polynomial for Savitzky-Golay filter"

    # key = 'dateAnalyzed'
    # theDict[key] = {}
    # theDict[key]['defaultValue'] = ''
    # theDict[key]['type'] = 'str'
    # theDict[key]['allowNone'] = False
    # theDict[key]['units'] = ''
    # theDict[key]['humanName'] = 'Date Analyzed'
    # theDict[key]['errors'] = ('')
    # theDict[key]['description'] = 'The date of analysis (yyyymmdd)'

    key = "verbose"
    theDict[key] = {}
    theDict[key]["defaultValue"] = False
    theDict[key]["type"] = "boolean"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "Boolean"
    theDict[key]["humanName"] = "Verbose"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Verbose Detection Reporting"

    # assign each detection param current value to it default value
    for k, v in theDict.items():
        defaultValue = theDict[k]["defaultValue"]
        theDict[k]["currentValue"] = defaultValue

    """
    if detectionPreset == bDetection.detectionPresets.default:
        # these are defaults from above
        pass
    elif detectionPreset == bDetection.detectionPresets.sanode:
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
        theDict['dvdtThreshold']['defaultValue'] = 20
        theDict['mvThreshold']['defaultValue'] = -40
        theDict['refractory_ms']['defaultValue'] = 4
        theDict['peakWindow_ms']['defaultValue'] = 5
        theDict['halfWidthWindow_ms']['defaultValue'] = 4
        theDict['dvdtPreWindow_ms']['defaultValue'] = 2
        theDict['dvdtPostWindow_ms']['defaultValue'] = 2
        theDict['preSpikeClipWidth_ms']['defaultValue'] = 2
        theDict['postSpikeClipWidth_ms']['defaultValue'] = 2
    elif detectionPreset == bDetection.detectionPresets.fastneuron:
        theDict['dvdtThreshold']['defaultValue'] = 20
        theDict['mvThreshold']['defaultValue'] = -40
        theDict['refractory_ms']['defaultValue'] = 3
        theDict['peakWindow_ms']['defaultValue'] = 2
        theDict['halfWidthWindow_ms']['defaultValue'] = 4
        theDict['dvdtPreWindow_ms']['defaultValue'] = 2
        theDict['dvdtPostWindow_ms']['defaultValue'] = 2
        theDict['preSpikeClipWidth_ms']['defaultValue'] = 2
        theDict['postSpikeClipWidth_ms']['defaultValue'] = 2
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
    elif detectionPreset == bDetection.detectionPresets.caspikes:
        #theDict['detectionType']['defaultValue'] = sanpy.bDetection.detectionTypes.mv # ('dvdt', 'mv')
        theDict['dvdtThreshold']['defaultValue'] = math.nan #if None then detect only using mvThreshold
        theDict['mvThreshold']['defaultValue'] = 0.5
        #theDict['refractory_ms']['defaultValue'] = 200 #170 # reject spikes with instantaneous frequency
        #theDict['halfWidthWindow_ms']['defaultValue'] = 200 #was 20
    elif detectionPreset == bDetection.detectionPresets.cakymograph:
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
        logger.error(f'    bDetection.detectionPresets.fastneuron: {bDetection.detectionPresets.fastneuron}')
        logger.error(f'    type(bDetection.detectionPresets.fastneuron): {type(bDetection.detectionPresets.fastneuron)}')
        logger.error(f'    detectionPreset == bDetection.detectionPresets.fastneuron: {detectionPreset == bDetection.detectionPresets.fastneuron}')
    """

    # assign each detection param current value to it default value
    """
    for k,v in theDict.items():
        defaultValue = theDict[k]['defaultValue']
        theDict[k]['currentValue'] = defaultValue
    """

    return theDict.copy()


def printDocs():
    """Print out human readable detection parameters and convert to markdown table.

    Requires:
        pip install tabulate

    See: bAnalysisResults.printDocs()
    """
    logger.info("")

    import pandas as pd

    # detectionPreset = bDetection.detectionPresets.default  # detectionPresets_ is an enum class
    d = getDefaultDetection()
    dictList = []
    for k, v in d.items():
        parameter = k
        oneDict = {
            "Parameter": parameter,
            "Default Value": v["defaultValue"],
            "Units": v["units"],
            "Human Readable": v["humanName"],
            "Description": v["description"],
        }
        dictList.append(oneDict)
    #
    df = pd.DataFrame(dictList)

    # spit out markdown to copy/paste into mkdocs md file
    # REMEMBER: This requires `pip install tabulate`
    # outStr = df.to_markdown()
    # print(outStr)

    # save to csv for making a table for manuscript
    path = "/Users/cudmore/Desktop/sanpy-detection-params-20230316.csv"
    print("saving to:", path)
    df.to_csv(path, index=False)


'''
class detectionPresets():
    """A list of bDetection that are saved/loaded from json files.
    """
    def __init__(self):
        self._path = 'detectionPresets'  # folder to load from
        
        self.loadPresets()
    
    def loadPresets(self):
        """Load all presets in folder 'detectionPresets'
        """
        
        logger.info('')
        files = os.dir(self._path)
        for file in files:
            if not file.endswith('.json'):
                continue
            oneJson = json_load(file)
            print(oneJson)
'''


class bDetection(object):
    """Class to manage detection parameters."""

    detectionTypes = detectionTypes_
    """ Enum with the type of spike detection, (dvdt, mv)"""

    def __init__(self):
        """Load all sanpy and <user> detection json files."""

        # dict with detection key and current value
        self._dDict = getDefaultDetection()

        # list of preset names including <user>SanPy/detection json files
        # use item=e[key] or item=e(value) then use item.name or item.value
        _theDict, _userPresetsDict = self._getPresetsDict()
        self._detectionEnum = Enum("self.detectionEnum", _theDict)

        # dictionary of presets, each key is like 'sanode' and then value is a dict of
        #   detection param keys and their values
        self._detectionPreset = {}
        for item in self._detectionEnum:
            # item is like self.detectionEnum.sanode
            # logger.info(f'  loaded {item}, {item.name}, "{item.value}"')
            presetValues = self._getPresetValues(item)
            if presetValues:
                # got value of built in preset
                self._detectionPreset[item.name] = presetValues
            else:
                # find in user loaded presets
                _userKey = item.name
                try:
                    self._detectionPreset[item.name] = _userPresetsDict[_userKey]
                except:
                    logger.erro(
                        f"did not find item.name:{item.name} in _detectionPreset {self._detectionPreset.keys()}"
                    )

    def getDetectionPresetList(self):
        """Get list of names of detection type.

        Used to make a list in popup in interface/ and interface/plugins
        """
        detectionList = []
        for detectionPreset in self._detectionEnum:
            detectionList.append(detectionPreset.value)
        return detectionList

    def getDetectionKey(self, humanName):
        """Map human readable name like 'SA Node' back to key 'sanode'
        """
        for detectionPreset in self._detectionEnum:
            if detectionPreset.value == humanName:
                return detectionPreset.name
        logger.error(f'did not find human name {humanName} in detection presets?')
        logger.error(f'  possible names are {self.getDetectionPresetList()}')

    def _getPresetsDict(self):
        """Load detection presets from json files in 2 different folder:
            1) sanpy/detection-presets
            2) <user>/Documents/Sanpy/detection/

        For file name like 'Fast Neuron.json' make key 'fastneuron'

        Returns:
            userPresets (dict): One item per user file
        """

        def fileNameToKey(filePath):
            """Given full path to json file, return
            Filename without extension, and a well formed key.
            """
            fileName = os.path.split(filePath)[1]
            fileName = os.path.splitext(fileName)[0]

            fileNameKey = os.path.split(filePath)[1]
            fileNameKey = os.path.splitext(fileNameKey)[0]
            # reduce preset json filename to (lower case, no spaces, no dash)
            fileNameKey = fileNameKey.lower()
            fileNameKey = fileNameKey.replace(" ", "")
            fileNameKey = fileNameKey.replace(
                "-", ""
            )  # in case user specifies a '-' in file name
            return fileName, fileNameKey

        theDict = {}
        userPresets = {}

        #
        # get files in our 'detection-presets' folder
        """
        presetsPath = pathlib.Path(sanpy._util.getBundledDir()) / 'detection-presets' / '*.json'
        files = glob.glob(str(presetsPath))
        for filePath in files:
            fileName, fileNameKey = fileNameToKey(filePath)
            #
            theDict[fileNameKey] = fileName
        """
        theDict["sanode"] = "SA Node"
        theDict["ventricular"] = "Ventricular"
        theDict["neuron"] = "Neuron"
        theDict["fastneuron"] = "Fast Neuron"
        theDict["subthreshold"] = "Sub Threshold"
        theDict["caspikes"] = "Ca Spikes"
        theDict["cakymograph"] = "Ca Kymograph"

        #
        # get files in <users>/Documents/SanPy/detection/ folder
        # userDetectionPath = pathlib.Path(sanpy._util._getUserDetectionFolder()) / '*.json'
        # files = glob.glob(str(userDetectionPath))
        files = self._getUserFiles()
        # print('user files:', files)
        for filePath in files:
            fileName, fileNameKey = fileNameToKey(filePath)
            theDict[fileNameKey] = fileName

            # load user preset json and grab (param keys and values)
            with open(filePath, "r") as f:
                userPresetsDict = json.load(f)
                userPresets[fileNameKey] = userPresetsDict

        return theDict, userPresets

    def _getUserFiles(self):
        """Get the full path to all user file presets .json"""
        userDetectionPath = pathlib.Path(sanpy._util._getUserDetectionFolder())
        if userDetectionPath.is_dir:
            files = userDetectionPath.glob("*.json")
            return files
        else:
            return []

    def toJson(self):
        """Get key and defaultValue"""
        theDict = {}
        for k, v in self._dDict.items():
            theDict[k] = v["defaultValue"]

        # logger.info('theDict:')
        # pprint(theDict)

        # with open(savePath, 'w') as f:
        #    json.dump(self._dDict, f, indent=4)
        theJson = json.dumps(theDict, indent=4)
        # logger.info('theJson:')
        return theJson

    def old_saveAs(self, detectionType: str, filename, path=None):
        """Save a detection dictionary to json.

        If running in GUI, main SanPy app will specify the correct path.

        This is only for user defined sets, we never save our built in detection (hard coded in code).

        Args:
            detectionType: human readable like 'SA Node', will become 'SA Node.json'
            filename: Name of file to save (no extension, will append .json)
        """
        # _keyName = self._detectionEnum(detectionType).name
        if path is None:
            # get <user>/Documents/SanPy/xxx folder
            savePath = sanpy._util._getUserDetectionFolder()
            savePath = pathlib.Path(savePath) / f"{filename}.json"
        logger.info(str(savePath))
        with open(savePath, "w") as f:
            dDict = self.getDetectionDict(detectionType)
            dDict["detectionName"] = filename
            json.dump(dDict, f, indent=4)

    def printDict(self):
        for k in self._dDict.keys():
            v = self._dDict[k]["currentValue"]
            print(f'  {k}: "{v}" {type(v)}')

    def getMasterDict(self, detectionType: str):
        """Get the full dictionary from self._dDict getDefaultDetection()

        This is needed by sanpy/interface/plugins/detectionParams.py
        """

        retDict = copy.deepcopy(self._dDict)

        detectionTypeKey = self._detectionEnum(detectionType).name
        oneType = self._detectionPreset[detectionTypeKey]
        for k, v in oneType.items():
            retDict[k]["currentValue"] = v

        return retDict

    def getDetectionDict(self, detectionType: str, allParameter=True):
        """Get a full detection dict.

        Presets like 'SA Node' only over-ride a subset of the defaults, thus need to merge.
        User saved detection parameters will have all keys.

        Args:
            detectionType : detection type key, like 'SA Node'
        """
        try:
            if allParameter:
                dDict = {}

                # master template to get all default values
                for k, v in self._dDict.items():
                    dDict[k] = v["currentValue"]

                # use specified detection type to get over-written values
                detectionTypeKey = self._detectionEnum(detectionType).name
                oneType = self._detectionPreset[detectionTypeKey]
                for k, v in oneType.items():
                    dDict[k] = v
            return dDict
        except KeyError as e:
            logger.error(f'Did not find detectionType:"{detectionType}"')
        except ValueError as e:
            logger.error(f'Did not find detectionType:"{detectionType}"')

    def getValue(self, detectionType: str, key):
        """Get current value from key. Valid keys are defined in getDefaultDetection().

        Args:
            detectionType : string value from enum, like 'SA Node'
        """
        try:
            # return self._dDict[key]['currentValue']
            return self._detectionPreset[detectionType][key]
        except KeyError as e:
            logger.warning(
                f'Did not find detectionType "{detectionType}" or key "{key}" to get current value'
            )
            # TODO: define default when not found ???
            return None

    def setValue(self,
                    detectionType: str,
                    key: str,
                    value):
        """
        Set current value for key. Valid keys are defined in getDefaultDetection.

        For float values that need to take on none, value comes in as -1e9

        Args:
            detectionType : short name (not value)
        """
        try:
            valueType = type(value)
            valueIsNumber = isinstance(value, numbers.Number)
            valueIsString = isinstance(value, str)
            valueIsBool = isinstance(value, bool)
            valueIsList = isinstance(value, list)
            valueIsNone = value is None

            # from the master list
            expectedType = self._dDict[key]["type"]  # (number, string, boolean)
            allowNone = self._dDict[key][
                "allowNone"
            ]  # used to turn off a detection param

            # logger.info(f'expectedType:{expectedType} value type is {type(value)}')

            if allowNone and valueIsNone:
                pass
            elif expectedType == "number" and not valueIsNumber:
                logger.warning(
                    f'Type mismatch (number) setting key "{key}", got {valueType}, expecting {expectedType}'
                )
                return False
            elif expectedType == "string" and not valueIsString:
                logger.warning(
                    f'Type mismatch (string) setting "{key}", got {valueType}, expecting {expectedType}'
                )
                return False
            elif expectedType == "boolean" and not valueIsBool:
                logger.warning(
                    f'Type mismatch (bool) setting "{key}", got {valueType}, expecting {expectedType}'
                )
                return False
            elif expectedType == "list" and not valueIsList:
                logger.warning(
                    f'Type mismatch (list) setting "{key}", got {valueType}, expecting {expectedType}'
                )
                return False
            """
            elif expectedType=='sanpy.bDetection.detectionTypes':
                try:
                    value = sanpy.bDetection.detectionTypes[value].name
                    #print(value == sanpy.bDetection.detectionTypes.dvdt)
                    #print(value == sanpy.bDetection.detectionTypes.mv)
                except (KeyError) as e:
                    logger.error(f'sanpy.bDetection.detectionTypes does not contain value "{value}"')
            """
            #
            # set
            # self._dDict[key]['currentValue'] = value
            self._detectionPreset[detectionType][key] = value

            logger.info(
                f"now detectionType:{detectionType} key:{key}: {self._detectionPreset[detectionType][key]} {type(self._detectionPreset[detectionType][key])}"
            )

            return True

        except KeyError as e:
            logger.warning(
                f'Did not find detectionType:{detectionType}, key:"{key}" to set current value to "{value}"'
            )
            logger.warning(f'  available detectionType are: {self._detectionPreset.keys()}')
            return False

    def old_save(self, saveBase):
        """
        Save underlying dict to json file

        Args:
            save base (str): basename to append '-detection.json'
        """

        # convert

        savePath = saveBase + "-detection.json"

        with open(savePath, "w") as f:
            json.dump(self._dDict, f, indent=4)

    def old_load(self, loadBase):
        """
        Load detection from json file.

        Fill in underlying dict
        """

        loadPath = loadBase + "-detection.json"

        if not os.path.isfile(loadPath):
            logger.error(f"Did not find file: {loadPath}")
            return

        with open(loadPath, "r") as f:
            self._dDict = json.load(f)

        # convert

    def _getPresetValues(self, detectionPreset):
        """
        detectionName : corresponds to key in enum self._detectionEnum
        """

        theDict = {}

        if detectionPreset == self._detectionEnum.sanode:
            theDict["detectionName"] = "SA Node"
            theDict["dvdtThreshold"] = 20
            theDict["mvThreshold"] = -20
            theDict["refractory_ms"] = 170  # max freq of 5 Hz
            theDict["peakWindow_ms"] = 100
            theDict["halfWidthWindow_ms"] = 200
            theDict["preSpikeClipWidth_ms"] = 200
            theDict["postSpikeClipWidth_ms"] = 500
        elif detectionPreset == self._detectionEnum.ventricular:
            theDict["detectionName"] = "Ventricular"
            theDict["dvdtThreshold"] = 100
            theDict["mvThreshold"] = -20
            theDict["refractory_ms"] = 200  # max freq of 5 Hz
            theDict["peakWindow_ms"] = 100
            theDict["halfWidthWindow_ms"] = 300
            theDict["preSpikeClipWidth_ms"] = 200
            theDict["postSpikeClipWidth_ms"] = 500
        elif detectionPreset == self._detectionEnum.neuron:
            theDict["detectionName"] = "Neuron"
            theDict["dvdtThreshold"] = 20
            theDict["mvThreshold"] = -40
            theDict["refractory_ms"] = 4
            theDict["peakWindow_ms"] = 5
            theDict["halfWidthWindow_ms"] = 4
            theDict["dvdtPreWindow_ms"] = 2
            theDict["dvdtPostWindow_ms"] = 2
            theDict["preSpikeClipWidth_ms"] = 2
            theDict["postSpikeClipWidth_ms"] = 2
        elif detectionPreset == self._detectionEnum.fastneuron:
            theDict["detectionName"] = "Fast Neuron"
            theDict["dvdtThreshold"] = 20
            theDict["mvThreshold"] = -40
            theDict["refractory_ms"] = 3
            theDict["peakWindow_ms"] = 2
            theDict["halfWidthWindow_ms"] = 4
            theDict["dvdtPreWindow_ms"] = 2
            theDict["dvdtPostWindow_ms"] = 2
            theDict["preSpikeClipWidth_ms"] = 2
            theDict["postSpikeClipWidth_ms"] = 2
        elif detectionPreset == self._detectionEnum.subthreshold:
            theDict["detectionName"] = "Subthreshold"
            theDict["dvdtThreshold"] = math.nan
            theDict["mvThreshold"] = -20  # user specifies
            theDict["refractory_ms"] = 100  # max freq is 10 Hz
            theDict["peakWindow_ms"] = 50
            theDict["halfWidthWindow_ms"] = 100
            theDict["preSpikeClipWidth_ms"] = 100
            theDict["postSpikeClipWidth_ms"] = 200
            theDict["onlyPeaksAbove_mV"] = None
            theDict["onlyPeaksBelow_mV"] = -20
            # todo: add onlyPeaksBelow_mV
        elif detectionPreset == self._detectionEnum.caspikes:
            theDict["detectionName"] = "Ca Spikes"
            # theDict['detectionType'] = sanpy.bDetection.detectionTypes.mv # ('dvdt', 'mv')
            theDict[
                "dvdtThreshold"
            ] = math.nan  # if None then detect only using mvThreshold
            theDict["mvThreshold"] = 0.5
            # theDict['refractory_ms'] = 200 #170 # reject spikes with instantaneous frequency
            # theDict['halfWidthWindow_ms'] = 200 #was 20
        elif detectionPreset == self._detectionEnum.cakymograph:
            theDict["detectionName"] = "Ca Kymograph"
            theDict["detectionType"] = sanpy.bDetection.detectionTypes["dvdt"].value
            # rosie, was math.nan #if None then detect only using mvThreshold
            theDict["dvdtThreshold"] = 0.05
            theDict["mvThreshold"] = 0.5
            theDict["peakWindow_ms"] = 400  # rosie, was 700
            theDict["halfWidthWindow_ms"] = 400  # rosie, was 800
            theDict["refractory_ms"] = 500
            theDict["doBackupSpikeVm"] = False
            # theDict['SavitzkyGolay_pnts'] = 5
            theDict["preSpikeClipWidth_ms"] = 200
            theDict["postSpikeClipWidth_ms"] = 1000
        else:
            logger.error(f"did not understand detectionPreset: {detectionPreset}")

        return theDict


def test_0():
    """
    Testing get/set of detection params
    """

    bd = bDetection()

    # xxx = bd.getValue('xxx')

    # ok = bd.setValue('xxx', 2)
    # print('ok:', ok)

    ok1 = bd.setValue("dvdtThreshold", None)
    if not ok1:
        print("ok1:", ok1)

    ok1_5 = bd.setValue("mvThreshold", None)
    if not ok1_5:
        print("failure ok ok1_5:", ok1_5)

    ok2 = bd.setValue("cellType", "111")
    if not ok2:
        print("ok2:", ok2)

    # for setting list, check that (i) not empty and (ii) list[i] == expected type
    ok3 = bd.setValue("halfHeights", [])
    if not ok3:
        print("ok3:", ok3)

    # start/stop seconds defaults to None but we want 'number'
    ok4 = bd.setValue("startSeconds", 1e6)
    if not ok4:
        print("ok4:", ok4)

    tmpDict = {
        "Idx": 2.0,
        "Include": 1.0,
        "File": "19114001.abf",
        "Dur(s)": 60.0,
        "kHz": 20.0,
        "Mode": "fix",
        "Cell Type": "",
        "Sex": "",
        "Condition": "",
        "Start(s)": math.nan,
        "Stop(s)": math.nan,
        "dvdtThreshold": 50.0,
        "mvThreshold": -20.0,
        "refractory_ms": math.nan,
        "peakWindow_ms": math.nan,
        "halfWidthWindow_ms": math.nan,
        "Notes": "",
    }
    for k, v in tmpDict.items():
        print("  ", k, ":", v)
    okSetFromDict = bd.setFromDict(tmpDict)


def test_save_load():
    # load an abf
    path = "/Users/cudmore/Sites/SanPy/data/19114001.abf"
    ba = sanpy.bAnalysis(path)

    # analyze
    ba.spikeDetect()
    print(ba)

    # print(ba._getSaveFolder())
    saveBase = ba._getSaveBase()

    detectionClass = ba.detectionClass

    """
    detectionClass.save(saveBase)
    detectionClass._dDict = None

    detectionClass.load(saveBase)

    detectionClass.print()
    """

    # might work
    ba.saveAnalysis()

    ba.loadAnalysis()

    # ba.detectionClass.print()

    print(ba)


def _exportDetectionJson():
    """20220705

    need to load/save detection presets from json

    To start, this will save json from the hard coded getDefaultDetection() function.
    """
    savePath = "/Users/cudmore/Desktop/detection-presets"

    for oneDetection in bDetection.detectionPresets:
        print("oneDetection:", oneDetection, "oneDetection.value:", oneDetection.value)

        onePreset = bDetection.detectionPresets(oneDetection)
        oneDetectionClass = bDetection(onePreset)
        # oneJson = oneDetectionClass.toJson()

        _theDict = {}
        for k, v in oneDetectionClass._dDict.items():
            print(k)
            _theDict[k] = v["defaultValue"]

        # print('_theDict.items():', _theDict.items())
        # pprint(_theDict)

        oneSaveFile = oneDetection.value + ".json"
        onseSavePath = os.path.join(savePath, oneSaveFile)
        print("    ", onseSavePath)

        with open(onseSavePath, "w") as f:
            # json.dump(oneJson, f, ensure_ascii=False, indent=4)
            json.dump(_theDict, f, indent=4)

        # load to check
        with open(onseSavePath) as f:
            # need this to keep them in order ... 'object_pairs_hook=OrderedDict'
            data_loaded = json.load(f, object_pairs_hook=OrderedDict)
        pprint(data_loaded)

        # break


def testSwitchType():
    # bd = sanpy.bDetection() # default to bDetection.detectionDefaults.default
    bd = sanpy.bDetection()

    # names of all presets, both (built in, and user)
    presetList = bd.getDetectionPresetList()
    print("presetList:", presetList)

    # detection dict for one
    print("=== sanode")
    dDict = bd.getDetectionDict("SA Node")
    for k, v in dDict.items():
        print(f"    {k}:{v} {type(v)}")

    print("=== fastneuron2")
    dDict = bd.getDetectionDict("Fast Neuron 2")
    for k, v in dDict.items():
        print(f"    {k}:{v} {type(v)}")

    # detection dict for all
    """
    for item in bd._detectionEnum:
        dDict = bd.getDetectionDict(item.name)
        print(f'=== {item.name} {item.value}')
        pprint(dDict)
    """

    bd.setValue("sanode", "dvdtThreshold", 12)

    print("=== after setValue 12 sanode")
    dDict = bd.getDetectionDict("SA Node")
    for k, v in dDict.items():
        print(f"    {k}:{v} {type(v)}")

    newValue = bd.getValue("sanode", "dvdtThreshold")
    print("newValue:", newValue)

    # works
    # bd.saveAs('SA Node', filename='xxx yyy')
    bd.saveAs("SA Node", filename="SA Node 3")


if __name__ == "__main__":
    # test_0()

    # this works
    printDocs()

    # test_save_load()

    # _exportDetectionJson()

    # testSwitchType()
    # print('detectionPresets.default:', bDetection.detectionPresets.default)
    # print('detectionPresets.neuron:', bDetection.detectionPresets.neuron)
    # print('detectionPresets.neuron.value:', bDetection.detectionPresets.neuron.value)
    # print('getDetectionPresetList:', bDetection.getDetectionPresetList())
