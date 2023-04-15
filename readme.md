
[![Python](https://img.shields.io/badge/python-3.8|3.9|3.10|3.11-blue.svg)](https://www.python.org/downloads/release/python-3111/)
[![tests](https://github.com/cudmore/SanPy/workflows/Test/badge.svg)](https://github.com/cudmore/SanPy/actions)
[![codecov](https://codecov.io/gh/cudmore/SanPy/branch/master/graph/badge.svg?token=L7L3FB04IP)](https://codecov.io/gh/cudmore/SanPy)
[![OS](https://img.shields.io/badge/OS-Linux|Windows|macOS-blue.svg)]()
[![License](https://img.shields.io/badge/license-GPLv3-blue)](https://github.com/cudmore/SanPy/blob/master/LICENSE)


## SanPy is software for whole-cell current clamp analysis

Originally designed for cardiac myocytes, we have been busy extending SanPy to handle most whole-cell current clamp recordings and analysis including neurons.

## Please see our [documentation website](https://cudmore.github.io/SanPy/).

## Desktop Application

We now provide [macOS and Windows downloads](https://cudmore.github.io/SanPy/download/) to run the desktop application. No command line, no complicated installation, just an easy to use point and click GUI.

<IMG SRC="docs/docs/img/sanpy-app.png" width=600>

## Desktop Application - Plugins
 
The desktop application comes bundled with a growing number of plugins. See our [plugin documentation page](https://cudmore.github.io/SanPy/plugins/).

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

Please see the [install instructions](https://cudmore.github.io/SanPy/install/) on the documentation website.

## Writing custom Python scripts

We realize that SanPy need to be extensible. To acheive this we have created software architectures such that our programming users can write custom file loders, create new analysis, and even create full GUI plugins. Please see our [API documentation](https://cudmore.github.io/SanPy/scripting/) with lots of examples to get started.

If you find the code in this repository interesting, please email Robert Cudmore at UC Davis (rhcudmore@ucdavis.edu) and we can get you started. We are looking for users and collaborators.