import sys
import os
import subprocess
from typing import List, Optional, Dict, Any

import matplotlib.pyplot as plt

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QHBoxLayout, QPushButton, QApplication, QCheckBox
)
from PyQt5.QtCore import pyqtSignal, Qt
import pandas as pd

from sanpy.kym.logger import get_logger
logger = get_logger(__name__)

from sanpy.kym.tif_file_backend import TifFileBackend

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
    
    # Emitted when state is saved
    stateSaved = pyqtSignal(str)  # csv_filename

    def __init__(self, backend: TifFileBackend, show_third_level: bool = False, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.show_third_level = show_third_level
        
        # Set up context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenu)
        
        # Create UI elements
        self._createUI()
        
        # Initial population
        self._populateTree()

    def _createUI(self):
        """Create the user interface elements."""
        # Create Refresh button
        self.refreshButton = QPushButton("Refresh")
        self.refreshButton.clicked.connect(self.refresh)
        self.refreshButton.setToolTip("Refresh the file list from disk")
        
        # Create Save State button
        self.saveStateButton = QPushButton("Save State")
        self.saveStateButton.clicked.connect(self.saveState)
        self.saveStateButton.setToolTip("Save current selection state to CSV file")
        
        # Create button layout - all buttons in one row
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.refreshButton)
        buttonLayout.addWidget(self.saveStateButton)
        buttonLayout.addStretch()
        
        # Create tree with multiple columns
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Files and Folders", "Condition", "Repeat"])
        self.tree.itemChanged.connect(self.handleItemChanged)
        self.tree.itemSelectionChanged.connect(self.handleItemSelectionChanged)
        self.tree.itemDoubleClicked.connect(self.handleItemDoubleClicked)
        
        # Set column widths
        self.tree.setColumnWidth(0, 300)  # Files and Folders
        self.tree.setColumnWidth(1, 100)  # Condition
        self.tree.setColumnWidth(2, 80)   # Repeat
        
        # Main layout
        layout = QVBoxLayout()
        layout.addLayout(buttonLayout)
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
        great_grandparents = [gg for gg in great_grandparents if gg]  # Remove empty strings
        
        if great_grandparents:
            # We have great-grandparent folders, use the original logic
            for great_grandparent_name in sorted(great_grandparents):
                # Create great-grandparent item (no checkbox, just for display)
                great_grandparent_item = QTreeWidgetItem([great_grandparent_name, "", ""])
                great_grandparent_item.setFlags(great_grandparent_item.flags() | Qt.ItemIsSelectable)
                great_grandparent_item.setData(0, Qt.UserRole, ("great_grandparent", great_grandparent_name))
                
                # Get grandparent folders for this great-grandparent
                grandparent_data = self.backend.df[self.backend.df['great_grandparent_folder'] == great_grandparent_name]
                grandparents = grandparent_data['grandparent_folder'].unique()
                grandparents = [gp for gp in grandparents if gp]  # Remove empty strings
                
                for grandparent_name in sorted(grandparents):
                    # Create grandparent item (no checkbox, just for display)
                    grandparent_item = QTreeWidgetItem([grandparent_name, "", ""])
                    grandparent_item.setFlags(grandparent_item.flags() | Qt.ItemIsSelectable)
                    grandparent_item.setData(0, Qt.UserRole, ("grandparent", grandparent_name))
                    
                    # Get data for this grandparent
                    parent_data = grandparent_data[grandparent_data['grandparent_folder'] == grandparent_name]
                    
                    if self.show_third_level:
                        # Three-level structure: great_grandparent -> grandparent -> folder -> files
                        folders = parent_data['parent_folder'].unique()
                        folders = [f for f in folders if f]  # Remove empty strings
                        
                        for folder_name in sorted(folders):
                            # Create folder item (no checkbox, just for display)
                            folder_item = QTreeWidgetItem([folder_name, "", ""])
                            folder_item.setFlags(folder_item.flags() | Qt.ItemIsSelectable)
                            folder_item.setData(0, Qt.UserRole, ("folder", folder_name))
                            
                            # Add .tif files as children (with checkboxes)
                            folder_data = parent_data[parent_data['parent_folder'] == folder_name]
                            for _, row in folder_data.iterrows():
                                file_item = QTreeWidgetItem([
                                    row['filename'], 
                                    row['condition'], 
                                    str(row['repeat'])
                                ])
                                file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                                file_item.setCheckState(0, Qt.Checked if row['show_file'] else Qt.Unchecked)
                                file_item.setData(0, Qt.UserRole, ("file", row['full_path']))
                                folder_item.addChild(file_item)
                            
                            grandparent_item.addChild(folder_item)
                    else:
                        # Two-level structure: great_grandparent -> grandparent -> files
                        # Add .tif files directly as children of grandparent (with checkboxes)
                        for _, row in parent_data.iterrows():
                            file_item = QTreeWidgetItem([
                                row['filename'], 
                                row['condition'], 
                                str(row['repeat'])
                            ])
                            file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                            file_item.setCheckState(0, Qt.Checked if row['show_file'] else Qt.Unchecked)
                            file_item.setData(0, Qt.UserRole, ("file", row['full_path']))
                            grandparent_item.addChild(file_item)
                    
                    great_grandparent_item.addChild(grandparent_item)
                
                self.tree.addTopLevelItem(great_grandparent_item)
                great_grandparent_item.setExpanded(True)
        else:
            # No great-grandparent folders, create top-level items for grandparent folders
            grandparents = self.backend.df['grandparent_folder'].unique()
            grandparents = [gp for gp in grandparents if gp]  # Remove empty strings
            
            for grandparent_name in sorted(grandparents):
                # Create grandparent item (no checkbox, just for display)
                grandparent_item = QTreeWidgetItem([grandparent_name, "", ""])
                grandparent_item.setFlags(grandparent_item.flags() | Qt.ItemIsSelectable)
                grandparent_item.setData(0, Qt.UserRole, ("grandparent", grandparent_name))
                
                # Get data for this grandparent
                parent_data = self.backend.df[self.backend.df['grandparent_folder'] == grandparent_name]
                
                if self.show_third_level:
                    # Three-level structure: grandparent -> folder -> files
                    folders = parent_data['parent_folder'].unique()
                    folders = [f for f in folders if f]  # Remove empty strings
                    
                    for folder_name in sorted(folders):
                        # Create folder item (no checkbox, just for display)
                        folder_item = QTreeWidgetItem([folder_name, "", ""])
                        folder_item.setFlags(folder_item.flags() | Qt.ItemIsSelectable)
                        folder_item.setData(0, Qt.UserRole, ("folder", folder_name))
                        
                        # Add .tif files as children (with checkboxes)
                        folder_data = parent_data[parent_data['parent_folder'] == folder_name]
                        for _, row in folder_data.iterrows():
                            file_item = QTreeWidgetItem([
                                row['filename'], 
                                row['condition'], 
                                str(row['repeat'])
                            ])
                            file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                            file_item.setCheckState(0, Qt.Checked if row['show_file'] else Qt.Unchecked)
                            file_item.setData(0, Qt.UserRole, ("file", row['full_path']))
                            folder_item.addChild(file_item)
                        
                        grandparent_item.addChild(folder_item)
                else:
                    # Two-level structure: grandparent -> files
                    # Add .tif files directly as children of grandparent (with checkboxes)
                    for _, row in parent_data.iterrows():
                        file_item = QTreeWidgetItem([
                            row['filename'], 
                            row['condition'], 
                            str(row['repeat'])
                        ])
                        file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                        file_item.setCheckState(0, Qt.Checked if row['show_file'] else Qt.Unchecked)
                        file_item.setData(0, Qt.UserRole, ("file", row['full_path']))
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
            contextMenu.addAction('Open File')
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
                great_grandparent_path = os.path.join(self.backend.root_path, great_grandparent_name)
                if os.path.exists(great_grandparent_path):
                    subprocess.run(['open', great_grandparent_path])
            elif data[0] == "grandparent":
                # Find the actual path for grandparent
                grandparent_name = data[1]
                grandparent_path = os.path.join(self.backend.root_path, grandparent_name)
                if os.path.exists(grandparent_path):
                    subprocess.run(['open', grandparent_path])
            elif data[0] == "folder":
                subprocess.run(['open', data[1]])
            elif data[0] == "file":
                subprocess.run(['open', '-R', data[1]])
        elif actionText == 'Open File':
            if data[0] == "file":
                subprocess.run(['open', data[1]])
        elif actionText == 'Copy Path':
            if data[0] == "file":
                clipboard = QApplication.clipboard()
                clipboard.setText(data[1])

    def handleItemChanged(self, item, column):
        """Handle checkbox state changes for individual files."""
        data = item.data(0, Qt.UserRole)
        if data is None:
            return

        # Only handle file checkboxes
        if data[0] == "file":
            file_path = data[1]
            checked = item.checkState(0) == Qt.Checked
            
            # Update backend
            self.backend.set_checked('file', file_path, checked)
            
            # Emit signal
            self.fileToggled.emit(file_path, checked)

        self.tree.itemChanged.connect(self.handleItemChanged)

    def handleItemSelectionChanged(self):
        """Handle item selection changes."""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        data = item.data(0, Qt.UserRole)
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
        data = item.data(0, Qt.UserRole)
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
                self.backend.set_checked('file', row['full_path'], checked)
            
            # Update tree display to reflect the changes
            self._rebuildTreeDisplay()

    def saveState(self):
        """Save the current state to a CSV file."""
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()  # Ensure all checkbox changes are committed
        if self.backend:
            csv_filepath = self.backend.save_state()
            if csv_filepath:
                csv_filename = os.path.basename(csv_filepath)
                self.stateSaved.emit(csv_filename)
                logger.info(f"State saved to: {csv_filename}") 