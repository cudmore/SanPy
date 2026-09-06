"""Write the two row-oriented resources in requested representations."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .json_codec import canonical_json


def prepare_table(table: pd.DataFrame) -> pd.DataFrame:
    output = table.copy(deep=True)
    for column in output.columns:
        if output[column].dtype == object:
            output[column] = output[column].map(_cell)
    return output


def write_table(table: pd.DataFrame, stem: Path, table_format: str) -> dict:
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


def _cell(value):
    if isinstance(value, (dict, list, tuple)):
        return canonical_json(value)
    return value
