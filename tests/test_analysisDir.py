"""Tests for constructing an ``analysisDir`` from stable test data."""

from pathlib import Path

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
    assert str(target) in statuses[0]
