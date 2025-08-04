from functools import partial
from typing import Any

from PyQt5 import QtGui, QtCore, QtWidgets
import numpy as np
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QSpinBox,
    QCheckBox,
    QDoubleSpinBox,
)
from PyQt5.QtCore import pyqtSignal

from sanpy.kym.kymRoiMetaData import KymRoiMetaData
from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


class MetaDataWidget(QtWidgets.QWidget):
    def __init__(self, kymRoiMetaData: KymRoiMetaData):
        super().__init__()

        self._kymRoiMetaData = kymRoiMetaData

        self._buildUI()

    def _buildUI(self):
        vBox = QtWidgets.QVBoxLayout()
        vBox.setContentsMargins(0, 0, 0, 0)
        vBox.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(vBox)

        for key, v in self._kymRoiMetaData.items():
            if not self._kymRoiMetaData.showInGui(key):
                continue

            hBox = QtWidgets.QHBoxLayout()
            hBox.setAlignment(QtCore.Qt.AlignLeft)
            vBox.addLayout(hBox)

            aLabel = QtWidgets.QLabel(key)
            hBox.addWidget(aLabel)

            _allowEdit = self._kymRoiMetaData.allowTextEdit(key)
            if _allowEdit:
                # Create type-appropriate widget
                widget = self._create_widget_for_field(key, v)
                hBox.addWidget(widget)
            else:
                vStr = str(v)
                aLabel = QtWidgets.QLabel(vStr)
                hBox.addWidget(aLabel)

    def _create_widget_for_field(self, key: str, value: Any) -> QtWidgets.QWidget:
        """Create appropriate widget based on field type."""
        field_name = self._kymRoiMetaData._get_field_name(key)
        field_type = self._kymRoiMetaData._fields.__dataclass_fields__[field_name].type
        
        if field_type == bool:
            return self._create_checkbox(key, value)
        elif field_type == int:
            return self._create_spinbox(key, value)
        elif field_type == float:
            return self._create_double_spinbox(key, value)
        elif field_type == str:
            return self._create_lineedit(key, value)
        else:
            # Fallback to string for unknown types
            logger.warning(f'Unknown field type {field_type} for key {key}, using QLineEdit')
            return self._create_lineedit(key, value)

    def _create_lineedit(self, key: str, value: Any) -> QtWidgets.QLineEdit:
        """Create QLineEdit for string fields."""
        widget = QtWidgets.QLineEdit(str(value))
        widget.editingFinished.connect(
            partial(self.on_text_edit, widget, key)
        )
        return widget

    def _create_spinbox(self, key: str, value: Any) -> QtWidgets.QSpinBox:
        """Create QSpinBox for integer fields."""
        widget = QtWidgets.QSpinBox()
        widget.setRange(-999999, 999999)  # Reasonable range for metadata
        widget.setValue(int(value) if value is not None else 0)
        widget.valueChanged.connect(
            partial(self.on_int_edit, widget, key)
        )
        return widget

    def _create_double_spinbox(self, key: str, value: Any) -> QtWidgets.QDoubleSpinBox:
        """Create QDoubleSpinBox for float fields."""
        widget = QtWidgets.QDoubleSpinBox()
        widget.setRange(-999999.0, 999999.0)  # Reasonable range for metadata
        widget.setDecimals(6)  # Allow 6 decimal places
        widget.setValue(float(value) if value is not None else 0.0)
        widget.valueChanged.connect(
            partial(self.on_float_edit, widget, key)
        )
        return widget

    def _create_checkbox(self, key: str, value: Any) -> QtWidgets.QCheckBox:
        """Create QCheckBox for boolean fields."""
        widget = QtWidgets.QCheckBox()
        widget.setChecked(bool(value) if value is not None else False)
        widget.toggled.connect(
            partial(self.on_bool_edit, widget, key)
        )
        return widget

    def on_text_edit(self, aWidget, key):
        """Handle text field changes."""
        strValue = aWidget.text()
        logger.info(f'key:"{key}" strValue:{strValue}')
        self._kymRoiMetaData.setParam(key, strValue)

    def on_int_edit(self, aWidget, key):
        """Handle integer field changes."""
        intValue = aWidget.value()
        logger.info(f'key:"{key}" intValue:{intValue}')
        self._kymRoiMetaData.setParam(key, intValue)

    def on_float_edit(self, aWidget, key):
        """Handle float field changes."""
        floatValue = aWidget.value()
        logger.info(f'key:"{key}" floatValue:{floatValue}')
        self._kymRoiMetaData.setParam(key, floatValue)

    def on_bool_edit(self, aWidget, key):
        """Handle boolean field changes."""
        boolValue = aWidget.isChecked()
        logger.info(f'key:"{key}" boolValue:{boolValue}')
        self._kymRoiMetaData.setParam(key, boolValue)
