"""Tests for SanPy text acquisition snapshot extraction."""

from pathlib import Path

import numpy as np

import sanpy
from sanpy.io.zarr_export.sanpy_file_adapter import snapshot_sanpy


def test_snapshot_sanpy_preserves_sweep_epochs(sanpy_data_folder: Path) -> None:
    """Copy every text sweep and its sweep-specific epoch levels.

    Args:
        sanpy_data_folder: Data folder containing the canonical source file.
    """
    source = sanpy_data_folder / "stochastic-hh.sanpy"
    analysis = sanpy.bAnalysis(str(source))

    snapshot = snapshot_sanpy(analysis)

    assert snapshot.raw.shape == (15, 1, 100001)
    assert snapshot.command.shape == snapshot.raw.shape
    assert snapshot.epochs.groupby("sweep").size().tolist() == [4] * 15
    epoch_two = snapshot.epochs.query("epoch == 2").sort_values("sweep")
    expected_levels = [
        analysis.fileLoader.getEpochTable(sweep).getLevel(2)
        for sweep in analysis.fileLoader.sweepList
    ]
    np.testing.assert_array_equal(epoch_two["level"], expected_levels)
    assert set(snapshot.epochs["channel"]) == {0}
    assert snapshot.source_format == "sanpy"
