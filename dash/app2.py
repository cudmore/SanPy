'''
pip install dash==0.39.0  # The core dash backend
pip install dash-daq==0.1.0  # DAQ components (newly open-sourced!)
'''

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import pandas as pd
import plotly.graph_objs as go

##
# bAnalysis
import sys
sys.path.append("..") # Adds higher directory to python modules path.
from bAnalysisApp import bAnalysis

myFile = '../data/19114001.abf'
ba = bAnalysis.bAnalysis(myFile)

# detect spikes
myThreshold = 100
myMedianFilter = 3
halfHeights = [20, 50, 80]
ba.spikeDetect(dVthresholdPos=myThreshold, medianFilter=myMedianFilter, halfHeights=halfHeights)

plotEveryPoint = 10
start = 0
stop = len(ba.abf.sweepX) - 1
subSetOfPnts = range(start, stop, plotEveryPoint)
##

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# a list of key names in ba.spikeDict
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

app.layout = html.Div([
	html.Label('File: ' + myFile),

	html.Button(id='plot-button', children='Plot'),
	
	dcc.Graph(style={'height': '300px'}, id='dvdt-graph'),
	dcc.Graph(style={'height': '300px'}, id='raw-graph'),

	html.Div([
		html.Label('Y'),
		dcc.Dropdown(
			id='yaxis-column',
			options=myOptionsList,
			value='thresholdVal'
		),
	], style={'width': '48%', 'display': 'inline-block'}),

	html.Div([
		html.Label('X'),
		dcc.Dropdown(
			id='xaxis-column',
			options=myOptionsList,
			value='peakSec'
		),
	], style={'width': '48%', 'display': 'inline-block'}),


	dcc.Graph(style={'height': '300px'}, id='life-exp-vs-gdp')
])

#
# dvdt plot
@app.callback(
	Output('dvdt-graph', 'figure'),
	[Input('plot-button','id'),
	Input('plot-button', 'n_clicks'),
	Input('dvdt-graph', 'relayoutData')
	])
def dvdt_plot_callback(id, n_clicks, relayoutData):
	print('dvdt_plot_callback id:', id, 'relayoutData:', relayoutData)
	# relayoutData: {'autosize': True}
	xMin = 0
	xMax = ba.abf.sweepX[-1]
	if relayoutData is not None:
		if 'xaxis.range[0]' in relayoutData and 'xaxis.range[1]' in relayoutData:
			xMin = relayoutData['xaxis.range[0]']
			xMax = relayoutData['xaxis.range[1]']
			#print('xMin:', xMin, 'xMax:', xMax)
	print('   xMin:', xMin, 'xMax:', xMax)
	
	return {
		'data': [go.Scatter(
			x=ba.abf.sweepX[subSetOfPnts],
			y=ba.filteredDeriv[subSetOfPnts],
			text='???', #dff[dff['Indicator Name'] == yaxis_column_name]['Country Name'],
			mode='lines',
			marker={
				'size': 15,
				'opacity': 0.5,
				'line': {'width': 0.5, 'color': 'white'}
			}
		)],
		'layout': go.Layout(
			xaxis={
				'title': 'Time (sec)',
				'type': 'linear',
				'range': [xMin, xMax]
			},
			yaxis={
				'title': 'dV/dt',
				'type': 'linear'
			},
			margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
			hovermode='closest',
		)
	}
	
#
# raw plot
@app.callback(
	Output('raw-graph', 'figure'),
	[Input('plot-button','id'),
	Input('plot-button', 'n_clicks'),
	Input('raw-graph', 'relayoutData')
	])
def raw_plot_callback(id, n_clicks, relayoutData):
	print('raw_plot_callback id:', id)
	xMin = 0
	xMax = ba.abf.sweepX[-1]
	if relayoutData is not None:
		if 'xaxis.range[0]' in relayoutData and 'xaxis.range[1]' in relayoutData:
			xMin = relayoutData['xaxis.range[0]']
			xMax = relayoutData['xaxis.range[1]']
			#print('xMin:', xMin, 'xMax:', xMax)
	print('   xMin:', xMin, 'xMax:', xMax)
	return {
		'data': [go.Scatter(
			x=ba.abf.sweepX[subSetOfPnts], #dff[dff['Indicator Name'] == xaxis_column_name]['Value'],
			y=ba.abf.sweepY[subSetOfPnts], #dff[dff['Indicator Name'] == yaxis_column_name]['Value'],
			text='???', #dff[dff['Indicator Name'] == yaxis_column_name]['Country Name'],
			mode='lines',
			marker={
				'size': 15,
				'opacity': 0.5,
				'line': {'width': 0.5, 'color': 'white'}
			}
		)],
		'layout': go.Layout(
			xaxis={
				'title': 'Time (sec)',
				'type': 'linear',
				'range': [xMin, xMax]
			},
			yaxis={
				'title': 'dV/dt',
				'type': 'linear'
			},
			margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
			hovermode='closest'
		)
	}
	
#
# stat plot
@app.callback(
	Output('life-exp-vs-gdp', 'figure'),
	[Input('xaxis-column', 'value'),
	 Input('yaxis-column', 'value')])
def update_graph(xaxis_column_name, yaxis_column_name):
	print('update_graph()')
	print('   xaxis_column_name:', xaxis_column_name)
	print('   yaxis_column_name:', yaxis_column_name)
	xaxis_type = 'Linear'
	yaxis_type = 'Linear'
	x = [spike[xaxis_column_name] for spike in ba.spikeDict]
	y = [spike[yaxis_column_name] for spike in ba.spikeDict]

	#dff = df[df['Year'] == year_value]

	return {
		'data': [go.Scatter(
			x=x, #dff[dff['Indicator Name'] == xaxis_column_name]['Value'],
			y=y, #dff[dff['Indicator Name'] == yaxis_column_name]['Value'],
			text='???', #dff[dff['Indicator Name'] == yaxis_column_name]['Country Name'],
			mode='markers',
			marker={
				'size': 15,
				'opacity': 0.5,
				'line': {'width': 0.5, 'color': 'white'}
			}
		)],
		'layout': go.Layout(
			xaxis={
				'title': xaxis_column_name,
				'type': 'linear' if xaxis_type == 'Linear' else 'log'
			},
			yaxis={
				'title': yaxis_column_name,
				'type': 'linear' if yaxis_type == 'Linear' else 'log'
			},
			margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
			hovermode='closest'
		)
	}

if __name__ == '__main__':
	app.run_server(debug=True)
