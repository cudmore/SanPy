
[![Python](https://img.shields.io/badge/python-3.8|3.9|3.10|3.11-blue.svg)](https://www.python.org/downloads/release/python-3111/)
[![tests](https://github.com/cudmore/SanPy/workflows/Test/badge.svg)](https://github.com/cudmore/SanPy/actions)
[![codecov](https://codecov.io/gh/cudmore/SanPy/branch/master/graph/badge.svg?token=L7L3FB04IP)](https://codecov.io/gh/cudmore/SanPy)
[![OS](https://img.shields.io/badge/OS-Linux|Windows|macOS-blue.svg)]()
[![License](https://img.shields.io/badge/license-GPLv3-blue)](https://github.com/cudmore/SanPy/blob/master/LICENSE)


## SanPy is software for whole-cell current clamp analysis

It is designed to analyze action potentials and extract a number of parameters including spike time, voltage threshold, half-widths, interval statistics, and lots more.

Originally designed for cardiac myocytes, we have been busy extending SanPy to handle a wide range of whole-cell current clamp recordings including neurons.

## Please see our [documentation website](https://cudmore.github.io/SanPy/).

## Desktop Application

We provide desktop applications for macOS and Windows users. Go to the [download page](https://cudmore.github.io/SanPy/download/) to get started. No command line, no complicated installation, just an easy to use point and click GUI!

<IMG SRC="docs/docs/img/sanpy-app.png" width=600>

## Plugins
 
The desktop application comes bundled with a growing number of plugins. See our [plugin documentation page](https://cudmore.github.io/SanPy/plugins/).

<table style="border=1px">
<tr>
    <td>
    <IMG SRC="docs/docs/img/plugins/plot-recording.png" width=300>
    </td>
    <td>
    <IMG SRC="docs/docs/img/plugins/spike-clips.png" width=300>
    </td>
</tr>
<tr>
    <td>
    <IMG SRC="docs/docs/img/plugins/plot-fi.png" width=300>
    </td>
    <td>
    <IMG SRC="docs/docs/img/plugins/scatter-plot.png" width=300>
    </td>
</tr>
</table>

## Contact

If you find the code in this repository interesting, please email Robert Cudmore at UC Davis (rhcudmore@ucdavis.edu) and we can get you started. We are looking for users and collaborators.

## Contributing to SanPy

To install SanPy from source, see our [install instructions](https://cudmore.github.io/SanPy/install/).

To make SanPy extensible, users create their own file loaders, analysis, and plugins. Please see our [API documentation](https://cudmore.github.io/SanPy/api/overview) with lots of examples to get started.
