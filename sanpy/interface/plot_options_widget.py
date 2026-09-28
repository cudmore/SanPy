"""Checkbox panel for turning named plot overlays on and off.

The widget draws the options. The owner decides what a checked name means.
"""

from qtpy import QtCore, QtWidgets

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class PlotOptionsWidget(QtWidgets.QWidget):
    """Show named overlay choices in a two-column checkbox grid.

    Attributes:
        optionToggled: Emitted with the option name and checked state when
            the user clicks a checkbox.
    """

    optionToggled = QtCore.Signal(str, bool)

    def __init__(
        self,
        options: list[tuple[str, bool]],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Build the Plot Options group from an ordered list of options.

        Args:
            options: Option name and initial checked state, in display order.
                Names must be unique.
            parent: Optional owning Qt widget.

        Raises:
            ValueError: If an option name is duplicated.
        """
        super().__init__(parent)
        self._checkboxes: dict[str, QtWidgets.QCheckBox] = {}

        group = QtWidgets.QGroupBox("Plot Options", self)
        grid = QtWidgets.QGridLayout(group)
        grid.setContentsMargins(4, 4, 0, 0)

        row = 0
        col = 0
        for name, checked in options:
            if name in self._checkboxes:
                raise ValueError(f'Duplicate plot option name: "{name}"')
            checkbox = QtWidgets.QCheckBox(name, group)
            checkbox.setChecked(checked)
            checkbox.toggled.connect(self._on_checkbox_toggled)
            grid.addWidget(checkbox, row, col)
            self._checkboxes[name] = checkbox
            col += 1
            if col == 2:
                col = 0
                row += 1

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(group)

    def set_checked(self, name: str, checked: bool) -> None:
        """Set one checkbox without emitting ``optionToggled``.

        Args:
            name: Option name passed to the constructor.
            checked: New checked state.
        """
        checkbox = self._checkboxes.get(name)
        if checkbox is None:
            logger.error(f'Unknown plot option "{name}".')
            return
        checkbox.blockSignals(True)
        checkbox.setChecked(checked)
        checkbox.blockSignals(False)

    def _on_checkbox_toggled(self, checked: bool) -> None:
        """Emit the checkbox name and its new checked state.

        Args:
            checked: Whether the user turned that option on.
        """
        checkbox = self.sender()
        if not isinstance(checkbox, QtWidgets.QCheckBox):
            logger.error("Plot option toggle did not come from a checkbox.")
            return
        self.optionToggled.emit(checkbox.text(), checked)
