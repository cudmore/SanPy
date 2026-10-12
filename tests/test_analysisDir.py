"""Tests for constructing an ``analysisDir`` from stable test data."""

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import sanpy


def test_dir(test_data_dir: Path) -> None:
    """Discover supported recordings in the test data directory.

    Args:
        test_data_dir: Stable test-only data directory.
    """
    directory = sanpy.analysisDir(
        path=str(test_data_dir), autoLoad=False, folderDepth=1
    )

    assert len(directory) > 0
    for row_index, _row in enumerate(directory):
        assert directory.getAnalysis(row_index) is not None


def test_file(test_data_dir: Path) -> None:
    """Construct an ``analysisDir`` for one ABF file.

    Args:
        test_data_dir: Stable test-only data directory.
    """
    file_path = test_data_dir / "2021_07_20_0010.abf"

    directory = sanpy.analysisDir(
        path=str(file_path), autoLoad=False, folderDepth=1
    )

    assert len(directory) == 1
    row = directory.getRowDict(0)
    assert row["Dur(s)"] == 0.16
    assert row["Channels"] == 2
    assert row["Sweeps"] == 18
    assert row["Epochs"] == 5
    assert row["kHz"] == 10.0
    assert row["Mode"] == "I-Clamp"
    assert directory._df.at[0, "_ba"] is None


def test_constructor_reports_scan_progress(
    test_data_dir: Path,
    tmp_path: Path,
) -> None:
    """Report file-scan progress through the construction callback.

    Args:
        test_data_dir: Stable test-only data directory.
        tmp_path: Temporary folder without an existing analysis database.
    """
    source = test_data_dir / "2021_07_20_0010.abf"
    target = tmp_path / source.name
    target.write_bytes(source.read_bytes())
    statuses: list[str] = []

    sanpy.analysisDir(
        path=str(tmp_path),
        autoLoad=False,
        folderDepth=1,
        status_callback=statuses.append,
    )

    assert len(statuses) == 1
    assert 'Loading file 1 of 1' in statuses[0]
    assert source.name in statuses[0]
    assert str(target) not in statuses[0]


def test_pool_spike_dataframe_caches_saved_frames_without_loading_raw_data() -> None:
    """Reuse cached saved spike results without retaining a temporary analysis."""
    directory = sanpy.analysisDir.__new__(sanpy.analysisDir)
    directory.path = "/recordings"
    directory._pool_frame_cache = {}
    directory._df = pd.DataFrame(
        {
            "relPath": ["nested/cell.abf"],
            "uuid": ["saved-uuid"],
            "_ba": [None],
        }
    )
    analysis = MagicMock()
    analysis.isAnalyzed.return_value = True
    analysis.asDataFrame.return_value = pd.DataFrame({"spikeNumber": [2]})
    directory.loadOneAnalysis = MagicMock(return_value=analysis)
    statuses: list[str] = []

    first = directory.pool_spike_dataframe(status_callback=statuses.append)
    assert first is not None
    first.loc[0, "spikeNumber"] = 99
    second = directory.pool_spike_dataframe()

    assert second is not None
    assert second.loc[0, "spikeNumber"] == 2
    assert second.loc[0, "file_number"] == 0
    assert second.loc[0, "file_key"] == "nested/cell.abf"
    assert second.loc[0, "row_id"] == "0:2"
    assert directory._df.at[0, "_ba"] is None
    directory.loadOneAnalysis.assert_called_once_with(
        "/recordings/nested/cell.abf",
        "saved-uuid",
        allowAutoLoad=False,
    )
    assert statuses == ['Pooling file 1 of 1 "nested/cell.abf"']


def test_pool_spike_dataframe_prefers_live_analysis_and_evicts_cache() -> None:
    """Use current in-memory results instead of a stale saved-frame cache."""
    directory = sanpy.analysisDir.__new__(sanpy.analysisDir)
    directory.path = "/recordings"
    directory._pool_frame_cache = {
        "cell.abf": (
            "saved-uuid",
            pd.DataFrame(
                {
                    "spikeNumber": [1],
                    "file_number": [0],
                    "file_key": ["cell.abf"],
                    "row_id": ["0:1"],
                }
            ),
        )
    }
    live_analysis = MagicMock()
    live_analysis.isAnalyzed.return_value = True
    live_analysis.asDataFrame.return_value = pd.DataFrame({"spikeNumber": [4]})
    directory._df = pd.DataFrame(
        {
            "relPath": ["cell.abf"],
            "uuid": ["saved-uuid"],
            "_ba": [live_analysis],
        }
    )

    pooled = directory.pool_spike_dataframe()

    assert pooled is not None
    assert pooled.loc[0, "spikeNumber"] == 4
    assert "cell.abf" not in directory._pool_frame_cache


def test_unload_row_invalidates_cached_pool_frame() -> None:
    """Discard one cached frame when its analysis row is unloaded."""
    directory = sanpy.analysisDir.__new__(sanpy.analysisDir)
    directory._pool_frame_cache = {
        "cell.abf": ("saved-uuid", pd.DataFrame({"spikeNumber": [1]}))
    }
    directory._df = pd.DataFrame(
        {
            "relPath": ["cell.abf"],
            "uuid": ["saved-uuid"],
            "_ba": [MagicMock()],
        }
    )
    directory._updateLoadedAnalyzed = MagicMock()

    directory.unloadRow(0)

    assert directory._df.at[0, "_ba"] is None
    assert directory._pool_frame_cache == {}
