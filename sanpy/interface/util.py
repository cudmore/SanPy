from functools import partial

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class sanpyCursors(QtCore.QObject):
    signalCursorDragged = QtCore.pyqtSignal(str)  # dx
    signalSetDetectionParam = QtCore.pyqtSignal(str, float)

    def __init__(self, plotWidget : pg.PlotWidget, showInView=True):
        """Add cursors to a PlotWidget. Normally vmPlot.
        """
        super().__init__(None)
        
        self._showCursors = False
        self._delx : float = float('nan')
        self._cCursorVal : float = float('nan')

        self._showCursorsY = False
        self._delx : float = float('nan')

        labelOpts = {'position':0.95}
        self._cursorA = pg.InfiniteLine(pos=0, angle=90, label='A', labelOpts=labelOpts, movable=True)
        self._cursorA.sigDragged.connect(partial(self._cursorDragged, 'cursorA'))
        self._cursorA.setVisible(self._showCursors)
        self._cursorB = pg.InfiniteLine(pos=10, angle=90, label='B', labelOpts=labelOpts, movable=True)
        self._cursorB.sigDragged.connect(partial(self._cursorDragged, 'cursorB'))
        self._cursorB.setVisible(self._showCursors)

        yLabelOpts = {'position':0.05}
        self._cursorC = pg.InfiniteLine(pos=0, angle=0, label='C', labelOpts=yLabelOpts, movable=True)
        self._cursorC.sigDragged.connect(partial(self._cursorDragged, 'cursorA'))
        self._cursorC.setVisible(self._showCursors)
        # self._cursorD = pg.InfiniteLine(pos=10, angle=0, label='D', labelOpts=yLabelOpts, movable=True)
        # self._cursorD.sigDragged.connect(partial(self._cursorDragged, 'cursorB'))
        # self._cursorD.setVisible(self._showCursors)

        self._plotWidget = plotWidget
        
        self._plotWidget.addItem(self._cursorA)
        self._plotWidget.addItem(self._cursorB)
        self._plotWidget.addItem(self._cursorC)
        # self._plotWidget.addItem(self._cursorD)

        # logger.info(self._getName())
        #self._showInView()
        self.toggleCursors(showInView)
        self._showInView()
        
    def _getName(self):
        return self._plotWidget.getViewBox().name
    
    def toggleCursors(self, visible):
        self._showCursors = visible
        self._cursorA.setVisible(visible)
        self._cursorB.setVisible(visible)
        
        self._cursorC.setVisible(visible)
        # self._cursorD.setVisible(visible)

        if visible:
            # set position to start/stop of current view
            self._showInView()

    def getMenuActions(self, contextMenu):
        """Add cursor actions to a ocntext menu.
        """

        contextMenu.addSeparator()
        
        showCursorAction = contextMenu.addAction(f"Cursors")
        showCursorAction.setCheckable(True)
        showCursorAction.setChecked(self._showCursors)
        
        aAction = contextMenu.addAction(f'Show In View')
        aAction.setEnabled(self._showCursors)

        if self._getName() == 'vmPlot':
            _delx_ms = int(self._delx*1000)
            
            # mvThreshold
            aAction = contextMenu.addAction(f'Set Threshold (mV) {self._cCursorVal}')
            aAction.setEnabled(self._showCursors)

            # refractory_ms, APs with interval (with respect to previous AP) less than this will be removed
            aAction = contextMenu.addAction(f'Set Refactory Period (ms) {_delx_ms}')
            aAction.setEnabled(self._showCursors)
    
            # halfWidthWindow_ms, Window (ms) after TOP to look for AP Durations
            aAction = contextMenu.addAction(f'Set Half Width Window (ms) {_delx_ms}')
            aAction.setEnabled(self._showCursors)
        elif self._getName() == 'derivPlot':
            # dvdtThreshold
            aAction = contextMenu.addAction(f'Set dVdt Threshold {self._cCursorVal}')
            aAction.setEnabled(self._showCursors)
        else:
            logger.error(f'did not understand plot name "{self._getName()}"')

    def handleMenu(self, actionText : str, isChecked):
        _handled = True
        _name = self._getName()
        if actionText == 'Cursors':
            logger.info(f'{actionText} {isChecked}')
            self.toggleCursors(isChecked)
        elif actionText == 'Show In View':
            self._showInView()

        elif _name=='vmPlot' and actionText.startswith('Set Threshold (mV)'):
            self.signalSetDetectionParam.emit('mvThreshold', self._cCursorVal)
        elif _name=='vmPlot' and actionText.startswith('Set Refactory Period (ms)'):
            self.signalSetDetectionParam.emit('refractory_ms', self._delx*1000)
        elif _name=='vmPlot' and actionText.startswith('Set Half Width Window (ms)'):
            self.signalSetDetectionParam.emit('halfWidthWindow_ms', self._delx*1000)

        elif _name=='derivPlot' and actionText.startswith('Set dVdt Threshold'):
            self.signalSetDetectionParam.emit('dvdtThreshold', self._cCursorVal)
        else:
            _handled = False
        return _handled

    def _showInView(self):
        """Make cursors visible within current zoom.
        """
        rect = self._plotWidget.viewRect()  # get xaxis

        percentOfView = rect.width() * 0.05
        left = rect.left() + percentOfView
        right = rect.right() - percentOfView

        yPercentOfView = rect.height() * 0.1
        bottom = rect.top() + yPercentOfView  # y is flipped
        top = rect.bottom() - yPercentOfView

        logger.info(f'left:{left} right:{right} bottom:{bottom} top:{top}')


        self._cursorA.setValue(left)
        self._cursorB.setValue(right)

        self._cursorC.setValue(bottom)
        # self._cursorD.setValue(top)

        self._cursorDragged('cursorA', self._cursorA)

    def _cursorDragged(self, name, infLine):
        # logger.info(f'{name} {infLine.pos()}')
        xCursorA = self._cursorA.pos().x()
        xCursorB = self._cursorB.pos().x()
        delx = xCursorB - xCursorA
        delx = round(delx, 4)
        
        # logger.info(f'delx:{delx}')

        self._delx = delx

        xCursorA = round(xCursorA,4)
        xCursorB = round(xCursorB,4)

        yCursorC = self._cursorC.pos().y()
        # yCursorD = self._cursorD.pos().y()
        # dely = yCursorD - yCursorC
        # dely = round(dely, 4)

        self._cCursorVal = round(yCursorC,3)

        yCursorC = round(yCursorC,4)
        # yCursorD = round(yCursorD,4)

        # self._cursorB.label.setFormat(f'B\ndelx={delx}')
        delStr = f'A:{xCursorA} B:{xCursorB} Delta:{delx}'
        delStr += f' | C:{yCursorC}'
        # delStr += f' | C:{yCursorC} D:{yCursorD} Delta:{dely}'
        
        self.signalCursorDragged.emit(delStr)
        #self.updateStatusBar(delStr)
        