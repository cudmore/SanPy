"""Extract acquisition snapshots from loaded SanPy text recordings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import sanpy

from .models import EPOCH_COLUMNS, AcquisitionSnapshot


def snapshot_sanpy(analysis: Any) -> AcquisitionSnapshot:
    """Copy acquisition data from a SanPy-text-backed analysis.

    Args:
        analysis: Loaded SanPy bAnalysis instance.

    Returns:
        A self-contained acquisition snapshot.

    Raises:
        FileNotFoundError: If the source recording no longer exists.
        ValueError: If loader arrays or recording units are inconsistent.
    """
    loader = analysis.fileLoader
    source = Path(loader.filepath).expanduser().resolve(strict=True)
    if source.suffix.lower() != ".sanpy":
        raise ValueError(f"Expected a .sanpy source, got: {source}")

    time = np.asarray(loader._sweepX[:, 0], dtype=np.float64).copy()
    point_by_sweep = np.asarray(loader._sweepY, dtype=np.float64)
    if point_by_sweep.ndim != 2 or point_by_sweep.shape[0] != len(time):
        raise ValueError(f"Inconsistent .sanpy recording arrays: {source}")
    raw = point_by_sweep.T[:, np.newaxis, :].copy()

    if loader._sweepC is None:
        command = np.zeros_like(raw)
    else:
        point_by_sweep_command = np.asarray(loader._sweepC, dtype=np.float64)
        if point_by_sweep_command.shape != point_by_sweep.shape:
            raise ValueError(f"Inconsistent .sanpy command array: {source}")
        command = point_by_sweep_command.T[:, np.newaxis, :].copy()

    recording_token = str(loader.sweepLabelY)
    if recording_token == "mv":
        channel_name, channel_unit = "Vm", "mV"
        command_name, command_unit = "Im", "pA"
    elif recording_token == "pA":
        channel_name, channel_unit = "Im", "pA"
        command_name, command_unit = "Vm", "mV"
    else:
        raise ValueError(f"Unsupported .sanpy recording unit: {recording_token!r}")

    epoch_rows: list[dict[str, object]] = []
    for sweep in loader.sweepList:
        table = loader.getEpochTable(sweep)
        if table is None:
            continue
        for epoch in table.getEpochList():
            epoch_rows.append(_epoch_row(epoch, sweep))

    return AcquisitionSnapshot(
        source_path=source,
        name=source.name,
        protocol="",
        acquisition_datetime="",
        sample_rate_hz=float(loader.dataPointsPerMs) * 1000.0,
        time=time,
        raw=raw,
        command=command,
        channel_names=(channel_name,),
        channel_units=(channel_unit,),
        command_names=(command_name,),
        command_units=(command_unit,),
        epochs=pd.DataFrame(epoch_rows, columns=EPOCH_COLUMNS),
        source_format="sanpy",
        reader_version=str(sanpy.__version__),
    )


def _epoch_row(epoch: dict[str, Any], sweep: int) -> dict[str, object]:
    """Normalize one loader epoch for persistence.

    Args:
        epoch: Epoch dictionary returned by epochTable.
        sweep: Zero-based sweep index.

    Returns:
        Epoch values matching the shared export table columns.
    """
    return {
        "sweep": int(sweep),
        "channel": 0,
        "epoch": int(epoch["index"]),
        "startPnt": int(epoch["startPoint"]),
        "stopPnt": int(epoch["stopPoint"]),
        "startSec": float(epoch["startSec"]),
        "stopSec": float(epoch["stopSec"]),
        "level": float(epoch["level"]),
        "type": str(epoch["type"]),
        "pulseWidth": int(epoch.get("pulseWidth", 0)),
        "pulsePeriod": int(epoch.get("pulsePeriod", 0)),
        "digitalStates": list(
            epoch.get("digitalStates", epoch.get("digitalState", []))
        ),
    }
