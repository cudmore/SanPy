# Robert Cudmore
# 20181127

"""
self.eventTree
"""

import numpy as np

import tkinter
from tkinter import ttk
from tkinter import messagebox

import bDialog

###################################################################################
class bTree(ttk.Frame):
	def __init__(self, parent, parentApp, *args, **kwargs):
		ttk.Frame.__init__(self, parent)
		
		self.myParentApp = parentApp
		self.myParent = parent
		
		myPadding = 5

		self.grid_rowconfigure(0, weight=1)
		self.grid_columnconfigure(0, weight=1)

		self.treeview = ttk.Treeview(self, selectmode="browse", show=['headings'], *args, **kwargs)
		self.treeview.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)

		self.scrollbar = ttk.Scrollbar(self, orient="vertical", command = self.treeview.yview)
		self.scrollbar.grid(row=0, column=0, sticky='nse', padx=myPadding, pady=myPadding)
		self.treeview.configure(yscrollcommand=self.scrollbar.set)

	def sort_column(self, col, reverse):
		print('=== bTree.sort_column()()', 'col:', col, 'reverse:', reverse)

		sortType = 'float'
		if col in ['file', 'note']:
			sortType = 'str'
			#print('   not allowed to sort on:', col)
			#return 0
		
		itemList = self.treeview.get_children()
		
		frameStartList = []
		valuesList = [] # list of each rows 'values'
		for item in self.treeview.get_children(''):
			# set() here is actually getting row as dict (names are column name)
			itemColValue = self.treeview.set(item, col) # itemColValue is always a string
			if sortType == 'str':
				currentFrameStart = itemColValue # itemColValue is a str
			else:
				if itemColValue:
					currentFrameStart = float(itemColValue)
				else:
					# handles empy string ''
					currentFrameStart = np.NaN
			frameStartList.append(currentFrameStart)

			values = self.treeview.item(item, 'values')
			valuesList.append(values)
			
		#print('frameStartList:', frameStartList)
		
		sortOrder = np.argsort(frameStartList).tolist()
		
		if reverse:
			sortOrder = list(reversed(sortOrder))
		
		#print('sortOrder:', sortOrder)
		
		"""
		# get current selection
		selectedIndex, selectedItem = self._getTreeViewSelection('index')
		"""
		
		# first delete entries
		"""for i in self.treeview.get_children():
			self.treeview.delete(i)
		"""
		
		# re-insert in proper order
		for idx, i in enumerate(sortOrder):
			#event = self.eventList.eventList[i]
			position = idx
			values = valuesList[i]
			#self.treeview.insert("" , position, text=str(idx+1), values=values)
			self.treeview.move(itemList[i], '', idx)
			
		# if sorted by frameStart then flag each item for out of order
		if col == 'frameStart':
			for idx, i in enumerate(sortOrder):
				self.flagOverlap(itemList[i])

		# re-select original selection
		#print('selectedIndex:', selectedIndex, type(selectedIndex))
		"""
		if selectedIndex is not None:
			selectedIndex = int(selectedIndex)
			self._selectTreeViewRow('index', selectedIndex)
		"""
		
		
		# reverse sort next time
		self.treeview.heading(col, command=lambda:self.sort_column(col, not reverse))

	def _getTreeViewSelection(self, col):
		"""
		Get value of selected column
			tv: treeview
			col: (str) column name
		"""
		item = self.treeview.focus()
		if item == '':
			print('_getTreeViewSelection() did not find a selection in treeview')
			return None, None
		columns = self.treeview['columns']				
		colIdx = columns.index(col) # assuming 'frameStart' exists
		values = self.treeview.item(item, "values") # tuple of a values in tv row
		theRet = values[colIdx]
		return theRet, item

	def _selectTreeViewRow(self, col, isThis):
		"""
		Given a column name (col) and a value (isThis)
		Visually select the row in tree view that has column mathcing isThis
		
		col: (str) column name
		isThis: (str) value of a cell in column (col)
		"""
		if not isinstance(isThis, str):
			print('warning: _selectTreeViewRow() expecting string isThis, got', type(isThis))
		
		theRow, theItem = self._getTreeViewRow(col, isThis)
		
		if theRow is not None:
			# get the item
			children = self.treeview.get_children()
			item = children[theRow]
			#print('item:', item)
			
			# select the row
			self.treeview.focus(item) # select internally
			self.treeview.selection_set(item) # visually select
		else:
			print('warning: _selectTreeViewRow() did not find row for col:', col, 'matching:', isThis, type(isThis))
			
	def _getTreeViewRow(self, col, isThis):
		"""
		Given a treeview, a col name and a value (isThis)
		Return the row index of the column col matching isThis
		"""
		if not isinstance(isThis, str):
			print('warning: _getTreeViewRow() expecting string isThis, got', type(isThis))

		#print('_getTreeViewRow col:', col, 'isThis:', isThis)

		# get the tree view columns and find the col we are looking for
		columns = self.treeview['columns']				
		try:
			colIdx = columns.index(col) # assuming 'frameStart' exists
		except (ValueError):
			print('warning: _getTreeViewRow() did not find col:', col)
			colIdx = None
					
		theRet = None
		theItem = None
		if colIdx is not None:
			rowIdx = 0
			for child in self.treeview.get_children():
				values = self.treeview.item(child)["values"] # values at current row
				#print('type(values[colIdx])', type(values[colIdx]))
				#print('values[colIdx]: "' + values[colIdx] + '"', 'looking for isThis "' + isThis + '"')
				if values[colIdx] == isThis:
					theRet = rowIdx
					theItem = child
					break
				rowIdx += 1
		#else:
		#	print('_getTreeViewRow() did not find col:', col)
		
		return theRet, theItem
			
###################################################################################
class bFileTree(bTree):
	def __init__(self, parent, parentApp, videoFileList, *args, **kwargs):
		bTree.__init__(self, parent, parentApp, *args, **kwargs)
		
		self.videoFileList = videoFileList # bVideoList object

	def populateVideoFiles(self, videoFileList, doInit=False):
		print('bVideoFileTree.populateVideoFiles()')
		
		self.videoFileList = videoFileList # bVideoList object

		if doInit:
			videoFileColumns = self.videoFileList.getColumns()
			
			# configure columns
			self.treeview['columns'] = videoFileColumns
			hideColumns = ['Path'] # hide some columns
			displaycolumns = [] # build a list of columns not in hideColumns
			for column in videoFileColumns:
				self.treeview.column(column, width=10)
				self.treeview.heading(column, text=column, command=lambda c=column: self.sort_column(c, False))
				if column not in hideColumns:
					displaycolumns.append(column)

			# set some column widths, width is in pixels?
			self.treeview.column('Index', width=5)
			
			# set some column widths, width is in pixels?
			#gVideoFileColumns = ('index', 'path', 'file', 'width', 'height', 'frames', 'fps', 'seconds', 'numevents', 'note')
			defaultWidth = 120
			self.treeview.column('Index', minwidth=50, width=50, stretch="no")
			self.treeview.column('File', width=300)

			self.treeview.column('kHz', minwidth=defaultWidth, width=defaultWidth, stretch="no")
			self.treeview.column('Duration (sec)', minwidth=defaultWidth, width=defaultWidth, stretch="no")
			self.treeview.column('Sweeps', minwidth=defaultWidth, width=defaultWidth, stretch="no")

			'''
			self.treeview.column('width', minwidth=defaultWidth, width=defaultWidth, stretch="no")
			self.treeview.column('height', minwidth=defaultWidth, width=defaultWidth, stretch="no")
			self.treeview.column('frames', minwidth=defaultWidth, width=defaultWidth, stretch="no")
			self.treeview.column('fps', minwidth=defaultWidth, width=defaultWidth, stretch="no")
			self.treeview.column('seconds', minwidth=defaultWidth, width=defaultWidth, stretch="no")
			self.treeview.column('minutes', minwidth=defaultWidth, width=defaultWidth, stretch="no")
			self.treeview.column('numevents', minwidth=defaultWidth, width=defaultWidth, stretch="no")
			'''
			
			# hide some columns
			self.treeview["displaycolumns"] = displaycolumns
			
			self.treeview.bind("<ButtonRelease-1>", self.single_click)

			# right-click popup
			# see: https://stackoverflow.com/questions/12014210/tkinter-app-adding-a-right-click-context-menu
			'''
			self.popup_menu = tkinter.Menu(self.treeview, tearoff=0)
			self.popup_menu.add_command(label="Set Note",
										command=self.setNote)
			self.treeview.bind("<Button-2>", self.popup)
			self.treeview.bind("<Button-3>", self.popup) # Button-2 on Aqua
			'''
			
		# first delete entries
		for i in self.treeview.get_children():
			self.treeview.delete(i)

		for idx, videoFile in enumerate(self.videoFileList.getList()):
			position = "end"
			self.treeview.insert("" , position, text=str(idx+1), values=videoFile.asTuple())

	def single_click(self, event):
		""" display events """
		print('=== bVideoFileTree.single_click()')		
		
		# get video file path
		path, item = self._getTreeViewSelection('Path')
		#print('   path:', path)

		if path is None:
			# when heading is clicked
			pass
		else:
			# switch video stream
			self.myParentApp.switchvideo(path, paused=True, gotoFrame=0)
		
		"""
		# switch event list
		self.eventList = bEventList.bEventList(path)
		
		# populate event list tree
		self.populateEvents()
		
		# set feedback frame
		self.numFrameLabel['text'] = 'of ' + str(self.vs.streamParams['numFrames'])
		self.numSecondsLabel['text'] = 'of ' + str(self.vs.streamParams['numSeconds'])
		
		# set frame slider
		self.video_frame_slider['to'] = self.vs.streamParams['numFrames']
		"""

	def setNote(self):
		print('bVideoFileTree.setNote() not implemented')
		#self.selection_set(0, 'end')

	def popup(self, event):
		print('popup()')
		try:
			self.popup_menu.tk_popup(event.x_root, event.y_root) #, 0)
		finally:
			self.popup_menu.grab_release()
		

###################################################################################
if __name__ == '__main__':
	print('testing')
	
	myPadding = 5
	
	# fire up a small tkinter app
	import tkinter
	root = tkinter.Tk()

	# load an event list
	firstVideoPath = '/Users/cudmore/Dropbox/PiE/video/1-homecage-movie.mp4'
	#eventList = bEventList.bEventList(firstVideoPath)
	
	# this will not work because we do not have VideoApp parent app
	parentApp = None
	et = bEventTree(root, parentApp, firstVideoPath)
	et.grid(row=0,column=0, sticky="nsew", padx=myPadding, pady=myPadding)
	
	#et.populateEvents(eventList, doInit=True)
	
	root.mainloop()
	