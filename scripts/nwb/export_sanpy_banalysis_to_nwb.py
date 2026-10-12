"""Export one loaded SanPy ``bAnalysis`` current-clamp recording to NWB.

This is a standalone development script. Edit ``ABF_PATH``,
and ``NWB_PATH`` in the ``__main__`` block before running it.

run with:
    uv run --with pynwb scripts/nwb/export_sanpy_banalysis_to_nwb.py

"""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterator
from zoneinfo import ZoneInfo

import numpy as np
from pynwb import NWBHDF5IO, NWBFile, validate
from pynwb.icephys import CurrentClampSeries, CurrentClampStimulusSeries

import sanpy

if TYPE_CHECKING:
    from sanpy.bAnalysis import bAnalysis


LOGGER = logging.getLogger(__name__)


class SanPyNwbExporter:
    """Export one loaded SanPy current-clamp analysis to an NWB file."""

    def __init__(
        self,
        analysis: bAnalysis,
        timezone_name: str = "America/New_York",
    ) -> None:
        """Initialize the exporter.

        Args:
            analysis: Loaded SanPy ``bAnalysis`` instance.
            timezone_name: IANA timezone used to interpret acquisition date and
                time strings. SanPy currently does not retain a source timezone.

        Raises:
            ValueError: If the analysis has no usable file loader.
        """
        if analysis.loadError or analysis.fileLoader is None:
            raise ValueError("SanPy analysis does not contain a loaded recording")

        self._analysis = analysis
        self._loader = analysis.fileLoader
        self._timezone = ZoneInfo(timezone_name)

    def export(self, output_path: Path) -> Path:
        """Build and write an NWB file.

        Args:
            output_path: Destination path for the NWB file.

        Returns:
            The resolved destination path.

        Raises:
            FileExistsError: If ``output_path`` already exists.
            ValueError: If the SanPy recording is unsupported or inconsistent.
        """
        output_path = output_path.expanduser().resolve()

        # if output_path.exists():
        #     # Avoid silently replacing an existing scientific data file.
        #     raise FileExistsError(f"Refusing to overwrite existing file: {output_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._validate_recording()
        nwbfile = self._build_nwbfile()

        with NWBHDF5IO(path=str(output_path), mode="w") as io:
            io.write(nwbfile)

        return output_path

    def _build_nwbfile(self) -> NWBFile:
        """Construct the in-memory NWB representation.

        Returns:
            An NWB file populated with all current-clamp sweeps and metadata.
        """
        nwbfile = NWBFile(
            session_description=(
                f"SanPy current-clamp recording exported from "
                f"{self._loader.filename}"
            ),
            identifier=str(self._analysis.uuid),
            session_start_time=self._get_session_start_time(),
        )

        # SanPy does not currently expose amplifier hardware details.
        device = nwbfile.create_device(
            name="unknown_device",
            description="Recording device; hardware details not provided",
        )
        electrode = nwbfile.create_icephys_electrode(
            name="electrode_0",
            description="Intracellular electrode; hardware details not provided",
            device=device,
        )

        # NWB uses Hz, while SanPy recordingFrequency is expressed in kHz.
        sampling_rate_hz = float(self._loader.recordingFrequency) * 1000.0

        for sweep in self._loader.sweepList:
            try:
                sweep_x = np.asarray(self._loader.get_sweep_x(sweep))
                sweep_y = np.asarray(self._loader.get_sweep_y(sweep))
                sweep_c = np.asarray(self._loader.get_sweep_c(sweep))
            except IndexError as e:
                LOGGER.warning(f"Sweep {sweep} is missing data: {e}")
                # continue
                raise e

            self._validate_sweep(
                sweep=sweep,
                sweep_x=sweep_x,
                sweep_y=sweep_y,
                sweep_c=sweep_c,
                sampling_rate_hz=sampling_rate_hz,
            )

            # SanPy's time base is sweep-local. Actual inter-sweep offsets are
            # not available through the current public runtime API.
            starting_time = float(sweep_x[0])
            sweep_number = np.uint64(sweep)

            response = CurrentClampSeries(
                name=f"response_sweep_{sweep}",
                data=sweep_y,
                electrode=electrode,
                unit="volts",
                # Preserve stored mV values and convert them to NWB's volts.
                conversion=1e-3,
                starting_time=starting_time,
                rate=sampling_rate_hz,
                sweep_number=sweep_number,
                description="Membrane voltage recorded by SanPy, stored in mV",
            )

            stimulus = CurrentClampStimulusSeries(
                name=f"stimulus_sweep_{sweep}",
                data=sweep_c,
                electrode=electrode,
                unit="amperes",
                # Preserve stored nA values and convert them to NWB's amperes.
                conversion=1e-9,
                starting_time=starting_time,
                rate=sampling_rate_hz,
                sweep_number=sweep_number,
                description=(
                    "Ideal DAC current-clamp command from the SanPy runtime, "
                    "stored in nA"
                ),
            )

            # One table row explicitly associates this sweep's command and Vm.
            nwbfile.add_intracellular_recording(
                electrode=electrode,
                stimulus=stimulus,
                response=response,
            )

        # Preserve mapping order; do not sort metadata keys during serialization.
        nwbfile.add_scratch(
            data=json.dumps(self._loader.metadata),
            name="sanpy_metadata_json",
            description="SanPy file/session metadata serialized as JSON",
        )

        # abb file metadata is not json serializable
        # nwbfile.add_scratch(
        #     data=json.dumps(self._loader.fileMetadata),
        #     name="file_metadata_json",
        #     description="Immutable SanPy file-loader metadata serialized as JSON",
        # )

        return nwbfile

    def _get_session_start_time(self) -> datetime:
        """Return a timezone-aware acquisition datetime.

        Returns:
            The parsed acquisition datetime, or the current system datetime when
            SanPy does not provide both acquisition date and acquisition time.

        Raises:
            ValueError: If non-empty acquisition strings are not valid ISO date
                and time values.
        """
        acquisition_date = self._loader.acqDate
        acquisition_time = self._loader.acqTime

        if not acquisition_date or not acquisition_time:
            fallback = datetime.now(self._timezone)
            LOGGER.warning(
                "SanPy acquisition date or time is empty; using current system "
                "time %s as NWB session_start_time",
                fallback.isoformat(),
            )
            return fallback

        # SanPy documents these as ISO-style YYYY-MM-DD and HH:MM:SS strings.
        parsed = datetime.fromisoformat(f"{acquisition_date}T{acquisition_time}")
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=self._timezone)
        return parsed

    def _validate_recording(self) -> None:
        """Validate recording-level assumptions for the v1 exporter.

        Raises:
            ValueError: If the recording is outside the supported v1 scope.
        """
        if self._loader.recordingMode.value != "I-Clamp":
            raise ValueError(
                "The v1 NWB exporter supports only I-Clamp recordings; got "
                f"{self._loader.recordingMode.value!r}"
            )

        # if self._loader.numChannels != 1:
        #     raise ValueError(
        #         "The v1 NWB exporter requires exactly one normalized channel; "
        #         f"got {self._loader.numChannels}"
        #     )

        if not self._loader.sweepList:
            raise ValueError("The SanPy recording contains no sweeps")
        if len(self._loader.sweepList) != self._loader.numSweeps:
            raise ValueError("SanPy sweepList length does not match numSweeps")
        if self._loader.recordingFrequency is None:
            raise ValueError("SanPy recordingFrequency is unavailable")
        if float(self._loader.recordingFrequency) <= 0:
            raise ValueError("SanPy recordingFrequency must be positive")

    @staticmethod
    def _validate_sweep(
        sweep: int,
        sweep_x: np.ndarray,
        sweep_y: np.ndarray,
        sweep_c: np.ndarray,
        sampling_rate_hz: float,
    ) -> None:
        """Validate one sweep without altering loader state.

        Args:
            sweep: Zero-based sweep number.
            sweep_x: Sweep-local time values in seconds.
            sweep_y: Recorded membrane voltage values in mV.
            sweep_c: Ideal DAC command values in nA.
            sampling_rate_hz: Declared sampling rate in samples per second.

        Raises:
            ValueError: If shapes, lengths, types, or sampling are inconsistent.
        """
        arrays = {"time": sweep_x, "response": sweep_y, "command": sweep_c}
        for label, values in arrays.items():
            if values.ndim != 1:
                raise ValueError(
                    f"Sweep {sweep} {label} must be one-dimensional; "
                    f"got shape {values.shape}"
                )

        if len(sweep_x) < 2:
            raise ValueError(f"Sweep {sweep} must contain at least two samples")
        if len(sweep_x) != len(sweep_y) or len(sweep_y) != len(sweep_c):
            raise ValueError(
                f"Sweep {sweep} time, response, and command lengths differ: "
                f"{len(sweep_x)}, {len(sweep_y)}, {len(sweep_c)}"
            )
        if not np.issubdtype(sweep_y.dtype, np.floating):
            raise ValueError(
                f"Sweep {sweep} response must use a floating dtype; "
                f"got {sweep_y.dtype}"
            )
        if not np.issubdtype(sweep_c.dtype, np.floating):
            raise ValueError(
                f"Sweep {sweep} command must use a floating dtype; got {sweep_c.dtype}"
            )

        sample_intervals = np.diff(sweep_x)
        expected_interval = 1.0 / sampling_rate_hz
        if not np.allclose(
            sample_intervals,
            expected_interval,
            rtol=1e-6,
            atol=max(1e-12, expected_interval * 1e-9),
        ):
            raise ValueError(
                f"Sweep {sweep} time values are not regularly sampled at "
                f"{sampling_rate_hz} Hz"
            )


class NwbRecordingLoader:
    """Open an NWB file while keeping its lazy HDF5 datasets valid."""

    def __init__(self, nwb_path: Path) -> None:
        """Initialize the loader.

        Args:
            nwb_path: Path to an existing NWB file.
        """
        self._nwb_path = nwb_path.expanduser().resolve()

    @contextmanager
    def open(self) -> Iterator[NWBFile]:
        """Open and yield an NWB file, then close its underlying HDF5 handle.

        Yields:
            The loaded NWB file. Consumers must use it only inside the context.

        Raises:
            FileNotFoundError: If the requested NWB file does not exist.
        """
        if not self._nwb_path.is_file():
            raise FileNotFoundError(f"NWB file does not exist: {self._nwb_path}")

        with NWBHDF5IO(path=str(self._nwb_path), mode="r") as io:
            yield io.read()


class NwbExportVerifier:
    """Verify an NWB export against its source SanPy runtime object."""

    def __init__(self, analysis: bAnalysis, nwb_path: Path) -> None:
        """Initialize the verifier.

        Args:
            analysis: Source SanPy analysis used for export.
            nwb_path: Path to the exported NWB file.
        """
        if analysis.fileLoader is None:
            raise ValueError("SanPy analysis does not contain a file loader")
        self._analysis = analysis
        self._loader = analysis.fileLoader
        self._nwb_path = nwb_path.expanduser().resolve()

    def verify(self) -> None:
        """Run schema validation and compare exported data with SanPy.

        Raises:
            ValueError: If NWB schema validation or a round-trip check fails.
        """
        validation_errors = validate(path=self._nwb_path)
        if validation_errors:
            details = "\n".join(str(error) for error in validation_errors)
            raise ValueError(f"NWB schema validation failed:\n{details}")

        expected_rate_hz = float(self._loader.recordingFrequency) * 1000.0

        expected_scratch = {
            "sanpy_metadata_json": json.dumps(self._loader.metadata),
            # "file_metadata_json": json.dumps(self._loader.fileMetadata),
        }

        with NwbRecordingLoader(self._nwb_path).open() as nwbfile:
            recordings = nwbfile.intracellular_recordings
            if recordings is None or len(recordings) != self._loader.numSweeps:
                actual_count = 0 if recordings is None else len(recordings)
                raise ValueError(
                    "Intracellular recording count differs from SanPy: "
                    f"expected {self._loader.numSweeps}, got {actual_count}"
                )

            for sweep in self._loader.sweepList:
                response = nwbfile.acquisition[f"response_sweep_{sweep}"]
                stimulus = nwbfile.stimulus[f"stimulus_sweep_{sweep}"]

                if not np.array_equal(
                    np.asarray(response.data),
                    np.asarray(self._loader.get_sweep_y(sweep)),
                    equal_nan=True,
                ):
                    raise ValueError(f"Sweep {sweep} response failed round-trip check")
                if not np.array_equal(
                    np.asarray(stimulus.data),
                    np.asarray(self._loader.get_sweep_c(sweep)),
                    equal_nan=True,
                ):
                    raise ValueError(f"Sweep {sweep} command failed round-trip check")
                if not np.isclose(response.rate, expected_rate_hz):
                    raise ValueError(f"Sweep {sweep} response rate is incorrect")
                if not np.isclose(stimulus.rate, expected_rate_hz):
                    raise ValueError(f"Sweep {sweep} stimulus rate is incorrect")
                if not np.isclose(response.conversion, 1e-3):
                    raise ValueError(f"Sweep {sweep} voltage conversion is incorrect")
                if not np.isclose(stimulus.conversion, 1e-9):
                    raise ValueError(f"Sweep {sweep} current conversion is incorrect")

            for name, expected_text in expected_scratch.items():
                stored_text = self._read_scratch_text(nwbfile, name)
                if stored_text != expected_text:
                    raise ValueError(f"Scratch metadata {name!r} failed round-trip check")

    @staticmethod
    def _read_scratch_text(nwbfile: NWBFile, name: str) -> str:
        """Read one scalar string from NWB scratch space.

        Args:
            nwbfile: Open NWB file containing the scratch value.
            name: Scratch dataset name.

        Returns:
            The stored text value.

        Raises:
            ValueError: If the scratch value is missing or is not scalar text.
        """
        if name not in nwbfile.scratch:
            raise ValueError(f"Required scratch metadata is missing: {name}")

        value = nwbfile.scratch[name].data
        if (
            not isinstance(value, (str, bytes, np.ndarray))
            and hasattr(value, "shape")
            and hasattr(value, "__getitem__")
        ):
            # A reopened HDF5 scalar may remain a lazy dataset until indexed.
            value = value[()]
        if isinstance(value, np.ndarray):
            if value.ndim != 0:
                raise ValueError(f"Scratch metadata {name!r} is not scalar text")
            value = value.item()
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        if not isinstance(value, str):
            raise ValueError(f"Scratch metadata {name!r} is not text")
        return value


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Edit these hard-coded development paths for your SanPy checkout and data.
    # ABF_PATH = (
    #     Path("/Users/cudmore/Sites/SanPy")
    #     / "sanpy/user_files/SanPy-User-Files/example-data/19114000.abf"
    #     / "/Users/cudmore/Sites/SanPy/sanpy/user_files/SanPy-User-Files/example-data/2021_07_20_0010.abf"
    # )
    ABF_PATH = Path("/Users/cudmore/Sites/SanPy/sanpy/user_files/SanPy-User-Files/example-data/2021_07_20_0010.abf")

    # NWB_PATH = Path("/Users/cudmore/Desktop/nwb/19114000.nwb")
    NWB_PATH = Path("/Users/cudmore/Desktop/nwb") / f"{ABF_PATH.stem}.nwb"

    analysis = sanpy.bAnalysis(str(ABF_PATH))
    if analysis.loadError or analysis.fileLoader is None:
        raise RuntimeError(f"SanPy could not load the recording: {ABF_PATH}")

    exporter = SanPyNwbExporter(analysis)
    written_path = exporter.export(NWB_PATH)

    verifier = NwbExportVerifier(analysis, written_path)
    verifier.verify()

    # Loading is a separate operation and keeps lazy datasets valid in context.
    with NwbRecordingLoader(written_path).open() as loaded_nwb:
        print(loaded_nwb)

    print(f"Exported and verified NWB file: {written_path}")
