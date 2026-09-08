"""Public writer for self-contained SanPy Zarr collections."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import zarr

from .contract import DEFAULT_CHUNK_POINTS, FORMAT_NAME, FORMAT_VERSION, TABLE_FORMATS
from .json_codec import json_value
from .models import AcquisitionSnapshot, RecordingExport
from .pyabf_adapter import snapshot_abf
from .sanpy_adapter import snapshot_banalysis
from .table_writer import write_table
from .validator import validate_collection


_EPOCH_LEVEL_DECIMAL_PLACES = 2


def export_collection(
    analyses: Iterable[Any],
    destination: str | Path,
    *,
    name: str | None = None,
    table_format: str = "both",
    overwrite: bool = False,
    chunk_points: int = DEFAULT_CHUNK_POINTS,
) -> Path:
    """Export analyses into one self-contained SanPy Zarr collection.

    Args:
        analyses: ABF-backed SanPy ``bAnalysis`` instances to export.
        destination: Output directory ending in ``.sanpy.zarr``.
        name: Optional collection name. The destination name is used when
            omitted.
        table_format: One of ``"csv"``, ``"parquet"``, or ``"both"``.
        overwrite: Replace an existing destination when ``True``.
        chunk_points: Maximum number of points in each signal chunk.

    Returns:
        Absolute path to the completed collection.

    Raises:
        ValueError: If arguments are invalid or an analysis is not ABF-backed.
        FileExistsError: If the destination exists and overwrite is disabled.
        SanPyZarrValidationError: If the staged collection fails validation.
    """
    if table_format not in TABLE_FORMATS:
        raise ValueError(f"table_format must be one of {sorted(TABLE_FORMATS)}")
    if chunk_points <= 0:
        raise ValueError("chunk_points must be positive")
    members = tuple(analyses)
    if not members:
        raise ValueError("Cannot export an empty collection")
    target = Path(destination).expanduser().resolve(strict=False)
    if not target.name.lower().endswith(".sanpy.zarr"):
        raise ValueError("Destination must end in '.sanpy.zarr'")
    if target.exists() and not overwrite:
        raise FileExistsError(f"Destination already exists: {target}")

    snapshots = tuple(_snapshot(item) for item in members)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{target.name}.staging-", dir=target.parent) as tmp:
        staged = Path(tmp) / target.name
        staged.mkdir()
        _write_collection(staged, snapshots, name or _collection_name(target), table_format, chunk_points)
        validate_collection(staged)
        _install(staged, target, overwrite)
    return target


def _snapshot(analysis: Any) -> RecordingExport:
    """Create complete acquisition and SanPy snapshots for one analysis.

    Args:
        analysis: ABF-backed SanPy analysis instance.

    Returns:
        Complete recording export data.

    Raises:
        ValueError: If the analysis is not backed by an ABF file.
    """
    source_path = analysis.fileLoader.filepath
    if not source_path or Path(source_path).suffix.lower() != ".abf":
        raise ValueError("SanPy Zarr export currently requires an ABF-backed bAnalysis")
    return RecordingExport(snapshot_abf(source_path), snapshot_banalysis(analysis))


def _write_collection(
    root: Path,
    recordings: Sequence[RecordingExport],
    name: str,
    table_format: str,
    chunk_points: int,
) -> None:
    """Write collection and recording resources into a staging directory.

    Args:
        root: Staging collection root.
        recordings: Fully snapshotted recordings.
        name: Human-readable collection name.
        table_format: Requested table representation mode.
        chunk_points: Maximum signal chunk length.

    Raises:
        ValueError: If a recording identifier is unsafe or duplicated.
    """
    members = []
    used_ids = set()
    for recording in recordings:
        recording_id = recording.sanpy.recording_id
        if not re.fullmatch(r"[A-Za-z0-9._-]+", recording_id):
            raise ValueError(f"Unsafe SanPy recording ID: {recording_id!r}")
        if recording_id in used_ids:
            raise ValueError(f"Duplicate SanPy recording ID: {recording_id}")
        used_ids.add(recording_id)
        relative = Path("recordings") / recording_id
        _write_recording(root / relative, recording, table_format, chunk_points)
        acquisition = recording.acquisition
        members.append(
            {
                "id": recording_id,
                "name": acquisition.name,
                "recording": (relative / "recording.json").as_posix(),
                "summary": {
                    "sweeps": int(acquisition.raw.shape[0]),
                    "channels": int(acquisition.raw.shape[1]),
                    "points": int(acquisition.raw.shape[2]),
                    "sampling_rate_hz": acquisition.sample_rate_hz,
                    "analysis_results": len(recording.sanpy.analysis_results),
                    "protocol": acquisition.protocol,
                    "acquisition_datetime": acquisition.acquisition_datetime,
                },
            }
        )
    _write_json(
        root / "collection.json",
        {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "id": str(uuid.uuid4()),
            "name": name,
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "members": members,
        },
    )


def _write_recording(
    root: Path,
    recording: RecordingExport,
    table_format: str,
    chunk_points: int,
) -> None:
    """Write all resources for one recording.

    Args:
        root: Recording output directory.
        recording: Acquisition and SanPy snapshots.
        table_format: Requested table representation mode.
        chunk_points: Maximum signal chunk length.
    """
    root.mkdir(parents=True)
    metadata_root = root / "metadata"
    tables_root = root / "tables"
    metadata_root.mkdir()
    tables_root.mkdir()
    acquisition = recording.acquisition
    sanpy_state = recording.sanpy
    epoch_index = _epoch_index(acquisition)
    group = zarr.open_group(str(root / "data.zarr"), mode="w", zarr_format=3)
    _array(group, "time", acquisition.time, (min(len(acquisition.time), chunk_points),), ("point",), "s")
    signal_chunks = (1, 1, min(acquisition.raw.shape[2], chunk_points))
    _array(group, "raw", acquisition.raw, signal_chunks, ("sweep", "channel", "point"), None)
    _array(group, "command", acquisition.command, signal_chunks, ("sweep", "channel", "point"), None)
    _array(group, "epoch_index", epoch_index, signal_chunks, ("sweep", "channel", "point"), None)
    if sanpy_state.filtered is not None:
        _array(group, "filtered", sanpy_state.filtered, (1, min(sanpy_state.filtered.shape[1], chunk_points)), ("sweep", "point"), acquisition.channel_units[0])
    if sanpy_state.dvdt is not None:
        _array(group, "dvdt", sanpy_state.dvdt, (1, min(sanpy_state.dvdt.shape[1], chunk_points)), ("sweep", "point"), f"{acquisition.channel_units[0]}/ms")

    epoch_resource = write_table(
        _normalize_epoch_level(acquisition.epochs, "level"),
        tables_root / "epochs",
        table_format,
    )
    result_resource = write_table(
        _normalize_epoch_level(sanpy_state.analysis_results, "epochLevel"),
        tables_root / "analysis_results",
        table_format,
    )
    _write_json(metadata_root / "sanpy_metadata.json", sanpy_state.metadata)
    _write_json(metadata_root / "detection_parameters.json", sanpy_state.detection_parameters)
    _write_json(metadata_root / "detection_parameter_definitions.json", sanpy_state.detection_definitions)
    _write_json(metadata_root / "analysis_result_definitions.json", sanpy_state.result_definitions)
    _write_json(
        metadata_root / "trace_overlays.json",
        {"overlays": sanpy_state.trace_overlay_definitions},
    )
    _write_json(
        root / "recording.json",
        {
            "format": "sanpy-zarr-recording",
            "version": FORMAT_VERSION,
            "id": sanpy_state.recording_id,
            "name": acquisition.name,
            "dimensions": {
                "sweeps": int(acquisition.raw.shape[0]),
                "channels": int(acquisition.raw.shape[1]),
                "points": int(acquisition.raw.shape[2]),
            },
            "sampling_rate_hz": acquisition.sample_rate_hz,
            "protocol": acquisition.protocol,
            "acquisition_datetime": acquisition.acquisition_datetime,
            "channels": [
                {"index": index, "name": channel_name, "unit": acquisition.channel_units[index], "values_are_scaled": True}
                for index, channel_name in enumerate(acquisition.channel_names)
            ],
            "command_channels": [
                {"index": index, "name": channel_name, "unit": acquisition.command_units[index]}
                for index, channel_name in enumerate(acquisition.command_names)
            ],
            "analysis_channel": sanpy_state.analysis_channel,
            "source": {
                "filename": acquisition.name,
                "pyabf_version": acquisition.pyabf_version,
            },
            "export": {"sanpy_version": sanpy_state.sanpy_version},
            "resources": {
                "data": "data.zarr",
                "epochs": epoch_resource,
                "analysis_results": result_resource,
                "sanpy_metadata": "metadata/sanpy_metadata.json",
                "detection_parameters": "metadata/detection_parameters.json",
                "detection_parameter_definitions": "metadata/detection_parameter_definitions.json",
                "analysis_result_definitions": "metadata/analysis_result_definitions.json",
                "trace_overlays": "metadata/trace_overlays.json",
            },
        },
    )


def _normalize_epoch_level(table: Any, column: str) -> Any:
    """Round one exported epoch-level column without mutating its snapshot."""
    if column not in table.columns:
        return table
    normalized = table.copy(deep=True)
    normalized[column] = normalized[column].round(_EPOCH_LEVEL_DECIMAL_PLACES)
    return normalized


def _array(
    group: zarr.Group,
    name: str,
    data: np.ndarray,
    chunks: tuple[int, ...],
    dimensions: tuple[str, ...],
    unit: str | None,
) -> None:
    """Create one dimension-labeled Zarr array.

    Args:
        group: Destination Zarr group.
        name: Array name.
        data: Array values.
        chunks: Chunk shape.
        dimensions: Ordered semantic dimension names.
        unit: Optional uniform unit for the complete array.
    """
    array = group.create_array(
        name,
        data=np.asarray(data),
        chunks=chunks,
        dimension_names=dimensions,
    )
    if unit is not None:
        array.attrs["unit"] = unit


def _epoch_index(acquisition: AcquisitionSnapshot) -> np.ndarray:
    """Build a point-aligned epoch label array.

    Args:
        acquisition: Acquisition snapshot containing signal shapes and epochs.

    Returns:
        Integer labels arranged as sweep, channel, and point, with ``-1`` for
        points outside defined epochs.
    """
    labels = np.full(acquisition.raw.shape, -1, dtype=np.int32)
    for row in acquisition.epochs.itertuples(index=False):
        labels[row.sweep, row.channel, row.startPnt : row.stopPnt] = row.epoch
    return labels


def _write_json(path: Path, value: Any) -> None:
    """Write a runtime value as deterministic, strict JSON.

    Args:
        path: Destination JSON path.
        value: Runtime value to convert and serialize.
    """
    path.write_text(json.dumps(json_value(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _install(staged: Path, destination: Path, overwrite: bool) -> None:
    """Atomically install a validated staged collection.

    Args:
        staged: Validated staging directory.
        destination: Final collection path.
        overwrite: Whether an existing destination may be replaced.

    Raises:
        FileExistsError: If the destination exists and overwrite is disabled.
    """
    if not destination.exists():
        os.replace(staged, destination)
        return
    if not overwrite:
        raise FileExistsError(destination)
    backup = destination.with_name(f".{destination.name}.backup-{uuid.uuid4()}")
    os.replace(destination, backup)
    try:
        os.replace(staged, destination)
    except Exception:
        os.replace(backup, destination)
        raise
    shutil.rmtree(backup)


def _collection_name(path: Path) -> str:
    """Derive a default collection name from its directory name.

    Args:
        path: Collection directory path.

    Returns:
        Filename with the ``.sanpy.zarr`` suffix removed.
    """
    return path.name[: -len(".sanpy.zarr")]
