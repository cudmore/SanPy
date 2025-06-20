# Colin Module Tests

This directory contains tests for the colin-related modules in the `simple_scatter` package.

## Test Files

### `test_colin_global.py`
Tests for the `colin_global` module, including:
- **FileInfo dataclass**: Tests the parsing of file paths like "20250602 ISAN R3 LS3 Control Epoch 1.tif"
- **iterate_unique_cell_rows function**: Tests the iterator that returns unique rows from a DataFrame for a given cellID
- **Edge cases**: Tests error handling for malformed file paths

### `test_colin_stats.py`
Tests for the `colin_stats` module, including:
- **FileInfo integration**: Tests that FileInfo works correctly within colin_stats
- **_removeOneSpikeControl logic**: Tests the logic for filtering control cells with low spike counts
- **DataFrame operations**: Tests various pandas operations used in the module

## Running Tests

### Individual Test Files
```bash
# Run colin_global tests
python sanpy/kym/tests/test_colin_global.py

# Run colin_stats tests
python sanpy/kym/tests/test_colin_stats.py
```

### All Tests
```bash
# Run all colin-related tests
python sanpy/kym/tests/run_all_tests.py
```

## Test Structure

Each test file follows this structure:
1. **Setup**: Import necessary modules and set up test data
2. **Test Functions**: Individual test functions for specific functionality
3. **Main Runner**: A main section that runs all tests when the file is executed directly

## What Was Tested Today

### FileInfo Dataclass
- Parsing of file paths with different conditions (Control, Ivab, Thap)
- Extraction of cellID, epoch, date, region, and condition
- Handling of files with and without epochs
- Error handling for malformed paths

### Iterator Function
- Returning unique rows for a given cellID
- Handling duplicate rows correctly
- Working with non-existent cellIDs
- Integration with list comprehensions

### DataFrame Operations
- Groupby and transform operations
- Filtering by conditions
- Avoiding SettingWithCopyWarning with `.copy()`

## Notes

- Tests are designed to be run independently
- Each test function includes detailed output for debugging
- The test runner provides a summary of all test results
- Tests use sample data that mimics the real data structure 