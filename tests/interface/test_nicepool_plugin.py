"""Tests for the SanPy NicePool plugin's data and selection boundaries."""

from __future__ import annotations

import json
from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pandas as pd
import pytest
from PyQt5 import QtCore
from PyQt5.QtTest import QSignalSpy
from pytestqt.qtbot import QtBot

from sanpy.interface.plugins.nicepool_plugin import (
    NicePoolPlugin,
    _PRESET_FI_PLOT,
    _PRESET_SWEEP_PLOT,
    _preset_required_columns,
    prepare_nicepool_data,
    selection_to_spikes,
    selection_to_window_state,
)
from sanpy.interface.plugins.nicepool_pool_plugin import NicePoolPoolPlugin
from sanpy.interface.window_state import WindowState


def test_named_presets_are_dataset_aware_override_definitions() -> None:
    """Keep SanPy preset policy partial and leave complete state to NicePool."""
    assert _PRESET_FI_PLOT["name"] == "FI Plot"
    assert _PRESET_FI_PLOT["state"]["layout"] == "1x2"
    assert _PRESET_SWEEP_PLOT["name"] == "Sweep Plot"
    assert _PRESET_SWEEP_PLOT["state"]["layout"] == "1x2"
    for plot in _PRESET_FI_PLOT["state"]["plots"]:
        assert plot["groupColumn"] == "epochLevel"
        assert plot["yColumn"] == "spikeFreq_hz"
    for plot in _PRESET_SWEEP_PLOT["state"]["plots"]:
        assert plot["groupColumn"] == "sweep"
        assert plot["yColumn"] == "spikeFreq_hz"


def test_preset_required_columns_come_from_assigned_keys() -> None:
    """Collect only columns assigned in a named preset's plot slots."""
    assert _preset_required_columns(_PRESET_FI_PLOT) == {
        "epochLevel",
        "spikeFreq_hz",
    }
    assert _preset_required_columns(_PRESET_SWEEP_PLOT) == {"sweep", "spikeFreq_hz"}


def test_prepare_nicepool_data_projects_scalar_plot_columns() -> None:
    """Project registered plot results while excluding nested values."""
    source = pd.DataFrame(
        {
            "file": ["cell.abf"],
            "spikeNumber": [3],
            "sweep": [0],
            "epoch": [1],
            "epochLevel": [10.0],
            "include": ["yes"],
            "thresholdVal": [-42.5],
            "halfHeights": [[10, 50, 90]],
        }
    )

    projected, schema, prefilters = prepare_nicepool_data(source)

    assert projected.columns.tolist() == [
        "file",
        "include",
        "sweep",
        "epoch",
        "epochLevel",
        "spikeNumber",
        "thresholdVal",
    ]
    assert "halfHeights" not in projected.columns
    assert prefilters == ["sweep", "epoch", "include"]
    assert {entry["name"] for entry in schema} == set(projected.columns)
    schema_by_name = {entry["name"]: entry for entry in schema}
    assert schema_by_name["sweep"]["type"] == "number"
    assert schema_by_name["sweep"]["categorical"] is True
    assert schema_by_name["sweep"]["category"] == "acquisition"
    assert schema_by_name["sweep"]["axis_label"] == "Sweep"
    assert schema_by_name["epochLevel"]["type"] == "number"
    assert schema_by_name["epochLevel"]["categorical"] is True
    assert schema_by_name["epochLevel"]["category"] == "acquisition"
    assert schema_by_name["epochLevel"]["axis_label"] == "Epoch level"
    assert schema_by_name["file"]["category"] == "acquisition"
    assert schema_by_name["include"]["type"] == "string"
    assert schema_by_name["include"]["category"] == "metadata"
    assert schema_by_name["include"]["axis_label"] == "Include"


def test_prepare_nicepool_data_projects_experimental_metadata() -> None:
    """Offer every experimental-metadata column as a categorical metadata group."""
    source = pd.DataFrame(
        {
            "file": ["cell.abf"],
            "spikeNumber": [3],
            "include": ["no"],
            "sex": ["female"],
            "condition": ["control"],
            "cell_type": ["SAN"],
            "note": [""],
            "errors": [[{"Type": "t"}]],
        }
    )

    projected, schema, _prefilters = prepare_nicepool_data(source)

    assert projected.columns.tolist() == [
        "file",
        "include",
        "cell_type",
        "sex",
        "condition",
        "note",
        "spikeNumber",
    ]
    schema_by_name = {entry["name"]: entry for entry in schema}
    for name, label in (
        ("sex", "Sex"),
        ("condition", "Condition"),
        ("cell_type", "Cell Type"),
    ):
        assert schema_by_name[name] == {
            "name": name,
            "type": "string",
            "axis_label": label,
            "category": "metadata",
            "categorical": True,
        }


def _plugin_for_apply(keep_view: bool) -> NicePoolPlugin:
    """Build a single-file plugin ready to push one table to a mocked NicePool.

    Args:
        keep_view: Whether the next push should keep NicePool's current view.

    Returns:
        A plugin with a mocked NicePool widget and status label.
    """
    plugin = NicePoolPlugin.__new__(NicePoolPlugin)
    plugin._nicepool = MagicMock()
    plugin._status_label = MagicMock()
    plugin._keep_view_on_apply = keep_view
    plugin._highlight_spikes = None
    plugin._handling_nicepool_selection = False
    plugin._current_file_number = None
    plugin._row_id_to_file_key = {}
    plugin._selectedSpikeList = []
    window = SimpleNamespace(state=WindowState("cell.abf", 0, None))
    plugin.getSanPyWindow = lambda: window
    return plugin


_APPLY_SOURCE = pd.DataFrame(
    {
        "file": ["cell.abf"],
        "spikeNumber": [0],
        "sweep": [0],
        "include": ["no"],
        "spikeFreq_hz": [2.0],
    }
)


def test_metadata_refresh_replaces_rows_and_keeps_view() -> None:
    """Replace rows without resetting NicePool's plots and filters."""
    plugin = _plugin_for_apply(keep_view=True)

    plugin._apply_spike_results(_APPLY_SOURCE)

    plugin._nicepool.replace_dataframe.assert_called_once()
    plugin._nicepool.set_dataframe.assert_not_called()
    assert plugin._keep_view_on_apply is False


def test_rejected_metadata_refresh_reloads_with_presets() -> None:
    """Reload with SanPy presets when NicePool rejects the kept view."""
    plugin = _plugin_for_apply(keep_view=True)

    plugin._apply_spike_results(_APPLY_SOURCE)
    error_callback = plugin._nicepool.replace_dataframe.call_args.kwargs[
        "error_callback"
    ]
    error_callback("invalid state")

    plugin._nicepool.set_dataframe.assert_called_once()
    assert plugin._nicepool.set_dataframe.call_args.kwargs["default_preset"] == (
        "Sweep Plot"
    )


def test_plain_replot_loads_with_presets() -> None:
    """Load with SanPy presets when no metadata refresh is pending."""
    plugin = _plugin_for_apply(keep_view=False)

    plugin._apply_spike_results(_APPLY_SOURCE)

    plugin._nicepool.set_dataframe.assert_called_once()
    plugin._nicepool.replace_dataframe.assert_not_called()


def test_metadata_change_refreshes_only_the_shown_file() -> None:
    """Refresh the single-file plugin only for its own recording's metadata."""
    plugin = NicePoolPlugin.__new__(NicePoolPlugin)
    plugin._nicepool = MagicMock()
    plugin._ba = MagicMock()
    plugin._keep_view_on_apply = False
    plugin.replot = MagicMock()

    plugin.slot_metaDataChanged({"ba": MagicMock(), "key": "include", "value": "no"})
    plugin.replot.assert_not_called()
    assert plugin._keep_view_on_apply is False

    plugin.slot_metaDataChanged({"ba": plugin._ba, "key": "include", "value": "no"})
    plugin.replot.assert_called_once_with()
    assert plugin._keep_view_on_apply is True


def test_pool_metadata_change_refreshes_for_any_file() -> None:
    """Re-pool after a metadata edit to any recording in the folder."""
    plugin = NicePoolPoolPlugin.__new__(NicePoolPoolPlugin)
    plugin._nicepool = MagicMock()
    plugin._ba = MagicMock()
    plugin._keep_view_on_apply = False
    plugin.replot = MagicMock()

    plugin.slot_metaDataChanged({"ba": MagicMock(), "key": "sex", "value": "male"})

    plugin.replot.assert_called_once_with()
    assert plugin._keep_view_on_apply is True


def test_prepare_nicepool_data_requires_spike_identity() -> None:
    """Reject a table that cannot map rows back to SanPy spikes."""
    with pytest.raises(ValueError, match="spikeNumber"):
        prepare_nicepool_data(pd.DataFrame({"thresholdVal": [-42.5]}))


def test_selection_to_spikes_puts_primary_first_and_deduplicates() -> None:
    """Preserve multi-selection while making the primary row deterministic."""
    selection = {
        "primaryRowId": "3",
        "selectedRowIds": ["2", "3", "unknown"],
    }

    primary, spikes = selection_to_spikes(selection, {"2": 2, "3": 3})

    assert primary == "3"
    assert spikes == [3, 2]


def test_nicepool_spike_results_are_the_current_file() -> None:
    """Keep the single-file plugin on one analysis table."""
    analysis = MagicMock()
    analysis.isAnalyzed.return_value = True
    frame = pd.DataFrame({"spikeNumber": [0]})
    analysis.asDataFrame.return_value = frame
    plugin = NicePoolPlugin.__new__(NicePoolPlugin)
    plugin._current_file_number = 4
    plugin._ba = analysis

    result = plugin._spike_results()

    assert result is frame
    assert plugin._current_file_number is None
    analysis.asDataFrame.assert_called_once_with(regenerateAnalysisDataFrame=True)


def test_nicepool_pool_plugin_builds_rows_incrementally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pool one row per timer turn and report each relative file key.

    Args:
        monkeypatch: Pytest fixture used to capture timer callbacks.
    """
    assert issubclass(NicePoolPoolPlugin, NicePoolPlugin)

    callbacks: list[Callable[[], None]] = []
    monkeypatch.setattr(
        QtCore.QTimer,
        "singleShot",
        lambda _delay, callback: callbacks.append(callback),
    )
    first = pd.DataFrame(
        {
            "spikeNumber": [1],
            "file_number": [0],
            "file_key": ["first.abf"],
            "row_id": ["0:1"],
        }
    )
    analysis_dir = MagicMock()
    analysis_dir.get_row_for_file_key.return_value = 1
    analysis_dir.getDataFrame.return_value = pd.DataFrame(index=[0, 1])
    analysis_dir.get_file_key.side_effect = ["first.abf", "nested/second.abf"]
    analysis_dir.spike_dataframe_for_row.side_effect = [first, None]
    window = MagicMock()
    window.myAnalysisDir = analysis_dir
    window.state = WindowState("current.abf", 0, None)
    plugin = NicePoolPoolPlugin.__new__(NicePoolPoolPlugin)
    plugin._nicepool = MagicMock()
    plugin._pool_generation = 0
    plugin._pool_row_indices = []
    plugin._pool_frames = []
    plugin._pool_position = 0
    plugin._initial_pool_complete = False
    plugin._current_file_number = None
    plugin._handling_nicepool_selection = False
    plugin._row_id_to_file_key = {}
    plugin._apply_spike_results = MagicMock()
    plugin.mark_initial_display_ready = MagicMock()
    plugin.getSanPyWindow = lambda: window

    plugin.replot()
    assert len(callbacks) == 1
    callbacks.pop(0)()
    callbacks.pop(0)()
    plugin.mark_initial_display_ready.assert_not_called()
    callbacks.pop(0)()

    assert plugin._current_file_number == 1
    assert window.slot_updateStatus.call_args_list == [
        call('Pooling file 1 of 2 "first.abf"'),
        call('Pooling file 2 of 2 "nested/second.abf"'),
    ]
    analysis_dir.spike_dataframe_for_row.assert_any_call(0)
    analysis_dir.spike_dataframe_for_row.assert_any_call(1)
    pooled = plugin._apply_spike_results.call_args.args[0]
    pd.testing.assert_frame_equal(pooled, first)
    plugin.mark_initial_display_ready.assert_called_once_with()


def test_pool_sanpy_selection_uses_current_file_row_ids() -> None:
    """Map SanPy spikes to pooled row IDs for the current recording."""
    plugin = NicePoolPoolPlugin.__new__(NicePoolPoolPlugin)
    plugin._nicepool = MagicMock()
    plugin._current_file_number = 4
    plugin._handling_nicepool_selection = False
    plugin._row_id_to_spike = {"4:2": 2, "4:3": 3, "5:2": 2}
    plugin._selectedSpikeList = [3, 2]
    plugin._highlight_spikes = None

    plugin.selectSpikeList()

    plugin._nicepool.set_selection.assert_called_once_with(
        "4:3",
        ["4:3", "4:2"],
    )


def test_nicepool_selection_is_not_echoed_back_to_nicepool() -> None:
    """Skip the NicePool push while the window applies NicePool's own request."""
    window = SimpleNamespace(
        state=WindowState("cell.abf", 0, None),
        myAnalysisDir=MagicMock(),
    )
    plugin = NicePoolPlugin.__new__(NicePoolPlugin)
    plugin._nicepool = MagicMock()
    plugin._ba = MagicMock()
    plugin._current_file_number = None
    plugin._handling_nicepool_selection = False
    plugin._row_id_to_spike = {"2": 2, "3": 3}
    plugin._row_id_to_file_key = {"2": "cell.abf", "3": "cell.abf"}
    plugin._selectedSpikeList = [2, 3]
    plugin._highlight_spikes = None
    plugin.getSanPyWindow = lambda: window
    window.myAnalysisDir.get_analysis_for_file_key.return_value.getSpikeStat.return_value = [0]

    def echo_state(_state: WindowState, _do_zoom: bool = False) -> None:
        """Mimic the window calling back into the plugin synchronously.

        Args:
            _state: Requested window state.
            _do_zoom: Whether zoom was requested.
        """
        plugin.selectSpikeList()

    plugin.request_window_state = MagicMock(side_effect=echo_state)

    plugin._on_nicepool_selection({"primaryRowId": "2", "selectedRowIds": ["2", "3"]})

    plugin.request_window_state.assert_called_once_with(
        WindowState("cell.abf", 0, (2, 3))
    )
    plugin._nicepool.set_selection.assert_not_called()
    assert plugin._handling_nicepool_selection is False
    plugin.selectSpikeList()
    plugin._nicepool.set_selection.assert_called_once_with("2", ["2", "3"])


def test_nicepool_pool_file_change_keeps_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Track a new current file and its selection without rebuilding the pool.

    Args:
        monkeypatch: Pytest fixture used to detect pool timer scheduling.
    """
    timers = MagicMock()
    monkeypatch.setattr(QtCore.QTimer, "singleShot", timers)
    second = MagicMock()
    analysis_dir = MagicMock()
    analysis_dir.get_analysis_for_file_key.return_value = second
    analysis_dir.get_row_for_file_key.return_value = 5
    window = SimpleNamespace(myAnalysisDir=analysis_dir)
    plugin = NicePoolPoolPlugin.__new__(NicePoolPoolPlugin)
    plugin._nicepool = MagicMock()
    plugin._ba = MagicMock()
    plugin._pool_generation = 3
    plugin._current_file_number = 1
    plugin._handling_nicepool_selection = False
    plugin._row_id_to_spike = {"5:8": 8, "1:8": 8}
    plugin._selectedSpikeList = []
    plugin._last_window_state = WindowState("first.abf", 0, None)
    plugin._highlight_spikes = None
    plugin._mySetWindowTitle = MagicMock()
    plugin._updateTopToolbar = MagicMock()
    plugin.getSanPyWindow = lambda: window

    plugin.slot_window_state(WindowState("nested/second.abf", 0, (8,)))

    assert plugin.ba is second
    assert plugin._current_file_number == 5
    assert plugin.selectedSpike == 8
    assert plugin._pool_generation == 3
    timers.assert_not_called()
    plugin._nicepool.set_dataframe.assert_not_called()
    plugin._nicepool.set_selection.assert_called_once_with("5:8", ["5:8"])


def _pool_plugin_for_window_state(
    monkeypatch: pytest.MonkeyPatch,
    previous: WindowState,
    sweep_spikes: list[int],
) -> NicePoolPoolPlugin:
    """Build a pooled plugin whose window lookup returns one recording at row 5.

    Args:
        monkeypatch: Pytest fixture used to disable pool timer scheduling.
        previous: Window state the plugin last received.
        sweep_spikes: Spike numbers the recording reports for any sweep.

    Returns:
        A pooled plugin with a mocked NicePool widget.
    """
    monkeypatch.setattr(QtCore.QTimer, "singleShot", MagicMock())
    ba = MagicMock()
    ba.numSpikes = 3
    ba.getStat.return_value = sweep_spikes
    analysis_dir = MagicMock()
    analysis_dir.get_analysis_for_file_key.return_value = ba
    analysis_dir.get_row_for_file_key.return_value = 5
    window = SimpleNamespace(myAnalysisDir=analysis_dir)
    plugin = NicePoolPoolPlugin.__new__(NicePoolPoolPlugin)
    plugin._nicepool = MagicMock()
    plugin._ba = ba
    plugin._current_file_number = 5
    plugin._handling_nicepool_selection = False
    plugin._row_id_to_spike = {"5:0": 0, "5:1": 1, "5:2": 2, "1:0": 0}
    plugin._selectedSpikeList = []
    plugin._last_window_state = previous
    plugin._highlight_spikes = None
    plugin._mySetWindowTitle = MagicMock()
    plugin._updateTopToolbar = MagicMock()
    plugin.getSanPyWindow = lambda: window
    return plugin


def test_nicepool_pool_new_file_highlights_every_file_spike(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Highlight all pooled rows of a newly selected file without a primary row.

    Args:
        monkeypatch: Pytest fixture used to disable pool timer scheduling.
    """
    plugin = _pool_plugin_for_window_state(
        monkeypatch, WindowState("first.abf", 0, None), [0]
    )

    plugin.slot_window_state(WindowState("second.abf", 0, None))

    plugin._nicepool.set_selection.assert_called_once_with(
        None, ["5:0", "5:1", "5:2"]
    )
    assert plugin.getSelectedSpikes() == []


def test_nicepool_pool_sweep_change_highlights_sweep_spikes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Highlight the pooled rows of the newly selected sweep.

    Args:
        monkeypatch: Pytest fixture used to disable pool timer scheduling.
    """
    plugin = _pool_plugin_for_window_state(
        monkeypatch, WindowState("second.abf", 0, None), [1, 2]
    )

    plugin.slot_window_state(WindowState("second.abf", 1, None))

    plugin._ba.getStat.assert_called_once_with("spikeNumber", sweepNumber=1)
    plugin._nicepool.set_selection.assert_called_once_with(None, ["5:1", "5:2"])


def test_nicepool_pool_spike_selection_wins_over_file_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the window's spike selection when it also changes the file.

    Args:
        monkeypatch: Pytest fixture used to disable pool timer scheduling.
    """
    plugin = _pool_plugin_for_window_state(
        monkeypatch, WindowState("first.abf", 0, None), [0]
    )

    plugin.slot_window_state(WindowState("second.abf", 1, (2,)))

    plugin._nicepool.set_selection.assert_called_once_with("5:2", ["5:2"])


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (WindowState("cell.abf", 1, None), (None, ["3", "4"])),
        (WindowState("other.abf", 1, None), (None, [])),
        (WindowState("cell.abf", 0, None), (None, [])),
    ],
)
def test_nicepool_highlight_follows_sweep_but_not_file(
    state: WindowState,
    expected: tuple[str | None, list[str]],
) -> None:
    """Highlight a new sweep's spikes, but not a new file's, in the single-file plugin.

    Args:
        state: Window state following ``cell.abf`` sweep 0.
        expected: Primary and selected row IDs pushed to NicePool.
    """
    plugin = NicePoolPlugin.__new__(NicePoolPlugin)
    plugin._nicepool = MagicMock()
    plugin._ba = MagicMock()
    plugin._ba.getStat.return_value = [3, 4]
    plugin._current_file_number = None
    plugin._handling_nicepool_selection = False
    plugin._row_id_to_spike = {"3": 3, "4": 4}
    plugin._selectedSpikeList = []
    plugin._last_window_state = WindowState("cell.abf", 0, None)
    plugin._highlight_spikes = None

    plugin._update_highlight(state)
    plugin.selectSpikeList()

    plugin._nicepool.set_selection.assert_called_once_with(*expected)
    assert plugin._last_window_state == state


def test_nicepool_pool_without_a_folder_shows_empty_state() -> None:
    """Do not fall back to the current file when no folder is open."""
    plugin = NicePoolPoolPlugin.__new__(NicePoolPoolPlugin)
    plugin._nicepool = MagicMock()
    plugin._pool_generation = 0
    plugin._pool_row_indices = []
    plugin._pool_frames = []
    plugin._pool_position = 0
    plugin._initial_pool_complete = False
    plugin._current_file_number = 3
    plugin._handling_nicepool_selection = False
    plugin._row_id_to_file_key = {}
    plugin._apply_spike_results = MagicMock()
    plugin.mark_initial_display_ready = MagicMock()
    plugin.getSanPyWindow = lambda: None

    plugin.replot()

    assert plugin._current_file_number is None
    plugin._apply_spike_results.assert_called_once_with(None)
    plugin.mark_initial_display_ready.assert_called_once_with()


def test_nicepool_pool_ignores_superseded_timer_callback() -> None:
    """Drop a timer callback after replot or close advances its generation."""
    plugin = NicePoolPoolPlugin.__new__(NicePoolPoolPlugin)
    plugin._pool_generation = 2
    plugin.getSanPyWindow = MagicMock()

    plugin._pool_next_row(1)

    plugin.getSanPyWindow.assert_not_called()


def test_selection_to_spikes_rejects_malformed_payload() -> None:
    """Treat malformed browser selection data as an empty selection."""
    assert selection_to_spikes([], {"2": 2}) == (None, [])


def test_pool_primary_row_requests_its_file_and_drops_other_files() -> None:
    """Build one cross-file transition from the explicit NicePool primary row."""
    selected_analysis = MagicMock()
    selected_analysis.getSpikeStat.return_value = [4]
    analysis_dir = MagicMock()
    analysis_dir.get_analysis_for_file_key.return_value = selected_analysis
    selection = {
        "primaryRowId": "second:8",
        "selectedRowIds": ["first:2", "second:9", "second:8"],
    }

    state = selection_to_window_state(
        selection,
        {"first:2": 2, "second:8": 8, "second:9": 9},
        {
            "first:2": "first.abf",
            "second:8": "nested/second.abf",
            "second:9": "nested/second.abf",
        },
        analysis_dir,
        WindowState("first.abf", 0, None),
    )

    assert state == WindowState("nested/second.abf", 4, (8, 9))
    analysis_dir.get_analysis_for_file_key.assert_called_once_with(
        "nested/second.abf"
    )


def test_nicepool_plugin_webengine_selection_round_trip(qtbot: QtBot) -> None:
    """Synchronize selections in both directions without requesting zoom."""
    pytest.importorskip("nicepool_pyqt5")
    analysis = MagicMock()
    analysis.fileLoader.filename = "cell.abf"
    analysis.fileLoader.numEpochs = 1
    analysis.fileLoader.numSweeps = 1
    analysis.isAnalyzed.return_value = True
    analysis.getSpikeStat.return_value = [0]
    analysis.asDataFrame.return_value = pd.DataFrame(
        {
            "file": ["cell.abf", "cell.abf"],
            "spikeNumber": [2, 3],
            "sweep": [0, 0],
            "epoch": [0, 0],
            "epochLevel": [10.0, 10.0],
            "include": ["yes", "yes"],
            "thresholdVal": [-42.5, -40.0],
            "spikeFreq_hz": [20.0, 25.0],
        }
    )

    plugin = NicePoolPlugin(ba=analysis)
    qtbot.addWidget(plugin)
    assert plugin.size().width() == 1200
    assert plugin.size().height() == 800
    assert plugin._nicepool is not None, plugin._status_label.text()
    data_resets = QSignalSpy(plugin._nicepool.data_reset)
    analysis_dir = MagicMock()
    analysis_dir.get_analysis_for_file_key.return_value = analysis
    plugin._sanPyWindow = SimpleNamespace(
        state=WindowState("cell.abf", 0, None),
        myAnalysisDir=analysis_dir,
    )
    emitted_selections = QSignalSpy(plugin.signalStateRequest)
    errors = QSignalSpy(plugin._nicepool.error_occurred)

    plugin.show()
    qtbot.waitUntil(lambda: len(data_resets) == 1, timeout=20_000)
    initial_state: list[object] = []

    def collect_initial_state(state: object) -> None:
        """Collect the atomically initialized NicePool state.

        Args:
            state: Complete NicePool state returned by the browser.
        """
        initial_state.append(state)

    plugin._nicepool.get_state(collect_initial_state)
    qtbot.waitUntil(
        lambda: len(initial_state) == 1,
        timeout=5_000,
    )
    applied_state = initial_state[0]
    assert isinstance(applied_state, dict)
    assert applied_state["layout"] == "1x2"
    for plot in applied_state["plots"][:2]:
        assert plot["plotType"] == "swarm"
        assert plot["groupColumn"] == "sweep"
        assert plot["yColumn"] == "spikeFreq_hz"
        assert plot["showPlotlyToolbar"] is False
    presets: list[object] = []
    collapsed: list[object] = []
    plugin._nicepool.get_presets(presets.append)
    plugin._nicepool.get_controls_collapsed(collapsed.append)
    qtbot.waitUntil(lambda: len(presets) == 1 and len(collapsed) == 1, timeout=5_000)
    assert [preset["name"] for preset in presets[0]] == ["FI Plot", "Sweep Plot"]
    assert collapsed == [True]

    plugin.setSelectedSpikes([3, 2])
    plugin.selectSpikeList()
    browser_selection: list[object] = []
    plugin._nicepool.get_selection(browser_selection.append)
    qtbot.waitUntil(lambda: len(browser_selection) == 1, timeout=5_000)
    assert browser_selection == [
        {"primaryRowId": "3", "selectedRowIds": ["3", "2"]}
    ]

    selection = {"primaryRowId": "2", "selectedRowIds": ["3", "2"]}
    script = f"""
      document.querySelector('nice-pool').dispatchEvent(
        new CustomEvent('nicepool-selection-change', {{detail: {json.dumps(selection)}}})
      );
    """
    plugin._nicepool.web_view.page().runJavaScript(script)
    qtbot.waitUntil(lambda: len(emitted_selections) == 1, timeout=5_000)

    state = emitted_selections[0][0]
    assert state == WindowState("cell.abf", 0, (2, 3))
    assert emitted_selections[0][1] is False
    assert len(errors) == 0
