"""
Utility class to manage a list of BaNalaysis .txt files and provide dash style web objects
"""

import os, math, json, collections
import pandas as pd
import numpy as np

import plotly.colors

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

		# this is the selection in the stat list
		self.selectedStat_y = 'thresholdSec'
		self.selectedStat_x = 'peakVal'

		'''
		# keep track of x/y data that is plotted in graphs
		self.graphStat_y = ['thresholdSec', 'thresholdSec', 'thresholdSec', 'thresholdSec']
		self.graphStat_x = ['peakVal', 'peakVal', 'peakVal', 'peakVal']
		'''
		#list of what is plotted in each graph
		self.graphPlot = []
		plotDict = {}
		# 1
		plotDict['xStat'] = 'Take Off Potential (s)' #'thresholdSec'
		plotDict['yStat'] = 'AP Peak (mV)' #'peakVal'
		print('plotDict:', plotDict)
		self.graphPlot.append(plotDict)
		# 2
		plotDict = {}
		plotDict['xStat'] = 'Take Off Potential (s)'
		plotDict['yStat'] = 'AP Peak (mV)'
		print('plotDict:', plotDict)
		self.graphPlot.append(plotDict)
		# 3
		plotDict = {}
		plotDict['xStat'] = 'Take Off Potential (s)'
		plotDict['yStat'] = 'AP Peak (mV)'
		print('plotDict:', plotDict)
		self.graphPlot.append(plotDict)
		# 4
		plotDict = {}
		plotDict['xStat'] = 'Take Off Potential (s)'
		plotDict['yStat'] = 'AP Peak (mV)'
		print('plotDict:', plotDict)
		self.graphPlot.append(plotDict)

		print('self.graphPlot:', self.graphPlot)

		# list of point selected across all graphs
		# ['points': {'curveNumber': 0, 'pointNumber': 16, 'pointIndex': 16, 'x': 48.2177734375, 'y': 14.4013}]
		self.selectedPoints = None

		self.showMean = False
		self.showError = True
		self.showLines = False
		self.showMarkers = False

		self.plotlyColors = plotly.colors.DEFAULT_PLOTLY_COLORS

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
		print('bBrowser.setPlotOptions() plotOptions:', plotOptions)
		self.showMean = 'showMean' in plotOptions
		self.showLines = 'showLines' in plotOptions
		self.showMarkers = 'showMarkers' in plotOptions

	'''
	def setShowMean(self, showMean):
		"""
		if not checked, showMean is []
		if checked showMean is ['showMean']
		"""
		#print('bBrowser.setShowMean() showMean:', showMean)
		if 'showMean' in showMean:
			self.showMean = True
		else:
			self.showMean = False
	'''

	def setShow_sdev_sem(self, showSDEVID):
		"""
		if not checked, showMean is []
		if checked showMean is ['showMean']
		"""
		print('bBrowser.setShow_sdev_sem() showSDEVID:', showSDEVID)
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
		self.graphPlot[graphNum]['yStat'] = self.selectedStat_y
		self.graphPlot[graphNum]['xStat'] = self.selectedStat_x

	def loadFolder(self):
		"""
		Load a hard drive folder of bAnalysis output files (e.g. .txt files) into one Pandas dataframe (df)
		"""
		if not os.path.isdir(self.path):
			print('error: bBrowser.loadFolder() did not find path:', self.path)
			return

		columns = ['Index',
			'Condition 1', # new
			'Condition 2', # new
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

				# insert new columns not in original .txt file
				df.insert(0, 'Analysis File', file)
				df.insert(0, 'Condition 2', currIdx + 2)
				df.insert(0, 'Condition 1', currIdx + 1)

				numSpikes = len(df.index)
				firstSpikeSec = df['thresholdSec'].min()
				lastSpikeSec = df['thresholdSec'].max()
				abfFile = df.iloc[0]['file']
				abfFile = os.path.split(abfFile)[1] # get the file name from the path

				dfRow = collections.OrderedDict()
				dfRow['Index'] = currIdx + 1
				dfRow['Condition 1'] = currIdx + 1 # to start, these are FAKE
				dfRow['Condition 2'] = currIdx + 2 # to start, these are FAKE
				dfRow['Analysis File'] = file
				dfRow['ABF File'] = abfFile
				dfRow['Num Spikes'] = numSpikes
				dfRow['First Spike (Sec)'] = firstSpikeSec
				dfRow['Last Spike (Sec)'] = lastSpikeSec


				df0_list.append(dfRow)

				# BIG df with ALL spikes
				if self.df is None:
					self.df = df
				else:
					self.df = pd.concat([self.df, df], axis=0)

				currIdx += 1

		self.df0 = pd.DataFrame(df0_list)

	def getStatList(self):
		skipColumns = [''] #['file', 'spikeNumber', 'numError', 'errors', 'dVthreshold', 'medianFilter', 'halfHeights']
		retList = []
		mySpikeNumber = 0
		for column in self.df:
			if column in skipColumns:
				continue
			optionsDict = {
				'label': column,
				'value': column
			}
			retList.append(optionsDict)
		return retList

	def updatePlot(self, xStatName, yStatName):
		""" return a list of dict for plotly/dash data"""

		theRet = []

		meanDataDict = {} # dict of dict to be appended at end of loop
		
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
				
				abfFile = file['ABF File'] # use this to connect mean with line
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

				dataDict['mode'] = 'none' # 'none' is lower case !!!
				dataDict['marker'] = {
					'color': self.plotlyColors[actualCurveNumber],
					'size': 10,
				}
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
				
				theRet.append(dataDict)

				if self.showMean:
					# x
					xMean = np.nanmean(xStatVals)
					xSD = np.nanstd(xStatVals)
					xN = np.count_nonzero(~np.isnan(xStatVals))
					xSE = xSD / math.sqrt(xN - 1)
					#print('xMean:', xMean, 'xSE', xSE, 'xN:', xN)

					# y
					yMean = np.nanmean(yStatVals)
					ySD = np.nanstd(yStatVals)
					yN = np.count_nonzero(~np.isnan(yStatVals))
					ySE = ySD / math.sqrt(yN - 1)
					#print('yMean:', yMean, 'ySE', ySE, 'yN:', yN)

					if abfFile not in meanDataDict.keys():
						meanDataDict[abfFile] = {}
						#meanDataDict[abfFile]['myCurveNumber'] = actualCurveNumber
						meanDataDict[abfFile]['x'] = []
						meanDataDict[abfFile]['y'] = []
						meanDataDict[abfFile]['mode'] = 'lines+markers'
						meanDataDict[abfFile]['name'] = abfFile + '_mean' # todo: need to clean up abfFile
						meanDataDict[abfFile]['marker'] = {
							'color': [],
							'size': 13,
						}
						meanDataDict[abfFile]['line'] = {
							'color': ('rgb(0,0,0)'),
						}
						meanDataDict[abfFile]['error_x'] = {
							'type': 'data',
							'array': [],
							'visible': True,
							'color': [],
						}
						meanDataDict[abfFile]['error_y'] = {
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
					meanDataDict[abfFile]['x'].append(xMean) # xMean is a scalar
					meanDataDict[abfFile]['y'].append(yMean) # yMean is a scalar

					meanDataDict[abfFile]['marker']['color'].append(self.plotlyColors[actualCurveNumber])
					
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
						meanDataDict[abfFile]['error_x']['array'].append(xSE if self.showSE else xSD)
						meanDataDict[abfFile]['error_y']['array'].append(ySE if self.showSE else ySD)

						meanDataDict[abfFile]['error_x']['color'].append(self.plotlyColors[actualCurveNumber])
						meanDataDict[abfFile]['error_y']['color'].append(self.plotlyColors[actualCurveNumber])
						
					###
					meanDataDict[abfFile]['unselected'] = {
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
