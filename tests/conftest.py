"""Shared pytest configuration for SanPy tests."""

import pytest

from sanpy.interface.sanpy_app import SanPyApp
from sanpy.sanpyPaths import SanPyPaths


@pytest.fixture(scope="session")
def qapp_cls(tmp_path_factory: pytest.TempPathFactory) -> type[SanPyApp]:
    """Use an isolated SanPy application for every pytest-qt test.

    Args:
        tmp_path_factory: Session-scoped temporary-directory factory.

    Returns:
        SanPy application class configured with a temporary Documents folder.
    """
    documents_dir = tmp_path_factory.mktemp("sanpy-documents")

    class _TestSanPyApp(SanPyApp):
        """SanPy application that cannot access the real user Documents folder."""

        def __init__(self, argv: list[str]) -> None:
            """Initialize with isolated filesystem paths.

            Args:
                argv: Command-line arguments passed to Qt.
            """
            super().__init__(argv, SanPyPaths(documents_dir=documents_dir))

    return _TestSanPyApp
