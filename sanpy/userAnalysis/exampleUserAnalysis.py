import numpy as np

# this specific import is to stop circular imports
import sanpy.useranalysis.baseUserAnalysis as baseUserAnalysis

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class exampleUserAnalysis(baseUserAnalysis):
	"""
	An example user defined analysis.

	We will add cardiac style 'maximum depolarizing potential', defines as:
		For each AP, the minimum voltage between the previous AP and the current AP.
	"""

	userStatDict = {
		'user stat 1': {
			'name': 'mdp2_pnt',
			'yStat': 'mdp2_pnt',
		},
		'user stat 2': {
			'name': 'mdp2_val',
			'yStat': 'mdp2_val',
		}
	}

	def run(self):
		"""
		This is the user code to create and then fill in a new key/value for each spike.
		"""

		logger.info('Running ...')

		# add new keys to to ba.spikeDict
		#theDefault = None

		# get filtered vm for the entire trace
		filteredVm = self.getFilteredVm()

		lastThresholdPnt = None
		for spikeIdx, spike in enumerate(self.ba.spikeDict):
			thisThresholdPnt = spike['thresholdPnt']

			if spikeIdx == 0:
				# first spike does not have a mdp
				pass
			else:

				# pull out points between last spike and this spike
				preClipVm = filteredVm[lastThresholdPnt:thisThresholdPnt]

				# find the min point in vm
				# np.argmin returns zero based starting from lastThresholdPnt
				preMinPnt = np.argmin(preClipVm)
				preMinPnt += lastThresholdPnt

				# grab Vm value at that point
				theMin = filteredVm[preMinPnt]  # mV

				# assign to underlying bAnalysis
				self.setSpikeValue(spikeIdx, 'mdp2_pnt', preMinPnt)
				self.setSpikeValue(spikeIdx, 'mdp2_val', theMin)

			#
			lastThresholdPnt = thisThresholdPnt

def test1():
	path = ''
	path = '/home/cudmore/Sites/SanPy/data/19114000.abf'
	ba = sanpy.bAnalysis(path)
	detectionClass = ba.detectionClass
	detectionClass['verbose'] = False
	sweepNumber = 0
	ba.spikeDetect2__(sweepNumber, detectionClass)

	eua = exampleUserAnalysis(ba)
	eua.run()

if __name__ == '__main__':
	test1()
