import logging
import os

from sanpy.interface import sanpy_app
from sanpy import sanpyLogger


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
