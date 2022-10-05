import numbers, math
from functools import partial
import copy

from PyQt5 import QtCore, QtWidgets, QtGui

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class detectionParams(sanpyPlugin):
    """
    Plugin to display overview of analysis.

    Uses:
        QTableView: sanpy.interface.bErrorTable.errorTableView()
        QAbstractTableModel: sanpy.interface.bFileTable.pandasModel
    """
    myHumanName = 'Detection Parameters'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        logger.info('aaa')
        #self.dDict = sanpy.bDetection.getDefaultDetection()
        _currentDetection = None
        _detectionDict = None
        if self.ba is not None:
            # TODO: get the ba detection dict "detectionName"
            #   pull the detection class master dict
            baDetectionDict = self.ba.getDetectionDict()  # can be None
            if baDetectionDict is not None:
                _currentDetection = baDetectionDict['detectionName']
                _detectionDict = self.getSanPyApp().getDetectionClass().getMasterDict(_currentDetection)    

        if _detectionDict is None and self.getSanPyApp() is not None:
            # get the list
            presetList = self.getSanPyApp().getDetectionClass().getDetectionPresetList()
            # select first in list
            _currentDetection = presetList[0]
            _detectionDict = self.getSanPyApp().getDetectionClass().getMasterDict(_currentDetection)        
            #_detectionDict = copy.deepcopy(_detectionDict)

        self._detectionDict = _detectionDict  # The full master list

        # the name of the detection dict in ba OR the first detection type in detection class
        self._currentDetection = _currentDetection

        self.buildUI()

        #self.insertIntoScrollArea()

    def buildUI(self):

        self.vLayout = QtWidgets.QVBoxLayout()

        # top controls
        hControlLayout = QtWidgets.QHBoxLayout()

        fileName = 'None'
        if self.ba is not None:
            fileName = self.ba.getFileName()
        self.fileNameLabel = QtWidgets.QLabel(f'File: {fileName}')
        hControlLayout.addWidget(self.fileNameLabel, alignment=QtCore.Qt.AlignLeft)

        aName = 'Detect'
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton, alignment=QtCore.Qt.AlignLeft)

        aName = 'Set Defaults'
        aButton = QtWidgets.QPushButton(aName)
        aButton.clicked.connect(partial(self.on_button_click, aName))
        hControlLayout.addWidget(aButton, alignment=QtCore.Qt.AlignLeft)

        # get list of detection presets
        detectionPresetList = self.getSanPyApp().getDetectionClass().getDetectionPresetList()

        aComboBox = QtWidgets.QComboBox()
        #detectionPresets = sanpy.bDetection.getDetectionPresetList()
        for detectionPreset in detectionPresetList:
            aComboBox.addItem(detectionPreset)
        aComboBox.setCurrentText(detectionPresetList[0])
        aComboBox.currentTextChanged.connect(self.on_select_detection_preset)

        hControlLayout.addWidget(aComboBox, alignment=QtCore.Qt.AlignLeft)

        hControlLayout.addStretch()

        '''
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
        '''

        #
        self.vLayout.addLayout(hControlLayout)

        self.vLayoutParams = self.buildUI2()
        self.vLayout.addLayout(self.vLayoutParams)

        # finalize
        #self.setLayout(self.vLayout)

        #
        # scroll area again
        self.fuckWidget = QtWidgets.QWidget()
        self.fuckWidget.setLayout(self.vLayout)

        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True);
        self.scrollArea.setWidget(self.fuckWidget)

        self.finalLayout = QtWidgets.QVBoxLayout()
        self.finalLayout.addWidget(self.scrollArea)

        # finalize
        self.setLayout(self.finalLayout)

    def buildUI2(self):

        # list of keys/columns in main analysis dir file list
        analysisDirDict = sanpy.analysisDir.sanpyColumns
        #dDict = self.dDict
        dDict = self._detectionDict

        vLayoutParams = QtWidgets.QGridLayout()

        self.widgetDict = {}

        row = 0
        col = 0
        rowSpan = 1
        colSpan = 1
        for k,v in dDict.items():
            col = 0

            # k is the name in spike dictionary
            paramName = k
            #defaultValue = v['defaultValue']
            currentValue = v['currentValue']
            valueType = v['type']  # from ('int', 'float', 'boolean', 'string', detectionTypes_)
            units = v['units']
            humanName = v['humanName']
            description = v['description']
            allowNone = v['allowNone']  # set special value for spin box

            inAnalysisDir = paramName in analysisDirDict.keys()

            # add an '*' for params in main file table keys/columns
            aName = ' '
            if inAnalysisDir:
                aName = '*'
            aLabel = QtWidgets.QLabel(aName)
            vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
            col += 1

            # for debugging
            '''
            aLabel = QtWidgets.QLabel(paramName)
            vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
            col += 1
            '''

            aLabel = QtWidgets.QLabel(humanName)
            vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
            col += 1

            # for debugging
            '''
            aLabel = QtWidgets.QLabel(valueType)
            vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
            col += 1
            '''

            aLabel = QtWidgets.QLabel(units)
            vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
            col += 1

            aWidget = None
            if valueType == 'int':
                aWidget = QtWidgets.QSpinBox()
                aWidget.setRange(0, 2**16)  # minimum is used for setSpecialValueText()
                aWidget.setSpecialValueText("None")  # displayed when widget is set to minimum
                if currentValue is None or math.isnan(currentValue):
                    aWidget.setValue(0)
                else:
                    aWidget.setValue(currentValue)
                aWidget.setKeyboardTracking(False) # don't trigger signal as user edits
                aWidget.valueChanged.connect(partial(self.on_spin_box, paramName))
            elif valueType == 'float':
                aWidget = QtWidgets.QDoubleSpinBox()
                aWidget.setRange(-1e9, +1e9)  # minimum is used for setSpecialValueText()
                aWidget.setSpecialValueText("None")  # displayed when widget is set to minimum

                #logger.info(f'XXXXX paramName:{paramName} currentValue:{currentValue} {type(currentValue)}')

                if currentValue is None or math.isnan(currentValue):
                    aWidget.setValue(-1e9)
                else:
                    aWidget.setValue(currentValue)
                aWidget.setKeyboardTracking(False) # don't trigger signal as user edits
                aWidget.valueChanged.connect(partial(self.on_spin_box, paramName))
            elif valueType == 'list':
                # text edit a list
                pass
            elif valueType in ['bool', 'boolean']:
                # popup of True/False
                aWidget = QtWidgets.QComboBox()
                aWidget.addItem('True')
                aWidget.addItem('False')
                aWidget.setCurrentText(str(currentValue))
                aWidget.currentTextChanged.connect(partial(self.on_bool_combo_box, paramName))
            elif valueType == 'string':
                # text edit
                aWidget = QtWidgets.QLineEdit(currentValue)
                #aWidget.setKeyboardTracking(False) # don't trigger signal as user edits
                #aWidget.setValidator(QIntValidator())
                #aWidget.setMaxLength(4)
                aWidget.setAlignment(QtCore.Qt.AlignLeft)
                #aWidget.setFont(QFont("Arial",20))
                aWidget.editingFinished.connect(partial(self.on_text_edit, aWidget, paramName))
            elif valueType == 'sanpy.bDetection.detectionTypes':
                aWidget = QtWidgets.QComboBox()
                detectionTypes = sanpy.bDetection.detectionTypes
                for theType in detectionTypes:
                    aWidget.addItem(theType.name)
                aWidget.setCurrentText(str(currentValue))
                aWidget.currentTextChanged.connect(partial(self.on_detection_type_combo_box, paramName))
            else:
                logger.error(f'Did not understand valueType:"{valueType}" for parameter:"{paramName}"')

            if aWidget is not None:
                self.widgetDict[paramName] = aWidget
                vLayoutParams.addWidget(aWidget, row, col, rowSpan, colSpan)
            #
            col += 1

            # add a 'None' button for detection parameters that allow it
            if allowNone:
                aName = f'{paramName}_none'
                aButton = QtWidgets.QPushButton('Set None')
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

    def _setDict(self, paramName, value):
        logger.info(f'Setting dDict key:"{paramName}" to value "{value}" type:{type(value)}')
        #self.dDict[paramName] = value
        if value == -1e9:
            #print(f'TWEAK paramName:{paramName} --->>> value:', value)
            value = None
        #ok = self.detectionClass.setValue(paramName, value)
        # if not ok:
        #     logger.error('')
        self._detectionDict[paramName]['currentValue'] = value

    def on_bool_combo_box(self, paramName, text):
        #logger.info(f'paramName:{paramName} text:"{text}" {type(text)}')
        value = text == 'True'
        self._setDict(paramName, value)

    def on_detection_type_combo_box(self, paramName, text):
        #logger.info(f'paramName:"{paramName}" text:"{text}"')
        self._setDict(paramName, text)

    def on_text_edit(self, aWidget, paramName):
        text = aWidget.text()
        #logger.info(f'paramName:{paramName} text:"{text}"')
        self._setDict(paramName, text)

    def on_spin_box(self, paramName, value):
        """
        When QDoubldeSpinBox accepts None, value is -1e9
        """
        #logger.info(f'paramName:{paramName} value:"{value}" {type(value)}')
        self._setDict(paramName, value)

    def detect(self):
        logger.info('detecting spikes')
        
        if self.ba is None:
            return

        # spike detect
        self.ba.spikeDetect(self._detectionDict)

        # update interface
        self.signalDetect.emit(self.ba)

    def on_select_detection_preset(self, detectionPreset : str):
        """User selected a detection preset from combobox.
        """
        logger.info(f'detectionPreset:"{detectionPreset}"')
        #detectionPreset = sanpy.bDetection.detectionPresets[detectionPreset]
        #detectionPreset = sanpy.bDetection.detectionPresets(detectionPreset)
        #self.detectionClass.setToType(detectionPreset)
        
        # grab the detection from sanpy app
        self._detectionDict = self.getSanPyApp().getDetectionClass().getMasterDict(detectionPreset)

        self.replot()

    def on_button_click(self, buttonName):
        #logger.info(f'buttonNme:{buttonName}')
        # set to a defined preset
        # self.dDict = sanpy.bDetection.getDefaultDetection()
        if buttonName == 'Detect':
            # take our current dDict and ba.detectSpikes
            # need to signal main interface we did this
            self.detect()
        elif buttonName == 'Set Defaults':
            detectionPreset = sanpy.bDetection.detectionPresets.default
            self.detectionClass.setToType(detectionPreset)
            # refresh interface
            self.replot()
        
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

        elif buttonName.endswith('_none'):
            # set a parameter to None, will only work if 'allowNone'
            paramName = buttonName.replace('_none', '')
            self._setDict(paramName, None)
            self.replot()

        else:
            logger.warning(f'Button "{buttonName}" not understood.')

    def replot(self):
        #if self.ba is None:
        #    return

        logger.info('')

        # was this
        #detectionClass = self.detectionClass
        detectionDict = self._detectionDict

        #for detectionParam in detectionClass.keys():
        for detectionParam in detectionDict.keys():
            if detectionParam not in self.widgetDict.keys():
                logger.warning(f'XXX detectionParam:{detectionParam} missing')
                continue

            #currentValue = v['currentValue']
            #currentValue = detectionClass.getValue(detectionParam)
            currentValue = detectionDict[detectionParam]['currentValue']

            if currentValue == -1e9:
                logger.error(f'XXXXX detectionParam:{detectionParam} currentValue:{currentValue} {type(currentValue)}')
                currentValue = None

            aWidget = self.widgetDict[detectionParam]
            if isinstance(aWidget, QtWidgets.QSpinBox):
                try:
                    if currentValue is None or math.isnan(currentValue):
                        aWidget.setValue(0)
                    else:
                        aWidget.setValue(currentValue)
                except (TypeError) as e:
                    logger.error(f'QSpinBox detectionParam:{detectionParam} ... {e}')
            elif isinstance(aWidget, QtWidgets.QDoubleSpinBox):
                try:
                    if currentValue is None or math.isnan(currentValue):
                        aWidget.setValue(-1e9)
                    else:
                        aWidget.setValue(currentValue)
                except (TypeError) as e:
                    logger.error(f'QDoubleSpinBox detectionParam:{detectionParam} ... {e}')
            elif isinstance(aWidget, QtWidgets.QComboBox):
                aWidget.setCurrentText(str(currentValue))
            elif isinstance(aWidget, QtWidgets.QLineEdit):
                aWidget.setText(str(currentValue))
            else:
                logger.info(f'key "{detectionParam}" has value "{currentValue}" but widget type "{type(aWidget)}" not understood.')

    def slot_switchFile(self, rowDict, ba, replot=True):
        # don't replot until we set our detectionClass
        replot = False
        super().slot_switchFile(rowDict, ba, replot=replot)

        # grab a copy to modify and then set on 'detect'
        #logger.error('    CHANGE THIS BACK\ncaKymograph turning of switch_file\n')
        
        # before we detect a ba, its detection dict is None
        baDetectionDict = self.ba.getDetectionDict()  # can be None
        if baDetectionDict is not None:
            _currentDetection = baDetectionDict['detectionName']
            _detectionDict = self.getSanPyApp().getDetectionClass().getMasterDict(_currentDetection)    

            self._detectionDict = _detectionDict  # The full master list
            self._currentDetection = _currentDetection  # name of the current detection

            logger.info('TODO: set detection name combo box')

        self.replot()

if __name__ == '__main__':

    path = '/Users/cudmore/Sites/SanPy/data/19114001.abf'
    ba = sanpy.bAnalysis(path)

    bd = sanpy.bDetection()  # gets default
    dDict = bd.getDetectionDict('SA Node')

    ba.spikeDetect(dDict)
    print(ba.numSpikes)

    import sys
    app = QtWidgets.QApplication([])

    dp = detectionParams(ba=ba)
    dp.show()

    '''
    scrollArea = dp.insertIntoScrollArea()
    if scrollArea is not None:
        scrollArea.show()
    else:
        dp.show()
    '''

    sys.exit(app.exec_())
