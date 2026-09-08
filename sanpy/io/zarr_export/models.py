"""Plain-data snapshots consumed by the persistence writer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from sanpy.trace_overlays import TraceOverlayDefinition


EPOCH_COLUMNS = (
    "sweep",
    "channel",
    "epoch",
    "startPnt",
    "stopPnt",
    "startSec",
    "stopSec",
    "level",
    "type",
    "pulseWidth",
    "pulsePeriod",
    "digitalStates",
)


@dataclass(frozen=True)
class AcquisitionSnapshot:
    """Immutable acquisition data extracted from one source recording.

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
        source_format: Source recording format without a leading dot.
        reader_version: Version of the library used to read the source.
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
    source_format: str
    reader_version: str


@dataclass(frozen=True)
class SanPySnapshot:
    """Immutable SanPy-owned state associated with one recording.

    Attributes:
        recording_id: Stable SanPy recording identifier.
        metadata: Experimental metadata values.
        detection_parameters: Applied detection parameter values.
        detection_definitions: Runtime detection parameter schema.
        result_definitions: Runtime analysis-result schema.
        trace_overlay_definitions: Runtime mappings from results to trace
            overlays.
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
    trace_overlay_definitions: tuple[TraceOverlayDefinition, ...]
    analysis_results: pd.DataFrame
    filtered: np.ndarray | None
    dvdt: np.ndarray | None
    analysis_channel: int
    sanpy_version: str


@dataclass(frozen=True)
class RecordingExport:
    """Complete acquisition and SanPy snapshots for one recording.

    Attributes:
        acquisition: Complete source-recording acquisition snapshot.
        sanpy: SanPy runtime snapshot for the same recording.
    """

    acquisition: AcquisitionSnapshot
    sanpy: SanPySnapshot
