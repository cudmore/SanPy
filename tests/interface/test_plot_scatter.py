"""Tests for Plot Scatter marker and hue rendering."""

from typing import Any

import numpy as np
import pandas as pd
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from qtpy import QtWidgets

from sanpy.bAnalysisResults import get_plot_result_definitions
from sanpy.interface.bScatterPlotWidget2 import (
    bScatterPlotMainWindow,
    myStatListWidget,
)
from sanpy.interface.plugins.plotScatter import getPlotMarkersAndColors


class _ScatterAnalysis:
    """Provide the spike statistics required by the style helper."""

    def getSpikeStat(self, spike_list: list[int], stat: str) -> list[Any]:
        """Return deterministic values for one requested spike statistic.

        Args:
            spike_list: Absolute spike indices requested by the plot.
            stat: Spike-statistic name.

        Returns:
            Values aligned with ``spike_list``.

        Raises:
            KeyError: If the test does not define the requested statistic.
        """
        values = {
            "sweep": [0, 0, 3],
            "include": [True, False, True],
            "userType": [0, 1, 0],
        }
        return [values[stat][index] for index in spike_list]


class _StatWidgetParent:
    """Provide the callback required by the shared statistic widget."""

    def replot(self) -> None:
        """Accept a statistic-change callback without plotting."""


def test_stat_widget_uses_registry_labels_and_internal_keys(
    qtbot: Any,
) -> None:
    """Resolve one displayed registry label to its internal result key.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    definitions = get_plot_result_definitions()
    widget = myStatListWidget(_StatWidgetParent(), definitions)
    qtbot.addWidget(widget)

    widget.setCurrentRow("Spike frequency (Hz)")

    assert widget.getCurrentStat() == ("Spike frequency (Hz)", "spikeFreq_hz")
    assert widget.myTableWidget.rowCount() == len(definitions)


def test_plot_tool_scatter_switches_from_categorical_to_continuous_x(
    qtbot: Any,
) -> None:
    """Render a string X axis and then restore a continuous X axis."""
    dataframe = pd.DataFrame(
        {
            "File Number": [1, 1, 2, 2],
            "Include": ["yes", "yes", "yes", "yes"],
            "spike_condition": ["control", "drug", "control", "drug"],
            "thresholdSec": [1.0, 2.0, 3.0, 4.0],
            "spikeFreq_hz": [10.0, 20.0, 30.0, 40.0],
        }
    )
    definitions = {
        "thresholdSec": get_plot_result_definitions()["thresholdSec"],
        "spikeFreq_hz": get_plot_result_definitions()["spikeFreq_hz"],
        "spike_condition": {
            "axis_label": "Spike condition",
        },
    }
    window = bScatterPlotMainWindow(
        "",
        categoricalList=["File Number", "spike_condition"],
        statListDict=definitions,
        masterDf=dataframe,
    )
    qtbot.addWidget(window)

    window.slot_setStatName("X-Stat", "Spike condition")

    assert window._plotState["xStat"] == "spike_condition"
    assert window._plotState["xIsCategorical"] is True
    assert window.myPlotCanvasList[window.updatePlot].plotDf is not None

    window.slot_setStatName("X-Stat", "Threshold time (s)")

    assert window._plotState["xStat"] == "thresholdSec"
    assert window._plotState["xIsCategorical"] is False
    assert window.myPlotCanvasList[window.updatePlot].plotDf is not None


@pytest.mark.parametrize("hue", ["", "None", "Time", "Sweep"])
def test_plot_scatter_hue_styles_draw(hue: str) -> None:
    """Draw the scatter collection successfully for every hue choice.

    Args:
        hue: Hue mode exercised by the test.
    """
    analysis = _ScatterAnalysis()
    spike_list = [0, 1, 2]
    styles = getPlotMarkersAndColors(analysis, spike_list, hue)

    figure = Figure()
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_subplot()
    collection = axes.scatter([0, 1, 2], [2, 1, 0])
    collection.set_array(styles["colorMapArray"])
    collection.set_cmap(styles["cMap"])
    collection.set_color(styles["faceColors"])
    collection.set_paths(styles["pathList"])

    canvas.draw()

    assert len(collection.get_paths()) > 0
    if hue == "Sweep":
        np.testing.assert_array_equal(collection.get_array(), [0, 0, 3])
    elif hue == "Time":
        np.testing.assert_array_equal(collection.get_array(), [0, 1, 2])
