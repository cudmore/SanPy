"""Shared pytest fixtures for SanPy backend and interface tests."""

import importlib.util
from pathlib import Path

import pytest

collect_ignore: list[str] = (
    ["interface"] if importlib.util.find_spec("qtpy") is None else []
)


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return the stable test-only data directory.

    Returns:
        Absolute path to ``tests/data``.
    """
    return Path(__file__).resolve().parent / "data"
