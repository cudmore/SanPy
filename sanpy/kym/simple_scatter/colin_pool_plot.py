    # plot each cell id in each cond (control, ivab, thap)
import os
import sys
import ast
from typing import List, Optional
from pprint import pprint
from datetime import datetime

import numpy as np
import pandas as pd

# import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import matplotlib.patches as patches

import seaborn as sns
# import mplcursors

import tifffile

from sanpy.kym.kymRoiAnalysis import plotDetectionResults

from sanpy.kym.simple_scatter.colin_global import (loadMasterDfFile,
                          loadMeanDfFile,
                          getCellIdPdfFolder,
                          iterate_unique_cell_rows,
                          _loadKymRoiAnalysis,
                          # conditionOrder,
                          FileInfo,
                          )

from sanpy.kym.kymRoiAnalysis import KymRoi, KymRoiAnalysis, PeakDetectionTypes
from sanpy.kym.kymUtils import getAutoContrast

from sanpy.kym.logger import get_logger
logger = get_logger(__name__)

roiColorList = ['r', 'g', 'b', 'c', 'm', 'y']

# TODO: this is old, use ColinTraces
def _old_getDfTraces(tifFile, cellID, condition) -> pd.DataFrame:
    tifPath, tifName = os.path.split(tifFile)
    # cell id
    # 250318 SSAN R5 LS1
    # trace file
    # 250304 ISAN R3 LS1 c1-ch0-roiTraces.csv
    # 250304 ISAN R3 LS1 c2 Ivab-ch0-roiTraces.csv
    if condition == 'Control 0':
        cPrefix = 'c0'
        condStr = ''
    elif condition == 'Control':
        cPrefix = 'c1'
        condStr = ''
    elif condition == 'Ivab':
        cPrefix = 'c2'
        condStr = ' Ivab'
    elif condition == 'Thap':
        cPrefix = 'c3'
        condStr = ' Thap'

    roiTracesFile = f'{cellID} {cPrefix}{condStr}-ch0-roiTraces.csv'
    roiTracesPath = os.path.join(tifPath, 'sanpy-kym-roi-analysis', roiTracesFile)

    dfTraces = pd.read_csv(roiTracesPath, header=1)

    return dfTraces

# def plotOneKym(dfMaster, dfMean,
#                cellID,
#                condition,
#                epoch,
#                ):
def plotOneKym(tifPath:str) -> tuple[plt.Figure, plt.Axes]:
    """Plot all ROI in one kym image.
    
    This includes the kym image and one f/f0 plot per ROI.
    """
    # dfMeanPlot = dfMean[dfMean['Cell ID'] == cellID]
    # dfMeanPlot = dfMeanPlot[dfMeanPlot['Condition'] == condition]
    # dfMeanPlot = dfMeanPlot[dfMeanPlot['Epoch'] == epoch]

    # tifFile = dfMeanPlot.iloc[0]['Path']

    # load kymRoiAnalysis
    kymRoiAnalysis = _loadKymRoiAnalysis(tifPath)

    numRois = kymRoiAnalysis.numRoi

    fig, ax = plt.subplots(nrows=numRois+1,
                            ncols=1,
                            figsize=(8, 6),
                           sharex=True,
                            )
    fileInfo = FileInfo.from_path(tif_path=tifPath)
    
    fig.suptitle(f'"{fileInfo.cellID}" condition:"{fileInfo.condition}" epoch:{fileInfo.epoch}', fontsize=11)

    # despine top and right
    for oneAx in ax:
        sns.despine(top=True, right=True, ax=oneAx)

    linewidth = 1
    markersize = 5

    plotKymRoiTif(ax[0],
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
            logger.error(f'tifName:{tifName} roiIdx:{roiIdx} out of range for roiColorList:{roiColorList}')
            _color = 'k'

        kymRoi = kymRoiAnalysis.getRoi(roiLabelStr)
        kymRoiDetection = kymRoi.getDetectionParams(channel=0,
                                                    detectionType=PeakDetectionTypes.intensity)
        f0 = kymRoiDetection.getParam('f0 Value Percentile')

        # set the subplot title with f0 value and roi label
        _label = f'roi "{roiLabelStr}" f0:{f0:.1f}'
        ax[plotRow].set_title(_label, color=_color)

        timeTrace = kymRoiAnalysis.getAnalysisTrace(roiLabelStr, 'Time (s)', 0)
        f_f0Trace = kymRoiAnalysis.getAnalysisTrace(roiLabelStr, 'f/f0', 0)

        # timeTrace = dfTraces[f'ROI {roiLabelStr} Time (s)']
        # logger.info(f'timeTrace:{timeTrace}')
        # f_f0Trace = dfTraces[f'ROI {roiLabelStr} f/f0']  # hard coding f/f0 -->> df/f0
        ax[plotRow].plot(timeTrace, f_f0Trace,
                        'g',
                        linewidth=linewidth,
                        label=f'{fileInfo.cellID} {fileInfo.condition}')

        # in kymRoi, labels are str, in df they are int
        roiLabelInt = int(roiLabelStr)
        
        # theseRows = (dfMaster['Cell ID']==cellID) \
        #         & (dfMaster['ROI Number']==roiLabelInt) \
        #         & (dfMaster['Condition']==condition) \
        #         & (dfMaster['Epoch']==epoch)
        # dfPeaks = dfMaster.loc[theseRows]

        kymRoiResults = kymRoiAnalysis.getDataFrame(channel=0,
                                               peakDetectionType=PeakDetectionTypes.intensity,
                                               roiLabel=roiLabelInt)
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
            ax[plotRow].sharey(ax[plotRow-1])

    return fig, ax

def plotStatSwarm(dfMaster, yStat, cellID, epoch, roiLabel, ax):
    """plot a swarmplot for one kym, one roi
    
    x-axis is cond, y-axis is stat
    """
    theseRows = (dfMaster['Cell ID']==cellID) \
            & (dfMaster['Epoch']==epoch) \
            & (dfMaster['ROI Number']==roiLabel)
    dfSwarm = dfMaster.loc[theseRows]
    
    # Create new column with condition and epoch on separate lines
    # dfSwarm['Condition Epoch'] = dfSwarm['Condition Epoch'].str.replace(' ', '\n')
    dfSwarm.loc[:, 'Condition Epoch'] = dfSwarm['Condition Epoch'].str.replace(' ', '\n')
    # dfSwarm['Condition Epoch'] = dfSwarm['Condition Epoch Multiline'].astype('category')

    if yStat not in dfSwarm.columns:
        logger.warning(f'yStat:"{yStat}" not in dfSwarm.columns')
        logger.warning(f'dfSwarm.columns:{dfSwarm.columns}')
        return
    
    hue = 'Condition Epoch'

    # abb 20250623 mito atp, need to limit this so we do not plot non-existent conditions...
    hue_order = ['Control\n0', 'Control\n1', 'Ivab\n0', 'Thap\n0', 'FCCP\n0']

    plotDict = {
        'data': dfSwarm,  # df for one cell id
        'x': 'Condition Epoch',
        'y': yStat,
        # using new 'Condition Epoch' column
        'hue': hue,
        'order': hue_order
    }
    sns.swarmplot(ax=ax, **plotDict)

    # overlay mean bar
    markersize = 30
    sns.pointplot(data=dfSwarm,
                    x='Condition Epoch',
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
                order = hue_order,
                ax=ax,
                )

def plotRoiRects(ax:Axes,
                 kymRoiAnalysis: KymRoiAnalysis,
                 ):
    """Plot roi rect on a mpl axis.
    """
    secondsPerLine = kymRoiAnalysis.secondsPerLine

    roiLabels = kymRoiAnalysis.getRoiLabels()
    for roiIdx, kymRoiLabel in enumerate(roiLabels):
        try:
            roiColor = roiColorList[roiIdx]
        except IndexError:
            tifPath = kymRoiAnalysis.path
            tifName = os.path.basename(tifPath)
            logger.error(f'tifName:{tifName} roiIdx:{roiIdx} out of range for roiColorList:{roiColorList}')
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
            height = - height

        rect = patches.Rectangle((left, top),
                                    width, height,
                                    linewidth=1,
                                    edgecolor=roiColor,
                                    facecolor='none')
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

def plotKymRoiTif(ax:Axes,
                  kymRoiAnalysis: KymRoiAnalysis,
                  roiLabelStr:str=None,
                  detectThisTrace:str=None,
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
        detectionParams = kymRoi.getDetectionParams(channel=channel,
                                                    detectionType=PeakDetectionTypes.intensity)
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
    extent=[left_sec, right_sec, 0, height] # [left, right, top, bottom]

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
    
    logger.info(f'plotting {_file} _min:{_min} _max:{_max} \
                image min:{_imgDataDisplay.min()} \
                image max:{_imgDataDisplay.max()}')

    ax.imshow(imgData,
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

def plotTif(path:str,
            ax:Axes,
            channel=0,
            f0:float=None,
            detectThisTrace:str = None,
            roiRect:List[int] = None,
            cond:str = None,  # debug
            roiLabelStr:str = None,
            secondsPerLine:float = None,
            umPerPixel:float = None,  # debug
            ) -> np.ndarray:
    """Plot clipped roi for one ROI and its tif
    """
    from sanpy.bAnalysis_ import bAnalysis
    ba = bAnalysis(path)
    imgData = ba.fileLoader._tif  # list of color channel images
    imgData = imgData[channel]
    
    if f0 is not None:
        if detectThisTrace == 'f/f0':
            imgData = imgData / f0
            imgData = imgData.astype(np.int16)
        elif detectThisTrace == 'df/f0':
            imgData = (imgData - f0) / f0
            imgData = imgData.astype(np.int16)
        else:
            logger.error(f'detectThisTrace:{detectThisTrace} not supported')
            return

    # _tifFile = os.path.split(path)[1]

    if roiRect is not None:
        left = roiRect[0]
        top = roiRect[1]
        right = roiRect[2]
        bottom = roiRect[3]

        # width = right - left
        height = top - bottom

        # clip to [l, t, r, b]
        imgData = imgData[bottom:top, left:right]

    # numcols = height
    # numrows = width
    if secondsPerLine is not None:
        left_sec = left * secondsPerLine
        right_sec = right * secondsPerLine
        # top_um = top * umPerPixel
        # bottom_um = bottom * umPerPixel
        # extent=[left_sec, right_sec, bottom_um, top_um] # [left, right, top, bottom]
        extent=[left_sec, right_sec, 0, height] # [left, right, top, bottom]
    else:
        extent=[left, right, 0, height] # [left, right, top, bottom]


    imgMin, imgMax = getAutoContrast(imgData)  # new 20240925, should mimic ImageJ

    # plot the roi kym, normalizaition is critical
    ax.imshow(imgData,
              cmap="Greens",
              origin='lower',
              aspect='auto',
              extent=extent,
              vmin=imgMin,
              vmax=imgMax,
              )

    # despine bottom and left
    if 0:
        ax.spines['bottom'].set_visible(False)
        ax.set_xticks([]) # Removes x-axis tick marks and labels

        ax.spines['left'].set_visible(False)
        ax.set_yticks([]) # Removes x-axis tick marks and labels

    # this removes labels, not ticks
    ax.xaxis.set_tick_params(which='both', labelbottom=False)
    sns.despine(bottom=True, left=True, ax=ax)

    # ax.set_aspect('auto')
    return imgData

def plotTif2(path:str,
             ax:Axes,
             channel=0,
             ):
    """Plot clipped roi for one ROI and its tif
    """
    from sanpy.bAnalysis_ import bAnalysis
    ba = bAnalysis(path)
    imgData = ba.fileLoader._tif  # list of color channel images
    imgData = imgData[channel]

    imgMin = imgData.min()
    imgMax = imgData.max()

    imgMin = np.percentile(imgData, 2)
    imgMax = np.percentile(imgData, 98)

    ax.imshow(imgData,
              cmap="Greens",
              origin='lower',
              aspect='auto',
              vmin=imgMin,
              vmax=imgMax,
              )

    ax.xaxis.set_tick_params(which='both', labelbottom=False)
    sns.despine(bottom=True, left=True, ax=ax)

def plotRois():
    """Plot all rois f/f0 for one (cell id, condition, epoch)
    
    Use this to look at f/f0 for each roi in a kym.
    """
    dfMaster = loadMasterDfFile()
    dfMean = loadMeanDfFile()

    # list of cell id
    cellIDs = dfMean['Cell ID'].unique()
    for cellID in cellIDs:
        # using new api
        for row in iterate_unique_cell_rows(dfMean, cellID):
            condition = row['Condition']
            epoch = row['Epoch']
            dateStr = row['Date']
            dateStr = str(dateStr)  # dateStr is coming in as np.int64 (makes sense)
            regionStr = row['Region']
            tifPath = row['Path']

            _tifFile = os.path.split(tifPath)[1]
            _tifFile, _ = os.path.splitext(_tifFile)

            # logger.info(f'cellID:"{cellID}" condition:"{condition}" epoch:"{epoch}" Date:"{row["Date"]}"')

            # plot all roi for one kym
            fig, ax = plotOneKym(tifPath)

            # save the figure
            pdfPath = getCellIdPdfFolder(pdfOutputType='Per Cell ROI Plots',
                                        cellId=cellID,
                                        dateStr=dateStr,
                                        regionStr=regionStr)
            # pdfFilePath = os.path.join(pdfPath, f'{cellID} ROIs.pdf')
            pdfFilePath = os.path.join(pdfPath, f'{_tifFile} ROIs.pdf')
            logger.info(f'saving pdfFilePath:{pdfFilePath}')
            
            plt.savefig(pdfFilePath, format="pdf", dpi=300)
            plt.close()

def _exportClips(cellID):
    """Export image clips and traces.

    Traverse all conditions for one cell id and roi label
    """

    logger.info('')
    
    channel = 0

    dfMean = loadMeanDfFile()
    
    theseRows = (dfMean['Cell ID']==cellID) \
            & (dfMean['Condition']==condition) \
            & (dfMean['Epoch']==epoch)
    dfMeanOne = dfMean.loc[theseRows]

    regionStr = dfMeanOne.iloc[0]['Region']
    dateStr = dfMeanOne.iloc[0]['Date']
    dateStr = str(dateStr)  # dateStr is coming in as np.int64 (makes sense)
    tifPath = dfMeanOne.iloc[0]['Path']
    
    pdfPath = getCellIdPdfFolder(pdfOutputType='Per Cell Cond Plots',
                                 cellId=cellID,
                                 dateStr=dateStr,
                                 regionStr=regionStr)
    # clipsPath = os.path.join(pdfPath, 'clips')
    # os.makedirs(clipsPath, exist_ok=True)

    # logger.info(f'region:{regionStr} date:{dateStr} conditions:{conditions}')

    # we will save one csv with columns across each condition
    dfSaveTraces = pd.DataFrame()
        # load the kymRoiAnalysis
    ka = _loadKymRoiAnalysis(tifPath)
    for roiLabelStr in dfMeanOne['ROI Number'].unique():
        kymRoi = ka.getRoi(roiLabelStr)
        roiImgClipsDict = kymRoi.getRoiImgClips(channel)
        # logger.info(f'roiImgClipsDict:{roiImgClipsDict.keys()}')

        # main pdf across conditions is like:
        # 250225 ISAN R1 LS1 ROI 1
        clipFolder = f'{cellID} ROI {roiLabelStr}'
        clipFolderPath = os.path.join(pdfPath, clipFolder)
        os.makedirs(clipFolderPath, exist_ok=True)

        # theseClips = ['raw', 'f_f0', 'df_f0']
        theseClips = ['raw', 'f_f0', 'df_f0']
        for thisClip in theseClips:
            # logger.info(f'thisClip:{thisClip}')
            # logger.info(f'clip:{clip.shape}')

            # # save the clip
            clipFile = f'{cellID} ROI {roiLabelStr} {condition} {thisClip}.tif'
            clipPath = os.path.join(clipFolderPath, clipFile)
            # logger.info(f'  saving thisClip:{thisClip} to clipPath: {clipPath}')
            clip = roiImgClipsDict[thisClip]
            tifffile.imwrite(clipPath, clip)

        #
        # just use kymroianalysis api
        
        logger.error('TODO: use kymroianalysis api')
        return
        
        # save one df with f/f_0 for each condition
        # logger.info(f'dfAnalysisResults:{dfAnalysisResults.columns}')
        oneTraceCondition = _traces.getTraceDf(cellID, condition)
        # grab something like "ROI 3 f/f0"
        # ROI 1 Time (s)
        _time_key = f'ROI {roiLabelStr} Time (s)'  # redundant
        _f_f0_key = f'ROI {roiLabelStr} f/f0'
        _time = oneTraceCondition[_time_key]
        _f_f0 = oneTraceCondition[_f_f0_key]
        # make a df with just time and f_f0
        dfSaveTraces[_time_key] = _time  # redundant
        _cond_f_f0_key = f'{_f_f0_key} {condition} '
        dfSaveTraces[_cond_f_f0_key] = _f_f0

    # save dfSaveTraces
    dfTraceFile = f'{cellID} ROI {roiLabelStr} traces.csv'
    # logger.info(f'  saving dfTraceFile:{dfTraceFile}')
    dfSaveTraces.to_csv(os.path.join(clipFolderPath, dfTraceFile), index=False)

def new_plotCellID(dfMaster,
                   dfMean,
                   cellID,
                   roiLabelStr:int) -> tuple[plt.Figure, plt.Axes, dict]:
    roiLabelInt = int(roiLabelStr)
    channel = 0

    # get rows across all Epoch, each row becomes a column
    theseRows = (dfMean['Cell ID']==cellID) \
            & (dfMean['ROI Number']==roiLabelInt)    
    dfPlot = dfMean.loc[theseRows]
    # plot each (cond, epoch) as a column
    numCols = len(dfPlot)
    if numCols < 3:
        numCols = 3

    linewidth = 1
    markersize = 4  # for overlay of (onset, peak, decay)

    # always 3x3
    fig, ax = plt.subplots(nrows=3,
                            ncols=numCols,
                            figsize=(11, 8),
                            height_ratios=[1, 2, 2],  # shrink first row (kym image)
                            )
    
    _dateStr = datetime.now().strftime("%Y%m%d %H:%M")
    _suptitle = f'cell:"{cellID}" ROI:{roiLabelInt} saved:{_dateStr}'
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
            ax[imgRow][colIdx].sharey(ax[imgRow][colIdx-1])
            # all columns in peakRow share y axis
            ax[peakRow][colIdx].sharey(ax[peakRow][colIdx-1])
        
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
        epoch = row['Epoch']
        # tifFile = row['Tif File']
        tifPath = row['Path']
        
        axImg = ax[imgRow][colIdx]

        # load the kymRoiAnalysis
        ka = _loadKymRoiAnalysis(tifPath)
        kymRoi:KymRoi = ka.getRoi(roiLabelStr)

        secondsPerLine = kymRoi.secondsPerLine
        umPerPixel = kymRoi.umPerPixel
        from sanpy.kym.kymRoiAnalysis import PeakDetectionTypes
        _detectionParams = kymRoi.getDetectionParams(channel, PeakDetectionTypes.intensity)
        detectThisTrace = _detectionParams['detectThisTrace']
        f0_value_percentile = _detectionParams['f0 Value Percentile']
        polarity = _detectionParams['Polarity']
        roiRect = _detectionParams['ltrb']

        logger.info(f'  cond:{cond} epoch:{epoch} roiRect:{roiRect} f0:{f0_value_percentile}')

        imgData = plotTif(tifPath,
                ax=axImg,
                f0=f0_value_percentile,
                detectThisTrace=detectThisTrace,
                roiRect=roiRect,
                secondsPerLine=secondsPerLine,
                umPerPixel=umPerPixel,
                cond=cond,
                roiLabelStr=roiLabelStr,
                )

        axImg.set_title(f'"{cond} {epoch}" f0:{round(f0_value_percentile,1)} {polarity}',
                             fontsize=10)

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
        imgDataDict[tifPath] = {
            'roiLabelStr': roiLabelStr,
            'imgDataClip': imgData,
            'Time (s)': xPlot,
            'intRaw': raw,
            'f_f0': f_f0,
            'df_f0': df_f0,
        }

        ax[peakRow][colIdx].plot(xPlot, yPlot,
                                 color='g',
                                 linewidth=linewidth,
                                 )

        if colIdx == 0:
            ax[peakRow][colIdx].set_ylabel(detectThisTrace)

        # overlay peak detection (onset, peak, decay) from dfMaster
        dfMasterOne = dfMaster.loc[dfMaster['Cell ID']==cellID]
        dfMasterOne = dfMasterOne.loc[dfMasterOne['Condition']==cond]
        dfMasterOne = dfMasterOne.loc[dfMasterOne['Epoch']==epoch]
        dfMasterOne = dfMasterOne.loc[dfMasterOne['ROI Number']==roiLabelStr]
        
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
        plotStatSwarm(dfMean, 'Number of Spikes', cellID, epoch, roiLabelStr, ax[plotRow][0])

        # make 2x swarm plot (height, mass)
        plotStatSwarm(dfMaster, 'Peak Height', cellID, epoch, roiLabelStr, ax[plotRow][1])
        plotStatSwarm(dfMaster, 'Area Under Peak', cellID, epoch, roiLabelStr, ax[plotRow][2])

        if numCols > 3:
            # fig.delaxes(ax[plotRow][3])
            ax[plotRow][3].set_visible(False)

        fig.tight_layout()

    return fig, ax, imgDataDict


def _plotQuality():
    """Plot quality of detection for one cell id, roi.
    """
    _debug = False

    channel = 0

    dfMean = loadMeanDfFile()

    cellIDs = dfMean['Cell ID'].unique()

    if _debug:
        cellIDs = ['20250602 ISAN R1 LS3']

    for cellID in cellIDs:
        dfCellID = dfMean[dfMean['Cell ID'] == cellID]
        
        regionStr = dfCellID.iloc[0]['Region']
        dateStr = dfCellID.iloc[0]['Date']
        dateStr = str(dateStr)  # dateStr is coming in as np.int64 (makes sense)
        tifPath = dfCellID.iloc[0]['Path']

        roiLabels = dfCellID['ROI Number'].unique()
        logger.info(f'cellID:{cellID} roiLabels:{roiLabels}')

        kymRoiAnalysis = _loadKymRoiAnalysis(tifPath)

        # one plot per tif file roi
        for roiLabelStr in roiLabels:
            fig, ax = plotDetectionResults(kymRoiAnalysis, roiLabelStr, channel)

            pdfPath = getCellIdPdfFolder(pdfOutputType='ROI Quality Plots',
                                         cellId=cellID,
                                         dateStr=dateStr,
                                         regionStr=regionStr)
            _tifPath, _tifFile = os.path.split(tifPath)
            _tifFile, _ = os.path.splitext(_tifFile)
            pdfFilePath = os.path.join(pdfPath, f'{_tifFile} ROI {roiLabelStr}.pdf')
            # print(f'saving pdfPath:{pdfPath}')
            if _debug:
                pass
            else:
                plt.savefig(pdfFilePath, format="pdf")
                plt.close()
        
        if _debug:
            plt.show()

def plotCellID():
    """ Plot one pdf for each (cell id, roi), plot a column for each condition.

    Now with 'Epoch', we have one column for each (Condition, Epoch).
    """
    _debug = False

    dfMaster = loadMasterDfFile()
    dfMean = loadMeanDfFile()

    # abb depreciate this and just load kymRoiAnalysis?
    # _traces = ColinTraces(dfMaster, dfMean)
    
    numCellID = 0
    cellIDs = dfMean['Cell ID'].unique()
    logger.info(f'plotting {len(cellIDs)} cell ids')

    if _debug:
        cellIDs = ['20250602 ISAN R1 LS3']

    for cellID in cellIDs:
        dfCellID = dfMean[dfMean['Cell ID'] == cellID]
        
        regionStr = dfCellID.iloc[0]['Region']
        dateStr = dfCellID.iloc[0]['Date']
        dateStr = str(dateStr)  # dateStr is coming in as np.int64 (makes sense)

        # logger.info(f'dateStr:"{dateStr}" {type(dateStr)}')
        # sys.exit(1)

        roiLabels = dfCellID['ROI Number'].unique()
        logger.info(f'cellID:{cellID} roiLabels:{roiLabels}')

        for roiLabelStr in roiLabels:
            # plot one cell id across all (conditions, epochs)
            fig, ax, imgDataDict = \
                new_plotCellID(dfMaster, dfMean, cellID, roiLabelStr=roiLabelStr)
            # fig, ax = plotCellID(dfMaster=dfMaster, dfMean=dfMean, cellID=cellID, roiLabelStr=roiLabelStr)
            if fig is None:
                logger.warning('did not plot?')
                continue

            # save the figure
            pdfPath = getCellIdPdfFolder(pdfOutputType='Per Cell Cond Plots',
                                         cellId=cellID,
                                         dateStr=dateStr,
                                         regionStr=regionStr)
            pdfFilePath = os.path.join(pdfPath, f'{cellID} ROI {roiLabelStr}.pdf')
            # print(f'saving pdfPath:{pdfPath}')
            if _debug:
                pass
            else:
                plt.savefig(pdfFilePath, format="pdf")
                plt.close()

            """
            imgDataDict[tifPath] = {
            'roiLabelStr': roiLabelStr,
            'imgDataClip': imgData,
            'Time (s)': xPlot,
            'intRaw': raw,
            'f_f0': f_f0,
            'df_f0': df_f0,
                }
            """
            # make a new folder and save: tif clips and plotted detectThisTrace
            cellIdPath = os.path.join(pdfPath, cellID)
            os.makedirs(cellIdPath, exist_ok=True)
            _roiDir = os.path.join(cellIdPath, f'ROI {roiLabelStr}')
            os.makedirs(_roiDir, exist_ok=True)
            for _tif, _dict in imgDataDict.items():
                # fileInfo = FileInfo.from_path(_tif)
                imgDataClip = _dict['imgDataClip']

                _tifBase = os.path.split(_tif)[1]
                _tifBase, _ = os.path.splitext(_tifBase)
                _tifBase += f' ROI {roiLabelStr}'
                # make df from (raw, f_f0, df_f0)
                _df = pd.DataFrame()
                _df['Time (s)'] = _dict['Time (s)']
                _df['raw'] = _dict['intRaw']
                _df['f_f0'] = _dict['f_f0']
                _df['df_f0'] = _dict['df_f0']
                _tifBase = os.path.join(_roiDir, _tifBase)
                print(f'_tifBase:{_tifBase}')
                _df.to_csv(_tifBase + '.csv', index=False)
                tifffile.imwrite(_tifBase + '.tif', imgDataClip)
            
        #
        # _exportClips(cellID)

        numCellID += 1

        # if numCellID > 2:
        #     break

        if _debug:
            plt.show()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='SanPy kymograph plotting tools')
    parser.add_argument('command', 
                       choices=['plotcellid', 'plotrois', 'plotquality'],
                       help='Which plotting function to run')
    
    args = parser.parse_args()
    
    if args.command == 'plotcellid':
        # one pdf for a cell id across conditions and folder of clips, traces
        plotCellID()
    elif args.command == 'plotrois':
        # plot all rois f/f0 for one (cell id, condition)
        plotRois()
    elif args.command == 'plotquality':
        # plot quality of detection for one cell id, roi
        _plotQuality()
    else:
        print(f"Unknown command: {args.command}")
        print("Available commands: plotcellid, plotrois, plotquality")