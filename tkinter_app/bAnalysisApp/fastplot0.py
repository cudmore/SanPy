import pyqtgraph as pg
import numpy as np

app = pg.mkQApp()

'''
y = np.random.normal(size=(120,20000), scale=0.2) + np.arange(120)[:,np.newaxis]
x = np.empty((120,20000))
x[:] = np.arange(20000)[np.newaxis,:]
'''

###
from bAnalysis import bAnalysis
#import pyabf # see: https://github.com/swharden/pyABF

now = pg.ptime.time()

abfFile = '/Users/cudmore/Sites/bAnalysis/data/19221021.abf'
abfFile = '/Users/cudmore/Sites/bAnalysis/data/19114001.abf'
#myabf = pyabf.ABF(abfFile)
ba = bAnalysis(file=abfFile)

x = ba.abf.sweepX
y = ba.abf.sweepY

ba.getDerivative(medianFilter=5) # derivative
ba.spikeDetect0() # analysis

print ("abf load/anaysis time:", pg.ptime.time()-now, "sec")
###

view = pg.GraphicsLayoutWidget()
view.show()
w1 = view.addPlot(row=0, col=0)
w2 = view.addPlot(row=1, col=0)

class MultiLine(pg.QtGui.QGraphicsPathItem):
    def __init__(self, x, y):
        """x and y are 2D arrays of shape (Nplots, Nsamples)"""
        # abb removed
        #connect = np.ones(x.shape, dtype=bool)
        #connect[:,-1] = 0 # don't draw the segment between each trace
        #self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect.flatten())
        self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect='all')
        pg.QtGui.QGraphicsPathItem.__init__(self, self.path)
        self.setPen(pg.mkPen('w'))
    def shape(self): # override because QGraphicsPathItem.shape is too expensive.
        return pg.QtGui.QGraphicsItem.shape(self)
    def boundingRect(self):
        return self.path.boundingRect()

now = pg.ptime.time()

# plot derivative
lines = MultiLine(x, ba.filteredDeriv)
w1.addItem(lines)

# plot Vm
lines = MultiLine(x, y)
w2.addItem(lines)

def update_x_axis():
	print('update_x_axis()')
	
# try for horizontal selection
linearRegionItem = pg.LinearRegionItem(values=(0,0), orientation=pg.LinearRegionItem.Vertical)
linearRegionItem.sigRegionChangeFinished.connect(update_x_axis)
w2.addItem(linearRegionItem)

print ("Plot time:", pg.ptime.time()-now, "sec")

app.exec_()