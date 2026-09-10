"""Tests for Plot Scatter marker and hue rendering."""

from typing import Any

import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

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
