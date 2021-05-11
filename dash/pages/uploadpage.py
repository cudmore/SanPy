"""
dash app allowing drag/drop of csv or xls file
parses upload into table

todo: use this to define pandas df we are working with
"""

import sys
import base64
import datetime
import io

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table

import pandas as pd

from app import app
import pyabf
import sanpy

#app.layout = html.Div([
uploadPageLayout = html.Div([
	dbc.Row(
	[
	dbc.Col(
	dcc.Upload(
		id='upload-data',
		children=html.Div([
			'Drag and Drop File',
			#html.A('Select Files')
		]),
		style={
			'width': '100%',
			'height': '50px',
			'lineHeight': '50px',
			'borderWidth': '1px',
			'borderStyle': 'dashed',
			'borderRadius': '5px',
			'textAlign': 'center',
			#'margin': '10px'
		},
		# Allow multiple files to be uploaded
		multiple=True
	)
	), # col
	]), # row

	dbc.Row(
	[
		dbc.Col(html.Div(id='output-data-upload')),
	]),
])


def parse_contents_abf(contents, filename, date):
	"""
	parses binary abf file
	"""
	print('parse_contents_abf() filename:', filename)

	content_type, content_string = contents.split(',')

	#print('  content_type:', content_type)
	decoded = base64.b64decode(content_string)
	#print('  type(decoded)', type(decoded))
	fileLikeObject = io.BytesIO(decoded)
	#print('  type(fileLikeObject)', type(fileLikeObject))

	#print(len(fileLikeObject.getvalue()))
	#major = pyabf.abfHeader.abfFileFormat(fileLikeObject)
	#print('  pyabf major:', major)

	print('  instantiating sanpy.bAnalysis with byte stream')
	try:
		global ba
		ba = sanpy.bAnalysis(byteStream=fileLikeObject)
	except:
		print('*** exception in parse_contents_abf():')
		print(sys.exc_info())

	'''
	return html.Div([
		html.H6(f'Loaded file: {filename}'),
	])
	'''
	'''
	return html.Div([
		html.Hr(),
		html.H6(f'Loaded file: {filename}'),
	])
	'''
	return html.Label(f'Loaded file: {filename}')

def parse_contents(contents, filename, date):
	"""
	parses csv oor xls
	"""
	content_type, content_string = contents.split(',')

	decoded = base64.b64decode(content_string)
	try:
		if 'csv' in filename:
			# Assume that the user uploaded a CSV file
			df = pd.read_csv(
				io.StringIO(decoded.decode('utf-8')))
		elif 'xls' in filename:
			# Assume that the user uploaded an excel file
			df = pd.read_excel(io.BytesIO(decoded))
	except Exception as e:
		print(e)
		return html.Div([
			'There was an error processing this file.'
		])

	return html.Div([
		html.H5(f'Loaded file: {filename}'),
		#html.H6(datetime.datetime.fromtimestamp(date)),
		html.H6('First Few Rows are:'),
		dash_table.DataTable(
			data=df.head().to_dict('records'),
			columns=[{'name': i, 'id': i} for i in df.columns]
		),

		html.Hr(),  # horizontal line

		# For debugging, display the raw contents provided by the web browser
		#html.Div('Raw Content'),
		#html.Pre(contents[0:200] + '...', style={
		#	'whiteSpace': 'pre-wrap',
		#	'wordBreak': 'break-all'
		#})
	])


@app.callback(Output('output-data-upload', 'children'),
			  Input('upload-data', 'contents'),
			  State('upload-data', 'filename'),
			  State('upload-data', 'last_modified'))
def uploadPageCallback(list_of_contents, list_of_names, list_of_dates):
	print('uploadPageCallback()')
	print('  list_of_contents:', '** THIS IS BASE64 REPRESENTATION OF FILE')
	print('  list_of_names:', list_of_names)
	print('  list_of_dates:', list_of_dates)

	if list_of_contents is not None:
		children = [
			parse_contents_abf(c, n, d) for c, n, d in
			zip(list_of_contents, list_of_names, list_of_dates)]
		return children
