import logging
import os
from pathlib import Path

import pytest
from qtpy import QtCore, QtWidgets

from sanpy.interface import sanpy_app
from sanpy import sanpyLogger
from sanpy.sanpyPaths import SanPyPaths


def test_logger_text_combines_retained_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Read the rotated backup before the active SanPy log.

    Args:
        monkeypatch: Pytest fixture used to replace the configured log path.
        tmp_path: Temporary directory supplied by pytest.
    """
    log_path = tmp_path / "sanpy.log"
    backup_path = tmp_path / "sanpy.log.1"
    backup_path.write_text("old line\n", encoding="utf-8")
    log_path.write_text("new line\n", encoding="utf-8")
    monkeypatch.setattr(sanpyLogger, "getLoggerFile", lambda: str(log_path))

    assert sanpyLogger.getLoggerText() == "old line\nnew line\n"


def test_logger_text_handles_missing_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Return a useful diagnostic when no retained log exists.

    Args:
        monkeypatch: Pytest fixture used to replace the configured log path.
        tmp_path: Temporary directory supplied by pytest.
    """
    log_path = tmp_path / "sanpy.log"
    monkeypatch.setattr(sanpyLogger, "getLoggerFile", lambda: str(log_path))

    log_text = sanpyLogger.getLoggerText()

    assert log_text.startswith("Log file unavailable: no log files found")


def test_logger_text_handles_unreadable_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Return a diagnostic instead of raising when a log cannot be read.

    Args:
        monkeypatch: Pytest fixture used to replace the configured log path.
        tmp_path: Temporary directory supplied by pytest.
    """
    log_path = tmp_path / "sanpy.log"
    log_path.mkdir()
    monkeypatch.setattr(sanpyLogger, "getLoggerFile", lambda: str(log_path))

    log_text = sanpyLogger.getLoggerText()

    assert log_text.startswith("Log file unavailable:")
    assert str(log_path) in log_text


def test_clipboard_info_uses_all_retained_log_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Append retained log text after the clipboard separator.

    Args:
        monkeypatch: Pytest fixture used to isolate build and log text.
    """
    monkeypatch.setattr(
        sanpy_app.build_info, "get_build_info_json", lambda: '{"build": "info"}'
    )
    monkeypatch.setattr(sanpy_app, "getLoggerText", lambda: "old\nnew\n")

    assert sanpy_app._getSanPyInfoForClipboard() == (
        '{"build": "info"}\n\n=== log file ===\nold\nnew\n'
    )


def test_open_user_files_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Ask Qt to open the configured SanPy user-files directory.

    Args:
        monkeypatch: Pytest fixture used to isolate folder-opening services.
        tmp_path: Existing temporary directory supplied by pytest.
    """
    opened_urls: list[QtCore.QUrl] = []
    sanpy_paths = SanPyPaths(documents_dir=tmp_path)
    sanpy_paths.user_files_dir.mkdir()
    monkeypatch.setattr(
        sanpy_app.QtGui.QDesktopServices,
        "openUrl",
        lambda url: opened_urls.append(url) or True,
    )

    assert sanpy_app._openSanPyUserFilesFolder(sanpy_paths=sanpy_paths) is True
    assert len(opened_urls) == 1
    assert opened_urls[0].toLocalFile() == str(sanpy_paths.user_files_dir)


def test_open_user_files_folder_warns_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Warn instead of raising when the user-files folder is missing.

    Args:
        monkeypatch: Pytest fixture used to isolate folder-opening services.
        tmp_path: Temporary directory supplied by pytest.
    """
    sanpy_paths = SanPyPaths(documents_dir=tmp_path)
    missing_path = sanpy_paths.user_files_dir
    warnings: list[tuple[QtWidgets.QWidget | None, str, str]] = []
    monkeypatch.setattr(
        sanpy_app.QtWidgets.QMessageBox,
        "warning",
        lambda parent, title, message: warnings.append((parent, title, message)),
    )

    assert sanpy_app._openSanPyUserFilesFolder(sanpy_paths=sanpy_paths) is False
    assert warnings == [
        (
            None,
            "SanPy-User-Files",
            f"SanPy-User-Files folder was not found:\n{missing_path}",
        )
    ]


def test_open_user_files_folder_warns_when_launch_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Warn instead of raising when Qt cannot open an existing folder.

    Args:
        monkeypatch: Pytest fixture used to isolate folder-opening services.
        tmp_path: Existing temporary directory supplied by pytest.
    """
    warnings: list[tuple[QtWidgets.QWidget | None, str, str]] = []
    sanpy_paths = SanPyPaths(documents_dir=tmp_path)
    sanpy_paths.user_files_dir.mkdir()
    monkeypatch.setattr(
        sanpy_app.QtGui.QDesktopServices, "openUrl", lambda _url: False
    )
    monkeypatch.setattr(
        sanpy_app.QtWidgets.QMessageBox,
        "warning",
        lambda parent, title, message: warnings.append((parent, title, message)),
    )

    assert sanpy_app._openSanPyUserFilesFolder(sanpy_paths=sanpy_paths) is False
    assert warnings == [
        (
            None,
            "SanPy-User-Files",
            f"Could not open SanPy-User-Files folder:\n{sanpy_paths.user_files_dir}",
        )
    ]


def test_frozen_app_uses_persistent_matplotlib_cache(monkeypatch, tmp_path):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(sanpy_app.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        sanpy_app, "user_cache_dir", lambda *args, **kwargs: str(cache_dir)
    )

    sanpy_app._configure_matplotlib_cache()

    assert os.environ["MPLCONFIGDIR"] == str(cache_dir / "matplotlib")
    assert (cache_dir / "matplotlib").is_dir()


def test_matplotlib_cache_failure_keeps_existing_config(monkeypatch):
    existing_config = "pyinstaller-temporary-config"
    monkeypatch.setattr(sanpy_app.sys, "frozen", True, raising=False)
    monkeypatch.setenv("MPLCONFIGDIR", existing_config)
    monkeypatch.setattr(
        sanpy_app,
        "user_cache_dir",
        lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("denied")),
    )

    sanpy_app._configure_matplotlib_cache()

    assert os.environ["MPLCONFIGDIR"] == existing_config


def test_logger_uses_console_when_log_file_is_unavailable(monkeypatch):
    logger_name = "sanpy.tests.unavailable_file_logger"
    monkeypatch.setattr(
        sanpyLogger,
        "getLoggerFile",
        lambda: (_ for _ in ()).throw(PermissionError("denied")),
    )

    logger = sanpyLogger.get_logger(logger_name)

    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)

    logger.handlers.clear()
    logging.Logger.manager.loggerDict.pop(logger_name, None)
