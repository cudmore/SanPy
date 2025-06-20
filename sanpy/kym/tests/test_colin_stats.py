"""
Tests for colin_stats module.
"""

import sys
import os

# Add the simple_scatter directory to the path so we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'simple_scatter'))

import pandas as pd
from colin_stats import FileInfo


def test_file_info_usage():
    """Test that FileInfo works correctly in colin_stats module."""
    test_path = "20250602 ISAN R3 LS3 Control Epoch 1.tif"
    file_info = FileInfo.from_path(test_path)
    print(f"Testing FileInfo in colin_stats with: {test_path}")
    print(f"  cellID: {file_info.cellID}")
    print(f"  epoch: {file_info.epoch}")
    print(f"  date: {file_info.date}")
    print(f"  region: {file_info.region}")
    print(f"  condition: {file_info.condition}")
    print()
    
    # Assertions
    expected = {
        'cellID': '20250602 ISAN R3 LS3',
        'epoch': 1,
        'date': '20250602',
        'region': 'ISAN',
        'condition': 'Control'
    }
    
    assert file_info.cellID == expected['cellID'], f"cellID mismatch: expected {expected['cellID']}, got {file_info.cellID}"
    assert file_info.epoch == expected['epoch'], f"epoch mismatch: expected {expected['epoch']}, got {file_info.epoch}"
    assert file_info.date == expected['date'], f"date mismatch: expected {expected['date']}, got {file_info.date}"
    assert file_info.region == expected['region'], f"region mismatch: expected {expected['region']}, got {file_info.region}"
    assert file_info.condition == expected['condition'], f"condition mismatch: expected {expected['condition']}, got {file_info.condition}"
    
    print("✅ All FileInfo usage assertions passed!")


def test_remove_one_spike_control_logic():
    """Test the logic of _removeOneSpikeControl function without running the full analysis."""
    # Create a sample DataFrame that mimics the structure used in _removeOneSpikeControl
    data = {
        'Cell ID': ['20250602 ISAN R3 LS3', '20250602 ISAN R3 LS3', '20250602 ISAN R3 LS3',
                   '20250602 ISAN R3 LS3', '20250602 ISAN R3 LS3', '20250602 ISAN R3 LS3',
                   '20250602 SSAN R1 LS2', '20250602 SSAN R1 LS2', '20250602 SSAN R1 LS2'],
        'Condition': ['Control', 'Control', 'Control', 'Ivab', 'Ivab', 'Thap',
                     'Control', 'Ivab', 'Thap'],
        'Epoch': [0, 1, 2, 0, 1, 0, 0, 0, 0],
        'ROI Number': ['R1', 'R1', 'R1', 'R1', 'R1', 'R1', 'R2', 'R2', 'R2'],
        'Number of Spikes': [1, 2, 3, 5, 6, 4, 0, 3, 2],  # First cell has <=2 spikes in last epoch
        'Region': ['ISAN', 'ISAN', 'ISAN', 'ISAN', 'ISAN', 'ISAN', 'SSAN', 'SSAN', 'SSAN']
    }
    dfMean = pd.DataFrame(data)
    
    print("Sample DataFrame for _removeOneSpikeControl test:")
    print(dfMean)
    print()
    
    # Simulate the logic from _removeOneSpikeControl
    removeLessThanEqual = 2
    
    # Create an explicit copy to avoid SettingWithCopyWarning
    dfControl = dfMean[dfMean['Condition'] == 'Control'].copy()
    
    # For each cell id, get the last epoch
    dfControl['Last Epoch'] = dfControl.groupby('Cell ID')['Epoch'].transform('max')
    
    # Filter by last epoch
    dfControl = dfControl[dfControl['Epoch'] == dfControl['Last Epoch']]
    
    # Filter by number of spikes
    dfOneSpike = dfControl[dfControl['Number of Spikes'] <= removeLessThanEqual]
    
    print("Control rows after filtering by last epoch:")
    print(dfControl)
    print()
    
    print("Rows with <=2 spikes in last epoch:")
    print(dfOneSpike)
    print()
    
    numControlWithOneSpike = len(dfOneSpike['Cell ID'].unique())
    print(f"Number of Cell IDs with <= {removeLessThanEqual} peaks: {numControlWithOneSpike}")
    
    # Show which cells would be flagged
    flagged_cells = []
    for _, row in dfOneSpike.iterrows():
        cellID = row['Cell ID']
        roiNumber = row['ROI Number']
        print(f"  Would flag: Cell ID '{cellID}', ROI '{roiNumber}'")
        flagged_cells.append((cellID, roiNumber))
    
    # Assertions
    assert len(dfControl) == 2, f"Expected 2 control rows after filtering by last epoch, got {len(dfControl)}"
    assert len(dfOneSpike) == 1, f"Expected 1 row with <=2 spikes, got {len(dfOneSpike)}"
    assert numControlWithOneSpike == 1, f"Expected 1 cell ID with <=2 peaks, got {numControlWithOneSpike}"
    
    # Check specific values
    expected_flagged_cell = ('20250602 SSAN R1 LS2', 'R2')
    assert flagged_cells == [expected_flagged_cell], f"Expected flagged cell {expected_flagged_cell}, got {flagged_cells}"
    
    # Check that the flagged cell has 0 spikes
    flagged_row = dfOneSpike.iloc[0]
    assert flagged_row['Number of Spikes'] == 0, f"Expected 0 spikes for flagged cell, got {flagged_row['Number of Spikes']}"
    assert flagged_row['Epoch'] == 0, f"Expected epoch 0 for flagged cell, got {flagged_row['Epoch']}"
    
    print("✅ All _removeOneSpikeControl logic assertions passed!")


def test_dataframe_operations():
    """Test various DataFrame operations that might be used in colin_stats."""
    # Test the groupby and transform operations
    data = {
        'Cell ID': ['A', 'A', 'A', 'B', 'B', 'B'],
        'Epoch': [0, 1, 2, 0, 1, 3],
        'Value': [10, 20, 30, 5, 15, 25]
    }
    df = pd.DataFrame(data)
    
    print("Original DataFrame:")
    print(df)
    print()
    
    # Test groupby transform
    df['Max Epoch'] = df.groupby('Cell ID')['Epoch'].transform('max')
    print("After adding Max Epoch column:")
    print(df)
    print()
    
    # Test filtering by condition
    df_filtered = df[df['Epoch'] == df['Max Epoch']]
    print("Filtered to last epoch for each cell:")
    print(df_filtered)
    print()
    
    # Assertions
    assert len(df) == 6, f"Expected 6 rows in original DataFrame, got {len(df)}"
    assert len(df_filtered) == 2, f"Expected 2 rows after filtering, got {len(df_filtered)}"
    
    # Check Max Epoch values
    cell_a_max_epoch = df[df['Cell ID'] == 'A']['Max Epoch'].iloc[0]
    cell_b_max_epoch = df[df['Cell ID'] == 'B']['Max Epoch'].iloc[0]
    assert cell_a_max_epoch == 2, f"Expected max epoch 2 for cell A, got {cell_a_max_epoch}"
    assert cell_b_max_epoch == 3, f"Expected max epoch 3 for cell B, got {cell_b_max_epoch}"
    
    # Check filtered results
    filtered_cell_ids = df_filtered['Cell ID'].tolist()
    filtered_epochs = df_filtered['Epoch'].tolist()
    filtered_values = df_filtered['Value'].tolist()
    
    assert filtered_cell_ids == ['A', 'B'], f"Expected cell IDs ['A', 'B'], got {filtered_cell_ids}"
    assert filtered_epochs == [2, 3], f"Expected epochs [2, 3], got {filtered_epochs}"
    assert filtered_values == [30, 25], f"Expected values [30, 25], got {filtered_values}"
    
    # Test that the filtered rows have the correct Max Epoch values
    for _, row in df_filtered.iterrows():
        assert row['Epoch'] == row['Max Epoch'], f"Epoch {row['Epoch']} should equal Max Epoch {row['Max Epoch']}"
    
    print("✅ All DataFrame operations assertions passed!")


def test_copy_operation():
    """Test that .copy() operation works correctly to avoid SettingWithCopyWarning."""
    # Create original DataFrame
    original_data = {
        'Cell ID': ['A', 'A', 'B', 'B'],
        'Condition': ['Control', 'Control', 'Control', 'Control'],
        'Epoch': [0, 1, 0, 1],
        'Value': [10, 20, 30, 40]
    }
    df_original = pd.DataFrame(original_data)
    
    # Create a slice (this would normally cause SettingWithCopyWarning)
    df_slice = df_original[df_original['Condition'] == 'Control']
    
    # Create a copy (this should avoid the warning)
    df_copy = df_original[df_original['Condition'] == 'Control'].copy()
    
    # Modify the copy
    df_copy['New Column'] = 'test'
    
    # Assertions
    assert len(df_slice) == 4, f"Expected 4 rows in slice, got {len(df_slice)}"
    assert len(df_copy) == 4, f"Expected 4 rows in copy, got {len(df_copy)}"
    assert 'New Column' in df_copy.columns, "New Column should be added to copy"
    assert 'New Column' not in df_original.columns, "Original DataFrame should not be modified"
    assert 'New Column' not in df_slice.columns, "Slice should not be modified"
    
    # Check that original data is preserved
    assert len(df_original) == 4, f"Original DataFrame should still have 4 rows, got {len(df_original)}"
    assert 'New Column' not in df_original.columns, "Original DataFrame should not have New Column"
    
    print("✅ All copy operation assertions passed!")


if __name__ == '__main__':
    print("Running colin_stats tests...")
    print("=" * 50)
    
    print("\n1. Testing FileInfo usage in colin_stats:")
    test_file_info_usage()
    
    print("\n2. Testing _removeOneSpikeControl logic:")
    test_remove_one_spike_control_logic()
    
    print("\n3. Testing DataFrame operations:")
    test_dataframe_operations()
    
    print("\n4. Testing copy operation:")
    test_copy_operation()
    
    print("\n🎉 All tests completed successfully!") 