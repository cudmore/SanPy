import numpy as np

from sanpy.user_analysis.baseUserAnalysis import baseUserAnalysis
from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class exampleUserAnalysis(baseUserAnalysis):
    """
    An example user defined analysis.

    We will add 'User Time To Peak (ms)', defines as:
        For each AP, the time interval between spike threshold and peak

    We need to define the behavior of two inherited functions

    1) defineUserStats()
        add any numner of user stats with
            addUserStat(human_name, internal_name)

    2) run()
        Run the analysis you want to compute.
        Add the value for each spike with
            setSpikeValue(spike_index, internal_name, new_value)
    """

    def defineUserStats(self):
        """Add your user stats here."""
        self.addUserStat("User Time To Peak (ms)", "user_timeToPeak_ms")

    def run(self):
        """This is the user code to create and then fill in
            a new name/value for each spike."""

        # get filtered vm for the entire trace
        filteredVm = self.getFilteredVm()

        lastThresholdPnt = None
        for spikeIdx, spikeDict in enumerate(self.ba.spikeDict):
            # add time to peak
            thresholdSec = spikeDict["thresholdSec"]
            peakSecond = spikeDict["peakSec"]
            timeToPeak_ms = (peakSecond - thresholdSec) * 1000

            # assign to underlying bAnalysis
            # print(f'  exampleUserAnalysis() {spikeIdx} user_timeToPeak_ms {timeToPeak_ms}')
            self.setSpikeValue(spikeIdx, "user_timeToPeak_ms", timeToPeak_ms)

def test1():
    from pprint import pprint
    import sanpy

    path = ""
    path = "/Users/cudmore/Sites/SanPy/data/19114000.abf"
    ba = sanpy.bAnalysis(path)

    # detectionClass = ba.detectionClass
    # detectionClass['verbose'] = False
    # sweepNumber = 0
    # ba.spikeDetect2__(sweepNumber, detectionClass)
    ba.spikeDetect()

    # checking user analysis exists
    import inspect

    # userFunctions = inspect.getmembers(sanpy.user_analysis, inspect.isfunction)
    # print('userFunctions:', userFunctions)
    # for userFunction in userFunctions:
    #     print(userFunction)
    objList = sanpy.user_analysis.baseUserAnalysis.getObjectList()  # list of dict
    for item in objList:
        pprint(item)

    # eua = exampleUserAnalysis(ba)
    # eua.run()


if __name__ == "__main__":
    test1()
