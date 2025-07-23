from PyQt5 import QtGui, QtCore, QtWidgets

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis


class KymRoiWidget_Base(QtWidgets.QWidget):
    def __init__(self, kymRoiAnalysis: KymRoiAnalysis):
        super().__init__()

        self._kymRoiAnalysis = kymRoiAnalysis
        self._currentChannel = 0

    def slot_switchChannel(self, channel: int):
        self._currentChannel = channel
