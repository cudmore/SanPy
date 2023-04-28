import os
from collections import OrderedDict
from pprint import pprint
from typing import Union, Dict, List, Tuple, Optional

import numpy as np
import pandas as pd

import sanpy

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class bExport:
    """Once analysis is performed with sanpy.bAnalysis.spikeDetect(),
        reports can be generated with the bExport class.

    Example reports are:

    - Generating reports as a Pandas DataFrame.
    - (depreciated) Saving reports as a Microsoft Excel file.
    - Saving reports as a CSV text files.
    """

    def __init__(self, ba):
        """
        Args:
            ba (sanpy.bAnalysis): A bAnalysis object that has had spikes detected with detectSpikes().
        """
        self.ba = ba
        self.sweepNumber = 0

    def old_report(self, theMin, theMax):
        """
        Get entire spikeDict as a Pandas DataFrame.

        Args:
            theMin (float): Start seconds of the analysis
            theMax (float): Stop seconds of the analysis

        Returns:
            df: Pandas DataFrame
        """
        if theMin is None or theMax is None:
            # return None
            theMin = 0
            theMax = self.ba.fileLoader.recordingDur

        logger.info(f"theMin:{theMin} theMax:{theMax}")

        df = self.ba.asDataFrame()
        df = df[(df["thresholdSec"] >= theMin) & (df["thresholdSec"] <= theMax)]

        # added when trying to make scatterwidget for one file
        df["Condition"] = ""  # df['condition1']
        df["File Number"] = ""  # df['condition2']
        df["Sex"] = ""  # df['condition3']
        df["Region"] = ""  # df['condition4']

        # make new column with sex/region encoded
        """
        tmpNewCol = 'RegSex'
        self.ba.masterDf[tmpNewCol] = ''
        for tmpRegion in ['Superior', 'Inferior']:
            for tmpSex in ['Male', 'Female']:
                newEncoding = tmpRegion[0] + tmpSex[0]
                regSex = self.ba.masterDf[ (self.ba.masterDf['Region']==tmpRegion) & (self.ba.masterDf['Sex']==tmpSex)]
                regSex = (self.ba.masterDf['Region']==tmpRegion) & (self.ba.masterDf['Sex']==tmpSex)
                print('newEncoding:', newEncoding, 'regSex:', regSex.shape)
                self.ba.masterDf.loc[regSex, tmpNewCol] = newEncoding
        """

        # want this but region/sex/condition are not defined
        # print('bExport.report()')
        # print(df.head())
        tmpNewCol = "CellTypeSex"
        cellTypeStr = df["cellType"].iloc[0]
        sexStr = df["sex"].iloc[0]
        # print('cellTypeStr:', cellTypeStr, 'sexStr:', sexStr)
        regSexEncoding = cellTypeStr + sexStr
        df[tmpNewCol] = regSexEncoding

        minStr = "%.2f" % (theMin)
        maxStr = "%.2f" % (theMax)
        minStr = minStr.replace(".", "_")
        maxStr = maxStr.replace(".", "_")

        # TODO: bytestreams are not strictly from a hdd folder or file
        fileName = self.ba.fileLoader.filename
        if fileName is not None:
            fileName, tmpExt = os.path.splitext(fileName)
            analysisName = fileName + "_s" + minStr + "_s" + maxStr
            # print('    minStr:', minStr, 'maxStr:', maxStr, 'analysisName:', analysisName)
        else:
            analysisName = "bytestream"
        df["analysisname"] = analysisName

        return df

    def report3(self, sweep='All',
                epoch='All',
                theMin : Optional[float] = None,
                theMax : Optional[float] = None,
                ) -> pd.DataFrame:
        """Generate a full report of all spike columns.
        
        Like what is save in csv but limited by sweep, epoch, etc
        """

        if self.ba.numSpikes == 0:
            logger.warning(f"did not find and spikes for summary")
            return None

        df = self.ba.asDataFrame()  # full df with all spikes

        spikeList = self.ba.getStat('spikeNumber', sweepNumber=sweep, epochNumber=epoch)

        # reduce to spikes in list
        df = df.loc[df['spikeNumber'].isin(spikeList)]

        if theMin is not None and theMax is not None:
            df = df[ (df['thresholdSec']>=theMin) & (df['thresholdSec']<theMax)]
        
        return df
    
    def report2(self, sweep='All',
                epoch='All',
                theMin : Optional[float] = None,
                theMax : Optional[float] = None,
                ) -> pd.DataFrame:

        """Generate a human readable report of spikes.
        Include spike times between theMin and theMax (Sec).

        Args:
            sweep ('All' or int') : 'All' for all sweeps or int for one sweep
            epoch ('All' or int) : 'All' for all epochs or int for one epoch
            theMin (float): Start seconds to save, inclusive
            theMax (float): Stop seconds to save, inclusive

        Returns:
            df: pd.DataFrame
        """

        spikeList = self.ba.getStat('spikeNumber', sweepNumber=sweep, epochNumber=epoch)

        newList = []
        for spikeIdx in spikeList:
            spike = self.ba.getOneSpikeDict(spikeIdx)
            
            # if current spike time is out of bounds
            # then continue (e.g. it is not between theMin (sec) and theMax (sec)
            spikeTime_sec = self.ba.fileLoader.pnt2Sec_(spike["thresholdPnt"])
            if theMin is not None and theMax is not None:
                if spikeTime_sec < theMin or spikeTime_sec > theMax:
                    continue

            spikeDict = (
                OrderedDict()
            )  # use OrderedDict so Pandas output is in the correct order

            spikeDict["Spike"] = spikeIdx
            spikeDict["Take Off Potential (s)"] = self.ba.fileLoader.pnt2Sec_(
                spike["thresholdPnt"]
            )
            spikeDict["Take Off Potential (ms)"] = self.ba.fileLoader.pnt2Ms_(
                spike["thresholdPnt"]
            )
            spikeDict["Take Off Potential (mV)"] = spike["thresholdVal"]
            spikeDict["AP Peak (ms)"] = self.ba.fileLoader.pnt2Ms_(spike["peakPnt"])
            spikeDict["AP Peak (mV)"] = spike["peakVal"]
            spikeDict["AP Height (mV)"] = spike["peakHeight"]
            spikeDict["Pre AP Min (mV)"] = spike["preMinVal"]
            # spikeDict['Post AP Min (mV)'] = spike['postMinVal']
            #
            # spikeDict['AP Duration (ms)'] = spike['apDuration_ms']
            spikeDict["Early Diastolic Duration (ms)"] = spike[
                "earlyDiastolicDuration_ms"
            ]
            spikeDict["Early Diastolic Depolarization Rate (dV/s)"] = spike[
                "earlyDiastolicDurationRate"
            ]  # abb 202012
            spikeDict["Diastolic Duration (ms)"] = spike["diastolicDuration_ms"]
            #
            spikeDict["Inter-Spike-Interval (ms)"] = spike["isi_ms"]
            spikeDict["Spike Frequency (Hz)"] = spike["spikeFreq_hz"]
            spikeDict["ISI (ms)"] = spike["isi_ms"]

            spikeDict["Cycle Length (ms)"] = spike["cycleLength_ms"]

            spikeDict["Max AP Upstroke (dV/dt)"] = spike["preSpike_dvdt_max_val2"]
            spikeDict["Max AP Upstroke (mV)"] = spike["preSpike_dvdt_max_val"]

            spikeDict["Max AP Repolarization (dV/dt)"] = spike[
                "postSpike_dvdt_min_val2"
            ]
            spikeDict["Max AP Repolarization (mV)"] = spike["postSpike_dvdt_min_val"]

            # half-width
            for widthDict in spike["widths"]:
                keyName = "width_" + str(widthDict["halfHeight"])
                spikeDict[keyName] = widthDict["widthMs"]

            spikeDict["File"] = self.ba.fileLoader.filename

            # errors
            # spikeDict['numError'] = spike['numError']
            spikeDict["errors"] = spike["errors"]

            # append
            newList.append(spikeDict)

        df = pd.DataFrame(newList)
        return df

    def getSummary(self,
                   sweep='All',
                    epoch='All',
                    theMin: float = None, 
                    theMax: float = None
                    ) -> pd.DataFrame:
        """Get analysis summary as df.
        
        This adds some header information to spike report bExport.report2().
        """

        if self.ba.numSpikes == 0:
            logger.warning(f"did not find and spikes for summary")
            return None

        # if theMin is None or theMax is None:
        #     theMin = 0
        #     theMax = self.ba.fileLoader.recordingDur

        #
        # cardiac style analysis to sheet 'cardiac'
        # human readable columns
        cardiac_df = self.report2(sweep=sweep,
                                  epoch=epoch,
                                  theMin=theMin,
                                  theMax=theMax)

        dDict = self.ba.getDetectionDict()

        #
        # header sheet
        headerDict = OrderedDict()
        filePath, fileName = os.path.split(self.ba.fileLoader.filepath)
        headerDict["File Name"] = [fileName]
        headerDict["File Path"] = [filePath]

        headerDict["Cell Type"] = [dDict["cellType"]]
        headerDict["Sex"] = [dDict["sex"]]
        headerDict["Condition"] = [dDict["condition"]]

        headerDict["Date Analyzed"] = [
            self.ba.analysisDate
        ]  # pulled from first detected spike
        headerDict["Time Analyzed"] = [self.ba.analysisTime]

        headerDict["Detection Type"] = [dDict["detectionType"]]
        headerDict["dV/dt Threshold"] = [dDict["dvdtThreshold"]]
        # headerDict['mV Threshold'] = [self.ba.mvThreshold] # abb 202012
        headerDict["Vm Threshold (mV)"] = [dDict["mvThreshold"]]
        # headerDict['Median Filter (pnts)'] = [self.ba.medianFilter]
        headerDict["Analysis Version"] = [sanpy.analysisVersion]
        headerDict["Interface Version"] = [sanpy.interfaceVersion]

        # headerDict['Analysis Start (sec)'] = [self.ba.startSeconds]
        # headerDict['Analysis Stop (sec)'] = [self.ba.stopSeconds]
        headerDict["Sweep Number"] = ["Default 0"]  # [self.ba.currentSweep]
        headerDict["Number of Sweeps"] = [self.ba.fileLoader.numSweeps]
        headerDict["Export Start (sec)"] = [
            float("%.2f" % (theMin))
        ]  # on export, x-axis of raw plot will be ouput
        headerDict["Export Stop (sec)"] = [
            float("%.2f" % (theMax))
        ]  # on export, x-axis of raw plot will be ouput

        # 'stats' has xxx columns (name, mean, sd, se, n)
        headerDict["stats"] = []

        ignoreColumns = ["Spike", "File"]
        for idx, col in enumerate(cardiac_df):
            if col in ignoreColumns:
                # in general, skip non numerical columns
                continue
            headerDict[col] = []

        # mean
        theMean = cardiac_df.mean(numeric_only=True)  # skipna default is True

        logger.info('cardiac_df:')
        print(cardiac_df)
        logger.info('theMean:')
        print(theMean)

        theMean["errors"] = ""
                
        # sd
        theSD = cardiac_df.std(numeric_only=True)  # skipna default is True
        theSD["errors"] = ""
        # se
        theSE = cardiac_df.sem(numeric_only=True)  # skipna default is True
        theSE["errors"] = ""
        # n
        theN = cardiac_df.count(numeric_only=True)  # skipna default is True
        theN["errors"] = ""

        statCols = ["mean", "sd", "se", "n"]
        for j, stat in enumerate(statCols):
            if j == 0:
                pass
            else:
                # need to append columns to keep Excel sheet columns in sync
                # for k,v in headerDict.items():
                #    headerDict[k].append('')

                headerDict["File Name"].append("")
                headerDict["File Path"].append("")
                headerDict["Cell Type"].append("")
                headerDict["Sex"].append("")
                headerDict["Condition"].append("")
                #
                headerDict["Date Analyzed"].append("")
                headerDict["Time Analyzed"].append("")
                headerDict["Detection Type"].append("")
                headerDict["dV/dt Threshold"].append("")
                headerDict["Vm Threshold (mV)"].append("")
                # headerDict['Median Filter (pnts)'].append('')
                headerDict["Analysis Version"].append("")
                headerDict["Interface Version"].append("")
                headerDict["Sweep Number"].append("")
                headerDict["Number of Sweeps"].append("")
                headerDict["Export Start (sec)"].append("")
                headerDict["Export Stop (sec)"].append("")

            # a dictionary key for each stat
            headerDict["stats"].append(stat)
            for idx, col in enumerate(cardiac_df):
                if col in ignoreColumns:
                    # in general, need to ignore string columns
                    # headerDict[col].append('')
                    continue
                # headerDict[col].append('')
                if stat == "mean":
                    headerDict[col].append(theMean[col])
                elif stat == "sd":
                    headerDict[col].append(theSD[col])
                elif stat == "se":
                    headerDict[col].append(theSE[col])
                elif stat == "n":
                    headerDict[col].append(theN[col])

        # end for j, stat
        # print('=== headerDict')
        # for k,v in headerDict.items():
        #    print(k, ':', v)

        # dict to pandas dataframe
        df = pd.DataFrame(headerDict).T
        df.insert(0, "", headerDict.keys(), allow_duplicates=True)

        return df

    def saveReport(
        self,
        savefile,
        theMin=None,
        theMax=None,
        saveExcel=True,
        alsoSaveTxt=True,
        verbose=True,
    ):
        """
        Save a spike report for detected spikes between theMin (sec) and theMax (sec).

        This is used by main interface 'Export Spike Report'

        Args:
            savefile (str): path to xlsx file
            theMin (float): start/stop seconds of the analysis
            theMax (float): start/stop seconds of the analysis
            saveExcel (bool):
            alsoSaveTxt (bool):

        Return:
            str: analysisName
            df: df
        """
        if theMin is None or theMax is None:
            theMin = 0
            theMax = self.ba.fileLoader.recordingDur

        # always grab a df to the entire analysis (not sure what I will do with this)
        # df = self.ba.report() # report() is my own 'bob' verbiage

        theRet = None

        logger.warning("NEVER SAVING EXCEL !!! dec 2022")
        saveExcel = False
        if saveExcel and savefile:
            # if verbose: print('    bExport.saveReport() saving user specified .xlsx file:', savefile)
            excelFilePath = savefile
            writer = pd.ExcelWriter(excelFilePath, engine="xlsxwriter")

            #
            # cardiac style analysis to sheet 'cardiac'
            cardiac_df = self.report2(theMin, theMax)  # report2 is more 'cardiac'

            dDict = self.ba.getDetectionDict()
            dateAnalyzed = self.ba.dateAnalyzed
            timeAnalyzed = self.ba.dateAnalyzed

            #
            # header sheet
            headerDict = OrderedDict()
            filePath, fileName = os.path.split(self.ba.filepath)
            headerDict["File Name"] = [fileName]
            headerDict["File Path"] = [filePath]

            headerDict["Cell Type"] = [dDict["cellType"]]
            headerDict["Sex"] = [dDict["sex"]]
            headerDict["Condition"] = [dDict["condition"]]

            # todo: get these params in ONE dict inside self.ba
            # dateAnalyzed, timeAnalyzed = self.ba.dateAnalyzed.split(' ')
            headerDict["Date Analyzed"] = [dateAnalyzed]
            headerDict["Time Analyzed"] = [timeAnalyzed]
            headerDict["Detection Type"] = [dDict["detectionType"]]
            headerDict["dV/dt Threshold"] = [dDict["dvdtThreshold"]]
            # headerDict['mV Threshold'] = [self.ba.mvThreshold] # abb 202012
            headerDict["Vm Threshold (mV)"] = [dDict["mvThreshold"]]
            # headerDict['Median Filter (pnts)'] = [self.ba.medianFilter]
            headerDict["Analysis Version"] = [sanpy.analysisVersion]
            headerDict["Interface Version"] = [sanpy.interfaceVersion]

            # headerDict['Analysis Start (sec)'] = [self.ba.startSeconds]
            # headerDict['Analysis Stop (sec)'] = [self.ba.stopSeconds]
            headerDict["Sweep Number"] = ["Default 0"]  # [self.ba.currentSweep]
            headerDict["Number of Sweeps"] = [self.ba.fileLoader.numSweeps]
            headerDict["Export Start (sec)"] = [
                float("%.2f" % (theMin))
            ]  # on export, x-axis of raw plot will be ouput
            headerDict["Export Stop (sec)"] = [
                float("%.2f" % (theMax))
            ]  # on export, x-axis of raw plot will be ouput

            # 'stats' has xxx columns (name, mean, sd, se, n)
            headerDict["stats"] = []

            ignoreColumns = ["Spike", "File"]
            for idx, col in enumerate(cardiac_df):
                if col in ignoreColumns:
                    # in general, need to ignore string columns
                    # headerDict[col].append('')
                    continue
                headerDict[col] = []

            # mean
            theMean = cardiac_df.mean()  # skipna default is True
            theMean["errors"] = ""
            # sd
            theSD = cardiac_df.std()  # skipna default is True
            theSD["errors"] = ""
            # se
            theSE = cardiac_df.sem()  # skipna default is True
            theSE["errors"] = ""
            # n
            theN = cardiac_df.count()  # skipna default is True
            theN["errors"] = ""

            statCols = ["mean", "sd", "se", "n"]
            for j, stat in enumerate(statCols):
                if j == 0:
                    pass
                else:
                    # need to append columns to keep Excel sheet columns in sync
                    # for k,v in headerDict.items():
                    #    headerDict[k].append('')

                    headerDict["File Name"].append("")
                    headerDict["File Path"].append("")
                    headerDict["Cell Type"].append("")
                    headerDict["Sex"].append("")
                    headerDict["Condition"].append("")
                    #
                    headerDict["Date Analyzed"].append("")
                    headerDict["Time Analyzed"].append("")
                    headerDict["Detection Type"].append("")
                    headerDict["dV/dt Threshold"].append("")
                    headerDict["Vm Threshold (mV)"].append("")
                    # headerDict['Median Filter (pnts)'].append('')
                    headerDict["Analysis Version"].append("")
                    headerDict["Interface Version"].append("")
                    headerDict["Sweep Number"].append("")
                    headerDict["Number of Sweeps"].append("")
                    headerDict["Export Start (sec)"].append("")
                    headerDict["Export Stop (sec)"].append("")

                # a dictionary key for each stat
                headerDict["stats"].append(stat)
                for idx, col in enumerate(cardiac_df):
                    if col in ignoreColumns:
                        # in general, need to ignore string columns
                        # headerDict[col].append('')
                        continue
                    # headerDict[col].append('')
                    if stat == "mean":
                        headerDict[col].append(theMean[col])
                    elif stat == "sd":
                        headerDict[col].append(theSD[col])
                    elif stat == "se":
                        headerDict[col].append(theSE[col])
                    elif stat == "n":
                        headerDict[col].append(theN[col])

            # print(headerDict)
            # for k,v in headerDict.items():
            #    print(k, v)

            # dict to pandas dataframe
            df = pd.DataFrame(headerDict).T
            df.to_excel(writer, sheet_name="summary")

            # set the column widths in excel sheet 'cardiac'
            columnWidth = 25
            worksheet = writer.sheets["summary"]  # pull worksheet object
            for idx, col in enumerate(df):  # loop through all columns
                worksheet.set_column(idx, idx, columnWidth)  # set column width

            #
            # 'params' sheet with all detection params
            # need to convert list values in dict to string (o.w. we get one row per item in list)
            exportDetectionDict = {}
            for k, v in dDict.items():
                # v is a dict from bDetection
                if isinstance(v, list):
                    v = f'"{v}"'
                exportDetectionDict[k] = v
            # print('  === "params" sheet exportDetectionDict:', exportDetectionDict)
            # df = pd.DataFrame(exportDetectionDict, index=[0]).T # index=[0] needed when dict has all scalar values
            detection_df = pd.DataFrame(exportDetectionDict).T
            detection_df.to_excel(writer, sheet_name="params")
            # worksheet is <class 'xlsxwriter.worksheet.Worksheet'>
            worksheet = writer.sheets["params"]  # pull worksheet object
            # set first 20 columns to columnWidth
            columnWidth = 18
            startCol = 0
            stopCol = 20  # xlswriter.worksheet does not care about the stop column
            worksheet.set_column(0, stopCol, columnWidth)  # set column width

            #
            # 'cardiac' sheet with human readable stat names
            cardiac_df.to_excel(writer, sheet_name="cardiac")

            # set the column widths in excel sheet 'cardiac'
            columnWidth = 20
            worksheet = writer.sheets["cardiac"]  # pull worksheet object
            for idx, col in enumerate(cardiac_df):  # loop through all columns
                worksheet.set_column(idx, idx, columnWidth)  # set column width

            #
            # mean spike clip
            theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(
                theMin, theMax, sweepNumber=self.sweepNumber
            )
            try:
                first_X = theseClips_x[0]  # - theseClips_x[0][0]
                # if verbose: print('    bExport.saveReport() saving mean clip to sheet "Avg Spike" from', len(theseClips), 'clips')
                df = pd.DataFrame(meanClip, first_X)
                df.to_excel(writer, sheet_name="Avg Spike")
            except IndexError as e:
                logger.warning("Got bad spike clips. Usually happend when 1-2 spikes")

            writer.save()

        #
        # save a csv text file
        #
        analysisName = ""
        if alsoSaveTxt:
            # this also saves
            analysisName, df0 = self.getReportDf(theMin, theMax, savefile)

            #
            # save mean spike clip

            not_used_theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(
                theMin, theMax, sweepNumber=self.sweepNumber
            )
            if len(theseClips_x) == 0:
                pass
            else:
                first_X = theseClips_x[0]  # - theseClips_x[0][0]
                first_X = np.array(first_X)
                first_X /= self.ba.fileLoader.dataPointsPerMs  # pnts to ms
                # if verbose: print('    bExport.saveReport() saving mean clip to sheet "Avg Spike" from', len(theseClips), 'clips')
                # dfClip = pd.DataFrame(meanClip, first_X)
                dfClip = pd.DataFrame.from_dict({"xMs": first_X, "yVm": meanClip})
                # load clip based on analysisname (with start/stop seconds)
                analysisname = df0["analysisname"].iloc[
                    0
                ]  # name with start/stop seconds
                logger.info(f"analysisname: {analysisname}")
                clipFileName = analysisname + "_clip.csv"
                tmpPath, tmpFile = os.path.split(savefile)
                tmpPath = os.path.join(tmpPath, "analysis")
                # dir is already created in getReportDf
                if not os.path.isdir(tmpPath):
                    os.mkdir(tmpPath)
                clipSavePath = os.path.join(tmpPath, clipFileName)
                logger.info(f"clipSavePath: {clipSavePath}")
                dfClip.to_csv(clipSavePath)
            #
            theRet = df0
        #
        return analysisName, theRet

    def getReportDf(self, theMin, theMax, savefile):
        """Get spikes as a Pandas DataFrame, one row per spike.

        Args:
            theMin (float): xxx
            theMax (float): xxx
            savefile (str): .xls file path

        Returns:
            df: Pandas DataFrame
        """
        filePath, fileName = os.path.split(os.path.abspath(savefile))

        dDict = self.ba.getDetectionDict()

        # make an analysis folder
        filePath = os.path.join(filePath, "analysis")
        if not os.path.isdir(filePath):
            logger.info(f"Making output folder: {filePath}")
            os.mkdir(filePath)

        textFileBaseName, tmpExtension = os.path.splitext(fileName)
        textFilePath = os.path.join(filePath, textFileBaseName + ".csv")

        # save header
        textFileHeader = OrderedDict()
        textFileHeader["file"] = self.ba.fileLoader.filename
        # textFileHeader['condition1'] = self.ba.condition1
        # textFileHeader['condition2'] = self.ba.condition2
        # textFileHeader['condition3'] = self.ba.condition3
        textFileHeader["cellType"] = dDict["cellType"]
        textFileHeader["sex"] = dDict["sex"]
        textFileHeader["condition"] = dDict["condition"]
        #
        textFileHeader["dateAnalyzed"] = self.ba.dateAnalyzed
        textFileHeader["detectionType"] = dDict["detectionType"]
        textFileHeader["dvdtThreshold"] = [dDict["dvdtThreshold"]]
        textFileHeader["mvThreshold"] = [dDict["mvThreshold"]]
        # textFileHeader['medianFilter'] = self.ba.medianFilter
        textFileHeader["startSeconds"] = "%.2f" % (theMin)
        textFileHeader["stopSeconds"] = "%.2f" % (theMax)
        # textFileHeader['startSeconds'] = self.ba.startSeconds
        # textFileHeader['stopSeconds'] = self.ba.stopSeconds
        textFileHeader["currentSweep"] = "Default 0"  # self.ba.currentSweep
        textFileHeader["numSweeps"] = self.ba.fileLoader.numSweeps
        # textFileHeader['theMin'] = theMin
        # textFileHeader['theMax'] = theMax

        # 20210125, this is not needed, we are saviing pandas df below ???
        headerStr = ""
        for k, v in textFileHeader.items():
            headerStr += k + "=" + str(v) + ";"
        headerStr += "\n"
        # print('headerStr:', headerStr)
        with open(textFilePath, "w") as f:
            f.write(headerStr)

        # df = self.report(theMin, theMax)
        df = self.ba.asDataFrame()

        # we need a column indicating (path), the original .abf file
        # along with (start,stop) which should make this analysis unique?
        minStr = "%.2f" % (theMin)
        maxStr = "%.2f" % (theMax)
        minStr = minStr.replace(".", "_")
        maxStr = maxStr.replace(".", "_")
        tmpPath, tmpFile = os.path.split(self.ba.fileLoader.filepath)
        tmpFile, tmpExt = os.path.splitext(tmpFile)
        analysisName = tmpFile + "_s" + minStr + "_s" + maxStr
        logger.info(f"minStr:{minStr} maxStr:{maxStr} analysisName:{analysisName}")
        df["analysisname"] = analysisName

        # should be filled in by self.ba.report
        # df['Condition'] =     df['condition1']
        # df['File Number'] =     df['condition2']
        # df['Sex'] =     df['condition3']
        # df['Region'] =     df['condition4']
        df["filename"] = [
            os.path.splitext(os.path.split(x)[1])[0] for x in df["file"].tolist()
        ]

        #
        logger.info("saving text file: {textFilePath}")
        # df.to_csv(textFilePath, sep=',', index_label='index', mode='a')
        df.to_csv(textFilePath, sep=",", index_label="index", mode="w")

        return analysisName, df


def test():
    path = "data/19114001.abf"
    ba = sanpy.bAnalysis(path)

    bd = sanpy.bDetection()  # gets default
    dDict = bd.getDetectionDict("SA Node")
    ba.spikeDetect(dDict)

    be = bExport(ba)
    df = be.getSummary()
    logger.info("")
    print(df)


if __name__ == "__main__":
    test()
