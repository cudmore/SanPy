## SanPy

A spike detection program optimized for cardiac myocytes

## To Do

 - add spinner on file load
 - make sure arrow keys in file table will load new files
 - add default selection in scatter plot - ap peak
 
 - add group boxes to detection widget toolbar (borders around each)
  - detection
  - plot
  
 - add menus
  - scatter plot
  - [done[ save preferences
  - [done] load folder
  - quit
  
 - [done] make it so selecting same file does not replot everything (just do nothing)
 
 - add sweeps to detection widget
 
 - (maybe) add selection to scatter plot as x-axis is zoomed ???
 - (maybe) add selection to scatter to highlight in raw/dvdt
 
 - [done] implement 'Save' of selected x-axis analysis

 - [done] Get stats on top of dv/dt and Vm
 - [done] make sure clips show when toggling on/off with 'show clips'
 
 - [done] update/save file table on detect (dv/dt threshold, analysis date/time, num spikes)
 
 - add 'min spike mV' to file table. need to update format of json saved in folder !!!
 
 - [done] add all 'human' stat names to scatter widget
 
 - move ba to main window (remove from detection). Add option to detection to hold it.
    - once ba is in main window, add detection htere
    - propagate changes to children including (detection widget, file widget, scatter widget)
    
 @@@@@ IMPORTANT @@@@@@
 - *** ADD RESET mV BEFORE WE DETECT NEXT SPIKE *** !!! !!!
 @@@@@ IMPORTANT @@@@@@
 
 
 - [done] fix bug when there is one spike
 
```
   File "/Users/cudmore/Sites/bAnalysis/SanPy/bScatterPlotWidget.py", line 138, in metaPlotStat
    self._static_ax.set_ylim([yMin, yMax])
```

```
Traceback (most recent call last):
  File "/Users/cudmore/Sites/bAnalysis/SanPy/bScatterPlotWidget.py", line 257, in on_scatter_toolbar_table_click
    self.myParent.metaPlotStat(yStat)
  File "/Users/cudmore/Sites/bAnalysis/SanPy/bScatterPlotWidget.py", line 138, in metaPlotStat
    self._static_ax.set_ylim([yMin, yMax])
  File "/usr/local/lib/python3.7/site-packages/matplotlib/axes/_base.py", line 3616, in set_ylim
    bottom = self._validate_converted_limits(bottom, self.convert_yunits)
  File "/usr/local/lib/python3.7/site-packages/matplotlib/axes/_base.py", line 3139, in _validate_converted_limits
    raise ValueError("Axis limits cannot be NaN or Inf")
ValueError: Axis limits cannot be NaN or Inf
Abort trap: 6
```