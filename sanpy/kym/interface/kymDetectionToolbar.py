from functools import partial
from typing import Optional

from PyQt5 import QtCore, QtWidgets

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis, PeakDetectionTypes
from sanpy.kym.kymRoiDetection import KymRoiDetection

from sanpy.kym.logger import get_logger
logger = get_logger(__name__)

class KymDetectionGroupBox(QtWidgets.QGroupBox):
    """A group box to show detection parameters.
    
    Either for detecting in (sum f0 or diameter).
    """

    signalDetectionParamChanged = QtCore.pyqtSignal(str, object)  # (group name, KymRoiDetection)
    signalDetection = QtCore.pyqtSignal(object)
    signalSetWidgetVisible = QtCore.pyqtSignal(object, object)  # (widget name, visible)

    def __init__(self,
                 kymRoiAnalysis : KymRoiAnalysis,
                 peakDetectionType : PeakDetectionTypes,
                 kymRoiDetection : KymRoiDetection,
                 groupName,
                 detectThisTraceList,
    ):

        super().__init__(title=groupName)  # title will be updated when roi is selected

        # only used to get roi detection on slot_selectroi
        self._kymRoiAnalysis = kymRoiAnalysis
        """KymRoiAnalysis object to get the roi detection dict.
        """
        self._peakDetectionType : PeakDetectionTypes = peakDetectionType
        
        self._kymRoiDetection = kymRoiDetection
        """KymRoiDetection object to get the roi detection dict.
        """
        self._groupName = groupName
        self._detectThisTraceList = detectThisTraceList

        self._blockSlots = False

        self._contentMarginLeft = 5
        self._contentMarginTop = 5

        # baltimore april
        self._selectedChannel = None
        self._selectedRoiLabel = None

        self._buildUI(groupName=groupName)

    def _old_setDetectionDict(self, kymRoiDetection : KymRoiDetection):
        """Update with new dict.
        
        Used when selecting an roi.
        """
        self._kymRoiDetection = kymRoiDetection
        self._updateDetectionParamGui()

    def setWidgetEnabled(self, widgetName, enabled : bool):
        """Enable/disable a widget.
        """
        if widgetName not in self._detectionControls.keys():
            logger.error(f'did not find widget "{widgetName}" available widgets are {self._detectionControls.keys()}')
            return
        self._detectionControls[widgetName].setEnabled(enabled)

    def setWidgetVisible(self, widgetName, visible : bool):
        """Enable/disable a widget.
        """
        if widgetName not in self._detectionControls.keys():
            logger.error(f'did not find widget "{widgetName}" available widgets are {self._detectionControls.keys()}')
            return
        self._detectionControls[widgetName].setVisible(visible)

        if widgetName == 'f0 Type':
            # logger.error('layout has no set visible !!!!!!!!!!!!!!!!!!!!')
            # self.hLayout_f0.setVisible(visible)
            self._widget_f0.setVisible(visible)

    def _buildTopToolbar(self) -> QtWidgets.QVBoxLayout:
        """Derived classes define this.
        """
        pass

    def _buildUI(self,
                groupName : str,
                ) -> QtWidgets.QGroupBox:
        """A detection toolbar, either for detection in int f0 or diameter.
        """

        # logger.info(f'building groupName:{groupName}')
        
        detectionDict = self._kymRoiDetection
        """dict to pull values from"""
        
        # a dict of detection controls so we can update them on roi selection in _updateDetectionParamGui
        self._detectionControls = {}  
        
        # content margins are inherited, when we add a widget or layout to QGroupBox (e.g. self)
        # all containing layout will inherit!
        self.setContentsMargins(self._contentMarginLeft, 0, 0, 0)

        # add the groupbox as the main layout (always confusing)
        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.setAlignment(QtCore.Qt.AlignTop)
        # mainLayout.setContentsMargins(self._contentMarginLeft, 0, 0, 0)
        self.setLayout(mainLayout)

        # abb 202505 colin, removing nested QGroupBox
        # self.detectionGroupBox = QtWidgets.QGroupBox(groupName)
        # self.detectionGroupBox.setEnabled(False)  # only enable when an roi is selected
        # mainLayout.addWidget(self.detectionGroupBox)

        # abb 202505 colin, removing nested QGroupBox
        # v layout for groupbox
        # vLayout = QtWidgets.QVBoxLayout()
        # vLayout.setAlignment(QtCore.Qt.AlignTop)
        # self.detectionGroupBox.setLayout(vLayout)

        _topToolbar = self._buildTopToolbar()
        if _topToolbar is not None:
            # vLayout.addLayout(_topToolbar)
            mainLayout.addLayout(_topToolbar)

        #
        hLayoutAnalyze = QtWidgets.QHBoxLayout()
        hLayoutAnalyze.setAlignment(QtCore.Qt.AlignLeft)
        mainLayout.addLayout(hLayoutAnalyze)

        aCheckBoxName = 'Auto'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip(detectionDict.getDescription(aCheckBoxName))
        aCheckBox.setChecked(detectionDict[aCheckBoxName])
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayoutAnalyze.addWidget(aCheckBox)
        self._detectionControls[aCheckBoxName] = aCheckBox

        buttonName = 'Detect Peaks'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setStyleSheet("background-color: green")
        aButton.setToolTip('Perform the analysis')
        aButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        hLayoutAnalyze.addWidget(aButton)
        self._detectionControls[buttonName] = aButton  # so we can set the color

        aName = 'detectThisTrace'
        aComboBox = QtWidgets.QComboBox()
        aComboBox.setToolTip(detectionDict.getDescription(aName))
        aComboBox.addItems(self._detectThisTraceList)
        aComboBox.currentTextChanged.connect(
            partial(self._on_combobox, aName)
        )
        hLayoutAnalyze.addWidget(aComboBox)
        self._detectionControls[aName] = aComboBox

        buttonName = 'Reset'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Reset detection parameters to default.')
        aButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        hLayoutAnalyze.addWidget(aButton)

        #
        hLayout00 = QtWidgets.QHBoxLayout()
        hLayout00.setAlignment(QtCore.Qt.AlignLeft)
        # hLayout00.setContentsMargins(self._contentMarginLeft, 0, 0, 0)
        mainLayout.addLayout(hLayout00)

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
        # hLayout000.setContentsMargins(self._contentMarginLeft, 0, 0, 0)
        mainLayout.addLayout(hLayout000)

        aCheckBoxName = 'Exponential Detrend'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        aCheckBox.setToolTip(detectionDict.getDescription(aCheckBoxName))
        aCheckBox.setChecked(detectionDict[aCheckBoxName])
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayout000.addWidget(aCheckBox)
        self._detectionControls[aCheckBoxName] = aCheckBox

        # need self.hLayout_f0 so we can hide entire row
        # abb 202505 colin, put in a widget so we can hide
        self._widget_f0 = QtWidgets.QWidget()
        
        hLayout_f0 = QtWidgets.QHBoxLayout()
        hLayout_f0.setAlignment(QtCore.Qt.AlignLeft)
        self._widget_f0.setLayout(hLayout_f0)

        # mainLayout.addLayout(hLayout_f0)
        mainLayout.addWidget(self._widget_f0)

        #
        aName = 'f0 Type'
        _displayName = 'f0'
        # aLabel = QtWidgets.QLabel(aName)
        aLabel = QtWidgets.QLabel(_displayName)
        hLayout_f0.addWidget(aLabel)
        
        aComboBox = QtWidgets.QComboBox()
        aComboBox.setToolTip(detectionDict.getDescription(aName))
        aComboBox.addItems(['Manual', 'Percentile'])
        aComboBox.currentTextChanged.connect(
            partial(self._on_combobox, aName)
        )
        # self.hLayout_f0.addWidget(aComboBox)
        hLayout_f0.addWidget(aComboBox)
        self._detectionControls[aName] = aComboBox

        #
        spinBoxName = 'f0 Percentile'
        _displayName = 'Percentile'
        # aLabel = QtWidgets.QLabel(spinBoxName)
        # hLayout_f0.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0.001,1000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setPrefix(f'{_displayName}: ')
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout_f0.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        spinBoxName = 'f0 Value Manual'
        _displayName = 'Manual'
        # aLabel = QtWidgets.QLabel(spinBoxName)
        # hLayout_f0.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0.001,1000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setPrefix(f'{_displayName}: ')
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
        # hLayout000.setContentsMargins(self._contentMarginLeft, 0, 0, 0)
        mainLayout.addLayout(hLayout000)

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
        hLayout0.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        # hLayout0.setContentsMargins(self._contentMarginLeft, 0, 0, 0)
        mainLayout.addLayout(hLayout0)

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
        aSpinBox.setRange(0,100)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout0.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        # second row
        # hLayout1 = QtWidgets.QHBoxLayout()
        # hLayout1.setAlignment(QtCore.Qt.AlignLeft)
        # # hLayout1.setContentsMargins(self._contentMarginLeft, 0, 0, 0)
        # vLayout.addLayout(hLayout1)

        vLayoutProminence = QtWidgets.QVBoxLayout()
        vLayoutProminence.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        # vLayoutProminence.setContentsMargins(self._contentMarginLeft, 0, 0, 0)
        mainLayout.addLayout(vLayoutProminence)

        spinBoxName = 'Prominence'
        # aLabel = QtWidgets.QLabel(spinBoxName)
        # hLayout1.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(-100,100)
        aSpinBox.setSingleStep(0.1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setPrefix(f'{spinBoxName}:')
        # aSpinBox.setSuffix(" (pixels)")

        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        vLayoutProminence.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        spinBoxName = 'Width (ms)'
        # aLabel = QtWidgets.QLabel(spinBoxName)
        # hLayout1.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setPrefix(f'{spinBoxName} ')
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        vLayoutProminence.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        # hLayout11 = QtWidgets.QHBoxLayout()
        # hLayout11.setAlignment(QtCore.Qt.AlignLeft)
        # # hLayout11.setContentsMargins(self._contentMarginLeft, 0, 0, 0)
        # vLayout.addLayout(hLayout11)

        spinBoxName = 'Distance (ms)'
        # aLabel = QtWidgets.QLabel(spinBoxName)
        # vLayoutProminence.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,10000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setPrefix(f'{spinBoxName} ')
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        vLayoutProminence.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        spinBoxName = 'Decay (ms)'
        # aLabel = QtWidgets.QLabel(spinBoxName)
        # hLayout11.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setPrefix(f'{spinBoxName} ')
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        vLayoutProminence.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        # FINISH VLayout

        #
        # third row
        # hLayout2 = QtWidgets.QHBoxLayout()
        # hLayout2.setAlignment(QtCore.Qt.AlignLeft)
        # # hLayout2.setContentsMargins(self._contentMarginLeft, 0, 0, 0)
        # vLayout.addLayout(hLayout2)

        #
        # 2.5 row
        hLayout2_5 = QtWidgets.QHBoxLayout()
        hLayout2_5.setAlignment(QtCore.Qt.AlignLeft)
        # hLayout2_5.setContentsMargins(self._contentMarginLeft, 0, 0, 0)
        mainLayout.addLayout(hLayout2_5)
        #
        spinBoxName = 'thresh_rel_height'
        # aLabel = QtWidgets.QLabel(spinBoxName)
        # hLayout2_5.addWidget(aLabel)

        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(.1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setPrefix(f'{spinBoxName} ')
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
        mainLayout.addLayout(hLayout3)
        #
        spinBoxName = 'newOnsetOffsetFraction'
        aSpinBox = QtWidgets.QDoubleSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,1000)
        aSpinBox.setSingleStep(.1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setPrefix(f'{spinBoxName} ')
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout3.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

        #
        # fourth row
        hLayout4 = QtWidgets.QHBoxLayout()
        hLayout4.setAlignment(QtCore.Qt.AlignLeft)
        mainLayout.addLayout(hLayout4)

        spinBoxName = 'Post Median Filter Kernel'
        aSpinBox = QtWidgets.QSpinBox()
        aSpinBox.setToolTip(detectionDict.getDescription(spinBoxName))
        aSpinBox.setRange(0,51)
        aSpinBox.setSingleStep(1)
        aSpinBox.setValue(detectionDict[spinBoxName])
        aSpinBox.setPrefix(f'{spinBoxName} ')
        aSpinBox.setKeyboardTracking(False)
        aSpinBox.valueChanged.connect(
            partial(self._on_spin_box, spinBoxName)
            )
        hLayout4.addWidget(aSpinBox)
        self._detectionControls[spinBoxName] = aSpinBox

    def _on_spin_box(self, name, value):
        if self._blockSlots:
            # logger.warning(f'self._blockSlots:{self._blockSlots} -->> no update for {name} {value}')
            return
        
        logger.info(f'name:{name} value:{value}')
        
        detectionDict = self._kymRoiDetection
        
        if name not in detectionDict.keys():
            logger.error(f'did not understand "{name}" available keys are {detectionDict.keys()}')
            return
        else:
            detectionDict[name] = value
            logger.info(f'-->> emit signalDetectionParamChanged group:{self._groupName} + KymRoiDetection')
            self.signalDetectionParamChanged.emit(self._groupName, detectionDict)

    def _on_combobox(self, name, value):
        """
        Parameters
        ----------
        detectionDict : dict
            Switches between multiple detection group boxes like (detect int, detect diam)
        """
        if self._blockSlots:
            # logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return
        
        logger.info(f'"{name}" value:{value}')
        
        detectionDict = self._kymRoiDetection

        if name not in detectionDict.keys():
            logger.error(f'did not understand "{name}" available keys are {detectionDict.keys()}')
            return
        else:
            detectionDict[name] = value
            logger.info(f'-->> emit signalDetectionParamChanged group:{self._groupName} + KymRoiDetection')
            self.signalDetectionParamChanged.emit(self._groupName, detectionDict)

        return

    def _on_checkbox_clicked(self, name, value = None):
        if self._blockSlots:
            # logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return

        if value > 0:
            value = 1
        
        # logger.info(f'name:{name} value:{value}')

        detectionDict = self._kymRoiDetection

        if name not in detectionDict.keys():
            logger.error(f'did not understand "{name}" available keys are {detectionDict.keys()}')
            return
        else:
            detectionDict[name] = value
            logger.info(f'-->> emit signalDetectionParamChanged group:{self._groupName} + KymRoiDetection')
            self.signalDetectionParamChanged.emit(self._groupName, detectionDict)

        return

    def _on_button_click(self, name : str):
        if self._blockSlots:
            # logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return

        logger.info(f'name:{name}')

        if name == 'Detect Peaks':
            self.signalDetection.emit(self._groupName)

        elif name == 'Reset':
            # reset detection params to default
            self._kymRoiDetection.setDefaults()
            self._updateDetectionParamGui()
        
        elif name == 'Plot Quality':
            from sanpy.kym.kymRoiAnalysis import plotDetectionResults
            # plotDetectionResults(self._kymRoiAnalysis.getRoi(self._selectedRoiLabel),
            #                      self._selectedChannel)
            fig, ax = plotDetectionResults(self._kymRoiAnalysis,
                                 self._selectedRoiLabel,
                                 self._selectedChannel)
            from matplotlib import pyplot as plt
            plt.show()

    def _updateDetectionParamGui(self):

        logger.info('')

        self._blockSlots = True
        
        detectionDict = self._kymRoiDetection
        if detectionDict is None:
            # no roi selection
            logger.warning('todo: disable gui on None roi')
            return
        
        if detectionDict['Polarity'] == 'Pos':
            self._detectionControls['Polarity'].setCurrentIndex(0)
        elif detectionDict['Polarity'] == 'Neg':
            self._detectionControls['Polarity'].setCurrentIndex(1)
        else:
            logger.error(f"did not understand polarity: {detectionDict['Polarity']}")


        self._detectionControls['Auto'].setChecked(detectionDict['Auto'])  # boolean
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

        # abb 202505, need to refactor to auto fill in detection params
        self._detectionControls['thresh_rel_height'].setValue(detectionDict['thresh_rel_height'])
        self._detectionControls['newOnsetOffsetFraction'].setValue(detectionDict['newOnsetOffsetFraction'])

        # set detectThisTrace combobox
        detectThisTrace = detectionDict['detectThisTrace']
        _idx = self._detectThisTraceList.index(detectThisTrace)
        self._detectionControls['detectThisTrace'].setCurrentIndex(_idx)

        self._blockSlots = False

    def slot_selectRoi(self, channel : int, roiLabel : Optional[str]):
        
        # always setTitle()
        _title = f'{self._groupName} ch {channel+1} roi {roiLabel}'
        # self.detectionGroupBox.setTitle(_title)
        self.setTitle(_title)

        if roiLabel is not None:
            # self.detectionGroupBox.setEnabled(True)
            self.setEnabled(True)
            self._kymRoiDetection = self._kymRoiAnalysis.getDetectionParams(roiLabel, self._peakDetectionType, channel)
            self._updateDetectionParamGui()

            # detect button follow channel color
            # from sanpy.kym.interface.kymRoiWidget import getChannelColor
            detectButtonColor = self._kymRoiAnalysis.getChannelColor(channel)
            self._detectionControls['Detect Peaks'].setStyleSheet(f'background-color: {detectButtonColor}')

            self._selectedRoiLabel = roiLabel
            self._selectedChannel = channel

        else:
            # self.detectionGroupBox.setEnabled(False)
            self.setEnabled(False)
            self._kymRoiDetection = None        
            self._selectedRoiLabel = None
            self._selectedChannel = None

class KymDetectionGroupBox_Intensity(KymDetectionGroupBox):
    def __init__(self,
                 kymRoiAnalysis : KymRoiAnalysis,
                 kymRoiDetection : KymRoiDetection,
                 groupName,
                 detectThisTraceList,
    ):
        super().__init__(kymRoiAnalysis,
                         PeakDetectionTypes.intensity,
                         kymRoiDetection,
                         groupName,
                         detectThisTraceList)

    def _buildTopToolbar(self) -> QtWidgets.QVBoxLayout:
        vLayout = QtWidgets.QVBoxLayout()
        # vLayout.setContentsMargins(self._contentMarginLeft, self._contentMarginTop, 0, 0)

        # buttons to toggle sum and intensity (f0)
        hLayoutButtons = QtWidgets.QHBoxLayout()
        hLayoutButtons.setAlignment(QtCore.Qt.AlignLeft)
        # hLayoutButtons.setContentsMargins(self._contentMarginLeft, self._contentMarginTop, 0, 0)

        vLayout.addLayout(hLayoutButtons)

        aLabel = QtWidgets.QLabel('Plots:')
        hLayoutButtons.addWidget(aLabel)

        # # visual control of interface (not part of detection parameters)
        # aCheckBoxName = 'Intensity'
        # aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        # aCheckBox.setChecked(True)
        # aCheckBox.stateChanged.connect(
        #     partial(self._on_checkbox_clicked, aCheckBoxName)
        # )
        # hLayoutButtons.addWidget(aCheckBox)
        
        # # visual control of interface (not part of detection parameters)
        # aCheckBoxName = 'f0'
        # aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        # aCheckBox.setChecked(False)
        # aCheckBox.stateChanged.connect(
        #     partial(self._on_checkbox_clicked, aCheckBoxName)
        # )
        # hLayoutButtons.addWidget(aCheckBox)

        #
        buttonName = 'Plot Quality'
        aButton = QtWidgets.QPushButton(buttonName)
        aButton.setToolTip('Matplotlib plot of steps in forming dF/F0.')
        aButton.clicked.connect(
            partial(self._on_button_click, buttonName)
        )
        hLayoutButtons.addWidget(aButton)

        return vLayout
    
    def _on_checkbox_clicked(self, name, value = None):
        if self._blockSlots:
            # logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return

        if value > 0:
            value = 1

        # if name == 'Intensity':
        #     logger.info('TODO: hide show intensity plot (sum)')
        #     self.signalSetWidgetVisible.emit(name, value)
        # elif name == 'f0':
        #     logger.info('TODO: hide show f0 intensity plot')
        #     self.signalSetWidgetVisible.emit(name, value)
        # else:
        #     super()._on_checkbox_clicked(name, value)

        super()._on_checkbox_clicked(name, value)

class KymDetectionGroupBox_Diameter(KymDetectionGroupBox):
    def __init__(self,
                 kymRoiAnalysis : KymRoiAnalysis,
                 kymRoiDetection : KymRoiDetection,
                 groupName,
                 detectThisTraceList,
    ):
        super().__init__(kymRoiAnalysis,
                         PeakDetectionTypes.diameter,
                        kymRoiDetection,
                         groupName,
                         detectThisTraceList)

    def _buildTopToolbar(self) -> QtWidgets.QVBoxLayout:
        vLayout = QtWidgets.QVBoxLayout()
        
        # buttons to toggle sum and intensity (f0)
        hLayoutButtons = QtWidgets.QHBoxLayout()
        hLayoutButtons.setAlignment(QtCore.Qt.AlignLeft)
        vLayout.addLayout(hLayoutButtons)

        aLabel = QtWidgets.QLabel('Plots:')
        hLayoutButtons.addWidget(aLabel)

        # visual control of interface (not part of detection parameters)
        aCheckBoxName = 'Diameter'
        aCheckBox = QtWidgets.QCheckBox(aCheckBoxName)
        # aCheckBox.setToolTip(detectionDict.getDescription(aCheckBoxName))
        # aCheckBox.setChecked(detectionDict[aCheckBoxName])
        aCheckBox.setChecked(False)
        aCheckBox.stateChanged.connect(
            partial(self._on_checkbox_clicked, aCheckBoxName)
        )
        hLayoutButtons.addWidget(aCheckBox)

        return vLayout
    
    def _on_checkbox_clicked(self, name, value = None):
        if self._blockSlots:
            # logger.warning(f'_blockSlots -->> no update for {name} {value}')
            return

        if value > 0:
            value = 1

        if name == 'Diameter':
            logger.info('TODO: hide show intensity plot (sum)')
            self.signalSetWidgetVisible.emit(name, value)
        else:
            super()._on_checkbox_clicked(name, value)

