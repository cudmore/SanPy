import os
import sys
from typing import List, Optional, Any
import json
from pprint import pprint

import numpy as np
import pandas as pd

from sanpy.kym.tif_info import TifInfo

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

        # auto fill some values from TifInfo (parses filename)
        tifInfo = TifInfo.from_filename(path)

        """
            date: str
            cellid: str
            condition: str
            region: str
            repeat: int
        """

        self._dict = {
            # user can edit these, see allowTextEdit()
            'version': 0.1,  # abb 20250728
            'Animal ID': '',
            'Cell Type': '',
            'Region': tifInfo.region,
            'Cell ID': tifInfo.cellid,
            'Condition': tifInfo.condition,
            'Repeat': tifInfo.repeat,
            'Date': tifInfo.date,
            'Note': '',  # abb todo move to kymroianalysis
            'Accept': True,  # abb todo move to kymroianalysis
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
            'Repeat',
            'Date',
            'Note',
            'Accept',
        ]
        """Keys that are editable in qt dialog.
        """

        self._doNotShowInGui = 'path'
        """Keys to not show in GUI.
        """

    def setValuesFromTifFile(self, path: str):
        """Set values from tif file name."""
        logger.info('  setting values from filename')

        tifInfo = TifInfo.from_filename(path)
        self.setParam('Region', tifInfo.region)
        self.setParam('Cell ID', tifInfo.cellid)
        self.setParam('Condition', tifInfo.condition)
        self.setParam('Repeat', tifInfo.repeat)
        self.setParam('Date', tifInfo.date)

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

    def allowTextEdit(self, key: str) -> bool:
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
    def fromDict(cls, _dict: dict):
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

        if 'version' not in _dict.keys():
            # abb 20250728 this is an upgrade from our previous (no version) file version
            logger.error('no version in loaded metadata: -->> upgrading to new file version')

            # grab values from loaded dict
            logger.info('setting loaded key values:')
            for k, v in _dict.items():
                # logger.info(f'k:{k} v:{v}')
                instance.setParam(k, v)

            # this is the upgrade, reset values from tif file name (colin)
            # logger.info('recalculating some keys from tif file name')
            instance.setValuesFromTifFile(path)

            # logger.info('  -->>upgrade complete self._dict is:')
            # pprint(instance._dict)

        # abb 20250728 we are never here (yet)
        elif _dict['version'] < cls.getParam('version'):
            # abb 20250728 we are never here (yet)
            # this will handle future version changes
            logger.error(f'Version mismatch in saved state file: {_dict["path"]}')
            logger.error('  -->> ignore loaded header (implement this when we incrment version for metadata)')
            return instance

        else:
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
