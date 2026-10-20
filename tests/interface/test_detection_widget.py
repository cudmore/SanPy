"""Tests for detection-widget plotting behavior."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import numpy as np
import pyqtgraph as pg
import pytest
from qtpy import QtCore, QtGui, QtWidgets

import sanpy
from sanpy.interface.util import sanpyCursors
from sanpy.interface.window_state import WindowState


def test_window_state_normalizes_empty_spike_selection() -> None:
    """Represent every empty spike selection with the canonical ``None`` value."""
    state = WindowState("recording.abf", 0, ())

    assert state.spike_selection is None


def test_folder_window_selects_first_visible_file(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, tmp_path: Path
) -> None:
    """Select the top file-table row when a folder window opens.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        tmp_path: Temporary directory supplied by pytest.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    for name in ("2021_07_20_0010.abf", "19114001.abf"):
        source = data_path / name
        (tmp_path / name).write_bytes(source.read_bytes())
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(tmp_path))
    table = window._fileListWidget.getTableView()
    real_row = table.model()._data.index[0]
    file_key = window.myAnalysisDir.get_file_key(real_row)

    assert window.state == WindowState(file_key, 0, None)
    assert table.currentIndex().row() == 0
    assert window.myDetectionWidget.ba is window.myAnalysisDir.get_analysis_for_file_key(
        file_key
    )


def test_empty_folder_window_leaves_detection_unselected(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, tmp_path: Path
) -> None:
    """Leave detection empty when a folder window has no recordings.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        tmp_path: Temporary directory supplied by pytest.
    """
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(tmp_path))

    assert window.state is None
    assert window.get_bAnalysis() is None
    assert window._fileListWidget.getTableView().currentIndex().row() == -1


def test_file_switch_applies_one_complete_state_without_nested_request(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Apply a file click once with sweep zero and no selected spikes.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    previous_row = window.myAnalysisDir.findFileRow("2021_07_20_0010.abf")
    previous_key = window.myAnalysisDir.get_file_key(previous_row)
    window.request_state(WindowState(previous_key, 0, None))
    row = window.myAnalysisDir.findFileRow("19114001.abf")
    row_dict = window.myAnalysisDir.getRowDict(row)
    file_key = window.myAnalysisDir.get_file_key(row)
    state_requests = Mock()
    state_changes = Mock()
    window.myDetectionWidget.signalStateRequest.connect(state_requests)
    window.signalStateChanged.connect(state_changes)

    window.slot_fileTableClicked(row, row_dict, selectingAgain=False)

    expected = WindowState(file_key, 0, None)
    assert window.state == expected
    assert window.myDetectionWidget.ba is window.myAnalysisDir.get_analysis_for_file_key(
        file_key
    )
    assert window.myDetectionWidget.sweepNumber == 0
    assert window.myDetectionWidget._selectedSpikeList == []
    assert state_requests.call_count == 0
    assert state_changes.call_count == 1
    assert state_changes.call_args.args == (expected,)


def test_applied_sweep_and_spike_state_do_not_request_nested_state(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Keep render-only sweep, clear, and zoom operations out of request flow.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    row = window.myAnalysisDir.findFileRow("2021_07_20_0010.abf")
    file_key = window.myAnalysisDir.get_file_key(row)
    window.request_state(WindowState(file_key, 0, None))
    analysis = window.myAnalysisDir.get_analysis_for_file_key(file_key)
    assert analysis is not None
    analysis.spikeDetect(sanpy.bDetection().getDetectionDict("Fast Neuron"))
    state_requests = Mock()
    state_changes = Mock()
    window.myDetectionWidget.signalStateRequest.connect(state_requests)
    window.signalStateChanged.connect(state_changes)

    window.request_state(WindowState(file_key, 1, None))

    assert window.state == WindowState(file_key, 1, None)
    assert window.myDetectionWidget.sweepNumber == 1
    assert window.myDetectionWidget._selectedSpikeList == []
    assert state_requests.call_count == 0
    assert state_changes.call_count == 1

    state_requests.reset_mock()
    state_changes.reset_mock()
    window.request_state(WindowState(file_key, 8, (0,)), do_zoom=True)

    expected = WindowState(file_key, 8, (0,))
    assert window.state == expected
    assert window.myDetectionWidget.sweepNumber == 8
    assert window.myDetectionWidget._selectedSpikeList == [0]
    assert state_requests.call_count == 0
    assert state_changes.call_count == 1
    assert state_changes.call_args.args == (expected,)


def test_plot_range_signals_are_connected_once(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Connect each plot-range callback once during widget construction.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    widget = window.myDetectionWidget
    plot_item = widget.vmPlot.getPlotItem()

    assert plot_item.receivers(widget.vmPlot.sigXRangeChanged) == 1
    assert plot_item.receivers(widget.vmPlot.sigYRangeChanged) == 1

    # Replot two recordings; receiver counts must remain unchanged.
    first_row = window.myAnalysisDir.findFileRow("19114001.abf")
    second_row = window.myAnalysisDir.findFileRow("2021_07_20_0010.abf")
    assert first_row is not None
    assert second_row is not None
    window.selectFileListRow(first_row)
    window.selectFileListRow(second_row)
    assert plot_item.receivers(widget.vmPlot.sigXRangeChanged) == 1
    assert plot_item.receivers(widget.vmPlot.sigYRangeChanged) == 1


def test_invalid_spike_still_applies_valid_file_and_sweep(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Discard a bad spike without rejecting its valid file and sweep.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    row = window.myAnalysisDir.findFileRow("2021_07_20_0010.abf")
    file_key = window.myAnalysisDir.get_file_key(row)

    window.request_state(WindowState(file_key, 1, (10_000_000,)))

    assert window.state == WindowState(file_key, 1, None)
    assert window.myDetectionWidget.sweepNumber == 1
    assert "Ignoring invalid spike selection" in window.statusBar().currentMessage()

def test_theme_switch_updates_existing_recording_plots(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Refresh existing pyqtgraph backgrounds, axes, and trace pens.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
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
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    widget = window.myDetectionWidget
    button = widget._viewToggleButtons[("rawDataPanels", "Derivative")][0]
    first_button = button.parentWidget().layout().itemAt(0).widget()

    assert first_button.text() == "Full Recording"

    button.click()

    assert qapp.getOptions()["rawDataPanels"]["Derivative"] is button.isChecked()
    assert (not widget.derivPlot.isHidden()) is button.isChecked()

    menu_state = not button.isChecked()
    window._viewMenuAction("rawDataPanels", "Derivative", menu_state)

    assert button.isChecked() is menu_state
    assert (not widget.derivPlot.isHidden()) is menu_state


def test_left_toolbar_opens_one_panel_and_closes_plugin(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Show one left panel at a time, including SanPy Info, and disconnect a closed plugin.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    widget = window.myDetectionWidget
    toolbar_button = widget._leftToolbar._panel_buttons["Detection Panel"]
    file_button = widget._leftToolbar._panel_buttons["File Metadata Panel"]
    meta_button = widget._leftToolbar._panel_buttons["Set Meta Data Panel"]
    params_button = widget._leftToolbar._panel_buttons["Detection Parameters"]
    info_button = widget._leftToolbar._panel_buttons["SanPy Info"]

    assert list(widget._leftToolbar._panel_buttons) == [
        "Detection Panel",
        "File Metadata Panel",
        "Set Meta Data Panel",
        "Detection Parameters",
        "SanPy Info",
    ]
    assert file_button.toolTip() == "File Metadata"
    assert meta_button.toolTip() == "Experimental Metadata"
    assert widget.myHBoxLayout_detect.itemAt(0).widget() is widget._leftToolbar
    assert widget._leftPanelSplitter.widget(0) is widget._leftPanelContainer
    assert widget._leftPanelSplitter.widget(1) is widget._rawPlotColumn
    assert widget._leftToolbar.isHidden() is False
    # assert any(
    #     icon_name == "fa6s.tags"
    #     for _button, icon_name in widget._leftToolbar._icon_buttons
    # )
    # assert any(
    #     icon_name == "fa6s.circle-info"
    #     for _button, icon_name in widget._leftToolbar._icon_buttons
    # )
    assert toolbar_button.isChecked() is False
    assert file_button.isChecked() is False
    assert params_button.isChecked() is False
    assert meta_button.isChecked() is False
    assert info_button.isChecked() is False
    # A shared window may already be showing the detection panel.
    if not widget._detectionPanelWidget.isHidden():
        widget.toggleInterface("Detection Panel", False)
    assert widget._detectionPanelWidget.isHidden()
    assert widget._sanpyInfoWidget is None
    assert widget._leftPanelContainer.isHidden()
    assert widget.detectToolbarWidget.maximumWidth() > 280

    params_button.click()

    assert params_button.isChecked() is True
    assert toolbar_button.isChecked() is False
    assert file_button.isChecked() is False
    assert widget._detectionPanelWidget.isHidden() is True
    assert widget._leftPanelContainer.isHidden() is False
    assert widget._leftToolbar.isHidden() is False
    plugin = widget._leftPanelPlugin
    assert plugin is not None
    assert plugin.getHumanName() == "Detection Parameters"
    assert plugin.getWidget().isHidden() is False

    file_button.click()

    assert file_button.isChecked() is True
    assert params_button.isChecked() is False
    assert widget._leftPanelPlugin is not None
    assert widget._leftPanelPlugin.getHumanName() == "File Metadata"
    assert widget._detectionPanelWidget.isHidden() is True
    with pytest.raises(TypeError):
        window.signalStateChanged.disconnect(plugin.slot_window_state)

    file_plugin = widget._leftPanelPlugin
    meta_button.click()

    assert meta_button.isChecked() is True
    assert file_button.isChecked() is False
    assert params_button.isChecked() is False
    assert widget._leftPanelPlugin is not None
    assert widget._leftPanelPlugin.getHumanName() == "Set Meta Data"
    assert widget._detectionPanelWidget.isHidden() is True
    with pytest.raises(TypeError):
        window.signalStateChanged.disconnect(file_plugin.slot_window_state)

    meta_plugin = widget._leftPanelPlugin
    meta_button.click()

    assert widget._leftPanelPlugin is None
    assert widget._leftPanelContainer.isHidden() is True
    assert widget._leftToolbar.isHidden() is False
    with pytest.raises(TypeError):
        window.signalStateChanged.disconnect(meta_plugin.slot_window_state)
    with pytest.raises(TypeError):
        plugin.signalDetect.disconnect(window.slot_detect)

    toolbar_button.click()

    assert toolbar_button.isChecked() is True
    assert file_button.isChecked() is False
    assert params_button.isChecked() is False
    assert meta_button.isChecked() is False
    assert info_button.isChecked() is False
    assert widget._detectionPanelWidget.isHidden() is False
    assert widget._sanpyInfoWidget is None
    assert widget._leftPanelContainer.isHidden() is False

    info_button.click()

    assert info_button.isChecked() is True
    assert toolbar_button.isChecked() is False
    assert file_button.isChecked() is False
    assert params_button.isChecked() is False
    assert meta_button.isChecked() is False
    assert widget._leftPanelPlugin is None
    assert widget._detectionPanelWidget.isHidden() is True
    assert widget._sanpyInfoWidget is not None
    assert widget._sanpyInfoWidget.isHidden() is False
    assert widget._leftPanelContainer.isHidden() is False
    button_labels = [
        button.text()
        for button in widget._sanpyInfoWidget.findChildren(QtWidgets.QPushButton)
    ]
    assert button_labels == ["Copy SanPy Info", "SanPy-User-Files"]

    info_button.click()

    assert info_button.isChecked() is False
    assert widget._sanpyInfoWidget is None
    assert widget._leftPanelContainer.isHidden() is True


def test_raw_plot_toolbar_resets_axis_and_rebalances_visible_plots(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Reset the time range and give the Vm plot the leftover column height.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
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

    window.resize(1000, 900)
    qtbot.waitUntil(lambda: window.height() == 900)
    for name in ("Full Recording", "Derivative", "DAC"):
        window.setViewPanelVisible("rawDataPanels", name, False)
    qtbot.wait(1)

    column = widget._rawPlotColumn
    toggle_bar = widget._rawPlotLayout.itemAt(0).widget()
    sweep_controls = widget._plotSweepControls
    toggle_gap = sweep_controls.y() - toggle_bar.geometry().bottom() - 1
    plot_gap = widget.vmPlot.y() - sweep_controls.geometry().bottom() - 1
    layout_margins = widget.myHBoxLayout_detect.contentsMargins()
    available_height = (
        widget.contentsRect().height()
        - layout_margins.top()
        - layout_margins.bottom()
    )
    assert widget._leftPanelSplitter.height() == available_height
    assert column.height() == widget._leftPanelSplitter.contentsRect().height()
    assert toggle_gap == plot_gap
    assert widget.vmPlot.geometry().bottom() == column.rect().bottom()
    assert widget.vmPlot.height() == (
        column.height()
        - toggle_bar.height()
        - sweep_controls.height()
        - (2 * plot_gap)
    )
    for hidden_plot in (widget.vmPlotGlobal, widget.derivPlot, widget.dacPlot):
        assert hidden_plot.isHidden()


def test_sweep_change_fits_vm_y_axis_without_changing_x_axis(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Fit the selected sweep vertically while preserving its time range.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    row = window.myAnalysisDir.findFileRow("2021_07_20_0010.abf")
    assert row is not None
    window.selectFileListRow(row)
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
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    row = window.myAnalysisDir.findFileRow("2021_07_20_0010.abf")
    assert row is not None
    window.selectFileListRow(row)
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
    data_path = Path(__file__).resolve().parents[1] / "data"
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
            is_initial_display_ready=lambda: True,
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
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    widget = window.myDetectionWidget

    splitter_index = widget.myHBoxLayout_detect.indexOf(widget._leftPanelSplitter)

    assert widget.myHBoxLayout_detect.stretch(splitter_index) == 1
    assert widget._leftPanelSplitter.widget(1) is widget._rawPlotColumn
    assert widget._rawPlotColumn.layout() is widget._rawPlotLayout


def test_full_recording_and_derivative_scatter_overlays_start_off(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Leave Full Recording and Derivative scatter overlays off by default.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    widget = window.myDetectionWidget

    expected = {
        "Global Threshold (mV)": "vmGlobal",
        "Threshold (dV/dt)": "dvdt",
    }
    for name, plot_on in expected.items():
        index = next(
            index
            for index, plot_def in enumerate(widget.myPlots)
            if plot_def["humanName"] == name
        )
        assert widget.myPlots[index]["plotOn"] == plot_on
        assert widget.myPlots[index]["plotIsOn"] is False
        x_data, _y_data = widget.myPlotList[index].getData()
        assert x_data is None or len(x_data) == 0


def test_vm_plot_options_button_toggles_vm_overlays(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Open Vm overlay choices from the Vm plot and show or hide that overlay.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    widget = window.myDetectionWidget

    toolbar_titles = [
        box.title()
        for box in widget.detectToolbarWidget.findChildren(QtWidgets.QGroupBox)
    ]
    assert "Plot Options" not in toolbar_titles

    button = widget._vmPlotOptionsButton
    menu = button.menu()
    assert button.parentWidget() is widget.vmPlot
    assert button.text() == ""
    assert button.toolButtonStyle() == QtCore.Qt.ToolButtonIconOnly
    assert button.icon().isNull() is False
    assert button.iconSize() == QtCore.QSize(16, 16)
    assert button.popupMode() == QtWidgets.QToolButton.InstantPopup
    assert menu is not None
    assert menu.actions()[0].defaultWidget() is widget._vmPlotOptions

    grid = widget._vmPlotOptions.findChild(QtWidgets.QGridLayout)
    assert grid is not None
    placed: list[tuple[int, int, str, bool]] = []
    peak_box: QtWidgets.QCheckBox | None = None
    for index in range(grid.count()):
        child = grid.itemAt(index).widget()
        assert isinstance(child, QtWidgets.QCheckBox)
        row, column, _row_span, _column_span = grid.getItemPosition(index)
        placed.append((row, column, child.text(), child.isChecked()))
        if child.text() == "AP Peak (mV)":
            peak_box = child
    placed.sort()
    assert placed == [
        (0, 0, "Threshold (mV)", True),
        (0, 1, "AP Peak (mV)", False),
        (1, 0, "Fast AHP (mV)", False),
        (1, 1, "Half-Widths", False),
        (2, 0, "Epoch Lines", False),
    ]
    assert peak_box is not None

    plot = widget.vmPlot
    plot.resize(480, 240)
    widget._on_vm_plot_resized(plot, None)
    assert button.x() == 6
    assert button.y() == max(0, plot.height() - button.height() - 6)

    peak_index = next(
        index
        for index, plot_def in enumerate(widget.myPlots)
        if plot_def["humanName"] == "AP Peak (mV)"
    )
    peak_box.click()
    assert widget.myPlots[peak_index]["plotIsOn"] is True
    assert widget.myPlotList[peak_index].isVisible() is True

    peak_box.click()
    assert widget.myPlots[peak_index]["plotIsOn"] is False
    assert widget.myPlotList[peak_index].isVisible() is False


def test_vm_right_axis_shows_derivative_or_dac(
    monkeypatch: pytest.MonkeyPatch, qapp: Any, qtbot: Any
) -> None:
    """Show Derivative or DAC on the Vm right axis without changing stacked plots.

    Args:
        monkeypatch: Pytest fixture used to prevent preference-file writes.
        qapp: Running SanPy Qt application supplied by pytest-qt.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    data_path = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setattr(qapp.getOptions(), "save", lambda: None)
    window = qapp.openSanPyWindow(str(data_path))
    row = window.myAnalysisDir.findFileRow("2021_07_20_0010.abf")
    assert row is not None
    window.selectFileListRow(row)
    widget = window.myDetectionWidget
    qtbot.wait(1)

    assert set(qapp.getOptions()["rawDataPanels"]) == {
        "plotEveryPoint",
        "Full Recording",
        "Derivative",
        "DAC",
    }
    if not widget._vmRightAxisButtons["None"].isChecked():
        widget._vmRightAxisButtons["None"].click()
    assert widget.vmPlot.getAxis("right").isVisible() is False

    derivative_hidden = widget.derivPlot.isHidden()
    dac_hidden = widget.dacPlot.isHidden()
    widget._vmRightAxisButtons["Derivative"].click()
    qtbot.wait(1)

    derivative = np.asarray(widget.ba.fileLoader.filteredDeriv)
    sweep_y = np.asarray(widget.ba.fileLoader.sweepY)
    _x_data, right_y = widget._vmRightCurve.getData()
    _vm_x, vm_y_data = widget.vmPlot_.getData()
    assert widget.vmPlot.getAxis("right").isVisible() is True
    assert widget.vmPlot.getAxis("right").labelText == "Derivative"
    assert np.allclose(right_y, derivative, equal_nan=True)
    assert np.allclose(vm_y_data, sweep_y, equal_nan=True)
    assert widget.derivPlot.isHidden() is derivative_hidden
    assert widget.dacPlot.isHidden() is dac_hidden

    widget.vmPlot.setXRange(0.1, 0.2, padding=0)
    vm_x_range, vm_y_range = widget.vmPlot.viewRange()
    right_x_range, right_y_range = widget._vmRightView.viewRange()
    # ViewBox linking maps through each view's screen rectangle, so the shared
    # time window can differ by a fraction of a pixel.
    assert right_x_range == pytest.approx(vm_x_range, abs=1e-3)
    assert right_y_range[0] <= np.nanmin(derivative)
    assert right_y_range[1] >= np.nanmax(derivative)
    assert vm_y_range[0] <= np.nanmin(sweep_y)
    assert vm_y_range[1] >= np.nanmax(sweep_y)

    widget._vmRightAxisButtons["DAC"].click()
    qtbot.wait(1)
    sweep_c = np.asarray(widget.ba.fileLoader.sweepC)
    _x_data, right_y = widget._vmRightCurve.getData()
    assert widget.vmPlot.getAxis("right").labelText == "DAC"
    assert np.allclose(right_y, sweep_c, equal_nan=True)
    assert widget.derivPlot.isHidden() is derivative_hidden
    assert widget.dacPlot.isHidden() is dac_hidden

    widget.setPlotTheme(True)
    assert widget._vmRightCurve.opts["pen"].color().name() == pg.mkPen("b").color().name()
    assert (
        widget.vmPlot_.opts["pen"].color().name()
        != widget._vmRightCurve.opts["pen"].color().name()
    )

    widget._vmRightAxisButtons["None"].click()
    cleared_x, _cleared_y = widget._vmRightCurve.getData()
    assert widget.vmPlot.getAxis("right").isVisible() is False
    assert cleared_x is None or len(cleared_x) == 0
