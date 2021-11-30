"""
A Jupyter scatter widget
"""
import pandas as pd
import numpy as np

import seaborn as sns
import ipywidgets as widgets
import IPython.display
import matplotlib.pyplot as plt

class myScatterWidget():
	def __init__(self, df, statList:list=None, acceptCol='accept', styleCol=None, hueCols=None):
		"""
		statList (list): List of str taken from columns in df
		df (DataFrame): Pandas DataFrame with one value for each row
		acceptCol (str): Column in df to code accept/reject (bool)
		styleCol (str):
		hueCols (list): List of columns to use as Seaborn hue (colors and grouping)
		"""
		if statList is None:
			statList = df.columns  # all column
		self._statList = statList
		self._df = df
		self._plotDf = df  # keep track of what we are plotting

		self._acceptCol = acceptCol
		self._styleCol = styleCol
		self._hueCols = hueCols

		self._selectedHueCol = None
		self._selectedHues = None  # tuple
		self.selectFiles = None  # part of the interface
		if self._hueCols is not None:
			self.setHue(self._hueCols[0])

		xStatIndex = 5
		yStatIndex = 6
		self._xStat = statList[xStatIndex]
		self._yStat = statList[yStatIndex]

		self._plotOptions = {
			'Show Reject': True,
			'Legend': True,
			'Cumulative Histograms': False,
			'Linear Fit': False,
		}

		self.initGui()
		self.refreshScatter()

	@property
	def plotOptions(self):
		return self._plotOptions

	def setHue(self, hueCol):
		"""
		Set the hue to a given column name. Hue controls group by and plot colors

		Argse:
			hueCol (str): hue column
		"""
		if self._hueCols is not None:
			self._selectedHueCol = hueCol
			self._selectedHues = tuple(self._df[hueCol].unique())
			if self.selectFiles is not None:
				self.selectFiles.options = self._selectedHues  # update list in interface
				# does not work
				#self.selectFiles.value = self._selectedHues  # select all possible

	def on_x_stat_select(self, event):
		"""
		User selected a new x stat
		"""
		newStat = event['new']
		self._xStat = newStat
		self.updateStats()
		self.refreshScatter()

	def on_y_stat_select(self, event):
		"""
		User selected a new y stat
		"""
		newStat = event['new']
		self._yStat = newStat
		self.updateStats()
		self.refreshScatter()

	def updateStats(self):
		with self.myOutStat:
			IPython.display.clear_output()
			df = self.getStats()
			display(df)

	def on_checkbox(self, event):
		description = event['owner'].description
		newValue = event['new']
		try:
			self.plotOptions[description] = newValue
		except (KeyError) as e:
			print(e)
		self.updateStats()
		self.refreshScatter()

	'''
	def on_legend_checkbox(self, event):
		newValue = event['new']
		self.plotOptions['showLegend'] = newValue
		self.updateStats()
		self.refreshScatter()
	'''

	def on_select_hue0(self, event):
		"""
		user selected a hue from self._hueCols
		"""
		newValue = event['new']
		self.setHue(newValue)
		self.updateStats()
		self.refreshScatter()

	def on_select_hue(self, event):
		"""
		User selected a number of unique values from current hue (like a list of file names, genotype, or sex)
		"""
		newValue = event['new']  # a tuple of strings
		self._selectedHues = newValue
		self.updateStats()
		self.refreshScatter()

	def on_scatter_pick(self, event):
		"""
		User clicked a point in scatter plot

		Args:
			e (matplotlib.backend_bases.PickEvent)
		"""
		# we need to use 'with' so error and print() show up in the jupyter/browser
		with self.myScatterOut:
			IPython.display.clear_output()
			ind = event.ind  # list of points withing specified tolerance
			ind = ind[0]
			#offsets = event.artist.get_offsets()

			s = ''
			for hueCol in self._hueCols:
				value = self._plotDf.loc[ind, hueCol]
				s += f'{hueCol}: {value}'
				s += ' '
			print(s)

	def updateScatterOut(self, s):
		"""
		Give feedback on scatter selection.
		"""
		with self.myScatterOut:
			IPython.display.clear_output()
			print(s)

	def reduceDf(self):
		df = df = self._df
		if not self.plotOptions['Show Reject']:
			df = df[ df[self._acceptCol]==True ]
		# reduce on selected hue
		if self._hueCols is not None:
			df = df[ df[self._selectedHueCol].isin(self._selectedHues) ]
		return df

	def getFit(self):
		"""
		Return a linear fit for each unique hue value

		Returns:
			List of dict of {m, b}

		Note correcting for 1 pnts difference for stats like freq and isi
		"""
		retList = []
		df = self.reduceDf()

		# unique entries for our hue column (corresponds to stat groupby)
		uniqueList = df[self._selectedHueCol].unique()

		xStat = self._xStat
		yStat = self._yStat
		for unique in uniqueList:
			uniqueDf = df[ df[self._selectedHueCol]==unique ]
			x = uniqueDf[xStat]
			y = uniqueDf[yStat]

			#x = x[~np.isnan(x)]
			#y = y[~np.isnan(y)]

			# correct for 1 pnt difference for (freq, isi)
			if len(x) == len(y)+1:
				x = x[1:]
			if len(y) == len(x)+1:
				y = y[1:]

			# pairwise mask out nan in either x or y
			mask = ~np.isnan(x) & ~np.isnan(y)
			x = x[mask]
			y = y[mask]

			if len(x) != len(y):
				print(f'error in getFit(): {unique} {len(x)} {len(y)}')

			m, b = np.polyfit(x, y, 1)
			retDict = {'m':m, 'b':b}
			retList.append(retDict)

		return retList

	def getStats(self):
		"""
		"""
		xStat = self._xStat
		yStat = self._yStat

		df = self.reduceDf()

		badObjects = [object, bool]
		if df[xStat].dtype in badObjects or df[yStat].dtype in badObjects:
			return 'Please select a stat with numbers'

		theseStats = ['count', 'min', 'max', 'median', 'mean', 'std', 'sem']
		dfAgg = df.groupby(self._selectedHueCol).agg(
			{
				xStat: theseStats,
				yStat: theseStats,
			}
		)
		return dfAgg

	def initGui(self):

		selectWidgetHeight = '175px'

		# x stat list
		xStatList = widgets.Select(
		    options=self._statList,
		    value=self._statList[0],
		    # rows=10,
		    description='',
		    disabled=False,
			layout={'height': selectWidgetHeight}
		)
		xStatList.observe(self.on_x_stat_select, names='value')

		# y stat list
		yStatList = widgets.Select(
		    options=self._statList,
		    value=self._statList[0],
		    # rows=10,
		    description='',
		    disabled=False,
			layout={'height': selectWidgetHeight}
		)
		yStatList.observe(self.on_y_stat_select, names='value')

		# corresponds to hue
		if self._hueCols is not None:
			# popup of hue cols
			hueDropdown = widgets.Dropdown(
			    options=self._hueCols,
			    value=self._hueCols[0],
			    description='',
			    disabled=False,
			)
			hueDropdown.observe(self.on_select_hue0, names='value')
			# list of unique objects (from df) for a given hue
			self.selectFiles = widgets.SelectMultiple(
			    options=self._selectedHues,
			    value=self._selectedHues, # select all
			    rows=8,
			    description='',
			    disabled=False
			)
			self.selectFiles.observe(self.on_select_hue, names='value')

			hueBox = widgets.VBox([hueDropdown, self.selectFiles])

		hBox = widgets.HBox([xStatList, yStatList, hueBox])
		display(hBox)

		#
		checkboxList = []
		for key,value in self.plotOptions.items():
			aCheckbox = widgets.Checkbox(
			    description=key,
			    value=value,
			    disabled=False,
			    indent=False
			)
			aCheckbox.observe(self.on_checkbox, names='value')
			checkboxList.append(aCheckbox)

		hBox = widgets.HBox(checkboxList)
		display(hBox)

		# output to show one line update
		self.myScatterOut = widgets.Output()
		hBox = widgets.HBox([self.myScatterOut])
		display(hBox)

		# scatter plot
		self.scatterFig = plt.figure(figsize=(6, 6))
		#self.scatterFig.set_tight_layout(True)

		self.gs = self.scatterFig.add_gridspec(2, 2,  width_ratios=(7, 2), height_ratios=(2, 7),
											left=0.1, right=0.9, bottom=0.1, top=0.9,
											wspace=0.05, hspace=0.05)

		self.axScatter = self.scatterFig.add_subplot(self.gs[1, 0])

		self.scatterFig.canvas.mpl_connect('pick_event', self.on_scatter_pick)

		# x/y hist
		marginalHist = True
		if marginalHist:
			self.axHistX = self.scatterFig.add_subplot(self.gs[0, 0], sharex=self.axScatter)
			self.axHistY = self.scatterFig.add_subplot(self.gs[1, 1], sharey=self.axScatter)
			#
			self.axHistX.spines['right'].set_visible(False)
			self.axHistX.spines['top'].set_visible(False)
			self.axHistY.spines['right'].set_visible(False)
			self.axHistY.spines['top'].set_visible(False)

		# output widgets to show table of x/y stats
		self.myOutStat = widgets.Output()
		hBox = widgets.HBox([self.myOutStat])
		display(hBox)

	def refreshScatter(self):

		df = self.reduceDf()

		xStat = self._xStat
		yStat = self._yStat

		xData = df[xStat]
		yData = df[yStat]

		badObjects = [object, bool]
		if xData.dtype in badObjects or yData.dtype in badObjects:
			with self.myScatterOut:
				IPython.display.clear_output()
				print('Please select a stat with numbers')
			#return

		self._plotDf = df

		# clear everybody
		self.axScatter.clear()
		self.axHistX.clear()
		self.axHistY.clear()

		palette = 'deep' # for hue

		style = self._acceptCol
		hue = self._selectedHueCol  # can be none

		#self.axScatter.set_xlabel(xStat)
		#self.axScatter.set_ylabel(yStat)

		# histograms
		marginalHist = True
		if marginalHist:
			bins = 'doane'

			element = 'bars'
			fill = True
			cumulative = False
			stat = 'count'
			common_norm = False

			if self.plotOptions['Cumulative Histograms']:
				element="step"
				fill=False
				cumulative=True
				stat="density"
				common_norm=False

			# x histogram
			self.axHistX = sns.histplot(x=xStat, data=df,
										hue=hue, palette=palette,
										bins=bins, legend=False,
										element=element, fill=fill, cumulative=cumulative, stat=stat, common_norm=common_norm,
										ax=self.axHistX)
			#self.axHistX.set_xticklabels([])
			self.axHistX.set(xlabel=None)

			# y histogram
			self.axHistY = sns.histplot(y=yStat, data=df,
										hue=hue, palette=palette,
										bins=bins, legend=False,
										element=element, fill=fill, cumulative=cumulative, stat=stat, common_norm=common_norm,
										ax=self.axHistY)
			#self.axHistY.set(yticklabels=[])
			self.axHistY.set(ylabel=None)

		# scatter

		legend = self.plotOptions['Legend']
		if xStat in self._hueCols:
			# box plot
			# assuming hue has limited number of options, like (sex, genotype, etc)
			self.axScatter = sns.boxplot(x=xStat, y=yStat, data=df,
			            	hue=hue, palette=palette,
							whis=[0, 100], width=.6,
							ax=self.axScatter,
							)

			# Add in points to show each observation
			sns.stripplot(x=xStat, y=yStat, data=df,
			            	hue=hue, palette=palette,
			             	size=4,
						 	#color=".3",
							linewidth=0,
							ax=self.axScatter,
							)
		else:
			# default is scatter plot
			self.axScatter = sns.scatterplot(x=xStat, y=yStat, data=df,
						hue=hue, palette=palette,
						#style=style,
						legend=legend,
						picker=5,
						ax=self.axScatter,
						#facet_kws={"legend_out": True},
						)

		# move legend outside plot
		self.axScatter.legend(loc='center left', bbox_to_anchor=(1.0, 1.2), ncol=1)

		# fit a line
		if self.plotOptions['Linear Fit']:
			fitList = self.getFit()
			for fit in fitList:
				m = fit['m']
				b = fit['b']
				x = df[xStat]
				self.axScatter.plot(df[xStat], m*df[xStat] + b)

		# refresh
		self.scatterFig.canvas.draw()

if __name__ == '__main__':
	path = '/media/cudmore/data/colin/21n10003_full.csv'
	df = pd.read_csv(path)
	statList = df.columns
	msw = myScatterWidget(statList, df)
