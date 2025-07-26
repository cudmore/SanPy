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
            first_relative_path = backend.df.iloc[0]['relative_path']
            first_full_path = backend.get_full_path(first_relative_path)
            backend.set_checked('file', first_full_path, False)
            
            # Check if the change was applied
            updated_checked = backend.get('files')
            self.assertEqual(len(updated_checked), initial_count - 1)
            
            # Set it back to checked
            backend.set_checked('file', first_full_path, True)
            final_checked = backend.get('files')
            self.assertEqual(len(final_checked), initial_count)
    
    def test_state_saving_and_loading(self):
        """Test saving and loading state."""
        backend = TifFileBackend(self.test_dir)
        
        # Modify a file's checked state
        if len(backend.df) > 0:
            first_relative_path = backend.df.iloc[0]['relative_path']
            first_full_path = backend.get_full_path(first_relative_path)
            backend.set_checked('file', first_full_path, False)
            
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
            first_relative_path = backend1.df.iloc[0]['relative_path']
            first_full_path = backend1.get_full_path(first_relative_path)
            print(f"DEBUG: Setting file {first_full_path} to False")
            backend1.set_checked('file', first_full_path, False)
            backend1.save_state()  # Save to default location
        
        # Create a new backend instance (should auto-load the state)
        backend2 = TifFileBackend(self.test_dir)
        
        # Check if state was automatically loaded for the same file by relative_path
        if len(backend2.df) > 0:
            mask = backend2.df['relative_path'] == first_relative_path
            self.assertTrue(mask.any())
            is_checked = backend2.df.loc[mask, 'show_file'].iloc[0]
            print(f"DEBUG: File {first_full_path} has show_file = {is_checked} (type: {type(is_checked)})")
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
        self.assertTrue(backend.df['Repeat'].dtype in ['int32', 'int64'])
        
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

    def test_real_data_folder_1(self):
        """Test backend with real data from mito-atp-20250623-RHC folder."""
        folder_path = "/Users/cudmore/Dropbox/data/colin/2025/mito-atp/mito-atp-20250623-RHC"
        
        if not os.path.exists(folder_path):
            self.skipTest(f"Test folder does not exist: {folder_path}")
        
        print(f"\nTesting real data folder 1: {folder_path}")
        
        # Create backend
        backend = TifFileBackend(folder_path)
        
        # Basic checks
        self.assertIsNotNone(backend.df)
        file_count = len(backend.df)
        print(f"Found {file_count} .tif files")
        
        if file_count > 0:
            # Check that we have the expected columns
            expected_columns = ['relative_path', 'filename', 'date', 'cell_id', 'region', 'condition', 'repeat', 'error']
            for col in expected_columns:
                self.assertIn(col, backend.df.columns, f"Missing column: {col}")
            
            # Check that relative_path is properly set and full_path is constructed correctly
            for idx, row in backend.df.iterrows():
                relative_path = row['relative_path']
                filename = row['filename']
                
                # Verify relative_path is relative to root
                self.assertFalse(os.path.isabs(relative_path), f"relative_path should be relative: {relative_path}")
                
                # Verify full_path is constructed correctly
                full_path = backend.get_full_path(relative_path)
                self.assertTrue(os.path.isabs(full_path), f"full_path should be absolute: {full_path}")
                
                # Verify resolve_path works correctly
                resolved_path = backend.resolve_path(relative_path)
                self.assertEqual(resolved_path, full_path, f"Path resolution failed for {filename}")
                
                # Verify file exists
                self.assertTrue(os.path.exists(full_path), f"File does not exist: {full_path}")
            
            # Check unique conditions and repeats
            conditions = backend.get('unique_conditions')
            repeats = backend.get('unique_repeats')
            print(f"Unique conditions: {conditions}")
            print(f"Unique repeats: {repeats}")
            
            # Test filtering
            if conditions:
                first_condition = conditions[0]
                filtered_files = backend.get('filter_by_condition', condition=first_condition)
                print(f"Files with condition '{first_condition}': {len(filtered_files)}")
            
            # Test path resolution for a few files
            for i, row in backend.df.head(3).iterrows():
                relative_path = row['relative_path']
                full_path = backend.get_full_path(relative_path)
                resolved_path = backend.resolve_path(relative_path)
                self.assertEqual(resolved_path, full_path, f"Path resolution failed for row {i}")
        
        # Test state saving (should not fail even with no files)
        state_file = backend.save_state()
        if state_file:
            print(f"State saved to: {state_file}")
            self.assertTrue(os.path.exists(state_file))

    def test_real_data_folder_2(self):
        """Test backend with real data from mito-iATP Analysis folder."""
        folder_path = "/Users/cudmore/Dropbox/data/colin/2025/mito-atp/mito-iATP Analysis"
        
        if not os.path.exists(folder_path):
            self.skipTest(f"Test folder does not exist: {folder_path}")
        
        print(f"\nTesting real data folder 2: {folder_path}")
        
        # Create backend
        backend = TifFileBackend(folder_path)
        
        # Basic checks
        self.assertIsNotNone(backend.df)
        file_count = len(backend.df)
        print(f"Found {file_count} .tif files")
        
        if file_count > 0:
            # Check that we have the expected columns
            expected_columns = ['relative_path', 'filename', 'date', 'cell_id', 'region', 'condition', 'repeat', 'error']
            for col in expected_columns:
                self.assertIn(col, backend.df.columns, f"Missing column: {col}")
            
            # Check that relative_path is properly set and full_path is constructed correctly
            for idx, row in backend.df.iterrows():
                relative_path = row['relative_path']
                filename = row['filename']
                
                # Verify relative_path is relative to root
                self.assertFalse(os.path.isabs(relative_path), f"relative_path should be relative: {relative_path}")
                
                # Verify full_path is constructed correctly
                full_path = backend.get_full_path(relative_path)
                self.assertTrue(os.path.isabs(full_path), f"full_path should be absolute: {full_path}")
                
                # Verify resolve_path works correctly
                resolved_path = backend.resolve_path(relative_path)
                self.assertEqual(resolved_path, full_path, f"Path resolution failed for {filename}")
                
                # Verify file exists
                self.assertTrue(os.path.exists(full_path), f"File does not exist: {full_path}")
            
            # Check unique conditions and repeats
            conditions = backend.get('unique_conditions')
            repeats = backend.get('unique_repeats')
            print(f"Unique conditions: {conditions}")
            print(f"Unique repeats: {repeats}")
            
            # Test filtering
            if conditions:
                first_condition = conditions[0]
                filtered_files = backend.get('filter_by_condition', condition=first_condition)
                print(f"Files with condition '{first_condition}': {len(filtered_files)}")
            
            # Test path resolution for a few files
            for i, row in backend.df.head(3).iterrows():
                relative_path = row['relative_path']
                full_path = backend.get_full_path(relative_path)
                resolved_path = backend.resolve_path(relative_path)
                self.assertEqual(resolved_path, full_path, f"Path resolution failed for row {i}")
        
        # Test state saving (should not fail even with no files)
        state_file = backend.save_state()
        if state_file:
            print(f"State saved to: {state_file}")
            self.assertTrue(os.path.exists(state_file))

    def test_kym_roi_analysis_integration(self):
        """Test KymRoiAnalysis integration with real data folders."""
        # Test with both real folders
        test_folders = [
            "/Users/cudmore/Dropbox/data/colin/2025/mito-atp/mito-atp-20250623-RHC",
            "/Users/cudmore/Dropbox/data/colin/2025/mito-atp/mito-iATP Analysis"
        ]
        
        for folder_path in test_folders:
            if not os.path.exists(folder_path):
                print(f"Skipping folder (does not exist): {folder_path}")
                continue
            
            print(f"\nTesting KymRoiAnalysis integration with: {folder_path}")
            
            backend = TifFileBackend(folder_path)
            
            if len(backend.df) == 0:
                print("No files found, skipping KymRoiAnalysis tests")
                continue
            
            # Check that KymRoiAnalysis columns exist
            self.assertIn('_KymRoiAnalysis', backend.df.columns)
            self.assertIn('_KymRoiAnalysis_Loaded', backend.df.columns)
            
            # Check initial state
            self.assertTrue(backend.df['_KymRoiAnalysis'].isna().all(), "KymRoiAnalysis should be None initially")
            self.assertFalse(backend.df['_KymRoiAnalysis_Loaded'].any(), "KymRoiAnalysis should not be loaded initially")
            
            # Test loading KymRoiAnalysis for first few files
            for i, row in backend.df.head(2).iterrows():
                filename = row['filename']
                relative_path = row['relative_path']
                
                print(f"Testing KymRoiAnalysis loading for: {filename}")
                
                # Test loading by row index
                kym_analysis = backend.get_kym_roi_analysis(i)
                if kym_analysis is not None:
                    print(f"  ✓ Successfully loaded KymRoiAnalysis for row {i}")
                    self.assertTrue(backend.df.iloc[i]['_KymRoiAnalysis_Loaded'])
                else:
                    print(f"  ✗ Failed to load KymRoiAnalysis for row {i}")
                
                # Test loading by relative path
                kym_analysis_by_relative_path = backend.get_kym_roi_analysis_by_path(relative_path)
                if kym_analysis_by_relative_path is not None:
                    print(f"  ✓ Successfully loaded KymRoiAnalysis by relative path: {relative_path}")
                else:
                    print(f"  ✗ Failed to load KymRoiAnalysis by relative path: {relative_path}")
            
            # Test cache clearing
            cached_count = backend.get_cached_kym_roi_analysis_count()
            print(f"Cached KymRoiAnalysis objects: {cached_count}")
            
            if cached_count > 0:
                backend.clear_kym_roi_analysis_cache()
                new_cached_count = backend.get_cached_kym_roi_analysis_count()
                self.assertEqual(new_cached_count, 0, "Cache should be cleared")
                print("  ✓ Cache cleared successfully")

    def test_note_column_workflow(self):
        """Test the complete note column workflow: edit, save, reload."""
        print(f"\nTesting note column workflow with test directory: {self.test_dir}")
        
        # Step 1: Create initial backend and verify note column exists
        backend1 = TifFileBackend(self.test_dir)
        self.assertIn('note', backend1.df.columns, "Note column should exist in DataFrame")
        
        if len(backend1.df) == 0:
            self.skipTest("No files found for note testing")
        
        # Get first file info
        first_row = backend1.df.iloc[0]
        first_relative_path = first_row['relative_path']
        initial_note = first_row['note']
        
        print(f"Testing with file: {first_relative_path}")
        print(f"Initial note: '{initial_note}'")
        
        # Step 2: Edit a note using the backend API
        test_note = "This is a test note for the file"
        print(f"Setting note to: '{test_note}'")
        
        # Update the note in the backend
        mask = backend1.df['relative_path'] == first_relative_path
        self.assertTrue(mask.any(), f"File {first_relative_path} should exist in backend")
        backend1.df.loc[mask, 'note'] = test_note
        
        # Verify the note was updated in memory
        updated_note = backend1.df.loc[mask, 'note'].iloc[0]
        self.assertEqual(updated_note, test_note, f"Note should be updated in memory. Expected: '{test_note}', Got: '{updated_note}'")
        print(f"✅ Note updated in memory: '{updated_note}'")
        
        # Step 3: Save the state to CSV
        state_filepath = backend1.save_state()
        self.assertIsNotNone(state_filepath, "State should be saved successfully")
        self.assertTrue(os.path.exists(state_filepath), f"State file should exist: {state_filepath}")
        print(f"✅ State saved to: {state_filepath}")
        
        # Step 4: Create a new backend instance to test loading
        backend2 = TifFileBackend(self.test_dir)
        self.assertIn('note', backend2.df.columns, "Note column should exist in new backend")
        
        # Step 5: Verify the note was loaded correctly
        mask2 = backend2.df['relative_path'] == first_relative_path
        self.assertTrue(mask2.any(), f"File {first_relative_path} should exist in new backend")
        
        loaded_note = backend2.df.loc[mask2, 'note'].iloc[0]
        print(f"Loaded note: '{loaded_note}'")
        
        # The note should be loaded correctly
        self.assertEqual(loaded_note, test_note, f"Note should be loaded correctly. Expected: '{test_note}', Got: '{loaded_note}'")
        print(f"✅ Note loaded correctly: '{loaded_note}'")
        
        # Step 6: Test that other files still have empty notes
        other_files = backend2.df[backend2.df['relative_path'] != first_relative_path]
        if len(other_files) > 0:
            other_notes = other_files['note'].tolist()
            print(f"Other files notes: {other_notes}")
            for note in other_notes:
                self.assertEqual(note, '', f"Other files should have empty notes, got: '{note}'")
            print("✅ Other files have empty notes")
        
        # Step 7: Test editing multiple notes
        if len(backend2.df) > 1:
            second_row = backend2.df.iloc[1]
            second_relative_path = second_row['relative_path']
            second_test_note = "Second file note"
            
            print(f"Testing second file: {second_relative_path}")
            print(f"Setting second note to: '{second_test_note}'")
            
            # Update second note
            mask3 = backend2.df['relative_path'] == second_relative_path
            backend2.df.loc[mask3, 'note'] = second_test_note
            
            # Save and reload
            backend2.save_state()
            backend3 = TifFileBackend(self.test_dir)
            
            # Verify both notes are correct
            mask4 = backend3.df['relative_path'] == first_relative_path
            mask5 = backend3.df['relative_path'] == second_relative_path
            
            first_note_final = backend3.df.loc[mask4, 'note'].iloc[0]
            second_note_final = backend3.df.loc[mask5, 'note'].iloc[0]
            
            self.assertEqual(first_note_final, test_note, f"First note should persist. Expected: '{test_note}', Got: '{first_note_final}'")
            self.assertEqual(second_note_final, second_test_note, f"Second note should be saved. Expected: '{second_test_note}', Got: '{second_note_final}'")
            
            print(f"✅ First note persists: '{first_note_final}'")
            print(f"✅ Second note saved: '{second_note_final}'")
        
        print("✅ Note column workflow test completed successfully!")

    def test_note_column_initialization(self):
        """Test that note column is properly initialized."""
        backend = TifFileBackend(self.test_dir)
        
        # Check that note column exists and is configured correctly
        self.assertIn('note', backend.df.columns, "Note column should exist")
        
        note_config = backend.get_column_config('note')
        self.assertTrue(note_config.get('editable', False), "Note column should be editable")
        self.assertTrue(note_config.get('table_visible', False), "Note column should be visible in table")
        
        # Check that all notes are initialized to empty string
        if len(backend.df) > 0:
            note_values = backend.df['Note'].tolist()
            for note in note_values:
                self.assertEqual(note, '', f"Notes should be initialized to empty string, got: '{note}'")
        
        print("✅ Note column initialization test passed")

    def test_note_column_with_special_characters(self):
        """Test that note column handles special characters correctly."""
        backend = TifFileBackend(self.test_dir)
        
        if len(backend.df) == 0:
            self.skipTest("No files found for special character testing")
        
        # Test note with special characters
        special_note = "Test note with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        first_relative_path = backend.df.iloc[0]['relative_path']
        
        # Update note
        mask = backend.df['relative_path'] == first_relative_path
        backend.df.loc[mask, 'note'] = special_note
        
        # Save and reload
        backend.save_state()
        backend2 = TifFileBackend(self.test_dir)
        
        # Verify special characters are preserved
        mask2 = backend2.df['relative_path'] == first_relative_path
        loaded_note = backend2.df.loc[mask2, 'note'].iloc[0]
        
        self.assertEqual(loaded_note, special_note, f"Special characters should be preserved. Expected: '{special_note}', Got: '{loaded_note}'")
        print("✅ Special characters preserved in note")

    def test_note_column_with_multiline_text(self):
        """Test that note column handles multiline text correctly."""
        backend = TifFileBackend(self.test_dir)
        
        if len(backend.df) == 0:
            self.skipTest("No files found for multiline testing")
        
        # Test note with newlines
        multiline_note = "Line 1\nLine 2\nLine 3 with special chars: !@#$%"
        first_relative_path = backend.df.iloc[0]['relative_path']
        
        # Update note
        mask = backend.df['relative_path'] == first_relative_path
        backend.df.loc[mask, 'note'] = multiline_note
        
        # Save and reload
        backend.save_state()
        backend2 = TifFileBackend(self.test_dir)
        
        # Verify multiline text is preserved
        mask2 = backend2.df['relative_path'] == first_relative_path
        loaded_note = backend2.df.loc[mask2, 'note'].iloc[0]
        
        self.assertEqual(loaded_note, multiline_note, f"Multiline text should be preserved. Expected: '{multiline_note}', Got: '{loaded_note}'")
        print("✅ Multiline text preserved in note")


if __name__ == '__main__':
    unittest.main() 