"""
Widget to act as the interface for kymographPlugin

This widget shows 4 plots in a vertical layout
 - kym image
 - line intensity profile
 - diameter
 - sum line scan

I am keeping it seperate because it can be used standalone.
"""

import sys
import numpy as np

from qtpy import QtGui, QtCore, QtWidgets

import pyqtgraph as pg

import qdarktheme

import sanpy
import sanpy.interface
import sanpy.user_analysis

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

# class kymographPlugin2(QtWidgets.QWidget):
class kymographPlugin2(QtWidgets.QMainWindow):
    """Interface for kymograph analysis.
    
        20230526, Re-activating this for 'shortening' experiments.
    """
    def __init__(self, ba: sanpy.bAnalysis, parent=None):
        # exportDiameter()
        
        logger.info("")

        super().__init__(parent)

        self._ba = None
        if ba is not None and ba.fileLoader.isKymograph():
            self._ba = ba

        # this is class sanpy.kymAnalysis
        self._kymographAnalysis : sanpy.kymAnalysis = None  # will be created in slotSwitchFile()
        if self._ba is not None:
            self._kymographAnalysis = ba.kymAnalysis

        # self._imageMedianKernel = 5
        # self._lineMedianKernel = 5

        self._currentLineNumber = 0

        self._fitIsVivible = True
        # keep track of left/right fit on top of kym image

        self._kymWidgetMain = None  # sanpy.interface.kymographWidget(self._ba)
        self._initGui()

        self.slotSwitchFile(self._ba)

        self._on_slider_changed(0)

        self.refreshSumLinePlot()
        self.refreshDiameterPlot()

    def _cursor_setDetectionParam(self, detectionParam : str, value : float):
        """Used by sanpyCursor.
        """
        logger.info(f'detectionParam:{detectionParam} value:{value}')

    def _cursor_updateStatusBar(self, text):
        """Used by sanpyCursor.
        """
        logger.info('not implemented')
        logger.info(f'  {text}')
        # if self.myMainWindow is not None:
        #     self.myMainWindow.slot_updateStatus(text)
        # else:
        #     logger.info(text)

    # july 2023, moved from multi line
    def _add_in_contextMenuEvent(self, event):
        """Show popup context menu in response to right(command)+click.
        
        Toggle crosshair on line profile
        Toggle plots on/off


        Parameters
        ----------
        event : QContextMenuEvent
        """

        logger.info('kymographPlugin2')
        
        contextMenu = QtWidgets.QMenu()

        self._showCrosshair = True
        
        showCrosshairAction = contextMenu.addAction(f"Crosshair")
        showCrosshairAction.setCheckable(True)
        showCrosshairAction.setChecked(self._showCrosshair)

        # show menu
        pos = QtCore.QPoint(event.x(), event.y())
        pos = self.mapToGlobal(event.pos())
        action = contextMenu.exec_(pos)
        if action is None:
            return
        
        actionText = action.text()
        if actionText == 'Crosshair':
            print('toggle line profile crosshair')
    
    def keyPressEvent(self, event):
        logger.info('')
        key = event.key()
        if key in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            self._resetZoom()
        
        elif key == QtCore.Qt.Key_Right:
            print('move slider right')
            self._kymWidgetMain.incDecLineSlider(+1)
        elif key == QtCore.Qt.Key_Left:
            print('move slider left')
            self._kymWidgetMain.incDecLineSlider(-1)

        elif key == QtCore.Qt.Key_D:
            # detect line and show mpl plot
            lineScanNumber = self._kymWidgetMain.getDisplayedLineNumber()
            self._kymographAnalysis._getFitLineProfile(lineScanNumber, doMplPlot=True)

    def _checkboxCallback(self, state: bool, name: str):
        logger.info(f"state:{state} name:{name}")
        if name == "Line Profile":
            self.showLineProfile(state)
            self._on_slider_changed()
        elif name == "Diameter":
            self.diameterPlotItem.setVisible(state)
            self.footPeakCheckBox.setEnabled(state)  # foot/peak checkbox follows diameter plot
        elif name =='Foot/Peak':
            self._diamFootPlotItem.setVisible(state)
            self._diamPeakPlotItem.setVisible(state)
        elif name == "Line Intensity":
            self.sumIntensityPlotItem.setVisible(state)
            self._linePlotCombo.setEnabled(state)
        elif name == "Fit On Kym":
            self._fitIsVivible = state
            self.refreshDiameterPlot(autoRange='none')

    def showLineProfile(self, state: bool):
        """Toggle interface for Line Profile.
        """
        # self.profileSlider.setVisible(state)

        self.lineIntensityPlotItem.setVisible(state)

        # for line in self._sliceLinesList:
        #     line.setVisible(state)

    def _buttonCallback(self, name):
        logger.info(f"name:{name}")
        # pos = self._rectRoi.pos()  # (left, bottom)
        # size = self._rectRoi.size()  # (widht, height)
        # print(f'    pos:{pos} size:{size}')

        if name == "Reset ROI":
            pos, size = self._kymographAnalysis.getFullRectRoi()  # (w,h)
            self._rectRoi.setPos(pos)
            self._rectRoi.setSize(size)
            # set the x-axis of the image plot
            # self.kymographWindow.setXRange(0, shape[0])

        elif name == 'Reset Zoom':
            self._resetZoom()
        
        elif name == "Analyze":
            if self._kymographAnalysis is None:
                return
            
            # during analysis button is red
            self._analyzeButton.setStyleSheet("background-color : #AA2222")
            self._analyzeButton.repaint()
            self._analyzeButton.update()
            QtCore.QCoreApplication.processEvents()

            # left_idx, right_idx = self._kymographAnalysis.getLineProfileWidth()
            # imageMedianKernel = self._imageMedianKernel
            # lineMedianKernel = self._lineMedianKernel

            # self._kymographAnalysis.printAnlysisParam()

            # 20230728, was this
            self._kymographAnalysis.analyzeDiameter(verbose=True)
            #self._kymographAnalysis.analyzeDiameter_mp()

            #     imageMedianKernel=imageMedianKernel,
            #     lineMedianKernel=lineMedianKernel
            # )

            if self._ba.isAnalyzed():
                _kymUserAnalysis = sanpy.user_analysis.kymUserAnalysis(self._ba)
                _kymUserAnalysis.defineUserStats()
                _kymUserAnalysis.run()
                self._ba._detectionDirty = True

            # self.refreshSumLinePlot()
            self.refreshDiameterPlot(autoRange='y')
            self.refreshSumLinePlot(autoRange='y')

            # after analysis, button is green
            self._analyzeButton.setStyleSheet("background-color : #22AA22")
            self._analyzeButton.repaint()
            self._analyzeButton.update()
            QtCore.QCoreApplication.processEvents()

        elif name == "Save":
            # # get file name to save
            # saveFilePath = self._kymographAnalysis.getAnalysisFile()
            # # name = QtGui.QFileDialog.getSaveFileName(self, 'Save File')
            # savefile, tmp = QtWidgets.QFileDialog.getSaveFileName(
            #     self, "Save File", saveFilePath
            # )
            # if savefile:
            #     self._kymographAnalysis.saveAnalysis(savefile)
            self._kymographAnalysis.saveAnalysis()

        elif name == "Rot -90":
            newImage = self._kymographAnalysis.rotateImage()
            self.kymographImage.setImage(newImage)

        else:
            logger.warning(f'did not understand "{name}"')

    def _old_setLineWidth(self, value: int):
        logger.info(value)
        if self._kymographAnalysis is not None:
            self._kymographAnalysis.setAnalysisParam('lineWidth', value)

    def setPercentMax(self, value: float, doSet = False):
        logger.info(f"value:{value}")
        if self._kymographAnalysis is not None:
            self._kymographAnalysis.setAnalysisParam('percentOfMax', value)

        if doSet:
            self.percentMaxSpinbox.setValue(value)

        # refresh the line profile plot
        self._on_slider_changed(value=None)

    def slotSwitchFile(self, ba: sanpy.bAnalysis):
        if ba is None:
            return
            
        if ba is not None and not ba.fileLoader.isKymograph():
            return

        self._ba = ba

        # update image widget
        self._kymWidgetMain.slot_switchFile(ba=self._ba)

        self._kymographAnalysis = ba.kymAnalysis

        # refresh detection controls
        self._refreshGui()

        # self._on_slider_changed(0)
        self._kymWidgetMain._on_line_slider_changed(0)
        
        self.refreshSumLinePlot()
        self.refreshDiameterPlot()

        self._resetZoom()

    def _slot_roi_changed2(self, newRect):
        """User modified ROI.

        Sent from bKymographWidget. Rewrite of '_slot_roi_changed'
            To use new improved bKymographWidget

        Args:
            newRect: [l,t,r,b]
        """

        # replot line profile
        self._on_slider_changed()

        # replot sum
        self.refreshSumLinePlot()

    def _on_diam_plot_popup(self, value : str):
        """Set the type of diam plot.
        """
        self._plotDiamType = value
        self.refreshDiameterPlot(autoRange='y')
        
    def _on_line_intensity_popup(self, value : str):
        """Set the type of line  intensity plot.
        
        Either sum or range.
        """

        # self._plotSumType = 'Intensity Sum'
        # self._plotSumType = 'Intensity Range'

        self._plotSumType = value
        self.refreshSumLinePlot()

    def _on_lineWidth(self, lineWidth : str, doSet = False):
        logger.info(f'lineWidth:{lineWidth} {type(lineWidth)}')
        
        if self._kymographAnalysis is not None:
            self._kymographAnalysis.setAnalysisParam('lineWidth', int(lineWidth))
        if doSet:
            self._lineWidthSpinbox.setCurrentText(lineWidth)
        else:
            self._on_slider_changed()  # refresh line scan
      
    def _on_overSample(self, interpMult : str, doSet = False):
        logger.info(f'interpMult:{interpMult} {type(interpMult)}')
        
        if interpMult == 'Off':
            interpMult = '0'
                
        if self._kymographAnalysis is not None:
            self._kymographAnalysis.setAnalysisParam('interpMult', int(interpMult))
        if doSet:
            self._overSample.setCurrentText(interpMult)
        else:
            self._on_slider_changed()  # refresh line scan


    # def _on_median_image(self, medianImageStr : str, doSet = False):
    #     logger.info(f'medianImageStr:{medianImageStr}')

    #     if medianImageStr == 'Off':
    #         medianImageStr = '0'

    #     if self._kymographAnalysis is not None:
    #         self._kymographAnalysis.setAnalysisParam('imageFilterKenel', int(medianImageStr))

    #     if doSet:
    #         self._medianImage.setCurrentText(medianImageStr)
    #     else:
    #         self._on_slider_changed()  # refresh line scan

    def _on_median_line(self, mediaLineStr : str, doSet = False):
        logger.info(f'medianImageStr:{mediaLineStr}')

        if mediaLineStr == 'Off':
            mediaLineStr = '0'

        if self._kymographAnalysis is not None:
            self._kymographAnalysis.setAnalysisParam('lineFilterKernel', int(mediaLineStr))

        if doSet:
            self._medianLine.setCurrentText(mediaLineStr)
        else:
            self._on_slider_changed()  # refresh line scan

    def _on_detect_polarity(self, posNegStr : str, doSet = False):
        logger.info(f'posNegStr:{posNegStr}')

        if self._kymographAnalysis is not None:
            self._kymographAnalysis.setAnalysisParam('detectPosNeg', posNegStr)

        if posNegStr == 'pos':
            posNegIdx = 0
        elif posNegStr == 'neg':
            posNegIdx = 1
        else:
            logger.error(f'Did not understand posNegStr: "{posNegStr}"')
            posNegIdx = 0

        if doSet:
            self._detectPosNeg.setCurrentIndex(posNegIdx)
        else:
            self._on_slider_changed()  # refresh line scan

    def setImageMedianKernel(self, value):
        """TODO: dpreciate this.
        """
        # self._imageMedianKernel = value

        self._kymographAnalysis.setAnalysisParam('imageFilterKenel', value)

        # refresh the line profile plot
        self._on_slider_changed(value=None)

    def setLineMedianKernel(self, value):
        # self._lineMedianKernel = value

        self._kymographAnalysis.setAnalysisParam('lineFilterKernel', value)

        # refresh the line profile plot
        self._on_slider_changed(value=None)

    def _on_slider_changed(self, value : int = None):
        """Respond to user changing the "Line Scan" slider.

        Args:
            value: The line profile number
        """
        if self._ba is None:
            return

        if value is None:
            value = self._currentLineNumber
        else:
            self._currentLineNumber = value

        # logger.info(f"value:{value}")

        xScale = self._ba.fileLoader.tifHeader["secondsPerLine"]

        # secondsValue = value * self._kymographAnalysis._secondsPerLine
        secondsValue = value * xScale

        # update vertical lines on top of plots
        for line in self._sliceLinesList:
            line.setValue(secondsValue)

        # update one line profile plot
        if self._kymographAnalysis is None:
            logger.warning('did not find _kymographAnalysis -> return None')
            return

        lineProfile, left_pnt, right_pnt = self._kymographAnalysis._getFitLineProfile(value)
        pointsPerLineScan = self._kymographAnalysis.pointsPerLineScan()
        umPerPixel = self._kymographAnalysis.umPerPixel

        xData = np.arange(0, pointsPerLineScan)
        xData = np.multiply(xData, umPerPixel)
        if len(xData) != len(lineProfile):
            logger.error(f"xData: {len(xData)}")
            logger.error(f"lineProfile: {len(lineProfile)}")
        self.lineIntensityPlot.setData(xData, lineProfile)

        # if the fit fails we get left/right as nan
        if np.isnan(left_pnt) or np.isnan(right_pnt):
            xLeftRightData = [np.nan, np.nan]
            yLeftRightData = [np.nan, np.nan]
        else:
            left_um = self._kymographAnalysis.pnt2um(left_pnt)
            right_um = self._kymographAnalysis.pnt2um(right_pnt)
            xLeftRightData = [left_um, right_um]
            # print(xLeftRightData)
            # 20230920, will not be exact math with interp
            left_pnt_rnd = int(round(left_pnt))
            right_pnt_rnd = int(round(right_pnt))
            # yLeftRightData = [lineProfile[left_pnt_rnd], lineProfile[right_pnt]]
            
            # 20231202
            try:
                yLeftRightData = [lineProfile[left_pnt_rnd], lineProfile[right_pnt_rnd]]
            except (IndexError):
                self.leftRightPlot.setData([], [])
            else:
                self.leftRightPlot.setData(xLeftRightData, yLeftRightData)

    def _refreshGui(self):
        """On file change set detection params.
        """
        # _posNegIdx = 0
        # _percentMax = 0.5
        # if self._kymographAnalysis is not None:
        # kym analysis have defaults when instantiated
        if 1:
            # _lineWidth = self._kymographAnalysis.getAnalysisParam('lineWidth')
            
            _posNegStr = self._kymographAnalysis.getAnalysisParam('detectPosNeg')
            if _posNegStr == 'pos':
                _posNegIdx = 0
            elif _posNegStr == 'neg':
                _posNegIdx = 1
            else:
                logger.error(f'Did not understand posNegStr: "{_posNegStr}"')
                _posNegIdx = 0

            _percentMax = self._kymographAnalysis.getAnalysisParam('percentOfMax')
            # _imageFilterKenel = self._kymographAnalysis.getAnalysisParam('imageFilterKenel')
            # _lineFilterKernel = self._kymographAnalysis.getAnalysisParam('lineFilterKernel')

        # self._lineWidthSpinbox.setValue(_lineWidth)
        self._percentMaxSpinbox.setValue(_percentMax)
        self._detectPosNeg.setCurrentIndex(_posNegIdx)

        # self._imageMedianKernelSpinbox.setValue(_imageFilterKenel)
        # self._lineMedianKernelSpinbox.setValue(_lineFilterKernel)

        lineWidth = self._kymographAnalysis.getAnalysisParam('lineWidth')
        lineWidth = str(lineWidth)
        self._lineWidthSpinbox.setCurrentText(lineWidth)

        interpMult = self._kymographAnalysis.getAnalysisParam('interpMult')
        if interpMult == 0:
            interpMult = 'Off'
        else:
            interpMult = str(interpMult)
        self._overSample.setCurrentText(str(interpMult))

        # imageFilterKenel = self._kymographAnalysis.getAnalysisParam('imageFilterKenel')
        # self._medianImage.setCurrentText(str(imageFilterKenel))

        lineFilterKernel = self._kymographAnalysis.getAnalysisParam('lineFilterKernel')
        self._medianLine.setCurrentText(str(lineFilterKernel))

    def _initGui(self):
        self.setWindowTitle("Kymograph Analysis")

        self._plotDiamType = 'Diameter (um)'
        self._plotSumType = 'Intensity Sum'

        self._sliceLinesList = []

        # vBoxLayout = QtWidgets.QVBoxLayout()

        # typical wrapper for PyQt, we can't use setLayout(), we need to use setCentralWidget()
        _mainWidget = QtWidgets.QWidget()
        vBoxLayout = QtWidgets.QVBoxLayout()
        _mainWidget.setLayout(vBoxLayout)
        self.setCentralWidget(_mainWidget)

        # kymograph widget from main interface
        # self._kymWidgetMain = sanpy.interface.kymographWidget(self._ba)  # will handle na is None
        self._kymWidgetMain = sanpy.interface.kymographWidget(None)  # will handle na is None
        self._kymWidgetMain.signalKymographRoiChanged.connect(self._slot_roi_changed2)
        self._kymWidgetMain.signalLineSliderChanged.connect(self._on_slider_changed)
        self._kymWidgetMain.signalResetZoom.connect(self._resetZoom)

        # v1 in layout
        # vBoxLayout.addWidget(self._kymWidgetMain)

        # v2 in a dock
        self.fileDock = QtWidgets.QDockWidget('Files',self)
        self.fileDock.setWidget(self._kymWidgetMain)
        self.fileDock.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures | \
                                  QtWidgets.QDockWidget.DockWidgetVerticalTitleBar)
        self.fileDock.setFloating(False)
        self.fileDock.setTitleBarWidget(QtWidgets.QWidget())
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.fileDock)

        #
        # control bar
        hBoxLayoutControls = QtWidgets.QHBoxLayout()

        aLabel = QtWidgets.QLabel("Line Width")
        hBoxLayoutControls.addWidget(aLabel)
        self._lineWidthSpinbox = QtWidgets.QComboBox()
        self._lineWidthSpinbox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self._lineWidthSpinbox.setToolTip('Number of line scans to pool per line analysis.')
        self._lineWidthSpinbox.addItems(['1', '3', '5', '7', '9', '11'])
        if self._kymographAnalysis is not None:
            lineWidth = self._kymographAnalysis.getAnalysisParam('lineWidth')
            lineWidth = str(lineWidth)
        else:
            lineWidth = '1'
        self._on_lineWidth(lineWidth, doSet=True)
        self._lineWidthSpinbox.currentTextChanged.connect(self._on_lineWidth)
        hBoxLayoutControls.addWidget(self._lineWidthSpinbox)

        # detect pos or neg intensity (polartity)
        aLabel = QtWidgets.QLabel("Polarity")
        hBoxLayoutControls.addWidget(aLabel)
        self._detectPosNeg = QtWidgets.QComboBox()
        self._detectPosNeg.setToolTip('Detect positive or negative peaks.')
        self._detectPosNeg.addItem('pos')
        self._detectPosNeg.addItem('neg')
        if self._kymographAnalysis is not None:
            posNegStr = self._kymographAnalysis.getAnalysisParam('detectPosNeg')
        else:
            posNegStr = 'pos'
        self._on_detect_polarity(posNegStr, doSet=True)
        self._detectPosNeg.currentTextChanged.connect(
            self._on_detect_polarity
        )
        hBoxLayoutControls.addWidget(self._detectPosNeg)

        # percent of max in line profile (for analysis)
        percentMaxLabel = QtWidgets.QLabel("STD Threshold")
        hBoxLayoutControls.addWidget(percentMaxLabel)
        self._percentMaxSpinbox = QtWidgets.QDoubleSpinBox()
        self._percentMaxSpinbox.setToolTip('Threshold for diameter as fraction of standard deviation (STD).')
        self._percentMaxSpinbox.setSingleStep(0.1)
        self._percentMaxSpinbox.setMinimum(0.1)
        self._percentMaxSpinbox.setDecimals(2)
        if self._kymographAnalysis is not None:
            _percentMax = self._kymographAnalysis.getAnalysisParam('percentOfMax')
            # percentMaxSpinbox.setValue(self._kymographAnalysis.getAnalysisParam('percentOfMax'))
        # else:
        #     percentMaxSpinbox.setValue(10)
        self._percentMaxSpinbox.valueChanged.connect(
            self.setPercentMax
        )  # triggers as user types e.g. (22)
        #self.setPercentMax(_percentMax, doSet=True)
        hBoxLayoutControls.addWidget(self._percentMaxSpinbox)

        # hBoxLayoutControls.addStretch()

        # line 1
        hBoxLayoutControls1 = QtWidgets.QHBoxLayout()

        # aLabel = QtWidgets.QLabel("Median Image")
        # hBoxLayoutControls1.addWidget(aLabel)
        # self._medianImage = QtWidgets.QComboBox()
        # self._medianImage.setToolTip('Median filter image size (pixels).')
        # self._medianImage.addItems(['Off', '3', '5'])
        # if self._kymographAnalysis is not None:
        #     imageFilterKenel = self._kymographAnalysis.getAnalysisParam('imageFilterKenel')
        #     imageFilterKenelStr = str(imageFilterKenel)
        #     logger.info(f' _kymographAnalysis loaded imageFilterKenelStr is "{imageFilterKenelStr}"')
        # else:
        #     imageFilterKenelStr = 'Off'
        #     logger.info(f' _kymographAnalysis NOT loaded imageFilterKenelStr is "{imageFilterKenelStr}"')
        # self._on_median_image(imageFilterKenelStr, doSet=True)
        # self._medianImage.currentTextChanged.connect(
        #     self._on_median_image
        # )
        # hBoxLayoutControls1.addWidget(self._medianImage)

        # oversample factor (using interp)
        aLabel = QtWidgets.QLabel("Line profile: Over Sample")
        hBoxLayoutControls1.addWidget(aLabel)
        self._overSample = QtWidgets.QComboBox()
        self._overSample.setToolTip('Factor to oversample line profile.')
        self._overSample.addItems(['Off', '1', '2', '3', '4', '5', '6'])
        if self._kymographAnalysis is not None:
            interpMult = self._kymographAnalysis.getAnalysisParam('interpMult')
            interpMult = str(interpMult)
        else:
            interpMult = 'Off'
        self._on_overSample(interpMult, doSet=True)
        self._overSample.currentTextChanged.connect(
            self._on_overSample
        )
        hBoxLayoutControls1.addWidget(self._overSample)

        aLabel = QtWidgets.QLabel("median filter")
        hBoxLayoutControls1.addWidget(aLabel)
        self._medianLine = QtWidgets.QComboBox()
        self._medianLine.setToolTip('Median filter line profile (pixels).')
        self._medianLine.addItems(['Off', '3', '5'])
        if self._kymographAnalysis is not None:
            imageFilterKenel = self._kymographAnalysis.getAnalysisParam('lineFilterKernel')
            imageFilterKenelStr = str(imageFilterKenel)
        else:
            imageFilterKenelStr = 'Off'
        self._on_median_line(imageFilterKenelStr, doSet=True)
        self._medianLine.currentTextChanged.connect(
            self._on_median_line
        )
        hBoxLayoutControls1.addWidget(self._medianLine)

        # hBoxLayoutControls1.addStretch()

        # buttons
        buttonName = 'Reset Zoom'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(lambda state, name=buttonName: self._buttonCallback(name))
        hBoxLayoutControls1.addWidget(aButton)

        # buttonName = 'Reset ROI'
        # aButton = QtWidgets.QPushButton(buttonName)
        # aButton.clicked.connect(lambda state, name=buttonName: self._buttonCallback(name))
        # hBoxLayoutControls.addWidget(aButton)

        # buttonName = 'Rot -90'
        # aButton = QtWidgets.QPushButton(buttonName)
        # aButton.setEnabled(False)
        # aButton.clicked.connect(lambda state, name=buttonName: self._buttonCallback(name))
        # hBoxLayoutControls.addWidget(aButton)

        # keep reference to button so we can change color during analysis
        buttonName = 'Analyze'
        self._analyzeButton = QtWidgets.QPushButton(buttonName)
        self._analyzeButton.setStyleSheet("background-color : #22AA22")
        self._analyzeButton.clicked.connect(
            lambda state, name=buttonName: self._buttonCallback(name)
        )
        hBoxLayoutControls1.addWidget(self._analyzeButton)

        buttonName = "Save"
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.clicked.connect(
            lambda state, name=buttonName: self._buttonCallback(name)
        )
        hBoxLayoutControls1.addWidget(aButton)

        # 3nd row of controls
        hBoxLayoutControls2 = QtWidgets.QHBoxLayout()

        aLabel = QtWidgets.QLabel("Display:")
        hBoxLayoutControls2.addWidget(aLabel)

        checkboxName = "Line Profile"
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setToolTip('Toggle line profile on/off.')
        aCheckBox.setChecked(True)
        aCheckBox.stateChanged.connect(
            lambda state, name=checkboxName: self._checkboxCallback(state, name)
        )
        hBoxLayoutControls2.addWidget(aCheckBox)

        checkboxName = "Diameter"
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setToolTip('Toggle diameter plot on/off')
        aCheckBox.setChecked(True)
        aCheckBox.stateChanged.connect(
            lambda state, name=checkboxName: self._checkboxCallback(state, name)
        )
        hBoxLayoutControls2.addWidget(aCheckBox)

        # plot one of (diameter, left_um, right_um)
        self._diamPlotCombo = QtWidgets.QComboBox()
        self._diamPlotCombo.setToolTip('Select the type of diameter plot.')
        self._diamPlotCombo.addItem('Diameter (um)')
        self._diamPlotCombo.addItem('Diameter Filtered (um)')
        self._diamPlotCombo.addItem('Start (um)')
        self._diamPlotCombo.addItem('Stop (um)')
        self._diamPlotCombo.currentTextChanged.connect(
            self._on_diam_plot_popup
        )
        hBoxLayoutControls2.addWidget(self._diamPlotCombo)

        checkboxName = "Foot/Peak"
        self.footPeakCheckBox = QtWidgets.QCheckBox(checkboxName)
        self.footPeakCheckBox.setToolTip('Toggle foot/peak diameter overlay on/off.')
        self.footPeakCheckBox.setChecked(True)
        self.footPeakCheckBox.stateChanged.connect(
            lambda state, name=checkboxName: self._checkboxCallback(state, name)
        )
        hBoxLayoutControls2.addWidget(self.footPeakCheckBox)

        checkboxName = "Line Intensity"
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setToolTip('Toggle intensity sum plot on/off.')
        aCheckBox.setChecked(True)
        aCheckBox.stateChanged.connect(
            lambda state, name=checkboxName: self._checkboxCallback(state, name)
        )
        hBoxLayoutControls2.addWidget(aCheckBox)

        # popup to select ()'sum intensity' or 'range intensity')
        self._linePlotCombo = QtWidgets.QComboBox()
        self._linePlotCombo.setToolTip('Select the type of intensity plot.')
        self._linePlotCombo.addItem('Intensity Sum')
        self._linePlotCombo.addItem('Intensity Range')
        self._linePlotCombo.currentTextChanged.connect(
            self._on_line_intensity_popup
        )
        hBoxLayoutControls2.addWidget(self._linePlotCombo)

        checkboxName = "Fit On Kym"
        aCheckBox = QtWidgets.QCheckBox(checkboxName)
        aCheckBox.setToolTip('Toggle diameter fit on kymograph image on/off.')
        aCheckBox.setChecked(self._fitIsVivible)
        aCheckBox.stateChanged.connect(
            lambda state, name=checkboxName: self._checkboxCallback(state, name)
        )
        hBoxLayoutControls2.addWidget(aCheckBox)

        # hBoxLayoutControls2.addStretch()
        
        # 3rd row of controls
        # hBoxLayoutControls3 = QtWidgets.QHBoxLayout()

        # percentMaxLabel = QtWidgets.QLabel('y: um/pixel')
        # hBoxLayoutControls3.addWidget(percentMaxLabel)

        # percentMaxLabel = QtWidgets.QLabel('x: sec/line')
        # hBoxLayoutControls3.addWidget(percentMaxLabel)

        # todo: add this in
        # _leftControlBar = self.leftControlBar()
        # vBoxLayout.addLayout(_leftControlBar)

        # add 2 rows of controls
        vBoxLayout.addLayout(hBoxLayoutControls)
        vBoxLayout.addLayout(hBoxLayoutControls1)
        vBoxLayout.addLayout(hBoxLayoutControls2)
        # vBoxLayout.addLayout(hBoxLayoutControls3)

        # 1) kymograph image
        if 0:
            self.kymographWindow = pg.PlotWidget()
            self.kymographWindow.setLabel("left", "Line Scan", units="")
            # self.kymographWindow.setLabel('bottom', 'Time', units='')

            self.kymographImage = pg.ImageItem(self._kymographAnalysis.getImage())
            # setRect(x, y, w, h)
            imageRect = self._kymographAnalysis.getImageRect()  # (x,y,w,h)
            # pos, size = self._kymographAnalysis.getFullRectRoi()  # (x,y,w,h)
            self.kymographImage.setRect(
                imageRect[0], imageRect[1], imageRect[2], imageRect[3]
            )
            # self.kymographImage.setRect(pos[0], pos[1], size[0], size[1])
            self.kymographWindow.addItem(self.kymographImage)

            # vertical line to show "Line Profile"
            sliceLine = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('y', width=2),)
            self._sliceLinesList.append(
                sliceLine
            )  # keep a list of vertical slice lines so we can update all at once
            self.kymographWindow.addItem(sliceLine)

            # rectangulaar roi over image
            # _penWidth = self._kymographAnalysis.getLineWidth()
            _penWidth = 1
            rectPen = pg.mkPen("r", width=_penWidth)
            pos = self._kymographAnalysis.getPosRoi()
            size = self._kymographAnalysis.getSizeRoi()
            _imageRect = self._kymographAnalysis.getImageRect()  # (x,y,w,h)
            maxBounds = QtCore.QRectF(
                _imageRect[0], _imageRect[1], _imageRect[2], _imageRect[3]
            )
            # print('  init roi pos:', pos)
            # print('  init roi size:', size)
            # print('  init roi pos:', maxBounds)
            self._rectRoi = pg.ROI(pos=pos, size=size, maxBounds=maxBounds, pen=rectPen)
            self._rectRoi.addScaleHandle(pos=(1, 0), center=(0, 1))
            self._rectRoi.sigRegionChangeFinished.connect(
                self._slot_roi_changed
            )  # remove
            self.kymographWindow.addItem(self._rectRoi)

            vBoxLayout.addWidget(self.kymographWindow)

        #
        # 1.5) slider to step through "Line Profile"
        if 0:
            self.profileSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.profileSlider.setMinimum(0)
            self.profileSlider.setMaximum(self._kymographAnalysis.numLineScans())
            self.profileSlider.valueChanged.connect(self._on_slider_changed)
            vBoxLayout.addWidget(self.profileSlider)

        #
        # plot of just one line intensity
        self.lineIntensityPlotItem = pg.PlotWidget(name='lineProfile')
        self.lineIntensityPlotItem.setLabel("left", 'Intensity', units="")
        self.lineIntensityPlotItem.setLabel("bottom", 'um', units="")
        # self.lineIntensityPlotItem.setVisible(True)
        self.lineIntensityPlot = self.lineIntensityPlotItem.plot(
            name="lineIntensityPlot"
        )
        if self._kymographAnalysis is not None:
            xPlot = np.arange(0, self._kymographAnalysis.numLineScans())
        else:
            xPlot = np.arange(0, 0)
        yPlot = xPlot * np.nan
        xPlot = []
        yPlot = []
        self.lineIntensityPlot.setData(xPlot, yPlot,
                                        pen=pg.mkPen('y', width=2),
                                       connect="finite")  # fill with nan
        # single point of left/right
        self.leftRightPlot = self.lineIntensityPlotItem.plot(name="leftRightPlot", pen='c')

        # self._sanpyCursors = sanpy.interface.sanpyCursors(self.lineIntensityPlotItem, showInView=True)
        # self._sanpyCursors.signalCursorDragged.connect(self.updateStatusBar)
        # self._sanpyCursors.signalSetDetectionParam.connect(self._setDetectionParam)

        vBoxLayout.addWidget(self.lineIntensityPlotItem)

        #
        # 3) dimaeter of each line scan
        self.diameterPlotItem = pg.PlotWidget()
        self.diameterPlotItem.setLabel("left", "Diameter", units="")
        self.diameterPlot = self.diameterPlotItem.plot(
                                name="diameterPlot",
                                pen=pg.mkPen('c', width=1),
                                # 20230919 paula
                                # symbol='o',
                                # symbolPen='c'
                                )
        # if self._kymographAnalysis is not None:
        #     xPlot = np.arange(0, self._kymographAnalysis.numLineScans())
        # else:
        #     xPlot = np.arange(0, 0)
        # yPlot = xPlot * np.nan
        xPlot = []
        yPlot = []
        self.diameterPlot.setData(xPlot, yPlot, connect="finite")  # fill with nan
        # link x-axis with kymograph PlotWidget
        # self.diameterPlotItem.setXLink(self.kymographWindow)
        # link to kymographWidget plot of the image
        self.diameterPlotItem.setXLink(self._kymWidgetMain.kymographPlot)

        # vertical line to show "Line Profile"
        sliceLine = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('y', width=2),)
        self._sliceLinesList.append(
            sliceLine
        )  # keep a list of vertical slice lines so we can update all at once
        self.diameterPlotItem.addItem(sliceLine)

        # overlay scatter of foot and peak
        _footPeakSize = 6
        # self._diamFootPlotItem = pg.ScatterPlotItem(
        #     size=_footPeakSize, brush=pg.mkBrush('r')
        # )
        self._diamFootPlotItem = pg.PlotDataItem(
            pen=None,
            symbol='o',
            symbolSize=_footPeakSize,
            symbolPen=None,
            symbolBrush='r',
        )
        # self._diamFootPlotItem = pg.PlotDataItem(pen=None,
        #                                   symbol='o',
        #                                 symbolBrush='r',
        #                                 fillOutline=False,
        #                                 markeredgewidth=0.0,
        #                                 size=_footPeakSize,
        #                                 connect="finite")
        self.diameterPlotItem.addItem(self._diamFootPlotItem, ignorBounds=True)
        
        # _footPeakSize = 5
        # self._diamPeakPlotItem = pg.ScatterPlotItem(
        #     size=_footPeakSize, brush=pg.mkBrush('r')
        # )
        self._diamPeakPlotItem = pg.PlotDataItem(
            pen=None,
            symbol='o',
            symbolSize=_footPeakSize,
            symbolPen=None,
            symbolBrush='b',
        )
        # self._diamPeakPlotItem = pg.PlotDataItem(pen=None,
        #                                   symbol='o',
        #                                 symbolBrush='b',
        #                                 fillOutline=False,
        #                                 markeredgewidth=0.0,
        #                                 size=_footPeakSize,
        #                                 connect="finite")
        self.diameterPlotItem.addItem(self._diamPeakPlotItem, ignorBounds=True)

        vBoxLayout.addWidget(self.diameterPlotItem)

        # 4) sum intensity of each line scan
        self.sumIntensityPlotItem = pg.PlotWidget()
        self.sumIntensityPlotItem.setLabel("left", "Sum Intensity", units="")
        self.sumIntensityPlot = self.sumIntensityPlotItem.plot(name="sumIntensityPlot")
        # TODO: fix
        if self._ba is not None:
            _recordingDur = self._ba.fileLoader.recordingDur
        else:
            _recordingDur = 0
        # xPlot = np.arange(0, self._kymographAnalysis.numLineScans())
        xPlot = []  # np.arange(0, _recordingDur)
        yPlot = []  # xPlot * np.nan
        self.sumIntensityPlot.setData(xPlot, yPlot, connect="finite")  # fill with nan
        # link x-axis with kymograph PlotWidget
        # self.sumIntensityPlotItem.setXLink(self.kymographWindow)
        # Link this view’s X axis to another view. (see LinkView)
        # link to kymographWidget plot of the image
        self.sumIntensityPlotItem.setXLink(self._kymWidgetMain.kymographPlot)

        # vertical line to show "Line Profile"
        sliceLine = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('y', width=2),)
        self._sliceLinesList.append(
            sliceLine
        )  # keep a list of vertical slice lines so we can update all at once
        self.sumIntensityPlotItem.addItem(sliceLine)

        vBoxLayout.addWidget(self.sumIntensityPlotItem)

        # finalize (only for QWidget)
        # self.setLayout(vBoxLayout)

    def _resetZoom(self):
        """Set all pyqtgraph plots to full zoom
        """
        
        self._kymWidgetMain._resetZoom(doEmit=False)
        
        # self.vmPlot.autoRange(items=[self.vmPlot_])  # 20221003
        self.diameterPlotItem.autoRange()
        self.sumIntensityPlotItem.autoRange()

    def refreshSumLinePlot(self, autoRange='all'):
        if self._ba is None:
            return

        xPlot = self._ba.fileLoader.sweepX
        yPlot = np.zeros(len(xPlot))

        if self._plotSumType == 'Intensity Sum':
            leftLabel = 'Intensity Sum'
            yPlot = self._ba.fileLoader.sweepY
        else:
            # plot the intensity range of each line scan
            leftLabel = 'Intensity Range'
            if self._kymographAnalysis.hasDiamAnalysis():
                yPlot = self._kymographAnalysis.getResults('rangeInt')

        if yPlot is not None:
            self.sumIntensityPlot.setData(xPlot, yPlot, connect="finite")

        self.sumIntensityPlotItem.setLabel("left", leftLabel, units="")
        
        # if autoRange:
        #     self.sumIntensityPlotItem.autoRange()

        if autoRange == 'all':
            self.sumIntensityPlotItem.autoRange()
        elif autoRange == 'y':
            if yPlot is not None:
                self.sumIntensityPlotItem.setRange(yRange=[min(yPlot), max(yPlot)])
        elif autoRange == 'x':
            self.sumIntensityPlotItem.setRange(xRange=[min(xPlot), max(xPlot)])

    def refreshDiameterPlot(self, autoRange='all'):
        """
        autoRange in ['none', 'x', 'y', 'none']
        """
        if self._ba is None:
            return

        logger.info(f'refreshing with self._plotDiamType: "{self._plotDiamType}"')

        xPlot = self._ba.fileLoader.sweepX

        if self._plotDiamType == 'Diameter (um)':
            leftLabel = 'Diameter (um)'
            yDiamPlot = self._kymographAnalysis.getResults("diameter_um")
        elif self._plotDiamType == 'Diameter Filtered (um)':
            leftLabel = 'Diameter Filtered (um)'
            # yDiamPlot = self._kymographAnalysis.getResults("diameter_um_filt")
            yDiamPlot = self._kymographAnalysis.getResults("diameter_um_golay")
        elif self._plotDiamType == 'Start (um)':
            leftLabel = 'Start (um)'
            yDiamPlot = self._kymographAnalysis.getResults("left_um")
        elif self._plotDiamType == 'Stop (um)':
            leftLabel = 'Stop (um)'
            yDiamPlot = self._kymographAnalysis.getResults("right_um")
        else:
            logger.error(f'did not understand _plotDiamType: "{self._plotDiamType}"')
            yDiamPlot = None

        # showFinalFilter = True
        # if showFinalFilter:
        #     yDiam_um = self._kymographAnalysis.getResults("diameter_um_filt")
        # else:
        #     yDiam_um = self._kymographAnalysis.getResults("diameter_um")
        
        if yDiamPlot is not None:
            self.diameterPlot.setData(xPlot, yDiamPlot, connect="finite")
            self.diameterPlotItem.setLabel("left", leftLabel, units="")
        else:
            self.diameterPlot.setData([], [])

        # update the scatter of foot and peak
        xFoot = []
        yFoot = []
        xPeak = []
        yPeak = []
        if self._plotDiamType in ['Diameter (um)', 'Diameter Filtered (um)']:

            xFoot = self._ba.getStat('k_diam_foot_sec')
            yFoot = self._ba.getStat('k_diam_foot')
            xPeak = self._ba.getStat('k_diam_peak_sec')
            yPeak = self._ba.getStat('k_diam_peak')

        self._diamFootPlotItem.setData(xFoot, yFoot,
                                        #symbolBrush='r',
                                        # pen=None,
                                        # symbol='o'
                                        )
        self._diamPeakPlotItem.setData(xPeak, yPeak,
                                        # pen=None,
                                        # symbol='o'
                                        )

        # show start/stop of fit in main kymograph
        left_pnt = self._kymographAnalysis.getResults("left_pnt")
        right_pnt = self._kymographAnalysis.getResults("right_pnt")
        self._kymWidgetMain.updateLeftRightFit(
            left_pnt, right_pnt, visible=self._fitIsVivible
        )

        if autoRange == 'all':
            self.diameterPlotItem.autoRange()
        elif autoRange == 'y':
            self.diameterPlotItem.setRange(yRange=[min(yDiamPlot), max(yDiamPlot)])
        elif autoRange == 'x':
            self.diameterPlotItem.setRange(xRange=[min(xPlot), max(xPlot)])

def exportDiameter():
    import sanpy.interface.bExportWidget
    
    logger.info('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    path = '/Users/cudmore/Dropbox/data/cell-shortening/cell 05.tif'
    ba = sanpy.bAnalysis(path)

    ba.kymAnalysis.analyzeDiameter()

    x = ba.kymAnalysis.getResults('time_sec')
    y = ba.kymAnalysis.getResults('diameter_um')

    x = np.array(x)
    y = np.array(y)

    logger.info(x[0:20])
    logger.info(y[0:20])
    
    xyUnits = ("Time (sec)", "DImaeter (um)")

    xMin = 0
    xMax = 10
    xMargin = 0

    type = 'vm'

    exportWidget = sanpy.interface.bExportWidget(
        x,
        y,
        xyUnits=xyUnits,
        path=path,
        xMin=xMin,
        xMax=xMax,
        xMargin=xMargin,
        type=type,
        darkTheme=True,
    )

    exportWidget.show()

    return exportWidget

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    qdarktheme.setup_theme()

    path = "/Users/cudmore/data/kym-example/control 2.5_0012.tif.frames/control 2.5_0012.tif"
    # path = '/Users/cudmore/data/sa-node-ca-video/HighK-aligned-8bit_ch1.tif'

    path = "/Users/cudmore/data/rosie/Raw data for contraction analysis/Female Old/filter median 1 C2-0-255 Cell 2 CTRL  2_5_21 female wt old.tif"

    path = 'data/kymograph/rosie-kymograph.tif'

    #path = '/Users/cudmore/Dropbox/data/cell-shortening/cell 03.tif'
    # path = '/Users/cudmore/Dropbox/data/cell-shortening/cell 05.tif'
    #path = '/Users/cudmore/Dropbox/data/cell-shortening/Cell 04_C002T001.tif'
    

    ba = sanpy.bAnalysis(path)

    kw = kymographPlugin2(ba)
    kw.show()

    # ed = exportDiameter()

    # print(kw._kymographAnalysis._getHeader())

    sys.exit(app.exec_())
