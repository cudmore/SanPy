"""Tests for ``bExport`` report headers."""

import csv
from pathlib import Path

import sanpy
from sanpy.bExport import bExport


def test_summary_header_uses_file_metadata(test_data_dir: Path) -> None:
    """Report cell type, sex, and condition from file metadata.

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
