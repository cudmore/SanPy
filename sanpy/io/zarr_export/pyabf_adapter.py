"""Extract a complete acquisition snapshot through verified PyABF APIs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyabf

from .models import AcquisitionSnapshot


_EPOCH_COLUMNS = (
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


def snapshot_abf(path: str | Path) -> AcquisitionSnapshot:
    """Read every sweep and ADC channel from an ABF through PyABF.

    Args:
        path: Source ABF path.

    Returns:
        A self-contained acquisition snapshot containing scaled signals,
        commands, channel metadata, timing, and epochs.

    Raises:
        FileNotFoundError: If the source ABF does not exist.
        ValueError: If the ABF is empty, has inconsistent point counts, or has
            differing time axes between sweeps or channels.
    """
    source = Path(path).expanduser().resolve(strict=True)
    abf = pyabf.ABF(str(source))
    sweeps = tuple(int(value) for value in abf.sweepList)
    channels = tuple(int(value) for value in abf.channelList)
    if not sweeps or not channels:
        raise ValueError(f"ABF has no sweeps or channels: {source}")
    points = int(abf.sweepPointCount)
    raw = np.empty((len(sweeps), len(channels), points), dtype=np.float64)
    command = np.empty((len(sweeps), len(channels), points), dtype=np.float64)
    reference_time = None
    epoch_rows: list[dict] = []
    for sweep_position, sweep in enumerate(sweeps):
        for channel_position, channel in enumerate(channels):
            abf.setSweep(sweepNumber=sweep, channel=channel, absoluteTime=False)
            time = np.asarray(abf.sweepX, dtype=np.float64)
            values = np.asarray(abf.sweepY, dtype=np.float64)
            commands = np.asarray(abf.sweepC, dtype=np.float64)
            _require_points(source, sweep, channel, points, time, values, commands)
            if reference_time is None:
                reference_time = time.copy()
            elif not np.array_equal(reference_time, time):
                raise ValueError(f"ABF time axes differ at sweep {sweep}, channel {channel}")
            raw[sweep_position, channel_position] = values
            command[sweep_position, channel_position] = commands
            epoch_rows.extend(_epoch_rows(abf, sweep_position, channel_position))
    assert reference_time is not None
    return AcquisitionSnapshot(
        source_path=source,
        name=source.name,
        protocol=str(abf.protocol),
        acquisition_datetime=abf.abfDateTime.isoformat(),
        sample_rate_hz=float(abf.dataRate),
        time=reference_time,
        raw=raw,
        command=command,
        channel_names=tuple(str(value) for value in abf.adcNames),
        channel_units=tuple(str(value) for value in abf.adcUnits),
        command_names=tuple(str(value) for value in abf.dacNames[: len(channels)]),
        command_units=tuple(str(value) for value in abf.dacUnits[: len(channels)]),
        epochs=pd.DataFrame(epoch_rows, columns=_EPOCH_COLUMNS),
        pyabf_version=str(pyabf.__version__),
    )


def _require_points(
    path: Path,
    sweep: int,
    channel: int,
    points: int,
    *arrays: np.ndarray,
) -> None:
    """Require point-aligned arrays to match the declared sweep length.

    Args:
        path: Source ABF path used in error messages.
        sweep: Zero-based sweep position.
        channel: Zero-based channel position.
        points: Expected number of points.
        *arrays: Point-aligned arrays to check.

    Raises:
        ValueError: If any array length differs from ``points``.
    """
    lengths = tuple(len(value) for value in arrays)
    if any(length != points for length in lengths):
        raise ValueError(
            f"ABF point count mismatch in {path.name}, sweep {sweep}, "
            f"channel {channel}: expected {points}, got {lengths}"
        )


def _epoch_rows(abf: pyabf.ABF, sweep: int, channel: int) -> list[dict[str, object]]:
    """Normalize the selected PyABF sweep's epoch table.

    Args:
        abf: PyABF recording with its target sweep and channel selected.
        sweep: Zero-based sweep position stored in the output.
        channel: Zero-based channel position stored in the output.

    Returns:
        One normalized dictionary per epoch.
    """
    epochs = abf.sweepEpochs
    rows = []
    for index, start in enumerate(epochs.p1s):
        stop = int(epochs.p2s[index])
        rows.append(
            {
                "sweep": sweep,
                "channel": channel,
                "epoch": index,
                "startPnt": int(start),
                "stopPnt": stop,
                "startSec": float(start) / abf.dataRate,
                "stopSec": stop / abf.dataRate,
                "level": float(epochs.levels[index]),
                "type": str(epochs.types[index]),
                "pulseWidth": int(epochs.pulseWidths[index]),
                "pulsePeriod": int(epochs.pulsePeriods[index]),
                "digitalStates": list(epochs.digitalStates[index]),
            }
        )
    return rows
