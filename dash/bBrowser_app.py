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

from bBrowser import bBrowser
		
myBrowser = bBrowser()
myBrowser.loadFolder()

#print('myBrowser.getStatList():', myBrowser.getStatList())
myStatList = myBrowser.getStatList()

#newData = myBrowser.updatePlot(xStatName='thresholdSec', yStatName='thresholdVal')

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

# plot one of 4 graphs. USed in initialization and in 'plot' button callbacks
def plotButton(graphNum):
	print('plotButton() graphNum:', graphNum)
	
	yStat = myBrowser.selectedStat_y
	xStat = myBrowser.selectedStat_x

	returnData = myBrowser.updatePlot(xStatName=xStat, yStatName=yStat)

	return {
		'data': returnData, # data is a list of go.Scatter
		'layout': {
			'xaxis': {
				'title':xStat
			},
			'yaxis': {
				'title':yStat
			},
			'margin':{'l': 50, 'b': 50, 't': 50, 'r': 50},
			'clickmode':'event+select',
			'dragmode': 'select',
		}
	}

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
			row_selectable='single',
			selected_rows=[12],
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
			row_selectable='single',
			selected_rows=[14],
		),
		], style={'width': '50%', 'display': 'inline-block', 'vertical-align': 'middle'}),
	], className='two columns'),

	html.Div(id='hidden-div2'),
		
	html.Div([
		html.Div(
			html.Div([
				dcc.Graph(
					id='myGraph1',
					figure = plotButton(0)
				),
				html.Button('Plot', id='plot1-button'),
			]), className='four columns'
		),
	
		html.Div(
			html.Div([
				dcc.Graph(
					id='myGraph2',
					figure = plotButton(1)
				),
				html.Button('Plot', id='plot2-button'),
			]), className='four columns'
		),
	], className='row'),

	html.Div(id='graph1-hidden-div'),

	]) # closing app.layout = html.Div([

#
# callbacks
#

		
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
@app.callback(
	dash.dependencies.Output('hidden-div2', 'children'),
	[
	Input('y-datatable', 'selected_rows'),
	Input('x-datatable', 'selected_rows'),
	])
def myTableSelect(y_activeCell, x_activeCell):
	print('\nmyTableSelect() y_activeCell:', y_activeCell)
	print('myTableSelect() x_activeCell:', x_activeCell)
	
	'''
	try:
		if y_activeCell is None or x_activeCell is None or len(y_activeCell)==0 or len(x_activeCell)==0:
			raise myCallbackException('myTableSelect() got empty y_activeCell or x_activeCell')
	except (myCallbackException) as e:
		#raise
		pass
	'''
			
	xSel, ySel = None, None
	if len(y_activeCell) > 0: # is not None:
		yRow = y_activeCell[0]
		ySel = myStatList[yRow]['label']
		myBrowser.selectedStat_y = ySel
	if len(x_activeCell) > 0: # is not None:
		xRow = x_activeCell[0]
		xSel = myStatList[xRow]['label']
		myBrowser.selectedStat_x = xSel
	print('myTableSelect ySel:', ySel, 'xSel:', xSel)
	

# graph 1
@app.callback(
	Output('myGraph1', 'figure'),
	[Input('plot1-button', 'n_clicks')]
)
def plotButtonCallback1(n_clicks):
	return plotButton(0)

@app.callback(
    Output('graph1-hidden-div', 'children'),
    [Input('myGraph1', 'selectedData'),]
)
def graph1_select(selectedData):
	print('graph1_select() selectedData:', selectedData)
	myPointList = []
	for point in selectedData['points']:
		print(point)
		myPointList.append(point['pointIndex'])

# graph 2
@app.callback(
	Output('myGraph2', 'figure'),
	[Input('plot2-button', 'n_clicks')]
)
def plotButtonCallback2(n_clicks):
	return plotButton(1)
	
if __name__ == '__main__':

	app.run_server(debug=True)
