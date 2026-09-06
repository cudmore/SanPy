"""Plain-data snapshots consumed by the persistence writer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AcquisitionSnapshot:
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
    acquisition: AcquisitionSnapshot
    sanpy: SanPySnapshot
