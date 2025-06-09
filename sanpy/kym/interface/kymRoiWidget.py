import os
from functools import partial
import json

import numpy as np

from PyQt5 import QtGui, QtCore, QtWidgets
import pyqtgraph as pg

# import sanpy

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, PeakDetectionTypes
from sanpy.kym.kymRoiDetection import KymRoiDetection

from sanpy.kym.interface.kymRoiImageWidget import KymRoiImageWidget
from sanpy.kym.interface.kymDetectionToolbar import KymDetectionGroupBox_Intensity, KymDetectionGroupBox_Diameter
from sanpy.kym.interface.kymRoiToolbar import KymRoiGroupBox  # abb 202505
from sanpy.kym.interface.kymDiamToolbar import KymDiameterToolbar
from sanpy.kym.interface.kymPlotWidget import KymPlotWidget  # new 20241014
from sanpy.kym.interface.kymRoiSetF0Widget import SetF0Widget
from sanpy.kym.interface.kymRoiMetaDataWidget import MetaDataWidget
from sanpy.kym.interface.kymRoiScatter import SimpleRoiScatter
from sanpy.kym.interface.kymRoiClipsWidget import KymRoiClipsWidget

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class KymRoiWidget(QtWidgets.QMainWindow):
    signalRoiSumChanged = QtCore.pyqtSignal(int, object)  # (channel, roiLabel)
    signalRoiDiameterChanged = QtCore.pyqtSignal(int, object)  # (channel, roiLabel)
    # signalRoiSelected = QtCore.pyqtSignal(int, object)  # (channel, roiLabel)
    signalSwitchChannel = QtCore.pyqtSignal(object)  # xxx
    
    _pgAxisLabelFontSize = 12
    """Specify font size for all pg plots.
    """

    def __init__(self, kymRoiAnalysis : KymRoiAnalysis):
        super().__init__(None)
        
        self._kymRoiAnalysis = kymRoiAnalysis

        # this switches for each selected ROI
        self._detectionParams : KymRoiDetection = KymRoiDetection(PeakDetectionTypes.intensity)
        
        self._detectionParamsDiameter : KymRoiDetection = KymRoiDetection(PeakDetectionTypes.diameter)
        self._detectionParamsDiameter.setParam('Exponential Detrend', False)

        # self._blockSlots = False
        
        self._buildUI()

        # re-wire right-click (for entire widget)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu)

        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)

        self.setWindowTitle(self.path)

        self.loadAnalysis()  # load from folder with text file analysis (if it exists)

        # self.font_change()

    # def font_change(self):
    #     font, ok = QtWidgets.QFontDialog.getFont()
    #     if ok:
    #         for name, obj in self.getmembers(self):
    #             if isinstance(obj, QtWidgets.QLabel):
    #                 obj.setFont(font)

    def getSelectedRoiLabel(self) -> str:
        return self._kymRoiImageWidget.getSelectedRoiLabel()

    def slot_detectionChanged(self, detectionType : str, detectionDict : KymRoiDetection):
        """Put this here so we can turn off detection when value changes.
        """
        auto = detectionDict.getParam('Auto')
        logger.info(f'detectionType:{detectionType} auto:{auto}')
        if auto:
            self.slot_doAnalysis(detectionType)

    def slot_doAnalysis(self, detectionType : str):
        """Perform analysis based on which detection gui emitted the signal.
        
        Either detect in intensity or detect in diam.
        """
        logger.info(f'detectionType: {detectionType}')

        if detectionType == 'Detect Peaks (Intensity)':
            roiLabel = self._kymRoiImageWidget.getSelectedRoiLabel()
            ok = self.analyzeRoi(roiLabel, PeakDetectionTypes.intensity)  # analyze the selected ROI
            if ok is not None:
                self.updateRoiIntensityPlot(roiLabel, doAnalysis=False)
        
        elif detectionType == 'Detect Diameter':
            # detect diameter from kym image
            roiLabel = self._kymRoiImageWidget.getSelectedRoiLabel()
            self.updateRoiDiameterPlot(roiLabel, doAnalysis=True)
            logger.warning(f'   -->> signalRoiDiameterChanged.emit with self.currentChannel:{self.currentChannel} roiLabel:{roiLabel}')
            self.signalRoiDiameterChanged.emit(self.currentChannel, roiLabel)

        elif detectionType == 'Detect Peaks (Diameter)':
            # detect peaks in 'Diameter (um)'
            roiLabel = self._kymRoiImageWidget.getSelectedRoiLabel()
            ok = self.analyzeRoi(roiLabel, PeakDetectionTypes.diameter)  # analyze the selected ROI
            if ok is not None:
                # update overlay of diameter plot (e.g. peak, threshold, etc)
                # roi = self.roiList.selectedRoi
                # self.updateRoiDiameterPlot2(roiLabel)

                # roi = self.roiList.selectedRoi
                # roiLabel = self.getRoiLabel(roi)
                logger.warning(f'   -->> signalRoiDiameterChanged.emit with self.currentChannel:{self.currentChannel} roiLabel:{roiLabel}')
                self.signalRoiDiameterChanged.emit(self.currentChannel, roiLabel)

        else:
            logger.error(f'did not understand detectionType:{detectionType}')

    @property
    def currentChannel(self):
        return self._kymRoiImageWidget._currentChannel
    
    def switchChannel(self, channel):
        logger.info(f'channel:{channel} {type(channel)}')
        
        # not used
        # self.signalSwitchChannel.emit(channel)

        # cancel selection
        # self.selectRoi(roi = None)

    def isDirty(self):
        return self._kymRoiAnalysis._isDirty

    def closeEvent(self, event):
        logger.info('veto close if peak analysis is dirty')
        acceptAndContinue = True
        if self.isDirty():
            logger.info('   kym peak analysis is dirty, prompt to save')

            from sanpy.interface.bDialog import yesNoCancelDialog
            # saveDialog = yesNoCancelDialog('xxx is dirty', 'yyy save?')

            userResp = yesNoCancelDialog(
                "There is analysis that is not saved.\nDo you want to save?"
            )
            if userResp == QtWidgets.QMessageBox.Yes:
                # self.saveFilesTable()
                logger.warning('TODO: actually save kym roi peaks')
                self.saveAnalysis()
                acceptAndContinue = True
            elif userResp == QtWidgets.QMessageBox.No:
                acceptAndContinue = True
            else:  # userResp == QtWidgets.QMessageBox.Cancel:
                acceptAndContinue = False
        #
        # return acceptAndContinue
        if acceptAndContinue:
            event.accept()
        else:
            event.ignore()

    def loadAnalysis(self):
        """Load and add each roi in _kymRoiAnalysis
        """
        # logger.info(self._kymRoiAnalysis._roiDict.items())
        for _idx, (roiLabel, kymRoi) in enumerate(self._kymRoiAnalysis._roiDict.items()):
            ltrb = kymRoi.getRect()
            logger.info(f'adding roi {roiLabel} with rect {ltrb}')
            # self.addRoi(ltrb, doAnalysis=False, doSelect=False)

            # add a pg.ROI
            _pgRoi = self._kymRoiImageWidget._addRoi(kymRoi)  # add roi to gui    

            doSelect = _idx == 0
            if doSelect:
                # select the first roi
                self.updateRoiIntensityPlot(roiLabel, doAnalysis=False)

    @property
    def path(self):
        return self._kymRoiAnalysis.path
    
    @property
    def imgData(self) -> np.ndarray:
        """Get image data for one image channel.
        """
        return self._kymRoiAnalysis.getImageChannel(self.currentChannel)
    
    def mySetStatusbar(self, text : str):
        """Update the status bar with some text.
        """
        self.statusBar.showMessage(text)  # ,2000)

    def slot_selectRoi(self, channel : int, roiLabel : str):
        """On selection of an ROI, we set the f_f0 and diameter detection members.

        If roi is None then deselect all.
        """
        logger.info(f'DOES NOTHING roi:"{roiLabel}"')

        # if roiLabel is not None:
        #     # set our detection params to the selected roi
        #     self._detectionParams = self._kymRoiAnalysis.getDetectionParams(roiLabel, PeakDetectionTypes.intensity, self.currentChannel)
        #     self._detectionParamsDiameter = self._kymRoiAnalysis.getDetectionParams(roiLabel, PeakDetectionTypes.diameter, self.currentChannel)

        #     self._updateDetectionParamGui()

        # self.updateRoiDiameterPlot(roiLabel, doAnalysis=False)
        
        # logger.warning(f'   -->> signalRoiSelected.emit with self.currentChannel:{self.currentChannel} {type(roiLabel)}')
        # self.signalRoiSelected.emit(self.currentChannel, roiLabel)

    def _updateDetectionParamGui(self):
        """Update gui for KymDetectionToolbar.
        """
        logger.info('')
        # self._detectionToolbar.setDetectionDict(self._detectionParams)
        # self._diamDetectionToolbar.setDetectionDict(self._detectionParamsDiameter)
        # self._kymDiamDetectToolbar.setDetectionDict(self._detectionParamsDiameter)

    def _buildTopToolbar(self) -> QtWidgets.QVBoxLayout:
        vBoxLayout = QtWidgets.QVBoxLayout()
        vBoxLayout.setAlignment(QtCore.Qt.AlignTop)
        
        hLayout = QtWidgets.QHBoxLayout()
        hLayout.setAlignment(QtCore.Qt.AlignLeft)
        vBoxLayout.addLayout(hLayout)

        buttonName = 'Save Analysis'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Save analysis for all roi(s)')
        aButton.clicked.connect(
            self.saveAnalysis
        )
        hLayout.addWidget(aButton)

        buttonName = 'Load'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Save analysis for all roi(s)')
        aButton.clicked.connect(
            self.saveAnalysis
        )
        hLayout.addWidget(aButton)

        # second row
        # hLayout1 = QtWidgets.QHBoxLayout()
        # hLayout1.setAlignment(QtCore.Qt.AlignLeft)
        # vBoxLayout.addLayout(hLayout1)

        aCheckBoxName = 'Detection'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle detection panel on/off')
        aCheckBox.setChecked(True)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout.addWidget(aCheckBox)

        aCheckBoxName = 'Clips'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle peak clips on/off')
        aCheckBox.setChecked(False)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout.addWidget(aCheckBox)

        aCheckBoxName = 'Scatter'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip('Toggle scatter plot on/off')
        aCheckBox.setChecked(False)  # show by default
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout.addWidget(aCheckBox)

        # show intensity under cursor
        # TODO: put this somewhere better
        # self.hoverLabel = QtWidgets.QLabel(None)
        # hLayout1.addWidget(self.hoverLabel, alignment=QtCore.Qt.AlignRight)

        return vBoxLayout
    
    def _on_combobox(self, name, value):
        """
        Parameters
        ----------
        detectionDict : dict
            Switches between multiple detection group boxes like (detect int, detect diam)
        """
        # if self._blockSlots:
        #     # logger.warning(f'_blockSlots -->> no update for {name} {value}')
        #     return
        
        logger.info(f'"{name}" value:{value}')
        
        if name == 'Channel':
            self.switchChannel(value)

    def setWidgetVisible(self, name : str, visible : bool):
        """Slot responding to child requesting to hid/show a widget.
        """
        if name == 'f0':
            # self.rawIntensityPlotItem.setVisible(visible)
            self._setf0Widget.setVisible(visible)

        elif name == 'Intensity':
            self.sumIntensityPlotItem.setVisible(visible)

        elif name == 'Diameter':
            self.diameterPlotItem.setVisible(visible)

        else:
            logger.warning(f'did not understand name:"{name}"')

    def _on_checkbox_clicked(self, name, value = None):
        # if self._blockSlots:
        #     # logger.warning(f'_blockSlots -->> no update for {name} {value}')
        #     return

        if value > 0:
            value = 1
        logger.info(f'"{name}" {value}')
        
        # show/hide widgets
        # if name == 'Contrast':
        #     self._contrastSliders.setVisible(value)

        # if name == 'Sum Intensity (f0)':
        #     self.rawIntensityPlotItem.setVisible(value)

        # elif name == 'Diameter':
        #     self.diameterPlotItem.setVisible(value)

        if name == 'Clips':
            self.peakClipsWidget.setVisible(value)

        elif name == 'Scatter':
            self.simpleScatter.setVisible(value)

        # elif name == 'ROI':
        #     # toggle all roi
        #     self._kymRoiImageWidget._toggleROI(value)

        elif name == 'Detection':
            self._tabwidget.setVisible(value)

        else:
            logger.info(f'did not understand name:"{name}"')

    def _buildUI(self):
        # self.setContentsMargins(0, 0, 0, 0)

        self.myVBoxLayout = QtWidgets.QVBoxLayout()
        self.myVBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        # needed for QMainWindow
        mainWidget = QtWidgets.QWidget()
        mainWidget.setLayout(self.myVBoxLayout)
        self.setCentralWidget(mainWidget)

        mainHBox = QtWidgets.QHBoxLayout()  # left is detection, right is plots
        self.myVBoxLayout.addLayout(mainHBox)
        
        # vBoxPlot is buttons, then all the plots
        vBoxPlot = QtWidgets.QVBoxLayout()
        vBoxPlot.setAlignment(QtCore.Qt.AlignTop)
        mainHBox.addLayout(vBoxPlot)

        _topToolbar = self._buildTopToolbar()
        vBoxPlot.addLayout(_topToolbar)

        # 20241024 using KymRoiImageWidget
        self._kymRoiImageWidget = KymRoiImageWidget(self._kymRoiAnalysis, self)
        self._kymRoiImageWidget.signalSelectRoi.connect(self.slot_selectRoi)
        self._kymRoiImageWidget.signalRoiChanged.connect(self.slot_roiChanged)
        vBoxPlot.addWidget(self._kymRoiImageWidget)

        # new 20241109 (replaces rawIntensityPlotItem)
        self._setf0Widget = SetF0Widget(self._kymRoiAnalysis)
        self._setf0Widget.setVisible(False)  # hidden by default
        self._setf0Widget._setXLink(self._kymRoiImageWidget.kymographPlot)
        self._setf0Widget.signalUpdateF0.connect(self.slot_f0_changed)  # !!!
        self._kymRoiImageWidget.signalSelectRoi.connect(self._setf0Widget.slot_selectRoi)
        self.signalRoiSumChanged.connect(self._setf0Widget.slot_selectRoi)
        self._kymRoiImageWidget.signalSetLineProfile.connect(self._setf0Widget.slot_updateLineProfile)
        vBoxPlot.addWidget(self._setf0Widget)

        #
        # 4) sum intensity of each line scan (actually our int/f0 plot)
        self.sumIntensityPlotItem = KymPlotWidget(self._kymRoiAnalysis,
                                                  xTrace='Time (s)',
                                                  yTrace='f/f0',
                                                  peakDetectionType=PeakDetectionTypes.intensity)
        # self.sumIntensityPlotItem.sumIntensityPlotItem.setLabel("left", 'Santana Intensity (f/f0)', units="")
        self.sumIntensityPlotItem.setXLink(self._kymRoiImageWidget.kymographPlot)
        self.sumIntensityPlotItem.signalCursorMove.connect(self.mySetStatusbar)
        #
        self.signalRoiSumChanged.connect(self.sumIntensityPlotItem.slot_selectRoi)
        # self.signalRoiSelected.connect(self.sumIntensityPlotItem.slot_selectRoi)
        self._kymRoiImageWidget.signalSetLineProfile.connect(self.sumIntensityPlotItem.slot_updateLineProfile)
        self._kymRoiImageWidget.signalSelectRoi.connect(self.sumIntensityPlotItem.slot_selectRoi)
        vBoxPlot.addWidget(self.sumIntensityPlotItem)

        # diameter plot
        self.diameterPlotItem = KymPlotWidget(self._kymRoiAnalysis,
                                              xTrace='Time (s)',
                                              yTrace='Diameter (um)',
                                              peakDetectionType=PeakDetectionTypes.diameter)
        self.diameterPlotItem.setVisible(False)  # off by default
        # self.diameterPlotItem.sumIntensityPlotItem.setLabel("left", 'Dimaeter (um)', units="")
        self.diameterPlotItem.setXLink(self._kymRoiImageWidget.kymographPlot)
        self.diameterPlotItem.signalCursorMove.connect(self.mySetStatusbar)
        #
        self.signalRoiDiameterChanged.connect(self.diameterPlotItem.slot_selectRoi)
        # self.signalRoiSelected.connect(self.diameterPlotItem.slot_selectRoi)
        self._kymRoiImageWidget.signalSetLineProfile.connect(self.diameterPlotItem.slot_updateLineProfile)
        self._kymRoiImageWidget.signalSelectRoi.connect(self.diameterPlotItem.slot_selectRoi)
        vBoxPlot.addWidget(self.diameterPlotItem)

        # TODO: make 3-tabs (intensity, diameter, velocity)
        self._tabwidget = QtWidgets.QTabWidget()
        mainHBox.addWidget(self._tabwidget)

        # vbox to hold kymRoi and intensity detection
        _tmpVBox = QtWidgets.QVBoxLayout()
        _tmpVBox.setAlignment(QtCore.Qt.AlignTop)
        _tmpWidget = QtWidgets.QWidget()
        _tmpWidget.setLayout(_tmpVBox)
        self._tabwidget.addTab(_tmpWidget, "Intensity")

        # abb 202505
        # toolbar to show/set roi manually (not with dragging)
        # this will emit KymRoiGroupBox.signalRoiChanged
        groupName = 'Edit ROI'
        self._kymRoiToolbar = KymRoiGroupBox(self._kymRoiAnalysis,
                                                      self._detectionParams,
                                                      groupName=groupName,
                                                      )
        self._kymRoiImageWidget.signalSelectRoi.connect(self._kymRoiToolbar.slot_selectRoi)
        self._kymRoiImageWidget.signalRoiChanged.connect(self._kymRoiToolbar.slot_rio_changed)
        # abb 202505 bidirectional change of roi
        self._kymRoiToolbar.signalRoiChanged.connect(self._kymRoiImageWidget.slot_roi_changed)
        _tmpVBox.addWidget(self._kymRoiToolbar)

        # KymDetectionGroupBox_Intensity
        groupName = 'Detect Peaks (Intensity)'
        self._detectionToolbar = KymDetectionGroupBox_Intensity(self._kymRoiAnalysis,
                                                      self._detectionParams,
                                                      groupName=groupName,
                                                      detectThisTraceList=['f/f0', 'df/f0', 'Divided']
                                                      )
        self._detectionToolbar.signalDetectionParamChanged.connect(self.slot_detectionChanged)
        self._detectionToolbar.signalDetection.connect(self.slot_doAnalysis)
        self._detectionToolbar.signalSetWidgetVisible.connect(self.setWidgetVisible)
        self._kymRoiImageWidget.signalSelectRoi.connect(self._detectionToolbar.slot_selectRoi)
        # self._tabwidget.addTab(self._detectionToolbar, "Intensity")
        _tmpVBox.addWidget(self._detectionToolbar)

        #
        # a toolbar (group) to detect diameter from kym image
        
        # hold 2x detection , diameter and diameter peaks
        _diameter_widget = QtWidgets.QWidget()
        _diameter_vbox = QtWidgets.QVBoxLayout()
        _diameter_vbox.setAlignment(QtCore.Qt.AlignTop)

        _diameter_widget.setLayout(_diameter_vbox)
        self._tabwidget.addTab(_diameter_widget, "Diameter")

        groupName = 'Detect Diameter'
        kymRoiDetection = self._detectionParamsDiameter
        self._kymDiamDetectToolbar = KymDiameterToolbar(self._kymRoiAnalysis,
                                                        kymRoiDetection,
                                                                   groupName=groupName,
                                                                   )
        self._kymDiamDetectToolbar.signalDetectionParamChanged.connect(self.slot_detectionChanged)
        self._kymDiamDetectToolbar.signalDetection.connect(self.slot_doAnalysis)
        self._kymDiamDetectToolbar.signalDetectionParamChanged.connect(self._kymRoiImageWidget.slot_detectionChanged)
        self._kymRoiImageWidget.signalSelectRoi.connect(self._kymDiamDetectToolbar.slot_selectRoi)
        _diameter_vbox.addWidget(self._kymDiamDetectToolbar)

        groupName = 'Detect Peaks (Diameter)'
        self._diamDetectionToolbar = KymDetectionGroupBox_Diameter(self._kymRoiAnalysis,
                                                        self._detectionParamsDiameter,
                                                          groupName=groupName,
                                                          detectThisTraceList=['Diameter (um)', 'Left Diameter (um)', 'Right Diameter (um)'])

        # abb 202505 colin was using set enabled, start using set visible (vertical hight is too big on laptop)
        # self._diamDetectionToolbar.setWidgetEnabled('Background Subtract', False)
        # self._diamDetectionToolbar.setWidgetEnabled('Exponential Detrend', False)
        # self._diamDetectionToolbar.setWidgetEnabled('f0 Type', False)
        # self._diamDetectionToolbar.setWidgetEnabled('f0 Percentile', False)
        self._diamDetectionToolbar.setWidgetVisible('Background Subtract', False)
        self._diamDetectionToolbar.setWidgetVisible('Exponential Detrend', False)
        self._diamDetectionToolbar.setWidgetVisible('f0 Type', False)
        self._diamDetectionToolbar.setWidgetVisible('f0 Percentile', False)

        self._diamDetectionToolbar.signalDetectionParamChanged.connect(self.slot_detectionChanged)
        self._diamDetectionToolbar.signalDetection.connect(self.slot_doAnalysis)
        self._diamDetectionToolbar.signalSetWidgetVisible.connect(self.setWidgetVisible)
        self._kymRoiImageWidget.signalSelectRoi.connect(self._diamDetectionToolbar.slot_selectRoi)

        # vBoxDetectionLayout_left.addWidget(self._diamDetectionToolbar)
        _diameter_vbox.addWidget(self._diamDetectionToolbar)

        #
        # coming soon
        #
        # _velocityWidget = QtWidgets.QWidget()
        # self._tabwidget.addTab(_velocityWidget, "Velocity")

        # metadata
        _metaDataWidget = MetaDataWidget(self._kymRoiAnalysis.header)
        self._tabwidget.addTab(_metaDataWidget, "Meta Data")

        #
        vBoxForClipsScatterTable = QtWidgets.QVBoxLayout()

        _tmpWidget = QtWidgets.QWidget()
        _tmpWidget.setLayout(vBoxForClipsScatterTable)

        self.peakClipsWidget = KymRoiClipsWidget(self._kymRoiAnalysis)
        self.peakClipsWidget.setVisible(False)
        self.signalRoiSumChanged.connect(self.peakClipsWidget.slot_selectRoi)
        self.signalRoiDiameterChanged.connect(self.peakClipsWidget.slot_selectRoi)
        # self.signalRoiSelected.connect(self.peakClipsWidget.slot_selectRoi)
        self._kymRoiImageWidget.signalSelectRoi.connect(self.peakClipsWidget.slot_selectRoi)
        vBoxForClipsScatterTable.addWidget(self.peakClipsWidget)

        #
        # simple scatter plot
        self.simpleScatter = SimpleRoiScatter(self._kymRoiAnalysis)
        self.simpleScatter.setVisible(False)
        self.signalRoiSumChanged.connect(self.simpleScatter.slot_analysisChanged)
        self.signalRoiDiameterChanged.connect(self.simpleScatter.slot_analysisChanged)
        vBoxForClipsScatterTable.addWidget(self.simpleScatter)

        #
        # file list as a dock
        self.fileDock = QtWidgets.QDockWidget('Files')
        self.fileDock.setWidget(_tmpWidget)
        self.fileDock.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures | \
                                  QtWidgets.QDockWidget.DockWidgetVerticalTitleBar)
        self.fileDock.setFloating(False)
        self.fileDock.setTitleBarWidget(QtWidgets.QWidget())
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.fileDock)
    
    def slot_roiChanged(self, roiLabel : str):
        """Slot responding to roi change.
        """
        logger.info(f'roiLabel:"{roiLabel}"')
        
        # update the f0 plot
        self.updateRoiIntensityPlot(roiLabel, doAnalysis=True)

        # update the diameter plot
        # self.updateRoiDiameterPlot(roiLabel, doAnalysis=False)

    def slot_f0_changed(self, channelIdx, roiLabel, f0Value):
        """Recieved from SetF0Widget (f0 is already updated in detection.
        """
        self.updateRoiIntensityPlot(roiLabelStr=roiLabel, doAnalysis=True)

    def analyzeRoiDiam(self, roiLabel : str):

        logger.info('   === WIDGET PERFORMING ROI ANALYSIS ===> diam')

        # this creates 3x traces (left, right, diameter)
        # self.roiList.kymRoiList[roi].detectDiam(self.currentChannel)
        self._kymRoiAnalysis.detectDiam(roiLabel, self.currentChannel)
    
    def analyzeRoi(self, roiLabelStr : str, peakDetectionType : PeakDetectionTypes):
        """Analyze one roi e.g. detect peaks.
        """

        if roiLabelStr is None:
            logger.info('please select an roi to analyze')
            self.mySetStatusbar('please select an roi to analyze')
            return

        logger.info(f'   === WIDGET PERFORMING ROI ANALYSIS ===> peakDetectionType:{peakDetectionType}')

        # ok = self.roiList.kymRoiList[roi].peakDetect(self.currentChannel, kymRoiDetection=kymRoiDetection, verbose=False)
        kymRoi = self._kymRoiAnalysis.getRoi(roiLabelStr)
        ok = kymRoi.peakDetect(self.currentChannel, peakDetectionType, verbose=False)

        return ok
    
    def saveAnalysis(self):
        """Save all peak analysis into one csv file.

        This includes a header with roi [l,t,r,b] and detection parameters used.
        """
                
        _saved = self._kymRoiAnalysis.saveAnalysis()

        if _saved:
            self.mySetStatusbar(f'Saved analysis for {self.path}')
        else:
            self.mySetStatusbar('Nothing to save')

    def _old_update_fo_plot(self, roiLabelStr : str):

        self.rawIntensityPlot.setData([], [])

        if roiLabelStr is None:
            return
        
        channel = self.currentChannel
        
        timeSec = self._kymRoiAnalysis.getAnalysisTrace(roiLabelStr, 'Time (s)', channel)
        intDetrend = self._kymRoiAnalysis.getAnalysisTrace(roiLabelStr, 'intDetrend', channel)

        logger.error(f'timeSec:{len(timeSec)} intDetrend:{len(intDetrend)}')

        # TODO: refactor to not use None
        if timeSec is None or intDetrend is None:
            logger.error('did not find timeSec or intDetrend')
            return
        
        self.rawIntensityPlot.setData(timeSec, intDetrend)

        # f0Value = self._detectionParams['f0 Value']
        _detection = self._kymRoiAnalysis.getRoi(roiLabelStr).getDetectionParams(channel, PeakDetectionTypes.intensity)
        f0Value = _detection['f0 Value']
        self.rawIntensity_f0_line.setPos(round(f0Value,2))

        self._rawPlotCursors._showInView()

    def updateRoiDiameterPlot(self, roiLabel : str, doAnalysis=True):
        """Analyze and then update diameter from kym image.
        
        This generates (left, right, and diam.
        Diam is then peak detected.
        """
        # left/right on kym image
        # self._overlayKymDict['leftDiamOverlay'].setData([], [])
        # self._overlayKymDict['rightDiamOverlay'].setData([], [])

        if roiLabel is None:
            self._kymRoiImageWidget.refreshDiameterPlot([], [], [])
            return

        #
        # find left/right diam from kymograph
        # 20241027, moving all analysis into (new roi, move roi, change detection params)
        if doAnalysis:
            self.analyzeRoiDiam(roiLabel)

        #
        # update plots
        # timeSec = self._kymRoiAnalysis.getAnalysisTrace(roiLabel, 'timeSec', self.currentChannel)
        timeSec = self._kymRoiAnalysis.getAnalysisTrace(roiLabel, 'Time (s)', self.currentChannel)
        leftDiameterUm = self._kymRoiAnalysis.getAnalysisTrace(roiLabel, 'Left Diameter (um)', self.currentChannel)
        rightDiameterUm = self._kymRoiAnalysis.getAnalysisTrace(roiLabel, 'Right Diameter (um)', self.currentChannel)

        if leftDiameterUm is None:
            logger.info('no diameter to plot')
            return
        
        # left/right on kym image
        # self._overlayKymDict['leftDiamOverlay'].setData(timeSec, leftDiameterUm)
        # self._overlayKymDict['rightDiamOverlay'].setData(timeSec, rightDiameterUm)
        logger.info('REFRESHING KYM DIAM PLOT')
        self._kymRoiImageWidget.refreshDiameterPlot(timeSec, leftDiameterUm, rightDiameterUm)

    def updateRoiIntensityPlot(self, roiLabelStr : str, doAnalysis=True):
        """Update f/f0 intensity plot when user adjusts roi.
        """

        # perform analysis
        logger.warning(f'turned off auto analysis - implementing "Analyze" button doAnalysis:{doAnalysis}')
        if doAnalysis:
            ok = self.analyzeRoi(roiLabelStr, PeakDetectionTypes.intensity)
            if ok is None:
                logger.error('did not perform analysis')
                return

        logger.warning(f'  -->> signalRoiSumChanged.emit with currentChannel:{self.currentChannel} roiLabelStr:"{roiLabelStr}"')
        self.signalRoiSumChanged.emit(self.currentChannel, roiLabelStr)

        #
        # update other widgets
        #
        
        # raw intensity plot (to manually set f0)
        # self.update_fo_plot(roiLabelStr)

    def _resetZoom(self, doEmit=True):
        
        # order matter, do sum then image
        # 
        # self.sumIntensityPlotItem.autoRange()  # item=self._roiIntensityPlot[roi]
        # self.diameterPlotItem.autoRange()

        self._kymRoiImageWidget.kymographPlot.autoRange(item=self._kymRoiImageWidget.myImageItem)

    def keyReleaseEvent(self, event):
    
        key = event.key()
        isShift = key == QtCore.Qt.Key_Shift
        
        if isShift:
            # default is x-zoom
            self._kymRoiImageWidget.kymographPlot.setMouseEnabled(x=True, y=False)
            self.sumIntensityPlotItem.setMouseEnabled(x=True, y=False)
            # self.rawIntensityPlotItem.setMouseEnabled(x=True, y=False)
            self.diameterPlotItem.setMouseEnabled(x=True, y=False)
    
    def keyPressEvent(self, event):
        """Respond to user key press.

        Parameters
        ----------
        event : PyQt5.QtGui.QKeyEvent
        """
        key = event.key()
        text = event.text()
        
        isShift = event.modifiers() == QtCore.Qt.ShiftModifier
        isAlt = event.modifiers() == QtCore.Qt.AltModifier
        isCtrl = event.modifiers() == QtCore.Qt.ControlModifier
        
        logger.info(f'key:{key} text:{text} isCtrl:{isCtrl} isAlt:{isAlt} isShift:{isShift}')

        if isShift:
            # default is x-zoom
            # self.kymographPlot.setMouseEnabled(x=True, y=False)
            # switch it to y-zoom
            self._kymRoiImageWidget.kymographPlot.setMouseEnabled(x=False, y=True)
            self.sumIntensityPlotItem.setMouseEnabled(x=False, y=True)
            # self.rawIntensityPlotItem.setMouseEnabled(x=False, y=True)
            self.diameterPlotItem.setMouseEnabled(x=False, y=True)

        if key in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            self._resetZoom()

        elif key == QtCore.Qt.Key.Key_Escape:
            self._kymRoiImageWidget._selectRoi(None)

        elif key in [QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace]:
            #self.removeSelectedRoi()
            self._kymRoiImageWidget.onUserDeleteRoi()

        elif key in [QtCore.Qt.Key_Plus, QtCore.Qt.Key_Equal]:
            self._kymRoiImageWidget.onUserAddRoi()

        elif key in [QtCore.Qt.Key_W] and isCtrl:
            self.simpleScatter.copyTableToClipboard()

        elif isCtrl and key == QtCore.Qt.Key_S:
            self.saveAnalysis()

        # elif key == QtCore.Qt.Key_S:
        #     self.savePlotItemAs()

        else:
            logger.warning('did not understand user key press')

    def savePlotItemAs(self, plotItem : pg.graphicsItems.PlotItem, name : str):
        """Save a plot item to file.
        """
        import pyqtgraph.exporters
        # filename = 'filename.png'
        # filename = 'filename.pdf'  # does not work
        # filename = 'filename.tif'
        # filename = 'filename.svg'

        # roi = self.roiList.selectedRoi
        # if roi is None:
        #     return
        
        saveFolder = self._kymRoiAnalysis._getSaveFolder(createFolder=True)
        
        _, _file = os.path.split(self.path)
        _file, _ = os.path.splitext(_file)
        _file = _file + '-' + name + '.png'
        savePath = os.path.join(saveFolder, _file)

        logger.info(f'saving {name} to {savePath}')

        exporter = pg.exporters.ImageExporter(plotItem)
        exporter.export(savePath)
        _ret = f'Saved "{name}" to {savePath}'
        return _ret
    
    def _contextMenu(self, pos):
        """Context menu for entire widget.
        
        See also myRawContextMenu.
        """
        # logger.info('')

        # build menu
        contextMenu = QtWidgets.QMenu()
        contextMenu.addAction('Full Zoom')
        contextMenu.addSeparator()

        # toggle kym image
        _toggleKymAction = contextMenu.addAction('Kymograph Image')
        _toggleKymAction.setCheckable(True)
        _toggleKymAction.setChecked(self._kymRoiImageWidget.isVisible())
        
        # toggle intensity plot
        _toggleIntensity = contextMenu.addAction('Intensity Plot')
        _toggleIntensity.setCheckable(True)
        _toggleIntensity.setChecked(self.sumIntensityPlotItem.isVisible())

        # a menu to select an roi (use this when they visually overlap)
        contextMenu.addSeparator()
        for kymRoi in self._kymRoiAnalysis:
            roiLabelText = kymRoi.getLabel()
            contextMenu.addAction(f'Select ROI: {roiLabelText}')

        # copy rois to clipboad
        _copyRois = contextMenu.addAction('Copy ROIs to Clipboard')

        # set santana norm lie scan
        _setSantanaNormLine = contextMenu.addAction('Set Santana Norm Scan')

        # paste rois from clipboad
        # check that we have rois on the clipboard
        app = QtWidgets.QApplication.instance()
        _json = app.clipboard().text()
        try:
            _dict = json.loads(_json)
        except(json.decoder.JSONDecodeError) as e:
            # logger.error(f'clipboard does not contain roi json:\n{_json}')
            _dict = {}
        _pasteRois = contextMenu.addAction('Paste ROIs from Clipboard')
        _pasteRois.setEnabled(len(_dict) > 0)

        # show menu
        pos = self.mapToGlobal(pos)
        action = contextMenu.exec_(pos)
        if action is None:
            return
        
        # respond to menu selection
        _ret = ''
        actionText = action.text()
        if actionText == 'Full Zoom':
            self._resetZoom()
            _ret = 'Reset zoom'

        # elif actionText == 'Cursors':
        #     _checked = action.isChecked()
        #     self._sanpyCursors.toggleCursors(_checked)
        #     # self._rawPlotCursors.toggleCursors(_checked)

        # elif actionText == 'Save Kym Image ...':
        #     _ret = self.savePlotItemAs(self.kymographPlot, 'kym-image')

        # elif actionText == 'Save Sum Plot ...':
        #     roiLabelText = self.roiList.roiLabelList[selectedRoi].toPlainText()
        #     _ret = self.savePlotItemAs(self.sumIntensityPlotItem.plotItem, f'sum-plot-roi-{roiLabelText}')

        # elif actionText == 'Save Clips ...':
        #     roiLabelText = self.roiList.roiLabelList[selectedRoi].toPlainText()
        #     _ret = self.savePlotItemAs(self.peakClipsWidget.peakClipPlotItem.plotItem, f'clip-plot-{roiLabelText}')

        # elif actionText == 'Copy Stats Table ...':
        #     _ret = self.simpleScatter.copyTableToClipboard()
        
        # special case on transition to backend
        elif action == _toggleKymAction:
            _checked = action.isChecked()
            self._kymRoiImageWidget.setVisible(_checked)
            self._kymRoiImageWidget.setEnabled(_checked)

        elif action == _toggleIntensity:
            _checked = action.isChecked()
            self.sumIntensityPlotItem.setVisible(_checked)
            self.sumIntensityPlotItem.setEnabled(_checked)

        elif actionText.startswith('Select ROI'):
            _, roiLabel = actionText.split(': ')
            logger.info(f'selecting roiLabel:{roiLabel}')
            self._kymRoiImageWidget.selectRoiFromLabel(roiLabel)

        elif action == _setSantanaNormLine:
            # grab the current line scan from the kym image widget slider
            lineScanNumber = self._kymRoiImageWidget._lineScanSlider.value()
            logger.info(f'setting santana norm line to lineScanNumber:{lineScanNumber}')
            self._kymRoiAnalysis.setKymDetectionParam('santanaLineScanNorm', lineScanNumber)

        # copy rois to clipboard
        elif action == _copyRois:
            # copy rois to clipboard
            _dict = self._kymRoiAnalysis.getCopyToClipboard()
            _json = json.dumps(_dict, indent=4)
            logger.info(f'copying rois to clipboard:\n{_json}')
            # QtGui.QGuiApplication().clipboard().setText(_json)
            app = QtWidgets.QApplication.instance()
            app.clipboard().setText(_json)

            _ret = f'Copied {len(_dict)} rois to clipboard'

        # paste rois from clipboard
        elif action == _pasteRois:
            app = QtWidgets.QApplication.instance()
            _json = app.clipboard().text()
            try:
                _dict = json.loads(_json)
            except(json.decoder.JSONDecodeError) as e:
                # logger.error(f'clipboard does not contain roi json:\n{_json}')
                return
            
            # logger.info(f'retrieved rois from clipboard _dict:\n{_dict}')
        
            # self._kymRoiAnalysis.setRoiDict(_dict)
            
            # delete all roi
            logger.info(f'deleting {self._kymRoiAnalysis.numRoi} existing rois')
            for roiLabel in self._kymRoiAnalysis.getRoiLabels():
                # self._kymRoiAnalysis.deleteRoi(roiLabel)
                self._kymRoiImageWidget.onUserDeleteRoi(roiLabel=roiLabel)

            logger.info(f'adding {len(_dict)} rois from the clipboard')
            for roiLabel, roiDict in _dict.items():
                # roi = KymRoi(roiLabel, roiDict)
                # self._kymRoiAnalysis.addRoi(roi)
                ltrb = [0] * 4
                ltrb[0] = roiDict['left']
                ltrb[1] = roiDict['top']
                ltrb[2] = roiDict['right']
                ltrb[3] = roiDict['bottom']
                # self._kymRoiAnalysis.addRoi(ltrb)
                self._kymRoiImageWidget.onUserAddRoi(ltrbRoi=ltrb)

            _ret = f'Pasted {len(_dict)} rois from clipboard'

        self.mySetStatusbar(_ret)