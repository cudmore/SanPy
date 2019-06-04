"""
Utility class to manage a list of BaNalaysis .txt files and provide dash style web objects
"""

import os, math, json, collections
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

class bBrowser:
	def __init__(self, path=''):
		if path == '':
			path = '/Users/cudmore/Sites/bAnalysis/data'
		self.path = path

		self.selectedRows = []

		# list of files
		self.df0 = None # small dataframe with list of files loaded

		# list of all spikes across all files
		self.df = None # massive dataframe with all spikes across all file

		self.folderOptions = None # loaded from enclosing folder of self.path
		self.options_Load() # load program options
		
		# this is the selection in the stat list
		self.selectedStat_y = 'thresholdSec'
		self.selectedStat_x = 'peakVal'

		# list of point selected across all graphs
		# ['points': {'curveNumber': 0, 'pointNumber': 16, 'pointIndex': 16, 'x': 48.2177734375, 'y': 14.4013}]
		self.selectedPoints = None

		self.showMean = False
		self.showMeanLines = False
		self.showError = True
		self.showLines = False
		self.showMarkers = False

		self.plotlyColors = plotly.colors.DEFAULT_PLOTLY_COLORS
		print('bBrowser() will only show', len(self.plotlyColors), 'files !!!')
		
	#
	# define, save, and load global program options
	def options_FactoryDefault(self):
		"""
		Create factory default options from bBrowser_FactoryDefaults.json file
		"""
		dir_path = os.path.dirname(os.path.realpath(__file__))
		optionsPath = os.path.join(dir_path, 'bBrowser_FactoryDefaults.json')
		with open(optionsPath) as json_file:  
			self.options = json.load(json_file)
		
	def option_Save(self):
		dir_path = os.path.dirname(os.path.realpath(__file__))
		optionsPath = os.path.join(dir_path, 'bBrowser_Options.json')
		with open(optionsPath, 'w') as json_file:  
		    json.dump(self.options, json_file, indent=4)
    		
	def options_Load(self):
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
		print('bBrowser.setSelectedFiles() rows:', rows)

		self.selectedRows = rows

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
			print('bBrowser.setSelectPoints() points:', points)
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

	def plotTheseStats(self, graphNum):
		"""
		Set the x/y stat for graph graphNum to current x/y selected stat
		"""
		graphNumStr= str(graphNum)
		self.options['graphOptions'][graphNumStr]['yStat'] = self.selectedStat_y
		self.options['graphOptions'][graphNumStr]['xStat'] = self.selectedStat_x

	def _folderOptions_GetName(self):
		"""
		get the name of the enclosing folder options file
		"""
		enclosingFolder = os.path.split(self.path)[1]
		fileName = enclosingFolder + '.json'
		saveFilePath = os.path.join(self.path, fileName)
		return saveFilePath
	
	def folderOptions_Save(self):
		"""
		Save options for an analysis folder
		
		Save a dict of:
			global options: (lines, markers, mean, etc etc) and
			for each file: (color, condition 1/2/3) 
		
		'Analysis File' makes each file unique
		"""
		print('folderOptions_Save()')
		
		outDict = {} # one key per file
		for index, row in self.df0.iterrows():
			#print(row)
			analysisFile = row['Analysis File']
			outDict[analysisFile] = {}
			outDict[analysisFile]['Condition 1'] = row['Condition 1']
			outDict[analysisFile]['Condition 2'] = row['Condition 2']
			outDict[analysisFile]['Condition 3'] = row['Condition 3']
			outDict[analysisFile]['Color'] = row['Color']


		saveFilePath = self._folderOptions_GetName()
		with open(saveFilePath, 'w') as json_file:  
		    json.dump(outDict, json_file, indent=4)
			
		
			
	def folderOptions_Load(self):
		"""
		Load options for an analysis folder
		"""
		saveFilePath = self._folderOptions_GetName()
		if os.path.isfile(saveFilePath):
			# load json
			pass
		else:
			# no options yet
			pass
			
	def loadFolder2(self):
		print('loadFolder2()')
		self.loadFolder()
		
	def loadFolder(self):
		"""
		Load a hard drive folder of bAnalysis output .txt files into one Pandas dataframe self.df0
		"""
		if not os.path.isdir(self.path):
			print('error: bBrowser.loadFolder() did not find path:', self.path)
			return

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

		currIdx = 0
		for file in os.listdir(self.path):
			if file.startswith('.'):
				continue
			if file.endswith('.txt'):
				currFile = os.path.join(self.path,file)
				print('bBrowser.loadFolder() loading analysis file:', currFile)
				df = pd.read_csv(currFile, header=0) # load comma seperated values, read header names from row 1

				# look into self.folderOptions
				if self.folderOptions is None:
					condition1 = 'None'
					condition2 = 'None'
					condition3 = 'None'
					color = 'rgb(0,0,0)'
				else:
					pass
					
				# insert new columns not in original .txt file
				df.insert(0, 'Analysis File', file)
				df.insert(0, 'Condition 3', condition3) # 'currIdx + 3' is bogus default value
				df.insert(0, 'Condition 2', condition2)
				df.insert(0, 'Condition 1', condition1)

				numSpikes = len(df.index)
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

		self.df0 = pd.DataFrame(df0_list)

		# trying to get saving json for folder working
		#self.folderOptions_Save()
		
	def updatePlot(self, xStatName, yStatName):
		""" return a list of dict for plotly/dash data"""

		theRet = []

		meanDataDict = {} # dict of dict to be appended at end of loop
		
		doNotDoMean = ['Condition 1', 'Condition 2', 'Condition 3']
		
		doBar = xStatName in doNotDoMean or yStatName in doNotDoMean
		doBar = False
		
		hideMeanLines = not self.showMeanLines or (xStatName in doNotDoMean or yStatName in doNotDoMean)
		
		if xStatName and yStatName:
			displayedFileRows = 0
			for index, file in self.df0.iterrows():
				#print(index, file['ABF File'])
				#print(index, file)

				if index not in self.selectedRows:
					continue

				#
				# this is critical, have not thought a lot about it -->> may break !!!!
				# this is to allow show/hide of mean/sd/se which make index and selection curveNumber out of sync
				#
				
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
				xStatVals = thisFileRows[xStatName]
				yStatVals = thisFileRows[yStatName]

				dataDict = {}
				dataDict['x'] = xStatVals
				dataDict['y'] = yStatVals

				if doBar:
					dataDict['marker'] = {
						'color': self.plotlyColors[actualCurveNumber],
					}
				else:
					dataDict['marker'] = {
						'color': self.plotlyColors[actualCurveNumber],
						'size': 10,
					}

				if doBar:
					pass
				else:
					dataDict['mode'] = ''
					if not self.showLines and not self.showMarkers:
						dataDict['mode'] = 'none' # 'none' is lower case !!!
					if self.showLines:
						dataDict['mode'] += '+lines'
					if self.showMarkers:
						dataDict['mode'] += '+markers'

				dataDict['name'] = 'File ' + str(index + 1) #analysisFile

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
				
				'''
				if doBar:
					myScatter = go.Bar(dataDict)
				else:
					myScatter = go.Scatter(dataDict)
				'''
				
				#myScatter = go.Scatter(dataDict)
				
				#theRet.append(myScatter)
				theRet.append(dataDict)

				if self.showMean:
					# x
					xMean, xSD, xN, xSE = None, None, None, None
					if xStatName in doNotDoMean:
						#print('xStatVals:', xStatVals)
						xMean = xStatVals[0]
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
						#print('xStatVals:', xStatVals)
						yMean = yStatVals[0]
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
					meanKey = str(condition1)
					if meanKey not in meanDataDict.keys():
						#meanDataDict[abfFile] = {}
						print('=== making meanDataDict for file index:', index, 'meanKey:', meanKey)
						meanDataDict[meanKey] = {}
						meanDataDict[meanKey]['x'] = []
						meanDataDict[meanKey]['y'] = []
						if hideMeanLines:
							meanDataDict[meanKey]['mode'] = 'markers'
						else:
							meanDataDict[meanKey]['mode'] = 'lines+markers'
						meanDataDict[meanKey]['name'] = abfFile + '_mean' # todo: need to clean up abfFile
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

					meanDataDict[meanKey]['marker']['color'].append(self.plotlyColors[actualCurveNumber])
					
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

						meanDataDict[meanKey]['error_x']['color'].append(self.plotlyColors[actualCurveNumber])
						meanDataDict[meanKey]['error_y']['color'].append(self.plotlyColors[actualCurveNumber])
						
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


		# def updatePlot() return
		return theRet
