## Whole cell recording analysis

## Detect action potentials

See
 - bBrowser.ipynb
 - ap.ipynb

```
abf = bLoadFile('data/171116sh_0018.abf')
sweepNumber = 15
spikeTimes = bSpikeDetect(abf, sweepNumber, dVthresholdPos=15)
bPlotSweep(abf, sweepNumber, spikeTimes=spikeTimes)
```

<IMG SRC="img/example1.png" width=600>

## Analyze action potentials

Coming soon, will plot current versus a number of AP parameters including: number, instantaneous frequency, spike threshold, ...

## Passive properties

Coming soon, will analyze and plot resting membrane potential, whole cell capacitance.

## ParamAP

[Github repository][paramap]

## Install Python 3.7.x and required libraries

Requires

 - Python >= 3.7
 - numpy
 - matplotlib
 - plotly
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
pip3 install plotly
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

## Change log

20190216, created the code and implemented ap detection


[python3]: https://www.python.org/downloads/
[pip3]: https://pip.pypa.io/en/stable/installing/
[pyabf]: https://github.com/swharden/pyABF
[paramap]: https://github.com/christianrickert/ParamAP
