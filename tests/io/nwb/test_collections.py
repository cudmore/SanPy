"""Focused tests for local Dandiset and remote NWB collection boundaries."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import h5py
import numpy as np

import sanpy
from sanpy.io.nwb.dandiset import (
    DandisetMetadata,
    read_dandiset,
    write_dandiset,
)
from sanpy.io.nwb.recording import NwbRecordingMetadata, write_recording
from sanpy.io.nwb.remote import RemoteNwbAsset, read_remote_recording


class _AnalysisDirectory:
    """Provide the public analysis-directory method needed by the writer."""

    def __init__(self, analyses: dict[int, Any]) -> None:
        """Initialize selected test analyses.

        Args:
            analyses: Analyses keyed by source row.
        """
        self._analyses = analyses

    def getAnalysis(self, row: int, allowAutoLoad: bool = True) -> Any:
        """Return one selected analysis.

        Args:
            row: Source row index.
            allowAutoLoad: Compatibility flag accepted by ``analysisDir``.

        Returns:
            Analysis at the requested row.
        """
        del allowAutoLoad
        return self._analyses[row]


class _LocalTransport:
    """Expose a local NWB file through the remote transport protocol."""

    def __init__(self, path: Path) -> None:
        """Initialize the test transport.

        Args:
            path: Local NWB file to expose.
        """
        self._path = path

    @contextmanager
    def open_h5(self, content_url: str) -> Iterator[h5py.File]:
        """Open the configured local HDF5 file.

        Args:
            content_url: Expected fake content URL.

        Yields:
            Read-only local HDF5 file.
        """
        assert content_url == "https://example.invalid/recording.nwb"
        with h5py.File(self._path, "r") as h5_file:
            yield h5_file


def _recording_metadata(subject_id: str) -> NwbRecordingMetadata:
    """Create explicit test recording metadata.

    Args:
        subject_id: Subject identifier for the recording.

    Returns:
        Valid recording metadata.
    """
    return NwbRecordingMetadata(
        subject_id=subject_id,
        cell_id=f"cell-{subject_id}",
        species="Mus musculus",
        session_start_time=datetime(2021, 5, 20, 12, 54, tzinfo=timezone.utc),
        age="P90D",
        sex="U",
    )


def test_remote_transport_uses_shared_decoder(
    tmp_path: Path, test_data_dir: Path
) -> None:
    """Materialize a fake remote asset through the normal NWB loader.

    Args:
        tmp_path: Pytest-managed output directory.
        test_data_dir: Stable SanPy test-data directory.
    """
    source = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    local_path = write_recording(
        source, tmp_path / "source.nwb", _recording_metadata("remote")
    )
    asset = RemoteNwbAsset(
        dandiset_id="000001",
        version="0.1.0",
        asset_id="asset-1",
        path="sub-remote/recording.nwb",
        content_url="https://example.invalid/recording.nwb",
    )

    restored = read_remote_recording(asset, transport=_LocalTransport(local_path))

    assert not restored.loadError
    np.testing.assert_allclose(
        restored.fileLoader.get_sweep_y(0), source.fileLoader.get_sweep_y(0)
    )
    assert restored.fileLoader.filepath == asset.path


def test_local_dandiset_round_trip(
    tmp_path: Path, test_data_dir: Path
) -> None:
    """Write selected rows atomically and reopen both organized assets.

    Args:
        tmp_path: Pytest-managed output directory.
        test_data_dir: Stable SanPy test-data directory.
    """
    first = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    second = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    analyses = _AnalysisDirectory({2: first, 5: second})
    destination = tmp_path / "local-dandiset"

    report = write_dandiset(
        analyses,
        destination,
        row_indices=[2, 5],
        recording_metadata={
            2: _recording_metadata("subject-2"),
            5: _recording_metadata("subject-5"),
        },
        dandiset_metadata=DandisetMetadata(
            identifier="000000",
            name="SanPy focused test",
            description="Two synthetic local exports for a focused test",
        ),
    )
    reopened = read_dandiset(destination)

    assert report.source_rows == (2, 5)
    assert reopened.asset_paths == report.asset_paths
    assert len(reopened.asset_paths) == 2
    for index in range(2):
        restored = reopened.read_recording(index)
        assert not restored.loadError
        np.testing.assert_allclose(
            restored.fileLoader.get_sweep_y(0), first.fileLoader.get_sweep_y(0)
        )
