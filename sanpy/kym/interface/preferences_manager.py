#!/usr/bin/env python3
"""
Preferences manager for SanPy Kymograph application.

This module provides a singleton preferences manager that handles
loading, saving, and accessing application preferences.
"""

import os
import json
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal

from sanpy.kym.logger import get_logger
logger = get_logger(__name__)

class PreferencesManager(QObject):
    """
    Singleton preferences manager for SanPy Kymograph application.
    
    This class provides a centralized way to access and manage
    application preferences. It loads preferences from a JSON file
    and validates them against a gold standard preferences dictionary.
    """
    
    # Signal emitted when preferences are changed
    preferencesChanged = pyqtSignal(dict)
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(PreferencesManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the preferences manager."""
        if self._initialized:
            return
        
        super().__init__()
        
        # Initialize preferences
        self.preferences = {}
        
        # Load preferences
        self.loadPreferences()
        
        self._initialized = True
    
    def getDefaultPreferences(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the default preferences dictionary.
        
        This is the 'gold standard' preferences dict that defines
        all valid preference keys and their default values.
        
        Returns:
            Dictionary containing default preferences organized by group.
        """
        return {
            'Load Kymograph': {
                'olympus_export': False
            }
        }
    
    def getPreferencesFilePath(self) -> str:
        """
        Get the path to the preferences file.
        
        Returns:
            Path to the preferences JSON file.
        """
        # Use the sanpy user files directory
        user_files_dir = os.path.join(
            os.path.expanduser("~"), 
            "SanPy-User-Files"
        )
        
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
                logger.warning(f"Failed to load preferences from {preferences_file}: {e}")
                # Keep default preferences
        else:
            logger.info(f"No preferences file found at {preferences_file}, using defaults")
    
    def validatePreferences(self, loaded_prefs: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
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
    
    def savePreferences(self, preferences: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Save preferences to JSON file.
        
        Args:
            preferences: Preferences to save. If None, uses current preferences.
        """
        if preferences is not None:
            self.preferences = preferences
        
        # Save to file
        preferences_file = self.getPreferencesFilePath()
        
        try:
            with open(preferences_file, 'w') as f:
                json.dump(self.preferences, f, indent=2)
            
            logger.info(f"Preferences saved to {preferences_file}")
            
            # Emit signal
            self.preferencesChanged.emit(self.preferences)
            
        except IOError as e:
            logger.error(f"Failed to save preferences to {preferences_file}: {e}")
            raise
    
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
    
    def getAllPreferences(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all current preferences.
        
        Returns:
            Dictionary containing all current preferences.
        """
        return self.preferences.copy()
    
    def resetToDefaults(self):
        """Reset all preferences to default values."""
        self.preferences = self.getDefaultPreferences()
        self.savePreferences()
        logger.info("Preferences reset to defaults")
    
    def reloadPreferences(self):
        """Reload preferences from file."""
        self.loadPreferences()
        self.preferencesChanged.emit(self.preferences)
        logger.info("Preferences reloaded from file")

# Global instance
preferences_manager = PreferencesManager() 