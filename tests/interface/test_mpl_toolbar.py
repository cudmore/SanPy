"""Tests for compact Matplotlib toolbars shared by SanPy widgets."""

from typing import Any

import numpy as np
from qtpy import QtCore, QtWidgets

from sanpy.interface.bExportWidget import bExportWidget
from sanpy.interface.bScatterPlotWidget2 import myMplCanvas, plotState


def _assert_compact_toolbar(
    toolbar: QtWidgets.QToolBar, parent: QtWidgets.QWidget
) -> None:
    """Assert that a toolbar uses SanPy's shared compact configuration.

    Args:
        toolbar: Matplotlib toolbar to inspect.
        parent: Expected Qt owner of the toolbar.
    """
    assert toolbar.parent() is parent
    assert toolbar.iconSize() == QtCore.QSize(16, 16)
    assert toolbar.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Fixed


def test_export_trace_uses_compact_toolbar(qtbot: Any) -> None:
    """Use the shared compact toolbar in Export Trace.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    widget = bExportWidget(
        np.array([0.0, 1.0]), np.array([0.0, 1.0])
    )
    qtbot.addWidget(widget)

    _assert_compact_toolbar(widget.toolbar, widget)


def test_plot_tools_use_compact_toolbar(qtbot: Any) -> None:
    """Use the shared compact toolbar in Plot Tool and Plot Tool (pool).

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    widget = myMplCanvas(plotState(0))
    qtbot.addWidget(widget)

    _assert_compact_toolbar(widget.mplToolbar, widget)
