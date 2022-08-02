
import sys

import sanpy.analysisDir
import sanpy.bDetection

def main():
    path = '/Users/cudmore/data/theanne-griffith'
    
    # load nested folder of abf files
    ad = sanpy.analysisDir(path)

    detectionClass = sanpy.bDetection()
    detectionDict = detectionClass.getDetectionDict('Fast Neuron')

    # load each abf and spike detect
    for rowIdx, file in enumerate(ad):
        ba = ad.getAnalysis(rowIdx)

        ba.spikeDetect(detectionDict)
        
        # if rowIdx>10:
        #     break

    # save h5 file into 'path'
    ad.saveHdf()

    print('===========')
    for rowIdx, file in enumerate(ad):
        # has to load all analysis, layer in script we will have it
        ba = ad.getAnalysis(rowIdx, verbose=False)
        
        print(rowIdx, ba)

    # print('===========')
    # for rowIdx, file in enumerate(ad):
    #     # has to load all analysis, layer in script we will have it
    #     ba = ad.getAnalysis(rowIdx)
    #     print(rowIdx, ba)

if __name__ == '__main__':
    main()