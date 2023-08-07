# created 20210212
import os, math

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtGui, QtWidgets

import sanpy.analysisDir
import sanpy.bDetection

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


def old_loadDatabase(path):
    """
    Load a csv/xls/xlsx file as a pandas dataframe.

    Args:
        path (Str): full path to .csv file generated with reanalyze.py

    Returns:
        pandas dataframe
    """
    masterDf = None
    if path is None:
        pass
    elif not os.path.isfile(path):
        print(f'error: bUtil.loadDatabase() did not find file: "{path}"')
    elif path.endswith(".csv"):
        masterDf = pd.read_csv(
            path, header=0, index_col=False
        )  # , dtype={'ABF File': str})
    elif path.endswith(".xls"):
        masterDf = pd.read_excel(path, header=0)  # , dtype={'ABF File': str})
    elif path.endswith(".xlsx"):
        masterDf = pd.read_excel(
            path, header=0, engine="openpyxl"
        )  # , dtype={'ABF File': str})
    else:
        print("error: file type not supported. Expecting csv/xls/xlsx. Path:", path)
    #
    return masterDf


def printDict(d, withType=False):
    for k, v in d.items():
        if withType:
            print(f"  {k}: {v} {type(v)}")
        else:
            print(f"  {k}: {v}")


class myTableView(QtWidgets.QTableView):
    """Table view to display list of files.

    TODO: Try and implement the first column (filename) as a frozen column.

    See: https://doc.qt.io/qt-5/qtwidgets-itemviews-frozencolumn-example.html
    """

    signalDuplicateRow = QtCore.pyqtSignal(object)  # row index
    signalDeleteRow = QtCore.pyqtSignal(object)  # row index
    # signalRefreshTabe = QtCore.pyqtSignal(object) # row index
    signalCopyTable = QtCore.pyqtSignal()
    signalFindNewFiles = QtCore.pyqtSignal()
    signalSaveFileTable = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """ """
        super(myTableView, self).__init__(parent)

        self.doIncludeCheckbox = False  # todo: turn this on
        # need a local reference to delegate else 'segmentation fault'
        # self.keepCheckBoxDelegate = myCheckBoxDelegate(None)

        # self.setFont(QtGui.QFont('Arial', 10))

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

        self.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
            | QtWidgets.QAbstractItemView.DoubleClicked
        )

        # removed mar 26 2023
        """
        rowHeight = 11
        fnt = self.font()
        fnt.setPointSize(rowHeight)
        self.setFont(fnt)
        self.verticalHeader().setDefaultSectionSize(rowHeight)
        """

        """
        p = self.palette()
        color1 = QtGui.QColor('#dddddd')
        color2 = QtGui.QColor('#ffffff')
        p.setColor(QtGui.QPalette.Base, color1)
        p.setColor(QtGui.QPalette.AlternateBase, color2)
        self.setPalette(p)
        self.setAlternatingRowColors(True)
        """

    # def keyPressEvent(self, event): #Reimplement the event here, in your case, do nothing
    #    return

    def mySetModel(self, model):
        """
        Set the model. Needed so we can show/hide columns
        """
        self.setModel(model)

        # print('---trying to hide columns')
        # self.hideColumn(1)
        # self.setColumnHidden(1,True);
        # self.setColumnHidden(1, True)
        # self.horizontalHeader().hideSection(1)

    """
    # trying to use this to remove tooltip when it comes up as empty ''
    def viewportEvent(self, event):
        logger.info('')
        return True
    """

    def contextMenuEvent(self, event):
        """Handle right mouse click"""
        contextMenu = QtWidgets.QMenu(self)

        duplicateRow = contextMenu.addAction("Duplicate Row")
        contextMenu.addSeparator()

        # deleteRow = contextMenu.addAction("Delete Row")
        # contextMenu.addSeparator()

        copyTable = contextMenu.addAction("Copy Table")
        contextMenu.addSeparator()

        findNewFiles = contextMenu.addAction("Sync With Folder")
        contextMenu.addSeparator()

        saveTable = contextMenu.addAction("Save Table")

        #
        action = contextMenu.exec_(self.mapToGlobal(event.pos()))
        # logger.info(f'  action:{action}')
        if action == duplicateRow:
            # print('  todo: duplicateRow')
            tmp = self.selectedIndexes()
            if len(tmp) > 0:
                selectedRow = tmp[0].row()
                self.signalDuplicateRow.emit(selectedRow)

        # elif action == deleteRow:
        #     #print('  todo: deleteRow')
        #     tmp = self.selectedIndexes()
        #     if len(tmp)>0:
        #         selectedRow = tmp[0].row()
        #         self.signalDeleteRow.emit(selectedRow)
        #     else:
        #         logger.warning('no selection?')

        elif action == copyTable:
            # print('  todo: copyTable')
            self.signalCopyTable.emit()

        elif action == findNewFiles:
            # print('  todo: findNewFiles')
            self.signalFindNewFiles.emit()

        elif action == saveTable:
            # print('  todo: saveTable')
            self.signalSaveFileTable.emit()

        else:
            logger.warning(f'action not taken "{action}"')


class pandasModel(QtCore.QAbstractTableModel):
    signalMyDataChanged = QtCore.pyqtSignal(object, object, object)
    """Emit on user editing a cell."""

    def __init__(self, data):
        """
        Data model for a pandas dataframe or sanpy.analysisDir.

        Args:
            data (dataframe or analysisDir): pandas dataframe or analysisDir
        """
        QtCore.QAbstractTableModel.__init__(self)

        self.isDirty = False

        # data is either DataFrame or analysisDir
        self.isAnalysisDir = False
        if isinstance(data, pd.core.frame.DataFrame):
            self.isAnalysisDir = False
        elif isinstance(data, sanpy.analysisDir):
            self.isAnalysisDir = True
        else:
            logger.error("Expecting data in (DataFrame, sanpy.analysisDir)")
        self._data = data

        # self.setSortingEnabled(True)

    """
    def modelReset(self):
        print('modelReset()')
    """

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parnet=None):
        return self._data.shape[1]

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.ToolTipRole:
                # removed
                # swapped sanpy.bDetection.defaultDetection to a class
                # do not want to instantiate every time
                """
                # get default value from bAnalysis
                defaultDetection = sanpy.bDetection.defaultDetection
                columnName = self._data.columns[index.column()]
                toolTip = QtCore.QVariant()  # empty tooltip
                try:
                    toolTip = str(defaultDetection[columnName]['defaultValue'])
                    toolTip += ': ' + defaultDetection[columnName]['description']
                except (KeyError):
                    pass
                return toolTip
                """
            elif role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole]:
                columnName = self._data.columns[index.column()]
                if self.isAnalysisDir and columnName == "I":
                    return ""

                # don't get col from index, get from name
                # retVal = self._data.iloc[index.row(), index.column()]
                # retVal = self._data.loc[index.row(), columnName]
                realRow = self._data.index[index.row()]
                # retVal = self._data.iloc[realRow, index.column()]
                retVal = self._data.loc[realRow, columnName]
                if isinstance(retVal, np.float64):
                    retVal = float(retVal)
                elif isinstance(retVal, np.int64):
                    retVal = int(retVal)
                elif isinstance(retVal, str) and retVal == "nan":
                    retVal = ""

                if isinstance(retVal, float) and math.isnan(retVal):
                    # don't show 'nan' in table
                    retVal = ""
                return retVal

            elif role == QtCore.Qt.CheckStateRole:
                columnName = self._data.columns[index.column()]
                realRow = self._data.index[index.row()]
                # retVal = self._data.iloc[index.row(), index.column()]
                retVal = self._data.loc[realRow, columnName]
                if columnName == "I":
                    if retVal:
                        return QtCore.Qt.Checked
                    else:
                        return QtCore.Qt.Unchecked
                return QtCore.QVariant()

            elif role == QtCore.Qt.FontRole:
                realRow = self._data.index[index.row()]
                columnName = self._data.columns[index.column()]
                if columnName == "L":
                    if self._data.isLoaded(realRow):  # or self._data.isSaved(realRow):
                        return QtCore.QVariant(QtGui.QFont("Arial", pointSize=32))
                elif columnName == "A":
                    if self._data.isAnalyzed(
                        realRow
                    ):  # or self._data.isSaved(realRow):
                        return QtCore.QVariant(QtGui.QFont("Arial", pointSize=32))
                elif columnName == "S":
                    if self._data.isSaved(realRow):
                        return QtCore.QVariant(QtGui.QFont("Arial", pointSize=32))
                return QtCore.QVariant()
            elif role == QtCore.Qt.ForegroundRole:
                if self.isAnalysisDir:
                    realRow = self._data.index[index.row()]
                    columnName = self._data.columns[index.column()]
                    if columnName == "L":
                        if self._data.isLoaded(realRow):
                            return QtCore.QVariant(QtGui.QColor("#4444EE"))
                    elif columnName == "A":
                        if self._data.analysisIsDirty(realRow):
                            # has been analyzed but not saved
                            return QtCore.QVariant(QtGui.QColor("#994444"))  # red
                        elif self._data.isAnalyzed(realRow):
                            return QtCore.QVariant(QtGui.QColor("#449944"))  # green
                    elif columnName == "S":
                        if self._data.isSaved(realRow):
                            return QtCore.QVariant(
                                QtGui.QColor("#999944")
                            )  # mustard yellow
                return QtCore.QVariant()
            elif role == QtCore.Qt.BackgroundRole:
                # set colors of alternating background
                # if index.row() % 2 == 0:
                #     return QtCore.QVariant(QtGui.QColor('#444444'))
                # else:
                #     return QtCore.QVariant(QtGui.QColor('#666666'))
                pass

        #
        return QtCore.QVariant()

    # def update(self, dataIn):
    #     print('  pandasModel.update() dataIn:', dataIn)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """
        Respond to user/keyboard edits.

        True if value is changed. Calls layoutChanged after update.
        Returns:
            False if value is not different from original value.
        """
        if index.isValid():
            if role == QtCore.Qt.EditRole:
                rowIdx = index.row()
                columnIdx = index.column()

                # use to check isEditable
                columnName = self._data.columns[columnIdx]
                if self.isAnalysisDir:
                    isEditable = self._data.columnIsEditable(columnName)
                    if not isEditable:
                        return False

                # in general, DO NOT USE iLoc, use loc as it is absolute (i,j)
                columnName = self._data.columns[index.column()]
                realRow = self._data.index[index.row()]
                v = self._data.loc[realRow, columnName]
                # logger.info(f'Existing value for column "{columnName}" is v: "{v}" {type(v)}')
                # logger.info(f'  proposed value:"{value}" {type(value)}')
                if isinstance(v, np.float64):
                    try:
                        if value == "":
                            value = np.nan
                        else:
                            value = float(value)
                    except ValueError as e:
                        logger.info("  No action -->> please enter a number")
                        # self.signalUpdateStatus.emit('Please enter a number')
                        return False

                # set
                # logger.info(f'  New value for column "{columnName}" is "{value}" {type(value)}')
                self._data.loc[realRow, columnName] = value
                # self._data.iloc[rowIdx, columnIdx] = value

                # emit change
                emitRowDict = self.myGetRowDict(realRow)
                self.signalMyDataChanged.emit(columnName, value, emitRowDict)

                self.isDirty = True
                return True
            elif role == QtCore.Qt.CheckStateRole:
                rowIdx = index.row()
                columnIdx = index.column()
                columnName = self._data.columns[index.column()]
                realRow = self._data.index[index.row()]
                logger.info(f"CheckStateRole column:{columnName} value:{value}")
                if columnName == "I":
                    self._data.loc[realRow, columnName] = value == 2
                    self.dataChanged.emit(index, index)
                    return QtCore.Qt.Checked

        #
        return QtCore.QVariant()

    def flags(self, index):
        if not index.isValid():
            logger.warning("index is not valid")

        rowIdx = index.row()
        columnIdx = index.column()

        # use to check isEditable
        try:
            columnName = self._data.columns[columnIdx]
        except IndexError as e:
            logger.warning(
                f"IndexError for columnIdx:{columnIdx} len:{len(self._data.columns)}"
            )
            print("self._data.columns:", self._data.columns)
            raise

        theRet = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        isEditable = False
        isCheckbox = False
        if self.isAnalysisDir:
            # columnsDict is a big dict, one key for each column, in analysisDir.sanpyColumns
            isEditable = self._data.columnIsEditable(columnName)
            isCheckbox = self._data.columnIsCheckBox(columnName)
        if isEditable:
            theRet |= QtCore.Qt.ItemIsEditable
        if isCheckbox:
            # logger.info(f'isCheckbox {columnIdx}')
            theRet |= QtCore.Qt.ItemIsUserCheckable
        #
        return theRet

        # flags |= QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsUserCheckable | Qt.ItemIsEnabled

    def headerData(self, col, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                try:
                    return self._data.columns[col]
                except IndexError as e:
                    logger.warning(
                        f"IndexError for col:{col} len:{len(self._data.columns)}, shape:{self._data.shape}"
                    )
                    # raise
            elif orientation == QtCore.Qt.Vertical:
                # this is to show pandas 'index' column
                return col

        return QtCore.QVariant()

    def sort(self, Ncol, order):
        # logger.info(f'Ncol:{Ncol} order:{order}')
        self.layoutAboutToBeChanged.emit()
        if self.isAnalysisDir:
            self._data.sort_values(Ncol, order)
        else:
            self._data = self._data.sort_values(
                self._data.columns[Ncol], ascending=not order
            )
        self.layoutChanged.emit()

    def myCopyTable(self):
        """Copy model data to clipboard.
        """
        dfCopy = self._data.copy()
        dfCopy.to_clipboard(sep="\t", index=False)

    def myGetValue(self, rowIdx, colStr):
        val = None
        if colStr not in self._data.columns:  #  columns is a list
            logger.error(f'Got bad column name: "{colStr}"')
        elif len(self._data) - 1 < rowIdx:
            logger.error(f"Got bad row:{rowIdx} from possible {len(self._data)}")
        else:
            val = self._data.loc[rowIdx, colStr]
        return val

    def myGetRowDict(self, rowIdx):
        """
        return a dict with selected row as dict (includes detection parameters)
        """
        theRet = {}
        for column in self._data.columns:
            theRet[column] = self.myGetValue(rowIdx, column)
        return theRet

    def myGetColumnList(self, col):
        # return all values in column as a list
        colList = self._data[col].tolist()
        return colList

    def myAppendRow(self, rowDict=None):
        # append one empty row
        newRowIdx = len(self._data)
        self.beginInsertRows(QtCore.QModelIndex(), newRowIdx, newRowIdx)

        if self.isAnalysisDir:
            # if using analysis dir, azll actions are in-place
            self._data.appendRow()
        else:
            df = self._data
            df = df.append(pd.Series(), ignore_index=True)
            df = df.reset_index(drop=True)
            self._data = df

        self.endInsertRows()

    def old_myDeleteRow(self, rowIdx):
        msg = QtWidgets.QMessageBox()
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        msg.setDefaultButton(QtWidgets.QMessageBox.Ok)
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText(f"Are you sure you want to delete row {rowIdx}?")
        msg.setWindowTitle("Delete Row")
        returnValue = msg.exec_()
        if returnValue == QtWidgets.QMessageBox.Ok:
            #
            #
            rowIdx = self._data.index[rowIdx]  # assume rows are sorted
            self.beginRemoveRows(QtCore.QModelIndex(), rowIdx, rowIdx)
            #
            if self.isAnalysisDir:
                # if using analysis dir, azll actions are in-place
                self._data.deleteRow(rowIdx)
            else:
                df = self._data
                df = df.drop([rowIdx])
                df = df.reset_index(drop=True)
                self._data = df
            #
            self.endRemoveRows()

    def myUnloadRow(self, rowIdx):
        """Unload raw data by setting column ['_ba'] = None"""
        rowIdx = self._data.index[rowIdx]  # assume rows are sorted
        # self._data.loc[rowIdx, '_ba'] = None
        if self.isAnalysisDir:
            # if using analysis dir, azll actions are in-place
            self._data.unloadRow(rowIdx)

            # we changed the model, we need to emit dataChanged
            indexStart = self.createIndex(rowIdx, 0)
            indexStop = self.createIndex(rowIdx + 1, 0)
            self.dataChanged.emit(indexStart, indexStop)

    def myRemoveFromDatabase(self, rowIdx):
        """Remove bAnalysis from h5 database"""
        rowIdx = self._data.index[rowIdx]  # assume rows are sorted
        # self.beginInsertRows(QtCore.QModelIndex(), rowIdx, rowIdx)
        if self.isAnalysisDir:
            # if using analysis dir, azll actions are in-place
            # self.beginResetModel()
            self._data.removeRowFromDatabase(rowIdx)
            # self.endResetModel()

            # we changed the model, we need to emit dataChanged
            indexStart = self.createIndex(rowIdx, 0)
            indexStop = self.createIndex(rowIdx + 1, 0)
            self.dataChanged.emit(indexStart, indexStop)
        # self.endInsertRows()

    def myDuplicateRow(self, rowIdx):
        rowIdx = self._data.index[rowIdx]  # assume rows are sorted
        self.beginInsertRows(QtCore.QModelIndex(), rowIdx + 1, rowIdx + 1)
        #
        # duplicate rowIdx

        if self.isAnalysisDir:
            df = self._data._df  # either Dataframe or analysisDir
            self._data.duplicateRow(rowIdx)
        else:
            # make copy
            rowDict = self.myGetRowDict(rowIdx)
            newIdx = rowIdx + 0.5
            dfRow = pd.DataFrame(rowDict, index=[newIdx])

            df = self._data  # either Dataframe or analysisDir

            # append dfRow to the end
            df = df.append(dfRow, ignore_index=True)

            # sort by file name
            df = df.sort_values(
                by=["File"], axis="index", ascending=True, inplace=False
            )
            df = df.reset_index(drop=True)
            #
            self._data = df
        #
        self.endInsertRows()

    def mySetRow(self, rowIdx, rowDict):
        """Only set keys already in self._data.columns"""
        rowIdx = self._data.index[rowIdx]  # assume rows are sorted
        # rowSeries = pd.Series(rowDict)
        # self._data.loc[rowIdx] = rowSeries
        # self._data = self._data.reset_index(drop=True)
        for k, v in rowDict.items():
            if k in self._data.columns:
                self._data.at[rowIdx, k] = v

    def mySaveDb(self, path):
        # print('pandasModel.mySaveDb() path:', path)
        # logger.info(f'Saving csv {path}')
        self._data.to_csv(path, index=False)
        self.isDirty = False

    """
    def saveHdf(self):
        if self.isAnalysisDir:
            self._data.saveHdf()
    """

    def mySave(self):
        if self.isAnalysisDir:
            self._data.save()

    def mySyncDfWithPath(self):
        if self.isAnalysisDir:
            self.beginResetModel()
            self._data.syncDfWithPath()
            self.endResetModel()

    def myUpdateLoadedAnalyzed(self, ba, rowIdx):
        if self.isAnalysisDir:
            rowIdx = self._data.index[rowIdx]  # assume rows are sorted
            self._data._updateLoadedAnalyzed(rowIdx)

            # we changed the model, we need to emit dataChanged
            indexStart = self.createIndex(rowIdx, 0)
            indexStop = self.createIndex(rowIdx + 1, 0)
            self.dataChanged.emit(indexStart, indexStop)

    def _old_mySetDetectionParams(self, rowIdx, cellType):
        """Set predefined detection paramers.

        For example: SA Node, Neuron, Subthreshold, etc
        """
        logger.info(f"rowIdx:{rowIdx} cellType:{cellType}")
        rowDict = self.myGetRowDict(rowIdx)
        # print('  [1] rowDict:', rowDict)
        # get defaults
        dDict = sanpy.bAnalysis.getDefaultDetection(cellType=cellType)
        for k, v in dDict.items():
            if k in rowDict.keys():
                rowDict[k] = v
        # print('  [2] rowDict:', rowDict)
        self.mySetRow(rowIdx, rowDict)
        # print(self._data._df['_ba'])

        # signal data change
        indexStart = self.createIndex(rowIdx, 0)
        indexStop = self.createIndex(rowIdx + 1, 0)
        self.dataChanged.emit(indexStart, indexStop)

        # detection widget needs to update (dvdtThreshold, mVThreshold, ...)
        # emitRowDict = self.myGetRowDict(rowIdx)
        self.signalMyDataChanged.emit(None, None, rowDict)

    '''
    def mySetColumns(self, columnsDict):
        """
        When used as a file table, set with: sanpy.analysisDir.sanpyColumns
        """
        self.sanpyColumns = columnsDict
    '''


# see: https://stackoverflow.com/questions/17748546/pyqt-column-of-checkboxes-in-a-qtableview
class old_myCheckBoxDelegate(QtWidgets.QItemDelegate):
    """
    A delegate that places a fully functioning QCheckBox cell of the column to which it's applied.
    """

    def __init__(self, parent):
        QtWidgets.QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        """
        Important, otherwise an editor is created if the user clicks in this cell.
        """
        return None

    def paint(self, painter, option, index):
        """
        Paint a checkbox without the label.
        """
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
        print("myCheckBoxDelegate.setModelData()")
        model.setData(index, 1 if int(index.data()) == 0 else 0, QtCore.Qt.EditRole)
