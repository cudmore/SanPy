"""
See:
"""
from typing import Union
from pprint import pprint

import pyabf
path = 'data/20191009_0005.abf'
path = '/Users/cudmore/data/theanne-griffith/07.20.21/2021_07_20_0013.abf'
abf = pyabf.ABF(path)

class epochTable():
	def __init__(self, abf : pyabf.ABF):
		
		self._epochList = []

		print('sweepX pnts:', len(abf.sweepX))

		#print('===')
		#pprint(vars(abf.sweepEpochs))
		#print('===')
		
		dataPointsPerMs = abf.dataPointsPerMs
		"""To convert point to seconds"""

		# sweepEpochs is type "pyabf.waveform.EpochSweepWaveform"
		for epochIdx, p1 in enumerate(abf.sweepEpochs.p1s):
			p2 = abf.sweepEpochs.p2s[epochIdx]  # stop point of each pulse
			epochLevel = abf.sweepEpochs.levels[epochIdx]
			epochType = abf.sweepEpochs.types[epochIdx]
			pulseWidth = abf.sweepEpochs.pulseWidths[epochIdx]
			pulsePeriod = abf.sweepEpochs.pulsePeriods[epochIdx]
			digitalState = abf.sweepEpochs.pulsePeriods[epochIdx]
			##print(f"epoch index {epochIdx}: at point {p1} there is a {epochType} to level {epochLevel}")
			
			epochDict = {
				'index': epochIdx,
				'type': epochType,
				'startPoint': p1,  # point the epoch starts
				'stopPoint': p2,  # point the epoch starts
				'level': epochLevel,
				'pulseWidth': pulseWidth,
				'pulsePeriod': pulsePeriod,
				'digitalState': digitalState,  # list of 0/1 for 8x digital states
			}
			self._epochList.append(epochDict)

	def findEpoch(self, pnt : int) -> Union[None, int]:
		"""Return epoch index for a point in recording.

		Stop points are always the same as next epoch start point.
		Be sure to use '<' like pnt<stopPnt to get epoch index correct.
		"""
		for epochIdx, epoch in enumerate(self._epochList):
			startPoint = epoch['startPoint']
			stopPoint = epoch['stopPoint']
			if pnt >= startPoint and pnt < stopPoint:
				return epochIdx
		#
		return None

et = epochTable(abf)
pprint(et._epochList)

testPnt = 1280
epochIndex = et.findEpoch(testPnt)
print(f'testPnt:{testPnt} is in epoch index: {epochIndex}')
