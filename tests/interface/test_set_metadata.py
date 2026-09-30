"""Tests for experimental-metadata edits shared by the plugin and file table."""

from pathlib import Path
from typing import Any

import pytest
from qtpy import QtCore, QtWidgets

import sanpy
from sanpy.interface.plugins.setMetaData import SetMetaData


def _display_value(model: Any, row_label: object, column_name: str) -> object:
    """Return one file-table display value.

    Args:
        model: File-table model backed by an analysis directory.
        row_label: Dataframe index label of the recording row.
        column_name: Column to read.

    Returns:
        Value reported for the display role.
    """
    visual_row = list(model._data.index).index(row_label)
    column = list(model._data.columns).index(column_name)
    return model.data(model.index(visual_row, column))


def test_set_metadata_shows_sweep_condition_editors(qtbot: Any) -> None:
    """Show one sweep-condition editor for each sweep on the selected recording.

    Args:
        qtbot: Pytest-qt widget manager.
    """
    analysis = sanpy.bAnalysis("tests/data/2021_07_20_0010.abf")
    plugin = SetMetaData(ba=analysis)
    qtbot.addWidget(plugin)

    assert list(plugin._sweepConditionEdits) == list(analysis.fileLoader.sweepList)


def test_metadata_editors_update_the_same_analysis(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Keep the plugin, analysis metadata, and file table on one value.

    Args:
        monkeypatch: Pytest fixture used to suppress preference writes and save prompts.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    folder = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(folder))
    assert window is not None
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "prepareToClose", lambda: True)

    filename = "2021_07_20_0010.abf"
    window._fileListWidget.getTableView().selectRowByFile(filename)
    analysis = window.get_bAnalysis()
    assert analysis is not None
    assert analysis.getFileName() == filename
    row_label = window.myAnalysisDir.findFileRow(filename)

    plugin = window.runPlugin("Set Meta Data", analysis, show=False)
    assert isinstance(plugin, SetMetaData)
    qtbot.addWidget(plugin)

    note = plugin._widgetDict["note"]
    assert isinstance(note, QtWidgets.QLineEdit)
    note.setText("alpha;beta")
    plugin._on_text_edit(note, "note")

    assert analysis.metaData.getMetaData("note") == "alpha,beta"
    assert note.text() == "alpha,beta"
    assert _display_value(window.myModel, row_label, "note") == "alpha,beta"

    visual_row = list(window.myModel._data.index).index(row_label)
    note_column = list(window.myModel._data.columns).index("note")
    edited = window.myModel.setData(
        window.myModel.index(visual_row, note_column), "gamma"
    )
    assert edited is True
    assert analysis.metaData.getMetaData("note") == "gamma"
    assert note.text() == "gamma"
    assert _display_value(window.myModel, row_label, "note") == "gamma"

    include = plugin._widgetDict["include"]
    assert isinstance(include, QtWidgets.QComboBox)
    plugin._on_combo_box("include", "no")
    assert analysis.metaData.getMetaData("include") == "no"
    assert include.currentData() == "no"
    assert window.myAnalysisDir.columnIsEditable("include") is False
    assert _display_value(window.myModel, row_label, "include") == "no"
    include_column = list(window.myModel._data.columns).index("include")
    assert (
        window.myModel.headerData(
            include_column, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole
        )
        == "Include"
    )
    assert (
        window.myModel.headerData(
            note_column, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole
        )
        == "Note"
    )
