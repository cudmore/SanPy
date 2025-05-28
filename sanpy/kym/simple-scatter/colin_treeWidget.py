import sys
from functools import partial
from pprint import pprint

import pandas as pd

from PyQt5 import QtGui, QtCore, QtWidgets

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class KymTreeWidget(QtWidgets.QWidget):
    signalAllCellsOnOff = QtCore.pyqtSignal(object)  # bool
    """Turn all cell/roi on/off."""
    signalToggleCellID = QtCore.pyqtSignal(object)  # (list of dict {type, cell id, roi, value})
    """Toggle a cell on/off."""
    # signalToggleRoi = QtCore.pyqtSignal(object, object, object)  # (Cell ID, roi, bool)
    # """Toggle an ROI on/off."""
    signalPlotCellIDRoi = QtCore.pyqtSignal(object, object)  # (cell id, roi label)
    """On shift click, plot cell id roi (raw data.)"""

    def __init__(self, df:pd.DataFrame, parent = None):
        super().__init__(parent)

        self.df = df

        # headerItem  = QtWidgets.QTreeWidgetItem()
        # item    = QtWidgets.QTreeWidgetItem()

        self._roiQueue = []

        self._buildUI()

    def _buildUI(self):

        cellVLayout = QtWidgets.QVBoxLayout()
        self.setLayout(cellVLayout)

        hLayoutRow1 = QtWidgets.QHBoxLayout()
        cellVLayout.addLayout(hLayoutRow1)

        # All checkbox
        cellCheckBox = QtWidgets.QCheckBox('All')
        cellCheckBox.setChecked(True)
        cellCheckBox.stateChanged.connect(
            partial(self._on_cell_checkbox, 'All')
        )
        hLayoutRow1.addWidget(cellCheckBox)
        
        expandCheckbox = QtWidgets.QCheckBox('Expand')
        expandCheckbox.setChecked(True)
        expandCheckbox.stateChanged.connect(
            partial(self._on_cell_checkbox, 'Expand')
        )
        hLayoutRow1.addWidget(expandCheckbox)

        # tree widget
        self._treeWidget = QtWidgets.QTreeWidget()
        cellVLayout.addWidget(self._treeWidget)

        df = self.df
        cellIDs = df['Cell ID'].unique()
        for cellID in cellIDs:
            dfCellID = df[df['Cell ID']==cellID]
            roiLabels = dfCellID['ROI Number'].unique()

            parent = QtWidgets.QTreeWidgetItem(self._treeWidget)
            parent.setText(0, cellID)
            parent.setFlags(parent.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
            # parent.setCheckState(1, QtCore.Qt.Unchecked)
            parent.setCheckState(1, QtCore.Qt.Checked)
            parent._myName = 'Cell ID'

            # parent.itemChanged.connect(self.return_checked_headers)
            for roiLabel in roiLabels:
                child = QtWidgets.QTreeWidgetItem(parent)
                child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                child.setText(0, f'ROI {roiLabel}')
                child._myName = 'ROI Number'
                # child.setCheckState(0, QtCore.Qt.Unchecked)
                child.setCheckState(0, QtCore.Qt.Checked)
    
        # self._treeWidget.setSelectionMode(QtWidgets.QAbstractItemView.ContiguousSelection)
        # self._treeWidget.expandAll()
        # self._treeWidget.clearSelection()

        # when user clicks a checkbox
        self._treeWidget.itemChanged.connect(self.onItemChanged)
        # when user clicks a row (item)
        self._treeWidget.itemClicked.connect(self.onItemClicked)

    # @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def onItemChanged(self, item:QtWidgets.QTreeWidgetItem, col):
        """When user toggles a checkbox.
        
        PROBLEM:
        This is called multiple times and we can't replot for each -->> very slow
        
        Need some way to put these in a queue.
        """
        # logger.info(f'item:{item}')
        checked = item.checkState(col) in [1, 2]
        itemText = item.text(col)
        myName = item._myName
        
        # logger.info(f'myName:"{myName}" itemText:"{itemText} checked:{checked}')

        _col = 0

        myName = item._myName
        if myName == 'Cell ID':
            cellID = itemText

            # type, cell id, roi, value
            roiItem = {
                'type': 'Cell ID',
                'cellID': cellID,
                'roiLabel': None,
                'checked': checked,
            }
            self._roiQueue.append(roiItem)

            logger.info(f'-->> emit signalToggleCellID ')
            # for itemInQueue in self._roiQueue:
            #     print(f'  {itemInQueue}')

            self.signalToggleCellID.emit(self._roiQueue)
            # clear the queue
            self._roiQueue = []

        # we need to queue "ROI Number" until we get a cell ID!!!
        elif myName == 'ROI Number':
            parentText = item.parent().text(_col)
            cellID = parentText
            roiLabel = itemText  # in gui is 'roi n', we want n
            roiLabel = roiLabel.replace('ROI ', '')
            
            # append to event queue, will emit on 'cell id' (see above)
            roiItem = {
                'type': 'ROI Label',
                'cellID': cellID,
                'roiLabel': roiLabel,
                'checked': checked,
            }
            self._roiQueue.append(roiItem)

        else:
            print(f'did not understand item._myName:{myName}')

    # @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def onItemClicked(self, item:QtWidgets.QTreeWidgetItem, col):
        """User has selected a row (not a checkbox)."""
        itemText = item.text(col)

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        isShift = modifiers == QtCore.Qt.ShiftModifier

        if not isShift:
            return
        
        _col = 0

        myName = item._myName
        if myName == 'ROI Number':
            parentText = item.parent().text(_col)

            cellID = parentText

            cellID = parentText
            roiLabelStr = itemText.replace('ROI ', '')
            logger.info(f'-->> emit signalPlotCellIDRoi cellID:"{cellID}" roiLabelStr:"{roiLabelStr}"')
            self.signalPlotCellIDRoi.emit(cellID, roiLabelStr)

    def _on_cell_checkbox(self, name, value):
        """Handle cell checkbox changes
        """
        value = value == QtCore.Qt.Checked
        logger.info(f'name:{name} value: {value}')
        if name =='All':
            # this is a row selection, not checkbox selection
            # selectedItems = self._treeWidget.selectedItems()
            # print(selectedItems)

            # gui
            # turn off slots, just set the checkbox(s)
            self._treeWidget.blockSignals(True)
            items = get_all_items(self._treeWidget)
            for item in items:
                checkState = 2 if value else 0
                # item.blockSignals(True)
                item.setCheckState(0, checkState)
                # item.blockSignals(False)
            self._treeWidget.blockSignals(False)

            logger.info(f'-->> emit signalAllCellsOnOff value:{value}')
            self.signalAllCellsOnOff.emit(value)

        elif name == 'Expand':
            if value:
                self._treeWidget.expandAll()
            else:
                self._treeWidget.collapseAll()

# see: https://stackoverflow.com/questions/9986231/getting-a-qtreewidgetitem-list-again-from-qtreewidget
def get_subtree_nodes(tree_widget_item):
    """Returns all QTreeWidgetItems in the subtree rooted at the given node."""
    nodes = []
    nodes.append(tree_widget_item)
    for i in range(tree_widget_item.childCount()):
        nodes.extend(get_subtree_nodes(tree_widget_item.child(i)))
    return nodes

def get_all_items(tree_widget):
    """Returns all QTreeWidgetItems in the given QTreeWidget."""
    all_items = []
    for i in range(tree_widget.topLevelItemCount()):
        top_item = tree_widget.topLevelItem(i)
        all_items.extend(get_subtree_nodes(top_item))
    return all_items

def test_tree():
    import pandas as pd
    df = pd.read_csv('/Users/cudmore/colin_peak_summary_20250521.csv')

    app     = QtWidgets.QApplication (sys.argv)
    
    kymTreeWidget = KymTreeWidget(df)
    kymTreeWidget.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    test_tree()