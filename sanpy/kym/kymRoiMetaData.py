import os
from typing import List, Optional, Any
import json

import numpy as np
import pandas as pd

from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


def get_parent_folders(path):
    folder, _ = os.path.split(path)
    parent = os.path.basename(folder)
    grandparent = os.path.basename(os.path.dirname(folder))
    great_grandparent = os.path.basename(os.path.dirname(os.path.dirname(folder)))
    return parent, grandparent, great_grandparent


class KymRoiMetaData:
    def __init__(self, path: str, imgData: List[np.ndarray] = None) -> None:

        folder, filename = os.path.split(path)

        parentFolder1, parentFolder2, parentFolder3 = get_parent_folders(path)

        self._dict = {
            # user can edit these, see allowTextEdit()
            'Animal ID': '',
            'Region': '',
            'Cell Type': '',
            'Cell ID': '',
            'Condition': '',
            'Note': '',
            # not editable
            'path': path,
            'File Name': filename,
            'Parent Folder 1': parentFolder1,
            'Parent Folder 2': parentFolder2,
            'Parent Folder 3': parentFolder3,
            'Acq Date': '',
            'Acq Time': '',
            'secondsPerLine': None,
            'umPerPixel': None,
            'numChannels': 0 if imgData is None else len(imgData),
            'imageHeight': 0 if imgData is None else imgData[0].shape[0],  # number of pixels in each line scan
            'imageWidth': 0 if imgData is None else imgData[0].shape[1],  # number of line scans
        }

        self._allowEdit = [
            'Animal ID',
            'Region',
            'Cell Type',
            'Cell ID',
            'Condition',
            'Note',
        ]
        """Keys that are editable in qt dialog.
        """

        self._doNotShowInGui = 'path'
        """Keys to not show in GUI.
        """

    def setParam(self, key, value):
        """Set a parameter value."""
        if key in self._dict:
            self._dict[key] = value
            return True
        else:
            logger.debug(f'key:{key} not in self._dict.keys()')
            return False

    def getParam(self, key) -> Optional[Any]:
        try:
            return self._dict[key]
        except KeyError:
            logger.debug(f'key:{key} not in self._dict.keys()')
            logger.debug(f'available keys are {self._dict.keys()}')
        return None

    def showInGui(self, key):
        """Return True if we show in Qt gui."""
        return key not in self._doNotShowInGui

    def allowTextEdit(self, key):
        """Return True if we edit a str in the gui."""
        return key in self._allowEdit

    def toJson(self):
        _ret = json.dumps(self._dict)
        return _ret

    def fromJson(self, jsonStr):
        logger.debug('fromJson called')
        _dict = json.loads(jsonStr)
        for k, v in _dict.items():
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
        logger.debug('fromDict called')
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

    def __contains__(self, key):
        """Support the 'in' operator for checking if a key exists in the metadata."""
        return key in self._dict
