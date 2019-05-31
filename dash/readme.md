## Plotly Dash experiments

These python files provide a web interface to browse analysis saved by bAnalysis..


## To Do

 - Add header to saved text file and add
     - sampling frequency
     - abf name
     
 - [done] Filter stat names to match 'cardiac' like in the desktop app
 - Add trace color as background in one cell of file list
 - Add dropdown to each plot to specify: markers, lines, lines+markers
 - [done, needs to be checked] Try and connect mean with line when between the same abf file ???
 - Add columns to file list for condition. Once done, plot x-axis as 'condition'
     - Implement grand mean between files that have same condition
 
## Troubleshooting

Trying to set background color in file list Index column causes Dash to not render? There is no error?

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
	]
```
