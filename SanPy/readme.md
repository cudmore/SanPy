## SanPy

A spike detection program optimized for cardiac myocytes

## To Do

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
 
 - implement 'Save' of selected x-axis analysis

 - [done] Get stats on top of dv/dt and Vm
 - [done] make sure clips show when toggling on/off with 'show clips'
 
 - update/save file table on detect (dv/dt threshold, analysis date/time, num spikes)
 
 - add 'min spike mV' to file table. need to update format of json saved in folder !!!
 
 - [done] add all 'human' stat names to scatter widget
 
 - move ba to main window (remove from detection). Add option to detection to hold it.
    - once ba is in main window, add detection htere
    - propagate changes to children including (detection widget, file widget, scatter widget)
    
 @@@@@ IMPORTANT @@@@@@
 - *** ADD RESET mV BEFORE WE DETECT NEXT SPIKE *** !!! !!!
 @@@@@ IMPORTANT @@@@@@
 
 
 - fix bug when there is one spike
 
 ```
   File "/Users/cudmore/Sites/bAnalysis/SanPy/bScatterPlotWidget.py", line 138, in metaPlotStat
    self._static_ax.set_ylim([yMin, yMax])
```

