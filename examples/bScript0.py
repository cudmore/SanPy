import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
from matplotlib.widgets import SpanSelector
from matplotlib.widgets import CheckButtons
from matplotlib.widgets import TextBox
from matplotlib.widgets import Button

from bAnalysis import bAnalysis

file = 'data/19114001.abf'
file = 'data/SAN-AP-example.abf'
file = 'data/SAN-AP-sample-Rs-change.abf'
file = 'data/SAN-AP-example-Rs-change.abf'

ba = bAnalysis.bAnalysis(file)

myThreshold = 10

fig = ba.plotDeriv(medianFilter=3, dVthresholdPos=myThreshold)

axes = fig.axes
ax1 = axes[0]
ax2 = axes[1]

line2 = ax1.lines[1]

#cursor = Cursor(ax1, useblit=True, color='red', linewidth=2)

x = ba.abf.sweepX
y = ba.abf.sweepY

def onselect(xmin, xmax):
	print('onselect() xmin:', xmin, 'xmax:', xmax)
	indmin, indmax = np.searchsorted(x, (xmin, xmax))
	indmax = min(len(x) - 1, indmax)

	thisx = x[indmin:indmax]
	thisy = y[indmin:indmax]
	
	'''
	line2.set_data(thisx, thisy)
	ax2.set_xlim(thisx[0], thisx[-1])
	ax2.set_ylim(thisy.min(), thisy.max())
	fig.canvas.draw()
	'''
	
span = SpanSelector(ax1, onselect, 'horizontal', useblit=True,
					rectprops=dict(alpha=0.5, facecolor='yellow'))

lines = ax1.lines
rax = plt.axes([0.05, 0.4, 0.2, 0.25])
labels = [str(line.get_label()) for line in lines]
visibility = [line.get_visible() for line in lines]
myCheckButton = CheckButtons(rax, labels, visibility)

def myTextbox_callback(text):
	print('myTextbox_callback() text:', text)
	global myThreshold
	myThreshold = int(text)

axThresholdTextbox = plt.axes([0.7, 0.0, 0.1, 0.05])
initial_text = str(myThreshold)
myTextbox = TextBox(axThresholdTextbox, 'Threshold', initial=initial_text)
myTextbox.on_submit(myTextbox_callback)

def myCheckButton_callback(label):
	print('myCheckButton_callback()')
	index = labels.index(label)
	lines[index].set_visible(not lines[index].get_visible())
	plt.draw()

myCheckButton.on_clicked(myCheckButton_callback)

def myButtonCallback(event):
	print('myButtonCallback() myThreshold:', myThreshold)

	# todo: need to replot and re-grab ax1.lines
	global fig
	oldFig = fig
	fig = ba.plotDeriv(medianFilter=3, dVthresholdPos=myThreshold, fig=oldFig)
	
axMyButton = plt.axes([0.81, 0.0, 0.1, 0.05]) # [left, bottom, width, height]
myButton = Button(axMyButton, 'Threshold')
myButton.on_clicked(myButtonCallback)

if 0:
	halfHeights = [20, 50, 80]
	ba.spikeDetect(dVthresholdPos=myThreshold, medianFilter=3, halfHeights=halfHeights)


if 0:
	ba.plotSpikes()

'''
halfHeights = [20, 50, 80]
ba.spikeDetect(dVthresholdPos=myThreshold, medianFilter=3, halfHeights=halfHeights)
ba.plotClips()
'''

if 1:
	plt.show()
