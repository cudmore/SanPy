
[![Build Status](https://travis-ci.org/cudmore/SanPy.svg?branch=master)](https://travis-ci.org/cudmore/SanPy)

## SanPy, pronounced ['senpai']['senpai']

['senpai']: https://en.wikipedia.org/wiki/Senpai_and_k%C5%8Dhai

## Whole cell myocyte action potential analysis

This repository has code to perform [cardiac action potential][cardiac action potential] analysis. It is primarily designed to analyze spontaneous cardiac action potentials from whole-cell current-clamp recordings of [cardiac myocytes].

[cardiac action potential]: https://en.wikipedia.org/wiki/Cardiac_action_potential
[cardiac myocytes]: https://en.wikipedia.org/wiki/Cardiac_muscle_cell

## Please see our documentation website

[https://cudmore.github.io/SanPy/][https://cudmore.github.io/SanPy/]

['sanpy-docs']: https://cudmore.github.io/SanPy/

## This is a work in progress, do not use this code.

If you find the code in this repository interesting, please email Robert Cudmore at UC Davis (rhcudmore@ucdavis.edu) and we can get you started. We are looking for users and collaborators.

## Desktop Application

The desktop application allows the user to load a folder of files (top table). Selecting a file will display both the derivative and raw membrane potential (middle two traces). Spike detection is then easily performed by specifying a threshold in either the derivative of the membrane potential or the membrane potential itself. Once spikes are detected, the detection parameters are overlaid over the raw membrane and derivative traces. Finally, there is an interface (lower table and colored plot) to inspect the detection parameters.


<IMG SRC="docs/docs/img/spike-app.png" width=700>


<IMG SRC="docs/docs/img/meta-window-example.png" width=700>

## Writing custom Python scripts

In just a few lines of code, recordings can be loaded, analyzed, and plotted. See the [/examples](examples) folder for examples.

```
import matplotlib.pyplot as plt
import bAnalysis
import bAnalysisPlot

ba = bAnalysis.bAnalysis('data/SAN-AP-example-Rs-change.abf')
ba.spikeDetect()

bAnalysisPlot.bPlot.plotSpikes(ba, xMin=140, xMax=145)
plt.show()
```

<IMG SRC="docs/docs/img/example1.png" width=600>

## Install

This code will run on macOS, Microsoft Windows, or Linux.

Assuming you have the following

 - [Python 3.7.x][python3]
 - [pip][pip]
 - [git][git] (optional)

### Install the desktop application

##### Option 1) Install using ./install

```
# If you have git installed.
# Clone the github repository (this will create a SanPy/ folder).
git clone https://github.com/cudmore/SanPy.git

# If you do not have git installed you can download the .zip file manually.
# In a browser, go to 'https://github.com/cudmore/SanPy'.
# Click green button 'Clone or download'.
# Select 'Download ZIP'.
# Once downloaded, manually extract the contents of the .zip file and continue following this tutorial.

# Change into the cloned or downloaded 'SanPy/' folder.
cd SanPy

# Install
./install

# Run
./run
```

##### Option 2) Install manually

```
# clone the github repository (this will create a SanPy/ folder)
git clone https://github.com/cudmore/SanPy.git

# change into the cloned SanPy folder
cd SanPy

# create a Python3 virtual environment in 'sanpy_env/' folder
python -m venv sanpy_env

# [OR] if python is bound to Python 2 (check with 'python --version')

python3 -m venv sanpy_env

# activate the virtual environment in sanpy_env/
source sanpy_env/bin/activate

# install the package
pip install .

# [OR] install the required python packages (into the activated virtual environment)
# pip install -r requirements.txt
```

### Running the desktop application

##### Option 1) Using ./run

```
cd SanPy
./run
```

##### Option 2) Manually

```
# activate the virtual environment in sanpy_env/
cd SanPy
source sanpy_env/bin/activate

# run the desktop application
python sanpy/sanpy_app.py
```

## Web Application

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

## What spike parameters are detected?

We are following the cardiac myocyte nomenclature from this paper:

[Larson, et al (2013) Depressed pacemaker activity of sinoatrial node
myocytes contributes to the age-dependent decline in maximum heart rate. PNAS 110(44):18011-18016][larson et al 2013]

- MDP and Vmax were defined as the most negative and positive membrane potentials, respectively
- Take-off potential (TOP) was defined as the membrane potential when the first derivative of voltage with respect to time (dV/dt) reached 10% of its maximum value
- Cycle length was defined as the interval between MDPs in successive APs
- The maximum rates of the AP upstroke and repolarization were taken as the maximum and minimum values of the first derivative (dV/dtmax and dV/dtmin, respectively)
- Action potential duration (APD) was defined as the interval between the TOP and the subsequent MDP
- APD_50 and APD_90 were defined as the interval between the TOP and 50% and 90% repolarization, respectively
- The diastolic duration was defined as the interval between MDP and TOP
- The early diastolic depolarization rate was estimated as the slope of a linear fit between 10% and 50% of the diastolic duration and the early diastolic duration was the corresponding time interval
- The nonlinear late diastolic depolarization phase was estimated as the duration between 1% and 10% dV/dt

[larson et al 2013]: https://www.ncbi.nlm.nih.gov/pubmed/24128759

## Why is this useful?

We provide a Python library that can load, analyze, save, and plot eletropysiology recordings. This library is then accessed through simple to use graphical user interfaces (GUIs) with either a traditional desktop or web based application. Finally, the same code that drives the user interface can be scripted. In just a few lines of code, the exact same loading, analysis, saving, and plotting can be performed as is done with the GUIs.

## Why is this important?

When you publish a paper, you need to ensure your primary data is available for interogation and that your analysis can be reproduced. This software facilitates that by allowing you to share the raw data, provide the code that was used to analyze it, and explicity show how it was analyzed such that it can be verified and reproduced.

## Technologies used

#### Backend

 - [Python][Python]
 - [Pandas][Pandas]
 - [NumPy][NumPy]
 - [pyABF][pyABF] - Package to open Axon Binary Format (ABF) files
 - [XlsxWriter][XlsxWriter]
 -
#### Desktop Application

 - [PyQt][PyQt] - Desktop application interface
 - [PyQtGraph][pyqtgraph] - Derived from PyQt and used to make fast plots
 - [Matplotlib][Matplotlib] - Desktop application plotting

#### Web application

 - [Plotly Python][Plotly]
 - [Plotly Dash][Dash] - Web application interface
 - [Dash Bootstrap components][Dash Bootstrap components]

[Python]: https://www.python.org/
[Pandas]: https://pandas.pydata.org/
[NumPy]: https://www.numpy.org/
[pyABF]: https://github.com/swharden/pyABF
[TkInter]: https://docs.python.org/3/library/tkinter.html
[PyQt]: https://riverbankcomputing.com/software/pyqt/intro
[pyqtgraph]: http://www.pyqtgraph.org/
[XlsxWriter]: https://xlsxwriter.readthedocs.io/
[Matplotlib]: https://matplotlib.org/
[Plotly]: https://plot.ly/python/
[Dash]: https://plot.ly/products/dash/
[Dash Bootstrap components]: https://dash-bootstrap-components.opensource.faculty.ai/

## Other software

 - [ParamAP][ParamAP] - Standardized parameterization of sinoatrial node myocyte action potentials
 - [stimfit][stimfit] - A program for viewing and analyzing electrophysiological data

C++ libraries

 - [biosig][biosig] - A C/C++ library providing reading and writing routines for biosignal data formats
 - [sigviewer][sigviewer] - SigViewer is a viewing application for biosignals.

[ParamAP]: https://github.com/christianrickert/ParamAP
[stimfit]: https://github.com/neurodroid/stimfit
[biosig]: http://biosig.sourceforge.net/projects.html
[sigviewer]: https://github.com/cbrnr/sigviewer

## Advanced

#### Building a stand alone app (macOS)

Install pyinstaller

    pip install pyinstaller

Make the app

    cd SanPy
    ./makeapp

You can find the app in `dist/SanPy.app`.

#### Download the AnalysisApp

**This is not available yet.** We will eventually distribute a precompiled application for macOS, Microsoft Windows, an Linux.

Be sure to download the .zip file by clicking the triple tilde '...' on the top-right of the page and select download.

Once you have the .zip file ...

When you run the app you will see a dialog telling you 'Can't be opened because it is from an unidentified developer'.

You need to go into your 'Apple Menu - System Preferences - Security & Privacy'

Find the part that says "SpikeAnalysis... was blocked from opening because it is not from an identified developer" and click "Open Anyway"

After that, you are good to go!

[python3]: https://www.python.org/downloads/
[pip]: https://pip.pypa.io/en/stable/
[pyabf]: https://github.com/swharden/pyABF
[paramap]: https://github.com/christianrickert/ParamAP
[git]: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git
[virtualenv]: https://virtualenv.pypa.io/en/stable/

## Change log

 - 20190216, Created the code and implemented ap detection
 - 20190518, Started making web application (fairly complete as of 20190601)

## To Do

 - Set from/to (sec) when user zooms by dragging on graph
 - get file table to update when analysis is saved

### 20190326

 - Save analysis csv file and reload when loading folder. Don't always require re-analysis. Will break when format of csv file changes, make sure to include a file version.
 - Implement all stats used by Larson ... Proenza (2013) paper.
 - Show average spike clip in red
 - Export average spike clip
 - Take all stats on average spike clip. Is it different from taking average across all spikes?

### 20190329

Done:
 - 'Save Spike Report' now prompts for a file name
 - Added checkbox option to hide/show spike clips. It was getting too slow to always show spike clips when there are a ton of spikes. When you want to see them, you just turn it on.
 - Excel file column width are now (sanely) wider
 - Added max upstroke and min downstroke dV/dt to excel report
 - Added spike errors to excel report

To Do:
 - Convert ALL reported units to milli-seconds
 - Add new window to plot stats on x/y. For example, peak AP amplitude (mV) versus spike width (ms).

### 20190329
 - Gave new code to Laura that does pure Vm detection
 - New after giving Laura code
 - Meta plot will remember last stat plot when switching files, when first run it defaults to 'Spike Frequency (Hz)'
 - Median filter needs to be odd, if even value is specified we tweek it to odd
