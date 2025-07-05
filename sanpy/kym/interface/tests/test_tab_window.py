#!/usr/bin/env python3
"""
Test script for the tabbed TifTreeWindow with both tree and table views.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from sanpy.kym.interface.kym_file_list.tif_tree_window import TifTreeWindow

def main():
    """Test the tabbed window with both views."""
    app = QApplication(sys.argv)
    
    # Use a test path that exists
    test_path = "/Users/cudmore/Dropbox/data/colin/2025/mito-atp/mito-atp-20250623-RHC"
    
    # Create and show the window
    window = TifTreeWindow(path=test_path)
    window.show()
    
    print("Tabbed window created successfully!")
    print("You should see two tabs: 'Tree View' and 'Table View'")
    print("Both views should show the same data from the backend")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 