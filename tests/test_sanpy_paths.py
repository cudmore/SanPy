"""Tests for centralized SanPy filesystem paths."""

from pathlib import Path
from typing import Any

import pytest

from sanpy.sanpyPaths import SanPyPaths


def _make_template(bundled_dir: Path) -> Path:
    """Create a minimal bundled user-files template.

    Args:
        bundled_dir: Temporary bundled-resource directory.

    Returns:
        Created template directory.
    """
    template_dir = bundled_dir / "_userFiles" / "SanPy-User-Files"
    template_dir.mkdir(parents=True)
    (template_dir / "preferences").mkdir()
    return template_dir


def test_paths_derive_from_injected_roots(tmp_path: Path) -> None:
    """Build every path from explicit Documents and bundle roots.

    Args:
        tmp_path: Temporary root supplied by pytest.
    """
    documents_dir = tmp_path / "Documents"
    bundled_dir = tmp_path / "bundle"
    sanpy_paths = SanPyPaths(documents_dir=documents_dir, bundled_dir=bundled_dir)

    assert sanpy_paths.user_documents_dir == documents_dir
    assert sanpy_paths.user_files_dir == documents_dir / "SanPy-User-Files"
    assert sanpy_paths.preferences_dir == sanpy_paths.user_files_dir / "preferences"
    assert sanpy_paths.detection_dir == sanpy_paths.user_files_dir / "detection"
    assert sanpy_paths.example_data_dir == sanpy_paths.user_files_dir / "example-data"
    assert sanpy_paths.bundled_dir == bundled_dir


def test_ensure_user_files_copies_template_once(tmp_path: Path) -> None:
    """Copy the template only when the user-files directory is absent.

    Args:
        tmp_path: Temporary root supplied by pytest.
    """
    bundled_dir = tmp_path / "bundle"
    _make_template(bundled_dir)
    sanpy_paths = SanPyPaths(
        documents_dir=tmp_path / "Documents", bundled_dir=bundled_dir
    )

    assert sanpy_paths.ensure_user_files() is True
    assert sanpy_paths.preferences_dir.is_dir()
    assert sanpy_paths.ensure_user_files() is False


def test_ensure_user_files_logs_copy_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Return safely when the bundled template cannot be copied.

    Args:
        monkeypatch: Pytest fixture used to intercept error logging.
        tmp_path: Temporary root supplied by pytest.
    """
    sanpy_paths = SanPyPaths(
        documents_dir=tmp_path / "Documents", bundled_dir=tmp_path / "missing"
    )
    logged: list[str] = []

    def _record_error(message: str, path: Any) -> None:
        """Record an expected filesystem error.

        Args:
            message: Logger format string.
            path: Path supplied to the logger.
        """
        del path
        logged.append(message)

    monkeypatch.setattr("sanpy.sanpyPaths.logger.exception", _record_error)

    assert sanpy_paths.ensure_user_files() is False
    assert logged
    assert not sanpy_paths.user_files_dir.exists()
