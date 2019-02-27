# ParamAP
**Standardized parameterization of sinoatrial node myocyte action potentials**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.823742.svg)](https://doi.org/10.5281/zenodo.823742)

ParamAP is a standalone computational tool that uses a template-free detection algorithm to automatically identify and parameterize sinoatrial myocyte action potentials.  ParamAP is written in Python 3 and it can be run on Windows, Mac OS X, or Ubuntu operating systems.  It employs a graphic user interface with automatic and user-editable input modes.  ParamAP accepts text input files and returns a total of 16 AP waveform parameters as text and graphical outputs. The software is available under the [GNU General Public License 2](https://github.com/crickert1234/ParamAP/blob/master/LICENSE).

![Screenshot of a parameterization summary](https://github.com/crickert1234/ParamAP/blob/master/img/ParamAP-Screenshot.png)

## Hardware requirements
ParamAP can be run on any computer for which [Python 3](https://www.python.org/downloads/) and the libraries [NumPy](https://www.scipy.org/scipylib/download.html), [SciPy](https://www.scipy.org/install.html), and [Matplotlib](https://matplotlib.org/users/installing.html) are available, which includes most common processor architectures and operating systems (Mac OS X, Linux/Ubuntu, Windows).  The minimum system requirements are very modest (~ 2 GB system memory, 1 GHz processor frequency,  and at least 1 GB of free disk space).  As a general rule, the minimum memory required is approximately ten times the largest file size to be analyzed, which depends on the data sampling rate and the length of the recording to be read.

## Software requirements
The minimum software requirements for ParamAP are current versions of:
* `Python 3`
* `NumPy`
* `SciPy`
* `Matplotlib`

## Softare download
The latest versions of ParamAP can be found on the repository's [releases](https://github.com/crickert1234/ParamAP/releases) page.

## Installation & Usage
Please consult the [User Manual](https://github.com/crickert1234/ParamAP/releases/download/v1.0.1/ParamAP-1.0-Manual.pdf) for information on how to install and use ParamAP.

## Development & Bug reporting
If you would like to participate in the development of ParamAP, please [fork this repository](https://help.github.com/articles/fork-a-repo) to your GitHub account. In order to report a problem with ParamAP, please login to your GitHub account and create a [new issue](https://help.github.com/articles/creating-an-issue/) in this repository.

Your feedback is welcome! Please contact us using [GitHub](https://github.com/crickert1234/) or via [e-mail](mailto:Christian.Rickert@ucdenver.edu).
