"""
Display a tif kymograph and allow user to modify a rect roi
"""

import sys
import numpy as np
from functools import partial

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class kymographImage(pg.ImageItem):
    """
    Utility class to inherit and redefine some functions.
    """
    def mouseClickEvent(self, event):
        #print("Click", event.pos())
        x = event.pos().x()
        y = event.pos().y()

    def mouseDragEvent(self, event):
        return

        if event.isStart():
            print("Start drag", event.pos())
        elif event.isFinish():
            print("Stop drag", event.pos())
        else:
            print("Drag", event.pos())

    def old_hoverEvent(self, event):
        logger.info('')
        if not event.isExit():
            # the mouse is hovering over the image; make sure no other items
            # will receive left click/drag events from here.
            event.acceptDrags(pg.QtCore.Qt.LeftButton)
            event.acceptClicks(pg.QtCore.Qt.LeftButton)

class kymWidget(QtWidgets.QWidget):

    signalKymographRoiChanged = QtCore.pyqtSignal(object)  # list of [l, t, r, b]
    signalSwitchToMolar = QtCore.pyqtSignal(object, object, object)  # (boolean, kd, caConc)

    def __init__(self, ba=None, parent=None):
        super(kymWidget, self).__init__(parent)

        logger.info('')
        
        self.ba = ba
        self.myImageItem = None  # kymographImage
        self.myLineRoi = None
        self.myLineRoiBackground = None
        self.myColorBarItem = None
        self.buildUI()
        self._replot()

    def on_convert_to_nm_clicked(self, value):
        onOff = value==2
        #self.detectionWidget.toggleCrosshair(onOff)
        self.signalSwitchToMolar.emit(onOff)

    def on_button_click(self, name):
        logger.info(name)
        if name == 'Reset ROI':
            newRect = self.ba.resetKymographRect()
            #self.ba._updateTifRoi(newRect)
            self._replot()
            self.signalKymographRoiChanged.emit(newRect)  # underlying _abf has new rect

        else:
            logger.info(f'Case not taken: {name}')

    def buildUI(self):
        # one row of controls and then kymograph image
        self.myVBoxLayout = QtWidgets.QVBoxLayout(self)
        self.myVBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        controlBarLayout = QtWidgets.QHBoxLayout()

        # todo: add checkbox to turn kn/rest calculation on off
        #            need signal
        convertToMolarCheckBox = QtWidgets.QCheckBox('Convert to Molar')
        convertToMolarCheckBox.setChecked(False)
        convertToMolarCheckBox.stateChanged.connect(self.on_convert_to_nm_clicked)
        convertToMolarCheckBox.setDisabled(True)
        controlBarLayout.addWidget(convertToMolarCheckBox)

        #
        # kd
        kdLabel = QtWidgets.QLabel('kd')
        controlBarLayout.addWidget(kdLabel)

        kdDefault = 22.1
        self.kdSpinBox = QtWidgets.QDoubleSpinBox()
        self.kdSpinBox.setMinimum(0)
        self.kdSpinBox.setMaximum(+1e6)
        self.kdSpinBox.setValue(kdDefault)
        self.kdSpinBox.setDisabled(True)
        #self.kdSpinBox.setSpecialValueText("None")
        controlBarLayout.addWidget(self.kdSpinBox)

        #
        # resting Ca
        restingCaLabel = QtWidgets.QLabel('Resting Ca')
        controlBarLayout.addWidget(restingCaLabel)

        restingCaDefault = 113.7
        self.restingCaSpinBox = QtWidgets.QDoubleSpinBox()
        self.restingCaSpinBox.setMinimum(0)
        self.restingCaSpinBox.setMaximum(+1e6)
        self.restingCaSpinBox.setValue(restingCaDefault)
        self.restingCaSpinBox.setDisabled(True)
        #self.kdSpinBox.setSpecialValueText("None")
        controlBarLayout.addWidget(self.restingCaSpinBox)

        buttonName = 'Reset ROI'
        button = QtWidgets.QPushButton(buttonName)
        #button.setToolTip('Detect spikes using dV/dt threshold.')
        button.clicked.connect(partial(self.on_button_click,buttonName))
        controlBarLayout.addWidget(button)

        self.myVBoxLayout.addLayout(controlBarLayout) #

        #
        # display the (min, max, cursor) intensity
        controlBarLayout0 = QtWidgets.QHBoxLayout()
        # min
        self.tifMinLabel = QtWidgets.QLabel('Min:')
        controlBarLayout0.addWidget(self.tifMinLabel)
        # max
        self.tifMaxLabel = QtWidgets.QLabel('Max:')
        controlBarLayout0.addWidget(self.tifMaxLabel)
        # roi min
        self.roiMinLabel = QtWidgets.QLabel('ROI Min:')
        controlBarLayout0.addWidget(self.roiMinLabel)
        # roi max
        self.roiMaxLabel = QtWidgets.QLabel('ROI Max:')
        controlBarLayout0.addWidget(self.roiMaxLabel)

        # background min
        self.backgroundRoiMinLabel = QtWidgets.QLabel('Background Min:')
        controlBarLayout0.addWidget(self.backgroundRoiMinLabel)
        # background max
        self.backgroundRoiMaxLabel = QtWidgets.QLabel('Background Max:')
        controlBarLayout0.addWidget(self.backgroundRoiMaxLabel)

        # cursor
        self.tifCursorLabel = QtWidgets.QLabel('Cursor:')
        controlBarLayout0.addWidget(self.tifCursorLabel)
        #
        self.myVBoxLayout.addLayout(controlBarLayout0) #


        #
        # kymograph
        self.view = pg.GraphicsLayoutWidget()
        #self.view.show()

        row = 0
        colSpan = 1
        rowSpan = 1
        self.kymographPlot = self.view.addPlot(row=row, col=0, rowSpan=rowSpan, colSpan=colSpan)
        self.kymographPlot.enableAutoRange()
        # turn off x/y dragging of deriv and vm
        self.kymographPlot.setMouseEnabled(x=False, y=False)
        # hide the little 'A' button to rescale axis
        self.kymographPlot.hideButtons()
        # turn off right-click menu
        self.kymographPlot.setMenuEnabled(False)
        # hide by default
        self.kymographPlot.hide()  # show in _replot() if self.ba.isKymograph()

        self.myVBoxLayout.addWidget(self.view)

    def _replot(self):
        logger.info('')

        if self.ba is None:
            return

        self.kymographPlot.clear()
        self.kymographPlot.show()

        myTif = self.ba.tifData
        print('  myTif:', myTif)
        #self.myImageItem = pg.ImageItem(myTif, axisOrder='row-major')
        #  TODO: set height to micro-meters
        axisOrder='row-major'
        rect=[0,0, self.ba.recordingDur, self.ba.tifData.shape[0]]  # x, y, w, h
        if self.myImageItem is None:
            # first time build
            self.myImageItem = kymographImage(myTif, axisOrder=axisOrder,
                            rect=rect)
            # redirect hover to self (to display intensity
            self.myImageItem.hoverEvent = self.hoverEvent
        else:
            # second time update
            myTif = self.ba.tifData
            self.myImageItem.setImage(myTif, axisOrder=axisOrder,
                            rect=rect)
        self.kymographPlot.addItem(self.myImageItem)

        # color bar with contrast !!!
        if myTif.dtype == np.dtype('uint8'):
            bitDepth = 8
        elif myTif.dtype == np.dtype('uint16'):
            bitDepth = 16
        else:
            bitDepth = 16
            logger.error(f'Did not recognize tif dtype: {myTif.dtype}')

        minTif = np.nanmin(myTif)
        maxTif = np.nanmax(myTif)
        #print(type(dtype), dtype)  # <class 'numpy.dtype[uint16]'> uint16

        cm = pg.colormap.get('Greens_r', source='matplotlib') # prepare a linear color map
        #values = (0, 2**bitDepth)
        #values = (0, maxTif)
        values = (0, 2**12)
        limits = (0, 2**12)
        #logger.info(f'color bar bit depth is {bitDepth} with values in {values}')
        doColorBar = False
        if doColorBar:
            if self.myColorBarItem == None:
                self.myColorBarItem = pg.ColorBarItem( values=values, limits=limits,
                                                interactive=True,
                                                label='', cmap=cm, orientation='horizontal' )
            # Have ColorBarItem control colors of img and appear in 'plot':
            self.myColorBarItem.setImageItem( self.myImageItem, insert_in=self.kymographPlot )
            self.myColorBarItem.setLevels(values=values)

        kymographRect = self.ba.getKymographRect()
        if kymographRect is not None:
            # TODO: I guess we always have a rect, o.w. this would be a runtime error
            xRoiPos = kymographRect[0]
            yRoiPos = kymographRect[3]
            top = kymographRect[1]
            right = kymographRect[2]
            bottom = kymographRect[3]
            widthRoi = right - xRoiPos + 1
            #heightRoi = bottom - yRoiPos + 1
            heightRoi = top - yRoiPos + 1
        '''
        else:
            #  TODO: Put this logic into function in bAbfText
            pos, size = self.ba.defaultTifRoi()

            xRoiPos = 0  # startSeconds
            yRoiPos = 0  # pixels
            widthRoi = myTif.shape[1]
            heightRoi = myTif.shape[0]
            tifHeightPercent = myTif.shape[0] * 0.2
            #print('tifHeightPercent:', tifHeightPercent)
            yRoiPos += tifHeightPercent
            heightRoi -= 2 * tifHeightPercent
        '''
        # TODO: get this out of replot, recreating the ROI is causing runtime error
        pos = (xRoiPos,yRoiPos)
        size = (widthRoi,heightRoi)
        if self.myLineRoi is None:
            self.myLineRoi = pg.ROI(pos=pos, size=size, parent=self.myImageItem)
            self.myLineRoi.addScaleHandle((0,0), (1,1), name='topleft')  # at origin
            self.myLineRoi.addScaleHandle((0.5,0), (0.5,1))  # top center
            self.myLineRoi.addScaleHandle((0.5,1), (0.5,0))  # bottom center
            self.myLineRoi.addScaleHandle((0,0.5), (1,0.5))  # left center
            self.myLineRoi.addScaleHandle((1,0.5), (0,0.5))  # right center
            self.myLineRoi.addScaleHandle((1,1), (0,0), name='bottomright')  # bottom right
            self.myLineRoi.sigRegionChangeFinished.connect(self.kymographChanged)
        else:
            self.myLineRoi.setPos(pos, finish=False)
            self.myLineRoi.setSize(size, finish=False)

        #
        # background kymograph ROI
        backgroundRect = self.ba.getKymographBackgroundRect()  # keep this in the backend
        if backgroundRect is not None:
            xRoiPos = backgroundRect[0]
            yRoiPos = backgroundRect[3]
            top = backgroundRect[1]
            right = backgroundRect[2]
            bottom = backgroundRect[3]
            widthRoi = right - xRoiPos + 1
            #heightRoi = bottom - yRoiPos + 1
            heightRoi = top - yRoiPos + 1
        pos = (xRoiPos,yRoiPos)
        size = (widthRoi,heightRoi)

        if self.myLineRoiBackground is None:
            # TODO: get this out of replot, recreating the ROI is causing runtime error
            self.myLineRoiBackground = pg.ROI(pos=pos, size=size, parent=self.myImageItem)
        else:
            self.myLineRoiBackground.setPos(pos, finish=False)
            self.myLineRoiBackground.setSize(size, finish=False)

        # update min/max labels
        # TODO: also display min max within roi ???
        self.tifMinLabel.setText(f'Min:{minTif}')
        self.tifMaxLabel.setText(f'Max:{maxTif}')

        # update min/max displayed to user
        self._updateRoiMinMax(kymographRect)
        self._updateBackgroundRoiMinMax(backgroundRect)

    def _updateBackgroundRoiMinMax(self, backgroundRect=None):
        """
        update background roi

        TODO: Add self.ba.getBackGroundStats()

        """
        logger.warning(f'Need to add interface for user to adjust background roi')
        if backgroundRect is None:
            backgroundRect = self.ba.getKymographBackgroundRect()

        left = backgroundRect[0]
        top = backgroundRect[1]
        right = backgroundRect[2]
        bottom = backgroundRect[3]

        myTif = self.ba.tifData
        tifClip = myTif[bottom:top, left:right]

        roiMin = np.nanmin(tifClip)
        roiMax = np.nanmax(tifClip)

        self.backgroundRoiMinLabel.setText(f'Background Min:{roiMin}')
        self.backgroundRoiMaxLabel.setText(f'Background Max:{roiMax}')

    def _updateRoiMinMax(self, theRect):
        left = theRect[0]
        top = theRect[1]
        right = theRect[2]
        bottom = theRect[3]

        myTif = self.ba.tifData
        tifClip = myTif[bottom:top, left:right]

        roiMin = np.nanmin(tifClip)
        roiMax = np.nanmax(tifClip)

        self.roiMinLabel.setText(f'ROI Min:{roiMin}')
        self.roiMaxLabel.setText(f'ROI Max:{roiMax}')

    def kymographChanged(self, event):
        """
        User finished gragging the ROI

        Args:
            event (pyqtgraph.graphicsItems.ROI.ROI)
        """
        logger.info('')
        pos = event.pos()
        size = event.size()

        left, top, right, bottom = None, None, None, None
        handles = event.getSceneHandlePositions()
        for handle in handles:
            if handle[0] is not None:
                imagePos = self.myImageItem.mapFromScene(handle[1])
                x = imagePos.x()
                y = imagePos.y()
                # units are in image pixels !!!
                if handle[0] == 'topleft':
                    left = x
                    bottom = y
                elif handle[0] == 'bottomright':
                    right = x
                    top = y
        #
        left = int(left)
        top = int(top)
        right = int(right)
        bottom = int(bottom)

        if left<0:
            left = 0

        print(f'  left:{left} top:{top} right:{right} bottom:{bottom}')

        #  cludge
        if bottom > top:
            logger.warning(f'fixing bad top/bottom')
            tmp = top
            top = bottom
            bottom = tmp

        theRect = [left, top, right, bottom]

        self._updateRoiMinMax(theRect)

        # TODO: detection widget needs a slot to (i) analyze and then replot
        #self.ba._updateTifRoi(theRect)
        #self._replot(startSec=None, stopSec=None, userUpdate=True)
        #self.signalDetect.emit(self.ba)  # underlying _abf has new rect
        self.ba._updateTifRoi(theRect)
        self.signalKymographRoiChanged.emit(theRect)  # underlying _abf has new rect

    def slot_switchFile(self, ba=None):
        if ba is not None and ba.isKymograph():
            self.ba = ba
            #self._updateRoiMinMax(theRect)
            self._replot()

    def hoverEvent(self, event):
        if event.isExit():
            return

        xPos = event.pos().x()
        yPos = event.pos().y()

        xPos = int(xPos)
        yPos = int(yPos)

        myTif = self.ba.tifData
        intensity = myTif[yPos, xPos]  # flipped

        #logger.info(f'x:{xPos} y:{yPos} intensity:{intensity}')

        self.tifCursorLabel.setText(f'Cursor:{intensity}')
        self.tifCursorLabel.update()

if __name__ == '__main__':
    path = '/media/cudmore/data/rabbit-ca-transient/jan-12-2022/Control/220110n_0003.tif.frames/220110n_0003.tif'
    ba = sanpy.bAnalysis(path)
    print(ba)

    app = QtWidgets.QApplication(sys.argv)

    kw = kymWidget(ba)
    kw.show()

    sys.exit(app.exec_())
