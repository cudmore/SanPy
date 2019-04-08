import sys
sys.path.append("..") # Adds higher directory to python modules path.

import matplotlib
matplotlib.use("TkAgg")

import matplotlib.pyplot as plt

from bAnalysisApp import bAnalysis

# open an abf file into a bAnalysis object
myFile = '../data/19114001.abf'
ba = bAnalysis.bAnalysis(myFile)

# detect spikes
myThreshold = 100
myMedianFilter = 3
halfHeights = [20, 50, 80]
ba.spikeDetect(dVthresholdPos=myThreshold, medianFilter=myMedianFilter, halfHeights=halfHeights)

# ba now has a number of spikes, they are all in a list called ba.spikeDict
print('number of spikes detected:', len(ba.spikeDict))

# each spike in the list is a python dictionary
# lets look at one spike
mySpikeNumber= 5
print(ba.spikeDict[mySpikeNumber])

# each spike has a number of keys (e.g. the name of the stat) and for each of those a 'value'
for key,value in ba.spikeDict[mySpikeNumber].items():
	print(key, value)
	
for spike in ba.spikeDict:
	print(spike['thresholdVal'])

# plot spike threshold (mV) versus spike time (seconds)
