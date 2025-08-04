import os
import sys
from typing import List, Optional, Any
import json
from pprint import pprint
from dataclasses import dataclass, asdict

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


@dataclass
class KymRoiMetaDataFields:
    """Dataclass containing the metadata fields with proper types."""
    # User editable fields
    version: float = 0.1
    Animal_ID: str = ''
    Cell_Type: str = ''
    Region: str = ''
    Cell_ID: str = ''
    Condition: str = ''
    Repeat: int = 0
    Date: str = ''
    Note: str = ''
    Accept: bool = True
    
    # Non-editable fields
    path: str = ''
    File_Name: str = ''
    Parent_Folder_1: str = ''
    Parent_Folder_2: str = ''
    Parent_Folder_3: str = ''
    Acq_Date: str = ''
    Acq_Time: str = ''
    secondsPerLine: Optional[float] = None
    umPerPixel: Optional[float] = None
    numChannels: int = 0
    imageHeight: int = 0
    imageWidth: int = 0


class KymRoiMetaData:
    def __init__(self, path: str, imgData: List[np.ndarray] = None) -> None:

        folder, filename = os.path.split(path)

        parentFolder1, parentFolder2, parentFolder3 = get_parent_folders(path)

        # auto fill some values from TifInfo (parses filename)
        tifInfo = TifInfo.from_filename(path)

        # Create the dataclass instance
        self._fields = KymRoiMetaDataFields(
            version=0.1,
            Animal_ID='',
            Cell_Type='',
            Region=tifInfo.region,
            Cell_ID=tifInfo.cellid,
            Condition=tifInfo.condition,
            Repeat=tifInfo.repeat,
            Date=tifInfo.date,
            Note='',
            Accept=True,
            path=path,
            File_Name=filename,
            Parent_Folder_1=parentFolder1,
            Parent_Folder_2=parentFolder2,
            Parent_Folder_3=parentFolder3,
            Acq_Date='',
            Acq_Time='',
            secondsPerLine=None,
            umPerPixel=None,
            numChannels=0 if imgData is None else len(imgData),
            imageHeight=0 if imgData is None else imgData[0].shape[0],
            imageWidth=0 if imgData is None else imgData[0].shape[1],
        )

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

    def _get_field_name(self, key: str) -> str:
        """Convert space-separated key to dataclass field name."""
        return key.replace(' ', '_')

    def _get_display_name(self, field_name: str) -> str:
        """Convert dataclass field name to display name with spaces."""
        return field_name.replace('_', ' ')

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
        field_name = self._get_field_name(key)
        if field_name in self._fields.__dataclass_fields__:
            setattr(self._fields, field_name, value)
            return True
        else:
            logger.debug(f'key:{key} not in dataclass fields')
            return False

    def getParam(self, key) -> Optional[Any]:
        """Get a parameter value."""
        field_name = self._get_field_name(key)
        if field_name in self._fields.__dataclass_fields__:
            return getattr(self._fields, field_name)
        else:
            logger.debug(f'key:{key} not in dataclass fields')
            logger.debug(f'available keys are {[self._get_display_name(field) for field in self._fields.__dataclass_fields__.keys()]}')
        return None

    def showInGui(self, key):
        """Return True if we show in Qt gui."""
        return key not in self._doNotShowInGui

    def allowTextEdit(self, key: str) -> bool:
        """Return True if we edit a str in the gui."""
        return key in self._allowEdit

    def toJson(self):
        """Convert to JSON string."""
        # Convert dataclass to dict with display names
        data_dict = {}
        for field_name in self._fields.__dataclass_fields__.keys():
            display_name = self._get_display_name(field_name)
            data_dict[display_name] = getattr(self._fields, field_name)
        return json.dumps(data_dict)

    def fromJson(self, jsonStr):
        """Load from JSON string."""
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
        elif _dict['version'] < instance.getParam('version'):
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
        """Return items with display names (spaces instead of underscores)."""
        items_list = []
        for field_name in self._fields.__dataclass_fields__.keys():
            display_name = self._get_display_name(field_name)
            items_list.append((display_name, getattr(self._fields, field_name)))
        return items_list

    def __contains__(self, key):
        """Support the 'in' operator for checking if a key exists in the metadata."""
        field_name = self._get_field_name(key)
        return field_name in self._fields.__dataclass_fields__
