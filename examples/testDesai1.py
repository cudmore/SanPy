"""
Load Matlab .mat files from Niraj Desai's PathClamp software.
"""

from pprint import pprint

import matplotlib.pyplot as plt
import scipy.io

def run():
    path = '/Users/cudmore/Sites/patchclamp/patchclamp/examples/experiment001trial001_current_steps.mat'

    # import numpy as np
    # import h5py
    # f = h5py.File(path,'r')
    # data = f.get('data/variable1')
    # data = np.array(data) # For converting to a NumPy array

    mat = scipy.io.loadmat(path)  # load a dict
    
    print(mat.keys())
    
    print('__header__:', mat['__header__'])
    print('__version__:', mat['__version__'])
    print('__globals__:', mat['__globals__'])  # ['Pars', 'inputData', 'outputData']
    print('__function_workspace__:', type(mat['__function_workspace__']))

    functionWorkSpace = mat['__function_workspace__']  # numpy.ndarray (1, 1096)
    print('functionWorkSpace:', functionWorkSpace.shape)
    #pprint(functionWorkSpace)

    sampleRate = mat['Pars']['sampleRate']
    print('sampleRate:', sampleRate)

    #DeprecationWarning: Please use `mat_struct` from the `scipy.io.matlab` namespace,
    # the `scipy.io.matlab.mio5_params` namespace is deprecated.
    #xxx = isinstance(sampleRate, scipy.io.matlab.mio5_params.mat_struct)
    xxx = isinstance(sampleRate, scipy.io.matlab.mat_struct)
    print('xxx:', xxx)
    if isinstance(sampleRate, scipy.io.matlab.mio5_params.mat_struct):
        print('is spio.matlab.mio5_params.mat_struct')

    # pars = mat['Pars']  # numpy.ndarray (1,1)
    # print('Pars:', type(pars), pars.shape)
    # pars0 = pars[0]
    # print('pars0:', type(pars0), pars0.shape)
    # #print(pars0)

    # pars00 = pars0[0]
    # print('pars00:', type(pars00), pars00.shape, len(pars00))
    # pprint(pars00)
    # for i in range(len(pars00)):
    #     print('  ', i, pars00[i])

    inputData = mat['inputData']  # numpy.ndarray shape (30000, 17)
    print('inputData:', type(inputData), inputData.shape)

    outputData = mat['outputData']  # numpy.ndarray shape (30000, 17)
    print('outputData:', type(outputData), outputData.shape)

    if 0:
        numInputRows, numInputCols = inputData.shape    
        for col in range(numInputCols):
            plt.plot(inputData[:,col])

        plt.show()

        numOutputRows, numOutputCols = outputData.shape    
        for col in range(numOutputCols):
            plt.plot(outputData[:,col])

        plt.show()


if __name__ == '__main__':
    run()