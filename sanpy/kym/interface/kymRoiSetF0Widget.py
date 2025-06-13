from typing import Optional

import numpy as np

from PyQt5 import QtGui, QtCore, QtWidgets
import pyqtgraph as pg

from sanpy.interface.util import sanpyCursors

from sanpy.kym.kymRoiDetection import KymRoiDetection
from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, PeakDetectionTypes

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class SetF0Widget(QtWidgets.QWidget):
    """Class to display sum intensity to show and manually set f0.
    """

    signalUpdateF0 = QtCore.pyqtSignal(object, object, object)  # (channel, roiLabel, new_f0_value)

    def __init__(self, kymRoiAnalysis : KymRoiAnalysis):
        super().__init__()

        self._kymRoiAnalysis = kymRoiAnalysis
        
        self.xTrace = 'Time (s)'
        self.yTrace = 'intDetrend'

        self._kymRoiDetection : KymRoiDetection = None
        """Switches to one channel in slot_selectRoi().
        """
        
        self._channelIdx : Optional[int] = None
        self._roiLabel : Optional[str] = None

        self._buildUI()

    def slot_selectRoi(self, channelIdx : int, roiLabel : Optional[str]):
        # logger.info(f'channelIdx:{channelIdx} roiLabel:{roiLabel}')

        if roiLabel is None:
            # clear the plot
            # yEmpty = [np.nan] * self._kymRoiAnalysis.numLineScans
            logger.info('clearing f0 plot')
            self.intensityPlotItem.setData(np.array([]), np.array([]))

            self._channelIdx = None
            self._roiLabel = None
            self._kymRoiDetection = None

            return
        
        self._channelIdx = channelIdx
        self._roiLabel = roiLabel
        
        # backend KymRoi
        kymRoi = self._kymRoiAnalysis.getRoi(roiLabel)
        self._kymRoiDetection = kymRoi.getDetectionParams(channelIdx, PeakDetectionTypes.intensity)

        xPlot = kymRoi.getTrace(channelIdx, self.xTrace)
        yPlot = kymRoi.getTrace(channelIdx, self.yTrace)

        self.intensityPlotItem.setData(xPlot, yPlot)
        
        # if channelIdx == 0:
        #     _color = '#DD1111'
        # else:
        #     _color = 'Green'
        _color = self._kymRoiAnalysis.getChannelColor(channelIdx)

        self.intensityPlotItem.setPen(pg.mkPen(color=_color))

        self.intensityPlotWidget.setLabel("left", 'Sum Intensity', color=_color, units="")

        # set horizontal line for f0 percentile (pg.InfiniteLine)
        f0_percentile = self._kymRoiDetection['f0 Value Percentile']
        if f0_percentile is not None:
            # f0Value = kymRoi.getTrace(channelIdx, 'f0 Value Percentile')
            self.rawIntensity_f0_line.setPos(f0_percentile)
            # logger.error(f'infinite line has no set label, want to set to f0_percentile:{f0_percentile:.2f}')
            # self.rawIntensity_f0_line.setLabel(f'f0={f0_percentile:.2f}')
            self.rawIntensity_f0_line.setVisible(True)
        else:
            self.rawIntensity_f0_line.setVisible(False)

        # set cursor c to manual f0
        f0_manual = self._kymRoiDetection['f0 Value Manual']
        self._sanpyCursors._cursorC.setPos(f0_manual)

    def myContextMenu(self, event):
        """Context menu for raw plot item.
        
        Used to set f0 from cursors.
        See also _contextMenu() for global widget context menus.
        """
        if self._kymRoiDetection is None:
            return
        
        contextMenu = QtWidgets.QMenu()
        
        contextMenu.addAction('Full Zoom')
        contextMenu.addSeparator()

        _cursorsShowing = self._sanpyCursors.cursorsAreShowing()
        
        cCursorValue = self._sanpyCursors._cCursorVal
        cCursorValue = round(cCursorValue, 2)  # round

        cursorAction = QtWidgets.QAction('Cursors')
        cursorAction.setCheckable(True)
        cursorAction.setChecked(_cursorsShowing)
        contextMenu.addAction(cursorAction)
        contextMenu.addSeparator()

        #
        f0ManualPercentile = self._kymRoiDetection['f0 Type']  # in (Manual, Percentile)
        logger.info(f'f0ManualPercentile:"{f0ManualPercentile}"')
        _do_f0_Manual = f0ManualPercentile == 'Manual'
        
        f0Action = QtWidgets.QAction(f'Set f0 to {cCursorValue}')
        f0Action.setEnabled(_cursorsShowing and _do_f0_Manual)
        contextMenu.addAction(f0Action)

        action = contextMenu.exec_(event.globalPos())
        if action is None:
            return
        
        # respond to menu selection
        _ret = ''
        actionText = action.text()
        if actionText == 'Full Zoom':
            self._resetZoom()
            _ret = 'Reset zoom'

        elif actionText == 'Cursors':
            _checked = cursorAction.isChecked()
            # self._sanpyCursors.toggleCursors(_checked)
            self._sanpyCursors.toggleCursors(_checked)

        elif action == f0Action:
            _ret = f'User set f0 to {cCursorValue}'
            logger.info(_ret)
            
            self._kymRoiDetection['f0 Value Manual'] = cCursorValue
            logger.info(f'   --->>> emit _channelIdx:{self._channelIdx} _roiLabel:{self._roiLabel} cCursorValue:{cCursorValue}')
            self.signalUpdateF0.emit(self._channelIdx, self._roiLabel, cCursorValue)

        self.mySetStatusbar(_ret)

    def _resetZoom(self):
        self.intensityPlotItem.autoRange()

    def _setXLink(self, widget):
        self.intensityPlotWidget.setXLink(widget)

    def _buildUI(self):
        vBoxPlot = QtWidgets.QVBoxLayout()
        vBoxPlot.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(vBoxPlot)

        self.intensityPlotWidget = pg.PlotWidget()
        vBoxPlot.addWidget(self.intensityPlotWidget)

        self.intensityPlotWidget.setDefaultPadding()
        self.intensityPlotWidget.enableAutoRange()
        self.intensityPlotWidget.setMouseEnabled(x=True, y=False)
        self.intensityPlotWidget.hideButtons()  # hide the little 'A' button to rescale axis

        # abb 20250501
        logger.warning('hard coding getChannelColor to 0')
        _channelColor = self._kymRoiAnalysis.getChannelColor(0)

        self.intensityPlotWidget.setLabel("left", 'Sum Intensity', color=_channelColor, units="")
        self.intensityPlotWidget.setLabel("bottom", 'Time (s)', units="")

        # get the original font and make it bigger
        _origFont = self.intensityPlotWidget.getAxis("bottom").label.font()
        from sanpy.kym.interface.kymRoiWidget import KymRoiWidget  # just for font size
        _origFont.setPointSize(KymRoiWidget._pgAxisLabelFontSize)
        self.intensityPlotWidget.getAxis("bottom").label.setFont(_origFont)
        self.intensityPlotWidget.getAxis("left").label.setFont(_origFont)

        # self.intensityPlotWidget.setXLink(self._kymRoiImageWidget.kymographPlot)

        # re-wire right-click (for entire widget)
        # self.intensityPlotWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # self.intensityPlotWidget.customContextMenuRequested.connect(self.myContextMenu)
        self.intensityPlotWidget.contextMenuEvent = self.myContextMenu  # rewire right-click to custom function

        self.intensityPlotItem = pg.PlotCurveItem(pen=pg.mkPen(_channelColor, width=2))
        self.intensityPlotItem.setData(x=self._kymRoiAnalysis.getXAxis(), y=[np.nan]*self._kymRoiAnalysis.numLineScans)
        self.intensityPlotWidget.addItem(self.intensityPlotItem)

        # horizontal line to show f0
        self.rawIntensity_f0_line = pg.InfiniteLine(angle=0,
                                                    movable=False,
                                                    pen = pg.mkPen('c', width=2),
                                                    # label=f'f0={f0Value}',
                                                    label='f0 %:{value:.2f}',  # hidden variable value is value of line
                                                    # labelText='f0={value:.2f}',
                                                    # labelOpts={'position':0.05},
                                                    # labelOpts={'position':0.85, 'color':'c', 'font-size':'10pt'},
                                                    labelOpts={'position':0.85, 'color':'c'},
                                                    )
        self.intensityPlotWidget.addItem(self.rawIntensity_f0_line)

        # a vertical line to show selected line scan
        self._kymLineScanLine = pg.InfiniteLine(pen=pg.mkPen(color='c', width=2))
        self.intensityPlotWidget.addItem(self._kymLineScanLine)

        # cursors for user to set f0 manual
        # self._sanpyCursors._cursorC is a pg iinfinite line
        self._sanpyCursors = sanpyCursors(self.intensityPlotWidget,
                                          showCursorD=False,
                                          cursorC_label='f0 Manual:',)
        self._sanpyCursors._showCursorA = False
        self._sanpyCursors._showCursorB = False
        self._sanpyCursors.toggleCursors(True)  # initially visible
        self._sanpyCursors.signalCursorDragged.connect(self.mySetStatusbar)

    def slot_updateLineProfile(self, lineScanIdx : int):
        """Update vertical line showing current selected line scan.
        """
        # logger.info(f'lineScanIdx:{lineScanIdx}')
        lineScanSec = lineScanIdx * self._kymRoiAnalysis.secondsPerLine
        self._kymLineScanLine.setPos(lineScanSec)

    def mySetStatusbar(self, text : str):
        # logger.info('')
        pass