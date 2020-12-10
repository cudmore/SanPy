import bAnalysis
import bAnalysisPlot

ba = bAnalysis.bAnalysis('../data/SAN-AP-example-Rs-change.abf')
ba.spikeDetect()

bAnalysisPlot.bPlot.plotSpikes(ba, xMin=140, xMax=145)
plt.show()
