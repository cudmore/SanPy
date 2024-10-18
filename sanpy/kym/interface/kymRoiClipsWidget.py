from functools import partial

import numpy as np

from PyQt5 import QtGui, QtCore, QtWidgets
import pyqtgraph as pg

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class KymRoiClipsWidget(QtWidgets.QWidget):
    """A widget to show peak clips.
    """
    def __init__(self):
        super().__init__(None)

        self._secondsPerLine = None  # shared between df/f0 and diameter

        # peaks from df/d0
        self.y_df_f0 = None  # df/f0 to clip
        self.peakBins_df_f0 = None  # list of peaks (bins)
        self.plusMinusBins_df_f0 = 50
        
        # peaks from diameter
        self.y_diameter = None  # df/f0 to clip
        self.peakBins_diameter = None  # list of peaks (bins)
        self.plusMinusBins_diameter = 50
        
        # gui
        self._plotRaw = True
        self._plotMean = True
        self._plotPercent = True

        self._buildUI()

        # logger.info('')

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

        self._tabwidget.addTab(self.peakClipPlotItem, "f/f0")
        # vBox.addWidget(self.peakClipPlotItem)

        self._buildPeakDiamPlot()
        self._tabwidget.addTab(self.diameterClipPlotItem, "Diameter")
        
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
        self.phaseClipPlot = self.peakClipPlotItem.plot(name="phaseClipPlot",
                                                pen=pg.mkPen('#AAAAAA', width=2),
                                                #   symbol='o',
                                                #   size=4,
                                                #   brush=None,  #pg.mkBrush(100, 255, 100, 220)
                                                  )
        
        # plot mean
        self.phaseMeanClipPlot = self.peakClipPlotItem.plot(name="phaseMeanClipPlot",
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

        return hBox

    def _on_checkbox_clicked(self, name, value):
        if value>0:
            value = 1
        logger.info(f'name:{name} value:{value}')
        
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
        # f/f0
        self.plotPeakClips(self.y_df_f0,
                           self.peakBins_df_f0,
                           self._secondsPerLine,
                           self.plusMinusBins_df_f0,
                           )
        # f/f0
        self.plotPeakClips(self.y_diameter,
                           self.peakBins_diameter,
                           self._secondsPerLine,
                           self.plusMinusBins_diameter,
                           doDiameter=True
                           )

    def plotPeakClips(self, yPlot, xPeakBins, secondsPerLine, plusMinusBins, doDiameter : bool = False):
        """
        Parameters
        ----------
        yPlot : np.ndarray
        xPeakBins : np.ndarray
            Needs to be adjusted by left of roi (parent does this)
        """
        if xPeakBins is None:
            logger.warning(f'no peaks to clip, diameter:{doDiameter}')
            return
        
        self._secondsPerLine = secondsPerLine  # shared between df/f0 and diameter

        if doDiameter:
            self.y_diameter = yPlot
            self.peakBins_diameter = xPeakBins
            self.plusMinusBins_diameter = plusMinusBins
            self.diameterClipPlot.setData([], [])
        else:
            self.y_df_f0 = yPlot
            self.peakBins_df_f0 = xPeakBins
            self.plusMinusBins_df_f0 = plusMinusBins
            self.clipPlot.setData([], [])

        numPeaks = len(xPeakBins)
        numPntsInClip = plusMinusBins * 2

        if numPeaks == 0:
            # logger.warning('no peaks for clips.')
            return
        
        # all clips share same x
        xOneClip = [(x-plusMinusBins)*secondsPerLine for x in range(numPntsInClip)]

        xPlotClips = np.empty((numPeaks*2, numPntsInClip))
        xPlotClips[:] = np.nan
        yPlotClips = np.empty((numPeaks*2, numPntsInClip))
        yPlotClips[:] = np.nan

        for peakIdx, xPeak in enumerate(xPeakBins):
            # logger.info(f'peakIdx:{peakIdx}')
            
            xStart = xPeak - plusMinusBins
            if xStart < 0:
                xStart = 0
            
            xStop = xPeak + plusMinusBins
            if xStop > len(yPlot)-1:
                xStop = len(yPlot)-1

            # logger.info(f'   xPeak:{xPeak} xStart:{xStart} xStop:{xStop} xStop-xStart+1:{xStop-xStart+1} left:{left} len(xPlot):{len(xPlot)} len(yPlot):{len(yPlot)}')
            
            yOneClip = yPlot[xStart:xStop]

            # normalize to max -> percent
            try:
                if self._plotPercent:
                    yOneClip = yOneClip / np.max(yOneClip) * 100

            except (ValueError) as e:
                logger.warning(f'   (1) not showing clip for peak: {peakIdx} --> {e}')
                logger.error(f'      peakIdx:{peakIdx} xStart:{xStart} yStart:{xStart}')
                continue

            xPlotClips[peakIdx*2, :] = xOneClip
            
            try:
                yPlotClips[peakIdx*2, :] = yOneClip
            except (ValueError) as e:
                logger.warning(f'   (2) not showing clip for peak: {peakIdx} --> {e}')

        #
        # update GUI
        if doDiameter:
            self.diameterClipPlot.setData(xPlotClips.flatten(), yPlotClips.flatten())
            yMean = np.nanmean(yPlotClips, axis=0)
            self.diameterMeanClipPlot.setData(xOneClip, yMean)
            self.diameterClipPlotItem.autoRange()
            
        # original, clips for peaks in f/f0
        else:
            self.clipPlot.setData(xPlotClips.flatten(), yPlotClips.flatten())
            yMean = np.nanmean(yPlotClips, axis=0)
            self.meanClipPlot.setData(xOneClip, yMean)
            self.peakClipPlotItem.autoRange()
