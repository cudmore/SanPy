# Author: Robert H Cudmore
# Date: 20190717

from email.headerregistry import HeaderRegistry
import os, sys, math
#import inspect # to print call stack
from functools import partial
#import this

import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter

import sanpy
import sanpy.bDetection

import sanpy.interface.bKymograph

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class bDetectionWidget(QtWidgets.QWidget):
    signalSelectSpike = QtCore.pyqtSignal(object) # spike number, doZoom
    signalSelectSpikeList = QtCore.pyqtSignal(object) # spike number, doZoom
    signalDetect = QtCore.pyqtSignal(object)  # ba
    signalSelectSweep = QtCore.pyqtSignal(object, object)  # (bAnalysis, sweepNumber)
    #signalUpdateKymographROI = QtCore.pyqtSignal([])  # list of [left, top, right, bottom] in image pixels

    def __init__(self, ba=None, mainWindow=None, parent=None):
        """
        ba: bAnalysis object
        """

        super(bDetectionWidget, self).__init__(parent)

        self.ba = ba
        self.myMainWindow = mainWindow

        self.mySetTheme()

        #self._sweepNumber = None  # 'All'

        self.dvdtLines = None
        self.dvdtLinesFiltered = None
        self.dacLines = None
        self.vmLines = None
        self.vmLinesFiltered = None
        self.vmLinesFiltered2 = None
        self.linearRegionItem2 = None  # rectangle over global Vm
        self.clipLines = None
        self.meanClipLine = None

        self.myPlotList = []

        # a list of possible x/y plots (overlay over dvdt and Vm)
        # order here determines order in interface
        self.myPlots = [
            {
                'humanName': 'Global Threshold (mV)',
                'x': 'thresholdSec',
                'y': 'thresholdVal',
                'convertx_tosec': False,  # some stats are in points, we need to convert to seconds
                'color': 'r',
                'styleColor': 'color: red',
                'symbol': 'o',
                'plotOn': 'vmGlobal', # which plot to overlay (vm, dvdt)
                'plotIsOn': True,
            },
            {
                'humanName': 'Threshold (mV)',
                'x': 'thresholdSec',
                'y': 'thresholdVal',
                'convertx_tosec': False,  # some stats are in points, we need to convert to seconds
                'color': 'r',
                'styleColor': 'color: red',
                'symbol': 'o',
                'plotOn': 'vm', # which plot to overlay (vm, dvdt)
                'plotIsOn': True,
            },
            {
                'humanName': 'Threshold (dV/dt)',
                'x': 'thresholdSec',
                'y': 'thresholdVal_dvdt',
                'convertx_tosec': False,  # some stats are in points, we need to convert to seconds
                'color': 'r',
                'styleColor': 'color: red',
                'symbol': 'o',
                'plotOn': 'dvdt', # which plot to overlay (vm, dvdt)
                'plotIsOn': True,
            },
            {
                'humanName': 'AP Peak (mV)',
                'x': 'peakSec',
                'y': 'peakVal',
                'convertx_tosec': False,
                'color': 'g',
                'styleColor': 'color: green',
                'symbol': 'o',
                'plotOn': 'vm',
                'plotIsOn': True,
            },
            {
                'humanName': 'Half-Widths',
                'x': None,
                'y': None,
                'convertx_tosec': True,
                'color': 'y',
                'styleColor': 'color: yellow',
                'symbol': 'o',
                'plotOn': 'vm',
                'plotIsOn': False,
            },
            {
                'humanName': 'Epoch Lines',
                'x': None,
                'y': None,
                'convertx_tosec': True,
                'color': 'gray',
                'styleColor': 'color: gray',
                'symbol': 'o',
                'plotOn': 'vm',
                'plotIsOn': True,
            },
            {
                'humanName': 'Pre AP Min (mV)',
                'x': 'preMinPnt',
                'y': 'preMinVal',
                'convertx_tosec': True,
                'color': 'y',
                'styleColor': 'color: green',
                'symbol': 'o',
                'plotOn': 'vm',
                'plotIsOn': False,
            },
            #{
            #    'humanName': 'Post AP Min (mV)',
            #    'x': 'postMinPnt',
            #    'y': 'postMinVal',
            #    'convertx_tosec': True,
            #    'color': 'b',
            #    'styleColor': 'color: blue',
            #    'symbol': 'o',
            #    'plotOn': 'vm',
            #    'plotIsOn': False,
            #},
            {
                'humanName': 'EDD',
                'x': None,
                'y': None,
                'convertx_tosec': True,
                'color': 'm',
                'styleColor': 'color: megenta',
                'symbol': 'o',
                'plotOn': 'vm',
                'plotIsOn': False,
            },
            {
                'humanName': 'EDD Rate',
                'x': None,
                'y': None,
                'convertx_tosec': False,
                'color': 'm',
                'styleColor': 'color: megenta',
                'symbol': '--',
                'plotOn': 'vm',
                'plotIsOn': False,
            },
        ]

        # for kymograph
        #self.myImageItem = None  # kymographImage
        #self.myLineRoi = None

        self.buildUI()

        windowOptions = self.getMainWindowOptions()
        showDvDt = True
        #showClips = False
        #showScatter = True
        if windowOptions is not None:
            showDerivative = windowOptions['rawDataPanels']['Derivative']
            showDAC = windowOptions['rawDataPanels']['DAC']
            showFullRecording = windowOptions['rawDataPanels']['Full Recording']

            self.toggleInterface('Full Recording', showFullRecording)
            self.toggleInterface('Derivative', showDerivative)
            self.toggleInterface('DAC', showDAC)
            #self.toggleInterface('Clips', showClips)

            #
            # toggle interface to myDetectionToolbarWidget
            showPlotOption = windowOptions['detectionPanels']['Detection']
            self.toggleInterface('Detection', showPlotOption)

            showPlotOption = windowOptions['detectionPanels']['Display']
            self.toggleInterface('Display', showPlotOption)

            showPlotOption = windowOptions['detectionPanels']['Plot Options']
            self.toggleInterface('Plot Options', showPlotOption)

    @property
    def sweepNumber(self):
        """Get the current sweep number (from bAnalysis).
        """
        if self.ba is None:
            return None
        else:
            return self.ba.currentSweep

    def detect(self, detectionPresetStr: str, detectionType : sanpy.bDetection.detectionTypes,
                dvdtThreshold, mvThreshold, startSec=None, stopSec=None):
        """
        Detect spikes

        Args:
            detectionPreset (str) corresponds to Enum sanpy.bDetection.detectionPresets_
            detectionType (sanpy.bDetection.detectionTypes): The type of detection (dvdt, vm)
        """

        if self.ba is None:
            str = 'Please select a file to analyze.'
            self.updateStatusBar(str)
            return

        if self.ba.loadError:
            str = 'Did not spike detect, the file was not loaded or may be corrupt?'
            self.updateStatusBar(str)
            return

        #logger.info(f'Detecting with dvdtThreshold:{dvdtThreshold} mvThreshold:{mvThreshold}')
        self.updateStatusBar(f'Detecting spikes detectionType:{detectionType.value} dvdt:{dvdtThreshold} minVm:{mvThreshold} start:{startSec} stop:{stopSec}')

        if startSec is None or stopSec is None:
            startSec = 0
            stopSec = self.ba.recordingDur

        # get default detection parammeters and tweek
        #detectionDict = sanpy.bAnalysis.getDefaultDetection()

        # specify a default, e.g. caKymograph
        #detectionPreset = sanpy.bDetection.detectionPresets.cakymograph
        #sanpy.bDetection(detectionPreset=detectionPreset)
        # was this

        '''
        print(sanpy.bDetection.detectionPresets)
        detectionPreset = sanpy.bDetection.detectionPresets(detectionPresetStr)
        detectionDict = sanpy.bDetection(detectionPreset=detectionPreset) # gets default detection class
        detectionDict['detectionType'] = detectionType.value  # set detection type to ('dvdt', 'vm')
        detectionDict['dvdtThreshold'] = dvdtThreshold
        detectionDict['mvThreshold'] = mvThreshold
        '''

        _selectedDetection = self.detectToolbarWidget._selectedDetection
        detectionDict = self.getMainWindowDetectionClass().getDetectionDict(_selectedDetection)
        detectionDict['detectionType'] = detectionType.value  # set detection type to ('dvdt', 'vm')
        detectionDict['dvdtThreshold'] = dvdtThreshold
        detectionDict['mvThreshold'] = mvThreshold

        # TODO: pass this function detection params and call from sanpy_app ???
        if self.myMainWindow is not None:
            # grab parameters from main interface table
            logger.info('Grabbing detection parameters from main window table')

            # problem is these k/v have v that are mixture of str/float/int ... hard to parse
            myDetectionDict = self.myMainWindow.getSelectedFileDict()

            #
            # fill in detectionDict from *this interface
            detectionDict['startSeconds'] = startSec
            detectionDict['stopSeconds'] = stopSec

            #
            detectionDict['cellType'] = myDetectionDict['Cell Type']
            detectionDict['sex'] = myDetectionDict['Sex']
            detectionDict['condition'] = myDetectionDict['Condition']

        #
        # detect
        self.ba.spikeDetect(detectionDict)

        # show dialog when num spikes is 0
        '''
        if self.ba.numSpikes == 0:
            informativeText = f'dV/dt Threshold:{dvdtThreshold}\nVm Threshold (mV):{mvThreshold}'
            sanpy.interface.bDialog.okDialog('No Spikes Detected', informativeText=informativeText)
        '''

        #
        # fill in our start/stop in the main table
        # this is done in analysisDir.xxx()
        #setCellValue(self, rowIdx, colStr, value)

        self.replot() # replot statistics over traces

        # 20210821
        # refresh spike clips
        #self.refreshClips(None, None)

        self.signalDetect.emit(self.ba)
        #if self.myMainWindow is not None:
        #    # signal to main window so it can update (file list, scatter plot)
        #    self.myMainWindow.mySignal('detect') #, data=(dfReportForScatter, dfError))

    def mySetTheme(self):
        if self.myMainWindow is not None and self.myMainWindow.useDarkStyle:
            pg.setConfigOption('background', 'k')
            pg.setConfigOption('foreground', 'w')
            self.useDarkStyle = True
        else:
            pg.setConfigOption('background', 'w')
            pg.setConfigOption('foreground', 'k')
            self.useDarkStyle = False

    def getMainWindowOptions(self):
        theRet = None
        if self.myMainWindow is not None:
            theRet = self.myMainWindow.getOptions()
        return theRet

    def getMainWindowDetectionClass(self):
        theRet = None
        if self.myMainWindow is not None:
            theRet = self.myMainWindow.getDetectionClass()
        return theRet

    def save(self, alsoSaveTxt=False):
        """
        Prompt user for filename and save both xlsx and txt
        Save always defaults to data folder
        """
        if self.ba is None or self.ba.numSpikes==0:
            #print('   no analysis ???')
            return
        xMin, xMax = self.getXRange()
        #print('    xMin:', xMin, 'xMax:', xMax)

        # abb 20201217, I thought I was already doing this?
        xMinStr = '%.2f'%(xMin)
        xMaxStr = '%.2f'%(xMax)

        lhs, rhs = xMinStr.split('.')
        xMinStr = '_b' + lhs + '_' + rhs

        lhs, rhs = xMaxStr.split('.')
        xMaxStr = '_e' + lhs + '_' + rhs

        filePath, fileName = os.path.split(os.path.abspath(self.ba.path))
        fileBaseName, extension = os.path.splitext(fileName)
        fileBaseName = f'{fileBaseName}{xMinStr}{xMaxStr}.xlsx'
        #excelFileName = os.path.join(filePath, fileBaseName + '.xlsx')
        excelFileName = os.path.join(filePath, fileBaseName)

        #print('Asking user for file name to save...')
        #savefile, tmp = QtGui.QFileDialog.getSaveFileName(self, 'Save File', excelFileName)
        savefile, tmp = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', excelFileName)

        if len(savefile) > 0:
            logger.info(f'savefile: {savefile}')
            logger.info(f'xMin:{xMin} xMax:{xMax} alsoSaveTxt:{alsoSaveTxt}')
            exportObj = sanpy.bExport(self.ba)
            analysisName, df = exportObj.saveReport(savefile, xMin, xMax, alsoSaveTxt=alsoSaveTxt)
            #if self.myMainWindow is not None:
            #    self.myMainWindow.mySignal('saved', data=analysisName)
            txt = f'Exported Excel file: {analysisName}'
            self.updateStatusBar(txt)
        else:
            pass
            #print('no file saved')

    def getXRange(self):
        """
        Get the current range of X-Axis
        """
        rect = self.derivPlot.viewRect() # get xaxis
        xMin = rect.left()
        xMax = rect.right()
        return xMin, xMax

    def _setAxis(self, start, stop, set_xyBoth='xAxis', whichPlot='vm'):
        """
        Shared by (setAxisFull, setAxis)
        """
        # make sure start/stop are in correct order and swap if necc.
        if stop<start:
            tmp = start
            start = stop
            stop = tmp

        #logger.info(f'start:{start} stop:{stop} set_xyBoth:{set_xyBoth} whichPlot:{whichPlot}')

        padding = 0
        if set_xyBoth == 'xAxis':
            self.derivPlot.setXRange(start, stop, padding=padding) # linked to Vm
        if set_xyBoth == 'yAxis':
            if whichPlot in ['dvdt', 'dvdtFiltered']:
                self.derivPlot.setYRange(start, stop) # linked to Vm
            elif whichPlot in ['vm', 'vmFiltered']:
                self.vmPlot.setYRange(start, stop) # linked to Vm
            else:
                logger.error(f'did not understand whichPlot: {whichPlot}')

        # update rectangle in vmPlotGlobal
        self.linearRegionItem2.setRegion([start,stop])

        # update detection toolbar
        if set_xyBoth == 'xAxis':
            self.detectToolbarWidget.startSeconds.setValue(start)
            self.detectToolbarWidget.startSeconds.repaint()
            self.detectToolbarWidget.stopSeconds.setValue(stop)
            self.detectToolbarWidget.stopSeconds.repaint()
        #else:
        #    print('todo: add interface for y range in bDetectionWidget._setAxis()')

        #if set_xyBoth == 'xAxis':
        #    self.refreshClips(start, stop)

        return start, stop

    def setAxis_OnFileChange(self, startSec, stopSec):
        if startSec is None or stopSec is None or math.isnan(startSec) or math.isnan(stopSec):
            startSec = 0
            stopSec = self.ba.recordingDur

        self.vmPlotGlobal.autoRange(items=[self.vmLinesFiltered2])  # always full view
        self.linearRegionItem2.setRegion([startSec, stopSec])

        padding = 0
        self.derivPlot.setXRange(startSec, stopSec, padding=padding) # linked to Vm

    def setAxisFull_y(self, thisAxis):
        """
        thisAxis: (vm, dvdt)
        """
        #logger.info(f'thisAxis:"{thisAxis}"')
        # y-axis is NOT shared
        # dvdt
        if thisAxis in ['dvdt', 'dvdtFiltered']:
            filteredDeriv = self.ba.filteredDeriv
            top = np.nanmax(filteredDeriv)
            bottom = np.nanmin(filteredDeriv)
            start, stop = self._setAxis(bottom, top,
                                    set_xyBoth='yAxis',
                                    whichPlot='dvdt')
        elif thisAxis in ['vm', 'vmFiltered']:
            sweepY = self.ba.sweepY
            top = np.nanmax(sweepY)
            bottom = np.nanmin(sweepY)
            start, stop = self._setAxis(bottom, top,
                                    set_xyBoth='yAxis',
                                    whichPlot='vm')
        else:
            logger.error(f'Did not understand thisAxis:"{thisAxis}"')

    def setAxisFull(self):
        """Set full axis for (deriv, daq, vm, clips).
        """
        if self.ba is None:
            return

        self.derivPlot.autoRange()
        self.dacPlot.autoRange()

        # 20220115
        #self.vmPlot.autoRange(items=[self.vmLinesFiltered])
        self.vmPlot.enableAutoRange()

        self.vmPlotGlobal.autoRange(items=[self.vmLinesFiltered2])  # we never zoom this

        #self.refreshClips(None, None)
        #self.clipPlot.autoRange()

        # rectangle region on vmPlotGlobal
        self.linearRegionItem2.setRegion([0, self.ba.recordingDur])

        #
        # update detection toolbar
        start = 0
        stop = self.ba.recordingDur
        self.detectToolbarWidget.startSeconds.setValue(start)
        self.detectToolbarWidget.startSeconds.repaint()
        self.detectToolbarWidget.stopSeconds.setValue(stop)
        self.detectToolbarWidget.stopSeconds.repaint()

        # todo: make this a signal, with slot in main window
        if self.myMainWindow is not None:
            # currently, this will just update scatte plot
            self.myMainWindow.mySignal('set full x axis')

    def setAxis(self, start, stop, set_xyBoth='xAxis', whichPlot='vm'):
        """
        Called when user click+drag in a pyQtGraph plot.

        Args:
            start
            stop
            set_xyBoth: (xAxis, yAxis, Both)
            whichPlot: (dvdt, vm)
        """
        start, stop = self._setAxis(start, stop, set_xyBoth=set_xyBoth, whichPlot=whichPlot)
        #print('bDetectionWidget.setAxis()', start, stop)
        if set_xyBoth == 'xAxis':
            if self.myMainWindow is not None:
                self.myMainWindow.mySignal('set x axis', data=[start,stop])
        # no need to emit change in y-axis, no other widgets change
        '''
        elif set_xyBoth == 'yAxis':
            # todo: this needs to know which plot
            if self.myMainWindow is not None:
                self.myMainWindow.mySignal('set y axis', data=[start,stop])
        '''
        #elif set_xyBoth == 'both':
        #    self.myMainWindow.mySignal('set y axis', data=[start,stop])

    def fillInDetectionParameters(self, tableRowDict):
        """
        """
        #print('fillInDetectionParameters() tableRowDict:', tableRowDict)
        self.detectToolbarWidget.fillInDetectionParameters(tableRowDict)

    def updateStatusBar(self, text):
        if self.myMainWindow is not None:
            self.myMainWindow.slot_updateStatus(text)
        else:
            logger.info(text)

    def on_scatterClicked(self, item, points, ev=None):
        """
        item: PlotDataItem that was clicked
        points: list of points clicked (pyqtgraph.graphicsItems.ScatterPlotItem.SpotItem)
        """

        '''
        print('=== bDetectionWidget.on_scatterClicked')
        print('  item:', item)
        print('  points:', points)
        print('  ev:', ev)
        '''
        indexes = []
        #print('item.data:', item.data())
        #for idx, p in enumerate(points):
        #    print(f'    points[{idx}].data():{p.data()} p.index:{p.index()} p.pos:{p.pos()}')

        if len(points) > 0:
            sweepSpikeNumber = points[0].index()

            # convert sweep spike index to absolute
            absIndex = self.ba.getAbsSpikeFromSweep(sweepSpikeNumber, self.sweepNumber)

            logger.info(f'self.sweepNumber:{self.sweepNumber} sweepSpikeNumber:{sweepSpikeNumber} absIndex:{absIndex}')
            eDict = {
                'spikeNumber': absIndex,
                'doZoom': False,
                'ba': self.ba,
            }
            logger.info(f'    {eDict}')

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
        #print('bDetectionWidget.getEDD()')
        x = []
        y = []
        #for idx, spike in enumerate(self.ba.spikeDict:
        spikeDictionaries = self.ba.getSpikeDictionaries(sweepNumber=self.sweepNumber)
        for idx, spike in enumerate(spikeDictionaries):

            preLinearFitPnt0 = spike['preLinearFitPnt0']
            preLinearFitPnt1 = spike['preLinearFitPnt1']

            if preLinearFitPnt0 is not None:
                preLinearFitPnt0 = self.ba.pnt2Sec_(preLinearFitPnt0)
            else:
                preLinearFitPnt0 = np.nan

            if preLinearFitPnt1 is not None:
                preLinearFitPnt1 = self.ba.pnt2Sec_(preLinearFitPnt1)
            else:
                preLinearFitPnt1 = np.nan

            preLinearFitVal0 = spike['preLinearFitVal0']
            preLinearFitVal1 = spike['preLinearFitVal1']

            x.append(preLinearFitPnt0)
            x.append(preLinearFitPnt1)
            x.append(np.nan)

            y.append(preLinearFitVal0)
            y.append(preLinearFitVal1)
            y.append(np.nan)

        #print ('  returning', len(x), len(y))
        return x, y

    def old_getHalfWidths(self):
        """Get x/y pair for plotting all half widths."""
        # defer until we know how many half-widths 20/50/80
        x = []
        y = []
        numPerSpike = 3  # rise/fall/nan
        numSpikes = self.ba.numSpikes
        xyIdx = 0
        #for idx, spike in enumerate(self.ba.spikeDict):
        spikeDictionaries = self.ba.getSpikeDictionaries(sweepNumber=self.sweepNumber)
        for idx, spike in enumerate(spikeDictionaries):
            if idx ==0:
                # make x/y from first spike using halfHeights = [20,50,80]
                halfHeights = spike['halfHeights'] # will be same for all spike, like [20, 50, 80]
                numHalfHeights = len(halfHeights)
                # *numHalfHeights to account for rise/fall + padding nan
                x = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
                y = [np.nan] * (numSpikes * numHalfHeights * numPerSpike)
                #print('  len(x):', len(x), 'numHalfHeights:', numHalfHeights, 'numSpikes:', numSpikes, 'halfHeights:', halfHeights)

            if 'widths' not in spike:
                print(f'=== Did not find "widths" key in spike {idx}')
                #print(spike)
            for idx2, width in enumerate(spike['widths']):
                halfHeight = width['halfHeight'] # [20,50,80]
                risingPnt = width['risingPnt']
                risingVal = width['risingVal']
                fallingPnt = width['fallingPnt']
                fallingVal = width['fallingVal']

                if risingPnt is None or fallingPnt is None:
                    # half-height was not detected
                    continue

                risingSec = self.ba.pnt2Sec_(risingPnt)
                fallingSec = self.ba.pnt2Sec_(fallingPnt)

                x[xyIdx] = risingSec
                x[xyIdx+1] = fallingSec
                x[xyIdx+2] = np.nan
                # y
                y[xyIdx] = fallingVal  #risingVal, to make line horizontal
                y[xyIdx+1] = fallingVal
                y[xyIdx+2] = np.nan

                # each spike has 3x pnts: rise/fall/nan
                xyIdx += numPerSpike  # accounts for rising/falling/nan
            # end for width
        # end for spike
        #print('  numSpikes:', numSpikes, 'xyIdx:', xyIdx)
        #
        return x, y

    def replot(self, oneIndex=None):

        if self.ba is None:
            return

        for idx, plot in enumerate(self.myPlots):
            if oneIndex is not None and idx!=oneIndex:
                continue
            xPlot = []
            yPlot = []
            plotIsOn = plot['plotIsOn']
            #  TODO: fix the logic here, we are not calling replot() when user toggles plot radio checkboxes
            #plotIsOn = True
            if plotIsOn and plot['humanName'] == 'Half-Widths':
                spikeDictionaries = self.ba.getSpikeDictionaries(sweepNumber=self.sweepNumber)
                sweepX = self.ba.sweepX
                filteredVm = self.ba.filteredVm
                #filteredVm = filteredVm[:,0]
                xPlot, yPlot = sanpy.getHalfWidthLines(sweepX, filteredVm, spikeDictionaries)
            elif plotIsOn and plot['humanName'] == 'Epoch Lines':
                _epochTable = self.ba.getEpochTable(self.sweepNumber)
                xPlot, yPlot =  _epochTable.getEpochLines(yMin=np.nanmin(self.ba.filteredVm), yMax=np.nanmax(self.ba.filteredVm))
            elif plotIsOn and plot['humanName'] == 'EDD':
                xPlot, yPlot = self.getEDD()
            elif plotIsOn and plot['humanName'] == 'EDD Rate':
                #xPlot, yPlot = sanpy.analysisPlot.getEddLines(self.ba)
                xPlot, yPlot = sanpy.getEddLines(self.ba)
            elif plotIsOn:
                xPlot, yPlot = self.ba.getStat(plot['x'], plot['y'], sweepNumber=self.sweepNumber)
                if xPlot is not None and plot['convertx_tosec']:
                    xPlot = [self.ba.pnt2Sec_(x) for x in xPlot] # convert pnt to sec
            #
            # added connect='finite' to respect nan in half-width
            # not sure how connect='finite' affect all other plots using scatter???
            #print(f'{plot}')
            #print('  ', xPlot, yPlot)
            self.myPlotList[idx].setData(x=xPlot, y=yPlot)
            #self.togglePlot(idx, plot['plotIsOn'])

        # update label with number of spikes detected
        #print('todo: bDetectionWidget.replot(), make numSpikesLabel respond to signal/slot')
        numSpikesStr = str(self.ba.numSpikes)
        self.detectToolbarWidget.numSpikesLabel.setText('Spikes: ' + numSpikesStr)
        self.detectToolbarWidget.numSpikesLabel.repaint()

        # spike freq
        #print('todo: bDetectionWidget.replot(), make spikeFreqLabel respond to signal/slot')
        meanSpikeFreq = self.ba.getStatMean('spikeFreq_hz', sweepNumber=self.sweepNumber)
        if meanSpikeFreq is not None:
            meanSpikeFreq = round(meanSpikeFreq,2)
        self.detectToolbarWidget.spikeFreqLabel.setText('Freq: ' + str(meanSpikeFreq))
        self.detectToolbarWidget.spikeFreqLabel.repaint()

        # num errors
        self.detectToolbarWidget.numErrorsLabel.setText('Errors: ' + str(self.ba.numErrors()))
        self.detectToolbarWidget.numErrorsLabel.repaint()

    def togglePlot(self, idx, on):
        """
        Toggle overlay of stats like (spike threshold, spike peak, ...).

        Arg:
            idx (int): overlay index into self.myPlots
            on (bool):
        """
        if isinstance(idx, str):
            logger.error(f'Unexpected type for parameter idx "{idx}" with type {type(idx)}')
            return

        # toggle the plot on/off
        self.myPlots[idx]['plotIsOn'] = on

        if on:
            #self.myPlotList[idx].setData(pen=pg.mkPen(width=5, color=plot['color'], symbol=plot['symbol']), size=2)
            self.myPlotList[idx].show()
            #self.myPlotList[idx].setPen(pg.mkPen(width=5, color=plot['color'], symbol=plot['symbol']))
            # removed for half-width
            #self.myPlotList[idx].setSize(2)
        else:
            #self.myPlotList[idx].setData(pen=pg.mkPen(width=0, color=plot['color'], symbol=plot['symbol']), size=0)
            self.myPlotList[idx].hide()
            #self.myPlotList[idx].setPen(pg.mkPen(width=0, color=plot['color'], symbol=plot['symbol']))
            # removed for half-width
            #self.myPlotList[idx].setSize(0)

        # always replot everything
        self.replot(oneIndex=idx)

    def selectSweep(self, sweepNumber, startSec=None, stopSec=None, doEmit=True):
        """
        sweepNumber (str): from ('All', 0, 1, 2, 3, ...)
        """
        if sweepNumber == '':
            logger.error('')
            return

        if sweepNumber == 'All':
            sweepNumber = None
        else:
            sweepNumber = int(sweepNumber)

        if sweepNumber<0 or sweepNumber>self.ba.numSweeps-1:
            return

        logger.info(f'sweepNumber:"{sweepNumber}" {type(sweepNumber)} doEmit:{doEmit} startSec:"{startSec}" stopSec:"{stopSec}"')

        #if self._sweepNumber == sweepNumber:
        #    logger.info(f'Already showing sweep:{sweepNumber}      RETURNING')
        #    return

        #self._sweepNumber = sweepNumber
        self.ba.setSweep(sweepNumber)

        #self.setAxisFull()

        # cancel spike selection
        self.selectSpike(None)

        self._replot(startSec, stopSec)  # will set full axis

        if doEmit:
            self.signalSelectSweep.emit(self.ba, sweepNumber)

    def selectSpike(self, spikeNumber : int, doZoom=False, doEmit=False):
        """
        Args:
            spikeNumber: absolute
        """
        logger.info(f'spikeNumber:{spikeNumber} doZoom:{doZoom} doEmit:{doEmit}')
        
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
            if spikeNumber<0 or spikeNumber>self.ba.numSpikes-1:
                logger.error(f'Got spike {spikeNumber} but expecting range [0,{self.ba.numSpikes-1})')
                return

            sweep = self.ba.getSpikeStat(spikeList, 'sweep')
            sweep = sweep[0]  # just the first
            if sweep != self.sweepNumber:
                print('!!! SWITCHING to sweep:', sweep, 'from self.sweepNumber:', self.sweepNumber)
                self.slot_selectSweep(sweep)

            logger.info(f'spikeNumber: {spikeNumber}, sweep {sweep}, doZoom {doZoom}')
            sweepSpikeNumber = self.ba.getSweepSpikeFromAbsolute(spikeNumber, sweep)
            sweepSpikeList = [sweepSpikeNumber]
            print('    sweepSpikeNumber:', sweepSpikeNumber, type(sweepSpikeNumber))

            spikeList = [sweepSpikeNumber]

            # removed second clause while adding multiple spike selection
            #if spikeNumber is not None and spikeNumber < len(xPlot):
            #xPlot, yPlot = self.ba.getStat('peakSec', 'peakVal', sweepNumber=self.sweepNumber)
            xPlot, yPlot = self.ba.getStat('peakSec', 'peakVal', sweepNumber=sweep)
            xPlot = np.array(xPlot)
            yPlot = np.array(yPlot)
            try:
                x = xPlot[sweepSpikeList]
                y = yPlot[sweepSpikeList]
            except (IndexError) as e:
                logger.error(f'{e}')
                #pass

        self.mySingleSpikeScatterPlot.setData(x=x, y=y)

        # zoom
        if spikeNumber is not None and doZoom:
            thresholdSeconds = self.ba.getStat('thresholdSec', sweepNumber=self.sweepNumber)
            if sweepSpikeNumber < len(thresholdSeconds):
                logger.info('    !!!! REMOVE HARD CODED ZOOM')
                #thresholdSecond = thresholdSeconds[spikeNumber]
                thresholdSecond = thresholdSeconds[sweepSpikeNumber]
                thresholdSecond = round(thresholdSecond, 3)
                startSec = thresholdSecond - 0.5
                startSec = round(startSec, 2)
                stopSec = thresholdSecond + 0.5
                stopSec = round(stopSec, 2)
                #print('  spikeNumber:', spikeNumber, 'thresholdSecond:', thresholdSecond, 'startSec:', startSec, 'stopSec:', stopSec)
                start = self.setAxis(startSec, stopSec)

        if doEmit:
            eDict = {
                'spikeNumber': spikeNumber,
                'doZoom': doZoom,
                'ba': self.ba,
            }
            self.signalSelectSpike.emit(eDict)

    def selectSpikeList(self, spikeList, doZoom=False, doEmit=False):
        x = None
        y = None

        if len(spikeList) > 0:
            xPlot, yPlot = self.ba.getStat('peakSec', 'peakVal', sweepNumber=self.sweepNumber)
            xPlot = np.array(xPlot)
            yPlot = np.array(yPlot)
            x = xPlot[spikeList]
            y = yPlot[spikeList]

        self.mySpikeListScatterPlot.setData(x=x, y=y)

        # I don't think anybody is listening to this
        if doEmit:
            eDict = {
                'spikeList': spikeList,
                'doZoom': doZoom,
                'ba': self.ba,
            }
            self.signalSelectSpikeList.emit(eDict)

    def old_refreshClips(self, xMin=None, xMax=None):

        if not self.clipPlot.isVisible():
            # clips are not being displayed
            #logger.info('Clips not visible --- RETURNING')
            return

        logger.info('')

        # always remove existing
        # if there are no clips and we bail we will at least clear display
        self.clipPlot.clear()

        #if self.clipLines is not None:
        #    self.clipPlot.removeItem(self.clipLines)
        #if self.meanClipLine is not None:
        #    self.clipPlot.removeItem(self.meanClipLine)

        if self.ba is None:
            return

        if self.ba.numSpikes == 0:
            return

        # this returns x-axis in ms
        theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(xMin, xMax, sweepNumber=self.sweepNumber)

        # convert clips to 2d ndarray ???
        xTmp = np.array(theseClips_x)
        #xTmp /= self.ba.dataPointsPerMs # pnt to ms
        xTmp /= self.ba.dataPointsPerMs * 1000  # pnt to seconds
        yTmp = np.array(theseClips)

        #print('refreshClips() xTmp:', xTmp.shape)
        #print('refreshClips() yTmp:', yTmp.shape)

        self.clipLines = MultiLine(xTmp, yTmp, self, allowXAxisDrag=False, type='clip')
        self.clipPlot.addItem(self.clipLines)

        #print(xTmp.shape) # (num spikes, time)
        self.xMeanClip = xTmp
        if len(self.xMeanClip) > 0:
            self.xMeanClip = np.nanmean(xTmp, axis=0) # xTmp is in ms
        self.yMeanClip = yTmp
        if len(self.yMeanClip) > 0:
            self.yMeanClip = np.nanmean(yTmp, axis=0)
        self.meanClipLine = MultiLine(self.xMeanClip, self.yMeanClip, self, allowXAxisDrag=False, type='meanclip')
        self.clipPlot.addItem(self.meanClipLine)

    def toggleInterface(self, item, on):
        """
        show/hide different portions of interface
        """
        #print('toggle_Interface()', item, on)
        #if item == 'Clips':
        #    #self.toggleClips(on)
        #    if self.myMainWindow is not None:
        #        #self.myMainWindow.toggleStatisticsPlot(on)
        #        self.myMainWindow.preferencesSet('display', 'showClips', on)
        #    if on:
        #        self.clipPlot.show()
        #        self.refreshClips() # refresh if they exist (e.g. analysis has been done)
        #    else:
        #        self.clipPlot.hide()
        '''
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
        '''

        if item == 'Full Recording':
            if on:
                self.vmPlotGlobal.show()
            else:
                self.vmPlotGlobal.hide()
        elif item == 'Derivative':
            if on:
                self.derivPlot.show()
            else:
                self.derivPlot.hide()
        elif item == 'DAC':
            if on:
                self.dacPlot.show()
            else:
                self.dacPlot.hide()

        # toggle in myDetectionToolbarWidget
        elif item == 'Detection Panel':
            if on:
                self.detectToolbarWidget.show()
            else:
                self.detectToolbarWidget.hide()
        elif item == 'Detection':
            self.detectToolbarWidget.toggleInterface(item, on)
        elif item == 'Display':
            self.detectToolbarWidget.toggleInterface(item, on)
        elif item == 'Plot Options':
            self.detectToolbarWidget.toggleInterface(item, on)

        else:
            # Toggle overlay of stats like (TOP, spike peak, half-width, ...)
            self.togglePlot(item, on) # assuming item is int !!!

    def old_kymographChanged(self, event):
        """
        User finished gragging the ROI

        Args:
            event (pyqtgraph.graphicsItems.ROI.ROI)
        """
        logger.info('')
        #print(event)
        pos = event.pos()
        size = event.size()
        #print(pos, size)

        #imagePos = self.myImageItem.mapFromScene(event.scenePos())
        #imageSize = self.myImageItem.mapFromScene(event.size())
        #print('  imagePos:', imagePos, 'imageSize:', imageSize)

        left, top, right, bottom = None, None, None, None
        handles = event.getSceneHandlePositions()
        for handle in handles:
            if handle[0] is not None:
                imagePos = self.myImageItem.mapFromScene(handle[1])
                x = imagePos.x()
                y = imagePos.y()
                # units are in image pixels !!!
                #print(handle[0], 'x:', x, 'y:', y)
                if handle[0] == 'topleft':
                    left = x
                    bottom = y
                    #top = y
                elif handle[0] == 'bottomright':
                    right = x
                    top = y
                    #bottom = y
        #
        left = int(left)
        top = int(top)
        right = int(right)
        bottom = int(bottom)

        if left<0:
            left = 0

        print(f'  left:{left} top:{top} right:{right} bottom:{bottom}')

        #  cludge
        if bottom > top:
            logger.warning(f'fixing bad top/bottom')
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

    def buildUI(self):
        # left is toolbar, right is PYQtGraph (self.view)
        self.myHBoxLayout_detect = QtWidgets.QHBoxLayout(self)
        self.myHBoxLayout_detect.setAlignment(QtCore.Qt.AlignTop)

        # detection widget toolbar
        # abb 20201110, switching over to a better layout
        #self.detectToolbarWidget = myDetectToolbarWidget(self.myPlots, self)
        #self.myHBoxLayout_detect.addLayout(self.detectToolbarWidget, stretch=1) # stretch=10, not sure on the units???
        self.detectToolbarWidget = myDetectToolbarWidget2(self.myPlots, self)
        self.signalSelectSpike.connect(self.detectToolbarWidget.slot_selectSpike)
        #if self.myMainWindow is not None:
        #    self.detectToolbarWidget.signalSelectSpike.connect(self.myMainWindow.slotSelectSpike)

        # was this
        #self.myHBoxLayout_detect.addWidget(self.detectToolbarWidget, stretch=1) # stretch=10, not sure on the units???
        self.myHBoxLayout_detect.addWidget(self.detectToolbarWidget) # stretch=10, not sure on the units???

        # kymograph, we need a vboxlayout to hollder (kym widget, self.view)
        vBoxLayoutForPlot = QtWidgets.QVBoxLayout(self)

        self.myKymWidget = sanpy.interface.bKymograph.kymWidget()
        self.myKymWidget.signalKymographRoiChanged.connect(self.slot_kymographChanged)
        self.myKymWidget.setVisible(False)
        vBoxLayoutForPlot.addWidget(self.myKymWidget)

        # was this
        self.view = pg.GraphicsLayoutWidget()

        #self.view.scene().sigMouseClicked.connect(self.tmpOnClick)

        # works but does not stick
        #self.view.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
        self.view.show()

        row = 0
        colSpan = 1

        # Kymograph, always build (hidden) and show/hide in replot based on self.ba.isKymograph
        '''
        rowSpan = 1
        self.kymographPlot = self.view.addPlot(row=row, col=0, rowSpan=rowSpan, colSpan=colSpan)
        self.kymographPlot.enableAutoRange()
        # turn off x/y dragging of deriv and vm
        self.kymographPlot.setMouseEnabled(x=False, y=False)
        # hide the little 'A' button to rescale axis
        self.kymographPlot.hideButtons()
        # turn off right-click menu
        self.kymographPlot.setMenuEnabled(False)
        # hide by default
        self.kymographPlot.hide()  # show in _replot() if self.ba.isKymograph()

        #if self.ba.isKymograph():
        #    myTif = self.ba.tifData
        #    self.myImageItem = kymographImage(myTif, axisOrder='row-major',
        #                        rect=[0,0, self.ba.recordingDur, self.ba.tifData.shape[0]])

        row += rowSpan
        '''

        #
        rowSpan = 1
        self.vmPlotGlobal = self.view.addPlot(row=row, col=0, rowSpan=rowSpan, colSpan=colSpan)
        self.vmPlotGlobal.enableAutoRange()
        row += rowSpan
        rowSpan = 1
        self.derivPlot = self.view.addPlot(row=row, col=0, rowSpan=rowSpan, colSpan=colSpan)
        self.derivPlot.enableAutoRange()
        row += rowSpan
        rowSpan = 1
        self.dacPlot = self.view.addPlot(row=row, col=0, rowSpan=rowSpan, colSpan=colSpan)
        self.dacPlot.enableAutoRange()
        row += rowSpan
        rowSpan = 2  # make Vm plot taller than others
        self.vmPlot = self.view.addPlot(row=row, col=0, rowSpan=rowSpan, colSpan=colSpan)
        self.vmPlot.enableAutoRange()
        #row += rowSpan
        #rowSpan = 1
        #self.clipPlot = self.view.addPlot(row=row, col=0, rowSpan=rowSpan, colSpan=colSpan)

        #
        # mouse crosshair
        #crosshairPlots = ['derivPlot', 'dacPlot', 'vmPlot', 'clipPlot']
        crosshairPlots = ['derivPlot', 'dacPlot', 'vmPlot']
        self.crosshairDict = {}
        for crosshairPlot in crosshairPlots:
            self.crosshairDict[crosshairPlot] = {
                'h': pg.InfiniteLine(angle=0, movable=False),
                'v': pg.InfiniteLine(angle=90, movable=False)
            }
            # start hidden
            self.crosshairDict[crosshairPlot]['h'].hide()
            self.crosshairDict[crosshairPlot]['v'].hide()

            # add h/v to appropriate plot
            if crosshairPlot == 'derivPlot':
                self.derivPlot.addItem(self.crosshairDict[crosshairPlot]['h'], ignoreBounds=True)
                self.derivPlot.addItem(self.crosshairDict[crosshairPlot]['v'], ignoreBounds=True)
            elif crosshairPlot == 'dacPlot':
                self.dacPlot.addItem(self.crosshairDict[crosshairPlot]['h'], ignoreBounds=True)
                self.dacPlot.addItem(self.crosshairDict[crosshairPlot]['v'], ignoreBounds=True)
            elif crosshairPlot == 'vmPlot':
                self.vmPlot.addItem(self.crosshairDict[crosshairPlot]['h'], ignoreBounds=True)
                self.vmPlot.addItem(self.crosshairDict[crosshairPlot]['v'], ignoreBounds=True)
            #elif crosshairPlot == 'clipPlot':
            #    self.clipPlot.addItem(self.crosshairDict[crosshairPlot]['h'], ignoreBounds=True)
            #    self.clipPlot.addItem(self.crosshairDict[crosshairPlot]['v'], ignoreBounds=True)
            else:
                logger.error(f'case not taken for crosshairPlot: {crosshairPlot}')

        #
        # epoch as vertical lines
        # we don't know the number of epochs until we have a ba?

        # trying to implement mouse moved events
        self.myProxy = pg.SignalProxy(self.vmPlot.scene().sigMouseMoved, rateLimit=60, slot=self.myMouseMoved)
        #self.vmPlot.scene().sigMouseMoved.connect(self.myMouseMoved)

        # does not have setStyleSheet
        #self.derivPlot.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))

        # hide the little 'A' button to rescale axis
        self.vmPlotGlobal.hideButtons()
        self.derivPlot.hideButtons()
        self.dacPlot.hideButtons()
        self.vmPlot.hideButtons()
        #self.clipPlot.hideButtons()

        # turn off right-click menu
        self.vmPlotGlobal.setMenuEnabled(False)
        self.derivPlot.setMenuEnabled(False)
        self.dacPlot.setMenuEnabled(False)
        self.vmPlot.setMenuEnabled(False)
        #self.clipPlot.setMenuEnabled(False)

        # link x-axis of deriv and vm
        self.derivPlot.setXLink(self.vmPlot)
        self.derivPlot.setXLink(self.dacPlot)
        self.dacPlot.setXLink(self.derivPlot)
        self.dacPlot.setXLink(self.vmPlot)
        self.vmPlot.setXLink(self.derivPlot)
        self.vmPlot.setXLink(self.dacPlot)
        #
        #self.kymographPlot.setXLink(self.vmPlot)  # TODO: need to set scale of kymograph x-axis
        #self.kymographPlot.setXLink(self.derivPlot)

        # turn off x/y dragging of deriv and vm
        self.vmPlotGlobal.setMouseEnabled(x=False, y=False)
        self.derivPlot.setMouseEnabled(x=False, y=False)
        self.dacPlot.setMouseEnabled(x=False, y=False)
        self.vmPlot.setMouseEnabled(x=False, y=False)
        #self.clipPlot.setMouseEnabled(x=False, y=False)

        #self.toggleClips(False)

        # add all overlaid scatter plots
        self.myPlotList = [] # list of pg.ScatterPlotItem
        for idx, plot in enumerate(self.myPlots):
            color = plot['color']
            symbol = plot['symbol']
            humanName = plot['humanName']
            if humanName in ['Half-Widths']:
                # PlotCurveItem
                myScatterPlot = pg.PlotDataItem(pen=pg.mkPen(width=2, color=color), connect='finite') # default is no symbol
            elif humanName in ['Epoch Lines']:
                myScatterPlot = pg.PlotDataItem(pen=pg.mkPen(width=1, color=color, style=QtCore.Qt.DashLine), connect='finite') # default is no symbol
            elif humanName == 'EDD Rate':
                # edd rate is a dashed line showing slope/rate of edd
                myScatterPlot = pg.PlotDataItem(pen=pg.mkPen(width=2, color=color, style=QtCore.Qt.DashLine), connect='finite') # default is no symbol
            else:
                myScatterPlot = pg.PlotDataItem(pen=None, symbol=symbol, symbolSize=6, symbolPen=None, symbolBrush=color)
                myScatterPlot.setData(x=[], y=[]) # start empty
                if humanName in ['Threshold (mV)', 'AP Peak (mV)']:
                    myScatterPlot.sigPointsClicked.connect(self.on_scatterClicked)

            self.myPlotList.append(myScatterPlot)

            # add plot to pyqtgraph
            if plot['plotOn'] == 'vm':
                self.vmPlot.addItem(myScatterPlot)
            elif plot['plotOn'] == 'vmGlobal':
                self.vmPlotGlobal.addItem(myScatterPlot)
            elif plot['plotOn'] == 'dvdt':
                self.derivPlot.addItem(myScatterPlot)

        # single spike selection
        color = 'y'
        symbol = 'x'
        self.mySingleSpikeScatterPlot = pg.ScatterPlotItem(pen=pg.mkPen(width=2, color=color), symbol=symbol, size=10)
        self.vmPlot.addItem(self.mySingleSpikeScatterPlot)

        # mult spike selection (spikeList)
        color = 'c'
        symbol = 'o'
        self.mySpikeListScatterPlot = pg.ScatterPlotItem(pen=pg.mkPen(width=2, color=color), symbol=symbol, size=10)
        self.vmPlot.addItem(self.mySpikeListScatterPlot)

        # axis labels
        # TODO (cudmore) get the units correct, grab from y-axis of abf file
        self.vmPlotGlobal.getAxis('left').setLabel('mV')
        self.derivPlot.getAxis('left').setLabel('Derivative')
        self.dacPlot.getAxis('left').setLabel('DAC')
        self.vmPlot.getAxis('left').setLabel('mV')
        self.vmPlot.getAxis('bottom').setLabel('Seconds')

        self.replot()

        # kymograph
        #tmpVLayout = QtWidgets.QVBoxLayout()
        vBoxLayoutForPlot.addWidget(self.view)

        self.myHBoxLayout_detect.addLayout(vBoxLayoutForPlot)

        # was this, switchin to kym
        #self.myHBoxLayout_detect.addWidget(self.view)


    def toggleCrosshair(self, onOff):
        for plotName in self.crosshairDict.keys():
            self.crosshairDict[plotName]['h'].setVisible(onOff)
            self.crosshairDict[plotName]['v'].setVisible(onOff)

    def myMouseMoved(self, event):
        # event: PyQt5.QtCore.QPointF
        #print('myMouseMoved()', event)

        # looking directly at checkbox in myDetectionToolbarWidget2
        if not self.detectToolbarWidget.crossHairCheckBox.isChecked():
            return

        pos = event[0]  ## using signal proxy turns original arguments into a tuple

        x = None
        y = None
        mousePoint = None
        inPlot = None
        if self.derivPlot.sceneBoundingRect().contains(pos):
            # deriv
            inPlot = 'derivPlot'
            self.crosshairDict[inPlot]['h'].show()
            self.crosshairDict[inPlot]['v'].show()
            mousePoint = self.derivPlot.vb.mapSceneToView(pos)
            # hide the horizontal in dacPlot
            self.crosshairDict['dacPlot']['v'].show()
            self.crosshairDict['dacPlot']['h'].hide()
            # hide the horizontal in vmPlot
            self.crosshairDict['vmPlot']['v'].show()
            self.crosshairDict['vmPlot']['h'].hide()

        elif self.dacPlot.sceneBoundingRect().contains(pos):
            # dac
            inPlot = 'dacPlot'
            self.crosshairDict[inPlot]['h'].show()
            self.crosshairDict[inPlot]['v'].show()
            mousePoint = self.dacPlot.vb.mapSceneToView(pos)
            # hide the horizontal in derivPlot
            self.crosshairDict['derivPlot']['v'].show()
            self.crosshairDict['derivPlot']['h'].hide()
            # hide the horizontal in vmPlot
            self.crosshairDict['vmPlot']['v'].show()
            self.crosshairDict['vmPlot']['h'].hide()

        elif self.vmPlot.sceneBoundingRect().contains(pos):
            # vm
            inPlot = 'vmPlot'
            self.crosshairDict[inPlot]['h'].show()
            self.crosshairDict[inPlot]['v'].show()
            mousePoint = self.vmPlot.vb.mapSceneToView(pos)
            # hide the horizontal in dacPlot
            self.crosshairDict['dacPlot']['v'].show()
            self.crosshairDict['dacPlot']['h'].hide()
            # hide the horizontal in derivPlot
            self.crosshairDict['derivPlot']['v'].show()
            self.crosshairDict['derivPlot']['h'].hide()

        #elif self.clipPlot.sceneBoundingRect().contains(pos):
        #    # clip
        #    inPlot = 'clipPlot'
        #    self.crosshairDict[inPlot]['h'].show()
        #    self.crosshairDict[inPlot]['v'].show()
        #    mousePoint = self.clipPlot.vb.mapSceneToView(pos)
        #    # hide the horizontal/vertical in both derivPlot and vmPlot

        if inPlot is not None and mousePoint is not None:
            self.crosshairDict[inPlot]['h'].setPos(mousePoint.y())
            self.crosshairDict[inPlot]['v'].setPos(mousePoint.x())

        if inPlot == 'derivPlot':
            self.crosshairDict['dacPlot']['v'].setPos(mousePoint.x())
            self.crosshairDict['vmPlot']['v'].setPos(mousePoint.x())
        elif inPlot == 'dacPlot':
            self.crosshairDict['derivPlot']['v'].setPos(mousePoint.x())
            self.crosshairDict['vmPlot']['v'].setPos(mousePoint.x())
        if inPlot == 'vmPlot':
            self.crosshairDict['derivPlot']['v'].setPos(mousePoint.x())
            self.crosshairDict['dacPlot']['v'].setPos(mousePoint.x())

        if mousePoint is not None:
            x = mousePoint.x()
            y = mousePoint.y()

        # x/y can still be None
        self.detectToolbarWidget.setMousePositionLabel(x,y)

    def keyPressEvent(self, event):
        #print('=== sanpy_app.MainWindow() keyPressEvent()')
        key = event.key()
        text = event.text()
        #print('== bDetectionWidget.keyPressEvent() key:', key, 'text:', text)
        #logger.info(f'key:{key} text:{text}')

        if text == 'h':
            if self.detectToolbarWidget.isVisible():
                self.detectToolbarWidget.hide()
            else:
                self.detectToolbarWidget.show()

        if text == 'a':
            #self.detectToolbarWidget.keyPressEvent(event)
            self.setAxisFull()

        if key == QtCore.Qt.Key.Key_Escape:
            self.myMainWindow.mySignal('cancel all selections')

    def slot_selectSweep(self, sweep : int):
        """Fake slot, not ising in emit/connect.
        """
        self.selectSweep(sweep)
        self.detectToolbarWidget.slot_selectSweep(sweep)

    def slot_selectSpike(self, sDict):
        logger.info(f'detection widget {sDict}')
        spikeNumber = sDict['spikeNumber']
        doZoom = sDict['doZoom']
        self.selectSpike(spikeNumber, doZoom=doZoom)
        #self.detectToolbarWidget.slot_selectSpike(sDict)

    def slot_selectSpikeList(self, sDict):
        #print('detectionWidget.slotSelectSpike() sDict:', sDict)
        spikeList = sDict['spikeList']
        doZoom = sDict['doZoom']
        self.selectSpikeList(spikeList, doZoom=doZoom)
        #self.detectToolbarWidget.slot_selectSpike(sDict)

    def slot_switchFile(self, tableRowDict=None, ba=None):
        """
        Set self.ba to new bAnalysis object ba

        Can fail if .abf file is corrupt

        Args:
            path (str):
            tableRowDict (dict):
            ba (bAnalysis):

        Returns: True/False
        """

        # bAnalysis object
        self.ba = ba

        # abb 20201009
        if self.ba.loadError:
            self.replot()
            fileName = self.ba.getFileName()  # tableRowDict['File']
            errStr = f'The bAnalysis file was flagged with loadError ... aborting: "{fileName}".'
            logger.error(errStr)
            self.updateStatusBar(errStr)
            return False

        # fill in detection parameters (dvdt, vm, start, stop)
        startSec = ''
        stopSec = ''
        if tableRowDict is not None:
            self.detectToolbarWidget.slot_selectFile(tableRowDict)
            self.fillInDetectionParameters(tableRowDict) # fills in controls
            #self.updateStatusBar(f'Plotting file {path}')
            startSec = tableRowDict['Start(s)']
            stopSec = tableRowDict['Stop(s)']

        if startSec=='' or stopSec=='':
            startSec = 0
            stopSec = self.ba.recordingDur

        # cancel spike selection
        self.selectSpike(None)

        # set sweep to 0
        self.selectSweep(0, startSec, stopSec, doEmit=False) # calls self._replot()

        # set full axis
        # abb 20220615
        self.setAxisFull()

        # abb implement sweep, move to function()
        #abb 20220615
        self._replot(startSec, stopSec)

        #self.refreshClips(startSec, stopSec)

        # update x/y axis labels
        yLabel = self.ba._sweepLabelY
        self.dacPlot.getAxis('left').setLabel('DAC')
        self.derivPlot.getAxis('left').setLabel('Derivative')
        self.vmPlotGlobal.getAxis('left').setLabel(yLabel)
        #self.vmPlotGlobal.getAxis('bottom').setLabel('Seconds')
        self.vmPlot.getAxis('left').setLabel(yLabel)
        self.vmPlot.getAxis('bottom').setLabel('Seconds')

        self.myKymWidget.slot_switchFile(ba)

        return True

    def slot_dataChanged(self, columnName, value, rowDict):
        """User has edited main file table."""
        self.detectToolbarWidget.slot_dataChanged(columnName, value, rowDict)

    def slot_updateAnalysis(self):
        self.replot() # replot statistics over traces
        # refresh spike clips
        #self.refreshClips(None, None)

    def _replot(self, startSec, stopSec, userUpdate=False):
        #remove vm/dvdt/clip items (even when abf file is corrupt)
        #if self.dvdtLines is not None:
        #    self.derivPlot.removeItem(self.dvdtLines)
        if self.dvdtLinesFiltered is not None:
            self.derivPlot.removeItem(self.dvdtLinesFiltered)
        if self.dacLines is not None:
            self.dacPlot.removeItem(self.dacLines)
        if self.vmLinesFiltered is not None:
            self.vmPlot.removeItem(self.vmLinesFiltered)
        if self.vmLinesFiltered2 is not None:
            self.vmPlotGlobal.removeItem(self.vmLinesFiltered2)
        if self.linearRegionItem2 is not None:
            self.vmPlotGlobal.removeItem(self.linearRegionItem2)
        #if self.clipLines is not None:
        #    self.clipPlot.removeItem(self.clipLines)

        # update lines
        #self.dvdtLines = MultiLine(self.ba.abf.sweepX, self.ba.deriv,
        #                    self, type='dvdt')

        # shared by all plot
        sweepX = self.ba.sweepX
        filteredDeriv = self.ba.filteredDeriv
        sweepC = self.ba.sweepC
        filteredVm = self.ba.filteredVm

        #sweepC = self.ba._sweepC[:,3]

        # debug
        '''
        logger.info(f'sweepX: {sweepX.shape}')
        logger.info(f'filteredDeriv: {filteredDeriv.shape}')
        logger.info(f'sweepC: {sweepC.shape}')
        logger.info(f'filteredVm: {filteredVm.shape}')
        '''

        #
        self.dvdtLinesFiltered = MultiLine(sweepX, filteredDeriv,
                            self, forcePenColor=None, type='dvdtFiltered',
                            columnOrder=True)
        #self.derivPlot.addItem(self.dvdtLines)
        self.derivPlot.addItem(self.dvdtLinesFiltered)

        self.dacLines = MultiLine(sweepX, sweepC,
                            self, forcePenColor=None, type='dac',
                            columnOrder=True)
        self.dacPlot.addItem(self.dacLines)

        self.vmLinesFiltered = MultiLine(sweepX, filteredVm,
                            self, forcePenColor=None, type='vmFiltered',
                            columnOrder=True)
        self.vmPlot.addItem(self.vmLinesFiltered)

        # can't add a multi line to 2 different plots???
        self.vmLinesFiltered2 = MultiLine(sweepX, filteredVm,
                            self, forcePenColor='b', type='vmFiltered',
                            columnOrder=True)
        self.vmPlotGlobal.addItem(self.vmLinesFiltered2)
        self.linearRegionItem2 = pg.LinearRegionItem(values=(0,self.ba.recordingDur),
                                    orientation=pg.LinearRegionItem.Vertical,
                                    brush=pg.mkBrush(100,100,100,100),
                                    pen=pg.mkPen(None))
        self.linearRegionItem2.setMovable(False)
        self.vmPlotGlobal.addItem(self.linearRegionItem2)

        # Kymograph
        isKymograph = self.ba.isKymograph()
        self.myKymWidget.setVisible(isKymograph)
        #self.kymographPlot.hide()
        '''
        else:
            self.kymographPlot.clear()
            self.kymographPlot.show()
            #self.tmpImage = np.random.normal(size=(20,50))  # (rows, cols) e.g. (y,x)
            myTif = self.ba.tifData
            #self.myImageItem = pg.ImageItem(myTif, axisOrder='row-major')
            #  TODO: set height to micro-meters
            # was this
            if self.ba.isKymograph():
                axisOrder='row-major'
                rect=[0,0, self.ba.recordingDur, self.ba.tifData.shape[0]]  # x, y, w, h
                if self.myImageItem is None:
                    # first time build
                    self.myImageItem = kymographImage(myTif, axisOrder=axisOrder,
                                    rect=rect)
                else:
                    # second time update
                    myTif = self.ba.tifData
                    self.myImageItem.setImage(myTif, axisOrder=axisOrder,
                                    rect=rect)
            #self.myImageItem.setImage(image=myTif, autoLevels=True)
            #self.myImageItem.setLevels([100,500])
            self.kymographPlot.addItem(self.myImageItem)
            # TODO: put ROI in buildUI
            #self.myLineRoi = pg.ROI(pos=(10,10), size=(500,20), parent=self.kymographPlot)

            kymographRect = self.ba.getKymographRect()
            if kymographRect is not None:
                xRoiPos = kymographRect[0]
                #yRoiPos = kymographRect[1]
                yRoiPos = kymographRect[3]
                top = kymographRect[1]
                right = kymographRect[2]
                bottom = kymographRect[3]
                widthRoi = right - xRoiPos + 1
                #heightRoi = bottom - yRoiPos + 1
                heightRoi = top - yRoiPos + 1

                # TODO: get this out of replot, recreating the ROI is causing runtime error
                pos = (xRoiPos,yRoiPos)
                size = (widthRoi,heightRoi)
                if self.myLineRoi is None:
                    self.myLineRoi = pg.ROI(pos=pos, size=size, parent=self.myImageItem)
                    self.myLineRoi.addScaleHandle((0,0), (1,1), name='topleft')  # at origin
                    self.myLineRoi.addScaleHandle((0.5,0), (0.5,1))  # top center
                    self.myLineRoi.addScaleHandle((0.5,1), (0.5,0))  # bottom center
                    self.myLineRoi.addScaleHandle((0,0.5), (1,0.5))  # left center
                    self.myLineRoi.addScaleHandle((1,0.5), (0,0.5))  # right center
                    self.myLineRoi.addScaleHandle((1,1), (0,0), name='bottomright')  # bottom right
                    self.myLineRoi.sigRegionChangeFinished.connect(self.kymographChanged)
                else:
                    self.myLineRoi.setPos(pos, finish=False)
                    self.myLineRoi.setSize(size, finish=False)

            # background kymograph ROI
            backgroundRect = self.ba.getKymographBackgroundRect()
            #print('xxx backgroundRect:', backgroundRect)
            if backgroundRect is not None:
                xRoiPos = backgroundRect[0]
                yRoiPos = backgroundRect[1]
                right = backgroundRect[2]
                bottom = backgroundRect[3]
                widthRoi = right - xRoiPos + 1
                heightRoi = bottom - yRoiPos + 1

                # TODO: get this out of replot, recreating the ROI is causing runtime error
                self.myLineRoiBackground = pg.ROI(pos=(xRoiPos,yRoiPos), size=(widthRoi,heightRoi), parent=self.myImageItem)
        '''

        #
        # remove and re-add plot overlays
        for idx, plot in enumerate(self.myPlots):
            plotItem = self.myPlotList[idx]
            if plot['plotOn'] == 'vm':
                self.vmPlot.removeItem(plotItem)
                self.vmPlot.addItem(plotItem)
            elif plot['plotOn'] == 'vmGlobal':
                self.vmPlotGlobal.removeItem(plotItem)
                self.vmPlotGlobal.addItem(plotItem)
            elif plot['plotOn'] == 'dvdt':
                self.derivPlot.removeItem(plotItem)
                self.derivPlot.addItem(plotItem)

        # single spike selection
        '''
        self.vmPlotGlobal.removeItem(self.mySingleSpikeScatterPlot)
        self.vmPlotGlobal.addItem(self.mySingleSpikeScatterPlot)
        self.vmPlot.removeItem(self.mySingleSpikeScatterPlot)
        self.vmPlot.addItem(self.mySingleSpikeScatterPlot)
        '''

        # set full axis
        # setAxisFull was causing start/stop to get over-written
        #self.setAxisFull()
        self.setAxis_OnFileChange(startSec, stopSec)
        #self.detectToolbarWidget.on_start_stop()

        #
        # critical, replot() is inherited
        self.replot()

class kymographImage(pg.ImageItem):
    def mouseClickEvent(self, event):
        #print("Click", event.pos())
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
        print('QtGui.QImageWriter.supportedImageFormats():', QtGui.QImageWriter.supportedImageFormats())

    def widthChanged(self):
        sr = self.getSourceRect()
        ar = float(sr.height()) / sr.width()
        myHeight = int(self.params['width'] * ar)
        self.params.param('height').setValue(myHeight, blockSignal=self.heightChanged)

    def heightChanged(self):
        sr = self.getSourceRect()
        ar = float(sr.width()) / sr.height()
        myWidth = int(self.params['height'] * ar)
        self.params.param('width').setValue(myWidth, blockSignal=self.widthChanged)

class MultiLine(pg.QtGui.QGraphicsPathItem):
    """
    This will display a time-series whole-cell recording efficiently
    It does this by converting the array of points to a QPath

    see: https://stackoverflow.com/questions/17103698/plotting-large-arrays-in-pyqtgraph/17108463#17108463
    """
    def __init__(self, x, y, detectionWidget, type, forcePenColor=None, allowXAxisDrag=True, columnOrder=False):
        """
        x and y are 2D arrays of shape (Nplots, Nsamples)

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

        self.xDrag = None # if true, user is dragging x-axis, otherwise y-axis
        self.xStart = None
        self.xCurrent = None
        self.linearRegionItem = None

        if len(x.shape) == 2:
            connect = np.ones(x.shape, dtype=bool)
            if columnOrder:
                connect[-1,:] = 0 # don't draw the segment between each trace
            else:
                connect[:,-1] = 0 # don't draw the segment between each trace
            self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect.flatten())
        else:
            self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect='all')
        pg.QtGui.QGraphicsPathItem.__init__(self, self.path)

        # holy shit, this is bad, without this the app becomes non responsive???
        # if width > 1.0 then this whole app STALLS
        # default heme
        #self.setPen(pg.mkPen(color='k', width=1))
        # dark theme
        if forcePenColor is not None:
            penColor = forcePenColor
        elif self.detectionWidget.myMainWindow is None:
            penColor = 'k'
        else:
            if self.detectionWidget.myMainWindow.useDarkStyle:
                penColor = 'w'
            else:
                penColor = 'k'
        #
        width = 1
        if self.myType == 'meanclip':
            penColor = 'r'
            width = 3

        #
        self.setPen(pg.mkPen(color=penColor, width=width))

    def shape(self):
        # override because QGraphicsPathItem.shape is too expensive.
        #print(time.time(), 'MultiLine.shape()', pg.QtGui.QGraphicsItem.shape(self))
        return pg.QtGui.QGraphicsItem.shape(self)

    def boundingRect(self):
        #print(time.time(), 'MultiLine.boundingRect()', self.path.boundingRect())
        return self.path.boundingRect()

    def mouseClickEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            print('mouseClickEvent() right click', self.myType)
            self.contextMenuEvent(event)

    def contextMenuEvent(self, event):
        myType = self.myType

        '''
        if myType == 'clip':
            logger.warning('No export for clips, try clicking again')
            return
        '''

        contextMenu = QtWidgets.QMenu()
        exportTraceAction = contextMenu.addAction(f'Export Trace {myType}')
        contextMenu.addSeparator()
        resetAllAxisAction = contextMenu.addAction(f'Reset All Axis')
        resetYAxisAction = contextMenu.addAction(f'Reset Y-Axis')
        #openAct = contextMenu.addAction("Open")
        #quitAct = contextMenu.addAction("Quit")
        #action = contextMenu.exec_(self.mapToGlobal(event.pos()))
        posQPoint = QtCore.QPoint(event.screenPos().x(), event.screenPos().y())
        action = contextMenu.exec_(posQPoint)
        if action is None:
            return
        actionText = action.text()
        if actionText == f'Export Trace {myType}':
            #
            # See: plugins/exportTRace.py
            #

            #print('Opening Export Trace Window')

            if self.myType == 'vmFiltered':
                xyUnits = ('Time (sec)', 'Vm (mV)')# todo: pass xMin,xMax to constructor
            elif self.myType == 'dvdtFiltered':
                xyUnits = ('Time (sec)', 'dV/dt (mV/ms)')# todo: pass xMin,xMax to constructor
            elif self.myType == 'meanclip':
                xyUnits = ('Time (ms)', 'Vm (mV)')# todo: pass xMin,xMax to constructor
            else:
                logger.error(f'Unknown myType: "{self.myType}"')
                xyUnits = ('error time', 'error y')

            path = self.detectionWidget.ba.path

            xMin = None
            xMax = None
            #if self.myType in ['clip', 'meanclip']:
            #    xMin, xMax = self.detectionWidget.clipPlot.getAxis('bottom').range
            #else:
            #    xMin, xMax = self.detectionWidget.getXRange()
            xMin, xMax = self.detectionWidget.getXRange()
            #print('  xMin:', xMin, 'xMax:', xMax)

            if self.myType in ['vm', 'dvdt']:
                xMargin = 2 # seconds
            else:
                xMargin = 2

            exportWidget = sanpy.interface.bExportWidget(self.x, self.y,
                            xyUnits=xyUnits,
                            path=path,
                            xMin=xMin, xMax=xMax,
                            xMargin = xMargin,
                            type=self.myType,
                            darkTheme=self.detectionWidget.useDarkStyle)

            exportWidget.myCloseSignal.connect(self.slot_closeChildWindow)
            exportWidget.show()

            self.exportWidgetList.append(exportWidget)
        elif actionText == 'Reset All Axis':
            #print('Reset Y-Axis', self.myType)
            self.detectionWidget.setAxisFull()
        elif actionText == 'Reset Y-Axis':
            #print('Reset Y-Axis', self.myType)
            self.detectionWidget.setAxisFull_y(self.myType)
        else:
            logger.warning(f'action not taken: {action}')

    def slot_closeChildWindow(self, windowPointer):
        #print('closeChildWindow()', windowPointer)
        #print('  exportWidgetList:', self.exportWidgetList)

        idx = self.exportWidgetList.index(windowPointer)
        if idx is not None:
            popedItem = self.exportWidgetList.pop(idx)
            #print('  popedItem:', popedItem)
        else:
            print(' slot_closeChildWindow() did not find', windowPointer)

    def mouseDragEvent(self, ev):
        """
        default is to drag x-axis, use alt_drag for y-axis
        """
        #print('MultiLine.mouseDragEvent():', type(ev), ev)

        if ev.button() != QtCore.Qt.LeftButton:
            ev.ignore()
            return

        #modifiers = QtWidgets.QApplication.keyboardModifiers()
        #isAlt = modifiers == QtCore.Qt.AltModifier
        isAlt = ev.modifiers() == QtCore.Qt.AltModifier

        #xDrag = not isAlt # x drag is dafault, when alt is pressed, xDrag==False

        # allowXAxisDrag is now used for both x and y
        if not self.allowXAxisDrag:
            ev.accept() # this prevents click+drag of plot
            return

        if ev.isStart():
            self.xDrag = not isAlt
            if self.xDrag:
                self.xStart = ev.buttonDownPos()[0]
                self.linearRegionItem = pg.LinearRegionItem(values=(self.xStart,0), orientation=pg.LinearRegionItem.Vertical)
            else:
                # in y-drag, we need to know (vm, dvdt)
                self.xStart = ev.buttonDownPos()[1]
                self.linearRegionItem = pg.LinearRegionItem(values=(0,self.xStart), orientation=pg.LinearRegionItem.Horizontal)
            #self.linearRegionItem.sigRegionChangeFinished.connect(self.update_x_axis)
            # add the LinearRegionItem to the parent widget (Cannot add to self as it is an item)
            self.parentWidget().addItem(self.linearRegionItem)
        elif ev.isFinish():
            if self.xDrag:
                set_xyBoth = 'xAxis'
            else:
                set_xyBoth = 'yAxis'
            #self.parentWidget().setXRange(self.xStart, self.xCurrent)
            self.detectionWidget.setAxis(self.xStart, self.xCurrent, set_xyBoth=set_xyBoth, whichPlot=self.myType)

            self.xDrag = None
            self.xStart = None
            self.xCurrent = None

            # 20210821, not sure ???
            #if self.myType == 'clip':
            #    if self.xDrag:
            #        self.clipPlot.setXRange(self.xStart, self.xCurrent, padding=padding)
            #    else:
            #        self.clipPlot.setYRange(self.xStart, self.xCurrent, padding=padding)
            #else:
            #    self.parentWidget().removeItem(self.linearRegionItem)
            self.parentWidget().removeItem(self.linearRegionItem)

            # was getting QGraphicsScene::removeItem: item 0x55f2844ff8e0's scene (0x0) is different from this scene (0x55f282051690)
            #self.parentWidget().removeItem(self.linearRegionItem)

            self.linearRegionItem = None

            return

        if self.xDrag:
            self.xCurrent = ev.pos()[0]
            #print('xStart:', self.xStart, 'self.xCurrent:', self.xCurrent)
            self.linearRegionItem.setRegion((self.xStart, self.xCurrent))
        else:
            self.xCurrent = ev.pos()[1]
            #print('xStart:', self.xStart, 'self.xCurrent:', self.xCurrent)
            self.linearRegionItem.setRegion((self.xStart, self.xCurrent))
        ev.accept()

class myDetectToolbarWidget2(QtWidgets.QWidget):
    #signalSelectSpike = QtCore.Signal(object, object) # spike number, doZoom

    def __init__(self, myPlots, detectionWidget : bDetectionWidget, parent=None):
        super(myDetectToolbarWidget2, self).__init__(parent)

        self.myPlots = myPlots
        self.detectionWidget = detectionWidget # parent detection widget

        self._startSec = None
        self._stopSec = None

        self._selectedDetection = None

        self.buildUI()

    def fillInDetectionParameters(self, tableRowDict):
        """
        Set detection widget interface (mostly QSpinBox) to match values from table
        """

        '''
        print('fillInDetectionParameters()')
        print('  tableRowDict:')
        for k,v in tableRowDict.items():
            print('  ', k, ':', v, type(v))
        '''

        try:
            dvdtThreshold = tableRowDict['dvdtThreshold']
            mvThreshold = tableRowDict['mvThreshold']
            startSeconds = tableRowDict['Start(s)']
            stopSeconds = tableRowDict['Stop(s)']
        except (KeyError) as e:
            logger.error(e)
            return
        #logger.info(f'startSeconds:{startSeconds} stopSeconds:{stopSeconds}')

        # in table we specify 'nan' but float spin box will not show that
        if math.isnan(dvdtThreshold):
            windowOptions = self.detectionWidget.getMainWindowOptions()
            dvdtThreshold = windowOptions['detect']['detectDvDt']

        if math.isnan(mvThreshold):
            windowOptions = self.detectionWidget.getMainWindowOptions()
            mvThreshold = windowOptions['detect']['detectMv']

        # print('=== fillInDetectionParameters dvdtThreshold:', dvdtThreshold)
        # print('=== fillInDetectionParameters mvThreshold:', mvThreshold)
        
        self.dvdtThreshold.setValue(dvdtThreshold)
        self.mvThreshold.setValue(mvThreshold)

        if math.isnan(startSeconds):
            startSeconds = 0
        if math.isnan(stopSeconds):
            #stopSeconds = self.detectionWidget.ba.sweepX[-1]
            stopSeconds = self.detectionWidget.ba.recordingDur

        self.startSeconds.setValue(startSeconds)
        self.stopSeconds.setValue(stopSeconds)

    '''
    def sweepSelectionChange(self,i):
        sweepNumber = int(self.cb.currentText())
        print('    todo: implement sweep number:', sweepNumber)
    '''

    def on_detection_preset_change(self, detectionTypeStr):
        """User selected a preset detection.
        
        Fill in preset dv/dt and mV.
        Use this detection preset when user hits detect
        """
        logger.info('')

        # grab default (dv/dt, mv) from preset
        #detectionPreset = sanpy.bDetection.detectionPresets(detectionTypeStr)
        #detectionClass = sanpy.bDetection(detectionPreset=detectionPreset)

        self._selectedDetection = detectionTypeStr
        detectionDict = self.detectionWidget.getMainWindowDetectionClass().getDetectionDict(self._selectedDetection)
        dvdtThreshold = detectionDict['dvdtThreshold']
        mvThreshold = detectionDict['mvThreshold']
        print('    dvdtThreshold:', dvdtThreshold, 'mvThreshold:', mvThreshold)
        
        # set interface
        self.dvdtThreshold.setValue(dvdtThreshold)
        self.mvThreshold.setValue(mvThreshold)

    def on_sweep_change(self, sweepNumber):
        """
        Args:
            sweepNumber (str): The current selected item, from ('All', 0, 1, 2, ...)
        """
        #logger.debug(f'sweepNumber:"{sweepNumber}" {type(sweepNumber)}')
        if sweepNumber == '':
            # we receive this as we rebuild xxx on switching file
            #logger.error('Got empty sweep -- ABORTING')
            return
        logger.info(f'Calling selectSweep() {sweepNumber}')
        self.detectionWidget.selectSweep(sweepNumber)

    def on_sweep_change_2(self, prevNext : str):
        if self.detectionWidget.ba is None:
            return

        if prevNext == 'previous':
            inc = -1
        else:
            inc = +1
        newSweep = self.detectionWidget.sweepNumber
        if newSweep is None:
            return
        else:
            newSweep += inc
        
        if newSweep<0 or newSweep > self.detectionWidget.ba.numSweeps-1:
            return
        
        self.detectionWidget.slot_selectSweep(newSweep)
        #self.detectionWidget.selectSweep(newSweep)

        # update combobox
        #self.sweepComboBox.setCurrentIndex(newSweep+1)

    def slot_selectSweep(self, sweep : int):
        """Fake slot, not ising in emit/connect.
        """
        self.sweepComboBox.setCurrentIndex(sweep+1)

        #self.spikeNumber.setMaximum(+1e6)
        #self.spikeNumber.setValue(0)

    #@QtCore.pyqtSlot()
    def on_start_stop(self):
        start = self.startSeconds.value()
        stop = self.stopSeconds.value()
        
        if (start != self._startSec) or (stop != self._stopSec):
            self._startSec = start
            self._stopSec = stop
            
            logger.info(f'start:{start}, stop:{stop}')
            self.detectionWidget.setAxis(start, stop)

    def on_plot_every(self):
        logger.info('TODO: update plots with plot every.')

    #@QtCore.pyqtSlot()
    def on_button_click(self, name):
        logger.info(name)
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        isShift = modifiers == QtCore.Qt.ShiftModifier

        if name == 'Detect dV/dt':
            detectionPreset = self.detectionPresets.currentText()
            
            dvdtThreshold = self.dvdtThreshold.value()
            #print(f'  dvdtThreshold:', dvdtThreshold, type(dvdtThreshold))
            mvThreshold = self.mvThreshold.value()
            #print('    dvdtThreshold:', dvdtThreshold)
            #print('    mvThreshold:', mvThreshold)
            if dvdtThreshold==0:
                # 0 is special value shown as 'None'
                str = 'Please set a threshold greater than 0'
                self.detectionWidget.updateStatusBar(str)
                return
            startSec = self.startSeconds.value()
            stopSec = self.stopSeconds.value()
            #
            detectionType = sanpy.bDetection.detectionTypes.dvdt
            self.detectionWidget.detect(detectionPreset, detectionType, dvdtThreshold, mvThreshold, startSec, stopSec)

        elif name =='Detect mV':
            dvdtThreshold = self.dvdtThreshold.value()
            mvThreshold = self.mvThreshold.value()
            #print('    mvThreshold:', mvThreshold)
            # passing dvdtThreshold=None we will detect suing mvThreshold

            # was this, switching to detection class
            #dvdtThreshold = None

            #print('    dvdtThreshold:', dvdtThreshold)
            #print('    mvThreshold:', mvThreshold)
            startSec = self.startSeconds.value()
            stopSec = self.stopSeconds.value()
            #
            detectionType = sanpy.bDetection.detectionTypes.mv
            self.detectionWidget.detect(detectionPreset, detectionType, dvdtThreshold, mvThreshold, startSec, stopSec)

        # Reset Axes
        #elif name == 'Reset Axes':
        elif name == '[]':
            self.detectionWidget.setAxisFull()

        elif name == 'Export Spike Report':
            #print('"Save Spike Report" isShift:', isShift)
            self.detectionWidget.save(alsoSaveTxt=isShift)

        # next/previous sweep
        elif name == '<':
            self.on_sweep_change_2('previous')
        elif name == '>':
            self.on_sweep_change_2('next')

        #elif name == 'Explore':
        #    # open bScatterPlot2 for one recording
        #    self.detectionWidget.exploreSpikes()

        #elif name == 'Error':
        #    self.detectionWidget.ba.errorReport()

        elif name == 'Go':
            spikeNumber = self.spikeNumber.value()
            doZoom = isShift
            self.detectionWidget.selectSpike(spikeNumber, doZoom, doEmit=True)

        elif name == '<<':
            spikeNumber = self.spikeNumber.value()
            spikeNumber -= 1
            if spikeNumber < 0:
                spikeNumber = 0
            doZoom = isShift
            self.detectionWidget.selectSpike(spikeNumber, doZoom, doEmit=True)

        elif name == '>>':
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
        #print('on_check_click() text:', checkbox.text(), 'isChecked:', isChecked, 'idx:', idx)
        self.detectionWidget.toggleInterface(idx, isChecked)

    def on_crosshair_clicked(self, value):
        #print('on_crosshair_clicked() value:', value)
        onOff = value==2
        self.detectionWidget.toggleCrosshair(onOff)

    def toggleInterface(self, panelName : str, onoff : bool):
        """Toggle interface panels on/off.
        """

        if panelName == 'Detection':
            if onoff:
                self.detectionGroupBox.show()
            else:
                self.detectionGroupBox.hide()
        elif panelName == 'Display':
            if onoff:
                self.displayGroupBox.show()
            else:
                self.displayGroupBox.hide()
        elif panelName == 'Plot Options':
            if onoff:
                self.plotGroupBox.show()
            else:
                self.plotGroupBox.hide()

        else:
            logger.warning(f'did not understand panelName "{panelName}"')

    def buildUI(self):
        #self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))

        myPath = os.path.dirname(os.path.abspath(__file__))

        windowOptions = self.detectionWidget.getMainWindowOptions()
        detectDvDt = 20
        detectMv = -20
        showGlobalVm = True
        showDvDt = True
        showDAC = True
        #showClips = False
        #showScatter = True
        if windowOptions is not None:
            detectDvDt = windowOptions['detect']['detectDvDt']
            detectMv = windowOptions['detect']['detectMv']

            showDvDt = windowOptions['rawDataPanels']['Derivative']
            showDAC = windowOptions['rawDataPanels']['DAC']
            showGlobalVm = windowOptions['rawDataPanels']['Full Recording']
            #showClips = windowOptions['display']['showClips']
            #showScatter = windowOptions['display']['showScatter']
            #showErrors = windowOptions['display']['showErrors']

        self.setFixedWidth(300)

        # why do I need self here?
        self.mainLayout = QtWidgets.QVBoxLayout()

        self.mainLayout.setAlignment(QtCore.Qt.AlignTop)

        # Show selected file
        self.mySelectedFileLabel = QtWidgets.QLabel('None')
        self.mainLayout.addWidget(self.mySelectedFileLabel)

        #
        # detection parameters group
        self.detectionGroupBox = QtWidgets.QGroupBox('Detection')

        # breeze
        #detectionGroupBox.setStyleSheet(myStyleSheet)

        #detectionGroupBox.setAlignment(QtCore.Qt.AlignTop)

        detectionGridLayout = QtWidgets.QGridLayout()
        #detectionGridLayout.setAlignment(QtCore.Qt.AlignTop)

        row = 0
        rowSpan = 1
        columnSpan = 2

        aComboLabel = QtWidgets.QLabel('Presets')
        
        # get list of detection presets
        #detectionTypes = sanpy.bDetection.getDetectionPresetList()
        detectionClass = self.detectionWidget.getMainWindowDetectionClass()
        detectionTypes = detectionClass.getDetectionPresetList()
        
        self._selectedDetection = detectionTypes[0]  # set to the first detection type

        self.detectionPresets = QtWidgets.QComboBox()
        for detectionType in detectionTypes:
            self.detectionPresets.addItem(detectionType)
        self.detectionPresets.currentTextChanged.connect(self.on_detection_preset_change)

        columnSpan = 1
        detectionGridLayout.addWidget(aComboLabel, row, 0, rowSpan, columnSpan)
        columnSpan = 3
        detectionGridLayout.addWidget(self.detectionPresets, row, 1, rowSpan, columnSpan)
        row += 1

        #
        buttonName = 'Detect dV/dt'
        button = QtWidgets.QPushButton(buttonName)
        button.setToolTip('Detect spikes using dV/dt threshold.')
        button.clicked.connect(partial(self.on_button_click,buttonName))

        #row = 0
        rowSpan = 1
        columnSpan = 2
        detectionGridLayout.addWidget(button, row, 0, rowSpan, columnSpan)

        self.dvdtThreshold = QtWidgets.QDoubleSpinBox()
        self.dvdtThreshold.setMinimum(0)
        self.dvdtThreshold.setMaximum(+1e6)
        self.dvdtThreshold.setValue(detectDvDt)
        self.dvdtThreshold.setSpecialValueText("None")
        #self.dvdtThreshold.setValue(np.nan)
        detectionGridLayout.addWidget(self.dvdtThreshold, row, 2, rowSpan, columnSpan)

        row += 1
        rowSpan = 1
        columnSpan = 2
        buttonName = 'Detect mV'
        button = QtWidgets.QPushButton(buttonName)
        button.setToolTip('Detect spikes using mV threshold.')
        button.clicked.connect(partial(self.on_button_click,buttonName))
        detectionGridLayout.addWidget(button, row, 0, rowSpan, columnSpan)

        # Vm Threshold (mV)
        #mvThresholdLabel = QtWidgets.QLabel('Vm Threshold (mV)')
        #self.addWidget(mvThresholdLabel, row, 1)

        #row += 1
        self.mvThreshold = QtWidgets.QDoubleSpinBox()
        self.mvThreshold.setMinimum(-1e6)
        self.mvThreshold.setMaximum(+1e6)
        self.mvThreshold.setValue(detectMv)
        detectionGridLayout.addWidget(self.mvThreshold, row, 2, rowSpan, columnSpan)

        #tmpRowSpan = 1
        #tmpColSpan = 2
        row += 1
        startSeconds = QtWidgets.QLabel('From (s)')
        detectionGridLayout.addWidget(startSeconds, row, 0)
        #
        self.startSeconds = QtWidgets.QDoubleSpinBox()
        self.startSeconds.setMinimum(-1e6)
        self.startSeconds.setMaximum(+1e6)
        self.startSeconds.setKeyboardTracking(False)
        self.startSeconds.setValue(0)
        #self.startSeconds.valueChanged.connect(self.on_start_stop)
        self.startSeconds.editingFinished.connect(self.on_start_stop)
        detectionGridLayout.addWidget(self.startSeconds, row, 1)
        #
        stopSeconds = QtWidgets.QLabel('To (s)')
        detectionGridLayout.addWidget(stopSeconds, row, 2)

        self.stopSeconds = QtWidgets.QDoubleSpinBox()
        self.stopSeconds.setMinimum(-1e6)
        self.stopSeconds.setMaximum(+1e6)
        self.stopSeconds.setKeyboardTracking(False)
        self.stopSeconds.setValue(0)
        #self.stopSeconds.valueChanged.connect(self.on_start_stop)
        self.stopSeconds.editingFinished.connect(self.on_start_stop)
        detectionGridLayout.addWidget(self.stopSeconds, row, 3)

        row += 1
        tmpHLayout = QtWidgets.QHBoxLayout()

        self.numSpikesLabel = QtWidgets.QLabel('Spikes: None')
        tmpHLayout.addWidget(self.numSpikesLabel)
        #detectionGridLayout.addWidget(self.numSpikesLabel, row, 0, tmpRowSpan, tmpColSpan)

        self.spikeFreqLabel = QtWidgets.QLabel('Freq: None')
        tmpHLayout.addWidget(self.spikeFreqLabel)
        #detectionGridLayout.addWidget(self.spikeFreqLabel, row, 1, tmpRowSpan, tmpColSpan)

        self.numErrorsLabel = QtWidgets.QLabel('Errors: None')
        tmpHLayout.addWidget(self.numErrorsLabel)
        #detectionGridLayout.addWidget(self.numErrorsLabel, row, 2, tmpRowSpan, tmpColSpan)
        col = 0
        rowSpan=1
        colSpan = 4
        detectionGridLayout.addLayout(tmpHLayout, row, col, rowSpan, colSpan)

        row += 1
        buttonName = 'Export Spike Report'
        button = QtWidgets.QPushButton(buttonName)
        button.setToolTip('Save Detected Spikes to Excel file')
        #button.setStyleSheet("background-color: green")
        button.clicked.connect(partial(self.on_button_click,buttonName))
        rowSpan=1
        colSpan = 4
        detectionGridLayout.addWidget(button, row , 0, rowSpan, colSpan)

        # finalize
        self.detectionGroupBox.setLayout(detectionGridLayout)
        self.mainLayout.addWidget(self.detectionGroupBox)

        #
        # display group
        self.displayGroupBox = QtWidgets.QGroupBox('Display')
        
        displayGridLayout = QtWidgets.QGridLayout()

        row = 0
        # sweeps
        tmpSweepLabel = QtWidgets.QLabel('Sweep')
        buttonName = '<'
        self.previousSweepButton = QtWidgets.QPushButton(buttonName)
        self.previousSweepButton.clicked.connect(partial(self.on_button_click,buttonName))
        buttonName = '>'
        self.nextSweepButton = QtWidgets.QPushButton(buttonName)
        self.nextSweepButton.clicked.connect(partial(self.on_button_click,buttonName))

        self.sweepComboBox = QtWidgets.QComboBox()
        self.sweepComboBox.currentTextChanged.connect(self.on_sweep_change)
        # will be set in self.slot_selectFile()
        #for sweep in range(self.detectionWidget.ba.numSweeps):
        #    self.sweepComboBox.addItem(str(sweep))
        hSweepLayout = QtWidgets.QHBoxLayout()
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
        '''
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
        '''

        row += 1
        self.crossHairCheckBox = QtWidgets.QCheckBox('Crosshair')
        self.crossHairCheckBox.setChecked(False)
        self.crossHairCheckBox.stateChanged.connect(self.on_crosshair_clicked)
        tmpRowSpan = 1
        tmpColSpan = 1
        displayGridLayout.addWidget(self.crossHairCheckBox, row, 0, tmpRowSpan, tmpColSpan)

        # x/y coordinates of mouse in each of derivPlot, vmPlot, clipPlot)
        self.mousePositionLabel = QtWidgets.QLabel('x:None\ty:None')
        displayGridLayout.addWidget(self.mousePositionLabel, row, 1, tmpRowSpan, tmpColSpan)

        hBoxSpikeBrowser = self._buildSpikeBrowser()  # includes (Spike, Go, <<, >>, [])
        row += 1
        rowSpan = 1
        columnSpan = 2
        displayGridLayout.addLayout(hBoxSpikeBrowser, row, 0, rowSpan, columnSpan)

        # finalize
        self.displayGroupBox.setLayout(displayGridLayout)
        self.mainLayout.addWidget(self.displayGroupBox)

        #
        # plots  group
        self.plotGroupBox = QtWidgets.QGroupBox('Plot Options')

        # breeze
        #plotGroupBox.setStyleSheet(myStyleSheet)

        plotGridLayout = QtWidgets.QGridLayout()

        row = 0

        # add widgets
        '''
        row = 0
        col = 0
        aCheckbox = QtWidgets.QCheckBox('Global Vm')
        aCheckbox.setChecked(showGlobalVm)
        aCheckbox.stateChanged.connect(partial(self.on_check_click,aCheckbox,'Global Vm'))
        plotGridLayout.addWidget(aCheckbox, row, col)
        '''

        '''
        row = 0
        col += 1
        show_dvdt_checkbox = QtWidgets.QCheckBox('dV/dt')
        show_dvdt_checkbox.setChecked(showDvDt)
        show_dvdt_checkbox.stateChanged.connect(partial(self.on_check_click,show_dvdt_checkbox,'dV/dt'))
        plotGridLayout.addWidget(show_dvdt_checkbox, row, col)
        '''

        '''
        row = 0
        col += 1
        show_dac_checkbox = QtWidgets.QCheckBox('DAC')
        show_dac_checkbox.setChecked(showDAC)
        show_dac_checkbox.stateChanged.connect(partial(self.on_check_click,show_dac_checkbox,'DAC'))
        plotGridLayout.addWidget(show_dac_checkbox, row, col)
        '''

        # a number of stats that will get overlaid on dv/dt and Vm
        #row += 1
        row += 1
        col = 0
        for idx, plot in enumerate(self.myPlots):
            #print('humanName:', plot['humanName'])
            humanName = plot['humanName']
            isChecked = plot['plotIsOn']
            styleColor = plot['styleColor']
            checkbox = QtWidgets.QCheckBox(humanName)
            checkbox.setChecked(isChecked)
            #checkbox.setStyleSheet(styleColor) # looks really ugly
            #checkbox.stateChanged.connect(lambda:self.on_check_click(checkbox))
            checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,idx))
            # append
            plotGridLayout.addWidget(checkbox, row, col)
            # increment
            col += 1
            if col == 2: # we only have col 0/1, nx2 grid
                col = 0
                row += 1

        '''
        row = 0
        col += 1
        checkbox = QtWidgets.QCheckBox('Clips')
        checkbox.setChecked(showClips)
        checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Clips'))
        plotGridLayout.addWidget(checkbox, row, col)
        '''

        '''
        row = 0
        col += 1
        checkbox = QtWidgets.QCheckBox('Scatter')
        checkbox.setChecked(showScatter)
        checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Scatter'))
        plotGridLayout.addWidget(checkbox, row, col)
        '''

        '''
        row = 0
        col += 1
        checkbox = QtWidgets.QCheckBox('Errors')
        checkbox.setChecked(showErrors)
        checkbox.stateChanged.connect(partial(self.on_check_click,checkbox,'Errors'))
        plotGridLayout.addWidget(checkbox, row, col)
        '''

        # finalize
        self.plotGroupBox.setLayout(plotGridLayout)
        self.mainLayout.addWidget(self.plotGroupBox)


        # finalize
        self.setLayout(self.mainLayout)

    def on_spike_number(self, spikeNumber):
        logger.info(f'!!! THIS IS A PROBLEM spikeNumber:{spikeNumber}')
        doZoom = False
        self.detectionWidget.selectSpike(spikeNumber, doZoom, doEmit=True)

    def _buildSpikeBrowser(self):
        """Build interface to go to spike number, previous <<, and next >>"""
        hBoxSpikeBrowser = QtWidgets.QHBoxLayout()

        aLabel = QtWidgets.QLabel('Spike')
        hBoxSpikeBrowser.addWidget(aLabel)

        # absolute spike number
        self.spikeNumber = QtWidgets.QSpinBox()
        self.spikeNumber.setMinimum(0)
        self.spikeNumber.setMaximum(+1e6)
        self.spikeNumber.setKeyboardTracking(False)
        self.spikeNumber.setValue(0)
        self.spikeNumber.valueChanged.connect(self.on_spike_number)
        #self.spikeNumber.editingFinished.connect(self.on_spike_number)
        #self.spikeNumber.setKeyboardTracking(False)

        hBoxSpikeBrowser.addWidget(self.spikeNumber)

        buttonName = 'Go'
        button = QtWidgets.QPushButton(buttonName)
        button.setToolTip('Go To Spike Number')
        button.clicked.connect(partial(self.on_button_click,buttonName))
        hBoxSpikeBrowser.addWidget(button)

        buttonName = '<<'
        button = QtWidgets.QPushButton(buttonName)
        button.setToolTip('Previous Spike')
        button.clicked.connect(partial(self.on_button_click,buttonName))
        hBoxSpikeBrowser.addWidget(button)

        buttonName = '>>'
        button = QtWidgets.QPushButton(buttonName)
        button.setToolTip('Next Spike')
        button.clicked.connect(partial(self.on_button_click,buttonName))
        hBoxSpikeBrowser.addWidget(button)

        buttonName = '[]'
        button = QtWidgets.QPushButton(buttonName)
        button.clicked.connect(partial(self.on_button_click,buttonName))
        hBoxSpikeBrowser.addWidget(button)

        return hBoxSpikeBrowser

    def setMousePositionLabel(self, x, y):
        if x is not None:
            x = round(x,4) # 4 to get 10kHz precision, 0.0001
        if y is not None:
            y = round(y,2)
        labelStr = f'x:{x}   y:{y}'
        self.mousePositionLabel.setText(labelStr)
        self.mousePositionLabel.repaint()

    def slot_selectSpike(self, sDict):
        logger.info(f'detectiontoolbar widget: sDict:{sDict}')
        spikeNumber = sDict['spikeNumber']
        # don't respond to a list of spikes
        if isinstance(spikeNumber, list):
            return
        # arbitrarily chosing spike 0 when no spike selection
        # spin boxes can not have 'no value'
        if spikeNumber is None:
            spikeNumber = 0
        
        # convert absolute to sweep
        sweepSpike = self.detectionWidget.ba.getSweepSpikeFromAbsolute(spikeNumber, self.detectionWidget.sweepNumber)
        
        '''
        print('    !!!! self.detectionWidget.sweepNumber:', self.detectionWidget.sweepNumber)
        print('    !!!! spikeNumber:', spikeNumber)
        print('    !!!! sweepSpike:', sweepSpike)
        '''

        # need to blockSignal or else this emits to callback
        self.spikeNumber.blockSignals(True)
        self.spikeNumber.setValue(spikeNumber)
        self.spikeNumber.blockSignals(False)

        self.spikeNumber.update()

    def slot_selectFile(self, rowDict):
        file = rowDict['File']
        self.mySelectedFileLabel.setText(file)

        # handled in fill in detection parameters
        # set start(s) stop(s)
        '''
        startSec = rowDict['Start(s)']
        stopSec = rowDict['Stop(s)']
        logger.info(f'setting startSec:"{stopSec}" {type(startSec)}')
        logger.info(f'setting stopSec:"{stopSec}" {type(stopSec)}')
        if isinstance(startSec, float):
            self.startSeconds.setValue(startSec)
        if isinstance(stopSec, float):
            self.stopSeconds.setValue(stopSec)
        '''

        # block signals as we update
        self.sweepComboBox.blockSignals(True)
        #

        # populate sweep combo box
        self.sweepComboBox.clear()
        self.sweepComboBox.addItem('All')
        for sweep in range(self.detectionWidget.ba.numSweeps):
            self.sweepComboBox.addItem(str(sweep))
        # always select sweep 0
        self.sweepComboBox.setCurrentIndex(1)
        #if self.detectionWidget.ba.numSweeps == 1:
        #    # select sweep 0
        #    self.sweepComboBox.setCurrentIndex(1)

        # turn off sweep combo box if just one sweep
        enableSweepButtons = self.detectionWidget.ba.numSweeps > 1
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
        """
        User has edited main file table.

        Update detection widget for columns (Start(s), Stop(s), dvdtThreshold, mvThreshold)
        """
        logger.info(f'{columnName} {value} {type(value)}')

        #for k,v in rowDict.items():
        #    print(f'  {k}:"{v}" {type(v)}')

        if columnName is not None:
            # user has made a change in one cell
            if columnName == 'dvdtThreshold':
                if value is None or math.isnan(value):
                    value = -1
                self.dvdtThreshold.setValue(value)
            elif columnName == 'mvThreshold':
                self.mvThreshold.setValue(value)
            elif columnName == 'Start(s)' and not math.isnan(value):
                self.startSeconds.setValue(value)
            elif columnName == 'Stop(s)' and not math.isnan(value):
                self.stopSeconds.setValue(value)
        else:
            # entire row has updated
            dvdtThreshold = rowDict['dvdtThreshold']
            # I really need to make 'no value' np.nan
            if dvdtThreshold is None or math.isnan(dvdtThreshold):
                dvdtThreshold = 0  # 0 corresponds to 'None'
            self.dvdtThreshold.setValue(dvdtThreshold)
            mvThreshold = rowDict['mvThreshold']
            self.mvThreshold.setValue(mvThreshold)
            startSeconds = rowDict['Start(s)']
            if not math.isnan(startSeconds):
                self.startSeconds.setValue(startSeconds)
            stopSeconds = rowDict['Stop(s)']
            if not math.isnan(stopSeconds):
                self.stopSeconds.setValue(stopSeconds)

if __name__ == '__main__':
    # load a bAnalysis file

    #abfFile = '/Users/cudmore/Sites/bAnalysis/data/19221021.abf'
    #abfFile = '/Users/cudmore/Sites/bAnalysis/data/19114001.abf'
    path = '/media/cudmore/data/Laura-data/manuscript-data/2020_06_23_0006.abf'
    path = '../data/19114001.abf'
    path = '/media/cudmore/data/rabbit-ca-transient/Control/220110n_0003.tif.frames/220110n_0003.tif'

    ba = sanpy.bAnalysis(path)

    app = QtWidgets.QApplication(sys.argv)
    w = bDetectionWidget()
    w.slot_switchFile(ba=ba)

    detectionType = sanpy.bDetection.detectionTypes.mv
    dvdtThreshold = 10
    mvThreshold = 1000  # -20
    #w.detect(detectionType, dvdtThreshold, mvThreshold)

    w.show()

    sys.exit(app.exec_())
