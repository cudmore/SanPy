# 20210522
import os
from collections import OrderedDict

import numpy as np
import pandas as pd

import sanpy

class bExport():
	"""
		Once analysis is performed with sanpy.bAnalysis.spikeDetect(dDict),
		reports can be generated with the bExport class.

		Example reports are:

		- Generating reports as a Pandas DataFrame.
		- Saving reports as a Microsoft Excel file.
		- Saving reports as a CSV text files.
	"""
	def __init__(self, ba):
		"""
		Args:
			ba (sanpy.bAnalysis): A bAnalysis object that has had spikes detected with detectSpikes().
		"""
		self.ba = ba

	def report(self, theMin, theMax):
		"""
		Get entire spikeDict as a Pandas DataFrame.

		Args:
			theMin (float): Start seconds of the analysis
			theMax (float): Stop seconds of the analysis

		Returns:
			df: Pandas DataFrame
		"""
		if theMin is None or theMax is None:
			#return None
			theMin = 0
			theMax = self.ba.sweepX[-1]

		df = pd.DataFrame(self.ba.spikeDict)
		df = df[df['thresholdSec'].between(theMin, theMax, inclusive=True)]

		# added when trying to make scatterwidget for one file
		#print('  20210426 adding columns in bExport.report()')
		df['Condition'] = '' #df['condition1']
		df['File Number'] = '' #df['condition2']
		df['Sex'] = '' #df['condition3']
		df['Region'] = '' #df['condition4']

		# make new column with sex/region encoded
		'''
		tmpNewCol = 'RegSex'
		self.ba.masterDf[tmpNewCol] = ''
		for tmpRegion in ['Superior', 'Inferior']:
			for tmpSex in ['Male', 'Female']:
				newEncoding = tmpRegion[0] + tmpSex[0]
				regSex = self.ba.masterDf[ (self.ba.masterDf['Region']==tmpRegion) & (self.ba.masterDf['Sex']==tmpSex)]
				regSex = (self.ba.masterDf['Region']==tmpRegion) & (self.ba.masterDf['Sex']==tmpSex)
				print('newEncoding:', newEncoding, 'regSex:', regSex.shape)
				self.ba.masterDf.loc[regSex, tmpNewCol] = newEncoding
		'''

		# want this but region/sex/condition are not defined
		print('bExport.report()')
		print(df.head())
		tmpNewCol = 'CellTypeSex'
		cellTypeStr = df['cellType'].iloc[0]
		sexStr = df['sex'].iloc[0]
		print('cellTypeStr:', cellTypeStr, 'sexStr:', sexStr)
		regSexEncoding = cellTypeStr + sexStr
		df[tmpNewCol] = regSexEncoding

		minStr = '%.2f'%(theMin)
		maxStr = '%.2f'%(theMax)
		minStr = minStr.replace('.', '_')
		maxStr = maxStr.replace('.', '_')
		tmpPath, tmpFile = os.path.split(self.ba.file)
		tmpFile, tmpExt = os.path.splitext(tmpFile)
		analysisName = tmpFile + '_s' + minStr + '_s' + maxStr
		print('    minStr:', minStr, 'maxStr:', maxStr, 'analysisName:', analysisName)
		df['analysisname'] = analysisName

		return df

	def report2(self, theMin, theMax):
		"""
		Generate a report of spikes with spike times between theMin (sec) and theMax (sec).

		Args:
			theMin (float): Start seconds to save
			theMax (float): Stop seconds to save

		Returns:
			df: Pandas DataFrame
		"""
		newList = []
		for spike in self.ba.spikeDict:

			# if current spike time is out of bounds then continue (e.g. it is not between theMin (sec) and theMax (sec)
			spikeTime_sec = self.ba.pnt2Sec_(spike['thresholdPnt'])
			if spikeTime_sec<theMin or spikeTime_sec>theMax:
				continue

			spikeDict = OrderedDict() # use OrderedDict so Pandas output is in the correct order
			spikeDict['Take Off Potential (s)'] = self.ba.pnt2Sec_(spike['thresholdPnt'])
			spikeDict['Take Off Potential (ms)'] = self.ba.pnt2Ms_(spike['thresholdPnt'])
			spikeDict['Take Off Potential (mV)'] = spike['thresholdVal']
			spikeDict['AP Peak (ms)'] = self.ba.pnt2Ms_(spike['peakPnt'])
			spikeDict['AP Peak (mV)'] = spike['peakVal']
			spikeDict['AP Height (mV)'] = spike['peakHeight']
			spikeDict['Pre AP Min (mV)'] = spike['preMinVal']
			#spikeDict['Post AP Min (mV)'] = spike['postMinVal']
			#
			#spikeDict['AP Duration (ms)'] = spike['apDuration_ms']
			spikeDict['Early Diastolic Duration (ms)'] = spike['earlyDiastolicDuration_ms']
			spikeDict['Early Diastolic Depolarization Rate (dV/s)'] = spike['earlyDiastolicDurationRate'] # abb 202012
			spikeDict['Diastolic Duration (ms)'] = spike['diastolicDuration_ms']
			#
			spikeDict['Inter-Spike-Interval (ms)'] = spike['isi_ms']
			spikeDict['Spike Frequency (Hz)'] = spike['spikeFreq_hz']

			spikeDict['Cycle Length (ms)'] = spike['cycleLength_ms']

			spikeDict['Max AP Upstroke (dV/dt)'] = spike['preSpike_dvdt_max_val2']
			spikeDict['Max AP Upstroke (mV)'] = spike['preSpike_dvdt_max_val']

			spikeDict['Max AP Repolarization (dV/dt)'] = spike['postSpike_dvdt_min_val2']
			spikeDict['Max AP Repolarization (mV)'] = spike['postSpike_dvdt_min_val']

			# half-width
			for widthDict in spike['widths']:
				keyName = 'width_' + str(widthDict['halfHeight'])
				spikeDict[keyName] = widthDict['widthMs']

			# errors
			#spikeDict['numError'] = spike['numError']
			spikeDict['errors'] = spike['errors']


			# append
			newList.append(spikeDict)

		df = pd.DataFrame(newList)
		return df

	#################################################################################
	# save results (e.g. report)
	#################################################################################
	def saveReport(self, savefile, theMin=None, theMax=None, saveExcel=True, alsoSaveTxt=True, verbose=True):
		"""
		Save a spike report for detected spikes between theMin (sec) and theMax (sec)

		Args:
			savefile (str): path to xlsx file
			theMin (float): start/stop seconds of the analysis
			theMax (float): start/stop seconds of the analysis
			saveExcel (bool): xxx
			alsoSaveTxt (bool): xxx

		Return:
			str: analysisName
			df: df
		"""

		if theMin == None:
			theMin = 0
		if theMax == None:
			theMax = self.ba.abf.sweepX[-1]

		# always grab a df to the entire analysis (not sure what I will do with this)
		#df = self.ba.report() # report() is my own 'bob' verbiage

		theRet = None

		if saveExcel and savefile:
			#if verbose: print('    bExport.saveReport() saving user specified .xlsx file:', savefile)
			excelFilePath = savefile
			writer = pd.ExcelWriter(excelFilePath, engine='xlsxwriter')

			#
			# cardiac style analysis to sheet 'cardiac'
			cardiac_df = self.report2(theMin, theMax) # report2 is more 'cardiac'

			#
			# header sheet
			headerDict = OrderedDict()
			filePath, fileName = os.path.split(self.ba.file)
			headerDict['File Name'] = [fileName]
			headerDict['File Path'] = [filePath]

			headerDict['Cell Type'] = [self.ba.detectionDict['cellType']]
			headerDict['Sex'] = [self.ba.detectionDict['sex']]
			headerDict['Condition'] = [self.ba.detectionDict['condition']]

			# todo: get these params in ONE dict inside self.ba
			dateAnalyzed, timeAnalyzed = self.ba.dateAnalyzed.split(' ')
			headerDict['Date Analyzed'] = [dateAnalyzed]
			headerDict['Time Analyzed'] = [timeAnalyzed]
			headerDict['Detection Type'] = [self.ba.detectionType]
			headerDict['dV/dt Threshold'] = [self.ba.detectionDict['dvdtThreshold']]
			#headerDict['mV Threshold'] = [self.ba.mvThreshold] # abb 202012
			headerDict['Vm Threshold (mV)'] = [self.ba.detectionDict['mvThreshold']]
			#headerDict['Median Filter (pnts)'] = [self.ba.medianFilter]
			headerDict['Analysis Version'] = [sanpy.analysisVersion]
			headerDict['Interface Version'] = [sanpy.interfaceVersion]

			#headerDict['Analysis Start (sec)'] = [self.ba.startSeconds]
			#headerDict['Analysis Stop (sec)'] = [self.ba.stopSeconds]
			headerDict['Sweep Number'] = [self.ba.currentSweep]
			headerDict['Number of Sweeps'] = [self.ba.numSweeps]
			headerDict['Export Start (sec)'] = [float('%.2f'%(theMin))] # on export, x-axis of raw plot will be ouput
			headerDict['Export Stop (sec)'] = [float('%.2f'%(theMax))] # on export, x-axis of raw plot will be ouput

			# 'stats' has xxx columns (name, mean, sd, se, n)
			headerDict['stats'] = []

			for idx, col in enumerate(cardiac_df):
				headerDict[col] = []

			# mean
			theMean = cardiac_df.mean() # skipna default is True
			theMean['errors'] = ''
			# sd
			theSD = cardiac_df.std() # skipna default is True
			theSD['errors'] = ''
			#se
			theSE = cardiac_df.sem() # skipna default is True
			theSE['errors'] = ''
			#n
			theN = cardiac_df.count() # skipna default is True
			theN['errors'] = ''

			statCols = ['mean', 'sd', 'se', 'n']
			for j, stat in enumerate(statCols):
				if j == 0:
					pass
				else:
					# need to append columns to keep Excel sheet columns in sync
					#for k,v in headerDict.items():
					#	headerDict[k].append('')

					headerDict['File Name'].append('')
					headerDict['File Path'].append('')
					headerDict['Cell Type'].append('')
					headerDict['Sex'].append('')
					headerDict['Condition'].append('')
					#
					headerDict['Date Analyzed'].append('')
					headerDict['Time Analyzed'].append('')
					headerDict['Detection Type'].append('')
					headerDict['dV/dt Threshold'].append('')
					headerDict['Vm Threshold (mV)'].append('')
					#headerDict['Median Filter (pnts)'].append('')
					headerDict['Analysis Version'].append('')
					headerDict['Interface Version'].append('')
					headerDict['Sweep Number'].append('')
					headerDict['Number of Sweeps'].append('')
					headerDict['Export Start (sec)'].append('')
					headerDict['Export Stop (sec)'].append('')

				# a dictionary key for each stat
				headerDict['stats'].append(stat)
				for idx, col in enumerate(cardiac_df):
					#headerDict[col].append('')
					if stat == 'mean':
						headerDict[col].append(theMean[col])
					elif stat == 'sd':
						headerDict[col].append(theSD[col])
					elif stat == 'se':
						headerDict[col].append(theSE[col])
					elif stat == 'n':
						headerDict[col].append(theN[col])

			#print(headerDict)
			#for k,v in headerDict.items():
			#	print(k, v)

			# dict to pandas dataframe
			df = pd.DataFrame(headerDict).T
			df.to_excel(writer, sheet_name='summary')

			# set the column widths in excel sheet 'cardiac'
			columnWidth = 25
			worksheet = writer.sheets['summary']  # pull worksheet object
			for idx, col in enumerate(df):  # loop through all columns
				worksheet.set_column(idx, idx, columnWidth)  # set column width

			#
			# 'params' sheet with all detection params
			# need to convert list values in dict to string (o.w. we get one row per item in list)
			exportDetectionDict = {}
			for k, v in self.ba.detectionDict.items():
				if isinstance(v, list):
					v = f'"{v}"'
				exportDetectionDict[k] = v
			#print('  === "params" sheet exportDetectionDict:', exportDetectionDict)
			df = pd.DataFrame(exportDetectionDict, index=[0]).T # index=[0] needed when dict has all scalar values
			#print('  df:')
			#print(df)
			df.to_excel(writer, sheet_name='params')
			columnWidth = 25
			worksheet = writer.sheets['params']  # pull worksheet object
			worksheet.set_column(0, 0, columnWidth)  # set column width

			#
			# 'cardiac' sheet
			cardiac_df.to_excel(writer, sheet_name='cardiac')

			# set the column widths in excel sheet 'cardiac'
			columnWidth = 20
			worksheet = writer.sheets['cardiac']  # pull worksheet object
			for idx, col in enumerate(cardiac_df):  # loop through all columns
				worksheet.set_column(idx, idx, columnWidth)  # set column width


			#
			# entire (verbose) analysis to sheet 'bob'
			#df.to_excel(writer, sheet_name='bob')

			#
			# mean spike clip
			theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(theMin, theMax)
			try:
				first_X = theseClips_x[0] #- theseClips_x[0][0]
				#if verbose: print('    bExport.saveReport() saving mean clip to sheet "Avg Spike" from', len(theseClips), 'clips')
				df = pd.DataFrame(meanClip, first_X)
				df.to_excel(writer, sheet_name='Avg Spike')
			except (IndexError) as e:
				print('warning: got bad spike clips in saveReport(). Usually happend when 1-2 spikes')
			#print('df:', df)

			writer.save()

		#
		# save a csv text file
		#
		analysisName = ''
		if alsoSaveTxt:
			# this also saves
			analysisName, df0 = self.getReportDf(theMin, theMax, savefile)

			#
			# save mean spike clip

			theseClips, theseClips_x, meanClip = self.ba.getSpikeClips(theMin, theMax)
			if len(theseClips_x) == 0:
				pass
			else:
				first_X = theseClips_x[0] #- theseClips_x[0][0]
				first_X = np.array(first_X)
				first_X /= self.ba.abf.dataPointsPerMs # pnts to ms
				#if verbose: print('    bExport.saveReport() saving mean clip to sheet "Avg Spike" from', len(theseClips), 'clips')
				#dfClip = pd.DataFrame(meanClip, first_X)
				dfClip = pd.DataFrame.from_dict({
					'xMs': first_X,
					'yVm': meanClip
					})
				# load clip based on analysisname (with start/stop seconds)
				analysisname = df0['analysisname'].iloc[0] # name with start/stop seconds
				print('bExport.saveReport() analysisname:', analysisname)
				#print('analysisname:', analysisname)
				clipFileName = analysisname + '_clip.csv'
				tmpPath, tmpFile = os.path.split(savefile)
				tmpPath = os.path.join(tmpPath, 'analysis')
				# dir is already created in getReportDf
				if not os.path.isdir(tmpPath):
					os.mkdir(tmpPath)
				clipSavePath = os.path.join(tmpPath, clipFileName)
				print('    clipSavePath:', clipSavePath)
				dfClip.to_csv(clipSavePath)
			#
			theRet = df0
		#
		return analysisName, theRet

	def getReportDf(self, theMin, theMax, savefile):
		"""
		Get spikes as a Pandas DataFrame, one row per spike.

		Args:
			theMin (float): xxx
			theMax (float): xxx
			savefile (str): .xls file path

		Returns:
			df: Pandas DataFrame
		"""
		filePath, fileName = os.path.split(os.path.abspath(savefile))

		# make an analysis folder
		filePath = os.path.join(filePath, 'analysis')
		if not os.path.isdir(filePath):
			print('    getReportDf() making output folder:', filePath)
			os.mkdir(filePath)

		textFileBaseName, tmpExtension = os.path.splitext(fileName)
		textFilePath = os.path.join(filePath, textFileBaseName + '.csv')

		# save header
		textFileHeader = OrderedDict()
		textFileHeader['file'] = self.ba.file # this is actuall file path
		#textFileHeader['condition1'] = self.ba.condition1
		#textFileHeader['condition2'] = self.ba.condition2
		#textFileHeader['condition3'] = self.ba.condition3
		textFileHeader['cellType'] = self.ba.detectionDict['cellType']
		textFileHeader['sex'] = self.ba.detectionDict['sex']
		textFileHeader['condition'] = self.ba.detectionDict['condition']
		#
		textFileHeader['dateAnalyzed'] = self.ba.dateAnalyzed
		textFileHeader['detectionType'] = self.ba.detectionType
		textFileHeader['dvdtThreshold'] = [self.ba.detectionDict['dvdtThreshold']]
		textFileHeader['mvThreshold'] = [self.ba.detectionDict['mvThreshold']]
		#textFileHeader['medianFilter'] = self.ba.medianFilter
		textFileHeader['startSeconds'] = '%.2f'%(theMin)
		textFileHeader['stopSeconds'] = '%.2f'%(theMax)
		#textFileHeader['startSeconds'] = self.ba.startSeconds
		#textFileHeader['stopSeconds'] = self.ba.stopSeconds
		textFileHeader['currentSweep'] = self.ba.currentSweep
		textFileHeader['numSweeps'] = self.ba.numSweeps
		#textFileHeader['theMin'] = theMin
		#textFileHeader['theMax'] = theMax

		# 20210125, this is not needed, we are saviing pandas df below ???
		headerStr = ''
		for k,v in textFileHeader.items():
			headerStr += k + '=' + str(v) + ';'
		headerStr += '\n'
		#print('headerStr:', headerStr)
		with open(textFilePath,'w') as f:
			f.write(headerStr)

		#print('Saving .txt file:', textFilePath)
		df = self.report(theMin, theMax)

		# we need a column indicating (path), the original .abf file
		# along with (start,stop) which should make this analysis unique?
		minStr = '%.2f'%(theMin)
		maxStr = '%.2f'%(theMax)
		minStr = minStr.replace('.', '_')
		maxStr = maxStr.replace('.', '_')
		tmpPath, tmpFile = os.path.split(self.ba.file)
		tmpFile, tmpExt = os.path.splitext(tmpFile)
		analysisName = tmpFile + '_s' + minStr + '_s' + maxStr
		print('    minStr:', minStr, 'maxStr:', maxStr, 'analysisName:', analysisName)
		df['analysisname'] = analysisName

		# should be filled in by self.ba.report
		#df['Condition'] = 	df['condition1']
		#df['File Number'] = 	df['condition2']
		#df['Sex'] = 	df['condition3']
		#df['Region'] = 	df['condition4']
		df['filename'] = [os.path.splitext(os.path.split(x)[1])[0] for x in 	df['file'].tolist()]

		#
		print('    bExport.getReportDf() saving text file:', textFilePath)
		#df.to_csv(textFilePath, sep=',', index_label='index', mode='a')
		df.to_csv(textFilePath, sep=',', index_label='index', mode='w')

		return analysisName, df
