"""Write and read one SanPy intracellular recording as an NWB file."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, field_validator
from pynwb import NWBHDF5IO, NWBFile, validate
from pynwb.file import Subject
from pynwb.icephys import (
    CurrentClampSeries,
    CurrentClampStimulusSeries,
    VoltageClampSeries,
    VoltageClampStimulusSeries,
)

from sanpy.bAnalysisResults import AnalysisResults
from sanpy.bDetection import DetectionParameters
from sanpy.fileloaders import recordingModes
from sanpy.io.nwb.payload import (
    SANPY_PAYLOAD_NAME,
    SanpyNwbPayload,
    build_payload,
)


class NwbRecordingMetadata(BaseModel):
    """Provide explicit scientific metadata required for one NWB recording."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    subject_id: str
    cell_id: str
    species: str
    session_start_time: datetime
    session_description: str = "SanPy intracellular recording"
    age: str | None = None
    sex: str | None = None
    genotype: str | None = None

    @field_validator("subject_id", "cell_id", "species", "session_description")
    @classmethod
    def _require_text(cls, value: str) -> str:
        """Require nonempty identifying metadata.

        Args:
            value: Candidate text value.

        Returns:
            Stripped nonempty text.

        Raises:
            ValueError: If the value is empty.
        """
        value = value.strip()
        if not value:
            raise ValueError("NWB identifying text must not be empty")
        return value

    @field_validator("session_start_time")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        """Require an explicit acquisition timezone.

        Args:
            value: Candidate session start time.

        Returns:
            Timezone-aware datetime.

        Raises:
            ValueError: If the datetime is timezone-naive.
        """
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("session_start_time must include a timezone")
        return value


def write_recording(
    analysis: Any,
    path: str | Path,
    recording_metadata: NwbRecordingMetadata,
) -> Path:
    """Write one validated SanPy analysis to a fresh NWB file.

    Args:
        analysis: Loaded SanPy ``bAnalysis`` instance.
        path: New destination path.
        recording_metadata: Explicit NWB subject and session metadata.

    Returns:
        Resolved path to the completed NWB file.

    Raises:
        FileExistsError: If the destination already exists.
        ValueError: If raw data or SanPy state is unsupported.
        RuntimeError: If PyNWB validation reports an error.
    """
    destination = Path(path).expanduser().resolve()
    if destination.exists():
        raise FileExistsError(f"Refusing to replace NWB file: {destination}")
    loader = analysis.fileLoader
    if analysis.loadError or loader is None:
        raise ValueError("Analysis has no loaded recording")
    payload = build_payload(analysis)
    if loader.recordingMode is recordingModes.vclamp and (
        payload.analysis_performed
        or payload.detection_parameters is not None
        or payload.analysis_results
    ):
        raise ValueError("Voltage-clamp recordings cannot save spike analysis")
    if loader.recordingMode not in {recordingModes.iclamp, recordingModes.vclamp}:
        raise ValueError(f"Unsupported recording mode: {loader.recordingMode.value}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    nwbfile = _build_nwbfile(analysis, recording_metadata, payload)
    handle = tempfile.NamedTemporaryFile(
        prefix=f".{destination.stem}-", suffix=".nwb", dir=destination.parent, delete=False
    )
    temporary = Path(handle.name)
    handle.close()
    try:
        with NWBHDF5IO(path=str(temporary), mode="w") as io:
            io.write(nwbfile)
        validation_errors = validate(path=str(temporary))
        if validation_errors:
            raise RuntimeError(
                f"PyNWB validation failed for {destination.name}: {validation_errors}"
            )
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return destination


def read_recording(path: str | Path) -> Any:
    """Load one local intracellular NWB recording through SanPy.

    Args:
        path: Existing local NWB path.

    Returns:
        Loaded ``bAnalysis`` instance.

    Raises:
        ValueError: If SanPy cannot represent the NWB recording.
    """
    import sanpy

    analysis = sanpy.bAnalysis(str(Path(path).expanduser().resolve()))
    if analysis.loadError:
        raise ValueError(f"SanPy could not load intracellular NWB recording: {path}")
    return analysis


def _build_nwbfile(
    analysis: Any,
    metadata: NwbRecordingMetadata,
    payload: SanpyNwbPayload,
) -> NWBFile:
    """Build the complete in-memory NWB representation.

    Args:
        analysis: Loaded SanPy analysis.
        metadata: Explicit NWB metadata.
        payload: Validated SanPy extension payload.

    Returns:
        Populated NWB file.
    """
    loader = analysis.fileLoader
    nwbfile = NWBFile(
        session_description=metadata.session_description,
        identifier=str(analysis.uuid),
        session_start_time=metadata.session_start_time,
        subject=Subject(
            subject_id=metadata.subject_id,
            species=metadata.species,
            age=metadata.age,
            sex=metadata.sex,
            genotype=metadata.genotype,
        ),
    )
    device = nwbfile.create_device(
        name="unknown_device",
        description="Recording device details are unavailable in SanPy",
    )
    electrode = nwbfile.create_icephys_electrode(
        name="electrode_0",
        description="Intracellular electrode",
        device=device,
        cell_id=metadata.cell_id,
    )
    rate_hz = float(loader.recordingFrequency) * 1000.0
    for sweep in loader.sweepList:
        sweep_x = np.asarray(loader.get_sweep_x(sweep), dtype=np.float64)
        sweep_y = np.asarray(loader.get_sweep_y(sweep), dtype=np.float64)
        sweep_c = np.asarray(loader.get_sweep_c(sweep), dtype=np.float64)
        _validate_sweep(sweep, sweep_x, sweep_y, sweep_c, rate_hz)
        common = {
            "electrode": electrode,
            "starting_time": float(sweep_x[0]),
            "rate": rate_hz,
            "sweep_number": np.uint64(sweep),
        }
        if loader.recordingMode is recordingModes.iclamp:
            response = CurrentClampSeries(
                name=f"response_sweep_{sweep}",
                data=sweep_y,
                unit="volts",
                conversion=1e-3,
                description="SanPy membrane voltage stored in mV",
                **common,
            )
            stimulus = CurrentClampStimulusSeries(
                name=f"stimulus_sweep_{sweep}",
                data=sweep_c,
                unit="amperes",
                conversion=1e-12,
                description="SanPy current command stored in pA",
                **common,
            )
        else:
            response = VoltageClampSeries(
                name=f"response_sweep_{sweep}",
                data=sweep_y,
                unit="amperes",
                conversion=_current_conversion(loader.sweepLabelY),
                description=f"SanPy clamp current stored in {loader.sweepLabelY}",
                **common,
            )
            stimulus = VoltageClampStimulusSeries(
                name=f"stimulus_sweep_{sweep}",
                data=sweep_c,
                unit="volts",
                conversion=1e-3,
                description="SanPy voltage command stored in mV",
                **common,
            )
        nwbfile.add_intracellular_recording(
            electrode=electrode, stimulus=stimulus, response=response
        )
    nwbfile.add_scratch(
        data=payload.model_dump_json(),
        name=SANPY_PAYLOAD_NAME,
        description="Versioned SanPy analysis payload encoded as strict JSON",
    )
    nwbfile.add_scratch(
        data=json.dumps(SanpyNwbPayload.model_json_schema(), separators=(",", ":")),
        name="sanpy_nwb_payload_schema_json",
        description="JSON Schema for the stored SanPy NWB payload",
    )
    nwbfile.add_scratch(
        data=json.dumps(DetectionParameters.model_json_schema(), separators=(",", ":")),
        name="sanpy_detection_parameters_schema_json",
        description="JSON Schema for SanPy detection parameters",
    )
    nwbfile.add_scratch(
        data=json.dumps(AnalysisResults.model_json_schema(), separators=(",", ":")),
        name="sanpy_analysis_results_schema_json",
        description="JSON Schema for one SanPy analysis result",
    )
    return nwbfile


def _validate_sweep(
    sweep: int,
    sweep_x: np.ndarray,
    sweep_y: np.ndarray,
    sweep_c: np.ndarray,
    rate_hz: float,
) -> None:
    """Validate one raw sweep before NWB construction.

    Args:
        sweep: Zero-based sweep index.
        sweep_x: Time values in seconds.
        sweep_y: Response values in SanPy runtime units.
        sweep_c: Command values in SanPy runtime units.
        rate_hz: Declared regular sample rate.

    Raises:
        ValueError: If shapes, values, or sampling are invalid.
    """
    if sweep_x.ndim != 1 or sweep_y.ndim != 1 or sweep_c.ndim != 1:
        raise ValueError(f"Sweep {sweep} arrays must be one-dimensional")
    if len(sweep_x) < 2 or len(sweep_x) != len(sweep_y) or len(sweep_x) != len(sweep_c):
        raise ValueError(f"Sweep {sweep} response, command, and time lengths differ")
    if not all(np.isfinite(values).all() for values in (sweep_x, sweep_y, sweep_c)):
        raise ValueError(f"Sweep {sweep} contains nonfinite raw values")
    intervals = np.diff(sweep_x)
    if not np.allclose(intervals, 1.0 / rate_hz, rtol=1e-9, atol=1e-12):
        raise ValueError(f"Sweep {sweep} is not sampled at the declared rate")


def _current_conversion(unit: str) -> float:
    """Return the NWB ampere conversion for one SanPy current label.

    Args:
        unit: SanPy response unit label.

    Returns:
        Multiplier converting stored values to amperes.

    Raises:
        ValueError: If the current unit is unsupported.
    """
    conversions = {"A": 1.0, "pA": 1e-12, "nA": 1e-9, "uA": 1e-6}
    try:
        return conversions[unit]
    except KeyError as error:
        raise ValueError(f"Unsupported SanPy current unit: {unit!r}") from error
