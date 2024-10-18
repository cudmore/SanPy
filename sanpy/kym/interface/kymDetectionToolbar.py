from functools import partial

from PyQt5 import QtCore, QtWidgets

from sanpy.kym.kymRoiDetection import KymRoiDetection

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class KymDetectionGroupBox(QtWidgets.QGroupBox):
    """A group box to show detection parameters.
    
    Either for detecting in (sun f0 or diameter).
    """

    signalDetectionParamChanged = QtCore.pyqtSignal(object)  # xxx
    signalDetection = QtCore.pyqtSignal(object)

    def __init__(self,
                 detectionDict : KymRoiDetection,
                 groupName = 'not assigned'
    ):

        super().__init__()

        self._groupName = groupName
        
        self._blockSlots = False

        self._detectionDict : KymRoiDetection = detectionDict

        # logger.info('')
        # print(self._detectionDict.printValues())

        self._buildUI(groupName=groupName)

    def setDetectionDict(self, detectionDict : KymRoiDetection):
        """Update with new dict.
        
        Used when selecting an roi.
        """
        self._detectionDict = detectionDict
        self._updateDetectionParamGui()

    def setWidgetEnabled(self, widgetName, enabled : bool):
        """Enable/disable a widget.
        """
        if widgetName not in self._detectionControls.keys():
            logger.error(f'did not find widget "{widgetName}" available widgets are {self._detectionControls.keys()}')
            return
        self._detectionControls[widgetName].setEnabled(enabled)

    def _buildUI(self,
                               groupName : str,
                               ) -> QtWidgets.QGroupBox:
        """A detection toolbar, either for detection in int f0 or diameter.
        """

        logger.info(f'building groupName:{groupName}')

        # dict to pull values from
        detectionDict = self._detectionDict
        
        # a dict of detection controls so we can update them on roi selection in _updateDetectionParamGui
        self._detectionControls = {}  
        
        detectionGroupBox = QtWidgets.QGroupBox(groupName)

        # add the groupbox as the main layout (always confusing)
        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(detectionGroupBox)
        self.setLayout(mainLayout)

        vLayout = QtWidgets.QVBoxLayout()
        vLayout.setAlignment(QtCore.Qt.AlignTop)

        detectionGroupBox.setLayout(vLayout)

        #
        hLayoutAnalyze = QtWidgets.QHBoxLayout()
        hLayoutAnalyze.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayoutAnalyze)

        buttonName = 'Detect Peaks'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Perform the analysis')
        aButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        hLayoutAnalyze.addWidget(aButton)

        #
        hLayout00 = QtWidgets.QHBoxLayout()
        hLayout00.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout00)

        #
        aLabel = QtWidgets.QLabel('Background Subtract')
        hLayout00.addWidget(aLabel)
        
        aName = 'Background Subtract'
        aComboBox = QtWidgets.QComboBox()
        aComboBox.setToolTip(detectionDict.getDescription(aName))
        _items = KymRoiDetection.backgroundSubtractTypes  # ['Off', 'Rolling-Ball', 'Median', 'Mean']
        aComboBox.addItems(_items)
        aComboBox.currentTextChanged.connect(
            partial(self._on_combobox, aName)
        )
        hLayout00.addWidget(aComboBox)
        self._detectionControls[aName] = aComboBox

        hLayout000 = QtWidgets.QHBoxLayout()
        hLayout000.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout000)

        aCheckBoxName = 'Exponential Detrend'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip(detectionDict.getDescription(aCheckBoxName))
        aCheckBox.setChecked(detectionDict[aCheckBoxName])
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout000.addWidget(aCheckBox)
        self._detectionControls[aCheckBoxName] = aCheckBox

        #
        hLayout_f0 = QtWidgets.QHBoxLayout()
        hLayout_f0.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout_f0)

        #
        aName = 'f0 Type'
        aLabel = QtWidgets.QLabel(aName)
        hLayout_f0.addWidget(aLabel)
        
        aComboBox = QtWidgets.QComboBox()
        aComboBox.setToolTip(detectionDict.getDescription(aName))
        aComboBox.addItems(['Manual', 'Percentile'])
        aComboBox.currentTextChanged.connect(
            partial(self._on_combobox, aName)
        )
        hLayout_f0.addWidget(aComboBox)
        self._detectionControls[aName] = aComboBox

        #
        spinBoxName = 'f0 Percentile'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout_f0.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout_f0.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        # 2nd row (filtering)
        _showFiltering = False
        
        hLayout000 = QtWidgets.QHBoxLayout()
        hLayout000.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout000)

        aCheckBoxName = 'Median Filter'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip(detectionDict.getDescription(aCheckBoxName))
        aCheckBox.setChecked(detectionDict[aCheckBoxName])
        aCheckBox.setVisible(_showFiltering)
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout000.addWidget(aCheckBox)
        self._detectionControls[aCheckBoxName] = aCheckBox

        spinBoxName = 'Median Filter Kernel'
        aSpinBox = QtWidgets.QSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(1,100)
        aSpinBox.setSingleStep(2)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.setVisible(_showFiltering)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout000.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        aCheckBoxName = 'Savitzky-Golay'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip(detectionDict.getDescription(aCheckBoxName))
        aCheckBox.setChecked(detectionDict[aCheckBoxName])
        aCheckBox.setVisible(_showFiltering)
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout000.addWidget(aCheckBox)
        self._detectionControls[aCheckBoxName] = aCheckBox

        #
        # third row
        hLayout0 = QtWidgets.QHBoxLayout()
        hLayout0.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout0)

        #
        aName = 'Polarity'
        aLabel = QtWidgets.QLabel(aName)
        hLayout0.addWidget(aLabel)
        
        aComboBox = QtWidgets.QComboBox()
        aComboBox.setToolTip(detectionDict.getDescription(aName))
        aComboBox.addItems(['Pos', 'Neg'])
        aComboBox.currentTextChanged.connect(
            partial(self._on_combobox, aName)
        )
        hLayout0.addWidget(aComboBox)
        self._detectionControls[aName] = aComboBox

        #
        spinBoxName = 'Bin Line Scans'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout0.addWidget(aLabel)

        aSpinBox = QtWidgets.QSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(1,100)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout0.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        buttonName = 'Reset'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Reset detection parameters to default.')
        aButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        hLayout0.addWidget(aButton)

        #
        # second row
        hLayout1 = QtWidgets.QHBoxLayout()
        hLayout1.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout1)

        spinBoxName = 'Prominence'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout1.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(-100,100)
        aSpinBox.setSingleStep(0.01)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout1.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        spinBoxName = 'Width (ms)'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout1.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout1.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        
        hLayout11 = QtWidgets.QHBoxLayout()
        hLayout11.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout11)

        spinBoxName = 'Distance (ms)'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout11.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,10000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout11.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        spinBoxName = 'Decay (ms)'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout11.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout11.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        # third row
        hLayout2 = QtWidgets.QHBoxLayout()
        hLayout2.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout2)

        #
        # 2.5 row
        hLayout2_5 = QtWidgets.QHBoxLayout()
        hLayout2_5.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout2_5)
        #
        spinBoxName = 'thresh_rel_height'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout2_5.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(.1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout2_5.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        # third row
        hLayout3 = QtWidgets.QHBoxLayout()
        hLayout3.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayout3)
        #
        spinBoxName = 'newOnsetOffsetFraction'
        aLabel = QtWidgets.QLabel(spinBoxName)
        hLayout3.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(.1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout3.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        buttonName = 'Plot Quality'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Matplotlib plot of steps in forming dF/F0.')
        aButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        hLayout3.addWidget(aButton)

        return detectionGroupBox

    def _on_spin_box(self, name, value):
        if self._blockSlots:
            logger.warning(f'self._blockSlots:{self._blockSlots} -->> no update for {name} {value}')
            return
        
        logger.info(f'name:{name} value:{value}')
        
        detectionDict = self._detectionDict
        
        if name not in detectionDict.keys():
            logger.error(f'did not understand "{name}" available keys are {detectionDict.keys()}')
            return
        else:
            detectionDict[name] = value
            self.signalDetectionParamChanged.emit(self._groupName)

        return

        if name == 'Median Filter Kernel':
            detectionDict['medianfilterkernel'] = value
            self.updateRoiIntensityPlot()  # update with selected
        
        elif name == 'Bin Lines':
            detectionDict['binLineScans'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Prominence':
            detectionDict['prominence'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Width (ms)':
            detectionDict['width (ms)'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Distance (ms)':
            detectionDict['distance (ms)'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'Decay (ms)':
            detectionDict['decay (ms)'] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'f0 Percentile':
            detectionDict[name] = value
            self.updateRoiIntensityPlot()  # update with selected

        elif name == 'newOnsetOffsetFraction':
            detectionDict[name] = value
            self.updateRoiIntensityPlot()  # update with selected

        #
        # diameter detection params
        elif name == 'line_width_diam':
            detectionDict[name] = value
            self.updateRoiDiamPlot()  # update with selected
        
        elif name == 'line_median_kernel_diam':
            if value % 2 == 0:
                # even
                value -= 1
                logger.warning(f'got even median kernal but must be odd, set to {value}')
            detectionDict[name] = value
            self.updateRoiDiamPlot()  # update with selected

        elif name == 'std_threshold_mult_diam':
            detectionDict[name] = value
            self.updateRoiDiamPlot()  # update with selected

        elif name == 'line_interp_mult_diam':
            detectionDict[name] = value
            self.updateRoiDiamPlot()  # update with selected

        else:
            logger.error(f'did not understand name:{name}')

    def _on_combobox(self, name, value):
        """
        Parameters
        ----------
        detectionDict : dict
            Switches between multiple detection group boxes like (detect int, detect diam)
        """
        if self._blockSlots:
            logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return
        
        logger.info(f'"{name}" value:{value}')
        
        detectionDict = self._detectionDict

        if name not in detectionDict.keys():
            logger.error(f'did not understand "{name}" available keys are {detectionDict.keys()}')
            return
        else:
            detectionDict[name] = value
            self.signalDetectionParamChanged.emit(self._groupName)

        return

    def _on_checkbox_clicked(self, name, value = None):
        if self._blockSlots:
            logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return

        if value > 0:
            value = 1
        
        # logger.info(f'name:{name} value:{value}')

        detectionDict = self._detectionDict

        if name not in detectionDict.keys():
            logger.error(f'did not understand "{name}" available keys are {detectionDict.keys()}')
            return
        else:
            detectionDict[name] = value
            self.signalDetectionParamChanged.emit(detectionDict)

        return

    def _on_button_click(self, name : str):
        logger.info(f'name:{name}')

        if name == 'Detect Peaks':
            self.signalDetection.emit(self._groupName)

        elif name == 'Reset':
            # reset detection params to default
            self._detectionDict.setDefaults()
            self._updateDetectionParamGui()

    def _updateDetectionParamGui(self):

        logger.info('')

        self._blockSlots = True
        
        detectionDict = self._detectionDict

        if detectionDict['Polarity'] == 'Pos':
            self._detectionControls['Polarity'].setCurrentIndex(0)
        elif detectionDict['Polarity'] == 'Neg':
            self._detectionControls['Polarity'].setCurrentIndex(1)
        else:
            logger.error(f"did not understand polarity: {detectionDict['Polarity']}")


        self._detectionControls['Median Filter'].setChecked(detectionDict['Median Filter'])  # boolean
        self._detectionControls['Median Filter Kernel'].setValue(detectionDict['Median Filter Kernel'])  # must be odd
        self._detectionControls['Savitzky-Golay'].setChecked(detectionDict['Savitzky-Golay'])
        self._detectionControls['Bin Line Scans'].setValue(detectionDict['Bin Line Scans'])
        self._detectionControls['Prominence'].setValue(detectionDict['Prominence'])
        self._detectionControls['Width (ms)'].setValue(detectionDict['Width (ms)'])
        self._detectionControls['Distance (ms)'].setValue(detectionDict['Distance (ms)'])

        self._detectionControls['f0 Percentile'].setValue(detectionDict['f0 Percentile'])

        if detectionDict['detectThisTrace'] == 'Diameter (um)':
            pass
        else:
            if detectionDict['f0 Type'] == 'Manual':
                self._detectionControls['f0 Type'].setCurrentIndex(0)
                self._detectionControls['f0 Percentile'].setEnabled(False)
            elif detectionDict['f0 Type'] == 'Percentile':
                self._detectionControls['f0 Type'].setCurrentIndex(1)
                self._detectionControls['f0 Percentile'].setEnabled(True)
            else:
                logger.error(f"did not understand 'f0 Type' {detectionDict['f0 Type']}")

        backgroundSubtractTypes = KymRoiDetection.backgroundSubtractTypes
        backgroundsubtract = detectionDict['Background Subtract']
        _idx = backgroundSubtractTypes.index(backgroundsubtract)
        self._detectionControls['Background Subtract'].setCurrentIndex(_idx)

        self._detectionControls['Exponential Detrend'].setChecked(detectionDict['Exponential Detrend'])  # boolean

        # self._detectionControls['thresh_rel_height'].setValue(detectionParamDict['thresh_rel_height'])  # boolean

        self._blockSlots = False
