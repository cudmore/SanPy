"""Tests for detection-widget plotting behavior."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import numpy as np
import pytest
from qtpy import QtCore, QtWidgets


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
    button_bar = button.parentWidget()
    detection_column = button_bar.parentWidget()

    assert button_bar.sizePolicy().verticalPolicy() == button_bar.sizePolicy().Fixed
    assert detection_column.layout().alignment() & QtCore.Qt.AlignTop

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


def test_raw_plot_toolbar_resets_axis_and_rebalances_visible_plots(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Reset the time range and equally stretch only visible trace plots.

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
    reset_axis = Mock()
    widget._resetAxisButton.clicked.disconnect()
    widget._resetAxisButton.clicked.connect(reset_axis)

    widget._resetAxisButton.click()
    window.setViewPanelVisible("rawDataPanels", "Derivative", False)
    window.setViewPanelVisible("rawDataPanels", "DAC", True)

    reset_axis.assert_called_once()
    plot_visibility = {
        widget.vmPlotGlobal: not widget.vmPlotGlobal.isHidden(),
        widget.derivPlot: not widget.derivPlot.isHidden(),
        widget.dacPlot: not widget.dacPlot.isHidden(),
        widget.vmPlot: not widget.vmPlot.isHidden(),
    }
    for plot_widget, visible in plot_visibility.items():
        layout_index = widget._rawPlotLayout.indexOf(plot_widget)
        assert widget._rawPlotLayout.stretch(layout_index) == (1 if visible else 0)


def test_sweep_change_fits_vm_y_axis_without_changing_x_axis(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Fit the selected sweep vertically while preserving its time range.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[2] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    window.selectFileListRow(2)
    widget = window.myDetectionWidget
    widget.vmPlot.setXRange(0.1, 0.2, padding=0)
    expected_x_range = widget.vmPlot.viewRange()[0]

    widget.selectSweep(1)
    qtbot.wait(1)

    actual_x_range, actual_y_range = widget.vmPlot.viewRange()
    sweep_y = np.asarray(widget.ba.fileLoader.sweepY)
    assert actual_x_range == pytest.approx(expected_x_range)
    assert actual_y_range[0] <= np.nanmin(sweep_y)
    assert actual_y_range[1] >= np.nanmax(sweep_y)


def test_plugins_button_uses_shared_menu_and_opens_new_tabs(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Open repeated plugin tabs from the right-aligned shared plugin menu.

    Args:
        monkeypatch: Pytest fixture used to isolate plugin construction.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[2] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    widget = window.myDetectionWidget
    plugin_button = widget._pluginMenuButton
    menu = plugin_button.menu()
    window.populatePluginTabMenu(menu)

    expected_plugins = qapp.getPlugins().pluginList()
    assert [action.text() for action in menu.actions()] == expected_plugins
    button_layout = plugin_button.parentWidget().layout()
    assert button_layout.itemAt(button_layout.count() - 1).widget() is plugin_button
    assert button_layout.itemAt(button_layout.count() - 2).spacerItem() is not None

    plugin_widgets = [QtWidgets.QWidget(), QtWidgets.QWidget()]
    plugins = [
        SimpleNamespace(
            getInitError=lambda: False,
            getShowSelf=lambda: True,
            getWidget=lambda widget=widget: widget,
        )
        for widget in plugin_widgets
    ]
    run_plugin = Mock(side_effect=plugins)
    monkeypatch.setattr(window, "runPlugin", run_plugin)
    window.pluginDock1.hide()
    initial_count = window.myPluginTab1.count()

    window.openPluginInTab(expected_plugins[0], window.myPluginTab1)
    window.openPluginInTab(expected_plugins[0], window.myPluginTab1)

    assert window.myPluginTab1.count() == initial_count + 2
    assert window.myPluginTab1.currentWidget() is plugin_widgets[-1]
    assert window.pluginDock1.isHidden() is False
    assert run_plugin.call_count == 2
