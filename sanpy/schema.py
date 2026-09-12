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

    IDENTITY = "identity"  # like spike number
    PEAK_DETECTION = "peak detection"
    TIMING = "timing"  # like spike frequency or isi
    CUSTOM = "custom"
    # abb 20260912
    ACQUISITION = "acquisition"
    DETECTION = "detection"
    METADATA = "metadata"
    WIDTHS = "widths"