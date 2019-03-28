## Whole cell recording analysis

This repository has code to perform action potential analysis. It is primarily designed to analyze spontaneous action potentials from cardiac myocytes.

## Install

We assume you have Python 3.7.x and pip installed.

```
# clone the repository
git clone https://github.com/cudmore/bAnalysis.git

# change into the downloaded folder
cd bAnalysis

# create a Python3 virtual environment and activate it
mkdir bAnalysis_env
virtualenv -p python3 --no-site-packages bAnalysis_env
source bAnalysis_env/bin/activate

# install the required python packages
pip install -r requirements.txt
		
# run the graphical-user-interface
python spike-analysis-app/src/AnalysisApp.py
```

## Application

<IMG SRC="img/spike-app.png" width=700>

## Writing your own Python scripts

See `bBrowser.ipynb`

```
abf = bLoadFile('data/171116sh_0018.abf')
sweepNumber = 15
spikeTimes = bSpikeDetect(abf, sweepNumber, dVthresholdPos=15)
bPlotSweep(abf, sweepNumber, spikeTimes=spikeTimes)
```

<IMG SRC="img/example1.png" width=600>

## Install Python 3.7.x and required libraries

Requires

 - Python >= 3.7
 - numpy
 - pandas
 - matplotlib
 - scipy
 - pyabf - download from https://github.com/swharden/pyABF


[Download][python3] and install Python 3.x

Install [pip3][pip3] (if neccessary)

```
# first, check if you have pip3
pip3

# if not, then install
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```

Install jupyter, numpy, matplotlib, plotly

```
pip3 install jupyter
pip3 install numpy
pip3 install matplotlib
pip3 install pandas
pip3 install plotly

# to export pandas data frame to excel
pip3 install openpyxl
```

Install [pyabf][pyabf]

```
pip install pyabf
```

## Running a notebook locally

Clone the bAnalysis repository (this repository)

```
git clone https://github.com/cudmore/bAnalysis.git
```

Change into the bAnalysis folder

```
cd bAnalysis
```

Depending on how you install jupyter/ipython, either

```
jupyter notebook

#or
ipython3 notebook
```

## ParamAP

[Github repository][paramap]

## Change log

20190216, created the code and implemented ap detection


[python3]: https://www.python.org/downloads/
[pip3]: https://pip.pypa.io/en/stable/installing/
[pyabf]: https://github.com/swharden/pyABF
[paramap]: https://github.com/christianrickert/ParamAP
