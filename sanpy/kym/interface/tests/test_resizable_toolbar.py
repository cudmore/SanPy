#!/usr/bin/env python3
"""
Test script to demonstrate the resizable toolbar functionality in ScatterWidget.
"""

import sys
import pandas as pd
from PyQt5 import QtWidgets, QtGui, QtCore

# Add the parent directory to the path to import the module
sys.path.append('..')
from colin_scatter_widget import ScatterWidget

def create_test_data():
    """Create some test data for the scatter widget."""
    # Create sample data
    data = {
        'Cell ID': ['Cell1', 'Cell1', 'Cell2', 'Cell2', 'Cell3', 'Cell3'],
        'Region': ['SSAN', 'SSAN', 'ISAN', 'ISAN', 'SSAN', 'SSAN'],
        'Condition': ['Control', 'Ivab', 'Control', 'Ivab', 'Control', 'Ivab'],
        'Epoch': [1, 1, 1, 1, 1, 1],
        'Polarity': ['Positive', 'Positive', 'Negative', 'Negative', 'Positive', 'Positive'],
        'ROI Number': [1, 1, 1, 1, 1, 1],
        'Peak Inst Freq (Hz)': [10.5, 8.2, 12.1, 9.8, 11.3, 7.9],
        'Peak Height': [0.8, 0.6, 0.9, 0.7, 0.85, 0.65],
        'File Number': [1, 1, 2, 2, 3, 3],
        'Tif File': ['test1.tif', 'test1.tif', 'test2.tif', 'test2.tif', 'test3.tif', 'test3.tif'],
        'Date': ['2024-01-01', '2024-01-01', '2024-01-02', '2024-01-02', '2024-01-03', '2024-01-03'],
        'show_region': [True, True, True, True, True, True],
        'show_condition': [True, True, True, True, True, True],
        'show_cell': [True, True, True, True, True, True],
        'show_roi': [True, True, True, True, True, True],
        'show_polarity': [True, True, True, True, True, True],
        'show_epoch': [True, True, True, True, True, True],
    }
    
    masterDf = pd.DataFrame(data)
    meanDf = masterDf.copy()  # For simplicity, use same data for mean
    
    return masterDf, meanDf

def main():
    """Main function to test the resizable toolbar."""
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QtGui.QFont("Arial", 10))
    
    # Create test data
    masterDf, meanDf = create_test_data()
    
    # Define hue list for the widget
    hueList = [
        'File Number', 'Cell ID', 'Condition', 'Epoch', 
        'Condition Epoch', 'Region', 'Date', 'ROI Number', 'Polarity'
    ]
    
    # Create the scatter widget
    scatterWidget = ScatterWidget(
        masterDf=masterDf,
        meanDf=meanDf,
        xStat='Region',
        yStat='Peak Inst Freq (Hz)',
        hueList=hueList,
        defaultPlotType='Swarm + Mean + SEM',
        defaultHue='Condition'
    )
    
    scatterWidget.setWindowTitle("Test - Resizable Toolbar")
    scatterWidget.resize(1200, 800)
    
    # Set initial splitter sizes
    scatterWidget.setSplitterSizes(350, 850)
    
    # Show the widget
    scatterWidget.show()
    
    print("ScatterWidget with resizable toolbar is now running.")
    print("You can:")
    print("1. Drag the splitter handle to resize the left toolbar")
    print("2. Right-click to access context menu with 'Reset Toolbar Width' option")
    print("3. The toolbar width will be saved when you close the window")
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 