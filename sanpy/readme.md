## SanPy

A current-clamp analysis API and desktop GUI

## Install

## Running

## Analysis errors:

 - dvdtPercent: error searching for percent (10%) of dvdt max.
 - preMin: error searching for spike pre min
 - fitEDD: error while fitting slope of EDD
 - preSpikeDvDt: error while searching for peak in max ap upstroke b/w spike threshold and dvdt peak
 - postMinError:
 - cycleLength:
 - spikeWidth: error finding a particular spike with (AP_Dur)

## To Do

### Most important

 - Add code to backend to load text files (currently limited to Axon Instruments ABF files)
 - Add all hard coded detection parameters to json file and provide interface ot change !!!

 - Clean up code and write API documentation for each function
 - Revamp example Jupyter notebooks
  - Example: load, analyze, plot dV/dt and Vm
  - Example: load, analyze, plot scatter
  - Example: load, analyze many files, plot scatter across many files
 - Document output .txt file

### General

 - move ba to main window (remove from detection). Add option to detection to hold it.
    - once ba is in main window, add detection there
    - propagate changes to children including (detection widget, file widget, scatter widget)

### Main Window

 - add menus
  - x/y scatter plot
  - [done[ save preferences
  - [done] load folder
  - quit

### File Table

 - add 'min spike mV' to file table. need to update format of json saved in data folder !!!
 - make sure arrow keys in file table will load new files
 - [done] make it so selecting same file does not replot everything (just do nothing)
 - [done] update/save file table on detect (dv/dt threshold, analysis date/time, num spikes)

### Detection widget

 - add sweeps to detection widget

 - add spinner on file load

 - add group boxes to detection widget toolbar (borders around each)
  - detection
  - plot

 - [done] implement 'Save' of selected x-axis analysis

 - [done] make sure saved Excel file always has average clip of x axis when we save

 - [done] Get stats on top of dv/dt and Vm
 - [done] make sure clips show when toggling on/off with 'show clips'

### Scatter Plot

 - [done] add default selected stat in scatter plot, e.g. 'Spike Frequency (Hz)'

 - (mostly done) add single spike selection to scatter and highlight in detection widget vm plot
 - (mostly done) add multi-spike selection to scatter plot as x-axis is zoomed ???

 - bug single spike selection in scatter widget goes to wrong index in detection widget vm plot
     - make sure my bAnalysis indices line up (for missing data) e.g. first/last spike

 - [done] add all 'human' stat names to scatter widget
 - [done] fix bug when there is one spike
