import numpy as np

# this specific import is to stop circular imports
from sanpy.user_analysis.baseUserAnalysis import baseUserAnalysis

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

def exampleFunction_xxx():
    logger.info(f'    !!!!')

exampleStatDict_xxx = {
    'a': 1,
    'b': 1,
}

class exampleUserAnalysis(baseUserAnalysis):
    """
    An example user defined analysis.

    We will add cardiac style 'maximum depolarizing potential', defines as:
        For each AP, the minimum voltage between the previous AP and the current AP.

    Don't include an __init__ function and inherited baseUserAnalysis.__init__() will be called
    If you define an __init__, need to call super()
    """

    userStatDict = {
        'user stat 1': {
            'name': 'mdp2_pnt',
            'yStat': 'mdp2_pnt',
        },
        'user stat 2': {
            'name': 'mdp2_val',
            'yStat': 'mdp2_val',
        },
        'user stat 3': {
            'name': 'timeToPeak_ms',
            'yStat': 'timeToPeak_ms',
        },
    }

    def run(self):
        """
        This is the user code to create and then fill in a new key/value for each spike.
        """

        #logger.info('Running ...')

        # add new keys to to ba.spikeDict
        #theDefault = None

        # get filtered vm for the entire trace
        filteredVm = self.getFilteredVm()

        lastThresholdPnt = None
        for spikeIdx, spikeDict in enumerate(self.ba.spikeDict):
            # add time to peak
            sweep = spikeDict['sweep']
            thresholdSec = spikeDict['thresholdSec']
            peakSecond = spikeDict['peakSec']
            timeToPeak_ms = (peakSecond - thresholdSec) * 1000

            # assign to underlying bAnalysis
            self.setSpikeValue(spikeIdx, 'timeToPeak_ms', timeToPeak_ms)

            thisThresholdPnt = spikeDict['thresholdPnt']

            # TODO: need to improve this, it cannot compare spikes across different sweeps !!!
            '''
            if spikeIdx == 0:
                # first spike does not have a mdp
                pass
            else:

                # pull out points between last spike and this spike
                preClipVm = filteredVm[lastThresholdPnt:thisThresholdPnt]

                #print(spikeIdx, spikeDict, preClipVm)
                print(spikeIdx, preClipVm)


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
            '''

def test1():
    from pprint import pprint
    import sanpy
    path = ''
    path = '/Users/cudmore/Sites/SanPy/data/19114000.abf'
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


    #eua = exampleUserAnalysis(ba)
    #eua.run()

if __name__ == '__main__':
    test1()
