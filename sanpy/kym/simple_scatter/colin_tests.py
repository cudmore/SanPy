import  os
import sys

import numpy as np
import tifffile
import roifile  # to import Fiji roi manager zip files

import matplotlib.pyplot as plt

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def test_load_roi():
    """20250528, need to perfect importing Fii ROI into sanpy.
    """
    tifPath = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/test-fiji-roi/ISAN Ivabradine R1 LS1.tif.frames/ISAN Ivabradine R1 LS1.tif'

    if not os.path.isfile(tifPath):
        logger.error('file not found')
        return
    
    rootPath = '/Users/cudmore/Dropbox/data/colin/2025/roi manager - 20250520'
    oneZipFile = '250225/ISAN/20250225 ISAN RoiSet.zip'
    
    oneZipPath = os.path.join(rootPath, oneZipFile)

    fijiRoiList = roifile.roiread(oneZipPath)

    # logger.info(f'')

    roiRectList = []
    for fijiRoiIdx, oneFijiRoi in enumerate(fijiRoiList):
        name = oneFijiRoi.name
        # if 'R1 LS1 Ivabradine Mode 1_2' not in name:
        if 'R1 LS1 Ivabradine' not in name:
            continue
        print(f'=== fijiRoiIdx:{fijiRoiIdx}')
        print(oneFijiRoi)

        left = oneFijiRoi.left
        top = oneFijiRoi.top
        right = oneFijiRoi.right
        bottom = oneFijiRoi.bottom
        
        # colin is specifying a 1-2 pixel roi with a stroke with
        # this will expand left/right
        stroke_width = oneFijiRoi.stroke_width

        half_stroke_width = stroke_width // 2
        left -= half_stroke_width
        right += half_stroke_width

        # up till 20250528, was this
        # this is correct, we need to just flip our tif files in y-axis !!!!
        # sanpyRect_v1 = [top, right, bottom, left]  # l/t/r/b
        logger.info('assuming file loader will flip y')
        # sanpyRect_v1 = [top, right, bottom, left]  # l/t/r/b
        # assuming file loader flips y
        sanpyRect_v1 = [top, left, bottom, right]  # l/t/r/b
        roiRectList.append(sanpyRect_v1)

        # sanpyRect = [top, left, bottom, right]  # l/t/r/b

    #
    test_plot_kym_image_with_roi(tifPath=tifPath, roiRectList=roiRectList)

def test_plot_kym_image_with_roi(tifPath, roiRectList, ax=None):
    """Plot one kym image with its rois.
    """

    if ax is None:
        fig, ax = plt.subplots(nrows=1,
                               ncols=1,
                               figsize=(8, 6),
                               )
    
    imgData = tifffile.imread(tifPath)
    imgData = np.rot90(imgData)
    # new 20250528 !!!
    imgData = np.flip(imgData, axis=0)
    # the start/stop of my line scan might be wrong !!!
    logger.info(f'new 20250528 flipped imgData:{imgData.shape}')

    # np.flip()
    _origin = 'lower'
    ax.imshow(imgData,
                cmap="Grays",
                # origin='lower',  # (0,0) is bottom left
                origin=_origin,  # (0,0) is bottom left
                aspect='auto',
    )

    roiColorList = ['r', 'g', 'b', 'c', 'm', 'y']
    for roiIdx, roiRect in enumerate(roiRectList):
        logger.info(f'plotting roiIdx:{roiIdx} roiRect:{roiRect}')
        
        roiColor = roiColorList[roiIdx]
        
        left = roiRect[0]
        top = roiRect[1]
        right = roiRect[2]
        bottom = roiRect[3]

        # plot roi as points
        x = [left, left, right, right]
        y = [bottom, top, top, bottom]
        ax.plot(x, y, 'or')

        width = right - left
        height = top - bottom
        # 20250528, if we plotted with origin='lower', height is negative !!!
        # nope, we seem to always need the negative of height
        # if our file loader does flip y then we do not need this
        # assumin when we import Fiji roi, we swap left with right
        logger.info('negative height ???')
        if _origin == 'lower':
            height = - height

        import matplotlib.patches as patches
        rect = patches.Rectangle((left, top),
                                    width, height,
                                    linewidth=2,
                                    edgecolor=roiColor,
                                    facecolor='none')
        ax.add_patch(rect)

        # label roi in image
        # f0_value_percentile = round(f0_value_percentile,1)
        # oneLabel = f'{roiLabel} f0:{f0_value_percentile}'
        oneLabel = f'roiIdx:{roiIdx}'
        _xOffset = 20  # 5
        ax.annotate(oneLabel, xy=(left, bottom),
                    xytext=(left+_xOffset, bottom-20),
                    arrowprops=dict(arrowstyle='->'),
                    fontsize=12,
                    weight='bold',
                    color=roiColor)

    #
    plt.show()

def testRot(tifPath):
    # Show loaded tif with no rot90 or flipy
    imgData = tifffile.imread(tifPath)

    fig, ax = plt.subplots(nrows=1,
                            ncols=1,
                            figsize=(8, 6),
                            )

    _origin = 'lower'
    ax.imshow(imgData,
                cmap="Grays",
                # origin='lower',  # (0,0) is bottom left
                origin=_origin,  # (0,0) is bottom left
                aspect='auto',
    )

    plt.show()

if __name__ == '__main__':

    # tifPath = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/test-fiji-roi/ISAN Ivabradine R1 LS1.tif.frames/ISAN Ivabradine R1 LS1.tif'
    # testRot(tifPath)

    test_load_roi()