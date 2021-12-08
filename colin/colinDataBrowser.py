"""
Browse raw data and analysis from a colinAnalysis.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import ipywidgets as widgets
import IPython.display

class colinDataBrowser():
	def __init__(self, ca):
		"""
		Display a data browser.

		Args:
			ca (colinAnalysis)
		"""

		self._ca = ca

		self.zoomSec1 = 10.0
		self.zoomSec2 = 0.2

		self._currentPeakIdx = 0

		self._fileList = self._ca.fileList
		self._currentFileIndex = 0
		self._selectedFile = None

		self.currentAnalysis = None

		if len(self._fileList) == 0:
			print('error: did not find any files in path:', self._ca._folderPath)

		else:
			self.setFileIndex(self._currentFileIndex)

			self.initGui()
			self.refreshPlot()

	def setFileIndex(self, fileIdx):
		self._currentFileIndex = fileIdx
		self._selectedFile = self._fileList[fileIdx]  # user selected files
		self.currentAnalysis = self._ca.getFile(fileIdx)

		self._currentPeakIdx = 0

	def on_zoom1_change(self, n):
		# print('on_zoom1_change')
		self.zoomSec1 = n['new']
		self.refreshPlot()

	def on_zoom2_change(self, n):
		# print('on_zoom2_change')
		self.zoomSec2 = n['new']
		self.refreshPlot()

	def updateMyOut(self, peakPnt:int = None):
		if peakPnt is None:
			peakPnt = self._currentPeakIdx

		df = self.currentAnalysis.analysisDf
		riseTime_ms = self.currentAnalysis.getValue('riseTime_ms', peakPnt)
		riseTime_ms = round(riseTime_ms,2)
		myHeight = self.currentAnalysis.getValue('myHeight', peakPnt)
		myHeight = round(myHeight,2)
		with self.myOut:
			IPython.display.clear_output()
			print(f'Peak {peakPnt} Amp(pA) {myHeight} Rise Time (ms) {riseTime_ms}')

	def updateMyOut2(self, s):
		with self.myOut:
			IPython.display.clear_output()
			print(s)

	def on_point_slider_change(self, n):
		"""
		Respond to user sliding point slider.

		n (dict): Dict with things like n['new']
		"""
		self._currentPeakIdx = n['new']  # new value

		self.updateMyOut()

		self.refreshPlot()

	def setAccept(self, newValue, peakIdx=None):
		if peakIdx is None:
			peakIdx = self._currentPeakIdx
		#self._ca.getDataFrame().loc[peakIdx, 'accept'] = newValue
		self.currentAnalysis.setValue(peakIdx, 'accept', newValue)

	def on_accept_button(self, e):
		self.setAccept(True)  # will use current gui index

		s = f'peak {self._currentPeakIdx} is now "Accept"'
		self.updateMyOut2(s)

		self.refreshPlot()

	def on_reject_button(self, e):
		self.setAccept(False)  # will use current gui index

		s = f'peak {self._currentPeakIdx} is now "Reject"'
		self.updateMyOut2(s)

		self.refreshPlot()

	def on_prev_button(self, e):
		self._currentPeakIdx -= 1
		if self._currentPeakIdx < 0:
			self._currentPeakIdx = 0

		self.updateMyOut()

		self.refreshPlot()

	def on_next_button(self, e):
		self._currentPeakIdx += 1
		if self._currentPeakIdx > self.currentAnalysis.numPeaks - 1:
			self._currentPeakIdx = self.currentAnalysis.numPeaks - 1

		self.updateMyOut()

		self.refreshPlot()

	def on_save_button(self, e):
		resultsPath = self.currentAnalysis.save()
		str = f'Saved {resultsPath}'
		self.updateMyOut2(str)

	def on_select_file(self, event):
		#newStr = event['new']  # a tuple of strings
		fileIdx = event['owner'].index  # index of user selection
		self.setFileIndex(fileIdx)

		self.refreshPlot()

	def on_detect_button(self, event):
		#print(event)
		thresholdValue = self.thresholdSpinBox.value
		#print(thresholdValue, type(thresholdValue))

		detectionDict = self.currentAnalysis.detectionParams
		detectionDict['threshold'] = thresholdValue
		self.currentAnalysis.detect(detectionDict=detectionDict)

		self._currentPeakIdx = 0  # important

		self.refreshPlot()

	def initGui(self):
		self.sweepX = self.currentAnalysis.sweepX
		self.sweepY = self.currentAnalysis.sweepY
		self.sweepC = self.currentAnalysis.sweepC

		# list of files
		self._selectedFile = self._fileList[0]
		self.selectFiles = widgets.Select(
		    options=self._fileList,
		    value=self._selectedFile, # select all
		    rows=8,
		    description='',
		    disabled=False
		)
		self.selectFiles.observe(self.on_select_file, names='value')

		self.thresholdSpinBox = widgets.BoundedFloatText(
		    value=7.5,
		    min=-1e6,
		    max=1e6,
		    step=0.1,
		    description='Threshold (pA)',
		    disabled=False
		)

		detectButton = widgets.Button(
		    description='Detect',
		    disabled=False,
		    button_style='success', # 'success', 'info', 'warning', 'danger' or ''
		    tooltip='xxx',
		    #icon='check' # (FontAwesome names without the `fa-` prefix)
		)
		detectButton.on_click(self.on_detect_button)

		fileBox = widgets.HBox([self.selectFiles, self.thresholdSpinBox, detectButton])
		display(fileBox)

		numSubplot = 3
		self.fig, self.axs = plt.subplots(numSubplot, 1, figsize=(8, 6))
		self.axs[0].grid(True)
		self.axs[1].grid(True)
		self.axs[2].grid(True)

		# right axis for DAQ0
		self.rightAxis = self.axs[0].twinx()

		# selected point slider
		min = 0
		max = self.currentAnalysis.numPeaks - 1
		myPointSlider = widgets.IntSlider(min=min, max=max, step=1,
										   value=self._currentPeakIdx,
										   continuous_update=False,
										  description='Peak Number')
		myPointSlider.observe(self.on_point_slider_change, names='value')

		#
		min = 0.1
		max = self.sweepX[-1]
		myZoomSlider1 = widgets.FloatSlider(min=min, max=max, step=0.1,
										   value=self.zoomSec1,
										   continuous_update=False,
										  description='Zoom 1 (Sec)')
		myZoomSlider1.observe(self.on_zoom1_change, names='value')

		min = 0.1
		max = self.sweepX[-1]
		myZoomSlider2 = widgets.FloatSlider(min=min, max=max, step=0.1,
										   value=self.zoomSec2,
										   continuous_update=False,
										  description='Zoom 2 (Sec)')
		myZoomSlider2.observe(self.on_zoom2_change, names='value')

		hBox = widgets.HBox([myPointSlider, myZoomSlider1, myZoomSlider2])
		display(hBox)

		# prev and next buttons
		prevButton = widgets.Button(description='<')
		prevButton.on_click(self.on_prev_button)

		nextButton = widgets.Button(description='>')
		nextButton.on_click(self.on_next_button)

		# accept and reject
		acceptButton = widgets.Button(description='Accept')
		acceptButton.on_click(self.on_accept_button)

		rejectButton = widgets.Button(description='Reject')
		rejectButton.on_click(self.on_reject_button)

		hBox = widgets.HBox([prevButton, nextButton, acceptButton, rejectButton])
		display(hBox)

		saveButton = widgets.Button(description='Save')
		saveButton.on_click(self.on_save_button)

		# output widget so we can give feedback like selected pnt number
		self.myOut = widgets.Output()

		hBox = widgets.HBox([saveButton, self.myOut])
		display(hBox)

	def refreshPlot(self):
		#self.replotScatter()  # needed for accept/reject
		#self.replotScatter_selection()

		self.sweepX = self.currentAnalysis.sweepX
		self.sweepY = self.currentAnalysis.sweepY
		self.sweepC = self.currentAnalysis.sweepC
		self.sweepY_filtered = self.currentAnalysis.sweepY_filtered

		peakNumber = self._currentPeakIdx

		df = self.currentAnalysis.analysisDf

		peaks = df['peak_pnt']  #analysis['peaks']
		acceptList = df['accept']  # analysis['accept']  # todo: update to df

		# peak we are looking at
		xPeak = df.loc[peakNumber, 'peak_pnt']  # peaks[peakNumber]  # point of the peak
		xPeakSec = df.loc[peakNumber, 'peak_sec']  # self._pnt2Sec(xPeak)
		yPeak = df.loc[peakNumber, 'peak_val']  # self.sweepY[xPeak]

		#
		# all data
		self.axs[0].clear()
		self.axs[0].plot(self.sweepX, self.sweepY, '-', linewidth=0.5)

		# plot peaks
		xPlotPeakSec0 = df['peak_sec']  # self._pnt2Sec(peaks)
		yPlotPeakSec0 = df['peak_val']  # self.sweepY[peaks]
		self.axs[0].scatter(xPlotPeakSec0, yPlotPeakSec0, c='k', marker='.', zorder=999)

		self.rightAxis.clear()
		self.rightAxis.plot(self.sweepX, self.sweepC, 'r-', linewidth=0.5)

		# intermeidate zoom
		mySelectColor = 'k' if acceptList[peakNumber] else 'r'

		#
		# zoom 1
		self.axs[1].clear()
		xMinSec = xPeakSec - (self.zoomSec1 / 2)
		xMaxSec = xPeakSec + (self.zoomSec1 / 2)
		xMaskPnts = (self.sweepX >= xMinSec) & (self.sweepX <= xMaxSec)
		#yRange = max(self.sweepY[xMaskPnts]) - min(self.sweepY[xMaskPnts]) # used for rectangle
		xClip1 = self.sweepX[xMaskPnts]
		yClip1 = self.sweepY[xMaskPnts]
		self.axs[1].plot(self.sweepX[xMaskPnts], self.sweepY_filtered[xMaskPnts], '-r', linewidth=0.5)
		# one peak
		self.axs[1].scatter(xPeakSec, yPeak, c=mySelectColor, marker='x')

		# find and plot visible peaks by reducing df
		df2 = df[ (df['peak_sec']>=xMinSec) & (df['peak_sec']<=xMaxSec)]
		xPlotPeakSec = df2['peak_sec']
		yPlotPeakSec = df2['peak_val']
		myColors = ['k' if x else 'r' for x in df2['accept']]
		self.axs[1].scatter(xPlotPeakSec, yPlotPeakSec, c=myColors, zorder=999)

		# h line with threshold
		threshold = self.currentAnalysis.detectionParams['threshold']
		self.axs[1].hlines(threshold, xMinSec, xMaxSec, color='r', linestyles='--')

		#
		# zoom 2 tight zoom
		self.axs[2].clear()
		xMinSec2 = xPeakSec - (self.zoomSec2 / 2)
		xMaxSec2 = xPeakSec + (self.zoomSec2 / 2)

		xMaskPnts2 = (self.sweepX >= xMinSec2) & (self.sweepX <= xMaxSec2)
		xClip2 = self.sweepX[xMaskPnts2] # just points within view
		yClip2 = self.sweepY[xMaskPnts2]

		#self.axs[2].plot(self.sweepX[xMaskPnts2], self._ca.sweepY[xMaskPnts2], '-')
		self.axs[2].plot(self.sweepX[xMaskPnts2], self.sweepY_filtered[xMaskPnts2], '-r', linewidth=0.5)

		# find and plot visible peaks by reducing df
		df2 = df[ (df['peak_sec']>=xMinSec2) & (df['peak_sec']<=xMaxSec2)]
		xPlotPeakSec = df2['peak_sec']
		yPlotPeakSec = df2['peak_val']
		myColors = ['k' if x else 'r' for x in df2['accept']]
		self.axs[2].scatter(xPlotPeakSec, yPlotPeakSec, c=myColors, zorder=999)

		self.axs[2].scatter(xPeakSec, yPeak, c=mySelectColor, marker='x')  # one peak

		# for debugging detection
		fullWidth_left_pnt = df['fullWidth_left_pnt']
		fullWidth_left_val = df['fullWidth_left_val']
		self.axs[2].scatter(fullWidth_left_pnt, fullWidth_left_val, c='g', marker='x', zorder=999)

		# hw 50
		halfWidths = [20, 50, 80]
		for halfWidth in halfWidths:
			hwBase = 'hw' + str(halfWidth) + '_'
			hw_val = df[hwBase+'val']
			hw_left_sec = df[hwBase+'left_sec']
			hw_right_sec = df[hwBase+'right_sec']
			self.axs[2].hlines(hw_val, hw_left_sec, hw_right_sec)

		# plot foot after backing up to 0 crossnig in derivative
		#df = self.getDataFrame()
		xPlotFoot = df2['foot_sec']
		yPlotFoot = df2['foot_val']
		self.axs[2].scatter(xPlotFoot, yPlotFoot, c='g', zorder=999)

		# this wil break user zooming ???
		self.axs[2].set_xlim(xMinSec2, xMaxSec2)

		# gray rectangle (on middle plot)
		rectWidth = max(xClip2) - min(xClip2)  # to match tighter view
		rectHeight = max(yClip1) - min(yClip1)
		xRectPos = min(xClip2)  # to match tighter view (3)
		yRectPos = min(yClip1)
		self.axs[1].add_patch(Rectangle((xRectPos, yRectPos), rectWidth, rectHeight, facecolor="silver"))

		# gray rectangle (on top plot)
		rectWidth = max(xClip1) - min(xClip1)  # to match middle view
		rectHeight = max(self.sweepY) - min(self.sweepY)
		xRectPos = min(xClip1)  # to match tighter view (3)
		yRectPos = min(self.sweepY)
		self.axs[0].add_patch(Rectangle((xRectPos, yRectPos), rectWidth, rectHeight, facecolor="silver"))

		# refresh
		self.fig.canvas.draw()
