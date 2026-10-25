"""Focused round-trip tests for SanPy-owned NWB recording state."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

import h5py
import numpy as np
import pytest
from pynwb import NWBHDF5IO

import sanpy
from sanpy.bAnalysisResults import AnalysisResults
from sanpy.fileloaders import recordingModes
from sanpy.io.nwb.payload import SANPY_PAYLOAD_NAME
from sanpy.io.nwb.recording import (
    NwbRecordingMetadata,
    read_recording,
    write_recording,
)


def _metadata() -> NwbRecordingMetadata:
    """Return stable explicit metadata for test NWB files.

    Returns:
        Valid NWB recording metadata.
    """
    return NwbRecordingMetadata(
        subject_id="subject-1",
        cell_id="cell-1",
        species="Mus musculus",
        session_start_time=datetime(2021, 5, 20, 12, 54, tzinfo=timezone.utc),
    )


def test_analysis_results_strict_json_round_trip(test_data_dir: Path) -> None:
    """Round-trip actual detected spikes through strict Pydantic JSON.

    Args:
        test_data_dir: Stable SanPy test-data directory.
    """
    analysis = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    analysis.spikeDetect(sanpy.bDetection().getDetectionDict("SA Node"))

    for saved in analysis.spikeDict.asList():
        result = AnalysisResults.model_validate(saved)
        restored = AnalysisResults.model_validate_json(result.model_dump_json())
        assert restored == result
        assert "NaN" not in result.model_dump_json()


def test_current_clamp_analysis_round_trip(
    tmp_path: Path, test_data_dir: Path
) -> None:
    """Restore raw data, results, conditions, metadata, and epochs.

    Args:
        tmp_path: Pytest-managed output directory.
        test_data_dir: Stable SanPy test-data directory.
    """
    source = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    source.metaData.setMetaData("animal_id", "mouse-1", triggerDirty=False)
    source.setSweepCondition(0, "control")
    source.spikeDetect(sanpy.bDetection().getDetectionDict("SA Node"))
    destination = tmp_path / "roundtrip.nwb"

    write_recording(source, destination, _metadata())
    restored = read_recording(destination)

    assert restored.isAnalyzed()
    assert restored.numSpikes == source.numSpikes
    assert restored.metaData["animal_id"] == "mouse-1"
    assert restored.getSweepCondition(0) == "control"
    assert restored.fileLoader.getEpochTable(0).level_unit == "pA"
    np.testing.assert_allclose(
        restored.fileLoader.get_sweep_y(0), source.fileLoader.get_sweep_y(0)
    )
    np.testing.assert_allclose(
        restored.fileLoader.get_sweep_c(0), source.fileLoader.get_sweep_c(0)
    )
    assert restored.spikeDict.asList() == source.spikeDict.asList()

    with NWBHDF5IO(str(destination), "r") as io:
        nwbfile = io.read()
        payload = json.loads(str(nwbfile.scratch[SANPY_PAYLOAD_NAME].data))
        assert payload["analysis_performed"] is True
        assert "halfHeights" not in payload["detection_parameters"]
        assert "widths" not in payload["analysis_results"][0]
        assert "width_50_rising_pnt" in payload["analysis_results"][0]


def test_analyzed_zero_spike_state_round_trip(
    tmp_path: Path, test_data_dir: Path
) -> None:
    """Preserve analyzed state independently of the result count.

    Args:
        tmp_path: Pytest-managed output directory.
        test_data_dir: Stable SanPy test-data directory.
    """
    source = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    source._detectionDict = sanpy.bDetection().getDetectionDict("SA Node")
    source._isAnalyzed = True
    destination = tmp_path / "zero-spikes.nwb"

    write_recording(source, destination, _metadata())
    restored = read_recording(destination)

    assert restored.isAnalyzed()
    assert restored.numSpikes == 0


def test_voltage_clamp_raw_round_trip(tmp_path: Path, test_data_dir: Path) -> None:
    """Round-trip raw voltage-clamp data without spike-analysis state.

    Args:
        tmp_path: Pytest-managed output directory.
        test_data_dir: Stable SanPy test-data directory.
    """
    source = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    source.fileLoader._recordingMode = recordingModes.vclamp
    source.fileLoader._sweepLabelY = "nA"
    source.fileLoader._fileMetadata = replace(
        source.fileLoader._fileMetadata,
        mode=recordingModes.vclamp.value,
        sweep_label_y="nA",
    )
    for sweep in source.fileLoader.sweepList:
        source.fileLoader.getEpochTable(sweep).set_level_unit("mV")
    destination = tmp_path / "voltage-clamp.nwb"

    write_recording(source, destination, _metadata())
    restored = read_recording(destination)

    assert restored.fileLoader.recordingMode is recordingModes.vclamp
    assert not restored.isAnalyzed()
    assert restored.fileLoader.getEpochTable(0).level_unit == "mV"
    np.testing.assert_allclose(
        restored.fileLoader.get_sweep_y(0), source.fileLoader.get_sweep_y(0)
    )
    np.testing.assert_allclose(
        restored.fileLoader.get_sweep_c(0), source.fileLoader.get_sweep_c(0)
    )


def test_invalid_sanpy_payload_keeps_raw_recording(
    tmp_path: Path, test_data_dir: Path
) -> None:
    """Load standard raw data when optional SanPy JSON is malformed.

    Args:
        tmp_path: Pytest-managed output directory.
        test_data_dir: Stable SanPy test-data directory.
    """
    source = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    destination = tmp_path / "invalid-payload.nwb"
    write_recording(source, destination, _metadata())
    with h5py.File(destination, "r+") as h5_file:
        h5_file[f"scratch/{SANPY_PAYLOAD_NAME}"][()] = "{invalid"

    restored = read_recording(destination)

    assert not restored.loadError
    assert not restored.isAnalyzed()
    assert restored.numSpikes == 0


def test_payload_application_failure_rolls_back_to_raw_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_data_dir: Path,
) -> None:
    """Discard every SanPy-specific mutation when payload application fails.

    Args:
        monkeypatch: Pytest fixture used to simulate an internal payload failure.
        tmp_path: Pytest-managed output directory.
        test_data_dir: Stable SanPy test-data directory.
    """
    source = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))
    source.metaData.setMetaData("animal_id", "saved-animal", triggerDirty=False)
    destination = tmp_path / "application-failure.nwb"
    write_recording(source, destination, _metadata())

    def fail_after_mutation(analysis: sanpy.bAnalysis, payload: object) -> None:
        """Mutate optional state and then simulate an unexpected decoder failure.

        Args:
            analysis: Analysis receiving optional state.
            payload: Parsed payload supplied by the loader.

        Raises:
            RuntimeError: Always, after one representative mutation.
        """
        del payload
        analysis.metaData.setMetaData(
            "animal_id", "partially-applied", triggerDirty=False
        )
        raise RuntimeError("simulated optional payload failure")

    monkeypatch.setattr("sanpy.io.nwb.payload.apply_payload", fail_after_mutation)

    restored = read_recording(destination)

    assert not restored.loadError
    assert restored.metaData["animal_id"] == ""
    assert not restored.isAnalyzed()
    assert restored.numSpikes == 0
