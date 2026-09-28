"""Immutable metadata describing a loaded recording file."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any


@dataclass(frozen=True, slots=True)
class FileMetadata:
    """File-derived acquisition facts shared by loaders and consumers.

    Attributes:
        acq_date: Acquisition date formatted as ``YYYY-MM-DD`` when available.
        acq_time: Acquisition time formatted as ``HH:MM:SS`` when available.
        acq_datetime: Complete acquisition timestamp when available.
        num_channels: Number of recorded channels in the source file.
        num_sweeps: Number of loaded sweeps.
        num_epochs: Validated number of epochs per sweep, or ``None``.
        sweep_label_x: Label for the sweep X axis.
        sweep_label_y: Label for the sweep Y axis.
        mode: Human-readable recording mode.
        recording_frequency_khz: Sampling frequency in kilohertz.
        user_list: Optional ABF user-list values.
    """

    acq_date: str = field(metadata={"display_name": "Acquisition Date"})
    acq_time: str = field(metadata={"display_name": "Acquisition Time"})
    acq_datetime: str = field(
        metadata={"display_name": "Acquisition Date and Time"}
    )
    num_channels: int = field(metadata={"display_name": "Number of Channels"})
    num_sweeps: int = field(metadata={"display_name": "Number of Sweeps"})
    num_epochs: int | None = field(metadata={"display_name": "Epochs per Sweep"})
    sweep_label_x: str = field(metadata={"display_name": "X-Axis Label"})
    sweep_label_y: str = field(metadata={"display_name": "Y-Axis Label"})
    mode: str = field(metadata={"display_name": "Recording Mode"})
    recording_frequency_khz: float = field(
        metadata={"display_name": "Recording Frequency (kHz)"}
    )
    user_list: tuple[float, ...] | None = field(
        metadata={"display_name": "ABF User List"}
    )


def get_file_metadata_definitions() -> dict[str, dict[str, Any]]:
    """Return portable presentation definitions for file metadata.

    Returns:
        Definitions keyed by canonical file-metadata field name.
    """
    return {
        metadata_field.name: {
            "display_name": str(
                metadata_field.metadata.get("display_name", metadata_field.name)
            )
        }
        for metadata_field in fields(FileMetadata)
    }
