#!/usr/bin/env python3
"""
Unit tests for TifTreeWindow to verify checkbox state saving and loading.
"""

import unittest
import tempfile
import os
import shutil
import sys
from unittest.mock import patch, MagicMock

# Mock PyQt5 for testing without GUI
sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtWidgets'] = MagicMock()
sys.modules['PyQt5.QtCore'] = MagicMock()
sys.modules['PyQt5.QtGui'] = MagicMock()

from sanpy.kym.tif_file_backend import TifFileBackend
from sanpy.kym.interface.kym_file_list.tif_tree_window import TifTreeWindow

class TestTifTreeWindow(unittest.TestCase):
    """Test TifTreeWindow functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.create_test_files()
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
        
    def create_test_files(self):
        """Create test .tif files with proper TifInfo format."""
        test_files = [
            "20250312 ISAN R1 LS1 Control_0001.tif",
            "20250312 ISAN R1 LS1 Control_0002.tif",
            "20250312 ISAN R2 LS1 FCCP_0001.tif",
            "20250312 ISAN R2 LS1 FCCP_0002.tif",
            "20250315 ISAN R1 LS2 Ivab_0001.tif",
            "20250315 ISAN R1 LS2 Thap_0001.tif",
        ]
        
        for filename in test_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test")
    
    def test_backend_state_saving_and_loading(self):
        """Test that TifFileBackend correctly saves and loads checkbox states."""
        # Create backend
        backend = TifFileBackend(self.test_dir)
        
        # Verify initial state - all files should be checked
        initial_files = backend.get('files')
        self.assertEqual(len(initial_files), 6)
        
        # Uncheck some files
        if len(backend.df) > 0:
            # Uncheck first file
            first_file = backend.df.iloc[0]['full_path']
            backend.set_checked('file', first_file, False)
            
            # Uncheck second file
            second_file = backend.df.iloc[1]['full_path']
            backend.set_checked('file', second_file, False)
            
            # Verify changes
            updated_files = backend.get('files')
            self.assertEqual(len(updated_files), 4)  # 6 - 2 = 4
            
            # Save state
            state_file = backend.save_state()
            self.assertIsNotNone(state_file)
            
            # Create new backend and load state
            backend2 = TifFileBackend(self.test_dir)
            
            # Verify state was loaded correctly
            loaded_files = backend2.get('files')
            self.assertEqual(len(loaded_files), 4)
            
            # Verify specific files are unchecked
            self.assertFalse(backend2.df.loc[backend2.df['full_path'] == first_file, 'show_file'].iloc[0])
            self.assertFalse(backend2.df.loc[backend2.df['full_path'] == second_file, 'show_file'].iloc[0])
    
    def test_boolean_type_consistency(self):
        """Test that boolean values are consistently Python bool type."""
        backend = TifFileBackend(self.test_dir)
        
        # Check that show_file column contains Python bools
        for val in backend.df['show_file']:
            self.assertIsInstance(val, bool)
        
        # Test setting and getting boolean values
        if len(backend.df) > 0:
            first_file = backend.df.iloc[0]['full_path']
            backend.set_checked('file', first_file, False)
            
            # Check that the value is still a Python bool
            updated_val = backend.df.loc[backend.df['full_path'] == first_file, 'show_file'].iloc[0]
            self.assertIsInstance(updated_val, bool)
            self.assertFalse(updated_val)

    def test_backend_initialization(self):
        """Test that TifFileBackend initializes correctly with test data."""
        backend = TifFileBackend(self.test_dir)
        
        # Check that DataFrame was created
        self.assertIsNotNone(backend.df)
        self.assertGreater(len(backend.df), 0)
        
        # Check that all expected columns exist
        expected_columns = [
            'relative_path', 'full_path', 'filename', 'parent_folder', 
            'grandparent_folder', 'great_grandparent_folder', 'date', 
            'cell_id', 'region', 'condition', 'repeat', 'error', 'show_file'
        ]
        for col in expected_columns:
            self.assertIn(col, backend.df.columns)
        
        # Check that all files are checked by default
        self.assertTrue(backend.df['show_file'].all())
        
        # Check that we found the expected number of files
        self.assertEqual(len(backend.df), 6)

if __name__ == '__main__':
    unittest.main() 