"""Tests for the standalone published-DANDI NWB collection."""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest
from pynwb import NWBHDF5IO, NWBFile
from pynwb.icephys import (
    CurrentClampSeries,
    CurrentClampStimulusSeries,
    IntracellularElectrode,
)

from dandi_dataset import (
    DandiDataset,
    DandiDatasetError,
    UnsupportedNwbError,
    _convert_current_to_na,
    _inspect_nwbfile,
    _materialize_recording,
)
from sanpy.fileloaders.fileLoader_nwb import fileLoader_nwb


def _new_nwbfile() -> tuple[NWBFile, IntracellularElectrode]:
    """Create an in-memory NWB file with one intracellular electrode.

    Returns:
        NWB file and its electrode.
    """
    nwbfile = NWBFile(
        session_description="DANDI streaming test",
        identifier="streaming-test",
        session_start_time=datetime(2026, 10, 20, tzinfo=timezone.utc),
        session_id="session-1",
    )
    device = nwbfile.create_device(name="device")
    electrode = nwbfile.create_icephys_electrode(
        name="electrode",
        description="test electrode",
        device=device,
    )
    return nwbfile, electrode


def _response(
    electrode: IntracellularElectrode,
    sweep: int,
) -> CurrentClampSeries:
    """Create one constant voltage response.

    Args:
        electrode: Electrode recording the response.
        sweep: NWB sweep number.

    Returns:
        Current-clamp response in volts.
    """
    return CurrentClampSeries(
        name=f"response_{sweep}",
        data=np.full(5, -0.060 - sweep * 0.001),
        electrode=electrode,
        unit="volts",
        rate=1000.0,
        starting_time=float(sweep),
        sweep_number=np.uint64(sweep),
    )


def _stimulus(
    electrode: IntracellularElectrode,
    sweep: int,
) -> CurrentClampStimulusSeries:
    """Create one constant current stimulus.

    Args:
        electrode: Electrode delivering the stimulus.
        sweep: NWB sweep number.

    Returns:
        Current-clamp stimulus in amperes.
    """
    return CurrentClampStimulusSeries(
        name=f"stimulus_{sweep}",
        data=np.full(5, (sweep + 1) * 1e-10),
        electrode=electrode,
        unit="amperes",
        rate=1000.0,
        starting_time=float(sweep),
        sweep_number=np.uint64(sweep),
    )


def _write_current_clamp(path: Path) -> Path:
    """Write a two-sweep current-clamp NWB fixture.

    Args:
        path: Destination NWB path.

    Returns:
        Written path.
    """
    nwbfile, electrode = _new_nwbfile()
    for sweep in (0, 1):
        nwbfile.add_intracellular_recording(
            electrode=electrode,
            response=_response(electrode, sweep),
            stimulus=_stimulus(electrode, sweep),
        )
    with NWBHDF5IO(str(path), mode="w") as io:
        io.write(nwbfile)
    return path


def test_accepts_explicit_published_identifier() -> None:
    """Parse an explicitly versioned published dandiset without network access."""
    dataset = DandiDataset.from_url("DANDI:001261/0.250917.2023")

    assert dataset.dandiset_id == "001261"
    assert dataset.version == "0.250917.2023"
    assert dataset.assets == ()
    assert len(dataset) == 0
    with pytest.raises(IndexError):
        dataset[0]


def test_accepts_canonical_api_url() -> None:
    """Parse a canonical, explicitly versioned DANDI API URL."""
    dataset = DandiDataset.from_url(
        "https://api.dandiarchive.org/api/dandisets/001261/versions/0.250917.2023"
    )

    assert dataset.dandiset_id == "001261"
    assert dataset.version == "0.250917.2023"


def test_rejects_draft_identifier() -> None:
    """Reject a mutable draft dandiset."""
    with pytest.raises(DandiDatasetError, match="Draft"):
        DandiDataset.from_url("DANDI:001261/draft")


def test_rejects_implicit_version() -> None:
    """Reject a dandiset identifier that omits its published version."""
    with pytest.raises(DandiDatasetError, match="explicit published"):
        DandiDataset.from_url("DANDI:001261")


def test_inspects_and_materializes_current_clamp(tmp_path: Path) -> None:
    """Read compatible header fields and convert voltage/current units.

    Args:
        tmp_path: Temporary directory for the NWB fixture.
    """
    path = _write_current_clamp(tmp_path / "current-clamp.nwb")

    with NWBHDF5IO(str(path), mode="r") as io:
        nwbfile = io.read()
        header, references = _inspect_nwbfile(nwbfile)
        recording = _materialize_recording(header, references)

    assert header.num_sweeps == 2
    assert header.sample_rate_hz == pytest.approx(1000.0)
    assert header.sweep_duration_seconds == pytest.approx(0.004)
    assert header.has_stimulus
    assert recording.time_seconds.shape == (5, 2)
    assert recording.voltage_mv.shape == (5, 2)
    assert recording.current_na is not None
    assert recording.current_na.shape == (5, 2)
    np.testing.assert_allclose(recording.voltage_mv[0], [-60.0, -61.0])
    np.testing.assert_allclose(recording.current_na[0], [0.1, 0.2])

    local_loader = fileLoader_nwb(str(path))
    assert not local_loader.getLoadError()
    np.testing.assert_allclose(recording.time_seconds, local_loader._sweepX)
    np.testing.assert_allclose(recording.voltage_mv, local_loader._sweepY)
    np.testing.assert_allclose(recording.current_na, local_loader._sweepC)


def test_rejects_implausible_nwb_current_scaling() -> None:
    """Reject metadata that interprets whole-cell step values as whole amperes."""
    stored_values = np.asarray([-60.0, 0.0, 200.0])

    with pytest.raises(UnsupportedNwbError, match="1000 nA"):
        _convert_current_to_na(
            stored_values,
            conversion=1.0,
            offset_amperes=0.0,
            stored_unit_override=None,
            label="test stimulus",
        )


def test_explicit_pa_override_repairs_known_stored_units() -> None:
    """Convert raw pA values only when the caller explicitly supplies pA."""
    stored_values = np.asarray([-60.0, 0.0, 200.0])

    current_na = _convert_current_to_na(
        stored_values,
        conversion=1.0,
        offset_amperes=0.0,
        stored_unit_override="pA",
        label="test stimulus",
    )

    np.testing.assert_allclose(current_na, [-0.06, 0.0, 0.2])
