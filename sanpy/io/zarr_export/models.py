"""Plain-data snapshots consumed by the persistence writer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AcquisitionSnapshot:
    """Immutable acquisition data extracted from one ABF recording.

    Attributes:
        source_path: Absolute path used only while producing the snapshot.
        name: Source recording filename.
        protocol: Acquisition protocol name.
        acquisition_datetime: ISO-formatted acquisition date and time.
        sample_rate_hz: Sampling frequency in hertz.
        time: Shared point-aligned time axis in seconds.
        raw: Scaled ADC values arranged as sweep, channel, and point.
        command: Command values arranged as sweep, channel, and point.
        channel_names: ADC channel names.
        channel_units: Scaled ADC channel units.
        command_names: Command channel names.
        command_units: Command channel units.
        epochs: Normalized epoch table.
        pyabf_version: PyABF version used for extraction.
    """

    source_path: Path
    name: str
    protocol: str
    acquisition_datetime: str
    sample_rate_hz: float
    time: np.ndarray
    raw: np.ndarray
    command: np.ndarray
    channel_names: tuple[str, ...]
    channel_units: tuple[str, ...]
    command_names: tuple[str, ...]
    command_units: tuple[str, ...]
    epochs: pd.DataFrame
    pyabf_version: str


@dataclass(frozen=True)
class SanPySnapshot:
    """Immutable SanPy-owned state associated with one recording.

    Attributes:
        recording_id: Stable SanPy recording identifier.
        metadata: Experimental metadata values.
        detection_parameters: Applied detection parameter values.
        detection_definitions: Runtime detection parameter schema.
        result_definitions: Runtime analysis-result schema.
        analysis_results: Actual one-row-per-spike results.
        filtered: Filtered analysis-channel values by sweep and point.
        dvdt: Analysis-channel derivative values by sweep and point.
        analysis_channel: Zero-based channel analyzed by SanPy.
        sanpy_version: SanPy version used for export.
    """

    recording_id: str
    metadata: dict[str, Any]
    detection_parameters: dict[str, Any]
    detection_definitions: dict[str, dict[str, Any]]
    result_definitions: dict[str, dict[str, Any]]
    analysis_results: pd.DataFrame
    filtered: np.ndarray | None
    dvdt: np.ndarray | None
    analysis_channel: int
    sanpy_version: str


@dataclass(frozen=True)
class RecordingExport:
    """Complete acquisition and SanPy snapshots for one recording.

    Attributes:
        acquisition: Complete ABF-derived acquisition snapshot.
        sanpy: SanPy runtime snapshot for the same recording.
    """

    acquisition: AcquisitionSnapshot
    sanpy: SanPySnapshot
