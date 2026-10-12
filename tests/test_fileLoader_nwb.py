"""Tests for the optional NWB current-clamp loader."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pytest

pytest.importorskip("pynwb")

from pynwb import NWBHDF5IO, NWBFile  # noqa: E402
from pynwb.icephys import (  # noqa: E402
    CurrentClampSeries,
    CurrentClampStimulusSeries,
    IntracellularElectrode,
)

from sanpy.fileloaders import getFileLoaders  # noqa: E402
from sanpy.fileloaders.fileLoader_nwb import fileLoader_nwb  # noqa: E402

_POINTS = 5
_RATE_HZ = 1000.0


def _new_nwbfile() -> tuple[NWBFile, IntracellularElectrode]:
    """Create an in-memory NWB file with one intracellular electrode.

    Returns:
        The NWB file and its electrode.
    """
    nwbfile = NWBFile(
        session_description="test",
        identifier="test-id",
        session_start_time=datetime(2021, 5, 20, 12, 54, 47, tzinfo=timezone.utc),
    )
    device = nwbfile.create_device(name="device")
    electrode = nwbfile.create_icephys_electrode(
        name="electrode", description="test", device=device
    )
    return nwbfile, electrode


def _response(
    electrode: IntracellularElectrode, sweep_number: int, volts: float, name: str
) -> CurrentClampSeries:
    """Create a constant response series.

    Args:
        electrode: Electrode recording the response.
        sweep_number: NWB sweep number.
        volts: Constant membrane potential in volts.
        name: Unique NWB object name.

    Returns:
        A current-clamp response series.
    """
    return CurrentClampSeries(
        name=name,
        data=np.full(_POINTS, volts),
        electrode=electrode,
        unit="volts",
        rate=_RATE_HZ,
        starting_time=float(sweep_number),
        sweep_number=np.uint64(sweep_number),
    )


def _stimulus(
    electrode: IntracellularElectrode, sweep_number: int, amperes: float, name: str
) -> CurrentClampStimulusSeries:
    """Create a constant stimulus series.

    Args:
        electrode: Electrode delivering the stimulus.
        sweep_number: NWB sweep number.
        amperes: Constant command current in amperes.
        name: Unique NWB object name.

    Returns:
        A current-clamp stimulus series.
    """
    return CurrentClampStimulusSeries(
        name=name,
        data=np.full(_POINTS, amperes),
        electrode=electrode,
        unit="amperes",
        rate=_RATE_HZ,
        starting_time=float(sweep_number),
        sweep_number=np.uint64(sweep_number),
    )


def _write(nwbfile: NWBFile, path: Path) -> Path:
    """Write an NWB file to disk.

    Args:
        nwbfile: In-memory NWB file.
        path: Destination path.

    Returns:
        The destination path.
    """
    with NWBHDF5IO(str(path), mode="w") as io:
        io.write(nwbfile)
    return path


def _write_legacy(
    tmp_path: Path,
    response_sweeps: list[int],
    stimulus_sweeps: list[int],
    metadata: Optional[dict[str, str]] = None,
) -> Path:
    """Write series to acquisition and stimulus without a recordings table.

    Args:
        tmp_path: Temporary directory for the file.
        response_sweeps: Sweep numbers for response series, in insertion order.
        stimulus_sweeps: Sweep numbers for stimulus series, in insertion order.
        metadata: Optional SanPy metadata to store in scratch space.

    Returns:
        Path to the written NWB file.
    """
    nwbfile, electrode = _new_nwbfile()
    for index, sweep_number in enumerate(response_sweeps):
        nwbfile.add_acquisition(
            _response(
                electrode,
                sweep_number,
                -0.060 - sweep_number * 0.001,
                name=f"response_{index}",
            )
        )
    for index, sweep_number in enumerate(stimulus_sweeps):
        nwbfile.add_stimulus(
            _stimulus(
                electrode,
                sweep_number,
                sweep_number * 1e-10,
                name=f"stimulus_{index}",
            )
        )
    if metadata is not None:
        nwbfile.add_scratch(
            data=json.dumps(metadata),
            name="sanpy_metadata_json",
            description="SanPy metadata",
        )
    return _write(nwbfile, tmp_path / "legacy.nwb")


def test_loads_intracellular_recordings_table(tmp_path: Path) -> None:
    """Load modern table rows with unit conversion and sweep-local time.

    Args:
        tmp_path: Temporary directory for the generated NWB file.
    """
    nwbfile, electrode = _new_nwbfile()
    for sweep_number in (0, 1):
        nwbfile.add_intracellular_recording(
            electrode=electrode,
            response=_response(
                electrode, sweep_number, -0.060, name=f"response_{sweep_number}"
            ),
            stimulus=_stimulus(
                electrode,
                sweep_number,
                2e-10 * (sweep_number + 1),
                name=f"stimulus_{sweep_number}",
            ),
        )
    path = _write(nwbfile, tmp_path / "modern.nwb")

    loader = fileLoader_nwb(str(path))

    assert not loader.getLoadError()
    assert loader.numSweeps == 2
    assert loader.recordingMode.value == "I-Clamp"
    assert loader.dataPointsPerMs == pytest.approx(1.0)
    assert loader.acqDate == "2021-05-20"
    assert loader.acqTime == "12:54:47"
    np.testing.assert_allclose(loader.get_sweep_x(1), np.arange(_POINTS) / _RATE_HZ)
    np.testing.assert_allclose(loader.get_sweep_y(0), np.full(_POINTS, -60.0))
    np.testing.assert_allclose(loader.get_sweep_c(1), np.full(_POINTS, 0.4))


def test_legacy_pairs_by_sweep_number_not_insertion_order(tmp_path: Path) -> None:
    """Pair legacy responses and stimuli by numeric sweep number.

    Args:
        tmp_path: Temporary directory for the generated NWB file.
    """
    path = _write_legacy(
        tmp_path,
        response_sweeps=[3, 1, 2],
        stimulus_sweeps=[2, 3, 1],
        metadata={"animal_id": "CG134"},
    )

    loader = fileLoader_nwb(str(path))

    assert not loader.getLoadError()
    assert loader.numSweeps == 3
    for column, sweep_number in enumerate((1, 2, 3)):
        np.testing.assert_allclose(
            loader.get_sweep_y(column), np.full(_POINTS, -60.0 - sweep_number)
        )
        np.testing.assert_allclose(
            loader.get_sweep_c(column), np.full(_POINTS, 0.1 * sweep_number)
        )
        np.testing.assert_allclose(
            loader.get_sweep_x(column), np.arange(_POINTS) / _RATE_HZ
        )
    assert loader.metadata["animal_id"] == "CG134"


def test_legacy_missing_stimulus_inserts_zero_command(tmp_path: Path) -> None:
    """Load a legacy response without a stimulus as a zero command column.

    Args:
        tmp_path: Temporary directory for the generated NWB file.
    """
    path = _write_legacy(tmp_path, response_sweeps=[0, 1], stimulus_sweeps=[1])

    loader = fileLoader_nwb(str(path))

    assert not loader.getLoadError()
    np.testing.assert_array_equal(loader.get_sweep_c(0), np.zeros(_POINTS))
    np.testing.assert_allclose(loader.get_sweep_c(1), np.full(_POINTS, 0.1))


@pytest.mark.parametrize(
    ("response_sweeps", "stimulus_sweeps"),
    (
        ([0, 0], [0]),
        ([0], [0, 0]),
        ([0], [0, 1]),
    ),
    ids=("duplicate-response", "duplicate-stimulus", "orphan-stimulus"),
)
def test_legacy_ambiguous_pairing_is_load_error(
    tmp_path: Path,
    response_sweeps: list[int],
    stimulus_sweeps: list[int],
) -> None:
    """Reject legacy files whose series cannot be paired unambiguously.

    Args:
        tmp_path: Temporary directory for the generated NWB file.
        response_sweeps: Sweep numbers for response series.
        stimulus_sweeps: Sweep numbers for stimulus series.
    """
    path = _write_legacy(tmp_path, response_sweeps, stimulus_sweeps)

    loader = fileLoader_nwb(str(path))

    assert loader.getLoadError()


def test_registry_discovers_nwb_loader() -> None:
    """Register ``.nwb`` automatically when PyNWB is installed."""
    assert getFileLoaders()[".nwb"]["constructor"] is fileLoader_nwb
