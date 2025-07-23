
Colin data

Colin's file pairs are like

/Users/cudmore/Dropbox/data/colin/sanAtp/SSAN Linescan 3 Metadata.txt
/Users/cudmore/Dropbox/data/colin/sanAtp/SSAN Linescan 3.tif

## TODO 20240911

- [done] Add loading of Olympus txt files to include file names with "Metadata"

- [done] add contrast sliders to kym image
- [done] add combobox to set color like (red, green, blue, gray)
- [done] add cursors to sum intensity plot (user can use to set detection params like 'distance', e.g. refractory period)
    Still need to add menus to set params like ('distance', 'refractory', etc.)

- write class KymRoiDetection(), we currently just use a dictionary
    Wrote the class, need to incorporate it into kymRoiWidget

- implement peak selection
    - in sum intensity plot
    - in scatter
    - in raw scatter plot table

- [done]integrate into SanPy as a plugin

- [done] read Olympus header txt file

- now that kyRoiWidget is a QMainWindow, add some status updates (bottom of window)
 - [done] on copy table
 - [done] on new
 - delete roi
 - [done] on select roi
 - on analysis, report number of peaks detected

- If decay fit tau is near zero (like < 0.001) then -> REJECT !!!!
    I am tending toward not using decay (single, double expontential) and just using 'decay (ms)', e.g. the time to decay from peak to 90% of peak.

- [done} Implement dark/light style. Currently we have a mixture and it is distracting/annoying.

- TODO: implement 'remove outliers' in y-stat summary when values are >1*sdThreshold ????
