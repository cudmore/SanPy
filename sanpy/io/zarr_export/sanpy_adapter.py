"""Snapshot SanPy-owned state without mutating a bAnalysis instance."""

from __future__ import annotations

import copy
import uuid

import numpy as np
import pandas as pd

import sanpy
from sanpy.bAnalysisResults import analysisResultDict
from sanpy.bDetection import getDefaultDetection

from .definitions import detection_definitions, result_definitions
from .models import SanPySnapshot


def snapshot_banalysis(analysis) -> SanPySnapshot:
    loader = analysis.fileLoader
    definitions = result_definitions(analysisResultDict)
    results = analysis.spikeDict.asDataFrame().copy(deep=True)
    if len(results.columns) == 0:
        results = results.reindex(columns=definitions)
    for column in results.columns:
        definitions.setdefault(
            str(column),
            {
                "category": "custom",
                "type": "unknown",
                "default": None,
                "units": "",
                "depends_on_detection": "",
                "error": "",
                "description": "Custom SanPy analysis result.",
            },
        )
    return SanPySnapshot(
        recording_id=str(getattr(analysis, "uuid", None) or uuid.uuid4()),
        metadata=copy.deepcopy(dict(analysis.metaData)),
        detection_parameters=copy.deepcopy(analysis.getDetectionDict() or {}),
        detection_definitions=detection_definitions(getDefaultDetection()),
        result_definitions=definitions,
        analysis_results=results,
        filtered=_copy_array(loader._filteredY),
        dvdt=_copy_array(loader._filteredDeriv),
        analysis_channel=0,
        sanpy_version=str(sanpy.__version__),
    )


def _copy_array(value) -> np.ndarray | None:
    return None if value is None else np.asarray(value).T.copy()
