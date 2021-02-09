from tkinter import *
import matplotlib
from pandastable import Table, TableModel

import dualAnalysis

class MyTable(Table):
	"""Custom table class inherits from Table. You can then override required methods"""
	def __init__(self, parent=None, app=None, **kwargs):
		Table.__init__(self, parent, **kwargs)

		self.app = app

		self.figList = [None] * len(self.model.df)
		self.spikeClipList = [None] * len(self.model.df)
		self.spikeDetectionList = [None] * len(self.model.df)

	def handle_left_click(self, event):
		"""Example - override left click"""
		Table.handle_left_click(self, event)

		return # now using right click

		#do custom code here
		print('handle_left_click() event:', type(event), event)
		selectedRow = self.getSelectedRow()
		print('  selectedRow:', selectedRow)

		if self.figList[selectedRow] is not None:
			# bring to front
			self.figList[selectedRow].show()
		else:
			# load and plot
			self.figList[selectedRow] = self.myPlotRow(selectedRow)
			print('self.figList[selectedRow]:', self.figList[selectedRow])

		#
		return

	def popupMenu(self, event, rows=None, cols=None, outside=None):
		"""Custom right click menu"""

		popupmenu = Menu(self, tearoff = 0)
		def popupFocusOut(event):
			popupmenu.unpost()
			# add commands here

		# self.app is a reference to the parent app
		popupmenu.add_command(label='Plot Dual Recording', command=self.myRightClick)
		popupmenu.add_command(label='Plot Spike Detection', command=self.myRightClickDetection)
		popupmenu.add_command(label='Plot Spike Phase', command=self.myRightClickPhase)
		popupmenu.bind("<FocusOut>", popupFocusOut)
		popupmenu.focus_set()
		popupmenu.post(event.x_root, event.y_root)
		return popupmenu

	def closeChild(self, type, fileNumber):
		"""
		type: (spike cclip plot, raw plot)
		"""
		if type == 'raw plot':
			self.figList[fileNumber] = None
		elif type == 'spike clip plot':
			self.spikeClipList[fileNumber] = None
		else:
			print('warning: table.closeChild() did not understand type:', type)

	#
	# plot dual recording
	#
	def myRightClick(self):
		selectedRow = self.getSelectedRow()
		print('myRightClick selectedRow:', selectedRow)
		self.figList[selectedRow] = self.myPlotRow(selectedRow)

	# plot (kymograph, ca, vm)
	def myPlotRow(self, rowNumber):
		tifFile = self.model.df['tifPath'].loc[rowNumber]
		abfFile = self.model.df['abfPath'].loc[rowNumber]
		region = self.model.df['region'].loc[rowNumber]
		print('  plotting tifFile:', tifFile)
		dr = dualAnalysis.dualRecord(tifFile, abfFile)

		'''
		print('matplotlib.rcsetup.interactive_bk:', matplotlib.rcsetup.interactive_bk)
		print('matplotlib.get_backend()', matplotlib.get_backend())
		matplotlib.use('Qt4Agg',force=True)
		from matplotlib import pyplot as plt
		print('matplotlib.get_backend()', matplotlib.get_backend())
		'''

		fig = dr.myPlot(fileNumber=rowNumber, region=region, myParent=self)
		fig.show()

		'''
		matplotlib.use('TkAgg',force=True)
		from matplotlib import pyplot as plt
		'''

		return fig

	# plot detected spikes
	def myRightClickDetection(self):
		rowNumber = self.getSelectedRow()
		tifFile = self.model.df['tifPath'].loc[rowNumber]
		abfFile = self.model.df['abfPath'].loc[rowNumber]
		print('  myRightClickDetection plotting tifFile:', tifFile)
		df = self.model.df
		dr = dualAnalysis.dualRecord(tifFile, abfFile)
		figTif, figAbf = dr.plotSpikeDetection_df(df, rowNumber, myParent=self)
		figTif.show()
		figAbf.show()
		return figTif # todo: fix this

	# plot phase
	def myRightClickPhase(self):
		selectedRow = self.getSelectedRow()
		print('myRightClick selectedRow:', selectedRow)
		self.myPlotPhase(selectedRow)

	def myPlotPhase(self, rowNumber):
		tifFile = self.model.df['tifPath'].loc[rowNumber]
		abfFile = self.model.df['abfPath'].loc[rowNumber]
		print('  plotting tifFile:', tifFile)
		df = self.model.df
		dr = dualAnalysis.dualRecord(tifFile, abfFile)
		fig = dr.plotSpikeClip_df(df, rowNumber, myParent=self)
		#dr = dualAnalysis.dualRecord(tifFile, abfFile)
		#fig = dr.plotSpikeClip(doPhasePlot=True, fileNumber=rowNumber, myParent=self)
		fig.show()
		return fig

class TestApp(Frame):
		"""Basic test frame for the table"""
		def __init__(self, parent=None):
			self.parent = parent
			Frame.__init__(self)
			self.main = self.master
			self.main.geometry('600x400+200+100')
			self.main.title('Table app')
			f = Frame(self.main)
			f.pack(fill=BOTH,expand=1)

			df = dualAnalysis.loadDatabase()
			#df = TableModel.getSampleData()

			self.table = pt = MyTable(f,
								app=self,
								dataframe=df,
								showtoolbar=False,
								showstatusbar=True)
								#parent=self)
			pt.show()
			return

app = TestApp()
#launch the app
app.mainloop()
