import os
import pathlib
import json
from json.decoder import JSONDecodeError

import sanpy
import sanpy.interface
import sanpy.interface.sanpy_app as sanpy_app

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class preferences:
    """Class to hold GUI preferences.

    Created and used by sanpy app SanPyWindow.
    """

    def __init__(self, sanpyApp: sanpy_app):
        super().__init__()
        self._sanpyApp = sanpyApp

        # bump this when we change, sanpy app will rebuild if loaded preferences are out of date
        # self._version = 1.2  # increment when we change preferences
        # self._version = 1.3  # added set spike
        # self._version = 1.4  # converted plugins from list[str] to dict to include externalWindow option
        # self._version = 1.5  # adding keys to plugins (l, t, w, h)
        # self._version = 1.6  # adding SetMetaData
        self._version = 1.7  # 20230804, adding folder depth

        self._maxRecent = 7  # a lucky number
        self._configDict = self.load()

    def __setitem__(self, key, item):
        self._configDict[key] = item

    def __getitem__(self, key):
        return self._configDict[key]

    @property
    def configDict(self):
        return self._configDict

    def addFolder(self, path: str):
        """Add a folder to preferences."""
        logger.info(f"{path}")

        # add if not in recentFolders
        if not path in self.configDict["recentFolders"]:
            self.configDict["recentFolders"].append(path)
            # limit list to last _maxNumUndo
            self.configDict["recentFolders"] = self.configDict["recentFolders"][
                -self._maxRecent :
            ]

        # always set as the most recent folder
        self.configDict["mostRecentFolder"] = path

    def addPlugin(self, pluginName: str, externalWindow: bool, ltwhTuple: tuple):
        """Add plugin to preferences."""
        # was this as list
        # if not pluginName in self.configDict['pluginPanels']:
        #     self.configDict['pluginPanels'].append(pluginName)
        if not pluginName in self.configDict["pluginPanels"].keys():
            self.configDict["pluginPanels"][pluginName] = {
                "externalWindow": externalWindow,
                "l": ltwhTuple[0],
                "t": ltwhTuple[1],
                "w": ltwhTuple[2],
                "h": ltwhTuple[3],
            }

    def removePlugin(self, pluginName: str):
        """Remove plugin from preferences."""
        # was this as list
        # if pluginName in self.configDict['pluginPanels']:
        #     self.configDict['pluginPanels'].remove(pluginName)
        if pluginName in self.configDict["pluginPanels"].keys():
            self.configDict["pluginPanels"].pop(pluginName)

    def getMostRecentFolder(self):
        return self.configDict["mostRecentFolder"]

    def getRecentFolder(self):
        return self.configDict["recentFolders"]

    def preferencesSet(self, key1, key2, val):
        """Set a preference. See `getDefaults()` for key values."""
        try:
            self._configDict[key1][key2] = val

            # actually show hide some widgets
            # if key1=='display' and key2=='showScatter':
            #    if val:
            #        self.myScatterPlotWidget.show()
            #    else:
            #        self.myScatterPlotWidget.hide()

            # if key1=='display' and key2=='showErrors':
            #    if val:
            #        self.myErrorTable.show()
            #    else:
            #        self.myErrorTable.hide()

        except KeyError as e:
            logger.error(f'Did not set preference with keys "{key1}" and "{key2}"')

    def preferencesGet(self, key1, key2):
        """Get a preference. See `getDefaults()` for key values."""
        try:
            return self._configDict[key1][key2]
        except KeyError as e:
            logger.error(f'Did not get preference with keys "{key1}" and "{key2}"')

    def getPreferencesFile(self):
        userPreferencesFolder = sanpy._util._getUserPreferencesFolder()
        optionsFile = pathlib.Path(userPreferencesFolder) / "sanpy_preferences.json"
        return optionsFile

    def load(self):
        """
        Always load preferences from:
            <user>/Documents/SanPy/preferences/sanpy_preferences.json
        """

        preferencesFile = self.getPreferencesFile()

        useDefault = True
        if os.path.isfile(preferencesFile):
            logger.info(f"Loading preferences file")
            logger.info(f"  {preferencesFile}")
            try:
                with open(preferencesFile) as f:
                    loadedJson = json.load(f)
                    loadedVersion = loadedJson["version"]
                    logger.info(f"  loaded preferences version {loadedVersion}")
                    if loadedVersion < self._version:
                        # use default
                        logger.warning(
                            "  older version found, reverting to current defaults"
                        )
                        logger.warning(
                            f"  loadedVersion:{loadedVersion} currentVersion:{self._version}"
                        )
                        pass
                    else:
                        return loadedJson
            except JSONDecodeError as e:
                logger.error(e)
            except TypeError as e:
                logger.error(e)
        if useDefault:
            logger.info(f"Using default options")
            return self.getDefaults()

    def getDefaults(self) -> dict:
        """Get default preferences.

        Be sure to increment self._version when making changes.
        """
        configDict = {}  # OrderedDict()

        configDict["version"] = self._version
        configDict["useDarkStyle"] = True
        configDict[
            "autoDetect"
        ] = True  # FALSE DOES NOT WORK!!!! auto detect on file selection and/or sweep selection

        configDict["recentFolders"] = []
        configDict["mostRecentFolder"] = ""

        configDict["windowGeometry"] = {}
        configDict["windowGeometry"]["x"] = 100
        configDict["windowGeometry"]["y"] = 100
        configDict["windowGeometry"]["width"] = 1000
        configDict["windowGeometry"]["height"] = 1000

        configDict["filePanels"] = {}
        configDict["filePanels"]["File Panel"] = True

        # panels withing detectionWidget -> myDetectionToolbar
        configDict["detectionPanels"] = {}
        configDict["detectionPanels"]["Detection Panel"] = True  # main panel
        configDict["detectionPanels"]["Detection"] = True
        configDict["detectionPanels"]["Display"] = True
        configDict["detectionPanels"]["Plot Options"] = False
        configDict["detectionPanels"]["Set Spikes"] = False
        configDict["detectionPanels"]["Set Meta Data"] = False

        # plugins to show at startup
        # 20230325 convert from List[str] to dict
        configDict["pluginPanels"] = {}

        # values in detectionWidget -> myDetectionToolbar
        configDict["detect"] = {}
        configDict["detect"]["detectDvDt"] = 20
        configDict["detect"]["detectMv"] = -20

        # display options within detectionWidget -> myDetectionToolbar
        configDict["rawDataPanels"] = {}
        configDict["rawDataPanels"]["plotEveryPoint"] = 10  # not used?
        configDict["rawDataPanels"]["Full Recording"] = False  #
        configDict["rawDataPanels"]["Derivative"] = True  #
        configDict["rawDataPanels"]["DAC"] = False  #

        configDict['fileList'] = {}
        configDict['fileList']['Folder Depth'] = 1

        return configDict

    def save(self):
        preferencesFile = self.getPreferencesFile()

        logger.info(f'Saving preferences file as: "{preferencesFile}"')

        # get the current position and size of the main window
        left, top, width, height = self._sanpyApp.getWindowGeometry()

        self._configDict["windowGeometry"]["x"] = left
        self._configDict["windowGeometry"]["y"] = top
        self._configDict["windowGeometry"]["width"] = width
        self._configDict["windowGeometry"]["height"] = height

        # TODO: extend to a list
        # self._configDict['lastPath'] = self._sanpyApp.path

        # TODO: get window position and size of all open plugins
        # self.configDict['pluginPanels'][pluginName] = {'externalWindow': externalWindow,
        #                                                    'l': ltwhTuple[0],
        #                                                    't': ltwhTuple[1],
        #                                                    'w': ltwhTuple[2],
        #                                                    'h': ltwhTuple[3],
        #                                                    }
        _openSet = self._sanpyApp.myPlugins._openSet
        for _onePlugin in _openSet:
            pluginName = _onePlugin.myHumanName
            ltwhTuple = _onePlugin.getWindowGeometry()
            self.configDict["pluginPanels"][pluginName]["l"] = ltwhTuple[0]
            self.configDict["pluginPanels"][pluginName]["t"] = ltwhTuple[1]
            self.configDict["pluginPanels"][pluginName]["w"] = ltwhTuple[2]
            self.configDict["pluginPanels"][pluginName]["h"] = ltwhTuple[3]

        #
        # save
        with open(preferencesFile, "w") as outfile:
            json.dump(self._configDict, outfile, indent=4, sort_keys=True)

        self._sanpyApp.slot_updateStatus("Saved preferences")
