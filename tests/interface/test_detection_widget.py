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


def test_detection_view_buttons_share_view_menu_state(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Keep detection buttons, preferences, and View-menu behavior synchronized.

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
    button = widget._viewToggleButtons[("detectionPanels", "Detection")]

    button.click()

    assert qapp.getOptions()["detectionPanels"]["Detection"] is button.isChecked()
    assert (
        not widget.detectToolbarWidget.detectionGroupBox.isHidden()
    ) is button.isChecked()

    menu_state = not button.isChecked()
    window._viewMenuAction("detectionPanels", "Detection", menu_state)

    assert button.isChecked() is menu_state
    assert (not widget.detectToolbarWidget.detectionGroupBox.isHidden()) is menu_state


def test_raw_plot_buttons_share_view_menu_state(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Keep raw-plot buttons, preferences, and View-menu state synchronized.

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
    button = widget._viewToggleButtons[("rawDataPanels", "Derivative")]

    button.click()

    assert qapp.getOptions()["rawDataPanels"]["Derivative"] is button.isChecked()
    assert (not widget.derivPlot.isHidden()) is button.isChecked()

    menu_state = not button.isChecked()
    window._viewMenuAction("rawDataPanels", "Derivative", menu_state)

    assert button.isChecked() is menu_state
    assert (not widget.derivPlot.isHidden()) is menu_state
