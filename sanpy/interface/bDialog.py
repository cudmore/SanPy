# 20210522

# from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5 import QtWidgets

"""
General purpose dialogs
"""


def okDialog(message, informativeText=None):
    """
    message:
    """
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Warning)
    msg.setText(message)
    if informativeText is not None:
        msg.setInformativeText(informativeText)
    msg.setWindowTitle(message)
    retval = msg.exec_()
    return retval


def okCancelDialog(message, informativeText=None):
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Warning)
    msg.setText(message)
    if informativeText is not None:
        msg.setInformativeText(informativeText)
    msg.setWindowTitle(message)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
    msg.setDefaultButton(QtWidgets.QMessageBox.Ok)
    retval = msg.exec_()
    return retval


def yesNoCancelDialog(message, informativeText=None):
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Warning)
    msg.setText(message)
    if informativeText is not None:
        msg.setInformativeText(informativeText)
    msg.setWindowTitle(message)
    msg.setStandardButtons(
        QtWidgets.QMessageBox.Yes
        | QtWidgets.QMessageBox.No
        | QtWidgets.QMessageBox.Cancel
    )
    retval = msg.exec_()
    return retval
