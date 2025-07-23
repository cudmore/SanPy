from functools import partial
from typing import Optional

import numpy as np
import pandas as pd
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

from sanpy.interface.util import sanpyCursors

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, PeakDetectionTypes
from sanpy.kym.kymRoiResults import KymRoiResults

from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


class KymPlotWidget(QtWidgets.QWidget):
    """Plot a trace like sum intensity or diameter and overlay KymAnalysis results."""

    signalCursorMove = QtCore.pyqtSignal(object)  # roi

    def __init__(
        self,
        kymRoiAnalysis: KymRoiAnalysis,
        xTrace: str,
        yTrace: str,  # we get seeded with one (e.g. f/f0) but can switch to other
        peakDetectionType: PeakDetectionTypes,
    ):
        super().__init__()

        self._kymRoiAnalysis = kymRoiAnalysis

        self.peakDetectionType = peakDetectionType

        self._additionalKeys = ['Half-Width', 'Exp Decay']
        # need to be defined in self._overlayPlotDict

        # sloppy
        self._rightAxisPlot = None

        self._buildUI()

        for _channel in range(self._kymRoiAnalysis.numChannels):
            self._showHideOverlays(_channel, True)

        # re-wire right-click (for entire widget)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu)

    def slot_selectRoi(self, channelIdx: int, roiLabel: Optional[str]):
        """Select an roi in one channel."""
        # logger.info(f'channelIdx:{channelIdx} roiLabel:{roiLabel} self.peakDetectionType:{self.peakDetectionType}')

        if not self.isVisible():
            return

        if roiLabel is None:
            # clear all plots
            self.sumIntensityPlot.setData(np.array([]), np.array([]))

            if self._rightAxisPlot is not None:
                self._rightAxisPlot.setData(np.array([]), np.array([]))

            for _channel in range(self._kymRoiAnalysis.numChannels):
                self.replotOverlays(_channel, roiLabel)

            self.setRoiLabelText('ROI: None')
            self.setNumPeaksLabelText('Peaks: None')
            return

        # backend KymRoi
        kymRoi = self._kymRoiAnalysis.getRoi(roiLabel)

        # replot one channel
        # _channel = channelIdx
        # if 1:
        for _channel in range(self._kymRoiAnalysis.numChannels):
            if _channel == 0:
                thisPlot = self.sumIntensityPlot
            else:
                thisPlot = self._rightAxisPlot

            # get what was detected, may change yPlot
            _detectionParams = kymRoi.getDetectionParams(
                _channel, self.peakDetectionType
            )
            # the trace that was detected
            detectThisTrace = _detectionParams.getParam('detectThisTrace')

            xPlot = kymRoi.getTrace(_channel, 'Time (s)')
            yPlot = kymRoi.getTrace(_channel, detectThisTrace)

            # xPlot (time s) will always have values, yPlot might all be nan
            yAllNan = np.isnan(yPlot).all()
            if yAllNan:
                logger.info(
                    f'detectThisTrace:{detectThisTrace} is all nan, setting x to nan as well.'
                )
                # xPlot[:] = np.nan
                xPlot = np.array([])
                yPlot = np.array([])

            # logger.info(f'  _channel:{_channel} detectThisTrace:"{detectThisTrace}"')
            # logger.info(f'      xPlot:{xPlot}')
            # logger.info(f'      yPlot:{yPlot}')

            thisPlot.setData(xPlot, yPlot)
            if _channel == 0:
                self.sumIntensityPlotItem.setLabel("left", detectThisTrace, units="")
            else:
                self.sumIntensityPlotItem.setLabel("right", detectThisTrace, units="")

            # overlay for given channel
            self.replotOverlays(_channel, roiLabel)

        _txt = f'ROI: {roiLabel}'
        self.setRoiLabelText(_txt)

        # logger.warning('extend number o fpeaks to both ch1 and ch2')
        # _txt = f'Peaks: {len(dfPlot)}'
        # self.setNumPeaksLabelText(_txt)

    def _contextMenu(self, pos):
        """Context menu for entire widget.

        See also myRawContextMenu.
        """
        logger.info('')

        # build menu
        contextMenu = QtWidgets.QMenu()
        contextMenu.addAction('Full Zoom')
        contextMenu.addSeparator()

        cursorAction = QtWidgets.QAction('Cursors')
        cursorAction.setCheckable(True)
        cursorAction.setChecked(self._sanpyCursors.cursorsAreShowing())
        contextMenu.addAction(cursorAction)
        contextMenu.addSeparator()

        toolbarAction = QtWidgets.QAction('Overlay Toolbar')
        toolbarAction.setCheckable(True)
        toolbarAction.setChecked(self.sumOverlayToolbar.isVisible())
        contextMenu.addAction(toolbarAction)
        # contextMenu.addSeparator()

        # show menu
        pos = self.mapToGlobal(pos)
        action = contextMenu.exec_(pos)
        if action is None:
            return

        # respond to menu selection
        actionText = action.text()

        if actionText == 'Full Zoom':
            self.autoRange()

        elif actionText == 'Cursors':
            self._sanpyCursors.toggleCursors(action.isChecked())

        elif actionText == 'Overlay Toolbar':
            self.sumOverlayToolbar.setVisible(action.isChecked())

    def autoRange(self):
        logger.info('')
        self.sumIntensityPlotItem.autoRange()

    def setMouseEnabled(self, x: bool, y: bool):
        logger.info(f'{self.peakDetectionType}')
        # the left axis
        self.sumIntensityPlotItem.setMouseEnabled(x=x, y=y)

        # the right axis
        if self._rightAxisPlotItem is not None:
            self._rightAxisPlotItem.setMouseEnabled(x=x, y=y)

        # AttributeError: 'PlotCurveItem' object has no attribute 'setMouseEnabled'
        # self._rightAxisPlot.setMouseEnabled(x=x, y=y)

    # def plotItem(self):
    #     return self.sumIntensityPlotItem.plotItem

    def setXLink(self, plotItem):
        self.sumIntensityPlotItem.setXLink(plotItem)

    def _buildUI(self):

        # self.setContentsMargins(0, 0, 0, 0)

        vBoxPlot = QtWidgets.QVBoxLayout()
        vBoxPlot.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(vBoxPlot)

        self.sumIntensityPlotItem = pg.PlotWidget()
        self.sumIntensityPlotItem.setDefaultPadding()
        self.sumIntensityPlotItem.enableAutoRange()
        self.sumIntensityPlotItem.setMouseEnabled(x=True, y=False)
        self.sumIntensityPlotItem.hideButtons()  # hide the little 'A' button to rescale axis

        _channelColor = self._kymRoiAnalysis.getChannelColor(0)

        self.sumIntensityPlotItem.setLabel("left", '', color=_channelColor, units="")
        self.sumIntensityPlotItem.setLabel("bottom", 'Time (s)', units="")
        # self.sumIntensityPlotItem.setXLink(self.kymographPlot)

        # get the original font andmake it bigger
        _origFont = self.sumIntensityPlotItem.getAxis("bottom").label.font()
        from sanpy.kym.interface.kymRoiWidget import KymRoiWidget

        _origFont.setPointSize(KymRoiWidget._pgAxisLabelFontSize)
        self.sumIntensityPlotItem.getAxis("bottom").label.setFont(_origFont)
        self.sumIntensityPlotItem.getAxis("left").label.setFont(_origFont)

        # self._leftAxisPlotItem = pg.ViewBox()
        # self.sumIntensityPlotItem.scene().addItem(self._leftAxisPlotItem)

        # self.sumIntensityPlotItem.getAxis('left').setLabel('axis2', color='#00ff00')

        # this is left axis plot (channel 0) - no longer gfp channel 2
        # the actual plot, pg PlotDataItem
        # self.sumIntensityPlot = self.sumIntensityPlotItem.plotItem
        # self.sumIntensityPlot = self.sumIntensityPlotItem.plot(name="sumIntensityPlot",
        #                                                 pen=pg.mkPen('Red', width=2),
        #                                                 #   symbol='o',
        #                                                 #   brush=pg.mkBrush(100, 255, 100, 220),
        #                                                 )

        self.sumIntensityPlot = pg.PlotCurveItem(pen=pg.mkPen(_channelColor, width=2))
        self.sumIntensityPlotItem.addItem(self.sumIntensityPlot)
        # self._leftAxisPlotItem.addItem(self.sumIntensityPlot)

        # logger.info(f'self.sumIntensityPlotItem:{type(self.sumIntensityPlotItem)} {self.sumIntensityPlotItem}')
        # logger.info(f'self.sumIntensityPlot:{type(self.sumIntensityPlot)} {self.sumIntensityPlot}')

        # if more than one channel, add right axis
        # if self._kymRoiAnalysis.numChannels > 1:
        self._addRightAxisPlot()

        #
        # a vertical line to show selected line scan
        self._kymLineScanLine = pg.InfiniteLine(pen=pg.mkPen(color='c', width=2))
        self.sumIntensityPlotItem.addItem(self._kymLineScanLine)

        self._sanpyCursors = sanpyCursors(self.sumIntensityPlotItem, showCursorD=True)
        self._sanpyCursors.toggleCursors(False)  # initially hidden
        self._sanpyCursors.signalCursorDragged.connect(self.mySetStatusbar)

        self._initSumPlotOverlays()  # requires
        self.sumOverlayToolbar = self._buildPlotOverlayToolbar()

        # order matters
        vBoxPlot.addWidget(self.sumOverlayToolbar)
        vBoxPlot.addWidget(self.sumIntensityPlotItem)

    def _updateViews(self):
        ## view has resized; update auxiliary views to match
        pw = self.sumIntensityPlotItem  # plot widget that contains a plotItem

        if self._rightAxisPlotItem is not None:
            p2 = self._rightAxisPlotItem
            p2.setGeometry(pw.plotItem.vb.sceneBoundingRect())

            ## need to re-update linked axes since this was called
            ## incorrectly while views had different shapes.
            ## (probably this should be handled in ViewBox.resizeEvent)
            # p2.linkedViewChanged(p1.vb, p2.XAxis)

            p2.linkedViewChanged(pw.plotItem.vb, p2.XAxis)
            # p2.linkedViewChanged(pw.plotItem.vb, p2.YAxis)

    def _addRightAxisPlot(self):
        """Add a right axis like matplotlib twinx.

        This adds right axis to self.sumIntensityPlotItem

        see: https://github.com/pyqtgraph/pyqtgraph/blob/master/pyqtgraph/examples/MultiplePlotAxes.py
        """

        if self._kymRoiAnalysis.numChannels == 1:
            self._rightAxisPlotItem = None
            return

        p1 = self.sumIntensityPlotItem  # original left axis

        self._rightAxisPlotItem = pg.ViewBox()
        p2 = self._rightAxisPlotItem
        p1.showAxis('right')
        p1.scene().addItem(p2)
        p1.getAxis('right').linkToView(p2)
        p2.setXLink(p1)
        # p2.setYLink(p1)  # this does link but left/right have different scale (does not visially work)
        p1.getAxis('right').setLabel('Channel 2', color='#00ff00')

        self._rightAxisPlot = pg.PlotCurveItem(pen=pg.mkPen('Green', width=2))
        p2.addItem(self._rightAxisPlot)

        self._updateViews()
        # p1.vb.sigResized.connect(self.updateViews)
        pw = self.sumIntensityPlotItem  # plot widget that contains a plotItem
        pw.plotItem.vb.sigResized.connect(self._updateViews)

        #
        # we can setdata on self._rightAxisPlot
        # self._rightAxisPlot.setData(np.array([10, 30, 20]))

    def slot_updateLineProfile(self, lineScanIdx: int):
        """Update vertical line showing current selected line scan."""
        # logger.info(f'lineScanIdx:{lineScanIdx}')
        lineScanSec = lineScanIdx * self._kymRoiAnalysis.secondsPerLine
        self._kymLineScanLine.setPos(lineScanSec)

    def setRoiLabelText(self, text):
        self._selectedRoiLabel.setText(text)

    def setNumPeaksLabelText(self, text):
        self._numPeaksLabel.setText(text)

    def mySetStatusbar(self, event):
        # logger.info(event)
        self.signalCursorMove.emit(event)

    def _on_user_scatter_click(self, scatterPlotItem, spotItems):
        """
        scatterPlotItem : scatterPlotItem
        spotItems : [SpotItem]
        """
        for spotItem in spotItems:
            logger.info(f'spotItem.index():{spotItem.index()}')

    def _initSumPlotOverlays(self):
        """ "Initialize a number of overlay plots on top of self.sumIntensityPlotItem.

        e.g. (peak, threshold, half-width, etc) taken from KymAnalysis
        """

        # scatter plots that go over peak detection
        self._overlayPlotDict = {}

        for _channel in range(self._kymRoiAnalysis.numChannels):
            self._overlayPlotDict[_channel] = {}

            for analysisKey in KymRoiResults.overlayKeys:
                symbol = KymRoiResults.getMarker(analysisKey)
                if symbol is None:
                    symbol = 'o'
                color = KymRoiResults.getColor(analysisKey)
                if color is None:
                    color = (200, 200, 200, 220)
                aPlot = pg.ScatterPlotItem(
                    name=analysisKey,
                    pen=None,  # draws outline
                    symbol=symbol,
                    size=10,
                    brush=pg.mkBrush(color),
                )
                aPlot.sigClicked.connect(self._on_user_scatter_click)
                if _channel == 0:
                    self.sumIntensityPlotItem.addItem(aPlot)
                    # _tmpItem = self.sumIntensityPlotItem.getPlotItem()
                    # logger.info(f'"{analysisKey}" _tmpItem:{_tmpItem}')
                else:
                    self._rightAxisPlotItem.addItem(aPlot)
                self._overlayPlotDict[_channel][analysisKey] = aPlot

            # half-width and exp decay are special cases
            for _additionalKey in self._additionalKeys:
                # connect='finite' will not draw lines between np.nan
                aLinePlot = pg.PlotCurveItem(
                    pen=pg.mkPen('Yellow', width=3),
                    connect='finite',
                    name=_additionalKey,
                )
                aLinePlot.setVisible(False)
                #
                if _channel == 0:
                    self.sumIntensityPlotItem.addItem(aLinePlot)
                else:
                    self._rightAxisPlotItem.addItem(aLinePlot)
                self._overlayPlotDict[_channel][_additionalKey] = aLinePlot

    def clearPlotOverlays(self, channelIdx: int = None):

        if channelIdx is None:
            theseChannels = range(self._kymRoiAnalysis.numChannels)
        else:
            theseChannels = [channelIdx]

        for _channel in theseChannels:
            for _key, _item in self._overlayPlotDict[_channel].items():
                # _item.setData(np.array([]), np.array([]))
                _item.clear()

    def _buildPlotOverlayToolbar(self):
        """Dynamically build a number of check boxes from keys in _overlayPlotDict.

        A VBox with two HBox rows.
        """

        # checkboxes only have one copy, shared between channel 0/1
        self._overlayCheckboxDict = {}

        vBox = QtWidgets.QVBoxLayout()
        vBox.setContentsMargins(0, 0, 0, 0)

        hBox = QtWidgets.QHBoxLayout()
        hBox.setAlignment(QtCore.Qt.AlignLeft)
        vBox.addLayout(hBox)

        # gui will control channel 1 (green, iATP)
        # plots have two channels, here just pull from first
        _channel = 0

        _initThisList = ['Peak Int', 'Onset Int']

        thisHBox = hBox
        _controlsPerRow = 5
        numberCreated = 0
        for analysisResultKey in self._overlayPlotDict[_channel].keys():
            if ' Int' not in analysisResultKey:
                # logger.warning(f'we are only showing analysis results with " Int" in their key, got key:{analysisResultKey}')
                continue
            _isChecked = analysisResultKey in _initThisList
            aCheckBoxName = analysisResultKey.replace(' Int', '')  # strip off ' Int'
            aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
            aCheckBox.setChecked(_isChecked)
            # aCheckBox.setChecked(self._overlayPlotDict[_channel][analysisResultKey].isVisible())
            aCheckBox.stateChanged.connect(
                partial(self._on_checkbox_clicked, aCheckBoxName, _channel)
            )
            self._overlayCheckboxDict[analysisResultKey] = aCheckBox
            # switch to second row
            if (
                numberCreated == _controlsPerRow
            ):  # hard coding 4 checkboxes per row (only two rows)
                thisHBox = QtWidgets.QHBoxLayout()
                thisHBox.setAlignment(QtCore.Qt.AlignLeft)
                vBox.addLayout(thisHBox)
                numberCreated = -1
            thisHBox.addWidget(aCheckBox)

            numberCreated += 1

        # add in additional key like Half-Width and Exp Decay (not explicitly in analysis results)
        for _additionalKey in self._additionalKeys:
            _isChecked = False
            aCheckBox = QtWidgets.QCheckBox(_additionalKey)
            aCheckBox.setChecked(_isChecked)
            # aCheckBox.setChecked(self._overlayPlotDict[_channel][_additionalKey].isVisible())
            aCheckBox.stateChanged.connect(
                partial(self._on_checkbox_clicked, _additionalKey, _channel)
            )
            self._overlayCheckboxDict[_additionalKey] = aCheckBox
            thisHBox.addWidget(aCheckBox)

        #
        hBox_final = QtWidgets.QHBoxLayout()
        hBox_final.setAlignment(QtCore.Qt.AlignLeft)
        vBox.addLayout(hBox_final)

        # add checkboxes to toggle entire channel on/off
        for _channel in range(self._kymRoiAnalysis.numChannels):
            aCheckBoxName = f'Channel {_channel+1}'
            aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
            aCheckBox.setChecked(True)
            aCheckBox.stateChanged.connect(
                partial(self._on_checkbox_clicked, aCheckBoxName, _channel)
            )
            self._overlayCheckboxDict[aCheckBoxName] = aCheckBox
            hBox_final.addWidget(aCheckBox)

        # label to show selected roi
        self._selectedRoiLabel = QtWidgets.QLabel('ROI: None')
        hBox_final.addWidget(self._selectedRoiLabel)
        # label to show number of peaks
        self._numPeaksLabel = QtWidgets.QLabel('Peaks: None')
        hBox_final.addWidget(self._numPeaksLabel)

        _widget = QtWidgets.QWidget()
        _widget.setContentsMargins(0, 0, 0, 0)
        _widget.setLayout(vBox)

        # initially hidden
        _widget.setVisible(False)

        return _widget

    def showingChannel(self, channelIdx):
        """If 'channel 1' and/or channel 2 checkbox is clicked."""
        thisCheckbox = f'Channel {channelIdx+1}'
        return self._overlayCheckboxDict[thisCheckbox].isChecked()

    def _on_checkbox_clicked(self, name, channelIdx, value):
        """
        name : str
            Name of an analysis result key (or _additionalKeys)
        channel : int
            0 based channel index
        """
        if value > 0:
            value = 1

        logger.info(f'name:"{name}" channelIdx:{channelIdx} value:{value}')

        # name might originate from an analysis result key like 'Peak Int'
        intKey = name + ' Int'

        if 'Channel ' in name:
            # toggle one channel on/off
            if channelIdx == 0:
                self.sumIntensityPlot.setVisible(value)
                # this would turn them all on/off (not what we want
                # for _key, _item in self._overlayPlotDict[channelIdx].items():
                #     _item.setVisible(value)

                # turn overlays on/off
                # for on, will follow check box is chacked
                self._showHideOverlays(channelIdx, value)

                # if value == 0:
                #     self.clearPlotOverlays(channelIdx=0)
                # else:
                #     self.replotOverlays(channelIdx=0)

            elif channelIdx == 1:
                # for the right-axis plot, this turns of trace and all overlay
                self._rightAxisPlotItem.setVisible(value)
                self._showHideOverlays(channelIdx, value)

        elif intKey in self._overlayPlotDict[channelIdx].keys():
            for _channel in range(self._kymRoiAnalysis.numChannels):
                logger.info(f'   -->> refreshing _channel:{_channel} intKey:{intKey}')
                if self.showingChannel(_channel):
                    self._overlayPlotDict[_channel][intKey].setVisible(value)

        elif name in self._additionalKeys:
            for _channel in range(self._kymRoiAnalysis.numChannels):
                logger.info(
                    f'   -->> refreshing _channel:{_channel} _additionalKeys name:{name}'
                )
                if self.showingChannel(_channel):
                    self._overlayPlotDict[_channel][name].setVisible(value)

        else:
            logger.info(f'did not understand name:"{name}"')

    def _showHideOverlays(self, channelIdx: int, value: bool):
        """Set Visible of each plot overlay (scatter) based on its checkbox values.

        We have 2x channels of plots but only one set of checkboxes.
        """
        _turningOn = value > 0
        for _key, _item in self._overlayPlotDict[channelIdx].items():
            if _turningOn:
                # don't turn on all overlays, follow check box dict
                _turnOn = self._overlayCheckboxDict[_key].isChecked()
            else:
                _turnOn = value
            _item.setVisible(_turnOn)

    def replotOverlays(self, channelIdx, roiLabel: str):
        """Replot all scatter/line overlay plots.

        Parameters
        ==========
        channel : int
        roiLabel : str
        """

        # logger.info(f'channelIdx:{channelIdx} roiLabel:{roiLabel} self.peakDetectionType:{self.peakDetectionType}-->> replotOverlay with dfPlot:')

        if roiLabel is None:
            logger.warning('   -->> got roiLabel None.')
            self.clearPlotOverlays(channelIdx=channelIdx)
            return

        kymRoi = self._kymRoiAnalysis.getRoi(roiLabel)
        dfPlot = kymRoi.getAnalysisResults(channelIdx, self.peakDetectionType).df

        if len(dfPlot) == 0:
            logger.warning('   -->> got empty analysis dataframe.')
            self.clearPlotOverlays(channelIdx=channelIdx)
            return

        for analysisKey in KymRoiResults.overlayKeys:
            # analysisKey should contain "Int" and is used as y-axis in scatter
            # if 'Int' not in analysisKey:
            #     continue

            if ' Int' in analysisKey:
                xKey = analysisKey.replace(' Int', ' (s)')
                xPlot = dfPlot[xKey].to_numpy()
                yPlot = dfPlot[analysisKey].to_numpy()

                # logger.info(f'channel:{channelIdx} analysisKey:"{analysisKey}"')
                # logger.info(f'  xPlot:{xPlot}')
                # logger.info(f'  yPlot:{yPlot}')

                self._overlayPlotDict[channelIdx][analysisKey].setData(xPlot, yPlot)
                #
                # _isVisible = self._overlayCheckboxDict[analysisKey].isVisible()
                # self._overlayPlotDict[channelIdx][analysisKey].setVisible(_isVisible)

        # refresh additional plots like half-width and exp decay
        for analysisKey in self._additionalKeys:
            if analysisKey == 'Exp Decay':
                xExp, yExp = kymRoi.getExpDecayPlot(
                    channel=channelIdx, peakDetectionType=self.peakDetectionType
                )
                # logger.info(f'channel:{channelIdx} analysisKey:"{analysisKey}"')
                # logger.info(f'  xExp:{xExp}')
                # logger.info(f'  yExp:{yExp}')
                self._overlayPlotDict[channelIdx][analysisKey].setData(xExp, yExp)

            elif analysisKey == 'Half-Width':
                xHalWidth, yHalfWidth = kymRoi.getHalfWidthPlot(
                    channel=channelIdx, peakDetectionType=self.peakDetectionType
                )
                # logger.info(f'channel:{channelIdx} analysisKey:"{analysisKey}"')
                # logger.info(f'  xHalWidth:{xHalWidth}')
                # logger.info(f'  yHalfWidth:{yHalfWidth}')
                self._overlayPlotDict[channelIdx][analysisKey].setData(
                    xHalWidth, yHalfWidth
                )

            #
            # _isVisible = self._overlayCheckboxDict[analysisKey].isVisible()
            # self._overlayPlotDict[channelIdx][analysisKey].setVisible(_isVisible)
