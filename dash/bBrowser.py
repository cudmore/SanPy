'''
Author: RObert Cudmore
Date: 20190518

Purpose:
   Create a web based data browser of all bAnalysis files in a folder
'''

import os, collections

import pandas as pd

import dash
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go

class bBrowser:
	def __init__(self, path=''):
		if path == '':
			path = '/Users/cudmore/Sites/bAnalysis/data'
		self.path = path
		
		self.selectedRows = []
		
		self.df0 = None # small dataframe with list of files loaded
		
		self.df = None # massive dataframe with all spikes across all file
		
	def setSelectedRows(self, rows):
		self.selectedRows = rows
		
	def loadFolder(self):
		"""
		Load a hard drive folder of bAnalysis output files (e.g. .txt files) into one Pandas dataframe (df)
		"""
		if not os.path.isdir(self.path):
			print('error: bBrowser.loadFolder() did not find path:', self.path)
			return
			
		columns = ['Index',
			'Analysis File',
			'ABF File',
			'Num Spikes',
			'First Spike (Sec)',
			'Last Spike (sec)'
		]
		self.df0 = pd.DataFrame(columns=columns)
		
		df0_list = []
		
		currIdx = 0
		for file in os.listdir(self.path):
			if file.startswith('.'):
				continue
			if file.endswith('.txt'):
				currFile = os.path.join(self.path,file)
				print('bBrowser.loadFolder() loading analysis file:', currFile)
				df = pd.read_csv(currFile, header=0) # load comma seperated values, read header names from row 1
				df.insert(0, 'Analysis File', file)

				numSpikes = len(df.index)
				firstSpikeSec = df['thresholdSec'].min()
				lastSpikeSec = df['thresholdSec'].max()
				abfFile = df.iloc[0]['file']
				#abfFile = os.path.split(abfFile)[1] # get the file name from the path
				
				dfRow = collections.OrderedDict()
				dfRow['Index'] = currIdx + 1
				dfRow['Analysis File'] = file
				dfRow['ABF File'] = abfFile
				dfRow['Num Spikes'] = numSpikes
				dfRow['First Spike (Sec)'] = firstSpikeSec
				dfRow['Last Spike (Sec)'] = lastSpikeSec

				df0_list.append(dfRow)
				
				# BIG df with ALL spikes
				if self.df is None:
					self.df = df
				else:
					self.df = pd.concat([self.df, df], axis=0)
								
				currIdx += 1
			
		self.df0 = pd.DataFrame(df0_list)
	
	def getStatList(self):
		skipColumns = [''] #['file', 'spikeNumber', 'numError', 'errors', 'dVthreshold', 'medianFilter', 'halfHeights']
		retList = []
		mySpikeNumber = 0
		for column in self.df:
			if column in skipColumns:
				continue
			optionsDict = {
				'label': column,
				'value': column
			}
			retList.append(optionsDict)
		return retList
		
	def updatePlot(self, xStatName, yStatName):
		""" return a list of dict for plotly/dash data"""
		
		theRet = []
		
		if xStatName and yStatName:
			for index, row in self.df0.iterrows():
				#print(index, row['ABF File'])
				#print(index, row)
		
				analysisFile = row['Analysis File']
				abfFile = row['ABF File']

				thisFileRows = self.df.loc[self.df['Analysis File'] == analysisFile]

				# get rows in self.df corresponding to abfFile
				xStatVals = thisFileRows[xStatName]
				yStatVals = thisFileRows[yStatName]
			
				dataDict = {}
				dataDict['x'] = xStatVals
				dataDict['y'] = yStatVals
				dataDict['mode'] = 'markers'
				dataDict['name'] = analysisFile + ':' + abfFile
			
				theRet.append(dataDict)
			
		return theRet
		
myBrowser = bBrowser()
myBrowser.loadFolder()

#print('myBrowser.getStatList():', myBrowser.getStatList())
myStatList = myBrowser.getStatList()

newData = myBrowser.updatePlot(xStatName='thresholdSec', yStatName='thresholdVal')

app = dash.Dash(__name__)

"""
			'''
			'data': [
				{
					'x': [1, 2, 3, 4],
					'y': [4, 1, 3, 5],
					'text': ['a', 'b', 'c', 'd'],
					'customdata': ['c.a', 'c.b', 'c.c', 'c.d'],
					'name': 'Trace 1',
					'mode': 'markers',
					'marker': {'size': 12}
				},
				{
					'x': [1, 2, 3, 4],
					'y': [9, 4, 1, 4],
					'text': ['w', 'x', 'y', 'z'],
					'customdata': ['c.w', 'c.x', 'c.y', 'c.z'],
					'name': 'Trace 2',
					'mode': 'markers',
					'marker': {'size': 12}
				}
			],
			'''
"""

app.layout = html.Div([
	
	dash_table.DataTable(
		id='file-list-table',
		row_selectable='multi',
		columns=[{"name": i, "id": i} for i in myBrowser.df0],
		#data=df.to_dict('records'),
		data=myBrowser.df0.to_dict('records'),
	),
	html.Div(id='hidden-div'),

	html.Div([
		html.Div([
		dash_table.DataTable(
			id='y-datatable',
			columns=[{"name": 'Idx', "id": 'Idx'}, {"name": 'Stat', "id": 'stat'}],
			data=[{"Idx": idx+1, "stat": myOption['label']} for idx, myOption in enumerate(myStatList)],
			style_table={
				'maxWidth': '300',
				'maxHeight': '300',
				'overflowY': 'scroll'
			},
			style_cell={'textAlign': 'left'},
			style_header={
				'backgroundColor': 'ltgray',
				'fontWeight': 'bold'
			},
			row_selectable=True,
			selected_rows=[12],
			#active_cell=[12,0],
		),
		], style={'width': '50%', 'display': 'inline-block', 'vertical-align': 'middle'}),

		html.Div([
		dash_table.DataTable(
			id='x-datatable',
			columns=[{"name": 'Idx', "id": 'Idx'}, {"name": 'Stat', "id": 'stat'}],
			data=[{"Idx": idx+1, "stat": myOption['label']} for idx, myOption in enumerate(myStatList)],
			style_table={
				'maxWidth': '300',
				'maxHeight': '300',
				'overflowY': 'scroll'
			},
			style_cell={'textAlign': 'left'},
			style_header={
				'backgroundColor': 'ltgray',
				'fontWeight': 'bold'
			},
			row_selectable=True,
			selected_rows=[14],
			#active_cell=[14,0],
		),
		], style={'width': '50%', 'display': 'inline-block', 'vertical-align': 'middle'}),
	], className='two columns'),

		
	dcc.Graph(
		id='life-exp-vs-gdp',
		figure={
			'data': newData, # data is a list of go.Scatter
			'layout': {
				#'title': 'xxxyyy',
				'xaxis': {
					'title':''
				},
				'yaxis': {
					'title':''
				},
				'margin':{'l': 50, 'b': 50, 't': 50, 'r': 50},
				'clickmode':'event+select'
			}
		}
	),

	]) # closing app.layout = html.Div([

#
# callbacks
#

class myCallbackException(Exception):
	def __init__(self, str):
		print('myCallbackException:', str)
		pass
		#raise
		
#
# analysis file selection
@app.callback(
	Output('hidden-div', 'children'),
	[Input('file-list-table', "derived_virtual_data"),
     Input('file-list-table', "derived_virtual_selected_rows")])
def myFileListSelect(rows, derived_virtual_selected_rows):
	"""
	rows: all the rows in the table ???
	derived_virtual_selected_rows: list of int of selected rows (rows that are checked)
	"""
	print('\nmyFileListSelect() rows:', rows)
	print('myFileListSelect() derived_virtual_selected_rows:', derived_virtual_selected_rows)
	myBrowser.setSelectedRows(rows)
	
#
# x/y stat selection
'''
	Input('y-datatable', 'active_cell'),
	Input('x-datatable', 'active_cell'),
'''
@app.callback(
	Output('life-exp-vs-gdp', 'figure'),
	[
	Input('y-datatable', 'selected_rows'),
	Input('x-datatable', 'selected_rows'),
	])
def myTableSelect(y_activeCell, x_activeCell):
	print('\nmyTableSelect() y_activeCell:', y_activeCell)
	print('myTableSelect() x_activeCell:', x_activeCell)
	
	try:
		if y_activeCell is None or x_activeCell is None or len(y_activeCell)==0 or len(x_activeCell)==0:
			raise myCallbackException('myTableSelect() got empty y_activeCell or x_activeCell')
	except (myCallbackException) as e:
		#raise
		pass
			
	xSel, ySel = None, None
	if len(y_activeCell) > 0: # is not None:
		yRow = y_activeCell[0]
		ySel = myStatList[yRow]['label']
	if len(x_activeCell) > 0: # is not None:
		xRow = x_activeCell[0]
		xSel = myStatList[xRow]['label']
	print('myTableSelect ySel:', ySel, 'xSel:', xSel)
	
	returnData = myBrowser.updatePlot(xStatName=xSel, yStatName=ySel)

	return {
		'data': returnData, # data is a list of go.Scatter
		'layout': {
			'xaxis': {
				'title':xSel
			},
			'yaxis': {
				'title':ySel
			},
			'margin':{'l': 50, 'b': 50, 't': 50, 'r': 50},
			'clickmode':'event+select'
		}
	}

if __name__ == '__main__':

	app.run_server(debug=True)
