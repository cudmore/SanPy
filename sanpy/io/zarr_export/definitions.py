"""Normalize SanPy's live definitions for portable consumers."""

from __future__ import annotations

import copy
from typing import Any

from .json_codec import json_value


_DETECTION_CATEGORIES = {
    "detectionName": "identification",
    "userSaveName": "identification",
    "detectionType": "detection",
    "dvdtThreshold": "detection",
    "mvThreshold": "detection",
    "startSeconds": "analysis window",
    "stopSeconds": "analysis window",
    "cellType": "metadata",
    "sex": "metadata",
    "condition": "metadata",
    "userType": "metadata",
    "halfHeights": "duration",
    "preSpikeClipWidth_ms": "clips",
    "postSpikeClipWidth_ms": "clips",
    "verbose": "advanced",
}


def _detection_category(name: str) -> str:
    if name in _DETECTION_CATEGORIES:
        return _DETECTION_CATEGORIES[name]
    lowered = name.lower()
    if "filter" in lowered or "golay" in lowered:
        return "filtering"
    if "window" in lowered or "refractory" in lowered:
        return "detection windows"
    if "dvdt" in lowered:
        return "derivative"
    if "peak" in lowered:
        return "peak"
    if "mdp" in lowered or "diastolic" in lowered:
        return "diastolic"
    return "advanced"


def _result_category(name: str) -> str:
    lowered = name.lower()
    if name in {"spikeNumber", "sweep", "epoch", "sweepSpikeNumber"}:
        return "identity"
    if name in {"include", "userType", "errors"}:
        return "annotations"
    if "date" in lowered or "time" in lowered and name in {"analysisTime", "modTime"}:
        return "provenance"
    if name in {"analysisVersion", "interfaceVersion", "file", "cellType", "sex", "condition"}:
        return "provenance"
    if "threshold" in lowered:
        return "threshold"
    if "peak" in lowered or "ahp" in lowered:
        return "peak"
    if "width" in lowered:
        return "duration"
    if "isi" in lowered or "freq" in lowered or "cycle" in lowered:
        return "interval"
    if "diastolic" in lowered or "prelinear" in lowered or "premin" in lowered:
        return "diastolic"
    if "dvdt" in lowered:
        return "derivative"
    if name in {"epochLevel", "dacCommand"}:
        return "stimulus"
    return "other"


def detection_definitions(source: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output = {}
    for name, original in source.items():
        item = copy.deepcopy(original)
        item.pop("currentValue", None)
        output[name] = {
            "category": _detection_category(name),
            "type": _normalized_type(item.get("type")),
            "allow_none": bool(item.get("allowNone", False)),
            "default": json_value(item.get("defaultValue")),
            "units": str(item.get("units", "")),
            "human_name": str(item.get("humanName", name)),
            "description": str(item.get("description", "")),
        }
    return output


def result_definitions(source: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output = {}
    for name, item in source.items():
        output[name] = {
            "category": _result_category(name),
            "type": _normalized_type(item.get("type")),
            "default": json_value(item.get("default")),
            "units": str(item.get("units", "")),
            "depends_on_detection": str(item.get("depends on detection", "")),
            "error": str(item.get("error", "")),
            "description": str(item.get("description", "")),
        }
    return output


def _normalized_type(value: Any) -> str:
    text = str(value or "unknown")
    return {"str": "string", "bool": "boolean"}.get(text, text)
