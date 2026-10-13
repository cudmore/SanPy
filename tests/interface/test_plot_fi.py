"""Tests for pandas-backed Plot FI summary calculations."""

import warnings
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest
from qtpy import QtCore, QtWidgets

from sanpy.interface.plugins.plotFi import getStatFi, plotFi
from sanpy.interface.plugins.sanpyPlugin import sanpyPlugin
from sanpy.interface.window_state import WindowState


def test_plot_fi_uses_horizontal_splitter(qtbot: Any) -> None:
    """Keep the statistic selector and plot in draggable left/right panes."""
    plugin = plotFi(ba=None)
    qtbot.addWidget(plugin)

    assert plugin._mainSplitter.orientation() == QtCore.Qt.Horizontal
    assert plugin._mainSplitter.count() == 2


def test_plot_fi_only_raw_artist_requests_spike_state(qtbot: Any) -> None:
    """Map a raw FI point to its spike while ignoring aggregate artists.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    plugin = plotFi.__new__(plotFi)
    QtWidgets.QWidget.__init__(plugin)
    qtbot.addWidget(plugin)
    raw_artist = object()
    plugin._raw_artist = raw_artist
    plugin._raw_spike_rows = pd.DataFrame(
        {"spikeNumber": [11, 12], "sweep": [2, 3]}
    )
    plugin._sanPyWindow = SimpleNamespace(
        state=WindowState("cell.abf", 0, None)
    )
    plugin.request_window_state = Mock()

    plugin._on_raw_pick(SimpleNamespace(artist=object(), ind=[0]))
    plugin.request_window_state.assert_not_called()

    plugin._on_raw_pick(SimpleNamespace(artist=raw_artist, ind=[1]))
    requested = plugin.request_window_state.call_args.args[0]
    assert requested == WindowState("cell.abf", 3, (12,))


def test_get_stat_fi_aligns_results_by_sweep() -> None:
    """Verify FI results align by sweep rather than source-row index."""
    master = pd.DataFrame(
        {
            "epoch": [2, 2, 2, 2, 2, 2],
            "epochLevel": [20.1234, 20.1234, 10.5678, 10.5678, 10.5678, 10.5678],
            "sweep": [7, 7, 3, 3, 3, 3],
            "thresholdSec": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        },
        index=[40, 54, 3, 7, 22, 77],
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = getStatFi(master, "thresholdSec", filename="example.abf")

    assert result["sweep"].tolist() == [7, 3]
    assert result["epochLevel"].tolist() == [20.123, 10.568]
    assert result["thresholdSec_count"].tolist() == [2, 4]
    assert result["thresholdSec_first"].tolist() == [0.1, 0.3]
    assert result["thresholdSec_second"].tolist() == [0.2, 0.4]
    assert result["thresholdSec_last"].tolist() == [0.2, 0.6]
    assert result["filename"].tolist() == ["example.abf", "example.abf"]
    sweep_seven = result.loc[result["sweep"] == 7].iloc[0]
    assert sweep_seven["thresholdSec_mean"] == 0.15
    assert sweep_seven["thresholdSec_median"] == 0.15
    assert sweep_seven["thresholdSec_min"] == 0.1
    assert sweep_seven["thresholdSec_max"] == 0.2
    assert sweep_seven["thresholdSec_std"] == 0.07
    assert sweep_seven["thresholdSec_sem"] == 0.05
    assert sweep_seven["thresholdSec_1_2"] == 0.5
    assert sweep_seven["thresholdSec_1_n"] == 0.5
    assert np.isclose(sweep_seven["thresholdSec_cv"], 0.07 / 0.15)


def test_get_stat_fi_handles_short_interval_groups() -> None:
    """Verify missing positional interval values are represented by NaN."""
    master = pd.DataFrame(
        {
            "epoch": [2, 2, 2, 2],
            "epochLevel": [10.0, 20.0, 20.0, 20.0],
            "sweep": [3, 7, 7, 7],
            "isi_ms": [np.nan, np.nan, 8.0, 10.0],
        },
        index=[10, 20, 30, 40],
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = getStatFi(master, "isi_ms", intervalStat=True)

    sweep_three = result.loc[result["sweep"] == 3].iloc[0]
    sweep_seven = result.loc[result["sweep"] == 7].iloc[0]
    assert np.isnan(sweep_three["isi_ms_first"])
    assert np.isnan(sweep_three["isi_ms_second"])
    assert np.isnan(sweep_three["isi_ms_last"])
    assert sweep_seven["isi_ms_first"] == 8.0
    assert sweep_seven["isi_ms_second"] == 10.0
    assert sweep_seven["isi_ms_last"] == 10.0


def test_get_stat_fi_returns_expected_empty_schema() -> None:
    """Verify an absent epoch returns an empty summary with stable columns."""
    master = pd.DataFrame(
        {
            "epoch": [1],
            "epochLevel": [10.0],
            "sweep": [0],
            "thresholdSec": [0.1],
        }
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = getStatFi(master, "thresholdSec", epochNumber=2)

    expected_columns = pd.Index(
        [
            "sweep",
            "epochLevel",
            "thresholdSec_count",
            "thresholdSec_mean",
            "thresholdSec_median",
            "thresholdSec_min",
            "thresholdSec_max",
            "thresholdSec_std",
            "thresholdSec_sem",
            "thresholdSec_first",
            "thresholdSec_second",
            "thresholdSec_last",
            "thresholdSec_1_2",
            "thresholdSec_1_n",
            "thresholdSec_cv",
            "filename",
        ]
    )
    pdt.assert_index_equal(result.columns, expected_columns)
    assert result.empty


def test_get_stat_fi_includes_all_events_without_epoch_filter() -> None:
    """Summarize every event when no numeric epoch is available."""
    master = pd.DataFrame(
        {
            "epoch": [np.nan, np.nan, np.nan],
            "epochLevel": [np.nan, np.nan, np.nan],
            "sweep": [0, 1, 1],
            "thresholdSec": [0.1, 0.2, 0.3],
        }
    )

    result = getStatFi(master, "thresholdSec", epochNumber=None)

    assert result["sweep"].tolist() == [0, 1]
    assert result["thresholdSec_count"].tolist() == [1, 2]


@pytest.mark.parametrize(
    ("selected_epoch", "num_epochs", "expected_epoch"),
    [(2, 3, 2), (2, None, "All"), ("All", 3, "All")],
    ids=["preserved", "epochs-unavailable", "all-preserved"],
)
def test_plot_fi_uses_epoch_availability_when_switching_files(
    qtbot: Any,
    monkeypatch: Any,
    selected_epoch: int | str,
    num_epochs: int | None,
    expected_epoch: int | str,
) -> None:
    """Preserve a numeric epoch only when the new recording has epochs.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
        monkeypatch: Pytest attribute replacement helper.
        selected_epoch: Plot FI epoch state before switching recordings.
        num_epochs: Epoch count reported by the new recording.
        expected_epoch: Plot FI epoch state after switching recordings.
    """
    plugin = plotFi.__new__(plotFi)
    QtWidgets.QWidget.__init__(plugin)
    qtbot.addWidget(plugin)
    plugin._epochNumber = selected_epoch
    calls: list[tuple[str, object]] = []

    def fake_base_switch(
        self: sanpyPlugin,
        ba: object,
        rowDict: dict[str, object] | None = None,
        replot: bool = True,
    ) -> None:
        """Record delegation while reproducing the shared epoch reset.

        Args:
            self: Plugin receiving the file switch.
            ba: Newly selected analysis.
            rowDict: Optional file-table state.
            replot: Whether the base implementation should redraw.
        """
        calls.append(("base", replot))
        self._epochNumber = "All"

    def fake_toolbar(self: plotFi) -> None:
        """Record toolbar synchronization after restoring the epoch.

        Args:
            self: Plot FI instance being synchronized.
        """
        calls.append(("toolbar", self.epochNumber))

    def fake_replot(self: plotFi) -> None:
        """Record the final redraw and its selected epoch.

        Args:
            self: Plot FI instance being redrawn.
        """
        calls.append(("replot", self.epochNumber))

    def fake_epoch_refresh(self: plotFi) -> None:
        """Record synchronization of Plot FI's local epoch selector.

        Args:
            self: Plot FI instance being synchronized.
        """
        calls.append(("epoch-control", self.epochNumber))

    monkeypatch.setattr(sanpyPlugin, "slot_switchFile", fake_base_switch)
    monkeypatch.setattr(plotFi, "_updateTopToolbar", fake_toolbar)
    monkeypatch.setattr(plotFi, "_refresh_fi_epoch_combo_box", fake_epoch_refresh)
    monkeypatch.setattr(plotFi, "replot", fake_replot)

    analysis = SimpleNamespace(
        fileLoader=SimpleNamespace(numEpochs=num_epochs)
    )
    plugin.slot_switchFile(analysis)

    assert plugin.epochNumber == expected_epoch
    assert calls == [
        ("base", False),
        ("toolbar", expected_epoch),
        ("epoch-control", expected_epoch),
        ("replot", expected_epoch),
    ]


def test_plot_fi_epoch_selector_lists_all_and_numeric_epochs(qtbot: Any) -> None:
    """Populate Plot FI's local selector with All followed by each epoch.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    plugin = plotFi.__new__(plotFi)
    QtWidgets.QWidget.__init__(plugin)
    qtbot.addWidget(plugin)
    plugin._blockComboBox = False
    plugin._epochNumber = 2
    plugin._ba = SimpleNamespace(fileLoader=SimpleNamespace(numEpochs=4))
    plugin._fiEpochComboBox = QtWidgets.QComboBox(plugin)
    plugin._fiEpochComboBox.currentIndexChanged.connect(
        plugin._on_fi_epoch_combo_box
    )
    plugin.replot = Mock()

    plugin._refresh_fi_epoch_combo_box()

    assert [
        plugin._fiEpochComboBox.itemText(index)
        for index in range(plugin._fiEpochComboBox.count())
    ] == ["All", "0", "1", "2", "3"]
    assert plugin._fiEpochComboBox.currentData() == 2
    # 20260912, this is way to specific for a unit test
    # assert plugin._fiEpochComboBox.minimumContentsLength() == 4
    # assert (
    #     plugin._fiEpochComboBox.view().minimumWidth()
    #     >= plugin._fiEpochComboBox.minimumSizeHint().width()
    # )

    plugin._fiEpochComboBox.setCurrentIndex(2)
    assert plugin.epochNumber == 1
    plugin._fiEpochComboBox.setCurrentIndex(0)
    assert plugin.epochNumber == "All"
    assert plugin.replot.call_count == 2


def test_plot_fi_epoch_selector_leaves_unavailable_epoch_unselected(
    qtbot: Any,
) -> None:
    """Do not silently replace an unavailable preserved epoch.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    plugin = plotFi.__new__(plotFi)
    QtWidgets.QWidget.__init__(plugin)
    qtbot.addWidget(plugin)
    plugin._blockComboBox = False
    plugin._epochNumber = 2
    plugin._ba = SimpleNamespace(fileLoader=SimpleNamespace(numEpochs=2))
    plugin._fiEpochComboBox = QtWidgets.QComboBox(plugin)

    plugin._refresh_fi_epoch_combo_box()

    assert plugin.epochNumber == 2
    assert plugin._fiEpochComboBox.currentIndex() == -1


def test_plot_fi_options_popup_stays_open_for_multiple_changes(
    qtbot: Any,
) -> None:
    """Keep the options popup open while applying embedded controls.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    plugin = plotFi.__new__(plotFi)
    QtWidgets.QWidget.__init__(plugin)
    qtbot.addWidget(plugin)
    plugin.setDefaultPlot()
    plugin.replot = Mock()
    button = plugin._buildPlotOptionsButton()
    layout = QtWidgets.QVBoxLayout(plugin)
    layout.addWidget(button)
    plugin.show()

    menu = button.menu()
    menu.popup(button.mapToGlobal(QtCore.QPoint(0, button.height())))
    qtbot.waitUntil(menu.isVisible)
    qtbot.mouseClick(plugin._rawCheckbox, QtCore.Qt.LeftButton)

    assert menu.isVisible()
    assert plugin._plotDict["Raw"] is False
    plugin.replot.assert_called_once_with()

    qtbot.keyClick(menu, QtCore.Qt.Key_Escape)
    qtbot.waitUntil(lambda: not menu.isVisible())


def test_plot_fi_clears_stale_output_for_unavailable_epoch(qtbot: Any) -> None:
    """Replace results from the prior file when its epoch is unavailable.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    plugin = plotFi.__new__(plotFi)
    QtWidgets.QWidget.__init__(plugin)
    qtbot.addWidget(plugin)
    plugin._epochNumber = 2
    plugin._ba = SimpleNamespace(
        fileLoader=SimpleNamespace(numEpochs=2),
        getFileName=lambda: "new.abf",
    )
    plugin.df_fi = pd.DataFrame({"stale": [1]})
    plugin.axs = Mock()
    plugin.axs.transAxes = object()
    plugin.static_canvas = Mock()
    plugin._fiTableView = Mock()

    plugin.replot()

    assert plugin.df_fi is None
    plugin._fiTableView.slotSwitchTableDf.assert_called_once_with(None)
    plugin.axs.text.assert_called_once()
    assert "Epoch 2 is not available" in plugin.axs.text.call_args.args
    plugin.static_canvas.draw.assert_called_once_with()


@pytest.mark.parametrize(
    "num_epochs", [None, 3], ids=["without-epochs", "all-selected"]
)
def test_plot_fi_uses_all_events_and_sweep_axis_without_epochs(
    qtbot: Any,
    num_epochs: int | None,
) -> None:
    """Plot every event by sweep without epochs or when All is selected.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
        num_epochs: Epoch count reported by the recording.
    """
    plugin = plotFi.__new__(plotFi)
    QtWidgets.QWidget.__init__(plugin)
    qtbot.addWidget(plugin)
    plugin._epochNumber = "All"
    plugin._ba = SimpleNamespace(
        fileLoader=SimpleNamespace(numEpochs=num_epochs),
        spikeDict=SimpleNamespace(
            asDataFrame=lambda: pd.DataFrame(
                {
                    "epoch": [np.nan, np.nan, np.nan],
                    "epochLevel": [np.nan, np.nan, np.nan],
                    "sweep": [0, 1, 1],
                    "spikeNumber": [0, 1, 2],
                    "thresholdSec": [0.1, 0.2, 0.3],
                }
            )
        ),
        getFileName=lambda: "new.nwb",
    )
    plugin.df_fi = pd.DataFrame({"stale": [1]})
    plugin.axs = Mock()
    plugin.axs.transAxes = object()
    plugin.axs.spines = {"right": Mock(), "top": Mock()}
    plugin.static_canvas = Mock()
    plugin._fiTableView = Mock()
    plugin._yStatListWidget = Mock()
    plugin._yStatListWidget.getCurrentStat.return_value = (
        "Threshold Time",
        "thresholdSec",
    )
    plugin.setDefaultPlot()

    plugin.replot()

    assert plugin.epochNumber == "All"
    assert plugin.df_fi["sweep"].tolist() == [0, 1]
    assert plugin.df_fi["thresholdSec_count"].tolist() == [1, 2]
    assert plugin.axs.scatter.call_args.args[:2] == ("sweep", "thresholdSec")
    assert plugin.axs.errorbar.call_args.args[:2] == (
        "sweep",
        "thresholdSec_mean",
    )
    plugin.axs.set_xlabel.assert_called_once_with("Sweep")
    table_df = plugin._fiTableView.slotSwitchTableDf.call_args.args[0]
    assert table_df is plugin.df_fi
    plugin.static_canvas.draw.assert_called_once_with()


@pytest.mark.parametrize(
    "spike_frame",
    [
        pd.DataFrame(),
        pd.DataFrame(
            {"epoch": [1], "epochLevel": [10.0], "thresholdSec": [0.1]}
        ),
    ],
    ids=["no-detected-spikes", "no-spikes-in-selected-epoch"],
)
def test_plot_fi_clears_stale_output_when_epoch_has_no_spikes(
    qtbot: Any, spike_frame: pd.DataFrame
) -> None:
    """Render a no-data message when no selected-epoch spikes are available.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
        spike_frame: New recording's per-spike analysis results.
    """
    plugin = plotFi.__new__(plotFi)
    QtWidgets.QWidget.__init__(plugin)
    qtbot.addWidget(plugin)
    plugin._epochNumber = 2
    plugin._ba = SimpleNamespace(
        fileLoader=SimpleNamespace(numEpochs=3),
        spikeDict=SimpleNamespace(asDataFrame=lambda: spike_frame),
        getFileName=lambda: "new.abf",
    )
    plugin.df_fi = pd.DataFrame({"stale": [1]})
    plugin.axs = Mock()
    plugin.axs.transAxes = object()
    plugin.static_canvas = Mock()
    plugin._fiTableView = Mock()
    plugin._yStatListWidget = Mock()
    plugin._yStatListWidget.getCurrentStat.return_value = (
        "Threshold Time",
        "thresholdSec",
    )

    plugin.replot()

    assert plugin.df_fi is None
    plugin._fiTableView.slotSwitchTableDf.assert_called_once_with(None)
    plugin.axs.text.assert_called_once()
    assert "No spikes detected in epoch 2" in plugin.axs.text.call_args.args
    plugin.static_canvas.draw.assert_called_once_with()
