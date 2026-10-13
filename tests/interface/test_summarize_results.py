"""Tests for Summarize Results row selection and its detection-error report."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import sanpy
from sanpy.interface.plugins.sanpyPlugin import sanpyPlugin
from sanpy.interface.plugins.summarizeResults import SummarizeResults
from sanpy.interface.window_state import WindowState


def test_error_report_uses_absolute_spike_numbers() -> None:
    """Report the absolute spike for an error detected as a sweep's first spike."""
    stored_error = {"Spike": 0, "Sweep": "", "Epoch": "", "Type": "t", "Details": "d"}
    ba = sanpy.bAnalysis.__new__(sanpy.bAnalysis)
    ba.spikeDict = [
        {"sweep": 0, "epoch": 0, "errors": []},
        {"sweep": 1, "epoch": 2, "errors": [stored_error]},
    ]
    ba._detectionDict = {"verbose": False}

    df = ba.getErrorReport()

    assert df["Spike"].tolist() == [1]
    assert df["Sweep"].tolist() == [1]
    assert df["Epoch"].tolist() == [2]
    assert stored_error["Spike"] == 0
    assert stored_error["Sweep"] == ""


def _plugin_with_window() -> SummarizeResults:
    """Build a Summarize Results plugin showing all sweeps of one recording.

    Returns:
        A plugin whose window requests call straight back into the plugin.
    """
    plugin = SummarizeResults.__new__(SummarizeResults)
    plugin._ba = MagicMock()
    plugin._ba.getSpikeStat.return_value = [3]
    plugin._sweepNumber = "All"
    plugin._selectedSpikeList = []
    plugin._requesting_spike = False
    plugin.myErrorTable = MagicMock()
    plugin.replot = MagicMock()
    window = SimpleNamespace(state=WindowState("cell.abf", 0, None))
    plugin.getSanPyWindow = lambda: window

    def echo_state(state: WindowState, do_zoom: bool = False) -> None:
        """Mimic the window calling back into the plugin synchronously.

        Args:
            state: Requested window state.
            do_zoom: Whether zoom was requested.
        """
        plugin.slot_window_state(state)

    plugin.request_window_state = MagicMock(side_effect=echo_state)
    return plugin


def test_row_click_keeps_all_sweeps_on_echo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Request the spike's sweep without switching the report away from 'All'.

    Args:
        monkeypatch: Pytest fixture used to detect the base-class transition.
    """
    base_slot = MagicMock()
    monkeypatch.setattr(sanpyPlugin, "slot_window_state", base_slot)
    plugin = _plugin_with_window()

    plugin._request_spike(7, False)

    plugin.request_window_state.assert_called_once_with(
        WindowState("cell.abf", 3, (7,)), do_zoom=False
    )
    base_slot.assert_not_called()
    plugin.replot.assert_not_called()
    assert plugin._sweepNumber == "All"
    assert plugin.getSelectedSpikes() == [7]
    assert plugin._requesting_spike is False


def test_window_transition_from_elsewhere_uses_base_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Follow window transitions that this plugin did not request.

    Args:
        monkeypatch: Pytest fixture used to detect the base-class transition.
    """
    base_slot = MagicMock()
    monkeypatch.setattr(sanpyPlugin, "slot_window_state", base_slot)
    plugin = _plugin_with_window()
    state = WindowState("cell.abf", 2, None)

    plugin.slot_window_state(state)

    base_slot.assert_called_once_with(state)
