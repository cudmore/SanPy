import json
import os
from typing import List, Optional, Callable
from pprint import pprint

import numpy as np
import pandas as pd

import tifffile

import matplotlib.pyplot as plt
# from matplotlib.patches import Rectangle
# from scipy import ndimage
# from scipy.stats import linregress
# import warnings

from sanpy.bAnalysis_ import bAnalysis
from sanpy._util import _loadLineScanHeader
from sanpy.kym.kymRoiDetection import KymRoiDetection
from sanpy.kym.kymRoiResults import KymRoiResults
from sanpy.kym.kymRoiMetaData import KymRoiMetaData
from sanpy.kym.kymRoi import KymRoi, PeakDetectionTypes, myMonoExp, myDoubleExp

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

class KymRoiAnalysis:
    def __init__(
        self,
        path: str = None,
        imgData: List[np.ndarray] = None,
        kymRoiWidget=None,
        loadAnalysis: bool = False,
        loadImgData: bool = True,
        analysis_only: bool = False,
        dirty_callback_function: Callable = None,
    ):
        """
        Holds a number of kymRoi for one image file (multiple channels).

        Parameters
        ----------
        path : str
            Full path to .tif file
        imgData : List[np.ndarray]
            A list of equal sized 2d arrays, one item per image channel.
        kymRoiWidget : sanpy.kym.interface.KymRoiWidget
            During GUI runtime to update the statusbar
        loadAnalysis : bool
            Whether to load saved analysis (deprecated, always loads if available)
        loadImgData : bool
            Whether to load image data from file (ignored if analysis_only=True)
        analysis_only : bool
            If True, only load analysis results without image data. This is efficient
            for accessing previously saved analysis results without the overhead of
            loading large image files. Image data will be loaded on-demand when needed.
        dirty_callback_function : Callable
            A function to call when the analysis is marked as dirty.
            The function should take two arguments: tifPath (str) and isDirty (bool).
            Example: myCallback(tifPath: str, isDirty: bool) -> None
            This callback can be used to update UI elements or external systems
            when the dirty state of the analysis changes.
        """
        # logger.debug("KymRoiAnalysis: __init__ start path=%s analysis_only=%s loadImgData=%s", path, analysis_only, loadImgData)
        
        # logger.info(f"KymRoiAnalysis: __init__ start path={path} analysis_only={analysis_only} loadImgData={loadImgData}")

        # Set all instance attributes at the very start
        self._path = path
        self._imgData = imgData
        self._kymRoiWidget = kymRoiWidget
        self._loadAnalysis = loadAnalysis
        self._loadImgData = loadImgData
        self._analysis_only = analysis_only
        self._roiDict = {}
        self._kymDetectionParams = {}
        self._isDirty = False
        self._fakeScale = False
        self.dirty_callback_function = dirty_callback_function
        
        # Initialize metadata based on analysis_only mode
        if self._analysis_only:
            # logger.debug("KymRoiAnalysis: analysis_only mode, skipping image data loading")
            self._imgData = None
        else:
            # Load image data if requested
            if self._loadImgData and self._path is not None:
        
                ba = bAnalysis(self._path)
                self._imgData = ba.fileLoader._tif
                if not isinstance(self._imgData, List):
                    self._imgData = [self._imgData]
            else:
                # logger.debug("KymRoiAnalysis: image data loading skipped")
                pass

        # Initialize metadata
        self._kymRoiMetaData = KymRoiMetaData(self._path, self._imgData)
        # logger.debug("KymRoiAnalysis: metadata initialized")
        
        # Load analysis results if available (e.g. saved csv files)
        # logger.debug("KymRoiAnalysis: loading analysis results (loadAnalysis)")
        loadedHeaderDict = self.loadAnalysis()
        # logger.debug("KymRoiAnalysis: finished loadAnalysis")

        if loadedHeaderDict is not None:
            pass  # abb 20250728 all handled in KymRoiMetaData

            # # logger.info("KymRoiAnalysis: loaded header dict from analysis file")
            # # Only set metadata keys that are valid
            # logger.info('loadedHeaderDict:')
            # pprint(loadedHeaderDict)

            # valid_metadata_keys = [
            #     'Acq Date', 'Acq Time', 'secondsPerLine', 'umPerPixel',
            #     'Animal ID', 'Region', 'Cell Type', 'Cell ID', 'Condition', 'Note'
            # ]
            # for key in valid_metadata_keys:
            #     if key in loadedHeaderDict:
            #         self._kymRoiMetaData[key] = loadedHeaderDict[key]
        else:
            logger.info("KymRoiAnalysis: no analysis file found, loading Olympus header or using defaults")
            # Only try to load from Olympus header if we have image data or are not in analysis_only mode
            # abb our __init__ is overly complicated
            # if we did not load saved analysis (csv files) then always load olympus header
            # if not analysis_only:
            if 1:  # colin
                # logger.info("KymRoiAnalysis: trying to load Olympus header")
                olympusHeader = _loadLineScanHeader(path)
                if olympusHeader is not None:
                    logger.info("KymRoiAnalysis: loaded Olympus header")
                    pprint(olympusHeader)
                    self._kymRoiMetaData['Acq Date'] = olympusHeader['date']
                    self._kymRoiMetaData['Acq Time'] = olympusHeader['time']
                    self._kymRoiMetaData['secondsPerLine'] = olympusHeader['secondsPerLine']
                    self._kymRoiMetaData['umPerPixel'] = olympusHeader['umPerPixel']
                    # abb
                    self._kymRoiMetaData['imageWidth'] = olympusHeader['numLines']
                    self._kymRoiMetaData['imageHeight'] = olympusHeader['numPixels']
                    # abb hard coding number of channels (does Olympus export have this?)
                    self._kymRoiMetaData['numChannels'] = 1
                else:
                    logger.error("  KymRoiAnalysis: USING FAKE IMAGE SCALE !!")
                    self._fakeScale = True
                    _secondsPerLine = 0.002
                    _umPerPixel = 0.15
                    self._kymRoiMetaData['secondsPerLine'] = _secondsPerLine
                    self._kymRoiMetaData['umPerPixel'] = _umPerPixel
            else:
                if self._kymRoiMetaData['secondsPerLine'] is None:
                    self._kymRoiMetaData['secondsPerLine'] = 0.002
                if self._kymRoiMetaData['umPerPixel'] is None:
                    self._kymRoiMetaData['umPerPixel'] = 0.15
        # logger.info("KymRoiAnalysis: metadata post-analysis loaded")

        # logger.info("KymRoiAnalysis: building xAxis")
        _xAxisBins = np.arange(0, self.numLineScans)
        self._xAxisSeconds = np.array(_xAxisBins, dtype=np.float32)
        self._xAxisSeconds *= self.secondsPerLine

        self._fakeScale = False
        self._isDirty = False  # redundant

        if loadedHeaderDict is not None:
            self._kymRoiMetaData['Acq Date'] = loadedHeaderDict['Acq Date']
            self._kymRoiMetaData['Acq Time'] = loadedHeaderDict['Acq Time']
            self._kymRoiMetaData['secondsPerLine'] = loadedHeaderDict['secondsPerLine']
            self._kymRoiMetaData['umPerPixel'] = loadedHeaderDict['umPerPixel']
        else:
            if not self._analysis_only:

                olympusHeader = _loadLineScanHeader(self._path)
                if olympusHeader is not None:
                    self._kymRoiMetaData['Acq Date'] = olympusHeader['date']
                    self._kymRoiMetaData['Acq Time'] = olympusHeader['time']
                    self._kymRoiMetaData['secondsPerLine'] = olympusHeader['secondsPerLine']
                    self._kymRoiMetaData['umPerPixel'] = olympusHeader['umPerPixel']
                else:
                    self._fakeScale = True
                    _secondsPerLine = 0.002
                    _umPerPixel = 0.15
                    self._kymRoiMetaData['secondsPerLine'] = _secondsPerLine
                    self._kymRoiMetaData['umPerPixel'] = _umPerPixel
                    logger.error(
                        f'USING FAKE IMAGE SCALE !! secondsPerLine:{_secondsPerLine} umPerPixel:{_umPerPixel}'
                    )
            else:
                if self._kymRoiMetaData['secondsPerLine'] is None:
                    self._kymRoiMetaData['secondsPerLine'] = 0.002
                if self._kymRoiMetaData['umPerPixel'] is None:
                    self._kymRoiMetaData['umPerPixel'] = 0.15
        # logger.debug("KymRoiAnalysis: metadata post-analysis loaded")

        # Build x-axis
        _xAxisBins = np.arange(0, self.numLineScans)
        self._xAxisSeconds = np.array(_xAxisBins, dtype=np.float32)
        self._xAxisSeconds *= self.secondsPerLine
        # logger.debug("KymRoiAnalysis: building xAxis")
        # logger.debug("KymRoiAnalysis: setDirty(False)")
        self.setDirty(False)
        # logger.debug("KymRoiAnalysis: __init__ complete")

    def __str__(self):
        return \
            f'KymRoiAnalysis path={self._path}\n' \
            f'  roiLabels={self.getRoiLabels()}\n' \
            f'  numRoi={self.numRoi}\n' \
            f'  numChannels={self.numChannels}\n' \
            f'  numLineScans={self.numLineScans}\n' \
            f'  numPixelsPerLine={self.numPixelsPerLine}\n' \
            f'  secondsPerLine={self.secondsPerLine}\n' \
            f'  umPerPixel={self.umPerPixel}\n'

    def _ensure_img_data_loaded(self):
        """Ensure image data is loaded. Load it if needed and not in analysis_only mode."""
        if self._imgData is None and self._path is not None and not self._analysis_only:
            # Only load image data if not in analysis_only mode
    
            ba = bAnalysis(self._path)
            self._imgData = ba.fileLoader._tif
            if not isinstance(self._imgData, List):
                self._imgData = [self._imgData]
            
            # Update metadata with image dimensions
            if self._imgData and len(self._imgData) > 0:
                self._kymRoiMetaData['numChannels'] = len(self._imgData)
                self._kymRoiMetaData['imageHeight'] = self._imgData[0].shape[0]
                self._kymRoiMetaData['imageWidth'] = self._imgData[0].shape[1]
            elif self._imgData is None and self._analysis_only:
                pass

    def setKymDetectionParam(self, key, value):
        if key not in self._kymDetectionParams.keys():
            logger.error(f'key:{key} not in self._kymDetectionParams.keys()')
            return
        self._kymDetectionParams[key] = value

    def getKymDetectionParam(self, key):
        if key not in self._kymDetectionParams.keys():
            logger.error(f'key:{key} not in self._kymDetectionParams.keys()')
            return
        return self._kymDetectionParams[key]

    def getChannelColor(self, channel: int):
        colorConfig = {0: 'Red', 1: 'Green'}
        if self.numChannels == 1:
            # 1 channel will always be green
            return colorConfig[1]
        else:
            return colorConfig[channel]

    def peakDetectAllRoi(self, channel):
        logger.info('=== detecting peaks for all roi')
        for roiLabel, kymRoi in self._roiDict.items():
            logger.info(f'   -->> roiLabel:{roiLabel}')
            kymRoi.peakDetect(channel, peakDetectionType=PeakDetectionTypes.intensity)

    def setDirty(self, value):
        # logger.info(f'value:{value}')
        self._isDirty = value
        if self.dirty_callback_function is not None:
            self.dirty_callback_function(self._path, value)

    @property
    def path(self):
        return self._path

    def getImageChannel(self, channel):
        # Ensure image data is loaded if needed
        self._ensure_img_data_loaded()
        
        if self._imgData is None:
            raise RuntimeError(
                f"Image data not available for channel {channel}. "
                "This can happen in analysis_only mode when trying to access image data. "
                "Use load_image_data() to explicitly load image data if needed."
            )
        
        if channel > len(self._imgData) - 1:
            logger.error(
                f'bad image channel {channel}, max channel number is {len(self._imgData)-1}'
            )
            return
        return self._imgData[channel]

    @property
    def header(self) -> KymRoiMetaData:
        # return self._headerDict
        return self._kymRoiMetaData

    @property
    def umPerPixel(self) -> float:
        return self.header.getParam('umPerPixel')

    @property
    def numChannels(self) -> int:
        return self.header.getParam('numChannels')

    @property
    def secondsPerLine(self) -> float:
        return self.header.getParam('secondsPerLine')

    @property
    def numLineScans(self) -> float:
        return self.header.getParam('imageWidth')

    @property
    def numPixelsPerLine(self) -> float:
        """Number of pixels in each line scan."""
        return self.header.getParam('imageHeight')

    @property
    def numRoi(self) -> int:
        """Get the number of rois."""
        return len(self._roiDict.keys())

    def getRoiLabels(self) -> List[str]:
        return list(self._roiDict.keys())

    # abb 202505 colin
    def getCopyToClipboard(self) -> dict:
        """Get a json serializable dict of all roi"""
        roiLabels = self.getRoiLabels()
        ret = {}
        for label in roiLabels:
            roi = self.getRoi(label)
            oneRoiDict = roi.getRectDict()
            ret[label] = oneRoiDict
        return ret

    def _getNextRoiLabel(self) -> str:
        """Get the next available roi label.
        
        ROIs are str keys, user might think of them as 1,2,3,... which is not true !!!
        """
        newRoiNumber = self.numRoi
        newLabel = f'ROI {newRoiNumber + 1}'
        while newLabel in self._roiDict.keys():
            newRoiNumber += 1
            newLabel = f'ROI {newRoiNumber}'
        return newLabel

    def setRoiLabel(self, roiLabel: str, newRoiLabel: str) -> Optional[str]:
        """Set the label of a roi.
        
        Parameters
        ----------
        roiLabel : str
            The new label for the roi.

        Returns
        -------
        str
            The new label for the roi,
                otherwise None if roiLabel already exists
        """
        if newRoiLabel in self._roiDict.keys():
            logger.error(f'roiLabel "{roiLabel}" already exists')
            return
        # get currrent value from key
        _roi = self._roiDict[roiLabel]
        # pop the old key
        self._roiDict.pop(roiLabel)
        # add the new key
        self._roiDict[newRoiLabel] = _roi
        
        self.setDirty(True)

        return self._roiDict[newRoiLabel]
    
    def addROI(
        self,
        ltrbRect: List[int] = None,
        reuseRoiLabel: str = None,
        mode: str = None,
        skip_constraint: bool = False,
        roiLabel: str = None
    ) -> KymRoi:
        """Add a new roi.

        Parameters
        ----------
        ltrb : [l, t, r, b]
        reuseRoiLabel :
            Reuse detection params of existing roi.
        skip_constraint : bool
            If True, skip the constraint check (used when loading from analysis files)
        roiLabel : str
            The label for the new roi. If None, a new label is generated.

        Notes:
            sets dirty to True, we do not want this when loading from saved analysis files
        """

        if roiLabel is None:
            roiLabel = self._getNextRoiLabel()

        # logger.info(f'adding new roi label {roiLabel}')

        # Ensure image data is loaded if needed for ROI creation
        self._ensure_img_data_loaded()
        
        # Check if image data is available
        if self._imgData is None:
            raise RuntimeError(
                f"Cannot add ROI '{roiLabel}' - image data not available. "
                "This can happen in analysis_only mode when trying to add new ROIs. "
                "Use load_image_data() to explicitly load image data first."
            )

        newRoi = KymRoi(
            roiLabel,
            self._imgData,
            header=self.header,
            ltrbRect=ltrbRect,
            reuseRoiLabel=reuseRoiLabel,
            kymRoiAnalysis=self,  # so roi can use reuseRoiLabel
            skip_constraint=skip_constraint,
        )
        self._roiDict[roiLabel] = newRoi
        self.setDirty(True)
        return newRoi

    def deleteRoi(self, roiLabel: str) -> bool:
        # roi will be none if it is not a key
        # logger.info(f'pop roiLabel:{roiLabel} from self._roiDict keys:{self._roiDict.keys()}')
        # this is popping a str (user may think of roi as 1,2,3,... which it is not !!!
        roi = self._roiDict.pop(roiLabel, None)
        self.setDirty(True)
        return roi

    def getRoi(self, roiLabel: str) -> KymRoi:
        """Get a KymRoi from a label str."""
        if not isinstance(roiLabel, str):
            roiLabel = str(roiLabel)
        if roiLabel not in self._roiDict.keys():
            logger.error(
                f'roiLabel "{roiLabel}" does not exist, available roi keys are {list(self._roiDict.keys())}'
            )
            return
        return self._roiDict[roiLabel]

    def getXAxis(self):
        return self._xAxisSeconds

    def _msToBin(self, msValue: float) -> int:
        """Convert ms to nearest bin using round."""
        _retBin1 = msValue / 1000 / self.secondsPerLine
        _retBin2 = int(round(_retBin1))
        # logger.info(f'msValue:{msValue} _retBin1:{_retBin1} _retBin2:{_retBin2}')
        return _retBin2

    # TODO: refactor, only used by _getSaveFile
    def _getSaveFolder(self, enclosingFolder=False, createFolder=True):
        _folder, _ = os.path.split(self.path)  # folder the raw tif is in

        if not enclosingFolder:
            # folder we save csv into
            _folder = os.path.join(_folder, 'sanpy-kym-roi-analysis')
        if createFolder and not os.path.isdir(_folder):
            os.mkdir(_folder)

        return _folder

    def _getSaveFile(self, channel, createFolder=True):
        """Get full path to file to save/load analysis.

        Returns
        -------
        peaks
        diameter
        traces
        """
        saveFolder = self._getSaveFolder(createFolder=createFolder)

        _, _file = os.path.split(self.path)  # folder the raw tif is in

        _saveFile = os.path.splitext(_file)[0]

        saveFilePeaks = _saveFile + f'-ch{channel}-roiPeaks.csv'  # peaks
        saveFilePeaks = os.path.join(saveFolder, saveFilePeaks)

        saveFileDiameter = _saveFile + f'-ch{channel}-roiDiameter.csv'  # diameter
        saveFileDiameter = os.path.join(saveFolder, saveFileDiameter)

        saveFileInt = _saveFile + f'-ch{channel}-roiTraces.csv'  # intensity
        saveFileIntPath = os.path.join(saveFolder, saveFileInt)

        return saveFilePeaks, saveFileDiameter, saveFileIntPath

    def getDataFrame(
        self, channel,
        peakDetectionType: PeakDetectionTypes,
        roiLabel=None
    ):
        """Get results df for one roi or all roi (use roiLabel=None).

        Only results for one type of PeakDetectionTypes
        """
        if roiLabel is not None:
            return self.getRoi(roiLabel).getAnalysisResults(channel, peakDetectionType)
        else:
            columns = list(KymRoiResults.analysisDict.keys())
            df = pd.DataFrame(columns=columns)  # empty df with proper columns
            for _roiIdx, roi in enumerate(self._roiDict.values()):
                # logger.info(f'oneDf:{oneDf}')
                oneDf = roi.getAnalysisResults(channel, peakDetectionType).df
                if _roiIdx == 0:
                    df = oneDf
                else:
                    # abb 20250621
                    # fixes
                    # FutureWarning: The behavior of DataFrame concatenation with empty or all-NA entries is deprecated
                    if len(oneDf) > 0:
                        df = pd.concat([df, oneDf], axis=0)
            try:
                df = df.reset_index(drop=True)
            except ValueError as e:
                logger.error(e)

            # logger.info('returning df:')
            # print(df)

            return df

    def getCombindedDataFrame(self, channel):
        """Get combined DataFrame of analysis including both f_f0 and diameter."""
        dfSum = self.getDataFrame(channel, PeakDetectionTypes.intensity)
        dfSum['Analysis Type'] = 'f/f0'

        dfDiameter = self.getDataFrame(channel, PeakDetectionTypes.diameter)
        dfDiameter['Analysis Type'] = 'Diameter (um)'

        df = pd.concat([dfSum, dfDiameter], axis=0)
        df = df.reset_index(drop=True)
        return df

    def isDirty(self):
        """isDirty is true if we are dirty or any of the rois are dirty."""
        if self._isDirty:
            logger.info('  kymRoiAnalysis is dirty')
            return True
        for roiLabel, kymRoi in self._roiDict.items():
            if kymRoi._isDirty:
                logger.info(f'  roiLabel: {roiLabel} is dirty')
                return True
        return False

    def mySetStatusBar(self, statusStr: str):
        """Set the status bar of a parent kymRoiWidget.

        Only exists during PyQt runtime (not in scripts).
        """
        if self._kymRoiWidget is not None:
            self._kymRoiWidget.mySetStatusbar(statusStr)

    def saveAnalysisTraces(self, channel):
        """Save all roi traces for a channel in one csv file."""
        _, _, tracePath = self._getSaveFile(channel)

        df = pd.DataFrame()

        for roiLabel, kymRoi in self._roiDict.items():

            kymRoi: KymRoi = kymRoi

            kymRoiTraces = kymRoi.kymRoiTraces[channel]
            # if kymRoiTraces.isEmpty():
            #     continue
            for traceKey, traceValues in kymRoiTraces.items():
                # don't save if all nan
                if np.all(np.isnan(traceValues)):
                    # logger.warning(f'  not saving trace:{traceKey} -->> all nan')
                    continue

                colName = f'ROI {roiLabel} {traceKey}'
                # df[colName] = [np.nan] * numLineScans
                # logger.info(f'   roiLabel:{roiLabel} traceKey:{traceKey} colName:{colName} len:{len(traceValues)}')
                df[colName] = traceValues  # might be nan

        # logger.warning('todo: save a one line header with um/pixel and seconds/line')
        _fileHeaderJson = self._kymRoiMetaData.toJson()

        # logger.warning('saving traces even if 0 peaks')
        # if len(df) == 0:
        #     # nothing to save
        #     pass
        # else:
        if 1:
            # logger.info(f'saving intensity traces to: {tracePath}')
            # df.to_csv(intPath, index=False)
            with open(tracePath, 'w') as f:
                f.write(_fileHeaderJson)
                f.write('\n')
                f.write(df.to_csv(header=True, index=False, mode='a'))

    def saveImageClips(self):
        """Save image clips for each roi.

        Each ROI will have 4x files (* color channel)
            - raw
            - background subtracted
            - binned
            - divided
        """
        # cell id from tif file
        _folder, _name = os.path.split(self.path)
        cellID = os.path.splitext(_name)[0]

        # WARNING: we need to ignore folder 'roi-img-clips' when building tif list !!!
        tifFolder = os.path.join(self._getSaveFolder(), 'kym-roi-img-clips')
        # logger.info(f'saving to tifFolder:{tifFolder}')

        for channel in range(self.numChannels):
            for roiLabel, kymRoi in self._roiDict.items():
                kymRoi: KymRoi = kymRoi
                # roiImg_raw, roiImg_bs, roiImg_binned, roiImg_divided = \

                # get a number of image clips (raw, f/f0 df/f0, divided)
                roiImgClipsDict = kymRoi.getRoiImgClips(channel)

                for clipKey, clipImgData in roiImgClipsDict.items():
                    if not os.path.isdir(tifFolder):
                        os.makedirs(tifFolder)
                    tifFileName = f'{cellID}-ch{channel}-roi{roiLabel}-{clipKey}.tif'
                    savePath = os.path.join(tifFolder, tifFileName)
                    # logger.info(f'  roiLabel:{roiLabel} clipKey:{clipKey}')
                    # logger.info(f'    tifFileName:{tifFileName}')
                    # logger.info(f'  savePath:{savePath}')
                    tifffile.imwrite(savePath, clipImgData)

    def saveAnalysis(self):
        """Save all analysis into a number of csv files.

        This includes a header with roi [l,t,r,b] and detection parameters used.

        Each ROI will have 3x files (* color channel)
            - intensity peaks
            - diameter peaks
            - traces (raw data that was analyzed, for both f/f0 peaks and diameter peaks)
        """

        # logger.info('')
        if not self.isDirty:
            _noSaveStr = 'No changes to save.'
            logger.info(_noSaveStr)
            self.mySetStatusBar(_noSaveStr)
            return False

        # self.saveImageClips()

        for channel in range(self.numChannels):

            # each channel goes to its own file
            _fileHeaderDict = {}
            _fileHeaderDictDiameter = {}

            # 202505 colin
            # logger.info(f'saving key "_kymDetectionParams":{self._kymDetectionParams}')
            _fileHeaderDict['kymDetectionParams'] = self._kymDetectionParams

            for roiLabel, kymRoi in self._roiDict.items():
                # what was used for detection, including [l,t,r,b] of rect roi

                # just key value pairs for detection parameters
                _fileHeaderDict[roiLabel] = kymRoi.getDetectionParams(
                    channel, PeakDetectionTypes.intensity
                ).getValueDict()
                _fileHeaderDictDiameter[roiLabel] = kymRoi.getDetectionParams(
                    channel, PeakDetectionTypes.diameter
                ).getValueDict()

            # one line json header with all roi and their detection params
            _fileHeaderJson = json.dumps(_fileHeaderDict)
            _fileHeaderJson_diameter = json.dumps(_fileHeaderDictDiameter)

            peakPath, diameterPath, _ = self._getSaveFile(channel)

            # _savedPeaks = False

            dfToSaveIntensity = self.getDataFrame(channel, PeakDetectionTypes.intensity)

            # if len(dfToSaveIntensity) == 0:
            #     pass
            #     # no intensity peaks to save
            # else:
            if 1:
                # logger.info(f'saving f/f0 peaks to: {peakPath}')
                # _savedPeaks = True
                with open(peakPath, 'w') as f:
                    f.write(_fileHeaderJson)
                    f.write('\n')
                    f.write(
                        dfToSaveIntensity.to_csv(header=True, index=False, mode='a')
                    )

            dfToSaveDiameter = self.getDataFrame(channel, PeakDetectionTypes.diameter)

            if len(dfToSaveDiameter) == 0:
                # no diameter peaks to save
                pass
            else:
                # logger.info(f'saving diameter to: {diameterPath}')
                # _savedPeaks = True
                with open(diameterPath, 'w') as f:
                    f.write(_fileHeaderJson_diameter)
                    f.write('\n')
                    f.write(dfToSaveDiameter.to_csv(header=True, index=False, mode='a'))

            # only save analysis traces if we save (intensity or diameter) peaks
            # 202505 always save, even of no peaks
            # if _savedPeaks:
            if 1:
                self.saveAnalysisTraces(channel)

        self.setDirty(False)
        for roiLabel, roi in self._roiDict.items():
            roi.setDirty(False)

        return True

    def _loadThisFile(
        self,
        filePath,
        channel,
        peakDetectionType: PeakDetectionTypes,
        addRois
    ):
        """Load peak detection file from either intensity or diameter.
        
        Parameters
        ==========
        addRois : bool
            If true then add rois
        """
        # logger.debug(f"_loadThisFile: filePath={filePath}, channel={channel}, peakDetectionType={peakDetectionType}")
        
        if not os.path.isfile(filePath):
            # logger.debug(f"_loadThisFile: file does not exist: {filePath}")
            return False

        with open(filePath) as f:
            headerJson = f.readline()
            _headerDict = json.loads(headerJson)

        # _headerDict has str keys for 'ROI Label', values() are dict with detection params
        # logger.info('_headerDict:')
        # from pprint import pprint
        # pprint(_headerDict)

        dfLoadedFromFile = pd.read_csv(filePath, header=1)  # can be empty

        # dfLoadedFromFile has old column 'ROI Number'
        # abb 20250718 switch 'ROI Number' -> 'ROI Label'
        if 'ROI Number' in dfLoadedFromFile.columns:
            logger.warning("converting 'ROI Number' to 'ROI Label")
            dfLoadedFromFile.rename(columns={'ROI Number': 'ROI Label'}, inplace=True)
            # old ROI Number is type int, new ROI Label is type str
            dfLoadedFromFile['ROI Label'] = dfLoadedFromFile['ROI Label'].astype(str)

        # logger.info('dfLoadedFromFile:')
        # print(dfLoadedFromFile)

        # _headerDict is a dict with roi name keys, make a number of rois
        # self._detectionDict = _headerDict
        _firstRoi = None
        for roiLabel, detectionDict in _headerDict.items():
            # roiNumber is str like '1', '2', '3',...
            # logger.debug(f"_loadThisFile: processing ROI {roiNumber}")

            if roiLabel == 'kymDetectionParams':
                # abb 202505 colin, global detection params for kym
                # logger.debug(f"_loadThisFile: loading kymDetectionParams")
                self._kymDetectionParams = detectionDict
                continue

            kymRoiDetection = KymRoiDetection(peakDetectionType, fromDict=detectionDict)

            # add the roi
            if addRois:
                # In analysis_only mode, we need to create ROIs without requiring image data
                if self._analysis_only:
                    # Create ROI with None as imgData to avoid loading image data
                    kymRoi = KymRoi(
                        roiLabel,
                        imgData=None,  # No image data in analysis_only mode
                        header=self._kymRoiMetaData,  # Pass the KymRoiMetaData object, not the dict
                        ltrbRect=kymRoiDetection['ltrb'],
                        kymRoiAnalysis=self,
                        skip_constraint=True  # Skip constraint check when loading from analysis
                    )
                    self._roiDict[roiLabel] = kymRoi
                else:
                    kymRoi = self.addROI(kymRoiDetection['ltrb'],
                                         skip_constraint=True,
                                         roiLabel=roiLabel)  # add to all channels, skip constraint when loading from analysis
            else:
                kymRoi = self.getRoi(roiLabel)

            # set detection
            kymRoi.setDetection(channel, PeakDetectionTypes.intensity, kymRoiDetection)

            # fill in analysis results
            oneRoiResults = KymRoiResults()

            # abb 20250718 switch 'ROI Number' -> 'ROI Label'
            # if 'ROI Number' in dfLoadedFromFile:
            #     # rename 'ROI Number' -> 'ROI Label'
            #     dfLoadedFromFile.rename(columns={'ROI Number': 'ROI Label'}, inplace=True)
            
            dfRoi = dfLoadedFromFile[dfLoadedFromFile['ROI Label'] == roiLabel]

            dfRoi = dfRoi.reset_index(
                drop=True
            )  # Do not try to insert index into dataframe columns.
            oneRoiResults._swapInNewDf(dfRoi)
            # kymRoi._kymRoiResults = oneRoiResults
            kymRoi.setResults(channel, PeakDetectionTypes.intensity, oneRoiResults)

        # logger.info('on load, always setting dirty -> False')
        self.setDirty(False)

        return True

    def loadAnalysis(self):
        """Load analysis results from saved files."""
        # logger.debug("loadAnalysis: start")
        _maxChannels = 3
        _loadedHeaderDict = None
        addRois = True
        for channel in range(_maxChannels):
            # logger.debug(f"loadAnalysis: channel={channel}")
            # gets paths to each type of analysis (peak, diameter, and trace)
            peakPath, diameterPath, tracePath = self._getSaveFile(
                channel, createFolder=False
            )
            # logger.debug(f"loadAnalysis: got save files: peakPath={peakPath}, diameterPath={diameterPath}, tracePath={tracePath}")
            
            # Try to load header (metadata) from trace file first
            header_loaded = False
            if os.path.isfile(tracePath):
                logger.info(f"loadAnalysis: opening tracePath: {tracePath}")
                with open(tracePath) as f:
                    headerJson = f.readline()
                    _loadedHeaderDict = json.loads(headerJson)
                    # set the path to the actual path during runtime
                    _loadedHeaderDict['path'] = self.path
                    self._kymRoiMetaData = KymRoiMetaData.fromDict(_loadedHeaderDict)
                header_loaded = True
            
            # If trace file doesn't exist or failed to load header, try to load from peak file
            # if not header_loaded and os.path.isfile(peakPath):
            #     try:
            #         logger.debug(f"loadAnalysis: loading header from peak file: {peakPath}")
            #         with open(peakPath) as f:
            #             headerJson = f.readline()
            #             _loadedHeaderDict = json.loads(headerJson)
            #             if '_loadedHeaderDict' not in _loadedHeaderDict.keys() or _loadedHeaderDict['version'] < self._kymRoiMetaData.getParam('version'):
            #                 logger.error(f'Version mismatch in saved state file: {peakPath}')
            #                 logger.error(F'  -->> ignore loaded header')
            #             else:
            #                 _loadedHeaderDict['path'] = self.path  # runtime path (in case user moved folder)
            #             self._kymRoiMetaData = KymRoiMetaData.fromDict(_loadedHeaderDict)
            #         header_loaded = True
            #     except Exception as e:
            #         logger.debug(f"loadAnalysis: failed to load header from peak file: {e}")
            
            # If we still don't have header, skip this channel
            if not header_loaded:
                # there was no saved csv file for channel

                continue


            loaded_f_f0 = self._loadThisFile(peakPath, channel, PeakDetectionTypes.intensity, addRois=addRois)
            if loaded_f_f0:
                addRois = False
            # logger.debug("loadAnalysis: loading diameter file")
            loaded_diameter = self._loadThisFile(diameterPath, channel, PeakDetectionTypes.diameter, addRois=addRois)
            if loaded_diameter:
                addRois = False

            # Try to load trace data if trace file exists
            if os.path.isfile(tracePath):
                try:
                    # logger.debug("loadAnalysis: loading trace data")
                    loadedIntDf = pd.read_csv(tracePath, header=1)

                    for _roiLabel in self.getRoiLabels():
                        try:
                            # logger.debug(f"loadAnalysis: loading traces for ROI {_roiLabel}")
                            kymRoi = self.getRoi(_roiLabel)
                            kymRoi.kymRoiTraces[channel].loadTraces(_roiLabel, loadedIntDf)
                        except pd.errors.EmptyDataError:
                            pass
                except Exception as e:
                    pass

          # logger.debug("loadAnalysis: end")

        # when we load, we and our rois are never dirty
        self.setDirty(False)
        for roi in self._roiDict.values():
            roi.setDirty(False)

        return _loadedHeaderDict

    def getParamDataFrame(self) -> pd.DataFrame:
        """Get a dataframe of all detection params.

        One row per roi.
        """
        dictList = []
        for roiLabel, roi in self._roiDict.items():
            dictList.append(roi.detectionParams.getValueDict())
        df = pd.DataFrame.from_dict(dictList)
        return df

    def getAnalysisTrace(self, roi: str, name: str, channel: int) -> np.ndarray:
        kymRoi = self.getRoi(roi)
        return kymRoi.getTrace(channel, name)

    def getDetectionParams(
        self, roiLabel: str, detectionType: PeakDetectionTypes, channel: int
    ) -> KymRoiDetection:
        kymRoi = self.getRoi(roiLabel)
        return kymRoi.getDetectionParams(channel, detectionType)

    def getAnalysisPeakResults(self, roiLabel: str, channel: int) -> KymRoiResults:
        kymRoi = self.getRoi(roiLabel)
        return kymRoi.getAnalysisResults(channel, PeakDetectionTypes.intensity)

    def getAnalysisResults(
        self,
        roiLabel: str,
        detectionType: PeakDetectionTypes,
        channel: int) -> KymRoiResults:
        
        kymRoi = self.getRoi(roiLabel)
        if kymRoi is None:
            logger.error(f'did not find roi label "{roiLabel}"')
            return
        return kymRoi.getAnalysisResults(channel, detectionType)

    def detectDiam(self, roi: str, channel: int):
        kymRoi = self.getRoi(roi)
        kymRoi.detectDiam(channel=channel)

    def __iter__(self):
        self._currentIter = -1
        return self

    def __next__(self):  # Python 2: def next(self)
        self._currentIter += 1
        if self._currentIter < self.numRoi:
            _keyList = list(self._roiDict.keys())
            _key = _keyList[self._currentIter]
            return self.getRoi(_key)
        raise StopIteration

    def load_image_data(self):
        """Explicitly load image data even in analysis_only mode.
        
        This method allows lazy loading of image data when needed,
        even when the object was created in analysis_only mode.
        """
        if self._imgData is None and self._path is not None:
            logger.info(f"Explicitly loading image data for: {self._path}")
            ba = bAnalysis(self._path)
            self._imgData = ba.fileLoader._tif
            if not isinstance(self._imgData, List):
                self._imgData = [self._imgData]
            
            # Update metadata with image dimensions
            if self._imgData and len(self._imgData) > 0:
                self._kymRoiMetaData['numChannels'] = len(self._imgData)
                self._kymRoiMetaData['imageHeight'] = self._imgData[0].shape[0]
                self._kymRoiMetaData['imageWidth'] = self._imgData[0].shape[1]


# utils
def _printImgStat(imgData: np.ndarray, name: str = ''):

    if name != '':
        name += ':'
    numZeros = np.count_nonzero(imgData == 0)
    logger.info(
        f'{name} {imgData.shape} mean:{np.mean(imgData)} median:{np.median(imgData)} min:{np.min(imgData)} max:{np.max(imgData)} num zero:{numZeros} {imgData.dtype}'
    )


# def plotDetectionResults(kymRoi : KymRoi, channel):
def plotDetectionResults(kymRoiAnalysis: KymRoiAnalysis, roiLabelStr, channel):
    """Plot analysis steps using MatPlotLib.
        - Raw sum
        - Detrended sum
        - df/d0

    Parameters
    ----------
    kymRoi : KymROi
        Results for one ROI
    """
    _channelColor = kymRoiAnalysis.getChannelColor(channel=channel)

    kymRoi = kymRoiAnalysis.getRoi(roiLabelStr)

    imgData = kymRoi.getRoiImg(channel=channel)

    timeSec = kymRoi.getTrace(channel, 'Time (s)')  # seconds
    intRaw = kymRoi.getTrace(channel, 'intRaw')
    intDetrend = kymRoi.getTrace(channel, 'intDetrend')
    logger.warning('defaulting to santana f/f0')
    int_df_f0 = kymRoi.getTrace(channel, 'f/f0')  # yDf_f0

    detectionParams = kymRoi.getDetectionParams(channel, PeakDetectionTypes.intensity)
    analysisResults = kymRoi.getAnalysisResults(channel, PeakDetectionTypes.intensity)

    peakSecond = analysisResults.getValues('Peak (s)')
    peakValue = analysisResults.getValues('Peak Int')

    #
    fig, axs = plt.subplots(4, 1, figsize=(8, 10), sharex=True)

    roiLabel = kymRoi.getLabel()
    _backgroundsubtract = (
        f"Background subtract: {detectionParams['Background Subtract']}"
    )
    _title = f'{os.path.split(kymRoi.path)[1]}, ROI {roiLabel}, {_backgroundsubtract}'
    fig.suptitle(_title)

    # image
    left, top, right, bottom = kymRoi.getRect()
    # logger.info(f'timeSec:{timeSec} {type(timeSec)}')
    # abb removed 20250508
    # try:
    #     leftSec = timeSec.values[0]
    #     rightSec = timeSec.values[-1]
    # except (AttributeError) as e:
    #     logger.error(f'sometimes timeSec is pandas, sometimes numpy ???: {e}')
    #     logger.error(f'  timeSec is type:{type(timeSec)}')
    #     logger.error(f'  timeSec:{timeSec}')
    #     logger.error(f'  roi left:{left}')
    #     leftSec = timeSec[0]
    #     rightSec = timeSec[-1]

    logger.warning('should be using left of roi (pixels)')
    leftSec = timeSec[0]
    rightSec = timeSec[-1]

    _extent = [leftSec, rightSec, bottom, top]

    detectThisTrace = detectionParams['detectThisTrace']
    f0 = detectionParams['f0 Value Percentile']
    if detectThisTrace == 'f/f0':
        imgData = imgData / f0
        imgData = imgData.astype(np.int16)
    elif detectThisTrace == 'df/f0':
        imgData = (imgData - f0) / f0
        imgData = imgData.astype(np.int16)
    else:
        logger.error(f'detectThisTrace:{detectThisTrace} not supported')
        return

    from sanpy.kym.kymUtils import getAutoContrast

    _min, _max = getAutoContrast(imgData)  # new 20240925, should mimic ImageJ

    # imgplot = axs[0].imshow(imgData, extent=_extent, aspect="auto")

    axs[0].imshow(
        imgData,
        cmap="Greens",
        origin='lower',
        aspect='auto',
        extent=_extent,
        vmin=_min,
        vmax=_max,
    )

    # I do not like how 'Greens' look ...
    # imgplot.set_cmap('nipy_spectral')
    # if _channelColor == 'Green':
    #     imgPlotColor = 'Greens'
    # else:
    #     imgPlotColor = 'Reds'
    # imgplot.set_cmap(imgPlotColor)
    # axs[0].legend(loc='upper right')  # legend does not work with imshow()

    # raw sum with fit
    axs[1].plot(
        timeSec,
        intRaw,
        _channelColor,
        label=f"Sum (bins={detectionParams['Bin Line Scans']})",
    )
    axs[1].set_ylabel('Intensity (per pixel)')
    # add exp fit
    fitDict = detectionParams['expDetrendFit']
    if fitDict is None:
        logger.info('expDetrend is off -->> no fit')
        # axs[0].legend('No Exp Detrend')
    else:
        _m = fitDict['m']
        _t = fitDict['tau']
        _b = fitDict['b']
        yFit = myMonoExp(timeSec, _m, _t, _b)
        _m = round(_m, 1)
        _t = round(_t, 1)
        _b = round(_b, 1)
        # ret = m * np.exp(-t * x) + b
        # _label = f'y = {_m} * exp(-{_t} * x) + {_b}'
        _label = 'Exp Fit'
        axs[1].plot(timeSec, yFit, 'c', label=_label)
        axs[1].legend()

    # after remove fit (if on) and selecting f0
    # axs[2].plot(timeSec, intDetrend, 'r', label='Detrend')
    axs[2].plot(timeSec, intDetrend, _channelColor)
    axs[2].set_ylabel('Subtract exp')
    # add f0
    f0_type = detectionParams['f0 Type']
    if f0_type == 'Percentile':
        _f0 = detectionParams['f0 Value Percentile']
    elif f0_type == 'Manual':
        _f0 = detectionParams['f0 Value Manual']
    else:
        logger.error(f'did not understand f0_type:{f0_type}')
        _f0 = 1
    _label = f"f0 {f0_type} = {round(_f0,2)}"
    axs[2].axhline(y=_f0, label=_label, color='c')
    axs[2].legend()

    # final dF/F0, with peaks (and fit)
    logger.warning('TODO: dynamically switch betwee df/d0 and santana f/f0')
    axs[3].plot(timeSec, int_df_f0, _channelColor, label='f/f0')
    axs[3].set_ylabel('f/f0')
    axs[3].plot(peakSecond, peakValue, 'go')
    axs[2].legend()

    # rise
    # axs[2].plot(peak10_left_ips, yDf_f0[peak10_left_ips.astype(int)], 'ro')
    # axs[2].plot(peak90_left_ips, yDf_f0[peak90_left_ips.astype(int)], 'r^')

    # decay
    # axs[2].plot(peak10_right_ips, yDf_f0[peak10_right_ips.astype(int)], 'co')
    # axs[2].plot(peak90_right_ips, yDf_f0[peak90_right_ips.astype(int)], 'c^')

    #
    # (1) exp decay

    # fix this constant bug !!!!
    [_left, _, _, _] = kymRoi.getRect()
    _peakBins = analysisResults.getValues('Peak Bin')

    xDecay = []
    yDecay = []
    for _peakIdx, _peakBin in enumerate(_peakBins):

        _peakBin = _peakBin - _left

        fit_m = analysisResults.getValues('fit_m')[_peakIdx]
        fit_tau = analysisResults.getValues('fit_tau')[_peakIdx]
        fit_b = analysisResults.getValues('fit_b')[_peakIdx]

        if np.isnan(fit_m):
            # logger.warning(f'no fit for peak {_peakIdx}')
            continue

        # ms to bin
        _decayMs = detectionParams['Decay (ms)']
        _decayBin = _decayMs / 1000 / kymRoi._header['secondsPerLine']
        _decayBin = int(round(_decayBin))

        # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine
        decayFitBins = _decayBin
        _xRange = timeSec[_peakBin : _peakBin + decayFitBins] - timeSec[_peakBin]

        # get line showing our fit
        fit_y = myMonoExp(_xRange, fit_m, fit_tau, fit_b)

        xDecay.extend(_xRange + timeSec[_peakBin])
        xDecay.append(np.nan)

        yDecay.extend(fit_y)
        yDecay.append(np.nan)
    #
    axs[3].plot(xDecay, yDecay, 'c')  # single exp fit to decay

    #
    # (2) double exp decay
    xDecay2 = []
    yDecay2 = []
    for _peakIdx, _peakBin in enumerate(_peakBins):

        # fix this constant bug !!!!
        _peakBin = _peakBin - _left

        fit_m1 = analysisResults.getValues('fit_m1')[_peakIdx]
        fit_tau1 = analysisResults.getValues('fit_tau1')[_peakIdx]
        fit_m2 = analysisResults.getValues('fit_m2')[_peakIdx]
        fit_tau2 = analysisResults.getValues('fit_tau2')[_peakIdx]

        if np.isnan(fit_m1):
            # logger.warning(f'no dbl exp fit for peak {_peakIdx}')
            continue

        # ms to bin
        _decayMs = detectionParams['Decay (ms)']
        decayFitBins = _decayMs / 1000 / kymRoi._header['secondsPerLine']
        decayFitBins = int(round(decayFitBins))

        _xRange = timeSec[_peakBin : _peakBin + decayFitBins] - timeSec[_peakBin]

        # get line showing our fit
        fit_y = myDoubleExp(_xRange, fit_m1, fit_tau1, fit_m2, fit_tau2)

        xDecay2.extend(_xRange + timeSec[_peakBin])
        xDecay2.append(np.nan)

        yDecay2.extend(fit_y)
        yDecay2.append(np.nan)
    #
    axs[3].plot(xDecay2, yDecay2, 'b')  # double exp fit to decay

    return fig, axs


if __name__ == '__main__':
    pass
