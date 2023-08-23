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
from collections import OrderedDict
import traceback
import pandas as pd
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt  # abb 202012 added to set theme
import seaborn as sns
# import mplcursors  # popup on hover

# sysPath = os.path.dirname(sys.path[0])
# sysPath = os.path.join(sysPath, 'sanpy')
# print('bScatterPlotWidget2.py sysPath:', sysPath)
# sys.path.append(sysPath)

# print('os.getcwd():', os.getcwd())
# import sanpy
# import bUtil # from sanpy folder, for pandas model

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def old_loadDatabase(path):
    """
    path: full path to .csv file generated with reanalyze.py
    """
    # path = '/Users/cudmore/data/laura-ephys/Superior vs Inferior database_master.csv'
    masterDf = None
    if not os.path.isfile(path):
        print("eror: bUtil.loadDatabase() did not find file:", path)
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
    def __init__(self, data):
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


# class MainWindow(QtWidgets.QWidget):
myInterfaceDefaults = OrderedDict(
    {
        "X Statistic": None,
        "Y Statistic": None,
        "Hue": None,
        "Group By": None,
    }
)


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
        """
        only selecct if selectDict['dataType'] matches what we are showing
        """
        if self.dataType != selectDict["dataType"]:
            return

        print("slotSelectRow() selectDict:", selectDict)
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
        """
        set model from df
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


# class myMplCanvas(FigureCanvas):
class myMplCanvas(QtWidgets.QFrame):
    """
    hold an fig/plot canvas, in scatter plot we can have 1-4 of these
    """

    signalSelectFromPlot = QtCore.Signal(object)
    signalSelectSquare = QtCore.Signal(object, object)

    def __init__(self, plotNumber=None, parent=None):
        super(myMplCanvas, self).__init__(parent)  # FigureCanvas

        # self.plotType = None

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
        self.plotNumber = plotNumber
        self.stateDict = None
        self.plotDf = None
        self.whatWeArePlotting = None
        # self.mplCursorHover = None

        # needed to show canvas in widget
        self.layout = QtWidgets.QVBoxLayout()  # any will do

        self.fig = Figure(constrained_layout=True)

        self.canvas = FigureCanvas(self.fig)

        self.canvas.axes = self.fig.add_subplot(111)  # was this
        # self.canvas.axes = self.fig.add_axes([0.1, 0.1, 0.9, 0.9]) # [x, y, w, h]
        # gs1 = gridspec.GridSpec(1, 1)
        # gs1.tight_layout(self.fig, rect=[0.5, 0, 1, 1], h_pad=0.5)
        # self.canvas.axes = self.fig.add_subplot(gs1[0])

        self.cid2 = self.canvas.mpl_connect("pick_event", self.on_pick_event)

        self.scatterPlotSelection = None

        self.mplToolbar = NavigationToolbar2QT(
            self.canvas, self.canvas
        )  # params are (canvas, parent)
        self.mplToolbar.hide()  # initially hidden

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

    def buildUI(self):
        pass

    def mousePressEvent(self, event):
        print("myMplCanvas.mousePressEvent()")
        print(
            "  todo: set all controls to match the plot just clicked on using self.stateDict!!!"
        )
        # print('  stateDict:', self.stateDict)
        self.signalSelectSquare.emit(self.plotNumber, self.stateDict)

    def contextMenuEvent(self, event):
        print("myMplCanvas.contextMenuEvent()")
        contextMenu = QtWidgets.QMenu(self)
        saveAsAction = contextMenu.addAction("Save As...")
        action = contextMenu.exec_(self.mapToGlobal(event.pos()))
        if action == saveAsAction:
            print("todo: save as")
            self.fig.savefig("", dpi=600)

    def on_pick_event(self, event):
        try:
            print("myMplCanvas.on_pick_event() event:", event)
            print("  event.ind:", event.ind)

            if len(event.ind) < 1:
                return
            spikeNumber = event.ind[0]
            print("  selected:", spikeNumber)

            # propagate a signal to parent
            # self.myMainWindow.mySignal('select spike', data=spikeNumber)
            # self.selectSpike(spikeNumber)
        except AttributeError as e:
            pass

    def onPick(self, event):
        """
        when user clicks on a point in the graph

        todo: this makes perfect sense for scatter but maybe not other plots???
        """
        print("=== myMplCanvas.onPick()")  #' event:', type(event), event)
        line = event.artist

        # filter out clicks on 'Annotation' used by mplcursors
        try:
            # when Scatter, line is 'PathCollection', a list of (x,y)
            offsets = line.get_offsets()
        except AttributeError as e:
            return

        ind = event.ind  # ind is a list []
        if len(ind) == 0:
            return
        ind = ind[0]

        # ind is the ith element in (x,y) list of offsets
        # ind 10 (0 based) is index 11 (1 based) in table list
        print(f"  selected from plot ind:{ind}, offsets values are {offsets[ind]}")
        selectDict = self.getAnnotation(ind)

        # to do, just put copy of state dict ???
        selectDict["plotType"] = self.stateDict["plotType"]
        selectDict["dataType"] = self.stateDict["dataType"]
        #
        # emit
        print("  myMplCanvas.signalSelectFromPlot.emit()", selectDict)
        self.signalSelectFromPlot.emit(selectDict)

    def _selectInd(self, ind):
        """
        visually select a point in scatter plot
        """
        print("myMplCanvas._selectInd() ind:", ind)
        if ind > len(self.plotDf) - 1:
            return
        xVal = self.plotDf.at[ind, self.stateDict["xStat"]]
        yVal = self.plotDf.at[ind, self.stateDict["yStat"]]
        if self.scatterPlotSelection is not None:
            print("  scatterPlotSelection x:", xVal, "y:", yVal)
            self.scatterPlotSelection.set_data(xVal, yVal)
        self.fig.canvas.draw()

    def getAnnotation(self, ind):
        if not np.issubdtype(ind, np.integer):
            print("myMplCanvas.getAnnotation() got bad ind:", ind, type(ind))
            return

        xStat = self.stateDict["xStat"]
        yStat = self.stateDict["yStat"]
        groupByColumnName = self.stateDict["groupByColumnName"]

        analysisName = self.plotDf.at[ind, groupByColumnName]
        index = self.plotDf.at[ind, "index"]
        try:
            region = self.plotDf.at[ind, "Region"]  # not all will have this
        except KeyError as e:
            region = "n/a"
        xVal = self.plotDf.at[ind, xStat]
        yVal = self.plotDf.at[ind, yStat]

        returnDict = {
            "ind": ind,
            "index": index,
            "analysisName": analysisName,
            "region": region,
            "xVal": xVal,
            "yVal": yVal,
            #'plotDf': self.plotDf, # potentially very big
        }
        return returnDict

    def slotSelectSquare(self, plotNumber, stateDict):
        # print('myMplCanvas.slotSelectSquare()', plotNumber, 'self.plotNumber:', self.plotNumber)
        if plotNumber == self.plotNumber:
            self.setLineWidth(1)
        else:
            self.setLineWidth(0)

    def slotSelectInd(self, selectDict):
        if self.stateDict["plotType"] == selectDict["plotType"]:
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
        """
        redraw using stored self.state
        """
        self.myUpdate(stateDict=None)

    def myUpdateGlobal(self, stateDict):
        """
        update globals but do not plot
        """
        self.canvas.axes.legend().set_visible(stateDict["showLegend"])

        if stateDict["showMplToolbar"]:
            self.mplToolbar.show()
        else:
            self.mplToolbar.hide()

        # if stateDict["doHover"] and self.whatWeArePlotting is not None:
        #     self.mplCursorHover = mplcursors.cursor(self.whatWeArePlotting, hover=True)

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

        # elif not stateDict["doHover"]:
        #     # cancel mplCursorHover hover selection
        #     if self.mplCursorHover is not None:
        #         selections = self.mplCursorHover.selections
        #         if len(selections) == 1:
        #             self.mplCursorHover.remove_selection(selections[0])

        #
        # self.draw() # to update hover
        self.fig.canvas.draw()

    def myUpdate(self, stateDict=None):
        """
        update plot based on control interface
        """

        # store stateDict so we can replot on changing dark theme
        if stateDict is None and self.stateDict is not None:
            # re-use our stateDict
            stateDict = self.stateDict
        else:
            self.stateDict = stateDict.copy()

        dataType = stateDict["dataType"]
        hue = stateDict["hue"]
        groupByColumnName = stateDict["groupByColumnName"]

        plotType = stateDict["plotType"]
        # self.plotType = plotType

        xStatHuman = stateDict["xStatHuman"]
        yStatHuman = stateDict["yStatHuman"]

        xStat = stateDict["xStat"]
        yStat = stateDict["yStat"]

        """
        print('=== myMplCanvas.myUpdate()')
        print('  ', plotType)
        print('  ', 'xStatHuman:', xStatHuman, 'yStatHuman:', yStatHuman)
        print('  ', 'xStat:', xStat, 'yStat:', yStat)
        """

        xIsCategorical = stateDict["xIsCategorical"]
        yIsCategorical = stateDict["yIsCategorical"]

        masterDf = stateDict["masterDf"]
        meanDf = stateDict["meanDf"]

        self.plotDf = meanDf

        self.canvas.axes.clear()

        picker = 5
        if plotType in ["Scatter Plot", "Scatter + Raw + Mean"]:
            # scatter plot user selection
            (self.scatterPlotSelection,) = self.canvas.axes.plot(
                [], [], "oy", markersize=12, fillstyle="none"
            )

            # main scatter
            try:
                self.whatWeArePlotting = sns.scatterplot(
                    x=xStat,
                    y=yStat,
                    hue=hue,
                    data=meanDf,
                    ax=self.canvas.axes,
                    picker=picker,
                    zorder=0,
                )
            except ValueError as e:
                self.fig.canvas.draw()
                print('  EXCEPTION: in myUpdate() "Scatter Plot", exception is:')
                print("  ", e)
                print("  ", "hue:", hue)

            # sem in both x and y, pulling from masterDf
            if dataType == "File Mean" or plotType == "Scatter + Raw + Mean":
                # we need to do this for each hue???
                # if x or y is in categorical (e.g. a string) then do not do this ...
                if xIsCategorical or yIsCategorical:
                    pass
                else:
                    print(
                        "  grabbing mean +- sem for self.groupByColumnName:",
                        groupByColumnName,
                    )
                    color = "k"
                    xd = masterDf.groupby(groupByColumnName).mean()[xStat]
                    xerrd = masterDf.groupby(groupByColumnName).sem()[xStat]
                    yd = masterDf.groupby(groupByColumnName).mean()[yStat]
                    yerrd = masterDf.groupby(groupByColumnName).sem()[yStat]
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
                print("EXCEPTIONin Histogram:", e)

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

                    # g.legend().remove()
                    self.canvas.axes.legend().remove()

                    handles, labels = self.canvas.axes.get_legend_handles_labels()
                    l = self.canvas.axes.legend(
                        handles[0:2],
                        labels[0:2],
                        bbox_to_anchor=(1.05, 1),
                        loc=2,
                        borderaxespad=0.0,
                    )

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
                        zorder=10,
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
            print("  did not understand plot type:", plotType)

        #
        # update
        self.canvas.axes.figure.canvas.mpl_connect("pick_event", self.onPick)

        # self.mplCursorHover = None
        # if stateDict["doHover"] and self.whatWeArePlotting is not None:
        #     self.mplCursorHover = mplcursors.cursor(self.whatWeArePlotting, hover=True)

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
        # self.mySetStatusBar(warningStr)

        self.canvas.axes.spines["right"].set_visible(False)
        self.canvas.axes.spines["top"].set_visible(False)

        if not stateDict["showLegend"]:
            self.canvas.axes.legend().remove()

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

        # subplots_adjust
        # self.fig.canvas.draw_idle()
        self.fig.canvas.draw()


class bScatterPlotMainWindow(QtWidgets.QMainWindow):
    # send_fig = QtCore.pyqtSignal(str)
    signalStateChange = QtCore.Signal(object)
    signalSelectFromPlot = QtCore.Signal(object)
    signalCancelSelection = QtCore.Signal()
    signalMeanModelChange = QtCore.Signal(object)
    signal_xModelChange = QtCore.Signal(object)
    signal_yModelChange = QtCore.Signal(object)

    def __init__(
        self,
        path,
        categoricalList,
        hueTypes,
        analysisName,
        sortOrder=None,
        statListDict=None,
        interfaceDefaults=None,
        masterDf=None,
        parent=None,
    ):
        """
        path: full path to .csv file generated with reanalyze
        categoricalList: specify columns that are categorical
            would just like to use 'if column is string' but sometimes number like 1/2/3 need to be categorical
        hueTypes:
        analysisName: column used for group by
        sortOrder:
        statListDict: dict where keys are human readable stat names
                    that map onto 'yStat' to specify column in csv
        interfaceDefaults: specify key/value in dict to set state of interface popups/etc
        masterDf: if not none then use it (rather than loading csv path)
                    used by main sanpy interface
        parent: not used, parent sanpy app

        todo: make pure text columns categorical
        todo: remove analysisName and add as 'groupby' popup from categorical columns
            depending on 'analysisName' popup, group differently in getMeanDf
        """
        super(bScatterPlotMainWindow, self).__init__(parent)

        # self.keepCheckBoxDelegate = myCheckBoxDelegate(None)

        if interfaceDefaults is None:
            interfaceDefaults = myInterfaceDefaults
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+w"), self)
        self.shortcut.activated.connect(self.myCloseAction)

        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)

        # self.mplCursorHover = None

        self.buildMenus()

        # assigns self.masterDf
        # if masterDf is not None will use masterDf rather than loading path
        self.loadPath(path, masterDf=masterDf, categoricalList=categoricalList)

        # statListDict is a dict with key=humanstat name and yStat=column name in csv
        # self.statListDict = sanpy.bAnalysisUtil.getStatList()
        # 20210305 done in loadPath()
        if statListDict is not None:
            self.statListDict = statListDict
            # append all categorical
            if categoricalList is not None:
                for categorical in categoricalList:
                    self.statListDict[categorical] = {"yStat": categorical}
        """
        if statListDict is None:
            # build statListDict from columns of csv path
            self.statListDict = {}
            for colStr in self.masterDfColumns:
                self.statListDict[colStr] = {'yStat': colStr}
        else:
            self.statListDict = statListDict
        """

        # categoricalList = ['Condition', 'Sex', 'Region', 'File Number', 'File Name']
        # 20210305 done in load path
        """
        for categorical in categoricalList:
            self.statListDict[categorical] = {'yStat': categorical}
        # this was originally in self.load() ???
        self.masterCatColumns = categoricalList
        """

        """
        self.stateDict = {}
        self.stateDict['groupByColumnName'] = analysisName
        self.stateDict['sortOrder'] = sortOrder
        self.stateDict['hue'] = hue
        self.stateDict['darkTheme'] = True
        self.stateDict['doKDE'] = False
        self.stateDict['doHover'] = False
        self.stateDict['plotSize'] = 'paper'
        self.stateDict['showLegend'] = True
        self.stateDict['plotType'] = 'Scatter Plot'
        self.stateDict['dataType'] = 'File Mean'
        """

        # unique identifyer to group by
        # for sanpy this is 'analysisName', for bImPy this is xxx
        self.groupByColumnName = analysisName
        self.sortOrder = sortOrder

        # 20210112 moved up
        # self.loadPath(path)

        self.whatWeArePlotting = None  # return from sns scatter plot (all plots)
        self.scatterPlotSelection = None
        self.xDf = None  #
        self.yDf = None  #
        self.plotDF = None  # df we are plotting (can be same as mean yDf)
        # use this to get row on self.onPick
        self.plotStatx = None
        self.plotStaty = None

        # self.main_widget = QtWidgets.QWidget(self)

        # this is causing tons of problems/crashes
        if interfaceDefaults["Hue"] is not None:
            self.hue = interfaceDefaults["Hue"]
        else:
            self.hue = "None"  # self.hueTypes[0]

        self.darkTheme = False
        self.doKDE = False  # fits on histogram plots
        self.showMplToolbar = False  # fits on histogram plots

        # self.doHover = False

        self.plotSizeList = ["paper", "talk", "poster"]
        self.plotSize = "paper"
        self.plotLayoutList = ["1x", "1x2", "2x1", "2x2"]
        self.plotLayoutType = "2x2"
        self.updatePlot = None  # which plot to update 1,2,3,4

        self.showLegend = False
        self.plotType = "Scatter Plot"

        self.dataTypes = ["All Spikes", "File Mean"]
        self.dataType = "File Mean"  # (Raw, File Mean)

        self.buildUI(interfaceDefaults=interfaceDefaults)

        # bar = self.menuBar()
        # file = bar.addMenu("Load")

        self.show()

        # self.updatePlotSize() # calls update2()
        self.update2()

    def buildUI(self, interfaceDefaults):
        # if self.darkTheme:
        #     plt.style.use('dark_background')
        if self.darkTheme:
            plt.style.use("dark_background")
        else:
            plt.rcParams.update(plt.rcParamsDefault)

        # HBox for control and plot grid
        self.hBoxLayout = QtWidgets.QHBoxLayout(self)

        # this is confusing, beacaue we are a QMainWindow
        # we need to create a central widget, set its layout
        # and then set the central widget of self (QMainWindow)
        centralWidget = QtWidgets.QWidget()
        centralWidget.setLayout(self.hBoxLayout)
        self.setCentralWidget(centralWidget)

        # switch to 2x2
        """
        # allow 1-4 plots
        tmpNumRow = 1
        tmpNumCol = 1
        numPlot = tmpNumRow * tmpNumCol

        self.fig = Figure()
        self.fig.tight_layout()
        # don't use subplot, each plot will be its own widget using myMplCanvas
        self.axes = [self.fig.add_subplot(tmpNumRow, tmpNumCol, i+1) for i in range(numPlot)]
        self.canvas = FigureCanvas(self.fig) # what is added to pyqt interface
        self.cid = self.canvas.mpl_connect('pick_event', self.on_pick_event)
        # maybe use
        #self.toolbar = NavigationToolbar(self.canvas, self)
        self.mplToolbar = NavigationToolbar2QT(self.canvas, self.canvas) # params are (canvas, parent)

        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                  QtWidgets.QSizePolicy.Expanding)
        self.canvas.updateGeometry()
        """

        # to hold popups
        self.layout = QtWidgets.QGridLayout()
        self.hBoxLayout.addLayout(self.layout)

        def _defaultDropdownIdx(keyList, name):
            # if name not in keys, return 0
            theRet = 0
            try:
                theRet = keyList.index(name)
            except ValueError as e:
                print(
                    f'WARNING: _defaultDropdownIdx() did not find "{name}"" in keyList: {keyList}'
                )
                theRet = 0
            return theRet

        keys = list(self.statListDict.keys())
        # keys += self.hueTypes
        self.xDropdown = QtWidgets.QComboBox()
        self.xDropdown.addItems(keys)
        if interfaceDefaults["X Statistic"] is not None:
            defaultIdx = _defaultDropdownIdx(keys, interfaceDefaults["X Statistic"])
        else:
            defaultIdx = 0
        self.xDropdown.setCurrentIndex(defaultIdx)

        self.yDropdown = QtWidgets.QComboBox()
        self.yDropdown.addItems(keys)
        if interfaceDefaults["Y Statistic"] is not None:
            defaultIdx = _defaultDropdownIdx(keys, interfaceDefaults["Y Statistic"])
        else:
            defaultIdx = 0
        self.yDropdown.setCurrentIndex(defaultIdx)

        #
        # hue, to control colors in plot
        hueList = ["None"] + self.hueTypes  # prepend 'None'
        self.hueDropdown = QtWidgets.QComboBox()
        self.hueDropdown.addItems(hueList)
        if interfaceDefaults["Hue"] is not None:
            defaultIdx = _defaultDropdownIdx(hueList, interfaceDefaults["Hue"])
        else:
            defaultIdx = 0
        self.hueDropdown.setCurrentIndex(defaultIdx)  # 1 because we pre-pended 'None'
        self.hueDropdown.currentIndexChanged.connect(self.updateHue)

        #
        # group by, to control grouping in table
        # todo: get 'None' implemented
        # groupByList = ['None'] + self.hueTypes # prepend 'None'
        groupByList = self.hueTypes
        self.groupByDropdown = QtWidgets.QComboBox()
        self.groupByDropdown.addItems(groupByList)
        if interfaceDefaults["Group By"] is not None:
            defaultIdx = _defaultDropdownIdx(groupByList, interfaceDefaults["Group By"])
        else:
            defaultIdx = 0
        self.groupByDropdown.setCurrentIndex(
            defaultIdx
        )  # 1 because we pre-pended 'None'
        self.groupByDropdown.currentIndexChanged.connect(self.updateGroupBy)

        # color
        # colorTypes = ['Region', 'Sex', 'Condition', 'File Number'] #, 'File Name'] #, 'None']
        # self.color = 'Region'
        """
        self.color = self.colorTypes[0]
        self.colorDropdown = QtWidgets.QComboBox()
        self.colorDropdown.addItems(self.colorTypes)
        self.colorDropdown.setCurrentIndex(0)
        self.colorDropdown.currentIndexChanged.connect(self.updateColor)
        """

        self.typeDropdown = QtWidgets.QComboBox()
        self.typeDropdown.addItems(
            [
                "Scatter Plot",
                "Scatter + Raw + Mean",
                "Regression Plot",
                "Violin Plot",
                "Box Plot",
                "Raw + Mean Plot",
                "Histogram",
                "Cumulative Histogram",
            ]
        )
        self.typeDropdown.setCurrentIndex(0)

        self.dataTypeDropdown = QtWidgets.QComboBox()
        self.dataTypeDropdown.setToolTip(
            "All Spikes is all spikes \n File Mean is the mean within each analysis file"
        )
        self.dataTypeDropdown.addItems(self.dataTypes)
        self.dataTypeDropdown.setCurrentIndex(1)

        self.xDropdown.currentIndexChanged.connect(self.update2)
        self.yDropdown.currentIndexChanged.connect(self.update2)
        self.typeDropdown.currentIndexChanged.connect(self.updatePlotType)
        self.dataTypeDropdown.currentIndexChanged.connect(self.updateDataType)

        showLegendCheckBox = QtWidgets.QCheckBox("Legend")
        showLegendCheckBox.setChecked(self.showLegend)
        showLegendCheckBox.stateChanged.connect(self.setShowLegend)

        # swap the sort order
        swapSortButton = QtWidgets.QPushButton("Swap Sort Order")
        swapSortButton.clicked.connect(self.setSwapSort)
        # works fine
        """
        darkThemeCheckBox = QtWidgets.QCheckBox('Dark Theme')
        darkThemeCheckBox.setChecked(self.darkTheme)
        darkThemeCheckBox.stateChanged.connect(self.setTheme)
        darkThemeCheckBox.setDisabled(True)
        darkThemeCheckBox.setEnabled(False)
        """

        """
        kdeCheckBox = QtWidgets.QCheckBox('kde (hist)')
        kdeCheckBox.setChecked(self.doKDE)
        kdeCheckBox.stateChanged.connect(self.setKDE)
        """
        mplToolbar = QtWidgets.QCheckBox("Toolbar")
        mplToolbar.setChecked(self.showMplToolbar)
        mplToolbar.stateChanged.connect(self.setMplToolbar)

        # hoverCheckbox = QtWidgets.QCheckBox("Hover Info")
        # hoverCheckbox.setChecked(self.doHover)
        # hoverCheckbox.stateChanged.connect(self.setHover)

        # work fine
        """
        self.plotSizeDropdown = QtWidgets.QComboBox()
        self.plotSizeDropdown.setToolTip('Set size of fonts for paper, talk, or poster')
        self.plotSizeDropdown.addItems(self.plotSizeList)
        self.plotSizeDropdown.setCurrentIndex(0) # paper
        self.plotSizeDropdown.currentIndexChanged.connect(self.updatePlotSize)
        self.plotSizeDropdown.setDisabled(True)
        """

        # works fine
        """
        self.plotLayoutDropdown = QtWidgets.QComboBox()
        self.plotLayoutDropdown.setToolTip('1, 2, or 4 plots')
        self.plotLayoutDropdown.addItems(self.plotLayoutList)
        self.plotLayoutDropdown.setCurrentIndex(3) #
        self.plotLayoutDropdown.currentIndexChanged.connect(self.updatePlotLayout)
        self.plotLayoutDropdown.setDisabled(True)
        """

        # not needed beccause we now clik plot to show red square
        """
        self.plotUpdateList = ['1', '2', '3', '4']
        self.plotUpdateDropdown = QtWidgets.QComboBox()
        self.plotUpdateDropdown.setToolTip('Which plot to update')
        self.plotUpdateDropdown.addItems(self.plotUpdateList)
        self.plotUpdateDropdown.setCurrentIndex(0) # paper
        self.plotUpdateDropdown.currentIndexChanged.connect(self.updatePlotUpdate)
        """

        self.layout.addWidget(QtWidgets.QLabel("X Statistic"), 0, 0)
        self.layout.addWidget(self.xDropdown, 0, 1)
        self.layout.addWidget(QtWidgets.QLabel("Y Statistic"), 1, 0)
        self.layout.addWidget(self.yDropdown, 1, 1)
        self.layout.addWidget(QtWidgets.QLabel("Hue"), 2, 0)
        self.layout.addWidget(self.hueDropdown, 2, 1)
        self.layout.addWidget(QtWidgets.QLabel("Group By"), 3, 0)
        self.layout.addWidget(self.groupByDropdown, 3, 1)
        # self.layout.addWidget(QtWidgets.QLabel("Color"), 3, 0)
        # self.layout.addWidget(self.colorDropdown, 3, 1)
        #
        self.layout.addWidget(QtWidgets.QLabel("Plot Type"), 0, 2)
        self.layout.addWidget(self.typeDropdown, 0, 3)
        self.layout.addWidget(QtWidgets.QLabel("Data Type"), 1, 2)
        self.layout.addWidget(self.dataTypeDropdown, 1, 3)
        self.layout.addWidget(showLegendCheckBox, 2, 2)
        # works fine
        # self.layout.addWidget(darkThemeCheckBox, 2, 3)
        self.layout.addWidget(swapSortButton, 2, 3)
        self.layout.addWidget(mplToolbar, 3, 2)
        # self.layout.addWidget(hoverCheckbox, 3, 3)
        # works fine
        # self.layout.addWidget(QtWidgets.QLabel("Plot Size"), 4, 2)
        # self.layout.addWidget(self.plotSizeDropdown, 4, 3)
        # works fine
        # self.layout.addWidget(QtWidgets.QLabel("Plot Layout"), 4, 0) # out of order
        # self.layout.addWidget(self.plotLayoutDropdown, 4, 1)

        # self.layout.addWidget(QtWidgets.QLabel("Update Plot"), 5, 0) # out of order
        # self.layout.addWidget(self.plotUpdateDropdown, 5, 1)

        nextRow = 5  # for text table
        rowSpan = 1
        colSpan = 4
        # self.layout.addWidget(self.canvas, 3, 0, rowSpan, colSpan)

        #
        # grid of plots (myMplCanvas)
        self.plotLayout = QtWidgets.QGridLayout()
        self.plotLayout.setContentsMargins(0, 0, 0, 0)
        self.plotLayout.setHorizontalSpacing(0)
        self.plotLayout.setVerticalSpacing(0)

        self.myPlotCanvasList = [None] * 4

        self.updatePlotLayoutGrid()

        # append
        self.hBoxLayout.addLayout(self.plotLayout)

        """
        self.myToolbar = QtWidgets.QToolBar()
        self.myToolbar.setFloatable(True)
        self.myToolbar.setMovable(True)
        self.tmpToolbarAction = self.myToolbar.addWidget(self.canvas)
        self.addToolBar(QtCore.Qt.RightToolBarArea, self.myToolbar)
        """

        tabwidget = QtWidgets.QTabWidget()

        # hold main df database (imutable except for 'include'
        self.rawTableView = myTableView("All Spikes")
        self.rawTableView.clicked.connect(self.slotTableViewClicked)
        self.signalCancelSelection.connect(self.rawTableView.clearSelection)
        self.signalSelectFromPlot.connect(self.rawTableView.slotSelectRow)
        # never switch rawTableView model, dust update column 'include'
        # self.signalMeanModelChange.connect(self.rawTableView.slotSwitchTableModel)
        self.rawTableView.slotSwitchTableDf(self.masterDf)

        # self.xDf
        self.xTableView = myTableView("File Mean")
        self.xTableView.clicked.connect(self.slotTableViewClicked)
        self.signalCancelSelection.connect(self.xTableView.clearSelection)
        self.signalSelectFromPlot.connect(self.xTableView.slotSelectRow)
        # never switch rawTableView model, dust update column 'include'
        # self.signalMeanModelChange.connect(self.rawTableView.slotSwitchTableModel)
        self.xTableView.slotSwitchTableDf(self.xDf)

        # self.yDf
        self.yTableView = myTableView("File Mean")
        self.yTableView.clicked.connect(self.slotTableViewClicked)
        self.signalCancelSelection.connect(self.yTableView.clearSelection)
        self.signalSelectFromPlot.connect(self.yTableView.slotSelectRow)
        # never switch rawTableView model, dust update column 'include'
        # self.signalMeanModelChange.connect(self.rawTableView.slotSwitchTableModel)
        self.yTableView.slotSwitchTableDf(self.yDf)

        # todo: make this mean across yDf with stat test
        # mean table with pandas dataframe
        """
        self.tableView = myTableView('Not Sure')
        self.tableView.clicked.connect(self.slotTableViewClicked)
        self.signalCancelSelection.connect(self.tableView.clearSelection)
        self.signalSelectFromPlot.connect(self.tableView.slotSelectRow)
        self.signalMeanModelChange.connect(self.tableView.slotSwitchTableModel)
        """

        #
        # self.layout.addWidget(self.tableView, nextRow, 0, rowSpan, colSpan)
        tabwidget.addTab(self.rawTableView, "Raw")
        # tabwidget.addTab(self.tableView, "Mean")
        tabwidget.addTab(self.xTableView, "X-Stats")
        tabwidget.addTab(self.yTableView, "Y-Stats")
        self.layout.addWidget(tabwidget, nextRow, 0, rowSpan, colSpan)

    def updatePlotLayoutGrid(self):
        """
        use this to switch between (1x, 1x2, 2x1, 2x2)
        """

        print("updatePlotLayoutGrid()")
        plotLayoutType = self.plotLayoutType  # 1x, 1x2, 2x1, 2x2
        if plotLayoutType == "1x":
            numPlots = 1
        elif plotLayoutType == "1x2":
            numPlots = 2
        elif plotLayoutType == "2x1":
            numPlots = 2
        elif plotLayoutType == "2x2":
            numPlots = 4

        # remove all widgets from self.plotLayout
        n = self.plotLayout.count()
        for i in range(n):
            item = self.plotLayout.itemAt(i)
            if item is None:
                print("  warning: updatePlotLayoutGrid() got None item at step", i)
                continue
            widget = item.widget()
            print("  updatePlotLayoutGrid() removing i:", i, "item:", type(item))
            self.plotLayout.removeWidget(widget)
            # self.plotLayout.removeItem(item)

        state = self.getState()
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
            oneCanvas = myMplCanvas(plotNumber=i)
            oneCanvas.myUpdate(state)  # initial plot
            self.signalCancelSelection.connect(oneCanvas.slotCancelSelection)
            self.myPlotCanvasList[i] = oneCanvas

            #
            self.plotLayout.addWidget(oneCanvas, row, col)

        # connect each canvas to all other canvas
        for i in range(numPlots):
            iCanvas = self.myPlotCanvasList[i]
            iCanvas.signalSelectSquare.connect(self.slotSelectSquare)
            iCanvas.signalSelectFromPlot.connect(self.slotSelectFromPlot)
            for j in range(numPlots):
                # if i==j:
                #    continue
                jCanvas = self.myPlotCanvasList[j]
                iCanvas.signalSelectFromPlot.connect(jCanvas.slotSelectInd)
                iCanvas.signalSelectSquare.connect(jCanvas.slotSelectSquare)

        #
        # select the firsr plot
        self.myPlotCanvasList[0].signalSelectSquare.emit(0, None)  # slotSelectSquare(0)

    def keyPressEvent(self, event):
        print("keyPressEvent()")
        if event.key() == QtCore.Qt.Key_Escape:
            self.cancelSelection()
        elif event.type() == QtCore.QEvent.KeyPress and event.matches(
            QtGui.QKeySequence.Copy
        ):
            self.copySelection2()
        #
        event.accept()

    def copySelection2(self):
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
                # append row then yDf
                dfCopy.append(pd.Series(), ignore_index=True)
                dfCopy.append(self.yDf, ignore_index=True)
            # self.yDf.to_clipboard(sep='\t', index=False)
            # print('Copied to clipboard')
            # print(self.yDf)
        #
        if dfCopy is not None:
            dfCopy.to_clipboard(sep="\t", index=False)
            print(dfCopy)

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

    def _switchTableModel(self, newModel):
        """
        switch model for mean table (Self.xxx)
        """
        # print('bScatterPlotMainWindow._switchTableModel()')
        self.signalMeanModelChange.emit(newModel)

    def getState(self):
        """
        query all controls and create dict with state

        used by myMplCanvas.update()
        """
        stateDict = {}

        stateDict["dataType"] = self.dataType  # ['All spikes', 'File Mean']
        stateDict["groupByColumnName"] = self.groupByColumnName

        plotType = self.plotType
        stateDict["plotType"] = plotType

        xStatHuman = self.xDropdown.currentText()
        yStatHuman = self.yDropdown.currentText()
        stateDict["xStatHuman"] = xStatHuman
        stateDict["yStatHuman"] = yStatHuman
        xStat = self.statListDict[xStatHuman]["yStat"]  # statListDict always used yStat
        yStat = self.statListDict[yStatHuman]["yStat"]
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

        stateDict["darkTheme"] = self.darkTheme
        stateDict["showLegend"] = self.showLegend
        # stateDict["doHover"] = self.doHover
        stateDict["showMplToolbar"] = self.showMplToolbar

        if self.dataType == "All Spikes":
            meanDf = self.masterDf
            if self.sortOrder is not None:
                # need to sort so onPick works
                print("  ", "(1) sorting by self.sortOrder:", self.sortOrder)
                meanDf = meanDf.sort_values(self.sortOrder)

            # remove rows that have nan in our x or y stat
            meanDf = meanDf[~meanDf[xStat].isnull()]
            meanDf = meanDf[~meanDf[yStat].isnull()]
            meanDf = meanDf.reset_index()

        elif self.dataType == "File Mean":
            meanDf = self.getMeanDf(xStat, yStat)
        else:
            print("error in self.dataType:", self.dataType)

        stateDict["masterDf"] = self.masterDf
        stateDict["meanDf"] = meanDf
        return stateDict

    def myCloseAction(self):
        print("myCloseAction()")

    def mySetStatusBar(self, text):
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
                    print("colStr:", colStr, "is", dtype)
                    categoricalList.append(colStr)
                elif dtype == np.int64:
                    unique = self.masterDf[colStr].unique()
                    numUnique = len(unique)
                    print("colStr:", colStr, "is", dtype, "numUnique:", numUnique)
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

    def setSwapSort(self):
        """
        rotate the sort key to be able to sort by different keys, like 'sex' versus 'region'
        """
        # print('=== setSwapSort()')
        # print('  sortOrder was:', self.sortOrder)
        self.sortOrder = self.sortOrder[1:] + self.sortOrder[:1]
        # print('  sortOrder now:', self.sortOrder)
        self.mySetStatusBar(f"Sort order is now: {self.sortOrder}")

    def setShowLegend(self, state):
        print("setShowLegend() state:", state)
        self.showLegend = state
        self.updateGlobal()

    """
    def setKDE(self, state):
        # only used in histograms
        self.doKDE = state
        self.updateGlobal()
    """

    def setMplToolbar(self, state):
        # only used in histograms
        self.showMplToolbar = state
        self.updateGlobal()

    # def setHover(self, state):
    #     # used in scatterplots and point plots
    #     self.doHover = state
    #     # self.signalStateChange.emit(self.getState())
    #     self.updateGlobal()

    def setTheme(self, state):
        print("setTheme() state:", state)

        self.darkTheme = state
        if self.darkTheme:
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

    def updatePlotLayout(self):
        """
        set number of plots [1x, 1x2, 2x1, 2x2]
        """
        self.plotLayoutType = (
            self.plotLayoutDropdown.currentText()
        )  # ['paper', 'poster', 'talk']

        self.updatePlotLayoutGrid()

        self.update2()

    def updatePlotSize(self):
        self.plotSize = (
            self.plotSizeDropdown.currentText()
        )  # ['paper', 'poster', 'talk']
        sns.set_context(self.plotSize)  # , font_scale=1.4)
        self.updateGlobal()

    def updateHue(self):
        hue = self.hueDropdown.currentText()
        self.hue = hue
        # self.signalStateChange.emit(self.getState())
        self.update2()

    def updateGroupBy(self):
        self.groupByColumnName = self.groupByDropdown.currentText()
        self.update2()  # todo: don't update plot, update table

    """
    def updateColor(self):
        color = self.colorDropdown.currentText()
        self.color = color
        self.update2()
    """

    def updatePlotType(self):
        plotType = self.typeDropdown.currentText()
        self.plotType = plotType
        self.update2()

    def updateDataType(self):
        dataType = self.dataTypeDropdown.currentText()
        self.dataType = dataType
        self.update2()

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

    def getMeanDf(self, xStat, yStat, verbose=False):
        # need to get all categorical columns from orig df
        # these do not change per file (sex, condition, region)
        print("=== getMeanDf() xStat:", xStat, "yStat:", yStat)
        print("  self.groupByColumnName:", self.groupByColumnName)

        xIsCategorical = pd.api.types.is_string_dtype(self.masterDf[xStat].dtype)
        yIsCategorical = pd.api.types.is_string_dtype(self.masterDf[yStat].dtype)

        groupByNone = self.groupByColumnName == "None"

        aggList = ["count", "mean", "std", "sem", "median"]
        if xIsCategorical or groupByNone:
            self.xDf = None
        else:
            self.xDf = self.masterDf.groupby(self.groupByColumnName, as_index=False)[
                xStat
            ].agg(aggList)
            self.xDf = self.xDf.reset_index()
            self.xDf.insert(1, "stat", xStat)  # column 1, in place

        if yIsCategorical or groupByNone:
            self.yDf = None
        else:
            self.yDf = self.masterDf.groupby(self.groupByColumnName, as_index=False)[
                yStat
            ].agg(aggList)
            self.yDf = self.yDf.reset_index()
            self.yDf.insert(1, "stat", yStat)  # column 1, in place

        if xStat == yStat:
            groupList = [xStat]
        else:
            groupList = [xStat, yStat]
        if groupByNone:
            meanDf = None
        else:
            meanDf = self.masterDf.groupby(self.groupByColumnName, as_index=False)[
                groupList
            ].mean()
            meanDf = meanDf.reset_index()

        #
        # 20210211 get median/std/sem/n
        # try and add median/std/sem/sem/n
        if 0:
            tmpDf = self.masterDf.groupby(self.groupByColumnName, as_index=False)[
                groupList
            ].median()
            # print('tmpDf:', tmpDf)
            meanDf["median"] = tmpDf[self.groupByColumnName]

        """
        for catName in self.masterCatColumns:
            #if catName == 'analysisname':
            if catName == self.groupByColumnName:
                # this is column we grouped by, already in meanDf
                continue
            meanDf[catName] = ''
        """

        # for each row, update all categorical columns using self.masterCatColumns
        fileNameList = meanDf[self.groupByColumnName].unique()
        # print('  getMeanDf() updating all categorical columns for rows in fileNameList:')#, fileNameList)
        # print('    categorical columns are self.masterCatColumns:', self.masterCatColumns)
        for i, analysisname in enumerate(fileNameList):
            tmpDf = self.masterDf[self.masterDf[self.groupByColumnName] == analysisname]
            if len(tmpDf) == 0:
                logger.error(f'got 0 length for analysisname: {analysisname}')
                continue
            # need to limit this to pre-defined catecorical columns
            for catName in self.masterCatColumns:
                # if i==0:
                #    print('analysisname:', analysisname, 'catName:', catName)

                # if catName == self.groupByColumnName:
                #    # this is column we grouped by, already in meanDf
                #    continue

                # find value of catName column from 1st instance in masterDf
                # if more than one unique value, don't put into table
                numUnique = len(tmpDf[catName].unique())
                if numUnique == 1:
                    # print('    updating categorical colum with catName:', catName)
                    catValue = tmpDf[catName].iloc[0]

                    theseRows = (
                        meanDf[self.groupByColumnName] == analysisname
                    ).tolist()
                    # if catName == self.groupByColumnName:
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
            print("  ", "sorting by self.sortOrder:", self.sortOrder)
            try:
                meanDf = meanDf.sort_values(self.sortOrder)
                if self.xDf is not None:
                    self.xDf = self.xDf.sort_values(self.sortOrder)
                if self.yDf is not None:
                    self.yDf = self.yDf.sort_values(self.sortOrder)
            except KeyError as e:
                print("    ", "sorting (2) failed with:", e)
        #
        meanDf["index"] = [x + 1 for x in range(len(meanDf))]
        meanDf = meanDf.reset_index()
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
        return meanDf

    def updateGlobal(self):
        """
        update all plots
        do not replot
        """
        state = self.getState()
        n = len(self.myPlotCanvasList)
        for i in range(n):
            if self.myPlotCanvasList[i] is not None:
                self.myPlotCanvasList[i].myUpdateGlobal(state)

    def update2(self):
        # self.updatePlot is the plot to update 1,2,3,4
        updateIndex = self.updatePlot
        if updateIndex is None:
            print(
                "update2() found no plots to update with self.updatePlot:",
                self.updatePlot,
            )
            self.mySetStatusBar("Please select a plot to update")
            return

        state = self.getState()

        # update table model
        meanDf = state["meanDf"]
        # modelMeanDf = meanDf.drop(['level_0'], axis=1)
        # self.myModel = myPandasModel(meanDf) # todo: don't need self.myModel
        myModel = myPandasModel(meanDf)  # todo: don't need self.myModel
        # print('calling _switchTableModel from update2() updateIndex:', updateIndex)
        self._switchTableModel(myModel)

        self.xTableView.slotSwitchTableDf(self.xDf)
        self.yTableView.slotSwitchTableDf(self.yDf)

        # update plots
        n = len(self.myPlotCanvasList)
        for i in range(n):
            if i == updateIndex:
                if self.myPlotCanvasList[i] is not None:
                    self.myPlotCanvasList[i].myUpdate(state)

    def old_getAnnotation(self, ind):
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

    def slotSelectSquare(self, plotNumber, stateDict):
        print("bScatterPlotMainWindow.slotSelectSquare()", plotNumber)
        # print('  stateDict:', stateDict)
        print("  todo: fill in all interface using stateDict")
        self.updatePlot = plotNumber

    def slotTableViewClicked(self, clickedIndex):
        """
        Respond to signal self.tableView.clicked
        clickedIndex: PyQt5.QtCore.QModelIndex
        """
        row = clickedIndex.row()
        model = clickedIndex.model()
        print(
            "bScatterPlotMainWindow.slotTableViewClicked() row:",
            row,
            "clickedIndex:",
            clickedIndex,
        )

        # select in plot
        # self._selectInd(row) # !!!! visually, index start at 1


if __name__ == "__main__":
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
    if 1:
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
            "Condition",
            "Region",
            "Sex",
            "RegSex",
            "File Number",
            "analysisname",
        ]  # , 'File Name']
        hueTypes = [
            "Region",
            "Sex",
            "RegSex",
            "Condition",
            "File Number",
            "analysisname",
        ]  # , 'File Name'] #, 'None']
        sortOrder = ["Region", "Sex", "Condition"]

        interfaceDefaults = {
            "Y Statistic": "Spike Frequency (Hz)",
            "X Statistic": "Region",
            "Hue": "Region",
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

    sys.exit(app.exec_())
