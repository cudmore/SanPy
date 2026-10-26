"""Tests for file-table column visibility."""

import shutil
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pandas as pd
import pytest
from PyQt5 import QtWidgets

import sanpy
from sanpy.interface.bFileTable import pandasModel
from sanpy.interface.bTableView import (
    DEFAULT_HIDDEN_FILE_COLUMNS,
    REQUIRED_FILE_COLUMNS,
    bTableView,
    hidden_file_column_keys,
)
from sanpy.interface.sanpy_app import SanPyApp

_RECORDING = Path(__file__).resolve().parents[1] / "data" / "2021_07_20_0010.abf"


def test_hidden_file_column_keys_drop_unknown_and_required_keys() -> None:
    """Keep only known optional columns from a saved hidden-column list."""
    hidden = hidden_file_column_keys(
        ["species", "not_a_column", "File", 3, "age", "age"],
        sanpy.analysisDir.sanpyColumns.keys(),
    )

    assert hidden == ["species", "age"]


def test_missing_hidden_file_column_value_uses_the_default() -> None:
    """Use the default hidden columns when no list has been saved."""
    hidden = hidden_file_column_keys(None, sanpy.analysisDir.sanpyColumns.keys())

    assert hidden == list(DEFAULT_HIDDEN_FILE_COLUMNS)


def test_empty_hidden_file_column_list_hides_nothing() -> None:
    """Treat an empty list as a request to show every optional column."""
    hidden = hidden_file_column_keys([], sanpy.analysisDir.sanpyColumns.keys())

    assert hidden == []


def _file_table(
    qtbot: Any, tmp_path: Path
) -> tuple[bTableView, pandasModel, list[str]]:
    """Create a file table for one recording.

    Args:
        qtbot: Pytest-qt bot that owns the widget.
        tmp_path: Temporary directory supplied by pytest.

    Returns:
        The table view, its model, and the column keys in table order.
    """
    shutil.copy2(_RECORDING, tmp_path / "recording.abf")
    table = sanpy.analysisDir(path=str(tmp_path), autoLoad=False, folderDepth=1)
    columns = [str(column) for column in table.columns]
    model = pandasModel(table)
    view = bTableView(model)
    qtbot.addWidget(view)
    return view, model, columns


@pytest.fixture
def restored_hidden_columns(qapp: SanPyApp):
    """Restore file-table visibility after a test mutates the session preferences.

    Args:
        qapp: Session SanPy application.

    Yields:
        Nothing. The fixture restores the hidden-column list on teardown.
    """
    file_list = qapp.getConfigDict().configDict["fileList"]
    original = list(file_list["hiddenColumns"])
    yield
    file_list["hiddenColumns"] = original


def test_file_table_applies_the_default_hidden_columns(
    qtbot: Any, tmp_path: Path
) -> None:
    """Hide the default optional columns and keep the required columns visible.

    Args:
        qtbot: Pytest-qt bot that owns the widget.
        tmp_path: Temporary directory supplied by pytest.
    """
    view, _model, columns = _file_table(qtbot, tmp_path)

    for column_name in DEFAULT_HIDDEN_FILE_COLUMNS:
        assert view.isColumnHidden(columns.index(column_name))
    for column_name in REQUIRED_FILE_COLUMNS:
        assert not view.isColumnHidden(columns.index(column_name))
    for column_name in ("Dur(s)", "include", "parent1"):
        assert not view.isColumnHidden(columns.index(column_name))


def test_column_menu_checks_visible_optional_columns(
    qtbot: Any, tmp_path: Path
) -> None:
    """Offer every optional column, checked when it is visible.

    Args:
        qtbot: Pytest-qt bot that owns the widget.
        tmp_path: Temporary directory supplied by pytest.
    """
    view, _model, _columns = _file_table(qtbot, tmp_path)
    menu = QtWidgets.QMenu()
    qtbot.addWidget(menu)
    actions = view._add_column_visibility_actions(menu)

    labels = [action.text() for action, _column_key in actions]
    assert "Animal ID" in labels
    assert "File" not in labels
    assert "L" not in labels
    animal_id = next(action for action, key in actions if key == "animal_id")
    duration = next(action for action, key in actions if key == "Dur(s)")
    assert not animal_id.isChecked()
    assert duration.isChecked()


def test_column_toggle_updates_memory_without_saving(
    qtbot: Any,
    qapp: SanPyApp,
    restored_hidden_columns: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Change visibility in memory and leave the preferences file untouched.

    Args:
        qtbot: Pytest-qt bot that owns the widget.
        qapp: Session SanPy application.
        restored_hidden_columns: Fixture that restores the hidden-column list.
        monkeypatch: Pytest fixture used to observe preference saves.
        tmp_path: Temporary directory supplied by pytest.
    """
    del restored_hidden_columns
    view, model, columns = _file_table(qtbot, tmp_path)
    save = Mock()
    monkeypatch.setattr(qapp.getConfigDict(), "save", save)

    view._set_column_hidden("Dur(s)", True)

    assert view.isColumnHidden(columns.index("Dur(s)"))
    assert "Dur(s)" in qapp.getConfigDict().configDict["fileList"]["hiddenColumns"]
    save.assert_not_called()

    captured: list[list[str]] = []

    def capture(frame: pd.DataFrame, sep: str = "\t", index: bool = True) -> None:
        """Record columns copied to the clipboard.

        Args:
            frame: Dataframe being copied.
            sep: Unused clipboard separator.
            index: Unused index flag.
        """
        del sep, index
        captured.append([str(column) for column in frame.columns])

    monkeypatch.setattr(pd.DataFrame, "to_clipboard", capture)
    model.myCopyTable()

    assert "Dur(s)" in captured[0]
    assert "animal_id" in captured[0]


def test_column_toggle_refreshes_every_open_file_table(
    qtbot: Any,
    qapp: SanPyApp,
    restored_hidden_columns: None,
    tmp_path: Path,
) -> None:
    """Apply one visibility change to every open file table.

    Args:
        qtbot: Pytest-qt bot that owns the widgets.
        qapp: Session SanPy application.
        restored_hidden_columns: Fixture that restores the hidden-column list.
        tmp_path: Temporary directory supplied by pytest.
    """
    del restored_hidden_columns
    view, _model, columns = _file_table(qtbot, tmp_path)
    other, _other_model, _other_columns = _file_table(qtbot, tmp_path)
    holder = type("Holder", (), {})()
    holder._fileListWidget = type("Files", (), {"getTableView": lambda self: other})()
    original_windows = list(qapp._windowList)
    qapp._windowList = [holder]
    try:
        view._set_column_hidden("Sweeps", True)
        assert view.isColumnHidden(columns.index("Sweeps"))
        assert other.isColumnHidden(columns.index("Sweeps"))
    finally:
        qapp._windowList = original_windows
