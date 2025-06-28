#!/usr/bin/env python3
"""
Test script to demonstrate the TifTableView widget.
"""

import sys
import tempfile
import os
import shutil

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

from sanpy.kym.tif_file_backend import TifFileBackend
from sanpy.kym.interface.kym_file_list.tif_table_view import TifTableView

def create_test_data():
    """Create test TIF files for demonstration."""
    temp_dir = tempfile.mkdtemp()
    
    # Create directory structure
    os.makedirs(os.path.join(temp_dir, "Experiment1", "Control", "Day1"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "Experiment1", "Control", "Day2"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "Experiment1", "Treatment", "Day1"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "Experiment2", "Control", "Day1"), exist_ok=True)
    
    # Create TIF files with proper naming convention
    files_to_create = [
        ("Experiment1/Control/Day1/20250312 ISAN R1 LS1 Control.tif", "test"),
        ("Experiment1/Control/Day1/20250312 ISAN R2 LS1 Control.tif", "test"),
        ("Experiment1/Control/Day2/20250312 ISAN R1 LS1 Control.tif", "test"),
        ("Experiment1/Treatment/Day1/20250312 ISAN R1 LS1 Treatment.tif", "test"),
        ("Experiment1/Treatment/Day1/20250312 ISAN R2 LS1 Treatment.tif", "test"),
        ("Experiment2/Control/Day1/20250312 SSAN R1 LS1 Control.tif", "test"),
        ("Experiment2/Control/Day1/20250312 SSAN R2 LS1 Control.tif", "test"),
    ]
    
    for filepath, content in files_to_create:
        full_path = os.path.join(temp_dir, filepath)
        with open(full_path, 'w') as f:
            f.write(content)
    
    return temp_dir

class TestWindow(QMainWindow):
    """Test window for the TifTableView widget."""
    
    def __init__(self, data_dir):
        super().__init__()
        self.data_dir = data_dir
        self.setupUI()
    
    def setupUI(self):
        """Set up the user interface."""
        self.setWindowTitle("TifTableView Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Create backend
        self.backend = TifFileBackend(self.data_dir, sort_by_grandparent=True)
        
        # Create table view
        self.table_view = TifTableView(self.backend)
        
        # Connect signals
        self.table_view.fileToggled.connect(self.onFileToggled)
        self.table_view.fileDoubleClicked.connect(self.onFileDoubleClicked)
        self.table_view.plotRoisRequested.connect(self.onPlotRoisRequested)
        self.table_view.exportCompleted.connect(self.onExportCompleted)
        
        # Add to layout
        layout.addWidget(self.table_view)
    
    def onFileToggled(self, file_path, checked):
        """Handle file toggle events."""
        print(f"File toggled: {os.path.basename(file_path)} -> {'checked' if checked else 'unchecked'}")
    
    def onFileDoubleClicked(self, file_path):
        """Handle file double-click events."""
        print(f"File double-clicked: {os.path.basename(file_path)}")
    
    def onPlotRoisRequested(self, file_path):
        """Handle plot ROIs requests."""
        print(f"Plot ROIs requested for: {os.path.basename(file_path)}")
    
    def onExportCompleted(self, export_path):
        """Handle export completion."""
        print(f"Export completed: {export_path}")

def main():
    """Main function to run the test."""
    app = QApplication(sys.argv)
    
    # Create test data
    data_dir = create_test_data()
    
    try:
        # Create and show test window
        window = TestWindow(data_dir)
        window.show()
        
        print("TifTableView Test Window")
        print("Features to test:")
        print("1. Column sorting (click column headers)")
        print("2. Filtering (use dropdowns and search box)")
        print("3. Checkbox selection (click checkboxes)")
        print("4. Bulk operations (Select All, Deselect All, Invert Selection)")
        print("5. Context menu (right-click on rows)")
        print("6. Export functionality (Export button)")
        print("7. Double-click on files")
        
        # Run the application
        sys.exit(app.exec_())
        
    finally:
        # Clean up test data
        shutil.rmtree(data_dir)

if __name__ == "__main__":
    main() 