#!/usr/bin/env python3
"""
Preferences dialog for SanPy Kymograph application.

This module provides a preferences dialog that allows users to configure
application settings. Preferences are stored in a JSON file and loaded
with validation against a gold standard preferences dictionary.
"""

import os
import json
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QFormLayout,
    QDialogButtonBox,
    QMessageBox,
    QWidget,
    QScrollArea,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


class PreferencesDialog(QDialog):
    """
    Preferences dialog for SanPy Kymograph application.

    This dialog provides a user interface for configuring application
    preferences. It uses QGroupBox widgets to organize settings and
    stores preferences in a JSON file.
    """

    # Signal emitted when preferences are saved
    preferencesSaved = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SanPy Preferences")
        self.setModal(True)
        self.setMinimumSize(500, 400)

        # Initialize preferences
        self.preferences = {}
        self.widgets = {}  # Store widget references for easy access

        # Setup UI
        self.setupUI()

        # Load current preferences
        self.loadPreferences()

        # Connect signals
        self.connectSignals()

    def setupUI(self):
        """Setup the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)

        # Create scroll area for preferences
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Create scroll widget
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Create preference groups
        self.createLoadKymographGroup(scroll_layout)

        # Add stretch to push everything to the top
        scroll_layout.addStretch()

        # Set scroll widget
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # Create button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        main_layout.addWidget(button_box)

        # Connect button box signals
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def createLoadKymographGroup(self, parent_layout):
        """Create the 'Load Kymograph' preference group."""
        group_box = QGroupBox("Load Kymograph")
        group_layout = QFormLayout(group_box)

        # Olympus Export checkbox
        self.olympus_export_checkbox = QCheckBox("Olympus Export")
        self.olympus_export_checkbox.setToolTip(
            "Enable Olympus export format when loading kymograph files"
        )
        group_layout.addRow("Olympus Export:", self.olympus_export_checkbox)

        # Store widget reference
        self.widgets['Load Kymograph'] = {
            'olympus_export': self.olympus_export_checkbox
        }

        parent_layout.addWidget(group_box)

    def connectSignals(self):
        """Connect widget signals."""
        # Connect the accept signal to save preferences
        self.accepted.connect(self.savePreferences)

    def getDefaultPreferences(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the default preferences dictionary.

        This is the 'gold standard' preferences dict that defines
        all valid preference keys and their default values.

        Returns:
            Dictionary containing default preferences organized by group.
        """
        return {'Load Kymograph': {'olympus_export': False}}

    def getPreferencesFilePath(self) -> str:
        """
        Get the path to the preferences file.

        Returns:
            Path to the preferences JSON file.
        """
        # Use the sanpy user files directory
        user_files_dir = os.path.join(os.path.expanduser("~"), "SanPy-User-Files")

        # Create directory if it doesn't exist
        os.makedirs(user_files_dir, exist_ok=True)

        return os.path.join(user_files_dir, "kymograph_preferences.json")

    def loadPreferences(self):
        """Load preferences from JSON file."""
        preferences_file = self.getPreferencesFilePath()

        # Start with default preferences
        self.preferences = self.getDefaultPreferences()

        # Try to load from file
        if os.path.exists(preferences_file):
            try:
                with open(preferences_file, 'r') as f:
                    loaded_prefs = json.load(f)

                # Validate loaded preferences against gold standard
                self.preferences = self.validatePreferences(loaded_prefs)
                logger.info(f"Loaded preferences from {preferences_file}")

            except (json.JSONDecodeError, IOError) as e:
                logger.warning(
                    f"Failed to load preferences from {preferences_file}: {e}"
                )
                # Keep default preferences
        else:
            logger.info(
                f"No preferences file found at {preferences_file}, using defaults"
            )

        # Update UI with loaded preferences
        self.updateUIFromPreferences()

    def validatePreferences(
        self, loaded_prefs: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Validate loaded preferences against the gold standard.

        Only loads keys/values that exist in the default preferences dict.

        Args:
            loaded_prefs: Preferences loaded from JSON file

        Returns:
            Validated preferences dictionary
        """
        default_prefs = self.getDefaultPreferences()
        validated_prefs = default_prefs.copy()

        for group_name, group_prefs in loaded_prefs.items():
            if group_name in default_prefs:
                for key, value in group_prefs.items():
                    if key in default_prefs[group_name]:
                        # Validate value type
                        expected_type = type(default_prefs[group_name][key])
                        if isinstance(value, expected_type):
                            validated_prefs[group_name][key] = value
                        else:
                            logger.warning(
                                f"Invalid preference type for {group_name}.{key}: "
                                f"expected {expected_type}, got {type(value)}"
                            )
                    else:
                        logger.warning(f"Unknown preference key: {group_name}.{key}")
            else:
                logger.warning(f"Unknown preference group: {group_name}")

        return validated_prefs

    def updateUIFromPreferences(self):
        """Update UI widgets with current preferences."""
        # Update Load Kymograph group
        if 'Load Kymograph' in self.preferences:
            load_prefs = self.preferences['Load Kymograph']

            if 'olympus_export' in load_prefs:
                self.olympus_export_checkbox.setChecked(load_prefs['olympus_export'])

    def getPreferencesFromUI(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current preferences from UI widgets.

        Returns:
            Dictionary containing current preferences from UI.
        """
        prefs = {}

        # Get Load Kymograph preferences
        prefs['Load Kymograph'] = {
            'olympus_export': self.olympus_export_checkbox.isChecked()
        }

        return prefs

    def savePreferences(self):
        """Save preferences to JSON file."""
        # Get preferences from UI
        self.preferences = self.getPreferencesFromUI()

        # Save to file
        preferences_file = self.getPreferencesFilePath()

        try:
            with open(preferences_file, 'w') as f:
                json.dump(self.preferences, f, indent=2)

            logger.info(f"Preferences saved to {preferences_file}")

            # Emit signal
            self.preferencesSaved.emit(self.preferences)

        except IOError as e:
            logger.error(f"Failed to save preferences to {preferences_file}: {e}")
            QMessageBox.warning(
                self, "Save Error", f"Failed to save preferences:\n{str(e)}"
            )

    def getPreference(self, group: str, key: str, default: Any = None) -> Any:
        """
        Get a specific preference value.

        Args:
            group: Preference group name
            key: Preference key name
            default: Default value if preference doesn't exist

        Returns:
            Preference value or default
        """
        if group in self.preferences and key in self.preferences[group]:
            return self.preferences[group][key]
        return default

    def setPreference(self, group: str, key: str, value: Any):
        """
        Set a specific preference value.

        Args:
            group: Preference group name
            key: Preference key name
            value: Value to set
        """
        if group not in self.preferences:
            self.preferences[group] = {}
        self.preferences[group][key] = value
