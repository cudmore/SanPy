import math
import os
from functools import partial
import json
from typing import Union, Dict, List, Tuple, Optional, Optional

from PyQt5 import QtCore, QtWidgets, QtGui

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class SetMetaData(sanpyPlugin):

    myHumanName = "Set Meta Data"
    showInMenu = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._buildUI()
    
        if self.ba is not None:
            self.replot()

    def replot(self):
        if self.ba is None:
            # todo deactivate all controls
            return
        
        metaDataDict = self.ba.metaData

        logger.info(metaDataDict)

        for k,v in self.ba.metaData.items():
            if not k in self._widgetDict.keys():
                k = k.capitalize()

                if not k in self._widgetDict.keys():
                    logger.error(f'key "{k}" is not in metadata keys {self._widgetDict.keys()}')
                    continue

            if k == 'Include':
                # combo box
                if v == 'yes':
                    self._widgetDict[k].setCurrentIndex(0)  #
                elif v == 'no':
                    self._widgetDict[k].setCurrentIndex(1)  #
                else:
                    logger.error(f'did not understand control "{k}" value "{v}"')
                
            elif k == 'Sex':
                # combo box
                if v == 'unknown':
                    self._widgetDict[k].setCurrentIndex(0)  #
                elif v == 'female':
                    self._widgetDict[k].setCurrentIndex(1)  #
                elif v == 'male':
                    self._widgetDict[k].setCurrentIndex(2)  #
                else:
                    logger.error(f'did not understand control "{k}" value "{v}"')

            else:
                # line edit
                try:
                    self._widgetDict[k].setText(v)
                except (AttributeError) as e:
                    logger.error(f'widget {k} is type {self._widgetDict[k]}')
                except(KeyError) as e:
                    logger.error(f'key "{k}" is not in metadata keys {self._widgetDict.keys()}')


    def _on_text_edit(self, aWidget, paramName):
        if self.ba is None:
            return
        logger.info(f'{aWidget} {paramName}')
        value = aWidget.text()

        if ';' in value:
            logger.warning(f'Semicolon (;) is not allowed -->> replacing with comma (,)')
            value = value.replace(';', ',')
        """
        TODO:
        # eventDict = setSpikeStatEvent
        setSpikeStatEvent = {}
        setSpikeStatEvent['ba'] = self.ba
        #setSpikeStatEvent["spikeList"] = self.getSelectedSpikes()
        setSpikeStatEvent["colStr"] = paramName
        setSpikeStatEvent["value"] = value

        logger.info(f"  -->> emit signalUpdateAnalysis:{setSpikeStatEvent}")
        self.signalUpdateAnalysis.emit(setSpikeStatEvent)
        """

        self.ba.metaData.setMetaData(paramName, value)

    def _on_combo_box(self, paramName : str, value : str):
        if self.ba is None:
            return
        logger.info(f'paramName:{paramName} value:{value}')
        if paramName == 'Include':
            if value == 'yes':
                self._widgetDict[paramName].setCurrentIndex(0)
            elif value == 'no':
                self._widgetDict[paramName].setCurrentIndex(1)
            else:
                logger.error(f'did not understand control "{paramName}" value "{value}"')
                return
            self.ba.metaData.setMetaData(paramName, value)

        elif paramName == 'Sex':
            if value == 'unknown':
                self._widgetDict[paramName].setCurrentIndex(0)
            elif value == 'female':
                self._widgetDict[paramName].setCurrentIndex(1)
            elif value == 'male':
                self._widgetDict[paramName].setCurrentIndex(2)
            else:
                logger.error(f'did not understand control "{paramName}" value "{value}"')
                return
            self.ba.metaData.setMetaData(paramName, value)

        else:
            logger.error(f'did not understand param name"{paramName}"')

    def _buildUI(self):
        self._widgetDict = {}
        
        vBoxLayout = self.getVBoxLayout()
        vBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        # current default of metadata, getMetaDataDict is static
        _metaData = sanpy.MetaData.getMetaDataDict()
        
        for paramName, paramValue in _metaData.items():
            logger.info(f'paramName:{paramName}')

            hBoxLayout = QtWidgets.QHBoxLayout()

            aLabel = QtWidgets.QLabel(paramName)
            hBoxLayout.addWidget(aLabel, alignment=QtCore.Qt.AlignLeft)

            if paramName == 'Include':
                aComboBox = QtWidgets.QComboBox()
                aComboBox.addItem('yes')
                aComboBox.addItem('no')
                aComboBox.currentTextChanged.connect(
                    partial(self._on_combo_box, paramName)
                )
                self._widgetDict[paramName] = aComboBox
                hBoxLayout.addWidget(aComboBox, alignment=QtCore.Qt.AlignLeft)

            elif paramName == 'Sex':
                aComboBox = QtWidgets.QComboBox()
                aComboBox.addItem('unknown')
                aComboBox.addItem('female')
                aComboBox.addItem('male')
                aComboBox.currentTextChanged.connect(
                    partial(self._on_combo_box, paramName)
                )
                self._widgetDict[paramName] = aComboBox
                hBoxLayout.addWidget(aComboBox, alignment=QtCore.Qt.AlignLeft)

            else:
                aLineEdit = QtWidgets.QLineEdit("")
                aLineEdit.editingFinished.connect(
                    partial(self._on_text_edit, aLineEdit, paramName)
                )
                self._widgetDict[paramName] = aLineEdit
                hBoxLayout.addWidget(aLineEdit, alignment=QtCore.Qt.AlignLeft)
            
            vBoxLayout.addLayout(hBoxLayout)


        