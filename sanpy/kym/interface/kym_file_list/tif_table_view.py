import os
import subprocess
import sys
from functools import partial
from typing import List, Optional

import pandas as pd
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMenu, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget
)
from PyQt5.QtGui import QDesktopServices

from sanpy.kym.tif_file_backend import TifFileBackend
from sanpy.kym.logger import get_logger

logger = get_logger(__name__)

class TifTableView(QWidget):
    """A QTableWidget that displays TIF file data with advanced features."""
    
    # Signals
    fileToggled = pyqtSignal(str, bool)  # file_path, checked
    fileSelected = pyqtSignal(str)  # file_path
    fileDoubleClicked = pyqtSignal(str)  # file_path
    plotRoisRequested = pyqtSignal(str)  # tif_file_path
    exportCompleted = pyqtSignal(str)  # export_filepath
    loadKymAnalysisRequested = pyqtSignal(str)  # tif_file_path
    
    def __init__(self, backend: TifFileBackend, parent=None):
        super().__init__(parent)
        self.backend = backend
        
        # Get visible columns from backend
        self.visible_columns = self.backend.get_visible_columns('table')
        
        # Filter state
        self.current_filters = {}
        
        # Selection state
        self.selected_rows = set()
        
        # Set up context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu)
        
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
        filter_layout.addWidget(self.search_box)
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
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search filenames...")
        self.search_box.textChanged.connect(self._applyFilters)
        
        # Clear filters button
        self.clear_filters_btn = QPushButton("Clear Filters")
        self.clear_filters_btn.clicked.connect(self._clearFilters)
    
    def _setupTable(self):
        """Set up the table configuration."""
        # Enable sorting
        self.table.setSortingEnabled(True)
        
        # Disable default double-click editing behavior
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Set up headers using backend column display names
        display_names = self.backend.get_column_display_names(self.visible_columns)
        self.table.setColumnCount(len(self.visible_columns))
        self.table.setHorizontalHeaderLabels(display_names)
        
        # Configure header
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.Interactive)
        
        # Set column widths and stretch behavior using backend config
        for col_idx, column_name in enumerate(self.visible_columns):
            width = self.backend.get_column_width(column_name)
            
            if self.backend.is_column_stretch(column_name):
                header.setSectionResizeMode(col_idx, QHeaderView.Stretch)
            elif width is not None:
                self.table.setColumnWidth(col_idx, width)
    
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
                elif column == '_KymRoiAnalysis_Loaded':
                    # Create status icon item
                    if value:
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
                    # Regular text item
                    item = QTableWidgetItem(str(value))
                    item.setData(Qt.UserRole, row['relative_path'])  # Store relative path for reference
                    
                    # Set edit flags based on backend column configuration
                    if self.backend.is_column_editable(column):
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
                    else:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    
                    self.table.setItem(row_idx, col_idx, item)
        
        # Update status
        self._updateStatus()
        
        # Update filter options
        self._updateFilterOptions()
    
    def _getFilteredData(self):
        """Get filtered data based on current filters."""
        if self.backend.df is None:
            return pd.DataFrame()
        
        df = self.backend.df.copy()
        
        # Apply filters
        if self.current_filters.get('condition') and self.current_filters['condition'] != "All Conditions":
            df = df[df['condition'] == self.current_filters['condition']]
        
        if self.current_filters.get('region') and self.current_filters['region'] != "All Regions":
            df = df[df['region'] == self.current_filters['region']]
        
        if self.current_filters.get('repeat') and self.current_filters['repeat'] != "All Repeats":
            df = df[df['repeat'] == int(self.current_filters['repeat'])]
        
        if self.current_filters.get('search'):
            search_term = self.current_filters['search'].lower()
            df = df[df['filename'].str.lower().str.contains(search_term, na=False)]
        
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
        self.condition_filter.currentTextChanged.disconnect()
        self.region_filter.currentTextChanged.disconnect()
        self.repeat_filter.currentTextChanged.disconnect()
        
        # Update condition filter
        conditions = ['All Conditions'] + sorted(self.backend.df['condition'].unique().tolist())
        self.condition_filter.clear()
        self.condition_filter.addItems(conditions)
        
        # Update region filter
        regions = ['All Regions'] + sorted(self.backend.df['region'].unique().tolist())
        self.region_filter.clear()
        self.region_filter.addItems(regions)
        
        # Update repeat filter
        repeats = ['All Repeats'] + [str(r) for r in sorted(self.backend.df['repeat'].unique().tolist())]
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
            'search': self.search_box.text()
        }
        
        # Repopulate table with filtered data
        self._populateTable()
    
    def _clearFilters(self):
        """Clear all filters."""
        self.condition_filter.setCurrentText("All Conditions")
        self.region_filter.setCurrentText("All Regions")
        self.repeat_filter.setCurrentText("All Repeats")
        self.search_box.clear()
        self._applyFilters()
    
    def _updateStatus(self):
        """Update status label."""
        # Status is now handled by the main window's status bar
        pass
    
    def _onSelectionChanged(self):
        """Handle selection changes."""
        self._updateStatus()
    
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
                col_name = self.visible_columns[column] if column < len(self.visible_columns) else "unknown"
                logger.info(f"Double-click - Row {row}, Col {column} ({col_name}): {file_path}")
                self.fileDoubleClicked.emit(file_path)
    
    def _onCellChanged(self, row, column):
        """Handle cell content changes."""
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
            
            # Get the filtered data to find the correct row
            filtered_df = self._getFilteredData()
            if filtered_df is None or len(filtered_df) == 0:
                return
            
            if row >= len(filtered_df):
                return
            
            # Get the relative_path for this row
            relative_path = filtered_df.iloc[row]['relative_path']
            
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
    
    def _onCheckboxChanged(self, file_path, state):
        """Handle checkbox state changes."""
        checked = state == Qt.Checked
        self.backend.set_checked('file', file_path, checked)
        self.fileToggled.emit(file_path, checked)
    
    def _contextMenu(self, pos):
        """Handle right-click context menu."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        
        # Get the relative_path from the selected row in the backend
        item = selected_items[0]
        row = item.row()
        
        # Get the filtered data to find the correct row
        filtered_df = self._getFilteredData()
        if filtered_df is None or len(filtered_df) == 0:
            return
        
        if row >= len(filtered_df):
            return
        
        # Get the relative_path from the backend for this row
        relative_path = filtered_df.iloc[row]['relative_path']
        if not relative_path:
            return
        
        context_menu = QMenu()
        
        # Single file actions only
        context_menu.addAction('Plot ROIs', partial(self.plotRoisRequested.emit, relative_path))
        context_menu.addAction('Load Kym Analysis', partial(self.loadKymAnalysisRequested.emit, relative_path))
        context_menu.addSeparator()
        context_menu.addAction('Open File', partial(self._openFile, relative_path))
        context_menu.addAction('Show in Finder', partial(self._showInFinder, relative_path))
        context_menu.addAction('Copy Path', partial(self._copyPath, relative_path))
        
        # Show menu
        pos = self.mapToGlobal(pos)
        context_menu.exec_(pos)
    
    def _openFile(self, relative_path):
        """Open file in default application."""
        try:
            full_path = self.backend.resolve_path(relative_path)
            if os.path.exists(full_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(full_path))
            else:
                logger.error(f"File not found: {full_path}")
        except Exception as e:
            logger.error(f"Error opening file {relative_path}: {e}")
    
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
            clipboard.setText(full_path)
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
    
    def saveState(self):
        """Save the current state to a CSV file."""
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()  # Ensure all checkbox changes are committed
        if self.backend:
            csv_filepath = self.backend.save_state()
            if csv_filepath:
                csv_filename = os.path.basename(csv_filepath)
                logger.info(f"State saved to: {csv_filename}")
                return csv_filename
        return None
    
    def getSelectedFiles(self) -> List[str]:
        """Get list of selected file paths."""
        selected_files = []
        checkbox_col = self.get_column_index('show_file')
        filename_col = self.get_column_index('filename')
        
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, checkbox_col)
            if checkbox and checkbox.isChecked():
                item = self.table.item(row, filename_col)
                if item:
                    file_path = item.data(Qt.UserRole)
                    if file_path:
                        selected_files.append(file_path)
        return selected_files
    
    def getVisibleFiles(self) -> List[str]:
        """Get list of all visible file paths."""
        visible_files = []
        filename_col = self.get_column_index('filename')
        
        for row in range(self.table.rowCount()):
            item = self.table.item(row, filename_col)
            if item:
                file_path = item.data(Qt.UserRole)
                if file_path:
                    visible_files.append(file_path)
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
            self, "Save table as...", 
            os.path.join(self.backend.root_path, "tif_table_export.csv"),
            "CSV Files (*.csv);;All Files (*)"
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
        # Find the row with this filename in the current filtered data
        filtered_df = self._getFilteredData()
        if filtered_df is None or len(filtered_df) == 0:
            return
        
        # Find the row index in the filtered data
        mask = filtered_df['filename'] == filename
        if not mask.any():
            return
        
        row_idx = mask.idxmax()
        # Convert to table row index
        table_row_idx = filtered_df.index.get_loc(row_idx)
        
        # Find the status column index
        try:
            status_col_idx = self.get_column_index('_KymRoiAnalysis_Loaded')
        except ValueError:
            # Status column not visible
            return
        
        # Check if the KymRoiAnalysis is loaded
        is_loaded = self.backend.df.loc[row_idx, '_KymRoiAnalysis_Loaded']
        
        # Update the table item
        if is_loaded:
            # Green circle for loaded
            item = QTableWidgetItem("●")
            item.setForeground(QtGui.QColor("#449944"))  # Green
        else:
            # Empty circle for not loaded
            item = QTableWidgetItem("○")
            item.setForeground(QtGui.QColor("#999999"))  # Gray
        
        item.setData(Qt.UserRole, filename)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(table_row_idx, status_col_idx, item) 