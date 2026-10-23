"""Tests for ``bExport`` report headers."""

import csv
from pathlib import Path

import pandas as pd

import sanpy
from sanpy.bExport import bExport


def test_summary_header_uses_file_metadata(test_data_dir: Path) -> None:
    """Report file metadata and schema names in the summary.

    Args:
        test_data_dir: Stable test-only data directory.
    """
    analysis = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    analysis.spikeDetect(sanpy.bDetection().getDetectionDict("SA Node"))
    analysis.metaData.setMetaData("cell_type", "SAN")
    analysis.metaData.setMetaData("sex", "female")
    analysis.metaData.setMetaData("condition", "drug")

    summary = bExport(analysis).getSummary()

    assert summary is not None
    assert summary.loc["Cell Type", 0] == "SAN"
    assert summary.loc["Sex", 0] == "female"
    assert summary.loc["Condition", 0] == "drug"
    assert "thresholdSec" in summary.index
    assert "spikeNumber" not in summary.index
    assert "file" not in summary.index
    assert "Take Off Potential (s)" not in summary.index


def test_clip_csv_time_axis_is_milliseconds(
    tmp_path: Path, test_data_dir: Path
) -> None:
    """Write the clip CSV time axis in milliseconds.

    Args:
        tmp_path: Temporary directory for the report files.
        test_data_dir: Stable test-only data directory.
    """
    analysis = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    analysis.spikeDetect(sanpy.bDetection().getDetectionDict("SA Node"))
    loader = analysis.fileLoader
    assert loader is not None

    bExport(analysis).saveReport(str(tmp_path / "report.xlsx"), verbose=False)

    clip_paths = list((tmp_path / "analysis").glob("*_clip.csv"))
    assert len(clip_paths) == 1
    with clip_paths[0].open(newline="") as clip_file:
        row = next(csv.DictReader(clip_file))

    expected = analysis.spike_clips.get(0, loader.recordingDur, sweep_number=0)
    assert expected is not None
    assert float(row["xMs"]) == expected[1][0][0]


def test_report2_matches_report3_rows_and_schema_columns(test_data_dir: Path) -> None:
    """Keep ``report2`` on the same spikes and schema columns as ``report3``.

    A recording with no detected spikes returns ``None``.

    Args:
        test_data_dir: Stable test-only data directory.
    """
    analysis = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    assert bExport(analysis).report2() is None

    analysis.spikeDetect(sanpy.bDetection().getDetectionDict("SA Node"))
    export = bExport(analysis)
    full = export.report3()
    readable = export.report2()

    assert full is not None
    assert readable is not None
    pd.testing.assert_frame_equal(readable, full.loc[:, list(readable.columns)])
    assert "thresholdSec" in readable.columns
    assert "peakSec" in readable.columns
    assert "isi_ms" in readable.columns
    assert "widths_50" in readable.columns
    assert "Take Off Potential (s)" not in readable.columns
    assert "Take Off Potential (ms)" not in readable.columns
    assert "AP Peak (ms)" not in readable.columns
    assert "ISI (ms)" not in readable.columns
    assert "width_50" not in readable.columns

    stop = float(full["thresholdSec"].max())
    clipped = export.report2(theMin=0, theMax=stop)
    clipped_full = export.report3(theMin=0, theMax=stop)
    assert clipped is not None
    assert clipped_full is not None
    pd.testing.assert_frame_equal(clipped, clipped_full.loc[:, list(clipped.columns)])
    assert len(clipped) < len(readable)
    assert bool((clipped["thresholdSec"] < stop).all())
