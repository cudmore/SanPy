#!/usr/bin/env python3
"""
Unit tests for TifFileBackend class.
"""

import unittest
import tempfile
import shutil
import os

from sanpy.kym.tif_file_backend import TifFileBackend


class TestTifFileBackend(unittest.TestCase):
    """Test cases for TifFileBackend class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.create_test_files()
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)
    
    def create_test_files(self):
        """Create test .tif files with various conditions and repeats."""
        test_structure = [
            "20250312 ISAN R1 LS2 FCCP.tif",
            "20250312 ISAN R1 LS1 Control.tif",
            "20250312 ISAN R2 LS2 FCCP.tif",
            "20250312 ISAN R2 LS1 Control.tif",
            "20250312 ISAN R3 LS2 Ivab.tif",
            "20250312 ISAN R3 LS1 Thap.tif",
            "20250312 ISAN R3 LS1 Thap_0001.tif",
            "20250312 ISAN R3 LS1 Thap_0002.tif",
        ]
        
        for file_path in test_structure:
            full_path = os.path.join(self.test_dir, file_path)
            # Create an empty file
            with open(full_path, 'w') as f:
                f.write("test")
    
    def test_backend_initialization(self):
        """Test backend initialization and file scanning."""
        backend = TifFileBackend(self.test_dir)
        
        # Check that files were found
        file_count = backend.get('file_count')
        self.assertGreater(file_count, 0)
        self.assertEqual(file_count, 8)  # We created 8 test files
        
        # Check that conditions were extracted
        conditions = backend.get('unique_conditions')
        self.assertIn('Control', conditions)
        self.assertIn('FCCP', conditions)
        self.assertIn('Ivab', conditions)
        self.assertIn('Thap', conditions)
    
    def test_condition_extraction(self):
        """Test condition extraction from filenames."""
        backend = TifFileBackend(self.test_dir)
        
        # Check specific files
        for idx, row in backend.df.iterrows():
            filename = row['filename']
            condition = row['condition']
            
            if 'FCCP' in filename:
                self.assertEqual(condition, 'FCCP')
            elif 'Control' in filename:
                self.assertEqual(condition, 'Control')
            elif 'Ivab' in filename:
                self.assertEqual(condition, 'Ivab')
            elif 'Thap' in filename:
                self.assertEqual(condition, 'Thap')
    
    def test_repeat_extraction(self):
        """Test repeat number extraction from filenames."""
        backend = TifFileBackend(self.test_dir)
        
        # Check that repeat numbers are extracted correctly
        for idx, row in backend.df.iterrows():
            filename = row['filename']
            repeat = row['repeat']
            
            # TifFileBackend only extracts from _0001 pattern, not R1/R2/R3
            if '0001' in filename:
                self.assertEqual(repeat, 1)
            elif '0002' in filename:
                self.assertEqual(repeat, 2)
            else:
                # R1, R2, R3 patterns are not extracted by current implementation
                self.assertEqual(repeat, 0)
    
    def test_filtering_by_condition(self):
        """Test filtering files by condition."""
        backend = TifFileBackend(self.test_dir)
        
        # Filter by Control condition
        control_files = backend.get('filter_by_condition', condition="Control")
        self.assertEqual(len(control_files), 2)  # Should find 2 Control files
        
        # Filter by FCCP condition
        fccp_files = backend.get('filter_by_condition', condition="FCCP")
        self.assertEqual(len(fccp_files), 2)  # Should find 2 FCCP files
    
    def test_filtering_by_repeat(self):
        """Test filtering files by repeat number."""
        backend = TifFileBackend(self.test_dir)
        
        # Filter by repeat 1 (only _0001 files)
        repeat_1_files = backend.get('filter_by_repeat', repeat=1)
        self.assertEqual(len(repeat_1_files), 1)  # Only 1 file with _0001 pattern
        
        # Filter by repeat 2 (only _0002 files)
        repeat_2_files = backend.get('filter_by_repeat', repeat=2)
        self.assertEqual(len(repeat_2_files), 1)  # Only 1 file with _0002 pattern
        
        # Filter by repeat 0 (files without _000 pattern)
        repeat_0_files = backend.get('filter_by_repeat', repeat=0)
        self.assertEqual(len(repeat_0_files), 6)  # 6 files without _000 pattern
    
    def test_checked_state_management(self):
        """Test setting and getting checked states."""
        backend = TifFileBackend(self.test_dir)
        
        # Get initial checked files
        initial_checked = backend.get('files')
        initial_count = len(initial_checked)
        
        # Set a file to unchecked
        if len(backend.df) > 0:
            first_file = backend.df.iloc[0]['full_path']
            backend.set_checked('file', first_file, False)
            
            # Check if the change was applied
            updated_checked = backend.get('files')
            self.assertEqual(len(updated_checked), initial_count - 1)
            
            # Set it back to checked
            backend.set_checked('file', first_file, True)
            final_checked = backend.get('files')
            self.assertEqual(len(final_checked), initial_count)
    
    def test_state_saving_and_loading(self):
        """Test saving and loading state."""
        backend = TifFileBackend(self.test_dir)
        
        # Modify a file's checked state
        if len(backend.df) > 0:
            first_file = backend.df.iloc[0]['full_path']
            backend.set_checked('file', first_file, False)
            
            # Save state
            state_file = os.path.join(self.test_dir, "test_state.csv")
            backend.save_state(state_file)
            
            # Verify file was created
            self.assertTrue(os.path.exists(state_file))
            
            # Load state back
            backend.load_state(state_file)
            
            # Check if the modification was preserved
            is_checked = backend.df.iloc[0]['show_file']
            self.assertFalse(is_checked)
    
    def test_automatic_state_loading(self):
        """Test automatic state loading on initialization."""
        backend1 = TifFileBackend(self.test_dir)
        
        # Modify state
        if len(backend1.df) > 0:
            first_file = backend1.df.iloc[0]['full_path']
            print(f"DEBUG: Setting file {first_file} to False")
            backend1.set_checked('file', first_file, False)
            backend1.save_state()  # Save to default location
        
        # Create a new backend instance (should auto-load the state)
        backend2 = TifFileBackend(self.test_dir)
        
        # Check if state was automatically loaded for the same file by full_path
        if len(backend2.df) > 0:
            mask = backend2.df['full_path'] == first_file
            self.assertTrue(mask.any())
            is_checked = backend2.df.loc[mask, 'show_file'].iloc[0]
            print(f"DEBUG: File {first_file} has show_file = {is_checked} (type: {type(is_checked)})")
            print(f"DEBUG: All show_file values: {backend2.df['show_file'].tolist()}")
            self.assertFalse(is_checked)
    
    def test_folder_hierarchy_extraction(self):
        """Test extraction of folder hierarchy information."""
        # Create a nested folder structure
        nested_dir = os.path.join(self.test_dir, "level1", "level2", "level3")
        os.makedirs(nested_dir, exist_ok=True)
        
        _newFile = '20250312 ISAN R1 LS2.tif'

        # Create a file in the nested directory
        nested_file = os.path.join(nested_dir, _newFile)
        with open(nested_file, 'w') as f:
            f.write("test")
        
        backend = TifFileBackend(self.test_dir)
        
        # Find the nested file
        nested_file_row = backend.df[backend.df['filename'] == _newFile].iloc[0]
        
        # Check folder hierarchy
        self.assertEqual(nested_file_row['parent_folder'], 'level3')
        self.assertEqual(nested_file_row['grandparent_folder'], 'level2')
        self.assertEqual(nested_file_row['great_grandparent_folder'], 'level1')
    
    def test_exclude_folders(self):
        """Test that excluded folders are properly ignored."""
        # Create an excluded folder
        excluded_dir = os.path.join(self.test_dir, "sanpy-reports-pdf")
        os.makedirs(excluded_dir, exist_ok=True)
        
        # Create a file in the excluded directory
        excluded_file = os.path.join(excluded_dir, "excluded_file.tif")
        with open(excluded_file, 'w') as f:
            f.write("test")
        
        backend = TifFileBackend(self.test_dir)
        
        # Check that the excluded file is not in the dataframe
        excluded_files = backend.df[backend.df['filename'] == 'excluded_file.tif']
        self.assertEqual(len(excluded_files), 0)
    
    def test_invalid_root_path(self):
        """Test behavior with invalid root path."""
        invalid_path = "/path/that/does/not/exist"
        backend = TifFileBackend(invalid_path)
        
        # Should handle gracefully without crashing
        self.assertIsNotNone(backend.df)
        self.assertEqual(len(backend.df), 0)
    
    def test_tifinfo_integration(self):
        """Test that TifFileBackend correctly uses TifInfo for parsing filenames."""
        # Clean up any existing files first
        for file in os.listdir(self.test_dir):
            if file.endswith('.tif'):
                os.remove(os.path.join(self.test_dir, file))
        
        # Create test files with various TifInfo patterns
        test_files = [
            "20250312 ISAN R3 LS1 Thap_0003.tif",  # Valid TifInfo format with repeat 3
            "20250315 ISAN R1 LS2 Control_0001.tif",  # Valid TifInfo format with repeat 1
            "20250318 ISAN R2 LS3 FCCP_0002.tif",  # Valid TifInfo format with repeat 2
            "20250320 ISAN R1 LS4 Ivab_0001.tif",  # Valid TifInfo format with repeat 1
            "invalid_filename.tif",  # Invalid format - should have error
            "20250325 ISAN R5 LS5 Unknown_0005.tif",  # Valid format with unknown condition and repeat 5
        ]
        
        for filename in test_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test")
        
        backend = TifFileBackend(self.test_dir)
        
        # Check that all files were found
        self.assertEqual(len(backend.df), len(test_files))
        
        # Check that TifInfo columns are present
        expected_columns = ['date', 'cell_id', 'region', 'condition', 'repeat', 'error']
        for col in expected_columns:
            self.assertIn(col, backend.df.columns)
        
        # Check specific TifInfo parsing results
        for idx, row in backend.df.iterrows():
            filename = row['filename']
            
            if filename == "20250312 ISAN R3 LS1 Thap_0003.tif":
                self.assertEqual(row['date'], "20250312")
                self.assertEqual(row['cell_id'], "20250312 ISAN R3 LS1")
                self.assertEqual(row['region'], "ISAN")
                self.assertEqual(row['condition'], "Thap")
                self.assertEqual(row['repeat'], 3)
                self.assertEqual(row['error'], "")
                
            elif filename == "20250315 ISAN R1 LS2 Control_0001.tif":
                self.assertEqual(row['date'], "20250315")
                self.assertEqual(row['cell_id'], "20250315 ISAN R1 LS2")
                self.assertEqual(row['region'], "ISAN")
                self.assertEqual(row['condition'], "Control")
                self.assertEqual(row['repeat'], 1)
                self.assertEqual(row['error'], "")
                
            elif filename == "20250318 ISAN R2 LS3 FCCP_0002.tif":
                self.assertEqual(row['date'], "20250318")
                self.assertEqual(row['cell_id'], "20250318 ISAN R2 LS3")
                self.assertEqual(row['region'], "ISAN")
                self.assertEqual(row['condition'], "FCCP")
                self.assertEqual(row['repeat'], 2)
                self.assertEqual(row['error'], "")
                
            elif filename == "20250320 ISAN R1 LS4 Ivab_0001.tif":
                self.assertEqual(row['date'], "20250320")
                self.assertEqual(row['cell_id'], "20250320 ISAN R1 LS4")
                self.assertEqual(row['region'], "ISAN")
                self.assertEqual(row['condition'], "Ivab")
                self.assertEqual(row['repeat'], 1)
                self.assertEqual(row['error'], "")
                
            elif filename == "invalid_filename.tif":
                # Should have error and default values
                self.assertEqual(row['date'], "")
                self.assertEqual(row['cell_id'], "")
                self.assertEqual(row['region'], "")
                self.assertEqual(row['condition'], "Control")  # Default condition
                self.assertEqual(row['repeat'], 0)
                self.assertNotEqual(row['error'], "")  # Should have error message
                
            elif filename == "20250325 ISAN R5 LS5 Unknown_0005.tif":
                self.assertEqual(row['date'], "20250325")
                self.assertEqual(row['cell_id'], "20250325 ISAN R5 LS5 Unknown")
                self.assertEqual(row['region'], "ISAN")
                self.assertEqual(row['condition'], "Control")  # Default condition since "Unknown" is not in POSSIBLE_CONDITIONS
                self.assertEqual(row['repeat'], 5)
                self.assertEqual(row['error'], "")
        
        # Check that repeat column is always integer
        self.assertTrue(backend.df['repeat'].dtype in ['int32', 'int64'])
        
        # Check that condition extraction is now from TifInfo (not regex)
        conditions = backend.get('unique_conditions')
        self.assertIn('Control', conditions)
        self.assertIn('FCCP', conditions)
        self.assertIn('Ivab', conditions)
        self.assertIn('Thap', conditions)
        
        # Check that repeat extraction is now from TifInfo
        repeats = backend.get('unique_repeats')
        self.assertIn(1, repeats)
        self.assertIn(2, repeats)
        self.assertIn(3, repeats)
        self.assertIn(5, repeats)
        self.assertIn(0, repeats)  # From invalid filename


if __name__ == '__main__':
    unittest.main() 