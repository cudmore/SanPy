## Plotly Dash experiments

These python files provide a web interface to browse analysis saved by bAnalysis..


## To Do

 - [done] On select in one graph, highlight in others
 - [done] Filter stat names to match 'cardiac' like in the desktop app
 - [done] Add trace color as background in one cell of file list
 - Add dropdown to each plot to specify: markers, lines, lines+markers
 - [done, needs to be checked] Try and connect mean with line when between the same abf file ???
 - [done] Add columns to file list for condition. Once done, plot x-axis as 'condition'
     - Implement grand mean between files that have same condition
 - Add header to saved text file and add
     - sampling frequency
     - abf name
     
 
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
