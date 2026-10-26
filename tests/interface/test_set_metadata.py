"""Tests for experimental-metadata edits shared by the plugin and file table."""

from pathlib import Path
from typing import Any

import pytest
from qtpy import QtCore, QtWidgets

import sanpy
from sanpy.interface.plugins.setMetaData import SetMetaData
from sanpy.interface.sanpy_window import _SelectedFileProgressDialog


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
    monkeypatch: pytest.MonkeyPatch,
    qapp: Any,
    qtbot: Any,
    tmp_path: Path,
) -> None:
    """Keep the plugin, analysis metadata, and file table on one value.

    Args:
        monkeypatch: Pytest fixture used to suppress preference writes and save prompts.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
        tmp_path: Temporary directory supplied by pytest.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    filename = "2021_07_20_0010.abf"
    (tmp_path / filename).write_bytes((data_path / filename).read_bytes())
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(tmp_path))
    assert window is not None
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "prepareToClose", lambda: True)
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


def test_metadata_edit_confirms_and_updates_multi_selection(
    monkeypatch: pytest.MonkeyPatch,
    qapp: Any,
    qtbot: Any,
    tmp_path: Path,
) -> None:
    """Apply one confirmed metadata value to every selected recording.

    Args:
        monkeypatch: Pytest fixture used to accept confirmation and suppress saves.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
        tmp_path: Temporary directory supplied by pytest.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    filenames = ("2021_07_20_0010.abf", "19114001.abf")
    for filename in filenames:
        (tmp_path / filename).write_bytes((data_path / filename).read_bytes())
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)

    def accept_question(*args: object, **kwargs: object) -> int:
        """Accept the batch metadata confirmation.

        Args:
            *args: Positional message-box arguments.
            **kwargs: Keyword message-box arguments.

        Returns:
            Qt's affirmative message-box result.
        """
        del args, kwargs
        return int(QtWidgets.QMessageBox.Yes)

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        accept_question,
    )
    window = qapp.openSanPyWindow(str(tmp_path))
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "prepareToClose", lambda: True)
    table = window._fileListWidget.getTableView()
    model = table.model()
    selection = table.selectionModel()
    selection.clearSelection()
    row_flag = QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows
    visual_rows: list[int] = []
    for filename in filenames:
        row_label = window.myAnalysisDir.findFileRow(filename)
        visual_row = list(model._data.index).index(row_label)
        visual_rows.append(visual_row)
        selection.select(model.index(visual_row, 0), row_flag)
    selected_keys = window.selected_file_keys
    expected_keys = tuple(
        window.myAnalysisDir.get_file_key(model._data.index[row])
        for row in sorted(visual_rows)
    )
    assert selected_keys == expected_keys
    plugin = window.runPlugin("Set Meta Data", window.get_bAnalysis(), show=False)
    assert isinstance(plugin, SetMetaData)
    qtbot.addWidget(plugin)

    plugin._on_combo_box("condition", "drug")

    for file_key in selected_keys:
        analysis = window.myAnalysisDir.get_analysis_for_file_key(file_key)
        assert analysis is not None
        assert analysis.metaData.getMetaData("condition") == "drug"
        assert analysis.isDirty()


def test_selected_file_progress_dialog_stops_after_cancel(qtbot: Any) -> None:
    """Count only files accepted before Cancel and then close the dialog.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    parent = QtWidgets.QWidget()
    qtbot.addWidget(parent)
    dialog = _SelectedFileProgressDialog(parent, 2, "Updating")
    qtbot.addWidget(dialog)

    assert dialog.should_continue(1, 2, "first.abf") is True
    assert dialog.labelText() == 'Updating file 1 of 2: "first.abf"'
    dialog.advance()
    assert dialog.value() == 1
    assert dialog.accepted_count == 1
    dialog.cancel()
    assert dialog.should_continue(2, 2, "second.abf") is False
    assert dialog.accepted_count == 1
    dialog.finish()
    assert dialog.isVisible() is False


@pytest.mark.parametrize("key_press", [QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab])
def test_metadata_tab_commits_without_opening_the_next_field(
    monkeypatch: pytest.MonkeyPatch,
    qapp: Any,
    qtbot: Any,
    tmp_path: Path,
    key_press: QtCore.Qt.Key,
) -> None:
    """Store the current metadata field when Tab is pressed without focusing another.

    Args:
        monkeypatch: Pytest fixture used to record metadata requests and suppress saves.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
        tmp_path: Temporary directory supplied by pytest.
        key_press: Tab or Shift+Tab key delivered to the editor.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    filename = "2021_07_20_0010.abf"
    (tmp_path / filename).write_bytes((data_path / filename).read_bytes())
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(tmp_path))
    assert window is not None
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "prepareToClose", lambda: True)
    window._fileListWidget.getTableView().selectRowByFile(filename)
    analysis = window.get_bAnalysis()
    assert analysis is not None
    plugin = window.runPlugin("Set Meta Data", analysis, show=True)
    assert isinstance(plugin, SetMetaData)
    qtbot.addWidget(plugin)
    qtbot.waitExposed(plugin)
    note = plugin._widgetDict["note"]
    assert isinstance(note, QtWidgets.QLineEdit)
    stored: list[tuple[str, str]] = []
    original = window.request_set_metadata

    def record_request(key: str, value: str) -> bool:
        """Record one metadata request and perform it.

        Args:
            key: Canonical experimental-metadata key.
            value: Proposed string value.

        Returns:
            Result of the original metadata request.
        """
        stored.append((key, value))
        return original(key, value)

    monkeypatch.setattr(window, "request_set_metadata", record_request)
    note.setFocus(QtCore.Qt.OtherFocusReason)
    qtbot.waitUntil(lambda: note.hasFocus())
    note.setText("alpha")
    stored.clear()
    qtbot.keyClick(note, key_press)

    assert stored == [("note", "alpha")]
    assert analysis.metaData.getMetaData("note") == "alpha"
    assert note.hasFocus() is False
    assert not any(
        widget.hasFocus()
        for widget in plugin._widgetDict.values()
        if isinstance(widget, QtWidgets.QLineEdit)
    )
