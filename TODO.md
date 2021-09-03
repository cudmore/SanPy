1) always use ms2pnt() for
	postSpike_pnts = self.dataPointsPerMs * postSpike_ms

2) [done] add new detection param, to specify window to search for min dvdt after spike

	#
	# minima in dv/dt after spike
	#postRange = dvdt[self.spikeTimes[i]:postMinPnt]
	postSpike_ms = 10


3) [done] add a new detection param to flag low edd rate (slope)
units???

	lowestEddRate = 8

4) [done] fix save excel analysis, make sure we dump ALL detection params into sheet tab 'parameters'

5) summary spikes plugin needs to respond to changes in x-axis

6) in summary analysis plugin, turn off key press (we take no action).

7) analysisDir delete row needs to also delete uuid from h5 file

8) working on scatterplotwidget2, this will eventually not depend on sanpy but just a pandas df

- constructor takes statListDict, just use sanpy

9) Allow user to save preset detection parameters

10) mdp is currently looking in a pre TP window. This is not very 'cardiac'.
	- Add second mdp_cardiac to simply look for minimum in Vm between spikes
	- hold off on adding EDD and edd rate for this 'mdp_cardiac' ???

11) Add single spike selection to bDetectionWidget global

12) increase point size of overlay scatter plot in vm and dvdt.
	TODO: add option for user to control this point size

13) add a common QVLayout to all plugins to show: (file, start sec, stop sec, num spikes)
	Do this for: (plot scatter, error summary, summary analysis, ... OTHERS)

14) Modify ALL QTableView to retain blue selection when disabled. Like main file QTableView

15) Look into abf convert
	https://github.com/swharden/AbfConvert
