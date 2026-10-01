"""Typed state shared by the SanPy analysis window and interactive plugins."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowState:
    """Describe the recording, sweep, and spikes selected in one window.

    Attributes:
        file_key: Normalized path relative to the owning analysis directory.
        sweep: Zero-based sweep displayed by the main analysis window.
        spike_selection: Absolute spike numbers, or ``None`` when none are selected.
    """

    file_key: str
    sweep: int
    spike_selection: tuple[int, ...] | None = None
