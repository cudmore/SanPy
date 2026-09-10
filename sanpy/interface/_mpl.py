"""Shared Matplotlib helpers for SanPy Qt widgets."""

from matplotlib.backends import backend_qtagg
from qtpy import QtCore, QtWidgets


def _make_navigation_toolbar(
    canvas: backend_qtagg.FigureCanvasQTAgg,
    parent: QtWidgets.QWidget,
) -> backend_qtagg.NavigationToolbar2QT:
    """Create a compact Matplotlib navigation toolbar.

    Args:
        canvas: Matplotlib Qt canvas controlled by the toolbar.
        parent: Qt widget that owns the toolbar.

    Returns:
        Navigation toolbar with compact icons and fixed vertical sizing.
    """
    toolbar = backend_qtagg.NavigationToolbar2QT(
        canvas, parent, coordinates=True
    )
    toolbar.setIconSize(QtCore.QSize(16, 16))
    size_policy = toolbar.sizePolicy()
    size_policy.setVerticalPolicy(QtWidgets.QSizePolicy.Fixed)
    toolbar.setSizePolicy(size_policy)
    return toolbar
