"""
Tests for colin_global module.
"""

import sys
import os

# Add the simple_scatter directory to the path so we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'simple_scatter'))

import pandas as pd
from colin_global import FileInfo, iterate_unique_cell_rows


def test_file_info():
    """Test the FileInfo dataclass with various file paths."""
    test_cases = [
        ("20250602 ISAN R3 LS3 Control Epoch 1.tif", {
            'cellID': '20250602 ISAN R3 LS3',
            'epoch': 1,
            'date': '20250602',
            'region': 'ISAN',
            'condition': 'Control'
        }),
        ("20250602 SSAN R1 LS2 Ivab.tif", {
            'cellID': '20250602 SSAN R1 LS2',
            'epoch': 0,
            'date': '20250602',
            'region': 'SSAN',
            'condition': 'Ivab'
        }),
        ("20250602 ISAN R2 LS1 Thap Epoch 2.tif", {
            'cellID': '20250602 ISAN R2 LS1',
            'epoch': 2,
            'date': '20250602',
            'region': 'ISAN',
            'condition': 'Thap'
        }),
        ("20250602 SSAN R4 LS3 Control.tif", {
            'cellID': '20250602 SSAN R4 LS3',
            'epoch': 0,
            'date': '20250602',
            'region': 'SSAN',
            'condition': 'Control'
        })
    ]
    
    for test_path, expected in test_cases:
        file_info = FileInfo.from_path(test_path)
        print(f"Testing FileInfo with: {test_path}")
        print(f"  cellID: {file_info.cellID}")
        print(f"  epoch: {file_info.epoch}")
        print(f"  date: {file_info.date}")
        print(f"  region: {file_info.region}")
        print(f"  condition: {file_info.condition}")
        print()
        
        # Assertions
        assert file_info.cellID == expected['cellID'], f"cellID mismatch: expected {expected['cellID']}, got {file_info.cellID}"
        assert file_info.epoch == expected['epoch'], f"epoch mismatch: expected {expected['epoch']}, got {file_info.epoch}"
        assert file_info.date == expected['date'], f"date mismatch: expected {expected['date']}, got {file_info.date}"
        assert file_info.region == expected['region'], f"region mismatch: expected {expected['region']}, got {file_info.region}"
        assert file_info.condition == expected['condition'], f"condition mismatch: expected {expected['condition']}, got {file_info.condition}"
    
    print("✅ All FileInfo assertions passed!")


def test_iterator_function():
    """Test the iterate_unique_cell_rows function."""
    # Create a sample DataFrame with some duplicate rows and edge cases
    data = {
        'Cell ID': ['20250602 ISAN R3 LS3', '20250602 ISAN R3 LS3', '20250602 ISAN R3 LS3', 
                   '20250602 ISAN R3 LS3', '20250602 ISAN R3 LS3',  # Duplicate Control rows
                   '20250602 SSAN R1 LS2', '20250602 SSAN R1 LS2',
                   '20250602 ISAN R2 LS1', '20250602 ISAN R2 LS1'],
        'Condition': ['Control', 'Ivab', 'Thap', 'Control', 'Control',  # Duplicate Control
                     'Control', 'Ivab',
                     'Control', 'Ivab'],
        'Epoch': [0, 0, 0, 0, 0,  # Same epoch for duplicates
                 1, 1,
                 2, 2],
        'Region': ['ISAN', 'ISAN', 'ISAN', 'ISAN', 'ISAN',
                  'SSAN', 'SSAN',
                  'ISAN', 'ISAN'],
        'Value': [10, 15, 12, 10, 10,  # Same values for duplicates
                 8, 11,
                 20, 25]
    }
    df = pd.DataFrame(data)
    
    print("Sample DataFrame (with duplicates):")
    print(df)
    print()
    
    # Test with first cell ID (has duplicates)
    cell_id = '20250602 ISAN R3 LS3'
    print(f"Unique rows for cell ID: {cell_id}")
    unique_count = 0
    unique_conditions = []
    unique_epochs = []
    unique_values = []
    
    for i, row in enumerate(iterate_unique_cell_rows(df, cell_id)):
        print(f"  Row {i+1}: {row['Condition']} Epoch {row['Epoch']} Value {row['Value']}")
        unique_count += 1
        unique_conditions.append(row['Condition'])
        unique_epochs.append(row['Epoch'])
        unique_values.append(row['Value'])
    
    print(f"  Total unique rows: {unique_count}")
    print()
    
    # Assertions for first cell ID
    assert unique_count == 3, f"Expected 3 unique rows, got {unique_count}"
    assert set(unique_conditions) == {'Control', 'Ivab', 'Thap'}, f"Expected conditions {'Control', 'Ivab', 'Thap'}, got {set(unique_conditions)}"
    assert all(epoch == 0 for epoch in unique_epochs), f"Expected all epochs to be 0, got {unique_epochs}"
    assert set(unique_values) == {10, 15, 12}, f"Expected values {10, 15, 12}, got {set(unique_values)}"
    
    # Test with second cell ID (no duplicates)
    cell_id = '20250602 SSAN R1 LS2'
    print(f"Unique rows for cell ID: {cell_id}")
    unique_count = 0
    unique_conditions = []
    unique_epochs = []
    
    for i, row in enumerate(iterate_unique_cell_rows(df, cell_id)):
        print(f"  Row {i+1}: {row['Condition']} Epoch {row['Epoch']} Value {row['Value']}")
        unique_count += 1
        unique_conditions.append(row['Condition'])
        unique_epochs.append(row['Epoch'])
    
    print(f"  Total unique rows: {unique_count}")
    print()
    
    # Assertions for second cell ID
    assert unique_count == 2, f"Expected 2 unique rows, got {unique_count}"
    assert set(unique_conditions) == {'Control', 'Ivab'}, f"Expected conditions {'Control', 'Ivab'}, got {set(unique_conditions)}"
    assert set(unique_epochs) == {1}, f"Expected all epochs to be 1, got {set(unique_epochs)}"
    
    # Test with non-existent cell ID
    cell_id = 'NonExistentCell'
    print(f"Unique rows for cell ID: {cell_id}")
    unique_count = 0
    for i, row in enumerate(iterate_unique_cell_rows(df, cell_id)):
        print(f"  Row {i+1}: {row['Condition']} Epoch {row['Epoch']}")
        unique_count += 1
    print(f"  Total unique rows: {unique_count}")
    print()
    
    # Assertions for non-existent cell ID
    assert unique_count == 0, f"Expected 0 unique rows for non-existent cell, got {unique_count}"
    
    # Demonstrate using the iterator in a list comprehension
    cell_id = '20250602 ISAN R3 LS3'
    unique_conditions = [row['Condition'] for row in iterate_unique_cell_rows(df, cell_id)]
    print(f"Unique conditions for {cell_id}: {unique_conditions}")
    
    # Assertions for list comprehension
    assert len(unique_conditions) == 3, f"Expected 3 conditions, got {len(unique_conditions)}"
    assert set(unique_conditions) == {'Control', 'Ivab', 'Thap'}, f"Expected conditions {'Control', 'Ivab', 'Thap'}, got {set(unique_conditions)}"
    
    print("✅ All iterator function assertions passed!")


def test_file_info_edge_cases():
    """Test FileInfo with edge cases and error conditions."""
    # Test with missing region
    try:
        file_info = FileInfo.from_path("20250602 R3 LS3 Control.tif")
        print(f"Unexpected success with missing region: {file_info.region}")
        # Should not reach here - should have logged an error
        assert file_info.region == 'Unknown', f"Expected 'Unknown' region, got {file_info.region}"
    except Exception as e:
        print(f"Expected error with missing region: {e}")
    
    # Test with missing condition
    try:
        file_info = FileInfo.from_path("20250602 ISAN R3 LS3.tif")
        print(f"Unexpected success with missing condition: {file_info.condition}")
        # Should not reach here - should have logged an error
        assert file_info.condition == 'Unknown', f"Expected 'Unknown' condition, got {file_info.condition}"
    except Exception as e:
        print(f"Expected error with missing condition: {e}")
    
    # Test with different epoch formats
    test_paths = [
        ("20250602 ISAN R3 LS3 Control Epoch 5.tif", 5),
        ("20250602 ISAN R3 LS3 Control.tif", 0),  # No epoch
        ("20250602 ISAN R3 LS3 Control Epoch 0.tif", 0)
    ]
    
    for test_path, expected_epoch in test_paths:
        file_info = FileInfo.from_path(test_path)
        print(f"Testing: {test_path}")
        print(f"  Epoch: {file_info.epoch}")
        print()
        
        # Assertions
        assert file_info.epoch == expected_epoch, f"Expected epoch {expected_epoch}, got {file_info.epoch}"
        assert file_info.region == 'ISAN', f"Expected region 'ISAN', got {file_info.region}"
        assert file_info.condition == 'Control', f"Expected condition 'Control', got {file_info.condition}"
    
    print("✅ All edge case assertions passed!")


if __name__ == '__main__':
    print("Running colin_global tests...")
    print("=" * 50)
    
    print("\n1. Testing FileInfo dataclass:")
    test_file_info()
    
    print("\n2. Testing iterator function:")
    test_iterator_function()
    
    print("\n3. Testing edge cases:")
    test_file_info_edge_cases()
    
    print("\n🎉 All tests completed successfully!") 