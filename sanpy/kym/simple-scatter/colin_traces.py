import os
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

def _old_plotTraces(df):
    ssan_control_cell_id = df
    ssan_control_cell_id = ssan_control_cell_id[ssan_control_cell_id['Region']=='SSAN']
    ssan_control_cell_id = ssan_control_cell_id[ssan_control_cell_id['Condition']=='Control']
    ssanControlCellID = ssan_control_cell_id['Cell ID'].unique()
    # print(ssan_control_cell_id[['Region', 'Condition', 'Cell ID']])

    ssanTraceList = loadTraces(df, region='SSAN', condition='Control')
    isanTraceList = loadTraces(df, region='ISAN', condition='Control')

    ssan_ivab_TraceList = loadTraces(df, region='SSAN', condition='Ivab')
    isan_ivab_TraceList = loadTraces(df, region='ISAN', condition='Ivab')

    ssan_thaps_TraceList = loadTraces(df, region='SSAN', condition='Thap')
    isan_thaps_TraceList = loadTraces(df, region='ISAN', condition='Thap')

    linewidth = 1

    #
    # plot all ssan control traces
    if 0:
        numTraces = len(ssanTraceList)
        fig, ax = plt.subplots(nrows=numTraces, ncols=1, figsize=(8, 6), sharey=True)
        for idx, dfPlot in enumerate(ssanTraceList):
            # TODO: check this is correct
            # cellID = ssan_control_cell_id['Cell ID'].iloc[idx]
            cellID = ssanControlCellID[idx]
            
            timeTrace = dfPlot['ROI 1 Time (s)']
            f_f0Trace = dfPlot['ROI 1 f/f0']
            ax[idx].plot(timeTrace, f_f0Trace, linewidth=linewidth, label=cellID)
            ax[idx].title.set_text(f'SSAN Control {cellID}')

        mplcursors.cursor().connect(
            "add", lambda sel: sel.annotation.set_text(sel.artist.get_label()))

        # plt.show()

    fig, ax = plt.subplots(nrows=2, ncols=3, figsize=(8, 6), sharey=True)

    # SSAN
    for idx, dfPlot in enumerate(ssanTraceList):
        _cellID = ssanControlCellID[idx]
        timeTrace = dfPlot['ROI 1 Time (s)']
        f_f0Trace = dfPlot['ROI 1 f/f0']
        ax[0][0].plot(timeTrace, f_f0Trace, linewidth=linewidth, label=_cellID)
        ax[0][0].title.set_text('SSAN Control')

    for dfPlot in ssan_ivab_TraceList:
        timeTrace = dfPlot['ROI 1 Time (s)']
        f_f0Trace = dfPlot['ROI 1 f/f0']
        ax[0][1].plot(timeTrace, f_f0Trace, linewidth=linewidth)
        ax[0][1].title.set_text('SSAN Ivab')

    for dfPlot in ssan_thaps_TraceList:
        timeTrace = dfPlot['ROI 1 Time (s)']
        f_f0Trace = dfPlot['ROI 1 f/f0']
        ax[0][2].plot(timeTrace, f_f0Trace, linewidth=linewidth)
        ax[0][2].title.set_text('SSAN Thaps')

    # ISAN
    for dfPlot in isanTraceList:
        timeTrace = dfPlot['ROI 1 Time (s)']
        f_f0Trace = dfPlot['ROI 1 f/f0']
        ax[1][0].plot(timeTrace, f_f0Trace, linewidth=linewidth)
        ax[1][0].title.set_text('ISAN Control')

    for dfPlot in isan_ivab_TraceList:
        timeTrace = dfPlot['ROI 1 Time (s)']
        f_f0Trace = dfPlot['ROI 1 f/f0']
        ax[1][1].plot(timeTrace, f_f0Trace, linewidth=linewidth)
        ax[1][1].title.set_text('ISAN Ivab')

    for dfPlot in isan_thaps_TraceList:
        timeTrace = dfPlot['ROI 1 Time (s)']
        f_f0Trace = dfPlot['ROI 1 f/f0']
        ax[1][2].plot(timeTrace, f_f0Trace, linewidth=linewidth)
        ax[1][2].title.set_text('ISAN Thaps')

    import mplcursors
    mplcursors.cursor().connect(
        "add", lambda sel: sel.annotation.set_text(sel.artist.get_label()))

    # plt.show()

def _old_loadTraces(df, region, condition, roiNumberStr:str="1") -> List[pd.DataFrame]:
    """Load all traces for a region and condition.
    """
    # path is full path to raw tif file
    # that folder has a folder "sanpy-kym-roi-analysis"
    # with analysis traces
    # 250225 ISAN R1 LS1 c2 Ivab-ch0-roiTraces.csv
    # ROI 1 Time (s),
    # ROI 1 intRaw,
    # ROI 1 intDetrend,
    # ROI 1 df/f0,
    # ROI 1 f/f0,
    # ROI 1 Diameter (um),
    # ROI 1 Left Diameter (um),
    # ROI 1 Right Diameter (um)

    logger.info(f'region:{region} condition:{condition}')

    dfPlot = df
    dfPlot = dfPlot[dfPlot['Region']==region]
    dfPlot = dfPlot[dfPlot['Condition']==condition]

    # print(dfPlot[['Region', 'Cell ID', 'Condition', 'Tif File']])
    
    dfList = []

    for cellID in dfPlot['Cell ID'].unique():
        oneCellDf = dfPlot[dfPlot['Cell ID'] == cellID]
        # print(oneCellDf[['Region', 'Cell ID', 'Condition', 'Tif File']])
        tifPath = oneCellDf['Path'].iloc[0]
        _folder, _tifFile = os.path.split(tifPath)
        kymAnalysisFolder = os.path.join(_folder, 'sanpy-kym-roi-analysis')
        # my saved names are complicated, like:
        #  250225 ISAN R1 LS1 c2 Ivab-ch0-roiTraces.csv
        # they encode conditions and channels, assume there is ONE file
        # ending in roiTraces.csv
        # logger.info(f'kymAnalysisFolder:{kymAnalysisFolder}')
        fileNames = os.listdir(kymAnalysisFolder)
        thisFile = None
        for fileName in fileNames:
            if 'roiTraces.csv' in fileName:
                thisFile = fileName
                break
        if thisFile is None:
            logger.error(f'did not find roi trace path. Was analysis saved?')
            continue

        # finally, the roi trace file path is
        roiTracePath = os.path.join(kymAnalysisFolder, thisFile)
        dfRoiTrace = pd.read_csv(roiTracePath, header=1)
        dfList.append(dfRoiTrace)

    return dfList

def plotCellID(dfMaster, dfMean, cellID, roiLabelStr:str=1):
    """Plot all cond for one cell id and one roi

    Including img kym
    """

    # dfMasterPlot = dfMaster[dfMaster['Cell ID'] == cellID]
    dfMeanPlot = dfMean[dfMean['Cell ID'] == cellID]

    _region = dfMeanPlot.iloc[0]['Region']

    condKeys = dfMeanPlot['Condition'].unique()
    numCond = len(condKeys)

    logger.info(f'cellID:"{cellID}" _region:"{_region}" condKeys:{condKeys}')

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

    # mplcursors.cursor().connect(
    #     "add", lambda sel: sel.annotation.set_text(sel.artist.get_label()))

    return fig, ax

def plotAllRoi(dfMean, cellID):
    logger.info(f'=== cellID:{cellID}')
    
    dfPlot = dfMean[dfMean['Cell ID'] == cellID]

    conds = dfPlot['Condition'].unique()
    numCond = len(conds)
    fig, ax = plt.subplots(nrows=1,
                            ncols=numCond,
                            figsize=(8, 6),
                           sharex=True,
                           sharey=True,
                            # sharey='row'
                            )

    fig.suptitle(f'Cell ID:{cellID}')

    roiColorList = ['r', 'g', 'b', 'c', 'm', 'y', 'w']

    for condIdx, cond in enumerate(conds):
        dfOnePlot = dfPlot[dfPlot['Condition'] == cond]  # one row per roi
        tifPath = dfOnePlot.iloc[0]['Path']  # all roi from same path

        logger.info(f'condIdx:{condIdx}')

        from sanpy.bAnalysis_ import bAnalysis
        ba = bAnalysis(tifPath, verbose=False)
        imgData = ba.fileLoader._tif  # list of color channel images
        channel = 0
        imgData = imgData[channel]
        # imgData = imgData / f0_value_percentile

        minval = np.percentile(imgData, 2)
        maxval = np.percentile(imgData, 98)
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
            ax[condIdx].annotate(oneLabel, xy=(left, bottom), xytext=(left+5, bottom-20),
                                 arrowprops=dict(arrowstyle='->'),
                                 fontsize=12,
                                 weight='bold',
                                 color=roiColor)

    # save
    savePath = '/Users/cudmore/Desktop/AllKymRoi'
    pdfPath = os.path.join(savePath, f'{cellID}.pdf')
    print(f'saving pdfPath:{pdfPath}')
    plt.savefig(pdfPath, format="pdf")

def plotTif(path:str,
            ax:Axes,
            channel=0,
            f0:float=1,
            roiRect:List[int] = None):
    """Plot clipped roi for one ROI and its tif
    """
    from sanpy.bAnalysis_ import bAnalysis
    ba = bAnalysis(path)
    imgData = ba.fileLoader._tif  # list of color channel images
    imgData = imgData[channel]
    imgData = imgData / f0

    logger.info(f'imgData:{imgData.shape} f0:{f0} roiRect:{roiRect}')

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

    def plotCellID(self, cellID, roiLabelStr:str=1):
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
            tifPath = dfMean.iloc[0]['Path']
            roiRectStr = dfMean.iloc[0]['ROI Rect']
            roiRect = ast.literal_eval(roiRectStr)
            f0_value_percentile = dfMean.iloc[0]['f0_value_percentile']
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
        path = '/Users/cudmore/Dropbox/data/colin/2025/analysis-20250510-rhc/renamed-20250521/250225/ISAN/ISAN R1 LS3.tif.frames/250225 ISAN R1 LS3 c1.tif'
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(8, 6))
        f0 = 20
        roiRect = [0, 134, 2000, 119]
        plotTif(path, ax, f0=f0, roiRect=roiRect)
        plt.show()

    if 0:
        path = '/Users/cudmore/colin_peak_mean_20250521.csv'
        dfMean = pd.read_csv(path)
        count = 0
        for cellID in dfMean['Cell ID'].unique():
            plotAllRoi(dfMean, cellID)
            # if count>5:
            #     break
            count += 1
        print(f'{count} cell ids')
        # plt.show()

    # plot each cell id in each cond (control, ivab, thap)
    if 1:
        path = '/Users/cudmore/colin_peak_summary_20250521.csv'
        dfMaster = pd.read_csv(path)

        path = '/Users/cudmore/colin_peak_mean_20250521.csv'
        dfMean = pd.read_csv(path)

        for cellID in dfMean['Cell ID'].unique():
            dfCellID = dfMean[dfMean['Cell ID'] == cellID]
            roiLabels = dfCellID['ROI Number'].unique()
            for roiLabelStr in roiLabels:
                plotCellID(dfMaster=dfMaster, dfMean=dfMean, cellID=cellID, roiLabelStr=roiLabelStr)
                break

            break

        plt.show()