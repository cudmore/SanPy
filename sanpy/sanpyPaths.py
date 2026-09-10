"""Centralized filesystem paths used by SanPy."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from platformdirs import user_documents_dir

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class SanPyPaths:
    """Build and initialize SanPy's bundled and user-visible paths.

    Args:
        documents_dir: Optional Documents directory override. Tests use this
            to keep filesystem operations out of the real user directory.
        bundled_dir: Optional bundled-resource directory override.
    """

    def __init__(
        self,
        documents_dir: Path | str | None = None,
        bundled_dir: Path | str | None = None,
    ) -> None:
        self._documents_dir = Path(documents_dir or user_documents_dir())
        self._bundled_dir = (
            Path(bundled_dir) if bundled_dir is not None else self._default_bundled_dir()
        )

    @staticmethod
    def _default_bundled_dir() -> Path:
        """Return the source package or frozen-application resource directory.

        Returns:
            Directory containing SanPy's bundled resources.
        """
        if getattr(sys, "frozen", False):
            return Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return Path(__file__).resolve().parent

    @property
    def bundled_dir(self) -> Path:
        """Return the directory containing bundled SanPy resources."""
        return self._bundled_dir

    @property
    def bundled_user_files_dir(self) -> Path:
        """Return the bundled first-run user-files template directory."""
        return self.bundled_dir / "_userFiles" / "SanPy-User-Files"

    @property
    def user_documents_dir(self) -> Path:
        """Return the platform-specific Documents directory."""
        return self._documents_dir

    @property
    def user_files_dir(self) -> Path:
        """Return the user-visible SanPy files directory."""
        return self.user_documents_dir / "SanPy-User-Files"

    @property
    def preferences_dir(self) -> Path:
        """Return the directory containing SanPy preferences."""
        return self.user_files_dir / "preferences"

    @property
    def detection_dir(self) -> Path:
        """Return the directory containing user detection presets."""
        return self.user_files_dir / "detection"

    @property
    def example_data_dir(self) -> Path:
        """Return the directory containing bundled example recordings."""
        return self.user_files_dir / "exampleData"

    @property
    def plugin_dir(self) -> Path:
        """Return the disabled external-plugin directory."""
        return self.user_files_dir / "plugins"

    @property
    def analysis_dir(self) -> Path:
        """Return the disabled external-analysis directory."""
        return self.user_files_dir / "analysis"

    @property
    def file_loader_dir(self) -> Path:
        """Return the disabled external file-loader directory."""
        return self.user_files_dir / "file loaders"

    def ensure_user_files(self) -> bool:
        """Copy the bundled user-files template on first launch.

        Returns:
            True when the directory was created, otherwise False.
        """
        if self.user_files_dir.is_dir():
            return False

        logger.info('Creating SanPy user files at "%s"', self.user_files_dir)
        try:
            # A platform Documents location may not exist in a minimal account.
            self.user_documents_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(self.bundled_user_files_dir, self.user_files_dir)
        except OSError:
            logger.exception(
                'Could not create SanPy user files at "%s"', self.user_files_dir
            )
            return False
        return True
