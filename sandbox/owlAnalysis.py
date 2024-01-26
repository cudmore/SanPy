import numpy as np
import pyabf

import matplotlib.pyplot as plt

import sanpy

def _demo_deltaT(abf):
    """Demonstrate delta duration."""
    import matplotlib.pyplot as plt
    # abf = pyabf.ABF(PATH_DATA+"/2018_04_13_0016a_original.abf")
    epochTable = pyabf.waveform.EpochTable(abf, 0)
    print('epochTable')
    print(epochTable)

    fig = plt.figure(figsize=(8, 5))
    ax1 = fig.add_subplot(211)
    ax2 = fig.add_subplot(212, sharex=ax1)
    # for sweep in abf.sweepList[:20]:
    for sweep in abf.sweepList:
        abf.setSweep(sweep)
        sweepWaveform = epochTable.epochWaveformsBySweep[sweep]
        sweepC = sweepWaveform.getWaveform()
        ax1.plot(abf.sweepX, abf.sweepY, color='b', lw=.5)
        ax2.plot(abf.sweepX, sweepC, color='r', lw=.5)
    plt.show()

def _demo_sweepD(abf):
    """Demonstrate how to access digital outputs."""
    import matplotlib.pyplot as plt
    # abf = pyabf.ABF(PATH_DATA+"/17o05026_vc_stim.abf")
    epochTable = pyabf.waveform.EpochTable(abf, 0)  # channel 0
    for sweep in abf.sweepList:
        sweepWaveform = epochTable.epochWaveformsBySweep[sweep]  # sweep 0
        for digitalIdx in range(8):
            sweepD = sweepWaveform.getDigitalWaveform(digitalIdx)  # digital output 4
            print(f'digitalIdx:{digitalIdx} SweepD:{sweepD}')
            plt.plot(sweepD)
    plt.show()

def _demo_epoch_access(abf):
    """Demonstrate how to access epoch levels and point indexes."""
    import matplotlib.pyplot as plt
    # for fname in glob.glob(PATH_DATA+"/18702001-*.abf"):
    if 1:
        # abf = pyabf.ABF(fname)
        print("\n\n", "#"*20, abf.abfID, "(CH 1)", "#"*20)

        # show waveform info for each sweep
        epochTable = pyabf.waveform.EpochTable(abf, 0)
        for sweep in abf.sweepList:
            sweepWaveform = epochTable.epochWaveformsBySweep[sweep]
            print("\n", "#"*5, "Sweep", sweep, "#"*5)
            print(sweepWaveform)
            print("levels:", sweepWaveform.levels)
            print("types:", sweepWaveform.types)
            print("p1s:", sweepWaveform.p1s)
            print("p2s:", sweepWaveform.p2s)
            print("pulsePeriods:", sweepWaveform.pulsePeriods)
            print("pulseWidths:", sweepWaveform.pulseWidths)

def attemptTwo(abf):

    # sweeps (6,7,8,9,10,11)
    # path = '/Users/cudmore/Dropbox/data/sanpy-users/porter/data/2022_08_15_0022.abf'

    # abf = pyabf.ABF(path)

    _userList = abf.userList
    print('userList:', len(_userList), _userList)

    print('userListEnable:', abf.userListEnable, type(abf.userListEnable))
    print('userListParamToVary:', abf.userListParamToVary, type(abf.userListParamToVary))
    print('userListParamToVaryName:', abf.userListParamToVaryName, type(abf.userListParamToVaryName))
    print('userListRepeat:', abf.userListRepeat, type(abf.userListRepeat))
    print('_userListSection:', abf._userListSection, type(abf._userListSection))

    #print(abf.sweepD)
    #print('abf.tagTimesSec:', abf.tagTimesSec)

    sweepList = abf.sweepList
    numSweeps = len(sweepList)

    print('numSweeps:', numSweeps)

    return abf

    for sweep in sweepList:
        abf.setSweep(sweep)
        for digitalIdx in range(8):
            oneSweepD = abf.sweepD(digitalIdx)

    channel = 0
    sweepListSmall = [6,7,8,9,10,11]
    for sweep in sweepListSmall:
        abf.setSweep(sweep)
        print(f'=== sweep {sweep}')
        oneEpochTable = pyabf.waveform.EpochTable(abf, channel)
        print(oneEpochTable)

def attemptOne():
    # 18 sweeps
    path = '/Users/cudmore/Dropbox/data/sanpy-users/porter/2022_08_15_0022.abf'

    # 1 sweep
    # path = '/Users/cudmore/Dropbox/data/sanpy-users/porter/2022_09_01_0046.abf'

    path = '/Users/cudmore/Dropbox/data/sanpy-users/porter/data/2022_08_15_0022.abf'

    ba = sanpy.bAnalysis(path)
    print(ba.fileLoader.getEpochTable(0))
    print('')
    print(ba.fileLoader.getEpochTable(1))

    abf = pyabf.ABF(path)

    # _demo_epoch_access(abf)
    # _demo_sweepD(abf)
    # _demo_deltaT(abf)

    print('abf.channelList:', abf.channelList)

    #print(abf.sweepD)
    #print('abf.tagTimesSec:', abf.tagTimesSec)

    sweepList = abf.sweepList
    numSweeps = len(sweepList)

    print('numSweeps:', numSweeps)

    numDigitialOutputs = 8

    fig, axs = plt.subplots(3, 1, sharex=True)

    print('self._abf.sweepD')

    if 1:
        sweepD_list = []
        for sweepIdx, sweep in enumerate(sweepList):

            # if sweepIdx < 4:
            #     continue
            
            abf.setSweep(sweep)
            
            sweepX = abf.sweepX
            sweepY = abf.sweepY
            sweepC = abf.sweepC
            
            if 1:
                for i in range(numDigitialOutputs):
                    oneSweepD = abf.sweepD(i)  # 8 digital per sweep
                    sweepD_list.append(oneSweepD)
                    _max = np.max(oneSweepD)
                    if _max > 0:
                        equalOne = np.where(oneSweepD == 1)
                        equalOne = equalOne[0]
                        print(f'sweep {sweep} digital:{i} len:{len(oneSweepD)} min:{np.min(oneSweepD)} max:{np.max(oneSweepD)} equal1: {len(equalOne)} {equalOne}')
                    axs[0].plot(sweepX, sweepD_list[-1])
        
            if sweepIdx == 10:
                oneEpochTable = pyabf.waveform.EpochTable(abf, channel=0)
                print(oneEpochTable)

            axs[1].plot(sweepX, sweepC)
            axs[2].plot(sweepX, sweepY)

    # use sanpy to generate an epoch table, one table per sweep
    if 0:
        _numSweeps = len(abf.sweepList)
        _epochTableList = [None] * _numSweeps
        for _sweepIdx in range(_numSweeps):
            abf.setSweep(_sweepIdx)
            _epochTableList[_sweepIdx] = sanpy.fileloaders.epochTable(
                abf
            )
        abf.setSweep(0)
        for epochTable in _epochTableList:
            print(epochTable)

    if 0:
        # from the pyabf web documentation
        _numSweeps = len(abf.sweepList)
        for _sweepIdx in range(_numSweeps):
            abf.setSweep(_sweepIdx)
            for epochIdx, p1 in enumerate(abf.sweepEpochs.p1s):
                epochLevel = abf.sweepEpochs.levels[epochIdx]
                epochType = abf.sweepEpochs.types[epochIdx]

                pulseWidth = abf.sweepEpochs.pulseWidths[epochIdx]
                pulsePeriod = abf.sweepEpochs.pulsePeriods[epochIdx]
                digitalStates = abf.sweepEpochs.digitalStates[epochIdx]

                # used by pyabf when we access sweepD, getDigitalWaveform

                print(f"sweep:{_sweepIdx} epoch index {epochIdx}: at point {p1} there is a {epochType} to level {epochLevel} pulseWidth:{pulseWidth} pulsePeriod:{pulsePeriod} digitalStates:{digitalStates}")


    plt.show()

    return abf

if __name__ == '__main__':
    print(pyabf.__version__)
    
    abf = attemptOne()
    attemptTwo(abf)