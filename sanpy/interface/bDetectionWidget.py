import os
import sys
import math
import time

# import inspect # to print call stack
from functools import partial
from typing import Union, Dict, List, Tuple, Optional

import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter

import sanpy
import sanpy.bDetection
import sanpy.interface

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class bDetectionWidget(QtWidgets.QWidget):
    signalSelectSpike = QtCore.pyqtSignal(object)  # spike number, doZoom
    signalSelectSpikeList = QtCore.pyqtSignal(object)  # spike number, doZoom
    signalDetect = QtCore.pyqtSignal(object)  # ba
    signalSelectSweep = QtCore.pyqtSignal(object, object)  # (bAnalysis, sweepNumber)
    # signalUpdateKymographROI = QtCore.pyqtSignal([])  # list of [left, top, right, bottom] in image pixels

    def __init__(
        self,
        ba: sanpy.bAnalysis = None,
        mainWindow: "sanpy.interface.SanPyWindow" = None,
        parent=None,
    ):
        """
        ba : sanpy.bAnalysis
            bAnalysis object
        mainWindow : sanpy.interface.SanPyWindow
        """

        super(bDetectionWidget, self).__init__(parent)

        self.ba : sanpy.bAnalysis = ba
        self.myMainWindow: "sanpy.interface.SanPyWindow" = mainWindow

        self._pgPointSize = 10  # use +/- to increase decrease

        self._blockSlots: bool = False

        self._selectedSpikeList: List[int] = None

        self.dvdtLines = None
        self.dvdtLinesFiltered = None
        self.dacLines = None
        self.vmLines = None
        # self.vmLinesFiltered = None
        # self.vmLinesFiltered2 = None
        self.linearRegionItem2 = None  # rectangle over global Vm
        # self.clipLines = None
        # self.meanClipLine = None

        self._showCrosshair = False

        self.myPlotList = []

        # a list of possible x/y plots (overlay over dvdt and Vm)
        # order here determines order in interface
        self.myPlots = [
            {
                "humanName": "Global Threshold (mV)",
                "x": "thresholdSec",
                "y": "thresholdVal",
                "convertx_tosec": False,  # some stats are in points, we need to convert to seconds
                "color": "r",
                "styleColor": "color: red",
                "symbol": "o",
                "plotOn": "vmGlobal",  # which plot to overlay (vm, dvdt)
                "plotIsOn": True,
            },

            {
                "humanName": "Threshold (dV/dt)",
                "x": "thresholdSec",
                "y": "thresholdVal_dvdt",
                "convertx_tosec": False,  # some stats are in points, we need to convert to seconds
                "color": "r",
                "styleColor": "color: red",
                "symbol": "o",
                "plotOn": "dvdt",  # which plot to overlay (vm, dvdt)
                "plotIsOn": True,
            },

            {
                "humanName": "Threshold (mV)",
                "x": "thresholdSec",
                "y": "thresholdVal",
                "convertx_tosec": False,  # some stats are in points, we need to convert to seconds
                "color": "r",
                "styleColor": "color: red",
                "symbol": "o",
                "plotOn": "vm",  # which plot to overlay (vm, dvdt)
                "plotIsOn": True,
            },

            {
                "humanName": "AP Peak (mV)",
                "x": "peakSec",
                "y": "peakVal",
                "convertx_tosec": False,
                "color": "g",
                "styleColor": "color: green",
                "symbol": "o",
                "plotOn": "vm",
                "plotIsOn": True,
            },
            {
                "humanName": "Half-Widths",
                "x": None,
                "y": None,
                "convertx_tosec": True,
                "color": "y",
                "styleColor": "color: yellow",
                "symbol": "o",
                "plotOn": "vm",
                "plotIsOn": False,
            },
            {
                "humanName": "Epoch Lines",
                "x": None,
                "y": None,
                "convertx_tosec": True,
                "color": "gray",
                "styleColor": "color: gray",
                "symbol": "o",
                "plotOn": "vm",
                "plotIsOn": True,
            },
            # removed april 15, 2023
            # {
            #     "humanName": "Pre AP Min (mV)",
            #     "x": "preMinPnt",
            #     "y": "preMinVal",
            #     "convertx_tosec": True,
            #     "color": "y",
            #     "styleColor": "color: green",
            #     "symbol": "o",
            #     "plotOn": "vm",
            #     "plotIsOn": False,
            # },
            
            # {
            #    'humanName': 'Post AP Min (mV)',
            #    'x': 'postMinPnt',
            #    'y': 'postMinVal',
            #    'convertx_tosec': True,
            #    'color': 'b',
            #    'styleColor': 'color: blue',
            #    'symbol': 'o',
            #    'plotOn': 'vm',
            #    'plotIsOn': False,
            # },

            # removed april 15, 2023
            # {
            #     "humanName": "EDD",
            #     "x": None,
            #     "y": None,
            #     "convertx_tosec": True,
            #     "color": "m",
            #     "styleColor": "color: megenta",
            #     "symbol": "o",
            #     "plotOn": "vm",
            #     "plotIsOn": False,
            # },

            # removed april 15, 2023
            # {
            #     "humanName": "EDD Rate",
            #     "x": None,
            #     "y": None,
            #     "convertx_tosec": False,
            #     "color": "m",
            #     "styleColor": "color: megenta",
            #     "symbol": "--",
            #     "plotOn": "vm",
            #     "plotIsOn": False,
            # },

        ]
        
        # for kymograph
        # self.myImageItem = None  # kymographImage
        # self.myLineRoi = None

        self._buildUI()

        windowOptions = self.getMainWindowOptions()
        showDvDt = True
        # showClips = False
        # showScatter = True
        if windowOptions is not None:
            showDerivative = windowOptions["rawDataPanels"]["Derivative"]
            showDAC = windowOptions["rawDataPanels"]["DAC"]
            showFullRecording = windowOptions["rawDataPanels"]["Full Recording"]

            self.toggleInterface("Full Recording", showFullRecording)
            self.toggleInterface("Derivative", showDerivative)
            self.toggleInterface("DAC", showDAC)
            # self.toggleInterface('Clips', showClips)

            #
            # toggle interface to myDetectionToolbarWidget
            showPlotOption = windowOptions["detectionPanels"]["Detection"]
            self.toggleInterface("Detection", showPlotOption)

            showPlotOption = windowOptions["detectionPanels"]["Display"]
            self.toggleInterface("Display", showPlotOption)

            showPlotOption = windowOptions["detectionPanels"]["Plot Options"]
            self.toggleInterface("Plot Options", showPlotOption)

            showPlotOption = windowOptions["detectionPanels"]["Set Spikes"]
            self.toggleInterface("Set Spikes", showPlotOption)

            showPlotOption = windowOptions["detectionPanels"]["Set Meta Data"]
            self.toggleInterface("Set Meta Data", showPlotOption)

    def slot_contextMenu(self, plotName : str, plot, pos):
        """Some plot widgets (vmPlot, derivPlot) have their context menu set to here.
        
        This is necc. as we need to know which plot it is coming from (as compared to the entire detectionWidget.
        """
        # logger.info(f'{plotName}')
        pos = plot.mapToGlobal(pos)
        self._myContextMenuEvent(plotName, pos)

    # july 2023, moved from multi line
    def _myContextMenuEvent(self, plotName, pos):
        """Show popup context menu in response to right(command)+click.
        
        This is inherited from QWidget.
        """

        contextMenu = QtWidgets.QMenu()

        showCrosshairAction = contextMenu.addAction(f"Crosshair")
        showCrosshairAction.setCheckable(True)
        showCrosshairAction.setChecked(self._showCrosshair)
        
        inVmPlot = plotName == 'vmPlot'  #self.vmPlot.sceneBoundingRect().contains(event.pos())
        inDerivPlot = plotName == 'derivPlot'  #self.derivPlot.sceneBoundingRect().contains(event.pos())

        if inVmPlot:
            _cursorAction = self._sanpyCursors.getMenuActions(contextMenu)
        if inDerivPlot:
            _cursorAction2 = self._sanpyCursors_dvdt.getMenuActions(contextMenu)
        
        contextMenu.addSeparator()

        # exportTraceAction = contextMenu.addAction(f"Export Trace {myType}")
        # contextMenu.addSeparator()

        resetAllAxisAction = contextMenu.addAction(f"Reset All Axis")
        resetYAxisAction = contextMenu.addAction(f"Reset Y-Axis")
        # openAct = contextMenu.addAction("Open")
        # quitAct = contextMenu.addAction("Quit")
        # action = contextMenu.exec_(self.mapToGlobal(event.pos()))

        # show menu
        action = contextMenu.exec_(pos)
        if action is None:
            return
        
        actionText = action.text()
        # if actionText == f"Export Trace {myType}":
        #     #
        #     # See: plugins/exportTrace.py
        #     #

        #     # print('Opening Export Trace Window')

        #     # todo: pass xMin,xMax to constructor
        #     if self.myType == "vmFiltered":
        #         xyUnits = ("Time (sec)", "Vm (mV)")
        #     elif self.myType == "dvdtFiltered":
        #         xyUnits = ("Time (sec)", "dV/dt (mV/ms)")
        #     elif self.myType == "meanclip":
        #         xyUnits = ("Time (ms)", "Vm (mV)")
        #     else:
        #         logger.error(f'Unknown myType: "{self.myType}"')
        #         xyUnits = ("error time", "error y")

        #     path = self.detectionWidget.ba.fileLoader.filepath

        #     xMin, xMax = self.detectionWidget.getXRange()

        #     if self.myType in ["vm", "dvdt"]:
        #         xMargin = 2  # seconds
        #     else:
        #         xMargin = 2

        #     exportWidget = sanpy.interface.bExportWidget(
        #         self.x,
        #         self.y,
        #         xyUnits=xyUnits,
        #         path=path,
        #         xMin=xMin,
        #         xMax=xMax,
        #         xMargin=xMargin,
        #         type=self.myType,
        #         darkTheme=self.detectionWidget.useDarkStyle,
        #     )

        #     exportWidget.myCloseSignal.connect(self.slot_closeChildWindow)
        #     exportWidget.show()

        #     self.exportWidgetList.append(exportWidget)

        if actionText == "Reset All Axis":
            # print('Reset Y-Axis', self.myType)
            self.setAxisFull()

        elif actionText == "Reset Y-Axis":
            # print('Reset Y-Axis', self.myType)
            self.setAxisFull_y(self.myType)

        elif actionText == 'Crosshair':
            isChecked = action.isChecked()
            #isChecked = not isChecked
            logger.info(f'{actionText} {isChecked}')
            self.toggleCrosshair(isChecked)
            
        elif actionText == 'Cursors':
            isChecked = action.isChecked()
            logger.info(f'{actionText} {isChecked}')
            self._sanpyCursors.toggleCursors(isChecked)
            self._sanpyCursors_dvdt.toggleCursors(isChecked)
        else:
            isChecked = action.isChecked()
            if inVmPlot:
                _handled = self._sanpyCursors.handleMenu(actionText, isChecked)
            if inDerivPlot:
                _handled = self._sanpyCursors_dvdt.handleMenu(actionText, isChecked)

            if not _handled:
                logger.warning(f"action not taken: {action}")

    @property
    def sweepNumber(self):
        """Get the current sweep number (from bAnalysis)."""
        if self.ba is None:
            return None
        else:
            return self.ba.fileLoader.currentSweep

    def detect(
        self,
        detectionPresetStr: str,
        detectionType: sanpy.bDetection.detectionTypes,
        dvdtThreshold: float,
        mvThreshold: float,
        startSec: float = None,
        stopSec: float = None,
    ):
        """Detect spikes.

        Args:
            detectionPreset (str) corresponds to Enum sanpy.bDetection.detectionPresets_
            detectionType (sanpy.bDetection.detectionTypes): The type of detection (dvdt, vm)
        """

        _startSec = time.time()

        if self.ba is None:
            str = "Please select a file to analyze."
            self.updateStatusBar(str)
            return

        if self.ba.loadError:
            str = "Did not spike detect, the file was not loaded or may be corrupt?"
            self.updateStatusBar(str)
            return

        # logger.info(f'Detecting with dvdtThreshold:{dvdtThreshold} mvThreshold:{mvThreshold}')
        self.updateStatusBar(
            f"Detecting spikes detectionType:{detectionType.value} dvdt:{dvdtThreshold} minVm:{mvThreshold} start:{startSec} stop:{stopSec}"
        )

        if startSec is None or stopSec is None:
            startSec = 0
            stopSec = self.ba.fileLoader.recordingDur

        # TODO: replace with a member function
        _selectedDetection = self.detectToolbarWidget._selectedDetection
        detectionDict = self.getMainWindowDetectionClass().getDetectionDict(
            _selectedDetection
        )
        detectionDict[
            "detectionType"
        ] = detectionType.value  # set detection type to ('dvdt', 'vm')
        detectionDict["dvdtThreshold"] = dvdtThreshold
        detectionDict["mvThreshold"] = mvThreshold

        # TODO: pass this function detection params and call from sanpy_app ???
        if self.myMainWindow is not None:
            # grab parameters from main interface table
            logger.info("Grabbing detection parameters from main window table")

            # problem is these k/v have v that are mixture of str/float/int ... hard to parse
            myDetectionDict = self.myMainWindow.getSelectedFileDict()

            #
            # fill in detectionDict from *this interface
            detectionDict["startSeconds"] = startSec
            detectionDict["stopSeconds"] = stopSec

            # mar 2023, I removed these from the table
            # detectionDict['cellType'] = myDetectionDict['Cell Type']
            # detectionDict['sex'] = myDetectionDict['Sex']
            # detectionDict['condition'] = myDetectionDict['Condition']

        #
        # detect
        self.ba.spikeDetect(detectionDict)

        # show dialog when num spikes is 0
        """
        if self.ba.numSpikes == 0:
            informativeText = f'dV/dt Threshold:{dvdtThreshold}\nVm Threshold (mV):{mvThreshold}'
            sanpy.interface.bDialog.okDialog('No Spikes Detected', informativeText=informativeText)
        """

        #
        # fill in our start/stop in the main table
        # this is done in analysisDir.xxx()
        # setCellValue(self, rowIdx, colStr, value)

        self.replotOverlays()  # replot statistics over traces

        # 20210821
        # refresh spike clips
        # self.refreshClips(None, None)

        self.signalDetect.emit(self.ba)
        # if self.myMainWindow is not None:
        #    # signal to main window so it can update (file list, scatter plot)
        #    self.myMainWindow.mySignal('detect') #, data=(dfReportForScatter, dfError))

        # report the number of spikes and the time it took
        _stopSec = time.time()
        numSpikes = self.ba.numSpikes
        _elapsedSec = round(_stopSec - _startSec, 2)
        updateStr = f"Detected {numSpikes} in {_elapsedSec} seconds"
        self.updateStatusBar(updateStr)

    def mySetTheme(self, doReplot=True):
        if self.myMainWindow is not None and self.myMainWindow.useDarkStyle:
            # pg.setConfigOption('background', 'k')
            # pg.setConfigOption('foreground', 'w')
            self.useDarkStyle = True
        else:
            # pg.setConfigOption('background', 'w')
            # pg.setConfigOption('foreground', 'k')
            self.useDarkStyle = False
        if doReplot:
            self._replot(startSec=None, stopSec=None)

    def getMainWindowOptions(self):
        theRet = None
        if self.myMainWindow is not None:
            theRet = self.myMainWindow.getOptions()
        return theRet

    def getMainWindowDetectionClass(self):
        """The detection class loads a number of json files.
        When running SanPy app do this once.
        """
        theRet = None
        if self.myMainWindow is not None:
            theRet = self.myMainWindow.getDetectionClass()
        return theRet

    def getMainWindowFileLoaderDict(self):
        """The file loader dict loads and parses a number of .py files.
        When running SanPy app do this one.
        """
        theRet = None
        if self.myMainWindow is not None:
            theRet = self.myMainWindow.getFileLoaderDict()
        return theRet

    def save(self, saveCsv=True):
        """Prompt user for filename and save both xlsx and txt"""
        if self.ba is None or self.ba.numSpikes == 0:
            _warning = "No analysis to save"
            logger.warning(_warning)
            self.updateStatusBar(_warning)
            return
        xMin, xMax = self.getXRange()
        xMinStr = "%.2f" % (xMin)
        xMaxStr = "%.2f" % (xMax)

        lhs, rhs = xMinStr.split(".")
        xMinStr = "_b" + lhs + "_" + rhs

        lhs, rhs = xMaxStr.split(".")
        xMaxStr = "_e" + lhs + "_" + rhs

        filePath, fileName = os.path.split(os.path.abspath(self.ba.fileLoader.filepath))
        fileBaseName, extension = os.path.splitext(fileName)
        fileBaseName = f"{fileBaseName}{xMinStr}{xMaxStr}.csv"
        csvFileName = os.path.join(filePath, fileBaseName)

        # ask user for file to save
        savefile, tmp = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save CSV File", csvFileName
        )

        if len(savefile) > 0:
            logger.info(f"savefile: {savefile}")
            logger.info(f"  xMin:{xMin} xMax:{xMax} alsoSaveTxt:{saveCsv}")
            exportObj = sanpy.bExport(self.ba)
            analysisName, df = exportObj.saveReport(
                savefile, xMin, xMax, alsoSaveTxt=saveCsv
            )
            # if self.myMainWindow is not None:
            #    self.myMainWindow.mySignal('saved', data=analysisName)
            txt = f"Exported CSV file: {analysisName}"
            self.updateStatusBar(txt)
        else:
            # user cancelled save
            pass

    def getXRange(self):
        """Get the current range of X-Axis."""
        rect = self.vmPlot.viewRect()  # get xaxis
        xMin = rect.left()
        xMax = rect.right()
        return xMin, xMax

    def _setAxis(self, start, stop, set_xyBoth="xAxis", whichPlot="vm"):
        """Shared by (setAxisFull, setAxis)."""
        # make sure start/stop are in correct order and swap if necc.
        logger.info('')
        if start is not None and stop is not None:
            if stop < start:
                tmp = start
                start = stop
                stop = tmp

        # logger.info(f'start:{start} stop:{stop} set_xyBoth:{set_xyBoth} whichPlot:{whichPlot}')

        padding = 0
        if set_xyBoth == "xAxis":
            if start is None or np.isnan(stop) or stop is None or np.isnan(stop):
                start = 0
                stop = self.ba.fileLoader.recordingDur

            logger.info('!!!! SETING X !!!')
            # self.derivPlot.setXRange(start, stop, padding=padding) # linked to Vm
            self.vmPlot.setXRange(start, stop, padding=padding)  # linked to Vm

            # self.myKymWidget.kymographPlot.setXRange(
            #     start, stop, padding=padding
            # )  # row major is different

        if set_xyBoth == "yAxis":
            if whichPlot in ["dvdt", "dvdtFiltered"]:
                self.derivPlot.setYRange(start, stop)  # linked to Vm
            elif whichPlot in ["vm", "vmFiltered"]:
                self.vmPlot.setYRange(start, stop)  # linked to Vm
            else:
                logger.error(f"did not understand whichPlot: {whichPlot}")

        # update rectangle in vmPlotGlobal
        self.linearRegionItem2.setRegion([start, stop])

        # update detection toolbar
        if set_xyBoth == "xAxis":
            # 20230419
            # self.detectToolbarWidget.startSeconds.setValue(start)
            # self.detectToolbarWidget.startSeconds.repaint()
            # self.detectToolbarWidget.stopSeconds.setValue(stop)
            # self.detectToolbarWidget.stopSeconds.repaint()
            self.detectToolbarWidget._startSec = start
            self.detectToolbarWidget._stopSec = stop

        # else:
        #    print('todo: add interface for y range in bDetectionWidget._setAxis()')

        # if set_xyBoth == 'xAxis':
        #    self.refreshClips(start, stop)

        return start, stop

    def _old_setAxis_OnFileChange(self, startSec, stopSec):
        if (
            startSec is None
            or stopSec is None
            or math.isnan(startSec)
            or math.isnan(stopSec)
        ):
            startSec = 0
            stopSec = self.ba.fileLoader.recordingDur

        self.vmPlotGlobal.autoRange(items=[self.vmLinesFiltered2])  # always full view
        self.linearRegionItem2.setRegion([startSec, stopSec])

        # padding = 0
        # self.derivPlot.setXRange(startSec, stopSec, padding=padding) # linked to Vm
        # self.myKymWidget.kymographPlot.autoRange()  # row major is different

    def setAxisFull_y(self, thisAxis):
        """Set full y-axis.

        Args:
            thisAxis: Specifies the axis to set, like (vm, dvdt)
        """
        # logger.info(f'thisAxis:"{thisAxis}"')
        # y-axis is NOT shared
        # dvdt
        if thisAxis in ["dvdt", "dvdtFiltered"]:
            filteredDeriv = self.ba.fileLoader.filteredDeriv
            top = np.nanmax(filteredDeriv)
            bottom = np.nanmin(filteredDeriv)
            start, stop = self._setAxis(
                bottom, top, set_xyBoth="yAxis", whichPlot="dvdt"
            )
        elif thisAxis in ["vm", "vmFiltered"]:
            sweepY = self.ba.fileLoader.sweepY
            top = np.nanmax(sweepY)
            bottom = np.nanmin(sweepY)
            start, stop = self._setAxis(bottom, top, set_xyBoth="yAxis", whichPlot="vm")
        else:
            logger.error(f'Did not understand thisAxis:"{thisAxis}"')

    def setAxisFull(self):
        """Set full axis for (deriv, daq, vm, clips).
        """
        if self.ba is None:
            return

        logger.info('')

        # 20220115
        # self.vmPlot.autoRange(items=[self.vmLinesFiltered])
        # self.vmPlot.enableAutoRange()
        
        logger.info('!!!!! setting vmPlot auto range !!!')
        self.vmPlot.autoRange(items=[self.vmPlot_])  # 20221003
    
        # these are linked to vmPlot
        # self.derivPlot.autoRange()
        # self.dacPlot.autoRange()

        self.vmPlotGlobal.autoRange(items=[self.vmPlotGlobal_])  # we never zoom this

        # self.refreshClips(None, None)
        # self.clipPlot.autoRange()

        # rectangle region on vmPlotGlobal
        self.linearRegionItem2.setRegion([0, self.ba.fileLoader.recordingDur])

        # kymograph
        # self.myKymWidget.kymographPlot.setXRange(start, stop, padding=padding)  # row major is different
        #self.myKymWidget.kymographPlot.autoRange()  # row major is different
        if sanpy.DO_KYMOGRAPH_ANALYSIS:
            if self.ba.fileLoader.isKymograph():
                self.myKymWidget.kymographPlot.autoRange()

        #
        # update detection toolbar
        start = 0
        stop = self.ba.fileLoader.recordingDur
        # removed 20230419
        # self.detectToolbarWidget.startSeconds.setValue(start)
        # self.detectToolbarWidget.startSeconds.repaint()
        # self.detectToolbarWidget.stopSeconds.setValue(stop)
        # self.detectToolbarWidget.stopSeconds.repaint()
        self.detectToolbarWidget._startSec = start
        self.detectToolbarWidget._stopSec = stop
        
        # todo: make this a signal, with slot in main window
        if self.myMainWindow is not None:
            # currently, this will just update scatte plot
            logger.info('calling myMainWindow "set full x axis"')
            self.myMainWindow.mySignal("set full x axis")

    def setAxis(self, start, stop, set_xyBoth="xAxis", whichPlot="vm"):
        """Called when user click+drag in a pyQtGraph plot.

        Args:
            start
            stop
            set_xyBoth: (xAxis, yAxis, Both)
            whichPlot: (dvdt, vm)
        """
        # logger.info(f'start:{start} stop:{stop} set_xyBoth:{set_xyBoth} whichPlot:{whichPlot}')

        start, stop = self._setAxis(
            start, stop, set_xyBoth=set_xyBoth, whichPlot=whichPlot
        )
        # print('bDetectionWidget.setAxis()', start, stop)
        if set_xyBoth == "xAxis":
            if self.myMainWindow is not None:
                self.myMainWindow.mySignal("set x axis", data=[start, stop])
        # no need to emit change in y-axis, no other widgets change
        """
        elif set_xyBoth == 'yAxis':
            # todo: this needs to know which plot
            if self.myMainWindow is not None:
                self.myMainWindow.mySignal('set y axis', data=[start,stop])
        """
        # elif set_xyBoth == 'both':
        #    self.myMainWindow.mySignal('set y axis', data=[start,stop])

    def fillInDetectionParameters(self, tableRowDict):
        """ """
        # print('fillInDetectionParameters() tableRowDict:', tableRowDict)
        self.detectToolbarWidget.fillInDetectionParameters(tableRowDict)

    def updateStatusBar(self, text):
        if self.myMainWindow is not None:
            self.myMainWindow.slot_updateStatus(text)
        else:
            logger.info(text)

    def on_scatterClicked(self, item, points, ev=None):
        """

        Parameters
        ----------
        item : PlotDataItem
            that was clicked
        points : list of points clicked (pyqtgraph.graphicsItems.ScatterPlotItem.SpotItem)
        """

        """
        print('=== bDetectionWidget.on_scatterClicked')
        print('  item:', item)
        print('  points:', points)
        print('  ev:', ev)
        """
        indexes = []
        # print('item.data:', item.data())
        # for idx, p in enumerate(points):
        #    print(f'    points[{idx}].data():{p.data()} p.index:{p.index()} p.pos:{p.pos()}')

        if len(points) > 0:
            # just one point
            # when showing a sweep, this is relative to sweep (not abs in all analysis)
            sweepSpikeNumber = points[0].index()

            # convert sweep spike index to absolute
            _spikeNumber = self.ba.getStat("spikeNumber", sweepNumber=self.sweepNumber)
            absSpikeNumber = _spikeNumber[sweepSpikeNumber]

            logger.info(
                f"self.sweepNumber:{self.sweepNumber} sweepSpikeNumber:{sweepSpikeNumber} absIndex:{absSpikeNumber}"
            )
            eDict = {
                "spikeNumber": absSpikeNumber,
                "doZoom": False,
                "ba": self.ba,
            }
            logger.info(f"    {eDict}")

            self.signalSelectSpike.emit(eDict)

        """
        for p in points:
            p = p.pos()
            x, y = p.x(), p.y()
            lx = np.argwhere(item.data['x'] == x)
            ly = np.argwhere(item.data['y'] == y)
            i = np.intersect1d(lx, ly).tolist()
            indexes += i
        indexes = list(set(indexes))
        print('spike(s):', indexes)
        """

    def getEDD(self):
        # get x/y plot position of all EDD from all spikes
        # print('bDetectionWidget.getEDD()')
        x = []
        y = []
        # for idx, spike in enumerate(self.ba.spikeDict:
        spikeDictionaries = self.ba.getSpikeDictionaries(sweepNumber=self.sweepNumber)
        for idx, spike in enumerate(spikeDictionaries):
            preLinearFitPnt0 = spike["preLinearFitPnt0"]
            preLinearFitPnt1 = spike["preLinearFitPnt1"]

            if preLinearFitPnt0 is not None:
                preLinearFitPnt0 = self.ba.fileLoader.pnt2Sec_(preLinearFitPnt0)
            else:
                preLinearFitPnt0 = np.nan

            if preLinearFitPnt1 is not None:
                preLinearFitPnt1 = self.ba.fileLoader.pnt2Sec_(preLinearFitPnt1)
            else:
                preLinearFitPnt1 = np.nan

            preLinearFitVal0 = spike["preLinearFitVal0"]
            preLinearFitVal1 = spike["preLinearFitVal1"]

            x.append(preLinearFitPnt0)
            x.append(preLinearFitPnt1)
            x.append(np.nan)

            y.append(preLinearFitVal0)
            y.append(preLinearFitVal1)
            y.append(np.nan)

        # print ('  returning', len(x), len(y))
        return x, y

    def _old_getHalfWidths(self):
        """Get x/y pair for plotting all half widths."""
        # defer until we know how many half-widths 20/50/80
        x = []
        y = []
        numPerSpike = 3  # rise/fall/nan
        numSpikes = self.ba.numSpikes
        xyIdx = 0
        # for idx, spike in enumerate(self.ba.spikeDict):
        spikeDictionaries = self.ba.getSpikeDictionaries(sweepNumber=self.sweepNumber)
        for idx, spike in enumerate(spikeDictionaries):
            if idx == 0:
                # make x/y from first spike using halfHeights = [20,50,80]
                halfHeights = spike[
                    "halfHeights"
                ]  # will be same for all spike, like [20, 50, 80]
                numHalfHeights = len(halfHeights)
                # *numHalfHeights to account for rise/fall + padding nan
                x = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
                y = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
                # print('  len(x):', len(x), 'numHalfHeights:', numHalfHeights, 'numSpikes:', numSpikes, 'halfHeights:', halfHeights)

            if "widths" not in spike:
                print(f'=== Did not find "widths" key in spike {idx}')
                # print(spike)
            for idx2, width in enumerate(spike["widths"]):
                halfHeight = width["halfHeight"]  # [20,50,80]
                risingPnt = width["risingPnt"]
                risingVal = width["risingVal"]
                fallingPnt = width["fallingPnt"]
                fallingVal = width["fallingVal"]

                if risingPnt is None or fallingPnt is None:
                    # half-height was not detected
                    continue

                risingSec = self.ba.fileLoader.pnt2Sec_(risingPnt)
                fallingSec = self.ba.fileLoader.pnt2Sec_(fallingPnt)

                x[xyIdx] = risingSec
                x[xyIdx + 1] = fallingSec
                x[xyIdx + 2] = np.nan
                # y
                y[xyIdx] = fallingVal  # risingVal, to make line horizontal
                y[xyIdx + 1] = fallingVal
                y[xyIdx + 2] = np.nan

                # each spike has 3x pnts: rise/fall/nan
                xyIdx += numPerSpike  # accounts for rising/falling/nan
            # end for width
        # end for spike
        # print('  numSpikes:', numSpikes, 'xyIdx:', xyIdx)
        #
        return x, y

    def replotOverlays(self, oneIndex=None):
        """Replot analysis results overlays.

        Parameters
        ----------
        oneIndex : int
            If specified then replot just one overlay from self.myPlots
        """
    
        if self.ba is None:
            return

        # get marker symbols once (for spikes we are plotting)
        # if _spikeNumbers is None then no spikes
        _spikeNumbers = self.ba.getStat('spikeNumber', sweepNumber=self.sweepNumber)
        
        # logger.info(f'self.sweepNumber:{self.sweepNumber} _spikeNumbers:{_spikeNumbers}')

        _n = None
        if _spikeNumbers is not None:
            _n = len(_spikeNumbers)
        # logger.info(f'fetching {_n} markers and colors -- WILL  BE SLOW')
        
        _plotMarkerDict = sanpy.interface.plugins.getPlotMarkersAndColors(self.ba, _spikeNumbers)
        markerList_pg = _plotMarkerDict['markerList_pg']
        faceColors = _plotMarkerDict['faceColors']

        for idx, plot in enumerate(self.myPlots):
            if oneIndex is not None and idx != oneIndex:
                continue
            
            #print(plot)
            
            xPlot = []
            yPlot = []
            markers = []
            colors = []
            plotIsOn = plot["plotIsOn"]
            #  TODO: fix the logic here, we are not calling replot() when user toggles plot radio checkboxes
            # plotIsOn = True
            if plotIsOn and plot["humanName"] == "Half-Widths":
                spikeDictionaries = self.ba.getSpikeDictionaries(
                    sweepNumber=self.sweepNumber
                )
                sweepX = self.ba.fileLoader.sweepX
                sweepY = self.ba.fileLoader.sweepY
                # filteredVm = self.ba.filteredVm
                # filteredVm = filteredVm[:,0]
                xPlot, yPlot = sanpy.analysisUtil.getHalfWidthLines(
                    sweepX, sweepY, spikeDictionaries
                )
                self.myPlotList[idx].setData(x=xPlot, y=yPlot)

            elif plotIsOn and plot["humanName"] == "Epoch Lines":
                # vertical lines showing epoch within a sweep
                _epochTable = self.ba.fileLoader.getEpochTable(self.sweepNumber)
                if _epochTable is not None:
                    # happens when file is tif kymograph
                    sweepY = self.ba.fileLoader.sweepY
                    # filteredVm = self.ba.filteredVm
                    xPlot, yPlot = _epochTable.getEpochLines(
                        yMin=np.nanmin(sweepY), yMax=np.nanmax(sweepY)
                    )
                self.myPlotList[idx].setData(x=xPlot, y=yPlot)

            elif plotIsOn and plot["humanName"] == "EDD":
                xPlot, yPlot = self.getEDD()
                self.myPlotList[idx].setData(x=xPlot, y=yPlot)

            elif plotIsOn and plot["humanName"] == "EDD Rate":
                xPlot, yPlot = sanpy.analysisUtil.getEddLines(self.ba)
                self.myPlotList[idx].setData(x=xPlot, y=yPlot)

            elif plotIsOn:
                xPlot, yPlot = self.ba.getStat(
                    plot["x"], plot["y"], sweepNumber=self.sweepNumber
                )
                if xPlot is not None and plot["convertx_tosec"]:
                    xPlot = [
                        self.ba.fileLoader.pnt2Sec_(x) for x in xPlot
                    ]  # convert pnt to sec
                
                _brushList = [None] * len(xPlot)
                #_penList = [None] * len(xPlot)
                
                #print('faceColors:', faceColors)
                #print('markerList_pg:', markerList_pg)
                
                if faceColors is not None:
                    for _idx in range(len(xPlot)):
                        _brushList[_idx] = pg.mkBrush(faceColors[_idx])
                        #_penList[_idx] = pg.mkPen(faceColors[_idx])
                
                # use symbolBrush, not brush
                # see: https://stackoverflow.com/questions/41060163/pyqtgraph-scatterplotitem-setbrush
                self.myPlotList[idx].setData(x=xPlot, y=yPlot,
                                             symbolBrush=_brushList,
                                             #brush=_brushList,
                                             pen=None,
                                             symbol=markerList_pg,
                                             size=self._pgPointSize)

            # self.togglePlot(idx, plot['plotIsOn'])

        # update label with number of spikes detected
        # print('todo: bDetectionWidget.replot(), make numSpikesLabel respond to signal/slot')
        # numSpikesStr = str(self.ba.numSpikes)
        # self.detectToolbarWidget.numSpikesLabel.setText("Spikes: " + numSpikesStr)
        # self.detectToolbarWidget.numSpikesLabel.repaint()

        # spike freq
        # print('todo: bDetectionWidget.replot(), make spikeFreqLabel respond to signal/slot')
        # meanSpikeFreq = self.ba.getStatMean(
        #     "spikeFreq_hz", sweepNumber=self.sweepNumber
        # )
        # if meanSpikeFreq is not None:
        #     meanSpikeFreq = round(meanSpikeFreq, 2)
        # self.detectToolbarWidget.spikeFreqLabel.setText("Freq: " + str(meanSpikeFreq))
        # self.detectToolbarWidget.spikeFreqLabel.repaint()

        # num errors
        # self.detectToolbarWidget.numErrorsLabel.setText(
        #     "Errors: " + str(self.ba.numErrors())
        # )
        # self.detectToolbarWidget.numErrorsLabel.repaint()

    def togglePlot(self, idx: int, on: bool):
        """Toggle overlay of stats like (spike threshold, spike peak, ...).

        Arg:
            idx (int)
                overlay index into self.myPlots
            on (bool):
                if True then on
        """
        if isinstance(idx, str):
            logger.error(
                f'Unexpected type for parameter idx "{idx}" with type {type(idx)}'
            )
            return

        # toggle the plot on/off
        self.myPlots[idx]["plotIsOn"] = on

        if on:
            # self.myPlotList[idx].setData(pen=pg.mkPen(width=5, color=plot['color'], symbol=plot['symbol']), size=2)
            self.myPlotList[idx].show()
            # self.myPlotList[idx].setPen(pg.mkPen(width=5, color=plot['color'], symbol=plot['symbol']))
            # removed for half-width
            # self.myPlotList[idx].setSize(2)
        else:
            # self.myPlotList[idx].setData(pen=pg.mkPen(width=0, color=plot['color'], symbol=plot['symbol']), size=0)
            self.myPlotList[idx].hide()
            # self.myPlotList[idx].setPen(pg.mkPen(width=0, color=plot['color'], symbol=plot['symbol']))
            # removed for half-width
            # self.myPlotList[idx].setSize(0)

        # always replot everything
        self.replotOverlays(oneIndex=idx)

    def selectSweep(self,
        sweepNumber : int,
        startSec=None, stopSec=None,
        doEmit=True, doReplot=True
    ):
        """
        Parameters
        ----------
        sweepNumber : str or int
            From ('All', 0, 1, 2, 3, ...)
        startSec : float or None
        stopSec : float or None
        doEmit : bool
            If True then emit signal signalSelectSweep
        doReplot : bool
            If True then call _replot()
        """
        if sweepNumber == "":
            logger.error(f'got unexpected swep number "{sweepNumber}" {type(sweepNumber)}')
            return

        if sweepNumber == "All":
            sweepNumber = None
        else:
            sweepNumber = int(sweepNumber)

        if sweepNumber is not None and (
            sweepNumber < 0 or sweepNumber > self.ba.fileLoader.numSweeps - 1
        ):
            return

        logger.info(
            f'sweepNumber:"{sweepNumber}" {type(sweepNumber)} doEmit:{doEmit} startSec:"{startSec}" stopSec:"{stopSec}"'
        )

        # if self._sweepNumber == sweepNumber:
        #    logger.info(f'Already showing sweep:{sweepNumber}      RETURNING')
        #    return

        # self._sweepNumber = sweepNumber
        self.ba.fileLoader.setSweep(sweepNumber)

        # self.setAxisFull()

        # cancel spike selection
        self.selectSpike(None)

        if doReplot:
            self._replot(startSec, stopSec)  # will set full axis

        if doEmit:
            logger.info(f' -->> emit signalSelectSweep {sweepNumber}')
            self.signalSelectSweep.emit(self.ba, sweepNumber)

    def setSpikeStat(self, stat: str = "condition", value: str = "xxx"):
        """Set the selected spikes."""
        logger.info(f'setting spike stat "{stat}" to "{value}"')
        if self._selectedSpikeList is not None:
            self.ba.setSpikeStat(self._selectedSpikeList, stat, value)

    def selectSpike(self, spikeNumber: int, doZoom: bool = False, doEmit: bool = False):
        """

        Notes
        -----
        Will set the sweep if we are not looking at the sweep of spikeNumber

        Args:
            spikeNumber: absolute
            doZoom:
            doEmit: If True then emit signalSelectSpike signal
        """
        logger.info(f"spikeNumber:{spikeNumber} doZoom:{doZoom} doEmit:{doEmit}")
        logger.warning(f"  converting to spike list selection")

        # # march 11, 2023

        # if self._blockSlots:
        #     return

        # self._blockSlots = True

        # if spikeNumber is None:
        #     spikeList = []
        # else:
        #     spikeList = [spikeNumber]
        # self.selectSpikeList(spikeList, doEmit=True)

        # self._blockSlots = False

        # return

        # we will always use self.ba ('peakSec', 'peakVal')
        if self.ba is None:
            return
        if self.ba.numSpikes == 0:
            return

        spikeList = [spikeNumber]

        x = None
        y = None

        # potentially move on to a new sweep (while implementing Thian data)
        if spikeNumber is not None:
            if spikeNumber < 0 or spikeNumber > self.ba.numSpikes - 1:
                logger.error(
                    f"Got spike {spikeNumber} but expecting range [0,{self.ba.numSpikes-1})"
                )
                return

            sweep = self.ba.getSpikeStat(spikeList, "sweep")
            sweep = sweep[0]  # just the first
            if sweep != self.sweepNumber:
                logger.info(
                    f"!!! SWITCHING to sweep: {sweep} from self.sweepNumber:{self.sweepNumber}"
                )
                self.slot_selectSweep(sweep)

            # our plot is of ONE SWEEP, we need to convert abs spike number to
            # spike number within the sweep
            logger.info(f"spikeNumber: {spikeNumber}, sweep {sweep}, doZoom {doZoom}")
            sweepSpikeNumber = self.ba.getSweepSpikeFromAbsolute(spikeNumber, sweep)

            # removed mar 11
            # sweepSpikeList = [sweepSpikeNumber]
            # logger.info(f'  sweepSpikeNumber:{sweepSpikeNumber} {type(sweepSpikeNumber)}')

            # spikeList = [sweepSpikeNumber]

            # xPlot, yPlot = self.ba.getStat('peakSec', 'peakVal', sweepNumber=sweep)
            # xPlot = np.array(xPlot)
            # yPlot = np.array(yPlot)
            # try:
            #     x = xPlot[sweepSpikeList]
            #     y = yPlot[sweepSpikeList]
            # except (IndexError) as e:
            #     logger.error(f'{e}')

        # removed mar 11 2023
        # self.mySingleSpikeScatterPlot.setData(x=x, y=y)

        # zoom to one selected spike
        if spikeNumber is not None and doZoom:
            thresholdSeconds = self.ba.getStat(
                "thresholdSec", sweepNumber=self.sweepNumber
            )
            if sweepSpikeNumber < len(thresholdSeconds):
                logger.info("    !!!! REMOVE HARD CODED ZOOM")
                # thresholdSecond = thresholdSeconds[spikeNumber]
                thresholdSecond = thresholdSeconds[sweepSpikeNumber]
                thresholdSecond = round(thresholdSecond, 3)
                
                # TODO: replace with a member function
                # _selectedDetection = self.detectToolbarWidget._selectedDetection
                # detectionDict = self.getMainWindowDetectionClass().getDetectionDict(
                #     _selectedDetection
                # )

                # if we get here, we assume we have a banalysis and it has been detected
                detectionDict = self.ba.getDetectionDict()

                #print(detectionDict.keys())
                preSpikeClipWidth_ms = detectionDict['preSpikeClipWidth_ms']
                preSpikeClipWidth_sec = preSpikeClipWidth_ms / 1000
                
                postSpikeClipWidth_ms = detectionDict['postSpikeClipWidth_ms']
                postSpikeClipWidth_sec = postSpikeClipWidth_ms / 1000

                logger.info(f'zooming to preSpikeClipWidth_sec:{preSpikeClipWidth_sec}, postSpikeClipWidth_sec:{postSpikeClipWidth_sec}')
                
                startSec = thresholdSecond - preSpikeClipWidth_sec
                #startSec = round(startSec, 2)
                stopSec = thresholdSecond + postSpikeClipWidth_sec
                #stopSec = round(stopSec, 2)
                # print('  spikeNumber:', spikeNumber, 'thresholdSecond:', thresholdSecond, 'startSec:', startSec, 'stopSec:', stopSec)
                start = self.setAxis(startSec, stopSec)

        if doEmit:
            eDict = {
                "spikeNumber": spikeNumber,
                "doZoom": doZoom,
                "ba": self.ba,
            }
            logger.info(f"  -->> emit signalSelectSpike")
            self.signalSelectSpike.emit(eDict)

        # march 11, 2023
        if self._blockSlots:
            return

        self._blockSlots = True

        if spikeNumber is None:
            spikeList = []
        else:
            spikeList = [spikeNumber]
        self.selectSpikeList(spikeList, doEmit=True)

        self._blockSlots = False

    def selectSpikeList(self,
                        spikeList: List[int],
                        doZoom: bool = False,
                        doEmit: bool = False):
        """Visually select a number of spikes.

        Parameters
        ----------
        spikeList : list of int
            A list of spikes (absolute)

        Notes
        -----
        spikeList is absolute but we are only plotting a subset (for one sweep).
        """

        x = None
        y = None
        markerList_pg = None

        if len(spikeList) > 0:
            _xSweepSpikeNumber = self.ba.getStat(
                "sweepSpikeNumber", sweepNumber=self.sweepNumber
            )

            # get the abs spike numbers we are showing
            _xSpikeNumber = self.ba.getStat("spikeNumber", sweepNumber=self.sweepNumber)

            # convert abs spike number (across sweeps) to relative to one sweep
            _sweepSpikeList = [
                _sweepIdx for _sweepIdx, x in enumerate(_xSpikeNumber) if x in spikeList
            ]

            # logger.info('xxx')
            # print('spikeList:', spikeList)
            # print('_sweepSpikeList:', _sweepSpikeList)

            xPlot, yPlot = self.ba.getStat(
                "peakSec", "peakVal", sweepNumber=self.sweepNumber
            )
            xPlot = np.array(xPlot)
            yPlot = np.array(yPlot)
            # try:
            if 1:
                x = xPlot[_sweepSpikeList]
                y = yPlot[_sweepSpikeList]
            # except (IndexError) as e:
            #     # TODO: Cludge to handle spike selection (in a plugin) but we are not looking at that sweep
            #     # see selectSpike()
            #     # sweepSpikeNumber = self.ba.getSweepSpikeFromAbsolute(spikeNumber, sweep)
            #     logger.warning(f'  We are not looking at the correct sweep, self.sweepNumber:{self.sweepNumber}')
            #     return

            # make selection symbol match user type
            # remember, not all selected spikes are in the sweep we are showing
            _plotMarkerDict = sanpy.interface.plugins.getPlotMarkersAndColors(self.ba, _sweepSpikeList)
            markerList_pg = _plotMarkerDict['markerList_pg']

        self._selectedSpikeList = spikeList

        self.mySpikeListScatterPlot.setData(x=x, y=y)
        
        # set symbol for userType
        if markerList_pg is not None:
            self.mySpikeListScatterPlot.setSymbol(markerList_pg)

        # TODO: I don't think anybody is listening to this
        if doEmit:
            if self._blockSlots:
                return
            self._blockSlots = True
            eDict = {
                "spikeList": spikeList,
                "doZoom": doZoom,
                "ba": self.ba,
            }
            logger.info(f"  -->> emit signalSelectSpikeList eDict")
            self.signalSelectSpikeList.emit(eDict)
            self._blockSlots = False

    # def _old_refreshClips(self, xMin=None, xMax=None):
    #     if not self.clipPlot.isVisible():
    #         # clips are not being displayed
    #         # logger.info('Clips not visible --- RETURNING')
    #         return

    #     logger.info("")

    #     # always remove existing
    #     # if there are no clips and we bail we will at least clear display
    #     self.clipPlot.clear()

    #     # if self.clipLines is not None:
    #     #    self.clipPlot.removeItem(self.clipLines)
    #     # if self.meanClipLine is not None:
    #     #    self.clipPlot.removeItem(self.meanClipLine)

    #     if self.ba is None:
    #         return

    #     if self.ba.numSpikes == 0:
    #         return

    #     # this returns x-axis in ms
    #     theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(
    #         xMin, xMax, sweepNumber=self.sweepNumber
    #     )

    #     # convert clips to 2d ndarray ???
    #     xTmp = np.array(theseClips_x)
    #     # xTmp /= self.ba.dataPointsPerMs # pnt to ms
    #     xTmp /= self.ba.fileLoader.dataPointsPerMs * 1000  # pnt to seconds
    #     yTmp = np.array(theseClips)

    #     # print('refreshClips() xTmp:', xTmp.shape)
    #     # print('refreshClips() yTmp:', yTmp.shape)

    #     self.clipLines = MultiLine(xTmp, yTmp, self, allowXAxisDrag=False, type="clip")
    #     self.clipPlot.addItem(self.clipLines)

    #     # print(xTmp.shape) # (num spikes, time)
    #     self.xMeanClip = xTmp
    #     if len(self.xMeanClip) > 0:
    #         self.xMeanClip = np.nanmean(xTmp, axis=0)  # xTmp is in ms
    #     self.yMeanClip = yTmp
    #     if len(self.yMeanClip) > 0:
    #         self.yMeanClip = np.nanmean(yTmp, axis=0)
    #     self.meanClipLine = MultiLine(
    #         self.xMeanClip, self.yMeanClip, self, allowXAxisDrag=False, type="meanclip"
    #     )
    #     self.clipPlot.addItem(self.meanClipLine)

    def toggleInterface(self, item, on):
        """Visually toggle different portions of interface"""
        # print('toggle_Interface()', item, on)
        # if item == 'Clips':
        #    #self.toggleClips(on)
        #    if self.myMainWindow is not None:
        #        #self.myMainWindow.toggleStatisticsPlot(on)
        #        self.myMainWindow.preferencesSet('display', 'showClips', on)
        #    if on:
        #        self.clipPlot.show()
        #        self.refreshClips() # refresh if they exist (e.g. analysis has been done)
        #    else:
        #        self.clipPlot.hide()
        """
        if item == 'dV/dt':
            #self.toggle_dvdt(on)
            if self.myMainWindow is not None:
                #self.myMainWindow.toggleStatisticsPlot(on)
                self.myMainWindow.preferencesSet('display', 'showDvDt', on)
            if on:
                self.derivPlot.show()
            else:
                self.derivPlot.hide()
        elif item == 'DAC':
            #self.toggle_dvdt(on)
            if self.myMainWindow is not None:
                #self.myMainWindow.toggleStatisticsPlot(on)
                self.myMainWindow.preferencesSet('display', 'showDAC', on)
            if on:
                self.dacPlot.show()
            else:
                self.dacPlot.hide()
        elif item == 'Global Vm':
            #self.toggle_dvdt(on)
            if self.myMainWindow is not None:
                #self.myMainWindow.toggleStatisticsPlot(on)
                self.myMainWindow.preferencesSet('display', 'showGlobalVm', on)
            if on:
                self.vmPlotGlobal.show()
            else:
                self.vmPlotGlobal.hide()
        """

        if item == "Full Recording":
            if on:
                self.vmPlotGlobal.show()
            else:
                self.vmPlotGlobal.hide()
        elif item == "Derivative":
            if on:
                self.derivPlot.show()
            else:
                self.derivPlot.hide()
        elif item == "DAC":
            if on:
                self.dacPlot.show()
            else:
                self.dacPlot.hide()

        # toggle in myDetectionToolbarWidget
        elif item == "Detection Panel":
            if on:
                self.detectToolbarWidget.show()
            else:
                self.detectToolbarWidget.hide()
        elif item == "Detection":
            self.detectToolbarWidget.toggleInterface(item, on)
        elif item == "Display":
            self.detectToolbarWidget.toggleInterface(item, on)
        elif item == "Plot Options":
            self.detectToolbarWidget.toggleInterface(item, on)
        elif item == "Set Spikes":
            self.detectToolbarWidget.toggleInterface(item, on)
        elif item == "Set Meta Data":
            self.detectToolbarWidget.toggleInterface(item, on)

        else:
            # Toggle overlay of stats like (TOP, spike peak, half-width, ...)
            self.togglePlot(item, on)  # assuming item is int !!!

    def _old_kymographChanged(self, event):
        """
        User finished gragging the ROI

        Args:
            event (pyqtgraph.graphicsItems.ROI.ROI)
        """
        logger.info("")
        # print(event)
        pos = event.pos()
        size = event.size()
        # print(pos, size)

        # imagePos = self.myImageItem.mapFromScene(event.scenePos())
        # imageSize = self.myImageItem.mapFromScene(event.size())
        # print('  imagePos:', imagePos, 'imageSize:', imageSize)

        left, top, right, bottom = None, None, None, None
        handles = event.getSceneHandlePositions()
        for handle in handles:
            if handle[0] is not None:
                imagePos = self.myImageItem.mapFromScene(handle[1])
                x = imagePos.x()
                y = imagePos.y()
                # units are in image pixels !!!
                # print(handle[0], 'x:', x, 'y:', y)
                if handle[0] == "topleft":
                    left = x
                    bottom = y
                    # top = y
                elif handle[0] == "bottomright":
                    right = x
                    top = y
                    # bottom = y
        #
        left = int(left)
        top = int(top)
        right = int(right)
        bottom = int(bottom)

        if left < 0:
            left = 0

        print(f"  left:{left} top:{top} right:{right} bottom:{bottom}")

        #  cludge
        if bottom > top:
            logger.warning(f"fixing bad top/bottom")
            tmp = top
            top = bottom
            bottom = tmp

        theRect = [left, top, right, bottom]
        self.ba._updateTifRoi(theRect)

        self._replot(startSec=None, stopSec=None, userUpdate=True)

        self.signalDetect.emit(self.ba)  # underlying _abf has new rect

    def slot_kymographChanged(self):
        self._replot(startSec=None, stopSec=None, userUpdate=True)
        self.signalDetect.emit(self.ba)  # underlying _abf has new rect

    def _buildUI(self):
        self.mySetTheme(doReplot=False)

        # left is toolbar, right is PYQtGraph (self.view)
        self.myHBoxLayout_detect = QtWidgets.QHBoxLayout(self)
        self.myHBoxLayout_detect.setAlignment(QtCore.Qt.AlignTop)

        # hSplitter gets added to h layout
        # then we add left/right widgets to the splitter
        _hSplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # detection widget toolbar
        self.detectToolbarWidget = myDetectToolbarWidget2(self.myPlots, self)
        self.signalSelectSpike.connect(self.detectToolbarWidget.slot_selectSpike)
        self.signalSelectSpikeList.connect(
            self.detectToolbarWidget.slot_selectSpikeList
        )

        # v1
        self.myHBoxLayout_detect.addWidget(self.detectToolbarWidget)
        # v2
        # _hSplitter.addWidget(self.detectToolbarWidget)
        # self.myHBoxLayout_detect.addWidget(_hSplitter)

        # kymograph, we need a vboxlayout to hold (kym widget, self.view)
        vBoxLayoutForPlot = QtWidgets.QVBoxLayout(self)

        # for publication, don't do kymographs
        # make a branch and get this working
        if sanpy.DO_KYMOGRAPH_ANALYSIS:
            self.myKymWidget = sanpy.interface.kymographWidget()
            self.myKymWidget.signalKymographRoiChanged.connect(self.slot_kymographChanged)
            self.myKymWidget.setVisible(False)
            self.myKymWidget.showSliceLine(False)
            self.myKymWidget.showLineSlider(False)
            vBoxLayoutForPlot.addWidget(self.myKymWidget)

        xPlotEmpty = []  # np.arange(0, _recordingDur)
        yPlotEmpty = []  # xPlot * np.nan

        # addPlot return a plotItem
        self.vmPlotGlobal = pg.PlotWidget()
        self.vmPlotGlobal_ = self.vmPlotGlobal.plot(name="vmPlotGlobal")
        self.vmPlotGlobal_.setData(xPlotEmpty, yPlotEmpty, connect="finite")
        vBoxLayoutForPlot.addWidget(self.vmPlotGlobal)
        self.vmPlotGlobal.enableAutoRange()

        self.derivPlot = pg.PlotWidget(name='derivPlot')
        self.derivPlot_ = self.derivPlot.plot(name="derivPlot")
        self.derivPlot_.setData(xPlotEmpty, yPlotEmpty, connect="finite")
        vBoxLayoutForPlot.addWidget(self.derivPlot)
        self.derivPlot.enableAutoRange()
        self.derivPlot.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.derivPlot.customContextMenuRequested.connect(partial(self.slot_contextMenu,'derivPlot', self.derivPlot))

        self.dacPlot = pg.PlotWidget()
        self.dacPlot_ = self.dacPlot.plot(name="dacPlot")
        self.dacPlot_.setData(xPlotEmpty, yPlotEmpty, connect="finite")
        vBoxLayoutForPlot.addWidget(self.dacPlot)
        self.dacPlot.enableAutoRange()

        self.vmPlot = pg.PlotWidget(name='vmPlot')
        # vmPlot_ is pyqtgraph.graphicsItems.PlotDataItem.PlotDataItem
        self.vmPlot_ = self.vmPlot.plot(name="vmPlot")
        self.vmPlot_.setData(xPlotEmpty, yPlotEmpty, connect="finite")
        vBoxLayoutForPlot.addWidget(self.vmPlot)
        self.vmPlot.enableAutoRange()
        # see: https://wiki.python.org/moin/PyQt/Handling%20context%20menus
        self.vmPlot.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.vmPlot.customContextMenuRequested.connect(partial(self.slot_contextMenu,'vmPlot', self.vmPlot))

        # show hover text when showing crosshairs
        self._displayHoverText= pg.TextItem(text='xxx hover', color=(200,200,200), anchor=(1,1))
        self._displayHoverText.hide()
        self.vmPlot.addItem(self._displayHoverText, ignorBounds=True)

        self._displayHoverText_deriv = pg.TextItem(text='xxx hover', color=(200,200,200), anchor=(1,1))
        self._displayHoverText_deriv.hide()
        self.derivPlot.addItem(self._displayHoverText_deriv, ignorBounds=True)

        # link x-axis
        self.derivPlot.setXLink(self.vmPlot)
        self.dacPlot.setXLink(self.vmPlot)
        # self.myKymWidget.kymographPlot.setXLink(self.vmPlot)  # row major is different

        # July 15, 2023
        # cursors, start by adding to vmPlot
        self._sanpyCursors = sanpy.interface.sanpyCursors(self.vmPlot)
        self._sanpyCursors.signalCursorDragged.connect(self.updateStatusBar)
        self._sanpyCursors.signalSetDetectionParam.connect(self._setDetectionParam)

        self._sanpyCursors_dvdt = sanpy.interface.sanpyCursors(self.derivPlot)
        self._sanpyCursors_dvdt.signalCursorDragged.connect(self.updateStatusBar)
        self._sanpyCursors_dvdt.signalSetDetectionParam.connect(self._setDetectionParam)
        
        #
        # mouse crosshair
        # crosshairPlots = ['derivPlot', 'dacPlot', 'vmPlot', 'clipPlot']
        crosshairPlots = ["derivPlot", "dacPlot", "vmPlot"]
        self.crosshairDict = {}
        for crosshairPlot in crosshairPlots:
            self.crosshairDict[crosshairPlot] = {
                "h": pg.InfiniteLine(angle=0, movable=False),
                "v": pg.InfiniteLine(angle=90, movable=False),
            }
            # start hidden
            self.crosshairDict[crosshairPlot]["h"].hide()
            self.crosshairDict[crosshairPlot]["v"].hide()

            # add h/v to appropriate plot
            if crosshairPlot == "derivPlot":
                self.derivPlot.addItem(
                    self.crosshairDict[crosshairPlot]["h"], ignoreBounds=True
                )
                self.derivPlot.addItem(
                    self.crosshairDict[crosshairPlot]["v"], ignoreBounds=True
                )
            elif crosshairPlot == "dacPlot":
                self.dacPlot.addItem(
                    self.crosshairDict[crosshairPlot]["h"], ignoreBounds=True
                )
                self.dacPlot.addItem(
                    self.crosshairDict[crosshairPlot]["v"], ignoreBounds=True
                )
            elif crosshairPlot == "vmPlot":
                self.vmPlot.addItem(
                    self.crosshairDict[crosshairPlot]["h"], ignoreBounds=True
                )
                self.vmPlot.addItem(
                    self.crosshairDict[crosshairPlot]["v"], ignoreBounds=True
                )
            # elif crosshairPlot == 'clipPlot':
            #    self.clipPlot.addItem(self.crosshairDict[crosshairPlot]['h'], ignoreBounds=True)
            #    self.clipPlot.addItem(self.crosshairDict[crosshairPlot]['v'], ignoreBounds=True)
            else:
                logger.error(f"case not taken for crosshairPlot: {crosshairPlot}")

        #
        # epoch as vertical lines
        # we don't know the number of epochs until we have a ba?

        # trying to implement mouse moved events
        # self.myProxy = pg.SignalProxy(
        #     self.vmPlot.scene().sigMouseMoved, rateLimit=60, slot=self._myMouseMoved
        # )
        self.vmPlotGlobal.scene().sigMouseMoved.connect(partial(self._myMouseMoved, 'vmPlotGlobal'))
        self.derivPlot.scene().sigMouseMoved.connect(partial(self._myMouseMoved, 'derivPlot'))
        self.dacPlot.scene().sigMouseMoved.connect(partial(self._myMouseMoved, 'dacPlot'))
        self.vmPlot.scene().sigMouseMoved.connect(partial(self._myMouseMoved, 'vmPlot'))

        # does not have setStyleSheet
        # self.derivPlot.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))

        # hide the little 'A' button to rescale axis
        self.vmPlotGlobal.hideButtons()
        self.derivPlot.hideButtons()
        self.dacPlot.hideButtons()
        self.vmPlot.hideButtons()
        # self.clipPlot.hideButtons()

        # turn off right-click menu
        self.vmPlotGlobal.setMenuEnabled(False)
        self.derivPlot.setMenuEnabled(False)
        self.dacPlot.setMenuEnabled(False)
        self.vmPlot.setMenuEnabled(False)

        # # 20221003 just link everything to vmPlot
        # self.derivPlot.setXLink(self.vmPlot)
        # self.dacPlot.setXLink(self.vmPlot)
        
        # #self.vmPlot.setXLink(self.myKymWidget.kymographPlot)
        # self.myKymWidget.kymographPlot.setXLink(self.vmPlot)  # row major is different    
        # # self.myKymWidget.myImageItem.setXLink(self.vmPlot)

        # turn off x/y dragging of deriv and vm
        self.vmPlotGlobal.setMouseEnabled(x=True, y=False)
        self.derivPlot.setMouseEnabled(x=True, y=False)
        self.dacPlot.setMouseEnabled(x=True, y=False)
        self.vmPlot.setMouseEnabled(x=True, y=False)


        # single spike selection
        # removed mar 11 2023
        # color = 'y'
        # symbol = 'x'
        # size = 20
        # self.mySingleSpikeScatterPlot = pg.ScatterPlotItem(pen=pg.mkPen(width=2, color=color), symbol=symbol, size=size)
        # self.vmPlot.addItem(self.mySingleSpikeScatterPlot)

        # mult spike selection (spikeList)
        # TODO: make sure this on top of the plot of analysis results
        color = "y"
        symbol = "o"
        size = 12
        self.mySpikeListScatterPlot = pg.ScatterPlotItem(
            pen=pg.mkPen(width=2, color=color), symbol=symbol, size=size
        )
        self.vmPlot.addItem(self.mySpikeListScatterPlot, ignorBounds=True)

        # TODO: add this to application options
        _defaultScatterCircleSize = 8  # 6
        
        # add all overlaid scatter plots
        self.myPlotList = []  # list of pg.ScatterPlotItem
        for idx, plot in enumerate(self.myPlots):
            color = plot["color"]
            symbol = plot["symbol"]
            humanName = plot["humanName"]
            if humanName in ["Half-Widths"]:
                # PlotCurveItem
                # default is no symbol
                myScatterPlot = pg.PlotDataItem(
                    pen=pg.mkPen(width=2, color=color), connect="finite"
                )
            elif humanName in ["Epoch Lines"]:
                # TODO: this is causing an error on linux after pip install sanpy-ephys[gui]
                # TODO: clone sanpy repo on linux and troubleshoot (do not go through the whole PyPi workflow
                myScatterPlot = pg.PlotDataItem(
                    pen=pg.mkPen(width=2, color=color, style=QtCore.Qt.DashLine),
                    connect="finite",
                )  # default is no symbol
            elif humanName == "EDD Rate":
                # edd rate is a dashed line showing slope/rate of edd
                myScatterPlot = pg.PlotDataItem(
                    pen=pg.mkPen(width=2, color=color, style=QtCore.Qt.DashLine),
                    connect="finite",
                )  # default is no symbol
            else:
                myScatterPlot = pg.PlotDataItem(
                    pen=None,
                    symbol=symbol,
                    symbolSize=_defaultScatterCircleSize,
                    symbolPen=None,
                    symbolBrush=color,
                )
                myScatterPlot.setData(x=[], y=[])  # start empty
                if humanName in ["Threshold (mV)", "AP Peak (mV)"]:
                    myScatterPlot.sigPointsClicked.connect(self.on_scatterClicked)

            self.myPlotList.append(myScatterPlot)

            # add plot to pyqtgraph
            if plot["plotOn"] == "vm":
                self.vmPlot.addItem(myScatterPlot, ignorBounds=True)
            elif plot["plotOn"] == "vmGlobal":
                self.vmPlotGlobal.addItem(myScatterPlot, ignorBounds=True)
            elif plot["plotOn"] == "dvdt":
                self.derivPlot.addItem(myScatterPlot, ignorBounds=True)

        self.replotOverlays()

        # was this june 4
        # vBoxLayoutForPlot.addWidget(self.view)

        # v1
        self.myHBoxLayout_detect.addLayout(vBoxLayoutForPlot)
        # v2
        # _tmpSplitterWidget = QtWidgets.QWidget()
        # _tmpSplitterWidget.setLayout(vBoxLayoutForPlot)
        # _hSplitter.addWidget(_tmpSplitterWidget)

    # def _cursorDragged(self, name, infLine):
    #     # logger.info(f'{name} {infLine.pos()}')
    #     xCursorA = self._cursorA.pos().x()
    #     xCursorB = self._cursorB.pos().x()
    #     delx = xCursorB - xCursorA
    #     delx = round(delx, 4)
    #     logger.info(f'delx:{delx}')

    #     self._cursorB.label.setFormat(f'B\ndelx={delx}')
    #     delStr = f'Cursor Delta X = {delx}'
    #     self.updateStatusBar(delStr)

    # def toggleCursors(self, visible : bool):
    #     self._showCursors = visible
    #     self._cursorA.setVisible(visible)
    #     self._cursorB.setVisible(visible)
        
    #     if visible:
    #         # set position to start/stop of current view
    #         pass

    def _setDetectionParam(self, detectionParam : str, value : float):
        """Set a detection param.
        
        This is in response to sanpyCursors context menu.
        """
        # human name of detection type ('SA Node'', "Fast NEuron", etc)
        selectedDetection = self.detectToolbarWidget._selectedDetection  # str

        logger.info(f'selectedDetection{selectedDetection} detectionParam:{detectionParam} value:{value}')

        _detectionClass = self.getMainWindowDetectionClass()
        detectionKey = _detectionClass.getDetectionKey(selectedDetection)

        _detectionClass.setValue(detectionKey, detectionParam, value)

        # update the interface
        self.detectToolbarWidget.on_detection_preset_change(selectedDetection)

    def toggleCrosshair(self, onOff):
        """Toggle mouse crosshair on and off.
        """
        self._showCrosshair = onOff
        if onOff:
            self._displayHoverText.show()
            self._displayHoverText_deriv.show()
        else:
            self._displayHoverText.hide()
            self._displayHoverText_deriv.hide()

        for plotName in self.crosshairDict.keys():
            self.crosshairDict[plotName]["h"].setVisible(onOff)
            self.crosshairDict[plotName]["v"].setVisible(onOff)

    def _myMouseMoved(self, inPlot, event):
        """Respond to mouse moves.

            Update cursor position
            If crosshair is visible, update that too.

        Args:
            event: PyQt5.QtCore.QPointF
        """

        # looking directly at checkbox in myDetectionToolbarWidget2
        # _crossHairIsOn = self.detectToolbarWidget.crossHairCheckBox.isChecked()
        #if not self.detectToolbarWidget.crossHairCheckBox.isChecked():
        if not self._showCrosshair:
            return

        # logger.info(f'"{inPlot}" {event}')

        # pos = event[0]  ## using signal proxy turns original arguments into a tuple
        pos = event

        # logger.info(pos)

        x = None
        y = None
        mousePoint = None
        # inPlot = None
        # if 0 and self.derivPlot.sceneBoundingRect().contains(pos):
        if inPlot == 'derivPlot':
            # logger.info('move in deriv')
            # deriv
            # inPlot = "derivPlot"
            self.crosshairDict[inPlot]["h"].show()
            self.crosshairDict[inPlot]["v"].show()
            # mousePoint = self.derivPlot.vb.mapSceneToView(pos)
            #mousePoint = self.derivPlot.mapSceneToView(pos)
            # mousePoint = self.derivPlot.scene().mapSceneToView()
            mousePoint = self.derivPlot.getPlotItem().getViewBox().mapSceneToView(pos)
            # hide the horizontal in dacPlot
            self.crosshairDict["dacPlot"]["v"].show()
            self.crosshairDict["dacPlot"]["h"].hide()
            # hide the horizontal in vmPlot
            self.crosshairDict["vmPlot"]["v"].show()
            self.crosshairDict["vmPlot"]["h"].hide()

            x = mousePoint.x()
            y = mousePoint.y()

            x = round(x,4)
            y = round(y,4)

            if self._showCrosshair:
                _hoverText = f'x:{x} \n y:{y}'
                self._displayHoverText_deriv.setText(_hoverText)
                self._displayHoverText_deriv.setPos(x, y)

        # elif 0 and self.dacPlot.sceneBoundingRect().contains(pos):
        elif inPlot == 'dacPlot':
            # logger.info('move in dac')
            # dac
            # inPlot = "dacPlot"
            self.crosshairDict[inPlot]["h"].show()
            self.crosshairDict[inPlot]["v"].show()
            # mousePoint = self.dacPlot.vb.mapSceneToView(pos)
            mousePoint = self.dacPlot.getPlotItem().getViewBox().mapSceneToView(pos)
            # hide the horizontal in derivPlot
            self.crosshairDict["derivPlot"]["v"].show()
            self.crosshairDict["derivPlot"]["h"].hide()
            # hide the horizontal in vmPlot
            self.crosshairDict["vmPlot"]["v"].show()
            self.crosshairDict["vmPlot"]["h"].hide()

        # elif self.vmPlot.sceneBoundingRect().contains(pos):
        elif inPlot == 'vmPlot':
            # logger.info('move in vm')
            # vm
            # inPlot = "vmPlot"
            self.crosshairDict[inPlot]["h"].show()
            self.crosshairDict[inPlot]["v"].show()
            # mousePoint = self.vmPlot.vb.mapSceneToView(pos)
            mousePoint = self.vmPlot.getPlotItem().getViewBox().mapSceneToView(pos)
            # hide the horizontal in dacPlot
            self.crosshairDict["dacPlot"]["v"].show()
            self.crosshairDict["dacPlot"]["h"].hide()
            # hide the horizontal in derivPlot
            self.crosshairDict["derivPlot"]["v"].show()
            self.crosshairDict["derivPlot"]["h"].hide()

            #
            # 20230419 implementing mouse hover tooltip
            # moved to _buildUI()
            # self._displayHoverText= pg.TextItem(text='444',color=(176,23,31),anchor=(1,1))
            # self.vmPlot.addItem(self._displayHoverText)

            if self._showCrosshair:
                x = mousePoint.x()
                y = mousePoint.y()

                x = round(x,4)
                y = round(y,4)

                _hoverText = f'x:{x} \n y:{y}'
                self._displayHoverText.setText(_hoverText)
                self._displayHoverText.setPos(x, y)

        # elif self.clipPlot.sceneBoundingRect().contains(pos):
        #    # clip
        #    inPlot = 'clipPlot'
        #    self.crosshairDict[inPlot]['h'].show()
        #    self.crosshairDict[inPlot]['v'].show()
        #    mousePoint = self.clipPlot.vb.mapSceneToView(pos)
        #    # hide the horizontal/vertical in both derivPlot and vmPlot

        if inPlot is not None and mousePoint is not None:
            self.crosshairDict[inPlot]["h"].setPos(mousePoint.y())
            self.crosshairDict[inPlot]["v"].setPos(mousePoint.x())

        if inPlot == "derivPlot":
            self.crosshairDict["dacPlot"]["v"].setPos(mousePoint.x())
            self.crosshairDict["vmPlot"]["v"].setPos(mousePoint.x())
            if self._showCrosshair:
                self._displayHoverText_deriv.show()
                self._displayHoverText.hide()

        elif inPlot == "dacPlot":
            self.crosshairDict["derivPlot"]["v"].setPos(mousePoint.x())
            self.crosshairDict["vmPlot"]["v"].setPos(mousePoint.x())
            self._displayHoverText.hide()
            if self._showCrosshair:
                self._displayHoverText_deriv.hide()
                self._displayHoverText.hide()

        if inPlot == "vmPlot":
            self.crosshairDict["derivPlot"]["v"].setPos(mousePoint.x())
            self.crosshairDict["dacPlot"]["v"].setPos(mousePoint.x())
            if self._showCrosshair:
                self._displayHoverText_deriv.hide()
                self._displayHoverText.show()

        # if mousePoint is not None:
        #     x = mousePoint.x()
        #     y = mousePoint.y()

        # x/y can still be None
        # removed 20230419 on adding _displayHoverText
        # self.detectToolbarWidget.setMousePositionLabel(x, y)

        # _hoverText = f'x:{x} \n y:{y}'
        # self._displayHoverText.setText(_hoverText)
        # self._displayHoverText.setPos(mousePoint.x(), mousePoint.y())

    def keyPressEvent(self, event):
        """Respond to user key press.

        Parameters
        ----------
        event : PyQt5.QtGui.QKeyEvent
        """
        key = event.key()
        text = event.text()
        logger.info(f"bDetectionWidget key:{key} text:{text}")

        # handled in 'View' menu
        # if text == 'h':
        # if key == QtCore.Qt.Key_H:
        #     if self.detectToolbarWidget.isVisible():
        #         self.detectToolbarWidget.hide()
        #     else:
        #         self.detectToolbarWidget.show()

        # if text == 'a':
        if key in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            # self.detectToolbarWidget.keyPressEvent(event)
            self.setAxisFull()

        elif key == QtCore.Qt.Key.Key_Escape:
            self.myMainWindow.mySignal("cancel all selections")

        elif key in [QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Equal]:
            self._pgPointSize *= 5
            logger.info(f'_pgPointSize:{self._pgPointSize}')
            self._replot()
        elif key in [QtCore.Qt.Key.Key_Minus]:
            self._pgPointSize -= 10
            if self._pgPointSize < 0:
                self._pgPointSize = 0
            logger.info(f'_pgPointSize:{self._pgPointSize}')
            self._replot()

        elif key == QtCore.Qt.Key.Key_N:
            # set metadata (note) of file loader
            if self.ba is not None:
                pass
                # setMetaData

        # elif key == QtCore.Qt.Key_C:
        #     logger.warning("what was this for ??? responding to keyboard C ???")
        #     # self.setSpikeStat()

    def slot_setSpikeStat(self, setSpikeStatEvent: dict):
        """Respond to changes from setSpikeStack plugin.

        Notes
        -----
        setSpikeStatEvent = {}
        setSpikeStatEvent['spikeList'] = self.getSelectedSpikes()
        setSpikeStatEvent['colStr'] = colStr
        setSpikeStatEvent['value'] = value
        """
        logger.info(f"setSpikeStatEvent: {setSpikeStatEvent}")

        spikeList = setSpikeStatEvent["spikeList"]
        colStr = setSpikeStatEvent["colStr"]
        value = setSpikeStatEvent["value"]

        # set the stat
        self.ba.setSpikeStat(spikeList, colStr, value)

        # logger.info(f"  -->> emit signalDetect")
        # self.signalDetect.emit(self.ba)  # underlying _abf has new rect

    def slot_selectSweep(self, sweep: int):
        """Fake slot, not using in emit/connect."""
        self.selectSweep(sweep)
        self.detectToolbarWidget.slot_selectSweep(sweep)

    def slot_selectSpike(self, sDict):
        logger.info(f"detection widget {sDict}")

        spikeNumber = sDict["spikeNumber"]
        doZoom = sDict["doZoom"]

        # march 11, 2023 was this
        # this will set the correct sweep
        self.selectSpike(spikeNumber, doZoom=doZoom)

        if spikeNumber is None:
            spikeList = []
        else:
            spikeList = [spikeNumber]

        spikeListDict = {"spikeList": spikeList, "doZoom": doZoom}
        self.slot_selectSpikeList(spikeListDict)

    def slot_selectSpikeList(self, sDict):
        # print('detectionWidget.slotSelectSpike() sDict:', sDict)
        spikeList = sDict["spikeList"]
        doZoom = sDict["doZoom"]
        self.selectSpikeList(spikeList, doZoom=doZoom, doEmit=True)

        # mar 11
        # if spikeList == []:
        #     spikeNumber = 0
        # else:
        #     spikeNumber = spikeList[0]
        # self.selectSpike(spikeNumber, doZoom=doZoom)

    def slot_switchFile(self, ba: sanpy.bAnalysis = None, tableRowDict: dict = None):
        """Switch to a new file.

        Set self.ba to new bAnalysis object ba

        Can fail if .abf file is corrupt

        Parameters
        ----------
        tableRowDict :dict
        ba : sanpy.bAnalysis

        Returns: True/False
        """
        # logger.info(f"tableRowDict:{tableRowDict}")
        logger.info(f"ba:{ba}")

        # bAnalysis object
        self.ba = ba

        if self.ba.loadError:
            self.replotOverlays()
            fileName = self.ba.fileLoader.filename()  # tableRowDict['File']
            errStr = f'The bAnalysis file was flagged with loadError ... aborting: "{fileName}".'
            logger.error(errStr)
            self.updateStatusBar(errStr)
            return False

        # fill in detection parameters (dvdt, vm, start, stop)
        startSec = ""
        stopSec = ""
        if tableRowDict is not None:
            self.detectToolbarWidget.slot_selectFile(tableRowDict)
            self.fillInDetectionParameters(tableRowDict)  # fills in controls
            # self.updateStatusBar(f'Plotting file {path}')
            startSec = tableRowDict["Start(s)"]
            stopSec = tableRowDict["Stop(s)"]

        if startSec == "" or stopSec == "" or np.isnan(startSec) or np.isnan(stopSec):
            startSec = 0
            stopSec = self.ba.fileLoader.recordingDur

        # cancel spike selection
        self.selectSpikeList([])

        # set sweep to 0
        self.selectSweep(0, doEmit=False, doReplot=False)

        # abb implement sweep, move to function()
        # abb 20220615
        self._replot(startSec, stopSec)
        # self._replot()

        # update x/y axis labels
        yLabel = self.ba.fileLoader._sweepLabelY
        self.dacPlot.getAxis("left").setLabel("DAC")
        self.derivPlot.getAxis("left").setLabel("Derivative")
        self.vmPlotGlobal.getAxis("left").setLabel(yLabel)
        # self.vmPlotGlobal.getAxis('bottom').setLabel('Seconds')
        self.vmPlot.getAxis("left").setLabel(yLabel)
        self.vmPlot.getAxis("bottom").setLabel("Seconds")

        if sanpy.DO_KYMOGRAPH_ANALYSIS:
            if self.ba.fileLoader.isKymograph():
                self.myKymWidget.setVisible(True)
                # self.myKymWidget.slot_switchFile(ba, startSec, stopSec)
                self.vmPlot.setXLink(self.myKymWidget.kymographPlot)
                # self.myKymWidget.kymographPlot.setXLink(self.vmPlot)  # row major is different
                self.myKymWidget.slot_switchFile(ba)
            else:
                self.myKymWidget.setVisible(False)
                # self.myKymWidget.kymographPlot.setXLink(None)  # row major is different
                self.vmPlot.setXLink(None)

        #self.myKymWidget.kymographPlot.setXLink(self.vmPlot)  # row major is different    

        # set full axis
        # abb 20220615
        # self.setAxisFull()
        
        # 20221003 just link everything to vmPlot
        # self.derivPlot.setXLink(self.vmPlot)
        # self.dacPlot.setXLink(self.vmPlot)
        
        # self.myKymWidget.kymographPlot.setXLink(self.vmPlot)  # row major is different    
        # self.myKymWidget.myImageItem.setXLink(self.vmPlot)
        # self.myKymWidget.setXLink(self.vmPlot)

        return True

    def slot_dataChanged(self, columnName, value, rowDict):
        """User has edited main file table."""
        self.detectToolbarWidget.slot_dataChanged(columnName, value, rowDict)

    def slot_updateAnalysis(self, sDict : dict):
        logger.info('')
        self.replotOverlays()  # replot statistics over traces
        
        # reselect selected spikes on analysis changed
        # this is needed to refresh the symbols of the selection
        self.selectSpikeList(self._selectedSpikeList)

    def _slot_x_range_changed(self, viewbox, range_):
        """Respond to changes in x-axis

        Parameters
        ----------
        viewbox : pyqtgraph.graphicsItems.ViewBox.ViewBox.ViewBox
        range_ : (float, float)
            The current x-axis range
        Notes
        -----
        Trying to connect but not working yet

        self.vmPlot.sigXRangeChanged.connect(self._slot_x_range_changed)

        """
        # logger.info(event)
        # logger.info(f'v:{v}')
        #logger.info(f'range_:{range_}')
        
        # set glbal vm to this range
        # update rectangle in vmPlotGlobal
        start = range_[0]
        stop = range_[1]
        self.linearRegionItem2.setRegion([start, stop])

    def _replot(self, startSec : Optional[float] = None,
                stopSec : Optional[float] = None,
                userUpdate : bool = False):
        """Full replot.

        Parameters
        ----------
        startSec : float or None
        stopSec : float or None
        userUpdate : bool
            Depreciated, not used
        """
        logger.info(f"startSec:{startSec} stopSec:{stopSec} userUpdate:{userUpdate}")

        if startSec is None or stopSec is None:
            startSec, stopSec = self.getXRange()

        # remove vm/dvdt/clip items (even when abf file is corrupt)
        # if self.dvdtLines is not None:
        #    self.derivPlot.removeItem(self.dvdtLines)
        # if self.dvdtLinesFiltered is not None:
        #     self.derivPlot.removeItem(self.dvdtLinesFiltered)
        # if self.dacLines is not None:
        #     self.dacPlot.removeItem(self.dacLines)
        # was this june 4
        # if self.vmLinesFiltered is not None:
        #     self.vmPlot.removeItem(self.vmLinesFiltered)
        # if self.vmLinesFiltered2 is not None:
        #     self.vmPlotGlobal.removeItem(self.vmLinesFiltered2)
        # if self.linearRegionItem2 is not None:
        #     self.vmPlotGlobal.removeItem(self.linearRegionItem2)
        # if self.clipLines is not None:
        #    self.clipPlot.removeItem(self.clipLines)

        # update lines
        # self.dvdtLines = MultiLine(self.ba.abf.sweepX, self.ba.deriv,
        #                    self, type='dvdt')

        if self.ba is None:
            return

        # shared by all plot
        sweepX = self.ba.fileLoader.sweepX
        filteredDeriv = self.ba.fileLoader.filteredDeriv  # dec 2022, check if exists
        sweepC = self.ba.fileLoader.sweepC
        # filteredVm = self.ba.filteredVm
        sweepY = self.ba.fileLoader.sweepY

        #
        if sweepX.shape != filteredDeriv.shape:
            logger.error(f"filteredDeriv shapes do not match")

        self.derivPlot_.setData(sweepX, filteredDeriv, connect="finite")
        # self.dvdtLinesFiltered = MultiLine(
        #     sweepX,
        #     filteredDeriv,
        #     self,
        #     forcePenColor=None,
        #     type="dvdtFiltered",
        #     columnOrder=True,
        # )
        # # self.derivPlot.addItem(self.dvdtLines)
        # self.derivPlot.addItem(self.dvdtLinesFiltered)

        self.dacPlot_.setData(sweepX, sweepC, connect="finite")
        # self.dacLines = MultiLine(
        #     sweepX, sweepC, self, forcePenColor=None, type="dac", columnOrder=True
        # )
        # self.dacPlot.addItem(self.dacLines)

        # self.vmLinesFiltered = MultiLine(
        #     sweepX,
        #     sweepY,
        #     self,
        #     forcePenColor=None,
        #     type="vmFiltered",
        #     allowXAxisDrag=True,  #default is True
        #     columnOrder=True,
        # )
        # self.vmPlot.addItem(self.vmLinesFiltered)
        self.vmPlot_.setData(sweepX, sweepY, connect="finite")

        # vmPlot_ is PlotDataItem
        # logger.info(f'vmPlot.viewRange {self.vmPlot.viewRange()}')

        # april 30, 2023
        # was this jun 4
        # self.vmPlot.sigXRangeChanged.connect(self._slot_x_range_changed)

        # can't add a multi line to 2 different plots???
        # self.vmLinesFiltered2 = MultiLine(
        #     sweepX, sweepY, self, forcePenColor="b", type="vmFiltered", columnOrder=True
        # )
        # self.vmPlotGlobal.addItem(self.vmLinesFiltered2)
        self.vmPlotGlobal_.setData(sweepX, sweepY, connect="finite", pen='b')
        self.linearRegionItem2 = pg.LinearRegionItem(
            values=(0, self.ba.fileLoader.recordingDur),
            orientation=pg.LinearRegionItem.Vertical,
            brush=pg.mkBrush(150, 150, 150, 100),
            pen=pg.mkPen(None),
        )
        self.linearRegionItem2.setMovable(False)
        self.vmPlotGlobal.addItem(self.linearRegionItem2, ignorBounds=True)

        # Kymograph
        # isKymograph = self.ba.fileLoader.isKymograph()
        # self.myKymWidget.setVisible(isKymograph)
        # self.kymographPlot.hide()

        #
        # remove and re-add plot overlays
        for idx, plot in enumerate(self.myPlots):
            plotItem = self.myPlotList[idx]
            
            # moved to rpelotOverlays
            # adjust symbol size
            # plotItem.setSymbolSize(self._pgPointSize)
            # plotItem.setSymbol(_pg_symbols)

            if plot["plotOn"] == "vm":
                self.vmPlot.removeItem(plotItem)
                self.vmPlot.addItem(plotItem, ignorBounds=True)
            elif plot["plotOn"] == "vmGlobal":
                self.vmPlotGlobal.removeItem(plotItem)
                self.vmPlotGlobal.addItem(plotItem, ignorBounds=True)
            elif plot["plotOn"] == "dvdt":
                self.derivPlot.removeItem(plotItem)
                self.derivPlot.addItem(plotItem, ignorBounds=True)

        # single spike selection
        """
        self.vmPlotGlobal.removeItem(self.mySingleSpikeScatterPlot)
        self.vmPlotGlobal.addItem(self.mySingleSpikeScatterPlot)
        self.vmPlot.removeItem(self.mySingleSpikeScatterPlot)
        self.vmPlot.addItem(self.mySingleSpikeScatterPlot)
        """

        # set full axis
        # setAxisFull was causing start/stop to get over-written
        # self.setAxisFull()
        # 20221003 was this
        # self.setAxis_OnFileChange(startSec, stopSec)
        
        # was this june 4
        self.setAxisFull()
        
        # self.detectToolbarWidget.on_start_stop()
        
        # was this june 4
        # self._setAxis(start=startSec, stop=stopSec)

        #
        # critical, replot() is inherited
        self.replotOverlays()


class kymographImage(pg.ImageItem):
    def mouseClickEvent(self, event):
        # print("Click", event.pos())
        x = event.pos().x()
        y = event.pos().y()

    def mouseDragEvent(self, event):
        return

        if event.isStart():
            print("Start drag", event.pos())
        elif event.isFinish():
            print("Stop drag", event.pos())
        else:
            print("Drag", event.pos())

    def hoverEvent(self, event):
        if not event.isExit():
            # the mouse is hovering over the image; make sure no other items
            # will receive left click/drag events from here.
            event.acceptDrags(pg.QtCore.Qt.LeftButton)
            event.acceptClicks(pg.QtCore.Qt.LeftButton)


class myImageExporter(ImageExporter):
    def __init__(self, item):
        pg.exporters.ImageExporter.__init__(self, item)
        print(
            "QtGui.QImageWriter.supportedImageFormats():",
            QtGui.QImageWriter.supportedImageFormats(),
        )

    def widthChanged(self):
        sr = self.getSourceRect()
        ar = float(sr.height()) / sr.width()
        myHeight = int(self.params["width"] * ar)
        self.params.param("height").setValue(myHeight, blockSignal=self.heightChanged)

    def heightChanged(self):
        sr = self.getSourceRect()
        ar = float(sr.width()) / sr.height()
        myWidth = int(self.params["height"] * ar)
        self.params.param("width").setValue(myWidth, blockSignal=self.widthChanged)


# class MultiLine(pg.QtGui.QGraphicsPathItem):
class _old_MultiLine(QtWidgets.QGraphicsPathItem):
    def __init__(
        self,
        x,
        y,
        detectionWidget,
        type,
        forcePenColor=None,
        allowXAxisDrag=True,
        columnOrder=False,
    ):
        """Display a time-series whole-cell recording efficiently
        It does this by converting the array of points to a QPath

        see: https://stackoverflow.com/questions/17103698/plotting-large-arrays-in-pyqtgraph/17108463#17108463

        Args:
            x and y are 2D arrays of shape (Nplots, Nsamples)
            detectionWidget
            type: (dvdt, vm)
            forcePenColor
            allowXAxisDrag
            columnOrder (bool): if True then data is in columns (like multi sweep abf file)
        """

        self.exportWidgetList = []

        self.x = x
        self.y = y
        self.detectionWidget = detectionWidget
        self.myType = type
        self.allowXAxisDrag = allowXAxisDrag

        self.xDrag = None  # if true, user is dragging x-axis, otherwise y-axis
        self.xStart = None
        self.xCurrent = None
        self.linearRegionItem = None

        if len(x.shape) == 2:
            connect = np.ones(x.shape, dtype=bool)
            if columnOrder:
                connect[-1, :] = 0  # don't draw the segment between each trace
            else:
                connect[:, -1] = 0  # don't draw the segment between each trace
            self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect.flatten())
        else:
            self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect="all")
        # pg.QtGui.QGraphicsPathItem.__init__(self, self.path)
        super().__init__(self.path)

        # this is bad, without this the app becomes non responsive???
        # if width > 1.0 then this whole app STALLS
        # default theme
        # self.setPen(pg.mkPen(color='k', width=1))
        # dark theme
        if forcePenColor is not None:
            penColor = forcePenColor
        elif self.detectionWidget.myMainWindow is None:
            penColor = "k"
        else:
            if self.detectionWidget.myMainWindow.useDarkStyle:
                penColor = "w"
            else:
                penColor = "k"
        #
        width = 1
        if self.myType == "meanclip":
            penColor = "r"
            width = 3

        #
        self.setPen(pg.mkPen(color=penColor, width=width))

    def shape(self):
        # override because QGraphicsPathItem.shape is too expensive.
        # print(time.time(), 'MultiLine.shape()', pg.QtGui.QGraphicsItem.shape(self))

        # removed mar 26 2023
        # gives error in pyqtgraph-0.13.2
        # return pg.QtGui.QGraphicsItem.shape(self)

        # now this
        return super().shape()

    def boundingRect(self):
        # print(time.time(), 'MultiLine.boundingRect()', self.path.boundingRect())
        return self.path.boundingRect()

    def mouseClickEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            logger.info(f"mouseClickEvent() right click {self.myType}")
            self.contextMenuEvent(event)

    def mouseDragEvent(self, ev):
        """Default is to drag x-axis, use alt+drag for y-axis (option+drag on macOS).

        TODO: implement option+drag to select spike point from scatter

        see:
            https://gist.github.com/eyllanesc/f305119027ae3b85dfcf8a3ef8c00238
        """
        # print('MultiLine.mouseDragEvent():', type(ev), ev)

        # if we do nothing here, we recover pyqtgraph click+drag to pan
        # return
    
        # april 30, only allow this on isAlt so user can zoom into y-axis

        if ev.button() != QtCore.Qt.LeftButton:
            ev.ignore()
            return

        # modifiers = QtWidgets.QApplication.keyboardModifiers()
        # isAlt = modifiers == QtCore.Qt.AltModifier
        # alt on macOS is 'option'
        isAlt = ev.modifiers() == QtCore.Qt.AltModifier
        #logger.info(f'isAlt:{isAlt}')

        # april 30, only allow this on isAlt so user can zoom into y-axis
        if not isAlt:
            return
        
        # xDrag = not isAlt # x drag is dafault, when alt is pressed, xDrag==False

        # allowXAxisDrag is now used for both x and y
        if not self.allowXAxisDrag:
            ev.accept()  # this prevents click+drag of plot
            return

        if ev.isStart():
            self.xDrag = not isAlt
            if self.xDrag:
                self.xStart = ev.buttonDownPos()[0]
                self.linearRegionItem = pg.LinearRegionItem(
                    values=(self.xStart, 0), orientation=pg.LinearRegionItem.Vertical
                )
            else:
                # in y-drag, we need to know (vm, dvdt)
                self.xStart = ev.buttonDownPos()[1]
                self.linearRegionItem = pg.LinearRegionItem(
                    values=(0, self.xStart), orientation=pg.LinearRegionItem.Horizontal
                )
            # self.linearRegionItem.sigRegionChangeFinished.connect(self.update_x_axis)
            # add the LinearRegionItem to the parent widget (Cannot add to self as it is an item)
            self.parentWidget().addItem(self.linearRegionItem)
        elif ev.isFinish():
            if self.xDrag:
                set_xyBoth = "xAxis"
            else:
                set_xyBoth = "yAxis"
            # self.parentWidget().setXRange(self.xStart, self.xCurrent)
            self.detectionWidget.setAxis(
                self.xStart, self.xCurrent, set_xyBoth=set_xyBoth, whichPlot=self.myType
            )

            self.xDrag = None
            self.xStart = None
            self.xCurrent = None

            # 20210821, not sure ???
            # if self.myType == 'clip':
            #    if self.xDrag:
            #        self.clipPlot.setXRange(self.xStart, self.xCurrent, padding=padding)
            #    else:
            #        self.clipPlot.setYRange(self.xStart, self.xCurrent, padding=padding)
            # else:
            #    self.parentWidget().removeItem(self.linearRegionItem)
            self.parentWidget().removeItem(self.linearRegionItem)

            # was getting QGraphicsScene::removeItem: item 0x55f2844ff8e0's scene (0x0) is different from this scene (0x55f282051690)
            # self.parentWidget().removeItem(self.linearRegionItem)

            self.linearRegionItem = None

            return

        if self.xDrag:
            self.xCurrent = ev.pos()[0]
            # print('xStart:', self.xStart, 'self.xCurrent:', self.xCurrent)
            self.linearRegionItem.setRegion((self.xStart, self.xCurrent))
        else:
            self.xCurrent = ev.pos()[1]
            # print('xStart:', self.xStart, 'self.xCurrent:', self.xCurrent)
            self.linearRegionItem.setRegion((self.xStart, self.xCurrent))
        ev.accept()

    def contextMenuEvent(self, event):
        """Show popup context menu in response to right(command)+click.
        
        This is inherited from QWidget.
        """
        myType = self.myType

        """
        if myType == 'clip':
            logger.warning('No export for clips, try clicking again')
            return
        """

        contextMenu = QtWidgets.QMenu()

        showCrosshairAction = contextMenu.addAction(f"Crosshair")
        showCrosshairAction.setCheckable(True)
        showCrosshairAction.setChecked(self.detectionWidget._showCrosshair)
        
        contextMenu.addSeparator()

        exportTraceAction = contextMenu.addAction(f"Export Trace {myType}")
        contextMenu.addSeparator()

        resetAllAxisAction = contextMenu.addAction(f"Reset All Axis")
        resetYAxisAction = contextMenu.addAction(f"Reset Y-Axis")
        # openAct = contextMenu.addAction("Open")
        # quitAct = contextMenu.addAction("Quit")
        # action = contextMenu.exec_(self.mapToGlobal(event.pos()))

        # show menu
        posQPoint = QtCore.QPoint(event.screenPos().x(), event.screenPos().y())
        action = contextMenu.exec_(posQPoint)
        if action is None:
            return
        
        actionText = action.text()
        if actionText == f"Export Trace {myType}":
            #
            # See: plugins/exportTrace.py
            #

            # print('Opening Export Trace Window')

            # todo: pass xMin,xMax to constructor
            if self.myType == "vmFiltered":
                xyUnits = ("Time (sec)", "Vm (mV)")
            elif self.myType == "dvdtFiltered":
                xyUnits = ("Time (sec)", "dV/dt (mV/ms)")
            elif self.myType == "meanclip":
                xyUnits = ("Time (ms)", "Vm (mV)")
            else:
                logger.error(f'Unknown myType: "{self.myType}"')
                xyUnits = ("error time", "error y")

            path = self.detectionWidget.ba.fileLoader.filepath

            xMin, xMax = self.detectionWidget.getXRange()

            if self.myType in ["vm", "dvdt"]:
                xMargin = 2  # seconds
            else:
                xMargin = 2

            exportWidget = sanpy.interface.bExportWidget(
                self.x,
                self.y,
                xyUnits=xyUnits,
                path=path,
                xMin=xMin,
                xMax=xMax,
                xMargin=xMargin,
                type=self.myType,
                darkTheme=self.detectionWidget.useDarkStyle,
            )

            exportWidget.myCloseSignal.connect(self.slot_closeChildWindow)
            exportWidget.show()

            self.exportWidgetList.append(exportWidget)

        elif actionText == "Reset All Axis":
            # print('Reset Y-Axis', self.myType)
            self.detectionWidget.setAxisFull()

        elif actionText == "Reset Y-Axis":
            # print('Reset Y-Axis', self.myType)
            self.detectionWidget.setAxisFull_y(self.myType)

        elif actionText == 'Crosshair':
            isChecked = action.isChecked()
            #isChecked = not isChecked
            logger.info(f'{actionText} {isChecked}')
            self.detectionWidget.toggleCrosshair(isChecked)
            
        else:
            logger.warning(f"action not taken: {action}")

    def slot_closeChildWindow(self, windowPointer):
        # print('closeChildWindow()', windowPointer)
        # print('  exportWidgetList:', self.exportWidgetList)

        idx = self.exportWidgetList.index(windowPointer)
        if idx is not None:
            popedItem = self.exportWidgetList.pop(idx)
            # print('  popedItem:', popedItem)
        else:
            print(" slot_closeChildWindow() did not find", windowPointer)


class myDetectToolbarWidget2(QtWidgets.QWidget):
    # signalSelectSpike = QtCore.Signal(object, object) # spike number, doZoom

    def __init__(self, myPlots, detectionWidget: bDetectionWidget, parent=None):
        super(myDetectToolbarWidget2, self).__init__(parent)

        self.myPlots = myPlots
        self.detectionWidget = detectionWidget  # parent detection widget

        self._startSec = None
        self._stopSec = None

        self._selectedDetection = None

        self._blockSlots = False

        self._buildUI()

    def fillInDetectionParameters(self, tableRowDict):
        """Set detection widget interface (mostly QSpinBox) to match values from table
        """

        """
        print('fillInDetectionParameters()')
        print('  tableRowDict:')
        for k,v in tableRowDict.items():
            print('  ', k, ':', v, type(v))
        """

        try:
            dvdtThreshold = tableRowDict["dvdtThreshold"]
            mvThreshold = tableRowDict["mvThreshold"]
            startSeconds = tableRowDict["Start(s)"]
            stopSeconds = tableRowDict["Stop(s)"]
        except KeyError as e:
            logger.error(e)
            return
        # logger.info(f'startSeconds:{startSeconds} stopSeconds:{stopSeconds}')

        # in table we specify 'nan' but float spin box will not show that
        if math.isnan(dvdtThreshold):
            windowOptions = self.detectionWidget.getMainWindowOptions()
            dvdtThreshold = windowOptions["detect"]["detectDvDt"]

        if math.isnan(mvThreshold):
            windowOptions = self.detectionWidget.getMainWindowOptions()
            mvThreshold = windowOptions["detect"]["detectMv"]

        # print('=== fillInDetectionParameters dvdtThreshold:', dvdtThreshold)
        # print('=== fillInDetectionParameters mvThreshold:', mvThreshold)

        self.dvdtThreshold.setValue(dvdtThreshold)
        self.mvThreshold.setValue(mvThreshold)

        if math.isnan(startSeconds):
            startSeconds = 0
        if math.isnan(stopSeconds):
            # stopSeconds = self.detectionWidget.ba.sweepX[-1]
            stopSeconds = self.detectionWidget.ba.fileLoader.recordingDur

        # removed 20230419
        # self.startSeconds.setValue(startSeconds)
        # self.stopSeconds.setValue(stopSeconds)

    """
    def sweepSelectionChange(self,i):
        sweepNumber = int(self.cb.currentText())
        print('    todo: implement sweep number:', sweepNumber)
    """

    def on_detection_preset_change(self, detectionTypeStr):
        """User selected a preset detection.

        Fill in preset dv/dt and mV.
        Use this detection preset when user hits detect
        """
        logger.info(f'{detectionTypeStr}')

        # grab default (dv/dt, mv) from preset
        # detectionPreset = sanpy.bDetection.detectionPresets(detectionTypeStr)
        # detectionClass = sanpy.bDetection(detectionPreset=detectionPreset)

        self._selectedDetection = detectionTypeStr
        detectionDict = (
            self.detectionWidget.getMainWindowDetectionClass().getDetectionDict(
                self._selectedDetection
            )
        )
        dvdtThreshold = detectionDict["dvdtThreshold"]
        mvThreshold = detectionDict["mvThreshold"]
        logger.info(f"    dvdtThreshold:{dvdtThreshold} mvThreshold:{mvThreshold}")

        # set interface
        self.dvdtThreshold.setValue(dvdtThreshold)
        self.mvThreshold.setValue(mvThreshold)

    def on_sweep_change(self, sweepNumber):
        """
        Args:
            sweepNumber (str): The current selected item, from ('All', 0, 1, 2, ...)
        """
        # logger.debug(f'sweepNumber:"{sweepNumber}" {type(sweepNumber)}')
        if sweepNumber == "":
            # we receive this as we rebuild xxx on switching file
            # logger.error('Got empty sweep -- ABORTING')
            return
        logger.info(f"Calling selectSweep() {sweepNumber}")
        self.detectionWidget.selectSweep(sweepNumber)

    def on_sweep_change_2(self, prevNext: str):
        if self.detectionWidget.ba is None:
            return

        if prevNext == "previous":
            inc = -1
        else:
            inc = +1
        newSweep = self.detectionWidget.sweepNumber
        if newSweep is None:
            return
        else:
            newSweep += inc

        if newSweep < 0 or newSweep > self.detectionWidget.ba.fileLoader.numSweeps - 1:
            return

        self.detectionWidget.slot_selectSweep(newSweep)
        # self.detectionWidget.selectSweep(newSweep)

        # update combobox
        # self.sweepComboBox.setCurrentIndex(newSweep+1)

    def _old_on_start_stop(self):
        """Respond to user changing start/stop seconds
        """
        start = self.startSeconds.value()
        stop = self.stopSeconds.value()

        if (start != self._startSec) or (stop != self._stopSec):
            self._startSec = start
            self._stopSec = stop

            logger.info(f"start:{start}, stop:{stop}")
            self.detectionWidget.setAxis(start, stop)

    def on_plot_every(self):
        logger.info("TODO: update plots with plot every.")

    def _on_button_click(self, name):
        """User clicked a button.
        """
        logger.info(f'User clicked button "{name}"')

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        isShift = modifiers == QtCore.Qt.ShiftModifier

        if name == "Detect dV/dt":
            detectionPreset = self.detectionPresets.currentText()

            dvdtThreshold = self.dvdtThreshold.value()
            mvThreshold = self.mvThreshold.value()

            if dvdtThreshold == 0:
                # 0 is special value shown as 'None'
                str = "Please set a threshold greater than 0"
                self.detectionWidget.updateStatusBar(str)
                return
            
            # removed 20230419
            # startSec = self.startSeconds.value()
            # stopSec = self.stopSeconds.value()
            startSec = self._startSec
            stopSec = self._stopSec

            #
            detectionType = sanpy.bDetection.detectionTypes.dvdt
            self.detectionWidget.detect(
                detectionPreset,
                detectionType,
                dvdtThreshold,
                mvThreshold,
                startSec,
                stopSec,
            )

        elif name == "Detect mV":
            detectionPreset = self.detectionPresets.currentText()

            dvdtThreshold = self.dvdtThreshold.value()
            mvThreshold = self.mvThreshold.value()
            # print('    mvThreshold:', mvThreshold)
            # passing dvdtThreshold=None we will detect suing mvThreshold

            # was this, switching to detection class
            # dvdtThreshold = None

            # startSec = self.startSeconds.value()
            # stopSec = self.stopSeconds.value()
            startSec = self._startSec
            stopSec = self._stopSec

            #
            detectionType = sanpy.bDetection.detectionTypes.mv
            self.detectionWidget.detect(
                detectionPreset,
                detectionType,
                dvdtThreshold,
                mvThreshold,
                startSec,
                stopSec,
            )

        elif name == "[]":
            # Reset Axes
            self.detectionWidget.setAxisFull()

        elif name == "Export Spike Report":
            # self.detectionWidget.save(alsoSaveTxt=isShift)
            self.detectionWidget.save(saveCsv=True)

        # next/previous sweep
        elif name == "<":
            self.on_sweep_change_2("previous")
        elif name == ">":
            self.on_sweep_change_2("next")

        elif name == "Go":
            spikeNumber = self.spikeNumber.value()
            doZoom = isShift
            self.detectionWidget.selectSpike(spikeNumber, doZoom, doEmit=True)

        elif name == "<<":
            spikeNumber = self.spikeNumber.value()
            spikeNumber -= 1
            if spikeNumber < 0:
                spikeNumber = 0
            doZoom = isShift
            self.detectionWidget.selectSpike(spikeNumber, doZoom, doEmit=True)

        elif name == ">>":
            if self.detectionWidget.ba is None:
                return
            spikeNumber = self.spikeNumber.value()
            spikeNumber += 1
            if spikeNumber > self.detectionWidget.ba.numSpikes - 1:
                spikeNumber = self.detectionWidget.ba.numSpikes - 1
            doZoom = isShift
            self.detectionWidget.selectSpike(spikeNumber, doZoom, doEmit=True)

        else:
            logger.warning(f'Did not understand button: "{name}"')

    def on_check_click(self, checkbox, idx):
        isChecked = checkbox.isChecked()
        # print('on_check_click() text:', checkbox.text(), 'isChecked:', isChecked, 'idx:', idx)
        self.detectionWidget.toggleInterface(idx, isChecked)

    def _old_on_crosshair_clicked(self, value):
        # print('on_crosshair_clicked() value:', value)
        onOff = value == 2
        self.detectionWidget.toggleCrosshair(onOff)

    def toggleInterface(self, panelName: str, onoff: bool):
        """Toggle interface panels on/off."""

        if panelName == "Detection":
            if onoff:
                self.detectionGroupBox.show()
            else:
                self.detectionGroupBox.hide()
        elif panelName == "Display":
            if onoff:
                self.displayGroupBox.show()
            else:
                self.displayGroupBox.hide()
        # mar 11
        elif panelName == "Set Spikes":
            if onoff:
                self.setSpikeGroupBox.show()
            else:
                self.setSpikeGroupBox.hide()
        elif panelName == "Set Meta Data":
            if onoff:
                self.setMetaDataGroupBox.show()
            else:
                self.setMetaDataGroupBox.hide()
        elif panelName == "Plot Options":
            if onoff:
                self.plotGroupBox.show()
            else:
                self.plotGroupBox.hide()

        else:
            logger.warning(f'did not understand panelName "{panelName}"')

    def _buildUI(self):
        """
        Notes
        -----
        Using setFixedWidth()
        """
        myPath = os.path.dirname(os.path.abspath(__file__))

        windowOptions = self.detectionWidget.getMainWindowOptions()
        detectDvDt = 20
        detectMv = -20
        showGlobalVm = True
        showDvDt = True
        showDAC = True
        if windowOptions is not None:
            detectDvDt = windowOptions["detect"]["detectDvDt"]
            detectMv = windowOptions["detect"]["detectMv"]

            showDvDt = windowOptions["rawDataPanels"]["Derivative"]
            showDAC = windowOptions["rawDataPanels"]["DAC"]
            showGlobalVm = windowOptions["rawDataPanels"]["Full Recording"]

        # April 15, 2023, removed when adding horizontal splitter
        #self.setFixedWidth(280)
        self.setFixedWidth(280)

        # why do I need self here?
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.setAlignment(QtCore.Qt.AlignTop)

        self.mainLayout.setContentsMargins(0,0,0,0)

        # Show selected file
        # self.mySelectedFileLabel = QtWidgets.QLabel("None")
        # self.mySelectedFileLabel.setContentsMargins(0,0,0,0)
        # self.mainLayout.addWidget(self.mySelectedFileLabel)

        #
        # detection parameters group
        self.detectionGroupBox = QtWidgets.QGroupBox("Detection")

        # breeze
        # detectionGroupBox.setStyleSheet(myStyleSheet)

        # detectionGroupBox.setAlignment(QtCore.Qt.AlignTop)

        detectionGridLayout = QtWidgets.QGridLayout()
        # detectionGridLayout.setAlignment(QtCore.Qt.AlignTop)

        row = 0
        rowSpan = 1
        columnSpan = 2

        aComboLabel = QtWidgets.QLabel("Presets")

        # get list of detection presets
        # detectionTypes = sanpy.bDetection.getDetectionPresetList()
        detectionClass = self.detectionWidget.getMainWindowDetectionClass()
        detectionTypes = detectionClass.getDetectionPresetList()

        self._selectedDetection = detectionTypes[0]  # set to the first detection type

        self.detectionPresets = QtWidgets.QComboBox()
        for detectionType in detectionTypes:
            self.detectionPresets.addItem(detectionType)
        self.detectionPresets.currentTextChanged.connect(
            self.on_detection_preset_change
        )

        columnSpan = 1
        detectionGridLayout.addWidget(aComboLabel, row, 0, rowSpan, columnSpan)
        columnSpan = 3
        detectionGridLayout.addWidget(
            self.detectionPresets, row, 1, rowSpan, columnSpan
        )
        row += 1

        #
        buttonName = "Detect dV/dt"
        button = QtWidgets.QPushButton(buttonName)
        button.setToolTip("Detect spikes using dV/dt threshold.")
        button.clicked.connect(partial(self._on_button_click, buttonName))

        # row = 0
        rowSpan = 1
        columnSpan = 2
        detectionGridLayout.addWidget(button, row, 0, rowSpan, columnSpan)

        self.dvdtThreshold = QtWidgets.QDoubleSpinBox()
        self.dvdtThreshold.setToolTip("dV/dt threshold.")
        self.dvdtThreshold.setDecimals(3)
        self.dvdtThreshold.setMinimum(0)
        self.dvdtThreshold.setMaximum(+1e6)
        self.dvdtThreshold.setValue(detectDvDt)
        self.dvdtThreshold.setSpecialValueText("None")
        # self.dvdtThreshold.setValue(np.nan)
        detectionGridLayout.addWidget(self.dvdtThreshold, row, 2, rowSpan, columnSpan)

        row += 1
        rowSpan = 1
        columnSpan = 2
        buttonName = "Detect mV"
        button = QtWidgets.QPushButton(buttonName)
        button.setToolTip("Detect spikes using mV threshold.")
        button.clicked.connect(partial(self._on_button_click, buttonName))
        detectionGridLayout.addWidget(button, row, 0, rowSpan, columnSpan)

        # Vm Threshold (mV)
        # mvThresholdLabel = QtWidgets.QLabel('Vm Threshold (mV)')
        # self.addWidget(mvThresholdLabel, row, 1)

        # row += 1
        self.mvThreshold = QtWidgets.QDoubleSpinBox()
        self.mvThreshold.setToolTip("mV threshold.")
        self.mvThreshold.setMinimum(-1e6)
        self.mvThreshold.setMaximum(+1e6)
        self.mvThreshold.setValue(detectMv)
        detectionGridLayout.addWidget(self.mvThreshold, row, 2, rowSpan, columnSpan)

        # removed 20230419
        # decided to not show start/stop seconds ???
        #

        self._startSeconds = 0
        self._stopSeconds = 0

        # instead, we need a member variable to keep track of this
        # see
        # self._startSec and self._stopSec
        
        # row += 1

        # startSeconds = QtWidgets.QLabel("From (s)")
        # detectionGridLayout.addWidget(startSeconds, row, 0)

        # self.startSeconds = QtWidgets.QDoubleSpinBox()
        # self.startSeconds.setMinimum(-1e6)
        # self.startSeconds.setMaximum(+1e6)
        # self.startSeconds.setKeyboardTracking(False)
        # self.startSeconds.setValue(0)
        # self.startSeconds.editingFinished.connect(self._on_start_stop)
        # detectionGridLayout.addWidget(self.startSeconds, row, 1)

        # stopSeconds = QtWidgets.QLabel("To (s)")
        # detectionGridLayout.addWidget(stopSeconds, row, 2)

        # self.stopSeconds = QtWidgets.QDoubleSpinBox()
        # self.stopSeconds.setMinimum(-1e6)
        # self.stopSeconds.setMaximum(+1e6)
        # self.stopSeconds.setKeyboardTracking(False)
        # self.stopSeconds.setValue(0)
        # # self.stopSeconds.valueChanged.connect(self.on_start_stop)
        # self.stopSeconds.editingFinished.connect(self._on_start_stop)
        # detectionGridLayout.addWidget(self.stopSeconds, row, 3)

        # removed april 15, 2023 to conserve space
        # row += 1
        # tmpHLayout = QtWidgets.QHBoxLayout()

        # self.numSpikesLabel = QtWidgets.QLabel("Spikes: None")
        # tmpHLayout.addWidget(self.numSpikesLabel)

        # self.spikeFreqLabel = QtWidgets.QLabel("Freq: None")
        # tmpHLayout.addWidget(self.spikeFreqLabel)

        # self.numErrorsLabel = QtWidgets.QLabel("Errors: None")
        # tmpHLayout.addWidget(self.numErrorsLabel)
        # col = 0
        # rowSpan = 1
        # colSpan = 4
        # detectionGridLayout.addLayout(tmpHLayout, row, col, rowSpan, colSpan)

        row += 1
        buttonName = "Export Spike Report"
        button = QtWidgets.QPushButton(buttonName)
        button.setToolTip("Save Detected Spikes to csv file")
        # button.setStyleSheet("background-color: green")
        button.clicked.connect(partial(self._on_button_click, buttonName))
        rowSpan = 1
        colSpan = 4
        detectionGridLayout.addWidget(button, row, 0, rowSpan, colSpan)

        # finalize
        self.detectionGroupBox.setLayout(detectionGridLayout)
        self.mainLayout.addWidget(self.detectionGroupBox)

        #
        # display group
        self.displayGroupBox = QtWidgets.QGroupBox("Display")

        displayGridLayout = QtWidgets.QGridLayout()

        row = 0

        # channel, we only support one channel
        # _tmpChannelLabel = QtWidgets.QLabel('Channel')
        # _channelComboBox = QtWidgets.QComboBox()
        # # add channels from abf
        # _fakeChannels = ['1', '2', '3', 'bizarre']
        # for channel in _fakeChannels:
        #     _channelComboBox.addItem(channel)

        # sweeps
        tmpSweepLabel = QtWidgets.QLabel("Sweep")
        buttonName = "<"
        self.previousSweepButton = QtWidgets.QPushButton(buttonName)
        self.previousSweepButton.setToolTip("Previous Sweep")
        self.previousSweepButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        buttonName = ">"
        self.nextSweepButton = QtWidgets.QPushButton(buttonName)
        self.nextSweepButton.setToolTip("Next Sweep")
        self.nextSweepButton.clicked.connect(partial(self._on_button_click, buttonName))

        self.sweepComboBox = QtWidgets.QComboBox()
        self.sweepComboBox.setToolTip("Select Sweep")
        self.sweepComboBox.currentTextChanged.connect(self.on_sweep_change)
        # will be set in self.slot_selectFile()
        # for sweep in range(self.detectionWidget.ba.numSweeps):
        #    self.sweepComboBox.addItem(str(sweep))
        hSweepLayout = QtWidgets.QHBoxLayout()

        # hSweepLayout.addWidget(_tmpChannelLabel)
        # hSweepLayout.addWidget(_channelComboBox)

        hSweepLayout.addWidget(tmpSweepLabel)
        hSweepLayout.addWidget(self.previousSweepButton)
        hSweepLayout.addWidget(self.sweepComboBox)
        hSweepLayout.addWidget(self.nextSweepButton)
        tmpRowSpan = 1
        tmpColSpan = 2
        displayGridLayout.addLayout(hSweepLayout, row, 0, tmpRowSpan, tmpColSpan)
        # displayGridLayout.addWidget(tmpSweepLabel, row, 0, tmpRowSpan, tmpColSpan)
        # displayGridLayout.addWidget(previousSweepButton, row, 1, tmpRowSpan, tmpColSpan)
        # displayGridLayout.addWidget(self.sweepComboBox, row, 2, tmpRowSpan, tmpColSpan)
        # displayGridLayout.addWidget(nextSweepButton, row, 3, tmpRowSpan, tmpColSpan)

        # plot every x th pnts, value of 10 would plot every 10th point
        """
        row += 1
        tmpPlotEveryLabel = QtWidgets.QLabel('Plot Every')

        self.plotEverySpinBox = QtWidgets.QSpinBox()
        self.plotEverySpinBox.setMinimum(1)
        self.plotEverySpinBox.setMaximum(20)
        self.plotEverySpinBox.setKeyboardTracking(False)
        self.plotEverySpinBox.setValue(1)
        #self.stopSeconds.valueChanged.connect(self.on_start_stop)
        self.plotEverySpinBox.editingFinished.connect(self.on_plot_every)

        displayGridLayout.addWidget(tmpPlotEveryLabel, row, 0, tmpRowSpan, tmpColSpan)
        displayGridLayout.addWidget(self.plotEverySpinBox, row, 1, tmpRowSpan, tmpColSpan)
        """

        # removed in favor of showing tooltip on mouse move
        # row += 1
        # self.crossHairCheckBox = QtWidgets.QCheckBox("Crosshair")
        # self.crossHairCheckBox.setChecked(False)
        # self.crossHairCheckBox.stateChanged.connect(self.on_crosshair_clicked)
        # tmpRowSpan = 1
        # tmpColSpan = 1
        # displayGridLayout.addWidget(
        #     self.crossHairCheckBox, row, 0, tmpRowSpan, tmpColSpan
        # )

        # # x/y coordinates of mouse in each of derivPlot, vmPlot, clipPlot)
        # self.mousePositionLabel = QtWidgets.QLabel("x:None\ty:None")
        # displayGridLayout.addWidget(
        #     self.mousePositionLabel, row, 1, tmpRowSpan, tmpColSpan
        # )

        hBoxSpikeBrowser = self._buildSpikeBrowser()  # includes (Spike, Go, <<, >>, [])
        row += 1
        rowSpan = 1
        columnSpan = 2
        displayGridLayout.addLayout(hBoxSpikeBrowser, row, 0, rowSpan, columnSpan)

        # finalize
        self.displayGroupBox.setLayout(displayGridLayout)
        self.mainLayout.addWidget(self.displayGroupBox)

        #
        # mar 11 set spike group box
        #
        # set spike group
        self.setSpikeGroupBox = QtWidgets.QGroupBox("Set Spikes")
        self.setContentsMargins(0,0,0,0)
        setSpikeLayout = QtWidgets.QHBoxLayout()
        setSpikeLayout.setContentsMargins(0,0,0,0)

        # mar 11, created a setSpikestat plugin
        setSpikeStatWidget = sanpy.interface.plugins.SetSpikeStat(
            ba=self.detectionWidget.ba,
            bPlugin=self.detectionWidget.myMainWindow.myPlugins,
        )

        # signalSetSpikeStat is now in sanpyPlugin base class
        # setSpikeStatWidget.signalSetSpikeStat.connect(
        #     self.detectionWidget.slot_setSpikeStat
        # )

        setSpikeLayout.addWidget(setSpikeStatWidget)

        self.setSpikeGroupBox.setLayout(setSpikeLayout)
        self.mainLayout.addWidget(self.setSpikeGroupBox)

        #
        # SetMetaData group
        self.setMetaDataGroupBox = QtWidgets.QGroupBox("Set Meta Data")
        self.setContentsMargins(0,0,0,0)
        setMetaDataLayout = QtWidgets.QHBoxLayout()
        setMetaDataLayout.setContentsMargins(0,0,0,0)

        # mar 11, created a setMetaData stat plugin
        setMetaDataWidget = sanpy.interface.plugins.SetMetaData(
            ba=self.detectionWidget.ba,
            bPlugin=self.detectionWidget.myMainWindow.myPlugins,
        )

        # signalsetMetaData is now in sanpyPlugin base class
        # setMetaDataWidget.signalsetMetaData.connect(
        #     self.detectionWidget.slot_setMetaData
        # )

        setMetaDataLayout.addWidget(setMetaDataWidget)

        self.setMetaDataGroupBox.setLayout(setMetaDataLayout)
        self.mainLayout.addWidget(self.setMetaDataGroupBox)

        #
        # plots  group
        self.plotGroupBox = QtWidgets.QGroupBox("Plot Options")
        # self.plotGroupBox.setContentsMargins(0,0,0,0)

        plotGridLayout = QtWidgets.QGridLayout()
        plotGridLayout.setContentsMargins(4,4,0,0)

        row = 0

        # add widgets
        # a number of stats that will get overlaid on dv/dt and Vm
        # row += 1
        row += 1
        col = 0
        for idx, plot in enumerate(self.myPlots):
            # print('humanName:', plot['humanName'])
            humanName = plot["humanName"]
            isChecked = plot["plotIsOn"]
            styleColor = plot["styleColor"]
            checkbox = QtWidgets.QCheckBox(humanName)
            checkbox.setChecked(isChecked)
            # checkbox.setStyleSheet(styleColor) # looks really ugly
            # checkbox.stateChanged.connect(lambda:self.on_check_click(checkbox))
            checkbox.stateChanged.connect(partial(self.on_check_click, checkbox, idx))
            # append
            plotGridLayout.addWidget(checkbox, row, col)
            # increment
            col += 1
            if col == 2:  # we only have col 0/1, nx2 grid
                col = 0
                row += 1

        """
        row = 0
        col += 1
        checkbox = QtWidgets.QCheckBox('Clips')
        checkbox.setChecked(showClips)
        checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Clips'))
        plotGridLayout.addWidget(checkbox, row, col)
        """

        """
        row = 0
        col += 1
        checkbox = QtWidgets.QCheckBox('Scatter')
        checkbox.setChecked(showScatter)
        checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Scatter'))
        plotGridLayout.addWidget(checkbox, row, col)
        """

        """
        row = 0
        col += 1
        checkbox = QtWidgets.QCheckBox('Errors')
        checkbox.setChecked(showErrors)
        checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Errors'))
        plotGridLayout.addWidget(checkbox, row, col)
        """

        # finalize
        self.plotGroupBox.setLayout(plotGridLayout)
        self.mainLayout.addWidget(self.plotGroupBox)

        # finalize
        self.setLayout(self.mainLayout)

    def _on_spike_number(self, spikeNumber):
        """Respond to user setting spike number.
        """
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        isShift = modifiers == QtCore.Qt.ShiftModifier

        self.detectionWidget.selectSpike(spikeNumber, isShift, doEmit=True)

        # spikeNumber = self.spikeNumber.value()
        # doZoom = isShift
        # self.detectionWidget.selectSpike(spikeNumber, doZoom, doEmit=True)

    def _buildSpikeBrowser(self):
        """Build interface to go to spike number, previous <<, and next >>"""
        hBoxSpikeBrowser = QtWidgets.QHBoxLayout()

        # aLabel = QtWidgets.QLabel('Spike')
        # hBoxSpikeBrowser.addWidget(aLabel)

        # absolute spike number
        aLabel = QtWidgets.QLabel('Spike')
        hBoxSpikeBrowser.addWidget(aLabel)

        buttonName = "<<"
        button = QtWidgets.QPushButton(buttonName)
        button.setToolTip("Previous Spike")
        button.clicked.connect(partial(self._on_button_click, buttonName))
        hBoxSpikeBrowser.addWidget(button)

        self.spikeNumber = QtWidgets.QSpinBox()
        self.spikeNumber.setToolTip("Go To Spike")
        self.spikeNumber.setMinimum(0)
        self.spikeNumber.setMaximum(2**16)
        self.spikeNumber.setKeyboardTracking(False)
        self.spikeNumber.setValue(0)
        self.spikeNumber.valueChanged.connect(self._on_spike_number)
        # self.spikeNumber.editingFinished.connect(self.on_spike_number)
        # self.spikeNumber.setKeyboardTracking(False)
        hBoxSpikeBrowser.addWidget(self.spikeNumber)

        # 20230419 removing Go, <<, >>
        # condense everything into self.spikeNumber QtWidgets.QSpinBox
        
        # buttonName = "Go"
        # button = QtWidgets.QPushButton(buttonName)
        # button.setToolTip("Go To Spike Number")
        # button.clicked.connect(partial(self.on_button_click, buttonName))
        # hBoxSpikeBrowser.addWidget(button)

        buttonName = ">>"
        button = QtWidgets.QPushButton(buttonName)
        button.setToolTip("Next Spike")
        button.clicked.connect(partial(self._on_button_click, buttonName))
        hBoxSpikeBrowser.addWidget(button)

        buttonName = "[]"
        button = QtWidgets.QPushButton(buttonName)
        button.setToolTip("Display Full Recording")
        button.clicked.connect(partial(self._on_button_click, buttonName))
        hBoxSpikeBrowser.addWidget(button)

        return hBoxSpikeBrowser

    def setMousePositionLabel(self, x, y):
        if x is not None:
            x = round(x, 4)  # 4 to get 10kHz precision, 0.0001
        if y is not None:
            y = round(y, 2)
        labelStr = f"x:{x}   y:{y}"
        self.mousePositionLabel.setText(labelStr)
        self.mousePositionLabel.repaint()

    # def slot_setSpikeStat(self, setDict : dict):
    #     """Respond to changes from setSpikeStack plugin.

    #     Notes
    #     -----
    #     setSpikeStatEvent = {}
    #     setSpikeStatEvent['spikeList'] = self.getSelectedSpikes()
    #     setSpikeStatEvent['colStr'] = colStr
    #     setSpikeStatEvent['value'] = value
    #     """
    #     logger.info(setDict)
    #     self.detectionWidget.slot_setSpikeStat(setDict)

    def slot_selectSweep(self, sweep: int):
        """Fake slot, not ising in emit/connect."""
        
        # logger.info(f'myDetectionToolbarWidget slot_selectSweep:{sweep}')

        # +1 is for when we start combo box with 'All'
        # self.sweepComboBox.setCurrentIndex(sweep + 1)
        self.sweepComboBox.setCurrentIndex(sweep)

        # self.spikeNumber.setMaximum(+1e6)
        # self.spikeNumber.setValue(0)

    def slot_selectSpike(self, sDict):
        logger.info(f"detectiontoolbar widget: sDict:{sDict}")
        spikeNumber = sDict["spikeNumber"]
        # don't respond to a list of spikes
        if isinstance(spikeNumber, list):
            return
        # arbitrarily chosing spike 0 when no spike selection
        # spin boxes can not have 'no value'
        if spikeNumber is None:
            spikeNumber = 0

        # convert absolute to sweep
        # sweepSpike = self.detectionWidget.ba.getSweepSpikeFromAbsolute(spikeNumber, self.detectionWidget.sweepNumber)

        """
        print('    !!!! self.detectionWidget.sweepNumber:', self.detectionWidget.sweepNumber)
        print('    !!!! spikeNumber:', spikeNumber)
        print('    !!!! sweepSpike:', sweepSpike)
        """

        # need to blockSignal or else this emits to callback
        self.spikeNumber.blockSignals(True)
        self.spikeNumber.setValue(spikeNumber)
        self.spikeNumber.blockSignals(False)

        self.spikeNumber.update()

    def slot_selectSpikeList(self, sDict):
        logger.warning(f"mar 1, added and converting to select 1st spike")
        # print('detectionWidget.slotSelectSpike() sDict:', sDict)
        spikeList = sDict["spikeList"]
        doZoom = sDict["doZoom"]

        # mar 11, detection toolbar does not select multiple spikes
        # self.selectSpikeList(spikeList, doZoom=doZoom)

        # mar 11
        if spikeList == []:
            spikeNumber = 0
        else:
            spikeNumber = spikeList[0]
        sDict = {"spikeNumber": spikeNumber}
        # self.selectSpike(spikeNumber, doZoom=doZoom)
        self.slot_selectSpike(sDict)

    def slot_selectFile(self, rowDict):
        file = rowDict["File"]
        
        #self.mySelectedFileLabel.setText(file)

        # handled in fill in detection parameters
        # set start(s) stop(s)
        """
        startSec = rowDict['Start(s)']
        stopSec = rowDict['Stop(s)']
        logger.info(f'setting startSec:"{stopSec}" {type(startSec)}')
        logger.info(f'setting stopSec:"{stopSec}" {type(stopSec)}')
        if isinstance(startSec, float):
            self.startSeconds.setValue(startSec)
        if isinstance(stopSec, float):
            self.stopSeconds.setValue(stopSec)
        """

        # block signals as we update
        self.sweepComboBox.blockSignals(True)
        #

        # populate sweep combo box
        self.sweepComboBox.clear()
        # self.sweepComboBox.addItem('All')
        for sweep in range(self.detectionWidget.ba.fileLoader.numSweeps):
            self.sweepComboBox.addItem(str(sweep))
        # always select sweep 0

        # 1 was for when we had 'All'
        self.sweepComboBox.setCurrentIndex(0)

        # if self.detectionWidget.ba.numSweeps == 1:
        #    # select sweep 0
        #    self.sweepComboBox.setCurrentIndex(1)

        # turn off sweep combo box if just one sweep
        enableSweepButtons = self.detectionWidget.ba.fileLoader.numSweeps > 1
        self.sweepComboBox.setEnabled(enableSweepButtons)
        self.previousSweepButton.setEnabled(enableSweepButtons)
        self.nextSweepButton.setEnabled(enableSweepButtons)

        #
        self.sweepComboBox.blockSignals(False)
        #

        # TODO: Fix this, we need to set this when user performs new analysis
        # self.spikeNumber.setMaximum(self.detectionWidget.ba.numSpikes - 1)

        self.spikeNumber.blockSignals(True)
        self.spikeNumber.setValue(0)
        self.spikeNumber.blockSignals(False)

    def slot_dataChanged(self, columnName, value, rowDict):
        """User has edited main file table.

        Update detection widget for columns (Start(s), Stop(s), dvdtThreshold, mvThreshold)
        """
        logger.info(f"{columnName} {value} {type(value)}")

        # for k,v in rowDict.items():
        #    print(f'  {k}:"{v}" {type(v)}')

        if columnName is not None:
            # user has made a change in one cell
            if columnName == "dvdtThreshold":
                if value is None or math.isnan(value):
                    value = -1
                self.dvdtThreshold.setValue(value)
            elif columnName == "mvThreshold":
                self.mvThreshold.setValue(value)
            # removed 20230419
            # elif columnName == "Start(s)" and not math.isnan(value):
            #     self.startSeconds.setValue(value)
            # elif columnName == "Stop(s)" and not math.isnan(value):
            #     self.stopSeconds.setValue(value)
        else:
            # entire row has updated
            dvdtThreshold = rowDict["dvdtThreshold"]
            # I really need to make 'no value' np.nan
            if dvdtThreshold is None or math.isnan(dvdtThreshold):
                dvdtThreshold = 0  # 0 corresponds to 'None'
            self.dvdtThreshold.setValue(dvdtThreshold)
            mvThreshold = rowDict["mvThreshold"]
            self.mvThreshold.setValue(mvThreshold)
            
            # removed 20230419
            # startSeconds = rowDict["Start(s)"]
            # if not math.isnan(startSeconds):
            #     self.startSeconds.setValue(startSeconds)
            # stopSeconds = rowDict["Stop(s)"]
            # if not math.isnan(stopSeconds):
            #     self.stopSeconds.setValue(stopSeconds)


if __name__ == "__main__":
    # load a bAnalysis file

    # abfFile = '/Users/cudmore/Sites/bAnalysis/data/19221021.abf'
    # abfFile = '/Users/cudmore/Sites/bAnalysis/data/19114001.abf'
    path = "/media/cudmore/data/Laura-data/manuscript-data/2020_06_23_0006.abf"
    path = "../data/19114001.abf"
    path = "/media/cudmore/data/rabbit-ca-transient/Control/220110n_0003.tif.frames/220110n_0003.tif"

    ba = sanpy.bAnalysis(path)

    app = QtWidgets.QApplication(sys.argv)
    w = bDetectionWidget()
    w.slot_switchFile(ba=ba)

    detectionType = sanpy.bDetection.detectionTypes.mv
    dvdtThreshold = 10
    mvThreshold = 1000  # -20
    # w.detect(detectionType, dvdtThreshold, mvThreshold)

    w.show()

    sys.exit(app.exec_())
