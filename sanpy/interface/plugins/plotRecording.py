from functools import partial

import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui

import matplotlib.pyplot as plt

import sanpy
from sanpy import bAnalysis
from sanpy.interface.plugins import sanpyPlugin
from sanpy.interface.plugins import (
    ResponseType,
)  # to toggle response to set sweeps, etc

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

# taken from
# https://www.pythonguis.com/widgets/qcolorbutton-a-color-selector-tool-for-pyqt/
class ColorButton(QtWidgets.QPushButton):
    '''
    Custom Qt Widget to show a chosen color.

    Left-clicking the button shows the color-chooser, while
    right-clicking resets the color to None (no-color).
    '''

    colorChanged = QtCore.pyqtSignal(object)

    def __init__(self, *args, color=None, **kwargs):
        super(ColorButton, self).__init__(*args, **kwargs)

        self._color = None
        self._default = color
        self.pressed.connect(self.onColorPicker)

        # Set the initial/default state.
        self.setColor(self._default)

    def setColor(self, color):
        if color != self._color:
            self._color = color
            # logger.info(f'emit color: {color}')
            self.colorChanged.emit(color)

        if self._color:
            self.setStyleSheet("background-color: %s;" % self._color)
        else:
            self.setStyleSheet("")

    def color(self):
        return self._color

    def onColorPicker(self):
        '''
        Show color-picker dialog to select color.

        Qt will use the native dialog by default.

        '''
        dlg = QtWidgets.QColorDialog(self)
        if self._color:
            dlg.setCurrentColor(QtGui.QColor(self._color))

        if dlg.exec_():
            self.setColor(dlg.currentColor().name())

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.RightButton:
            self.setColor(self._default)

        return super(ColorButton, self).mousePressEvent(e)

# TODO: switch this to a dict with keys of 'humanName'
def getPlotOptionsDict():
     theRet = {
           "Threshold (mV)": {
                # "humanName": "Threshold (mV)",
                "x": "thresholdSec",
                "y": "thresholdVal",
                "convertx_tosec": False,  # some stats are in points, we need to convert to seconds
                "color": "red",
                "styleColor": "color: red",
                "symbol": ".",
                "showLines": '.',  # . will not show lines, - will
                "markerSize": 4,
                "plotOn": "vm",  # which plot to overlay (vm, dvdt)
                "plotIsOn": True,
            },

           "AP Peak (mV)":
            {
                # "humanName": "AP Peak (mV)",
                "x": "peakSec",
                "y": "peakVal",
                "convertx_tosec": False,
                "color": "blue",
                "styleColor": "color: green",
                "symbol": "o",
                "showLines": '.',  # . will not show lines, - will
                "markerSize": 4,
                "plotOn": "vm",
                "plotIsOn": True,
            },

           "Fast AHP (mV)":
            {
                # "humanName": "Fast AHP (mV)",
                "x": "fastAhpSec",
                "y": "fastAhpValue",
                "convertx_tosec": False,
                "color": "cyan",
                "styleColor": "color: yellow",
                "symbol": "o",
                "showLines": '.',  # . will not show lines, - will
                "markerSize": 4,
                "plotOn": "vm",
                "plotIsOn": False,
            },

           "Half-Widths":
            {
                # "humanName": "Half-Widths",
                "x": None,
                "y": None,
                "convertx_tosec": True,
                "color": "yellow",
                "styleColor": "color: yellow",
                "symbol": None,
                "showLines": '-',  # . will not show lines, - will
                "markerSize": 4,
                "plotOn": "vm",
                "plotIsOn": False,
            },
           "EDD Rate":
            {
                # "humanName": "EDD Rate",
                "x": None,
                "y": None,
                "convertx_tosec": False,
                "color": "magenta",
                "styleColor": "color: megenta",
                "symbol": None,
                "showLines": '-',  # . will not show lines, - will
                "markerSize": 4,
                "plotOn": "vm",
                "plotIsOn": False,
            },
            # "Epoch Lines":
            # {
            #     "humanName": "Epoch Lines",
            #     "x": None,
            #     "y": None,
            #     "convertx_tosec": True,
            #     "color": "y",
            #     "styleColor": "color: gray",
            #     "symbol": "o",
            #     "plotOn": "vm",
            #     "plotIsOn": True,
            # },
     }
     return theRet

class plotRecording(sanpyPlugin):
    """Example of matplotlib plugin.
    """

    myHumanName = "Plot Recording"

    def __init__(self, **kwargs):
        super(plotRecording, self).__init__(**kwargs)

        # this is a very simple plugin, do not respond to changes in interface
        # switchFile = self.responseTypes.switchFile
        # self.toggleResponseOptions(switchFile, newValue=False)

        # analysisChange = self.responseTypes.analysisChange
        # self.toggleResponseOptions(analysisChange, newValue=False)

        # selectSpike = self.responseTypes.selectSpike
        # self.toggleResponseOptions(selectSpike, newValue=False)

        # we are plotting all sweeps and all axis, turn these off
        self.toggleResponseOptions(ResponseType.setSweep, False)  # we plot all sweeps
        self.toggleResponseOptions(ResponseType.setAxis, False)

        setAxis = self.responseTypes.setAxis
        self.toggleResponseOptions(setAxis, newValue=False)

        self._plotOptionsDict = getPlotOptionsDict()
        # a list of dict telling us how to plot each item (like threshold, peak etc)

        self.rawLine = None
        self.rawLineWidth = 0.5
        # raw data
        
        self._plotList = {}

        # a list of self.axs.plot that we actually plot using _plotDictList

        self.xOffset = 0.01
        self.yOffset = 50

        self._buildGui()
        self.replot(firstPlot=True)

    def toggleOffsetSpinBox(self, visible : bool):
        self.xOffsetSpinBox.setVisible(visible)
        self.yOffsetSpinBox.setVisible(visible)

    def _buildControlLayout(self):
        _vLayoutControls = QtWidgets.QVBoxLayout()
        _vLayoutControls.setAlignment(QtCore.Qt.AlignTop)

        # raw line width
        _hLayoutRawLineWidth = QtWidgets.QHBoxLayout()
        _hLayoutRawLineWidth.setAlignment(QtCore.Qt.AlignLeft)
        aLabel = QtWidgets.QLabel('Raw Line Width')
        _hLayoutRawLineWidth.addWidget(aLabel)
        rawLineWidthSpinBox = QtWidgets.QDoubleSpinBox()
        rawLineWidthSpinBox.setValue(self.rawLineWidth)
        rawLineWidthSpinBox.valueChanged.connect(self._on_raw_line_width)
        _hLayoutRawLineWidth.addWidget(rawLineWidthSpinBox)

        _vLayoutControls.addLayout(_hLayoutRawLineWidth)

        # x/y offset per sweep
        _hLayoutOffset = QtWidgets.QHBoxLayout()
        _hLayoutOffset.setAlignment(QtCore.Qt.AlignLeft)
        aLabel = QtWidgets.QLabel('Sweep Offsets (x/y)')
        _hLayoutOffset.addWidget(aLabel)
        # x offset
        self.xOffsetSpinBox = QtWidgets.QDoubleSpinBox()
        self.xOffsetSpinBox.setValue(self.xOffset)
        self.xOffsetSpinBox.valueChanged.connect(partial(self._on_offset_spinbox, 'xOffset'))
        _hLayoutOffset.addWidget(self.xOffsetSpinBox)
        # y offset
        self.yOffsetSpinBox = QtWidgets.QDoubleSpinBox()
        self.yOffsetSpinBox.setValue(self.yOffset)
        self.yOffsetSpinBox.valueChanged.connect(partial(self._on_offset_spinbox, 'yOffset'))
        _hLayoutOffset.addWidget(self.yOffsetSpinBox)

        _vLayoutControls.addLayout(_hLayoutOffset)

        for humanName, optionsDict in self._plotOptionsDict.items():
            _rowHLayout = QtWidgets.QHBoxLayout()
            _rowHLayout.setAlignment(QtCore.Qt.AlignLeft)

            # humanName = statDict['humanName']
            color = optionsDict['color']
            markersize = optionsDict['markerSize']
            showLines = optionsDict['showLines']
            plotIsOn = optionsDict['plotIsOn']

            aCheckbox = QtWidgets.QCheckBox(humanName)
            aCheckbox.setChecked(plotIsOn)
            aCheckbox.stateChanged.connect(partial(self._on_check_click, aCheckbox, humanName))
            _rowHLayout.addWidget(aCheckbox)

            # color button
            aColorButton = ColorButton()
            aColorButton.setColor(color)
            # aColorButton.resize(100, 100)
            aColorButton.setFixedSize(QtCore.QSize(20, 20))
            aColorButton.colorChanged.connect(partial(self._on_color_click, humanName))
            _rowHLayout.addWidget(aColorButton)

            # marker size, if showLines is '-' then we are not showing markers
            if showLines == '.':
                aSpinBox = QtWidgets.QSpinBox()
                aSpinBox.setValue(markersize)
                aSpinBox.valueChanged.connect(partial(self._on_size_spinbox, humanName))
                _rowHLayout.addWidget(aSpinBox)

            _vLayoutControls.addLayout(_rowHLayout)

        
        resetZoom = QtWidgets.QPushButton('Reset Zoom')
        resetZoom.clicked.connect(self.setFullZoom)
        _vLayoutControls.addWidget(resetZoom)
        
        return _vLayoutControls
    
    def _on_raw_line_width(self, value : float):
        self.rawLineWidth = value
        self.replot()
        
    def _on_offset_spinbox(self, xyName : str, value : float):
        # logger.info(f'{xyName} {value}')
        if xyName == 'xOffset':
            self.xOffset = value
        elif xyName == 'yOffset':
            self.yOffset = value
        
        self.replot()

    def _on_check_click(self, checkbox, humanName : str):
        isChecked = checkbox.isChecked()
        # logger.info(f'{humanName} {isChecked}')
        self._plotOptionsDict[humanName]['plotIsOn'] = isChecked

        self.replot()

    def _on_color_click(self, humanName, color : str):
        # logger.info(f'{humanName} {color}')
        self._plotOptionsDict[humanName]['color'] = color

        self.replot()

    def _on_size_spinbox(self, humanName, markerSize):
        # logger.info(f'{humanName} {markerSize}')
        self._plotOptionsDict[humanName]['markerSize'] = markerSize

        self.replot()

    def _buildGui(self):
        # if self.ba is None:
        #     return
        
        _vlayout = self.getVBoxLayout()
        
        # hold controls and plot
        _hLayout = QtWidgets.QHBoxLayout()
        _vlayout.addLayout(_hLayout)

        # controls
        _vLayoutControls = self._buildControlLayout()
        _hLayout.addLayout(_vLayoutControls)

        # plot
        _vLayoutPlot = QtWidgets.QVBoxLayout()
        static_canvas, mplToolbar = self.mplWindow2(addToLayout=False)  # assigns (self.fig, self.axs)
        _vLayoutPlot.addWidget(static_canvas)
        _vLayoutPlot.addWidget(mplToolbar)
        _hLayout.addLayout(_vLayoutPlot)

    def replot(self, firstPlot=False):
        """bAnalysis has been updated, replot"""
        logger.info(f"{self.ba}")

        if self.ba is None:
            return

        self.toggleOffsetSpinBox(self.ba.fileLoader.numSweeps > 1)

        xCurrentOffset = 0
        yCurrentOffset = 0

        # currentSweep = self.ba.fileLoader.currentSweep
        #numSweeps = self.ba.fileLoader.numSweeps
        sweepNumber = self.sweepNumber  # can be 'All'
        logger.info(f'sweepNumber:{sweepNumber}')
        if sweepNumber == 'All':
            theseSweeps = list(range(self.ba.fileLoader.numSweeps))
        else:
            theseSweeps = [sweepNumber]
        numSweeps = len(theseSweeps)

        if not firstPlot:
            _xLimOrig = self.axs.get_xlim()
            # logger.info(f'_xLimOrig: {_xLimOrig}')
            _yLimOrig = self.axs.get_ylim()
            # logger.info(f'_yLimOrig: {_yLimOrig}')

        self.fig.clear(True)
        self.axs = self.fig.add_subplot(1, 1, 1)

        self.rawLine = [None] * numSweeps

        _penColor = self.getPenColor()

        # each plot has to have a [] for sweeps
        for humanName in self._plotOptionsDict.keys():
            self._plotList[humanName] = [None] * numSweeps

        for plotIdx, sweepIdx in enumerate(theseSweeps):
            self.ba.fileLoader.setSweep(sweepIdx)

            sweepX = self.getSweep("x")
            sweepY = self.getSweep("y")

            self.sweepX = sweepX
            self.sweepY = sweepY

            (self.rawLine[plotIdx],) = self.axs.plot(
                sweepX + xCurrentOffset,
                sweepY + yCurrentOffset,
                "-",
                color=_penColor,
                linewidth=self.rawLineWidth,
            )

            self.axs.spines['right'].set_visible(False)
            self.axs.spines['top'].set_visible(False)

            for humanName, onePlotDict in self._plotOptionsDict.items():
                xStat = onePlotDict['x']
                yStat = onePlotDict['y']
                
                # humanName = onePlotDict['humanName']
                color = onePlotDict['color']
                symbol = onePlotDict['symbol']
                markerSize = onePlotDict['markerSize']
                showLines = onePlotDict['showLines']
                plotIsOn = onePlotDict['plotIsOn']
                if not plotIsOn:
                    continue

                if humanName == 'Half-Widths':
                    spikeDictionaries = self.ba.getSpikeDictionaries(
                        sweepNumber=sweepIdx
                    )
                
                    xValue, yValue = sanpy.analysisUtil.getHalfWidthLines(
                        sweepX, sweepY, spikeDictionaries)
                
                elif humanName == 'EDD Rate':
                    xValue, yValue = sanpy.analysisUtil.getEddLines(self.ba)
                
                elif xStat is None:
                    continue

                else:
                    xValue = self.ba.getStat(xStat, sweepNumber=sweepIdx)
                    yValue = self.ba.getStat(yStat, sweepNumber=sweepIdx)

                xValue = [x + xCurrentOffset for x in xValue]
                yValue = [y + yCurrentOffset for y in yValue]

                self._plotList[humanName][plotIdx] = self.axs.plot(
                    xValue, yValue,
                    showLines,  # '-' to show, '.' to not
                    color=color,
                    marker=symbol,
                    markersize=markerSize,
                )

            # thresholdSec = self.ba.getStat("thresholdSec", sweepNumber=sweepIdx)
            # thresholdSec = [x + xCurrentOffset for x in thresholdSec]
            # thresholdVal = self.ba.getStat("thresholdVal", sweepNumber=sweepIdx)
            # thresholdVal = [x + yCurrentOffset for x in thresholdVal]
            # markersize = 4
            # self.thresholdLine[sweepIdx] = self.axs.plot(
            #     thresholdSec, thresholdVal, "r.", markersize=markersize
            # )

            """
            if thresholdSec is None or thresholdVal is None:
                self.thresholdLine[sweepIdx].set_data([], [])
            else:
                self.thresholdLine[sweepIdx] = self.axs.plot(thresholdSec, thresholdSec, 'o')
            """

            """
            xHW, yHW = self.getHalfWidths()
            self.lineHW, = self.axs.plot(xHW, yHW, '-')
            """

            xCurrentOffset += self.xOffset
            yCurrentOffset += self.yOffset

        self.axs.relim()
        self.axs.autoscale_view(True, True, True)

        if not firstPlot:
            self.axs.set_xlim(_xLimOrig)
            self.axs.set_ylim(_yLimOrig)

        # self.ba.fileLoader.setSweep(currentSweep)
        self.static_canvas.draw_idle()
        plt.draw()

    def setFullZoom(self):
        xMin = 0
        xMax = self.ba.fileLoader.sweepX[-1]
        yMin = np.min(self.ba.fileLoader.sweepY)
        yMax = np.max(self.ba.fileLoader.sweepY)

        self.axs.set_xlim([xMin, xMax])
        self.axs.set_ylim([yMin, yMax])

        self.static_canvas.draw_idle()
        plt.draw()

    def selectSpikeList(self):
        """Only respond to single spike selection."""
        logger.info("")
        spikeList = self.getSelectedSpikes()

        if spikeList == [] or len(spikeList) > 1:
            return

        if self.ba is None:
            return

        spikeNumber = spikeList[0]

        thresholdSec = self.ba.getStat("thresholdSec")
        spikeTime = thresholdSec[spikeNumber]
        xMin = spikeTime - 0.5
        xMax = spikeTime + 0.5

        self.axs.set_xlim(xMin, xMax)

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

def testPlot():
    import os

    file_path = os.path.realpath(__file__)  # full path to this file
    file_path = os.path.split(file_path)[0]  # folder for this file
    path = os.path.join(file_path, "../../../data/19114001.abf")

    ba = bAnalysis(path)
    if ba.loadError:
        print("error loading file")
        return
    ba.spikeDetect()

    # create plugin
    ap = plotRecording(ba=ba)

    # ap.plot()

    # ap.slotUpdateAnalysis()


def main():
    path = "/Users/cudmore/Sites/SanPy/data/2021_07_20_0010.abf"
    ba = sanpy.bAnalysis(path)
    ba.spikeDetect()
    print(ba.numSpikes)

    import sys

    app = QtWidgets.QApplication([])
    pr = plotRecording(ba=ba)
    pr.show()
    sys.exit(app.exec_())


def testLoad():
    import os, glob

    pluginFolder = "/Users/cudmore/sanpy_plugins"
    files = glob.glob(os.path.join(pluginFolder, "*.py"))
    for file in files:
        # if file.startswith('.'):
        #    continue
        if file.endswith("__init__.py"):
            continue
        print(file)

def debugManuscript():
    """Open folder, select a file, run Plot Recording plugin.
    """
    import sys
    import sanpy.interface
    app = sanpy.interface.SanPyApp([])
    
    path = '/Users/cudmore/Sites/SanPy/data'
    w = app.openSanPyWindow(path)

    # select first file
    # todo: add sanpy window selectFileRow(), only if showing a folder path
    rowIdx = 0
    # w._fileListWidget.getTableView()._onLeftClick(rowIdx)
    w.selectFileListRow(rowIdx)

    # w.selectSpikeList([10000])

    w.sanpyPlugin_action('Plot Recording')

    sys.exit(app.exec_())

if __name__ == "__main__":
    # testPlot()
    # testLoad()
    #main()
    debugManuscript()