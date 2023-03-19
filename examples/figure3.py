"""
Not sure this is needed?

Plot Figure 3 of SanPy manuscript
"""

import matplotlib.pyplot as plt  # just to show plots during script

import sanpy

def fig():
    
    path = 'data/19114000.abf'

    ba = sanpy.bAnalysis(path)

    print(ba)

    ap = sanpy.bAnalysisPlot(ba)

    axs = ap.plotRaw()

    plt.show()

if __name__ == '__main__':
    fig()