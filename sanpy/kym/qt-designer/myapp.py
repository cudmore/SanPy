import sys
from functools import partial
import inspect

from PyQt5 import QtCore, QtWidgets  # , uic
# import pyqtgraph as pg

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

"""
    # Convert the Designer ui file to a python class.
    
    pyuic5 -x mymainwindow2.ui -o mymainwindow2.py
"""

# import the designer class (mymainwindow2 was generated with pyuic5)
from mymainwindow2 import Ui_MainWindow

# print(f"Ui_MainWindow:{globals()['Ui_MainWindow']}")

class SanPyGui():
    """GUI class that wraps a pyuic generated class.
    
    Add functions to make life easier.
    """
    def __init__(self, myMainWindow, uiClassName : str):
        """
        Parameters
        ----------
        myMainWindow : QWidget
            Usually a QMainWindow
        uiClassName : str
            Imported class from Qt Designer (e.g. from mymainwindow2 import Ui_MainWindow)
        """
        super().__init__()

        _classConstructor = globals()[uiClassName]
        self._ui = _classConstructor()
        
        logger.info(f'self._ui:{self._ui} is class:{inspect.isclass(self._ui)}')

        self._ui.setupUi(myMainWindow)  # setupUi() is a function inherited from "Ui_MainWindow"

        self.widgetList = []
        # A list of string where each item is the name of a QWidget

        _attrList = dir(self._ui)
        for attrStr in _attrList:
            widget = getattr(self._ui, attrStr)
            if isinstance(widget, QtWidgets.QWidget):
                # logger.info(f'attrStr:{attrStr}')
                self.widgetList.append(attrStr)

        self._installCallbacks()

    def _installCallbacks(self):
        """Install callbacks for each QWidget.
        """
        _ignoreList = (QtWidgets.QLabel, QtWidgets.QGroupBox, QtWidgets.QSplitter)
        
        for widgetStr in self.widgetList:
            # logger.info(f'widget:{widgetStr}')
            widget = getattr(self._ui, widgetStr)
            if isinstance(widget, QtWidgets.QCheckBox):
                widget.stateChanged.connect(partial(self.on_check_click, widget.objectName()))
            
            elif isinstance(widget, QtWidgets.QPushButton):
                widget.clicked.connect(
                    partial(self._on_button_click, widget.objectName())
                    )
            
            elif isinstance(widget, QtWidgets.QAbstractSpinBox):
                widget.setKeyboardTracking(False)  # could be done in Qt Designer
                widget.valueChanged.connect(
                    partial(self._on_spinbox, widget.objectName())
                    )
            
            elif isinstance(widget, QtWidgets.QComboBox):
                widget.currentTextChanged.connect(
                    partial(self._on_combobox, widget.objectName())
                    )
            
            elif isinstance(widget, _ignoreList):
                pass
            
            elif isinstance(widget, QtWidgets.QWidget):
                # if QWidget and we did not install callback above
                pass

            else:
                logger.warning(f'no widget callback for "{widgetStr}" {widget}')

    @QtCore.pyqtSlot()
    def on_check_click(self, name, value):
        logger.info(f'name:{name} value:{value}')
    
    def _on_button_click(self, name):
        logger.info(f'name:{name}')
    
    def _on_spinbox(self, name, value):
        logger.info(f'name:{name} value:{value}')
    
    def _on_combobox(self, name, value):
        logger.info(f'name:{name} value:{value}')
    
    def getWidget(self, name : str):
        """Get a widget from name.
        """
        if name not in self.widgetList:
            logger.error(f'"{name}" not in available widget. Widgets are {self.widgetList}')
            return
        return getattr(self._ui, name)
    
    def toggleWidget(self, name):
        """Toggle visibility of a widget.

        Layout can not be toggled.
        """
        _widget = self.getWidget(name)
        
        if _widget is None:
            return
        
        if isinstance(_widget, QtWidgets.QLayout):
            logger.error(f'Can not toggle QLayout visibility -> "{name}"')
            return
        
        _visible = not _widget.isVisible()
        _widget.setVisible(_visible)
        
        return _visible
    
# class myMainWindow(QtWidgets.QMainWindow, Ui_Form):
class myMainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        # v1
        # _userInterface = uic.loadUi("mymainwindow2.ui", self)

        # v2, I want this !!!
        # self.ui = Ui_MainWindow()  # instantiate the gui class (QMainWindow)
        # self.ui.setupUi(self)  # set our entire GUI interface to what is specified in designer

        self.ui = SanPyGui(self, 'Ui_MainWindow')

if __name__ == '__main__':

    # uiclass, baseclass = pg.Qt.loadUiType("mymainwindow.ui")
    # print(f'uiclass:{uiclass}')
    # print(f'baseclass:{baseclass}')

    app = QtWidgets.QApplication(sys.argv)
    myWindow = myMainWindow()
    myWindow.show()

    
    # myWindow.ui.toggleWidget('layoutWidget') # corresponds to 'verticalLayout_left'
    # myWindow.ui.toggleWidget('layoutWidget_2') # corresponds to 'verticalLayout_right'

    # attrList = dir(myWindow.ui)
    # for attr in attrList:
    #     if '_' in attr and '__' not in attr:
    #         print(attr)

    sys.exit(app.exec_())