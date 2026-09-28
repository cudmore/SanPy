"""Plugin for editing experimental metadata."""

from __future__ import annotations

from functools import partial
from typing import Any

from PyQt5 import QtCore, QtWidgets

import sanpy
from sanpy.interface.plugins import sanpyPlugin


class SetMetaData(sanpyPlugin):
    """Edit schema-defined experimental metadata for the current analysis."""

    myHumanName = "Set Meta Data"
    showInMenu = False

    def __init__(self, **kwargs: Any) -> None:
        """Build the editor and display the current analysis.

        Args:
            **kwargs: Arguments forwarded to :class:`sanpyPlugin`.
        """
        super().__init__(**kwargs)
        self._widgetDict: dict[str, QtWidgets.QWidget] = {}
        self._buildUI()
        if self.ba is not None:
            self.replot()

    def replot(self) -> None:
        """Refresh controls from the current analysis metadata."""
        if self.ba is None:
            return
        for key, value in self.ba.metaData.items():
            widget = self._widgetDict[key]
            if isinstance(widget, QtWidgets.QComboBox):
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)
            elif isinstance(widget, QtWidgets.QLineEdit):
                widget.setText(value)

    def _on_text_edit(self, widget: QtWidgets.QLineEdit, key: str) -> None:
        """Store one edited free-text value.

        Args:
            widget: Line edit containing the new value.
            key: Canonical experimental-metadata key.
        """
        if self.ba is None:
            return
        value = widget.text().replace(";", ",")
        self.ba.metaData.setMetaData(key, value)

    def _on_combo_box(self, key: str, value: str) -> None:
        """Store one selected choice value.

        Args:
            key: Canonical experimental-metadata key.
            value: Canonical selected value.
        """
        if self.ba is not None:
            self.ba.metaData.setMetaData(key, value)

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

    def _buildUI(self) -> None:
        """Build one schema-driven editor row per metadata field."""
        layout = self.getVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
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
        layout.addStretch()
        for widget in self._widgetDict.values():
            self._setFontSize(widget)
