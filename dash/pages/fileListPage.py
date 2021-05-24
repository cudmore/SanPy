
import dash_html_components as html
import dash_bootstrap_components as dbc

import myDashUtils
from pages import uploadpage

def getFileListLayout(path, dfFileList):

	fileListControls = html.Div(
		[
		dbc.Row(
			[
			dbc.Col(html.Button(id='load-folder-button', children='Load Folder', className='btn-primary')),
			#dbc.Col(dcc.Input(id='dvdtThreshold', type='number', value=50, style={'width': 65})),
			]
		),

		dbc.Row(
			[
			dbc.Col(html.Label(path)),
			]
		),

		dbc.Row(
			dbc.Col(uploadpage.uploadPageLayout)
			),
		]
	) # div

	boxBorder = "1px gray solid"
	oneRow = html.Div( # outer div
		[
			dbc.Row(
				[
				dbc.Col(
						html.Div([
							#html.Label('Parameters'),
							fileListControls,
						]
						) # div
						,width=3, style={"border":boxBorder}
					),

				# plot
				dbc.Col(
					html.Div([
						#html.Label('X-Stat'),
						myDashUtils.makeTable('file-list-table', dfFileList, height=180, defaultRow=0)
					]) # div
					,width=9,style={"border":boxBorder}
				), # col
				]
			), # row
		], className = 'container') # outerdiv

	#
	return oneRow
