"""Declare runtime-owned mappings from analysis results to trace overlays."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TraceOverlayDefinition:
    """Describe one analysis-result overlay without prescribing GUI styling.

    Attributes:
        id: Stable machine-readable overlay identifier.
        label: Human-readable overlay label.
        x_result: Analysis-result column containing horizontal coordinates.
        y_result: Analysis-result column containing vertical coordinates.
        point_id_result: Analysis-result column identifying each point.
        sweep_result: Analysis-result column identifying the point's sweep.
    """

    id: str
    label: str
    x_result: str
    y_result: str
    point_id_result: str
    sweep_result: str


TRACE_OVERLAY_DEFINITIONS: tuple[TraceOverlayDefinition, ...] = (
    TraceOverlayDefinition(
        id="peaks",
        label="Peaks",
        x_result="peakSec",
        y_result="peakVal",
        point_id_result="spikeNumber",
        sweep_result="sweep",
    ),
    TraceOverlayDefinition(
        id="thresholds",
        label="Take-off potentials",
        x_result="thresholdSec",
        y_result="thresholdVal",
        point_id_result="spikeNumber",
        sweep_result="sweep",
    ),
)


def get_trace_overlay_definitions() -> tuple[TraceOverlayDefinition, ...]:
    """Return the immutable runtime trace-overlay definitions.

    Returns:
        Runtime-owned definitions in their preferred display order.
    """
    return TRACE_OVERLAY_DEFINITIONS
