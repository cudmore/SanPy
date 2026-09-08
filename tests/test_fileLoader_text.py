"""Tests for the canonical ``.sanpy`` text loader."""

import numpy as np
import pandas as pd
import pytest

from sanpy.fileloaders.fileLoader_csv import fileLoader_text


def _write_sanpy(tmp_path, data: dict, name: str = "recording.sanpy"):
    path = tmp_path / name
    pd.DataFrame(data).to_csv(path, index=False)
    return path


def test_loads_sweeps_commands_and_per_sweep_epochs(tmp_path):
    path = _write_sanpy(
        tmp_path,
        {
            "seconds": np.arange(6) * 0.0001,
            "epoch_index": [0, 0, 1, 1, 2, 2],
            "mv_0": [-60, -59, -58, -57, -56, -55],
            "cmd_0": [0, 0, 1, 1, 0, 0],
            "mv_1": [-61, -60, -59, -58, -57, -56],
            "cmd_1": [0, 0, 2, 2, 0, 0],
        },
    )

    loader = fileLoader_text(str(path))

    assert not loader.getLoadError()
    assert loader.numSweeps == 2
    assert loader.sweepList == [0, 1]
    expected_levels = ([0.0, 1.0, 0.0], [0.0, 2.0, 0.0])
    for sweep, levels in enumerate(expected_levels):
        epochs = loader.getEpochTable(sweep).getEpochList()
        assert [epoch["index"] for epoch in epochs] == [0, 1, 2]
        assert [(epoch["startPoint"], epoch["stopPoint"]) for epoch in epochs] == [
            (0, 2),
            (2, 4),
            (4, 6),
        ]
        assert [epoch["level"] for epoch in epochs] == list(levels)


def test_epoch_index_is_optional(tmp_path):
    path = _write_sanpy(
        tmp_path,
        {
            "seconds": [0.0, 0.001, 0.002],
            "mv_0": [-60.0, -59.0, -58.0],
        },
    )

    loader = fileLoader_text(str(path))

    assert not loader.getLoadError()
    assert loader.getEpochTable(0) is None


@pytest.mark.parametrize(
    "epoch_indices",
    (
        [1, 1, 2, 2],
        [0, 0, 2, 2],
        [0, 1, 0, 1],
        [0.0, 0.0, 1.0, 1.0],
    ),
)
def test_rejects_invalid_epoch_indices(tmp_path, epoch_indices):
    path = _write_sanpy(
        tmp_path,
        {
            "seconds": [0.0, 0.001, 0.002, 0.003],
            "epoch_index": epoch_indices,
            "mv_0": [-60.0, -59.0, -58.0, -57.0],
            "cmd_0": [0.0, 0.0, 1.0, 1.0],
        },
    )

    assert fileLoader_text(str(path)).getLoadError()


def test_rejects_nonconstant_command_within_epoch(tmp_path):
    path = _write_sanpy(
        tmp_path,
        {
            "seconds": [0.0, 0.001, 0.002, 0.003],
            "epoch_index": [0, 0, 1, 1],
            "mv_0": [-60.0, -59.0, -58.0, -57.0],
            "cmd_0": [0.0, 0.1, 1.0, 1.0],
        },
    )

    assert fileLoader_text(str(path)).getLoadError()


def test_rejects_noncanonical_column_order(tmp_path):
    path = _write_sanpy(
        tmp_path,
        {
            "seconds": [0.0, 0.001],
            "epoch_index": [0, 0],
            "cmd_0": [0.0, 0.0],
            "mv_0": [-60.0, -59.0],
        },
    )

    assert fileLoader_text(str(path)).getLoadError()
