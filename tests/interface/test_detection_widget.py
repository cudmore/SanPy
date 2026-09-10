"""Tests for detection-widget plotting behavior."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import numpy as np
import pyqtgraph as pg
import pytest
from qtpy import QtCore, QtGui, QtWidgets

from sanpy.interface.util import sanpyCursors


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

    window.setViewPanelVisible("detectionPanels", "Detection Panel", False)
    assert detection_column.isHidden()
    assert button_bar.isVisibleTo(window) is False
    assert widget.detectToolbarWidget.isVisibleTo(window) is False

    window.setViewPanelVisible("detectionPanels", "Detection Panel", True)
    assert detection_column.isHidden() is False


def test_theme_switch_updates_existing_recording_plots(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Refresh existing pyqtgraph backgrounds, axes, and trace pens.

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
    original_theme = qapp.useDarkStyle
    full_recording_pen = widget.vmPlotGlobal_.opts["pen"]

    try:
        for is_dark in (False, True):
            background = QtGui.QColor("black" if is_dark else "white")
            foreground = QtGui.QColor("white" if is_dark else "black")
            qapp.toggleStyleSheet(doDark=is_dark)

            for plot_widget in (
                widget.vmPlotGlobal,
                widget.derivPlot,
                widget.dacPlot,
                widget.vmPlot,
            ):
                assert plot_widget.backgroundBrush().color() == background
                assert plot_widget.getAxis("left").pen().color() == foreground
                assert plot_widget.getAxis("left").textPen().color() == foreground

            for trace in (widget.derivPlot_, widget.dacPlot_, widget.vmPlot_):
                assert trace.curve.opts["pen"].color() == foreground
            assert widget.vmPlotGlobal_.opts["pen"] == full_recording_pen
    finally:
        qapp.toggleStyleSheet(doDark=original_theme)


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
    detection_button = widget._viewToggleButtons[
        ("detectionPanels", "Detection Panel")
    ]

    assert detection_button.text() == "<<"
    assert detection_button.parentWidget().layout().itemAt(0).widget() is detection_button

    detection_button.click()

    assert qapp.getOptions()["detectionPanels"]["Detection Panel"] is False
    assert widget._detectionPanelWidget.isHidden()

    window._viewMenuAction("detectionPanels", "Detection Panel", True)

    assert detection_button.isChecked()
    assert widget._detectionPanelWidget.isHidden() is False

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
    offscreen_cursor_y = 1_000_000.0
    widget._sanpyCursors._cursorC.setValue(offscreen_cursor_y)

    widget.selectSweep(1)
    qtbot.wait(1)

    actual_x_range, actual_y_range = widget.vmPlot.viewRange()
    sweep_y = np.asarray(widget.ba.fileLoader.sweepY)
    assert actual_x_range == pytest.approx(expected_x_range)
    assert actual_y_range[0] <= np.nanmin(sweep_y)
    assert actual_y_range[1] >= np.nanmax(sweep_y)
    assert actual_y_range[1] < offscreen_cursor_y
    assert widget._sanpyCursors._cursorC.value() == offscreen_cursor_y



def test_cursor_overlays_do_not_affect_plot_bounds(qtbot: Any) -> None:
    """Exclude cursor overlays from auto-range while retaining Show In View.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    plot_widget = pg.PlotWidget(name="vmPlot")
    qtbot.addWidget(plot_widget)
    plot_widget.plot([10.0, 20.0], [-2.0, 3.0])
    cursors = sanpyCursors(plot_widget)
    offscreen_cursor_y = 1_000_000.0
    cursors._cursorC.setValue(offscreen_cursor_y)

    plot_widget.autoRange()
    _, y_range = plot_widget.viewRange()

    assert y_range[0] <= -2.0
    assert y_range[1] >= 3.0
    assert y_range[1] < offscreen_cursor_y
    assert cursors._cursorC.value() == offscreen_cursor_y

    # Show In View remains the explicit way to return an off-screen cursor.
    cursors.handleMenu("Show In View", False)
    cursor_y = cursors._cursorC.value()
    assert y_range[0] <= cursor_y <= y_range[1]


def test_full_recording_fits_y_axis_on_load_and_sweep_change(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Fit overview voltage data without changing its full time range.

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
    qtbot.wait(1)

    initial_x_range, initial_y_range = widget.vmPlotGlobal.viewRange()
    initial_sweep_y = np.asarray(widget.ba.fileLoader.sweepY)
    assert initial_y_range[0] <= np.nanmin(initial_sweep_y)
    assert initial_y_range[1] >= np.nanmax(initial_sweep_y)

    widget.selectSweep(1)
    qtbot.wait(1)

    actual_x_range, actual_y_range = widget.vmPlotGlobal.viewRange()
    sweep_y = np.asarray(widget.ba.fileLoader.sweepY)
    assert actual_x_range == pytest.approx(initial_x_range)
    assert actual_y_range[0] <= np.nanmin(sweep_y)
    assert actual_y_range[1] >= np.nanmax(sweep_y)


def test_plugins_button_reuses_existing_plugin_tabs(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Activate an existing plugin tab instead of constructing a duplicate.

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

    plugin_widgets = [
        QtWidgets.QWidget(),
        QtWidgets.QWidget(),
        QtWidgets.QWidget(),
    ]
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

    assert window.myPluginTab1.count() == initial_count + 1
    assert window.myPluginTab1.currentWidget() is plugin_widgets[0]
    assert window.pluginDock1.isHidden() is False
    assert run_plugin.call_count == 1

    window.openPluginInTab(expected_plugins[1], window.myPluginTab1)

    assert window.myPluginTab1.count() == initial_count + 2
    assert window.myPluginTab1.currentWidget() is plugin_widgets[1]
    assert run_plugin.call_count == 2

    first_plugin_index = next(
        index
        for index in range(window.myPluginTab1.count())
        if window.myPluginTab1.tabText(index) == expected_plugins[0]
    )
    window.slot_closeTab(first_plugin_index, window.myPluginTab1)
    window.openPluginInTab(expected_plugins[0], window.myPluginTab1)

    assert window.myPluginTab1.count() == initial_count + 2
    assert window.myPluginTab1.currentWidget() is plugin_widgets[2]
    assert run_plugin.call_count == 3


def test_raw_plot_column_expands_with_central_widget(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Assign expanding horizontal space to the raw-plot column.

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

    raw_plot_index = next(
        index
        for index in range(widget.myHBoxLayout_detect.count())
        if widget.myHBoxLayout_detect.itemAt(index).layout() is widget._rawPlotLayout
    )

    assert widget.myHBoxLayout_detect.stretch(raw_plot_index) == 1
