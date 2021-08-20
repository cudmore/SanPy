"""
Plugin to create and save Axon ATF files
"""

import os, sys
from functools import partial

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtWidgets, QtGui

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends import backend_qt5agg

import qdarkstyle

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class stimGen(sanpyPlugin):
	myHumanName = 'Stim Gen'

	def __init__(self, myAnalysisDir=None, **kwargs):
		"""
		Args:
			ba (bAnalysis): Not required
		"""
		super(stimGen, self).__init__(**kwargs)

		self.numSweeps = 5

		self._fs = 10000
		self._data = [None] * self.numSweeps  # list of sweeps
		self._t = []

		self.stimTypes = [
						'Sin',
						'Chirp',
						'Noise',
						'Epsp train',
						#'Stochastic HH',
						'Integrate and Fire'
						]
		self.stimType = 'Sin'
		self.durSeconds = 5
		self.amplitude = 3
		self.frequency = 2
		self.noiseAmplitude = 0  # sqrt() of this is STD of Gaussian noise

		# step for multiple sweeps
		self.amplitudeStep = 0
		self.frequencyStep = 0
		self.noiseStep = 0

		self.doRectify = False

		self.savePath = ''  # remember last save folder

		self.buildUI()

		self.updateStim()

	def getAtfHeader(self, numChannels=1):
		"""
		See: https://github.com/christianrickert/Axon-Text-File/blob/master/data.atf
		"""
		numDataColumns = numChannels + 1  # time + number of channels
		eol = '\n'
		tab = '\t'
		ATF_HEADER = "ATF	1.0" + eol
		ATF_HEADER += f'8\t{numDataColumns}' + eol
		ATF_HEADER += """
		"AcquisitionMode=Episodic Stimulation"
		"Comment="
		"YTop=2000"
		"YBottom=-2000"
		"SyncTimeUnits=20"
		"SweepStartTimesMS=0.000"
		"SignalsExported=IN 0"
		"Signals="	"IN 0"
		""".strip()
		ATF_HEADER += eol
		ATF_HEADER += f'"Time (s)"' + tab
		for channel in range(numChannels):
			traceStr = f'"Trace #{channel+1}"' + tab  # not sure if trailing tab is ok???
			ATF_HEADER += traceStr
		ATF_HEADER += eol

		print('ATF_HEADER:')
		print(ATF_HEADER)

		'''
		ATF_HEADER = """
		ATF	1.0
		8	3
		"AcquisitionMode=Episodic Stimulation"
		"Comment="
		"YTop=2000"
		"YBottom=-2000"
		"SyncTimeUnits=20"
		"SweepStartTimesMS=0.000"
		"SignalsExported=IN 0"
		"Signals="	"IN 0"
		"Time (s)"	"Trace #1"	"Trace #2"
		""".strip()
		'''

		return ATF_HEADER

	'''
	@property
	def data(self):
		return self._data
	'''

	@property
	def t(self):
		return self._t

	@property
	def fs(self):
		return self._fs

	def makeStim(self):
		type = self.stimType
		fs = self.fs
		durSec = self.durSeconds
		amp = self.amplitude
		freq = self.frequency
		noiseAmp = self.noiseAmplitude
		doRectify = self.doRectify

		amplitudeStep = self.amplitudeStep
		frequencyStep = self.frequencyStep
		noiseStep = self.noiseStep

		self._data = [None] * self.numSweeps
		for sweepNum in range(self.numSweeps):
			currAmp = amp + (sweepNum * amplitudeStep)
			currFreq = freq + (sweepNum * frequencyStep)
			currNoiseAmp = noiseAmp + (sweepNum * noiseStep)
			print(f'  makeStim() {type} sweep:{sweepNum} durSec:{durSec} amp:{currAmp} freq:{currFreq} noiseAmp:{currNoiseAmp}')
			self._data[sweepNum] = sanpy.atfStim.makeStim(type, amp=currAmp, durSec=durSec,
							freq=currFreq, fs=fs, noiseAmp=currNoiseAmp, rectify=doRectify,
							autoPad=True, autoSave=False)
			if self._data[sweepNum] is None:
				print(f'makeStim() error making {type} at sweep number {sweepNum}')

		self._t = np.arange(len(self._data[0])) / fs  # just using first sweep

	'''
	def plotStim(self):
		logger.info(f'_t:{self._t.shape}')
		logger.info(f'_data:{self._data.shape}')
		plt.plot(self._t, self._data)
	'''

	'''
	def saveStim(Self):
		sanpy.atfStim.saveAtf(self.data, fileName="output.atf", fs=10000)
	'''

	def _grabParams(self):
		self.numSweeps = self.numSweepsSpinBox.value()

		self.durSeconds = self.durationSpinBox.value()
		self.amplitude = self.amplitudeSpinBox.value()
		self.frequency = self.frequencySpinBox.value()
		self.noiseAmplitude = self.noiseAmpSpinBox.value()

		self.amplitudeStep = self.amplitudeStepSpinBox.value()
		self.frequencyStep = self.frequencyStepSpinBox.value()
		self.noiseStep = self.noiseStepSpinBox.value()

		self.doRectify = self.rectifyCheckBox.isChecked()
		self._fs = self.fsSpinBox.value()

		rmsMult = 1/np.sqrt(2)
		sinRms = self.amplitude * rmsMult
		sinRms = round(sinRms,2)
		aName = f'RMS:{sinRms}'
		self.sinRms.setText(aName)

	def updateStim(self):
		self._grabParams()
		self.makeStim()
		self.replot()

	def on_spin_box(self, name):
		logger.info(name)
		if name == 'Number Of Sweeps':
			numSweeps = self.numSweepsSpinBox.value()
			self._updateNumSweeps(numSweeps)
		#
		self.updateStim()

	def on_stim_type(self, type):
		logger.info(type)
		self.stimType = type
		self.updateStim()

	def on_button_click(self, name):
		logger.info(name)
		if name == 'Make Stimulus':
			self.makeStim()
		elif name == 'Save As...':
			self.saveAs()
		else:
			logger.info(f'name "{name}" not understood.')

	def on_checkbox_clicked(self, name):
		self.updateStim()

	def buildUI(self):
		# main layout
		vLayout = QtWidgets.QVBoxLayout()
		controlLayout = QtWidgets.QHBoxLayout()

		'''
		aName = 'Make Stimulus'
		aButton = QtWidgets.QPushButton(aName)
		aButton.clicked.connect(partial(self.on_button_click,aName))
		controlLayout.addWidget(aButton)
		'''

		aName = 'Save As...'
		aButton = QtWidgets.QPushButton(aName)
		aButton.clicked.connect(partial(self.on_button_click,aName))
		controlLayout.addWidget(aButton)

		aName = 'Stim Type'
		aLabel = QtWidgets.QLabel(aName)
		controlLayout.addWidget(aLabel)
		self.stimTypeDropdown = QtWidgets.QComboBox()
		for type in self.stimTypes:
			self.stimTypeDropdown.addItem(type)
		self.stimTypeDropdown.currentTextChanged.connect(self.on_stim_type)
		controlLayout.addWidget(self.stimTypeDropdown)

		aName = 'Duration(s)'
		aLabel = QtWidgets.QLabel(aName)
		controlLayout.addWidget(aLabel)
		self.durationSpinBox = QtWidgets.QDoubleSpinBox()
		self.durationSpinBox.setKeyboardTracking(False)
		self.durationSpinBox.setRange(0, 1e9)
		self.durationSpinBox.setValue(self.durSeconds)
		self.durationSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
		controlLayout.addWidget(self.durationSpinBox)

		aName = 'Number Of Sweeps'
		aLabel = QtWidgets.QLabel(aName)
		controlLayout.addWidget(aLabel)
		self.numSweepsSpinBox = QtWidgets.QSpinBox()
		self.numSweepsSpinBox.setKeyboardTracking(False)
		self.numSweepsSpinBox.setRange(1, 1e9)
		self.numSweepsSpinBox.setValue(self.numSweeps)
		self.numSweepsSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
		controlLayout.addWidget(self.numSweepsSpinBox)

		vLayout.addLayout(controlLayout) # add mpl canvas

		# 2nd row
		controlLayout_row2 = QtWidgets.QGridLayout()
		rowSpan = 1
		colSpan = 1
		row = 0
		col = 0

		aName = 'Amplitude'
		aLabel = QtWidgets.QLabel(aName)
		controlLayout_row2.addWidget(aLabel, row, col, rowSpan, colSpan)
		self.amplitudeSpinBox = QtWidgets.QDoubleSpinBox()
		self.amplitudeSpinBox.setKeyboardTracking(False)
		self.amplitudeSpinBox.setRange(0, 1e9)
		self.amplitudeSpinBox.setValue(self.amplitude)
		self.amplitudeSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
		controlLayout_row2.addWidget(self.amplitudeSpinBox, 0, 1, rowSpan, colSpan)

		aName = 'Frequency (Hz)'
		aLabel = QtWidgets.QLabel(aName)
		controlLayout_row2.addWidget(aLabel, 0, 2, rowSpan, colSpan)
		self.frequencySpinBox = QtWidgets.QDoubleSpinBox()
		self.frequencySpinBox.setKeyboardTracking(False)
		self.frequencySpinBox.setRange(0, 1e9)
		self.frequencySpinBox.setValue(self.frequency)
		self.frequencySpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
		controlLayout_row2.addWidget(self.frequencySpinBox, 0, 3, rowSpan, colSpan)

		# rms of sin (amp and freq)
		rmsMult = 1/np.sqrt(2)
		sinRms = self.amplitude * rmsMult
		sinRms = round(sinRms,2)
		aName = f'RMS:{sinRms}'
		self.sinRms = QtWidgets.QLabel(aName)
		controlLayout_row2.addWidget(self.sinRms, 0, 4, rowSpan, colSpan)

		aName = 'Noise Amplitude'
		aLabel = QtWidgets.QLabel(aName)
		controlLayout_row2.addWidget(aLabel, 0, 5, rowSpan, colSpan)
		self.noiseAmpSpinBox = QtWidgets.QDoubleSpinBox()
		self.noiseAmpSpinBox.setKeyboardTracking(False)
		self.noiseAmpSpinBox.setSingleStep(0.1)
		self.noiseAmpSpinBox.setRange(0, 1e9)
		self.noiseAmpSpinBox.setValue(self.noiseAmplitude)
		self.noiseAmpSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
		controlLayout_row2.addWidget(self.noiseAmpSpinBox, 0, 6, rowSpan, colSpan)

		#
		# row 2
		#controlLayout_row2 = QtWidgets.QHBoxLayout()

		aName = 'Amplitude Step'
		aLabel = QtWidgets.QLabel(aName)
		controlLayout_row2.addWidget(aLabel, 1, 0, rowSpan, colSpan)
		self.amplitudeStepSpinBox = QtWidgets.QDoubleSpinBox()
		self.amplitudeStepSpinBox.setKeyboardTracking(False)
		self.amplitudeStepSpinBox.setSingleStep(0.1)
		self.amplitudeStepSpinBox.setRange(0, 1e9)
		self.amplitudeStepSpinBox.setValue(self.amplitudeStep)
		self.amplitudeStepSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
		controlLayout_row2.addWidget(self.amplitudeStepSpinBox, 1, 1, rowSpan, colSpan)

		aName = 'Frequency Step'
		aLabel = QtWidgets.QLabel(aName)
		controlLayout_row2.addWidget(aLabel, 1, 2, rowSpan, colSpan)
		self.frequencyStepSpinBox = QtWidgets.QDoubleSpinBox()
		self.frequencyStepSpinBox.setKeyboardTracking(False)
		self.frequencyStepSpinBox.setSingleStep(0.1)
		self.frequencyStepSpinBox.setRange(0, 1e9)
		self.frequencyStepSpinBox.setValue(self.frequencyStep)
		self.frequencyStepSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
		controlLayout_row2.addWidget(self.frequencyStepSpinBox, 1, 3, rowSpan, colSpan)

		# first row in grid has freq rms

		aName = 'Noise Step'
		aLabel = QtWidgets.QLabel(aName)
		controlLayout_row2.addWidget(aLabel, 1, 5, rowSpan, colSpan)
		self.noiseStepSpinBox = QtWidgets.QDoubleSpinBox()
		self.noiseStepSpinBox.setKeyboardTracking(False)
		self.noiseStepSpinBox.setSingleStep(0.1)
		self.noiseStepSpinBox.setRange(0, 1e9)
		self.noiseStepSpinBox.setValue(self.frequencyStep)
		self.noiseStepSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
		controlLayout_row2.addWidget(self.noiseStepSpinBox, 1, 6, rowSpan, colSpan)

		#
		vLayout.addLayout(controlLayout_row2) # add mpl canvas

		controlLayout_row3 = QtWidgets.QHBoxLayout()

		checkboxName = 'Rectify'
		self.rectifyCheckBox = QtWidgets.QCheckBox(checkboxName)
		self.rectifyCheckBox.setChecked(self.doRectify)
		self.rectifyCheckBox.stateChanged.connect(partial(self.on_checkbox_clicked, checkboxName))
		controlLayout_row3.addWidget(self.rectifyCheckBox)

		aName = 'Samples Per Second'
		aLabel = QtWidgets.QLabel(aName)
		controlLayout_row3.addWidget(aLabel)
		self.fsSpinBox = QtWidgets.QSpinBox()
		self.fsSpinBox.setKeyboardTracking(False)
		self.fsSpinBox.setRange(1, 1e9)
		self.fsSpinBox.setValue(self._fs)
		self.fsSpinBox.valueChanged.connect(partial(self.on_spin_box, aName))
		controlLayout_row3.addWidget(self.fsSpinBox)

		#
		vLayout.addLayout(controlLayout_row3) # add mpl canvas

		vSplitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
		vLayout.addWidget(vSplitter)

		plt.style.use('dark_background')

		self.fig = mpl.figure.Figure(constrained_layout=True)
		self.static_canvas = backend_qt5agg.FigureCanvas(self.fig)
		self.static_canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
		self.static_canvas.setFocus()

		#can do self.mplToolbar.hide()
		self.mplToolbar = mpl.backends.backend_qt5agg.NavigationToolbar2QT(self.static_canvas, self.static_canvas)

		self._updateNumSweeps(self.numSweeps)
		#self.rawAxes = self.static_canvas.figure.add_subplot(self.numSweeps,1,1)
		#self.plotLine, = self.rawAxes[0].plot([], [], '-w', linewidth=1)

		vSplitter.addWidget(self.static_canvas) # add mpl canvas
		vSplitter.addWidget(self.mplToolbar) # add mpl canvas

		#
		# finalize
		self.mainWidget = QtWidgets.QWidget()
		if qdarkstyle is not None:
			self.mainWidget.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
		else:
			self.mainWidget.setStyleSheet("")

		# set the layout of the main window
		self.mainWidget.setLayout(vLayout)
		self.mainWidget.show()


	def _updateNumSweeps(self, numSweeps):
		"""
		Remove and add all Figure axes
		"""
		self.numSweeps = numSweeps

		self.static_canvas.figure.clear()

		self.plotLine = [None] * numSweeps
		self.rawAxes = [None] * numSweeps

		for i in range(numSweeps):
			if i == 0:
				self.rawAxes[i] = self.static_canvas.figure.add_subplot(numSweeps,1, i+1)  # +1 because subplot index is 1 based
			else:
				self.rawAxes[i] = self.static_canvas.figure.add_subplot(numSweeps,1, i+1, sharex=self.rawAxes[0])  # +1 because subplot index is 1 based
			self.plotLine[i], = self.rawAxes[i].plot([], [], '-w', linewidth=0.5)

			self.rawAxes[i].spines['right'].set_visible(False)
			self.rawAxes[i].spines['top'].set_visible(False)

			lastSweep = i == (numSweeps - 1)
			if not lastSweep:
				self.rawAxes[i].spines['bottom'].set_visible(False)
				self.rawAxes[i].tick_params(axis="x", labelbottom=False) # no labels

	def replot(self):
		logger.info(f't:{len(self._t)}, data:{len(self._data)}')

		yMin = 1e9
		yMax = -1e9

		for i in range(self.numSweeps):
			self.plotLine[i].set_xdata(self._t)
			self.plotLine[i].set_ydata(self._data[i])
			#
			self.rawAxes[i].relim()
			self.rawAxes[i].autoscale_view(True,True,True)

			thisMin = np.nanmin(self._data[i])
			thisMax = np.nanmax(self._data[i])
			if thisMin < yMin:
				yMin = thisMin
			if thisMax > yMax:
				yMax = thisMax

		for i in range(self.numSweeps):
			self.rawAxes[i].set_ylim([yMin, yMax])

		#
		self.static_canvas.draw()

	'''
	def _getTime(self):
		"""Get time in seconds."""
		n = int(durSec * fs) # total number of samples
		t = np.linspace(0, self.durSeconds, n, endpoint=True)
		return t
	'''

	def saveAs(self):
		"""Save a stimulus waveform array as an ATF 1.0 file.

		If use specifies .atf then save as .atf
		If user specifies .csv then save as .csv
		"""
		fileName = self.getFileName()
		options = QtWidgets.QFileDialog.Options()
		savePath = os.path.join(self.savePath, fileName)
		fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self.mainWidget,"Save .atf file",
							savePath,"Atf Files (*.atf);;CSV Files (*.csv)", options=options)
		if not fileName:
			return

		self.savePath = os.path.split(fileName)[0]

		if fileName.endswith('.atf'):
			numSweeps = self.numSweeps
			out = self.getAtfHeader(numChannels=numSweeps)
			data = self._data  # list of sweeps
			fs = self._fs

			#if numChannels == 2:
			#	myNoise = np.random.normal(scale=np.sqrt(5), size=data.shape)

			# TODO: getAtfHeader needs to append trailing eol
			# 		Then here we don't pre-pend with \n but append each line
			eol = '\n'
			pntsPerSweep = len(self._data[0])
			for i in range(pntsPerSweep):
				for sweepNumber in range(self.numSweeps):
					#sweepData = self._data[sweepNumber]
					val = self._data[sweepNumber][i]
					# TODO: Convert to f'' format
					if sweepNumber == 0:
						# time and sweep 0
						out += '%.05f\t%.05f'%(i/fs,val)
					else:
						# append value for next sweep
						out += '\t%.05f'%(val)
				#
				out += eol
			#
			with open(fileName,'w') as f:
				f.write(out)

		elif fileName.endswith('.csv'):
			df = pd.DataFrame(columns=['sec', 'pA'])
			df['sec'] = self._t
			df['pA'] = self._data
			df.to_csv(fileName, index=False)
		#
		logger.info(f'Saved: "{fileName}"')

	def getFileName(self):
		stimType = self.stimType
		numSweeps = self.numSweeps
		durSeconds = self.durSeconds  # sweep duration
		amplitude = self.amplitude
		frequency = self.frequency
		noiseAmplitude = self.noiseAmplitude
		noiseStep = self.noiseStep
		"""
		_s : number of sweeps
		_sd : sweep duration (seconds)
		_a : amplitude
		_f : frequency
		_g : start noise amplitude
		_ns : noise step
		"""
		filename = f'{stimType}_s{numSweeps}_sd{durSeconds}_a{amplitude}_f{frequency}_g{noiseAmplitude}'
		if numSweeps > 1:
			filename += f'_ns{noiseStep}'
		filename += '.atf'
		return filename

def run():
	app = QtWidgets.QApplication(sys.argv)

	msp = stimGen()

	sys.exit(app.exec_())

if __name__ == '__main__':
	run()
