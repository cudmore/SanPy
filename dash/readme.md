## Web interface to abf file analysis and plotting

 - dash_app.py, provides a web interface to load, visualize, analyze and save results of spike analysis.
 - bBrowser_app.py, EXPERIMENTAL, provides a web interface to browse many analysis files and parameters at the same time.

## install

```
python3 -m venv sanpy_dash
source sanpy_dash/bin/activate
#pip install -r requirements.txt
pip install wheel
pip install dash
pip install dash-bootstrap-components
pip install dash-daq
```

## To Do (backend)

 - Add header to saved text file and add
     - sampling frequency
     - abf name
 - Allow files other than abf to be opened?

## To Do (bAnalysis)

 - Implement save!!!!
 - Get rid of 'Load Folder' button and implement dropdown to select /data folder like I have done in bBrowser
 - Fix updating of raw dV/dt and Vm when a new files is selected and analyzed
 - Implement data shader to speed up plotting of raw data

## To Do (bBrowser)

 - [done] On select in one graph, highlight in others
 - [done] Filter stat names to match 'cardiac' like in the desktop app
 - [done] Add trace color as background in one cell of file list
 - Add dropdown to each plot to specify: markers, lines, lines+markers
 - [done, needs to be checked] Try and connect mean with line when between the same abf file ???
 - [done] Add columns to file list for condition. Once done, plot x-axis as 'condition'
 - When plotting conditions, add grand mean of means between files that have same condition

## Versions

```
dash==0.43.0
dash-bootstrap-components==0.6.1
dash-core-components==0.48.0
dash-daq==0.1.0
dash-html-components==0.16.0
dash-renderer==0.24.0
dash-table==3.7.0
```

## Troubleshooting

Trying to set background color in file list Index column causes Dash to not render? There is no error?

Seemed to get fixed with myStyleDataConditional()

```
	style_data_conditional=[
	    {
	        'if': {
	            'column_id': 'Index',
	            'filter': '{Index} eq "1"'
	        },
	        'backgroundColor': colorList[0],
	        'color': 'white',
	    },
	],
```

## To Do

 - Add right-click to bring up color picker and set color of a given file ...
 - Condition plotting is not working when condition is a string

 - Finish code to connect 'mean lines b/w condition 1/2/3'
