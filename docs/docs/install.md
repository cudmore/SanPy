This page describes how to install SanPy from the command-line.

If you want to download and run SanPy as a pre-built desktop application, please see our easy to follow [download sanpy](../download) page.

## Install from the command line

SanPy currently uses Python 3.11 and a pinned scientific stack. We recommend
[uv](https://docs.astral.sh/uv/) to create and manage the environment.

### Install SanPy from [PyPi](https://pypi.org/project/sanpy-ephys/)

!!! Important

    The SanPy package is named `sanpy-ephys`.

    uv tool install --python 3.11 sanpy-ephys

### Run the GUI

    sanpy

## Install from a local source

For users interested in modifying the source code, install
[uv](https://docs.astral.sh/uv/getting-started/installation/) and Git.

1) Clone the repository

    git clone https://github.com/cudmore/SanPy.git

2) Install the locked SanPy development environment

    cd SanPy
    uv sync --locked

3) Run SanPy

    uv run sanpy

4) Run the tests

    Run the groups in separate processes to avoid a known PyQt teardown crash.

    uv run pytest tests/test_analysisDir.py
    uv run pytest tests/test_analysis.py tests/test_detection.py tests/test_fileLoader.py tests/test_metadata.py
    uv run pytest tests/interface
