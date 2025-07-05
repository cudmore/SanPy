from functools import partial

from PyQt5 import QtCore, QtWidgets

from sanpy.kym.kymRoiDetection import KymRoiDetection
from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, PeakDetectionTypes

from sanpy.kym.logger import get_logger
logger = get_logger(__name__)

class KymDiameterToolbar(QtWidgets.QGroupBox):
    """A groupbox to detect diameter in kym image.
    """

    signalDetectionParamChanged = QtCore.pyqtSignal(str, object)  # (group name, KymRoiDetection)
    signalDetection = QtCore.pyqtSignal(object)

    def __init__(self,
                 kymRoiAnalysis : KymRoiAnalysis,
                 kymRoiDetection : KymRoiDetection,
                 groupName : str):
        super().__init__()

        self._kymRoiAnalysis : KymRoiAnalysis = kymRoiAnalysis
        self._kymRoiDetection = kymRoiDetection  #KymRoiDetection(PeakDetectionTypes.diameter)  # on init is defaults
        self._groupName = groupName
        self._blockSlots = False

        self._buildUI()

    def setDetectionDict(self, detectionDict : KymRoiDetection):
        """Update with new dict.
        
        Used when selecting an roi.
        """
        self._kymRoiDetection = detectionDict
        self._updateDetectionParamGui()

    def _updateDetectionParamGui(self):
        """Update GUI with current detection parameters.
        """
        logger.warning('  this is triggering KeyError on "Detect Diameter"')
        self._blockSlots = True
        detectionDict = self._kymRoiDetection

        for name, widget in self._detectionControls.items():
            value = detectionDict[name]
            if isinstance(widget, QtWidgets.QCheckBox):
                widget.setChecked(value)
            elif isinstance(widget, QtWidgets.QAbstractSpinBox):
                widget.setValue(value)

        self._blockSlots = False

    def _buildUI(self):
        self._detectionControls = {}
        
        detectionDict = self._kymRoiDetection

        # self.detectionGroupBox = QtWidgets.QGroupBox(self._groupName)

        # add the groupbox as the main layout (always confusing)
        mainLayout = QtWidgets.QVBoxLayout()
        # mainLayout.addWidget(self.detectionGroupBox)
        self.setLayout(mainLayout)

        # vLayout = QtWidgets.QVBoxLayout()
        # vLayout.setAlignment(QtCore.Qt.AlignTop)
        # self.detectionGroupBox.setLayout(vLayout)

        #
        aButtonName = 'Detect Diameter'
        aButton = QtWidgets.QPushButton(aButtonName)
        aButton.setToolTip('Perform the analysis')
        aButton.clicked.connect(
            partial(self._on_button_click, aButtonName)
        )
        self._detectionControls[aButtonName] = aButton
        self._addHLayout(aButton, mainLayout, labelStr=None)

        aName = 'do_background_subtract_diam'
        aCheckBox = QtWidgets.QCheckBox(aName)
        aCheckBox.setChecked(detectionDict[aName])
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aName)
        )
        self._detectionControls[aName] = aCheckBox
        self._addHLayout(aCheckBox, mainLayout, labelStr=None)

        aName = 'line_width_diam'
        aSpinBox = self._aSpinBox(aName)
        self._detectionControls[aName] = aSpinBox
        self._addHLayout(aSpinBox, mainLayout, labelStr=aName)

        aName = 'line_median_kernel_diam'
        aSpinBox = self._aSpinBox(aName)
        aSpinBox.setSingleStep(2)
        self._detectionControls[aName] = aSpinBox
        self._addHLayout(aSpinBox, mainLayout, labelStr=aName)

        # main detection param
        aName = 'std_threshold_mult_diam'
        aSpinBox = self._aSpinBox(aName)
        aSpinBox.setMinimum(-4)
        self._detectionControls[aName] = aSpinBox
        self._addHLayout(aSpinBox, mainLayout, labelStr=aName)

        aName = 'line_scan_fraction_diam'
        aSpinBox = self._aSpinBox(aName)
        self._detectionControls[aName] = aSpinBox
        self._addHLayout(aSpinBox, mainLayout, labelStr=aName)

        aName = 'line_interp_mult_diam'
        aSpinBox = self._aSpinBox(aName)
        self._detectionControls[aName] = aSpinBox
        self._addHLayout(aSpinBox, mainLayout, labelStr=aName)

    def _aSpinBox(self, name : str):
        detectionDict = self._kymRoiDetection
        
        _type = detectionDict.getType(name)
        if _type == 'int':
            aSpinBox = QtWidgets.QSpinBox()
        elif _type == 'float':
            aSpinBox = QtWidgets.QDoubleSpinBox()
            aSpinBox.setSingleStep(0.1)
        else:
            logger.error(f'did not understand type for spinbox "{_type}"')
            return
        
        aSpinBox.setToolTip(detectionDict.getDescription(name))
        # aSpinBox.setRange(1,100)
        # aSpinBox.setSingleStep(2)
        aSpinBox.setValue(detectionDict[name])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, name)
            )
        return aSpinBox
    
    def _addHLayout(self, widget : QtWidgets.QWidget, parentLayout, labelStr : str = None):
        """Add a new hLayout to parentLayout.
        """
        hLayout = QtWidgets.QHBoxLayout()
        hLayout.setAlignment(QtCore.Qt.AlignLeft)

        if labelStr is not None:
            aLabel = QtWidgets.QLabel(labelStr)
            hLayout.addWidget(aLabel)

        hLayout.addWidget(widget)
        parentLayout.addLayout(hLayout)

    def _on_button_click(self, name):
        logger.info(f'{name}')
        if name == 'Detect Diameter':
            self.signalDetection.emit(self._groupName)

    def _on_checkbox_clicked(self, name, value):
        if self._blockSlots:
            logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return

        if value > 0:
            value = 1
        logger.info(f'{name} {value}')
        detectionDict = self._kymRoiDetection
        if name not in detectionDict.keys():
            logger.error(f'did not understand "{name}" available keys are {detectionDict.keys()}')
            return
        else:
            detectionDict[name] = value
            logger.info(f'-->> emit signalDetectionParamChanged group:{self._groupName} + KymRoiDetection')
            self.signalDetectionParamChanged.emit(self._groupName, detectionDict)

    def _on_spin_box(self, name, value):
        if self._blockSlots:
            logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return

        logger.info(f'{name} {value}')
        detectionDict = self._kymRoiDetection
        if name not in detectionDict.keys():
            logger.error(f'did not understand "{name}" available keys are {detectionDict.keys()}')
            return
        else:
            detectionDict[name] = value
            logger.info(f'-->> emit signalDetectionParamChanged group:{self._groupName} + KymRoiDetection')
            self.signalDetectionParamChanged.emit(self._groupName, detectionDict)

    def slot_selectRoi(self, channel : int, roiLabel : str):
        # logger.info(f'channel:{channel} roi:{roi}')
        # logger.info('   TODO: implemet this')

        # always setTitle()
        _title = f'{self._groupName} ch {channel+1} roi {roiLabel}'
        # self.detectionGroupBox.setTitle(_title)
        self.setTitle(_title)

        if roiLabel is not None:
            # self.detectionGroupBox.setEnabled(True)
            self.setEnabled(True)
            
            self._kymRoiDetection = self._kymRoiAnalysis.getRoi(roiLabel).getDetectionParams(channel, PeakDetectionTypes.diameter)
            self._updateDetectionParamGui()

            # detect button follow channel color
            # from sanpy.kym.interface.kymRoiWidget import getChannelColor
            detectButtonColor = self._kymRoiAnalysis.getChannelColor(channel)
            self._detectionControls['Detect Diameter'].setStyleSheet(f'background-color: {detectButtonColor}')

        else:
            # self.detectionGroupBox.setEnabled(False)
            self.setEnabled(False)
            self._kymRoiDetection = None        
