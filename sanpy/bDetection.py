"""Manage SanPy spike-detection parameters and presets."""
from http.client import RemoteDisconnected
import os
import numbers
import math
from enum import Enum
import json
import pathlib
from pprint import pprint
import glob

from sanpy.sanpyPaths import SanPyPaths
import copy
from collections import OrderedDict
from typing import Any

import sanpy
from sanpy.schema import DetectionParameterCategory

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


def getDefaultDetection() -> dict[str, dict[str, Any]]:
    """Build the authoritative detection-parameter definition dictionary.

    Returns:
        A new ordered dictionary mapping internal parameter names to their
        runtime definitions, including presentation categories.
    """

    theDict = OrderedDict()  # {}

    key = "detectionName"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.GENERAL
    theDict[key]["show_in_editor"] = True
    theDict[key]["defaultValue"] = "default"  # detectionPreset.value # ('dvdt', 'mv')
    theDict[key]["type"] = "string"
    theDict[key][
        "allowNone"
    ] = False  # To do, have 2x entry points to bAnalysis detect, never set this to nan
    theDict[key]["units"] = ""
    theDict[key]["humanName"] = "Detection Preset"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "The name of detection preset"

    key = "userSaveName"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.GENERAL
    theDict[key]["show_in_editor"] = True
    theDict[key]["defaultValue"] = ""  # detectionPreset.value # ('dvdt', 'mv')
    theDict[key]["type"] = "string"
    theDict[key][
        "allowNone"
    ] = False  # To do, have 2x entry points to bAnalysis detect, never set this to nan
    theDict[key]["units"] = ""
    theDict[key]["humanName"] = "Save User Name"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "The name of saved user detection params"

    key = "detectionType"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.DETECTION
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.DETECTION
    theDict[key]["show_in_editor"] = True
    theDict[key]["defaultValue"] = 20
    theDict[key]["type"] = "float"
    theDict[key][
        "allowNone"
    ] = True  # To do, have 2x entry points to bAnalysis detect, never set this to nan
    theDict[key]["units"] = "mV/ms"
    theDict[key]["humanName"] = "dV/dt Threshold"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "Minimum dV/dt used to detect a spike threshold"

    key = "mvThreshold"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.DETECTION
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.WINDOWS
    theDict[key]["show_in_editor"] = False
    theDict[key]["defaultValue"] = None
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = True
    theDict[key]["units"] = "s"
    theDict[key]["humanName"] = "Start(s)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = (
        "Start seconds of analysis, set from the visible x-range when detecting"
    )

    key = "stopSeconds"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.WINDOWS
    theDict[key]["show_in_editor"] = False
    theDict[key]["defaultValue"] = None
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = True
    theDict[key]["units"] = "s"
    theDict[key]["humanName"] = "Stop(s)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = (
        "Stop seconds of analysis, set from the visible x-range when detecting"
    )

    # abb 202610, userType does not belong in detection. it is a spike property
    # key = "userType"
    # theDict[key] = {}
    # theDict[key]["category"] = DetectionParameterCategory.GENERAL
    # theDict[key]["defaultValue"] = "0"
    # theDict[key]["type"] = "int"
    # theDict[key]["allowNone"] = False
    # theDict[key]["units"] = ""
    # theDict[key]["humanName"] = "User Type"
    # theDict[key]["errors"] = ""
    # theDict[key]["description"] = "User Type"

    key = "dvdt_percentOfMax"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.DETECTION
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.WAVEFORM
    theDict[key]["show_in_editor"] = True
    theDict[key]["defaultValue"] = None
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = True
    theDict[key]["units"] = "mV"
    theDict[key]["humanName"] = "Accept Peaks Above (mV)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Only accept APs with peaks above this value (mV)"

    key = "onlyPeaksBelow_mV"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.WAVEFORM
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.ADVANCED
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.WINDOWS
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.WINDOWS
    theDict[key]["show_in_editor"] = True
    theDict[key]["defaultValue"] = 100
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "Peak Window (ms)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Window after TOP (ms) to seach for AP peak (mV)"

    key = "dvdtPreWindow_ms"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.WINDOWS
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.WINDOWS
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.WINDOWS
    theDict[key]["show_in_editor"] = True
    theDict[key]["defaultValue"] = 250
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "Pre AP MDP window (ms)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Window (ms) before an AP to look for MDP"

    key = "avgWindow_ms"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.WINDOWS
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.ADVANCED
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.WAVEFORM
    theDict[key]["show_in_editor"] = True
    theDict[key]["defaultValue"] = [10, 20, 50, 80, 90]
    theDict[key]["type"] = "list"  # list of number
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = ""
    theDict[key]["humanName"] = "AP Widths"
    theDict[key]["errors"] = ""
    theDict[key][
        "description"
    ] = "AP Widths - hard coded as [10, 20, 50, 80, 90] percent of AP height (AP Peak (mV) - TOP (mV))"

    key = "halfWidthWindow_ms"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.WINDOWS
    theDict[key]["show_in_editor"] = True
    theDict[key]["defaultValue"] = 200
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "Half Width Window (ms)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Window (ms) after TOP to look for AP widths"

    key = "preSpikeClipWidth_ms"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.WINDOWS
    theDict[key]["show_in_editor"] = True
    theDict[key]["defaultValue"] = 4
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "Pre AP Clip Width (ms)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "The pre duration of generated AP clips (Before AP)"

    key = "postSpikeClipWidth_ms"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.WINDOWS
    theDict[key]["show_in_editor"] = True
    theDict[key]["defaultValue"] = 8
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "Post AP Clip Width (ms)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "The post duration of generated AP clips (After AP)"

    # new 20231201, for mich lab
    key = "fastAhpWindow_ms"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.WINDOWS
    theDict[key]["show_in_editor"] = True
    theDict[key]["defaultValue"] = 8
    theDict[key]["type"] = "float"
    theDict[key]["allowNone"] = False
    theDict[key]["units"] = "ms"
    theDict[key]["humanName"] = "Fast AHP Window (ms)"
    theDict[key]["errors"] = ""
    theDict[key]["description"] = "Window (ms) after peak to look for a fast AHP"

    key = "medianFilter"
    theDict[key] = {}
    theDict[key]["category"] = DetectionParameterCategory.FILTERING
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.FILTERING
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.FILTERING
    theDict[key]["show_in_editor"] = True
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
    theDict[key]["category"] = DetectionParameterCategory.ADVANCED
    theDict[key]["show_in_editor"] = True
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


def printDocs() -> None:
    """Print or save human-readable detection-parameter documentation.

    This developer utility currently writes a CSV file used when maintaining
    SanPy documentation.
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
            "Category": v["category"],
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

    def __init__(self, sanpy_paths: SanPyPaths | None = None) -> None:
        """Load all bundled and user detection presets.

        Args:
            sanpy_paths: Optional application path manager.
        """

        self._sanpy_paths = sanpy_paths or SanPyPaths()

        # dict with detection key and current value
        self._dDict = getDefaultDetection()

        # Names of presets loaded from the user detection folder.
        self._userPresetNames: set[str] = set()

        # list of preset names including <user>SanPy/detection json files
        # use item=e[key] or item=e(value) then use item.name or item.value
        # _theDict, _userPresetsDict = self._getPresetsDict()
        self._detectionPreset = self._getPresetsDict()

    def getDetectionPresetList(self) -> list[str]:
        """Return the names of all loaded detection presets.

        Returns:
            Bundled and user-defined preset names.
        """
        return list(self._detectionPreset.keys())

    def isUserPreset(self, name: str) -> bool:
        """Return whether ``name`` was loaded from the user detection folder.

        Args:
            name: Detection-preset name, such as ``"User - My Params"``.

        Returns:
            True when ``name`` came from the user ``detection/`` folder.
        """
        return name in self._userPresetNames

    def reloadPresets(self) -> None:
        """Reload bundled and user detection presets from disk.

        Call this after a user preset file is saved so later preset queries
        include that file.
        """
        self._userPresetNames = set()
        self._detectionPreset = self._getPresetsDict()

    def _getPresetsDict(self) -> dict:
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

            return fileName, fileNameKey

        theDict = {}
        # userPresets = {}

        #
        # get files in our 'detection-presets' folder
        presetsPath = self._sanpy_paths.bundled_dir / 'detection-presets' / '*.json'
        files = glob.glob(str(presetsPath))
        for filePath in files:
            fileName, fileNameKey = fileNameToKey(filePath)
            # logger.info(f'detection-presets json fileNameKey:{fileNameKey} fileName:{fileName}')
            #
            # theDict[fileNameKey] = fileName

            # load bundled preset json and grab (param keys and values)
            with open(filePath, "r") as f:
                userPresetsDict = json.load(f)
                theDict[fileNameKey] = userPresetsDict

        # theDict["sanode"] = "SA Node"
        # theDict["ventricular"] = "Ventricular"
        # theDict["neuron"] = "Neuron"
        # theDict["fastneuron"] = "Fast Neuron"

        #
        # get files in <users>/Documents/SanPy/detection/ folder
        files = self._getUserFiles()
        for filePath in files:
            fileName, fileNameKey = fileNameToKey(filePath)
            # theDict[fileNameKey] = fileName

            # load user preset json and grab (param keys and values)
            with open(filePath, "r") as f:
                userPresetsDict = json.load(f)
                theDict[fileNameKey] = userPresetsDict
                self._userPresetNames.add(fileNameKey)

        # make sure what we loaded has all the needed keys
        _defaultDetection = getDefaultDetection()
        for _fileNameKey, _loadedDetectionDict in theDict.items():
            for _key, _defaultDict in _defaultDetection.items():
                if _key not in _loadedDetectionDict.keys():
                    _loadedDetectionDict[_key] = _defaultDetection[_key]['defaultValue']

        return theDict  #, userPresets

    def _getUserFiles(self) -> list[pathlib.Path]:
        """Return paths to user detection-preset files.

        Returns:
            Detection-preset JSON paths, or an empty list when unavailable.
        """
        userDetectionPath = self._sanpy_paths.detection_dir
        if userDetectionPath.is_dir():
            return list(userDetectionPath.glob("*.json"))
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

    def printDict(self):
        for k in self._dDict.keys():
            v = self._dDict[k]["currentValue"]
            print(f'  {k}: "{v}" {type(v)}')

    def getMasterDict(self, detectionType: str):
        """Get the full dictionary from self._dDict getDefaultDetection()

        This is needed by sanpy/interface/plugins/detectionParams.py
        """

        retDict = copy.deepcopy(self._dDict)

        oneType = self.getDetectionDict(detectionType)
        for k, v in oneType.items():
            retDict[k]["currentValue"] = v

        return retDict

    def getDetectionDict(
        self, detectionType: str, allParameter: bool = True
    ) -> dict[str, Any]:
        """Return an independent detection-parameter dictionary for a preset.

        All presets are completed with default parameter values when they are
        loaded, so callers can safely adjust the returned dictionary before
        passing it to ``bAnalysis.spikeDetect()``.

        Args:
            detectionType: Preset name, such as ``"SA Node"``.
            allParameter: Retained for compatibility. Presets always contain all
                detection parameters.

        Returns:
            A copy of the requested preset's detection parameters.

        Raises:
            KeyError: If ``detectionType`` is not a loaded preset name.
        """
        return copy.deepcopy(self._detectionPreset[detectionType])

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
        """Set current value for key. Valid keys are defined in getDefaultDetection.

        For float values that need to take on none, value comes in as -1e9

        Args:
            detectionType : str
                Name of detection type (corresonds to json file)
            key: str
                Detection parameter name
            value:
                the value to set
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


if __name__ == "__main__":

    # this works
    printDocs()
