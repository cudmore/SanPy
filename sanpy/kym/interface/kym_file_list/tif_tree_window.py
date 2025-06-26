#!/usr/bin/env python3
"""
Example script demonstrating the TifTreeWidget class.

This script creates a simple application that shows how to use the TifTreeWidget
to browse and select .tif files from a folder structure.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton, QFileDialog, QCheckBox, QMenuBar, QMenu, QAction, QHBoxLayout
from PyQt5.QtCore import Qt
from functools import partial
import sip

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

from sanpy.kym.tif_file_backend import TifFileBackend
from sanpy.kym.interface.kym_file_list.tif_tree_widget import TifTreeWidget

class TifTreeWindow(QMainWindow):
    def __init__(self, path=None):
        super().__init__()
        self.setWindowTitle("TifTreeWidget Example")
        self.setGeometry(100, 100, 800, 600)
        
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
        
        # Create tree widget (will be initialized when folder is selected)
        self.tree_widget = None
        self.backend = None
        
        # Connect signals
        self.connectSignals()
        
        # Initialize with default path if it exists
        if self.default_path and os.path.exists(self.default_path):
            self.initializeTreeWidget(self.default_path)
        else:
            self.statusBar().showMessage("No folder selected")

    def createMenuBar(self):
        """Create the menu bar with Windows menu."""
        menubar = self.menuBar()
        
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
        """Create control buttons."""
        # Create horizontal layout for buttons
        button_layout = QHBoxLayout()
        
        # Select folder button
        self.select_folder_btn = QPushButton("Load Folder")
        self.select_folder_btn.setToolTip("Select a folder containing .tif files to load")
        button_layout.addWidget(self.select_folder_btn)
        
        # Add stretch to push buttons to the left
        button_layout.addStretch()
        
        # Add the button layout to the main layout
        layout.addLayout(button_layout)

    def connectSignals(self):
        """Connect button signals to slots."""
        self.select_folder_btn.clicked.connect(self.selectFolder)

    def selectFolder(self):
        """Open folder dialog and initialize tree widget."""
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Folder Containing .tif Files",
            self.default_path if self.default_path and os.path.exists(self.default_path) else os.path.expanduser("~")
        )
        
        if folder_path:
            self.initializeTreeWidget(folder_path)

    def initializeTreeWidget(self, folder_path):
        """Initialize the tree widget with the selected folder."""
        # Remove existing tree widget if it exists
        if self.tree_widget:
            self.tree_widget.deleteLater()
        
        # Create backend
        self.backend = TifFileBackend(folder_path, exclude_folders=["sanpy-reports-pdf"])
        
        # Create new tree widget (default to no third level)
        self.tree_widget = TifTreeWidget(self.backend, show_third_level=False, parent=self)
        
        # Add to layout
        layout = self.centralWidget().layout()
        layout.addWidget(self.tree_widget)
        
        # Update window title with folder name
        folder_name = os.path.basename(folder_path)
        self.setWindowTitle(f"TifTreeWidget Example - {folder_name}")
        
        # Update status
        file_count = self.tree_widget.getFileCount()
        self.statusBar().showMessage(f"Folder: {folder_name} | Found {file_count} .tif files")
        
        # Connect tree widget signals
        self.tree_widget.filesRefreshed.connect(self.onFilesRefreshed)
        self.tree_widget.fileSelected.connect(self.onFileSelected)
        self.tree_widget.folderSelected.connect(self.onFolderSelected)
        self.tree_widget.fileToggled.connect(self.onFileToggled)
        self.tree_widget.fileDoubleClicked.connect(self.onFileDoubleClicked)
        self.tree_widget.plotRoisRequested.connect(self.onPlotRoisRequested)
        self.tree_widget.stateSaved.connect(self.onStateSaved)

    def onFilesRefreshed(self, file_list):
        """Called when files are refreshed."""
        logger.info(f"Files refreshed. Found {len(file_list)} .tif files")
        file_count = len(file_list)
        self.statusBar().showMessage(f"Refreshed: Found {file_count} .tif files")

    def onFileSelected(self, file_path):
        """Called when a file is selected."""
        logger.info(f"File selected: {file_path}")

    def onFolderSelected(self, folder_path):
        """Called when a folder is selected."""
        logger.info(f"Folder selected: {folder_path}")

    def onFileToggled(self, file_path, checked):
        """Called when a file is checked/unchecked."""
        # self.showSelectedFiles()
        pass

    def onFileDoubleClicked(self, file_path):
        """Called when a .tif file is double-clicked."""
        logger.info(f"File double-clicked: {file_path}")
        # You can add custom actions here, such as opening the file
        # subprocess.run(['open', file_path])  # Uncomment to open files
        from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis
        from sanpy.kym.interface.kymRoiWidget import KymRoiWidget
        aKymRoiAnalysis = KymRoiAnalysis(file_path)
        aWidget = KymRoiWidget(aKymRoiAnalysis)
        
        # Add widget to tracking system, use tif file name as label
        tif_label = os.path.basename(file_path)
        widget_id = self.addOpenWidget(aWidget, tif_label, "KymRoi")
        aWidget.setWindowTitle(f"KymRoi - {tif_label}")
        aWidget.show()

    def onPlotRoisRequested(self, tif_file_path):
        """Called when user selects 'Plot ROIs' from context menu."""
        logger.info(f"Plot ROIs requested for: {tif_file_path}")
        
        try:
            from sanpy.kym.simple_scatter.colin_pool_plot import plotOneKym
            from sanpy.kym.simple_scatter.colin_simple_figure import KymRoiMainWindow
            
            # Create the plot
            fig, ax = plotOneKym(tif_file_path)
            
            # Create the widget
            plot_widget = KymRoiMainWindow(fig, ax)
            
            # Track this widget (but don't add to Windows menu)
            self.widget_counter += 1
            widget_id = f"Plot {self.widget_counter}"
            self.open_widgets[widget_id] = (plot_widget, f"Plot - {os.path.basename(tif_file_path)}")
            
            # Connect widget's closeEvent to remove from tracking
            orig_closeEvent = plot_widget.closeEvent
            def new_closeEvent(ev):
                if widget_id in self.open_widgets:
                    del self.open_widgets[widget_id]
                orig_closeEvent(ev)
            plot_widget.closeEvent = new_closeEvent
            
            # Also connect destroyed for robustness
            plot_widget.destroyed.connect(partial(self.removeOpenWidget, widget_id))
            
            # Set window title and show
            plot_widget.setWindowTitle(f"Plot - {os.path.basename(tif_file_path)}")
            plot_widget.show()
            
        except Exception as e:
            logger.error(f"Error creating plot for {tif_file_path}: {e}")
            # Could show a QMessageBox here if desired

    def onStateSaved(self, csv_filename):
        """Update the status bar when state is saved."""
        self.statusBar().showMessage(f"State saved to: {csv_filename}")

    def showSelectedFiles(self):
        """Show all currently checked files."""
        if not self.tree_widget:
            return
        
        checked_files = self.tree_widget.getCheckedFiles()
        checked_folders = self.tree_widget.getCheckedFolders()
        checked_grandparents = self.tree_widget.getCheckedGrandparents()
        checked_great_grandparents = self.tree_widget.getCheckedGreatGrandparents()
        
        logger.info("\n=== Selected Files ===")
        for file_path in checked_files:
            logger.info(f"  {file_path}")
        
        logger.info("\n=== Selected Folders ===")
        for folder_path in checked_folders:
            logger.info(f"  {folder_path}")
        
        logger.info("\n=== Selected Grandparents ===")
        for grandparent_name in checked_grandparents:
            logger.info(f"  {grandparent_name}")
        
        logger.info("\n=== Selected Great-Grandparents ===")
        for great_grandparent_name in checked_great_grandparents:
            logger.info(f"  {great_grandparent_name}")
        
        logger.info(f"\nTotal: {len(checked_files)} files, {len(checked_folders)} folders, {len(checked_grandparents)} grandparents, {len(checked_great_grandparents)} great-grandparents")

def main():
    """Main function to run the example."""
    # Set dark theme before creating QApplication
    try:
        import qdarktheme
        qdarktheme.enable_hi_dpi()
    except ImportError:
        print("qdarktheme not available, using default theme")
    
    app = QApplication(sys.argv)
    
    # Apply dark theme after QApplication is created
    try:
        import qdarktheme
        qdarktheme.setup_theme("dark")
    except ImportError:
        pass
    
    # Default path to use
    default_path = "/Users/cudmore/Dropbox/data/colin/2025/mito-atp/mito-atp-20250623-RHC"
    
    # Create and show the main window
    window = TifTreeWindow(path=default_path)
    window.show()
    
    # Run the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 