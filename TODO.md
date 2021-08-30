1) always use ms2pnt() for
	postSpike_pnts = self.dataPointsPerMs * postSpike_ms

* 2) add new detection param, to specify window to search for min dvdt after spike

	#
	# minima in dv/dt after spike
	#postRange = dvdt[self.spikeTimes[i]:postMinPnt]
	postSpike_ms = 10


* 3) add a new detection param to flag low edd rate (slope)
units???

	lowestEddRate = 8

4) fix save excel analysis, make sure we dump ALL detection params into sheet tab 'parameters'

5) summary spikes plugin needs to respond to changes in x-axis

6) in summary analysis plugin, turn off key press (we take no action).

7) analysisDir delete row needs to also delete uuid from h5 file

8) working on scatterplotwidget2

- constructor takes statListDict, just use sanpy
