"""Define, validate, and store SanPy current-clamp spike results."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from copy import deepcopy
from datetime import datetime
from enum import StrEnum
import math
from numbers import Real
from typing import Any, TypeAlias

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from sanpy.bDetection import detectionTypes_
from sanpy.sanpyLogger import get_logger
from sanpy.schema import AnalysisResultCategory

logger = get_logger(__name__)
AnalysisResultValues: TypeAlias = dict[str, Any]
"""Mutable values used while calculating one spike result."""
HALF_HEIGHTS: tuple[int, int, int, int, int] = (10, 20, 50, 80, 90)
"""Fixed percentages used for action-potential width measurements."""


class AnalysisErrorCode(StrEnum):
    """Identify one stable category of spike-analysis diagnostic."""

    SPIKE_WIDTH = "spike_width"
    DVDT_PERCENT = "dvdt_percent"
    FAST_AHP_WINDOW = "fast_ahp_window"
    PRE_SPIKE_MIN_UNDERRUN = "pre_spike_min_underrun"
    PRE_SPIKE_MIN_ZERO = "pre_spike_min_zero"
    PRE_SPIKE_MIN = "pre_spike_min"
    EARLY_DIASTOLIC_FIT = "early_diastolic_fit"
    PRE_SPIKE_DVDT = "pre_spike_dvdt"
    CYCLE_LENGTH = "cycle_length"


class AnalysisError(BaseModel):
    """Describe one diagnostic attached to a completed spike result."""

    model_config = ConfigDict(
        extra="forbid", frozen=True, json_schema_extra={"additionalProperties": False}
    )

    code: AnalysisErrorCode
    message: str


def _field(
    default: Any = PydanticUndefined,
    *,
    title: str,
    description: str,
    category: AnalysisResultCategory,
    show: bool = False,
    categorical: bool = False,
    units: str = "",
    depends: str = "",
    error: str = "",
    factory: Callable[[], Any] | None = None,
) -> Any:
    """Create one result field with presentation metadata.

    Args:
        default: Default value, or Pydantic's sentinel for a required field.
        title: Human-readable label.
        description: Human-readable explanation.
        category: Presentation category.
        show: Whether statistic selectors show the result.
        categorical: Whether plots treat the result as categorical.
        units: Physical or logical units.
        depends: Detection parameters affecting the result.
        error: Documented error condition.
        factory: Optional factory for a fresh mutable default.

    Returns:
        A configured Pydantic field.
    """
    extra = {
        "x-category": category.value,
        "x-show-in-plot-menu": show,
        "x-is-categorical": categorical,
        "x-units": units,
        "x-depends-on-detection": depends,
        "x-error": error,
    }
    kwargs = {"title": title, "description": description, "json_schema_extra": extra}
    if factory is not None:
        return Field(default_factory=factory, **kwargs)
    return Field(default=default, **kwargs)


A = AnalysisResultCategory.ACQUISITION
D = AnalysisResultCategory.DETECTION
M = AnalysisResultCategory.METADATA
I = AnalysisResultCategory.IDENTITY
P = AnalysisResultCategory.PEAK_DETECTION
T = AnalysisResultCategory.TIMING
W = AnalysisResultCategory.WIDTHS


class AnalysisResults(BaseModel):
    """Validated completed measurements and annotations for one action potential."""

    model_config = ConfigDict(
        extra="forbid", frozen=True, json_schema_extra={"additionalProperties": False}
    )

    @field_validator("*", mode="before")
    @classmethod
    def _normalize_nonfinite_measurement(cls, value: Any) -> Any:
        """Convert nonfinite numeric measurements to missing values.

        Args:
            value: Candidate field value supplied by analysis calculations or
                persistence.

        Returns:
            ``None`` for nonfinite real numbers, otherwise the original value.
        """
        if isinstance(value, Real) and not isinstance(value, bool):
            return value if math.isfinite(float(value)) else None
        return value

    file: str = _field(
        "", title="File", description="Name of the analyzed raw-data file.", category=A
    )
    sweep: int = _field(
        title="Sweep",
        description="Zero-based analyzed sweep number.",
        category=A,
        show=True,
        categorical=True,
    )
    epoch: int | None = _field(
        None,
        title="Epoch",
        description="Zero-based stimulus epoch containing the spike.",
        category=A,
        show=True,
        categorical=True,
    )
    epochLevel: float | None = _field(
        None,
        title="Epoch level (pA)",
        description="DAC stimulus level during the spike.",
        category=A,
        show=True,
        categorical=True,
        units="pA",
    )
    detectionType: detectionTypes_ = _field(
        title="Detection type", description="Spike-detection algorithm.", category=D
    )
    dvdtThreshold: float | None = _field(
        None,
        title="dV/dt threshold (mV/ms)",
        description="Derivative threshold used for detection.",
        category=D,
        units="dvdt",
        depends="dvdtThreshold",
    )
    mvThreshold: float | None = _field(
        None,
        title="Voltage threshold (mV)",
        description="Membrane-potential detection threshold.",
        category=D,
        units="mV",
        depends="mvThreshold",
    )
    medianFilter: int | None = _field(
        0,
        title="Median filter",
        description="Median-filter width in points.",
        category=D,
        depends="medianFilter",
    )
    analysisDate: str = _field(
        "",
        title="Analysis date",
        description="Analysis date in YYYYMMDD format.",
        category=D,
    )
    analysisTime: str = _field(
        "",
        title="Analysis time",
        description="Analysis time in 24-hour HH:MM:SS format.",
        category=D,
    )
    modDate: str = _field(
        "",
        title="Modification date",
        description="Date of a post-detection edit.",
        category=D,
    )
    modTime: str = _field(
        "",
        title="Modification time",
        description="Time of a post-detection edit.",
        category=D,
    )
    sanpy_version: str = _field(
        "",
        title="Sanpy Version",
        description="SanPy version used for analysis.",
        category=D,
    )
    sanpy_git_commit: str = _field(
        "",
        title="Sanpy Git Commit",
        description="SanPy Git commit used for analysis.",
        category=D,
    )
    sanpy_git_dirty: bool | str = _field(
        "",
        title="Sanpy Git Dirty",
        description="Whether the checkout had changes.",
        category=D,
    )
    spike_include: str = _field(
        "yes",
        title="Spike included",
        description="Whether this spike is included.",
        category=M,
        show=True,
        categorical=True,
    )
    file_number: int = _field(
        0,
        title="File Number",
        description="File number used when pooling analyses.",
        category=M,
        show=True,
        categorical=True,
    )
    sweepCondition: str = _field(
        "",
        title="Sweep condition",
        description="User-assigned sweep condition.",
        category=I,
        show=True,
        categorical=True,
    )
    spikeNumber: int = _field(
        title="Spike number",
        description="Zero-based spike number across all sweeps.",
        category=I,
        show=True,
    )
    sweepSpikeNumber: int = _field(
        title="Sweep spike number",
        description="Zero-based spike number within the sweep.",
        category=I,
        show=True,
    )
    userType: int = _field(
        0,
        title="User type",
        description="User-assigned integer spike type.",
        category=I,
        show=True,
        categorical=True,
    )
    spike_condition: str = _field(
        "",
        title="Spike condition",
        description="User-assigned condition for this spike.",
        category=I,
        show=True,
        categorical=True,
    )
    errors: list[AnalysisError] = _field(
        title="Errors",
        description="Detection errors for this spike.",
        category=I,
        factory=list,
    )
    thresholdPnt: int = _field(
        title="Threshold point",
        description="Action-potential threshold point.",
        category=P,
        units="point",
    )
    thresholdSec: float | None = _field(
        None,
        title="Threshold time (s)",
        description="Action-potential threshold time.",
        category=P,
        show=True,
        units="sec",
    )
    thresholdVal: float | None = _field(
        None,
        title="Threshold voltage (mV)",
        description="Voltage at threshold.",
        category=P,
        show=True,
        units="mV",
    )
    thresholdVal_dvdt: float | None = _field(
        None,
        title="Threshold dV/dt (mV/ms)",
        description="dV/dt at threshold.",
        category=P,
        units="dvdt",
    )
    peakPnt: int = _field(
        title="Peak point",
        description="Action-potential peak point.",
        category=P,
        units="point",
        depends="(onlyPeaksAbove_mV, peakWindow_ms)",
    )
    peakSec: float | None = _field(
        None,
        title="Peak time (s)",
        description="Action-potential peak time.",
        category=P,
        units="sec",
    )
    peakVal: float | None = _field(
        None,
        title="Peak voltage (mV)",
        description="Voltage at the peak.",
        category=P,
        show=True,
        units="mV",
    )
    peakHeight: float | None = _field(
        None,
        title="Spike height (mV)",
        description="Peak voltage minus threshold voltage.",
        category=P,
        show=True,
        units="mV",
    )
    timeToPeak_ms: float | None = _field(
        None,
        title="Time to peak (ms)",
        description="Time from threshold to peak.",
        category=P,
        show=True,
        units="ms",
    )
    fastAhpPnt: int | None = _field(
        None,
        title="Fast AHP point",
        description="Fast afterhyperpolarization point.",
        category=P,
        units="point",
        depends="fastAhpWindow_ms",
    )
    fastAhpSec: float | None = _field(
        None,
        title="Fast AHP time (s)",
        description="Fast AHP time.",
        category=P,
        units="sec",
    )
    fastAhpValue: float | None = _field(
        None,
        title="Fast AHP voltage (mV)",
        description="Voltage at the fast AHP.",
        category=P,
        show=True,
        units="mV",
    )
    preMinPnt: int | None = _field(
        None,
        title="Pre-spike minimum point",
        description="Minimum point before the spike.",
        category=P,
        units="point",
        depends="mdp_ms",
    )
    preMinVal: float | None = _field(
        None,
        title="Pre-spike minimum voltage (mV)",
        description="Minimum voltage before the spike.",
        category=P,
        show=True,
        units="mV",
    )
    preLinearFitPnt0: int = _field(
        title="Early diastolic fit start point",
        description="Start point for the early-diastolic fit.",
        category=P,
        units="point",
    )
    preLinearFitPnt1: int = _field(
        title="Early diastolic fit end point",
        description="End point for the early-diastolic fit.",
        category=P,
        units="point",
    )
    earlyDiastolicDuration_ms: float | None = _field(
        None,
        title="Early diastolic duration (ms)",
        description="Duration of the early-diastolic fit.",
        category=P,
        show=True,
        units="ms",
    )
    preLinearFitVal0: float | None = _field(
        None,
        title="Early diastolic fit start voltage (mV)",
        description="Voltage at the fit start.",
        category=P,
        units="mV",
    )
    preLinearFitVal1: float | None = _field(
        None,
        title="Early diastolic fit end voltage (mV)",
        description="Voltage at the fit end.",
        category=P,
        units="mV",
    )
    earlyDiastolicDurationRate: float | None = _field(
        None,
        title="Early diastolic rate (mV/s)",
        description="Slope of the early-diastolic fit.",
        category=P,
        show=True,
        units="mV/s",
    )
    lateDiastolicDuration: float | None = _field(
        None,
        title="Late diastolic duration",
        description="Deprecated late-diastolic duration.",
        category=P,
    )
    preSpike_dvdt_max_pnt: int | None = _field(
        None,
        title="Pre-spike maximum dV/dt point",
        description="Point of maximum dV/dt before the peak.",
        category=P,
        units="point",
    )
    preSpike_dvdt_max_val: float | None = _field(
        None,
        title="Voltage at pre-spike maximum dV/dt (mV)",
        description="Voltage at maximum pre-spike dV/dt.",
        category=P,
        show=True,
        units="mV",
    )
    preSpike_dvdt_max_val2: float | None = _field(
        None,
        title="Pre-spike maximum dV/dt (mV/ms)",
        description="Maximum pre-spike dV/dt.",
        category=P,
        show=True,
        units="dV/dt",
    )
    postSpike_dvdt_min_pnt: int = _field(
        title="Post-spike minimum dV/dt point",
        description="Point of minimum dV/dt after the peak.",
        category=P,
        units="point",
        depends="dvdtPostWindow_ms",
    )
    postSpike_dvdt_min_val: float | None = _field(
        None,
        title="Voltage at post-spike minimum dV/dt (mV)",
        description="Voltage at minimum post-spike dV/dt.",
        category=P,
        show=True,
        units="mV",
    )
    postSpike_dvdt_min_val2: float | None = _field(
        None,
        title="Post-spike minimum dV/dt (mV/ms)",
        description="Minimum post-spike dV/dt.",
        category=P,
        units="dV/dt",
    )
    isi_pnts: int | None = _field(
        None,
        title="Interspike interval (points)",
        description="Points since the previous threshold.",
        category=T,
        units="point",
        depends="refractory_ms",
    )
    isi_ms: float | None = _field(
        None,
        title="Interspike interval (ms)",
        description="Time since the previous threshold.",
        category=T,
        show=True,
        units="ms",
    )
    spikeFreq_hz: float | None = _field(
        None,
        title="Spike frequency (Hz)",
        description="Instantaneous frequency from the previous spike.",
        category=T,
        show=True,
        units="Hz",
    )
    cycleLength_pnts: int | None = _field(
        None,
        title="Cycle length (points)",
        description="Points between successive pre-spike minima.",
        category=T,
        units="point",
    )
    cycleLength_ms: float | None = _field(
        None,
        title="Cycle length (ms)",
        description="Time between successive pre-spike minima.",
        category=T,
        show=True,
        units="ms",
    )
    diastolicDuration_ms: float | None = _field(
        None,
        title="Diastolic duration (ms)",
        description="Time from pre-spike minimum to threshold.",
        category=T,
        show=True,
        units="ms",
    )
    width_10_ms: float | None = _field(
        None,
        title="Spike width at 10% (ms)",
        description="Width at 10 percent of spike height.",
        category=W,
        show=True,
        units="ms",
        depends="halfWidthWindow_ms",
    )
    width_10_rising_pnt: int | None = _field(
        None,
        title="Spike width 10% rising point",
        description="Rising-phase crossing point at 10 percent of spike height.",
        category=W,
        units="point",
        depends="halfWidthWindow_ms",
    )
    width_10_falling_pnt: int | None = _field(
        None,
        title="Spike width 10% falling point",
        description="Falling-phase crossing point at 10 percent of spike height.",
        category=W,
        units="point",
        depends="halfWidthWindow_ms",
    )
    width_20_ms: float | None = _field(
        None,
        title="Spike width at 20% (ms)",
        description="Width at 20 percent of spike height.",
        category=W,
        show=True,
        units="ms",
        depends="halfWidthWindow_ms",
    )
    width_20_rising_pnt: int | None = _field(
        None,
        title="Spike width 20% rising point",
        description="Rising-phase crossing point at 20 percent of spike height.",
        category=W,
        units="point",
        depends="halfWidthWindow_ms",
    )
    width_20_falling_pnt: int | None = _field(
        None,
        title="Spike width 20% falling point",
        description="Falling-phase crossing point at 20 percent of spike height.",
        category=W,
        units="point",
        depends="halfWidthWindow_ms",
    )
    width_50_ms: float | None = _field(
        None,
        title="Spike width at 50% (ms)",
        description="Width at 50 percent of spike height.",
        category=W,
        show=True,
        units="ms",
        depends="halfWidthWindow_ms",
    )
    width_50_rising_pnt: int | None = _field(
        None,
        title="Spike width 50% rising point",
        description="Rising-phase crossing point at 50 percent of spike height.",
        category=W,
        units="point",
        depends="halfWidthWindow_ms",
    )
    width_50_falling_pnt: int | None = _field(
        None,
        title="Spike width 50% falling point",
        description="Falling-phase crossing point at 50 percent of spike height.",
        category=W,
        units="point",
        depends="halfWidthWindow_ms",
    )
    width_80_ms: float | None = _field(
        None,
        title="Spike width at 80% (ms)",
        description="Width at 80 percent of spike height.",
        category=W,
        show=True,
        units="ms",
        depends="halfWidthWindow_ms",
    )
    width_80_rising_pnt: int | None = _field(
        None,
        title="Spike width 80% rising point",
        description="Rising-phase crossing point at 80 percent of spike height.",
        category=W,
        units="point",
        depends="halfWidthWindow_ms",
    )
    width_80_falling_pnt: int | None = _field(
        None,
        title="Spike width 80% falling point",
        description="Falling-phase crossing point at 80 percent of spike height.",
        category=W,
        units="point",
        depends="halfWidthWindow_ms",
    )
    width_90_ms: float | None = _field(
        None,
        title="Spike width at 90% (ms)",
        description="Width at 90 percent of spike height.",
        category=W,
        show=True,
        units="ms",
        depends="halfWidthWindow_ms",
    )
    width_90_rising_pnt: int | None = _field(
        None,
        title="Spike width 90% rising point",
        description="Rising-phase crossing point at 90 percent of spike height.",
        category=W,
        units="point",
        depends="halfWidthWindow_ms",
    )
    width_90_falling_pnt: int | None = _field(
        None,
        title="Spike width 90% falling point",
        description="Falling-phase crossing point at 90 percent of spike height.",
        category=W,
        units="point",
        depends="halfWidthWindow_ms",
    )


def new_result_values() -> AnalysisResultValues:
    """Create independent defaults for an in-progress spike calculation.

    Returns:
        Defaults for every non-required result field.
    """
    return {
        name: field.get_default(call_default_factory=True)
        for name, field in AnalysisResults.model_fields.items()
        if not field.is_required()
    }


def _definition(name: str, field: FieldInfo) -> dict[str, Any]:
    """Convert one model field to the established metadata shape.

    Args:
        name: Internal result name.
        field: Pydantic field metadata.

    Returns:
        A detached compatibility definition.
    """
    extra = field.json_schema_extra or {}
    default = (
        None if field.is_required() else field.get_default(call_default_factory=True)
    )
    annotation = field.annotation
    return {
        "category": AnalysisResultCategory(extra["x-category"]),
        "axis_label": field.title or name,
        "show_in_plot_menu": extra["x-show-in-plot-menu"],
        "is_categorical": extra["x-is-categorical"],
        "type": getattr(annotation, "__name__", str(annotation)),
        "default": deepcopy(default),
        "units": extra["x-units"],
        "depends on detection": extra["x-depends-on-detection"],
        "error": extra["x-error"],
        "description": field.description or "",
    }


def get_analysis_result_definitions() -> dict[str, dict[str, Any]]:
    """Return ordered result metadata derived from the model.

    Returns:
        Detached result definitions keyed by storage name.
    """
    return {
        name: _definition(name, field)
        for name, field in AnalysisResults.model_fields.items()
    }


def get_plot_result_definitions() -> dict[str, dict[str, Any]]:
    """Return result definitions shown in statistic selectors.

    Returns:
        Ordered plottable definitions keyed by storage name.
    """
    return {
        name: value
        for name, value in get_analysis_result_definitions().items()
        if value["show_in_plot_menu"]
    }


def printDocs() -> None:
    """Print the result schema as an HTML table."""
    rows = [
        {"Name": name, **value}
        for name, value in get_analysis_result_definitions().items()
    ]
    from sanpy.sanpy_version import getSanPyProvenance

    provenance = getSanPyProvenance()
    date = datetime.today().strftime("%Y-%m-%d")
    print(f"Generated {date} with SanPy version {provenance.version}")
    print(pd.DataFrame(rows).to_html())


class analysisResultList:
    """Store dictionary-compatible spike results in detection order."""

    def __init__(self) -> None:
        """Create an empty collection."""
        self._myList: list[AnalysisResultValues] = []

    def setFromListDict(self, listOfDict: list[dict[str, Any]]) -> None:
        """Load saved rows while logging and skipping unknown fields.

        Args:
            listOfDict: Persisted spike-result dictionaries.
        """
        self._myList = []
        for saved in listOfDict:
            values = new_result_values()
            for name, value in saved.items():
                if name not in AnalysisResults.model_fields:
                    logger.error(f'Ignoring unknown saved analysis-result key "{name}"')
                    continue
                values[name] = value
            self._myList.append(values)

    def extend_completed(self, results: Iterable[AnalysisResults]) -> None:
        """Append validated completed results.

        Args:
            results: Completed spike models to serialize and append.
        """
        self._myList.extend(result.model_dump(mode="python") for result in results)

    def append_result(self, values: Mapping[str, Any]) -> None:
        """Append a partial compatibility row, logging unknown fields.

        Args:
            values: Partial or complete result values.
        """
        result = new_result_values()
        for name, value in values.items():
            if name not in AnalysisResults.model_fields:
                logger.error(f'Ignoring unknown analysis-result key "{name}"')
                continue
            result[name] = value
        self._myList.append(result)

    def analysisDate(self) -> str | None:
        """Return the first analysis date, if present.

        Returns:
            First analysis date or ``None``.
        """
        return self._myList[0]["analysisDate"] if self._myList else None

    def analysisTime(self) -> str | None:
        """Return the first analysis time, if present.

        Returns:
            First analysis time or ``None``.
        """
        return self._myList[0]["analysisTime"] if self._myList else None

    def asList(self) -> list[AnalysisResultValues]:
        """Return independent result dictionaries.

        Returns:
            A deep copy of stored rows.
        """
        return deepcopy(self._myList)

    def asDataFrame(self) -> pd.DataFrame:
        """Return one DataFrame row per spike.

        Returns:
            Result DataFrame in model-field order.
        """
        return pd.DataFrame(self.asList(), columns=AnalysisResults.model_fields)

    def __getitem__(self, key: int) -> AnalysisResultValues:
        """Return one mutable stored result.

        Args:
            key: Zero-based row index.

        Returns:
            Stored result dictionary.
        """
        return self._myList[key]

    def __delitem__(self, key: int) -> None:
        """Delete one stored result.

        Args:
            key: Zero-based row index.
        """
        del self._myList[key]

    def __len__(self) -> int:
        """Return the number of rows.

        Returns:
            Number of stored results.
        """
        return len(self._myList)

    def __iter__(self) -> Iterator[AnalysisResultValues]:
        """Iterate over mutable result dictionaries.

        Returns:
            Iterator over stored rows.
        """
        return iter(self._myList)


if __name__ == "__main__":
    printDocs()
