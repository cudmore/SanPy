import sys

from PyQt5.QtWidgets import (
    QWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QApplication, QCheckBox
)
from PyQt5.QtCore import pyqtSignal, Qt
import pandas as pd

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class KymTreeWidget(QWidget):
    # Emitted when a cell (group of ROIs) is checked or unchecked
    cellToggled = pyqtSignal(str, bool)

    # Emitted when an individual ROI is checked or unchecked
    roiToggled = pyqtSignal(str, int, bool)

    # Emitted when the user selects a cell (row selected, not checkbox)
    cellSelected = pyqtSignal(str)

    # Emitted when the user selects a ROI (row selected, not checkbox)
    roiSelected = pyqtSignal(str, int)

    # Emitted when the "Toggle All" checkbox is toggled (True = checked)
    toggleAllToggled = pyqtSignal(bool)

    def __init__(self, dataframe, parent=None):
        super().__init__(parent)
        self.df = dataframe

        # Create Toggle All checkbox
        self.toggleAllCheckbox = QCheckBox("Toggle All")
        self.toggleAllCheckbox.setTristate(False)
        self.toggleAllCheckbox.stateChanged.connect(self.toggleAll)

        # Create tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Cell ID / ROI Number"])
        self.tree.itemChanged.connect(self.handleItemChanged)
        self.tree.itemSelectionChanged.connect(self.handleItemSelectionChanged)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.toggleAllCheckbox)
        layout.addWidget(self.tree)
        self.setLayout(layout)

        self._populateTree()

    def _populateTree(self):
        # Group by Cell ID and Condition (each group represents a top-level item)
        grouped = self.df.groupby(["Cell ID", "Condition"])
        for (cell_id, condition), group in grouped:
            # region = group["Region"].iloc[0] if "Region" in group.columns else "Unknown"
            # cell_text = f"{cell_id} | Region: {region} | Condition: {condition}"
            cell_text = f"{cell_id} | {condition}"

            cell_item = QTreeWidgetItem([cell_text])
            cell_item.setFlags(cell_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            cell_item.setCheckState(0, Qt.Checked if group["show_cell"].iloc[0] else Qt.Unchecked)
            cell_item.setData(0, Qt.UserRole, ("cell", cell_id))

            for _, row in group.iterrows():
                num_peaks = row["Number of Spikes"] if "Number of Spikes" in row else "N/A"
                roi_text = f"ROI {row['ROI Number']} | Peaks: {num_peaks}"

                roi_item = QTreeWidgetItem([roi_text])
                roi_item.setFlags(roi_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                roi_item.setCheckState(0, Qt.Checked if row["show_roi"] else Qt.Unchecked)
                roi_item.setData(0, Qt.UserRole, ("roi", cell_id, row['ROI Number']))
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
            checked = item.checkState(0) == Qt.Checked
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
            self.cellToggled.emit(cell_id, checked)

        elif data[0] == "roi":
            cell_id, roi_number = data[1], data[2]
            checked = item.checkState(0) == Qt.Checked
            self.roiToggled.emit(cell_id, roi_number, checked)

            # Update parent state based on children's state
            parent = item.parent()
            if parent:
                all_checked = all(parent.child(i).checkState(0) == Qt.Checked for i in range(parent.childCount()))
                all_unchecked = all(parent.child(i).checkState(0) == Qt.Unchecked for i in range(parent.childCount()))
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
            self.cellSelected.emit(data[1])
        elif data[0] == "roi":
            self.roiSelected.emit(data[1], data[2])

    def toggleAll(self, state):
        """Toggles all tree items on/off based on the checkbox state."""
        self.tree.itemChanged.disconnect(self.handleItemChanged)

        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            parent.setCheckState(0, Qt.Checked if state == Qt.Checked else Qt.Unchecked)
            for j in range(parent.childCount()):
                child = parent.child(j)
                child.setCheckState(0, Qt.Checked if state == Qt.Checked else Qt.Unchecked)

        self.tree.itemChanged.connect(self.handleItemChanged)
        self.toggleAllToggled.emit(state == Qt.Checked)


# Example usage
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Sample data
    df = pd.DataFrame({
        'Cell ID': ['Cell1', 'Cell1', 'Cell2', 'Cell2', 'Cell2'],
        'ROI Number': [1, 2, 1, 2, 3],
        'accept cell': [True, True, False, False, False],
        'accept roi': [True, False, True, False, True],
        'Number of Spikes': [5, 3, 7, 0, 2],
        'Region': ['CA1', 'CA1', 'CA3', 'CA3', 'CA3'],
        'Condition': ['Control', 'Control', 'Treated', 'Treated', 'Stimulated']
    })

    widget = KymTreeWidget(df)

    def on_cell_toggled(cell_id, state):
        print(f"Cell {cell_id} toggled to {state}")

    def on_roi_toggled(cell_id, roi, state):
        print(f"ROI {roi} in Cell {cell_id} toggled to {state}")

    def on_cell_selected(cell_id):
        print(f"Selected Cell: {cell_id}")

    def on_roi_selected(cell_id, roi):
        print(f"Selected ROI {roi} in Cell {cell_id}")

    def on_toggle_all(state):
        print(f"'Toggle All' checkbox toggled to {state}")

    widget.cellToggled.connect(on_cell_toggled)
    widget.roiToggled.connect(on_roi_toggled)
    widget.cellSelected.connect(on_cell_selected)
    widget.roiSelected.connect(on_roi_selected)
    widget.toggleAllToggled.connect(on_toggle_all)

    widget.show()
    sys.exit(app.exec_())
