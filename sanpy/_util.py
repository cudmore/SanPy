import os

#from shapeanalysisplugin._my_logger import logger
from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

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
