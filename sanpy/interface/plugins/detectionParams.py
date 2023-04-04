import math
import os
from functools import partial
import json
from typing import Union, Dict, List, Tuple, Optional, Optional

from PyQt5 import QtCore, QtWidgets, QtGui

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class detectionParams(sanpyPlugin):
    """
    Plugin to display overview of detection parameters for analysis.

    Uses:
        QTableView: sanpy.interface.bErrorTable.errorTableView()
        QAbstractTableModel: sanpy.interface.bFileTable.pandasModel
    """

    myHumanName = "Detection Parameters"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        logger.info("")

        # this is a class that holds all premade and loaded presets
        # it exists when runnin the sanpy app
        # if not running sanpy app then build it here (for debuggin)
        self._detectionObject: sanpy.bDetection = None

        _detectionDict: dict = None
        _currentDetectionName: str = None

        _sanPyApp = self.getSanPyApp()
        if _sanPyApp is not None:
            self._detectionObject = _sanPyApp.getDetectionClass()
        else:
            self._detectionObject = sanpy.bDetection()

        # get from ba
        if self.ba is not None:
            # get the ba detection dict
            # only exists if analysis has been performed
            _detectionDict = self.ba.getDetectionDict(asCopy=True)  # can be None

        # or, get from app
        if _detectionDict is None:
            # ba is either None or does not have detection yet
            # get the list
            presetList = self._detectionObject.getDetectionPresetList()
            # select first in list
            _currentDetectionName = presetList[0]
            _detectionDict = self._detectionObject.getDetectionDict(
                _currentDetectionName
            )

        # deep copy because we are modifying this
        # do not want to change ba (for example) until we detect
        self._detectionDict = _detectionDict  # dict

        # the name of the detection dict in ba OR the first detection type in detection class
        _currentDetectionName = _detectionDict["detectionName"]
        self._currentDetectionName = _currentDetectionName

        self._qLabelRed = "QLabel { background-color : #888822;}"
        self._qLabelBackground = "QLabel { background-color : #222222;}"

        self.buildUI()

        # self.insertIntoScrollArea()

    def buildUI(self):
        self.vLayout = QtWidgets.QVBoxLayout()

        # top controls
        hControlLayout = QtWidgets.QHBoxLayout()

        fileName = "None"
        if self.ba is not None:
            fileName = self.ba.fileLoader.filename
        self.fileNameLabel = QtWidgets.QLabel(f"File: {fileName}")
        hControlLayout.addWidget(self.fileNameLabel, alignment=QtCore.Qt.AlignLeft)

        aName = "Detect"
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton, alignment=QtCore.Qt.AlignLeft)

        aName = "Set Defaults"
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton, alignment=QtCore.Qt.AlignLeft)

        # get list of names of detection presets (like SANode)
        # detectionPresetList = self.getSanPyApp().getDetectionClass().getDetectionPresetList()
        detectionPresetList = self._detectionObject.getDetectionPresetList()

        aComboBox = QtWidgets.QComboBox()
        # detectionPresets = sanpy.bDetection.getDetectionPresetList()
        for detectionPreset in detectionPresetList:
            aComboBox.addItem(detectionPreset)
        aComboBox.setCurrentText(detectionPresetList[0])
        aComboBox.currentTextChanged.connect(self.on_select_detection_preset)
        hControlLayout.addWidget(aComboBox, alignment=QtCore.Qt.AlignLeft)

        aName = "Save Params"
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton, alignment=QtCore.Qt.AlignLeft)

        hControlLayout.addStretch()

        """
        aName = 'Set Defaults'
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton)

        aName = 'SA Node'
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton)

        aName = 'Ventricular'
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton)

        aName = 'Ca++ Kymograph'
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton)

        aName = 'Neuron'
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton)

        aName = 'Subthreshold'
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton)

        aName = 'Ca++ Spikes'
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton)
        """

        #
        self.vLayout.addLayout(hControlLayout)

        self.vLayoutParams = self.buildUI2()
        self.vLayout.addLayout(self.vLayoutParams)

        #
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

    def buildUI2(self):
        """Build a control for each detection parameter."""
        # list of keys/columns in main analysis dir file list
        analysisDirDict = sanpy.analysisDir.sanpyColumns

        dDict = self._detectionObject.getMasterDict(self._currentDetectionName)

        vLayoutParams = QtWidgets.QGridLayout()

        self.widgetDict = {}  # list of widgets we are displaying

        row = 0
        col = 0
        rowSpan = 1
        colSpan = 1
        for k, v in dDict.items():
            col = 0

            currentValue = self._detectionDict[k]

            # k is the name in spike dictionary
            paramName = k
            defaultValue = v["defaultValue"]
            valueType = v[
                "type"
            ]  # from ('int', 'float', 'boolean', 'string', detectionTypes_)
            units = v["units"]
            humanName = v["humanName"]
            description = v["description"]
            allowNone = v["allowNone"]  # set special value for spin box

            # flag with red
            flagWithRed = currentValue != defaultValue

            inAnalysisDir = paramName in analysisDirDict.keys()

            # add an '*' for params in main file table keys/columns
            aName = " "
            if inAnalysisDir:
                aName = "*"
            nameLabel = QtWidgets.QLabel(
                aName
            )  # added to list so we can later set color
            col += 1

            # for debugging
            """
            aLabel = QtWidgets.QLabel(paramName)
            vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
            col += 1
            """

            humanNameLabel = QtWidgets.QLabel(humanName)
            vLayoutParams.addWidget(nameLabel, row, col, rowSpan, colSpan)
            if flagWithRed:
                humanNameLabel.setStyleSheet(self._qLabelRed)
            vLayoutParams.addWidget(humanNameLabel, row, col, rowSpan, colSpan)
            col += 1

            # for debugging
            """
            aLabel = QtWidgets.QLabel(valueType)
            vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
            col += 1
            """

            aLabel = QtWidgets.QLabel(units)
            vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
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
                if currentValue is None or math.isnan(currentValue):
                    aWidget.setValue(0)
                else:
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
                aWidget.setReadOnly(True)  # for now our 1 edit widget is not editable
                # aWidget.setKeyboardTracking(False) # don't trigger signal as user edits
                # aWidget.setValidator(QIntValidator())
                # aWidget.setMaxLength(4)
                aWidget.setAlignment(QtCore.Qt.AlignLeft)
                aWidget.editingFinished.connect(
                    partial(self.on_text_edit, aWidget, paramName)
                )
            elif valueType == "sanpy.bDetection.detectionTypes":
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

    def _setDict(self, detectionParam, value):
        """Respond to user chhanging a detection parameter.

        This is getting triggered when we update values in Widgets in replot()
        Not intended but just be aware
        """
        logger.info(
            f'Setting dDict key:"{detectionParam}" to value "{value}" type:{type(value)}'
        )
        if value == -1e9:
            # print(f'TWEAK paramName:{paramName} --->>> value:', value)
            value = None
        # ok = self.detectionClass.setValue(paramName, value)
        # if not ok:
        #     logger.error('')
        self._detectionDict[detectionParam] = value

        _masterDict = self._detectionObject.getMasterDict(self._currentDetectionName)
        defaultValue = _masterDict[detectionParam]["defaultValue"]
        flagWithRed = value != defaultValue
        aLabel = self.widgetDict[detectionParam]["nameLabelWidget"]
        if flagWithRed:
            aLabel.setStyleSheet(self._qLabelRed)
        else:
            aLabel.setStyleSheet(self._qLabelBackground)

    def on_bool_combo_box(self, paramName, text):
        # logger.info(f'paramName:{paramName} text:"{text}" {type(text)}')
        value = text == "True"
        self._setDict(paramName, value)

    def on_detection_type_combo_box(self, paramName, text):
        # logger.info(f'paramName:"{paramName}" text:"{text}"')
        self._setDict(paramName, text)

    def on_text_edit(self, aWidget, paramName):
        text = aWidget.text()
        # logger.info(f'paramName:{paramName} text:"{text}"')
        self._setDict(paramName, text)

    def on_spin_box(self, paramName, value):
        """
        When QDoubldeSpinBox accepts None, value is -1e9
        """
        # logger.info(f'paramName:{paramName} value:"{value}" {type(value)}')
        self._setDict(paramName, value)

    def detect(self):
        logger.info("detecting spikes")

        if self.ba is None:
            return

        # spike detect
        self.ba.spikeDetect(self._detectionDict)

        logger.info(f"detected {self.ba.numSpikes} spikes")

        # update interface
        self.signalDetect.emit(self.ba)

    def on_select_detection_preset(self, detectionPresetName: str):
        """User selected a detection preset from combobox."""
        logger.info(f'detectionPresetName:"{detectionPresetName}"')
        # detectionPreset = sanpy.bDetection.detectionPresets[detectionPreset]
        # detectionPreset = sanpy.bDetection.detectionPresets(detectionPreset)
        # self.detectionClass.setToType(detectionPreset)

        # grab the detection from sanpy app
        self._detectionDict = self._detectionObject.getDetectionDict(
            detectionPresetName
        )
        self._currentDetectionName = self._detectionDict["detectionName"]

        self.replot()

    def on_button_click(self, buttonName):
        if buttonName == "Detect":
            # take our current dDict and ba.detectSpikes
            # need to signal main interface we did this
            self.detect()

        elif buttonName == "Set Defaults":
            # set current dict to defaults from sanpy.bDetection
            self._detectionDict = self._detectionObject.getDetectionDict(
                self._currentDetectionName
            )
            self._currentDetectionName = self._detectionDict["detectionName"]

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
            self._setDict(paramName, None)
            self.replot()

        else:
            logger.warning(f'Button "{buttonName}" not understood.')

    def replot(self):
        # if self.ba is None:
        #    return

        logger.info("")

        # was this
        # detectionClass = self.detectionClass
        detectionDict = self._detectionDict

        _masterDict = self._detectionObject.getMasterDict(self._currentDetectionName)

        # for detectionParam in detectionClass.keys():
        for detectionParam in detectionDict.keys():
            if detectionParam not in self.widgetDict.keys():
                logger.warning(
                    f'detectionParam missing "{detectionParam}" -->> not adding to display'
                )
                continue

            # currentValue = v['currentValue']
            # currentValue = detectionClass.getValue(detectionParam)
            currentValue = detectionDict[detectionParam]

            defaultValue = _masterDict[detectionParam]["defaultValue"]
            flagWithRed = defaultValue != currentValue

            if currentValue == -1e9:
                logger.error(
                    f"XXXXX detectionParam:{detectionParam} currentValue:{currentValue} {type(currentValue)}"
                )
                currentValue = None

            aLabel = self.widgetDict[detectionParam]["nameLabelWidget"]
            if flagWithRed:
                aLabel.setStyleSheet(self._qLabelRed)
                aLabel.update()
            else:
                aLabel.setStyleSheet(self._qLabelBackground)
                aLabel.update()

            aWidget = self.widgetDict[detectionParam]["widget"]
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

    def slot_switchFile(
        self, ba: sanpy.bAnalysis, rowDict: Optional[dict] = None, replot: bool = True
    ):
        # don't replot until we set our detectionClass
        replot = False
        super().slot_switchFile(ba, rowDict, replot=replot)

        # before we detect a ba, its detection dict is None
        _detectionDict = self.ba.getDetectionDict(asCopy=True)  # can be None
        if _detectionDict is not None:
            self._detectionDict = _detectionDict  #
            self._currentDetectionName = _detectionDict["detectionName"]

        self.replot()

    def save(self):
        """Save our current detection dict to a user file."""
        userDetectionFolder = sanpy._util._getUserDetectionFolder()

        # key 'detectionName'
        filename = self._detectionDict["userSaveName"]
        if not filename:
            filename = self._detectionDict["detectionName"] + " User"

        savePath = os.path.join(userDetectionFolder, filename + ".json")

        userSaveFile, _tmp = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Detection Params", savePath
        )
        logger.info(userSaveFile)

        with open(userSaveFile, "w") as f:
            self._detectionDict["userSaveName"] = filename
            json.dump(self._detectionDict, f, indent=4)


if __name__ == "__main__":
    path = "data/19114001.abf"
    ba = sanpy.bAnalysis(path)

    bd = sanpy.bDetection()  # gets default
    dDict = bd.getDetectionDict("SA Node")  # an actual dict

    # from pprint import pprint
    # pprint(dDict)

    # dDict['dvdtThreshold'] = 12

    ba.spikeDetect(dDict)
    logger.info(f"detected numSpike:{ba.numSpikes}")

    import sys

    app = QtWidgets.QApplication([])

    dp = detectionParams(ba=ba)  # dec 2022, do not pass bd
    dp.show()

    """
    scrollArea = dp.insertIntoScrollArea()
    if scrollArea is not None:
        scrollArea.show()
    else:
        dp.show()
    """

    sys.exit(app.exec_())
