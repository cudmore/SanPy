"""
Code to analyze, plot, and save kymograph diameter.

Strategy is to just extract the diameter from an ROI that encompasses the entire kymograph tif.

This is different than extracting proper linescan sum and performing spike detection.

20220610

This script uses sanpy.kymographAnalysis(), the output columns are specified there.
"""

import os
from glob import glob
from pprint import pprint
from collections import OrderedDict

import numpy as np
import pandas as pd
import scipy.signal
import matplotlib.pyplot as plt

import sanpy

def run(path):
    """Run analysis on all raw data in path.
    """
    # folder to save all this analysis
    savePath = '/Users/cudmore/Desktop/kymAnalysis'
    if not os.path.isdir(savePath):
        os.mkdir(savePath)

    # the folder we loaded from, make a new folder in savePAth
    _loadedPath, loadedFolder = os.path.split(path)
    finalSavePath = os.path.join(savePath, loadedFolder)
    if not os.path.isdir(finalSavePath):
        os.mkdir(finalSavePath)

    path2 = os.path.join(path, '**', '*.tif')
    print('fetching tif files from:', path2)
    files = glob(path2, recursive=True)
    
    dictList = []
    
    for idx, file in enumerate(files):
        print(f'=== {idx} of {len(files)} {file}')
        
        ka = sanpy.kymographAnalysis(file, autoLoad=False)

        # analyze with default rect roi
        ka.setLineWidth(1)
        ka.analyze()


        # get kym report
        oneDict = ka.getReport()
        dictList.append(oneDict)

        # plot
        fig = plotKym(ka)

        # save figure
        if 1:
            folder = oneDict['folder']
            fileName, _tmp = os.path.splitext(oneDict['file'])
            saveFigName = fileName + '.png'
            saveFigPath = os.path.join(finalSavePath, folder)
            if not os.path.isdir(saveFigPath):
                os.mkdir(saveFigPath)
            saveFigPath = os.path.join(saveFigPath, saveFigName)
            print('  saveFigPath:', saveFigPath)
            fig.savefig(saveFigPath, dpi=600)

        #break

    #
    # save report as csv
    df = pd.DataFrame(dictList)
    print('final summary df is:')
    pprint(df)
    kymReport = os.path.join(finalSavePath, 'kymReport.csv')
    print('  saving kymReport:', kymReport)
    df.to_csv(kymReport)

    #plt.show()

    return df

def plotKym(ka : sanpy.kymographAnalysis):
    """
    """

    tifData = ka.getImage()
    
    time_ms = ka.getResults('time_ms')
    diameter_um = ka.getResults('diameter_um')
    sumintensity = ka.getResults('sumintensity')

    # smooth
    kernelSize = 5
    diameter_um_f = scipy.signal.medfilt(diameter_um, kernelSize)
    sumintensity_f = scipy.signal.medfilt(sumintensity, kernelSize)

    sharex = True
    #fig, axs = plt.subplots(nrows=3, ncols=1, sharex=sharex, figsize=(6,5), constrained_layout=True) # need constrained_layout=True to see axes titles
    fig = plt.figure(constrained_layout=True, figsize=(5,7))
    gs = fig.add_gridspec(4, 2)
    axs0 = fig.add_subplot(gs[0, :])
    axs1 = fig.add_subplot(gs[1, :])
    axs2 = fig.add_subplot(gs[2, :])

    squareAxs = fig.add_subplot(gs[-1, 0])

    # sharex
    axs0.get_shared_x_axes().join(axs0, axs1)
    axs1.get_shared_x_axes().join(axs1, axs2)

    axs = [axs0, axs1, axs2]

    #pointsPerLineScan = ka.pointsPerLineScan()
    #numLineScans = ka.numLineScans()
    #aspect = pointsPerLineScan / numLineScans
    aspect = 'auto'

    spaceArray = ka.getSpaceArray()
    extent = [0, time_ms[-1], 0, spaceArray[-1]]  # [xmin, xmax, ymin, ymax]

    plotTif = np.rot90(tifData)  # matplotlib swaps axis
    axs[0].imshow(plotTif, extent=extent, aspect=aspect)
    axs[0].spines['top'].set_visible(False)
    axs[0].spines['right'].set_visible(False)
    axs[0].set_ylabel('Pixels')
    axs[0].set_xlabel('Line Scans')

    axs[1].plot(time_ms, diameter_um_f, 'k')
    axs[1].set_ylabel('Diameter (um)')
    axs[1].spines['top'].set_visible(False)
    axs[1].spines['right'].set_visible(False)
    
    axs[2].plot(time_ms, sumintensity_f, 'k')
    axs[2].set_ylabel('Mean Intensity')
    axs[2].spines['top'].set_visible(False)
    axs[2].spines['right'].set_visible(False)

    axs[2].set_xlabel('Time (s)')

    #
    # second plot with intensity versus diam
    axs2 = [squareAxs]
    cIdx = ka.getTimeArray()  # range(len(sumintensity_f))
    _im = axs2[0].scatter(sumintensity_f, diameter_um_f, marker='.', c=cIdx)
    fig.colorbar(_im, ax=axs2[0])

    axs2[0].set_ylabel('Diameter (um)')
    axs2[0].set_xlabel('Mean Intensity')
    axs2[0].spines['top'].set_visible(False)
    axs2[0].spines['right'].set_visible(False)

    return fig

if __name__ == '__main__':
    # run this script on a number of raw data acquisition days
    path = '/Users/cudmore/data/kym-example'  # load raw data from here
    
    # run this analysis on all raw data
    path1 = '/Users/cudmore/data/rabbit-kym/Feb 8 2022'
    path2 = '/Users/cudmore/data/rabbit-kym/Feb 15 2022'
    path3 = '/Users/cudmore/data/rabbit-kym/Jan 11 2022'
    path4 = '/Users/cudmore/data/rabbit-kym/Jan 18 2022'

    # TODO: make sure all paths exist
    
    #path = '/Users/cudmore/data/rabbit-kym'

    #pathList = [path, path]

    pathList = [path1, path2, path3, path4]

    dfMaster = None
    
    for path in pathList:
        df = run(path)
        if dfMaster is None:
            dfMaster = df
        else:
            dfMaster = pd.concat([dfMaster, df], ignore_index=True)

    pprint(dfMaster)
    masterMasterCsv = '/Users/cudmore/Desktop/kymMaster.csv'
    dfMaster.to_csv(masterMasterCsv)