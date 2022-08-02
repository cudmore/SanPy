
class fileLoader_base:
    handleExtension : str = 'None'  # define in derived
    
    def __init__(self, path : str):
        """
        
        Args:
            path: File path, will load different derived classes based on extension
        """
        self._paramDict = {
            'path': path,
            'loadError': None,
            'fileType': None,
            'numChannels': None,
            'dataPointsPerMs': None,
            'currentSweep': None,
            'sweepList': None,
            'sweepLengthSec': None,

            'acqDate': None,
            'acqTime': None,
            
            'recordingMode': None,  # recording mode per channel
            'sweepLabelX': None,  # sweep label per channel
            'sweepLabelY': None,  # sweep label per channel
            
        }

    @property
    def path(self):
        """Get the full file path.
        """
        return self._getParam('path')

    def getFilePath(self):
        return self._getParam('path')

    def getFileName(self):
        if self._getParam('path') is None:
            return None
        else:
            return os.path.split(self._getParam('path'))[1]

    def _getParam(self, key : str):
        """Get a parameter, raise key error if not found.
        """
        if key not in self._paramDict.keys():
            errStr = f'_getParam did not find key: "{key}", possible values are {self._paramDict.keys()}')
            raise(KeyError(errStr))
            return
        else:
            return self._paramDict[key]

    def _setParam(self, key : str, value):
        """Set a parameter, raise key error if not found.
        """
        if key not in self._paramDict.keys():
            errStr = f'_setParam did not find key: "{key}", possible values are {self._paramDict.keys()}')
            raise(KeyError(errStr))
            return
        else:
            self._paramDict[key] = value
