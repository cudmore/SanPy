import json
import shutil

import numpy as np
import pandas as pd
import pyabf
import pytest
import zarr

import sanpy
from sanpy.io.zarr_export.exporter import export_collection
from sanpy.io.zarr_export.validator import validate_collection


def _analysis(path):
    return sanpy.bAnalysis(str(path))


def _recording_root(export):
    collection = json.loads((export / "collection.json").read_text())
    return export / collection["members"][0]["recording"].rsplit("/", 1)[0]


def test_export_is_zarr3_and_preserves_runtime_state(tmp_path, small_abf):
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


@pytest.mark.parametrize("table_format,extension", [("csv", ".csv"), ("parquet", ".parquet")])
def test_table_format_selects_one_representation(tmp_path, small_abf, table_format, extension):
    destination = tmp_path / f"{table_format}.sanpy.zarr"
    export_collection([_analysis(small_abf)], destination, table_format=table_format)
    tables = _recording_root(destination) / "tables"

    assert list(tables.glob("*"))
    assert all(path.suffix == extension for path in tables.iterdir())


def test_export_remains_readable_after_source_is_removed(tmp_path, small_abf):
    source = tmp_path / "source.abf"
    shutil.copy2(small_abf, source)
    destination = tmp_path / "independent.sanpy.zarr"
    export_collection([_analysis(source)], destination, table_format="csv")
    source.unlink()

    validate_collection(destination)
    root = _recording_root(destination)
    assert np.asarray(zarr.open_group(str(root / "data.zarr"), mode="r")["raw"]).size > 0
    assert not pd.read_csv(root / "tables" / "epochs.csv").empty


def test_existing_destination_requires_overwrite(tmp_path, small_abf):
    destination = tmp_path / "existing.sanpy.zarr"
    export_collection([_analysis(small_abf)], destination, table_format="csv")

    with pytest.raises(FileExistsError):
        export_collection([_analysis(small_abf)], destination, table_format="csv")


def test_overwrite_replaces_an_existing_export(tmp_path, small_abf):
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


def test_collection_contains_multiple_independent_recordings(tmp_path, small_abf):
    first = _analysis(small_abf)
    second = _analysis(small_abf)
    destination = tmp_path / "multiple.sanpy.zarr"

    export_collection([first, second], destination, table_format="csv")

    manifest = json.loads((destination / "collection.json").read_text())
    assert len(manifest["members"]) == 2
    assert len({member["id"] for member in manifest["members"]}) == 2
    assert not list(destination.rglob("*.abf"))
    validate_collection(destination)


def test_csv_export_writes_no_parquet_resources(tmp_path, small_abf):
    destination = tmp_path / "csv-only.sanpy.zarr"
    export_collection([_analysis(small_abf)], destination, table_format="csv")

    assert not list((_recording_root(destination) / "tables").glob("*.parquet"))


def test_raw_data_matches_direct_pyabf_read(tmp_path, small_abf):
    destination = tmp_path / "values.sanpy.zarr"
    export_collection([_analysis(small_abf)], destination, table_format="csv")
    raw = zarr.open_group(str(_recording_root(destination) / "data.zarr"), mode="r")["raw"]
    source = pyabf.ABF(str(small_abf))
    source.setSweep(7, 1)

    np.testing.assert_array_equal(raw[7, 1], source.sweepY)


def test_actual_detection_parameters_and_results_are_separate_from_definitions(tmp_path, small_abf):
    analysis = _analysis(small_abf)
    detection = sanpy.bDetection().getDetectionDict("SA Node")
    analysis.spikeDetect(detection)
    destination = tmp_path / "analyzed.sanpy.zarr"

    export_collection([analysis], destination, table_format="both")

    root = _recording_root(destination)
    actual_parameters = json.loads((root / "metadata" / "detection_parameters.json").read_text())
    parameter_definitions = json.loads((root / "metadata" / "detection_parameter_definitions.json").read_text())
    result_definitions = json.loads((root / "metadata" / "analysis_result_definitions.json").read_text())
    results = pd.read_csv(root / "tables" / "analysis_results.csv")
    assert actual_parameters["detectionName"] == detection["detectionName"]
    assert isinstance(actual_parameters["detectionName"], str)
    assert "default" in parameter_definitions["detectionName"]
    assert parameter_definitions["detectionName"]["category"]
    assert result_definitions["thresholdPnt"]["category"] == "threshold"
    assert len(results) == analysis.numSpikes
    assert "errors" in results.columns
