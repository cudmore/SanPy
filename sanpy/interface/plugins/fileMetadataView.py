"""Display recording metadata and editable per-sweep conditions."""

from __future__ import annotations

from dataclasses import fields
from functools import partial
from typing import Any

from PyQt5 import QtCore, QtWidgets

from sanpy.fileloaders.fileMetadata import FileMetadata
from sanpy.interface.plugins.sanpyPlugin import ResponseType, sanpyPlugin


class FileMetadataView(sanpyPlugin):
    """Display read-only file metadata and editable sweep conditions."""

    myHumanName = "File Metadata"
    showInMenu = True

    def __init__(self, **kwargs: Any) -> None:
        """Build the metadata form and show the current recording.

        Args:
            **kwargs: Arguments forwarded to :class:`sanpyPlugin`.
        """
        super().__init__(**kwargs)
        for response_type in self.responseTypes:
            self.toggleResponseOptions(response_type, False)
        self.toggleResponseOptions(ResponseType.switchFile, True)

        self._valueLabels: dict[str, QtWidgets.QLabel] = {}
        form = QtWidgets.QFormLayout()
        for metadata_field in fields(FileMetadata):
            display_name = str(
                metadata_field.metadata.get("display_name", metadata_field.name)
            )
            value_label = QtWidgets.QLabel("")
            value_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            value_label.setWordWrap(True)
            self._valueLabels[metadata_field.name] = value_label
            form.addRow(display_name, value_label)
        self.getVBoxLayout().addLayout(form)

        self._sweepConditionEdits: dict[int, QtWidgets.QLineEdit] = {}
        self._sweepConditionsGroup = QtWidgets.QGroupBox("Sweep Conditions")
        self._sweepConditionsForm = QtWidgets.QFormLayout(
            self._sweepConditionsGroup
        )
        self.getVBoxLayout().addWidget(self._sweepConditionsGroup)
        self.getVBoxLayout().addStretch()
        self.replot()

    def replot(self) -> None:
        """Refresh displayed values from the selected recording."""
        metadata = None if self.ba is None else self.ba.fileLoader.fileMetadata
        for field_name, value_label in self._valueLabels.items():
            value = "" if metadata is None else getattr(metadata, field_name)
            value_label.setText(str(value))
        self._rebuildSweepConditionRows()

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
