"""Tests for detection-widget plotting behavior."""

from pathlib import Path
from typing import Any

import pytest


def test_plot_range_signals_are_connected_once(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Connect each plot-range callback once during widget construction.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[2] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    qtbot.addWidget(window)
    widget = window.myDetectionWidget
    plot_item = widget.vmPlot.getPlotItem()

    assert plot_item.receivers(widget.vmPlot.sigXRangeChanged) == 1
    assert plot_item.receivers(widget.vmPlot.sigYRangeChanged) == 1

    # Replot two recordings; receiver counts must remain unchanged.
    window.selectFileListRow(3)
    window.selectFileListRow(2)
    assert plot_item.receivers(widget.vmPlot.sigXRangeChanged) == 1
    assert plot_item.receivers(widget.vmPlot.sigYRangeChanged) == 1
