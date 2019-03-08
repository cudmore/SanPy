import matplotlib.pyplot as plt

from bAnalysis import bAnalysis

file = 'data/19114001.abf'
ba = bAnalysis.bAnalysis(file)

myThreshold = 100

ba.plotDeriv(medianFilter=3, dVthresholdPos=myThreshold)

'''
halfHeights = [20, 50, 80]
ba.spikeDetect(dVthresholdPos=myThreshold, medianFilter=3, halfHeights=halfHeights)
'''

#ba.plotSpikes()

plt.show()
