# How to add to the core analysis

Here we will add a `fast AHP` measurement to the core analysis. This requires the addition of a new detection parameter `fastAhpWindow_ms`. If a new detection parameters is not needed, the core analysis can be extended with a new [analysis plugin](writing-new-analysis.md).

### Add to `detection-presets/Fast Neuron.json`

    "fastAhpWindow_ms": 5,

### Add to `bDetection.py`

This defines a new detection parameter `fastAhpWindow_ms`.

```python
key = "fastAhpWindow_ms"
theDict[key] = {}
theDict[key]["defaultValue"] = 5
theDict[key]["type"] = "float"
theDict[key]["allowNone"] = False
theDict[key]["units"] = "ms"
theDict[key]["humanName"] = "Fast AHP Window (ms)"
theDict[key]["errors"] = ""
theDict[key]["description"] = "Window (ms) after peak to look for a fast AHP"
```

### Add to `bAnalysisResults`

This defines 3 new analysis results to keep track of the point, seconds, and value of the fast AHP.

```python
key = "fastAhpPnt"
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]["type"] = "int"
analysisResultDict[key]["default"] = defaultVal
analysisResultDict[key]["units"] = "point"
analysisResultDict[key]["depends on detection"] = "fastAhpWindow_ms"
analysisResultDict[key]["description"] = "fast AHP point."

key = "fastAhpSec"
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]["type"] = "float"
analysisResultDict[key]["default"] = defaultVal
analysisResultDict[key]["units"] = "sec"
analysisResultDict[key]["description"] = "fast AHP seconds."

key = "fastAhpValue"
analysisResultDict[key] = getDefaultDict()
analysisResultDict[key]["type"] = "float"
analysisResultDict[key]["default"] = defaultVal
analysisResultDict[key]["units"] = "mV"  # voltage-clamp'
analysisResultDict[key]["description"] = "Value of Vm at fast AHP point."
```

### Add to `bAnalysisUtil._buildStatList()`

This defines a human readable `Fast AHP (mv)` and is used in the gui. For an example of how it is used, see the scatter plot plugin.

```python
statList["Fast AHP (mV)"] = {
    "name": "fastAhpValue",
    "units": "mV",
    "yStat": "fastAhpValue",
    "yStatUnits": "mV",
    "xStat": "fastAhpPnt",
    "xStatUnits": "Points",
}
```

### Add to `bAnalysis_._spikeDetect2()`

This is the code that does the actual analysis. For each spike, we look in a window after the peak for the minimum membrane potential. We also log an error when the fast AHP is in the last bin using `fastAhpWindow_pnts`.

```python
# look in a window after each peak to get 'fast ahp'
fastAhpWindow_pnts = self.fileLoader.ms2Pnt_(dDict["fastAhpWindow_ms"])
```

```python
if peakPnt+fastAhpWindow_pnts < len(sweepX):
    fastAhpClip = filteredVm[peakPnt : peakPnt+fastAhpWindow_pnts]
    fastAhpPnt = np.argmin(fastAhpClip)
    
    fastAhpError = fastAhpPnt == len(fastAhpClip)-1
    
    fastAhpPnt += peakPnt
    fastAhpSec = self.fileLoader.pnt2Sec_(fastAhpPnt)
    fastAhpValue = filteredVm[fastAhpPnt]

    spikeDict[i]["fastAhpPnt"] = fastAhpPnt
    spikeDict[i]["fastAhpSec"] = fastAhpSec
    spikeDict[i]["fastAhpValue"] = fastAhpValue

    # log error
    if fastAhpError:
        errorType = "Fast AHP was detected at end of fast AHP window"
        errorStr = "Consider increasing the fast AHP window with fastAhpWindow_ms"
        eDict = self._getErrorDict(
            i, spikeTimes[i], errorType, errorStr
        )  # spikeTime is in pnts
        spikeDict[iIdx]["errors"].append(eDict)
```

### Add to `bDetectionWidget.__init()`

This adds fast ahp to the main interface.

```python
{
    "humanName": "Fast AHP (mV)",
    "x": "fastAhpSec",
    "y": "fastAhpValue",
    "convertx_tosec": False,
    "color": "y",
    "styleColor": "color: yellow",
    "symbol": "o",
    "plotOn": "vm",
    "plotIsOn": True,
},
```