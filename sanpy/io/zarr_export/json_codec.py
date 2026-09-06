"""Strict conversion of SanPy values to portable JSON values."""

from __future__ import annotations

import enum
import json
import math
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def json_value(value: Any) -> Any:
    """Convert a runtime value into a strict, portable JSON value.

    Args:
        value: Runtime value to convert recursively.

    Returns:
        A value supported by the standard JSON data model.

    Raises:
        TypeError: If the value has no supported JSON representation.
    """
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_value(value.tolist())
    if isinstance(value, np.generic):
        return json_value(value.item())
    if isinstance(value, enum.Enum):
        return json_value(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return json_value(asdict(value))
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, Path):
        return value.name
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize a structured table cell as deterministic compact JSON.

    Args:
        value: Structured runtime value to serialize.

    Returns:
        Canonical JSON text with sorted keys and no insignificant whitespace.
    """
    return json.dumps(json_value(value), sort_keys=True, separators=(",", ":"))
