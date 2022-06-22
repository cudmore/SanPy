import os
import sys
import pathlib

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def getBundledDir():
    """
    """
    if getattr(sys, 'frozen', False):
        # we are running in a bundle (frozen)
        bundle_dir = sys._MEIPASS
    else:
        # we are running in a normal Python environment
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    #logger.info(f'bundle_dir: {bundle_dir}')
    
    return bundle_dir

def addUserPath():
    """Make user SanPy folder and add it to the Python sys.path
    """
    
    logger.info('')
    makeSanPyFolders()  # make if necc
            
    userSanPyFolder = getUserSanPyFolder()

    if userSanPyFolder in sys.path:
        sys.path.remove(userSanPyFolder)

    if not userSanPyFolder in sys.path:
        logger.info(f'Adding to sys.path: {userSanPyFolder}')
        sys.path.append(userSanPyFolder)

    logger.info('sys.path is now:')

    for path in sys.path:
        logger.info(f'    {path}')

def getUserDocumentsFolder():
    userPath = pathlib.Path.home()
    userDocumentsFolder = os.path.join(userPath, 'Documents')
    if not os.path.isdir(userDocumentsFolder):
        logger.error(f'Did not find path "{userDocumentsFolder}"')
        logger.error(f'   Using "{userPath}"')
        return userPath
    else:
        return userDocumentsFolder

def getUserSanPyFolder():
    userDocumentsFolder = getUserDocumentsFolder()
    sanpyFolder = os.path.join(userDocumentsFolder, 'SanPy')
    return sanpyFolder

def getUserPluginFolder():
    userSanPyFolder = getUserSanPyFolder()
    userPluginFolder = os.path.join(userSanPyFolder, 'plugins')
    return userPluginFolder

def getUserAnalysisFolder():
    userAnalysisFolder = getUserSanPyFolder()
    userAnalysisFolder = os.path.join(userAnalysisFolder, 'analysis')
    return userAnalysisFolder

def makeSanPyFolders():
    """Make SanPy folder in user Documents path.

    If no Documents folder then make SanPy folder directly in user path.
    """
    userDocumentsFolder = getUserDocumentsFolder()

    sanpyFolder = os.path.join(userDocumentsFolder, 'SanPy')
    if not os.path.isdir(sanpyFolder):
        logger.info(f'Making SanPy folder "{sanpyFolder}"')
        os.mkdir(sanpyFolder)

    # to save detection parameters json
    detectionFolder = os.path.join(sanpyFolder, 'detection')
    if not os.path.isdir(detectionFolder):
        logger.info(f'Making user detection folder "{detectionFolder}"')
        os.mkdir(detectionFolder)

    # to hold custom .py plugins
    pluginFolder = getUserPluginFolder()  # os.path.join(sanpyFolder, 'plugins')
    if not os.path.isdir(pluginFolder):
        # TODO: add __init__.py
        logger.info(f'Making user plugin folder "{pluginFolder}"')
        os.mkdir(pluginFolder)

    # to hold custom .py analysis
    detectionFolder = os.path.join(sanpyFolder, 'analysis')
    if not os.path.isdir(detectionFolder):
        # TODO: add __init__.py
        logger.info(f'Making user analysis folder "{detectionFolder}"')
        os.mkdir(detectionFolder)

def _loadLineScanHeader(path):
    """
    path: full path to tif

    we will load and parse coresponding .txt file

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

    txtFile = os.path.splitext(path)[0] + '.txt'

    if not os.path.isfile(txtFile):
        logger.error(f'did not find file:{txtFile}')
        return None

    theRet = {'tif': path}

    # tif shape is (lines, pixels)
    #theRet['numLines'] = self.tif.shape[1]
    #theRet['numLines'] = tifData.shape[0]

    gotImageSize = False

    with open(txtFile, 'r') as fp:
        lines = fp.readlines()
        for line in lines:
            line = line.strip()
            if line.startswith('"X Dimension"'):
                line = line.replace('"', "")
                line = line.replace(',', "")
                #print('loadLineScanHeader:', line)
                # 2 number of pixels in line
                # 5 um length of line
                # 7 um/pixel
                splitLine = line.split()
                for idx, split in enumerate(splitLine):
                    #print('  ', idx, split)
                    if idx == 2:
                        numPixels = int(split)
                        theRet['numPixels'] = numPixels
                    elif idx == 5:
                        umLength = float(split)
                        theRet['umLength'] = umLength
                    elif idx == 7:
                        umPerPixel = float(split)
                        theRet['umPerPixel'] = umPerPixel

            elif line.startswith('"T Dimension"'):
                # "T Dimension"	"1, 0.000 - 35.496 [s], Interval FreeRun"
                line = line.replace('"', "")
                line = line.replace(',', "")
                #print('loadLineScanHeader:', line)
                # 5 total duration of image acquisition (seconds)
                splitLine = line.split()
                for idx, split in enumerate(splitLine):
                    #print('  ', idx, split)
                    if idx == 5:
                        totalSeconds = float(split)
                        theRet['totalSeconds'] = totalSeconds

                        #theRet['secondsPerLine'] =

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
                line = line.replace(',', "")
                splitLine = line.split('\t')  # yes, a FREAKING tab !!!!
                splitLine = splitLine[1]
                splitLine2 = splitLine.split()
                #print('splitLine2:', splitLine2)

                theRet['numLines'] = int(splitLine2[2])

            #elif line.startswith('"Image Size(Unit Converted)"'):
            #	print('loadLineScanHeader:', line)

    # tif shape is (lines, pixels)
    shape = (theRet['numLines'], theRet['numPixels'])
    #theRet['shape'] = self.tif.shape
    #theRet['shape'] = tifData.shape
    theRet['shape'] = shape
    theRet['secondsPerLine'] = theRet['totalSeconds'] / theRet['shape'][0]
    theRet['linesPerSecond'] = 1 / theRet['secondsPerLine']
    #
    return theRet
