"""Tests for discovery and isolation of external SanPy plugins."""

from pathlib import Path

import pytest

import sanpy
from sanpy.interface.bPlugins import bPlugins


def test_invalid_user_plugin_does_not_stop_discovery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log one invalid user plugin and continue loading valid plugins.

    Args:
        monkeypatch: Pytest fixture used to enable the isolated extension path.
        tmp_path: Temporary directory used as the external plugin folder.
        caplog: Pytest log-capture fixture.
    """
    monkeypatch.setattr(sanpy._util, "ALLOW_USER_CODE_IMPORTS", True)
    broken_path = tmp_path / "brokenPlugin.py"
    broken_path.write_text("import module_that_does_not_exist\n", encoding="utf-8")
    valid_path = tmp_path / "validPlugin.py"
    valid_path.write_text(
        "class validPlugin:\n"
        "    myHumanName = 'Valid User Plugin'\n"
        "    showInMenu = True\n",
        encoding="utf-8",
    )

    manager = bPlugins.__new__(bPlugins)
    manager._sanpyApp = None
    manager.userPluginFolder = str(tmp_path)
    manager.pluginDict = {}
    manager._openSet = set()

    with caplog.at_level("ERROR"):
        manager.loadPlugins()

    assert "Valid User Plugin" in manager.pluginDict
    assert "brokenPlugin" not in manager.pluginDict
    assert str(broken_path) in caplog.text
    assert "module_that_does_not_exist" in caplog.text
