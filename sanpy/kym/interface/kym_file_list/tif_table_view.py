import os
import subprocess
import sys
from functools import partial
from typing import List, Optional

import pandas as pd
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    # QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    # QLineEdit,
    QMenu,
    # QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtGui import QDesktopServices

from sanpy.kym.tif_file_backend import TifFileBackend
from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


class TifTableView(QWidget):
    """A QTableWidget that displays TIF file data with advanced features."""

    # Signals
    fileToggled = pyqtSignal(str, bool)  # file_path, checked
    fileSelected = pyqtSignal(str)  # file_path
    fileDoubleClicked = pyqtSignal(str)  # file_path
    plotRoisRequested = pyqtSignal(str)  # tif_file_path
    # exportCompleted = pyqtSignal(str)  # export_filepath
    statusBarMessage = pyqtSignal(str)  # status_message

    def __init__(self,
                 backend: TifFileBackend,
                 parent=None):
        super().__init__(parent)
        self.backend = backend
        # logger.info(f'TifTableView: parent:{parent}')

        # Get visible columns from backend
        self.visible_columns = self.backend.get_visible_columns('table')

        # Filter state
        self.current_filters = {}

        # Selection state
        self.selected_rows = set()

        # Flag to track programmatic table population
        self._populating_table = False

        # Create UI
        self._createUI()
        self._setupTable()
        self._populateTable()
        self._setupConnections()

    def _createUI(self):
        """Create the user interface elements."""
        # Create filter controls
        self._createFilterControls()

        # Create table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)

        # Layout
        layout = QVBoxLayout()

        # Filter section
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filters:"))
        filter_layout.addWidget(self.condition_filter)
        filter_layout.addWidget(self.region_filter)
        filter_layout.addWidget(self.repeat_filter)
        # filter_layout.addWidget(self.search_box)  # COMMENTED OUT due to issues
        filter_layout.addWidget(self.clear_filters_btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Table
        layout.addWidget(self.table)

        self.setLayout(layout)

    def _createFilterControls(self):
        """Create filter controls."""
        # Condition filter
        self.condition_filter = QComboBox()
        self.condition_filter.addItem("All Conditions")
        self.condition_filter.currentTextChanged.connect(self._applyFilters)

        # Region filter
        self.region_filter = QComboBox()
        self.region_filter.addItem("All Regions")
        self.region_filter.currentTextChanged.connect(self._applyFilters)

        # Repeat filter
        self.repeat_filter = QComboBox()
        self.repeat_filter.addItem("All Repeats")
        self.repeat_filter.currentTextChanged.connect(self._applyFilters)

        # Search box - COMMENTED OUT due to issues
        # self.search_box = QLineEdit()
        # self.search_box.setPlaceholderText("Search filenames...")
        # self.search_box.textChanged.connect(self._applyFilters)

        # Clear filters button
        self.clear_filters_btn = QPushButton("Clear Filters")
        self.clear_filters_btn.clicked.connect(self._clearFilters)

    def _setupTable(self):
        """Set up the table configuration."""
        # Enable sorting
        self.table.setSortingEnabled(True)

        # Disable default double-click editing behavior
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Set up custom context menu for table background
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._handleTableContextMenu)

        # Set up headers using backend column display names
        display_names = self.backend.get_column_display_names(self.visible_columns)
        self.table.setColumnCount(len(self.visible_columns))
        self.table.setHorizontalHeaderLabels(display_names)

        # Configure header for interactive resizing
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.Interactive)

        # Set initial column widths from backend config
        for col_idx, column_name in enumerate(self.visible_columns):
            width = self.backend.get_column_width(column_name)
            if width is not None:
                self.table.setColumnWidth(col_idx, width)
            
            # Add tooltips from backend configuration
            tooltip = self.backend.get_column_tooltip(column_name)
            if tooltip:
                header_item = self.table.horizontalHeaderItem(col_idx)
                if header_item:
                    header_item.setToolTip(tooltip)

    def _setupConnections(self):
        """Set up signal connections."""
        self.table.itemSelectionChanged.connect(self._onSelectionChanged)
        try:
            self.table.itemDoubleClicked.disconnect()
        except Exception:
            pass
        self.table.itemDoubleClicked.connect(self._onItemDoubleClicked)
        self.table.cellChanged.connect(self._onCellChanged)

    def _populateTable(self):
        """Populate the table with data from the backend."""
        if self.backend.df is None or len(self.backend.df) == 0:
            return

        # Save current selection before repopulating
        selected_files = self._get_currently_selected_files()

        # Set flag to indicate we're programmatically populating the table
        self._populating_table = True

        # Temporarily disconnect cellChanged signal to prevent false triggers during population
        try:
            self.table.cellChanged.disconnect(self._onCellChanged)
        except TypeError:
            pass  # Not connected, safe to ignore
        
        try:
            # Get filtered data
            filtered_df = self._getFilteredData()

            # Set row count
            self.table.setRowCount(len(filtered_df))

            # Populate data
            for row_idx, (_, row) in enumerate(filtered_df.iterrows()):
                for col_idx, column in enumerate(self.visible_columns):
                    value = row[column]

                    if column == 'show_file':
                        # Create checkbox
                        checkbox = QCheckBox()
                        checkbox.setChecked(value)
                        checkbox.stateChanged.connect(
                            partial(self._onCheckboxChanged, row['relative_path'])
                        )
                        self.table.setCellWidget(row_idx, col_idx, checkbox)
                    elif column == '_kymRoiAnalysis':
                        # Create status icon item based on whether KymRoiAnalysis is loaded
                        if value is not None:
                            # Green circle for loaded
                            item = QTableWidgetItem("●")
                            item.setForeground(QtGui.QColor("#449944"))  # Green
                        else:
                            # Empty for not loaded
                            item = QTableWidgetItem("○")
                            item.setForeground(QtGui.QColor("#999999"))  # Gray

                        item.setData(Qt.UserRole, row['relative_path'])
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        self.table.setItem(row_idx, col_idx, item)
                    else:
                        # Regular text item - format based on column type
                        column_type = self.backend.get_column_type(column)
                        
                        # Format value based on its type
                        if pd.isna(value) or value is None:
                            display_value = ""
                        elif column_type == int:
                            # Ensure integers are displayed as integers, not floats
                            try:
                                display_value = str(int(value))
                            except (ValueError, TypeError):
                                display_value = str(value)
                        elif column_type == float:
                            # Format floats with appropriate precision
                            try:
                                float_value = float(value)
                                # Use more precision for msPerLine since values are larger
                                if column == 'msPerLine':
                                    display_value = f"{float_value:.1f}"
                                else:
                                    display_value = f"{float_value:.2f}"
                            except (ValueError, TypeError):
                                display_value = str(value)
                        elif column_type == bool:
                            # Display booleans as Yes/No
                            display_value = "Yes" if value else "No"
                        else:
                            # Default to string representation
                            display_value = str(value)
                        
                        item = QTableWidgetItem(display_value)
                        item.setData(
                            Qt.UserRole, row['relative_path']
                        )  # Store relative path for reference

                        # Set edit flags based on backend column configuration
                        if self.backend.is_column_editable(column):
                            item.setFlags(item.flags() | Qt.ItemIsEditable)
                        else:
                            item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                        self.table.setItem(row_idx, col_idx, item)

            # Restore selection after populating
            self._restore_selection(selected_files)

            # Update status
            # self._updateStatus()

            # Update filter options
            self._updateFilterOptions()
            
            # Auto-resize columns to fit content
            self.table.resizeColumnsToContents()
            
        finally:
            # Always reconnect cellChanged signal, even if an exception occurred
            self.table.cellChanged.connect(self._onCellChanged)
            # Reset the populating flag
            self._populating_table = False

    def _get_currently_selected_files(self) -> List[str]:
        """Get the file paths of currently selected rows."""
        selected_files = []
        selected_items = self.table.selectedItems()
        
        # Group selected items by row to avoid duplicates
        selected_rows = set()
        for item in selected_items:
            selected_rows.add(item.row())
        
        # Get file paths for selected rows
        for row in selected_rows:
            # Get file path from any column that has UserRole data
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and item.data(Qt.UserRole):
                    file_path = item.data(Qt.UserRole)
                    if file_path:
                        selected_files.append(file_path)
                    break  # Found the file path, no need to check other columns
        
        return selected_files

    def _restore_selection(self, selected_files: List[str]):
        """Restore selection for the given file paths if they are still visible."""
        if not selected_files:
            return
        
        # Clear current selection
        self.table.clearSelection()
        
        # Find and select rows that contain the previously selected files
        for row in range(self.table.rowCount()):
            # Get file path from any column that has UserRole data
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and item.data(Qt.UserRole):
                    file_path = item.data(Qt.UserRole)
                    if file_path in selected_files:
                        # Select this entire row
                        for col_idx in range(self.table.columnCount()):
                            item_to_select = self.table.item(row, col_idx)
                            if item_to_select:
                                item_to_select.setSelected(True)
                        break  # Found the file path, no need to check other columns

    def _getFilteredData(self):
        """Get filtered data based on current filters."""
        if self.backend.df is None:
            return pd.DataFrame()

        df = self.backend.df.copy()

        # Apply filters
        if (
            self.current_filters.get('condition')
            and self.current_filters['condition'] != "All Conditions"
        ):
            df = df[df['condition'] == self.current_filters['condition']]

        if (
            self.current_filters.get('region')
            and self.current_filters['region'] != "All Regions"
        ):
            df = df[df['region'] == self.current_filters['region']]

        if (
            self.current_filters.get('repeat')
            and self.current_filters['repeat'] != "All Repeats"
        ):
            df = df[df['repeat'] == int(self.current_filters['repeat'])]

        # Search filtering - COMMENTED OUT due to issues
        # if self.current_filters.get('search'):
        #     search_term = self.current_filters['search'].lower()
        #     df = df[df['filename'].str.lower().str.contains(search_term, na=False)]

        return df

    def _updateFilterOptions(self):
        """Update filter dropdown options based on current data."""
        if self.backend.df is None:
            return

        # Store current filter selections
        current_condition = self.condition_filter.currentText()
        current_region = self.region_filter.currentText()
        current_repeat = self.repeat_filter.currentText()

        # Temporarily disconnect signals to prevent infinite loop
        try:
            self.condition_filter.currentTextChanged.disconnect()
        except TypeError:
            pass  # Not connected, safe to ignore
        try:
            self.region_filter.currentTextChanged.disconnect()
        except TypeError:
            pass  # Not connected, safe to ignore
        try:
            self.repeat_filter.currentTextChanged.disconnect()
        except TypeError:
            pass  # Not connected, safe to ignore

        # Update condition filter
        conditions = ['All Conditions'] + sorted(
            self.backend.df['condition'].unique().tolist()
        )
        self.condition_filter.clear()
        self.condition_filter.addItems(conditions)

        # Update region filter
        regions = ['All Regions'] + sorted(self.backend.df['region'].unique().tolist())
        self.region_filter.clear()
        self.region_filter.addItems(regions)

        # Update repeat filter
        repeats = ['All Repeats'] + [
            str(r) for r in sorted(self.backend.df['repeat'].unique().tolist())
        ]
        self.repeat_filter.clear()
        self.repeat_filter.addItems(repeats)

        # Restore current filter selections if they still exist in the new options
        if current_condition in conditions:
            self.condition_filter.setCurrentText(current_condition)
        else:
            self.condition_filter.setCurrentText("All Conditions")

        if current_region in regions:
            self.region_filter.setCurrentText(current_region)
        else:
            self.region_filter.setCurrentText("All Regions")

        if current_repeat in repeats:
            self.repeat_filter.setCurrentText(current_repeat)
        else:
            self.repeat_filter.setCurrentText("All Repeats")

        # Reconnect signals
        self.condition_filter.currentTextChanged.connect(self._applyFilters)
        self.region_filter.currentTextChanged.connect(self._applyFilters)
        self.repeat_filter.currentTextChanged.connect(self._applyFilters)

    def _applyFilters(self):
        """Apply current filters to the table."""
        # Update current filters
        self.current_filters = {
            'condition': self.condition_filter.currentText(),
            'region': self.region_filter.currentText(),
            'repeat': self.repeat_filter.currentText(),
            # 'search': self.search_box.text(),  # COMMENTED OUT due to issues
        }

        # Repopulate table with filtered data
        self._populateTable()

    def _clearFilters(self):
        """Clear all filters."""
        self.condition_filter.setCurrentText("All Conditions")
        self.region_filter.setCurrentText("All Regions")
        self.repeat_filter.setCurrentText("All Repeats")
        # self.search_box.clear()  # COMMENTED OUT due to issues
        self._applyFilters()

    def _onSelectionChanged(self):
        """Handle selection changes."""
        # self._updateStatus()
        pass

    def _onItemDoubleClicked(self, item):
        """Handle double-click on table item."""
        if item is None:
            return
        row = item.row()
        column = item.column()
        if not self.is_checkbox_column(column):
            if self.is_editable_column(column):
                self.table.editItem(item)
                return
            file_path = item.data(Qt.UserRole)
            if file_path:
                # Debug: log the path and column info
                col_name = (
                    self.visible_columns[column]
                    if column < len(self.visible_columns)
                    else "unknown"
                )
                logger.info(
                    f"fileDoubleClicked -->> emit row:{row}, column:{column} col_name:{col_name}"
                )
                self.fileDoubleClicked.emit(file_path)

    def _onCellChanged(self, row, column):
        """Handle cell content changes."""
        # Ignore changes during programmatic table population
        if self._populating_table:
            return
            
        if column < 0 or column >= len(self.visible_columns):
            return

        column_name = self.visible_columns[column]

        # Handle note changes
        if column_name == 'note':
            # Get the new note value
            item = self.table.item(row, column)
            if item is None:
                return

            new_note = item.text()

            # Get the relative_path directly from the item's data
            # This works correctly even when the table is sorted
            relative_path = item.data(Qt.UserRole)
            
            if not relative_path:
                return

            # Update the note in the backend
            self._updateNoteInBackend(relative_path, new_note)

            logger.info(f"Note updated for {relative_path}: {new_note}")

    def _updateNoteInBackend(self, relative_path: str, note: str):
        """Update the note for a specific file in the backend."""
        if self.backend.df is None:
            return

        # Find the row with this relative path
        mask = self.backend.df['relative_path'] == relative_path
        if mask.any():
            # Update the note
            self.backend.df.loc[mask, 'note'] = note
            # Auto-save state after updating note
            self.backend._auto_save_state()

    def _onCheckboxChanged(self, file_path, state):
        """Handle checkbox state changes."""
        checked = state == Qt.Checked
        self.backend.set_checked('file', file_path, checked)
        self.fileToggled.emit(file_path, checked)

    def _handleTableContextMenu(self, pos):
        """Handle right-click context menu for table."""
        # Check if we clicked on an item
        item = self.table.itemAt(pos)
        
        if item and item.data(Qt.UserRole):
            # Clicked on an item, show item-specific context menu
            self._contextMenu(pos)
        else:
            # Clicked on table background, show table context menu
            # this is never executed, unclear where the user can click that is not an item
            # self._showTableContextMenu(pos)
            pass

    def _contextMenu(self, pos):
        """Handle right-click context menu for table items."""
        logger.info('')

        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        # Get the relative_path directly from the selected item's data
        # This works correctly even when the table is sorted
        item = selected_items[0]
        relative_path = item.data(Qt.UserRole)
        
        if not relative_path:
            return

        context_menu = QMenu()

        # Single file actions only
        context_menu.addAction(
            'Plot ROIs', partial(self.plotRoisRequested.emit, relative_path)
        )
        context_menu.addSeparator()
        context_menu.addAction(
            'Show in Finder', partial(self._showInFinder, relative_path)
        )
        context_menu.addAction('Copy Path', partial(self._copyPath, relative_path))

        context_menu.addSeparator()
        context_menu.addAction(
            "Copy table...",
            partial(self._copyTableToClipboard)
        )

        # Show menu
        pos = self.mapToGlobal(pos)
        context_menu.exec_(pos)

    def _copyTableToClipboard(self):
        """Copy the currently displayed table data to clipboard."""
        try:
            # Get the current filtered table data
            table_data = self.getTableData()
            
            if table_data is None or len(table_data) == 0:
                logger.warning("No table data to copy")
                return
            
            # Copy to clipboard using pandas
            table_data.to_clipboard(index=False)
            
            # Show status message
            row_count = len(table_data)
            col_count = len(table_data.columns)
            _msg = f"Copied {row_count} rows and {col_count} columns to clipboard"
            logger.info(_msg)
            logger.info(f'TifTableView: parent:{self.parent()}')
            self.statusBarMessage.emit(_msg)  # set status bar message

        except Exception as e:
            logger.error(f"Error copying table to clipboard: {e}")

    def _showInFinder(self, relative_path):
        """Show file in Finder/Explorer."""
        try:
            full_path = self.backend.resolve_path(relative_path)
            if os.path.exists(full_path):
                if sys.platform == "darwin":  # macOS
                    subprocess.run(["open", "-R", full_path])
                elif sys.platform == "win32":  # Windows
                    subprocess.run(["explorer", "/select,", full_path])
                else:  # Linux
                    subprocess.run(["xdg-open", os.path.dirname(full_path)])
            else:
                logger.error(f"File not found: {full_path}")
        except Exception as e:
            logger.error(f"Error showing file {relative_path} in Finder: {e}")

    def _copyPath(self, relative_path):
        """Copy file path to clipboard."""
        try:
            # Copy the full absolute path
            full_path = self.backend.resolve_path(relative_path)
            clipboard = QApplication.clipboard()
            clipboard.setText(str(full_path))
            
            # Show status message
            _msg = f"Copied path to clipboard: {str(full_path)}"
            logger.info(_msg)
            self.statusBarMessage.emit(_msg)
        except Exception as e:
            logger.error(f"Error copying path for {relative_path}: {e}")

    def _copyPaths(self, filenames):
        """Copy multiple file paths to clipboard."""
        relative_paths = []
        for filename in filenames:
            mask = self.backend.df['filename'] == filename
            if mask.any():
                relative_path = self.backend.df[mask]['relative_path'].iloc[0]
                relative_paths.append(relative_path)

        clipboard = QApplication.clipboard()
        clipboard.setText('\n'.join(relative_paths))

    def _selectFiles(self, filenames, checked):
        """Select/deselect multiple files."""
        for filename in filenames:
            mask = self.backend.df['filename'] == filename
            if mask.any():
                relative_path = self.backend.df[mask]['relative_path'].iloc[0]
                self.backend.set_checked('file', relative_path, checked)
        self._populateTable()

    # Public methods
    def refresh(self):
        """Refresh the table data."""
        self.backend.refresh()
        self._populateTable()
        logger.info("Table refreshed")

    def refresh_display(self):
        """Refresh only the table display without rescanning backend data."""
        self._populateTable()
        logger.info("Table display refreshed")

    def getSelectedFiles(self) -> List[str]:
        """Get list of selected file paths."""
        selected_files = []
        checkbox_col = self.get_column_index('show_file')

        # Iterate through all table rows and check checkbox state
        # Use Qt.UserRole data to get the correct file path regardless of sorting
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, checkbox_col)
            if checkbox and checkbox.isChecked():
                # Get the file path from any column that has UserRole data
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item and item.data(Qt.UserRole):
                        file_path = item.data(Qt.UserRole)
                        if file_path:
                            selected_files.append(file_path)
                        break  # Found the file path, no need to check other columns
        return selected_files

    def getVisibleFiles(self) -> List[str]:
        """Get list of all visible file paths."""
        visible_files = []

        # Iterate through all table rows
        # Use Qt.UserRole data to get the correct file path regardless of sorting
        for row in range(self.table.rowCount()):
            # Get the file path from any column that has UserRole data
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and item.data(Qt.UserRole):
                    file_path = item.data(Qt.UserRole)
                    if file_path:
                        visible_files.append(file_path)
                    break  # Found the file path, no need to check other columns
        return visible_files

    def getTableData(self) -> Optional[pd.DataFrame]:
        """Get the current filtered table data as a DataFrame."""
        if self.backend.df is None or len(self.backend.df) == 0:
            return None

        # Get filtered data (same as what's displayed in table)
        filtered_df = self._getFilteredData()

        if len(filtered_df) == 0:
            return None

        # Return only visible columns
        export_columns = [col for col in self.visible_columns]
        return filtered_df[export_columns]

    def saveTableDataToCSV(self, table_data: pd.DataFrame) -> Optional[str]:
        """Save table data to a CSV file and return the filepath."""
        if table_data is None or len(table_data) == 0:
            return None

        # Get save file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save table as...",
            os.path.join(self.backend.root_path, "tif_table_export.csv"),
            "CSV Files (*.csv);;All Files (*)",
        )

        if file_path:
            try:
                table_data.to_csv(file_path, index=False)
                logger.info(f"Table data exported to: {file_path}")
                return file_path
            except Exception as e:
                logger.error(f"Failed to export table data: {e}")
                return None

        return None

    def get_column_index(self, column_name: str) -> int:
        """Get the index of a column by name."""
        return self.visible_columns.index(column_name)

    def is_checkbox_column(self, column: int) -> bool:
        """Check if the given column is a checkbox column."""
        if column < 0 or column >= len(self.visible_columns):
            return False
        column_name = self.visible_columns[column]
        return self.backend.is_checkbox_column(column_name)

    def is_editable_column(self, column: int) -> bool:
        """Check if the given column is editable."""
        if column < 0 or column >= len(self.visible_columns):
            return False
        column_name = self.visible_columns[column]
        return self.backend.is_column_editable(column_name)

    def updateKymAnalysisStatus(self, filename: str):
        """
        Update the KymRoiAnalysis status icon for a specific file.

        This method should be called after a KymRoiAnalysis object is loaded
        to refresh the visual indicator in the table.

        Parameters
        ----------
        filename : str
            The filename (e.g., "20250312 ISAN R1 LS1 Control.tif")
        """
        # Find the status column index
        try:
            status_col_idx = self.get_column_index('_kymRoiAnalysis')
        except ValueError:
            # Status column not visible
            return

        # Find the table row that contains this filename
        # We need to search through all table items to find the correct row
        # This works correctly even when the table is sorted
        target_table_row = None
        for row in range(self.table.rowCount()):
            # Check any column that has the relative_path stored in UserRole
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and item.data(Qt.UserRole):
                    # Extract filename from relative_path for comparison
                    relative_path = item.data(Qt.UserRole)
                    item_filename = os.path.basename(relative_path)
                    if item_filename == filename:
                        target_table_row = row
                        break
            if target_table_row is not None:
                break

        if target_table_row is None:
            # File not found in current table view (might be filtered out)
            return

        # Find the corresponding row in the backend DataFrame
        mask = self.backend.df['filename'] == filename
        if not mask.any():
            return

        backend_row_idx = mask.idxmax()

        # Check if the KymRoiAnalysis is loaded
        is_loaded = self.backend.df.loc[backend_row_idx, '_kymRoiAnalysis'] is not None

        # Update the table item
        if is_loaded:
            # Green circle for loaded
            item = QTableWidgetItem("●")
            item.setForeground(QtGui.QColor("#449944"))  # Green
        else:
            # Empty circle for not loaded
            item = QTableWidgetItem("○")
            item.setForeground(QtGui.QColor("#999999"))  # Gray

        # Get the relative_path for this row to store in UserRole
        relative_path = self.backend.df.loc[backend_row_idx, 'relative_path']
        item.setData(Qt.UserRole, relative_path)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(target_table_row, status_col_idx, item)
