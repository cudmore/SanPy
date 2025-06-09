import os
import sys
import ast
from typing import List, Optional

import numpy as np
import pandas as pd

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import seaborn as sns
import mplcursors

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def _getDfTraces(tifFile, condition) -> pd.DataFrame:
    tifPath, tifName = os.path.split(tifFile)
    # cell id
    # 250318 SSAN R5 LS1
    # trace file
    # 250304 ISAN R3 LS1 c1-ch0-roiTraces.csv
    # 250304 ISAN R3 LS1 c2 Ivab-ch0-roiTraces.csv
    if condition == 'Control':
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

def plotOneKym(dfMaster, dfMean, cellID, condition):
    """Plot all ROI in one kym image.
    
    This includes the kym image and one f/f0 plot per ROI.
    """
    dfMeanPlot = dfMean[dfMean['Cell ID'] == cellID]
    dfMeanPlot = dfMeanPlot[dfMeanPlot['Condition'] == condition]

    tifFile = dfMeanPlot.iloc[0]['Path']

    dfTraces = _getDfTraces(tifFile, condition)

    rois = dfMeanPlot['ROI Number'].unique()
    numRois = len(rois)

    fig, ax = plt.subplots(nrows=numRois+1,
                            ncols=1,
                            figsize=(8, 6),
                        #    sharex=True,
                        #    sharey=True,
                            # sharey='row'
                            )
    fig.suptitle(f'{cellID} {condition}', fontsize=12)

    linewidth = 1
    markersize = 5

    for roiIdx, roiLabelStr in enumerate(rois):
        timeTrace = dfTraces[f'ROI {roiLabelStr} Time (s)']
        f_f0Trace = dfTraces[f'ROI {roiLabelStr} f/f0']  # hard coding f/f0 -->> df/f0
        ax[roiIdx+1].plot(timeTrace, f_f0Trace,
                        'g',
                        linewidth=linewidth,
                        label=f'{cellID} {condition}')

        theseRows = (dfMaster['Cell ID']==cellID) \
                & (dfMaster['ROI Number']==roiLabelStr) \
                & (dfMaster['Condition']==condition)
        dfPeaks = dfMaster.loc[theseRows]

        # onset
        xPlot = dfPeaks['Onset (s)']
        yPlot = dfPeaks['Onset Int']
        ax[roiIdx+1].plot(xPlot, yPlot, 'co', markersize=markersize)

        # peak
        xPlot = dfPeaks['Peak (s)']
        yPlot = dfPeaks['Peak Int']
        ax[roiIdx+1].plot(xPlot, yPlot, 'ro', markersize=markersize)

        # onset
        xPlot = dfPeaks['Decay (s)']
        yPlot = dfPeaks['Decay Int']
        ax[roiIdx+1].plot(xPlot, yPlot, 'mo', markersize=markersize)

    return fig, ax

def plotStatSwarm(dfMaster, yStat, cellID, roiLabel, ax):
    """plot a swarmplot for one kym, one roi
    
    x-axis is cond, y-axis is stat
    """
    theseRows = (dfMaster['Cell ID']==cellID) \
            & (dfMaster['ROI Number']==roiLabel)
    dfSwarm = dfMaster.loc[theseRows]
    
    plotDict = {
        'data': dfSwarm,  # df for one cell id
        'x': 'Condition',
        'y': yStat,
        'hue': 'Condition',
        'order': ['Control', 'Ivab', 'Thap']
    }
    sns.swarmplot(ax=ax, **plotDict)

    # overlay mean bar
    markersize = 30
    sns.pointplot(data=dfSwarm,
                    x='Condition',
                    y=yStat,
                hue='Condition',
                order=['Control', 'Ivab', 'Thap'],
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
                ax=ax,
                )

def plotCellID(dfMaster, dfMean, cellID, roiLabelStr:str):
    """Plot all cond for one cell id and one roi

    Including img kym
    """

    # dfMasterPlot = dfMaster[dfMaster['Cell ID'] == cellID]
    dfMeanPlot = dfMean[dfMean['Cell ID'] == cellID]

    _region = dfMeanPlot.iloc[0]['Region']

    condKeys = dfMeanPlot['Condition'].unique()

    linewidth = 1
    markersize = 5

    fig, ax = plt.subplots(nrows=3,
                            # ncols=numCond,
                            ncols=3,
                            figsize=(10, 6),
                            # sharey='row'
                            )
    
    # for the 3rd row, turn off sharey
    # 0
    ax[2][0]._shared_axes['y'].remove(ax[2][1])
    ax[2][0]._shared_axes['y'].remove(ax[2][2])
    # 1
    ax[2][1]._shared_axes['y'].remove(ax[2][0])
    ax[2][1]._shared_axes['y'].remove(ax[2][2])
    # 2
    ax[2][2]._shared_axes['y'].remove(ax[2][0])
    ax[2][2]._shared_axes['y'].remove(ax[2][1])

    fig.suptitle(f'{cellID} {_region} ROI #{roiLabelStr}', fontsize=12)
    
    imgRow = 0
    peakRow = 1
    plotRow = 2

    # despine top/right of each subplot
    for oneAx in ax.flatten():
        sns.despine(top=True, right=True, ax=oneAx)

    for idx, cond in enumerate(condKeys):
        #dfPlot = self.getTraceDf(cellID, cond)
        dfCondPlot = dfMeanPlot[dfMeanPlot['Condition']==cond]
        condTifFile = dfCondPlot.iloc[0]['Path']

        # form path to trace csv
        tifPath, tifName = os.path.split(condTifFile)
        # cell id
        # 250318 SSAN R5 LS1
        # trace file
        # 250304 ISAN R3 LS1 c1-ch0-roiTraces.csv
        # 250304 ISAN R3 LS1 c2 Ivab-ch0-roiTraces.csv
        if cond == 'Control':
            cPrefix = 'c1'
            condStr = ''
        elif cond == 'Ivab':
            cPrefix = 'c2'
            condStr = ' Ivab'
        elif cond == 'Thap':
            cPrefix = 'c3'
            condStr = ' Thap'

        roiTracesFile = f'{cellID} {cPrefix}{condStr}-ch0-roiTraces.csv'
        roiTracesPath = os.path.join(tifPath, 'sanpy-kym-roi-analysis', roiTracesFile)
        dfTraces = pd.read_csv(roiTracesPath, header=1)
      
        timeTrace = dfTraces[f'ROI {roiLabelStr} Time (s)']
        f_f0Trace = dfTraces[f'ROI {roiLabelStr} f/f0']  # hard coding f/f0 -->> df/f0
        ax[peakRow][idx].plot(timeTrace, f_f0Trace,
                        'g',
                        linewidth=linewidth,
                        label=f'{cellID} {cond}')
        if idx == 0:
            ax[peakRow][idx].set_xlabel('Time (s)')
            ax[peakRow][idx].set_ylabel('f/f0')
        
        theseRows = (dfMaster['Cell ID']==cellID) \
                & (dfMaster['ROI Number']==roiLabelStr) \
                & (dfMaster['Condition']==cond)
        dfPeaks = dfMaster.loc[theseRows]
        
        # plot just the roi of img data
        # Need to use _dfMean because _dfMaster has no rows when num peaks == 0
        theseRows_mean = (dfMean['Cell ID']==cellID) \
                & (dfMean['ROI Number']==roiLabelStr) \
                & (dfMean['Condition']==cond)
        _dfMeanCond = dfMean.loc[theseRows_mean]
        tifPath = _dfMeanCond.iloc[0]['Path']
        roiRectStr = _dfMeanCond.iloc[0]['ROI Rect']
        roiRect = ast.literal_eval(roiRectStr)
        f0_value_percentile = _dfMeanCond.iloc[0]['f0_value_percentile']
        # logger.info(f'plotTif for cellID:"{cellID}" cond:{cond} roiLabelStr:{roiLabelStr}')
        plotTif(tifPath, ax=ax[imgRow][idx], f0=f0_value_percentile, roiRect=roiRect, cond=cond, roi=roiLabelStr)

        ax[imgRow][idx].title.set_text(f'{cond} f0:{round(f0_value_percentile,1)}')

        # onset
        xPlot = dfPeaks['Onset (s)']
        yPlot = dfPeaks['Onset Int']
        ax[peakRow][idx].plot(xPlot, yPlot, 'co', markersize=markersize)

        # peak
        xPlot = dfPeaks['Peak (s)']
        yPlot = dfPeaks['Peak Int']
        ax[peakRow][idx].plot(xPlot, yPlot, 'ro', markersize=markersize)

        # onset
        xPlot = dfPeaks['Decay (s)']
        yPlot = dfPeaks['Decay Int']
        ax[peakRow][idx].plot(xPlot, yPlot, 'mo', markersize=markersize)

    # plot numbe of spikes per cond (for this one roi)
    theseRows = (dfMean['Cell ID']==cellID) \
            & (dfMean['ROI Number']==roiLabelStr)
    dfSwarm = dfMean.loc[theseRows]
    # print(dfSwarm['Cell ID', 'ROI Number', 'Condition', 'Number of Spikes'])
    plotStatSwarm(dfSwarm, 'Number of Spikes', cellID, roiLabelStr, ax[plotRow][0])

    # make 2x swarm plot (height, mass)
    plotStatSwarm(dfMaster, 'Peak Height', cellID, roiLabelStr, ax[plotRow][1])
    plotStatSwarm(dfMaster, 'Area Under Peak', cellID, roiLabelStr, ax[plotRow][2])

    # mplcursors.cursor().connect(
    #     "add", lambda sel: sel.annotation.set_text(sel.artist.get_label()))

    return fig, ax

def plotAllRoi(dfMean,
               cellID,
               justOneCond:str=None,
               doSave:bool=False):
    """Plot a tif with each roi overlaid as a rect.
    
    Use this to check our import from roimanager is working (colin).
    """
    logger.info(f'=== cellID:{cellID}')
    
    dfPlot = dfMean[dfMean['Cell ID'] == cellID]

    # to create date region folder on save
    regionStr = dfPlot.iloc[0]['Region']
    dateStr = dfPlot.iloc[0]['Date']
    dateStr = str(dateStr)

    if justOneCond:
        conds = [justOneCond]
    else:
        conds = dfPlot['Condition'].unique()
    numCond = len(conds)
    fig, ax = plt.subplots(nrows=1,
                            ncols=numCond,
                            figsize=(8, 6),
                           sharex=True,
                           sharey=True,
                            # sharey='row'
                            )
    if numCond == 1:
        ax = [ax]

    fig.suptitle(f'Cell ID:{cellID}')

    roiColorList = ['r', 'g', 'b', 'c', 'm', 'y', 'w']

    for condIdx, cond in enumerate(conds):
        dfOnePlot = dfPlot[dfPlot['Condition'] == cond]  # one row per roi
        tifPath = dfOnePlot.iloc[0]['Path']  # all roi from same path
        tifFile = os.path.split(tifPath)[1]

        # logger.info(f'condIdx:{condIdx}')
        # print(os.path.split(tifPath)[1])
        # print(tifPath)
        
        from sanpy.bAnalysis_ import bAnalysis
        ba = bAnalysis(tifPath, verbose=False)
        imgData = ba.fileLoader._tif  # list of color channel images
        channel = 0
        imgData = imgData[channel]
        # imgData = imgData / f0_value_percentile

        minval = np.percentile(imgData, 2)
        maxval = np.percentile(imgData, 98)
        # minval = np.percentile(imgData, 20)
        # maxval = np.percentile(imgData, 80)
        imgData = np.clip(imgData, minval, maxval)
        imgData = ((imgData - minval) / (maxval - minval)) * 255

        # imgData = ((imgData - imgData.min()) / (imgData.max()-imgData.min())) * 2**16

        ax[condIdx].imshow(imgData,
                # cmap="inferno",
                cmap="Grays",
                origin='lower',
                aspect='auto',
                #   extent=extent
                )

        # here, just show the image (f0 is for EACH ROI)
        # ax[condIdx].title.set_text(f'{cond} f0:{round(f0_value_percentile,1)}')
        
        # set title of subplot
        ax[condIdx].title.set_text(f'tif:{tifFile}')

        rois = dfOnePlot['ROI Number'].unique()
        # the order of roi labels is 'out of order' from original fiji import
        for roiLabel in rois:
            # logger.info(f'    === roiIdx:{roiIdx} roiLabel:{roiLabel}')
            
            roiLabel = int(roiLabel)
            roiColor = roiColorList[roiLabel]

            dfRoi = dfOnePlot[dfOnePlot['ROI Number'] == roiLabel]  # only one row
            if len(dfRoi) > 1:
                logger.error('')
                sys.exit(1)
            f0_value_percentile = dfRoi.iloc[0]['f0_value_percentile']
            roiRectStr = dfRoi.iloc[0]['ROI Rect']
            roiRect = ast.literal_eval(roiRectStr)
            left = roiRect[0]
            top = roiRect[1]
            right = roiRect[2]
            bottom = roiRect[3]

            width = right - left
            height = top - bottom
            import matplotlib.patches as patches
            rect = patches.Rectangle((left, bottom),
                                     width, height,
                                     linewidth=2,
                                     edgecolor=roiColor,
                                     facecolor='none')
            ax[condIdx].add_patch(rect)

            # label roi in image
            f0_value_percentile = round(f0_value_percentile,1)
            oneLabel = f'{roiLabel} f0:{f0_value_percentile}'
            ax[condIdx].annotate(oneLabel, xy=(left, bottom),
                                 xytext=(left+5, bottom-20),
                                 arrowprops=dict(arrowstyle='->'),
                                 fontsize=12,
                                 weight='bold',
                                 color=roiColor)

    # save
    if not doSave:
        pass
        # plt.show()
    else:
        from colin_global import getRootAnalysisFolder
        rootAnalysis = getRootAnalysisFolder()
        # make an 'CheckKymRoi' folder
        savePath = os.path.join(rootAnalysis, 'CheckKymRoi')
        if not os.path.exists(savePath):
            os.mkdir(savePath)
        
        # make date folders
        savePath = os.path.join(savePath, dateStr)
        if not os.path.exists(savePath):
            os.mkdir(savePath)

        # make region folders
        savePath = os.path.join(savePath, regionStr)
        if not os.path.exists(savePath):
            os.mkdir(savePath)

        pdfPath = os.path.join(savePath, f'{cellID}.pdf')
        print(f'saving pdfPath:{pdfPath}')
        plt.savefig(pdfPath, format="pdf")

def plotTif(path:str,
            ax:Axes,
            channel=0,
            f0:float=1,
            roiRect:List[int] = None,
            cond:str = None,  # debug
            roi:str = None,  # debug
            ):
    """Plot clipped roi for one ROI and its tif
    """
    from sanpy.bAnalysis_ import bAnalysis
    ba = bAnalysis(path)
    imgData = ba.fileLoader._tif  # list of color channel images
    imgData = imgData[channel]
    imgData = imgData / f0

    _debugStr = '' if cond is None else f'cond:{cond}'
    _debugStr += '' if roi is None else f' roi:{roi}'

    # logger.info(f'  imgData:{imgData.shape} f0:{f0} roiRect:{roiRect} {_debugStr}')

    left = roiRect[0]
    top = roiRect[1]
    right = roiRect[2]
    bottom = roiRect[3]

    # print(f'left:{type(left)} {left} top:{type(top)} {top} right:{type(right)} bottom:{type(bottom)}')

    width = right - left
    height = top - bottom

    # ax.set_ylim(bottom=bottom, top=top)
    # ax.set_xlim(left=left, right=right)

    # clip to [l, t, r, b]
    imgData = imgData[bottom:top, left:right]
    # roiImg = np.copy(roiImg)

    # import matplotlib.patches as patches
    # rect = patches.Rectangle((left, bottom), width, height, linewidth=1, edgecolor='r', facecolor='none')
    # ax.add_patch(rect)

    numcols = height
    numrows = width
    # extent=[0, numcols, 0, numrows]
    ax.imshow(imgData,
              cmap="inferno",
              origin='lower',
              aspect='auto',
            #   extent=extent
              )

    ax.spines['bottom'].set_visible(False)
    ax.set_xticks([]) # Removes x-axis tick marks and labels
    # ax.spines['left'].set_visible(False)

    ax.set_aspect('auto')

class ColinTraces:
    def __init__(self, dfMaster, dfMean):
        self._dfMaster = dfMaster
        self._dfMean = dfMean
        
        self._traceDict = {}
        """Dict of dict, first key is cell id, second key(s) are conditions."""

        self._load()

    def loadOneTrace(self, cellID, cond):
        try:
            _dfMaster = self._traceDict[cellID][cond]
            logger.info(f'already loaded')
            return
        except (KeyError) as e:
            logger.error(e)
        
        logger.info(f'loading {cellID} {cond}')
        if cellID not in self._traceDict.keys():
            self._traceDict[cellID] = {}

        df = self._dfMaster
        oneCellDf = df[df['Cell ID'] == cellID]

        _region = oneCellDf['Region'].iloc[0]
        self._traceDict[cellID]['Region'] = _region

        oneCondDf = oneCellDf[oneCellDf['Condition'] == cond]
        tifPath = oneCondDf['Path'].iloc[0]

        _folder, _tifFile = os.path.split(tifPath)
        kymAnalysisFolder = os.path.join(_folder, 'sanpy-kym-roi-analysis')

        fileNames = os.listdir(kymAnalysisFolder)
        thisFile = None
        for fileName in fileNames:
            if 'roiTraces.csv' in fileName:
                thisFile = fileName
                break
        if thisFile is None:
            logger.error(f'did not find {cellID} "{cond}" roi trace path. Was analysis saved?')
            return

        # finally, the roi trace file path is
        roiTracePath = os.path.join(kymAnalysisFolder, thisFile)
        logger.info(f'loading roiTracePath:{roiTracePath}')
        dfRoiTrace = pd.read_csv(roiTracePath, header=1)

        # store traces
        self._traceDict[cellID][cond] = dfRoiTrace  

    def _load(self):
        df = self._dfMaster
        for cellID in df['Cell ID'].unique():
            self._traceDict[cellID] = {}
            
            oneCellDf = df[df['Cell ID'] == cellID]
            _region = oneCellDf['Region'].iloc[0]
            
            self._traceDict[cellID]['Region'] = _region
            
            # we want order (c, i, t), not necc the order in the df !!!
            conditions = oneCellDf['Condition'].unique()
            conditions = sorted(conditions)  # dumb luck that (c, i, t) is alphabetical
            for cond in conditions:
                oneCondDf = oneCellDf[oneCellDf['Condition'] == cond]
                tifPath = oneCondDf['Path'].iloc[0]
                _folder, _tifFile = os.path.split(tifPath)
                kymAnalysisFolder = os.path.join(_folder, 'sanpy-kym-roi-analysis')

                fileNames = os.listdir(kymAnalysisFolder)
                thisFile = None
                for fileName in fileNames:
                    if 'roiTraces.csv' in fileName:
                        thisFile = fileName
                        break
                if thisFile is None:
                    logger.error(f'did not find {cellID} "{cond}" roi trace path. Was analysis saved?')
                    continue

                # finally, the roi trace file path is
                roiTracePath = os.path.join(kymAnalysisFolder, thisFile)
                dfRoiTrace = pd.read_csv(roiTracePath, header=1)
                
                # logger.info(f'loaded {roiTracePath}')
                # logger.info(f'dfRoiTrace:{dfRoiTrace.columns}')

                self._traceDict[cellID][cond] = dfRoiTrace                
    
    def getCondKeys(self, cellID) -> List[str]:
        keys = list(self._traceDict[cellID].keys())
        keys.remove('Region')  # remove item by item value
        return keys
    
    def getTraceDf(self, cellID, cond:str):
        """Get one cond trace for a cell id.
        
        Columns are all analysis traces (raw, df/d0, f/f0, etc).
        """
        return self._traceDict[cellID][cond]
    
    def plotOneCond(self, cond:str, region:str=Optional[str]):
        """Plot all traces for one cond.
        
        Useful to pick bad traces.
        """
        dfPlot = self._dfMaster
        if region is not None:
            dfPlot = dfPlot[dfPlot['Region']==region]
        dfPlot = dfPlot[dfPlot['Condition']==cond]

        cellIDs = dfPlot['Cell ID'].unique()
        
        linewidth = 1

        # numCell = len(dfPlot)
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(8, 6))
        ax = [ax]
        ax[0].title.set_text(f'cond:{cond} region:{region}')

        for idx, cellID in enumerate(cellIDs):
            dfTrace = self.getTraceDf(cellID, cond)
            timeTrace = dfTrace['ROI 1 Time (s)']
            f_f0Trace = dfTrace['ROI 1 f/f0']
            ax[0].plot(timeTrace, f_f0Trace, linewidth=linewidth, label=cellID)

        mplcursors.cursor().connect(
            "add", lambda sel: sel.annotation.set_text(sel.artist.get_label()))

        # plt.show()

    def plotCellID(self, cellID, roiLabelStr:int=1):
        """Plot all cond for one cell id.

        Including img kym
        """

        _region = self._traceDict[cellID]['Region']
        condKeys = self.getCondKeys(cellID)
        numCond = len(condKeys)

        linewidth = 1
        markersize = 5

        fig, ax = plt.subplots(nrows=2,
                               ncols=numCond,
                               figsize=(8, 6),
                            #    sharex=True,
                            #    sharey=True,
                               sharey='row'
                               )
        fig.suptitle(f'{cellID} {_region} ROI #{roiLabelStr}', fontsize=12)
        
        imgRow = 0
        peakRow = 1

        # despine top/right of each subplot
        for oneAx in ax.flatten():
            sns.despine(top=True, right=True, ax=oneAx)

        for idx, cond in enumerate(condKeys):
            dfPlot = self.getTraceDf(cellID, cond)
            
            # logger.info(f'getting timeTrace from columns')
            # print(dfPlot.columns)
            
            timeTrace = dfPlot[f'ROI {roiLabelStr} Time (s)']
            f_f0Trace = dfPlot[f'ROI {roiLabelStr} f/f0']  # hard coding f/f0 -->> df/f0
            ax[peakRow][idx].plot(timeTrace, f_f0Trace,
                         'g',
                         linewidth=linewidth,
                         label=f'{cellID} {cond}')
            if idx == 0:
                ax[peakRow][idx].set_xlabel('Time (s)')
                ax[peakRow][idx].set_ylabel('f/f0')
            
            theseRows = (self._dfMaster['Cell ID']==cellID) \
                    & (self._dfMaster['ROI Number']==roiLabelStr) \
                    & (self._dfMaster['Condition']==cond)
            dfPeaks = self._dfMaster.loc[theseRows]
            
            # plot just the roi of img data
            # Need to use _dfMean because _dfMaster has no rows when num peaks == 0
            theseRows_mean = (self._dfMean['Cell ID']==cellID) \
                    & (self._dfMean['ROI Number']==roiLabelStr) \
                    & (self._dfMean['Condition']==cond)
            dfMean = self._dfMean.loc[theseRows_mean]
            if len(dfMean) == 0:
                logger.error(f'did not get a mean df to plot???')
                return None, None
            
            tifPath = dfMean.iloc[0]['Path']
            roiRectStr = dfMean.iloc[0]['ROI Rect']
            roiRect = ast.literal_eval(roiRectStr)
            f0_value_percentile = dfMean.iloc[0]['f0_value_percentile']
            logger.info(f'plotTif for cellID:"{cellID}" cond:{cond} roiLabelStr:{roiLabelStr}')
            plotTif(tifPath, ax=ax[imgRow][idx], f0=f0_value_percentile, roiRect=roiRect)

            ax[imgRow][idx].title.set_text(f'{cond} f0:{round(f0_value_percentile,1)}')

            # onset
            xPlot = dfPeaks['Onset (s)']
            yPlot = dfPeaks['Onset Int']
            ax[peakRow][idx].plot(xPlot, yPlot, 'co', markersize=markersize)

            # peak
            xPlot = dfPeaks['Peak (s)']
            yPlot = dfPeaks['Peak Int']
            ax[peakRow][idx].plot(xPlot, yPlot, 'ro', markersize=markersize)

            # onset
            xPlot = dfPeaks['Decay (s)']
            yPlot = dfPeaks['Decay Int']
            ax[peakRow][idx].plot(xPlot, yPlot, 'mo', markersize=markersize)

        mplcursors.cursor().connect(
            "add", lambda sel: sel.annotation.set_text(sel.artist.get_label()))

        # plt.show()

        return fig, ax
    
if __name__ == '__main__':

    if 0:
        # plot one kym to check rois
        from colin_global import loadMeanDfFile
        dfMean = loadMeanDfFile()
        cellID = '250225 ISAN R2 LS2'
        plotAllRoi(dfMean, cellID, justOneCond='Control', doSave=False)
        plotAllRoi(dfMean, cellID, justOneCond='Ivab', doSave=False)
        plotAllRoi(dfMean, cellID, justOneCond='Thap', doSave=False)
        plt.show()

    if 0:
        # plot each cell id across conditions
        # overlay all roi and label them
        # this is used to check we have imported rois correctly
        from colin_global import loadMeanDfFile
        dfMean = loadMeanDfFile()
        # dfMean = pd.read_csv(path)
        count = 0
        for cellID in dfMean['Cell ID'].unique():
            plotAllRoi(dfMean, cellID, doSave=True)
            # if count>5:
            #     break
            plt.close()
            count += 1
        print(f'{count} cell ids')
        # plt.show()

    # plot all rois f/f0 for one (cell id, condition)
    # use this to look at f/f0 for each roi in a kym
    if 0:
        from colin_global import loadMasterDfFile, loadMeanDfFile
        dfMaster = loadMasterDfFile()
        dfMean = loadMeanDfFile()

        numCellID = 0
        for cellID in dfMean['Cell ID'].unique():
            dfCellID = dfMean[dfMean['Cell ID'] == cellID]
            conditions = dfCellID['Condition'].unique()
            for condition in conditions:
                fig, ax = plotOneKym(dfMaster, dfMean, cellID=cellID, condition=condition)
                break
            break
        plt.show()

    # plot each cell id in each cond (control, ivab, thap)
    if 1:
        from colin_global import loadMasterDfFile, loadMeanDfFile
        dfMaster = loadMasterDfFile()
        dfMean = loadMeanDfFile()

        numCellID = 0
        for cellID in dfMean['Cell ID'].unique():
            dfCellID = dfMean[dfMean['Cell ID'] == cellID]
            
            regionStr = dfCellID.iloc[0]['Region']
            dateStr = dfCellID.iloc[0]['Date']
            # dateStr is coming in as np.int64 (makes sense)
            dateStr = str(dateStr)

            # logger.info(f'dateStr:"{dateStr}" {type(dateStr)}')
            # sys.exit(1)

            roiLabels = dfCellID['ROI Number'].unique()
            logger.info(f'cellID:{cellID} roiLabels:{roiLabels}')

            for roiLabelStr in roiLabels:
                fig, ax = plotCellID(dfMaster=dfMaster, dfMean=dfMean, cellID=cellID, roiLabelStr=roiLabelStr)

                # save
                from colin_global import getRootAnalysisFolder
                rootAnalysis = getRootAnalysisFolder()
                # make an 'CheckKymRoi' folder
                savePath = os.path.join(rootAnalysis, 'Per Cell Cond Plots')
                if not os.path.exists(savePath):
                    os.mkdir(savePath)
                
                # make date folders
                savePath = os.path.join(savePath, dateStr)
                if not os.path.exists(savePath):
                    os.mkdir(savePath)

                # make region folders
                savePath = os.path.join(savePath, regionStr)
                if not os.path.exists(savePath):
                    os.mkdir(savePath)

                pdfPath = os.path.join(savePath, f'{cellID} ROI {roiLabelStr}.pdf')
                print(f'saving pdfPath:{pdfPath}')
                plt.savefig(pdfPath, format="pdf")
                
                plt.close()

                # break

            numCellID += 1
            # if numCellID > 0:
            #     break

        plt.show()