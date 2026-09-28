"""Tests for immutable metadata finalized by file loaders."""

from dataclasses import FrozenInstanceError, fields
import pyabf
import pytest
import numpy as np

from sanpy.fileloaders.epochTable import epochTable
from sanpy.fileloaders.fileLoader_base import fileLoader_base
from sanpy.fileloaders.fileLoader_abf import fileLoader_abf
from sanpy.fileloaders.fileMetadata import FileMetadata
from sanpy.io.zarr_export.json_codec import json_value


class _InconsistentEpochLoader(fileLoader_base):
    """Synthetic loader containing different epoch counts per sweep."""

    loadFileType = ".synthetic"

    def loadFile(self) -> None:
        """Create two sweeps with intentionally inconsistent epoch tables."""
        sweep_x = np.arange(4, dtype=np.float64)[:, np.newaxis] * 0.001
        sweep_y = np.zeros((4, 2), dtype=np.float64)
        self.setLoadedData(sweep_x, sweep_y, xLabel="sec", yLabel="mV")
        first = epochTable()
        second = epochTable()
        first.addEpoch(0, 0.0, 0.004, 1, 0.0)
        second.addEpoch(1, 0.0, 0.002, 1, 0.0)
        second.addEpoch(1, 0.002, 0.004, 1, 1.0)
        self._epochTableList = [first, second]


def test_file_metadata_is_immutable_and_json_compatible() -> None:
    """Keep field values immutable while converting tuples to JSON arrays."""
    metadata = FileMetadata(
        acq_date="2026-09-28",
        acq_time="12:34:56",
        acq_datetime="2026-09-28 12:34:56.123456",
        num_channels=2,
        num_sweeps=3,
        num_epochs=None,
        sweep_label_x="sec",
        sweep_label_y="mV",
        mode="I-Clamp",
        recording_frequency_khz=10.0,
        user_list=(1.0, 2.0),
    )

    with pytest.raises(FrozenInstanceError):
        metadata.num_sweeps = 4  # type: ignore[misc]

    value = json_value(metadata)
    assert value["user_list"] == [1.0, 2.0]
    assert [item.metadata["display_name"] for item in fields(FileMetadata)] == [
        "Acquisition Date",
        "Acquisition Time",
        "Acquisition Date and Time",
        "Number of Channels",
        "Number of Sweeps",
        "Epochs per Sweep",
        "X-Axis Label",
        "Y-Axis Label",
        "Recording Mode",
        "Recording Frequency (kHz)",
        "ABF User List",
    ]


def test_abf_file_metadata_matches_source_header() -> None:
    """Finalize ABF acquisition facts and preserve compatibility properties."""
    source_path = "tests/data/2021_07_20_0010.abf"
    source = pyabf.ABF(source_path)
    loader = fileLoader_abf(source_path)
    metadata = loader.fileMetadata

    assert metadata.acq_date == source.abfDateTime.strftime("%Y-%m-%d")
    assert metadata.acq_time == source.abfDateTime.strftime("%H:%M:%S")
    assert metadata.acq_datetime == source.abfDateTime.isoformat(sep=" ")
    assert metadata.num_channels == len(source.adcUnits) == 2
    assert metadata.num_sweeps == len(source.sweepList) == loader.numSweeps
    assert metadata.num_epochs == loader.numEpochs == 5
    assert metadata.recording_frequency_khz == loader.recordingFrequency == 10.0
    assert loader._sweepY.shape[1] == metadata.num_sweeps


def test_inconsistent_epoch_counts_remain_loadable(caplog: pytest.LogCaptureFixture) -> None:
    """Warn and omit the scalar summary when per-sweep counts differ.

    Args:
        caplog: Pytest log-capture fixture.
    """
    loader = _InconsistentEpochLoader("synthetic")

    assert not loader.getLoadError()
    assert loader.fileMetadata.num_epochs is None
    assert "Could not represent one epoch count per sweep" in caplog.text
