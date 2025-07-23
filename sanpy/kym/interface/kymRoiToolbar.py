from typing import Optional
from functools import partial

from PyQt5 import QtCore, QtWidgets

import qtawesome as qta
import numpy as np
from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QGroupBox,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis
from sanpy.kym.kymRoiDetection import KymRoiDetection

from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)


class KymRoiGroupBox(QtWidgets.QGroupBox):
    """
    A widget to display and edit an roi.
    """

    signalRoiChanged = QtCore.pyqtSignal(object)  # (roi label)

    def __init__(
        self,
        kymRoiAnalysis: KymRoiAnalysis,
        kymRoiDetection: KymRoiDetection,
        groupName: str,
    ):

        super().__init__(title=groupName)

        self._kymRoiAnalysis = kymRoiAnalysis
        self._kymRoiDetection = kymRoiDetection
        self._groupName = groupName

        self._roiLabel = None  # set in slot_selectRoi()

        self._blockSlots = False

        self._buildUI()

    def slot_rio_changed(self, roiLabel: str):
        logger.warning('hard coding channel=0 ???')
        self.slot_selectRoi(channel=0, roiLabel=roiLabel)

    def slot_selectRoi(self, channel: int, roiLabel: Optional[str]):
        logger.info(f'channel:{channel} roiLabel:{roiLabel}')

        # always setTitle()
        _title = f'{self._groupName} ch {channel+1} roi {roiLabel}'
        self.setTitle(_title)

        self._roiLabel = roiLabel

        if roiLabel is not None:
            self.setEnabled(True)

            roi = self._kymRoiAnalysis.getRoi(roiLabel)
            _rectDict = roi.getRectDict()
            logger.info(
                f'  roi _rectDict:{_rectDict} '
            )  # pixels like [0, 512, 2000, 0]

            self._widgetDict['leftLabel'].setText(f"Left: {_rectDict['left']}")
            self._widgetDict['topLabel'].setText(f"Top: {_rectDict['top']}")
            self._widgetDict['rightLabel'].setText(f"Right: {_rectDict['right']}")
            self._widgetDict['bottomLabel'].setText(f"Bottom: {_rectDict['bottom']}")

            # set value of spinbox
            self._blockSlots = True  # TODO: use context manager
            _height = _rectDict['top'] - _rectDict['bottom']
            self._widgetDict['setHeight'].setValue(_height)
            self._blockSlots = False

        else:
            self.setEnabled(False)

    def _on_spin_box(self, name, value):
        """
        Slot to handle spin box value changes.
        """
        if self._blockSlots:
            logger.warning('blocked')
            return
        
        logger.info(f'spin box "{name}" value:{value}')

        if name == 'Height':
            # set backend height of roi in pixels
            self._kymRoiAnalysis.getRoi(roiLabel=self._roiLabel).setRoiHeightPixels(
                value
            )

        logger.info(f'-->> emit signalRoiChanged roi label:{self._roiLabel}')
        self.signalRoiChanged.emit(self._roiLabel)

    def _buildUI(self):
        """
        Build the UI for the group box.
        """
        self.setEnabled(False)

        self._widgetDict = {}

        # self.setTitle(self._groupName)
        # self.setCheckable(True)
        # self.setChecked(True)

        # self.setContentsMargins(self._contentMarginLeft, 0, 0, 0)

        # Create a layout for the group box
        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(mainLayout)  # main layout for self groupbox (inherited)

        _hBox1 = QtWidgets.QHBoxLayout()
        _hBox1.setAlignment(QtCore.Qt.AlignLeft)
        mainLayout.addLayout(_hBox1)

        _leftLabel = QtWidgets.QLabel("Left")
        _topLabel = QtWidgets.QLabel("Top")
        _rightLabel = QtWidgets.QLabel("Right")
        _bottomLabel = QtWidgets.QLabel("Bottom")

        _hBox1.addWidget(_leftLabel)
        _hBox1.addWidget(_topLabel)
        _hBox1.addWidget(_rightLabel)
        _hBox1.addWidget(_bottomLabel)

        # leftLabel.setAlignment(QtCore.Qt.AlignLeft)
        # leftLabel.setContentsMargins(self._contentMarginLeft, 0, 0, 0)
        self._widgetDict['leftLabel'] = _leftLabel
        self._widgetDict['topLabel'] = _topLabel
        self._widgetDict['rightLabel'] = _rightLabel
        self._widgetDict['bottomLabel'] = _bottomLabel

        # set height of roi in pixels
        _hBox2 = QtWidgets.QHBoxLayout()
        _hBox2.setAlignment(QtCore.Qt.AlignLeft)
        mainLayout.addLayout(_hBox2)

        spinBoxName = 'Height'
        _heightSpinBox = QtWidgets.QSpinBox()
        _heightSpinBox.setRange(0, 10000)
        _heightSpinBox.setValue(0)
        _heightSpinBox.setSingleStep(1)
        _heightSpinBox.setPrefix(f'{spinBoxName} ')
        _heightSpinBox.setSuffix(" (pixels)")
        _heightSpinBox.setAlignment(QtCore.Qt.AlignLeft)
        #
        _heightSpinBox.setKeyboardTracking(False)
        _heightSpinBox.valueChanged.connect(partial(self._on_spin_box, spinBoxName))
        #
        self._widgetDict['setHeight'] = _heightSpinBox
        _hBox2.addWidget(_heightSpinBox)

        # buttons for nudge roi left/right/up/down
        _nudgeLeftButton = QtWidgets.QPushButton(qta.icon('mdi6.arrow-left'), '')
        _nudgeLeftButton.setToolTip("Nudge Left")
        _nudgeRightButton = QtWidgets.QPushButton(qta.icon('mdi6.arrow-right'), '')
        _nudgeRightButton.setToolTip("Nudge Right")
        _nudgeUpButton = QtWidgets.QPushButton(qta.icon('mdi6.arrow-up'), '')
        _nudgeUpButton.setToolTip("Nudge Up")
        _nudgeDownButton = QtWidgets.QPushButton(qta.icon('mdi6.arrow-down'), '')
        _nudgeDownButton.setToolTip("Nudge Down")
        _hBox2.addWidget(_nudgeLeftButton)
        _hBox2.addWidget(_nudgeRightButton)
        _hBox2.addWidget(_nudgeUpButton)
        _hBox2.addWidget(_nudgeDownButton)
        _hBox2.addStretch(1)
        # connect buttons to slots
        _nudgeLeftButton.clicked.connect(partial(self.nudgeRoi, direction='left'))
        _nudgeRightButton.clicked.connect(partial(self.nudgeRoi, direction='right'))
        _nudgeUpButton.clicked.connect(partial(self.nudgeRoi, direction='up'))
        _nudgeDownButton.clicked.connect(partial(self.nudgeRoi, direction='down'))

    def nudgeRoi(self, direction: str):
        """
        Nudge the roi in the specified direction.
        """
        logger.info(f'nudgeRoi {self._roiLabel} {direction}')
        # self._kymRoiDetection.nudgeRoi(roiLabel=roiLabel, direction=direction)
        self._kymRoiAnalysis.getRoi(roiLabel=self._roiLabel).nudge(direction)

        logger.info(f'-->> emit signalRoiChanged roi label:{self._roiLabel}')
        self.signalRoiChanged.emit(self._roiLabel)
