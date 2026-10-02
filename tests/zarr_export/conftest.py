"""Shared fixtures for SanPy Zarr export tests."""

from pathlib import Path

import pytest


@pytest.fixture
def small_abf(test_data_dir: Path) -> Path:
    """Return the repository's small multi-sweep, multi-channel ABF fixture.

    Args:
        test_data_dir: Stable test-only data directory.

    Returns:
        Absolute path to the ABF fixture.
    """
    return test_data_dir / "2021_07_20_0010.abf"


@pytest.fixture
def sanpy_data_folder(test_data_dir: Path) -> Path:
    """Return the repository data folder with a saved SanPy-text analysis.

    Args:
        test_data_dir: Stable test-only data directory.

    Returns:
        Folder containing stochastic-hh.sanpy and its HDF5 catalog.
    """
    return test_data_dir / "persisted_analysis"
