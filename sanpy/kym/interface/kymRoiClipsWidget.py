from functools import partial
from typing import Optional

import numpy as np

from PyQt5 import QtGui, QtCore, QtWidgets
import pyqtgraph as pg

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, PeakDetectionTypes

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class KymRoiClipsWidget(QtWidgets.QWidget):
    """A widget to show peak clips.
    """
    def __init__(self, kymRoiAnalysis : KymRoiAnalysis):
        super().__init__(None)

        self._kymRoiAnalysis : KymRoiAnalysis= kymRoiAnalysis
        
        # so we can replot on gui change
        self._channel = None
        self._roiLabel = None
        
        # gui state
        self._plusMinusMs = 100
        self._plotRaw = True
        self._plotMean = True
        self._plotPercent = True

        self._buildUI()

    def slot_selectRoi(self, channel : int, roiLabel : Optional[str]):
        # logger.info(f'channel:{channel} roi:{roiLabel}')

        self._clearClips()

        # so we can _replot
        self._channel = channel
        self._roiLabel = roiLabel
        
        # plotPeakClips(self, yPlot, xPeakBins, secondsPerLine, plusMinusBins, doDiameter : bool = False)

        if roiLabel is None:
            self._clearClips()
            return
        
        self.plotPeakClips(channel, roiLabel)

    def _buildUI(self):
        vBox = QtWidgets.QVBoxLayout()

        _topToolbar = self._buildTopToolbar()
        vBox.addLayout(_topToolbar)

        # tabs will be peak clips from (f/f0, diameter, phase plots)
        self._tabwidget = QtWidgets.QTabWidget()
        vBox.addWidget(self._tabwidget)

        self.peakClipPlotItem = pg.PlotWidget()
        self.peakClipPlotItem.setLabel("left", "Intensity (%)", units="")
        self.peakClipPlotItem.setLabel("bottom", "Time (s)", units="")

        self.peakClipPlotItem.enableAutoRange()
        self.peakClipPlotItem.setMouseEnabled(x=True, y=False)
        self.peakClipPlotItem.hideButtons()  # hide the little 'A' button to rescale axis

        # raw plot item to update
        self.clipPlot = self.peakClipPlotItem.plot(name="clipPlot",
                                                pen=pg.mkPen('#AAAAAA', width=2),
                                                #   symbol='o',
                                                #   size=4,
                                                #   brush=None,  #pg.mkBrush(100, 255, 100, 220)
                                                  )
        
        # plot mean
        self.meanClipPlot = self.peakClipPlotItem.plot(name="meanClipPlot",
                                                pen=pg.mkPen('r', width=2),
                                                #   symbol='o',
                                                #   size=4,
                                                #   brush=None,  #pg.mkBrush(100, 255, 100, 220)
                                                  )

        self._tabwidget.addTab(self.peakClipPlotItem, "Intensity")
        # vBox.addWidget(self.peakClipPlotItem)

        self._buildPeakDiamPlot()
        self._tabwidget.addTab(self.diameterClipPlotItem, "Diameter")
        self._tabwidget.setCurrentIndex(0)

        # TODO: ADD
        self._buildPhasePlot()
        self._tabwidget.addTab(self.phaseClipPlotItem, "Phase")

        #
        self.setLayout(vBox)

    def _buildPeakDiamPlot(self):
        """Peak clips for diameter.
        """
        self.diameterClipPlotItem = pg.PlotWidget()
        self.diameterClipPlotItem.setLabel("left", "Diameter (%)", units="")
        self.diameterClipPlotItem.setLabel("bottom", "Time (s)", units="")

        self.diameterClipPlotItem.enableAutoRange()
        self.diameterClipPlotItem.setMouseEnabled(x=True, y=False)
        self.diameterClipPlotItem.hideButtons()  # hide the little 'A' button to rescale axis

        # raw plot item to update
        self.diameterClipPlot = self.diameterClipPlotItem.plot(name="diameterClipPlot",
                                                pen=pg.mkPen('#AAAAAA', width=2),
                                                #   symbol='o',
                                                #   size=4,
                                                #   brush=None,  #pg.mkBrush(100, 255, 100, 220)
                                                  )
        
        # plot mean
        self.diameterMeanClipPlot = self.diameterClipPlotItem.plot(name="diameterMeanClipPlot",
                                                pen=pg.mkPen('r', width=2),
                                                #   symbol='o',
                                                #   size=4,
                                                #   brush=None,  #pg.mkBrush(100, 255, 100, 220)
                                                  )
        
        return self.diameterClipPlotItem

    def _buildPhasePlot(self):
        """Phase plot of (peak clip vs diam clip).
        """
        self.phaseClipPlotItem = pg.PlotWidget()
        self.phaseClipPlotItem.setLabel("left", "Diameter (%)", units="")
        self.phaseClipPlotItem.setLabel("bottom", "Intensity", units="")

        self.phaseClipPlotItem.enableAutoRange()
        self.phaseClipPlotItem.setMouseEnabled(x=True, y=False)
        self.phaseClipPlotItem.hideButtons()  # hide the little 'A' button to rescale axis

        # raw plot item to update
        self.phaseClipPlot = self.phaseClipPlotItem.plot(name="phaseClipPlot",
                                                pen=pg.mkPen('#AAAAAA', width=2),
                                                #   symbol='o',
                                                #   size=4,
                                                #   brush=None,  #pg.mkBrush(100, 255, 100, 220)
                                                  )
        self.phaseClipPlot.setData([10, 20, 5], [20, 40, 30])
        
        # plot mean
        self.phaseMeanClipPlot = self.phaseClipPlotItem.plot(name="phaseMeanClipPlot",
                                                pen=pg.mkPen('r', width=2),
                                                #   symbol='o',
                                                #   size=4,
                                                #   brush=None,  #pg.mkBrush(100, 255, 100, 220)
                                                  )

        return self.phaseClipPlotItem
    
    def _buildTopToolbar(self):
        hBox = QtWidgets.QHBoxLayout()
        hBox.setAlignment(QtCore.Qt.AlignLeft)

        aCheckBoxName = 'Raw'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setChecked(self._plotMean)
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hBox.addWidget(aCheckBox)

        aCheckBoxName = 'Mean'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setChecked(self._plotMean)
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hBox.addWidget(aCheckBox)

        aCheckBoxName = 'Y Percent'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setChecked(self._plotPercent)
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hBox.addWidget(aCheckBox)

        # spin box for clip width (ms)
        spinBoxName = 'Clip (ms)'

        aLabel = QtWidgets.QLabel(spinBoxName)
        hBox.addWidget(aLabel)

        aSpinBox = QtWidgets.QSpinBox()
        aSpinBox.setToolTip('Length of the clip (ms)')
        aSpinBox.setRange(1,2000)
        aSpinBox.setSingleStep(5)
        aSpinBox.setValue(self._plusMinusMs)
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hBox.addWidget(aSpinBox)

        return hBox

    def _on_spin_box(self, name, value):
        if name == 'Clip (ms)':
            self._plusMinusMs = value
            self._replot()

        else:
            logger.warning(f'did not understand name "{name}"')

    def _on_checkbox_clicked(self, name, value):
        if value>0:
            value = 1
        # logger.info(f'name:{name} value:{value}')
        
        if name == 'Raw':
            self._plotRaw = value
            self.clipPlot.setVisible(value)
        elif name == 'Mean':
            self._plotRaw = value
            self.meanClipPlot.setVisible(value)

        elif name == 'Y Percent':
            self._plotPercent = value
            self._replot()
            
    def _replot(self):
        self.plotPeakClips(self._channel, self._roiLabel)

    def plotPeakClips(self, channel, roiLabel):
        """
        """
        if roiLabel is None:
            self._clearClips()
            return
        
        # from sanpy.kym.interface.kymRoiWidget import getChannelColor
        _color = self._kymRoiAnalysis.getChannelColor(self._channel)

        kymRoi = self._kymRoiAnalysis.getRoi(roiLabel)  # KymRoi
        
        clipDict = {}
        numIntClips = None
        numDiamClips = None

        for peakDetectionType in PeakDetectionTypes:

            xPlotClips, yPlotClips = kymRoi.getPeakClips(peakDetectionType,
                                                         channel=channel,
                                                         asPercent = self._plotPercent,
                                                         plusMinusMs=self._plusMinusMs)

            if xPlotClips is None or yPlotClips is None:
                # no clips to plot
                # self._clearClips()
                continue
            
            # if xPlotClips is None or yPlotClips is None:
            # logger.warning(f'xPlotClips is: {xPlotClips.shape}')
            # logger.warning(f'xPlotClips is: {xPlotClips}')
            if np.isnan(xPlotClips).all() or np.isnan(yPlotClips).all():
                # no clips to plot
                self._clearClips()
                continue
            
            detectThisTrace = kymRoi.getDetectionParams(channel, peakDetectionType)['detectThisTrace']

            if peakDetectionType == PeakDetectionTypes.intensity:
                
                _xFlatten = xPlotClips.flatten()
                _xFlatten = _xFlatten[~np.isnan(_xFlatten)]

                _yFlatten = yPlotClips.flatten()
                _yFlatten = _yFlatten[~np.isnan(_yFlatten)]

                if len(_yFlatten) != len(_xFlatten):
                    logger.warning(f'   x and y are not the same length: {len(_xFlatten)} != {len(_yFlatten)}')
                    # self.clipPlot.setData(xPlotClips.flatten(), yPlotClips.flatten(), pen=pg.mkPen(color=_color))

                else:
                    # self.clipPlot.setData(xPlotClips.flatten(), yPlotClips.flatten(), pen=pg.mkPen(color=_color))
                    self.clipPlot.setData(_xFlatten, _yFlatten, pen=pg.mkPen(color=_color))
                
                yMean = np.nanmean(yPlotClips, axis=0)
                self.meanClipPlot.setData(xPlotClips[0], yMean)  # assuming xPlotClips[0] is not NaN
                self.peakClipPlotItem.autoRange()
                self.peakClipPlotItem.setLabel("left", detectThisTrace, units="")
                numIntClips = len(yPlotClips)

            elif peakDetectionType == PeakDetectionTypes.diameter:
                self.diameterClipPlot.setData(xPlotClips.flatten(), yPlotClips.flatten(), pen=pg.mkPen(color=_color))
                yMean = np.nanmean(yPlotClips, axis=0)
                self.diameterMeanClipPlot.setData(xPlotClips[0], yMean)
                self.diameterClipPlotItem.setLabel("left", detectThisTrace, units="")
                self.diameterClipPlotItem.autoRange()
                numDiamClips = len(yPlotClips)

            clipDict[peakDetectionType.value] = {
                # 'xPlotClips' : xPlotClips,
                'yPlotClips' : yPlotClips,
            }
        
        if numIntClips is not None and numDiamClips is not None and (numIntClips == numDiamClips):
            xPhase = clipDict[PeakDetectionTypes.intensity.value]['yPlotClips']
            yPhase = clipDict[PeakDetectionTypes.diameter.value]['yPlotClips']
            
            # same number of points
            if len(xPhase[0]) == len(yPhase[0]):
                
                logger.warning('   plotting phase clips -->> -->>')
                print(xPhase.flatten())
                print(yPhase.flatten())
                
                self.phaseClipPlot.setData(xPhase.flatten(), yPhase.flatten())
            
                detectThisTrace = kymRoi.getDetectionParams(channel, PeakDetectionTypes.intensity)['detectThisTrace']
                self.phaseClipPlotItem.setLabel("bottom", detectThisTrace, units="")
                detectThisTrace = kymRoi.getDetectionParams(channel, PeakDetectionTypes.diameter)['detectThisTrace']
                self.phaseClipPlotItem.setLabel("left", detectThisTrace, units="")

    def _clearClips(self):
        # intensity
        self.clipPlot.setData([], [])
        self.meanClipPlot.setData([], [])

        # diameter
        self.diameterClipPlot.setData([], [])
        self.diameterMeanClipPlot.setData([], [])

        # phase plot
        self.phaseClipPlot.setData([], [])
        
    def keyPressEvent(self, event):
        key = event.key()

        if key in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            self._resetZoom()

    def _resetZoom(self, doEmit=True):
        # self._kymRoiImageWidget.kymographPlot.autoRange(item=self._kymRoiImageWidget.myImageItem)
        _currentTabIndex = self._tabwidget.currentIndex()
        if _currentTabIndex == 0:
            self.peakClipPlotItem.autoRange()
        elif _currentTabIndex == 1:
            self.diameterClipPlotItem.autoRange()
        else:
            logger.info(f'did not understand tab index {_currentTabIndex}')
        