'''
pip install dash==0.39.0  # The core dash backend
pip install dash-daq==0.1.0  # DAQ components (newly open-sourced!)
'''

import os, time, collections
from textwrap import dedent as d

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table

import pandas as pd
import plotly.graph_objs as go
from plotly import tools

##
# bAnalysis
import sys
sys.path.append("..") # Adds higher directory to python modules path.
from bAnalysisApp import bAnalysis

myPath = '../data'

# detect spikes
myThreshold = 100
myMedianFilter = 3
halfHeights = [20, 50, 80]

plotEveryPoint = 10
##

def loadFile(name):
	filePath = os.path.join(myPath, name)
	global ba
	ba = bAnalysis.bAnalysis(filePath)
	ba.getDerivative(medianFilter=5)
	ba.spikeDetect(dVthresholdPos=myThreshold, medianFilter=myMedianFilter, halfHeights=halfHeights)
	start = 0
	stop = len(ba.abf.sweepX) - 1
	global subSetOfPnts
	subSetOfPnts = range(start, stop, plotEveryPoint)

def myDetect(dvdtThreshold):
	ba.spikeDetect(dVthresholdPos=dvdtThreshold, medianFilter=myMedianFilter, halfHeights=halfHeights)

myFile = '19114001.abf' # SMALL @ 60 sec
#myFile = '19221021.abf' # BIG @ 300 sec
loadFile(myFile)

#
# get a list of abf files
def getFileList(path):
	retFileList = []
	useExtension = '.abf'
	videoFileIdx = 0

	fileDict = {}
	fileDict['File Name'] = ''
	#fileDict['path'] = ''
	fileDict['kHz'] = ''
	fileDict['Duration (Sec)'] = ''
	fileDict['Number of Sweeps'] = ''
	for file in os.listdir(path):
		if file.startswith('.'):
			continue
		if file.endswith(useExtension):
			fullPath = os.path.join(path, file)

			fileDict = {} # WOW, I need this here !!!!!!!!
			fileDict['File Name'] = file
			#fileDict['path'] = fullPath

			tmp_ba = bAnalysis.bAnalysis(file=fullPath)
			pntsPerMS = tmp_ba.dataPointsPerMs
			numSweeps = len(tmp_ba.sweepList)
			durationSec = max(tmp_ba.abf.sweepX)

			fileDict['kHz'] = pntsPerMS
			fileDict['Duration (Sec)'] = int(round(durationSec))
			fileDict['Number of Sweeps'] = numSweeps


			retFileList.append(fileDict)
			videoFileIdx += 1
	if len(retFileList) == 0:
		retFileList.append(fileDict)
	return retFileList

path = '../data'
fileList = getFileList(path)

#
# a list of key names in ba.spikeDict
"""
skipKeys = ['file', 'spikeNumber', 'numError', 'errors', 'dVthreshold', 'medianFilter', 'halfHeights']
myOptionsList = []
mySpikeNumber = 0
for key,value in ba.spikeDict[mySpikeNumber].items():
	#print(key, value)
	if key in skipKeys:
		continue
	optionsDict = {
		'label': key,
		'value': key
	}
	myOptionsList.append(optionsDict)
"""

###
###
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
###
###

myOptionsList = list(statDict.keys())
#print('\n\nmyOptionsList:', myOptionsList)

tmpData=[{"Idx": idx+1, "stat": myOption} for idx, myOption in enumerate(myOptionsList)]
#for tmpDataRow in enumerate(tmpData):
#	print('   ', tmpDataRow)
	
# see: https://codepen.io/chriddyp/pen/bWLwgP
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, static_folder='static')
app.css.append_css({'external_url': 'static/my.css'})

app.layout = html.Div([


	html.Div([

		html.Div([
			html.Button(id='load-folder-button', children='Load Folder', className='button-primary'),
			html.Label('File: ' + os.path.join(myPath, myFile)),
		], className='two columns'),

		html.Div([
		dash_table.DataTable(
			id='file-datatable',
			#columns=[{"name": 'Idx', "id": 'Idx'}, {"name": 'Stat', "id": 'stat'}],
			columns = [{'name': key, 'id': key} for key in fileList[0]],
			data=[oneFile for idx, oneFile in enumerate(fileList)],
			style_table={
				'maxWidth': '1000',
				'maxHeight': '300',
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
			selected_rows=[2],
		),
		], className='ten columns'),
		# style={'width': '49%', 'display': 'inline-block', 'vertical-align': 'middle'}),
	], className='row'),

	html.H2(" "),
	
	html.Div(id='tmpdiv', className='row'),
	html.Div(id='tmpdiv2', className='row'),
	html.Div(id='tmpdivRadio', className='row'),

	html.Div([
		html.Div([
				html.Button(id='detect-button', children='Detect', className='button-primary'),
					
				html.Div([
					dcc.Input(id='dvdtThreshold', type='number', value=50, style={'width': 65}),
				
					" dV/dt",
				], style={'display': 'inline-block'}), 
				
				html.H5("Plot"),
				
				dcc.Checklist(
					id='plot-radio-buttons',
					options=[
						{'label': 'Take Off Potential (dVdt)', 'value': 'Take Off Potential (dVdt)'},
						{'label': 'AP Amp (mV)', 'value': 'AP Amp (mV)'},
						{'label': 'Take Off Potential (mV)', 'value': 'Take Off Potential (mV)'},
					],
					values=[]
				),

				html.H2(" "),
				
				html.Button(id='save-button', children='Save', className='button-primary'),
		], className='two columns'),

		# one dcc.Graph for both dvdt and vm
		html.Div([
			dcc.Graph(style={'height': '600px'}, id='linked-graph'),
		], className='ten columns'),
	], className='row'),

	html.Div([ # row
	html.Div([

		html.Div([
		dash_table.DataTable(
			id='x-datatable',
			columns=[{"name": '', "id": 'Idx'}, {"name": 'X Stat', "id": 'stat'}],
			data=[{"Idx": idx+1, "stat": myOption} for idx, myOption in enumerate(myOptionsList)],
			style_table={
				'maxHeight': '300',
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
		], style={'display': 'inline-block', 'vertical-align': 'middle'}),

		html.Div([
		dash_table.DataTable(
			id='y-datatable',
			columns=[{"name": '', "id": 'Idx'}, {"name": 'Y Stat', "id": 'stat'}],
			data=[{"Idx": idx+1, "stat": myOption} for idx, myOption in enumerate(myOptionsList)],
			style_table={
				'maxHeight': '400',
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
		], style={'display': 'inline-block', 'vertical-align': 'middle'}),

	], className='six columns'),

	html.Div([
		dcc.Graph(id='life-exp-vs-gdp')
	], className='six columns'),
	
	], className='row'),
	
]) # app.layout = html.Div([

###
# Callbacks
###

@app.callback(Output('tmpdiv2', 'children'),
	[Input('detect-button', 'n_clicks')], [State('dvdtThreshold', 'value')])
def detectButton(n_clicks, dvdtThreshold):
	print('=== detectButton() dvdtThreshold:', dvdtThreshold)
	myDetect(dvdtThreshold)

'''
@app.callback(
	Output('tmpdivRadio', 'children'),
	[Input('plot-radio-buttons', 'values')
	])
def plotRadioButtons(values):
	print('=== plotRadioButtons values:', values)
	xMin = 0
	xMax = 60
	#if values == 'apAmp':
	if 1:
		_regenerateFig(xMin, xMax, statList=values)
'''

# see: https://stackoverflow.com/questions/46075960/live-updating-only-the-data-in-dash-plotly
# idea is to make fig in main code, then just makea a list [] of traces and return that as 'return {'data': traces}'
def _regenerateFig(xMin, xMax, statList=None):
	print('_regenerateFig() xMin:', xMin, 'xMax::', xMax, 'statlist:', statList)

	startSeconds = time.time()

	dvdtTrace = go.Scattergl(x=ba.abf.sweepX[subSetOfPnts], y=ba.filteredDeriv[subSetOfPnts], line=dict(color='black'), showlegend=False)
	vmTrace = go.Scattergl(x=ba.abf.sweepX[subSetOfPnts], y=ba.abf.sweepY[subSetOfPnts], line=dict(color='black'), showlegend=False)

	# see: https://stackoverflow.com/questions/43106170/remove-the-this-is-the-format-of-your-plot-grid-in-a-plotly-subplot-in-a-jupy
	fig = tools.make_subplots(rows=2, cols=1, shared_xaxes=True, print_grid=False)
	fig.append_trace(dvdtTrace, 1, 1)
	fig.append_trace(vmTrace, 2, 1)


	#statList = ['apAmp']
	if statList is not None:
		for stat in statList:
			print('   _regenerateFig() stat:"' + stat + '"')
			x, y, = None, None
			if stat == 'AP Amp (mV)':
				x = [spike['peakSec'] for spike in ba.spikeDict]
				y = [spike['peakVal'] for spike in ba.spikeDict]

			if stat == 'Take Off Potential (mV)':
				x = [spike['thresholdSec'] for spike in ba.spikeDict]
				y = [spike['thresholdVal'] for spike in ba.spikeDict]
			if stat == 'Take Off Potential (dVdt)':
				x = [spike['thresholdSec'] for spike in ba.spikeDict]
				y = [spike['thresholdVal_dvdt'] for spike in ba.spikeDict]

			'''
			print('x:', x)
			print('y:', y)
			'''
			if x is not None and y is not None:
				thisScatter = go.Scattergl(
					x=x,
					y=y,
					mode='markers',
					marker = dict(
						size = 10,
						color = 'rgba(225, 0, 0, .8)',
						#line = dict(width = 2, color = 'rgb(0, 0, 0)'),
						),
					showlegend=False)
				# how do I append this into the plot????
				#print('   appending thisScatter')
				if stat == 'Take Off Potential (dVdt)':
					fig.append_trace(thisScatter, 1, 1)
				else:
					fig.append_trace(thisScatter, 2, 1)

	# only use xaxis1 because the two plots (dvdt and vm) are linked with the SAME xaxis !!!
	fig['layout']['xaxis1'].update(title='Seconds')

	fig['layout']['yaxis1'].update(title='dV/dt')
	fig['layout']['yaxis2'].update(title='mV')

	# only use xaxis1 because the two plots (dvdt and vm) are linked with the SAME xaxis !!!
	fig['layout']['xaxis1'].update(range= [xMin, xMax])
	fig['layout'].update(margin= {'l': 50, 'b': 40, 't': 10, 'r': 10})

	stopSeconds = time.time()
	print('   took', str(stopSeconds-startSeconds), 'seconds')
	return fig

#
# combined dvdt and raw data
@app.callback(
	Output('linked-graph', 'figure'),
	[Input('linked-graph', 'relayoutData'),
	Input('plot-radio-buttons', 'values'),
	])
def linked_graph(relayoutData, values):
	xMin = 0
	xMax = ba.abf.sweepX[-1]
	if relayoutData is not None:
		if 'xaxis.range[0]' in relayoutData and 'xaxis.range[1]' in relayoutData:
			xMin = relayoutData['xaxis.range[0]']
			xMax = relayoutData['xaxis.range[1]']
			#print('xMin:', xMin, 'xMax:', xMax)
	print('=== linked_graph() xMin:', xMin, 'xMax:', xMax, 'values:', values)

	'''
	dvdtTrace = go.Scatter(x=ba.abf.sweepX[subSetOfPnts], y=ba.filteredDeriv[subSetOfPnts], showlegend=False)
	vmTrace = go.Scatter(x=ba.abf.sweepX[subSetOfPnts], y=ba.abf.sweepY[subSetOfPnts], showlegend=False)

	# see: https://stackoverflow.com/questions/43106170/remove-the-this-is-the-format-of-your-plot-grid-in-a-plotly-subplot-in-a-jupy
	fig = tools.make_subplots(rows=2, cols=1, shared_xaxes=True, print_grid=False)
	fig.append_trace(dvdtTrace, 1, 1)
	fig.append_trace(vmTrace, 2, 1)

	# only use xaxis1 because the two plots (dvdt and vm) are linked with the SAME xaxis !!!
	fig['layout']['xaxis1'].update(title='Seconds')

	fig['layout']['yaxis1'].update(title='dV/dt')
	fig['layout']['yaxis2'].update(title='mV')

	# only use xaxis1 because the two plots (dvdt and vm) are linked with the SAME xaxis !!!
	fig['layout']['xaxis1'].update(range= [xMin, xMax])
	fig['layout'].update(margin= {'l': 100, 'b': 40, 't': 10, 'r': 10})
	'''

	fig = _regenerateFig(xMin, xMax, values)
	return fig

#
# selecting a file
@app.callback(
	Output('tmpdiv', 'children'),
	[
	Input('file-datatable', 'selected_rows'),
	])
def myFileSelect(activeCell):
	#print('myTableSelect()')
	if activeCell is not None:
		print('myFileSelect()', 'activeCell:', activeCell)
		selRow = activeCell[0]
		fileSelection = fileList[selRow]['File Name']
		print('   file selection is:', fileSelection)
		print('   XXX LOADING FILE THIS IS WHERE I NEED REDIS !!!!!!!!!!!!!!!!!!!!!!!!!')
		loadFile(fileSelection)
#
# selecting a stat in table
#['active_cell', 'columns', 'locale_format', 'content_style', 'css', 'data', 'data_previous', 'data_timestamp', 'editable', 'end_cell', 'id', 'is_focused', 'merge_duplicate_headers', 'n_fixed_columns', 'n_fixed_rows', 'row_deletable', 'row_selectable', 'selected_cells', 'selected_rows', 'start_cell', 'style_as_list_view', 'pagination_mode', 'pagination_settings', 'navigation', 'column_conditional_dropdowns', 'column_static_dropdown', 'column_static_tooltip', 'column_conditional_tooltips', 'tooltips', 'tooltip_delay', 'tooltip_duration', 'filtering', 'filtering_settings', 'filtering_type', 'filtering_types', 'sorting', 'sorting_type', 'sorting_settings', 'sorting_treat_empty_string_as_none', 'style_table', 'style_cell', 'style_data', 'style_filter', 'style_header', 'style_cell_conditional', 'style_data_conditional', 'style_filter_conditional', 'style_header_conditional', 'virtualization', 'derived_viewport_data', 'derived_viewport_indices', 'derived_viewport_selected_rows', 'derived_virtual_data', 'derived_virtual_indices', 'derived_virtual_selected_rows', 'dropdown_properties']
@app.callback(
	Output('life-exp-vs-gdp', 'figure'),
	[
	Input('y-datatable', 'selected_rows'),
	Input('x-datatable', 'selected_rows'),
	])
def myTableSelect(y_activeCell, x_activeCell):
	"""
	y_activeCell: {'row': 1, 'column': 1, 'column_id': 'stat'}
	x_activeCell: {'row': 3, 'column': 1, 'column_id': 'stat'}
	"""
	print('myTableSelect()')
	print('   y_activeCell:', y_activeCell)
	print('   x_activeCell:', x_activeCell)
	xSel, ySel = None, None
	if y_activeCell is not None:
		yRow = y_activeCell[0]
		ySelHuman = myOptionsList[yRow] # human readable
		ySel = statDict[ySelHuman] # convert back to backend names
	if x_activeCell is not None:
		xRow = x_activeCell[0]
		xSelHuman = myOptionsList[xRow]
		xSel = statDict[xSelHuman] # convert back to backend names
	print('myTableSelect ySel:', ySel, 'xSrl:', xSel)
	xaxis_type = 'Linear'
	yaxis_type = 'Linear'
	if xSel is not None and ySel is not None:
		x = [spike[xSel] for spike in ba.spikeDict]
		y = [spike[ySel] for spike in ba.spikeDict]
	else:
		x = []
		y = []

	return {
		'data': [go.Scatter(
			x=x, #dff[dff['Indicator Name'] == xaxis_column_name]['Value'],
			y=y, #dff[dff['Indicator Name'] == yaxis_column_name]['Value'],
			mode='markers',
			marker={
				'size': 15,
				'opacity': 0.5,
				'line': {'width': 0.5, 'color': 'white'}
			}
		)],
		'layout': go.Layout(
			xaxis={
				'title': xSelHuman,
				'type': 'linear' if xaxis_type == 'Linear' else 'log'
			},
			yaxis={
				'title': ySelHuman,
				'type': 'linear' if yaxis_type == 'Linear' else 'log'
			},
			margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
			hovermode='closest'
		)
	}

if __name__ == '__main__':
	app.run_server(debug=True, host='0.0.0.0', port=8000)
