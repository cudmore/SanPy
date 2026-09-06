"""Shared fixtures for SanPy Zarr export tests."""

from pathlib import Path

import pytest


@pytest.fixture
def small_abf() -> Path:
    """Return the repository's small multi-sweep, multi-channel ABF fixture.

    Returns:
        Absolute path to the ABF fixture.
    """
    return Path(__file__).parents[1] / "data" / "2021_07_20_0010.abf"
