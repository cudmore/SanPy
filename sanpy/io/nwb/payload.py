"""Define and apply the versioned SanPy JSON payload stored in NWB scratch."""

from __future__ import annotations

import math
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from sanpy.bAnalysisResults import AnalysisResults
from sanpy.bDetection import DetectionParameters
from sanpy.fileloaders.epochTable import Epoch, EpochLevelUnit, epochTable
from sanpy.metaData import MetaData

SANPY_PAYLOAD_NAME = "sanpy_analysis_payload_json"
"""NWB scratch key containing the authoritative SanPy payload."""
SANPY_PAYLOAD_FORMAT = "org.sanpy.nwb-analysis"
"""Stable identifier for the SanPy NWB extension payload."""
SANPY_PAYLOAD_VERSION = "1.0.0"
"""Current SanPy NWB payload version."""


class ExperimentalMetadataPayload(BaseModel):
    """Store canonical SanPy experimental metadata values."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    include: str = "yes"
    animal_id: str = ""
    species: str = ""
    region: str = ""
    cell_type: str = ""
    age: str = ""
    sex: str = "unknown"
    genotype: str = ""
    condition: str = ""
    experiment: str = ""
    note: str = ""


class SweepConditionPayload(BaseModel):
    """Store one user-assigned condition for a loaded sweep."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sweep: int
    condition: str


class EpochTablePayload(BaseModel):
    """Store canonical epochs and their shared command unit for one sweep."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sweep: int
    level_unit: EpochLevelUnit
    epochs: tuple[Epoch, ...]

    @model_validator(mode="after")
    def _validate_rows(self) -> EpochTablePayload:
        """Require ordered epoch rows to belong to this table's sweep.

        Returns:
            Validated table payload.

        Raises:
            ValueError: If rows use another sweep or noncontiguous indices.
        """
        if any(epoch.sweep_number != self.sweep for epoch in self.epochs):
            raise ValueError("Every epoch must belong to its table sweep")
        if [epoch.index for epoch in self.epochs] != list(range(len(self.epochs))):
            raise ValueError("Epoch indices must be contiguous and start at zero")
        return self


class SanpyNwbPayload(BaseModel):
    """Store all SanPy-owned state persisted inside one NWB recording."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    format: Literal["org.sanpy.nwb-analysis"] = SANPY_PAYLOAD_FORMAT
    version: Literal["1.0.0"] = SANPY_PAYLOAD_VERSION
    analysis_performed: bool
    detection_parameters: DetectionParameters | None = None
    experimental_metadata: ExperimentalMetadataPayload
    analysis_results: tuple[AnalysisResults, ...] = Field(default_factory=tuple)
    sweep_conditions: tuple[SweepConditionPayload, ...] = Field(default_factory=tuple)
    epoch_tables: tuple[EpochTablePayload, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _validate_analysis_state(self) -> SanpyNwbPayload:
        """Require analysis parameters and results to match analyzed state.

        Returns:
            Validated payload.

        Raises:
            ValueError: If unanalyzed state contains analysis-owned values.
        """
        if not self.analysis_performed:
            if self.detection_parameters is not None or self.analysis_results:
                raise ValueError(
                    "Unanalyzed payload cannot contain detection parameters or results"
                )
        elif self.detection_parameters is None:
            raise ValueError("Analyzed payload requires detection parameters")
        return self


def build_payload(analysis: Any) -> SanpyNwbPayload:
    """Snapshot validated SanPy-owned state from one loaded analysis.

    Args:
        analysis: Loaded ``bAnalysis`` instance to snapshot.

    Returns:
        Immutable validated payload ready for strict JSON serialization.

    Raises:
        ValueError: If analyzed state lacks valid detection parameters or epochs.
    """
    loader = analysis.fileLoader
    if loader is None:
        raise ValueError("Analysis has no loaded recording")
    analyzed = bool(analysis.isAnalyzed())
    detection = analysis.getDetectionDict()
    parameters = (
        DetectionParameters.model_validate(detection)
        if analyzed and detection is not None
        else None
    )
    results = tuple(
        AnalysisResults.model_validate(row) for row in analysis.spikeDict.asList()
    )
    conditions = tuple(
        SweepConditionPayload(
            sweep=int(sweep), condition=analysis.getSweepCondition(sweep)
        )
        for sweep in loader.sweepList
    )
    epoch_tables: list[EpochTablePayload] = []
    for sweep in loader.sweepList:
        table = loader.getEpochTable(sweep)
        if table is None:
            continue
        if table.level_unit is None:
            raise ValueError(f"Epoch table for sweep {sweep} has no level unit")
        rows = tuple(_epoch_from_runtime(row) for row in table.getEpochList())
        epoch_tables.append(
            EpochTablePayload(sweep=sweep, level_unit=table.level_unit, epochs=rows)
        )
    return SanpyNwbPayload(
        analysis_performed=analyzed,
        detection_parameters=parameters,
        experimental_metadata=ExperimentalMetadataPayload.model_validate(
            dict(analysis.metaData)
        ),
        analysis_results=results,
        sweep_conditions=conditions,
        epoch_tables=tuple(epoch_tables),
    )


def apply_payload(analysis: Any, payload: SanpyNwbPayload) -> None:
    """Atomically validate and apply one payload to a loaded analysis.

    Args:
        analysis: Loaded ``bAnalysis`` receiving persisted state.
        payload: Fully parsed SanPy NWB payload.

    Raises:
        ValueError: If payload references invalid sweeps, points, or clamp state.
    """
    loader = analysis.fileLoader
    if loader is None:
        raise ValueError("Analysis has no loaded recording")
    sweeps = set(loader.sweepList)
    _validate_payload_references(payload, sweeps, int(loader._sweepY.shape[0]))
    if loader.recordingMode.value == "V-Clamp" and (
        payload.analysis_performed
        or payload.detection_parameters is not None
        or payload.analysis_results
    ):
        raise ValueError("Voltage-clamp recordings cannot contain spike analysis")
    restored_tables: list[epochTable | None] = [None] * len(loader.sweepList)
    for saved in payload.epoch_tables:
        restored_tables[saved.sweep] = epochTable.from_epochs(
            saved.epochs,
            data_points_per_ms=float(loader.dataPointsPerMs),
            level_unit=saved.level_unit,
        )

    metadata = payload.experimental_metadata.model_dump(mode="python")
    result_rows = [result.model_dump(mode="python") for result in payload.analysis_results]
    detection = (
        None
        if payload.detection_parameters is None
        else payload.detection_parameters.model_dump(mode="json")
    )

    analysis.metaData.fromDict(metadata, triggerDirty=False)
    analysis._detectionDict = detection
    analysis.spikeDict.setFromListDict(result_rows)
    analysis._isAnalyzed = payload.analysis_performed
    for condition in payload.sweep_conditions:
        analysis.setSweepCondition(condition.sweep, condition.condition)
    analysis.clearSweepConditionsDirty()
    if payload.epoch_tables:
        loader._epochTableList = restored_tables
        loader._finalizeFileMetadata()
    if payload.analysis_performed:
        analysis.regenerateAnalysisDataFrame()
        analysis.dfError = analysis.getErrorReport()
    analysis._detectionDirty = False


def _epoch_from_runtime(row: dict[str, Any]) -> Epoch:
    """Convert one runtime epoch dictionary into a strict payload model.

    Args:
        row: Runtime epoch values from ``epochTable``.

    Returns:
        Validated canonical epoch.
    """
    digital_state = row.get("digitalState")
    if digital_state is not None:
        digital_state = tuple(int(value) for value in np.asarray(digital_state).tolist())
    return Epoch(
        sweep_number=int(row["sweepNumber"]),
        index=int(row["index"]),
        type=str(row["type"]),
        start_point=int(row["startPoint"]),
        stop_point=int(row["stopPoint"]),
        level=float(row["level"]),
        pulse_width=_optional_finite_float(row.get("pulseWidth")),
        pulse_period=_optional_finite_float(row.get("pulsePeriod")),
        digital_state=digital_state,
    )


def _optional_finite_float(value: Any) -> float | None:
    """Normalize an optional runtime scalar for strict JSON.

    Args:
        value: Candidate scalar value.

    Returns:
        Finite float or ``None`` for absent/nonfinite values.
    """
    if value is None:
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _validate_payload_references(
    payload: SanpyNwbPayload, sweeps: set[int], sample_count: int
) -> None:
    """Validate payload references against one decoded raw recording.

    Args:
        payload: Parsed payload to validate.
        sweeps: Available zero-based sweep indices.
        sample_count: Number of response points in each sweep.

    Raises:
        ValueError: If a result, condition, or epoch references invalid raw data.
    """
    if any(result.sweep not in sweeps for result in payload.analysis_results):
        raise ValueError("Analysis result references an unavailable sweep")
    condition_sweeps = [item.sweep for item in payload.sweep_conditions]
    if len(condition_sweeps) != len(set(condition_sweeps)):
        raise ValueError("Sweep conditions contain duplicate sweeps")
    if any(sweep not in sweeps for sweep in condition_sweeps):
        raise ValueError("Sweep condition references an unavailable sweep")
    table_sweeps = [table.sweep for table in payload.epoch_tables]
    if len(table_sweeps) != len(set(table_sweeps)):
        raise ValueError("Epoch payload contains duplicate sweep tables")
    if any(sweep not in sweeps for sweep in table_sweeps):
        raise ValueError("Epoch table references an unavailable sweep")
    for table in payload.epoch_tables:
        for epoch in table.epochs:
            if epoch.start_point < 0 or epoch.stop_point > sample_count:
                raise ValueError("Epoch point range exceeds its raw sweep")
