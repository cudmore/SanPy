"""Load single-electrode current-clamp NWB recordings.

Requires the optional ``pynwb`` dependency, installed with the ``nwb`` extra.
"""

from __future__ import annotations

import json
from typing import Optional

import numpy as np
from pynwb import NWBHDF5IO, NWBFile
from pynwb.base import TimeSeriesReference
from pynwb.icephys import (
    CurrentClampSeries,
    CurrentClampStimulusSeries,
    IZeroClampSeries,
    PatchClampSeries,
)

from sanpy.fileloaders.epochTable import epochTable
from sanpy.fileloaders.fileLoader_base import fileLoader_base, recordingModes
from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)

_RTOL = 1e-9
_ATOL = 1e-12
_SANPY_METADATA_NAME = "sanpy_metadata_json"


class fileLoader_nwb(fileLoader_base):
    """Load a regularly sampled, single-electrode current-clamp NWB file."""

    loadFileType = ".nwb"

    def loadFile(self) -> None:
        """Load NWB metadata and optionally materialize raw sweep arrays.

        Any exception is logged and converted to the standard SanPy loader-error
        state so callers can inspect ``analysis.loadError``.
        """
        try:
            self._load_file()
        except Exception as error:
            logger.error(f'Could not load NWB file "{self.filepath}": {error}')
            self._loadError = True

    def _load_file(self) -> None:
        """Read NWB intracellular metadata and optional raw arrays.

        Raises:
            ValueError: If the NWB data cannot be represented faithfully by the
                current SanPy single-channel, regularly sampled data model.
        """
        with NWBHDF5IO(path=self.filepath, mode="r") as io:
            nwbfile = io.read()
            recording_references = self._collect_sweep_references(nwbfile)

            sweep_times: list[np.ndarray] = []
            sweep_responses: list[np.ndarray] = []
            sweep_commands: list[Optional[np.ndarray]] = []
            electrode_ids: set[str] = set()
            normalized_start_times: list[float] = []
            missing_stimulus_sweeps: list[int] = []
            common_sample_interval: Optional[float] = None
            expected_length: Optional[int] = None
            expected_duration: Optional[float] = None

            for sweep, (
                response_reference,
                stimulus_reference,
            ) in enumerate(recording_references):
                response_series = response_reference.timeseries
                if not isinstance(
                    response_series,
                    (CurrentClampSeries, IZeroClampSeries),
                ):
                    raise ValueError(
                        f"Sweep {sweep} response must be CurrentClampSeries or "
                        f"IZeroClampSeries; got {type(response_series).__name__}"
                    )
                if response_series.unit != "volts":
                    raise ValueError(
                        f"Sweep {sweep} response unit must be 'volts'; got "
                        f"{response_series.unit!r}"
                    )

                electrode_id = getattr(response_series.electrode, "object_id", None)
                if electrode_id is None:
                    raise ValueError(f"Sweep {sweep} response has no electrode ID")
                electrode_ids.add(str(electrode_id))

                sample_interval, sweep_duration, start_time = self._reference_timing(
                    response_reference,
                    label=f"response for sweep {sweep}",
                )
                normalized_start_times.append(start_time)

                if common_sample_interval is None:
                    common_sample_interval = sample_interval
                elif not np.isclose(
                    sample_interval,
                    common_sample_interval,
                    rtol=_RTOL,
                    atol=_ATOL,
                ):
                    raise ValueError(
                        f"Sweep {sweep} sample interval {sample_interval} differs "
                        f"from {common_sample_interval} seconds"
                    )

                if expected_duration is None:
                    expected_duration = sweep_duration
                elif not np.isclose(
                    sweep_duration,
                    expected_duration,
                    rtol=_RTOL,
                    atol=_ATOL,
                ):
                    raise ValueError(
                        f"Sweep {sweep} duration {sweep_duration} differs "
                        f"from {expected_duration} seconds"
                    )

                sample_count = int(response_reference.count)
                if expected_length is None:
                    expected_length = sample_count
                elif sample_count != expected_length:
                    raise ValueError(
                        f"Sweep {sweep} has {sample_count} response samples; "
                        f"expected {expected_length}"
                    )

                response_mv: Optional[np.ndarray] = None
                local_time: Optional[np.ndarray] = None
                if self._loadData:
                    response_time = self._reference_timestamps(
                        response_reference,
                        label=f"response for sweep {sweep}",
                    )
                    response_values = self._reference_values(
                        response_reference,
                        label=f"response for sweep {sweep}",
                    )
                    response_mv = (
                        response_values * float(response_series.conversion)
                        + float(response_series.offset)
                    ) * 1e3
                    local_time = response_time - float(response_time[0])
                    self._validate_regular_time(
                        local_time,
                        label=f"response for sweep {sweep}",
                    )

                command_na: Optional[np.ndarray] = None
                if stimulus_reference is None:
                    missing_stimulus_sweeps.append(sweep)
                else:
                    stimulus_series = stimulus_reference.timeseries
                    if not isinstance(stimulus_series, CurrentClampStimulusSeries):
                        raise ValueError(
                            f"Sweep {sweep} stimulus must be "
                            "CurrentClampStimulusSeries; got "
                            f"{type(stimulus_series).__name__}"
                        )
                    if stimulus_series.unit != "amperes":
                        raise ValueError(
                            f"Sweep {sweep} stimulus unit must be 'amperes'; got "
                            f"{stimulus_series.unit!r}"
                        )
                    stimulus_electrode_id = getattr(
                        stimulus_series.electrode,
                        "object_id",
                        None,
                    )
                    if stimulus_electrode_id != electrode_id:
                        raise ValueError(
                            f"Sweep {sweep} stimulus and response reference "
                            "different electrodes"
                        )

                    (
                        stimulus_interval,
                        stimulus_duration,
                        _stimulus_start,
                    ) = self._reference_timing(
                        stimulus_reference,
                        label=f"stimulus for sweep {sweep}",
                    )
                    if int(stimulus_reference.count) != sample_count:
                        raise ValueError(
                            f"Sweep {sweep} stimulus and response lengths differ: "
                            f"{int(stimulus_reference.count)} and {sample_count}"
                        )
                    if not np.isclose(
                        stimulus_interval,
                        sample_interval,
                        rtol=_RTOL,
                        atol=_ATOL,
                    ):
                        raise ValueError(
                            f"Sweep {sweep} stimulus and response sample intervals "
                            "differ"
                        )
                    if not np.isclose(
                        stimulus_duration,
                        sweep_duration,
                        rtol=_RTOL,
                        atol=_ATOL,
                    ):
                        raise ValueError(
                            f"Sweep {sweep} stimulus and response durations differ"
                        )

                    if self._loadData:
                        stimulus_time = self._reference_timestamps(
                            stimulus_reference,
                            label=f"stimulus for sweep {sweep}",
                        )
                        stimulus_values = self._reference_values(
                            stimulus_reference,
                            label=f"stimulus for sweep {sweep}",
                        )
                        stimulus_local_time = stimulus_time - float(stimulus_time[0])
                        self._validate_regular_time(
                            stimulus_local_time,
                            label=f"stimulus for sweep {sweep}",
                        )
                        if local_time is None or not np.allclose(
                            stimulus_local_time,
                            local_time,
                            rtol=_RTOL,
                            atol=_ATOL,
                        ):
                            raise ValueError(
                                f"Sweep {sweep} stimulus and response sample times "
                                "do not align"
                            )
                        command_na = (
                            stimulus_values * float(stimulus_series.conversion)
                            + float(stimulus_series.offset)
                        ) * 1e9

                if self._loadData:
                    if local_time is None or response_mv is None:
                        raise RuntimeError(
                            f"Sweep {sweep} raw response data was not materialized"
                        )
                    sweep_times.append(local_time.astype(np.float64, copy=False))
                    sweep_responses.append(
                        response_mv.astype(np.float64, copy=False)
                    )
                    sweep_commands.append(
                        None
                        if command_na is None
                        else command_na.astype(np.float64, copy=False)
                    )

            if len(electrode_ids) != 1:
                raise ValueError(
                    "The NWB loader requires one electrode; found "
                    f"{len(electrode_ids)}"
                )

            if (
                common_sample_interval is None
                or expected_duration is None
                or expected_length is None
            ):
                raise ValueError("NWB file contains no usable response sweeps")

            session_start_time = nwbfile.session_start_time
            self.setAcqDate(session_start_time.strftime("%Y-%m-%d"))
            self.setAcqTime(session_start_time.strftime("%H:%M:%S"))
            self.setAcqDateTime(session_start_time.isoformat())
            self._numChannels = len(electrode_ids)
            self._numSweeps = len(recording_references)
            self._sweepList = list(range(self._numSweeps))
            self._sweepLengthSec = expected_duration
            self._dataPointsPerMs = 1.0 / (common_sample_interval * 1000.0)
            self._recordingMode = recordingModes.iclamp
            self._sweepLabelX = "seconds"
            self._sweepLabelY = "mv"

            if any(
                not np.isclose(value, 0.0, rtol=0.0, atol=_ATOL)
                for value in normalized_start_times
            ):
                preview_label = " (first 10)" if len(normalized_start_times) > 10 else ""
                logger.warning(
                    "Normalized NWB recording-relative sweep start times to "
                    f"sweep-local zero. Original start times in seconds"
                    f"{preview_label}: {normalized_start_times[:10]}"
                )

            if self._loadData:
                sweep_x = np.column_stack(sweep_times)
                sweep_y = np.column_stack(sweep_responses)
                sweep_c: Optional[np.ndarray]
                if len(missing_stimulus_sweeps) == len(sweep_commands):
                    sweep_c = None
                    logger.warning(
                        "NWB file contains no usable current-clamp stimulus for "
                        "any sweep; SanPy will provide zero commands through its "
                        "public API"
                    )
                else:
                    command_columns: list[np.ndarray] = []
                    for sweep, command in enumerate(sweep_commands):
                        if command is None:
                            command = np.zeros_like(sweep_responses[sweep])
                        command_columns.append(command)
                    sweep_c = np.column_stack(command_columns)
                    if missing_stimulus_sweeps:
                        logger.warning(
                            f"NWB stimuli were missing for sweeps "
                            f"{missing_stimulus_sweeps}; inserted zero command "
                            "columns because SanPy requires a rectangular command "
                            "matrix"
                        )

                self.setLoadedData(
                    sweepX=sweep_x,
                    sweepY=sweep_y,
                    sweepC=sweep_c,
                    recordingMode=recordingModes.iclamp,
                    xLabel="seconds",
                    yLabel="mv",
                )
                if sweep_c is not None:
                    self._epochTableList = self._build_epoch_tables(
                        sweep_commands, self._dataPointsPerMs
                    )
                self._restore_optional_sanpy_metadata(nwbfile)

    @staticmethod
    def _build_epoch_tables(
        sweep_commands: list[Optional[np.ndarray]],
        data_points_per_ms: float,
    ) -> list[Optional[epochTable]]:
        """Build one epoch table per sweep from its current command.

        Assumes every command is a piecewise-constant DC step waveform. A new
        epoch starts wherever the stored command value changes, and every
        epoch is a ``Step``. Ramps and other waveform shapes are not detected.

        A flat sweep, whose command never changes, is assumed to be a step
        whose amplitude equals the holding command (for example a 0 nA step).
        When every stepped sweep has identical boundaries, each flat sweep is
        given those boundaries so all sweeps share one epoch count, as in
        ABF protocols. A flat sweep's boundaries are therefore copied from the
        other sweeps, not observed in its own command. When stepped sweeps
        disagree, or every sweep is flat, each sweep keeps its own detected
        epochs. Different epoch counts per sweep are not handled here.

        Args:
            sweep_commands: Command in nanoamps for each sweep, or ``None``
                for a sweep whose NWB stimulus is missing.
            data_points_per_ms: Sampling rate in points per millisecond.

        Returns:
            One epoch table per sweep, with ``None`` for sweeps without a
            command.
        """
        boundaries_by_sweep: list[Optional[np.ndarray]] = []
        for command in sweep_commands:
            if command is None:
                boundaries_by_sweep.append(None)
                continue
            # DC steps only: any change in the stored value starts a new epoch.
            transitions = np.flatnonzero(np.diff(command) != 0) + 1
            boundaries_by_sweep.append(
                np.concatenate(([0], transitions, [len(command)]))
            )

        # Flat sweeps have only [0, n]; borrow boundaries from stepped sweeps
        # only when every stepped sweep agrees.
        stepped = [b for b in boundaries_by_sweep if b is not None and len(b) > 2]
        if stepped and all(np.array_equal(b, stepped[0]) for b in stepped):
            boundaries_by_sweep = [
                stepped[0] if b is not None and len(b) == 2 else b
                for b in boundaries_by_sweep
            ]

        tables: list[Optional[epochTable]] = []
        for sweep, (command, boundaries) in enumerate(
            zip(sweep_commands, boundaries_by_sweep)
        ):
            if command is None or boundaries is None:
                tables.append(None)
                continue
            table = epochTable()
            for start_point, stop_point in zip(boundaries[:-1], boundaries[1:]):
                table.addEpoch(
                    sweepNumber=sweep,
                    startPoint=int(start_point),
                    stopPoint=int(stop_point),
                    dataPointsPerMs=data_points_per_ms,
                    level=float(command[start_point]),
                )
            tables.append(table)
        return tables

    @staticmethod
    def _collect_sweep_references(
        nwbfile: NWBFile,
    ) -> list[tuple[TimeSeriesReference, Optional[TimeSeriesReference]]]:
        """Collect ordered response and stimulus references from an NWB file.

        Modern files are read from ``IntracellularRecordingsTable``. Files that
        predate that table are read from the acquisition and stimulus containers
        and paired by their NWB sweep numbers.

        Args:
            nwbfile: Open NWB file whose lazy datasets remain accessible.

        Returns:
            Ordered response references paired with optional stimulus references.

        Raises:
            ValueError: If references are missing or legacy series cannot be
                paired unambiguously.
        """
        recordings = nwbfile.intracellular_recordings
        if recordings is not None and len(recordings) > 0:
            recording_frame = recordings.to_dataframe(
                ignore_category_ids=True,
            )

            print(f'abb recording_frame:{recording_frame}')

            response_column = ("responses", "response")
            stimulus_column = ("stimuli", "stimulus")
            template_column = ("stimuli", "stimulus_template")
            if response_column not in recording_frame.columns:
                raise ValueError(
                    "IntracellularRecordingsTable has no response-reference column"
                )

            references: list[
                tuple[TimeSeriesReference, Optional[TimeSeriesReference]]
            ] = []
            template_fallback_sweeps: list[int] = []
            for sweep, (_, row) in enumerate(recording_frame.iterrows()):
                response_reference = fileLoader_nwb._require_reference(
                    row[response_column],
                    label=f"response for sweep {sweep}",
                )
                stimulus_reference = fileLoader_nwb._optional_reference(
                    row[stimulus_column]
                    if stimulus_column in recording_frame.columns
                    else None
                )
                if (
                    stimulus_reference is None
                    and template_column in recording_frame.columns
                ):
                    stimulus_reference = fileLoader_nwb._optional_reference(
                        row[template_column]
                    )
                    if stimulus_reference is not None:
                        template_fallback_sweeps.append(sweep)
                references.append((response_reference, stimulus_reference))

            if template_fallback_sweeps:
                logger.warning(
                    f"Primary NWB stimuli were missing for sweeps "
                    f"{template_fallback_sweeps}; loaded valid "
                    "CurrentClampStimulusSeries templates as SanPy commands"
                )
            return references

        responses: dict[int, CurrentClampSeries | IZeroClampSeries] = {}
        for series in nwbfile.acquisition.values():
            if not isinstance(series, (CurrentClampSeries, IZeroClampSeries)):
                continue
            sweep_number = fileLoader_nwb._require_sweep_number(series)
            if sweep_number in responses:
                raise ValueError(
                    f"Legacy NWB data has multiple responses for sweep "
                    f"{sweep_number}"
                )
            responses[sweep_number] = series

        if not responses:
            raise ValueError(
                "NWB file has neither IntracellularRecordingsTable rows nor "
                "supported current-clamp acquisition series"
            )

        stimuli: dict[int, CurrentClampStimulusSeries] = {}
        for series in nwbfile.stimulus.values():
            if not isinstance(series, CurrentClampStimulusSeries):
                continue
            sweep_number = fileLoader_nwb._require_sweep_number(series)
            if sweep_number in stimuli:
                raise ValueError(
                    f"Legacy NWB data has multiple stimuli for sweep {sweep_number}"
                )

            # abb, how do i get current amplitude?
            # print(f'abb series:{series}')
            # print(f'abb series.electrode:{series.electrode}')
            # print(f'abb series.data:{series.data}')
            # from matplotlib import pyplot as plt
            # # raw_data are current for all sweeps
            # raw_data = np.asarray(series.data[...], dtype=np.float64)
            # plt.plot(raw_data)
            # plt.show()

            stimuli[sweep_number] = series

        orphan_sweeps = sorted(set(stimuli).difference(responses))
        if orphan_sweeps:
            raise ValueError(
                f"Legacy NWB stimuli have no matching responses for sweeps "
                f"{orphan_sweeps}"
            )

        references = []
        for sweep_number in sorted(responses):
            response = responses[sweep_number]
            response_reference = TimeSeriesReference(0, len(response.data), response)
            stimulus = stimuli.get(sweep_number)
            stimulus_reference = (
                None
                if stimulus is None
                else TimeSeriesReference(0, len(stimulus.data), stimulus)
            )
            references.append((response_reference, stimulus_reference))

        # logger.warning(
        #     f"NWB file has no IntracellularRecordingsTable rows; loaded "
        #     f"{len(references)} legacy sweeps by matching acquisition and "
        #     "stimulus sweep numbers"
        # )
        return references

    @staticmethod
    def _require_sweep_number(series: PatchClampSeries) -> int:
        """Return a valid nonnegative integer sweep number for an NWB series.

        Args:
            series: Patch-clamp series requiring a sweep association.

        Returns:
            The normalized integer sweep number.

        Raises:
            ValueError: If the series has no nonnegative integer sweep number.
        """
        value = series.sweep_number
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"NWB series {series.name!r} has invalid sweep number {value!r}"
            ) from error
        if (
            not np.isfinite(numeric_value)
            or not numeric_value.is_integer()
            or numeric_value < 0
        ):
            raise ValueError(
                f"NWB series {series.name!r} has invalid sweep number {value!r}"
            )
        return int(numeric_value)

    def _restore_optional_sanpy_metadata(self, nwbfile: NWBFile) -> None:
        """Restore optional SanPy JSON metadata without blocking raw-data import.

        Args:
            nwbfile: Open NWB file whose scratch space may hold SanPy metadata.
        """
        scratch = nwbfile.scratch
        if _SANPY_METADATA_NAME not in scratch:
            # logger.warning(
            #     f"NWB file has no optional {_SANPY_METADATA_NAME} scratch entry; "
            #     "using default SanPy metadata"
            # )
            return

        try:
            metadata_text = self._read_scalar_text(scratch[_SANPY_METADATA_NAME].data)
            metadata = json.loads(metadata_text)
            if not isinstance(metadata, dict):
                raise ValueError("decoded metadata is not a JSON object")
            self.metadata.update(metadata)
        except Exception as error:
            logger.warning(
                f"Could not restore optional SanPy metadata from "
                f"{_SANPY_METADATA_NAME}: {error}; using default metadata"
            )

    @staticmethod
    def _require_reference(value: object, label: str) -> TimeSeriesReference:
        """Return a valid NWB time-series reference or raise an error.

        Args:
            value: Candidate table value.
            label: Human-readable location used in errors.

        Returns:
            A valid time-series reference.

        Raises:
            ValueError: If the value is not a valid reference.
        """
        reference = fileLoader_nwb._optional_reference(value)
        if reference is None:
            raise ValueError(f"NWB file has no valid {label}")
        return reference

    @staticmethod
    def _optional_reference(value: object) -> Optional[TimeSeriesReference]:
        """Return a valid NWB time-series reference when one is present.

        Args:
            value: Candidate value from an intracellular-recordings table.

        Returns:
            A valid reference, or ``None`` for a missing/invalid reference.
        """
        if not isinstance(value, TimeSeriesReference):
            return None
        if not value.isvalid():
            return None
        return value

    @staticmethod
    def _reference_timing(
        reference: TimeSeriesReference,
        label: str,
    ) -> tuple[float, float, float]:
        """Read timing metadata without materializing a complete time axis.

        Args:
            reference: Valid NWB time-series reference.
            label: Human-readable location used in errors.

        Returns:
            Sample interval, selected duration, and selected starting time in
            seconds.

        Raises:
            ValueError: If timing metadata is missing, nonfinite, or invalid.
        """
        count = int(reference.count)
        if count < 2:
            raise ValueError(f"{label} must contain at least two samples")

        series = reference.timeseries
        start_index = int(reference.idx_start)
        if series.timestamps is None:
            rate = float(series.rate)
            if not np.isfinite(rate) or rate <= 0:
                raise ValueError(f"{label} sampling rate must be positive")
            sample_interval = 1.0 / rate
            start_time = float(series.starting_time) + start_index * sample_interval
            duration = (count - 1) * sample_interval
        else:
            first = float(series.timestamps[start_index])
            second = float(series.timestamps[start_index + 1])
            last = float(series.timestamps[start_index + count - 1])
            values = np.asarray((first, second, last), dtype=np.float64)
            if not np.isfinite(values).all():
                raise ValueError(f"{label} timing metadata must be finite")
            sample_interval = second - first
            start_time = first
            duration = last - first
            if sample_interval <= 0 or duration <= 0:
                raise ValueError(f"{label} timestamps must be strictly increasing")

        return sample_interval, duration, start_time

    @staticmethod
    def _reference_values(
        reference: TimeSeriesReference,
        label: str,
    ) -> np.ndarray:
        """Materialize selected numeric data from an NWB table reference.

        Args:
            reference: Valid NWB time-series reference.
            label: Human-readable location used in errors.

        Returns:
            One-dimensional floating-point stored values.

        Raises:
            ValueError: If the selected data are masked, nonnumeric, or not 1-D.
        """
        values = np.asanyarray(reference.data)
        if np.ma.isMaskedArray(values) and np.ma.getmaskarray(values).any():
            raise ValueError(f"{label} contains masked data")
        values = np.asarray(values)
        if values.ndim != 1:
            raise ValueError(f"{label} data must be one-dimensional; got {values.shape}")
        if not np.issubdtype(values.dtype, np.number):
            raise ValueError(f"{label} data must be numeric; got {values.dtype}")
        return values.astype(np.float64, copy=False)

    @staticmethod
    def _reference_timestamps(
        reference: TimeSeriesReference,
        label: str,
    ) -> np.ndarray:
        """Materialize selected timestamps from an NWB table reference.

        Args:
            reference: Valid NWB time-series reference.
            label: Human-readable location used in errors.

        Returns:
            One-dimensional timestamps in seconds.

        Raises:
            ValueError: If timestamps are masked, nonfinite, or not 1-D.
        """
        timestamps = np.asanyarray(reference.timestamps)
        if np.ma.isMaskedArray(timestamps) and np.ma.getmaskarray(timestamps).any():
            raise ValueError(f"{label} contains masked timestamps")
        timestamps = np.asarray(timestamps, dtype=np.float64)
        if timestamps.ndim != 1:
            raise ValueError(
                f"{label} timestamps must be one-dimensional; got {timestamps.shape}"
            )
        if not np.isfinite(timestamps).all():
            raise ValueError(f"{label} timestamps must be finite")
        return timestamps

    @staticmethod
    def _validate_regular_time(timestamps: np.ndarray, label: str) -> float:
        """Validate a strictly increasing, regularly sampled time axis.

        Args:
            timestamps: One-dimensional time values in seconds.
            label: Human-readable location used in errors.

        Returns:
            The sample interval in seconds.

        Raises:
            ValueError: If fewer than two samples exist or sampling is irregular.
        """
        if len(timestamps) < 2:
            raise ValueError(f"{label} must contain at least two samples")
        intervals = np.diff(timestamps)
        if np.any(intervals <= 0):
            raise ValueError(f"{label} timestamps must be strictly increasing")
        sample_interval = float(intervals[0])
        if not np.allclose(intervals, sample_interval, rtol=_RTOL, atol=_ATOL):
            raise ValueError(f"{label} uses irregular sampling")
        return sample_interval

    @staticmethod
    def _read_scalar_text(value: object) -> str:
        """Read scalar text from an in-memory or lazy HDF5 value.

        Args:
            value: Scalar string, bytes, NumPy scalar, or lazy HDF5 dataset.

        Returns:
            Decoded text.

        Raises:
            ValueError: If the stored value is not scalar text.
        """
        if (
            not isinstance(value, (str, bytes, np.ndarray))
            and hasattr(value, "shape")
            and hasattr(value, "__getitem__")
        ):
            value = value[()]
        if isinstance(value, np.ndarray):
            if value.ndim != 0:
                raise ValueError("scratch metadata is not scalar text")
            value = value.item()
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        if not isinstance(value, str):
            raise ValueError("scratch metadata is not text")
        return value
