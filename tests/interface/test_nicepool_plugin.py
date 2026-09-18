"""Tests for the SanPy NicePool plugin's data and selection boundaries."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock

import pandas as pd
import pytest
from PyQt5.QtTest import QSignalSpy
from pytestqt.qtbot import QtBot

from sanpy.interface.plugins.nicepool_plugin import (
    NicePoolPlugin,
    _PRESET_FI_PLOT,
    _PRESET_SWEEP_PLOT,
    _preset_required_columns,
    prepare_nicepool_data,
    selection_to_spikes,
)


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
            "include": [True],
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
    assert schema_by_name["include"]["category"] == "metadata"
    assert schema_by_name["include"]["axis_label"] == "Included"


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

    spikes = selection_to_spikes(selection, {"2": 2, "3": 3})

    assert spikes == [3, 2]


def test_selection_to_spikes_rejects_malformed_payload() -> None:
    """Treat malformed browser selection data as an empty selection."""
    assert selection_to_spikes([], {"2": 2}) == []


@pytest.mark.skipif(
    os.environ.get("SANPY_RUN_NICEPOOL_WEBENGINE_TEST") != "1",
    reason="set SANPY_RUN_NICEPOOL_WEBENGINE_TEST=1 on a macOS development host",
)
def test_nicepool_plugin_webengine_selection_round_trip(qtbot: QtBot) -> None:
    """Synchronize selections in both directions without requesting zoom."""
    analysis = MagicMock()
    analysis.fileLoader.filename = "cell.abf"
    analysis.fileLoader.numEpochs = 1
    analysis.fileLoader.numSweeps = 1
    analysis.isAnalyzed.return_value = True
    analysis.asDataFrame.return_value = pd.DataFrame(
        {
            "file": ["cell.abf", "cell.abf"],
            "spikeNumber": [2, 3],
            "sweep": [0, 0],
            "epoch": [0, 0],
            "epochLevel": [10.0, 10.0],
            "include": [True, True],
            "thresholdVal": [-42.5, -40.0],
            "spikeFreq_hz": [20.0, 25.0],
        }
    )

    plugin = NicePoolPlugin(ba=analysis)
    qtbot.addWidget(plugin)
    assert plugin.size().width() == 1200
    assert plugin.size().height() == 800
    assert plugin._nicepool is not None
    data_resets = QSignalSpy(plugin._nicepool.data_reset)
    emitted_selections = QSignalSpy(plugin.signalSelectSpikeList)
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
        assert plot["groupColumn"] == "epochLevel"
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

    event = emitted_selections[0][0]
    assert event["spikeList"] == [2, 3]
    assert event["doZoom"] is False
    assert event["ba"] is analysis
    assert len(errors) == 0
