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

            spikeDict["Sweep"] = spike["sweep"]
            spikeDict["Epoch"] = spike["epoch"]
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
                    theMin: Optional[float] = None, 
                    theMax: Optional[float] = None
                    ) -> pd.DataFrame:
        """Get analysis summary as df.
        
        This adds some header information to spike report bExport.report2().
        """

        if self.ba.numSpikes == 0:
            logger.warning(f"did not find and spikes for summary")
            return None

        if theMin is None or theMax is None:
            theMin = 0
            theMax = self.ba.fileLoader.recordingDur

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

        headerDict["Cell Type"] = [self.ba.metaData["cell_type"]]
        headerDict["Sex"] = [self.ba.metaData["sex"]]
        headerDict["Condition"] = [self.ba.metaData["condition"]]

        headerDict["Date Analyzed"] = [
            self.ba.analysisDate
        ]  # pulled from first detected spike
        headerDict["Time Analyzed"] = [self.ba.analysisTime]

        headerDict["Detection Type"] = [dDict["detectionType"]]
        headerDict["dV/dt Threshold"] = [dDict["dvdtThreshold"]]
        # headerDict['mV Threshold'] = [self.ba.mvThreshold] # abb 202012
        headerDict["Vm Threshold (mV)"] = [dDict["mvThreshold"]]
        # headerDict['Median Filter (pnts)'] = [self.ba.medianFilter]
        # headerDict["Analysis Version"] = [analysisVersion]
        # headerDict["Interface Version"] = [interfaceVersion]

        # headerDict['Analysis Start (sec)'] = [self.ba.startSeconds]
        # headerDict['Analysis Stop (sec)'] = [self.ba.stopSeconds]
        headerDict["Sweep Number"] = [sweep]
        headerDict["Epoch Number"] = [epoch]
        headerDict["Number of Sweeps"] = [self.ba.fileLoader.numSweeps]
        headerDict["Export Start (sec)"] = [
            float("%.2f" % (theMin))
        ]  # on export, x-axis of raw plot will be ouput
        headerDict["Export Stop (sec)"] = [
            float("%.2f" % (theMax))
        ]  # on export, x-axis of raw plot will be ouput

        # 'stats' has xxx columns (name, mean, sd, se, n)
        headerDict["stats"] = []

        ignoreColumns = ["Sweep", "Epoch", "Spike", "File"]
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
                # headerDict["Analysis Version"].append("")
                # headerDict["Interface Version"].append("")
                headerDict["Sweep Number"].append("")
                headerDict["Epoch Number"].append("")
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
        verbose=True,
    ):
        """
        Save a spike report for detected spikes between theMin (sec) and theMax (sec).

        This is used by main interface 'Export Spike Report'

        Args:
            savefile (str): path to xlsx file
            theMin (float): start/stop seconds of the analysis
            theMax (float): start/stop seconds of the analysis

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

        #
        # save a csv text file
        analysisName = ""
        if 1:
            # this also saves
            analysisName, df0 = self.getReportDf(theMin, theMax, savefile)

            #
            # save mean spike clip

            not_used_theseClips, theseClips_x, meanClip = self.ba.spike_clips.get(
                theMin, theMax, sweep_number=self.sweepNumber
            )
            if len(theseClips_x) == 0:
                pass
            else:
                first_X = theseClips_x[0]  # - theseClips_x[0][0]
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

        # make an analysis folder
        filePath = os.path.join(filePath, "analysis")
        if not os.path.isdir(filePath):
            logger.info(f"Making output folder: {filePath}")
            os.mkdir(filePath)

        textFileBaseName, tmpExtension = os.path.splitext(fileName)
        textFilePath = os.path.join(filePath, textFileBaseName + ".csv")

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
