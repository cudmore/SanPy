SanPy is designed to run on: macOS, Microsoft Windows, and Linux.

## Download the SanPy app.

We are building SanPy desktop applications so users can download a single file and get working with just a double-click. This does not require anything special on our users end. **No programming, no installing Python, and no command line**. See our [download](../download) page.

## Install from the command line

Create and activate a virtual environment with either `conda` or `venv`.

!!! Important

    M1/2 Mac users need to use a [Conda][mini-conda] environment as the arm64 versions of a number of Python packages are not available on PyPi (e.g. with pip install).

[mini-conda]: https://docs.conda.io/en/latest/miniconda.html

### Either create a `conda` environment

    conda create -y -n sanpy-env python=3.9
    conda activate sanpy-env

### Or create a `venv` environment

    python -m venv sanpy-env
    
    # macOS activate the environment
    source sanpy-env/bin/activate

    # Windows activate the environment
    sanpy-env\Scripts\activate

### Install SanPy from [PyPi](https://pypi.org/project/sanpy-ephys/)

!!! Important

    The SanPy package is named `sanpy-ephys`.

```
pip install "sanpy-ephys[gui]"
```

### Run the GUI

    sanpy

## Install from a local source

For users interested in modifying the source code, you can clone the GitHub repository and install from local source.

Be sure to create and activate a virtual environment (See above).

Assuming you have the following

 - [Python > 3.8][python3]
 - [pip][pip]
 - [git][git]

[python3]: https://www.python.org/downloads/
[pip]: https://pip.pypa.io/en/stable/
[git]: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git

1) Clone the repository

    git clone https://github.com/cudmore/SanPy.git

2) Install SanPy

    cd SanPy
    pip install -e ".[gui]"

4) Run `sanpy`

    sanpy

5) Have fun