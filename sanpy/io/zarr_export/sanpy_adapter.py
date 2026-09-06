"""Snapshot SanPy-owned state without mutating a bAnalysis instance."""

from __future__ import annotations

import copy
import uuid
from typing import Any

import numpy as np
import pandas as pd

import sanpy
from sanpy.bAnalysisResults import analysisResultDict
from sanpy.bDetection import getDefaultDetection
from sanpy.trace_overlays import get_trace_overlay_definitions

from .models import SanPySnapshot


def snapshot_banalysis(analysis: Any) -> SanPySnapshot:
    """Copy exportable state from a SanPy ``bAnalysis`` instance.

    Args:
        analysis: An ABF-backed SanPy analysis instance.

    Returns:
        An immutable snapshot of metadata, applied parameters, runtime
        definitions, results, and derived signals.
    """
    loader = analysis.fileLoader
    results = analysis.spikeDict.asDataFrame().copy(deep=True)
    if len(results.columns) == 0:
        results = results.reindex(columns=analysisResultDict)
    return SanPySnapshot(
        recording_id=str(getattr(analysis, "uuid", None) or uuid.uuid4()),
        metadata=copy.deepcopy(dict(analysis.metaData)),
        detection_parameters=copy.deepcopy(analysis.getDetectionDict() or {}),
        detection_definitions=copy.deepcopy(getDefaultDetection()),
        result_definitions=copy.deepcopy(analysisResultDict),
        trace_overlay_definitions=get_trace_overlay_definitions(),
        analysis_results=results,
        filtered=_copy_array(loader._filteredY),
        dvdt=_copy_array(loader._filteredDeriv),
        analysis_channel=0,
        sanpy_version=str(sanpy.__version__),
    )


def _copy_array(value: Any) -> np.ndarray | None:
    """Copy and orient a SanPy point-by-sweep array for persistence.

    Args:
        value: SanPy array-like value or ``None``.

    Returns:
        A sweep-by-point array copy, or ``None`` when no value exists.
    """
    return None if value is None else np.asarray(value).T.copy()
