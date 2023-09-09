# 20210610

import os
import sys

# import pathlib
import glob
import importlib
import inspect

from typing import Union, Dict, List, Tuple, Optional

import sanpy

# import sanpy.interface
import sanpy.interface.plugins

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class bPlugins:
    """Generate a dict of plugins.

    Populate the dict by looking in
        - package, sanpy.interface.plugins
        - folder, <user>/sanpy_plugins
    """

    def __init__(self, sanpyApp: Optional["sanpy.interface.SanPyWindow"] = None):
        self._sanpyApp = sanpyApp

        self.userPluginFolder: str = sanpy._util._getUserPluginFolder()
        if not os.path.isdir(self.userPluginFolder):
            self.userPluginFolder = None
        """path to <user>/plugin_dir"""

        self.pluginDict = {}
        """dict of pointers to open plugins"""

        self._openSet = set()
        """set of open plugins"""

        self.loadPlugins()

    def getSanPyApp(self) -> Optional["sanpy.interface.SanPyWindow"]:
        """Get the underlying SanPy app."""
        return self._sanpyApp

    def loadPlugins(self):
        """Load plugins from both:
         - Package: sanpy.interface.plugins
         - Folder: <user>/sanpy_plugins

        See: sanpy.fileLoaders.fileLoader_base.getFileLoader()
        """
        self.pluginDict = {}

        # Enum is to ignore bPlugins.py class ResponseType(Enum)
        ignoreModuleList = [
            "sanpyPlugin",
            "myWidget",
            "ResponseType",
            "SpikeSelectEvent",
            "basePlotTool",
            "NavigationToolbar2QT",
            "myStatListWidget",
        ]

        #
        # system plugins from sanpy.interface.plugins
        # print('loadPlugins sanpy.interface.plugins:', sanpy.interface.plugins)
        loadedList = []
        for moduleName, obj in inspect.getmembers(sanpy.interface.plugins):
            # print('moduleName:', moduleName, 'obj:', obj)
            if inspect.isclass(obj):
                # logger.info(f'moduleName: {moduleName}')
                if moduleName in ignoreModuleList:
                    # our base plugin class
                    continue
                loadedList.append(moduleName)
                fullModuleName = "sanpy.interface.plugins." + moduleName
                humanName = obj.myHumanName  # myHumanName is a static str
                showInMenu = obj.showInMenu  # showInMenu is a static bool
                pluginDict = {
                    "pluginClass": moduleName,
                    "type": "system",
                    "module": fullModuleName,
                    "path": "",
                    "constructor": obj,
                    "humanName": humanName,
                    "showInMenu": showInMenu,
                }
                if humanName in self.pluginDict.keys():
                    logger.warning(
                        f'Plugin already added "{moduleName}" humanName:"{humanName}"'
                    )
                else:
                    self.pluginDict[humanName] = pluginDict

        # print the loaded plugins
        logger.info(f"Loaded plugins:")
        for loaded in loadedList:
            logger.info(f"    {loaded}")
        # sort
        self.pluginDict = dict(sorted(self.pluginDict.items()))

        #
        # user plugins from files in folder <user>/SanPy/plugins
        loadedModuleList = []
        if self.userPluginFolder is not None:
            files = glob.glob(os.path.join(self.userPluginFolder, "*.py"))
        else:
            files = []

        for file in files:
            if file.endswith("__init__.py"):
                continue

            moduleName = os.path.split(file)[1]
            moduleName = os.path.splitext(moduleName)[0]
            fullModuleName = "sanpy.interface.plugins." + moduleName

            loadedModule = self._module_from_file(fullModuleName, file)

            try:
                oneConstructor = getattr(loadedModule, moduleName)
            except AttributeError as e:
                logger.error(
                    f'Did not load user plugin, make sure file name and class name are the same:"{moduleName}"'
                )
            else:
                humanName = oneConstructor.myHumanName
                showInMenu = oneConstructor.showInMenu
                pluginDict = {
                    "pluginClass": moduleName,
                    "type": "user",
                    "module": fullModuleName,
                    "path": file,
                    "constructor": oneConstructor,
                    "humanName": humanName,
                    "showInMenu": showInMenu,
                }
                if humanName in self.pluginDict.keys():
                    logger.warning(
                        f'Plugin already added "{moduleName}" humanName:"{humanName}"'
                    )
                else:
                    self.pluginDict[humanName] = pluginDict
                    loadedModuleList.append(moduleName)

        # print the loaded plugins
        logger.info(f"Loaded {len(loadedModuleList)} user plugin(s)")
        for loaded in loadedModuleList:
            logger.info(f"    {loaded}")

    def runPlugin(self, pluginName: str, ba: sanpy.bAnalysis, show: bool = True):
        """Run one plugin with given a bAnalysis.

        Args:
            pluginName (str):
            ba (bAnalysis): object
            show:
        """
        if not pluginName in self.pluginDict.keys():
            logger.error(f'Did not find plugin: "{pluginName}"')
            return
        else:
            humanName = self.pluginDict[pluginName]["constructor"].myHumanName

            ltwhTuple = None

            # get the visible x-axis from main app
            startStop = None
            app = self.getSanPyApp()
            _pluginDict = None
            if app is not None:
                startSec = app.startSec
                stopSec = app.stopSec
                if startSec is None and stopSec is None:
                    startStop = None
                else:
                    startStop = [startSec, stopSec]

                # has keys for (l, t, w, h)
                _pluginDict = app.getOptions().preferencesGet("pluginPanels", humanName)
                # ltwhTuple = None
                # if _pluginDict is not None:
                #     ltwhTuple = tuple(
                #         _pluginDict['l'],
                #         _pluginDict['t'],
                #         _pluginDict['w'],
                #         _pluginDict['h'],
                #     )
            logger.info(f"Running plugin:")
            logger.info(f"  pluginName:{pluginName}")
            logger.info(f"  humanName:{humanName}")
            logger.info(f"  startStop:{startStop}")
            if _pluginDict is not None:
                logger.info(f"  _pluginDict:{_pluginDict}")
            logger.info(f"  TODO: put try except back in !!!")
            # TODO: to open PyQt windows, we need to keep a local (persistent) variable
            # try:
            if 1:
                # print(1)
                newPlugin = self.pluginDict[pluginName]["constructor"](
                    ba=ba, bPlugin=self, startStop=startStop
                )
                # print(2)
                if not newPlugin.getInitError() and show:
                    if _pluginDict is not None:
                        newPlugin.setGeometry(
                            _pluginDict["l"],
                            _pluginDict["t"],
                            _pluginDict["w"],
                            _pluginDict["h"],
                        )
                    newPlugin.getWidget().show()
                    newPlugin.getWidget().setVisible(True)
                    # newPlugin.getWidget().raise_()  # bring to front, raise is a python keyword
                    # newPlugin.getWidget().activateWindow()  # bring to front

                else:
                    newPlugin.getWidget().hide()
                    newPlugin.getWidget().setVisible(False)

                # add the plugin to open next time we run

            # except(TypeError) as e:
            #     logger.error(f'Error opening plugin "{pluginName}": {e}')
            #     return
            if not newPlugin.getInitError():
                self._openSet.add(newPlugin)

            return newPlugin

    def getType(self, pluginName):
        """
        returns one of ('system', 'user')
        """
        if not pluginName in self.pluginDict.keys():
            logger.error(f'Did not find plugin: "{pluginName}"')
            return None
        else:
            theRet = self.pluginDict[pluginName]["type"]
            return theRet

    def pluginList(self, forMenu=True):
        """Get list of names of loaded plugins

        Pay attention to showInMenu
        """
        retList = []
        for k, v in self.pluginDict.items():
            # k is the name of the plugin
            # v is a dict with its current state
            # print(' QANON ', k)
            # print('     v:', v)
            if not v["showInMenu"]:
                continue
            retList.append(k)
        return retList

    def getHumanNames(self):
        retList = []
        for k, v in self.pluginDict.items():
            myHumanName = v["myHumanName"]
            retList.append(myHumanName)
        return retList

    def _module_from_file(self, module_name: str, file_path: str):
        """

        Args:
            module_name: Is like sanpy.interface.plugins.onePluginFile
            file_path: Full path to onePluginFile source code (onePluginFile.py)
        """
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def slot_closeWindow(self, pluginObj):
        """Close named plugin window.

        Args:
            pluginObj (object): The running plugin object reference.

        Important:
            Need to disconnect signal/slot using _disconnectSignalSlot().
            Mostly connections to main SanPy app signals
        """
        # logger.info(pluginObj)
        try:
            logger.info(f'Removing plugin from _openSet: "{pluginObj.getHumanName()}"')
            # Critical to detatch signal/slot, removing from set does not seem to do this?
            pluginObj._disconnectSignalSlot()
            self._openSet.remove(pluginObj)

            # remove from preferences
            if pluginObj is not None and self.getSanPyApp() is not None:
                self.getSanPyApp().configDict.removePlugin(pluginObj.getHumanName())

        except KeyError as e:
            logger.exception(e)

    def _old_slot_selectSpike(self, sDict):
        """
        On user selection of spike in a plugin

        Tell main app to select a spike everywhere
        """
        logger.info(sDict)
        app = self.getSanPyApp()
        if app is not None:
            spikeNumber = sDict["spikeNumber"]
            doZoom = sDict["doZoom"]
            app.selectSpike(spikeNumber, doZoom=doZoom)

    def _old_slot_selectSpikeList(self, sDict: dict):
        """On user selection of spike(s) in a plugin

        Tell main app to select a spike everywhere

        Args:
            sDict (dict) with keys
                spikeList : List[int]
                doZoom : bool
                ba : sanpy.bAnalysis_.bAnalysis
        """
        logger.info(sDict)
        app = self.getSanPyApp()
        if app is not None:
            spikeList = sDict["spikeList"]
            doZoom = sDict["doZoom"]
            app.selectSpikeList(spikeList, doZoom=doZoom)


def test_print_classes():
    """testing"""
    print("__name__:", __name__)
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            print(name, ":", obj)

    print("===")
    for name, obj in inspect.getmembers(sanpy.interface.plugins):
        if inspect.isclass(obj):
            print(name, ":", obj)


if __name__ == "__main__":
    # print_classes()
    # sys.exit(1)

    bp = bPlugins()

    pluginList = bp.pluginList()
    print("pluginList:", pluginList)

    abfPath = "/Users/cudmore/Sites/SanPy/data/19114001.abf"
    ba = sanpy.bAnalysis(abfPath)

    bp.runPlugin("plotRecording", ba)
    # bp.runPlugin('plotRecording3', ba)
