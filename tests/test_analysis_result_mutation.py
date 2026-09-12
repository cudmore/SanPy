"""Tests for explicit mutation of per-spike analysis results."""

from typing import Any

import pandas as pd
from qtpy import QtWidgets

from sanpy.bAnalysisResults import analysisResultList, get_plot_result_definitions
from sanpy.bAnalysis_ import bAnalysis
from sanpy.interface.bScatterPlotWidget2 import bScatterPlotMainWindow, plotState
from sanpy.interface.plugins.setSpikeStat import EDITABLE_SPIKE_RESULTS


def _analysis_with_two_spikes() -> bAnalysis:
    """Create a minimal analysis instance with two result records.

    Returns:
        Analysis instance suitable for exercising ``setSpikeStat``.
    """
    analysis = bAnalysis.__new__(bAnalysis)
    analysis.spikeDict = analysisResultList()
    analysis.spikeDict.appendDefault()
    analysis.spikeDict.appendDefault()
    analysis._detectionDirty = False
    return analysis


def test_set_spike_stat_updates_annotation_fields() -> None:
    """Set each field exposed by the Detection Panel's Set Spikes view."""
    analysis = _analysis_with_two_spikes()

    analysis.setSpikeStat([0, 1], "spike_condition", "drug")
    analysis.setSpikeStat([0, 1], "userType", 3)
    analysis.setSpikeStat([0, 1], "include", False)

    assert EDITABLE_SPIKE_RESULTS == ("spike_condition", "userType", "include")
    for spike in analysis.spikeDict:
        assert spike["spike_condition"] == "drug"
        assert spike["condition"] == ""
        assert spike["userType"] == 3
        assert spike["include"] is False
        assert spike["modDate"]
        assert spike["modTime"]
    assert analysis._detectionDirty


def test_set_spike_stat_accepts_one_integer_index() -> None:
    """Update one spike when the caller supplies a scalar spike index."""
    analysis = _analysis_with_two_spikes()

    analysis.setSpikeStat(1, "spike_condition", "control")

    assert analysis.spikeDict[0]["spike_condition"] == ""
    assert analysis.spikeDict[1]["spike_condition"] == "control"


def test_analysis_result_filtering_combines_sweep_and_epoch() -> None:
    """Return only spikes matching both Plot Scatter toolbar filters."""
    analysis = _analysis_with_two_spikes()
    analysis.spikeDict[0]["sweep"] = 0
    analysis.spikeDict[0]["epoch"] = 1
    analysis.spikeDict[0]["thresholdSec"] = 1.0
    analysis.spikeDict[1]["sweep"] = 1
    analysis.spikeDict[1]["epoch"] = 2
    analysis.spikeDict[1]["thresholdSec"] = 2.0

    assert analysis.getStat("thresholdSec", sweepNumber="All", epochNumber="All") == [
        1.0,
        2.0,
    ]
    assert analysis.getStat("thresholdSec", sweepNumber=1, epochNumber="All") == [
        2.0
    ]
    assert analysis.getStat("thresholdSec", sweepNumber="All", epochNumber=1) == [
        1.0
    ]
    assert analysis.getStat("thresholdSec", sweepNumber=1, epochNumber=2) == [2.0]


def test_plot_summary_supports_categorical_then_continuous_x_axis(
    qtbot: Any,
) -> None:
    """Avoid string means without poisoning subsequent stat selections."""
    window = bScatterPlotMainWindow.__new__(bScatterPlotMainWindow)
    QtWidgets.QMainWindow.__init__(window)
    qtbot.addWidget(window)
    window.masterDf = pd.DataFrame(
        {
            "File Number": [1, 1, 1, 1],
            "Include": ["yes", "yes", "yes", "yes"],
            "spike_condition": ["control", "control", "drug", "drug"],
            "thresholdSec": [1.0, 2.0, 3.0, 4.0],
            "spikeFreq_hz": [10.0, 20.0, 30.0, 40.0],
        }
    )
    window.masterCatColumns = ["File Number", "spike_condition"]
    window.statListDict = get_plot_result_definitions()
    window.sortOrder = None
    window.xDf = None
    window.yDf = None
    window._plotState = plotState(plotIndex=0)
    window._plotState.setState("xStat", "spike_condition")
    window._plotState.setState("yStat", "spikeFreq_hz")

    _, _, categorical_mean = window.getMeanDf()

    assert categorical_mean is not None
    assert categorical_mean["spike_condition"].tolist() == ["control", "drug"]
    assert categorical_mean["spikeFreq_hz"].tolist() == [15.0, 35.0]

    window._plotState.setState("xStat", "thresholdSec")
    _, _, continuous_mean = window.getMeanDf()

    assert continuous_mean is not None
    assert continuous_mean["thresholdSec"].tolist() == [2.5]
    assert continuous_mean["spikeFreq_hz"].tolist() == [25.0]
