# spike detection widget

from dash import dcc, html
import dash_bootstrap_components as dbc

import myDashUtils

def getDetectionLayout():

	plotParamList = [
		'Derivative',
		'Take Off Potential (dVdt)',
		'Take Off Potential (mV)',
		'AP Amp (mV)',
		'MDP (mV)',
		'EDD (s)',
		'AP Dur (s)',
	]

	#
	detectionRow = html.Div(
		[
		dbc.Row(
			[
			dbc.Col(html.Button(id='detect-button', children='Detect Spikes (dV/dt)', className='btn-primary')),
			dbc.Spinner(children=[html.Div(id='detect-spinner')]),
			]
		),

		dbc.Row(
			[
			dbc.Col(
				[
				dcc.Input(id='dvdtThreshold', type='number', value=50, style={'width': 60}),
				html.Label('dV/dt'),
				]),
			]
		),

		dbc.Row(
			[
			dbc.Col(
				[
				dcc.Input(id='mvThreshold', type='number', value=-20, style={'width': 60}),
				html.Label('Min AP Amp (mV)'),
				]),
			]
		),

		dbc.Row(
			[
			#dcc.Input(id='dvdtThreshold', type='number', value=50, style={'width': 60}),
			dbc.Col(
				[
				dcc.Input(id='refractory-ms', type='number', value='', style={'width': 60}),
				html.Label('Minimum ISI (ms)'),
				]),
			],
		),

		dbc.Row(dbc.Col(html.Label('Plot Options'))),
		dbc.Row(
			dbc.Col(myDashUtils.makeCheckList('plot-options-check-list', plotParamList))
			),

		dbc.Row(
			dbc.Col(html.Button(id='save-button', children='Save Analysis', className='btn-primary')),
			),

		dbc.Row(dbc.Col(html.Label('Spike Errors'))),
		dbc.Row(
			dbc.Col(
				#html.Label('Spike Errors'),
				myDashUtils.makeTable('spike-error-table', None, height=200)
			)
			), # row
		]
	) # div

	#
	#boxBorder = "1px gray solid"
	oneRow = html.Div( # outer div
		[
			dbc.Row(
				[
				dbc.Col(
						html.Div([
							#html.Label('Parameters'),
							detectionRow,
						]
						) # div
						,width=3, style={"border":myDashUtils.boxBorder}
					),

				# plot
				dbc.Col(
					html.Div([
						#dcc.Graph(style={'height': '500px'}, id='linked-graph'),
						dcc.Graph(id='linked-graph'),
					]
					) # div
					,width=9, style={"border":myDashUtils.boxBorder}
				),
				]
			), # row
		], className = 'container') # outerdiv

	#
	return oneRow
