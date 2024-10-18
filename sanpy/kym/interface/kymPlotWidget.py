from functools import partial
import numpy as np
import pandas as pd
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

from sanpy.interface.util import sanpyCursors

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class KymPlotWidget(QtWidgets.QWidget):
    """Plot a trace like sum intensity or diameter and overlay KymAnalysis results.
    """

    signalCursorMove = QtCore.pyqtSignal(object)  # roi

    def __init__(self):
        super().__init__()

        self.xPlot = None
        self.yPlot = None
    
        self._buildUI()

        # re-wire right-click (for entire widget)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu)


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
        self.sumIntensityPlotItem.autoRange()

    def setMouseEnabled(self, x : bool, y : bool):
        self.sumIntensityPlotItem.setMouseEnabled(x=x, y=y)

    def plotItem(self):
        return self.sumIntensityPlotItem.plotItem

    def setXLink(self, plotItem):
        self.sumIntensityPlotItem.setXLink(plotItem)

    def _buildUI(self):
        vBoxPlot = QtWidgets.QVBoxLayout()
        # vBoxPlot.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(vBoxPlot
                       )
        self.sumIntensityPlotItem = pg.PlotWidget()
        self.sumIntensityPlotItem.setDefaultPadding()
        self.sumIntensityPlotItem.enableAutoRange()
        self.sumIntensityPlotItem.setMouseEnabled(x=True, y=False)
        self.sumIntensityPlotItem.hideButtons()  # hide the little 'A' button to rescale axis

        # self.sumIntensityPlotItem.setLabel("left", 'Santana Intensity (f/f0)', units="")
        self.sumIntensityPlotItem.setLabel("bottom", 'Time (s)', units="")
        # self.sumIntensityPlotItem.setXLink(self.kymographPlot)

        # the actual plot
        self.sumIntensityPlot = self.sumIntensityPlotItem.plot(name="sumIntensityPlot",
                                                        pen=pg.mkPen(width=3),
                                                        #   symbol='o',
                                                        #   brush=pg.mkBrush(100, 255, 100, 220),
                                                        )   
        
        self._sanpyCursors = sanpyCursors(self.sumIntensityPlotItem, showCursorD=True)
        self._sanpyCursors.toggleCursors(False)  # initially hidden
        self._sanpyCursors.signalCursorDragged.connect(self.mySetStatusbar)

        self._initSumPlotOverlays()  # requires
        self.sumOverlayToolbar = self._buildPlotOverlayToolbar()

        # order matters
        vBoxPlot.addWidget(self.sumOverlayToolbar)
        vBoxPlot.addWidget(self.sumIntensityPlotItem)

    def setRoiLabelText(self, text):
        self._selectedRoiLabel.setText(text)

    def setNumPeaksLabelText(self, text):
        self._numPeaksLabel.setText(text)

    def mySetStatusbar(self, event):
        # logger.info(event)
        self.signalCursorMove.emit(event)

    def _initSumPlotOverlays(self):
        """"Initialize a number of overlay plots on top of self.sumIntensityPlotItem.
        
        e.g. (peak, threshold, half-width, etc) taken from KymAnalysis
        """

        # scatter plots that go over peak detection
        self._overlayPlotDict = {}

        self._overlayPlotDict['Threshold'] = self.sumIntensityPlotItem.plot(name="sumIntensityPeaksPlot",
                                                  pen=None,
                                                  symbol='o',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(255, 0, 0, 220)
                                                  )

        self._overlayPlotDict['Decay'] = self.sumIntensityPlotItem.plot(name="sumIntensityPeaksPlot",
                                                  pen=None,
                                                  symbol='t',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(255, 0, 255, 220)
                                                  )

        self._overlayPlotDict['Peak Int'] = self.sumIntensityPlotItem.plot(name="Peak Int",
                                                  pen=None,
                                                  symbol='o',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(0, 255, 0, 220)
                                                  )

        # Peak 90 Bin
        self._overlayPlotDict['Onset 10'] = self.sumIntensityPlotItem.plot(name="Onset 10",
                                                  pen=None,
                                                  symbol='x',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(0, 255, 0, 220)
                                                  )

        # Decay 90 Bin
        self._overlayPlotDict['Decay 10'] = self.sumIntensityPlotItem.plot(name="Decay 10",
                                                  pen=None,
                                                  symbol='x',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(0, 255, 0, 220)
                                                  )

        # Peak 90 Bin
        self._overlayPlotDict['Onset 90'] = self.sumIntensityPlotItem.plot(name="Onset 90",
                                                  pen=None,
                                                  symbol='x',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(0, 255, 0, 220)
                                                  )

        # Decay 90 Bin
        self._overlayPlotDict['Decay 90'] = self.sumIntensityPlotItem.plot(name="Decay 90",
                                                  pen=None,
                                                  symbol='x',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(0, 255, 0, 220)
                                                  )

        self._overlayPlotDict['Half-width'] = self.sumIntensityPlotItem.plot(name="sumIntensityPeaksPlot",
                                                #   pen=None,
                                                  symbol='o',
                                                  symbolPen=None,
                                                  symbolSize=10,
                                                  symbolBrush=pg.mkBrush(0, 255, 255, 220)
                                                  )

        self._overlayPlotDict['Exp Decay'] = self.sumIntensityPlotItem.plot(name="sumIntensityPeaksPlot",
                                                  pen=pg.mkPen(color='m', width=2),
                                                #   symbol='o',
                                                #   symbolPen=None,
                                                #   symbolSize=10,
                                                #   symbolBrush=pg.mkBrush(0, 255, 255, 220)
                                                  )
        self._overlayPlotDict['Exp Decay'].setVisible(False)

        self._overlayPlotDict['Dbl Exp Decay'] = self.sumIntensityPlotItem.plot(name="dbl exp decay",
                                                  pen=pg.mkPen(color='y', width=2),
                                                #   symbol='o',
                                                #   symbolPen=None,
                                                #   symbolSize=10,
                                                #   symbolBrush=pg.mkBrush(0, 255, 255, 220)
                                                  )
        self._overlayPlotDict['Dbl Exp Decay'].setVisible(False)

    def setData(self, xPlot, yPlot):
        """Refresh the main line plot.
        """
        self.xPlot = xPlot
        self.yPlot = yPlot
        
        self.sumIntensityPlot.setData(xPlot, yPlot)

    def clearPlot(self):
        self.setData([], [])

        for _key, _item in self._overlayPlotDict.items():
            _item.setData([], [])

    def _buildPlotOverlayToolbar(self):
        """Dynamically build a number of check boxes from keys in _overlayPlotDict.
        
        A VBox with two HBox rows.
        """
        vBox = QtWidgets.QVBoxLayout()
        
        hBox = QtWidgets.QHBoxLayout()
        hBox.setAlignment(QtCore.Qt.AlignLeft)
        vBox.addLayout(hBox)

        hBox2 = QtWidgets.QHBoxLayout()
        hBox2.setAlignment(QtCore.Qt.AlignLeft)
        vBox.addLayout(hBox2)

        thisHBox = hBox
        for aCheckBoxName in self._overlayPlotDict.keys():
            aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
            aCheckBox.setChecked(self._overlayPlotDict[aCheckBoxName].isVisible())
            aCheckBox.stateChanged.connect(
                partial(self._on_checkbox_clicked, aCheckBoxName)
            )
            if aCheckBoxName == 'Half-width':
                thisHBox = hBox2
            thisHBox.addWidget(aCheckBox)
        
        # lab to show selected roi
        self._selectedRoiLabel = QtWidgets.QLabel('ROI: None')
        hBox2.addWidget(self._selectedRoiLabel)
        self._numPeaksLabel = QtWidgets.QLabel('Peaks: None')
        hBox2.addWidget(self._numPeaksLabel)

        _widget = QtWidgets.QWidget()
        _widget.setLayout(vBox)

        return _widget

    def _on_checkbox_clicked(self, name, value):
        if value > 0:
            value = 1
        
        if name in self._overlayPlotDict.keys():
            self._overlayPlotDict[name].setVisible(value)

        else:
            logger.info(f'did not understand name:"{name}"')

    def replotOverlays(self, dfPlot : pd.DataFrame):
        """
        Parameters
        ==========
        dfPlot : pd.DataFrame
            From kymAnalysis
        """
        numPeaks = len(dfPlot)

        self.setNumPeaksLabelText(f'Peaks:{numPeaks}')

        # onset/offset at 90%
        # onset10Bin = dfPlot['Onset 10 Bin']
        # onset10Seconds = self.xPlot[onset10Bin]
        # onset10Value = self.yPlot[onset10Bin]
        onset10Seconds = dfPlot['Onset 10 Second']
        onset10Value = dfPlot['Onset 10 Int']
        self._overlayPlotDict['Onset 10'].setData(onset10Seconds, onset10Value)

        # decay10Bin = dfPlot['Decay 10 Bin']
        # decay10BinSeconds = self.xPlot[decay10Bin]
        # decay10Value = self.yPlot[decay10Bin]            
        decay10BinSeconds = dfPlot['Decay 10 Second']
        decay10Value = dfPlot['Decay 10 Int']
        self._overlayPlotDict['Decay 10'].setData(decay10BinSeconds, decay10Value)

        # orig
        peakSecond = dfPlot['Peak Second']
        yPeak = dfPlot['Peak Int']
        self._overlayPlotDict['Peak Int'].setData(peakSecond, yPeak)

        thresholdSecond = dfPlot['Onset Second']
        thresholdValue = dfPlot['Onset Int']
        self._overlayPlotDict['Threshold'].setData(thresholdSecond, thresholdValue)

        decaySecond = dfPlot['Decay Second']
        decayValue = dfPlot['Decay Int']
        self._overlayPlotDict['Decay'].setData(decaySecond, decayValue)

        # Threshold 90 and Decay 90
        peak90Second = dfPlot['Onset 90 Second']
        peak90Value = dfPlot['Onset 90 Int']
        self._overlayPlotDict['Onset 90'].setData(peak90Second, peak90Value)

        decay90Second = dfPlot['Decay 90 Second']
        decay90Value = dfPlot['Decay 90 Int']
        self._overlayPlotDict['Decay 90'].setData(decay90Second, decay90Value)

        # half width
        xHalfwidth = []
        yHalfwidth = []
        for _peakIdx in range(numPeaks):
            hwLeftBin = dfPlot['HW Left Bin'][_peakIdx]
            hwLeftSec = self.xPlot[hwLeftBin]

            hwRightBin = dfPlot['HW Right Bin'][_peakIdx]
            hwRightSec = self.xPlot[hwRightBin]

            xHalfwidth.append( hwLeftSec )
            xHalfwidth.append( hwRightSec )
            xHalfwidth.append( np.nan )

            yHalfwidth.append( dfPlot['HW Height'][_peakIdx] )
            yHalfwidth.append( dfPlot['HW Height'][_peakIdx] )
            yHalfwidth.append( np.nan )

        self._overlayPlotDict['Half-width'].setData(xHalfwidth, yHalfwidth)

        
        # turned off -->> we do not have ms2bin()
        if 0:
            # (1) exp decay
            from sanpy.kym.kymRoiAnalysis import myMonoExp
            xDecay = []
            yDecay = []
            _peakBins = dfPlot['Peak Bin']
            for _peakIdx, _peakBin in enumerate(_peakBins):
                
                # fix this constant bug !!!!
                # [_left, _, _, _] = self.roiList._roiAsRect(roi)
                # _peakBin = _peakBin - _left
                
                fit_m = dfPlot['fit_m'][_peakIdx]            
                fit_tau = dfPlot['fit_tau'][_peakIdx]
                fit_b = dfPlot['fit_b'][_peakIdx]

                if np.isnan(fit_m):
                    logger.warning(f'no exp fit for peak {_peakIdx}')
                    continue

                decayFitBins = self._msToBin(self._detectionDict['Decay (ms)'])
                _xRange = np.arange(decayFitBins)
                # get line showing our fit
                fit_y = myMonoExp(_xRange, fit_m, fit_tau, fit_b)

                xDecay.extend(_xRange + self.xPlot[_peakBin])
                xDecay.append(np.nan)

                yDecay.extend(fit_y)
                yDecay.append(np.nan)

            self._overlayPlotDict['Exp Decay'].setData(xDecay, yDecay)

        #
        # (2) double exp decay
        # xDecay = []
        # yDecay = []
        # _peakBins = dfPlot['Peak Bin']
        # for _peakIdx, _peakBin in enumerate(_peakBins):
            
        #     # fix this constant bug !!!!
        #     [_left, _, _, _] = self.roiList._roiAsRect(roi)
        #     _peakBin = _peakBin - _left
            
        #     fit_m1 = dfPlot['fit_m1'][_peakIdx]            
        #     fit_tau1 = dfPlot['fit_tau1'][_peakIdx]
        #     fit_m2 = dfPlot['fit_m2'][_peakIdx]            
        #     fit_tau2 = dfPlot['fit_tau2'][_peakIdx]

        #     if np.isnan(fit_m1):
        #         # logger.warning(f'no fit for peak {_peakIdx}')
        #         continue

        #     # decayFitBins = self._detectionDict['decay (ms)'] / 1000 / self.secondsPerLine
        #     decayFitBins = self._msToBin(self._detectionDict['decay (ms)'])
        #     _xRange = xPlot[_peakBin:_peakBin+decayFitBins] - xPlot[_peakBin]
            
        #     # get line showing our fit
        #     fit_y = myDoubleExp(_xRange, fit_m1, fit_tau1, fit_m2, fit_tau2)

        #     xDecay.extend(_xRange+xPlot[_peakBin])
        #     xDecay.append(np.nan)

        #     yDecay.extend(fit_y)
        #     yDecay.append(np.nan)

        # self._overlayPlotDict['Dbl Exp Decay'].setData(xDecay, yDecay)

        # refresh cursors
        self._sanpyCursors._showInView()
