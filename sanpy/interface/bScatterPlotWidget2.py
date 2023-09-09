"""
202012

General purpose plotting from arbitrary csv files

Started as specifically for SanPy (using reanalyze.py) from a database of spikes

20210112, extending it to any csv for use with bImPy nodes/edges
    See: bImPy/bimpy/analysis/bScrapeNodesAndEdges.py

I want this to run independent of SanPy, to do this:
    copy (pandas model, checkbox delegate) from sanpy.butil
    into a local folder and change imports

Requires (need to make local copies of (pandas model, checkbox delegate)
    pandas
    numpy
    PyQt5
    matplotlib
    seaborn
    #mplcursors
    openpyxl # to load xlsx
"""

import os, sys, io, csv
import copy
from functools import partial
from collections import OrderedDict
import traceback
from typing import List, Union, Optional

import pandas as pd
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt  # abb 202012 added to set theme
import seaborn as sns
import mplcursors  # popup on hover

# originally, I wanted this to not rely on sanpy
import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)


def old_loadDatabase(path):
    """
    path: full path to .csv file generated with reanalyze.py
    """
    # path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'
    masterDf = None
    if not os.path.isfile(path):
        logger.error("did not find file:", path)
    elif path.endswith(".csv"):
        masterDf = pd.read_csv(path, header=0)  # , dtype={'ABF File': str})
    elif path.endswith(".xls"):
        masterDf = pd.read_excel(path, header=0)  # , dtype={'ABF File': str})
    elif path.endswith(".xlsx"):
        masterDf = pd.read_excel(
            path, header=0, engine="openpyxl"
        )  # , dtype={'ABF File': str})
    else:
        print("error: file type not supported. Expecting csv/xls/xlsx. Path:", path)

    # self.masterDfColumns = self.masterDf.columns.to_list()

    # not sure what this was for ???
    # 20210112, put back in if necc
    # self.masterCatColumns = ['Condition', 'File Number', 'Sex', 'Region', 'filename', 'analysisname']
    # self.masterCatColumns = self.categoricalList

    # print(self.masterDf.head())
    """
    print(masterDf.info())
    print('masterDf.iloc[0,3]:', masterDf.iloc[0,3], type(masterDf.iloc[0,3]))
    print('start seconds:', masterDf['Start Seconds'].dtype.type)
    print('start seconds:', masterDf['Start Seconds'].dtype)
    """
    #
    return masterDf


def printDict(d, withType=False):
    for k, v in d.items():
        if withType:
            print(f"  {k}: {v} {type(v)}")
        else:
            print(f"  {k}: {v}")


class myPandasModel(QtCore.QAbstractTableModel):
    def __init__(self, data : pd.DataFrame):
        """
        data: pandas dataframe
        """
        QtCore.QAbstractTableModel.__init__(self)
        self.verbose = False
        self._data = data
        columnList = self._data.columns.values.tolist()
        if "include" in columnList:
            self.includeCol = columnList.index("include")
        else:
            self.includeCol = None
        # print('pandasModel.__init__() self.includeCol:', self.includeCol)
        self.columns_boolean = ["include"]

    def rowCount(self, parent=None):
        # if self.verbose: print('myPandasModel.rowCount()')
        return self._data.shape[0]

    def columnCount(self, parnet=None):
        # if self.verbose: print('myPandasModel.columnCount()')
        return self._data.shape[1]

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if self.verbose:
            print("myPandasModel.data()")
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                # return QtCore.QVariant()

                # return str(self._data.iloc[index.row(), index.column()])
                retVal = self._data.iloc[index.row(), index.column()]
                if isinstance(retVal, np.float64):
                    retVal = float(retVal)
                    retVal = round(retVal, 4)  # round everything to 4 decimal places
                    if np.isnan(retVal):
                        retVal = ""
                elif isinstance(retVal, np.int64):
                    retVal = int(retVal)
                #
                return retVal
            elif role == QtCore.Qt.BackgroundRole:
                # return
                return QtCore.QVariant()

        return None

    def update(self, dataIn):
        if self.verbose:
            print("myPandasModel.update()")

    def setData(self, index, value, role=QtCore.Qt.DisplayRole):
        """
        This is curently limited to only handle checkbox
        todo: extend to allow editing

        Returns:
            True if value is changed. Calls layoutChanged after update.
            False if value is not different from original value.
        """
        if self.verbose:
            print("myPandasModel.setData()")
        print(
            "  myPandasModel.setData() row:",
            index.row(),
            "column:",
            index.column(),
            "value:",
            value,
            type(value),
        )
        # if index.column() == self.includeCol:

        # dataChanged is inherited from QAbstractItemModel
        # topLeftIndex = index
        # bottomRightIndex = index
        # self.dataChanged.emit(index, index)

        if 1:
            # print('value:', value, type(value))
            v = self._data.iloc[index.row(), index.column()]
            # print('before v:',v, type(v))
            # print('isinstance:', isinstance(v, np.float64))
            if isinstance(v, np.float64):
                try:
                    value = float(value)
                except ValueError as e:
                    print("please enter a number")
                    return False

            # set
            self._data.iloc[index.row(), index.column()] = value

            v = self._data.iloc[index.row(), index.column()]
            print("    after v:", v, type(v))
            return True
        return True

    def flags(self, index):
        if self.verbose:
            print("myPandasModel.flags()")
            print("  index.column():", index.column())
        if 1:
            # turn on editing (limited to checkbox for now)
            if index.column() in self.columns_boolean:
                # print('  return with columns_boolean')
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable
            # print('  return with ...')
            return (
                QtCore.Qt.ItemIsEditable
                | QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsSelectable
            )
        else:
            return QtCore.Qt.ItemIsEnabled

    def headerData(self, col, orientation, role):
        # if self.verbose: print('myPandasModel.headerData()')
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._data.columns[col]
        return None


# see: https://stackoverflow.com/questions/17748546/pyqt-column-of-checkboxes-in-a-qtableview
class myCheckBoxDelegate(QtWidgets.QItemDelegate):
    """
    A delegate that places a fully functioning QCheckBox cell of the column to which it's applied.
    """

    def __init__(self, parent):
        QtWidgets.QItemDelegate.__init__(self, parent)
        self.verbose = False
        if self.verbose:
            print("myCheckBoxDelegate.__init__()")

    def createEditor(self, parent, option, index):
        """
        Important, otherwise an editor is created if the user clicks in this cell.
        """
        if self.verbose:
            print("myCheckBoxDelegate.createEditor()")
        return None

    def paint(self, painter, option, index):
        """
        Paint a checkbox without the label.

        option: PyQt5.QtWidgets.QStyleOptionViewItem
        index: PyQt5.QtCore.QModelIndex
        """
        if self.verbose:
            print("myCheckBoxDelegate.paint()")
        # print('  option:', option, 'index:', index)
        # print('  index.data():', type(index.data()), index.data())
        # HasCheckIndicator = QtWidget.QStyleOptionViewItem.HasCheckIndicator
        # options.HasCheckIndicator returns hex 4, value of enum
        # how do i query it?
        # print('  ', option.ViewItemFeatures().HasCheckIndicator) # returns PyQt5.QtWidgets.QStyleOptionViewItem.ViewItemFeature
        # print('  ', option.features)
        # print('  ', index.data(QtCore.Qt.CheckStateRole)  )
        # state = index.data(QtCore.Qt.CheckStateRole)
        # print('  state:', state, 'option.HasCheckIndicator:', option.HasCheckIndicator)
        self.drawCheck(
            painter,
            option,
            option.rect,
            QtCore.Qt.Unchecked if int(index.data()) == 0 else QtCore.Qt.Checked,
        )

    def editorEvent(self, event, model, option, index):
        """
        Change the data in the model and the state of the checkbox
        if the user presses the left mousebutton and this cell is editable. Otherwise do nothing.
        """
        if self.verbose:
            print("myCheckBoxDelegate.editorEvent()")
        if not int(index.flags() & QtCore.Qt.ItemIsEditable) > 0:
            return False

        if (
            event.type() == QtCore.QEvent.MouseButtonRelease
            and event.button() == QtCore.Qt.LeftButton
        ):
            # Change the checkbox-state
            self.setModelData(None, model, index)
            return True

        return False

    def setModelData(self, editor, model, index):
        """
        The user wanted to change the old state in the opposite.
        """
        if self.verbose:
            print("myCheckBoxDelegate.setModelData()")
            print("  editor:", editor)
            print("  model:", model)
            print("  index:", index)
            print("  index.data():", type(index.data()), index.data())
        # data = index.data()
        # if isinstance(data, str):
        #    return
        newValue = 1 if int(index.data()) == 0 else 0
        model.setData(index, newValue, QtCore.Qt.EditRole)

class myTableView(QtWidgets.QTableView):
    def __init__(self, dataType, parent=None):
        """
        dataType: in ['All Spikes', 'File Mean']
        """
        super(myTableView, self).__init__(parent)

        self.dataType = dataType

        self.doIncludeCheckbox = False  # todo: turn this on
        self.keepCheckBoxDelegate = myCheckBoxDelegate(None)

        # self.setFont(QtGui.QFont('Arial', 10))
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

        p = self.palette()
        color1 = QtGui.QColor("#dddddd")
        color2 = QtGui.QColor("#ffffff")
        p.setColor(QtGui.QPalette.Base, color1)
        p.setColor(QtGui.QPalette.AlternateBase, color2)
        self.setAlternatingRowColors(True)
        self.setPalette(p)

    def slotSelectRow(self, selectDict):
        """only select if selectDict['Data Type'] matches what we are showing
        """
        if self.dataType != selectDict["Data Type"]:
            return

        logger.info(f'slotSelectRow() selectDict:{selectDict}')
        ind = selectDict["index"]
        """
        plotDf = selectDict['plotDf']
        index = plotDf.at[ind, 'index']
        index = int(index)
        """
        index = ind
        index -= 1  # !!! MY VISUAL INDEX IN TABLE IS ONE BASED !!!
        column = 0
        modelIndex = self.model().index(index, column)
        self.setCurrentIndex(modelIndex)

    def slotSwitchTableDf(self, newDf):
        """set model from df
        """
        if newDf is None:
            model = None
        else:
            model = myPandasModel(newDf)
        self.slotSwitchTableModel(model)

    def slotSwitchTableModel(self, newModel):
        """
        switch between full .csv model and getMeanDf model
        """
        # print('myTableView.slotSwitchTableModel()')
        self.setModel(newModel)

        if newModel is None:
            return

        colList = newModel._data.columns.values.tolist()
        # print('  todo: slotSwitchTableModel() set all columns to default delegate itemDelegate()')
        for idx, col in enumerate(colList):
            # default delegate is self.tableView.itemDelegate()
            self.setItemDelegateForColumn(idx, self.itemDelegate())

        # install checkboxes in 'incude' column
        if self.doIncludeCheckbox and "include" in colList:
            includeColIndex = colList.index("include")
            print(
                f"_switchTableModel() setting include column {includeColIndex} to myCheckBoxDelegate"
            )
            # self.tableView.setItemDelegateForColumn(includeColIndex, myCheckBoxDelegate(None))
            self.setItemDelegateForColumn(includeColIndex, self.keepCheckBoxDelegate)


class myStatListWidget(QtWidgets.QWidget):
    """Widget to display a table with selectable stats.

    Gets list of stats from: sanpy.bAnalysisUtil.getStatList()
    """

    signalStatSelection = QtCore.pyqtSignal(object, object)  # str: header str
                                                            #str: human deadable stat name

    def __init__(self, myParent, statList=None, headerStr="Stat", parent=None):
        """
        Parameters
        ----------
        myParent : sanpy.interface.plugins.sanpyPlugin
        statList : dict
            from sanpy.bAnalysisUtil.getStatList()
        headerStr : str
            Show as label aove stat list
        """
        super().__init__(parent)

        self.myParent = myParent
        if statList is not None:
            self.statList = statList
        else:
            # from main sanpy
            # for pooling we have some addition columns like 'file number'
            self.statList = sanpy.bAnalysisUtil.getStatList()

        self._headerStr = headerStr

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
        fnt = self.font()
        fnt.setPointSize(self._rowHeight)
        self.myTableWidget.setFont(fnt)

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

    def setCurrentRow(self, str):
        """Select row based on row item string.
        
        Ussually a analysis parameter like 'Spike Frequency (Hz)'
        """
        # find index in dict
        try:
            idx = list(self.statList.keys()).index(str)
        except (KeyError) as e:
            logger.error(f'did not find key {str}')
            return

        # select row index
        if idx >= 0:
            self.myTableWidget.selectRow(idx)

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
            logger.error(f'Did not find humanStat:"{humanStat}"')
            humanStat = None
            stat = None

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
        yStat = self.myTableWidget.item(row, 0).text()
        logger.info(f'{yStat}')
        self.myParent.replot()

        self.signalStatSelection.emit(self._headerStr, yStat)

    """
    @QtCore.pyqtSlot()
    def on_button_click(self, name):
        print('=== myStatPlotToolbarWidget.on_button_click() name:', name)
    """


# class myMplCanvas(FigureCanvas):
class myMplCanvas(QtWidgets.QFrame):
    """Hold an fig/plot canvas, in scatter plot we can have 1-4 of these
    """

    signalSelectFromPlot = QtCore.Signal(object)
    signalSelectSquare = QtCore.Signal(object, object)  # plot number, state dict
    signalSetStatusBar = QtCore.Signal(str)

    def __init__(self, plotState : "plotState", parent=None):
        super().__init__(parent)  # FigureCanvas

        # self.setFrameWidth(5)
        # self.setStyleSheet("background-color: rgb(0, 255, 0)")
        # self.setContentsMargins(0, 0, 0, 0)
        # self.setContentsMargins(-20, 0, 5, 0)
        self.setFrameShape(QtWidgets.QFrame.Box)
        self.setLineWidth(0)

        pal = self.palette()
        pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor("red"))
        self.setPalette(pal)

        #
        self.stateDict = plotState
        #self.plotNumber = plotState['Plot Number']
        self.plotDf = None
        self.whatWeArePlotting = None

        self.mplCursorHover = None
        # self.mplCursorHover = mplcursors.cursor(self.whatWeArePlotting,
        #                                         highlight=True,
        #                                         hover=mplcursors.HoverMode.Transient)

        # needed to show canvas in widget
        self.layout = QtWidgets.QVBoxLayout()  # any will do

        self.fig = Figure(constrained_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.axes = self.fig.add_subplot(111)  # was this

        # self.canvas.axes = self.fig.add_axes([0.1, 0.1, 0.9, 0.9]) # [x, y, w, h]
        # gs1 = gridspec.GridSpec(1, 1)
        # gs1.tight_layout(self.fig, rect=[0.5, 0, 1, 1], h_pad=0.5)
        # self.canvas.axes = self.fig.add_subplot(gs1[0])

        # user clicks on plot point
        self.cid2 = self.canvas.mpl_connect("pick_event", self.on_pick_event)
        
        # user clicks in the figure, used to highlight the widget with red square
        self.cid3 = self.canvas.mpl_connect("button_press_event", self.on_pick_event2)

        self.scatterPlotSelection = None

        self.mplToolbar = NavigationToolbar2QT(
            self.canvas, self.canvas
        )  # params are (canvas, parent)
        self.mplToolbar.hide()  # initially hidden

        # 20210829
        """
        print('1 creating empty legend')
        self.myLegend = self.canvas.axes.legend()
        self.myLegend.set_visible(False)  #hide()
        """

        self.canvas.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.canvas.updateGeometry()

        # fig.subplots_adjust(wspace=0.3, hspace=0.3)
        # self.fig.tight_layout(pad = 3.0) # Padding between the figure edge and the edges of subplots, as a fraction of the font size.
        # self.fig.subplots_adjust(left=0.15,right=0.9,
        #                            bottom=0.1,top=0.9,
        #                            hspace=0.2,wspace=0.2)

        #
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)

    #@property
    def getPlotNumber(self):
        return self.stateDict['Plot Index']

    def mousePressEvent(self, event):
        logger.info("===")
        print(
            "  todo: set all controls to match the plot just clicked on using self.stateDict!!!"
        )
        # print('  stateDict:', self.stateDict)
        self.signalSelectSquare.emit(self.getPlotNumber(), self.stateDict)

    def contextMenuEvent(self, event):
        print("myMplCanvas.contextMenuEvent()")
        contextMenu = QtWidgets.QMenu(self)
        saveAsAction = contextMenu.addAction("Save As...")
        action = contextMenu.exec_(self.mapToGlobal(event.pos()))
        if action == saveAsAction:
            print("todo: save as")
            self.fig.savefig("", dpi=600)

    def on_pick_event(self, event):
        """On pick for Line Plot.

        Parameters
        ----------
        event : matplotlib.backend_bases.PickEvent
        """

        logger.info('===')

        ax = self.whatWeArePlotting
        # print('  axes has num lines:', len(ax.get_lines()))

        legend_label = event.artist.get_label()   
        # print('  event.artist:', event.artist)
        # event.artist: Line2D(_child63)
        # print('  event legend_label:', legend_label)

        # Seaborn uses 2 labels for 1 line, we only want to use the second label
        half_label_length = int(len(ax.get_lines())/2)
        try:
            _labelList = [_line.get_label() for _line in ax.get_lines()]
            
            # for _labelIdx, _label in enumerate(_labelList):
            #     print(f'  _labelIdx:{_labelIdx} has _label:{_label}')
            
            # realIdx = ax.get_lines().index(legend_label)
            actualIndex = _labelList.index(legend_label)
            # sometimes we get labels like 'sex', 'unique name' and sometimes not ???
            labelOffset = 0  # = -2
            realIdx = actualIndex + half_label_length + labelOffset
            # realLabel = ax.get_lines()[realIdx].getLabel()
            realLabel = _labelList[realIdx]

            logger.info(f'realLabel:{realLabel}')
            self.signalSetStatusBar.emit(realLabel)

            # logger.info(f'  legend_label:{legend_label}')
            # logger.info(f'  at actual index:{actualIndex}')
            # logger.info(f'  has realIdx:{realIdx}')
            # logger.info(f'  realLabel:{realLabel}')

        except (ValueError) as e:
            logger.error(f'ValueError of: {e}')

        return

        # Seaborn uses 2 labels for 1 line, we only want to use the second label
        label_length = int(len(ax.get_lines())/2)
        label_length = int(len(ax.get_lines()))
        for x in range(label_length):
            currLabel = ax.get_lines()[x+label_length].get_label()
            print('  currLabel:', currLabel)

            if legend_label == currLabel:
                if ax.get_lines()[x].get_visible():
                    ax.get_lines()[x].set_visible(False)
                else:
                    ax.get_lines()[x].set_visible(True)
                #fig.canvas.draw()
        return

        try:
            # logger.info(f'  {type(event)}')
            # logger.info(f'  {event}')
            logger.info(f'=== event.ind: "{event.ind}"')

            # line = event.artist  # like Line2D(_child63)
            # print('line:', line)

            # axisIndex = self.canvas.axes.lines.index(event.artist)
            
            # <Axes.ArtistList of 1 lines>
            print('  self.whatWeArePlotting.lines:', self.whatWeArePlotting.lines)
            
            axisIndex = self.whatWeArePlotting.lines.index(event.artist)
            print('  axisIndex:', axisIndex)

            if len(event.ind) < 1:
                return
            spikeNumber = event.ind[0]
            # print('  selected:', spikeNumber)

            # propagate a signal to parent
            # self.myMainWindow.mySignal('select spike', data=spikeNumber)
            # self.selectSpike(spikeNumber)

        except AttributeError as e:
            pass

    def on_pick_event2(self, event):
        """Pick event to select a square.
        """
        #logger.info("===")

        # for k, v in self.stateDict.items():
        #     if k == "masterDf":
        #         print(f"  {k}: length is {len(v)}")
        #     else:
        #         print(f"  {k}: {v}")

        self.signalSelectSquare.emit(self.getPlotNumber(), self.stateDict)

    def on_pick(self, event):
        """Handle user click in scatter

        todo: this makes perfect sense for scatter but maybe not other plots???
        """
        logger.info('=== myMplCanvas')  #' event:', type(event), event)
        
        # only allow pick in Scatter Plot
        if not self.stateDict['Plot Type'] in ['Scatter Plot', 'Scatter + Raw + Mean']:
            logger.warning('picking only allowed in scatter plots')
            # self.signalSetStatusBar.emit('Selection only allowed in scatter plots')
            return

        # if what we are plotting has different length from df
        # means there were nan value in df, picking is not possible
        line = event.artist
        offsets = line.get_offsets()
        if len(offsets) != len(self.plotDf):
            logger.error('Plot and DataFrame length do not match')
            logger.error('  this occurs when there were nan values in dataframe and they do not get plotted')
            _warningStr = 'Plot and DataFrame length do not match. This happens when we plot something like "Spike Frequency", the first spike does not have a value.'
            self.signalSetStatusBar.emit(_warningStr)
            return

        # filter out clicks on 'Annotation' used by mplcursors
        # try:
        #     # when Scatter, line is 'PathCollection', a list of (x,y)
        #     offsets = line.get_offsets()
        # except AttributeError as e:
        #     logger.info(f'get_offsets() triggered AttributeError, not a scatter plot.')
        #     return

        ind = event.ind  # ind is a list []
        if len(ind) == 0:
            return
        ind = ind[0]

        # ind is the ith element in (x,y) list of offsets
        # ind 10 (0 based) is index 11 (1 based) in table list
        # logger.info(f"  user selected ind:{ind}, offsets: {offsets[ind]}")
        logger.info(f"  user selected ind:{ind}")
        
        selectDict = self.getAnnotation(ind)

        if selectDict is None:
            return
        
        # to do, just put copy of state dict ???
        selectDict["Plot Type"] = self.stateDict["Plot Type"]
        selectDict["Data Type"] = self.stateDict["Data Type"]
        #
        # emit
        logger.info(f"  myMplCanvas.signalSelectFromPlot.emit(selectDict)")
        for k,v in selectDict.items():
            print('  k:', k, 'v:', v)

        self.signalSelectFromPlot.emit(selectDict)
        
        _selStr = selectDict['Unique Name']
        self.signalSetStatusBar.emit(_selStr)

    def _selectInd(self, ind):
        """visually select a point in scatter plot
        """
        if self.plotDf is None:
            # no plot yet
            return
        logger.info(f'myMplCanvas._selectInd() ind:{ind}')
        if ind > len(self.plotDf) - 1:
            return
        xVal = self.plotDf.at[ind, self.stateDict["xStat"]]
        yVal = self.plotDf.at[ind, self.stateDict["yStat"]]
        if self.scatterPlotSelection is not None:
            logger.info(f'  scatterPlotSelection x:{xVal} y:{yVal}')
            self.scatterPlotSelection.set_data(xVal, yVal)
        self.fig.canvas.draw()

    def getAnnotation(self, ind : int):
        """Get info on an annotation index.
        
        Lots of plots do not give an integer index and just ignore them.
        """
        if not np.issubdtype(ind, np.integer):
            #logger.error(f'myMplCanvas.getAnnotation() got bad ind:{ind} {type(ind)}')
            return

        xStat = self.stateDict["xStat"]
        yStat = self.stateDict["yStat"]
        # groupByColumnName = self.stateDict["Group By (Stats)"]

        # analysisName = self.plotDf.at[ind, groupByColumnName]
        index = None
        if not 'index' in self.plotDf.columns:
            logger.error(f'did not find "index" column. Available columns are')
            logger.error(f'{self.plotDf.columns}')
        else:
            index = self.plotDf.at[ind, "index"]

        try:
            uniqueName = self.plotDf.at[ind, "Unique Name"]  # not all will have this
        except KeyError as e:
            uniqueName = "n/a"

        # for v in self.plotDf.loc[ind]:
        #     print(v)

        xVal = self.plotDf.at[ind, xStat]
        yVal = self.plotDf.at[ind, yStat]

        returnDict = {
            "Unique Name": uniqueName,
            "ind": ind,
            "index": index,
            # "analysisName": analysisName,
            # "region": region,
            "xVal": xVal,
            "yVal": yVal,
            #'plotDf': self.plotDf, # potentially very big
        }
        return returnDict

    def slot_selectSquare(self, plotNumber, stateDict):
        # print('myMplCanvas.slotSelectSquare()', plotNumber, 'self.plotNumber:', self.plotNumber)
        if plotNumber == self.getPlotNumber():
            self.setLineWidth(1)
        else:
            self.setLineWidth(0)

    def slot_selectInd(self, selectDict):
        logger.info(f'selectDict:{selectDict}')
        if self.stateDict["Plot Type"] == selectDict["Plot Type"]:
            # only select if same plot type, o/w selections are out of synch
            self._selectInd(selectDict["ind"])

    def slotCancelSelection(self):
        if self.scatterPlotSelection is not None:
            self.scatterPlotSelection.set_data([], [])
        # self.draw()
        # cancel mplCursorHover hover selection
        # if self.mplCursorHover is not None:
        #     selections = self.mplCursorHover.selections
        #     if len(selections) == 1:
        #         self.mplCursorHover.remove_selection(selections[0])

        # never cancel red square, we always wan't one
        # self.slotSelectSquare(None)

        #
        # self.draw() # to update hover
        self.fig.canvas.draw()

    def updateTheme(self):
        """redraw using stored self.state
        """
        self.myUpdate()

    def myUpdateGlobal(self, stateDict):
        """Update globals but do not plot.

        globals are things shared across all plots like mpl toolbar and legend.
        """
        # self.canvas.axes.legend().set_visible(stateDict["Legend"])
        _legend = self.canvas.axes.get_legend()
        if _legend is not None:
            _legend.set_visible(stateDict["Legend"])

        if stateDict["Toolbar"]:
            self.mplToolbar.show()
        else:
            self.mplToolbar.hide()

        #print('stateDict:', stateDict.keys())
        
        if stateDict["Hover Info"] and self.whatWeArePlotting is not None:
            
            # self.doHover = True
            if self.mplCursorHover is not None:
                # Remove all Selections, disconnect all callbacks,
                # and allow the cursor to be garbage collected.
                self.mplCursorHover.remove()
                self.mplCursorHover = None

            self.mplCursorHover = mplcursors.cursor(self.whatWeArePlotting,
                                                    highlight=False,
                                                    hover=mplcursors.HoverMode.Transient)
            self.mplCursorHover.connect('add', self._mplCursorCallback)

            # @self.mplCursorHover.connect("add")
            # def _(sel):
            #     #sel: mplcursors._pick_info.Selection
            #     logger.info(f'sel:{type(sel)}')
            #     # sel.annotation.get_bbox_patch().set(fc="white")
            #     sel.annotation.arrow_patch.set(
            #         arrowstyle="simple", fc="white", alpha=0.5
            #     )
            #     # row in df is from sel.target.index
            #     # print('sel.target.index:', sel.target.index)
            #     # ind = sel.target.index
            #     ind = sel.index
            #     annotationDict = self.getAnnotation(ind)
            #     myText = ""
            #     if annotationDict is not None:
            #         for k, v in annotationDict.items():
            #             myText += f"{k}: {v}\n"
            #     sel.annotation.set_text(myText)

        elif not stateDict["Hover Info"]:
            # self.mplCursorHover = mplcursors.cursor(self.whatWeArePlotting,
            #                                         highlight=False,
            #                                         hover=mplcursors.HoverMode.NoHover)
            if self.mplCursorHover is not None:
                self.mplCursorHover.remove()
                self.mplCursorHover = None

            # self.doHover = False
            # if self.mplCursorHover is not None:
            #     # self.mplCursorHover.HoverMode(mplcursors.HoverMode.NoHover)
            #     try:
            #         self.mplCursorHover.disconnect("add", self._mplCursorCallback)
            #     except (ValueError) as e:
            #         pass
            # cancel mplCursorHover hover selection
            # if self.mplCursorHover is not None:
            #     selections = self.mplCursorHover.selections
            #     if len(selections) == 1:
            #         self.mplCursorHover.remove_selection(selections[0])

        
        # self.draw() # to update hover
        self.fig.canvas.draw()

    def _mplCursorCallback(self, sel):
        logger.info(sel)
        # logger.info(self.stateDict['doHover'])

        # if not self.stateDict['doHover']:
        #     return

        #sel: mplcursors._pick_info.Selection
        # logger.info(f'sel:{type(sel)}')
        # sel.annotation.get_bbox_patch().set(fc="white")
        sel.annotation.arrow_patch.set(
            arrowstyle="simple", fc="white", alpha=0.5
        )
        # row in df is from sel.target.index
        # print('sel.target.index:', sel.target.index)
        # ind = sel.target.index
        ind = sel.index
        annotationDict = self.getAnnotation(ind)
        myText = ""
        if annotationDict is not None:
            for k, v in annotationDict.items():
                myText += f"{k}: {v}\n"
        sel.annotation.set_text(myText)

    def _stateIsMyState(self, state : "plotState") -> bool:
        """Return true if state matches self.stateDict.
        
        Do this by comparing 'Plot Index'
        """
        
        # logger.info(f"state plot index is {state['Plot Index']} and self.stateDict is {self.stateDict['Plot Index']}")

        return state['Plot Index'] == self.stateDict['Plot Index']

    def myUpdate(self, state : "plotState" = None, forceDeepCopy=False):
        """update plot based on control interface
        """

        if state is not None and not self._stateIsMyState(state):
            # DeepCopy the state and claim ownership
            logger.info(f'!!! DeepCopy to new state !!!')
            myPlotIndex = self.getPlotNumber()
            self.stateDict = copy.deepcopy(state)
            self.stateDict.setState('Plot Index', myPlotIndex)

        state = self.stateDict

        plotType = state["Plot Type"]
        dataType = state["Data Type"]
        
        hue = state["Hue"]
        if hue == 'None':
            hue = None
        
        style = state["Style"]
        if style == 'None':
            style = None
        
        groupByColumnName = state["Group By (Stats)"]

        markerSize = state['Marker Size']

        xStatHuman = state["X Statistic"]
        yStatHuman = state["Y Statistic"]

        logger.info(f'myMplCanvas plotting {self.getPlotNumber()}')
        logger.info(f'  plotType:{plotType}')
        logger.info(f'  dataType:{dataType}')
        logger.info(f'  xStatHuman:{xStatHuman}')
        logger.info(f'  yStatHuman:{yStatHuman}')
        logger.info(f'  markerSize:{markerSize}')

        xStat = state["xStat"]
        yStat = state["yStat"]

        xIsCategorical = state["xIsCategorical"]
        yIsCategorical = state["yIsCategorical"]

        masterDf = state["masterDf"]
        meanDf = state["meanDf"]

        if masterDf is None:
            logger.error(f"masterDf is None for plot {state['Plot Index']} -->> not plotting")
            return
        if meanDf is None:
            logger.error(f"meanDf is None for plot {state['Plot Index']} -->> not plotting")
            return
        
        includeNo = state['Include No']
        if includeNo:
            thisMasterDf = masterDf
        else:
            thisMasterDf = masterDf[masterDf['Include']=='yes']
            thisMasterDf = thisMasterDf.reset_index()

        if dataType == 'All Spikes':
            self.plotDf = thisMasterDf
        else:
            self.plotDf = meanDf

        warningStr = ''  # fill in and will emit to staus bar
        
        self.canvas.axes.clear()

        picker = 5
        if plotType in ["Scatter Plot", "Scatter + Raw + Mean", 'Line Plot', 'Line + Markers']:
            # scatter plot user selection
            (self.scatterPlotSelection,) = self.canvas.axes.plot(
                [], [], "oy", markersize=markerSize,
                # fillstyle="none"
            )

            # main scatter
            try:
                if plotType in ['Line Plot', 'Line + Markers']:
                    if plotType == 'Line + Markers':
                        doMarkerSize = markerSize
                        doMarker = 'o'
                    else:
                        doMarker = ''
                        doMarkerSize = None
                    self.whatWeArePlotting = sns.lineplot(
                        x=xStat,
                        y=yStat,
                        hue=hue,
                        style=style,
                        data=thisMasterDf,
                        ax=self.canvas.axes,
                        picker=picker,
                        marker=doMarker,
                        markersize=doMarkerSize,  # default is 6
                        zorder=0,
                    )
                else:
                    # logger.info(f'markerSize:{markerSize}')
                    
                    # while debugging fact that plotting with nan yileds a plot without nan index
                    # __idx = 273
                    # print(f'xxx thisMasterDf __idx', __idx, 'has x/y for x:', xStat, 'y:', yStat)
                    # print('  ', thisMasterDf.loc[__idx]['index'])
                    # print('  ', thisMasterDf.loc[__idx][xStat])
                    # print('  ', thisMasterDf.loc[__idx][yStat])
                    
                    self.whatWeArePlotting = sns.scatterplot(
                        x=xStat,
                        y=yStat,
                        hue=hue,
                        style=style,
                        data=thisMasterDf,
                        ax=self.canvas.axes,
                        picker=picker,
                        zorder=0,
                        size=markerSize,  # default is 6
                    )
            except ValueError as e:
                self.fig.canvas.draw()
                logger.error('  EXCEPTION: in "Scatter/Line Plot", exception is:')
                logger.error(f'  {e}')
                logger.error(f'  hue:{hue}')
                logger.error(f'  meanDf columns are {meanDf.columns}')

            # sem in both x and y, pulling from masterDf
            if dataType == "File Mean" or plotType == "Scatter + Raw + Mean":
                # we need to do this for each hue???
                # if x or y is in categorical (e.g. a string) then do not do this ...
                if xIsCategorical or yIsCategorical:
                    pass
                else:
                    logger.info(
                        f"  grabbing mean +- sem for self.groupByColumnName: {groupByColumnName}"
                    )
                    color = "k"
                    xd = thisMasterDf.groupby(groupByColumnName).mean(numeric_only=True)[
                        xStat
                    ]
                    xerrd = thisMasterDf.groupby(groupByColumnName).sem(numeric_only=True)[
                        xStat
                    ]
                    yd = thisMasterDf.groupby(groupByColumnName).mean(numeric_only=True)[
                        yStat
                    ]
                    yerrd = thisMasterDf.groupby(groupByColumnName).sem(numeric_only=True)[
                        yStat
                    ]
                    self.canvas.axes.errorbar(
                        xd,
                        yd,
                        xerr=xerrd,
                        yerr=yerrd,
                        fmt="none",
                        capsize=0,
                        zorder=10,
                        color=color,
                        alpha=0.5,
                    )

        elif plotType == "Histogram":
            yStatHuman = "Count"
            doKde = False  # stateDict['doKDE']
            try:
                g = sns.histplot(
                    x=xStat,
                    hue=hue,
                    kde=doKde,
                    data=meanDf,
                    ax=self.canvas.axes,
                    picker=picker,
                )
            except ValueError as e:
                self.fig.canvas.draw()
                logger.error(f'Histogram:{e}')

        elif plotType == "Cumulative Histogram":
            yStatHuman = "Probability"
            try:
                g = sns.histplot(
                    x=xStat,
                    hue=hue,
                    cumulative=True,
                    stat="density",
                    element="step",
                    fill=False,
                    common_norm=False,
                    data=meanDf,
                    ax=self.canvas.axes,
                    picker=picker,
                )
            except ValueError as e:
                self.fig.canvas.draw()
                print("EXCEPTION in Cumulative Histogram:", e)

        elif plotType == "Cumulative Histogram":
            yStatHuman = "Probability"
            try:
                g = sns.histplot(
                    x=xStat,
                    hue=hue,
                    cumulative=True,
                    stat="density",
                    element="step",
                    fill=False,
                    common_norm=False,
                    data=meanDf,
                    ax=self.canvas.axes,
                    picker=picker,
                )
            except ValueError as e:
                self.fig.canvas.draw()
                print("EXCEPTION in Cumulative Histogram:", e)

        elif plotType == "Violin Plot":
            if not xIsCategorical:
                warningStr = "Violin plot requires a categorical x statistic"
            else:
                g = sns.violinplot(
                    x=xStat, y=yStat, hue=hue, data=meanDf, ax=self.canvas.axes
                )

        elif plotType == "Box Plot":
            if not xIsCategorical:
                warningStr = "Box plot requires a categorical x statistic"
            else:
                g = sns.boxplot(
                    x=xStat, y=yStat, hue=hue, data=meanDf, ax=self.canvas.axes
                )

        elif plotType == "Raw + Mean Plot":
            if not xIsCategorical:
                warningStr = "Raw + Mean plot requires a categorical x statistic"
            else:
                try:
                    # does not work here for categorical x
                    # self.scatterPlotSelection, = self.canvas.axes[0].plot([], [], 'oy',
                    #                markersize=12, fillstyle='none')

                    """
                    colorList = [('red'), ('green'), 'b', 'c', 'm', 'y']
                    hueList = meanDf[hue].unique()
                    palette = {}
                    for idx, hue in enumerate(hueList):
                        palette[hue] = colorList[idx]
                    print(palette)
                    """

                    palette = sns.color_palette("Paired")
                    # palette = ['r', 'g', 'b']

                    # stripplot
                    # g = sns.swarmplot(x=xStat, y=yStat,
                    g = sns.stripplot(
                        x=xStat,
                        y=yStat,
                        hue=hue,
                        palette=palette,
                        data=meanDf,
                        ax=self.canvas.axes,
                        # color = color,
                        dodge=True,
                        alpha=0.6,
                        picker=picker,
                        zorder=1,
                    )

                    # logger.error('!!!!!!!!!!!! grabbing get_legend_handles_labels()')
                    self.canvas.axes.legend().remove()

                    # logger.error('!!!!!!!!!!!! grabbing get_legend_handles_labels()')
                    
                    # removed 20230816
                    # print("\n\n\nREMAKING LEGEND\n\n\n")
                    # handles, labels = self.canvas.axes.get_legend_handles_labels()
                    # l = self.canvas.axes.legend(
                    #     handles[0:2],
                    #     labels[0:2],
                    #     bbox_to_anchor=(1.05, 1),
                    #     loc=2,
                    #     borderaxespad=0.0,
                    # )
                    
                    # self.myLegend = self.canvas.axes.Legend(handles[0:2], labels[0:2], bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

                    """
                    if self.darkTheme:
                        color = 'w'
                    else:
                        color = 'k'
                    color = [color] * len(hueList)
                    print('color:', color)
                    """

                    self.whatWeArePlotting = sns.pointplot(
                        x=xStat,
                        y=yStat,
                        hue=hue,
                        # palette=palette,
                        data=meanDf,
                        estimator=np.nanmean,
                        ci=68,
                        capsize=0.1,
                        ax=self.canvas.axes,
                        color="r",
                        # legend='full',
                        # zorder=10)
                    )
                except ValueError as e:
                    print('EXCEPTION in "Raw + Mean Plot":', e)
                    traceback.print_exc()

        elif plotType == "Regression Plot":
            # regplot does not have hue
            if xIsCategorical or yIsCategorical:
                warningStr = "Regression plot requires continuous x and y statistics"
            else:
                # todo: loop and make a regplot
                # for each unique() name in
                # hue (like Region, Sex, Condition)
                hueList = masterDf[hue].unique()
                for oneHue in hueList:
                    if oneHue == "None":
                        continue
                    tmpDf = meanDf[meanDf[hue] == oneHue]
                    # print('regplot oneHue:', oneHue, 'len(tmpDf)', len(tmpDf))
                    sns.regplot(x=xStat, y=yStat, data=tmpDf, ax=self.canvas.axes)
        else:
            logger.error(f'did not understand plot type: {plotType}')

        #
        # update
        self.canvas.axes.figure.canvas.mpl_connect("pick_event", self.on_pick)

        # self.mplCursorHover = None
        # if stateDict["doHover"] and self.whatWeArePlotting is not None:
        #     self.mplCursorHover = mplcursors.cursor(self.whatWeArePlotting, hover=mplcursors.HoverMode.Transient)

        #     @self.mplCursorHover.connect("add")
        #     def _(sel):
        #         # sel.annotation.get_bbox_patch().set(fc="white")
        #         sel.annotation.arrow_patch.set(
        #             arrowstyle="simple", fc="white", alpha=0.5
        #         )
        #         # row in df is from sel.target.index
        #         # print('sel.target.index:', sel.target.index)
        #         ind = sel.target.index
        #         annotationDict = self.getAnnotation(ind)
        #         myText = ""
        #         for k, v in annotationDict.items():
        #             myText += f"{k}: {v}\n"
        #         sel.annotation.set_text(myText)

        #
        # self.slot_setStatusBar(warningStr)

        self.canvas.axes.spines["right"].set_visible(False)
        self.canvas.axes.spines["top"].set_visible(False)

        # if not state["Legend"]:
            # print('self.canvas.axes.legend():', self.canvas.axes.legend())
            # print('self.canvas.axes.legend:', self.canvas.axes.legend)
            # if self.canvas.axes.legend() is not None:
            # logger.error('!!!!!!!!!!!! grabbing get_legend_handles_labels()')
            #logger.info('  removing legend')
            # self.canvas.axes.legend().remove()
            #self.canvas.axes.get_legend().remove()

        # print('myUpdate() self.plotSize:', self.plotSize)
        self.canvas.axes.set_xlabel(xStatHuman)
        self.canvas.axes.set_ylabel(yStatHuman)
        """
        if self.plotSize == 'paper':
            fontsize = 10
            self.canvas.axes[0].set_xlabel(xStatHuman, fontsize=fontsize)
            self.canvas.axes[0].set_ylabel(yStatHuman, fontsize=fontsize)
        else:
            self.canvas.axes[0].set_xlabel(xStatHuman)
            self.canvas.axes[0].set_ylabel(yStatHuman)
        """

        # emit warnings
        self.signalSetStatusBar.emit(warningStr)

        # subplots_adjust
        # self.fig.canvas.draw_idle()
        self.fig.canvas.draw()

class plotState:
    def __init__(self, plotIndex : int):
        self._dict = {
            'Plot Index': plotIndex,  # will be set to 1,2,3,... on mpl canvas creation
            "X Statistic": 'Spike Time (s)',
            "Y Statistic": 'Spike Frequency (Hz)',
            'xStat': 'thresholdSec',
            'yStat': 'spikeFreq_hz',

            'Plot Type': 'Scatter Plot',
            'Data Type': 'All Spikes',  # ['All Spikes', 'File Mean']
            'Include No': False,
            "Hue": 'File  Number',  #'Unique Name',
            "Style": 'None',
            "Group By (Stats)": 'File Number',  #'Unique Name',

            'Legend': False,
            'Toolbar': False,  # mpl toolbar
            'Hover Info': False,
            # 'Dark Theme': False,

            'masterDf': None,
            'meanDf': None,  # for plotting
            'xDf': None,
            'yDf': None,

            'Marker Size': 6,  # mpl default is 6
            'Plot Size': 'paper',

            'xIsCategorical': False,
            'yIsCategorical': False,
            
            'selectionIndex': None,

        }

    def __getitem__(self, key):
        try:
            return self._dict[key]
        except (KeyError) as e:
            logger.error(f'did not find key "{key}", available keys are {self._dict.keys()}')

    def getState(self, key):
        try:
            return self._dict[key]
        except (KeyError) as e:
            logger.error(f'did not find key "{key}", available keys are {self._dict.keys()}')

    def setState(self, key, value):
        try:
            self._dict[key] = value
        except (KeyError) as e:
            logger.error(f'did not find key "{key}", available keys are {self._dict.keys()}')

    def incInt(self, key):
        """Increment an integer key value.
        """
        try:
            self._dict[key] += 1
        except (KeyError) as e:
            logger.error(f'did not find key "{key}", available keys are {self._dict.keys()}')
            return
        return self._dict[key]

    def decInt(self, key):
        """Decrement an integer key value.
        """
        try:
            self._dict[key] -= 1
            if self._dict[key] < 1:
                self._dict[key] = 0
        except (KeyError) as e:
            logger.error(f'did not find key "{key}", available keys are {self._dict.keys()}')
            return
        return self._dict[key]

class bScatterPlotMainWindow(QtWidgets.QMainWindow):
    # send_fig = QtCore.pyqtSignal(str)
    signalStateChange = QtCore.Signal(object)
    signalSelectFromPlot = QtCore.Signal(object)
    signalCancelSelection = QtCore.Signal()
    # signalMeanModelChange = QtCore.Signal(object)
    signal_xModelChange = QtCore.Signal(object)
    signal_yModelChange = QtCore.Signal(object)

    def __init__(
        self,
        path,
        categoricalList,
        # hueTypes,
        # analysisName,
        sortOrder=None,
        statListDict=None,
        #interfaceDefaults=None,
        masterDf=None,
        limitToCol=None,  # col like 'epoch' to create popup to limit to one value (like 0)
        parent=None,
    ):
        """
        path: full path to .csv file generated with reanalyze
        categoricalList: specify columns that are categorical
            would just like to use 'if column is string' but sometimes number like 1/2/3 need to be categorical
        # hueTypes:
        # analysisName: column used for group by
        sortOrder:
        statListDict: dict where keys are human readable stat names
                    that map onto 'yStat' to specify column in csv
        #interfaceDefaults: specify key/value in dict to set state of interface popups/etc
        masterDf: if not none then use it (rather than loading csv path)
                    used by main sanpy interface
        parent: not used, parent sanpy app

        todo: make pure text columns categorical
        todo: remove analysisName and add as 'groupby' popup from categorical columns
            depending on 'analysisName' popup, group differently in getMeanDf
        """
        super().__init__(parent)

        self._blockSlots = False
        self._darkTheme = False

        # is assigned when we select a plot
        self._plotState = None  #plotState()
        
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+w"), self)
        self.shortcut.activated.connect(self.myCloseAction)

        # bottom status bar
        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)

        # self.mplCursorHover = None

        self.buildMenus()

        # assigns self.masterDf
        # if masterDf is not None will use masterDf rather than loading path
        self.loadPath(path, masterDf=masterDf, categoricalList=categoricalList)

        # dec 2022
        self._limitToCol = limitToCol

        # statListDict is a dict with key=humanstat name and yStat=column name in csv
        # self.statListDict = sanpy.bAnalysisUtil.getStatList()
        # 20210305 done in loadPath()
        if statListDict is not None:
            self.statListDict = statListDict
            # append all categorical
            if categoricalList is not None:
                for categorical in categoricalList:
                    self.statListDict[categorical] = {"yStat": categorical}
                    self.statListDict[categorical] = {"name": categorical}
                    # we need both yStat and name !!!

        # statListDict now has categorical like 'File Number'
        # for k, v in self.statListDict.items():
        #     print("    ", k, v)

        """
        if statListDict is None:
            # build statListDict from columns of csv path
            self.statListDict = {}
            for colStr in self.masterDfColumns:
                self.statListDict[colStr] = {'yStat': colStr}
        else:
            self.statListDict = statListDict
        """

        # unique identifyer to group by
        # for sanpy this is 'analysisName', for bImPy this is xxx
        self.sortOrder = sortOrder

        self.whatWeArePlotting = None  # return from sns plot (all plots)
        self.scatterPlotSelection = None
        self.xDf = None  #
        self.yDf = None  #
        # self.plotDF = None  # df we are plotting (can be same as mean yDf)

        self.hueList = ["None"] + self.hueTypes  # prepend 'None'
        self.styleList = ["None"] + self.hueTypes  # prepend 'None'
        # self.groupByList = ['None'] + self.hueTypes  # we force a group by,
        self.groupByList = self.hueTypes  # we force a group by,
            # we always provide a raw tab which is group by None

        self.plotTypeList = [
                "Scatter Plot",
                "Scatter + Raw + Mean",
                "Regression Plot",
                "Line Plot",
                "Line + Markers",
                "Violin Plot",
                "Box Plot",
                "Raw + Mean Plot",
                "Histogram",
                "Cumulative Histogram",
            ]
        self.dataTypes = ["All Spikes", "File Mean"]

        self.doKDE = False  # fits on histogram plots

        self.plotSizeList = ["paper", "talk", "poster"]
        # self.plotSize = "paper"

        self.plotLayoutList = ['1x1', '1x2', '2x1', '2x2']
        self.plotLayoutType = "1x2"
        self.numPlots = 2
        self.plotUpdateList = [str(x+1) for x in range(self.numPlots)]

        self.updatePlot = None  # which plot to update 1,2,3,4

        self.buildUI()

        # ???
        self.updatePlotLayoutGrid()

        # cludge
        #self.myPlotCanvasList[0].signalSelectSquare.emit(0, None)  # slot_selectSquare(0)
        _plotNumber = 0
        _state = self.myPlotCanvasList[0].stateDict
        self.slot_selectSquare(_plotNumber, _state)

        # refresh interface based on state
        # called in slot_selectSquare()
        # self.refreshInterface()

        # bar = self.menuBar()
        # file = bar.addMenu("Load")

        # self.updatePlotSize() # calls update2()
        self.update2()

    def getBackendStat(self, humanStat : str) -> str:
        # convert from human readbale to backend
        try:
            return self.statListDict[humanStat]["name"]
        except KeyError as e:
            logger.error(f'Did not find human stat name:"{humanStat}"')

    def _mySetWindowTitle(self, windowTitle):
        """Required to interact with sanpyPlugin."""
        self.setWindowTitle(windowTitle)

    def _old__buildPlotOptionsLayout(self):
        hBoxLayout = QtWidgets.QHBoxLayout()

        hueList = ["None"] + self.hueTypes  # prepend 'None'
        hueDropdown = QtWidgets.QComboBox()
        hueDropdown.addItems(hueList)
        # if interfaceDefaults['Hue'] is not None:
        #     defaultIdx = _defaultDropdownIdx(hueList, interfaceDefaults['Hue'])
        # else:
        #     defaultIdx = 0
        defaultIdx = 0
        hueDropdown.setCurrentIndex(defaultIdx)  # 1 because we pre-pended 'None'
        hueDropdown.currentTextChanged.connect(self.updateHue)

        hBoxLayout.addWidget(hueDropdown)
        return hBoxLayout

    def _defaultDropdownIdx(self, keyList, name):
        # if name not in keyList, return 0
        theRet = 0
        try:
            theRet = keyList.index(name)
        except ValueError as e:
            logger.error(f'did not find "{name}"" in keyList: {keyList}')
            theRet = 0
        return theRet

    def refreshInterface(self):
        """Refresh based on state.

        We never own state, we get a pointer to state from myMplCanvas.
        """

        self._blockSlots = True

        defaultIdx = self._defaultDropdownIdx(self.hueList, self._plotState.getState("Hue"))
        self.hueDropdown.setCurrentIndex(defaultIdx)  # 1 because we pre-pended 'None'

        defaultIdx = self._defaultDropdownIdx(self.plotTypeList, self._plotState.getState("Plot Type"))
        self.typeDropdown.setCurrentIndex(defaultIdx)

        defaultIdx = self._defaultDropdownIdx(self.dataTypes, self._plotState.getState("Data Type"))
        self.dataTypeDropdown.setCurrentIndex(defaultIdx)

        self.includeNoCheckBox.setChecked(self._plotState['Include No'])


        defaultIdx = self._defaultDropdownIdx(self.hueList, self._plotState.getState("Style"))
        self.styleDropdown.setCurrentIndex(defaultIdx)  # 1 because we pre-pended 'None'

        defaultIdx = self._defaultDropdownIdx(self.groupByList, self._plotState.getState("Group By (Stats)"))
        self.groupByDropdown.setCurrentIndex(defaultIdx)  # 1 because we pre-pended 'None'

        #
        self.showLegendCheckBox.setChecked(self._plotState['Legend'])
        self.mplToolbar.setChecked(self._plotState['Toolbar'])
        self.hoverCheckbox.setChecked(self._plotState['Hover Info'])

        
        defaultIdx = self._defaultDropdownIdx(self.plotSizeList, self._plotState.getState("Plot Size"))
        self.plotSizeDropdown.setCurrentIndex(0) # paper

        # self.darkThemeCheckBox.setChecked(self._plotState['Dark Theme'])
        self.darkThemeCheckBox.setChecked(self._darkTheme)

        # table views of x/y stats
        xStatistic = self._plotState.getState("X Statistic")
        self.xStatTableView.setCurrentRow(xStatistic)

        yStatistic = self._plotState.getState("Y Statistic")
        self.yStatTableView.setCurrentRow(yStatistic)

        # table view of (xDf, yDf) in tabs
        xDf = self._plotState['xDf']
        self.xTableView.slotSwitchTableDf(xDf)
        yDf = self._plotState['yDf']
        self.yTableView.slotSwitchTableDf(yDf)
        
        self._blockSlots = False

    def buildUI(self):
        # if self._plotState['Dark Theme']:
        if self._darkTheme:
                plt.style.use("dark_background")

        # HBox for control and plot grid
        self.hBoxLayout = QtWidgets.QHBoxLayout(self)

        # this is confusing, beacaue we are a QMainWindow
        # we need to create a central widget, set its layout
        # and then set the central widget of self (QMainWindow)
        centralWidget = QtWidgets.QWidget()
        centralWidget.setLayout(self.hBoxLayout)
        self.setCentralWidget(centralWidget)

        # to hold popups, x/y stats list, and mean tables (tabs)
        self.leftVertLayout = QtWidgets.QVBoxLayout()
        
        self.layout = QtWidgets.QGridLayout()
        self.leftVertLayout.addLayout(self.layout)
        
        # self.hBoxLayout.addLayout(self.layout)
        self.hBoxLayout.addLayout(self.leftVertLayout)

        #
        # hue, to control colors in plot
        # hueList = ["None"] + self.hueTypes  # prepend 'None'
        self.hueDropdown = QtWidgets.QComboBox()
        self.hueDropdown.addItems(self.hueList)
        # defaultIdx = self._defaultDropdownIdx(hueList, self._plotState.getState("Hue"))
        # self.hueDropdown.setCurrentIndex(defaultIdx)  # 1 because we pre-pended 'None'
        self.hueDropdown.currentTextChanged.connect(self.updateHue)

        #
        # style, to control marker/lines in plot
        # styleList = ["None"] + self.hueTypes  # prepend 'None'
        self.styleDropdown = QtWidgets.QComboBox()
        self.styleDropdown.addItems(self.styleList)
        # defaultIdx = self._defaultDropdownIdx(hueList, self._plotState.getState("Style"))
        # self.styleDropdown.setCurrentIndex(defaultIdx)  # 1 because we pre-pended 'None'
        # style defaults to None
        # self.styleDropdown.setCurrentIndex(0)  # 1 because we pre-pended 'None'
        self.styleDropdown.currentTextChanged.connect(self.updateStyle)

        #
        # group by, to control grouping in table
        # todo: get 'None' implemented
        # groupByList = ['None'] + self.hueTypes # prepend 'None'
        self.groupByDropdown = QtWidgets.QComboBox()
        self.groupByDropdown.addItems(self.groupByList)
        # defaultIdx = self._defaultDropdownIdx(groupByList, self._plotState.getState("Group By (Stats)"))
        # self.groupByDropdown.setCurrentIndex(defaultIdx)  # 1 because we pre-pended 'None'
        self.groupByDropdown.currentTextChanged.connect(self.updateGroupBy)

        #
        # plot type
        self.typeDropdown = QtWidgets.QComboBox()
        self.typeDropdown.addItems(self.plotTypeList)
        # self.typeDropdown.setCurrentIndex(0)
        self.typeDropdown.currentTextChanged.connect(self.updatePlotType)

        #
        # data type to display (raw or mean)
        self.dataTypeDropdown = QtWidgets.QComboBox()
        self.dataTypeDropdown.setToolTip(
            "All Spikes is all spikes \n File Mean is the mean within each Hue"
        )
        self.dataTypeDropdown.addItems(self.dataTypes)
        # self.dataTypeDropdown.setCurrentIndex(0)
        self.dataTypeDropdown.currentTextChanged.connect(self.updateDataType)

        self.showLegendCheckBox = QtWidgets.QCheckBox("Legend")
        # self.showLegendCheckBox.setChecked(self._plotState['Legend'])
        self.showLegendCheckBox.stateChanged.connect(self.setShowLegend)

        # swap the sort order
        aName = "Swap Sort Order"
        swapSortButton = QtWidgets.QPushButton(aName)
        swapSortButton.clicked.connect(partial(self.on_button_click, aName))

        """
        kdeCheckBox = QtWidgets.QCheckBox('kde (hist)')
        kdeCheckBox.setChecked(self.doKDE)
        kdeCheckBox.stateChanged.connect(self.setKDE)
        """

        self.mplToolbar = QtWidgets.QCheckBox("Toolbar")
        # self.mplToolbar.setChecked(self._plotState['Toolbar'])
        self.mplToolbar.stateChanged.connect(self.setMplToolbar)

        self.hoverCheckbox = QtWidgets.QCheckBox("Hover Info")
        # hoverCheckbox.setChecked(self._plotState['Hover Info'])
        self.hoverCheckbox.stateChanged.connect(self.setHover)

        # work fine
        self.plotSizeDropdown = QtWidgets.QComboBox()
        self.plotSizeDropdown.setToolTip('Set size of fonts for paper, talk, or poster')
        self.plotSizeDropdown.addItems(self.plotSizeList)
        # self.plotSizeDropdown.setCurrentIndex(0) # paper
        self.plotSizeDropdown.currentTextChanged.connect(self.updatePlotSize)
        # self.plotSizeDropdown.setDisabled(True)

        # works fine
        self.darkThemeCheckBox = QtWidgets.QCheckBox('Dark Theme')
        # self.darkThemeCheckBox.setChecked(self._plotState['Dark Theme'])
        self.darkThemeCheckBox.stateChanged.connect(self.setTheme)
        # darkThemeCheckBox.setDisabled(True)
        # darkThemeCheckBox.setEnabled(False)

        # works fine
        self.plotLayoutDropdown = QtWidgets.QComboBox()
        self.plotLayoutDropdown.setToolTip('1, 2, or 4 plots')
        self.plotLayoutDropdown.addItems(self.plotLayoutList)
        self.plotLayoutDropdown.setCurrentIndex(3) #
        self.plotLayoutDropdown.currentTextChanged.connect(self.updatePlotLayout)

        _vLayoutOfControls = QtWidgets.QVBoxLayout()
        self.leftVertLayout.addLayout(_vLayoutOfControls)

        #
        _rowOne = QtWidgets.QHBoxLayout()
        _vLayoutOfControls.addLayout(_rowOne)

        aName = "Replot"
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        # self.layout.addWidget(aButton, 1, 0)
        _rowOne.addWidget(aButton, alignment=QtCore.Qt.AlignLeft)

        # not needed beccause we now clik plot to show red square
        # add back in so user can click a plot (like 1), select plot 2 and then plot with state of plot 1
        # self.plotUpdateList = ['1', '2', '3', '4']
        self.plotUpdateDropdown = QtWidgets.QComboBox()
        self.plotUpdateDropdown.setToolTip('Which plot to update')
        self.plotUpdateDropdown.addItems(self.plotUpdateList)
        self.plotUpdateDropdown.setCurrentIndex(0) #
        self.plotUpdateDropdown.currentIndexChanged.connect(self.updatePlotUpdate)

        _rowOne.addWidget(self.plotUpdateDropdown, alignment=QtCore.Qt.AlignLeft)
        _rowOne.addStretch()

        #
        _rowTwo0 = QtWidgets.QHBoxLayout()
        _vLayoutOfControls.addLayout(_rowTwo0)

        _rowTwo0.addWidget(QtWidgets.QLabel("Plot Type"), alignment=QtCore.Qt.AlignLeft)
        _rowTwo0.addWidget(self.typeDropdown, alignment=QtCore.Qt.AlignLeft)
        _rowTwo0.addWidget(QtWidgets.QLabel("Data Type"), alignment=QtCore.Qt.AlignLeft)
        _rowTwo0.addWidget(self.dataTypeDropdown, alignment=QtCore.Qt.AlignLeft)

        self.includeNoCheckBox = QtWidgets.QCheckBox("Include No")
        self.includeNoCheckBox.setToolTip('If checked, all plots and analysis will contain files flagged as include no.')
        self.includeNoCheckBox.stateChanged.connect(self.setIncludeNo)
        _rowTwo0.addWidget(self.includeNoCheckBox, alignment=QtCore.Qt.AlignLeft)

        _rowTwo0.addStretch()

        #
        _rowTwo = QtWidgets.QHBoxLayout()
        _vLayoutOfControls.addLayout(_rowTwo)

        # self.layout.addWidget(QtWidgets.QLabel("Hue"), 2, col)
        # self.layout.addWidget(self.hueDropdown, 2, col + 1)
        _rowTwo.addWidget(QtWidgets.QLabel("Hue"))
        _rowTwo.addWidget(self.hueDropdown)

        # self.layout.addWidget(QtWidgets.QLabel("Style"), 3, col)
        # self.layout.addWidget(self.styleDropdown, 3, col + 1)
        _rowTwo.addWidget(QtWidgets.QLabel("Style"))
        _rowTwo.addWidget(self.styleDropdown)

        # self.layout.addWidget(QtWidgets.QLabel("Group By (Stats)"), 4, col)
        # self.layout.addWidget(self.groupByDropdown, 4, col + 1)
        _rowTwo.addWidget(QtWidgets.QLabel("Group By (Stats)"))
        _rowTwo.addWidget(self.groupByDropdown)

        #
        _rowThree = QtWidgets.QHBoxLayout()
        _vLayoutOfControls.addLayout(_rowThree)

        _rowThree.addWidget(self.showLegendCheckBox)
        _rowThree.addWidget(self.mplToolbar)
        _rowThree.addWidget(self.hoverCheckbox)
        _rowThree.addWidget(swapSortButton)
        _rowThree.addWidget(self.plotSizeDropdown)
        _rowThree.addWidget(self.darkThemeCheckBox)

        _rowThree.addStretch()

        # self.layout.addWidget(QtWidgets.QLabel("Color"), 3, 0)
        # self.layout.addWidget(self.colorDropdown, 3, 1)

        #
        _rowFour = QtWidgets.QHBoxLayout()
        _vLayoutOfControls.addLayout(_rowFour)

        # markerSizeLayout = QtWidgets.QHBoxLayout()
        markerLabel = QtWidgets.QLabel('Marker Size')
        smallerMarkerButton = QtWidgets.QPushButton('-')
        smallerMarkerButton.clicked.connect(partial(self.on_button_click, 'smallerMarkerButton'))
        largerMarkerButton = QtWidgets.QPushButton('+')
        largerMarkerButton.clicked.connect(partial(self.on_button_click, 'largerMarkerButton'))

        _rowFour.addWidget(markerLabel)
        _rowFour.addWidget(smallerMarkerButton)
        _rowFour.addWidget(largerMarkerButton)
        _rowFour.addStretch()

        # works fine
        # self.layout.addWidget(QtWidgets.QLabel("Plot Size"), 4, 2)
        # self.layout.addWidget(self.plotSizeDropdown, 4, 3)
        # works fine
        # self.layout.addWidget(QtWidgets.QLabel("Plot Layout"), 4, 0) # out of order
        # self.layout.addWidget(self.plotLayoutDropdown, 4, 1)

        # self.layout.addWidget(QtWidgets.QLabel("Update Plot"), 5, 0) # out of order
        # self.layout.addWidget(self.plotUpdateDropdown, 5, 1)

        # nextRow = 6  # for text table
        # rowSpan = 1
        # colSpan = 5
        # self.layout.addWidget(self.canvas, 3, 0, rowSpan, colSpan)


        """
        self.myToolbar = QtWidgets.QToolBar()
        self.myToolbar.setFloatable(True)
        self.myToolbar.setMovable(True)
        self.tmpToolbarAction = self.myToolbar.addWidget(self.canvas)
        self.addToolBar(QtCore.Qt.RightToolBarArea, self.myToolbar)
        """

        #
        # table view of x stat
        _horzLayout = QtWidgets.QHBoxLayout()
        self.leftVertLayout.addLayout(_horzLayout)

        self.xStatTableView = myStatListWidget(
            myParent=self, headerStr="X-Stat", statList=self.statListDict
        )
        self.xStatTableView.signalStatSelection.connect(self.slot_setStatName)
        # xStatistic = self._plotState.getState("X Statistic")
        # self.xStatTableView.setCurrentRow(xStatistic)
        _horzLayout.addWidget(self.xStatTableView)

        # table view of y stat
        self.yStatTableView = myStatListWidget(
            myParent=self, headerStr="Y-Stat", statList=self.statListDict
        )
        self.yStatTableView.signalStatSelection.connect(self.slot_setStatName)
        # yStatistic = self._plotState.getState("Y Statistic")
        # self.yStatTableView.setCurrentRow(yStatistic)
        _horzLayout.addWidget(self.yStatTableView)

        #
        # tabs to show (raw, x, y) stat tables
        tabwidget = QtWidgets.QTabWidget()

        # hold main df database (imutable except for 'include'
        # table-view to insert into tab
        self.rawTableView = myTableView("All Spikes")
        self.rawTableView.clicked.connect(self.slotTableViewClicked)
        self.signalCancelSelection.connect(self.rawTableView.clearSelection)
        self.signalSelectFromPlot.connect(self.rawTableView.slotSelectRow)
        # never switch rawTableView model, dust update column 'include'
        # self.signalMeanModelChange.connect(self.rawTableView.slotSwitchTableModel)
        self.rawTableView.slotSwitchTableDf(self.masterDf)

        # self.xDf
        # table-view to insert into tab
        self.xTableView = myTableView("File Mean")
        self.xTableView.clicked.connect(self.slotTableViewClicked)
        self.signalCancelSelection.connect(self.xTableView.clearSelection)
        self.signalSelectFromPlot.connect(self.xTableView.slotSelectRow)
        # never switch rawTableView model, dust update column 'include'
        # self.signalMeanModelChange.connect(self.rawTableView.slotSwitchTableModel)
        #self.xTableView.slotSwitchTableDf(self.xDf)

        # self.yDf
        self.yTableView = myTableView("File Mean")
        # table-view to insert into tab
        self.yTableView.clicked.connect(self.slotTableViewClicked)
        self.signalCancelSelection.connect(self.yTableView.clearSelection)
        self.signalSelectFromPlot.connect(self.yTableView.slotSelectRow)
        # never switch rawTableView model, dust update column 'include'
        # self.signalMeanModelChange.connect(self.rawTableView.slotSwitchTableModel)
        #self.yTableView.slotSwitchTableDf(self.yDf)

        #
        # self.layout.addWidget(self.tableView, nextRow, 0, rowSpan, colSpan)
        tabwidget.addTab(self.xTableView, "X-Stats")
        tabwidget.addTab(self.yTableView, "Y-Stats")
        tabwidget.addTab(self.rawTableView, "Raw")
        # tabwidget.addTab(self.tableView, "Mean")
        # rowSpan = 1
        # colSpan = 5
        # self.layout.addWidget(
        #     tabwidget, nextRow, 0, rowSpan, colSpan
        # )  # add widget takes ownership
        self.leftVertLayout.addWidget(tabwidget)

        #
        # grid of plots (myMplCanvas)
        self.plotLayout = QtWidgets.QGridLayout()
        self.plotLayout.setContentsMargins(0, 0, 0, 0)
        self.plotLayout.setHorizontalSpacing(0)
        self.plotLayout.setVerticalSpacing(0)

        self.myPlotCanvasList : List[myMplCanvas] = [None] * 4

        # # ???
        # self.updatePlotLayoutGrid()

        # append
        self.hBoxLayout.addLayout(self.plotLayout)

    def slot_setStatName(self, headerStr, statName):
        """User clicked on a new stat in one of (X-Stat, Y-Stat).
        """
        logger.info(f'headerStr:{headerStr} statName:{statName}')
        backendStat = self.getBackendStat(statName)
        if headerStr == 'X-Stat':
            self._plotState.setState('X Statistic', statName)
            self._plotState.setState('xStat', backendStat)
            xIsCategorical = pd.api.types.is_string_dtype(self.masterDf[backendStat].dtype)
            self._plotState.setState("xIsCategorical", xIsCategorical)
        elif headerStr == 'Y-Stat':
            self._plotState.setState('Y Statistic', statName)
            self._plotState.setState('yStat', backendStat)
            yIsCategorical = pd.api.types.is_string_dtype(self.masterDf[backendStat].dtype)
            self._plotState.setState("yIsCategorical", yIsCategorical)
        else:
            logger.error(f'did not understand headerStr:{headerStr}')
            return
        
        self.update2()

    def updatePlotUpdate(self, plotNumber : int):
        """Respond to user selecting plot number combo box.
        
        Parameters
        ----------
        plotNumber : int
            The zero-based plot number.
        """
        logger.info(f'plotNumber:{plotNumber} {type(plotNumber)}')
        self.updatePlot = plotNumber

    def updatePlotLayoutGrid(self):
        """use this to switch between (1x, 1x2, 2x1, 2x2)
        """

        plotLayoutType = self.plotLayoutType  # 1x, 1x2, 2x1, 2x2

        logger.info(f'plotLayoutType:{plotLayoutType}')


        if plotLayoutType == "1x1":
            numPlots = 1
        elif plotLayoutType == "1x2":
            numPlots = 2
        elif plotLayoutType == "2x1":
            numPlots = 2
        elif plotLayoutType == "2x2":
            numPlots = 4

        self.plotUpdateList = [str(x+1) for x in range(numPlots)]

        # remove all widgets from self.plotLayout
        n = self.plotLayout.count()
        for i in range(n):
            item = self.plotLayout.itemAt(i)
            if item is None:
                logger.error('got None item at step {i}')
                continue
            widget = item.widget()
            logger.info(f'  updatePlotLayoutGrid() removing i:{i} item:{type(item)}')
            self.plotLayout.removeWidget(widget)
            # self.plotLayout.removeItem(item)

        # make df
        # state = self.getState()
        # state = self._plotState

        for i in range(numPlots):
            if i == 0:
                row = 0
                col = 0
            elif i == 1:
                if plotLayoutType == "1x2":
                    row = 0
                    col = 1
                elif plotLayoutType == "2x1":
                    row = 1
                    col = 0
                elif plotLayoutType == "2x2":
                    row = 0
                    col = 1
            elif i == 2:
                row = 1
                col = 0
            elif i == 3:
                row = 1
                col = 1
            #
            _plotState = plotState(plotIndex=i)
            _plotState.setState('masterDf', self.masterDf)
            oneCanvas = myMplCanvas(plotState=_plotState)
            oneCanvas.signalSetStatusBar.connect(self.slot_setStatusBar)
            #oneCanvas.myUpdate(self._plotState)  # initial plot
            
            self.signalCancelSelection.connect(oneCanvas.slotCancelSelection)
            self.myPlotCanvasList[i] = oneCanvas

            #
            self.plotLayout.addWidget(oneCanvas, row, col)

        # connect each canvas to all other canvas
        for i in range(numPlots):
            iCanvas = self.myPlotCanvasList[i]
            iCanvas.signalSelectSquare.connect(self.slot_selectSquare)
            iCanvas.signalSelectFromPlot.connect(self.slotSelectFromPlot)
            for j in range(numPlots):
                # if i==j:
                #    continue
                jCanvas = self.myPlotCanvasList[j]
                iCanvas.signalSelectFromPlot.connect(jCanvas.slot_selectInd)
                iCanvas.signalSelectSquare.connect(jCanvas.slot_selectSquare)

        #
        # select the first plot
        _plotState = self.myPlotCanvasList[0].stateDict
        self.myPlotCanvasList[0].signalSelectSquare.emit(0, _plotState)  # slot_selectSquare(0)

    def keyPressEvent(self, event):
        logger.info("keyPressEvent()")
        if event.key() == QtCore.Qt.Key_Escape:
            self.cancelSelection()
        elif event.type() == QtCore.QEvent.KeyPress and event.matches(
            QtGui.QKeySequence.Copy
        ):
            self.copySelection2()
        #
        event.accept()

    def copySelection2(self):
        """Copy xDf and yDf to clipboard.
        """
        dfCopy = None
        if self.xDf is not None:
            dfCopy = self.xDf.copy()
            # self.xDf.to_clipboard(sep='\t', index=False)
            # print('Copied to clipboard')
            # print(self.xDf)

        if self.yDf is not None:
            if dfCopy is None:
                dfCopy = self.yDf.copy()
            else:
                logger.info(f'y len:{len(self.yDf)}')
                # append row then yDf
                _emptyDf = pd.DataFrame([[' '] * dfCopy.shape[1]], columns=dfCopy.columns)
                dfCopy = pd.concat([dfCopy, _emptyDf, self.yDf])

            # self.yDf.to_clipboard(sep='\t', index=False)
            # print('Copied to clipboard')
            # print(self.yDf)
        #
        if dfCopy is not None:
            dfCopy.to_clipboard(sep="\t", index=False)
            # print(dfCopy.head())
            # print(dfCopy.tail())

        self.slot_setStatusBar('Table of X-Stats and Y-Stats copied to the clipboard')

    """
    def eventFilter(self, source, event):
        if (event.type() == QtCore.QEvent.KeyPress and
                        event.matches(QtGui.QKeySequence.Copy)):
            self.copySelection2()
            return True
        return super(bScatterPlotMainWindow, self).eventFilter(source, event)
    """

    def cancelSelection(self):
        self.signalCancelSelection.emit()
        # clear status bar
        self.slot_setStatusBar('')

    def _old_switchTableModel(self, newModel):
        """switch model for mean table (Self.xxx)
        """
        # print('bScatterPlotMainWindow._switchTableModel()')
        self.signalMeanModelChange.emit(newModel)

    def getState(self):
        """Refresh the mean DataFrame in the state.
        
        Call this when X/Y stat changes.
        """

        # xStat = self._plotState['xStat']
        # yStat = self._plotState['yStat']

        xDf, yDf, meanDf = self.getMeanDf()

        #self._plotState.setState("masterDf", self.masterDf)  # never changes
        self._plotState.setState("xDf", xDf)  # never changes
        self._plotState.setState("yDf", yDf)  # never changes
        self._plotState.setState("meanDf", meanDf)  # never changes

    def __old_getState(self):
        """Query all controls and create dict with state

        used by myMplCanvas.update()
        """
        stateDict = {}

        stateDict["dataType"] = self.dataType  # ['All spikes', 'File Mean']
        stateDict["groupByColumnName"] = self.groupByColumnName

        plotType = self.plotType
        stateDict["plotType"] = plotType

        xStatHuman, xStat = self.xStatTableView.getCurrentStat()
        yStatHuman, yStat = self.yStatTableView.getCurrentStat()

        stateDict["xStatHuman"] = xStatHuman
        stateDict["yStatHuman"] = yStatHuman
        # xStat = self.statListDict[xStatHuman]['yStat'] # statListDict always used yStat
        # yStat = self.statListDict[yStatHuman]['yStat']
        stateDict["xStat"] = xStat
        stateDict["yStat"] = yStat
        stateDict["xIsCategorical"] = pd.api.types.is_string_dtype(
            self.masterDf[xStat].dtype
        )
        stateDict["yIsCategorical"] = pd.api.types.is_string_dtype(
            self.masterDf[yStat].dtype
        )

        if self.hue == "None":
            # special case, we do not want None in self.statNameMap
            hue = None
        else:
            hue = self.hue
        stateDict["hue"] = hue

        stateDict['markerSize'] = self._markerSize

        if self.style == "None":
            # special case, we do not want None in self.statNameMap
            style = None
        else:
            style = self.style
        stateDict["style"] = style

        stateDict["darkTheme"] = self.darkTheme
        stateDict["showLegend"] = self.showLegend
        stateDict["doHover"] = self.doHover
        stateDict["showMplToolbar"] = self.showMplToolbar

        meanDf = self.getMeanDf(xStat, yStat)

        stateDict["masterDf"] = self.masterDf
        stateDict["meanDf"] = meanDf
        return stateDict

    def myCloseAction(self):
        print("myCloseAction()")

    def slot_setStatusBar(self, text : str):
        self.statusBar.showMessage(text)  # ,2000)

    """
    def copyTable(self):
        headerList = []
        for i in self.tableView.model().columnCount():
            headers.append(self.tableView.model().headerData(i, QtCore.Qt.Horizontal).toString()
        print('copyTable()')
        print('  headers:', headers)
        m = self.tableView.rowCount()
        n = self.tableView.columnCount()
        table = [[''] * n for x in range(m+1)]
        #for i in m:
    """

    """
    def copySelection(self):
        #self.copyTable()

        selection = self.tableView.selectedIndexes()
        if selection:
            rows = sorted(index.row() for index in selection)
            columns = sorted(index.column() for index in selection)
            rowcount = rows[-1] - rows[0] + 1
            colcount = columns[-1] - columns[0] + 1
            table = [[''] * colcount for _ in range(rowcount)]
            for index in selection:
                row = index.row() - rows[0]
                column = index.column() - columns[0]
                table[row][column] = index.data()
            stream = io.StringIO()
            csv.writer(stream).writerows(table)
            QtWidgets.QApplication.clipboard().setText(stream.getvalue())
    """

    def buildMenus(self):
        return
        
        loadAction = QtWidgets.QAction("Load database.xlsx", self)
        loadAction.triggered.connect(self.loadPathMenuAction)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu("&File")
        fileMenu.addAction(loadAction)

    def loadPathMenuAction(self):
        """
        prompt user for database.xlsx
        run reanalyze.py on that xlsx database
        load resultant _master.csv
        """
        print("loadPathMenuAction")

    def loadPath(self, path, masterDf=None, categoricalList=None):
        """
        path: full path to .csv file generated with reanalyze.py
        """
        # path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'
        if masterDf is not None:
            self.masterDf = masterDf
        else:
            if path.endswith(".csv"):
                self.masterDf = pd.read_csv(
                    path, header=0
                )  # , dtype={'ABF File': str})
            elif path.endswith(".xls"):
                self.masterDf = pd.read_excel(
                    path, header=0
                )  # , dtype={'ABF File': str})
            elif path.endswith(".xlsx"):
                self.masterDf = pd.read_excel(
                    path, header=0, engine="openpyxl"
                )  # , dtype={'ABF File': str})
            else:
                print(
                    "error: file type not supported. Expecting csv/xls/xlsx. Path:",
                    path,
                )

        # 20210426
        # combine some columns into new encoding
        # like, 'male+superior' as 'ms'
        # moved to reanalyze
        # want to move to reanalyze
        # but my base analysis does not have region/sex/condition etc
        if "Region" in self.masterDf.columns and "Sex" in self.masterDf.columns:
            tmpNewCol = "RegSex"
            self.masterDf[tmpNewCol] = ""
            for tmpRegion in ["Superior", "Inferior"]:
                for tmpSex in ["Male", "Female"]:
                    newEncoding = tmpRegion[0] + tmpSex[0]
                    regSex = self.masterDf[
                        (self.masterDf["Region"] == tmpRegion)
                        & (self.masterDf["Sex"] == tmpSex)
                    ]
                    regSex = (self.masterDf["Region"] == tmpRegion) & (
                        self.masterDf["Sex"] == tmpSex
                    )
                    print("newEncoding:", newEncoding, "regSex:", regSex.shape)
                    self.masterDf.loc[regSex, tmpNewCol] = newEncoding

        # sys.exit()

        self.masterDfColumns = self.masterDf.columns.to_list()

        #
        # try and guess categorical columns
        # if int64 and unique()<20 then assume it is category (works for date yyyymmdd)
        # print('loadPath() dtypes:')
        # print(self.masterDf.dtypes)
        if categoricalList is None:
            categoricalList = []
            for colStr, dtype in self.masterDf.dtypes.items():
                if dtype == object:
                    logger.info(f'adding to categoricalList colStr:{colStr} with type {dtype}')
                    categoricalList.append(colStr)
                elif dtype == np.int64:
                    unique = self.masterDf[colStr].unique()
                    numUnique = len(unique)
                    logger.info(f'adding to categoricalList colStr:{colStr} with type {dtype} numUnique:{numUnique}')
                    categoricalList.append(colStr)

        self.masterCatColumns = categoricalList
        self.hueTypes = categoricalList

        self.statListDict = {}
        for colStr in self.masterDfColumns:
            self.statListDict[colStr] = {"yStat": colStr}

        # not sure what this was for ???
        # 20210112, put back in if necc
        # self.masterCatColumns = ['Condition', 'File Number', 'Sex', 'Region', 'filename', 'analysisname']
        # self.masterCatColumns = self.categoricalList

        # todo: put this somewhere better
        self.setWindowTitle(path)

    def on_button_click(self, name):
        """ """
        logger.info(f"=== {name}")

        if name == "Replot":
            self.replot()

        elif name == "Swap Sort Order":
            # rotate the sort key to be able to sort by different keys, like 'sex' versus 'region'
            # print('  sortOrder was:', self.sortOrder)
            self.sortOrder = self.sortOrder[1:] + self.sortOrder[:1]
            # print('  sortOrder now:', self.sortOrder)
            self.slot_setStatusBar(f"Sort order is now: {self.sortOrder}")

        elif name == 'smallerMarkerButton':
            self._plotState.decInt('Marker Size')
            self.update2()
        elif name == 'largerMarkerButton':
            self._plotState.incInt('Marker Size')
            self.update2()

        else:
            logger.warning(f'Did not understand button: "{name}"')

    """
    def setKDE(self, state):
        # only used in histograms
        self.doKDE = state
        self.updateGlobal()
    """

    def setShowLegend(self, state):
        state = state > 0
        logger.info(f"setShowLegend() state: {state}")
        self._plotState.setState('Legend', state)
        self.updateGlobal()

    def setMplToolbar(self, state):
        # only used in histograms
        state = state > 0
        self._plotState.setState('Toolbar', state)
        self.updateGlobal()

    def setHover(self, state):
        # used in scatterplots and point plots
        state = state > 0
        self._plotState.setState('Hover Info', state)
        self.updateGlobal()

    def setTheme(self, state):
        state = state > 0
        self._plotState.setState('Toolbar', state)

        if state:
            plt.style.use("dark_background")
            # sns.set_context('talk')

        else:
            # print(plt.style.available)
            plt.rcParams.update(plt.rcParamsDefault)
            # sns.set_context('paper')

        # self.updateGlobal()
        n = len(self.myPlotCanvasList)
        for i in range(n):
            if self.myPlotCanvasList[i] is not None:
                self.myPlotCanvasList[i].updateTheme()

        ###
        return
        ###

        ###
        ###
        # remove
        # self.plotVBoxLayout.removeWidget(self.toolbar)
        # need this !!! removeWidget does not work
        # self.myToolbar.removeAction(self.tmpToolbarAction)
        self.hBoxLayout.removeWidget(self.canvas)
        self.canvas.setParent(None)

        self.fig = None  # ???
        self.mplToolbar = None
        self.canvas = None

        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        tmpAx = self.fig.add_subplot(111)  # self.ax1 not used
        self.axes = [tmpAx]
        self.cid = self.canvas.mpl_connect("pick_event", self.on_pick_event)
        # matplotlib navigation toolbar
        self.mplToolbar = NavigationToolbar2QT(
            self.canvas, self.canvas
        )  # params are (canvas, parent)
        self.hBoxLayout.addWidget(self.canvas)

        #
        # add a second plot
        if self.canvas2 is not None:
            self.hBoxLayout.removeWidget(self.canvas2)
            self.canvas2.setParent(None)
        self.canvas2 = myMplCanvas()
        self.signalStateChange.connect(self.canvas2.myUpdate)
        tmpState = self.getState()
        self.canvas2.myUpdate(tmpState)
        self.hBoxLayout.addWidget(self.canvas2)

        # original plot
        self.update2()

    def updatePlotLayout(self, value : str):
        """Set number of plots [1x, 1x2, 2x1, 2x2]
        """
        self.plotLayoutType = value

        self.updatePlotLayoutGrid()

        self.update2()

    def updatePlotSize(self, text):
        self._plotState.setState('Plot Size', text)
        sns.set_context(text)  # , font_scale=1.4)
        self.update2()

    def updatePlotType(self, text):
        if self._blockSlots:
            return
        self._plotState.setState('Plot Type', text)
        self.update2()

    def updateDataType(self, text):
        if self._blockSlots:
            return
        self._plotState.setState('Data Type', text)
        self.update2()

    def setIncludeNo(self, state):
        # only used in histograms
        state = state > 0
        self._plotState.setState('Include No', state)
        self.update2()

    def updateHue(self, text):
        if self._blockSlots:
            return
        self._plotState.setState('Hue', text)
        self.update2()

    def updateStyle(self, text):
        if self._blockSlots:
            return
        self._plotState.setState('Style', text)
        self.update2()

    def updateGroupBy(self, text):
        if self._blockSlots:
            return
        self._plotState.setState('Group By (Stats)', text)
        self.update2()  # todo: don't update plot, update table

    def updateLimitTo(self):
        logger.info("not implemented")

    """
    def updateColor(self):
        color = self.colorDropdown.currentText()
        self.color = color
        self.update2()
    """

    """
    def old_on_pick_event(self, event):
        try:
            print('on_pick_event() event:', event)
            print('event.ind:', event.ind)

            if len(event.ind) < 1:
                return
            spikeNumber = event.ind[0]
            print('  selected:', spikeNumber)

            # propagate a signal to parent
            #self.myMainWindow.mySignal('select spike', data=spikeNumber)
            #self.selectSpike(spikeNumber)
        except (AttributeError) as e:
            pass
    """

    def getMeanDf(self, verbose=False):
        # need to get all categorical columns from orig df
        # these do not change per file (sex, condition, region)

        includeNo = self._plotState['Include No']

        xStat = self._plotState['xStat']
        yStat = self._plotState['yStat']
        groupByColumnName = self._plotState['Group By (Stats)']
        
        logger.info(f'=== xStat:{xStat} yStat:{yStat} groupByColumnName:{groupByColumnName}')

        xIsCategorical = pd.api.types.is_string_dtype(self.masterDf[xStat].dtype)
        yIsCategorical = pd.api.types.is_string_dtype(self.masterDf[yStat].dtype)

        groupByNone = groupByColumnName == "None"

        aggList = ["count", "mean", "std", "sem", "median"]
        
        if includeNo:
            thisDf = self.masterDf
        else:
            thisDf = self.masterDf[self.masterDf['Include']=='yes']

        # xDf for table
        if xIsCategorical or groupByNone:
            self.xDf = None
        else:
            try:
                self.xDf = thisDf.groupby(groupByColumnName, as_index=False)[
                    xStat
                ].agg(aggList)
                self.xDf = self.xDf.reset_index()
                self.xDf.insert(1, "stat", xStat)  # column 1, in place
            except (KeyError) as e:
                logger.error(f'did not find "{groupByColumnName}" in columns -->> setting xDf to None')
                self.xDf = None

        # yDf for table
        if yIsCategorical or groupByNone:
            self.yDf = None
        else:
            try:
                self.yDf = thisDf.groupby(groupByColumnName, as_index=False)[
                    yStat
                ].agg(aggList)
                self.yDf = self.yDf.reset_index()
                self.yDf.insert(1, "stat", yStat)  # column 1, in place
            except (KeyError) as e:
                logger.error(f'did not find "{groupByColumnName}" in columns -->> setting yDf to None')
                self.yDf = None

        # meanDf for plotState (mpl canvas)
        if xStat == yStat:
            groupList = [xStat]
        else:
            groupList = [xStat, yStat]

        if groupByNone:
            meanDf = None
        else:
            try:
                meanDf = thisDf.groupby(groupByColumnName, as_index=False)[
                    groupList
                ].mean()
                meanDf = meanDf.reset_index()
            except (KeyError) as e:
                logger.error(f'did not find "{groupByColumnName}" in columns -->> setting meanDf to None')
                meanDf = None
                return self.xDf, self.yDf, meanDf

        #
        # 20210211 get median/std/sem/n
        # try and add median/std/sem/sem/n
        # if 0:
        #     tmpDf = self.masterDf.groupby(groupByColumnName, as_index=False)[
        #         groupList
        #     ].median()
        #     # print('tmpDf:', tmpDf)
        #     meanDf["median"] = tmpDf[groupByColumnName]

        """
        for catName in self.masterCatColumns:
            #if catName == 'analysisname':
            if catName == self.groupByColumnName:
                # this is column we grouped by, already in meanDf
                continue
            meanDf[catName] = ''
        """

        # for each row, update all categorical columns using self.masterCatColumns
        fileNameList = meanDf[groupByColumnName].unique()
        # print('  getMeanDf() updating all categorical columns for rows in fileNameList:')#, fileNameList)
        # print('    categorical columns are self.masterCatColumns:', self.masterCatColumns)
        for i, analysisname in enumerate(fileNameList):
            tmpDf = thisDf[self.masterDf[groupByColumnName] == analysisname]
            if len(tmpDf) == 0:
                logger.error(f'  got 0 length for analysisname:{analysisname}')
                continue
            # need to limit this to pre-defined catecorical columns
            for catName in self.masterCatColumns:
                # if i==0:
                #    print('analysisname:', analysisname, 'catName:', catName)

                # if catName == groupByColumnName:
                #    # this is column we grouped by, already in meanDf
                #    continue

                # find value of catName column from 1st instance in masterDf
                # if more than one unique value, don't put into table
                try:
                    numUnique = len(tmpDf[catName].unique())
                except (KeyError) as e:
                    logger.warning(f'did not find catName key "{catName}"')
                    continue
                if numUnique == 1:
                    # print('    updating categorical colum with catName:', catName)
                    catValue = tmpDf[catName].iloc[0]

                    theseRows = (
                        meanDf[groupByColumnName] == analysisname
                    ).tolist()
                    # if catName == groupByColumnName:
                    meanDf.loc[theseRows, catName] = catValue
                    if self.xDf is not None:
                        self.xDf.loc[theseRows, catName] = catValue
                    if self.yDf is not None:
                        self.yDf.loc[theseRows, catName] = catValue
                    # print('catName:', catName, 'catValue:', type(catValue), catValue)
                else:
                    logger.warning(f"catName: {catName} has {numUnique} unique values")
                    pass
                    # print(f'not adding {catName} to table, numUnique: {numUnique}')
        #
        # sort
        # meanDf = meanDf.sort_values(['Region', 'Sex', 'Condition'])
        if self.sortOrder is not None:
            logger.info(f'sorting by sortOrder:{self.sortOrder}')
            try:
                meanDf = meanDf.sort_values(self.sortOrder)
                if self.xDf is not None:
                    self.xDf = self.xDf.sort_values(self.sortOrder)
                if self.yDf is not None:
                    self.yDf = self.yDf.sort_values(self.sortOrder)
            except KeyError as e:
                logger.warning(f'sorting (2) failed with: {e}')
        #
        meanDf["index"] = [x + 1 for x in range(len(meanDf))]
        meanDf = meanDf.reset_index()

        # what was I using index for?
        if self.xDf is not None:
            self.xDf["index"] = [x + 1 for x in range(len(self.xDf))]
            self.xDf = self.xDf.reset_index()
        if self.yDf is not None:
            self.yDf["index"] = [x + 1 for x in range(len(self.yDf))]
            self.yDf = self.yDf.reset_index()

        # drop extra columns
        # modelMeanDf = meanDf.drop(['level_0'], axis=1)
        if self.xDf is not None and "level_0" in self.xDf.columns:
            self.xDf = self.xDf.drop(["level_0"], axis=1)
        if self.yDf is not None and "level_0" in self.yDf.columns:
            self.yDf = self.yDf.drop(["level_0"], axis=1)
        # we need to round for the table, but NOT the plot !!!!!
        # meanDf = meanDf.round(3)
        
        #
        if verbose:
            print("getMeanDf():")
            print(meanDf)
        #
        return self.xDf, self.yDf, meanDf

    def updateGlobal(self):
        """Update all plot globals like legend, toolbar, and hover.
        
        Do not replot
        """
        # state = self.getState()
        state = self._plotState
        
        n = len(self.myPlotCanvasList)
        for i in range(n):
            if self.myPlotCanvasList[i] is not None:
                self.myPlotCanvasList[i].myUpdateGlobal(state)

    def replot(self):
        self.update2()

        logger.info(f'selecting square:{self.updatePlot}')
        _plotState = self.myPlotCanvasList[self.updatePlot].stateDict
        self.myPlotCanvasList[self.updatePlot].signalSelectSquare.emit(self.updatePlot, _plotState)  # slot_selectSquare(0)

        # mpl canvas might have made a deep copy
        self._plotState = self.myPlotCanvasList[self.updatePlot].stateDict

        self.slot_setStatusBar('')

    def update2(self):
        """Update meanDf for a state.
        """
        if self.updatePlot is None:
            logger.error(f"Found no plots to update with self.updatePlot: {self.updatePlot}")
            self.slot_setStatusBar("Please select a plot to update")
            return

        logger.info(f'  plot: {self.updatePlot}')
        
        # this refreshes meanDF and determines if x/y stat is categorical
        self.getState()
        
        # state = self._plotState

        # update table model
        # meanDf = state.getState("meanDf")
        
        # modelMeanDf = meanDf.drop(['level_0'], axis=1)
        # self.myModel = myPandasModel(meanDf) # todo: don't need self.myModel

        # if meanDf is None:
        #     logger.error(f'got None meanDf')
        # else:
        #     myModel = myPandasModel(meanDf)  # todo: don't need self.myModel
        #     # print('calling _switchTableModel from update2() updateIndex:', updateIndex)
        #     self._switchTableModel(myModel)

        self.xTableView.slotSwitchTableDf(self.xDf)
        self.yTableView.slotSwitchTableDf(self.yDf)

        # update one plot corresponding to updateIndex
        self.myPlotCanvasList[self.updatePlot].myUpdate(self._plotState)

        # update all mpl canvas with globalstate (toolbar, hover, legend, etc)
        self.updateGlobal()

    def _old_getAnnotation(self, ind):
        # todo: replace with _getStatFromPlot

        if not np.issubdtype(ind, np.integer):
            print("getAnnotation() got bad ind:", ind, type(ind))
            return

        analysisName = self.plotDf.at[ind, self.groupByColumnName]
        index = self.plotDf.at[ind, "index"]
        try:
            region = self.plotDf.at[ind, "Region"]  # not all will have this
        except KeyError as e:
            region = "n/a"
        xVal = self.plotDf.at[ind, self.plotStatx]
        yVal = self.plotDf.at[ind, self.plotStaty]

        returnDict = {
            "index": index,
            "analysisName": analysisName,
            "region": region,
            "xVal": xVal,
            "yVal": yVal,
            #'plotDf': self.plotDf, # potentially very big
        }
        return returnDict

    # see: https://stackoverflow.com/questions/7908636/possible-to-make-labels-appear-when-hovering-over-a-point-in-matplotlib
    """
    def old_onHover(self, event):
        print('onHover:', type(event), 'inaxes:', event.inaxes)
        if event.inaxes == self.axes[0]:
            print('  in plotted axes')
        else:
            print('  not in plotted axes:', self.axes[0])

        print('  whatWeArePlotting:', type(self.whatWeArePlotting))
        cont, ind = self.whatWeArePlotting.contains(event)
        print('  cont:', cont)
        print('  ind:', ind)
        '''
        ind = event.ind # ind is a list []
        ind = ind[0]
        self._getStatFromPlot(ind)
        '''
    """

    '''
    def old_getStatFromPlot(self, ind):
        """
        get stat from self.plotDf from connected click/hover
        """
        analysisName = self.plotDf.at[ind, self.groupByColumnName]
        index = self.plotDf.at[ind, 'index']
        region = self.plotDf.at[ind, 'region']
        xVal = self.plotDf.at[ind, self.plotStatx]
        yVal = self.plotDf.at[ind, self.plotStaty]
        print(f'index:{index}, analysisName:{analysisName}, region:{region}, {self.plotStatx}:{xVal}, {self.plotStaty}:{yVal}')
    '''

    def slotSelectFromPlot(self, selectDict):
        """
        A point in one of plots was selected
        pass this to parent app
        """
        print("bScatterPlotMainWindow.slotSelectFromPlot() ", selectDict)

    def slot_selectSquare(self, plotNumber, stateDict):
        """Respond to user clicking a mpl plot widget.
        """
        if plotNumber == self.updatePlot:
            # already selected
            logger.warning(f'already showing plotNumber:{plotNumber}')
            return
        
        logger.info(f'plotNumber:{plotNumber}')
        
        self.updatePlot = plotNumber
        self._plotState = stateDict

        self.plotUpdateDropdown.setCurrentIndex(plotNumber)

        print('   Y-State is:', stateDict['Y Statistic'])

        # refresh interface based on new state
        self.refreshInterface()

    def slotTableViewClicked(self, clickedIndex):
        """Respond to signal self.tableView.clicked
        
        Parameters
        ----------
        clickedIndex: PyQt5.QtCore.QModelIndex
        """
        row = clickedIndex.row()
        model = clickedIndex.model()
        logger.info(f"row:{row} clickedIndex:{clickedIndex}")

        # select in plot
        # self._selectInd(row) # !!!! visually, index start at 1


def test():
    """
    20210112, extending this to work with any csv. Starting with nodes/edges from bimpy
    """

    # todo: using 'analysisname' for group by, I think I can also use 'File Number'
    statListDict = None  # list of dict mapping human readbale to column names
    masterDf = None
    interfaceDefaults = None

    # machine learning db
    if 0:
        # this is from mac laptop
        # path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'
        path = "/Users/cudmore/data/laura-ephys/SANdatabaseForMachineLearning.xlsx"
        analysisName = "File Number"
        # statListDict = None #sanpy.bAnalysisUtil.getStatList()
        categoricalList = ["LOCATION", "SEX", "File Number"]  # , 'File Name']
        hueTypes = ["LOCATION", "SEX", "File Number"]  # , 'File Name'] #, 'None']
        sortOrder = ["LOCATION", "SEX", "File Number"]

    # sanpy database
    if 0:
        # import sanpy
        # sys.path.append(os.path.join(os.path.dirname(sys.path[0]),'sanpy'))
        # import bAnalysisUtil
        # statListDict = bAnalysisUtil.statList
        import statlist

        statListDict = statlist.statList

        # this is from mac laptop
        # path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'
        path = "../examples/Superior vs Inferior database_master.csv"
        path = "/Users/cudmore/data/laura-ephys/Superior_Inferior_database_master_jan25.csv"
        path = (
            "/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv"
        )
        path = "/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master_20210402.csv"

        # path = 'data/Superior vs Inferior database_master_20210402.csv'
        path = "data/Superior vs Inferior database_master_20210402.csv"
        # path = '/Users/cudmore/data/laura-ephys/Superior_Inferior_database_master_jan25.csv'
        path = "data/Superior vs Inferior database_13_Feb_master.csv"
        analysisName = "analysisname"
        # statListDict = None #sanpy.bAnalysisUtil.getStatList()
        categoricalList = [
            "include",
            "condition",
            "region",
            "Sex",
            "RegSex",
            "File Number",
            "analysisname",
        ]  # , 'File Name']
        hueTypes = [
            "region",
            "sex",
            "RegSex",
            "condition",
            "File Number",
            "analysisname",
        ]  # , 'File Name'] #, 'None']
        sortOrder = ["region", "sex", "condition"]

        interfaceDefaults = {
            "Y Statistic": "Spike Frequency (Hz)",
            "X Statistic": "region",
            "Hue": "region",
            "Group By": "File Number",
        }
    # bimpy database
    if 0:
        path = "../examples/edges_db.csv"
        analysisName = "fileNumber"
        categoricalList = ["san", "region", "path", "file", "fileNumber", "nCon"]
        hueTypes = categoricalList
        sortOrder = ["san", "region"]

    # dualAnalysis database
    if 0:
        # grab our list of dict mapping human readable to .csv column names
        sys.path.append(os.path.join(os.path.dirname(sys.path[0]), "sanpy"))
        import bAnalysisUtil

        statListDict = bAnalysisUtil.statList

        path = "/Users/cudmore/Sites/SanPy/examples/dual-analysis/dualAnalysis_final_db.csv"
        analysisName = "fileNumber"  # # rows in .xlsx database, one recording per row
        # trial is 1a/1b/1c... trial withing cellNumber
        categoricalList = [
            "include",
            "region",
            "fileNumber",
            "cellNumber",
            "trial",
            "quality",
        ]
        hueTypes = categoricalList
        sortOrder = ["region"]

    # sparkmaster lcr database
    if 0:
        path = "/Users/cudmore/Sites/SanPy/examples/dual-analysis/lcr-database.csv"
        analysisName = "fileNumber"  # # rows in .xlsx database, one recording per row
        # trial is 1a/1b/1c... trial withing cellNumber
        categoricalList = ["quality", "region", "fileNumber", "dateFolder", "tifFile"]
        hueTypes = categoricalList
        sortOrder = ["region"]

    # lcr/vm analysis using lcrPicker.py
    if 0:
        # basePath = '/Users/cudmore/Sites/SanPy/examples/dual-analysis/'
        # path = basePath + 'dual-data/20210115/20210115__0002_lcrPicker.csv'
        # path = basePath + 'dual-data/20210115/20210115__0001_lcrPicker.csv'

        # output of lcrPicker.py ... mergeDatabase()
        path = "/Users/cudmore/Sites/SanPy/examples/dual-analysis/lcrPicker-db.csv"
        categoricalList = None
        hueTypes = None
        analysisName = "tifFile"
        sortOrder = None

    # merged sanpy+lcr pre spike slope
    # generated by dualAnalysis.py xxx()
    # usnig to compare lcr slope to edddr for fig 9
    if 0:
        path = "/Users/cudmore/Sites/SanPy/examples/dual-analysis/combined-sanpy-lcr-db.csv"
        statListDict = None
        categoricalList = None
        hueTypes = None
        analysisName = "filename"
        sortOrder = None

    if 1:
        path = "data"
        ad = sanpy.analysisDir(path, autoLoad=True)
        for row in range(len(ad)):
            ad.getAnalysis(row)
        masterDf = ad.pool_build()
        categoricalList = ["file", "File Number"]
        hueTypes = ["file", "File Number"]
        analysisName = "file"
        from sanpy.bAnalysisUtil import statList as statListDict

        sortOrder = ["file", "File Number"]
        interfaceDefaults = {
            "Y Statistic": "Spike Frequency (Hz)",
            "X Statistic": "Spike Number",
            "Hue": "file",
            "Group By": "file",
        }

    #
    app = QtWidgets.QApplication(sys.argv)

    ex = bScatterPlotMainWindow(
        path,
        categoricalList,
        hueTypes,
        analysisName,
        sortOrder,
        statListDict=statListDict,
        masterDf=masterDf,
        interfaceDefaults=interfaceDefaults,
    )
    ex.show()

    sys.exit(app.exec_())


def testDec2022():
    import sanpy.interface

    app = QtWidgets.QApplication(sys.argv)
    df = pd.read_csv("/Users/cudmore/Desktop/tmpDf-20221231.csv")
    ptp = sanpy.interface.plugins.plotToolPool(tmpMasterDf=df)
    ptp.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    # test()
    testDec2022()
