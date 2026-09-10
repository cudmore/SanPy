"""Tests for the default-off external user-code policy."""

import importlib
from pathlib import Path

import pytest

import sanpy
from sanpy.interface.bPlugins import bPlugins


def test_external_plugin_files_are_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Ignore Python plugins found in the user folder by default.

    Args:
        monkeypatch: Pytest fixture used to enforce the default-off policy.
        tmp_path: Temporary directory containing an external plugin.
    """
    (tmp_path / "externalPlugin.py").write_text(
        "class externalPlugin:\n"
        "    myHumanName = 'External Plugin'\n"
        "    showInMenu = True\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sanpy._util, "ALLOW_USER_CODE_IMPORTS", False)
    manager = bPlugins.__new__(bPlugins)
    manager._sanpyApp = None
    manager.userPluginFolder = str(tmp_path)
    manager.pluginDict = {}
    manager._openSet = set()

    manager.loadPlugins()

    assert "External Plugin" not in manager.pluginDict
    assert manager.pluginList()


def test_external_file_loaders_are_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Do not execute Python file loaders found in the user folder.

    Args:
        monkeypatch: Pytest fixture used to observe module loading.
        tmp_path: Temporary directory representing external file loaders.
    """
    loader_module = importlib.import_module("sanpy.fileloaders.fileLoader_base")
    attempted_imports: list[tuple[str, str]] = []
    (tmp_path / "externalLoader.py").write_text("raise RuntimeError\n")
    monkeypatch.setattr(sanpy._util, "ALLOW_USER_CODE_IMPORTS", False)
    monkeypatch.setattr(
        sanpy._util,
        "_module_from_file",
        lambda module_name, file_path: attempted_imports.append(
            (module_name, file_path)
        ),
    )

    loaders = loader_module.getFileLoaders()

    assert attempted_imports == []
    assert ".abf" in loaders


def test_external_analysis_files_are_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Do not execute Python analyses found in the user folder.

    Args:
        monkeypatch: Pytest fixture used to observe module loading.
        tmp_path: Temporary directory representing external analyses.
    """
    analysis_module = importlib.import_module(
        "sanpy.user_analysis.baseUserAnalysis"
    )
    attempted_imports: list[tuple[str, str]] = []
    (tmp_path / "externalAnalysis.py").write_text("raise RuntimeError\n")
    monkeypatch.setattr(sanpy._util, "ALLOW_USER_CODE_IMPORTS", False)
    monkeypatch.setattr(
        analysis_module,
        "_module_from_file",
        lambda module_name, file_path: attempted_imports.append(
            (module_name, file_path)
        ),
    )

    analysis_module._getObjectList()

    assert attempted_imports == []


def test_user_file_template_contains_no_python_extensions() -> None:
    """Keep executable extension directories out of new user folders."""
    template = (
        Path(__file__).resolve().parents[1]
        / "sanpy"
        / "_userFiles"
        / "SanPy-User-Files"
    )

    assert not (template / "plugins").exists()
    assert not (template / "analysis").exists()
    assert not (template / "file loaders").exists()
