from functools import partial
from typing import Optional

import pandas as pd

from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
import matplotlib.pyplot as plt

import seaborn as sns
# sns.set_palette("colorblind")

from PyQt5 import QtGui, QtCore, QtWidgets

from sanpy.kym.kymRoiResults import KymRoiResults

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class simpleTableWidget(QtWidgets.QTableWidget):
    def __init__(self, df : Optional[pd.DataFrame] = None):
        super().__init__(None)
        self._df = df
        if self._df is not None:
            self.setDf(self._df)

    def setDf(self, df : pd.DataFrame):
        self._df = df
        
        self.setRowCount(df.shape[0])
        self.setColumnCount(df.shape[1])
        self.setHorizontalHeaderLabels(df.columns)

        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                item = QtWidgets.QTableWidgetItem(str(df.iloc[row, col]))
                self.setItem(row, col, item)
                 
class SimpleRoiScatter(QtWidgets.QWidget):
    """Plot a scatter plot from peak/diameter detection df.
    """
    def __init__(self, df : pd.DataFrame = None):
        super().__init__(None)
        self._df = df

        # columns in analysis df
        self._columns = KymRoiResults.userAnalysisKeys  # reduces analysis keys, just for the user

        # ignore some bookkeeping columns

        self._plotTypes = ['Scatter', 'Swarm', 'Swarm + Mean', 'Swarm + Mean + STD', 'Swarm + Mean + SEM', 'Histogram', 'Cumulative Histogram']
        
        self._state = {
            'xStat': 'Peak Number',
            'yStat': 'Peak Height',
            'hue': 'ROI Number',
            'plotType': 'Swarm + Mean',
            'makeSquare': False,
        }

        # re-wire right-click (for entire widget)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu)

        self._buildUI()

        # anable/disable combobox(es) based on plot type
        self._updateGuiOnPlotType(self._state['plotType'])

    def _buildUI(self):

        # this is dangerous, collides with self.mplWindow()
        self.fig = mpl.figure.Figure()
        # self.static_canvas = backend_qt5agg.FigureCanvas(self.fig)
        self.static_canvas = backend_qt5agg.FigureCanvasQTAgg(self.fig)
        self.static_canvas.setFocusPolicy(
            QtCore.Qt.ClickFocus
        )  # this is really tricky and annoying
        self.static_canvas.setFocus()
        # self.axs[idx] = self.static_canvas.figure.add_subplot(numRow,1,plotNum)

        self.gs = self.fig.add_gridspec(
            1, 1, left=0.1, right=0.9, bottom=0.1, top=0.9, wspace=0.05, hspace=0.05
        )

        # redraw everything
        self.static_canvas.figure.clear()

        self.axScatter = self.static_canvas.figure.add_subplot(self.gs[0, 0])

        # despine top/right
        self.axScatter.spines["right"].set_visible(False)
        self.axScatter.spines["top"].set_visible(False)

        self.fig.canvas.mpl_connect("key_press_event", self.keyPressEvent)

        self.mplToolbar = mpl.backends.backend_qt5agg.NavigationToolbar2QT(
            self.static_canvas, self.static_canvas
        )

        # put toolbar and static_canvas in a V layout
        # plotWidget = QtWidgets.QWidget()
        vLayoutPlot = QtWidgets.QVBoxLayout(self)
        
        self._topToolbar = self._buildTopToobar()
        vLayoutPlot.addLayout(self._topToolbar)

        vLayoutPlot.addWidget(self.static_canvas)
        vLayoutPlot.addWidget(self.mplToolbar)
        #plotWidget.setLayout(vLayoutPlot)

        #
        # raw and y-stat summary in tabs
        self._tabwidget = QtWidgets.QTabWidget()

        self.rawTableWidget = simpleTableWidget(self._df)
        self._tabwidget.addTab(self.rawTableWidget, "Raw")

        self.yStatSummaryTableWidget = simpleTableWidget()
        self._tabwidget.addTab(self.yStatSummaryTableWidget, "Y-Stat Summary")

        self._tabwidget.setCurrentIndex(0)

        vLayoutPlot.addWidget(self._tabwidget)

        #
        self.static_canvas.draw()

    @property
    def state(self):
        return self._state
    
    def copyTableToClipboard(self):
        _tabIndex = self._tabwidget.currentIndex()
        if _tabIndex == 0:
            logger.info('=== copy raw to clipboard ===')
            print(self._df)
            self._df.to_clipboard(sep="\t", index=False)
            _ret = 'Copied raw table to clipboard'
        elif _tabIndex == 1:
            logger.info('=== copy summary to clipboard ===')
            print(self._dfYStatSummary)
            self._dfYStatSummary.to_clipboard(sep="\t", index=False)
            _ret = 'Copied y-stat-summary table to clipboard'
        else:
            logger.warning(f'did not understand tab: {_tabIndex}')
            _ret = 'Did not copy, please select a table'
        return _ret
    
    def _buildTopToobar(self):
        vBoxLayout = QtWidgets.QVBoxLayout()
        vBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        # row 1
        hBoxLayout = QtWidgets.QHBoxLayout()
        hBoxLayout.setAlignment(QtCore.Qt.AlignLeft)
        vBoxLayout.addLayout(hBoxLayout)

        # plot type
        aName = 'Plot Type'
        aLabel = QtWidgets.QLabel(aName)
        hBoxLayout.addWidget(aLabel)

        self.plotTypeComboBox = QtWidgets.QComboBox()
        self.plotTypeComboBox.addItems(self._plotTypes)
        _index = self._plotTypes.index('Swarm')
        self.plotTypeComboBox.setCurrentIndex(_index)
        self.plotTypeComboBox.currentTextChanged.connect(
            partial(self._on_stat_combobox, aName)
        )
        hBoxLayout.addWidget(self.plotTypeComboBox)

        #
        # hueName = 'Hue'
        # hueLabel = QtWidgets.QLabel(hueName)
        # hBoxLayout.addWidget(hueLabel)

        # _hueList = ['None', 'ROI Number', 'Peak Number']
        # self.hueComboBox = QtWidgets.QComboBox()
        # self.hueComboBox.addItems(_hueList)
        # self.hueComboBox.setCurrentIndex(1)  # default to 'ROI Number'
        # self.hueComboBox.currentTextChanged.connect(
        #     partial(self._on_stat_combobox, hueName)
        # )
        # hBoxLayout.addWidget(self.hueComboBox)

        # second row
        hBoxLayout2 = QtWidgets.QHBoxLayout()
        hBoxLayout2.setAlignment(QtCore.Qt.AlignLeft)
        vBoxLayout.addLayout(hBoxLayout2)

        #
        xName = 'X-Stat'
        xLabel = QtWidgets.QLabel(xName)
        hBoxLayout2.addWidget(xLabel)

        self.xComboBox = QtWidgets.QComboBox()
        self.xComboBox.addItems(self._columns)
        _index = self._columns.index(self.state['xStat'])
        self.xComboBox.setCurrentIndex(_index)
        self.xComboBox.currentTextChanged.connect(
            partial(self._on_stat_combobox, xName)
        )
        hBoxLayout2.addWidget(self.xComboBox)

        #
        yName = 'Y-Stat'
        yLabel = QtWidgets.QLabel(yName)
        hBoxLayout2.addWidget(yLabel)

        self.yComboBox = QtWidgets.QComboBox()
        self.yComboBox.addItems(self._columns)
        _index = self._columns.index(self.state['yStat'])
        self.yComboBox.setCurrentIndex(_index)
        self.yComboBox.currentTextChanged.connect(
            partial(self._on_stat_combobox, yName)
        )
        hBoxLayout2.addWidget(self.yComboBox)

        #
        return vBoxLayout
    
    def _updateGuiOnPlotType(self, plotType):
        """Enable/disable giu on plot type.
        """
        # plot types turn on/off X-Stat
        enableXStat = plotType == 'Scatter'
        self.xComboBox.setEnabled(enableXStat)

    def _on_stat_combobox(self, name : str, value : str):
        logger.info(f'name:{name} value:{value}')
        
        if name == 'Plot Type':
            self.state['plotType'] = value
            self._updateGuiOnPlotType(self._state['plotType'])

        elif name == 'X-Stat':
            self.state['xStat'] = value
        
        elif name == 'Y-Stat':
            self.state['yStat'] = value
        
        # elif name == 'Hue':
        #     if value == 'None':
        #         value = None
        #     self.state['hue'] = value
        
        else:
            logger.warning(f'did not understand "{name}"')

        self.replot()

    def onpick(self, event):
        """
        event : matplotlib.backend_bases.PickEvent
        """
        logger.info(event)
        logger.info(f'  event.artist:{event.artist}')  # matplotlib.collections.PathCollection
        logger.info(f'  event.ind:{event.ind}')
        
        ind = event.ind
        dfRow = self._df.loc[ind]
        print(dfRow)

    def replot(self, df=None):

        if df is not None:
            # logger.info('df is')
            # print(df[self._columns])
            self._df = df

        df = self._df
        xStat = self.state['xStat']
        yStat = self.state['yStat']
        hue = self.state['hue']
        plotType = self.state['plotType']

        # logger.info(f'plotType:{plotType}')

        dfGrouped = self.getGroupedDataframe(yStat)
        self._dfYStatSummary = dfGrouped
        
        self.rawTableWidget.setDf(self._df)
        self.yStatSummaryTableWidget.setDf(dfGrouped)

        # sns.set_palette()
        numRoiNum = len(df['ROI Number'].unique())
        sns.set_palette("colorblind")
        palette = sns.color_palette(n_colors=numRoiNum)

        # try:
        if 1:

            # returns "matplotlib.axes._axes.Axes"
            self.axScatter.cla()
                   
            if plotType == 'Scatter':
                self.axScatter = sns.scatterplot(data=df,
                                                 x=xStat,
                                                 y=yStat,
                                                 hue=hue,
                                                 palette=palette,
                                                 ax=self.axScatter,
                                                 picker=5)  # return matplotlib.axes.Axes

                if self._state['makeSquare']:
                    # logger.info('making scatter plot square')
                    _xLim = self.axScatter.get_xlim()
                    _yLim = self.axScatter.get_ylim()
                    _min = min(_xLim[0], _yLim[0])
                    _max = max(_xLim[1], _yLim[1])

                    # logger.info(f'_min:{_min} _max:{_max}')
                    self.axScatter.set_xlim([_min, _max])
                    self.axScatter.set_ylim([_min, _max])

                    # draw a diagonal line
                    # Using transform=self.axScatter.transAxes, the supplied x and y coordinates are interpreted as axes coordinates instead of data coordinates.
                    self.axScatter.plot([0, 1], [0, 1], '--', transform=self.axScatter.transAxes)
                
            elif plotType in ['Swarm', 'Swarm + Mean', 'Swarm + Mean + STD', 'Swarm + Mean + SEM']:
                # picker does not work for stripplot
                # fernando's favorite
                
                # reduce the brightness of raw data
                if plotType in ['Swarm + Mean', 'Swarm + Mean + STD', 'Swarm + Mean + SEM']:
                    alpha = 0.6
                    # ['ci', 'pi', 'se', 'sd']
                    if plotType == 'Swarm + Mean':
                        errorBar = None
                    elif plotType == 'Swarm + Mean + STD':
                        errorBar = 'sd'
                    elif plotType == 'Swarm + Mean + SEM':
                        errorBar = 'se'
                else:
                    alpha = 1
                    errorBar = None

                self.axScatter = sns.stripplot(data=df,
                                               x='ROI Number',
                                               y=yStat,
                                               hue=hue,
                                               alpha=alpha,
                                               palette=palette,
                                               legend=False,
                                               ax=self.axScatter)
                    
                # if errorBar is not None:
                if plotType in ['Swarm + Mean', 'Swarm + Mean + STD', 'Swarm + Mean + SEM']:
                    # overlay mean +- sem
                    errorbar = errorBar
                    markersize = 30
                    sns.pointplot(data=df, x='ROI Number', y=yStat, hue=hue,
                                errorbar=errorbar,  # can be 'se', 'sem', etc
                                # capsize=capsize,
                                linestyle='none',  # do not connect (with line) between categorical x
                                marker="_",
                                markersize=markersize,
                                # markeredgewidth=3,
                                legend=False,
                                palette=palette,
                                ax=self.axScatter)

            elif plotType == 'Histogram':
                self.axScatter = sns.histplot(data=df,
                                              x=yStat,
                                              hue=hue,
                                                palette=palette,
                                               ax=self.axScatter)

            elif plotType == 'Cumulative Histogram':
                self.axScatter = sns.histplot(data=df, x=yStat, hue=hue,
                                              element="step",
                                              fill=False,
                                              cumulative=True,
                                              stat="density",
                                              common_norm=False,
                                                palette=palette,
                                               ax=self.axScatter)

            else:
                logger.warning(f'did not understand plot type: {plotType}')

            self.static_canvas.draw()

        # except (ValueError) as e:
        #     logger.error(e)

    def keyPressEvent(self, event):
        _handled = False
        isMpl = isinstance(event, mpl.backend_bases.KeyEvent)
        if isMpl:
            text = event.key
            logger.info(f'mpl key: "{text}"')

            doCopy = text in ["ctrl+c", "cmd+c"]
            if doCopy:
                self.copyTableToClipboard()

    def _contextMenu(self, pos):
        logger.info('')

        contextMenu = QtWidgets.QMenu()

        makeSquareAction = QtWidgets.QAction('Make Square')
        makeSquareAction.setCheckable(True)
        makeSquareAction.setChecked(self._state['makeSquare'])
        makeSquareAction.setEnabled(self._state['plotType'] == 'Scatter')
        contextMenu.addAction(makeSquareAction)

        contextMenu.addSeparator()
        contextMenu.addAction('Copy Stats Table ...')
        
        # show menu
        pos = self.mapToGlobal(pos)
        action = contextMenu.exec_(pos)
        if action is None:
            return
        
        _ret = ''
        actionText = action.text()
        if action == makeSquareAction:
            self._state['makeSquare'] =  makeSquareAction.isChecked()
            self.replot()
        
        elif actionText == 'Copy Stats Table ...':
            _ret = self.copyTableToClipboard()

    def getGroupedDataframe(self, statColumn, groupByColumn = 'ROI Number'):
        import numpy as np
        from scipy.stats import variation 
        
        aggList = ["count", "mean", "std", "sem", variation, "median", "min", "max"]

        # aggDf = self._df.groupby(groupByColumn, as_index=False)[statColumn].agg(aggList)
        dfDropNan = self._df.dropna(subset=[statColumn])  # drop rows where statColumn is nan
                
        try:
            aggDf = dfDropNan.groupby(groupByColumn).agg({statColumn : aggList})
        except (TypeError) as e:
            logger.error(f'groupByColumn "{groupByColumn}" failed')
            aggDf = dfDropNan

        aggDf.columns = aggDf.columns.droplevel(0)  # get rid of statColumn multiindex
        aggDf.insert(0, "stat", statColumn)  # add column 0, in place
        aggDf = aggDf.reset_index()  # move groupByColum (e.g. 'ROI Number') from row index label to column
        
        # rename column 'variation' as 'CV'
        aggDf = aggDf.rename(columns={'variation': 'CV'}) 

        # round some columns
        aggList = ["mean", "std", "sem", "CV", "median", "min", "max"]
        for agg in aggList:
            if agg == 'count':
                continue
            # logger.info(f'rounding agg:{agg}')
            aggDf[agg] =round(aggDf[agg], 2)

        return aggDf
    