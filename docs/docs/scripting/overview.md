## Writing custom Python scripts

In just a few lines of code, recordings can be loaded, analyzed, and plotted. See the [/examples][examples] folder for examples.

[examples]: https://github.com/cudmore/SanPy/tree/master/examples

```
import matplotlib.pyplot as plt
import bAnalysis
import bAnalysisPlot

ba = bAnalysis.bAnalysis('data/SAN-AP-example-Rs-change.abf')
ba.spikeDetect()

bAnalysisPlot.bPlot.plotSpikes(ba, xMin=140, xMax=145)
plt.show()
```

<IMG SRC="../../img/example1.png" width=600>
