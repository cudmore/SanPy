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
    VoltageClampSeries,
    VoltageClampStimulusSeries,
)

from dandi_dataset import (
    DandiAssetMetadata,
    DandiDataset,
    DandiDatasetError,
    DandiNwbAsset,
    DandiSweep,
    NwbHeaderMetadata,
    UnsupportedNwbError,
    _apply_nwb_conversion,
    _dataset_metadata,
    _inspect_nwbfile,
    _materialize_recording,
    _materialize_sweep,
    _min_max_downsample,
    _summarize_nwbfile,
)


def test_maps_published_dataset_metadata() -> None:
    """Map the useful DANDI metadata subset and normalize DOI URLs."""
    metadata = _dataset_metadata(
        {
            "name": "Example intracellular dataset",
            "description": "A useful description.",
            "doi": "https://doi.org/10.48324/dandi.001261/0.250917.2023",
            "url": "https://dandiarchive.org/dandiset/001261/0.250917.2023",
            "citation": "Example citation.",
        },
        dandiset_id="001261",
        version="0.250917.2023",
    )

    assert metadata.name == "Example intracellular dataset"
    assert metadata.doi == "10.48324/dandi.001261/0.250917.2023"
    assert metadata.citation == "Example citation."


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


def _voltage_clamp_response(
    electrode: IntracellularElectrode,
    sweep: int,
) -> VoltageClampSeries:
    """Create one constant voltage-clamp current response.

    Args:
        electrode: Electrode recording the response.
        sweep: NWB sweep number.

    Returns:
        Voltage-clamp response in amperes.
    """
    return VoltageClampSeries(
        name=f"vc_response_{sweep}",
        data=np.full(5, (sweep + 1) * 1e-12),
        electrode=electrode,
        unit="amperes",
        rate=2000.0,
        starting_time=float(sweep),
        sweep_number=np.uint64(sweep),
    )


def _voltage_clamp_stimulus(
    electrode: IntracellularElectrode,
    sweep: int,
) -> VoltageClampStimulusSeries:
    """Create one constant voltage-clamp voltage command.

    Args:
        electrode: Electrode delivering the stimulus.
        sweep: NWB sweep number.

    Returns:
        Voltage-clamp stimulus in volts.
    """
    return VoltageClampStimulusSeries(
        name=f"vc_stimulus_{sweep}",
        data=np.full(5, -0.070 + sweep * 0.005),
        electrode=electrode,
        unit="volts",
        rate=2000.0,
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


def test_accepts_published_dandi_doi_url() -> None:
    """Normalize a published DANDI DOI URL without network access."""
    dataset = DandiDataset.from_url(
        "https://doi.org/10.48324/dandi.001544/0.260827.1410"
    )

    assert dataset.dandiset_id == "001544"
    assert dataset.version == "0.260827.1410"


def test_rejects_draft_identifier() -> None:
    """Reject a mutable draft dandiset."""
    with pytest.raises(DandiDatasetError, match="Draft"):
        DandiDataset.from_url("DANDI:001261/draft")


def test_rejects_implicit_version() -> None:
    """Reject a dandiset identifier that omits its published version."""
    with pytest.raises(DandiDatasetError, match="explicit published"):
        DandiDataset.from_url("DANDI:001261")


def test_inspects_and_materializes_current_clamp(tmp_path: Path) -> None:
    """Read current-clamp values in their declared NWB base units.

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
    assert header.clamp_mode == "current clamp"
    assert recording.response_values.shape == (5, 2)
    assert recording.response_unit == "volts"
    assert recording.stimulus_values is not None
    assert recording.stimulus_values.shape == (5, 2)
    assert recording.stimulus_unit == "amperes"
    np.testing.assert_allclose(recording.response_values[0], [-0.060, -0.061])
    np.testing.assert_allclose(recording.stimulus_values[0], [1e-10, 2e-10])


def test_inspects_and_materializes_voltage_clamp() -> None:
    """Read voltage-clamp response and stimulus in NWB base units."""
    nwbfile, electrode = _new_nwbfile()
    for sweep in (0, 1):
        nwbfile.add_intracellular_recording(
            electrode=electrode,
            response=_voltage_clamp_response(electrode, sweep),
            stimulus=_voltage_clamp_stimulus(electrode, sweep),
        )

    header, references = _inspect_nwbfile(nwbfile)
    recording = _materialize_recording(header, references)

    assert header.clamp_mode == "voltage clamp"
    assert header.num_sweeps == 2
    assert recording.response_unit == "amperes"
    assert recording.stimulus_unit == "volts"
    np.testing.assert_allclose(recording.response_values[0], [1e-12, 2e-12])
    assert recording.stimulus_values is not None
    np.testing.assert_allclose(recording.stimulus_values[0], [-0.070, -0.065])


def test_applies_only_official_nwb_conversion_and_offset() -> None:
    """Apply series conversion metadata without magnitude repair or SI scaling."""
    _nwbfile, electrode = _new_nwbfile()
    series = CurrentClampStimulusSeries(
        name="scaled",
        data=np.asarray([-60.0, 0.0, 200.0]),
        electrode=electrode,
        unit="amperes",
        conversion=2.0,
        offset=3.0,
        rate=1000.0,
        starting_time=0.0,
    )

    converted = _apply_nwb_conversion(np.asarray(series.data), series)

    np.testing.assert_allclose(converted, [-117.0, 3.0, 403.0])


def test_materializes_only_selected_sweep(tmp_path: Path) -> None:
    """Materialize one selected sweep as one-dimensional complete arrays.

    Args:
        tmp_path: Temporary directory for the NWB fixture.
    """
    path = _write_current_clamp(tmp_path / "selected-sweep.nwb")

    with NWBHDF5IO(str(path), mode="r") as io:
        nwbfile = io.read()
        header, references = _inspect_nwbfile(nwbfile)
        sweep = _materialize_sweep(header, references[1], sweep_index=1)

    assert sweep.sweep_index == 1
    assert sweep.time_seconds.shape == (5,)
    assert sweep.response_values.shape == (5,)
    assert sweep.response_unit == "volts"
    assert sweep.stimulus_values is not None
    assert sweep.stimulus_values.shape == (5,)
    assert sweep.stimulus_unit == "amperes"
    np.testing.assert_allclose(sweep.response_values, -0.061)
    np.testing.assert_allclose(sweep.stimulus_values, 2e-10)


def test_builds_lightweight_summary_header(tmp_path: Path) -> None:
    """Read catalog fields without performing full-recording validation.

    Args:
        tmp_path: Temporary directory for the NWB fixture.
    """
    path = _write_current_clamp(tmp_path / "summary.nwb")

    with NWBHDF5IO(str(path), mode="r") as io:
        header = _summarize_nwbfile(io.read())

    assert header.num_sweeps == 2
    assert header.sample_rate_hz == pytest.approx(1000.0)
    assert header.samples_per_sweep == 5
    assert header.sweep_duration_seconds == pytest.approx(0.004)


def test_min_max_downsampling_preserves_fast_action_potential() -> None:
    """Keep a narrow action-potential peak when reducing a long trace."""
    time_seconds = np.arange(10_000, dtype=np.float64) / 10_000.0
    voltage_mv = np.full(10_000, -70.0)
    voltage_mv[4_999] = 35.0

    plot_time, plot_voltage = _min_max_downsample(
        time_seconds,
        voltage_mv,
        max_points=500,
    )

    assert len(plot_time) <= 500
    assert len(plot_time) == len(plot_voltage)
    assert 35.0 in plot_voltage
    assert np.all(np.diff(plot_time) >= 0)


def test_sweep_plot_data_supplies_units_and_preserves_complete_arrays() -> None:
    """Expose declared base-unit labels without modifying complete arrays."""
    time_seconds = np.arange(10, dtype=np.float64) / 1000.0
    response_values = np.linspace(-0.070, 0.030, 10)
    stimulus_values = np.linspace(-1e-10, 2e-10, 10)
    header = _test_header(samples_per_sweep=10)
    sweep = DandiSweep(
        header=header,
        sweep_index=0,
        time_seconds=time_seconds,
        response_values=response_values,
        response_unit="volts",
        stimulus_values=stimulus_values,
        stimulus_unit="amperes",
        warnings=(),
    )

    plot_data = sweep.to_plot_data(max_points=6)

    assert plot_data.response.x_axis_label == "Time (s)"
    assert plot_data.response.y_axis_label == "Voltage (V)"
    assert plot_data.stimulus is not None
    assert plot_data.stimulus.y_axis_label == "Current (A)"
    assert np.max(plot_data.stimulus.values) == pytest.approx(2e-10)
    np.testing.assert_allclose(sweep.stimulus_values, stimulus_values)


def test_asset_summary_provides_complete_table_row() -> None:
    """Build a table-ready row entirely in the backend API.
    """
    dataset = DandiDataset.from_url("DANDI:001261/0.250917.2023")
    metadata = DandiAssetMetadata(
        asset_id="asset-id",
        path="subject/session.nwb",
        size_bytes=12_500_000,
        created=None,
        modified=None,
    )
    asset = DandiNwbAsset(dataset, metadata)
    header = _test_header(samples_per_sweep=10)
    asset._header = header

    row = asset.load_summary(index=3).to_row()

    assert row["index"] == 3
    assert row["path"] == "subject/session.nwb"
    assert row["size_mb"] == 12.5
    assert row["status"] == "summary ready"
    assert row["subject_id"] == "subject"
    assert row["num_sweeps"] == 1
    assert row["duration_seconds"] == pytest.approx(0.009)


def test_sweep_plot_data_is_cached_by_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reuse prepared plot traces without materializing a sweep again.

    Args:
        monkeypatch: Pytest fixture used to isolate plot caching from file access.
    """
    dataset = DandiDataset.from_url("DANDI:001261/0.250917.2023")
    metadata = DandiAssetMetadata(
        asset_id="asset-id",
        path="subject/session.nwb",
        size_bytes=100,
        created=None,
        modified=None,
    )
    asset = DandiNwbAsset(dataset, metadata)
    load_count = 0

    def load_sweep(
        sweep_index: int,
    ) -> DandiSweep:
        """Return deterministic sweep data while counting materializations.

        Args:
            sweep_index: Requested zero-based sweep position.
        Returns:
            Deterministic test sweep.
        """
        nonlocal load_count
        load_count += 1
        values = np.arange(10, dtype=np.float64)
        return DandiSweep(
            header=_test_header(samples_per_sweep=10),
            sweep_index=sweep_index,
            time_seconds=values / 1000.0,
            response_values=values,
            response_unit="volts",
            stimulus_values=values / 1000.0,
            stimulus_unit="amperes",
            warnings=(),
        )

    monkeypatch.setattr(asset, "load_sweep", load_sweep)

    first = asset.load_sweep_plot_data(0, max_points=6)
    second = asset.load_sweep_plot_data(0, max_points=6)

    assert first is second
    assert load_count == 1


def _test_header(samples_per_sweep: int) -> NwbHeaderMetadata:
    """Build compact header metadata for value-object tests.

    Args:
        samples_per_sweep: Number of samples represented by the header.

    Returns:
        Header metadata accepted by ``DandiSweep``.
    """
    return NwbHeaderMetadata(
        subject_id="subject",
        session_id="session",
        acquisition_datetime="2026-10-20T00:00:00+00:00",
        num_sweeps=1,
        num_channels=1,
        sample_rate_hz=1000.0,
        samples_per_sweep=samples_per_sweep,
        sweep_duration_seconds=(samples_per_sweep - 1) / 1000.0,
        has_stimulus=True,
        clamp_mode="current clamp",
    )
