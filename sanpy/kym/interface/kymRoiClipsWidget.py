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

        self._plusMinusBins = 50
        self._plotRaw = True
        self._plotMean = True
        self._plotPercent = True

        self._buildUI()

        # logger.info('')

    def _buildUI(self):
        vBox = QtWidgets.QVBoxLayout()

        _topToolbar = self._buildTopToolbar()
        vBox.addLayout(_topToolbar)

        self.peakClipPlotItem = pg.PlotWidget()
        self.peakClipPlotItem.setLabel("left", "Intensity (%)", units="")
        self.peakClipPlotItem.setLabel("bottom", "Time (s)", units="")

        self.peakClipPlotItem.enableAutoRange()
        self.peakClipPlotItem.setMouseEnabled(x=True, y=False)
        self.peakClipPlotItem.hideButtons()  # hide the little 'A' button to rescale axis

        # raw plot item to update
        self.clipPlot = self.peakClipPlotItem.plot(name="peakClipPlot",
                                                pen=pg.mkPen('#AAAAAA', width=2),
                                                #   symbol='o',
                                                #   size=4,
                                                #   brush=None,  #pg.mkBrush(100, 255, 100, 220)
                                                  )
        
        # plot mean
        self.meanClipPlot = self.peakClipPlotItem.plot(name="peakClipPlot",
                                                pen=pg.mkPen('r', width=2),
                                                #   symbol='o',
                                                #   size=4,
                                                #   brush=None,  #pg.mkBrush(100, 255, 100, 220)
                                                  )

        vBox.addWidget(self.peakClipPlotItem)

        #
        self.setLayout(vBox)

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
        logger.info(f'name:{name} value:{value}')
        if value>0:
            value = 1
        
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
        self.plotPeakClips(self._yPlot,
                           self._xPeakBins,
                           self._secondsPerLine,
                           self._plusMinusBins,
                           )

    def plotPeakClips(self, yPlot, xPeakBins, secondsPerLine, plusMinBins):
        """
        Parameters
        ----------
        yPlot : np.ndarray
        xPeakBins : np.ndarray
            Needs to be adjusted by left of roi (parent does this)
        """
        self._yPlot = yPlot
        self._xPeakBins = xPeakBins
        self._secondsPerLine = secondsPerLine
        self._plusMinusBins = plusMinBins

        # clear
        self.clipPlot.setData([], [])

        numPeaks = len(xPeakBins)
        numPntsInClip = self._plusMinusBins * 2

        if numPeaks == 0:
            # logger.warning('no peaks for clips.')
            return
        
        # all clips share same x
        xOneClip = [(x-self._plusMinusBins)*secondsPerLine for x in range(numPntsInClip)]

        xPlotClips = np.empty((numPeaks*2, numPntsInClip))
        xPlotClips[:] = np.nan
        yPlotClips = np.empty((numPeaks*2, numPntsInClip))
        yPlotClips[:] = np.nan

        for peakIdx, xPeak in enumerate(xPeakBins):
            # logger.info(f'peakIdx:{peakIdx}')
            
            xStart = xPeak - self._plusMinusBins
            if xStart < 0:
                xStart = 0
            
            xStop = xPeak + self._plusMinusBins
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

            # logger.info(f'peakIdx:{peakIdx}')
            # logger.info(f'   xStart:{xStart} xStop:{xStop}')
            # logger.info(f'   xOneClip:{xOneClip} yOneClip:{yOneClip}')

            xPlotClips[peakIdx*2, :] = xOneClip
            
            try:
                yPlotClips[peakIdx*2, :] = yOneClip
            except (ValueError) as e:
                logger.warning(f'   (2) not showing clip for peak: {peakIdx} --> {e}')

        #
        self.clipPlot.setData(xPlotClips.flatten(), yPlotClips.flatten())

        yMean = np.nanmean(yPlotClips, axis=0)
        # logger.info(f'xOneClip: {len(xOneClip)} {xOneClip}')
        # logger.info(f'yMean: {len(yMean)} {yMean}')
        self.meanClipPlot.setData(xOneClip, yMean)

        # logger.warning('TEMPORARY ... set data for self.peakClipsWidget')
        # self.peakClipsWidget.setData(xPlotClips.flatten(), yPlotClips.flatten())

        # self.peakClipPlotItem.autoRange(item=self.clipPlot)
        self.peakClipPlotItem.autoRange()
