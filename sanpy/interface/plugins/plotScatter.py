import math

from typing import Union, Dict, List, Tuple, Optional

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtWidgets, QtGui

from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector  # To click+drag rectangular selection
import matplotlib.markers as mmarkers  # To define different markers for scatter

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin

def getPlotMarkersAndColors(ba : sanpy.bAnalysis,
                            spikeList : List[int],
                            hue = '') -> dict:
    """Given a list of spikes, get plotting color and symbol.
    
    Parse bAnalysis for 'condition' and usertype'

    Parameters
    ----------
    ba : sanpy.bAnalysis
    spikeList List[int]
    hue : str
        In ("", "Time", "Sweep")

    TODO: Add one more return for pyqtgraph markers in ('o', 'star', 't', 't3')
    """
    cMap = mpl.pyplot.cm.coolwarm.copy()
    cMap.set_under("white")  # only works for dark theme
    # do not specify 'c' argument, we set colors using set_facecolor, set_color

    cMap = None
    colorMapArray = None
    faceColors = None
    pathList = None
    markerList_pg = None

    if hue == "Time":
        colorMapArray = np.array(range(len(spikeList)))
        # self.lines.set_array(colorMapArray)  # set_array is for a color map
        # self.lines.set_cmap(cmap)  # mpl.pyplot.cm.coolwarm
        # self.lines.set_color(faceColors)

    elif hue == "Sweep":
        # color sweeps
        _sweeps = ba.getSpikeStat(spikeList, 'sweep')
        colorMapArray = np.array(range(len(_sweeps)))
        # self.lines.set_array(colorMapArray)  # set_array is for a color map
        # self.lines.set_cmap(self.cmap)  # mpl.pyplot.cm.coolwarm
        # self.lines.set_color(faceColors)

    else:
        # tmpColor = np.array(range(len(xData)))
        # assuming self.cmap.set_under("white")

        # from matplotlib.colors import ListedColormap
        #_color_dict = {1: "blue", 2: "red", 13: "orange", 7: "green"}
        _color_dict = {
            "good": 'c',  # cyan
            "bad": 'r',  # red
            #'userType1':(0,0,1,1), # blue
            #'userType2':(0,1,1,1), # cyan
            #'userType3':(1,0,1,1), # magenta
        }
        _marker_dict = {
            "noUserType": mmarkers.MarkerStyle("o"),  # circle
            "userType1": mmarkers.MarkerStyle("*"),  # star
            "userType2": mmarkers.MarkerStyle("v"),  # triangle_down
            "userType3": mmarkers.MarkerStyle("<"),  # triangle_left
        }

        _marker_dict_pg = {
            "noUserType": 'o',
            "userType1": 'star',
            "userType2": 't',
            "userType3": 't3',
        }

        # no need for a cmap ???
        # cm = ListedColormap([_color_dict[x] for x in _color_dict.keys()])
        # self.lines.set_cmap(cm)

        goodSpikes = ba.getSpikeStat(spikeList, "include")
        #print('goodSpikes:', goodSpikes)
        userTypeList = ba.getSpikeStat(spikeList, "userType")

        # logger.warning("   debug set spike stat, user types need to be int")
        # print('userTypeList:', type(userTypeList))
        # print(userTypeList)

        # user types will use symbols
        # tmpColors = [_color_dict['type'+num2str(x)] if x>0 else tmpColors[idx] for idx,x in enumerate(userTypeList)]
        # bad needs to trump user type !!!
        # faceColors is used to set_facecolor() and set_color
        if goodSpikes is not None:
            faceColors = [
                _color_dict["good"] if x else _color_dict["bad"]
                for idx, x in enumerate(goodSpikes)  # x is (good, bad), (1,0)
            ]
        #faceColors = np.array(faceColors)
        # print('tmpColors', type(tmpColors), tmpColors.shape, tmpColors)

        # self.lines.set_array(None)  # used to map [0,1] to color map
        # self.lines.set_facecolor(faceColors)
        # self.lines.set_color(faceColors)  # sets the outline

        # set user type 2 to 'star'
        # see: https://stackoverflow.com/questions/52303660/iterating-markers-in-plots/52303895#52303895
        # import matplotlib.markers as mmarkers
        markerList = []
        markerList_pg = []
        if userTypeList is not None:
            for x in userTypeList:
                markerList.append(
                    _marker_dict["userType" + str(x)] if x > 0 else _marker_dict['noUserType']
                )
                markerList_pg.append(
                    _marker_dict_pg["userType" + str(x)] if x > 0 else _marker_dict_pg['noUserType']
                )
            
        # tODO: roll this into above for loop
        pathList = []
        for marker in markerList:
            path = marker.get_path().transformed(marker.get_transform())
            pathList.append(path)
        #self.lines.set_paths(pathList)

    retDict = {
        'cMap': cMap,
        'colorMapArray': colorMapArray,
        'faceColors': faceColors,
        'pathList': pathList,
        'markerList_pg': markerList_pg,
    }

    # logger.info(f'spikeList: {spikeList}')
    # for k,v in retDict.items():
    #     print('    ', k, ':', v)

    return retDict

class plotScatter(sanpyPlugin):
    """Plot x/y statiistics as a scatter.

    Get stat names and variables from sanpy.bAnalysisUtil.getStatList()
    """

    myHumanName = "Plot Scatter"

    def __init__(self, **kwargs):
        """
        Args:
            ba (bAnalysis): Not required
        """
        super().__init__(**kwargs)

        self._hueList = ["None", "Time", "Sweep"]
        self._hue = "None"  # from ["None", "Time", "Sweep"]
        
        # april 2023, deactivated this, need to debug
        self.plotChasePlot = False  # i vs i-1
        
        # self.plotIsBad= True
        self.plotHistograms = True

        # keep track of what we are plotting.
        # use this in replot() and copy to clipboard.
        self.xStatName = None
        self.yStatName = None
        self.xStatHumanName = None
        self.yStatHumanName = None

        self.xData = []
        self.yData = []
        
        self._markerSize = 20

        # when we plot, we plot a subset of spikes
        # this list tells us the spikes we are plotting and [ind_1] gives us the real spike number
        self._plotSpikeNumber = []
        
        # self.xAxisSpikeNumber = []  # We need to keep track of this for 'Chase Plot'

        # main layout
        hLayout = QtWidgets.QHBoxLayout()
        hSplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        hLayout.addWidget(hSplitter)

        # coontrols and 2x stat list
        vLayout = QtWidgets.QVBoxLayout()

        # controls
        controlWidget = QtWidgets.QWidget()

        hLayout2 = QtWidgets.QHBoxLayout()

        #
        # self.b2 = QtWidgets.QCheckBox("Chase Plot")
        # self.b2.setEnabled(False)  # april 15, 2023, disbale for now (need to debug)
        # self.b2.setChecked(self.plotChasePlot)
        # self.b2.stateChanged.connect(lambda: self.btnstate(self.b2))
        # hLayout2.addWidget(self.b2)

        #
        # self.colorTime = QtWidgets.QCheckBox("Color Time")
        # self.colorTime.setChecked(self.plotColorTime)
        # self.colorTime.stateChanged.connect(lambda:self.btnstate(self.colorTime))
        # hLayout2.addWidget(self.colorTime)

        aLabel = QtWidgets.QLabel("Hue")
        hLayout2.addWidget(aLabel)
        aComboBox = QtWidgets.QComboBox()
        aComboBox.addItems(self._hueList)  # from none, time, sweep
        aComboBox.currentTextChanged.connect(self._on_select_hue)
        hLayout2.addWidget(aComboBox)

        #
        """
        self.colorType = QtWidgets.QCheckBox("Color Type")
        self.colorType.setChecked(self.plotColorType)
        self.colorType.stateChanged.connect(lambda:self.btnstate(self.colorType))
        hLayout2.addWidget(self.colorType)
        """

        #
        """
        self.showBad = QtWidgets.QCheckBox("Show Bad")
        self.showBad.setChecked(self.plotIsBad)
        self.showBad.stateChanged.connect(lambda:self.btnstate(self.showBad))
        hLayout2.addWidget(self.showBad)
        """

        #
        self.histogramCheckbox = QtWidgets.QCheckBox("Histograms")
        self.histogramCheckbox.setChecked(self.plotHistograms)
        self.histogramCheckbox.stateChanged.connect(
            lambda: self.btnstate(self.histogramCheckbox)
        )
        hLayout2.addWidget(self.histogramCheckbox)

        vLayout.addLayout(hLayout2)

        # second row of controls
        hLayout2_2 = QtWidgets.QHBoxLayout()

        aName = "Spike: None"
        self.spikeNumberLabel = QtWidgets.QLabel(aName)
        hLayout2_2.addWidget(self.spikeNumberLabel)

        vLayout.addLayout(hLayout2_2)

        # x and y stat lists
        hLayout3 = QtWidgets.QHBoxLayout()
        self.xPlotWidget = myStatListWidget(self, headerStr="X Stat")
        self.xPlotWidget.myTableWidget.selectRow(0)
        self.yPlotWidget = myStatListWidget(self, headerStr="Y Stat")
        self.yPlotWidget.myTableWidget.selectRow(7)
        hLayout3.addWidget(self.xPlotWidget)
        hLayout3.addWidget(self.yPlotWidget)
        vLayout.addLayout(hLayout3)

        controlWidget.setLayout(vLayout)

        #
        # create a mpl plot (self._static_ax, self.static_canvas)
        # self.mplWindow2()
        # plt.style.use('dark_background')
        if self.darkTheme:
            plt.style.use("dark_background")
        else:
            plt.rcParams.update(plt.rcParamsDefault)

        # this is dangerous, collides with self.mplWindow()
        self.fig = mpl.figure.Figure()
        self.static_canvas = backend_qt5agg.FigureCanvas(self.fig)
        self.static_canvas.setFocusPolicy(
            QtCore.Qt.ClickFocus
        )  # this is really tricky and annoying
        self.static_canvas.setFocus()
        # self.axs[idx] = self.static_canvas.figure.add_subplot(numRow,1,plotNum)

        self._switchScatter()
        """
        # gridspec for scatter + hist
        self.gs = self.fig.add_gridspec(2, 2,  width_ratios=(7, 2), height_ratios=(2, 7),
                                left=0.1, right=0.9, bottom=0.1, top=0.9,
                                wspace=0.05, hspace=0.05)

        self.axScatter = self.static_canvas.figure.add_subplot(self.gs[1, 0])
        self.axHistX = self.static_canvas.figure.add_subplot(self.gs[0, 0], sharex=self.axScatter)
        self.axHistY = self.static_canvas.figure.add_subplot(self.gs[1, 1], sharey=self.axScatter)


        # make initial empty scatter plot
        #self.lines, = self._static_ax.plot([], [], 'ow', picker=5)
        self.cmap = mpl.pyplot.cm.coolwarm
        self.cmap.set_under("white") # only works for dark theme
        #self.lines = self._static_ax.scatter([], [], c=[], cmap=self.cmap, picker=5)
        self.lines = self.axScatter.scatter([], [], c=[], cmap=self.cmap, picker=5)

        # make initial empty spike selection plot
        #self.spikeSel, = self._static_ax.plot([], [], 'oy')
        self.spikeSel, = self.axScatter.plot([], [], 'oy')

        # despine top/right
        self.axScatter.spines['right'].set_visible(False)
        self.axScatter.spines['top'].set_visible(False)
        self.axHistX.spines['right'].set_visible(False)
        self.axHistX.spines['top'].set_visible(False)
        self.axHistY.spines['right'].set_visible(False)
        self.axHistY.spines['top'].set_visible(False)
        """

        # can do self.mplToolbar.hide()
        # matplotlib.backends.backend_qt5.NavigationToolbar2QT
        self.mplToolbar = mpl.backends.backend_qt5agg.NavigationToolbar2QT(
            self.static_canvas, self.static_canvas
        )

        # put toolbar and static_canvas in a V layout
        plotWidget = QtWidgets.QWidget()
        vLayoutPlot = QtWidgets.QVBoxLayout()
        vLayoutPlot.addWidget(self.static_canvas)
        vLayoutPlot.addWidget(self.mplToolbar)
        plotWidget.setLayout(vLayoutPlot)

        # finalize
        # hLayout.addLayout(vLayout)
        hSplitter.addWidget(controlWidget)
        # hSplitter.addWidget(self.static_canvas) # add mpl canvas
        hSplitter.addWidget(plotWidget)

        # set the layout of the main window
        # playing with dock
        # self.mainWidget.setLayout(hLayout)

        # mar 17 was this
        # self.setLayout(hLayout)
        self.getVBoxLayout().addLayout(hLayout)

        # self.mainWidget.setGeometry(100, 100, 1200, 600)

        self.replot()

    def keyPressEvent(self, event):
        _handled = False
        isMpl = isinstance(event, mpl.backend_bases.KeyEvent)
        if isMpl:
            text = event.key
            logger.info(f'mpl key: "{text}"')
            if text in ['=', '+']:
                # increase scatter points
                _handled = True
                self._markerSize += 10
                logger.info(f'marker size is now {self._markerSize}')
                self.replot()
            elif text in ['-']:
                _handled = True
                self._markerSize -= 10
                if self._markerSize<0:
                    self._markerSize = 0
                logger.info(f'marker size is now {self._markerSize}')
                self.replot()
        if not _handled:
            super().keyPressEvent(event)

    def _switchScatter(self):
        """Switch between single scatter plot and scatter + marginal histograms"""

        if self.plotHistograms:
            # gridspec for scatter + hist
            self.gs = self.fig.add_gridspec(
                2,
                2,
                width_ratios=(7, 2),
                height_ratios=(2, 7),
                left=0.1,
                right=0.9,
                bottom=0.1,
                top=0.9,
                wspace=0.05,
                hspace=0.05,
            )
        else:
            self.gs = self.fig.add_gridspec(
                1, 1, left=0.1, right=0.9, bottom=0.1, top=0.9, wspace=0.05, hspace=0.05
            )

        self.static_canvas.figure.clear()
        if self.plotHistograms:
            self.axScatter = self.static_canvas.figure.add_subplot(self.gs[1, 0])

            # x/y hist
            self.axHistX = self.static_canvas.figure.add_subplot(
                self.gs[0, 0], sharex=self.axScatter
            )
            self.axHistY = self.static_canvas.figure.add_subplot(
                self.gs[1, 1], sharey=self.axScatter
            )
            #
            self.axHistX.spines["right"].set_visible(False)
            self.axHistX.spines["top"].set_visible(False)
            self.axHistY.spines["right"].set_visible(False)
            self.axHistY.spines["top"].set_visible(False)

            # self.axHistX.tick_params(axis="x", labelbottom=False) # no labels
            # self.axHistX.tick_params(axis="y", labelleft=False) # no labels
        else:
            self.axScatter = self.static_canvas.figure.add_subplot(self.gs[0, 0])
            self.axHistX = None
            self.axHistY = None

        # we might have memory garbage collection issues
        # passing self so we can receive selectSpikesFromHighlighter()
        self.myHighlighter = Highlighter(self, self.axScatter, [], [], [])

        #
        # we will always have axScatter
        #
        # make initial empty scatter plot
        self.cmap = mpl.pyplot.cm.coolwarm.copy()
        self.cmap.set_under("white")  # only works for dark theme
        # do not specify 'c' argument, we set colors using set_facecolor, set_color

        self.lines = self.axScatter.scatter([], [], picker=5)

        # make initial empty spike selection plot

        # self.spikeSel, = self.axScatter.plot([], [], 'x', markerfacecolor='none', color='y', markersize=10)  # no picker for selection
        # TODO: standardize this with Highlighter scatter
        # was this
        # self.spikeListSel, = self.axScatter.plot([], [], 'o', markerfacecolor='none', color='y', markersize=10)  # no picker for selection
        #logger.info("hard coding spike selection markerSize=10")

        # markerSize = self._markerSize / 2  # 10
        # (self.spikeListSel,) = self.axScatter.plot(
        #     [], [], "o", markersize=markerSize, color="yellow", zorder=10
        # )

        # despine top/right
        self.axScatter.spines["right"].set_visible(False)
        self.axScatter.spines["top"].set_visible(False)

        # TODO: refactor and use mplToolBar()
        # self.cid = self.static_canvas.mpl_connect("pick_event", self._on_spike_pick_event2)

        self.fig.canvas.mpl_connect("key_press_event", self.keyPressEvent)

        #
        # self.replot()

    def _old__on_spike_pick_event2(self, event):
        """Respond to user left-mouse clicks in mpl plot.

        Args:
            event : matplotlib.backend_bases.PickEvent
                PickEvent with indices in ind[]

        Notes:
            need to clean up fft on pick, it is still in base plugin class
        """

        # ignore when not left mouse button
        if event.mouseevent.button != 1:
            return

        # no hits
        if len(event.ind) < 1:
            return

        _clickedPlotIdx = event.ind[0]

        # convert to what we are actually plotting
        try:
            #_realSpikeNumber = self._plotSpikeNumber.index(_clickedPlotIdx)
            # get real spike number from subset of plotted psikes
            _realSpikeNumber = self._plotSpikeNumber[_clickedPlotIdx]
        except (IndexError) as e:
            logger.warning(f'  xxx we are not plotting _clickedPlotIdx {_clickedPlotIdx}')

        doZoom = False
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            doZoom = True

        #logger.info(f'  _clickedPlotIdx:{_clickedPlotIdx} _realSpikeNumber:{_realSpikeNumber}')
        logger.info(
            f"  got {len(event.ind)} candidates, first is spike:{_realSpikeNumber} doZoom:{doZoom}"
        )

        # propagate a signal to parent
        # TODO: use class SpikeSelectEvent()
        sDict = {
            "spikeList": [_realSpikeNumber],
            "doZoom": doZoom,
            "ba": self.ba,
        }
        logger.info(f'{self._myClassName()} -->> emit signalSelectSpikeList')
        self.signalSelectSpikeList.emit(sDict)

    def btnstate(self, b):
        state = b.isChecked()
        # if b.text() == "Respond To Analysis Changes":
        #    self.setRespondToAnalysisChange(state)
        if b.text() == "Chase Plot":
            self.plotChasePlot = state
            logger.info(f"plotChasePlot:{self.plotChasePlot}")
            self.replot()
        # elif b.text() == 'Color Time':
        #     self.plotColorTime = state
        #     logger.info(f'plotColorTime:{self.plotColorTime}')
        #     self.replot()

        # elif b.text() == 'Color Type':
        #    self.plotColorType = state
        #    logger.info(f'plotColorType:{self.plotColorType}')
        #    self.replot()
        # elif b.text() == 'Show Bad':
        #    self.plotIsBad = state
        #    logger.info(f'plotIsBad:{self.plotIsBad}')
        #    self.replot()
        elif b.text() == "Histograms":
            self.plotHistograms = state
            self._switchScatter()
            logger.info(f"plotHistograms:{self.plotHistograms}")
            self.replot()
        else:
            logger.warning(f'Did not respond to button "{b.text()}"')

    def _on_select_hue(self, hue: str):
        self._hue = hue
        self.replot()

    def setAxis(self):
        """Inherited, respond to user setting x-axis.

        Generate a list of spikes and select them.
        """

        logger.info('deactivated - april 30')

        # as of april 30, 2023, do nothin on set axis
        return
    
        startSec, stopSec = self.getStartStop()
        if startSec is None or stopSec is None:
            return

        # select spike in range
        thresholdSec = self.getStat("thresholdSec")
        _selectedSpikeList = [
            spikeIdx
            for spikeIdx, spikeSec in enumerate(thresholdSec)
            if (spikeSec > startSec and spikeSec < stopSec)
        ]
        self.setSelectedSpikes(_selectedSpikeList)
        self.selectSpikeList()

    def replot(self):
        """Replot when file or analysis changes.
        """

        logger.info(f"{self._myClassName()} sweepNumber:{self.sweepNumber} epochNumber:{self.epochNumber}")

        # get from stat lists
        xHumanStat, xStat = self.xPlotWidget.getCurrentStat()
        yHumanStat, yStat = self.yPlotWidget.getCurrentStat()

        # logger.info(f'x:"{xHumanStat}" y:"{yHumanStat}"')
        # logger.info(f'x:"{xStat}" y:"{yStat}"')

        if self.ba is None or xHumanStat is None or yHumanStat is None:
            xData = []
            yData = []
            self._plotSpikeNumber = []
        else:
            # use getFullList when we have a recording with
            # multiple sweeps and epochs
            xData = self.getStat(xStat, getFullList=False)
            yData = self.getStat(yStat, getFullList=False)
            self._plotSpikeNumber = self.getStat('spikeNumber')

        # logger.warning('debug plotting epochs')
        # print('xData:', xData)

        #
        # TODO: use ba.getStat() option for this.)
        xData = np.array(xData)
        yData = np.array(yData)

        #
        # return if we got no data, happens when there is no analysis
        if (
            xData is None
            or yData is None
            or np.isnan(xData).all()
            or np.isnan(yData).all()
        ):
            # We get here when there is no analysis
            # logger.warning(f'Did not find either xStat: "{xStat}" or yStat: "{yStat}"')
            self.lines.set_offsets([np.nan, np.nan])
            self.scatter_hist([], [], self.axHistX, self.axHistY)
            self.static_canvas.draw()
            return

        self.xStatName = xStat
        self.yStatName = yStat
        self.xStatHumanName = xHumanStat
        self.yStatHumanName = yHumanStat

        # need to mask color and marker
        if self.plotChasePlot:
            # keep track of x-axis spike number (for chase plot)
            xAxisSpikeNumber = self.getStat("spikeNumber")
            xAxisSpikeNumber = np.array(xAxisSpikeNumber)

            # on selection, ind will refer to y-axis spike
            xData = xData[1:-1]  # x is the reference spike for marking (bad, type)
            yData = yData[0:-2]
            #
            # xAxisSpikeNumber = xAxisSpikeNumber[1:-1]
            xAxisSpikeNumber = xAxisSpikeNumber[0:-2]

        self.xData = xData
        self.yData = yData
        # self.xAxisSpikeNumber = xAxisSpikeNumber

        # data
        data = np.stack([xData, yData], axis=1)
        self.lines.set_offsets(data)  # (N, 2)
        
        _sizes = [self._markerSize] * len(xData)
        self.lines.set_sizes(_sizes)

        # AttributeError: 'Line2D' object has no attribute 'set_sizes'
        # _sizes = [self._markerSize * 0.3] * len(xData)
        # self.spikeListSel.set_sizes()

        # 20230417
        plotSpikeNumberList = self.getStat('spikeNumber', getFullList=False)
        _tmpDict = getPlotMarkersAndColors(self.ba, plotSpikeNumberList, self._hue)

        cMap = _tmpDict['cMap']
        colorMapArray = _tmpDict['colorMapArray']
        faceColors = _tmpDict['faceColors']
        pathList = _tmpDict['pathList']

        self.lines.set_array(colorMapArray)  # set_array is for a color map
        self.lines.set_cmap(cMap)  # mpl.pyplot.cm.coolwarm
        self.lines.set_color(faceColors)
        self.lines.set_color(faceColors)  # sets the outline
        self.lines.set_paths(pathList)

        #
        # color
        # if self._hue == "Time":
        #     tmpColor = np.array(range(len(xData)))
        #     self.lines.set_array(tmpColor)  # set_array is for a color map
        #     self.lines.set_cmap(self.cmap)  # mpl.pyplot.cm.coolwarm
        #     self.lines.set_color(None)
        # elif self._hue == "Sweep":
        #     # color sweeps
        #     _sweeps = self.getStat("sweep")
        #     tmpColor = np.array(range(len(_sweeps)))
        #     self.lines.set_array(tmpColor)  # set_array is for a color map
        #     self.lines.set_cmap(self.cmap)  # mpl.pyplot.cm.coolwarm
        #     self.lines.set_color(None)

        # else:
        #     # tmpColor = np.array(range(len(xData)))
        #     # assuming self.cmap.set_under("white")

        #     # from matplotlib.colors import ListedColormap
        #     color_dict = {1: "blue", 2: "red", 13: "orange", 7: "green"}
        #     color_dict = {
        #         "good": (0, 1, 1, 1),  # cyan
        #         "bad": (1, 0, 0, 1),  # red
        #         #'userType1':(0,0,1,1), # blue
        #         #'userType2':(0,1,1,1), # cyan
        #         #'userType3':(1,0,1,1), # magenta
        #     }
        #     marker_dict = {
        #         "userType1": mmarkers.MarkerStyle("*"),  # star
        #         "userType2": mmarkers.MarkerStyle("v"),  # triangle_down
        #         "userType3": mmarkers.MarkerStyle("<"),  # triangle_left
        #     }

        #     # no need for a cmap ???
        #     # cm = ListedColormap([color_dict[x] for x in color_dict.keys()])
        #     # self.lines.set_cmap(cm)

        #     goodSpikes = self.getStat("include")
        #     userTypeList = self.getStat("userType")

        #     logger.warning("   debug set spike stat, user types need to be int")
        #     logger.warning("   we ARE NOT GETTING THE CORRECT SPIKE INDEX")
        #     # print(userTypeList)

        #     if self.plotChasePlot:
        #         # xData = xData[1:-1] # x is the reference spike for marking (bad, type)
        #         # goodSpikes = goodSpikes[1:-1]
        #         # userTypeList = userTypeList[1:-1]
        #         goodSpikes = goodSpikes[0:-2]
        #         userTypeList = userTypeList[0:-2]

        #     tmpColors = [color_dict["bad"]] * len(xData)  # start as all good

        #     # user types will use symbols
        #     # tmpColors = [color_dict['type'+num2str(x)] if x>0 else tmpColors[idx] for idx,x in enumerate(userTypeList)]
        #     # bad needs to trump user type !!!
        #     tmpColors = [
        #         color_dict["good"] if x else tmpColors[idx]
        #         for idx, x in enumerate(goodSpikes)
        #     ]
        #     tmpColors = np.array(tmpColors)
        #     # print('tmpColors', type(tmpColors), tmpColors.shape, tmpColors)

        #     self.lines.set_array(None)  # used to map [0,1] to color map
        #     self.lines.set_facecolor(tmpColors)
        #     self.lines.set_color(tmpColors)  # sets the outline

        #     # set user type 2 to 'star'
        #     # see: https://stackoverflow.com/questions/52303660/iterating-markers-in-plots/52303895#52303895
        #     # import matplotlib.markers as mmarkers
        #     myMarkerList = [
        #         marker_dict["userType" + str(x)] if x > 0 else mmarkers.MarkerStyle("o")
        #         for x in userTypeList
        #     ]
        #     myPathList = []
        #     for myMarker in myMarkerList:
        #         path = myMarker.get_path().transformed(myMarker.get_transform())
        #         myPathList.append(path)
        #     self.lines.set_paths(myPathList)

        #
        # update highlighter, needs coordinates of x/y to highlight
        self.myHighlighter.setData(xData, yData, self._plotSpikeNumber)

        # label axes
        xStatLabel = xHumanStat
        yStatLabel = yHumanStat
        if self.plotChasePlot:
            xStatLabel += " [i]"
            yStatLabel += " [i-1]"
        self.axScatter.set_xlabel(xStatLabel)
        self.axScatter.set_ylabel(yStatLabel)

        # don't cancel on replot
        """
        # cancel any selections
        self.spikeSel.set_data([], [])
        #self.spikeSel.set_offsets([], [])
        self.spikeListSel.set_data([], [])
        #self.spikeListSel.set_offsets([], [])
        """

        xMin = np.nanmin(xData)
        xMax = np.nanmax(xData)
        yMin = np.nanmin(yData)
        yMax = np.nanmax(yData)
        # expand by 5%
        xSpan = abs(xMax - xMin)
        percentSpan = xSpan * 0.05
        xMin -= percentSpan
        xMax += percentSpan
        #
        ySpan = abs(yMax - yMin)
        percentSpan = ySpan * 0.05
        yMin -= percentSpan
        yMax += percentSpan

        #logger.warning(f'refactor this, do not always set x/y lim')
        # UserWarning: Attempting to set identical left == right == 0.0275 results in singular transformations; automatically expanding.
        self.axScatter.set_xlim([xMin, xMax])
        self.axScatter.set_ylim([yMin, yMax])

        # self.scatter_hist(xData, yData, self.axScatter, self.axHistX, self.axHistY)
        self.scatter_hist(xData, yData, self.axHistX, self.axHistY)

        # redraw
        self.static_canvas.draw()
        # was this
        # self.repaint() # update the widget

    # def scatter_hist(self, x, y, ax, ax_histx, ax_histy):
    def scatter_hist(self, x, y, ax_histx, ax_histy):
        """
        plot a scatter with x/y histograms in margin

        Args:
            x (date):
            y (data):
            ax_histx (axes) Histogram Axes
            ax_histy (axes) Histogram Axes
        """

        xBins = "auto"
        yBins = "auto"

        xTmp = np.array(x)  # y[~np.isnan(y)]
        xTmp = xTmp[~np.isnan(xTmp)]
        xTmpBins = np.histogram_bin_edges(xTmp, "auto")
        xNumBins = len(xTmpBins)
        if xNumBins * 2 < len(x):
            xNumBins *= 2
        xBins = xNumBins

        yTmp = np.array(y)  # y[~np.isnan(y)]
        yTmp = yTmp[~np.isnan(yTmp)]
        yTmpBins = np.histogram_bin_edges(yTmp, "auto")
        yNumBins = len(yTmpBins)
        if yNumBins * 2 < len(y):
            yNumBins *= 2
        yBins = yNumBins

        # x
        if ax_histx is not None:
            ax_histx.clear()
            nHistX, binsHistX, patchesHistX = ax_histx.hist(
                x, bins=xBins, facecolor="silver", edgecolor="gray"
            )
            ax_histx.tick_params(axis="x", labelbottom=False)  # no labels
            # ax_histx.spines['right'].set_visible(False)
            # ax_histx.spines['top'].set_visible(False)
            # ax_histx.yaxis.set_ticks_position('left')
            # ax_histx.xaxis.set_ticks_position('bottom')
            # print('  binsHistX:', len(binsHistX))
        # y
        if ax_histy is not None:
            ax_histy.clear()
            nHistY, binsHistY, patchesHistY = ax_histy.hist(
                y,
                bins=yBins,
                orientation="horizontal",
                facecolor="silver",
                edgecolor="gray",
            )
            ax_histy.tick_params(axis="y", labelleft=False)
            # ax_histy.yaxis.set_ticks_position('left')
            # ax_histy.xaxis.set_ticks_position('bottom')
            # print('  binsHistY:', len(binsHistY))

    def selectSpikeList(self):
        """Use getSelectedSpikes() to select spikes.
        
        Notes
        -----
        Always have to use the list of spikes we are actually plotting
        self._plotSpikeNumber
        """
        spikeList = self.getSelectedSpikes()

        logger.info(f"{self._myClassName()} spikeList:{len(spikeList)} {self}")

        if self.xStatName is None or self.yStatName is None:
            return

        # TODO (error) when we are plotting just one epoch (like 2), we get index errors
        
        # if spikeList is not None:
        _plotSpikeIndexList = []
        if len(spikeList) > 0:
            for _realSpikeNumber in spikeList:
                # _realSpikeNumber is the actual spike number of bAnalysis
                try:
                    # for each spike in spikeList
                    # need to find the index into the actual plot
                    # this is the only place we need index() and it runs at n^2
                    _plotSpikeIndex = self._plotSpikeNumber.index(_realSpikeNumber)
                    _plotSpikeIndexList.append(_plotSpikeIndex)
                except (ValueError) as e:
                    logger.warning(f'we are not plotting spike number {_realSpikeNumber}')

            # xData = [self.xData[spikeList]]
            # yData = [self.yData[spikeList]]
            xData = [self.xData[_plotSpikeIndexList]]
            yData = [self.yData[_plotSpikeIndexList]]

        else:
            xData = []
            yData = []

        # logger.info(f'!!! SET DATA {xData} {yData}')
        #self.spikeListSel.set_data(xData, yData)
        #self.myHighlighter.setData(xData, yData, _plotSpikeIndexList)
        self.myHighlighter.selectSpikeList(_plotSpikeIndexList)

        # update a little info about first spike
        _str = ""
        if len(spikeList) > 0:
            firstSpike = spikeList[0]
            _oneDict = self.ba.getOneSpikeDict(firstSpike)
            _str += f"Number {_oneDict['spikeNumber']}"
            _str += f" UserType {_oneDict['userType']}"
            _str += f" Sweep {_oneDict['sweep']}"
            _str += f" Epoch {_oneDict['epoch']}"

        self.spikeNumberLabel.setText(f"First Spike Selection: {_str}")

        self.static_canvas.draw()
        # was this
        # self.repaint() # update the widget

    def old_selectSpike(self, sDict=None):
        """Select a spike

        sDict (dict): NOT USED
        """

        # logger.info(sDict)

        # spikeNumber = sDict['spikeNumber']
        # spikeList = [spikeNumber]

        spikeNumber = self.selectedSpike

        if self.xStatName is None or self.yStatName is None:
            return

        xData = []
        yData = []
        if spikeNumber is not None:
            try:
                xData = [self.xData[spikeNumber]]
                yData = [self.yData[spikeNumber]]
            except IndexError as e:
                logger.error(e)

        self.spikeSel.set_data(xData, yData)
        # self.spikeSel.set_offsets(xData, yData)

        self.spikeNumberLabel.setText(f"Spike: {spikeNumber}")

        self.static_canvas.draw()
        # was this
        # self.repaint() # update the widget

    def selectSpikesFromHighlighter(self, selectedSpikeList):
        """User selected some spikes with Highlighter -->> Propogate to main.
        
        Notes
        =====
        selectedSpikeList is based on what we are plotting (a subset of all spikes)
        get actual spikes from self._plotSpikeNumber
        """
        # logger.info(f'got highlighter plot selectedSpikeList: {selectedSpikeList}')

        if len(selectedSpikeList) > 0:
            actualSpikeList = []
            for _plotSpike in selectedSpikeList:
                try:
                    actualSpike = self._plotSpikeNumber[_plotSpike]
                    actualSpikeList.append(actualSpike)
                except (IndexError) as e:
                    logger.warning(f'we are not plotting spike {_plotSpike}')

            # print('    selectedSpikeList:', selectedSpikeList)
            # print('    actualSpikeList:', actualSpikeList)
            
            #self.setSelectedSpikes(selectedSpikeList)
            self.setSelectedSpikes(actualSpikeList)
            sDict = {
                "spikeList": self.getSelectedSpikes(),
                "doZoom": False,  # never zoom on multiple spike selection
                "ba": self.ba,
            }
            logger.info(f'{self._myClassName()} -->> emit signalSelectSpikeList')
            logger.info(f"spikeList: {sDict['spikeList']}")
            
            self._blockSlots = True
            self.signalSelectSpikeList.emit(sDict)
            self._blockSlots = False

    def toolbarHasSelection(self):
        """Return true if either ['zoom rect', 'pan/zoom'] are selected

        This is needed to cancel mouse clicks in Highlighter and right click in SanPyPlugin
        """
        state = self.mplToolbar.mode
        return state in ["zoom rect", "pan/zoom"]

    def prependMenus(self, contextMenu):
        """Prepend menus to context menu.
        
        Inherited from sanpyPlugin
        """

        noSpikesSelected = len(self.getSelectedSpikes()) == 0

        includeAction = contextMenu.addAction("Accept")
        includeAction.setDisabled(noSpikesSelected)  # disable if no spikes

        rejectAction = contextMenu.addAction("Reject")
        rejectAction.setDisabled(noSpikesSelected)

        userType1_action = contextMenu.addAction("User Type 1")
        userType1_action.setDisabled(noSpikesSelected)

        userType2_action = contextMenu.addAction("User Type 2")
        userType2_action.setDisabled(noSpikesSelected)

        userType3_action = contextMenu.addAction("User Type 3")
        userType3_action.setDisabled(noSpikesSelected)

        userType4_action = contextMenu.addAction("User Type 4")
        userType4_action.setDisabled(noSpikesSelected)

        userType5_action = contextMenu.addAction("User Type 5")
        userType5_action.setDisabled(noSpikesSelected)

        userType4_action = contextMenu.addAction("Reset User Type")
        userType4_action.setDisabled(noSpikesSelected)

        contextMenu.addSeparator()

    def handleContextMenu(self, action):
        """
        Returns:
            True if handled, otherwise False
        """
        if action is None:
            return False

        text = action.text()
        logger.info(f'Action text "{text}"')

        _selectedSpikes = self.getSelectedSpikes()

        # eventDict = setSpikeStatEvent
        setSpikeStatEvent = {}
        setSpikeStatEvent["ba"] = self.ba
        setSpikeStatEvent["spikeList"] = self.getSelectedSpikes()
        setSpikeStatEvent["colStr"] = None  # colStr
        setSpikeStatEvent["value"] = None  # value

        # logger.info(f"  -->> emit setSpikeStatEvent:{setSpikeStatEvent}")
        # self.signalSetSpikeStat.emit(setSpikeStatEvent)

        handled = False
        if text == "Accept":
            # print('Set selected spikes to include (not isbad)')
            # self.ba.setSpikeStat(_selectedSpikes, "include", False)
            setSpikeStatEvent["colStr"] = 'include'  # colStr
            setSpikeStatEvent["value"] = True  # value
            # self.replot()
            handled = True
        elif text == "Reject":
            # print('Set selected spikes to reject (isbad)')
            # self.ba.setSpikeStat(_selectedSpikes, "include", True)
            setSpikeStatEvent["colStr"] = 'include'  # colStr
            setSpikeStatEvent["value"] = False  # value
            # self.replot()
            handled = True
        elif text == "User Type 1":
            # self.ba.setSpikeStat(_selectedSpikes, "userType", 1)
            setSpikeStatEvent["colStr"] = 'userType'  # colStr
            setSpikeStatEvent["value"] = 1  # value
            # self.replot()
            handled = True
        elif text == "User Type 2":
            # self.ba.setSpikeStat(_selectedSpikes, "userType", 2)
            setSpikeStatEvent["colStr"] = 'userType'  # colStr
            setSpikeStatEvent["value"] = 2  # value
            # self.replot()
            handled = True
        elif text == "User Type 3":
            # self.ba.setSpikeStat(_selectedSpikes, "userType", 3)
            setSpikeStatEvent["colStr"] = 'userType'  # colStr
            setSpikeStatEvent["value"] = 3  # value
            # self.replot()
            handled = True
        elif text == "User Type 4":
            setSpikeStatEvent["colStr"] = 'userType'  # colStr
            setSpikeStatEvent["value"] = 4  # value
            handled = True
        elif text == "User Type 5":
            setSpikeStatEvent["colStr"] = 'userType'  # colStr
            setSpikeStatEvent["value"] = 5  # value
            handled = True
        elif text == "Reset User Type":
            # self.ba.setSpikeStat(_selectedSpikes, "userType", 0)
            setSpikeStatEvent["colStr"] = 'userType'  # colStr
            setSpikeStatEvent["value"] = 0  # value
            # self.replot()
            handled = True
        else:
            # logger.info(f'Action not understood "{text}"')
            pass

        if handled:
            logger.info(f"  -->> emit setSpikeStatEvent:{setSpikeStatEvent}")
            self.signalUpdateAnalysis.emit(setSpikeStatEvent)

        return handled

    def copyToClipboard(self):
        """Copy current x/y stats to clipboard with some other book-keeping.

        For example: spike number, spike time (s), is bad, user type, and file name.
        """
        spikeNumber = self.getStat("spikeNumber")
        spikeTimeSec = self.getStat("thresholdSec")
        xStat = self.getStat(self.xStatName)
        yStat = self.getStat(self.yStatName)
        goodSpikes = self.getStat("include")
        userType = self.getStat("userType")
        file = self.getStat("file")

        columns = [
            "Spike Number",
            "Spike Time(s)",
            self.xStatHumanName,
            self.yStatHumanName,
            "Include",
            "User Type",
            "File",
        ]
        df = pd.DataFrame(columns=columns)
        df["Spike Number"] = spikeNumber
        df["Spike Time(s)"] = spikeTimeSec
        df[self.xStatHumanName] = xStat
        df[self.yStatHumanName] = yStat
        df["Include"] = goodSpikes
        df["User Type"] = userType
        df["File"] = file

        excel = True
        sep = "\t"
        df.to_clipboard(excel=excel, sep=sep)

        logger.info(f"Copied {len(df)} spikes to clipboard.")


class myStatListWidget(QtWidgets.QWidget):
    """
    Widget to display a table with selectable stats.

    Gets list of stats from: sanpy.bAnalysisUtil.getStatList()
    """

    def __init__(self, myParent, statList=None, headerStr="Stat", parent=None):
        """
        Parameters
        ----------
        myParent : sanpy.interface.plugins.sanpyPlugin
        """
        super().__init__(parent)

        self.myParent = myParent
        if statList is not None:
            self.statList = statList
        else:
            self.statList = sanpy.bAnalysisUtil.getStatList()
        self._rowHeight = 9

        self.myQVBoxLayout = QtWidgets.QVBoxLayout(self)

        self.myTableWidget = QtWidgets.QTableWidget()
        self.myTableWidget.setWordWrap(False)
        self.myTableWidget.setRowCount(len(self.statList))
        self.myTableWidget.setColumnCount(1)
        self.myTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.myTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.myTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.myTableWidget.cellClicked.connect(self.on_scatter_toolbar_table_click)

        # set font size of table (default seems to be 13 point)
        # fnt = self.font()
        # fnt.setPointSize(self._rowHeight)
        # self.myTableWidget.setFont(fnt)

        headerLabels = [headerStr]
        self.myTableWidget.setHorizontalHeaderLabels(headerLabels)

        header = self.myTableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        # QHeaderView will automatically resize the section to fill the available space. The size cannot be changed by the user or programmatically.
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

        for idx, stat in enumerate(self.statList):
            item = QtWidgets.QTableWidgetItem(stat)
            self.myTableWidget.setItem(idx, 0, item)
            self.myTableWidget.setRowHeight(idx, self._rowHeight)

        # assuming dark theme
        # does not work
        """
        p = self.myTableWidget.palette()
        color1 = QtGui.QColor('#222222')
        color2 = QtGui.QColor('#555555')
        p.setColor(QtGui.QPalette.Base, color1)
        p.setColor(QtGui.QPalette.AlternateBase, color2)
        self.myTableWidget.setPalette(p)
        self.myTableWidget.setAlternatingRowColors(True)
        """
        self.myQVBoxLayout.addWidget(self.myTableWidget)

        # select a default stat
        self.myTableWidget.selectRow(0)  # hard coding 'Spike Frequency (Hz)'

    def getCurrentRow(self):
        return self.myTableWidget.currentRow()

    def getCurrentStat(self):
        # assuming single selection
        row = self.getCurrentRow()
        humanStat = self.myTableWidget.item(row, 0).text()

        # convert from human readbale to backend
        try:
            stat = self.statList[humanStat]["name"]
        except KeyError as e:
            logger.error(f'Did not find humanStat "{humanStat}" exception:{e}')
            humanStat = None
            stat = None
            # for k,v in

        return humanStat, stat

    @QtCore.pyqtSlot()
    def on_scatter_toolbar_table_click(self):
        """
        replot the stat based on selected row
        """
        # print('*** on table click ***')
        row = self.myTableWidget.currentRow()
        if row == -1 or row is None:
            return
        # yStat = self.myTableWidget.item(row,0).text()
        self.myParent.replot()

    """
    @QtCore.pyqtSlot()
    def on_button_click(self, name):
        print('=== myStatPlotToolbarWidget.on_button_click() name:', name)
    """


class Highlighter(object):
    """
    See: https://stackoverflow.com/questions/31919765/choosing-a-box-of-data-points-from-a-plot
    """

    def __init__(self, parentPlot, ax, x, y, plotSpikeNumber):
        self._parentPlot = parentPlot
        self.ax = ax
        self.canvas = ax.figure.canvas

        self.x = None  # these are set in setData
        self.y = None
        self._plotSpikeNumber = None
        #self._plotSpikeNumber = None

        self.setData(x, y, self._plotSpikeNumber)

        # mask will be set in self.setData
        if x and y:
            self.mask = np.zeros(x.shape, dtype=bool)
        else:
            self.mask = None

        markerSize = 50
        self._highlight = ax.scatter([], [], s=markerSize, color="yellow", zorder=10)

        # here self is setting the callback and calls __call__
        # self.selector = RectangleSelector(ax, self, useblit=True, interactive=False)
        # matplotlib.widgets.RectangleSelector
        self.selector = RectangleSelector(
            ax,
            self._HighlighterReleasedEvent,
            button=[1],
            useblit=True,
            interactive=False,
        )

        self.mouseDownEvent = None
        self.keyIsDown = None

        # april 2023, adding ?
        self._keepPickEvent = self.ax.figure.canvas.mpl_connect("pick_event", self._on_spike_pick_event3)

        self.ax.figure.canvas.mpl_connect("key_press_event", self._keyPressEvent)
        self.ax.figure.canvas.mpl_connect("key_release_event", self._keyReleaseEvent)

        # remember, sanpyPlugin is installing for key press and on pick
        self.keepOnMotion = self.ax.figure.canvas.mpl_connect(
            "motion_notify_event", self.on_mouse_move
        )
        self.keepMouseDown = self.ax.figure.canvas.mpl_connect(
            "button_press_event", self.on_button_press
        )
        self._keepMouseDown = self.ax.figure.canvas.mpl_connect(
            "button_release_event", self.on_button_release
        )

    def _keyPressEvent(self, event):
        # logger.info(event)
        self.keyIsDown = event.key

    def _keyReleaseEvent(self, event):
        # logger.info(event)
        self.keyIsDown = None

    def _on_spike_pick_event3(self, event):
        """
        
        Parameters
        ----------
        event : matplotlib.backend_bases.PickEvent
        """

        # ignore when not left mouse button
        if event.mouseevent.button != 1:
            return

        # no hits
        if len(event.ind) < 1:
            return

        _clickedPlotIdx = event.ind[0]
        logger.info(f'HighLighter _clickedPlotIdx: {_clickedPlotIdx} keyIsDown:{self.keyIsDown}')

        # convert to what we are actually plotting
        try:
            #_realSpikeNumber = self._plotSpikeNumber.index(_clickedPlotIdx)
            # get real spike number from subset of plotted psikes
            _realSpikeNumber = self._plotSpikeNumber[_clickedPlotIdx]
        except (IndexError) as e:
            logger.warning(f'  xxx we are not plotting _clickedPlotIdx {_clickedPlotIdx}')

        logger.info(f'_realSpikeNumber: {_realSpikeNumber}')

        # xData = self.x[_realSpikeNumber]
        # yData = self.y[_realSpikeNumber]
        # self._highlight.set_offsets([xData, yData])

        # if shift then add to mask
        # self.mask |= _insideMask
        newMask = np.zeros(self.x.shape, dtype=bool)
        newMask[_clickedPlotIdx] = True
        
        if self.keyIsDown == "shift":
            # oldMask = np.where(self.mask == True)
            # oldMask = oldMask[0]  # why does np do this ???
            # print('oldMask:', oldMask)

            newSelectedSpikes = np.where(newMask == True)
            newSelectedSpikes = newSelectedSpikes[0]  # why does np do this ???
            #print('newSelectedSpikes:', newSelectedSpikes)

            # add to mask
            self.mask |= newMask

            # print('newMask:')
            # print(newMask)
            # print('self.mask:')
            # print(self.mask)
            
        else:
            # replace with new
            self.mask = newMask

        # newMask = np.where(self.mask == True)
        # newMask = newMask[0]  # why does np do this ???
        # print('2) newMask:', newMask)

        xy = np.column_stack([self.x[self.mask], self.y[self.mask]])
        self._highlight.set_offsets(xy)
        
        self._HighlighterReleasedEvent()

        self.canvas.draw()

    def on_button_press(self, event):
        """
        Args:
            event : matplotlib.backend_bases.MouseEvent
        """
    
        # logger.info(f'Highlighter')

        # don't take action on right-click
        if event.button != 1:
            # not the left button
            # print('  rejecting not button 1')
            return

        # do nothing in zoom or pan/zoom is active
        # finding documentation on mpl toolbar is near impossible
        # https://stackoverflow.com/questions/20711148/ignore-matplotlib-cursor-widget-when-toolbar-widget-selected
        # state = self._parentPlot.static_canvas.manager.toolbar.mode  # manager is coming up None
        if self._parentPlot.toolbarHasSelection():
            return
        # was this
        # state = self._parentPlot.mplToolbar.mode
        # if state in ['zoom rect', 'pan/zoom']:
        #    logger.info(f'Ignoring because tool "{state}" is active')
        #    return

        self.mouseDownEvent = event
    
        # not sure why I was clearing the mask here
        if self.keyIsDown == "shift":
            # if shift is down then add to mask
            pass
        else:
            # create a new mask
            #logger.info('CLEARING MASK')
            #self.mask = np.zeros(self.x.shape, dtype=bool)
            pass

    def on_button_release(self, event):
        logger.info(f'Highlighter')

        # don't take action on right-click
        if event.button != 1:
            # not the left button
            # print('  rejecting not button 1')
            return

        self.mouseDownEvent = None

    def on_mouse_move(self, event):
        """When mouse is down, respond to movement and select points.

        Parameters
        ----------
        event : matplotlib.backend_bases.MouseEvent

        Notes
        -----
        event contains:
            motion_notify_event: xy=(113, 36)
            xydata=(None, None)
            button=None
            dblclick=False
            inaxes=None
        """

        # self.ax is our main scatter plot axes
        if event.inaxes != self.ax:
            return

        # mouse is not down
        if self.mouseDownEvent is None:
            return

        event1 = self.mouseDownEvent
        event2 = event

        if event1 is None or event2 is None:
            return

        _insideMask = self.inside(event1, event2)
        # print(f'_insideMask: {_insideMask}')

        self.mask |= _insideMask
        xy = np.column_stack([self.x[self.mask], self.y[self.mask]])
        self._highlight.set_offsets(xy)
        self.canvas.draw()

    def setData(self, x, y, plotSpikeNumber : List[int]):
        """Set underlying highlighter data, call this when we replot() scatter
        
        """
        # convert list to np array
        xArray = np.array(x)
        yArray = np.array(y)

        self.mask = np.zeros(xArray.shape, dtype=bool)
        self.x = xArray
        self.y = yArray
        self._plotSpikeNumber = plotSpikeNumber

    def selectSpikeList(self, plotIdxList):
        """
        plotIdxList : List[int]
            List of plot indices to select
        """
        self.mask = np.zeros(self.x.shape, dtype=bool)
        self.mask[plotIdxList] = True

        xy = np.column_stack([self.x[self.mask], self.y[self.mask]])
        self._highlight.set_offsets(xy)
        
        # self._HighlighterReleasedEvent()

        self.canvas.draw()

    # def selectSpikes(self, spikeList):
        
    #     self.mask = np.zeros(self.x.shape, dtype=bool)
        
    #     # the spike numbers we are plotting self._plotSpikeNumber
    #     _selectionIdx = []
    #     for spike in spikeList:
    #         if spike in self._plotSpikeNumber:

    #     self.mask

    #     xy = np.column_stack([self.x[self.mask], self.y[self.mask]])
    #     self._highlight.set_offsets(xy)
        
    #     self._HighlighterReleasedEvent()

    #     self.canvas.draw()

    # def __call__(self, event1, event2):
    def _HighlighterReleasedEvent(self, event1=None, event2=None):
        """RectangleSelector callback when mouse is released

        event1:
            button_press_event: xy=(87.0, 136.99999999999991) xydata=(27.912559411227885, 538.8555851528383) button=1 dblclick=False inaxes=AxesSubplot(0.1,0.1;0.607046x0.607046)
        event2:
            button_release_event: xy=(131.0, 211.99999999999991) xydata=(48.83371692821588, 657.6677439956331) button=1 dblclick=False inaxes=AxesSubplot(0.1,0.1;0.607046x0.607046)
        """

        self.mouseDownEvent = None

        # emit the selected spikes
        selectedSpikes = np.where(self.mask == True)
        selectedSpikes = selectedSpikes[0]  # why does np do this ???

        logger.info(f'selectedSpikes: {selectedSpikes}')

        selectedSpikesList = selectedSpikes.tolist()
        self._parentPlot.selectSpikesFromHighlighter(selectedSpikesList)

        # we now use self._blockSlots
        # # clear the selection user just made, will get 'reselected' in signal/slot
        #self._highlight.set_offsets([np.nan, np.nan])

        return

    def inside(self, event1, event2):
        """Returns a boolean mask of the points inside the
        rectangle defined by event1 and event2.
        """
        # Note: Could use points_inside_poly, as well
        x0, x1 = sorted([event1.xdata, event2.xdata])
        y0, y1 = sorted([event1.ydata, event2.ydata])
        mask = (self.x > x0) & (self.x < x1) & (self.y > y0) & (self.y < y1)
        return mask


def run():
    path = "/Users/cudmore/Sites/SanPy/data/19114001.abf"
    ba = sanpy.bAnalysis(path)
    ba.spikeDetect()
    print(ba)

    import sys

    app = QtWidgets.QApplication([])
    sp = plotScatter(ba=ba)
    sp.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
