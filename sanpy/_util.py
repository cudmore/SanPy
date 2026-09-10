"""General filesystem and runtime utilities for SanPy."""

import os
import importlib
from typing import List, Union
import uuid

import numpy as np

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


# External Python extensions are intentionally disabled until the runtime
# extension architecture and trust model are ready for end users.
ALLOW_USER_CODE_IMPORTS = False


def getNewUuid():
    return "t" + str(uuid.uuid4()).replace("-", "_")


def _module_from_file(module_name: str, file_path: str):
    """

    Args:
        module_name: Is like sanpy.interface.plugins.onePluginFile
        file_path: Full path to onePluginFile source code (onePluginFile.py)
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pprint(d: dict):
    for k, v in d.items():
        print(f"  {k}: {v}")


def _loadLineScanHeader(path):
    """Find corresponding txt file with Olympus tif header.
    
    Load and parse coresponding .txt file

    Parameters
    ----------
    path: full path to tif

    returns dict:
        numPixels:
        umLength:
        umPerPixel:
        totalSeconds:
    """
    # "X Dimension"	"138, 0.0 - 57.176 [um], 0.414 [um/pixel]"
    # "T Dimension"	"1, 0.000 - 35.496 [s], Interval FreeRun"
    # "Image Size(Unit Converted)"	"57.176 [um] * 35500.000 [ms]"

    # 20220606, adding
    # "Image Size"	"294 * 1000 [pixel]"

    txtFile = os.path.splitext(path)[0] + ".txt"

    if not os.path.isfile(txtFile):
        # logger.error(f"did not find file:{txtFile}")

        _filePath, _fileName = os.path.split(path)
        _idx = _fileName.find('_C')
        filePrefix = _fileName[0:_idx]
    
        txtFileName = filePrefix + '.txt'
        txtFilePath = os.path.join(_filePath, txtFileName)
        if not os.path.isfile(txtFilePath):
            return None
        txtFile = txtFilePath
        
    theRet = {"tif": path}

    # tif shape is (lines, pixels)
    # theRet['numLines'] = self.tif.shape[1]
    # theRet['numLines'] = tifData.shape[0]

    gotNumPixels = False
    gotImageSize = False

    with open(txtFile, "r") as fp:
        lines = fp.readlines()
        for line in lines:
            line = line.strip()
            if line.startswith('"X Dimension"'):
                line = line.replace('"', "")
                line = line.replace(",", "")
                # print('loadLineScanHeader:', line)
                # 2 number of pixels in line
                # 5 um length of line
                # 7 um/pixel
                splitLine = line.split()
                for idx, split in enumerate(splitLine):
                    # print('  ', idx, split)
                    if idx == 2:
                        numPixels = int(split)
                        theRet["numPixels"] = numPixels
                        gotNumPixels = True
                    elif idx == 5:
                        umLength = float(split)
                        theRet["umLength"] = umLength
                    elif idx == 7:
                        umPerPixel = float(split)
                        theRet["umPerPixel"] = umPerPixel

            elif line.startswith('"T Dimension"'):
                # "T Dimension"	"1, 0.000 - 35.496 [s], Interval FreeRun"
                line = line.replace('"', "")
                line = line.replace(",", "")
                # print('loadLineScanHeader:', line)
                # 5 total duration of image acquisition (seconds)
                splitLine = line.split()
                for idx, split in enumerate(splitLine):
                    # print('  ', idx, split)
                    if idx == 5:
                        totalSeconds = float(split)
                        theRet["totalSeconds"] = totalSeconds

                        # theRet['secondsPerLine'] =

            # order in file will matter, there are multiple "Image Size" lines
            # we want the first
            # "Image Size"	"294 * 1000 [pixel]"
            elif line.startswith('"Image Size"'):
                if line.startswith('"Image Size(Unit Converted)"'):
                    continue
                if gotImageSize:
                    continue
                gotImageSize = True
                line = line.replace('"', "")
                line = line.replace(",", "")
                splitLine = line.split("\t")  # yes, a FREAKING tab !!!!
                splitLine = splitLine[1]
                splitLine2 = splitLine.split()
                # print('splitLine2:', splitLine2)

                theRet["numLines"] = int(splitLine2[2])

            # elif line.startswith('"Image Size(Unit Converted)"'):
            # 	print('loadLineScanHeader:', line)

    # tif shape is (lines, pixels)
    if gotNumPixels and gotImageSize:
        shape = (theRet["numLines"], theRet["numPixels"])
    else:
        shape = (np.nan, np.nan)
    # theRet['shape'] = self.tif.shape
    # theRet['shape'] = tifData.shape
    theRet["shape"] = shape
    
    try:
        theRet["secondsPerLine"] = theRet["totalSeconds"] / theRet["shape"][0]
    except (KeyError) as e:
        logger.warning(f'did not find key {e}')
    try:
        theRet["linesPerSecond"] = 1 / theRet["secondsPerLine"]
    except (KeyError) as e:
        logger.warning(f'did not find key {e}')

    #
    return theRet

def _listdir(path):
    """
    recursively walk directory to specified depth
    :param path: (str) path to list files from
    :yields: (str) filename, including path
    """
    for filename in os.listdir(path):
        if filename.startswith('.'):
            continue
        yield os.path.join(path, filename)


def _walk(path='.', depth=None):
    """
    recursively walk directory to specified depth
    :param path: (str) the base path to start walking from
    :param depth: (None or int) max. recursive depth, None = no limit
    :yields: (str) filename, including path
    """
    if depth and depth == 1:
        for filename in _listdir(path):
            yield filename
    else:
        top_pathlen = len(path) + len(os.path.sep)
        for dirpath, dirnames, filenames in os.walk(path):
            dirlevel = dirpath[top_pathlen:].count(os.path.sep)
            if depth and dirlevel >= depth:
                dirnames[:] = []
            else:
                for filename in filenames:
                    yield os.path.join(dirpath, filename)
                    
def getFileList(path, depth=1):
    fileList = [filePath for filePath in _walk(path, depth)]
    return fileList
