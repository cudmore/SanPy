#!/usr/bin/env python3
"""
TifViewer - A specialized widget for viewing .tif files using CustomWidget as base.

This widget demonstrates how to use the CustomWidget API to create a specialized
viewer with three main sections: file browser, image viewer, and analysis panel.
"""

import sys
import os
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QTextEdit,
    QFrame,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QApplication,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont

from sanpy.kym.interface.kym_file_list.tif_viewer_base import CustomWidget
from sanpy.kym.interface.kym_file_list.tif_table_view import TifTableView
from sanpy.kym.tif_file_backend import TifFileBackend
from sanpy.kym.interface.kymRoiImageWidget import KymRoiImageWidget
from sanpy.kym.interface.kymPlotWidget import KymPlotWidget
from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, PeakDetectionTypes


class TifViewer(CustomWidget):
    """
    TifViewer widget that uses CustomWidget as a base and adds three specialized widgets:
    1. File Browser - for selecting and browsing .tif files using TifTableView
    2. Image Viewer - for displaying the selected .tif image using KymRoiImageWidget
    3. Analysis Panel - for showing analysis results and controls
    """

    # Custom signals for this widget
    file_selected = pyqtSignal(str)  # Emitted when a .tif file is selected
    analysis_requested = pyqtSignal(str)  # Emitted when analysis is requested

    def __init__(self, folder_path: str):
        """
        Initialize TifViewer with a folder path.

        Parameters
        ----------
        folder_path : str
            Path to the folder containing .tif files
        """
        super().__init__()

        # Validate folder path
        if not os.path.exists(folder_path):
            raise ValueError(f"Folder path does not exist: {folder_path}")

        self.folder_path = folder_path
        self.current_file = None
        self.current_kym_analysis = None
        self.current_image_widget = None
        self.sum_intensity_plot_item = None

        # Create backend for the folder
        self.backend = TifFileBackend(folder_path)

        self.init_tif_viewer_ui()

    def init_tif_viewer_ui(self):
        """Initialize the TIF viewer specific UI components"""
        self.setWindowTitle(f'TIF File Viewer - {os.path.basename(self.folder_path)}')

        # Create the three main widgets
        self.create_file_browser()
        self.create_image_viewer()
        self.create_analysis_panel()

        # Add custom toolbar widgets for TIF viewer functionality
        self.create_tif_toolbar()

        # Set proportional splitter sizes (file browser: 30%, image viewer: 40%, analysis panel: 30%)
        total_height = self.height() if self.height() > 0 else 600
        self.splitter.setSizes(
            [
                int(total_height * 0.30),
                int(total_height * 0.40),
                int(total_height * 0.30),
            ]
        )

    def create_file_browser(self):
        """Create the file browser widget using TifTableView"""
        # Create TifTableView with our backend
        self.tif_table_view = TifTableView(self.backend)

        # Connect signals from TifTableView to our handlers
        self.tif_table_view.fileSelected.connect(self.on_file_selected)
        self.tif_table_view.fileDoubleClicked.connect(self.on_file_double_clicked)
        self.tif_table_view.loadKymAnalysisRequested.connect(self.on_load_kym_analysis)

        # Add to CustomWidget using the API
        self.add_widget("File Browser", self.tif_table_view, "#E6F3FF")

    def create_image_viewer(self):
        """Create the image viewer widget using KymRoiImageWidget"""
        # Create a container widget for the image viewer
        image_viewer_container = QWidget()
        layout = QVBoxLayout()

        # Status label
        self.image_status_label = QLabel("No file selected")
        self.image_status_label.setAlignment(Qt.AlignCenter)
        self.image_status_label.setStyleSheet("color: #666666; font-style: italic;")
        layout.addWidget(self.image_status_label)

        # Container for the KymRoiImageWidget (will be populated when file is selected)
        self.image_viewer_widget = QWidget()
        self.image_viewer_widget.setStyleSheet(
            "border: 2px dashed #CCCCCC; background-color: #F8F8F8;"
        )
        layout.addWidget(self.image_viewer_widget)

        image_viewer_container.setLayout(layout)

        # Add to CustomWidget using the API
        self.add_widget("Image Viewer", image_viewer_container, "#FFE6E6")

    def create_analysis_panel(self):
        """Create the analysis panel widget with KymPlotWidget"""
        analysis_panel_widget = QWidget()
        layout = QVBoxLayout()

        # Container for KymPlotWidget (will be populated when file is selected)
        self.plot_widget_container = QWidget()
        self.plot_widget_container.setStyleSheet(
            "border: 2px dashed #CCCCCC; background-color: #F8F8F8;"
        )
        layout.addWidget(self.plot_widget_container)

        analysis_panel_widget.setLayout(layout)

        # Add to CustomWidget using the API
        self.add_widget("Analysis Panel", analysis_panel_widget, "#E6FFE6")

    def create_tif_toolbar(self):
        """Add TIF viewer specific toolbar widgets"""
        from PyQt5.QtWidgets import QComboBox, QSpinBox

        # Update the status label
        self.set_toolbar_value(
            "Status Label", f"TIF Viewer Ready - {len(self.backend.df)} files loaded"
        )

    def on_file_selected(self, file_path):
        """Handle file selection from TifTableView"""
        self.load_file(file_path)

    def on_file_double_clicked(self, file_path):
        """Handle file double-click from TifTableView"""
        self.load_file(file_path)

    def on_load_kym_analysis(self, file_path):
        """Handle KymRoiAnalysis load request from TifTableView"""
        # This could trigger analysis or other actions
        self.set_toolbar_value(
            "Status Label", f"KymRoiAnalysis requested for: {file_path}"
        )

    def load_file(self, file_path):
        """Load and display a .tif file using KymRoiImageWidget"""
        try:
            # Find the row in the backend that matches this file path
            # Convert absolute path to relative path for matching
            if os.path.isabs(file_path):
                try:
                    relative_path = os.path.relpath(file_path, self.folder_path)
                except ValueError:
                    # Handle case where paths are on different drives
                    relative_path = file_path
            else:
                relative_path = file_path

            # Find the row index in the backend
            mask = self.backend.df['relative_path'] == relative_path
            if not mask.any():
                raise Exception(f"File not found in backend: {relative_path}")

            row_index = mask.idxmax()

            # Get or create the KymRoiAnalysis for this file
            kym_analysis = self.backend.get_kym_roi_analysis(row_index)
            if kym_analysis is None:
                raise Exception(f"Failed to load KymRoiAnalysis for: {relative_path}")

            # Update current state
            self.current_file = file_path
            self.current_kym_analysis = kym_analysis

            # Create or refresh the KymRoiImageWidget
            self.refresh_image_widget(kym_analysis)

            # Create or refresh the KymPlotWidget
            self.refresh_plot_widget(kym_analysis)

            # Emit signal
            self.file_selected.emit(file_path)

            self.set_toolbar_value(
                "Status Label", f"Loaded: {os.path.basename(file_path)}"
            )

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load file: {str(e)}")
            self.set_toolbar_value("Status Label", "Error loading file")
            self.image_status_label.setText(f"Error: {str(e)}")

    def refresh_image_widget(self, kym_analysis):
        """Create or refresh the KymRoiImageWidget with the given KymRoiAnalysis"""
        try:
            # Clear the existing image widget
            if self.current_image_widget is not None:
                # Remove the old widget from the layout
                layout = self.image_viewer_widget.layout()
                if layout is None:
                    layout = QVBoxLayout()
                    self.image_viewer_widget.setLayout(layout)

                # Remove all widgets from the layout
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().setParent(None)

            # Create new KymRoiImageWidget
            self.current_image_widget = KymRoiImageWidget(
                kym_analysis,
                detectThisTrace='',  # Empty string as suggested
                kymRoiWidget=None,
            )

            # Add to the container widget
            layout = self.image_viewer_widget.layout()
            if layout is None:
                layout = QVBoxLayout()
                self.image_viewer_widget.setLayout(layout)

            layout.addWidget(self.current_image_widget)

            # Connect the image widget's ROI selection signal to the plot widget's slot
            if self.sum_intensity_plot_item is not None:
                self.current_image_widget.signalSelectRoi.connect(
                    self.sum_intensity_plot_item.slot_selectRoi
                )

            # Update status
            self.image_status_label.setText(
                f"Loaded: {os.path.basename(self.current_file)} - {kym_analysis.numRoi} ROIs"
            )

        except Exception as e:
            self.image_status_label.setText(f"Error creating image widget: {str(e)}")
            raise

    def refresh_plot_widget(self, kym_analysis):
        """Create or refresh the KymPlotWidget with the given KymRoiAnalysis"""
        try:
            # Clear the existing plot widget
            if self.sum_intensity_plot_item is not None:
                # Remove the old plot from the layout
                layout = self.plot_widget_container.layout()
                if layout is None:
                    layout = QVBoxLayout()
                    self.plot_widget_container.setLayout(layout)

                # Remove all widgets from the layout
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().setParent(None)

            # Create new KymPlotWidget
            self.sum_intensity_plot_item = KymPlotWidget(
                kym_analysis,
                xTrace='Time (s)',
                yTrace='f/f0',
                peakDetectionType=PeakDetectionTypes.intensity,
            )

            # Add to the container widget
            layout = self.plot_widget_container.layout()
            if layout is None:
                layout = QVBoxLayout()
                self.plot_widget_container.setLayout(layout)

            layout.addWidget(self.sum_intensity_plot_item)

            # Set X-link if we have an image widget with a plot
            if hasattr(self.current_image_widget, 'kymographPlot'):
                self.sum_intensity_plot_item.setXLink(
                    self.current_image_widget.kymographPlot
                )

        except Exception as e:
            print(f"Error creating plot widget: {str(e)}")
            # Don't raise here, as plot widget is optional

    def resizeEvent(self, event):
        """Handle window resize to maintain proportional splitter sizes"""
        super().resizeEvent(event)
        # Maintain proportional sizes when window is resized
        total_height = self.height()
        if total_height > 0:
            self.splitter.setSizes(
                [
                    int(total_height * 0.30),
                    int(total_height * 0.40),
                    int(total_height * 0.30),
                ]
            )


def main():
    """Demo function to show the TifViewer in action"""
    from functools import partial

    app = QApplication(sys.argv)

    # Use the sample-data folder
    sample_data_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "sample-data"
    )

    if not os.path.exists(sample_data_path):
        print(f"Error: Sample data folder not found at {sample_data_path}")
        sys.exit(1)

    viewer = TifViewer(sample_data_path)
    viewer.show()

    # Connect signals for demo
    viewer.file_selected.connect(partial(print, "File selected: {}"))
    viewer.analysis_requested.connect(partial(print, "Analysis requested for: {}"))

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
