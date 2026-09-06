"""Structural and cross-resource validation for SanPy Zarr collections."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

import pandas as pd
import numpy as np
import zarr
from jsonschema import Draft202012Validator

from .contract import FORMAT_NAME, FORMAT_VERSION


class SanPyZarrValidationError(ValueError):
    pass


def validate_collection(root: str | Path) -> None:
    collection_root = Path(root).expanduser().resolve(strict=True)
    collection = _json(collection_root / "collection.json")
    _schema(collection, "collection-v1.schema.json")
    if collection.get("format") != FORMAT_NAME or collection.get("version") != FORMAT_VERSION:
        raise SanPyZarrValidationError("Unsupported SanPy Zarr collection format")
    members = collection.get("members")
    if not isinstance(members, list) or not members:
        raise SanPyZarrValidationError("Collection must contain recordings")
    ids = [item.get("id") for item in members]
    if len(ids) != len(set(ids)):
        raise SanPyZarrValidationError("Collection contains duplicate recording IDs")
    for member in members:
        path = _resource(collection_root, member["recording"])
        _validate_recording(collection_root, member, _json(path))


def _validate_recording(root, member, recording) -> None:
    _schema(recording, "recording-v1.schema.json")
    if recording.get("id") != member.get("id"):
        raise SanPyZarrValidationError("Recording identity mismatch")
    dimensions = recording["dimensions"]
    expected = (dimensions["sweeps"], dimensions["channels"], dimensions["points"])
    recording_root = _resource(root, member["recording"]).parent
    group = zarr.open_group(str(_resource(recording_root, recording["resources"]["data"])), mode="r")
    _shape(group, "time", (dimensions["points"],))
    _dimensions(group, "time", ("point",))
    for name in ("raw", "command", "epoch_index"):
        _shape(group, name, expected)
        _dimensions(group, name, ("sweep", "channel", "point"))
    for name in ("filtered", "dvdt"):
        if name in group:
            _shape(group, name, (dimensions["sweeps"], dimensions["points"]))
            _dimensions(group, name, ("sweep", "point"))
    if group.metadata.zarr_format != 3:
        raise SanPyZarrValidationError("data.zarr is not Zarr format 3")
    if len(recording["channels"]) != dimensions["channels"]:
        raise SanPyZarrValidationError("Recorded channel metadata count mismatch")
    if len(recording["command_channels"]) != dimensions["channels"]:
        raise SanPyZarrValidationError("Command channel metadata count mismatch")
    if recording["analysis_channel"] >= dimensions["channels"]:
        raise SanPyZarrValidationError("Analysis channel is out of bounds")
    for key in ("sanpy_metadata", "detection_parameters", "detection_parameter_definitions", "analysis_result_definitions"):
        _json(_resource(recording_root, recording["resources"][key]))
    for key in ("epochs", "analysis_results"):
        _validate_table(recording_root, recording["resources"][key])
    if member["summary"]["analysis_results"] != recording["resources"]["analysis_results"]["rows"]:
        raise SanPyZarrValidationError("Analysis result row count mismatch")


def _validate_table(root: Path, resource: dict) -> None:
    frames = {}
    for kind, relative in resource["representations"].items():
        path = _resource(root / "tables", relative)
        frames[kind] = (
            pd.read_csv(path, keep_default_na=False)
            if kind == "csv"
            else pd.read_parquet(path)
        )
    if not frames:
        raise SanPyZarrValidationError("Table has no representation")
    for frame in frames.values():
        if len(frame) != resource["rows"]:
            raise SanPyZarrValidationError("Table row count mismatch")
    if len(frames) == 2:
        csv = frames["csv"]
        parquet = frames["parquet"]
        if list(csv.columns) != list(parquet.columns) or csv.shape != parquet.shape:
            raise SanPyZarrValidationError("CSV and Parquet table structures differ")
        if not _equivalent_values(csv, parquet):
            raise SanPyZarrValidationError("CSV and Parquet table values differ")


def _equivalent_values(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    for column in left.columns:
        left_values = left[column].map(_comparison_cell)
        right_values = right[column].map(_comparison_cell)
        left_null = left_values == "<null>"
        right_null = right_values == "<null>"
        if not left_null.equals(right_null):
            return False
        present = ~left_null
        if not present.any():
            continue
        try:
            left_numeric = pd.to_numeric(left_values[present], errors="raise")
            right_numeric = pd.to_numeric(right_values[present], errors="raise")
        except (TypeError, ValueError):
            if not left_values[present].astype(str).equals(right_values[present].astype(str)):
                return False
        else:
            if not np.allclose(
                left_numeric, right_numeric, rtol=1e-14, atol=1e-15, equal_nan=True
            ):
                return False
    return True


def _comparison_cell(value):
    if pd.isna(value) or value == "null":
        return "<null>"
    return value


def _shape(group, name, expected) -> None:
    if name not in group or tuple(group[name].shape) != expected:
        raise SanPyZarrValidationError(f"Zarr array {name!r} shape mismatch")


def _dimensions(group, name, expected) -> None:
    if tuple(group[name].metadata.dimension_names or ()) != expected:
        raise SanPyZarrValidationError(f"Zarr array {name!r} dimensions mismatch")


def _resource(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative:
        raise SanPyZarrValidationError(f"Unsafe resource path: {relative}")
    resolved = root / path
    if not resolved.exists():
        raise SanPyZarrValidationError(f"Missing resource: {relative}")
    return resolved


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SanPyZarrValidationError(f"Invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise SanPyZarrValidationError(f"Expected JSON object: {path}")
    return value


def _schema(value: dict, filename: str) -> None:
    schema_path = files("sanpy.io.zarr_export.schemas").joinpath(filename)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.path))
    if errors:
        raise SanPyZarrValidationError(f"Schema validation failed: {errors[0].message}")
