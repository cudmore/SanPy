import glob
import importlib

# import inspect
import os
import traceback  # to print call stack on exception
import inspect
from typing import List, Union

import sanpy

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


# TODO: put this in _util.py
def _module_from_file(module_name, file_path):
    """Load a module from a file.

    Parameters
    ----------
    module_name : str
        Name of the module.
    file_path : str
        Full path to the file

    Returns
    -------
    module
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _getObjectList(verbose=True) -> List[dict]:
    """Return a list of classes defined in sanpy.userAnalysis.

    Each of these is an object we can (i) construct or (ii) interrogate statis class members

    Returns
    -------
    list of dict
    """

    if verbose:
        logger.info("")
  
    #
    # user plugins from files in folder <user>/SanPy/analysis
    userAnalysisFolder = sanpy._util._getUserAnalysisFolder()
    files = glob.glob(os.path.join(userAnalysisFolder, "*.py"))

    pluginDict = {}
    loadedModuleList = []

    for file in files:
        if file.endswith("__init__.py"):
            continue

        if file == 'baseUserAnalysis.py':
            continue

        moduleName = os.path.split(file)[1]
        moduleName = os.path.splitext(moduleName)[0]
        fullModuleName = "sanpy.user_analysis." + moduleName  # + "." + moduleName

        loadedModule = _module_from_file(fullModuleName, file)

        if verbose:
            logger.info("")
            logger.info(f"    file: {file}")
            logger.info(f"    fullModuleName: {fullModuleName}")
            logger.info(f"    moduleName: {moduleName}")
            logger.info(f"    loadedModule: {loadedModule}")

        # class based user analysis
        oneConstructor = None
        try:
            oneConstructor = getattr(
                loadedModule, moduleName
            )  # moduleName is derived from file name (must match)
            if verbose:
                logger.info(f"    oneConstructor: {oneConstructor}")
                logger.info(f"    type(oneConstructor): {type(oneConstructor)}")
        except AttributeError as e:
            logger.error(
                f'Make sure filename and class name are the same,  file name is "{moduleName}"'
            )

        # instantiate the object and it will create a dictionary of new stats
        _tmpObj = oneConstructor(ba=None)
        _statStatDict = _tmpObj._getUserStatDict()

        # humanName = oneConstructor.myHumanName
        pluginDict = {
            "pluginClass": moduleName,
            "type": "user",
            "module": fullModuleName,
            "path": file,
            "constructor": oneConstructor,
            "staticStatDict": _statStatDict,
        }

        if verbose:
            logger.info(f'  loading user analysis from file: "{file}"')

        loadedModuleList.append(pluginDict)

    # new, june 2023, get from user_analysis folder as well
    logger.info('fetching user analysis from course code folder sanpy.user_analysis')
    for moduleName, obj in inspect.getmembers(sanpy.user_analysis):
        if inspect.isclass(obj):
            # print('moduleName:', moduleName, 'obj:', obj)
            # moduleName: kymUserAnalysis obj: <class 'sanpy.user_analysis.userKymDiamAnalysis.kymUserAnalysis'>
            fullModuleName = "sanpy.user_analysis." + moduleName

            # instantiate the object and it will create a dictionary of new stats
            _tmpObj = obj(ba=None)
            _statStatDict = _tmpObj._getUserStatDict()

            pluginDict = {
                "pluginClass": moduleName,
                "type": "user_analysis",
                "module": fullModuleName,
                "path": 'not_used',
                "constructor": obj,
                "staticStatDict": _statStatDict,
            }

            if verbose:
                logger.info(f' loading user analysis from user_analysis: "{moduleName}"')

            loadedModuleList.append(pluginDict)
          
    # print out the entire list
    # logger.info('')
    # for loadedModuleDict in loadedModuleList:
    #     for k,v in loadedModuleDict.items():
    #         logger.info(f'    {k} : {v}')
    #
    return loadedModuleList  # list of dict


def findUserAnalysisStats() -> List[dict]:
    """Get the stat names of all user defined analysis."""
    userStatList: List[dict] = []
    objList = _getObjectList()  # list of dict
    for obj in objList:
        # sanpy._util.pprint(obj)
        # print('')

        # instantiate the object
        userObj = obj["constructor"](ba=None)

        userObjStatDict = userObj._getUserStatDict()

        for k, v in userObjStatDict.items():
            oneUserStatDict = {k: v}
            userStatList.append(oneUserStatDict)

    return userStatList


def runAllUserAnalysis(ba, verbose=False):
    """Run all user defined analysis.

    Notes
    -----
    Called at end of sanpy.bAnalysis.detect()
    """

    # step through each
    objList = _getObjectList()  # list of dict

    if verbose:
        logger.info(f"objList: {objList}")
    for obj in objList:
        # instantiate and call run (will add values for stats
        # was this
        # userObj = obj(ba)
        # userObj.run()

        try:
            # instantiate a user object
            userObj = obj["constructor"](ba)

            # run the analysis
            userObj.run()  # run the analysis and append to actual ba object
        except Exception as e:
            logger.error(f"Exception in running user defined analysis: {e}")
            logger.error(traceback.format_exc())


class baseUserAnalysis:
    """Create a userAnalysis object after bAnalysis has been analyzed with the core analysis results."""

    def __init__(self, ba: "sanpy.bAnalysis"):
        self._myAnalysis: sanpy.bAnalysis = ba

        self._userStatDict: dict = {}
        # add to this with addUserStat()

        self.defineUserStats()

    def _getUserStatDict(self):
        """Get dict of user defined stats, one key per stat."""
        return self._userStatDict

    def defineUserStats(self):
        """Derived classes add each stat with addUserStat().

        See Also
        --------
        addUserStat
        """
        pass

    def addUserStat(self, humanName: str, internalName: str):
        """Add a user stat. Derived classes do this in defineUserStats().

        Parameters
        ----------
        humanName : str
            Human readable name for the stat, like 'Threshold Potential (mV)'
        internalName : str
            Name to use for the variable name of the stat.
            Should not contain special characters like space or '-'
            Can contain '_'

        Notes
        -----
        userStatDict = {
            'User Time To Peak (ms)' : {
                'name': 'user_timeToPeak_ms',
                'units': 'ms',
                'yStat': 'user_timeToPeak_ms',
                'yStatUnits': 'ms',
                'xStat': 'thresholdPnt',
                'xStatUnits': 'Points'
                }
        }
        """
        if humanName in self._userStatDict.keys():
            # logger.error(f'User stat with human name "{humanName}" already exists')
            return
        statDict = {
            "name": internalName,
            "units": None,
            "yStat": None,
            "yStatUnits": None,
            "xStat": None,
            "xStatUnits": None,
        }
        self._userStatDict[humanName] = statDict

    @property
    def ba(self):
        """Get the underlying [sanpy.bAnalysis][sanpy.bAnalysis] object"""
        return self._myAnalysis

    def getSweepX(self):
        """Get the x-axis of a recording."""
        return self.ba.fileLoader.sweepX

    def getSweepY(self):
        """Get the y-axis of a recording."""
        return self.ba.fileLoader.sweepY

    def getSweepC(self):
        """Get the DAC axis of a recording."""
        return self.ba.fileLoader.sweepC

    def getFilteredVm(self):
        return self.ba.fileLoader.sweepY_filtered

    def setSpikeValue(self, spikeIdx, theKey, theVal):
        """Set the value of a spike key.

        Parameters
        ----------
        spikeIdx : int
            The spike index , 0 based.
        theKey : str
            Name of the user defined internal name.
        theVal :
            The value for the key, can be almost any type like
            (float, int, bool, dict, list)

        Raises
        ------
        KeyError
            If theKey is not a key in analysis results.
        IndexError
            If spikeIdx is beyond number of spikes -1.
        """
        try:
            self.ba.spikeDict[spikeIdx][theKey] = theVal
        except KeyError as e:
            logger.error(f'User internal stat does not exist "{theKey}"')
        except IndexError as e:
            logger.error(
                f"spikeIdx {spikeIdx} is out of range, max value is {self.ba.numSpikes}"
            )

    def getSpikeValue(self, spikeIdx, theKey):
        """Get a single spike analysis result from key.

        Parameters
        ----------
        spikeIdx : int
            The spike index, 0 based.
        theKey : str
            Name of the analysis result defined internal name.

        Raises
        ------
        KeyError
            If theKey is not a key in analysis results.
        IndexError
            If spikeIdx is beyond number of spikes -1.
        """
        try:
            theRet = self.ba.spikeDict[spikeIdx][theKey]
            return theRet
        except KeyError as e:
            logger.error(f'User internal stat does not exist "{theKey}"')
        except IndexError as e:
            logger.error(
                f"spikeIdx {spikeIdx} is out of range, max value is {self.ba.numSpikes}"
            )

    def run(self):
        """Run user analysis. Calculate values for each new user stat."""


if __name__ == "__main__":
    # test1()
    _getObjectList(verbose=True)
    
    #findUserAnalysisStats()
