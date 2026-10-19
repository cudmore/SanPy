import math
import os
from functools import partial
import json
from types import UnionType
from typing import Any, Optional, get_args, get_origin

from PyQt5 import QtCore, QtWidgets, QtGui

import sanpy
from pydantic import ValidationError

from sanpy.bDetection import DetectionParameters, detectionTypes_
from sanpy.interface.plugins import sanpyPlugin
from sanpy.schema import DetectionParameterCategory

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


def _editor_type(annotation: Any) -> tuple[str | type[detectionTypes_], bool]:
    """Resolve a model annotation into the editor's supported control type.

    Args:
        annotation: Detection model field annotation.

    Returns:
        The scalar control type and whether the field accepts ``None``.

    Raises:
        TypeError: If the annotation has no supported editor control.
    """
    arguments = get_args(annotation)
    allow_none = get_origin(annotation) is UnionType and type(None) in arguments
    base = next((item for item in arguments if item is not type(None)), annotation)
    mapping: dict[Any, str | type[detectionTypes_]] = {
        str: "string",
        bool: "boolean",
        int: "int",
        float: "float",
        detectionTypes_: detectionTypes_,
    }
    if get_origin(base) is list:
        return "list", allow_none
    if base not in mapping:
        raise TypeError(f"Unsupported detection parameter annotation: {annotation}")
    return mapping[base], allow_none


def _display_value(value: Any) -> Any:
    """Convert a typed model value into its Qt display representation.

    Args:
        value: Typed detection parameter value.

    Returns:
        Enum values as their stored strings; all other values unchanged.
    """
    return value.value if isinstance(value, detectionTypes_) else value


class detectionParams(sanpyPlugin):
    """
    Plugin to display overview of detection parameters for analysis.
    """

    myHumanName = "Detection Parameters"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the detection-parameter editor.

        Args:
            **kwargs: Plugin initialization arguments forwarded to the base class.
        """
        super().__init__(**kwargs)

        logger.info("")

        # this is a class that holds all premade and loaded presets
        # it exists when runnin the sanpy app
        # if not running sanpy app then build it here (for debuggin)
        self._detectionObject: sanpy.bDetection | None = None

        detection_values: dict[str, Any] | None = None
        _currentDetectionName: str | None = None

        _sanPyApp = self.getSanPyApp()
        if _sanPyApp is not None:
            self._detectionObject = _sanPyApp.getDetectionClass()
        else:
            self._detectionObject = sanpy.bDetection()

        # get from ba
        if self.ba is not None:
            # get the ba detection dict
            # only exists if analysis has been performed
            detection_values = self.ba.getDetectionDict(asCopy=True)

        # or, get from app
        if detection_values is None:
            # ba is either None or does not have detection yet
            # get the list
            presetList = self._detectionObject.getDetectionPresetList()
            # select first in list
            _currentDetectionName = presetList[0]
            detection_values = self._detectionObject.getDetectionDict(
                _currentDetectionName
            )

        # deep copy because we are modifying this
        # do not want to change ba (for example) until we detect
        self._detection_parameters = DetectionParameters.from_saved(detection_values)

        # the name of the detection dict in ba OR the first detection type in detection class
        _currentDetectionName = self._detection_parameters.detectionName
        self._currentDetectionName = _currentDetectionName

        self._qLabelRed = "QLabel { background-color : #999922;}"
        self._qLabelBackground = "QLabel { background-color : #222222;}"

        self.buildUI()

        # self.insertIntoScrollArea()

    def buildUI(self) -> None:
        """Build the plugin controls and parameter scroll area."""
        self.vLayout = QtWidgets.QVBoxLayout()

        # top controls
        hControlLayout0 = QtWidgets.QHBoxLayout()
        hControlLayout = QtWidgets.QHBoxLayout()

        fileName = "None"
        if self.ba is not None:
            fileName = self.ba.fileLoader.filename
        self.fileNameLabel = QtWidgets.QLabel(f"File: {fileName}")
        hControlLayout0.addWidget(self.fileNameLabel, alignment=QtCore.Qt.AlignLeft)

        aName = "Detect"
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton, alignment=QtCore.Qt.AlignLeft)

        aName = "Set Defaults"
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton, alignment=QtCore.Qt.AlignLeft)

        # Fill before connecting so this does not reload the preset and
        # replace parameters already taken from an analyzed file.
        self._presetCombo = QtWidgets.QComboBox()
        self._fillPresetCombo(self._currentDetectionName)
        self._presetCombo.currentTextChanged.connect(self.on_select_detection_preset)
        hControlLayout.addWidget(self._presetCombo, alignment=QtCore.Qt.AlignLeft)

        aName = "Save Params"
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton, alignment=QtCore.Qt.AlignLeft)

        hControlLayout.addStretch()

        self.vLayout.addLayout(hControlLayout0)
        self.vLayout.addLayout(hControlLayout)

        self.vLayoutParams = self.buildUI_2()
        self.vLayout.addLayout(self.vLayoutParams)

        # scroll area again
        self._tmpWidget = QtWidgets.QWidget()
        self._tmpWidget.setLayout(self.vLayout)

        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self._tmpWidget)

        self.finalLayout = QtWidgets.QVBoxLayout()
        self.finalLayout.addWidget(self.scrollArea)

        # finalize
        # self.setLayout(self.finalLayout)
        _vBoxLayout = self.getVBoxLayout()
        _vBoxLayout.addLayout(self.finalLayout)

    def buildUI_2(self) -> QtWidgets.QGridLayout:
        """Build a control for each detection parameter shown in the editor.

        Visible parameters are placed in one section per
        ``DetectionParameterCategory``, in enum order. Parameters keep their
        definition order inside a section.

        Returns:
            Grid layout holding one header and one row of controls per visible
            parameter.
        """
        analysisDirDict = sanpy.analysisDir.sanpyColumns

        fields = DetectionParameters.model_fields
        compare_parameters = self._getCompareParameters()

        grouped: dict[DetectionParameterCategory, list[tuple[str, Any]]] = {
            category: [] for category in DetectionParameterCategory
        }
        for key, field in fields.items():
            metadata = field.json_schema_extra or {}
            if not metadata["x-show-in-editor"]:
                continue
            grouped[DetectionParameterCategory(metadata["x-category"])].append((key, field))

        vLayoutParams = QtWidgets.QGridLayout()

        self.widgetDict = {}  # list of widgets we are displaying

        row = 0
        col = 0
        rowSpan = 1
        colSpan = 1
        for category, parameters in grouped.items():
            if not parameters:
                continue

            header = QtWidgets.QLabel(category.value.capitalize())
            headerFont = header.font()
            headerFont.setBold(True)
            if headerFont.pointSize() > 0:
                headerFont.setPointSize(headerFont.pointSize() + 2)
            header.setFont(headerFont)
            vLayoutParams.addWidget(header, row, 0, rowSpan, 6)
            row += 1

            for k, v in parameters:
                col = 0

                try:
                    currentValue = _display_value(
                        self._detection_parameters.get_value(k)
                    )
                except (KeyError) as e:
                    logger.error('did not find key "{k}" in _detectionDict')
                    continue
                # k is the name in spike dictionary
                paramName = k
                metadata = v.json_schema_extra or {}
                valueType, allowNone = _editor_type(v.annotation)
                units = metadata["x-units"]
                humanName = v.title
                description = v.description

                inAnalysisDir = paramName in analysisDirDict.keys()

                # add an '*' for params in main file table keys/columns
                aName = " "
                if inAnalysisDir:
                    aName = "*"
                nameLabel = QtWidgets.QLabel(
                    aName
                )  # added to list so we can later set color
                col += 1

                humanNameLabel = QtWidgets.QLabel(humanName)
                vLayoutParams.addWidget(nameLabel, row, col, rowSpan, colSpan)
                if (
                    compare_parameters is not None
                    and currentValue
                    != _display_value(compare_parameters.get_value(paramName))
                ):
                    humanNameLabel.setStyleSheet(self._qLabelRed)
                vLayoutParams.addWidget(humanNameLabel, row, col, rowSpan, colSpan)
                col += 1

                aWidget = None
                if valueType == "int":
                    aWidget = QtWidgets.QSpinBox()
                    aWidget.setRange(
                        0, 2**16
                    )  # minimum is used for setSpecialValueText()
                    aWidget.setSpecialValueText(
                        "None"
                    )  # displayed when widget is set to minimum
                    if currentValue is None:
                        aWidget.setValue(0)
                    # elif math.isnan(currentValue):
                    #     pass
                    else:
                        currentValue = int(currentValue)
                        aWidget.setValue(currentValue)
                    aWidget.setKeyboardTracking(False)  # don't trigger signal as user edits
                    aWidget.valueChanged.connect(partial(self.on_spin_box, paramName))
                elif valueType == "float":
                    aWidget = QtWidgets.QDoubleSpinBox()
                    aWidget.setRange(
                        -1e9, +1e9
                    )  # minimum is used for setSpecialValueText()
                    aWidget.setSpecialValueText(
                        "None"
                    )  # displayed when widget is set to minimum

                    if currentValue is None or math.isnan(currentValue):
                        aWidget.setValue(-1e9)
                    else:
                        aWidget.setValue(currentValue)
                    aWidget.setKeyboardTracking(False)  # don't trigger signal as user edits
                    aWidget.valueChanged.connect(partial(self.on_spin_box, paramName))
                elif valueType == "list":
                    # text edit a list
                    pass
                elif valueType in ["bool", "boolean"]:
                    # popup of True/False
                    aWidget = QtWidgets.QComboBox()
                    aWidget.addItem("True")
                    aWidget.addItem("False")
                    aWidget.setCurrentText(str(currentValue))
                    aWidget.currentTextChanged.connect(
                        partial(self.on_bool_combo_box, paramName)
                    )
                elif valueType == "string":
                    # text edit
                    aWidget = QtWidgets.QLineEdit(currentValue)
                    # logger.info(f'paramName:{paramName}')
                    _allow_edit = paramName == 'userSaveName'  # abb so user can specify name to save
                    aWidget.setReadOnly(not _allow_edit)
                    # aWidget.setKeyboardTracking(False) # don't trigger signal as user edits
                    # aWidget.setValidator(QIntValidator())
                    # aWidget.setMaxLength(4)
                    aWidget.setAlignment(QtCore.Qt.AlignLeft)
                    aWidget.editingFinished.connect(
                        partial(self.on_text_edit, aWidget, paramName)
                    )
                elif valueType is detectionTypes_:
                    aWidget = QtWidgets.QComboBox()
                    detectionTypes = sanpy.bDetection.detectionTypes
                    for theType in detectionTypes:
                        aWidget.addItem(theType.name)
                    aWidget.setCurrentText(str(currentValue))
                    aWidget.currentTextChanged.connect(
                        partial(self.on_detection_type_combo_box, paramName)
                    )
                else:
                    logger.error(
                        f'Did not understand valueType:"{valueType}" for parameter:"{paramName}"'
                    )

                if aWidget is not None:
                    # keep track of what we are displaying
                    # used to we can get default value (form 'key' and set label to red
                    self.widgetDict[paramName] = {
                        "widget": aWidget,
                        "nameLabelWidget": humanNameLabel,
                    }

                    vLayoutParams.addWidget(aWidget, row, col, rowSpan, colSpan)
                #
                col += 1

                # units
                aLabel = QtWidgets.QLabel(units)
                vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
                col += 1

                # add a 'None' button for detection parameters that allow it
                if allowNone:
                    aName = f"{paramName}_none"
                    aButton = QtWidgets.QPushButton("Set None")
                    aButton.clicked.connect(partial(self.on_button_click, aName))
                    vLayoutParams.addWidget(aButton, row, col, rowSpan, colSpan)
                #
                col += 1

                aLabel = QtWidgets.QLabel(description)
                vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)

                #
                row += 1
        #
        return vLayoutParams

    def _getCompareParameters(self) -> DetectionParameters | None:
        """Return the parent preset model used for label highlighting.

        Core presets never highlight. User presets compare against the core
        preset named by ``detectionName``.

        Returns:
            Parent core-preset parameter model, or ``None`` when the
            selected preset is a core preset.
        """
        if not self._detectionObject.isUserPreset(self._currentDetectionName):
            return None
        parent_name = self._detection_parameters.detectionName
        values = self._detectionObject.getDetectionDict(parent_name)
        return DetectionParameters.from_saved(values)

    def _set_parameter(self, detection_param: str, value: Any) -> bool:
        """Strictly validate and apply one editor value.

        Args:
            detection_param: Detection model field name.
            value: Proposed field value.

        Returns:
            True when the value was applied, otherwise False.
        """
        logger.info(
            f'Setting detection parameter "{detection_param}" to "{value}" type:{type(value)}'
        )
        if value == -1e9:
            value = None
        try:
            self._detection_parameters = self._detection_parameters.with_value(
                detection_param, value
            )
        except (KeyError, ValueError, ValidationError) as error:
            logger.warning(f'Invalid value for "{detection_param}": {error}')
            self.replot()
            return False

        compare_parameters = self._getCompareParameters()
        aLabel = self.widgetDict[detection_param]["nameLabelWidget"]
        if (
            compare_parameters is not None
            and _display_value(value)
            != _display_value(compare_parameters.get_value(detection_param))
        ):
            aLabel.setStyleSheet(self._qLabelRed)
        else:
            aLabel.setStyleSheet(self._qLabelBackground)
        return True

    def on_bool_combo_box(self, paramName: str, text: str) -> None:
        """Store a boolean combo-box edit.

        Args:
            paramName: Detection parameter field name.
            text: Selected boolean text.
        """
        # logger.info(f'paramName:{paramName} text:"{text}" {type(text)}')
        value = text == "True"
        self._set_parameter(paramName, value)

    def on_detection_type_combo_box(self, paramName: str, text: str) -> None:
        """Store a detection-algorithm combo-box edit.

        Args:
            paramName: Detection parameter field name.
            text: Selected detection type value.
        """
        # logger.info(f'paramName:"{paramName}" text:"{text}"')
        self._set_parameter(paramName, text)

    def on_text_edit(self, aWidget: QtWidgets.QLineEdit, paramName: str) -> None:
        """Store a line-edit value.

        Args:
            aWidget: Edited line widget.
            paramName: Detection parameter field name.
        """
        text = aWidget.text()
        logger.info(f'paramName:{paramName} text:"{text}"')
        self._set_parameter(paramName, text)

    def on_spin_box(self, paramName: str, value: int | float) -> None:
        """Store a numeric edit, including the legacy ``None`` sentinel.

        Args:
            paramName: Detection parameter field name.
            value: Numeric widget value.
        """
        # logger.info(f'paramName:{paramName} value:"{value}" {type(value)}')
        self._set_parameter(paramName, value)

    def detect(self) -> None:
        """Detect spikes in the current file with the editor's parameters.

        Parameters hidden from the editor are reset to None so detection is
        not limited by values the user cannot see.
        """
        logger.info("detecting spikes")

        if self.ba is None:
            return

        parameters = self._parameters_for_detection()

        # spike detect
        self.ba.spikeDetect(parameters.model_dump(mode="json"))

        logger.info(f"detected {self.ba.numSpikes} spikes")

        # update interface
        self.signalDetect.emit(self.ba)

    def _parameters_for_detection(self) -> DetectionParameters:
        """Return an emission copy with hidden range fields cleared.

        Returns:
            Parameters ready for detection or preset persistence.
        """
        parameters = self._detection_parameters
        for name, field in DetectionParameters.model_fields.items():
            metadata = field.json_schema_extra or {}
            if not metadata["x-show-in-editor"] and name != "halfHeights":
                parameters = parameters.with_value(name, None)
        return parameters

    def _fillPresetCombo(self, selectedName: str) -> None:
        """Refill the preset combo and select one name without emitting.

        Args:
            selectedName: Preset name to select, such as ``"Neuron"`` or
                ``"User - My Params"``.
        """
        self._presetCombo.blockSignals(True)
        self._presetCombo.clear()
        for presetName in self._detectionObject.getDetectionPresetList():
            self._presetCombo.addItem(presetName)
        self._presetCombo.setCurrentText(selectedName)
        self._presetCombo.blockSignals(False)

    def on_select_detection_preset(self, detectionPresetName: str) -> None:
        """Load a newly selected detection preset.

        Args:
            detectionPresetName: Selected preset name.
        """
        logger.info(f'detectionPresetName:"{detectionPresetName}"')
        # detectionPreset = sanpy.bDetection.detectionPresets[detectionPreset]
        # detectionPreset = sanpy.bDetection.detectionPresets(detectionPreset)
        # self.detectionClass.setToType(detectionPreset)

        # grab the detection from sanpy app
        self._detection_parameters = DetectionParameters.from_saved(
            self._detectionObject.getDetectionDict(detectionPresetName)
        )
        # Keep the selected preset name (dropdown text), not detectionName.
        # User presets keep detectionName of their parent core preset.
        self._currentDetectionName = detectionPresetName

        self.replot()

    def on_button_click(self, buttonName: str) -> None:
        """Handle one of the plugin's action buttons.

        Args:
            buttonName: Button action name.
        """
        if buttonName == "Detect":
            # take our current dDict and ba.detectSpikes
            # need to signal main interface we did this
            self.detect()

        elif buttonName == "Set Defaults":
            # set current dict to defaults from sanpy.bDetection
            self._detection_parameters = DetectionParameters.from_saved(
                self._detectionObject.getDetectionDict(self._currentDetectionName)
            )

            # refresh interface
            self.replot()

        elif buttonName == "Save Params":
            self.save()

        # elif buttonName == 'SA Node':
        #     detectionPreset = sanpy.bDetection.detectionPresets.sanode
        #     self.detectionClass.setToType(detectionPreset)
        #     # refresh interface
        #     self.replot()
        # elif buttonName == 'Ventricular':
        #     detectionPreset = sanpy.bDetection.detectionPresets.ventricular
        #     self.detectionClass.setToType(detectionPreset)
        #     # refresh interface
        #     self.replot()
        # elif buttonName == 'Neuron':
        #     detectionPreset = sanpy.bDetection.detectionPresets.neuron
        #     self.detectionClass.setToType(detectionPreset)
        #     # refresh interface
        #     self.replot()
        # elif buttonName == 'Subthreshold':
        #     detectionPreset = sanpy.bDetection.detectionPresets.subthreshold
        #     self.detectionClass.setToType(detectionPreset)
        #     # refresh interface
        #     self.replot()
        # elif buttonName == 'Ca++ Spikes':
        #     detectionPreset = sanpy.bDetection.detectionPresets.caspikes
        #     self.detectionClass.setToType(detectionPreset)
        #     # refresh interface
        #     self.replot()
        # elif buttonName == 'Ca++ Kymograph':
        #     detectionPreset = sanpy.bDetection.detectionPresets.cakymograph
        #     self.detectionClass.setToType(detectionPreset)
        #     # refresh interface
        #     self.replot()

        elif buttonName.endswith("_none"):
            # set a parameter to None, will only work if 'allowNone'
            paramName = buttonName.replace("_none", "")
            self._set_parameter(paramName, None)
            self.replot()

        else:
            logger.warning(f'Button "{buttonName}" not understood.')

    def replot(self) -> None:
        """Refresh editor widgets from the current detection parameters."""
        compare_parameters = self._getCompareParameters()

        for detectionParam, field in DetectionParameters.model_fields.items():
            metadata = field.json_schema_extra or {}
            if not metadata["x-show-in-editor"]:
                continue
            if detectionParam not in self.widgetDict.keys():
                logger.warning(
                    f'detectionParam missing "{detectionParam}" -->> not adding to display'
                )
                continue

            currentValue = _display_value(
                self._detection_parameters.get_value(detectionParam)
            )

            if currentValue == -1e9:
                logger.error(
                    f"XXXXX detectionParam:{detectionParam} currentValue:{currentValue} {type(currentValue)}"
                )
                currentValue = None

            aLabel = self.widgetDict[detectionParam]["nameLabelWidget"]
            if (
                compare_parameters is not None
                and currentValue
                != _display_value(compare_parameters.get_value(detectionParam))
            ):
                aLabel.setStyleSheet(self._qLabelRed)
                aLabel.update()
            else:
                aLabel.setStyleSheet(self._qLabelBackground)
                aLabel.update()

            aWidget = self.widgetDict[detectionParam]["widget"]
            aWidget.blockSignals(True)
            try:
                if isinstance(aWidget, QtWidgets.QSpinBox):
                    try:
                        if currentValue is None or math.isnan(currentValue):
                            aWidget.setValue(0)
                        else:
                            aWidget.setValue(currentValue)
                    except TypeError as e:
                        logger.error(f"QSpinBox detectionParam:{detectionParam} ... {e}")
                elif isinstance(aWidget, QtWidgets.QDoubleSpinBox):
                    try:
                        if currentValue is None or math.isnan(currentValue):
                            aWidget.setValue(-1e9)
                        else:
                            aWidget.setValue(currentValue)
                    except TypeError as e:
                        logger.error(
                            f"QDoubleSpinBox detectionParam:{detectionParam} ... {e}"
                        )
                elif isinstance(aWidget, QtWidgets.QComboBox):
                    aWidget.setCurrentText(str(currentValue))
                elif isinstance(aWidget, QtWidgets.QLineEdit):
                    aWidget.setText(str(currentValue))
                else:
                    logger.warning(
                        f'key "{detectionParam}" has value "{currentValue}" but widget type "{type(aWidget)}" not understood.'
                    )
            finally:
                aWidget.blockSignals(False)

    def slot_switchFile(
        self, ba: sanpy.bAnalysis, rowDict: Optional[dict] = None, replot: bool = True
    ) -> None:
        """Load the selected file and show its file name.

        Args:
            ba: Analysis object for the selected file.
            rowDict: Optional file-table row. This editor does not read it.
            replot: Ignored. Parameter widgets are refreshed after the file
                detection parameters are loaded.
        """
        # don't replot until we set our detectionClass
        replot = False
        super().slot_switchFile(ba, rowDict, replot=replot)

        if self.ba is not None:
            self.fileNameLabel.setText(f"File: {self.ba.fileLoader.filename}")

        # before we detect a ba, its detection dict is None
        detection_values = self.ba.getDetectionDict(asCopy=True)
        if detection_values is not None:
            self._detection_parameters = DetectionParameters.from_saved(detection_values)
            self._currentDetectionName = self._detection_parameters.detectionName
            # Do not emit currentTextChanged; that reloads the preset and
            # drops parameter values stored with this file.
            self._presetCombo.blockSignals(True)
            self._presetCombo.setCurrentText(self._currentDetectionName)
            self._presetCombo.blockSignals(False)

        self.replot()

    def save(self) -> None:
        """Save the current detection parameters to a user preset file.

        Saving requires ``userSaveName``. Parameters hidden from the editor
        are saved as None because they are set per detection, not per preset.
        """
        userSaveName = self._detection_parameters.userSaveName
        if not isinstance(userSaveName, str) or not userSaveName.strip():
            QtWidgets.QMessageBox.warning(
                self,
                "Save Params",
                "Specify a Save User Name before saving detection parameters.",
            )
            return

        sanpy_app = self.getSanPyApp()
        sanpy_paths = sanpy_app.sanpy_paths if sanpy_app is not None else sanpy.sanpy_paths()
        userDetectionFolder = sanpy_paths.detection_dir

        # saved detection dict always start with "User - "
        # so saved names never conflict with built in detection names
        filename = "User - " + userSaveName

        savePath = str(userDetectionFolder / f"{filename}.json")

        # abb 202610, removing dialog and just using filename
        # userSaveFile, _tmp = QtWidgets.QFileDialog.getSaveFileName(
        #     self, "Save Detection Params", savePath
        # )
        # logger.info(f'userSaveFile:"{userSaveFile}"')

        # with open(userSaveFile, "w") as f:
        # always over-write with no warning
        saveDict = self._parameters_for_detection().model_dump(mode="json")

        with open(savePath, "w", encoding="utf-8") as f:
            # abb do not change the user specified name
            # self._detectionDict["userSaveName"] = filename
            json.dump(saveDict, f, indent=2)

        logger.info(f'saved detection params to "{savePath}"')

        self._detectionObject.reloadPresets()
        self._fillPresetCombo(filename)
        self._currentDetectionName = filename

        window = self.getSanPyWindow()
        if window is not None:
            window.myDetectionWidget.detectToolbarWidget.refreshDetectionPresets()
            window.slot_updateStatus(f'Saved detection params to "{savePath}"')
