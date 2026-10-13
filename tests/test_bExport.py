"""Tests for ``bExport`` report headers."""

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
