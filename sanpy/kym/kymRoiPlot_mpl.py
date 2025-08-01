"""
Plot kymROiAnalysis using matplotlib.
"""

import os
import sys
from datetime import datetime

import numpy as np

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import matplotlib.patches as patches
import seaborn as sns

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis
from sanpy.kym.tif_file_backend import TifFileBackend
from sanpy.kym.kymRoi import PeakDetectionTypes, KymRoi
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
    channel: int = 0
):
    """Plot either a full kym tif or one roi tif.

    If specified, both (detectThisTrace and f0) need to be specified.
    """
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
        logger.info(f'_file:{_file} imgData.shape:{imgData.shape} height:{height}')

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
        # cast _imgDataDisplay original dtype of imgData
        _imgDataDisplay = _imgDataDisplay.astype(imgData.dtype)

    else:
        _imgDataDisplay = imgData


    _fullImgData = kymRoiAnalysis.getImageChannel(channel=channel)

    logger.info(f'plotting {_file}')
    logger.info(f'_fullImgData.shape:{_fullImgData.shape}')
    logger.info(f'roiLabelStr:{roiLabelStr} f0:{f0} detectThisTrace:{detectThisTrace}')
    logger.info(f'imgData.dtype:{imgData.dtype} _imgDataDisplay.dtype:{_imgDataDisplay.dtype}')
    logger.info(f'imgData.shape:{imgData.shape} _imgDataDisplay.shape:{_imgDataDisplay.shape}')
    logger.info(f'_imgDataDisplay min:{_imgDataDisplay.min()} _imgDataDisplay max:{_imgDataDisplay.max()}')

    # imgMin = np.percentile(imgData, 5)  # 2
    # imgMax = np.percentile(imgData, 90)  # 98
    _min, _max = getAutoContrast(_imgDataDisplay)  # new 20240925, should mimic ImageJ


    ax.imshow(
        _imgDataDisplay,
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

def plotStatSwarm(dfMaster,
                  yStat,
                  cellID,
                  repeat,
                  roiLabel, ax):
    """plot a swarmplot for one kym, one roi

    x-axis is cond, y-axis is stat
    """
    theseRows = (
        (dfMaster['Cell ID'] == cellID)
        & (dfMaster['Repeat'] == repeat)
        & (dfMaster['ROI Label'] == roiLabel)
    )
    dfSwarm = dfMaster.loc[theseRows]

    # logger.info('dfSwarm:')
    # print(dfSwarm)
    # return

    # Create new column with condition and epoch on separate lines
    # dfSwarm['Condition Epoch'] = dfSwarm['Condition Epoch'].str.replace(' ', '\n')
    # dfSwarm.loc[:, 'Condition Epoch'] = dfSwarm['Condition Epoch'].str.replace(
    #     ' ', '\n'
    # )
    # dfSwarm['Condition Epoch'] = dfSwarm['Condition Epoch Multiline'].astype('category')

    if yStat not in dfSwarm.columns:
        logger.warning(f'yStat:"{yStat}" not in dfSwarm.columns')
        logger.warning(f'dfSwarm.columns:{dfSwarm.columns}')
        return

    # hue = 'Condition Epoch'
    logger.warning('TODO: implement "condition repeat" column -->> was "condition epoch"')
    hue = 'Condition'

    # abb 20250623 mito atp, need to limit this so we do not plot non-existent conditions...
    logger.warning('fix hue order')
    # hue_order = ['Control\n0', 'Control\n1', 'Ivab\n0', 'Thap\n0', 'FCCP\n0']
    hue_order = None

    plotDict = {
        'data': dfSwarm,  # df for one cell id
        # 'x': 'Condition Epoch',
        'x': 'Condition',
        'y': yStat,
        # using new 'Condition Epoch' column
        'hue': hue,
        'order': hue_order,
    }
    sns.swarmplot(ax=ax, **plotDict)

    # logger.error(f'dfSwarm for yStat:{yStat}')
    # print(f'hue_order:{hue_order}')
    # print(dfSwarm[['Condition', yStat, hue]])

    # overlay mean bar
    markersize = 30
    sns.pointplot(
        data=dfSwarm,
        # x='Condition Epoch',
        x='Condition',
        y=yStat,
        hue=hue,
        # order=conditionOrder,
        errorbar=None,  # can be 'se', 'sem', etc
        # capsize=capsize,
        linestyle='none',  # do not connect (with line) between categorical x
        marker="_",
        markersize=markersize,
        # markeredgewidth=3,
        legend=False,
        # palette=palette,
        # dodge=0.5,  # separate the points by hue
        # dodge=None if len(uniqueHue)==1 else 0.5,  # separate the points by hue
        # dodge=True,  # 0.5 or true
        order=hue_order,
        ax=ax,
    )

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

def plot_cell_id_conds(
    backend: TifFileBackend,  # df from main interface
    cellID,
    roiLabel: str
) -> tuple[plt.Figure, plt.Axes, dict]:
    channel = 0

    dfMaster = backend._tifPool.get_master_dataframe()
    dfMean = backend._tifPool.get_df_mean()

    # get rows across all Epoch, each row becomes a column
    dfPlot = backend.get('filter_by_cell_id', cell_id=cellID)

    # use backend to make sure each row kymAnalysis is loaded using relative_path) column
    # for row in dfPlot.itertuples():
    #     backend.get_kym_roi_analysis_by_path(row.relative_path)

    # plot each (cond, epoch) as a column
    numCols = len(dfPlot)
    if numCols < 3:
        numCols = 3

    linewidth = 1
    markersize = 4  # for overlay of (onset, peak, decay)

    # always 3x3
    fig, ax = plt.subplots(
        nrows=3,
        ncols=numCols,
        figsize=(11, 8),
        height_ratios=[1, 2, 2],  # shrink first row (kym image)
    )

    _dateStr = datetime.now().strftime("%Y%m%d %H:%M")
    _suptitle = f'cell:"{cellID}" ROI:{roiLabel} plotted:{_dateStr}'
    fig.suptitle(_suptitle, fontsize=11)

    # despine top/right of each subplot
    for oneAx in ax.flatten():
        sns.despine(top=True, right=True, ax=oneAx)

    imgRow = 0
    peakRow = 1
    plotRow = 2

    # link x/y axis
    for colIdx in range(numCols):
        if colIdx > 0:
            # all columns in imgRow share y axis
            ax[imgRow][colIdx].sharey(ax[imgRow][colIdx - 1])
            # all columns in peakRow share y axis
            ax[peakRow][colIdx].sharey(ax[peakRow][colIdx - 1])

        # each column in peakRow shares x axis with same column in imgRow
        ax[peakRow][colIdx].sharex(ax[imgRow][colIdx])

    # iterate through rows in dfPlot (one column per row)
    # logger.info('dfPlot is:')
    # print(dfPlot)

    # return a dict with imgData and x/y traces
    imgDataDict = {}

    for rowIdx, (rowLabel, row) in enumerate(dfPlot.iterrows()):
        colIdx = rowIdx  # each row in df corresponds to a column
        cond = row['Condition']
        epoch = row['Repeat']
    
        # tifFile = row['Tif File']
        relative_path = row['relative_path']
        # abs_path = backend.resolve_path(relative_path)


        axImg = ax[imgRow][colIdx]

        # load the kymRoiAnalysis
        # ka = KymRoiAnalysis(abs_path)
        # kymRoi: KymRoi = ka.getRoi(roiLabel)
        ka = backend.get_kym_roi_analysis_with_image_data_by_path(relative_path)
        kymRoi: KymRoi = ka.getRoi(roiLabel)

        # secondsPerLine = kymRoi.secondsPerLine
        # umPerPixel = kymRoi.umPerPixel
        from sanpy.kym.kymRoiAnalysis import PeakDetectionTypes

        _detectionParams = kymRoi.getDetectionParams(
            channel, PeakDetectionTypes.intensity
        )
        detectThisTrace = _detectionParams['detectThisTrace']
        f0_value_percentile = _detectionParams['f0 Value Percentile']
        polarity = _detectionParams['Polarity']
        roiRect = _detectionParams['ltrb']

        logger.info(
            f'  cond:{cond} epoch:{epoch} roiRect:{roiRect} f0:{f0_value_percentile}'
        )

        imgData = plotKymRoiTif(
            ax=axImg,
            kymRoiAnalysis=ka,
            roiLabelStr=roiLabel,
            detectThisTrace=detectThisTrace,
        )

        axImg.set_title(
            f'"{cond} {epoch}" f0:{round(f0_value_percentile,1)} {polarity}',
            fontsize=10,
        )

        # turn x-axis labels/ticks back on
        ax[peakRow][colIdx].xaxis.set_tick_params(which='both', labelbottom=True)

        # plot sum intensity like f/f_0
        xPlot = kymRoi.getTrace(channel, 'Time (s)')
        yPlot = kymRoi.getTrace(channel, detectThisTrace)

        # collect into return dict
        # info for one (Cell id, cond, epoch, roi label)
        f_f0 = kymRoi.getTrace(channel, 'f/f0')
        df_f0 = kymRoi.getTrace(channel, 'df/f0')
        raw = kymRoi.getTrace(channel, 'intRaw')
        imgDataDict[relative_path] = {
            'roiLabelStr': roiLabel,
            'imgDataClip': imgData,
            'Time (s)': xPlot,
            'intRaw': raw,
            'f_f0': f_f0,
            'df_f0': df_f0,
        }

        ax[peakRow][colIdx].plot(
            xPlot,
            yPlot,
            color='g',
            linewidth=linewidth,
        )

        if colIdx == 0:
            ax[peakRow][colIdx].set_ylabel(detectThisTrace)

        # overlay peak detection (onset, peak, decay) from dfMaster
        dfMasterOne = dfMaster.loc[dfMaster['Cell ID'] == cellID]
        dfMasterOne = dfMasterOne.loc[dfMasterOne['Condition'] == cond]
        dfMasterOne = dfMasterOne.loc[dfMasterOne['Repeat'] == epoch]
        dfMasterOne = dfMasterOne.loc[dfMasterOne['ROI Label'] == roiLabel]

        # onset
        xPlot = dfMasterOne['Onset (s)']
        yPlot = dfMasterOne['Onset Int']
        ax[peakRow][colIdx].plot(xPlot, yPlot, 'co', markersize=markersize)

        # peak
        xPlot = dfMasterOne['Peak (s)']
        yPlot = dfMasterOne['Peak Int']
        ax[peakRow][colIdx].plot(xPlot, yPlot, 'ro', markersize=markersize)

        # decay
        xPlot = dfMasterOne['Decay (s)']
        yPlot = dfMasterOne['Decay Int']
        ax[peakRow][colIdx].plot(xPlot, yPlot, 'mo', markersize=markersize)

        # plot ystat across conditions
        plotStatSwarm(
            dfMean, 'Number of Peaks', cellID, epoch, roiLabel, ax[plotRow][0]
        )

        # make 2x swarm plot (height, mass)
        plotStatSwarm(
            dfMaster, 'Peak Height', cellID, epoch, roiLabel, ax[plotRow][1]
        )
        plotStatSwarm(
            dfMaster, 'Area Under Peak', cellID, epoch, roiLabel, ax[plotRow][2]
        )

        if numCols > 3:
            # fig.delaxes(ax[plotRow][3])
            ax[plotRow][3].set_visible(False)

        fig.tight_layout()

    return fig, ax, imgDataDict

