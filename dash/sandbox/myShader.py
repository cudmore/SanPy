# coding: utf-8

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.plotly as py
import plotly.graph_objs as go
import datashader as ds
import datashader.transfer_functions as tf
import pandas as pd
import numpy as np
import json
import copy
import xarray as xr
from collections import OrderedDict

#######################################################################################################################
# Data generation
#######################################################################################################################

'''
n = 1000000
max_points = 100000

np.random.seed(2)
cols = ['Signal']  # Column name of signal
start = 1456297053  # Start time
end = start + n  # End time

# Generate a fake signal
time = np.linspace(start, end, n)
signal = np.random.normal(0, 0.3, size=n).cumsum() + 50

# Generate many noisy samples from the signal
noise = lambda var, bias, n: np.random.normal(bias, var, n)
data = {c: signal + noise(1, 10 * (np.random.random() - 0.5), n) for c in cols}

# # Pick a few samples and really blow them out
locs = np.random.choice(n, 10)

# print locs
data['Signal'][locs] *= 2
'''

###
###
import sys
sys.path.append("..") # Adds higher directory to python modules path.
from bAnalysisApp import bAnalysis

myFilePath = '../data/19221021.abf' # 300 sec
#myFilePath = '../data/19114001.abf' # 60 sec
ba = bAnalysis.bAnalysis(myFilePath)
ba.getDerivative(medianFilter=5)
ba.spikeDetect(dVthresholdPos=50, medianFilter=5, halfHeights=[20, 50, 80])

myX = ba.abf.sweepX
signal = ba.abf.sweepY

cols = ['Signal']  # Column name of signal
data = {c: signal for c in cols}

start = 0
end = myX[-1]
n = len(myX)
max_points = n
###
###

# # Default plot ranges:
x_range = (start, end)
y_range = (1.2 * signal.min(), 1.2 * signal.max())

# Create a dataframe
data['Time'] = np.linspace(start, end, n)
df = pd.DataFrame(data)

time_start = df['Time'].values[0]
time_end = df['Time'].values[-1]

cvs = ds.Canvas(x_range=x_range, y_range=y_range)

aggs = OrderedDict((c, cvs.line(df, 'Time', c)) for c in cols)
img = tf.shade(aggs['Signal'])

arr = np.array(img)
z = arr.tolist()

# axes
dims = len(z[0]), len(z)

x = np.linspace(x_range[0], x_range[1], dims[0])
y = np.linspace(y_range[0], y_range[1], dims[0])

#
# make a second df2 to hold spike times
'''
					'x': [spike['thresholdSec'] for spike in ba.spikeDict if (spike['thresholdSec'] > x0 and spike['thresholdSec'] < x1)],
					'y': [spike['thresholdVal'] for spike in ba.spikeDict if (spike['thresholdSec'] > x0 and spike['thresholdSec'] < x1)],
'''
signal2 = [spike['thresholdVal'] for spike in ba.spikeDict]
myX2 = [spike['thresholdSec'] for spike in ba.spikeDict]

data2 = {c: signal2 for c in cols}
#start2 = 0
#end2 = myX2[-1]
#n2 = len(myX2)
#max_points2 = n2
data2['Time'] = myX2 #np.linspace(start2, end2, n2)
df2 = pd.DataFrame(data2)

#######################################################################################################################
# Layout
#######################################################################################################################

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', '/static/shader_style.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

fig1 = {
	'data': [{
		'x': x,
		'y': y,
		'z': z,
		'type': 'heatmap',
		'showscale': False,
		'colorscale': [[0, 'rgba(255, 255, 255,0)'], [1, '#a3a7b0']]},
		{
			'x': [spike['thresholdSec'] for spike in ba.spikeDict],
			'y': [spike['thresholdVal'] for spike in ba.spikeDict],
			'mode': 'markers',
		}
		],
	'layout': {
		'margin': {'t': 50, 'b': 20},
		'height': 250,
		'xaxis': {
			'showline': True,
			'zeroline': False,
			'showgrid': False,
			'showticklabels': True,
			'color': '#a3a7b0'
		},
		'yaxis': {
			'fixedrange': True,
			'showline': False,
			'zeroline': False,
			'showgrid': False,
			'showticklabels': False,
			'ticks': '',
			'color': '#a3a7b0'
		},
		'plot_bgcolor': '#23272c',
		'paper_bgcolor': '#23272c'}
}

fig2 = {
	'data': [
		{
			'x': x,
			'y': y,
			'z': z,
			'type': 'heatmap',
			'showscale': False,
			'colorscale': [[0, 'rgba(255, 255, 255,0)'], [1, '#75baf2']]
		}
	],
	'layout': {
		'margin': {'t': 50, 'b': 20},
		'height': 250,
		'xaxis': {
			'fixedrange': True,
			'showline': True,
			'zeroline': False,
			'showgrid': False,
			'showticklabels': True,
			'color': '#a3a7b0'
		},
		'yaxis': {
			'fixedrange': True,
			'showline': False,
			'zeroline': False,
			'showgrid': False,
			'showticklabels': False,
			'ticks': '',
			'color': '#a3a7b0'
		},
		'plot_bgcolor': '#23272c',
		'paper_bgcolor': '#23272c'}
}

app.layout = html.Div([
	html.Div(
		id='header',
		children=[
			html.Div([
				html.H3('Visualize millions of points with datashader and Plotly')
			], className="eight columns"),

			html.Div([
				html.Img(
					id='logo',
					src=app.get_asset_url('dash-logo.png'),
					style={
						'height': '50px',
						'float': 'right'}),
			], className="four columns")
		], className="row"),
	html.Hr(),
	html.Div([
		html.Div([
			html.P('Click and drag on the plot for high-res view of\
			 selected data', id='header-1'),

			#dcc.Loading(id="loading-1", children=[
			dcc.Graph(
				id='graph-1',
				figure=fig1,
				config={
					'doubleClick': 'reset'
				}
			)
			#], type="default"),
			
		], className='twelve columns')
	], className='row'),

	html.Div([
		html.Div([
			html.Div(
				children=[
					html.Strong(
						children=['0'],
						id='header-2-strong'
					),
					html.P(
						children=[' points selected'],
						id='header-2-p'
					),
				],
				id='header-2'
			),
			dcc.Graph(
				id='graph-2',
				figure=fig2
			)
		], className='twelve columns')
	], className='row'),

])


#######################################################################################################################
# Callbacks
#######################################################################################################################

@app.callback(
	[Output('header-2-strong', 'children'),
	 Output('header-2-p', 'children')],
	[Input('graph-1', 'relayoutData')]
)
def selectionRange(selection):
	if selection is not None and 'xaxis.range[0]' in selection and \
			'xaxis.range[1]' in selection:
		x0 = selection['xaxis.range[0]']
		x1 = selection['xaxis.range[1]']
		sub_df = df[(df.Time >= x0) & (df.Time <= x1)]
		num_pts = len(sub_df)
		if num_pts < max_points:
			number = "{:,}".format(abs(int(selection['xaxis.range[1]']) - int(selection['xaxis.range[0]'])))
			number_print = " points selected between {0:,.4} and {1:,.4}". \
				format(selection['xaxis.range[0]'], selection['xaxis.range[1]'])
		else:
			number = "{:,}".format(abs(int(selection['xaxis.range[1]']) - int(selection['xaxis.range[0]'])))
			number_print = " points selected. Select less than {0:}k \
			points to invoke high-res scattergl trace".format(max_points / 1000)
	else:
		number = "0"
		number_print = " points selected"
	return [number, number_print]


@app.callback(
	Output('graph-2', 'figure'),
	[Input('graph-1', 'relayoutData')])
def selectionHighlight(selection):
	new_fig2 = fig2.copy()
	if selection is not None and 'xaxis.range[0]' in selection and \
			'xaxis.range[1]' in selection:
		x0 = selection['xaxis.range[0]']
		x1 = selection['xaxis.range[1]']
		sub_df = df[(df.Time >= x0) & (df.Time <= x1)]
		num_pts = len(sub_df)
		if num_pts < max_points:
			shape = dict(
				type='rect',
				xref='x',
				yref='paper',
				y0=0,
				y1=1,
				x0=x0,
				x1=x1,
				line={
					'width': 0,
				},
				fillcolor='rgba(165, 131, 226, 0.10)'
			)

			new_fig2['layout']['shapes'] = [shape]
		else:
			new_fig2['layout']['shapes'] = []
	else:
		new_fig2['layout']['shapes'] = []
	return new_fig2

@app.callback(
	Output('graph-1', 'figure'),
	[Input('graph-1', 'relayoutData')])
def draw_undecimated_data(selection):
	new_fig1 = fig1.copy()
	if selection is not None and 'xaxis.range[0]' in selection and \
			'xaxis.range[1]' in selection:
		x0 = selection['xaxis.range[0]']
		x1 = selection['xaxis.range[1]']
		
		print('draw_undecimated_data() x0:', x0, 'x1:', x1)
		
		sub_df = df[(df.Time >= x0) & (df.Time <= x1)]
		num_pts = len(sub_df)
		
		sub_df2 = df2[(df2.Time >= x0) & (df2.Time <= x1)]
		num_pts2 = len(sub_df2)
		
		#print('sub_df2:', sub_df2)
		
		if num_pts < max_points:
			high_res_data = [
				dict(
					x=sub_df['Time'],
					y=sub_df['Signal'],
					type='scattergl',
					marker=dict(
						sizemin=1,
						sizemax=30,
						color='#a3a7b0'
					)
				),
				{
					#'x': [spike['thresholdSec'] for spike in ba.spikeDict if (spike['thresholdSec'] > x0 and spike['thresholdSec'] < x1)],
					#'y': [spike['thresholdVal'] for spike in ba.spikeDict if (spike['thresholdSec'] > x0 and spike['thresholdSec'] < x1)],
					'x': sub_df2['Time'],
					'y': sub_df2['Signal'],
					'mode': 'markers',
					#'type': 'scattergl',
				}
				]
			high_res_layout = new_fig1['layout']
			high_res = dict(data=high_res_data, layout=high_res_layout)
		else:
			high_res = fig1.copy()
	else:
		high_res = fig1.copy()
	return high_res


if __name__ == '__main__':
	app.run_server(debug=True)