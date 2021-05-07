def old_file_table_get_value(self, thisRow, thisColumnName):
	"""
	get the value of a column columnName at a selected row
	"""
	theValue = ''

	numCol = self.myTableWidget.columnCount()
	for j in range(numCol):
		headerText = self.myTableWidget.horizontalHeaderItem(j).text()
		if headerText == thisColumnName:
			theValue = self.myTableWidget.item(thisRow,j).text()
			break
	if len(theValue) > 0:
		return theValue
	else:
		print('error: file_table_get_value() did not find', thisRow, thisColumnName)
		return None

def old_on_file_table_click(self):
	row = self.myTableWidget.currentRow()

	findThisColumn = 'File'
	fileName = ''

	# todo: replace this with file_table_get_value()
	numCol = self.myTableWidget.columnCount()
	for j in range(numCol):
		headerText = self.myTableWidget.horizontalHeaderItem(j).text()
		if headerText == findThisColumn:
			tmpItem = self.myTableWidget.item(row,j)
			if tmpItem is not None:
				fileName = tmpItem.text()
			break

	if len(fileName) > 0:
		#spinner = WaitingSpinner(self.myTableWidget, True, True, QtCore.Qt.ApplicationModal)
		#spinner.start() # starts spinning

		path = os.path.join(self.path, fileName)
		print('=== sanpy.on_file_table_click() row:', row+1, 'path:', path)
		self.myDetectionWidget.switchFile(path)

		# we should be able to open one for each file?
		#if self.myExportWidget is not None:
		#	self.myExportWidget.setFile2(path, plotRaw=True)

		#spinner.stop() # starts spinning

	else:
		print('error: on_file_table_click() did not find File name at row:', row)

def old_refreshFileTableWidget_Row(self):
	"""
	refresh the selected row
	"""
	selectedRow = self.myTableWidget.currentRow()
	selectedFile = self.file_table_get_value(selectedRow, 'File')

	# abb 202012
	# if abfError then set file name text to red
	abfError = self.fileList.getFileError(selectedFile)

	fileValues = self.fileList.getFileValues(selectedFile) # get list of values in correct column order
	for colIdx, fileValue in enumerate(fileValues):
		if str(fileValue) == 'None':
			fileValue = ''
		item = QtWidgets.QTableWidgetItem(str(fileValue))
		if colIdx==0 and abfError:
			item.setForeground(QtGui.QBrush(QtGui.QColor("#DD4444")))
		self.myTableWidget.setItem(selectedRow, colIdx, item)
		self.myTableWidget.setRowHeight(selectedRow, self._rowHeight)

def old_refreshFileTableWidget(self):
	#print('refreshFileTableWidget()')

	if self.fileList is None:
		print('refreshFileTableWidget() did not find a file list')
		return

	#self.myTableWidget.setShowGrid(False) # remove grid
	#self.myTableWidget.setFont(QtGui.QFont('Arial', 13))

	#
	# this will not change for a given path ???
	numRows = self.fileList.numFiles()
	numCols = len(self.fileList.getColumns())
	self.myTableWidget.setRowCount(numRows+1) # trying to get last row visible
	self.myTableWidget.setColumnCount(numCols)

	headerLabels = self.fileList.getColumns()
	self.myTableWidget.setHorizontalHeaderLabels(headerLabels)

	header = self.myTableWidget.horizontalHeader()
	header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
	header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
	header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)

	#
	# update to reflect analysis date/time etc
	fileList = self.fileList.getList() #ordered dict of files

	#for idx, filename in enumerate(fileList.keys()):
	for idx, filename in enumerate(sorted(fileList)):
		abfError = self.fileList.getFileError(filename) # abb 202012
		fileValues = self.fileList.getFileValues(filename) # get list of values in correct column order
		#print('refreshFileTableWidget()', idx+1, filename, fileValues)
		for idx2, fileValue in enumerate(fileValues):
			if str(fileValue) == 'None':
				fileValue = ''
			item = QtWidgets.QTableWidgetItem(str(fileValue))
			if idx2==0 and abfError:
				item.setForeground(QtGui.QBrush(QtGui.QColor("#DD4444")))
			self.myTableWidget.setItem(idx, idx2, item)
			self.myTableWidget.setRowHeight(idx, self._rowHeight)

def old_export_pdf(self):
	"""
	Open a new window with raw Vm and provide interface to save as pdf
	"""
	if self.myDetectionWidget.ba is not None:
		#self.myExportWidget = sanpy.bExportWidget(self.myDetectionWidget.ba.file)
		sweepX = self.myDetectionWidget.ba.abf.sweepX
		sweepY = self.myDetectionWidget.ba.abf.sweepY
		xyUnits = ('Time (sec)', 'Vm (mV)')
		self.myExportWidget = sanpy.bExportWidget(sweepX, sweepY,
							path=self.myDetectionWidget.ba.file,
							xyUnits=xyUnits,
							darkTheme=self.useDarkStyle)
	else:
		print('please select an abf file')

		def old_getTableRowDict(self):
			"""
			return a dict with selected row as dict (includes detection parameters)
			"""
			theRet = None
			if self.selectedRow is not None:
				theRet = {}
				for column in self.myModel._data.columns:
					theRet[column] = self.getTableValue(self.selectedRow, column)
			return theRet

		def old_getTableValue(self, rowIdx, colStr):
			val = None
			if colStr not in self.myModel._data.columns: # columns is a list
				print('error: getTableValue() got bad column name:', colStr)
			elif len(self.myModel._data)-1 < rowIdx:
				print('error: getTableValue() got bad row:', row)
			else:
				val = self.myModel._data.loc[rowIdx, colStr]
			return val
