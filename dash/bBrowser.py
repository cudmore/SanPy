"""
Utility class to manage a list of BaNalaysis .txt files and provide dash style web objects
"""

import os, collections
import pandas as pd

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
		
		self.df0 = None # small dataframe with list of files loaded
		
		self.df = None # massive dataframe with all spikes across all file
		
		self.selectedStat_y = 'thresholdSec'
		self.selectedStat_x = 'peakVal'
		
		self.selectedPoints = []
		
		'''
		# keep track of x/y data that is plotted in graphs
		self.graphStat_y = ['thresholdSec', 'thresholdSec', 'thresholdSec', 'thresholdSec']
		self.graphStat_x = ['peakVal', 'peakVal', 'peakVal', 'peakVal']
		'''
		
	def setSelectedRows(self, rows):
		self.selectedRows = rows
		
	def selectedPoints(self, points):
		self.selectedPoints = points
		
	def loadFolder(self):
		"""
		Load a hard drive folder of bAnalysis output files (e.g. .txt files) into one Pandas dataframe (df)
		"""
		if not os.path.isdir(self.path):
			print('error: bBrowser.loadFolder() did not find path:', self.path)
			return
			
		columns = ['Index',
			'Analysis File',
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
				df.insert(0, 'Analysis File', file)

				numSpikes = len(df.index)
				firstSpikeSec = df['thresholdSec'].min()
				lastSpikeSec = df['thresholdSec'].max()
				abfFile = df.iloc[0]['file']
				#abfFile = os.path.split(abfFile)[1] # get the file name from the path
				
				dfRow = collections.OrderedDict()
				dfRow['Index'] = currIdx + 1
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
		
		if xStatName and yStatName:
			for index, row in self.df0.iterrows():
				#print(index, row['ABF File'])
				#print(index, row)
		
				analysisFile = row['Analysis File']
				abfFile = row['ABF File']

				thisFileRows = self.df.loc[self.df['Analysis File'] == analysisFile]

				# get rows in self.df corresponding to abfFile
				xStatVals = thisFileRows[xStatName]
				yStatVals = thisFileRows[yStatName]
			
				dataDict = {}
				dataDict['x'] = xStatVals
				dataDict['y'] = yStatVals
				dataDict['mode'] = 'markers'
				dataDict['name'] = analysisFile + ':' + abfFile
			
				theRet.append(dataDict)
			
			# append selection
			
		return theRet
