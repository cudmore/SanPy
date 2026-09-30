"""Display read-only recording metadata."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from PyQt5 import QtCore, QtWidgets

from sanpy.fileloaders.fileMetadata import FileMetadata
from sanpy.interface.plugins.sanpyPlugin import ResponseType, sanpyPlugin


class FileMetadataView(sanpyPlugin):
    """Display read-only file metadata."""

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
        layout = self.getVBoxLayout()

        title = QtWidgets.QLabel("File Metadata")
        title_font = title.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)


        form = QtWidgets.QFormLayout()
        form.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        for metadata_field in fields(FileMetadata):
            display_name = str(
                metadata_field.metadata.get("display_name", metadata_field.name)
            )
            value_label = QtWidgets.QLabel("")
            value_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            value_label.setWordWrap(True)
            self._valueLabels[metadata_field.name] = value_label
            form.addRow(display_name, value_label)
        layout.addLayout(form)
        layout.addStretch()
        self.replot()

    def replot(self) -> None:
        """Refresh displayed values from the selected recording."""
        metadata = None if self.ba is None else self.ba.fileLoader.fileMetadata
        for field_name, value_label in self._valueLabels.items():
            value = "" if metadata is None else getattr(metadata, field_name)
            value_label.setText(str(value))
