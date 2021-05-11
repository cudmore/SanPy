#
import os
import pandas as pd

import dash_core_components as dcc
import dash_html_components as html
import dash_table
import dash_bootstrap_components as dbc

import sanpy

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

			tmp_ba = sanpy.bAnalysis(file=fullPath)
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

	df = pd.DataFrame(retFileList)

	return df

def makeCheckList(id, itemList, defaultItem=None):
	options = [{'label': x, 'value': x} for x in itemList]
	ret = dcc.Checklist(
		id=id,
		persistence = True,
		options=options,
		value=[itemList[0]],
		#labelStyle={'display': 'inline-block'}
		labelStyle={"margin-right": "15px"}, # adds space between options list
		inputStyle={"margin-right": "5px"}, # adds space between check and its label
	), # Checklist
	return ret

# todo: put this is myDashUtil.py
def makeTable(id, df, height=200, row_selectable='single', defaultRow=0):
	"""
	defaultRow: row index selected on __init__
	"""
	ret = dash_table.DataTable(
		id=id,
		persistence = True,
		columns=[{"name": i, "id": i} for i in df.columns],
		data=df.to_dict('records'),
		row_selectable=row_selectable,
		fixed_rows={'headers': True}, # on scroll, keep headers at top
		selected_rows = [defaultRow], # default selected row
		style_header={
			'backgroundColor': 'rgb(30, 30, 50)',
			'fontWeight': 'bold',
		},
		style_cell={
			'textAlign': 'left',
			'fontSize':11, 'font-family':'sans-serif',
			'color': 'white', # dark theme
			'backgroundColor': 'rgb(30, 30, 30)',# dark theme
			},
		style_data_conditional=[
			{
			'if': {'row_index': 'odd'},
			#'backgroundColor': 'rgb(50, 50, 50)' # dark theme
			'backgroundColor': 'rgb(50, 50, 50)' # light theme
			}
		],
		style_table={
			'height': height, # hard coding height
			#'overflowY': 'scroll',
			'overflowX': 'auto',
			'overflowY': 'auto',
			#'width': width
		}
	)
	return ret
