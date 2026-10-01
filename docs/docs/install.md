This page describes how to install SanPy from the command-line.

If you want to download and run SanPy as a pre-built desktop application, please see our easy to follow [download sanpy](../download) page.

## Install from the command line

SanPy currently uses Python 3.13 and a pinned scientific stack. We recommend
[uv](https://docs.astral.sh/uv/) to create and manage the environment.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git.

1) Clone the repository

    git clone https://github.com/cudmore/SanPy.git

2) Install the environment

    cd SanPy

    Core library:

        uv sync

    Desktop app and GUI tests:

        uv sync --extra gui

    Matplotlib plots, including `sanpy.analysisPlot`:

        uv sync --extra plot

    With pip, those are `pip install .`, `pip install ".[gui]"`, and
    `pip install ".[plot]"`.

3) Install NicePool for local development

    NicePool is a sibling package. It is not part of `sanpy-ephys[gui]`.
    From the SanPy repository root, after the GUI sync:

        (cd ../mapmanager-web-components && npm run build --workspace @mapmanager/nicepool-pyqt5-frontend)

        uv pip install --python .venv/bin/python --editable \
          ../mapmanager-web-components/integrations/nicepool-pyqt5

    `uv sync` removes that editable install. Run the `uv pip install` command
    again after every sync.

4) Run SanPy

    uv run sanpy

    The first time you run from the command line will take some time. Please be patient.

5) Run the tests

    uv run pytest

    That command includes the NicePool browser test when `nicepool_pyqt5` is
    installed. The test is skipped when that package is not installed.
