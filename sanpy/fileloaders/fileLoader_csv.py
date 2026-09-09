"""Load canonical CSV-like ``.sanpy`` recordings."""

import re
from typing import Optional

import numpy as np
import pandas as pd

from sanpy.fileloaders.epochTable import epochTable
from sanpy.fileloaders.fileLoader_base import fileLoader_base, recordingModes
from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

_RECORDING_COLUMN = re.compile(r"^(mv|pA)_(\d+)$")
_COMMAND_COLUMN = re.compile(r"^cmd_(\d+)$")
_RTOL = 1e-9
_ATOL = 1e-12


def _parse_sanpy_columns(
    columns: list[str],
) -> tuple[str, list[str], list[str], bool]:
    """Validate canonical column order and return the recording layout."""
    if not columns or columns[0] != "seconds":
        raise ValueError("first column must be 'seconds'")

    has_epoch_index = len(columns) > 1 and columns[1] == "epoch_index"
    signal_columns = columns[2:] if has_epoch_index else columns[1:]
    if not signal_columns:
        raise ValueError("expected at least one numbered recording column")

    first_recording = _RECORDING_COLUMN.fullmatch(signal_columns[0])
    if first_recording is None or int(first_recording.group(2)) != 0:
        raise ValueError("first recording column must be 'mv_0' or 'pA_0'")
    recording_token = first_recording.group(1)

    has_commands = any(_COMMAND_COLUMN.fullmatch(name) for name in signal_columns)
    stride = 2 if has_commands else 1
    if len(signal_columns) % stride:
        raise ValueError("recording and command columns must form complete sweep pairs")

    num_sweeps = len(signal_columns) // stride
    recording_columns = [f"{recording_token}_{sweep}" for sweep in range(num_sweeps)]
    command_columns = [f"cmd_{sweep}" for sweep in range(num_sweeps)] if has_commands else []
    expected_columns: list[str] = []
    for sweep in range(num_sweeps):
        expected_columns.append(recording_columns[sweep])
        if has_commands:
            expected_columns.append(command_columns[sweep])

    if signal_columns != expected_columns:
        raise ValueError(
            "signal columns must use one recording type and contiguous sweeps in "
            f"canonical order; expected {expected_columns}, got {signal_columns}"
        )
    if has_epoch_index and not has_commands:
        raise ValueError("'epoch_index' requires one matching 'cmd_<sweep>' column per sweep")

    return recording_token, recording_columns, command_columns, has_epoch_index


class fileLoader_text(fileLoader_base):
    """Load a canonical ``.sanpy`` recording without raising into the GUI."""

    loadFileType = ".sanpy"

    def loadFile(self) -> None:
        """Load ``self.filepath`` and contain malformed-file failures."""
        try:
            self._load_file()
        except Exception as error:
            logger.error(
                'Could not load .sanpy file "%s": %s', self.filepath, error
            )
            self._loadError = True

    def _load_file(self) -> None:
        dataframe = pd.read_csv(self.filepath)
        if dataframe.empty:
            raise ValueError("file contains no recording rows")

        columns = [str(name) for name in dataframe.columns]
        recording_token, y_columns, c_columns, has_epoch_index = _parse_sanpy_columns(
            columns
        )

        seconds = dataframe["seconds"].to_numpy(dtype=np.float64)
        if len(seconds) < 2:
            raise ValueError("'seconds' must contain at least two samples")
        if not np.isfinite(seconds).all():
            raise ValueError("'seconds' must contain only finite numeric values")
        if not np.isclose(seconds[0], 0.0, rtol=0.0, atol=_ATOL):
            raise ValueError("'seconds' must begin at zero")

        time_steps = np.diff(seconds)
        if np.any(time_steps <= 0):
            raise ValueError("'seconds' must be strictly increasing")
        sample_interval = float(time_steps[0])
        if not np.allclose(time_steps, sample_interval, rtol=_RTOL, atol=_ATOL):
            raise ValueError("'seconds' must be uniformly sampled")

        sweep_y = dataframe[y_columns].to_numpy(dtype=np.float64)
        if not np.isfinite(sweep_y).all():
            raise ValueError("recording columns must contain only finite numeric values")

        sweep_c: Optional[np.ndarray] = None
        if c_columns:
            sweep_c = dataframe[c_columns].to_numpy(dtype=np.float64)
            if not np.isfinite(sweep_c).all():
                raise ValueError("command columns must contain only finite numeric values")

        epoch_tables: Optional[list[epochTable]] = None
        if has_epoch_index:
            if not pd.api.types.is_integer_dtype(dataframe["epoch_index"].dtype):
                raise ValueError("'epoch_index' must contain integer values")
            epoch_indices = dataframe["epoch_index"].to_numpy(dtype=np.int64)
            if epoch_indices[0] != 0:
                raise ValueError("'epoch_index' must begin at 0")
            epoch_steps = np.diff(epoch_indices)
            if not np.isin(epoch_steps, (0, 1)).all():
                raise ValueError(
                    "'epoch_index' may only remain unchanged or increase by 1"
                )
            if sweep_c is None:  # Guaranteed by column validation; keeps typing explicit.
                raise ValueError("'epoch_index' requires command columns")
            epoch_tables = self._build_epoch_tables(
                epoch_indices, sweep_c, sample_interval
            )

        recording_mode = (
            recordingModes.iclamp
            if recording_token == "mv"
            else recordingModes.vclamp
        )
        self.setLoadedData(
            sweepX=seconds[:, np.newaxis],
            sweepY=sweep_y,
            sweepC=sweep_c,
            recordingMode=recording_mode,
            xLabel="seconds",
            yLabel=recording_token,
        )
        self._epochTableList = epoch_tables

    @staticmethod
    def _build_epoch_tables(
        epoch_indices: np.ndarray,
        sweep_c: np.ndarray,
        sample_interval: float,
    ) -> list[epochTable]:
        """Build one epoch table per sweep from shared point labels."""
        transition_points = np.flatnonzero(np.diff(epoch_indices)) + 1
        boundaries = np.concatenate(([0], transition_points, [len(epoch_indices)]))
        data_points_per_ms = 1.0 / (sample_interval * 1000.0)
        tables: list[epochTable] = []

        for sweep in range(sweep_c.shape[1]):
            table = epochTable()
            for epoch_index, (start_point, stop_point) in enumerate(
                zip(boundaries[:-1], boundaries[1:])
            ):
                command = sweep_c[start_point:stop_point, sweep]
                level = float(command[0])
                if not np.allclose(command, level, rtol=_RTOL, atol=_ATOL):
                    raise ValueError(
                        f"command for sweep {sweep}, epoch {epoch_index} is not constant"
                    )

                start_sec = float(start_point * sample_interval)
                stop_sec = float(stop_point * sample_interval)
                table.addEpoch(
                    sweepNumber=sweep,
                    startSec=start_sec,
                    stopSec=stop_sec,
                    dataPointsPerMs=data_points_per_ms,
                    level=level,
                )
                added_epoch = table.getEpochList()[-1]
                if (
                    added_epoch["startPoint"] != start_point
                    or added_epoch["stopPoint"] != stop_point
                ):
                    raise ValueError(
                        "epoch boundary conversion mismatch for "
                        f"sweep {sweep}, epoch {epoch_index}: expected "
                        f"[{start_point}, {stop_point}), got "
                        f"[{added_epoch['startPoint']}, {added_epoch['stopPoint']})"
                    )
            tables.append(table)

        return tables
