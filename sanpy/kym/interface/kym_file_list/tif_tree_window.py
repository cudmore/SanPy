#!/usr/bin/env python3
"""
Example script demonstrating the TifTreeWidget class.

This script creates a simple application that shows how to use the TifTreeWidget
to browse and select .tif files from a folder structure.
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton, QFileDialog, QCheckBox, QMenuBar, QMenu, QAction, QHBoxLayout, QTabWidget, QMessageBox
)
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from functools import partial
import sip

from sanpy.interface.sanpy_app import SanPyApp

from sanpy.kym.tif_file_backend import TifFileBackend
from sanpy.kym.interface.kym_file_list.tif_tree_widget import TifTreeWidget
from sanpy.kym.interface.kym_file_list.tif_table_view import TifTableView
from sanpy.kym.interface.preferences_dialog import PreferencesDialog
from sanpy.kym.interface.preferences_manager import preferences_manager

from sanpy.kym.logger import get_logger
logger = get_logger(__name__)

def yesNoCancelDialog(message, informativeText=None):
    """Simple yes/no/cancel dialog to avoid importing from sanpy.interface.bDialog."""
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setText(message)
    if informativeText is not None:
        msg.setInformativeText(informativeText)
    msg.setWindowTitle(message)
    msg.setStandardButtons(
        QMessageBox.Yes
        | QMessageBox.No
        | QMessageBox.Cancel
    )
    retval = msg.exec_()
    return retval

class TifTreeWindow(QMainWindow):
    def __init__(self, sanPyApp : SanPyApp, path=None):
        """
        Parameters
        ----------
        sanPyApp : SanPyApp
            Allows access to app wide info such as options, file loaders, plugins
        path : str
            Full path to folder with raw files (abf,csv,tif).
        """
        super().__init__()
        self.setWindowTitle("TifTreeWindow")
        self.setGeometry(100, 100, 1000, 700)
        
        self._sanPyApp : SanPyApp = sanPyApp
        self.path = path
        
        # Track open widgets: {widget_id: (widget_instance, label)}
        self.open_widgets = {}
        self.widget_counter = 0
        
        # Default path
        self.default_path = path
        
        # Create menu bar
        self.createMenuBar()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Create controls
        self.createControls(layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Initialize widgets (will be created when folder is selected)
        self.tree_widget = None
        self.table_widget = None
        self.backend = None
        
        # Connect signals
        self.connectSignals()
        
        # Initialize with default path if it exists
        if self.default_path and os.path.exists(self.default_path):
            self.initializeWidgets(self.default_path)
        else:
            self.statusBar().showMessage("No folder selected")

    def createMenuBar(self):
        """Create the menu bar with Windows menu."""
        menubar = self.menuBar()
        
        # Create File menu
        self.file_menu = QMenu("File", self)
        menubar.addMenu(self.file_menu)
        
        # Add Save table as... action
        self.save_table_action = QAction("Save table as...", self)
        self.save_table_action.setShortcut("Ctrl+S")
        self.save_table_action.setStatusTip("Save current table data to CSV file")
        self.save_table_action.setEnabled(False)  # Disabled until folder is loaded
        self.save_table_action.triggered.connect(self.saveTableAs)
        self.file_menu.addAction(self.save_table_action)
        
        # Create Settings menu
        self.settings_menu = QMenu("Settings", self)
        menubar.addMenu(self.settings_menu)
        
        # Add Preferences action
        self.preferences_action = QAction("Preferences...", self)
        self.preferences_action.setShortcut("Ctrl+,")
        self.preferences_action.setStatusTip("Open application preferences")
        self.preferences_action.triggered.connect(self.showPreferences)
        self.settings_menu.addAction(self.preferences_action)
        
        # Create Windows menu
        self.windows_menu = QMenu("Windows", self)
        menubar.addMenu(self.windows_menu)
        
        # Update the Windows menu
        self.updateWindowsMenu()

    def updateWindowsMenu(self):
        """Update the Windows menu with current open widgets."""
        # Robustness: Only update if menu and window are valid
        if not hasattr(self, 'windows_menu') or self.windows_menu is None:
            return
        if sip.isdeleted(self.windows_menu):
            return
        self.windows_menu.clear()
        if not self.open_widgets:
            no_windows_action = QAction("No windows open", self)
            no_windows_action.setEnabled(False)
            self.windows_menu.addAction(no_windows_action)
        else:
            for widget_id, (widget, label) in self.open_widgets.items():
                action = QAction(label, self)
                action.triggered.connect(partial(self.bringWidgetToFront, widget))
                self.windows_menu.addAction(action)

    def bringWidgetToFront(self, widget):
        """Bring the specified widget to the front."""
        if widget:
            widget.raise_()
            widget.activateWindow()

    def addOpenWidget(self, widget, label, widget_type="Widget"):
        """Add a widget to the tracking system."""
        self.widget_counter += 1
        widget_id = f"{widget_type} {self.widget_counter}"
        self.open_widgets[widget_id] = (widget, label)
        # Connect widget's closeEvent to remove from menu immediately
        orig_closeEvent = widget.closeEvent
        def new_closeEvent(ev):
            self.removeOpenWidget(widget_id)
            orig_closeEvent(ev)
        widget.closeEvent = new_closeEvent
        # Also connect destroyed for robustness
        widget.destroyed.connect(partial(self.removeOpenWidget, widget_id))
        self.updateWindowsMenu()
        return widget_id

    def removeOpenWidget(self, widget_id):
        """Remove a widget from the tracking system."""
        if widget_id in self.open_widgets:
            del self.open_widgets[widget_id]
            if hasattr(self, 'windows_menu') and self.windows_menu is not None:
                if not sip.isdeleted(self.windows_menu):
                    self.updateWindowsMenu()

    def createControls(self, layout):
        """Create control buttons for the top toolbar."""
        # Create horizontal layout for buttons
        button_layout = QHBoxLayout()
        
        # Load Folder button
        self.select_folder_btn = QPushButton("Load Folder")
        self.select_folder_btn.setToolTip("Select a folder containing .tif files to load")
        button_layout.addWidget(self.select_folder_btn)
        
        # Add some spacing
        button_layout.addSpacing(10)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Refresh the file list from disk")
        self.refresh_btn.setEnabled(False)  # Disabled until folder is loaded
        button_layout.addWidget(self.refresh_btn)
        
        # Save State button
        self.save_state_btn = QPushButton("Save State")
        self.save_state_btn.setToolTip("Save current selection state to CSV file")
        self.save_state_btn.setEnabled(False)  # Disabled until folder is loaded
        button_layout.addWidget(self.save_state_btn)
        
        # Add stretch to push buttons to the left
        button_layout.addStretch()
        
        # Add the button layout to the main layout
        layout.addLayout(button_layout)

    def connectSignals(self):
        """Connect button signals to slots."""
        self.select_folder_btn.clicked.connect(self.selectFolder)
        self.refresh_btn.clicked.connect(self.refreshData)
        self.save_state_btn.clicked.connect(self.saveState)

    def selectFolder(self):
        """Open folder dialog and initialize tree widget."""
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Folder Containing .tif Files",
            self.default_path if self.default_path and os.path.exists(self.default_path) else os.path.expanduser("~")
        )
        
        if folder_path:
            self.initializeWidgets(folder_path)

    def initializeWidgets(self, folder_path):
        """Initialize the tree and table widgets with the selected folder."""
        # Remove existing widgets if they exist
        if self.tree_widget:
            self.tree_widget.deleteLater()
        if self.table_widget:
            self.table_widget.deleteLater()
        
        # Create backend
        # abb sort_by_grandparent=True for opening tif exported from olympus
        self.backend = TifFileBackend(folder_path, exclude_folders=["sanpy-reports-pdf"], sort_by_grandparent=True)
        
        # Create new tree widget (default to no third level)
        self.tree_widget = TifTreeWidget(self.backend, show_third_level=False, parent=self)
        
        # Create new table widget
        self.table_widget = TifTableView(self.backend, parent=self)
        
        # Add widgets to tab widget
        self.tab_widget.addTab(self.table_widget, "Table View")
        self.tab_widget.addTab(self.tree_widget, "Tree View")
        
        # Update window title with folder name
        folder_name = os.path.basename(folder_path)
        self.setWindowTitle(f"{folder_name}")
        
        # Update status
        file_count = self.tree_widget.getFileCount()
        self.statusBar().showMessage(f"Folder: {folder_name} | Found {file_count} .tif files")
        
        # Enable the toolbar buttons now that we have a backend
        self.refresh_btn.setEnabled(True)
        self.save_state_btn.setEnabled(True)
        
        # Enable the save table action
        self.save_table_action.setEnabled(True)
        
        # Connect tree widget signals
        self.tree_widget.filesRefreshed.connect(self.onFilesRefreshed)
        self.tree_widget.fileSelected.connect(self.onFileSelected)
        self.tree_widget.folderSelected.connect(self.onFolderSelected)
        self.tree_widget.fileToggled.connect(self.onFileToggled)
        self.tree_widget.fileDoubleClicked.connect(self.onFileDoubleClicked)
        self.tree_widget.plotRoisRequested.connect(self.onPlotRoisRequested)
        self.tree_widget.stateSaved.connect(self.onStateSaved)
        
        # Connect table widget signals (only connect to signals that exist)
        self.table_widget.fileSelected.connect(self.onFileSelected)
        self.table_widget.fileToggled.connect(self.onFileToggled)
        self.table_widget.fileDoubleClicked.connect(self.onFileDoubleClicked)
        self.table_widget.plotRoisRequested.connect(self.onPlotRoisRequested)
        self.table_widget.loadKymAnalysisRequested.connect(self.onLoadKymAnalysisRequested)

    def onFilesRefreshed(self, absolute_path_list):
        """Called when files are refreshed."""
        logger.info(f"Files refreshed. Found {len(absolute_path_list)} .tif files")
        file_count = len(absolute_path_list)
        self.statusBar().showMessage(f"Refreshed: Found {file_count} .tif files")

    def onFileSelected(self, relative_path):
        """Called when a file is selected."""
        logger.info(f"File selected: {relative_path}")

    def onFolderSelected(self, absolute_path):
        """Called when a folder is selected."""
        logger.info(f"Folder selected: {absolute_path}")

    def onFileToggled(self, relative_path, checked):
        """Called when a file is checked/unchecked."""
        # self.showSelectedFiles()
        pass

    def onFileDoubleClicked(self, relative_path):
        """Called when a .tif file is double-clicked."""
        logger.info(f"File double-clicked: {relative_path}")
        # You can add custom actions here, such as opening the file
        # subprocess.run(['open', relative_path])  # Uncomment to open files
        
        from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis
        from sanpy.kym.interface.kymRoiWidget import KymRoiWidget
        
        # Create a custom KymRoiWidget that uses our local dialog function
        class CustomKymRoiWidget(KymRoiWidget):
            def closeEvent(self, event):
                logger.info('veto close if peak analysis is dirty')
                acceptAndContinue = True
                if self.isDirty():
                    logger.info('   kym peak analysis is dirty, prompt to save')

                    userResp = yesNoCancelDialog(
                        "There is analysis that is not saved.\nDo you want to save?"
                    )
                    if userResp == QtWidgets.QMessageBox.Yes:
                        logger.warning('TODO: actually save kym roi peaks')
                        self.saveAnalysis()
                        acceptAndContinue = True
                    elif userResp == QtWidgets.QMessageBox.No:
                        acceptAndContinue = True
                    else:  # userResp == QtWidgets.QMessageBox.Cancel:
                        acceptAndContinue = False
                
                if acceptAndContinue:
                    event.accept()
                else:
                    event.ignore()
        
        # Resolve the relative path to full path
        if self.backend:
            absolute_path = self.backend.resolve_path(relative_path)
            logger.info(f"Resolved relative path '{relative_path}' to absolute path '{absolute_path}'")
        else:
            # Fallback if no backend available
            absolute_path = relative_path
            logger.warning(f"No backend available, using path as-is: {relative_path}")
        
        logger.info(f"creating widget: {absolute_path}")
        
        aKymRoiAnalysis = KymRoiAnalysis(absolute_path)
        aWidget = CustomKymRoiWidget(aKymRoiAnalysis)
        
        # Add widget to tracking system, use tif file name as label
        tif_label = os.path.basename(relative_path)
        widget_id = self.addOpenWidget(aWidget, tif_label, "KymRoi")
        aWidget.setWindowTitle(f"KymRoi - {tif_label}")
        aWidget.show()

    def onPlotRoisRequested(self, relative_path):
        """Called when user selects 'Plot ROIs' from context menu."""
        logger.info(f"Plot ROIs requested for: {relative_path}")
        # You can add custom actions here, such as opening a plotting window
        
    def onLoadKymAnalysisRequested(self, relative_path):
        """Called when user selects 'Load Kym Analysis' from context menu."""
        logger.info(f"Load Kym Analysis requested for: {relative_path}")
        
        try:
            # Use the backend's lazy loading to get or create the KymRoiAnalysis
            kym_analysis = self.backend.get_kym_roi_analysis_by_path(relative_path)
            
            if kym_analysis is not None:
                # Get the filename for status update
                filename = os.path.basename(relative_path)
                # Update the table to show the loaded status
                self.table_widget.updateKymAnalysisStatus(filename)
                
                # Show success message
                self.statusBar().showMessage(f"KymRoiAnalysis loaded for: {filename}")
                
                logger.info(f"Successfully loaded KymRoiAnalysis for: {filename}")
            else:
                # Show error message
                self.statusBar().showMessage(f"Failed to load KymRoiAnalysis for: {relative_path}")
                
                logger.error(f"Failed to load KymRoiAnalysis for: {relative_path}")
                
        except Exception as e:
            logger.error(f"Error loading KymRoiAnalysis for {relative_path}: {e}")
            self.statusBar().showMessage(f"Error loading KymRoiAnalysis: {str(e)}")

    def onStateSaved(self, csv_filename):
        """Update the status bar when state is saved."""
        self.statusBar().showMessage(f"State saved to: {csv_filename}")

    def showSelectedFiles(self):
        """Show all currently checked files."""
        if not self.backend:
            return
        
        checked_files = self.backend.get('files')
        
        logger.info("\n=== Selected Files ===")
        for absolute_path in checked_files:
            logger.info(f"  {absolute_path}")
        
        logger.info(f"\nTotal: {len(checked_files)} files selected")

    def refreshData(self):
        """Refresh the data from disk."""
        if self.backend:
            logger.info("Refreshing data from disk")
            
            # Refresh the backend
            self.backend.refresh()
            
            # Refresh both widgets
            if self.tree_widget:
                self.tree_widget.refresh()
            if self.table_widget:
                self.table_widget.refresh()
            
            # Update status
            file_count = self.backend.get('file_count')
            folder_name = os.path.basename(self.backend.root_path)
            self.statusBar().showMessage(f"Refreshed: {folder_name} | Found {file_count} .tif files")
            
            logger.info(f"Data refreshed. Found {file_count} .tif files")
        else:
            logger.warning("No backend available to refresh")
    
    def saveState(self):
        """Save the current state to a CSV file."""
        if self.backend:
            logger.info("Saving current state")
            
            # Save state using the backend
            csv_filepath = self.backend.save_state()
            
            if csv_filepath:
                csv_filename = os.path.basename(csv_filepath)
                self.statusBar().showMessage(f"State saved to: {csv_filename}")
                logger.info(f"State saved to: {csv_filename}")
            else:
                self.statusBar().showMessage("Failed to save state")
                logger.error("Failed to save state")
        else:
            logger.warning("No backend available to save state")

    def saveTableAs(self):
        """Save the current table data to a CSV file."""
        if not self.table_widget:
            self.statusBar().showMessage("No table widget available")
            return
        
        # Get the table data
        table_data = self.table_widget.getTableData()
        
        if table_data is None or len(table_data) == 0:
            self.statusBar().showMessage("No table data to save")
            return
        
        # Show current status
        total_rows = len(table_data)
        self.statusBar().showMessage(f"Saving {total_rows} rows of table data...")
        
        # Save the table data to a CSV file
        csv_filepath = self.table_widget.saveTableDataToCSV(table_data)
        
        if csv_filepath:
            csv_filename = os.path.basename(csv_filepath)
            self.statusBar().showMessage(f"Table saved: {csv_filename} ({total_rows} rows)")
            logger.info(f"Table saved to: {csv_filepath} ({total_rows} rows)")
        else:
            self.statusBar().showMessage("Save cancelled or failed")
            logger.warning("Table save was cancelled or failed")

    def showPreferences(self):
        """Show the preferences dialog."""
        dialog = PreferencesDialog(self)
        
        # Connect the preferences saved signal
        dialog.preferencesSaved.connect(self.onPreferencesSaved)
        
        # Show the dialog
        dialog.exec_()
    
    def onPreferencesSaved(self, preferences):
        """Called when preferences are saved."""
        logger.info("Preferences saved")
        self.statusBar().showMessage("Preferences saved successfully")
        
        # You can add code here to apply preferences to the current application state
        # For example, if the Olympus Export preference changed, you might need to
        # reload the current data or update the UI accordingly
        
        # Example: Check if Olympus Export preference changed
        olympus_export = preferences.get('Load Kymograph', {}).get('olympus_export', False)
        logger.info(f"Olympus Export setting: {olympus_export}")
        
        # If you have a backend loaded, you might want to refresh it with new settings
        if self.backend:
            # You could add a method to the backend to reload with new preferences
            # self.backend.reloadWithPreferences(preferences)
            pass

def main():
    """Main function to run the example."""
    # Set dark theme before creating QApplication
    try:
        import qdarktheme
        qdarktheme.enable_hi_dpi()
    except ImportError:
        print("qdarktheme not available, using default theme")
    
    from sanpy.interface.sanpy_app import SanPyApp
    sanPyApp = SanPyApp(sys.argv)
    
    # app = QApplication(sys.argv)
    
    # Apply dark theme after QApplication is created
    # try:
    #     import qdarktheme
    #     qdarktheme.setup_theme("dark")
    # except ImportError:
    #     pass
    
    # Default path to use
    default_path = "/Users/cudmore/Dropbox/data/colin/2025/mito-atp/mito-atp-20250623-RHC"
    
    # Create and show the main window
    window = TifTreeWindow(sanPyApp=sanPyApp, path=default_path)
    window.show()
    
    # Run the application
    sys.exit(sanPyApp.exec_())

if __name__ == "__main__":
    main() 