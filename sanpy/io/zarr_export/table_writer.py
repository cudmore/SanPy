"""Write the two row-oriented resources in requested representations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .json_codec import canonical_json


def prepare_table(table: pd.DataFrame) -> pd.DataFrame:
    """Copy a table and encode structured object cells as canonical JSON.

    Args:
        table: Source dataframe containing runtime analysis values.

    Returns:
        An independent dataframe suitable for CSV or Parquet serialization.
    """
    output = table.copy(deep=True)
    for column in output.columns:
        if output[column].dtype == object:
            output[column] = output[column].map(_cell)
    return output


def write_table(table: pd.DataFrame, stem: Path, table_format: str) -> dict[str, Any]:
    """Write a logical table in the requested physical representations.

    Args:
        table: Source dataframe.
        stem: Output path without a filename extension.
        table_format: One of ``"csv"``, ``"parquet"``, or ``"both"``.

    Returns:
        Table resource metadata containing row count and representation paths.
    """
    prepared = prepare_table(table)
    resources = {}
    if table_format in {"csv", "both"}:
        path = stem.with_suffix(".csv")
        prepared.to_csv(path, index=False, float_format="%.17g", na_rep="null")
        resources["csv"] = path.name
    if table_format in {"parquet", "both"}:
        path = stem.with_suffix(".parquet")
        prepared.to_parquet(path, index=False, engine="pyarrow")
        resources["parquet"] = path.name
    return {"rows": len(prepared), "representations": resources}


def _cell(value: Any) -> Any:
    """Normalize one object-dtype table cell.

    Args:
        value: Cell value to normalize.

    Returns:
        Canonical JSON text for structured values, otherwise the original
        scalar value.
    """
    if isinstance(value, (dict, list, tuple)):
        return canonical_json(value)
    return value
