import sys
import os
import subprocess

from PyQt5 import QtGui, QtCore, QtWidgets

from PyQt5.QtWidgets import (
    QWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QApplication,
    QCheckBox,
)
from PyQt5.QtCore import pyqtSignal, Qt
import pandas as pd

from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


class KymTreeWidget(QWidget):
    # Emitted when a cell (group of ROIs) is checked or unchecked
    cellToggled = pyqtSignal(str, str, int, bool)  # cell_id, condition, repeat, checked

    # Emitted when an individual ROI is checked or unchecked
    roiToggled = pyqtSignal(str, str, bool)  # cell_id, roi_number, checked

    # Emitted when the user selects a cell (row selected, not checkbox)
    cellSelected = pyqtSignal(str, str, int)  # cell_id, condition, repeat

    # Emitted when the user selects a ROI (row selected, not checkbox)
    roiSelected = pyqtSignal(
        str, str, int, int
    )  # cell_id, condition, repeat, roi_number

    # Emitted when the "Toggle All" checkbox is toggled (True = checked)
    toggleAllToggled = pyqtSignal(bool)

    # Emitted on right-click plot cell id (cell id, roi label)
    plotCellID = pyqtSignal(str, int)

    def __init__(self, dataframe, parent=None):
        super().__init__(parent)
        self.df = dataframe

        # re-wire right-click (for entire widget)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu)

        # Create Toggle All checkbox
        # self.toggleAllCheckbox = QCheckBox("Toggle All")
        # self.toggleAllCheckbox.setTristate(False)
        # self.toggleAllCheckbox.stateChanged.connect(self.toggleAll)

        # Create tree
        self.tree: QTreeWidget = QTreeWidget()
        self.tree.setHeaderLabels(["Cell ID / Condition / Repeat"])
        self.tree.itemChanged.connect(self.handleItemChanged)
        self.tree.itemSelectionChanged.connect(self.handleItemSelectionChanged)

        # Layout
        layout = QVBoxLayout()
        # layout.addWidget(self.toggleAllCheckbox)
        layout.addWidget(self.tree)
        self.setLayout(layout)

        self._populateTree()

    def _contextMenu(self, pos):
        logger.info('')

        selectedItems = self.tree.selectedItems()
        if len(selectedItems) == 0:
            logger.warning('no items selected')
            return

        item = selectedItems[0]  # one selected item

        contextMenu = QtWidgets.QMenu()

        contextMenu.addAction('Show Analysis Folder')
        _action = contextMenu.addAction('Plot Cell ID')
        if item.data(0, Qt.UserRole)[0] != "roi":
            _action.setEnabled(False)

        # show menu
        pos = self.mapToGlobal(pos)
        action = contextMenu.exec_(pos)
        if action is None:
            return

        actionText = action.text()

        if actionText == 'Show Analysis Folder':
            cell_id = item.data(0, Qt.UserRole)[1]
            condition = item.data(0, Qt.UserRole)[2]
            repeat = item.data(0, Qt.UserRole)[3]

            # find cell id row in df
            theseRows = (
                (self.df['Cell ID'] == cell_id)
                & (self.df['Condition'] == condition)
                & (self.df['Repeat'] == repeat)
            )
            df = self.df[theseRows]
            tifPath = df.iloc[0]['Path']
            tifFolder = os.path.split(tifPath)[0]
            logger.info(f'analysis folder is:{tifFolder}')

            # open in finder
            subprocess.run(['open', tifFolder])

        elif actionText == 'Plot Cell ID':
            if item.data(0, Qt.UserRole)[0] != "roi":
                # only for an roi (plots a kym roi across conditions)
                return

            cell_id = item.data(0, Qt.UserRole)[1]
            roi_number = item.data(0, Qt.UserRole)[4]
            self.plotCellID.emit(cell_id, roi_number)

    def _populateTree(self):
        # Group by Cell ID, Condition, and Repeat (each group represents a top-level item)
        
        grouped = self.df.groupby(["Cell ID", "Condition", "Repeat"])
        
        for (cell_id, condition, repeat), group in grouped:
            # region = group["Region"].iloc[0] if "Region" in group.columns else "Unknown"
            # cell_text = f"{cell_id} | Region: {region} | Condition: {condition}"
            cell_text = f"{cell_id} | {condition} | Repeat {repeat}"

            cell_item = QTreeWidgetItem([cell_text])
            cell_item.setFlags(
                cell_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable
            )
            cell_item.setCheckState(
                0, Qt.Checked if group["show_cell"].iloc[0] else Qt.Unchecked
            )
            cell_item.setData(0, Qt.UserRole, ("cell", cell_id, condition, repeat))
            # abb
            cell_item.setData(1, Qt.UserRole, ("cell", condition, repeat))

            for _, row in group.iterrows():
                num_peaks = (
                    row["Number of Peaks"] if "Number of Peaks" in row else "N/A"
                )
                polarity = row["Polarity"] if "Polarity" in row else "N/A"
                roi_text = f"ROI {row['ROI Label']} | {polarity} | Peaks: {num_peaks}"

                roi_item = QTreeWidgetItem([roi_text])
                roi_item.setFlags(
                    roi_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable
                )
                roi_item.setCheckState(
                    0, Qt.Checked if row["show_roi"] else Qt.Unchecked
                )
                roi_item.setData(
                    0,
                    Qt.UserRole,
                    ("roi", cell_id, condition, repeat, row['ROI Label']),
                )
                # roi_item.setData(1, Qt.UserRole, ("roi", cell_id, condition, repeat, row['ROI Label']))
                cell_item.addChild(roi_item)

            self.tree.addTopLevelItem(cell_item)
            cell_item.setExpanded(True)

    def handleItemChanged(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data is None:
            return

        self.tree.itemChanged.disconnect(self.handleItemChanged)

        if data[0] == "cell":
            cell_id = data[1]
            condition = data[2]
            repeat = data[3]
            checked = item.checkState(0) == Qt.Checked
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
            logger.info(f'cellToggled -->> emit with cell_id:"{cell_id}" condition:"{condition}" repeat:"{repeat}" checked:{checked}')
            self.cellToggled.emit(cell_id, condition, repeat, checked)

        elif data[0] == "roi":
            cell_id, condition, repeat, roi_number = data[1], data[2], data[3], data[4]
            checked = item.checkState(0) == Qt.Checked
            logger.info(f'roiToggled -->> emit with cell_id:"{cell_id}" roi_number:"{roi_number}" checked:{checked}')
            self.roiToggled.emit(cell_id, roi_number, checked)

            # Update parent state based on children's state
            parent = item.parent()
            if parent:
                all_checked = all(
                    parent.child(i).checkState(0) == Qt.Checked
                    for i in range(parent.childCount())
                )
                all_unchecked = all(
                    parent.child(i).checkState(0) == Qt.Unchecked
                    for i in range(parent.childCount())
                )
                if all_checked:
                    parent.setCheckState(0, Qt.Checked)
                elif all_unchecked:
                    parent.setCheckState(0, Qt.Unchecked)
                else:
                    parent.setCheckState(0, Qt.PartiallyChecked)

        self.tree.itemChanged.connect(self.handleItemChanged)

    def handleItemSelectionChanged(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        data = item.data(0, Qt.UserRole)
        if data is None:
            return

        if data[0] == "cell":
            # dataCondition = item.data(1, Qt.UserRole)
            cell_id = data[1]
            condition = data[2]
            repeat = data[3]
            self.cellSelected.emit(cell_id, condition, repeat)

        elif data[0] == "roi":
            # (cell id, condition, repeat, roi)
            cellID = data[1]
            condition = data[2]
            repeat = data[3]
            roiNumber = data[4]
            self.roiSelected.emit(cellID, condition, repeat, roiNumber)

    def toggleAll(self, state):
        """Toggles all tree items on/off based on the checkbox state."""
        self.tree.itemChanged.disconnect(self.handleItemChanged)

        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            parent.setCheckState(0, Qt.Checked if state == Qt.Checked else Qt.Unchecked)
            for j in range(parent.childCount()):
                child = parent.child(j)
                child.setCheckState(
                    0, Qt.Checked if state == Qt.Checked else Qt.Unchecked
                )

        self.tree.itemChanged.connect(self.handleItemChanged)
        self.toggleAllToggled.emit(state == Qt.Checked)


# Example usage
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Sample data
    df = pd.DataFrame(
        {
            'Cell ID': ['Cell1', 'Cell1', 'Cell2', 'Cell2', 'Cell2'],
            'ROI Label': [1, 2, 1, 2, 3],
            'accept cell': [True, True, False, False, False],
            'accept roi': [True, False, True, False, True],
            'Number of Spikes': [5, 3, 7, 0, 2],
            'Region': ['CA1', 'CA1', 'CA3', 'CA3', 'CA3'],
            'Condition': ['Control', 'Control', 'Treated', 'Treated', 'Stimulated'],
            'Repeat': [1, 1, 1, 2, 1],
            'show_cell': [True, True, False, False, False],
            'show_roi': [True, False, True, False, True],
        }
    )

    widget = KymTreeWidget(df)

    def on_cell_toggled(cell_id, condition, repeat, state):
        print(
            f"Cell {cell_id} in Condition {condition} and Repeat {repeat} toggled to {state}"
        )

    def on_roi_toggled(cell_id, roi, state):
        print(f"ROI {roi} in Cell {cell_id} toggled to {state}")

    def on_cell_selected(cell_id, condition, repeat):
        print(f"Selected Cell: {cell_id} in Condition {condition} and Repeat {repeat}")

    def on_roi_selected(cell_id, condition, repeat, roi):
        print(
            f"Selected ROI {roi} in Cell {cell_id} in Condition {condition} and Repeat {repeat}"
        )

    def on_toggle_all(state):
        print(f"'Toggle All' checkbox toggled to {state}")

    widget.cellToggled.connect(on_cell_toggled)
    widget.roiToggled.connect(on_roi_toggled)
    widget.cellSelected.connect(on_cell_selected)
    widget.roiSelected.connect(on_roi_selected)
    widget.toggleAllToggled.connect(on_toggle_all)

    widget.show()
    sys.exit(app.exec_())
