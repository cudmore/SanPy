'''
Author: Robert Cudmore
Date: 20190518

Purpose:
   Create a web based data browser of all bAnalysis files in a folder
'''

import os, datetime, json, collections

import pandas as pd
import numpy as np

from itertools import chain

import dash
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go

import dash_bootstrap_components as dbc # dash bootstrap https://github.com/facultyai/dash-bootstrap-components

from bBrowser import bBrowser

myBrowser = bBrowser()
myBrowser.loadFolder()

myStatList = myBrowser.getStatList()

statDict = collections.OrderedDict()
statDict['Take Off Potential (s)'] = 'thresholdSec'
statDict['AP Peak (mV)'] = 'peakVal'
statDict['AP Height (mV)'] = 'peakHeight'
statDict['Pre AP Min (mV)'] = 'preMinVal'
statDict['Post AP Min (mV)'] = 'postMinVal'
statDict['AP Duration (ms)'] = 'apDuration_ms'
statDict['Early Diastolic Duration (ms)'] = 'earlyDiastolicDuration_ms'
statDict['Diastolic Duration (ms)'] = 'diastolicDuration_ms'
statDict['Inter-Spike-Interval (ms)'] = 'isi_ms'
statDict['Cycle Length (ms)'] = 'cycleLength_ms'
statDict['Max AP Upstroke (dV/dt)'] = 'preSpike_dvdt_max_val2'
statDict['Max AP Upstroke (mV)'] = 'preSpike_dvdt_max_val'
statDict['Max AP Repolarization (dV/dt)'] = 'postSpike_dvdt_min_val2'
statDict['Max AP Repolarization (mV)'] = 'postSpike_dvdt_min_val'
statDict['Condition 1'] = 'Condition 1'
statDict['Condition 2'] = 'Condition 2'

myStatList = list(statDict.keys())

# plot one of 4 graphs. USed in initialization and in 'plot' button callbacks
def plotButton(graphNum):

	yStatHuman = myBrowser.graphPlot[graphNum]['yStat']
	xStatHuman = myBrowser.graphPlot[graphNum]['xStat']

	# convert human readable cardiac stats back to back end stat name
	yStat = statDict[yStatHuman]
	xStat = statDict[xStatHuman]

	print('bBrowser_app.plotButton() graphNum:', graphNum, 'xStat:', xStat, 'yStat:', yStat)

	returnData = myBrowser.updatePlot(xStatName=xStat, yStatName=yStat)

	# determine min/max so we can expand by 5%
	xRange = []
	'''
	xList = [data['x'] for data in returnData]
	print('xList:', xList)
	if len(xList) > 0:
		xMin = np.nanmin(xList)
		xMax = np.nanmax(xList)
		xBuffer = (xMax-xMin) * 0.05
		xRange = [xMin-xBuffer, xMax+xBuffer]
	'''
	yRange = []
	'''yList = [data['y'] for data in returnData]
	if len(yList) > 0:
		yMin = np.nanmin(yList)
		yMax = np.nanmax(yList)
		yBuffer = (yMax-yMin) * 0.05
		yRange = [yMin-yBuffer, yMax+yBuffer]
	'''

	return {
		'data': returnData, # data is a list of go.Scatter
		'layout': {
			'xaxis': {
				'title':xStatHuman,
				'zeroline':False,
				'range':xRange,
			},
			'yaxis': {
				'title':yStatHuman,
				'zeroline':False,
			},
			'margin':{'l': 50, 'b': 50, 't': 5, 'r': 5},
			'clickmode':'event+select',
			'dragmode': 'select',
			'showlegend': False,
		}
	}

#app = dash.Dash(__name__)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
#app.css.append_css({'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'})  # noqa: E501

app.css.append_css({
   'external_url': (
       'static/my.css'
   )
})

graph_names = ['g1', 'g2', 'g3', 'g4']

pre_style = {"backgroundColor": "#ddd", "fontSize": 20, "padding": "10px", "margin": "10px"}

###########
editableColumns = [1, 2]

def myStyleDataConditional():
	""" return a list of dict, one item per file"""
	m = len(myBrowser.df0.index)
	theRet = []
	for rowIdx in range(m):
		theDict = {}
		theDict = {
			'if': {
				'column_id': 'Index',
				'filter': '{Index} eq ' + str(rowIdx+1)
			},
			'backgroundColor': myBrowser.plotlyColors[rowIdx],
			'color': 'white',
		}
		theRet.append(theDict)
	return theRet
	
print(myStyleDataConditional())

myBody = dbc.Container(
	[
		dbc.Row(
			[
				dbc.Col(
					[
						#html.H5('File List'),

						dash_table.DataTable(
							id='file-list-table',
							row_selectable='multi',
							# i want to make only certain column cells editable
							columns=[{'name':i, 'id':i, 'editable':True} for i in myBrowser.df0], 

							style_data_conditional = myStyleDataConditional(),
							
							data=myBrowser.df0.to_dict('records'),
							editable=True, # this makes all cells editable
							selected_rows=[0,1],
						),
					])
			]
		),

		html.P(''),

		dbc.Row(
			[
				html.H6("Options"),

				dcc.Checklist(
					id='showMeanID',
					options=[
						{'label': 'Lines', 'value': 'showLines'},
						{'label': 'Markers', 'value': 'showMarkers'},
						{'label': 'Mean', 'value': 'showMean'},
						{'label': 'Mean Lines', 'value': 'showMeanLines'},
					], values=['showMarkers', 'showMean', 'showMeanLines'], labelStyle={'padding-left': '20px', 'display': 'inline-block'}
				),

				html.Div('Error Bars', style={'padding-left': '20px', 'display': 'inline-block'}),
				dcc.RadioItems(
					id='showSDEVID',
					options=[
						{'label': 'None', 'value': 'None'},
						{'label': 'SEM', 'value': 'SEM'},
						{'label': 'SDEV', 'value': 'SDEV'},
					],
					value='SEM',
					labelStyle={'padding-left': '10px', 'display': 'inline-block'}
				),
			], no_gutters=False, align='stretch', # row
		),

		dbc.Row(
			[
				dbc.Col(
					[

						# X-Stat
						#html.H5("X-Stat"),

						dash_table.DataTable(
							id='x-datatable',
							columns=[{"name": '', "id": 'Idx'}, {"name": 'X Stat', "id": 'stat'}],
							#data=[{"Idx": idx+1, "stat": myOption['label']} for idx, myOption in enumerate(myStatList)],
							data=[{"Idx": idx+1, "stat": myOption} for idx, myOption in enumerate(myStatList)],
							style_table={
								'maxHeight': '800px',
								'overflowY': 'scroll'
							},
							style_cell={'textAlign': 'left'},
							style_header={
								'backgroundColor': 'ltgray',
								'fontWeight': 'bold'
							},
							style_cell_conditional=[{
								'if': {'row_index': 'odd'},
								'backgroundColor': 'rgb(248, 248, 248)'
							}],
							row_selectable='single',
							selected_rows=[0],
						),

						html.P(''),

						#html.H5("Y-Stat"),

						dash_table.DataTable(
							id='y-datatable',
							columns=[{"name": '', "id": 'Idx'}, {"name": 'Y Stat', "id": 'stat'}],
							#data=[{"Idx": idx+1, "stat": myOption['label']} for idx, myOption in enumerate(myStatList)],
							data=[{"Idx": idx+1, "stat": myOption} for idx, myOption in enumerate(myStatList)],
							style_table={
								'maxHeight': '800px',
								'overflowY': 'scroll'
							},
							style_cell={'textAlign': 'left'},
							style_header={
								'backgroundColor': 'ltgray',
								'fontWeight': 'bold'
							},
							style_cell_conditional=[{
								'if': {'row_index': 'odd'},
								'backgroundColor': 'rgb(248, 248, 248)'
							}],
							row_selectable='single',
							selected_rows=[1],
						),						

					],
					width={'size':100},

				),
				dbc.Col(
					[
						dbc.Button("Plot 1", color="primary", outline=True, size="sm", id='g1-plot-button'),
						dcc.Graph(
							id='g1',
							figure=plotButton(0),
						),

						dbc.Button("Plot 3", color="primary", outline=True, size="sm", id='g3-plot-button'),
						dcc.Graph(
							id='g3',
							figure=plotButton(2),
						),
					],
					md=4, align='stretch',

				),
				dbc.Col(
					[
						dbc.Button("Plot 2", color="primary", outline=True, size="sm", id='g2-plot-button'),
						dcc.Graph(
							id='g2',
							figure=plotButton(1),
						),

						dbc.Button("Plot 4", color="primary", outline=True, size="sm", id='g4-plot-button'),
						dcc.Graph(
							id='g4',
							figure=plotButton(3),
						),
					],
					md=4, align='stretch',
				),
			], no_gutters=False, align='stretch', # row
		)
	], className="mt-4", fluid=True,
)

##############
app.layout = html.Div([

	myBody,

	html.Div(id='hidden-div'),
	html.Div(id='hidden-div2'),
	html.Div(id='hidden-div3'),


	html.Div(children=[
		html.Label('g1 clickDatas'),
		html.Pre(id='g1-click-datas', style=pre_style),
		html.Label('g2 clickDatas'),
		html.Pre(id='g2-click-datas', style=pre_style),
		html.Label('g3 clickDatas'),
		html.Pre(id='g3-click-datas', style=pre_style),
		html.Label('g4 clickDatas'),
		html.Pre(id='g4-click-datas', style=pre_style),
		html.Label('update on click data'),
		html.Pre(id='update-on-click-data', style=pre_style),

		html.Pre(id='my-tmp-pre', style=pre_style),
	], style={'display': 'none'}),


	]) # closing 'app.layout = html.Div(['

#
# callbacks
#

# see: https://gist.github.com/shawkinsl/22a0f4e0bf519330b92b7e99b3cfee8a

@app.callback(Output('my-tmp-pre', 'children'),
			  [Input('g1', 'clickData')],
			  [State('g1-click-datas', 'id'), State('g1-click-datas', 'children')])
def graph_clicked_xxx(click_data, clicked_id, children):
	print('=== graph_clicked_xxx() click_data:', click_data)
	if not children:
		children = []
	if click_data is None:
		return []
	else:
		click_data["time"] = int(datetime.datetime.now().timestamp())
		click_data["id"] = clicked_id
		children.append(json.dumps(click_data) + "\n")
		children = children[-3:]
		return children

for name in graph_names:
	@app.callback(Output('{}-click-datas'.format(name), 'children'),
				  [Input(name, 'selectedData')],
				  [State('{}-click-datas'.format(name), 'id'), State('{}-click-datas'.format(name), 'children')])
	def graph_clicked(click_data, clicked_id, children):
		print('=== graph_clicked() click_data:', click_data)
		if not children:
			children = []
		if click_data is None:
			return []
		else:
			click_data["time"] = int(datetime.datetime.now().timestamp())
			click_data["id"] = clicked_id
			children.append(json.dumps(click_data) + "\n")
			children = children[-3:]
			return children


@app.callback(Output('update-on-click-data', 'children'),
			  [Input("{}-click-datas".format(name), 'children') for name in graph_names])
def determine_last_click(*clickdatas):
	print('=== determine_last_click()')
	most_recent = None
	for clickdata in clickdatas:
		if clickdata:
			last_child = json.loads(clickdata[-1].strip())
			if clickdata and (most_recent is None or int(last_child['time']) > json.loads(most_recent)['time']):
				most_recent = json.dumps(last_child)
	return most_recent



#
# these 4 callbacks are unruly, create a dict to pass to handleGraphCallback()
#

# keep track of the number of clicks on each 'plot <n>'
numClicks = [0, 0, 0, 0]

def handleGraphCallback(graphNumber, n_clicks, update_on_click_data, derived_virtual_selected_rows, showMean, showSDEVID):
	myBrowser.setSelectPoints(update_on_click_data)
	myBrowser.setSelectedFiles(derived_virtual_selected_rows)
	myBrowser.setPlotOptions(showMean) # show mean is from ['', '', ...]
	myBrowser.setShow_sdev_sem(showSDEVID)
	if n_clicks is not None and n_clicks > numClicks[graphNumber]:
		numClicks[graphNumber] = n_clicks
		myBrowser.plotTheseStats(graphNumber)

##
# new
##

inputList = [
	#Input('g1-plot-button','n_clicks'),
	Input('update-on-click-data', 'children'),
	Input('file-list-table', "derived_virtual_selected_rows"),
	Input('showMeanID', 'values'),
	Input('showSDEVID', 'value'),
]

g1_Input = [Input('g1-plot-button','n_clicks')] + inputList
g2_Input = [Input('g2-plot-button','n_clicks')] + inputList
g3_Input = [Input('g3-plot-button','n_clicks')] + inputList
g4_Input = [Input('g4-plot-button','n_clicks')] + inputList

# 1
@app.callback(Output('g1', 'figure'), g1_Input)
def my1(*args):
	graphNumber = 0
	handleGraphCallback(graphNumber, *args)
	return plotButton(graphNumber)
# 2
@app.callback(Output('g2', 'figure'), g2_Input)
def my2(*args):
	graphNumber = 1
	handleGraphCallback(graphNumber, *args)
	return plotButton(graphNumber)
# 3
@app.callback(Output('g3', 'figure'), g3_Input)
def my3(*args):
	graphNumber = 2
	handleGraphCallback(graphNumber, *args)
	return plotButton(graphNumber)
# 4
@app.callback(Output('g4', 'figure'), g4_Input)
def my4(*args):
	graphNumber = 3
	handleGraphCallback(graphNumber, *args)
	return plotButton(graphNumber)


# disable error bars when mean is off
'''
@app.callback(Output('showSDEVID', 'disabled'), [Input('showMeanID', 'values')])
def myMeanCheckbox(values):
	print('myMeanCheckbox() values:', values)
	return not 'showMean' in values
'''

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

	#print('\nmyFileListSelect() rows:', rows)
	print('myFileListSelect() derived_virtual_selected_rows:', derived_virtual_selected_rows)

	myBrowser.setSelectedFiles(derived_virtual_selected_rows)

#
# x/y stat selection
@app.callback(
	dash.dependencies.Output('hidden-div2', 'children'),
	[
	Input('y-datatable', 'selected_rows'),
	Input('x-datatable', 'selected_rows'),
	])
def myTableSelect(y_activeCell, x_activeCell):
	print('myTableSelect() y_activeCell:', y_activeCell, 'x_activeCell:', x_activeCell)
	xSel, ySel = None, None
	if len(y_activeCell) > 0: # is not None:
		yRow = y_activeCell[0]
		#ySel = myStatList[yRow]['label']
		ySel = myStatList[yRow]
		myBrowser.setSelectedStat('y', ySel)
	if len(x_activeCell) > 0: # is not None:
		xRow = x_activeCell[0]
		#xSel = myStatList[xRow]['label']
		xSel = myStatList[xRow]
		myBrowser.setSelectedStat('x', xSel)

# edit condition
@app.callback(
    Output('file-list-table', 'data'),
    [Input('file-list-table', 'data_timestamp')], # data_timestamp is not working ???
    [State('file-list-table', 'data')])
def display_output(data_timestamp, data):
	print('display_output()')
	theRet = []
	for rowIdx, item in enumerate(data):
		#print('   item:', item)
		
		# convert to number
		#item['Condition 1'] = int(item['Condition 1'])
		
		analysisFile = item['Analysis_File']
		condition1 = item['Condition 1']

		#print('   condition1:', condition1)
		
		rowsToChange = myBrowser.df0['Analysis_File'] == analysisFile
		myBrowser.df0.loc[rowsToChange, 'Condition 1'] = condition1
		
		rowsToChange = myBrowser.df['Analysis_File'] == analysisFile
		myBrowser.df.loc[rowsToChange, 'Condition 1'] = condition1
		
		
		theRet.append(item)
	return theRet
	
#
# main
#
if __name__ == '__main__':

	app.run_server(debug=True)
