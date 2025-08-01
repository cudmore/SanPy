#!/usr/bin/env python3
"""
Example script demonstrating the TifTreeWidget class.

This script creates a simple application that shows how to use the TifTreeWidget
to browse and select .tif files from a folder structure.
"""

import sys
import os
from PyQt5.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QLabel,
    QPushButton,
    QFileDialog,
    QCheckBox,
    QMenuBar,
    QMenu,
    QAction,
    QHBoxLayout,
    QTabWidget,
    QMessageBox,
)
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt
from functools import partial
import sip

from sanpy.interface.sanpy_app import SanPyApp

from sanpy.kym.tif_file_backend import TifFileBackend
from sanpy.kym.interface.kym_file_list.tif_tree_widget import TifTreeWidget
from sanpy.kym.interface.kym_file_list.tif_table_view import TifTableView
from sanpy.kym.interface.preferences_dialog import PreferencesDialog
from sanpy.kym.interface.preferences_manager import preferences_manager
from sanpy.kym.interface.tif_pool_scatter import ScatterWidget
from sanpy.interface.progress_widget.progress_widget import ProgressWidget, get_progress_callback, ProgressDialog

from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


def yesNoCancelDialog(message, informativeText=None):
    """Simple yes/no/cancel dialog to avoid importing from sanpy.interface.bDialog."""
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setText(message)
    if informativeText is not None:
        msg.setInformativeText(informativeText)
    msg.setWindowTitle(message)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
    retval = msg.exec_()
    return retval


def get_folder_hierarchy_title(folder_path):
    """
    Extract parent and grandparent folder names for display in window title.
    
    Parameters
    ----------
    folder_path : str
        Full path to the folder
        
    Returns
    -------
    str
        Formatted title showing parent/grandparent folders, or just folder name if not enough levels
    """
    try:
        # Split the path into components
        path_parts = folder_path.split(os.sep)
        
        # Remove empty parts (can happen with leading/trailing separators)
        path_parts = [part for part in path_parts if part]
        
        if len(path_parts) >= 3:
            # We have enough levels: show grandparent/parent/current
            grandparent = path_parts[-3]
            parent = path_parts[-2]
            current = path_parts[-1]
            return f"{grandparent} / {parent} / {current}"
        elif len(path_parts) == 2:
            # Two levels: show parent/current
            parent = path_parts[-2]
            current = path_parts[-1]
            return f"{parent} / {current}"
        else:
            # Single level or root: just show the folder name
            return path_parts[-1] if path_parts else "Unknown"
    except Exception:
        # Fallback to just the folder name if anything goes wrong
        return os.path.basename(folder_path)


class TifTreeWindow(QMainWindow):
    def __init__(self,
                 sanPyApp: SanPyApp,
                 path:str):
        """
        Parameters
        ----------
        sanPyApp : SanPyApp
            Allows access to app wide info such as options, file loaders, plugins
        path : str
            Full path to folder with raw files (tif).
        """
        super().__init__()
        self.setWindowTitle("TifTreeWindow")
        self.setGeometry(100, 100, 1000, 700)

        self._sanPyApp: SanPyApp = sanPyApp
        self.path = path  # abb is this used?

        # Track open widgets: {widget_id: (widget_instance, label)}
        self.open_widgets = {}
        self.widget_counter = 0
        
        # Track TifPoolScatter widget separately for checkable menu
        self.tif_pool_scatter_widget = None

        # Create menu bar
        self.createMenuBar()

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create layout
        layout = QVBoxLayout(central_widget)

        # Create controls
        self.createControls(layout)

        # Create progress widget (hidden by default)
        self.progress_widget = ProgressWidget(parent=self)
        layout.addWidget(self.progress_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Initialize widgets (will be created when folder is selected)
        self.tree_widget = None
        self.table_widget = None
        self.backend = None

        # Connect signals
        # self.connectSignals()

        # Close window shortcut: platform-independent (Ctrl+W or Cmd+W)
        shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Close), self)
        shortcut.activated.connect(self.close)

        # Initialize with default path if it exists
        if os.path.exists(self.path):
            self.initializeWidgets(self.path)
        else:
            self.statusBar().showMessage(f"Folder not found: {self.path}")

    def closeEvent(self, event):
        logger.info('')
        # check if we have any dirty kymRoiAnalysis
        doCloseWindow = True
        for widget_id, (widget, label) in self.open_widgets.items():
            if widget.isDirty():
                doCloseWindow = False
                userResp = yesNoCancelDialog(
                    f"{label} has analysis that is not saved.\nDo you want to save?"
                )
                if userResp == QtWidgets.QMessageBox.Yes:
                    widget.saveAnalysis()
                    widget.close()
                    doCloseWindow = True
                elif userResp == QtWidgets.QMessageBox.No:
                    widget.close()
                    doCloseWindow = True
                else:  # userResp == QtWidgets.QMessageBox.Cancel:
                    # cancel
                    doCloseWindow = False
                    break

        if doCloseWindow:
            self._sanPyApp.closeSanPyWindow(self)

    def createMenuBar(self):
        """Create the menu bar using SanPyApp menu structure."""
        menubar = self.menuBar()
        
        # Get the SanPyApp menu structure and insert our menus before Help
        _helpAction = self._sanPyApp._buildMenus(menubar)
        
        # Create our custom Kym menu
        self._createKymMenu(menubar, _helpAction)
        
        # Create Windows menu (similar to SanPyWindow)
        self._createWindowsMenu(menubar, _helpAction)
        
        # Update the Windows menu
        self.updateWindowsMenu()

    def _createKymMenu(self, menubar: QMenuBar, helpAction: QAction):
        """Create the Kym menu and insert it before Help."""
        self.kym_menu = QMenu("Kym", self)
        menubar.insertMenu(helpAction, self.kym_menu)
        
        # Add TifPoolScatter action (checkable) to the Kym menu
        self.tif_pool_scatter_action = QAction("Tif Pool Scatter", self)
        self.tif_pool_scatter_action.setStatusTip("Open/Close TifPoolScatter window")
        self.tif_pool_scatter_action.setCheckable(True)
        self.tif_pool_scatter_action.setEnabled(False)  # Will be enabled when backend is created
        self.tif_pool_scatter_action.triggered.connect(self.toggleTifPoolScatter)
        self.kym_menu.addAction(self.tif_pool_scatter_action)

        # Add 'Show Folder In Finder' action
        show_folder_action = QAction("Show Folder In Finder", self)
        show_folder_action.setStatusTip("Show the current folder in the system file explorer")
        show_folder_action.setEnabled(True)
        def _show_folder_in_finder():
            import subprocess, sys
            folder_path = self.path
            if os.path.exists(folder_path):
                if sys.platform == "darwin":
                    subprocess.run(["open", folder_path])
                elif sys.platform == "win32":
                    subprocess.run(["explorer", folder_path])
                else:
                    subprocess.run(["xdg-open", folder_path])
        show_folder_action.triggered.connect(_show_folder_in_finder)
        self.kym_menu.addSeparator()
        self.kym_menu.addAction(show_folder_action)
        
        self.kym_menu.addSeparator()

        # add a refresh folder action to the Kym menu
        refresh_folder_action = QAction("Refresh Folder", self)
        refresh_folder_action.setStatusTip("Refresh the file list from disk (add new and remove deleted tif files)")
        refresh_folder_action.setEnabled(True)  # self.path always exists
        refresh_folder_action.triggered.connect(self.refreshData)
        self.kym_menu.addAction(refresh_folder_action)
        
        # add a 'Rebuild Folder Database' action to the Kym menu
        rebuild_database_action = QAction("Rebuild Folder Database", self)
        rebuild_database_action.setStatusTip("Force re-analysis of all files (expensive operation)")
        rebuild_database_action.setEnabled(True)  # self.path always exists
        rebuild_database_action.triggered.connect(self.forceReanalyzeAll)
        self.kym_menu.addAction(rebuild_database_action)
        
        # add an 'Unload all analysis' action to the Kym menu
        self.unload_all_analysis_action = QAction("Unload all analysis", self)
        self.unload_all_analysis_action.setStatusTip("Unload all KymRoiAnalysis objects from memory to free up resources")
        self.unload_all_analysis_action.setEnabled(False)  # Will be enabled when backend is created
        self.unload_all_analysis_action.triggered.connect(self.unloadAllAnalysis)
        self.kym_menu.addAction(self.unload_all_analysis_action)
                
    def _createWindowsMenu(self, menubar, helpAction):
        """Create the Windows menu and insert it before Help."""
        self.windows_menu = QMenu("Windows", self)
        menubar.insertMenu(helpAction, self.windows_menu)
        self.windows_menu.aboutToShow.connect(self._refreshWindowsMenu)

    def _refreshWindowsMenu(self):
        """Refresh the Windows menu with current open widgets."""
        self.windows_menu.clear()
        
        # Add SanPyApp's windows
        self._sanPyApp.getWindowsMenu(self.windows_menu)
        
        self.windows_menu.addSeparator()
        
        # Add our open widgets
        if not self.open_widgets:
            no_windows_action = QAction("No kymograph windows open", self)
            no_windows_action.setEnabled(False)
            self.windows_menu.addAction(no_windows_action)
        else:
            for widget_id, (widget, label) in self.open_widgets.items():
                action = QAction(label, self)
                action.triggered.connect(partial(self.bringWidgetToFront, widget))
                self.windows_menu.addAction(action)

    def updateWindowsMenu(self):
        """Update the Windows menu with current open widgets."""
        # Robustness: Only update if menu and window are valid
        if not hasattr(self, 'windows_menu') or self.windows_menu is None:
            return
        if sip.isdeleted(self.windows_menu):
            return
        self._refreshWindowsMenu()
        
        # Update Kym menu action states
        if hasattr(self, 'tif_pool_scatter_action'):
            # Update enabled state based on backend availability
            self.tif_pool_scatter_action.setEnabled(hasattr(self, 'backend') and self.backend is not None)
            # Update checked state based on widget existence
            self.tif_pool_scatter_action.setChecked(self.tif_pool_scatter_widget is not None)
            
        # Update unload all analysis action state
        if hasattr(self, 'unload_all_analysis_action'):
            # Enable if backend exists and has loaded analysis
            has_loaded_analysis = (hasattr(self, 'backend') and 
                                 self.backend is not None and 
                                 self.backend.get_cached_kym_roi_analysis_count() > 0)
            self.unload_all_analysis_action.setEnabled(has_loaded_analysis)

    def bringWidgetToFront(self, widget):
        """Bring the specified widget to the front."""
        if widget:
            widget.raise_()
            widget.activateWindow()

    def addOpenWidget(self,
                      widget,
                      label,
                      widget_type="Widget"):
        """Add a widget to the tracking system."""
        self.widget_counter += 1
        widget_id = f"{widget_type} {self.widget_counter}"
        self.open_widgets[widget_id] = (widget, label)
        # Connect widget's closeEvent to remove from menu immediately
        orig_closeEvent = widget.closeEvent

        def new_closeEvent(ev):
            logger.info(f'removeOpenWidget:{widget_id}')
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
        return
    
        """
        button_layout = QHBoxLayout()

        # Add some spacing
        # button_layout.addSpacing(10)

        # Refresh Folder button
        self.refresh_btn = QPushButton("Refresh Folder")
        self.refresh_btn.setToolTip("Refresh the file list from disk (add new and remove deleted tif files)")
        self.refresh_btn.setEnabled(False)  # Disabled until folder is loaded
        button_layout.addWidget(self.refresh_btn)

        # Add stretch to push buttons to the left
        button_layout.addStretch()

        # Add the button layout to the main layout
        layout.addLayout(button_layout)
        """

    def initializeWidgets(self, folder_path):
        """Initialize the tree and table widgets with the selected folder."""
        # Remove existing widgets if they exist
        if self.tree_widget:
            self.tree_widget.deleteLater()
        if self.table_widget:
            self.table_widget.deleteLater()

        # Create backend
        # abb sort_by_grandparent=True for opening tif exported from olympus
        self.backend = TifFileBackend(
            folder_path,
            exclude_folders=["sanpy-reports-pdf"],
            sort_by_grandparent=True,
            load_analysis_csv=False  # abb 20250714 turned off
        )
        # Save state CSV only if it does not already exist
        state_csv_path = self.backend._get_state_filepath()
        if not os.path.exists(state_csv_path):
            self.backend.save_state()
        
        # Create TiffPool for analysis data management
        from sanpy.kym.tif_pool import TiffPool
        self.backend._tifPool = TiffPool(
            self.backend,
            group_columns=['Cell ID', 'Condition', 'ROI Label', 'Channel'],
            metadata_columns=['Region', 'Date', 'Repeat', 'Analysis Type', 'Channel', 'Polarity']
        )
        
        # Intelligently initialize TiffPool data
        self._initialize_tiff_pool_data()
        
        logger.info("Created TiffPool for analysis data management")

        # Create new tree widget (default to no third level)
        self.tree_widget = TifTreeWidget(
            self.backend, show_third_level=False, parent=self
        )
        # Create new table widget
        self.table_widget = TifTableView(self.backend, parent=self)
        self.table_widget.statusBarMessage.connect(self.statusBar().showMessage)

        # Add widgets to tab widget
        self.tab_widget.addTab(self.table_widget, "Table View")
        self.tab_widget.addTab(self.tree_widget, "Tree View")

        # Update window title with folder name
        folder_name = get_folder_hierarchy_title(folder_path)
        self.setWindowTitle(f"{folder_name}")

        # Update status
        file_count = self.tree_widget.getFileCount()
        self.statusBar().showMessage(
            f"Folder: {folder_name} | Found {file_count} .tif files"
        )

        # Connect tree widget signals
        self.tree_widget.filesRefreshed.connect(self.onFilesRefreshed)
        self.tree_widget.fileSelected.connect(self.onFileSelected)
        self.tree_widget.folderSelected.connect(self.onFolderSelected)
        self.tree_widget.fileToggled.connect(self.onFileToggled)
        self.tree_widget.fileDoubleClicked.connect(self.onFileDoubleClicked)
        self.tree_widget.plotRoisRequested.connect(self.onPlotRoisRequested)

        # Connect table widget signals (only connect to signals that exist)
        self.table_widget.fileSelected.connect(self.onFileSelected)
        self.table_widget.fileToggled.connect(self.onFileToggled)
        self.table_widget.fileDoubleClicked.connect(self.onFileDoubleClicked)
        self.table_widget.plotRoisRequested.connect(self.onPlotRoisRequested)
        
        # Update Windows menu and enable actions now that backend exists
        self.updateWindowsMenu()

    def _initialize_tiff_pool_data(self):
        """
        Intelligently initialize TiffPool data based on what's available.
        
        This method checks if main/mean CSV files exist and loads them.
        If they don't exist but kymRoiAnalysis files are available, it generates
        the pooled data from the analysis files.
        """
        tiff_pool = self.backend._tifPool
        
        # Check if main/mean CSV files exist
        main_csv_exists = os.path.exists(tiff_pool._get_pooled_data_filepath())
        mean_csv_exists = os.path.exists(tiff_pool._get_mean_data_filepath())
        
        if main_csv_exists and mean_csv_exists:
            logger.info("Found existing TiffPool CSV files - loaded successfully")
            return
        
        # Check if we have any kymRoiAnalysis files available
        analysis_files_exist = False
        for idx, row in self.backend.df.iterrows():
            kym_analysis = self.backend.get_kym_roi_analysis(idx)
            if kym_analysis is not None:
                analysis_files_exist = True
                break
        
        if analysis_files_exist:
            logger.info("No TiffPool CSV files found, but kymRoiAnalysis files exist - generating pooled data")
            
            # Get total number of files for progress tracking
            total_files = len(self.backend.df)
            
            # Create progress callback
            progress_callback = get_progress_callback(
                total_steps=total_files,
                title="Generating TiffPool Data"
            )
            
            # Show modal progress dialog
            progress_dialog = ProgressDialog(
                title="Generating TiffPool Data",
                total_steps=total_files,
                parent=self,
                show_cancel_button=True
            )
            progress_dialog.show()
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            tiff_pool.pool_all_analysis(progress_callback=progress_callback)
            
            # Verify that data was generated and saved
            master_count = len(tiff_pool.get_master_dataframe())
            mean_count = len(tiff_pool.get_df_mean())
            logger.info(f"After pooling: master_df has {master_count} rows, dfMean has {mean_count} rows")
            
            # Check if CSV files were created
            main_csv_exists = os.path.exists(tiff_pool._get_pooled_data_filepath())
            mean_csv_exists = os.path.exists(tiff_pool._get_mean_data_filepath())
            logger.info(f"CSV files created: main={main_csv_exists}, mean={mean_csv_exists}")
            progress_dialog.status_label.setText("Pooling complete!")
            progress_dialog.accept()
        else:
            logger.info("No TiffPool CSV files or kymRoiAnalysis files found - TiffPool ready for future analysis")

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
        logger.info(f"relative_path:{relative_path}")
        # You can add custom actions here, such as opening the file
        # subprocess.run(['open', relative_path])  # Uncomment to open files

        # from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis
        from sanpy.kym.interface.kymRoiWidget import KymRoiWidget

        # logger.info(f"creating widget: {relative_path}")

        # Get KymRoiAnalysis with image data loaded (not just CSV analysis)
        aKymRoiAnalysis = self.backend.get_kym_roi_analysis_with_image_data_by_path(relative_path)
        if aKymRoiAnalysis is None:
            logger.error(f"Failed to load KymRoiAnalysis with image data for: {relative_path}")
            return
            
        aWidget = KymRoiWidget(aKymRoiAnalysis)

        aWidget.signalAnalysisSaved.connect(self.slot_analysisSaved)
        # Connect to ROI label change signal with the widget instance
        aWidget.signalRoiLabelChanged.connect(lambda old_label, new_label, widget=aWidget: self.slot_roiLabelChanged(old_label, new_label, widget))
        
        # Update menu states after loading analysis
        self.updateWindowsMenu()

        # Update the table to show the loaded status
        if aKymRoiAnalysis is not None:
            filename = os.path.basename(relative_path)
            self.table_widget.updateKymAnalysisStatus(filename)
            # logger.info(f"Updated KymRoiAnalysis status for: {filename}")

        # Add widget to tracking system, use tif file name as label
        tif_label = os.path.basename(relative_path)
        widget_id = self.addOpenWidget(aWidget, tif_label, "KymRoi")
        aWidget.setWindowTitle(f"KymRoi - {tif_label}")
        aWidget.show()

    def slot_analysisSaved(self, path):
        """Called when analysis is saved."""
        logger.info(f"path:{path}")

        # Update the entire row in the backend from saved analysis
        backend_success = self.backend.update_row_from_saved_analysis(path)
        
        # Update the TiffPool data
        tiff_pool_success = self.backend._tifPool.on_analysis_saved(path)
        
        if backend_success and tiff_pool_success:
            # Refresh the table row to show updated data
            if self.table_widget:
                # Get relative path for the table update
                if os.path.isabs(path):
                    relative_path = os.path.relpath(path, self.backend.root_path)
                else:
                    relative_path = path
                self.table_widget.refresh_row_after_save(relative_path)
            logger.info(f"Successfully updated row for {path} and refreshed table and TiffPool")
        else:
            if not backend_success:
                logger.warning(f"Failed to update backend row for {path}")
            if not tiff_pool_success:
                logger.warning(f"Failed to update TiffPool analysis for {path}")

    def slot_roiLabelChanged(self, oldRoiLabel: str, newRoiLabel: str, kymRoiWidget):
        """Called when an ROI label is changed in a KymRoiWidget."""
        logger.info(f"ROI label changed from '{oldRoiLabel}' to '{newRoiLabel}' for widget: {kymRoiWidget}")
        
        # Get the TiffPool from the backend
        if not hasattr(self, 'backend') or self.backend is None:
            logger.warning("No backend available for ROI label update")
            return
            
        tiff_pool = self.backend._tifPool
        if tiff_pool is None:
            logger.warning("No TiffPool available for ROI label update")
            return
        
        # Get the TIF file path from the KymRoiWidget
        tif_path = kymRoiWidget.path
        logger.info(f"Updating ROI label for TIF file: {tif_path}")
        
        # Update the TiffPool dataframes with the new ROI label for this specific file
        success = tiff_pool.update_roi_label_for_file(oldRoiLabel, newRoiLabel, tif_path)
        
        if success:
            logger.info(f"Successfully updated ROI label in TiffPool from '{oldRoiLabel}' to '{newRoiLabel}' for file: {tif_path}")
            
            # Refresh the table view to show updated data
            if self.table_widget:
                self.table_widget.refresh_display()
                
            # Refresh the tree widget if it displays ROI information
            if self.tree_widget:
                self.tree_widget.refresh()
                
            # Refresh the TifPoolScatter widget if it's open
            if self.tif_pool_scatter_widget is not None:
                try:
                    # Get updated dataframes from TiffPool
                    master_df = tiff_pool.get_master_dataframe()
                    mean_df = tiff_pool.get_df_mean()
                    errors_df = tiff_pool.get_df_errors()
                    
                    # Update the ScatterWidget's data
                    self.tif_pool_scatter_widget._masterDf = master_df
                    self.tif_pool_scatter_widget._meanDf = mean_df
                    self.tif_pool_scatter_widget._errorsDf = errors_df
                    
                    # Replot to show the updated data
                    self.tif_pool_scatter_widget.replot()
                    
                    logger.info("Successfully refreshed TifPoolScatter widget with updated ROI labels")
                except Exception as e:
                    logger.warning(f"Failed to refresh TifPoolScatter widget: {e}")
        else:
            logger.warning(f"Failed to update ROI label in TiffPool from '{oldRoiLabel}' to '{newRoiLabel}' for file: {tif_path}")

    def onPlotRoisRequested(self, relative_path):
        """Called when user selects 'Plot ROIs' from context menu."""
        logger.info(f"Plot ROIs requested for: {relative_path}")
        
        if 0:
            from sanpy.kym.kymRoiPlot_mpl import plotOneKym
            kymRoiAnalysis = self.backend.get_kym_roi_analysis_by_path(relative_path)
            fig, ax = plotOneKym(kymRoiAnalysis)
            fig.show()

        # test plot_cellid_cond
        self.plot_cellid_cond(relative_path, '1')

    def plot_cellid_cond(self, pathToTif: str, roiLabel: str):
        """Given a tif file and a roi label, plot the label across all conditions.
        
        Parameters
        ----------
        pathToTif : str
            The path to the TIF file (abs or relative).
        roiLabel : str
            The ROI label to plot.
        """
        # get cell id from backend
        from sanpy.kym.kymRoiPlot_mpl import plot_cell_id_conds
        row = self.backend.get_row_by_path(pathToTif)
        fig, ax, imgDataDict = plot_cell_id_conds(
            self.backend,
            cellID=row['Cell ID'],
            roiLabel=roiLabel)
        fig.show()
    

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
        """Refresh the data from disk.
        
        Remove deleted and add new tif files from the backend
        and refresh the tree and table widgets.
        """
        if self.backend:
            logger.info("Refreshing data from disk (Add new and remove deleted)")

            # Refresh the backend
            self.backend.refresh()

            # Refresh both widgets
            if self.tree_widget:
                self.tree_widget.refresh()
            if self.table_widget:
                self.table_widget.refresh()

            # Re-initialize TiffPool data after refresh
            self._initialize_tiff_pool_data()

            # Update status
            file_count = self.backend.get('file_count')
            folder_name = get_folder_hierarchy_title(self.backend.root_path)
            self.statusBar().showMessage(
                f"Refreshed: {folder_name} | Found {file_count} .tif files"
            )

            logger.info(f"Data refreshed. Found {file_count} .tif files")
        else:
            logger.warning("No backend available to refresh")

    def forceReanalyzeAll(self):
        """Force re-analysis of all files (expensive operation)."""
        if self.backend:
            logger.info("Force re-analyzing all files")

            # Show status message
            self.statusBar().showMessage("Force re-analyzing all files...")

            # Force re-analyze all files in the backend
            self.backend.force_reanalyze_all()

            # Refresh both widgets
            if self.tree_widget:
                self.tree_widget.refresh()
            if self.table_widget:
                self.table_widget.refresh()

            # Re-initialize TiffPool data after force re-analyze
            self._initialize_tiff_pool_data()

            # Update status
            file_count = self.backend.get('file_count')
            folder_name = get_folder_hierarchy_title(self.backend.root_path)
            self.statusBar().showMessage(
                f"Force re-analyzed: {folder_name} | Found {file_count} .tif files"
            )

            logger.info(f"Force re-analyzed all files. Found {file_count} .tif files")
        else:
            logger.warning("No backend available to force re-analyze")

    def unloadAllAnalysis(self):
        """Unload all KymRoiAnalysis objects from memory to free up resources."""
        if self.backend:
            # Get count before unloading
            loaded_count = self.backend.get_cached_kym_roi_analysis_count()
            
            if loaded_count == 0:
                logger.info("No KymRoiAnalysis objects loaded to unload")
                self.statusBar().showMessage("No analysis objects loaded")
                return
            
            logger.info(f"Unloading {loaded_count} KymRoiAnalysis objects from memory")
            
            # Show status message
            self.statusBar().showMessage(f"Unloading {loaded_count} analysis objects...")
            
            # Clear all cached KymRoiAnalysis objects (just set pointers to None)
            self.backend.clear_kym_roi_analysis_cache()
            
            # Update status icons in table widget without full refresh
            if self.table_widget:
                self.table_widget.update_kym_analysis_status_icons()
            
            # Update menu states
            self.updateWindowsMenu()
            
            # Update status
            folder_name = get_folder_hierarchy_title(self.backend.root_path)
            self.statusBar().showMessage(
                f"Unloaded {loaded_count} analysis objects from {folder_name}"
            )
            
            logger.info(f"Successfully unloaded {loaded_count} KymRoiAnalysis objects")
        else:
            logger.warning("No backend available to unload analysis")

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
        self.statusBar().showMessage("Kym Preferences saved successfully")

        # You can add code here to apply preferences to the current application state
        # For example, if the Olympus Export preference changed, you might need to
        # reload the current data or update the UI accordingly

        # Example: Check if Olympus Export preference changed
        olympus_export = preferences.get('Load Kymograph', {}).get(
            'olympus_export', False
        )
        logger.info(f"Olympus Export setting: {olympus_export}")

        # If you have a backend loaded, you might want to refresh it with new settings
        if self.backend:
            # You could add a method to the backend to reload with new preferences
            # self.backend.reloadWithPreferences(preferences)
            pass

    def toggleTifPoolScatter(self):
        """Toggle the TifPoolScatter window open/closed."""
        if self.tif_pool_scatter_widget is None:
            # Widget is not open, so open it
            self.openTifPoolScatter()
        else:
            # Widget is open, so bring it to front
            self.bringTifPoolScatterToFront()
    
    def bringTifPoolScatterToFront(self):
        """Bring the TifPoolScatter widget to the front."""
        if self.tif_pool_scatter_widget:
            self.tif_pool_scatter_widget.raise_()
            self.tif_pool_scatter_widget.activateWindow()
            logger.info("Brought TifPoolScatter to front")
    
    def openTifPoolScatter(self):
        """Open the TifPoolScatter window."""
        if self.backend:
            # Get the TiffPool from the backend
            tiff_pool = self.backend._tifPool
            
            # Get the master and mean dataframes
            master_df = tiff_pool.get_master_dataframe()
            mean_df = tiff_pool.get_df_mean()
            errors_df = tiff_pool.get_df_errors()
            
            # Check if we have data
            if len(master_df) == 0 or len(mean_df) == 0:
                self.statusBar().showMessage("No analysis data available. Please analyze files before using Tif Pool Scatter.")
                return
            
            # Debug: Log available columns
            # logger.info(f"Available columns in mean_df: {list(mean_df.columns)}")
            # logger.info(f"Available columns in master_df: {list(master_df.columns)}")
            
            # Define hue list for the scatter widget - use columns that actually exist in the DataFrame
            potential_hue_columns = [
                'File Number',
                'Cell ID',
                'Condition',
                'Repeat',
                'Condition Repeat',
                'Region',
                'Date',
                'ROI Label',
                # 'ROI Label',  # Fallback for legacy data
                'Polarity',
            ]
            
            # Filter to only include columns that actually exist in the DataFrame
            hue_list = [col for col in potential_hue_columns if col in mean_df.columns]
            
            # Ensure we have at least some hue options
            if not hue_list:
                logger.warning("No suitable hue columns found in DataFrame, using basic options")
                hue_list = ['Cell ID', 'Condition']  # Fallback options
            
            # Define plot columns to show user - use columns that actually exist in the DataFrame
            potential_plot_columns = [
                'Cell ID',
                'File Number',
                'Tif File',
                'Condition',
                'Region',
                'Date',
                'ROI Label',
                # 'ROI Number',  # Fallback for legacy data
                'Polarity',
                'Peak Inst Interval (s)',
                'Peak Inst Freq (Hz)',
                'Peak Height',
                'FW (ms)',
                'HW (ms)',
                'Rise Time (ms)',
                'Decay Time (ms)',
                'Area Under Peak',
                'Area Under Peak (Sum)',
                'Number of Peaks',
                'fit_tau',
                'fit_tau1',
            ]
            
            # Filter to only include columns that actually exist in the DataFrame
            plot_columns = [col for col in potential_plot_columns if col in mean_df.columns]
            
            # Create the ScatterWidget
            scatter_widget = ScatterWidget(
                master_df,
                mean_df,
                xStat='Region',
                yStat='Peak Inst Freq (Hz)',
                defaultPlotType='Swarm + Mean + SEM',
                hueList=hue_list,
                defaultHue='Condition',
                imgFolder=None,
                plotColumns=plot_columns,
                errorsDf=errors_df,
            )
            
            # Set window title
            folder_name = get_folder_hierarchy_title(self.backend.root_path)
            scatter_widget.setWindowTitle(f"TifPoolScatter - {folder_name}")
            
            # Store reference to TifPoolScatter widget
            self.tif_pool_scatter_widget = scatter_widget
            
            # Connect widget's closeEvent to handle cleanup
            orig_closeEvent = scatter_widget.closeEvent
            def new_closeEvent(ev):
                self.tif_pool_scatter_widget = None
                # Update menu checked state
                if hasattr(self, 'tif_pool_scatter_action'):
                    self.tif_pool_scatter_action.setChecked(False)
                orig_closeEvent(ev)
            scatter_widget.closeEvent = new_closeEvent
            
            # Also connect destroyed for robustness
            scatter_widget.destroyed.connect(self._on_tif_pool_scatter_destroyed)
            
            scatter_widget.show()
            logger.info(f"Opened TifPoolScatter window with {len(master_df)} master rows and {len(mean_df)} mean rows")
        else:
            logger.warning("No backend available to open TifPoolScatter")
            QMessageBox.warning(self, "Error", "No backend available. Please load a folder first.")
    
    def _on_tif_pool_scatter_destroyed(self):
        """Called when TifPoolScatter widget is destroyed."""
        self.tif_pool_scatter_widget = None
        # Update menu checked state
        if hasattr(self, 'tif_pool_scatter_action'):
            self.tif_pool_scatter_action.setChecked(False)


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
    default_path = (
        # "/Users/cudmore/Dropbox/data/colin/2025/mito-atp/mito-atp-20250623-RHC"
        '/Users/cudmore/Sites/SanPy/sanpy/kym/sample-data'
    )

    # Create and show the main window
    window = TifTreeWindow(sanPyApp=sanPyApp, path=default_path)
    window.show()

    # Run the application
    sys.exit(sanPyApp.exec_())


if __name__ == "__main__":
    main()
