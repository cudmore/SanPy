"""Shared pytest configuration for SanPy tests."""

from collections.abc import Callable

import pytest

from sanpy.interface.sanpy_app import SanPyApp


@pytest.fixture(scope="session")
def qapp_cls() -> Callable[..., SanPyApp]:
    """Use the SanPy application subclass for every pytest-qt test.

    Returns:
        The application class constructed by pytest-qt.
    """
    return SanPyApp
