The SanPy API is split into two main sections: backend and frontend.

### Loading raw data

The following code loads from a file into a bAnalysis object.

```
import sanpy
path = 'xxx'
ba = sanpy.bAnalysis(path)
```

### Detecting Spikes

Spike detection takes a number of parameters but in its simplest form only requires a threshold in the derivative (dV/dt) of membrane potential (mV).

```
# set detecction parameters
dDict = ba.getDefaultDetection()
dDict['dvdtThreshold'] = 50

# perform spike detection
ba.spikeDetect(dDict)
```

### Plotting Results

Once analyze, parameters can be plotted over the raw data

```
bp = sanpy.bAnalysisPlot(ba)
fig, ax = bp.plotSpikes()
```

### Saved file formats

TODO: Fill this in. xxx
