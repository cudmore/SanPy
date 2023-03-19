import math, enum

# Error if we use 'from functools import partial'
# Error shows up in sanpy.bPlugin when it tries to grab <plugin>.myHumanName ???
import functools

from typing import Union, Dict, List, Tuple, Optional, Optional

from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
import matplotlib.pyplot as plt

# Allow this code to run with just backend
from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

import qdarkstyle

import sanpy
import sanpy.interface

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class ResponseType(enum.Enum):
    """Enum representing the types of events a Plugin will respond to.
    """
    switchFile = 'Switch File'
    setSweep = 'Set Sweep'
    analysisChange = 'Analysis Change'
    selectSpike = 'Select Spike'
    setAxis = 'Set Axis'

class SpikeSelectEvent():
    """Class that encapsulates a spike(s) selection event.
    """
    def __init__(self, spikeList : List[int] = [],
                 ba : sanpy.bAnalysis = None,
                 isAlt : bool = False):
        self._spikeList = spikeList
        self._ba = ba
        self._isAlt = isAlt

    def getSpikeList(self):
        return self._spikeList
    
    def getAnalysis(self):
        return self._ba
    
    def getDoZoom(self):
        return self._isAlt
    
class sanpyPlugin(QtWidgets.QWidget):
    """Base class for all SanPy plugins.
    
    Provides general purpose API to build plugings including:

    - Open PyQt and Matplotlib plots
    - Set up signal/slots to communicate with the main SanPy app:

        - file is changed
        - detection is run
        - spike is selected
        - axis is changed

    Users derive from this class to create new plugins.

    Examples
    --------
    Run a plugin with the following code

    ```python
    import sys
    from PyQt5 import QtCore, QtWidgets, QtGui
    import sanpy
    import sanpy.interface

    # load sample data
    path = '../../../data/19114001.abf'
    ba = sanpy.bAnalysis(path)

    # get presets detection parameters for 'SA Node'
    _dDict = sanpy.bDetection().getDetectionDict('SA Node')

    # spike detect
    ba.spikeDetect(_dDict)

    # create a PyQt application
    app = QtWidgets.QApplication([])

    # open the interface for the 'plotScatter' plugin.
    sa = sanpy.interface.plugins.plotScatter(ba=ba, startStop=None)

    sys.exit(app.exec_())
    ```

    Attributes
    ----------
    signalCloseWindow : QtCore.pyqtSignal
        Signal emitted when the plugin window is closed.
    signalSelectSpikeList : QtCore.pyqtSignal
        Signal emitted when spikes are selected in the plugin.
    ba
    """

    signalCloseWindow = QtCore.pyqtSignal(object)
    """Emit signal on window close."""

    #signalSelectSpike = QtCore.pyqtSignal(object)
    """Emit signal on spike selection."""

    signalSelectSpikeList = QtCore.pyqtSignal(object)
    """Emit signal on spike selection."""

    signalDetect = QtCore.pyqtSignal(object)
    """Emit signal on spike selection."""

    myHumanName = 'UNDEFINED-PLUGIN-NAME'
    """Each derived class needs to define this."""

    # mar 11, if True then show in menus
    showInMenu = True

    responseTypes = ResponseType
    """Defines how a plugin will response to interface changes. Includes (switchFile, analysisChange, selectSpike, setAxis)."""

    def __init__(self,
                 ba : Optional[sanpy.bAnalysis] = None,
                 bPlugin : Optional["sanpy.interface.bPlugin"] = None,
                 startStop : Optional[List[float]] = None,
                 options=None,
                 parent=None):
        """
        Parameters
        ----------
        ba : sanpy.bAnalysis
            Object representing one file.
        bPlugin : "sanpy.interface.bPlugin"
            Used in PyQt to get SanPy App and to setup signal/slot.
        startStop : list(float)
            Start and stop (s) of x-axis.
        options : dict
            Depreciated.
            Dictionary of optional plugins.
                        Used by 'plot tool' to plot a pool using app analysisDir dfMaster.
        """
        super().__init__(parent)
        
        # derived classes will set this in init (see kymographPlugin)
        self._initError : bool = False

        # underlying bAnalaysis
        self._ba : sanpy.bAnalysis = ba

        # the sweep number of the bAnalaysis
        self._sweepNumber : Union[int,str] = 0
        self._epochNumber : Union[int,str] = 'All'

        self._bPlugins : "sanpy.interface.bPlugin" = bPlugin
        # pointer to object, send signal back on close

        # to show as a widget
        self._showSelf : bool = True

        # the start and stop secinds to display
        self._startSec : Optional[float] = None
        self._stopSec : Optional[float] = None
        if startStop is not None:
            self._startSec = startStop[0]
            self._stopSec = startStop[1]

        # keep track of analysis parameters
        #self.fileRowDict = None  # for detectionParams plugin

        # TODO: keep track of spike selection
        #self.selectedSpike = None
        self._selectedSpikeList : List[int] = []

        #
        # build a dict of boolean from ResponseType enum class
        # Things to respond to like switch file, set sweep, etc
        self._responseOptions : dict = {}
        for option in (self.responseTypes):
            #print(type(option))
            self._responseOptions[option.name] = True

        doDark = True
        if doDark and qdarkstyle is not None:
            self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
        else:
            self.setStyleSheet("")

        # created in self.mplWindow()
        self.fig = None
        self.ax = None
        self.mplToolbar = None

        self.keyIsDown = None

        self.winWidth_inches = 4  # used by mpl
        self.winHeight_inches = 4

        # connect self to main app with signals/slots
        self._installSignalSlot()

        self._mySetWindowTitle()

        # all plugin widgets always have a single QtWidgetQVBoxLayout
        # both widget and layouts can be added to this
        self._vBoxLayout = self.makeVLayout()
        
        # the top toolbar is always present
        self._blockComboBox : bool = False
        self._topToolbarWidget = self._buildTopToolbarWidget()
        self.toggleTopToobar(False)  # initially hidden
        self._updateTopToolbar()

        self._vBoxLayout.addWidget(self._topToolbarWidget)

    def getStat(self, stat : str) -> list:
        """Convenianece function to get a stat from underling sanpy.bAnalysis.
        
        Parameters
        ----------
        stat : str
            Stat to get, corresponds to a column in sanpy.bAnalysis
        """
        return self.ba.getStat(stat,
                               sweepNumber=self.sweepNumber,
                               epochNumber=self.epochNumber)
                              
    @property
    def responseOptions(self):
        return self._responseOptions
    
    def toggleTopToobar(self, visible : bool = None):
        """If None then toggle, otherwise set to visible.
        """
        if visible is None:
            visible = not self._topToolbarWidget.isVisible()
        self._topToolbarWidget.setVisible(visible)

    def getVBoxLayout(self):
        """Get the main QVBoxLayout, this can be added to.
        """
        return self._vBoxLayout
    
    def getSelectedSpikes(self) -> List[int]:
        """Get the currently selected spikes.
        """
        return self._selectedSpikeList
    
    def setSelectedSpikes(self, spikes : List[int]):
        """Set the currently selected spikes.
        """
        self._selectedSpikeList = spikes

    def getHumanName(self):
        return self.myHumanName
    
    def getInitError(self):
        return self._initError

    def getWidget(self):
        """Over-ride if plugin makes its own PyQt widget.
        """
        return self
    
    def getShowSelf(self):
        return self._showSelf

    def setShowSelf(self, show : bool):
        self._showSelf = show

    @property
    def sweepNumber(self):
        """Get the current sweep number, can be 'All'.
        """
        return self._sweepNumber

    @property
    def epochNumber(self):
        """Get the epoch number, can be all.
        """
        return self._epochNumber

    def getSweep(self, type : str):
        """Get the raw data from a sweep.
        
        Parameters
        ----------
        type : str
            The sweep type from ('X', 'Y', 'C', 'filteredDeriv', 'filteredVm')
        """
        theRet = None
        type = type.upper()
        if self.ba is None:
            return theRet
        if type == 'X':
            theRet = self.ba.fileLoader.sweepX
        elif type == 'Y':
            theRet = self.ba.fileLoader.sweepY
        elif type == 'C':
            theRet = self.ba.fileLoader.sweepC
        elif type == 'filteredDeriv':
            theRet = self.ba.fileLoader.filteredDeriv
        elif type == 'filteredVm':
            theRet = self.ba.fileLoader.sweepY_filtered
        else:
            logger.error(f'Did not understand type: "{type}"')
        #
        return theRet

    '''
    def _setLayout(self, layout):
        #self.mainWidget.setLayout(layout)
        super().setLayout(layout)

        #self.scrollArea.setWidget(self.mainWidget)
        self.scrollArea.setWidget(self)

        #self.mainWidget.show()
        #self.scrollArea.show()
    '''

    def insertIntoScrollArea(self):
        """When inserting this widget into an interface, may want to wrap it in a ScrollArea

        This is used in main SanPy interface to insert this widget into a tab

        Example in inherited class:
            ```
            scrollArea = QtWidgets.QScrollArea()
            scrollArea.setWidget(self)
            return scrollArea
            ```
        """
        return None

    def get_bAnalysis(self):
        """Get current bAnalysis either from SanPy app or self.
        """
        theRet = None
        if self.getSanPyApp() is not None:
            theRet = self.getSanPyApp().get_bAnalysis()
        else:
            theRet = self._ba
        return theRet

    @property
    def ba(self):
        """todo: Depreciate and use self.get_bAnalysis().

        Returns
        -------
        sanpy.bAnalysis
            The underlying bAnalysis object
        """
        return self._ba

    def get_bPlugins(self):
        """???"""
        return self._bPlugins

    def getSanPyApp(self):
        """Return underlying SanPy app. Only exists if running in SanPy Qt Gui
        """
        theRet = None
        if self._bPlugins is not None:
            theRet = self._bPlugins.getSanPyApp()
        return theRet

    def _installSignalSlot(self):
        """Set up communication signals/slots.
        
        Be sure to call _disconnectSignalSlot() on plugin destruction.
        """
        app = self.getSanPyApp()
        if app is not None:
            # receive spike selection
            # app.signalSelectSpike.connect(self.slot_selectSpike)
            app.signalSelectSpikeList.connect(self.slot_selectSpikeList)
            # receive update analysis (both file change and detect)
            app.signalSwitchFile.connect(self.slot_switchFile)
            app.signalUpdateAnalysis.connect(self.slot_updateAnalysis)
            # recieve set sweep
            app.signalSelectSweep.connect(self.slot_setSweep)
            # recieve set x axis
            app.signalSetXAxis.connect(self.slot_set_x_axis)

            # emit when we spike detect (used in detectionParams plugin)
            self.signalDetect.connect(app.slot_detect)

        bPlugins = self.get_bPlugins()
        if bPlugins is not None:
            # emit spike selection
            # self.signalSelectSpike.connect(bPlugins.slot_selectSpike)
            self.signalSelectSpikeList.connect(bPlugins.slot_selectSpikeList)
            # emit on close window
            self.signalCloseWindow.connect(bPlugins.slot_closeWindow)

        # connect to self
        # self.signalSelectSpike.connect(self.slot_selectSpike)
        self.signalSelectSpikeList.connect(self.slot_selectSpikeList)

    def _disconnectSignalSlot(self):
        """Disconnect signal/slot on destruction.
        """
        app = self.getSanPyApp()
        if app is not None:
            # receive spike selection
            # app.signalSelectSpike.disconnect(self.slot_selectSpike)
            # receive update analysis (both file change and detect)
            app.signalSwitchFile.disconnect(self.slot_switchFile)
            app.signalUpdateAnalysis.disconnect(self.slot_updateAnalysis)
            # recieve set sweep
            app.signalSelectSweep.disconnect(self.slot_setSweep)
            # recieve set x axis
            app.signalSetXAxis.disconnect(self.slot_set_x_axis)

    def toggleResponseOptions(self, thisOption, newValue=None):
        """Set underlying responseOptions based on name of thisOption.

        Parameters
        ----------
        thisOption : ResponseType
        newValue : Optional[bool]
            If boolean then set, if None then toggle.
        """
        logger.info(f'{thisOption} {newValue}')
        if newValue is None:
            newValue = not self.responseOptions[thisOption.name]
        self.responseOptions[thisOption.name] = newValue

    def getResponseOption(self, thisOption : ResponseType):
        """Get the state of a plot option from responseOptions.

        Parameters
        ----------
        thisOption : ResponseType
        """
        return self.responseOptions[thisOption.name]

    def plot(self):
        """Derived class adds code to plot."""
        pass

    def replot(self):
        """Derived class adds code to replot."""
        pass

    def old_selectSpike(self, sDict=None):
        """Derived class adds code to select spike from sDict."""
        pass

    def selectSpikeList(self):
        """Derived class adds code to select spike from sDict.
        
        Get selected spike list with getSelectedSpikes()
        """
        pass

    def getStartStop(self):
        """Get current start stop of interface.

        Returns:
            tuple: (start, stop) in seconds. Can be None
        """
        return self._startSec, self._stopSec

    def keyReleaseEvent(self, event):
        self.keyIsDown = None

    def keyPressEvent(self, event):
        """Handle key press events.

        On 'ctrl+c' will copy-to-clipboard.

        On 'esc' emits signalSelectSpikeList.

        Parameters
        ----------
        event : Union[QtGui.QKeyEvent, matplotlib.backend_bases.KeyEvent]
            Either a PyQt or matplotlib key press event.
        """
        isQt = isinstance(event, QtGui.QKeyEvent)
        isMpl = isinstance(event, mpl.backend_bases.KeyEvent)

        key = None
        text = None
        doCopy = False
        if isQt:
            key = event.key()
            text = event.text()
            doCopy = event.matches(QtGui.QKeySequence.Copy)
        elif isMpl:
            # q will quit !!!!
            text = event.key
            doCopy = text == 'ctrl+c'
            logger.info(f'mpl key: "{text}"')
        else:
            logger.warning(f'Unknown event type: {type(event)}')
            return

        self.keyIsDown = text

        if doCopy:
            self.copyToClipboard()
        elif key==QtCore.Qt.Key_Escape or text=='esc' or text=='escape':
            # single spike
            # sDict = {
            #     'spikeNumber': None,
            #     'doZoom': False,
            #     'ba': self.ba,

            # }
            # self.signalSelectSpike.emit(sDict)
            # spike list
            sDict = {
                'spikeList': [],
                'doZoom': False,
                'ba': self.ba,
            }
            self.signalSelectSpikeList.emit(sDict)
        elif key==QtCore.Qt.Key_T or text=='t':
            self.toggleTopToobar()
        elif text == '':
            pass

        # critical difference between mpl and qt
        if isMpl:
            return text
        else:
            #return event
            return

    def copyToClipboard(self, df = None):
        """Derived classes add code to copy plugin to clipboard.
        """
        if self.ba is None:
            return
        
        fileName = self.ba.fileLoader.filename
        fileName += '.csv'
        savePath = fileName
        options = QtWidgets.QFileDialog.Options()
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,"Save .csv file",
                            savePath,"CSV Files (*.csv)", options=options)
        if not fileName:
            return

        logger.info(f'Saving: "{fileName}"')
        df.to_csv(fileName, index=False)

    def saveResultsFigure(self, pgPlot = None):
        """In derived, add code to save main figure to file.
        
        In derived, pass in a pg plot from a view and we will save it.
        """
        if pgPlot is None:
            return
        
        exporter = pg.exporters.ImageExporter(pgPlot)
        #print(f'exporter: {type(exporter)}')
        #print('getSupportedImageFormats:', exporter.getSupportedImageFormats())
        # set export parameters if needed
        
        # (width, height, antialias, background, invertvalue)
        exporter.parameters()['width'] = 1000   # (note this also affects height parameter)
        
        # ask user for file
        fileName = self.ba.fileLoader.filename
        fileName += '.png'
        savePath = fileName
        options = QtWidgets.QFileDialog.Options()
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,"Save .png file",
                            savePath,"CSV Files (*.png)", options=options)
        if not fileName:
            return
        
        # save to file
        logger.info(f'Saving to: {fileName}')
        exporter.export(fileName)

    def bringToFront(self):
        """Bring the widget to the front.
        """
        if not self._showSelf:
            return
        
        # Qt
        self.getWidget().show()
        self.getWidget().activateWindow()

        # Matplotlib
        if self.fig is not None:
            FigureManagerQT = self.fig.canvas.manager
            FigureManagerQT.window.activateWindow()
            FigureManagerQT.window.raise_()

    def makeVLayout(self):
        """Make a PyQt QVBoxLayout.
        """
        vBoxLayout = QtWidgets.QVBoxLayout()
        self.setLayout(vBoxLayout)
        return vBoxLayout
    
    def mplWindow2(self, numRow=1, numCol=1):
        """Make a matplotlib figure, canvas, and axis.
        """
        plt.style.use('dark_background')
        # this is dangerous, collides with self.mplWindow()
        self.fig = mpl.figure.Figure()

        # not working
        #self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)

        self.static_canvas = backend_qt5agg.FigureCanvas(self.fig)
        self.static_canvas.setFocusPolicy( QtCore.Qt.ClickFocus ) # this is really triccky and annoying
        self.static_canvas.setFocus()
        self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)

        self.axs = [None] * numRow  # empty list
        if numRow==1 and numCol==1:
            self._static_ax = self.static_canvas.figure.subplots()
            self.axs = self._static_ax
        else:

            for idx in range(numRow):
                plotNum = idx + 1
                #print('mplWindow2()', idx)
                self.axs[idx] = self.static_canvas.figure.add_subplot(numRow,1,plotNum)

        self._mySetWindowTitle()

        # does not work
        #self.static_canvas.mpl_connect('key_press_event', self.keyPressEvent)

        # pick_event assumes 'picker=5' in any .plot()
        self.cid = self.static_canvas.mpl_connect('pick_event', self.spike_pick_event)

        # toolbar need to be added to layout
        #from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
        self.mplToolbar = mpl.backends.backend_qt5agg.NavigationToolbar2QT(self.static_canvas, self.static_canvas)

        #layout = QtWidgets.QVBoxLayout()
        layout = self.getVBoxLayout()
        layout.addWidget(self.static_canvas)
        layout.addWidget(self.mplToolbar)
        #self.setLayout(layout)

    def _mySetWindowTitle(self):
        """Set the window title based on ba.
        """
        if self.ba is not None:
            fileName = self.ba.fileLoader.filename
        else:
            fileName = ''
        _windowTitle = self.myHumanName + ':' + fileName

        # mpl
        if self.fig is not None:
            if self.fig.canvas.manager is not None:
                self.fig.canvas.manager.set_window_title(_windowTitle)

        # pyqt
        #self.mainWidget._mySetWindowTitle(self.windowTitle)
        self.getWidget().setWindowTitle(_windowTitle)

    def spike_pick_event(self, event):
        """Respond to user clicks in mpl plot
        
        Assumes plot(..., picker=5)
        
        Parameters
        ----------
        event : matplotlib.backend_bases.PickEvent
            PickEvent with plot indices in ind[]
        """
        if len(event.ind) < 1:
            return

        #logger.info(f'{event.ind}')

        spikeNumber = event.ind[0]

        doZoom = False
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            doZoom = True

        logger.info(f'got {len(event.ind)} candidates, first is spike:{spikeNumber} doZoom:{doZoom}')

        # propagate a signal to parent
        # TODO: use class SpikeSelectEvent()
        sDict = {
            'spikeList': [spikeNumber],
            'doZoom': doZoom,
            'ba': self.ba,
        }
        self.signalSelectSpikeList.emit(sDict)

    def closeEvent(self, event):
        """Signal close event back to parent bPlugin object.

        Parameters
        ----------
        event Union[matplotlib.backend_bases.CloseEvent, PyQt5.QtGui.QCloseEvent]
            The close event from either PyQt or matplotlib
        """
        self.signalCloseWindow.emit(self)

    def slot_switchFile(self,
                        ba : sanpy.bAnalysis,
                        rowDict : Optional[dict] = None,
                        replot : bool = True):
        """Respond to switch file.
        
        Parameters
        ----------
        rowDict : dict
            Optional, assumes rowDict has keys ['Start(s)', 'Stop(s)']
        ba : sanpy.bAnalysis
            The new bAnalysis file to switch to
        replot : bool
            If true then call replot()
        """
        if not self.getResponseOption(self.responseTypes.switchFile):
            return

        if ba is None:
            return
        
        # don't respond if we are already using ba
        if self._ba == ba:
            return
        
        '''
        app = self.getSanPyApp()
        if app is not None:
            self._ba = app.get_bAnalysis()
        '''
        self._ba = ba
        #self.fileRowDict = rowDict  # for detectionParams plugin

        # rest sweep
        self._sweepNumber = 0

        # reset start/stop
        startSec = None
        stopSec = None
        if rowDict is not None:
            startSec = rowDict['Start(s)']
            stopSec = rowDict['Stop(s)']
            if math.isnan(startSec):
                startSec = None
            if math.isnan(stopSec):
                stopSec = None
        self._startSec = startSec
        self._stopSec = stopSec

        # reset spike and spike list selection
        self._selectedSpikeList = []
        self.selectedSpike = None
        
        # inform derived classes of change
        #self.old_selectSpike()
        self.selectSpikeList()

        # set pyqt window title
        self._mySetWindowTitle()

        self._updateTopToolbar()

        if replot:
            self.replot()

    def slot_updateAnalysis(self, ba):
        """Respond to new spike detection.

        Parameters
        ----------
        ba : sanpy.bAnalysis
        """
        logger.info('')
        if not self.getResponseOption(self.responseTypes.analysisChange):
            return
        
        if ba is None:
            return
        
        # don't update analysis if we are showing different ba
        if self._ba != ba:
            return

        self.replot()

    def slot_setSweep(self, ba : sanpy.bAnalysis, sweepNumber : int):
        """Respond to user selecting a sweep.
        """
        logger.info('')
        
        if not self.getResponseOption(self.responseTypes.setSweep):
            return

        if ba is None:
            return
        
        # don't respond if we are showing different ba
        if self._ba != ba:
            return
            
        self._sweepNumber = sweepNumber

        # reset selection
        self._selectedSpikeList = []
        self.selectedSpike = None

        self.replot()

    def slot_selectSpikeList(self, eDict : dict):
        """Respond to spike selection.

        TODO: convert dict to class spikeSelection
        """

        logger.info(f'mar 11 eDict:{eDict}')
        
        # don't respond if we are showing a different ba (bAnalysis)
        ba = eDict['ba']
        if self.ba != ba:
            return

        spikeList = eDict['spikeList']
        self._selectedSpikeList = spikeList  # [] on no selection

        self.selectSpikeList()

    def old_slot_selectSpike(self, eDict):
        """Respond to spike selection.
        """

        # don't respond if user/code has turned this off
        if not self.getResponseOption(self.responseTypes.selectSpike):
            return

        # don't respond if we are showing a different ba (bAnalysis)
        ba = eDict['ba']
        if self.ba != ba:
            return

        self.selectedSpike = eDict['spikeNumber']

        self.old_selectSpike(eDict)

    def slot_set_x_axis(self, startStopList : List[float]):
        """Respond to changes in x-axis.

        Parameters
        ----------
        startStopList : list(float)
            Two element list with [start, stop] in seconds
        """
        if not self.getResponseOption(self.responseTypes.setAxis):
            return
        
        # don't set axis if we are showing different ba
        app = self.getSanPyApp()
        if app is not None:
            ba = app.get_bAnalysis()
            if self._ba != ba:
                return

        #logger.info(startStopList)
        if startStopList is None:
            self._startSec = None
            self._stopSec = None
        else:
            self._startSec = startStopList[0]
            self._stopSec = startStopList[1]
        #
        # we do not always want to replot on set axis
        self.setAxis()
        #self.replot()

    def setAxis(self):
        """Respond to set axis.

        Some plugins want to replot() when x-axis changes.
        """
        pass

    def turnOffAllSignalSlot(self):
        """Make plugin not respond to any changes in interface.
        """
        # turn off all signal/slot
        switchFile = self.responseTypes.switchFile
        self.toggleResponseOptions(switchFile, newValue=False)

        setSweep = self.responseTypes.setSweep
        self.toggleResponseOptions(setSweep, newValue=False)

        analysisChange = self.responseTypes.analysisChange
        self.toggleResponseOptions(analysisChange, newValue=False)

        selectSpike = self.responseTypes.selectSpike
        self.toggleResponseOptions(selectSpike, newValue=False)

        setAxis = self.responseTypes.setAxis
        self.toggleResponseOptions(setAxis, newValue=False)

    def contextMenuEvent(self, event):
        """Handle right-click

        Parameters
        ----------
        event : QtGui.QContextMenuEvent
            Used to position popup
        """
        if self.mplToolbar is not None:
            state = self.mplToolbar.mode
            if state in ['zoom rect', 'pan/zoom']:
                # don't process right-click when toolbar is active
                return

        logger.info('')

        contextMenu = QtWidgets.QMenu(self)
        
        # prepend any menu from derived classes
        self.prependMenus(contextMenu)

        switchFile = contextMenu.addAction("Switch File")
        switchFile.setCheckable(True)
        switchFile.setChecked(self.responseOptions['switchFile'])

        setSweep = contextMenu.addAction("Set Sweep")
        setSweep.setCheckable(True)
        setSweep.setChecked(self.responseOptions['setSweep'])

        analysisChange = contextMenu.addAction("Analysis Change")
        analysisChange.setCheckable(True)
        analysisChange.setChecked(self.responseOptions['analysisChange'])

        selectSpike = contextMenu.addAction("Select Spike")
        selectSpike.setCheckable(True)
        selectSpike.setChecked(self.responseOptions['selectSpike'])

        axisChange = contextMenu.addAction('Axis Change')
        axisChange.setCheckable(True)
        axisChange.setChecked(self.responseOptions['setAxis'])

        contextMenu.addSeparator()
        copyTable = contextMenu.addAction('Copy Results')
        saveFigure = contextMenu.addAction('Save Figure')

        contextMenu.addSeparator()
        showTopToolbar = contextMenu.addAction('Toggle Top Toolbar')

        #contextMenu.addSeparator()
        #saveTable = contextMenu.addAction("Save Table")

        #
        # open the menu
        action = contextMenu.exec_(self.mapToGlobal(event.pos()))

        if action is None:
            # n menu selected
            return

        #
        # handle actions
        handled = self.handleContextMenu(action)

        if handled:
            return

        if action == switchFile:
            self.toggleResponseOptions(self.responseTypes.switchFile)
        elif action == analysisChange:
            self.toggleResponseOptions(self.responseTypes.analysisChange)
        elif action == selectSpike:
            self.toggleResponseOptions(self.responseTypes.selectSpike)
        elif action == axisChange:
            self.toggleResponseOptions(self.responseTypes.setAxis)
        elif action == copyTable:
            self.copyToClipboard()
        elif action == saveFigure:
            self.saveResultsFigure()
        elif action == showTopToolbar:
            self.toggleTopToobar()
        #elif action == saveTable:
        #    #self.saveToFile()
        #    logger.info('NOT IMPLEMENTED')

        elif action is not None:
                logger.warning(f'Menu action not taken "{action.text}"')

    def prependMenus(self, contextMenu):
        pass

    def handleContextMenu(self, action):
        pass

    def _updateTopToolbar(self):
        """Update the top toolbar on state change like switch file.
        """
        if self.ba is None:
            return
        
        _sweepList = self.ba.fileLoader.sweepList
        self._blockComboBox = True
        self._sweepComboBox.clear()
        self._sweepComboBox.addItem('All')
        for _sweep in _sweepList:
            self._sweepComboBox.addItem(str(_sweep))
        _enabled = len(_sweepList) > 1
        self._sweepComboBox.setEnabled(_enabled)
        if self.sweepNumber == 'All':
            self._sweepComboBox.setCurrentIndex(0)
        else:
            self._sweepComboBox.setCurrentIndex(self.sweepNumber+1)
        self._blockComboBox = False

        # minimum of 2 (never 1 or 0)
        # because of annoying pClamp default short epoch 0
        _numEpochs = self.ba.fileLoader.numEpochs
        self._blockComboBox = True
        self._epochComboBox.clear()
        self._epochComboBox.addItem('All')
        for _epoch in range(_numEpochs):
            self._epochComboBox.addItem(str(_epoch))
        _enabled = _numEpochs > 2
        self._epochComboBox.setEnabled(_enabled)
        self._epochComboBox.setCurrentIndex(0)
        self._blockComboBox = False


        filename = self.ba.getFileName()
        self._fileLabel.setText(filename)

    def _on_sweep_combo_box(self, idx : int):
        """Respond to user selecting sweep combobox.

        Notes
        -----
        idx 0 is 'All', idx 1 is sweep 0
        """
        if self._blockComboBox:
            return
        
        idx = idx - 1  # first item is always 'All'
        if idx == -1:
            idx = 'All'
        logger.info(idx)
        self._sweepNumber = idx

        if self.ba is None:
            return
        
        self.replot()

    def _on_epoch_combo_box(self, idx : int):
        if self._blockComboBox:
            return
        
        idx = idx - 1  # first item is always 'All'
        if idx == -1:
            idx = 'All'
        logger.info(idx)
        self._epochNumber = idx

        if self.ba is None:
            return
        
        self.replot()

    def _buildTopToolbarWidget(self) -> QtWidgets.QWidget:
        """Toolbar to show file, toggle responses on/off, etc
        """
            
        #
        # first row of controls
        hLayout0 = QtWidgets.QHBoxLayout()

        # sweep popup
        aLabel = QtWidgets.QLabel('Sweeps')
        hLayout0.addWidget(aLabel, alignment=QtCore.Qt.AlignLeft)
        self._sweepComboBox = QtWidgets.QComboBox()
        self._sweepComboBox.currentIndexChanged.connect(self._on_sweep_combo_box)
        #hLayout0.addWidget(self._sweepComboBox, alignment=QtCore.Qt.AlignLeft)
        hLayout0.addWidget(self._sweepComboBox)

        hLayout0.addStretch()

        # epoch popup
        aLabel = QtWidgets.QLabel('Epochs')
        hLayout0.addWidget(aLabel, alignment=QtCore.Qt.AlignLeft)
        self._epochComboBox = QtWidgets.QComboBox()
        self._epochComboBox.currentIndexChanged.connect(self._on_epoch_combo_box)
        hLayout0.addWidget(self._epochComboBox, alignment=QtCore.Qt.AlignLeft)

        # update on switch file
        self._fileLabel = QtWidgets.QLabel('File')
        hLayout0.addWidget(self._fileLabel, alignment=QtCore.Qt.AlignLeft)

        # update for all response types (switch file, set sweep, analyze, ...)
        self._numSpikesLabel = QtWidgets.QLabel('unknown spikes')
        hLayout0.addWidget(self._numSpikesLabel, alignment=QtCore.Qt.AlignLeft)

        hLayout0.addStretch()

        #
        # second row of controls
        hLayout1 = QtWidgets.QHBoxLayout()

        # a checkbox for each 'respond to' in the ResponseType enum
        for item in ResponseType:
            aCheckbox = QtWidgets.QCheckBox(item.value)
            aCheckbox.setChecked(self.responseOptions[item.name])
            aCheckbox.stateChanged.connect(functools.partial(self.toggleResponseOptions, item))
            hLayout1.addWidget(aCheckbox, alignment=QtCore.Qt.AlignLeft)

        hLayout0.addStretch()

        #toolbar layout needs to be in a widget so it can be hidden
        _mainWidget = QtWidgets.QWidget()
        _topToolbarLayout = QtWidgets.QVBoxLayout(_mainWidget)
        _topToolbarLayout.addLayout(hLayout0)
        _topToolbarLayout.addLayout(hLayout1)

        return _mainWidget
    
    # def __on_checkbox_clicked(self, checkBoxName, checkBoxState):
    #     logger.info(checkBoxName, checkBoxState)

# Not used 20220609
class myWidget(QtWidgets.QWidget):
    """Helper class to open a PyQt window from within a plugin.
    """
    def __init__(self, parentPlugin, doDark=True):
        """
        Arguments:
            parentPlugin (sanpyPlugin): [sanpyPlugin][sanpy.interface.plugins.sanpyPlugin.sanpyPlugin#sanpyPlugin]
            doDark (bool): If True then use dark theme, False use light theme.
        """
        super().__init__()
        self._parentPlugin = parentPlugin

        #self._mySetWindowTitle()

        # breeze
        if doDark and qdarkstyle is not None:
            self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
        else:
            self.setStyleSheet("")

        #self.show()

    '''
    def _mySetWindowTitle(self, windowTitle):
        """
        Set pyqt window title from current ba
        """
        self.setWindowTitle(windowTitle)
    '''

    @property
    def parentPlugin(self):
        return self._parentPlugin

    def keyPressEvent(self, event):
        """
        Used so user can turn on/off responding to analysis changes

        Args: event (PyQt5.QtGui.QKeyEvent): Qt event

        TODO: Add to mpl windows
        """
        #logger.info(event)
        self._parentPlugin.keyPressEvent(event)

    def keyReleaseEvent(self, event):
        #logger.info(event)
        self._parentPlugin.keyReleaseEvent(event)

    def contextMenuEvent(self, event):
        """Right-click context menu depends on enum ReponseType."""
        self._parentPlugin.contextMenuEvent(event)

    def closeEvent(self, event):
        logger.info(f'event:{type(event)}')
        self._parentPlugin.onClose(event)

def test_plugin():
    import sys
    from PyQt5 import QtCore, QtWidgets, QtGui
    import sanpy
    import sanpy.interface

    # create a PyQt application
    app = QtWidgets.QApplication([])

    # load and analyze sample data
    path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
    ba = sanpy.bAnalysis(path)
    ba.spikeDetect()

    # open the interface for the 'saveAnalysis' plugin.
    sa = sanpy.interface.plugins.plotScatter(ba=ba, startStop=None)

    sys.exit(app.exec_())

if __name__ == '__main__':
    test_plugin()
