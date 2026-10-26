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


def test_spike_clips(detected_analysis: sanpy.bAnalysis) -> None:
    """Return a full clip and matching time axis for each spike that fits.

    On this fixture the first spike starts before the pre-clip window, so
    that clip is omitted. Time windows and spike selection use the detection
    spike index, so spike 0 selects nothing and spike 1 selects the first
    kept clip.

    Args:
        detected_analysis: Analysis prepared with the SA Node preset.
    """
    spike_times = detected_analysis.getSpikeTimes(sweepNumber=0, epochNumber="All")
    result = detected_analysis.spike_clips.get(None, None, sweep_number=0)
    assert result is not None
    clips, clips_x, mean_clip = result
    assert len(spike_times) == 103
    assert len(clips) == len(spike_times) - 1
    assert len(clips_x) == len(clips)
    for clip, x_row in zip(clips, clips_x):
        assert len(x_row) == len(clip)
    assert clips_x[0][0] < 0
    assert 0 in clips_x[0]
    assert len(mean_clip) == len(clips[0])

    loader = detected_analysis.fileLoader
    assert loader is not None
    spike0_sec = loader.pnt2Sec_(spike_times[0])
    spike1_sec = loader.pnt2Sec_(spike_times[1])
    around_spike0 = detected_analysis.spike_clips.get(
        spike0_sec - 0.01, spike0_sec + 0.01, sweep_number=0
    )
    around_spike1 = detected_analysis.spike_clips.get(
        spike1_sec - 0.01, spike1_sec + 0.01, sweep_number=0
    )
    selected_spike0 = detected_analysis.spike_clips.get(
        None, None, spike_selection=[0], sweep_number=0
    )
    selected_spike1 = detected_analysis.spike_clips.get(
        None, None, spike_selection=[1], sweep_number=0
    )
    assert around_spike0 is not None
    assert around_spike1 is not None
    assert selected_spike0 is not None
    assert selected_spike1 is not None
    assert around_spike0[0] == []
    assert len(around_spike1[0]) == 1
    assert selected_spike0[0] == []
    assert len(selected_spike1[0]) == 1
    assert (selected_spike1[0][0] == around_spike1[0][0]).all()
    assert (selected_spike1[0][0] == clips[0]).all()


def test_plot_phase_plot_uses_one_spike_clip(
    detected_analysis: sanpy.bAnalysis,
) -> None:
    """Plot the phase of a spike that has a clip.

    Args:
        detected_analysis: Analysis prepared with the SA Node preset.
    """
    pytest.importorskip(
        "matplotlib",
        reason="Install the plot or gui extra to run Matplotlib tests",
    )
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    from sanpy.analysisPlot import bAnalysisPlot

    plotter = bAnalysisPlot(detected_analysis)
    assert plotter.plotPhasePlot(0) is None

    _figure, ax = plt.subplots()
    line = plotter.plotPhasePlot(1, ax=ax)
    assert line is not None
    assert len(line.get_xdata()) == len(line.get_ydata())
    assert len(line.get_xdata()) > 0
    plt.close(_figure)


def test_spike_clips_without_spikes(test_data_dir: Path) -> None:
    """Return no clips before spike detection.

    Args:
        test_data_dir: Stable test-only data directory.
    """
    analysis = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    assert analysis.numSpikes == 0
    assert analysis.spike_clips.get(0, 1) is None
