#
import os
import pandas as pd

import dash_core_components as dcc
import dash_html_components as html
import dash_table
import dash_bootstrap_components as dbc

import sanpy

boxBorder = "1px gray solid"

def getFileList(path):
	"""
	Get list of bAnalysis from path

	Returns:
		list of bAnalysis
	"""
	baList = []
	retFileList = []
	useExtension = '.abf'
	videoFileIdx = 0

	fileDict = {}
	fileDict['Type'] = 'file'
	fileDict['File Name'] = ''
	#fileDict['path'] = ''
	fileDict['kHz'] = ''
	fileDict['Duration (Sec)'] = ''
	fileDict['Number of Sweeps'] = ''
	error = False
	if not os.path.isdir(path):
		# ERROR
		error = True

	if not error:
		for file in os.listdir(path):
			if file.startswith('.'):
				continue
			if file.endswith(useExtension):
				fullPath = os.path.join(path, file)

				fileDict = {} # WOW, I need this here !!!!!!!!
				fileDict['Type'] = 'file'
				fileDict['File Name'] = file
				#fileDict['path'] = fullPath

				ba = sanpy.bAnalysis(file=fullPath)

				baList.append(ba)
				'''
				if videoFileIdx == 0:
					print(ba.abf.headerText)
					sweepUnitsC # what we are clamping (mV, pA)
					sweepUnitsX
					sweepUnitsY
				'''

				# TODO: get this from bAnalysis header
				baHeader = ba.api_getHeader()
				recording_kHz = baHeader['recording_kHz'] #ba.dataPointsPerMs
				numSweeps = len(ba.sweepList)
				recordingDur_sec = baHeader['recordingDur_sec'] #max(ba.abf.sweepX)

				fileDict['kHz'] = recording_kHz
				fileDict['Duration (Sec)'] = round(recordingDur_sec,3)
				fileDict['Number of Sweeps'] = numSweeps

				retFileList.append(fileDict)
				videoFileIdx += 1
	#
	if len(retFileList) == 0:
		retFileList.append(fileDict)

	df = pd.DataFrame(retFileList)

	return df, baList

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
	if df is None:
		statDict = {'tmp':'empty'}
		df = pd.DataFrame(columns=['Idx', 'Error'])
		#df['idx'] = [i for i in range(len(statDict.keys()))]
		#df['error'] = [x for x in statDict.keys()]

	#
	columns=[{"name": i, "id": i} for i in df.columns]
	data=df.to_dict('records')

	ret = dash_table.DataTable(
		id=id,
		persistence = True,
		columns=columns,
		data=data,
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
		# CSS styles to be applied to the outer table container
		style_table={
			'height': height, # hard coding height
			'overflowX': 'auto',
			'overflowY': 'auto',
			#'width': width
		}
	)
	return ret
