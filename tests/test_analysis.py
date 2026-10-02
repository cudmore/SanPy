"""Tests for loading, detecting, and reading results from ``bAnalysis``."""

from pathlib import Path

import pytest

import sanpy


@pytest.fixture(scope="module")
def detected_analysis(test_data_dir: Path) -> sanpy.bAnalysis:
    """Load and analyze the stable single-sweep ABF fixture.

    Args:
        test_data_dir: Stable test-only data directory.

    Returns:
        Analysis containing SA Node detection results.
    """
    analysis = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    detection = sanpy.bDetection().getDetectionDict("SA Node")
    analysis.spikeDetect(detection)
    return analysis


def test_load(test_data_dir: Path) -> None:
    """Load a stable ABF fixture and expose matching time and voltage arrays.

    Args:
        test_data_dir: Stable test-only data directory.
    """
    analysis = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))

    assert not analysis.loadError
    assert analysis.fileLoader is not None
    assert analysis.fileLoader.sweepX is not None
    assert analysis.fileLoader.sweepY is not None
    assert len(analysis.fileLoader.sweepX) == len(analysis.fileLoader.sweepY)


def test_detect(detected_analysis: sanpy.bAnalysis) -> None:
    """Detect the expected spikes and detection errors.

    Args:
        detected_analysis: Analysis prepared with the SA Node preset.
    """
    assert detected_analysis.numSpikes == 103
    assert len(detected_analysis.dfError) == 102


def test_stats(detected_analysis: sanpy.bAnalysis) -> None:
    """Return one threshold-time statistic for every detected spike.

    Args:
        detected_analysis: Analysis prepared with the SA Node preset.
    """
    assert len(detected_analysis.getStat("thresholdSec")) == 103
