"""Tests for the optional NWB current-clamp loader."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import Mock

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


def test_reads_nwb_metadata_without_materializing_raw_arrays(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Read NWB table metadata without invoking raw-value helpers.

    Args:
        monkeypatch: Pytest fixture used to block raw-value helper calls.
        tmp_path: Temporary directory for the generated NWB file.
    """
    nwbfile, electrode = _new_nwbfile()
    for sweep_number in (0, 1):
        nwbfile.add_intracellular_recording(
            electrode=electrode,
            response=_response(
                electrode,
                sweep_number,
                -0.060,
                name=f"response_{sweep_number}",
            ),
            stimulus=_stimulus(
                electrode,
                sweep_number,
                2e-10,
                name=f"stimulus_{sweep_number}",
            ),
        )
    path = _write(nwbfile, tmp_path / "metadata-only.nwb")
    read_values = Mock(side_effect=AssertionError("raw values were read"))
    read_timestamps = Mock(side_effect=AssertionError("full timestamps were read"))
    monkeypatch.setattr(fileLoader_nwb, "_reference_values", read_values)
    monkeypatch.setattr(fileLoader_nwb, "_reference_timestamps", read_timestamps)

    loader = fileLoader_nwb(str(path), loadData=False)

    assert not loader.getLoadError()
    assert loader.recordingDur == pytest.approx(0.004)
    assert loader.numChannels == 1
    assert loader.numSweeps == 2
    assert loader.numEpochs is None
    assert loader.recordingFrequency == pytest.approx(1.0)
    assert loader.recordingMode.value == "I-Clamp"
    assert loader._sweepX is None
    assert loader._sweepY is None
    assert loader._sweepC is None
    read_values.assert_not_called()
    read_timestamps.assert_not_called()


def test_legacy_pairs_by_sweep_number_not_insertion_order(tmp_path: Path) -> None:
    """Pair legacy responses and stimuli by numeric sweep number.

    Args:
        tmp_path: Temporary directory for the generated NWB file.
    """
    path = _write_legacy(
        tmp_path,
        response_sweeps=[3, 1, 2],
        stimulus_sweeps=[2, 3, 1],
        # metadata={"animal_id": "CG134"},  # abb metadata is now in banalysis
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
    # assert loader.metadata["animal_id"] == "CG134"


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


def test_builds_epoch_table_from_dc_step_command(tmp_path: Path) -> None:
    """Split a DC step command into one epoch per constant level.

    Args:
        tmp_path: Temporary directory for the generated NWB file.
    """
    nwbfile, electrode = _new_nwbfile()
    stimulus = CurrentClampStimulusSeries(
        name="stimulus_0",
        data=np.array([0.0, 0.0, 1e-10, 1e-10, 0.0]),
        electrode=electrode,
        unit="amperes",
        rate=_RATE_HZ,
        starting_time=0.0,
        sweep_number=np.uint64(0),
    )
    nwbfile.add_intracellular_recording(
        electrode=electrode,
        response=_response(electrode, 0, -0.060, name="response_0"),
        stimulus=stimulus,
    )
    path = _write(nwbfile, tmp_path / "stepped.nwb")

    loader = fileLoader_nwb(str(path))

    assert not loader.getLoadError()
    assert loader.numEpochs == 3
    epochs = loader.getEpochTable(0).getEpochList()
    assert [(e["startPoint"], e["stopPoint"]) for e in epochs] == [
        (0, 2),
        (2, 4),
        (4, 5),
    ]
    np.testing.assert_allclose([e["level"] for e in epochs], [0.0, 0.1, 0.0])
    assert {e["type"] for e in epochs} == {"Step"}
    assert loader.getEpochTable(0).findEpoch(4) == 2


@pytest.mark.parametrize(
    ("commands", "expected_bounds", "expected_levels"),
    (
        (
            (np.array([0.0, 0.0, 1e-10, 1e-10, 0.0]), np.zeros(_POINTS)),
            [(0, 2), (2, 4), (4, 5)],
            ([0.0, 0.1, 0.0], [0.0, 0.0, 0.0]),
        ),
        (
            (
                np.array([0.0, 1e-10, 1e-10, 0.0, 0.0]),
                np.array([0.0, 0.0, 0.0, 2e-10, 0.0]),
            ),
            [(0, 1), (1, 3), (3, 4), (4, 5)],
            ([0.0, 0.1, 0.0, 0.0], [0.0, 0.0, 0.2, 0.0]),
        ),
    ),
    ids=("flat-sweep", "no-sweep-shows-every-change"),
)
def test_sweeps_share_union_of_change_points(
    tmp_path: Path,
    commands: tuple[np.ndarray, ...],
    expected_bounds: list[tuple[int, int]],
    expected_levels: tuple[list[float], ...],
) -> None:
    """Give every sweep the union of change points across all sweeps.

    Args:
        tmp_path: Temporary directory for the generated NWB file.
        commands: Stimulus in amperes for each sweep.
        expected_bounds: Shared epoch start and stop points.
        expected_levels: Expected epoch levels in nanoamps for each sweep.
    """
    nwbfile, electrode = _new_nwbfile()
    for sweep_number, data in enumerate(commands):
        nwbfile.add_intracellular_recording(
            electrode=electrode,
            response=_response(
                electrode, sweep_number, -0.060, name=f"response_{sweep_number}"
            ),
            stimulus=CurrentClampStimulusSeries(
                name=f"stimulus_{sweep_number}",
                data=data,
                electrode=electrode,
                unit="amperes",
                rate=_RATE_HZ,
                starting_time=float(sweep_number),
                sweep_number=np.uint64(sweep_number),
            ),
        )
    path = _write(nwbfile, tmp_path / "union.nwb")

    loader = fileLoader_nwb(str(path))

    assert not loader.getLoadError()
    assert loader.numEpochs == len(expected_bounds)
    for sweep, levels in enumerate(expected_levels):
        epochs = loader.getEpochTable(sweep).getEpochList()
        assert [(e["startPoint"], e["stopPoint"]) for e in epochs] == expected_bounds
        np.testing.assert_allclose([e["level"] for e in epochs], levels)


def test_missing_stimulus_sweep_has_no_epoch_table(tmp_path: Path) -> None:
    """Store ``None`` for a sweep whose stimulus is missing.

    Args:
        tmp_path: Temporary directory for the generated NWB file.
    """
    path = _write_legacy(tmp_path, response_sweeps=[0, 1], stimulus_sweeps=[1])

    loader = fileLoader_nwb(str(path))

    assert not loader.getLoadError()
    assert loader.getEpochTable(0) is None
    epochs = loader.getEpochTable(1).getEpochList()
    assert len(epochs) == 1
    assert epochs[0]["level"] == pytest.approx(0.1)


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
