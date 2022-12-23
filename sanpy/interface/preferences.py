import os
import pathlib
import json
from json.decoder import JSONDecodeError

import sanpy
import sanpy.interface
import sanpy.interface.sanpy_app as sanpy_app

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class preferences():
    """
    Class to hold GUI preferences. Created and used by app SanPyWindow.

    Created: 20220629
    """
    def __init__(self, sanpyApp : sanpy_app):
        super().__init__()
        self._sanpyApp = sanpyApp
        self._version = 1.2  # increment when we change preferences
        self._maxRecent = 7  # a lucky number
        self._configDict = self.load()

    def __setitem__(self, key, item):
        self._configDict[key] = item

    def __getitem__(self, key):
        return self._configDict[key]

    @property
    def configDict(self):
        return self._configDict
    
    def addFolder(self, path : str):
        """Add a folder to preferences.
        """
        logger.info(f'{path}')
        
        # add if not in recentFolders
        if not path in self.configDict['recentFolders']:
            self.configDict['recentFolders'].append(path)
            # limit list to last _maxNumUndo 
            self.configDict['recentFolders'] = self.configDict['recentFolders'][-self._maxRecent:] 
    
        # always set as the most recent folder
        self.configDict['mostRecentFolder'] = path

    def addPlugin(self, pluginName : str):
        """Add plugin to preferences.
        """
        if not pluginName in self.configDict['pluginPanels']:
            self.configDict['pluginPanels'].append(pluginName)

    def removePlugin(self, pluginName : str):
        """Remove plugin from preferences.
        """
        if pluginName in self.configDict['pluginPanels']:
            self.configDict['pluginPanels'].remove(pluginName)

    def getMostRecentFolder(self):
        return self.configDict['mostRecentFolder']
        
    def getRecentFolder(self):
        return self.configDict['recentFolders']

    def preferencesSet(self, key1, key2, val):
        """Set a preference. See `getDefaults()` for key values."""
        try:
            self._configDict[key1][key2] = val

            # actually show hide some widgets
            #if key1=='display' and key2=='showScatter':
            #    if val:
            #        self.myScatterPlotWidget.show()
            #    else:
            #        self.myScatterPlotWidget.hide()

            #if key1=='display' and key2=='showErrors':
            #    if val:
            #        self.myErrorTable.show()
            #    else:
            #        self.myErrorTable.hide()

        except (KeyError) as e:
            logger.error(f'Did not set preference with keys "{key1}" and "{key2}"')

    def preferencesGet(self, key1, key2):
        """Get a preference. See `getDefaults()` for key values."""
        try:
            return self._configDict[key1][key2]
        except (KeyError) as e:
            logger.error(f'Did not get preference with keys "{key1}" and "{key2}"')

    def getPreferencesFile(self):
        userPreferencesFolder = sanpy._util._getUserPreferencesFolder()
        optionsFile = pathlib.Path(userPreferencesFolder) / 'sanpy_preferences.json'
        return optionsFile

    def load(self):
        """
        Always load preferences from:
            <user>/Documents/SanPy/preferences/sanpy_preferences.json
        """

        preferencesFile = self.getPreferencesFile()

        useDefault = True
        if os.path.isfile(preferencesFile):
            logger.info(f'Loading preferences file: {preferencesFile}')
            try:
                with open(preferencesFile) as f:
                    loadedJson = json.load(f)
                    loadedVersion = loadedJson['version']
                    logger.info(f'    loaded preferences version {loadedVersion}')
                    if loadedVersion < self._version:
                        # use default
                        logger.warning('    older version found, reverting to current defaults')
                        pass
                    else:
                        return loadedJson
            except (JSONDecodeError) as e:
                logger.error(e)
            except (TypeError) as e:
                logger.error(e)
        if useDefault:
            logger.info(f'Using default options')
            return self.getDefaults()

    def getDefaults(self):
        configDict = {}  # OrderedDict()

        configDict['version'] = self._version
        configDict['useDarkStyle'] = True
        configDict['autoDetect'] = True # FALSE DOES NOT WORK!!!! auto detect on file selection and/or sweep selection

        configDict['recentFolders'] = []
        configDict['mostRecentFolder'] = ''

        configDict['windowGeometry'] = {}
        configDict['windowGeometry']['x'] = 100
        configDict['windowGeometry']['y'] = 100
        configDict['windowGeometry']['width'] = 1000
        configDict['windowGeometry']['height'] = 1000
        
        configDict['filePanels'] = {}
        configDict['filePanels']['File Panel'] = True

        # panels withing detectionWidget -> myDetectionToolbar
        configDict['detectionPanels'] = {}
        configDict['detectionPanels']['Detection Panel'] = True  # main panel
        configDict['detectionPanels']['Detection'] = True
        configDict['detectionPanels']['Display'] = True
        configDict['detectionPanels']['Plot Options'] = False
        
        # plugins to show at startup
        configDict['pluginPanels'] = []

        # values in detectionWidget -> myDetectionToolbar
        configDict['detect'] = {}
        configDict['detect']['detectDvDt'] = 20
        configDict['detect']['detectMv'] = -20

        # display options within detectionWidget -> myDetectionToolbar
        configDict['rawDataPanels'] = {}
        configDict['rawDataPanels']['plotEveryPoint'] = 10 # not used?
        configDict['rawDataPanels']['Full Recording'] = True #
        configDict['rawDataPanels']['Derivative'] = False #
        configDict['rawDataPanels']['DAC'] = False #

        return configDict

    def save(self):
        preferencesFile = self.getPreferencesFile()
        
        logger.info(f'Saving preferences file as: "{preferencesFile}"')

        # myRect = self.geometry()
        # left = myRect.left()
        # top = myRect.top()
        # width = myRect.width()
        # height = myRect.height()

        left, top, width, height = self._sanpyApp.getWindowGeometry()
        
        self._configDict['windowGeometry']['x'] = left
        self._configDict['windowGeometry']['y'] = top
        self._configDict['windowGeometry']['width'] = width
        self._configDict['windowGeometry']['height'] = height

        # TODO: extend to a list
        #self._configDict['lastPath'] = self._sanpyApp.path

        #
        # save
        with open(preferencesFile, 'w') as outfile:
            json.dump(self._configDict, outfile, indent=4, sort_keys=True)
