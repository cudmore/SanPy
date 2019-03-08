import matplotlib.pyplot as plt

from bAnalysis import bAnalysis

file = 'data/19114001.abf'
file = 'data/SAN-AP-example.abf'
file = 'data/SAN-AP-sample-Rs-change.abf'
ba = bAnalysis.bAnalysis(file)

myThreshold = 20

#ba.plotDeriv(medianFilter=3, dVthresholdPos=myThreshold)


halfHeights = [20, 50, 80]
ba.spikeDetect(dVthresholdPos=myThreshold, medianFilter=3, halfHeights=halfHeights)


ba.plotSpikes()

plt.show()
