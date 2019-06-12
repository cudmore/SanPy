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
import dash_daq as daq
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go

import dash_bootstrap_components as dbc # dash bootstrap https://github.com/facultyai/dash-bootstrap-components

from bBrowser import bBrowser

print('dash.__version__=', dash.__version__)

myBrowser = bBrowser()
myBrowser.loadFolder()

#print(myBrowser.df0.to_dict('records'))

# removed 20190603
#myStatList = myBrowser.getStatList()

statDict = collections.OrderedDict()
statDict['Take Off Potential (s)'] = 'thresholdSec'
statDict['Take Off Potential (mV)'] = 'thresholdVal'
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

	'''
	yStatHuman = myBrowser.graphPlot[graphNum]['yStat']
	xStatHuman = myBrowser.graphPlot[graphNum]['xStat']
	'''
	graphNumStr = str(graphNum) # I don't like making dict keys as int ???
	yStatHuman = myBrowser.options['graphOptions'][graphNumStr]['yStat']
	xStatHuman = myBrowser.options['graphOptions'][graphNumStr]['xStat']


	# convert human readable cardiac stats back to back end stat name
	yStat = statDict[yStatHuman]
	xStat = statDict[xStatHuman]

	print('bBrowser_app.plotButton() graphNum:', graphNum, 'xStat:', xStat, 'yStat:', yStat)

	returnData = myBrowser.updatePlot(xStatName=xStat, yStatName=yStat)

	# determine min/max so we can expand by 5%
	xRange = []

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
				'column_id': 'Color',
				'filter': '{Index} eq ' + str(rowIdx+1)
			},

			##
			## HERE I NEED TO READ FROM ACTUAL COLOR !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
			##
			#'backgroundColor': myBrowser.plotlyColors[rowIdx],
			'backgroundColor': myBrowser.df0.loc[rowIdx, 'Color'],
			'color': 'white',
		}
		print('      === myStyleDataConditional() set rowIdx:', rowIdx, 'to color:', myBrowser.df0.loc[rowIdx, 'Color'])

		theRet.append(theDict)
	return theRet

###
###
defaultColor = '#000000'

colorPicker = html.Div([
    daq.ColorPicker(
        id='my-color-picker',
        label='Pick A Color',
        value={'hex': defaultColor}
    ),
    html.Div(id='color-picker-output')
])

popover = html.Div(
    [
        html.P(
            #["Click on the word ", html.Span("popover", id="popover-target")]
            # It seems the popover target needs to be a html.Span(), it cannot be a DataTable???
            [html.Span("", id="popover-target")]
        ),
        dbc.Popover(
            [
                #dbc.PopoverHeader("Popover header"),
                #dbc.PopoverBody("Popover body"),
                colorPicker,
                dbc.Button("OK", color="primary", outline=True, size="sm", id='ok-color-button'),
                dbc.Button("Cancel", color="primary", outline=True, size="sm", id='cancel-color-button'),
            ],
            id='popover',
            is_open=False,
            target="popover-target",
            #target="file-list-table",
            delay={'show':100, 'hide':500},
        ),
    ]
)
###
###

myFolderList = myBrowser.makeFolderList() # a string list of full folder paths in /data
myFolderListItems = [] # items for 'my-folder-dropdown' dcc.Dropdown
for folder in myFolderList:
	folderItemDict = {}
	folderItemDict['label'] = folder
	folderItemDict['value'] = folder
	myFolderListItems.append(folderItemDict)

myBody = dbc.Container(
	[
		dbc.Row(
			[
				#html.Div(
				#	dbc.Button("Load Folder", color="primary", outline=False, size="sm", id='load-folder-button'),
				#	style={'padding-left': '20px'}
				#),

				# add some horizontal padding so popover does not cover 'Color' column
				html.Div(
					style={'padding-left': '150px'}
				),

				popover,

				"Select a data folder",

				html.Div(
					dcc.Dropdown(
						id='my-folder-dropdown',
						options=myFolderListItems,
						value=myFolderListItems[0]['value'] # default to first folder, should be /data
					),
					style={'width': '50%'} # this is necessary o/w it gets pinched horizontally?
				),
				html.Div(id='my-folder-dropdown-selection', style={'display': 'none'}),

			]
		),

		html.P(''), # some vertical padding

		dbc.Row(
			[
				dbc.Col(
					[
						#html.H5('File List'),

						dash_table.DataTable(
							id='file-list-table',
							row_selectable='multi',
							# i want to make only certain column cells editable
							columns=[{'name':i, 'id':i, 'editable':True} for i in myBrowser.df0], # big assumption that columns do not change

							# order matter here, we need data then style_data_conditional

							data = myBrowser.df0.to_dict('records'),

							style_data_conditional = myStyleDataConditional(),


							editable = True, # this makes all cells editable
							selected_rows = [0,1],
						),
					])
			]
		),

		html.P(''),

		dbc.Row(
			[
				html.H6('Plot Options'),

				dcc.Checklist(
					id='showMeanID',
					options=[
						{'label': 'Lines', 'value': 'showLines'},
						{'label': 'Markers', 'value': 'showMarkers'},
						{'label': 'Mean', 'value': 'showMean'},
						# get rid of this showMeanLines
						{'label': 'Mean Lines', 'value': 'showMeanLines'},
					], values=['showMarkers', 'showMean', 'showMeanLines'], labelStyle={'padding-left': '20px', 'display': 'inline-block'}
				),
				dbc.Tooltip(
					[dcc.Markdown("""Select the plot options for all 4 plots."""),
					dcc.Markdown("""Lines: Lines between sequential spikes."""),
					dcc.Markdown("""Markers: Plot a marker for each spike."""),
					dcc.Markdown("""Mean: Plot the mean for each file."""),
					dcc.Markdown("""Mean Lines: Connect files that share the same 'Condition 1' with a line."""),
					],
					target="showMeanID",
				),

				# I need another structure in here for show mean lines between matching 'condition 1', 'condition 2', ...
				html.Div('Mean Lines b/w Condition', style={'padding-left': '20px', 'display': 'inline-block'}),
				dcc.Checklist(
					id='showMeanLineID',
					options=[
						{'label': '1', 'value': 'meanLinesCondition1'},
						{'label': '2', 'value': 'meanLinesCondition2'},
						{'label': '3', 'value': 'meanLinesCondition3'},
					], values=['meanLinesCondition1', 'meanLinesCondition2', 'meanLinesCondition3'], labelStyle={'padding-left': '20px', 'display': 'inline-block'}
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
				dbc.Tooltip([
					dcc.Markdown("""Select the type of error bars."""),
					dcc.Markdown("""None: No error bars."""),
					dcc.Markdown("""SEM: Standard Error of the Mean."""),
					dcc.Markdown("""SDEV: Standard Deviation."""),
					],
					target="showSDEVID",
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
						dbc.Tooltip(
							"Select both an X-Stat and Y-Stat, then use this button to plot those stats.",
							target="g1-plot-button",
						),
						dcc.Graph(
							id='g1',
							figure=plotButton(0),
						),

						dbc.Button("Plot 3", color="primary", outline=True, size="sm", id='g3-plot-button'),
						dcc.Graph(
							id='g3',
							figure=plotButton(2),
						),
						dbc.Tooltip(
							"Select both an X-Stat and Y-Stat, then use this button to plot those stats.",
							target="g3-plot-button",
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
	html.Div(id='hidden-div-color'),
	html.Div(id='hidden-div2'),
	html.Div(id='hidden-div3'),
	html.Div(id='hidden-div4'),


	html.Div(id='this-is-fucking-stupid'),

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

g_popover_ok_n_clicks = 0
g_popover_cancel_n_clicks = 0

#
# analysis file selection
@app.callback(
	Output('hidden-div', 'children'),
	[Input('file-list-table', "derived_virtual_data"),
	 Input('file-list-table', "derived_virtual_selected_rows"),
	 ])
def myFileListSelect(rows, derived_virtual_selected_rows):
	"""
	rows: all the rows in the table ???
	derived_virtual_selected_rows: list of int of selected rows (rows that are checked)
	"""

	#print('\nmyFileListSelect() rows:', rows)
	#print('myFileListSelect() derived_virtual_selected_rows:', derived_virtual_selected_rows)

	myBrowser.setSelectedFiles(derived_virtual_selected_rows)


updateColorDict = None #{'row': None, 'color': None,}

# on click of a file in the color column
# show a color picker
@app.callback(
    Output('popover', 'is_open'),
	[
	Input('file-list-table', 'selected_cells'),
	Input('ok-color-button', 'n_clicks'),
	Input('cancel-color-button', 'n_clicks'),
	],
	[
	State('popover', "is_open"),
	State('my-color-picker', 'value'),
	])
def myFileListSelectColor(selected_cells, ok_n_clicks, cancel_n_clicks, is_open, colorValue):
	print('\n')
	print('************* myFileListSelectColor() selected_cells:', selected_cells)
	print('   selected_cells:', selected_cells)
	print('   ok_n_clicks:', ok_n_clicks)
	print('   cancel_n_clicks:', cancel_n_clicks)
	print('   is_open:', is_open)
	print('   colorValue:', colorValue)

	global g_popover_ok_n_clicks
	global g_popover_cancel_n_clicks
	global updateColorDict

	print('   g_popover_ok_n_clicks:', g_popover_ok_n_clicks)
	print('   g_popover_cancel_n_clicks:', g_popover_cancel_n_clicks)
	print('   updateColorDict:', updateColorDict)

	theRet = is_open

	if selected_cells is not None:
		selected_cells = selected_cells[0]
		selectedRow = selected_cells['row']
		colName = selected_cells['column_id']

		if colName == 'Color':
			print('   myFileListSelectColor() colName:', colName)
			theRet = (is_open is None) or (not is_open)

		if ok_n_clicks is not None and ok_n_clicks > g_popover_ok_n_clicks: #or n_clicks:
			print('   -->> myFileListSelectColor() OK clicked new color:', colorValue)
			g_popover_ok_n_clicks = ok_n_clicks
			updateColorDict = {}
			updateColorDict['row'] = selectedRow
			updateColorDict['color'] = colorValue['hex']
			theRet = False

		if cancel_n_clicks is not None and cancel_n_clicks > g_popover_cancel_n_clicks: #or n_clicks:
			print('   -->> myFileListSelectColor() CANCEL clicked')
			g_popover_cancel_n_clicks = cancel_n_clicks
			updateColorDict = None
			theRet = False
		print('   myFileListSelectColor() return theRet:', theRet)
		return theRet
###
###

ok_n_clicks2 = 0

@app.callback(
	Output('this-is-fucking-stupid', 'children'),
	[
	Input('ok-color-button', 'n_clicks'),
	],
	[
	State('my-color-picker', 'value'),
	State('file-list-table', 'selected_cells'),
	])
def thisIsFuckingStupid(ok_Button_n_clicks2, colorPickerValue, selected_cells):
	'''
	print('\n************** thisIsFuckingStupid()')
	print('   ok_Button_n_clicks2:', ok_Button_n_clicks2)
	print('   colorPickerValue:', colorPickerValue) # {'hex': '#e80e0e', 'rgb': {'r': 232, 'g': 14, 'b': 14, 'a': 1}}
	print('   selected_cells:', selected_cells) # a list of [{'row': 1, 'column': 1, 'column_id': 'Color'}]
	'''

	global ok_n_clicks2

	# my temptation here is to start using globals outside the purpose of handling dash callbacks!!!!!!!

	if (ok_Button_n_clicks2 is not None) and (ok_Button_n_clicks2 > ok_n_clicks2):
		ok_n_clicks2 = ok_Button_n_clicks2

		selectedRow = selected_cells[0]['row']
		selectedColor = colorPickerValue['hex']

		global updateColorDict
		updateColorDict = {}
		updateColorDict['row'] = selectedRow
		updateColorDict['color'] = selectedColor

		theRet = json.dumps(updateColorDict)

		#return 'this-is-fucking-stupid ' + str(ok_n_clicks2)
		return theRet
	else:
		return ''

# data folder dropdown 'my-folder-dropdown'
@app.callback(
	[
	Output('my-folder-dropdown-selection', 'children'),
	],
	[
	Input('my-folder-dropdown', 'value'),
	],
	)
def myFolderDropdown(value):
	print('myFolderDropdown()')
	print('   value:', value)

	if value is not None:
		# todo: get this assignment out of here !!!!
		myBrowser.path = value
		myBrowser.loadFolder()

	return [value]

###
# I want to also return required changes to style_data_conditional
# As of dash 3.9 we can have multiple Output() !!!!!!!!!!!!!!!
#
# edit condition

currentFolder = myBrowser.path

@app.callback(
	[
	Output('file-list-table', 'data'),
	Output('file-list-table', 'style_data_conditional'),
	# this is a stretch
	#Output('this-is-fucking-stupid', 'children'),
	],
	[
	Input('file-list-table', 'data_timestamp'),
	Input('this-is-fucking-stupid', 'children'),
	Input('my-folder-dropdown-selection', 'children'),
	],
	[
	State('file-list-table', 'data'),
	])
def edit_file_list_table(data_timestamp, this_is_fucking_stupid_children, folderDropdownValue, data):
	print('edit_file_list_table()')
	print('   data_timestamp:', data_timestamp)
	print('   this_is_fucking_stupid_children:', this_is_fucking_stupid_children)
	print('   folderDropdownValue:', folderDropdownValue)
	'''
	print('   INCOMING data:')
	for item in data:
		print('   ', item)
	'''

	theRet = []

	global currentFolder # todo: get rid of this global and store it in a div !!!
	if (folderDropdownValue is not None) and folderDropdownValue != currentFolder:
		# need to refresh all values in table

		currentFolder = folderDropdownValue

		print('edit_file_list_table() is switching to data folder:', currentFolder)
		# switching incoming 'data' to new folder
		data = myBrowser.df0.to_dict('records'),
		# todo: fix this
		data = data[0]
		'''
		print('   SWAPPED data:')
		print('data:', data)
		for item in data:
			print('   ', item)
		print('\n')
		'''

	# this_is_fucking_stupid_children will be a string with a dictionary like
	# {'row': 1, 'color': '#aabbcc'}
	stupidDict = None
	if this_is_fucking_stupid_children:
		print('\n\tthis_is_fucking_stupid_children:', this_is_fucking_stupid_children, '\n')
		stupidDict = json.loads(this_is_fucking_stupid_children)

	if data is None:
		theRet = data
	else:

		for rowIdx, item in enumerate(data):
			#print('   item:', item)

			# convert to number
			#item['Condition 1'] = int(item['Condition 1'])

			analysisFile = item['Analysis File']
			condition1 = item['Condition 1']
			condition2 = item['Condition 2']
			condition3 = item['Condition 3']
			theColor = item['Color']

			#print('   condition1:', condition1)

			rowsToChange = myBrowser.df0['Analysis File'] == analysisFile
			myBrowser.df0.loc[rowsToChange, 'Condition 1'] = condition1
			myBrowser.df0.loc[rowsToChange, 'Condition 2'] = condition2
			myBrowser.df0.loc[rowsToChange, 'Condition 3'] = condition3
			myBrowser.df0.loc[rowsToChange, 'Color'] = theColor

			rowsToChange = myBrowser.df['Analysis File'] == analysisFile
			myBrowser.df.loc[rowsToChange, 'Condition 1'] = condition1
			myBrowser.df.loc[rowsToChange, 'Condition 2'] = condition2
			myBrowser.df.loc[rowsToChange, 'Condition 3'] = condition3

			'''
			print('*** updateColorDict:', updateColorDict)
			if updateColorDict is not None:
				pass
			'''

			if (stupidDict is not None) and rowIdx == stupidDict['row']:
				print('*** ASSIGNING NEW COLOR')
				newColor = stupidDict['color']
				#print('ROW INDEX IS SAME AS STUPID DICT, SET THE COLOR TO:', newColor, '!!!!!!!!!!!!')
				rowsToChange = myBrowser.df0['Analysis File'] == analysisFile
				#print('rowsToChange:', rowsToChange)
				myBrowser.df0.loc[rowsToChange, 'Color'] = newColor

				# need to actually mody the item here
				item['Color'] = newColor

			theRet.append(item)

		myBrowser.folderOptions_Save()

	style_data_conditional = myStyleDataConditional()

	return theRet, style_data_conditional#, ('')

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


#
# main
#
if __name__ == '__main__':

	app.run_server(debug=True)
