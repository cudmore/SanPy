"""


"""

from pprint import pprint

import scipy.io as spio
import numpy as np
import matplotlib.pyplot as plt


def _loadmat(filename):
    '''
    See here for the code in xxx
        https://stackoverflow.com/questions/7008608/scipy-io-loadmat-nested-structures-i-e-dictionaries

    this function should be called instead of direct spio.loadmat
    as it cures the problem of not properly recovering python dictionaries
    from mat files. It calls the function check keys to cure all entries
    which are still mat-objects
    '''
    def _check_keys(d):
        '''
        checks if entries in dictionary are mat-objects. If yes
        todict is called to change them to nested dictionaries
        '''
        for key in d:
            #if isinstance(d[key], spio.matlab.mio5_params.mat_struct):
            if isinstance(d[key], spio.matlab.mat_struct):
                d[key] = _todict(d[key])
        return d

    def _todict(matobj):
        '''
        A recursive function which constructs from matobjects nested dictionaries
        '''
        d = {}
        for strg in matobj._fieldnames:
            elem = matobj.__dict__[strg]
            #if isinstance(elem, spio.matlab.mio5_params.mat_struct):
            if isinstance(elem, spio.matlab.mat_struct):
                d[strg] = _todict(elem)
            elif isinstance(elem, np.ndarray):
                d[strg] = _tolist(elem)
            else:
                d[strg] = elem
        return d

    def _tolist(ndarray):
        '''
        A recursive function which constructs lists from cellarrays
        (which are loaded as numpy ndarrays), recursing into the elements
        if they contain matobjects.
        '''
        elem_list = []
        for sub_elem in ndarray:
            #if isinstance(sub_elem, spio.matlab.mio5_params.mat_struct):
            if isinstance(sub_elem, spio.matlab.mat_struct):
                elem_list.append(_todict(sub_elem))
            elif isinstance(sub_elem, np.ndarray):
                elem_list.append(_tolist(sub_elem))
            else:
                elem_list.append(sub_elem)
        return elem_list
    data = spio.loadmat(filename, struct_as_record=False, squeeze_me=True)
    return _check_keys(data)

if __name__ == '__main__':
    path = '/Users/cudmore/Sites/patchclamp/patchclamp/examples/experiment001trial001_current_steps.mat'
    #path = '/Users/cudmore/Sites/patchclamp/patchclamp/examples/experiment002trial001_current_steps.mat'
    #path = '/Users/cudmore/Sites/patchclamp/patchclamp/examples/experiment001trial002_mEPSC.mat'
    
    # transform the mat file into a well behaved nested Python dictionary
    mat = _loadmat(path)
    
    sampleRateKHz = mat['Pars']['sampleRate']  # sampleRate is defined by Desai as 20000
    sampleIntervalSec = 1 / sampleRateKHz
    sampleIntervalMs = sampleIntervalSec * 1000  # 0.05 ms
    samplePerMs = 1 / sampleIntervalMs  # should be an int
    print('  sampleRateKHz:', sampleRateKHz)
    print('  sampleIntervalSec:', sampleIntervalSec)
    print('  sampleIntervalMs:', sampleIntervalMs)
    print('  samplePerMs:', samplePerMs)

    # input (recording)
    inputData = mat['inputData']  # numpy.ndarray shape (30000, 17)
    _len = len(inputData.shape)
    if _len == 1:
        # one sweep
        numSweeps = 1
        numSamples = len(inputData)
    elif _len == 2:
        # multiple sweeps
        numSweeps = inputData.shape[1]
        numSamples = inputData.shape[0]
    else:
        print(f'error: inputData is unexpected shape with len {_len}, expecting 1 or 2')
    print('numSamples:', numSamples)
    print('numSweeps:', numSweeps)

    # output (DAC)
    outputData = mat['outputData']  # numpy.ndarray shape (30000, 17)
    _len = len(outputData.shape)
    if _len == 1:
        # one sweep
        numStimSweeps = 1
    elif _len == 2:
        # multiple sweeps
        numStimSweeps = outputData.shape[1]
    else:
        print(f'error: outputData is unexpected shape with len {_len}, expecting 1 or 2')
    print('numStimSweeps:', numStimSweeps)

    # shared by all inputData and outputData
    xPlot = [x*sampleIntervalSec for x in range(numSamples)]
    
    doPlot = 1
    if doPlot:
        #numInputRows, numInputCols = inputData.shape    
        for col in range(numSweeps):
            if numSweeps == 1:
                plt.plot(xPlot, inputData)
            else:
                plt.plot(xPlot, inputData[:,col])
        plt.show()

        #numOutputRows, numOutputCols = outputData.shape    
        for col in range(numStimSweeps):
            if numStimSweeps == 1:
                plt.plot(xPlot, outputData)
            else:
                plt.plot(xPlot, outputData[:,col])

        plt.show()

