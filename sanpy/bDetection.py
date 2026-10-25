"""Manage SanPy spike-detection parameters and presets."""

from __future__ import annotations

import glob
import json
import os
import pathlib
from enum import Enum
from typing import Any, Mapping, Self

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from sanpy.sanpyLogger import get_logger
from sanpy.sanpy_paths import SanPyPaths
from sanpy.schema import DetectionParameterCategory

logger = get_logger(__name__)


class detectionTypes_(Enum):
    """Available spike-detection algorithms."""

    dvdt = "dvdt"
    mv = "mv"


def _field(
    default: Any,
    *,
    title: str,
    description: str,
    category: DetectionParameterCategory,
    show_in_editor: bool = True,
    units: str = "",
) -> Any:
    """Build one detection-parameter field with presentation metadata.

    Args:
        default: Default parameter value.
        title: Human-readable parameter name.
        description: Human-readable parameter description.
        category: Editor and documentation category.
        show_in_editor: Whether the Qt editor should display the parameter.
        units: Display units, or an empty string when dimensionless.

    Returns:
        A configured Pydantic field definition.
    """
    return Field(
        default=default,
        title=title,
        description=description,
        json_schema_extra={
            "x-category": category.value,
            "x-show-in-editor": show_in_editor,
            "x-units": units,
        },
    )


class DetectionParameters(BaseModel):
    """Validated spike-detection parameter values."""

    model_config = ConfigDict(
        extra="forbid", frozen=True, json_schema_extra={"additionalProperties": False}
    )

    detectionName: str = _field(
        "default",
        title="Detection Preset",
        description="The name of detection preset",
        category=DetectionParameterCategory.PRESETS,
    )
    userSaveName: str = _field(
        "",
        title="Save User Name",
        description="The name of saved user detection params",
        category=DetectionParameterCategory.PRESETS,
    )
    detectionType: detectionTypes_ = _field(
        detectionTypes_.dvdt,
        title="Detection Type",
        description="Detect using derivative (dvdt) or membrane potential (mV)",
        category=DetectionParameterCategory.DETECTION,
    )
    dvdtThreshold: float | None = _field(
        20,
        title="dV/dt Threshold",
        description="Minimum dV/dt used to detect a spike threshold",
        category=DetectionParameterCategory.DETECTION,
        units="mV/ms",
    )
    mvThreshold: float = _field(
        -20,
        title="mV Threshold",
        description="mV threshold for spike AND minimum spike mV when detecting with dV/dt",
        category=DetectionParameterCategory.DETECTION,
        units="mV",
    )
    startSeconds: float | None = _field(
        None,
        title="Start(s)",
        description="Start seconds of analysis, set from the visible x-range when detecting",
        category=DetectionParameterCategory.WINDOWS,
        show_in_editor=False,
        units="s",
    )
    stopSeconds: float | None = _field(
        None,
        title="Stop(s)",
        description="Stop seconds of analysis, set from the visible x-range when detecting",
        category=DetectionParameterCategory.WINDOWS,
        show_in_editor=False,
        units="s",
    )
    dvdt_percentOfMax: float = _field(
        0.1,
        title="dV/dt Percent of max",
        description="For dV/dt detection, the final TOP is when dV/dt drops to this percent from dV/dt AP peak",
        category=DetectionParameterCategory.DETECTION,
        units="Percent",
    )
    onlyPeaksAbove_mV: float | None = _field(
        None,
        title="Accept Peaks Above (mV)",
        description="Only accept APs with peaks above this value (mV)",
        category=DetectionParameterCategory.WAVEFORM,
        units="mV",
    )
    onlyPeaksBelow_mV: float | None = _field(
        None,
        title="Accept Peaks Below (mV)",
        description="Only accept APs below this value (mV)",
        category=DetectionParameterCategory.WAVEFORM,
        units="mV",
    )
    doBackupSpikeVm: bool = _field(
        False,
        title="Backup Vm Spikes",
        description="If true, APs detected with just mV will be backed up until Vm falls to xxx",
        category=DetectionParameterCategory.ADVANCED,
        units="Boolean",
    )
    refractory_ms: float = _field(
        170,
        title="Minimum AP interval (ms)",
        description="APs with interval (wrt previous AP) less than this will be removed",
        category=DetectionParameterCategory.WINDOWS,
        units="ms",
    )
    peakWindow_ms: float = _field(
        100,
        title="Peak Window (ms)",
        description="Window after TOP (ms) to seach for AP peak (mV)",
        category=DetectionParameterCategory.WINDOWS,
        units="ms",
    )
    dvdtPreWindow_ms: float = _field(
        10,
        title="dV/dt Pre Window (ms)",
        description="Window (ms) to search before each TOP for real threshold crossing",
        category=DetectionParameterCategory.WINDOWS,
        units="ms",
    )
    dvdtPostWindow_ms: float = _field(
        20,
        title="dV/dt Post Window (ms)",
        description="Window (ms) to search after each AP peak for minimum in dv/dt",
        category=DetectionParameterCategory.WINDOWS,
        units="ms",
    )
    mdp_ms: float = _field(
        250,
        title="Pre AP MDP window (ms)",
        description="Window (ms) before an AP to look for MDP",
        category=DetectionParameterCategory.WINDOWS,
        units="ms",
    )
    avgWindow_ms: float = _field(
        5,
        title="MDP averaging window (ms)",
        description="Window (ms) to calculate MDP (mV) as a mean rather than mV at single point for MDP",
        category=DetectionParameterCategory.WINDOWS,
        units="ms",
    )
    lowEddRate_warning: float = _field(
        8,
        title="EDD slope warning",
        description="Generate warning when EED slope is lower than this value.",
        category=DetectionParameterCategory.ADVANCED,
        units="EDD slope",
    )
    halfWidthWindow_ms: float = _field(
        200,
        title="Half Width Window (ms)",
        description="Window (ms) after TOP to look for AP widths",
        category=DetectionParameterCategory.WINDOWS,
        units="ms",
    )
    preSpikeClipWidth_ms: float = _field(
        4,
        title="Pre AP Clip Width (ms)",
        description="The pre duration of generated AP clips (Before AP)",
        category=DetectionParameterCategory.SPIKE_CLIPS,
        units="ms",
    )
    postSpikeClipWidth_ms: float = _field(
        8,
        title="Post AP Clip Width (ms)",
        description="The post duration of generated AP clips (After AP)",
        category=DetectionParameterCategory.SPIKE_CLIPS,
        units="ms",
    )
    fastAhpWindow_ms: float = _field(
        8,
        title="Fast AHP Window (ms)",
        description="Window (ms) after peak to look for a fast AHP",
        category=DetectionParameterCategory.WINDOWS,
        units="ms",
    )
    medianFilter: int | None = _field(
        0,
        title="Median Filter Points",
        description="Number of points in median filter, must be odd, 0 for no filter",
        category=DetectionParameterCategory.FILTERING,
        units="points",
    )
    SavitzkyGolay_pnts: int | None = _field(
        5,
        title="SavitzkyGolay Points",
        description="Number of points in SavitzkyGolay filter, must be odd, 0 for no filter",
        category=DetectionParameterCategory.FILTERING,
        units="points",
    )
    SavitzkyGolay_poly: int = _field(
        2,
        title="SavitzkyGolay Poly Deg",
        description="The degree of the polynomial for Savitzky-Golay filter",
        category=DetectionParameterCategory.FILTERING,
    )
    verbose: bool = _field(
        False,
        title="Verbose",
        description="Verbose Detection Reporting",
        category=DetectionParameterCategory.ADVANCED,
        units="Boolean",
    )

    @classmethod
    def from_saved(cls, data: Mapping[str, Any]) -> Self:
        """Load saved parameters while tolerating obsolete fields.

        Args:
            data: Saved detection parameter mapping.

        Returns:
            Validated parameters with current defaults added.

        Raises:
            ValidationError: If a known field contains an invalid value.
        """
        unknown = sorted(set(data) - set(cls.model_fields))
        for name in unknown:
            logger.warning(f'Ignoring unknown saved detection parameter "{name}"')
        normalized = {
            name: _normalize_missing(value)
            for name, value in data.items()
            if name in cls.model_fields
        }
        return cls.model_validate(normalized)

    def get_value(self, name: str) -> Any:
        """Return one parameter selected dynamically by name.

        Args:
            name: Detection parameter field name.

        Returns:
            The typed parameter value.

        Raises:
            KeyError: If the parameter name is unknown.
        """
        if name not in type(self).model_fields:
            raise KeyError(name)
        return getattr(self, name)

    def with_value(self, name: str, value: Any) -> Self:
        """Return a strictly validated copy with one changed value.

        Args:
            name: Detection parameter field name.
            value: Replacement parameter value.

        Returns:
            A new validated parameter model.

        Raises:
            KeyError: If the parameter name is unknown.
            ValidationError: If the replacement has the wrong type or value.
        """
        if name not in type(self).model_fields:
            raise KeyError(name)
        if name == "detectionType" and isinstance(value, str):
            value = detectionTypes_(value)
        candidate = self.model_dump(mode="python")
        candidate[name] = value
        return type(self).model_validate(candidate, strict=True)


def _normalize_missing(value: Any) -> Any:
    """Convert scalar pandas missing values to ``None``.

    Args:
        value: Value loaded from JSON or a pandas row.

    Returns:
        ``None`` for a recognized scalar missing value, otherwise the input.
    """
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if not isinstance(value, (str, bytes, list, tuple, dict)):
        missing = pd.isna(value)
        if bool(missing):
            return None
    return value


def _preset_names(path: str | pathlib.Path) -> tuple[str, str]:
    """Return the display and dictionary names for a preset path.

    Args:
        path: Detection-preset JSON path.

    Returns:
        The filename stem twice, preserving the historical two-name API.
    """
    name = os.path.splitext(os.path.basename(path))[0]
    return name, name


class bDetection:
    """Manage bundled and user-defined detection presets."""

    detectionTypes = detectionTypes_

    def __init__(self, sanpy_paths: SanPyPaths | None = None) -> None:
        """Load all bundled and user detection presets.

        Args:
            sanpy_paths: Optional application path manager.
        """
        self._sanpy_paths = sanpy_paths or SanPyPaths()
        self._userPresetNames: set[str] = set()
        self._detectionPreset = self._getPresetsDict()

    def getDetectionPresetList(self) -> list[str]:
        """Return the names of all loaded detection presets.

        Returns:
            Bundled and user-defined preset names.
        """
        return list(self._detectionPreset)

    def isUserPreset(self, name: str) -> bool:
        """Return whether a preset came from the user detection folder.

        Args:
            name: Detection-preset name.

        Returns:
            True when the preset was loaded from the user folder.
        """
        return name in self._userPresetNames

    def reloadPresets(self) -> None:
        """Reload bundled and user detection presets from disk."""
        self._userPresetNames = set()
        self._detectionPreset = self._getPresetsDict()

    def _getPresetsDict(self) -> dict[str, DetectionParameters]:
        """Load and validate bundled and user detection presets.

        Returns:
            Preset models keyed by filename stem.

        Raises:
            ValidationError: If a preset contains an invalid known value.
        """
        presets: dict[str, DetectionParameters] = {}
        bundled = self._sanpy_paths.bundled_dir / "detection-presets" / "*.json"
        for file_path in glob.glob(str(bundled)):
            _, key = _preset_names(file_path)
            with open(file_path, "r", encoding="utf-8") as handle:
                presets[key] = DetectionParameters.from_saved(json.load(handle))
        for file_path in self._getUserFiles():
            _, key = _preset_names(file_path)
            with open(file_path, "r", encoding="utf-8") as handle:
                presets[key] = DetectionParameters.from_saved(json.load(handle))
            self._userPresetNames.add(key)
        return presets

    def _getUserFiles(self) -> list[pathlib.Path]:
        """Return paths to user detection-preset files.

        Returns:
            Detection-preset JSON paths, or an empty list when unavailable.
        """
        path = self._sanpy_paths.detection_dir
        return list(path.glob("*.json")) if path.is_dir() else []

    def getDetectionDict(
        self, detectionType: str, allParameter: bool = True
    ) -> dict[str, Any]:
        """Return an independent JSON-compatible preset dictionary.

        Args:
            detectionType: Preset name, such as ``"SA Node"``.
            allParameter: Retained for compatibility; all fields are returned.

        Returns:
            Validated detection parameter values.

        Raises:
            KeyError: If the preset name is unknown.
        """
        return self._detectionPreset[detectionType].model_dump(mode="json")

    def getValue(self, detectionType: str, key: str) -> Any:
        """Return one value from a loaded detection preset.

        Args:
            detectionType: Loaded detection-preset name.
            key: Detection parameter field name.

        Returns:
            The parameter value, or ``None`` when either name is unknown.
        """
        try:
            return self._detectionPreset[detectionType].get_value(key)
        except KeyError:
            logger.warning(
                f'Did not find detectionType "{detectionType}" or key "{key}" to get current value'
            )
            return None

    def setValue(self, detectionType: str, key: str, value: Any) -> bool:
        """Strictly validate and store one preset value.

        Args:
            detectionType: Loaded detection-preset name.
            key: Detection parameter field name.
            value: Replacement value.

        Returns:
            True when the value was stored, otherwise False.
        """
        try:
            current = self._detectionPreset[detectionType]
            self._detectionPreset[detectionType] = current.with_value(key, value)
        except (KeyError, ValueError, ValidationError) as error:
            logger.warning(
                f'Could not set detectionType:{detectionType}, key:"{key}" to "{value}": {error}'
            )
            return False
        return True
