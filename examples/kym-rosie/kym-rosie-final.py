"""
For a condition like 'Female Old', load each '-fpAnalysis.csv'

,xFoot,yFoot,xPeak,yPeak,yPeakAmp
0,72.0,335.0,210.0,326.0,-9.0

The first column is the index,

    - Read x/y scale from Rosetta.csv
    - Add new columns in seconds and um
    - Add a few other columns (tifFile, condition, etc)

    - Finally, save a master database in a csv file
"""

import os, sys
import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns

#from mplcursors import cursor
import mplcursors

def findFileInRosetta_0(folderList, dfRosetta):
    """
    folderList: list of fullpath to folders with .tif files
    """
    for folderPath in folderList:
        tifFiles = os.listdir(folderPath)
        tifFiles = sorted(tifFiles)
        tifSkipped = []  # list of tif with no analysis
        for tifFile in tifFiles:
            if not tifFile.endswith('.tif'):
                continue
            
            tifFilePath = os.path.join(folderPath, tifFile)
            
            # can be None
            _secondsPerLine, _umPerPixel, _condition2 = \
                        findFileInRosetta(tifFilePath, dfRosetta)

            if _secondsPerLine is None or _umPerPixel is None:
                print(f'ERROR: did not find scale for file {tifFile}')
                tifSkipped.append(tifFile)
                continue
            
            parentFolder = os.path.split(folderPath)[1]
            
            # save into a -scale.txt file
            scaleFile = tifFile.replace('.tif', '-scale.txt')
            scaleFilePath = os.path.join(folderPath, scaleFile)
            contentsStr = f'umPerPixel={_umPerPixel}\n'
            contentsStr += f'secondsPerLine={_secondsPerLine}\n'
            print(f'_umPerPixel:{_umPerPixel} _secondsPerLine:{_secondsPerLine} {parentFolder}/{scaleFile}')

            # now that we have scale, modify each -analysis.csv file
            # time_ms
            # diameter_um
            analysisPath = tifFilePath.replace('.tif', '-analysis.csv')

            # if not os.path.isfile(analysisPath):
            #     print(f'ERROR DID NOT FIND FILE {analysisPath}')
            #     # load analysis2.csv and see if it has our scale columns
            #     # if not, use that
            #     analysisPath2 = tifFilePath.replace('.tif', '-analysis2.csv')
            #     _dfTmp = pd.read_csv(analysisPath2, header=1)
            #     if not 'diameter_pixels' in _dfTmp.columns:
            #         # this file has not been converted, use it
            #         print('REMEMBER: USING SAVE analysis2.csv that DOES NOT HAVE SCALE YET')
            #         analysisPath = analysisPath2
            #     sys.exit()

            if not os.path.isfile(analysisPath):
                print(f'ERROR: did not find analysis csv file: {os.path.split(analysisPath)[1]}')
                sys.exit()
            else:
                with open(analysisPath) as f:
                    headerLine = f.readline()
                
                print('headerLine:', headerLine)

                dfAnalysis = pd.read_csv(analysisPath, header=1)
                #
                old_time_ms = dfAnalysis['time_ms']  # this is in lines
                dfAnalysis['time_sec'] = old_time_ms * _secondsPerLine
                dfAnalysis['time_ms'] = old_time_ms * _secondsPerLine * 1000
                #
                old_diameter_um = dfAnalysis['diameter_um']  # this is in pixels
                dfAnalysis['diameter_pixels'] = old_diameter_um
                dfAnalysis['diameter_um'] = old_diameter_um * _umPerPixel
                saveAnalysisPath = tifFilePath.replace('.tif', '-analysis2.csv')
                print('    saveAnalysisPath:', os.path.split(saveAnalysisPath)[1])

                with open(saveAnalysisPath, 'w') as f:
                    f.write(headerLine)
                    #f.write('\n')

                dfAnalysis.to_csv(saveAnalysisPath, index=False, mode='a')
            
            # now that we have scale, modify each -fpAnalysis.csv file
            fpAnalysisPath = tifFilePath.replace('.tif', '-fpAnalysis.csv')
            if not os.path.isfile(fpAnalysisPath):
                print(f'=== ERROR DID NOT FIND FILE fpAnalysisPath:{fpAnalysisPath}')
            else:
                # xFoot	yFoot	xPeak	yPeak	yPeakAmp
                df_fpAnalysis = pd.read_csv(fpAnalysisPath, header=0)
                #
                xFoot = df_fpAnalysis['xFoot']  # this is in lines
                df_fpAnalysis['xFoot_sec'] = xFoot * _secondsPerLine
                yFoot = df_fpAnalysis['xFoot']  # this is in pixels
                df_fpAnalysis['yFoot_um'] = yFoot * _umPerPixel
                #
                xPeak = df_fpAnalysis['xPeak']  # this is in lines
                df_fpAnalysis['xPeak_sec'] = xPeak * _secondsPerLine
                yPeak = df_fpAnalysis['yPeak']  # this is in pixels
                df_fpAnalysis['yPeak_um'] = yPeak * _umPerPixel
                #
                yPeakAmp = df_fpAnalysis['yPeakAmp']  # this is in pixels
                df_fpAnalysis['yPeakAmp_um'] = yPeakAmp * _umPerPixel

                # save version 2
                _saveVersion2 = fpAnalysisPath.replace('-fpAnalysis.csv', '-fpAnalysis2.csv')
                print('  fpAnalysis _saveVersion2:', _saveVersion2)
                df_fpAnalysis.to_csv(_saveVersion2, index=False)

def findFileInRosetta(tifFilePath, dfRosetta):
    """
    tiffFile: full path to tiff file of raw data.
            This name is different from that in the rosetta with scale provided by xxx
    dfRosetta: Pandas DataFrame of rosetta file contents.
            We need to massage tifFileName into a new in rosetta.
    """
    _secondsPerLine = None
    _umPerPixel = None

    filePath, file = os.path.split(tifFilePath)
    
    # figure out x/y scale
    _origFile = file.replace('-fpAnalysis.csv', '')  # 
    _origFile = file.replace('.tif', '')  # 
    _origFile = _origFile.replace('filter median 1 C2-0-255 ', '')
    _origFile = _origFile.replace('filter median 1 C2-', '')
    _origFile = _origFile.replace('Filter median 1 C2-', '')
    _origFile = _origFile.replace('filter median 1C2-0-255 ', '')
    if _origFile.endswith(' '):
        _origFile = _origFile[0:-1]
    if _origFile == 'Cell 4 ISO 3min 1_19_21 male WT Young':
        _origFile = 'Cell 4 ISO 1_19_21 male WT Young'
    if _origFile == 'Cell 7 ISO 100nM 3min male WT young  5_21_21 CaT':
        _origFile = 'Cell 7 ISO male WT young  5_21_21 CaT'
    if _origFile == 'Cell 8 ISOl 1_19_21 male WT Young':
        _origFile = 'Cell 8 ISO1_19_21 male WT Young'
    if _origFile == 'Cell 2 ISO 3min 1_19_21 male WT Young':
        _origFile = 'Cell 2 ISO 1_19_21 male WT Young'
    #20220926
    if _origFile == 'Cell 3 CTRL 5_26_21 CaT male WT 2 years old':
        _origFile = 'Cell 3 male WT Old 5_26_21'
    if _origFile == 'Cell 4 Ctrl 1_19_21 male WT Young':
        _origFile = 'Cell 4 CTRL 1_19_21 male WT Young'

    # bin1 folder
    _origFile = _origFile.replace('filter median 1 C1-', '')

    # in rosetta "Cell 3 male WT Old 5_26_21"
    # corresponds to "Cell 3 CTRL 5_26_21 CaT male WT 2 years old"

    _loc = dfRosetta.loc[dfRosetta['fileName'] == _origFile]
    if len(_loc)==1:
        # += 1
        # fileName  secondsPerLine  umPerPixel
        _fileName = _loc['fileName'].values[0]
        _secondsPerLine = _loc['secondsPerLine'].values[0]
        _umPerPixel = _loc['umPerPixel'].values[0]
        #print(f'  {_fileName} _secondsPerLine:{_secondsPerLine} _umPerPixel:{_umPerPixel}')
    elif len(_loc)>1:
        print('  === === ERROR: found multiple entries for:', _origFile)
    else:
        print(f'  === === ERROR: did not find file in Rosetta:"{_origFile}"')
        print(f'    path:{filePath}')
        
    if 'ISO' in _origFile:
        #print('  -- ISO')
        condition2 = 'ISO'
    elif 'ctrl' in _origFile.lower():
        # they have a mixture of ['CTRL', 'Ctrl', 'ctrl']
        #print('  -- CTRL')
        condition2 = 'CTRL'
    else:
        #print(f'  --- UNDEFINED: "{_origFile}"')
        condition2 = 'UNKNOWN'

    return _secondsPerLine, _umPerPixel, condition2

def createPool():
    """
    For each file ending in '-fpAnalysis.csv'
        - load df
        - find secondsPerLine and umPerPixel in rosetta database
        - append columns after converting x pixel to seconds and y pixels to um
        - append columns for condition
        - append column for filename
    Save as one master DataFrame
    """
    finalDfSavePath = '/Users/cudmore/data/rosie'
    
    # path to original excel file with x/y scale
    rosieRosettaPath = '/Users/cudmore/data/rosie/rosie-rosetta.csv'
    dfRosetta = pd.read_csv(rosieRosettaPath)
    #print(dfRosetta)

    folderPath0 = '/Users/cudmore/data/rosie/Raw data for contraction analysis/Female Old'
    folderPath1 = '/Users/cudmore/data/rosie/Raw data for contraction analysis/Female Young'
    folderPath2 = '/Users/cudmore/data/rosie/Raw data for contraction analysis/Male Old'
    folderPath3 = '/Users/cudmore/data/rosie/Raw data for contraction analysis/Male Young'
    folderPath4 = '/Users/cudmore/data/rosie/Raw data for contraction analysis/Male Old AAV9 shBin1'
    
    folderList = [folderPath0, folderPath1, folderPath2, folderPath3, folderPath4]

    #
    # make a -scale.txt file for each .tif file
    # make -fpAnalysis2.csv using x/y scale
    #findFileInRosetta_0(folderList, dfRosetta)
    #
    #

    #sys.exit()

    dfMaster = pd.DataFrame()
    masterFileNum = 0

    for folderPath in folderList:
        _condition = os.path.split(folderPath)[1]

        print(f'\n=== start "{_condition}" {folderPath}')

        # for each .tif, look for 'postfixStr' file
        # to count number analyzed (and number not analyzed)
        postfixStr = '-fpAnalysis.csv'  # 'fp'  is foot peak analysis
        tifFiles = os.listdir(folderPath)
        tifFiles = sorted(tifFiles)
        numTif = 0
        numAnalyzed = 0
        tifSkipped = []  # list of tif with no analysis
        for tifFile in tifFiles:
            if not tifFile.endswith('.tif'):
                continue
            
            tifFilePath = os.path.join(folderPath, tifFile)
            _secondsPerLine, _umPerPixel, _condition2 = \
                        findFileInRosetta(tifFilePath, dfRosetta)
            
            numTif += 1
            analysisFile = os.path.splitext(tifFile)[0] + postfixStr
            analysisFile = os.path.join(folderPath, analysisFile)
            if os.path.isfile(analysisFile):
                numAnalyzed += 1
            else:
                tifSkipped.append(tifFile)
        print(f'Found {numTif} tif files and {numAnalyzed} analysis files, missing {numTif-numAnalyzed}')
        for _tifSkipped in tifSkipped:
            print('  _tifSkipped:', _tifSkipped)

        # dfMaster = pd.DataFrame()

        numFiles = 0
        numFilesFound = 0

        files = os.listdir(folderPath)
        files = sorted(files)
        _alreadyAnalyzed = []
        for file in files:
            if not file.endswith('-fpAnalysis.csv'):
                # look for version 2
                if not file.endswith('-fpAnalysis2.csv'):
                    continue
                else:
                    # version 2
                    print('   !!! using v2 file:', file)

            tifFile = file.replace('-fpAnalysis.csv', '.tif')
            tifFile = tifFile.replace('-fpAnalysis2.csv', '.tif')

            if tifFile in _alreadyAnalyzed:
                print('        already analyzed:', tifFile)
                continue
            
            numFiles += 1
            masterFileNum += 1

            _alreadyAnalyzed.append(tifFile)

            fullFilePath = os.path.join(folderPath, file)
            
            # load the diameter analysis
            # ,xFoot,yFoot,xPeak,yPeak,yPeakAmp
            dfDiam = pd.read_csv(fullFilePath)
            #print(dfDiameter[['xFoot', 'yFoot']])

            # figure out x/y scale
            _origFile = file.replace('-fpAnalysis.csv', '')  # no trailing space ' '
            _origFile = _origFile.replace('-fpAnalysis2.csv', '')  # no trailing space ' '
            _origFile = _origFile.replace('filter median 1 C2-0-255 ', '')
            _origFile = _origFile.replace('filter median 1 C2-', '')
            _origFile = _origFile.replace('Filter median 1 C2-', '')
            _origFile = _origFile.replace('filter median 1C2-0-255 ', '')
            if _origFile.endswith(' '):
                _origFile = _origFile[0:-1]
            if _origFile == 'Cell 4 ISO 3min 1_19_21 male WT Young':
                _origFile = 'Cell 4 ISO 1_19_21 male WT Young'
            if _origFile == 'Cell 7 ISO 100nM 3min male WT young  5_21_21 CaT':
                _origFile = 'Cell 7 ISO male WT young  5_21_21 CaT'
            if _origFile == 'Cell 8 ISOl 1_19_21 male WT Young':
                _origFile = 'Cell 8 ISO1_19_21 male WT Young'
            if _origFile == 'Cell 2 ISO 3min 1_19_21 male WT Young':
                _origFile = 'Cell 2 ISO 1_19_21 male WT Young'
            # bin1 folder
            _origFile = _origFile.replace('filter median 1 C1-', '')

            # in rosetta "Cell 3 male WT Old 5_26_21"
            # corresponds to "Cell 3 CTRL 5_26_21 CaT male WT 2 years old"

            _loc = dfRosetta.loc[dfRosetta['fileName'] == _origFile]
            if len(_loc)==1:
                numFilesFound += 1
                # fileName  secondsPerLine  umPerPixel
                _fileName = _loc['fileName'].values[0]
                _secondsPerLine = _loc['secondsPerLine'].values[0]
                _umPerPixel = _loc['umPerPixel'].values[0]
                #print(f'  {_fileName} _secondsPerLine:{_secondsPerLine} _umPerPixel:{_umPerPixel}')
            elif len(_loc)>1:
                print('  === === ERROR: found multiple entries for:', _origFile)
                continue
            else:
                print(f'  === === ERROR: did not find file in Rosetta:"{_origFile}"')
                continue
                
            if 'ISO' in _origFile:
                #print('  -- ISO')
                condition2 = 'ISO'
            elif 'ctrl' in _origFile.lower():
                # they have a mixture of ['CTRL', 'Ctrl', 'ctrl']
                #print('  -- CTRL')
                condition2 = 'CTRL'
            else:
                #print(f'  --- UNDEFINED: "{_origFile}"')
                condition2 = 'UNKNOWN'

            dfDiam['Condition'] = _condition  # from folder name (young male, old male, ...)
            dfDiam['Condition2'] = condition2
            
            # we found x/y scale, convert to time (seconds) and space (um/pixel)
            # dfDiameter has columns
            # ,xFoot,yFoot,xPeak,yPeak,yPeakAmp
            dfDiam['xFootSec'] = dfDiam['xFoot'] * _secondsPerLine
            dfDiam['yFootUm'] = dfDiam['yFoot'] * _umPerPixel
            dfDiam['xPeakSec'] = dfDiam['xPeak'] * _secondsPerLine
            dfDiam['yPeakUm'] = dfDiam['yPeak'] * _umPerPixel
            
            dfDiam['yPeakAmpUm'] = dfDiam['yPeakAmp'] * _umPerPixel

            dfDiam['diamRationUm'] = dfDiam['yPeakUm'] / dfDiam['yFootUm']

            dfDiam['secondsPerLine'] = _secondsPerLine
            dfDiam['umPerPixel'] = _umPerPixel

            dfDiam['tifFile'] = tifFile
            dfDiam['Short File'] = _origFile

            dfDiam['masterFileNum'] = masterFileNum

            dfMaster = pd.concat([dfMaster, dfDiam], ignore_index=True)  # dfMaster.append(dfDiam, ignore_index=True)

        print(f'  === DONE: _condition:"{_condition}" numFiles:{numFiles} numFilesFound:{numFilesFound}')
        print('    folderPath:', folderPath)
        #print('  dfMaster:')
        #print(dfMaster)

    # save
    if 1:
        finalNumFiles = len(dfMaster['tifFile'].unique())
        print(f'dfMaster has {finalNumFiles} files and {len(dfMaster)} rows')
        saveMasterDf = os.path.join(finalDfSavePath, 'kym-summary-20220926.csv')
        # we can plot data from this
        print(f'  saving to: {saveMasterDf}')
        dfMaster.to_csv(saveMasterDf)

def load0():
    finalDfSavePath = '/Users/cudmore/data/rosie'
    saveMasterDf = os.path.join(finalDfSavePath, 'kym-summary-20220926.csv')
    dfMaster = pd.read_csv(saveMasterDf, index_col=False)

    # for col in ['Condition', 'Condition2']:
    #     dfMaster[col] = dfMaster[col].astype('category')

    # make 'shortening' positive
    dfMaster['yPeakAmpUm_abs'] = abs(dfMaster['yPeakAmpUm'].values)

    # reject
    rejectTifFile = 'Filter median 1 C2-Cell 3 CTRL  Ca transients male wt 2 years old 12_17_20.tif'
    dfMaster = dfMaster[dfMaster.tifFile != rejectTifFile]

    dfMaster = dfMaster.reset_index(drop=True)

    return dfMaster, saveMasterDf

def plot0():
    def _myUpdateCursor(sel):
        hoverText = dfMaster["Condition"][sel.index] + '\n'
        hoverText += dfMaster["Condition2"][sel.index] + '\n'
        hoverText += dfMaster["Short File"][sel.index] + '\n'
        sel.annotation.set_text(hoverText)

    def _myUpdateCursor2(sel):
        hoverText = ''
        sel.annotation.set_text(hoverText)

    '''
    finalDfSavePath = '/Users/cudmore/data/rosie'
    saveMasterDf = os.path.join(finalDfSavePath, 'kym-summary-20220926.csv')
    dfMaster = pd.read_csv(saveMasterDf, index_col=False)

    for col in ['Condition', 'Condition2']:
        dfMaster[col] = dfMaster[col].astype('category')

    # make 'shortening' positive
    dfMaster['yPeakAmpUm_abs'] = abs(dfMaster['yPeakAmpUm'].values)

    # reject
    rejectTifFile = 'Filter median 1 C2-Cell 3 CTRL  Ca transients male wt 2 years old 12_17_20.tif'
    dfMaster = dfMaster[dfMaster.tifFile != rejectTifFile]
    '''
    
    dfMaster, saveMasterDf = load0()

    # Conditon is like (iso, ctrl)
    # Condition2 is like 'Female Old'
    style = 'Condition2'
    hue = 'Condition'
    xStat = 'masterFileNum'  #'Condition2'  #'masterFileNum'  # 'yFootUm'
    yStat = 'yPeakAmpUm_abs'  # amplitude in diam change (um)
    #yStat = 'diamRationUm' # amplitude of diam change normalized to starting diam

    # print('dfMaster:')
    # print(dfMaster[[style, hue, xStat, yStat]])
    # print(dfMaster['Condition2'])
    print(dfMaster.info())

    # exercise = sns.load_dataset("exercise")
    # print(exercise)
    # print(exercise.info())

    if 0:
        sns.scatterplot(x=xStat, y=yStat,
                    hue=hue,  # color
                    style=style,  # marker
                    data=dfMaster)

    # Conditon is like (iso, ctrl)
    # Condition2 is like 'Female Old'
    if 1:
        xStat = 'Condition'
        hue = 'Condition2'
        kind = 'box'
        # g = sns.catplot(x=xStat, y=yStat,
        #                 hue=hue,
        #                 data=dfMaster,
        #                 kind=kind)
        # g.map_dataframe(sns.stripplot, x=xStat, y=yStat, 
        #         hue=hue, palette=["#404040"], 
        #         alpha=0.6, dodge=True)

        hue_order = ['CTRL', 'ISO']

        ax = sns.barplot(x=xStat, y=yStat,
                        hue=hue,
                        hue_order=hue_order,
                        alpha=0.8,
                        errorbar='se',
                        data=dfMaster)

        # overlay raw data
        if 1:
            sns.stripplot(x=xStat, y=yStat,
                        hue=hue,
                        hue_order=hue_order,
                        data=dfMaster,
                        dodge=True, alpha=0.9,
                        ax=ax)
            #remove extra legend handles
            handles, labels = ax.get_legend_handles_labels()
            ax.legend(handles[2:], labels[2:], title='Condition', bbox_to_anchor=(1, 1.02), loc='upper left')

        #g.set_axis_labels("Day", "Total Bill");

    # crs = mplcursors.cursor(hover=True)
    # crs.connect(
    #     #"add", lambda sel: sel.annotation.set_text(dfMaster["Condition"][sel.index]))
    #     "add", _myUpdateCursor)
    # crs.connect(
    #     #"add", lambda sel: sel.annotation.set_text(dfMaster["Condition"][sel.index]))
    #     "remove", _myUpdateCursor2)

    # print('show')
    plt.show()

def debugPlot():
    exercise = sns.load_dataset("exercise")
    print(exercise)
    print(exercise.info())
    g = sns.catplot(x="time",
                y="pulse",
                hue="kind",
                data=exercise, 
                kind="box")

    plt.show()

def stats0():
    dfMaster,saveMasterDf = load0()

    # 1: This is for all diameter change measurements (no pooling)
    # apply all these functions to 'yPeakAmpUm' while grouping by 'Condition' :
    agg_func_math = {
        'yPeakAmpUm_abs':
        ['count', 'mean', 'median', 'min', 'max', 'std', 'var', 'sem']
    }
    # Condito2 is like (iso, ctrl)
    # Condition is like 'Female Old'
    #groups = ['tifFile', 'Condition', 'Condition2']
    groups = ['Condition', 'Condition2', 'tifFile']
    as_index = False  # want False, does not work !!!
    dfGroup = dfMaster.groupby(groups, as_index=as_index).agg(agg_func_math).round(3)

    # this works but switch 'Column' -> 'Column_'
    dfGroup.columns = ['_'.join(col) for col in dfGroup.columns]
    # remove trailing '_'
    dfGroup.columns = [col[:-1] if col.endswith('_') else col for col in dfGroup.columns]

    dfGroup = dfGroup.sort_values(['Condition', 'Condition2'])

    # move 'Male Old AAV9 shBin1' to end
    _moveThisCondition = 'Male Old AAV9 shBin1'
    _oneGroup = dfGroup[dfGroup.Condition!=_moveThisCondition]
    _anotherGroup = dfGroup[dfGroup.Condition==_moveThisCondition]
    dfGroup = pd.concat([_oneGroup,_anotherGroup])
    dfGroup = dfGroup.reset_index(drop=True)

    print(dfGroup)
    #print(dfGroup.columns)

    # save df grouped by 'tifFile'
    saveGroupDf = saveMasterDf.replace('.csv', '-grouped.csv')
    print('saving saveGroupDf:', saveGroupDf)
    dfGroup.to_csv(saveGroupDf)

    if 1:
        xStat = 'Condition'
        yStat = 'yPeakAmpUm_abs_mean'  # requires 'dfGroup.columns =...' above
        hue = 'Condition2'
        hue_order = ['CTRL', 'ISO']
        ax = sns.barplot(x=xStat, y=yStat,
                        hue=hue,
                        hue_order=hue_order,
                        errorbar='se',
                        alpha=0.8,
                        data=dfGroup)
        # overlay raw data
        if 1:
            sns.stripplot(x=xStat, y=yStat,
                        hue=hue,
                        hue_order=hue_order,
                        data=dfGroup,
                        dodge=True, alpha=0.9,
                        ax=ax)
            #remove extra legend handles
            handles, labels = ax.get_legend_handles_labels()
            ax.legend(handles[2:], labels[2:], title='Condition', bbox_to_anchor=(1, 1.02), loc='upper left')

        ax.set(xlabel='', ylabel='Cell Shortening (um)')

        # Hide the right and top spines
        ax.spines.right.set_visible(False)
        ax.spines.top.set_visible(False)

        fig = ax.get_figure()
        fig.savefig("/Users/cudmore/Desktop/out.png") 

        plt.show()

if __name__ == '__main__':
    """
    It would be interesting if there is a
    very small diameter change in old cardiomyocytes compared to young ones
    """
    
    createPool()

    #plot0()

    #debugPlot()

    stats0()

    plt.show()
