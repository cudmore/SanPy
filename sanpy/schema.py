"""Shared runtime schema types for SanPy detection and analysis results."""

from enum import StrEnum


class DetectionParameterCategory(StrEnum):
    """Categories used to organize detection parameters for presentation."""

    GENERAL = "general"
    DETECTION = "detection"
    FILTERING = "filtering"
    WINDOWS = "windows"
    WAVEFORM = "waveform"
    ADVANCED = "advanced"


class AnalysisResultCategory(StrEnum):
    """Categories used to organize analysis results for presentation."""

    IDENTITY = "identity"
    ANNOTATION = "annotation"
    WAVEFORM = "waveform"
    TIMING = "timing"
    DERIVATIVE = "derivative"
    STIMULUS = "stimulus"
    CONFIGURATION = "configuration"
    PROVENANCE = "provenance"
    CUSTOM = "custom"
