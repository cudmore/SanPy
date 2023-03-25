
[![Python](https://img.shields.io/badge/python-3.7|3.8|3.9|3.10|3.11-blue.svg)](https://www.python.org/downloads/release/python-3111/)
[![tests](https://github.com/cudmore/SanPy/workflows/Test/badge.svg)](https://github.com/cudmore/SanPy/actions)
[![codecov](https://codecov.io/github/cudmore/SanPy/branch/master/graph/badge.svg?token=0ZR226588I)](https://codecov.io/github/cudmore/SanPy)
[![OS](https://img.shields.io/badge/OS-Linux|Windows|macOS-blue.svg)]()
[![License](https://img.shields.io/badge/license-GPLv3-blue)](https://github.com/cudmore/SanPy/blob/master/LICENSE)

## SanPy is software for whole-cell current clamp analysis

Originally designed for cardiac myocytes, we have been busy extending SanPy to handle most whole-cell current clamp recordings and analysis including neurons.

SanPy is pronounced ['senpai']['senpai']

['senpai']: https://en.wikipedia.org/wiki/Senpai_and_k%C5%8Dhai

If you find the code in this repository interesting, please email Robert Cudmore at UC Davis (rhcudmore@ucdavis.edu) and we can get you started. We are looking for users and collaborators.

## Please see our documentation website

[https://cudmore.github.io/SanPy/](https://cudmore.github.io/SanPy/)

['sanpy-docs']: https://cudmore.github.io/SanPy/

## Desktop Application

**Soon** we will be providing one file downloads to run the desktop application.


<!-- <IMG SRC="docs/docs/img/spike-app.png" width=600> -->
<IMG SRC="docs/docs/img/sanpy-app.png" width=600>

<!-- <IMG SRC="docs/docs/img/meta-window-example.png" width=600> -->

## Desktop Application - Plugins

The desktop application comes bundled with a growing number of plugins. See our [plugin documentation page](docs/docs/plugins).

<table>
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

## Install from source

Please see the [install instructions](docs/docs/install) on the documentation website.

## Writing custom Python scripts

Please see our [API documentation](docs/docs/scripting.ipynb) with some examples to get started.

## Why is this useful?

We provide a Python package that can load, analyze, plot, and save eletropysiology recordings. This package is then accessed through a desktop application with a simple to use graphical user interface (GUI). Finally, the same code that drives the GUI  can be scripted. In just a few lines of code, the exact same loading, analysis, plotting, saving can be performed as is done with the GUIs.

## Why is this important?

When you publish a paper, you need to ensure your primary data is available for interogation and that your analysis can be reproduced. This software facilitates that by allowing you to share the raw data, provide the code that was used to analyze it, and explicity show how it was analyzed such that it can be verified and reproduced.

