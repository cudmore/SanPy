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

## Install heroku cli

First had to manually update brew with the following.

```
git -C /usr/local/Homebrew/Library/Taps/homebrew/homebrew-core fetch --unshallow

# then, Took 20-30 minutes.
brew update
```

See: https://devcenter.heroku.com/articles/heroku-cli
```
brew tap heroku/brew && brew install heroku
```

## Install amazon aws cli

## To Do: Install amazon elastic beanstalk

## To Do: Look into using datashader to plot e-phys traces

See dash/sandbox/myShader.py

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

## Deploy to Heroku

`git push` main git repo then manually 'deploy' heroku app from heroku web interface.


### Install heroku cli

```
brew tap heroku/brew && brew install heroku
```

Run locally

```
heroku local
```

View logs ( from online web version)

```
heroku logs --app=sanpy
```

Use command line to push to git and heroku

```
heroku git:remote -a sanpy
# responds: set git remote heroku to https://git.heroku.com/sanpy.git
```

We now have

```
git remote -v

heroku	https://git.heroku.com/sanpy.git (fetch)
heroku	https://git.heroku.com/sanpy.git (push)
origin	https://github.com/cudmore/bAnalysis.git (fetch)
origin	https://github.com/cudmore/bAnalysis.git (push)
```

## Heroku available runtime

```
python-3.10.0 on all supported stacks
python-3.9.7 on all supported stacks
python-3.8.12 on all supported stacks
python-3.7.12 on all supported stacks
python-3.6.15 on all supported stacks
```

## Clear heroku build cache

See: https://help.heroku.com/18PI5RSY/how-do-i-clear-the-build-cache

```
heroku plugins:install heroku-builds
heroku builds:cache:purge -a sanpy --confirm sanpy

# push an empty commit
git commit --allow-empty -m "Purge cache"
git push
```

## HEroku imports are failing

See: https://stackoverflow.com/questions/41412917/getting-error-importerror-no-module-named-on-heroku-but-not-locally

```
2021-10-24T21:24:24.600261+00:00 app[web.1]:     from .bAnalysisUtil import bAnalysisUtil
2021-10-24T21:24:24.600262+00:00 app[web.1]:   File "/app/.heroku/python/lib/python3.9/site-packages/sanpy/bAnalysisUtil.py", line 12, in <module>
2021-10-24T21:24:24.600262+00:00 app[web.1]:     import sanpy.useranalysis
2021-10-24T21:24:24.600262+00:00 app[web.1]: ModuleNotFoundError: No module named 'sanpy.useranalysis'
```


### Save as an excel file:

https://dash.plotly.com/dash-core-components/download

## Dec 2022 pulled from main readme

## Web Application (experimental and in development)

The browser based web application provides the same interface for analysis as the desktop application.

<IMG SRC="docs/docs/img/app2-interface.png" width=700 border=1>


Once data is analyzed, Pooling allows browsing detection parameters across any number of files.


<IMG SRC="docs/docs/img/pymy-pooling.png" width=700 border=1>

### Install the web application

Please note, this is experimental and does not have all functions implemented. Please use the desktop version instead.

```
cd SanPy/dash
pip install -r requirements.txt
```

### Running the web applications

Run the web application to analyze raw data

```
cd SanPy/dash
python app2.py
```

The web application for analysis is available at

```
http://localhost:8000
```

Run the web application to browse and pool saved analysis

```
cd SanPy/dash
python bBrowser_app.py
```

The web application for browsing and pooling saved analysis is available at

```
http://localhost:8050
```
