'''
Author: RObert Cudmore
Date: 20190518

Purpose:
   Create a web based data browser of all bAnalysis files in a folder
'''

import os, datetime, json, collections

import pandas as pd

from itertools import chain

import dash
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go

import dash_bootstrap_components as dbc # dash bootstrap https://github.com/facultyai/dash-bootstrap-components

import plotly.colors
print('plotly.colors.DEFAULT_PLOTLY_COLORS:', plotly.colors.DEFAULT_PLOTLY_COLORS)


from bBrowser import bBrowser

myBrowser = bBrowser()
myBrowser.loadFolder()

#print('myBrowser.getStatList():', myBrowser.getStatList())
myStatList = myBrowser.getStatList()

# plot one of 4 graphs. USed in initialization and in 'plot' button callbacks
def plotButton(graphNum):

	yStat = myBrowser.graphPlot[graphNum]['yStat']
	xStat = myBrowser.graphPlot[graphNum]['xStat']

	print('bBrowser_app.plotButton() graphNum:', graphNum, 'xStat:', xStat, 'yStat:', yStat)

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
			'margin':{'l': 50, 'b': 50, 't': 5, 'r': 5},
			'clickmode':'event+select',
			'dragmode': 'select',
			'showlegend': False,
		}
	}

#app = dash.Dash(__name__)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
#app.css.append_css({'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'})  # noqa: E501


graph_names = ['g1', 'g2', 'g3', 'g4']

pre_style = {"backgroundColor": "#ddd", "fontSize": 20, "padding": "10px", "margin": "10px"}

###########
###########
myRow = html.Div(
	[
		dbc.Row(dbc.Col(html.Div("A single column"))),
		dbc.Row(
			[
				dbc.Col(html.Div("One of three columns")),
				dbc.Col(html.Div("One of three columns")),
				dbc.Col(html.Div("One of three columns")),
			]
		),
	]
)

colorList = ['rgb(31, 119, 180)', 'rgb(255, 127, 14)', 'rgb(44, 160, 44)', 'rgb(214, 39, 40)', 'rgb(148, 103, 189)', 'rgb(140, 86, 75)', 'rgb(227, 119, 194)', 'rgb(127, 127, 127)', 'rgb(188, 189, 34)', 'rgb(23, 190, 207)']
myBody = dbc.Container(
	[
		dbc.Row(
			[
				dbc.Col(
					[
						html.H4("File List"),

						dash_table.DataTable(
							id='file-list-table',
							row_selectable='multi',
							columns=[{"name": i, "id": i} for i in myBrowser.df0],
							data=myBrowser.df0.to_dict('records'),
						),
					])
			]
		),

		html.P(''),

		dbc.Row(
			[
				html.H4("Plot Options"),

				dcc.Checklist(
					id='showMeanID',
					options=[
						{'label': 'Mean', 'value': 'showMean'},
					], values=['showMean'], labelStyle={'padding-left': '20px', 'display': 'inline-block'}
				),

				dcc.RadioItems(
					id='showSDEVID',
					options=[
						{'label': 'SEM', 'value': 'SEM'},
						{'label': 'SDEV', 'value': 'SDEV'},
					], value='SEM', labelStyle={'padding-left': '10px', 'display': 'inline-block'}
				),
			], no_gutters=False, align='stretch', # row
		),

		dbc.Row(
			[
				dbc.Col(
					[

						html.H4("Y-Stat"),

						dash_table.DataTable(
							id='y-datatable',
							columns=[{"name": 'Idx', "id": 'Idx'}, {"name": 'Stat', "id": 'stat'}],
							data=[{"Idx": idx+1, "stat": myOption['label']} for idx, myOption in enumerate(myStatList)],
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
							selected_rows=[12],
						),

					],
					width={'size':100},

				),
				dbc.Col(
					[

						html.H4("X-Stat"),

						dash_table.DataTable(
							id='x-datatable',
							columns=[{"name": 'Idx', "id": 'Idx'}, {"name": 'Stat', "id": 'stat'}],
							data=[{"Idx": idx+1, "stat": myOption['label']} for idx, myOption in enumerate(myStatList)],
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
							selected_rows=[12],
						),

					],
					width={'size':100},

				),
				dbc.Col(
					[
						dbc.Button("Plot 1", color="primary", id='g1-plot-button'),
						dcc.Graph(
							id='g1',
							figure=plotButton(0),
						),

						dbc.Button("Plot 3", color="primary", id='g3-plot-button'),
						dcc.Graph(
							id='g3',
							figure=plotButton(2),
						),
					],
					md=3, align='stretch',

				),
				dbc.Col(
					[
						dbc.Button("Plot 2", color="primary", id='g2-plot-button'),
						dcc.Graph(
							id='g2',
							figure={
								"data": [{"x": [1, 2, 3], "y": [1, 4, 9]}],
								'layout': {
									'margin':{'l': 50, 'b': 50, 't': 5, 'r': 5},
									},
								},
						),

						dbc.Button("Plot 4", color="primary", id='g4-plot-button'),
						dcc.Graph(
							id='g4',
							figure={
								"data": [{"x": [1, 2, 3], "y": [1, 4, 9]}],
								'layout': {
									'margin':{'l': 50, 'b': 50, 't': 5, 'r': 5},
									},
								},
						),
					],
					md=3, align='stretch',
				),
			], no_gutters=False, align='stretch', # row
		)
	], className="mt-4", fluid=True,
)
##############
##############
app.layout = html.Div([

	myBody,

	html.Div(id='hidden-div'),
	html.Div(id='hidden-div2'),


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


	]) # closing app.layout = html.Div([

#
# callbacks
#

# see: https://gist.github.com/shawkinsl/22a0f4e0bf519330b92b7e99b3cfee8a

@app.callback(Output('my-tmp-pre', 'children'),
			  [Input('g1', 'clickData')],
			  [State('g1-click-datas', 'id'), State('g1-click-datas', 'children')])
def graph_clicked_xxx(click_data, clicked_id, children):
	print('=== graph_clicked_xxx()')
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
		print('=== graph_clicked()')
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


numClicks = [0, 0, 0, 0]

def handleGraphCallback(graphNumber, update_on_click_data, n_clicks, derived_virtual_selected_rows, showMean, showSDEVID):
	myBrowser.setSelectPoints(update_on_click_data)
	myBrowser.setSelectedFiles(derived_virtual_selected_rows)
	myBrowser.setShowMean(showMean)
	myBrowser.setShow_sdev_sem(showSDEVID)
	if n_clicks is not None and n_clicks > numClicks[graphNumber]:
		numClicks[graphNumber] = n_clicks
		myBrowser.plotTheseStats(graphNumber)


#
# these 4 callbacks are unruly, create a dict to pass to handleGraphCallback()

#1
@app.callback(Output('g1', 'figure'),
			[
			Input('update-on-click-data', 'children'),
			Input('g1-plot-button','n_clicks'),
			Input('file-list-table', "derived_virtual_selected_rows"),
			Input('showMeanID', 'values'),
			Input('showSDEVID', 'value'),
			])
def my1(update_on_click_data, n_clicks, derived_virtual_selected_rows, showMean, showSDEVID):
	graphNumber = 0
	#print('graph', graphNumber, 'callback() update_on_click_data:', update_on_click_data, 'n_clicks:', n_clicks)
	handleGraphCallback(graphNumber, update_on_click_data, n_clicks, derived_virtual_selected_rows, showMean, showSDEVID)
	return plotButton(graphNumber)

#2
@app.callback(Output('g2', 'figure'),
			[Input('update-on-click-data', 'children'),
			Input('g2-plot-button','n_clicks'),
			Input('file-list-table', "derived_virtual_selected_rows"),
			Input('showMeanID', 'values'),
			Input('showSDEVID', 'value'),
			])
def my2(update_on_click_data, n_clicks, derived_virtual_selected_rows, showMean, showSDEVID):
	graphNumber = 1
	#print('graph', graphNumber, 'callback() update_on_click_data:', update_on_click_data, 'n_clicks:', n_clicks)
	handleGraphCallback(graphNumber, update_on_click_data, n_clicks, derived_virtual_selected_rows, showMean, showSDEVID)
	return plotButton(graphNumber)

#3
@app.callback(Output('g3', 'figure'),
			[Input('update-on-click-data', 'children'),
			Input('g3-plot-button','n_clicks'),
			Input('file-list-table', "derived_virtual_selected_rows"),
			Input('showMeanID', 'values'),
			Input('showSDEVID', 'value'),
			])
def my2(update_on_click_data, n_clicks, derived_virtual_selected_rows, showMean, showSDEVID):
	graphNumber = 2
	#print('graph', graphNumber, 'callback() update_on_click_data:', update_on_click_data, 'n_clicks:', n_clicks)
	handleGraphCallback(graphNumber, update_on_click_data, n_clicks, derived_virtual_selected_rows, showMean, showSDEVID)
	return plotButton(graphNumber)

#4
@app.callback(Output('g4', 'figure'),
			[Input('update-on-click-data', 'children'),
			Input('g4-plot-button','n_clicks'),
			Input('file-list-table', "derived_virtual_selected_rows"),
			Input('showMeanID', 'values'),
			Input('showSDEVID', 'value'),
			])
def my2(update_on_click_data, n_clicks, derived_virtual_selected_rows, showMean, showSDEVID):
	graphNumber = 3
	#print('graph', graphNumber, 'callback() update_on_click_data:', update_on_click_data, 'n_clicks:', n_clicks)
	handleGraphCallback(graphNumber, update_on_click_data, n_clicks, derived_virtual_selected_rows, showMean, showSDEVID)
	return plotButton(graphNumber)

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
		ySel = myStatList[yRow]['label']
		myBrowser.setSelectedStat('y', ySel)
	if len(x_activeCell) > 0: # is not None:
		xRow = x_activeCell[0]
		xSel = myStatList[xRow]['label']
		myBrowser.setSelectedStat('x', xSel)

#
# main
#
if __name__ == '__main__':

	app.run_server(debug=True)
