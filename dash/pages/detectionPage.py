# spike detection widget

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

import myDashUtils

def getDetectionLayout():

	plotParamList = [
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
			dbc.Spinner(children=[html.Div(id='detect-spinner')]),
			dbc.Col(html.Button(id='detect-button', children='Detect Spikes (dV/dt)', className='btn-primary')),
			# [dbc.Spinner(size="sm"), " Loading..."]
			#dbc.Col(dbc.Button(id='detect-button0', children='Detect Spikes (dV/dt)', className='btn-primary btn-small')),
			#
			#dbc.Col(dbc.Button([dbc.Spinner(size="sm"), 'Detect Spikes (dV/dt)'], id='detect-button', color='primary', className='btn-primary btn-sm')),
			#dbc.Col(dbc.Button(id='detect-button', children='Detect Spikes (dV/dt)', color='primary')),
			dbc.Col(dcc.Input(id='dvdtThreshold', type='number', value=50, style={'width': 40})),
			#dbc.Col(dcc.Input(id='dvdtThreshold', type='number', value=50)),
			]
		),

		dbc.Row(html.Label('Plot Options')),

		dbc.Row(
			dbc.Col(myDashUtils.makeCheckList('plot-options-check-list', plotParamList))
			),

		dbc.Row(
			dbc.Col(html.Button(id='save-button', children='Save Analysis', className='btn-primary')),
			),
		]
	) # div

	#
	boxBorder = "1px gray solid"
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
						,width=3, style={"border":boxBorder}
					),

				# plot
				dbc.Col(
					html.Div([
						#dcc.Graph(style={'height': '500px'}, id='linked-graph'),
						dcc.Graph(id='linked-graph'),
					]
					) # div
					,width=9, style={"border":boxBorder}
				),
				]
			), # row
		], className = 'container') # outerdiv

	#
	return oneRow
