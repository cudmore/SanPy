"""
Plot kymROiAnalysis using matplotlib.
"""

import os

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import matplotlib.patches as patches
import seaborn as sns

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis
from sanpy.kym.kymRoi import PeakDetectionTypes
# from sanpy.kym.kymRoiAnalysis import FileInfo
from sanpy.kym.kymUtils import getAutoContrast


from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

roiColorList = ['r', 'g', 'b', 'c', 'm', 'y']

def plotRoiRects(
    ax: Axes,
    kymRoiAnalysis: KymRoiAnalysis,
):
    """Plot roi rect on a mpl axis."""
    secondsPerLine = kymRoiAnalysis.secondsPerLine

    roiLabels = kymRoiAnalysis.getRoiLabels()
    for roiIdx, kymRoiLabel in enumerate(roiLabels):
        try:
            roiColor = roiColorList[roiIdx]
        except IndexError:
            tifPath = kymRoiAnalysis.path
            tifName = os.path.basename(tifPath)
            logger.error(
                f'tifName:{tifName} roiIdx:{roiIdx} out of range for roiColorList:{roiColorList}'
            )
            roiColor = 'k'

        kymRoi = kymRoiAnalysis.getRoi(kymRoiLabel)
        roiRect = kymRoi.getRect()

        left = roiRect[0]
        top = roiRect[1]
        right = roiRect[2]
        bottom = roiRect[3]

        left = left * secondsPerLine
        right = right * secondsPerLine

        # plot roi as points
        # x = [left, left, right, right]
        # y = [bottom, top, top, bottom]
        # ax.plot(x, y, 'or')

        width = right - left
        height = top - bottom
        # 20250528, if we plotted with origin='lower', height is negative !!!
        # nope, we seem to always need the negative of height
        # if our file loader does flip y then we do not need this
        # assumin when we import Fiji roi, we swap left with right
        # logger.info('negative height ???')
        _origin = 'lower'
        if _origin == 'lower':
            height = -height

        rect = patches.Rectangle(
            (left, top),
            width,
            height,
            linewidth=1,
            edgecolor=roiColor,
            facecolor='none',
        )
        ax.add_patch(rect)

        # label roi in image
        # oneLabel = f'roiIdx:{roiIdx}'
        # _xOffset = 20  # 5
        # ax.annotate(oneLabel, xy=(left, bottom),
        #             xytext=(left+_xOffset, bottom-20),
        #             arrowprops=dict(arrowstyle='->'),
        #             fontsize=12,
        #             weight='bold',
        #             color=roiColor)

def plotKymRoiTif(
    ax: Axes,
    kymRoiAnalysis: KymRoiAnalysis,
    roiLabelStr: str = None,
    detectThisTrace: str = None,
):
    """Plot either a full kym tif or one roi tif.

    If specified, both (detectThisTrace and f0) need to be specified.
    """
    channel = 0
    _path = kymRoiAnalysis.path
    _path, _file = os.path.split(_path)
    secondsPerLine = kymRoiAnalysis.secondsPerLine
    numLineScans = kymRoiAnalysis.numLineScans
    f0 = None
    if roiLabelStr is None:
        # full kym
        imgData = kymRoiAnalysis.getImageChannel(channel=channel)
        height = kymRoiAnalysis.numPixelsPerLine
        # _rect = kymRoiAnalysis.getRect()
    else:
        # one roi
        kymRoi = kymRoiAnalysis.getRoi(roiLabelStr)
        imgData = kymRoi.getRoiImg(channel)
        _rect = kymRoi.getRect()
        detectionParams = kymRoi.getDetectionParams(
            channel=channel, detectionType=PeakDetectionTypes.intensity
        )
        f0 = detectionParams.getParam('f0 Value Percentile')

        height = _rect[1] - _rect[3]

    # this wil fail for kymroi with left != 0
    left = 0
    right = numLineScans

    left_sec = left * secondsPerLine
    right_sec = right * secondsPerLine
    # top_um = top * umPerPixel
    # bottom_um = bottom * umPerPixel
    # extent=[left_sec, right_sec, bottom_um, top_um] # [left, right, top, bottom]
    extent = [left_sec, right_sec, 0, height]  # [left, right, top, bottom]

    if f0 is not None:
        if detectThisTrace == 'f/f0':
            _imgDataDisplay = imgData / f0
        elif detectThisTrace == 'df/f0':
            _imgDataDisplay = (imgData - f0) / f0
        else:
            logger.error(f'detectThisTrace:{detectThisTrace} not supported')
            return
    else:
        _imgDataDisplay = imgData

    # imgMin = np.percentile(imgData, 5)  # 2
    # imgMax = np.percentile(imgData, 90)  # 98
    _min, _max = getAutoContrast(_imgDataDisplay)  # new 20240925, should mimic ImageJ

    logger.info(
        f'plotting {_file} _min:{_min} _max:{_max} \
                image min:{_imgDataDisplay.min()} \
                image max:{_imgDataDisplay.max()}'
    )

    ax.imshow(
        imgData,
        cmap="Greens",
        origin='lower',
        aspect='auto',
        extent=extent,
        vmin=_min,
        vmax=_max,
    )

    ax.xaxis.set_tick_params(which='both', labelbottom=False)
    sns.despine(bottom=True, left=True, ax=ax)

    # plot all roi on full kym img
    plotRoiRects(ax, kymRoiAnalysis)

def plotOneKym(kymRoiAnalysis: KymRoiAnalysis) -> tuple[plt.Figure, plt.Axes]:
    """Plot all ROI in one kym image.

    This includes the kym image and one f/f0 plot per ROI.
    """

    numRois = kymRoiAnalysis.numRoi

    fig, ax = plt.subplots(
        nrows=numRois + 1,
        ncols=1,
        figsize=(8, 6),
        sharex=True,
    )
    
    # fileInfo = FileInfo.from_path(tif_path=kymRoiAnalysis.path)
    # fig.suptitle(
    #     f'"{fileInfo.cellID}" condition:"{fileInfo.condition}" epoch:{fileInfo.epoch}',
    #     fontsize=11,
    # )

    fig.suptitle(
        f'{os.path.basename(kymRoiAnalysis.path)}'
    )

    # despine top and right
    for oneAx in ax:
        sns.despine(top=True, right=True, ax=oneAx)

    linewidth = 1
    markersize = 5

    plotKymRoiTif(
        ax[0],
        kymRoiAnalysis,
    )

    roiLabels = kymRoiAnalysis.getRoiLabels()
    for roiIdx, roiLabelStr in enumerate(roiLabels):
        logger.info(f'-->> plotting roiIdx:{roiIdx} roiLabelStr:{roiLabelStr}')
        plotRow = roiIdx + 1
        try:
            _color = roiColorList[roiIdx]
        except IndexError:
            tifPath = kymRoiAnalysis.path
            tifName = os.path.basename(tifPath)
            logger.error(
                f'tifName:{tifName} roiIdx:{roiIdx} out of range for roiColorList:{roiColorList}'
            )
            _color = 'k'

        kymRoi = kymRoiAnalysis.getRoi(roiLabelStr)
        kymRoiDetection = kymRoi.getDetectionParams(
            channel=0, detectionType=PeakDetectionTypes.intensity
        )
        f0 = kymRoiDetection.getParam('f0 Value Percentile')

        # set the subplot title with f0 value and roi label
        _label = f'roi "{roiLabelStr}" f0:{f0:.1f}'
        ax[plotRow].set_title(_label, color=_color)

        timeTrace = kymRoiAnalysis.getAnalysisTrace(roiLabelStr, 'Time (s)', 0)
        f_f0Trace = kymRoiAnalysis.getAnalysisTrace(roiLabelStr, 'f/f0', 0)

        # timeTrace = dfTraces[f'ROI {roiLabelStr} Time (s)']
        # logger.info(f'timeTrace:{timeTrace}')
        # f_f0Trace = dfTraces[f'ROI {roiLabelStr} f/f0']  # hard coding f/f0 -->> df/f0
        ax[plotRow].plot(
            timeTrace,
            f_f0Trace,
            'g',
            linewidth=linewidth,
            # label=f'{fileInfo.cellID} {fileInfo.condition}',
        )

        # in kymRoi, labels are str, in df they are int
        # roiLabelInt = int(roiLabelStr)

        # theseRows = (dfMaster['Cell ID']==cellID) \
        #         & (dfMaster['ROI Number']==roiLabelInt) \
        #         & (dfMaster['Condition']==condition) \
        #         & (dfMaster['Epoch']==epoch)
        # dfPeaks = dfMaster.loc[theseRows]

        kymRoiResults = kymRoiAnalysis.getDataFrame(
            channel=0,
            peakDetectionType=PeakDetectionTypes.intensity,
            roiLabel=roiLabelStr,
        )
        dfPeaks = kymRoiResults.df

        # onset
        xPlot = dfPeaks['Onset (s)']
        yPlot = dfPeaks['Onset Int']
        ax[plotRow].plot(xPlot, yPlot, 'co', markersize=markersize)

        # peak
        xPlot = dfPeaks['Peak (s)']
        yPlot = dfPeaks['Peak Int']
        ax[plotRow].plot(xPlot, yPlot, 'ro', markersize=markersize)

        # onset
        xPlot = dfPeaks['Decay (s)']
        yPlot = dfPeaks['Decay Int']
        ax[plotRow].plot(xPlot, yPlot, 'mo', markersize=markersize)

        if plotRow > 1:
            ax[plotRow].sharey(ax[plotRow - 1])

    return fig, ax
