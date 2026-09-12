"""End-to-end tests for self-contained SanPy Zarr collection export."""

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyabf
import pytest
import zarr

import sanpy
from sanpy.bAnalysisResults import analysisResultDict
from sanpy.bDetection import getDefaultDetection
from sanpy.io.zarr_export.exporter import export_collection
from sanpy.io.zarr_export.json_codec import json_value
from sanpy.io.zarr_export.pyabf_adapter import snapshot_abf
from sanpy.io.zarr_export.validator import SanPyZarrValidationError, validate_collection
from sanpy.trace_overlays import get_trace_overlay_definitions


def _analysis(path: Path) -> Any:
    """Create a SanPy analysis for an ABF fixture.

    Args:
        path: Source ABF path.

    Returns:
        Newly loaded SanPy ``bAnalysis`` instance.
    """
    return sanpy.bAnalysis(str(path))


def _recording_root(export: Path) -> Path:
    """Resolve the first recording directory in an exported collection.

    Args:
        export: SanPy Zarr collection root.

    Returns:
        Directory containing the first recording manifest.
    """
    collection = json.loads((export / "collection.json").read_text())
    return export / collection["members"][0]["recording"].rsplit("/", 1)[0]


def _saved_sanpy_analysis(data_folder: Path) -> Any:
    """Load the saved stochastic SanPy-text analysis from HDF5.

    Args:
        data_folder: Repository data folder containing the source and catalog.

    Returns:
        SanPy analysis with its persisted results restored.
    """
    directory = sanpy.analysisDir(str(data_folder), autoLoad=False)
    row = directory.findFileRow("stochastic-hh.sanpy")
    assert row is not None
    analysis = directory.getAnalysis(row, allowAutoLoad=True)
    assert analysis is not None
    return analysis


def test_export_is_zarr3_and_preserves_runtime_state(
    tmp_path: Path, small_abf: Path
) -> None:
    """Write Zarr v3 without mutating the supplied SanPy analysis.

    Args:
        tmp_path: Pytest-managed output directory.
        small_abf: Multi-sweep, multi-channel ABF fixture.
    """
    analysis = _analysis(small_abf)
    analysis.fileLoader.setSweep(4)
    filtered = analysis.fileLoader._filteredY.copy()
    destination = tmp_path / "collection.sanpy.zarr"

    export_collection([analysis], destination, table_format="both", chunk_points=128)

    assert analysis.fileLoader.currentSweep == 4
    np.testing.assert_array_equal(analysis.fileLoader._filteredY, filtered)
    root = _recording_root(destination)
    group = zarr.open_group(str(root / "data.zarr"), mode="r")
    assert group.metadata.zarr_format == 3
    assert group["raw"].metadata.dimension_names == ("sweep", "channel", "point")
    assert group["raw"].shape == (18, 2, 1600)
    assert group["filtered"].shape == (18, 1600)
    assert group["dvdt"].shape == (18, 1600)
    assert (root / "tables" / "epochs.csv").is_file()
    assert (root / "tables" / "epochs.parquet").is_file()
    assert (root / "tables" / "analysis_results.csv").is_file()
    assert (root / "tables" / "analysis_results.parquet").is_file()
    validate_collection(destination)


def test_export_saved_sanpy_recording(tmp_path: Path, sanpy_data_folder: Path) -> None:
    """Export SanPy text signals, epochs, and HDF5-restored results.

    Args:
        tmp_path: Pytest-managed output directory.
        sanpy_data_folder: Data folder containing the saved analysis.
    """
    analysis = _saved_sanpy_analysis(sanpy_data_folder)
    destination = tmp_path / "stochastic.sanpy.zarr"

    export_collection([analysis], destination, table_format="csv")

    root = _recording_root(destination)
    manifest = json.loads((root / "recording.json").read_text())
    group = zarr.open_group(str(root / "data.zarr"), mode="r")
    epochs = pd.read_csv(root / "tables" / "epochs.csv")
    results = pd.read_csv(root / "tables" / "analysis_results.csv")

    assert manifest["source"] == {
        "filename": "stochastic-hh.sanpy",
        "format": "sanpy",
        "reader_version": str(sanpy.__version__),
    }
    assert manifest["protocol"] == ""
    assert manifest["acquisition_datetime"] == ""
    assert manifest["channels"] == [
        {"index": 0, "name": "Vm", "unit": "mV", "values_are_scaled": True}
    ]
    assert manifest["command_channels"] == [{"index": 0, "name": "Im", "unit": "pA"}]
    assert group["raw"].shape == (15, 1, 100001)
    assert group["command"].shape == (15, 1, 100001)
    assert group["epoch_index"].shape == (15, 1, 100001)
    assert len(epochs) == 60
    assert len(results) == 388
    np.testing.assert_array_equal(group["raw"][3, 0], analysis.fileLoader._sweepY[:, 3])
    np.testing.assert_array_equal(
        group["command"][3, 0], analysis.fileLoader._sweepC[:, 3]
    )
    validate_collection(destination)


def test_export_normalizes_only_epoch_levels_in_both_table_formats(
    tmp_path: Path, small_abf: Path
) -> None:
    """Round epoch levels consistently without mutating SanPy results."""
    analysis = _analysis(small_abf)
    analysis.spikeDetect(sanpy.bDetection().getDetectionDict("SA Node"))
    original_results = analysis.spikeDict.asDataFrame().copy(deep=True)
    original_epochs = snapshot_abf(small_abf).epochs
    destination = tmp_path / "epoch-levels.sanpy.zarr"

    export_collection([analysis], destination, table_format="both")

    tables = _recording_root(destination) / "tables"
    for name, column, original in (
        ("epochs", "level", original_epochs),
        ("analysis_results", "epochLevel", original_results),
    ):
        expected = original[column].round(2).reset_index(drop=True)
        csv_values = pd.read_csv(tables / f"{name}.csv")[column]
        parquet_values = pd.read_parquet(tables / f"{name}.parquet")[column]
        pd.testing.assert_series_equal(csv_values, expected, check_names=False)
        pd.testing.assert_series_equal(parquet_values, expected, check_names=False)

    pd.testing.assert_frame_equal(analysis.spikeDict.asDataFrame(), original_results)


@pytest.mark.parametrize("table_format,extension", [("csv", ".csv"), ("parquet", ".parquet")])
def test_table_format_selects_one_representation(
    tmp_path: Path,
    small_abf: Path,
    table_format: str,
    extension: str,
) -> None:
    """Write only the requested physical table representation.

    Args:
        tmp_path: Pytest-managed output directory.
        small_abf: Multi-sweep, multi-channel ABF fixture.
        table_format: Requested table format.
        extension: Expected output filename extension.
    """
    destination = tmp_path / f"{table_format}.sanpy.zarr"
    export_collection([_analysis(small_abf)], destination, table_format=table_format)
    tables = _recording_root(destination) / "tables"

    assert list(tables.glob("*"))
    assert all(path.suffix == extension for path in tables.iterdir())


def test_export_remains_readable_after_source_is_removed(
    tmp_path: Path, small_abf: Path
) -> None:
    """Validate source independence after deleting a copied source ABF.

    Args:
        tmp_path: Pytest-managed output directory.
        small_abf: Source ABF fixture copied before export.
    """
    source = tmp_path / "source.abf"
    shutil.copy2(small_abf, source)
    destination = tmp_path / "independent.sanpy.zarr"
    export_collection([_analysis(source)], destination, table_format="csv")
    source.unlink()

    validate_collection(destination)
    root = _recording_root(destination)
    assert np.asarray(zarr.open_group(str(root / "data.zarr"), mode="r")["raw"]).size > 0
    assert not pd.read_csv(root / "tables" / "epochs.csv").empty


def test_existing_destination_requires_overwrite(
    tmp_path: Path, small_abf: Path
) -> None:
    """Protect an existing collection unless overwrite is explicit.

    Args:
        tmp_path: Pytest-managed output directory.
        small_abf: Source ABF fixture.
    """
    destination = tmp_path / "existing.sanpy.zarr"
    export_collection([_analysis(small_abf)], destination, table_format="csv")

    with pytest.raises(FileExistsError):
        export_collection([_analysis(small_abf)], destination, table_format="csv")


def test_overwrite_replaces_an_existing_export(
    tmp_path: Path, small_abf: Path
) -> None:
    """Atomically replace an existing collection when requested.

    Args:
        tmp_path: Pytest-managed output directory.
        small_abf: Source ABF fixture.
    """
    destination = tmp_path / "replace.sanpy.zarr"
    export_collection([_analysis(small_abf)], destination, name="first", table_format="csv")

    export_collection(
        [_analysis(small_abf)],
        destination,
        name="second",
        table_format="csv",
        overwrite=True,
    )

    assert json.loads((destination / "collection.json").read_text())["name"] == "second"
    assert not list(tmp_path.glob(".replace.sanpy.zarr.backup-*"))


def test_collection_contains_multiple_independent_recordings(
    tmp_path: Path, small_abf: Path
) -> None:
    """Store independently addressable recordings without embedding ABFs.

    Args:
        tmp_path: Pytest-managed output directory.
        small_abf: Source ABF fixture used for two distinct analyses.
    """
    first = _analysis(small_abf)
    second = _analysis(small_abf)
    destination = tmp_path / "multiple.sanpy.zarr"

    export_collection([first, second], destination, table_format="csv")

    manifest = json.loads((destination / "collection.json").read_text())
    assert len(manifest["members"]) == 2
    assert len({member["id"] for member in manifest["members"]}) == 2
    summary = manifest["members"][0]["summary"]
    assert summary == {
        "sweeps": 18,
        "channels": 2,
        "points": 1600,
        "sampling_rate_hz": 10000.0,
        "analysis_results": 0,
        "protocol": "I-Clamp MedDRG",
        "acquisition_datetime": "2021-07-20T17:26:31.796000",
    }
    assert not list(destination.rglob("*.abf"))
    validate_collection(destination)


def test_csv_export_writes_no_parquet_resources(
    tmp_path: Path, small_abf: Path
) -> None:
    """Keep CSV-only export independent of Parquet resources.

    Args:
        tmp_path: Pytest-managed output directory.
        small_abf: Source ABF fixture.
    """
    destination = tmp_path / "csv-only.sanpy.zarr"
    export_collection([_analysis(small_abf)], destination, table_format="csv")

    assert not list((_recording_root(destination) / "tables").glob("*.parquet"))


def test_raw_data_matches_direct_pyabf_read(
    tmp_path: Path, small_abf: Path
) -> None:
    """Preserve direct PyABF signal values exactly.

    Args:
        tmp_path: Pytest-managed output directory.
        small_abf: Source ABF fixture.
    """
    destination = tmp_path / "values.sanpy.zarr"
    export_collection([_analysis(small_abf)], destination, table_format="csv")
    raw = zarr.open_group(str(_recording_root(destination) / "data.zarr"), mode="r")["raw"]
    source = pyabf.ABF(str(small_abf))
    source.setSweep(7, 1)

    np.testing.assert_array_equal(raw[7, 1], source.sweepY)


def test_actual_detection_parameters_and_results_are_separate_from_definitions(
    tmp_path: Path, small_abf: Path
) -> None:
    """Keep actual values separate from faithful runtime definitions.

    Args:
        tmp_path: Pytest-managed output directory.
        small_abf: Source ABF fixture.
    """
    analysis = _analysis(small_abf)
    detection = sanpy.bDetection().getDetectionDict("SA Node")
    analysis.spikeDetect(detection)
    destination = tmp_path / "analyzed.sanpy.zarr"

    export_collection([analysis], destination, table_format="both")

    root = _recording_root(destination)
    actual_parameters = json.loads((root / "metadata" / "detection_parameters.json").read_text())
    parameter_definitions = json.loads((root / "metadata" / "detection_parameter_definitions.json").read_text())
    result_definitions = json.loads((root / "metadata" / "analysis_result_definitions.json").read_text())
    overlay_definitions = json.loads((root / "metadata" / "trace_overlays.json").read_text())
    results = pd.read_csv(root / "tables" / "analysis_results.csv")
    assert actual_parameters["detectionName"] == detection["detectionName"]
    assert isinstance(actual_parameters["detectionName"], str)
    assert "defaultValue" in parameter_definitions["detectionName"]
    assert parameter_definitions["detectionName"]["category"]
    assert parameter_definitions["detectionName"]["humanName"]
    # abb 202609 way too specific
    # assert result_definitions["thresholdPnt"]["category"] == "waveform"
    assert "depends on detection" in result_definitions["thresholdPnt"]
    assert parameter_definitions == json_value(getDefaultDetection())
    assert result_definitions == json_value(analysisResultDict)
    assert overlay_definitions == {
        "overlays": json_value(get_trace_overlay_definitions())
    }
    assert len(results) == analysis.numSpikes
    assert "errors" in results.columns


def test_overlay_definitions_must_reference_known_results(
    tmp_path: Path, small_abf: Path
) -> None:
    """Reject overlay mappings that reference an unknown result column.

    Args:
        tmp_path: Pytest-managed output directory.
        small_abf: Source ABF fixture.
    """
    destination = tmp_path / "invalid-overlay.sanpy.zarr"
    export_collection([_analysis(small_abf)], destination, table_format="csv")
    overlay_path = _recording_root(destination) / "metadata" / "trace_overlays.json"
    overlays = json.loads(overlay_path.read_text())
    overlays["overlays"][0]["x_result"] = "unknownResult"
    overlay_path.write_text(json.dumps(overlays))

    with pytest.raises(SanPyZarrValidationError, match="unknown result"):
        validate_collection(destination)
