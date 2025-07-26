import sys
import os
import subprocess
from typing import List, Optional, Dict, Any

import matplotlib.pyplot as plt

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QApplication,
    QCheckBox,
)
from PyQt5.QtCore import pyqtSignal, Qt
import pandas as pd

from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)

from sanpy.kym.tif_file_backend import TifFileBackend


class TreeColumnConfig:
    """Configuration class for tree widget columns."""

    def __init__(self):
        # Current columns
        self.current_columns = [
            'files_folders',  # Main tree column with checkboxes
                    'Condition',  # Condition column
        'Repeat',  # Repeat column
        ]

        # Planned additional columns (from backend)
        self.planned_columns = [
                    'Date',  # Date column (redundant with table)
        'Region',  # Region column (redundant with table)
            'error',  # Error column (new)
            'um_per_pixel',  # um per pixel (new)
            'ms_per_line',  # ms per line (new)
            'acq_date',  # Acquisition date (new)
            'acq_time',  # Acquisition time (new)
        ]

        # All columns (current + planned)
        self.all_columns = self.current_columns + self.planned_columns

        # Column metadata
        self.column_metadata = {
            # Current columns
            'files_folders': {
                'display_name': 'Files and Folders',
                'width': 300,
                'stretch': True,
                'editable': False,
                'has_checkbox': True,
                'backend_field': None,  # Special case for tree structure
            },
            'Condition': {
                'display_name': 'Condition',
                'width': 100,
                'stretch': False,
                'editable': False,
                'has_checkbox': False,
                'backend_field': 'Condition',
            },
            'Repeat': {
                'display_name': 'Repeat',
                'width': 80,
                'stretch': False,
                'editable': False,
                'has_checkbox': False,
                'backend_field': 'Repeat',
            },
            # Planned columns
            'Date': {
                'display_name': 'Date',
                'width': 100,
                'stretch': False,
                'editable': False,
                'has_checkbox': False,
                'backend_field': 'Date',
            },
            'Region': {
                'display_name': 'Region',
                'width': 80,
                'stretch': False,
                'editable': False,
                'has_checkbox': False,
                'backend_field': 'Region',
            },
            'error': {
                'display_name': 'Error',
                'width': 80,
                'stretch': False,
                'editable': False,
                'has_checkbox': False,
                'backend_field': 'error',
            },
            'um_per_pixel': {
                'display_name': 'μm/px',
                'width': 70,
                'stretch': False,
                'editable': False,
                'has_checkbox': False,
                'backend_field': 'um_per_pixel',
            },
            'ms_per_line': {
                'display_name': 'ms/line',
                'width': 70,
                'stretch': False,
                'editable': False,
                'has_checkbox': False,
                'backend_field': 'ms_per_line',
            },
            'acq_date': {
                'display_name': 'Acq Date',
                'width': 90,
                'stretch': False,
                'editable': False,
                'has_checkbox': False,
                'backend_field': 'acq_date',
            },
            'acq_time': {
                'display_name': 'Acq Time',
                'width': 90,
                'stretch': False,
                'editable': False,
                'has_checkbox': False,
                'backend_field': 'acq_time',
            },
        }

        # Active columns (can be modified to show/hide columns)
        self.active_columns = self.current_columns.copy()

        # Update indexes
        self._update_indexes()

    def _update_indexes(self):
        """Update column indexes based on active columns."""
        self.column_indexes = {col: idx for idx, col in enumerate(self.active_columns)}

    def get_index(self, column_name: str) -> int:
        """Get column index by name."""
        return self.column_indexes.get(column_name, -1)

    def get_display_name(self, column_name: str) -> str:
        """Get display name for column."""
        return self.column_metadata.get(column_name, {}).get(
            'display_name', column_name
        )

    def get_width(self, column_name: str) -> Optional[int]:
        """Get column width by name."""
        return self.column_metadata.get(column_name, {}).get('width')

    def is_stretch(self, column_name: str) -> bool:
        """Check if column should stretch."""
        return self.column_metadata.get(column_name, {}).get('stretch', False)

    def has_checkbox(self, column_name: str) -> bool:
        """Check if column has checkboxes."""
        return self.column_metadata.get(column_name, {}).get('has_checkbox', False)

    def get_backend_field(self, column_name: str) -> Optional[str]:
        """Get backend field name for column."""
        return self.column_metadata.get(column_name, {}).get('backend_field')

    def get_active_columns(self) -> List[str]:
        """Get list of currently active columns."""
        return self.active_columns.copy()

    def get_active_display_names(self) -> List[str]:
        """Get list of display names for active columns."""
        return [self.get_display_name(col) for col in self.active_columns]

    def add_column(self, column_name: str):
        """Add a column to the active columns."""
        if column_name in self.all_columns and column_name not in self.active_columns:
            self.active_columns.append(column_name)
            self._update_indexes()

    def remove_column(self, column_name: str):
        """Remove a column from active columns."""
        if column_name in self.active_columns and column_name != 'files_folders':
            self.active_columns.remove(column_name)
            self._update_indexes()

    def set_columns(self, column_names: List[str]):
        """Set the active columns."""
        if 'files_folders' not in column_names:
            column_names.insert(0, 'files_folders')  # Always keep files_folders first

        self.active_columns = [col for col in column_names if col in self.all_columns]
        self._update_indexes()

    def is_checkbox_column(self, column_index: int) -> bool:
        """Check if column index is a checkbox column."""
        if column_index < 0 or column_index >= len(self.active_columns):
            return False
        column_name = self.active_columns[column_index]
        return self.has_checkbox(column_name)


class TifTreeWidget(QWidget):
    """A QTreeWidget that displays .tif files from a folder structure with refresh capability."""

    # Emitted when a file is checked or unchecked
    fileToggled = pyqtSignal(str, bool)  # file_path, checked

    # Emitted when the user selects a folder
    folderSelected = pyqtSignal(str)  # folder_path

    # Emitted when the user selects a file
    fileSelected = pyqtSignal(str)  # file_path

    # Emitted when the user selects a grandparent folder
    grandparentSelected = pyqtSignal(str)  # grandparent_name

    # Emitted when the user selects a great-grandparent folder
    greatGrandparentSelected = pyqtSignal(str)  # great_grandparent_name

    # Emitted when files are refreshed
    filesRefreshed = pyqtSignal(list)  # list of file paths

    # Emitted when a .tif file is double-clicked
    fileDoubleClicked = pyqtSignal(str)  # file_path

    # Emitted when user selects "Plot ROIs" from context menu
    plotRoisRequested = pyqtSignal(str)  # tif_file_path



    def __init__(
        self, backend: TifFileBackend, show_third_level: bool = False, parent=None
    ):
        super().__init__(parent)
        self.backend = backend
        self.show_third_level = show_third_level

        # Column configuration
        self.column_config = TreeColumnConfig()

        # Set up context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu)

        # Create UI elements
        self._createUI()

        # Initial population
        self._populateTree()

    def _createUI(self):
        """Create the user interface elements."""
        # Create tree with multiple columns
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(self.column_config.get_active_display_names())
        self.tree.itemChanged.connect(self.handleItemChanged)
        self.tree.itemSelectionChanged.connect(self.handleItemSelectionChanged)
        self.tree.itemDoubleClicked.connect(self.handleItemDoubleClicked)

        # Set up column widths
        self._setup_column_widths()

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)

    def refresh(self):
        """Refresh the tree by refreshing the backend data."""
        logger.info("Refreshing tree from backend")

        # Refresh backend data
        self.backend.refresh()

        # Rebuild tree display
        self._rebuildTreeDisplay()

        # Emit signal with found files
        self.filesRefreshed.emit(self.backend.get('files'))

        logger.info(f"Found {self.backend.get('file_count')} .tif files")

    def _populateTree(self):
        """Populate the tree with folders and files using backend data."""
        if self.backend.df is None or len(self.backend.df) == 0:
            return

        # Get unique great-grandparent folders
        great_grandparents = self.backend.df['great_grandparent_folder'].unique()
        great_grandparents = [
            gg for gg in great_grandparents if gg
        ]  # Remove empty strings

        if great_grandparents:
            # We have great-grandparent folders, use the original logic
            for great_grandparent_name in sorted(great_grandparents):
                # Create great-grandparent item
                great_grandparent_item = self._create_tree_item(
                    "great_grandparent", great_grandparent_name
                )

                # Get grandparent folders for this great-grandparent
                grandparent_data = self.backend.df[
                    self.backend.df['great_grandparent_folder']
                    == great_grandparent_name
                ]
                grandparents = grandparent_data['grandparent_folder'].unique()
                grandparents = [gp for gp in grandparents if gp]  # Remove empty strings

                for grandparent_name in sorted(grandparents):
                    # Create grandparent item
                    grandparent_item = self._create_tree_item(
                        "grandparent", grandparent_name
                    )

                    # Get data for this grandparent
                    parent_data = grandparent_data[
                        grandparent_data['grandparent_folder'] == grandparent_name
                    ]

                    if self.show_third_level:
                        # Three-level structure: great_grandparent -> grandparent -> folder -> files
                        folders = parent_data['parent_folder'].unique()
                        folders = [f for f in folders if f]  # Remove empty strings

                        for folder_name in sorted(folders):
                            # Create folder item
                            folder_item = self._create_tree_item("folder", folder_name)

                            # Add .tif files as children
                            folder_data = parent_data[
                                parent_data['parent_folder'] == folder_name
                            ]
                            for _, row in folder_data.iterrows():
                                file_item = self._create_tree_item(
                                    "file", row['filename'], row
                                )
                                folder_item.addChild(file_item)

                            grandparent_item.addChild(folder_item)
                    else:
                        # Two-level structure: great_grandparent -> grandparent -> files
                        # Add .tif files directly as children of grandparent
                        for _, row in parent_data.iterrows():
                            file_item = self._create_tree_item(
                                "file", row['filename'], row
                            )
                            grandparent_item.addChild(file_item)

                    great_grandparent_item.addChild(grandparent_item)

                self.tree.addTopLevelItem(great_grandparent_item)
                great_grandparent_item.setExpanded(True)
        else:
            # No great-grandparent folders, create top-level items for grandparent folders
            grandparents = self.backend.df['grandparent_folder'].unique()
            grandparents = [gp for gp in grandparents if gp]  # Remove empty strings

            for grandparent_name in sorted(grandparents):
                # Create grandparent item
                grandparent_item = self._create_tree_item(
                    "grandparent", grandparent_name
                )

                # Get data for this grandparent
                parent_data = self.backend.df[
                    self.backend.df['grandparent_folder'] == grandparent_name
                ]

                if self.show_third_level:
                    # Three-level structure: grandparent -> folder -> files
                    folders = parent_data['parent_folder'].unique()
                    folders = [f for f in folders if f]  # Remove empty strings

                    for folder_name in sorted(folders):
                        # Create folder item
                        folder_item = self._create_tree_item("folder", folder_name)

                        # Add .tif files as children
                        folder_data = parent_data[
                            parent_data['parent_folder'] == folder_name
                        ]
                        for _, row in folder_data.iterrows():
                            file_item = self._create_tree_item(
                                "file", row['filename'], row
                            )
                            folder_item.addChild(file_item)

                        grandparent_item.addChild(folder_item)
                else:
                    # Two-level structure: grandparent -> files
                    # Add .tif files directly as children of grandparent
                    for _, row in parent_data.iterrows():
                        file_item = self._create_tree_item("file", row['filename'], row)
                        grandparent_item.addChild(file_item)

                self.tree.addTopLevelItem(grandparent_item)
                grandparent_item.setExpanded(True)

        # Expand all items by default
        self._expandAllItems()

    def _expandAllItems(self):
        """Expand all tree items to show disclosure triangles open."""

        def expandItem(item):
            item.setExpanded(True)
            for i in range(item.childCount()):
                expandItem(item.child(i))

        for i in range(self.tree.topLevelItemCount()):
            expandItem(self.tree.topLevelItem(i))

    def _rebuildTreeDisplay(self):
        """Rebuild the tree display from scratch."""
        self.tree.clear()
        self._populateTree()

    def setShowThirdLevel(self, show: bool):
        """Set whether to show the third level (enclosing folder) and rebuild the tree display."""
        if self.show_third_level != show:
            self.show_third_level = show

            # Only rebuild the tree display, don't refresh the backend data
            self._rebuildTreeDisplay()

    def getShowThirdLevel(self) -> bool:
        """Get whether the third level is currently shown."""
        return self.show_third_level

    def toggleThirdLevel(self):
        """Toggle the third level display on/off."""
        self.setShowThirdLevel(not self.show_third_level)

    def _contextMenu(self, pos):
        """Handle right-click context menu."""
        logger.info('')

        selectedItems = self.tree.selectedItems()
        if len(selectedItems) == 0:
            return

        item = selectedItems[0]
        data = item.data(0, Qt.UserRole)
        if data is None:
            return

        contextMenu = QtWidgets.QMenu()

        if data[0] == "great_grandparent":
            contextMenu.addAction('Show in Finder')
        elif data[0] == "grandparent":
            contextMenu.addAction('Show in Finder')
        elif data[0] == "folder":
            contextMenu.addAction('Open Folder')
            contextMenu.addAction('Show in Finder')
        elif data[0] == "file":
            contextMenu.addAction('Plot ROIs')
            contextMenu.addSeparator()
            contextMenu.addAction('Show in Finder')
            contextMenu.addAction('Copy Path')

        # Show menu
        pos = self.mapToGlobal(pos)
        action = contextMenu.exec_(pos)
        if action is None:
            return

        actionText = action.text()

        if actionText == 'Plot ROIs':
            if data[0] == "file":
                _tifFile = data[1]
                self.plotRoisRequested.emit(_tifFile)

        elif actionText == 'Open Folder':
            if data[0] == "folder":
                subprocess.run(['open', data[1]])
        elif actionText == 'Show in Finder':
            if data[0] == "great_grandparent":
                # Find the actual path for great-grandparent
                great_grandparent_name = data[1]
                great_grandparent_path = os.path.join(
                    self.backend.root_path, great_grandparent_name
                )
                if os.path.exists(great_grandparent_path):
                    subprocess.run(['open', great_grandparent_path])
            elif data[0] == "grandparent":
                # Find the actual path for grandparent
                grandparent_name = data[1]
                grandparent_path = os.path.join(
                    self.backend.root_path, grandparent_name
                )
                if os.path.exists(grandparent_path):
                    subprocess.run(['open', grandparent_path])
            elif data[0] == "folder":
                subprocess.run(['open', data[1]])
            elif data[0] == "file":
                # Resolve relative path to absolute path for file operations
                file_path = os.path.join(self.backend.root_path, data[1])
                subprocess.run(['open', '-R', file_path])
        elif actionText == 'Copy Path':
            if data[0] == "file":
                clipboard = QApplication.clipboard()
                # Resolve relative path to absolute path for clipboard
                file_path = os.path.join(self.backend.root_path, data[1])
                clipboard.setText(file_path)

    def handleItemChanged(self, item, column):
        """Handle checkbox state changes for individual files."""
        data = item.data(self.get_column_index('files_folders'), Qt.UserRole)
        if data is None:
            return

        # Only handle file checkboxes in the checkbox column
        if data[0] == "file" and self.is_checkbox_column(column):
            file_path = data[1]
            checked = item.checkState(column) == Qt.Checked

            # Update backend
            self.backend.set_checked('file', file_path, checked)

            # Emit signal
            self.fileToggled.emit(file_path, checked)

    def handleItemSelectionChanged(self):
        """Handle item selection changes."""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        data = item.data(self.get_column_index('files_folders'), Qt.UserRole)
        if data is None:
            return

        if data[0] == "great_grandparent":
            self.greatGrandparentSelected.emit(data[1])
        elif data[0] == "grandparent":
            self.grandparentSelected.emit(data[1])
        elif data[0] == "folder":
            self.folderSelected.emit(data[1])
        elif data[0] == "file":
            self.fileSelected.emit(data[1])

    def handleItemDoubleClicked(self, item, column):
        """Handle double-click on .tif files."""
        data = item.data(self.get_column_index('files_folders'), Qt.UserRole)
        if data is None:
            return

        if data[0] == "file":
            file_path = data[1]
            self.fileDoubleClicked.emit(file_path)

    def getCheckedFiles(self) -> List[str]:
        """Get list of checked file paths."""
        return self.backend.get('files')

    def getFileCount(self) -> int:
        """Get total number of files."""
        return self.backend.get('file_count')

    def getBackend(self) -> TifFileBackend:
        """Get the backend instance."""
        return self.backend

    def setAllChecked(self, checked: bool):
        """
        Programmatically set all checkboxes to the specified state.

        Parameters
        ----------
        checked : bool
            Whether all items should be checked (True) or unchecked (False)
        """
        if self.backend.df is not None:
            # Update backend for all files using the backend's API
            for _, row in self.backend.df.iterrows():
                self.backend.set_checked('file', row['relative_path'], checked)

            # Update tree display to reflect the changes
            self._rebuildTreeDisplay()



    def get_column_index(self, column_name: str) -> int:
        """Get the column index for a given column name."""
        return self.column_config.get_index(column_name)

    def is_checkbox_column(self, column: int) -> bool:
        """Check if the given column is a checkbox column."""
        return self.column_config.is_checkbox_column(column)

    def add_column(self, column_name: str):
        """Add a column to the tree widget."""
        self.column_config.add_column(column_name)
        self._rebuild_tree_headers()
        self._rebuildTreeDisplay()

    def remove_column(self, column_name: str):
        """Remove a column from the tree widget."""
        self.column_config.remove_column(column_name)
        self._rebuild_tree_headers()
        self._rebuildTreeDisplay()

    def set_columns(self, column_names: List[str]):
        """Set the active columns for the tree widget."""
        self.column_config.set_columns(column_names)
        self._rebuild_tree_headers()
        self._rebuildTreeDisplay()

    def _rebuild_tree_headers(self):
        """Rebuild the tree headers based on current column configuration."""
        if hasattr(self, 'tree'):
            self.tree.setHeaderLabels(self.column_config.get_active_display_names())
            self._setup_column_widths()

    def _setup_column_widths(self):
        """Set up column widths based on column configuration."""
        for column_name in self.column_config.get_active_columns():
            col_idx = self.get_column_index(column_name)
            width = self.column_config.get_width(column_name)

            if width is not None:
                self.tree.setColumnWidth(col_idx, width)

    def _create_tree_item(
        self, item_type: str, item_name: str, row_data: pd.Series = None
    ) -> QTreeWidgetItem:
        """Create a tree item with the appropriate columns based on configuration."""
        # Initialize item text for all active columns
        item_texts = [""] * len(self.column_config.get_active_columns())

        # Set the main item name in the files_folders column
        files_folders_idx = self.get_column_index('files_folders')
        if files_folders_idx >= 0:
            item_texts[files_folders_idx] = item_name

        # For file items, populate data from backend
        if item_type == "file" and row_data is not None:
            for column_name in self.column_config.get_active_columns():
                col_idx = self.get_column_index(column_name)
                if col_idx >= 0 and column_name != 'files_folders':
                    backend_field = self.column_config.get_backend_field(column_name)
                    if backend_field and backend_field in row_data:
                        value = row_data[backend_field]
                        # Format the value appropriately
                        if pd.isna(value):
                            item_texts[col_idx] = ""
                        elif isinstance(value, (int, float)):
                            item_texts[col_idx] = str(value)
                        else:
                            item_texts[col_idx] = str(value)

        # Create the tree item
        item = QTreeWidgetItem(item_texts)

        # Set flags and data
        if item_type == "file":
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            if row_data is not None:
                checked = row_data.get('Accept', False)
                item.setCheckState(
                    files_folders_idx, Qt.Checked if checked else Qt.Unchecked
                )
                item.setData(
                    files_folders_idx, Qt.UserRole, ("file", row_data['relative_path'])
                )
        else:
            item.setFlags(item.flags() | Qt.ItemIsSelectable)
            item.setData(files_folders_idx, Qt.UserRole, (item_type, item_name))

        return item
