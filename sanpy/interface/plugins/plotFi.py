import time
from typing import Union, Dict, List, Tuple, Optional, Optional
from functools import partial

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns

from PyQt5 import QtCore, QtWidgets, QtGui

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

import sanpy
from sanpy import bDetection
from sanpy import bAnalysis
from sanpy.interface import myTableView_tmp  # name conflict with interface.myTableView
from sanpy.interface.plugins import sanpyPlugin
from sanpy.interface.plugins import (
    ResponseType,
)  # to toggle response to set sweeps, etc
from sanpy.interface.plugins import myStatListWidget


def getStatFi(
    dfMaster: pd.DataFrame,
    stat: str,
    epochNumber: int = 2,
    intervalStat: bool = False,
    filename: str = "",
) -> pd.DataFrame:
    """Given a bAnalysis stat, derive a number of stats
    for each sweep

    Sweeps correspond to different current injection amplitudes.

    Parameters
    ----------
    dfMaster : DataFrame
    stat : str
    epochNumber : int
    epochNumber : bool
        If true then skip first spike.
        Used for stat like spike frequency (Hz) or ISI (ms)
    filename : str
        Append filename column

    Notes
    -----
    Rows in the table are sweeps, if there are no spikes in a sweep it will not be included
    """

    _startSec = time.time()

    # reduce to only spikes for given epochNumber
    dfEpoch = dfMaster[dfMaster["epoch"] == epochNumber]

    # epochLevels is a list of current injection amplitudes
    epochLevels = dfEpoch["epochLevel"].unique()
    epochLevels = np.round(epochLevels, 3)

    # we also want 1st, 2nd, 3rd and nth values
    # don't use agg variable `first` or `last`` (they skip nan)
    #   `second`` is not available
    agg_func_math = {stat: ["count", "mean", "median", "min", "max", "std", "sem"]}
    as_index = True  # if True then 'sweep' number becomes the row index
    dfSweepsSummary = (
        dfEpoch.groupby(["sweep"], as_index=as_index).agg(agg_func_math).round(2)
    )

    # flatten
    dfSweepsSummary.columns = [
        "_".join(col).rstrip("_") for col in dfSweepsSummary.columns.values
    ]

    # insert as first column, after 'sweeps'
    dfSweepsSummary.insert(0, "epochLevel", epochLevels)
    # dfSweepsSummary['epochLevel'] = epochLevels

    # get the first, second and last values
    # if we are doing interval statistics like 'inter spike interval'
    # then always ignore the `first` event in the epoch (e.g. no interval for first spike)

    if intervalStat:
        firstSpike = 1
    else:
        firstSpike = 0

    _first = dfEpoch.groupby(["sweep"], as_index=True)[stat].nth(firstSpike)
    dfSweepsSummary.at[_first.index, stat + "_first"] = _first.values
    # print('_first.index', _first.index)

    _second = dfEpoch.groupby(["sweep"], as_index=True)[stat].nth(firstSpike + 1)
    dfSweepsSummary.at[_second.index, stat + "_second"] = _second.values
    # print('_second.index', _second.index)

    # _third = dfEpoch.groupby(['sweep'], as_index=True)[stat].nth(2)
    # dfSweepsSummary.at[_second.index, stat + '_third'] = _third.values

    _last = dfEpoch.groupby(["sweep"], as_index=True)[stat].nth(-1)
    dfSweepsSummary.at[_last.index, stat + "_last"] = _last.values
    # print('_last.index', _last.index)

    # 1st / 2nd and 1s / last
    dfSweepsSummary[stat + "_1_2"] = (
        dfSweepsSummary[stat + "_first"] / dfSweepsSummary[stat + "_second"]
    )
    dfSweepsSummary[stat + "_1_n"] = (
        dfSweepsSummary[stat + "_first"] / dfSweepsSummary[stat + "_last"]
    )

    # coefficient of variation.
    # Always calculate but only meaningful for interval stats?
    dfSweepsSummary[stat + "_cv"] = (
        dfSweepsSummary[stat + "_std"] / dfSweepsSummary[stat + "_mean"]
    )

    dfSweepsSummary["filename"] = filename

    # move index column 'sweep' into a column
    dfSweepsSummary = dfSweepsSummary.reset_index()

    _stopSec = time.time()
    # print(f'Took {round(_stopSec-_startSec,3)} seconds')

    return dfSweepsSummary


class plotFi(sanpyPlugin):
    myHumanName = "Plot FI"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.toggleResponseOptions(ResponseType.setSweep, False)  # we plot all sweeps
        self.toggleResponseOptions(ResponseType.setAxis, False)

        # inherited property
        self._epochNumber = 2

        self.setDefaultPlot()

        self.df_fi = None
        self._buildUI()

        self._refreshPlotOptionsLayout()

        self._selectInTable("Spike Frequency (Hz)")

        self.replot()

    def setDefaultPlot(self):
        """Default plot dict"""

        self._plotDict = {
            "Raw": True,
            "Error": "sem",  # in [None, 'std', 'sem']
            "Legend": False,
            # keys correspond to columns returned by getStatFI()
            "overlays": {
                "Mean": True,
                "First": False,
                "Last": False,
                "CV": False,
                "Count": False,
                "1_2": False,  # first spike / second spike
                "1_n": False,  # first spike / last spike
            },
        }

    def on_error_combo_box(self, item: str):
        if item == "None":
            item = None
        self._plotDict["Error"] = item
        self.replot()

    def _selectInTable(self, findStatKey: str):
        # this is a CLUDGE !!! FIX IT
        # select in table
        _statList = self._yStatListWidget.statList
        # find 'Spike Frequency (Hz)'
        foundKeyIdx = None
        for keyIdx, k in enumerate(_statList.keys()):
            if k == findStatKey:
                foundKeyIdx = keyIdx
        if foundKeyIdx is not None:
            self._yStatListWidget.myTableWidget.selectRow(foundKeyIdx)

    def on_button_click(self, name: str):
        """
        Parameters
        ----------
        name : str
            Name of the buton clicked
        """
        logger.info(name)
        if name == "Inst Freq":
            self.setDefaultPlot()  # reset _plotDict to defaults
            # set based on button
            self._plotDict["Raw"] = True
            self._plotDict["Error"] = "sem"
            self._plotDict["overlays"]["Mean"] = True

            self._selectInTable("Spike Frequency (Hz)")

        elif name == "Spike Count":
            self.setDefaultPlot()  # reset _plotDict to defaults
            # set based on button
            self._plotDict["Raw"] = False
            self._plotDict["Error"] = None
            self._plotDict["Legend"] = True
            self._plotDict["overlays"]["Count"] = True
        else:
            logger.warning(f'Did not understand "{name}')
            return

        # refresh interface
        self._refreshPlotOptionsLayout()

        # replot
        self.replot()

    def on_check_click(self, state: int, name: str):
        isChecked = state > 0

        logger.info(f"{name} is checked {isChecked}")

        _doReplot = False

        if name == "Results Table":
            self._fiTableView.setVisible(isChecked)
        elif name == "Plot Toolbar":
            self._mplToolbar.setVisible(isChecked)
        elif name in self._plotDict.keys():
            # top level like [Raw, Legend, Error]
            self._plotDict[name] = isChecked
            _doReplot = True
        elif name in self._plotDict["overlays"].keys():
            self._plotDict["overlays"][name] = isChecked
            _doReplot = True
        else:
            logger.warning(f'Did not understand checkbox "{name}"')
            return

        if _doReplot:
            self.replot()

    def _buildTopToolbar(self):
        _topToolbar = QtWidgets.QHBoxLayout()

        _defualtButtons = ["Inst Freq", "Spike Count"]

        for buttonName in _defualtButtons:
            _aButton = QtWidgets.QPushButton(buttonName)
            _aButton.clicked.connect(partial(self.on_button_click, buttonName))
            _topToolbar.addWidget(_aButton, alignment=QtCore.Qt.AlignLeft)

        # toggle the fi stat table
        name = "Results Table"
        _aCheckbox = QtWidgets.QCheckBox(name)
        _aCheckbox.setChecked(False)
        _aCheckbox.stateChanged.connect(
            lambda state, name=name: self.on_check_click(state, name)
        )
        _topToolbar.addWidget(_aCheckbox, alignment=QtCore.Qt.AlignLeft)

        # toggle self._mplToolbar
        name = "Plot Toolbar"
        _aCheckbox = QtWidgets.QCheckBox(name)
        _aCheckbox.setChecked(False)
        _aCheckbox.stateChanged.connect(
            lambda state, name=name: self.on_check_click(state, name)
        )
        _topToolbar.addWidget(_aCheckbox, alignment=QtCore.Qt.AlignLeft)

        _topToolbar.addStretch()

        return _topToolbar

    def _refreshPlotOptionsLayout(self):
        """Refresh all buttons in _overlayCheckboxes with self._plotDict['overlays']"""

        # raw
        _plotRaw = self._plotDict["Raw"]
        self._rawCheckbox.setChecked(_plotRaw)

        # error
        _errorType = self._plotDict["Error"]
        if _errorType is None:
            _errorType = "None"
        self._errorComboBox.setCurrentText(_errorType)

        for name, value in self._plotDict["overlays"].items():
            self._overlayCheckBoxes[name].setChecked(value)

    def _buildPlotOptionsLayout(self):
        _vLayout = QtWidgets.QVBoxLayout()

        # to toggle columns in fi analysis df

        name = "Legend"
        value = self._plotDict[name]
        _aCheckbox = QtWidgets.QCheckBox(name)
        _aCheckbox.setChecked(value)
        _aCheckbox.stateChanged.connect(
            lambda state, name=name: self.on_check_click(state, name)
        )
        _vLayout.addWidget(_aCheckbox, alignment=QtCore.Qt.AlignTop)

        name = "Raw"
        value = self._plotDict[name]
        self._rawCheckbox = QtWidgets.QCheckBox(name)
        self._rawCheckbox.setChecked(value)
        self._rawCheckbox.stateChanged.connect(
            lambda state, name=name: self.on_check_click(state, name)
        )
        _vLayout.addWidget(self._rawCheckbox, alignment=QtCore.Qt.AlignTop)

        name = "Error"
        _errorLayout = QtWidgets.QHBoxLayout()
        _aLabel = QtWidgets.QLabel(name)
        _errorLayout.addWidget(_aLabel)
        self._errorComboBox = QtWidgets.QComboBox()
        self._errorComboBox.addItems(["None", "std", "sem"])
        self._errorComboBox.currentTextChanged.connect(self.on_error_combo_box)
        _errorLayout.addWidget(self._errorComboBox, alignment=QtCore.Qt.AlignTop)
        _vLayout.addLayout(_errorLayout)

        self._overlayCheckBoxes = {}
        for name, value in self._plotDict["overlays"].items():
            _aCheckbox = QtWidgets.QCheckBox(name)
            _aCheckbox.setChecked(value)
            _aCheckbox.stateChanged.connect(
                lambda state, name=name: self.on_check_click(state, name)
            )
            _vLayout.addWidget(_aCheckbox, alignment=QtCore.Qt.AlignTop)

            self._overlayCheckBoxes[name] = _aCheckbox

        _vLayout.addStretch()

        return _vLayout

    def replot(self):
        """Replot when file or analysis changes."""

        logger.info("")

        if self.ba is None:
            return

        # get from stat lists
        yHumanStat, yStat = self._yStatListWidget.getCurrentStat()

        # always clear the axis
        self.axs.clear()

        self.axs.autoscale(enable=True, axis="y", tight=None)

        # get masterDf
        dfMaster = self.ba.spikeDict.asDataFrame()
        if dfMaster is None or dfMaster.empty:
            # no spikes
            logger.info("no spikes to plot -> return")
            return

        # user has to specify which epoch
        plotRaw = self._plotDict["Raw"]
        if plotRaw:
            # reduce to only spikes for given epochNumber
            dfEpoch = dfMaster[dfMaster["epoch"] == self.epochNumber]
            # sns.scatterplot(x='epochLevel', y=stat, data=dfEpoch, ax=_ax)
            self.axs.scatter(
                "epochLevel",
                yStat,
                data=dfEpoch,
                marker="o",
                c="#aaaaaa",
                label=yHumanStat,
            )

        #
        # get a df with summary fi data
        intervalStat = False
        if yStat in ["spikeFreq_hz", "isi_ms"]:
            intervalStat = True
        _filename = self.ba.getFileName()
        logger.info(
            f"calling getStatFi() with epoch:{self.epochNumber} intervalStat:{intervalStat} filename:{_filename}"
        )
        self.df_fi = getStatFi(
            dfMaster,
            yStat,
            epochNumber=self.epochNumber,
            intervalStat=intervalStat,
            filename=_filename,
        )

        logger.info("generated new fi table self.df_fi:")
        print(self.df_fi)

        if self.df_fi.empty:
            logger.warning("  got empty dataframe -> return")
            return

        self._fiTableView.slotSwitchTableDf(self.df_fi)

        # cycle color
        _fiStatColor = ["c", "m", "r", "b"] * 5

        # for plotIdx, _fiStat in enumerate(fiStatList):
        plotIdx = -1
        for _fiStat, value in self._plotDict["overlays"].items():
            plotIdx += 1
            if not value:
                # plot is turned off
                continue
            _stat = yStat + "_" + _fiStat.lower()
            # _ax = sns.scatterplot(x='epochLevel', y=_stat, data=df_fi, ax=_ax)
            # _ax.plot('epochLevel', _stat, data=df_fi, linestyle='-', marker='o', color='k')
            currentColor = _fiStatColor[plotIdx]
            logger.info(f'plotting _stat:"{_stat}"')
            _errorType = self._plotDict["Error"]
            if _fiStat == "Mean" and _errorType is not None:
                _yerr = yStat + "_" + _errorType
            else:
                _yerr = None
            self.axs.errorbar(
                "epochLevel",
                _stat,
                yerr=_yerr,
                data=self.df_fi,
                linestyle="-",
                marker="o",
                color=currentColor,
                label=_fiStat,
            )

        if self._plotDict["Legend"]:
            self.axs.legend(loc="upper left")

        #
        # set x-axis to full range of all injected currents (e.g. epochLevel)
        # pad by 10%
        epochLevels = dfMaster["epochLevel"].unique()
        _minEpochLevel = np.min(epochLevels)
        _maxEpochLevel = np.max(epochLevels)
        _xRange = _maxEpochLevel - _minEpochLevel
        _xPad = _xRange * 0.1
        _xMin = _minEpochLevel - _xPad
        _xMax = _maxEpochLevel + _xPad
        logger.info(f"_xMin:{_xMin} _xMax:{_xMax}")
        if np.isnan(_xMin) or np.isnan(_xMax):
            pass
        else:
            self.axs.set_xlim([_xMin, _xMax])

        # set axis labels
        self.axs.set_xlabel("Current Step (pA)")
        self.axs.set_ylabel(yHumanStat)

        self.axs.spines["right"].set_visible(False)
        self.axs.spines["top"].set_visible(False)

        # redraw
        self.static_canvas.draw()

    def copyToClipboard(self, df: pd.DataFrame = None):
        logger.info("")
        if self.df_fi is None:
            return
        self.df_fi.to_clipboard(sep="\t", index=False)

        # want to provide some feedback
        # #if self.getSanPyApp() is not None:

    def _buildUI(self):
        # top toolbar
        _topToolbar = self._buildTopToolbar()
        self.getVBoxLayout().addLayout(_topToolbar)

        main_hLayout = QtWidgets.QHBoxLayout()

        # add list of y stats
        # has statList, a copy of sanpy.bAnalysisUtil.getStatList()
        # looks like
        #   statList['Spike Time (s)'] = {
        #       'name': 'thresholdSec',

        # trim down stat list
        _statList = sanpy.bAnalysisUtil.getStatList()
        # for k in _statList.keys():
        #     print(k)
        _hideTheseKeys = [
            "Spike Number",
            "Sweep Spike Number",
            "Sweep Number",
            "Epoch",
            "Epoch DAC",
            "Epoch Spike Number",
        ]
        _statListShort = {}
        for k, v in _statList.items():
            if k not in _hideTheseKeys:
                _statListShort[k] = v
        # _statListShort = None
        self._yStatListWidget = myStatListWidget(
            self, statList=_statListShort, headerStr="Y-Stat"
        )
        self._yStatListWidget.myTableWidget.selectRow(3)
        main_hLayout.addWidget(self._yStatListWidget)

        # add vertical list of button for fi stats like (first, last, mean, cv, etc)
        _plotOptionsLayout = self._buildPlotOptionsLayout()
        main_hLayout.addLayout(_plotOptionsLayout)

        _vPlotLayout = QtWidgets.QVBoxLayout()
        _canvas, self._mplToolbar = self.mplWindow2(addToLayout=False)
        self._mplToolbar.setVisible(False)
        # self.axs.scatter('epochLevel', stat, data=dfEpoch, marker='o', c='#777777')
        self.axs.scatter([], [])
        sns.despine()

        _vPlotLayout.addWidget(_canvas)
        _vPlotLayout.addWidget(self._mplToolbar)

        main_hLayout.addLayout(_vPlotLayout)

        self.getVBoxLayout().addLayout(main_hLayout)

        #
        # table view of current fi stats
        self._fiTableView = myTableView_tmp("FI Results")
        self._fiTableView.setVisible(False)
        # self._fiTableView.slotSwitchTableDf(self.masterDf)
        self.getVBoxLayout().addWidget(self._fiTableView)


def testPlugin():
    # load raw data
    path = "data/2021_07_20_0010.abf"
    ba = bAnalysis(path)

    # spike detect
    _dDict = bDetection().getDetectionDict("Fast Neuron")
    ba.spikeDetect(_dDict)

    # run the plugin
    import sys

    app = QtWidgets.QApplication([])
    pfi = plotFi(ba=ba)
    pfi.show()
    sys.exit(app.exec_())


def test():
    # load raw data
    path = "data/2021_07_20_0010.abf"
    ba = bAnalysis(path)

    # spike detect
    _dDict = bDetection().getDetectionDict("Fast Neuron")
    ba.spikeDetect(_dDict)

    # get masterDf
    dfMaster = ba.asDataFrame()
    if dfMaster is None:
        # no spikes
        return

    # user has to specify which epoch
    epochNumber = 2

    # the plot we will append to
    fig, _ax = plt.subplots(1, 1, sharex=True)

    # decide on what we want to plot
    # this is done in gui

    #
    # fiStat could be [first, second, mean, count, etc)

    # fiStat is a column in df_fi (See below)

    # 1) plot num spikes, no raw data
    if 0:
        fiStat = "count"  # the number of spikes
        stat = "thresholdSec"  # thresholdSec, spikeFreq_hz
        plotRaw = False

    # 1.1) plot fiStat: first, last, mean, ... spike time
    if 0:
        fiStat = "first"
        fiStat = "last"
        fiStat = "mean"
        stat = "thresholdSec"  # thresholdSec, spikeFreq_hz
        plotRaw = True

    if 0:
        # 2) plot inst freq
        fiStat = (
            "second"  # spike freq is an interval statistic (first spike does not count)
        )
        fiStat = "mean"
        stat = "spikeFreq_hz"  # thresholdSec, spikeFreq_hz
        plotRaw = True

    if 0:
        # 3) plot isi_ms
        fiStat = (
            "second"  # spike freq is an interval statistic (first spike does not count)
        )
        stat = "isi_ms"  # thresholdSec, spikeFreq_hz
        plotRaw = True

    fiStatList = ["first", "last", "mean"]
    fiStatList = ["mean"]
    stat = "spikeFreq_hz"  # thresholdSec, spikeFreq_hz
    intervalStat = True
    plotRaw = True

    #
    # get a df with summary fi data
    df_fi = getStatFi(
        dfMaster, stat, epochNumber=epochNumber, intervalStat=intervalStat
    )

    print("=== summary df_fi:")
    print(df_fi)

    # plot raw data
    # lines is of type 'matplotlib.axes._subplots.AxesSubplot'
    if plotRaw:
        # reduce to only spikes for given epochNumber
        dfEpoch = dfMaster[dfMaster["epoch"] == epochNumber]
        # sns.scatterplot(x='epochLevel', y=stat, data=dfEpoch, ax=_ax)
        _ax.scatter("epochLevel", stat, data=dfEpoch, marker="o", c="#777777")

    #
    # overlay with one stat like _mean
    # order matters! This is on top of previous plots
    _yerr = stat + "_std"
    # _yerr = stat + '_sem'

    for _fiStat in fiStatList:
        _stat = stat + "_" + _fiStat
        # _ax = sns.scatterplot(x='epochLevel', y=_stat, data=df_fi, ax=_ax)
        # _ax.plot('epochLevel', _stat, data=df_fi, linestyle='-', marker='o', color='k')
        _ax.errorbar(
            "epochLevel",
            _stat,
            yerr=_yerr,
            data=df_fi,
            linestyle="-",
            marker="o",
            color="k",
        )

    #
    # set x-axis to full range of all injected currents (e.g. epochLevel)
    # TODO: expand a bit so we can see everything
    epochLevels = dfMaster["epochLevel"].unique()
    # epochLevels = np.round(epochLevels,3)
    _minEpochLevel = np.min(epochLevels)
    _maxEpochLevel = np.max(epochLevels)
    # pad by 10%
    _xRange = _maxEpochLevel - _minEpochLevel
    _xPad = _xRange * 0.1
    # set x-axis
    _ax.set_xlim([_minEpochLevel - _xPad, _maxEpochLevel + _xPad])

    sns.despine()

    plt.show()


if __name__ == "__main__":
    # test()
    testPlugin()
