"""Test single-recording export and local Dandiset construction."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import numpy as np
from pynwb import NWBHDF5IO

from export_sanpy_banalysis_to_nwb import (
    NwbExportMetadata,
    NwbExportVerifier,
    SanPyNwbExporter,
)
from export_sanpy_collection import _nwb_sex, _optional_text
from local_dandiset import LocalDandisetBuilder, _normalize_identifier


class _FakeLoader:
    """Provide the minimal public SanPy loader API required by the exporter."""

    def __init__(self, include_datetime: bool = True) -> None:
        """Create a regular one-sweep current-clamp recording.

        Args:
            include_datetime: Whether runtime file metadata includes a timestamp.
        """
        self.filename = "synthetic-recording.abf"
        self.recordingMode = SimpleNamespace(value="I-Clamp")
        self.sweepList = [0]
        self.numSweeps = 1
        self.recordingFrequency = 10.0
        self.metadata: dict[str, str] = {}
        self.fileMetadata = SimpleNamespace(
            acq_datetime=(
                "2026-10-22T12:30:00-04:00" if include_datetime else ""
            ),
            acq_date="" if not include_datetime else "2026-10-22",
            acq_time="" if not include_datetime else "12:30:00",
        )
        self._time = np.arange(20, dtype=float) / 10_000.0
        self._response = np.linspace(-65.0, -55.0, 20)
        self._command = np.zeros(20, dtype=float)

    def get_sweep_x(self, sweep: int) -> np.ndarray:
        """Return synthetic sweep-local time.

        Args:
            sweep: Requested zero-based sweep.

        Returns:
            Time values in seconds.
        """
        if sweep != 0:
            raise IndexError(sweep)
        return self._time

    def get_sweep_y(self, sweep: int) -> np.ndarray:
        """Return synthetic membrane voltage.

        Args:
            sweep: Requested zero-based sweep.

        Returns:
            Voltage values in millivolts.
        """
        if sweep != 0:
            raise IndexError(sweep)
        return self._response

    def get_sweep_c(self, sweep: int) -> np.ndarray:
        """Return synthetic current command.

        Args:
            sweep: Requested zero-based sweep.

        Returns:
            Current values in nanoamps.
        """
        if sweep != 0:
            raise IndexError(sweep)
        return self._command


class _FakeAnalysis:
    """Provide the minimal loaded ``bAnalysis`` surface used by the exporter."""

    def __init__(self, include_datetime: bool = True) -> None:
        """Create a successful analysis wrapper.

        Args:
            include_datetime: Whether runtime file metadata includes a timestamp.
        """
        self.loadError = False
        self.fileLoader = _FakeLoader(include_datetime=include_datetime)
        self.uuid = "synthetic-analysis-uuid"
        self.metaData: dict[str, str] = {}


def _metadata() -> NwbExportMetadata:
    """Return explicit scientific metadata for a synthetic export.

    Returns:
        Valid development export metadata.
    """
    return NwbExportMetadata(
        subject_id="development-subject-001",
        cell_id="development-cell-001",
        species="Mus musculus",
        fallback_acquisition_datetime=datetime(
            1970,
            1,
            1,
            tzinfo=ZoneInfo("America/New_York"),
        ),
        sex="U",
    )


def test_exports_subject_and_runtime_datetime(tmp_path: Path) -> None:
    """Write and verify one NWB file from a synthetic SanPy runtime.

    Args:
        tmp_path: Temporary output directory.
    """
    analysis = _FakeAnalysis()
    output_path = tmp_path / "recording.nwb"
    exporter = SanPyNwbExporter(analysis, _metadata())  # type: ignore[arg-type]

    exporter.export(output_path)
    NwbExportVerifier(analysis, output_path).verify()  # type: ignore[arg-type]

    assert not exporter.used_fallback_acquisition_datetime
    with NWBHDF5IO(str(output_path), mode="r") as io:
        nwbfile = io.read()
        assert nwbfile.subject is not None
        assert nwbfile.subject.subject_id == "development-subject-001"
        assert nwbfile.subject.species == "Mus musculus"
        assert nwbfile.subject.sex == "U"
        electrode = next(iter(nwbfile.icephys_electrodes.values()))
        assert electrode.cell_id == "development-cell-001"
        assert nwbfile.session_start_time.isoformat() == "2026-10-22T12:30:00-04:00"


def test_marks_fallback_acquisition_datetime(tmp_path: Path) -> None:
    """Record explicit fallback use when runtime acquisition metadata is absent.

    Args:
        tmp_path: Temporary output directory.
    """
    analysis = _FakeAnalysis(include_datetime=False)
    output_path = tmp_path / "recording.nwb"
    exporter = SanPyNwbExporter(analysis, _metadata())  # type: ignore[arg-type]

    exporter.export(output_path)

    assert exporter.used_fallback_acquisition_datetime


def test_builds_and_reopens_local_dandiset(tmp_path: Path) -> None:
    """Organize one verified NWB into a local Dandiset.

    Args:
        tmp_path: Temporary source and destination parent.
    """
    analysis = _FakeAnalysis()
    staged_path = tmp_path / "staged" / "recording.nwb"
    SanPyNwbExporter(analysis, _metadata()).export(staged_path)  # type: ignore[arg-type]

    report = LocalDandisetBuilder(
        output_directory=tmp_path / "dandiset",
        identifier="000000",
        name="Synthetic SanPy Dandiset",
        description="Synthetic local export test.",
    ).build([staged_path])

    assert report.identifier == "DANDI:000000"
    assert len(report.asset_paths) == 1
    assert report.asset_paths[0].endswith(".nwb")
    blocking = [
        result
        for result in report.validation_results
        if result.severity is not None
        and result.severity.name in {"WARNING", "ERROR", "CRITICAL"}
    ]
    assert len(blocking) == 1
    assert blocking[0].id == "NWBI.check_subject_age"


def test_normalizes_optional_metadata() -> None:
    """Normalize optional SanPy values without inventing missing metadata."""
    assert _optional_text("") is None
    assert _optional_text("  P90D ") == "P90D"
    assert _nwb_sex("female") == "F"
    assert _nwb_sex("unknown") == "U"
    assert _nwb_sex("") == "U"
    assert _normalize_identifier("000000") == "DANDI:000000"
