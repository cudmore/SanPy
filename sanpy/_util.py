import os
import sys
import importlib
import pathlib
import shutil
from typing import List, Union
import uuid

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


def getNewUuid():
    return "t" + str(uuid.uuid4()).replace("-", "_")


def getBundledDir():
    """Get the working directory where user preferences are save.

    This will be source code folder when running from source,
      will be a more freeform folder when running as a frozen app/exe
    """
    if getattr(sys, "frozen", False):
        # we are running in a bundle (frozen)
        bundle_dir = sys._MEIPASS
    else:
        # we are running in a normal Python environment
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    return bundle_dir


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


def addUserPath():
    """Make <user>/Documents/SanPy folder and add it to the Python sys.path

    Returns:
        True: If we made the folder (first time SanPy is running)
    """

    logger.info("")

    madeUserFolder = _makeSanPyFolders()  # make <user>/Documents/SanPy if necc

    userSanPyFolder = _getUserSanPyFolder()

    # if userSanPyFolder in sys.path:
    #     sys.path.remove(userSanPyFolder)

    if not userSanPyFolder in sys.path:
        logger.info(f"Adding to sys.path: {userSanPyFolder}")
        sys.path.append(userSanPyFolder)

    logger.info("sys.path is now:")
    for path in sys.path:
        logger.info(f"    {path}")

    return madeUserFolder


def _getUserDocumentsFolder():
    """Get <user>/Documents folder."""
    userPath = pathlib.Path.home()
    userDocumentsFolder = os.path.join(userPath, "Documents")
    if not os.path.isdir(userDocumentsFolder):
        logger.error(f'Did not find path "{userDocumentsFolder}"')
        logger.error(f'   Using "{userPath}"')
        return userPath
    else:
        return userDocumentsFolder


def _getUserSanPyFolder():
    """Get <user>/Documents/SanPy folder."""
    userDocumentsFolder = _getUserDocumentsFolder()
    sanpyFolder = os.path.join(userDocumentsFolder, "SanPy-User-Files")
    return sanpyFolder


def _old_getUserFolder(folder: str) -> str:
    userSanPyFolder = _getUserSanPyFolder()
    if folder == "plugins":
        theFolder = os.path.join(userSanPyFolder, "plugins")
    elif folder == "analysis":
        theFolder = os.path.join(userSanPyFolder, "analysis")
    elif folder == "preferences":
        theFolder = os.path.join(userSanPyFolder, "preferences")
    else:
        logger.error(f'did not understand folder: "{folder}"')
        return None
    return theFolder


def _getUserFileLoaderFolder():
    userSanPyFolder = _getUserSanPyFolder()
    fileLoaderFolder = os.path.join(userSanPyFolder, "file loaders")
    return fileLoaderFolder


def _getUserPluginFolder():
    userSanPyFolder = _getUserSanPyFolder()
    userPluginFolder = os.path.join(userSanPyFolder, "plugins")
    return userPluginFolder


def _getUserDetectionFolder():
    """Folder of saved user detection presets.

    Each is a json file.
    """
    userSanPyFolder = _getUserSanPyFolder()
    userDetectionFolder = os.path.join(userSanPyFolder, "detection")
    return userDetectionFolder


def _getUserAnalysisFolder():
    """Folder of custom user analysis code."""
    userAnalysisFolder = _getUserSanPyFolder()
    userAnalysisFolder = os.path.join(userAnalysisFolder, "analysis")
    return userAnalysisFolder


def _getUserPreferencesFolder():
    """Folder of SanPy app preferences and logs (user does not modify this."""
    userPreferencesFolder = _getUserSanPyFolder()
    userPreferencesFolder = os.path.join(userPreferencesFolder, "preferences")
    return userPreferencesFolder


def pprint(d: dict):
    for k, v in d.items():
        print(f"  {k}: {v}")


def _makeSanPyFolders():
    """Make <user>/Documents/SanPy-User-Files folder .

    If no Documents folder then make SanPy folder directly in <user> path.
    """
    userDocumentsFolder = _getUserDocumentsFolder()

    madeUserFolder = False

    # main <user>/Documents/SanPy folder
    sanpyFolder = _getUserSanPyFolder()
    if not os.path.isdir(sanpyFolder):
        # first time run
        logger.info(f'Making <user>/SanPy-User-Files folder "{sanpyFolder}"')
        madeUserFolder = True
        #
        # copy entire xxx into <user>/Documents/SanPy
        _bundDir = getBundledDir()
        _srcPath = pathlib.Path(_bundDir) / "_userFiles" / "SanPy-User-Files"
        _dstPath = pathlib.Path(sanpyFolder)
        logger.info(f"    copying folder tree to <user>/Documents/SanPy-User-Folder")
        logger.info(f"    _srcPath:{_srcPath}")
        logger.info(f"    _dstPath:{_dstPath}")
        shutil.copytree(_srcPath, _dstPath)
    else:
        # already exists, make sure we have all sub-folders that are expected
        pass

    return madeUserFolder

def _loadLineScanHeader(path):
    """Find corresponding txt file with Olympus tif header.
    L
    oad and parse coresponding .txt file

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
    shape = (theRet["numLines"], theRet["numPixels"])
    # theRet['shape'] = self.tif.shape
    # theRet['shape'] = tifData.shape
    theRet["shape"] = shape
    theRet["secondsPerLine"] = theRet["totalSeconds"] / theRet["shape"][0]
    theRet["linesPerSecond"] = 1 / theRet["secondsPerLine"]
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

if __name__ == '__main__':
    path = '/Users/cudmore/Dropbox/data/cell-shortening/fig1'
    fileList = getFileList(path, 4)
    for file in fileList:
        print(file)


