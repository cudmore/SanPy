from sanpy.fileloaders import fileLoader_tif
from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis

def testKymRoiAnalysis(path):

    flt = fileLoader_tif(path)
    imgData = flt._tif  # list of color channel images
    # imgData = imgData[0]

    kra = KymRoiAnalysis(path, imgData)

    ltrb = [0, 30, 1000, 0]
    
    roi = kra.addROI(ltrb)
    print(roi)

    channel = 0
    roi.detectDiam(channel)
    roi.peakDetect(channel)

if __name__ == '__main__':
    path = '/Users/cudmore/Desktop/retreat-sept-2024/SSAN Linescan 12.tif'
    testKymRoiAnalysis(path)