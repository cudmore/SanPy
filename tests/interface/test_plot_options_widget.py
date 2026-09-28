"""Tests for the standalone plot options checkbox panel."""

from typing import Any

import pytest
from qtpy import QtWidgets

from sanpy.interface.plot_options_widget import PlotOptionsWidget


def _checkbox_grid(
    widget: PlotOptionsWidget,
) -> list[tuple[int, int, str, bool]]:
    """Return checkbox row, column, name, and checked state.

    Args:
        widget: Plot options panel to inspect.

    Returns:
        Checkboxes in row-major order.
    """
    grid = widget.findChild(QtWidgets.QGridLayout)
    assert grid is not None
    placed: list[tuple[int, int, str, bool]] = []
    for index in range(grid.count()):
        child = grid.itemAt(index).widget()
        assert isinstance(child, QtWidgets.QCheckBox)
        row, column, _row_span, _column_span = grid.getItemPosition(index)
        placed.append((row, column, child.text(), child.isChecked()))
    placed.sort()
    return placed


def test_plot_options_grid_preserves_order_and_checks(qtbot: Any) -> None:
    """Place options left to right, then down, with the given checked state.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    widget = PlotOptionsWidget(
        [("Threshold (mV)", True), ("AP Peak (mV)", False), ("Half-Widths", True)]
    )
    qtbot.addWidget(widget)

    assert widget.findChild(QtWidgets.QGroupBox).title() == "Plot Options"
    assert _checkbox_grid(widget) == [
        (0, 0, "Threshold (mV)", True),
        (0, 1, "AP Peak (mV)", False),
        (1, 0, "Half-Widths", True),
    ]


def test_plot_option_toggle_emits_name(qtbot: Any) -> None:
    """Emit the checkbox name and its new checked state.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    widget = PlotOptionsWidget([("AP Peak (mV)", True)])
    qtbot.addWidget(widget)
    seen: list[tuple[str, bool]] = []
    widget.optionToggled.connect(
        lambda name, checked: seen.append((name, checked))
    )

    checkbox = widget.findChild(QtWidgets.QCheckBox)
    checkbox.click()

    assert seen == [("AP Peak (mV)", False)]


def test_set_checked_updates_without_emitting(qtbot: Any) -> None:
    """Let an owner synchronize a checkbox without a second toggle.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    widget = PlotOptionsWidget([("AP Peak (mV)", True)])
    qtbot.addWidget(widget)
    seen: list[tuple[str, bool]] = []
    widget.optionToggled.connect(
        lambda name, checked: seen.append((name, checked))
    )

    widget.set_checked("AP Peak (mV)", False)
    widget.set_checked("Missing", True)

    checkbox = widget.findChild(QtWidgets.QCheckBox)
    assert checkbox.isChecked() is False
    assert seen == []


def test_duplicate_plot_option_name_is_rejected() -> None:
    """Reject two options that would emit the same name."""
    with pytest.raises(ValueError, match="AP Peak"):
        PlotOptionsWidget([("AP Peak (mV)", True), ("AP Peak (mV)", False)])
