"""Plugin for editing experimental metadata and sweep conditions."""

from __future__ import annotations

from functools import partial
from typing import Any

from PyQt5 import QtCore, QtWidgets

import sanpy
from sanpy.interface.plugins import sanpyPlugin


class SetMetaData(sanpyPlugin):
    """Edit experimental metadata and per-sweep conditions for the current analysis."""

    myHumanName = "Set Meta Data"
    showInMenu = False

    def __init__(self, **kwargs: Any) -> None:
        """Build the editor and display the current analysis.

        Args:
            **kwargs: Arguments forwarded to :class:`sanpyPlugin`.
        """
        super().__init__(**kwargs)
        self._widgetDict: dict[str, QtWidgets.QWidget] = {}
        self._sweepConditionEdits: dict[int, QtWidgets.QLineEdit] = {}
        self._buildUI()
        self.replot()

    def replot(self) -> None:
        """Refresh metadata editors and sweep-condition rows."""
        self._rebuildSweepConditionRows()
        if self.ba is None:
            return
        for key, value in self.ba.metaData.items():
            widget = self._widgetDict[key]
            widget.blockSignals(True)
            try:
                if isinstance(widget, QtWidgets.QComboBox):
                    index = widget.findData(value)
                    if index >= 0:
                        widget.setCurrentIndex(index)
                elif isinstance(widget, QtWidgets.QLineEdit):
                    widget.setText(value)
            finally:
                widget.blockSignals(False)

    def slot_metaDataChanged(self, event: dict[str, Any]) -> None:
        """Refill controls after metadata is stored for this analysis.

        Args:
            event: Payload with ``ba``, ``key``, and ``value``.
        """
        if self.ba is None or not self._widgetDict or event.get("ba") is not self.ba:
            return
        self.replot()

    def _store_meta_data(self, key: str, value: str) -> None:
        """Ask the window to store one experimental metadata value.

        Args:
            key: Canonical experimental-metadata key.
            value: New string value.
        """
        window = self.getSanPyWindow()
        if window is None or self.ba is None:
            return
        window.slot_setMetaData(self.ba, key, value)

    def _on_text_edit(self, widget: QtWidgets.QLineEdit, key: str) -> None:
        """Store one edited free-text value.

        Args:
            widget: Line edit containing the new value.
            key: Canonical experimental-metadata key.
        """
        self._store_meta_data(key, widget.text().replace(";", ","))

    def _on_combo_box(self, key: str, value: str) -> None:
        """Store one selected choice value.

        Args:
            key: Canonical experimental-metadata key.
            value: Canonical selected value.
        """
        self._store_meta_data(key, value)

    def _setFontSize(self, widget: QtWidgets.QWidget) -> None:
        """Apply the plugin's compact control font.

        Args:
            widget: Widget to resize.
        """
        font_size = 12
        font = widget.font()
        font.setPointSize(font_size)
        widget.setFont(font)
        widget.setMinimumSize(5, font_size + int(font_size / 2))

    def _rebuildSweepConditionRows(self) -> None:
        """Rebuild sweep-condition editors for the selected recording."""
        for condition_edit in self._sweepConditionEdits.values():
            condition_edit.blockSignals(True)
        while self._sweepConditionsForm.rowCount() > 0:
            self._sweepConditionsForm.removeRow(0)
        self._sweepConditionEdits.clear()

        if self.ba is None or self.ba.fileLoader.sweepList is None:
            self._sweepConditionsGroup.setEnabled(False)
            return

        self._sweepConditionsGroup.setEnabled(True)
        for sweep in self.ba.fileLoader.sweepList:
            condition_edit = QtWidgets.QLineEdit(
                self.ba.fileLoader.getSweepCondition(sweep)
            )
            condition_edit.editingFinished.connect(
                partial(self._setSweepCondition, sweep, condition_edit)
            )
            self._sweepConditionEdits[sweep] = condition_edit
            self._sweepConditionsForm.addRow(str(sweep), condition_edit)

    def _setSweepCondition(
        self, sweep: int, condition_edit: QtWidgets.QLineEdit
    ) -> None:
        """Store an edited condition on the selected recording's loader.

        Args:
            sweep: Sweep index associated with the editor.
            condition_edit: Editor containing the new condition value.
        """
        if self.ba is None:
            return
        self.ba.fileLoader.setSweepCondition(sweep, condition_edit.text())

    def _buildUI(self) -> None:
        """Build the panel title, metadata editors, and sweep-condition group."""
        layout = self.getVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        title = QtWidgets.QLabel("Experimental Metadata")
        title_font = title.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        definitions = sanpy.MetaData.getMetaDataDefinitions()
        for key, definition in definitions.items():
            row = QtWidgets.QHBoxLayout()
            label = QtWidgets.QLabel(str(definition["display_name"]))
            self._setFontSize(label)
            row.addWidget(label, alignment=QtCore.Qt.AlignLeft)
            choices = definition.get("choices")
            if isinstance(choices, list):
                widget = QtWidgets.QComboBox()
                for choice in choices:
                    value = str(choice)
                    widget.addItem(value.replace("_", " ").capitalize(), value)
                widget.currentIndexChanged.connect(
                    lambda _index, combo=widget, field=key: self._on_combo_box(
                        field, str(combo.currentData())
                    )
                )
            else:
                widget = QtWidgets.QLineEdit("")
                widget.editingFinished.connect(
                    partial(self._on_text_edit, widget, key)
                )
            self._widgetDict[key] = widget
            row.addWidget(widget, alignment=QtCore.Qt.AlignLeft)
            layout.addLayout(row)
        self._sweepConditionsGroup = QtWidgets.QGroupBox("Sweep Conditions")
        self._sweepConditionsForm = QtWidgets.QFormLayout(
            self._sweepConditionsGroup
        )
        layout.addWidget(self._sweepConditionsGroup)
        layout.addStretch()
        for widget in self._widgetDict.values():
            self._setFontSize(widget)
