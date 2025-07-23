import os
import sys
from functools import partial
from itertools import combinations
from typing import Optional, List

import pandas as pd
import numpy as np

from scipy.stats import variation

from matplotlib.backends import backend_qt5agg
import matplotlib as mpl
import matplotlib.pyplot as plt

import seaborn as sns

# sns.set_palette("colorblind")

from statannotations.Annotator import Annotator

from PyQt5 import QtGui, QtCore, QtWidgets

# from colin_traces import ColinTraces
from colin_tree_widget import KymTreeWidget

# from colin_traces import plotCellID
from colin_global import conditionOrder
from colin_simple_figure import KymRoiMainWindow

from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


class simpleTableWidget(QtWidgets.QTableWidget):
    def __init__(self, df: Optional[pd.DataFrame] = None):
        super().__init__(None)
        self._df = df
        if self._df is not None:
            self.setDf(self._df)

    def setDf(self, df: pd.DataFrame):
        self._df = df

        self.setRowCount(df.shape[0])
        self.setColumnCount(df.shape[1])
        self.setHorizontalHeaderLabels(df.columns)

        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                item = QtWidgets.QTableWidgetItem(str(df.iloc[row, col]))
                self.setItem(row, col, item)


def _makeComboBox(
    name: str, items: List[str], defaultItem: Optional[str] = None, callbackFn=None
) -> QtWidgets.QHBoxLayout:
    hBoxLayout = QtWidgets.QHBoxLayout()
    aLabel = QtWidgets.QLabel(name)
    hBoxLayout.addWidget(aLabel)

    aComboBox = QtWidgets.QComboBox()
    hBoxLayout.addWidget(aComboBox)

    aComboBox.addItems(items)

    if defaultItem is not None:
        _index = items.index(defaultItem)
    else:
        # default to first
        _index = 0
    aComboBox.setCurrentIndex(_index)

    if callbackFn is not None:
        aComboBox.currentTextChanged.connect(partial(callbackFn, name))

    return hBoxLayout


def _getNumSpikesDf(df) -> pd.DataFrame:
    dictList = []
    for oneCellID in df['Cell ID'].unique():
        logger.info(f'oneCellStr:{oneCellID}')
        oneDf = df[df['Cell ID'] == oneCellID]

        _oneRegion = oneDf['Region'].iloc[0]

        numSpikesControl = 0
        for oneCond in conditionOrder:
            oneCondDf = oneDf[oneDf['Condition'] == oneCond]
            # print(oneCondDf)
            numSpikes = len(oneCondDf)
            # print(f'numSpikes:{numSpikes}')
            # if numSpikes == 0:
            #     logger.error(f'0 spikes oneCellStr:{oneCellID} cond:{oneCond}')
            #     continue
            if oneCond == 'Control':
                numSpikesControl = numSpikes
                percentChange = 100
            else:
                if numSpikesControl == 0:
                    percentChange = np.nan
                else:
                    percentChange = numSpikes / numSpikesControl * 100

            # if numSpikes == 0:
            #     oneFreq = np.nan
            # else:
            #     from colin_peak_freq import getSimpleFreq
            #     tifPath = oneCondDf['tifPath'].iloc[0]
            #     oneFreq = getSimpleFreq(tifPath, csvPath)

            oneDict = {
                'Cell ID': oneCellID,
                'Region': _oneRegion,
                'Condition': oneCond,
                'Num Spikes': numSpikes,
                'percentChange': percentChange,
            }
            # print(oneDict)
            dictList.append(oneDict)

    dfNumSpikes = pd.DataFrame(dictList)
    print('=== dfNumSpikes:')
    print(dfNumSpikes)

    #
    # run stats on num spikes
    from scipy.stats import mannwhitneyu

    # 1) isan vs ssan in control
    iSanSpikes = dfNumSpikes
    iSanSpikes = iSanSpikes[iSanSpikes['Region'] == 'ISAN']
    iSanControlSpikes = iSanSpikes[iSanSpikes['Condition'] == 'Control']
    iSanIvabSpikes = iSanSpikes[iSanSpikes['Condition'] == 'Ivab']
    #
    sSanSpikes = dfNumSpikes
    sSanSpikes = sSanSpikes[sSanSpikes['Region'] == 'SSAN']
    sSanControlSpikes = sSanSpikes[sSanSpikes['Condition'] == 'Control']
    sSanIvabSpikes = sSanSpikes[sSanSpikes['Condition'] == 'Ivab']

    # compare control and ivan (for each of isan and ssan)
    # ssan
    sample1 = sSanControlSpikes['Num Spikes'].to_list()
    sample2 = sSanIvabSpikes['Num Spikes'].to_list()
    if len(sample1) == 0 or len(sample2) == 0:
        pass
    else:
        print('=== mannwhitneyu comparing num spikes in Control versus Ivab (SSAN)')
        result = mannwhitneyu(sample1, sample2)
        print(result)

    # isan
    sample1 = iSanControlSpikes['Num Spikes'].to_list()
    sample2 = iSanIvabSpikes['Num Spikes'].to_list()
    if len(sample1) == 0 or len(sample2) == 0:
        pass
    else:
        print('=== mannwhitneyu comparing num spikes in Control versus Ivab (ISAN)')
        result = mannwhitneyu(sample1, sample2)
        print(result)

    # compare isan to ssan control spikes
    sample1 = iSanControlSpikes['Num Spikes'].to_list()
    sample2 = sSanControlSpikes['Num Spikes'].to_list()
    logger.warning(f'sample1:{len(sample1)} sample2:{len(sample2)}')
    if len(sample1) == 0 or len(sample2) == 0:
        pass
    else:
        print('=== mannwhitneyu comparing num spikes in control (SSAN vs ISAN)')
        result = mannwhitneyu(sample1, sample2)
        print(result)

    return dfNumSpikes


class ScatterOptions(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scatter Options")
        self.setGeometry(100, 100, 300, 200)

        # Create layout and widgets here
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Add widgets to the layout
        label = QtWidgets.QLabel("Scatter Options")
        layout.addWidget(label)


class ScatterWidget(QtWidgets.QMainWindow):
    """Plot a scatter plot from peak/diameter detection df."""

    # TODO emit signal on user selection
    def __init__(
        self,
        masterDf: pd.DataFrame,
        meanDf: pd.DataFrame,
        xStat: str,
        yStat: str,
        hueList: List[str],
        defaultPlotType: str = None,
        defaultHue: str = None,
        defaultStyle: str = None,
        imgFolder: str = None,  # to load sm2 images
        plotColumns=None,
    ):
        super().__init__(None)

        # logger.error('problems with tif Path')
        # print(df['Path'].iloc[0])
        # sys.exit()

        # always construct from master (one peak per row)
        # self._colinTraces = ColinTraces(masterDf, meanDf)

        self._masterDf = masterDf
        self._meanDf = meanDf

        # columns in analysis df
        if plotColumns is None:
            # all columns
            self._columns = list(
                masterDf.columns
            )  # reduce analysis keys, just for the user
        else:
            # only show these columns
            self._columns = plotColumns

        self._hueList = hueList

        # for sm2 output sparkmaster
        self._imgFolder = imgFolder

        self._plotColumns = plotColumns

        self._plotTypes = [
            'Line Plot',
            'Scatter',
            'Swarm',
            'Swarm + Mean',
            'Swarm + Mean + STD',
            'Swarm + Mean + SEM',
            'Box Plot',
            'Histogram',
            'Cumulative Histogram',
        ]

        self._state = {
            'xStat': xStat,
            'yStat': yStat,
            'hue': hueList[0] if defaultHue is None else defaultHue,
            'style': hueList[0] if defaultStyle is None else defaultHue,
            'plotType': 'Scatter' if defaultPlotType is None else defaultPlotType,
            # 'Swarm + Mean',
            'makeSquare': False,
            'legend': True,
            # 'tables': True,
            'stats': True,
            'plotDf': 'Mean',
            'plotStat': 'Mean',  # either mean(default) or _cv
        }

        # re-wire right-click (for entire widget)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu)

        self._buildUI()

        # enable/disable combobox(es) based on plot type
        self._updateGuiOnPlotType(self._state['plotType'])

        self.replot()

    def getDf(self):
        if self.state['plotDf'] == 'Raw':
            return self._masterDf
        elif self.state['plotDf'] == 'Mean':
            return self._meanDf
        else:
            logger.error(f"did not understand state plotDf {self.state['plotDf']}")

    def _buildUI(self):

        self.status_bar = self.statusBar()
        self.setStatusBar('started ...')

        # this is dangerous, collides with self.mplWindow()
        self.fig = mpl.figure.Figure()
        # self.static_canvas = backend_qt5agg.FigureCanvas(self.fig)
        self.static_canvas = backend_qt5agg.FigureCanvasQTAgg(self.fig)
        self.static_canvas.setFocusPolicy(
            QtCore.Qt.ClickFocus
        )  # this is really tricky and annoying
        self.static_canvas.setFocus()
        # self.axs[idx] = self.static_canvas.figure.add_subplot(numRow,1,plotNum)

        # abb 202505 removed
        # self.gs = self.fig.add_gridspec(
        #     1, 1, left=0.1, right=0.9, bottom=0.1, top=0.9, wspace=0.05, hspace=0.05
        # )

        # redraw everything
        self.static_canvas.figure.clear()

        # self.axScatter = self.static_canvas.figure.add_subplot(self.gs[0, 0])
        self.axScatter = self.static_canvas.figure.add_subplot(1, 1, 1)

        # despine top/right
        self.axScatter.spines["right"].set_visible(False)
        self.axScatter.spines["top"].set_visible(False)
        # self.axScatter = None

        self.fig.canvas.mpl_connect("key_press_event", self.keyPressEvent)

        self.mplToolbar = mpl.backends.backend_qt5agg.NavigationToolbar2QT(
            self.static_canvas, self.static_canvas
        )

        # put toolbar and static_canvas in a V layout
        # plotWidget = QtWidgets.QWidget()
        vLayoutPlot = QtWidgets.QVBoxLayout(self)
        aWidget = QtWidgets.QWidget()
        aWidget.setLayout(vLayoutPlot)
        self.setCentralWidget(aWidget)
        # vLayoutPlot.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

        self._topToolbar = self._buildTopToobar()
        vLayoutPlot.addLayout(self._topToolbar)

        # Create a horizontal splitter for resizable left toolbar and plot
        self._mainSplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self._mainSplitter.setHandleWidth(
            8
        )  # Make the splitter handle wider and more visible
        self._mainSplitter.setStyleSheet(
            """
            QSplitter::handle {
                background-color: #cccccc;
                border: 1px solid #999999;
            }
            QSplitter::handle:hover {
                background-color: #aaaaaa;
            }
        """
        )
        vLayoutPlot.addWidget(self._mainSplitter)

        # Build left toolbar as a widget
        self._leftToolbarWidget = self._buildLeftToobar()
        self._mainSplitter.addWidget(self._leftToolbarWidget)

        # Add the matplotlib canvas to the splitter
        self._mainSplitter.addWidget(self.static_canvas)

        # Set initial splitter sizes (left toolbar gets 300px, rest goes to plot)
        self._mainSplitter.setSizes([300, 800])

        #
        # raw and y-stat summary in tabs
        self._tabwidget = QtWidgets.QTabWidget()

        self.rawTableWidget = simpleTableWidget(self.getDf())
        self._tabwidget.addTab(self.rawTableWidget, "Raw")

        self.yStatSummaryTableWidget = simpleTableWidget()
        self._tabwidget.addTab(self.yStatSummaryTableWidget, "Y-Stat Summary")

        self._tabwidget.setCurrentIndex(0)

        self._tabwidget.setVisible(False)

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
            self.getDf().to_clipboard(sep="\t", index=False)
            _ret = 'Copied raw table to clipboard'
        elif _tabIndex == 1:
            logger.info('=== copy summary to clipboard ===')
            self._dfYStatSummary.to_clipboard(sep="\t", index=False)
            _ret = 'Copied y-stat-summary table to clipboard'
        else:
            logger.warning(f'did not understand tab: {_tabIndex}')
            _ret = 'Did not copy, please select a table'
        return _ret

    def _buildLeftToobar(self) -> QtWidgets.QWidget:
        # Create a widget to hold the layout
        leftToolbarWidget = QtWidgets.QWidget()
        leftToolbarWidget.setMinimumWidth(200)  # Set minimum width for the toolbar
        leftToolbarWidget.setMaximumWidth(600)  # Set maximum width for the toolbar

        vBoxLayout = QtWidgets.QVBoxLayout(leftToolbarWidget)
        # vBoxLayout.setAlignment(QtCore.Qt.AlignTop)
        vBoxLayout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

        # hLayout for ['Regions', 'Conditions']
        regionConditionHBox = QtWidgets.QHBoxLayout()
        vBoxLayout.addLayout(regionConditionHBox)

        #
        # Regions group box
        regionsGroupBox = QtWidgets.QGroupBox('Regions')
        regionConditionHBox.addWidget(regionsGroupBox)

        # one checkbox for each Region
        regionsVLayout = QtWidgets.QVBoxLayout()
        regionsGroupBox.setLayout(regionsVLayout)

        regions = self.getDf()['Region'].unique()
        for regionStr in regions:
            regionCheckBox = QtWidgets.QCheckBox(regionStr)
            regionCheckBox.setChecked(True)
            regionCheckBox.stateChanged.connect(
                partial(self._on_condition_checkbox, 'Region', regionStr)
            )
            regionsVLayout.addWidget(regionCheckBox)

        #
        # conditions group box
        conditionsGroupBox = QtWidgets.QGroupBox('Conditions')
        regionConditionHBox.addWidget(conditionsGroupBox)

        # one checkbox for each Condition
        conditionsVLayout = QtWidgets.QVBoxLayout()
        conditionsGroupBox.setLayout(conditionsVLayout)

        conditions = sorted(self.getDf()['Condition'].unique())
        for conditionStr in conditions:
            # each condition has a hlayout with epoch checkboxes
            conditionHLayout = QtWidgets.QHBoxLayout()
            conditionsVLayout.addLayout(conditionHLayout)

            conditionCheckBox = QtWidgets.QCheckBox(conditionStr)
            conditionCheckBox.setChecked(True)
            conditionCheckBox.stateChanged.connect(
                partial(self._on_condition_checkbox, 'Condition', conditionStr)
            )
            conditionHLayout.addWidget(conditionCheckBox)

            # one checkbox for each Epoch
            theseRows = self.getDf()['Condition'] == conditionStr
            theseEpochs = sorted(self.getDf()[theseRows]['Epoch'].unique())
            for epochInt in theseEpochs:
                epochStr = str(epochInt)
                epochCheckBox = QtWidgets.QCheckBox(epochStr)
                epochCheckBox.setChecked(True)

                # if condition has 1 epoch, disable
                if len(theseEpochs) == 1:
                    epochCheckBox.setEnabled(False)

                epochCheckBox.stateChanged.connect(
                    partial(
                        self._on_condition_checkbox, 'Epoch', conditionStr, epochStr
                    )
                )
                conditionHLayout.addWidget(epochCheckBox)

        #
        # polarity group box
        polarityGroupBox = QtWidgets.QGroupBox('Polarity')
        regionConditionHBox.addWidget(polarityGroupBox)

        # one checkbox for each Condition
        polaritiesVLayout = QtWidgets.QVBoxLayout()
        polarityGroupBox.setLayout(polaritiesVLayout)

        polarities = sorted(self.getDf()['Polarity'].unique())
        for polarityStr in polarities:
            polarityCheckBox = QtWidgets.QCheckBox(polarityStr)
            polarityCheckBox.setChecked(True)
            polarityCheckBox.stateChanged.connect(
                partial(self._on_condition_checkbox, 'Polarity', polarityStr)
            )
            polaritiesVLayout.addWidget(polarityCheckBox)

        #
        # cell id group box
        cellGroupBox = QtWidgets.QGroupBox('Cells')
        vBoxLayout.addWidget(cellGroupBox)

        # one checkbox for each Condition
        cellVLayout = QtWidgets.QVBoxLayout()
        cellGroupBox.setLayout(cellVLayout)

        # All checkbox
        # cellCheckBox = QtWidgets.QCheckBox('All')
        # cellCheckBox.setChecked(True)
        # cellCheckBox.stateChanged.connect(
        #     partial(self._on_cell_checkbox, 'All')
        # )
        # cellVLayout.addWidget(cellCheckBox)

        # one checkbox per cell id
        # populate with mean df
        _df = self._meanDf
        kymTreeWidget = KymTreeWidget(_df)
        kymTreeWidget.toggleAllToggled.connect(self.slot_toggle_all_cell_id)
        kymTreeWidget.cellToggled.connect(self.slot_toggle_cell)
        kymTreeWidget.roiToggled.connect(self.slot_toggle_roi)
        kymTreeWidget.roiSelected.connect(self.slot_roi_selected)
        kymTreeWidget.cellSelected.connect(self.slot_cell_selected)
        kymTreeWidget.plotCellID.connect(self.slot_plot_cell_id)
        cellVLayout.addWidget(kymTreeWidget)

        return leftToolbarWidget

    def slot_toggle_all_cell_id(self, value: bool):
        """Handle toggle all checkbox."""
        self.getDf()['show_cell'] = value
        self.getDf()['show_roi'] = value
        self.replot()

    def slot_toggle_cell(self, cell_id: str, checked: bool):
        """Handle cell checkbox toggle."""
        df = self.getDf()
        theseRows = df['Cell ID'] == cell_id
        df.loc[theseRows, 'show_cell'] = checked
        self.replot()

    def slot_toggle_roi(self, cell_id: str, roi_number: int, checked: bool):
        """Handle ROI checkbox toggle."""
        df = self.getDf()
        theseRows = (df['Cell ID'] == cell_id) & (df['ROI Number'] == roi_number)
        df.loc[theseRows, 'show_roi'] = checked
        self.replot()

    def slot_cell_selected(self, cell_id: str, condition: str):
        logger.info(f'cell_id:"{cell_id}" condition:"{condition}"')

    def slot_plot_cell_id(self, cell_id: str, roi_number: int):
        logger.info(f'cell_id:"{cell_id}" roi_number:{roi_number}')

        # fig, ax = self._colinTraces.plotCellID(cell_id, roiLabelStr=roi_number)

        from colin_pool_plot import new_plotCellID

        fig, ax, _tmpDict = new_plotCellID(
            self._masterDf, self._meanDf, cell_id, roi_number
        )

        if fig is None or ax is None:
            return

        self._mainWindow = MainWindow(fig, ax)
        self._mainWindow.setWindowTitle(f'cell ID:"{cell_id}" roi:{roi_number}')
        self._mainWindow.show()

    def slot_roi_selected(self, cell_id: str, condition: str, roi_number: int):
        # logger.info(f'cellID:"{cell_id}" condition:{condition} roiLabelInt:{roi_number} -->> plotCellID()')
        # logger.info('-->> off')
        logger.info('TODO: select roi peaks in plot !!!')
        pass

    def _buildTopToobar(self) -> QtWidgets.QVBoxLayout:
        vBoxLayout = QtWidgets.QVBoxLayout()
        # vBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        # row 1
        hBoxLayout = QtWidgets.QHBoxLayout()
        hBoxLayout.setAlignment(QtCore.Qt.AlignLeft)
        vBoxLayout.addLayout(hBoxLayout)

        plotTypeComboBox = _makeComboBox(
            name='Plot Type',
            items=self._plotTypes,
            defaultItem=self._state['plotType'],
            callbackFn=self._on_stat_combobox,
        )
        hBoxLayout.addLayout(plotTypeComboBox)

        # plot type
        # aName = 'Plot Type'
        # aLabel = QtWidgets.QLabel(aName)
        # hBoxLayout.addWidget(aLabel)

        # plotTypeComboBox = QtWidgets.QComboBox()
        # plotTypeComboBox.addItems(self._plotTypes)
        # _index = self._plotTypes.index('Scatter')  # default to scatter plot
        # plotTypeComboBox.setCurrentIndex(_index)
        # plotTypeComboBox.currentTextChanged.connect(
        #     partial(self._on_stat_combobox, aName)
        # )
        # hBoxLayout.addWidget(plotTypeComboBox)

        # hue
        _hueList = ['None'] + self._hueList
        hueComboBox = _makeComboBox(
            name='Hue',
            items=_hueList,
            defaultItem=self._state['hue'],
            callbackFn=self._on_stat_combobox,
        )
        hBoxLayout.addLayout(hueComboBox)

        # hueName = 'Hue'
        # hueLabel = QtWidgets.QLabel(hueName)
        # hBoxLayout.addWidget(hueLabel)

        # self.hueComboBox = QtWidgets.QComboBox()
        # _hueList = ['None'] + self._hueList
        # self.hueComboBox.addItems(_hueList)
        # # find index from self._defaultHue
        # if self._state['hue'] in self._hueList:
        #     _index = self._hueList.index(self._state['hue'])
        # else:
        #     _index = 0
        # self.hueComboBox.setCurrentIndex(_index)
        # # self.hueComboBox.setCurrentIndex(1)  # default to 'ROI Number'
        # self.hueComboBox.currentTextChanged.connect(
        #     partial(self._on_stat_combobox, hueName)
        # )
        # hBoxLayout.addWidget(self.hueComboBox)

        # style
        _hueList = ['None'] + self._hueList
        styleCombo = _makeComboBox(
            name='Style',
            items=_hueList,
            callbackFn=self._on_stat_combobox,
        )
        hBoxLayout.addLayout(styleCombo)

        # aName = 'Style'
        # aLabel = QtWidgets.QLabel(aName)
        # hBoxLayout.addWidget(aLabel)

        # self.styleComboBox = QtWidgets.QComboBox()
        # _hueList = ['None'] + self._hueList
        # self.styleComboBox.addItems(_hueList)
        # # find index from self._defaultHue
        # if self._state['style'] in self._hueList:
        #     _index = self._hueList.index(self._state['style'])
        # else:
        #     _index = 0
        # self.styleComboBox.setCurrentIndex(_index)
        # # self.hueComboBox.setCurrentIndex(1)  # default to 'ROI Number'
        # self.styleComboBox.currentTextChanged.connect(
        #     partial(self._on_stat_combobox, aName)
        # )
        # hBoxLayout.addWidget(self.styleComboBox)

        # legend
        legendCheckBox = QtWidgets.QCheckBox('Legend')
        legendCheckBox.setChecked(True)
        legendCheckBox.stateChanged.connect(
            lambda state: self._on_stat_combobox('Legend', state)
        )
        hBoxLayout.addWidget(legendCheckBox)

        # tables
        aCheckbox = QtWidgets.QCheckBox('Tables')
        aCheckbox.setChecked(False)
        aCheckbox.stateChanged.connect(
            lambda state: self._on_stat_combobox('Tables', state)
        )
        hBoxLayout.addWidget(aCheckbox)

        # stats
        aCheckbox = QtWidgets.QCheckBox('Stats')
        aCheckbox.setChecked(True)
        aCheckbox.stateChanged.connect(
            lambda state: self._on_stat_combobox('Stats', state)
        )
        hBoxLayout.addWidget(aCheckbox)

        # plot
        aPushButton = QtWidgets.QPushButton('Replot')
        aPushButton.setCheckable(False)
        aPushButton.clicked.connect(partial(self.replot))
        hBoxLayout.addWidget(aPushButton)

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

        # popup to plot (raw, mean) dataframe
        hBox = _makeComboBox(
            name="Plot Data",
            items=('Raw', 'Mean'),
            defaultItem='Mean',
            callbackFn=self._on_stat_combobox,
        )
        hBoxLayout2.addLayout(hBox)

        # popup to plot mean(default) or CV
        hBox = _makeComboBox(
            name="Plot Stat",
            items=('Mean', 'CV'),
            defaultItem='Mean',
            callbackFn=self._on_stat_combobox,
        )
        hBoxLayout2.addLayout(hBox)

        #
        return vBoxLayout

    def _updateGuiOnPlotType(self, plotType):
        """Enable/disable giu on plot type."""
        # plot types turn on/off X-Stat
        enableXStat = plotType == 'Scatter'
        # self.xComboBox.setEnabled(enableXStat)

    def _on_stat_combobox(self, name: str, value: str):
        """Handle both combobox and checkbox changes"""
        logger.info(f'name:{name} value:{value}')

        if name == 'Plot Type':
            self.state['plotType'] = value
            self._updateGuiOnPlotType(self._state['plotType'])

        elif name == 'X-Stat':
            self.state['xStat'] = value

        elif name == 'Y-Stat':
            self.state['yStat'] = value

        elif name == 'Hue':
            if value == 'None':
                value = None
            self.state['hue'] = value

        elif name == 'Style':
            if value == 'None':
                value = None
            self.state['style'] = value

        elif name == 'Legend':
            self.state['legend'] = value == QtCore.Qt.Checked

        elif name == 'Tables':
            self._tabwidget.setVisible(value == QtCore.Qt.Checked)
            # don't replot
            return

        elif name == 'Stats':
            # statistical tests on/off
            self.state['stats'] = value == QtCore.Qt.Checked

        elif name == 'Plot Data':
            # either master or mead dataframe
            self.state['plotDf'] = value

        elif name == 'Plot Stat':
            # either mean (default) or cv
            self.state['plotStat'] = value

        else:
            logger.warning(f'did not understand "{name}"')

        self.replot()

    def _on_condition_checkbox(
        self,
        name: str,
        conditionStr: str,  # either (Condition, Region)
        epochStr: str = None,
        value=None,  # PyQt Checkbox value
    ):
        logger.info(f'name:{name} conditionStr:{conditionStr} value:{value}')
        if name == 'Condition':
            value = value == QtCore.Qt.Checked
            # logger.info(f'name:{name} name: "{conditionStr}" value: {value}')
            self.getDf().loc[
                self.getDf()['Condition'] == conditionStr, 'show_condition'
            ] = value

            self.replot()

        elif name == 'Region':
            value = value == QtCore.Qt.Checked
            # logger.info(f'name:{name} name: "{conditionStr}" value: {value}')
            self.getDf().loc[
                self.getDf()['Region'] == conditionStr, 'show_region'
            ] = value

            self.replot()

        elif name == 'Polarity':
            value = value == QtCore.Qt.Checked
            # logger.info(f'name:{name} name: "{conditionStr}" value: {value}')
            self.getDf().loc[
                self.getDf()['Polarity'] == conditionStr, 'show_polarity'
            ] = value

            self.replot()

        elif name == 'Epoch':
            value = value == QtCore.Qt.Checked
            # logger.info(f'name:{name} name: "{conditionStr}" value: {value}')
            logger.info(f'  conditionStr:"{conditionStr}" epochStr:"{epochStr}"')
            epochInt = int(epochStr)
            theseRows = (self.getDf()['Condition'] == conditionStr) & (
                self.getDf()['Epoch'] == epochInt
            )
            self.getDf().loc[theseRows, 'show_epoch'] = value

            self.replot()

        else:
            logger.warning(f'did not understand name:"{name}')

    def _on_user_pick_scatterplot(self, event):
        """
        event : matplotlib.backend_bases.PickEvent
        """
        # logger.info(event)
        logger.info(
            f'  event.artist:{event.artist}'
        )  # matplotlib.collections.PathCollection
        logger.info(f'  event.ind:{event.ind}')

        # assuming scatterplot preserves index
        ind = event.ind
        dfRow = self.getDf().loc[ind]
        print(dfRow)

        # todo: open image and overlay spark roi
        # oneIdx = ind[0]  # just the first ind
        # self._sparkMasterShowImg(oneIdx)

    def _on_user_pick_lineplot(self, event):
        logger.info('===')
        logger.info(f'event.ind:{event.ind} event.artist:{event.artist}')

    def _on_user_pick_stripplot(self, event):
        """
        Problem
        =======
        If there is a nan value, like inst freq, our ind=ind+1
        """
        logger.info('===')

        try:
            event.artist.label
        except AttributeError as e:
            logger.warning(f'event.artist.label failed: {e}')
            return

        df = self._dfStripPlot

        xStat = self.state['xStat']
        yStat = self.state['yStat']
        hue = self.state['hue']
        # plotType = self.state['plotType']

        dfNoNan = df[df[yStat].notna()]

        # print(f'  xStat: {xStat} hue: {hue} plotType: {plotType}')

        # print(f'  event.artist.label: "{event.artist.label}"')
        # print(f'  event.artist.animal: "{event.artist.animal}"')
        # print(f'  event.ind: {event.ind}')

        # CRITICAL TO STRIP NAN HERE IN CALLBACK !!!
        df2 = dfNoNan[dfNoNan[hue] == event.artist.label]
        colList = ['Cell ID', 'Region', 'Condition', 'ROI Number', xStat, yStat, hue]
        # print(f'df2 from event.artist.label:"{event.artist.label}" is:')
        # print(df2[colList])

        # abb 20250519 THIS IS TOTALLY WRONG
        # WTF DID I DO !!!!
        # logger.info(f'=== user picked row ind :{event.ind}')
        # print(df2[colList].iloc[event.ind])

        # TODO: fix
        df3 = df2[df2[xStat] == event.artist.animal]  # animal is region (ssan, isan)

        # print(f'df3 from event.artist.animal:"{event.artist.animal}" is:')
        # print(df3[colList])

        # logger.info(f'picked gui event.ind:{event.ind}')
        # try:
        #     print(df3[colList].iloc[event.ind])
        # except (IndexError) as e:
        #     logger.error('!!!!!')
        #     print(f'event.ind:{event.ind}')
        #     print(df3[colList])

        # dfClicked = df3[colList].iloc[event.ind]
        dfClicked = df3.iloc[event.ind]
        print('user clicked -->>')
        print(dfClicked[colList])
        # print(dfClicked.columns)

        # update status bar
        cellID = dfClicked['Cell ID'].iloc[0]
        condition = dfClicked['Condition'].iloc[0]
        roiLabelStr = dfClicked['ROI Number'].iloc[0]
        _str = f"Cell ID:'{cellID}' Condition:{condition} ROI Number: {roiLabelStr}"
        self.setStatusBar(_str)

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        isShift = modifiers == QtCore.Qt.ShiftModifier

        # show raw analysis (first peak, user click can yield multiple)
        if isShift:
            clickedCellID = dfClicked['Cell ID'].iloc[0]
            roiLabelStr = dfClicked['ROI Number'].iloc[0]
            logger.info(
                f'-->> plotting cell id:"{clickedCellID}" roiLabelStr:{roiLabelStr}'
            )

            # fig, ax = self._colinTraces.plotCellID(clickedCellID, roiLabelStr=roiLabelStr)
            from colin_pool_plot import new_plotCellID

            fig, ax = new_plotCellID(
                self._masterDf, self._meanDf, clickedCellID, roiLabelStr
            )

            if fig is None or ax is None:
                return

            self._mainWindow = MainWindow(fig, ax)
            self._mainWindow.setWindowTitle(
                f'cell ID:"{clickedCellID}" roi:{roiLabelStr}'
            )
            self._mainWindow.show()

    def _old_sparkMasterShowImg(self, ind):
        """Open image from spark master"""
        if self._imgFolder is None:
            logger.warning('imgFolder is None')
            return

        logger.warning(f'ind:{ind} type:{type(ind)}')

        # assuming sm2 saved file has these !!!!
        # get l,t,r,b
        minRow = self._df.at[ind, 'bounding box min row (pixels)']
        maxRow = self._df.at[ind, 'bounding box max row (pixels)']
        minCol = self._df.at[ind, 'bounding box min column (pixels)']
        maxCol = self._df.at[ind, 'bounding box max column (pixels)']
        # like: minRow:203 maxRow:220 minCol:0 maxCol:15
        logger.info(f'minRow:{minRow} maxRow:{maxRow} minCol:{minCol} maxCol:{maxCol}')

        import matplotlib.patches as patches

        # _x = minCol
        # _y = minRow
        # _width = maxCol - minCol
        # _height = maxRow - minRow

        _x = minRow
        _y = minCol
        _width = maxRow - minRow
        _height = maxCol - minCol

        _rect = patches.Rectangle(
            (_x, _y), _width, _height, linewidth=1, edgecolor='r', facecolor='none'
        )
        logger.info(f'_rect is:{_rect}')

        imgFile = self._df.at[ind, 'File Name']
        # File Name is analysis .csv, convert to original
        logger.warning('assuming raw data is png (usually tif)')
        imgFile = os.path.splitext(imgFile)[0] + '.png'

        imgPath = os.path.join(self._imgFolder, imgFile)
        logger.info(f'opening image: {imgPath}')

        logger.warning(
            'defaulting to matplotlib imread -->> no good!'
        )  # import tifffile
        # imgData = tifffile.imread(imgPath)
        imgData = plt.imread(imgPath)
        logger.info(f'lodaded imgData: {imgData.shape} {imgData.dtype}')
        # convert float32 to int8
        imgData -= np.min(imgData)
        imgData = imgData / np.max(imgData) * 255
        imgData = imgData.astype(np.uint8)
        logger.info(f'now imgData: {imgData.shape} {imgData.dtype}')

        fig, ax = plt.subplots(1)

        _plot = ax.imshow(imgData)  # AxesImage
        # todo: add path to title
        # _plot.setTitle(imgPath)

        ax.add_patch(_rect)

        plt.show()

    def linePlot(self, df, yStat, hue):
        logger.info(f'=== yStat:{yStat} hue:{hue}')

        legend = self.state['legend']
        logger.warning(f'forcing xStat to "Condition"')
        xStat = 'Condition'
        hue_order = conditionOrder
        try:
            df[xStat] = pd.Categorical(df[xStat], categories=hue_order, ordered=True)
        except KeyError as e:
            logger.error(f'KeyError xStat:{xStat} avail col:{df.columns}')
        myHue = 'Cell ID'  # one line per cell across (C, i, t)

        if 1:
            self.axScatter = sns.lineplot(
                data=df,
                x="Condition",  # want order ['c', 'i', 't']
                y=yStat,
                hue=myHue,  # one line per cell (x is control, ivab, thaps)
                # style='Region',
                style='ROI Number',
                #  hue_order=hue_order,
                markers=True,
                legend=legend,
                # err_style="bars",  # for mean df we have _std and _sem columns
                # errorbar=("se", 1),
                errorbar=None,
                ax=self.axScatter,
            )

            # dfPlot = df.groupby(['Cell ID', 'ROI Number'])

            _lines = self.axScatter.get_lines()
            print('_lines')
            print(_lines)
            # Enable picking on each line
            for line in self.axScatter.lines:
                line.set_picker(5)  # Enable picking
            self.fig.canvas.mpl_connect("pick_event", self._on_user_pick_lineplot)
            # self.axScatter.figure.canvas.mpl_connect("pick_event", self._on_user_pick_lineplot)

        # plot 2x plots for region (SSAN, ISAN)
        if 0:
            # relPlot return "FacetGrid" ???
            # self.axScatter = sns.relplot(
            _ax = sns.relplot(
                data=df,
                x="Condition",
                y=yStat,
                col="Region",  # 2x plots across (SSAN, ISAN)
                hue=myHue,
                # style="event",
                kind="line",
                # ax=self.axScatter,  # not available in relplot
            )
            logger.info(f'_ax:{_ax}')
            plt.show()

    def replot(self):
        """Replot the scatter plot"""

        df = self.getDf()
        # reduce based on show_condition and show_cell
        df = df[df['show_region']]  # include if true
        df = df[df['show_condition']]  # include if true
        df = df[df['show_cell']]  # include if true
        df = df[df['show_roi']]  # include if true
        df = df[df['show_polarity']]  # include if true
        df = df[df['show_epoch']]  # include if true

        # logger.info(f'plotting df with rows:{len(df)}')
        # print(df)

        # store df for striplot callback _on_user_pick_striplot
        self._dfStripPlot = df

        xStat = self.state['xStat']
        yStat = self.state['yStat']
        if self.state['plotStat'] == 'CV':
            yStat = f'{yStat}_cv'
        hue = None if self.state['hue'] == 'None' else self.state['hue']
        style = None if self.state['style'] == 'None' else self.state['style']
        plotType = self.state['plotType']
        legend = self.state['legend']

        uniqueHue = [] if hue is None else df[hue].unique()
        numHue = len(uniqueHue)

        if hue in ['Condition', 'Region', 'Condition Epoch']:
            hue_order = sorted(df[hue].unique())
        else:
            hue_order = None

        # if hue == 'Condition':
        #     # hue_order = conditionOrder
        #     hue_order = sorted(df[hue].unique())
        # elif hue == 'Region':
        #     # hue_order = regionOrder
        #     hue_order = sorted(df[hue].unique())
        # elif hue == 'Condition Epoch':
        #     hue_order = sorted(df[hue].unique())
        # else:
        #     hue_order = None

        if hue_order is not None and len(hue_order) == 0:
            hue_order = None

        logger.info(f'hue:"{hue}" hue_order:"{hue_order}"')

        # dodge = False if numHue<=1 else 0.5
        dodge = True if numHue <= 1 else 0.5

        logger.info(f'numHue:{numHue} dodge:{dodge}')

        # print stats to cli
        # from colin_summary import genStats
        # logger.info(f'=== generating stats for "{yStat}"')
        # genStats(df, yStat)

        # broken
        logger.warning('turned off getGroupedDataframe')
        if 0:
            dfGrouped = self.getGroupedDataframe(yStat, groupByColumn=hue)
            self._dfYStatSummary = dfGrouped

            if self.rawTableWidget is not None:
                self.rawTableWidget.setDf(self.getDf())
                self.yStatSummaryTableWidget.setDf(dfGrouped)

        # sns.set_palette()
        # numRoiNum = len(df['ROI Number'].unique())
        logger.warning('202505 turned off palette')
        # numRoiNum = len(df)
        # sns.set_palette("colorblind")
        # palette = sns.color_palette(n_colors=numRoiNum)

        # try:
        if 1:

            # returns "matplotlib.axes._axes.Axes"
            if self.axScatter is not None:
                self.axScatter.cla()

            if len(df) == 0:
                logger.warning('nothing to plot -->> return')
                return

            if plotType == 'Line Plot':
                self.linePlot(df, yStat, hue)

            elif plotType == 'Scatter':
                self.axScatter = sns.scatterplot(
                    data=df,
                    x=xStat,
                    y=yStat,
                    hue=hue,
                    #  palette=palette,
                    ax=self.axScatter,
                    legend=legend,  # TODO ad QCheckbox for this
                    picker=5,
                )  # return matplotlib.axes.Axes

                # abb 202505 removed
                self.axScatter.figure.canvas.mpl_connect(
                    "pick_event", self._on_user_pick_scatterplot
                )

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
                    self.axScatter.plot(
                        [0, 1], [0, 1], '--', transform=self.axScatter.transAxes
                    )

            elif plotType in ['Box Plot']:
                self.axScatter = sns.boxplot(
                    data=df,
                    x=xStat,
                    y=yStat,
                    hue=hue,
                    legend=legend,
                    ax=self.axScatter,
                    dodge=dodge,  # separate the points by hue
                    hue_order=hue_order,
                )

            elif plotType in [
                'Swarm',
                'Swarm + Mean',
                'Swarm + Mean + STD',
                'Swarm + Mean + SEM',
            ]:
                # 20250515 colin, got it working
                # picker does not work for stripplot
                # fernando's favorite

                # reduce the brightness of raw data
                if plotType in [
                    'Swarm + Mean',
                    'Swarm + Mean + STD',
                    'Swarm + Mean + SEM',
                ]:
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

                logger.info(f'=== making stripplot xStat:"{xStat}" hue:"{hue}"')
                # logger.info(f'plotDict hue_order is:{hue_order}')

                # 20250520 hue_order has to be the same length as unique() hue
                # hue_order = ['Control', 'Ivab']

                plotDict = {
                    'data': df,
                    'x': xStat,
                    'y': yStat,
                    'hue': hue,
                    # 'style': style,  # only used in scatterplot
                    'alpha': alpha,
                    # 'palette': None,
                    'legend': legend,
                    # 'ax': self.axScatter,
                    'picker': 5,
                    'dodge': dodge,  # separate the points by hue
                    # 'hue_order': hue_order,  # hue_order is tripping up our complex code for picking with groups and splits !!!!
                }
                if hue_order is not None:
                    plotDict['hue_order'] = hue_order

                # 20250515, switched to swarmplot
                # self.axScatter = sns.stripplot(data=df,
                self.axScatter = sns.swarmplot(ax=self.axScatter, **plotDict)

                _mplFigure = self.axScatter.figure
                # logger.info(f'_mplFigure:{_mplFigure}')

                # see:
                # https://stackoverflow.com/questions/66201678/oclick-with-seaborn-stripplot

                if hue is None:
                    logger.warning('no picking with hue None')
                else:
                    # TODO: refactor to handle simple case, group_len = 1
                    # hue_order is tripping up our complex code for picking with groups and splits !!!!

                    logger.warning(f'need groups using hue order instead ??? hue:{hue}')
                    groups = df[hue].unique()
                    groups = sorted(groups)  # fake hue order based on sorting
                    # groups = hue_order
                    splits = df[xStat].unique()
                    # <Axes.ArtistList of 15 collections>
                    # print(self.axScatter.collections)
                    group_len = len(groups)
                    # print(f'groups is len:{group_len} {groups}')
                    # print(f'splits is:{splits}')
                    for idx, artist in enumerate(self.axScatter.collections):
                        # logger.info(f'idx:{idx} artist:{artist}')
                        # matplotlib.collections.PathCollection
                        artist.animal = splits[
                            idx // group_len
                        ]  # floor division 5//2 = 2
                        artist.label = groups[idx % group_len]
                        # print(f'{idx}')
                        # print(f'  artist.animal: "{artist.animal}"')
                        # print(f'  artist.label: "{artist.label}"')

                    self.fig.canvas.mpl_connect(
                        "pick_event", self._on_user_pick_stripplot
                    )

                # add stats
                if self.state['stats']:
                    # # between all hue within each x (cell)
                    if hue is None or (xStat == hue):
                        logger.warning(
                            'no pairwise comparison if no hue -->> default to pairwise x-stat'
                        )
                        # pairwise between x-stat (cell id)
                        _xUnique = df[xStat].unique()
                        pairs = list(combinations(_xUnique, 2))
                    else:
                        pairs = []
                        for _xStat in df[xStat].unique():
                            # logger.info(f'adding pair for _xStat: {_xStat}')
                            onePair = [
                                [(_xStat, a), (_xStat, b)]
                                for a, b in combinations(uniqueHue, 2)
                            ]
                            # logger.info(f'onePair is len:{len(onePair)}')
                            # logger.info(f'  {onePair}')
                            # append items in onePair to pairs
                            pairs.extend(onePair)

                    # print(f'=== pairs is {type(pairs)} {len(pairs)}:')
                    # print(pairs)
                    # for idx, pair in enumerate(pairs):
                    #     print(f'  {idx}: {pair}')

                    try:

                        logger.info(
                            f'constructing stats Annotator Mann-Whitney NO CORRECTION'
                        )
                        annotator = Annotator(
                            pairs=pairs, ax=self.axScatter, **plotDict
                        )
                        # logger.info('  annotator.configure')
                        annotator.configure(
                            test='Mann-Whitney',
                            text_format='star',
                            # loc='outside',
                            verbose=False,
                        )
                        # logger.info('  annotator.apply_and_annotate')
                        annotator.apply_and_annotate()
                    except ValueError as e:
                        logger.error(f'annotator failed: {e}')
                    # 20250708
                    except TypeError as e:
                        logger.error(f'annotator failed: {e}')
                        logger.error(f'  pairs:{pairs}')
                        logger.error(f'  hue:{hue}')

                # overlay mean +- std or sem
                # no overlay if hue is None
                # if hue is not None and \
                #     plotType in ['Swarm + Mean', 'Swarm + Mean + STD', 'Swarm + Mean + SEM']:
                if plotType in [
                    'Swarm + Mean',
                    'Swarm + Mean + STD',
                    'Swarm + Mean + SEM',
                ]:

                    errorbar = errorBar
                    markersize = 30
                    sns.pointplot(
                        data=df,
                        x=xStat,
                        y=yStat,
                        # ???
                        #   hue= xStat if hue is None else hue,
                        hue=hue,
                        errorbar=errorbar,  # can be 'se', 'sem', etc
                        # capsize=capsize,
                        linestyle='none',  # do not connect (with line) between categorical x
                        marker="_",
                        markersize=markersize,
                        # markeredgewidth=3,
                        legend=False,
                        # palette=palette,
                        # dodge=0.5,  # separate the points by hue
                        # dodge=None if len(uniqueHue)==1 else 0.5,  # separate the points by hue
                        dodge=dodge,
                        hue_order=hue_order,
                        ax=self.axScatter,
                    )

            elif plotType == 'Histogram':
                self.axScatter = sns.histplot(
                    data=df,
                    x=yStat,
                    hue=hue,
                    # palette=palette,
                    legend=legend,
                    ax=self.axScatter,
                )

            elif plotType == 'Cumulative Histogram':
                self.axScatter = sns.histplot(
                    data=df,
                    x=yStat,
                    hue=hue,
                    element="step",
                    fill=False,
                    cumulative=True,
                    stat="density",
                    common_norm=False,
                    # palette=palette,
                    legend=legend,
                    ax=self.axScatter,
                )

            else:
                logger.warning(f'did not understand plot type: {plotType}')

            self.static_canvas.draw()

        # except (ValueError) as e:
        #     logger.error(e)
        plt.tight_layout()

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

        # Add splitter control options
        contextMenu.addSeparator()
        resetSplitterAction = QtWidgets.QAction('Reset Toolbar Width')
        contextMenu.addAction(resetSplitterAction)

        # contextMenu.addSeparator()
        # contextMenu.addAction('Show Analysis Folder')

        # show menu
        pos = self.mapToGlobal(pos)
        action = contextMenu.exec_(pos)
        if action is None:
            return

        _ret = ''
        actionText = action.text()
        if action == makeSquareAction:
            self._state['makeSquare'] = makeSquareAction.isChecked()
            self.replot()

        elif actionText == 'Copy Stats Table ...':
            _ret = self.copyTableToClipboard()

        elif actionText == 'Reset Toolbar Width':
            self.resetSplitterSizes()

    def setStatusBar(self, msg: str, msecs: int = 0):
        """Set the text of the status bar.

        Defaults to 4 seconds.
        """
        # if msecs is None:
        #     msecs=4000
        self.status_bar.showMessage(msg, msecs=msecs)

    def getGroupedDataframe(self, statColumn, groupByColumn):

        logger.info(f'groupByColumn:{groupByColumn}')

        aggList = ["count", "mean", "std", "sem", variation, "median", "min", "max"]

        # if len(self._df)>0:
        #     # get first row value
        #     detectedTrace = self._df['Detected Trace'].iloc[0]
        # else:
        #     detectedTrace = 'N/A'

        # aggDf = self._df.groupby(groupByColumn, as_index=False)[statColumn].agg(aggList)
        dfDropNan = self.getDf().dropna(
            subset=[statColumn]
        )  # drop rows where statColumn is nan

        try:
            aggDf = dfDropNan.groupby(groupByColumn).agg({statColumn: aggList})
        except TypeError as e:
            logger.error(f'groupByColumn "{groupByColumn}" failed e:{e}')
            aggDf = dfDropNan

        try:
            aggDf.columns = aggDf.columns.droplevel(
                0
            )  # get rid of statColumn multiindex
        except ValueError as e:
            logger.error(e)
        aggDf.insert(0, 'Stat', statColumn)  # add column 0, in place
        aggDf = (
            aggDf.reset_index()
        )  # move groupByColum (e.g. 'ROI Number') from row index label to column

        # rename column 'variation' as 'CV'
        aggDf = aggDf.rename(columns={'variation': 'CV'})

        # round some columns
        aggList = ["mean", "std", "sem", "CV", "median", "min", "max"]
        for agg in aggList:
            if agg == 'count':
                continue
            # logger.info(f'rounding agg:{agg}')
            try:
                aggDf[agg] = round(aggDf[agg], 2)
            except KeyError as e:
                logger.warning(
                    f'did not find agg column:{agg} possible keys are {aggDf.columns}'
                )
        return aggDf

    def setSplitterSizes(self, leftWidth: int, rightWidth: int = None):
        """Set the splitter sizes programmatically.

        Args:
            leftWidth: Width for the left toolbar in pixels
            rightWidth: Width for the right plot area in pixels (optional)
        """
        if hasattr(self, '_mainSplitter'):
            if rightWidth is None:
                # Calculate right width based on current window size
                currentSizes = self._mainSplitter.sizes()
                totalWidth = sum(currentSizes)
                rightWidth = totalWidth - leftWidth
            self._mainSplitter.setSizes([leftWidth, rightWidth])

    def getSplitterSizes(self):
        """Get current splitter sizes."""
        if hasattr(self, '_mainSplitter'):
            return self._mainSplitter.sizes()
        return [300, 800]  # Default fallback

    def resetSplitterSizes(self):
        """Reset splitter sizes to default."""
        self.setSplitterSizes(300, 800)

    def saveSplitterSizes(self):
        """Save current splitter sizes to settings."""
        if hasattr(self, '_mainSplitter'):
            sizes = self._mainSplitter.sizes()
            # You can save this to a settings file or registry
            # For now, just store in instance variable
            self._savedSplitterSizes = sizes
            logger.info(f'Saved splitter sizes: {sizes}')

    def restoreSplitterSizes(self):
        """Restore saved splitter sizes."""
        if hasattr(self, '_savedSplitterSizes'):
            self._mainSplitter.setSizes(self._savedSplitterSizes)
            logger.info(f'Restored splitter sizes: {self._savedSplitterSizes}')

    def closeEvent(self, event):
        """Override closeEvent to save splitter sizes before closing."""
        self.saveSplitterSizes()
        super().closeEvent(event)


def run():
    # this was my analysis with 1 roi per kym
    # savePath = '/Users/cudmore/colin_peak_summary_20250517.csv'

    # this is new colin analysis with multiple roi per kym
    # savePath = '/Users/cudmore/colin_peak_summary_20250521.csv'
    # savePath = '/Users/cudmore/colin_peak_summary_20250527.csv'

    # load csv analysis files as pd DataFrame
    from colin_global import loadMasterDfFile, loadMeanDfFile, getMeanDfPath

    masterDf = loadMasterDfFile()
    meanDf = loadMeanDfFile()

    # print(meanDf.columns)
    # meanSavePath = '/Users/cudmore/colin_peak_mean_20250521.csv'
    # meanDf = pd.read_csv(meanSavePath)

    hueList = [
        'File Number',
        'Cell ID',
        #    'Cell ID (plot)',  # removed 20250521
        #    'Tif File',
        'Condition',
        'Epoch',
        'Condition Epoch',
        'Region',
        'Date',
        'ROI Number',
        'Polarity',
    ]

    # limit what we show user
    plotColumns = [
        'Cell ID',
        # 'Cell ID (plot)',  # removed 20250521
        'File Number',
        'Tif File',
        'Condition',
        'Region',
        'Date',
        'ROI Number',
        'Polarity',
        # 'Onset (s)',
        # 'Decay (s)',
        'Peak Inst Interval (s)',
        'Peak Inst Freq (Hz)',
        'Peak Height',
        'FW (ms)',
        'HW (ms)',
        'Rise Time (ms)',
        'Decay Time (ms)',
        'Area Under Peak',
        'Area Under Peak (Sum)',
        'Number of Spikes',
        # 'Spike Frequency (Hz)',
        'fit_tau',
        'fit_tau1',
    ]

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    # app.setStyleSheet("QWidget { font-size: 12pt; }")
    # app.setWindowIcon(QtGui.QIcon('sanpy.png'))
    app.setFont(QtGui.QFont("Arial", 10))
    # app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)

    myWin = ScatterWidget(
        masterDf,
        meanDf,
        xStat='Region',
        yStat='Peak Inst Freq (Hz)',
        # defaultPlotType='Line Plot',
        defaultPlotType='Swarm + Mean + SEM',
        hueList=hueList,
        defaultHue='Condition',
        imgFolder=None,
        plotColumns=plotColumns,
    )

    myWin.setWindowTitle(getMeanDfPath())

    # plot all control traces for ssan and isan
    # myWin._colinTraces.plotOneCond('Control', 'SSAN')
    # myWin._colinTraces.plotOneCond('Control', 'ISAN')
    # plt.show()

    myWin.show()

    # options = ScatterOptions()
    # options.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
