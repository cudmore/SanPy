#
import os
import pandas as pd

from dash import dcc, html
from dash import dash_table
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
	fileDict['Dur(s)'] = ''
	fileDict['Sweeps'] = ''
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
				fileDict['Dur(s)'] = round(recordingDur_sec,3)
				fileDict['Sweeps'] = numSweeps

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
def makeTable(id, df, height=300, row_selectable='single', defaultRow=0):
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

def old_test_requests():
	"""
	this gets all files, including

	https://api.github.com/repos/cudmore/SanPy/git/trees/master?recursive=1

    {
      "path": "data",
      "mode": "040000",
      "type": "tree",
      "sha": "8b97ef351ea95308b524b6febb2890f000b86388",
      "url": "https://api.github.com/repos/cudmore/SanPy/git/trees/8b97ef351ea95308b524b6febb2890f000b86388"
    },
    {
      "path": "data/171116sh_0018.abf",
      "mode": "100644",
      "type": "blob",
      "sha": "5f3322b08d86458bf7ac8b5c12564933142ffd17",
      "size": 2047488,
      "url": "https://api.github.com/repos/cudmore/SanPy/git/blobs/5f3322b08d86458bf7ac8b5c12564933142ffd17"
    },

	Then this url:
	https://api.github.com/repos/cudmore/SanPy/git/blobs/5f3322b08d86458bf7ac8b5c12564933142ffd17
	returns a dict d{} with

	{
	  "sha": "5f3322b08d86458bf7ac8b5c12564933142ffd17",
	  "node_id": "MDQ6QmxvYjE3MTA2NDA5Nzo1ZjMzMjJiMDhkODY0NThiZjdhYzhiNWMxMjU2NDkzMzE0MmZmZDE3",
	  "size": 2047488,
	  "url": "https://api.github.com/repos/cudmore/SanPy/git/blobs/5f3322b08d86458bf7ac8b5c12564933142ffd17",
	  "coontent": "<CONTENTS>"
	  "encoding": "base64"
	  }

	https://api.github.com/repos/:owner/:repo_name/contents/:path

	"""
	import requests
	import io

	# this works
	'''
	url = "https://github.com/cudmore/SanPy/blob/master/data/19114001.abf?raw=true"
	# Make sure the url is the raw version of the file on GitHub
	download = requests.get(url).content
	'''

	owner = 'cudmore'
	repo_name = 'SanPy'
	path = 'data'
	url = f'https://api.github.com/repos/{owner}/{repo_name}/contents/{path}'
	response = requests.get(url).json()
	print('response:', type(response))
	#print(response.json())
	for idx, item in enumerate(response):
		if not item['name'].endswith('.abf'):
			continue
		print(idx)
		# use item['git_url']
		for k,v in item.items():
			print('  ', k, ':', v)

	#
	# grab the first file
	#gitURl = response[0]['git_url']
	'''
	print('  === gitURL:', gitURL)
	#download = requests.get(gitURl).content
	downloadRespoonse = requests.get(gitURL).json()
	print('  downloadRespoonse:', type(downloadRespoonse))
	content = downloadRespoonse['content']
	#print('  ', downloadRespoonse)
	#decoded = download.decode('utf-8')
	#print('  decoded:', type(decoded))
	'''

	# use response[0]['download_url'] to directly download file
	#gitURL = 'https://raw.githubusercontent.com/cudmore/SanPy/master/data/SAN-AP-example-Rs-change.abf'
	download_url = response[1]['download_url']
	content = requests.get(download_url).content

	#import base64
	#myBase64 = base64.b64encode(bytes(content, 'utf-8'))
	#myBase64 = base64.b64encode(bytes(content, 'base64'))
	'''
	myBase64 = base64.b64encode(bytes(content, 'utf-8'))
	print('myBase64:', type(myBase64))
	'''
	#decoded = content.decode('utf-8')
	#print(download)
	#import pyabf
	fileLikeObject = io.BytesIO(content)
	ba = sanpy.bAnalysis(byteStream=fileLikeObject)
	print(ba._abf)
	print(ba.api_getHeader())

if __name__ == '__main__':
	#test_requests()
	pass
