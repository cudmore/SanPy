This page describes how to install SanPy from the command-line.

If you want to download and run SanPy as a pre-built desktop application, please see our easy to follow [download sanpy](../download) page.

## Install from the command line

SanPy currently uses Python 3.13 and a pinned scientific stack. We recommend
[uv](https://docs.astral.sh/uv/) to create and manage the environment.

### Install SanPy from [PyPi](https://pypi.org/project/sanpy-ephys/)

!!! Important

    The SanPy package is named `sanpy-ephys`.

    Core library, without the desktop app:

        uv tool install --python 3.13 sanpy-ephys

    Matplotlib plots, including `sanpy.analysisPlot`, without the desktop app:

        uv tool install --python 3.13 "sanpy-ephys[plot]"

    Desktop app:

        uv tool install --python 3.13 "sanpy-ephys[gui]"

The same split works with pip: `pip install sanpy-ephys`,
`pip install "sanpy-ephys[plot]"`, and `pip install "sanpy-ephys[gui]"`.

### Run the GUI

    sanpy

## Install from a local source

For users interested in modifying the source code, install
[uv](https://docs.astral.sh/uv/getting-started/installation/) and Git.

1) Clone the repository

    git clone https://github.com/cudmore/SanPy.git

2) Install the locked environment

    cd SanPy

    Core library. `uv sync` does not install matplotlib or seaborn.
    `pip install .` still installs matplotlib, because pyabf 2.3.8 declares it
    and pip does not read uv's dependency metadata.

        uv sync --locked

    Matplotlib plots, including `sanpy.analysisPlot`:

        uv sync --locked --extra plot

    Desktop app and GUI tests:

        uv sync --locked --extra gui

    With pip, those are `pip install .`, `pip install ".[plot]"`, and
    `pip install ".[gui]"`.

3) Install NicePool for local development

    NicePool is a sibling package. It is not part of `sanpy-ephys[gui]`.
    From the SanPy repository root, after the GUI sync:

        (cd ../cs_project/mapmanager-web-components && npm run build --workspace @mapmanager/nicepool-pyqt5-frontend)

        uv pip install --python .venv/bin/python --editable \
          ../cs_project/mapmanager-web-components/integrations/nicepool-pyqt5

    `uv sync` removes that editable install. Run the `uv pip install` command
    again after every sync.

4) Run SanPy

    uv run sanpy

5) Run the tests

    uv run pytest

    The NicePool browser test stays skipped unless you set
    `SANPY_RUN_NICEPOOL_WEBENGINE_TEST=1` on a macOS machine that has the
    sibling package installed:

        SANPY_RUN_NICEPOOL_WEBENGINE_TEST=1 uv run pytest tests/interface/test_nicepool_plugin.py

    GitHub Actions installs the `gui` extra for the full test job and does not
    install mapmanager-web-components. It does not set
    `SANPY_RUN_NICEPOOL_WEBENGINE_TEST`, so that browser test stays skipped.
