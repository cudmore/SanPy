import os
import matplotlib.pyplot as plt

import sanpy

def run(path):
    ba = sanpy.bAnalysis(path)
    print(ba)

    print(ba._sweepX)
    print(ba._sweepY)

    plt.plot(ba.sweepX, ba.sweepY)
    plt.show()

if __name__ == '__main__':
    path = '/media/cudmore/data/rabbit-ca-transient/Control/220110n_0003.tif.frames/220110n_0003.tif'
    
    rootdir = '/media/cudmore/data/rabbit-ca-transient'
    count = 0
    fileList = []
    for root, subdirs, files in os.walk(rootdir):
        print(count)
        #print('  ', root)
        #print('  ', subdirs)
        #print('  ', files)
        count += 1
        for file in files:
            if file.endswith('.tif'):
                oneFile = os.path.join(root, file)
                print('  ', oneFile)
                fileList.append(oneFile)

    run(path)