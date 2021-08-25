import numbers
from functools import partial
import copy

from PyQt5 import QtCore, QtWidgets, QtGui

import sanpy
from sanpy.interface.plugins import sanpyPlugin

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class detectionParams(sanpyPlugin):
	"""
	Plugin to display overview of analysis.

	Uses:
		QTableView: sanpy.interface.bErrorTable.errorTableView()
		QAbstractTableModel: sanpy.interface.bFileTable.pandasModel
	"""
	myHumanName = 'Detection Parameters'

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		# fill this in
		#self.dDict = sanpy.bDetection.getDefaultDetection()
		if self.ba is not None:
			# make a copy and send it back on 'detect'
			detectionClass = copy.deepcopy(self.ba.detectionClass)
		else:
			detectionPreset = sanpy.bDetection.detectionPresets.default
			detectionClass = sanpy.bDetection(detectionPreset=detectionPreset)
		#
		self.detectionClass = detectionClass

		# put *this widget into a scroll area
		#self.myScrollArea = QtWidgets.QScrollArea()
		#self.myScrollArea.setWidget(self)

		self.vLayout = QtWidgets.QVBoxLayout()

		# top controls
		hControlLayout = QtWidgets.QHBoxLayout()

		fileName = 'None'
		if self.ba is not None:
			fileName = self.ba.getFileName()
		self.fileNameLabel = QtWidgets.QLabel(f'File: {fileName}')
		hControlLayout.addWidget(self.fileNameLabel)

		aName = 'Detect'
		aButton = QtWidgets.QPushButton(aName)
		aButton.clicked.connect(partial(self.on_button_click, aName))
		hControlLayout.addWidget(aButton)

		aName = 'Set Defaults'
		aButton = QtWidgets.QPushButton(aName)
		aButton.clicked.connect(partial(self.on_button_click, aName))
		hControlLayout.addWidget(aButton)

		aName = 'SA Node'
		aButton = QtWidgets.QPushButton(aName)
		aButton.clicked.connect(partial(self.on_button_click, aName))
		hControlLayout.addWidget(aButton)

		aName = 'Ventricular'
		aButton = QtWidgets.QPushButton(aName)
		aButton.clicked.connect(partial(self.on_button_click, aName))
		hControlLayout.addWidget(aButton)

		aName = 'Neuron'
		aButton = QtWidgets.QPushButton(aName)
		aButton.clicked.connect(partial(self.on_button_click, aName))
		hControlLayout.addWidget(aButton)

		aName = 'Subthreshold'
		aButton = QtWidgets.QPushButton(aName)
		aButton.clicked.connect(partial(self.on_button_click, aName))
		hControlLayout.addWidget(aButton)

		aName = 'Ca++ Spikes'
		aButton = QtWidgets.QPushButton(aName)
		aButton.clicked.connect(partial(self.on_button_click, aName))
		hControlLayout.addWidget(aButton)

		#
		self.vLayout.addLayout(hControlLayout)

		vLayoutParams = self.buildUI()
		self.vLayout.addLayout(vLayoutParams)

		# final widget
		'''
		finalLayout = QtWidgets.QVBoxLayout()
		scrollArea = QtWidgets.QScrollArea()
		scrollArea.setWidget(finalLayout)
		finalLayout.addWidget(scrollArea)
		'''

		#
		self.setLayout(self.vLayout)
		#self.setLayout(finalLayout)

	def insertIntoScrollArea(self):
		"""
		When inserting this widget into an interface, may want to wrap it in a ScrollArea

		This is used in main SanPy interface to insert this widget into a tab
		"""
		scrollArea = QtWidgets.QScrollArea()
		scrollArea.setWidget(self)
		return scrollArea

	def buildUI(self):

		# list of keys/columns in main analysis dir file list
		analysisDirDict = sanpy.analysisDir.sanpyColumns

		#dDict = self.dDict
		dDict = self.detectionClass

		vLayoutParams = QtWidgets.QGridLayout()

		self.widgetDict = {}

		row = 0
		col = 0
		rowSpan = 1
		colSpan = 1
		for k,v in dDict.items():
			col = 0

			# k is the name in spike dictionary
			paramName = k
			defaultValue = v['defaultValue']
			type = v['type']  # from ('int', 'float', 'boolean', 'string', detectionTypes_)
			units = v['units']
			humanName = v['humanName']
			description = v['description']
			allowNone = v['allowNone']  # set special value for spin box

			inAnalysisDir = paramName in analysisDirDict.keys()

			# add an '*' for params in main file table keys/columns
			aName = ' '
			if inAnalysisDir:
				aName = '*'
			aLabel = QtWidgets.QLabel(aName)
			vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
			col += 1

			# for debugging
			aLabel = QtWidgets.QLabel(paramName)
			vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
			col += 1

			aLabel = QtWidgets.QLabel(humanName)
			vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
			col += 1
			aLabel = QtWidgets.QLabel(type)
			vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
			col += 1
			aLabel = QtWidgets.QLabel(units)
			vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)
			col += 1

			aWidget = None
			if type == 'int':
				aWidget = QtWidgets.QSpinBox()
				aWidget.setRange(0, 2**16)  # minimum is used for setSpecialValueText()
				aWidget.setSpecialValueText("None")  # displayed when widget is set to minimum
				if defaultValue is None:
					aWidget.setValue(0)
				else:
					aWidget.setValue(defaultValue)
				aWidget.setKeyboardTracking(False) # don't trigger signal as user edits
				aWidget.valueChanged.connect(partial(self.on_spin_box, paramName))
			elif type == 'float':
				aWidget = QtWidgets.QDoubleSpinBox()
				aWidget.setRange(-1e9, +1e9)  # minimum is used for setSpecialValueText()
				aWidget.setSpecialValueText("None")  # displayed when widget is set to minimum
				if defaultValue is None:
					aWidget.setValue(-1e9)
				else:
					aWidget.setValue(defaultValue)
				aWidget.setKeyboardTracking(False) # don't trigger signal as user edits
				aWidget.valueChanged.connect(partial(self.on_spin_box, paramName))
			elif type == 'list':
				# text edit a list
				pass
			elif type == 'boolean':
				# popup of True/False
				aWidget = QtWidgets.QComboBox()
				aWidget.addItem('True')
				aWidget.addItem('False')
				aWidget.setCurrentText(str(defaultValue))
				aWidget.currentTextChanged.connect(partial(self.on_bool_combo_box, paramName))
			elif type == 'string':
				# text edit
				aWidget = QtWidgets.QLineEdit(defaultValue)
				#aWidget.setKeyboardTracking(False) # don't trigger signal as user edits
				#aWidget.setValidator(QIntValidator())
				#aWidget.setMaxLength(4)
				aWidget.setAlignment(QtCore.Qt.AlignLeft)
				#aWidget.setFont(QFont("Arial",20))
				aWidget.editingFinished.connect(partial(self.on_text_edit, aWidget, paramName))
			elif type == 'sanpy.bDetection.detectionTypes':
				aWidget = QtWidgets.QComboBox()
				detectionTypes = sanpy.bDetection.detectionTypes
				for theType in detectionTypes:
					aWidget.addItem(theType.name)
				aWidget.setCurrentText(str(defaultValue))
				aWidget.currentTextChanged.connect(partial(self.on_detection_type_combo_box, paramName))
			else:
				logger.error(f'Did not understand type:"{type}" for parameter:"{paramName}"')

			if aWidget is not None:
				self.widgetDict[paramName] = aWidget
				vLayoutParams.addWidget(aWidget, row, col, rowSpan, colSpan)
			#
			col += 1

			# add a 'None' button for detection parameters that allow it
			if allowNone:
				aName = f'{paramName}_none'
				aButton = QtWidgets.QPushButton('Set None')
				aButton.clicked.connect(partial(self.on_button_click, aName))
				vLayoutParams.addWidget(aButton, row, col, rowSpan, colSpan)
			#
			col += 1

			aLabel = QtWidgets.QLabel(description)
			vLayoutParams.addWidget(aLabel, row, col, rowSpan, colSpan)

			#
			row += 1
		#
		return vLayoutParams

	def _setDict(self, paramName, value):
		logger.info(f'Setting dDict key:"{paramName}" to value "{value}" type:{type(value)}')
		#self.dDict[paramName] = value
		ok = self.detectionClass.setValue(paramName, value)
		if not ok:
			logger.error('')

	def on_bool_combo_box(self, paramName, text):
		#logger.info(f'paramName:{paramName} text:"{text}" {type(text)}')
		value = text == 'True'
		self._setDict(paramName, value)

	def on_detection_type_combo_box(self, paramName, text):
		logger.info(f'paramName:"{paramName}" text:"{text}"')
		self._setDict(paramName, text)

	def on_text_edit(self, aWidget, paramName):
		text = aWidget.text()
		#logger.info(f'paramName:{paramName} text:"{text}"')
		self._setDict(paramName, text)

	def on_spin_box(self, paramName, value):
		#logger.info(f'paramName:{paramName} value:"{value}" {type(value)}')
		self._setDict(paramName, value)

	def on_button_click(self, buttonName):
		logger.info(f'buttonNme:{buttonName}')
		# set to a defined preset
		# self.dDict = sanpy.bDetection.getDefaultDetection()
		if buttonName == 'Detect':
			# take our current dDict and ba.detectSpikes
			# need to signal main interface we did this
			logger.info('NOT IMPLEMENTED')
		elif buttonName == 'Set Defaults':
			detectionPreset = sanpy.bDetection.detectionPresets.default
			self.detectionClass.setToType(detectionPreset)
			# refresh interface
			self.replot()
		elif buttonName == 'SA Node':
			detectionPreset = sanpy.bDetection.detectionPresets.saNode
			self.detectionClass.setToType(detectionPreset)
			# refresh interface
			self.replot()
		elif buttonName == 'Ventricular':
			detectionPreset = sanpy.bDetection.detectionPresets.ventricular
			self.detectionClass.setToType(detectionPreset)
			# refresh interface
			self.replot()
		elif buttonName == 'Neuron':
			detectionPreset = sanpy.bDetection.detectionPresets.neuron
			self.detectionClass.setToType(detectionPreset)
			# refresh interface
			self.replot()
		elif buttonName == 'Subthreshold':
			detectionPreset = sanpy.bDetection.detectionPresets.subthreshold
			self.detectionClass.setToType(detectionPreset)
			# refresh interface
			self.replot()
		elif buttonName == 'Ca++ Spikes':
			detectionPreset = sanpy.bDetection.detectionPresets.caSpikes
			self.detectionClass.setToType(detectionPreset)
			# refresh interface
			self.replot()
		elif buttonName.endswith('_none'):
			# set a parameter to None, will only work if 'allowNone'
			paramName = buttonName.replace('_none', '')
			self._setDict(paramName, None)
			self.replot()

		else:
			logger.warning(f'Button "{buttonName}" not understood.')

	def replot(self):
		if self.ba is None:
			return

		logger.info('')

		# ba will always have a detectionClass
		# todo: do this on switch file
		#detectionClass = self.ba.detectionClass

		detectionClass = self.detectionClass

		fileName = self.ba.getFileName()
		self.fileNameLabel.setText(f'File: {fileName}')

		#for k,v in self.widgetDict.items():
		for detectionParam in detectionClass.keys():
			if detectionParam not in self.widgetDict.keys():
				continue

			#currentValue = v['currentValue']
			currentValue = detectionClass.getValue(detectionParam)

			#print(f'  set {detectionParam} {self.widgetDict[detectionParam]} to "{currentValue}" {type(currentValue)}')

			aWidget = self.widgetDict[detectionParam]
			if isinstance(aWidget, QtWidgets.QSpinBox):
				try:
					if currentValue is None:
						aWidget.setValue(0)
					else:
						aWidget.setValue(currentValue)
				except (TypeError) as e:
					logger.error(f'QSpinBox detectionParam:{detectionParam} ... {e}')
			elif isinstance(aWidget, QtWidgets.QDoubleSpinBox):
				try:
					if currentValue is None:
						aWidget.setValue(-1e9)
					else:
						aWidget.setValue(currentValue)
				except (TypeError) as e:
					logger.error(f'QDoubleSpinBox detectionParam:{detectionParam} ... {e}')
			elif isinstance(aWidget, QtWidgets.QComboBox):
				aWidget.setCurrentText(str(currentValue))
			elif isinstance(aWidget, QtWidgets.QLineEdit):
				aWidget.setText(str(currentValue))
			else:
				logger.info(f'key "{detectionParam}" has value "{currentValue}" but widget type "{type(aWidget)}" not understood.')

	def slot_switchFile(self, rowDict, ba, replot=True):
		# don't replot until we set our detectionClass
		replot = False
		super().slot_switchFile(rowDict, ba, replot=replot)

		# grab a copy to modify and then set on 'detect'
		self.detectionClass = copy.deepcopy(self.ba.detectionClass)

		self.replot()

if __name__ == '__main__':

	path = '/home/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(path)
	ba.spikeDetect()
	print(ba.numSpikes)

	import sys
	app = QtWidgets.QApplication([])

	dp = detectionParams(ba=ba)
	#dp.show()

	scrollArea = dp.insertIntoScrollArea()
	if scrollArea is not None:
		scrollArea.show()
	else:
		dp.show()

	sys.exit(app.exec_())
