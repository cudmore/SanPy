"""Tests for pandas-backed Plot FI summary calculations."""

import warnings
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest
from qtpy import QtWidgets

from sanpy.interface.plugins.plotFi import getStatFi, plotFi
from sanpy.interface.plugins.sanpyPlugin import sanpyPlugin


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


def test_plot_fi_preserves_epoch_when_switching_files(
    qtbot: Any, monkeypatch: Any
) -> None:
    """Keep Plot FI's numeric epoch while delegating shared switch behavior.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
        monkeypatch: Pytest attribute replacement helper.
    """
    plugin = plotFi.__new__(plotFi)
    QtWidgets.QWidget.__init__(plugin)
    qtbot.addWidget(plugin)
    plugin._epochNumber = 2
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

    monkeypatch.setattr(sanpyPlugin, "slot_switchFile", fake_base_switch)
    monkeypatch.setattr(plotFi, "_updateTopToolbar", fake_toolbar)
    monkeypatch.setattr(plotFi, "replot", fake_replot)

    plugin.slot_switchFile(SimpleNamespace())

    assert plugin.epochNumber == 2
    assert calls == [("base", False), ("toolbar", 2), ("replot", 2)]


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
