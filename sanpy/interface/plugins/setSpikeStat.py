from functools import partial

from PyQt5 import QtWidgets, QtGui, QtCore

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin


class ComboBox(QtWidgets.QComboBox):
    # https://code.qt.io/cgit/qt/qtbase.git/tree/src/widgets/widgets/qcombobox.cpp?h=5.15.2#n3173
    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        painter.setPen(self.palette().color(QtGui.QPalette.Text))

        # draw the combobox frame, focusrect and selected etc.
        opt = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(opt)
        painter.drawComplexControl(QtWidgets.QStyle.CC_ComboBox, opt)

        if self.currentIndex() < 0:
            opt.palette.setBrush(
                QtGui.QPalette.ButtonText,
                opt.palette.brush(QtGui.QPalette.ButtonText).color().lighter(),
            )
            if self.placeholderText():
                opt.currentText = self.placeholderText()

        # draw the icon and text
        painter.drawControl(QtWidgets.QStyle.CE_ComboBoxLabel, opt)


# setSpikeStatEvent = {
#     'spikeList': [],
#     'colStr': '',
#     'value': ''
# }


class SetSpikeStat(sanpyPlugin):
    """Plugin to provide an interface to set spike stats like condition, userType, include, etc.

    Get stat names and variables from sanpy.bAnalysisUtil.getStatList()
    """

    myHumanName = "Set Spike Stats"
    showInMenu = False

    def __init__(self, **kwargs):
        logger.info("")
        super().__init__(**kwargs)

        self.trueFalseItems = ["True", "False"]
        self.userTypeItems = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        self._buildUI()

        self._setState()

    def _buildUI(self):
        vBoxLayout = self.getVBoxLayout()
        vBoxLayout.setAlignment(QtCore.Qt.AlignTop)
        # vBoxLayout.setContentsMargins(0,0,0,0)

        # first row
        hBoxLayout = QtWidgets.QHBoxLayout()
        # hBoxLayout.setContentsMargins(0,0,0,0)
        vBoxLayout.addLayout(hBoxLayout)

        # a button to set
        self._setButton = QtWidgets.QPushButton("Set")
        self._setButton.clicked.connect(self.on_set_button)
        hBoxLayout.addWidget(self._setButton, alignment=QtCore.Qt.AlignLeft)

        # a label to report spike selection
        self._spikeLabel = QtWidgets.QLabel("0 Spikes")
        hBoxLayout.addWidget(self._spikeLabel, alignment=QtCore.Qt.AlignLeft)

        # second row
        hBoxLayout = QtWidgets.QHBoxLayout()
        # hBoxLayout.setContentsMargins(0,0,0,0)
        vBoxLayout.addLayout(hBoxLayout)

        # popup with column types
        _items = ["condition", "userType", "include"]
        self._statComboBox = ComboBox()
        for item in _items:
            self._statComboBox.addItem(item)
        # self._statComboBox.setPlaceholderText("Some placeholder text here")
        # self._statComboBox.setCurrentIndex(-1)
        self._statComboBox.setCurrentIndex(0)
        self._statComboBox.currentIndexChanged.connect(self.on_stat_change)
        hBoxLayout.addWidget(self._statComboBox, alignment=QtCore.Qt.AlignLeft)

        # line edit for user to enter values
        self._lineEdit = QtWidgets.QLineEdit("")
        # self._lineEdit.setReadOnly(True)  # for now our 1 edit widget is not editable
        # self._lineEdit.setKeyboardTracking(False) # don't trigger signal as user edits
        # self._lineEdit.setValidator(QIntValidator())
        # self._lineEdit.setMaxLength(4)
        self._lineEdit.setAlignment(QtCore.Qt.AlignLeft)
        self._lineEdit.editingFinished.connect(
            partial(self.on_text_edit, self._lineEdit)
        )
        hBoxLayout.addWidget(self._lineEdit, alignment=QtCore.Qt.AlignLeft)

        # popup with true false (for some column types like 'include')
        # switch to userType [1,2,3,4, ...]
        _items = ["True", "False"]
        self._valueComboBox = ComboBox()
        for item in _items:
            self._valueComboBox.addItem(item)
        # self._valueComboBox.setPlaceholderText("Some placeholder text here")
        # self._valueComboBox.setCurrentIndex(-1)
        self._valueComboBox.setEnabled(False)
        self._valueComboBox.setCurrentIndex(0)
        hBoxLayout.addWidget(self._valueComboBox, alignment=QtCore.Qt.AlignLeft)

    def _setState(self):
        """Set all ui based on state, the number of spikes and the popups selected."""

        _selectedSpikes = self.getSelectedSpikes()

        if _selectedSpikes == []:
            self._spikeLabel.setText("0 Spikes")
            self._setButton.setEnabled(False)
            self._statComboBox.setEnabled(False)
            self._lineEdit.setEnabled(False)
            self._valueComboBox.setEnabled(False)
            return

        self._setButton.setEnabled(True)
        self._statComboBox.setEnabled(True)

        self._spikeLabel.setText(f"{len(_selectedSpikes)} Spikes")

        # include sets combobox to trueFalseItems
        # userType sets combobox to userTypeItems
        colStr = self._statComboBox.currentText()

        # like a radio button, either one or the other but not both (disjoint)
        trueFalseEnabled = colStr in ["include", "userType"]
        self._lineEdit.setEnabled(not trueFalseEnabled)
        self._valueComboBox.setEnabled(trueFalseEnabled)

        # switch items in combobox
        if "userType" in colStr:
            items = self.userTypeItems
        elif colStr == "include":
            items = self.trueFalseItems
        else:
            items = None

        if trueFalseEnabled and items is not None:
            # set items in combo box and select item 0
            _numItems = self._valueComboBox.count()
            self._valueComboBox.clear()
            # logger.info(f'adding {items}')
            for item in items:
                self._valueComboBox.addItem(item)
            self._valueComboBox.setCurrentIndex(0)

    def on_set_button(self):
        """Respond to user clicking the 'set' button."""
        colStr = self._statComboBox.currentText()

        if colStr in ["include"]:
            value = self._valueComboBox.currentText()
            if value == 'True':
                value = True
            else:
                value = False
        elif colStr in ["userType"]:
            value = self._valueComboBox.currentText()
        else:
            value = self._lineEdit.text()

        if colStr == "userType":
            value = int(value)

        # eventDict = setSpikeStatEvent
        setSpikeStatEvent = {}
        setSpikeStatEvent['ba'] = self.ba
        setSpikeStatEvent["spikeList"] = self.getSelectedSpikes()
        setSpikeStatEvent["colStr"] = colStr
        setSpikeStatEvent["value"] = value

        logger.info(f"  -->> emit signalUpdateAnalysis:{setSpikeStatEvent}")
        self.signalUpdateAnalysis.emit(setSpikeStatEvent)

    def on_stat_change(self, index: int):
        """User has selected an item in the stat combo box."""
        self._setState()

    def on_text_edit(self, widget: QtWidgets.QLineEdit):
        """User has finished editing the text for a column."""
        text = widget.text()
        logger.info(f"{text}")

    def replot(self):
        """Inherited."""
        self._setState()

    def selectSpikeList(self):
        """Inherited."""
        self.replot()


def testSetSpikeStat():
    import sys

    # load file
    path = "/Users/cudmore/Dropbox/data/san-ap/20191009_0006.abf"
    ba = sanpy.bAnalysis(path)

    # get all detection presets
    _detectionParams = sanpy.bDetection()
    # select 'SA Node' presets
    _dDict = _detectionParams.getDetectionDict("SA Node")

    ba.spikeDetect(_dDict)
    print(ba)

    # run the app
    app = QtWidgets.QApplication([])

    sss = SetSpikeStat(ba=ba)
    sss.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    testSetSpikeStat()
