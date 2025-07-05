#!/usr/bin/env python3
"""
Test script for the preferences system.

This script demonstrates how to use the preferences dialog and manager.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt

# Add the sanpy directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sanpy.kym.interface.preferences_dialog import PreferencesDialog
from sanpy.kym.interface.preferences_manager import preferences_manager
from sanpy.kym.logger import get_logger

logger = get_logger(__name__)

class PreferencesTestWindow(QMainWindow):
    """Simple test window for the preferences system."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Preferences Test")
        self.setGeometry(100, 100, 400, 300)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Add some test controls
        self.createControls(layout)
        
        # Connect to preferences manager signals
        preferences_manager.preferencesChanged.connect(self.onPreferencesChanged)
    
    def createControls(self, layout):
        """Create test controls."""
        # Title
        title_label = QLabel("Preferences System Test")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # Current preferences display
        self.prefs_label = QLabel("Current preferences will be shown here")
        self.prefs_label.setWordWrap(True)
        self.prefs_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc;")
        layout.addWidget(self.prefs_label)
        
        # Update the display
        self.updatePreferencesDisplay()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Show preferences dialog button
        show_prefs_btn = QPushButton("Show Preferences Dialog")
        show_prefs_btn.clicked.connect(self.showPreferences)
        button_layout.addWidget(show_prefs_btn)
        
        # Reset preferences button
        reset_prefs_btn = QPushButton("Reset to Defaults")
        reset_prefs_btn.clicked.connect(self.resetPreferences)
        button_layout.addWidget(reset_prefs_btn)
        
        # Reload preferences button
        reload_prefs_btn = QPushButton("Reload from File")
        reload_prefs_btn.clicked.connect(self.reloadPreferences)
        button_layout.addWidget(reload_prefs_btn)
        
        layout.addLayout(button_layout)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def showPreferences(self):
        """Show the preferences dialog."""
        dialog = PreferencesDialog(self)
        
        # Connect the preferences saved signal
        dialog.preferencesSaved.connect(self.onPreferencesSaved)
        
        # Show the dialog
        result = dialog.exec_()
        
        if result == PreferencesDialog.Accepted:
            logger.info("Preferences dialog accepted")
        else:
            logger.info("Preferences dialog cancelled")
    
    def onPreferencesSaved(self, preferences):
        """Called when preferences are saved from the dialog."""
        logger.info("Preferences saved from dialog")
        self.updatePreferencesDisplay()
    
    def onPreferencesChanged(self, preferences):
        """Called when preferences are changed via the manager."""
        logger.info("Preferences changed via manager")
        self.updatePreferencesDisplay()
    
    def resetPreferences(self):
        """Reset preferences to defaults."""
        preferences_manager.resetToDefaults()
        logger.info("Preferences reset to defaults")
    
    def reloadPreferences(self):
        """Reload preferences from file."""
        preferences_manager.reloadPreferences()
        logger.info("Preferences reloaded from file")
    
    def updatePreferencesDisplay(self):
        """Update the preferences display label."""
        prefs = preferences_manager.getAllPreferences()
        
        # Format preferences for display
        prefs_text = "Current Preferences:\n\n"
        
        for group_name, group_prefs in prefs.items():
            prefs_text += f"{group_name}:\n"
            for key, value in group_prefs.items():
                prefs_text += f"  {key}: {value}\n"
            prefs_text += "\n"
        
        self.prefs_label.setText(prefs_text)

def main():
    """Main function to run the test."""
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
    
    # Create and show the test window
    window = PreferencesTestWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 