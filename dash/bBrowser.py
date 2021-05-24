"""
Utility class to manage a list of bAnalysis .txt files and provide dash style web objects
"""

import os, sys, math, json, collections
from collections import OrderedDict

import pandas as pd
import numpy as np

import plotly.colors
import plotly.graph_objs as go

'''
class myCallbackException(Exception):
	def __init__(self, str):
		print('myCallbackException:', str)
		pass
		#raise
'''

#blackColor =

class bBrowser:
	def __init__(self, path=''):
		if path == '':
			path = '/Users/cudmore/Sites/bAnalysis/data'
		self.path = path

		self.makeFolderList()

		self.selectedFileRows = []

		# list of files
		self.df0 = None # small dataframe with list of files loaded

		# list of all spikes across all files
		self.df = None # massive dataframe with all spikes across all file

		self.options_Load() # load program options

		self.folderOptions = None # loaded from enclosing folder of self.path

		# this is the selection in the stat list
		self.selectedStat_y = 'thresholdSec'
		self.selectedStat_x = 'peakVal'

		# list of point selected across all graphs
		# ['points': {'curveNumber': 0, 'pointNumber': 16, 'pointIndex': 16, 'x': 48.2177734375, 'y': 14.4013}]
		self.selectedPoints = None

		self.showMean = False
		self.showMeanLines = False
		self.showError = True
		self.showNormalize = 'normalizeNone' # for plots with x-axis as 'Condition 1'
		self.showLines = False
		self.showMarkers = False

		self.plotlyColors = plotly.colors.DEFAULT_PLOTLY_COLORS + plotly.colors.DEFAULT_PLOTLY_COLORS
		'''
		print('bBrowser() will only show', len(self.plotlyColors), 'files !!!')
		print('self.plotlyColors:', self.plotlyColors)
		'''
		
	def makeFolderList(self):
		folderList = [self.path] # always include root /data folder as an option
		for item in os.listdir(self.path):
			currPath = os.path.join(self.path, item)
			if os.path.isdir(currPath):
				folderList.append(currPath)
		return folderList

	#
	# define, save, and load global program options
	def options_FactoryDefault(self):
		"""
		Create factory default options from bBrowser_FactoryDefaults.json file
		"""
		print('bBrowser.options_FactoryDefault()')
		dir_path = os.path.dirname(os.path.realpath(__file__))
		optionsPath = os.path.join(dir_path, 'bBrowser_FactoryDefaults.json')
		with open(optionsPath) as json_file:
			self.options = json.load(json_file)

	def option_Save(self):
		print('bBrowser.option_Save()')
		dir_path = os.path.dirname(os.path.realpath(__file__))
		optionsPath = os.path.join(dir_path, 'bBrowser_Options.json')
		with open(optionsPath, 'w') as json_file:
		    json.dump(self.options, json_file, indent=4)

	def options_Load(self):
		print('bBrowser.options_Load()')
		dir_path = os.path.dirname(os.path.realpath(__file__))
		optionsPath = os.path.join(dir_path, 'bBrowser_Options.json')
		if not os.path.isfile(optionsPath):
			self.options_FactoryDefault()
			#self.option_Save()
		else:
			with open(optionsPath) as json_file:
				self.options = json.load(json_file)

	#
	def setSelectedFiles(self, rows):
		"""
		Set the rows of selected files.

		rows: int list of selected rows
		"""

		#print('bBrowser.setSelectedFiles() rows:', rows)

		self.selectedFileRows = rows

	def setSelectedStat(self, xy, thisStat):
		"""
		thisStat: Human readbale, convert back to actual columns in loaded file
		"""
		print('setSelectedStat()', xy, thisStat)
		if xy == 'x':
			self.selectedStat_x = thisStat
		elif xy == 'y':
			self.selectedStat_y = thisStat

	def setSelectPoints(self, points):
		"""
		Set select points in a graph

		points: can be None
				otherwise: {'curveNumber': 0, 'pointNumber': 16, 'pointIndex': 16, 'x': 48.2177734375, 'y': 14.4013}
		"""
		if points is not None:
			#print('bBrowser.setSelectPoints() points:', points)
			points = json.loads(points)
		self.selectedPoints = points

	# more general than just show mean
	def setPlotOptions(self, plotOptions):
		#print('bBrowser.setPlotOptions() plotOptions:', plotOptions)
		self.showMean = 'showMean' in plotOptions
		self.showMeanLines = 'showMeanLines' in plotOptions
		self.showLines = 'showLines' in plotOptions
		self.showMarkers = 'showMarkers' in plotOptions

	def setShow_sdev_sem(self, showSDEVID):
		"""
		if not checked, showMean is []
		if checked showMean is ['showMean']
		"""
		#print('bBrowser.setShow_sdev_sem() showSDEVID:', showSDEVID)
		if 'None' in showSDEVID:
			self.showError = False
		elif 'SEM' in showSDEVID:
			self.showError = True
			self.showSE = True
		else:
			self.showError = True
			self.showSE = False

	def setShow_Normalize(self, normalizeValue):
		#print('setShow_Normalize()', normalizeValue)
		self.showNormalize = normalizeValue

	def plotTheseStats(self, graphNum):
		"""
		Set the x/y stat for graph graphNum to current x/y selected stat
		"""
		graphNumStr= str(graphNum)
		self.options['graphOptions'][graphNumStr]['yStat'] = self.selectedStat_y
		self.options['graphOptions'][graphNumStr]['xStat'] = self.selectedStat_x

	#
	# folder options
	#

	def _folderOptions_GetName(self):
		"""
		get the name of the enclosing folder options file
		"""
		enclosingFolder = os.path.split(self.path)[1]
		fileName = enclosingFolder + '_dash_db.json'
		saveFilePath = os.path.join(self.path, fileName)
		return saveFilePath

	def _folderOptions_Print(self):
		if self.folderOptions is not None:
			for item in self.folderOptions.items():
				print('   ', item)
		else:
			print('warning: _folderOptions_Print() found None self.folderOptions')

	def folderOptions_Save(self):
		"""
		Save options for an analysis folder

		Save a dict of:
			global options: (lines, markers, mean, etc etc) and
			for each file: (color, condition 1/2/3)

		'Analysis File' makes each file unique
		"""

		#print('folderOptions_Save()')

		# update self.folderOptions with any new conditions/color
		#outDict = {} # one key per file
		for index, row in self.df0.iterrows():
			#print(row)
			analysisFile = row['Analysis File']
			#self.folderOptions[analysisFile] = {}
			self.folderOptions[analysisFile]['Condition 1'] = row['Condition 1']
			self.folderOptions[analysisFile]['Condition 2'] = row['Condition 2']
			self.folderOptions[analysisFile]['Condition 3'] = row['Condition 3']
			self.folderOptions[analysisFile]['Color'] = row['Color']


		saveFilePath = self._folderOptions_GetName()
		with open(saveFilePath, 'w') as json_file:
		    print('bBrowser.folderOptions_Save() is saving saveFilePath:', saveFilePath)
		    json.dump(self.folderOptions, json_file, indent=4)

	def folderOptions_Load(self):
		"""
		Load options for an analysis folder
		"""
		theRet = None

		saveFilePath = self._folderOptions_GetName()
		if os.path.isfile(saveFilePath):
			print('bBrowser.folderOptions_Load() is loading saveFilePath:', saveFilePath)
			# load json
			with open(saveFilePath) as json_file:
				self.folderOptions = json.load(json_file)
				self._folderOptions_Print()
		return theRet

	def loadFolder(self):
		"""
		Load a hard drive folder of bAnalysis output .txt files into one Pandas dataframe self.df0
		"""
		if not os.path.isdir(self.path):
			print('error: bBrowser.loadFolder() did not find path:', self.path)
			return

		#
		# load the index file, if self.folderOptions is None then build it !!!
		self.folderOptions = self.folderOptions_Load()
		madeNewFolderOptions = False
		if self.folderOptions is None:
			madeNewFolderOptions = True
			self.folderOptions = OrderedDict()

		#
		# load each text file

		columns = ['Index',
			'Condition 1', # new
			'Condition 2', # new
			'Condition 3', # new
			'Analysis File', # new
			'ABF File',
			'Num Spikes',
			'First Spike (Sec)',
			'Last Spike (sec)'
		]
		self.df0 = pd.DataFrame(columns=columns)

		df0_list = []

		selectedFileRows = [] #self.selectedFileRows
		currIdx = 0
		currColorIdx = 0
		for file in sorted(os.listdir(self.path)):
			if file.startswith('.'):
				continue
			if file.endswith('.txt'):
				currFile = os.path.join(self.path,file)
				print('   bBrowser.loadFolder() loading analysis file:', currFile)
				df = pd.read_csv(currFile, header=1) # load comma seperated values, read header names from row 1

				# look into self.folderOptions
				if (self.folderOptions is not None) and file in self.folderOptions.keys():
					isChecked = self.folderOptions[file]['isChecked']
					condition1 = self.folderOptions[file]['Condition 1']
					condition2 = self.folderOptions[file]['Condition 2']
					condition3 = self.folderOptions[file]['Condition 3']
					color = self.folderOptions[file]['Color']
				else:
					isChecked = True
					condition1 = df.iloc[0]['condition1'] # assuming each row/spike has same condition 1/2/3
					condition2 = df.iloc[0]['condition2']
					condition3 = df.iloc[0]['condition3']
					
					if currColorIdx > len(self.plotlyColors)-1:
						currColorIdx = 0
					color = self.plotlyColors[currColorIdx]

					# add a new file
					self.folderOptions[file] = OrderedDict()
					self.folderOptions[file]['isChecked'] = isChecked
					self.folderOptions[file]['Condition 1'] = condition1
					self.folderOptions[file]['Condition 2'] = condition2
					self.folderOptions[file]['Condition 3'] = condition3
					self.folderOptions[file]['Color'] = color

				selectedFileRows.append(isChecked)

				# THIS IS TOO FUCKING COMPLICATED !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
				# regardless set self.folderOptions

				# insert new columns not in original .txt file
				df.insert(0, 'Analysis File', file)
				#df.insert(0, 'Condition 3', condition3) # 'currIdx + 3' is bogus default value
				#df.insert(0, 'Condition 2', condition2)
				#df.insert(0, 'Condition 1', condition1)

				numSpikes = len(df.index)
				
				#
				#
				# 20190724, newly saved files fail here, there is no thresholdSec
				#
				#
				firstSpikeSec = df['thresholdSec'].min()
				lastSpikeSec = df['thresholdSec'].max()
				abfFile = df.iloc[0]['file']
				abfFile = os.path.split(abfFile)[1] # get the file name from the path

				dfRow = collections.OrderedDict()
				dfRow['Index'] = currIdx + 1
				dfRow['Color'] = color
				dfRow['Condition 1'] = condition1 # to start, condition1/2/3 are FAKE
				dfRow['Condition 2'] = condition2
				dfRow['Condition 3'] = condition3
				dfRow['Analysis File'] = file
				dfRow['ABF File'] = abfFile
				dfRow['Num Spikes'] = numSpikes
				dfRow['First Spike (Sec)'] = float('%.3f'%(firstSpikeSec))
				dfRow['Last Spike (Sec)'] = float('%.3f'%(lastSpikeSec))


				df0_list.append(dfRow)

				# BIG df with ALL spikes
				if self.df is None:
					self.df = df
				else:
					self.df = pd.concat([self.df, df], axis=0)

				currIdx += 1
				currColorIdx += 1
				
		self.df0 = pd.DataFrame(df0_list)

		self.selectedFileRows = selectedFileRows

		if madeNewFolderOptions:
			self.folderOptions_Save()

	def updatePlot(self, graphNum, xStatName, yStatName):
		"""
		Update a plot with new x/y stat
		
		Return
			1) a list of dict for plotly/dash data
			2) layout
		"""

		theRet = []

		meanDataDict = {} # dict of dict to be appended at end of loop

		doNotDoMean = ['Condition 1', 'Condition 2', 'Condition 3']

		hideMeanLines = not self.showMeanLines or (xStatName in doNotDoMean or yStatName in doNotDoMean)
		hideMeanLines = False

		myNormDict = {}

		if xStatName and yStatName:
			displayedFileRows = 0
			for index, file in self.df0.iterrows():
				#print(index, file['ABF File'])
				#print(index, file)

				if index not in self.selectedFileRows:
					continue

				#
				# this is critical, have not thought a lot about it -->> may break !!!!
				# this is to allow show/hide of mean/sd/se which make index and selection curveNumber out of sync
				#

				thisIsMyColor = self.df0.loc[index, 'Color']

				#displayedFileRows += 1
				actualCurveNumber = index
				'''
				if self.showMean:
					actualCurveNumber = (displayedFileRows-1) * 2
				'''

				abfFile = file['ABF File']
				condition1 = file['Condition 1'] # use this to connect mean with line
				analysisFile = file['Analysis File']
				abfFile = file['ABF File']

				# rows of large (spikes) df that make this file
				thisFileRows = self.df.loc[self.df['Analysis File'] == analysisFile]

				# get columns in self.df corresponding to selected stat
				if xStatName in thisFileRows.columns:
					xStatVals = thisFileRows[xStatName] #pandas.core.series.Series
				else:
					print('WARNING: bBrowser.updatePlot() did not find specified x statistic "' + xStatName + '"')
					return {}
				if yStatName in thisFileRows.columns:
					yStatVals = thisFileRows[yStatName] #pandas.core.series.Series
				else:
					print('WARNING: bBrowser.updatePlot() did not find specified y statistic "' + yStatName + '"')
					return {}

				#
				# normalize to first
				# NOTE: as I was adding this I transformed xStatVals and yStatVal from pandas series to numpy ndarray
				if self.showNormalize != 'normalizeNone' and xStatName == 'Condition 1':
					#pass
					# before loop, create a dict
					if abfFile not in myNormDict.keys():
						# 20190725, here, I need to normalize to FIRST condition
						# but we do not know the FIRST condition !!!!
						# conditions are coming in as we encounter them in the file list !!!!
						print('!!! bBrowser.updatePlot() adding abf file to myNormDict, abfFile:', abfFile, 'condition1:', condition1)
						myNormDict[abfFile] = {
							#'x': xStatVals.values,
							'y': np.nanmean(yStatVals.values)
						}
					#print('type(xStatVals)', type(xStatVals))
					#print('type(xStatVals.values)', type(xStatVals.values))
					#print('type(xStatVals.values())', type(xStatVals.values()))
					#sys.exit()
					#xStatVals = xStatVals.values / myNormDict[abfFile]['x']
					if self.showNormalize == 'normalizeAbsolute':
						yStatVals = yStatVals.values - myNormDict[abfFile]['y']
					elif self.showNormalize == 'normalizePercent':
						yStatVals = yStatVals.values / myNormDict[abfFile]['y'] * 100

				#print('type(xStatVals)', type(xStatVals))
				#print('xStatVals[0]', xStatVals[0])
				dataDict = {}
				dataDict['x'] = xStatVals
				dataDict['y'] = yStatVals

				dataDict['marker'] = {
					#'color': self.plotlyColors[actualCurveNumber],
					#myBrowser.df0.loc[rowsToChange, 'Color']
					'color': self.df0.loc[index, 'Color'],
					'color': thisIsMyColor,
					'size': 10,
				}

				dataDict['mode'] = ''
				if not self.showLines and not self.showMarkers:
					dataDict['mode'] = 'none' # 'none' is lower case !!!
				if self.showLines:
					dataDict['mode'] += '+lines'
				if self.showMarkers:
					dataDict['mode'] += '+markers'

				dataDict['name'] = analysisFile #'File ' + str(index + 1)

				if self.selectedPoints is not None:
					if isinstance(self.selectedPoints, str):
						print('\n\n      updatePlot() converting to dict -- THIS SHOULD NEVER HAPPEN \n\n')
						self.selectedPoints = json.loads(self.selectedPoints)

					# debug selection of mean
					'''
					for point in self.selectedPoints['points']:
						#print('point:', point)
						print("point['curveNumber']:", point['curveNumber'], 'actualCurveNumber:', actualCurveNumber)
					'''

					# todo: problem here ???
					# 20190530, we can't do this until we have appended the mean ???
					selectedPoints = [point['pointNumber'] for point in self.selectedPoints['points'] if point['curveNumber'] == actualCurveNumber]
					dataDict['selectedpoints'] = selectedPoints

					dataDict['unselected'] = {
						'marker': {
							'opacity': 0.3,
						},
						'textfont': {
							# make text transparent when not selected
							'color': 'rgba(0, 0, 0, 0)'
						}
					}

				theRet.append(dataDict)

				if self.showMean:
					# x
					xMean, xSD, xN, xSE = None, None, None, None
					if xStatName in doNotDoMean:
						xMean = xStatVals.values[0]
						#print('type(xMean):', type(xMean), 'xMean:', xMean)
						'''
						xSD = 0
						xN = 0
						xSE = 0
						'''
					else:
						xMean = np.nanmean(xStatVals)
						xSD = np.nanstd(xStatVals)
						xN = np.count_nonzero(~np.isnan(xStatVals))
						xSE = xSD / math.sqrt(xN - 1)
						#print('xMean:', xMean, 'xSE', xSE, 'xN:', xN)

					# y
					yMean, ySD, yN, ySE = None, None, None, None
					if yStatName in doNotDoMean:
						#print('yStatVals:', yStatVals)
						yMean = yStatVals.values[0]
						'''
						ySD = 0
						yN = 0
						ySE = 0
						'''
					else:
						yMean = np.nanmean(yStatVals)
						ySD = np.nanstd(yStatVals)
						yN = np.count_nonzero(~np.isnan(yStatVals))
						ySE = ySD / math.sqrt(yN - 1)
						#print('yMean:', yMean, 'ySE', ySE, 'yN:', yN)

					#if abfFile not in meanDataDict.keys():
					#meanKey = str(condition1)
					meanKey = str(abfFile)
					if meanKey not in meanDataDict.keys():
						#print('=== making meanDataDict for file index:', index, 'meanKey:', meanKey)
						meanDataDict[meanKey] = {}
						meanDataDict[meanKey]['x'] = []
						meanDataDict[meanKey]['y'] = []
						if hideMeanLines:
							meanDataDict[meanKey]['mode'] = 'markers'
						else:
							meanDataDict[meanKey]['mode'] = 'lines+markers'
						#meanDataDict[meanKey]['name'] = abfFile + '_mean' # todo: need to clean up abfFile
						#meanDataDict[meanKey]['name'] = condition1 + '_mean' # todo: need to clean up abfFile
						#meanDataDict[meanKey]['name'] = condition1 + ' ' + abfFile # todo: need to clean up abfFile
						meanDataDict[meanKey]['name'] = analysisFile # todo: need to clean up abfFile
						#abfFile
						meanDataDict[meanKey]['marker'] = {
							'color': [],
							'size': 13,
						}
						meanDataDict[meanKey]['line'] = {
							'color': ('rgb(0,0,0)'),
						}
						meanDataDict[meanKey]['error_x'] = {
							'type': 'data',
							'array': [],
							'visible': True,
							'color': [],
						}
						meanDataDict[meanKey]['error_y'] = {
							'type': 'data',
							'array': [],
							'visible': True,
							'color': [],
						}

					'''
					meanDict = {}
					meanDict['x'] = [xMean] # these have to be list, not scalar !
					meanDict['y'] = [yMean]
					meanDict['mode'] = 'markers'
					meanDict['name'] = analysisFile + '_mean'
					'''
					meanDataDict[meanKey]['x'].append(xMean) # xMean is a scalar
					meanDataDict[meanKey]['y'].append(yMean) # yMean is a scalar

					#meanDataDict[meanKey]['marker']['color'].append(self.plotlyColors[actualCurveNumber])
					meanDataDict[meanKey]['marker']['color'].append(thisIsMyColor)

					if self.showError:
						'''
						meanDict['error_x'] = {
							'type': 'data',
							'array': [xSE] if self.showSE else [xSD],
							'visible': True
						}
						meanDict['error_y'] = {
							'type': 'data',
							'array': [ySE] if self.showSE else [ySD],
							'visible': True
						}
						'''
						meanDataDict[meanKey]['error_x']['array'].append(xSE if self.showSE else xSD)
						meanDataDict[meanKey]['error_y']['array'].append(ySE if self.showSE else ySD)

						#meanDataDict[meanKey]['error_x']['color'].append(self.plotlyColors[actualCurveNumber])
						#meanDataDict[meanKey]['error_y']['color'].append(self.plotlyColors[actualCurveNumber])
						meanDataDict[meanKey]['error_x']['color'].append(thisIsMyColor)
						meanDataDict[meanKey]['error_y']['color'].append(thisIsMyColor)

					###
					meanDataDict[meanKey]['unselected'] = {
						'marker': {
							'opacity': 0.3,
						},
						'textfont': {
							# make text transparent when not selected
							'color': 'rgba(0, 0, 0, 0)'
						}
					}
					###

					#print('meanDict:', meanDict)

					#meanDataDict[abfFile].append(meanDict)
					#theRet.append(meanDict)

			# after 'for index, file in self.df0.iterrows():'

			# append means at end, they are grouped based on original abf file !!!
			for key, value in meanDataDict.items():
				theRet.append(value)

			# 20190530
			# try and get user selection of a point including both (raw, mean)
			# theRet has a number of traces including raw data (from) files and potentially a mean for each file
			if self.selectedPoints is not None:
				for idx, item in enumerate(theRet):
					#print('xxx item:', item)
					selectedPoints = [point['pointNumber'] for point in self.selectedPoints['points'] if point['curveNumber'] == idx]

					if len(selectedPoints) > 0:
						#dataDict['selectedpoints'] = selectedPoints
						print('   curve number idx:', idx, 'has selectedPoints:', selectedPoints)
						theRet[idx]['selectedpoints'] = selectedPoints

					###
					theRet[idx]['unselected'] = {
						'marker': {
							'opacity': 0.3,
						},
						'textfont': {
							# make text transparent when not selected
							'color': 'rgba(0, 0, 0, 0)'
						}
					}
					###

		# 20190626, get this to work !!!!!!!!!!!
		graphNumStr = str(graphNum)
		yStatHuman = self.options['graphOptions'][graphNumStr]['yStat']
		xStatHuman = self.options['graphOptions'][graphNumStr]['xStat']

		#print('   !!!!!!!!!!!!!!!!!! WHY IS LAYOUT XAXIS FONT SIZE NOT WORKING????????????????????????????????')

		#if self.showNormalize != 'normalizeNone' and xStatName == 'Condition 1':
		yaxisLabel = yStatHuman
		if xStatName == 'Condition 1':
			if self.showNormalize == 'normalizeNone':
				yaxisLabel = yStatHuman
			elif self.showNormalize == 'normalizeAbsolute':
				yaxisLabel = yStatHuman + ' Abs'
			elif self.showNormalize == 'normalizePercent':
				yaxisLabel = yStatHuman + ' %'

		layout = {
			'xaxis': {
				#'title': xStatHuman,
				'title': {
					'text': xStatHuman,
					'font': { 'size': 18},
				},
				'zeroline': False,
				#'font': { 'size': 56},
				'range': [],
			},
			'yaxis': {
				#'title': yStatHuman,
				'title': {
					'text': yaxisLabel,
					'font': { 'size': 18},
				},
				'zeroline': False,
			},
			'margin':{'l': 50, 'b': 50, 't': 5, 'r': 5},
			'clickmode':'event+select',
			'dragmode': 'select',
			'showlegend': False,
		}
		#},
		# OH MY FUCKING GOD, if a dict definition {} has a trailing ',', it becomes a tuple !!!!!!!! FUCK

		# 20190626 was this
		#return theRet

		# 20190626, get this to work !!!!!!!!!!!!
		finalReturn = {
			'data': theRet,
			'layout': layout,
		}
		return finalReturn
		"""
		return {
			'data': theRet,
			'layout': layout,
		}
		"""
