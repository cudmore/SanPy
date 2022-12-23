"""
Implement a base class so users can add additional analysis.

Author: Robert Cudmore

Date: 20210929
"""
import glob
import importlib
import inspect
import os
import traceback  # to print call stack on exception
import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

# TODO: put this in _util.py
def _module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def getObjectList(verbose = False):
    """
    Return a list of classes defined in sanpy.userAnalysis.

    Each of these is an object we can (i) construct or (ii) interrogate statis class members
    """

    verbose = False
    
    if verbose:
        logger.info('')

    #
    # user plugins from files in folder <user>/SanPy/analysis
    userAnalysisFolder = sanpy._util._getUserAnalysisFolder()
    files = glob.glob(os.path.join(userAnalysisFolder, '*.py'))

    pluginDict = {}

    loadedModuleList = []

    for file in files:
        if file.endswith('__init__.py'):
            continue

        moduleName = os.path.split(file)[1]
        moduleName = os.path.splitext(moduleName)[0]
        fullModuleName = 'sanpy.user_analysis.' + moduleName  # + "." + moduleName

        loadedModule = _module_from_file(fullModuleName, file)

        if verbose:
            logger.info('')
            logger.info(f'    file: {file}')
            logger.info(f'    fullModuleName: {fullModuleName}')
            logger.info(f'    moduleName: {moduleName}')
            logger.info(f'    loadedModule: {loadedModule}')

        # 1) class based user analysis
        oneConstructor = None
        try:
            oneConstructor = getattr(loadedModule, moduleName)  # moduleName is derived from file name (must match)
            if verbose:
                logger.info(f'    oneConstructor: {oneConstructor}')
                logger.info(f'    type(oneConstructor): {type(oneConstructor)}')
        except (AttributeError) as e:
            logger.error(f'Make sure filename and class name are the same,  file name is "{moduleName}"')

        # 2) function based user analysis
        oneStatDict = None
        oneRunFunction = None
        try:
            oneRunFunction = getattr(loadedModule, 'exampleFunction_xxx')  # moduleName is derived from file name (must match)
            oneStatDict = getattr(loadedModule, 'exampleStatDict_xxx')  # moduleName is derived from file name (must match)
        except (AttributeError) as e:
            pass
            #logger.error(f'Make sure filename and class name are the same,  file name is "{moduleName}"')
        
        # 20220630, get the static stat attribute from the class
        _statStatDict = getattr(oneConstructor, 'userStatDict')
        #print('_statStatDict:', _statStatDict)

        #humanName = oneConstructor.myHumanName
        pluginDict = {
            'pluginClass': moduleName,
            'type': 'user',
            'module': fullModuleName,
            'path': file,
            'constructor': oneConstructor,
            'staticStatDict': _statStatDict,
            #
            # experimental, trying to use functions rather than class
            'runFunction': oneRunFunction,
            'statDict': oneStatDict,
            #'humanName': humanName
            }

        # assuming user analysis is unique
        # if humanName in self.pluginDict.keys():
        #     logger.warning(f'Plugin already added "{moduleName}" humanName:"{humanName}"')
        # else:
        #     logger.info(f'loading user plugin: "{file}"')
        #     #self.pluginDict[moduleName] = pluginDict
        #     self.pluginDict[humanName] = pluginDict
        #     loadedModuleList.append(moduleName)

        if verbose:
            logger.info(f'loading user analysis from file: "{file}"')
        
        #pluginDict[humanName] = pluginDict
        
        loadedModuleList.append(pluginDict)

    # print out the entire list
    logger.info('')
    for loadedModuleDict in loadedModuleList:
        for k,v in loadedModuleDict.items():
            logger.info(f'    {k} : {v}')
    #
    return loadedModuleList  # list of dict

    #
    # OLD
    """
    ignoreModuleList = ['baseUserAnalysis']

    objList = []
    #userStatDict = {}
    for moduleName, obj in inspect.getmembers(sanpy.userAnalysis):
        #print('moduleName:', moduleName, 'obj:', obj)
        if inspect.isclass(obj):
            if moduleName in ignoreModuleList:
                continue
            print(f'  is class moduleName {moduleName} obj:{obj}')
            # obj is a constructor function
            # <class 'sanpy.userAnalysis.userAnalysis.exampleUserAnalysis'>
            print('  ', obj.userStatDict)

            # from findUserAnalysis
            '''
            oneStatDict = obj.userStatDict
            for k,v in oneStatDict.items():
                userStatDict[k] = {}
                userStatDict[k]['name'] = v['name']
            '''
            objList.append(obj)  # obj is a class constructor

    #
    return objList
    """

def broken_findUserAnalysis():
    """
    20220630 is BROKEN !!!
    Find files in 'sanpy/userAnalysis' and populate a dict with stat names
    this will be appended to bAnalysisUtil.statList
    """

    logger.info('')

    ignoreModuleList = ['baseUserAnalysis']

    userStatDict = {}
    for moduleName, obj in inspect.getmembers(sanpy.user_analysis):
        #print('moduleName:', moduleName, 'obj:', obj)
        if inspect.isclass(obj):
            if moduleName in ignoreModuleList:
                continue
            print(f' is class moduleName {moduleName} obj:{obj}')
            # obj is a constructor function
            # <class 'sanpy.userAnalysis.userAnalysis.exampleUserAnalysis'>
            print('  ', obj.userStatDict)
            oneStatDict = obj.userStatDict
            for k,v in oneStatDict.items():
                userStatDict[k] = {}
                userStatDict[k]['name'] = v['name']

    #
    return userStatDict

def runAllUserAnalysis(ba, verbose=False):
    """
    call at end of bAnalysis
    """

    # step through each
    objList = getObjectList()  # list of dict

    if verbose:
        logger.info(f'objList: {objList}')
    for obj in objList:
        # instantiate and call run (will add values for stats
        # was this
        #userObj = obj(ba)
        #userObj.run()

        try:
            # instantiate a user object
            userObj = obj['constructor'](ba)

            # run the analysis
            userObj.run()  # run the analysis and append to actual ba object
        except (Exception) as e:
            logger.error(f'Exception in running user defined analysis: {e}')
            logger.error(traceback.format_exc())

class baseUserAnalysis:
    """
    Create a userAnalysis object after bAnalysis has been analyzed with the core analysis results.
    """
    userStatDict = {}
    """User needs to fill this in see xxx for example"""

    def __init__(self, ba):
        self._myAnalysis = ba

        self._installStats()

    def _installStats(self, verbose=False):
        if verbose:
            logger.info(f'Installing "{self.userStatDict}"')
        for k, v in self.userStatDict.items():
            if verbose:
                logger.info(f'{k}: {v}')
            name = v['name']
            self.addKey(name, theDefault=None)

    @property
    def ba(self):
        """Get the underlying sanpy.bAnalysis object"""
        return self._myAnalysis

    def getSweepX(self):
        """Get the x-axis of a recording."""
        return self.ba.sweepX

    def getSweepY(self):
        """Get the y-axis of a recording."""
        return self.ba.sweepY

    def getSweepC(self):
        """Get the DAC axis of a recording."""
        return self.ba.sweepC

    def getFilteredVm(self):
        return self.ba.filteredVm

    def addKey(self, theKey, theDefault=None):
        """Add a new key to analysis results.

        Will add key to each spike in self.ba.spikeDict
        """
        self.ba.spikeDict.addAnalysisResult(theKey, theDefault)

    def setSpikeValue(self, spikeIdx, theKey, theVal):
        """
        Set the value of a spike key.

        Args:
            spikeIdx (int): The spike index , 0 based.
            theKey (str): Name of the key.
            theVal (): The value for the key, can be almost any type like
                        (float, int, bool, dict, list)

        Raises:
            KeyError: xxx.
            IndexError: xxx.
        """
        self.ba.spikeDict[spikeIdx][theKey] = theVal

    def getSpikeValue(self, spikeIdx, theKey):
        """
        Get a single spike analysis result from key.

        Args:
            spikeIdx (int): The spike index, 0 based
            theKey (str): xxx

        Raises:
            KeyError: If theKey is not a key in analysis results.
            IndexError: If spikeIdx is beyond number of spikes -1.
        """
        try:
            theRet = self.ba.spikeDict[spikeIdx][theKey]
            return theRet
        except (KeyError) as e:
            print(e)
        except (IndexError) as e:
            print(e)

    def run(self):
        """
        Run user analysis. Add a key to analysis results and fill in its values.

        Try not to re-use existing keys
        """

if __name__ == '__main__':
    #test1()
    getObjectList()
