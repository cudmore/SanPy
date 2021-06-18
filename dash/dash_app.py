'''
pip install dash==0.39.0  # The core dash backend
pip install dash-daq==0.1.0  # DAQ components (newly open-sourced!)
'''

import os, sys, time, collections
import io, base64 # to handle drag and drop of binary abf files
from textwrap import dedent as d

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly import subplots

from pages import fileListPage, scatterPage, uploadpage, detectionPage
import myDashUtils

#from sanpy import *
import sanpy
from sanpy.bAnalysisUtil import statList
statDict = statList

# see: https://codepen.io/chriddyp/pen/bWLwgP
'''
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = 'SanPy Detection'
app.css.append_css({'external_url': 'assets/my.css'})
'''
from app import app
from app import server # needed for heroku

def loadFile(path, name, rowIdx):
	print('app2.loadFile() name:', name, 'rowIdx:', rowIdx)

	global ba

	if rowIdx > len(baList)-1:
		# error
		return

	# already loaded when page was initialized
	ba = baList[rowIdx]

	start = 0
	stop = len(ba.sweepX) - 1
	global subSetOfPnts
	subSetOfPnts = range(start, stop, plotEveryPoint)
	print('  load file subSetOfPnts:', subSetOfPnts)

def myDetect(dvdtThreshold):
	print('app2.myDetect() dvdtThreshold:', dvdtThreshold)
	dDict = ba.getDefaultDetection()
	dDict['dvdtThreshold'] = dvdtThreshold
	ba.spikeDetect(dDict)

myPath = '../data'

# detect spikes
myThreshold = 20
# limit points we are plotting
plotEveryPoint = 10
##
subSetOfPnts = None

global baList
baList = []

#fileList = getFileList(myPath)
dfFileList, baList = myDashUtils.getFileList(myPath) # used to build file list DataTable ('file-list-table')

# load first file in list
loadFirstFile = dfFileList['File Name'][0]
print('loadFirstFile:', loadFirstFile)
loadFile(myPath, loadFirstFile, 0)

myOptionsList = list(statDict.keys())

#tmpData = [{"Idx": idx+1, "stat": myOption} for idx, myOption in enumerate(myOptionsList)]

app.layout = html.Div([

	html.H2(" "),

	html.Div(id='tmpdiv', className='row'),
	html.Div(id='tmpdiv2', className='row'),
	html.Div(id='tmpdivRadio', className='row'),

	fileListPage.getFileListLayout(myPath, dfFileList),

	detectionPage.getDetectionLayout(),

	scatterPage.getScatterPageLayout(statList),

]) # app.layout = html.Div([

def todo_myDataTable(id, xxx):
	dt = dash_table.DataTable(
		id=id,
		fixed_rows={'headers': True},
		columns=[{"name": '', "id": 'Idx'}, {"name": 'X Stat', "id": 'stat'}],
		data=[{"Idx": idx+1, "stat": myOption} for idx, myOption in enumerate(myOptionsList)],
		style_table={
			'maxHeight': '300',
			'overflowY': 'scroll'
		},
		style_cell={'textAlign': 'left'},
		style_header={
			#'backgroundColor': 'ltgray',
			'fontWeight': 'bold'
		},
		style_data_conditional=[{
			'if': {'row_index': 'odd'},
			'backgroundColor': 'rgb(248, 248, 248)'
		}],
		row_selectable='single',
		selected_rows=[0],
	)
	return dt

###
# Callbacks
###

# removed to fix bug in global ba
'''
@app.callback(Output('detect-spinner', 'children'),
	[
	Input('detect-button', 'n_clicks'),
	],
	[State('dvdtThreshold', 'value')])
def detectButton(detectButton, dvdtThreshold):
	print('=== detectButton() dvdtThreshold:', dvdtThreshold)
	ctx = dash.callback_context
	if ctx.triggered:
		triggeredControlId = ctx.triggered[0]['prop_id'].split('.')[0]
	else:
		triggeredControlId = None
	print('  triggeredControlId:', triggeredControlId)

	if triggeredControlId == 'detect-button':
		myDetect(dvdtThreshold)
	#elif triggeredControlId == 'save-button':
	#	print('  todo: save')
	return html.Div(" ")
'''

@app.callback(Output('tmpdiv2', 'children'),
	[
	Input('save-button', 'n_clicks'),
	])
def saveButton(saveButton):
	print('=== saveButton()')
	ctx = dash.callback_context
	if ctx.triggered:
		triggeredControlId = ctx.triggered[0]['prop_id'].split('.')[0]
	else:
		triggeredControlId = None
	print('  triggeredControlId:', triggeredControlId)

	#if triggeredControlId == 'detect-button':
	#	myDetect(dvdtThreshold)
	if triggeredControlId == 'save-button':
		print('  todo: save')

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
	"""
	plot dv/dt and vm

	globals:
		subSetOfPnts
	"""
	print('_regenerateFig() xMin:', xMin, 'xMax::', xMax, 'statlist:', statList)

	startSeconds = time.time()

	lineDict = {
		'color': 'white', # for dark layout
		'width': 0.7,
	}

	#print('	type(subSetOfPnts):', type(subSetOfPnts), len(subSetOfPnts))
	'''
	print('	type(ba.abf.sweepX)', type(ba.abf.sweepX), len(ba.abf.sweepX))
	print('	type(ba.abf.sweepY)', type(ba.abf.sweepY), len(ba.abf.sweepY))
	print('	type(ba.filteredDeriv)', type(ba.filteredDeriv), len(ba.filteredDeriv))
	#print('subSetOfPntsgg:', subSetOfPnts)
	print('	sweepY:', np.min(ba.abf.sweepY), np.max(ba.abf.sweepY))
	print('	filteredDeriv:', np.min(ba.filteredDeriv), np.max(ba.filteredDeriv))
	'''

	doDeriv = 'Derivative' in statList

	try:
		if doDeriv:
			dvdtTrace = go.Scattergl(x=ba.abf.sweepX[subSetOfPnts], y=ba.filteredDeriv[subSetOfPnts],
							line=lineDict, showlegend=False)
		else:
			dvdtTrace = None
		vmTrace = go.Scattergl(x=ba.abf.sweepX[subSetOfPnts], y=ba.abf.sweepY[subSetOfPnts],
							line=lineDict, showlegend=False)
	except (TypeError) as e:
		print('EXCEPTION: _regenerateFig() got TypeError ... reploting WITHOUT subSetOfPnts')
		print(e)
		#print('  subSetOfPnts:', type(subSetOfPnts), subSetOfPnts)
		'''
		print('  len(ba.filteredDeriv):', len(ba.filteredDeriv))
		dvdtTrace = go.Scattergl(x=ba.abf.sweepX, y=ba.filteredDeriv,
							line=lineDict, showlegend=False)
		vmTrace = go.Scattergl(x=ba.abf.sweepX, y=ba.abf.sweepY,
							line=lineDict, showlegend=False)
		'''

	# see: https://stackoverflow.com/questions/43106170/remove-the-this-is-the-format-of-your-plot-grid-in-a-plotly-subplot-in-a-jupy
	if doDeriv:
		numRows = 2
	else:
		numRows = 1

	fig = subplots.make_subplots(rows=numRows, cols=1, shared_xaxes=True, print_grid=False)
	if doDeriv:
		fig.append_trace(dvdtTrace, 1, 1)
		fig.append_trace(vmTrace, 2, 1)
	else:
		fig.append_trace(vmTrace, 1, 1)

	#statList = ['apAmp']
	numSpikes = len(ba.spikeDict)
	if numSpikes > 0 and statList is not None:
		for stat in statList:
			print('   _regenerateFig() stat:"' + stat + '"')
			x, y, = None, None
			if stat == 'AP Amp (mV)':
				x = [spike['peakSec'] for spike in ba.spikeDict]
				y = [spike['peakVal'] for spike in ba.spikeDict]

			elif stat == 'Take Off Potential (mV)':
				x = [spike['thresholdSec'] for spike in ba.spikeDict]
				y = [spike['thresholdVal'] for spike in ba.spikeDict]
			elif doDeriv and stat == 'Take Off Potential (dVdt)':
				x = [spike['thresholdSec'] for spike in ba.spikeDict]
				y = [spike['thresholdVal_dvdt'] for spike in ba.spikeDict]
			else:
				print('  warning: _regenerateFig() did not understand stat:', stat)
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
					# assuming we are showing with doDeriv
					fig.append_trace(thisScatter, 1, 1)
				else:
					if doDeriv:
						fig.append_trace(thisScatter, 2, 1)
					else:
						fig.append_trace(thisScatter, 1, 1)

	# only use xaxis1 because the two plots (dvdt and vm) are linked with the SAME xaxis !!!
	print('  todo: put axis labels back in')
	'''
	fig['layout']['xaxis2'].update(title='Seconds')

	fig['layout']['yaxis1'].update(title='dV/dt') # TODO: get units from bAnalysis
	fig['layout']['yaxis2'].update(title='mV')
	'''

	# only use xaxis1 because the two plots (dvdt and vm) are linked with the SAME xaxis !!!
	# 20210508 PUT THIS BACK IN
	fig['layout']['xaxis1'].update(range= [xMin, xMax])
	fig['layout'].update(margin= {'l': 50, 'b': 10, 't': 10, 'r': 10})
	fig['layout'].update(template='plotly_dark')

	stopSeconds = time.time()
	print('   took', str(stopSeconds-startSeconds), 'seconds')
	return fig

# spike error table
'''
@app.callback(
	[Output("spike-error-table", "data"), Output('spike-error-table', 'columns')],
	[Input("btn", "n_clicks")]
)
def updateTable(n_clicks):
	# 	global ba
	if n_clicks is None:
		return df.values[0:100], columns

	return df.values[100:110], columns[0:3]
'''

# update file list table
@app.callback(
	[
	Output("file-list-table", "data"),
	Output('file-list-table', 'columns')
	],
	[
	Input('upload-data', 'filename'),
	])
def updateFileTable_Callback(filename):
	print('updateFileTable_Callback() filename::', filename)

	return dash.no_update, dash.no_update

#
# combined dvdt and raw data
@app.callback(
	[
	Output('linked-graph', 'figure'),
	Output("spike-error-table", "data"), Output('spike-error-table', 'columns')
	],
	[
	Input('linked-graph', 'relayoutData'),
	Input('file-list-table', 'selected_rows'),
	Input('plot-options-check-list', 'value'),
	Input('spike-error-table', 'selected_rows'),
	Input('upload-data', 'contents'),
	Input('detect-button', 'n_clicks'),
	State('spike-error-table', 'derived_virtual_data'),
	State('upload-data', 'filename'),
	State('upload-data', 'last_modified'),
	State('dvdtThreshold', 'value'),
	])
def linked_graph(relayoutData, selected_rows, values, errorRowSelection,
				list_of_contents, detectButton, errorRowData, list_of_names, list_of_dates,
				dvdtThreshold):
	print('=== linked_graph()')
	print('  relayoutData:', relayoutData)
	print('  selected_rows:', selected_rows)
	print('  values:', values)
	print('  errorRowSelection:', errorRowSelection)
	#print('  errorRowData:', errorRowData)
	#print('	 list_of_contents:', list_of_contents)
	print('  list_of_names:', list_of_names)
	print('  list_of_dates:', list_of_dates)

	ctx = dash.callback_context

	triggeredControlId = None
	if ctx.triggered:
		triggeredControlId = ctx.triggered[0]['prop_id'].split('.')[0]

	print('  triggeredControlId:', triggeredControlId)
	print('  global baList len:', len(baList))

	if relayoutData is None:
		return dash.no_update, dash.no_update, dash.no_update

	xMin = 0
	xMax = ba.abf.sweepX[-1]
	if relayoutData is not None:
		if 'xaxis.range[0]' in relayoutData and 'xaxis.range[1]' in relayoutData:
			xMin = relayoutData['xaxis.range[0]']
			xMax = relayoutData['xaxis.range[1]']
			#print('xMin:', xMin, 'xMax:', xMax)
	print('  xMin:', xMin, 'xMax:', xMax, 'values:', values)

	if triggeredControlId == 'detect-button':
		myDetect(dvdtThreshold)

	elif triggeredControlId=='file-list-table' and selected_rows is not None:
		print('  myFileSelect()', 'activeCell:', selected_rows)
		selRow = selected_rows[0]
		#fileSelection = fileList[selRow]['File Name']
		fileSelection = dfFileList.at[selRow, 'File Name']
		print('   file selection is:', fileSelection)
		print('     XXX LOADING FILE THIS IS WHERE I NEED REDIS !!!!!!!!!!!!!!!!!!!!!!!!!')
		loadFile(myPath, fileSelection, selRow)
	elif triggeredControlId=='upload-data':
		print('  user uploaded an abf:', list_of_names)
		# todo: fix this syntax, really weird !!!
		try:
			#[uploadPage.parse_contents_abf(c, n, d) for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)]
			c = list_of_contents[0]
			n = list_of_names[0]
			d = list_of_dates[0]
			print('  n:', n)
			print('  d:', d)
			parse_contents_abf(c, n, d)
		except:
			print('*** exception in parse_contents_abf():')
			print(sys.exc_info())

	elif triggeredControlId == 'spike-error-table' and errorRowSelection is not None:
		errorRowSelection = errorRowSelection[0]
		print('TODO: select error row:', errorRowSelection)
		seconds = errorRowData[errorRowSelection]['Seconds']
		xMin = seconds - 1
		xMax = seconds + 1

	if relayoutData is None:
		fig = dash.no_update
	else:
		fig = _regenerateFig(xMin, xMax, values)

	# TODO: if we are not switching files but just updating plots overlay, don't do this
	# spike errors table
	dataError = dash.no_update
	columnsError = dash.no_update

	#if triggeredControlId in ['file-list-table', 'upload-data']:
	if triggeredControlId in ['detect-button', 'file-list-table', 'upload-data']:
		print('  grabbing errors')
		dfError = ba.errorReport()
		if dfError is not None:
			dataError =  dfError.to_dict('records')
			columnList = dfError.columns.to_list()
			columnsError = [{'id':x, 'name':x} for x in columnList]
	#print('dataError:', dataError)
	#print('columnsError:', columnsError)

	#
	return fig, dataError, columnsError

def parse_contents_abf(contents, filename, date):
	"""
	parses binary abf file
	"""
	print('app2.parse_contents_abf() filename:', filename)

	content_type, content_string = contents.split(',')

	print('  content_type:', content_type)
	decoded = base64.b64decode(content_string)
	#print('  type(decoded)', type(decoded))
	fileLikeObject = io.BytesIO(decoded)
	#print('  type(fileLikeObject)', type(fileLikeObject))

	#print(len(fileLikeObject.getvalue()))
	#major = pyabf.abfHeader.abfFileFormat(fileLikeObject)
	#print('  pyabf major:', major)

	print('  *** instantiating sanpy.bAnalysis with byte stream')
	try:
		global ba
		ba = sanpy.bAnalysis(byteStream=fileLikeObject)

		global baList
		baList.append(ba)

		#print(ba.abf.headerText)

		# TODO: Add to file list
		# {'File Name':fileName, 'kHz':, kHz, 'Duration (Sec)':durSeconds, 'Number of Sweeps':numberOfSweeps}
		print('  todo: keep track of ba for this file and add to file list')

		# todo: get rid of this weirdness
		start = 0
		stop = len(ba.abf.sweepX) - 1
		print('	stop:', stop)
		print('	plotEveryPoint:', plotEveryPoint)
		global subSetOfPnts
		subSetOfPnts = slice(start, stop, plotEveryPoint)
		#print('  subSetOfPnts:', subSetOfPnts)
	except:
		print('*** exception in app2.parse_contents_abf():')
		print(sys.exc_info())

	return html.Div([
		html.H5(f'Loaded file: {filename}'),
	])

@app.callback(
	Output('life-exp-vs-gdp', 'figure'),
	[
	Input('y-stat-table', 'selected_rows'),
	Input('x-stat-table', 'selected_rows'),
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
		ySel = statDict[ySelHuman]['yStat'] # convert back to backend names
	if x_activeCell is not None:
		xRow = x_activeCell[0]
		xSelHuman = myOptionsList[xRow]
		xSel = statDict[xSelHuman]['yStat'] # convert back to backend names
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
				'size': 10,
				#'color': 'k',
				'opacity': 0.9,
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
			template='plotly_dark',
			hovermode='closest'
		)
	}

if __name__ == '__main__':
	app.run_server(debug=True)
	#app.run_server(debug=True, host='0.0.0.0', port=8000)
