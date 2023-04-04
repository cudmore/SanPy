from PyQt5 import QtCore, QtWidgets, QtGui

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

import sanpy
from sanpy.interface.plugins import sanpyPlugin


class sanpyLog(sanpyPlugin):
    """
    Plugin to display sanpy.log

    Good example of PyQt plugin
    """

    myHumanName = "SanPy Log"

    def __init__(self, **kwargs):
        """
        Args:
            ba (bAnalysis): Not required
        """
        super(sanpyLog, self).__init__(**kwargs)

        # self.pyqtWindow() # makes self.mainWidget

        layout = QtWidgets.QVBoxLayout()
        widget = QtWidgets.QPlainTextEdit()
        widget.setReadOnly(True)
        layout.addWidget(widget)

        # load sanpy.log
        logFilePath = sanpy.sanpyLogger.getLoggerFile()
        with open(logFilePath, "r") as f:
            lines = f.readlines()
        text = ""
        for line in lines:
            text += line  # line already has CR

        # add text to widget
        widget.document().setPlainText(text)

        logger.info(f"logFilePath: {logFilePath}")

        self._mySetWindowTitle()

        # self.setLayout(layout)
        self.getVBoxLayout().addLayout(layout)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication([])
    spl = sanpyLog()
    spl.show()
    sys.exit(app.exec_())
