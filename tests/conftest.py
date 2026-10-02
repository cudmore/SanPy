"""Shared pytest fixtures for SanPy backend and interface tests."""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return the stable test-only data directory.

    Returns:
        Absolute path to ``tests/data``.
    """
    return Path(__file__).resolve().parent / "data"
