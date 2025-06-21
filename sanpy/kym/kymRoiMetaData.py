import os
from typing import List, Optional, Any
import json

import numpy as np

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class KymRoiMetaData():
    def __init__(self, path : str,
                 imgData : List[np.ndarray] = None) -> None:
        
        folder, filename = os.path.split(path)

        parentFolder1 = os.path.split(folder)[1]
        _parentFolder1 = os.path.split(folder)[0]
        parentFolder2 = os.path.split(_parentFolder1)[1]

        self._dict = {
            # user can edit these, see allowTextEdit()
            'Animal ID' : '',
            'Region' : '',
            'Cell Type' : '',
            'Condition 1' : '',
            'Note 1' : '',
            'Note 2' : '',
            'Note 3' : '',
            
            # not editable
            'path' : path,
            'File Name' : filename,
            'Parent Folder 1' : parentFolder1,
            'Parent Folder 2' : parentFolder2,
            'Acq Date': '',
            'Acq Time': '',
            'secondsPerLine' : None,
            'umPerPixel' : None,
            'numChannels' : 0 if imgData is None else len(imgData),
            'imageHeight' : 0 if imgData is None else imgData[0].shape[0],  # number of pixels in each line scan
            'imageWidth' : 0 if imgData is None else imgData[0].shape[1],  # number of line scans
        }
    
        self._allowEdit = ['Animal ID', 'Region', 'Cell Type', 'Condition 1', 'Condition 2']
        """Keys that are editable in qt dialog.
        """

        self._doNotShowInGui = 'path'
        """Keys to not show in GUI.
        """

    def setParam(self, key, value) -> bool:
        try:
            self._dict[key] = value
            return True
        except (KeyError):
            logger.error(f'did not set "{key}", available keys are {self._dict.keys()}')
            return False
        
    def getParam(self, key) -> Optional[Any]:
        try:
            return self._dict[key]
        except (KeyError):
            logger.error(f'did not set "{key}", available keys are {self._dict.keys()}')
        return None

    def showInGui(self, key):
        """Return True if we show in Qt gui.
        """
        return key not in self._doNotShowInGui
    
    def allowTextEdit(self, key):
        """Return True if we edit a str in the gui.
        """
        return key in self._allowEdit
    
    def toJson(self):
        _ret = json.dumps(self._dict)
        return _ret
    
    def fromJson(self,jsonStr):
        _dict = json.loads(jsonStr)
        for k,v in _dict.items():
            self.setParam(k, v)

    @classmethod
    def fromDict(cls, _dict):
        """Create a KymRoiMetaData instance from a dictionary.
        
        Parameters
        ----------
        _dict : dict
            Dictionary containing metadata values
            
        Returns
        -------
        KymRoiMetaData
            New instance with values from the dictionary
        """
        # Extract required parameters for __init__
        path = _dict.get('path', '')
        
        # Create the instance with optional imgData (None is now allowed)
        instance = cls(path, imgData=None)
        
        # Set all the dictionary values
        for k, v in _dict.items():
            instance.setParam(k, v)
            
        return instance

    def __setitem__(self, key, value) -> bool:
        return self.setParam(key, value)

    def __getitem__(self, key) -> Optional[Any]:
        return self.getParam(key)
    
    def items(self):
        return self._dict.items()